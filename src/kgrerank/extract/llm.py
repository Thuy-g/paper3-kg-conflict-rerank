"""LLM claim extractor: asks for one JSON claim; anything invalid yields None (never a guess)."""

from __future__ import annotations

import json
import re

from kgrerank.extract.claims import Claim
from kgrerank.kg.time import Interval, year_period, year_range
from kgrerank.llm.base import ChatMessage, LLMBackend

PROMPT_V0 = (
    "Question: {question}\nPassage: {passage}\n"
    "Extract the single claim of the passage that answers or relates to the question. Reply with "
    'JSON only: {{"subject": str, "relation": str, "object": str, "year_start": int|null, '
    '"year_end": int|null, "year": int|null}}. Use null when the passage states no time. '
    "Reply with {{}} if the passage contains no such claim."
)
_JSON = re.compile(r"\{.*\}", re.S)


class LLMClaimExtractor:
    name = "llm_v0"

    def __init__(self, backend: LLMBackend, prompt: str = PROMPT_V0, max_tokens: int = 128):
        self.backend, self.prompt, self.max_tokens = backend, prompt, max_tokens
        self.calls = 0

    def extract(self, pid: str, text: str, question: str = "") -> Claim | None:
        msg = self.prompt.format(question=question, passage=text)
        resp = self.backend.chat([ChatMessage("user", msg)], max_tokens=self.max_tokens, seed=0)
        self.calls += 1
        m = _JSON.search(resp.text)
        if not m:
            return None
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        if not isinstance(d, dict) or not all(
            isinstance(d.get(k), str) and d[k].strip() for k in ("subject", "relation", "object")
        ):
            return None

        def yr(key: str):
            v = d.get(key)
            return year_range(v) if isinstance(v, int) else None

        time = None
        if isinstance(d.get("year"), int):
            time = year_period(d["year"])  # "in 1950" = the whole year, as in the pattern extractor
        elif yr("year_start") or yr("year_end"):
            time = Interval(yr("year_start"), yr("year_end"))
        return Claim(
            pid,
            d["subject"].strip(),
            d["relation"].strip().lower(),
            d["object"].strip(),
            time,
            "",
            self.name,
        )
