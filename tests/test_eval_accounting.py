"""Evaluation accounting: unjudged passages, condensed metrics, WFR variants, typing report."""

from __future__ import annotations

from pathlib import Path

import pytest

from kgrerank.metrics.conflict import wfr_compat_v1, wfr_support_v1
from kgrerank.metrics.decision import typing_report
from kgrerank.pipeline import decision_counts, per_query_metrics
from kgrerank.rerankers.base import Ranking
from kgrerank.schema import Candidate, Decision, Evidence, Example

C, X, U = Decision.COMPATIBLE, Decision.CONTRADICTING, Decision.UNKNOWN
FIXTURES = Path(__file__).parent / "fixtures"


def _ann(support: str) -> list[Evidence]:
    return [Evidence("note", "annotation:it_x", {"answer_support": support})]


def _example(judged: list[str] | None) -> Example:
    cands = [
        Candidate("a", "", "", False, U),  # unjudged
        Candidate("b", "", "", True, C, [], "manual", _ann("yes")),
        Candidate("c", "", "", False, C, ["temporal_scope"], "manual", _ann("no")),
        Candidate("d", "", "", False, U, [], "manual", _ann("unclear")),  # human UNKNOWN
    ]
    meta = {"source": "t", "synthetic": True}
    if judged is not None:
        meta["relevance_judged_pids"] = judged
    return Example("q", "?", ["x"], cands, meta)


def test_unjudged_passages_are_not_negatives():
    ex = _example(["b", "c", "d"])
    r = Ranking(order=("a", "b", "c", "d"))
    row = per_query_metrics([ex], {"q": r}, {"q": r}, [1], [])["q"]
    assert row["recall@1"] is None and row["mrr"] is None  # judgments incomplete: not reported
    assert row["recall@1_cond"] == 1.0 and row["mrr_cond"] == 1.0  # 'a' removed, 'b' first
    full = per_query_metrics([_example(None)], {"q": r}, {"q": r}, [1], [])["q"]
    assert full["recall@1"] == 0.0 and full["mrr"] == 0.5


def test_label_source_counts_separate_unjudged_from_human_unknown():
    counts = decision_counts([_example(None)])
    assert counts["unlabelled"]["UNKNOWN"] == 1 and counts["manual"]["UNKNOWN"] == 1


def test_wfr_variants():
    ex = _example(None)
    removed_c = Ranking(order=("a", "b", "d"), removed=frozenset({"c"}))
    assert wfr_compat_v1(ex, removed_c) == 1.0  # c is COMPATIBLE
    assert wfr_support_v1(ex, removed_c) == 0.0  # c does not support the answer
    removed_b = Ranking(order=("a", "c", "d"), removed=frozenset({"b"}))
    assert wfr_support_v1(ex, removed_b) == 1.0


def test_typing_report_counts_failures_and_clusters_by_question():
    items = [
        ("q1", C, C, "kg"),
        ("q1", X, None, "fallback_parse_error"),
        ("q1", U, C, "kg"),
        ("q2", C, U, "kg"),
        ("q2", X, X, "fallback_ok"),
        ("q3", C, C, "kg"),
    ]
    rep = typing_report(items, n_boot=200, seed=1)
    assert rep["n_passages"] == 5 and rep["n_questions"] == 3 and rep["excluded_gold_unknown"] == 1
    assert rep["failure_rate"] == pytest.approx(1 / 5)
    assert rep["accuracy"] == pytest.approx(3 / 5)  # the failure counts as wrong, not abstention
    assert rep["coverage"] == pytest.approx(3 / 5)  # predicted UNKNOWN and failure not covered
    # Macro-F1 uses the same 5 passages: the failure is a miss for CONTRADICTING; IRRELEVANT is
    # absent from gold and prediction, so it is not averaged. C: P=1, R=2/3; X: P=1, R=1/2.
    assert rep["macro_f1"] == pytest.approx((0.8 + 2 / 3) / 2)
    lo, hi = rep["ci95_cluster"]["accuracy"]
    assert 0.0 <= lo <= rep["accuracy"] <= hi <= 1.0
    assert rep["status_counts"]["fallback_parse_error"] == 1


def test_macro_f1_skips_classes_absent_from_gold_and_prediction():
    from kgrerank.metrics.decision import decision_metrics

    m = decision_metrics([(C, C), (X, C)])
    # C: P=1/2, R=1 -> 2/3; X: R=0 -> 0; IRRELEVANT absent -> not averaged.
    assert m["macro_f1"] == pytest.approx((2 / 3 + 0.0) / 2)


def test_g2plus_reads_resolved_frames_path_and_records_config_value(tmp_path):
    from kgrerank.annotation.schema import write_jsonl
    from kgrerank.frames.schema import InferenceFrame
    from kgrerank.pipeline import build_reranker, information_access

    path = tmp_path / "frames_pilot.jsonl"
    write_jsonl(path, [InferenceFrame("q1", "Where was X born?").to_dict()])
    spec = {
        "name": "g2plus:S2",
        "type": "g2plus",
        "kg_view": str(FIXTURES / "toy_kg.json"),
        "frames": "data/frames/v1/frames_pilot.jsonl",  # relative config value, not read
        "frames_path": str(path),
    }
    rr = build_reranker(spec, 0, None)
    assert set(rr.frames) == {"q1"} and not rr.frames["q1"].supported
    assert information_access(spec)["frames"] == "data/frames/v1/frames_pilot.jsonl"
