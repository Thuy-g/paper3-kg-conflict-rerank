from __future__ import annotations

import pytest

from kgrerank.schema import (
    Candidate,
    Decision,
    Evidence,
    Example,
    SchemaError,
    read_jsonl,
    validate_example,
    write_jsonl,
)


def _ex(*cands: Candidate) -> Example:
    return Example("q", "question?", ["a"], list(cands), {"source": "t", "synthetic": True})


def test_fixture_roundtrip(toy_examples, tmp_path):
    out = tmp_path / "x.jsonl"
    write_jsonl(out, toy_examples)
    again = read_jsonl(out)
    assert again == toy_examples
    assert all(ex.meta["synthetic"] is True for ex in again)


def test_gold_cannot_contradict():
    c = Candidate(
        "p", "", "t", is_gold=True, decision=Decision.CONTRADICTING, label_source="manual"
    )
    with pytest.raises(SchemaError, match="gold passage cannot be CONTRADICTING"):
        validate_example(_ex(c))


@pytest.mark.parametrize(
    ("cand", "msg"),
    [
        (Candidate("p", "", "t", reasons=["alias", "alias"]), "duplicated reason"),
        (Candidate("p", "", "t", reasons=["synonym"]), "unknown reason"),
        (Candidate("p", "", "t", decision=Decision.IRRELEVANT), "unlabelled passages must"),
        (
            Candidate(
                "p", "", "t", decision=Decision.COMPATIBLE, label_source="perturbation_rule_v0"
            ),
            "must carry evidence",
        ),
        (Candidate("p", "", "t", label_source="crowd"), "unknown label_source"),
        (
            Candidate("p", "", "t", label_source="manual", evidence=[Evidence("blog", "x")]),
            "unknown evidence kind",
        ),
    ],
)
def test_invalid_candidates(cand, msg):
    with pytest.raises(SchemaError, match=msg):
        validate_example(_ex(cand))


def test_duplicate_pids_and_meta():
    a = Candidate("p", "", "t")
    with pytest.raises(SchemaError, match="unique"):
        validate_example(_ex(a, Candidate("p", "", "u")))
    bad = Example("q", "?", ["a"], [a], {"source": "t"})
    with pytest.raises(SchemaError, match="synthetic"):
        validate_example(bad)


def test_reason_does_not_fix_decision():
    # The schema accepts the same reason with any decision: decisions come from evidence.
    for d in Decision:
        src = "unlabelled" if d is Decision.UNKNOWN else "manual"
        validate_example(
            _ex(Candidate("p", "", "t", decision=d, reasons=["homonym"], label_source=src))
        )
