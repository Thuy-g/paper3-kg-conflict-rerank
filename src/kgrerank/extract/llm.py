"""LLM claim extractor: asks for one JSON claim about the question; never a guess.

Input: the question and one passage only (no reference answer, gold labels or other passages).
Statuses: ok | no_claim (valid empty JSON) | parse_error | truncated | thinking_output |
backend_error. Only "ok" yields a Claim.
"""

from __future__ import annotations

import json
import re

from kgrerank.extract.claims import Claim
from kgrerank.kg.time import Interval, year_period, year_range
from kgrerank.llm.base import ChatMessage, LLMBackend

PROMPT_V1 = (
    "Question: {question}\nPassage: {passage}\n"
    "Extract the single claim of the passage that answers or relates to the question. Reply with "
    'JSON only: {{"subject": str, "relation": str, "object": str, "year_start": int|null, '
    '"year_end": int|null, "year": int|null}}. Use null when the passage states no time. '
    "Reply with {{}} if the passage contains no such claim."
)
_JSON = re.compile(r"\{.*\}", re.S)


class LLMClaimExtractor:
    name = "llm_extract_v1"

    def __init__(
        self,
        backend: LLMBackend,
        prompt: str = PROMPT_V1,
        max_tokens: int = 256,
        temperature: float = 0.0,
        seed: int | None = 0,
    ):
        self.backend, self.prompt, self.max_tokens = backend, prompt, max_tokens
        self.temperature, self.seed = temperature, seed

    def extract_with_status(self, pid: str, text: str, question: str) -> tuple[Claim | None, str]:
        msg = self.prompt.format(question=question, passage=text)
        resp = self.backend.chat(
            [ChatMessage("user", msg)],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            seed=self.seed,
            role="extract",
        )
        if resp.status != "ok":
            return None, resp.status
        m = _JSON.search(resp.text)
        if not m:
            return None, "parse_error"
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None, "parse_error"
        if d == {}:
            return None, "no_claim"
        if not isinstance(d, dict) or not all(
            isinstance(d.get(k), str) and d[k].strip() for k in ("subject", "relation", "object")
        ):
            return None, "parse_error"

        def yr(key: str):
            v = d.get(key)
            return year_range(v) if isinstance(v, int) else None

        time = None
        if isinstance(d.get("year"), int):
            time = year_period(d["year"])  # "in 1950" = the whole year, as in the pattern extractor
        elif yr("year_start") or yr("year_end"):
            time = Interval(yr("year_start"), yr("year_end"))
        claim = Claim(
            pid,
            d["subject"].strip(),
            d["relation"].strip().lower(),
            d["object"].strip(),
            time,
            "",
            self.name,
        )
        return claim, "ok"

    def extract(self, pid: str, text: str, question: str = "") -> Claim | None:
        return self.extract_with_status(pid, text, question)[0]
