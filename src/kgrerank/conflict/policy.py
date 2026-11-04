"""Combination policy v0: an explicit, ordered rule table over separately computed signals.

Each verdict names the rule that fired. Confidences are fixed a priori in this file (not tuned on
any data). Constraints are soft evidence: a conflict needs *all* of
  same subject, same relation, different objects that no identity/hierarchy evidence reconciles,
  overlapping time, no exception for the subject, and a cardinality constraint;
and even then the confidence stays below 1. Unscoped statements on a mutable property, or any
missing signal, give "unknown" (to be passed to the LLM fallback or left UNKNOWN).

| rule | condition | relation |
|---|---|---|
| R-subject-different | subject identity DIFFERENT | unrelated |
| R-subject-unknown | subject identity UNKNOWN | unknown |
| R-relation-different | relation RELATED_DIFFERENT / UNRELATED | unrelated |
| R-relation-unknown | relation SUBPROPERTY / UNKNOWN | unknown |
| R-time-disjoint | claim time DISJOINT from the question time (or the reference) | consistent |
| R-object-same | object identity SAME | consistent |
| R-no-reference | no reference claim and time not disjoint | unknown |
| R-object-unknown | object identity UNKNOWN | unknown |
| R-hierarchy-coarser | object is a KG ancestor, no time-qualified edge | consistent |
| R-hierarchy-uncertain | ancestor via time-qualified edge, or object is finer | unknown |
| R-time-unknown | different objects, time UNKNOWN | unknown |
| R-mutable-unscoped | overlap only assumed (both unscoped), property annotated mutable | unknown |
| R-exception | subject listed as a constraint exception | unknown |
| R-single-value / R-single-best-value | overlap, cardinality constraint present | conflict |
| R-cardinality-open | overlap, multi-value / none declared / unknown | unknown |
"""

from __future__ import annotations

from dataclasses import dataclass

from kgrerank.conflict.signals import PairSignals
from kgrerank.signals import Cardinality, Identity, Mutability, RelationSemantics, TemporalRelation

POLICY_VERSION = "policy_v0.1"
CONFIDENCE = {
    "unrelated": 0.6,
    "same": 0.8,
    "coarser": 0.7,
    "time_disjoint": 0.7,
    ("single_value", "mandatory"): 0.7,
    ("single_value", "other"): 0.6,
    ("single_best_value", "other"): 0.5,
    ("single_best_value", "suggestion"): 0.4,
    "assumed_overlap_penalty": 0.1,
}


@dataclass(frozen=True)
class PairVerdict:
    relation: str  # consistent | conflict | unrelated | unknown
    rule: str
    confidence: float
    reasons: tuple[str, ...] = ()


def decide_pair(s: PairSignals) -> PairVerdict:
    b = s.bundle
    assert b.entity_identity and b.relation_semantics and b.temporal_overlap
    assert b.cardinality_constraint and b.mutability_class
    if s.subject_identity.value is Identity.DIFFERENT:
        homonym = s.subject_identity.evidence_kind in ("description", "name_of_other_entities")
        return PairVerdict(
            "unrelated",
            "R-subject-different",
            CONFIDENCE["unrelated"],
            ("homonym",) if homonym else ("entity_identity_mismatch",),
        )
    if s.subject_identity.value is Identity.UNKNOWN:
        return PairVerdict("unknown", "R-subject-unknown", 0.0)
    rel = b.relation_semantics.value
    if rel in (RelationSemantics.RELATED_DIFFERENT, RelationSemantics.UNRELATED):
        return PairVerdict(
            "unrelated", "R-relation-different", CONFIDENCE["unrelated"], ("predicate_mismatch",)
        )
    if rel in (RelationSemantics.SUBPROPERTY, RelationSemantics.UNKNOWN):
        return PairVerdict("unknown", "R-relation-unknown", 0.0)
    extra = ("inverse_relation",) if rel is RelationSemantics.INVERSE else ()
    v = _objects(s)
    return PairVerdict(v.relation, v.rule, v.confidence, extra + v.reasons)


def _objects(s: PairSignals) -> PairVerdict:
    b = s.bundle
    ident, t = b.entity_identity, b.temporal_overlap
    if t.value is TemporalRelation.DISJOINT:
        return PairVerdict(
            "consistent", "R-time-disjoint", CONFIDENCE["time_disjoint"], ("temporal_scope",)
        )
    if ident.value is Identity.SAME:
        reasons = {"alias": ("alias",), "name_statement": ("historical_identity",)}.get(
            ident.evidence_kind, ()
        )
        return PairVerdict("consistent", "R-object-same", CONFIDENCE["same"], reasons)
    if ident.value is Identity.UNKNOWN:
        rule = "R-no-reference" if ident.evidence_kind == "no_reference" else "R-object-unknown"
        return PairVerdict("unknown", rule, 0.0)
    if ident.evidence_kind.startswith("hierarchy"):
        if ident.evidence_kind == "hierarchy_ancestor" and ident.basis.note != "timed_edges":
            return PairVerdict(
                "consistent",
                "R-hierarchy-coarser",
                CONFIDENCE["coarser"],
                ("geographic_granularity",),
            )
        return PairVerdict("unknown", "R-hierarchy-uncertain", 0.0, ("geographic_granularity",))
    if t.value is TemporalRelation.UNKNOWN:
        return PairVerdict("unknown", "R-time-unknown", 0.0)
    assumed = t.basis.note == "both_unscoped"
    if assumed and b.mutability_class.value is Mutability.MUTABLE:
        return PairVerdict("unknown", "R-mutable-unscoped", 0.0, ("temporal_scope",))
    card = b.cardinality_constraint
    if card.subject_is_exception:
        return PairVerdict("unknown", "R-exception", 0.0)
    if card.value is Cardinality.SINGLE_VALUE:
        key = ("single_value", "mandatory" if card.status == "mandatory" else "other")
        rule = "R-single-value"
    elif card.value is Cardinality.SINGLE_BEST_VALUE:
        key = ("single_best_value", "suggestion" if card.status == "suggestion" else "other")
        rule = "R-single-best-value"
    else:
        return PairVerdict("unknown", "R-cardinality-open", 0.0)
    conf = CONFIDENCE[key] - (CONFIDENCE["assumed_overlap_penalty"] if assumed else 0.0)
    return PairVerdict("conflict", rule, round(conf, 3), ("counterfactual",))
