"""Inter-annotator agreement for two annotators (docs/ANNOTATION_GUIDELINES.md §6).

Decision: raw agreement, Cohen's kappa, confusion matrix. Reasons (multi-label sets):
Krippendorff's alpha with MASI distance (Passonneau 2006), mean Jaccard, exact-set agreement and
per-reason binary kappa. Confidence intervals use a cluster bootstrap over questions, because
several items share a question. No agreement threshold is defined here (owner rule).
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from typing import Any

from kgrerank.metrics.stats import _percentile


def raw_agreement(a: Sequence[Hashable], b: Sequence[Hashable]) -> float | None:
    if len(a) != len(b):
        raise ValueError("label sequences must be aligned")
    return sum(x == y for x, y in zip(a, b, strict=True)) / len(a) if a else None


def cohen_kappa(a: Sequence[Hashable], b: Sequence[Hashable]) -> float | None:
    """Cohen's kappa; None when undefined (no items, or chance agreement equals 1)."""
    po = raw_agreement(a, b)
    if po is None:
        return None
    n = len(a)
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1.0 - pe)


def confusion(
    a: Sequence[str], b: Sequence[str], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    out = {x: {y: 0 for y in labels} for x in labels}
    for x, y in zip(a, b, strict=True):
        out[x][y] += 1
    return out


def jaccard(x: frozenset[str], y: frozenset[str]) -> float:
    if not x and not y:
        return 1.0
    return len(x & y) / len(x | y)


def masi_distance(x: frozenset[str], y: frozenset[str]) -> float:
    """1 - Jaccard * monotonicity (1 equal, 2/3 subset, 1/3 overlap, 0 disjoint)."""
    if x == y:
        return 0.0
    if x <= y or y <= x:
        m = 2 / 3
    elif x & y:
        m = 1 / 3
    else:
        m = 0.0
    return 1.0 - jaccard(x, y) * m


def krippendorff_alpha_two(
    a: Sequence[Any], b: Sequence[Any], distance: Callable[[Any, Any], float]
) -> float | None:
    """Krippendorff's alpha for two coders who both coded every unit.

    D_o = mean distance within units; D_e = mean distance over all ordered pairs of the pooled
    2n values; alpha = 1 - D_o / D_e. None when undefined (no units, or D_e = 0).
    """
    if len(a) != len(b):
        raise ValueError("label sequences must be aligned")
    n = len(a)
    if n == 0:
        return None
    d_o = sum(distance(x, y) for x, y in zip(a, b, strict=True)) / n
    pooled = list(a) + list(b)
    total = sum(distance(pooled[i], pooled[j]) for i in range(2 * n) for j in range(i + 1, 2 * n))
    d_e = 2 * total / (2 * n * (2 * n - 1))
    if d_e == 0:
        return None
    return 1.0 - d_o / d_e


def cluster_bootstrap(
    clusters: Sequence[str],
    stat: Callable[[list[int]], float | None],
    n_boot: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float | None, float | None]:
    """Percentile CI of ``stat`` by resampling clusters (questions) with replacement."""
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(clusters):
        groups.setdefault(c, []).append(i)
    keys = sorted(groups)
    if not keys:
        return None, None
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        idx = [i for _ in keys for i in groups[keys[rng.randrange(len(keys))]]]
        v = stat(idx)
        if v is not None:
            vals.append(v)
    if not vals:
        return None, None
    vals.sort()
    return _percentile(vals, alpha / 2), _percentile(vals, 1 - alpha / 2)


def agreement_report(
    pairs: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    clusters: Sequence[str],
    decisions: Sequence[str],
    reason_types: Sequence[str],
    n_boot: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """Agreement over aligned items. ``pairs`` = (A1 labels, A2 labels) per item.

    Labels are dicts with decision, reasons and answer_support.
    """
    dec_a = [p[0]["decision"] for p in pairs]
    dec_b = [p[1]["decision"] for p in pairs]
    rs_a = [frozenset(p[0]["reasons"]) for p in pairs]
    rs_b = [frozenset(p[1]["reasons"]) for p in pairs]
    sup_a = [p[0]["answer_support"] for p in pairs]
    sup_b = [p[1]["answer_support"] for p in pairs]

    def sub(seq: Sequence[Any], idx: list[int]) -> list[Any]:
        return [seq[i] for i in idx]

    def kappa_on(idx: list[int]) -> float | None:
        return cohen_kappa(sub(dec_a, idx), sub(dec_b, idx))

    def alpha_on(idx: list[int]) -> float | None:
        return krippendorff_alpha_two(sub(rs_a, idx), sub(rs_b, idx), masi_distance)

    per_reason = {}
    for r in reason_types:
        xa = [r in s for s in rs_a]
        xb = [r in s for s in rs_b]
        per_reason[r] = {
            "n_A1": sum(xa),
            "n_A2": sum(xb),
            "n_both": sum(x and y for x, y in zip(xa, xb, strict=True)),
            "kappa": cohen_kappa(xa, xb) if (any(xa) or any(xb)) else None,
        }
    k_lo, k_hi = cluster_bootstrap(clusters, kappa_on, n_boot, seed)
    a_lo, a_hi = cluster_bootstrap(clusters, alpha_on, n_boot, seed + 1)
    return {
        "n_items": len(pairs),
        "n_questions": len(set(clusters)),
        "decision": {
            "raw_agreement": raw_agreement(dec_a, dec_b),
            "cohen_kappa": kappa_on(list(range(len(pairs)))),
            "cohen_kappa_ci95_cluster_bootstrap": [k_lo, k_hi],
            "confusion_A1_rows_A2_cols": confusion(dec_a, dec_b, decisions),
            "marginals_A1": dict(Counter(dec_a)),
            "marginals_A2": dict(Counter(dec_b)),
        },
        "reasons": {
            "krippendorff_alpha_masi": alpha_on(list(range(len(pairs)))),
            "krippendorff_alpha_masi_ci95_cluster_bootstrap": [a_lo, a_hi],
            "mean_jaccard": (
                sum(jaccard(x, y) for x, y in zip(rs_a, rs_b, strict=True)) / len(pairs)
            )
            if pairs
            else None,
            "exact_set_agreement": raw_agreement(rs_a, rs_b),
            "per_reason_binary": per_reason,
        },
        "answer_support": {
            "raw_agreement": raw_agreement(sup_a, sup_b),
            "cohen_kappa": cohen_kappa(sup_a, sup_b),
        },
        "bootstrap": {"n_boot": n_boot, "seed": seed, "unit": "question (cluster)"},
    }
