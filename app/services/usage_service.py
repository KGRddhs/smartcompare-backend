"""Freemium usage tracking and tier enforcement.

Monthly cap = base tier limit + ``users.referral_bonus_comparisons_this_month``.
Lazy reset of the bonus happens inside ``_get_user_tier_info`` whenever
``referral_bonus_reset_at`` falls in the past — no cron job required.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.cache_service import redis_client
from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)

# Tier configuration
TIER_LIMITS = {
    "free": {
        "lifetime_free": 3,    # First 3 comparisons ever — no restrictions
        "monthly": 10,
        "daily": 3,
    },
    "premium": {
        "lifetime_free": 0,    # Not applicable
        "monthly": 70,
        "daily": 10,
    },
}


def _daily_key(user_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"usage:daily:{user_id}:{today}"


def _monthly_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"usage:monthly:{user_id}:{month}"


def _get_redis_count(key: str) -> int:
    if not redis_client:
        return 0
    try:
        val = redis_client.get(key)
        return int(val) if val else 0
    except Exception:
        return 0


async def _get_user_tier_info(user_id: str) -> dict:
    """Get user's subscription tier, lifetime usage, and referral bonus state.

    Performs lazy reset of ``referral_bonus_comparisons_this_month`` when
    ``referral_bonus_reset_at`` is in the past — no cron needed.
    """
    try:
        client = get_admin_supabase_client()
        result = client.table("users").select(
            "subscription_tier, lifetime_comparisons_used, "
            "referral_bonus_comparisons_this_month, referral_bonus_reset_at"
        ).eq("id", user_id).single().execute()
        data = result.data or {}
        # Lazy referral bonus reset
        return _maybe_reset_referral_bonus(client, user_id, data)
    except Exception as e:
        logger.error(f"Failed to get user tier info: {e}")
        return {
            "subscription_tier": "free",
            "lifetime_comparisons_used": 0,
            "referral_bonus_comparisons_this_month": 0,
        }


def _maybe_reset_referral_bonus(client, user_id: str, data: dict) -> dict:
    """If ``referral_bonus_reset_at < now()``, reset counter to 0 and roll
    ``reset_at`` forward by ~1 month. Returns the (possibly-mutated) dict.

    No-op when the user's row predates migration 014 (fields missing) — we
    just supply zero defaults so downstream cap math works."""
    reset_at = data.get("referral_bonus_reset_at")
    if not reset_at:
        data.setdefault("referral_bonus_comparisons_this_month", 0)
        return data

    try:
        reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        data.setdefault("referral_bonus_comparisons_this_month", 0)
        return data

    now = datetime.now(timezone.utc)
    if reset_dt > now:
        data.setdefault("referral_bonus_comparisons_this_month", 0)
        return data

    # Past reset_at — zero the bonus and roll forward 30 days. The next
    # scheduled reset uses the same 30d cadence as the column default.
    new_reset_at = (now + timedelta(days=30)).isoformat()
    try:
        client.table("users").update(
            {
                "referral_bonus_comparisons_this_month": 0,
                "referral_bonus_reset_at": new_reset_at,
            }
        ).eq("id", user_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[usage] referral bonus reset failed for %s: %s", user_id, exc
        )
    data["referral_bonus_comparisons_this_month"] = 0
    data["referral_bonus_reset_at"] = new_reset_at
    return data


async def check_usage_allowed(user_id: str, access_token: str) -> dict:
    """Check if user can make a comparison.

    Returns:
        {
            "allowed": bool,
            "reason": str | None,
            "tier": str,
            "remaining": {"daily": int, "monthly": int, "lifetime_free": int}
        }
    """
    user_info = await _get_user_tier_info(user_id)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    bonus = user_info.get("referral_bonus_comparisons_this_month") or 0
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    monthly_cap = limits["monthly"] + bonus

    # Lifetime free comparisons (free tier only) — no cap check needed
    if tier == "free" and lifetime_used < limits["lifetime_free"]:
        return {
            "allowed": True,
            "reason": None,
            "tier": tier,
            "remaining": {
                "daily": limits["daily"],
                "monthly": monthly_cap,
                "lifetime_free": limits["lifetime_free"] - lifetime_used,
            },
        }

    # Get current usage from Redis
    daily_used = _get_redis_count(_daily_key(user_id))
    monthly_used = _get_redis_count(_monthly_key(user_id))

    # Check daily limit first (more restrictive)
    if daily_used >= limits["daily"]:
        return {
            "allowed": False,
            "reason": "daily_limit",
            "tier": tier,
            "remaining": {"daily": 0, "monthly": max(0, monthly_cap - monthly_used), "lifetime_free": 0},
        }

    # Check monthly limit (base + bonus)
    if monthly_used >= monthly_cap:
        return {
            "allowed": False,
            "reason": "monthly_limit",
            "tier": tier,
            "remaining": {"daily": max(0, limits["daily"] - daily_used), "monthly": 0, "lifetime_free": 0},
        }

    return {
        "allowed": True,
        "reason": None,
        "tier": tier,
        "remaining": {
            "daily": limits["daily"] - daily_used,
            "monthly": monthly_cap - monthly_used,
            "lifetime_free": 0,
        },
    }


async def record_comparison(user_id: str, access_token: str) -> None:
    """Increment usage counters after a successful comparison.

    Call via asyncio.create_task() — fire-and-forget.
    """
    try:
        # Increment Redis counters
        if redis_client:
            daily_key = _daily_key(user_id)
            monthly_key = _monthly_key(user_id)

            daily_count = redis_client.incr(daily_key)
            if daily_count == 1:
                redis_client.expire(daily_key, 86400)  # 24h TTL

            monthly_count = redis_client.incr(monthly_key)
            if monthly_count == 1:
                redis_client.expire(monthly_key, 86400 * 32)  # ~32 days TTL

        # Increment lifetime counter in Supabase
        client = get_admin_supabase_client()
        client.rpc("increment_lifetime_comparisons", {"target_user_id": user_id}).execute()

    except Exception as e:
        logger.error(f"Failed to record comparison usage for {user_id}: {e}")


async def get_usage_status(user_id: str, access_token: str) -> dict:
    """Get current usage counts and limits for display.

    Reports the EFFECTIVE monthly cap (base + referral bonus) so the
    frontend's "X / Y" display accurately reflects bonus capacity.
    """
    user_info = await _get_user_tier_info(user_id)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    bonus = user_info.get("referral_bonus_comparisons_this_month") or 0
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    monthly_cap = limits["monthly"] + bonus

    daily_used = _get_redis_count(_daily_key(user_id))
    monthly_used = _get_redis_count(_monthly_key(user_id))

    return {
        "tier": tier,
        "used": {
            "daily": daily_used,
            "monthly": monthly_used,
            "lifetime": lifetime_used,
        },
        "limits": {
            "daily": limits["daily"],
            "monthly": monthly_cap,
            "monthly_base": limits["monthly"],
            "monthly_bonus": bonus,
            "lifetime_free": limits["lifetime_free"],
        },
        "remaining": {
            "daily": max(0, limits["daily"] - daily_used),
            "monthly": max(0, monthly_cap - monthly_used),
        },
    }
