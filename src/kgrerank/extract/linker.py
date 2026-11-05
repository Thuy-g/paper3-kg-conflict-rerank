"""Entity linking by exact (case-insensitive) name match against a KG view.

Names include labels, aliases and name statements (P1448/P1449/P2561/P1813). Ambiguity is never
resolved silently: several candidates give status "ambiguous", which the policy treats as unknown,
unless a disambiguating description in the passage selects exactly one candidate.
"""

from __future__ import annotations

from dataclasses import dataclass

from kgrerank.kg.view import KGView

NAME_PROPS = ("P1448", "P1449", "P2561", "P1813")


@dataclass(frozen=True)
class Link:
    mention: str
    candidates: tuple[str, ...]
    status: str  # unique | ambiguous | none
    via: str = ""  # label | alias | name_statement | description

    @property
    def eid(self) -> str | None:
        return self.candidates[0] if self.status == "unique" else None


class EntityLinker:
    def __init__(self, kg: KGView):
        self.kg = kg
        self._names: dict[str, dict[str, str]] = {}
        for ent in kg.entities.values():
            self._add(ent.label, ent.eid, "label")
            for a in ent.aliases:
                self._add(a, ent.eid, "alias")
        for st in kg.statements:
            if st.prop in NAME_PROPS and st.value.value:
                self._add(st.value.value, st.subject, "name_statement")

    def _add(self, name: str, eid: str, via: str) -> None:
        if name:
            self._names.setdefault(name.casefold(), {}).setdefault(eid, via)

    def link(self, mention: str, description: str = "") -> Link:
        found = self._names.get(mention.strip().casefold(), {})
        cands = tuple(sorted(found))
        if not cands:
            return Link(mention, (), "none")
        if len(cands) == 1:
            return Link(mention, cands, "unique", found[cands[0]])
        if description:
            match = [
                e
                for e in cands
                if (ent := self.kg.entity(e))
                and ent.description.casefold() == description.casefold()
            ]
            if len(match) == 1:
                return Link(mention, (match[0],), "unique", "description")
        return Link(mention, cands, "ambiguous")

    def property_by_label(self, label: str) -> str | None:
        hits = sorted(
            p.pid for p in self.kg.properties.values() if p.label.casefold() == label.casefold()
        )
        return hits[0] if len(hits) == 1 else None
