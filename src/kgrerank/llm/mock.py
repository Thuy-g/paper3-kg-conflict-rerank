"""Deterministic offline backend (default). Output depends only on model, seed and messages."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from kgrerank.llm.base import ChatMessage, LLMBackend
from kgrerank.llm.budget import BudgetGuard, TokenLogger


class MockLLM(LLMBackend):
    """Returns one of ``choices`` picked by a hash of the request (no network, no randomness)."""

    name = "mock"

    def __init__(
        self,
        model: str = "mock-1",
        choices: Sequence[str] = ("COMPATIBLE", "CONTRADICTING", "IRRELEVANT", "UNKNOWN"),
        guard: BudgetGuard | None = None,
        logger: TokenLogger | None = None,
    ):
        super().__init__(model, guard or BudgetGuard(is_local=True), logger, host="mock")
        if not choices:
            raise ValueError("choices must be non-empty")
        self.choices = tuple(choices)

    def _complete(
        self, messages: Sequence[ChatMessage], max_tokens: int, temperature: float, seed: int | None
    ) -> tuple[str, dict | None]:
        h = hashlib.sha256()
        h.update(f"{self.model}|{seed}".encode())
        for m in messages:
            h.update(f"|{m.role}:{m.content}".encode())
        idx = int.from_bytes(h.digest()[:8], "big") % len(self.choices)
        return self.choices[idx], None
