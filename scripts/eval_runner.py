#!/usr/bin/env python3
"""Bundle B Phase B.6 - async eval-loop runner + grader.

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4
Gold: data/validation_gold_truth.json
DB:   migrations/031_eval_runs.sql (one eval_runs row per run)

This is the measurement backbone every later Bundle B phase gates on. It
hits the deployed comparison endpoint once per gold-truth query
(?nocache=true), records the response + wall time, grades along 4 axes
(price / specs / winner / factual), and aggregates a weighted pass-rate +
per-axis averages + p50/p95 wall-time.

Relationship to scripts/run_validation_matrix.py (Sprint A merge-gate
script): that earlier script is a synchronous `requests`-based one-shot
that reads the *prose* winner (overview.winner.product_index) and uses
fractional axis scores. THIS runner is the Bundle B observability backbone:
async httpx with a concurrency cap, boolean axis grading per the F4.2
contract, reads the *deterministic* winner (scoring_v2.overall_score.
winner_idx), persists to eval_runs, and supports regression/absolute gate
modes + a smoke20 subset. New code targets this module.

COST GUARD: a full cold-cache run of all 50/200 queries burns ~600-1,000
Serper credits. NEVER run the full set against prod without explicit
dispatcher GO. All tests mock the httpx transport. The CLI defaults to the
smoke20 subset and refuses the full set unless --allow-full is passed.

Usage (mocked in tests; live runs are dispatcher-gated):
    TARGET_BASE_URL=https://web-production-58776.up.railway.app \\
        python -m scripts.eval_runner --subset smoke20 --mode absolute --threshold 0.95
    python -m scripts.eval_runner --mode regression --baseline-run-id <uuid>

Exit codes:
    0 - gate satisfied
    1 - gate failed (pass-rate / axis regression below threshold)
    3 - runtime / network / config error preventing the run
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import logging
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLD = REPO_ROOT / "data" / "validation_gold_truth.json"
DEFAULT_SMOKE_SUBSET = REPO_ROOT / "data" / "eval_smoke_subset.json"
DEFAULT_PROD_URL = "https://web-production-58776.up.railway.app"

# Axis weights for the per-query weighted-pass score AND the run-level
# aggregate. The CANONICAL source is the gold file's _metadata.axis_weights
# (loaded via load_axis_weights), so every run pins the weights it used via
# the gold_truth_version git SHA - one source of truth, no docs-vs-reality
# drift. This module constant is the FALLBACK only, used when metadata is
# absent/malformed; it mirrors the gold file's current values in short-key
# form. The gold file stores LONG axis names (price_accuracy, ...), mapped
# to these short names by _AXIS_LONG_TO_SHORT. Must sum to 1.0.
AXIS_WEIGHTS: Dict[str, float] = {
    "price": 0.25,
    "specs": 0.25,
    "winner": 0.30,
    "factual": 0.20,
}

# Gold-file _metadata.axis_weights long key -> short axis name used in code.
_AXIS_LONG_TO_SHORT: Dict[str, str] = {
    "price_accuracy": "price",
    "specs_correctness": "specs",
    "winner_correctness": "winner",
    "factual_claim_integrity": "factual",
}

# The exact 4 short axis names every weights dict must carry (after mapping).
_AXIS_NAMES = frozenset({"price", "specs", "winner", "factual"})

# A query passes when its weighted axis score clears this floor.
QUERY_PASS_THRESHOLD = 0.80

# Price band tolerance (F4.2): accept when within [min*0.85, max*1.15].
PRICE_LOWER_FACTOR = 0.85
PRICE_UPPER_FACTOR = 1.15

# Default async concurrency (dispatcher brief: 3).
DEFAULT_CONCURRENCY = 3

# Per-query timeout = max_wall_seconds + this slack.
TIMEOUT_SLACK_SECONDS = 10.0

# STREAM_HARD_CAP_SECONDS in prod (CLAUDE.md, B0-C Item 3). p95 wall is
# checked against this in the report.
STREAM_HARD_CAP_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Gold-truth loading
# ---------------------------------------------------------------------------

def load_gold_truth(path: Path | str = DEFAULT_GOLD) -> Dict[str, Any]:
    """Load + parse the gold-truth JSON. Raises FileNotFoundError if absent."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"gold-truth file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def gold_truth_version(gold_path: Path | str = DEFAULT_GOLD) -> str:
    """Git SHA of the gold-truth file content (team-lead Q3 decision).

    `git rev-parse HEAD:<relpath>` resolves the blob SHA of the file as of
    HEAD  -  pins the exact gold content without a content hash. Falls back to
    'unknown' when not in a git tree (e.g. a tarball deploy)."""
    gold_path = Path(gold_path)
    try:
        rel = gold_path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        rel = gold_path
    try:
        # encoding='utf-8' is explicit: text=True alone decodes via the
        # platform default (cp1252 on Windows), the codec trap that mis-reads
        # UTF-8 bytes elsewhere in this layer. The SHA output is ASCII so this
        # call is safe either way, but we pin the encoding structurally so no
        # read in the measurement layer is ever decoder-dependent.
        out = subprocess.run(
            ["git", "rev-parse", f"HEAD:{rel.as_posix()}"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        logger.warning("[eval_runner] gold_truth_version unavailable: %s", exc)
        return "unknown"


def load_axis_weights(gold: Dict[str, Any]) -> Dict[str, float]:
    """Resolve the canonical per-axis weights from the gold file.

    The gold file's _metadata.axis_weights is the single source of truth.
    It stores LONG axis names (price_accuracy, specs_correctness,
    winner_correctness, factual_claim_integrity); this maps them to the
    short names used in code and validates the result.

    Semantics (team-lead ruling):
      - _metadata.axis_weights ABSENT entirely  -> fallback to AXIS_WEIGHTS
        (the gold file's current values in short form) + a logged warning.
      - PRESENT but malformed (unknown keys, missing an axis, or sum not
        1.0 +/- 1e-6)  -> hard-fail with ValueError. A silently mis-
        normalized gate is worse than no gate.
    """
    metadata = gold.get("_metadata") if isinstance(gold, dict) else None
    raw = (metadata or {}).get("axis_weights")
    if not raw:
        logger.warning(
            "[eval_runner] gold _metadata.axis_weights absent - using fallback "
            "AXIS_WEIGHTS %s", AXIS_WEIGHTS,
        )
        return dict(AXIS_WEIGHTS)

    mapped: Dict[str, float] = {}
    for long_key, value in raw.items():
        short = _AXIS_LONG_TO_SHORT.get(long_key)
        if short is None:
            raise ValueError(
                f"gold _metadata.axis_weights has unknown axis key {long_key!r}; "
                f"expected one of {sorted(_AXIS_LONG_TO_SHORT)}"
            )
        try:
            mapped[short] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"gold _metadata.axis_weights[{long_key!r}] is non-numeric: {value!r}"
            ) from exc

    if set(mapped) != _AXIS_NAMES:
        raise ValueError(
            f"gold _metadata.axis_weights must cover exactly {sorted(_AXIS_NAMES)} "
            f"(after long->short mapping); got {sorted(mapped)}"
        )

    total = sum(mapped.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"gold _metadata.axis_weights must sum to 1.0 (+/-1e-6); got {total}"
        )
    return mapped


# ---------------------------------------------------------------------------
# Response field extraction (mirrors response_builder shape)
# ---------------------------------------------------------------------------

def _unwrap_body(response_json: Dict[str, Any]) -> Dict[str, Any]:
    """Some shapes nest the comparison under `.data`. Unwrap once if the
    nested dict carries the comparison keys; otherwise use the top level."""
    data = response_json.get("data")
    if isinstance(data, dict) and ("overview" in data or "scoring_v2" in data):
        return data
    return response_json


def _products_overview(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    return (body.get("overview") or {}).get("products") or body.get("products") or []


def _products_specs(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    return (body.get("specs") or {}).get("products") or []


def extract_winner_index(body: Dict[str, Any]) -> Optional[int]:
    """Deterministic winner  -  scoring_v2.overall_score.winner_idx.

    Per dispatcher brief this is read from scoring_v2 (the deterministic
    scorer), NOT overview.winner.product_index (which is prose-derived and
    can disagree). Falls back to overview only when scoring_v2 is absent."""
    sv2 = body.get("scoring_v2")
    if isinstance(sv2, dict):
        overall = sv2.get("overall_score")
        if isinstance(overall, dict) and overall.get("winner_idx") is not None:
            return overall["winner_idx"]
    overview = body.get("overview") or {}
    winner = overview.get("winner") or {}
    if winner.get("product_index") is not None:
        return winner["product_index"]
    return body.get("winner_index")


def extract_price_amount(body: Dict[str, Any], product_idx: int) -> Optional[float]:
    """overview.products[i].price.amount as a float (None when missing)."""
    products = _products_overview(body)
    if product_idx >= len(products):
        return None
    price = products[product_idx].get("price")
    if not isinstance(price, dict):
        return None
    amount = price.get("amount")
    try:
        return float(amount) if amount is not None else None
    except (TypeError, ValueError):
        return None


def extract_specs(body: Dict[str, Any], product_idx: int) -> Dict[str, Any]:
    """specs.products[i].specs dict (falls back to overview products)."""
    specs_products = _products_specs(body)
    if product_idx < len(specs_products):
        return specs_products[product_idx].get("specs") or {}
    overview_products = _products_overview(body)
    if product_idx < len(overview_products):
        return overview_products[product_idx].get("specs") or {}
    return {}


def collect_verdict_text(body: Dict[str, Any]) -> str:
    """All free-text the factual grader scans for forbidden facts: the
    overview verdict block, scoring_v2.factual_verdict lines, per-product
    best_for, and review-summary consensus/highlights."""
    parts: List[str] = []
    overview = body.get("overview") or {}
    winner = overview.get("winner") or {}
    for key in ("declaration", "reason", "key_tradeoff", "winner_declaration"):
        val = winner.get(key)
        if isinstance(val, str):
            parts.append(val)

    sv2 = body.get("scoring_v2") or {}
    fv = sv2.get("factual_verdict")
    if isinstance(fv, dict):
        for key in ("line1", "line2"):
            val = fv.get(key)
            if isinstance(val, str):
                parts.append(val)

    for product in (overview.get("products") or []):
        bf = product.get("best_for")
        if isinstance(bf, str):
            parts.append(bf)

    for product in ((body.get("reviews") or {}).get("products") or []):
        summary = product.get("review_summary")
        if isinstance(summary, dict):
            consensus = summary.get("consensus")
            if isinstance(consensus, str):
                parts.append(consensus)
            for hl in summary.get("highlights") or []:
                if isinstance(hl, str):
                    parts.append(hl)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Grading functions (pure  -  F4.2 contract)
# ---------------------------------------------------------------------------

def grade_price(actual_amount: Optional[float], expected: Dict[str, Any]) -> bool:
    """True iff actual price is within [min*0.85, max*1.15].

    An un-authored / empty expected dict is vacuously satisfied (the gold
    set leaves price bands blank for some products)."""
    if not expected:
        return True
    e_min = expected.get("min")
    e_max = expected.get("max")
    if e_min is None or e_max is None:
        return True
    if actual_amount is None:
        return False
    # Round the computed bounds to avoid float drift at the band edge
    # (e.g. 200 * 1.15 = 229.99999999999997 would reject a clean 230.0).
    # BHD prices carry at most 3 decimals, so 4-place rounding is safe.
    lower = round(e_min * PRICE_LOWER_FACTOR, 4)
    upper = round(e_max * PRICE_UPPER_FACTOR, 4)
    return lower <= actual_amount <= upper


_DIGIT_LETTER_SEAM = re.compile(r"(?<=[0-9])(?=[a-z])|(?<=[a-z])(?=[0-9])")


def _spec_canonical(value: Any) -> str:
    """Lowercase, insert a space at every digit<->letter seam, collapse
    whitespace: '128GB' and '128 GB' both canonicalise to '128 gb'
    (case + unit-spacing tolerant)."""
    s = str(value).lower().strip()
    s = _DIGIT_LETTER_SEAM.sub(" ", s)
    return " ".join(s.split())


def _spec_value_matches(expected_value: Any, actual_value: Any) -> bool:
    """Boundary-bounded containment of canonical expected within canonical
    actual. 'iOS' matches 'iOS 17' (complete-token containment) and '8GB'
    matches '8 GB' (unit-spacing tolerance); but '55' does NOT match
    '155 cm' and '8GB' does NOT match '128GB' - bare substring credit
    inflated the specs axis (F3 cross-QA finding, S1)."""
    exp = _spec_canonical(expected_value)
    if not exp:
        return False
    act = _spec_canonical(actual_value)
    return re.search(
        r"(?<![a-z0-9])" + re.escape(exp) + r"(?![a-z0-9])", act
    ) is not None


def grade_specs(actual_specs: Optional[Dict[str, Any]], expected: Dict[str, Any]) -> float:
    """Fraction of expected spec keys whose actual value matches
    (boundary-bounded, case- and unit-spacing-tolerant). Empty
    expected -> 1.0 (no-op)."""
    if not expected:
        return 1.0
    actual_specs = actual_specs or {}
    matched = 0
    for key, expected_value in expected.items():
        actual_value = actual_specs.get(key)
        if actual_value is None:
            continue
        if _spec_value_matches(expected_value, actual_value):
            matched += 1
    return matched / len(expected)


def grade_winner(actual_winner_index: Optional[int], expected_winner_index: Optional[int]) -> bool:
    """True iff the deterministic winner index equals the expected index.

    expected None -> vacuously True (gold leaves winner unspecified)."""
    if expected_winner_index is None:
        return True
    if actual_winner_index is None:
        return False
    return actual_winner_index == expected_winner_index


def grade_factual(response_text: str, forbidden_facts: Sequence[str]) -> bool:
    """True iff NO forbidden fact substring appears in the verdict/review
    text (case-insensitive). Empty forbidden list -> True."""
    if not forbidden_facts:
        return True
    haystack = (response_text or "").lower()
    return not any(fact.lower() in haystack for fact in forbidden_facts if fact)


def weighted_pass_score(price_pass: bool, specs_score: float,
                        winner_pass: bool, factual_pass: bool,
                        weights: Optional[Dict[str, float]] = None) -> float:
    """Compose the per-query weighted score from the 4 axes. Boolean axes
    contribute 1.0/0.0; specs contributes its fraction. `weights` defaults
    to AXIS_WEIGHTS (the fallback) but the orchestrator threads in the
    canonical weights loaded from the gold file."""
    w = weights if weights is not None else AXIS_WEIGHTS
    return (
        (1.0 if price_pass else 0.0) * w["price"]
        + specs_score * w["specs"]
        + (1.0 if winner_pass else 0.0) * w["winner"]
        + (1.0 if factual_pass else 0.0) * w["factual"]
    )


# ---------------------------------------------------------------------------
# Result records
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class QueryRunResult:
    """Raw outcome of hitting the endpoint for one query (pre-grading)."""
    id: str
    query: str
    category: str
    http_status: int
    wall_ms: int
    error: Optional[str]
    response: Optional[Dict[str, Any]]


@dataclasses.dataclass
class GradedQuery:
    """A query's graded outcome along all 4 axes."""
    id: str
    category: str
    wall_ms: int
    http_status: int
    error: Optional[str]
    price_pass: bool
    specs_score: float
    winner_pass: bool
    factual_pass: bool
    weighted_score: float
    passing: bool
    wall_over_cap: bool


@dataclasses.dataclass
class EvalReport:
    """Aggregate of a full eval run  -  mirrors the eval_runs row columns."""
    queries_total: int
    queries_passing: int
    pass_rate: float
    axis_avg_price: float
    axis_avg_specs: float
    axis_avg_winner: float
    axis_avg_factual: float
    wall_p50_ms: Optional[int]
    wall_p95_ms: Optional[int]
    per_query: List[GradedQuery]
    failing_ids: List[str]
    p95_over_cap: bool


# ---------------------------------------------------------------------------
# Single-query execution + grading
# ---------------------------------------------------------------------------

async def run_query(client: httpx.AsyncClient, record: Dict[str, Any]) -> QueryRunResult:
    """Hit /api/v1/text/compare for one gold record (?nocache=true).

    Records http status, wall-time (ms), parsed JSON, and any network/parse
    error. Never raises  -  failures are captured on the result so the run
    completes."""
    params = {
        "q": record["query"],
        "region": record.get("region", "bahrain"),
        "nocache": "true",
    }
    timeout = float(record.get("max_wall_seconds", 25.0)) + TIMEOUT_SLACK_SECONDS
    start = time.monotonic()
    http_status = 0
    error: Optional[str] = None
    response_json: Optional[Dict[str, Any]] = None
    try:
        resp = await client.get("/api/v1/text/compare", params=params, timeout=timeout)
        http_status = resp.status_code
        if resp.status_code == 200:
            response_json = _unwrap_body(resp.json())
        else:
            error = f"http_{resp.status_code}"
    except httpx.TimeoutException:
        error = "timeout"
    except httpx.HTTPError as exc:
        error = f"network:{type(exc).__name__}"
    except json.JSONDecodeError as exc:
        error = f"json_decode:{exc}"
    wall_ms = int((time.monotonic() - start) * 1000)
    return QueryRunResult(
        id=record["id"],
        query=record["query"],
        category=record.get("category", ""),
        http_status=http_status,
        wall_ms=wall_ms,
        error=error,
        response=response_json,
    )


def grade_run_result(run_result: QueryRunResult, record: Dict[str, Any],
                     weights: Optional[Dict[str, float]] = None) -> GradedQuery:
    """Apply the 4 graders to a raw run result against its gold record.
    `weights` (canonical, from the gold file) is threaded into the weighted
    pass score; defaults to AXIS_WEIGHTS when not supplied."""
    body = run_result.response or {}
    expected_prices = record.get("expected_prices") or {}
    expected_specs = record.get("expected_specs") or {}

    # Price axis: BOTH products must satisfy their band (un-authored bands
    # are vacuously satisfied per grade_price).
    price_pass = run_result.error is None and all(
        grade_price(extract_price_amount(body, idx), expected_prices.get(f"product_{idx}") or {})
        for idx in (0, 1)
    )

    # Specs axis: average of per-product spec fractions.
    if run_result.error is not None:
        specs_score = 0.0
    else:
        specs_scores = [
            grade_specs(extract_specs(body, idx), expected_specs.get(f"product_{idx}") or {})
            for idx in (0, 1)
        ]
        specs_score = sum(specs_scores) / len(specs_scores)

    winner_pass = run_result.error is None and grade_winner(
        extract_winner_index(body), record.get("expected_winner_index")
    )

    factual_pass = run_result.error is None and grade_factual(
        collect_verdict_text(body), record.get("forbidden_facts") or []
    )

    weighted = weighted_pass_score(price_pass, specs_score, winner_pass, factual_pass,
                                   weights=weights)
    passing = run_result.error is None and weighted >= QUERY_PASS_THRESHOLD
    cap = float(record.get("max_wall_seconds", 25.0))
    return GradedQuery(
        id=run_result.id,
        category=run_result.category,
        wall_ms=run_result.wall_ms,
        http_status=run_result.http_status,
        error=run_result.error,
        price_pass=price_pass,
        specs_score=round(specs_score, 4),
        winner_pass=winner_pass,
        factual_pass=factual_pass,
        weighted_score=round(weighted, 4),
        passing=passing,
        wall_over_cap=(run_result.wall_ms / 1000.0) > cap,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def _percentile(sorted_values: List[int], pct: float) -> int:
    """Nearest-rank percentile (pct in [0,1]) over a sorted int list."""
    if not sorted_values:
        return 0
    k = max(0, min(len(sorted_values) - 1, int(round(pct * (len(sorted_values) - 1)))))
    return sorted_values[k]


def aggregate(graded: List[GradedQuery]) -> EvalReport:
    """Roll per-query grades up into an EvalReport (eval_runs row shape)."""
    total = len(graded)
    passing = sum(1 for g in graded if g.passing)
    pass_rate = (passing / total) if total else 0.0

    def _avg(values: List[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    axis_avg_price = _avg([1.0 if g.price_pass else 0.0 for g in graded])
    axis_avg_specs = _avg([g.specs_score for g in graded])
    axis_avg_winner = _avg([1.0 if g.winner_pass else 0.0 for g in graded])
    axis_avg_factual = _avg([1.0 if g.factual_pass else 0.0 for g in graded])

    walls = sorted(g.wall_ms for g in graded)
    p50 = _percentile(walls, 0.50) if walls else None
    p95 = _percentile(walls, 0.95) if walls else None

    return EvalReport(
        queries_total=total,
        queries_passing=passing,
        pass_rate=round(pass_rate, 4),
        axis_avg_price=axis_avg_price,
        axis_avg_specs=axis_avg_specs,
        axis_avg_winner=axis_avg_winner,
        axis_avg_factual=axis_avg_factual,
        wall_p50_ms=p50,
        wall_p95_ms=p95,
        per_query=graded,
        failing_ids=[g.id for g in graded if not g.passing],
        p95_over_cap=(p95 is not None and p95 > STREAM_HARD_CAP_SECONDS * 1000),
    )


async def run_eval(
    queries: List[Dict[str, Any]],
    *,
    base_url: str,
    transport: Optional[httpx.BaseTransport] = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    weights: Optional[Dict[str, float]] = None,
) -> EvalReport:
    """Execute every query against base_url with a bounded-concurrency pool,
    grade each, and aggregate. `transport` lets tests inject a MockTransport.
    `weights` (canonical, from the gold file via load_axis_weights) is
    threaded into per-query grading; defaults to AXIS_WEIGHTS."""
    semaphore = asyncio.Semaphore(concurrency)
    client_kwargs: Dict[str, Any] = {"base_url": base_url}
    if transport is not None:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        async def _one(record: Dict[str, Any]) -> GradedQuery:
            async with semaphore:
                run_result = await run_query(client, record)
            return grade_run_result(run_result, record, weights=weights)

        graded = await asyncio.gather(*[_one(q) for q in queries])

    return aggregate(list(graded))


# ---------------------------------------------------------------------------
# Subset selection
# ---------------------------------------------------------------------------

def select_queries(gold: Dict[str, Any], subset: Optional[str] = None,
                   subset_path: Path = DEFAULT_SMOKE_SUBSET) -> List[Dict[str, Any]]:
    """Return the query list, optionally filtered to the smoke20 subset.

    subset='smoke20' reads data/eval_smoke_subset.json (a list of ids) and
    returns those gold records in gold order. subset=None -> all queries."""
    queries = gold.get("queries") or []
    if subset == "smoke20":
        if not subset_path.exists():
            raise FileNotFoundError(f"smoke subset file missing: {subset_path}")
        subset_doc = json.loads(subset_path.read_text(encoding="utf-8"))
        ids = set(subset_doc.get("ids") or [])
        return [q for q in queries if q["id"] in ids]
    return queries


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_report(report: EvalReport) -> str:
    lines = [
        "=" * 60,
        f"queries: {report.queries_passing}/{report.queries_total} passing  "
        f"pass_rate={report.pass_rate:.1%}",
        f"axis avg  -  price={report.axis_avg_price:.3f} specs={report.axis_avg_specs:.3f} "
        f"winner={report.axis_avg_winner:.3f} factual={report.axis_avg_factual:.3f}",
        f"wall p50={report.wall_p50_ms}ms p95={report.wall_p95_ms}ms "
        f"(cap {int(STREAM_HARD_CAP_SECONDS * 1000)}ms) "
        f"{'OVER-CAP' if report.p95_over_cap else 'within cap'}",
    ]
    if report.failing_ids:
        lines.append(f"failing: {', '.join(report.failing_ids)}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=os.getenv("TARGET_BASE_URL", DEFAULT_PROD_URL),
                        help="Target API base URL (env TARGET_BASE_URL)")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD))
    parser.add_argument("--subset", choices=["smoke20"], default=None,
                        help="Run only the curated 20-id smoke subset")
    parser.add_argument("--mode", choices=["regression", "absolute"], default="absolute")
    parser.add_argument("--threshold", type=float, default=0.95,
                        help="absolute mode: min pass-rate (default 0.95)")
    parser.add_argument("--baseline-run-id", default=None,
                        help="regression mode: eval_runs row id to compare against")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--run-kind", choices=["ci_pr", "nightly", "manual", "staging_smoke"],
                        default="manual")
    parser.add_argument("--persist", action="store_true",
                        help="Write an eval_runs row (service-role Supabase)")
    parser.add_argument("--allow-full", action="store_true",
                        help="Required to run the FULL set live (cost guard)")
    parser.add_argument("--out", default=None, help="Write per-query JSON lines to PATH")
    args = parser.parse_args(argv)

    try:
        gold = load_gold_truth(args.gold)
        queries = select_queries(gold, subset=args.subset)
        # Canonical weights from the gold file (long->short mapped + validated).
        # A malformed _metadata.axis_weights hard-fails here rather than
        # silently grading on a mis-normalized weight set.
        axis_weights = load_axis_weights(gold)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    if not queries:
        print("ERROR: no queries selected", file=sys.stderr)
        return 3

    # Cost guard  -  the full set live needs an explicit opt-in.
    if args.subset is None and not args.allow_full:
        print(
            f"REFUSING to run the full {len(queries)}-query set live without "
            f"--allow-full (Serper cost guard). Use --subset smoke20 or pass "
            f"--allow-full after dispatcher GO.",
            file=sys.stderr,
        )
        return 3

    print(f"# eval run: base={args.base_url} n={len(queries)} mode={args.mode} "
          f"subset={args.subset or 'full'} weights={axis_weights}")
    report = asyncio.run(run_eval(queries, base_url=args.base_url,
                                  concurrency=args.concurrency,
                                  weights=axis_weights))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for g in report.per_query:
                fh.write(json.dumps(dataclasses.asdict(g), ensure_ascii=False) + "\n")

    print(_format_report(report))

    run_id = None
    if args.persist:
        from scripts import eval_persistence  # local import keeps DB optional
        run_id = eval_persistence.persist_eval_run(
            report, run_kind=args.run_kind,
            gold_version=gold_truth_version(args.gold),
            metadata={"base_url": args.base_url, "subset": args.subset or "full",
                      "axis_weights_used": axis_weights},
        )
        print(f"# eval_runs row: {run_id}")

    # Gate evaluation
    from scripts import eval_gate
    gate_pass, gate_msg = eval_gate.evaluate_gate(
        report, mode=args.mode, threshold=args.threshold,
        baseline_run_id=args.baseline_run_id,
    )
    print(gate_msg)
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
