"""SPEND-BREAKER (S81-04, ENABLE_LLM_SPEND_BREAKER): per-Asia/Riyadh-day USD caps
on every LLM dispatch.

A LAST-RESORT spend bound, not an abuse control (R-S04-11): four lanes (live,
escalation, search, offclock) each hold one Upstash key per Riyadh day,
``llm_spend:<lane>:<YYYY-MM-DD>`` (a string float written by INCRBYFLOAT, expiring
one hour after the next Riyadh midnight). The flag is read per call by
``spend_breaker_enabled`` and is the first statement of every gated caller
branch; with it OFF no function here is called.

The contract every LLM dispatch follows (spec 2.8 as amended by RULINGS_S81_04;
binding on S81-06 / S81-16 / S81-21 / S81-22 and the escalation unit):

1. Gate: ``if llm_spend_breaker.spend_breaker_enabled():`` first.
2. Before the provider call: ``await admit_async(lane, ub)`` on the event loop,
   ``admit(lane, ub)`` in a script or worker thread, with ``ub`` the call's
   UPPER BOUND: ``upper_bound_usd(provider, model, prompt_tokens, max_tokens,
   web_search_max_uses)`` and, when that is None (an unpriced id),
   ``conservative_bound_usd(provider, prompt_tokens, max_tokens, searches)``
   (the most expensive row of the provider's table; Anthropic and any other
   provider: the Sonnet 5.5 row; OpenAI: the 4o row; R-S04-3). ``prompt_tokens``
   is ``count_tokens`` when the adapter has it, else
   ``prompt_token_upper_bound(messages, response_format, tools, provider)``.
   A refused call raises the EXISTING ``api_budget_service.LLMUnavailableError``
   (a caller maps it by class, never by message text).
3. After a SERVED response: ``record_soon(lane, actual, admitted_usd=ub)`` on the
   loop or ``record(lane, actual, admitted_usd=ub)`` off it, ``actual`` =
   ``llm_pricing.price_call(...)`` over the served usage. An unpriced or missing
   actual records the admitted bound (never zero; gate GC-4 covers a served
   response with no usage too). A raising or cancelled call records nothing.
4. Batch / cron / search submitters RESERVE instead (R-S04-5):
   ``reserve(lane, ub)`` is ONE Lua check-and-increment and returns True when the
   bound is held (None on a fail-open, when nothing is known to be held); after
   the results land, ``settle(lane, ub, actual)`` when the reserve returned True,
   ``record(lane, actual, admitted_usd=ub)`` when it returned None.
5. Lanes: ``live`` for a request-path call (the chokepoint lane is per process,
   ``LLM_SPEND_CHOKEPOINT_LANE``), ``escalation`` for a Sonnet escalation,
   ``search`` for a call carrying web_search, ``offclock`` for Batch submissions
   and crons. The breaker is not a ``PROVIDER_CONFIGS`` provider (R-S03-9).

Reads are memoised per process for ``LLM_SPEND_MEMO_SECONDS`` together with this
process's own in-flight record deltas (R-S04-1); every Redis command is bounded by
``LLM_SPEND_REDIS_TIMEOUT_SECONDS`` and runs on the dedicated ``llm-spend`` pool of
four workers, never on the event loop and never on the default executor
(R-S04-2). Every Redis problem fails OPEN: no client, an error, a stalled
command or a bad stored value admits and records nothing, with one rate-limited
WARNING (type names only) and the ``llm_spend_fail_open`` counter on /health.

Imports: the stdlib, ``cache_service`` (the client, read per call through the
module attribute), ``llm_pricing`` and ``openai_pricing`` (prices) and
``async_utils`` (the durable background-task registry). ``api_budget_service``
imports this module at its top, so the refusal class is imported inside the
refusal arm only (no cycle). No model-id literal lives here.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from app.services import cache_service as _cache_service
from app.services import llm_pricing as _llm_pricing
from app.services import openai_pricing as _openai_pricing
from app.utils import async_utils as _async_utils

logger = logging.getLogger(__name__)

FLAG = "ENABLE_LLM_SPEND_BREAKER"

LANE_LIVE = "live"
LANE_ESCALATION = "escalation"
LANE_SEARCH = "search"
LANE_OFFCLOCK = "offclock"
LANES: Tuple[str, ...] = tuple(_llm_pricing.SPEND_LANES)

# The owner's open ruling, bracketed defaults (PLAN_S81 "Owner rulings still
# open"): USD per Asia/Riyadh day. About 140 OpenAI list-price compares a day fit
# the live default (runs/critic.json cost_table, about 0.021 USD per compare).
DEFAULT_CAPS_USD: Dict[str, float] = {
    LANE_LIVE: 3.0, LANE_ESCALATION: 1.0, LANE_SEARCH: 0.5, LANE_OFFCLOCK: 2.0,
}
CAP_ENV: Dict[str, str] = {
    LANE_LIVE: "LLM_SPEND_CAP_LIVE_USD",
    LANE_ESCALATION: "LLM_SPEND_CAP_ESCALATION_USD",
    LANE_SEARCH: "LLM_SPEND_CAP_SEARCH_USD",
    LANE_OFFCLOCK: "LLM_SPEND_CAP_OFFCLOCK_USD",
}
MEMO_ENV = "LLM_SPEND_MEMO_SECONDS"
DEFAULT_MEMO_SECONDS = 5.0
REDIS_TIMEOUT_ENV = "LLM_SPEND_REDIS_TIMEOUT_SECONDS"
DEFAULT_REDIS_TIMEOUT_SECONDS = 0.5  # the measured TLS GET is 163-203 ms (S78-SM)
ENTRY_RESERVE_ENV = "LLM_SPEND_ENTRY_RESERVE_USD"
DEFAULT_ENTRY_RESERVE_USD = 0.10
CHOKEPOINT_LANE_ENV = "LLM_SPEND_CHOKEPOINT_LANE"

RIYADH_UTC_OFFSET_HOURS = 3  # Asia/Riyadh, fixed, no DST (owner decision 5)
KEY_PREFIX = "llm_spend"
KEY_GRACE_SECONDS = 3600  # the key outlives its Riyadh day by one hour

# The prompt upper bound counts UTF-8 BYTES as tokens (a byte-level BPE token
# covers at least one byte), plus a fixed overhead per call and per message.
OVERHEAD_TOKENS_PER_CALL = 16
OVERHEAD_TOKENS_PER_MESSAGE = 4
# R-S04-9: OpenAI's published high-detail image rule for the 4o family: 85 base
# tokens + 170 per 512-px tile, at most 8 tiles (768 x 2048 after the resize).
OPENAI_IMAGE_PART_TOKEN_BOUND = 85 + 170 * 8
# R-S04-9: Anthropic's rule ceil(w/28) x ceil(h/28), the long edge downscaled to
# 2,576 px, capped at 4,784 tokens (runs/research/R14.json).
ANTHROPIC_IMAGE_TILE_PX = 28
ANTHROPIC_IMAGE_TOKEN_CAP = 4784
_IMAGE_PART_TYPES = ("image_url", "input_image", "image")
# Gate GC-3: the output bound for a garbage or missing max_tokens, and the token
# count of the conservative fallback bound of a garbage admitted bound.
LLM_SPEND_FALLBACK_OUTPUT_TOKENS = 16384
DEFAULT_OUTPUT_TOKEN_BOUND = LLM_SPEND_FALLBACK_OUTPUT_TOKENS

POOL_WORKERS = 4
POOL_THREAD_PREFIX = "llm-spend"

# Gate GC-9: the two Lua scripts, pinned as literals by the unit file.
# RECORD: KEYS[1] = the lane key; ARGV = [delta, expireat]. INCRBYFLOAT returns a
# bulk string, returned unchanged (a Lua number would truncate to an integer).
RECORD_SCRIPT = (
    "local v = redis.call('INCRBYFLOAT', KEYS[1], ARGV[1])\n"
    "redis.call('EXPIREAT', KEYS[1], ARGV[2])\n"
    "return v"
)
# RESERVE: KEYS[1] = the lane key; ARGV = [upper_bound, cap, expireat]. Refuses
# (nil) when spent + upper_bound > cap, else adds the bound and returns the total.
RESERVE_SCRIPT = (
    "local cur = tonumber(redis.call('GET', KEYS[1]) or '0')\n"
    "if cur + tonumber(ARGV[1]) > tonumber(ARGV[2]) then return false end\n"
    "local v = redis.call('INCRBYFLOAT', KEYS[1], ARGV[1])\n"
    "redis.call('EXPIREAT', KEYS[1], ARGV[3])\n"
    "return v"
)
# Contains none of "429", "rate", "quota": the verdict fallback matcher
# (extraction_service) keys on those substrings, so a refused primary verdict
# never dispatches a second call.
REFUSAL_MESSAGE = "llm spend cap reached for lane %s; dispatch suppressed"

_FAILOPEN_WARN_INTERVAL_SECONDS = 60.0


class RedisUnconfigured(Exception):
    """No Redis client in this process (the fail-open reason name)."""


class SpendTicket(NamedTuple):
    """The opaque admit ticket: the lane and the admitted upper bound (USD)."""

    lane: str
    bound_usd: float


class _Flight(NamedTuple):
    """One submitted record: the delta counted in the memo until it lands."""

    lane: str
    day: str
    amount: float
    generation: int


_LOCK = threading.Lock()
# lane -> {"day": str, "base": float, "read_at": float}: the last total this
# process observed in Upstash (a GET, or the total an EVAL returned).
_MEMO: Dict[str, Dict[str, Any]] = {}
# (lane, day) -> [sum, count] of the record deltas submitted and not yet landed.
_INFLIGHT: Dict[Tuple[str, str], List[float]] = {}
_WARN_AT: Dict[str, float] = {}
_STATE: Dict[str, Any] = {"ran": False, "fail_open": 0, "generation": 0}
_POOL: Optional[concurrent.futures.ThreadPoolExecutor] = None
_POOL_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# test seams [prod: the real clock and the cache_service client]
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _monotonic() -> float:
    return time.monotonic()


def _client() -> Any:
    """The process Redis client, read per call through the module attribute
    (never ``from cache_service import redis_client``: the #183 reload hazard)."""
    return _cache_service.redis_client


# ---------------------------------------------------------------------------
# flag and knobs (read per call)
# ---------------------------------------------------------------------------
def spend_breaker_enabled() -> bool:
    """The house idiom, read per call (never cached)."""
    return os.getenv(FLAG, "false").strip().lower() in ("true", "1", "yes", "on")


def _positive_float_knob(name: str, default: float) -> float:
    """Unset / blank / garbage / inf / -inf / nan / <= 0 -> the default."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except ValueError:
        return default
    if not math.isfinite(value) or value <= 0:
        return default
    return value


def _check_lane(lane: Any) -> None:
    if not isinstance(lane, str) or lane not in LANES:
        raise ValueError("unknown spend lane")


def cap_usd(lane: str) -> float:
    """The lane cap in USD per Riyadh day, read per call. ValueError for an
    unknown lane (a programming error, never a fail-open)."""
    _check_lane(lane)
    return _positive_float_knob(CAP_ENV[lane], DEFAULT_CAPS_USD[lane])


def memo_seconds() -> float:
    return _positive_float_knob(MEMO_ENV, DEFAULT_MEMO_SECONDS)


def redis_timeout_seconds() -> float:
    return _positive_float_knob(REDIS_TIMEOUT_ENV, DEFAULT_REDIS_TIMEOUT_SECONDS)


def entry_reserve_usd() -> float:
    return _positive_float_knob(ENTRY_RESERVE_ENV, DEFAULT_ENTRY_RESERVE_USD)


def chokepoint_lane() -> str:
    """The lane of the guarded_llm_create chokepoint in this process (R-S04-6):
    the knob stripped and lower-cased; anything outside LANES -> live."""
    raw = (os.getenv(CHOKEPOINT_LANE_ENV) or "").strip().lower()
    return raw if raw in LANES else LANE_LIVE


# ---------------------------------------------------------------------------
# the Riyadh day and the key
# ---------------------------------------------------------------------------
def riyadh_day(now: Optional[datetime] = None) -> Tuple[str, int]:
    """(the Asia/Riyadh day as YYYY-MM-DD, the key's EXPIREAT epoch seconds =
    the next Riyadh midnight + one hour). A naive ``now`` is read as UTC.
    Module-local; S81-09 may move it to a shared helper."""
    now = now if now is not None else _utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    day = (now + timedelta(hours=RIYADH_UTC_OFFSET_HOURS)).date()
    next_midnight_utc = (datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
                         + timedelta(days=1) - timedelta(hours=RIYADH_UTC_OFFSET_HOURS))
    return day.isoformat(), int(next_midnight_utc.timestamp()) + KEY_GRACE_SECONDS


def spend_key(lane: str, day: str) -> str:
    _check_lane(lane)
    return "%s:%s:%s" % (KEY_PREFIX, lane, day)


# ---------------------------------------------------------------------------
# upper bounds (pure, never raise)
# ---------------------------------------------------------------------------
def _nbytes(value: Any) -> int:
    try:
        return len(str(value).encode("utf-8"))
    except Exception:  # noqa: BLE001 -- a bound never raises
        return 0


def _json_bytes(value: Any) -> int:
    try:
        return len(json.dumps(value, default=str).encode("utf-8"))
    except Exception:  # noqa: BLE001 -- a bound never raises
        return _nbytes(value)


def anthropic_image_token_bound(width: Any, height: Any) -> int:
    """ceil(w/28) x ceil(h/28) capped at ANTHROPIC_IMAGE_TOKEN_CAP; any dimension
    that is not a positive finite non-bool number -> the cap."""
    def _ok(v: Any) -> bool:
        return (isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) and v > 0)
    if not (_ok(width) and _ok(height)):
        return ANTHROPIC_IMAGE_TOKEN_CAP
    tiles = (math.ceil(width / ANTHROPIC_IMAGE_TILE_PX)
             * math.ceil(height / ANTHROPIC_IMAGE_TILE_PX))
    return min(tiles, ANTHROPIC_IMAGE_TOKEN_CAP)


def _image_part_bound(provider: Any) -> int:
    # An unknown provider takes the larger (Anthropic) bound.
    return OPENAI_IMAGE_PART_TOKEN_BOUND if provider == "openai" else ANTHROPIC_IMAGE_TOKEN_CAP


def _content_bound(content: Any, provider: Any) -> int:
    if content is None:
        return 0
    if isinstance(content, str):
        return _nbytes(content)
    if isinstance(content, (list, tuple)):
        total = 0
        for part in content:
            if isinstance(part, dict):
                kind = part.get("type")
                if kind == "text":
                    text = part.get("text")
                    total += _nbytes(text) if text is not None else 0
                elif kind in _IMAGE_PART_TYPES:
                    total += _image_part_bound(provider)
                else:
                    total += _json_bytes(part)
            else:
                total += _nbytes(part)
        return total
    return _nbytes(content)


def prompt_token_upper_bound(messages: Any, response_format: Any = None, tools: Any = None,
                             provider: Any = "openai") -> int:
    """An UPPER bound on the billed prompt tokens of one chat call: 16 per call,
    then per message 4 + the content bound (str: its UTF-8 bytes; a part list: a
    text part's bytes, an image part the provider's image bound whatever its
    data-URL size, any other part its JSON bytes) + the JSON bytes of every key
    other than role / content (name, tool_calls); then the JSON bytes of
    ``response_format`` and of ``tools`` (billed non-message input, review
    correction 8). Never raises."""
    total = OVERHEAD_TOKENS_PER_CALL
    try:
        if isinstance(messages, (list, tuple)):
            for message in messages:
                total += OVERHEAD_TOKENS_PER_MESSAGE
                if isinstance(message, dict):
                    total += _content_bound(message.get("content"), provider)
                    for key, value in message.items():
                        if key not in ("role", "content") and value is not None:
                            total += _json_bytes(value)
                else:
                    total += _content_bound(message, provider)
        if response_format is not None:
            total += _json_bytes(response_format)
        if tools is not None:
            total += _json_bytes(tools)
    except Exception:  # noqa: BLE001 -- a bound never raises
        return total
    return total


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def output_token_bound(max_tokens: Any, max_completion_tokens: Any) -> int:
    """The first of the two that is a positive non-bool int, else
    LLM_SPEND_FALLBACK_OUTPUT_TOKENS."""
    for value in (max_tokens, max_completion_tokens):
        if _positive_int(value):
            return value
    return LLM_SPEND_FALLBACK_OUTPUT_TOKENS


def upper_bound_usd(provider: Any, model: Any, prompt_tokens: Any, max_tokens: Any,
                    web_search_max_uses: Any = 0) -> Optional[float]:
    """The S81-03 list price of the bound (``llm_pricing.price_call``, sync,
    batch False); None when the call is unpriced. Never raises."""
    try:
        return _llm_pricing.price_call(provider, model, input_tokens=prompt_tokens,
                                       output_tokens=max_tokens,
                                       web_search_requests=web_search_max_uses)
    except Exception:  # noqa: BLE001 -- a bound never raises
        return None


def _most_expensive_row(table: Any) -> Dict[str, float]:
    return max(table.values(), key=lambda row: (row.get("output", 0.0), row.get("input", 0.0)))


def _count_or_zero(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def conservative_bound_usd(provider: Any, prompt_tokens: Any, output_tokens: Any,
                           web_search_requests: Any = 0) -> float:
    """The bound of an UNPRICED call (R-S04-3): the rates of the most expensive
    row of the provider's table (OpenAI: the 4o row; Anthropic and any other
    provider: the Sonnet 5.5 row), derived from the S81-03 tables, plus 0.01 USD
    per search. A garbage output count -> LLM_SPEND_FALLBACK_OUTPUT_TOKENS, a
    garbage prompt or search count -> 0. Never None, never zero."""
    if provider == "openai":
        row = _most_expensive_row(_openai_pricing.PRICE_USD_PER_1M)
    else:
        row = _most_expensive_row(_llm_pricing.ANTHROPIC_PRICE_USD_PER_1M)
    prompt = _count_or_zero(prompt_tokens)
    output = output_tokens if _positive_int(output_tokens) else LLM_SPEND_FALLBACK_OUTPUT_TOKENS
    searches = _count_or_zero(web_search_requests)
    return ((prompt * row["input"] + output * row["output"]) / 1e6
            + searches * _llm_pricing.WEB_SEARCH_USD_PER_REQUEST)


def fallback_bound_usd(provider: Any = None) -> float:
    """Gate GC-3: the bound of a garbage or missing admitted bound = the
    conservative rate at LLM_SPEND_FALLBACK_OUTPUT_TOKENS output tokens
    (``admit`` knows no provider, so it uses the unknown-provider branch)."""
    return conservative_bound_usd(provider, 0, LLM_SPEND_FALLBACK_OUTPUT_TOKENS)


def _valid_usd(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def _cents(value: float) -> int:
    # round, never ceil: 0.07 * 100 == 7.000000000000001 (measured)
    return int(round(value * 100))


def _fmt(value: float) -> str:
    return "%.10f" % value


# ---------------------------------------------------------------------------
# state: the memo, the in-flight deltas, the rate-limited warnings
# ---------------------------------------------------------------------------
def _warn_limited(kind: str, message: str, *args: Any) -> None:
    now = _monotonic()
    with _LOCK:
        last = _WARN_AT.get(kind)
        if last is not None and 0 <= now - last < _FAILOPEN_WARN_INTERVAL_SECONDS:
            return
        _WARN_AT[kind] = now
    logger.warning(message, *args)


def _fail_open(reason: str) -> None:
    """Count the fail-open (it is a run of the breaker for /health, GC-5) and
    log at most one WARNING per process per minute, the reason a type name."""
    with _LOCK:
        _STATE["ran"] = True
        _STATE["fail_open"] += 1
    _warn_limited("failopen", "[SPEND] breaker fail-open (%s) -- admitting and not recording", reason)


def _warn_unpriced(lane: str) -> None:
    _warn_limited("unpriced",
                  "[SPEND] lane=%s upper bound unpriced -- admitting on the conservative bound", lane)


def _sanitized_bound(lane: str, value: Any) -> float:
    """R-S04-10: a non-number, NaN, inf, negative or bool bound is the GC-3
    fallback bound; never a TypeError out of admit, never a zero-cost admit."""
    if _valid_usd(value):
        return float(value)
    _warn_unpriced(lane)
    return fallback_bound_usd(None)


def _inflight_sum(lane: str, day: str) -> float:
    entry = _INFLIGHT.get((lane, day))
    return entry[0] if entry else 0.0


def _memo_view(lane: str, day: str) -> Optional[float]:
    """The memoised spent total (the observed base + this process's in-flight
    deltas) while the memo is fresh for ``day``; None when a read is due."""
    now = _monotonic()
    window = memo_seconds()
    with _LOCK:
        entry = _MEMO.get(lane)
        if entry is None or entry["day"] != day:
            return None
        age = now - entry["read_at"]
        if not 0 <= age < window:
            return None
        return entry["base"] + _inflight_sum(lane, day)


def _observe_read(lane: str, day: str, total: float) -> float:
    """A GET is authoritative: it replaces the base. Returns the spent view."""
    now = _monotonic()
    with _LOCK:
        _MEMO[lane] = {"day": day, "base": total, "read_at": now}
        _STATE["ran"] = True
        return total + _inflight_sum(lane, day)


def _observe_write_locked(lane: str, day: str, total: float) -> None:
    """An EVAL total includes this write and everything that landed before it;
    concurrent writes can return out of order, so the base only moves up here
    (a decrease, from a settle, is seen at the next GET). Caller holds _LOCK."""
    entry = _MEMO.get(lane)
    now = _monotonic()
    if entry is None or entry["day"] != day:
        _MEMO[lane] = {"day": day, "base": total, "read_at": now}
    else:
        entry["base"] = max(entry["base"], total)
        entry["read_at"] = now
    _STATE["ran"] = True


def _parse_total(raw: Any) -> Optional[float]:
    try:
        value = float(raw.decode("utf-8") if hasattr(raw, "decode") else raw)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    return value if math.isfinite(value) else None


def _inflight_add(lane: str, day: str, amount: float) -> _Flight:
    with _LOCK:
        entry = _INFLIGHT.setdefault((lane, day), [0.0, 0])
        entry[0] += amount
        entry[1] += 1
        _STATE["ran"] = True
        return _Flight(lane, day, amount, _STATE["generation"])


def _inflight_done(flight: _Flight, raw: Any) -> None:
    """The submitted record finished (``raw`` = the EVAL result, or None when it
    raised): drop its delta from the in-flight sum and, on success, observe the
    returned total, in ONE critical section. A flight of an earlier state
    generation (a test reset) is ignored."""
    total = _parse_total(raw) if raw is not None else None
    with _LOCK:
        if flight.generation != _STATE["generation"]:
            return
        key = (flight.lane, flight.day)
        entry = _INFLIGHT.get(key)
        if entry is not None:
            entry[0] -= flight.amount
            entry[1] -= 1
            if entry[1] <= 0:
                _INFLIGHT.pop(key, None)
        if total is not None:
            _observe_write_locked(flight.lane, flight.day, total)


# ---------------------------------------------------------------------------
# the dedicated pool and the bounded calls (R-S04-2)
# ---------------------------------------------------------------------------
def _get_llm_spend_pool() -> concurrent.futures.ThreadPoolExecutor:
    """The dedicated ``llm-spend`` pool (POOL_WORKERS threads), built lazily:
    never the loop's default ``qaren-worker`` executor (the adapter fan-out) and
    never the ``redis-offloop`` pool (it queues behind multi-MB catalog GETs)."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = concurrent.futures.ThreadPoolExecutor(
                max_workers=POOL_WORKERS, thread_name_prefix=POOL_THREAD_PREFIX)
            logger.info("[SPEND] pool built workers=%d", POOL_WORKERS)
        return _POOL


def _run_bounded_sync(fn: Any, *args: Any) -> Any:
    """Run ``fn`` on the pool and wait at most LLM_SPEND_REDIS_TIMEOUT_SECONDS
    (a sync caller: a script or a worker thread). A timeout raises TimeoutError;
    a queued job is cancelled, a running one finishes on its thread."""
    future = _get_llm_spend_pool().submit(fn, *args)
    try:
        return future.result(timeout=redis_timeout_seconds())
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise TimeoutError("llm spend redis call timed out") from None


async def _run_bounded_async(fn: Any, *args: Any, durable: bool = False) -> Any:
    """Await ``fn`` on the pool under ``asyncio.wait_for``; the loop thread never
    runs the command. ``durable``: the job is shielded, so a timeout or a
    cancellation never cancels a write that already started."""
    future = asyncio.wrap_future(_get_llm_spend_pool().submit(fn, *args))
    awaitable = asyncio.shield(future) if durable else future
    return await asyncio.wait_for(awaitable, redis_timeout_seconds())


def _eval(client: Any, script: str, keys: List[str], args: List[str]) -> Any:
    """The two client shapes differ (spec 2.6): upstash-redis 1.7.0
    ``eval(script, keys=, args=)``; redis-py 8.1.0 ``eval(script, numkeys, *keys_and_args)``."""
    if type(client).__module__.split(".")[0] == "upstash_redis":
        return client.eval(script, keys=list(keys), args=list(args))
    return client.eval(script, len(keys), *keys, *args)


def _read_spent(client: Any, key: str) -> float:
    """One GET; a missing key is 0.0; a value that is not a finite float >= 0
    raises ValueError (a fail-open)."""
    raw = client.get(key)
    if raw is None:
        return 0.0
    value = float(raw.decode("utf-8") if hasattr(raw, "decode") else raw)
    if not math.isfinite(value) or value < 0:
        raise ValueError("bad stored spend")
    return value


def _record_job(client: Any, key: str, amount: float, expireat: int, flight: _Flight) -> Any:
    """The record EVAL, run on a pool thread; it settles its own in-flight delta
    exactly once (success or failure), even after its awaiter gave up."""
    try:
        raw = _eval(client, RECORD_SCRIPT, [key], [_fmt(amount), str(expireat)])
    except BaseException:
        _inflight_done(flight, None)
        raise
    _inflight_done(flight, raw)
    return raw


# ---------------------------------------------------------------------------
# the decisions
# ---------------------------------------------------------------------------
def lane_exhausted(lane: str, spent: float) -> bool:
    """Gate GC-6: the ONE exhausted predicate, used by the compare-entry check
    and by the /health snapshot: spent + LLM_SPEND_ENTRY_RESERVE_USD >= cap."""
    return spent + entry_reserve_usd() >= cap_usd(lane)


def _refuse_dispatch(lane: str, spent: float, bound: float) -> None:
    from app.services.api_budget_service import LLMUnavailableError

    logger.warning(
        "[SPEND] lane=%s cap reached (spent_cents=%d cap_cents=%d bound_cents=%d) -- dispatch refused",
        lane, _cents(spent), _cents(cap_usd(lane)), _cents(bound))
    raise LLMUnavailableError(REFUSAL_MESSAGE % lane)


def _decide(lane: str, spent: float, bound: float) -> None:
    # STRICT: spent + bound == cap is admitted.
    if spent + bound > cap_usd(lane):
        _refuse_dispatch(lane, spent, bound)


def admit(lane: str, upper_bound_usd: Any) -> None:
    """Sync admit (scripts, batch submitters, worker threads): refuse with the
    existing LLMUnavailableError iff spent + bound > cap (strict). The flag is
    not read here (callers gate). Fail-open -> None."""
    _check_lane(lane)
    bound = _sanitized_bound(lane, upper_bound_usd)
    day, _expireat = riyadh_day()
    spent = _memo_view(lane, day)
    if spent is None:
        client = _client()
        if client is None:
            _fail_open(RedisUnconfigured.__name__)
            return None
        try:
            base = _run_bounded_sync(_read_spent, client, spend_key(lane, day))
        except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
            _fail_open(type(exc).__name__)
            return None
        spent = _observe_read(lane, day, base)
    _decide(lane, spent, bound)
    return None


async def admit_async(lane: str, upper_bound_usd: Any) -> None:
    """The event-loop admit: a fresh memo costs no hop; a due read is ONE GET on
    the llm-spend pool under the timeout. ``LLMUnavailableError`` propagates; a
    cancellation propagates; every other failure admits (fail-open)."""
    _check_lane(lane)
    bound = _sanitized_bound(lane, upper_bound_usd)
    day, _expireat = riyadh_day()
    spent = _memo_view(lane, day)
    if spent is None:
        client = _client()
        if client is None:
            _fail_open(RedisUnconfigured.__name__)
            return None
        try:
            base = await _run_bounded_async(_read_spent, client, spend_key(lane, day))
        except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
            _fail_open(type(exc).__name__)
            return None
        spent = _observe_read(lane, day, base)
    _decide(lane, spent, bound)
    return None


async def entry_refuses_async(lane: str) -> bool:
    """The compare-entry check (R-S04-4, read-only): True iff the lane is
    exhausted (``lane_exhausted``); one WARNING without the query. Fail-open ->
    False."""
    _check_lane(lane)
    day, _expireat = riyadh_day()
    spent = _memo_view(lane, day)
    if spent is None:
        client = _client()
        if client is None:
            _fail_open(RedisUnconfigured.__name__)
            return False
        try:
            base = await _run_bounded_async(_read_spent, client, spend_key(lane, day))
        except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
            _fail_open(type(exc).__name__)
            return False
        spent = _observe_read(lane, day, base)
    if not lane_exhausted(lane, spent):
        return False
    logger.warning(
        "[SPEND] lane=%s cap reached (spent_cents=%d cap_cents=%d reserve_cents=%d) -- "
        "short-circuiting the compare BEFORE the provider fan-out",
        lane, _cents(spent), _cents(cap_usd(lane)), _cents(entry_reserve_usd()))
    return True


def _record_amount(actual_usd: Any, admitted_usd: Any) -> Optional[float]:
    """The amount a record writes: a positive finite actual, else a positive
    finite admitted bound (R-S04-3: never zero), else nothing."""
    for value in (actual_usd, admitted_usd):
        if _valid_usd(value) and value > 0:
            return float(value)
    return None


def record(lane: str, actual_usd: Any, admitted_usd: Any = None) -> None:
    """Sync record: ONE Lua EVAL (INCRBYFLOAT + EXPIREAT) on the pool under the
    timeout. Fail-open on any problem (no raise)."""
    _check_lane(lane)
    amount = _record_amount(actual_usd, admitted_usd)
    if amount is None:
        return None
    client = _client()
    if client is None:
        _fail_open(RedisUnconfigured.__name__)
        return None
    day, expireat = riyadh_day()
    flight = _inflight_add(lane, day, amount)
    try:
        _run_bounded_sync(_record_job, client, spend_key(lane, day), amount, expireat, flight)
    except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
        _fail_open(type(exc).__name__)
    return None


async def _record_task(client: Any, key: str, amount: float, expireat: int, flight: _Flight) -> None:
    try:
        await _run_bounded_async(_record_job, client, key, amount, expireat, flight, durable=True)
    except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
        _fail_open(type(exc).__name__)
    return None


def record_soon(lane: str, actual_usd: Any, admitted_usd: Any = None) -> Optional[asyncio.Task]:
    """The live-path record, NON-awaited: the delta joins the memo at once and the
    EVAL runs as a durable background task (registered in
    ``async_utils._BACKGROUND_TASKS``, so the W1-6 shutdown drain covers it and a
    request cancellation never cancels it). None when nothing is recorded."""
    _check_lane(lane)
    amount = _record_amount(actual_usd, admitted_usd)
    if amount is None:
        return None
    client = _client()
    if client is None:
        _fail_open(RedisUnconfigured.__name__)
        return None
    day, expireat = riyadh_day()
    flight = _inflight_add(lane, day, amount)
    coro = _record_task(client, spend_key(lane, day), amount, expireat, flight)
    try:
        return _async_utils.fire_and_forget(coro, "llm_spend.record")
    except Exception as exc:  # noqa: BLE001 -- e.g. no running loop
        coro.close()
        _inflight_done(flight, None)
        _fail_open(type(exc).__name__)
        return None


def reserve(lane: str, upper_bound_usd: Any) -> Optional[bool]:
    """R-S04-5: ONE Lua EVAL that adds the bound when spent + bound <= cap.
    True = the bound is held (settle later); a refusal raises LLMUnavailableError;
    None = failed open (nothing known to be held: record instead of settle)."""
    _check_lane(lane)
    bound = _sanitized_bound(lane, upper_bound_usd)
    client = _client()
    if client is None:
        _fail_open(RedisUnconfigured.__name__)
        return None
    day, expireat = riyadh_day()
    cap = cap_usd(lane)
    try:
        raw = _run_bounded_sync(_eval, client, RESERVE_SCRIPT, [spend_key(lane, day)],
                                [_fmt(bound), _fmt(cap), str(expireat)])
    except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
        _fail_open(type(exc).__name__)
        return None
    if raw is None or raw is False:
        from app.services.api_budget_service import LLMUnavailableError

        logger.warning(
            "[SPEND] lane=%s cap reached (cap_cents=%d bound_cents=%d) -- reservation refused",
            lane, _cents(cap), _cents(bound))
        raise LLMUnavailableError(REFUSAL_MESSAGE % lane)
    total = _parse_total(raw)
    if total is not None:
        with _LOCK:
            _observe_write_locked(lane, day, total)
    return True


def settle(lane: str, upper_bound_usd: Any, actual_usd: Any) -> None:
    """R-S04-5: ONE INCRBYFLOAT of (actual - bound) after a held reserve. An
    unpriced (invalid) actual or an exact one issues no command (the reserved
    bound stays: never zero). Fail-open on any problem."""
    _check_lane(lane)
    if not _valid_usd(upper_bound_usd) or not _valid_usd(actual_usd):
        return None
    delta = float(actual_usd) - float(upper_bound_usd)
    if delta == 0:
        return None
    client = _client()
    if client is None:
        _fail_open(RedisUnconfigured.__name__)
        return None
    day, expireat = riyadh_day()
    try:
        raw = _run_bounded_sync(_eval, client, RECORD_SCRIPT, [spend_key(lane, day)],
                                [_fmt(delta), str(expireat)])
    except Exception as exc:  # noqa: BLE001 -- fail-open, the type name only
        _fail_open(type(exc).__name__)
        return None
    total = _parse_total(raw)
    if total is not None:
        with _LOCK:
            _observe_write_locked(lane, day, total)
    return None


# ---------------------------------------------------------------------------
# the guarded_llm_create helpers (the OpenAI chokepoint)
# ---------------------------------------------------------------------------
async def admit_openai_dispatch(model: Any, messages: Any, max_tokens: Any, max_completion_tokens: Any,
                                response_format: Any = None, tools: Any = None) -> SpendTicket:
    """Bound one OpenAI chat call from its kwargs and admit it on the chokepoint
    lane; returns the opaque ticket the record needs."""
    lane = chokepoint_lane()
    provider = _llm_pricing.provider_of(model) or "openai"
    prompt = prompt_token_upper_bound(messages, response_format, tools, provider)
    output = output_token_bound(max_tokens, max_completion_tokens)
    bound = upper_bound_usd(provider, model, prompt, output)
    if bound is None:
        _warn_unpriced(lane)
        bound = conservative_bound_usd(provider, prompt, output)
    await admit_async(lane, bound)
    return SpendTicket(lane, bound)


def record_openai_response_soon(ticket: Any, model: Any, response: Any) -> Optional[asyncio.Task]:
    """Record a SERVED response at its list price when the model is priced and
    the response carries a usage; otherwise the admitted bound (R-S04-3, GC-4).
    Never raises."""
    try:
        if not isinstance(ticket, SpendTicket):
            return None
        actual = None
        usage = getattr(response, "usage", None)
        if usage is not None and _openai_pricing.price_row(model) is not None:
            actual = _llm_pricing.openai_usage_cost_usd(model, usage)
        return record_soon(ticket.lane, actual, admitted_usd=ticket.bound_usd)
    except Exception as exc:  # noqa: BLE001 -- the record never fails a served call
        _fail_open(type(exc).__name__)
        return None


# ---------------------------------------------------------------------------
# /health and the admin view (pure: no Redis command, no thread)
# ---------------------------------------------------------------------------
def _memo_copy() -> Tuple[bool, int, Dict[str, Dict[str, Any]], Dict[Tuple[str, str], float]]:
    with _LOCK:
        return (bool(_STATE["ran"]), int(_STATE["fail_open"]),
                {lane: dict(entry) for lane, entry in _MEMO.items()},
                {key: entry[0] for key, entry in _INFLIGHT.items()})


def spend_snapshot() -> Dict[str, Any]:
    """/health (R-S04-7): ``{}`` until the breaker ran in this process (a
    fail-open counts, GC-5); then ``llm_spend`` {lane: {exhausted, day}} for each
    observed lane (``exhausted`` = ``lane_exhausted`` on the current Riyadh day)
    and the ``llm_spend_fail_open`` counter. No amounts; never raises."""
    try:
        ran, fail_open, memo, inflight = _memo_copy()
        if not ran:
            return {}
        today = riyadh_day()[0]
        lanes: Dict[str, Any] = {}
        for lane in LANES:
            entry = memo.get(lane)
            if entry is None:
                continue
            spent = entry["base"] + inflight.get((lane, entry["day"]), 0.0)
            exhausted = entry["day"] == today and lane_exhausted(lane, spent)
            lanes[lane] = {"exhausted": bool(exhausted), "day": entry["day"]}
        return {"llm_spend": lanes, "llm_spend_fail_open": fail_open}
    except Exception:  # noqa: BLE001 -- /health must never fail
        return {}


def admin_snapshot() -> Dict[str, Any]:
    """The X-Admin-Key view (GET /api/v1/admin/costs ``spend_breaker``): per
    observed lane the spent total this process holds, the cap, the day and the
    memo age in seconds. Never raises ({} on a failure)."""
    try:
        _ran, _fail_open_count, memo, inflight = _memo_copy()
        now = _monotonic()
        out: Dict[str, Any] = {}
        for lane in LANES:
            entry = memo.get(lane)
            if entry is None:
                continue
            spent = entry["base"] + inflight.get((lane, entry["day"]), 0.0)
            out[lane] = {
                "spent_usd": round(spent, 6),
                "cap_usd": cap_usd(lane),
                "day": entry["day"],
                "memo_age_seconds": round(max(0.0, now - entry["read_at"]), 3),
            }
        return out
    except Exception:  # noqa: BLE001 -- the admin page must never fail on this
        return {}


def _reset_spend_breaker_state() -> None:
    """Test-only: drop the memo, the in-flight deltas, the warning timestamps and
    the counters; a record finishing later belongs to the old generation and is
    ignored."""
    with _LOCK:
        _MEMO.clear()
        _INFLIGHT.clear()
        _WARN_AT.clear()
        _STATE["ran"] = False
        _STATE["fail_open"] = 0
        _STATE["generation"] += 1
