"""Wikidata-style time values and three-valued interval comparison.

A Wikidata time value is a string such as ``+1976-07-02T00:00:00Z`` with a precision
(9 = year, 10 = month, 11 = day, 8 = decade). Each time point is turned into a closed range of
calendar dates ``[lo, hi]`` (as ``(year, month, day)`` tuples, so BCE years work). Precision below
decade is treated as unknown.

Missing interval endpoints mean *unknown*, not *open*: a statement with a start time but no end
time may still hold or may simply lack the end time. Comparisons therefore return ``OVERLAP`` or
``DISJOINT`` only when the known endpoints force the answer, and ``UNKNOWN`` otherwise.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass

from kgrerank.signals import TemporalRelation

DateTuple = tuple[int, int, int]
_TIME_RE = re.compile(r"^([+-])(\d{1,16})-(\d{2})-(\d{2})T")
MIN_DATE: DateTuple = (-(10**9), 1, 1)
MAX_DATE: DateTuple = (10**9, 12, 31)


@dataclass(frozen=True)
class TimeRange:
    """Closed range of calendar dates covered by one (imprecise) time value."""

    lo: DateTuple
    hi: DateTuple


def _last_day(year: int, month: int) -> int:
    # calendar handles proleptic Gregorian years >= 1; use a leap-year-neutral fallback otherwise.
    if year >= 1:
        return calendar.monthrange(year, month)[1]
    return 29 if month == 2 else (30 if month in (4, 6, 9, 11) else 31)


def parse_wikidata_time(value: str, precision: int) -> TimeRange | None:
    """Parse a Wikidata time string; return ``None`` when it cannot be placed on the calendar."""
    m = _TIME_RE.match(value)
    if m is None:
        return None
    sign, y, mo, d = m.groups()
    year = int(y) * (-1 if sign == "-" else 1)
    month, day = int(mo), int(d)
    if precision >= 11 and month and day:
        return TimeRange((year, month, day), (year, month, day))
    if precision == 10 and month:
        return TimeRange((year, month, 1), (year, month, _last_day(year, month)))
    if precision == 9:
        return TimeRange((year, 1, 1), (year, 12, 31))
    if precision == 8:
        start = year - (year % 10)
        return TimeRange((start, 1, 1), (start + 9, 12, 31))
    return None


def year_range(year: int) -> TimeRange:
    return TimeRange((year, 1, 1), (year, 12, 31))


def year_period(year: int) -> Interval:
    """The calendar year as a period with exact boundaries ("in 2010" = all of 2010)."""
    return Interval(
        TimeRange((year, 1, 1), (year, 1, 1)), TimeRange((year, 12, 31), (year, 12, 31))
    )


@dataclass(frozen=True)
class Interval:
    """Validity interval; ``None`` endpoints are unknown (not open).

    ``is_point`` marks a single (possibly imprecise) moment: its start and end are the *same*
    unknown date inside ``start``, which matters for guaranteed-overlap reasoning.
    """

    start: TimeRange | None
    end: TimeRange | None
    is_point: bool = False

    @classmethod
    def point(cls, t: TimeRange) -> Interval:
        return cls(start=t, end=t, is_point=True)

    @classmethod
    def unbounded(cls) -> Interval:
        """Explicitly open on both sides (for example 'at any time'); differs from unknown."""
        return cls(start=TimeRange(MIN_DATE, MIN_DATE), end=TimeRange(MAX_DATE, MAX_DATE))

    def is_known(self) -> bool:
        return self.start is not None and self.end is not None


def temporal_relation(a: Interval, b: Interval) -> TemporalRelation:
    """Three-valued overlap test between two validity intervals.

    DISJOINT if one interval certainly ends before the other certainly starts; OVERLAP if all
    endpoints are known and every realisation of the imprecise endpoints overlaps; UNKNOWN
    otherwise (including all cases with missing endpoints that do not force DISJOINT).
    """
    if a.end is not None and b.start is not None and a.end.hi < b.start.lo:
        return TemporalRelation.DISJOINT
    if b.end is not None and a.start is not None and b.end.hi < a.start.lo:
        return TemporalRelation.DISJOINT
    if not (a.is_known() and b.is_known()):
        return TemporalRelation.UNKNOWN
    assert a.start and a.end and b.start and b.end
    if a.is_point and b.is_point:
        same_day = a.start.lo == a.start.hi == b.start.lo == b.start.hi
        return TemporalRelation.OVERLAP if same_day else TemporalRelation.UNKNOWN
    if a.is_point or b.is_point:
        pt, iv = (a, b) if a.is_point else (b, a)
        assert pt.start and iv.start and iv.end
        # Every possible date of the point must lie inside every possible realisation of iv.
        if iv.start.hi <= pt.start.lo and pt.start.hi <= iv.end.lo:
            return TemporalRelation.OVERLAP
        return TemporalRelation.UNKNOWN
    # Two intervals: worst case is the latest possible starts and the earliest possible ends.
    if max(a.start.hi, b.start.hi) <= min(a.end.lo, b.end.lo):
        return TemporalRelation.OVERLAP
    return TemporalRelation.UNKNOWN
