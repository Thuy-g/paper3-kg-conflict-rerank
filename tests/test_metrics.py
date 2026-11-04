from __future__ import annotations

import pytest

from kgrerank.metrics.conflict import conflict_metrics
from kgrerank.metrics.decision import decision_metrics
from kgrerank.metrics.qa import exact_match, f1_score
from kgrerank.metrics.retrieval import mrr, ndcg_at_k, recall_at_k
from kgrerank.rerankers.base import Ranking
from kgrerank.schema import Candidate, Decision, Example

C, X, IR, U = Decision.COMPATIBLE, Decision.CONTRADICTING, Decision.IRRELEVANT, Decision.UNKNOWN


def test_retrieval_hand_values():
    order, gold = ["a", "b", "c", "d"], {"b", "d"}
    assert recall_at_k(order, gold, 1) == 0.0
    assert recall_at_k(order, gold, 2) == 0.5
    assert recall_at_k(order, gold, 4) == 1.0
    assert mrr(order, gold) == 0.5
    assert ndcg_at_k(order, gold, 2) == pytest.approx(0.3868528072, abs=1e-9)
    assert recall_at_k(order, set(), 3) is None and mrr(order, set()) is None


def test_qa():
    assert exact_match("The Eiffel Tower!", ["eiffel tower"]) == 1.0
    assert f1_score("big red apple", ["red apple"]) == pytest.approx(0.8)
    assert exact_match("x", []) is None


def test_conflict_metrics_hand_values():
    cands = [
        Candidate("g", "", "", True, C, [], "manual"),
        Candidate("a1", "", "", False, C, ["alias"], "manual"),
        Candidate("a2", "", "", False, C, ["temporal_scope"], "manual"),
        Candidate("n1", "", "", False, X, ["counterfactual"], "manual"),
        Candidate("d", "", ""),
    ]
    ex = Example("q", "?", ["x"], cands, {"source": "t", "synthetic": True})
    ref = Ranking(order=("g", "a1", "n1", "a2", "d"))
    method = Ranking(order=("g", "d", "a2", "n1"), removed=frozenset({"a1"}))
    m = conflict_metrics(ex, method, ref, [3], reasons=["alias", "temporal_scope"])
    assert m["fcfr_paired@3"] == 1.0  # a1 was in the reference top-3 and is gone
    assert m["fcfr_abs@3"] == 0.5
    assert m["fcfr_filter"] == 0.5
    assert m["ger_paired@3"] == 1.0 and m["ger_abs@3"] == 1.0
    assert m["wfr"] == 1.0
    assert m["fcfr_paired@3[alias]"] == 1.0
    assert m["fcfr_paired@3[temporal_scope]"] is None  # a2 was not in the reference top-3


def test_decision_metrics_hand_values():
    pairs = [(C, C), (C, U), (X, X), (X, C), (IR, IR), (U, X)]
    m = decision_metrics(pairs)
    assert m["n"] == 5  # gold UNKNOWN excluded
    assert m["accuracy"] == pytest.approx(3 / 5)
    assert m["coverage"] == pytest.approx(4 / 5)
    assert m["selective_accuracy"] == pytest.approx(3 / 4)
    # per class F1: C: tp1 fp1 fn1 -> 0.5; X: tp1 fp0 fn1 -> 2/3; I: 1.0
    assert m["macro_f1"] == pytest.approx((0.5 + 2 / 3 + 1.0) / 3)
    assert decision_metrics([(U, C)])["accuracy"] is None
