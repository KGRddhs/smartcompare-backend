"""D14 LIVE-ROBOTS: the persisted robots verdict before a live fetch, plus the
per-compare attempt counters and their ONE Redis health flush.

Flags (new names, default OFF, read PER CALL, the price_service.exact_gate_enabled
idiom; never cached):

* ``ENABLE_LIVE_ROBOTS_REGISTRY`` - the main flag. ON, every hooked fetcher (the
  curl wave, the Shopify .js / .json / UCP hop fetcher, the WooCommerce Store API, the
  Algolia storefront, URL mode) asks :func:`gate` before it fetches; the answer
  comes from the PERSISTED S81-15 record of the host (a per-process memo of the
  merchant rows: host, status, deny, robots, challenge), never from a robots.txt
  fetch on the live path. Anything but an allow is a skip, counted
  ``robots_skip`` (fail-closed: a cold memo skips). It also answers the D08 seam
  ``jsonld_widen.ROBOTS_ENTRY_LOOKUP``. OFF: every hook is one env read and the
  base statements; no memo read, no client, no ContextVar write, no Redis call.
* ``ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`` - the sub-flag (meaningful only with the
  main flag ON): the per-compare counters are flushed as ONE Upstash pipeline of
  ``HINCRBY kbh:<UTC day>:<host> <source>:<outcome> <n>`` + one ``EXPIRE`` per key,
  on the shared ``redis-offloop`` pool, never awaited by the response.

Knobs (read per call, defensive): the three ``MERCHANT_REGISTRY_*`` memo knobs of
merchant_registry (reused by name) and ``LIVE_ROBOTS_HEALTH_TTL_DAYS`` (8, 1..30).

The verdict (:func:`url_verdict`) and the memo snapshot (:func:`records_snapshot`,
:func:`load_records_sync`) are flag-free: S81-17 KB-INGEST reads them for its
offer / image decisions whatever the main flag says.

Log lines carry constants, normalized hosts and ints only (never a URL path or
query). Test seams (module attributes read at call time): ``_now`` (aware
datetime, the verdict clock), ``_monotonic`` (seconds, the memo clock),
``_admin_client`` and ``_redis_client`` (each called to obtain the client).
"""
from __future__ import annotations

import asyncio
import contextvars
import copy
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import urlsplit

from app.services import deny_hosts, jsonld_widen

logger = logging.getLogger(__name__)

_TRUTHY = ("true", "1", "yes", "on")

#: The reasons a URL is refused, in decision order (the G2 url_gate order minus tos).
VERDICT_REASONS: Tuple[str, ...] = (
    "bad_url", "denied", "no_row", "not_live", "no_record", "origin", "robots",
)
#: The attempt outcomes the per-compare aggregator counts.
OUTCOMES: Tuple[str, ...] = ("ok", "fail", "robots_skip", "challenge")
#: The memo's read: exactly these columns of the live and blocked merchant rows.
READ_COLUMNS = "host,status,deny,robots,challenge"
READ_STATUSES: Tuple[str, ...] = ("live", "blocked")
_VIEW_KEYS: Tuple[str, ...] = ("host", "status", "deny", "robots", "challenge")
_ENTRY_KEYS: Tuple[str, ...] = ("status", "deny", "robots", "challenge")
_PAGE_SIZE = 500
_HEALTH_PREFIX = "kbh:"
_TTL_DEFAULT_DAYS = 8.0
_TTL_MIN_DAYS = 1.0
_TTL_MAX_DAYS = 30.0


# --------------------------------------------------------------------------- flags
def live_robots_enabled() -> bool:
    """True iff ``ENABLE_LIVE_ROBOTS_REGISTRY`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_LIVE_ROBOTS_REGISTRY", "false").strip().lower() in _TRUTHY


def health_flush_enabled() -> bool:
    """True iff ``ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_LIVE_ROBOTS_HEALTH_FLUSH", "false").strip().lower() in _TRUTHY


def health_ttl_seconds() -> int:
    """``LIVE_ROBOTS_HEALTH_TTL_DAYS`` in seconds: default 8 days, clamped 1..30;
    unset, blank, garbage, inf, nan or <= 0 fall back to the default."""
    days = _TTL_DEFAULT_DAYS
    raw = os.getenv("LIVE_ROBOTS_HEALTH_TTL_DAYS")
    if raw is not None:
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            value = float("nan")
        if math.isfinite(value) and value > 0:
            days = min(max(value, _TTL_MIN_DAYS), _TTL_MAX_DAYS)
    return int(days) * 86400


# --------------------------------------------------------------------------- seams
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _monotonic() -> float:
    return time.monotonic()


def _admin_client() -> Any:
    from app.services.database_service import get_admin_supabase_client

    return get_admin_supabase_client()


def _redis_client() -> Any:
    from app.services import cache_service

    return cache_service.redis_client


def _memo_seconds() -> float:
    from app.services import merchant_registry

    return merchant_registry.memo_seconds()


def _read_timeout_seconds() -> float:
    from app.services import merchant_registry

    return merchant_registry.read_timeout_seconds()


def _max_stale_seconds() -> float:
    from app.services import merchant_registry

    return merchant_registry.max_stale_seconds()


# --------------------------------------------------------------------------- hosts
def _origin_of(url: Any) -> str:
    """scheme://host[:port] of an http(s) URL (lower-case host), else ""."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except (TypeError, ValueError, AttributeError):
        return ""
    if parts.scheme not in ("http", "https") or not host:
        return ""
    return parts.scheme + "://" + host + (":" + str(port) if port else "")


def host_of(url: Any) -> str:
    """The normalized host of a URL (deny_hosts.normalize_host), "" when none."""
    try:
        if not isinstance(url, str):
            return ""
        return deny_hosts.normalize_host(urlsplit(url.strip()).hostname or "")
    except Exception:  # noqa: BLE001 - a host read never raises
        return ""


def match_row(rows: Any, host: Any) -> Optional[Dict[str, Any]]:
    """The row of ``host`` in ``rows`` ({host: view}); else the row of the LONGEST
    registry host that ``host`` is a subdomain of; else None. No copy."""
    if not isinstance(rows, Mapping):
        return None
    h = deny_hosts.normalize_host(host) if isinstance(host, str) else ""
    if not h:
        return None
    if h in rows:
        return rows[h]
    best = None
    for key in rows:
        if isinstance(key, str) and key and h.endswith("." + key) and (
                best is None or len(key) > len(best)):
            best = key
    return rows[best] if best is not None else None


# --------------------------------------------------------------------------- verdict
def url_verdict(url: Any, row: Any, now: Any) -> Optional[str]:
    """None = allow, else one VERDICT_REASONS member. Pure, total, never raises
    (an internal error is ``bad_url``, fail-closed). The order is the G2 url_gate
    order: url shape, the deny list, the row, live, the record, the origin, then
    jsonld_widen.rating_host_allowed (state allow, fresh, untruncated, BOTH the
    named-agent and the * rules allow the path, no parked challenge)."""
    try:
        if not isinstance(url, str):
            return "bad_url"
        parts = urlsplit(url.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return "bad_url"
        if deny_hosts.is_denied_url(url):
            return "denied"
        if not isinstance(row, dict):
            return "no_row"
        if row.get("deny"):
            return "denied"
        if row.get("status") != "live":
            return "not_live"
        robots = row.get("robots")
        if not isinstance(robots, dict) or not robots.get("origin"):
            return "no_record"
        if robots.get("origin") != _origin_of(url):
            return "origin"
        entry = {key: row.get(key) for key in _ENTRY_KEYS}
        if not jsonld_widen.rating_host_allowed(entry, url, now):
            return "robots"
        return None
    except Exception:  # noqa: BLE001 - fail-closed
        return "bad_url"


# --------------------------------------------------------------------------- memo
_LOCK = threading.Lock()
_STATE: Dict[str, Any] = {
    "rows": None,       # Dict[host, view] of the last GOOD load, or None
    "loaded_at": None,  # monotonic time of the last load ATTEMPT (good or failed)
    "good_at": None,    # monotonic time of the last GOOD load
    "warned_at": None,  # monotonic time of the last refresh-failure WARNING
}
_REFRESH: Optional[Tuple[Any, Any]] = None  # (loop, task) of the in-flight refresh


def _read_rows(client: Any) -> Dict[str, Dict[str, Any]]:
    """The paged read of the live + blocked merchant rows (worker thread only)."""
    from app.services import merchant_registry

    rows: Dict[str, Dict[str, Any]] = {}
    start = 0
    while True:
        resp = (
            client.table(merchant_registry.KB_MERCHANTS_TABLE)
            .select(READ_COLUMNS)
            .in_("status", list(READ_STATUSES))
            .order("host")
            .range(start, start + _PAGE_SIZE - 1)
            .execute()
        )
        data = getattr(resp, "data", None) or []
        for raw in data:
            if not isinstance(raw, dict) or not isinstance(raw.get("host"), str):
                continue
            host = deny_hosts.normalize_host(raw["host"])
            if not host:
                continue
            view = {key: copy.deepcopy(raw.get(key)) for key in _VIEW_KEYS}
            view["host"] = host
            rows[host] = view
        if len(data) < _PAGE_SIZE:
            return rows
        start += _PAGE_SIZE


def _store_good(rows: Dict[str, Dict[str, Any]]) -> None:
    now = _monotonic()
    with _LOCK:
        _STATE["rows"] = rows
        _STATE["loaded_at"] = now
        _STATE["good_at"] = now


def load_records_sync(client: Any) -> Dict[str, Dict[str, Any]]:
    """Flag-free: read the records with ``client`` on the CALLING thread (a worker
    thread, never the loop), store the good load in the memo and return a copy
    {host: view}. Raises what the read raises (the caller owns the failure)."""
    rows = _read_rows(client)
    _store_good(rows)
    return copy.deepcopy(rows)


def records_snapshot() -> Optional[Dict[str, Dict[str, Any]]]:
    """Flag-free and AGE-AWARE (R-G3-5): a copy of the last good load while it is
    younger than MERCHANT_REGISTRY_MEMO_SECONDS, else None. Never raises."""
    try:
        now = _monotonic()
        with _LOCK:
            rows, good_at = _STATE["rows"], _STATE["good_at"]
        if rows is None or good_at is None or now - good_at > _memo_seconds():
            return None
        return copy.deepcopy(rows)
    except Exception:  # noqa: BLE001
        return None


async def _refresh() -> None:
    try:
        client = _admin_client()
        if client is None:
            raise RuntimeError("no service-role client")
        rows = await asyncio.wait_for(asyncio.to_thread(_read_rows, client),
                                      _read_timeout_seconds())
        _store_good(rows)
    except Exception as exc:  # noqa: BLE001 - keep the last good load
        now = _monotonic()
        warn = False
        with _LOCK:
            _STATE["loaded_at"] = now
            last = _STATE["warned_at"]
            if last is None or now - last >= _memo_seconds():
                _STATE["warned_at"] = now
                warn = True
        if warn:
            logger.warning("[LIVE_ROBOTS] memo refresh failed: %s", type(exc).__name__)


def _schedule_refresh() -> None:
    """ONE refresh per loop (single flight), in a fresh contextvars.Context; with
    no running loop (a script, a warmer) nothing is scheduled."""
    global _REFRESH
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    with _LOCK:
        current = _REFRESH
        if current is not None and current[0] is loop and not current[1].done():
            return
        coro = _refresh()
        try:
            task = contextvars.Context().run(loop.create_task, coro)
        except Exception:  # noqa: BLE001
            coro.close()
            return
        _REFRESH = (loop, task)


def row_for_host(host: Any) -> Optional[Dict[str, Any]]:
    """The memo row view of ``host`` (exact, else the longest registry parent host)
    as a deep copy, or None (unknown host, cold memo, or the last good load older
    than MERCHANT_REGISTRY_MAX_STALE_SECONDS). No I/O on the caller: a due refresh
    is scheduled on the running loop, if any. Never raises."""
    try:
        now = _monotonic()
        with _LOCK:
            rows, good_at, loaded_at = _STATE["rows"], _STATE["good_at"], _STATE["loaded_at"]
        row = None
        if rows is not None and good_at is not None and now - good_at <= _max_stale_seconds():
            row = match_row(rows, host)
        if loaded_at is None or now - loaded_at >= _memo_seconds():
            _schedule_refresh()
        return copy.deepcopy(row)
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- counters
_ATTEMPTS_CTX: "contextvars.ContextVar[Optional[Dict[Tuple[str, str, str], int]]]" = (
    contextvars.ContextVar("live_robots_attempts", default=None)
)


def bind_attempts() -> None:
    """Bind a fresh per-compare aggregator (flag ON only; OFF: the env read only)."""
    if not live_robots_enabled():
        return
    _ATTEMPTS_CTX.set({})


def record(source: str, host: Any, outcome: str) -> None:
    """Count one attempt outcome for (source, normalized host). Flag ON only; a
    silent no-op with no bound aggregator (a fetch outside a compare). Never raises."""
    if not live_robots_enabled():
        return
    try:
        if outcome not in OUTCOMES:
            return
        bucket = _ATTEMPTS_CTX.get()
        if not isinstance(bucket, dict):
            return
        key = (str(source), deny_hosts.normalize_host(host) if isinstance(host, str) else "",
               outcome)
        bucket[key] = bucket.get(key, 0) + 1
    except Exception:  # noqa: BLE001
        return


def outcome_of(resp: Any) -> str:
    """ok for a 200; challenge for a ``cf-mitigated: challenge`` response; else fail.
    A response without a status or headers is a fail. Never raises."""
    try:
        status = getattr(resp, "status_code", None)
        if status == 200:
            return "ok"
        headers = getattr(resp, "headers", None)
        mark = None
        if headers is not None and hasattr(headers, "get"):
            mark = headers.get("cf-mitigated")
            if mark is None:
                mark = headers.get("Cf-Mitigated")
        if isinstance(mark, str) and mark.strip().lower() == "challenge":
            return "challenge"
    except Exception:  # noqa: BLE001
        pass
    return "fail"


def record_response(source: str, url: Any, resp: Any) -> None:
    """Count the outcome of one observed response of ``url``. Never raises."""
    try:
        record(source, host_of(url), outcome_of(resp))
    except Exception:  # noqa: BLE001
        return


def record_url(source: str, url: Any, outcome: str) -> None:
    """Count ``outcome`` for the host of ``url`` (no response object). Never raises."""
    try:
        record(source, host_of(url), outcome)
    except Exception:  # noqa: BLE001
        return


# --------------------------------------------------------------------------- the hook
def gate(url: Any, source: str) -> bool:
    """True = fetch. Flag OFF: True after one env read. ON: the persisted verdict of
    the URL; a skip is counted ``robots_skip`` and logged once at INFO with the
    source, the normalized host and the reason (never the path or query). Any
    internal error is a skip (fail-closed); never raises."""
    if not live_robots_enabled():
        return True
    host = ""
    try:
        host = host_of(url)
        reason = url_verdict(url, row_for_host(host), _now())
    except Exception:  # noqa: BLE001 - fail-closed
        reason = "bad_url"
    if reason is None:
        return True
    record(source, host, "robots_skip")
    logger.info("[LIVE_ROBOTS] skip source=%s host=%s reason=%s", source, host or "-", reason)
    return False


# --------------------------------------------------------------------------- the flush
def _flush_sync(counts: Dict[Tuple[str, str, str], int], day: str, ttl: int) -> None:
    """ONE pipeline: HINCRBY per non-zero counter + one EXPIRE per touched key, ONE
    exec. Runs on the redis-offloop pool thread."""
    commands = []
    keys = []
    for (source, host, outcome), n in sorted(counts.items()):
        if not host or not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            continue
        key = _HEALTH_PREFIX + day + ":" + host
        commands.append((key, source + ":" + outcome, n))
        if key not in keys:
            keys.append(key)
    if not commands:
        return
    client = _redis_client()
    if client is None:
        return
    pipe = client.pipeline()
    for key, field, n in commands:
        pipe.hincrby(key, field, n)
    for key in keys:
        pipe.expire(key, ttl)
    # exec on the upstash-redis pipeline; execute on the redis-py pipeline of
    # cache_service's redis:// fallback (F1-3).
    fn = getattr(pipe, "exec", None) or getattr(pipe, "execute")
    fn()


async def _flush_job(counts: Dict[Tuple[str, str, str], int], day: str, ttl: int) -> None:
    try:
        from app.utils import redis_offloop

        await redis_offloop.run_redis_offloop_pool(_flush_sync, counts, day, ttl)
    except Exception as exc:  # noqa: BLE001 - telemetry never reaches the caller
        logger.warning("[LIVE_ROBOTS] health flush failed: %s", type(exc).__name__)


def flush_attempts() -> None:
    """Called from the compare's ``finally``: read and unbind the aggregator and,
    with ENABLE_LIVE_ROBOTS_HEALTH_FLUSH, hand ONE job to the redis-offloop pool
    through async_utils.fire_and_forget (never awaited). Flag OFF: one env read.
    No running loop: dropped with one DEBUG line. Never raises."""
    if not live_robots_enabled():
        return
    try:
        bucket = _ATTEMPTS_CTX.get()
        if bucket is None:
            return
        _ATTEMPTS_CTX.set(None)
        if not bucket or not health_flush_enabled():
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("[LIVE_ROBOTS] health flush dropped: no running loop")
            return
        from app.utils import async_utils

        async_utils.fire_and_forget(
            _flush_job(dict(bucket), _now().strftime("%Y%m%d"), health_ttl_seconds()),
            "live_robots_health_flush",
        )
    except Exception:  # noqa: BLE001
        return


# --------------------------------------------------------------------------- D08 seam
def robots_entry_lookup(host: str) -> Optional[Mapping[str, Any]]:
    """The D08 ROBOTS_ENTRY_LOOKUP reader (R-G1-1): flag OFF None for every host
    (the _no_entry answer, no memo read); ON the memo row's {status, deny, robots,
    challenge} or None."""
    if not live_robots_enabled():
        return None
    row = row_for_host(host)
    if not isinstance(row, dict):
        return None
    return {key: row.get(key) for key in _ENTRY_KEYS}


jsonld_widen.ROBOTS_ENTRY_LOOKUP = robots_entry_lookup
