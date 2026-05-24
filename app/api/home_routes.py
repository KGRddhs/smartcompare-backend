"""Home screen editorial-section endpoints (Bundle D Phase 2.5).

Three GET endpoints under `/api/v1/home/*` that power the new editorial
HomeScreen sections shipped in Bundle D Phase 2.F.2:

  /home/savings     — aggregate winner-vs-loser BHD savings for SavingsBanner
  /home/smart-pick  — personalized winner story for SmartPickCard
  /home/trending    — region-aware trending product-pair queries (curated)

All endpoints:
- require auth via `Depends(get_current_user)` (except /trending which is
  auth-optional via `Depends(get_optional_user)` so non-auth users on the
  Splash → Home flow still see region defaults)
- read from `comparisons` rows filtered to `schema_version=2` (Migration
  020 invariant — never include legacy v1 rows that bypassed the
  `_validate_renderable` write-side check)
- cache results in Redis (per-user 5min for savings + smart-pick; global
  per-region 1h for trending)
- return safe defaults / empty-state on degraded data — frontend never
  needs to defensively check for null at top-level

Trending privacy: Approach A (curated JSON at `data/trending_curated.json`)
chosen over Approach B (search_logs k-anonymity aggregation) per the
Bundle D dispatcher direction. Zero PII surface; admin updates list
weekly via PR. See `docs/plans/bundle-d-followups.md` for the Bundle E
followup on Approach B (k-anonymity threshold + PII regex filter).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth_routes import get_current_user, get_optional_user
from app.middleware.rate_limiter import limiter
from app.services.cache_service import _redis_get, _redis_set
from app.services.database_service import (
    get_admin_supabase_client,
    get_user_supabase_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/home", tags=["home"])

# -----------------------------------------------------------------------------
# Cache TTLs per dispatcher spec
# -----------------------------------------------------------------------------
_SAVINGS_TTL_SECONDS = 5 * 60        # per-user 5min
_SMART_PICK_TTL_SECONDS = 5 * 60     # per-user 5min
_TRENDING_TTL_SECONDS = 60 * 60      # global per-region 1h

# Frontend caption gate per dispatcher: hide SavingsBanner when count < 3.
_SAVINGS_BANNER_THRESHOLD = 3

# Curated trending list — Approach A (zero PII surface). Admin updates
# via PR; weekly refresh cadence.
_TRENDING_CURATED_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "trending_curated.json"
)

# Default region when user/query doesn't specify one.
_DEFAULT_REGION = "bahrain"
_VALID_REGIONS = {"bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"}


def _safe_float(value: Any) -> Optional[float]:
    """Cast jsonb numeric → float, returning None on garbage input."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_winner_loser_prices(full_response: dict) -> tuple[Optional[float], Optional[float]]:
    """Return (winner_price_bhd, loser_price_bhd) from a renderable v2 row.

    Falls back to (None, None) on any shape gap — the caller filters
    None values out of the aggregate so a single malformed row doesn't
    corrupt the savings total.
    """
    if not isinstance(full_response, dict):
        return (None, None)
    products = full_response.get("products") or []
    if not isinstance(products, list) or len(products) < 2:
        return (None, None)
    winner_idx = full_response.get("winner_index")
    if winner_idx not in (0, 1):
        return (None, None)
    loser_idx = 1 - winner_idx
    winner_price = (products[winner_idx] or {}).get("price") or {}
    loser_price = (products[loser_idx] or {}).get("price") or {}
    # We only aggregate BHD prices — mixing currencies would require
    # conversion + dilutes the headline. v2 rows in current prod are
    # ~100% BHD per `comparisons` table inspection.
    if winner_price.get("currency") != "BHD" or loser_price.get("currency") != "BHD":
        return (None, None)
    return (_safe_float(winner_price.get("amount")), _safe_float(loser_price.get("amount")))


# =============================================================================
# 1. GET /api/v1/home/savings
# =============================================================================


@router.get("/savings")
@limiter.limit("30/minute")
async def home_savings(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Aggregate BHD savings + decision count for SavingsBanner.

    Returns:
        {
          "savings_bhd": float,         # SUM(max(loser_price - winner_price, 0))
          "decisions_count": int,       # COUNT(*) of v2 comparisons
          "threshold_met": bool,        # decisions_count >= 3
        }

    Frontend HIDES the SavingsBanner when `threshold_met=false` —
    avoids "you saved 0 BHD across 1 decision" for new users.

    Cache: 5min per-user Redis. ~30/min rate limit (defensive — this is
    a read-only endpoint, abuse vector is minimal).
    """
    user_id = current_user["id"]
    cache_key = f"home:savings:{user_id}"

    cached = _redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:  # noqa: BLE001 — never let stale cache crash
            logger.warning("[home/savings] stale cache for %s; recomputing", user_id)

    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )

    try:
        resp = (
            client.table("comparisons")
            .select("full_response")
            .eq("user_id", user_id)
            .eq("schema_version", 2)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("[home/savings] DB fetch failed for %s: %r", user_id, exc)
        # Fail-safe — don't 500; degrade to empty.
        rows = []

    total_savings = 0.0
    decisions_count = 0
    for row in rows:
        winner, loser = _extract_winner_loser_prices(row.get("full_response") or {})
        if winner is None or loser is None:
            continue  # row has shape gaps; skip from aggregate but still counted
        decisions_count += 1
        # max(0, ...) — never frame as negative savings (user chose pricier
        # winner: surfaced as 0 saved on that row, not -BHD).
        total_savings += max(0.0, loser - winner)

    payload = {
        "savings_bhd": round(total_savings, 2),
        "decisions_count": decisions_count,
        "threshold_met": decisions_count >= _SAVINGS_BANNER_THRESHOLD,
    }

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_SAVINGS_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[home/savings] cache write failed: %r", exc)

    return payload


# =============================================================================
# 2. GET /api/v1/home/smart-pick
# =============================================================================


def _select_smart_pick(
    priorities: list[str],
    comparisons: list[dict],
) -> Optional[dict]:
    """Pick the comparison whose winner's strongest dim aligns with the
    user's #1 priority. Falls back to "most recent v2 comparison" if no
    priority/dim match.

    Returns the shaped payload dict (without `reason_key` / `reason_params`
    — caller fills those in based on which branch fired) or None when
    no comparisons are eligible.
    """
    if not comparisons:
        return None

    user_top_priority = (priorities[0] if priorities else "").strip().lower()
    eligible: list[tuple[dict, str]] = []  # (comparison, reason_key)

    for comparison in comparisons:
        full = comparison.get("full_response") or {}
        if not isinstance(full, dict):
            continue
        winner_idx = full.get("winner_index")
        if winner_idx not in (0, 1):
            continue
        products = full.get("products") or []
        if len(products) < 2:
            continue
        loser_idx = 1 - winner_idx
        winner = products[winner_idx] or {}
        loser = products[loser_idx] or {}
        winner_price = (winner.get("price") or {}).get("amount")
        loser_price = (loser.get("price") or {}).get("amount")
        if winner_price is None or loser_price is None:
            continue

        # Priority-match check: does the winner's strongest scored dim
        # contain a substring of the user's #1 priority? The scoring is
        # under scoring.dimension_winners — keyed by dim name; the
        # winner appears as the value.
        scoring = full.get("scoring") or {}
        dim_winners = scoring.get("dimension_winners") or {}
        winner_name = f"{winner.get('brand', '')} {winner.get('name', '')}".strip()
        priority_match = False
        if user_top_priority:
            for dim_key, winner_label in dim_winners.items():
                if (
                    winner_label == winner_name
                    and user_top_priority in dim_key.lower()
                ):
                    priority_match = True
                    break

        reason_key = (
            "home.smart_pick.reason.priority_match"
            if priority_match
            else "home.smart_pick.reason.recent_winner"
        )
        eligible.append((comparison, reason_key))

    if not eligible:
        return None

    # Prefer priority-match results; if none matched, take the most-recent
    # eligible row (input order — caller passes desc by created_at).
    chosen = next(
        (c for c, r in eligible if r == "home.smart_pick.reason.priority_match"),
        eligible[0][0],
    )
    reason_key = next(
        (r for c, r in eligible if c is chosen),
        "home.smart_pick.reason.recent_winner",
    )

    full = chosen.get("full_response") or {}
    products = full.get("products") or []
    winner_idx = full.get("winner_index", 0)
    loser_idx = 1 - winner_idx
    winner = products[winner_idx]
    loser = products[loser_idx]

    return {
        "comparison_id": chosen.get("id"),
        "winner_name": f"{(winner.get('brand') or '').strip()} {(winner.get('name') or '').strip()}".strip(),
        "runner_up_name": f"{(loser.get('brand') or '').strip()} {(loser.get('name') or '').strip()}".strip(),
        "winner_price_bhd": _safe_float((winner.get("price") or {}).get("amount")),
        "runner_up_price_bhd": _safe_float((loser.get("price") or {}).get("amount")),
        "reason_key": reason_key,
        "reason_params": (
            {"priority": user_top_priority}
            if reason_key == "home.smart_pick.reason.priority_match"
            else {}
        ),
    }


@router.get("/smart-pick")
@limiter.limit("30/minute")
async def home_smart_pick(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Personalized winner story for SmartPickCard.

    Returns:
        {
          "smart_pick": {comparison_id, winner_name, runner_up_name,
                         winner_price_bhd, runner_up_price_bhd,
                         reason_key, reason_params} OR null,
          "empty_state": bool,
          "cta_text_key": str (only when empty_state=true)
        }

    Empty state when user has zero v2 comparisons OR all rows are
    malformed (no winner/loser/prices). Frontend renders the
    "Run your first comparison to unlock personalized picks" copy via
    the `cta_text_key`.

    Priority source: `users.preferences.priorities` (authoritative;
    Bundle D Phase 2.5 ack with dispatcher 2026-05-23). The `behavior_profile`
    in Supabase doesn't carry a `priorities` field — that field lives on
    `users.preferences.priorities` from onboarding step 9.

    Cache: 5min per-user Redis.
    """
    user_id = current_user["id"]
    cache_key = f"home:smart_pick:{user_id}"

    cached = _redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            logger.warning("[home/smart_pick] stale cache for %s; recomputing", user_id)

    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )

    # Step 1 — read user's priorities + most-recent 5 v2 comparisons in parallel
    priorities: list[str] = []
    comparisons: list[dict] = []

    try:
        user_resp = (
            client.table("users")
            .select("preferences")
            .eq("id", user_id)
            .single()
            .execute()
        )
        prefs = (user_resp.data or {}).get("preferences") or {}
        if isinstance(prefs, dict):
            raw = prefs.get("priorities") or []
            if isinstance(raw, list):
                priorities = [str(p) for p in raw[:3] if p]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[home/smart_pick] users prefs read failed for %s: %r", user_id, exc)

    try:
        comp_resp = (
            client.table("comparisons")
            .select("id, full_response, created_at")
            .eq("user_id", user_id)
            .eq("schema_version", 2)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        comparisons = comp_resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("[home/smart_pick] comparisons read failed for %s: %r", user_id, exc)

    pick = _select_smart_pick(priorities, comparisons)

    if pick is None:
        payload = {
            "smart_pick": None,
            "empty_state": True,
            "cta_text_key": "home.smart_pick.empty_cta",
        }
    else:
        payload = {
            "smart_pick": pick,
            "empty_state": False,
        }

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_SMART_PICK_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[home/smart_pick] cache write failed: %r", exc)

    return payload


# =============================================================================
# 3. GET /api/v1/home/trending
# =============================================================================


def _load_curated_trending() -> dict[str, list[dict]]:
    """Read the curated JSON file. Returns a region → list[entry] map.

    Each entry is `{query: str, view_count: int}`. The region key gates
    response shape — see /trending endpoint for the merge logic.

    Returns an empty dict if the file is missing or malformed — fail-safe
    so a missing file degrades to "no trending items" rather than 500.
    """
    try:
        if not _TRENDING_CURATED_PATH.exists():
            logger.warning(
                "[home/trending] curated JSON missing at %s — returning empty",
                _TRENDING_CURATED_PATH,
            )
            return {}
        with open(_TRENDING_CURATED_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return {}
        # Validate per-region entries
        cleaned: dict[str, list[dict]] = {}
        for region, entries in raw.items():
            if not isinstance(entries, list):
                continue
            valid_entries = []
            for e in entries:
                if not isinstance(e, dict):
                    continue
                q = e.get("query")
                vc = e.get("view_count")
                if not isinstance(q, str) or not isinstance(vc, int):
                    continue
                valid_entries.append({"query": q, "view_count": vc})
            cleaned[region] = valid_entries
        return cleaned
    except Exception as exc:  # noqa: BLE001
        logger.error("[home/trending] curated JSON load failed: %r", exc)
        return {}


@router.get("/trending")
@limiter.limit("60/minute")
async def home_trending(
    request: Request,
    region: Optional[str] = Query(
        None,
        description="GCC region key (bahrain, saudi_arabia, uae, kuwait, qatar, oman). "
                    "Defaults to bahrain when missing or unrecognized.",
    ),
    user: Optional[dict] = Depends(get_optional_user),  # auth-optional
):
    """Region-aware trending product pairs for TrendingNearYou.

    Returns:
        {
          "trending": [{query, view_count, region}, ...],
          "region": str (the resolved region key),
        }

    Auth-optional: non-authenticated users on the Splash → Home flow
    can still hit this endpoint and see region defaults.

    Region resolution:
      1. `?region=` query param (if in _VALID_REGIONS)
      2. Authenticated user's `preferences.region` (if set)
      3. Default `bahrain`

    Cache: 1h global per region (`home:trending:{region}`). Curated
    JSON is shared across all users in a region — no per-user fan-out.

    PRIVACY: This endpoint serves a CURATED list from
    `data/trending_curated.json`. Zero PII surface — admin updates the
    list weekly via PR. The alternative (k-anonymity aggregation of
    `search_logs`) is logged as Bundle E followup in
    `docs/plans/bundle-d-followups.md`.
    """
    # Resolve region with fallbacks
    resolved_region = (region or "").strip().lower()
    if resolved_region not in _VALID_REGIONS:
        # Try user preference fallback
        if user:
            access_token = user.get("access_token")
            client = (
                get_user_supabase_client(access_token) if access_token
                else get_admin_supabase_client()
            )
            try:
                user_resp = (
                    client.table("users").select("preferences")
                    .eq("id", user["id"]).single().execute()
                )
                user_region = (
                    ((user_resp.data or {}).get("preferences") or {}).get("region") or ""
                ).strip().lower()
                if user_region in _VALID_REGIONS:
                    resolved_region = user_region
            except Exception as exc:  # noqa: BLE001
                logger.warning("[home/trending] user-region fallback read failed: %r", exc)
        # Final fallback
        if resolved_region not in _VALID_REGIONS:
            resolved_region = _DEFAULT_REGION

    cache_key = f"home:trending:{resolved_region}"
    cached = _redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            logger.warning("[home/trending] stale cache for %s; recomputing", resolved_region)

    curated = _load_curated_trending()
    raw_entries = curated.get(resolved_region) or []
    # Final shape: attach `region` to each entry for FE clarity
    entries = [
        {"query": e["query"], "view_count": e["view_count"], "region": resolved_region}
        for e in raw_entries
    ]

    payload = {"trending": entries, "region": resolved_region}

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_TRENDING_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[home/trending] cache write failed: %r", exc)

    return payload
