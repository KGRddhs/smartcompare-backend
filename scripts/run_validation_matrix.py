#!/usr/bin/env python3
"""50-query Bahrain validation matrix runner (Sprint A merge gate).

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.3
Design: docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 8
Doc:   docs/plans/2026-06-08-A-validation-matrix-50q.md
Gold:  data/validation_gold_truth.json

Hits the deployed Railway endpoint once per query (?nocache=true), scores
each query along 4 axes, prints per-query JSON lines + aggregate pass-rate.

Exit codes:
    0 — pass-rate >= 0.80 (Sprint A merge gate met)
    2 — pass-rate < 0.80
    3 — runtime / network / parse failure preventing the run from completing
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_PREVIEW_URL = "https://web-production-58776.up.railway.app"  # Railway preview
DEFAULT_PROD_URL = "https://web-production-58776.up.railway.app"     # Same endpoint pre-blue-green
DEFAULT_GOLD = Path(__file__).resolve().parent.parent / "data" / "validation_gold_truth.json"
DEFAULT_TIMEOUT_S = 35.0


# ---------------------------------------------------------------------------
# Axis scorers
# ---------------------------------------------------------------------------

def _price_within_tolerance(returned: Optional[float], expected_min: float, expected_max: float, tolerance_pct: float) -> bool:
    """Accept if returned is inside [min, max] OR within ±tolerance of the
    midpoint. The midpoint test catches cases where the gold range is
    narrow and the API returns a value just outside it."""
    if returned is None:
        return False
    if expected_min <= returned <= expected_max:
        return True
    midpoint = (expected_min + expected_max) / 2.0
    if midpoint <= 0:
        return False
    deviation = abs(returned - midpoint) / midpoint
    return deviation <= (tolerance_pct / 100.0)


def score_price(response: Dict[str, Any], expected: Dict[str, Any], tolerance_pct: float) -> float:
    """Both products must satisfy the price tolerance — score is 1.0 if
    both match, 0.5 if only one, 0.0 if neither (or data missing)."""
    products = response.get("products") or response.get("overview", {}).get("products") or []
    if len(products) < 2:
        return 0.0
    hits = 0
    for idx in (0, 1):
        key = f"product_{idx}"
        gold = expected.get(key) or {}
        if not gold:
            hits += 1  # un-authored gold = neutral / no-op
            continue
        amount = None
        try:
            amount = float((products[idx].get("price") or {}).get("amount") or 0)
        except (TypeError, ValueError):
            amount = None
        if _price_within_tolerance(amount, gold["min"], gold["max"], tolerance_pct):
            hits += 1
    return hits / 2.0


def score_specs(response: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """For each product, fraction of authored spec keys whose returned
    value (case-insensitive contains) matches the gold value. Score is
    the average across both products."""
    products = response.get("products") or response.get("overview", {}).get("products") or []
    if len(products) < 2:
        return 0.0
    per_product_scores: List[float] = []
    for idx in (0, 1):
        gold = expected.get(f"product_{idx}") or {}
        if not gold:
            per_product_scores.append(1.0)  # un-authored → not penalised
            continue
        returned_specs = (products[idx].get("specs") or {})
        matched = 0
        for key, gold_value in gold.items():
            returned_value = returned_specs.get(key)
            if returned_value is None:
                continue
            if str(gold_value).lower() in str(returned_value).lower():
                matched += 1
        per_product_scores.append(matched / max(len(gold), 1))
    return sum(per_product_scores) / max(len(per_product_scores), 1)


def score_winner(response: Dict[str, Any], expected_index: Optional[int]) -> float:
    if expected_index is None:
        return 1.0
    overview = response.get("overview") or {}
    winner = overview.get("winner") or {}
    returned_idx = winner.get("product_index")
    if returned_idx is None:
        # Legacy alias
        returned_idx = response.get("winner_index")
    if returned_idx is None:
        return 0.0
    return 1.0 if returned_idx == expected_index else 0.0


def _collect_verdict_text(response: Dict[str, Any]) -> str:
    overview = response.get("overview") or {}
    fields = [
        (overview.get("verdict") or {}).get("winner_reason", ""),
        (overview.get("verdict") or {}).get("key_tradeoff", ""),
        (overview.get("verdict") or {}).get("value_context", ""),
        (overview.get("verdict") or {}).get("winner_declaration", ""),
        (response.get("comparison") or {}).get("winner_declaration", ""),
        (response.get("comparison") or {}).get("recommendation", ""),
    ]
    # Per-product best_for entries
    for p in (overview.get("products") or response.get("products") or []):
        v = p.get("best_for") or ""
        fields.append(v if isinstance(v, str) else "")
    return "\n".join(s for s in fields if isinstance(s, str))


def score_factual(response: Dict[str, Any], forbidden_facts: List[str]) -> float:
    if not forbidden_facts:
        return 1.0
    text = _collect_verdict_text(response).lower()
    if not text:
        return 1.0
    hits = sum(1 for f in forbidden_facts if f.lower() in text)
    fail_share = hits / len(forbidden_facts)
    # ANY hit drops the score significantly; total miss = 1.0
    return max(0.0, 1.0 - fail_share)


# ---------------------------------------------------------------------------
# Per-query runner
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class QueryResult:
    id: str
    query: str
    category: str
    wall_s: float
    http_status: int
    error: Optional[str]
    price_score: float
    specs_score: float
    winner_score: float
    factual_score: float
    weighted_score: float
    passing: bool
    wall_over_cap: bool


def _weighted(price: float, specs: float, winner: float, factual: float, weights: Dict[str, float]) -> float:
    return (
        price * weights["price_accuracy"]
        + specs * weights["specs_correctness"]
        + winner * weights["winner_correctness"]
        + factual * weights["factual_claim_integrity"]
    )


def run_query(base_url: str, query_record: Dict[str, Any], weights: Dict[str, float], tolerance_pct: float, timeout_s: float) -> QueryResult:
    url = f"{base_url}/api/v1/text/compare"
    params = {"q": query_record["query"], "region": query_record["region"], "nocache": "true"}
    start = time.time()
    http_status = 0
    error: Optional[str] = None
    response_json: Dict[str, Any] = {}
    try:
        resp = requests.get(url, params=params, timeout=timeout_s)
        http_status = resp.status_code
        if resp.status_code == 200:
            response_json = resp.json()
        else:
            error = f"http_{resp.status_code}"
    except requests.RequestException as exc:
        error = f"network:{type(exc).__name__}"
    except json.JSONDecodeError as exc:
        error = f"json_decode:{exc}"
    wall_s = time.time() - start

    # Some response shapes nest data under .data — unwrap once if present.
    body = response_json.get("data") if isinstance(response_json.get("data"), dict) and "products" in response_json["data"] else response_json
    if not isinstance(body, dict):
        body = response_json

    price = score_price(body, query_record.get("expected_prices") or {}, tolerance_pct)
    specs = score_specs(body, query_record.get("expected_specs") or {})
    winner = score_winner(body, query_record.get("expected_winner_index"))
    factual = score_factual(body, query_record.get("forbidden_facts") or [])
    weighted = _weighted(price, specs, winner, factual, weights)
    return QueryResult(
        id=query_record["id"],
        query=query_record["query"],
        category=query_record["category"],
        wall_s=round(wall_s, 2),
        http_status=http_status,
        error=error,
        price_score=round(price, 3),
        specs_score=round(specs, 3),
        winner_score=round(winner, 3),
        factual_score=round(factual, 3),
        weighted_score=round(weighted, 3),
        passing=weighted >= 0.80 and error is None,
        wall_over_cap=wall_s > query_record.get("max_wall_seconds", 25.0),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=["preview", "production"], default="preview")
    parser.add_argument("--base-url", default=None, help="Override env URL")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD), help="gold-truth JSON path")
    parser.add_argument("--limit", type=int, default=None, help="Run only first N queries (smoke test)")
    parser.add_argument("--category", default=None, help="Filter to a single category")
    parser.add_argument("--out", default=None, help="Write per-query JSON lines to PATH (default: stdout)")
    parser.add_argument("--gate", type=float, default=0.80, help="Aggregate pass-rate gate (default 0.80)")
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    base_url = args.base_url or (DEFAULT_PROD_URL if args.env == "production" else DEFAULT_PREVIEW_URL)
    gold_path = Path(args.gold)
    if not gold_path.exists():
        print(f"ERROR: gold file missing: {gold_path}", file=sys.stderr)
        return 3
    try:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: gold file parse failed: {exc}", file=sys.stderr)
        return 3

    meta = gold.get("_metadata") or {}
    weights = meta.get("axis_weights") or {
        "price_accuracy": 0.25,
        "specs_correctness": 0.25,
        "winner_correctness": 0.30,
        "factual_claim_integrity": 0.20,
    }
    tolerance_pct = meta.get("price_tolerance_pct", 15.0)
    queries = gold.get("queries") or []
    if args.category:
        queries = [q for q in queries if q["category"] == args.category]
    if args.limit:
        queries = queries[: args.limit]

    if not queries:
        print("ERROR: no queries selected", file=sys.stderr)
        return 3

    out_fh = open(args.out, "w", encoding="utf-8") if args.out else None

    results: List[QueryResult] = []
    started_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not args.quiet:
        print(f"# matrix run: env={args.env} base={base_url} n={len(queries)} gate={args.gate} started={started_at}")

    for i, q in enumerate(queries, start=1):
        r = run_query(base_url, q, weights, tolerance_pct, args.timeout_s)
        results.append(r)
        line = json.dumps(dataclasses.asdict(r), ensure_ascii=False)
        if out_fh:
            out_fh.write(line + "\n")
        if not args.quiet:
            tag = "PASS" if r.passing else "FAIL"
            print(f"  [{i:>2}/{len(queries)}] {tag} {r.id} {r.weighted_score:.2f} wall={r.wall_s:.1f}s err={r.error or ''}")

    if out_fh:
        out_fh.close()

    pass_n = sum(1 for r in results if r.passing)
    pass_rate = pass_n / len(results)
    avg_wall = sum(r.wall_s for r in results) / max(len(results), 1)
    over_cap = sum(1 for r in results if r.wall_over_cap)

    print()
    print("=" * 60)
    print(f"Aggregate pass-rate: {pass_rate:.1%} ({pass_n}/{len(results)})")
    print(f"Avg wall-time: {avg_wall:.1f}s  Over-cap: {over_cap}/{len(results)}")
    print(f"Gate: {args.gate:.0%}  Result: {'PASS' if pass_rate >= args.gate else 'FAIL'}")
    print("=" * 60)
    return 0 if pass_rate >= args.gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
