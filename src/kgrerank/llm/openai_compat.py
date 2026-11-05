"""OpenAI-compatible chat backend (default: local vLLM at http://localhost:8000/v1).

The HTTP transport is injectable so tests never touch the network. The API key is read from an
environment variable at call time and is never logged or stored on the instance.
``extra_body`` is merged into every request (e.g. {"chat_template_kwargs": {"enable_thinking":
false}} for Qwen3 non-thinking mode on vLLM — field name [UNVERIFIED], see reports/05);
``sampling`` adds generation settings such as top_p, top_k, min_p, presence_penalty.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from kgrerank.llm.base import ChatMessage, Completion, LLMBackend, is_local_endpoint
from kgrerank.llm.budget import BudgetGuard, TokenLogger

Transport = Callable[[str, dict, dict, float], dict]


def urllib_transport(url: str, headers: dict, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # URL comes from config
        return json.loads(resp.read().decode("utf-8"))


class OpenAICompatLLM(LLMBackend):
    name = "openai_compat"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8000/v1",
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 120.0,
        logger: TokenLogger | None = None,
        env: Mapping[str, str] | None = None,
        transport: Transport | None = None,
        extra_body: Mapping[str, Any] | None = None,
        sampling: Mapping[str, Any] | None = None,
    ):
        self._env = os.environ if env is None else env
        guard = BudgetGuard.from_env(is_local_endpoint(base_url), self._env)  # may refuse
        super().__init__(model, guard, logger, host=urlparse(base_url).hostname or "")
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.extra_body = dict(extra_body or {})
        self.sampling = dict(sampling or {})
        self._transport = transport or urllib_transport

    def _complete(
        self, messages: Sequence[ChatMessage], max_tokens: int, temperature: float, seed: int | None
    ) -> Completion:
        headers = {"Content-Type": "application/json"}
        key = self._env.get(self.api_key_env)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **self.sampling,
            **self.extra_body,
        }
        if seed is not None:
            body["seed"] = seed
        data = self._transport(f"{self.base_url}/chat/completions", headers, body, self.timeout)
        choice = data["choices"][0]
        usage = data.get("usage")
        return Completion(
            choice["message"].get("content") or "",
            choice.get("finish_reason"),
            dict(usage) if isinstance(usage, dict) else None,
        )
