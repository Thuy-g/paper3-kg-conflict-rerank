"""Deterministic offline backend (default). Output depends only on model, seed and messages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence

from kgrerank.llm.base import ChatMessage, Completion, LLMBackend
from kgrerank.llm.budget import BudgetGuard, TokenLogger

DECISION_LABELS = ("COMPATIBLE", "CONTRADICTING", "IRRELEVANT", "UNKNOWN")


class MockLLM(LLMBackend):
    """Picks one of ``choices`` by a hash of the request; no network, no randomness.

    ``json_decision=True`` wraps the choice as {"decision": ...} (the format the typers expect).
    ``responder`` (tests only) computes the reply from the messages, e.g. to inspect prompts.
    """

    name = "mock"

    def __init__(
        self,
        model: str = "mock-1",
        choices: Sequence[str] = DECISION_LABELS,
        guard: BudgetGuard | None = None,
        logger: TokenLogger | None = None,
        json_decision: bool = True,
        responder: Callable[[Sequence[ChatMessage]], Completion] | None = None,
    ):
        super().__init__(model, guard or BudgetGuard(is_local=True), logger, host="mock")
        if not choices:
            raise ValueError("choices must be non-empty")
        self.choices = tuple(choices)
        self.json_decision = json_decision
        self.responder = responder

    def _complete(
        self, messages: Sequence[ChatMessage], max_tokens: int, temperature: float, seed: int | None
    ) -> Completion:
        if self.responder is not None:
            return self.responder(messages)
        h = hashlib.sha256()
        h.update(f"{self.model}|{seed}".encode())
        for m in messages:
            h.update(f"|{m.role}:{m.content}".encode())
        choice = self.choices[int.from_bytes(h.digest()[:8], "big") % len(self.choices)]
        text = json.dumps({"decision": choice}) if self.json_decision else choice
        return Completion(text, "stop", None)
