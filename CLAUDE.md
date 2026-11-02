# CLAUDE.md — Paper 3: Relation-Aware Evidence Reranking for Reliable RAG

Agent-facing project memory. Read it at the start of every session (cloud or local).
Code, comments and docstrings are in English. Reports in `reports/` and planning docs in `docs/`
are in Vietnamese, keeping technical terms in English.

## 1. Project context

- Owner: PhD student, Graduate School of Informatics, Kyoto University. Solo project.
- Deliverable: third journal paper. Working title: *"Relation-Aware Evidence Reranking for
  Reliable RAG under Noisy and Conflicting Evidence"*.
- Theme: Knowledge Graph (KG)-guided retrieval/reranking for robust RAG.
- Core question: on a **fixed candidate evidence pool** (retrieval is held fixed; every method
  reranks or filters the same candidates per question), can KG schema knowledge separate
  **apparent conflicts** from **genuine conflicts**, and penalise only the genuine ones?
  - Apparent conflicts (surface disagreement that KG knowledge reconciles):
    - `alias`: aliases and historical names (Saigon / Ho Chi Minh City, Bombay / Mumbai, Edo / Tokyo)
    - `granularity`: part-of / located-in hierarchy (P361-like / P131-like)
    - `temporal_scope`: different validity periods (start/end-time qualifiers, P580/P582-like)
    - `homonym`: same surface name, different entity (different P31-like entity type)
    - `predicate_mismatch`: related-but-different predicates (place of birth vs. place of death)
  - Genuine conflicts: counterfactual edits, misinformation.
- Status: research prototype. Nothing produced so far is an experimental result.

## 2. Hardware

| Where | Spec | Use |
|---|---|---|
| Cloud session (claude.ai/code) | 4 vCPU, ~15 GiB RAM, **no GPU**; arXiv and Wikidata blocked; GitHub *web pages* of out-of-scope repos return 403, but `git clone` of public repos works (see `reports/00_environment.md`, `reports/02_codebase_map.md` §1) | audit, CPU prototype, unit + smoke tests |
| Desktop MSI MEG Vision X AI 2NVZ9-014JP | 1x RTX 5090 (32 GB VRAM), 64 GB RAM, Ubuntu on WSL2 | real experiments; open-weight LLMs via vLLM OpenAI-compatible server at `http://localhost:8000/v1` |
| MacBook Air M4 | 24 GB unified memory, 512 GB SSD (owner wrote "512 MB"; assumed typo) | local development, CPU tests; no CUDA |

## 3. Hard rules (from the owner; non-negotiable)

1. **No fabrication.** Never invent papers, authors, venues, URLs, file paths, function names,
   experimental results or novelty claims. Every important claim cites a paper section or
   `path:line` + symbol name. Anything not verified in-session is marked **[UNVERIFIED]**.
2. **Upstream code is read-only.** Clone into `third_party/` (gitignored); never modify. If a
   clone fails (e.g. 403 from the GitHub proxy), record the exact error and continue; do not
   work around it. The owner's attached forks (`Thuy-g/*`) may be used as read-only sources.
3. **Tiny data only.** At most 200 examples per dataset and 50 MB in total; never download model
   weights larger than 100 MB (check the size before downloading). No full datasets.
4. **No paid API** unless `ALLOW_PAID_API=1` AND `MAX_API_CALLS` AND `MAX_API_TOKENS` are set.
   Log estimated tokens of every call to `logs/api_usage.jsonl`. Default backend: `MockLLM`.
5. **Phases with STOP POINTs.** At the end of each phase: commit, push to the audit branch,
   summarise, then STOP until the owner types "Tiếp tục".
6. **Language.** English for code/comments/docstrings; Vietnamese for Markdown reports, keeping
   technical terms in English (reranker, cross-encoder, fixed candidate evidence pool, entity
   linking, triple extraction, ablation study, research gap, ...).
7. **Prototype, not results.** Every number computed on toy data is labelled
   "smoke test on toy data – not a result".
8. **Ask before cost.** Before any step expected to take > 5 CPU-minutes or to cost money:
   stop, estimate, ask.
9. **Secrets.** Never print or commit secrets; API keys only via environment variables.
10. Honesty and quality over quantity of code.

## 4. Coding conventions

- Python **3.11**. In the cloud container use `/usr/bin/python3.11`; the default `python3` there
  is 3.13 and must not be used for the project venv.
- src-layout: package in `src/kgrerank/`, tests in `tests/` (fixtures in `tests/fixtures/`),
  CLI scripts in `scripts/`, YAML configs in `configs/`.
- Tooling: `uv` (venv + install), `pytest`, `ruff` (lint + format, line length 100).
- Type hints on all public functions and methods; `from __future__ import annotations`;
  `dataclasses` for records; no bare `except`.
- Determinism: fixed seed (default `42`) passed explicitly through config; use local
  `random.Random(seed)` / `numpy.random.default_rng(seed)` instances, never global RNG state;
  stable sorts with explicit tie-breaks (e.g. by `pid`).
- Configuration: YAML files in `configs/`; scripts take `--config <file>.yaml`; no hard-coded
  absolute paths.
- Tests are offline: no network, no GPU, no model download. Network-dependent code lives in
  `scripts/` and is never imported by unit tests. Optional heavy dependencies (torch,
  sentence-transformers) are imported lazily and their tests are skipped when absent.
- Dependency versions are pinned exactly (`==`) in `pyproject.toml`.
- Normalised example schema (all loaders produce this):

  ```json
  {"qid": "str", "question": "str", "answers": ["str"],
   "candidates": [{"pid": "str", "title": "str", "text": "str", "is_gold": true,
                   "conflict_label": "compatible|contradicting|irrelevant",
                   "conflict_type": "none|irrelevant|counterfactual|alias_historical_name|granularity|temporal_scope|homonym|predicate_mismatch"}],
   "meta": {"source": "str", "synthetic": false}}
  ```

## 5. LLM backends and API budget

- All backends implement `LLMBackend` (OpenAI-compatible chat interface).
  - `MockLLM`: default; deterministic; no network.
  - `OpenAICompatLLM`: any OpenAI-compatible server, default `http://localhost:8000/v1` (vLLM).
- Budget guard:
  - Local endpoints (`localhost`, `127.0.0.1`, `::1`) cost nothing but still go through the
    guard and the token log.
  - Any other endpoint is treated as paid and is refused unless `ALLOW_PAID_API=1`,
    `MAX_API_CALLS` and `MAX_API_TOKENS` are all set; the guard aborts before either cap is
    exceeded.
- Token log: one JSON object per call appended to `logs/api_usage.jsonl` (timestamp, backend,
  endpoint host, model, estimated prompt/completion tokens, cumulative totals). Never log keys.

## 6. Repository layout (target; built up during Phases A–C)

```
paper3-kg-conflict-rerank/
├── CLAUDE.md, README.md, HANDOFF.md (Phase C)
├── docs/PLAN.md                    # phase plan + completion criteria
├── reports/                        # 00_environment … 07_uncertainties (Vietnamese)
├── third_party/                    # read-only upstream clones (gitignored)
├── src/kgrerank/
│   ├── data/  perturb/  rerankers/  llm/  metrics/        # Phase B
│   └── kg/  extract/  conflict/                           # Phase C
├── configs/                        # YAML configs (smoke.yaml, pilot.yaml)
├── scripts/                        # run_pilot.py, slicing scripts
├── tests/  (fixtures/)             # offline unit + smoke tests
├── logs/  outputs/  data/          # gitignored runtime artefacts and dataset slices
├── pyproject.toml, Makefile
```

## 7. How to run (targets exist from Phase B on)

```bash
make install   # uv venv --python /usr/bin/python3.11 .venv && uv pip install -e ".[dev]"
make test      # pytest -q (offline)
make lint      # ruff check . && ruff format --check .
make smoke     # scripts/run_pilot.py --config configs/smoke.yaml (CPU, < 2 min, MockLLM)
```

Local vLLM (desktop): start `vllm serve <model>` on port 8000, then set `llm.backend:
openai_compat` and `llm.base_url: http://localhost:8000/v1` in the YAML config.

## 8. Git workflow

- Audit branch for this effort: `claude/paper3-audit-20261102` (date fixed at the start, kept for
  all phases; one pull request at the end of Phase C).
- Commit at every STOP POINT; push with `git push -u origin <branch>`.
- Never commit `third_party/`, `.venv/`, `logs/`, `outputs/`, `data/` (third-party dataset
  slices: licences may forbid redistribution) or secrets. Hand-written fixtures in
  `tests/fixtures/` are fine and must say `"synthetic": true`.

## 9. Upstream sources for the audit (read-only)

Venue and arXiv IDs below are as given by the owner; checking them is part of Phase A.

| Upstream | Attached fork | Paper (as given by owner) |
|---|---|---|
| `STAIR-BUPT/TruthfulRAG` | `Thuy-g/TruthfulRAG` | TruthfulRAG, AAAI 2026, arXiv 2511.10375 |
| `GraphRAG-Bench/GraphRAG-Benchmark` | `Thuy-g/GraphRAG-Benchmark` | GraphRAG-Bench, ICLR 2026, arXiv 2506.05690 |
| `HYU-NLP/MAGIC` | `Thuy-g/MAGIC` | MAGIC, Findings of EMNLP 2025, arXiv 2507.21544 |
| `google-research-datasets/rag_conflicts` | `Thuy-g/rag_conflicts` | CONFLICTS, arXiv 2506.08500 |
| `1212Judy/ArbGraph` | `Thuy-g/ArbGraph` | ArbGraph, arXiv 2604.18362 (fork `readme.md:73`: "This is a research prototype and may require GPU for efficient execution") |
| `DMiC-Lab-HFUT/Relink` | `Thuy-g/Relink` | Relink |
| `norikinishida/kapipe` | `Thuy-g/kapipe` | ProStruct-RAG, EMNLP 2026 |

In cloud sessions the forks are pre-cloned at `/home/user/<Repo>`.
