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
from kgrerank.metrics.retrieval import mrr, ndcg_at_k, recall_at_k
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
from kgrerank.rerankers.llm_judge import LLMJudgeFilter
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
        b = spec.get("backend", {"type": "mock"})
        if b["type"] == "mock":
            backend = MockLLM(model=b.get("model", "mock-1"), logger=logger)
        elif b["type"] == "openai_compat":
            backend = OpenAICompatLLM(model=b["model"], base_url=b["base_url"], logger=logger)
        else:
            raise ValueError(f"unknown backend {b['type']!r}")
        base = build_reranker({"type": spec.get("base", "bm25"), "name": "base"}, seed, logger)
        return LLMJudgeFilter(
            base=base, backend=backend, top_m=spec.get("top_m", 10), seed=seed, name=spec["name"]
        )
    raise ValueError(f"unknown reranker type {kind!r}")


def per_query_metrics(
    examples: Sequence[Example],
    rankings: dict[str, Ranking],
    ref: dict[str, Ranking],
    ks: Sequence[int],
    reasons: Sequence[str],
) -> PerQuery:
    out: PerQuery = {}
    for ex in examples:
        r = rankings[ex.qid]
        gold = ex.gold_pids
        row: dict[str, float | None] = {"mrr": mrr(r.order, gold)}
        for k in ks:
            row[f"recall@{k}"] = recall_at_k(r.order, gold, k)
            row[f"ndcg@{k}"] = ndcg_at_k(r.order, gold, k)
        row.update(conflict_metrics(ex, r, ref[ex.qid], ks, reasons))
        row["llm_calls"] = float(r.llm_calls)
        out[ex.qid] = row
    return out


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


def run_systems(
    examples: Sequence[Example],
    system_specs: Sequence[dict[str, Any]],
    reference_name: str,
    ks: Sequence[int],
    reasons: Sequence[str],
    default_seed: int,
    logger: TokenLogger | None = None,
) -> dict[str, SystemResult]:
    ref_spec = next(s for s in system_specs if s["name"] == reference_name)
    ref_rankings = _rank_all(build_reranker(ref_spec, default_seed, logger), examples)
    results: dict[str, SystemResult] = {}
    for spec in system_specs:
        seeds = list(spec.get("seeds", [default_seed]))
        per_seed: list[PerQuery] = []
        for s in seeds:
            rankings = _rank_all(build_reranker(spec, s, logger), examples)
            per_seed.append(per_query_metrics(examples, rankings, ref_rankings, ks, reasons))
        seed_means: dict[str, list[float]] = {}
        for m in per_seed[0][examples[0].qid]:
            for ps in per_seed:
                vals = [row[m] for row in ps.values() if row[m] is not None]
                if vals:
                    seed_means.setdefault(m, []).append(statistics.fmean(vals))
        results[spec["name"]] = SystemResult(
            spec["name"], seeds, _mean_over_seeds(per_seed), seed_means
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
    summary: dict[str, Any] = {"systems": {}, "paired_vs_reference": {}, "wfr_mcnemar": {}}
    for name, res in results.items():
        metrics: dict[str, Any] = {}
        for m in next(iter(res.per_query.values())):
            vals = [row[m] for row in res.per_query.values() if row[m] is not None]
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
        qids = [
            q
            for q in ref
            if ref[q].get("wfr") is not None and res.per_query[q].get("wfr") is not None
        ]
        binary = all(
            ref[q]["wfr"] in (0.0, 1.0) and res.per_query[q]["wfr"] in (0.0, 1.0) for q in qids
        )
        if qids and binary:
            b01 = sum(ref[q]["wfr"] == 0.0 and res.per_query[q]["wfr"] == 1.0 for q in qids)
            b10 = sum(ref[q]["wfr"] == 1.0 and res.per_query[q]["wfr"] == 0.0 for q in qids)
            pvals[name] = mcnemar_exact(b01, b10)
            summary["wfr_mcnemar"][name] = {"b01": b01, "b10": b10, "p": pvals[name]}
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


def decision_counts(examples: Sequence[Example]) -> dict[str, int]:
    c: Counter[str] = Counter(cand.decision.value for ex in examples for cand in ex.candidates)
    return {d.value: c.get(d.value, 0) for d in Decision}
