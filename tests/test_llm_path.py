"""LLM path: call statuses, information access of prompts, extractor and fallback integration."""

from __future__ import annotations

import json

from kgrerank.extract.llm import LLMClaimExtractor
from kgrerank.llm.base import ChatMessage, Completion
from kgrerank.llm.mock import MockLLM
from kgrerank.llm.openai_compat import OpenAICompatLLM
from kgrerank.rerankers.llm_judge import LLMJudgeFilter, LLMTyper
from kgrerank.rerankers.simple import IdentityReranker
from kgrerank.schema import Candidate, Decision, Example

REFERENCE = "Mira Okonkwo"  # the dataset answer: must never reach any prompt


def _ex() -> Example:
    cands = [
        Candidate("a", "T1", "In 2010 the head of government of Avalon City was Bram Ostler."),
        Candidate("b", "T2", "Avalon City is a port."),
        Candidate("c", "T3", "Teo Brandt led the city from 2012."),
    ]
    return Example(
        "q1",
        "Who was the head of government of Port Avalon in 2010?",
        [REFERENCE],
        cands,
        {"source": "t", "synthetic": True},
    )


class Recorder:
    """responder for MockLLM: records prompts and replies with a fixed completion."""

    def __init__(self, completion: Completion):
        self.completion, self.prompts = completion, []

    def __call__(self, messages):
        self.prompts.append("\n".join(m.content for m in messages))
        return self.completion


def test_statuses_are_explicit():
    def backend(text, finish="stop", fail=False):
        def responder(messages):
            if fail:
                raise TimeoutError("server timeout")
            return Completion(text, finish, None)

        return MockLLM(responder=responder)

    assert backend('{"decision": "COMPATIBLE"}').chat([ChatMessage("user", "x")]).status == "ok"
    assert backend('{"decis', "length").chat([ChatMessage("user", "x")]).status == "truncated"
    assert (
        backend("<think>hm</think>{}").chat([ChatMessage("user", "x")]).status == "thinking_output"
    )
    resp = backend("", fail=True).chat([ChatMessage("user", "x")])
    assert resp.status == "backend_error" and "TimeoutError" in resp.error


def test_failures_are_not_unknown_decisions():
    ex = _ex()
    for completion, status in [
        (Completion('{"decision": "UNK', "length"), "truncated"),
        (Completion("I think it is fine.", "stop"), "parse_error"),
        (Completion('{"decision": "UNKNOWN"}', "stop"), "ok"),
    ]:
        typer = LLMTyper(MockLLM(responder=Recorder(completion)))
        d = typer.type_passages(ex, ["a"], ["a", "b", "c"])["a"]
        assert d.status == status
        assert (d.decision is Decision.UNKNOWN) == (status == "ok")


def test_prompts_never_contain_the_reference_answer_and_show_declared_context():
    ex = _ex()
    rec = Recorder(Completion('{"decision": "COMPATIBLE"}', "stop"))
    inter = LLMTyper(MockLLM(responder=rec), prompt="inter_context_v1", context_m=1)
    inter.type_passages(ex, ["a"], ["b", "a", "c"])
    assert ex.question in rec.prompts[0] and "Avalon City is a port." in rec.prompts[0]
    assert "Teo Brandt" not in rec.prompts[0]  # context_m=1: only the first other passage
    single = LLMTyper(MockLLM(responder=rec), prompt="single_passage_v1")
    single.type_passages(ex, ["a"], ["b", "a", "c"])
    assert "Avalon City is a port." not in rec.prompts[1]  # no other passages
    assert all(REFERENCE not in p for p in rec.prompts)
    assert "other_passages" in inter.information_access()
    assert "reference_answer" in inter.information_access()["never"]


def test_extractor_receives_the_question():
    rec = Recorder(
        Completion(
            json.dumps(
                {
                    "subject": "Avalon City",
                    "relation": "head of government",
                    "object": "Bram Ostler",
                    "year": 2010,
                }
            ),
            "stop",
        )
    )
    ext = LLMClaimExtractor(MockLLM(responder=rec))
    claim, status = ext.extract_with_status("a", _ex().candidates[0].text, _ex().question)
    assert status == "ok" and claim.obj == "Bram Ostler"
    assert _ex().question in rec.prompts[0] and REFERENCE not in rec.prompts[0]
    empty = LLMClaimExtractor(MockLLM(responder=Recorder(Completion("{}", "stop"))))
    assert empty.extract_with_status("a", "t", "q") == (None, "no_claim")


def test_openai_compat_sends_extra_body_and_reads_finish_reason():
    sent = {}

    def transport(url, headers, body, timeout):
        sent.update(body)
        return {"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}]}

    llm = OpenAICompatLLM(
        model="Qwen/Qwen3-8B",
        base_url="http://localhost:8000/v1",
        env={},
        transport=transport,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        sampling={"top_p": 0.8, "top_k": 20},
    )
    resp = llm.chat([ChatMessage("user", "x")], max_tokens=16, role="judge")
    assert sent["chat_template_kwargs"] == {"enable_thinking": False} and sent["top_k"] == 20
    assert resp.status == "truncated" and llm.events[-1]["role"] == "judge"


def test_judge_usage_counts_every_call():
    ex = _ex()
    f = LLMJudgeFilter(IdentityReranker(), LLMTyper(MockLLM()), top_m=3)
    r = f.rank(ex)
    assert r.llm_calls == 3 and r.llm_usage["prompt_tokens_est"] > 0
    assert r.llm_usage["cache_policy"] == "none"
