"""S81-24 AUTH-THROTTLE-V2 phase 1: per-email and per-account auth throttles.

Dark behind ENABLE_AUTH_THROTTLE_V2 (default OFF). The routes in
app/api/auth_routes.py read the flag per call as the FIRST statement of each
guard; gate() and the two record functions never re-read it, so a route with
the flag OFF touches nothing in this module.

Every decision is ONE Lua EVAL (the six frozen scripts below) run on a
dedicated 4-thread pool under asyncio.wait_for. Keys are
auth_throttle:<endpoint>:<kind>:<HMAC-SHA256(pepper, ident)[:32]>; no key,
digest, email, user id or pepper is ever logged. Every failure (no client,
an EVAL error, a timeout, a malformed reply, an unset pepper) fails OPEN:
the request proceeds and the per-IP slowapi floor stays in force.

Login (R-S24-19, count-only): the gate refuses only while a wait armed by a
PREVIOUS counted failure is live; the n-th consecutive wrong-password result
arms min(2^(n-1) s, cap); a success deletes the hash. The two record writes
are shielded (a timeout or a disconnect never drops a clear); the gate read
stays cancellable.
"""
import asyncio
import concurrent.futures
import hashlib
import hmac
import logging
import math
import os
import threading
import time
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException

from app.services import cache_service as _cache_service

logger = logging.getLogger(__name__)

FLAG = "ENABLE_AUTH_THROTTLE_V2"
PEPPER_ENV = "AUTH_THROTTLE_PEPPER"

ENDPOINTS = (
    "login",
    "register",
    "password_reset",
    "resend_verification",
    "change_password",
    "update_email",
)
_PER_USER_ENDPOINTS = frozenset(("change_password", "update_email"))
_DAY_CAPPED_ENDPOINTS = frozenset(("password_reset", "resend_verification"))

_TRUE_VALUES = ("true", "1", "yes", "on")

# name -> (default, lowest valid, highest valid); out of range -> the default.
KNOBS = {
    "AUTH_THROTTLE_LOGIN_CAP_SECONDS": (60, 8, 3600),
    "AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS": (60, 10, 3600),
    "AUTH_THROTTLE_RESET_INTERVAL_SECONDS": (60, 10, 3600),
    "AUTH_THROTTLE_RESET_PER_DAY": (5, 1, 100),
    "AUTH_THROTTLE_ACCOUNT_PER_WINDOW": (5, 1, 100),
    "AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS": (600, 60, 86400),
    "AUTH_THROTTLE_TTL_SECONDS": (21600, 60, 86400),
    "AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS": (0.5, 0.05, 5.0),
}

DAY_KEY_TTL_SECONDS = 86400
RIYADH_UTC_OFFSET_HOURS = 3
POOL_WORKERS = 4
POOL_THREAD_PREFIX = "auth-throttle"
DIGEST_HEX_CHARS = 32
SKIP_LOG_MEMO_SECONDS = 60

# Equal to the slowapi handler's message (app/middleware/error_handler.py), so
# a V2 refusal and a slowapi refusal are the same envelope on the wire.
THROTTLED_MESSAGE = "Rate limit exceeded. Please try again later."

# The one login result that counts toward the backoff: GoTrue's wrong-password
# and unknown-user class as the service layer maps it.
_COUNTED_LOGIN_ERROR = "Invalid email or password"


def _lua(*lines: str) -> str:
    """LF join, no trailing LF (the frozen form the RED pins by sha256)."""
    return "\n".join(lines)


# KEYS[1] the backoff hash; ARGV [now_ms]. Read-only, count-only.
LOGIN_GATE_SCRIPT = _lua(
    "local u = tonumber(redis.call('HGET', KEYS[1], 'u') or '0')",
    "local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')",
    "local now = tonumber(ARGV[1])",
    "if now < u then return {0, math.ceil((u - now) / 1000), c} end",
    "return {1, 0, c}",
)

# KEYS[1] the backoff hash; ARGV [now_ms, cap_ms, ttl_s]. The c-th consecutive
# counted failure arms min(2^(c-1) s, cap).
LOGIN_FAIL_SCRIPT = _lua(
    "local c = redis.call('HINCRBY', KEYS[1], 'c', 1)",
    "local w = 1000",
    "for i = 2, math.min(c, 23) do w = w * 2 end",
    "if w > tonumber(ARGV[2]) then w = tonumber(ARGV[2]) end",
    "redis.call('HSET', KEYS[1], 'u', tonumber(ARGV[1]) + w)",
    "redis.call('EXPIRE', KEYS[1], ARGV[3])",
    "return c",
)

# KEYS[1] the backoff hash; no ARGV.
LOGIN_CLEAR_SCRIPT = _lua(
    "return redis.call('DEL', KEYS[1])",
)

# KEYS[1] the interval key; ARGV [now_ms, interval_ms, interval_s].
INTERVAL_SCRIPT = _lua(
    "local now = tonumber(ARGV[1])",
    "local u = tonumber(redis.call('GET', KEYS[1]) or '0')",
    "if now < u then return {0, math.ceil((u - now) / 1000), 1} end",
    "redis.call('SET', KEYS[1], now + tonumber(ARGV[2]), 'EX', ARGV[3])",
    "return {1, 0, 1}",
)

# KEYS [the interval key, the Riyadh-day key]; ARGV [now_ms, interval_ms,
# per_day, interval_s, day_ttl_s, seconds_to_riyadh_midnight].
RESET_SCRIPT = _lua(
    "local now = tonumber(ARGV[1])",
    "local u = tonumber(redis.call('GET', KEYS[1]) or '0')",
    "local d = tonumber(redis.call('GET', KEYS[2]) or '0')",
    "if now < u then return {0, math.ceil((u - now) / 1000), d} end",
    "if d >= tonumber(ARGV[3]) then return {0, tonumber(ARGV[6]), d} end",
    "redis.call('SET', KEYS[1], now + tonumber(ARGV[2]), 'EX', ARGV[4])",
    "d = redis.call('INCR', KEYS[2])",
    "if d == 1 then redis.call('EXPIRE', KEYS[2], ARGV[5]) end",
    "return {1, 0, d}",
)

# KEYS[1] the per-account window hash; ARGV [now_ms, per_window, window_ms,
# window_s].
ACCOUNT_SCRIPT = _lua(
    "local now = tonumber(ARGV[1])",
    "local w = tonumber(ARGV[3])",
    "local s = tonumber(redis.call('HGET', KEYS[1], 's') or '0')",
    "local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')",
    "if now - s >= w then",
    "  s = now",
    "  c = 0",
    "end",
    "if c >= tonumber(ARGV[2]) then return {0, math.ceil((s + w - now) / 1000), c} end",
    "c = c + 1",
    "redis.call('HSET', KEYS[1], 's', s, 'c', c)",
    "redis.call('EXPIRE', KEYS[1], ARGV[4])",
    "return {1, 0, c}",
)


class RedisUnconfigured(Exception):
    """The process Redis client (cache_service.redis_client) is None."""


# ---------------------------------------------------------------------------
# the flag and the knobs (read per call)
# ---------------------------------------------------------------------------
def auth_throttle_v2_enabled() -> bool:
    """The house idiom, read per call (never cached)."""
    return os.getenv(FLAG, "false").strip().lower() in _TRUE_VALUES


def knob(name: str) -> Any:
    """A knob parsed defensively: unset, blank, garbage, inf, nan or out of
    range -> the default (never a clamp to the bound)."""
    default, lo, hi = KNOBS[name]
    raw = os.getenv(name)
    if raw is None:
        return default
    text = raw.strip()
    try:
        if isinstance(default, float):
            value: Any = float(text)
            if not math.isfinite(value):
                return default
        else:
            value = int(text, 10)
    except (TypeError, ValueError):
        return default
    if value < lo or value > hi:
        return default
    return value


def redis_timeout_seconds() -> float:
    return knob("AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS")


# ---------------------------------------------------------------------------
# the pepper, the identifiers and the keys
# ---------------------------------------------------------------------------
_PEPPER_LOCK = threading.Lock()
_PEPPER_WARNED = False


def _warn_pepper_once() -> None:
    global _PEPPER_WARNED
    with _PEPPER_LOCK:
        if _PEPPER_WARNED:
            return
        _PEPPER_WARNED = True
    logger.warning("[AUTH_THROTTLE] pepper unset")


def _reset_pepper_warning() -> None:
    """Test seam: clear the once-per-process WARNING latch."""
    global _PEPPER_WARNED
    with _PEPPER_LOCK:
        _PEPPER_WARNED = False


def digest(ident: object) -> Optional[str]:
    """HMAC-SHA256(pepper, ident) as 32 lower-case hex, or None. An unset,
    blank or non-encodable pepper is ONE WARNING per process (V2 inactive)."""
    if not isinstance(ident, str):
        return None
    pepper = os.getenv(PEPPER_ENV)
    if pepper is None or not pepper.strip():
        _warn_pepper_once()
        return None
    try:
        pepper_bytes = pepper.strip().encode("utf-8")
        message = ident.encode("utf-8")
    except UnicodeError:
        _warn_pepper_once()
        return None
    return hmac.new(pepper_bytes, message, hashlib.sha256).hexdigest()[:DIGEST_HEX_CHARS]


def email_ident(raw: object) -> Optional[str]:
    """The trimmed lower-cased email, or None for a non-str or blank value."""
    if not isinstance(raw, str):
        return None
    value = raw.strip().lower()
    return value if value else None


def account_ident(raw: object) -> Optional[str]:
    """The trimmed user id, or None for a non-str or blank value."""
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value if value else None


def throttle_key(endpoint: str, kind: str, dig: str) -> str:
    return "auth_throttle:%s:%s:%s" % (endpoint, kind, dig)


def riyadh_day_compact(now_epoch_s: int) -> str:
    """The Asia/Riyadh calendar day (fixed +03:00, no DST) as YYYYMMDD."""
    local = time.gmtime(int(now_epoch_s) + RIYADH_UTC_OFFSET_HOURS * 3600)
    return "%04d%02d%02d" % (local.tm_year, local.tm_mon, local.tm_mday)


def seconds_to_riyadh_midnight(now_epoch_s: int) -> int:
    """Whole seconds to the next 00:00 Asia/Riyadh, at least 1."""
    local_s = int(now_epoch_s) + RIYADH_UTC_OFFSET_HOURS * 3600
    return max(1, 86400 - local_s % 86400)


def _now_ms() -> int:
    """Test seam: the web process wall clock in milliseconds."""
    return int(time.time() * 1000)


def _monotonic() -> float:
    """Test seam: the clock of the skipped-line memo."""
    return time.monotonic()


# ---------------------------------------------------------------------------
# the skipped-line memo (R-S24-21: one line per endpoint per 60 s)
# ---------------------------------------------------------------------------
_SKIP_LOCK = threading.Lock()
_SKIP_LAST: dict = {}


def _reset_skip_memo() -> None:
    """Test seam: forget every endpoint's last skipped line."""
    with _SKIP_LOCK:
        _SKIP_LAST.clear()


def _log_skipped(endpoint: str, exc: BaseException) -> None:
    now = _monotonic()
    with _SKIP_LOCK:
        last = _SKIP_LAST.get(endpoint)
        if last is not None and now - last < SKIP_LOG_MEMO_SECONDS:
            return
        _SKIP_LAST[endpoint] = now
    logger.warning(
        "[AUTH_THROTTLE] skipped endpoint=%s type=%s", endpoint, type(exc).__name__
    )


# ---------------------------------------------------------------------------
# the dedicated pool and the bounded EVAL
# ---------------------------------------------------------------------------
_POOL_LOCK = threading.Lock()
_POOL: Optional[concurrent.futures.ThreadPoolExecutor] = None


def _pool() -> concurrent.futures.ThreadPoolExecutor:
    """The dedicated 'auth-throttle' pool, built lazily once (never the loop's
    default executor, never another service's pool)."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = concurrent.futures.ThreadPoolExecutor(
                max_workers=POOL_WORKERS, thread_name_prefix=POOL_THREAD_PREFIX
            )
        return _POOL


def _eval(client: Any, script: str, keys: List[str], args: List[str]) -> Any:
    """The two client shapes: upstash-redis 1.7.0 eval(script, keys=, args=);
    redis-py 8.1.0 eval(script, numkeys, *keys_and_args)."""
    if type(client).__module__.split(".")[0] == "upstash_redis":
        return client.eval(script, keys=list(keys), args=list(args))
    return client.eval(script, len(keys), *keys, *args)


async def _run(script: str, keys: List[str], args: List[str], durable: bool = False) -> Any:
    """One EVAL on the pool under the timeout knob; the loop thread never runs
    the command. durable: shielded, so a timeout or a cancellation of the
    caller never cancels the write (it lands when a pool thread takes it)."""
    client = _cache_service.redis_client
    if client is None:
        raise RedisUnconfigured()
    job = asyncio.wrap_future(_pool().submit(_eval, client, script, keys, args))
    return await asyncio.wait_for(
        asyncio.shield(job) if durable else job, redis_timeout_seconds()
    )


def _parse_reply(raw: Any) -> Tuple[bool, int, int]:
    """[allowed, retry_after_seconds, count]: exactly three non-bool ints with
    allowed in {0, 1}; anything else is a ValueError (fail open)."""
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise ValueError("auth throttle reply shape")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in raw):
        raise ValueError("auth throttle reply type")
    allowed, retry, count = raw
    if allowed not in (0, 1):
        raise ValueError("auth throttle reply flag")
    return allowed == 1, int(retry), int(count)


def _decision(endpoint: str, dig: str, now_ms: int) -> Tuple[str, List[str], List[str]]:
    """The script, KEYS and ARGV of one gate decision (R-S24-20 TTLs)."""
    if endpoint == "login":
        return LOGIN_GATE_SCRIPT, [throttle_key(endpoint, "backoff", dig)], [str(now_ms)]
    if endpoint in _DAY_CAPPED_ENDPOINTS:
        interval = knob("AUTH_THROTTLE_RESET_INTERVAL_SECONDS")
        now_s = now_ms // 1000
        keys = [
            throttle_key(endpoint, "interval", dig),
            throttle_key(endpoint, "day" + riyadh_day_compact(now_s), dig),
        ]
        args = [
            str(now_ms),
            str(interval * 1000),
            str(knob("AUTH_THROTTLE_RESET_PER_DAY")),
            str(interval),
            str(DAY_KEY_TTL_SECONDS),
            str(seconds_to_riyadh_midnight(now_s)),
        ]
        return RESET_SCRIPT, keys, args
    if endpoint in _PER_USER_ENDPOINTS:
        window = knob("AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS")
        args = [
            str(now_ms),
            str(knob("AUTH_THROTTLE_ACCOUNT_PER_WINDOW")),
            str(window * 1000),
            str(window),
        ]
        return ACCOUNT_SCRIPT, [throttle_key(endpoint, "account", dig)], args
    interval = knob("AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS")
    args = [str(now_ms), str(interval * 1000), str(interval)]
    return INTERVAL_SCRIPT, [throttle_key(endpoint, "interval", dig)], args


def _login_backoff_key(email: object) -> Optional[str]:
    norm = email_ident(email)
    if norm is None:
        return None
    dig = digest(norm)
    if dig is None:
        return None
    return throttle_key("login", "backoff", dig)


# ---------------------------------------------------------------------------
# the public coroutines
# ---------------------------------------------------------------------------
async def gate(endpoint: str, ident: object) -> None:
    """Allow (return None) or refuse (raise the slowapi-equal 429). Never
    raises anything else: an unknown endpoint, a bad ident, an unset pepper and
    every Redis-side failure allow."""
    if endpoint not in ENDPOINTS:
        return None
    if endpoint in _PER_USER_ENDPOINTS:
        norm = account_ident(ident)
    else:
        norm = email_ident(ident)
    if norm is None:
        return None
    dig = digest(norm)
    if dig is None:
        return None
    try:
        script, keys, args = _decision(endpoint, dig, _now_ms())
        allowed, retry, count = _parse_reply(await _run(script, keys, args))
    except Exception as exc:  # noqa: BLE001 -- fail open, the type name only
        _log_skipped(endpoint, exc)
        return None
    if allowed:
        return None
    retry = max(1, retry)
    logger.info(
        "[AUTH_THROTTLE] throttled endpoint=%s count=%d retry_after=%d",
        endpoint, count, retry,
    )
    raise HTTPException(
        status_code=429,
        detail={"error": THROTTLED_MESSAGE, "code": "RATE_LIMITED", "retry_after": retry},
    )


async def record_login_failure(email: object, result: object) -> None:
    """Count a wrong-password / unknown-user login (only that result class);
    a shielded write; never raises."""
    if not isinstance(result, dict) or result.get("error") != _COUNTED_LOGIN_ERROR:
        return None
    key = _login_backoff_key(email)
    if key is None:
        return None
    try:
        cap = knob("AUTH_THROTTLE_LOGIN_CAP_SECONDS")
        ttl = max(knob("AUTH_THROTTLE_TTL_SECONDS"), cap)
        await _run(
            LOGIN_FAIL_SCRIPT, [key], [str(_now_ms()), str(cap * 1000), str(ttl)],
            durable=True,
        )
    except Exception as exc:  # noqa: BLE001 -- fail open, the type name only
        _log_skipped("login_fail", exc)
    return None


async def record_login_success(email: object) -> None:
    """Clear the login backoff after a success; a shielded write; never raises."""
    key = _login_backoff_key(email)
    if key is None:
        return None
    try:
        await _run(LOGIN_CLEAR_SCRIPT, [key], [], durable=True)
    except Exception as exc:  # noqa: BLE001 -- fail open, the type name only
        _log_skipped("login_clear", exc)
    return None
