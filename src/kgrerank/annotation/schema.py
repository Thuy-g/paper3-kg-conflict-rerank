"""Annotation item and record formats, validation, and CSV/JSONL I/O.

An *item* is what an annotator sees: (question, reference answer, passage). It never contains
the sampling stratum, dataset gold flags, method predictions, KG decisions or scores.
A *record* is one annotator's label for one item.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from kgrerank.schema import REASON_TYPES, Decision

DECISIONS: tuple[str, ...] = tuple(d.value for d in Decision)
ANSWER_SUPPORT: tuple[str, ...] = ("yes", "partial", "no", "unclear")
CONFIDENCE: tuple[str, ...] = ("high", "medium", "low", "")
FLAGS: tuple[str, ...] = (
    "passage_truncated",
    "passage_unreadable",
    "question_ambiguous",
    "reference_unclear",
    "reference_suspect",
    "needs_domain_knowledge",
)
ITEM_FIELDS: tuple[str, ...] = (
    "item_id",
    "question",
    "reference_answer",
    "passage_title",
    "passage_date",
    "passage_text",
)
LABEL_FIELDS: tuple[str, ...] = (
    "decision",
    "reasons",
    "answer_support",
    "confidence",
    "rationale",
    "reason_note",
    "flags",
)
LIST_SEP = ";"


@dataclass(frozen=True)
class AnnotationItem:
    """What the annotator sees (blinded)."""

    item_id: str
    question: str
    reference_answer: str
    passage_title: str
    passage_date: str
    passage_text: str


@dataclass
class AnnotationRecord:
    item_id: str
    annotator_id: str
    codebook_version: str
    decision: str
    reasons: list[str] = field(default_factory=list)
    answer_support: str = "unclear"
    confidence: str = ""
    rationale: str = ""
    reason_note: str = ""
    flags: list[str] = field(default_factory=list)

    def labels(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": sorted(self.reasons),
            "answer_support": self.answer_support,
        }


def record_problems(rec: AnnotationRecord) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one record. Errors block submission; warnings do not."""
    err: list[str] = []
    warn: list[str] = []
    where = f"item {rec.item_id}"
    if rec.decision not in DECISIONS:
        err.append(f"{where}: decision must be one of {DECISIONS}, got {rec.decision!r}")
    bad = [r for r in rec.reasons if r not in REASON_TYPES]
    if bad:
        err.append(f"{where}: unknown reasons {bad}")
    if len(set(rec.reasons)) != len(rec.reasons):
        err.append(f"{where}: duplicated reasons")
    if rec.answer_support not in ANSWER_SUPPORT:
        err.append(f"{where}: answer_support must be one of {ANSWER_SUPPORT}")
    if rec.confidence not in CONFIDENCE:
        err.append(f"{where}: confidence must be one of {CONFIDENCE[:-1]} or empty")
    bad_flags = [f for f in rec.flags if f not in FLAGS]
    if bad_flags:
        err.append(f"{where}: unknown flags {bad_flags}")
    if rec.decision in ("CONTRADICTING", "UNKNOWN") and not rec.rationale.strip():
        err.append(f"{where}: rationale is required for {rec.decision}")
    if rec.decision in ("CONTRADICTING", "IRRELEVANT") and rec.answer_support in ("yes", "partial"):
        err.append(f"{where}: a {rec.decision} passage cannot support the reference answer")
    if "unknown" in rec.reasons and not rec.reason_note.strip():
        warn.append(f"{where}: reason 'unknown' without reason_note")
    if rec.decision == "COMPATIBLE" and rec.answer_support == "unclear":
        warn.append(f"{where}: COMPATIBLE with answer_support 'unclear'")
    return err, warn


# ---------------------------------------------------------------------------------- I/O
def _split(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").split(LIST_SEP) if v.strip()]


def record_from_row(
    row: dict[str, Any], annotator_id: str, codebook_version: str
) -> AnnotationRecord:
    return AnnotationRecord(
        item_id=str(row["item_id"]).strip(),
        annotator_id=annotator_id,
        codebook_version=codebook_version,
        decision=str(row.get("decision", "")).strip().upper(),
        reasons=_split(row.get("reasons", "")),
        answer_support=str(row.get("answer_support", "")).strip().lower() or "unclear",
        confidence=str(row.get("confidence", "")).strip().lower(),
        rationale=str(row.get("rationale", "") or ""),
        reason_note=str(row.get("reason_note", "") or ""),
        flags=_split(row.get("flags", "")),
    )


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    """Read a filled sheet (.csv) or JSONL file into dict rows."""
    path = Path(path)
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_sheet(path: str | Path, items: Sequence[AnnotationItem]) -> None:
    """Blank annotation sheet: item columns filled, label columns empty."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[*ITEM_FIELDS, *LABEL_FIELDS])
        writer.writeheader()
        for it in items:
            writer.writerow({**asdict(it), **{k: "" for k in LABEL_FIELDS}})


def record_to_dict(rec: AnnotationRecord) -> dict[str, Any]:
    return asdict(rec)


def record_from_dict(d: dict[str, Any]) -> AnnotationRecord:
    return AnnotationRecord(**{k: d[k] for k in AnnotationRecord.__dataclass_fields__ if k in d})
