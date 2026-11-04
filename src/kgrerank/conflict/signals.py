"""Compute the six signals (plus subject identity) for a candidate claim against a reference claim.

Each signal is computed on its own and carries its basis. Nothing here decides anything.
"""

from __future__ import annotations

from dataclasses import dataclass

from kgrerank.extract.claims import Claim
from kgrerank.extract.linker import EntityLinker, Link
from kgrerank.kg.time import temporal_relation
from kgrerank.kg.view import (
    Q_MANDATORY,
    Q_MULTI_VALUE,
    Q_SINGLE_BEST_VALUE,
    Q_SINGLE_VALUE,
    Q_SUGGESTION,
    KGView,
)
from kgrerank.perturb.operators import QuestionFrame
from kgrerank.signals import (
    Basis,
    Cardinality,
    CardinalitySignal,
    EntityIdentitySignal,
    Identity,
    Mutability,
    MutabilitySignal,
    QualifierEvidenceSignal,
    RelationSemantics,
    RelationSemanticsSignal,
    SignalBundle,
    TemporalOverlapSignal,
    TemporalRelation,
)

HIERARCHY = ("P131", "P361")
_STATUS = {Q_MANDATORY: "mandatory", Q_SUGGESTION: "suggestion"}


@dataclass(frozen=True)
class Resolved:
    claim: Claim
    subject: Link
    obj: Link
    prop: str | None  # PID after normalisation (None = relation not recognised)
    inverse: bool = False


def resolve(claim: Claim, linker: EntityLinker, kg: KGView, frame: QuestionFrame) -> Resolved:
    """Link mentions and map the relation label; inverse statements are flipped to the frame's
    property (s, p', o) -> (o, p, s) when p' is declared inverse of p."""
    subj = linker.link(claim.subject, claim.note)
    if subj.status == "ambiguous" and frame.subject in subj.candidates and not claim.note:
        # Default reading: a bare name in a passage retrieved for this question means the
        # question's entity (weaker evidence than a unique match; a description overrides it).
        subj = Link(claim.subject, (frame.subject,), "unique", "default_question_entity")
    obj = linker.link(claim.obj)
    prop = linker.property_by_label(claim.relation)
    if prop and prop != frame.prop and kg.declared_inverse(frame.prop, prop):
        return Resolved(claim, obj, subj, frame.prop, inverse=True)
    return Resolved(claim, subj, obj, prop)


@dataclass(frozen=True)
class PairSignals:
    subject_identity: EntityIdentitySignal
    bundle: SignalBundle

    def to_dict(self) -> dict:
        return {
            "subject_identity": {
                "value": self.subject_identity.value.value,
                "evidence_kind": self.subject_identity.evidence_kind,
            },
            **self.bundle.to_dict(),
        }


def subject_identity(
    cand: Resolved, ref: Resolved | None, frame: QuestionFrame
) -> EntityIdentitySignal:
    link = cand.subject
    if link.status == "unique":
        same = link.eid == frame.subject
        return EntityIdentitySignal(
            Identity.SAME if same else Identity.DIFFERENT,
            link.via or "qid",
            Basis("kg:linker", (link.eid or "",)),
        )
    if link.status == "ambiguous":
        if frame.subject in link.candidates:
            return EntityIdentitySignal(
                Identity.UNKNOWN, "ambiguous", Basis("kg:linker", link.candidates)
            )
        return EntityIdentitySignal(
            Identity.DIFFERENT, "name_of_other_entities", Basis("kg:linker", link.candidates)
        )
    if ref is not None and cand.claim.subject.casefold() == ref.claim.subject.casefold():
        return EntityIdentitySignal(Identity.SAME, "surface", Basis("surface"))
    return EntityIdentitySignal(Identity.UNKNOWN, "unlinked", Basis("surface"))


def relation_semantics(
    cand: Resolved, ref: Resolved, kg: KGView, frame: QuestionFrame
) -> RelationSemanticsSignal:
    if cand.inverse:
        return RelationSemanticsSignal(
            RelationSemantics.INVERSE, Basis("kg:property", (frame.prop,))
        )
    if cand.prop is None or frame.prop not in kg.properties:
        same = ref is not None and cand.claim.relation == ref.claim.relation
        return RelationSemanticsSignal(
            RelationSemantics.SAME if same else RelationSemantics.UNKNOWN, Basis("surface")
        )
    if cand.prop == frame.prop:
        return RelationSemanticsSignal(RelationSemantics.SAME, Basis("kg:property", (cand.prop,)))
    if kg.is_subproperty(cand.prop, frame.prop):
        return RelationSemanticsSignal(
            RelationSemantics.SUBPROPERTY, Basis("kg:P1647", (cand.prop,))
        )
    return RelationSemanticsSignal(
        RelationSemantics.RELATED_DIFFERENT, Basis("kg:property", (cand.prop,))
    )


def object_identity(
    cand: Resolved, ref: Resolved, kg: KGView, frame: QuestionFrame
) -> EntityIdentitySignal:
    if ref is None:
        return EntityIdentitySignal(Identity.UNKNOWN, "no_reference", Basis("none"))
    a, b = cand.obj, ref.obj
    if a.status == "unique" and b.status == "unique":
        if a.eid == b.eid:
            return EntityIdentitySignal(Identity.SAME, a.via, Basis("kg:linker", (a.eid or "",)))
        for x, y, kind in (
            (a.eid, b.eid, "hierarchy_ancestor"),
            (b.eid, a.eid, "hierarchy_descendant"),
        ):
            path = kg.ancestor_paths(y or "", HIERARCHY).get(x or "")
            if path is not None:
                timed = [st.sid for st in path if st.has_temporal_qualifier()]
                note = "timed_edges" if timed else ""
                return EntityIdentitySignal(
                    Identity.DIFFERENT,
                    kind,
                    Basis("kg:hierarchy", tuple(st.sid for st in path), note),
                )
        return EntityIdentitySignal(
            Identity.DIFFERENT, "qid", Basis("kg:linker", (a.eid or "", b.eid or ""))
        )
    if a.status == "none" and b.status == "none":
        if cand.claim.obj.casefold() == ref.claim.obj.casefold():
            return EntityIdentitySignal(Identity.SAME, "surface", Basis("surface"))
        return EntityIdentitySignal(Identity.UNKNOWN, "surface_mismatch", Basis("surface"))
    return EntityIdentitySignal(Identity.UNKNOWN, "unlinked_or_ambiguous", Basis("kg:linker"))


def temporal_overlap(
    cand: Resolved, ref: Resolved | None, frame: QuestionFrame
) -> TemporalOverlapSignal:
    """Against the question's time when it has one; otherwise against the reference claim."""
    ta = cand.claim.time
    if frame.time_anchor is not None:
        if ta is None:
            return TemporalOverlapSignal(
                TemporalRelation.UNKNOWN, Basis("passage", note="unscoped_vs_question")
            )
        return TemporalOverlapSignal(
            temporal_relation(ta, frame.time_anchor), Basis("passage", note="question_anchor")
        )
    if ref is None:
        return TemporalOverlapSignal(TemporalRelation.UNKNOWN, Basis("none", note="no_reference"))
    tb = ref.claim.time
    if ta is None and tb is None:
        # Assumption (policy v0): two unscoped statements are read as being about the same time.
        return TemporalOverlapSignal(
            TemporalRelation.OVERLAP, Basis("assumption", note="both_unscoped")
        )
    if ta is None or tb is None:
        return TemporalOverlapSignal(
            TemporalRelation.UNKNOWN, Basis("passage", note="one_unscoped")
        )
    return TemporalOverlapSignal(temporal_relation(ta, tb), Basis("passage", note="compared"))


def cardinality(kg: KGView, frame: QuestionFrame) -> CardinalitySignal:
    info = kg.property(frame.prop)
    if info is None:
        return CardinalitySignal(Cardinality.UNKNOWN, Basis("none"))
    for ctype, value in (
        (Q_SINGLE_VALUE, Cardinality.SINGLE_VALUE),
        (Q_SINGLE_BEST_VALUE, Cardinality.SINGLE_BEST_VALUE),
        (Q_MULTI_VALUE, Cardinality.MULTI_VALUE),
    ):
        for c in info.constraints_of(ctype):
            return CardinalitySignal(
                value,
                Basis(f"kg:{frame.prop}#P2302", (ctype,)),
                status=_STATUS.get(c.status or "", c.status),
                separators=c.separators,
                exceptions=c.exceptions,
                subject_is_exception=frame.subject in c.exceptions,
            )
    return CardinalitySignal(Cardinality.NONE_DECLARED, Basis(f"kg:{frame.prop}#P2302"))


def mutability(kg: KGView, frame: QuestionFrame) -> MutabilitySignal:
    info = kg.property(frame.prop)
    if info is None or info.mutability not in ("stable", "mutable"):
        return MutabilitySignal(Mutability.UNKNOWN, Basis("none"))
    return MutabilitySignal(
        Mutability(info.mutability), Basis("project_annotation", note=info.mutability_basis)
    )


def qualifier_evidence(
    cand: Resolved, kg: KGView, frame: QuestionFrame
) -> QualifierEvidenceSignal | None:
    if cand.obj.status != "unique":
        return None
    for st in kg.statements_of(frame.subject, frame.prop):
        if st.value.value == cand.obj.eid:
            return QualifierEvidenceSignal(
                st.qualifier_pids(), Basis("kg:statement", (st.sid,)), st.rank, st.n_references
            )
    return None


def pair_signals(
    cand: Resolved, ref: Resolved | None, kg: KGView, frame: QuestionFrame
) -> PairSignals:
    bundle = SignalBundle(
        cardinality_constraint=cardinality(kg, frame),
        mutability_class=mutability(kg, frame),
        temporal_overlap=temporal_overlap(cand, ref, frame),
        qualifier_evidence=qualifier_evidence(cand, kg, frame),
        entity_identity=object_identity(cand, ref, kg, frame),
        relation_semantics=relation_semantics(cand, ref, kg, frame),
    )
    return PairSignals(subject_identity(cand, ref, frame), bundle)
