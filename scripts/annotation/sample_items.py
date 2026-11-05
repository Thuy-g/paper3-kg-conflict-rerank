#!/usr/bin/env python3
"""Deterministic, pre-registered sampling of annotation items (pilot, main, double subset).

Usage: sample_items.py --config configs/annotation_v1.yaml
Writes blinded items and blank sheets to data/annotation/<version>/ (gitignored) and the
pre-registration manifest (sampled IDs, seed, source hashes; no text) to manifests/.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.annotation.layout import Layout  # noqa: E402
from kgrerank.annotation.sampling import (  # noqa: E402
    choose_double,
    conflicts_frame,
    draw_conflicts,
    draw_twowiki,
    sheet_order,
    stratum_counts,
    twowiki_frame,
)
from kgrerank.annotation.schema import AnnotationItem, write_jsonl, write_sheet  # noqa: E402
from kgrerank.manifest import git_state, sha256_file, utc_now, write_manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing sample files and the pre-registered manifest",
    )
    ap.add_argument(
        "--rebuild-data",
        action="store_true",
        help="rewrite the gitignored item/sheet files only, after checking that the "
        "items equal the committed manifest; the manifest is never changed",
    )
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    seed, version = int(cfg["seed"]), str(cfg["sample_version"])
    sc, sw = cfg["sources"]["conflicts"], cfg["sources"]["twowiki"]
    c_path, w_path = (ROOT / sc["path"]).resolve(), (ROOT / sw["path"]).resolve()
    with c_path.open(encoding="utf-8") as fh:
        c_records = [json.loads(line) for line in fh if line.strip()]
    w_records = json.loads(w_path.read_text(encoding="utf-8"))
    c_frame = conflicts_frame(
        c_records, sc["text_field"], int(sc["max_chars"]), bool(sc["require_reference_answer"])
    )
    w_frame = twowiki_frame(w_records)

    pilot = draw_conflicts(c_frame, cfg["pilot"]["conflicts"], "pilot", seed, version, set())
    pilot += draw_twowiki(w_frame, cfg["pilot"]["twowiki"], "pilot", seed, version, set())
    used = {it.qid for it in pilot}
    main_items = draw_conflicts(
        c_frame,
        cfg["main"]["conflicts"],
        "main",
        seed,
        version,
        used,
        total=int(cfg["main"]["conflicts_total"]),
    )
    main_items += draw_twowiki(w_frame, cfg["main"]["twowiki"], "main", seed, version, used)
    main_items = choose_double(main_items, int(cfg["double_annotation"]["n"]), seed)
    if {it.qid for it in main_items} & used:
        raise SystemExit("pilot and main share a question")
    if len({it.item_id for it in pilot + main_items}) != len(pilot) + len(main_items):
        raise SystemExit("duplicated item id")

    layout = Layout(ROOT / cfg["out_dir"])
    write_data = args.force or not (layout.root.exists() and any(layout.root.iterdir()))
    if args.rebuild_data:
        old = json.loads((ROOT / cfg["manifest"]).read_text(encoding="utf-8"))
        new_items = sorted((asdict(it) for it in pilot + main_items), key=lambda r: r["item_id"])
        old_items = [{k: v for k, v in r.items() if k != "text_sha256"} for r in old["items"]]
        if new_items != old_items:
            raise SystemExit("items differ from the pre-registered manifest: nothing rewritten")
        write_data = True
    if not write_data:
        print(f"{layout.root} is not empty: sample files are NOT overwritten (use --force)")
    queries = {(q.source, q.qid): q for q in c_frame + w_frame}
    passages = {(q.source, q.qid, p.pid): p for q in c_frame + w_frame for p in q.passages}
    key_rows, items_by_set = [], {"pilot": [], "main": []}
    for it in pilot + main_items:
        q, p = queries[(it.source, it.qid)], passages[(it.source, it.qid, it.pid)]
        key_rows.append({**asdict(it), "text_sha256": p.text_sha256})
        items_by_set[it.set].append(
            AnnotationItem(it.item_id, q.question, q.reference_answer, p.title, p.date, p.text)
        )
    by_id = {i.item_id: i for s in items_by_set.values() for i in s}
    a1, a2 = cfg["annotators"]["primary"], cfg["annotators"]["secondary"]
    if write_data:
        write_jsonl(layout.key, sorted(key_rows, key=lambda r: r["item_id"]))
    for set_name, sampled in (("pilot", pilot), ("main", main_items)) if write_data else ():
        write_jsonl(
            layout.items(set_name),
            [asdict(i) for i in sorted(items_by_set[set_name], key=lambda i: i.item_id)],
        )
        for ann in (a1, a2):
            mine = [it for it in sampled if set_name == "pilot" or ann == a1 or it.double]
            ordered = sheet_order(mine, seed, set_name, ann)
            write_sheet(layout.sheet(set_name, ann), [by_id[it.item_id] for it in ordered])

    manifest = {
        "name": f"annotation_sample_{version}",
        "purpose": "pre-registered sample of the independent natural-evidence annotation set",
        "created_utc": utc_now(),
        "pre_registration_note": "created before any G2+ prediction exists; no model output, "
        "ranking or score was used for sampling",
        "seed": seed,
        "config": cfg,
        "script": "scripts/annotation/sample_items.py",
        "script_sha256": sha256_file(Path(__file__)),
        "repo_git": git_state(ROOT),
        "sources": {
            "conflicts": {
                "path": sc["path"],
                "sha256": sha256_file(c_path),
                "records": len(c_records),
                "eligible_queries": len(c_frame),
            },
            "twowiki": {
                "path": sw["path"],
                "sha256": sha256_file(w_path),
                "records": len(w_records),
                "eligible_queries": len(w_frame),
            },
        },
        "frame_counts": {
            "conflicts_queries_by_stratum": stratum_counts_frame(c_frame),
            "twowiki_queries_by_type": stratum_counts_frame(w_frame),
        },
        "counts": {
            "pilot_items": len(pilot),
            "pilot_by_stratum": stratum_counts(pilot),
            "pilot_questions": len({(i.source, i.qid) for i in pilot}),
            "main_items": len(main_items),
            "main_by_stratum": stratum_counts(main_items),
            "main_questions": len({(i.source, i.qid) for i in main_items}),
            "double_items": sum(i.double for i in main_items),
            "double_by_stratum": stratum_counts(i for i in main_items if i.double),
        },
        "items": sorted(key_rows, key=lambda r: r["item_id"]),
        "committed": "metadata only (IDs, strata, text hashes); texts stay in data/ (gitignored)",
    }
    path = ROOT / cfg["manifest"]
    if args.rebuild_data or (path.exists() and not args.force):
        old = json.loads(path.read_text(encoding="utf-8"))
        same = old["items"] == manifest["items"] and old["seed"] == manifest["seed"]
        print(
            "pre-registered sample reproduced: identical items"
            if same
            else "MISMATCH with the pre-registered sample (manifest not changed)"
        )
        return 0 if same else 1
    write_manifest(path, manifest)
    print(json.dumps(manifest["counts"], indent=1))
    return 0


def stratum_counts_frame(frame: list) -> dict[str, int]:
    out: dict[str, int] = {}
    for q in frame:
        out[q.stratum] = out.get(q.stratum, 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    raise SystemExit(main())
