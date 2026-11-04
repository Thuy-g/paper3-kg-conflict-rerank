"""Label protocol v0: per operator, one case with full evidence and one that must be UNKNOWN."""

from __future__ import annotations

import copy

from conftest import PickRNG

from kgrerank.kg.time import Interval, year_range
from kgrerank.kg.view import KGView
from kgrerank.perturb.operators import (
    QuestionFrame,
    alias,
    apply_operators,
    counterfactual,
    granularity,
    historical_name,
    homonym,
    inverse,
    predicate,
    temporal,
)
from kgrerank.schema import Decision, validate_example

Q1 = QuestionFrame("Z1", "P19", ("Z3",), fact_time=Interval.point(year_range(1950)))
Q2 = QuestionFrame("Z3", "P6", ("Z10",), time_anchor=Interval.point(year_range(2010)))
Q3 = QuestionFrame("Z1", "P22", ("Z14",))


def _unmet(res):
    return list(res.unmet)


def test_counterfactual(toy_kg):
    res = counterfactual(toy_kg, Q2, PickRNG(lambda e: e == "Z16"), "q", 0)
    assert res.candidate.decision is Decision.CONTRADICTING and not res.unmet
    assert res.candidate.text.startswith("In 2010,")  # anchored to the question's time
    # Without a time anchor, (Z3, P6) has three non-deprecated values: no single answer in scope.
    loose = QuestionFrame("Z3", "P6", ("Z10",))
    res2 = counterfactual(toy_kg, loose, PickRNG(), "q", 0)
    assert res2.candidate.decision is Decision.UNKNOWN
    assert "not exactly 1" in _unmet(res2)[0]
    assert res2.candidate.reasons == res.candidate.reasons == ["counterfactual"]


def test_counterfactual_excludes_kg_values_and_aliases(toy_kg):
    seen = set()
    for seed in range(30):
        import random

        res = counterfactual(toy_kg, Q1, random.Random(seed), "q", 0)
        seen.add(res.candidate.text.rsplit(" ", 1)[-1].rstrip("."))
    assert "Avalon" not in seen and "City" not in seen  # never the gold value or its alias
    assert seen <= {"Northgate", "Lowmarsh"}


def test_alias(toy_kg, toy_kg_dict):
    res = alias(toy_kg, Q1, PickRNG(), "q", 0)
    assert res.candidate.decision is Decision.COMPATIBLE and "Avalon City" in res.candidate.text
    d = copy.deepcopy(toy_kg_dict)
    d["entities"]["Z7"]["aliases"] = ["Avalon City"]  # alias now ambiguous in the view
    res2 = alias(KGView.from_dict(d), Q1, PickRNG(), "q", 0)
    assert res2.candidate.decision is Decision.UNKNOWN and "shared" in _unmet(res2)[0]


def test_historical_name(toy_kg):
    res = historical_name(toy_kg, Q1, PickRNG(), "q", 0)
    assert res.candidate.decision is Decision.COMPATIBLE
    assert "from 1800 to 1902" in res.candidate.text
    name_q = QuestionFrame("Z1", "P1448", ("Z3",))  # asks about a name
    res2 = historical_name(toy_kg, name_q, PickRNG(), "q", 0)
    assert res2.candidate.decision is Decision.UNKNOWN


def test_temporal_requires_stated_period_and_disjoint_time(toy_kg):
    teo = PickRNG(lambda st: st.value.value == "Z11")
    stated = temporal(toy_kg, Q2, teo, "q", 0)
    unstated = temporal(toy_kg, Q2, teo, "q", 0, state_interval=False)
    assert stated.candidate.reasons == unstated.candidate.reasons == ["temporal_scope"]
    assert stated.candidate.decision is Decision.COMPATIBLE
    assert unstated.candidate.decision is Decision.UNKNOWN  # same reason, different evidence
    in_1995 = QuestionFrame("Z3", "P6", ("Z10",), time_anchor=Interval.point(year_range(1995)))
    ivo = temporal(toy_kg, in_1995, PickRNG(lambda st: st.value.value == "Z12"), "q", 0)
    assert ivo.candidate.decision is Decision.UNKNOWN  # Ivo also held office in 1995


def test_granularity_time_qualified_edges(toy_kg):
    res = granularity(toy_kg, Q1, PickRNG(lambda a: a == "Z6"), "q", 0)
    assert res.candidate.decision is Decision.COMPATIBLE
    assert any(ev.ref == "assumption" for ev in res.candidate.evidence)
    lowmarsh = PickRNG(lambda a: a == "Z5")
    unknown_time = QuestionFrame("Z1", "P19", ("Z7",))
    assert (
        granularity(toy_kg, unknown_time, lowmarsh, "q", 0).candidate.decision is Decision.UNKNOWN
    )
    in_1975 = QuestionFrame("Z1", "P19", ("Z7",), fact_time=Interval.point(year_range(1975)))
    assert granularity(toy_kg, in_1975, lowmarsh, "q", 0).candidate.decision is Decision.COMPATIBLE
    in_2000 = QuestionFrame("Z1", "P19", ("Z7",), fact_time=Interval.point(year_range(2000)))
    assert granularity(toy_kg, in_2000, lowmarsh, "q", 0).candidate.decision is Decision.UNKNOWN


def test_predicate(toy_kg, toy_kg_dict):
    res = predicate(toy_kg, Q1, PickRNG(), "q", 0)
    assert res.candidate.decision is Decision.COMPATIBLE and "place of death" in res.candidate.text
    d = copy.deepcopy(toy_kg_dict)
    del d["properties"]["P19"], d["properties"]["P20"]
    res2 = predicate(KGView.from_dict(d), Q1, PickRNG(), "q", 0)
    assert res2.candidate.decision is Decision.UNKNOWN  # relation semantics unknown


def test_inverse(toy_kg, toy_kg_dict):
    res = inverse(toy_kg, Q3, PickRNG(), "q", 0)
    assert res.candidate.decision is Decision.COMPATIBLE
    assert res.candidate.text == "The child of Oren Verdan is Alma Verdan."
    d = copy.deepcopy(toy_kg_dict)
    d["statements"] = [s for s in d["statements"] if not (s["s"] == "Z1" and s["p"] == "P22")]
    res2 = inverse(KGView.from_dict(d), Q3, PickRNG(), "q", 0)
    assert res2.candidate.decision is Decision.UNKNOWN


def test_homonym_needs_type_evidence(toy_kg):
    town = homonym(toy_kg, Q2, PickRNG(lambda o: o[0] == "Z9"), "q", 0)
    assert town.candidate.decision is Decision.IRRELEVANT
    assert town.candidate.reasons == ["homonym", "entity_identity_mismatch"]
    city = homonym(toy_kg, Q2, PickRNG(lambda o: o[0] == "Z17"), "q", 0)
    assert city.candidate.decision is Decision.UNKNOWN  # both are cities: no type evidence
    assert "share P31" in city.unmet[0]


def test_apply_operators_deterministic(toy_examples, toy_kg):
    ops = ["counterfactual", "alias", "temporal", "granularity", "homonym"]
    a, _ = apply_operators(toy_examples[1], toy_kg, ops, seed=42)
    b, _ = apply_operators(toy_examples[1], toy_kg, list(reversed(ops)), seed=42)
    ta = {c.pid: c.text for c in a.candidates}
    assert ta == {c.pid: c.text for c in b.candidates}  # independent of operator order
    texts = {
        tuple(c.text for c in apply_operators(toy_examples[1], toy_kg, ops, seed=s)[0].candidates)
        for s in range(10)
    }
    assert len(texts) > 1  # different seeds give different perturbations
    validate_example(a)
    dropped, _ = apply_operators(
        toy_examples[1], toy_kg, ["temporal_unstated"], 42, drop_unknown=True
    )
    assert len(dropped.candidates) == len(toy_examples[1].candidates)


def test_no_frame_no_perturbation(toy_examples, toy_kg):
    ex = toy_examples[3]  # no KG frame
    new, results = apply_operators(ex, toy_kg, ["counterfactual"], 42)
    assert new is ex and results == []
