from __future__ import annotations

import json
from pathlib import Path

import pytest

from kgrerank.kg.view import KGView
from kgrerank.schema import read_jsonl

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def toy_kg_dict() -> dict:
    return json.loads((FIX / "toy_kg.json").read_text(encoding="utf-8"))


@pytest.fixture
def toy_kg(toy_kg_dict: dict) -> KGView:
    return KGView.from_dict(toy_kg_dict)


@pytest.fixture
def toy_examples():
    return read_jsonl(FIX / "toy_examples.jsonl")


class PickRNG:
    """Deterministic stand-in for random.Random: choice() returns the first item matching pred."""

    def __init__(self, pred=lambda x: True):
        self.pred = pred

    def choice(self, seq):
        for x in seq:
            if self.pred(x):
                return x
        raise AssertionError(f"no option matches in {seq!r}")
