"""Statistics with the query as the unit (docs/PLAN.md B.6). Pure Python, seeded, deterministic."""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CI:
    mean: float
    lo: float
    hi: float
    n: int


def _percentile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear interpolation percentile, q in [0, 1]."""
    if not sorted_vals:
        raise ValueError("empty sequence")
    pos = q * (len(sorted_vals) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def bootstrap_ci(values: Sequence[float], n_boot: int, seed: int, alpha: float = 0.05) -> CI:
    """Percentile bootstrap CI of the mean, resampling queries with replacement."""
    vals = list(values)
    if not vals:
        raise ValueError("no values")
    n = len(vals)
    rng = random.Random(seed)
    means = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return CI(sum(vals) / n, _percentile(means, alpha / 2), _percentile(means, 1 - alpha / 2), n)


def paired_bootstrap_ci(
    a: Sequence[float], b: Sequence[float], n_boot: int, seed: int, alpha: float = 0.05
) -> CI:
    """CI of mean(b - a); the same resampled query indices are used for both systems."""
    if len(a) != len(b):
        raise ValueError("paired samples must be aligned and of equal length")
    return bootstrap_ci([y - x for x, y in zip(a, b, strict=True)], n_boot, seed, alpha)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from discordant counts b (0→1) and c (1→0)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def holm(pvalues: Mapping[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (monotone, capped at 1)."""
    items = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def minimum_detectable_effect(
    sd_diff: float, n: int, alpha: float = 0.05, power: float = 0.8
) -> float:
    """MDE of a paired mean difference (normal approximation, two-sided test)."""
    if n <= 0:
        raise ValueError("n must be positive")
    z = statistics.NormalDist()
    return (z.inv_cdf(1 - alpha / 2) + z.inv_cdf(power)) * sd_diff / math.sqrt(n)


def seed_summary(values: Sequence[float]) -> tuple[float, float]:
    """Mean and sample SD across seeds (SD = 0.0 for a single seed)."""
    vals = list(values)
    if not vals:
        raise ValueError("no values")
    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return statistics.fmean(vals), sd
