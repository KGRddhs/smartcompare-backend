"""Freemium usage tracking and tier enforcement.

Monthly cap = base tier limit + ``users.referral_bonus_comparisons_this_month``.
Lazy reset of the bonus happens inside ``_get_user_tier_info`` whenever
``referral_bonus_reset_at`` falls in the past — no cron job required.
"""
import asyncio
import logging
import math
import os
import re
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.cache_service import redis_client, _redis_offload_enabled
from app.services.database_service import get_admin_supabase_client
from app.utils import request_context as _request_context  # S81-09: the S81-05 stdlib leaf
from app.utils.db_offload import run_db  # M13-05 ENABLE_SYNC_DB_OFFLOAD
from app.utils.redis_offloop import run_redis_offloop_pool, usage_path_offloop_enabled  # S81 ST1

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

    M18 CD-interactions-05: this now CONSUMES the credit atomically at the gate
    (the M13-37 ``_atomic_consume`` pattern, keyed ``anon:{fingerprint}``)
    instead of read-then-record — N parallel same-fingerprint requests can no
    longer all read the same pre-increment value and all pass. On ``allowed``
    the credit is already debited; ``record_anon_comparison`` is a no-op and a
    failed comparison should refund via ``refund_anon_comparison_credit``.

    Anonymous devices have no `users` row (the lifetime counter lives in
    Supabase keyed by user_id), so this uses the free-tier daily + monthly
    Redis counters. Fails OPEN when Redis is unavailable — a cache outage must
    never block a legitimate user. Same shape as ``check_usage_allowed`` plus
    ``consumed`` / ``consumed_keys``.
    """
    limits = TIER_LIMITS["free"]
    anon_id = f"anon:{device_fingerprint}"
    outcome = await _atomic_consume_async(anon_id, limits["daily"], limits["monthly"])
    reason = (str(outcome) or None) if outcome is not None else None
    daily_after = getattr(outcome, "daily_after", None)
    monthly_after = getattr(outcome, "monthly_after", None)

    if reason == "daily_limit":
        monthly_used = (
            monthly_after
            if monthly_after is not None
            else await _get_redis_count_async(_monthly_key(anon_id))
        )
        return {
            "allowed": False,
            "reason": "daily_limit",
            "tier": "free",
            "consumed": False,
            "remaining": {"daily": 0, "monthly": max(0, limits["monthly"] - monthly_used), "lifetime_free": 0},
        }
    if reason == "monthly_limit":
        daily_used = (
            daily_after
            if daily_after is not None
            else await _get_redis_count_async(_daily_key(anon_id))
        )
        return {
            "allowed": False,
            "reason": "monthly_limit",
            "tier": "free",
            "consumed": False,
            "remaining": {"daily": max(0, limits["daily"] - daily_used), "monthly": 0, "lifetime_free": 0},
        }

    # Success (or fail-open): the INCRBY return values ARE the post-consume
    # counts (LS-event-loop-03) — no redundant re-reads. Fail-open (counts
    # None) degrades to the same 0-count reads as before.
    daily_used = (
        daily_after if daily_after is not None else await _get_redis_count_async(_daily_key(anon_id))
    )
    monthly_used = (
        monthly_after if monthly_after is not None else await _get_redis_count_async(_monthly_key(anon_id))
    )
    return {
        "allowed": True,
        "reason": None,
        "tier": "free",
        "consumed": True,
        "consumed_keys": {
            "daily": getattr(outcome, "daily_key", None) or _daily_key(anon_id),
            "monthly": getattr(outcome, "monthly_key", None) or _monthly_key(anon_id),
        },
        "remaining": {
            "daily": max(0, limits["daily"] - daily_used),
            "monthly": max(0, limits["monthly"] - monthly_used),
            "lifetime_free": 0,
        },
    }


async def record_anon_comparison(device_fingerprint: str) -> None:
    """DEPRECATED no-op (M18 CD-interactions-05). The anonymous gate now
    debits the credit atomically inside ``check_anon_usage_allowed`` —
    incrementing here again would double-count every successful anonymous
    comparison. Kept (async, same signature) because the routes still
    fire-and-forget it on success."""
    return None


async def refund_anon_comparison_credit(
    device_fingerprint: str, consumed_keys: Optional[dict] = None
) -> None:
    """Refund the credit ``check_anon_usage_allowed`` reserved, for when the
    comparison work then failed. Symmetric twin of ``refund_comparison_credit``
    keyed on ``anon:{fingerprint}``. Fire-and-forget safe."""
    await refund_comparison_credit(f"anon:{device_fingerprint}", consumed_keys)

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


# ---------------------------------------------------------------------------
# S81-09 DEVICE-QUOTA-RIYADH: ENABLE_DEVICE_DAILY_QUOTA + ENABLE_RIYADH_RESET
# (both default OFF, read PER CALL with the house idiom; the unit spec
# .qa-s80/S81-09_UNIT_SPEC.md as amended by RULINGS_S81_09 and GATE_S81_09 in
# the session-81 state folder). Both flags OFF = today's UTC per-account keys,
# results, bodies and log lines byte for byte (pinned by the committed golden
# tests/fixtures/s81_s09_flag_off_golden.json). No log line of this unit carries
# a key, an id, a fingerprint, a device key, a count or the pepper.
# ---------------------------------------------------------------------------
DEVICE_DAILY_CAP = 3  # R-S09-6: a module constant (the Terms s4 "up to 3"), no knob
RIYADH_UTC_OFFSET_HOURS = 3  # Asia/Riyadh, fixed, no DST (owner decision 5)
DEVICE_QUOTA_GRACE_SECONDS = 3600  # a quota-path counter outlives its reset by 1 h
DEVICE_QUOTA_EXEMPT_ENV = "DEVICE_QUOTA_EXEMPT_USER_IDS"  # R-S09-4 (a NAME only)
_DEVICE_QUOTA_EXEMPT_MAX = 50
_EXEMPT_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_EXEMPT_SPLIT_RE = re.compile(r"[\s,]+")
_RIYADH_TZ = timezone(timedelta(hours=RIYADH_UTC_OFFSET_HOURS))
_USAGE_LIMIT_EXTRA_FIELDS = ("retry_after", "resets_at", "scope")
_S09_TRUTHY = ("true", "1", "yes", "on")


def device_daily_quota_enabled() -> bool:
    """ENABLE_DEVICE_DAILY_QUOTA (S81-09, default OFF), read PER CALL.
    error_handler and referral_service read the SAME name through their own
    local one-liners (the middleware never imports a service)."""
    return os.getenv("ENABLE_DEVICE_DAILY_QUOTA", "false").strip().lower() in _S09_TRUTHY


def riyadh_reset_enabled() -> bool:
    """ENABLE_RIYADH_RESET (S81-09, default OFF), read PER CALL by the ONE date
    helper _usage_window: the usage calendar becomes Asia/Riyadh (+03:00)."""
    return os.getenv("ENABLE_RIYADH_RESET", "false").strip().lower() in _S09_TRUTHY


def _device_quota_exempt(user_id) -> bool:
    """R-S09-4: is ``user_id`` listed in DEVICE_QUOTA_EXEMPT_USER_IDS? Read per
    call with os.getenv; split on commas and whitespace; only canonical uuid
    tokens count (case-insensitive), at most the first 50 of them; unset or
    blank = nobody. Read only after the quota flag read ON and the tier is
    free, so flag OFF never reads it. The value is never logged."""
    raw = os.getenv(DEVICE_QUOTA_EXEMPT_ENV, "")
    if not isinstance(user_id, str) or not raw or not raw.strip():
        return False
    wanted = user_id.lower()
    valid = 0
    for token in _EXEMPT_SPLIT_RE.split(raw):
        candidate = token.strip().lower()
        if _EXEMPT_UUID_RE.fullmatch(candidate) is None:
            continue
        valid += 1
        if candidate == wanted:
            return True
        if valid >= _DEVICE_QUOTA_EXEMPT_MAX:
            return False
    return False


def _as_utc(now: datetime) -> datetime:
    """An aware UTC instant (a naive value is read as UTC, as riyadh_day does)."""
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _usage_window_state(now: Optional[datetime] = None):
    """(the usage day, the next reset as an aware UTC instant, Riyadh ON?) with
    ONE read of ENABLE_RIYADH_RESET. ``now`` defaults to the module ``datetime``
    clock (so a FakeDatetime patch of usage_service.datetime is honoured); only
    arithmetic on that value, never a datetime(...) construction through the
    module global. OFF: the UTC day of ``now`` exactly as the base key helpers
    formatted it, and the next UTC midnight. ON: the Asia/Riyadh day and the
    next 00:00 Riyadh (21:00 UTC). The reset is strictly after ``now``."""
    if now is None:
        now = datetime.now(timezone.utc)
    utc_now = _as_utc(now)
    if riyadh_reset_enabled():
        local = utc_now + timedelta(hours=RIYADH_UTC_OFFSET_HOURS)
        local_midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        next_reset = local_midnight + timedelta(days=1) - timedelta(hours=RIYADH_UTC_OFFSET_HOURS)
        return local.date(), next_reset, True
    utc_midnight = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now.date(), utc_midnight + timedelta(days=1), False


def _usage_window(now: Optional[datetime] = None):
    """S81-09: the ONE date helper of the usage counters, (day, next_reset);
    the four key helpers, the quota path and its status read it."""
    day, next_reset, _riyadh = _usage_window_state(now)
    return day, next_reset


def _reset_instant_text(next_reset: datetime, riyadh: bool) -> str:
    """The next reset as ISO 8601 in the reset zone (+03:00 under
    ENABLE_RIYADH_RESET, else +00:00): the same instant either way."""
    zone = _RIYADH_TZ if riyadh else timezone.utc
    return next_reset.astimezone(zone).isoformat(timespec="seconds")


def _daily_key(user_id: str, day=None) -> str:
    # S81-09: the day of the ONE usage calendar; the quota path passes the day
    # of its own single window read so its two keys can never straddle a reset.
    today = (day if day is not None else _usage_window()[0]).strftime("%Y-%m-%d")
    return f"usage:daily:{user_id}:{today}"


def _device_daily_key(device_hmac: str, day) -> str:
    """S81-09: the device-daily counter key: the S81-05 HMAC device key of the
    request fingerprint (never the fingerprint) and the usage day."""
    return f"usage:device:{device_hmac}:{day.strftime('%Y-%m-%d')}"


def _monthly_key(user_id: str) -> str:
    month = _usage_window()[0].strftime("%Y-%m")
    return f"usage:monthly:{user_id}:{month}"


def _previous_daily_key(user_id: str) -> str:
    """Yesterday's daily key — the refund fallback window (M18 usage-symmetry):
    a consume just before midnight refunded just after must credit back the
    window it actually debited. S81-09: yesterday of the usage calendar
    (_usage_window: UTC, or Asia/Riyadh under ENABLE_RIYADH_RESET)."""
    yesterday = _usage_window()[0] - timedelta(days=1)
    return f"usage:daily:{user_id}:{yesterday.strftime('%Y-%m-%d')}"


def _previous_monthly_key(user_id: str) -> str:
    """Last month's monthly key — the refund fallback window across a month
    rollover (the usage calendar of _usage_window)."""
    last_month = _usage_window()[0].replace(day=1) - timedelta(days=1)
    return f"usage:monthly:{user_id}:{last_month.strftime('%Y-%m')}"


# The two Lua scripts (R-S09-10; pinned byte for byte by the RED file: LF-joined,
# no trailing LF, the S81-04 RECORD_SCRIPT precedent). CONSUME: KEYS = [account
# daily] or [account daily, device daily]; ARGV = [account cap, device cap,
# expireat]; the device is checked and debited FIRST; a refusal writes nothing;
# EXPIREAT ARGV[3] on every debited key. Reply {code, account, device}: 0 =
# debited (the counts after), 1 = the account refused, 2 = the device refused.
DEVICE_CONSUME_SCRIPT = (
    "local a = tonumber(redis.call('GET', KEYS[1]) or '0')\n"
    "local d = 0\n"
    "if #KEYS > 1 then\n"
    "  d = tonumber(redis.call('GET', KEYS[2]) or '0')\n"
    "  if d >= tonumber(ARGV[2]) then return {2, a, d} end\n"
    "end\n"
    "if a >= tonumber(ARGV[1]) then return {1, a, d} end\n"
    "if #KEYS > 1 then\n"
    "  d = redis.call('INCR', KEYS[2])\n"
    "  redis.call('EXPIREAT', KEYS[2], ARGV[3])\n"
    "end\n"
    "a = redis.call('INCR', KEYS[1])\n"
    "redis.call('EXPIREAT', KEYS[1], ARGV[3])\n"
    "return {0, a, d}"
)
# REFUND: KEYS = the debited keys, no ARGV; a floor-at-zero DECR of each (never
# creates a key, never writes a TTL: the key keeps its EXPIREAT).
DEVICE_REFUND_SCRIPT = (
    "local out = {}\n"
    "for i, k in ipairs(KEYS) do\n"
    "  local v = tonumber(redis.call('GET', k) or '0')\n"
    "  if v > 0 then out[i] = redis.call('DECR', k) else out[i] = -1 end\n"
    "end\n"
    "return out"
)


class _DeviceDebit:
    """R-S09-3: the request-scoped record of ONE quota-path debit: the user id,
    the debited keys and an at-most-once refund latch. Set only on a debit
    (script code 0); a task created inside the request (fire_and_forget, the
    stream generator) copies the context and shares this object, so the latch
    is seen by every refund of the request."""

    __slots__ = ("user_id", "keys", "refunded")

    def __init__(self, user_id: str, keys: tuple):
        self.user_id = user_id
        self.keys = keys
        self.refunded = False


_DEVICE_DEBIT: ContextVar[Optional[_DeviceDebit]] = ContextVar("s81_09_device_debit", default=None)


def _device_consume_sync(keys: list, args: list):
    """ONE EVAL of DEVICE_CONSUME_SCRIPT on the module Redis client (read per
    call) through llm_spend_breaker._eval (the upstash-redis and redis-py call
    shapes, S81-04), imported inside the quota arm so flag OFF never imports it."""
    from app.services import llm_spend_breaker as _spend_breaker

    return _spend_breaker._eval(redis_client, DEVICE_CONSUME_SCRIPT, keys, args)


def _device_refund_sync(keys: list):
    """ONE EVAL of DEVICE_REFUND_SCRIPT over the debited keys (no ARGV)."""
    from app.services import llm_spend_breaker as _spend_breaker

    return _spend_breaker._eval(redis_client, DEVICE_REFUND_SCRIPT, keys, [])


async def _offload_dispatch_async(fn, *args):
    """The #115 dispatch of the S81-09 EVALs (parity with _atomic_consume_async):
    asyncio.to_thread iff ENABLE_ASYNC_REDIS_OFFLOAD, else inline on the loop."""
    if _redis_offload_enabled():
        return await asyncio.to_thread(fn, *args)
    return fn(*args)


def _parse_consume_reply(reply, has_device: bool):
    """(code, account_count, device_count), or None = BadReply (C19): exactly
    three ints (a bool is refused), a code in {0, 1, 2}, and code 2 only when a
    device key was sent. A reply of any other shape is never read as a debit."""
    if not isinstance(reply, (list, tuple)) or len(reply) != 3:
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in reply):
        return None
    code, account_count, device_count = reply
    if code not in (0, 1, 2) or (code == 2 and not has_device):
        return None
    return code, account_count, device_count


async def _consume_device_quota(user_id: str, device_fp) -> dict:
    """S81-09 quota path (ENABLE_DEVICE_DAILY_QUOTA ON, the free tier, not in the
    allow-list): ONE EVAL debits the account-daily key and, with a device key,
    the device-daily key (the device checked first, so a fresh account on a
    capped device gets nothing), EXPIREAT the next reset + 1 h. The monthly cap,
    the referral bonus and the lifetime-free bypass are retired on this path.
    No usable device key (no / malformed header, the pepper unset, the request
    context flag OFF) = account-only plus ONE INFO metric line, never a 400. A
    Redis error or a bad reply fails OPEN (allowed, nothing debited, no stash)
    with ONE WARNING (the outage counter). remaining.daily is the BINDING axis
    (GC-2); a refusal carries retry_after (int), resets_at and scope."""
    now = datetime.now(timezone.utc)
    device_hmac = _request_context.device_key(device_fp) if device_fp else None
    if device_hmac is None:
        logger.info(
            "[USAGE-DEVICE] account-only header=%s",
            _request_context.header_state(_request_context.HEADER_DEVICE_FINGERPRINT),
        )
    day, next_reset, riyadh = _usage_window_state(now)
    account_key = _daily_key(user_id, day)
    keys = [account_key]
    if device_hmac is not None:
        keys.append(_device_daily_key(device_hmac, day))
    account_cap = TIER_LIMITS["free"]["daily"]
    monthly_shown = TIER_LIMITS["free"]["monthly"]  # the retired axis, never binding
    fail_open = {
        "allowed": True,
        "reason": None,
        "tier": "free",
        "consumed": False,
        "remaining": {"daily": account_cap, "monthly": monthly_shown, "lifetime_free": 0},
    }
    if not redis_client:
        return fail_open
    expireat = int(next_reset.timestamp()) + DEVICE_QUOTA_GRACE_SECONDS
    args = [str(account_cap), str(DEVICE_DAILY_CAP), str(expireat)]
    try:
        reply = await _offload_dispatch_async(_device_consume_sync, keys, args)
    except Exception as exc:  # noqa: BLE001 - fail open; the type name only
        logger.warning("[USAGE-DEVICE] consume fail-open type=%s", type(exc).__name__)
        return fail_open
    parsed = _parse_consume_reply(reply, device_hmac is not None)
    if parsed is None:
        logger.warning("[USAGE-DEVICE] consume fail-open type=%s", "BadReply")
        return fail_open
    code, account_count, device_count = parsed
    account_left = 0 if code == 1 else max(0, account_cap - account_count)
    remaining = {"daily": account_left, "monthly": monthly_shown, "lifetime_free": 0}
    if device_hmac is not None:
        device_left = 0 if code == 2 else max(0, DEVICE_DAILY_CAP - device_count)
        remaining["daily"] = min(account_left, device_left)  # GC-2: the binding axis
        remaining["device_daily"] = device_left
    if code == 0:
        _DEVICE_DEBIT.set(_DeviceDebit(user_id, tuple(keys)))
        consumed_keys = {"daily": account_key}
        if device_hmac is not None:
            consumed_keys["device_daily"] = keys[1]
        return {
            "allowed": True,
            "reason": None,
            "tier": "free",
            "consumed": True,
            "consumed_keys": consumed_keys,
            "remaining": remaining,
        }
    device_refused = code == 2
    return {
        "allowed": False,
        "reason": "device_daily_limit" if device_refused else "daily_limit",
        "tier": "free",
        "consumed": False,
        "remaining": remaining,
        "retry_after": max(1, math.ceil((next_reset - _as_utc(now)).total_seconds())),
        "resets_at": _reset_instant_text(next_reset, riyadh),
        "scope": "device_daily" if device_refused else "daily",
    }


def _device_refund_keys(user_id: str, consumed_keys: Optional[dict]):
    """R-S09-3 / GC-5: the keys of a quota-path debit to refund, read WHATEVER the
    quota flag says now (the stash exists only after a debit made under the
    flag, so flag OFF without a stash is one ContextVar read and nothing else).
    Explicit consumed_keys carrying "device_daily" win; else the request-scoped
    stash when it names this user. The latch is set here, on the loop, before
    any offload, so a second refund of the same debit returns [] (no call).
    None = no quota-path debit: the caller runs the base refund unchanged."""
    debit = _DEVICE_DEBIT.get()
    if isinstance(consumed_keys, dict) and consumed_keys.get("device_daily"):
        keys = tuple(k for k in (consumed_keys.get("daily"), consumed_keys.get("device_daily")) if k)
        if debit is not None and debit.user_id == user_id and debit.keys == keys:
            if debit.refunded:
                return []
            debit.refunded = True
        return list(keys)
    if debit is None or debit.user_id != user_id:
        return None
    if debit.refunded:
        return []
    debit.refunded = True
    return list(debit.keys)


async def _refund_device_debit(keys: list) -> None:
    """Best effort, never raises: ONE EVAL of DEVICE_REFUND_SCRIPT over exactly
    the debited keys; a failure logs ONE WARNING with the type name only (the
    counters then stay +1 until their reset + 1 h)."""
    if not keys or not redis_client:
        return
    try:
        await _offload_dispatch_async(_device_refund_sync, keys)
    except Exception as exc:  # noqa: BLE001 - best effort; the type name only
        logger.warning("[USAGE-DEVICE] refund failed type=%s", type(exc).__name__)


def usage_limit_extras(usage_check: dict) -> dict:
    """S81-09: the additive USAGE_LIMIT 429 detail fields of a quota-path refusal
    (retry_after, resets_at, scope); {} for every base consume result (none
    carries them), so a route's 429 detail is unchanged with the flag OFF."""
    return {k: usage_check[k] for k in _USAGE_LIMIT_EXTRA_FIELDS if k in usage_check}


def device_quota_kwargs() -> dict:
    """S81-09: the extra kwargs of a consume call (and of the quota-path status
    call): {} with ENABLE_DEVICE_DAILY_QUOTA OFF (the base call, exactly
    (user_id, access_token)); ON, the request's bound X-Device-Fingerprint (the
    S81-05 ContextVar, None without a valid header), read on the request path
    before any offload. No route reads the header or names the leaf itself."""
    if not device_daily_quota_enabled():
        return {}
    return {"device_fp": _request_context.device_fingerprint()}


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


class _ConsumeOutcome(str):
    """Result of ``_atomic_consume`` (M18 usage-symmetry). Compares equal to the
    legacy reason string (``'' `` and falsy on success, ``'daily_limit'`` /
    ``'monthly_limit'`` on rejection) so every existing ``reason == ...`` check
    and test keeps working, while ALSO carrying:
      - ``daily_after`` / ``monthly_after``: the post-operation counter values
        (the INCRBY return values, rollback-adjusted) so callers need no
        redundant remaining-count GETs (LS-event-loop-03);
      - ``daily_key`` / ``monthly_key``: the exact date-stamped keys debited,
        so a refund can credit back the SAME window the consume debited
        (CD-interactions-07 / CD-wave-diffs-09).
    """

    daily_after: Optional[int]
    monthly_after: Optional[int]
    daily_key: Optional[str]
    monthly_key: Optional[str]

    def __new__(
        cls,
        reason: str = "",
        daily_after: Optional[int] = None,
        monthly_after: Optional[int] = None,
        daily_key: Optional[str] = None,
        monthly_key: Optional[str] = None,
    ):
        obj = super().__new__(cls, reason or "")
        obj.daily_after = daily_after
        obj.monthly_after = monthly_after
        obj.daily_key = daily_key
        obj.monthly_key = monthly_key
        return obj


def _atomic_consume(user_id: str, daily_limit: int, monthly_cap: int):
    """Atomic INCRBY-then-check-then-DECRBY-rollback of the daily then monthly
    Redis counters (the try_consume_serper_image_credit pattern). Returns a
    falsy ``_ConsumeOutcome('')`` on success (both counters advanced; carries
    the post-INCRBY counts and the exact keys debited), else an outcome equal
    to the reason string ('daily_limit'/'monthly_limit') after fully rolling
    back. Fails OPEN (plain None, counts unknown) on a Redis error — a cache
    outage must never block a legitimate user."""
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
            return _ConsumeOutcome(
                "daily_limit",
                daily_after=new_daily - 1,
                daily_key=daily_key,
                monthly_key=monthly_key,
            )
        new_monthly = redis_client.incrby(monthly_key, 1)
        if new_monthly == 1:
            _safe_expire(monthly_key, 86400 * 32)  # ~32d
        if new_monthly > monthly_cap:
            _safe_decr(monthly_key)
            _safe_decr(daily_key)  # roll back the daily taken above
            return _ConsumeOutcome(
                "monthly_limit",
                daily_after=new_daily - 1,
                monthly_after=new_monthly - 1,
                daily_key=daily_key,
                monthly_key=monthly_key,
            )
        return _ConsumeOutcome(
            "",
            daily_after=new_daily,
            monthly_after=new_monthly,
            daily_key=daily_key,
            monthly_key=monthly_key,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[usage] atomic consume failed for %s: %s — fail-open", user_id, e)
        return None


# --- #115 module-local offload dispatches (ENABLE_ASYNC_REDIS_OFFLOAD) -------
# Per the cache_service.py design note, each dispatch lives in the CALLING
# module and references the module-level blocking symbol in BOTH branches, so a
# test that patches usage_service._atomic_consume / _get_redis_count /
# _bump_counters intercepts flag-ON and flag-OFF alike. Flag OFF -> the sync
# call runs inline to completion with no scheduler yield (byte-identical).


async def _atomic_consume_async(user_id: str, daily_limit: int, monthly_cap: int):
    """Offload dispatch for _atomic_consume (up to ~6 Upstash commands). The
    INCRBY/DECRBY rollback ordering lives inside _atomic_consume, untouched."""
    if _redis_offload_enabled():
        return await asyncio.to_thread(_atomic_consume, user_id, daily_limit, monthly_cap)
    return _atomic_consume(user_id, daily_limit, monthly_cap)


async def _get_redis_count_async(key: str) -> int:
    """Offload dispatch for the remaining-count GETs on the consume path."""
    if _redis_offload_enabled():
        return await asyncio.to_thread(_get_redis_count, key)
    return _get_redis_count(key)


async def _bump_counters_async(user_id: str) -> None:
    """Offload dispatch for the lifetime-free-window counter bump."""
    if _redis_offload_enabled():
        return await asyncio.to_thread(_bump_counters, user_id)
    return _bump_counters(user_id)


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


async def consume_comparison_credit(
    user_id: str, access_token: str, *, device_fp: Optional[str] = None
) -> dict:
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
    daily/monthly credit was taken and must be refunded on a later work failure)
    and 'consumed_keys' (the exact date-stamped Redis keys debited — pass them
    to refund_comparison_credit so the refund credits the SAME window).

    S81-09: ``device_fp`` (keyword-only; the routes pass it only under
    ENABLE_DEVICE_DAILY_QUOTA, through device_quota_kwargs) feeds the quota
    path: flag ON, the free tier and a user outside the allow-list take
    _consume_device_quota (3 a day per account AND per device, one EVAL);
    premium, a NULL or any other tier, the allow-list and flag OFF run the base
    body below unchanged.
    """
    # LS-event-loop-03: the two Supabase reads are independent of each other —
    # fetch them concurrently instead of serially.
    user_info, bonus = await asyncio.gather(
        _get_user_tier_info(user_id), _get_active_referral_bonus(user_id)
    )
    tier = user_info.get("subscription_tier", "free")
    # S81-09: the flag is read FIRST, so OFF reads no allow-list and no state.
    if device_daily_quota_enabled() and tier == "free" and not _device_quota_exempt(user_id):
        return await _consume_device_quota(user_id, device_fp)
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    monthly_cap = limits["monthly"] + bonus

    # Lifetime-free path: allowed regardless of daily/monthly, but still advance
    # the counters (parity with the legacy record_comparison).
    if tier == "free" and lifetime_used < limits["lifetime_free"]:
        # Keys captured adjacent to the bump so a later refund credits the
        # window actually debited (the microsecond window to the incrby inside
        # _bump_counters is negligible next to the minutes-later refund).
        consumed_keys = {"daily": _daily_key(user_id), "monthly": _monthly_key(user_id)}
        await _bump_counters_async(user_id)
        return {
            "allowed": True,
            "reason": None,
            "tier": tier,
            "consumed": True,
            "consumed_keys": consumed_keys,
            "remaining": {
                "daily": limits["daily"],
                "monthly": monthly_cap,
                "lifetime_free": limits["lifetime_free"] - lifetime_used,
            },
        }

    # #115 — the atomic consume (and any fallback remaining-count read) goes
    # through the module-local async dispatches (ENABLE_ASYNC_REDIS_OFFLOAD;
    # inline when OFF). LS-event-loop-03: the INCRBY return values carried on
    # the outcome ARE the post-consume counts, so the success path issues ZERO
    # extra reads; the GET fallback only fires for legacy/fail-open outcomes
    # with no counts attached.
    outcome = await _atomic_consume_async(user_id, limits["daily"], monthly_cap)
    reason = (str(outcome) or None) if outcome is not None else None
    daily_after = getattr(outcome, "daily_after", None)
    monthly_after = getattr(outcome, "monthly_after", None)
    if reason == "daily_limit":
        monthly_used = (
            monthly_after
            if monthly_after is not None
            else await _get_redis_count_async(_monthly_key(user_id))
        )
        return {
            "allowed": False, "reason": "daily_limit", "tier": tier, "consumed": False,
            "remaining": {"daily": 0, "monthly": max(0, monthly_cap - monthly_used), "lifetime_free": 0},
        }
    if reason == "monthly_limit":
        daily_used = (
            daily_after
            if daily_after is not None
            else await _get_redis_count_async(_daily_key(user_id))
        )
        return {
            "allowed": False, "reason": "monthly_limit", "tier": tier, "consumed": False,
            "remaining": {"daily": max(0, limits["daily"] - daily_used), "monthly": 0, "lifetime_free": 0},
        }
    daily_used = (
        daily_after
        if daily_after is not None
        else await _get_redis_count_async(_daily_key(user_id))
    )
    monthly_used = (
        monthly_after
        if monthly_after is not None
        else await _get_redis_count_async(_monthly_key(user_id))
    )
    return {
        "allowed": True, "reason": None, "tier": tier, "consumed": True,
        "consumed_keys": {
            "daily": getattr(outcome, "daily_key", None) or _daily_key(user_id),
            "monthly": getattr(outcome, "monthly_key", None) or _monthly_key(user_id),
        },
        "remaining": {
            "daily": max(0, limits["daily"] - daily_used),
            "monthly": max(0, monthly_cap - monthly_used),
            "lifetime_free": 0,
        },
    }


def _refund_one_window(primary_key: Optional[str], fallback_key: Optional[str], ttl: int) -> None:
    """Floor-at-zero refund of one counter window (M18 CD-interactions-07 /
    CD-wave-diffs-09). Tries ``primary_key``; if the DECRBY would go negative
    (the key was absent — this consume's debit lives in an OLDER window, e.g. a
    pre-midnight consume refunded post-midnight, or was never taken at all) the
    decrement is compensated back, the stray key gets a TTL so it cannot leak,
    and the ``fallback_key`` (previous window) is tried the same way. Never
    leaves a counter negative.

    GET-before-DECR (not blind DECR) so a window that holds no debit — e.g.
    the monthly counter after a partial fail-open consume where only the daily
    INCRBY succeeded — is never decremented at all; the compensation branch
    only covers the small GET→DECR race against a concurrent refund."""
    for key in (primary_key, fallback_key):
        if not key:
            continue
        try:
            raw = redis_client.get(key)
            current = int(raw) if raw else 0
        except Exception:  # noqa: BLE001 — refund is best-effort
            return
        if current <= 0:
            continue  # no debit recorded in this window — try the older one
        try:
            value = redis_client.decrby(key, 1)
        except Exception:  # noqa: BLE001
            return
        if value >= 0:
            return  # credited a real debit in this window — done
        # Lost a GET→DECR race (another refund drained it first). Undo, and if
        # we just created the key (-1), attach a TTL so the stray 0-key expires.
        try:
            redis_client.incrby(key, 1)
            if value == -1:
                _safe_expire(key, ttl)
        except Exception:  # noqa: BLE001
            return


def _refund_credit_sync(counter_id: str, consumed_keys: Optional[dict] = None) -> None:
    """Blocking body of refund_comparison_credit. With ``consumed_keys`` the
    refund credits EXACTLY the keys the consume debited (deterministic
    symmetry). Without them (legacy callers) it floors-at-zero on the current
    window and falls back to the previous day/month window, so a consume that
    straddled a UTC boundary is still credited back where it was debited."""
    if not redis_client:
        return
    if consumed_keys:
        _refund_one_window(consumed_keys.get("daily"), None, 86400)
        _refund_one_window(consumed_keys.get("monthly"), None, 86400 * 32)
        return
    _refund_one_window(_daily_key(counter_id), _previous_daily_key(counter_id), 86400)
    _refund_one_window(_monthly_key(counter_id), _previous_monthly_key(counter_id), 86400 * 32)


async def refund_comparison_credit(user_id: str, consumed_keys: Optional[dict] = None) -> None:
    """Best-effort refund of the daily+monthly credit reserved at the gate, for
    when the comparison work then failed — preserves the legacy behaviour where a
    failed comparison did not burn a daily credit. Fire-and-forget safe.

    M18 usage-symmetry: pass the gate result's ``consumed_keys`` to credit the
    exact window the consume debited; without them the refund floors at zero
    and falls back to the previous UTC window instead of driving the NEW
    window's counter negative (the midnight/month-rollover corruption).

    S81-09 (R-S09-3): a quota-path debit is refunded first, by ONE EVAL of
    DEVICE_REFUND_SCRIPT over exactly the keys it debited (the account and the
    device counter), at most once per debit; every other refund (no such debit
    in this request) runs the base body below unchanged."""
    device_keys = _device_refund_keys(user_id, consumed_keys)
    if device_keys is not None:
        await _refund_device_debit(device_keys)
        return
    try:
        # #115-style offload dispatch: both branches reference the module-level
        # blocking symbol so test patches intercept flag-ON and flag-OFF alike.
        if _redis_offload_enabled():
            await asyncio.to_thread(_refund_credit_sync, user_id, consumed_keys)
        else:
            _refund_credit_sync(user_id, consumed_keys)
    except Exception as e:  # noqa: BLE001
        logger.warning("[usage] refund failed for %s: %s", user_id, e)


async def record_lifetime_comparison(user_id: str, access_token: str) -> None:
    """Fire-and-forget Supabase lifetime-counter increment. The daily+monthly
    Redis credit is reserved synchronously at the gate by consume_comparison_credit,
    so this deliberately does NOT touch the Redis counters (that would double-count)."""
    try:
        client = get_admin_supabase_client()
        await run_db(lambda: client.rpc("increment_lifetime_comparisons", {"target_user_id": user_id}).execute())
    except Exception as e:
        logger.error(f"Failed to record lifetime comparison for {user_id}: {e}")


async def _get_user_tier_info(user_id: str) -> dict:
    """Get user's subscription tier, lifetime usage, and referral bonus state.

    Performs lazy reset of ``referral_bonus_comparisons_this_month`` when
    ``referral_bonus_reset_at`` is in the past — no cron needed.
    """
    try:
        client = get_admin_supabase_client()
        result = await run_db(lambda: client.table("users").select(
            "subscription_tier, lifetime_comparisons_used, "
            "referral_bonus_comparisons_this_month, referral_bonus_reset_at"
        ).eq("id", user_id).single().execute())
        data = result.data or {}
        # Lazy referral bonus reset. #115 — W3 deferred this site by name: the
        # reset path does a users UPDATE .execute() inline on the loop. The
        # whole call goes through run_db (ENABLE_SYNC_DB_OFFLOAD; inline when
        # OFF); the lambda references the module-level symbol so test patches
        # on usage_service._maybe_reset_referral_bonus intercept both branches.
        return await run_db(lambda: _maybe_reset_referral_bonus(client, user_id, data))
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
        resp = await run_db(lambda: (
            client.table("referral_redemptions")
            .select("loop2_comparisons_granted")
            .eq("referrer_user_id", user_id)
            .gt("expires_at", now_iso)
            .is_("consumed_at", "null")
            .execute()
        ))
        rows = resp.data or []
        return sum(int(r.get("loop2_comparisons_granted") or 0) for r in rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[usage] active referral bonus lookup failed for %s: %s", user_id, exc
        )
        return 0


async def _usage_reads_offloop(user_id: str) -> list:
    """S81 ST1 (ENABLE_USAGE_PATH_OFFLOOP): the four usage reads in ONE gather.

    The Supabase half is the EXISTING async helpers, byte-unchanged: they go
    through run_db, so they leave the loop only under ENABLE_SYNC_DB_OFFLOAD
    (R-ST1-1 / R-ST1-2). The two Upstash counter GETs run on the shared
    redis-offloop pool whatever ENABLE_PRICE_PATH_REDIS_OFFLOOP says. The date
    keys are computed on the loop before any dispatch. The two GETs are listed
    FIRST (fix round 1, F1-8), so with ENABLE_SYNC_DB_OFFLOAD OFF they are in
    flight on the pool while the inline Supabase reads run. Returns
    ``[user_info, bonus, daily_used, monthly_used]``.

    If building an awaitable raises (a synchronous dispatch failure), the
    awaitables already built are closed before the error propagates, so no
    coroutine is left un-awaited (GT-6); the caller then falls back inline.
    """
    daily_key = _daily_key(user_id)
    monthly_key = _monthly_key(user_id)
    reads = []
    try:
        reads.append(run_redis_offloop_pool(_get_redis_count, daily_key))
        reads.append(run_redis_offloop_pool(_get_redis_count, monthly_key))
        reads.append(_get_user_tier_info(user_id))
        reads.append(_get_active_referral_bonus(user_id))
    except BaseException:
        for pending in reads:
            close = getattr(pending, "close", None)
            if callable(close):
                close()
        raise
    daily_used, monthly_used, user_info, bonus = await asyncio.gather(*reads)
    return [user_info, bonus, daily_used, monthly_used]


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
    if usage_path_offloop_enabled():
        # S81 ST1: the four reads in one gather, then the one compute body. A
        # dispatch failure logs one WARNING and runs the base path below; the
        # body runs outside the try, so a compute failure propagates as at base.
        try:
            reads = await _usage_reads_offloop(user_id)
        except Exception as exc:  # noqa: BLE001 - dispatch failure: fall back inline
            logger.warning(
                "[USAGE-OFFLOOP] dispatch failed fn=check_usage_allowed type=%s -- inline fallback",
                type(exc).__name__,
            )
        else:
            return _usage_allowed_body(*reads)
    user_info = await _get_user_tier_info(user_id)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    # Path-(a): entitlement bonus = sum of active referral_redemptions rows
    # (not the INT counter, which stays for analytics only).
    bonus = await _get_active_referral_bonus(user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # Lifetime free comparisons (free tier only): no counter is read, as at base.
    if tier == "free" and lifetime_used < limits["lifetime_free"]:
        return _usage_allowed_body(user_info, bonus, 0, 0)

    # Get current usage from Redis
    daily_used = _get_redis_count(_daily_key(user_id))
    monthly_used = _get_redis_count(_monthly_key(user_id))
    return _usage_allowed_body(user_info, bonus, daily_used, monthly_used)


def _usage_allowed_body(user_info: dict, bonus: int, daily_used: int, monthly_used: int) -> dict:
    """S81 ST1 (R-ST1-3): the ONE compute body of check_usage_allowed, called by
    both flag states. Pure (no I/O); the counters are ignored on the
    lifetime-free path, as at base."""
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
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
        await run_db(lambda: client.rpc("increment_lifetime_comparisons", {"target_user_id": user_id}).execute())

    except Exception as e:
        logger.error(f"Failed to record comparison usage for {user_id}: {e}")


async def get_usage_status(user_id: str, access_token: str) -> dict:
    """Get current usage counts and limits for display.

    Reports the EFFECTIVE monthly cap (base + active referral bonus) so the
    frontend's "X / Y" display accurately reflects entitlement.
    Path-(a): bonus is summed from active redemptions, not the INT counter.
    """
    if usage_path_offloop_enabled():
        # S81 ST1: the four reads in one gather, then the one compute body. A
        # dispatch failure logs one WARNING and runs the base path below; the
        # body runs outside the try, so a compute failure propagates as at base.
        try:
            reads = await _usage_reads_offloop(user_id)
        except Exception as exc:  # noqa: BLE001 - dispatch failure: fall back inline
            logger.warning(
                "[USAGE-OFFLOOP] dispatch failed fn=get_usage_status type=%s -- inline fallback",
                type(exc).__name__,
            )
        else:
            return _usage_status_body(*reads)
    user_info = await _get_user_tier_info(user_id)
    bonus = await _get_active_referral_bonus(user_id)
    daily_used = _get_redis_count(_daily_key(user_id))
    monthly_used = _get_redis_count(_monthly_key(user_id))
    return _usage_status_body(user_info, bonus, daily_used, monthly_used)


def _usage_status_body(
    user_info: dict, bonus: int, daily_used: int, monthly_used: int, *, device: Optional[dict] = None
) -> dict:
    """S81 ST1 (R-ST1-3): the ONE compute body of get_usage_status, called by
    both flag states. Pure (no I/O); builds the base response in the base key
    order. S81-09: ``device`` (keyword-only, the quota-path window of
    get_device_usage_status) selects the quota-path body; None, as every base
    caller passes, is the base body unchanged."""
    if device is not None:
        return _device_status_body(user_info, daily_used, device)
    tier = user_info.get("subscription_tier", "free")
    lifetime_used = user_info.get("lifetime_comparisons_used", 0)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    monthly_cap = limits["monthly"] + bonus

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


def _device_status_body(user_info: dict, account_used: int, window: dict) -> dict:
    """S81-09 the quota-path /usage/status body (R-S09-1, R-S09-6, R-S09-14):
    remaining.daily / used.daily carry the BINDING axis (the device when its
    remaining is lower or equal: a tie names the device) so every reader of
    remaining.daily gates truthfully; remaining.device_daily only with a device
    key; the retired monthly axis is reported as never binding (used 0, bonus 0,
    remaining the full allowance) and remaining.lifetime_free as 0 (the bypass is
    retired); used.lifetime is the stored count (R-S08-13); limits.device_daily
    (DEVICE_DAILY_CAP) is appended last in limits, with or without a device key
    (GC-3); resets_at and counted_scope close the body."""
    free = TIER_LIMITS["free"]
    account_left = max(0, free["daily"] - account_used)
    device_used = window.get("device_used")
    has_device = device_used is not None
    device_left = max(0, DEVICE_DAILY_CAP - device_used) if has_device else None
    device_binds = has_device and device_left <= account_left
    remaining = {
        "daily": device_left if device_binds else account_left,
        "monthly": free["monthly"],
        "lifetime_free": 0,
    }
    if has_device:
        remaining["device_daily"] = device_left
    return {
        "tier": "free",
        "used": {
            "daily": device_used if device_binds else account_used,
            "monthly": 0,
            "lifetime": user_info.get("lifetime_comparisons_used", 0),
        },
        "limits": {
            "daily": free["daily"],
            "monthly": free["monthly"],
            "monthly_base": free["monthly"],
            "monthly_bonus": 0,
            "lifetime_free": free["lifetime_free"],
            "device_daily": DEVICE_DAILY_CAP,
        },
        "remaining": remaining,
        "resets_at": window["resets_at"],
        "counted_scope": "device_daily" if device_binds else "daily",
    }


async def _device_status_counts_offloop(keys: list) -> list:
    """The quota-path counter GETs as jobs on the shared redis-offloop pool (the
    ST1 _usage_reads_offloop pattern: the keys are computed on the loop first;
    if building an awaitable raises, those already built are closed before the
    error propagates, so no coroutine is left un-awaited)."""
    pending = []
    try:
        for key in keys:
            pending.append(run_redis_offloop_pool(_get_redis_count, key))
    except BaseException:
        for awaitable in pending:
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
        raise
    return list(await asyncio.gather(*pending))


async def _device_status_counts(keys: list) -> list:
    """The quota-path status counter GETs: on the shared redis-offloop pool under
    ENABLE_USAGE_PATH_OFFLOOP (the ST1 placement), else inline as the base
    status reads them. A dispatch failure logs ONE WARNING (the ST1 line shape,
    the type name only) and reads inline."""
    if usage_path_offloop_enabled():
        try:
            return await _device_status_counts_offloop(keys)
        except Exception as exc:  # noqa: BLE001 - dispatch failure: read inline
            logger.warning(
                "[USAGE-OFFLOOP] dispatch failed fn=get_device_usage_status type=%s -- inline fallback",
                type(exc).__name__,
            )
    return [_get_redis_count(key) for key in keys]


async def get_device_usage_status(
    user_id: str, access_token: str, *, device_fp: Optional[str] = None
) -> dict:
    """S81-09 /usage/status under ENABLE_DEVICE_DAILY_QUOTA (the route reads the
    flag, then calls this with the request's bound X-Device-Fingerprint). An
    allow-listed user: the base get_usage_status (no other read first). Else ONE
    tier read; a non-free tier (premium, NULL, any other string): the base
    get_usage_status, byte-identical (one extra tier read, stated). The free
    tier: GET the account-daily and, with a device key, the device-daily
    counter of ONE usage window (no bonus read, no monthly read); the body is
    the ONE compute body with the device window."""
    if _device_quota_exempt(user_id):
        return await get_usage_status(user_id, access_token)
    user_info = await _get_user_tier_info(user_id)
    if user_info.get("subscription_tier", "free") != "free":
        return await get_usage_status(user_id, access_token)
    device_hmac = _request_context.device_key(device_fp) if device_fp else None
    day, next_reset, riyadh = _usage_window_state()
    keys = [_daily_key(user_id, day)]
    if device_hmac is not None:
        keys.append(_device_daily_key(device_hmac, day))
    counts = await _device_status_counts(keys)
    window = {
        "device_used": counts[1] if device_hmac is not None else None,
        "resets_at": _reset_instant_text(next_reset, riyadh),
    }
    return _usage_status_body(user_info, 0, counts[0], 0, device=window)
