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
    ``ThreadPoolExecutor`` (``DNS_RESOLVER_POOL_SIZE``, default 16, CLAMPED to
    1..64) under an ``asyncio.wait_for`` bound
    (``DNS_RESOLVE_TIMEOUT_SECONDS``, default 2.0). The pool is deliberately NOT
    ``app.utils.executor``'s shared ``qaren-worker`` pool: a libc
    ``getaddrinfo`` cannot be cancelled, and ``asyncio.wait_for`` cancels only
    the await — the parked thread lives on until the OS gives up. Bounding
    the zombies to THIS pool keeps the adapter / DB offload pool intact.

    The default is 16, not 4: the ordinary price fan-out runs 10-20 CONCURRENT
    validations (``price_service.fan_out_price_lookup`` launches one task per
    candidate URL, and the two products run in parallel), so against a pool of
    4 a queue-induced timeout was the NORMAL case rather than the exceptional
    one. 16 keeps the uncancellable-zombie ceiling small and bounded while
    letting a normal fan-out through. The 1..64 clamp stops an ops typo
    (``DNS_RESOLVER_POOL_SIZE=1000000`` built a million-worker pool) from
    defeating the bounded-zombie design that is the whole reason this pool is
    dedicated.
  * a bounded 60 s memo (``_DNS_MEMO``, ~512 entries) over **CONFIRMED
    NEGATIVES ONLY**, consulted by the async AND the sync validator, so a
    black-holed host is resolved once instead of once per URL and per hop. A
    verdict is memoised for a ``gaierror``, for a private / loopback /
    link-local / reserved address, and for a timeout whose resolve actually
    STARTED and ran for most of the bound. Several verdicts are deliberately
    NEVER memoised:

      - **a successful public resolve.** Memoising it converted the guard's
        millisecond-wide DNS-rebinding TOCTOU into a DETERMINISTIC 60 s replay
        window on the UNAUTHENTICATED ``/api/v1/url/*`` routes: measured, a
        host that first resolved to ``93.184.216.34`` and then rebound to the
        cloud-metadata address ``169.254.169.254`` kept validating True for the
        rest of the window, where the base validator (which re-resolves on
        every call) returns False. The P0 is entirely about the NEGATIVE case
        — a black-holed host re-resolved per URL and per redirect hop — so the
        positive half bought little and cost a security regression. A public
        host is therefore re-resolved on EVERY call, exactly as base does.
      - **a timeout whose resolve never reached a worker.**
        ``ThreadPoolExecutor`` QUEUES work past its worker count, but
        ``asyncio.wait_for`` starts its clock at the await — so a validation
        that never ran would otherwise be recorded as a 60 s NEGATIVE verdict
        about a host nothing ever looked up. Measured at the old defaults, 4
        black-holed hosts saturating the pool blacklisted 8 of 8 unrelated
        HEALTHY storefronts on the price path, making flag ON strictly worse
        than flag OFF for capture. A ``threading.Event`` set by the resolver
        callable tells the two cases apart: the resolve STARTED and the host is
        genuinely slow (memoise — this is the P0's win, and it is kept) versus
        the call merely waited in the queue (fail closed for THIS call, write
        nothing).
      - **W0-1b: a timeout whose resolve started only just before the
        deadline.** ``started`` alone is not proof the host is slow: a job that
        waited in the queue and reached a worker a moment before the caller's
        bound would otherwise be blacklisted after milliseconds of resolving.
        ``_resolve`` records ``time.monotonic()`` when it starts, and a timeout
        is memoised only when that resolve had run for at least
        ``_TIMEOUT_MEMO_RUN_FRACTION`` (0.75) of the bound by the deadline.
      - **W0-1b: a transient ``gaierror``.** Only ``EAI_NONAME`` (and
        ``EAI_NODATA`` where the platform defines it) is a confirmed "no such
        name". ``EAI_AGAIN`` (resolver SERVFAIL / timeout), ``EAI_FAIL``, a
        ``gaierror`` with no errno and every other code fail closed for THIS
        call only and write nothing.

    W0-1b also drops a stale negative: a flag-ON resolve carries a
    done-callback, and when a resolve that outlived its caller's bound finally
    returns an ALLOWED public address, any ``False`` memo for that host is
    removed so the next call re-resolves. It never writes ``True`` (that is the
    rebinding window above).
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

_DEFAULT_POOL_SIZE = 16
_MIN_POOL_SIZE = 1
_MAX_POOL_SIZE = 64
_DEFAULT_RESOLVE_TIMEOUT_SECONDS = 2.0
_MEMO_TTL_SECONDS = 60.0
_MEMO_MAX_ENTRIES = 512

# The dedicated resolver pool, built lazily on the first flag-ON resolve so the
# flag-OFF process never creates a thread it does not use.
_DNS_POOL: Optional[ThreadPoolExecutor] = None
_DNS_POOL_LOCK = threading.Lock()

# hostname -> (monotonic expiry, result). CONFIRMED NEGATIVES ONLY (see the
# module docstring: a positive memo is a 60 s DNS-rebinding replay window, and
# a queued-but-never-started timeout is a verdict about a host nobody
# resolved). Guarded by its own lock: it is read and written from the event
# loop AND from resolver-pool threads.
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
    default 16). Read once, when the pool is built.

    Junk / empty / zero / negative degrade to the default; every other value is
    CLAMPED to ``1..64``. The clamp is load-bearing, not cosmetic: bounding the
    uncancellable-``getaddrinfo`` zombie count is the entire reason this pool is
    dedicated, and an unclamped ``1000000`` built a million-worker pool. The
    default is 16 because the ordinary price fan-out runs 10-20 concurrent
    validations, so a pool of 4 made queue-induced timeouts the normal case
    rather than the exceptional one.
    """
    try:
        value = int(os.getenv("DNS_RESOLVER_POOL_SIZE", ""))
    except (TypeError, ValueError):
        return _DEFAULT_POOL_SIZE
    if value <= 0:
        return _DEFAULT_POOL_SIZE
    return max(_MIN_POOL_SIZE, min(value, _MAX_POOL_SIZE))


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
    """Memoise ``result`` for ``hostname`` for 60 s, keeping the memo bounded.

    Callers only ever pass ``False``: the memo holds CONFIRMED NEGATIVES ONLY
    (see the module docstring). The ``result`` parameter is kept so the store
    stays a verdict cache rather than a set, and so any future caller has to
    state the polarity it is writing.
    """
    now = time.monotonic()
    with _DNS_MEMO_LOCK:
        if len(_DNS_MEMO) >= _MEMO_MAX_ENTRIES:
            for host in [h for h, (exp, _r) in _DNS_MEMO.items() if exp <= now]:
                _DNS_MEMO.pop(host, None)
            while len(_DNS_MEMO) >= _MEMO_MAX_ENTRIES:
                oldest = min(_DNS_MEMO.items(), key=lambda kv: kv[1][0])[0]
                _DNS_MEMO.pop(oldest, None)
        _DNS_MEMO[hostname] = (now + _MEMO_TTL_SECONDS, result)


# W0-1b: a STARTED resolve must have run for at least this fraction of the
# bound, by the caller's deadline, before its timeout is memoised as a black
# hole. Anything less is queue contention, not a slow host.
_TIMEOUT_MEMO_RUN_FRACTION = 0.75


def _gaierror_is_confirmed_negative(exc: BaseException) -> bool:
    """W0-1b: True only for a definitive "no such name" resolver answer.

    ``EAI_NONAME`` (and ``EAI_NODATA`` where the platform defines it) is the
    resolver saying the name does not exist: a confirmed negative, worth the
    60 s memo. ``EAI_AGAIN`` (SERVFAIL / resolver timeout), ``EAI_FAIL``, a
    ``gaierror`` with no errno and every other code are transient or unknown:
    they fail CLOSED for the current call only and write nothing, so one
    resolver hiccup cannot take a storefront off the price path for a minute.

    The constants are read from ``socket`` at CALL time because they are
    platform values: ``EAI_NONAME`` is -2 on Linux (CI, prod) and 11001 on
    Windows, where ``EAI_NODATA`` has the same value.
    """
    errno = getattr(exc, "errno", None)
    if errno is None:
        return False
    confirmed = {
        code
        for code in (
            getattr(socket, "EAI_NONAME", None),
            getattr(socket, "EAI_NODATA", None),
        )
        if code is not None
    }
    return errno in confirmed


def _clear_negative_if_resolved_public(fut, hostname: str) -> None:
    """W0-1b done-callback on a flag-ON resolve's concurrent future.

    When a resolve that outlived its caller's bound (a zombie) finally returns
    an ALLOWED public address, a ``False`` memo for ``hostname`` is contradicted
    by the resolver itself, so it is DROPPED and the next call re-resolves.
    An EMPTY answer is not proof the host resolves (``_addr_infos_allowed([])``
    is vacuously True), so it drops nothing. Nothing is ever written: a
    ``True`` memo is the 60 s DNS-rebinding replay window the module docstring
    forbids. Runs on a resolver-pool thread (or on the loop, when re-invoked
    after a late memo write) and never raises.
    """
    try:
        if fut.cancelled() or fut.exception() is not None:
            return
        with _DNS_MEMO_LOCK:
            entry = _DNS_MEMO.get(hostname)
        if entry is None or entry[1] is not False:
            return
        addr_infos = fut.result()
        if not addr_infos or not _addr_infos_allowed(addr_infos, hostname):
            return
        with _DNS_MEMO_LOCK:
            current = _DNS_MEMO.get(hostname)
            if current is not None and current[1] is False:
                _DNS_MEMO.pop(hostname, None)
    except Exception:  # noqa: BLE001 - a pool callback must never raise
        logger.debug(
            "[SSRF] resolve done-callback failed for hostname: %s",
            hostname,
            exc_info=True,
        )


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

    The memo is CONFIRMED NEGATIVES ONLY, in both validators. A successful
    public resolve is never memoised and is re-resolved on every call: a
    positive memo turns the guard's millisecond-wide DNS-rebinding TOCTOU into
    a deterministic 60 s replay window (measured: a host that rebound to
    ``169.254.169.254`` after one good resolve kept validating True, where base
    returns False), on routes that are UNAUTHENTICATED. The P0 is about the
    negative case only, so the positive half is not worth that.
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
        except socket.gaierror as exc:
            logger.warning(f"[SSRF] Could not resolve hostname: {hostname}")
            # W0-1b: only a confirmed NXDOMAIN is memoised; EAI_AGAIN and
            # friends fail closed for THIS call only.
            if memoise and _gaierror_is_confirmed_negative(exc):
                _memo_put(hostname, False)
            return False

        allowed = _addr_infos_allowed(addr_infos, hostname)
        # CONFIRMED NEGATIVES ONLY: a public resolve is re-run every call so a
        # rebinding host cannot replay a stale True for 60 s.
        if memoise and not allowed:
            _memo_put(hostname, False)
        return allowed
    except Exception as e:
        logger.warning(f"[SSRF] URL validation error: {e}")
        return False


async def validate_external_url_async(url: str) -> bool:
    """Off-loop twin of :func:`validate_external_url` (W0-1, P0
    LS-REQUEST-PATH-BLOCKING-01).

    Identical parse / scheme / private-range logic; the resolve runs in the
    dedicated ``dns-resolve`` pool under a ``DNS_RESOLVE_TIMEOUT_SECONDS`` bound
    (default 2.0). A timeout and a ``gaierror`` both fail CLOSED (False),
    exactly like today's gaierror branch.

    The 60 s memo covers CONFIRMED NEGATIVES ONLY, and this function reads and
    writes it ONLY when ``ENABLE_OFFLOOP_DNS_RESOLVE`` is on, so a future direct
    caller cannot get memo semantics with the flag OFF. Two verdicts are never
    written:

      * **a successful public resolve** — memoising it converts the guard's
        millisecond-wide DNS-rebinding TOCTOU into a deterministic 60 s replay
        window on the UNAUTHENTICATED ``/api/v1/url/*`` routes (measured: a
        host that rebound from ``93.184.216.34`` to the cloud-metadata address
        ``169.254.169.254`` kept validating True, where base returns False).
        The P0 is entirely about the negative case, so the positive half buys
        little and costs a security regression.
      * **a timeout whose resolve never STARTED, or started too late** —
        ``ThreadPoolExecutor`` queues work past its worker count while
        ``wait_for``'s clock starts at the await, so a queued-only call would
        otherwise blacklist a host nothing ever looked up (measured: 4
        black-holed hosts poisoned 8 of 8 healthy storefronts). W0-1b: the
        start time recorded inside ``_resolve`` distinguishes a genuinely slow
        resolver (ran >= 0.75 of the bound: memoise — the P0's win) from queue
        contention (fail closed for THIS call only).
      * **W0-1b: a transient gaierror** — only ``EAI_NONAME`` /
        ``EAI_NODATA`` is memoised.

    W0-1b: a flag-ON resolve also carries a done-callback that drops a
    ``False`` memo for the host once a zombie resolve returns an allowed public
    address (it never writes ``True``).

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

        # One flag read per call, mirroring the sync validator: the memo is
        # touched ONLY under the flag, so a future direct caller cannot get
        # memo semantics with ENABLE_OFFLOOP_DNS_RESOLVE off.
        memoise = offloop_dns_enabled()
        if memoise:
            memoised = _memo_get(hostname)
            if memoised is not None:
                return memoised

        timeout = _dns_resolve_timeout()
        loop = asyncio.get_running_loop()

        # ``started_at`` gets time.monotonic() the moment a pool worker picks
        # the job up (W0-1b). A ThreadPoolExecutor QUEUES work past its worker
        # count but wait_for's clock starts at the await, so without this a
        # validation that never ran -- or that reached a worker just before
        # the deadline -- would be memoised as a 60 s negative verdict about a
        # host nobody really resolved. ``socket.getaddrinfo`` is looked up at
        # CALL time so tests that monkeypatch it still take effect.
        started_at: List[float] = []

        def _resolve():
            started_at.append(time.monotonic())
            return socket.getaddrinfo(hostname, None)

        # Submitted directly rather than through loop.run_in_executor so the
        # CONCURRENT future is in hand for the W0-1b done-callback; wrap_future
        # + wait_for still cancel a job that is only queued, exactly as
        # run_in_executor did (run_in_executor is submit + wrap_future).
        cfut = _dns_pool().submit(_resolve)
        if memoise:
            cfut.add_done_callback(
                lambda f: _clear_negative_if_resolved_public(f, hostname)
            )
        deadline = time.monotonic() + timeout
        try:
            addr_infos = await asyncio.wait_for(
                asyncio.wrap_future(cfut, loop=loop),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            ran = (deadline - started_at[0]) if started_at else None
            if ran is not None and ran >= _TIMEOUT_MEMO_RUN_FRACTION * timeout:
                # The resolver really is slow / black-holed: this is the P0's
                # win, so memoise it and stop re-resolving per URL and per hop.
                logger.warning(
                    "[SSRF] DNS resolve exceeded %.1fs for hostname: %s",
                    timeout,
                    hostname,
                )
                if memoise:
                    _memo_put(hostname, False)
                    # The zombie may have returned a public address between
                    # the deadline and the write above, before this entry
                    # existed for its callback to drop.
                    if cfut.done():
                        _clear_negative_if_resolved_public(cfut, hostname)
            elif ran is not None:
                # W0-1b: it started, but only just before the deadline -- it
                # spent the bound queued behind a saturated pool. Queue
                # contention is not a verdict about the host: fail closed
                # for THIS call, record nothing.
                logger.warning(
                    "[SSRF] DNS resolve started only %.2fs before the %.1fs "
                    "bound for hostname: %s (resolver pool saturated; not "
                    "memoised)",
                    max(ran, 0.0),
                    timeout,
                    hostname,
                )
            else:
                # Queued behind a saturated pool and never started: fail closed
                # for THIS call, but record NOTHING — we know nothing about
                # this host, and a 60 s blacklist here takes healthy
                # storefronts off the price path.
                logger.warning(
                    "[SSRF] DNS resolve queued past the %.1fs bound without "
                    "starting for hostname: %s (resolver pool saturated; not "
                    "memoised)",
                    timeout,
                    hostname,
                )
            return False
        except socket.gaierror as exc:
            logger.warning(f"[SSRF] Could not resolve hostname: {hostname}")
            # W0-1b: only a confirmed NXDOMAIN is memoised.
            if memoise and _gaierror_is_confirmed_negative(exc):
                _memo_put(hostname, False)
            return False

        allowed = _addr_infos_allowed(addr_infos, hostname)
        # CONFIRMED NEGATIVES ONLY — see the docstring: a positive memo is a
        # deterministic 60 s DNS-rebinding replay window.
        if memoise and not allowed:
            _memo_put(hostname, False)
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
