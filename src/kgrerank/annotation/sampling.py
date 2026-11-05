"""Deterministic, pre-registered sampling of annotation items (docs/ANNOTATION_GUIDELINES.md §2).

Sampling uses only dataset fields (query category, question type, passage positions, the 2Wiki
supporting-fact flag for balancing). It never uses model outputs, rankings or scores. Every random
draw uses its own ``random.Random`` seeded by (seed, purpose), so changing one stratum does not
change the others. Pilot queries are disjoint from main queries.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from kgrerank.data.conflicts import convert_conflicts
from kgrerank.data.twowiki import convert_2wiki

CONFLICTS_STRATA = {
    "Conflict due to outdated information": "outdated",
    "No conflict": "no_conflict",
    "Complementary information": "complementary",
    "Conflict due to misinformation": "misinformation",
    "Conflicting opinions and research outcomes": "opinions",
}


@dataclass(frozen=True)
class FramePassage:
    pid: str
    title: str
    text: str
    date: str
    supporting: bool | None  # 2Wiki dataset flag; used for balancing only, never shown
    text_sha256: str


@dataclass(frozen=True)
class FrameQuery:
    source: str
    qid: str
    stratum: str
    question: str
    reference_answer: str
    passages: tuple[FramePassage, ...]


@dataclass(frozen=True)
class SampledItem:
    item_id: str
    set: str  # pilot | main
    source: str
    qid: str
    pid: str
    stratum: str
    double: bool = False


_MONTHS = {
    m: i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
    )
}


def normalize_date(raw: str | None) -> str:
    """Display date for annotators: ISO 'YYYY-MM-DD', or '' when missing ('NA').

    Formats seen in conflicts.jsonl: 'NA', 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM:SS', 'Mon DD, YYYY'.
    Anything else is shown unchanged. Display only: sampling never depends on dates.
    """
    s = (raw or "").strip()
    if not s or s.upper() == "NA":
        return ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and s[:4].isdigit():
        return s[:10]
    parts = s.replace(",", "").split()
    if len(parts) == 3 and parts[0][:3] in _MONTHS and parts[1].isdigit() and parts[2].isdigit():
        return f"{int(parts[2]):04d}-{_MONTHS[parts[0][:3]]:02d}-{int(parts[1]):02d}"
    return s


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_item_id(sample_version: str, source: str, qid: str, pid: str) -> str:
    """Opaque, stable ID: reveals neither the stratum nor the position in the pool."""
    return "it_" + sha256_text(f"{sample_version}|{source}|{qid}|{pid}")[:12]


def rng_for(seed: int, *parts: Any) -> random.Random:
    return random.Random("|".join([str(seed), *map(str, parts)]))


# ------------------------------------------------------------------------------ frames
def _dedupe(passages: Iterable[FramePassage]) -> tuple[FramePassage, ...]:
    seen: set[str] = set()
    out = []
    for p in passages:
        if p.text.strip() and p.text_sha256 not in seen:
            seen.add(p.text_sha256)
            out.append(p)
    return tuple(out)


def conflicts_frame(
    records: Sequence[dict[str, Any]],
    text_field: str = "short_text",
    max_chars: int = 2000,
    require_reference: bool = True,
) -> list[FrameQuery]:
    """One FrameQuery per eligible CONFLICTS line.

    Passage text is produced by the same converter as the harness, so annotators label exactly
    the text a method sees.
    """
    frame = []
    for i, rec in enumerate(records):
        stratum = CONFLICTS_STRATA.get(rec.get("conflict_type", ""), "other")
        ex = convert_conflicts(rec, i, text_field, max_chars)
        ref = ex.answers[0] if ex.answers else ""
        if require_reference and not ref:
            continue
        dates = {r["pid"]: normalize_date(r.get("date")) for r in ex.meta["results"]}
        passages = _dedupe(
            FramePassage(c.pid, c.title, c.text, dates.get(c.pid, ""), None, sha256_text(c.text))
            for c in ex.candidates
        )
        if passages:
            frame.append(FrameQuery("conflicts", ex.qid, stratum, ex.question, ref, passages))
    return frame


def twowiki_frame(records: Sequence[dict[str, Any]]) -> list[FrameQuery]:
    frame = []
    for rec in records:
        ex = convert_2wiki(rec)
        passages = _dedupe(
            FramePassage(c.pid, c.title, c.text, "", c.is_gold, sha256_text(c.text))
            for c in ex.candidates
        )
        stratum = str(ex.meta.get("question_type") or "unknown")
        frame.append(FrameQuery("twowiki", ex.qid, stratum, ex.question, ex.answers[0], passages))
    return frame


# ---------------------------------------------------------------------------- sampling
def largest_remainder(weights: dict[str, int], total: int) -> dict[str, int]:
    """Proportional integer allocation of ``total`` over keys (ties broken by key)."""
    s = sum(weights.values())
    if s == 0 or total <= 0:
        return {k: 0 for k in weights}
    raw = {k: total * w / s for k, w in weights.items()}
    alloc = {k: int(v) for k, v in raw.items()}
    rest = total - sum(alloc.values())
    for k in sorted(raw, key=lambda k: (-(raw[k] - alloc[k]), k))[:rest]:
        alloc[k] += 1
    return alloc


def pick_passages(
    q: FrameQuery, k: int, rng: random.Random, supporting_k: int | None = None
) -> list[FramePassage]:
    """Uniform choice of k passages; for 2Wiki, up to ``supporting_k`` supporting ones first."""
    if supporting_k is None:
        pool = sorted(q.passages, key=lambda p: p.pid)
        return rng.sample(pool, min(k, len(pool)))
    sup = sorted((p for p in q.passages if p.supporting), key=lambda p: p.pid)
    non = sorted((p for p in q.passages if not p.supporting), key=lambda p: p.pid)
    take_sup = rng.sample(sup, min(supporting_k, len(sup), k))
    take_non = rng.sample(non, min(k - len(take_sup), len(non)))
    return take_sup + take_non


def _items(
    version: str, set_name: str, q: FrameQuery, chosen: Iterable[FramePassage]
) -> list[SampledItem]:
    return [
        SampledItem(
            make_item_id(version, q.source, q.qid, p.pid),
            set_name,
            q.source,
            q.qid,
            p.pid,
            f"{q.source}:{q.stratum}",
        )
        for p in chosen
    ]


def draw_conflicts(
    frame: Sequence[FrameQuery],
    spec: dict[str, Any],
    set_name: str,
    seed: int,
    version: str,
    exclude_qids: set[str],
    total: int | None = None,
) -> list[SampledItem]:
    """Draw items per stratum spec: {queries, per_query} | {census, per_query_cap} | {fill, ...}."""
    by_stratum: dict[str, list[FrameQuery]] = {}
    for q in sorted(frame, key=lambda q: q.qid):
        if q.qid not in exclude_qids:
            by_stratum.setdefault(q.stratum, []).append(q)
    out: list[SampledItem] = []
    fill_key = None
    for key, s in sorted(spec.items()):
        if s.get("fill"):
            fill_key = key
            continue
        qs = by_stratum.get(key, [])
        if s.get("census"):
            chosen_q = qs
            k = int(s.get("per_query_cap", 10**6))
        else:
            chosen_q = rng_for(seed, set_name, key, "queries").sample(
                qs, min(int(s["queries"]), len(qs))
            )
            k = int(s["per_query"])
        for q in sorted(chosen_q, key=lambda q: q.qid):
            out.extend(
                _items(
                    version, set_name, q, pick_passages(q, k, rng_for(seed, set_name, key, q.qid))
                )
            )
    if fill_key is not None:
        if total is None:
            raise ValueError("a 'fill' stratum needs a total")
        target = total - len(out)
        k = int(spec[fill_key]["per_query"])
        qs = list(by_stratum.get(fill_key, []))
        rng_for(seed, set_name, fill_key, "queries").shuffle(qs)
        for q in qs:
            if target <= 0:
                break
            take = pick_passages(q, min(k, target), rng_for(seed, set_name, fill_key, q.qid))
            out.extend(_items(version, set_name, q, take))
            target -= len(take)
    return out


def draw_twowiki(
    frame: Sequence[FrameQuery],
    spec: dict[str, Any],
    set_name: str,
    seed: int,
    version: str,
    exclude_qids: set[str],
) -> list[SampledItem]:
    """Pilot: {items, per_query, supporting_per_query}; main adds {queries, stratify_by}."""
    qs = sorted((q for q in frame if q.qid not in exclude_qids), key=lambda q: q.qid)
    per_q, sup_k = int(spec["per_query"]), int(spec["supporting_per_query"])
    out: list[SampledItem] = []
    if "items" in spec:  # fill a fixed number of items, query by query
        target = int(spec["items"])
        order = list(qs)
        rng_for(seed, set_name, "twowiki", "queries").shuffle(order)
        for q in order:
            if target <= 0:
                break
            k = min(per_q, target)
            take = pick_passages(
                q, k, rng_for(seed, set_name, "twowiki", q.qid), min(sup_k, (k + 1) // 2)
            )
            out.extend(_items(version, set_name, q, take))
            target -= len(take)
        return out
    by_type: dict[str, list[FrameQuery]] = {}
    for q in qs:
        by_type.setdefault(q.stratum, []).append(q)
    alloc = largest_remainder({t: len(v) for t, v in by_type.items()}, int(spec["queries"]))
    for t in sorted(by_type):
        chosen = rng_for(seed, set_name, "twowiki", t).sample(by_type[t], alloc[t])
        for q in sorted(chosen, key=lambda q: q.qid):
            out.extend(
                _items(
                    version,
                    set_name,
                    q,
                    pick_passages(q, per_q, rng_for(seed, set_name, "twowiki", q.qid), sup_k),
                )
            )
    return out


def choose_double(items: Sequence[SampledItem], n: int, seed: int) -> list[SampledItem]:
    """Mark a stratified (proportional) random subset of ``n`` items for the second annotator."""
    by_stratum: dict[str, list[SampledItem]] = {}
    for it in sorted(items, key=lambda it: it.item_id):
        by_stratum.setdefault(it.stratum, []).append(it)
    alloc = largest_remainder({k: len(v) for k, v in by_stratum.items()}, min(n, len(items)))
    chosen: set[str] = set()
    for k, v in sorted(by_stratum.items()):
        chosen.update(it.item_id for it in rng_for(seed, "double", k).sample(v, alloc[k]))
    return [replace(it, double=it.item_id in chosen) for it in items]


def sheet_order(
    items: Sequence[SampledItem], seed: int, set_name: str, annotator: str
) -> list[SampledItem]:
    """Group items by question; shuffle question and passage order per annotator."""
    groups: dict[str, list[SampledItem]] = {}
    for it in sorted(items, key=lambda it: it.item_id):
        groups.setdefault(f"{it.source}|{it.qid}", []).append(it)
    keys = sorted(groups)
    rng = rng_for(seed, "order", set_name, annotator)
    rng.shuffle(keys)
    out: list[SampledItem] = []
    for key in keys:
        g = list(groups[key])
        rng.shuffle(g)
        out.extend(g)
    return out


def stratum_counts(items: Iterable[SampledItem]) -> dict[str, int]:
    return dict(sorted(Counter(it.stratum for it in items).items()))
