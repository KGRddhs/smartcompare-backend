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
    (``DNS_RESOLVER_POOL_SIZE``, default 4) -- never the shared ``qaren-worker``
    pool, because a libc getaddrinfo cannot be cancelled and the zombie count
    must be bounded by this pool alone;
  * it is bounded by ``DNS_RESOLVE_TIMEOUT_SECONDS`` (default 2.0) and fails
    CLOSED (False) on TimeoutError / socket.gaierror, exactly like today's
    gaierror branch;
  * positive AND negative results are memoised for 60s (bounded, ~512 entries);
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


def test_positive_result_is_memoized(monkeypatch):
    """The memo must cover successful resolves too (the price path validates
    the same host once per redirect hop)."""
    monkeypatch.setenv(FLAG, "true")
    calls = []
    _stub_getaddrinfo(monkeypatch, 0, calls, result=_PUBLIC_ADDRINFO)
    url = "https://memo-positive-w01.example/p"

    first = asyncio.run(_validate_under_flag(url))
    second = asyncio.run(_validate_under_flag(url))

    assert first is True and second is True, "a public host must validate True"
    assert len(calls) == 1, (
        "the 60s resolver memo is missing for POSITIVE results: two "
        f"validations of the same host made {len(calls)} getaddrinfo calls "
        "(expected 1)."
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
    assert pool._max_workers == 4, (
        f"DNS_RESOLVER_POOL_SIZE default must be 4, got {pool._max_workers}"
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
