"""Identity, seeded random, and oracle rerankers (oracles are for metric sanity checks only)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from kgrerank.rerankers.base import Ranking, Reranker
from kgrerank.schema import Decision, Example


@dataclass
class IdentityReranker:
    """Keeps the original pool order (for example the retriever's order)."""

    name: str = "identity"

    def rank(self, example: Example) -> Ranking:
        return Ranking(order=tuple(c.pid for c in example.candidates))


@dataclass
class RandomReranker:
    """Uniform random permutation; deterministic per (seed, qid)."""

    seed: int
    name: str = "random"

    def rank(self, example: Example) -> Ranking:
        rng = random.Random(f"{self.seed}|{example.qid}")
        pids = sorted(c.pid for c in example.candidates)
        rng.shuffle(pids)
        return Ranking(order=tuple(pids))


ORACLE_MODES = ("gold_first", "drop_contradicting", "drop_any_reason", "demote_any_reason")


@dataclass
class OracleReranker:
    """Uses gold labels. Only for checking metric implementations; never a baseline.

    Applied on top of a ``base`` ranking (default: pool order), so that paired metrics against
    the same base isolate the effect of the oracle. Modes: ``gold_first`` (gold passages first),
    ``drop_contradicting`` (ideal genuine-conflict filter), ``drop_any_reason`` (over-aggressive
    filter removing every passage with a surface disagreement), ``demote_any_reason`` (moves those
    passages to the bottom).
    """

    mode: str
    base: Reranker | None = None
    name: str = ""

    def __post_init__(self) -> None:
        if self.mode not in ORACLE_MODES:
            raise ValueError(f"unknown oracle mode {self.mode!r}")
        if not self.name:
            self.name = f"oracle:{self.mode}"

    def rank(self, example: Example) -> Ranking:
        base = (self.base or IdentityReranker()).rank(example)
        by_pid = {c.pid: c for c in example.candidates}
        order = list(base.order)
        if self.mode == "gold_first":
            order = [p for p in order if by_pid[p].is_gold] + [
                p for p in order if not by_pid[p].is_gold
            ]
            return Ranking(order=tuple(order), removed=base.removed, scores=base.scores)
        if self.mode == "drop_contradicting":
            drop = {p for p in order if by_pid[p].decision is Decision.CONTRADICTING}
        else:
            drop = {p for p in order if by_pid[p].reasons}
        kept = [p for p in order if p not in drop]
        if self.mode == "demote_any_reason":
            return Ranking(
                order=tuple(kept + [p for p in order if p in drop]),
                removed=base.removed,
                scores=base.scores,
            )
        return Ranking(
            order=tuple(kept), removed=base.removed | frozenset(drop), scores=base.scores
        )
