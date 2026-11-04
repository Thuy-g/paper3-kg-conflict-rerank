"""Metrics for methods that output a decision per passage (docs/PLAN.md B.5).

Gold UNKNOWN passages are excluded. A predicted UNKNOWN counts as abstention: it lowers coverage
and is excluded from selective accuracy, but counts as wrong in plain accuracy and macro-F1.
"""

from __future__ import annotations

from collections.abc import Sequence

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
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return {
        "n": n,
        "accuracy": correct / n,
        "macro_f1": sum(f1s) / len(f1s),
        "coverage": len(covered) / n,
        "selective_accuracy": (sum(g is p for g, p in covered) / len(covered)) if covered else None,
        "confusion": confusion,
    }
