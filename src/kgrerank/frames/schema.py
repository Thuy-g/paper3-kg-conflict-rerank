"""Inference frame: what a method may know about a question before reading any passage.

Kept separate from ``kgrerank.perturb.operators.QuestionFrame``, which carries the gold answer
for building synthetic examples. An ``InferenceFrame`` never contains answers, gold passage
labels, supporting-fact flags or annotation reasons. Uncertain parts stay unresolved: a subject
or property is set only when linking is unique; relative time is resolved only against a
configured benchmark snapshot, never against the date of the run.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from kgrerank.kg.time import Interval, TimeRange, year_period

QUESTION_TYPES = ("single_fact", "multi_hop", "comparison", "list_or_count", "other", "unparsed")
LINK_STATUSES = ("linked", "ambiguous", "unlinked", "not_parsed", "given")
TIME_STATUSES = ("explicit", "snapshot_relative", "none", "unresolved", "not_parsed", "given")


@dataclass(frozen=True)
class Snapshot:
    """Benchmark snapshot used for relative time ('current', 'this year'): a date window."""

    name: str
    start: tuple[int, int, int] | None = None
    end: tuple[int, int, int] | None = None
    basis: str = ""

    def defined(self) -> bool:
        return self.start is not None and self.end is not None

    def moment(self) -> Interval | None:
        """The snapshot moment: one (imprecise) day inside [start, end]."""
        if not self.defined():
            return None
        assert self.start and self.end
        return Interval.point(TimeRange(self.start, self.end))

    def year(self) -> int | None:
        if not self.defined() or self.start[0] != self.end[0]:  # type: ignore[index]
            return None
        return self.start[0]  # type: ignore[index]

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> Snapshot:
        d = d or {}

        def tup(x: str | None) -> tuple[int, int, int] | None:
            return tuple(int(p) for p in x.split("-")) if x else None  # type: ignore[return-value]

        return cls(d.get("name", ""), tup(d.get("start")), tup(d.get("end")), d.get("basis", ""))


@dataclass(frozen=True)
class InferenceFrame:
    qid: str
    question: str
    subject: str | None = None
    subject_mention: str = ""
    subject_status: str = "not_parsed"
    subject_candidates: tuple[str, ...] = ()
    prop: str | None = None
    relation_mention: str = ""
    prop_status: str = "not_parsed"
    time_anchor: Interval | None = None
    time_expression: str = ""
    time_status: str = "not_parsed"
    question_type: str = "unparsed"
    source: str = ""  # llm_parser | human_audit | synthetic_construction
    parser_version: str = ""
    model: str = ""
    errors: tuple[str, ...] = ()

    @property
    def supported(self) -> bool:
        """KG reasoning is attempted only for single-fact questions with linked subject/property
        and a time scope that is either absent, explicit, or resolved against the snapshot."""
        return (
            self.question_type == "single_fact"
            and self.subject_status in ("linked", "given")
            and self.prop_status in ("linked", "given")
            and self.time_status in ("explicit", "snapshot_relative", "none", "given")
            and not self.errors
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["time_anchor"] = _interval_to_dict(self.time_anchor)
        d["supported"] = self.supported
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> InferenceFrame:
        kw = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        kw["time_anchor"] = _interval_from_dict(d.get("time_anchor"))
        kw["subject_candidates"] = tuple(d.get("subject_candidates", ()))
        kw["errors"] = tuple(d.get("errors", ()))
        return cls(**kw)


def _interval_to_dict(iv: Interval | None) -> dict[str, Any] | None:
    if iv is None:
        return None
    return {
        "start": None if iv.start is None else [list(iv.start.lo), list(iv.start.hi)],
        "end": None if iv.end is None else [list(iv.end.lo), list(iv.end.hi)],
        "is_point": iv.is_point,
    }


def _interval_from_dict(d: dict[str, Any] | None) -> Interval | None:
    if not d:
        return None

    def rng(x: list | None) -> TimeRange | None:
        return None if x is None else TimeRange(tuple(x[0]), tuple(x[1]))  # type: ignore[arg-type]

    return Interval(rng(d.get("start")), rng(d.get("end")), bool(d.get("is_point")))


def frame_from_construction(qid: str, question: str, meta: dict[str, Any]) -> InferenceFrame | None:
    """Synthetic fixtures only: build an inference frame from construction metadata, dropping the
    gold answer. Subject, property and time anchor are question facts, not answers."""
    f = meta.get("frame")
    if not f:
        return None
    anchor = f.get("time_anchor_year")
    return InferenceFrame(
        qid=qid,
        question=question,
        subject=f["subject"],
        subject_status="given",
        prop=f["prop"],
        prop_status="given",
        time_anchor=year_period(anchor) if anchor is not None else None,
        time_status="given",
        question_type="single_fact",
        source="synthetic_construction",
        parser_version="construction_metadata",
    )
