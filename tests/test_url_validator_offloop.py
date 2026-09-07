"""W0-1 (SESSION 65) RED tests -- off-loop DNS resolve with a dedicated resolver
pool, a 2s bound and a 60s memo.

P0 LS-REQUEST-PATH-BLOCKING-01: ``app/utils/url_validator.py:30`` calls the
synchronous, untimeoutable libc ``socket.getaddrinfo`` DIRECTLY on the asyncio
event loop, from every unauthenticated ``/api/v1/url/*`` handler and once per
URL / redirect hop on the price path. A black-holed host stalls the WHOLE
single uvicorn worker for the OS resolver timeout (11-12s measured in review).

These tests are written BEFORE the implementation and are expected to be RED.
Each red node fails on an ASSERTION about behaviour observed through the
EXISTING runtime function (``validate_external_url`` / the live
``/api/v1/url/*`` route), never on an ImportError for a symbol that does not
exist yet: the ``_validate_under_flag`` helper below calls
``validate_external_url_async`` only if the module already exposes it, and
otherwise exercises today's sync path.

Contract under ``ENABLE_OFFLOOP_DNS_RESOLVE`` (default OFF, read per call):
  * the resolve runs in a DEDICATED ThreadPoolExecutor named ``dns-resolve``
    (``DNS_RESOLVER_POOL_SIZE``, default 16, clamped to 1..64) -- never the
    shared ``qaren-worker`` pool, because a libc getaddrinfo cannot be
    cancelled and the zombie count must be bounded by this pool alone;
  * it is bounded by ``DNS_RESOLVE_TIMEOUT_SECONDS`` (default 2.0) and fails
    CLOSED (False) on TimeoutError / socket.gaierror, exactly like today's
    gaierror branch;
  * CONFIRMED NEGATIVES ONLY are memoised for 60s (bounded, ~512 entries): a
    gaierror, a private/loopback/link-local/reserved verdict, and a timeout
    whose resolve actually STARTED. A successful public resolve is NEVER
    memoised (a positive memo is a deterministic 60s DNS-rebinding replay
    window on unauthenticated routes) and neither is a timeout whose resolve
    never left the pool queue (that would blacklist a host nobody resolved);
  * with the flag OFF the sync path is byte-identical to today: a direct
    ``socket.getaddrinfo`` on the caller's thread, no pool, no memo.

Every test uses a DISTINCT hostname so the 60s memo of one test can never
satisfy another.
"""
import asyncio
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import app.utils.url_validator as uv

FLAG = "ENABLE_OFFLOOP_DNS_RESOLVE"
_HAS_ASYNC_VALIDATOR = hasattr(uv, "validate_external_url_async")

# A routable public address -- what a successful resolve looks like.
_PUBLIC_ADDRINFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
]


def _stub_getaddrinfo(monkeypatch, delay, calls, thread_names=None, result=None):
    """Replace socket.getaddrinfo with a slow stub.

    ``result is None`` => raise socket.gaierror after ``delay`` (the black-hole
    case). Otherwise return ``result`` after ``delay``.
    """

    def _stub(host, port, *args, **kwargs):
        calls.append(host)
        if thread_names is not None:
            thread_names.append(threading.current_thread().name)
        if delay:
            time.sleep(delay)
        if result is None:
            raise socket.gaierror(-2, "Name or service not known")
        return result

    monkeypatch.setattr(uv.socket, "getaddrinfo", _stub)
    return _stub


async def _validate_under_flag(url):
    """Validate ``url`` through whatever the flag contract puts on the request
    path TODAY: the async form once it exists, else today's sync function.

    This is deliberately NOT a module-level
    ``from app.utils.url_validator import validate_external_url_async`` -- a
    missing symbol must not turn these tests red with an ImportError, only with
    an assertion about measured behaviour.
    """
    fn = getattr(uv, "validate_external_url_async", None)
    if fn is None:
        return uv.validate_external_url(url)
    return await fn(url)


async def _measure_loop_ticks(url, tick=0.01):
    """Run a ``tick``-second heartbeat concurrently with one validation.

    Returns (result, ticks_during_validation, elapsed_seconds). A validator that
    resolves ON the loop pins ticks at 0; an off-loop resolver lets the
    heartbeat keep ticking.
    """
    ticks = 0
    stop = False

    async def _heartbeat():
        nonlocal ticks
        while not stop:
            await asyncio.sleep(tick)
            ticks += 1

    hb = asyncio.create_task(_heartbeat())
    await asyncio.sleep(0.05)  # let the heartbeat actually start ticking
    before = ticks
    started = time.monotonic()
    result = await _validate_under_flag(url)
    elapsed = time.monotonic() - started
    during = ticks - before
    stop = True
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    return result, during, elapsed


# ---------------------------------------------------------------------------
# 1. The event loop must survive a black-holed host (THE P0)
# ---------------------------------------------------------------------------


def test_async_validator_does_not_block_the_loop(monkeypatch):
    """RED today: the request-path validator blocks the loop for the full
    resolver stall (heartbeat ticks == 0) instead of resolving off-loop under a
    2s bound."""
    monkeypatch.setenv(FLAG, "true")
    calls = []
    _stub_getaddrinfo(monkeypatch, 3.0, calls)

    result, ticks, elapsed = asyncio.run(
        _measure_loop_ticks("https://blackhole-w01.example/x")
    )

    # Preconditions -- these pin today's observed behaviour and must hold on
    # both sides of the implementation.
    assert calls == ["blackhole-w01.example"], (
        "precondition: the stubbed resolver must be reached exactly once, "
        f"got {calls!r}"
    )
    assert result is False, "resolve failure must fail CLOSED (False), as today"

    # THE RED ASSERTION. Today the sync getaddrinfo runs on the event loop, so
    # the 10ms heartbeat cannot tick at all for the whole 3s stall.
    # Threshold 50, not 100 (Fable review 2026-09-07): the resolve is bounded
    # at 2.0s and Windows' default ~15.6ms timer granularity yields only ~128
    # ticks in that window; 50 still proves the loop stayed live (today: 0).
    assert ticks >= 50, (
        "P0 LS-REQUEST-PATH-BLOCKING-01: DNS resolve is still ON the event "
        f"loop -- a 10ms heartbeat ticked {ticks} times (expected >=50) while "
        f"the validator held the loop for {elapsed:.2f}s. Every other in-flight "
        "request on this single uvicorn worker was stalled for that whole time."
    )
    assert elapsed < 2.5, (
        "the off-loop resolve must be bounded by DNS_RESOLVE_TIMEOUT_SECONDS "
        f"(default 2.0s), took {elapsed:.2f}s"
    )


@pytest.mark.skipif(
    not _HAS_ASYNC_VALIDATOR,
    reason=(
        "W0-1 not implemented yet: app.utils.url_validator."
        "validate_external_url_async does not exist. The event-loop blocking "
        "itself is asserted through the EXISTING sync validator in "
        "test_async_validator_does_not_block_the_loop (red today)."
    ),
)
def test_async_validator_is_bounded_and_fail_closed(monkeypatch):
    """The async form's own contract: bounded by DNS_RESOLVE_TIMEOUT_SECONDS,
    fail-CLOSED on both TimeoutError and gaierror, private ranges still
    blocked."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("DNS_RESOLVE_TIMEOUT_SECONDS", "0.5")
    fn = uv.validate_external_url_async

    # (a) a stall longer than the bound -> False, within the bound
    calls = []
    _stub_getaddrinfo(monkeypatch, 5.0, calls)
    started = time.monotonic()
    assert asyncio.run(fn("https://bounded-w01.example/x")) is False
    assert time.monotonic() - started < 2.5

    # (b) private range still blocked
    calls2 = []
    _stub_getaddrinfo(
        monkeypatch,
        0,
        calls2,
        result=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )
    assert asyncio.run(fn("http://loopback-w01.example/admin")) is False

    # (c) non-http scheme rejected without ever resolving
    calls3 = []
    _stub_getaddrinfo(monkeypatch, 0, calls3, result=_PUBLIC_ADDRINFO)
    assert asyncio.run(fn("file:///etc/passwd")) is False
    assert calls3 == []


# ---------------------------------------------------------------------------
# 2. Memoisation (both polarities), 60s TTL
# ---------------------------------------------------------------------------


def test_negative_result_is_memoized(monkeypatch):
    """RED today: every call re-resolves. Under the flag the negative result is
    memoised, so two validations of the same host cost ONE getaddrinfo."""
    monkeypatch.setenv(FLAG, "true")
    calls = []
    _stub_getaddrinfo(monkeypatch, 0, calls)
    url = "https://memo-negative-w01.example/x"

    first = asyncio.run(_validate_under_flag(url))
    second = asyncio.run(_validate_under_flag(url))

    assert first is False and second is False, "both calls must fail closed"
    assert len(calls) == 1, (
        "the 60s resolver memo is missing: two validations of the same host "
        f"made {len(calls)} getaddrinfo calls (expected 1). Without it a "
        "black-holed host is re-resolved on every URL and every redirect hop."
    )


def test_positive_result_is_not_memoized(monkeypatch):
    """SECURITY: a successful public resolve must NEVER be memoised.

    The W0-1 spec originally ordered a memo over BOTH polarities. The adversarial
    review measured what the positive half costs
    (``.qa-w0/qa_probes/p3_memo.py``, case ``c2_dns_rebinding``): a host that
    first resolves to ``93.184.216.34`` and then rebinds to the cloud-metadata
    address ``169.254.169.254`` kept validating True for the rest of the 60s
    window --

        flag_on_first(public)                   : true
        flag_on_after_rebind_to_169.254.169.254 : true    <-- SSRF guard bypassed
        flag_off_after_rebind (== base)         : false

    -- so the memo converted the guard's millisecond-wide DNS-rebinding TOCTOU
    into a DETERMINISTIC 60s replay window on the UNAUTHENTICATED
    ``/api/v1/url/*`` front door. The P0 is entirely about the NEGATIVE case (a
    black-holed host re-resolved per URL and per hop), so the positive half buys
    little and costs a security regression. Contract: a public host is
    re-resolved on EVERY call, exactly as base does.
    """
    monkeypatch.setenv(FLAG, "true")
    uv._reset_dns_state_for_tests()
    calls = []
    _stub_getaddrinfo(monkeypatch, 0, calls, result=_PUBLIC_ADDRINFO)
    host = "memo-positive-w01.example"
    url = f"https://{host}/p"

    first = asyncio.run(_validate_under_flag(url))
    second = asyncio.run(_validate_under_flag(url))

    assert first is True and second is True, "a public host must validate True"
    assert len(calls) == 2, (
        "a POSITIVE verdict was memoised: two validations of the same public "
        f"host made {len(calls)} getaddrinfo calls (expected 2 -- every call "
        "must re-resolve, or a rebinding host replays a stale True for 60s)."
    )
    assert uv._memo_get(host) is None, (
        f"the memo must hold CONFIRMED NEGATIVES ONLY, but {host!r} was stored "
        f"as {uv._memo_get(host)!r} after a successful resolve"
    )

    # ...and the measured consequence: a rebinding host must not replay True.
    rebind_host = "rebind-w01.example"
    current = {"ip": "93.184.216.34"}

    def _rebinding(host_arg, port, *args, **kwargs):
        calls.append(host_arg)
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (current["ip"], 0))
        ]

    monkeypatch.setattr(uv.socket, "getaddrinfo", _rebinding)
    assert asyncio.run(_validate_under_flag(f"https://{rebind_host}/x")) is True
    current["ip"] = "169.254.169.254"  # rebind to the cloud-metadata address
    assert asyncio.run(_validate_under_flag(f"https://{rebind_host}/x")) is False, (
        "a host that rebinds to 169.254.169.254 after one good resolve still "
        "validates True -- the positive memo is replaying a stale verdict past "
        "the SSRF guard, on an unauthenticated route. Base re-resolves every "
        "call and returns False here."
    )


def test_queued_but_never_started_resolve_is_not_memoized(monkeypatch):
    """MUST-FIX regression pin: never record a verdict about a host that was
    never resolved.

    ``ThreadPoolExecutor`` QUEUES work past its worker count, but
    ``asyncio.wait_for``'s clock starts at the await -- so a validation that
    never reached a worker still hits the bound. Recording that False in the 60s
    memo blacklists a host NOTHING ever looked up. Measured at the shipped
    defaults (``.qa-w0/qa_probes/p6_realistic_starvation.py``): 4 black-holed
    hosts saturating the pool memoised 8 of 8 unrelated HEALTHY storefronts as
    False, and the price path then served them straight from the poisoned memo
    with no resolve and no fetch -- making flag ON strictly WORSE than flag OFF
    for price capture.

    Contract: a queued-only timeout fails closed for THIS call and writes
    NOTHING, so an immediate retry against a free pool resolves normally.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("DNS_RESOLVE_TIMEOUT_SECONDS", "0.3")
    uv._reset_dns_state_for_tests()

    # A one-worker pool makes "queued past the bound" deterministic instead of
    # load-dependent. monkeypatch restores the module pool afterwards.
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dns-resolve")
    monkeypatch.setattr(uv, "_DNS_POOL", pool)

    blackhole = "queue-blackhole-w01.example"
    healthy = "queue-healthy-w01.example"
    release = threading.Event()
    started = []
    lock = threading.Lock()

    def _stub(host, port, *args, **kwargs):
        with lock:
            started.append(host)
        if host == blackhole:
            release.wait(20.0)
            raise socket.gaierror(-2, "Name or service not known")
        return _PUBLIC_ADDRINFO

    monkeypatch.setattr(uv.socket, "getaddrinfo", _stub)

    async def _drive():
        parked = asyncio.create_task(
            uv.validate_external_url_async(f"https://{blackhole}/x")
        )
        await asyncio.sleep(0.1)  # the single worker is now parked
        queued = await uv.validate_external_url_async(f"https://{healthy}/p")
        snapshot = (list(started), uv._memo_get(healthy))
        release.set()
        await parked
        retry = await uv.validate_external_url_async(f"https://{healthy}/p")
        return queued, snapshot, retry

    try:
        queued, (started_snapshot, memo_snapshot), retry = asyncio.run(_drive())
    finally:
        release.set()
        pool.shutdown(wait=False)

    assert queued is False, "a queued-out validation must still fail CLOSED"
    assert healthy not in started_snapshot, (
        "precondition: the healthy host's resolve must never have reached a "
        f"worker, but the stub recorded {started_snapshot!r}"
    )
    assert memo_snapshot is None, (
        f"the healthy host {healthy!r} was memoised as {memo_snapshot!r} after a "
        "timeout its resolve NEVER STARTED -- that is a 60s blacklist of a host "
        "nothing ever looked up. Only a STARTED timeout (a genuinely slow or "
        "black-holed resolver) may be memoised."
    )
    assert retry is True, (
        "with the pool free again the healthy host must resolve and validate "
        f"True, got {retry!r} (a poisoned memo is still short-circuiting it)"
    )


def test_started_timeout_is_memoized(monkeypatch):
    """The other half of the must-fix: a timeout whose resolve DID start is a
    real signal about a slow / black-holed resolver, and memoising it is the
    P0's win (one resolve instead of one per URL and per redirect hop). It must
    survive the queued-timeout fix."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("DNS_RESOLVE_TIMEOUT_SECONDS", "0.3")
    uv._reset_dns_state_for_tests()
    calls = []
    _stub_getaddrinfo(monkeypatch, 1.0, calls)  # starts, then far outruns the bound
    host = "slow-started-w01.example"
    url = f"https://{host}/x"

    first = asyncio.run(uv.validate_external_url_async(url))
    memoised = uv._memo_get(host)
    second = asyncio.run(uv.validate_external_url_async(url))

    assert first is False and second is False, "both calls must fail CLOSED"
    assert memoised is False, (
        "a STARTED timeout must be memoised -- that is the P0 fix: without it a "
        "black-holed host is re-resolved on every URL and every redirect hop"
    )
    assert calls == [host], (
        "the second validation must be served from the memo without a second "
        f"getaddrinfo, got {calls!r}"
    )


def test_memo_is_bounded_has_a_60s_ttl_and_is_resettable(monkeypatch):
    """Coverage for the three memo invariants the W0-1 red tests never pinned
    (adversarial review, should_fix 4): the 512-entry cap, the 60s TTL, and
    ``_reset_dns_state_for_tests`` (which must clear the memo and must NOT join
    the pool -- an uncancellable getaddrinfo would hang the caller)."""
    # (i) the cap holds under a flood of puts
    uv._reset_dns_state_for_tests()
    for i in range(uv._MEMO_MAX_ENTRIES + 128):
        uv._memo_put(f"cap{i}-w01.example", False)
    assert len(uv._DNS_MEMO) <= uv._MEMO_MAX_ENTRIES, (
        f"memo grew to {len(uv._DNS_MEMO)} entries, cap is "
        f"{uv._MEMO_MAX_ENTRIES}"
    )

    # (ii) the TTL is 60s and an expired entry is dropped on read
    uv._reset_dns_state_for_tests()
    host = "ttl-w01.example"
    uv._memo_put(host, False)
    expiry, result = uv._DNS_MEMO[host]
    assert result is False
    remaining = expiry - time.monotonic()
    assert 55.0 < remaining <= 60.0, f"TTL should be ~60s, got {remaining:.1f}s"
    assert uv._memo_get(host) is False
    uv._DNS_MEMO[host] = (time.monotonic() - 1.0, False)
    assert uv._memo_get(host) is None, "an expired entry must not be served"
    assert host not in uv._DNS_MEMO, "an expired entry must be evicted on read"

    # (iii) the reset helper clears the memo and leaves the pool alive
    monkeypatch.setenv(FLAG, "true")
    pool = uv._dns_pool()
    uv._memo_put("reset-w01.example", False)
    uv._reset_dns_state_for_tests()
    assert uv._DNS_MEMO == {}, "the reset helper must clear the memo"
    assert uv._DNS_POOL is pool, "the reset helper must not replace the pool"
    assert pool._shutdown is False, (
        "the reset helper must NOT shut the pool down: joining a parked, "
        "uncancellable getaddrinfo would hang the caller"
    )


# ---------------------------------------------------------------------------
# 3. The resolve must run in a DEDICATED pool, not the shared one
# ---------------------------------------------------------------------------


def test_resolver_uses_dedicated_pool(monkeypatch):
    """RED today: the resolve runs on the caller's (event-loop) thread. Under
    the flag it must run in a dedicated ``dns-resolve`` pool of 4 workers --
    NOT the shared ``qaren-worker`` executor, because an uncancellable
    getaddrinfo parks its thread for the OS timeout and the zombie count must
    be bounded by this pool alone."""
    monkeypatch.setenv(FLAG, "true")
    calls = []
    thread_names = []
    _stub_getaddrinfo(
        monkeypatch, 0, calls, thread_names=thread_names, result=_PUBLIC_ADDRINFO
    )

    result = asyncio.run(_validate_under_flag("https://pool-probe-w01.example/x"))

    assert result is True, "precondition: the public stub address must validate"
    assert thread_names, "precondition: the stubbed resolver must have been called"

    observed = thread_names[0]
    assert observed.startswith("dns-resolve"), (
        "the DNS resolve did not run in the dedicated resolver pool -- it ran "
        f"on thread {observed!r}. Expected a 'dns-resolve' worker (a "
        "'qaren-worker' name would mean the SHARED adapter/DB pool is being "
        "starved by uncancellable resolves)."
    )

    pool = getattr(uv, "_DNS_POOL", None)
    assert pool is not None, (
        "app.utils.url_validator must expose the module-level dedicated "
        "ThreadPoolExecutor used for the resolve"
    )
    assert getattr(pool, "_thread_name_prefix", "") == "dns-resolve"
    assert pool._max_workers == 16, (
        "DNS_RESOLVER_POOL_SIZE default must be 16, got "
        f"{pool._max_workers}. The ordinary price fan-out runs 10-20 concurrent "
        "validations (one task per candidate URL, two products in parallel), so "
        "a pool of 4 made queue-induced timeouts the NORMAL case."
    )


def test_pool_size_knob_defaults_to_16_and_is_clamped(monkeypatch):
    """``DNS_RESOLVER_POOL_SIZE`` degrades junk/zero/negative to the default and
    CLAMPS everything else to 1..64.

    The clamp is load-bearing: bounding the uncancellable-``getaddrinfo`` zombie
    count is the entire reason this pool is dedicated, and the review measured
    an unclamped ``1000000`` building a million-worker ``ThreadPoolExecutor``
    (``.qa-w0/qa_probes/p4_pool.py`` d3_pool_size_knob).
    """
    cases = [
        (None, 16),
        ("", 16),
        ("0", 16),
        ("-4", 16),
        ("garbage", 16),
        ("4.5", 16),
        ("1", 1),
        ("4", 4),
        ("16", 16),
        ("64", 64),
        ("65", 64),
        ("1000000", 64),
    ]
    for raw, expected in cases:
        if raw is None:
            monkeypatch.delenv("DNS_RESOLVER_POOL_SIZE", raising=False)
        else:
            monkeypatch.setenv("DNS_RESOLVER_POOL_SIZE", raw)
        assert uv._dns_pool_size() == expected, (
            f"DNS_RESOLVER_POOL_SIZE={raw!r} resolved to "
            f"{uv._dns_pool_size()}, expected {expected}"
        )


# ---------------------------------------------------------------------------
# 4. Flag OFF == today, byte-for-byte (this node PASSES today, by design)
# ---------------------------------------------------------------------------


def test_flag_off_sync_path_unchanged(monkeypatch):
    """Flag-OFF pin: ``validate_external_url`` resolves DIRECTLY on the
    caller's thread with no pool and no memo. Green today AND after the
    implementation -- this is the byte-identity guard, not a red."""
    monkeypatch.delenv(FLAG, raising=False)
    assert os.getenv(FLAG) is None
    calls = []
    thread_names = []
    _stub_getaddrinfo(monkeypatch, 0, calls, thread_names=thread_names)
    url = "https://flagoff-w01.example/x"

    caller = threading.current_thread().name
    first = uv.validate_external_url(url)
    second = uv.validate_external_url(url)

    assert first is False and second is False
    assert len(calls) == 2, (
        "flag OFF must NOT memoise -- expected 2 getaddrinfo calls, got "
        f"{len(calls)}"
    )
    assert thread_names == [caller, caller], (
        "flag OFF must resolve on the caller's own thread (no executor), got "
        f"{thread_names!r} from caller {caller!r}"
    )


# ---------------------------------------------------------------------------
# 5. The live route -- the surface the P0 was reported against
# ---------------------------------------------------------------------------


def _drive_url_compare_with_heartbeat(tick=0.01):
    """POST /api/v1/url/compare through the real ASGI app on THIS event loop,
    with a heartbeat task running concurrently on the same loop.

    Returns (status_code, ticks_during_request, max_stall_seconds,
    elapsed_seconds). The STALL (the longest gap between two consecutive
    heartbeat ticks) is the load-bearing number: a request also does framework
    work that legitimately yields, so a raw tick count is noisy, while the
    longest gap isolates exactly how long one caller held the loop.

    A TestClient cannot be used here: it drives the app on its own portal
    thread, so it cannot observe whether the app's event loop was stalled.
    """
    import httpx

    from app.main import app

    async def _run():
        ticks = 0
        stop = False
        max_gap = 0.0

        async def _heartbeat():
            nonlocal ticks, max_gap
            last = time.monotonic()
            while not stop:
                await asyncio.sleep(tick)
                now = time.monotonic()
                max_gap = max(max_gap, now - last)
                last = now
                ticks += 1

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            hb = asyncio.create_task(_heartbeat())
            await asyncio.sleep(0.05)
            before = ticks
            max_gap = 0.0  # ignore start-up jitter; measure the request only
            started = time.monotonic()
            response = await client.post(
                "/api/v1/url/compare",
                json={
                    "url1": "https://route-blackhole-w01.example/a",
                    "url2": "https://route-blackhole-w01.example/b",
                    "region": "bahrain",
                },
            )
            elapsed = time.monotonic() - started
            during = ticks - before
            stop = True
            hb.cancel()
            try:
                await hb
            except asyncio.CancelledError:
                pass
        return response.status_code, during, max_gap, elapsed

    return asyncio.run(_run())


def test_url_routes_use_offloop_validator_under_flag(monkeypatch):
    """RED today: an unauthenticated POST /api/v1/url/compare against a
    black-holed host stalls the event loop for the whole resolver timeout.

    The flag-OFF half is the byte-identity pin (one >=1s stall, today's
    behaviour); the flag-ON half is the red.
    """
    # --- flag OFF: today's behaviour, pinned (this half must stay green) ---
    monkeypatch.delenv(FLAG, raising=False)
    calls_off = []
    _stub_getaddrinfo(monkeypatch, 1.0, calls_off)
    status_off, ticks_off, stall_off, elapsed_off = (
        _drive_url_compare_with_heartbeat()
    )

    assert status_off == 400, (
        "precondition: an unresolvable host must be rejected by the SSRF guard "
        f"with 400, got {status_off}"
    )
    assert calls_off == ["route-blackhole-w01.example"], (
        f"precondition: exactly one resolve on the route path, got {calls_off!r}"
    )
    assert stall_off >= 0.9, (
        "flag-OFF pin: today's route holds the event loop for the whole 1.0s "
        f"resolve, so the heartbeat must show one >=0.9s gap -- got a "
        f"{stall_off:.2f}s stall ({ticks_off} ticks over {elapsed_off:.2f}s)"
    )

    # --- flag ON: the loop must stay responsive (RED today) ---
    monkeypatch.setenv(FLAG, "true")
    calls_on = []
    _stub_getaddrinfo(monkeypatch, 1.0, calls_on)
    status_on, ticks_on, stall_on, elapsed_on = _drive_url_compare_with_heartbeat()

    assert status_on == 400, f"expected 400 under the flag too, got {status_on}"
    assert calls_on == ["route-blackhole-w01.example"], (
        "the or-chain short-circuit must hold under the flag too: url2 is "
        "never validated once url1 is blocked, so exactly one resolve is "
        f"expected on the route path, got {calls_on!r}"
    )
    assert ticks_on > 0, (
        "POST /api/v1/url/compare produced no heartbeat ticks at all under "
        f"{FLAG}=true (request took {elapsed_on:.2f}s)"
    )
    assert stall_on < 0.5, (
        "POST /api/v1/url/compare still resolves DNS on the event loop under "
        f"{FLAG}=true -- one caller stalled the loop for {stall_on:.2f}s "
        f"(expected <0.5s; {ticks_on} heartbeat ticks over {elapsed_on:.2f}s). "
        "This route is unauthenticated, so any caller can stall the single "
        "uvicorn worker."
    )
