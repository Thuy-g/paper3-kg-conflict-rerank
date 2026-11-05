"""Conflict-aware reranker: score = relevance - lambda * confidence, only for CONTRADICTING.

Frames come from a frames file (automatic parser, or the separate human-audit diagnostic) keyed by
question ID, or — for synthetic fixtures only — from construction metadata with the answer
removed. A question without a supported frame gets no KG reasoning (fallback only). UNKNOWN,
IRRELEVANT and failed decisions are never penalised for being in conflict. mode="filter" removes
CONTRADICTING passages instead (for FCFR_filter and WFR).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kgrerank.conflict.typer import G2PlusTyper, TypedPassage
from kgrerank.frames.schema import InferenceFrame, frame_from_construction
from kgrerank.rerankers.base import Ranking, Reranker, sort_by_score
from kgrerank.schema import Decision, Example


@dataclass
class ConflictAwareReranker:
    base: Reranker
    typer: G2PlusTyper
    frames: dict[str, InferenceFrame] | None = None  # None: synthetic construction frames
    lam: float = 1.0
    mode: str = "penalize"
    name: str = "g2plus"
    last_typed: dict[str, list[TypedPassage]] = field(default_factory=dict, init=False)

    def frame_for(self, ex: Example) -> InferenceFrame | None:
        if self.frames is None:
            return frame_from_construction(ex.qid, ex.question, ex.meta)
        return self.frames.get(ex.qid)

    def rank(self, example: Example) -> Ranking:
        base = self.base.rank(example)
        typed = self.typer.type_example(example, self.frame_for(example), base.order)
        self.last_typed[example.qid] = typed
        usage = self.typer.last_usage
        contra = {t.pid: t.confidence for t in typed if t.decision is Decision.CONTRADICTING}
        n = len(base.order)
        scores = {pid: base.scores.get(pid, float(n - i)) for i, pid in enumerate(base.order)}
        if self.mode == "filter":
            kept = [p for p in base.order if p not in contra]
            return Ranking(
                order=tuple(kept),
                removed=base.removed | frozenset(contra),
                scores=scores,
                llm_calls=usage.get("calls", 0),
                llm_usage=usage,
            )
        new = {pid: s - self.lam * contra.get(pid, 0.0) for pid, s in scores.items()}
        return Ranking(
            order=sort_by_score(new, list(base.order)),
            removed=base.removed,
            scores=new,
            llm_calls=usage.get("calls", 0),
            llm_usage=usage,
        )
