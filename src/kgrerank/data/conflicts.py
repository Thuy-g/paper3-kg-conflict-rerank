"""CONFLICTS (google-research-datasets/rag_conflicts, ``conflicts.jsonl``) → schema v1.

Conflict labels in CONFLICTS are per query (``conflict_type``), not per passage, so passages are
UNKNOWN/unlabelled and the category is kept in ``meta.conflict_category``. Passage text is
third-party web content: use locally, never redistribute.
"""

from __future__ import annotations

from typing import Any

from kgrerank.schema import Candidate, Example

LICENCE_NOTE = "repo Apache-2.0; passages are third-party web content (local use only)"


def convert_conflicts(
    record: dict[str, Any], index: int, text_field: str = "short_text", max_chars: int = 2000
) -> Example:
    cands = []
    result_meta = []
    for j, r in enumerate(record.get("search_results", [])):
        text = (r.get(text_field) or r.get("snippet") or "").strip()[:max_chars]
        pid = f"r{j}"
        cands.append(Candidate(pid=pid, title=(r.get("title") or "").strip(), text=text))
        result_meta.append({"pid": pid, "url": r.get("url"), "date": r.get("date")})
    answer = (record.get("correct_answer") or "").strip()
    return Example(
        qid=f"conflicts-{index}",
        question=record["question"],
        answers=[answer] if answer else [],
        candidates=cands,
        meta={
            "source": "conflicts",
            "synthetic": False,
            "kg_derived": False,
            "license": LICENCE_NOTE,
            "conflict_category": record.get("conflict_type"),
            "origin_dataset": record.get("source"),
            "text_field": text_field,
            "results": result_meta,
        },
    )
