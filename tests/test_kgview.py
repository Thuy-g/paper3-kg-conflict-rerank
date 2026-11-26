from __future__ import annotations

import pytest

from kgrerank.kg.view import Q_SINGLE_BEST_VALUE, Q_SINGLE_VALUE, KGView


def test_basic_queries(toy_kg):
    assert toy_kg.label("Z3") == "Port Avalon"
    assert toy_kg.types("Z3") == {"Z101"}
    assert toy_kg.entities_named("port avalon") == {"Z3", "Z8", "Z9", "Z17"}
    assert toy_kg.entities_named("Avalon City") == {"Z3"}
    all_p6 = toy_kg.item_values("Z3", "P6", include_deprecated=True)
    assert "Z15" in all_p6
    assert "Z15" not in toy_kg.item_values("Z3", "P6")


def test_intervals_and_ranks(toy_kg):
    sts = {st.value.value: st for st in toy_kg.statements_of("Z3", "P6")}
    iv = sts["Z10"].interval()
    assert iv.start.lo == (2005, 1, 1) and iv.end.hi == (2012, 12, 31)
    assert sts["Z11"].rank == "preferred" and sts["Z11"].interval().end is None
    assert sts["Z15"].rank == "deprecated" and not sts["Z15"].has_temporal_qualifier()


def test_ancestors_and_relations(toy_kg):
    paths = toy_kg.ancestor_paths("Z3")
    assert set(paths) == {"Z5", "Z6"} and len(paths["Z6"]) == 2
    assert toy_kg.declared_inverse("P22", "P40") is True
    assert toy_kg.declared_inverse("P19", "P20") is False
    assert toy_kg.declared_inverse("P9998", "P9999") is None  # unknown, not False
    assert toy_kg.is_subproperty("P19", "P20") is False


def test_constraints_kept_as_data(toy_kg):
    p19 = toy_kg.property("P19")
    (c,) = p19.constraints_of(Q_SINGLE_VALUE)
    assert c.exceptions == ("Z99",) and c.status is None
    assert toy_kg.property("P6").constraints_of(Q_SINGLE_BEST_VALUE)
    assert p19.mutability == "stable" and "synthetic" in p19.mutability_basis


def test_bad_format(toy_kg_dict):
    with pytest.raises(ValueError, match="format"):
        KGView.from_dict({**toy_kg_dict, "format": "other"})
    bad = dict(toy_kg_dict)
    bad["statements"] = [
        {"s": "Z1", "p": "P31", "v": {"kind": "item", "value": "Z100"}, "rank": "x"}
    ]
    with pytest.raises(ValueError, match="rank"):
        KGView.from_dict(bad)
