"""Budget guard and token log (CLAUDE.md §5).

Local endpoints cost nothing but still go through the guard and the log. Any other endpoint is
refused unless ``ALLOW_PAID_API=1`` and both ``MAX_API_CALLS`` and ``MAX_API_TOKENS`` are set; the
guard aborts *before* a call that could exceed either cap (worst case: prompt estimate plus the
requested ``max_tokens``). API keys are never logged.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class PaidAPINotAllowed(RuntimeError):
    """A non-local endpoint was requested without the explicit budget environment variables."""


class BudgetExceeded(RuntimeError):
    """The next call could exceed the configured call or token cap."""


def _positive_int(env: Mapping[str, str], key: str) -> int | None:
    raw = env.get(key)
    if raw is None or raw == "":
        return None
    try:
        val = int(raw)
    except ValueError as err:
        raise PaidAPINotAllowed(f"{key} must be a positive integer, got {raw!r}") from err
    if val <= 0:
        raise PaidAPINotAllowed(f"{key} must be a positive integer, got {raw!r}")
    return val


@dataclass
class BudgetGuard:
    is_local: bool
    max_calls: int | None = None
    max_tokens: int | None = None
    calls: int = 0
    tokens: int = 0

    @classmethod
    def from_env(cls, is_local: bool, env: Mapping[str, str] | None = None) -> BudgetGuard:
        env = os.environ if env is None else env
        max_calls = _positive_int(env, "MAX_API_CALLS")
        max_tokens = _positive_int(env, "MAX_API_TOKENS")
        if not is_local and (
            env.get("ALLOW_PAID_API") != "1" or max_calls is None or max_tokens is None
        ):
            raise PaidAPINotAllowed(
                "non-local LLM endpoint refused: "
                "set ALLOW_PAID_API=1, MAX_API_CALLS and MAX_API_TOKENS"
            )
        return cls(is_local=is_local, max_calls=max_calls, max_tokens=max_tokens)

    def check(self, prompt_tokens_est: int, max_completion_tokens: int) -> None:
        if self.max_calls is not None and self.calls + 1 > self.max_calls:
            raise BudgetExceeded(f"call cap reached ({self.calls}/{self.max_calls})")
        worst = self.tokens + prompt_tokens_est + max_completion_tokens
        if self.max_tokens is not None and worst > self.max_tokens:
            raise BudgetExceeded(f"token cap would be exceeded ({worst} > {self.max_tokens})")

    def record(self, prompt_tokens_est: int, completion_tokens_est: int) -> None:
        self.calls += 1
        self.tokens += prompt_tokens_est + completion_tokens_est


class TokenLogger:
    """Appends one JSON object per call to a JSONL file (default ``logs/api_usage.jsonl``)."""

    def __init__(self, path: str | Path = "logs/api_usage.jsonl"):
        self.path = Path(path)

    def log(
        self,
        *,
        backend: str,
        endpoint_host: str,
        model: str,
        prompt_tokens_est: int,
        completion_tokens_est: int,
        guard: BudgetGuard,
        usage_reported: dict | None = None,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "backend": backend,
            "endpoint_host": endpoint_host,
            "model": model,
            "prompt_tokens_est": prompt_tokens_est,
            "completion_tokens_est": completion_tokens_est,
            "cumulative_calls": guard.calls,
            "cumulative_tokens_est": guard.tokens,
            "usage_reported": usage_reported,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
