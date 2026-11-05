"""Converters on tiny hand-written records that mimic each source format (synthetic)."""

from __future__ import annotations

from kgrerank.data.conflicts import convert_conflicts
from kgrerank.data.ragability import convert_ragability
from kgrerank.data.twowiki import convert_2wiki
from kgrerank.schema import Decision, validate_example

TWOWIKI = {
    "_id": "x1",
    "type": "compositional",
    "question": "Where was the father of A born?",
    "context": [
        ["A", ["A is a person.", "A's father is B."]],
        ["B", ["B was born in C."]],
        ["D", ["D is unrelated."]],
    ],
    "supporting_facts": [["A", 1], ["B", 0]],
    "evidences": [["A", "father", "B"], ["B", "place of birth", "C"]],
    "answer": "C",
}
CONFLICTS = {
    "source": "toy",
    "question": "who is x",
    "conflict_type": "Conflict due to outdated information",
    "correct_answer": " ",
    "search_results": [
        {
            "title": "T1",
            "snippet": "s1",
            "short_text": "long text 1",
            "url": "u1",
            "date": "d1",
            "response_str": "page",
        },
        {
            "title": "T2",
            "snippet": "s2",
            "short_text": "",
            "url": "u2",
            "date": None,
            "response_str": "page",
        },
    ],
}
RAGABILITY = {
    "contradiction_ID": 7,
    "WikiContradict_ID": 3.0,
    "query_text": "What is X?",
    "context_1": "X is A.",
    "context_2": "X is B.",
    "context_3_nc1_c2": "X is a kind of A.",
    "context_4_nc1_nc2_nc3": "X exists.",
    "answer_context1": "A",
    "answer_context2": "B",
    "c1xq": "qeu",
    "c2xq": "qn",
    "reasoning_required_c1c2": "categorical",
}


def test_2wiki_gold_and_unlabelled_distractors():
    ex = convert_2wiki(TWOWIKI)
    validate_example(ex)
    by_title = {c.title: c for c in ex.candidates}
    assert by_title["A"].is_gold and by_title["A"].decision is Decision.COMPATIBLE
    assert by_title["D"].decision is Decision.UNKNOWN and by_title["D"].label_source == "unlabelled"
    assert ex.meta["kg_derived"] is True and ex.answers == ["C"]


def test_conflicts_query_level_labels_only():
    ex = convert_conflicts(CONFLICTS, 5)
    validate_example(ex)
    assert ex.qid == "conflicts-5" and ex.answers == []
    assert [c.text for c in ex.candidates] == ["long text 1", "s2"]  # falls back to the snippet
    assert all(c.decision is Decision.UNKNOWN for c in ex.candidates)
    assert ex.meta["conflict_category"] == "Conflict due to outdated information"


def test_ragability_relative_labels():
    ex = convert_ragability(RAGABILITY, 0)
    validate_example(ex)
    d = {c.pid: c for c in ex.candidates}
    assert d["c1"].decision is Decision.COMPATIBLE and d["c1"].is_gold
    assert d["c2"].decision is Decision.UNKNOWN  # c2xq == qn: no information for the query
    assert d["c3"].decision is Decision.COMPATIBLE and d["c4"].decision is Decision.COMPATIBLE
    flipped = convert_ragability({**RAGABILITY, "c2xq": "qeu"}, 0, reference="context_2")
    f = {c.pid: c for c in flipped.candidates}
    assert f["c2"].decision is Decision.COMPATIBLE and f["c1"].decision is Decision.CONTRADICTING
    assert f["c3"].decision is Decision.CONTRADICTING  # c3 contradicts context_2
    assert flipped.answers == ["B"] and flipped.meta["reference"] == "context_2"
