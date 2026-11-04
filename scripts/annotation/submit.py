#!/usr/bin/env python3
"""Validate and freeze one annotator's filled sheet (independent submission).

Usage: submit.py --sample-dir data/annotation/v1 --set pilot|main --annotator A1 \
                 --codebook v1 --file <filled .csv or .jsonl> [--secondary A2]
On success writes submissions/<set>_<annotator>.jsonl and a .submission.json with the sha256 of
the raw and normalised files: these are the pre-adjudication labels and must not be edited.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.annotation.adjudication import load_submission  # noqa: E402
from kgrerank.annotation.layout import Layout, assigned_ids, load_key  # noqa: E402
from kgrerank.annotation.schema import read_rows, record_to_dict, write_jsonl  # noqa: E402
from kgrerank.manifest import sha256_file, utc_now, write_manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-dir", required=True)
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    ap.add_argument("--annotator", required=True)
    ap.add_argument("--secondary", default="A2")
    ap.add_argument("--codebook", required=True, help="codebook version used, e.g. v0 or v1")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()
    layout = Layout(ROOT / args.sample_dir)
    out = layout.submission(args.set, args.annotator)
    if out.exists():
        raise SystemExit(f"{out} exists: submissions are frozen; use a new codebook version")
    key = load_key(layout)
    expected = assigned_ids(key, args.set, args.annotator, args.secondary)
    recs, errors, warnings = load_submission(
        read_rows(args.file), args.annotator, args.codebook, expected
    )
    for w in warnings:
        print("WARNING", w)
    if errors:
        for e in errors:
            print("ERROR", e)
        return 1
    write_jsonl(out, [record_to_dict(recs[i]) for i in sorted(recs)])
    write_manifest(
        layout.submission_meta(args.set, args.annotator),
        {
            "set": args.set,
            "annotator": args.annotator,
            "codebook_version": args.codebook,
            "n_items": len(recs),
            "submitted_utc": utc_now(),
            "raw_file": str(Path(args.file).name),
            "raw_sha256": sha256_file(args.file),
            "normalised_sha256": sha256_file(out),
            "warnings": warnings,
        },
    )
    print(f"frozen {len(recs)} records -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
