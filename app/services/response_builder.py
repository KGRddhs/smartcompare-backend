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


def _factual_verdict_present_in_scoring_v2(scoring_v2: Dict[str, Any]) -> bool:
    """Return True iff scoring_v2 has a factual_verdict with line1 or line2.
    Used by the § 1b diagnostic and patchable from tests to simulate the
    post-A.3.2 populated state."""
    fv = scoring_v2.get("factual_verdict") if isinstance(scoring_v2, dict) else None
    if not isinstance(fv, dict):
        return False
    return bool(fv.get("line1")) or bool(fv.get("line2"))


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


def _format_line1(
    winner_name: str,
    candidate: Dict[str, Any],
) -> str:
    """Render the winner-anchored line1 from the largest-magnitude candidate.
    Strings are concise + presentational; honor the FIVE critical rules."""
    kind = candidate["kind"]
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
    candidates = [c for c in (
        _price_candidate(products, winner_index),
        _rating_candidate(products, winner_index),
        _top_dim_candidate(dimensions, winner_index),
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
    dimensions = build_dimensions_v2(product_data, scoring_result, category)
    # Bundle C § 1b A.3.2 — compose factual_verdict from existing fields.
    # Pure template, zero GPT cost. qa-bundle-c D.1.3 confirmed missing.
    factual_verdict = _build_factual_verdict(
        product_data, scoring_result, winner_index, dimensions
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
                    "price": pd.get("price"),
                    "rating": pd.get("rating"),
                    "review_count": pd.get("review_count"),
                    "overall_score": scoring_result.get("scores", {}).get(f"product_{i}", {}).get("overall"),
                    "value_badge": pd.get("value_badge", "fair_price"),
                    "value_context": _value_context_for(i),
                    "pros": pd.get("pros_cons", {}).get("pros", []),
                    "cons": pd.get("pros_cons", {}).get("cons", []),
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
            "specs_comparison": comparison.get("specs_comparison", {}),
        },

        "reviews": {
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "rating": pd.get("rating"),
                    "review_count": pd.get("review_count"),
                    "rating_source": pd.get("rating_source"),
                    "review_summary": pd.get("reviews", {}).get("review_summary", {
                        "overall_sentiment": "mixed",
                        "consensus": "",
                        "highlights": [],
                        "review_volume": "minimal",
                        "agreement_level": "moderate",
                    }),
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
