"""W0-1 (SESSION 65) RED tests -- the REDIRECT-HOP half of P0
LS-REQUEST-PATH-BLOCKING-01.

``tests/test_url_validator_offloop.py`` pins the validator itself and the
public ``POST /api/v1/url/compare`` route. It does NOT pin the three ``async
def`` bodies that call the SYNCHRONOUS
``app.utils.url_validator.validate_external_url`` inline -- once for the initial
URL and once per redirect hop -- while they own the event loop:

  (A) ``app.services.url_extraction_service.fetch_page``
      (``url_extraction_service.py:101`` initial, ``:111`` every hop) -- the
      URL-extraction path behind the public ``/url/*`` handlers.
  (B) ``app.services.price_service.curl_fetch_html_same_site``
      (``price_service.py:14016`` initial, ``:14037`` every hop; the ``async
      def`` spanning 13984-14059) -- THE PRICE-PATH HALF OF THE P0, reached on
      every same-site PDP fetch.
  (C) ``app.services.shopify_pdp_service._fetch_once`` via the SYNC
      ``_hop_is_allowed`` (``shopify_pdp_service.py:284``), which it calls
      before every request in its redirect loop.

All three validate BEFORE any network call, so a black-holed host is a pure
resolver stall: the single uvicorn worker is frozen for the OS resolver timeout
(11-12 s measured in review) per URL and per hop, with zero bytes on the wire.

Contract under ``ENABLE_OFFLOOP_DNS_RESOLVE`` (default OFF, read per call), per
the W0-1 spec and its binding 2026-09-07 Fable review amendments:
  * (A) and (B) must call ``await _validate_url_offloop_or_sync(url)`` at EVERY
    call site -- the initial URL and each redirect hop;
  * (C) gets an async twin ``shopify_pdp_service._hop_is_allowed_async``, used
    by ``_fetch_once`` under the flag (the sync ``_hop_is_allowed`` is kept for
    any future sync caller);
  * with the flag OFF all three are byte-identical to today.

Shape of every test below, mirroring
``test_url_routes_use_offloop_validator_under_flag`` in the sibling file:
``socket.getaddrinfo`` is stubbed to ``time.sleep(1.0)`` then raise
``socket.gaierror``; the coroutine runs under ``asyncio.run`` with a concurrent
10 ms heartbeat that records the LONGEST GAP between ticks. The gap -- not a raw
tick count -- is the load-bearing number: an async function legitimately yields,
so ticks are noisy, while the longest gap isolates exactly how long ONE caller
held the loop. The flag-OFF half asserts a >=0.9 s gap (today's behaviour: the
byte-identity PIN, GREEN today); the flag-ON half asserts <0.5 s (the RED).

Every test uses a DISTINCT hostname so the 60 s resolver memo of one test can
never satisfy another.
"""
import asyncio
import os
import socket
import threading
import time

import app.services.price_service as price_service
import app.services.shopify_pdp_service as shopify_pdp_service
import app.services.url_extraction_service as url_extraction_service
import app.utils.url_validator as uv

FLAG = "ENABLE_OFFLOOP_DNS_RESOLVE"

# How long the stubbed resolver stalls, and the two gap thresholds derived from
# it. 1.0s (not the 3.0s the sibling file uses for the validator-only test) is
# enough to separate the two thresholds by 2x while keeping six drives cheap.
_STALL_SECONDS = 1.0
_BLOCKING_GAP = 0.9   # flag-OFF pin: the loop MUST be held for ~the full stall
_OFFLOOP_GAP = 0.5    # flag-ON red: the loop must stay live


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


def _run_with_heartbeat(make_coro, tick=0.01):
    """Drive ``make_coro()`` on a fresh event loop with a ``tick``-second
    heartbeat running concurrently on that SAME loop.

    Returns ``(result, ticks_during, max_gap_seconds, elapsed_seconds)``.

    ``max_gap`` -- the longest interval between two consecutive heartbeat ticks
    while the call was in flight -- is exactly how long one caller held the
    loop. The settle sleep after the awaited call is load-bearing: the blocked
    branches under test return WITHOUT awaiting anything, so without it the
    heartbeat would never be rescheduled and the gap spanning the stall would go
    unrecorded. The settle is ~0.05s: two orders below ``_BLOCKING_GAP`` and an
    order below ``_OFFLOOP_GAP``, so it can bias neither threshold.
    """

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

        hb = asyncio.create_task(_heartbeat())
        await asyncio.sleep(0.05)  # let the heartbeat actually start ticking
        before = ticks
        max_gap = 0.0  # ignore start-up jitter; measure the call only
        started = time.monotonic()
        result = await make_coro()
        elapsed = time.monotonic() - started
        await asyncio.sleep(max(tick * 5, 0.05))  # let the gap be RECORDED
        during = ticks - before
        stop = True
        hb.cancel()
        try:
            await hb
        except asyncio.CancelledError:
            pass
        return result, during, max_gap, elapsed

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# (A) url_extraction_service.fetch_page -- :101 initial URL, :111 every hop
# ---------------------------------------------------------------------------


def test_extraction_fetch_page_validates_off_loop_under_flag(monkeypatch):
    """P0 LS-REQUEST-PATH-BLOCKING-01, flag ``ENABLE_OFFLOOP_DNS_RESOLVE``,
    site ``app/services/url_extraction_service.py:101`` (and :111 per hop).

    ``fetch_page`` is ``async def`` and calls the SYNC ``validate_external_url``
    inline before it ever opens an ``httpx.AsyncClient``, so a blocked initial
    URL costs a full resolver stall on the event loop and zero network.

    Flag-OFF half = the byte-identity PIN (green today). Flag-ON half = the RED.
    """
    # --- flag OFF: today's behaviour, pinned (this half must stay green) ---
    monkeypatch.delenv(FLAG, raising=False)
    assert os.getenv(FLAG) is None
    calls_off = []
    _stub_getaddrinfo(monkeypatch, _STALL_SECONDS, calls_off)

    result_off, ticks_off, gap_off, elapsed_off = _run_with_heartbeat(
        lambda: url_extraction_service.fetch_page(
            "https://hop-extract-off-w01.example/p"
        )
    )

    assert result_off is None, (
        "precondition: a blocked initial URL must return None before any "
        f"network call, got {result_off!r}"
    )
    assert calls_off == ["hop-extract-off-w01.example"], (
        "precondition: exactly one resolve for this host on the extraction "
        f"path, got {calls_off!r}"
    )
    assert gap_off >= _BLOCKING_GAP, (
        "flag-OFF pin: today's fetch_page holds the event loop for the whole "
        f"{_STALL_SECONDS:.1f}s resolve, so the heartbeat must show one "
        f">={_BLOCKING_GAP}s gap -- got {gap_off:.2f}s ({ticks_off} ticks over "
        f"{elapsed_off:.2f}s)"
    )

    # --- flag ON: the loop must stay responsive (RED today) ---
    monkeypatch.setenv(FLAG, "true")
    calls_on = []
    _stub_getaddrinfo(monkeypatch, _STALL_SECONDS, calls_on)

    result_on, ticks_on, gap_on, elapsed_on = _run_with_heartbeat(
        lambda: url_extraction_service.fetch_page(
            "https://hop-extract-on-w01.example/p"
        )
    )

    assert result_on is None, (
        "a blocked initial URL must still return None under the flag, got "
        f"{result_on!r}"
    )
    assert gap_on < _OFFLOOP_GAP, (
        "P0 LS-REQUEST-PATH-BLOCKING-01: app/services/url_extraction_service.py"
        f":101 still resolves DNS ON the event loop under {FLAG}=true -- one "
        f"caller stalled the loop for {gap_on:.2f}s (expected <{_OFFLOOP_GAP}s; "
        f"{ticks_on} heartbeat ticks over {elapsed_on:.2f}s). fetch_page must "
        "await _validate_url_offloop_or_sync at the initial URL (:101) and at "
        "every redirect hop (:111)."
    )


# ---------------------------------------------------------------------------
# (B) price_service.curl_fetch_html_same_site -- :14016 initial, :14037 per hop
#     THE PRICE-PATH HALF OF THE P0
# ---------------------------------------------------------------------------


def test_price_same_site_fetch_validates_off_loop_under_flag(monkeypatch):
    """P0 LS-REQUEST-PATH-BLOCKING-01, flag ``ENABLE_OFFLOOP_DNS_RESOLVE``,
    site ``app/services/price_service.py:14016`` (and :14037 per hop).

    ``curl_fetch_html_same_site`` is an ``async def`` (13984-14059) whose first
    statement after the local import is
    ``if not validate_external_url(url) or not _host_on_domain(url, domain)`` --
    a SYNC resolve on the event loop, before ``curl_cffi`` is even imported.
    This is the price-path half of the P0: it runs on every same-site PDP fetch,
    once per URL and once per redirect hop.

    ``domain`` is the URL's own hostname so ``_host_on_domain`` passes and the
    VALIDATOR is unambiguously the thing that blocks.
    """
    # --- flag OFF: today's behaviour, pinned (this half must stay green) ---
    monkeypatch.delenv(FLAG, raising=False)
    assert os.getenv(FLAG) is None
    host_off = "hop-price-off-w01.example"
    calls_off = []
    _stub_getaddrinfo(monkeypatch, _STALL_SECONDS, calls_off)

    result_off, ticks_off, gap_off, elapsed_off = _run_with_heartbeat(
        lambda: price_service.curl_fetch_html_same_site(
            f"https://{host_off}/products/x", host_off
        )
    )

    assert result_off is None, (
        "precondition: a blocked initial URL must return None before curl_cffi "
        f"is imported, got {type(result_off).__name__}"
    )
    assert calls_off == [host_off], (
        f"precondition: exactly one resolve on the price path, got {calls_off!r}"
    )
    assert gap_off >= _BLOCKING_GAP, (
        "flag-OFF pin: today's curl_fetch_html_same_site holds the event loop "
        f"for the whole {_STALL_SECONDS:.1f}s resolve, so the heartbeat must "
        f"show one >={_BLOCKING_GAP}s gap -- got {gap_off:.2f}s ({ticks_off} "
        f"ticks over {elapsed_off:.2f}s)"
    )

    # --- flag ON: the loop must stay responsive (RED today) ---
    monkeypatch.setenv(FLAG, "true")
    host_on = "hop-price-on-w01.example"
    calls_on = []
    _stub_getaddrinfo(monkeypatch, _STALL_SECONDS, calls_on)

    result_on, ticks_on, gap_on, elapsed_on = _run_with_heartbeat(
        lambda: price_service.curl_fetch_html_same_site(
            f"https://{host_on}/products/x", host_on
        )
    )

    assert result_on is None, (
        "a blocked initial URL must still return None under the flag, got "
        f"{type(result_on).__name__}"
    )
    assert gap_on < _OFFLOOP_GAP, (
        "P0 LS-REQUEST-PATH-BLOCKING-01: app/services/price_service.py:14016 "
        f"still resolves DNS ON the event loop under {FLAG}=true -- one caller "
        f"stalled the loop for {gap_on:.2f}s (expected <{_OFFLOOP_GAP}s; "
        f"{ticks_on} heartbeat ticks over {elapsed_on:.2f}s). This is the "
        "PRICE-PATH half of the P0: curl_fetch_html_same_site must await "
        "_validate_url_offloop_or_sync at the initial URL (:14016) and at every "
        "redirect hop (:14037)."
    )


# ---------------------------------------------------------------------------
# (C) shopify_pdp_service._fetch_once -> the SYNC _hop_is_allowed :284
# ---------------------------------------------------------------------------


def test_shopify_fetch_once_validates_off_loop_under_flag(monkeypatch):
    """P0 LS-REQUEST-PATH-BLOCKING-01, flag ``ENABLE_OFFLOOP_DNS_RESOLVE``,
    site ``app/services/shopify_pdp_service.py:284``.

    ``_fetch_once`` is ``async def`` and opens its redirect loop with the SYNC
    ``_hop_is_allowed(current, domain)``, which calls ``validate_external_url``
    -- so the resolve runs on the event loop before ``_await_domain_slot`` and
    before any ``curl_cffi`` request. A blocked hop returns ``(None, None)``.

    ``domain`` is the URL's own hostname so ``_host_on_domain`` passes and the
    VALIDATOR is unambiguously the thing that blocks. Under the flag
    ``_fetch_once`` must use the async twin ``_hop_is_allowed_async``.
    """
    # --- flag OFF: today's behaviour, pinned (this half must stay green) ---
    monkeypatch.delenv(FLAG, raising=False)
    assert os.getenv(FLAG) is None
    host_off = "hop-shopify-off-w01.example"
    calls_off = []
    _stub_getaddrinfo(monkeypatch, _STALL_SECONDS, calls_off)

    result_off, ticks_off, gap_off, elapsed_off = _run_with_heartbeat(
        lambda: shopify_pdp_service._fetch_once(
            f"https://{host_off}/products/x.js", host_off
        )
    )

    assert result_off == (None, None), (
        "precondition: a blocked hop must return (None, None) before any "
        f"request, got {result_off!r}"
    )
    assert calls_off == [host_off], (
        "precondition: exactly one resolve on the shopify hop path, got "
        f"{calls_off!r}"
    )
    assert gap_off >= _BLOCKING_GAP, (
        "flag-OFF pin: today's _hop_is_allowed holds the event loop for the "
        f"whole {_STALL_SECONDS:.1f}s resolve, so the heartbeat must show one "
        f">={_BLOCKING_GAP}s gap -- got {gap_off:.2f}s ({ticks_off} ticks over "
        f"{elapsed_off:.2f}s)"
    )

    # --- flag ON: the loop must stay responsive (RED today) ---
    monkeypatch.setenv(FLAG, "true")
    host_on = "hop-shopify-on-w01.example"
    calls_on = []
    _stub_getaddrinfo(monkeypatch, _STALL_SECONDS, calls_on)

    result_on, ticks_on, gap_on, elapsed_on = _run_with_heartbeat(
        lambda: shopify_pdp_service._fetch_once(
            f"https://{host_on}/products/x.js", host_on
        )
    )

    assert result_on == (None, None), (
        "a blocked hop must still return (None, None) under the flag, got "
        f"{result_on!r}"
    )
    assert gap_on < _OFFLOOP_GAP, (
        "P0 LS-REQUEST-PATH-BLOCKING-01: app/services/shopify_pdp_service.py"
        f":284 still resolves DNS ON the event loop under {FLAG}=true -- one "
        f"caller stalled the loop for {gap_on:.2f}s (expected <{_OFFLOOP_GAP}s; "
        f"{ticks_on} heartbeat ticks over {elapsed_on:.2f}s). _fetch_once must "
        "call the async twin _hop_is_allowed_async under the flag; the sync "
        "_hop_is_allowed at :284 cannot leave the loop."
    )


# ---------------------------------------------------------------------------
# (D) The realistic price-path fan-out -- a black-holed burst must not
#     blacklist healthy storefronts (adversarial-review must-fix, probe p6)
# ---------------------------------------------------------------------------

_PUBLIC_ADDRINFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
]


def test_blackholed_burst_does_not_blacklist_healthy_storefronts(monkeypatch):
    """MUST-FIX regression pin, price-path shape, at the DEFAULT knobs.

    ``price_service.fan_out_price_lookup`` launches ONE validation task per
    candidate URL and the two products run in parallel, so 10-20 concurrent
    validations is the ORDINARY price path, not a burst. With a 4-worker pool
    the review measured (``.qa-w0/qa_probes/p6_realistic_starvation.py``, pool=4
    / timeout=2.0 / ttl=60):

        resolves_actually_started:            blackhole0..3 only
        HEALTHY_HOSTS_WRONGLY_REJECTED:       store0..store7  (8 of 8)
        HEALTHY_HOSTS_MEMOISED_FALSE_FOR_60s: store0..store7  (8 of 8)
        downstream: curl_fetch_html_same_site -> None, resolve_attempted: []

    i.e. four black-holed hosts took every worker, the eight unrelated healthy
    storefronts timed out IN THE QUEUE, and each was blacklisted for 60s -- so
    flag ON was strictly WORSE than flag OFF for price capture (at base every
    healthy host is slow but ultimately resolved and allowed).

    Contract, and what this pins: a pool sized for the real fan-out (default
    16), plus "never memoise a verdict about a host that was never resolved".
    Zero healthy hosts rejected, zero healthy hosts memoised, while the P0's
    own win -- a STARTED timeout memoised so the price path stops re-resolving
    a black hole per URL and per hop -- is preserved.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.delenv("DNS_RESOLVER_POOL_SIZE", raising=False)
    monkeypatch.delenv("DNS_RESOLVE_TIMEOUT_SECONDS", raising=False)
    uv._reset_dns_state_for_tests()

    pool = uv._dns_pool()
    assert pool._max_workers == 16, (
        "precondition: the DEFAULT resolver pool must be 16 workers (the "
        f"ordinary price fan-out is 10-20 concurrent validations), got "
        f"{pool._max_workers}"
    )

    black = [f"burst-blackhole{i}-w01.example" for i in range(4)]
    healthy = [f"burst-store{i}-w01.example" for i in range(8)]
    release = threading.Event()
    started = []
    lock = threading.Lock()

    def _stub(host, port, *args, **kwargs):
        with lock:
            started.append(host)
        if host in black:
            release.wait(30.0)  # released by the test, never a real 12s stall
            raise socket.gaierror(-2, "Name or service not known")
        time.sleep(0.05)  # a healthy cold resolve
        return _PUBLIC_ADDRINFO

    monkeypatch.setattr(uv.socket, "getaddrinfo", _stub)

    async def _fanout():
        hosts = black + healthy
        results = await asyncio.gather(
            *[
                uv.validate_external_url_async(f"https://{h}/products/x")
                for h in hosts
            ]
        )
        return dict(zip(hosts, results))

    try:
        verdicts = asyncio.run(_fanout())
    finally:
        release.set()

    wrongly_rejected = [h for h in healthy if verdicts[h] is not True]
    assert wrongly_rejected == [], (
        f"{len(wrongly_rejected)} of {len(healthy)} HEALTHY storefronts were "
        f"rejected because four black-holed hosts saturated the resolver pool: "
        f"{wrongly_rejected!r}. On the price path that is a capture loss the "
        "flag-OFF code does not have."
    )
    poisoned = [h for h in healthy if uv._memo_get(h) is not None]
    assert poisoned == [], (
        f"HEALTHY storefronts were memoised for 60s after a queue-induced "
        f"timeout their resolve never even started: {poisoned!r}"
    )
    assert all(verdicts[h] is False for h in black), (
        f"the black-holed hosts must still fail CLOSED, got {verdicts!r}"
    )
    assert uv._memo_get(black[0]) is False, (
        "the P0's win must survive: a STARTED timeout is still memoised, so a "
        "black hole is resolved once instead of once per URL and per hop"
    )

    # Downstream, on the real price-path helper: the black-holed host is
    # short-circuited straight from the memo (no fresh resolve -- that is the
    # P0 fix), while a healthy storefront still passes the very gate
    # curl_fetch_html_same_site applies at price_service.py:14016.
    with lock:
        started.clear()
    blocked = asyncio.run(
        price_service.curl_fetch_html_same_site(
            f"https://{black[0]}/products/x", black[0]
        )
    )
    assert blocked is None, (
        f"a black-holed host must be refused before any fetch, got "
        f"{type(blocked).__name__}"
    )
    assert started == [], (
        "the black-holed host must be served from the memo without a fresh "
        f"resolve, got {started!r}"
    )
    assert (
        asyncio.run(
            uv._validate_url_offloop_or_sync(
                f"https://{healthy[0]}/products/x"
            )
        )
        is True
    ), (
        f"the healthy storefront {healthy[0]!r} is still being refused by the "
        "price path's own validation gate after the burst -- a transient "
        "contention event became a 60s blacklist"
    )
