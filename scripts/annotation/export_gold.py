#!/usr/bin/env python3
"""Export adjudicated gold labels to schema v1 examples with full candidate pools (offline).

Usage: export_gold.py --config configs/annotation_v1.yaml --set main
Writes data/annotation/<version>/gold_examples_<set>.jsonl for the evaluation harness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.annotation.export import gold_examples  # noqa: E402
from kgrerank.annotation.layout import Layout, load_key  # noqa: E402
from kgrerank.annotation.schema import read_jsonl  # noqa: E402
from kgrerank.schema import write_jsonl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--set", default="main", choices=["pilot", "main"])
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    layout = Layout(ROOT / cfg["out_dir"])
    sc = cfg["sources"]["conflicts"]
    with (ROOT / sc["path"]).open(encoding="utf-8") as fh:
        conflicts = [json.loads(line) for line in fh if line.strip()]
    twowiki = json.loads((ROOT / cfg["sources"]["twowiki"]["path"]).read_text(encoding="utf-8"))
    examples = gold_examples(
        read_jsonl(layout.gold(args.set)),
        load_key(layout),
        conflicts,
        twowiki,
        sc["text_field"],
        int(sc["max_chars"]),
        f"annotation_{cfg['sample_version']}_{args.set}",
    )
    n = write_jsonl(layout.gold_examples(args.set), examples)
    print(f"{n} examples -> {layout.gold_examples(args.set)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
