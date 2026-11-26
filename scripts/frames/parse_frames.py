#!/usr/bin/env python3
"""Parse question frames for the annotation set (cloud: mock backend; MSI: local vLLM).

Usage: parse_frames.py --config configs/frames_v1.yaml
Only (qid, question) is passed to the parser; reference answers in the item files are not read.
Writes data/frames/<v>/frames_<set>.jsonl (gitignored) and a run manifest with parser version,
prompt hash, model, settings, snapshot, coverage over ALL questions and LLM usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.annotation.schema import read_jsonl, write_jsonl  # noqa: E402
from kgrerank.extract.linker import EntityLinker  # noqa: E402
from kgrerank.frames.parser import PARSER_VERSION, PROMPT_V1, LLMFrameParser, coverage  # noqa: E402
from kgrerank.frames.schema import InferenceFrame, Snapshot  # noqa: E402
from kgrerank.kg.view import KGView  # noqa: E402
from kgrerank.llm.base import summarize_events  # noqa: E402
from kgrerank.llm.budget import TokenLogger  # noqa: E402
from kgrerank.manifest import git_state, utc_now, write_manifest  # noqa: E402
from kgrerank.pipeline import llm_backend  # noqa: E402


def questions_for(annotation_dir: Path, set_name: str) -> list[dict]:
    """(source, qid, question) per question of a set; nothing else is read from the items."""
    key = {r["item_id"]: r for r in read_jsonl(annotation_dir / "key.jsonl")}
    out: dict[tuple[str, str], dict] = {}
    for item in read_jsonl(annotation_dir / f"items_{set_name}.jsonl"):
        k = key[item["item_id"]]
        out.setdefault(
            (k["source"], k["qid"]),
            {
                "source": k["source"],
                "qid": k["qid"],
                "question": item["question"],
                "stratum": k["stratum"],
            },
        )
    return [out[x] for x in sorted(out)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    cfg = yaml.safe_load(Path(ap.parse_args().config).read_text(encoding="utf-8"))
    kg = KGView.from_json(ROOT / cfg["kg_view"])
    linker = EntityLinker(kg)
    labels = [p.label for p in kg.properties.values()]
    backend = llm_backend(
        cfg["backend"], TokenLogger(ROOT / "logs" / "api_usage.jsonl"), "mock-frames"
    )
    snapshots = {k: Snapshot.from_dict(v) for k, v in cfg["snapshots"].items()}
    out_dir = ROOT / cfg["out_dir"]
    report = {}
    for set_name in cfg["sets"]:
        qs = questions_for(ROOT / cfg["annotation_dir"], set_name)
        frames = []
        for q in qs:
            parser = LLMFrameParser(
                backend,
                linker,
                labels,
                snapshots[q["source"]],
                int(cfg["max_tokens"]),
                seed=cfg.get("seed"),
            )
            start = len(backend.events)
            fr = parser.parse(q["qid"], q["question"])
            frames.append(
                {
                    **fr.to_dict(),
                    "source_dataset": q["source"],
                    "llm_usage": summarize_events(backend.events[start:]),
                }
            )
        write_jsonl(out_dir / f"frames_{set_name}.jsonl", frames)
        report[set_name] = coverage([InferenceFrame.from_dict(f) for f in frames])
    mock = cfg["backend"]["type"] == "mock"
    # Mock runs are plumbing checks: their manifest goes to outputs/, never to manifests/.
    manifest_path = ROOT / ("outputs/frames/frames_mock_run.json" if mock else cfg["manifest"])
    write_manifest(
        manifest_path,
        {
            "frames_version": cfg["frames_version"],
            "created_utc": utc_now(),
            "parser_version": PARSER_VERSION,
            "prompt_sha256": hashlib.sha256(PROMPT_V1.encode()).hexdigest(),
            "backend": cfg["backend"],
            "max_tokens": cfg["max_tokens"],
            "seed": cfg.get("seed"),
            "kg_view": cfg["kg_view"],
            "snapshots": cfg["snapshots"],
            "coverage": report,
            "llm_usage": summarize_events(backend.events),
            "repo_git": git_state(ROOT),
            "note": "mock backend outputs are not frames of any value; plumbing only"
            if mock
            else "",
        },
    )
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
