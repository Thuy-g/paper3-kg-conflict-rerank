"""End-to-end smoke run of scripts/run_pilot.py on the synthetic fixtures (offline)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from kgrerank import SMOKE_LABEL

ROOT = Path(__file__).resolve().parents[1]


def test_smoke_run(tmp_path):
    cfg = yaml.safe_load((ROOT / "configs" / "smoke.yaml").read_text(encoding="utf-8"))
    out_rel = Path("outputs") / "pytest_smoke" / tmp_path.name
    cfg["output_dir"] = str(out_rel)
    cfg["api_log"] = str(out_rel / "api_usage.jsonl")
    cfg["metrics"]["bootstrap"]["n_boot"] = 200
    cfg_path = tmp_path / "smoke.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_pilot.py"), "--config", str(cfg_path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = ROOT / out_rel
    payload = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert payload["label"] == SMOKE_LABEL
    assert SMOKE_LABEL in (out / "report.md").read_text(encoding="utf-8")
    s = payload["summary"]["systems"]
    assert s["oracle:drop_contradicting"]["fcfr_paired@5"]["mean"] == 0.0
    assert s["oracle:drop_contradicting"]["ger_paired@5"]["mean"] == 1.0
    assert s["oracle:drop_any_reason"]["fcfr_paired@5"]["mean"] == 1.0
    assert s["bm25"]["fcfr_paired@5"]["mean"] == 0.0  # the reference against itself
    assert s["llm_judge_mock"]["llm_calls"]["mean"] > 0
    assert s["g2plus:S0"]["llm_calls"]["mean"] > s["g2plus:S3"]["llm_calls"]["mean"]
    assert "manual" in payload["summary"]["typing"]["g2plus:S3"]
    assert payload["summary"]["information_access"]["g2plus:S3"]["answer_facts_access"]
    assert payload["perturbation_counts"]["temporal_unstated"].get("UNKNOWN", 0) >= 1
    log = (out / "api_usage.jsonl").read_text(encoding="utf-8").splitlines()
    assert log and json.loads(log[0])["backend"] == "mock"
    shutil.rmtree(out)


def test_no_wikirecentchanges_material():
    """Owner rule: no code or data from the unlicensed WikiRecentChanges repository."""
    banned = ("WikiRecentChanges", "knowledge-conflicts-mutability", "MUTABLE_PROPERTIES")
    for sub in ("src", "scripts", "configs", "tests/fixtures", "manifests"):
        for path in (ROOT / sub).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".yaml", ".json", ".jsonl", ".md"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert not any(b in text for b in banned), path
