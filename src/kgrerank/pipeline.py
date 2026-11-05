"""Evaluation runner: fixed pools × rerankers → per-query metrics → bootstrap CIs and paired deltas.

Everything is driven by a config dict (see configs/smoke.yaml). Stochastic systems are run with
several seeds; per-query values are averaged over seeds before bootstrapping, and the spread of the
per-seed means is reported separately.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from kgrerank.kg.view import KGView
from kgrerank.llm.budget import TokenLogger
from kgrerank.llm.mock import MockLLM
from kgrerank.llm.openai_compat import OpenAICompatLLM
from kgrerank.metrics.conflict import conflict_metrics
from kgrerank.metrics.decision import typing_report
from kgrerank.metrics.retrieval import condense, mrr, ndcg_at_k, recall_at_k
from kgrerank.metrics.stats import (
    bootstrap_ci,
    holm,
    mcnemar_exact,
    minimum_detectable_effect,
    paired_bootstrap_ci,
    seed_summary,
)
from kgrerank.perturb.operators import apply_operators
from kgrerank.rerankers.base import Ranking, Reranker, check_ranking
from kgrerank.rerankers.bm25 import BM25Reranker
from kgrerank.rerankers.llm_judge import NEVER_ACCESSED, LLMJudgeFilter, LLMTyper
from kgrerank.rerankers.simple import IdentityReranker, OracleReranker, RandomReranker
from kgrerank.schema import Decision, Example, validate_example

PerQuery = dict[str, dict[str, float | None]]  # qid -> metric -> value


def build_reranker(spec: dict[str, Any], seed: int, logger: TokenLogger | None) -> Reranker:
    kind = spec["type"]
    if kind == "identity":
        return IdentityReranker(name=spec["name"])
    if kind == "random":
        return RandomReranker(seed=seed, name=spec["name"])
    if kind == "bm25":
        return BM25Reranker(k1=spec.get("k1", 1.5), b=spec.get("b", 0.75), name=spec["name"])
    if kind == "oracle":
        base_spec = {"type": spec.get("base", "identity"), "name": "base"}
        return OracleReranker(
            mode=spec["mode"], base=build_reranker(base_spec, seed, logger), name=spec["name"]
        )
    if kind == "cross_encoder":
        from kgrerank.rerankers.cross_encoder import CrossEncoderReranker

        return CrossEncoderReranker(model_name=spec["model"], name=spec["name"])
    if kind == "llm_judge":
        backend = llm_backend(spec.get("backend", {"type": "mock"}), logger, "mock-judge")
        typer = LLMTyper(
            backend,
            prompt=spec.get("prompt", "inter_context_v1"),
            max_tokens=int(spec.get("max_tokens", 256)),
            seed=seed,
            temperature=float(spec.get("temperature", 0.0)),
            context_m=int(spec.get("context_m", 5)),
            role="judge",
        )
        base = build_reranker({"type": spec.get("base", "bm25"), "name": "base"}, seed, logger)
        return LLMJudgeFilter(
            base=base, typer=typer, top_m=spec.get("top_m", 10), name=spec["name"]
        )
    if kind == "g2plus":
        return _build_g2plus(spec, seed, logger)
    raise ValueError(f"unknown reranker type {kind!r}")


def llm_backend(spec: dict[str, Any] | None, logger: TokenLogger | None, default_model: str):
    """None | {"type": "mock"} | {"type": "openai_compat", "model", "base_url", "extra_body",
    "sampling", "timeout"} (see configs/msi/qwen3_8b.yaml)."""
    if not spec:
        return None
    if spec["type"] == "mock":
        return MockLLM(model=spec.get("model", default_model), logger=logger)
    if spec["type"] == "openai_compat":
        return OpenAICompatLLM(
            model=spec["model"],
            base_url=spec["base_url"],
            logger=logger,
            timeout=float(spec.get("timeout", 120.0)),
            extra_body=spec.get("extra_body"),
            sampling=spec.get("sampling"),
        )
    raise ValueError(f"unknown backend {spec['type']!r}")


def _build_g2plus(spec: dict[str, Any], seed: int, logger: TokenLogger | None) -> Reranker:
    """G2+ skeleton.

    Spec keys: kg_view (absolute path), setting (S0-S3), frames ("construction" for synthetic
    fixtures, or the path of a frames JSONL as written in the config; ``frames_path``, if given,
    is the resolved path that is read), extractor (pattern | {backend}), fallback
    (none | mock | {backend}), fallback_prompt, max_tokens, temperature, lam, mode
    (penalize | filter), base.
    """
    from kgrerank.annotation.schema import read_jsonl
    from kgrerank.conflict.reranker import ConflictAwareReranker
    from kgrerank.conflict.typer import G2PlusTyper
    from kgrerank.extract.llm import LLMClaimExtractor
    from kgrerank.extract.pattern import PatternExtractor
    from kgrerank.frames.schema import InferenceFrame

    kg = KGView.from_json(spec["kg_view"])
    ext = spec.get("extractor", "pattern")
    if ext == "pattern":
        # Relation labels serve as an extraction lexicon only (not as KG facts).
        extractor: Any = PatternExtractor([p.label for p in kg.properties.values()])
    else:
        extractor = LLMClaimExtractor(
            llm_backend(ext, logger, "mock-extractor"),
            max_tokens=int(spec.get("max_tokens", 256)),
            temperature=float(spec.get("temperature", 0.0)),
            seed=seed,
        )
    fb = spec.get("fallback", "none")
    fb_backend = llm_backend(
        {"type": "mock"} if fb == "mock" else (None if fb == "none" else fb),
        logger,
        "mock-fallback",
    )
    fallback = (
        None
        if fb_backend is None
        else LLMTyper(
            fb_backend,
            prompt=spec.get("fallback_prompt", "inter_context_v1"),
            max_tokens=int(spec.get("max_tokens", 256)),
            temperature=float(spec.get("temperature", 0.0)),
            seed=seed,
            role="fallback",
        )
    )
    typer = G2PlusTyper(kg, spec.get("setting", "S2"), extractor, fallback)
    frames = None
    frame_usage: dict[str, Any] = {}
    if spec.get("frames", "construction") != "construction":
        recs = read_jsonl(spec.get("frames_path") or spec["frames"])
        frames = {r["qid"]: InferenceFrame.from_dict(r) for r in recs}
        frame_usage = {r["qid"]: r.get("llm_usage") or {} for r in recs}
    base = build_reranker({"type": spec.get("base", "bm25"), "name": "base"}, seed, logger)
    rr = ConflictAwareReranker(
        base, typer, frames, float(spec.get("lam", 1.0)), spec.get("mode", "penalize"), spec["name"]
    )
    rr.frame_usage = frame_usage  # type: ignore[attr-defined]
    return rr


def information_access(spec: dict[str, Any]) -> dict[str, Any]:
    """What each system may read; recorded in every metrics.json for fair comparison."""
    kind = spec["type"]
    out: dict[str, Any] = {"never": list(NEVER_ACCESSED), "question": True, "passages": "pool"}
    if kind == "llm_judge":
        out["llm"] = spec.get("prompt", "inter_context_v1")
    if kind == "g2plus":
        out.update(
            kg_setting=spec.get("setting", "S2"),
            frames=spec.get("frames", "construction"),
            llm_extractor=spec.get("extractor", "pattern") != "pattern",
            llm_fallback=spec.get("fallback_prompt", "inter_context_v1")
            if spec.get("fallback", "none") != "none"
            else None,
            answer_facts_access=spec.get("setting") == "S3",
        )
    if kind == "oracle":
        out["gold_labels"] = True  # oracles are metric sanity checks only
    return out


def _usage_row(usage: dict[str, Any]) -> dict[str, float]:
    errors = sum(v for k, v in (usage.get("by_status") or {}).items() if k != "ok")
    return {
        "llm_calls": float(usage.get("calls", 0)),
        "llm_prompt_tokens_est": float(usage.get("prompt_tokens_est", 0)),
        "llm_completion_tokens_est": float(usage.get("completion_tokens_est", 0)),
        "llm_latency_s": float(usage.get("latency_s", 0.0)),
        "llm_failed_calls": float(errors),
    }


def per_query_metrics(
    examples: Sequence[Example],
    rankings: dict[str, Ranking],
    ref: dict[str, Ranking],
    ks: Sequence[int],
    reasons: Sequence[str],
) -> PerQuery:
    """Retrieval metrics: full-list values only when relevance judgments cover the whole pool
    (``meta.relevance_judged_pids`` absent or complete); condensed ('_cond') values always, over
    judged passages only. Unjudged passages are never treated as non-relevant."""
    out: PerQuery = {}
    for ex in examples:
        r = rankings[ex.qid]
        pool = {c.pid for c in ex.candidates}
        judged = set(ex.meta.get("relevance_judged_pids") or pool)
        complete = judged >= pool
        gold = ex.gold_pids & judged
        cond = condense(r.order, judged)
        row: dict[str, float | None] = {
            "mrr": mrr(r.order, gold) if complete else None,
            "mrr_cond": mrr(cond, gold),
        }
        for k in ks:
            row[f"recall@{k}"] = recall_at_k(r.order, gold, k) if complete else None
            row[f"ndcg@{k}"] = ndcg_at_k(r.order, gold, k) if complete else None
            row[f"recall@{k}_cond"] = recall_at_k(cond, gold, k)
            row[f"ndcg@{k}_cond"] = ndcg_at_k(cond, gold, k)
        row.update(conflict_metrics(ex, r, ref[ex.qid], ks, reasons))
        row.update(_usage_row(r.llm_usage or {"calls": r.llm_calls}))
        out[ex.qid] = row
    return out


def typing_items(examples: Sequence[Example], reranker: Any) -> dict[str, list[tuple]]:
    """(qid, gold, predicted, status) per gold label source, from systems that expose decisions."""
    by_source: dict[str, list[tuple]] = {}
    typed = getattr(reranker, "last_typed", None)
    judged = getattr(reranker, "last_decisions", None)
    if not typed and not judged:
        return by_source
    for ex in examples:
        preds: dict[str, tuple[Any, str]] = {}
        if typed and ex.qid in typed:
            preds = {t.pid: (t.decision, t.status) for t in typed[ex.qid]}
        elif judged and ex.qid in judged:
            preds = {pid: (d.decision, d.status) for pid, d in judged[ex.qid].items()}
        for c in ex.candidates:
            if c.label_source == "unlabelled" or c.pid not in preds:
                continue  # unjudged passages and passages the system did not type
            pred, status = preds[c.pid]
            by_source.setdefault(c.label_source, []).append((ex.qid, c.decision, pred, status))
    return by_source


def _rank_all(reranker: Reranker, examples: Sequence[Example]) -> dict[str, Ranking]:
    out = {}
    for ex in examples:
        r = reranker.rank(ex)
        check_ranking(ex, r)
        out[ex.qid] = r
    return out


def _mean_over_seeds(per_seed: list[PerQuery]) -> PerQuery:
    merged: PerQuery = {}
    for qid in per_seed[0]:
        merged[qid] = {}
        for m in per_seed[0][qid]:
            vals = [ps[qid][m] for ps in per_seed]
            merged[qid][m] = None if any(v is None for v in vals) else statistics.fmean(vals)
    return merged


@dataclass
class SystemResult:
    name: str
    seeds: list[int]
    per_query: PerQuery
    per_seed_means: dict[str, list[float]] = field(default_factory=dict)
    typing: dict[str, Any] = field(default_factory=dict)
    information_access: dict[str, Any] = field(default_factory=dict)


def run_systems(
    examples: Sequence[Example],
    system_specs: Sequence[dict[str, Any]],
    reference_name: str,
    ks: Sequence[int],
    reasons: Sequence[str],
    default_seed: int,
    logger: TokenLogger | None = None,
    n_boot: int = 1000,
) -> dict[str, SystemResult]:
    ref_spec = next(s for s in system_specs if s["name"] == reference_name)
    ref_rankings = _rank_all(build_reranker(ref_spec, default_seed, logger), examples)
    results: dict[str, SystemResult] = {}
    for spec in system_specs:
        seeds = list(spec.get("seeds", [default_seed]))
        per_seed: list[PerQuery] = []
        typing: dict[str, Any] = {}
        for s in seeds:
            rr = build_reranker(spec, s, logger)
            rankings = _rank_all(rr, examples)
            for k, v in getattr(rr, "frame_usage", {}).items():  # frame parsing cost, per question
                if k in rankings and v:
                    u = dict(rankings[k].llm_usage or {})
                    for key in ("calls", "prompt_tokens_est", "completion_tokens_est", "latency_s"):
                        u[key] = u.get(key, 0) + v.get(key, 0)
                    u["frame_parse_calls"] = v.get("calls", 0)
                    rankings[k] = Ranking(
                        rankings[k].order,
                        rankings[k].removed,
                        rankings[k].scores,
                        int(u["calls"]),
                        u,
                    )
            per_seed.append(per_query_metrics(examples, rankings, ref_rankings, ks, reasons))
            if s == seeds[0]:
                typing = {
                    src: typing_report(items, n_boot, default_seed)
                    for src, items in typing_items(examples, rr).items()
                }
        seed_means: dict[str, list[float]] = {}
        for m in per_seed[0][examples[0].qid]:
            for ps in per_seed:
                vals = [row[m] for row in ps.values() if row[m] is not None]
                if vals:
                    seed_means.setdefault(m, []).append(statistics.fmean(vals))
        results[spec["name"]] = SystemResult(
            spec["name"],
            seeds,
            _mean_over_seeds(per_seed),
            seed_means,
            typing,
            information_access(spec),
        )
    return results


def summarize(
    results: dict[str, SystemResult],
    reference_name: str,
    delta_metrics: Sequence[str],
    n_boot: int,
    seed: int,
    alpha: float,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "systems": {},
        "paired_vs_reference": {},
        "wfr_mcnemar": {},
        "typing": {n: r.typing for n, r in results.items() if r.typing},
        "information_access": {n: r.information_access for n, r in results.items()},
    }
    for name, res in results.items():
        metrics: dict[str, Any] = {}
        for m in next(iter(res.per_query.values())):
            vals = [row[m] for row in res.per_query.values() if row[m] is not None]
            if m.startswith("den:"):
                metrics[m] = {"sum": sum(vals), "n_questions_nonzero": sum(v > 0 for v in vals)}
                continue
            if not vals:
                metrics[m] = {"n": 0}
                continue
            ci = bootstrap_ci(vals, n_boot, seed, alpha)
            entry: dict[str, Any] = {"mean": ci.mean, "ci_lo": ci.lo, "ci_hi": ci.hi, "n": ci.n}
            if len(res.seeds) > 1 and m in res.per_seed_means:
                mu, sd = seed_summary(res.per_seed_means[m])
                entry.update({"seed_mean": mu, "seed_sd": sd, "n_seeds": len(res.seeds)})
            metrics[m] = entry
        summary["systems"][name] = metrics
    ref = results[reference_name].per_query
    pvals: dict[str, float] = {}
    for name, res in results.items():
        if name == reference_name:
            continue
        deltas: dict[str, Any] = {}
        for m in delta_metrics:
            qids = [
                q for q in ref if ref[q].get(m) is not None and res.per_query[q].get(m) is not None
            ]
            if len(qids) < 2:
                deltas[m] = {"n": len(qids)}
                continue
            a = [ref[q][m] for q in qids]
            b = [res.per_query[q][m] for q in qids]
            ci = paired_bootstrap_ci(a, b, n_boot, seed, alpha)
            diffs = [y - x for x, y in zip(a, b, strict=True)]
            sd = statistics.stdev(diffs)
            deltas[m] = {
                "delta": ci.mean,
                "ci_lo": ci.lo,
                "ci_hi": ci.hi,
                "n": ci.n,
                "sd_diff": sd,
                "mde_80": minimum_detectable_effect(sd, ci.n, alpha),
            }
        summary["paired_vs_reference"][name] = deltas
        for wkey in ("wfr_compat_v1", "wfr_support_v1"):
            qids = [
                q
                for q in ref
                if ref[q].get(wkey) is not None and res.per_query[q].get(wkey) is not None
            ]
            binary = all(
                ref[q][wkey] in (0.0, 1.0) and res.per_query[q][wkey] in (0.0, 1.0) for q in qids
            )
            if qids and binary:
                b01 = sum(ref[q][wkey] == 0.0 and res.per_query[q][wkey] == 1.0 for q in qids)
                b10 = sum(ref[q][wkey] == 1.0 and res.per_query[q][wkey] == 0.0 for q in qids)
                pvals[f"{name}|{wkey}"] = mcnemar_exact(b01, b10)
                summary["wfr_mcnemar"][f"{name}|{wkey}"] = {
                    "b01": b01,
                    "b10": b10,
                    "p": pvals[f"{name}|{wkey}"],
                }
    for name, p_adj in holm(pvals).items():
        summary["wfr_mcnemar"][name]["p_holm"] = p_adj
    return summary


def perturb_examples(
    examples: Sequence[Example], kg: KGView, operators: Sequence[str], seed: int, drop_unknown: bool
) -> tuple[list[Example], dict[str, dict[str, int]]]:
    """Apply operators; return new examples and counts per operator of each resulting decision."""
    out: list[Example] = []
    counts: dict[str, Counter[str]] = {op: Counter() for op in operators}
    for ex in examples:
        new, results = apply_operators(ex, kg, operators, seed, drop_unknown)
        validate_example(new)
        out.append(new)
        for res in results:
            key = "not_built" if res.candidate is None else res.candidate.decision.value
            counts.setdefault(res.operator, Counter())[key] += 1
    return out, {op: dict(c) for op, c in counts.items()}


def decision_counts(examples: Sequence[Example]) -> dict[str, dict[str, int]]:
    """Counts by label source and decision: a human-judged UNKNOWN ('manual') is kept apart from
    an unjudged passage ('unlabelled')."""
    out: dict[str, dict[str, int]] = {}
    for ex in examples:
        for c in ex.candidates:
            src = out.setdefault(c.label_source, {d.value: 0 for d in Decision})
            src[c.decision.value] += 1
    return dict(sorted(out.items()))
