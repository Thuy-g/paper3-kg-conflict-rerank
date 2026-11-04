"""Conflict metrics on a fixed pool (docs/PLAN.md B.4). Unit = query; ``None`` = undefined.

A_q: COMPATIBLE passages with at least one reason (apparent conflicts); K_q: all COMPATIBLE
passages; N_q: CONTRADICTING passages. ``ref`` is a relevance-only reference ranking from the same
scorer without conflict handling; the paired variants count only passages the reference kept in
its top-k, so a passage that was never retrieved highly is not blamed on the method.
"""

from __future__ import annotations

from collections.abc import Iterable

from kgrerank.rerankers.base import Ranking
from kgrerank.schema import Candidate, Decision, Example


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def apparent_compatible(ex: Example, reason: str | None = None) -> set[str]:
    return {
        c.pid
        for c in ex.candidates
        if c.decision is Decision.COMPATIBLE
        and c.reasons
        and (reason is None or reason in c.reasons)
    }


def compatible(ex: Example) -> set[str]:
    return {c.pid for c in ex.candidates if c.decision is Decision.COMPATIBLE}


def contradicting(ex: Example, reason: str | None = None) -> set[str]:
    return {
        c.pid
        for c in ex.candidates
        if c.decision is Decision.CONTRADICTING and (reason is None or reason in c.reasons)
    }


def outside_top_k(target: set[str], ranking: Ranking, k: int) -> float | None:
    """Share of ``target`` not in the top-k of ``ranking`` (removed passages count as outside)."""
    top = set(ranking.top(k))
    return _ratio(len(target - top), len(target))


def paired_outside_top_k(target: set[str], ranking: Ranking, ref: Ranking, k: int) -> float | None:
    """Share of ``target`` passages in the reference top-k that the method pushed out or removed."""
    base = target & set(ref.top(k))
    return _ratio(len(base - set(ranking.top(k))), len(base))


def removed_share(target: set[str], ranking: Ranking) -> float | None:
    return _ratio(len(target & ranking.removed), len(target))


def wfr(ex: Example, ranking: Ranking) -> float | None:
    """EvoTrustRAG Eq. 8 per query: 1 if any passage that should stay available was removed.

    'Should remain available' = COMPATIBLE passages. Undefined when the query has none.
    """
    keep = compatible(ex)
    if not keep:
        return None
    return float(bool(keep & ranking.removed))


def conflict_metrics(
    ex: Example, ranking: Ranking, ref: Ranking, ks: Iterable[int], reasons: Iterable[str] = ()
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    a_set, n_set = apparent_compatible(ex), contradicting(ex)
    for k in ks:
        out[f"fcfr_abs@{k}"] = outside_top_k(a_set, ranking, k)
        out[f"fcfr_paired@{k}"] = paired_outside_top_k(a_set, ranking, ref, k)
        out[f"ger_abs@{k}"] = outside_top_k(n_set, ranking, k)
        out[f"ger_paired@{k}"] = paired_outside_top_k(n_set, ranking, ref, k)
        for r in reasons:
            out[f"fcfr_paired@{k}[{r}]"] = paired_outside_top_k(
                apparent_compatible(ex, r), ranking, ref, k
            )
    out["fcfr_filter"] = removed_share(a_set, ranking)
    out["ger_filter"] = removed_share(n_set, ranking)
    out["wfr"] = wfr(ex, ranking)
    return out


def pooled_counts(cands: Iterable[Candidate]) -> dict[str, int]:
    """Passage counts per decision (for reporting micro/pooled denominators)."""
    counts: dict[str, int] = {d.value: 0 for d in Decision}
    for c in cands:
        counts[c.decision.value] += 1
    return counts
