"""Export adjudicated annotations to schema v1 examples with full candidate pools.

Pools are rebuilt from the source files with the same converters as the harness; the text of
every annotated passage is checked against the sha256 recorded at sampling time. Decisions come
only from the annotation: unannotated passages stay UNKNOWN/unlabelled. ``is_gold``: CONFLICTS
uses ``answer_support == "yes"``; 2Wiki keeps the dataset supporting-fact flag unless the
annotation says CONTRADICTING.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from kgrerank.annotation.sampling import sha256_text
from kgrerank.data.conflicts import convert_conflicts
from kgrerank.data.twowiki import convert_2wiki
from kgrerank.schema import Candidate, Decision, Evidence, Example, validate_example


def gold_examples(
    gold: Sequence[dict[str, Any]],
    key: dict[str, dict[str, Any]],
    conflicts_records: Sequence[dict[str, Any]],
    twowiki_records: Sequence[dict[str, Any]],
    text_field: str = "short_text",
    max_chars: int = 2000,
    set_name: str = "annotation_v1",
) -> list[Example]:
    by_q: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for g in gold:
        k = key[g["item_id"]]
        by_q.setdefault((k["source"], k["qid"]), []).append(g)
    twowiki_by_id = {str(r["_id"]): r for r in twowiki_records}
    out = []
    for (source, qid), recs in sorted(by_q.items()):
        if source == "conflicts":
            idx = int(qid.split("-", 1)[1])
            ex = convert_conflicts(conflicts_records[idx], idx, text_field, max_chars)
        else:
            ex = convert_2wiki(twowiki_by_id[qid])
        labels = {key[g["item_id"]]["pid"]: g for g in recs}
        cands = []
        for c in ex.candidates:
            g = labels.get(c.pid)
            if g is None:
                cands.append(
                    replace(
                        c,
                        decision=Decision.UNKNOWN,
                        reasons=[],
                        label_source="unlabelled",
                        evidence=[],
                    )
                )
                continue
            k = key[g["item_id"]]
            if sha256_text(c.text) != k["text_sha256"]:
                raise ValueError(f"{g['item_id']}: passage text differs from the sampled text")
            fin = g["final"]
            decision = Decision(fin["decision"])
            if source == "conflicts":
                is_gold = fin["answer_support"] == "yes"
            else:
                is_gold = c.is_gold and decision is not Decision.CONTRADICTING
            ev = Evidence(
                "note",
                f"annotation:{g['item_id']}",
                {
                    "codebook_version": g["codebook_version"],
                    "double_annotated": g["double_annotated"],
                    "adjudication": g["adjudication"]["method"],
                    "answer_support": fin["answer_support"],
                },
            )
            cands.append(
                Candidate(
                    c.pid, c.title, c.text, is_gold, decision, list(fin["reasons"]), "manual", [ev]
                )
            )
        meta = {
            **ex.meta,
            "annotation_set": set_name,
            "synthetic": False,
            "annotated_pids": sorted(labels),
        }
        new = Example(ex.qid, ex.question, ex.answers, cands, meta)
        validate_example(new)
        out.append(new)
    return out
