"""Adjudication after independent submission (docs/ANNOTATION_GUIDELINES.md §7).

Both annotators' pre-adjudication labels are kept verbatim next to the final label. Items with
full agreement (decision, reason set, answer_support) are finalised automatically; every other
double-annotated item needs an adjudicated row with a method, an adjudicator and a note.
Single-annotated items keep annotator 1's labels and are marked as such.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kgrerank.annotation.schema import (
    AnnotationItem,
    AnnotationRecord,
    record_from_row,
    record_problems,
    record_to_dict,
)

ADJ_METHODS = ("discussion", "third_annotator", "owner_decision")


def load_submission(
    rows: Sequence[dict[str, Any]], annotator_id: str, codebook_version: str, expected_ids: set[str]
) -> tuple[dict[str, AnnotationRecord], list[str], list[str]]:
    """Parse and validate one annotator's filled sheet against the item IDs assigned to them."""
    errors: list[str] = []
    warnings: list[str] = []
    recs: dict[str, AnnotationRecord] = {}
    for row in rows:
        rec = record_from_row(row, annotator_id, codebook_version)
        if rec.item_id in recs:
            errors.append(f"item {rec.item_id}: duplicated row")
            continue
        e, w = record_problems(rec)
        errors.extend(e)
        warnings.extend(w)
        recs[rec.item_id] = rec
    missing = sorted(expected_ids - set(recs))
    extra = sorted(set(recs) - expected_ids)
    if missing:
        errors.append(f"{len(missing)} assigned items not annotated, e.g. {missing[:3]}")
    if extra:
        errors.append(f"{len(extra)} rows for items not assigned to {annotator_id}: {extra[:3]}")
    return recs, errors, warnings


def prepare_sheet(
    a1: dict[str, AnnotationRecord],
    a2: dict[str, AnnotationRecord],
    items: dict[str, AnnotationItem],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (IDs agreed on all labels, adjudication rows for every other overlapping item)."""
    agreed, rows = [], []
    for iid in sorted(set(a1) & set(a2)):
        x, y = a1[iid], a2[iid]
        if x.labels() == y.labels():
            agreed.append(iid)
            continue
        it = items[iid]
        rows.append(
            {
                "item_id": iid,
                "question": it.question,
                "reference_answer": it.reference_answer,
                "passage_date": it.passage_date,
                "passage_text": it.passage_text,
                "A1_decision": x.decision,
                "A1_reasons": ";".join(sorted(x.reasons)),
                "A1_answer_support": x.answer_support,
                "A1_rationale": x.rationale,
                "A2_decision": y.decision,
                "A2_reasons": ";".join(sorted(y.reasons)),
                "A2_answer_support": y.answer_support,
                "A2_rationale": y.rationale,
                "final_decision": "",
                "final_reasons": "",
                "final_answer_support": "",
                "adjudication_method": "",
                "adjudicator": "",
                "note": "",
            }
        )
    return agreed, rows


def merge_gold(
    a1: dict[str, AnnotationRecord],
    a2: dict[str, AnnotationRecord],
    adjudicated_rows: Sequence[dict[str, Any]],
    codebook_version: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Final gold records for all items of annotator 1, keeping pre-adjudication labels."""
    errors: list[str] = []
    adj = {str(r["item_id"]).strip(): r for r in adjudicated_rows}
    gold = []
    for iid in sorted(a1):
        x = a1[iid]
        rec: dict[str, Any] = {
            "item_id": iid,
            "codebook_version": codebook_version,
            "pre_adjudication": {"A1": record_to_dict(x)},
        }
        if iid not in a2:
            rec.update(
                final=x.labels(),
                double_annotated=False,
                adjudication={"method": "single_annotator", "adjudicator": "", "note": ""},
            )
            gold.append(rec)
            continue
        y = a2[iid]
        rec["pre_adjudication"]["A2"] = record_to_dict(y)
        rec["double_annotated"] = True
        if x.labels() == y.labels():
            rec.update(
                final=x.labels(),
                adjudication={"method": "agreement", "adjudicator": "", "note": ""},
            )
            gold.append(rec)
            continue
        row = adj.get(iid)
        if row is None:
            errors.append(f"item {iid}: disagreement without an adjudicated row")
            continue
        final = record_from_row(
            {
                "item_id": iid,
                "decision": row.get("final_decision", ""),
                "reasons": row.get("final_reasons", ""),
                "answer_support": row.get("final_answer_support", ""),
                "rationale": row.get("note", ""),
            },
            "ADJ",
            codebook_version,
        )
        e, _ = record_problems(final)
        errors.extend(e)
        method = str(row.get("adjudication_method", "")).strip()
        if method not in ADJ_METHODS:
            errors.append(f"item {iid}: adjudication_method must be one of {ADJ_METHODS}")
        if not str(row.get("adjudicator", "")).strip() or not str(row.get("note", "")).strip():
            errors.append(f"item {iid}: adjudicator and note are required")
        rec.update(
            final=final.labels(),
            adjudication={
                "method": method,
                "adjudicator": str(row.get("adjudicator", "")).strip(),
                "note": str(row.get("note", "")).strip(),
            },
        )
        gold.append(rec)
    return gold, errors
