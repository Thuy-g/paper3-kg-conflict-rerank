"""LLM question parser + deterministic linking into an InferenceFrame.

The parser sees only the question text and the benchmark snapshot description; it never sees
reference answers, passages, gold labels, supporting-fact flags or dataset question types.
Linking keeps ambiguity: several candidate entities give ``ambiguous`` (no choice is made), no
candidate gives ``unlinked``. Property mapping is an exact (case-insensitive) match against the
property labels of the KG view. Relative time words are resolved only against the snapshot.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import replace

from kgrerank.extract.linker import EntityLinker
from kgrerank.frames.schema import QUESTION_TYPES, InferenceFrame, Snapshot
from kgrerank.kg.time import year_period
from kgrerank.llm.base import ChatMessage, LLMBackend

PARSER_VERSION = "frame_parser_v1"
PROMPT_V1 = (
    "Question: {question}\n\n"
    "Describe what the question asks, without answering it. Reply with JSON only:\n"
    '{{"subject": "<the entity the question is about, as written in the question>", '
    '"relation": "<the property asked for, as a short noun phrase, e.g. place of birth>", '
    '"time_expression": "<the time words of the question, as written, or empty>", '
    '"question_type": "single_fact" | "multi_hop" | "comparison" | "list_or_count" | "other"}}\n'
    "single_fact: one property of one entity. multi_hop: needs an intermediate entity. "
    "comparison: compares two or more entities. Use empty strings when unsure."
)
RELATIVE = re.compile(
    r"\b(current|currently|now|today|present|latest|most recent|recent|so far|as of now|"
    r"this year|last year|next|last|upcoming|still)\b",
    re.I,
)
YEAR = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
_JSON = re.compile(r"\{.*\}", re.S)


def resolve_time(expr: str, snapshot: Snapshot) -> tuple[object | None, str]:
    """Return (Interval | None, status). Explicit years win; relative words need the snapshot."""
    expr = (expr or "").strip()
    if not expr:
        return None, "none"
    years = YEAR.findall(expr)
    if len(set(years)) == 1 and not RELATIVE.search(expr):
        return year_period(int(years[0])), "explicit"
    if RELATIVE.search(expr) and not years:
        if not snapshot.defined():
            return None, "unresolved"
        low = expr.lower()
        if "this year" in low and snapshot.year() is not None:
            return year_period(snapshot.year()), "snapshot_relative"  # type: ignore[arg-type]
        if "last year" in low and snapshot.year() is not None:
            return year_period(snapshot.year() - 1), "snapshot_relative"  # type: ignore[operator]
        return snapshot.moment(), "snapshot_relative"
    return None, "unresolved"


class LLMFrameParser:
    def __init__(
        self,
        backend: LLMBackend,
        linker: EntityLinker,
        relation_labels: Sequence[str],
        snapshot: Snapshot,
        max_tokens: int = 256,
        temperature: float = 0.0,
        seed: int | None = 0,
        prompt: str = PROMPT_V1,
    ):
        self.backend, self.linker, self.snapshot = backend, linker, snapshot
        self.labels = {lab.lower(): lab for lab in relation_labels if lab}
        self.max_tokens, self.temperature, self.seed, self.prompt = (
            max_tokens,
            temperature,
            seed,
            prompt,
        )

    def parse(self, qid: str, question: str) -> InferenceFrame:
        base = InferenceFrame(
            qid=qid,
            question=question,
            source="llm_parser",
            parser_version=PARSER_VERSION,
            model=self.backend.model,
        )
        resp = self.backend.chat(
            [ChatMessage("user", self.prompt.format(question=question))],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            seed=self.seed,
            role="frame_parse",
        )
        if resp.status != "ok":
            return replace(base, errors=(resp.status,))
        m = _JSON.search(resp.text)
        try:
            d = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            d = None
        if not isinstance(d, dict):
            return replace(base, errors=("parse_error",))
        qtype = str(d.get("question_type", "")).strip()
        subj, rel = str(d.get("subject") or "").strip(), str(d.get("relation") or "").strip()
        texpr = str(d.get("time_expression") or "").strip()
        errors: list[str] = []
        if qtype not in QUESTION_TYPES or qtype == "unparsed":
            errors.append("bad_question_type")
            qtype = "other"
        if subj and subj.casefold() not in question.casefold():
            errors.append("subject_not_in_question")  # parser must quote, not invent
        link = self.linker.link(subj) if subj else None
        if link is None:
            s_status, s_qid, cands = "unlinked", None, ()
        else:
            s_status = {"unique": "linked", "ambiguous": "ambiguous", "none": "unlinked"}[
                link.status
            ]
            s_qid = link.eid if link.status == "unique" else None
            cands = link.candidates
        pid = self.linker.property_by_label(rel) if rel else None
        p_status = "linked" if pid else "unlinked"
        anchor, t_status = resolve_time(texpr, self.snapshot)
        return replace(
            base,
            subject=s_qid,
            subject_mention=subj,
            subject_status=s_status,
            subject_candidates=tuple(cands),
            prop=pid,
            relation_mention=rel,
            prop_status=p_status,
            time_anchor=anchor,
            time_expression=texpr,
            time_status=t_status,
            question_type=qtype,
            errors=tuple(errors),
        )


def coverage(frames: Sequence[InferenceFrame]) -> dict[str, object]:
    """Coverage over ALL questions, including those the KG step cannot handle."""
    n = len(frames)

    def count(attr: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in frames:
            v = getattr(f, attr)
            out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items()))

    errs: dict[str, int] = {}
    for f in frames:
        for e in f.errors:
            errs[e] = errs.get(e, 0) + 1
    supported = sum(f.supported for f in frames)
    return {
        "questions": n,
        "supported": supported,
        "supported_share": (supported / n) if n else None,
        "question_type": count("question_type"),
        "subject_status": count("subject_status"),
        "prop_status": count("prop_status"),
        "time_status": count("time_status"),
        "errors": dict(sorted(errs.items())),
    }
