"""Keep the committed template and JSON schema in sync with the code constants."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from kgrerank.annotation.schema import (
    ANSWER_SUPPORT,
    CONFIDENCE,
    DECISIONS,
    FLAGS,
    ITEM_FIELDS,
    LABEL_FIELDS,
    record_from_row,
    record_problems,
)
from kgrerank.schema import REASON_TYPES

DOCS = Path(__file__).resolve().parents[1] / "docs" / "annotation"


def test_template_matches_code_and_validates():
    with (DOCS / "templates" / "annotation_template.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == [*ITEM_FIELDS, *LABEL_FIELDS]
    for row in rows:
        assert "SYNTHETIC" in row["question"]
        errors, _ = record_problems(record_from_row(row, "EX", "v0"))
        assert not errors


def test_json_schema_enums_match_code():
    schema = json.loads((DOCS / "annotation_record.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    assert tuple(props["decision"]["enum"]) == DECISIONS
    assert tuple(props["reasons"]["items"]["enum"]) == REASON_TYPES
    assert tuple(props["answer_support"]["enum"]) == ANSWER_SUPPORT
    assert tuple(props["confidence"]["enum"]) == CONFIDENCE
    assert tuple(props["flags"]["items"]["enum"]) == FLAGS


def test_codebook_lists_every_reason_type():
    text = (DOCS / "codebook_v0.md").read_text(encoding="utf-8")
    assert all(f"`{r}`" in text for r in REASON_TYPES)
