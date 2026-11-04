"""G2+ typer skeleton: claims -> resolution -> reference (anchor) -> signals -> policy -> fallback.

The reference is (S3) the KG statements of the question's (subject, property) in scope, an
upper-bound oracle; or (S0-S2) the consensus claim of the pool: the claim about the asked fact
with the most 'consistent' verdicts against the others (ties by pid). Known limitation: a
misinformation majority wins the consensus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from kgrerank.conflict.policy import POLICY_VERSION, PairVerdict, decide_pair
from kgrerank.conflict.signals import Resolved, pair_signals, resolve
from kgrerank.extract.claims import Claim
from kgrerank.extract.linker import EntityLinker, Link
from kgrerank.kg.settings import restrict
from kgrerank.kg.time import temporal_relation
from kgrerank.kg.view import KGView
from kgrerank.llm.base import ChatMessage, LLMBackend
from kgrerank.perturb.operators import QuestionFrame
from kgrerank.rerankers.llm_judge import PROMPT_V0, parse_decision
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
    def extract(self, pid: str, text: str) -> Claim | None: ...


@dataclass(frozen=True)
class TypedPassage:
    pid: str
    decision: Decision
    confidence: float
    reasons: tuple[str, ...]
    rule: str
    fallback: bool = False
    signals: dict[str, Any] | None = None
    policy: str = POLICY_VERSION


@dataclass
class G2PlusTyper:
    kg: KGView
    setting: str
    extractor: Extractor
    fallback: LLMBackend | None = None
    last_llm_calls: int = field(default=0, init=False)

    def _kg_anchors(self, view: KGView, frame: QuestionFrame) -> list[Resolved]:
        out = []
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
        self, view: KGView, frame: QuestionFrame, resolved: dict[str, Resolved]
    ) -> list[Resolved]:
        """Most-supported, most specific claim about the asked fact in the question's time scope."""
        about = [
            r
            for r in resolved.values()
            if r.prop == frame.prop  # the relation must be known to be the asked one
            and (r.subject.eid == frame.subject or r.subject.status == "none")
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
        # Exclude claims that are strictly coarser than another claim (e.g. a country vs a city).
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
        if support(best) == 0:
            # No claim is supported by another: no reliable consensus (a lone claim cannot
            # validate itself).
            return []
        return [best]

    def type_example(self, ex: Example, frame: QuestionFrame) -> list[TypedPassage]:
        view = restrict(self.kg, self.setting, mask=(frame.subject, frame.prop))
        linker = EntityLinker(view)
        claims = {c.pid: self.extractor.extract(c.pid, c.text) for c in ex.candidates}
        resolved = {pid: resolve(cl, linker, view, frame) for pid, cl in claims.items() if cl}
        anchors = (
            self._kg_anchors(view, frame)
            if self.setting == "S3"
            else self._consensus_anchor(view, frame, resolved)
        )
        self.last_llm_calls = 0
        out = []
        for cand in ex.candidates:
            r = resolved.get(cand.pid)
            if r is None:
                out.append(self._fallback(ex, cand.pid, cand.text, "R-no-claim"))
                continue
            if any(a.claim.pid == cand.pid for a in anchors):
                out.append(TypedPassage(cand.pid, Decision.COMPATIBLE, 0.5, (), "R-anchor"))
                continue
            refs: list[Resolved | None] = list(anchors) or [None]
            verdicts = [(decide_pair(sig := pair_signals(r, a, view, frame)), sig) for a in refs]
            v, sig = _best(verdicts)
            if v.relation == "unknown":
                out.append(
                    self._fallback(ex, cand.pid, cand.text, v.rule, sig.to_dict(), v.reasons)
                )
                continue
            out.append(
                TypedPassage(
                    cand.pid,
                    DECISION_OF[v.relation],
                    v.confidence,
                    v.reasons,
                    v.rule,
                    False,
                    sig.to_dict(),
                )
            )
        return out

    def _fallback(
        self,
        ex: Example,
        pid: str,
        text: str,
        rule: str,
        signals: dict[str, Any] | None = None,
        reasons: tuple[str, ...] = (),
    ) -> TypedPassage:
        if self.fallback is None:
            return TypedPassage(pid, Decision.UNKNOWN, 0.0, reasons, rule, False, signals)
        msg = PROMPT_V0.format(question=ex.question, passage=text)
        resp = self.fallback.chat([ChatMessage("user", msg)], max_tokens=4, seed=0)
        self.last_llm_calls += 1
        return TypedPassage(
            pid,
            parse_decision(resp.text),
            FALLBACK_CONFIDENCE,
            reasons,
            f"{rule}+llm_fallback",
            True,
            signals,
        )


def _best(verdicts: list[tuple[PairVerdict, Any]]) -> tuple[PairVerdict, Any]:
    """Against several reference values (S3): consistent with any wins, then conflict with all."""
    for rel in ("consistent", "unrelated"):
        for v, s in verdicts:
            if v.relation == rel:
                return v, s
    if all(v.relation == "conflict" for v, _ in verdicts):
        return min(verdicts, key=lambda vs: vs[0].confidence)
    return next((v, s) for v, s in verdicts if v.relation == "unknown")
