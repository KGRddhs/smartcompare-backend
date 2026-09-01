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

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth_routes import get_current_user, get_optional_user
from app.middleware.rate_limiter import limiter
from app.services.cache_service import _redis_get, _redis_offload_enabled, _redis_set
from app.services.database_service import (
    get_admin_supabase_client,
    get_user_supabase_client,
)
from app.utils.db_offload import run_db

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


def _home_savings_aggregate_enabled() -> bool:
    """Issue #116 — gate the SQL-side savings aggregate (migration 036).

    Read PER CALL via os.getenv (the db_offload.sync_db_offload_enabled idiom)
    so Railway can flip it without a redeploy. Default OFF: the legacy inline
    full_response scan runs, byte-identical to pre-#116 behaviour. Flip ONLY
    after migrations/036_home_savings_aggregate.sql has been applied — although
    flipping early is safe (the rpc failure logs and falls back to the inline
    scan), it pays an extra failed round trip per cache miss.
    """
    return os.getenv("ENABLE_HOME_SAVINGS_AGGREGATE", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


# ---------------------------------------------------------------------------
# Module-local Redis offload dispatch (M13-06 pattern, cache_service.py:540+:
# the dispatch MUST live in the calling module so a test patching
# `home_routes._redis_get` / `home_routes._redis_set` intercepts BOTH branches).
# Deliberately NOT scs._cache_get_async — that wraps get_cached, which
# json-decodes and returns None on JSONDecodeError, whereas this endpoint does
# its own json.loads inside a try that logs and RECOMPUTES on a decode failure.
# Flag OFF = inline call, identical semantics to the direct call.
# ---------------------------------------------------------------------------


async def _redis_get_async(key: str) -> Optional[str]:
    if _redis_offload_enabled():
        return await asyncio.to_thread(_redis_get, key)
    return _redis_get(key)


async def _redis_set_async(key: str, value: str, ex: int) -> bool:
    if _redis_offload_enabled():
        return await asyncio.to_thread(_redis_set, key, value, ex)
    return _redis_set(key, value, ex=ex)

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

    cached = await _redis_get_async(cache_key)
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

    payload: Optional[dict] = None
    if _home_savings_aggregate_enabled():
        # Issue #116 primary path: one SMALL round trip — Postgres computes the
        # SUM/COUNT over the jsonb price paths (migration 036), so cost no
        # longer grows with the user's comparison history and no full_response
        # blob crosses the wire. The blocking .execute() rides run_db so
        # ENABLE_SYNC_DB_OFFLOAD moves it off the event loop.
        payload = await _savings_via_sql_aggregate(client, user_id)

    if payload is None:
        # Legacy inline scan — the flag-OFF default (byte-identical to
        # pre-#116), and the safe degradation when the 036 migration has not
        # been applied yet (the rpc failure above logs and lands here — the
        # spec_spine_service fallback pattern: a deploy must not break on
        # unapplied DDL).
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
                continue  # row has shape gaps; skipped from BOTH the sum and the count
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
        await _redis_set_async(cache_key, json.dumps(payload), _SAVINGS_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[home/savings] cache write failed: %r", exc)

    return payload


async def _savings_via_sql_aggregate(client, user_id: str) -> Optional[dict]:
    """Call the migration-036 `home_savings_aggregate` rpc and shape the payload.

    Returns None on ANY failure (rpc missing because the migration has not been
    applied, network error, unexpected payload shape) so the caller degrades to
    the legacy inline scan — never a 500, never a silently-zeroed banner.

    The function is SECURITY INVOKER: called through the user-scoped client the
    comparisons RLS policy keeps the caller inside their own rows regardless of
    p_user_id; through the admin client the WHERE user_id filter does the work.
    """
    try:
        resp = await run_db(
            lambda: client.rpc(
                "home_savings_aggregate", {"p_user_id": user_id}
            ).execute()
        )
        data = resp.data
        if isinstance(data, list):
            row = data[0] if data else None
        elif isinstance(data, dict):
            row = data
        else:
            row = None
        if not isinstance(row, dict):
            raise ValueError(f"unexpected rpc payload shape: {type(data).__name__}")
        savings = float(row.get("savings_bhd") or 0.0)
        count = int(row.get("decisions_count") or 0)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[home/savings] SQL aggregate failed for %s "
            "(falling back to inline scan): %r",
            user_id, exc,
        )
        return None
    return {
        "savings_bhd": round(savings, 2),
        "decisions_count": count,
        "threshold_met": count >= _SAVINGS_BANNER_THRESHOLD,
    }


# =============================================================================
# 2. GET /api/v1/home/smart-pick
# =============================================================================


# Bundle E B4.3b — JSX-wins extension fields for /home/smart-pick.
#
# Keep the truncation budget tight (~140 chars target, 160 hard cap) so the
# verdict_short sentence fits the SmartPickCard footprint per JSX
# HomeScreen.jsx:483-489. The truncate routine prefers word boundaries to
# avoid mid-word chops; the trailing ellipsis is a single Unicode character
# (`…`) so total byte length stays predictable.
_VERDICT_SHORT_TARGET_CHARS = 140
_VERDICT_SHORT_HARD_CAP_CHARS = 160

# Sub-spec extraction: prefer storage/capacity for electronics, size for
# fashion, dosage for supplements, etc. Order matters — first match wins.
# When the source product has none of these keys, return None (frontend
# hides the sub line — per dispatcher rule no fabrication).
_SUB_SPEC_PRIORITY_KEYS = (
    "storage", "capacity", "size", "volume", "dosage",
    "weight", "memory", "ram",
)


def _truncate_verdict_short(text: str) -> Optional[str]:
    """Trim a winner_declaration to ~140 chars on a word boundary.

    Returns None when input is empty / not a string. Returns the full text
    when shorter than the target. Appends a single `…` (Unicode horizontal
    ellipsis) when truncated.
    """
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= _VERDICT_SHORT_TARGET_CHARS:
        return stripped
    # Truncate at last word boundary <= target chars
    cutoff = stripped[:_VERDICT_SHORT_HARD_CAP_CHARS]
    last_space = cutoff.rfind(" ", 0, _VERDICT_SHORT_TARGET_CHARS)
    if last_space <= 0:
        # No space within target window — hard chop at target.
        return cutoff[:_VERDICT_SHORT_TARGET_CHARS].rstrip() + "\u2026"
    return cutoff[:last_space].rstrip() + "\u2026"


def _extract_product_sub(full_response: dict, product_idx: int) -> Optional[str]:
    """Pull a short sub-label (e.g. '128GB') from a product's spec map.

    Reads `full_response.specs.products[idx].specs[<priority_key>]` in
    order of _SUB_SPEC_PRIORITY_KEYS; returns the first non-empty value
    stringified. Falls back to None when no priority key has a value
    (frontend hides the sub line — no fabrication).
    """
    if not isinstance(full_response, dict):
        return None
    specs_section = full_response.get("specs")
    if not isinstance(specs_section, dict):
        return None
    products = specs_section.get("products")
    if not isinstance(products, list) or product_idx >= len(products):
        return None
    pd = products[product_idx]
    if not isinstance(pd, dict):
        return None
    specs = pd.get("specs")
    if not isinstance(specs, dict):
        return None
    for key in _SUB_SPEC_PRIORITY_KEYS:
        value = specs.get(key)
        if value is None:
            continue
        # Stringify simple scalars only — never coerce dicts/lists into strings
        if isinstance(value, (str, int, float)):
            s = str(value).strip()
            if s:
                return s
    return None


def _format_updated_at(created_at_iso: Optional[str]) -> str:
    """Format `comparisons.created_at` as a short rel string for the
    SmartPickCard 'Updated …' chip per JSX HomeScreen.jsx:463-465.

    Outputs (server-computed so no clock-skew on device):
      < 1 min  → "Just now"
      < 1 hr   → "Xm ago"
      < 24 hr  → "Xh ago"
      < 7 day  → "Xd ago"
      ≥ 7 day  → "Older"

    NEVER returns raw ISO. Falls back to "Recently" on parse failure
    so the chip is always renderable (never null when the row exists).
    """
    if not isinstance(created_at_iso, str) or not created_at_iso.strip():
        return "Recently"
    from datetime import datetime, timezone
    try:
        # Supabase returns ISO with `Z` suffix or `+00:00`. fromisoformat()
        # supports the latter; coerce `Z` → `+00:00` for Python 3.10 compat.
        iso = created_at_iso.strip()
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:  # noqa: BLE001
        return "Recently"
    if elapsed < 60:
        return "Just now"
    if elapsed < 3600:
        return f"{int(elapsed // 60)}m ago"
    if elapsed < 86400:
        return f"{int(elapsed // 3600)}h ago"
    if elapsed < 86400 * 7:
        return f"{int(elapsed // 86400)}d ago"
    return "Older"


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

    # Bundle E B4.3b — JSX-wins extension fields. Each is null-when-absent
    # so the frontend hides the surround per dispatcher rule.
    category_raw = full.get("category")
    category = category_raw.strip() if isinstance(category_raw, str) and category_raw.strip() else None

    winner_declaration = (
        ((full.get("overview") or {}).get("winner") or {}).get("declaration")
    )
    verdict_short = _truncate_verdict_short(winner_declaration)

    winner_sub = _extract_product_sub(full, winner_idx)
    runner_up_sub = _extract_product_sub(full, loser_idx)

    updated_at = _format_updated_at(chosen.get("created_at"))

    # Bundle E S3 A3 — extract per-product image_url from the source
    # comparison row's `products[*].image_url`. Returns the string when it's
    # a valid http(s) URL; null otherwise (FE renders placeholder primitive).
    # Rejects non-string types defensively (legacy malformed rows can hold
    # ints / dicts / lists; we don't pass through bad shapes).
    def _safe_image_url(product: dict) -> Optional[str]:
        raw = product.get("image_url") if isinstance(product, dict) else None
        if not isinstance(raw, str):
            return None
        stripped = raw.strip()
        if not (stripped.startswith("http://") or stripped.startswith("https://")):
            return None
        return stripped

    return {
        # Legacy fields (one release cycle — same pattern as scoring_v2)
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
        # Bundle E B4.3b — JSX-driven extension fields (null-when-absent)
        "category": category,
        "updated_at": updated_at,
        "winner_sub": winner_sub,
        "runner_up_sub": runner_up_sub,
        "verdict_short": verdict_short,
        # Bundle E S3 A3 — image_url extension. Null when source comparison
        # was saved before A3 deploy (no image_url on legacy products).
        # FE renders placeholder primitive on null.
        "winner_image_url": _safe_image_url(winner),
        "runner_up_image_url": _safe_image_url(loser),
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

    Priority source (3-tier resolution per dispatcher 2026-05-23 ack):
      1. PRIMARY  — `users.preferences.priorities` (authoritative user-stated
         3-item list from onboarding step 9)
      2. FALLBACK — `users.behavior_profile.dimension_sensitivity` TOP entry
         (computed inference from tab_switch dwell events; for users who
         skipped step 9)
      3. EMPTY STATE — neither set + zero comparisons → empty_state=True

    The `behavior_profile.dimension_sensitivity` is a Dict[str, float]
    keyed by tab name with dwell-time weights — see
    `app/services/behavior_service.py:_compute_dimension_sensitivity`.

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

    # Step 1 — read user's priorities + behavior_profile + recent v2 comparisons
    priorities: list[str] = []
    comparisons: list[dict] = []

    try:
        # Pull both preferences AND behavior_profile in one users SELECT
        # so we have the dimension_sensitivity fallback available without
        # a second round-trip.
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
        # Tier 2 fallback per dispatcher 2026-05-23 ack: when
        # preferences.priorities is empty (user skipped onboarding step 9),
        # synthesize a single-element priorities list from the TOP entry
        # of behavior_profile.dimension_sensitivity. Computed from
        # tab_switch dwell events — see behavior_service.py:_compute_dimension_sensitivity.
        if not priorities:
            bp = user_row.get("behavior_profile") or {}
            if isinstance(bp, dict):
                dim_sens = bp.get("dimension_sensitivity") or {}
                if isinstance(dim_sens, dict) and dim_sens:
                    # TOP entry by weight (max float value)
                    try:
                        top_dim, _ = max(
                            ((k, float(v)) for k, v in dim_sens.items() if v is not None),
                            key=lambda kv: kv[1],
                            default=(None, 0.0),
                        )
                        if top_dim:
                            priorities = [str(top_dim)]
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "[home/smart_pick] dim_sensitivity fallback failed for %s: %r",
                            user_id, exc,
                        )
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


_VS_SPLIT_RE = re.compile(r"\s+vs\.?\s+", flags=re.IGNORECASE)


def _split_query_into_a_b(query: str) -> tuple[Optional[str], Optional[str]]:
    """Split a legacy `"X vs Y"` curated string into (a, b).

    Returns (None, None) when the query is malformed (no " vs " separator,
    splits into !=2 non-empty parts). Matches both `vs` and `vs.` case-insensitively.
    """
    if not isinstance(query, str) or not query.strip():
        return (None, None)
    parts = _VS_SPLIT_RE.split(query.strip(), maxsplit=1)
    if len(parts) != 2:
        return (None, None)
    a, b = parts[0].strip(), parts[1].strip()
    if not a or not b:
        return (None, None)
    return (a, b)


def _load_curated_trending() -> dict[str, list[dict]]:
    """Read the curated JSON file. Returns a region → list[entry] map.

    Bundle E B4.3a — entries are pre-split {tag, a, b, view_count} per
    JSX `HomeScreen.jsx:608-651`. For backwards-compat with any pre-Bundle-E
    curated rows that still ship the legacy `{query, view_count}` shape,
    this loader derives {a, b} from the query string and defaults `tag`
    to "Other" when missing. The endpoint then re-assembles a legacy
    `query` + `count` alias so consumers on either shape work.

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
        cleaned: dict[str, list[dict]] = {}
        for region, entries in raw.items():
            if not isinstance(entries, list):
                continue
            valid_entries = []
            for e in entries:
                if not isinstance(e, dict):
                    continue
                vc = e.get("view_count")
                if not isinstance(vc, int):
                    continue
                tag = e.get("tag")
                a = e.get("a")
                b = e.get("b")
                if isinstance(tag, str) and isinstance(a, str) and isinstance(b, str):
                    # Bundle E shape — already pre-split.
                    valid_entries.append({
                        "tag": tag.strip(),
                        "a": a.strip(),
                        "b": b.strip(),
                        "view_count": vc,
                    })
                    continue
                # Legacy shape — derive {a, b} from query string.
                q = e.get("query")
                if not isinstance(q, str):
                    continue
                derived_a, derived_b = _split_query_into_a_b(q)
                if derived_a is None or derived_b is None:
                    continue
                valid_entries.append({
                    "tag": (tag.strip() if isinstance(tag, str) and tag.strip() else "Other"),
                    "a": derived_a,
                    "b": derived_b,
                    "view_count": vc,
                })
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
    # Bundle E B4.3a — JSX-wins shape (tag/a/b/count) + legacy compat fields.
    # Frontend HomeScreen.jsx:608-651 reads tag/a/b/count; the legacy query +
    # view_count survive one release cycle for OTA consumers on the pre-Bundle-E
    # shape (matches the scoring_v2 legacy-key pattern).
    entries = [
        {
            "tag": e["tag"],
            "a": e["a"],
            "b": e["b"],
            "count": e["view_count"],
            "query": f"{e['a']} vs {e['b']}",
            "view_count": e["view_count"],
            "region": resolved_region,
        }
        for e in raw_entries
    ]

    payload = {"trending": entries, "region": resolved_region}

    try:
        _redis_set(cache_key, json.dumps(payload), ex=_TRENDING_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[home/trending] cache write failed: %r", exc)

    return payload
