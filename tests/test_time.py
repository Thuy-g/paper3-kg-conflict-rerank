from __future__ import annotations

from kgrerank.kg.time import Interval, parse_wikidata_time, temporal_relation, year_range
from kgrerank.signals import TemporalRelation as R


def test_parse_precisions():
    assert parse_wikidata_time("+1976-07-02T00:00:00Z", 11).lo == (1976, 7, 2)
    m = parse_wikidata_time("+1976-02-00T00:00:00Z", 10)
    assert (m.lo, m.hi) == ((1976, 2, 1), (1976, 2, 29))
    y = parse_wikidata_time("+1976-00-00T00:00:00Z", 9)
    assert (y.lo, y.hi) == ((1976, 1, 1), (1976, 12, 31))
    d = parse_wikidata_time("+1990-00-00T00:00:00Z", 8)
    assert (d.lo, d.hi) == ((1990, 1, 1), (1999, 12, 31))
    assert parse_wikidata_time("+1900-00-00T00:00:00Z", 7) is None  # century: too coarse
    assert parse_wikidata_time("-0044-03-15T00:00:00Z", 11).lo == (-44, 3, 15)
    assert parse_wikidata_time("garbage", 11) is None


def test_temporal_relation_three_valued():
    a = Interval(year_range(2005), year_range(2012))
    assert temporal_relation(a, Interval.point(year_range(2010))) is R.OVERLAP
    assert temporal_relation(a, Interval.point(year_range(2014))) is R.DISJOINT
    open_end = Interval(year_range(2012), None)  # end unknown, not open
    assert temporal_relation(open_end, Interval.point(year_range(2010))) is R.DISJOINT
    assert temporal_relation(open_end, Interval.point(year_range(2015))) is R.UNKNOWN
    # Imprecise endpoints: a ends in 2012 and b starts in 2012, order within the year unknown.
    touching = Interval(year_range(2012), year_range(2013))
    assert temporal_relation(a, touching) is R.UNKNOWN
    assert temporal_relation(a, Interval(year_range(2010), year_range(2011))) is R.OVERLAP
    # A year-precision point at the boundary year is not guaranteed inside the interval.
    assert temporal_relation(a, Interval.point(year_range(2012))) is R.UNKNOWN
    assert (
        temporal_relation(Interval.point(year_range(2010)), Interval.point(year_range(2010)))
        is R.UNKNOWN
    )
    assert temporal_relation(Interval(None, None), a) is R.UNKNOWN
    assert temporal_relation(Interval.unbounded(), a) is R.OVERLAP
