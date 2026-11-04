"""Pattern extractor for the synthetic templates of kgrerank.perturb (tests and smoke only).

Real passages need the LLM extractor; this one is deliberately narrow and returns None for any
sentence that does not match a template exactly.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from kgrerank.extract.claims import Claim
from kgrerank.kg.time import Interval, TimeRange, year_period, year_range

_YEAR = r"(?P<{name}>\d{{3,4}}(?:s)?)"
_GENERIC_REL = r"[a-z][a-z ]*?"


def _patterns(rel: str) -> list[re.Pattern[str]]:
    body = rf"the (?P<rel>{rel}) of (?P<s>.+?) (?:is|was) (?P<o>.+?)(?: \((?P<note>[^)]*)\))?\.$"
    return [
        re.compile(r"^(?P<head>[^:]+?) \((?P<desc>[^)]+)\): " + body, re.I),
        re.compile(
            rf"^From {_YEAR.format(name='start')} to {_YEAR.format(name='end')}, " + body, re.I
        ),
        re.compile(rf"^From {_YEAR.format(name='start')}, " + body, re.I),
        re.compile(rf"^Until {_YEAR.format(name='end')}, " + body, re.I),
        re.compile(rf"^In {_YEAR.format(name='point')}, " + body, re.I),
        re.compile(r"^" + body, re.I),
    ]


def _year(text: str | None):
    if not text:
        return None
    y = int(text.rstrip("s"))
    if text.endswith("s"):
        return TimeRange((y, 1, 1), (y + 9, 12, 31))
    return year_range(y)


class PatternExtractor:
    """``relations``: known relation labels (an extraction lexicon, not KG facts). Labels such as
    "place of birth" contain "of", so without the lexicon the split is ambiguous."""

    name = "pattern_v0"

    def __init__(self, relations: Sequence[str] = ()):
        labels = sorted({r.lower() for r in relations if r}, key=lambda r: (-len(r), r))
        rel = "|".join(re.escape(r) for r in labels) if labels else _GENERIC_REL
        self.patterns = _patterns(rel)

    def extract(self, pid: str, text: str) -> Claim | None:
        for pat in self.patterns:
            m = pat.match(text.strip())
            if not m:
                continue
            g = m.groupdict()
            time = None
            if g.get("point") and not g["point"].endswith("s"):
                time = year_period(int(g["point"]))
            elif g.get("point"):
                time = Interval(_year(g["point"]), _year(g["point"]))
            elif g.get("start") or g.get("end"):
                time = Interval(_year(g.get("start")), _year(g.get("end")))
            note = g.get("desc") or g.get("note") or ""
            return Claim(
                pid,
                g["s"].strip(),
                g["rel"].strip().lower(),
                g["o"].strip(),
                time,
                note.strip(),
                self.name,
            )
        return None
