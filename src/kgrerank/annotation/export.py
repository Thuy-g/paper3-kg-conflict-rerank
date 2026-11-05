"""Export adjudicated annotations to schema v1 examples with full candidate pools.

Pools are rebuilt from the source files with the same converters as the harness; the text of
every annotated passage is checked against the sha256 recorded at sampling time.

* Semantic labels come only from the annotation (label_source "manual"); unannotated passages
  stay UNKNOWN with label_source "unlabelled" (unjudged, which is different from a human
  UNKNOWN).
* Relevance (``is_gold``) and its coverage are recorded explicitly:
  - 2Wiki: relevance_source "dataset_supporting_facts"; judgments cover the whole pool
    (``meta.relevance_judged_pids`` = all pids). The dataset flags are also kept in
    ``meta.dataset_supporting_pids``, apart from the human labels.
  - CONFLICTS: relevance_source "human_answer_support" (answer_support == "yes");
    judgments cover only annotated passages, so full-list retrieval metrics are not reported
    and condensed ones are (kgrerank.metrics.retrieval).
* A 2Wiki supporting fact that annotators labelled CONTRADICTING cannot be gold under schema v1;
  it is exported with is_gold False and listed in the export report (never silently merged).
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
    report: dict[str, Any] | None = None,
) -> list[Example]:
    report = report if report is not None else {}
    report.setdefault("dataset_gold_vs_human_contradicting", [])
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
        dataset_gold = (
            sorted(c.pid for c in ex.candidates if c.is_gold) if source == "twowiki" else []
        )
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
                is_gold = c.is_gold
                if is_gold and decision is Decision.CONTRADICTING:
                    report["dataset_gold_vs_human_contradicting"].append(g["item_id"])
                    is_gold = False
            ev = Evidence(
                "note",
                f"annotation:{g['item_id']}",
                {
                    "codebook_version": g["codebook_version"],
                    "double_annotated": g["double_annotated"],
                    "adjudication": g["adjudication"]["method"],
                    "answer_support": fin["answer_support"],
                    "dataset_supporting_fact": c.pid in dataset_gold
                    if source == "twowiki"
                    else None,
                },
            )
            cands.append(
                Candidate(
                    c.pid, c.title, c.text, is_gold, decision, list(fin["reasons"]), "manual", [ev]
                )
            )
        complete = source == "twowiki"
        meta = {
            **ex.meta,
            "annotation_set": set_name,
            "synthetic": False,
            "annotated_pids": sorted(labels),
            "relevance_source": "dataset_supporting_facts" if complete else "human_answer_support",
            "relevance_judged_pids": sorted(c.pid for c in ex.candidates)
            if complete
            else sorted(labels),
            "dataset_supporting_pids": dataset_gold,
        }
        new = Example(ex.qid, ex.question, ex.answers, cands, meta)
        validate_example(new)
        out.append(new)
    return out
