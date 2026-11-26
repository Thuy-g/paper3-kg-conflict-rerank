"""Recall@k, MRR and nDCG@k with binary relevance (``is_gold``). ``None`` = undefined (no gold).

With incomplete relevance judgments (e.g. CONFLICTS, where only sampled passages were annotated)
unjudged passages must not count as non-relevant. ``condense`` removes unjudged passages from a
ranking before computing a metric ("condensed list" evaluation; Sakai, SIGIR 2007 —
[UNVERIFIED: citation not checked in session]). Full-list metrics are reported only when the
judgments cover the whole pool.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence


def recall_at_k(order: Sequence[str], gold: Collection[str], k: int) -> float | None:
    if not gold:
        return None
    return len(set(order[:k]) & set(gold)) / len(set(gold))


def mrr(order: Sequence[str], gold: Collection[str]) -> float | None:
    if not gold:
        return None
    gold_set = set(gold)
    for i, pid in enumerate(order, start=1):
        if pid in gold_set:
            return 1.0 / i
    return 0.0


def ndcg_at_k(order: Sequence[str], gold: Collection[str], k: int) -> float | None:
    if not gold:
        return None
    gold_set = set(gold)
    dcg = sum(1.0 / math.log2(i + 2) for i, pid in enumerate(order[:k]) if pid in gold_set)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(gold_set))))
    return dcg / idcg


def condense(order: Sequence[str], judged: Collection[str]) -> list[str]:
    """Keep only judged passages, in ranking order."""
    js = set(judged)
    return [p for p in order if p in js]
