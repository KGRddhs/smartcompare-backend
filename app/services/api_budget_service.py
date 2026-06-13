"""API Budget Service — credit tracking + circuit breakers for external APIs.

Uses cache_service helpers (_redis_get, _redis_set, _redis_incr, _redis_expire)
for Redis access. Gracefully degrades if Redis is unavailable.
"""
import json
import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from app.services.cache_service import _redis_get, _redis_set, _redis_incr, _redis_expire

logger = logging.getLogger(__name__)

# Default daily image-search budget. Separate from the main `serper` lifetime
# counter so the Bundle E S3 image pipeline cannot starve price/spec credit.
# Override via env `SERPER_IMAGE_DAILY_BUDGET` on Railway.
_DEFAULT_SERPER_IMAGE_DAILY_BUDGET = 500


def _serper_image_daily_budget() -> int:
    """Resolve the daily image-search budget from env (read fresh each call so
    tests + Railway env updates take effect without a restart)."""
    try:
        return int(os.environ.get("SERPER_IMAGE_DAILY_BUDGET", _DEFAULT_SERPER_IMAGE_DAILY_BUDGET))
    except (TypeError, ValueError):
        return _DEFAULT_SERPER_IMAGE_DAILY_BUDGET


# Provider configurations — budgets and thresholds
PROVIDER_CONFIGS = {
    "firecrawl": {
        "monthly_limit": 450,       # 500 free, save 50 buffer
        "warn_at": 400,
        "is_lifetime": True,        # Lifetime credits, not monthly-resetting
    },
    "scrapedo": {
        "monthly_limit": 900,       # 1,000/mo free, save 100 buffer
        "warn_at": 800,
        "is_lifetime": False,       # Monthly reset
    },
    "serper": {
        "monthly_limit": 2200,      # 2,500 credits, save 300 buffer
        "warn_at": 2000,
        "is_lifetime": True,
    },
    # Bundle B S3 L2 — YouTube Data API v3. Free quota is 10,000 units/DAY
    # (NOT lifetime, NOT monthly): search.list costs 100 units, videos.list 1.
    # The real spend-guard is the per-day check-and-increment counter
    # (try_consume_youtube_credit / _youtube_daily_*), which caps daily UNITS.
    # This PROVIDER_CONFIGS entry exists so has_budget()/the circuit breaker /
    # record_usage()'s burn-alert plumbing treat "youtube" as a known provider;
    # `monthly_limit` here is the daily unit ceiling and `is_lifetime` is False
    # so the (unused) monthly key would reset — but the daily counter below is
    # the authoritative budget, mirroring the serper_images pattern.
    "youtube": {
        "monthly_limit": 10000,     # daily unit ceiling (10k/day free quota)
        "warn_at": 8000,
        "is_lifetime": False,
    },
}

# Circuit breaker config
CB_FAILURE_THRESHOLD = 3           # consecutive failures to trip
CB_RECOVERY_TIMEOUT = 600          # 10 min cooldown
CB_HALF_OPEN_MAX_CALLS = 1         # 1 test call in half-open

# I5.0 (Bundle B S2) — 80%-burn alert. has_budget() only warns at `warn_at`
# (~91% for serper), which leaves almost no runway before a measurement run
# depletes the key (the S1 baseline incident). This earlier tripwire fires a
# log + Sentry capture_message ONCE when a provider crosses 80% of its
# ceiling, de-duped via a Redis sentinel so it does not spam every call.
WARN_BURN_FRACTION = 0.80

# Circuit breaker states
CB_CLOSED = "closed"
CB_OPEN = "open"
CB_HALF_OPEN = "half_open"

# TTL for circuit breaker state keys (1 hour)
_CB_TTL = 3600
# TTL for monthly budget keys (35 days)
_MONTHLY_TTL = 35 * 24 * 3600


# S3 L4.3 — fallback prefix when SERPER_API_KEY is unset/empty (test/CI without
# the secret). Keeps the counter key deterministic instead of collapsing to a
# bare 'budget:serper::lifetime'.
_SERPER_NO_KEY_PREFIX = "nokey"


def _serper_key_prefix() -> str:
    """First 8 chars of the live SERPER_API_KEY (read fresh each call so a
    Railway env update / key rotation takes effect without a restart, mirroring
    _serper_image_daily_budget).

    This scopes the Serper lifetime counter to the key that burned the credits:
    a rotation starts a fresh honest counter instead of inheriting the previous
    account's burn (the 5136-across-4-accounts false-trip, S2 G6). Falls back to
    a stable 'nokey' sentinel when the env var is unset/empty so the key stays
    deterministic."""
    raw = (os.environ.get("SERPER_API_KEY") or "").strip()
    return raw[:8] if raw else _SERPER_NO_KEY_PREFIX


def _budget_key(provider: str) -> str:
    """Redis key for budget counter.

    serper's lifetime counter is KEY-SCOPED (S3 L4.3): the live key's 8-char
    prefix is embedded so a rotation cannot inherit a depleted account's burn.
    Other lifetime providers (firecrawl) keep their plain lifetime key — they
    are not API-key-rotated the same way."""
    config = PROVIDER_CONFIGS.get(provider, {})
    if config.get("is_lifetime"):
        if provider == "serper":
            return f"budget:serper:{_serper_key_prefix()}:lifetime"
        return f"budget:{provider}:lifetime"
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"budget:{provider}:{month}"


def _circuit_key(provider: str) -> str:
    """Redis key for circuit breaker state."""
    return f"circuit:{provider}"


def has_budget(provider: str) -> bool:
    """Check if provider has remaining budget. Returns True if Redis unavailable (fail-open)."""
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return False
    try:
        raw = _redis_get(_budget_key(provider))
        if raw is None:
            return True  # No usage yet or Redis down
        used = int(raw)
        remaining = config["monthly_limit"] - used
        if remaining <= 0:
            logger.warning(f"[BUDGET] {provider} budget exhausted ({used}/{config['monthly_limit']})")
            return False
        if used >= config.get("warn_at", float("inf")):
            logger.warning(f"[BUDGET] {provider} budget warning ({used}/{config['monthly_limit']})")
        return True
    except Exception as e:
        logger.warning(f"[BUDGET] Error checking {provider}: {e}")
        return True  # fail-open


def _burn_threshold(provider: str) -> int:
    """80%-of-ceiling credit count for `provider` (0 for unknown providers)."""
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return 0
    return int(config["monthly_limit"] * WARN_BURN_FRACTION)


def _burn_sentinel_key(provider: str) -> str:
    """Redis sentinel marking the 80%-burn alert as already fired for the
    current budget window (lifetime, or this month for resetting providers).
    Tying it to the same window-stamp as the budget key means a monthly reset
    (new month key) naturally re-arms the alert.

    S3 L4.3 — for serper the sentinel is keyed by the live key's 8-char prefix
    (`burn_alert_fired:{prefix}`) so a key rotation re-arms the alert: the new
    prefix yields a new sentinel key, so the previous key's LATCHED (no-expiry)
    sentinel no longer suppresses the fresh key's alert. (Pre-L4.3 the no-expiry
    latch meant a counter-only reset on rotation left the alert permanently
    suppressed — CLAUDE.md rotation playbook had to DEL it manually.)"""
    if provider == "serper":
        return f"budget:serper:burn_alert_fired:{_serper_key_prefix()}"
    return f"budget:{provider}:burn_alert_fired:{_budget_key(provider)}"


def _maybe_fire_burn_alert(provider: str, used: int) -> None:
    """Fire a one-shot log + Sentry alert when `used` is at/over the 80% burn
    threshold for `provider`. De-duped via a Redis sentinel so it alerts once
    per budget window, not on every subsequent call. Best-effort: any failure
    (sentry missing, Redis down) is swallowed — never breaks usage recording.
    """
    try:
        threshold = _burn_threshold(provider)
        if threshold <= 0 or used < threshold:
            return
        # De-dup: only fire on the FIRST crossing within this budget window.
        sentinel = _burn_sentinel_key(provider)
        if _redis_get(sentinel) is not None:
            return

        config = PROVIDER_CONFIGS.get(provider, {})
        limit = config.get("monthly_limit", 0)
        pct = round(100 * used / limit, 1) if limit else 0.0
        msg = (
            f"[BUDGET] {provider} burn alert: {used}/{limit} credits "
            f"({pct}%) — crossed 80% ceiling"
        )
        logger.warning(msg)

        # Sentry capture_message at warning level (matches error_handler's
        # local-import-guard pattern so it no-ops when Sentry isn't installed).
        try:
            import sentry_sdk
            sentry_sdk.capture_message(msg, level="warning")
        except ImportError:
            pass

        # Mark fired AFTER alerting. A LIFETIME provider (serper/firecrawl — the
        # S1-depletion case) must stay LATCHED until the key is manually reset
        # on rotation → no expiry (ex=None). A MONTHLY provider re-arms via its
        # month-stamped sentinel key anyway, so a bounded _MONTHLY_TTL is fine.
        # (G1 finding F1: this ternary was inverted — lifetime got the 1h
        # _CB_TTL, so the alert re-fired hourly until rotation.)
        ttl = None if config.get("is_lifetime") else _MONTHLY_TTL
        _redis_set(sentinel, str(int(time.time())), ex=ttl)
    except Exception as e:  # noqa: BLE001 — alerting must never break recording
        logger.warning(f"[BUDGET] burn-alert check failed for {provider}: {e}")


def record_usage(provider: str, count: int = 1) -> None:
    """Record API usage after successful call (atomic operation).

    After the counter increments, checks the 80%-burn tripwire (I5.0) on the
    post-increment value so the alert fires at the exact crossing call.
    """
    try:
        key = _budget_key(provider)
        new_value = None
        from app.services.cache_service import redis_client
        if redis_client:
            new_value = redis_client.incrby(key, count)
        else:
            for _ in range(count):
                new_value = _redis_incr(key)
        config = PROVIDER_CONFIGS.get(provider, {})
        if not config.get("is_lifetime"):
            _redis_expire(key, _MONTHLY_TTL)
        # I5.0 — 80%-burn tripwire on the fresh counter value.
        if new_value is not None:
            try:
                _maybe_fire_burn_alert(provider, int(new_value))
            except (TypeError, ValueError):
                pass
    except Exception as e:
        logger.warning(f"[BUDGET] Error recording {provider}: {e}")


def is_circuit_closed(provider: str) -> bool:
    """Check if circuit breaker allows calls. Returns True if Redis unavailable (fail-open)."""
    try:
        raw = _redis_get(_circuit_key(provider))
        if not raw:
            return True  # No state = closed
        state = json.loads(raw)
        if state["state"] == CB_CLOSED:
            return True
        if state["state"] == CB_OPEN:
            # Check recovery timeout
            if time.time() - state.get("tripped_at", 0) >= CB_RECOVERY_TIMEOUT:
                # Transition to half-open
                state["state"] = CB_HALF_OPEN
                state["half_open_calls"] = 0
                _redis_set(_circuit_key(provider), json.dumps(state), ex=_CB_TTL)
                logger.info(f"[CIRCUIT] {provider} transitioning to half-open")
                return True
            return False
        if state["state"] == CB_HALF_OPEN:
            return state.get("half_open_calls", 0) < CB_HALF_OPEN_MAX_CALLS
        return True
    except Exception as e:
        logger.warning(f"[CIRCUIT] Error checking {provider}: {e}")
        return True


def record_failure(provider: str) -> None:
    """Record a failure (429, 503, timeout, connection refused/error). May trip circuit breaker.

    Call this on: 429, 503, timeout (status=0), connection refused (status=0).
    Do NOT call on: 200-no-price, 404, 403 (domain-level blocks, not service-level).
    """
    try:
        key = _circuit_key(provider)
        raw = _redis_get(key)
        state = json.loads(raw) if raw else {"state": CB_CLOSED, "failure_count": 0}

        state["failure_count"] = state.get("failure_count", 0) + 1
        state["last_failure_at"] = time.time()

        if state["failure_count"] >= CB_FAILURE_THRESHOLD:
            state["state"] = CB_OPEN
            state["tripped_at"] = time.time()
            logger.warning(f"[CIRCUIT] {provider} breaker TRIPPED after {state['failure_count']} failures")

        _redis_set(key, json.dumps(state), ex=_CB_TTL)
    except Exception as e:
        logger.warning(f"[CIRCUIT] Error recording failure for {provider}: {e}")


def record_success(provider: str) -> None:
    """Record success. Resets failure count. Closes half-open breaker."""
    try:
        key = _circuit_key(provider)
        raw = _redis_get(key)
        if not raw:
            return
        state = json.loads(raw)
        if state["state"] == CB_HALF_OPEN:
            logger.info(f"[CIRCUIT] {provider} breaker CLOSED after successful test call")
        state["state"] = CB_CLOSED
        state["failure_count"] = 0
        _redis_set(key, json.dumps(state), ex=_CB_TTL)
    except Exception as e:
        logger.warning(f"[CIRCUIT] Error recording success for {provider}: {e}")


def get_remaining(provider: str) -> int:
    """Bundle C § 1c diagnostic helper — return remaining credits for a provider.
    Read-only; safe to call from diagnostic logs without side effects. Fail-open:
    on Redis error or unknown provider, returns the provider's full limit so
    diagnostic output remains meaningful (or 0 for unknown providers)."""
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return 0
    used = 0
    try:
        raw = _redis_get(_budget_key(provider))
        if raw is not None:
            used = int(raw)
    except Exception:
        pass
    return max(0, config["monthly_limit"] - used)


def get_burn_status(provider: str) -> Dict[str, Any]:
    """I5.0 diagnostic — current burn state vs the 80% ceiling for `provider`.

    Read-only; fail-safe (no usage observed, never raises) on Redis error or
    unknown provider. Returns
    `{used, limit, threshold, fraction, over_threshold}` for the dashboard and
    the alert drill.
    """
    config = PROVIDER_CONFIGS.get(provider)
    limit = config["monthly_limit"] if config else 0
    threshold = _burn_threshold(provider)
    used = 0
    try:
        raw = _redis_get(_budget_key(provider))
        if raw is not None:
            used = int(raw)
    except Exception:
        pass
    return {
        "used": used,
        "limit": limit,
        "threshold": threshold,
        "fraction": round(used / limit, 4) if limit else 0.0,
        "over_threshold": bool(threshold and used >= threshold),
    }


def get_breaker_state(provider: str) -> str:
    """Bundle C § 1c diagnostic helper — return circuit-breaker state string.
    Read-only; fail-open ('closed') on Redis error so logs never raise."""
    try:
        raw = _redis_get(_circuit_key(provider))
        if not raw:
            return CB_CLOSED
        state = json.loads(raw)
        return state.get("state", CB_CLOSED)
    except Exception:
        return CB_CLOSED


def get_usage_summary() -> Dict[str, Any]:
    """Get usage summary for all providers (admin dashboard)."""
    result = {}
    for provider, config in PROVIDER_CONFIGS.items():
        used = 0
        try:
            raw = _redis_get(_budget_key(provider))
            if raw is not None:
                used = int(raw)
        except Exception:
            pass
        result[provider] = {
            "used": used,
            "limit": config["monthly_limit"],
            "remaining": max(0, config["monthly_limit"] - used),
            "is_lifetime": config.get("is_lifetime", False),
        }
        if config.get("is_lifetime"):
            result[provider]["lifetime_used"] = used

    # Circuit breaker states
    breakers = {}
    for provider in PROVIDER_CONFIGS:
        state_data = {"state": CB_CLOSED, "failures": 0}
        try:
            raw = _redis_get(_circuit_key(provider))
            if raw:
                s = json.loads(raw)
                state_data = {"state": s.get("state", CB_CLOSED), "failures": s.get("failure_count", 0)}
        except Exception:
            pass
        breakers[provider] = state_data

    # Bundle E S3 — image-pipeline daily counter (read-only summary)
    image_daily_limit = _serper_image_daily_budget()
    image_used = 0
    try:
        raw = _redis_get(_serper_image_key())
        if raw is not None:
            image_used = int(raw)
    except Exception:
        pass
    result["serper_images"] = {
        "used": image_used,
        "limit": image_daily_limit,
        "remaining": max(0, image_daily_limit - image_used),
        "scope": "daily",
    }

    return {"providers": result, "circuit_breakers": breakers}


# ============================================================================
# Bundle E S3 — Serper Images dedicated daily counter
# Separate from `serper` lifetime budget so the image pipeline cannot
# starve price / spec / review Serper credit.
# ============================================================================

def _serper_image_key() -> str:
    """Redis key for today's Serper Images count (UTC-aligned daily bucket)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"budget:serper_images:{today}"


# TTL for daily image counter: 36 hours so the key lives across the UTC
# boundary even if Redis trims aggressively (35h would be tight in some
# Upstash trim windows; 36h matches the pattern of _MONTHLY_TTL safety margin).
_SERPER_IMAGE_TTL = 36 * 3600


def try_consume_serper_image_credit(n: int = 1) -> bool:
    """Atomically check-and-increment the daily Serper Images counter.

    Returns True when the call may proceed (and the counter has been
    incremented), False when today's budget is exhausted. Fails OPEN on Redis
    errors per memory/project_upstash_redis_singlepoint_failure.md — we'd
    rather burn a credit than ship a placeholder image.

    Args:
        n: number of credits to consume (default 1).
    """
    if n <= 0:
        return True

    limit = _serper_image_daily_budget()
    key = _serper_image_key()

    try:
        from app.services.cache_service import redis_client
        if redis_client is None:
            return True  # fail-open

        # Atomic INCRBY first, then check — race-free counter math.
        new_value = redis_client.incrby(key, n)
        # Set TTL on first write only (incrby returns n on first call).
        if new_value == n:
            try:
                redis_client.expire(key, _SERPER_IMAGE_TTL)
            except Exception as e:
                logger.warning("[BUDGET] serper_images TTL set failed: %s", e)

        if new_value > limit:
            # Roll back the increment so the counter accurately reflects
            # *consumed* credits, not attempted ones — keeps admin dashboard
            # readable.
            try:
                redis_client.decrby(key, n)
            except Exception:
                pass
            logger.warning(
                "[BUDGET] serper_images daily budget exhausted (%s/%s)",
                new_value, limit,
            )
            return False
        return True
    except Exception as e:
        logger.warning("[BUDGET] serper_images consume failed: %s — fail-open", e)
        return True


def get_serper_image_usage() -> Dict[str, int]:
    """Diagnostic — return current day usage for the Serper Images counter.

    Returns:
        {"used": int, "limit": int, "remaining": int}
    """
    limit = _serper_image_daily_budget()
    used = 0
    try:
        raw = _redis_get(_serper_image_key())
        if raw is not None:
            used = int(raw)
    except Exception:
        pass
    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}


# ============================================================================
# Bundle B S3 L2 — YouTube Data API v3 daily UNIT counter
# YouTube's free quota is 10,000 UNITS per DAY (resets at midnight Pacific).
# search.list = 100 units, videos.list = 1 unit. We meter UNITS (not calls)
# in a per-UTC-day Redis counter, guard the expensive search.list with a
# check-and-increment, and fail OPEN on Redis down (a lost signal is cheaper
# than a hard failure). Modeled on try_consume_serper_image_credit.
# ============================================================================

# Default daily UNIT budget. 9,000 leaves a 1,000-unit safety buffer under the
# 10k free ceiling (~90 search.list calls/day). Override via env.
_DEFAULT_YOUTUBE_DAILY_UNITS = 9000


def _youtube_daily_unit_budget() -> int:
    """Resolve the daily YouTube UNIT budget from env (read fresh each call so
    tests + Railway env updates take effect without a restart)."""
    try:
        return int(os.environ.get("YOUTUBE_DAILY_UNIT_BUDGET", _DEFAULT_YOUTUBE_DAILY_UNITS))
    except (TypeError, ValueError):
        return _DEFAULT_YOUTUBE_DAILY_UNITS


def _youtube_daily_key() -> str:
    """Redis key for today's YouTube unit count (UTC-aligned daily bucket).

    NOTE: YouTube's quota actually resets at midnight Pacific, not UTC. We use a
    UTC day bucket for consistency with the rest of the codebase — the small
    boundary skew only costs at most one extra day's grace, well inside the
    1,000-unit safety buffer."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"budget:youtube_units:{today}"


# TTL 36h so the key survives across the UTC boundary even under aggressive
# Upstash trimming (matches the serper_images safety margin).
_YOUTUBE_UNIT_TTL = 36 * 3600


def try_consume_youtube_credit(units: int = 100) -> bool:
    """Atomically check-and-increment the daily YouTube UNIT counter.

    Call this BEFORE the expensive search.list (default 100 units). Returns
    True when the call may proceed (counter incremented), False when today's
    unit budget is exhausted. Fails OPEN on Redis errors (a missed YouTube
    signal is cheaper than a hard failure) per
    memory/project_upstash_redis_singlepoint_failure.md.

    The cheap videos.list (1 unit) is NOT separately gated here — it only runs
    after search.list already passed this guard, and 1 unit is within the
    safety buffer. record_usage("youtube", count=1) still meters it for the
    admin summary.

    Args:
        units: units to consume for this guarded call (default 100 = search.list).
    """
    if units <= 0:
        return True

    limit = _youtube_daily_unit_budget()
    key = _youtube_daily_key()

    try:
        from app.services.cache_service import redis_client
        if redis_client is None:
            return True  # fail-open

        new_value = redis_client.incrby(key, units)
        # Set TTL on first write only (incrby returns `units` on the first call).
        if new_value == units:
            try:
                redis_client.expire(key, _YOUTUBE_UNIT_TTL)
            except Exception as e:
                logger.warning("[BUDGET] youtube_units TTL set failed: %s", e)

        if new_value > limit:
            # Roll back so the counter reflects *consumed* units, not attempted.
            try:
                redis_client.decrby(key, units)
            except Exception:
                pass
            logger.warning(
                "[BUDGET] youtube daily unit budget exhausted (%s/%s)",
                new_value, limit,
            )
            return False
        return True
    except Exception as e:
        logger.warning("[BUDGET] youtube consume failed: %s — fail-open", e)
        return True


def get_youtube_unit_usage() -> Dict[str, int]:
    """Diagnostic — current day UNIT usage for the YouTube counter.

    Returns:
        {"used": int, "limit": int, "remaining": int}
    """
    limit = _youtube_daily_unit_budget()
    used = 0
    try:
        raw = _redis_get(_youtube_daily_key())
        if raw is not None:
            used = int(raw)
    except Exception:
        pass
    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}
