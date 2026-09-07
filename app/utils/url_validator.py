"""SSRF protection — validate external URLs before fetching.

W0-1 / P0 ``LS-REQUEST-PATH-BLOCKING-01`` (SESSION 65 full review): the resolve
below is a synchronous, **untimeoutable** libc ``socket.getaddrinfo``. Every
unauthenticated ``/api/v1/url/*`` handler, the URL-extraction path and the price
path call it from inside ``async def`` bodies — once per URL and once per
redirect hop — so a black-holed host freezes the single uvicorn worker for the
whole OS resolver timeout (11-12 s measured), with zero bytes on the wire.

``ENABLE_OFFLOOP_DNS_RESOLVE`` (default OFF, read PER CALL via ``os.getenv`` so
a Railway flip needs no restart) adds:

  * :func:`validate_external_url_async` — the same parse / scheme / private-range
    logic, but the resolve runs in a **dedicated** ``dns-resolve``
    ``ThreadPoolExecutor`` (``DNS_RESOLVER_POOL_SIZE``, default 4) under an
    ``asyncio.wait_for`` bound (``DNS_RESOLVE_TIMEOUT_SECONDS``, default 2.0).
    The pool is deliberately NOT ``app.utils.executor``'s shared
    ``qaren-worker`` pool: a libc ``getaddrinfo`` cannot be cancelled, and
    ``asyncio.wait_for`` cancels only the await — the parked thread lives on
    until the OS gives up. Bounding the zombies to THIS pool keeps the adapter /
    DB offload pool intact.
  * a bounded 60 s memo (``_DNS_MEMO``, ~512 entries) over BOTH positive and
    negative results, consulted by the async AND the sync validator, so a
    black-holed host is resolved once instead of once per URL and per hop.
  * :func:`_validate_url_offloop_or_sync` — the one helper every ``async def``
    call site uses, so with the flag OFF nothing changes.

Fail-CLOSED is preserved on every rung: a timeout, a ``gaierror``, a private /
loopback / link-local / reserved address, a non-http(s) scheme or any unexpected
exception all return ``False``.

**Flag OFF is byte-identical**: :func:`validate_external_url` takes the same
branches, calls ``socket.getaddrinfo`` directly on the caller's own thread,
never touches the pool and never reads or writes the memo;
``_validate_url_offloop_or_sync`` is an ``async def`` whose OFF branch contains
no ``await``, so awaiting it runs the sync validator to completion with no new
suspension point (the ``app.utils.db_offload.run_db`` idiom).
"""
import asyncio
import ipaddress
import logging
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_FLAG = "ENABLE_OFFLOOP_DNS_RESOLVE"

_DEFAULT_POOL_SIZE = 4
_DEFAULT_RESOLVE_TIMEOUT_SECONDS = 2.0
_MEMO_TTL_SECONDS = 60.0
_MEMO_MAX_ENTRIES = 512

# The dedicated resolver pool, built lazily on the first flag-ON resolve so the
# flag-OFF process never creates a thread it does not use.
_DNS_POOL: Optional[ThreadPoolExecutor] = None
_DNS_POOL_LOCK = threading.Lock()

# hostname -> (monotonic expiry, result). Guarded by its own lock: it is read
# and written from the event loop AND from resolver-pool threads.
_DNS_MEMO: Dict[str, Tuple[float, bool]] = {}
_DNS_MEMO_LOCK = threading.Lock()


def offloop_dns_enabled() -> bool:
    """True iff ``ENABLE_OFFLOOP_DNS_RESOLVE`` is on. Read per call (the
    ``price_service.exact_gate_enabled`` idiom) — never cached at import, so a
    Railway flip takes effect without a restart. Default OFF."""
    return os.getenv(_FLAG, "").strip().lower() in ("true", "1", "yes", "on")


def _dns_resolve_timeout() -> float:
    """The wall-clock bound on one off-loop resolve (``DNS_RESOLVE_TIMEOUT_SECONDS``,
    default 2.0). A junk or non-positive value degrades to the default."""
    try:
        value = float(os.getenv("DNS_RESOLVE_TIMEOUT_SECONDS", ""))
    except (TypeError, ValueError):
        return _DEFAULT_RESOLVE_TIMEOUT_SECONDS
    return value if value > 0 else _DEFAULT_RESOLVE_TIMEOUT_SECONDS


def _dns_pool_size() -> int:
    """Worker count for the dedicated resolver pool (``DNS_RESOLVER_POOL_SIZE``,
    default 4). Read once, when the pool is built."""
    try:
        value = int(os.getenv("DNS_RESOLVER_POOL_SIZE", ""))
    except (TypeError, ValueError):
        return _DEFAULT_POOL_SIZE
    return value if value > 0 else _DEFAULT_POOL_SIZE


def _dns_pool() -> ThreadPoolExecutor:
    """The module-level dedicated resolver pool, built on first use."""
    global _DNS_POOL
    pool = _DNS_POOL
    if pool is not None:
        return pool
    with _DNS_POOL_LOCK:
        if _DNS_POOL is None:
            size = _dns_pool_size()
            _DNS_POOL = ThreadPoolExecutor(
                max_workers=size, thread_name_prefix="dns-resolve"
            )
            logger.info(
                "[SSRF] dedicated DNS resolver pool created: max_workers=%d", size
            )
        return _DNS_POOL


def _memo_get(hostname: str) -> Optional[bool]:
    """The memoised verdict for ``hostname``, or None when absent/expired."""
    now = time.monotonic()
    with _DNS_MEMO_LOCK:
        entry = _DNS_MEMO.get(hostname)
        if entry is None:
            return None
        expiry, result = entry
        if expiry <= now:
            _DNS_MEMO.pop(hostname, None)
            return None
        return result


def _memo_put(hostname: str, result: bool) -> None:
    """Memoise ``result`` for ``hostname`` for 60 s, keeping the memo bounded."""
    now = time.monotonic()
    with _DNS_MEMO_LOCK:
        if len(_DNS_MEMO) >= _MEMO_MAX_ENTRIES:
            for host in [h for h, (exp, _r) in _DNS_MEMO.items() if exp <= now]:
                _DNS_MEMO.pop(host, None)
            while len(_DNS_MEMO) >= _MEMO_MAX_ENTRIES:
                oldest = min(_DNS_MEMO.items(), key=lambda kv: kv[1][0])[0]
                _DNS_MEMO.pop(oldest, None)
        _DNS_MEMO[hostname] = (now + _MEMO_TTL_SECONDS, result)


def _reset_dns_state_for_tests() -> None:
    """Drop the resolver memo. Deliberately does NOT shut the pool down — a
    ``getaddrinfo`` parked in a worker thread cannot be cancelled, so joining it
    would hang the caller."""
    with _DNS_MEMO_LOCK:
        _DNS_MEMO.clear()


def _addr_infos_allowed(addr_infos: List, hostname: str) -> bool:
    """The private/reserved-range half of the guard, shared by both validators.
    Pure: no resolution, no logging beyond the existing block warning."""
    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            logger.warning(f"[SSRF] Blocked private/reserved IP {ip} for host {hostname}")
            return False

    return True


def validate_external_url(url: str) -> bool:
    """Validate that a URL is safe to fetch (no SSRF).

    Rejects private IPs, localhost, link-local, cloud metadata,
    and non-http(s) schemes. Resolves hostname to check actual IP.

    Returns True if safe, False if blocked.

    The resolve is SYNCHRONOUS and blocks the calling thread — with
    ``ENABLE_OFFLOOP_DNS_RESOLVE`` OFF this is byte-identical to the pre-W0-1
    function; with it ON the 60 s memo short-circuits repeat hosts, but an
    ``async def`` caller must use :func:`_validate_url_offloop_or_sync` instead
    (P0 LS-REQUEST-PATH-BLOCKING-01).
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"[SSRF] Blocked non-http scheme: {parsed.scheme}")
            return False

        hostname = parsed.hostname
        if not hostname:
            logger.warning("[SSRF] Blocked URL with no hostname")
            return False

        # One flag read per call (not one per memo touch) so a mid-call flip
        # cannot half-apply: OFF => no memo read, no memo write, nothing but
        # today's direct resolve.
        memoise = offloop_dns_enabled()
        if memoise:
            memoised = _memo_get(hostname)
            if memoised is not None:
                return memoised

        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            logger.warning(f"[SSRF] Could not resolve hostname: {hostname}")
            if memoise:
                _memo_put(hostname, False)
            return False

        allowed = _addr_infos_allowed(addr_infos, hostname)
        if memoise:
            _memo_put(hostname, allowed)
        return allowed
    except Exception as e:
        logger.warning(f"[SSRF] URL validation error: {e}")
        return False


async def validate_external_url_async(url: str) -> bool:
    """Off-loop twin of :func:`validate_external_url` (W0-1, P0
    LS-REQUEST-PATH-BLOCKING-01).

    Identical parse / scheme / private-range logic; the resolve runs in the
    dedicated ``dns-resolve`` pool under a ``DNS_RESOLVE_TIMEOUT_SECONDS`` bound
    (default 2.0) and is memoised for 60 s in both polarities. A timeout and a
    ``gaierror`` both fail CLOSED (False), exactly like today's gaierror branch.

    Only reached under ``ENABLE_OFFLOOP_DNS_RESOLVE``; callers go through
    :func:`_validate_url_offloop_or_sync`.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"[SSRF] Blocked non-http scheme: {parsed.scheme}")
            return False

        hostname = parsed.hostname
        if not hostname:
            logger.warning("[SSRF] Blocked URL with no hostname")
            return False

        memoised = _memo_get(hostname)
        if memoised is not None:
            return memoised

        timeout = _dns_resolve_timeout()
        loop = asyncio.get_running_loop()
        try:
            addr_infos = await asyncio.wait_for(
                loop.run_in_executor(
                    _dns_pool(), socket.getaddrinfo, hostname, None
                ),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning(
                "[SSRF] DNS resolve exceeded %.1fs for hostname: %s", timeout, hostname
            )
            _memo_put(hostname, False)
            return False
        except socket.gaierror:
            logger.warning(f"[SSRF] Could not resolve hostname: {hostname}")
            _memo_put(hostname, False)
            return False

        allowed = _addr_infos_allowed(addr_infos, hostname)
        _memo_put(hostname, allowed)
        return allowed
    except Exception as e:
        logger.warning(f"[SSRF] URL validation error: {e}")
        return False


async def _validate_url_offloop_or_sync(url: str) -> bool:
    """The single entry point for every ``async def`` call site.

    Flag ON  -> :func:`validate_external_url_async` (dedicated pool, 2 s bound,
    60 s memo). Flag OFF -> the sync :func:`validate_external_url`, called
    INLINE: this branch contains no ``await``, so awaiting this coroutine runs
    the sync validator to completion with no new suspension point and no
    scheduling change — byte-identical to the direct call it replaced.
    """
    if offloop_dns_enabled():
        return await validate_external_url_async(url)
    return validate_external_url(url)
