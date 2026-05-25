"""Profile screen editorial-section endpoints (Bundle D Phase 2.6).

Three GET endpoints under `/api/v1/profile/*` that power the new editorial
ProfileScreen sections shipped in Bundle D Phase 2.F.2 Screen 3:

  /profile/recent-decisions   — last 3 user comparisons as mini vs cards
  /profile/monthly-stats      — month-bounded count + savings + bonus credits
  /profile/priorities-weighted — 3 weighted priorities for PrioritiesInline bars

Symmetric with `app/api/home_routes.py` (Phase 2.5):
- all endpoints require auth via `Depends(get_current_user)`
- read from `comparisons` rows filtered to `schema_version=2` (Migration
  020 invariant — never include legacy v1 rows)
- cache results in 5min per-user Redis
- return safe defaults / empty-state on degraded data — frontend never
  needs to defensively check for null at top-level
- max(0, ...) clamp on savings — never frame negative savings

Architecture note: separate router from `home_routes.py` per dispatcher
2026-05-24 ack — semantic grouping (`/profile/*` vs `/home/*`) matches
how Frontend consumers split. Each file stays under ~250 lines.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request

from app.api.auth_routes import get_current_user
from app.middleware.rate_limiter import limiter
from app.services.cache_service import _redis_get, _redis_set
from app.services.database_service import (
    get_admin_supabase_client,
    get_user_supabase_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

# -----------------------------------------------------------------------------
# Cache TTLs per dispatcher spec — all 5min per-user
# -----------------------------------------------------------------------------
_RECENT_TTL_SECONDS = 5 * 60
_MONTHLY_STATS_TTL_SECONDS = 5 * 60
_PRIORITIES_TTL_SECONDS = 5 * 60

# Frontend hide gate per dispatcher: hide monthly-stats banner when count < 3.
_MONTHLY_STATS_THRESHOLD = 3


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_winner_loser_prices(full_response: dict) -> tuple[Optional[float], Optional[float]]:
    """Mirror of `home_routes._extract_winner_loser_prices` — extract
    (winner_bhd, loser_bhd) from a v2 full_response. Returns (None, None)
    on shape gaps; both products must be BHD (skip mixed-currency rows).
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
    if winner_price.get("currency") != "BHD" or loser_price.get("currency") != "BHD":
        return (None, None)
    return (_safe_float(winner_price.get("amount")), _safe_float(loser_price.get("amount")))


def _extract_product_names(full_response: dict) -> tuple[Optional[str], Optional[str]]:
    """Return (winner_name, runner_up_name) from a v2 full_response.

    Name format: "{brand} {name}".strip() (matches scoring_service +
    home_routes._select_smart_pick conventions).
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
    winner = products[winner_idx] or {}
    loser = products[loser_idx] or {}
    winner_name = f"{(winner.get('brand') or '').strip()} {(winner.get('name') or '').strip()}".strip()
    loser_name = f"{(loser.get('brand') or '').strip()} {(loser.get('name') or '').strip()}".strip()
    return (winner_name or None, loser_name or None)


# =============================================================================
# 1. GET /api/v1/profile/recent-decisions
# =============================================================================


@router.get("/recent-decisions")
@limiter.limit("30/minute")
async def profile_recent_decisions(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Last 3 user comparisons as mini vs cards.

    Returns:
        {
          "recent": [{comparison_id, winner_name, runner_up_name, created_at}, ...],
          "empty_state": bool,
          "cta_text_key": str (ONLY when empty_state=true)
        }

    Empty state when user has zero v2 comparisons. Frontend renders the
    "Run your first comparison" copy via `cta_text_key`.

    Cache: 5min per-user Redis.
    """
    user_id = current_user["id"]
    cache_key = f"profile_recent:{user_id}"

    cached = _redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            logger.warning("[profile/recent] stale cache for %s; recomputing", user_id)

    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )

    try:
        resp = (
            client.table("comparisons")
            .select("id, full_response, created_at")
            .eq("user_id", user_id)
            .eq("schema_version", 2)
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("[profile/recent] DB fetch failed for %s: %r", user_id, exc)
        rows = []

    recent = []
    for row in rows:
        winner_name, runner_up_name = _extract_product_names(row.get("full_response") or {})
        if not winner_name or not runner_up_name:
            continue
        recent.append({
            "comparison_id": row.get("id"),
            "winner_name": winner_name,
            "runner_up_name": runner_up_name,
            "created_at": row.get("created_at"),
        })

    if not recent:
        payload = {
            "recent": [],
            "empty_state": True,
            "cta_text_key": "profile.recent_decisions.empty_cta",
        }
    else:
        payload = {"recent": recent, "empty_state": False}

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_RECENT_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[profile/recent] cache write failed: %r", exc)

    return payload


# =============================================================================
# 2. GET /api/v1/profile/monthly-stats
# =============================================================================


def _month_start_utc_iso() -> str:
    """Return ISO-8601 timestamp for the first instant of the current
    UTC month. Used as the SQL gte() filter cutoff.

    Example: if today is 2026-05-24T12:00:00Z, returns
    '2026-05-01T00:00:00+00:00'.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start.isoformat()


def _current_month_key() -> str:
    """Return YYYY-MM string for the current UTC month.

    Used as the `month` field in the response so frontend can display
    "May 2026" or similar after looking up the EN/AR month name.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m")


@router.get("/monthly-stats")
@limiter.limit("30/minute")
async def profile_monthly_stats(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Month-bounded stat strip (decisions + savings + bonus credits).

    Returns:
        {
          "month": "2026-05",
          "decisions_count": int,
          "savings_bhd": float,                  # SUM(max(loser - winner, 0))
          "bonus_credits_this_month": int,       # SUM(loop2_comparisons_granted) this month
          "threshold_met": bool                  # decisions_count >= 3
        }

    Frontend HIDES the stat strip when `threshold_met=false` (consistent
    with home/savings pattern). Avoids "0 BHD across 1 decision" UX.

    bonus_credits_this_month sources from `referral_redemptions` table
    (loop2_comparisons_granted SUM, this-month-only by created_at).
    Per `referral_service.py:850` this is the canonical post-Loop-2-grant
    column. If query fails or table empty → 0 + Frontend hides credits.

    Cache: 5min per-user Redis.
    """
    user_id = current_user["id"]
    cache_key = f"monthly_stats:{user_id}"

    cached = _redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            logger.warning("[profile/monthly_stats] stale cache for %s; recomputing", user_id)

    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )

    month_start = _month_start_utc_iso()
    month_key = _current_month_key()

    # 1. comparisons this month — count + savings aggregate
    decisions_count = 0
    total_savings = 0.0
    try:
        resp = (
            client.table("comparisons")
            .select("full_response, created_at")
            .eq("user_id", user_id)
            .eq("schema_version", 2)
            .gte("created_at", month_start)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("[profile/monthly_stats] comparisons fetch failed for %s: %r", user_id, exc)
        rows = []

    for row in rows:
        winner, loser = _extract_winner_loser_prices(row.get("full_response") or {})
        if winner is None or loser is None:
            continue
        decisions_count += 1
        total_savings += max(0.0, loser - winner)

    # 2. bonus_credits_this_month — referral_redemptions Loop 2 grants
    bonus_credits = 0
    try:
        rr_resp = (
            client.table("referral_redemptions")
            .select("loop2_comparisons_granted, created_at")
            .eq("referrer_user_id", user_id)
            .gte("created_at", month_start)
            .execute()
        )
        rr_rows = rr_resp.data or []
        for row in rr_rows:
            granted = row.get("loop2_comparisons_granted")
            if isinstance(granted, int) and granted > 0:
                bonus_credits += granted
            elif isinstance(granted, (float, str)):
                try:
                    g = int(float(granted))
                    if g > 0:
                        bonus_credits += g
                except Exception:
                    pass
    except Exception as exc:  # noqa: BLE001
        # Fail-safe: degrade to 0 bonus credits. Frontend hides that portion.
        logger.warning(
            "[profile/monthly_stats] referral_redemptions fetch failed for %s: %r; "
            "bonus_credits_this_month=0",
            user_id, exc,
        )
        bonus_credits = 0

    payload = {
        "month": month_key,
        "decisions_count": decisions_count,
        "savings_bhd": round(total_savings, 2),
        "bonus_credits_this_month": bonus_credits,
        "threshold_met": decisions_count >= _MONTHLY_STATS_THRESHOLD,
    }

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_MONTHLY_STATS_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[profile/monthly_stats] cache write failed: %r", exc)

    return payload


# =============================================================================
# 3. GET /api/v1/profile/priorities-weighted
# =============================================================================


def _normalize_weights_to_100(raw_weights: dict[str, float]) -> dict[str, int]:
    """Scale a dict of float weights so the SUM is 100 (relative shares).

    B3 (Path A): previously scaled the MAX to 100 which made every bar
    read 100% in the uniform-fallback case. The "What shapes your matches"
    bars show RELATIVE share of priority weight — they should sum to ~100,
    not each read 100%. Rounding may produce small drift (sum 99-101);
    that's acceptable for a 3-bar display. Empty input → empty dict.
    """
    if not raw_weights:
        return {}
    non_null = {k: v for k, v in raw_weights.items() if v is not None}
    total = sum(non_null.values())
    if total <= 0:
        # All zero — uniform split across remaining keys
        if not non_null:
            return {}
        share = max(1, int(round(100 / len(non_null))))
        return {k: share for k in non_null}
    return {
        k: max(0, min(100, int(round((v / total) * 100))))
        for k, v in non_null.items()
    }


@router.get("/priorities-weighted")
@limiter.limit("30/minute")
async def profile_priorities_weighted(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """3 weighted priorities (0-100 bar values) for PrioritiesInline.

    Returns:
        {
          "priorities": [
            {"key": str, "label_key": "priorities.<key>", "weight": int 0-100},
            ...up to 3
          ],
          "empty_state": bool
        }

    Three-tier resolution (matches /home/smart-pick fallback pattern):
      1. PRIMARY  — `users.preferences.priorities` (top 3 user-stated list)
      2. WEIGHTS  — `users.behavior_profile.dimension_sensitivity` mapped
                    to priorities; if empty, uniform 100 across all priorities
      3. EMPTY    — both preferences.priorities AND dim_sensitivity empty/missing
                    → empty_state=true so Frontend hides the inline

    Cache: 5min per-user Redis.
    """
    user_id = current_user["id"]
    cache_key = f"priorities_weighted:{user_id}"

    cached = _redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            logger.warning("[profile/priorities] stale cache for %s; recomputing", user_id)

    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )

    priorities: list[str] = []
    dim_sens: dict[str, float] = {}

    try:
        user_resp = (
            client.table("users")
            .select("preferences, behavior_profile")
            .eq("id", user_id)
            .single()
            .execute()
        )
        user_row = user_resp.data or {}
        prefs = user_row.get("preferences") or {}
        if isinstance(prefs, dict):
            raw = prefs.get("priorities") or []
            if isinstance(raw, list):
                priorities = [str(p) for p in raw[:3] if p]
        bp = user_row.get("behavior_profile") or {}
        if isinstance(bp, dict):
            raw_sens = bp.get("dimension_sensitivity") or {}
            if isinstance(raw_sens, dict):
                for k, v in raw_sens.items():
                    try:
                        if v is not None:
                            dim_sens[str(k)] = float(v)
                    except (TypeError, ValueError):
                        continue
    except Exception as exc:  # noqa: BLE001
        logger.warning("[profile/priorities] users prefs read failed for %s: %r", user_id, exc)

    # Tier 3 — both empty → empty state
    if not priorities and not dim_sens:
        payload = {"priorities": [], "empty_state": True}
        try:
            _redis_set(cache_key, json.dumps(payload), ex=_PRIORITIES_TTL_SECONDS)
        except Exception:
            pass
        return payload

    # When preferences.priorities is empty but dim_sens has entries, synthesize
    # the top-3 dim_sens keys as the priority list (Tier 2 fallback symmetric
    # with /home/smart-pick).
    if not priorities and dim_sens:
        sorted_dims = sorted(dim_sens.items(), key=lambda kv: kv[1], reverse=True)
        priorities = [k for k, _ in sorted_dims[:3]]

    # Weighting:
    # - If dim_sens has entries for our priorities → use those raw weights
    # - Else uniform: every priority gets weight 1.0 (normalized → 100)
    raw_weights: dict[str, float] = {}
    for p in priorities:
        if p in dim_sens:
            raw_weights[p] = dim_sens[p]
        else:
            # Substring match — priority "camera_quality" matches dim
            # "camera_quality_score" (consistent with smart-pick logic)
            matched = next(
                (v for k, v in dim_sens.items() if p in k or k in p),
                None,
            )
            raw_weights[p] = matched if matched is not None else 1.0

    normalized = _normalize_weights_to_100(raw_weights)

    priorities_list = [
        {
            "key": p,
            "label_key": f"priorities.{p}",
            "weight": normalized.get(p, 100),
        }
        for p in priorities
    ]

    payload = {"priorities": priorities_list, "empty_state": False}

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_PRIORITIES_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[profile/priorities] cache write failed: %r", exc)

    return payload
