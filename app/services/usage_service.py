"""Freemium usage tracking and tier enforcement."""
import logging
from datetime import datetime, timezone
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
    """Get user's subscription tier and lifetime usage from DB."""
    try:
        client = get_admin_supabase_client()
        result = client.table("users").select(
            "subscription_tier, lifetime_comparisons_used"
        ).eq("id", user_id).single().execute()
        return result.data or {"subscription_tier": "free", "lifetime_comparisons_used": 0}
    except Exception as e:
        logger.error(f"Failed to get user tier info: {e}")
        return {"subscription_tier": "free", "lifetime_comparisons_used": 0}


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
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # Lifetime free comparisons (free tier only) — no cap check needed
    if tier == "free" and lifetime_used < limits["lifetime_free"]:
        return {
            "allowed": True,
            "reason": None,
            "tier": tier,
            "remaining": {
                "daily": limits["daily"],
                "monthly": limits["monthly"],
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
            "remaining": {"daily": 0, "monthly": max(0, limits["monthly"] - monthly_used), "lifetime_free": 0},
        }

    # Check monthly limit
    if monthly_used >= limits["monthly"]:
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
            "monthly": limits["monthly"] - monthly_used,
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
    """Get current usage counts and limits for display."""
    user_info = await _get_user_tier_info(user_id)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

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
            "monthly": limits["monthly"],
            "lifetime_free": limits["lifetime_free"],
        },
        "remaining": {
            "daily": max(0, limits["daily"] - daily_used),
            "monthly": max(0, limits["monthly"] - monthly_used),
        },
    }
