#!/usr/bin/env python3
"""Run the method-neutral harness on a config (offline). Usage: run_pilot.py --config <file>.yaml

Writes ``<output_dir>/metrics.json`` and ``<output_dir>/report.md``. Every output carries the
configured label (for toy data: "smoke test on toy data – not a result").
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank import SMOKE_LABEL  # noqa: E402
from kgrerank.kg.view import KGView  # noqa: E402
from kgrerank.llm.budget import TokenLogger  # noqa: E402
from kgrerank.pipeline import decision_counts, perturb_examples, run_systems, summarize  # noqa: E402
from kgrerank.schema import read_jsonl  # noqa: E402


def _fmt(entry: dict) -> str:
    if not entry or entry.get("n", 0) == 0 or "mean" not in entry:
        return "n/a"
    s = f"{entry['mean']:.3f} [{entry['ci_lo']:.3f}, {entry['ci_hi']:.3f}] (n={entry['n']})"
    if "seed_sd" in entry:
        s += f" seed-SD={entry['seed_sd']:.3f}"
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    label = cfg.get("label", SMOKE_LABEL)
    seed = int(cfg["seed"])

    examples = []
    for item in cfg["data"]:
        path = ROOT / item["path"]
        if not path.exists():
            if item.get("optional", False):
                print(f"[skip] optional data file missing: {item['path']}")
                continue
            raise FileNotFoundError(path)
        examples.extend(read_jsonl(path))
    if not examples:
        raise SystemExit("no examples loaded")

    pert_counts = {}
    pcfg = cfg.get("perturbation", {})
    if pcfg.get("enabled", False):
        kg = KGView.from_json(ROOT / pcfg["kg_view"])
        examples, pert_counts = perturb_examples(
            examples, kg, pcfg["operators"], seed, bool(pcfg.get("drop_unknown", False))
        )

    for spec in cfg["rerankers"]["systems"]:
        if "kg_view" in spec:
            spec["kg_view"] = str(ROOT / spec["kg_view"])
    mcfg = cfg["metrics"]
    logger = TokenLogger(ROOT / cfg.get("api_log", "logs/api_usage.jsonl"))
    results = run_systems(
        examples,
        cfg["rerankers"]["systems"],
        cfg["rerankers"]["reference"],
        mcfg["ks"],
        mcfg.get("reasons", []),
        seed,
        logger,
    )
    summary = summarize(
        results,
        cfg["rerankers"]["reference"],
        mcfg["delta_metrics"],
        int(mcfg["bootstrap"]["n_boot"]),
        seed,
        float(mcfg["bootstrap"]["alpha"]),
    )
    out_dir = ROOT / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": label,
        "config": cfg,
        "n_examples": len(examples),
        "decision_counts": decision_counts(examples),
        "perturbation_counts": pert_counts,
        "summary": summary,
        "per_query": {name: res.per_query for name, res in results.items()},
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )
    lines = [f"# {cfg.get('run_name', 'run')} — {label}", "", f"> {label}", ""]
    lines.append(f"Examples: {len(examples)}; candidate decisions: {decision_counts(examples)}")
    if pert_counts:
        lines.append(f"Perturbation outcomes per operator: {pert_counts}")
    lines += [
        "",
        "| system | " + " | ".join(mcfg["report_metrics"]) + " |",
        "|---|" + "---|" * len(mcfg["report_metrics"]),
    ]
    for name, metrics in summary["systems"].items():
        cells = [_fmt(metrics.get(m, {})) for m in mcfg["report_metrics"]]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += ["", f"Paired deltas vs `{cfg['rerankers']['reference']}` (system − reference):", ""]
    for name, deltas in summary["paired_vs_reference"].items():
        for m, d in deltas.items():
            if "delta" in d:
                lines.append(
                    f"- {name} {m}: {d['delta']:+.3f} [{d['ci_lo']:+.3f}, {d['ci_hi']:+.3f}] "
                    f"(n={d['n']}, MDE80={d['mde_80']:.3f})"
                )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out_dir / 'metrics.json'} in {payload['elapsed_s']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
