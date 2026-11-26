"""2WikiMultiHopQA (original JSON format) → schema v1.

Supporting-fact passages are gold and COMPATIBLE (label_source = dataset). All other context
passages are UNKNOWN/unlabelled: distractors are not assumed IRRELEVANT. The dataset was built with
Wikidata (arXiv 2011.01060, abstract), so ``meta.kg_derived = True``.
"""

from __future__ import annotations

from typing import Any

from kgrerank.schema import Candidate, Decision, Evidence, Example

LICENCE_NOTE = (
    "data licence [UNVERIFIED]: repo Alab-NII/2wikimultihop is Apache-2.0 (LICENSE), README states "
    "no separate data licence; copy taken from the Relink fork (MIT); local use only"
)


def convert_2wiki(record: dict[str, Any], source: str = "2wikimultihopqa") -> Example:
    sf: dict[str, list[int]] = {}
    for title, sent_id in record.get("supporting_facts", []):
        sf.setdefault(title, []).append(int(sent_id))
    cands = []
    for i, (title, sentences) in enumerate(record["context"]):
        text = " ".join(s.strip() for s in sentences)
        if title in sf:
            cands.append(
                Candidate(
                    pid=f"p{i}",
                    title=title,
                    text=text,
                    is_gold=True,
                    decision=Decision.COMPATIBLE,
                    label_source="dataset",
                    evidence=[
                        Evidence("dataset_field", "supporting_facts", {"sent_ids": sf[title]})
                    ],
                )
            )
        else:
            cands.append(Candidate(pid=f"p{i}", title=title, text=text))
    return Example(
        qid=str(record["_id"]),
        question=record["question"],
        answers=[str(record["answer"])],
        candidates=cands,
        meta={
            "source": source,
            "synthetic": False,
            "kg_derived": True,
            "license": LICENCE_NOTE,
            "question_type": record.get("type"),
            "evidences": record.get("evidences", []),
        },
    )
