"""LLM backends behind one OpenAI-compatible chat interface, with budget guard and token log."""

from kgrerank.llm.base import (
    ChatMessage,
    Completion,
    LLMBackend,
    LLMResponse,
    estimate_tokens,
    summarize_events,
)
from kgrerank.llm.budget import BudgetExceeded, BudgetGuard, PaidAPINotAllowed, TokenLogger
from kgrerank.llm.mock import MockLLM
from kgrerank.llm.openai_compat import OpenAICompatLLM

__all__ = [
    "BudgetExceeded",
    "BudgetGuard",
    "ChatMessage",
    "Completion",
    "LLMBackend",
    "LLMResponse",
    "MockLLM",
    "OpenAICompatLLM",
    "PaidAPINotAllowed",
    "TokenLogger",
    "estimate_tokens",
    "summarize_events",
]
