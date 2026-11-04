"""G2+ skeleton: per reason type a positive case, a near-miss, and UNKNOWN without evidence.

All on the hand-written fictional KG (tests/fixtures/toy_kg.json); no real data, no network.
"""

from __future__ import annotations

import copy

import pytest

from kgrerank.conflict.policy import CONFIDENCE, POLICY_VERSION
from kgrerank.conflict.reranker import ConflictAwareReranker
from kgrerank.conflict.typer import G2PlusTyper
from kgrerank.extract.linker import EntityLinker
from kgrerank.extract.llm import LLMClaimExtractor
from kgrerank.extract.pattern import PatternExtractor
from kgrerank.kg.settings import restrict
from kgrerank.kg.time import year_period
from kgrerank.kg.view import KGView
from kgrerank.llm.mock import MockLLM
from kgrerank.perturb.operators import QuestionFrame
from kgrerank.rerankers.simple import IdentityReranker
from kgrerank.schema import Candidate, Decision, Example

P19 = QuestionFrame("Z1", "P19", ("Z3",))
P6_2010 = QuestionFrame("Z3", "P6", ("Z10",), time_anchor=year_period(2010))
P22 = QuestionFrame("Z1", "P22", ("Z14",))


def _ex(texts: list[str], frame: QuestionFrame) -> Example:
    meta = {
        "source": "t",
        "synthetic": True,
        "frame": {"subject": frame.subject, "prop": frame.prop, "gold": list(frame.gold)},
    }
    return Example("q", "?", ["x"], [Candidate(f"p{i}", "", t) for i, t in enumerate(texts)], meta)


def _typer(kg: KGView, setting: str, fallback=None) -> G2PlusTyper:
    return G2PlusTyper(
        kg, setting, PatternExtractor([p.label for p in kg.properties.values()]), fallback
    )


def _types(kg, setting, texts, frame, fallback=None):
    out = _typer(kg, setting, fallback).type_example(_ex(texts, frame), frame)
    return {t.pid: t for t in out}


def test_settings_restrict_and_mask(toy_kg):
    assert not restrict(toy_kg, "S0").properties
    s1 = restrict(toy_kg, "S1")
    assert s1.properties and not s1.statements and not s1.entities
    s2 = restrict(toy_kg, "S2", mask=("Z1", "P19"))
    assert not s2.statements_of("Z1", "P19")  # the question's own fact is masked
    assert s2.statements_of("Z3", "P131") and s2.statements_of("Z3", "P1448")
    assert not s2.statements_of("Z3", "P6")  # relational facts are not part of S2
    assert restrict(toy_kg, "S3").statements_of("Z1", "P19")
    with pytest.raises(ValueError):
        restrict(toy_kg, "S4")


def test_pattern_extractor_needs_lexicon(toy_kg):
    text = "The place of birth of Alma Verdan is Lowmarsh."
    generic = PatternExtractor().extract("p", text)
    assert (
        generic.relation == "place" and generic.subject == "birth of Alma Verdan"
    )  # ambiguous split
    c = PatternExtractor(["place of birth"]).extract("p", text)
    assert (c.relation, c.subject, c.obj, c.time) == (
        "place of birth",
        "Alma Verdan",
        "Lowmarsh",
        None,
    )
    lex = PatternExtractor(["head of government"])
    c = lex.extract("p", "In 2010, the head of government of Port Avalon was Bram Ostler.")
    assert c.time == year_period(2010)
    c = lex.extract(
        "p",
        "Port Avalon (fictional town in Lake County): the head of government of "
        "Port Avalon is Rosa Fein.",
    )
    assert c.note == "fictional town in Lake County"
    assert lex.extract("p", "Mira Okonkwo led the city.") is None


def test_linker(toy_kg):
    lk = EntityLinker(toy_kg)
    assert lk.link("Avalon City").eid == "Z3" and lk.link("Avalon City").via == "alias"
    assert lk.link("Kingsbridge").via == "name_statement"
    assert lk.link("Port Avalon").status == "ambiguous"
    assert lk.link("Port Avalon", "fictional town in Lake County").eid == "Z9"
    assert lk.property_by_label("place of birth") == "P19"


def test_identity_reasons(toy_kg, toy_kg_dict):
    t = _types(
        toy_kg,
        "S3",
        [
            "The place of birth of Alma Verdan is Avalon City.",
            "The place of birth of Alma Verdan is Kingsbridge.",
        ],
        P19,
    )
    assert t["p0"].decision is Decision.COMPATIBLE and t["p0"].reasons == ("alias",)
    assert t["p1"].decision is Decision.COMPATIBLE and t["p1"].reasons == ("historical_identity",)
    d = copy.deepcopy(toy_kg_dict)
    d["entities"]["Z7"]["aliases"] = ["Avalon City"]  # near-miss: ambiguous alias
    t2 = _types(
        KGView.from_dict(d), "S3", ["The place of birth of Alma Verdan is Avalon City."], P19
    )
    assert t2["p0"].decision is Decision.UNKNOWN and t2["p0"].rule == "R-object-unknown"


def test_granularity(toy_kg, toy_kg_dict):
    t = _types(toy_kg, "S3", ["The place of birth of Alma Verdan is Republic of Merrow."], P19)
    assert t["p0"].decision is Decision.COMPATIBLE and t["p0"].rule == "R-hierarchy-coarser"
    # Near-miss: the KG value is Lowmarsh, whose located-in edge is time-qualified (1960-1990).
    d = copy.deepcopy(toy_kg_dict)
    for st in d["statements"]:
        if st["s"] == "Z1" and st["p"] == "P19":
            st["v"]["value"] = "Z7"
    t2 = _types(
        KGView.from_dict(d),
        "S3",
        ["The place of birth of Alma Verdan is Avalon Province."],
        QuestionFrame("Z1", "P19", ("Z7",)),
    )
    assert t2["p0"].decision is Decision.UNKNOWN and t2["p0"].rule == "R-hierarchy-uncertain"


def test_temporal_scope(toy_kg):
    t = _types(
        toy_kg,
        "S3",
        [
            "From 2012, the head of government of Port Avalon was Teo Brandt.",
            "The head of government of Port Avalon is Ivo Sallis.",
        ],
        P6_2010,
    )
    assert t["p0"].decision is Decision.COMPATIBLE and t["p0"].rule == "R-time-disjoint"
    assert t["p1"].decision is Decision.UNKNOWN and t["p1"].rule == "R-time-unknown"
    # Without a KG (S0) the subject cannot be identified, so nothing is decided.
    t0 = _types(
        toy_kg, "S0", ["From 2012, the head of government of Port Avalon was Teo Brandt."], P6_2010
    )
    assert t0["p0"].decision is Decision.UNKNOWN and t0["p0"].rule == "R-subject-unknown"


def test_homonym_and_predicate(toy_kg):
    t = _types(
        toy_kg,
        "S3",
        [
            "Port Avalon (fictional town in Lake County): "
            "the head of government of Port Avalon is Rosa Fein.",
            "The head of state of Port Avalon is Gil Moray.",
        ],
        P6_2010,
    )
    assert t["p0"].decision is Decision.IRRELEVANT and t["p0"].reasons == ("homonym",)
    assert t["p1"].decision is Decision.IRRELEVANT and t["p1"].reasons == ("predicate_mismatch",)
    t0 = _types(toy_kg, "S0", ["The head of state of Port Avalon is Gil Moray."], P6_2010)
    assert t0["p0"].decision is Decision.UNKNOWN  # without property metadata


def test_inverse(toy_kg):
    t = _types(toy_kg, "S3", ["The child of Oren Verdan is Alma Verdan."], P22)
    assert t["p0"].decision is Decision.COMPATIBLE and "inverse_relation" in t["p0"].reasons


def test_counterfactual_is_soft(toy_kg, toy_kg_dict):
    t = _types(
        toy_kg, "S3", ["In 2010, the head of government of Port Avalon was Bram Ostler."], P6_2010
    )
    v = t["p0"]
    assert v.decision is Decision.CONTRADICTING and v.rule == "R-single-best-value"
    assert 0 < v.confidence < 1 and v.policy == POLICY_VERSION
    stable = _types(toy_kg, "S3", ["The place of birth of Alma Verdan is Lowmarsh."], P19)["p0"]
    assert stable.decision is Decision.CONTRADICTING
    assert stable.confidence == pytest.approx(CONFIDENCE[("single_value", "other")] - 0.1)
    # Near-miss 1: subject listed as a constraint exception -> UNKNOWN.
    d = copy.deepcopy(toy_kg_dict)
    d["properties"]["P19"]["constraints"][0]["exceptions"] = ["Z1"]
    t1 = _types(KGView.from_dict(d), "S3", ["The place of birth of Alma Verdan is Lowmarsh."], P19)
    assert t1["p0"].decision is Decision.UNKNOWN and t1["p0"].rule == "R-exception"
    # Near-miss 2: no cardinality constraint -> UNKNOWN (multiple values may coexist).
    t2 = _types(toy_kg, "S3", ["The father of Alma Verdan is Bram Ostler."], P22)
    assert t2["p0"].decision is Decision.UNKNOWN and t2["p0"].rule == "R-cardinality-open"
    # Near-miss 3: mutable property, both statements unscoped -> UNKNOWN.
    loose = QuestionFrame("Z3", "P6", ("Z11",))
    d3 = copy.deepcopy(toy_kg_dict)
    d3["statements"] = [
        s
        for s in d3["statements"]
        if not (s["s"] == "Z3" and s["p"] == "P6" and s["v"]["value"] != "Z11")
    ]
    d3["statements"] = [{**s, "q": {}} if s["p"] == "P6" else s for s in d3["statements"]]
    t3 = _types(
        KGView.from_dict(d3), "S3", ["The head of government of Port Avalon is Bram Ostler."], loose
    )
    assert t3["p0"].decision is Decision.UNKNOWN and t3["p0"].rule == "R-mutable-unscoped"


def test_fallback_counts_llm_calls(toy_kg):
    texts = ["The head of government of Port Avalon is Ivo Sallis.", "Unparseable sentence."]
    typer = _typer(toy_kg, "S3", MockLLM())
    out = typer.type_example(_ex(texts, P6_2010), P6_2010)
    assert all(t.fallback for t in out) and typer.last_llm_calls == 2
    assert all(t.confidence == 0.3 for t in out)
    no_fb = _types(toy_kg, "S3", texts, P6_2010)
    assert all(t.decision is Decision.UNKNOWN and not t.fallback for t in no_fb.values())


def test_llm_extractor_rejects_invalid_json(toy_kg):
    class Fixed(MockLLM):
        def __init__(self, reply):
            super().__init__(choices=(reply,))

    ok = LLMClaimExtractor(
        Fixed(
            '{"subject": "Alma Verdan", "relation": "Place of birth", '
            '"object": "Lowmarsh", "year": 1950}'
        )
    ).extract("p", "t")
    assert ok.relation == "place of birth" and ok.time == year_period(1950)
    assert LLMClaimExtractor(Fixed("not json")).extract("p", "t") is None
    assert LLMClaimExtractor(Fixed('{"subject": ""}')).extract("p", "t") is None


def test_reranker_penalises_only_contradicting(toy_kg):
    texts = [
        "In 2010, the head of government of Port Avalon was Bram Ostler.",
        "From 2012, the head of government of Port Avalon was Teo Brandt.",
        "Unparseable sentence.",
    ]
    ex = _ex(texts, P6_2010)
    ex.meta["frame"]["time_anchor_year"] = 2010
    rr = ConflictAwareReranker(IdentityReranker(), _typer(toy_kg, "S3"), lam=10.0)
    r = rr.rank(ex)
    assert r.order[-1] == "p0" and r.order[:2] == ("p1", "p2")
    f = ConflictAwareReranker(IdentityReranker(), _typer(toy_kg, "S3"), mode="filter").rank(ex)
    assert f.removed == frozenset({"p0"}) and f.order == ("p1", "p2")
    no_frame = Example("q", "?", [], ex.candidates, {"source": "t", "synthetic": True})
    assert rr.rank(no_frame).order == ("p0", "p1", "p2")
