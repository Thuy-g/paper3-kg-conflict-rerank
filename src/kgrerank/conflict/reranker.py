"""Conflict-aware reranker: score = relevance - lambda * confidence, only for CONTRADICTING.

UNKNOWN and IRRELEVANT passages are never penalised for being in conflict (IRRELEVANT ones are
left to the relevance scorer). mode="filter" removes CONTRADICTING passages instead, to measure
FCFR_filter and WFR. Examples without a question frame are returned unchanged (no typing).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kgrerank.conflict.typer import G2PlusTyper, TypedPassage
from kgrerank.perturb.operators import frame_from_meta
from kgrerank.rerankers.base import Ranking, Reranker, sort_by_score
from kgrerank.schema import Decision, Example


@dataclass
class ConflictAwareReranker:
    base: Reranker
    typer: G2PlusTyper
    lam: float = 1.0
    mode: str = "penalize"
    name: str = "g2plus"
    last_typed: dict[str, list[TypedPassage]] = field(default_factory=dict, init=False)

    def rank(self, example: Example) -> Ranking:
        base = self.base.rank(example)
        frame = frame_from_meta(example.meta)
        if frame is None:
            return base
        typed = self.typer.type_example(example, frame)
        self.last_typed[example.qid] = typed
        contra = {t.pid: t.confidence for t in typed if t.decision is Decision.CONTRADICTING}
        n = len(base.order)
        scores = {pid: base.scores.get(pid, float(n - i)) for i, pid in enumerate(base.order)}
        if self.mode == "filter":
            kept = [p for p in base.order if p not in contra]
            return Ranking(
                order=tuple(kept),
                removed=base.removed | frozenset(contra),
                scores=scores,
                llm_calls=self.typer.last_llm_calls,
            )
        new = {pid: s - self.lam * contra.get(pid, 0.0) for pid, s in scores.items()}
        return Ranking(
            order=sort_by_score(new, list(base.order)),
            removed=base.removed,
            scores=new,
            llm_calls=self.typer.last_llm_calls,
        )
