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

# Structural-vs-variance decomposition of the 45-id pure-bias set, derived from
# the 4-arm bias45 agreement analysis (commit ec436fc):
#   STRUCTURAL = all 4 verdict configs (4o / o3-mini / multiagent / reviews-trim)
#                picked the SAME wrong winner -> a real reasoning bias, the I1/I2
#                few-shot target.
#   VARIANCE   = all 4 configs picked the gold winner -> the S1 baseline got them
#                wrong on a one-shot at T=0.2; they flip on any re-run.
#   SPLIT      = configs disagreed -> true run-to-run noise.
# The dispatcher requires every variance-reduction arm's winner rate reported
# split by these buckets (does T=0 / best-of-3 recover the VARIANCE bucket
# without disturbing STRUCTURAL?).
STRUCTURAL_IDS: frozenset = frozenset({
    "elec-012", "elec-018", "elec-024", "fash-006", "fash-008", "fash-011",
    "fash-013", "fash-014", "frag-010", "frag-011", "frag-014", "frag-018",
    "groc-004", "groc-011", "groc-014", "make-011", "make-014", "other-009",
    "other-010", "other-012", "other-019", "skin-009", "skin-013", "supp-020",
})
VARIANCE_IDS: frozenset = frozenset({
    "elec-033", "fash-009", "fash-016", "frag-007", "frag-016", "groc-009",
    "hair-001", "hair-014", "hair-021", "make-003", "make-009", "make-013",
    "make-016", "other-011", "skin-005", "skin-010", "skin-015", "skin-018",
    "supp-013",
})
SPLIT_IDS: frozenset = frozenset({"groc-002", "groc-023"})


def split_winner_rate(grades: Sequence["ArmGrade"]) -> Dict[str, Dict[str, Any]]:
    """Winner rate within each agreement bucket (structural / variance / split /
    other) for an arm's graded rows. 'other' catches any id not in the three
    buckets (shouldn't happen on bias45, but keeps the accounting total)."""
    buckets = {
        "structural": STRUCTURAL_IDS,
        "variance": VARIANCE_IDS,
        "split": SPLIT_IDS,
    }
    out: Dict[str, Dict[str, Any]] = {}
    classified: set = set()
    for name, ids in buckets.items():
        rows = [g for g in grades if g.id in ids]
        classified.update(g.id for g in rows)
        n = len(rows)
        wins = sum(1 for g in rows if g.winner_pass)
        out[name] = {"n": n, "winner_correct": wins,
                     "winner_rate": round(wins / n, 4) if n else 0.0}
    other = [g for g in grades if g.id not in classified]
    if other:
        wins = sum(1 for g in other if g.winner_pass)
        out["other"] = {"n": len(other), "winner_correct": wins,
                        "winner_rate": round(wins / len(other), 4)}
    return out


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


# Abbreviation/alias expansions for brand+name JOIN robustness. A gold query
# may use a colloquial short form ("PS5") while the L2 row carries the full
# canonical name ("Sony PlayStation 5") with ZERO shared tokens — token overlap
# then fails honestly. This map expands the gold token to the canonical tokens
# so the join recovers without weakening the match gate. Scoped to abbreviations
# that actually appear in the gold set (audited: PS5 is the only zero-overlap
# case in gold-200) plus a few defensive electronics/GCC forms. Keys + values
# are pre-normalized (lowercase, space-delimited).
_ALIAS_EXPANSIONS: Dict[str, str] = {
    "ps5": "playstation 5",
    "ps4": "playstation 4",
    "xbox": "xbox",  # identity — guards against future bare-token drift
}


def _expand_aliases(tokens: set) -> set:
    """Augment a token set with canonical expansions of any known abbreviation
    tokens. Additive (never removes) so the original tokens still match too."""
    expanded = set(tokens)
    for tok in tokens:
        alias = _ALIAS_EXPANSIONS.get(tok)
        if alias:
            expanded.update(alias.split())
    return expanded


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
    Known abbreviations (PS5 -> PlayStation 5) are alias-expanded so the JOIN
    recovers colloquial gold phrasing. Category is a soft filter (preferred, not
    required — the parser can re-categorize). Returns the best row or None."""
    target = _norm(product_phrase)
    target_tokens = _expand_aliases(set(target.split()))
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
    # SERVED model id(s) from resp.model — proves the arm ran on the requested
    # model, not a silent fallback (G5 evidence hygiene).
    response_model: str = ""


def grade_arm_verdict(vi: VerdictInput, verdict: Dict[str, Any],
                      *, verdict_ms: int, cost_usd: float,
                      weights: Dict[str, float],
                      query_pass_threshold: float = 0.80,
                      error: Optional[str] = None,
                      response_model: str = "") -> ArmGrade:
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
        response_model=response_model,
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


# ---------------------------------------------------------------------------
# OpenAI pricing (per 1M tokens) — published rates, applied to METERED token
# counts. Token counts are stored alongside the derived cost so the dollar
# figure is reconstructible if a rate changes. Mirrors openai_service.py's
# gpt-4o-mini convention ($0.15 in / $0.60 out).
# ---------------------------------------------------------------------------

MODEL_PRICING_PER_1M: Dict[str, Tuple[float, float]] = {
    # model: (input_usd_per_1M, output_usd_per_1M)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o3-mini": (1.10, 4.40),
}


def call_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Dollar cost of one call from metered token counts + the published rate.
    Unknown models fall back to gpt-4o-mini pricing (and log a warning)."""
    rate = MODEL_PRICING_PER_1M.get(model)
    if rate is None:
        logger.warning("[shadow] no pricing for model %s — using gpt-4o-mini rate", model)
        rate = MODEL_PRICING_PER_1M["gpt-4o-mini"]
    in_rate, out_rate = rate
    return (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000


# ---------------------------------------------------------------------------
# L2 input reconstruction (the `prepare` step — DB reads only, ZERO Serper)
# ---------------------------------------------------------------------------

# An L2 dump (env SHADOW_L2_DUMP -> jsonl path) is the sandbox-safe input path:
# each line is one already-joined product row {brand,name,variant,category,
# specs,reviews,price}. Generated out-of-band via the Supabase MCP channel (see
# scripts/dump_l2_for_shadow.sql + the runbook), then read here with no network.
# Falls back to a live DB read when the env is unset (and the box has network).
_L2_DUMP_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None


def _load_l2_dump(path: Path | str) -> Dict[str, List[Dict[str, Any]]]:
    """Load a pre-exported L2 dump jsonl, grouped by category for the matcher.
    Each line: {brand,name,variant,category,specs,reviews,price}."""
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        by_cat.setdefault((row.get("category") or "other"), []).append(row)
    return by_cat


def _fetch_l2_rows_for_category(category: str) -> List[Dict[str, Any]]:
    """Join product_specs + product_reviews + latest product_price for every
    L2 product in a category, returning rows the matcher can search.

    If SHADOW_L2_DUMP is set, reads from that pre-exported jsonl (sandbox-safe,
    no network — this is the normal path on the restricted box). Otherwise hits
    the live DB via the service-role admin client. Reviews/price are LEFT-joined
    (a product with specs but no reviews still appears; the verdict tolerates
    empty reviews). Price is the most-recent bahrain row."""
    global _L2_DUMP_CACHE
    if _L2_DUMP_CACHE is None:
        _L2_DUMP_CACHE = _load_all_l2_rows()
    # Return the requested category FIRST, then every other category as a
    # cross-category fallback so a product the parser re-categorized (e.g. an
    # air cooler authored under gold 'other' but stored under 'electronics')
    # is still matchable. match_l2_product's category-bonus keeps the
    # same-category row preferred when both exist.
    primary = _L2_DUMP_CACHE.get(category, [])
    others = [r for cat, rows in _L2_DUMP_CACHE.items() if cat != category for r in rows]
    return primary + others


def _load_all_l2_rows() -> Dict[str, List[Dict[str, Any]]]:
    """Load EVERY fresh L2 product (all categories) once, grouped by category.

    Reads from SHADOW_L2_DUMP when set (sandbox-safe), else the live DB. Three
    full-table reads total (specs / reviews / bahrain-prices), joined on
    lower(brand|name). Freshest row wins per product per table."""
    dump_path = os.getenv("SHADOW_L2_DUMP")
    if dump_path:
        return _load_l2_dump(dump_path)

    from app.services.database_service import get_admin_supabase_client

    client = get_admin_supabase_client()
    specs_rows = (
        client.table("product_specs")
        .select("brand, name, variant, category, specs, fetched_at")
        .order("fetched_at", desc=True)
        .execute()
    ).data or []
    rev_rows = (
        client.table("product_reviews")
        .select("brand, name, reviews, fetched_at")
        .order("fetched_at", desc=True)
        .execute()
    ).data or []
    price_rows = (
        client.table("product_prices")
        .select("brand, name, region, amount, currency, retailer, url, "
                "source_method, estimated, fetched_at")
        .eq("region", "bahrain")
        .order("fetched_at", desc=True)
        .execute()
    ).data or []

    reviews_by_bn: Dict[str, Dict[str, Any]] = {}
    for rr in rev_rows:
        bn = _norm(f"{rr.get('brand', '')} {rr.get('name', '')}")
        reviews_by_bn.setdefault(bn, rr.get("reviews") or {})

    price_by_bn: Dict[str, Dict[str, Any]] = {}
    for pr in price_rows:
        bn = _norm(f"{pr.get('brand', '')} {pr.get('name', '')}")
        if bn in price_by_bn:
            continue
        price_by_bn[bn] = {
            "amount": float(pr["amount"]) if pr.get("amount") is not None else None,
            "currency": pr.get("currency"),
            "retailer": pr.get("retailer"),
            "url": pr.get("url"),
            "source_method": pr.get("source_method"),
            "estimated": pr.get("estimated") or False,
        }

    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    seen: set = set()
    for sr in specs_rows:
        bn = _norm(f"{sr.get('brand', '')} {sr.get('name', '')}")
        if bn in seen:
            continue  # freshest specs row per product only
        seen.add(bn)
        cat = sr.get("category") or "other"
        by_cat.setdefault(cat, []).append({
            "brand": sr.get("brand"),
            "name": sr.get("name"),
            "variant": sr.get("variant"),
            "category": cat,
            "specs": sr.get("specs") or {},
            "reviews": reviews_by_bn.get(bn, {}),
            "price": price_by_bn.get(bn),
        })
    return by_cat


def _compute_scores_summary_offline(product_data: List[Dict[str, Any]]) -> str:
    """Run the REAL deterministic scoring_service over the reconstructed
    product_data and build the scores_summary string the verdict consumes.
    Fully offline ($0) — scoring is pure arithmetic over specs/price/reviews."""
    from app.services.scoring_service import get_scoring_service

    svc = get_scoring_service()
    scoring_result = svc.compute_scores(product_data)
    names = [f"{p.get('brand', '')} {p.get('name', '')}".strip() for p in product_data]
    return svc.build_scores_summary(scoring_result, names)


def build_verdict_inputs(
    gold: Dict[str, Any],
    baseline: Dict[str, Dict[str, Any]],
    ids: Sequence[str],
) -> Tuple[List[VerdictInput], List[Dict[str, Any]]]:
    """Reconstruct VerdictInput records for the requested ids from L2 + gold.

    Returns (built_inputs, skipped) where skipped carries a reason per id that
    could not be reconstructed (unmatched product, unsplittable query, missing
    baseline). NEVER half-fabricates — an unmatched product skips the whole id.
    Caches L2 rows per category so each category is read once."""
    gold_by_id = {q["id"]: q for q in gold.get("queries", [])}
    l2_cache: Dict[str, List[Dict[str, Any]]] = {}
    built: List[VerdictInput] = []
    skipped: List[Dict[str, Any]] = []

    for qid in ids:
        gold_rec = gold_by_id.get(qid)
        base_rec = baseline.get(qid)
        if gold_rec is None:
            skipped.append({"id": qid, "reason": "no_gold_record"})
            continue
        if base_rec is None:
            skipped.append({"id": qid, "reason": "no_baseline_grade"})
            continue
        if base_rec.get("error") is not None:
            skipped.append({"id": qid, "reason": f"baseline_error:{base_rec['error']}"})
            continue

        split = _split_products_from_query(gold_rec["query"])
        if split is None:
            skipped.append({"id": qid, "reason": "unsplittable_query"})
            continue
        phrase_a, phrase_b = split
        category = gold_rec.get("category", "other")

        if category not in l2_cache:
            try:
                l2_cache[category] = _fetch_l2_rows_for_category(category)
            except Exception as exc:  # noqa: BLE001
                logger.error("[shadow] L2 fetch failed for category %s: %s", category, exc)
                l2_cache[category] = []
        rows = l2_cache[category]

        row_a = match_l2_product(phrase_a, category, rows)
        row_b = match_l2_product(phrase_b, category, rows)
        product_data = assemble_product_data(qid, gold_rec, row_a, row_b)
        if product_data is None:
            skipped.append({
                "id": qid,
                "reason": "l2_unmatched",
                "matched_a": bool(row_a),
                "matched_b": bool(row_b),
                "phrase_a": phrase_a,
                "phrase_b": phrase_b,
            })
            continue

        try:
            scores_summary = _compute_scores_summary_offline(product_data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[shadow] scores_summary failed for %s: %s", qid, exc)
            scores_summary = ""

        built.append(VerdictInput(
            id=qid,
            category=category,
            query=gold_rec["query"],
            region=gold_rec.get("region", "bahrain"),
            comparison_type=gold_rec.get("comparison_type", "value"),
            expected_winner_index=gold_rec.get("expected_winner_index"),
            forbidden_facts=gold_rec.get("forbidden_facts") or [],
            product_data=product_data,
            scores_summary=scores_summary,
            baseline_price_pass=bool(base_rec.get("price_pass")),
            baseline_specs_score=float(base_rec.get("specs_score") or 0.0),
            baseline_winner_pass=bool(base_rec.get("winner_pass")),
            baseline_factual_pass=bool(base_rec.get("factual_pass")),
        ))
    return built, skipped


def write_verdict_inputs(inputs: List[VerdictInput], path: Path | str) -> None:
    """Cache reconstructed inputs to jsonl so `run` is fully offline of the DB."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for vi in inputs:
            fh.write(json.dumps(vi.to_json(), ensure_ascii=False) + "\n")


def read_verdict_inputs(path: Path | str) -> List[VerdictInput]:
    path = Path(path)
    out: List[VerdictInput] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(VerdictInput.from_json(json.loads(line)))
    return out


# ---------------------------------------------------------------------------
# Verdict arms (the `run` step — the ONLY part that calls OpenAI)
# ---------------------------------------------------------------------------
#
# An arm is `async (VerdictInput) -> ArmCallResult`. Each arm varies exactly
# one thing about the verdict call (model, agent structure, review-context
# size). They share the production verdict CONTRACT: build the system prompt
# the same way generate_comparison does (COMPARISON_SYSTEM + personality +
# pain-workflow), wrap product_data in the same <USER_INPUT> envelope, request
# json_object, parse winner_index + prose. This keeps every arm an honest
# swap of the one variable, not a different prompt.

@dataclasses.dataclass
class ArmCallResult:
    verdict: Dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    model: str  # the REQUESTED model (what the arm asked for)
    error: Optional[str] = None
    # The SERVED model id from resp.model (e.g. 'o3-mini-2025-01-31') — the
    # evidence that the call ran on the model it requested, not a silent
    # fallback. Multiagent stores the editor's served model (its 4o leg).
    response_model: str = ""


def _build_verdict_system_prompt(vi: VerdictInput) -> str:
    """Build the verdict system prompt by calling the REAL production
    `build_verdict_prompt` (extraction_service.py) + the scoring-context block,
    byte-faithful to `generate_comparison` (ssc unification, I5.10).

    `build_verdict_prompt` already composes COMPARISON_SYSTEM + personality +
    the I2 exemplar/anti-pattern block (from data/verdict_exemplars.json) +
    pain-workflow — so whatever exemplar file is on disk is what every arm sees.
    The prompt-arm swaps that file content (see arm_prompt_exemplars) rather
    than appending a block, which keeps the A/B prod-faithful: baseline vs
    exemplar-prompt differ ONLY by the exemplar file, exactly as prod would
    differ before vs after I1's content lands. user_cohort=None (the shadow
    inputs carry no demographics); category is passed explicitly so the prompt
    is byte-identical to prod even when product dicts lack category_used."""
    from app.services.extraction_service import build_verdict_prompt

    system_msg = build_verdict_prompt(
        products=vi.product_data,
        comparison_quality="normal",
        user_cohort=None,
        category=vi.category,
    )
    if vi.scores_summary:
        system_msg += f"""

## Scoring Context
{vi.scores_summary}

## Verdict Requirements
1. WINNER REASON: State the winner with the score margin in under 20 words. Cite the single most important numeric advantage.
2. KEY TRADEOFF: Name the other product's strongest advantage -- what the user gives up by choosing the winner.
3. VALUE CONTEXT: Explain the value proposition. If cross-tier, acknowledge that each serves a different market segment -- do NOT penalize luxury for being expensive.
4. BEST FOR: One sentence per product describing the ideal buyer.

Your verdict MUST be consistent with the scores above. If Product A wins on reviews, your text must reflect that. Do NOT contradict the scoring data.
If this is a cross-tier comparison, frame it as "different products for different needs" rather than "expensive vs cheap."
"""
    return system_msg


def _build_verdict_user_msg(vi: VerdictInput,
                            review_context_chars: Optional[int] = None) -> str:
    """The <USER_INPUT> envelope generate_comparison sends. review_context_chars
    optionally trims each product's reviews payload (the I4.4 reviews-trim
    lever — measured against the untrimmed baseline arm)."""
    pd = [dict(p) for p in vi.product_data]
    if review_context_chars is not None:
        for p in pd:
            reviews = p.get("reviews")
            if isinstance(reviews, dict):
                # Serialize, truncate, keep as a string so the model still sees
                # the leading (most salient) review content but fewer tokens.
                blob = json.dumps(reviews, ensure_ascii=False)
                if len(blob) > review_context_chars:
                    p["reviews"] = blob[:review_context_chars]
    return f"""<USER_INPUT>
PRODUCT 1:
{json.dumps(pd[0], indent=2)}

PRODUCT 2:
{json.dumps(pd[1], indent=2)}

User's region: {vi.region}
Primary concern: {vi.comparison_type}
</USER_INPUT>"""


def _parse_verdict_json(content: str) -> Dict[str, Any]:
    """Parse the model's JSON verdict, tolerating ``` fences (generate_
    comparison:1278-1283)."""
    result = (content or "").strip()
    if result.startswith("```"):
        result = result.split("```")[1]
        if result.startswith("json"):
            result = result[4:]
    return json.loads(result)


# Bounded retry on 429 / rate-limit: the OpenAI org has a low gpt-4o TPM cap,
# so concurrent ~3k-token verdict calls trip 429s. A transient rate-limit must
# NOT score as an arm error (it would corrupt the factual axis — errored rows
# score factual=False). Exponential backoff + jitter, then surface the error.
_MAX_RETRIES = 6


async def _create_with_retry(client, **kwargs):
    """client.chat.completions.create with backoff on 429/rate-limit. Honors
    the Retry-After hint when the SDK exposes it; otherwise exponential."""
    import random

    delay = 2.0
    last_exc: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            is_rate = "429" in msg or "rate limit" in msg or "ratelimit" in msg \
                or type(exc).__name__ == "RateLimitError"
            if not is_rate or attempt == _MAX_RETRIES - 1:
                last_exc = exc
                raise
            wait = delay + random.uniform(0, 1.5)
            logger.info("[shadow] 429 backoff %.1fs (attempt %d/%d)",
                        wait, attempt + 1, _MAX_RETRIES)
            await asyncio.sleep(wait)
            delay = min(delay * 2, 30.0)
    if last_exc:
        raise last_exc


async def _chat_json(client, model: str, system_msg: str, user_msg: str,
                     *, max_tokens: int = 1000,
                     temperature: float = 0.2) -> Tuple[Dict[str, Any], int, int, str]:
    """One json_object chat call. Returns (parsed, prompt_tokens,
    completion_tokens, response_model).

    response_model is the SERVED model id from the API response (`resp.model`,
    e.g. 'o3-mini-2025-01-31'), NOT the request param — this is the evidence
    that proves an arm actually ran on the model it asked for (G5 hygiene: a
    request param is not proof; a silent fallback would surface here).

    o3-mini is a reasoning model: it rejects `temperature` and uses
    `max_completion_tokens` instead of `max_tokens`. Branch on the model
    family so the same helper drives every arm."""
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
    }
    if model.startswith("o3") or model.startswith("o1") or model.startswith("o4"):
        # Reasoning models: no temperature, token budget is max_completion_tokens,
        # and reasoning tokens eat into it — give headroom over the 4o budget.
        kwargs["max_completion_tokens"] = max(max_tokens * 4, 4000)
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    resp = await _create_with_retry(client, **kwargs)
    content = resp.choices[0].message.content
    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", 0) if usage else 0
    ct = getattr(usage, "completion_tokens", 0) if usage else 0
    response_model = getattr(resp, "model", "") or ""
    return _parse_verdict_json(content), pt, ct, response_model


async def arm_baseline_4o(vi: VerdictInput, client) -> ArmCallResult:
    """Control arm: gpt-4o verdict — the production verdict model. Re-running
    it (rather than reusing the baseline grade) controls for temperature
    variance + L2-reconstructed-input drift, so every other arm is compared
    on an apples-to-apples re-run, not against the original prod response."""
    system_msg = _build_verdict_system_prompt(vi)
    user_msg = _build_verdict_user_msg(vi)
    try:
        verdict, pt, ct, rm = await _chat_json(client, "gpt-4o", system_msg, user_msg)
        return ArmCallResult(verdict, pt, ct, "gpt-4o", response_model=rm)
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "gpt-4o", error=f"{type(exc).__name__}:{exc}")


async def arm_temp0(vi: VerdictInput, client) -> ArmCallResult:
    """Variance-reduction arm (dispatcher orders): gpt-4o verdict at
    temperature=0 (greedy decode). Identical prompt + inputs to arm_baseline_4o
    — the ONLY change is T=0.2 -> T=0. The shadow agreement analysis showed
    ~19/45 pure-bias failures are sampling variance at the prod T=0.2; greedy
    decode should recover much of that variance bucket at zero added cost.
    Same model rate, same call count — a free quality lever if it holds."""
    system_msg = _build_verdict_system_prompt(vi)
    user_msg = _build_verdict_user_msg(vi)
    try:
        verdict, pt, ct, rm = await _chat_json(client, "gpt-4o", system_msg, user_msg,
                                               temperature=0.0)
        return ArmCallResult(verdict, pt, ct, "gpt-4o", response_model=rm)
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "gpt-4o", error=f"{type(exc).__name__}:{exc}")


async def arm_best_of_3(vi: VerdictInput, client) -> ArmCallResult:
    """Variance-reduction arm (dispatcher orders): run the gpt-4o verdict 3x at
    the production T=0.2 and take the MAJORITY winner_index. Same prompt +
    inputs as arm_baseline_4o; the 3 samples vote on the winner. The verdict
    PROSE is taken from the sample whose winner_index matches the majority
    (so the returned text is self-consistent with the voted winner). Cost = 3x
    a single 4o call; the question the A/B answers is whether majority voting
    buys enough variance-bucket flips to justify 3x verdict cost vs the free
    T=0 arm. Reports its own (3x) cost."""
    system_msg = _build_verdict_system_prompt(vi)
    user_msg = _build_verdict_user_msg(vi)
    try:
        samples = await asyncio.gather(
            _chat_json(client, "gpt-4o", system_msg, user_msg),
            _chat_json(client, "gpt-4o", system_msg, user_msg),
            _chat_json(client, "gpt-4o", system_msg, user_msg),
        )
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "gpt-4o", error=f"{type(exc).__name__}:{exc}")

    verdicts = [s[0] for s in samples]
    total_pt = sum(s[1] for s in samples)
    total_ct = sum(s[2] for s in samples)
    sample_models = {s[3] for s in samples if s[3]}  # served models across the 3 samples

    # Majority vote on winner_index (None votes excluded; tie -> first sample's pick).
    from collections import Counter
    votes = []
    for v in verdicts:
        wi = v.get("winner_index")
        if wi is None:
            wi = v.get("winner_idx")
        if wi is not None:
            votes.append(wi)
    if votes:
        winner_idx, _ = Counter(votes).most_common(1)[0]
        # Return the prose of the FIRST sample that voted with the majority,
        # so the text is consistent with the declared winner.
        chosen = next((v for v in verdicts
                       if (v.get("winner_index", v.get("winner_idx")) == winner_idx)),
                      verdicts[0])
        chosen = dict(chosen)
        chosen["winner_index"] = winner_idx
    else:
        chosen = verdicts[0]
    return ArmCallResult(chosen, total_pt, total_ct, "gpt-4o",
                         response_model=",".join(sorted(sample_models)))


async def arm_o3_mini(vi: VerdictInput, client) -> ArmCallResult:
    """I4.2 — o3-mini verdict on identical inputs. Promotion bar: quality-up
    AND cost-neutral-or-better vs arm_baseline_4o."""
    system_msg = _build_verdict_system_prompt(vi)
    user_msg = _build_verdict_user_msg(vi)
    try:
        verdict, pt, ct, rm = await _chat_json(client, "o3-mini", system_msg, user_msg)
        return ArmCallResult(verdict, pt, ct, "o3-mini", response_model=rm)
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "o3-mini", error=f"{type(exc).__name__}:{exc}")


async def arm_reviews_trim(vi: VerdictInput, client) -> ArmCallResult:
    """I4.4 Decision-D lever: trim review context ([:2500] chars) on the gpt-4o
    verdict. Measured against arm_baseline_4o on winner/factual + latency.
    NOTE: this measures the verdict-stage effect of the trim only; the
    pipeline-wide -1-2s wall claim (extract_reviews max_tokens 1000->600) is an
    UPSTREAM change I5 owns — flagged in the report as out-of-harness-scope."""
    system_msg = _build_verdict_system_prompt(vi)
    user_msg = _build_verdict_user_msg(vi, review_context_chars=2500)
    try:
        verdict, pt, ct, rm = await _chat_json(client, "gpt-4o", system_msg, user_msg,
                                               max_tokens=600)
        return ArmCallResult(verdict, pt, ct, "gpt-4o", response_model=rm)
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "gpt-4o", error=f"{type(exc).__name__}:{exc}")


# --- Prompt-arm (dispatcher directive 2): baseline-prompt vs exemplar/AP-prompt
# -----------------------------------------------------------------------------
# The $0-Serper offline pre-read on the I1/I2 few-shot 45-id flip BEFORE the
# live nocache G3 indicator. Same gpt-4o model + same L2 inputs as
# arm_baseline_4o — the ONLY variable is the verdict-prompt's exemplar content.
#
# PROD-FAITHFUL DESIGN (post-G1/G2): prod `generate_comparison` is unified onto
# `build_verdict_prompt`, which injects the I2 exemplar block from
# data/verdict_exemplars.json UNCONDITIONALLY. So the honest A/B is NOT "append
# a block" — it is "swap the exemplar FILE the prod prompt reads":
#   - arm_baseline_4o  -> reads the on-disk file (main's APs-only G2 skeleton)
#   - arm_prompt_exemplars -> temporarily points the loader at I1's FILLED file
#     (APs + exemplars, the G3 state), resets the lru_cache, builds the prod
#     prompt, restores. Winner-axis delta is attributable to the exemplar
#     content alone, byte-faithful to what prod will do before vs after G3.
# Point SHADOW_EXEMPLAR_FILE at I1's data/verdict_exemplars.json (from their
# branch/worktree). SHADOW_EXEMPLAR_OFF forces the baseline file (pure control).

import contextlib


@contextlib.contextmanager
def _swapped_exemplar_file(path: Optional[str]):
    """Temporarily point the verdict_exemplar_loader at `path` (I1's filled
    exemplar JSON) + reset its lru_cache, restoring both on exit. No-op when
    path is None/SHADOW_EXEMPLAR_OFF — the arm then reads the on-disk file."""
    if not path or os.getenv("SHADOW_EXEMPLAR_OFF"):
        yield
        return
    from app.services import verdict_exemplar_loader as vel
    from pathlib import Path as _P

    original = vel._EXEMPLAR_FILE
    try:
        vel._EXEMPLAR_FILE = _P(path)
        vel.reset_cache()
        yield
    finally:
        vel._EXEMPLAR_FILE = original
        vel.reset_cache()


async def _prompt_exemplars_call(vi: VerdictInput, client, *, temperature: float) -> ArmCallResult:
    """Shared body for the prompt-arm at a given temperature: build the prod
    verdict prompt with I1's exemplar file swapped in (SHADOW_EXEMPLAR_FILE),
    call gpt-4o at `temperature`. The exemplar content is the ONLY variable vs
    the baseline at the same temperature."""
    exemplar_file = os.getenv("SHADOW_EXEMPLAR_FILE")
    with _swapped_exemplar_file(exemplar_file):
        system_msg = _build_verdict_system_prompt(vi)
    user_msg = _build_verdict_user_msg(vi)
    try:
        verdict, pt, ct, rm = await _chat_json(client, "gpt-4o", system_msg, user_msg,
                                               temperature=temperature)
        return ArmCallResult(verdict, pt, ct, "gpt-4o", response_model=rm)
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "gpt-4o", error=f"{type(exc).__name__}:{exc}")


async def arm_prompt_exemplars(vi: VerdictInput, client) -> ArmCallResult:
    """Directive 2 — gpt-4o verdict (T=0.2) with I1's exemplar file injected via
    the REAL prod `build_verdict_prompt` path. Pair with arm_baseline_4o (same
    T=0.2, on-disk APs-only file) so the winner-axis delta is attributable to
    the exemplar CONTENT alone."""
    return await _prompt_exemplars_call(vi, client, temperature=0.2)


async def arm_prompt_exemplars_t0(vi: VerdictInput, client) -> ArmCallResult:
    """G3 PRE-READ arm (dispatcher prod-parity requirement): the prompt-arm at
    temperature=0. T=0 is LIVE in prod since G2, so the G3 quality gate must
    isolate the EXEMPLAR content under the SHIPPED temperature — not T=0.2.
    Pair with `temp0` (baseline at T=0, on-disk APs-only file); the winner-axis
    delta between them, split structural-24/variance-19, IS the G3 gate.
    SHADOW_EXEMPLAR_FILE must point at I1's FIXED exemplar JSON (NOT a stale
    tip — their B4/B5/B6 fixes change content G3 will ship)."""
    return await _prompt_exemplars_call(vi, client, temperature=0.0)


# --- Multi-agent arm (I4.3): 3 mini analysts + 4o editor --------------------

_ANALYST_PROMPTS = {
    "spec": "You are a SPECIFICATIONS analyst. Given two products, write 2-3 "
            "terse factual sentences comparing ONLY their specs/performance for "
            "a Bahrain buyer. Cite concrete numbers. No verdict, no price talk.",
    "price": "You are a PRICE/VALUE analyst. Given two products with Bahrain "
             "prices, write 2-3 terse sentences on value-per-dinar. State which "
             "is cheaper and whether the premium (if any) is justified. No final verdict.",
    "review": "You are a REVIEW-CONSENSUS analyst. Given two products' review "
              "summaries, write 2-3 terse sentences on what real owners say. "
              "Note durability/satisfaction signals. No verdict.",
}


async def _run_analyst(client, role: str, vi: VerdictInput) -> Tuple[str, int, int, str]:
    """One gpt-4o-mini analyst pass. Returns (text, prompt_tok, completion_tok,
    served_model)."""
    user_msg = _build_verdict_user_msg(vi)
    resp = await _create_with_retry(
        client,
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _ANALYST_PROMPTS[role]},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=200,
        temperature=0.2,
    )
    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", 0) if usage else 0
    ct = getattr(usage, "completion_tokens", 0) if usage else 0
    return (resp.choices[0].message.content or ""), pt, ct, (getattr(resp, "model", "") or "")


async def arm_multiagent(vi: VerdictInput, client) -> ArmCallResult:
    """I4.3 — 3x gpt-4o-mini analysts (spec/price/review) run in parallel, then
    a gpt-4o editor synthesizes the final verdict JSON from their notes + the
    scores. Promotion bar: >=5% lift vs arm_baseline_4o. Envelope rule: this
    (+~$0.005) and self-critique cannot BOTH promote inside $0.015."""
    try:
        analyst_results = await asyncio.gather(
            _run_analyst(client, "spec", vi),
            _run_analyst(client, "price", vi),
            _run_analyst(client, "review", vi),
        )
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, 0, 0, "multiagent", error=f"analyst:{type(exc).__name__}:{exc}")

    analyst_notes = {
        "spec_analysis": analyst_results[0][0],
        "price_analysis": analyst_results[1][0],
        "review_analysis": analyst_results[2][0],
    }
    analyst_pt = sum(r[1] for r in analyst_results)
    analyst_ct = sum(r[2] for r in analyst_results)
    analyst_models = {r[3] for r in analyst_results if r[3]}

    editor_system = _build_verdict_system_prompt(vi) + """

## Analyst Notes
You are the EDITOR. Three specialist analysts have reviewed these products.
Synthesize their notes (below) + the scoring context into the final verdict
JSON. Weigh value-per-dinar and Bahrain-market reality, not just the spec sheet.
"""
    editor_user = f"""<ANALYST_NOTES>
{json.dumps(analyst_notes, indent=2)}
</ANALYST_NOTES>

{_build_verdict_user_msg(vi)}"""
    try:
        verdict, ed_pt, ed_ct, ed_model = await _chat_json(client, "gpt-4o",
                                                            editor_system, editor_user)
    except Exception as exc:  # noqa: BLE001
        return ArmCallResult({}, analyst_pt, analyst_ct, "multiagent",
                             error=f"editor:{type(exc).__name__}:{exc}")

    # Cost is the SUM across all 4 calls; we report it as a blended multiagent
    # cost by pricing each leg at its own model rate (done in run_arm via the
    # per-leg token split). Here we return aggregate tokens tagged "multiagent"
    # and stash the split for accurate pricing.
    total_pt = analyst_pt + ed_pt
    total_ct = analyst_ct + ed_ct
    # response_model records the served models across legs (editor 4o + analysts'
    # mini) so the multiagent arm proves its legs ran on the requested models too.
    served = {ed_model} | {m for m in analyst_models if m}
    result = ArmCallResult(verdict, total_pt, total_ct, "multiagent",
                           response_model=",".join(sorted(served)))
    # Attach the per-model token split for precise blended pricing.
    result.verdict.setdefault("_shadow_cost_split", {
        "gpt-4o-mini": {"pt": analyst_pt, "ct": analyst_ct},
        "gpt-4o": {"pt": ed_pt, "ct": ed_ct},
    })
    return result


ARMS: Dict[str, Callable] = {
    "baseline_4o": arm_baseline_4o,
    "o3_mini": arm_o3_mini,
    "reviews_trim": arm_reviews_trim,
    "multiagent": arm_multiagent,
    # Variance-reduction arms (dispatcher orders, driven by the agreement
    # finding): T=0 greedy decode + best-of-3 majority vote. temp0 doubles as
    # the BASELINE side of the G3 pre-read (baseline@T=0, on-disk APs-only file).
    "temp0": arm_temp0,
    "best_of_3": arm_best_of_3,
    # Directive-2 prompt-arm: T=0.2 (prompt_exemplars) + the G3 PRE-READ T=0
    # variant (prompt_exemplars_t0 — prod parity, paired with temp0).
    "prompt_exemplars": arm_prompt_exemplars,
    "prompt_exemplars_t0": arm_prompt_exemplars_t0,
}


def _arm_call_cost(res: ArmCallResult) -> float:
    """Dollar cost of an arm call. Multiagent prices each leg at its own model
    rate via the _shadow_cost_split stashed in the verdict; single-model arms
    price the metered tokens at the arm's model rate."""
    split = res.verdict.get("_shadow_cost_split") if isinstance(res.verdict, dict) else None
    if split:
        total = 0.0
        for model, tok in split.items():
            total += call_cost_usd(model, tok.get("pt", 0), tok.get("ct", 0))
        return total
    return call_cost_usd(res.model, res.prompt_tokens, res.completion_tokens)


async def run_arm(arm_name: str, inputs: List[VerdictInput], *,
                  weights: Dict[str, float], concurrency: int = 4,
                  client=None) -> ArmReport:
    """Run one arm over the reconstructed inputs and grade each result.

    concurrency bounds parallel OpenAI calls. The eval-runner gold grader is
    single-source — winner+factual re-graded, price+specs inherited."""
    arm_fn = ARMS[arm_name]
    own_client = client is None
    if own_client:
        from app.services.extraction_service import get_client
        client = get_client()

    semaphore = asyncio.Semaphore(concurrency)

    async def _one(vi: VerdictInput) -> ArmGrade:
        async with semaphore:
            start = time.monotonic()
            res = await arm_fn(vi, client)
            verdict_ms = int((time.monotonic() - start) * 1000)
        cost = _arm_call_cost(res) if res.error is None else 0.0
        # Strip the cost-split helper before grading so it never leaks into prose.
        if isinstance(res.verdict, dict):
            res.verdict.pop("_shadow_cost_split", None)
        return grade_arm_verdict(
            vi, res.verdict, verdict_ms=verdict_ms, cost_usd=cost,
            weights=weights, error=res.error, response_model=res.response_model,
        )

    grades = await asyncio.gather(*[_one(vi) for vi in inputs])
    return aggregate_arm(arm_name, list(grades))


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_arm_report(report: ArmReport, *, baseline: Optional[ArmReport] = None) -> str:
    """Human-readable per-arm block for the console + evidence doc."""
    lines = [
        f"## arm: {report.arm}",
        f"covered={report.n_covered}  passing={report.n_passing} "
        f"({report.pass_rate:.1%})  errors={report.n_errors}",
        f"winner: baseline_rate={report.baseline_winner_rate:.3f} -> "
        f"arm_rate={report.arm_winner_rate:.3f}  "
        f"flips +{report.winner_flips_to_correct}/-{report.winner_flips_to_wrong} "
        f"(net {report.net_winner_flips:+d})",
        f"axes: price={report.axis_avg_price:.3f} specs={report.axis_avg_specs:.3f} "
        f"winner={report.axis_avg_winner:.3f} factual={report.axis_avg_factual:.3f}",
        f"cost: mean=${report.mean_cost_usd:.5f}/call total=${report.total_cost_usd:.4f}",
        f"latency(verdict-call): mean={report.mean_verdict_ms:.0f}ms "
        f"p50={report.p50_verdict_ms}ms p95={report.p95_verdict_ms}ms",
    ]
    if baseline is not None and report.arm != baseline.arm:
        d_winner = report.axis_avg_winner - baseline.axis_avg_winner
        d_factual = report.axis_avg_factual - baseline.axis_avg_factual
        d_cost = report.mean_cost_usd - baseline.mean_cost_usd
        d_ms = report.mean_verdict_ms - baseline.mean_verdict_ms
        lines.append(
            f"vs {baseline.arm}: winner {d_winner:+.3f}  factual {d_factual:+.3f}  "
            f"cost {d_cost:+.5f}/call  latency {d_ms:+.0f}ms"
        )
    return "\n".join(lines)


def write_evidence_report(reports: Dict[str, ArmReport], path: Path | str, *,
                          baseline_arm: str = "baseline_4o",
                          coverage_note: str = "") -> None:
    """Write the I4.5 per-arm evidence markdown (feeds the G5 promotion review).

    Promotion bars (from the plan §4):
      - o3_mini: quality-up AND cost-neutral-or-better vs baseline_4o
      - multiagent: >=5% winner lift vs baseline_4o
      - reviews_trim: adopt only if winner/factual hold AND latency improves
    """
    path = Path(path)
    base = reports.get(baseline_arm)
    lines: List[str] = [
        "# Bundle B S2 — Lane I4 Shadow Experiment Results",
        "",
        f"> Generated by `scripts/shadow_experiments.py`. Grading via the "
        f"eval_runner gold graders (winner + factual re-graded from each arm's "
        f"verdict; price + specs inherited from the S1 baseline grade — a "
        f"verdict swap cannot move the extraction-set axes). Baseline anchor: "
        f"eval_runs `4aee8e88` (21.0% weighted).",
        "",
        "## Coverage",
        coverage_note or "_(coverage note not supplied)_",
        "",
        "## Summary table",
        "",
        "| arm | covered | winner rate | net flips | factual | mean $/call | mean verdict ms | promotion bar |",
        "|---|---|---|---|---|---|---|---|",
    ]
    _bars = {
        "baseline_4o": "control (gpt-4o, prod model)",
        "o3_mini": "quality-up AND cost <=baseline",
        "multiagent": ">=5% winner lift",
        "reviews_trim": "winner+factual hold AND latency down",
    }
    for arm_name, r in reports.items():
        lines.append(
            f"| {arm_name} | {r.n_covered} | {r.arm_winner_rate:.3f} | "
            f"{r.net_winner_flips:+d} | {r.axis_avg_factual:.3f} | "
            f"${r.mean_cost_usd:.5f} | {r.mean_verdict_ms:.0f} | {_bars.get(arm_name, '')} |"
        )
    lines.append("")
    for arm_name, r in reports.items():
        lines.append(format_arm_report(r, baseline=base))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_ids(gold: Dict[str, Any], baseline: Dict[str, Dict[str, Any]],
                 subset: str) -> List[str]:
    if subset == "bias45":
        return select_bias45(baseline)
    if subset == "graded200":
        return select_graded200(baseline)
    if subset == "smoke20":
        sub_path = REPO_ROOT / "data" / "eval_smoke_subset.json"
        ids = set(json.loads(sub_path.read_text(encoding="utf-8")).get("ids") or [])
        # only the http-200 smoke ids are reconstructable
        return [i for i in ids if baseline.get(i, {}).get("error") is None]
    raise ValueError(f"unknown subset {subset!r}")


def _ensure_env() -> None:
    """Load the worktree .env with override=True so its keys win over any stale
    shell-inherited values (the worktree was found 2 rotations stale before).
    Idempotent + safe to call before any live DB / OpenAI access."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:  # noqa: BLE001 — dotenv optional in some envs
        pass


def _cmd_prepare(args) -> int:
    _ensure_env()
    gold = load_gold_truth(args.gold)
    baseline = load_baseline_grades(args.baseline)
    ids = _resolve_ids(gold, baseline, args.subset)
    print(f"# prepare: subset={args.subset} candidate_ids={len(ids)} (offline, no Serper/OpenAI)")
    inputs, skipped = build_verdict_inputs(gold, baseline, ids)
    write_verdict_inputs(inputs, args.out)
    print(f"# reconstructed {len(inputs)} verdict inputs -> {args.out}")
    if skipped:
        print(f"# skipped {len(skipped)}:")
        by_reason: Dict[str, int] = {}
        for s in skipped:
            key = s["reason"].split(":")[0]
            by_reason[key] = by_reason.get(key, 0) + 1
        for reason, n in sorted(by_reason.items(), key=lambda kv: -kv[1]):
            print(f"#   {reason}: {n}")
        if args.skipped_out:
            Path(args.skipped_out).write_text(
                "\n".join(json.dumps(s, ensure_ascii=False) for s in skipped),
                encoding="utf-8",
            )
            print(f"# skipped detail -> {args.skipped_out}")
    return 0


def _cmd_dump(args) -> int:
    """Export all fresh L2 rows to a jsonl (one product per line, specs+reviews
    +bahrain-price joined). Reusable as SHADOW_L2_DUMP so later prepare runs
    need no DB access. DB read only — zero Serper, zero OpenAI."""
    _ensure_env()
    # Force the live path (ignore any SHADOW_L2_DUMP already set).
    prior = os.environ.pop("SHADOW_L2_DUMP", None)
    try:
        by_cat = _load_all_l2_rows()
    finally:
        if prior is not None:
            os.environ["SHADOW_L2_DUMP"] = prior
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for cat, rows in sorted(by_cat.items()):
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
    print(f"# dumped {n} L2 products across {len(by_cat)} categories -> {out_path}")
    return 0


# Expected served model id for the o3-mini arm (OpenAI's dated snapshot). The
# request param "o3-mini" routes to this; the verify command asserts the
# RESPONSE carries it (not a silent fallback to a 4o snapshot).
_EXPECTED_O3_MINI_SERVED = "o3-mini-2025-01-31"


def _cmd_verify(args) -> int:
    """LIVE model-routing verification (dispatcher G5-hygiene requirement).
    Makes N (default 3) real o3-mini chat calls and asserts each RESPONSE's
    `model` field == the expected served id (o3-mini-2025-01-31) — not just the
    request param. Prints each response's served model + token usage so the
    OpenAI dashboard movement can be cross-checked. Exit 0 = all served as
    o3-mini; exit 1 = at least one call did NOT (silent fallback / wrong model);
    exit 3 = the calls errored (e.g. quota)."""
    _ensure_env()
    from app.services.extraction_service import get_client

    model = args.model
    expected = args.expected or (_EXPECTED_O3_MINI_SERVED if model == "o3-mini" else None)
    n = args.n
    print(f"# VERIFY: {n} LIVE {model} calls — asserting resp.model"
          + (f" == {expected!r}" if expected else " (recording only)"))

    async def _probe(i: int) -> Dict[str, Any]:
        client = get_client()
        try:
            _verdict, pt, ct, served = await _chat_json(
                client, model,
                "You are a terse assistant. Reply with a JSON object.",
                'Return {"ok": true} and nothing else.',
                max_tokens=200,
            )
            return {"i": i, "served_model": served, "prompt_tokens": pt,
                    "completion_tokens": ct, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"i": i, "served_model": "", "prompt_tokens": 0,
                    "completion_tokens": 0, "error": f"{type(exc).__name__}:{exc}"}

    async def _run_all():
        return await asyncio.gather(*[_probe(i) for i in range(n)])

    results = asyncio.run(_run_all())

    any_error = False
    mismatch = False
    for r in results:
        if r["error"]:
            any_error = True
            print(f"  call {r['i']}: ERROR {r['error'][:120]}")
            continue
        ok = (expected is None) or (r["served_model"] == expected)
        flag = "OK" if ok else "MISMATCH"
        if not ok:
            mismatch = True
        print(f"  call {r['i']}: served_model={r['served_model']!r} "
              f"tokens={r['prompt_tokens']}+{r['completion_tokens']} [{flag}]")

    if args.out:
        Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"# verify result -> {args.out}")

    if any_error:
        print("# RESULT: calls ERRORED (e.g. insufficient_quota) — cannot verify; "
              "re-run when quota restored")
        return 3
    if mismatch:
        print(f"# RESULT: at least one call did NOT serve {expected!r} — the "
              f"arm's model attribution is WRONG; re-measure in the unified pass")
        return 1
    print(f"# RESULT: all {n} calls served the expected model — attribution VERIFIED")
    return 0


def _cmd_run(args) -> int:
    _ensure_env()
    gold = load_gold_truth(args.gold)
    weights = load_axis_weights(gold)
    inputs = read_verdict_inputs(args.inputs)
    if args.limit:
        inputs = inputs[: args.limit]
    if not inputs:
        print("ERROR: no inputs (run `prepare` first)", file=sys.stderr)
        return 3
    arm = args.arm
    if arm not in ARMS:
        print(f"ERROR: unknown arm {arm!r} (have {sorted(ARMS)})", file=sys.stderr)
        return 3
    print(f"# run arm={arm} n_inputs={len(inputs)} concurrency={args.concurrency} "
          f"— LIVE OpenAI calls, metered cost")
    report = asyncio.run(run_arm(arm, inputs, weights=weights, concurrency=args.concurrency))
    print(format_arm_report(report))

    # Structural-vs-variance split (dispatcher requirement for the variance arms).
    split = split_winner_rate(report.per_query)
    print("split (winner rate by agreement bucket):")
    for bucket in ("structural", "variance", "split", "other"):
        b = split.get(bucket)
        if b and b["n"]:
            print(f"  {bucket:<11} {b['winner_correct']}/{b['n']} = {b['winner_rate']:.3f}")

    # SERVED-model tripwire: surface the distinct resp.model values across the
    # run so a silent fallback (e.g. o3-mini arm actually served gpt-4o) is
    # visible in the run output itself, not just the per-query JSON. Empty when
    # all rows errored (no response).
    served = {}
    for g in report.per_query:
        if g.response_model:
            served[g.response_model] = served.get(g.response_model, 0) + 1
    if served:
        print("served models (resp.model — evidence the arm ran where it claimed):")
        for model, n in sorted(served.items(), key=lambda kv: -kv[1]):
            print(f"  {model}: {n}")
    else:
        print("served models: NONE captured (all rows errored or no response.model)")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "arm": report.arm,
                "n_covered": report.n_covered,
                "summary": {k: getattr(report, k) for k in (
                    "arm_winner_rate", "baseline_winner_rate", "net_winner_flips",
                    "winner_flips_to_correct", "winner_flips_to_wrong",
                    "axis_avg_factual", "mean_cost_usd", "total_cost_usd",
                    "mean_verdict_ms", "p50_verdict_ms", "p95_verdict_ms", "n_errors",
                )},
                "split_by_agreement_bucket": split,
                "per_query": [dataclasses.asdict(g) for g in report.per_query],
            }, ensure_ascii=False, indent=2))
        print(f"# arm result -> {args.out}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", default=str(DEFAULT_GOLD))
    parser.add_argument("--baseline", default=str(BASELINE_GRADES),
                        help="S1 per-query graded jsonl (default points at the "
                             "main repo's .qa-bias-rerun copy)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="reconstruct verdict inputs from L2 (offline)")
    p_prep.add_argument("--subset", choices=["bias45", "graded200", "smoke20"],
                        default="bias45")
    p_prep.add_argument("--out", default=".shadow/inputs.jsonl")
    p_prep.add_argument("--skipped-out", default=None)
    p_prep.set_defaults(func=_cmd_prepare)

    p_dump = sub.add_parser("dump", help="export all fresh L2 rows to a jsonl "
                            "(SHADOW_L2_DUMP input — sandbox-safe reuse)")
    p_dump.add_argument("--out", default=".shadow/l2_dump.jsonl")
    p_dump.set_defaults(func=_cmd_dump)

    p_verify = sub.add_parser("verify", help="LIVE model-routing verification: "
                              "assert resp.model == expected served id (G5 hygiene)")
    p_verify.add_argument("--model", default="o3-mini", help="request model to verify")
    p_verify.add_argument("--expected", default=None,
                          help="expected served resp.model (default: o3-mini-2025-01-31 for o3-mini)")
    p_verify.add_argument("--n", type=int, default=3, help="number of live calls")
    p_verify.add_argument("--out", default=None, help="write per-call JSON")
    p_verify.set_defaults(func=_cmd_verify)

    p_run = sub.add_parser("run", help="run one verdict arm over cached inputs (LIVE OpenAI)")
    p_run.add_argument("--arm", required=True, choices=sorted(ARMS))
    p_run.add_argument("--inputs", default=".shadow/inputs.jsonl")
    # default 2: the org's gpt-4o TPM cap trips 429s above this on ~3k-tok
    # verdict calls. _create_with_retry backs off, but lower concurrency keeps
    # the run smooth. Measurement runs can use 1 for full determinism.
    p_run.add_argument("--concurrency", type=int, default=2)
    p_run.add_argument("--limit", type=int, default=0, help="cap inputs (smoke test)")
    p_run.add_argument("--out", default=None, help="write per-query arm result JSON")
    p_run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
