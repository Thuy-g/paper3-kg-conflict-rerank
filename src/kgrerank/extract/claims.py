"""Structured claim extracted from one passage."""

from __future__ import annotations

from dataclasses import dataclass

from kgrerank.kg.time import Interval


@dataclass(frozen=True)
class Claim:
    pid: str
    subject: str  # surface mention
    relation: str  # surface relation label as written
    obj: str  # surface mention or literal
    time: Interval | None = None  # validity stated in the passage (None = not stated)
    note: str = ""  # parenthetical text, e.g. a disambiguating description
    extractor: str = ""
