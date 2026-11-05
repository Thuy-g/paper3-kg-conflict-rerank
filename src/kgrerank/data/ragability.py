"""Ragability corpus rows (ofai/RagabilityCorpus, CC-BY-SA-4.0) → schema v1.

Dataset card semantics: context_1 and context_2 contradict each other; context_3 is not
contradictory to context_1 but contradicts context_2; context_4 contradicts no other context.
The card does not say which side is true (entities are fictional), so passage decisions are
**relative to a chosen reference side** (default context_1), recorded in ``meta.reference``.
Reason types are not annotated by the dataset, so contradicting passages get ``["unknown"]``.
A context whose relation to the query is "q.noinfo" (``qn``) gets decision UNKNOWN.
"""

from __future__ import annotations

from typing import Any

from kgrerank.schema import Candidate, Decision, Evidence, Example

LICENCE_NOTE = (
    "CC-BY-SA-4.0 (ofai/RagabilityCorpus); attribution required; derived public data must be "
    "share-alike; local use only"
)
UNEQUIVOCAL = {"qeu", "qiu"}


def convert_ragability(row: dict[str, Any], index: int, reference: str = "context_1") -> Example:
    if reference not in ("context_1", "context_2"):
        raise ValueError("reference must be context_1 or context_2")
    ref_n, other_n = ("1", "2") if reference == "context_1" else ("2", "1")
    rel = {"1": (row.get("c1xq") or "").strip(), "2": (row.get("c2xq") or "").strip()}
    card = Evidence("dataset_field", "dataset_card:context_relations", {"reference": reference})

    def ctx(n: str) -> str:
        return (row.get(f"context_{n}") or "").strip()

    cands = []
    ref_ok = rel[ref_n] != "qn"
    cands.append(
        Candidate(
            pid=f"c{ref_n}",
            title="",
            text=ctx(ref_n),
            is_gold=rel[ref_n] in UNEQUIVOCAL,
            decision=Decision.COMPATIBLE if ref_ok else Decision.UNKNOWN,
            label_source="dataset" if ref_ok else "unlabelled",
            evidence=[card, Evidence("dataset_field", f"c{ref_n}xq", {"value": rel[ref_n]})],
        )
    )
    other_ok = rel[other_n] != "qn"
    cands.append(
        Candidate(
            pid=f"c{other_n}",
            title="",
            text=ctx(other_n),
            decision=Decision.CONTRADICTING if other_ok else Decision.UNKNOWN,
            reasons=["unknown"] if other_ok else [],
            label_source="dataset" if other_ok else "unlabelled",
            evidence=[card, Evidence("dataset_field", f"c{other_n}xq", {"value": rel[other_n]})],
        )
    )
    c3 = (row.get("context_3_nc1_c2") or "").strip()
    if c3:
        # context_3 agrees with context_1 and contradicts context_2.
        dec3 = Decision.COMPATIBLE if reference == "context_1" else Decision.CONTRADICTING
        cands.append(
            Candidate(pid="c3", title="", text=c3, decision=dec3,
                      reasons=[] if dec3 is Decision.COMPATIBLE else ["unknown"],
                      label_source="dataset", evidence=[card])
        )
    c4 = (row.get("context_4_nc1_nc2_nc3") or "").strip()
    if c4:
        cands.append(
            Candidate(pid="c4", title="", text=c4, decision=Decision.COMPATIBLE,
                      label_source="dataset", evidence=[card])
        )
    answer = row.get(f"answer_context{ref_n}") or ""
    return Example(
        qid=f"ragability-{row.get('contradiction_ID')}-{index}",
        question=(row.get("query_text") or "").strip(),
        answers=[str(answer).strip()] if str(answer).strip() else [],
        candidates=cands,
        meta={
            "source": "ragability",
            "synthetic": False,
            "fictional_entities": True,
            "kg_derived": False,
            "license": LICENCE_NOTE,
            "reference": reference,
            "reference_note": "decisions are relative to the reference side; the dataset does "
            "not state which side is true",
            "reasoning_required": (row.get("reasoning_required_c1c2") or "").strip(),
            "wikicontradict_id": row.get("WikiContradict_ID"),
        },
    )
