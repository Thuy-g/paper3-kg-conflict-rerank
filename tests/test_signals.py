from __future__ import annotations

from dataclasses import fields

from kgrerank.signals import (
    SIGNAL_NAMES,
    Basis,
    Cardinality,
    CardinalitySignal,
    Mutability,
    MutabilitySignal,
    SignalBundle,
)


def test_six_independent_signals_no_decision():
    names = tuple(f.name for f in fields(SignalBundle))
    assert names == SIGNAL_NAMES
    assert not hasattr(SignalBundle(), "decision")


def test_cardinality_and_mutability_are_independent():
    # multi-value + stable and single-value + mutable are both representable.
    for card, mut in [
        (Cardinality.MULTI_VALUE, Mutability.STABLE),
        (Cardinality.SINGLE_VALUE, Mutability.MUTABLE),
    ]:
        b = SignalBundle(
            cardinality_constraint=CardinalitySignal(card, Basis("test"), status="suggestion"),
            mutability_class=MutabilitySignal(mut, Basis("manual:test")),
        )
        assert b.available() == ("cardinality_constraint", "mutability_class")
        d = b.to_dict()
        assert d["cardinality_constraint"]["value"] == card.value
        assert d["mutability_class"]["value"] == mut.value
        assert d["temporal_overlap"] is None
