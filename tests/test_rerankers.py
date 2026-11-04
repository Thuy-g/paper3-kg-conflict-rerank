from __future__ import annotations

import pytest

from kgrerank.llm.mock import MockLLM
from kgrerank.metrics.conflict import conflict_metrics
from kgrerank.perturb.operators import OPERATORS, apply_operators
from kgrerank.rerankers.base import Ranking, check_ranking
from kgrerank.rerankers.bm25 import BM25Reranker, bm25_scores
from kgrerank.rerankers.llm_judge import LLMJudgeFilter, parse_decision
from kgrerank.rerankers.simple import IdentityReranker, OracleReranker, RandomReranker
from kgrerank.schema import Candidate, Decision, Example


def _ex(texts: dict[str, str], q: str = "red apple") -> Example:
    return Example(
        "q",
        q,
        ["x"],
        [Candidate(p, "", t) for p, t in texts.items()],
        {"source": "t", "synthetic": True},
    )


def test_bm25_hand_computed():
    s = bm25_scores("red apple", {"d1": "red apple", "d2": "green apple", "d3": "red car red"})
    assert s["d1"] == pytest.approx(1.0045879098, abs=1e-9)
    assert s["d2"] == pytest.approx(0.5022939549, abs=1e-9)
    assert s["d3"] == pytest.approx(0.6149580196, abs=1e-9)
    r = BM25Reranker().rank(_ex({"d1": "red apple", "d2": "green apple", "d3": "red car red"}))
    assert r.order == ("d1", "d3", "d2")


def test_bm25_tie_break_by_pid():
    r = BM25Reranker().rank(_ex({"b": "same text", "a": "same text", "c": "same text"}))
    assert r.order == ("a", "b", "c")


def test_random_seeded():
    ex = _ex({f"p{i}": "x" for i in range(8)})
    assert RandomReranker(1).rank(ex).order == RandomReranker(1).rank(ex).order
    assert RandomReranker(1).rank(ex).order != RandomReranker(2).rank(ex).order


def test_check_ranking_rejects_bad_partition():
    ex = _ex({"a": "x", "b": "y"})
    with pytest.raises(ValueError):
        check_ranking(ex, Ranking(order=("a",)))
    with pytest.raises(ValueError):
        check_ranking(ex, Ranking(order=("a", "b"), removed=frozenset({"a"})))


def test_oracles_hit_metric_extremes(toy_examples, toy_kg):
    examples = [apply_operators(ex, toy_kg, list(OPERATORS), 42)[0] for ex in toy_examples]
    ref_model = BM25Reranker()
    good = OracleReranker("drop_contradicting", base=ref_model)
    greedy = OracleReranker("drop_any_reason", base=ref_model)
    for ex in examples:
        ref = ref_model.rank(ex)
        g = conflict_metrics(ex, good.rank(ex), ref, [5])
        b = conflict_metrics(ex, greedy.rank(ex), ref, [5])
        if g["fcfr_paired@5"] is not None:
            assert g["fcfr_paired@5"] == 0.0 and b["fcfr_paired@5"] == 1.0
        if g["ger_paired@5"] is not None:
            assert g["ger_paired@5"] == 1.0
        assert g["wfr"] in (None, 0.0)


def test_llm_judge_with_mock(toy_examples):
    judge = LLMJudgeFilter(base=IdentityReranker(), backend=MockLLM(), top_m=2)
    r1 = judge.rank(toy_examples[0])
    r2 = LLMJudgeFilter(base=IdentityReranker(), backend=MockLLM(), top_m=2).rank(toy_examples[0])
    assert r1 == r2 and r1.llm_calls == 2
    check_ranking(toy_examples[0], r1)
    assert parse_decision(" contradicting.") is Decision.CONTRADICTING
    assert parse_decision("maybe") is Decision.UNKNOWN
    assert parse_decision("") is Decision.UNKNOWN
