"""LLM conflict typers (baselines and G2+ fallback) with explicit information access.

No system ever receives the dataset reference answer, gold labels, supporting-fact flags or
annotation reasons. Two prompts:

single_passage_v1  question + target passage (+ the model's parametric knowledge)
inter_context_v1   question + target passage + up to ``context_m`` other passages of the same pool,
                   taken in the order of the base relevance ranking (target excluded), each cut to
                   ``context_chars`` characters

Outputs are JSON {"decision": ..., "reason": ...}. A call that is truncated, unparsable, shows
thinking output or fails at the backend is recorded with that status and decision None; it is
never turned into a valid UNKNOWN decision.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from kgrerank.llm.base import ChatMessage, LLMBackend, summarize_events
from kgrerank.rerankers.base import Ranking, Reranker
from kgrerank.schema import Decision, Example

_JSON_INSTR = (  # braces doubled: the prompts are str.format templates
    'Reply with JSON only: {{"decision": "COMPATIBLE" | "CONTRADICTING" | "IRRELEVANT" | '
    '"UNKNOWN", "reason": "<one short sentence>"}}'
)
PROMPTS = {
    "single_passage_v1": (
        "Question: {question}\n\nPassage:\n{passage}\n\n"
        "Judge the passage using only the question, the passage and your general knowledge.\n"
        "COMPATIBLE: the passage is about what the question asks and nothing in it is false for "
        "the question's scope as far as you know.\n"
        "CONTRADICTING: the passage is about what the question asks and states something you "
        "believe is false for the question's scope.\n"
        "IRRELEVANT: the passage is not about what the question asks.\n"
        "UNKNOWN: you cannot decide.\n" + _JSON_INSTR
    ),
    "inter_context_v1": (
        "Question: {question}\n\nTarget passage:\n{passage}\n\n"
        "Other retrieved passages:\n{context}\n\n"
        "Decide how the TARGET passage relates to the OTHER passages for this question.\n"
        "COMPATIBLE: it is about what the question asks and can be true together with the other "
        "passages.\n"
        "CONTRADICTING: it is about what the question asks and cannot be true together with at "
        "least one other passage about the same entity, relation, time and place.\n"
        "IRRELEVANT: it is not about what the question asks.\n"
        "UNKNOWN: you cannot decide from these passages.\n"
        "Different values are not a contradiction when they refer to different times, places, "
        "entities or levels of detail, when one is another name of the other, or when the "
        "relation can have several values. Missing dates do not mean the same time.\n" + _JSON_INSTR
    ),
}
ACCESS = {
    "single_passage_v1": {
        "question": True,
        "target_passage": True,
        "other_passages": False,
        "parametric_knowledge": True,
    },
    "inter_context_v1": {
        "question": True,
        "target_passage": True,
        "other_passages": "top-m of base ranking, target excluded, truncated",
        "parametric_knowledge": True,
    },
}
NEVER_ACCESSED = ("reference_answer", "gold_labels", "supporting_fact_flags", "annotation_reasons")
_JSON = re.compile(r"\{.*\}", re.S)


@dataclass(frozen=True)
class LLMDecision:
    pid: str
    decision: Decision | None  # None unless status == "ok"
    status: str  # ok | parse_error | truncated | thinking_output | backend_error
    raw: str = ""


def parse_decision_json(text: str) -> tuple[Decision | None, str]:
    """Return (decision, "ok") or (None, "parse_error"). The label must be one of the four."""
    m = _JSON.search(text or "")
    if not m:
        return None, "parse_error"
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "parse_error"
    label = str(d.get("decision", "")).strip().upper() if isinstance(d, dict) else ""
    try:
        return Decision(label), "ok"
    except ValueError:
        return None, "parse_error"


@dataclass
class LLMTyper:
    backend: LLMBackend
    prompt: str = "inter_context_v1"
    max_tokens: int = 256
    temperature: float = 0.0
    seed: int | None = 0
    context_m: int = 5
    context_chars: int = 600
    role: str = "typer"

    def __post_init__(self) -> None:
        if self.prompt not in PROMPTS:
            raise ValueError(f"unknown prompt {self.prompt!r}")

    def information_access(self) -> dict[str, Any]:
        return {
            **ACCESS[self.prompt],
            "never": list(NEVER_ACCESSED),
            "context_m": self.context_m,
            "context_chars": self.context_chars,
        }

    def render(self, ex: Example, pid: str, context_order: Sequence[str]) -> str:
        cand = ex.candidate(pid)
        others = [p for p in context_order if p != pid][: self.context_m]
        context = (
            "\n".join(
                f"[{i}] {ex.candidate(p).title}: {ex.candidate(p).text[: self.context_chars]}"
                for i, p in enumerate(others, 1)
            )
            or "(none)"
        )
        return PROMPTS[self.prompt].format(
            question=ex.question, passage=f"{cand.title}: {cand.text}", context=context
        )

    def type_passages(
        self, ex: Example, pids: Sequence[str], context_order: Sequence[str]
    ) -> dict[str, LLMDecision]:
        out = {}
        for pid in pids:
            resp = self.backend.chat(
                [ChatMessage("user", self.render(ex, pid, context_order))],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                seed=self.seed,
                role=self.role,
            )
            if resp.status != "ok":
                out[pid] = LLMDecision(pid, None, resp.status, resp.text[:200])
                continue
            decision, status = parse_decision_json(resp.text)
            out[pid] = LLMDecision(pid, decision, status, resp.text[:200])
        return out


@dataclass
class LLMJudgeFilter:
    """LLM-only conflict filter: types the base top-m passages and removes CONTRADICTING ones."""

    base: Reranker
    typer: LLMTyper
    top_m: int = 10
    drop: tuple[Decision, ...] = (Decision.CONTRADICTING,)
    name: str = "llm_judge"
    last_decisions: dict[str, dict[str, LLMDecision]] = field(default_factory=dict)

    def rank(self, example: Example) -> Ranking:
        base = self.base.rank(example)
        start = len(self.typer.backend.events)
        decisions = self.typer.type_passages(example, base.order[: self.top_m], base.order)
        self.last_decisions[example.qid] = decisions
        removed = set(base.removed) | {p for p, d in decisions.items() if d.decision in self.drop}
        usage = summarize_events(self.typer.backend.events[start:])
        order = tuple(pid for pid in base.order if pid not in removed)
        return Ranking(
            order=order,
            removed=frozenset(removed),
            scores=base.scores,
            llm_calls=usage["calls"],
            llm_usage=usage,
        )
