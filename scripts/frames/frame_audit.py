#!/usr/bin/env python3
"""Human audit of parsed frames.

frame_audit.py sample  --config configs/frames_v1.yaml   -> blind sheet for the auditor
frame_audit.py compare --config configs/frames_v1.yaml --sheet <filled.csv>
    -> agreement per field (parser vs human) and human frames for the separate
       human-framed diagnostic run (never mixed with the automatic pipeline results)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "frames"))

from parse_frames import questions_for  # noqa: E402

from kgrerank.annotation.schema import read_jsonl, write_jsonl  # noqa: E402
from kgrerank.frames.audit import audit_sample, compare, human_frames, write_blind_sheet  # noqa: E402
from kgrerank.frames.schema import InferenceFrame, Snapshot  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["sample", "compare"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--sheet")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out_dir = ROOT / cfg["out_dir"]
    qs = questions_for(ROOT / cfg["annotation_dir"], "main")
    if args.command == "sample":
        sample = audit_sample(qs, int(cfg["audit"]["n_questions"]), int(cfg["audit"]["seed"]))
        notes = {
            k: (
                f"Relative time refers to {v.get('start')}..{v.get('end')}"
                if v.get("start")
                else "No snapshot defined"
            )
            for k, v in cfg["snapshots"].items()
        }
        sheet = out_dir / "frame_audit_sheet.csv"
        if sheet.exists():
            raise SystemExit(f"{sheet} exists; not overwriting")
        write_blind_sheet(sheet, sample, notes)
        print(f"{len(sample)} questions -> {sheet}")
        return 0
    with Path(args.sheet).open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    snaps = {k: Snapshot.from_dict(v) for k, v in cfg["snapshots"].items()}
    source_of = {q["qid"]: q["source"] for q in qs}
    human = human_frames(rows, snaps, source_of)
    parsed = {
        f["qid"]: InferenceFrame.from_dict(f) for f in read_jsonl(out_dir / "frames_main.jsonl")
    }
    write_jsonl(out_dir / "frames_main_human_audit.jsonl", [f.to_dict() for f in human.values()])
    rep = compare(parsed, human)
    (out_dir / "frame_audit_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
