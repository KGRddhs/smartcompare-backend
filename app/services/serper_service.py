"""
Serper Service - Web search via Serper API (Google Search)
Enhanced for structured product data extraction
"""
import asyncio
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

# Bundle C § 1c A.3.3-fix-1 — Serper credit-meter integration. Every
# successful Serper call (HTTP 200) bumps the Redis counter so the
# admin/costs Serper figure reflects actual usage. Missing-API-key and
# exception paths skip the bump (we don't bill non-events).
#
# #60 — the meter was WRITE-ONLY: this module recorded usage but never read it
# back, so nothing in the price/discovery path ever slowed live spend. A cold
# 2-product compare burns ~10-30 credits against a 2,500-credit ONE-TIME free
# pool (~180 cold compares), which is why the key has depleted repeatedly.
# `serper_gate_allows` is the read side; see _serper_budget_ok below.
from app.services.api_budget_service import (
    record_usage,
    serper_gate_allows,
    is_circuit_closed,
    record_failure,
    record_success,
)
from app.services.cache_service import _redis_offload_enabled

logger = logging.getLogger(__name__)


async def _record_usage_async(provider: str) -> None:
    """#115 — offload dispatch for the per-Serper-200 budget INCRBY, which ran
    inline on the event loop in every async search_* function
    (ENABLE_ASYNC_REDIS_OFFLOAD). Lives in THIS module and references the
    module-level `record_usage` in BOTH branches (the cache_service.py design
    note), so a test patching serper_service.record_usage intercepts flag-ON
    and flag-OFF alike. Flag OFF -> inline, byte-identical. record_usage
    swallows its own errors, so no new failure mode is introduced."""
    if _redis_offload_enabled():
        await asyncio.to_thread(record_usage, provider)
        return
    record_usage(provider)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_BASE_URL = "https://google.serper.dev"


# ============================================
# MULTI-KEY SERPER FAILOVER (genuine-price serper-multikey)
# ============================================
# A single free Serper key holds a finite lifetime credit pool; when it
# depletes mid-run the warmer cron (and live compares) silently degrade to
# `estimated`. This layer reads an ORDERED key list from SERPER_API_KEYS
# (comma-separated, priority order) and rotates to the next non-exhausted key
# when a response signals credit depletion.
#
# Backward compatibility (critical): when only SERPER_API_KEY is set (no
# SERPER_API_KEYS) and that key is NOT exhausted, behaviour is byte-identical
# to before — the active key IS SERPER_API_KEY, exactly ONE POST fires on the
# happy path (no rotation), only a single cheap Redis exhaustion-check read is
# added. The module attr SERPER_API_KEY is preserved (tests patch it) and is
# consulted as the single-key fallback so `monkeypatch.setattr(serper_service,
# "SERPER_API_KEY", ...)` continues to work.
#
# Exhaustion is DISTINCT from the api_budget_service circuit breaker: a
# credit-depletion failover marks the KEY exhausted (Redis flag serper:
# exhausted:<key8>) and rotates — it does NOT trip the 3-failure CB cooldown.
# A transient 500/timeout is neither: it neither marks the key exhausted nor
# rotates (the caller's existing except/raise handling deals with it).

# Redis prefix for the per-key exhaustion flag. Keyed by the same 8-char
# prefix api_budget_service uses to scope the lifetime counter.
_SERPER_EXHAUSTED_PREFIX = "serper:exhausted:"

# TTL for the exhaustion flag. MODERATE (6h): long enough that a truly-depleted
# free key is skipped for the rest of a warmer run / session, short enough that
# a transiently-misclassified key (or a key whose free quota resets) is retried
# later instead of being permanently blacklisted.
_SERPER_EXHAUSTED_TTL = 6 * 3600

# In-process de-dupe so the "key exhausted" WARNING logs once per key per
# process (Redis carries the cross-process authoritative state).
_serper_exhausted_logged: set = set()


def _serper_key_prefix8(key: Optional[str]) -> str:
    """First 8 chars of a key (for the Redis exhaustion flag + logs). Mirrors
    api_budget_service._serper_key_prefix scoping."""
    raw = (key or "").strip()
    return raw[:8] if raw else "nokey"


def _resolve_serper_keys() -> List[str]:
    """Resolve the ORDERED Serper key list, fresh per call (so a Railway env
    update takes effect without a restart).

    Priority: SERPER_API_KEYS (comma-separated, order = priority; trimmed,
    blanks skipped, de-duplicated preserving order). Falls back to the single
    module-level SERPER_API_KEY when SERPER_API_KEYS is unset/empty — this is
    what preserves backward compatibility AND test monkeypatching of the
    SERPER_API_KEY module attr.
    """
    raw_multi = (os.environ.get("SERPER_API_KEYS") or "").strip()
    keys: List[str] = []
    if raw_multi:
        for part in raw_multi.split(","):
            k = part.strip()
            if k and k not in keys:
                keys.append(k)
    if keys:
        return keys
    # Single-key fallback — read the MODULE attr (not os.getenv) so tests that
    # monkeypatch serper_service.SERPER_API_KEY keep working and a runtime
    # override is honoured.
    single = (SERPER_API_KEY or "")
    single = single.strip() if isinstance(single, str) else ""
    return [single] if single else []


def _is_serper_key_exhausted(key: str) -> bool:
    """True if the per-key exhaustion flag is set in Redis. Fail-open: on Redis
    error / unavailability the key is treated as NOT exhausted (do not block a
    healthy key just because Redis is down)."""
    try:
        from app.services.cache_service import _redis_get
        return bool(_redis_get(_SERPER_EXHAUSTED_PREFIX + _serper_key_prefix8(key)))
    except Exception:  # noqa: BLE001
        return False


def _mark_serper_key_exhausted(key: str) -> None:
    """Set the per-key exhaustion flag in Redis with a MODERATE TTL and log a
    WARNING once per key per process. Best-effort — a Redis failure just means
    the flag is not persisted (the failover for THIS call still rotated)."""
    prefix = _serper_key_prefix8(key)
    try:
        from app.services.cache_service import _redis_set
        _redis_set(_SERPER_EXHAUSTED_PREFIX + prefix, "1", ex=_SERPER_EXHAUSTED_TTL)
    except Exception:  # noqa: BLE001
        pass
    if prefix not in _serper_exhausted_logged:
        _serper_exhausted_logged.add(prefix)
        logger.warning(
            "SERPER_KEY_EXHAUSTED key=%s… marked exhausted (ttl=%ss); "
            "rotating to next key",
            prefix,
            _SERPER_EXHAUSTED_TTL,
        )


def _active_serper_key(exclude: Optional[set] = None) -> Optional[str]:
    """The active Serper key.

    (exclude: keys to skip for THIS selection — used by the fail-fast rotation
    loop to advance past a key that just timed out WITHOUT persistently marking it
    credit-exhausted. Defaults None -> byte-identical to the pre-fail-fast
    selection.)

    SINGLE-KEY INERT (the common prod case: only SERPER_API_KEY set, no
    SERPER_API_KEYS): with 0 or 1 resolved keys there is NO exhaustion machinery
    — return the single key (or None) directly with NO Redis exhaustion read.
    This is byte-identical to the pre-multikey behaviour AND prevents a
    single-key prod from ever self-skipping its own (only) key on a stale flag.

    MULTI-KEY (>=2 resolved keys): return the first key in priority order that
    is NOT currently marked exhausted (Redis-checked). Returns None when every
    key is exhausted (caller then degrades exactly as the legacy 'SERPER_API_KEY
    not set' path)."""
    keys = _resolve_serper_keys()
    if len(keys) <= 1:
        return keys[0] if keys else None
    for key in keys:
        if exclude and key in exclude:
            continue
        if not _is_serper_key_exhausted(key):
            return key
    return None


def _response_signals_exhaustion(status_code: Optional[int], body_text: str) -> bool:
    """Detect credit depletion from a Serper response. Two independent signals:
      1. HTTP status in {402, 403} (payment/forbidden — credit-related), OR
      2. an ERROR response (status >= 400) whose body contains 'credit'
         (case-insensitive) — a depleted free key returns
         {"message":"Not enough credits"} (observed with HTTP 400).

    The 'credit' substring is STATUS-GATED to status >= 400: a legit HTTP 200
    result body containing 'credit'/'accredited'/'credited' (e.g. a product
    named "credit card") must NOT false-positive as depletion. A transient 500
    / non-credit 4xx still does NOT match (no 'credit' substring)."""
    if status_code in (402, 403):
        return True
    if (
        status_code is not None
        and status_code >= 400
        and isinstance(body_text, str)
        and body_text
        and "credit" in body_text.lower()
    ):
        return True
    return False


# ============================================
# BUDGET GATE (#60)
# ============================================
# Every entry point below consults this BEFORE dispatching a live call, so a
# depleted account stops spending instead of discovering depletion one 400 at a
# time. A closed gate returns the SAME benign empty shape the missing-key
# branches already return, which the price cascade already knows how to handle
# (it falls through to Tier 1.5 / 2 / 3) — a budget-out must DEGRADE, never
# raise, and never relax a price. Fails OPEN on any error.
#
# OPT-IN, not default-on (#60 review, blocking 4). The gate is INERT until an
# operator declares the live key's real ceiling in SERPER_LIFETIME_LIMIT. The
# packaged 2200 is a FREE-tier number and prod runs a PAID key: arming a gate at
# it would take all six entry points — and the price-cache warmer — dark the
# moment the lifetime counter crossed it, which is the failure mode
# cron_warm_price_cache.py:118-131 refuses to reproduce. Metering (the counter,
# get_remaining, the 80%-burn alert) is unconditional; BLOCKING is declared.
# See api_budget_service._serper_gate_engaged. SERPER_LIFETIME_LIMIT=0 is the
# explicit off switch, and each process logs its effective config once.


# MEMOISED, and that is load-bearing (#60 review, blocking 3).
# serper_gate_allows() -> has_budget() -> cache_service._redis_get() is a
# BLOCKING Upstash REST round trip (measured 163ms in this worktree) executed on
# the single asyncio event loop. Called raw at six entry points it would add
# ~10-12 such stalls per compare INSIDE the 15s _PRICE_RACE_TIMEOUT, and it
# would serialise the discovery fan-out — each `asyncio.ensure_future(search_web
# (...))` waiting on its own blocking read. That is the exact hazard
# structured_comparison_service._cache_get_async / ENABLE_ASYNC_REDIS_OFFLOAD
# exist to remove (#71); fixing one audit finding by re-introducing another is
# not a fix.
#
# A cached boolean is functionally identical here: the lifetime counter moves by
# at most 1 per call, so the answer cannot flip within a TTL window except by
# one credit. Cost of the memo is bounded overshoot — at most one TTL window of
# calls past the ceiling — against removing every round trip but one per window.
_SERPER_GATE_CACHE_TTL_ENV = "SERPER_GATE_CACHE_TTL"
_DEFAULT_SERPER_GATE_CACHE_TTL = 60.0
_serper_gate_cache: Optional[tuple] = None  # (expires_at_monotonic, allowed)


def _serper_gate_cache_ttl() -> float:
    """Seconds a gate decision is reused. <=0 disables memoisation entirely
    (every call re-reads Redis) — the escape hatch if a decision ever needs to
    be instant."""
    return _serper_float_env(
        _SERPER_GATE_CACHE_TTL_ENV, _DEFAULT_SERPER_GATE_CACHE_TTL
    )


def reset_serper_budget_cache() -> None:
    """Drop the memoised gate decision so the next call re-reads. Used by tests
    and by anything that just changed SERPER_LIFETIME_LIMIT in-process."""
    global _serper_gate_cache
    _serper_gate_cache = None


def _serper_budget_ok() -> bool:
    """True when a live Serper call is within budget. FAIL-OPEN: any error here
    (Redis outage included) admits the call — a monitoring failure must never
    become an availability failure on the price path. Memoised for
    _serper_gate_cache_ttl() seconds; see the block comment above."""
    global _serper_gate_cache
    now = _time.monotonic()
    cached = _serper_gate_cache
    if cached is not None and now < cached[0]:
        return cached[1]
    try:
        allowed = serper_gate_allows()
    except Exception as e:  # noqa: BLE001 — never let the gate break the call
        logger.warning("[BUDGET] serper gate unavailable (%s) — failing open", e)
        allowed = True
    ttl = _serper_gate_cache_ttl()
    _serper_gate_cache = (now + ttl, allowed) if ttl > 0 else None
    return allowed


# ============================================
# SERPER CIRCUIT BREAKER (ENABLE_SERPER_BREAKER — opt-in, default OFF) — M13-32
# ============================================
# Serper — the highest-volume paid provider — had metering but NO circuit breaker
# (record_failure('serper') / is_circuit_closed('serper') had zero call sites). On
# the documented 403 state every compare still dispatched all six Serper entry
# points at their full timeout, per product, forever — no cooldown ever engaged.
# Gate _serper_post's dispatch on the breaker, record success/failure per response,
# and — like _serper_budget_ok — MEMOISE the breaker read so it adds no per-call
# blocking Redis round trip on the hot path (the exact event-loop hazard the block
# comment above exists to avoid). The memo is invalidated the moment a
# success/failure is recorded, so a trip/recovery takes effect on the very next
# call. Flag OFF -> none of this runs and _serper_post is byte-identical (every
# call dispatches, no breaker read, no record).
_serper_breaker_cache: Optional[tuple] = None  # (expires_at_monotonic, closed)


def _serper_breaker_enabled() -> bool:
    return os.getenv("ENABLE_SERPER_BREAKER", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _reset_serper_breaker_cache() -> None:
    global _serper_breaker_cache
    _serper_breaker_cache = None


def _serper_breaker_closed() -> bool:
    """Memoised is_circuit_closed('serper'), reusing the SERPER_GATE_CACHE_TTL
    window. FAIL-OPEN on any error. Invalidated by _serper_record_failure/success
    so the breaker's trip/recovery is seen on the next call."""
    global _serper_breaker_cache
    now = _time.monotonic()
    cached = _serper_breaker_cache
    if cached is not None and now < cached[0]:
        return cached[1]
    try:
        closed = is_circuit_closed("serper")
    except Exception as e:  # noqa: BLE001 — a monitoring failure must not block calls
        logger.warning("[CIRCUIT] serper breaker check failed (%s) — failing open", e)
        closed = True
    ttl = _serper_gate_cache_ttl()
    _serper_breaker_cache = (now + ttl, closed) if ttl > 0 else None
    return closed


def _serper_record_failure() -> None:
    """Record a Serper failure (timeout / 5xx / 403) and drop the breaker memo so
    a resulting trip engages immediately. No-op unless the breaker flag is ON."""
    if not _serper_breaker_enabled():
        return
    try:
        record_failure("serper")
    except Exception as e:  # noqa: BLE001
        logger.warning("[CIRCUIT] serper record_failure failed: %s", e)
    finally:
        _reset_serper_breaker_cache()


def _serper_record_success() -> None:
    """Record a Serper 200 and drop the breaker memo so a recovery closes the
    breaker promptly. No-op unless the breaker flag is ON."""
    if not _serper_breaker_enabled():
        return
    try:
        record_success("serper")
    except Exception as e:  # noqa: BLE001
        logger.warning("[CIRCUIT] serper record_success failed: %s", e)
    finally:
        _reset_serper_breaker_cache()


# ============================================
# FAIL-FAST SERPER TIMEOUT (ENABLE_SERPER_FAIL_FAST — opt-in, default OFF)
# ============================================
# The multi-key rotation loop below can stack N x the per-call timeout (3 keys x
# 15s = 45s) when free keys respond SLOWLY (throttled depletion-400s), starving
# the Serper-free genuine-BH adapter fan-out inside the price race. Opt-in
# fail-fast: a tighter connect/read budget + an overall rotation deadline +
# rotate-on-timeout so a slow key fails fast. Flag OFF -> the timeout stays 15.0
# and the loop is byte-identical (no deadline, no timeout-catch, no clock read).
import time as _time


def _serper_fail_fast_enabled() -> bool:
    """Fail-closed flag mirror (same truthy set as the other crons/flags)."""
    return os.getenv("ENABLE_SERPER_FAIL_FAST", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _serper_float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _serper_timeout():
    """httpx timeout for Serper calls. Flag OFF -> 15.0 (byte-identical to the
    pre-fail-fast literal). Flag ON -> a split connect/read budget (conservative
    canary defaults 3s connect / 10s read, env-tunable via SERPER_CONNECT_TIMEOUT
    / SERPER_READ_TIMEOUT) so a throttled key aborts fast instead of burning the
    full 15s. Keep SERPER_ROTATION_DEADLINE > SERPER_READ_TIMEOUT so a multi-key
    run still gets >=2 attempts."""
    if not _serper_fail_fast_enabled():
        return 15.0
    read = _serper_float_env("SERPER_READ_TIMEOUT", 10.0)
    connect = _serper_float_env("SERPER_CONNECT_TIMEOUT", 3.0)
    return httpx.Timeout(read, connect=connect)


def _serper_rotation_deadline() -> float:
    """Overall wall-clock budget (seconds) for the whole multi-key rotation loop,
    so N slow keys cannot stack to N x the per-call timeout. Conservative canary
    default 14s (> the 10s read default -> multi-key gets >=2 attempts). Env-tunable.

    #60 — this deadline is now UNCONDITIONAL (it used to apply only when
    ENABLE_SERPER_FAIL_FAST was on, and that flag defaults OFF). The hazard it
    bounds does NOT need the flag: with the flag off a throttled key answers
    SLOWLY with a depletion-400 rather than timing out, so the loop rotates and
    3 keys stacked ~45s inside structured_comparison_service's 15s
    _PRICE_RACE_TIMEOUT. The default MUST stay strictly under that race budget
    (pinned by tests/test_serper_fail_fast.py).

    The check is evaluated at the top of each loop iteration, so the bound is
    "deadline + at most one per-call timeout", not N x per-call timeout — the
    N-way stacking is what this removes.

    A value <=0 DISABLES the deadline (full rotation, no wall-clock bound),
    matching this repo's `<=0 disables the check` convention. It must never mean
    "make zero calls" — see the guard at the loop-top check."""
    return _serper_float_env("SERPER_ROTATION_DEADLINE", 14.0)


def _serper_now() -> float:
    """Monotonic clock read (indirected so the rotation deadline is testable)."""
    return _time.monotonic()


async def _serper_post(client, path: str, payload: Dict[str, Any]):
    """Breaker-gated wrapper over _serper_post_impl (M13-32).

    Flag OFF (default) -> delegates directly, byte-identical to the pre-breaker
    dispatch (no breaker read, no record, timeouts propagate identically). Flag ON
    -> short-circuits when the 'serper' breaker is OPEN (returns None so the
    caller's raise_for_status degrades to the same benign-empty path as a budget-
    out), records a failure on timeout / 5xx / 403 and a success on 200."""
    if not _serper_breaker_enabled():
        return await _serper_post_impl(client, path, payload)

    if not _serper_breaker_closed():
        logger.info("[CIRCUIT] serper breaker OPEN — short-circuiting Serper POST %s", path)
        return None

    try:
        response = await _serper_post_impl(client, path, payload)
    except httpx.TimeoutException:
        _serper_record_failure()
        raise

    if response is not None:
        status = getattr(response, "status_code", None)
        if status == 200:
            _serper_record_success()
        elif status is not None and (status >= 500 or status == 403):
            _serper_record_failure()
    return response


async def _serper_post_impl(client, path: str, payload: Dict[str, Any]):
    """Shared Serper POST with credit-exhaustion failover.

    Picks the active (first non-exhausted) key, POSTs to
    `{SERPER_BASE_URL}{path}` with the standard headers, and — if the response
    signals credit depletion — marks that key exhausted and retries with the
    NEXT non-exhausted key (bounded to len(keys) attempts). Returns the httpx
    Response of the FIRST non-exhaustion result (which the caller inspects /
    raise_for_status()es exactly as before), so response handling is unchanged.

    On the happy path (single healthy key) this fires exactly ONE POST and adds
    only one cheap Redis exhaustion-check read — byte-identical behaviour.

    The caller is responsible for the `if not <key>` guard BEFORE calling this
    (preserving the legacy short-circuit + no-record_usage semantics). Callers
    pass the active key implicitly via this helper; a None active key means all
    keys are exhausted and this helper is not reached.
    """
    keys = _resolve_serper_keys()

    # SINGLE-KEY INERT: 0 or 1 resolved keys (the common prod case) engage NO
    # exhaustion machinery — one direct POST with the single key, NO
    # _is_serper_key_exhausted read and NO _mark_serper_key_exhausted write and
    # NO rotation. Byte-identical to the pre-multikey single-POST path. The
    # exhaustion/rotation loop below runs ONLY when there are >=2 keys.
    if len(keys) <= 1:
        key = keys[0] if keys else None
        return await client.post(
            f"{SERPER_BASE_URL}{path}",
            headers={
                "X-API-KEY": key,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    attempts = 0
    max_attempts = max(1, len(keys))
    last_response = None
    # #60 — the overall rotation DEADLINE is UNCONDITIONAL; only the per-call
    # timeout + rotate-on-timeout stay behind ENABLE_SERPER_FAIL_FAST (so that
    # flag's existing semantics are preserved). Flag OFF still means: the
    # per-call timeout is 15.0 and a timeout re-raises exactly as an un-caught
    # one would — the ONLY flag-OFF difference is that N slow keys can no longer
    # stack past the wall-clock budget. The single-key path above short-circuits
    # before here, so it remains byte-identical (no clock read, no Redis read).
    fail_fast = _serper_fail_fast_enabled()
    deadline = _serper_rotation_deadline()
    start = _serper_now()
    last_timeout_exc: Optional[Exception] = None
    timed_out: set = set()  # keys that timed out THIS call (fail-fast local skip)
    while attempts < max_attempts:
        # Overall deadline — stop rotating once the wall-clock budget is spent so
        # N slow keys can't stack to N x the per-call timeout.
        #
        # `deadline > 0` is NOT decoration (#60 review, blocking 1). Making the
        # check unconditional turned SERPER_ROTATION_DEADLINE=0 into a silent
        # TOTAL Serper blackout for any multi-key config: deadline 0.0 makes the
        # very first loop-top comparison true, the loop breaks before any POST,
        # _serper_post returns None, and the caller's response.raise_for_status()
        # on None raises AttributeError straight into the broad `except` — a
        # benign empty result and zero calls, forever. That inverts this repo's
        # own `<=0 disables the check` convention (cron_warm_price_cache.py's
        # _serper_per_query_estimate / _serper_max_credits_per_run) on a value
        # that was completely INERT before #60, i.e. it is a brand-new footgun
        # sitting on the obvious rollback flip. <=0 now means "no deadline",
        # never "no calls".
        if deadline > 0 and (_serper_now() - start) >= deadline:
            break
        # exclude=timed_out advances past a key that timed out earlier in THIS
        # call; the set stays empty when the flag is off (byte-identical).
        key = _active_serper_key(exclude=timed_out)
        if not key:
            # All keys exhausted mid-loop — return the last response (if any) so
            # the caller's existing handling degrades gracefully.
            break
        attempts += 1
        try:
            response = await client.post(
                f"{SERPER_BASE_URL}{path}",
                headers={
                    "X-API-KEY": key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            # Flag OFF -> re-raise immediately (byte-identical: the timeout
            # propagates to the caller exactly as before). Flag ON -> a per-call
            # timeout ROTATES to the next key (a timeout is NOT a depletion
            # signal, so the key is NOT marked exhausted — a transiently-slow key
            # may be healthy). If every attempt times out, the last one is
            # re-raised below so the caller's except-path fires as before.
            if not fail_fast:
                raise
            last_timeout_exc = exc
            timed_out.add(key)  # skip this key for the rest of THIS call
            continue
        last_response = response
        # Inspect for credit exhaustion. Reading .text on a MagicMock is cheap;
        # on a real httpx.Response it is the already-buffered body.
        try:
            status = getattr(response, "status_code", None)
            body_text = getattr(response, "text", "") or ""
        except Exception:  # noqa: BLE001
            status = None
            body_text = ""
        if _response_signals_exhaustion(status, body_text):
            _mark_serper_key_exhausted(key)
            continue  # rotate to the next non-exhausted key
        return response
    # Fail-fast: every attempt timed out (no non-timeout response landed) —
    # re-raise the last timeout so the caller degrades / falls back to Bright
    # Data exactly as the pre-fail-fast timeout-propagation did.
    if fail_fast and last_response is None and last_timeout_exc is not None:
        raise last_timeout_exc
    return last_response


# ============================================
# ORIGINAL FUNCTIONS (backward compatibility)
# ============================================

async def search_product_price(product_name: str, country: str = "Bahrain") -> Dict[str, Any]:
    """
    Original function - Search for product prices.
    Kept for backward compatibility with comparison_service.py
    """
    country_codes = {
        "Bahrain": "bh",
        "Saudi Arabia": "sa",
        "UAE": "ae",
        "Kuwait": "kw",
        "Qatar": "qa",
        "Oman": "om"
    }
    
    code = country_codes.get(country, "bh")
    query = f"{product_name} price {country}"
    
    results = await search_product_prices(product_name, code)
    
    # Format for backward compatibility
    return {
        "query": query,
        "organic": results.get("organic", []),
        "shopping": results.get("shopping", []),
        "knowledge_graph": results.get("knowledge_graph")
    }


# ============================================
# CORE SEARCH FUNCTIONS
# ============================================

async def search_web(
    query: str,
    num_results: int = 10,
    country: str = "bh"
) -> Dict[str, Any]:
    """
    General web search.
    
    Args:
        query: Search query
        num_results: Number of results (max 100)
        country: Country code for localized results
    
    Returns:
        Search results with organic, featured snippets, etc.
    """
    # Bright Data fallback (2026-07-07) — when the Serper key is exhausted/absent,
    # fall back to the Bright Data SERP API (same {organic} shape). Inert unless
    # ENABLE_BRIGHTDATA_FALLBACK + the credentials are set → byte-identical to
    # Serper-only when off. Local import avoids any import-time coupling.
    from app.services.brightdata_service import _brightdata_enabled, bd_search_web

    if not _active_serper_key():
        if _brightdata_enabled():
            logger.info("[brightdata] Serper key unavailable — search_web fallback")
            return await bd_search_web(query, num_results, country)
        logger.warning("SERPER_API_KEY not set")
        return {"organic": [], "error": "Search not configured"}

    # #60 — budget gate. Degrades exactly like the key-unavailable branch above
    # (Bright Data when enabled, benign empty otherwise) so a budget-out is a
    # cheap degrade, not a dead end. Bright Data wiring itself is unchanged (#61).
    if not _serper_budget_ok():
        if _brightdata_enabled():
            logger.info("[brightdata] Serper budget exhausted — search_web fallback")
            return await bd_search_web(query, num_results, country)
        logger.warning("[BUDGET] serper budget exhausted — search_web degraded")
        return {"organic": [], "error": "Search budget exhausted"}

    try:
        async with httpx.AsyncClient(timeout=_serper_timeout()) as client:
            response = await _serper_post(
                client,
                "/search",
                {
                    "q": query,
                    "num": num_results,
                    "gl": country,
                    "hl": "en"
                }
            )
            response.raise_for_status()
            await _record_usage_async("serper")
            return response.json()

    except Exception as e:
        logger.error(f"Search error: {e}")
        if _brightdata_enabled():
            logger.info("[brightdata] Serper /search failed (%s) — fallback", str(e)[:60])
            return await bd_search_web(query, num_results, country)
        return {"organic": [], "error": str(e)}


# Bundle C § 1c A.3.3-fix-2 — Serper Shopping has thin GCC coverage.
# Direct-curl diagnostic (Session 52) showed gl=bh returns empty
# shopping[] for mainstream queries (iPhone 16, CeraVe, Centrum) while
# gl=us returns 20-40 items. The fallback below retries once with gl=us
# when the primary GCC country returns empty; downstream price_service
# converts USD→BHD via exchange_rate_service + tags source_method:
# 'converted_usd'. OPERATIONAL STOPGAP until Google Shopping's Bahrain
# merchant feed catches up.
_GCC_COUNTRIES = frozenset({"bh", "sa", "ae", "kw", "qa", "om"})


# #60 — per-country allow-list for the gl=<gcc> SHOPPING PRIMARY leg.
#
# The diagnostic this module is built on (Session 52, restated in
# tests/test_serper_gcc_fallback.py) found Serper Shopping returns an empty
# `shopping[]` for gl=bh|sa|ae|kw|qa|om SYSTEM-WIDE — Google has no GCC merchant
# feed. The primary leg was fired unconditionally anyway, so every GCC shopping
# search bought a known-empty result: one credit per product per compare against
# a 2,500-credit one-time pool.
#
# DEFAULT: empty -> the primary leg is not purchased for any GCC country, and
# the single gl=us call (the leg that actually returns data) runs alone. The
# response keeps `shopping_region="us_fallback"`, which is exactly what the
# empty-primary path already returned in production, so downstream selection,
# the USD->BHD conversion, and the admin fallback-rate dashboards are unchanged.
#
# ROLLBACK / FUTURE FEED: set SERPER_SHOPPING_PRIMARY_COUNTRIES="bh,sa,..." to
# restore the concurrent two-leg behaviour for those countries — an env flip, no
# redeploy. Selection is identical when it fires: a non-empty primary still wins
# and still tags `shopping_region=<country>`.
_SHOPPING_PRIMARY_COUNTRIES_ENV = "SERPER_SHOPPING_PRIMARY_COUNTRIES"


# #60 review (observability) — with the allow-list empty the gl=<gcc> primary is
# never purchased, so `shopping_region` reads "us_fallback" BY CONSTRUCTION and
# the admin fallback-rate dashboard becomes structurally 100%: it can no longer
# show a GCC merchant feed appearing. The evidence for dropping the leg is a
# Session-52 diagnostic that was not re-probed, and ae/sa are the codes most
# likely to grow a real Google Shopping feed — so count the skips (module-level,
# never resets, diagnostics only; same idiom as
# structured_comparison_service._CACHE_READ_REJECTED_COUNT) rather than letting
# the decision become invisible. A non-zero counter with a 100% us_fallback rate
# says "we chose not to look", not "there is nothing there".
_SHOPPING_PRIMARY_SKIPPED_COUNT = 0


def shopping_primary_skipped_count() -> int:
    """How many times a GCC gl=<country> shopping primary was skipped because the
    country is not on SERPER_SHOPPING_PRIMARY_COUNTRIES. Diagnostics only."""
    return _SHOPPING_PRIMARY_SKIPPED_COUNT


def _shopping_primary_countries() -> frozenset:
    """Country codes whose gl=<country> shopping primary is still worth buying.
    Read fresh each call so a Railway env update takes effect without a restart."""
    raw = (os.environ.get(_SHOPPING_PRIMARY_COUNTRIES_ENV) or "").strip()
    if not raw:
        return frozenset()
    return frozenset(
        part.strip().lower() for part in raw.split(",") if part.strip()
    )


# Bundle C HOTFIX-2 round 2 — GPT-emitted product_info["search_query"]
# sometimes appends operator-style suffixes like "price", "buy", "best
# price" because PRODUCT_PARSER_PROMPT (extraction_service.py:71+82)
# tells GPT to emit "an optimized search query for price searches".
# Direct curl proves these suffixes KILL Google Shopping match:
#   q="Apple iPhone 16 price" gl=us → 0 items
#   q="iPhone 16"             gl=us → 20 items
# Strip defensively so cached + new GPT outputs both work. The match
# is case-insensitive, only trailing tokens, only the operator words
# below (does not touch product-essential keywords like "Pro", "Plus").
import re as _re

_SHOPPING_QUERY_TAIL_NOISE = _re.compile(
    r"(?:\s+(?:price|prices|pricing|cost|buy|best\s+price|cheapest|deals?|sale|"
    r"on\s+sale|amazon|noon|carrefour|bahrain|saudi(?:\s+arabia)?|uae|"
    r"dubai|kuwait|qatar|oman|bhd|sar|aed|kwd|qar|omr|usd))+\s*$",
    _re.IGNORECASE,
)


def _clean_shopping_query(product: str) -> str:
    """Strip trailing operator-style suffixes that wreck Google Shopping
    match. Idempotent — calling twice is a no-op. Preserves all interior
    tokens (only the trailing run is removed). Applied repeatedly until
    no more trailing tail noise — handles 'iPhone price Bahrain BHD buy'
    by chewing one operator-run at a time."""
    if not product:
        return product
    prev = None
    cleaned = product
    while cleaned != prev:
        prev = cleaned
        cleaned = _SHOPPING_QUERY_TAIL_NOISE.sub("", cleaned).strip()
    return cleaned or product  # never return empty string


async def _do_serper_shopping(product: str, gl: str) -> Dict[str, Any]:
    """Single Serper Shopping call. Records usage on HTTP 200. Returns
    parsed JSON or {} on error. No retry, no fallback — fallback logic
    lives in the caller (search_product_prices)."""
    try:
        async with httpx.AsyncClient(timeout=_serper_timeout()) as client:
            shopping_response = await _serper_post(
                client,
                "/shopping",
                {
                    "q": product,
                    "gl": gl,
                    "hl": "en",
                    "num": 10
                }
            )
            if shopping_response.status_code == 200:
                await _record_usage_async("serper")
                return shopping_response.json()
            # Bundle C v1.1 § 1c SERPER_SHOPPING_NON_200 — capture what
            # Serper actually returns when not 200 so we can disambiguate
            # the 3 likely production failure modes:
            #   1. HTTP 429 + Retry-After  → rate limit (op fix)
            #   2. HTTP 200 empty shopping  → genuine coverage gap
            #      (this branch never fires for empty-but-200; here for
            #      completeness as a reminder that 200 is the success arm)
            #   3. HTTP 4xx other-shape    → request-side bug grep missed
            # All Serper POSTs in this codebase explicitly set
            # Content-Type: application/json AND use httpx json= kwarg
            # (auto-set) — verified by grep at all 7 sites. So a 400
            # here would point to a different cause than the header.
            # Always-on WARNING — appears in Railway prod without flag.
            # Body truncated to 300 chars to keep log lines bounded.
            try:
                body_snippet = (shopping_response.text or "")[:300]
            except Exception:  # noqa: BLE001
                body_snippet = "<unreadable>"
            retry_after = shopping_response.headers.get("retry-after")
            ratelimit_remaining = shopping_response.headers.get(
                "x-ratelimit-remaining"
            )
            logger.warning(
                "SERPER_SHOPPING_NON_200 gl=%s status=%s "
                "retry_after=%s ratelimit_remaining=%s "
                "body=%r product=%r",
                gl,
                shopping_response.status_code,
                retry_after,
                ratelimit_remaining,
                body_snippet,
                product[:80],
            )
            return {}
    except Exception as e:
        logger.error(f"Serper shopping call error (gl={gl}): {e}")
        return {}


async def search_product_prices(
    product: str,
    country: str = "bh",
    currency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for product prices via Serper Shopping API.

    Bundle C § 1c A.3.3-fix-2: when the GCC primary call returns an empty
    `shopping[]` array, retry ONCE with `gl=us` so downstream USD→BHD
    conversion can land real prices. The response's `shopping_region`
    field identifies which call's items are returned so admin
    dashboards can monitor fallback rate.

    Organic search is deferred to search_price_organic() and only
    called if both shopping calls return empty (Saudi-only items like
    Almarai laban — pipeline naturally falls through to Tier 1.5).
    """
    if not _active_serper_key():
        return {"shopping": [], "organic": [], "error": "Search not configured"}

    # #60 — budget gate. Same benign empty shape as the no-key branch above: the
    # cascade reads `shopping`/`organic`, finds nothing, and drops to Tier 1.5 /
    # 2 / 3. A budget-out therefore yields a PEND or an estimate — never a
    # relaxed price (the correctness gates downstream are untouched).
    if not _serper_budget_ok():
        logger.warning("[BUDGET] serper budget exhausted — shopping search degraded")
        return {"shopping": [], "organic": [], "error": "Search budget exhausted"}

    # HOTFIX-2 round 2 — drop GPT-emitted " price"/"buy"/etc. tails.
    # Both primary GCC and us_fallback share the cleaned string so
    # behaviour is consistent. Log when we actually changed something
    # so Ahmed can see in Railway whether old GPT outputs are still
    # producing dirty queries.
    original_product = product
    product = _clean_shopping_query(product)
    if product != original_product:
        logger.info(
            f"[SHOPPING_QUERY_CLEAN] before={original_product!r} after={product!r}"
        )

    # genuine-BH starvation fix (2026-06-27) — for a GCC country, fire the gl=country
    # primary AND the gl=us fallback CONCURRENTLY rather than sequentially. Google has
    # NO Bahrain shopping feed, so the gl=bh primary returns 0 essentially every time
    # and the gl=us fallback was ALWAYS reached — but it ran ~3s AFTER the dead gl=bh
    # call, stealing budget the downstream 15s genuine-BH curl fan_out needs. Running
    # them in parallel reclaims that ~3s. Selection is UNCHANGED: prefer gl=country
    # items when present (genuine local feed), else the gl=us fallback (powers the
    # USD->BHD conversion + parks the converted_fallback). Net Serper calls are the
    # same as before for the empty-primary path (the dominant GCC case); only WHEN the
    # second call fires changes (concurrent, not serial). Non-GCC countries keep the
    # single-call, no-fallback behaviour byte-for-byte.
    if country in _GCC_COUNTRIES:
        # #60 — the gl=<country> primary is only purchased for allow-listed
        # countries (default: none). Google has no GCC shopping feed, so the
        # primary returned 0 essentially every time and the gl=us fallback was
        # ALWAYS the leg that produced items. Skipping the dead leg halves the
        # credits this call costs; the empty-primary result shape below is
        # byte-identical to what production already returned.
        if country in _shopping_primary_countries():
            primary, fallback = await asyncio.gather(
                _do_serper_shopping(product, gl=country),
                _do_serper_shopping(product, gl="us"),
            )
        else:
            global _SHOPPING_PRIMARY_SKIPPED_COUNT
            _SHOPPING_PRIMARY_SKIPPED_COUNT += 1
            logger.debug(
                "[SHOPPING] gl=%s primary skipped (not on %s) — shopping_region "
                "will read us_fallback by construction; skips so far: %s",
                country, _SHOPPING_PRIMARY_COUNTRIES_ENV,
                _SHOPPING_PRIMARY_SKIPPED_COUNT,
            )
            primary = {}
            fallback = await _do_serper_shopping(product, gl="us")
        primary_shopping = primary.get("shopping", []) or []
        if primary_shopping:
            return {
                "shopping": primary_shopping,
                "organic": [],
                "query": product,
                "shopping_region": country,
            }
        fallback_shopping = fallback.get("shopping", []) or []
        if fallback_shopping:
            return {
                "shopping": fallback_shopping,
                "organic": [],
                "query": product,
                "shopping_region": "us_fallback",
            }
        # Both empty — pipeline falls through to Tier 1.5 / Tier 2 / Tier 3.
        return {
            "shopping": [],
            "organic": [],
            "query": product,
            "shopping_region": "us_fallback",
        }

    # Non-GCC primary — single call, no gl=us fallback.
    primary = await _do_serper_shopping(product, gl=country)
    primary_shopping = primary.get("shopping", []) or []
    if primary_shopping:
        return {
            "shopping": primary_shopping,
            "organic": [],
            "query": product,
            "shopping_region": country,
        }
    # Non-GCC primary returned empty — no fallback, just echo the primary
    # region tag so callers know we tried.
    return {
        "shopping": [],
        "organic": [],
        "query": product,
        "shopping_region": country,
    }


async def search_price_organic(
    product: str,
    country: str = "bh",
) -> Dict[str, Any]:
    """
    Organic search for price context — only called when Tier 1 shopping fails.
    Returns organic results for GPT Tier 2 price extraction.
    """
    # Bright Data fallback (2026-07-07) — inert unless ENABLE_BRIGHTDATA_FALLBACK
    # + creds are set (byte-identical Serper-only when off).
    from app.services.brightdata_service import _brightdata_enabled, bd_search_web

    if not _active_serper_key():
        if _brightdata_enabled():
            return {**(await bd_search_web(product, 10, country)), "query": product}
        return {"organic": [], "error": "Search not configured"}

    # #60 — budget gate, degrading exactly like the key-unavailable branch above.
    if not _serper_budget_ok():
        if _brightdata_enabled():
            logger.info("[brightdata] Serper budget exhausted — price-organic fallback")
            return {**(await bd_search_web(product, 10, country)), "query": product}
        logger.warning("[BUDGET] serper budget exhausted — price-organic degraded")
        return {"organic": [], "error": "Search budget exhausted"}

    country_terms = {
        "bh": "Bahrain price BHD buy",
        "sa": "Saudi Arabia price SAR buy",
        "ae": "UAE Dubai price AED buy",
        "kw": "Kuwait price KWD buy",
        "qa": "Qatar price QAR buy",
        "om": "Oman price OMR buy"
    }
    location_term = country_terms.get(country, "price buy")
    search_query = f"{product} {location_term}"

    try:
        async with httpx.AsyncClient(timeout=_serper_timeout()) as client:
            response = await _serper_post(
                client,
                "/search",
                {
                    "q": search_query,
                    "gl": country,
                    "hl": "en",
                    "num": 10
                }
            )

            results = {}
            if response.status_code == 200:
                results = response.json()
                await _record_usage_async("serper")
            elif _brightdata_enabled():
                # Serper non-200 (depletion/error) — fall back to Bright Data.
                logger.info("[brightdata] Serper price-organic HTTP %s — fallback", response.status_code)
                return {**(await bd_search_web(search_query, 10, country)), "query": search_query}

            return {
                "organic": results.get("organic", []),
                "knowledge_graph": results.get("knowledgeGraph"),
                "query": search_query
            }

    except Exception as e:
        logger.error(f"Price organic search error: {e}")
        if _brightdata_enabled():
            logger.info("[brightdata] Serper price-organic failed (%s) — fallback", str(e)[:60])
            return {**(await bd_search_web(search_query, 10, country)), "query": search_query}
        return {"organic": [], "error": str(e)}


async def search_product_specs(
    product: str,
    category: str = "electronics"
) -> Dict[str, Any]:
    """
    Search for product specifications.
    
    Args:
        product: Product name
        category: Product category for targeted search
    """
    # Category-specific search terms
    category_terms = {
        "electronics": "specifications specs features technical details",
        "grocery": "ingredients nutrition facts details",
        "beauty": "ingredients benefits how to use",
        "fashion": "material size guide care instructions",
        "home": "specifications dimensions features",
    }
    
    spec_terms = category_terms.get(category, "specifications details features")
    query = f"{product} {spec_terms}"
    
    return await search_web(query, num_results=10)


async def search_product_reviews(
    product: str,
    include_video: bool = False
) -> Dict[str, Any]:
    """
    Search for product reviews and ratings.
    
    Args:
        product: Product name
        include_video: Include video review results
    """
    query = f"{product} review rating user experience pros cons"
    
    results = await search_web(query, num_results=10)
    
    if include_video:
        video_results = await search_videos(f"{product} review")
        results["videos"] = video_results.get("videos", [])
    
    return results


async def search_videos(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for videos (reviews, tutorials, etc.)."""
    if not _active_serper_key():
        return {"videos": [], "error": "Search not configured"}

    # #60 — budget gate; same benign empty shape as the no-key branch.
    if not _serper_budget_ok():
        logger.warning("[BUDGET] serper budget exhausted — video search skipped")
        return {"videos": [], "error": "Search budget exhausted"}

    try:
        async with httpx.AsyncClient(timeout=_serper_timeout()) as client:
            response = await _serper_post(
                client,
                "/videos",
                {
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            await _record_usage_async("serper")
            return response.json()

    except Exception as e:
        logger.error(f"Video search error: {e}")
        return {"videos": [], "error": str(e)}


async def search_images(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for product images."""
    if not _active_serper_key():
        return {"images": [], "error": "Search not configured"}

    # #60 — budget gate. The image pipeline already has its OWN daily counter
    # (api_budget_service.try_consume_serper_image_credit); this is the
    # LIFETIME ceiling on top of it, so images cannot spend a depleted account
    # down. Non-critical path: the 4-state ProductImage fallback renders a
    # placeholder, so a skip never breaks a comparison.
    if not _serper_budget_ok():
        logger.warning("[BUDGET] serper budget exhausted — image search skipped")
        return {"images": [], "error": "Search budget exhausted"}

    try:
        async with httpx.AsyncClient(timeout=_serper_timeout()) as client:
            response = await _serper_post(
                client,
                "/images",
                {
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            await _record_usage_async("serper")
            return response.json()

    except Exception as e:
        # Image search is NON-CRITICAL — the image pipeline (ProductImage's
        # 4-state fallback) degrades to a placeholder, so a failure here NEVER
        # breaks the comparison. Log at WARNING (not ERROR → Sentry noise:
        # PYTHON-FASTAPI-M/-K, super-low actionability, 0 users) and include the
        # exception TYPE so an empty str(e) (some httpx/transient errors carry no
        # message) is still debuggable.
        logger.warning(
            f"Image search failed (non-critical, placeholder fallback): "
            f"{type(e).__name__}: {e}"
        )
        return {"images": [], "error": str(e)}


async def search_news(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for recent news about a product."""
    if not _active_serper_key():
        return {"news": [], "error": "Search not configured"}

    # #60 — budget gate; same benign empty shape as the no-key branch.
    if not _serper_budget_ok():
        logger.warning("[BUDGET] serper budget exhausted — news search skipped")
        return {"news": [], "error": "Search budget exhausted"}

    try:
        async with httpx.AsyncClient(timeout=_serper_timeout()) as client:
            response = await _serper_post(
                client,
                "/news",
                {
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            await _record_usage_async("serper")
            return response.json()

    except Exception as e:
        logger.error(f"News search error: {e}")
        return {"news": [], "error": str(e)}


# ============================================
# GCC Store-specific searches
# ============================================

GCC_RETAILERS = {
    "bahrain": [
        "carrefour bahrain",
        "lulu hypermarket bahrain",
        "sharaf dg bahrain",
        "virgin megastore bahrain",
        "best al yousifi",
        "ashraf"
    ],
    "saudi_arabia": [
        "amazon.sa",
        "jarir bookstore",
        "extra stores",
        "carrefour saudi",
        "noon.com"
    ],
    "uae": [
        "amazon.ae",
        "noon.com",
        "sharaf dg",
        "carrefour uae",
        "lulu hypermarket"
    ],
    "kuwait": [
        "xcite kuwait",
        "best al yousifi",
        "carrefour kuwait",
        "lulu hypermarket"
    ],
    "qatar": [
        "carrefour qatar",
        "lulu hypermarket qatar",
        "jarir bookstore qatar",
        "virgin megastore qatar"
    ],
    "oman": [
        "carrefour oman",
        "lulu hypermarket oman",
        "sharaf dg oman"
    ]
}


async def search_gcc_retailer_prices(
    product: str,
    region: str = "bahrain"
) -> List[Dict[str, Any]]:
    """
    Search specific GCC retailers for prices.
    
    Returns list of prices from different retailers.
    """
    retailers = GCC_RETAILERS.get(region, GCC_RETAILERS["bahrain"])
    results = []
    
    # Search top 3 retailers
    for retailer in retailers[:3]:
        query = f"{product} {retailer} price"
        search_result = await search_web(query, num_results=3)
        
        results.append({
            "retailer": retailer,
            "results": search_result.get("organic", [])[:2]
        })
    
    return results


# ============================================
# Utility functions
# ============================================

def extract_prices_from_text(text: str, currency: str = "BHD") -> List[Dict]:
    """
    Extract price patterns from text.
    
    Patterns:
    - BHD 99.99
    - 99.99 BHD
    - BD 99.99
    - $99.99
    """
    import re
    
    patterns = [
        # BHD/BD patterns
        r'(?:BHD|BD)\s*(\d+(?:\.\d{1,3})?)',
        r'(\d+(?:\.\d{1,3})?)\s*(?:BHD|BD)',
        # SAR patterns
        r'(?:SAR|SR)\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:SAR|SR)',
        # AED patterns
        r'(?:AED|DHS?)\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:AED|DHS?)',
        # USD patterns
        r'\$\s*(\d+(?:\.\d{1,2})?)',
        # Generic number with decimal
        r'(\d+\.\d{2,3})\s*(?:dinar|riyal)?'
    ]
    
    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match)
                if 0.1 < amount < 10000:  # Reasonable price range
                    prices.append({
                        "amount": amount,
                        "currency": currency,
                        "raw_text": match
                    })
            except ValueError:
                continue
    
    return prices
