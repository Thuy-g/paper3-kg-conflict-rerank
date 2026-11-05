"""Metrics for methods that output a decision per passage (docs/PLAN.md B.5).

Gold UNKNOWN passages are excluded. A predicted UNKNOWN counts as abstention: it lowers coverage
and is excluded from selective accuracy, but counts as wrong in plain accuracy and macro-F1.
Macro-F1 averages over the classes that occur in gold or prediction (the scikit-learn convention),
so a class absent from a small stratum does not add an F1 of zero.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Any

from kgrerank.schema import Decision

CLASSES: tuple[Decision, ...] = (Decision.COMPATIBLE, Decision.CONTRADICTING, Decision.IRRELEVANT)


def decision_metrics(pairs: Sequence[tuple[Decision, Decision]]) -> dict[str, float | dict | None]:
    """``pairs`` = (gold, predicted). Returns accuracy, macro-F1, coverage, selective accuracy."""
    pairs = [(g, p) for g, p in pairs if g is not Decision.UNKNOWN]
    n = len(pairs)
    confusion = {g.value: {p.value: 0 for p in Decision} for g in CLASSES}
    for g, p in pairs:
        confusion[g.value][p.value] += 1
    if n == 0:
        return {
            "n": 0,
            "accuracy": None,
            "macro_f1": None,
            "coverage": None,
            "selective_accuracy": None,
            "confusion": confusion,
        }
    correct = sum(g is p for g, p in pairs)
    covered = [(g, p) for g, p in pairs if p is not Decision.UNKNOWN]
    f1s = []
    for cls in CLASSES:
        tp = sum(g is cls and p is cls for g, p in pairs)
        fp = sum(g is not cls and p is cls for g, p in pairs)
        fn = sum(g is cls and p is not cls for g, p in pairs)
        if tp + fp + fn == 0:
            continue  # class absent from gold and prediction: not averaged
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return {
        "n": n,
        "accuracy": correct / n,
        "macro_f1": sum(f1s) / len(f1s) if f1s else None,
        "coverage": len(covered) / n,
        "selective_accuracy": (sum(g is p for g, p in covered) / len(covered)) if covered else None,
        "confusion": confusion,
    }


def typing_report(
    items: Sequence[tuple[str, Decision, Decision | None, str]],
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """Typing metrics against gold decisions, with question-level (cluster) bootstrap CIs.

    ``items``: (qid, gold, predicted or None, status). Gold UNKNOWN is excluded. A failed call
    (predicted None) is not an abstention: it counts as a miss in accuracy and macro-F1, lowers
    coverage, and is reported as a failure rate. All rates share the denominator ``n_passages``.
    Passages of one question are not independent, so the bootstrap resamples questions.
    """
    from kgrerank.metrics.stats import _percentile

    rows = [r for r in items if r[1] is not Decision.UNKNOWN]

    def stats(sub: Sequence[tuple[str, Decision, Decision | None, str]]) -> dict[str, float | None]:
        n = len(sub)
        if n == 0:
            return {
                "accuracy": None,
                "macro_f1": None,
                "coverage": None,
                "selective_accuracy": None,
                "failure_rate": None,
            }
        failed = [r for r in sub if r[2] is None]
        ok = [(g, p) for _, g, p, _ in sub if p is not None]
        # A failure is a miss for its gold class (like UNKNOWN in F1), never a valid decision.
        base = decision_metrics([(g, Decision.UNKNOWN if p is None else p) for _, g, p, _ in sub])
        correct = sum(g is p for _, g, p, _ in sub)
        covered = [(g, p) for g, p in ok if p is not Decision.UNKNOWN]
        return {
            "accuracy": correct / n,
            "macro_f1": base["macro_f1"],
            "coverage": len(covered) / n,
            "selective_accuracy": (sum(g is p for g, p in covered) / len(covered))
            if covered
            else None,
            "failure_rate": len(failed) / n,
        }

    point = stats(rows)
    groups: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        groups.setdefault(r[0], []).append(i)
    keys = sorted(groups)
    rng = random.Random(seed)
    boots: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_boot if keys else 0):
        idx = [i for _ in keys for i in groups[keys[rng.randrange(len(keys))]]]
        st = stats([rows[i] for i in idx])
        for k, v in st.items():
            if v is not None:
                boots[k].append(v)
    ci = {
        k: ([_percentile(sorted(v), 0.025), _percentile(sorted(v), 0.975)] if v else None)
        for k, v in boots.items()
    }
    statuses: dict[str, int] = {}
    for r in rows:
        statuses[r[3]] = statuses.get(r[3], 0) + 1
    return {
        "n_passages": len(rows),
        "n_questions": len(keys),
        **point,
        "ci95_cluster": ci,
        "status_counts": dict(sorted(statuses.items())),
        "excluded_gold_unknown": len(items) - len(rows),
    }
