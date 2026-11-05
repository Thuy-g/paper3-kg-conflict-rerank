#!/usr/bin/env python3
"""Fetch at most 200 rows of ofai/RagabilityCorpus via the HF datasets-server rows API.

Network script (never imported by tests). Raw responses go to data/raw/ragability/ (gitignored);
the manifest (committed) records URLs, timestamps, sha256, row count, revision and licence.
The corpus is CC-BY-SA-4.0: any public derived dataset must carry attribution and the same licence.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.manifest import git_state, sha256_bytes, sha256_file, utc_now, write_manifest  # noqa: E402

HARD_MAX_ROWS = 200


def fetch(url: str, ua: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    ts = utc_now()
    with urllib.request.urlopen(req, timeout=60) as resp:  # URLs are fixed HF endpoints
        return resp.status, resp.read(), ts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    cfg = yaml.safe_load(Path(ap.parse_args().config).read_text(encoding="utf-8"))
    ds, ua = cfg["dataset"], cfg["user_agent"]
    max_rows = min(int(cfg["max_rows"]), HARD_MAX_ROWS)
    out_dir = ROOT / cfg["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    requests_log = []

    info_url = f"https://huggingface.co/api/datasets/{ds}"
    status, body, ts = fetch(info_url, ua)
    info = json.loads(body)
    requests_log.append({"url": info_url, "utc": ts, "status": status, "bytes": len(body),
                         "sha256": sha256_bytes(body)})
    revision = info.get("sha")
    licence = (info.get("cardData") or {}).get("license")
    if licence != "cc-by-sa-4.0":
        raise SystemExit(f"licence changed or missing ({licence!r}); stop and ask the owner")
    time.sleep(cfg["sleep_s"])

    readme_url = f"https://huggingface.co/datasets/{ds}/raw/{revision}/README.md"
    status, body, ts = fetch(readme_url, ua)
    (out_dir / "README.md").write_bytes(body)
    requests_log.append({"url": readme_url, "utc": ts, "status": status, "bytes": len(body),
                         "sha256": sha256_bytes(body)})

    rows: list[dict] = []
    offset = 0
    while offset < max_rows:
        time.sleep(cfg["sleep_s"])
        length = min(int(cfg["page_size"]), max_rows - offset)
        q = urllib.parse.urlencode({"dataset": ds, "config": cfg["config"], "split": cfg["split"],
                                    "offset": offset, "length": length})
        url = f"https://datasets-server.huggingface.co/rows?{q}"
        status, body, ts = fetch(url, ua)
        page = json.loads(body)
        (out_dir / f"rows_{offset:04d}.json").write_bytes(body)
        got = page.get("rows", [])
        requests_log.append({"url": url, "utc": ts, "status": status, "bytes": len(body),
                             "sha256": sha256_bytes(body), "rows": len(got),
                             "num_rows_total": page.get("num_rows_total"),
                             "partial": page.get("partial")})
        rows.extend(r["row"] for r in got)
        if len(got) < length:
            break
        offset += length
    rows = rows[:max_rows]
    rows_path = out_dir / "rows.jsonl"
    with rows_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "name": "ragability",
        "dataset": ds,
        "hf_revision_sha": revision,
        "hf_last_modified": info.get("lastModified"),
        "revision_note": "datasets-server serves its latest processed revision; equality with "
        "hf_revision_sha is [UNVERIFIED]",
        "licence": "CC-BY-SA-4.0 (cardData.license and tag license:cc-by-sa-4.0)",
        "attribution": "Ragability corpus, ofai/RagabilityCorpus on Hugging Face (OFAI); cite the "
        "Ragability paper (LREC 2026) as listed in the dataset README",
        "share_alike_obligation": "Any public derived dataset must credit the source, state "
        "changes, and be released under CC-BY-SA-4.0 (or a compatible licence).",
        "created_utc": utc_now(),
        "script": "scripts/data/fetch_ragability_slice.py",
        "script_sha256": sha256_file(Path(__file__)),
        "repo_git": git_state(ROOT),
        "requests": requests_log,
        "row_count": len(rows),
        "output_path": str(rows_path.relative_to(ROOT)),
        "output_sha256": sha256_file(rows_path),
        "committed": "manifest only; rows stay in data/ (gitignored, never redistributed)",
    }
    write_manifest(ROOT / cfg["manifest"], manifest)
    print(f"ragability: {len(rows)} rows, revision {revision}, licence {licence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
