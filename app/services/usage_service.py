"""Freemium usage tracking and tier enforcement.

Monthly cap = base tier limit + ``users.referral_bonus_comparisons_this_month``.
Lazy reset of the bonus happens inside ``_get_user_tier_info`` whenever
``referral_bonus_reset_at`` falls in the past — no cron job required.
"""
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.cache_service import redis_client
from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)

# M13-03: X-Device-Fingerprint contract — SHA-256 hex, same regex the register
# endpoint enforces (auth_routes._DEVICE_FINGERPRINT_RE).
_DEVICE_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")


def anon_usage_gate_enabled() -> bool:
    """ENABLE_ANON_USAGE_GATE — read PER CALL. Default OFF so a bad fingerprint
    heuristic can never lock out real users until the flag is canaried on."""
    return os.getenv("ENABLE_ANON_USAGE_GATE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def valid_device_fingerprint(value: Optional[str]) -> Optional[str]:
    """Return the fingerprint iff it matches the SHA-256 hex contract, else None
    (an absent/garbage header simply means the anon gate does not apply)."""
    if value and _DEVICE_FINGERPRINT_RE.match(value):
        return value
    return None


async def check_anon_usage_allowed(device_fingerprint: str) -> dict:
    """Freemium gate for an ANONYMOUS caller, keyed on the device fingerprint.

    Anonymous devices have no `users` row (the lifetime counter lives in Supabase
    keyed by user_id), so this uses the free-tier daily + monthly Redis counters
    keyed on ``anon:{fingerprint}``. Fails OPEN when Redis is unavailable — a
    cache outage must never block a legitimate user. Same shape as
    ``check_usage_allowed``.
    """
    limits = TIER_LIMITS["free"]
    anon_id = f"anon:{device_fingerprint}"
    daily_used = _get_redis_count(_daily_key(anon_id))
    monthly_used = _get_redis_count(_monthly_key(anon_id))

    if daily_used >= limits["daily"]:
        return {
            "allowed": False,
            "reason": "daily_limit",
            "tier": "free",
            "remaining": {"daily": 0, "monthly": max(0, limits["monthly"] - monthly_used), "lifetime_free": 0},
        }
    if monthly_used >= limits["monthly"]:
        return {
            "allowed": False,
            "reason": "monthly_limit",
            "tier": "free",
            "remaining": {"daily": max(0, limits["daily"] - daily_used), "monthly": 0, "lifetime_free": 0},
        }
    return {
        "allowed": True,
        "reason": None,
        "tier": "free",
        "remaining": {
            "daily": limits["daily"] - daily_used,
            "monthly": limits["monthly"] - monthly_used,
            "lifetime_free": 0,
        },
    }


async def record_anon_comparison(device_fingerprint: str) -> None:
    """Increment the anonymous device's daily+monthly Redis counters after a
    successful comparison. Fire-and-forget safe; no-op when Redis is down."""
    if not redis_client:
        return
    try:
        anon_id = f"anon:{device_fingerprint}"
        daily_key = _daily_key(anon_id)
        monthly_key = _monthly_key(anon_id)

        daily_count = redis_client.incr(daily_key)
        if daily_count == 1:
            redis_client.expire(daily_key, 86400)  # 24h TTL

        monthly_count = redis_client.incr(monthly_key)
        if monthly_count == 1:
            redis_client.expire(monthly_key, 86400 * 32)  # ~32 days TTL
    except Exception as e:
        logger.error(f"Failed to record anon comparison usage: {e}")

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


def _safe_expire(key: str, ttl: int) -> None:
    try:
        redis_client.expire(key, ttl)
    except Exception as e:  # noqa: BLE001
        logger.warning("[usage] TTL set failed for %s: %s", key, e)


def _safe_decr(key: str) -> None:
    try:
        redis_client.decrby(key, 1)
    except Exception:  # noqa: BLE001 — rollback is best-effort
        pass


def _atomic_consume(user_id: str, daily_limit: int, monthly_cap: int):
    """Atomic INCRBY-then-check-then-DECRBY-rollback of the daily then monthly
    Redis counters (the try_consume_serper_image_credit pattern). Returns None on
    success (both counters advanced), else the reason string
    ('daily_limit'/'monthly_limit') after fully rolling back. Fails OPEN (None) on
    a Redis error — a cache outage must never block a legitimate user."""
    if not redis_client:
        return None  # fail-open: cannot meter without Redis
    daily_key = _daily_key(user_id)
    monthly_key = _monthly_key(user_id)
    try:
        new_daily = redis_client.incrby(daily_key, 1)
        if new_daily == 1:
            _safe_expire(daily_key, 86400)  # 24h
        if new_daily > daily_limit:
            _safe_decr(daily_key)
            return "daily_limit"
        new_monthly = redis_client.incrby(monthly_key, 1)
        if new_monthly == 1:
            _safe_expire(monthly_key, 86400 * 32)  # ~32d
        if new_monthly > monthly_cap:
            _safe_decr(monthly_key)
            _safe_decr(daily_key)  # roll back the daily taken above
            return "monthly_limit"
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("[usage] atomic consume failed for %s: %s — fail-open", user_id, e)
        return None


def _bump_counters(user_id: str) -> None:
    """Advance daily+monthly WITHOUT a cap check (the lifetime-free window). Parity
    with the legacy record_comparison, which incremented daily/monthly even during
    the first 3 lifetime-free comparisons."""
    if not redis_client:
        return
    try:
        daily_key = _daily_key(user_id)
        monthly_key = _monthly_key(user_id)
        if redis_client.incrby(daily_key, 1) == 1:
            _safe_expire(daily_key, 86400)
        if redis_client.incrby(monthly_key, 1) == 1:
            _safe_expire(monthly_key, 86400 * 32)
    except Exception as e:  # noqa: BLE001
        logger.warning("[usage] lifetime-free counter bump failed for %s: %s", user_id, e)


async def consume_comparison_credit(user_id: str, access_token: str) -> dict:
    """TOCTOU-safe freemium gate — the request-path replacement for
    check_usage_allowed.

    check_usage_allowed READ the counters and record_comparison INCREMENTED them
    later fire-and-forget, so N parallel /text/compare requests all read the same
    pre-increment value, all passed, and all ran (6 comparisons against a 3/day
    cap). This SYNCHRONOUSLY reserves the daily+monthly Redis credit with an atomic
    INCRBY + cap check + DECRBY rollback; the Supabase lifetime write stays
    fire-and-forget (record_lifetime_comparison). If the comparison work then
    fails, the caller refunds via refund_comparison_credit.

    Same return shape as check_usage_allowed, plus 'consumed' (True when the
    daily/monthly credit was taken and must be refunded on a later work failure).
    """
    user_info = await _get_user_tier_info(user_id)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    bonus = await _get_active_referral_bonus(user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    monthly_cap = limits["monthly"] + bonus

    # Lifetime-free path: allowed regardless of daily/monthly, but still advance
    # the counters (parity with the legacy record_comparison).
    if tier == "free" and lifetime_used < limits["lifetime_free"]:
        _bump_counters(user_id)
        return {
            "allowed": True,
            "reason": None,
            "tier": tier,
            "consumed": True,
            "remaining": {
                "daily": limits["daily"],
                "monthly": monthly_cap,
                "lifetime_free": limits["lifetime_free"] - lifetime_used,
            },
        }

    reason = _atomic_consume(user_id, limits["daily"], monthly_cap)
    if reason == "daily_limit":
        return {
            "allowed": False, "reason": "daily_limit", "tier": tier, "consumed": False,
            "remaining": {"daily": 0, "monthly": max(0, monthly_cap - _get_redis_count(_monthly_key(user_id))), "lifetime_free": 0},
        }
    if reason == "monthly_limit":
        return {
            "allowed": False, "reason": "monthly_limit", "tier": tier, "consumed": False,
            "remaining": {"daily": max(0, limits["daily"] - _get_redis_count(_daily_key(user_id))), "monthly": 0, "lifetime_free": 0},
        }
    return {
        "allowed": True, "reason": None, "tier": tier, "consumed": True,
        "remaining": {
            "daily": max(0, limits["daily"] - _get_redis_count(_daily_key(user_id))),
            "monthly": max(0, monthly_cap - _get_redis_count(_monthly_key(user_id))),
            "lifetime_free": 0,
        },
    }


async def refund_comparison_credit(user_id: str) -> None:
    """Best-effort DECRBY of the daily+monthly credit reserved at the gate, for
    when the comparison work then failed — preserves the legacy behaviour where a
    failed comparison did not burn a daily credit. Fire-and-forget safe."""
    if not redis_client:
        return
    try:
        _safe_decr(_daily_key(user_id))
        _safe_decr(_monthly_key(user_id))
    except Exception as e:  # noqa: BLE001
        logger.warning("[usage] refund failed for %s: %s", user_id, e)


async def record_lifetime_comparison(user_id: str, access_token: str) -> None:
    """Fire-and-forget Supabase lifetime-counter increment. The daily+monthly
    Redis credit is reserved synchronously at the gate by consume_comparison_credit,
    so this deliberately does NOT touch the Redis counters (that would double-count)."""
    try:
        client = get_admin_supabase_client()
        client.rpc("increment_lifetime_comparisons", {"target_user_id": user_id}).execute()
    except Exception as e:
        logger.error(f"Failed to record lifetime comparison for {user_id}: {e}")


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


async def _get_active_referral_bonus(user_id: str) -> int:
    """Sum the user's non-expired, non-consumed referral_redemptions grants.

    Path-(a) entitlement source per plan task 35: this is the AUTHORITATIVE
    bonus capacity — the INT counter `users.referral_bonus_comparisons_this_month`
    stays for analytics/display only and MUST NOT drive entitlement.
    Filters: expires_at > now() AND consumed_at IS NULL.
    Fail-open returning 0 — a transient DB error must NOT silently inflate
    the user's cap.
    """
    try:
        client = get_admin_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        resp = (
            client.table("referral_redemptions")
            .select("loop2_comparisons_granted")
            .eq("referrer_user_id", user_id)
            .gt("expires_at", now_iso)
            .is_("consumed_at", "null")
            .execute()
        )
        rows = resp.data or []
        return sum(int(r.get("loop2_comparisons_granted") or 0) for r in rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[usage] active referral bonus lookup failed for %s: %s", user_id, exc
        )
        return 0


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
    # Path-(a): entitlement bonus = sum of active referral_redemptions rows
    # (not the INT counter, which stays for analytics only).
    bonus = await _get_active_referral_bonus(user_id)
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

    Reports the EFFECTIVE monthly cap (base + active referral bonus) so the
    frontend's "X / Y" display accurately reflects entitlement.
    Path-(a): bonus is summed from active redemptions, not the INT counter.
    """
    user_info = await _get_user_tier_info(user_id)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    bonus = await _get_active_referral_bonus(user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    monthly_cap = limits["monthly"] + bonus

    daily_used = _get_redis_count(_daily_key(user_id))
    monthly_used = _get_redis_count(_monthly_key(user_id))

    # Mirror check_usage_allowed (line 167): a free-tier user with lifetime-free
    # comparisons left BYPASSES the daily/monthly counters. The DISPLAY must reflect
    # that — otherwise a user whose lifetime counter was reset (admin reset) while
    # the daily/monthly Redis counters are still high sees a FALSE paywall on Home,
    # even though the gate would allow the compare. On the lifetime-free path, report
    # the full daily/monthly allowance so the frontend's canCompare stays true.
    on_lifetime_free = tier == "free" and lifetime_used < limits["lifetime_free"]
    lifetime_free_remaining = (
        max(0, limits["lifetime_free"] - lifetime_used) if tier == "free" else 0
    )
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
            "daily": limits["daily"] if on_lifetime_free else max(0, limits["daily"] - daily_used),
            "monthly": monthly_cap if on_lifetime_free else max(0, monthly_cap - monthly_used),
            "lifetime_free": lifetime_free_remaining,
        },
    }
