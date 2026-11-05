from __future__ import annotations

import json

import pytest

from kgrerank.llm import (
    BudgetExceeded,
    BudgetGuard,
    ChatMessage,
    MockLLM,
    OpenAICompatLLM,
    PaidAPINotAllowed,
    TokenLogger,
)

REMOTE = "https://api.example.invalid/v1"
SECRET = "sk-test-not-a-real-key"


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, dict(headers), body))
        return {
            "choices": [{"message": {"content": "COMPATIBLE"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 1},
        }


def test_remote_endpoint_refused_without_budget_env():
    with pytest.raises(PaidAPINotAllowed):
        OpenAICompatLLM(model="m", base_url=REMOTE, env={}, transport=FakeTransport())
    with pytest.raises(PaidAPINotAllowed):  # caps missing
        OpenAICompatLLM(
            model="m", base_url=REMOTE, env={"ALLOW_PAID_API": "1"}, transport=FakeTransport()
        )
    with pytest.raises(PaidAPINotAllowed):  # caps must be positive integers
        OpenAICompatLLM(
            model="m",
            base_url=REMOTE,
            env={"ALLOW_PAID_API": "1", "MAX_API_CALLS": "x", "MAX_API_TOKENS": "5"},
            transport=FakeTransport(),
        )


def test_local_endpoint_allowed_and_logged_without_key(tmp_path):
    log = tmp_path / "api_usage.jsonl"
    t = FakeTransport()
    llm = OpenAICompatLLM(
        model="m",
        base_url="http://localhost:8000/v1",
        env={"OPENAI_API_KEY": SECRET},
        transport=t,
        logger=TokenLogger(log),
    )
    resp = llm.chat([ChatMessage("user", "hello world")], max_tokens=5)
    assert (
        resp.text == "COMPATIBLE" and t.calls[0][0] == "http://localhost:8000/v1/chat/completions"
    )
    assert t.calls[0][1]["Authorization"] == f"Bearer {SECRET}"
    text = log.read_text()
    assert SECRET not in text
    rec = json.loads(text.splitlines()[0])
    assert rec["endpoint_host"] == "localhost" and rec["cumulative_calls"] == 1
    assert rec["usage_reported"] == {"prompt_tokens": 7, "completion_tokens": 1}


def test_caps_abort_before_the_call():
    t = FakeTransport()
    env = {"ALLOW_PAID_API": "1", "MAX_API_CALLS": "1", "MAX_API_TOKENS": "1000"}
    llm = OpenAICompatLLM(model="m", base_url=REMOTE, env=env, transport=t)
    llm.chat([ChatMessage("user", "hi")], max_tokens=5)
    with pytest.raises(BudgetExceeded):
        llm.chat([ChatMessage("user", "hi")], max_tokens=5)
    assert len(t.calls) == 1  # the second call never reached the transport
    tok = OpenAICompatLLM(
        model="m",
        base_url=REMOTE,
        transport=t,
        env={"ALLOW_PAID_API": "1", "MAX_API_CALLS": "9", "MAX_API_TOKENS": "10"},
    )
    with pytest.raises(BudgetExceeded):  # prompt estimate + max_tokens would exceed the cap
        tok.chat([ChatMessage("user", "x" * 20)], max_tokens=8)
    assert len(t.calls) == 1


def test_mock_is_deterministic_and_guarded():
    a = MockLLM().chat([ChatMessage("user", "q")], seed=1).text
    assert a == MockLLM().chat([ChatMessage("user", "q")], seed=1).text
    capped = MockLLM(guard=BudgetGuard(is_local=True, max_calls=1))
    capped.chat([ChatMessage("user", "q")])
    with pytest.raises(BudgetExceeded):
        capped.chat([ChatMessage("user", "q")])
