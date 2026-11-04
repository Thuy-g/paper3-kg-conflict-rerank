"""Chat interface shared by all backends. Every call goes through the budget guard and token log."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

from kgrerank.llm.budget import BudgetGuard, TokenLogger

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


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
    usage_reported: dict | None = None


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token). Logged as an estimate, never as a count."""
    return math.ceil(len(text) / 4) if text else 0


def is_local_endpoint(base_url: str) -> bool:
    host = urlparse(base_url).hostname or ""
    return host in LOCAL_HOSTS


class LLMBackend(ABC):
    """Base class: subclasses implement ``_complete``; ``chat`` adds guard and logging."""

    name: str = "base"

    def __init__(self, model: str, guard: BudgetGuard, logger: TokenLogger | None, host: str):
        self.model = model
        self.guard = guard
        self.logger = logger
        self.host = host

    @abstractmethod
    def _complete(
        self, messages: Sequence[ChatMessage], max_tokens: int, temperature: float, seed: int | None
    ) -> tuple[str, dict | None]: ...

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> LLMResponse:
        prompt_est = sum(estimate_tokens(m.content) for m in messages)
        self.guard.check(
            prompt_est, max_tokens
        )  # raises before the call if a cap would be exceeded
        text, usage = self._complete(messages, max_tokens, temperature, seed)
        completion_est = estimate_tokens(text)
        self.guard.record(prompt_est, completion_est)
        if self.logger is not None:
            self.logger.log(
                backend=self.name,
                endpoint_host=self.host,
                model=self.model,
                prompt_tokens_est=prompt_est,
                completion_tokens_est=completion_est,
                guard=self.guard,
                usage_reported=usage,
            )
        return LLMResponse(text, self.model, self.name, prompt_est, completion_est, usage)
