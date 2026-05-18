"""API Budget Service — credit tracking + circuit breakers for external APIs.

Uses cache_service helpers (_redis_get, _redis_set, _redis_incr, _redis_expire)
for Redis access. Gracefully degrades if Redis is unavailable.
"""
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from app.services.cache_service import _redis_get, _redis_set, _redis_incr, _redis_expire

logger = logging.getLogger(__name__)

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
}

# Circuit breaker config
CB_FAILURE_THRESHOLD = 3           # consecutive failures to trip
CB_RECOVERY_TIMEOUT = 600          # 10 min cooldown
CB_HALF_OPEN_MAX_CALLS = 1         # 1 test call in half-open

# Circuit breaker states
CB_CLOSED = "closed"
CB_OPEN = "open"
CB_HALF_OPEN = "half_open"

# TTL for circuit breaker state keys (1 hour)
_CB_TTL = 3600
# TTL for monthly budget keys (35 days)
_MONTHLY_TTL = 35 * 24 * 3600


def _budget_key(provider: str) -> str:
    """Redis key for budget counter."""
    config = PROVIDER_CONFIGS.get(provider, {})
    if config.get("is_lifetime"):
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


def record_usage(provider: str, count: int = 1) -> None:
    """Record API usage after successful call (atomic operation)."""
    try:
        key = _budget_key(provider)
        from app.services.cache_service import redis_client
        if redis_client:
            redis_client.incrby(key, count)
        else:
            for _ in range(count):
                _redis_incr(key)
        config = PROVIDER_CONFIGS.get(provider, {})
        if not config.get("is_lifetime"):
            _redis_expire(key, _MONTHLY_TTL)
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

    return {"providers": result, "circuit_breakers": breakers}
