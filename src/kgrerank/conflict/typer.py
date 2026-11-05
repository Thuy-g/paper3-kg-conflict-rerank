"""G2+ typer skeleton: frame -> claims -> resolution -> reference -> signals -> policy -> fallback.

Input per question: the passages and an InferenceFrame (no answers, no gold labels). If the frame
is not supported (multi-hop, comparison, unlinked subject/property, unresolved time, parser
error) the KG step is skipped and every passage goes to the fallback.

Reference: (S3) the KG statements of the question's (subject, property) in scope — an
answer-access upper bound, never the main setting; or (S0-S2) the consensus claim of the pool,
i.e. the most specific claim about the asked fact supported by at least one other claim. A lone
claim cannot validate itself; a misinformation majority can win (known limitation).

Fallback: an LLMTyper (by default the same inter-context prompt as the LLM-only baseline), so the
comparison 'G2+ vs LLM-only' isolates what the KG step adds. Fallback errors keep their status and
are not counted as valid decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from kgrerank.conflict.policy import POLICY_VERSION, PairVerdict, decide_pair
from kgrerank.conflict.signals import Resolved, pair_signals, resolve
from kgrerank.extract.claims import Claim
from kgrerank.extract.linker import EntityLinker, Link
from kgrerank.frames.schema import InferenceFrame
from kgrerank.kg.settings import restrict
from kgrerank.kg.time import temporal_relation
from kgrerank.kg.view import KGView
from kgrerank.llm.base import summarize_events
from kgrerank.rerankers.llm_judge import LLMTyper
from kgrerank.schema import Decision, Example
from kgrerank.signals import TemporalRelation

DECISION_OF = {
    "consistent": Decision.COMPATIBLE,
    "conflict": Decision.CONTRADICTING,
    "unrelated": Decision.IRRELEVANT,
    "unknown": Decision.UNKNOWN,
}
FALLBACK_CONFIDENCE = 0.3


class Extractor(Protocol):
    def extract_with_status(
        self, pid: str, text: str, question: str
    ) -> tuple[Claim | None, str]: ...


@dataclass(frozen=True)
class TypedPassage:
    pid: str
    decision: Decision | None  # None when the fallback call failed (see status)
    confidence: float
    reasons: tuple[str, ...]
    rule: str
    status: str  # kg | fallback_ok | fallback_<error> | undecided (no fallback configured)
    extraction_status: str = ""
    signals: dict[str, Any] | None = None
    policy: str = POLICY_VERSION


@dataclass
class G2PlusTyper:
    kg: KGView
    setting: str
    extractor: Extractor
    fallback: LLMTyper | None = None
    last_usage: dict[str, Any] = field(default_factory=dict, init=False)

    def _backends(self) -> list[Any]:
        found: dict[int, Any] = {}
        for obj in (
            getattr(self.extractor, "backend", None),
            self.fallback.backend if self.fallback else None,
        ):
            if obj is not None:
                found[id(obj)] = obj
        return list(found.values())

    def _kg_anchors(self, view: KGView, frame: InferenceFrame) -> list[Resolved]:
        out = []
        assert frame.subject and frame.prop
        for st in view.statements_of(frame.subject, frame.prop, include_deprecated=False):
            if st.value.kind != "item":
                continue
            iv = st.interval() if st.has_temporal_qualifier() else None
            if (
                frame.time_anchor is not None
                and iv is not None
                and temporal_relation(iv, frame.time_anchor) is TemporalRelation.DISJOINT
            ):
                continue
            claim = Claim(
                f"kg:{st.sid}",
                view.label(frame.subject),
                "",
                view.label(st.value.value),
                iv,
                extractor="kg",
            )
            out.append(
                Resolved(
                    claim,
                    Link(claim.subject, (frame.subject,), "unique", "qid"),
                    Link(claim.obj, (st.value.value,), "unique", "qid"),
                    frame.prop,
                )
            )
        return out

    def _consensus_anchor(
        self, view: KGView, frame: InferenceFrame, resolved: dict[str, Resolved]
    ) -> list[Resolved]:
        about = [
            r
            for r in resolved.values()
            if r.prop == frame.prop  # the relation must be known to be the asked one
            and r.subject.eid == frame.subject  # and the subject uniquely linked to it
            and not (
                frame.time_anchor is not None
                and r.claim.time is not None
                and temporal_relation(r.claim.time, frame.time_anchor) is TemporalRelation.DISJOINT
            )
        ]
        if not about:
            return []
        verdict = {
            (a.claim.pid, b.claim.pid): decide_pair(pair_signals(a, b, view, frame))
            for a in about
            for b in about
            if a is not b
        }
        coarse = {a for (a, _), v in verdict.items() if v.rule == "R-hierarchy-coarser"}
        pool = [r for r in about if r.claim.pid not in coarse] or about

        def support(a: Resolved) -> int:
            return sum(
                verdict[(a.claim.pid, b.claim.pid)].relation == "consistent"
                or verdict[(b.claim.pid, a.claim.pid)].relation == "consistent"
                for b in about
                if b is not a
            )

        best = sorted(pool, key=lambda r: (-support(r), r.claim.pid))[0]
        return [best] if support(best) > 0 else []

    def type_example(
        self, ex: Example, frame: InferenceFrame | None, context_order: Sequence[str]
    ) -> list[TypedPassage]:
        starts = {id(b): len(b.events) for b in self._backends()}
        if frame is None or not frame.supported:
            pending = [(c.pid, "R-frame-unsupported", None, (), "") for c in ex.candidates]
            out = self._resolve_pending(ex, pending, context_order)
            self._usage(starts)
            return out
        view = restrict(self.kg, self.setting, mask=(frame.subject or "", frame.prop or ""))
        linker = EntityLinker(view)
        claims, ext_status = {}, {}
        for c in ex.candidates:
            claims[c.pid], ext_status[c.pid] = self.extractor.extract_with_status(
                c.pid, c.text, ex.question
            )
        resolved = {pid: resolve(cl, linker, view, frame) for pid, cl in claims.items() if cl}
        anchors = (
            self._kg_anchors(view, frame)
            if self.setting == "S3"
            else self._consensus_anchor(view, frame, resolved)
        )
        out: dict[str, TypedPassage] = {}
        pending = []
        for cand in ex.candidates:
            r = resolved.get(cand.pid)
            if r is None:
                pending.append((cand.pid, "R-no-claim", None, (), ext_status[cand.pid]))
                continue
            if any(a.claim.pid == cand.pid for a in anchors):
                out[cand.pid] = TypedPassage(
                    cand.pid, Decision.COMPATIBLE, 0.5, (), "R-anchor", "kg", ext_status[cand.pid]
                )
                continue
            refs: list[Resolved | None] = list(anchors) or [None]
            verdicts = [(decide_pair(sig := pair_signals(r, a, view, frame)), sig) for a in refs]
            v, sig = _best(verdicts)
            if v.relation == "unknown":
                pending.append((cand.pid, v.rule, sig.to_dict(), v.reasons, ext_status[cand.pid]))
                continue
            out[cand.pid] = TypedPassage(
                cand.pid,
                DECISION_OF[v.relation],
                v.confidence,
                v.reasons,
                v.rule,
                "kg",
                ext_status[cand.pid],
                sig.to_dict(),
            )
        for t in self._resolve_pending(ex, pending, context_order):
            out[t.pid] = t
        self._usage(starts)
        return [out[c.pid] for c in ex.candidates]

    def _resolve_pending(
        self, ex: Example, pending: list[tuple], context_order: Sequence[str]
    ) -> list[TypedPassage]:
        if not pending:
            return []
        if self.fallback is None:
            return [
                TypedPassage(pid, Decision.UNKNOWN, 0.0, reasons, rule, "undecided", es, sig)
                for pid, rule, sig, reasons, es in pending
            ]
        decisions = self.fallback.type_passages(ex, [p[0] for p in pending], context_order)
        out = []
        for pid, rule, sig, reasons, es in pending:
            d = decisions[pid]
            status = "fallback_ok" if d.status == "ok" else f"fallback_{d.status}"
            out.append(
                TypedPassage(
                    pid,
                    d.decision,
                    FALLBACK_CONFIDENCE if d.decision else 0.0,
                    reasons,
                    f"{rule}+llm_fallback",
                    status,
                    es,
                    sig,
                )
            )
        return out

    def _usage(self, starts: dict[int, int]) -> None:
        events = [e for b in self._backends() for e in b.events[starts.get(id(b), 0) :]]
        self.last_usage = summarize_events(events)


def _best(verdicts: list[tuple[PairVerdict, Any]]) -> tuple[PairVerdict, Any]:
    """Against several reference values (S3): consistent with any wins, then conflict with all."""
    for rel in ("consistent", "unrelated"):
        for v, s in verdicts:
            if v.relation == rel:
                return v, s
    if all(v.relation == "conflict" for v, _ in verdicts):
        return min(verdicts, key=lambda vs: vs[0].confidence)
    return next((v, s) for v, s in verdicts if v.relation == "unknown")
