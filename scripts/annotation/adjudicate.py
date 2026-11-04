#!/usr/bin/env python3
"""Adjudication after both independent submissions are frozen.

adjudicate.py prepare --sample-dir data/annotation/v1 --set main
    -> adjudication/<set>_sheet.csv with both annotators' labels for every disagreement
adjudicate.py merge --sample-dir data/annotation/v1 --set main --codebook v1
    -> adjudication/<set>_gold.jsonl (final + pre-adjudication labels) and a manifest with the
       sha256 of every input, proving the pre-adjudication labels were not changed.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.annotation.adjudication import merge_gold, prepare_sheet  # noqa: E402
from kgrerank.annotation.layout import Layout, load_items  # noqa: E402
from kgrerank.annotation.schema import read_jsonl, read_rows, record_from_dict, write_jsonl  # noqa: E402
from kgrerank.manifest import sha256_file, utc_now, write_manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["prepare", "merge"])
    ap.add_argument("--sample-dir", required=True)
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    ap.add_argument("--a1", default="A1")
    ap.add_argument("--a2", default="A2")
    ap.add_argument("--codebook", default="v1")
    args = ap.parse_args()
    layout = Layout(ROOT / args.sample_dir)
    p1, p2 = layout.submission(args.set, args.a1), layout.submission(args.set, args.a2)
    a1 = {r["item_id"]: record_from_dict(r) for r in read_jsonl(p1)}
    a2 = {r["item_id"]: record_from_dict(r) for r in read_jsonl(p2)}
    sheet = layout.adjudication_sheet(args.set)
    if args.command == "prepare":
        if sheet.exists():
            raise SystemExit(f"{sheet} exists; do not overwrite adjudication work")
        agreed, rows = prepare_sheet(a1, a2, load_items(layout, args.set))
        sheet.parent.mkdir(parents=True, exist_ok=True)
        with sheet.open("w", encoding="utf-8", newline="") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
        print(f"{len(agreed)} items agree on all labels; {len(rows)} to adjudicate -> {sheet}")
        return 0
    rows = read_rows(sheet) if sheet.exists() and sheet.stat().st_size else []
    gold, errors = merge_gold(a1, a2, rows, args.codebook)
    if errors:
        for e in errors:
            print("ERROR", e)
        return 1
    write_jsonl(layout.gold(args.set), gold)
    inputs = {"A1": p1, "A2": p2} | ({"sheet": sheet} if rows else {})
    write_manifest(
        layout.gold_meta(args.set),
        {
            "set": args.set,
            "codebook_version": args.codebook,
            "merged_utc": utc_now(),
            "n_gold": len(gold),
            "n_double": sum(g["double_annotated"] for g in gold),
            "methods": {
                m: sum(g["adjudication"]["method"] == m for g in gold)
                for m in sorted({g["adjudication"]["method"] for g in gold})
            },
            "inputs_sha256": {k: sha256_file(v) for k, v in inputs.items()},
            "gold_sha256": sha256_file(layout.gold(args.set)),
        },
    )
    print(f"wrote {len(gold)} gold records -> {layout.gold(args.set)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
