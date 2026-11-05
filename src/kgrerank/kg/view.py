"""Read-only view over a small KG in the ``kgview/v1`` JSON format.

The same format is used by hand-written synthetic fixtures and by the normalised output of
``scripts/wikidata/build_reference_slice.py``. Statements keep their rank and qualifiers, and
properties keep their constraint statements (type, status, separators, exceptions), so callers can
treat constraints as soft evidence rather than axioms.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kgrerank.kg.time import Interval, TimeRange, parse_wikidata_time

FORMAT = "kgview/v1"
RANKS = ("preferred", "normal", "deprecated")
START_QUALIFIERS = ("P580",)
END_QUALIFIERS = ("P582",)
POINT_QUALIFIERS = ("P585",)
# Constraint type items (verified 2026-11-04, reports/02d_kg_sources_and_constraints.md §1).
Q_SINGLE_VALUE = "Q19474404"
Q_SINGLE_BEST_VALUE = "Q52060874"
Q_MULTI_VALUE = "Q21510857"
Q_INVERSE = "Q21510855"
Q_MANDATORY = "Q21502408"
Q_SUGGESTION = "Q62026391"


@dataclass(frozen=True)
class Value:
    """A statement or qualifier value: kind is item|string|time|quantity|text|somevalue|novalue."""

    kind: str
    value: str
    precision: int | None = None
    lang: str | None = None

    def time_range(self) -> TimeRange | None:
        if self.kind != "time" or self.precision is None:
            return None
        return parse_wikidata_time(self.value, self.precision)


@dataclass(frozen=True)
class Statement:
    sid: str
    subject: str
    prop: str
    value: Value
    rank: str = "normal"
    qualifiers: tuple[tuple[str, tuple[Value, ...]], ...] = ()
    n_references: int = 0

    def qualifier_values(self, pid: str) -> tuple[Value, ...]:
        for key, vals in self.qualifiers:
            if key == pid:
                return vals
        return ()

    def qualifier_pids(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, _ in self.qualifiers))

    def interval(self) -> Interval:
        """Validity interval from P580/P582 (or P585 as a point); unknown endpoints stay None."""
        point = _first_time(self, POINT_QUALIFIERS)
        start = _first_time(self, START_QUALIFIERS)
        end = _first_time(self, END_QUALIFIERS)
        if point is not None and start is None and end is None:
            return Interval.point(point)
        return Interval(start=start, end=end)

    def has_temporal_qualifier(self) -> bool:
        pids = set(self.qualifier_pids())
        return bool(pids & set(START_QUALIFIERS + END_QUALIFIERS + POINT_QUALIFIERS))


def _first_time(st: Statement, pids: Iterable[str]) -> TimeRange | None:
    for pid in pids:
        for val in st.qualifier_values(pid):
            rng = val.time_range()
            if rng is not None:
                return rng
    return None


@dataclass(frozen=True)
class Entity:
    eid: str
    label: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    lastrevid: int | None = None


@dataclass(frozen=True)
class PropertyConstraint:
    ctype: str
    status: str | None = None
    separators: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    params: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def param(self, pid: str) -> tuple[str, ...]:
        for key, vals in self.params:
            if key == pid:
                return vals
        return ()


@dataclass(frozen=True)
class PropertyInfo:
    pid: str
    label: str
    datatype: str = ""
    constraints: tuple[PropertyConstraint, ...] = ()
    inverse: tuple[str, ...] = ()  # P1696 values
    subproperty_of: tuple[str, ...] = ()  # P1647 values
    mutability: str | None = None  # project annotation: stable | mutable | None
    mutability_basis: str = ""

    def constraints_of(self, ctype: str) -> tuple[PropertyConstraint, ...]:
        return tuple(c for c in self.constraints if c.ctype == ctype)


@dataclass
class KGView:
    entities: dict[str, Entity]
    statements: list[Statement]
    properties: dict[str, PropertyInfo]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_subject: dict[str, list[Statement]] = {}
        for st in self.statements:
            self._by_subject.setdefault(st.subject, []).append(st)
        self._by_name: dict[str, set[str]] = {}
        for ent in self.entities.values():
            for name in (ent.label, *ent.aliases):
                if name:
                    self._by_name.setdefault(name.casefold(), set()).add(ent.eid)

    # ------------------------------------------------------------------ loading
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KGView:
        if d.get("format") != FORMAT:
            raise ValueError(f"expected format {FORMAT!r}, got {d.get('format')!r}")
        entities = {
            eid: Entity(
                eid=eid,
                label=e.get("label", ""),
                aliases=tuple(e.get("aliases", [])),
                description=e.get("description", ""),
                lastrevid=e.get("lastrevid"),
            )
            for eid, e in d.get("entities", {}).items()
        }
        statements = []
        for i, s in enumerate(d.get("statements", [])):
            rank = s.get("rank", "normal")
            if rank not in RANKS:
                raise ValueError(f"statement {i}: bad rank {rank!r}")
            quals = tuple(
                (pid, tuple(_value(v) for v in vals))
                for pid, vals in sorted(s.get("q", {}).items())
            )
            statements.append(
                Statement(
                    sid=s.get("sid", f"s{i}"),
                    subject=s["s"],
                    prop=s["p"],
                    value=_value(s["v"]),
                    rank=rank,
                    qualifiers=quals,
                    n_references=int(s.get("n_refs", 0)),
                )
            )
        properties = {}
        for pid, p in d.get("properties", {}).items():
            constraints = tuple(
                PropertyConstraint(
                    ctype=c["type"],
                    status=c.get("status"),
                    separators=tuple(c.get("separators", [])),
                    exceptions=tuple(c.get("exceptions", [])),
                    params=tuple((k, tuple(v)) for k, v in sorted(c.get("params", {}).items())),
                )
                for c in p.get("constraints", [])
                if c.get("statement_rank", "normal") != "deprecated"  # deprecated: not in force
            )
            mut = p.get("mutability") or {}
            properties[pid] = PropertyInfo(
                pid=pid,
                label=p.get("label", ""),
                datatype=p.get("datatype", ""),
                constraints=constraints,
                inverse=tuple(p.get("inverse", [])),
                subproperty_of=tuple(p.get("subproperty_of", [])),
                mutability=mut.get("value"),
                mutability_basis=mut.get("basis", ""),
            )
        return cls(entities, statements, properties, dict(d.get("provenance", {})))

    @classmethod
    def from_json(cls, path: str | Path) -> KGView:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # ------------------------------------------------------------------ queries
    def entity(self, eid: str) -> Entity | None:
        return self.entities.get(eid)

    def label(self, eid: str) -> str:
        ent = self.entities.get(eid)
        return ent.label if ent and ent.label else eid

    def names(self, eid: str) -> set[str]:
        ent = self.entities.get(eid)
        if ent is None:
            return set()
        return {n for n in (ent.label, *ent.aliases) if n}

    def entities_named(self, name: str) -> set[str]:
        return set(self._by_name.get(name.casefold(), set()))

    def statements_of(
        self, subject: str, prop: str | None = None, include_deprecated: bool = True
    ) -> list[Statement]:
        out = [
            st
            for st in self._by_subject.get(subject, [])
            if (prop is None or st.prop == prop) and (include_deprecated or st.rank != "deprecated")
        ]
        return sorted(out, key=lambda st: st.sid)

    def item_values(self, subject: str, prop: str, include_deprecated: bool = False) -> list[str]:
        return [
            st.value.value
            for st in self.statements_of(subject, prop, include_deprecated)
            if st.value.kind == "item"
        ]

    def types(self, eid: str) -> set[str]:
        """Non-deprecated P31 values (instance of)."""
        return set(self.item_values(eid, "P31"))

    def property(self, pid: str) -> PropertyInfo | None:
        return self.properties.get(pid)

    def declared_inverse(self, p: str, q: str) -> bool | None:
        """True if p and q are declared inverse (P1696, or inverse constraint with P2306).

        Returns None when neither property is described in the view (unknown, not False).
        """
        info_p, info_q = self.properties.get(p), self.properties.get(q)
        if info_p is None and info_q is None:
            return None
        for other, info in ((q, info_p), (p, info_q)):
            if info is None:
                continue
            if other in info.inverse:
                return True
            if any(other in c.param("P2306") for c in info.constraints_of(Q_INVERSE)):
                return True
        return False

    def is_subproperty(self, p: str, q: str) -> bool | None:
        info_p, info_q = self.properties.get(p), self.properties.get(q)
        if info_p is None and info_q is None:
            return None
        return bool(
            (info_p and q in info_p.subproperty_of) or (info_q and p in info_q.subproperty_of)
        )

    def ancestor_paths(
        self, eid: str, props: tuple[str, ...] = ("P131",), max_depth: int = 6
    ) -> dict[str, list[Statement]]:
        """Breadth-first ancestors via ``props`` (non-deprecated statements only).

        Returns, for each reachable ancestor, the first-found path as a list of statements.
        """
        paths: dict[str, list[Statement]] = {}
        queue: deque[tuple[str, list[Statement]]] = deque([(eid, [])])
        while queue:
            node, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for prop in props:
                for st in self.statements_of(node, prop, include_deprecated=False):
                    if st.value.kind != "item":
                        continue
                    parent = st.value.value
                    if parent == eid or parent in paths:
                        continue
                    paths[parent] = [*path, st]
                    queue.append((parent, [*path, st]))
        return paths


def _value(v: dict[str, Any]) -> Value:
    return Value(
        kind=v["kind"],
        value=str(v.get("value", "")),
        precision=v.get("precision"),
        lang=v.get("lang"),
    )
