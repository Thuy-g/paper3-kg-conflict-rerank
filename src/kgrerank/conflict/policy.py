"""Combination policy v0.2: an explicit, ordered rule table over separately computed signals.

Each verdict names the rule that fired. Confidences are fixed a priori here, not tuned on data.

Changes from v0.1 (2026-11-05, before any natural-data G2+ result exists):
* single-best-value (Q52060874) no longer yields a conflict. The official constraint page says the
  property "may have any number of values, but exactly one of them ... should have preferred
  rank": it describes ranking, not mutual exclusivity (reports/02d §1).
* two statements without dates are no longer assumed to be about the same time; time matters
  unless the property is annotated stable (mutability is a separate signal).
* single-value with separator qualifiers (P4155) gives unknown: values may legitimately differ in
  those qualifiers, which passages usually do not state.
* deprecated constraint statements are ignored (KGView loader).
A conflict therefore needs all of: same subject (unique link), same relation, objects that are
different entities not reconciled by identity or hierarchy, time established as overlapping or a
stable property, a single-value constraint without separators, and no exception for the subject.
Even then confidence stays below 1. Everything else is unknown and goes to the LLM fallback.

| rule | condition | relation |
|---|---|---|
| R-subject-different | subject identity DIFFERENT | unrelated |
| R-subject-unknown | subject identity UNKNOWN (unlinked or ambiguous) | unknown |
| R-relation-different | relation known to differ (frames are single-fact) | unrelated |
| R-relation-unknown | relation SUBPROPERTY / UNKNOWN | unknown |
| R-time-disjoint | claim time DISJOINT from the question time (or the reference) | consistent |
| R-object-same | object identity SAME | consistent |
| R-no-reference | no reference claim | unknown |
| R-object-unknown | object identity UNKNOWN | unknown |
| R-hierarchy-coarser | object is a KG ancestor, no time-qualified edge | consistent |
| R-hierarchy-uncertain | ancestor via time-qualified edge, or object is finer | unknown |
| R-time-unknown | overlap not established and property not annotated stable | unknown |
| R-sbv-not-exclusive | only a single-best-value constraint | unknown |
| R-cardinality-open | multi-value / none declared / unknown | unknown |
| R-separator-uncertain | single-value constraint with separators | unknown |
| R-exception | subject listed as a constraint exception | unknown |
| R-single-value | all conditions above met | conflict |
"""

from __future__ import annotations

from dataclasses import dataclass

from kgrerank.conflict.signals import PairSignals
from kgrerank.signals import Cardinality, Identity, Mutability, RelationSemantics, TemporalRelation

POLICY_VERSION = "policy_v0.2"
CONFIDENCE = {
    "unrelated": 0.6,
    "same": 0.8,
    "coarser": 0.7,
    "time_disjoint": 0.7,
    "single_value_mandatory": 0.6,
    "single_value_other": 0.5,
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
    stable = b.mutability_class.value is Mutability.STABLE
    if t.value is not TemporalRelation.OVERLAP and not stable:
        return PairVerdict("unknown", "R-time-unknown", 0.0)
    card = b.cardinality_constraint
    if card.value is Cardinality.SINGLE_BEST_VALUE:
        return PairVerdict("unknown", "R-sbv-not-exclusive", 0.0)
    if card.value is not Cardinality.SINGLE_VALUE:
        return PairVerdict("unknown", "R-cardinality-open", 0.0)
    if card.separators:
        return PairVerdict("unknown", "R-separator-uncertain", 0.0)
    if card.subject_is_exception:
        return PairVerdict("unknown", "R-exception", 0.0)
    key = "single_value_mandatory" if card.status == "mandatory" else "single_value_other"
    return PairVerdict("conflict", "R-single-value", CONFIDENCE[key], ("counterfactual",))
