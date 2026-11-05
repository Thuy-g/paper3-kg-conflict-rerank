#!/usr/bin/env python3
"""Inter-annotator agreement on the double-annotated items of a set (no thresholds).

Usage: agreement.py --sample-dir data/annotation/v1 --set pilot|main [--a1 A1 --a2 A2]
Reads the frozen submissions and writes agreement/<set>_report.json and .md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.annotation.agreement import agreement_report  # noqa: E402
from kgrerank.annotation.layout import Layout, load_key  # noqa: E402
from kgrerank.annotation.schema import DECISIONS, read_jsonl, record_from_dict  # noqa: E402
from kgrerank.schema import REASON_TYPES  # noqa: E402


def _fmt(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-dir", required=True)
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    ap.add_argument("--a1", default="A1")
    ap.add_argument("--a2", default="A2")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    layout = Layout(ROOT / args.sample_dir)
    key = load_key(layout)
    a1 = {
        r["item_id"]: record_from_dict(r) for r in read_jsonl(layout.submission(args.set, args.a1))
    }
    a2 = {
        r["item_id"]: record_from_dict(r) for r in read_jsonl(layout.submission(args.set, args.a2))
    }
    versions = {r.codebook_version for r in (*a1.values(), *a2.values())}
    if len(versions) != 1:
        raise SystemExit(f"submissions use different codebook versions: {sorted(versions)}")
    ids = sorted(set(a1) & set(a2))
    pairs = [(a1[i].labels(), a2[i].labels()) for i in ids]
    clusters = [f"{key[i]['source']}|{key[i]['qid']}" for i in ids]
    rep = agreement_report(pairs, clusters, DECISIONS, REASON_TYPES, args.n_boot, args.seed)
    rep["by_stratum"] = {}
    for stratum in sorted({key[i]["stratum"] for i in ids}):
        sub = [j for j, i in enumerate(ids) if key[i]["stratum"] == stratum]
        r = agreement_report(
            [pairs[j] for j in sub],
            [clusters[j] for j in sub],
            DECISIONS,
            REASON_TYPES,
            n_boot=200,
            seed=args.seed,
        )
        rep["by_stratum"][stratum] = {
            "n": len(sub),
            "raw": r["decision"]["raw_agreement"],
            "kappa": r["decision"]["cohen_kappa"],
        }
    rep["codebook_version"] = versions.pop()
    out = layout.agreement(args.set, "json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    d, r = rep["decision"], rep["reasons"]
    lines = [
        f"# Agreement — {args.set} ({rep['n_items']} items, {rep['n_questions']} questions)",
        "",
        f"- decision raw agreement: {_fmt(d['raw_agreement'])}",
        f"- decision Cohen's kappa: {_fmt(d['cohen_kappa'])} "
        f"[{_fmt(d['cohen_kappa_ci95_cluster_bootstrap'][0])}, "
        f"{_fmt(d['cohen_kappa_ci95_cluster_bootstrap'][1])}] (cluster bootstrap)",
        f"- reasons Krippendorff's alpha (MASI): {_fmt(r['krippendorff_alpha_masi'])}",
        f"- reasons mean Jaccard: {_fmt(r['mean_jaccard'])}; exact set: "
        f"{_fmt(r['exact_set_agreement'])}",
        f"- answer_support kappa: {_fmt(rep['answer_support']['cohen_kappa'])}",
        "",
        "No agreement threshold is applied (protocol §6).",
        "",
    ]
    layout.agreement(args.set, "md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
