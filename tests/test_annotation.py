"""Annotation tooling on synthetic records (no real data)."""

from __future__ import annotations

from dataclasses import fields

import pytest

from kgrerank.annotation.adjudication import load_submission, merge_gold, prepare_sheet
from kgrerank.annotation.agreement import (
    agreement_report,
    cohen_kappa,
    krippendorff_alpha_two,
    masi_distance,
)
from kgrerank.annotation.export import gold_examples
from kgrerank.annotation.sampling import (
    choose_double,
    conflicts_frame,
    draw_conflicts,
    draw_twowiki,
    largest_remainder,
    sha256_text,
    sheet_order,
    twowiki_frame,
)
from kgrerank.annotation.schema import AnnotationItem, AnnotationRecord, record_problems
from kgrerank.schema import REASON_TYPES, Decision

CATS = {
    "outdated": "Conflict due to outdated information",
    "no_conflict": "No conflict",
    "complementary": "Complementary information",
    "misinformation": "Conflict due to misinformation",
}


def _conflicts(n_per_cat: int = 6, n_pass: int = 5) -> list[dict]:
    recs = []
    for key, cat in CATS.items():
        for q in range(n_per_cat):
            answer = "" if (key == "complementary" and q >= 2) else f"ans-{key}-{q}"
            results = [
                {
                    "title": f"t{j}",
                    "snippet": f"s{j}",
                    "short_text": f"{key} {q} passage {j}",
                    "url": "u",
                    "date": "2024-01-01",
                }
                for j in range(n_pass)
            ]
            results.append({"title": "dup", "snippet": "", "short_text": f"{key} {q} passage 0"})
            results.append({"title": "empty", "snippet": "", "short_text": ""})
            recs.append(
                {
                    "source": "toy",
                    "question": f"{key} question {q}?",
                    "conflict_type": cat,
                    "correct_answer": answer,
                    "search_results": results,
                }
            )
    return recs


def _twowiki(n: int = 12) -> list[dict]:
    types = ["compositional", "comparison", "inference"]
    recs = []
    for i in range(n):
        ctx = [[f"T{i}-{j}", [f"Sentence {i}.{j}."]] for j in range(10)]
        recs.append(
            {
                "_id": f"w{i:02d}",
                "type": types[i % 3],
                "question": f"Q{i}?",
                "context": ctx,
                "supporting_facts": [[f"T{i}-0", 0], [f"T{i}-1", 0]],
                "evidences": [],
                "answer": f"A{i}",
            }
        )
    return recs


def test_frames_eligibility_and_dedupe():
    frame = conflicts_frame(_conflicts())
    strata = [q.stratum for q in frame]
    assert strata.count("complementary") == 2  # only queries with a reference answer
    assert all(len(q.passages) == 5 for q in frame)  # duplicate and empty passages dropped
    w = twowiki_frame(_twowiki())
    assert sum(p.supporting for p in w[0].passages) == 2


def test_draws_are_deterministic_disjoint_and_sized():
    frame = conflicts_frame(_conflicts())
    pilot_spec = {
        "outdated": {"queries": 1, "per_query": 3},
        "complementary": {"queries": 1, "per_query": 2},
    }
    main_spec = {
        "no_conflict": {"queries": 2, "per_query": 3},
        "complementary": {"census": True, "per_query_cap": 4},
        "misinformation": {"census": True, "per_query_cap": 2},
        "outdated": {"fill": True, "per_query": 3},
    }
    pilot = draw_conflicts(frame, pilot_spec, "pilot", 7, "v1", set())
    used = {it.qid for it in pilot}
    main = draw_conflicts(frame, main_spec, "main", 7, "v1", used, total=30)
    assert len(main) == 30 and not ({it.qid for it in main} & used)
    by = {}
    for it in main:
        by[it.stratum] = by.get(it.stratum, 0) + 1
    assert by["conflicts:no_conflict"] == 6
    assert by["conflicts:complementary"] == 4  # census of the 1 remaining referenced query
    assert by["conflicts:misinformation"] == 12  # census: 6 queries x cap 2
    assert by["conflicts:outdated"] == 8  # fills up to the total
    again = draw_conflicts(frame, main_spec, "main", 7, "v1", used, total=30)
    assert [i.item_id for i in again] == [i.item_id for i in main]
    other = draw_conflicts(frame, main_spec, "main", 8, "v1", used, total=30)
    assert [i.item_id for i in other] != [i.item_id for i in main]


def test_twowiki_balance_and_double_subset():
    w = twowiki_frame(_twowiki(12))
    main = draw_twowiki(
        w, {"queries": 6, "per_query": 4, "supporting_per_query": 2}, "main", 3, "v1", set()
    )
    assert len(main) == 24
    sup = {(q.qid, p.pid) for q in w for p in q.passages if p.supporting}
    assert sum((it.qid, it.pid) in sup for it in main) == 12
    marked = choose_double(main, 10, 3)
    assert sum(i.double for i in marked) == 10
    assert largest_remainder({"a": 5, "b": 3, "c": 2}, 4) == {"a": 2, "b": 1, "c": 1}


def test_sheet_order_groups_questions():
    frame = conflicts_frame(_conflicts())
    items = draw_conflicts(
        frame, {"outdated": {"queries": 3, "per_query": 3}}, "main", 1, "v1", set()
    )
    order_a = sheet_order(items, 1, "main", "A1")
    order_b = sheet_order(items, 1, "main", "A2")
    qs = [it.qid for it in order_a]
    assert all(qs.index(q) + qs.count(q) - 1 == len(qs) - 1 - qs[::-1].index(q) for q in set(qs))
    assert [i.item_id for i in order_a] != [i.item_id for i in order_b]


def test_items_are_blinded():
    names = {f.name for f in fields(AnnotationItem)}
    assert not names & {"stratum", "is_gold", "supporting", "decision", "score", "prediction"}


def test_record_validation():
    ok = AnnotationRecord("i", "A1", "v0", "CONTRADICTING", ["temporal_scope"], "no", rationale="x")
    assert record_problems(ok) == ([], [])
    bad = AnnotationRecord("i", "A1", "v0", "IRRELEVANT", ["alias"], "yes")
    errs, _ = record_problems(bad)
    assert any("cannot support" in e for e in errs)
    unk = AnnotationRecord("i", "A1", "v0", "UNKNOWN", ["unknown"], "unclear")
    errs, warns = record_problems(unk)
    assert any("rationale" in e for e in errs) and any("reason_note" in w for w in warns)


def test_agreement_hand_values():
    assert cohen_kappa(list("CCXIUC"), list("CXXICC")) == pytest.approx(0.5)
    a = [frozenset({"alias"}), frozenset({"alias", "temporal_scope"}), frozenset()]
    b = [frozenset({"alias"}), frozenset({"alias"}), frozenset({"homonym"})]
    assert krippendorff_alpha_two(a, b, masi_distance) == pytest.approx(48 / 198)
    assert masi_distance(frozenset(), frozenset()) == 0.0
    lab = [{"decision": d, "reasons": [], "answer_support": "no"} for d in "CCXIUC"]
    lab2 = [{"decision": d, "reasons": [], "answer_support": "no"} for d in "CXXICC"]
    rep = agreement_report(
        list(zip(lab, lab2, strict=True)),
        list("aabbcc"),
        list("CXIU"),
        REASON_TYPES,
        n_boot=50,
        seed=1,
    )
    assert rep["decision"]["cohen_kappa"] == pytest.approx(0.5)
    assert rep["reasons"]["per_reason_binary"]["alias"]["kappa"] is None  # never used


def _rec(iid, ann, d, reasons=(), sup="no", rat="r"):
    return AnnotationRecord(iid, ann, "v1", d, list(reasons), sup, rationale=rat)


def test_adjudication_keeps_pre_labels():
    items = {i: AnnotationItem(i, "q", "a", "", "", "t") for i in ("x", "y", "z")}
    a1 = {
        "x": _rec("x", "A1", "COMPATIBLE", ["alias"], "yes"),
        "y": _rec("y", "A1", "UNKNOWN"),
        "z": _rec("z", "A1", "IRRELEVANT"),
    }
    a2 = {
        "x": _rec("x", "A2", "COMPATIBLE", ["alias"], "yes"),
        "y": _rec("y", "A2", "CONTRADICTING"),
    }
    agreed, rows = prepare_sheet(a1, a2, items)
    assert agreed == ["x"] and [r["item_id"] for r in rows] == ["y"]
    gold, errors = merge_gold(a1, a2, [], "v1")
    assert errors and "without an adjudicated row" in errors[0]
    rows[0].update(
        final_decision="CONTRADICTING",
        final_reasons="temporal_scope",
        final_answer_support="no",
        adjudication_method="discussion",
        adjudicator="ADJ",
        note="older value stated as current",
    )
    gold, errors = merge_gold(a1, a2, rows, "v1")
    assert not errors
    g = {r["item_id"]: r for r in gold}
    assert g["y"]["pre_adjudication"]["A1"]["decision"] == "UNKNOWN"
    assert g["y"]["pre_adjudication"]["A2"]["decision"] == "CONTRADICTING"
    assert g["y"]["final"]["decision"] == "CONTRADICTING"
    assert g["z"]["adjudication"]["method"] == "single_annotator" and not g["z"]["double_annotated"]
    _, errs, _ = load_submission([{"item_id": "x", "decision": "maybe"}], "A1", "v1", {"x", "w"})
    assert any("decision must be" in e for e in errs) and any("not annotated" in e for e in errs)


def test_export_to_schema_v1():
    recs = _conflicts(2, 3)
    frame = conflicts_frame(recs)
    q = frame[0]
    p = q.passages[1]
    key = {"it1": {"source": "conflicts", "qid": q.qid, "pid": p.pid, "text_sha256": p.text_sha256}}
    gold = [
        {
            "item_id": "it1",
            "codebook_version": "v1",
            "double_annotated": False,
            "final": {
                "decision": "COMPATIBLE",
                "reasons": ["temporal_scope"],
                "answer_support": "yes",
            },
            "adjudication": {"method": "single_annotator"},
        }
    ]
    (ex,) = gold_examples(gold, key, recs, [])
    lab = ex.candidate(p.pid)
    assert lab.decision is Decision.COMPATIBLE and lab.is_gold and lab.label_source == "manual"
    others = [c for c in ex.candidates if c.pid != p.pid]
    assert all(c.decision is Decision.UNKNOWN and c.label_source == "unlabelled" for c in others)
    key["it1"]["text_sha256"] = sha256_text("something else")
    with pytest.raises(ValueError, match="differs"):
        gold_examples(gold, key, recs, [])
