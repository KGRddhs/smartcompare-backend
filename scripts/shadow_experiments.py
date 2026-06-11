#!/usr/bin/env python3
"""Bundle B S2 Lane I4 — shadow verdict-experiment + A/B harness.

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md §4 (Lane I4).
Design inputs: docs/plans/2026-06-10-bundle-b-s2-design-inputs.md §3/§4.
Evidence report (output of this harness): docs/plans/2026-06-12-s2-shadow-results.md.

WHAT THIS IS
------------
Ahmed's Decision-D instrument: "try all possible methods and A/B test the
best winners and review against the current improvement." It re-grades
ALTERNATIVE verdict configurations (different model, multi-agent split,
trimmed review context, ...) against the gold set WITHOUT re-running the
full pipeline — so it never burns Serper credits.

THE SERPER-DISCIPLINE TRICK (load-bearing)
------------------------------------------
The S1 baseline run (eval_runs 4aee8e88, 2026-06-10, ?nocache=true) skips
the L2 cache *reads* but its *writes* still fire: after fresh extraction the
orchestrator unconditionally calls save_specs / save_price / save_reviews
(structured_comparison_service.py:2466-69 etc). So the product specs / prices
/ reviews the baseline verdicts actually saw are now sitting in the L2
`product_*` tables, keyed by brand+name+variant. This harness:

  1. reconstructs each gold query's `product_data[i]` dict from those L2 rows
     (join on brand+name within category — NOT the opaque product_key hash),
  2. computes `scores_summary` with the real deterministic scoring_service
     ($0, no network),
  3. runs ONLY the verdict LLM call per arm (the single thing an arm varies),
  4. grades winner + factual with the eval_runner grading functions (imported,
     never forked),
  5. holds price + specs axes at their baseline values (a verdict swap can't
     move them — they're set by the extraction pipeline, which we don't re-run).

COVERAGE BOUNDARY (stated honestly in the report)
-------------------------------------------------
Only the http-200 baseline rows have reconstructable verdict inputs. The 46
error rows (39 http_400 + 6 http_502 + 1 timeout) never ran a verdict, so
there is nothing to re-grade — that is Lane I5's recovery domain. Every arm
reports its exact covered-N.

COST
----
Input reconstruction = DB reads only ($0, no Serper). Verdict arms call
OpenAI (gpt-4o / o3-mini / gpt-4o-mini) — real per-call cost is metered and
reported. Live arms are marked live_unit and gated behind --run; the default
invocation only prepares + caches inputs and is fully offline-testable.

Usage:
    # offline — reconstruct + cache verdict inputs from L2 (no OpenAI, no Serper)
    python -m scripts.shadow_experiments prepare --subset bias45 --out .shadow/inputs.jsonl

    # live — run a verdict arm over cached inputs (dispatcher-announced; OpenAI cost)
    python -m scripts.shadow_experiments run --arm baseline_4o   --inputs .shadow/inputs.jsonl
    python -m scripts.shadow_experiments run --arm o3_mini        --inputs .shadow/inputs.jsonl
    python -m scripts.shadow_experiments run --arm multiagent     --inputs .shadow/inputs.jsonl
    python -m scripts.shadow_experiments run --arm reviews_trim   --inputs .shadow/inputs.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# eval_runner grading + extraction functions — IMPORTED, never forked, so the
# shadow grade and the production eval grade are the same code path.
from scripts.eval_runner import (
    collect_verdict_text,
    grade_factual,
    grade_winner,
    load_axis_weights,
    load_gold_truth,
    weighted_pass_score,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLD = REPO_ROOT / "data" / "validation_gold_truth.json"
BASELINE_GRADES = REPO_ROOT / ".qa-bias-rerun" / "baseline_s1_per_query.jsonl"

# The 45-id pure winner-bias set (dossier §1): no error, price+factual pass,
# specs >= 0.5, winner fails. These are the unambiguous teaching/measurement
# rows for verdict-quality arms. Spread: fashion 7, makeup 6, skincare 6,
# grocery 6, fragrances 6, other 5, electronics 4, haircare 3, supplements 2.
# Derived from baseline_s1_per_query.jsonl (see select_bias45()), kept here as
# a documented constant so the harness is reproducible if the jsonl moves.
# NOTE: this is computed at runtime from the baseline grades; the literal list
# below is the 2026-06-10 snapshot used for cross-checking.
BIAS45_SNAPSHOT_2026_06_10: Tuple[str, ...] = ()  # populated by tools/_dump on demand


# ---------------------------------------------------------------------------
# Baseline grades (the labels we measure deltas against)
# ---------------------------------------------------------------------------

def load_baseline_grades(path: Path | str = BASELINE_GRADES) -> Dict[str, Dict[str, Any]]:
    """Load the S1 per-query graded jsonl keyed by id.

    Each record matches eval_runner.GradedQuery: id, category, wall_ms,
    http_status, error, price_pass, specs_score, winner_pass, factual_pass,
    weighted_score, passing, wall_over_cap. This is the GRADES file (labels),
    not the raw responses — the raw verdict inputs come from L2."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"baseline grades missing: {path} — this file lives in the main "
            f"repo's .qa-bias-rerun/ (gitignored). Point --baseline at it."
        )
    out: Dict[str, Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        out[rec["id"]] = rec
    return out


def select_bias45(baseline: Dict[str, Dict[str, Any]]) -> List[str]:
    """The 45-id pure winner-bias set, computed from the baseline grades.

    Criteria (dossier §1): error is None, price_pass True, factual_pass True,
    specs_score >= 0.5, winner_pass False. Returns ids in baseline order."""
    ids = [
        rec_id
        for rec_id, rec in baseline.items()
        if rec.get("error") is None
        and rec.get("price_pass") is True
        and rec.get("factual_pass") is True
        and (rec.get("specs_score") or 0.0) >= 0.5
        and rec.get("winner_pass") is False
    ]
    return ids


def select_graded200(baseline: Dict[str, Dict[str, Any]]) -> List[str]:
    """All http-200 rows (error is None) — the full reconstructable set."""
    return [rec_id for rec_id, rec in baseline.items() if rec.get("error") is None]


# ---------------------------------------------------------------------------
# Verdict input reconstruction from L2 (zero Serper)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class VerdictInput:
    """Everything a verdict arm needs for one gold query, reconstructed from
    L2 + the gold record. This is what `prepare` caches to jsonl so `run`
    never touches the DB (or Serper)."""
    id: str
    category: str
    query: str
    region: str
    comparison_type: str
    expected_winner_index: Optional[int]
    forbidden_facts: List[str]
    # The two product_data dicts (verdict consumes specs/price/reviews/best_price).
    product_data: List[Dict[str, Any]]
    # Deterministic scores_summary string (computed offline via scoring_service).
    scores_summary: str
    # Baseline grade labels for this id (price_pass/specs_score held constant).
    baseline_price_pass: bool
    baseline_specs_score: float
    baseline_winner_pass: bool
    baseline_factual_pass: bool

    def to_json(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_json(cls, d: Dict[str, Any]) -> "VerdictInput":
        return cls(**d)


def _split_products_from_query(query: str) -> Optional[Tuple[str, str]]:
    """Split a gold query 'A vs B' into its two product name halves.

    The gold queries are authored as '<product1> vs <product2>'. This is a
    best-effort split on the ' vs ' separator (case-insensitive, first
    occurrence). Returns None when there is no clean 2-way split."""
    import re

    parts = re.split(r"\s+vs\.?\s+", query, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    a, b = parts[0].strip(), parts[1].strip()
    if not a or not b:
        return None
    return a, b


def _norm(s: str) -> str:
    """Lowercase + collapse whitespace + drop punctuation for fuzzy product
    name matching against the L2 brand/name columns."""
    import re

    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def match_l2_product(
    product_phrase: str,
    category: str,
    l2_rows: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Match one gold product phrase (e.g. 'NOW Foods D3') to an L2 row.

    l2_rows are the joined specs+reviews+price rows (each carries brand, name,
    variant, category, specs, reviews, price). Matching strategy, in order:
      1. exact normalized 'brand name' == normalized phrase,
      2. normalized 'brand name' is a token-subsequence of the phrase or v.v.,
      3. brand-token overlap + name-token overlap both non-empty, best score.
    Category is a soft filter (preferred, not required — the parser can
    re-categorize). Returns the best row or None."""
    target = _norm(product_phrase)
    target_tokens = set(target.split())
    if not target_tokens:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for row in l2_rows:
        bn = _norm(f"{row.get('brand', '')} {row.get('name', '')}")
        bn_tokens = set(bn.split())
        if not bn_tokens:
            continue
        score = 0.0
        # Exact match is the strongest signal.
        if bn == target:
            score = 1000.0
        else:
            # Subsequence either direction (handles 'iPhone 15' vs 'Apple iPhone 15').
            if bn in target or target in bn:
                score = 100.0 + len(bn_tokens)
            # Token overlap (Jaccard-ish, weighted by absolute overlap count).
            overlap = bn_tokens & target_tokens
            if overlap:
                score += len(overlap) * 10.0 + len(overlap) / max(len(bn_tokens | target_tokens), 1)
        # Category agreement is a tie-breaker bonus.
        if (row.get("category") or "").lower() == (category or "").lower():
            score += 1.0
        if score > best_score:
            best_score = score
            best = row
    # Require at least one shared content token to avoid garbage matches.
    if best is not None and best_score >= 11.0:
        return best
    return None


def assemble_product_data(query_id: str, gold_record: Dict[str, Any],
                          row_a: Optional[Dict[str, Any]],
                          row_b: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Build the two `product_data[i]` dicts the verdict call consumes from the
    matched L2 rows. Returns None when either product is unmatched (we never
    half-fabricate a verdict input). Mirrors the orchestrator's result-dict
    shape (structured_comparison_service.py:2034)."""
    if row_a is None or row_b is None:
        return None
    out: List[Dict[str, Any]] = []
    for row in (row_a, row_b):
        brand = row.get("brand") or ""
        name = row.get("name") or ""
        variant = row.get("variant")
        specs = row.get("specs") or {}
        price = row.get("price")  # dict {amount,currency,...} or None
        reviews = row.get("reviews") or {}
        pd: Dict[str, Any] = {
            "brand": brand,
            "name": name,
            "full_name": f"{brand} {name} {variant or ''}".strip(),
            "variant": variant,
            "category": row.get("category") or gold_record.get("category") or "other",
            "specs": specs,
            "reviews": reviews,
        }
        if isinstance(price, dict):
            pd["price"] = price
            if price.get("amount") is not None:
                pd["best_price"] = price.get("amount")
        out.append(pd)
    return out


# ---------------------------------------------------------------------------
# Grading a re-run verdict against gold (winner + factual only)
# ---------------------------------------------------------------------------

def _verdict_to_eval_body(verdict: Dict[str, Any],
                          product_data: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Splice a re-run verdict dict into the minimal response `body` shape the
    eval_runner extractors read (extract_winner_index + collect_verdict_text).

    The verdict dict (generate_comparison output) carries winner_index +
    free-text (winner_reason / winner_declaration / value_context / best_for /
    factual_verdict). We map those onto:
      - scoring_v2.overall_score.winner_idx (extract_winner_index reads this),
      - overview.winner.{declaration,reason,key_tradeoff,winner_declaration},
      - overview.products[i].best_for,
      - scoring_v2.factual_verdict.{line1,line2},
      - reviews.products[i].review_summary.{consensus,highlights}
    so collect_verdict_text scans the same surface production grading does."""
    winner_idx = verdict.get("winner_index")
    if winner_idx is None:
        winner_idx = verdict.get("winner_idx")

    # Pull every free-text field the verdict might carry into the body so the
    # factual grader sees the full prose surface.
    winner_block: Dict[str, Any] = {}
    if winner_idx is not None:
        winner_block["product_index"] = winner_idx
    for src_key, dst_key in (
        ("winner_reason", "reason"),
        ("winner_declaration", "winner_declaration"),
        ("key_tradeoff", "key_tradeoff"),
        ("declaration", "declaration"),
    ):
        val = verdict.get(src_key)
        if isinstance(val, str):
            winner_block[dst_key] = val

    overview_products: List[Dict[str, Any]] = []
    # best_for can be a per-product dict {product_0:..,product_1:..} or list.
    best_for = verdict.get("best_for")
    value_context = verdict.get("value_context")
    for i in range(len(product_data)):
        prod_entry: Dict[str, Any] = {}
        bf_text = _per_product_text(best_for, i)
        vc_text = _per_product_text(value_context, i)
        merged = " ".join(t for t in (bf_text, vc_text) if t)
        if merged:
            prod_entry["best_for"] = merged
        overview_products.append(prod_entry)

    # factual_verdict line1/line2 if present (Bundle C A.3.2 shape).
    fv = verdict.get("factual_verdict")
    factual_block: Dict[str, Any] = {}
    if isinstance(fv, dict):
        for k in ("line1", "line2"):
            if isinstance(fv.get(k), str):
                factual_block[k] = fv[k]
    elif isinstance(fv, str):
        factual_block["line1"] = fv

    body: Dict[str, Any] = {
        "overview": {"winner": winner_block, "products": overview_products},
        "scoring_v2": {
            "overall_score": {"winner_idx": winner_idx},
            "factual_verdict": factual_block,
        },
    }
    return body


def _per_product_text(field: Any, idx: int) -> str:
    """Extract product-idx text from a best_for/value_context field that may be
    a per-product dict ({'product_0':..}), a list, or a plain string."""
    if field is None:
        return ""
    if isinstance(field, str):
        return field if idx == 0 else ""
    if isinstance(field, dict):
        val = field.get(f"product_{idx}")
        if val is None and idx < len(field):
            # numeric-keyed fallback
            val = list(field.values())[idx] if len(field) > idx else None
        return val if isinstance(val, str) else ""
    if isinstance(field, (list, tuple)):
        if idx < len(field) and isinstance(field[idx], str):
            return field[idx]
    return ""


@dataclasses.dataclass
class ArmGrade:
    """One query's graded outcome under one arm. Price+specs are inherited from
    baseline (a verdict swap doesn't move them); winner+factual are re-graded
    from the arm's verdict."""
    id: str
    category: str
    price_pass: bool
    specs_score: float
    winner_pass: bool
    factual_pass: bool
    weighted_score: float
    passing: bool
    baseline_winner_pass: bool
    baseline_weighted: float
    winner_flipped_to_correct: bool
    winner_flipped_to_wrong: bool
    verdict_ms: int
    cost_usd: float
    error: Optional[str] = None


def grade_arm_verdict(vi: VerdictInput, verdict: Dict[str, Any],
                      *, verdict_ms: int, cost_usd: float,
                      weights: Dict[str, float],
                      query_pass_threshold: float = 0.80,
                      error: Optional[str] = None) -> ArmGrade:
    """Grade one arm's verdict for one query: winner + factual re-graded from
    the verdict; price + specs held at the baseline labels. Compose the
    weighted score with the canonical axis weights so the number is directly
    comparable to the eval_runner aggregate."""
    if error is not None:
        # Arm failed to produce a verdict — score it as a winner+factual miss
        # but keep baseline price/specs so the weighted number is honest about
        # which axis the failure hit.
        winner_pass = False
        factual_pass = False
    else:
        body = _verdict_to_eval_body(verdict, vi.product_data)
        from scripts.eval_runner import extract_winner_index

        actual_winner = extract_winner_index(body)
        winner_pass = grade_winner(actual_winner, vi.expected_winner_index)
        factual_pass = grade_factual(collect_verdict_text(body), vi.forbidden_facts)

    weighted = weighted_pass_score(
        vi.baseline_price_pass, vi.baseline_specs_score, winner_pass, factual_pass,
        weights=weights,
    )
    passing = error is None and weighted >= query_pass_threshold
    return ArmGrade(
        id=vi.id,
        category=vi.category,
        price_pass=vi.baseline_price_pass,
        specs_score=round(vi.baseline_specs_score, 4),
        winner_pass=winner_pass,
        factual_pass=factual_pass,
        weighted_score=round(weighted, 4),
        passing=passing,
        baseline_winner_pass=vi.baseline_winner_pass,
        baseline_weighted=round(
            weighted_pass_score(
                vi.baseline_price_pass, vi.baseline_specs_score,
                vi.baseline_winner_pass, vi.baseline_factual_pass, weights=weights,
            ), 4,
        ),
        winner_flipped_to_correct=(winner_pass and not vi.baseline_winner_pass),
        winner_flipped_to_wrong=((not winner_pass) and vi.baseline_winner_pass),
        verdict_ms=verdict_ms,
        cost_usd=round(cost_usd, 6),
        error=error,
    )


# ---------------------------------------------------------------------------
# Arm aggregation
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ArmReport:
    """Aggregate of one arm over the covered query set."""
    arm: str
    n_covered: int
    n_passing: int
    pass_rate: float
    axis_avg_price: float
    axis_avg_specs: float
    axis_avg_winner: float
    axis_avg_factual: float
    winner_flips_to_correct: int
    winner_flips_to_wrong: int
    net_winner_flips: int
    baseline_winner_rate: float
    arm_winner_rate: float
    total_cost_usd: float
    mean_cost_usd: float
    mean_verdict_ms: float
    p50_verdict_ms: int
    p95_verdict_ms: int
    n_errors: int
    per_query: List[ArmGrade]


def aggregate_arm(arm: str, grades: List[ArmGrade]) -> ArmReport:
    n = len(grades)

    def _avg(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    walls = sorted(g.verdict_ms for g in grades if g.error is None)

    def _pct(p: float) -> int:
        if not walls:
            return 0
        k = max(0, min(len(walls) - 1, int(round(p * (len(walls) - 1)))))
        return walls[k]

    flips_correct = sum(1 for g in grades if g.winner_flipped_to_correct)
    flips_wrong = sum(1 for g in grades if g.winner_flipped_to_wrong)
    costs = [g.cost_usd for g in grades if g.error is None]
    return ArmReport(
        arm=arm,
        n_covered=n,
        n_passing=sum(1 for g in grades if g.passing),
        pass_rate=round(sum(1 for g in grades if g.passing) / n, 4) if n else 0.0,
        axis_avg_price=_avg([1.0 if g.price_pass else 0.0 for g in grades]),
        axis_avg_specs=_avg([g.specs_score for g in grades]),
        axis_avg_winner=_avg([1.0 if g.winner_pass else 0.0 for g in grades]),
        axis_avg_factual=_avg([1.0 if g.factual_pass else 0.0 for g in grades]),
        winner_flips_to_correct=flips_correct,
        winner_flips_to_wrong=flips_wrong,
        net_winner_flips=flips_correct - flips_wrong,
        baseline_winner_rate=_avg([1.0 if g.baseline_winner_pass else 0.0 for g in grades]),
        arm_winner_rate=_avg([1.0 if g.winner_pass else 0.0 for g in grades]),
        total_cost_usd=round(sum(costs), 6),
        mean_cost_usd=round(sum(costs) / len(costs), 6) if costs else 0.0,
        mean_verdict_ms=round(sum(walls) / len(walls), 1) if walls else 0.0,
        p50_verdict_ms=_pct(0.50),
        p95_verdict_ms=_pct(0.95),
        n_errors=sum(1 for g in grades if g.error is not None),
        per_query=grades,
    )
