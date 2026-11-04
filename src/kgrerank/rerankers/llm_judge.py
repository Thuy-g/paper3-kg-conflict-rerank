"""LLM-only passage judge baseline: asks an LLM to label each top-m passage, drops CONTRADICTING.

This is the 'LLM conflict filter' family used to measure false conflict filtering (G7). The prompt
is deliberately neutral and uses no KG information. With ``MockLLM`` it only exercises plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass

from kgrerank.llm.base import ChatMessage, LLMBackend
from kgrerank.rerankers.base import Ranking, Reranker
from kgrerank.schema import Decision, Example

PROMPT_V0 = (
    "Question: {question}\n"
    "Passage: {passage}\n"
    "Does the passage support an answer to the question that is COMPATIBLE with other evidence, "
    "CONTRADICTING other evidence, IRRELEVANT to the question, or UNKNOWN? "
    "Reply with exactly one word: COMPATIBLE, CONTRADICTING, IRRELEVANT or UNKNOWN."
)


def parse_decision(text: str) -> Decision:
    head = text.strip().split()[0].strip(".,:;!\"'").upper() if text.strip() else ""
    try:
        return Decision(head)
    except ValueError:
        return Decision.UNKNOWN


@dataclass
class LLMJudgeFilter:
    base: Reranker
    backend: LLMBackend
    top_m: int = 10
    drop: tuple[Decision, ...] = (Decision.CONTRADICTING,)
    prompt: str = PROMPT_V0
    seed: int | None = 42
    name: str = "llm_judge"

    def rank(self, example: Example) -> Ranking:
        base = self.base.rank(example)
        removed = set(base.removed)
        calls = 0
        for pid in base.order[: self.top_m]:
            cand = example.candidate(pid)
            msg = self.prompt.format(
                question=example.question, passage=f"{cand.title}: {cand.text}"
            )
            resp = self.backend.chat([ChatMessage("user", msg)], max_tokens=4, seed=self.seed)
            calls += 1
            if parse_decision(resp.text) in self.drop:
                removed.add(pid)
        order = tuple(pid for pid in base.order if pid not in removed)
        return Ranking(order=order, removed=frozenset(removed), scores=base.scores, llm_calls=calls)
