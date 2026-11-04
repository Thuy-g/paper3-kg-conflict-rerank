"""Normalised example schema v1 (docs/PLAN.md B.1).

The semantic decision of a candidate passage is stored separately from the reason types that
describe *why* it disagrees on the surface with the gold answer. A reason never fixes the decision
on its own: unlabelled or under-evidenced passages are ``UNKNOWN``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Decision(StrEnum):
    """Semantic relation of a passage to the gold answer under the question's scope."""

    COMPATIBLE = "COMPATIBLE"
    CONTRADICTING = "CONTRADICTING"
    IRRELEVANT = "IRRELEVANT"
    UNKNOWN = "UNKNOWN"


REASON_TYPES: tuple[str, ...] = (
    "alias",
    "historical_identity",
    "hierarchy",
    "geographic_granularity",
    "temporal_scope",
    "entity_identity_mismatch",
    "homonym",
    "inverse_relation",
    "predicate_mismatch",
    "counterfactual",
    "unknown",
)
LABEL_SOURCES: tuple[str, ...] = ("dataset", "perturbation_rule_v0", "manual", "unlabelled")
EVIDENCE_KINDS: tuple[str, ...] = (
    "kg_statement",
    "kg_entity",
    "kg_property",
    "dataset_field",
    "note",
)


class SchemaError(ValueError):
    """Raised when an example violates schema v1."""


@dataclass(frozen=True)
class Evidence:
    """One piece of evidence behind a label (KG statement, entity record, dataset field, ...)."""

    kind: str
    ref: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Candidate:
    """A passage in the fixed candidate evidence pool of one question."""

    pid: str
    title: str
    text: str
    is_gold: bool = False
    decision: Decision = Decision.UNKNOWN
    reasons: list[str] = field(default_factory=list)
    label_source: str = "unlabelled"
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Example:
    """A question with its answers and fixed candidate pool."""

    qid: str
    question: str
    answers: list[str]
    candidates: list[Candidate]
    meta: dict[str, Any] = field(default_factory=dict)

    def candidate(self, pid: str) -> Candidate:
        for cand in self.candidates:
            if cand.pid == pid:
                return cand
        raise KeyError(pid)

    @property
    def gold_pids(self) -> set[str]:
        return {c.pid for c in self.candidates if c.is_gold}


def candidate_problems(cand: Candidate) -> list[str]:
    """Return the schema violations of one candidate (empty list if valid)."""
    out: list[str] = []
    where = f"candidate {cand.pid!r}"
    if not isinstance(cand.pid, str) or not cand.pid:
        out.append(f"{where}: pid must be a non-empty string")
    if not isinstance(cand.text, str) or not isinstance(cand.title, str):
        out.append(f"{where}: title and text must be strings")
    if not isinstance(cand.is_gold, bool):
        out.append(f"{where}: is_gold must be a bool")
    if not isinstance(cand.decision, Decision):
        out.append(f"{where}: decision must be a Decision")
    unknown_reasons = [r for r in cand.reasons if r not in REASON_TYPES]
    if unknown_reasons:
        out.append(f"{where}: unknown reason types {unknown_reasons}")
    if len(set(cand.reasons)) != len(cand.reasons):
        out.append(f"{where}: duplicated reason types {cand.reasons}")
    if cand.label_source not in LABEL_SOURCES:
        out.append(f"{where}: unknown label_source {cand.label_source!r}")
    for ev in cand.evidence:
        if ev.kind not in EVIDENCE_KINDS:
            out.append(f"{where}: unknown evidence kind {ev.kind!r}")
    if cand.is_gold and cand.decision is Decision.CONTRADICTING:
        out.append(f"{where}: a gold passage cannot be CONTRADICTING")
    if cand.label_source == "perturbation_rule_v0" and not cand.evidence:
        out.append(f"{where}: perturbation labels must carry evidence")
    if cand.label_source == "unlabelled" and cand.decision is not Decision.UNKNOWN:
        out.append(f"{where}: unlabelled passages must have decision UNKNOWN")
    return out


def validate_example(ex: Example) -> None:
    """Raise :class:`SchemaError` listing every violation of schema v1 in ``ex``."""
    problems: list[str] = []
    if not isinstance(ex.qid, str) or not ex.qid:
        problems.append("qid must be a non-empty string")
    if not isinstance(ex.question, str):
        problems.append("question must be a string")
    if not isinstance(ex.answers, list) or not all(isinstance(a, str) for a in ex.answers):
        problems.append("answers must be a list of strings")
    pids = [c.pid for c in ex.candidates]
    if len(set(pids)) != len(pids):
        problems.append("candidate pids must be unique")
    for cand in ex.candidates:
        problems.extend(candidate_problems(cand))
    if not isinstance(ex.meta.get("source"), str):
        problems.append("meta.source must be a string")
    if not isinstance(ex.meta.get("synthetic"), bool):
        problems.append("meta.synthetic must be a bool")
    if "kg_derived" in ex.meta and not isinstance(ex.meta["kg_derived"], bool):
        problems.append("meta.kg_derived must be a bool")
    if problems:
        raise SchemaError(f"example {ex.qid!r}: " + "; ".join(problems))


def evidence_to_dict(ev: Evidence) -> dict[str, Any]:
    return {"kind": ev.kind, "ref": ev.ref, "detail": dict(ev.detail)}


def candidate_to_dict(cand: Candidate) -> dict[str, Any]:
    return {
        "pid": cand.pid,
        "title": cand.title,
        "text": cand.text,
        "is_gold": cand.is_gold,
        "decision": cand.decision.value,
        "reasons": list(cand.reasons),
        "label_source": cand.label_source,
        "evidence": [evidence_to_dict(ev) for ev in cand.evidence],
    }


def example_to_dict(ex: Example) -> dict[str, Any]:
    return {
        "qid": ex.qid,
        "question": ex.question,
        "answers": list(ex.answers),
        "candidates": [candidate_to_dict(c) for c in ex.candidates],
        "meta": dict(ex.meta),
    }


def candidate_from_dict(d: dict[str, Any]) -> Candidate:
    try:
        decision = Decision(d.get("decision", "UNKNOWN"))
    except ValueError as err:
        raise SchemaError(
            f"candidate {d.get('pid')!r}: bad decision {d.get('decision')!r}"
        ) from err
    return Candidate(
        pid=d["pid"],
        title=d.get("title", ""),
        text=d["text"],
        is_gold=d.get("is_gold", False),
        decision=decision,
        reasons=list(d.get("reasons", [])),
        label_source=d.get("label_source", "unlabelled"),
        evidence=[
            Evidence(kind=e["kind"], ref=e["ref"], detail=dict(e.get("detail", {})))
            for e in d.get("evidence", [])
        ],
    )


def example_from_dict(d: dict[str, Any], validate: bool = True) -> Example:
    ex = Example(
        qid=d["qid"],
        question=d["question"],
        answers=list(d.get("answers", [])),
        candidates=[candidate_from_dict(c) for c in d["candidates"]],
        meta=dict(d.get("meta", {})),
    )
    if validate:
        validate_example(ex)
    return ex


def iter_jsonl(path: str | Path, validate: bool = True) -> Iterator[Example]:
    with Path(path).open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                yield example_from_dict(json.loads(line), validate=validate)
            except (KeyError, SchemaError) as err:
                raise SchemaError(f"{path}:{lineno}: {err}") from err


def read_jsonl(path: str | Path, validate: bool = True) -> list[Example]:
    return list(iter_jsonl(path, validate=validate))


def write_jsonl(path: str | Path, examples: Iterable[Example], validate: bool = True) -> int:
    """Write examples as JSON lines (sorted keys, UTF-8). Returns the number written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            if validate:
                validate_example(ex)
            fh.write(json.dumps(example_to_dict(ex), ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n
