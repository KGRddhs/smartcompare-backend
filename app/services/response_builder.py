"""Response Builder — builds the full comparison response dict.

Extracted from duplicated response assembly code in compare_from_text()
and compare_from_text_streaming().
"""
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.services.scoring_service import (
    MISSING_SCORE,
    build_dimensions_v2,
    calibrate_score,
    compute_confidence,
    count_missing_dim_cells,
)

logger = logging.getLogger(__name__)


# Bundle C § 1b diagnostic flag — gated on DEBUG_STAGE_TIMINGS=true so
# the factual_verdict None-emit hook adds zero overhead in production.
# Cached at process init; tests reset via monkeypatch on _FACTUAL_VERDICT_DIAG_FLAG.
_FACTUAL_VERDICT_DIAG_FLAG = None


def _factual_verdict_diag_enabled() -> bool:
    global _FACTUAL_VERDICT_DIAG_FLAG
    if _FACTUAL_VERDICT_DIAG_FLAG is None:
        _FACTUAL_VERDICT_DIAG_FLAG = (
            os.environ.get("DEBUG_STAGE_TIMINGS", "false").lower() == "true"
        )
    return _FACTUAL_VERDICT_DIAG_FLAG


def _compute_cache_observability(
    product_data: Optional[List[Dict[str, Any]]],
) -> Dict[str, bool]:
    """Faithful-Results Task 1.6 — per-response cache hit-rate signal.

    Returns `{cache_hit, genuine_from_cache}`:
      - `cache_hit`: True iff ANY product's price was served from cache
        (price `_cached` truthy).
      - `genuine_from_cache`: True iff a GENUINE-BH price (a
        `_GENUINE_BH_SOURCE_METHODS` method) was served from cache — the dial
        that proves the warmer serves genuine prices at $0 instead of
        re-scraping them.

    Defensive: price may be None / missing source_method / a pending shape.
    """
    out = {"cache_hit": False, "genuine_from_cache": False}
    if not product_data:
        return out
    try:
        from app.services.price_service import _GENUINE_BH_SOURCE_METHODS
    except Exception:  # noqa: BLE001 — never let the import break response build
        _GENUINE_BH_SOURCE_METHODS = frozenset()
    for p in product_data:
        price = (p or {}).get("price")
        if not isinstance(price, dict):
            continue
        if not price.get("_cached"):
            continue
        out["cache_hit"] = True
        sm = (price.get("source_method") or "").lower()
        if sm in _GENUINE_BH_SOURCE_METHODS and "converted" not in sm and "estimate" not in sm:
            out["genuine_from_cache"] = True
    return out


def _safe_review_praise(pd: Dict[str, Any]) -> Optional[str]:
    """Synthesized review praise for a product's reviews, fail-soft to None.
    Faithful-Results Phase 5 (Contract 2). Never raises."""
    try:
        from app.services.review_service import build_review_praise
        return build_review_praise((pd or {}).get("reviews"))
    except Exception:  # noqa: BLE001 — praise is additive; never break the response
        return None


def _factual_verdict_present_in_scoring_v2(scoring_v2: Dict[str, Any]) -> bool:
    """Return True iff scoring_v2 has a factual_verdict with line1 or line2.
    Used by the § 1b diagnostic and patchable from tests to simulate the
    post-A.3.2 populated state."""
    fv = scoring_v2.get("factual_verdict") if isinstance(scoring_v2, dict) else None
    if not isinstance(fv, dict):
        return False
    return bool(fv.get("line1")) or bool(fv.get("line2"))


def _gpt_winner_lever_enabled() -> bool:
    """S3 intervention #2 flag reader (default OFF). Read live so a Railway flip
    / monkeypatch takes effect without a restart."""
    return os.environ.get("ENABLE_GPT_WINNER", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _eval_capture_debug_enabled() -> bool:
    """S3 L3 v2 — EVAL_CAPTURE_DEBUG flag (default OFF). When ON, the response
    serializes the RAW per-product scoring INPUTS (fact_check) under
    overview.products[i]._debug_capture so the offline param sweep can re-run the
    v2 scorer EXACTLY (the harness re-normalizes — A1/gap-tol change normalization
    — so it needs raw inputs, not the post-norm breakdown). Flipped on Railway
    ONLY for the one full-200 capture run; OFF in normal prod (zero user-facing
    change, no payload bloat)."""
    return os.environ.get("EVAL_CAPTURE_DEBUG", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _debug_capture_payload(pd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Raw scoring inputs the captured body otherwise omits — currently the raw
    fact_check (the reliability dim INPUT). specs/price.source_method/rating/
    review_count/category already live in overview+specs, so fact_check is the
    one missing input for an EXACT offline re-score. None when no fact_check."""
    fc = pd.get("fact_check")
    if not isinstance(fc, dict):
        return None
    return {"fact_check": fc}


def _grounded_gpt_winner(comparison: Dict[str, Any]) -> Optional[int]:
    """Return the verdict's INDEPENDENT winner index (0/1) ONLY when it is
    grounded (model self-reported it justified the call from the supplied facts,
    not a guess) and the index is a valid 0/1 int. None otherwise (older prompt,
    parse miss, ungrounded guess, or malformed index) so the caller falls back
    to the deterministic winner. The `grounded` gate is the no-estimation
    guardrail — an admitted guess never overrides."""
    if not isinstance(comparison, dict):
        return None
    if comparison.get("independent_winner_grounded") is not True:
        return None
    idx = comparison.get("independent_winner_index")
    # Reject bools (bool is an int subclass) and non-0/1 values.
    if isinstance(idx, bool) or not isinstance(idx, int):
        return None
    if idx not in (0, 1):
        return None
    return idx


def derive_rating_from_scores(overall_score: float) -> float:
    """Derive a synthetic rating (1-5 scale) from overall score when no real rating exists."""
    rating = 2.5 + (overall_score / 100) * 2.3
    return round(min(rating, 4.8), 1)


# Bundle C v1 hot-fix wrappers — wire the A.4.5 + A.9.1 helpers from
# scoring_service + structured_comparison_service into the response so
# they actually surface in production payloads. Both are defensive — any
# import / runtime error falls back to a safe default (None for
# comparison_quality so frontend gets the legacy null contract; [] for
# applied_shifts per spec § 7a chip-hides-when-empty rule).


def _safe_detect_comparison_quality(product_data: List[Dict[str, Any]]):
    try:
        from app.services.structured_comparison_service import detect_comparison_quality
        return detect_comparison_quality(product_data, post_fallback=True)
    except Exception:  # noqa: BLE001 — never let a hot-fix wrapper crash the response
        return None


# Bundle D Task 2.B.5 (A.6.4 + A.6.5) — per-product value_match + bundle-
# level budget_mismatch metadata. value_match indicates whether a product's
# price tier matches the user's stated budget preference; budget_mismatch
# flips True when the WINNER product's tier disagrees with the user's
# budget. Both are pure-derivation helpers (no API calls, no side effects)
# so they can be computed unconditionally from existing scoring_result
# data + user_preferences.budget.

# Tier alignment matrix — exact match scores 'match', adjacent tiers score
# 'near', everything else scores 'mismatch'. The 5-tier ordering follows
# Migration 024: budget < mid < premium < luxury < top_tier.
_PRICE_TIER_ORDER = ["budget", "mid", "premium", "luxury", "top_tier"]


def _compute_value_match(product_tier: str, budget_pref: Optional[str]) -> str:
    """Bundle D A.6.4 — classify a product's value-vs-budget alignment.

    Returns 'match' (exact tier hit), 'near' (one tier off either way),
    'mismatch' (two+ tiers off), or 'unknown' (no budget preference, or
    unrecognized tier).

    Used by FE to render a per-product budget-fit indicator next to the
    price chip on the overview card.
    """
    if not budget_pref or budget_pref not in _PRICE_TIER_ORDER:
        return "unknown"
    if not product_tier or product_tier not in _PRICE_TIER_ORDER:
        return "unknown"
    pref_idx = _PRICE_TIER_ORDER.index(budget_pref)
    product_idx = _PRICE_TIER_ORDER.index(product_tier)
    gap = abs(pref_idx - product_idx)
    if gap == 0:
        return "match"
    if gap == 1:
        return "near"
    return "mismatch"


def _compute_budget_mismatch(
    winner_tier: Optional[str],
    budget_pref: Optional[str],
) -> bool:
    """Bundle D A.6.5 — flag at metadata level when the chosen winner's
    price tier doesn't align with the user's stated budget preference.

    True iff the winner's tier is two or more tiers off from the user's
    budget (i.e. _compute_value_match returns 'mismatch'). False when:
      - user has no budget set ('unknown')
      - winner tier is unknown
      - winner is in-tier or one tier off

    FE uses this to decide whether to render a 'this might stretch your
    budget' caption beside the verdict.
    """
    return _compute_value_match(winner_tier, budget_pref) == "mismatch"


def _compose_variant_string(product: Dict[str, Any], category: str) -> str:
    """Lane 1 L1.7 — build a short variant tag like '128GB · Black' for
    the product card. Category-aware: phones get storage+color+ram,
    fragrances get volume+concentration, supplements get dose+form,
    fashion gets size+color+material, etc.

    Returns "" when no hooks fire so the FE renders the title alone.
    Caps at 3 segments to fit narrow phones (design Screen 1 contract).
    """
    if not isinstance(product, dict):
        return ""
    specs = product.get("specs") or {}
    if not isinstance(specs, dict):
        return ""

    # Category-specific extraction order. The first 3 hits become the
    # rendered tag; everything past the cap is dropped.
    if category == "electronics":
        keys = ("storage", "color", "ram")
    elif category == "fragrances":
        keys = ("volume_ml", "concentration")
    elif category == "fashion":
        keys = ("size", "color", "material")
    elif category in ("supplements", "vitamins"):
        keys = ("active_ingredient", "form", "serving_size")
    elif category in ("makeup",):
        keys = ("shade", "finish", "spf")
    elif category in ("skincare",):
        keys = ("volume_ml", "form", "spf")
    elif category in ("haircare",):
        keys = ("volume_ml", "hair_type", "form")
    elif category in ("grocery",):
        keys = ("weight", "package_size", "flavor")
    else:
        # `other` / unknown — grab a few common hooks generically.
        keys = ("size", "color", "volume_ml", "weight")

    parts: list[str] = []
    for key in keys:
        if len(parts) >= 3:
            break
        value = specs.get(key)
        if value in (None, "", []):
            continue
        # Tidy ml-style numerics.
        if key == "volume_ml":
            try:
                parts.append(f"{int(float(value))}ml")
            except (TypeError, ValueError):
                parts.append(str(value).strip())
        else:
            parts.append(str(value).strip())
    return " · ".join(parts[:3])


# Fields where SMALLER values win the comparison (e.g. weight — lighter
# phone is better). Defaults to LARGER-wins for everything else.
_SPEC_SMALLER_WINS = {
    "weight",
    "weight_g",
    "weight_grams",
    "thickness",
    "thickness_mm",
    "depth",
    "size",  # ambiguous; better to leave to string-equality
}

# Spec fields with internal-only / metadata semantics — never emit as
# comparable rows on Screen 4.
_SPEC_INTERNAL_FIELDS = {
    "_field_confidence",
    "_internal",
    "_extraction_metadata",
}

# Tokens that signal "no data" on a string spec — the populated side
# wins the comparison.
_SPEC_NA_TOKENS = {"n/a", "na", "none", "unknown", "-", ""}


import re as _re_specs


def _extract_numeric(value) -> float | None:
    """Pull the first numeric out of a spec value like '3349 mAh' / '6 GB' /
    '6.1 inches' / 171. Returns None when no number was found."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    match = _re_specs.search(r"-?(\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _spec_row_winner(
    field: str,
    p0_value,
    p1_value,
) -> int | str | None:
    """Per-row winner detection. Returns 0/1/'tie'/None.

    Numeric specs: SMALLER wins for `_SPEC_SMALLER_WINS` fields, LARGER
    wins otherwise. String specs: 'tie' on equality; the populated side
    wins when the other side is N/A / null; None otherwise (FE renders
    a neutral row).
    """
    p0_str = str(p0_value).strip() if p0_value is not None else ""
    p1_str = str(p1_value).strip() if p1_value is not None else ""
    p0_na = p0_str.lower() in _SPEC_NA_TOKENS or p0_value is None
    p1_na = p1_str.lower() in _SPEC_NA_TOKENS or p1_value is None

    if p0_na and p1_na:
        return None
    if p0_na:
        return 1
    if p1_na:
        return 0

    n0 = _extract_numeric(p0_value)
    n1 = _extract_numeric(p1_value)
    if n0 is not None and n1 is not None:
        if abs(n0 - n1) < 1e-9:
            return "tie"
        smaller_wins = field.lower() in _SPEC_SMALLER_WINS
        if smaller_wins:
            return 0 if n0 < n1 else 1
        return 0 if n0 > n1 else 1

    # Both strings, no numeric — tie on equality (case-insensitive); else
    # neutral so the FE renders the row without a winner highlight.
    if p0_str.lower() == p1_str.lower():
        return "tie"
    return None


def _youtube_signal_for_response(pd: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """S3 L2 — surface the YouTube cited review signal in the response reviews
    section, flag-gated. Returns the signal dict when ENABLE_YOUTUBE_SOURCE is
    ON and the product carries one at reviews.youtube_review_signal; None
    otherwise. Rollback-safe: flag OFF -> None even if the 14d cache attached a
    stale signal to the product (mirrors the verdict-prompt scrub)."""
    if os.environ.get("ENABLE_YOUTUBE_SOURCE", "").strip().lower() not in (
        "true", "1", "on", "yes",
    ):
        return None
    if not isinstance(pd, dict):
        return None
    reviews = pd.get("reviews")
    if not isinstance(reviews, dict):
        return None
    signal = reviews.get("youtube_review_signal")
    if isinstance(signal, dict) and signal.get("top_channel"):
        return signal
    return None


def _build_specs_rows(
    products: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Lane 1 L1.9 — build the per-row specs comparison list for design
    Screen 4. Emits one row per spec field that BOTH products have
    populated. Internal metadata fields (`_field_confidence`, etc.) are
    skipped; one-sided fields are skipped (no half-empty rows)."""
    if len(products) < 2:
        return []
    p0_specs = (products[0] or {}).get("specs") or {}
    p1_specs = (products[1] or {}).get("specs") or {}
    if not isinstance(p0_specs, dict) or not isinstance(p1_specs, dict):
        return []

    rows: List[Dict[str, Any]] = []
    # Use p0's key order so the FE renders a deterministic sequence;
    # any fields exclusive to p1 are appended at the end.
    seen: set[str] = set()
    fields = list(p0_specs.keys()) + [k for k in p1_specs.keys() if k not in p0_specs]
    for field in fields:
        if field in _SPEC_INTERNAL_FIELDS or field.startswith("_"):
            continue
        if field in seen:
            continue
        seen.add(field)
        v0 = p0_specs.get(field)
        v1 = p1_specs.get(field)
        if v0 in (None, "") or v1 in (None, ""):
            continue
        rows.append(
            {
                "field": field,
                "p0_value": v0,
                "p1_value": v1,
                "winner": _spec_row_winner(field, v0, v1),
            }
        )
    return rows


def _build_pros_cons_block(
    product: Dict[str, Any],
    is_winner: bool,
) -> Dict[str, Any]:
    """Lane 1 L1.8 — emit the explicit accordion block.

    Sources pros / cons from `product_data[i].pros_cons.{pros,cons}` (the
    primary path used by extraction_service). Caps each side at 4 per
    design Screen 1 height constraint. `is_winner` lets the FE star the
    winner side without re-reading overview.winner.product_index.
    """
    pc = product.get("pros_cons")
    if not isinstance(pc, dict):
        pc = {}
    pros = pc.get("pros") or []
    cons = pc.get("cons") or []
    if not isinstance(pros, list):
        pros = []
    if not isinstance(cons, list):
        cons = []
    return {
        "pros": list(pros)[:4],
        "cons": list(cons)[:4],
        "is_winner": bool(is_winner),
    }


def _safe_compute_applied_shifts(scoring_result: Dict[str, Any]) -> list:
    """Spec § 7a: chip hides itself when applied_shifts is empty list — so
    we ALWAYS return a list (never None). Reads weights_used from the
    first product's scoring entry (both products share the same weights
    per `compute_scores` flow) and the category defaults from the
    scoring_result top-level."""
    try:
        from app.services.scoring_service import _compute_applied_shifts
        scores = (scoring_result or {}).get("scores") or {}
        first = scores.get("product_0") or {}
        weights_used = first.get("weights_used") or {}
        defaults = (scoring_result or {}).get("category_weights") or {}
        return _compute_applied_shifts(weights_used, defaults) or []
    except Exception:  # noqa: BLE001 — never crash the response
        return []


# ---------------------------------------------------------------------------
# Bundle C § 1b A.3.2 — _build_factual_verdict
# ---------------------------------------------------------------------------
# qa-bundle-c D.1.3 confirmed: every probe returned scoring_v2 with NO
# factual_verdict key because the builder never existed. Pure-template fix:
# compose line1 + line2 from existing product_data + scoring_result fields.
# Zero GPT cost. Respects the FIVE critical rules:
#   - no scary copy (no "couldn't" / "try again" / "Failed to")
#   - no backend internals (no coefficients / cap %s / shift math)
#   - no "estimated" / "reference price" / "approximate" leakage
# Strings are short, factual, and presentational.


def _product_name(p: Dict[str, Any]) -> str:
    """Return a short user-facing name. Falls back to brand + name if name
    alone is empty; final fallback 'this product'."""
    name = (p.get("name") or "").strip()
    if name:
        return name
    brand = (p.get("brand") or "").strip()
    return brand if brand else "this product"


def _safe_price_amount(p: Dict[str, Any]) -> Optional[float]:
    price = p.get("price")
    if isinstance(price, dict):
        amt = price.get("amount")
    else:
        amt = price
    try:
        amt = float(amt) if amt is not None else None
    except (TypeError, ValueError):
        return None
    return amt if (amt is not None and amt > 0) else None


def _safe_rating(p: Dict[str, Any]) -> Optional[float]:
    rating = p.get("rating")
    if isinstance(rating, dict):
        rating = rating.get("score") or rating.get("average")
    try:
        r = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        return None
    return r if r is not None else None


def _price_candidate(products: List[Dict[str, Any]], winner_index: int) -> Optional[Dict[str, Any]]:
    """Build the price-gap candidate fact. Magnitude is the % difference
    between the two prices (0.0–1.0). Returns None if either price missing."""
    if len(products) < 2:
        return None
    pa = _safe_price_amount(products[0])
    pb = _safe_price_amount(products[1])
    if pa is None or pb is None:
        return None
    lo, hi = min(pa, pb), max(pa, pb)
    if hi <= 0:
        return None
    pct = (hi - lo) / hi
    winner_price = (pa, pb)[winner_index]
    runner_price = (pa, pb)[1 - winner_index]
    winner_is_cheaper = winner_price <= runner_price
    return {
        "magnitude": pct,
        "kind": "price",
        "winner_cheaper": winner_is_cheaper,
        "pct": pct,
    }


def _rating_candidate(products: List[Dict[str, Any]], winner_index: int) -> Optional[Dict[str, Any]]:
    """Build the rating-gap candidate fact. Magnitude is the absolute star
    difference normalized to 0–1 (divide by 5)."""
    if len(products) < 2:
        return None
    ra = _safe_rating(products[0])
    rb = _safe_rating(products[1])
    if ra is None or rb is None:
        return None
    diff = abs(ra - rb)
    if diff <= 0.0:
        return None
    winner_rating = (ra, rb)[winner_index]
    runner_rating = (ra, rb)[1 - winner_index]
    winner_higher = winner_rating >= runner_rating
    return {
        "magnitude": diff / 5.0,  # normalize to compare with other candidates
        "kind": "rating",
        "winner_higher": winner_higher,
        "stars_diff": diff,
    }


def _top_dim_candidate(
    dimensions: List[Dict[str, Any]],
    winner_index: int,
) -> Optional[Dict[str, Any]]:
    """Build the dim-margin candidate fact for the WINNER's strongest dim.
    Skips price + reviews (they're already covered by dedicated candidates)
    so this fires for category-specific dims like build_quality / performance."""
    if not dimensions:
        return None
    best = None
    best_margin = 0.0
    for d in dimensions:
        key = d.get("key", "")
        if key in ("price", "reviews", "value"):
            continue
        sa = d.get("score_a")
        sb = d.get("score_b")
        if sa is None or sb is None:
            continue
        margin = sb - sa if winner_index == 1 else sa - sb
        if margin > best_margin:
            best_margin = margin
            best = d
    if best is None or best_margin <= 0:
        return None
    return {
        "magnitude": best_margin / 100.0,  # normalize to compare with other candidates
        "kind": "dim",
        "label": best.get("label", best.get("key", "")).strip(),
        "margin": best_margin,
    }


def _runner_up_dim_candidate(
    dimensions: List[Dict[str, Any]],
    winner_index: int,
) -> Optional[Dict[str, Any]]:
    """Find the dim where the RUNNER-UP beats the winner by the largest
    margin. Used by line2."""
    if not dimensions:
        return None
    runner_index = 1 - winner_index
    best = None
    best_margin = 0.0
    for d in dimensions:
        sa = d.get("score_a")
        sb = d.get("score_b")
        if sa is None or sb is None:
            continue
        margin = (sa - sb) if runner_index == 0 else (sb - sa)
        if margin > best_margin:
            best_margin = margin
            best = d
    if best is None or best_margin <= 0:
        return None
    return {
        "kind": best.get("key", "dim"),
        "label": best.get("label", best.get("key", "")).strip(),
        "margin": best_margin,
    }


# S3 L3.3 — review-density (YouTube attention) as a CITED factual_verdict fact.
# Flag-gated on ENABLE_YOUTUBE_SOURCE so a 14d-cache-carried signal can't leak
# into the verdict after a rollback (mirrors L2's scrub). Only fires when the
# winner has DECISIVELY more attention than the runner-up — a small gap is not a
# fact worth stating. Cites the channel + a humanized count; NEVER a raw integer
# view count, NEVER the word "estimated".
_YT_DENSITY_MIN_VIEWS = 10_000
_YT_DENSITY_DOMINANCE_RATIO = 3.0


def _youtube_source_enabled_rb() -> bool:
    return os.environ.get("ENABLE_YOUTUBE_SOURCE", "").strip().lower() in (
        "true", "1", "on", "yes",
    )


def _humanize_views(n: int) -> str:
    """Compact human view figure: 2_400_000 -> '2.4M', 12_500 -> '12.5K',
    900 -> '900'. Local to response_builder (L2's _humanize_count lives in
    extraction_service; keeping a private copy avoids a cross-module import and
    survives independent of merge order)."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    return str(n)


def _yt_signal_for(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Read L2's youtube_review_signal off a product, flag-gated. None when the
    flag is off / signal absent / malformed."""
    if not _youtube_source_enabled_rb():
        return None
    reviews = p.get("reviews")
    if not isinstance(reviews, dict):
        return None
    sig = reviews.get("youtube_review_signal")
    if isinstance(sig, dict) and sig.get("top_channel"):
        return sig
    return None


def _yt_views(sig: Optional[Dict[str, Any]]) -> int:
    if not isinstance(sig, dict):
        return 0
    try:
        return int(sig.get("total_views") or 0)
    except (TypeError, ValueError):
        return 0


def _review_density_candidate(
    products: List[Dict[str, Any]],
    winner_index: int,
) -> Optional[Dict[str, Any]]:
    """S3 L3.3 — build a CITED review-density candidate fact for the WINNER when
    the winner has decisively more YouTube review attention than the runner-up.
    Returns None when the flag is off, either signal is absent, or the gap isn't
    decisive (so we never state a meaningless 'more reviews' claim).

    Magnitude is normalized into the same 0–1 band the other candidates use so
    it competes fairly for line1. The candidate carries the channel + humanized
    count for citation — never a raw integer."""
    if len(products) < 2:
        return None
    sig_w = _yt_signal_for(products[winner_index])
    sig_r = _yt_signal_for(products[1 - winner_index])
    if sig_w is None:
        return None
    vw = _yt_views(sig_w)
    vr = _yt_views(sig_r)
    if vw < _YT_DENSITY_MIN_VIEWS:
        return None
    denom = max(vr, _YT_DENSITY_MIN_VIEWS / _YT_DENSITY_DOMINANCE_RATIO)
    if vw < denom * _YT_DENSITY_DOMINANCE_RATIO:
        return None  # winner's lead isn't decisive
    return {
        # Scale the gap into ~0–1 so it ranks against price/rating/dim. A 3×+
        # dominance lands ~0.5–0.9; cap at 1.0.
        "magnitude": min(1.0, (vw / denom) / 10.0 + 0.3),
        "kind": "review_density",
        "channel": (sig_w.get("top_channel") or "").strip(),
        "views_human": _humanize_views(vw),
        "video_count": sig_w.get("video_count") or 0,
    }


def _format_line1(
    winner_name: str,
    candidate: Dict[str, Any],
) -> str:
    """Render the winner-anchored line1 from the largest-magnitude candidate.
    Strings are concise + presentational; honor the FIVE critical rules."""
    kind = candidate["kind"]
    if kind == "review_density":
        ch = candidate.get("channel", "")
        views = candidate.get("views_human", "")
        cite = f", led by {ch}" if ch else ""
        return f"{winner_name} draws far more reviewer attention (~{views} YouTube views{cite})."
    if kind == "price":
        pct = round(candidate["pct"] * 100)
        if candidate["winner_cheaper"]:
            return f"{winner_name} comes in {pct}% cheaper."
        return f"{winner_name} carries a {pct}% price premium for the upgrade."
    if kind == "rating":
        diff = round(candidate["stars_diff"], 1)
        if candidate["winner_higher"]:
            return f"{winner_name} earns {diff} more stars from reviewers."
        return f"{winner_name} edges ahead despite slightly lower reviews."
    if kind == "dim":
        label = candidate["label"] or "its strongest dimension"
        return f"{winner_name} leads on {label}."
    return f"{winner_name} comes out on top."


def _format_line2(
    runner_name: str,
    candidate: Optional[Dict[str, Any]],
    products: List[Dict[str, Any]],
    winner_index: int,
) -> str:
    """Render the runner-up counter-fact. If a dim candidate exists, anchor
    on it. Otherwise fall back to price (if runner-up is cheaper) or a
    neutral 'still worth a look' phrasing."""
    if candidate is not None:
        label = candidate["label"] or "its strongest area"
        return f"{runner_name} pulls ahead on {label}."
    # Fallback to price — runner-up may be cheaper even if winner wins overall.
    pa = _safe_price_amount(products[0])
    pb = _safe_price_amount(products[1])
    if pa is not None and pb is not None:
        runner_price = (pa, pb)[1 - winner_index]
        winner_price = (pa, pb)[winner_index]
        if runner_price < winner_price:
            pct = round((winner_price - runner_price) / winner_price * 100)
            return f"{runner_name} stays {pct}% lighter on the wallet."
    # Fallback to rating mention
    ra = _safe_rating(products[0])
    rb = _safe_rating(products[1])
    if ra is not None and rb is not None:
        runner_rating = (ra, rb)[1 - winner_index]
        winner_rating = (ra, rb)[winner_index]
        if runner_rating > winner_rating:
            return f"{runner_name} rates a touch higher with shoppers."
    # Neutral fallback — comparable across the board.
    return f"{runner_name} stays in the conversation as a close alternative."


def _build_factual_verdict(
    products: List[Dict[str, Any]],
    scoring_result: Dict[str, Any],
    winner_index: int,
    dimensions: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Bundle C § 1b — compose factual_verdict.line1 + .line2 from existing
    fields. Pure template, zero GPT cost.

    line1 = winner declaration anchored on the strongest factual delta
            (price gap %, rating gap stars, or top winner-dim margin).
    line2 = runner-up counter-fact anchored on their strongest winning
            dim (or a price/rating fallback if no dim margin found).

    Returns None when fewer than 2 products are supplied (defensive — the
    caller already short-circuits this case in _build_scoring_v2)."""
    if len(products) < 2:
        return None
    dimensions = dimensions or []

    winner_name = _product_name(products[winner_index])
    runner_name = _product_name(products[1 - winner_index])

    # Gather candidate facts for line1, pick the largest-magnitude one.
    # S3 L3.3 — review-density (YouTube attention) joins as a CITED candidate,
    # flag-gated on ENABLE_YOUTUBE_SOURCE. It competes on normalized magnitude;
    # a decisive review-attention gap can anchor line1, otherwise the existing
    # price/rating/dim facts win.
    candidates = [c for c in (
        _price_candidate(products, winner_index),
        _rating_candidate(products, winner_index),
        _top_dim_candidate(dimensions, winner_index),
        _review_density_candidate(products, winner_index),
    ) if c is not None]

    if candidates:
        candidates.sort(key=lambda c: c["magnitude"], reverse=True)
        line1 = _format_line1(winner_name, candidates[0])
    else:
        # Sparse-data fallback — neither price nor rating nor a usable dim
        # margin. Keep it presentational and non-scary.
        line1 = f"{winner_name} edges ahead on the overall picture."

    # line2 — runner-up's strongest counter-fact.
    runner_dim = _runner_up_dim_candidate(dimensions, winner_index)
    line2 = _format_line2(runner_name, runner_dim, products, winner_index)

    return {"line1": line1, "line2": line2}


def _confidence_legs_and_details(
    product_data: List[Dict[str, Any]],
) -> tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Lane 1 L1.6 — compute the per-leg confidence + evidence dicts for
    scoring_v2. Wraps the existing `compute_confidence` so callers get
    the same legs as `overview.confidence` plus an FE-friendly
    `confidence_details` shape (sources_count, method_p0/method_p1,
    review counts, verified spec %).

    Defensive — never raises. Falls back to all-weak legs + empty detail
    dicts if `compute_confidence` blows up on unexpected input.
    """
    try:
        conf = compute_confidence(product_data) or {}
    except Exception:  # noqa: BLE001 — wrapper must never crash the response
        conf = {}

    legs = conf.get("legs") or {"price": "weak", "reviews": "weak", "specs": "weak"}

    # Per-leg evidence — match the existing `overview.confidence` shape
    # one-for-one so the FE can read either surface. Use plural
    # `sources_count` per the design plan (Screen 1 sheet calls it
    # "sources"); the legacy singular `source_count` stays on
    # `overview.confidence.price` for backwards-compat.
    price_legacy = conf.get("price") or {}
    rating_legacy = conf.get("rating") or {}
    specs_legacy = conf.get("specs") or {}

    # Pull per-product source methods to expose on the price detail card.
    p0 = (product_data[0] if product_data else {}) or {}
    p1 = (product_data[1] if len(product_data) > 1 else {}) or {}
    method_p0 = ((p0.get("price") or {}) if isinstance(p0.get("price"), dict) else {}).get("source_method")
    method_p1 = ((p1.get("price") or {}) if isinstance(p1.get("price"), dict) else {}).get("source_method")

    confidence_details = {
        "price": {
            "sources_count": price_legacy.get("source_count", 0),
            "method": price_legacy.get("method"),
            "method_p0": method_p0,
            "method_p1": method_p1,
            "freshness": price_legacy.get("freshness"),
        },
        "reviews": {
            "review_count": rating_legacy.get("review_count", 0),
            "source": rating_legacy.get("source"),
            "verified": bool(rating_legacy.get("verified")),
        },
        "specs": {
            "verified_pct": specs_legacy.get("verified_pct", 0),
            "citation_count": specs_legacy.get("citation_count", 0),
        },
    }
    return legs, confidence_details


def _build_scoring_v2(
    product_data: List[Dict[str, Any]],
    scoring_result: Dict[str, Any],
    category: str,
    winner_index: int,
) -> Dict[str, Any]:
    """Bundle E § Decision 2 — emit calibrated overall_score + dimensions[].
    Backward-compatible: lives alongside legacy `scoring` key for one release."""
    if len(product_data) < 2:
        return {}
    raw_a = scoring_result.get("scores", {}).get("product_0", {}).get("overall", 50)
    raw_b = scoring_result.get("scores", {}).get("product_1", {}).get("overall", 50)
    score_a = calibrate_score(raw_a)
    score_b = calibrate_score(raw_b)
    # S3 L3 v2 [gate finding A] — CALIBRATION-COLLAPSE invariant. The FE derives
    # the winner SOLELY from (product_a >= product_b) ? 0 : 1 (ResultsScreen.tsx),
    # never from winner_idx. calibrate_score = int(round(70+(raw-50)*0.5)) collapses
    # any sub-~2pt raw gap to product_a == product_b, so a genuine product_1 win by
    # a small margin → calibrated tie → the FE `>=` crowns product_0 while the
    # verdict/evidence/name/recommendation all say product_1. v2 (A1 band +
    # magnitude-awareness near-ties + ±4 authority) makes this the modal outcome.
    # ENFORCE argmax(score_a, score_b) == winner_index. Default: nudge the LOSER
    # strictly below the winner (winner keeps its honest calibrated score).
    #
    # [gate re-review — floor-edge hole] At the band FLOOR (both calibrate to 60)
    # the loser-lower can't separate: max(60, min(60, 59)) == 60 == winner → still
    # a tie → FE crowns the loser. calibrate is monotonic, so the floor is the ONE
    # sub-case the loser-nudge can't fix. Unreachable on default flags (A1 → overall
    # ≥~41 → calibrated ≥~66), but DISABLE_DIM_NORM_DAMPENING's legacy 30-100 band
    # reaches it → the bug resurfaces. So when the WINNER sits at/below the floor,
    # RAISE the winner above the loser instead (clamp to the calibration ceiling).
    # The invariant holds on BOTH flag paths.
    if score_a is not None and score_b is not None and winner_index in (0, 1):
        from app.services.scoring_service import (
            _CALIBRATION_FLOOR as _floor,
            _CALIBRATION_CEILING as _ceil,
        )
        win_score = score_a if winner_index == 0 else score_b
        los_score = score_b if winner_index == 0 else score_a
        if win_score <= los_score:  # tie or inverted — must separate
            if win_score <= _floor:
                # Can't push the loser below the floor → raise the winner instead.
                new_win = min(_ceil, los_score + 1)
            else:
                new_win = win_score  # winner stays honest; lower the loser below it
            new_los = max(_floor, min(los_score, new_win - 1))
            if winner_index == 0:
                score_a, score_b = new_win, new_los
            else:
                score_b, score_a = new_win, new_los
    dimensions = build_dimensions_v2(product_data, scoring_result, category)
    # Bundle C § 1b A.3.2 — compose factual_verdict from existing fields.
    # Pure template, zero GPT cost. qa-bundle-c D.1.3 confirmed missing.
    factual_verdict = _build_factual_verdict(
        product_data, scoring_result, winner_index, dimensions
    )
    # Lane 1 L1.6 — surface the existing per-leg confidence on scoring_v2
    # so the design Screen 1 confidence pills + tap-to-reveal sheet can
    # read the data directly off the v2 payload. Mirrors
    # `overview.confidence` — the upstream `compute_confidence(...)` call
    # in structured_comparison_service already computes the legs + per-
    # leg evidence dicts; we just thread them through.
    confidence_legs, confidence_details = _confidence_legs_and_details(product_data)
    # S3 L3.4 — surface the qualitative winner_evidence the scoring layer
    # produced (L3.2 price authority + L3.3 review density). Always a list of
    # short strings (never coefficients/caps/% per no_backend_internals_in_reveals);
    # coerce defensively so a malformed scoring_result can't ship a non-list.
    raw_evidence = scoring_result.get("winner_evidence")
    winner_evidence = (
        [str(e) for e in raw_evidence] if isinstance(raw_evidence, list) else []
    )
    scoring_v2 = {
        "overall_score": {
            "product_a": score_a,
            "product_b": score_b,
            "winner_idx": winner_index,
        },
        "win_margin": abs(score_a - score_b),
        "dimensions": dimensions,
        "factual_verdict": factual_verdict,
        # S3 L3.4 — qualitative reasons backing the winner pick (price
        # authority / Bahrain availability / review density). Empty list when
        # the comparison had no discriminating real-data evidence.
        "winner_evidence": winner_evidence,
        # Bundle C v1 hot-fix (round 2) — HeroRings.tsx reads
        # scoring_v2.comparison_quality per spec § 2e for weird-mode em-dash.
        # Also surface in scoring_v2 (in addition to metadata.comparison_quality
        # from the first hot-fix round) so both consumers see it.
        "comparison_quality": _safe_detect_comparison_quality(product_data),
        # Bundle C v1 hot-fix (round 2) — spec § 7b: scoring_v2.personalization
        # contains the chip's applied_shifts contract. ALWAYS emit the
        # personalization wrapper with applied_shifts as a list (empty
        # when no priorities/no shifts) so the frontend can iterate
        # safely.
        "personalization": {
            "applied_shifts": _safe_compute_applied_shifts(scoring_result),
        },
        # Lane 1 L1.6 — confidence_legs is the pill-row enum dict
        # ({price/reviews/specs: strong|acceptable|weak}); confidence_details
        # exposes the per-leg evidence (source counts, methods, review
        # counts, verified spec %).
        "confidence_legs": confidence_legs,
        "confidence_details": confidence_details,
    }

    # Bundle C § 1b diagnostic — log when scoring_v2 ships without a populated
    # factual_verdict (current state per § 1b — builder missing entirely).
    # Confirms whether the builder is genuinely absent vs gated by a flag,
    # and surfaces winner + price/rating context to diagnose root cause.
    if _factual_verdict_diag_enabled() and not _factual_verdict_present_in_scoring_v2(scoring_v2):
        try:
            product_summary = [
                (
                    p.get("name"),
                    (p.get("price") or {}).get("amount") if isinstance(p.get("price"), dict) else p.get("price"),
                    p.get("rating"),
                )
                for p in product_data
            ]
        except Exception:  # noqa: BLE001 — diagnostic must never raise
            product_summary = "<unavailable>"
        logger.warning(
            "FACTUAL_VERDICT_DIAGNOSTIC scoring_v2_emitted_without_factual_verdict winner_index=%s products=%s",
            winner_index,
            product_summary,
        )

    return scoring_v2


def build_comparison_response(
    *,
    product_data: Optional[List[Dict[str, Any]]] = None,
    products: Optional[List[Dict[str, Any]]] = None,
    comparison: Optional[Dict[str, Any]] = None,
    scoring_result: Optional[Dict[str, Any]] = None,
    product_names: Optional[List[str]] = None,
    tradeoffs: Optional[List[Dict]] = None,
    confidence: Optional[Dict] = None,
    verdict_validation: Optional[Dict] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    from_cache: bool = False,
    query: str = "",
    region: str = "bahrain",
    category_used: str = "",
    category_switched: bool = False,
    original_category: Optional[str] = None,
    total_cost: float = 0.0,
    api_calls: int = 0,
    gpt_calls: int = 0,
    serper_calls: int = 0,
    elapsed_seconds: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
    cohort_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the full structured comparison response.

    This is used by both compare_from_text() and compare_from_text_streaming()
    to avoid duplicating ~100 lines of response assembly.

    Bundle D Task 2.B.1 (B.0):
    - `products` is accepted as an alias for `product_data` (FE-friendly
      naming). Pass either; if both are passed `products` wins.
    - `metadata` kwarg accepts a dict whose keys are merged onto the
      auto-built `response["metadata"]` after assembly. Callers can use
      it to inject overrides like `{"comparison_quality": "weird"}`
      without unpicking the full positional spec.
    - All other positional-style params now have defaults so a minimal
      call (just `products` + `comparison`) works for unit tests and
      lightweight callers. Production callers still pass everything.

    Phase 3.1 — `cohort_summary` ({"peer_count": int, "governorate": str})
    is attached at the response ROOT when present and shape-valid. The FE
    ResultsScreen reads `result.cohort_summary` to render the cohort proof
    line ("N shoppers in {governorate} leaned the same way"). The orchestrator
    decides WHEN to pass it (gated by ENABLE_COHORT_PERSONALIZATION + cohort
    match quality via _build_cohort_summary); the builder defensively
    re-validates so a malformed/zero/blank value is OMITTED (the badge hides
    when peer_count <= 0 or governorate is blank).
    """
    # Resolve product_data / products alias
    if products is not None and product_data is None:
        product_data = products
    if product_data is None:
        product_data = []

    # Provide safe defaults for the dict-shape kwargs
    if comparison is None:
        comparison = {}
    if scoring_result is None:
        scoring_result = {}
    if product_names is None:
        product_names = [p.get("name", "") for p in product_data]
    if tradeoffs is None:
        tradeoffs = []
    if confidence is None:
        confidence = {}
    if verdict_validation is None:
        verdict_validation = {}
    # H1 fix: prefer the deterministic scoring winner over GPT's. GPT's
    # comparison["winner_index"] is prose-derived and can disagree with the
    # calibrated math, which previously caused a visible contradiction
    # between overview.winner.product_index (was GPT) and
    # scoring_v2.overall_score.winner_idx (always deterministic). Fall back
    # to GPT only when scoring did not produce a winner (legacy fixtures
    # or scoring-disabled mode).
    _scoring_winner = scoring_result.get("winner_index")
    _gpt_winner = comparison.get("winner_index", 0)
    if _scoring_winner is not None:
        winner_index = _scoring_winner
        if _scoring_winner != _gpt_winner:
            # Surface the disagreement so we can audit how often the GPT
            # verdict prose names a different winner than the score. Low
            # volume (only fires on mismatch); not flag-gated for now.
            logger.warning(
                "WINNER_INDEX_MISMATCH scoring=%s gpt=%s "
                "win_margin=%s — using deterministic scoring",
                _scoring_winner,
                _gpt_winner,
                scoring_result.get("win_margin", 0),
            )
    else:
        winner_index = _gpt_winner
    win_margin = scoring_result.get("win_margin", 0)

    # S3 L3 v2 (e) — GPT-qualitative-winner as a GROUNDED CROSS-CHECK LOG ONLY.
    # The shipped winner is ALWAYS the genuine deterministic argmax (the GPT
    # verdict EXPLAINS it). When ENABLE_GPT_WINNER is ON and the GPT verdict's
    # GROUNDED independent winner DISAGREES with the deterministic winner, LOG it
    # (like WINNER_INDEX_MISMATCH) for S3.1 investigation — NO index override
    # (override creates the consistency trap the v2 pivot removed). Default OFF.
    if _gpt_winner_lever_enabled():
        indep = _grounded_gpt_winner(comparison)
        if indep is not None and indep != winner_index:
            logger.info(
                "GPT_WINNER_DISAGREES deterministic=%s gpt_independent=%s grounded=true basis=%r",
                winner_index, indep,
                (comparison.get("independent_winner_basis") or "")[:120],
            )

    # Build personalization metadata
    personalized = user_preferences is not None and bool(user_preferences)
    personalization_factors = []
    if personalized:
        for p in user_preferences.get("priorities", []):
            personalization_factors.append(f"priority_{p}")
        if user_preferences.get("budget"):
            personalization_factors.append(f"budget_{user_preferences['budget']}")
        for tag in user_preferences.get("lifestyle", []):
            personalization_factors.append(f"lifestyle_{tag}")

    # Derive ratings for products with no real ratings
    for i, pd_item in enumerate(product_data):
        if pd_item.get("rating") is None:
            key = f"product_{i}"
            overall = scoring_result.get("scores", {}).get(key, {}).get("overall", MISSING_SCORE)
            pd_item["rating"] = derive_rating_from_scores(overall)
            pd_item["rating_derived"] = True

    # Bundle D Task 2.B.2 (A.7.2) — defense-in-depth: strip the `note`
    # field from price objects whose source_method is "estimated".
    # Frontend already silences "Estimated from training data" copy per
    # Bundle C `ca84eff`, but backend should not ship the string at all
    # when the source is Tier 3 GPT fallback. Keeps the source_method
    # enum value (consumed by analytics + admin dashboards) untouched —
    # only the user-rendered `note` text is removed.
    for pd_item in product_data:
        _price = pd_item.get("price")
        if isinstance(_price, dict) and _price.get("source_method") == "estimated":
            if "note" in _price:
                _price["note"] = None

    # Task C1 — price-pending presentation. A resolved price that is NOT
    # genuine/showable (estimated, fails an accuracy guard, or a
    # sample/decant listing) must NOT surface a misleading amount. Normalize
    # it to the price-pending shape so the FE (Phase 4) renders a "pricing in
    # a future update" line. This is the SINGLE chokepoint shared by both the
    # sync and streaming paths (build_comparison_response), so the rule is
    # applied consistently. Showable prices (genuine BHD + a real converted_usd)
    # pass through unchanged. Nulling the amount also makes _dim_price /
    # _dim_value (built below via _build_scoring_v2) take their honest
    # missing-data path, so no cross-price delta is asserted on a pending price.
    try:
        from app.services.price_service import is_price_showable, make_pending_price
        for pd_item in product_data:
            _name = pd_item.get("full_name") or pd_item.get("name") or ""
            _price = pd_item.get("price")
            if not isinstance(_price, dict):
                continue
            # An upstream pass (e.g. Task C2 size-basis reconciliation in the
            # orchestrator) may already have marked this price pending with its
            # OWN reason (size_mismatch). Don't clobber that reason — it's
            # already non-showable and correctly shaped.
            if _price.get("unavailable") is True:
                continue
            if not is_price_showable(_name, _price):
                pd_item["price"] = make_pending_price(
                    currency=_price.get("currency") or "BHD",
                    reason="pending_genuine",
                    size=_price.get("size"),
                )
                # Keep best_price/currency/retailer mirrors honest.
                pd_item["best_price"] = None
                if "retailer" in pd_item:
                    pd_item["retailer"] = None
    except Exception:  # noqa: BLE001 — price-pending must never crash the response
        logger.warning("price-pending normalization skipped", exc_info=True)

    # Detect price method mismatch
    price_methods = [p.get("price", {}).get("source_method") for p in product_data if p.get("price")]
    unique_methods = set(m for m in price_methods if m)

    # value_context: per-product dict (preferred) with legacy-string fallback.
    # Bug fix: previously a single comparison-level string was fanned out to
    # every product slot, producing identical text on each product card.
    raw_value_context = comparison.get("value_context", "")
    if isinstance(raw_value_context, dict):
        def _value_context_for(idx: int) -> str:
            return raw_value_context.get(f"product_{idx}", "") or ""
    else:
        # Legacy comparison-level string — both products share it (old behaviour
        # preserved for fixtures and pre-prompt-update payloads).
        _legacy_vc = raw_value_context if isinstance(raw_value_context, str) else ""
        def _value_context_for(idx: int) -> str:  # noqa: E306 — single-purpose helper
            return _legacy_vc

    result = {
        "success": True,
        "query": query,
        "category": category_used,
        "category_switched": category_switched,
        "original_category": original_category,

        "overview": {
            "winner": {
                "product_index": winner_index,
                "name": comparison.get("winner_declaration", product_names[winner_index] if product_names else ""),
                "declaration": comparison.get("winner_declaration", ""),
                "reason": comparison.get("winner_reason", ""),
                "key_tradeoff": comparison.get("key_tradeoff", ""),
                "margin": win_margin,
            },
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    # Lane 1 L1.7 — short variant tag like '128GB · Black'.
                    # Empty string when no hooks fire (FE renders title alone).
                    "variant": _compose_variant_string(pd, category_used),
                    "price": pd.get("price"),
                    "rating": pd.get("rating"),
                    "review_count": pd.get("review_count"),
                    "overall_score": scoring_result.get("scores", {}).get(f"product_{i}", {}).get("overall"),
                    "value_badge": pd.get("value_badge", "fair_price"),
                    "value_context": _value_context_for(i),
                    "pros": pd.get("pros_cons", {}).get("pros", []) if isinstance(pd.get("pros_cons"), dict) else [],
                    "cons": pd.get("pros_cons", {}).get("cons", []) if isinstance(pd.get("pros_cons"), dict) else [],
                    # Lane 1 L1.8 — explicit accordion block for design Screen 1.
                    # FE stars the winner side via `is_winner`. Kept additive
                    # alongside legacy `pros` / `cons` flat keys for one
                    # release; consumers can migrate at their own pace.
                    "pros_cons": _build_pros_cons_block(pd, is_winner=(i == winner_index)),
                    "best_for": comparison.get("best_for", {}).get(f"product_{i}", ""),
                    # Bundle E S3 — per-product image URL (Tier cascade
                    # resolved upstream in _fetch_product_data Phase 1).
                    # String when any tier hit; None when all tiers exhausted
                    # (frontend renders placeholder primitive).
                    "image_url": pd.get("image_url"),
                    # Bundle D A.6.4 — per-product budget-fit indicator.
                    # 'match' / 'near' / 'mismatch' / 'unknown'.
                    # price_tiers map is keyed by "{brand} {name}".strip()
                    # per scoring_service:price_tiers_map construction.
                    "value_match": _compute_value_match(
                        scoring_result.get("price_tiers", {}).get(
                            f"{pd.get('brand', '')} {pd.get('name', '')}".strip(),
                            "",
                        ),
                        (user_preferences or {}).get("budget"),
                    ),
                    # S3 L3 v2 — raw scoring inputs for the offline param sweep,
                    # emitted ONLY when EVAL_CAPTURE_DEBUG is set (the one capture
                    # run). None otherwise → key carries None in normal prod; FE
                    # ignores unknown keys. Kept additive + last so it never
                    # shifts the user-facing shape.
                    "_debug_capture": (
                        _debug_capture_payload(pd) if _eval_capture_debug_enabled() else None
                    ),
                }
                for i, pd in enumerate(product_data)
            ],
            "tradeoffs": tradeoffs,
            "confidence": confidence,
        },

        "specs": {
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "specs": pd.get("specs"),
                    "spec_advantages": comparison.get("specs_comparison", {}).get(f"product_{i}_advantages", []),
                }
                for i, pd in enumerate(product_data)
            ],
            # Lane 1 L1.9 — augment specs_comparison with `rows` list so
            # design Screen 4 can render the per-row table with emerald
            # winner highlighting. Existing `product_0_advantages`,
            # `product_1_advantages`, `similar` keys remain (additive).
            "specs_comparison": {
                **(comparison.get("specs_comparison") or {}),
                "rows": _build_specs_rows(product_data),
            },
        },

        "reviews": {
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "rating": pd.get("rating"),
                    "review_count": pd.get("review_count"),
                    "rating_source": pd.get("rating_source"),
                    # L2 per-race timeout sets pd['reviews']=None on TimeoutError;
                    # the legacy `.get("reviews", {})` returns None (not {}) when
                    # the key is PRESENT with None value, then .get('review_summary')
                    # raises AttributeError. (X or {}).get(...) coalesces None→{}.
                    # Regression: PYTHON-FASTAPI-J event ecaa64acab224c599c9aba3bb92dfc89.
                    "review_summary": (pd.get("reviews") or {}).get("review_summary", {
                        "overall_sentiment": "mixed",
                        "consensus": "",
                        "highlights": [],
                        "review_volume": "minimal",
                        "agreement_level": "moderate",
                    }),
                    # ITEM 1 — up to 3 per-source review quotes the FE Reviews
                    # accordion renders as compact AMAZON ★★★★★ "quote" lines.
                    # Built in _fetch_product_data from REAL organic snippets
                    # (no fabricated ratings); [] when none could be attributed
                    # (FE falls back to highlights, then a calm empty line).
                    "retailer_quotes": (pd.get("reviews") or {}).get("retailer_quotes", []),
                    # Faithful-Results Phase 5 (Contract 2) — synthesized praise
                    # line (non-verbatim, no citations/domains), mirrored here for
                    # streaming/section parity (canonical home is products[i]).
                    # None when no positive signal — FE branches on presence and
                    # stops rendering retailer_quotes/highlights for this surface.
                    "review_praise": _safe_review_praise(pd),
                    # S3 L2 — cited YouTube review signal (flag-gated). None
                    # when ENABLE_YOUTUBE_SOURCE OFF / no signal. Frontend
                    # renders "~N views · top video by <channel>" as a cited
                    # review source; never the word "estimated", always cited.
                    "youtube_review_signal": _youtube_signal_for_response(pd),
                }
                for pd in product_data
            ],
        },

        "scoring": {
            "scores": scoring_result.get("scores", {}),
            "dimension_winners": scoring_result.get("dimension_winners", {}),
            "price_tiers": scoring_result.get("price_tiers", {}),
            "is_cross_tier": scoring_result.get("is_cross_tier", False),
            "scoring_method": scoring_result.get("scoring_method", "category_weighted"),
            "category_weights": scoring_result.get("category_weights", {}),
        },

        "scoring_v2": _build_scoring_v2(product_data, scoring_result, category_used, winner_index),

        "personalization": {
            "personalized": personalized,
            "factors": personalization_factors,
            "personalized_insights": comparison.get("personalized_insights", []),
            # Bundle C § 7b A.9.1 hot-fix — wire _compute_applied_shifts so
            # the personalization chip can read the qualitative direction
            # arrows. Empty list (NOT None) when no priorities set OR no
            # significant shifts — chip hides itself naturally.
            "applied_shifts": _safe_compute_applied_shifts(scoring_result),
        },

        "metadata": {
            "query": query,
            "region": region,
            "elapsed_ms": round(elapsed_seconds * 1000),
            "elapsed_seconds": round(elapsed_seconds, 2),
            "api_calls": api_calls,
            "total_cost": round(total_cost, 6),
            "gpt_calls": gpt_calls,
            "serper_calls": serper_calls,
            "cached": from_cache,
            "fact_check": {
                "product_0": (product_data[0].get("fact_check", {}) if len(product_data) > 0 else {}),
                "product_1": (product_data[1].get("fact_check", {}) if len(product_data) > 1 else {}),
            },
            "verdict_validation": verdict_validation,
            "timestamp": datetime.now().isoformat(),
            # Bundle C § 2e A.4.5 hot-fix — wire detect_comparison_quality so
            # the frontend can adapt verdict framing without a UI banner.
            # Returns 'normal' | 'weak' | 'weird' per spec § 2e triggers.
            "comparison_quality": _safe_detect_comparison_quality(product_data),
            # Bundle D A.6.5 — bundle-level flag for FE caption rendering.
            # True when the WINNER's price tier is two or more tiers off
            # the user's stated budget preference. False when user has no
            # budget set, winner tier unknown, or tiers align within ±1.
            "budget_mismatch": _compute_budget_mismatch(
                scoring_result.get("price_tiers", {}).get(
                    f"{product_data[winner_index].get('brand', '')} {product_data[winner_index].get('name', '')}".strip(),
                    "",
                ) if product_data and 0 <= winner_index < len(product_data) else "",
                (user_preferences or {}).get("budget"),
            ),
            # S2 I3.6 — missing-dimension coverage metric. Counts the
            # MISSING_SCORE cells across both products' per-dim breakdowns
            # (the genuine data gap BEFORE display omission). The KPI dial
            # for Ahmed's Decision B "no missing data / no false certainty";
            # the eval runner aggregates this per-run so the Tier-3 fill's
            # reduction is measured, not asserted.
            "missing_dim_cells": count_missing_dim_cells(
                scoring_result or {}, category_used
            ),
            # Faithful-Results Task 1.6 — per-response cache hit-rate signal:
            # cache_hit (any price from cache) + genuine_from_cache (a genuine-BH
            # price served from cache — the warmer-working dial). Spread so both
            # keys land directly on metadata.
            **_compute_cache_observability(product_data),
        },
    }

    # Bundle D Task 2.B.1 (B.0) — merge caller-supplied `metadata` overrides
    # onto the auto-built metadata block. Caller wins on conflicting keys,
    # so a test or future analytics-injecting caller can override values
    # like `comparison_quality` directly without unpicking the full
    # positional spec. Same merge pattern as Pydantic model_dump-style
    # partial updates — keys not in the override are left untouched.
    if metadata:
        result["metadata"].update(metadata)

    # Phase 3.1 — cohort proof line. Attach `cohort_summary` at the response
    # ROOT only when the orchestrator resolved a real cohort match AND the
    # shape is renderable (peer_count > 0, non-blank governorate). The
    # CohortBadge on ResultsScreen hides when peer_count <= 0 or !governorate,
    # so we OMIT the key entirely in those cases rather than ship a zero line.
    # Defensive re-validate here keeps a malformed orchestrator value from ever
    # reaching the FE; the orchestrator's _build_cohort_summary owns the
    # ENABLE_COHORT_PERSONALIZATION + match-quality gating.
    if isinstance(cohort_summary, dict):
        _peer_count = cohort_summary.get("peer_count")
        _gov = cohort_summary.get("governorate")
        if (
            isinstance(_peer_count, int)
            and not isinstance(_peer_count, bool)
            and _peer_count > 0
            and isinstance(_gov, str)
            and _gov.strip()
        ):
            result["cohort_summary"] = {
                "peer_count": _peer_count,
                "governorate": _gov,
            }

    # Backward compatibility aliases
    # Bundle C v1.1 § 1a defensive — the canonical v2 path
    # `overview.products[i].pros / .cons` is already flat (lines
    # 533-534 project from `pros_cons`). But this legacy alias ships
    # the RAW `product_data` list which has `pros_cons` NESTED only —
    # no flat `pros`/`cons` keys. qa's parser-ambiguity confusion this
    # session traced to a consumer reading `response.products[*].pros`
    # (legacy path) and getting undefined → 0. Project flat keys onto
    # each product_data dict in-place BEFORE alias assignment so both
    # paths agree. Idempotent — honors pre-set flat values; only
    # fills from `pros_cons` when the flat key is absent. Nested
    # `pros_cons` retained for any consumer that already reads it.
    for pd in product_data:
        if "pros" not in pd:
            pd["pros"] = (pd.get("pros_cons") or {}).get("pros") or []
        if "cons" not in pd:
            pd["cons"] = (pd.get("pros_cons") or {}).get("cons") or []
        # Bundle E S3 — ensure image_url is present (None when missing) so
        # FE consumers using the legacy `products` alias path don't see
        # KeyError; mirror the canonical `overview.products[*].image_url`.
        if "image_url" not in pd:
            pd["image_url"] = None
        # Faithful-Results Phase 5 (Contract 2) — synthesized review praise line
        # (non-verbatim, no citations, no domains) + a canonical real-only
        # rating_count. review_praise is None when there's no positive signal
        # (FE branches on presence). Built from the reviews the pipeline already
        # has — zero extra API calls; ratings never fabricated.
        pd["review_praise"] = _safe_review_praise(pd)
        if "rating_count" not in pd:
            pd["rating_count"] = pd.get("review_count")
    result["products"] = product_data
    result["comparison"] = comparison
    result["recommendation"] = comparison.get("winner_reason", "")
    result["key_differences"] = []
    result["winner_index"] = winner_index
    result["category_used"] = category_used
    result["personalized"] = personalized
    result["personalization_factors"] = personalization_factors
    result["personalized_insights"] = comparison.get("personalized_insights", [])
    result["price_method_mismatch"] = len(unique_methods) > 1
    result["tier_context"] = {
        "price_tiers": scoring_result.get("price_tiers", {}),
        "is_cross_tier": scoring_result.get("is_cross_tier", False),
    }

    return result
