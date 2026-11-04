"""Perturbation operators and label protocol v0 (construction-time labels, not a method).

Each operator records in ``reasons`` *what it changed*. The decision is assigned only when every
precondition of the protocol has evidence in the :class:`KGView`; otherwise the candidate is
``UNKNOWN`` and the unmet preconditions are stored as evidence. The same operator (same reasons)
can therefore yield different decisions, which is the point: a reason type never fixes the
decision on its own.

Known limitation (documented in docs/PLAN.md and reports): labels are derived from the same KG a
KG-based method may consult, so synthetic perturbations are capability probes, not main evidence.
Absence of a value in the KG is not proof of falsity (open world); the counterfactual operator
therefore also requires that the asked (subject, property) has exactly one KG value in scope.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from kgrerank.kg.time import Interval, TimeRange, temporal_relation, year_range
from kgrerank.kg.view import KGView, Statement
from kgrerank.schema import Candidate, Decision, Evidence, Example
from kgrerank.signals import TemporalRelation

PROTOCOL = "perturbation_rule_v0"
NAME_PROPERTIES = frozenset({"P1448", "P1449", "P2561", "P1813", "P1705", "P742"})
HISTORICAL_NAME_PROPERTIES = ("P1448", "P2561")
RELATED_PREDICATES: dict[str, tuple[str, ...]] = {
    "P19": ("P20", "P551"),
    "P20": ("P19", "P551"),
    "P569": ("P570",),
    "P570": ("P569",),
    "P22": ("P25",),
    "P25": ("P22",),
    "P6": ("P35",),
    "P35": ("P6",),
}


@dataclass(frozen=True)
class QuestionFrame:
    """KG view of a question, taken from dataset annotations (never inferred by a method)."""

    subject: str
    prop: str
    gold: tuple[str, ...]
    time_anchor: Interval | None = None
    fact_time: Interval | None = None


@dataclass(frozen=True)
class PerturbationResult:
    operator: str
    candidate: Candidate | None
    unmet: tuple[str, ...]


def frame_from_meta(meta: dict) -> QuestionFrame | None:
    """Build a frame from ``meta['frame']``.

    Keys: subject, prop, gold, and optionally time_anchor_year and fact_year.
    """
    f = meta.get("frame")
    if not f:
        return None
    anchor = f.get("time_anchor_year")
    fact = f.get("fact_year")
    return QuestionFrame(
        subject=f["subject"],
        prop=f["prop"],
        gold=tuple(f["gold"]),
        time_anchor=Interval.point(year_range(anchor)) if anchor is not None else None,
        fact_time=Interval.point(year_range(fact)) if fact is not None else None,
    )


# ---------------------------------------------------------------------- helpers
def _plabel(kg: KGView, pid: str) -> str:
    info = kg.property(pid)
    return info.label if info and info.label else pid


def _year(t: TimeRange | None, which: str) -> str | None:
    if t is None:
        return None
    lo, hi = t.lo[0], t.hi[0]
    if lo == hi:
        return str(lo)
    return f"{lo}s" if hi - lo == 9 and lo % 10 == 0 else (str(lo) if which == "start" else str(hi))


def _period_phrase(iv: Interval) -> str | None:
    start, end = _year(iv.start, "start"), _year(iv.end, "end")
    if start and end:
        return f"from {start} to {end}" if start != end else f"in {start}"
    if start:
        return f"from {start}"
    if end:
        return f"until {end}"
    return None


def _claim(
    kg: KGView, frame: QuestionFrame, prop: str, subj: str, obj: str, anchored: bool = True
) -> str:
    """State (subj, prop, obj) at the question's time anchor when there is one.

    A claim without a time scope does not contradict (or support) an answer about a specific time,
    so anchored questions get anchored claims ("In 2010, the X of Y was Z.").
    """
    plabel = _plabel(kg, prop)
    if anchored and frame.time_anchor is not None and frame.time_anchor.start is not None:
        when = _year(frame.time_anchor.start, "start")
        return f"In {when}, the {plabel} of {subj} was {obj}."
    return f"The {plabel} of {subj} is {obj}."


def _st_ev(st: Statement) -> Evidence:
    return Evidence(
        kind="kg_statement",
        ref=st.sid,
        detail={
            "s": st.subject,
            "p": st.prop,
            "v": st.value.value,
            "rank": st.rank,
            "qualifiers": list(st.qualifier_pids()),
        },
    )


def _ent_ev(kg: KGView, eid: str, note: str = "") -> Evidence:
    ent = kg.entity(eid)
    detail: dict = {"label": kg.label(eid), "types": sorted(kg.types(eid))}
    if ent is not None:
        detail["aliases"] = list(ent.aliases)
        detail["description"] = ent.description
    if note:
        detail["note"] = note
    return Evidence(kind="kg_entity", ref=eid, detail=detail)


def _gold_statements(kg: KGView, frame: QuestionFrame) -> list[Statement]:
    return [
        st
        for st in kg.statements_of(frame.subject, frame.prop, include_deprecated=False)
        if st.value.value in frame.gold
    ]


def _values_in_scope(kg: KGView, frame: QuestionFrame) -> list[Statement]:
    """Non-deprecated statements of (s, p) that may hold at the question's time anchor."""
    sts = kg.statements_of(frame.subject, frame.prop, include_deprecated=False)
    if frame.time_anchor is None:
        return sts
    return [
        st
        for st in sts
        if temporal_relation(st.interval(), frame.time_anchor) is not TemporalRelation.DISJOINT
    ]


def _build(
    op: str,
    qid: str,
    k: int,
    title: str,
    text: str,
    reasons: Sequence[str],
    decision_if_met: Decision,
    unmet: list[str],
    evidence: list[Evidence],
) -> PerturbationResult:
    decision = decision_if_met if not unmet else Decision.UNKNOWN
    note = Evidence(
        kind="note",
        ref=PROTOCOL,
        detail={"operator": op, "decision_if_met": decision_if_met.value, "unmet": list(unmet)},
    )
    cand = Candidate(
        pid=f"{qid}::pert::{op}::{k}",
        title=title,
        text=text,
        is_gold=False,
        decision=decision,
        reasons=list(reasons),
        label_source=PROTOCOL,
        evidence=[*evidence, note],
    )
    return PerturbationResult(op, cand, tuple(unmet))


def _none(op: str, why: str) -> PerturbationResult:
    return PerturbationResult(op, None, (why,))


# ---------------------------------------------------------------------- operators
def counterfactual(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    op = "counterfactual"
    gold_types = set().union(*(kg.types(g) for g in frame.gold)) if frame.gold else set()
    if not gold_types:
        return _none(op, "gold value has no P31 type in the KG view")
    all_values = set(kg.item_values(frame.subject, frame.prop, include_deprecated=True))
    gold_names = set().union(*(kg.names(g) for g in frame.gold))
    pool = sorted(
        e
        for e in kg.entities
        if e not in frame.gold
        and e not in all_values
        and kg.types(e) & gold_types
        and not (kg.names(e) & gold_names)
    )
    if not pool:
        return _none(op, "no same-type replacement outside the KG values of (s, p)")
    new = rng.choice(pool)
    unmet: list[str] = []
    in_scope = _values_in_scope(kg, frame)
    if len(in_scope) != 1:
        unmet.append(f"(s, p) has {len(in_scope)} KG values in the question's scope, not exactly 1")
    text = _claim(kg, frame, frame.prop, kg.label(frame.subject), kg.label(new))
    ev = [*map(_st_ev, in_scope), _ent_ev(kg, new, "replacement; not a KG value of (s, p)")]
    return _build(
        op,
        qid,
        k,
        kg.label(frame.subject),
        text,
        ["counterfactual"],
        Decision.CONTRADICTING,
        unmet,
        ev,
    )


def alias(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    op = "alias"
    gold = sorted(frame.gold)
    if len(gold) != 1:
        return _none(op, "alias operator needs exactly one gold value")
    g = gold[0]
    ent = kg.entity(g)
    aliases = sorted(a for a in (ent.aliases if ent else ()) if a != kg.label(g))
    if not aliases:
        return _none(op, "gold value has no alias in the KG view")
    name = rng.choice(aliases)
    unmet: list[str] = []
    if frame.prop in NAME_PROPERTIES:
        unmet.append("the question asks about a name, so a different name may contradict")
    others = kg.entities_named(name) - {g}
    if others:
        unmet.append(f"alias is shared with other entities {sorted(others)}")
    text = _claim(kg, frame, frame.prop, kg.label(frame.subject), name)
    ev = [*map(_st_ev, _gold_statements(kg, frame)), _ent_ev(kg, g, f"alias used: {name}")]
    return _build(
        op, qid, k, kg.label(frame.subject), text, ["alias"], Decision.COMPATIBLE, unmet, ev
    )


def historical_name(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    op = "historical_name"
    gold = sorted(frame.gold)
    if len(gold) != 1:
        return _none(op, "historical-name operator needs exactly one gold value")
    g = gold[0]
    names = [
        st
        for pid in HISTORICAL_NAME_PROPERTIES
        for st in kg.statements_of(g, pid, include_deprecated=False)
        if st.value.value and st.value.value != kg.label(g) and st.has_temporal_qualifier()
    ]
    if not names:
        return _none(op, "gold value has no time-qualified historical name")
    st = rng.choice(names)
    period = _period_phrase(st.interval())
    unmet: list[str] = []
    if period is None:
        unmet.append("validity period of the name is unknown, so the passage cannot state it")
    if frame.prop in NAME_PROPERTIES:
        unmet.append("the question asks about a name, so a different name may contradict")
    if kg.entities_named(st.value.value) - {g}:
        unmet.append("historical name is shared with other entities")
    tail = f" ({st.value.value} was the name of {kg.label(g)} {period})" if period else ""
    text = _claim(kg, frame, frame.prop, kg.label(frame.subject), st.value.value)[:-1] + f"{tail}."
    ev = [*map(_st_ev, _gold_statements(kg, frame)), _st_ev(st)]
    return _build(
        op,
        qid,
        k,
        kg.label(frame.subject),
        text,
        ["historical_identity"],
        Decision.COMPATIBLE,
        unmet,
        ev,
    )


def temporal(
    kg: KGView,
    frame: QuestionFrame,
    rng: random.Random,
    qid: str,
    k: int = 0,
    state_interval: bool = True,
):
    op = "temporal" if state_interval else "temporal_unstated"
    options = [
        st
        for st in kg.statements_of(frame.subject, frame.prop, include_deprecated=False)
        if st.value.kind == "item"
        and st.value.value not in frame.gold
        and st.has_temporal_qualifier()
    ]
    if not options:
        return _none(op, "no other time-qualified value of (s, p)")
    st = rng.choice(options)
    period = _period_phrase(st.interval())
    unmet: list[str] = []
    if not state_interval or period is None:
        unmet.append("passage does not state the validity period of the value")
    if frame.time_anchor is not None:
        rel = temporal_relation(st.interval(), frame.time_anchor)
        if rel is TemporalRelation.OVERLAP:
            unmet.append("value also holds at the question's time (possible second answer)")
        elif rel is TemporalRelation.UNKNOWN:
            unmet.append("cannot decide whether the value holds at the question's time")
    subj, val = kg.label(frame.subject), kg.label(st.value.value)
    plabel = _plabel(kg, frame.prop)
    if state_interval and period:
        text = f"{period[0].upper()}{period[1:]}, the {plabel} of {subj} was {val}."
    else:
        text = f"The {plabel} of {subj} is {val}."
    return _build(
        op, qid, k, subj, text, ["temporal_scope"], Decision.COMPATIBLE, unmet, [_st_ev(st)]
    )


def granularity(
    kg: KGView,
    frame: QuestionFrame,
    rng: random.Random,
    qid: str,
    k: int = 0,
    props: tuple[str, ...] = ("P131",),
):
    op = "granularity"
    gold = sorted(frame.gold)
    if len(gold) != 1:
        return _none(op, "granularity operator needs exactly one gold value")
    paths = kg.ancestor_paths(gold[0], props)
    options = sorted(a for a in paths if a not in frame.gold)
    if not options:
        return _none(op, "gold value has no ancestor in the KG view")
    anc = rng.choice(options)
    unmet: list[str] = []
    notes: list[str] = []
    for edge in paths[anc]:
        if not edge.has_temporal_qualifier():
            notes.append(f"{edge.sid}: no temporal qualifier, assumed time-invariant")
            continue
        if frame.fact_time is None:
            unmet.append(f"{edge.sid} is time-qualified but the fact time is unknown")
        elif temporal_relation(edge.interval(), frame.fact_time) is not TemporalRelation.OVERLAP:
            unmet.append(f"{edge.sid} is not known to hold at the fact time")
    reason = "geographic_granularity" if set(props) & {"P131", "P17"} else "hierarchy"
    text = _claim(kg, frame, frame.prop, kg.label(frame.subject), kg.label(anc))
    ev = [*map(_st_ev, paths[anc])]
    if notes:
        ev.append(Evidence(kind="note", ref="assumption", detail={"notes": notes}))
    return _build(
        op, qid, k, kg.label(frame.subject), text, [reason], Decision.COMPATIBLE, unmet, ev
    )


def predicate(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    op = "predicate"
    options = [
        st
        for p2 in RELATED_PREDICATES.get(frame.prop, ())
        for st in kg.statements_of(frame.subject, p2, include_deprecated=False)
        if st.value.value not in frame.gold
    ]
    if not options:
        return _none(op, "subject has no value for a related predicate")
    st = rng.choice(options)
    unmet: list[str] = []
    inv = kg.declared_inverse(frame.prop, st.prop)
    sub = kg.is_subproperty(frame.prop, st.prop)
    if inv is None or sub is None:
        unmet.append("relation semantics of the two properties are not described in the KG view")
    elif inv or sub:
        unmet.append("the two properties are inverse or sub-properties, not merely different")
    val = kg.label(st.value.value) if st.value.kind == "item" else st.value.value
    text = f"The {_plabel(kg, st.prop)} of {kg.label(frame.subject)} is {val}."
    ev = [_st_ev(st), Evidence(kind="kg_property", ref=st.prop, detail={"asked": frame.prop})]
    return _build(
        op,
        qid,
        k,
        kg.label(frame.subject),
        text,
        ["predicate_mismatch"],
        Decision.COMPATIBLE,
        unmet,
        ev,
    )


def inverse(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    op = "inverse"
    inv_props = sorted(p for p in kg.properties if kg.declared_inverse(frame.prop, p))
    gold = sorted(frame.gold)
    if not inv_props or len(gold) != 1:
        return _none(op, "no declared inverse property, or not exactly one gold value")
    p2 = rng.choice(inv_props)
    unmet: list[str] = []
    gold_sts = _gold_statements(kg, frame)
    if not gold_sts:
        unmet.append("the gold triple is not in the KG view")
    text = _claim(kg, frame, p2, kg.label(gold[0]), kg.label(frame.subject))
    ev = [
        *map(_st_ev, gold_sts),
        Evidence(kind="kg_property", ref=p2, detail={"inverse_of": frame.prop}),
    ]
    return _build(
        op, qid, k, kg.label(gold[0]), text, ["inverse_relation"], Decision.COMPATIBLE, unmet, ev
    )


def homonym(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    op = "homonym"
    others = sorted(
        set().union(*(kg.entities_named(n) for n in kg.names(frame.subject))) - {frame.subject}
    )
    options = [
        (e2, st)
        for e2 in others
        for st in kg.statements_of(e2, frame.prop, include_deprecated=False)
        if st.value.kind == "item"
    ]
    if not options:
        return _none(op, "no same-name entity with a value for the asked property")
    e2, st = rng.choice(options)
    shared = sorted(kg.names(frame.subject) & kg.names(e2))[0]
    t1, t2 = kg.types(frame.subject), kg.types(e2)
    unmet: list[str] = []
    if not t1 or not t2:
        unmet.append("P31 type of one of the two entities is unknown")
    elif t1 & t2:
        unmet.append(f"the two entities share P31 types {sorted(t1 & t2)}")
    ent2 = kg.entity(e2)
    desc = ent2.description if ent2 else ""
    if not desc:
        unmet.append("the other entity has no description, so the passage cannot disambiguate")
    head = f"{shared} ({desc})" if desc else shared
    # Not anchored: the claim is about another entity, and its time is not in the evidence.
    claim = _claim(kg, frame, frame.prop, shared, kg.label(st.value.value), anchored=False)
    text = f"{head}: {claim[0].lower()}{claim[1:]}"
    ev = [
        _ent_ev(kg, frame.subject, "question subject"),
        _ent_ev(kg, e2, "same-name entity"),
        _st_ev(st),
    ]
    return _build(
        op,
        qid,
        k,
        shared,
        text,
        ["homonym", "entity_identity_mismatch"],
        Decision.IRRELEVANT,
        unmet,
        ev,
    )


def temporal_unstated(kg: KGView, frame: QuestionFrame, rng: random.Random, qid: str, k: int = 0):
    return temporal(kg, frame, rng, qid, k, state_interval=False)


Operator = Callable[[KGView, QuestionFrame, random.Random, str, int], PerturbationResult]
OPERATORS: dict[str, Operator] = {
    "counterfactual": counterfactual,
    "alias": alias,
    "historical_name": historical_name,
    "temporal": temporal,
    "temporal_unstated": temporal_unstated,
    "granularity": granularity,
    "predicate": predicate,
    "inverse": inverse,
    "homonym": homonym,
}


def apply_operators(
    example: Example,
    kg: KGView,
    operators: Sequence[str],
    seed: int,
    drop_unknown: bool = False,
) -> tuple[Example, list[PerturbationResult]]:
    """Append one perturbed candidate per applicable operator to a copy of ``example``.

    Randomness is local to (seed, qid, operator), so results do not depend on operator order.
    """
    frame = frame_from_meta(example.meta)
    if frame is None:
        return example, []
    new_cands = list(example.candidates)
    results: list[PerturbationResult] = []
    for name in operators:
        rng = random.Random(f"{seed}|{example.qid}|{name}")
        res = OPERATORS[name](kg, frame, rng, example.qid, 0)
        results.append(res)
        if res.candidate is None:
            continue
        if drop_unknown and res.candidate.decision is Decision.UNKNOWN:
            continue
        new_cands.append(res.candidate)
    return replace(example, candidates=new_cands), results
