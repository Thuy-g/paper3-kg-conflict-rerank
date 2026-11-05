"""BM25 over the candidate pool of each question (pure Python, deterministic).

IDF is computed within the pool, a common approximation when reranking a fixed pool without
access to corpus statistics: idf(t) = ln(1 + (N - df + 0.5) / (df + 0.5)) (non-negative variant).
Tokenisation: lower-case ``\\w+`` tokens; title and text are concatenated.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from kgrerank.rerankers.base import Ranking, sort_by_score
from kgrerank.schema import Example

_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def bm25_scores(
    query: str, docs: dict[str, str], k1: float = 1.5, b: float = 0.75
) -> dict[str, float]:
    toks = {pid: tokenize(text) for pid, text in docs.items()}
    n = len(toks)
    avgdl = (sum(len(t) for t in toks.values()) / n) if n else 0.0
    df: Counter[str] = Counter()
    for t in toks.values():
        df.update(set(t))
    q_terms = tokenize(query)
    scores: dict[str, float] = {}
    for pid, t in toks.items():
        tf = Counter(t)
        dl = len(t)
        s = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = math.log(1.0 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1.0 - b + b * (dl / avgdl if avgdl else 0.0))
            s += idf * tf[term] * (k1 + 1.0) / denom
        scores[pid] = s
    return scores


@dataclass
class BM25Reranker:
    k1: float = 1.5
    b: float = 0.75
    name: str = "bm25"

    def rank(self, example: Example) -> Ranking:
        docs = {c.pid: f"{c.title} {c.text}" for c in example.candidates}
        scores = bm25_scores(example.question, docs, self.k1, self.b)
        order = sort_by_score(scores, [c.pid for c in example.candidates])
        return Ranking(order=order, scores=scores)
