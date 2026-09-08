"""API Budget Service — credit tracking + circuit breakers for external APIs.

Uses cache_service helpers (_redis_get, _redis_set, _redis_incr, _redis_expire)
for Redis access. Gracefully degrades if Redis is unavailable.
"""
import asyncio
import json
import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

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
    # Scraping audit 2026-07-08 — Bright Data SERP fallback. Free tier is
    # ~5,000 requests/MONTH (not lifetime). Bounds the fallback-of-last-resort
    # under Serper depletion; INERT until ENABLE_BRIGHTDATA_BUDGET_GATE is ON —
    # only the gated path in brightdata_service reads this entry, so its mere
    # presence is behaviour-neutral (nothing else references "brightdata").
    "brightdata": {
        "monthly_limit": 4500,      # ~5,000/mo free, save 500 buffer
        "warn_at": 4000,
        "is_lifetime": False,       # Monthly reset (budget:brightdata:<YYYY-MM>)
    },
    "serper": {
        "monthly_limit": 2200,      # 2,500 credits, save 300 buffer
        "warn_at": 2000,
        "is_lifetime": True,
    },
    # W1-3 (LS-FAILURE-MODES-COST-02) — OpenAI was the ONE provider with no
    # budget row at all, despite gating whether any compare is worth anything.
    # This is a BUDGET ROW FOR FUTURE METERING, NOT PART OF THE BREAKER.
    # It is INERT today, and more inert than the `brightdata` entry above:
    # nothing calls has_budget("openai") or record_usage("openai"), and the
    # circuit-breaker path this unit wires up does NOT read it either — the
    # breaker keys off `circuit:openai` via _circuit_key(), which never
    # consults PROVIDER_CONFIGS (renaming this key leaves every breaker test
    # green; adversarial review MINOR 7). The only live effect of the row's
    # presence is cosmetic: PROVIDER_CONFIGS-iterating admin surfaces
    # (get_usage_summary, get_provider_burn) now list an `openai` line reading
    # 0/100000. The limit is a REQUEST count, not tokens or dollars; the real
    # spend ceilings are OPENAI_MAX_RETRIES (#117) and the OpenAI account cap.
    "openai": {
        "monthly_limit": 100000,    # request-count ceiling, monthly reset
        "warn_at": 90000,
        "is_lifetime": False,       # Monthly reset (budget:openai:<YYYY-MM>)
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


# ============================================================================
# #60 — env-tunable Serper ceiling + the gate serper_service consults.
#
# WHY this is not just `has_budget("serper")`: the 2200 above is a FREE-tier
# ceiling (2,500 one-time credits minus a 300 buffer). Production runs a PAID
# key, and `scripts/cron_warm_price_cache.py:118-131` documents deliberately
# NOT consulting has_budget for exactly that reason — once lifetime burn passes
# 2200 the counter would wrongly report "exhausted" and darken a healthy paid
# key. Hardcoding the free-tier number and then gating live traffic on it would
# reproduce that failure mode on the price path.
#
# So the ceiling becomes a knob, and — see _serper_gate_engaged below — the
# GATE only arms when that knob has actually been turned:
#   SERPER_LIFETIME_LIMIT unset  -> 2200 for accounting (byte-identical to the
#                                   packaged value: get_remaining("serper") ==
#                                   2200 as before) and the gate is INERT.
#   SERPER_LIFETIME_LIMIT=250000 -> the paid key's real ceiling; the gate arms
#                                   there and admits calls far past 2200.
#   SERPER_LIFETIME_LIMIT=0      -> gate explicitly DISABLED (same effect as
#                                   unset). This is the documented rollback env
#                                   flip for #60: one Railway variable, no
#                                   redeploy.
# Read fresh on every call (mirrors _serper_image_daily_budget) so a Railway env
# update takes effect without a restart.
# ============================================================================
_SERPER_LIFETIME_LIMIT_ENV = "SERPER_LIFETIME_LIMIT"


def _serper_declared_limit() -> Optional[int]:
    """The ceiling the OPERATOR explicitly declared via SERPER_LIFETIME_LIMIT.

    None when the var is absent, blank or unparseable — "no ceiling has been
    declared", which is deliberately NOT the same statement as "the ceiling is
    2200". _serper_gate_engaged() turns on exactly that distinction."""
    raw = (os.environ.get(_SERPER_LIFETIME_LIMIT_ENV) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _serper_lifetime_limit() -> int:
    """Effective serper lifetime ceiling for ACCOUNTING (get_remaining, the
    80%-burn tripwire, has_budget's arithmetic). Falls back to the packaged
    PROVIDER_CONFIGS value when no positive ceiling is declared, so an unset
    env is byte-identical to the pre-#60 numbers."""
    default = PROVIDER_CONFIGS["serper"]["monthly_limit"]
    declared = _serper_declared_limit()
    if declared is None or declared <= 0:
        return default
    return declared


def _provider_limit(provider: str) -> int:
    """The effective ceiling for `provider` — the env-resolved one for serper,
    the packaged PROVIDER_CONFIGS value for everyone else. 0 for unknown
    providers (callers already treat unknown as "no budget")."""
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return 0
    if provider == "serper":
        return _serper_lifetime_limit()
    return config["monthly_limit"]


def _provider_warn_at(provider: str) -> float:
    """The effective "budget warning" threshold for `provider`.

    #60 review (blocking 2): `limit` became env-resolved for serper but the
    warn threshold stayed the packaged literal, so declaring the paid ceiling
    (SERPER_LIFETIME_LIMIT=250000) made every has_budget("serper") call past
    2000 used credits emit `[BUDGET] serper budget warning (5136/250000)` — a
    false depletion alarm at 2% utilisation, and #60 wires the gate into all
    six serper entry points, so that is ~10-12 spurious WARN lines per compare
    forever, on the exact signal an operator uses to spot REAL depletion.

    The threshold therefore scales with the EFFECTIVE ceiling, preserving the
    ratio the packaged pair encodes (2000/2200 ~= 91%). Integer arithmetic, so
    when the effective ceiling IS the packaged one the result is exactly the
    packaged warn_at — byte-identical for an unset serper env and for every
    other provider (none of whose ceilings are env-resolved)."""
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return float("inf")
    packaged_warn = config.get("warn_at")
    if packaged_warn is None:
        return float("inf")
    packaged_limit = config.get("monthly_limit") or 0
    limit = _provider_limit(provider)
    if not packaged_limit or limit == packaged_limit:
        return packaged_warn
    return packaged_warn * limit // packaged_limit


def _serper_gate_engaged() -> bool:
    """Is the #60 live-spend gate ARMED?

    ONLY when the operator declared a POSITIVE ceiling via
    SERPER_LIFETIME_LIMIT. Absent — or <=0, the explicit off switch — leaves the
    gate INERT: every live call is admitted and 2200 stays what it always was,
    a get_remaining()/dashboard number.

    WHY default-INERT (#60 review, blocking 4). The packaged 2200 is a FREE-tier
    ceiling (2,500 one-time credits minus a 300 buffer) and production runs a
    PAID key. Shipping the gate armed at 2200 means that the moment the live
    lifetime counter crosses it, ALL SIX serper entry points go dark app-wide —
    price, specs, reviews, images and the 4-way discovery fan-out — and the
    price-cache warmer with them, on nothing but a number nobody declared. That
    is precisely the failure mode `scripts/cron_warm_price_cache.py:118-131`
    documents refusing to reproduce, and precisely what #60's own warning block
    told the implementer not to reproduce. A scheduled outage is not a budget
    control.

    So the gate is OPT-IN: declare the key's real ceiling and live spend is
    metered AND bounded; declare nothing and spend is metered only. The
    accounting side (`_serper_lifetime_limit`, get_remaining, the burn alert)
    is unchanged either way, so depletion is still visible on the dashboard and
    in the 80%-burn alert before anything is ever blocked."""
    declared = _serper_declared_limit()
    return declared is not None and declared > 0


# One-shot config log — without it the gate's state is invisible to an operator
# (#60 review, blocking 4: "no startup log of the effective ceiling"). Module
# global rather than a startup hook so it fires in whatever process actually
# spends credits (web, warmer cron, scripts).
_serper_gate_config_logged = False


def _log_serper_gate_config_once(engaged: bool) -> None:
    """Log, once per process, whether live Serper spend is actually gated and
    at what ceiling. Best-effort — never raises, never blocks the gate."""
    global _serper_gate_config_logged
    if _serper_gate_config_logged:
        return
    _serper_gate_config_logged = True
    try:
        limit = _provider_limit("serper")
        if engaged:
            logger.info(
                "[BUDGET] serper spend gate ENGAGED — ceiling %s "
                "(SERPER_LIFETIME_LIMIT), remaining %s",
                limit, get_remaining("serper"),
            )
        else:
            logger.info(
                "[BUDGET] serper spend gate INERT — %s is not set, so live "
                "Serper calls are METERED but never blocked. The packaged %s is "
                "a FREE-tier number and must not darken a paid key; set %s to "
                "this key's real ceiling to arm the gate.",
                _SERPER_LIFETIME_LIMIT_ENV, limit, _SERPER_LIFETIME_LIMIT_ENV,
            )
    except Exception:  # noqa: BLE001 — observability must never break the gate
        pass


def serper_gate_allows() -> bool:
    """Should a LIVE Serper call be dispatched?

    The single gate `serper_service` consults before spending a credit. Inert
    unless an operator declared a ceiling (see _serper_gate_engaged). Fails
    OPEN on any error (a dead Upstash must never disable Serper), matching
    has_budget's own convention."""
    try:
        engaged = _serper_gate_engaged()
        _log_serper_gate_config_once(engaged)
        if not engaged:
            return True
        return has_budget("serper")
    except Exception as e:  # noqa: BLE001 — a gate failure must never block spend
        logger.warning(f"[BUDGET] serper gate check failed: {e} — failing open")
        return True


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


# genuine-price serper-multikey — Redis prefix for the per-key exhaustion flag.
# Kept in sync with serper_service._SERPER_EXHAUSTED_PREFIX so the counter-scoping
# here and the failover there agree on which key is "active". Read directly via
# cache_service (no serper_service import → no circular dependency).
_SERPER_EXHAUSTED_PREFIX = "serper:exhausted:"


def _serper_env_keys() -> list:
    """Ordered Serper key list from env, read FRESH each call (Railway env update
    / rotation takes effect without a restart). Priority: SERPER_API_KEYS
    (comma-separated) then the single SERPER_API_KEY. Trimmed, blanks skipped,
    order-preserving de-dupe. Self-contained (no serper_service import) to avoid
    a serper_service ↔ api_budget_service cycle."""
    raw_multi = (os.environ.get("SERPER_API_KEYS") or "").strip()
    keys: list = []
    if raw_multi:
        for part in raw_multi.split(","):
            k = part.strip()
            if k and k not in keys:
                keys.append(k)
        if keys:
            return keys
    single = (os.environ.get("SERPER_API_KEY") or "").strip()
    return [single] if single else []


def _serper_key_prefix() -> str:
    """First 8 chars of the ACTIVE Serper key (read fresh each call so a Railway
    env update / key rotation takes effect without a restart, mirroring
    _serper_image_daily_budget).

    This scopes the Serper lifetime counter to the key that burned the credits:
    a rotation starts a fresh honest counter instead of inheriting the previous
    account's burn (the 5136-across-4-accounts false-trip, S2 G6). Falls back to
    a stable 'nokey' sentinel when no key is configured so the key stays
    deterministic.

    genuine-price serper-multikey: with SERPER_API_KEYS (comma-separated) set,
    the counter tracks whichever key is CURRENTLY active (first NON-exhausted)
    so each rotated-to key gets its own honest lifetime counter. With only the
    single SERPER_API_KEY set (no SERPER_API_KEYS), this is byte-identical to
    the pre-multikey scoping (first 8 chars of that key, or 'nokey')."""
    keys = _serper_env_keys()
    if not keys:
        return _SERPER_NO_KEY_PREFIX
    # SINGLE-KEY INERT: with 0 or 1 resolved keys (the common prod case: only
    # SERPER_API_KEY set, no SERPER_API_KEYS) there is NO exhaustion machinery —
    # the prefix is that key's first 8 chars with NO Redis exhaustion read.
    # Byte-identical to the pre-multikey scoping.
    if len(keys) == 1:
        return keys[0][:8]
    # MULTI-KEY (>=2): prefer the first key NOT flagged exhausted; if all are
    # flagged (or Redis is down / no flags), fall back to the first key so the
    # counter stays a stable, deterministic target.
    for key in keys:
        prefix = key[:8]
        try:
            if not _redis_get(_SERPER_EXHAUSTED_PREFIX + prefix):
                return prefix
        except Exception:  # noqa: BLE001
            return prefix
    return keys[0][:8]


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
        # #60 — serper's ceiling is env-resolved (SERPER_LIFETIME_LIMIT); every
        # other provider resolves to its packaged PROVIDER_CONFIGS value, so this
        # is byte-identical for them and for an unset serper env.
        limit = _provider_limit(provider)
        raw = _redis_get(_budget_key(provider))
        if raw is None:
            return True  # No usage yet or Redis down
        used = int(raw)
        remaining = limit - used
        if remaining <= 0:
            logger.warning(f"[BUDGET] {provider} budget exhausted ({used}/{limit})")
            return False
        # #60 — the warn threshold tracks the EFFECTIVE ceiling too, so raising
        # SERPER_LIFETIME_LIMIT does not turn a 2% utilisation into a permanent
        # "budget warning" on every call (see _provider_warn_at).
        if used >= _provider_warn_at(provider):
            logger.warning(f"[BUDGET] {provider} budget warning ({used}/{limit})")
        return True
    except Exception as e:
        logger.warning(f"[BUDGET] Error checking {provider}: {e}")
        return True  # fail-open


def _burn_threshold(provider: str) -> int:
    """80%-of-ceiling credit count for `provider` (0 for unknown providers).
    #60 — tracks the EFFECTIVE (env-resolved) ceiling so raising the serper
    limit moves the burn tripwire with it instead of alerting forever."""
    return int(_provider_limit(provider) * WARN_BURN_FRACTION)


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
        limit = _provider_limit(provider)  # #60 — effective (env-resolved) ceiling
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


def _half_open_probe_key(provider: str, state: Dict[str, Any]) -> str:
    """#115 — the atomic half-open probe counter key. Scoped by the trip's
    `tripped_at` so every OPEN->HALF_OPEN window gets a FRESH counter with no
    reset write (a delete-then-INCR reset would itself race under concurrent
    gate checks); a re-trip writes a new tripped_at and thereby a new counter.
    Old windows expire via the _CB_TTL set on first increment."""
    return f"{_circuit_key(provider)}:half_open:{int(state.get('tripped_at', 0) or 0)}"


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
                # Transition to half-open. M13-31: do NOT early-return True here —
                # that admitted an UNCOUNTED probe (the transition call), on top of
                # the ones the HALF_OPEN branch below then admitted, so the probe
                # budget was effectively never spent. Set up the half-open state
                # and FALL THROUGH to the single admission branch, which counts it.
                state["state"] = CB_HALF_OPEN
                state["half_open_calls"] = 0
                logger.info(f"[CIRCUIT] {provider} transitioning to half-open")
                # fall through to the CB_HALF_OPEN admission branch
            else:
                return False
        if state["state"] == CB_HALF_OPEN:
            # M13-31 landed the increment; #115 makes it ATOMIC. The old shape
            # was a decode -> +1 -> _redis_set read-modify-write on the JSON
            # blob: safe while inline-sync (no loop yield => gate checks
            # serialise), UNSAFE once ENABLE_ASYNC_REDIS_OFFLOAD wraps the gate
            # in asyncio.to_thread — parallel threads all read the same
            # half_open_calls and admit MULTIPLE paid render probes. The
            # admission now comes from a single Redis INCR on a per-trip-window
            # side key (the record_usage INCRBY idiom), so N concurrent checks
            # observe 1..N and exactly CB_HALF_OPEN_MAX_CALLS are admitted.
            probe_key = _half_open_probe_key(provider, state)
            n = _redis_incr(probe_key)
            if n <= 0:
                # Redis unavailable mid-branch — same fail-open contract as the
                # except path below.
                return True
            if n == 1:
                _redis_expire(probe_key, _CB_TTL)
                # Mirror the count into the blob for observability ONLY — it is
                # NEVER the admission input, so the blob write can no longer
                # over-admit.
                #
                # ONLY the ADMITTED probe (n == 1) writes the mirror. A DENIED
                # check must not, or it re-stamps the blob `half_open` and can
                # WEDGE the breaker in deny-all: flag-ON the gate check runs in
                # a thread while record_success runs on the loop, so a denied
                # check whose read->write span brackets record_success's CLOSED
                # write resurrects `half_open`; every later check then INCRs to
                # n >= 2, returns False AND refreshes the TTL, and since denied
                # checks never call record_success/record_failure the provider
                # stays denied indefinitely (the poisoned blob survives a
                # flag-OFF flip — it is in Redis). The admitted probe's mirror
                # strictly PRECEDES its own render call, so it can never land
                # after that render's record_success.
                state["half_open_calls"] = n
                _redis_set(_circuit_key(provider), json.dumps(state), ex=_CB_TTL)
            return n <= CB_HALF_OPEN_MAX_CALLS
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


# ============================================================================
# W1-3 — OPENAI PREFLIGHT BREAKER (ENABLE_LLM_PREFLIGHT_BREAKER, default OFF)
# ============================================================================
# Findings LS-FAILURE-MODES-COST-02/-03. Serper is dead by configuration on the
# `web` service (SERPER_LIFETIME_LIMIT=0), so every search leg routes to Bright
# Data, which is armed with no budget gate. Meanwhile OpenAI answers 429. The
# app's only compare shape (explicit_pair) never checked LLM health before
# dispatching, so every compare paid the full scrape/render cascade and THEN
# failed at the LLM. Money out, nothing back.
#
# This mirrors serper_service.py:284-320 (ENABLE_SERPER_BREAKER) — the template
# that already solved the two hard parts — and reuses THIS module's existing
# breaker (is_circuit_closed / record_failure / record_success). No new breaker
# abstraction is introduced.
#
#   * MEMOISE the breaker state (LLM_BREAKER_CACHE_TTL, default 60s) so the
#     check adds no per-call blocking Redis round trip to an async hot path —
#     the event-loop hazard W0 spent four units removing.
#   * FAIL-OPEN on any error. If the breaker state cannot be read, DISPATCH. A
#     Redis blip must never become "the app refuses every compare".
#   * Flag OFF -> nothing here runs: no breaker read, no record, every call
#     dispatches (byte-identical to the pre-unit code path).
#
# TWO DIFFERENT QUESTIONS, TWO DIFFERENT FUNCTIONS (adversarial review, BLOCKING
# 2 — this is the defect that would have fired the first time anyone flipped the
# flag). `is_circuit_closed` is NOT read-only: its CB_HALF_OPEN branch does a
# `_redis_incr(probe_key)` and CB_HALF_OPEN_MAX_CALLS is 1. Using it for the
# compare-entry preflight SPENDS that single probe on a compare that may never
# dispatch an LLM call at all (blocked by the L1 content-safety prefilter, or
# short-circuited earlier), after which nothing records an outcome, the breaker
# stays half-open with its budget spent, and every later compare is denied
# forever. So:
#
#   * PREFLIGHT — "should I even start?" — openai_preflight_allows_compare().
#     Strictly read-only (one GET, memoised, never an INCR, never a SET). It
#     denies ONLY a breaker that is OPEN and still inside its cooldown. A
#     half-open (or cooldown-expired) breaker PROCEEDS, precisely so the probe
#     is spent at a real dispatch that records an outcome.
#   * ADMISSION — "may I make this probe call?" — the dispatch chokepoint
#     guarded_llm_create(), which keeps is_circuit_closed and where a success or
#     failure is actually recorded.
#
# WHY THE PREFLIGHT IS RECOVERY-AWARE (a correction to the ruling's letter, kept
# faithful to its intent). get_breaker_state() returns the PERSISTED state
# string; it does not apply the CB_RECOVERY_TIMEOUT transition, because only
# is_circuit_closed writes that transition. A preflight that denied on a bare
# `state == CB_OPEN` would therefore deny forever: it blocks the compare, so
# nothing on the compare path ever calls is_circuit_closed, so the blob is never
# transitioned to half-open, so the preflight keeps reading "open" — the same
# permanent lockout in a new place (verified: get_breaker_state returns "open"
# indefinitely for a blob tripped long past CB_RECOVERY_TIMEOUT). Treating a
# cooldown-expired OPEN as "proceed" is what hands the probe to the dispatch
# chokepoint, which transitions and counts it correctly.
#
# THE SUCCESS PATH COSTS NOTHING ON THE HOT PATH (adversarial review, MAJOR 3).
# Measured before the fix: an identical compare went 12 -> 24 blocking Redis
# GETs with the flag ON, eleven of them from an un-memoised record_success on
# every successful dispatch. A closed breaker learning it is still closed is not
# information. The memo therefore caches the STATE (not just a boolean), and a
# dispatch whose snapshot says CLOSED with a zero failure count neither calls
# is_circuit_closed nor records a success: zero Redis round trips per call, one
# GET per memo window. An outcome is recorded only when it can change something
# — a standing failure streak, a half-open probe, or any failure.
_LLM_PREFLIGHT_FLAG = "ENABLE_LLM_PREFLIGHT_BREAKER"
_LLM_BREAKER_CACHE_TTL_ENV = "LLM_BREAKER_CACHE_TTL"
_DEFAULT_LLM_BREAKER_CACHE_TTL = 60.0

OPENAI_PROVIDER = "openai"

# (expires_at_monotonic, state, tripped_at, failure_count)
_openai_breaker_cache: Optional[tuple] = None


class LLMUnavailableError(RuntimeError):
    """Raised INSTEAD of dispatching when the `openai` breaker denies admission.

    The message deliberately avoids the substrings
    `extraction_service.generate_comparison` matches on to decide whether to run
    its rate-limited verdict fallback ("429" / "rate" / "quota"), so a suppressed
    primary call cannot trigger a second dispatch attempt.
    """


def llm_preflight_breaker_enabled() -> bool:
    """Read PER CALL (the price_service.exact_gate_enabled idiom) so a Railway
    flip takes effect without a restart. Default OFF."""
    return os.getenv(_LLM_PREFLIGHT_FLAG, "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _llm_breaker_cache_ttl() -> float:
    """Seconds a breaker snapshot is reused. <=0 disables memoisation entirely
    (every call re-reads Redis) — the escape hatch if a decision must be
    instant."""
    raw = (os.environ.get(_LLM_BREAKER_CACHE_TTL_ENV) or "").strip()
    if not raw:
        return _DEFAULT_LLM_BREAKER_CACHE_TTL
    try:
        return float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_LLM_BREAKER_CACHE_TTL


def _reset_openai_breaker_cache() -> None:
    """Drop the memoised breaker snapshot so the next call re-reads. Used by
    openai_record_failure and by tests."""
    global _openai_breaker_cache
    _openai_breaker_cache = None


def _store_openai_breaker_snapshot(state: str, tripped_at: float, failures: int) -> None:
    """Seed the memo from a state we just wrote ourselves, so a recorded outcome
    does not force the next call to re-read Redis."""
    global _openai_breaker_cache
    ttl = _llm_breaker_cache_ttl()
    _openai_breaker_cache = (
        (time.monotonic() + ttl, state, tripped_at, failures) if ttl > 0 else None
    )


def _openai_breaker_snapshot() -> tuple:
    """(state, tripped_at, failure_count) for the `openai` breaker.

    READ-ONLY — exactly one Redis GET per memo window and never a write, so it
    can never spend the half-open probe. FAIL-OPEN: an absent, malformed or
    unreadable blob reads as a clean CLOSED breaker, which dispatches."""
    global _openai_breaker_cache
    now = time.monotonic()
    cached = _openai_breaker_cache
    if cached is not None and now < cached[0]:
        return cached[1], cached[2], cached[3]
    state, tripped_at, failures = CB_CLOSED, 0.0, 0
    try:
        raw = _redis_get(_circuit_key(OPENAI_PROVIDER))
        if raw:
            blob = json.loads(raw)
            state = blob.get("state") or CB_CLOSED
            tripped_at = float(blob.get("tripped_at") or 0)
            failures = int(blob.get("failure_count") or 0)
    except Exception as e:  # noqa: BLE001 — a monitoring failure must not block calls
        logger.warning("[CIRCUIT] openai breaker read failed (%s) — failing open", e)
        state, tripped_at, failures = CB_CLOSED, 0.0, 0
    _store_openai_breaker_snapshot(state, tripped_at, failures)
    return state, tripped_at, failures


def openai_preflight_allows_compare() -> bool:
    """READ-ONLY compare-entry preflight: "should I even start?".

    False ONLY for a breaker that is OPEN and still inside CB_RECOVERY_TIMEOUT.
    Everything else proceeds — closed, half-open, a cooldown-expired OPEN, and
    any state that could not be read (fail-open). Never increments the half-open
    probe counter; that budget belongs to guarded_llm_create, which records an
    outcome for it."""
    state, tripped_at, _failures = _openai_breaker_snapshot()
    if state != CB_OPEN:
        return True
    if time.time() - tripped_at >= CB_RECOVERY_TIMEOUT:
        # Cooldown expired: this compare is the recovery probe's carrier. Let it
        # through so is_circuit_closed can transition + count the probe at a
        # dispatch that will actually record success or failure.
        return True
    return False


def _openai_dispatch_admission() -> tuple:
    """(admitted, outcome_matters) for ONE OpenAI dispatch.

    `outcome_matters` is False on the overwhelmingly common path — a breaker
    that is closed with no standing failure streak — because record_success
    would then write a state Redis already holds (MAJOR 3: eleven such writes
    per compare). Whenever the breaker is anything else, is_circuit_closed does
    the real admission (including the atomic half-open probe INCR) and the
    outcome is recorded."""
    state, tripped_at, failures = _openai_breaker_snapshot()
    if state == CB_CLOSED:
        # A closed breaker admits; is_circuit_closed would spend a Redis GET to
        # say the same thing. A success still matters while a partial failure
        # streak stands, because recording it resets the streak.
        return True, failures > 0
    if state == CB_OPEN and (time.time() - tripped_at) < CB_RECOVERY_TIMEOUT:
        # Denied without touching Redis; the probe budget is untouched.
        return False, False
    try:
        admitted = is_circuit_closed(OPENAI_PROVIDER)
    except Exception as e:  # noqa: BLE001 — a monitoring failure must not block calls
        logger.warning("[CIRCUIT] openai breaker check failed (%s) — failing open", e)
        admitted = True
    return admitted, True


def openai_record_failure() -> None:
    """Record an OpenAI transport failure (429 / 5xx / timeout / cancellation)
    and drop the breaker memo so a resulting trip engages immediately. No-op
    unless the preflight flag is ON."""
    if not llm_preflight_breaker_enabled():
        return
    try:
        record_failure(OPENAI_PROVIDER)
    except Exception as e:  # noqa: BLE001
        logger.warning("[CIRCUIT] openai record_failure failed: %s", e)
    finally:
        _reset_openai_breaker_cache()


def openai_record_success() -> None:
    """Record an OpenAI 200 so a half-open probe closes the breaker, or a
    standing failure streak resets. No-op unless the preflight flag is ON.

    Callers gate this on `outcome_matters` from _openai_dispatch_admission — a
    closed, clean breaker learning it is still closed is not information, and
    paying two Redis round trips per successful dispatch to write it is the
    hot-path tax MAJOR 3 measured."""
    if not llm_preflight_breaker_enabled():
        return
    try:
        record_success(OPENAI_PROVIDER)
    except Exception as e:  # noqa: BLE001
        logger.warning("[CIRCUIT] openai record_success failed: %s", e)
        _reset_openai_breaker_cache()
        return
    # We just wrote CLOSED / failure_count 0; model it locally instead of paying
    # a GET on the next call to rediscover it.
    _store_openai_breaker_snapshot(CB_CLOSED, 0.0, 0)


def _openai_failure_is_transient(exc: BaseException) -> bool:
    """True only for the failure classes record_failure's own docstring names:
    429, 5xx, timeout, connection error. A 400/401/403/404/422 is a REQUEST
    defect (a bad prompt, a wrong model id, a dead key) and must never trip a
    breaker that gates every compare. `openai` is imported lazily so this module
    keeps importing without the SDK present."""
    if isinstance(exc, TimeoutError):  # asyncio.TimeoutError is TimeoutError on 3.11+
        return True
    try:
        import openai as _openai_sdk
    except Exception:  # noqa: BLE001 — no SDK -> nothing to classify
        return False
    if isinstance(
        exc,
        (
            _openai_sdk.RateLimitError,
            _openai_sdk.APIConnectionError,  # APITimeoutError subclasses this
            _openai_sdk.InternalServerError,
        ),
    ):
        return True
    if isinstance(exc, _openai_sdk.APIStatusError):
        status = getattr(exc, "status_code", None)
        return isinstance(status, int) and status >= 500
    return False


# WHICH OpenAI CALLERS FEED THIS BREAKER — the full census, so nobody later
# assumes it sees traffic it does not (ruling #2; adversarial review MINOR 6).
# WIRED (14 dispatches, all reachable from a compare):
#   extraction_service      classify_category_llm, parse_product_query,
#                           extract_specs, extract_price_*(2), extract_reviews,
#                           generate_comparison (primary + rate-limit fallback)
#   openai_service          identify_products (vision), extract_specs_targeted,
#                           generate_comparison, disambiguate_variant_line
#   url_extraction_service  extract_with_ai
#   verdict_critique_service critique_verdict   (wired by this rework)
# NOT WIRED, deliberately:
#   content_safety_service:152 — `moderations.create`, a DIFFERENT API surface
#     with its own fail-open contract. A moderation blip is not an "LLM is down"
#     signal and must not gate every compare.
#   image_service:173 — the Tier-3 product-image GPT fallback. It IS reachable
#     from a compare (structured_comparison_service awaits get_product_image_url
#     in the product fetch), so this is a scope decision, not a reachability
#     one: it is optional enrichment whose own failure is already swallowed into
#     "no image", and letting it trip the breaker that gates every compare would
#     let a cosmetic tier take the whole product down. Revisit deliberately.
async def guarded_llm_create(client, **kwargs):
    """The ONE OpenAI chat-completion dispatch chokepoint the preflight breaker
    reads and records at.

    Flag OFF: a bare ``await client.chat.completions.create(**kwargs)`` — no
    breaker read, no record, every call dispatches.

    Flag ON: a denied admission raises LLMUnavailableError WITHOUT dispatching;
    otherwise the call runs and its outcome is recorded WHEN THE OUTCOME CAN
    CHANGE SOMETHING. This call-site guard is the backstop, NOT the saving — the
    saving is the preflight at the two compare entries
    (structured_comparison_service.compare_from_text and
    compare_from_text_streaming), because a check here alone saves the LLM call
    and still pays for all the scraping, which is the entire cost being attacked.
    """
    if not llm_preflight_breaker_enabled():
        return await client.chat.completions.create(**kwargs)
    admitted, outcome_matters = _openai_dispatch_admission()
    if not admitted:
        raise LLMUnavailableError(
            "openai circuit breaker denied admission — dispatch suppressed"
        )
    try:
        response = await client.chat.completions.create(**kwargs)
    except asyncio.CancelledError:
        # MINOR 5 — CancelledError is a BaseException, so an `except Exception`
        # never saw it and an asyncio.wait_for timeout around this call was
        # never recorded (measured: {'fail': 0, 'succ': 0}). Almost every
        # wait_for in the compare path wraps THIS coroutine, so the timeout the
        # breaker most needs to see arrived here as a cancellation.
        #
        # ACCEPTED RESIDUAL, disclosed rather than hidden: a cancellation from
        # an outer cause (process shutdown, or ENABLE_PREVERDICT_DISCONNECT_ABORT
        # closing the stream) is indistinguishable from a deadline here — the
        # task is cancelled identically in both cases — so it also records a
        # failure. It takes CB_FAILURE_THRESHOLD *consecutive* such records to
        # trip, and any successful dispatch in between resets the streak (that
        # is exactly the case `outcome_matters` keeps recording for).
        # The cancellation is re-raised untouched, never swallowed.
        openai_record_failure()
        raise
    except Exception as e:  # noqa: BLE001 — classify, record, re-raise unchanged
        if _openai_failure_is_transient(e):
            openai_record_failure()
        raise
    if outcome_matters:
        openai_record_success()
    return response


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
    return max(0, _provider_limit(provider) - used)


def get_burn_status(provider: str) -> Dict[str, Any]:
    """I5.0 diagnostic — current burn state vs the 80% ceiling for `provider`.

    Read-only; fail-safe (no usage observed, never raises) on Redis error or
    unknown provider. Returns
    `{used, limit, threshold, fraction, over_threshold}` for the dashboard and
    the alert drill.
    """
    config = PROVIDER_CONFIGS.get(provider)
    limit = _provider_limit(provider) if config else 0
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
            "limit": _provider_limit(provider),
            "remaining": max(0, _provider_limit(provider) - used),
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
