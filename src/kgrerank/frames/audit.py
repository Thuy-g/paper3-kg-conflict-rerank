"""Human audit of automatically parsed frames (independent of passage labels).

* ``audit_sample``: deterministic, stratified choice of questions (seeded; uses only question IDs
  and dataset strata, never passage labels or parser output).
* Blind sheet: the auditor sees the question and the snapshot note only (not the parser output).
* ``compare``: per-field agreement between parser frames and human frames.
* ``human_frames``: the audited frames as InferenceFrames (source "human_audit") for the
  human-framed diagnostic run, which is reported separately from the automatic pipeline.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from kgrerank.annotation.sampling import largest_remainder, rng_for
from kgrerank.frames.parser import resolve_time
from kgrerank.frames.schema import InferenceFrame, Snapshot

SHEET_FIELDS = (
    "qid",
    "question",
    "snapshot_note",
    "subject_mention",
    "subject_qid",
    "relation_mention",
    "property_pid",
    "time_expression",
    "question_type",
    "notes",
)
NONE_MARKS = {"", "NONE", "AMBIGUOUS", "UNKNOWN"}


def audit_sample(questions: Sequence[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    """``questions``: dicts with qid, question, stratum. Proportional by stratum, seeded."""
    by: dict[str, list[dict[str, Any]]] = {}
    for q in sorted(questions, key=lambda q: q["qid"]):
        by.setdefault(q["stratum"], []).append(q)
    alloc = largest_remainder({k: len(v) for k, v in by.items()}, min(n, len(questions)))
    out = []
    for k in sorted(by):
        out.extend(rng_for(seed, "frame_audit", k).sample(by[k], alloc[k]))
    return sorted(out, key=lambda q: q["qid"])


def write_blind_sheet(
    path: str | Path, sample: Sequence[dict[str, Any]], notes: dict[str, str]
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(SHEET_FIELDS))
        w.writeheader()
        for q in sample:
            w.writerow(
                {
                    "qid": q["qid"],
                    "question": q["question"],
                    "snapshot_note": notes.get(q["source"], ""),
                    **{k: "" for k in SHEET_FIELDS[3:]},
                }
            )


def human_frames(
    rows: Sequence[dict[str, Any]], snapshots: dict[str, Snapshot], source_of: dict[str, str]
) -> dict[str, InferenceFrame]:
    out = {}
    for r in rows:
        qid = r["qid"]
        subj = (r.get("subject_qid") or "").strip()
        pid = (r.get("property_pid") or "").strip()
        anchor, t_status = resolve_time(r.get("time_expression", ""), snapshots[source_of[qid]])
        out[qid] = InferenceFrame(
            qid=qid,
            question=r["question"],
            subject=None if subj.upper() in NONE_MARKS else subj,
            subject_mention=r.get("subject_mention", ""),
            subject_status="linked"
            if subj.upper() not in NONE_MARKS
            else ("ambiguous" if subj.upper() == "AMBIGUOUS" else "unlinked"),
            prop=None if pid.upper() in NONE_MARKS else pid,
            relation_mention=r.get("relation_mention", ""),
            prop_status="linked" if pid.upper() not in NONE_MARKS else "unlinked",
            time_anchor=anchor,
            time_expression=r.get("time_expression", ""),
            time_status=t_status,
            question_type=(r.get("question_type") or "other").strip(),
            source="human_audit",
            parser_version="human_frame_sheet_v1",
        )
    return out


def compare(parser: dict[str, InferenceFrame], human: dict[str, InferenceFrame]) -> dict[str, Any]:
    qids = sorted(set(parser) & set(human))

    def agree(fn) -> dict[str, Any]:
        hits = [fn(parser[q], human[q]) for q in qids]
        return {
            "n": len(hits),
            "agree": sum(hits),
            "share": (sum(hits) / len(hits)) if hits else None,
        }

    supported_mismatch = [q for q in qids if parser[q].supported and not human[q].supported]
    return {
        "questions": len(qids),
        "subject": agree(lambda p, h: p.subject == h.subject),
        "property": agree(lambda p, h: p.prop == h.prop),
        "question_type": agree(lambda p, h: p.question_type == h.question_type),
        "time_status": agree(lambda p, h: p.time_status == h.time_status),
        "supported": agree(lambda p, h: p.supported == h.supported),
        "parser_supported_but_human_not": supported_mismatch,
    }
