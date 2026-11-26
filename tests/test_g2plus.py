"""G2+ skeleton (policy v0.2) on the hand-written fictional KG; no real data, no network.

In the fixture "Port Avalon" names four entities (Z3 city, Z8 yacht, Z9 town, Z17 city), so a bare
"Port Avalon" in a passage must stay unresolved; "Avalon City" is a unique alias of Z3.
"""

from __future__ import annotations

import copy

import pytest

from kgrerank.conflict.policy import CONFIDENCE, POLICY_VERSION
from kgrerank.conflict.reranker import ConflictAwareReranker
from kgrerank.conflict.typer import G2PlusTyper
from kgrerank.extract.linker import EntityLinker
from kgrerank.extract.pattern import PatternExtractor
from kgrerank.frames.schema import InferenceFrame
from kgrerank.kg.settings import restrict
from kgrerank.kg.time import year_period
from kgrerank.kg.view import KGView
from kgrerank.llm.base import Completion
from kgrerank.llm.mock import MockLLM
from kgrerank.rerankers.llm_judge import LLMTyper
from kgrerank.rerankers.simple import IdentityReranker
from kgrerank.schema import Candidate, Decision, Example


def frame(subject, prop, year=None, qtype="single_fact") -> InferenceFrame:
    return InferenceFrame(
        qid="q",
        question="?",
        subject=subject,
        subject_status="given",
        prop=prop,
        prop_status="given",
        time_anchor=year_period(year) if year else None,
        time_status="given",
        question_type=qtype,
        source="test",
    )


P19 = frame("Z1", "P19")
P6_2010 = frame("Z3", "P6", 2010)
P22 = frame("Z1", "P22")


def _ex(texts: list[str]) -> Example:
    return Example(
        "q",
        "?",
        ["x"],
        [Candidate(f"p{i}", "", t) for i, t in enumerate(texts)],
        {"source": "t", "synthetic": True},
    )


def _typer(kg: KGView, setting: str, fallback=None) -> G2PlusTyper:
    return G2PlusTyper(
        kg, setting, PatternExtractor([p.label for p in kg.properties.values()]), fallback
    )


def _types(kg, setting, texts, fr, fallback=None):
    ex = _ex(texts)
    out = _typer(kg, setting, fallback).type_example(ex, fr, [c.pid for c in ex.candidates])
    return {t.pid: t for t in out}


def test_no_gold_in_inference_frames():
    assert not hasattr(P19, "gold")
    assert "gold" not in InferenceFrame.__dataclass_fields__


def test_settings_restrict_and_mask(toy_kg):
    assert not restrict(toy_kg, "S0").properties
    s1 = restrict(toy_kg, "S1")
    assert s1.properties and not s1.statements and not s1.entities
    s2 = restrict(toy_kg, "S2", mask=("Z1", "P19"))
    assert not s2.statements_of("Z1", "P19")
    assert s2.statements_of("Z3", "P131") and not s2.statements_of("Z3", "P6")
    with pytest.raises(ValueError):
        restrict(toy_kg, "S4")


def test_linker_keeps_ambiguity(toy_kg):
    lk = EntityLinker(toy_kg)
    assert lk.link("Avalon City").eid == "Z3" and lk.link("Kingsbridge").via == "name_statement"
    assert lk.link("Port Avalon").status == "ambiguous" and lk.link("Port Avalon").eid is None
    assert lk.link("Port Avalon", "fictional town in Lake County").eid == "Z9"


def test_ambiguous_subject_is_never_resolved_to_the_question_entity(toy_kg):
    t = _types(
        toy_kg, "S3", ["In 2010, the head of government of Port Avalon was Bram Ostler."], P6_2010
    )
    assert t["p0"].decision is Decision.UNKNOWN and t["p0"].rule == "R-subject-unknown"


def test_identity_and_hierarchy(toy_kg):
    t = _types(
        toy_kg,
        "S3",
        [
            "The place of birth of Alma Verdan is Avalon City.",
            "The place of birth of Alma Verdan is Kingsbridge.",
            "The place of birth of Alma Verdan is Republic of Merrow.",
        ],
        P19,
    )
    assert t["p0"].reasons == ("alias",) and t["p1"].reasons == ("historical_identity",)
    assert t["p2"].rule == "R-hierarchy-coarser"
    assert all(x.decision is Decision.COMPATIBLE and x.status == "kg" for x in t.values())


def test_temporal_scope_and_missing_dates(toy_kg):
    t = _types(
        toy_kg,
        "S3",
        [
            "From 2012, the head of government of Avalon City was Teo Brandt.",
            "The head of government of Avalon City is Ivo Sallis.",
        ],
        P6_2010,
    )
    assert t["p0"].decision is Decision.COMPATIBLE and t["p0"].rule == "R-time-disjoint"
    assert t["p1"].decision is Decision.UNKNOWN and t["p1"].rule == "R-time-unknown"


def test_homonym_and_predicate(toy_kg):
    t = _types(
        toy_kg,
        "S3",
        [
            "Port Avalon (fictional town in Lake County): "
            "the head of government of Port Avalon is Rosa Fein.",
            "The head of state of Avalon City is Gil Moray.",
        ],
        P6_2010,
    )
    assert t["p0"].decision is Decision.IRRELEVANT and t["p0"].reasons == ("homonym",)
    assert t["p1"].decision is Decision.IRRELEVANT and t["p1"].reasons == ("predicate_mismatch",)


def test_inverse(toy_kg):
    t = _types(toy_kg, "S3", ["The child of Oren Verdan is Alma Verdan."], P22)
    assert t["p0"].decision is Decision.COMPATIBLE and "inverse_relation" in t["p0"].reasons


def test_single_value_stable_property_gives_soft_conflict(toy_kg):
    v = _types(toy_kg, "S3", ["The place of birth of Alma Verdan is Lowmarsh."], P19)["p0"]
    assert v.decision is Decision.CONTRADICTING and v.rule == "R-single-value"
    assert v.confidence == CONFIDENCE["single_value_other"] < 1 and v.policy == POLICY_VERSION


def test_single_best_value_is_not_exclusive(toy_kg):
    t = _types(
        toy_kg, "S3", ["In 2010, the head of government of Avalon City was Bram Ostler."], P6_2010
    )
    assert t["p0"].decision is Decision.UNKNOWN and t["p0"].rule == "R-sbv-not-exclusive"


@pytest.mark.parametrize(
    ("change", "rule"),
    [
        (lambda c: c.update(separators=["P3831"]), "R-separator-uncertain"),
        (lambda c: c.update(exceptions=["Z1"]), "R-exception"),
        (lambda c: c.update(statement_rank="deprecated"), "R-cardinality-open"),
    ],
)
def test_constraint_details_block_conflicts(toy_kg_dict, change, rule):
    d = copy.deepcopy(toy_kg_dict)
    change(d["properties"]["P19"]["constraints"][0])
    t = _types(KGView.from_dict(d), "S3", ["The place of birth of Alma Verdan is Lowmarsh."], P19)
    assert t["p0"].decision is Decision.UNKNOWN and t["p0"].rule == rule


def test_missing_dates_need_a_stable_property(toy_kg_dict):
    d = copy.deepcopy(toy_kg_dict)
    d["properties"]["P19"]["mutability"] = None  # not annotated stable any more
    t = _types(KGView.from_dict(d), "S3", ["The place of birth of Alma Verdan is Lowmarsh."], P19)
    assert t["p0"].decision is Decision.UNKNOWN and t["p0"].rule == "R-time-unknown"
    t2 = _types(
        KGView.from_dict(toy_kg_dict), "S3", ["The father of Alma Verdan is Bram Ostler."], P22
    )
    assert t2["p0"].decision is Decision.UNKNOWN  # P22: no mutability, no cardinality


def test_unsupported_frames_go_to_fallback(toy_kg):
    for fr in (
        frame("Z1", "P19", qtype="multi_hop"),
        InferenceFrame(
            qid="q",
            question="?",
            subject=None,
            subject_status="ambiguous",
            prop="P19",
            prop_status="linked",
            time_status="none",
            question_type="single_fact",
        ),
        None,
    ):
        t = _types(toy_kg, "S3", ["The place of birth of Alma Verdan is Lowmarsh."], fr)
        assert t["p0"].decision is Decision.UNKNOWN and t["p0"].rule == "R-frame-unsupported"
        assert t["p0"].status == "undecided"


def test_fallback_statuses_and_usage(toy_kg):
    def typer_with(completion):
        fb = LLMTyper(MockLLM(responder=lambda m: completion), role="fallback")
        return _typer(toy_kg, "S3", fb)

    ex = _ex(["The head of government of Avalon City is Ivo Sallis.", "Unparseable sentence."])
    ok = typer_with(Completion('{"decision": "COMPATIBLE"}', "stop"))
    out = ok.type_example(ex, P6_2010, ["p0", "p1"])
    assert [t.status for t in out] == ["fallback_ok", "fallback_ok"]
    assert ok.last_usage["calls"] == 2 and ok.last_usage["by_role"] == {"fallback": 2}
    bad = typer_with(Completion('{"decision": "COMP', "length"))
    out = bad.type_example(ex, P6_2010, ["p0", "p1"])
    assert all(t.decision is None and t.status == "fallback_truncated" for t in out)


def test_reranker_penalises_only_contradicting(toy_kg):
    texts = [
        "The place of birth of Alma Verdan is Lowmarsh.",
        "The place of birth of Alma Verdan is Avalon City.",
        "Unparseable sentence.",
    ]
    ex = _ex(texts)
    frames = {"q": P19}
    rr = ConflictAwareReranker(IdentityReranker(), _typer(toy_kg, "S3"), frames, lam=10.0)
    r = rr.rank(ex)
    assert r.order[-1] == "p0" and r.order[:2] == ("p1", "p2")
    f = ConflictAwareReranker(IdentityReranker(), _typer(toy_kg, "S3"), frames, mode="filter")
    assert f.rank(ex).removed == frozenset({"p0"})
    none = ConflictAwareReranker(IdentityReranker(), _typer(toy_kg, "S3"), {}, lam=10.0)
    assert none.rank(ex).order == ("p0", "p1", "p2")  # no frame for the question: no KG step
