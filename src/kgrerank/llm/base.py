"""Chat interface shared by all backends. Every call goes through the budget guard and token log.

Each call returns an explicit ``status`` so that callers never mistake a failure for a model
decision:
  ok              normal completion
  truncated       the server stopped at max_tokens (finish_reason == "length")
  thinking_output the reply contains a <think> block although thinking should be off
                  (a configuration error, e.g. Qwen3 without enable_thinking=False)
  backend_error   transport/server error (the exception text is kept, never a key)
Budget violations (PaidAPINotAllowed, BudgetExceeded) are raised, never swallowed.
Every call is also appended to ``backend.events`` for per-system usage accounting
(role, status, token estimates, reported usage, latency). There is no response cache.
"""

from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from kgrerank.llm.budget import BudgetExceeded, BudgetGuard, PaidAPINotAllowed, TokenLogger

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
CACHE_POLICY = "none"
STATUSES = ("ok", "truncated", "thinking_output", "backend_error")


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    backend: str
    prompt_tokens_est: int
    completion_tokens_est: int
    status: str = "ok"
    finish_reason: str | None = None
    usage_reported: dict | None = None
    latency_s: float = 0.0
    error: str = ""


@dataclass(frozen=True)
class Completion:
    """What a concrete backend returns from ``_complete``."""

    text: str
    finish_reason: str | None = "stop"
    usage: dict | None = None


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token). Logged as an estimate, never as a count."""
    return math.ceil(len(text) / 4) if text else 0


def is_local_endpoint(base_url: str) -> bool:
    host = urlparse(base_url).hostname or ""
    return host in LOCAL_HOSTS


class LLMBackend(ABC):
    """Base class: subclasses implement ``_complete``; ``chat`` adds guard, status and logging."""

    name: str = "base"

    def __init__(self, model: str, guard: BudgetGuard, logger: TokenLogger | None, host: str):
        self.model = model
        self.guard = guard
        self.logger = logger
        self.host = host
        self.events: list[dict[str, Any]] = []

    @abstractmethod
    def _complete(
        self, messages: Sequence[ChatMessage], max_tokens: int, temperature: float, seed: int | None
    ) -> Completion: ...

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
        seed: int | None = None,
        role: str = "unspecified",
    ) -> LLMResponse:
        prompt_est = sum(estimate_tokens(m.content) for m in messages)
        self.guard.check(
            prompt_est, max_tokens
        )  # raises before the call if a cap would be exceeded
        t0 = time.perf_counter()
        error = ""
        try:
            comp = self._complete(messages, max_tokens, temperature, seed)
        except (BudgetExceeded, PaidAPINotAllowed):
            raise
        except (
            Exception
        ) as exc:  # any transport/server failure is recorded, never swallowed silently
            comp = Completion("", None, None)
            error = f"{type(exc).__name__}: {exc}"[:300]
        latency = time.perf_counter() - t0
        if error:
            status = "backend_error"
        elif comp.finish_reason == "length":
            status = "truncated"
        elif "<think>" in comp.text:
            status = "thinking_output"
        else:
            status = "ok"
        completion_est = estimate_tokens(comp.text)
        self.guard.record(prompt_est, completion_est)
        event = {
            "role": role,
            "status": status,
            "prompt_tokens_est": prompt_est,
            "completion_tokens_est": completion_est,
            "usage_reported": comp.usage,
            "latency_s": round(latency, 4),
            "finish_reason": comp.finish_reason,
        }
        self.events.append(event)
        if self.logger is not None:
            self.logger.log(
                backend=self.name,
                endpoint_host=self.host,
                model=self.model,
                prompt_tokens_est=prompt_est,
                completion_tokens_est=completion_est,
                guard=self.guard,
                usage_reported=comp.usage,
                extra={"role": role, "status": status, "latency_s": event["latency_s"]},
            )
        return LLMResponse(
            comp.text,
            self.model,
            self.name,
            prompt_est,
            completion_est,
            status,
            comp.finish_reason,
            comp.usage,
            latency,
            error,
        )


def summarize_events(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Calls, token estimates, reported tokens, latency and status counts, overall and by role."""
    out: dict[str, Any] = {
        "calls": len(events),
        "prompt_tokens_est": 0,
        "completion_tokens_est": 0,
        "reported_total_tokens": 0,
        "latency_s": 0.0,
        "by_role": {},
        "by_status": {},
        "cache_policy": CACHE_POLICY,
    }
    for e in events:
        out["prompt_tokens_est"] += e["prompt_tokens_est"]
        out["completion_tokens_est"] += e["completion_tokens_est"]
        rep = e.get("usage_reported") or {}
        out["reported_total_tokens"] += int(rep.get("total_tokens", 0) or 0)
        out["latency_s"] += e["latency_s"]
        out["by_role"][e["role"]] = out["by_role"].get(e["role"], 0) + 1
        out["by_status"][e["status"]] = out["by_status"].get(e["status"], 0) + 1
    out["latency_s"] = round(out["latency_s"], 4)
    return out
