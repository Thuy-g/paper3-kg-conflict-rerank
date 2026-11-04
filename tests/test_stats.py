from __future__ import annotations

import pytest

from kgrerank.metrics.stats import (
    bootstrap_ci,
    holm,
    mcnemar_exact,
    minimum_detectable_effect,
    paired_bootstrap_ci,
    seed_summary,
)


def test_bootstrap_deterministic_and_sane():
    vals = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    a, b = bootstrap_ci(vals, 500, seed=7), bootstrap_ci(vals, 500, seed=7)
    assert a == b and a.lo <= a.mean <= a.hi and a.n == 8
    const = bootstrap_ci([0.3] * 5, 200, seed=1)
    assert const.lo == pytest.approx(0.3) and const.hi == pytest.approx(0.3)
    with pytest.raises(ValueError):
        bootstrap_ci([], 10, 1)


def test_paired_bootstrap():
    ci = paired_bootstrap_ci([0.0, 0.0, 0.0], [1.0, 1.0, 1.0], 200, seed=3)
    assert ci.mean == 1.0 and ci.lo == 1.0
    with pytest.raises(ValueError):
        paired_bootstrap_ci([0.0], [1.0, 2.0], 10, 1)


def test_mcnemar_exact_hand_values():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(0, 6) == pytest.approx(2 / 64)
    assert mcnemar_exact(1, 9) == pytest.approx(22 / 1024)
    assert mcnemar_exact(5, 5) == 1.0


def test_holm():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})


def test_mde_and_seed_summary():
    assert minimum_detectable_effect(1.0, 100) == pytest.approx(0.2801585218, abs=1e-9)
    assert seed_summary([1.0]) == (1.0, 0.0)
    mu, sd = seed_summary([1.0, 3.0])
    assert mu == 2.0 and sd == pytest.approx(1.41421356, abs=1e-6)
