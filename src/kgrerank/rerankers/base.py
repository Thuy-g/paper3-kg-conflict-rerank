"""Common interface: a reranker returns an ordering of kept candidates plus the removed set."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from kgrerank.schema import Example


@dataclass(frozen=True)
class Ranking:
    """Kept candidates best-first, plus candidates removed by a filter (rank = infinity)."""

    order: tuple[str, ...]
    removed: frozenset[str] = frozenset()
    scores: dict[str, float] = field(default_factory=dict)
    llm_calls: int = 0

    def top(self, k: int) -> tuple[str, ...]:
        return self.order[:k]

    def rank_of(self, pid: str) -> int | None:
        """1-based rank, or None if removed or absent."""
        try:
            return self.order.index(pid) + 1
        except ValueError:
            return None


def check_ranking(example: Example, ranking: Ranking) -> None:
    """A ranking must be a partition of the example's pool into kept (ordered) and removed."""
    pool = [c.pid for c in example.candidates]
    kept = list(ranking.order)
    if len(set(kept)) != len(kept):
        raise ValueError(f"{example.qid}: duplicated pids in ranking")
    if set(kept) & ranking.removed:
        raise ValueError(f"{example.qid}: a pid is both kept and removed")
    if set(kept) | ranking.removed != set(pool):
        raise ValueError(f"{example.qid}: ranking does not cover the candidate pool exactly")


class Reranker(Protocol):
    name: str

    def rank(self, example: Example) -> Ranking: ...


def sort_by_score(scores: dict[str, float], pool_order: list[str]) -> tuple[str, ...]:
    """Descending score; ties broken by pid (stable and explicit)."""
    return tuple(sorted(pool_order, key=lambda pid: (-scores[pid], pid)))
