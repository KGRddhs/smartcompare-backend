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
# S3 E3 — OpenAI cost-guard
#
# The full-200 capture drained the OpenAI account (insufficient_quota took prod
# DOWN). The eval doesn't call OpenAI directly, but each /text/compare DRIVES a
# fan-out of backend OpenAI calls (product-parse + specs + price-extraction +
# reviews + verdict ≈ 5). Like the Serper --allow-full guard, we pre-flight a
# static estimate of the OpenAI calls a run will drive and REFUSE when it
# exceeds a safe budget unless explicitly overridden. Static estimate because
# the eval hits remote prod and can't read prod's live OpenAI counter.
# ---------------------------------------------------------------------------

# Conservative estimate of OpenAI calls one /compare drives (parse + specs +
# price extraction + reviews + verdict). Real count varies (cache hits, Tier
# fallbacks), so this is the upper-ish bound used for the pre-flight estimate.
OPENAI_CALLS_PER_QUERY = 5

# Default OpenAI-call budget for a single eval run. Sized so smoke20 (20 × 5 =
# 100) runs freely but any full-200-scale run (200 × 5 = 1000) is gated behind
# an explicit override — exactly the policy that would have caught the drain.
# Override via env EVAL_OPENAI_CALL_BUDGET or --openai-call-budget.
DEFAULT_OPENAI_CALL_BUDGET = 150

# Warn (but proceed) when the estimate crosses this fraction of the budget.
_OPENAI_WARN_FRACTION = 0.80


def _openai_call_budget() -> int:
    """Resolve the OpenAI-call budget from env (read fresh so a Railway/CI env
    update takes effect without an edit). Malformed → the default, never
    crashes the run."""
    try:
        return int(os.environ.get("EVAL_OPENAI_CALL_BUDGET", DEFAULT_OPENAI_CALL_BUDGET))
    except (TypeError, ValueError):
        return DEFAULT_OPENAI_CALL_BUDGET


def estimate_openai_calls(n_queries: int) -> int:
    """Static estimate of the OpenAI calls a run of `n_queries` will DRIVE
    (n_queries × the per-compare fan-out). The pre-flight cost-guard input."""
    return max(0, int(n_queries)) * OPENAI_CALLS_PER_QUERY


def check_openai_budget(n_queries: int, *, budget: int,
                        allow_overspend: bool) -> tuple[bool, str]:
    """Pre-flight the OpenAI spend for a run. Returns (ok, message).

    - estimate > budget and NOT allow_overspend → (False, refuse message).
    - estimate > budget and allow_overspend → (True, override-warning).
    - estimate within the warn band (>= 80% of budget) → (True, warning).
    - else → (True, ok message).

    The message always states the estimate + budget so the operator can act.
    This is the drain-prevention contract: a full-200-scale run cannot silently
    proceed past the budget."""
    # ASCII-only messages (no em-dash) so captured/redirected eval logs don't
    # mojibake under the Windows cp1252 console codec (CLAUDE.md trap).
    estimate = estimate_openai_calls(n_queries)
    head = f"OpenAI cost-guard: ~{estimate} calls estimated (budget {budget})"
    if estimate > budget:
        if not allow_overspend:
            return False, (
                f"REFUSING - {head}. This would exceed the safe OpenAI budget "
                f"(the full-200 capture drained the account + took prod down). "
                f"Pass --allow-openai-overspend after dispatcher GO, or use a "
                f"smaller subset."
            )
        return True, (
            f"WARNING - {head}: over budget but proceeding via "
            f"--allow-openai-overspend (override)."
        )
    if estimate >= _OPENAI_WARN_FRACTION * budget:
        pct = round(100 * estimate / budget) if budget else 0
        return True, f"WARNING - {head}: approaching budget ({pct}%)."
    return True, f"{head}: OK."


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


# Price source_method enum values that mean "real data", not a GPT estimate.
# The Tier-3 GPT training-data fallback tags `estimated`; everything else
# (local_bhd / converted_usd / page_scrape / page_scrape_rendered / firecrawl /
# scrapedo_rendered) is a real fetched/converted price. (CLAUDE.md price
# pipeline.) The estimate-share metric counts `estimated` against this set.
_ESTIMATED_SOURCE_METHOD = "estimated"


def extract_price_source_method(body: Dict[str, Any], product_idx: int) -> Optional[str]:
    """overview.products[i].price.source_method (None when no price produced).

    S3 L4.1 — the price provenance enum used by the estimate-share metric.
    Returns None when the product has no price object or the object carries no
    source_method key (older backend / no price found) — such a cell is in
    neither the estimated nor the priced bucket."""
    products = _products_overview(body)
    if product_idx >= len(products):
        return None
    price = products[product_idx].get("price")
    if not isinstance(price, dict):
        return None
    method = price.get("source_method")
    # A non-string or empty/whitespace method means no real provenance was
    # recorded — treat it as "no price produced" (in neither bucket) rather
    # than diluting the priced denominator with a phantom cell.
    if not isinstance(method, str) or not method.strip():
        return None
    return method


def count_price_source_cells(body: Dict[str, Any]) -> tuple[int, int]:
    """Tally (estimated_cells, priced_cells) across both products' prices.

    S3 L4.1 — `priced_cells` counts price fields the engine actually PRODUCED
    (a non-null source_method); `estimated_cells` is the subset whose method is
    the Tier-3 GPT `estimated` fallback. A product with no price (None) is in
    neither bucket — the metric measures the honesty of produced prices, not
    coverage. Run-level estimate_share = sum(estimated) / sum(priced)."""
    estimated = 0
    priced = 0
    for idx in (0, 1):
        method = extract_price_source_method(body, idx)
        if method is None:
            continue
        priced += 1
        if method == _ESTIMATED_SOURCE_METHOD:
            estimated += 1
    return estimated, priced


# S3 E1 — price source_method values that mean a GENUINE Bahrain price: a real
# fetch from a BH retailer page/feed (NOT a USD->BHD conversion, NOT a GPT
# estimate). Ahmed's standard is genuine BH first; converted_usd / estimated are
# last resort. `shopify_json` is included forward-compatibly — the Shopify
# products.json adapter (S3 tasks #14-16/#21) emits it, and the metric must
# credit it the moment it lands. (`page_scrape_rendered` is a real rendered BH
# page fetch, so it's genuine too.) The genuine-BH-share KPI counts this set as
# the numerator over all produced prices.
# MUST stay in parity with the backend's app/services/price_service.py
# `_GENUINE_BH_SOURCE_METHODS` — otherwise a genuine method the engine stamps
# (notably `page_scrape_jsonld`, which alhajis/ounass genuine BHD prices use)
# counts toward `priced` but NO bucket, silently UNDER-reporting genuine-share.
# tests/test_eval_genuine_methods_parity.py pins the two sets equal.
GENUINE_BH_SOURCE_METHODS = frozenset({
    "local_bhd",
    "page_scrape",
    "page_scrape_jsonld",
    "page_scrape_rendered",
    "firecrawl",
    "firecrawl_brand_domain",
    "scrapedo_rendered",
    "shopify_json",
    "official_brand",
    # BH/GCC source-build (2026-06-25) — mirror of the backend's 5 new direct-fetch
    # genuine methods. MUST stay equal to price_service._GENUINE_BH_SOURCE_METHODS
    # (tests/test_eval_genuine_methods_parity.py) or a genuine method the engine
    # stamps would count toward `priced` but no bucket, under-reporting the
    # genuine-BH-share KPI.
    "woo_store_api",
    "salla_api",
    "occ_rest_bhd",
    "magento_graphql_bhd",
    "rest_json_bhd",
})

# The one non-genuine, non-estimate bucket: a USD price converted to BHD. Real
# number, but not a BH-sourced price — tracked separately so we can see how much
# of the catalogue still leans on conversion vs genuine BH retail.
_CONVERTED_USD_SOURCE_METHOD = "converted_usd"


def count_price_provenance(body: Dict[str, Any]) -> Dict[str, int]:
    """Tally produced prices into provenance buckets across both products.

    S3 E1 — the full breakdown behind the genuine-BH-share KPI. Returns
    `{genuine_bh, converted_usd, estimated, priced}` where `priced` is the
    number of price fields the engine PRODUCED (non-null source_method) and the
    three buckets partition it (genuine_bh + converted_usd + estimated ==
    priced for known methods). A product with no price is in no bucket. An
    unrecognized non-empty method counts toward `priced` but no bucket — it is
    surfaced by the partition-vs-priced gap rather than silently miscredited."""
    genuine = converted = estimated = priced = 0
    for idx in (0, 1):
        method = extract_price_source_method(body, idx)
        if method is None:
            continue
        priced += 1
        if method in GENUINE_BH_SOURCE_METHODS:
            genuine += 1
        elif method == _CONVERTED_USD_SOURCE_METHOD:
            converted += 1
        elif method == _ESTIMATED_SOURCE_METHOD:
            estimated += 1
    return {
        "genuine_bh": genuine,
        "converted_usd": converted,
        "estimated": estimated,
        "priced": priced,
    }


def extract_specs(body: Dict[str, Any], product_idx: int) -> Dict[str, Any]:
    """specs.products[i].specs dict (falls back to overview products)."""
    specs_products = _products_specs(body)
    if product_idx < len(specs_products):
        return specs_products[product_idx].get("specs") or {}
    overview_products = _products_overview(body)
    if product_idx < len(overview_products):
        return overview_products[product_idx].get("specs") or {}
    return {}


def extract_missing_dim_cells(body: Dict[str, Any]) -> int:
    """S2 I3.6 — read metadata.missing_dim_cells.count (the count of
    MISSING_SCORE dimension cells the engine left unfilled). The KPI dial
    for Ahmed's Decision B "no missing data / no false certainty".

    Returns 0 when the metric is absent (older backend, or an error row
    with no body) — the metric measures DATA gaps in answered runs, not
    error starvation, so a missing metric is genuinely 0 for aggregation."""
    if not isinstance(body, dict):
        return 0
    metadata = body.get("metadata")
    if not isinstance(metadata, dict):
        return 0
    cells = metadata.get("missing_dim_cells")
    if not isinstance(cells, dict):
        return 0
    count = cells.get("count", 0)
    return int(count) if isinstance(count, (int, float)) else 0


# A4 — per-response cache-observability signal. Backend emits these as TOP-LEVEL
# metadata bools (response_builder.py:1415), always present (default False):
#   metadata.cache_hit          — any product price served from cache
#   metadata.genuine_from_cache — a GENUINE-BH price (a _GENUINE_BH_SOURCE_METHODS
#                                 method) served from cache.
# In a cold (?nocache=true) run both are False; in a --read-cache run that hits
# warmed genuine prices, genuine_from_cache flips True. That flip is the
# warmed-genuine signal the A4 mode exists to measure. (Distinct from the
# /admin/costs `cache_observability` 7-day aggregate, which uses different key
# names — these are the PER-RESPONSE keys.)

def _extract_metadata_bool(body: Dict[str, Any], key: str) -> bool:
    """Read a top-level metadata bool, coercing truthy/falsy. Absent → False
    (older backend / error row with no metadata) — never raises."""
    if not isinstance(body, dict):
        return False
    metadata = body.get("metadata")
    if not isinstance(metadata, dict):
        return False
    return bool(metadata.get(key, False))


def extract_cache_hit(body: Dict[str, Any]) -> bool:
    """A4 — metadata.cache_hit (any product price served from cache)."""
    return _extract_metadata_bool(body, "cache_hit")


def extract_genuine_from_cache(body: Dict[str, Any]) -> bool:
    """A4 — metadata.genuine_from_cache (a genuine-BH price served from cache).
    The warmed-genuine-share signal for a --read-cache run."""
    return _extract_metadata_bool(body, "genuine_from_cache")


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


# Insert a space at every letter<->digit seam so '128GB' tokenizes the same
# as '128 GB' (-> ['128','gb']). Applied before delimiter splitting.
_DIGIT_LETTER_SEAM = re.compile(r"(?<=[0-9])(?=[a-z])|(?<=[a-z])(?=[0-9])")

# Token delimiters: whitespace plus the punctuation that separates spec
# tokens. Splitting on these makes hyphen/space variants equal -
# '4K-UHD' and '4K UHD' both -> ['4','k','uhd'], 'Wi-Fi' / 'Wi Fi' -> ['wi','fi'].
_SPEC_DELIMITERS = re.compile(r"[\s,/;:|()\-]+")


def _tokenize_spec(value: Any) -> List[str]:
    """Lowercase a spec value, insert a space at letter<->digit seams, then
    split on whitespace and delimiters into comparable tokens.

    '128GB'   -> ['128', 'gb']      '128 GB'  -> ['128', 'gb']
    '4K-UHD'  -> ['4', 'k', 'uhd']  '4K UHD'  -> ['4', 'k', 'uhd']
    '155 cm'  -> ['155', 'cm']      'iOS 17'  -> ['ios', '17']
    Punctuation inside a token (the '.' in '1.5') is NOT a delimiter, so
    '1.5' stays one token and never matches a token of '145'."""
    s = _DIGIT_LETTER_SEAM.sub(" ", str(value).lower().strip())
    return [t for t in _SPEC_DELIMITERS.split(s) if t]


def _spec_value_matches(expected_value: Any, actual_value: Any) -> bool:
    """True iff the expected value's tokens appear as a CONTIGUOUS
    subsequence of the actual value's tokens. Token-level (not substring)
    matching is what keeps the unit-spacing + delimiter tolerance ('8GB' ==
    '8 GB', '4K-UHD' == '4K UHD', 'iOS' in 'iOS 17') while rejecting the
    bare-substring false positives F3 found ('55' not in '155 cm', '8GB'
    not in '128GB'). Empty expected -> no match."""
    exp = _tokenize_spec(expected_value)
    if not exp:
        return False
    act = _tokenize_spec(actual_value)
    n = len(exp)
    for i in range(len(act) - n + 1):
        if act[i:i + n] == exp:
            return True
    return False


def grade_specs(actual_specs: Optional[Dict[str, Any]], expected: Dict[str, Any]) -> float:
    """Fraction of expected spec keys whose actual value matches (token-
    level, case- + unit-spacing- + delimiter-tolerant). Empty expected ->
    1.0 (no-op)."""
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
    # S2 I3.6 — count of MISSING_SCORE dimension cells from the response
    # metadata (0 for error rows / older backends). Written to the --out
    # JSONL + aggregated into the run-level missing-dim coverage metric.
    missing_dim_cells: int = 0
    # S3 L4.1 — price-provenance cells for the estimate-share KPI. Of the
    # price fields this query PRODUCED (priced_cells = non-null source_method),
    # estimated_price_cells fell to the Tier-3 GPT `estimated` fallback. Both 0
    # on error rows (no produced prices). Written to the --out JSONL + summed
    # into the run-level estimate_share.
    estimated_price_cells: int = 0
    priced_cells: int = 0
    # S3 E1 — the other two provenance buckets (the genuine-BH-share KPI).
    # genuine_bh_price_cells = produced prices with a real BH-fetch method
    # (GENUINE_BH_SOURCE_METHODS); converted_usd_price_cells = USD->BHD
    # conversions. With estimated_price_cells they partition priced_cells.
    # Summed into the run-level + per-category genuine_bh_share / converted_usd_
    # share. 0 on error rows.
    genuine_bh_price_cells: int = 0
    converted_usd_price_cells: int = 0
    # A4 — per-response cache-observability bools (metadata.cache_hit /
    # genuine_from_cache). False on cold (?nocache) runs + error rows; in a
    # --read-cache run genuine_from_cache flips True when a warmed genuine price
    # is served. Aggregated into the run-level cache_hit_count /
    # genuine_from_cache_count so an A4 run reports the warmed-genuine signal.
    cache_hit: bool = False
    genuine_from_cache: bool = False


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
    # S2 I3.6 — run-level missing-dim coverage (sum + mean across queries).
    # Persisted into the eval_runs metadata jsonb (NOT a DB column) so
    # Decision B's "fully certain, no missing data" directive is measured.
    missing_dim_cells_total: int = 0
    missing_dim_cells_mean: float = 0.0
    # S3 L4.1 — run-level estimate-share (the "no false estimates" KPI).
    # estimated_price_cells_total / priced_cells_total = estimate_share (the
    # fraction of PRODUCED prices that fell to the GPT estimate). Persisted in
    # the eval_runs metadata jsonb so S3 can measure the drop vs the S2
    # baseline as real Bahrain data replaces estimates.
    estimated_price_cells_total: int = 0
    priced_cells_total: int = 0
    estimate_share: float = 0.0
    # S3 E1 — genuine-BH-price-share (the PRIMARY success dial; higher=better).
    # genuine_bh_price_cells_total / priced_cells_total = genuine_bh_share, the
    # fraction of PRODUCED prices that are real BH-sourced (vs converted_usd vs
    # estimated). Persisted in the eval_runs metadata jsonb. per_category_
    # provenance maps category -> {genuine_bh, converted_usd, estimated, priced,
    # genuine_bh_share, converted_usd_share, estimate_share} so we can see where
    # estimates persist by category.
    genuine_bh_price_cells_total: int = 0
    converted_usd_price_cells_total: int = 0
    genuine_bh_share: float = 0.0
    converted_usd_share: float = 0.0
    per_category_provenance: Dict[str, Dict[str, Any]] = dataclasses.field(
        default_factory=dict
    )
    # A4 — cache-observability roll-up (the warmed-genuine signal for a
    # --read-cache run). cache_hit_count = queries that served ANY price from
    # cache; genuine_from_cache_count = queries that served a GENUINE-BH price
    # from cache. Both 0 on a cold run. Surfaced in the report + (when read_cache)
    # the eval_runs metadata so the warmed genuine-share is measurable post-warmer.
    cache_hit_count: int = 0
    genuine_from_cache_count: int = 0


# ---------------------------------------------------------------------------
# Single-query execution + grading
# ---------------------------------------------------------------------------

async def run_query(client: httpx.AsyncClient, record: Dict[str, Any],
                    *, read_cache: bool = False) -> QueryRunResult:
    """Hit /api/v1/text/compare for one gold record.

    By default (cold path) sends ?nocache=true so the run measures cold
    scraping — what the baseline/regression gates compare. When
    `read_cache=True` (A4 --read-cache mode), nocache is OMITTED entirely so
    the engine serves from its L1/L2 price cache (what the warmer populated).
    That cache-read measurement is meaningful only AFTER the price-cache
    warmer cron is activated (see read_cache_note()).

    Records http status, wall-time (ms), parsed JSON, and any network/parse
    error. Never raises  -  failures are captured on the result so the run
    completes."""
    params = {
        "q": record["query"],
        "region": record.get("region", "bahrain"),
    }
    if not read_cache:
        params["nocache"] = "true"
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
    # S3 E1 — full provenance breakdown (genuine_bh / converted_usd / estimated
    # / priced) in one pass; supersedes the L4.1 (estimated, priced)-only count.
    prov = count_price_provenance(body)
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
        missing_dim_cells=extract_missing_dim_cells(body),
        estimated_price_cells=prov["estimated"],
        priced_cells=prov["priced"],
        genuine_bh_price_cells=prov["genuine_bh"],
        converted_usd_price_cells=prov["converted_usd"],
        cache_hit=extract_cache_hit(body),
        genuine_from_cache=extract_genuine_from_cache(body),
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

    missing_total = sum(g.missing_dim_cells for g in graded)
    missing_mean = round(missing_total / total, 4) if total else 0.0

    # S3 L4.1 — estimate-share = produced-prices-that-are-estimates / all-
    # produced-prices. Denominator guards ZeroDiv (all-error or no-price runs
    # → 0.0, an honest "no estimates produced").
    estimated_total = sum(g.estimated_price_cells for g in graded)
    priced_total = sum(g.priced_cells for g in graded)
    estimate_share = round(estimated_total / priced_total, 4) if priced_total else 0.0

    # S3 E1 — genuine-BH-share (PRIMARY dial) + converted_usd share, run-level.
    genuine_total = sum(g.genuine_bh_price_cells for g in graded)
    converted_total = sum(g.converted_usd_price_cells for g in graded)
    genuine_bh_share = round(genuine_total / priced_total, 4) if priced_total else 0.0
    converted_usd_share = round(converted_total / priced_total, 4) if priced_total else 0.0

    # A4 — cache-observability roll-up (the warmed-genuine signal for a
    # --read-cache run; both 0 on a cold ?nocache run).
    cache_hit_count = sum(1 for g in graded if g.cache_hit)
    genuine_from_cache_count = sum(1 for g in graded if g.genuine_from_cache)

    # S3 E1 — per-category provenance: bucket the cells by query category so the
    # report shows WHERE estimates persist (e.g. supplements still estimate-
    # heavy while electronics are genuine). Categories with zero produced prices
    # get zero-guarded shares (no ZeroDiv, not a misleading omission).
    per_category_provenance: Dict[str, Dict[str, Any]] = {}
    cats = sorted({g.category or "uncategorized" for g in graded})
    for cat in cats:
        rows = [g for g in graded if (g.category or "uncategorized") == cat]
        c_genuine = sum(g.genuine_bh_price_cells for g in rows)
        c_converted = sum(g.converted_usd_price_cells for g in rows)
        c_estimated = sum(g.estimated_price_cells for g in rows)
        c_priced = sum(g.priced_cells for g in rows)
        per_category_provenance[cat] = {
            "genuine_bh": c_genuine,
            "converted_usd": c_converted,
            "estimated": c_estimated,
            "priced": c_priced,
            "genuine_bh_share": round(c_genuine / c_priced, 4) if c_priced else 0.0,
            "converted_usd_share": round(c_converted / c_priced, 4) if c_priced else 0.0,
            "estimate_share": round(c_estimated / c_priced, 4) if c_priced else 0.0,
        }

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
        missing_dim_cells_total=missing_total,
        missing_dim_cells_mean=missing_mean,
        estimated_price_cells_total=estimated_total,
        priced_cells_total=priced_total,
        estimate_share=estimate_share,
        genuine_bh_price_cells_total=genuine_total,
        converted_usd_price_cells_total=converted_total,
        genuine_bh_share=genuine_bh_share,
        converted_usd_share=converted_usd_share,
        per_category_provenance=per_category_provenance,
        cache_hit_count=cache_hit_count,
        genuine_from_cache_count=genuine_from_cache_count,
    )


async def run_eval(
    queries: List[Dict[str, Any]],
    *,
    base_url: str,
    transport: Optional[httpx.BaseTransport] = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    weights: Optional[Dict[str, float]] = None,
    read_cache: bool = False,
) -> EvalReport:
    """Execute every query against base_url with a bounded-concurrency pool,
    grade each, and aggregate. `transport` lets tests inject a MockTransport.
    `weights` (canonical, from the gold file via load_axis_weights) is
    threaded into per-query grading; defaults to AXIS_WEIGHTS. `read_cache`
    (A4 --read-cache mode) omits ?nocache=true on every query so the engine
    serves cached prices — meaningful only post-warmer (read_cache_note())."""
    semaphore = asyncio.Semaphore(concurrency)
    client_kwargs: Dict[str, Any] = {"base_url": base_url}
    if transport is not None:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        async def _one(record: Dict[str, Any]) -> GradedQuery:
            async with semaphore:
                run_result = await run_query(client, record, read_cache=read_cache)
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
# A4 — cache-read mode caveat
# ---------------------------------------------------------------------------

def read_cache_note() -> str:
    """The caveat printed for a --read-cache run.

    The default eval measures COLD scraping (?nocache=true). --read-cache omits
    nocache so the engine serves cached prices — but that only reflects the
    warmer's genuine-share AFTER the price-cache warmer cron is activated
    (ENABLE_PRICE_CACHE_WARMER). Before activation a cache-read run mostly hits
    cold misses and is NOT a valid genuine-share measurement. ASCII-only (no
    em-dash/U+00B7) so captured/redirected logs don't mojibake under the
    Windows cp1252 console codec (CLAUDE.md trap)."""
    return (
        "NOTE [--read-cache]: this run does NOT pass nocache=true, so it reads "
        "the engine's cached prices. The genuine-BH-share it reports is only "
        "meaningful AFTER the price-cache warmer cron is activated "
        "(ENABLE_PRICE_CACHE_WARMER). Before activation most queries hit cold "
        "cache misses, so treat the numbers as a wiring smoke-check, not a "
        "genuine-share measurement."
    )


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
        f"missing-dim cells  -  total={report.missing_dim_cells_total} "
        f"mean={report.missing_dim_cells_mean:.2f}/query (I3.6 KPI dial)",
        f"estimate-share  -  {report.estimate_share:.1%} "
        f"({report.estimated_price_cells_total}/{report.priced_cells_total} "
        f"produced prices are estimates -- L4.1 KPI -- lower=better)",
        # S3 E1 — genuine-BH-share is the PRIMARY success dial (higher=better).
        # ASCII-only separators (no U+00B7) so captured/redirected reports don't
        # mojibake under the Windows cp1252 console codec (CLAUDE.md trap).
        f"genuine-BH-share  -  {report.genuine_bh_share:.1%} GENUINE "
        f"({report.genuine_bh_price_cells_total}/{report.priced_cells_total}) "
        f"| converted_usd {report.converted_usd_share:.1%} "
        f"| estimated {report.estimate_share:.1%} "
        f"-- E1 PRIMARY dial -- higher genuine=better",
    ]
    # S3 E1 — per-category provenance breakdown (where do estimates persist?).
    if report.per_category_provenance:
        lines.append("genuine-BH by category (genuine / converted / estimated of priced):")
        for cat, p in sorted(report.per_category_provenance.items()):
            if not p.get("priced"):
                continue
            lines.append(
                f"  {cat:<14} genuine={p['genuine_bh_share']:.0%} "
                f"converted={p['converted_usd_share']:.0%} "
                f"estimated={p['estimate_share']:.0%}  (n={p['priced']})"
            )
    # A4 — cache-observability (the warmed-genuine signal). Only shown when a
    # cache hit occurred (a cold ?nocache run = both 0, stays quiet). For a
    # --read-cache run post-warmer, genuine-from-cache is the real warmed share.
    if report.cache_hit_count or report.genuine_from_cache_count:
        n = report.queries_total or 1
        lines.append(
            f"cache-read  -  cache_hit {report.cache_hit_count}/{report.queries_total} "
            f"({report.cache_hit_count / n:.0%}) | genuine-from-cache "
            f"{report.genuine_from_cache_count}/{report.queries_total} "
            f"({report.genuine_from_cache_count / n:.0%}) "
            f"-- A4 warmed-genuine signal (read-cache runs only)"
        )
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
                        help="Required to run the FULL set live (Serper cost guard)")
    parser.add_argument("--openai-call-budget", type=int, default=None,
                        help="Max OpenAI calls a run may DRIVE before it refuses "
                             "(default env EVAL_OPENAI_CALL_BUDGET or "
                             f"{DEFAULT_OPENAI_CALL_BUDGET}). E3 drain guard.")
    parser.add_argument("--allow-openai-overspend", action="store_true",
                        help="Override the OpenAI cost-guard refusal for an "
                             "authorized big run (dispatcher GO).")
    parser.add_argument("--out", default=None, help="Write per-query JSON lines to PATH")
    parser.add_argument("--read-cache", action="store_true",
                        help="A4 cache-read mode: do NOT pass nocache=true, so "
                             "the engine serves cached prices. Meaningful only "
                             "AFTER the price-cache warmer cron is activated "
                             "(ENABLE_PRICE_CACHE_WARMER) — see read_cache_note().")
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

    # S3 E3 — OpenAI cost-guard. Pre-flight the OpenAI calls this run will DRIVE
    # and refuse if it would blow the safe budget (the full-200 capture drained
    # the account + took prod down). Mirrors the Serper guard above.
    openai_budget = (args.openai_call_budget if args.openai_call_budget is not None
                     else _openai_call_budget())
    openai_ok, openai_msg = check_openai_budget(
        len(queries), budget=openai_budget,
        allow_overspend=args.allow_openai_overspend,
    )
    print(f"# {openai_msg}")
    if not openai_ok:
        print(openai_msg, file=sys.stderr)
        return 3

    # A4 — a cache-read run reads the warmer's cached prices instead of
    # force-missing the cache. Surface the caveat loudly so a reader doesn't
    # mistake a pre-warmer cache-read number for a real genuine-share.
    cache_mode = "read-cache" if args.read_cache else "cold(nocache)"
    if args.read_cache:
        print(f"# {read_cache_note()}")
    print(f"# eval run: base={args.base_url} n={len(queries)} mode={args.mode} "
          f"subset={args.subset or 'full'} cache={cache_mode} weights={axis_weights}")
    report = asyncio.run(run_eval(queries, base_url=args.base_url,
                                  concurrency=args.concurrency,
                                  weights=axis_weights,
                                  read_cache=args.read_cache))

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
                      "axis_weights_used": axis_weights,
                      # S2 I3.6 — missing-dim coverage (Decision B KPI dial).
                      "missing_dim_cells_total": report.missing_dim_cells_total,
                      "missing_dim_cells_mean": report.missing_dim_cells_mean,
                      # S3 L4.1 — estimate-share ("no false estimates" KPI).
                      "estimate_share": report.estimate_share,
                      "estimated_price_cells_total": report.estimated_price_cells_total,
                      "priced_cells_total": report.priced_cells_total,
                      # S3 E1 — genuine-BH-share (PRIMARY success dial) + breakdown.
                      "genuine_bh_share": report.genuine_bh_share,
                      "converted_usd_share": report.converted_usd_share,
                      "genuine_bh_price_cells_total": report.genuine_bh_price_cells_total,
                      "converted_usd_price_cells_total": report.converted_usd_price_cells_total,
                      "per_category_provenance": report.per_category_provenance,
                      # A4 — cache-read mode + warmed-genuine signal (so an A4
                      # run's eval_runs row records whether it measured cold or
                      # warmed, and the warmed genuine-from-cache count).
                      "read_cache": bool(args.read_cache),
                      "cache_hit_count": report.cache_hit_count,
                      "genuine_from_cache_count": report.genuine_from_cache_count},
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
