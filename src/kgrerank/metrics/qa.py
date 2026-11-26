"""Exact match and token F1 with SQuAD-style normalisation; max over gold answers."""

from __future__ import annotations

import re
import string
from collections import Counter
from collections.abc import Sequence

_ARTICLES = re.compile(r"\b(a|an|the)\b", re.UNICODE)
_PUNCT = set(string.punctuation)


def normalize_answer(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in _PUNCT)
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def exact_match(prediction: str, answers: Sequence[str]) -> float | None:
    if not answers:
        return None
    pred = normalize_answer(prediction)
    return float(any(pred == normalize_answer(a) for a in answers))


def _f1(pred: str, gold: str) -> float:
    p, g = normalize_answer(pred).split(), normalize_answer(gold).split()
    if not p or not g:
        return float(p == g)
    common = Counter(p) & Counter(g)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision, recall = overlap / len(p), overlap / len(g)
    return 2 * precision * recall / (precision + recall)


def f1_score(prediction: str, answers: Sequence[str]) -> float | None:
    if not answers:
        return None
    return max(_f1(prediction, a) for a in answers)
