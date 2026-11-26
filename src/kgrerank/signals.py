"""Six separate KG signals: the input/output contract for Phase C methods (docs/PLAN.md B.0).

These are containers only. Nothing in this module (or anywhere in the Phase B harness) combines
signals into a decision. Wikidata constraints are guidance with exceptions, not axioms, so a
``cardinality_constraint`` value never implies a contradiction by itself. Mutability and
cardinality are independent: multi-value does not imply mutable, single-value does not imply
stable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from enum import Enum, StrEnum
from typing import Any


@dataclass(frozen=True)
class Basis:
    """Provenance of a signal value, e.g. ``wikidata:P19#P2302`` or ``manual:mutability_v0``."""

    source: str
    refs: tuple[str, ...] = ()
    note: str = ""


class Cardinality(StrEnum):
    SINGLE_VALUE = "single_value"  # Q19474404
    SINGLE_BEST_VALUE = "single_best_value"  # Q52060874
    MULTI_VALUE = "multi_value"  # Q21510857
    NONE_DECLARED = "none_declared"
    UNKNOWN = "unknown"


class Mutability(StrEnum):
    STABLE = "stable"
    MUTABLE = "mutable"
    UNKNOWN = "unknown"


class TemporalRelation(StrEnum):
    OVERLAP = "overlap"
    DISJOINT = "disjoint"
    UNKNOWN = "unknown"


class Identity(StrEnum):
    SAME = "same"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


class RelationSemantics(StrEnum):
    SAME = "same"
    INVERSE = "inverse"
    SUBPROPERTY = "subproperty"
    RELATED_DIFFERENT = "related_different"
    UNRELATED = "unrelated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CardinalitySignal:
    value: Cardinality
    basis: Basis
    status: str | None = None  # "mandatory" | "suggestion" | None (P2316 absent)
    separators: tuple[str, ...] = ()  # P4155
    exceptions: tuple[str, ...] = ()  # P2303
    subject_is_exception: bool | None = None


@dataclass(frozen=True)
class MutabilitySignal:
    value: Mutability
    basis: Basis


@dataclass(frozen=True)
class TemporalOverlapSignal:
    value: TemporalRelation
    basis: Basis


@dataclass(frozen=True)
class QualifierEvidenceSignal:
    qualifiers: tuple[str, ...]
    basis: Basis
    rank: str | None = None  # "preferred" | "normal" | "deprecated"
    n_references: int | None = None


@dataclass(frozen=True)
class EntityIdentitySignal:
    value: Identity
    evidence_kind: str  # qid | label | alias | historical_name | redirect | type_mismatch
    basis: Basis


@dataclass(frozen=True)
class RelationSemanticsSignal:
    value: RelationSemantics
    basis: Basis


SIGNAL_NAMES: tuple[str, ...] = (
    "cardinality_constraint",
    "mutability_class",
    "temporal_overlap",
    "qualifier_evidence",
    "entity_identity",
    "relation_semantics",
)


@dataclass(frozen=True)
class SignalBundle:
    """All six signals for one (question, passage) pair; every field is optional and independent."""

    cardinality_constraint: CardinalitySignal | None = None
    mutability_class: MutabilitySignal | None = None
    temporal_overlap: TemporalOverlapSignal | None = None
    qualifier_evidence: QualifierEvidenceSignal | None = None
    entity_identity: EntityIdentitySignal | None = None
    relation_semantics: RelationSemanticsSignal | None = None

    def available(self) -> tuple[str, ...]:
        """Names of the signals that are present (used for signal-availability ablations)."""
        return tuple(f.name for f in fields(self) if getattr(self, f.name) is not None)

    def to_dict(self) -> dict[str, Any]:
        def enc(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: enc(v) for k, v in obj.items()}
            if isinstance(obj, list | tuple):
                return [enc(v) for v in obj]
            return obj

        return {
            f.name: (None if getattr(self, f.name) is None else enc(asdict(getattr(self, f.name))))
            for f in fields(self)
        }
