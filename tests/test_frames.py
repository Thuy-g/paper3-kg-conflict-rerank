"""Inference frames: parser (mocked LLM), linking states, snapshot time, audit tooling."""

from __future__ import annotations

import json

from kgrerank.extract.linker import EntityLinker
from kgrerank.frames.audit import audit_sample, compare, human_frames
from kgrerank.frames.parser import LLMFrameParser, coverage, resolve_time
from kgrerank.frames.schema import InferenceFrame, Snapshot
from kgrerank.kg.time import year_period
from kgrerank.llm.base import Completion
from kgrerank.llm.mock import MockLLM

SNAP = Snapshot("s", (2025, 4, 3), (2025, 6, 15), "test")
NO_SNAP = Snapshot("none")


def _parser(toy_kg, reply: dict | str, snapshot=SNAP, prompts=None):
    def responder(messages):
        if prompts is not None:
            prompts.append(messages[0].content)
        text = reply if isinstance(reply, str) else json.dumps(reply)
        return Completion(text, "stop")

    labels = [p.label for p in toy_kg.properties.values()]
    return LLMFrameParser(MockLLM(responder=responder), EntityLinker(toy_kg), labels, snapshot)


def test_parser_sees_only_the_question_and_links_uniquely(toy_kg):
    prompts: list[str] = []
    q = "Where was Alma Verdan born?"
    f = _parser(
        toy_kg,
        {
            "subject": "Alma Verdan",
            "relation": "place of birth",
            "time_expression": "",
            "question_type": "single_fact",
        },
        prompts=prompts,
    ).parse("q1", q)
    assert f.subject == "Z1" and f.prop == "P19" and f.supported and f.source == "llm_parser"
    assert prompts == [prompts[0]] and q in prompts[0] and "Port Avalon" not in prompts[0]


def test_ambiguous_and_unlinked_stay_unresolved(toy_kg):
    amb = _parser(
        toy_kg,
        {
            "subject": "Port Avalon",
            "relation": "head of government",
            "time_expression": "",
            "question_type": "single_fact",
        },
    ).parse("q", "Who heads Port Avalon?")
    assert amb.subject is None and amb.subject_status == "ambiguous" and not amb.supported
    assert set(amb.subject_candidates) == {"Z3", "Z8", "Z9", "Z17"}
    unk = _parser(
        toy_kg,
        {
            "subject": "Atlantis",
            "relation": "population",
            "time_expression": "",
            "question_type": "single_fact",
        },
    ).parse("q", "What is the population of Atlantis?")
    assert unk.subject_status == "unlinked" and unk.prop_status == "unlinked" and not unk.supported


def test_unsupported_types_and_errors(toy_kg):
    mh = _parser(
        toy_kg,
        {
            "subject": "Alma Verdan",
            "relation": "place of birth",
            "time_expression": "",
            "question_type": "multi_hop",
        },
    ).parse("q", "Where was Alma Verdan's father born?")
    assert not mh.supported and mh.question_type == "multi_hop"
    bad = _parser(toy_kg, "not json").parse("q", "Where was Alma Verdan born?")
    assert bad.errors == ("parse_error",) and not bad.supported
    invented = _parser(
        toy_kg,
        {
            "subject": "Oren Verdan",
            "relation": "place of birth",
            "time_expression": "",
            "question_type": "single_fact",
        },
    ).parse("q", "Where was Alma Verdan born?")
    assert "subject_not_in_question" in invented.errors and not invented.supported


def test_relative_time_uses_the_snapshot_not_the_run_date():
    assert resolve_time("in 2010", SNAP) == (year_period(2010), "explicit")
    assert resolve_time("this year", SNAP) == (year_period(2025), "snapshot_relative")
    moment, status = resolve_time("currently", SNAP)
    assert status == "snapshot_relative" and moment.start.lo == (2025, 4, 3)
    assert moment.start.hi == (2025, 6, 15) and moment.is_point
    assert resolve_time("currently", NO_SNAP) == (None, "unresolved")
    assert resolve_time("", SNAP) == (None, "none")
    assert resolve_time("during the war", SNAP) == (None, "unresolved")


def test_frames_roundtrip_and_coverage(toy_kg):
    f = _parser(
        toy_kg,
        {
            "subject": "Alma Verdan",
            "relation": "place of birth",
            "time_expression": "in 1950",
            "question_type": "single_fact",
        },
    ).parse("q", "Where was Alma Verdan born in 1950?")
    again = InferenceFrame.from_dict(json.loads(json.dumps(f.to_dict())))
    assert again == f
    cov = coverage([f, InferenceFrame(qid="x", question="?")])
    assert cov["questions"] == 2 and cov["supported"] == 1 and cov["supported_share"] == 0.5


def test_audit_sample_is_deterministic_and_label_free():
    qs = [
        {"qid": f"q{i}", "question": "?", "stratum": "a" if i < 6 else "b", "source": "s"}
        for i in range(10)
    ]
    s1, s2 = audit_sample(qs, 4, 7), audit_sample(qs, 4, 7)
    assert s1 == s2 and len(s1) == 4
    assert sum(q["stratum"] == "a" for q in s1) == 2  # proportional 6:4 -> 2.4:1.6 -> 2:2


def test_human_frames_and_compare():
    rows = [
        {
            "qid": "q1",
            "question": "?",
            "subject_qid": "Z1",
            "property_pid": "P19",
            "time_expression": "",
            "question_type": "single_fact",
        },
        {
            "qid": "q2",
            "question": "?",
            "subject_qid": "AMBIGUOUS",
            "property_pid": "P6",
            "time_expression": "currently",
            "question_type": "single_fact",
        },
    ]
    human = human_frames(rows, {"s": SNAP}, {"q1": "s", "q2": "s"})
    assert human["q1"].supported and human["q1"].source == "human_audit"
    assert human["q2"].subject_status == "ambiguous" and not human["q2"].supported
    parsed = {
        "q1": human["q1"],
        "q2": InferenceFrame(
            qid="q2",
            question="?",
            subject="Z3",
            subject_status="linked",
            prop="P6",
            prop_status="linked",
            time_status="none",
            question_type="single_fact",
        ),
    }
    rep = compare(parsed, human)
    assert rep["subject"]["agree"] == 1 and rep["parser_supported_but_human_not"] == ["q2"]
