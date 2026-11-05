"""KG access settings S0–S3 (reports/02d_kg_sources_and_constraints.md §5.4).

S0  no KG.
S1  schema only: property metadata and constraints; no entities, no statements.
S2  S1 + identity and hierarchy: labels, aliases, names (P1448/P1449/P2561/P1813), types
    (P31/P279) and located-in/part-of (P131/P361/P17) statements, with every statement of the
    question's own (subject, property) masked.
S3  full view (KG-oracle): upper bound only, never the main setting.
"""

from __future__ import annotations

from kgrerank.kg.view import KGView

SETTINGS = ("S0", "S1", "S2", "S3")
IDENTITY_PROPS = frozenset({"P31", "P279", "P1448", "P1449", "P2561", "P1813"})
HIERARCHY_PROPS = frozenset({"P131", "P361", "P17"})


def restrict(kg: KGView, setting: str, mask: tuple[str, str] | None = None) -> KGView:
    """Return a new view for ``setting``; ``mask`` = (subject, property) of the question."""
    if setting not in SETTINGS:
        raise ValueError(f"unknown KG setting {setting!r}")
    prov = {**kg.provenance, "setting": setting, "mask": list(mask) if mask else None}
    if setting == "S0":
        return KGView({}, [], {}, prov)
    if setting == "S1":
        return KGView({}, [], dict(kg.properties), prov)
    keep = IDENTITY_PROPS | HIERARCHY_PROPS if setting == "S2" else None
    statements = [
        st
        for st in kg.statements
        if (keep is None or st.prop in keep)
        and not (mask is not None and setting == "S2" and (st.subject, st.prop) == mask)
    ]
    return KGView(dict(kg.entities), statements, dict(kg.properties), prov)
