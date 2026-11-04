"""File layout of one annotation sample directory (e.g. data/annotation/v1, gitignored)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kgrerank.annotation.schema import AnnotationItem, read_jsonl


@dataclass(frozen=True)
class Layout:
    root: Path

    @property
    def key(self) -> Path:  # NOT for annotators: contains strata and source positions
        return self.root / "key.jsonl"

    def items(self, set_name: str) -> Path:
        return self.root / f"items_{set_name}.jsonl"

    def sheet(self, set_name: str, annotator: str) -> Path:
        return self.root / "sheets" / f"{set_name}_{annotator}.csv"

    def submission(self, set_name: str, annotator: str) -> Path:
        return self.root / "submissions" / f"{set_name}_{annotator}.jsonl"

    def submission_meta(self, set_name: str, annotator: str) -> Path:
        return self.root / "submissions" / f"{set_name}_{annotator}.submission.json"

    def agreement(self, set_name: str, suffix: str) -> Path:
        return self.root / "agreement" / f"{set_name}_report.{suffix}"

    def adjudication_sheet(self, set_name: str) -> Path:
        return self.root / "adjudication" / f"{set_name}_sheet.csv"

    def gold(self, set_name: str) -> Path:
        return self.root / "adjudication" / f"{set_name}_gold.jsonl"

    def gold_meta(self, set_name: str) -> Path:
        return self.root / "adjudication" / f"{set_name}_gold.manifest.json"

    def gold_examples(self, set_name: str) -> Path:
        return self.root / f"gold_examples_{set_name}.jsonl"


def load_key(layout: Layout) -> dict[str, dict[str, Any]]:
    return {r["item_id"]: r for r in read_jsonl(layout.key)}


def load_items(layout: Layout, set_name: str) -> dict[str, AnnotationItem]:
    return {r["item_id"]: AnnotationItem(**r) for r in read_jsonl(layout.items(set_name))}


def assigned_ids(
    key: dict[str, dict[str, Any]], set_name: str, annotator: str, secondary: str
) -> set[str]:
    """Annotator 1 gets every item of the set; the secondary annotator gets the pilot and the
    double-annotation subset of the main set."""
    ids = {iid for iid, k in key.items() if k["set"] == set_name}
    if annotator == secondary and set_name == "main":
        ids = {iid for iid in ids if key[iid]["double"]}
    return ids
