#!/usr/bin/env python3
"""Build ≤200-example slices from local source files and write manifests (no network).

Usage: slice_local_sources.py --config configs/local_slices.yaml
Outputs: data/slices/<name>/examples.jsonl (gitignored) and manifests/<name>_slice.json.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.data.conflicts import LICENCE_NOTE as CONFLICTS_LICENCE  # noqa: E402
from kgrerank.data.conflicts import convert_conflicts  # noqa: E402
from kgrerank.data.ragability import LICENCE_NOTE as RAGABILITY_LICENCE  # noqa: E402
from kgrerank.data.ragability import convert_ragability  # noqa: E402
from kgrerank.data.twowiki import LICENCE_NOTE as TWOWIKI_LICENCE  # noqa: E402
from kgrerank.data.twowiki import convert_2wiki  # noqa: E402
from kgrerank.manifest import git_state, sha256_file, utc_now, write_manifest  # noqa: E402
from kgrerank.schema import write_jsonl  # noqa: E402

MAX_EXAMPLES = 200


def _select(n_total: int, n: int, seed: int, name: str) -> list[int]:
    n = min(n, n_total, MAX_EXAMPLES)
    return sorted(random.Random(f"{seed}|{name}").sample(range(n_total), n))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    cfg = yaml.safe_load(Path(ap.parse_args().config).read_text(encoding="utf-8"))
    seed = int(cfg["seed"])
    for name, src in cfg["sources"].items():
        path = (ROOT / src["path"]).resolve()
        if not path.exists():
            print(f"[skip] {name}: source not found at {src['path']}")
            continue
        if name == "twowiki_relink":
            records = json.loads(path.read_text(encoding="utf-8"))
            idx = _select(len(records), int(src["n"]), seed, name)
            examples = [convert_2wiki(records[i], source="2wikimultihopqa(relink-sample)") for i in idx]
            licence = TWOWIKI_LICENCE
        elif name == "conflicts":
            with path.open(encoding="utf-8") as fh:
                records = [json.loads(line) for line in fh if line.strip()]
            idx = _select(len(records), int(src["n"]), seed, name)
            examples = [
                convert_conflicts(records[i], i, src.get("text_field", "short_text"),
                                  int(src.get("max_chars", 2000)))
                for i in idx
            ]
            licence = CONFLICTS_LICENCE
        elif name == "ragability":
            with path.open(encoding="utf-8") as fh:
                records = [json.loads(line) for line in fh if line.strip()]
            idx = _select(len(records), int(src["n"]), seed, name)
            ref = src.get("reference", "context_1")
            examples = [convert_ragability(records[i], i, ref) for i in idx]
            licence = RAGABILITY_LICENCE
        else:
            print(f"[skip] {name}: no converter")
            continue
        out = ROOT / cfg["out_dir"] / name / "examples.jsonl"
        n = write_jsonl(out, examples)
        manifest = {
            "name": name,
            "created_utc": utc_now(),
            "script": "scripts/data/slice_local_sources.py",
            "script_sha256": sha256_file(Path(__file__)),
            "repo_git": git_state(ROOT),
            "source_path": src["path"],
            "source_sha256": sha256_file(path),
            "source_records": len(records),
            "selection": {"method": "random.Random(f'{seed}|{name}').sample, sorted", "seed": seed,
                          "indices": idx},
            "output_path": str(out.relative_to(ROOT)),
            "output_sha256": sha256_file(out),
            "output_bytes": out.stat().st_size,
            "n_examples": n,
            "licence": licence,
            "committed": "manifest only; examples stay in data/ (gitignored)",
        }
        write_manifest(ROOT / cfg["manifest_dir"] / f"{name}_slice.json", manifest)
        print(f"{name}: {n} examples, {out.stat().st_size} bytes -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
