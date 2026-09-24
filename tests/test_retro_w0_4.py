"""R-W04 retro red tests: W0-4 parse-once offload (ENABLE_PRICE_PARSE_OFFLOAD).

Spec: the retro adversary report for "W0-4 parse-once offload" (verdict DEFECTIVE) plus the
orchestrator's binding rulings. Everything stays under ENABLE_PRICE_PARSE_OFFLOAD (default
OFF, read per call). No new flag.

  W0-4b  fetch cap. Under the flag, ``curl_fetch_html`` truncates the body at
         ``PRICE_FETCH_MAX_BYTES = 3_000_000`` (``resp.text[:max_bytes]``, like
         ``curl_fetch_html_same_site``), and the firecrawl/scrapedo render-leg HTML is
         truncated to the same constant before ``_extract_price_from_html_maybe_offloaded``.
         Flag OFF is byte-identical: a 5 MB body passes through whole.
  W0-4c  the remaining parse sites. Under the flag, fetch_iherb_price, fetch_bolo_price,
         fetch_boutiqaat_price, _try_pharmacy_urls (its extract_jsonld_price soup) and
         url_extraction_service.extract_with_ai each move their pure-sync parse block into
         ONE offload call. Flag OFF keeps the inline code. A source-level AST test forbids
         an ``async def`` in app/services from calling BeautifulSoup /
         extract_price_from_html / extract_jsonld_price outside an offload call; its
         allowlist is EMPTY. That empty allowlist also catches a SIXTH site the reviewer did
         not name: ``StructuredComparisonService._fetch_page_price`` (structured_comparison_
         service.py:3108 at base, zero production callers, a test seam). It is carried as a
         site here ("scs._fetch_page_price") so the guard and the behavioural tests agree.
  W0-4d  a bounded parse pool. A lazily created
         ThreadPoolExecutor(max_workers=PRICE_PARSE_MAX_WORKERS, default 4, clamped 1..16,
         thread_name_prefix='price-parse') plus an asyncio.Semaphore of the same size, used by
         EVERY offloaded parse site instead of the default pool.
  minor  a CPU-bound heartbeat variant (a busy loop that never sleeps, so it holds the GIL)
         bounds the max loop gap, not only a tick count.
  minor  scripts/verify_flag_byte_identity.py gains ``--flags-on`` and ``--compare``. Per the
         ruling those tests live in tests/test_verify_flag_byte_identity.py, not here.

RED-TEST CONTRACT: nothing here imports a symbol the implementation has yet to add. Every red
test drives an EXISTING runtime function and fails on a measured value. The flag is already
read by the three W0-4 sites, so for the W0-4c sites setting it is a no-op today. Tests marked
PIN pass today and must still pass after the change.

TEST CONTRACTS THE IMPLEMENTATION MUST MEET (the only shapes these tests depend on):
  * The offload resolves module globals at CALL time. The stubs patch
    ``price_service.extract_price_from_html`` / ``structured_comparison_service.
    extract_price_from_html`` / ``bs4.BeautifulSoup.__init__``.
  * The AST test treats a call as offloaded when it sits inside the arguments of a call named
    ``to_thread``, ``run_in_executor``, or any name containing "offload" or "parse_pool" (for
    example a ``_run_parse_offloaded(fn, ...)`` or ``_run_in_parse_pool(fn, ...)`` helper), or
    inside a nested sync def whose name is passed to one. A call is flag-OFF-only when it sits
    in the ``else`` of ``if <...parse_offload_enabled()>:``, in the body of
    ``if not <...>:``, or after an ``if <...parse_offload_enabled()>:`` block that always
    returns. A local bound to that call
    (``_off = price_parse_offload_enabled()``) counts too.
  * The lazily created pool is a module-level global (any name) holding a
    ``concurrent.futures.ThreadPoolExecutor`` whose ``_thread_name_prefix`` starts with
    ``price-parse``. The autouse ``_fresh_parse_pool`` fixture resets it by TYPE (never by
    name) so each test sees ``PRICE_PARSE_MAX_WORKERS`` read afresh; a module-level
    ``asyncio.Semaphore`` global with "parse" in its name is reset too. Each test runs its own
    event loop, so the semaphore must not be bound to the first loop that used it (a per-loop
    holder is fine; the prototype keyed it on the running loop).
  * The offloaded parse runs in a copy of the caller's contextvars context (asyncio.to_thread
    does this; a bare loop.run_in_executor does not).
  * The semaphore is acquired BEFORE the job is submitted to the pool.

Zero network: the autouse ``_zero_network`` fixture blocks every non-loopback socket connect and
getaddrinfo, and it replaces ``curl_cffi.requests.get`` (libcurl never reaches the Python socket
layer). Any attempt fails the test.
"""

import ast
import asyncio
import concurrent.futures
import json
import os
import re
import socket
import threading
import time
import types
from pathlib import Path

import bs4
import pytest

from app.services import price_service as ps
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as ues
from app.utils.executor import install_default_executor

FLAG = "ENABLE_PRICE_PARSE_OFFLOAD"
POOL_ENV = "PRICE_PARSE_MAX_WORKERS"
CAP = 3_000_000
BIG_BODY_CHARS = 5_000_000

REPO = Path(__file__).resolve().parent.parent
SERVICES = REPO / "app" / "services"
FIX = Path(__file__).parent / "fixtures"

_PRODUCT_NAME = "Testbrand Aqua EDP 100ml"
_DOMAIN = "example-w04.com"
_URL = "https://example-w04.com/p/1"

_PARSE_SECONDS = 0.30
_TICK_SECONDS = 0.05
_MIN_TICKS_OFF_LOOP = 4  # same bound and rationale as tests/test_price_parse_offload.py

# The CPU-bound variant. The stub is a pure-Python busy loop that never sleeps, so it holds the
# GIL apart from the interpreter's 5 ms switch interval. Run inline it freezes the loop for the
# whole _BUSY_SECONDS. Off the loop, the heartbeat regains the GIL at every switch interval.
# The bound is half the busy time. That is far above the ~32 ms Windows timer floor the reviewer
# measured, and far below the >= 300 ms an inline parse or a GIL-holding C parse produces.
_BUSY_SECONDS = 0.30
_HEARTBEAT_SECONDS = 0.005
_MAX_LOOP_GAP_SECONDS = 0.15


# ---------------------------------------------------------------------------
# Fixtures: zero network, environment, pool reset
# ---------------------------------------------------------------------------

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "", None}


def _host_of(address):
    if isinstance(address, tuple) and address:
        return address[0]
    return address


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback connect / getaddrinfo, and libcurl's entry point."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def guard_connect(self, address):
        host = _host_of(address)
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host not in _LOOPBACK:
            attempts.append(("connect", host))
            raise OSError("R-W04 zero-network guard: blocked connect to %r" % (host,))
        return real_connect(self, address)

    def guard_connect_ex(self, address):
        host = _host_of(address)
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host not in _LOOPBACK:
            attempts.append(("connect_ex", host))
            raise OSError("R-W04 zero-network guard: blocked connect_ex to %r" % (host,))
        return real_connect_ex(self, address)

    def guard_getaddrinfo(host, *args, **kwargs):
        name = host.decode("ascii", "replace") if isinstance(host, bytes) else host
        if name not in _LOOPBACK:
            attempts.append(("getaddrinfo", name))
            raise socket.gaierror("R-W04 zero-network guard: blocked getaddrinfo(%r)" % (name,))
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)

    import curl_cffi.requests as curl_requests

    def curl_guard(*args, **kwargs):
        attempts.append(("curl_cffi.get", args[:1]))
        raise RuntimeError("R-W04 zero-network guard: blocked curl_cffi.requests.get")

    monkeypatch.setattr(curl_requests, "get", curl_guard)
    yield
    assert not attempts, "R-W04 zero-network guard: the test attempted network I/O: %r" % (
        attempts,
    )


@pytest.fixture(autouse=True)
def _w04_env(monkeypatch):
    """Each test opts in to the flag. The environment the extractors depend on is pinned to the
    SHIPPED defaults (see tests/test_price_parse_offload.py for the ENABLE_JSONLD_FIRST
    rationale)."""
    for name in (
        FLAG,
        POOL_ENV,
        "ENABLE_NOT_A_PDP_FILTER",
        "ENABLE_IHERB_PAGE_CURRENCY",
        "ENABLE_EXACT_PRICE_GATE",
        "ENABLE_LLM_PREFLIGHT_BREAKER",
        "ADAPTER_EXECUTOR_MAX_WORKERS",
        "ENABLE_CONVERTED_PROVENANCE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
    yield


def _reset_parse_pools():
    """Drop any lazily created price-parse pool and parse semaphore, by TYPE, never by name."""
    for module in (ps, scs, ues):
        for name, value in list(vars(module).items()):
            if isinstance(value, concurrent.futures.ThreadPoolExecutor) and str(
                getattr(value, "_thread_name_prefix", "")
            ).startswith("price-parse"):
                value.shutdown(wait=False, cancel_futures=True)
                setattr(module, name, None)
            elif isinstance(value, asyncio.Semaphore) and "parse" in name.lower():
                setattr(module, name, None)


@pytest.fixture(autouse=True)
def _fresh_parse_pool():
    _reset_parse_pools()
    yield
    _reset_parse_pools()


# ---------------------------------------------------------------------------
# Loop observation helpers (copied from tests/test_price_parse_offload.py, plus a gap meter)
# ---------------------------------------------------------------------------


async def _measure_loop_ticks(awaitable, tick=_TICK_SECONDS):
    """Run a heartbeat concurrently with ``awaitable``.

    Returns (result, ticks_during, elapsed, loop_thread_ident). An inline parse holds the tick
    count at 0 for its whole duration."""
    ticks = 0
    stop = False

    async def _heartbeat():
        nonlocal ticks
        while not stop:
            await asyncio.sleep(tick)
            ticks += 1

    hb = asyncio.create_task(_heartbeat())
    await asyncio.sleep(0.01)
    before = ticks
    started = time.monotonic()
    result = await awaitable
    elapsed = time.monotonic() - started
    during = ticks - before
    stop = True
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    return result, during, elapsed, threading.get_ident()


async def _measure_max_loop_gap(awaitable, tick=_HEARTBEAT_SECONDS):
    """Run a fast heartbeat concurrently with ``awaitable``.

    Returns (result, max_gap_seconds, elapsed). The gap is the longest interval inside the
    awaited window in which the loop could not run the heartbeat."""
    stamps = []
    stop = False

    async def _heartbeat():
        while not stop:
            stamps.append(time.perf_counter())
            await asyncio.sleep(tick)

    hb = asyncio.create_task(_heartbeat())
    await asyncio.sleep(0.02)
    started = time.perf_counter()
    result = await awaitable
    ended = time.perf_counter()
    stop = True
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    points = sorted([started, ended] + [s for s in stamps if started <= s <= ended])
    gaps = [b - a for a, b in zip(points, points[1:])]
    return result, (max(gaps) if gaps else 0.0), ended - started


def _busy(seconds):
    """Pure-Python CPU work that never sleeps and never releases the GIL voluntarily."""
    end = time.perf_counter() + seconds
    n = 0
    while time.perf_counter() < end:
        n += 1
    return n


def _record_thread(sink):
    """(thread ident, thread name, the resolved-price-category ContextVar as the parse sees it)."""
    sink.append((
        threading.get_ident(),
        threading.current_thread().name,
        ps._resolved_category_ctx.get(),
    ))


def _install_extract_stub(monkeypatch, module, mode="sleep", seconds=_PARSE_SECONDS, sink=None):
    """Replace ``module.extract_price_from_html`` (the parse helper of the three W0-4 sites).

    mode "sleep": time.sleep (releases the GIL). mode "busy": a GIL-holding busy loop. mode
    "instant": no wall time. Returns the list of (thread ident, thread name) per call."""
    calls = [] if sink is None else sink

    def stub(html, product_name, currency, domain, url, **kwargs):
        _record_thread(calls)
        if mode == "sleep":
            time.sleep(seconds)
        elif mode == "busy":
            _busy(seconds)
        return {
            "amount": 45.0,
            "currency": "BHD",
            "retailer": domain,
            "url": url,
            "title": _PRODUCT_NAME,
            "estimated": False,
            "source_method": "page_scrape",
        }

    monkeypatch.setattr(module, "extract_price_from_html", stub)
    return calls


def _install_soup_stub(monkeypatch, mode="sleep", seconds=_PARSE_SECONDS):
    """Wrap every ``BeautifulSoup`` construction (the parse primitive of the W0-4c sites).

    The real constructor still runs after the stall, so the site's result is real. Patching
    ``__init__`` catches every import style (module-level ``from bs4 import BeautifulSoup`` in
    url_extraction_service, and the call-time local imports in price_service)."""
    calls = []
    original = bs4.BeautifulSoup.__init__

    def wrapped(self, *args, **kwargs):
        _record_thread(calls)
        if mode == "sleep":
            time.sleep(seconds)
        elif mode == "busy":
            _busy(seconds)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(bs4.BeautifulSoup, "__init__", wrapped)
    return calls


# ---------------------------------------------------------------------------
# Site table: every async parse site the unit covers, fully stubbed (no network, no budget)
# ---------------------------------------------------------------------------


async def _stub_same_site_fetch(url, domain, **kwargs):
    return "<html><body>stub page for R-W04</body></html>"


def _setup_fetch_page_price(monkeypatch):
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_same_site_fetch)
    return (lambda: ps.fetch_page_price(_URL, _PRODUCT_NAME, "BHD")), ps


def _provider_attempts_sink(monkeypatch):
    rows = []
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: rows.append(kw))
    return rows


def _stub_render_gates(monkeypatch):
    async def _gate_ok(provider):
        return True

    monkeypatch.setattr(scs, "_provider_gate_ok_async", _gate_ok)
    monkeypatch.setattr(scs, "record_usage", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_success", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_failure", lambda *a, **k: None)


def _setup_firecrawl(monkeypatch, html="<html><body>stub page for R-W04</body></html>"):
    async def _scrape(url):
        return html, 200

    monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: True)
    monkeypatch.setattr(scs.firecrawl_service, "scrape_page_with_status", _scrape)
    _stub_render_gates(monkeypatch)
    _provider_attempts_sink(monkeypatch)
    return (lambda: scs._firecrawl_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)), scs


def _setup_scrapedo(monkeypatch, html="<html><body>stub page for R-W04</body></html>"):
    async def _render(url):
        return html, 200, 5

    monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: True)
    monkeypatch.setattr(scs.scrapedo_service, "render_page_with_status", _render)
    monkeypatch.setattr(scs, "validate_scrape_url", lambda url: True)
    _stub_render_gates(monkeypatch)
    _provider_attempts_sink(monkeypatch)
    return (lambda: scs._scrapedo_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)), scs


def _read_fixture(name):
    return (FIX / name).read_text(encoding="utf-8", errors="replace")


def _setup_bolo(monkeypatch):
    html = _read_fixture("bolo_pdp_kensington.html")
    monkeypatch.setattr(
        "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
        lambda domain, query: "https://www.bolo.bh/products/UO0872Z3OMT-kensington-wireless-presenter",
    )

    async def _fetch(url, domain, **kwargs):
        return html

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _fetch)
    return (lambda: ps.fetch_bolo_price("Kensington Wireless Presenter K33272WW", "BHD")), None


def _setup_boutiqaat(monkeypatch):
    html = _read_fixture("boutiqaat_pdp_ghuyoum_edp.html")
    monkeypatch.setattr(
        "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
        lambda domain, query: "https://www.boutiqaat.com/en-bh/women/ghuyoum-alqassar-100ml-edp-i-00000213650-1/p/",
    )

    async def _fetch(url, domain, **kwargs):
        return html

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _fetch)
    return (lambda: ps.fetch_boutiqaat_price("Ghuyoum Alqassar Eau de Parfum 100ml", "BHD")), None


def _setup_iherb(monkeypatch):
    html = _read_fixture("iherb_ga_cards.html")

    class _Resp:
        status_code = 200
        text = html

    import curl_cffi.requests as curl_requests

    monkeypatch.setattr(curl_requests, "get", lambda *a, **k: _Resp())
    return (
        lambda: ps.fetch_iherb_price(
            query="NOW Vitamin D3 5000", brand="NOW Foods",
            full_name="NOW Foods Vitamin D-3 5000 IU 120 Softgels",
            region_code="bh", currency="BHD",
        )
    ), None


_PHARMACY_PAGE = """<html><head>
<script type="application/ld+json">
{"@type": "Product", "name": "HealthAid Vitamin D3 1000iu Tablet Pack of 120",
 "brand": {"@type": "Brand", "name": "HealthAid"},
 "offers": {"@type": "Offer", "price": 9, "priceCurrency": "BHD",
            "availability": "https://schema.org/InStock"}}
</script></head><body><p>HealthAid Vitamin D3</p></body></html>"""


class _FakeHttpxResponse:
    status_code = 200
    text = _PHARMACY_PAGE


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        return _FakeHttpxResponse()


def _setup_pharmacy(monkeypatch):
    monkeypatch.setattr(ps.httpx, "AsyncClient", _FakeAsyncClient)
    return (
        lambda: ps._try_pharmacy_urls(
            [("https://www.example-pharmacy-w04.bh/p/healthaid-d3", "Example Pharmacy")],
            "HealthAid", "BHD",
            full_name="HealthAid Vitamin D3 1000iu Tablet Pack of 120",
        )
    ), None


_AI_PAGE = """<html><head><title>Kensington Wireless Presenter | Store</title>
<script>var x = 1;</script><style>p{}</style></head>
<body><nav>menu</nav><h1>Kensington Wireless Presenter K33272WW</h1>
<p>Price: 24.890 BHD</p><footer>foot</footer></body></html>"""


def _setup_extract_with_ai(monkeypatch):
    class _Msg:
        content = '{"title": "Kensington Wireless Presenter", "price": 24.89, "currency": "BHD"}'

    class _Choice:
        message = _Msg()

    class _Response:
        choices = [_Choice()]

    async def _guarded(client, **kwargs):
        return _Response()

    monkeypatch.setattr(ues, "get_client", lambda: object())
    monkeypatch.setattr(ues, "_llm_breaker", types.SimpleNamespace(guarded_llm_create=_guarded))
    retailer = {"name": "Example", "region": "bahrain", "currency": "BHD", "key": "example"}
    return (lambda: ues.extract_with_ai(_URL, _AI_PAGE, retailer)), None


_BHD_JSONLD_PAGE = """<html><head><title>Testbrand Aqua EDP 100ml</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
"name":"Testbrand Aqua EDP 100ml","brand":{"@type":"Brand","name":"Testbrand"},
"offers":{"@type":"Offer","price":"45.000","priceCurrency":"BHD",
"availability":"https://schema.org/InStock"}}</script>
</head><body><p>45.000 BHD</p></body></html>"""


def _setup_scs_fetch_page_price(monkeypatch):
    """StructuredComparisonService._fetch_page_price: the SIXTH inline parse site. The reviewer
    named five; the ruling's AST guard (empty allowlist) finds this one too. It has ZERO
    production callers in app/ today (a test seam kept "so tests can patch _curl_fetch_html"),
    but it is an async def that runs extract_price_from_html on the loop, so the guard forces it
    into scope. Built the way tests/test_page_scraping.py builds it (no __init__ side effects)."""
    svc = scs.StructuredComparisonService.__new__(scs.StructuredComparisonService)
    svc.total_cost = 0
    svc.api_calls = 0
    svc._shopping_items_cache = {}

    async def _fetch(url):
        return _BHD_JSONLD_PAGE

    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True)
    monkeypatch.setattr(svc, "_curl_fetch_html", _fetch)
    return (lambda: svc._fetch_page_price(_URL, _PRODUCT_NAME, "BHD")), scs


# name -> (setup, parse-helper kind, result check)
_EXISTING_SITES = {
    "fetch_page_price": (_setup_fetch_page_price, lambda r: r and r.get("amount") == 45.0),
    "firecrawl_scraper": (_setup_firecrawl, lambda r: r and r.get("value") == 45.0),
    "scrapedo_scraper": (_setup_scrapedo, lambda r: r and r.get("value") == 45.0),
}
_W04C_SITES = {
    "fetch_bolo_price": (_setup_bolo, lambda r: r and r.get("amount") == pytest.approx(24.89)),
    "fetch_boutiqaat_price": (
        _setup_boutiqaat, lambda r: r and r.get("amount") == pytest.approx(50.43),
    ),
    "fetch_iherb_price": (_setup_iherb, lambda r: r and r.get("amount") == 3.852),
    "_try_pharmacy_urls": (_setup_pharmacy, lambda r: r and r.get("amount") == 9.0),
    "extract_with_ai": (_setup_extract_with_ai, lambda r: r and r.get("price") == 24.89),
    "scs._fetch_page_price": (
        _setup_scs_fetch_page_price, lambda r: r and r.get("amount") == pytest.approx(45.0),
    ),
}
_ALL_SITES = dict(_EXISTING_SITES, **_W04C_SITES)


def _arm_site(monkeypatch, site, mode):
    """Stub the site's dependencies and its parse helper. Returns (make_coro, calls, check)."""
    setup, check = _ALL_SITES[site]
    make_coro, extract_module = setup(monkeypatch)
    if extract_module is not None:
        calls = _install_extract_stub(monkeypatch, extract_module, mode=mode)
    else:
        calls = _install_soup_stub(monkeypatch, mode=mode)
    return make_coro, calls, check


# ===========================================================================
# W0-4c: the remaining parse sites run off the loop under the flag
# ===========================================================================


@pytest.mark.parametrize("site", sorted(_W04C_SITES))
def test_w04c_site_parses_off_the_loop_under_flag(monkeypatch, site):
    """RED today: these five async sites build their soup ON the event loop even with the flag
    on. The CLAUDE.md row says fetch_iherb_price 'already parses inside a run_in_executor
    lambda', but that lambda wraps only curl_requests.get."""
    monkeypatch.setenv(FLAG, "true")
    make_coro, calls, check = _arm_site(monkeypatch, site, mode="sleep")

    result, ticks, elapsed, loop_thread = asyncio.run(_measure_loop_ticks(make_coro()))

    assert check(result), "precondition: the stubbed %s must still produce its result, got %r" % (
        site, result,
    )
    assert calls, "precondition: %s must build at least one soup" % site
    on_loop = [c for c in calls if c[0] == loop_thread]
    assert not on_loop and ticks >= _MIN_TICKS_OFF_LOOP, (
        "W0-4c: %s parsed on the event loop under %s. %d of %d soup constructions ran on the "
        "loop thread, and a %.0f ms heartbeat ticked %d times (expected >= %d) in %.2fs."
        % (site, FLAG, len(on_loop), len(calls), _TICK_SECONDS * 1000, ticks,
           _MIN_TICKS_OFF_LOOP, elapsed)
    )


@pytest.mark.parametrize("site", sorted(_W04C_SITES))
def test_w04c_site_flag_off_parses_inline(monkeypatch, site):
    """PIN (green today and after): flag OFF keeps every soup on the caller's thread."""
    make_coro, calls, check = _arm_site(monkeypatch, site, mode="sleep")

    result, ticks, elapsed, loop_thread = asyncio.run(_measure_loop_ticks(make_coro()))

    assert check(result), "flag-OFF %s must still produce its result, got %r" % (site, result)
    assert calls and all(c[0] == loop_thread for c in calls), (
        "flag OFF must keep %s's parse on the loop thread %r: %r" % (site, loop_thread, calls)
    )
    assert ticks <= 1, "flag-OFF pin: the inline parse must hold the loop (<= 1 tick, got %d)" % (
        ticks,
    )


@pytest.mark.parametrize("site", sorted(_W04C_SITES))
def test_w04c_site_result_identical_flag_on_vs_off(monkeypatch, site):
    """PIN: moving the parse block must not change what the site returns. Real parse, no stall.

    Green today because the flag is a no-op at these sites. After the change it proves that the
    offloaded block returns exactly what the inline one did."""
    setup, check = _ALL_SITES[site]
    make_coro, _ = setup(monkeypatch)
    off = asyncio.run(make_coro())
    monkeypatch.setenv(FLAG, "true")
    on = asyncio.run(make_coro())
    assert check(off), "precondition: flag-OFF %s must produce a result, got %r" % (site, off)
    assert on == off, "%s: flag ON returned %r, flag OFF %r" % (site, on, off)


# ---------------------------------------------------------------------------
# W0-4c: source-level AST guard
# ---------------------------------------------------------------------------

_DIRECT_PARSE_NAMES = frozenset({"BeautifulSoup", "extract_price_from_html", "extract_jsonld_price"})
_FLAG_CALL_RE = re.compile(r"parse_offload_enabled$")


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _is_offload_call(call):
    name = _call_name(call.func)
    low = name.lower()
    if low.endswith("enabled"):
        return False
    return name in ("to_thread", "run_in_executor") or "offload" in low or "parse_pool" in low


def _is_flag_call(node):
    return isinstance(node, ast.Call) and bool(_FLAG_CALL_RE.search(_call_name(node.func)))


def _flag_polarity(test, flag_vars):
    """'on' if the test is true exactly when the flag is on, 'off' for the negation, else None."""
    if _is_flag_call(test) or (isinstance(test, ast.Name) and test.id in flag_vars):
        return "on"
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = _flag_polarity(test.operand, flag_vars)
        if inner == "on":
            return "off"
        if inner == "off":
            return "on"
    return None


def _always_exits(stmts):
    return bool(stmts) and isinstance(stmts[-1], (ast.Return, ast.Raise))


def _inline_parse_calls(fn, parse_names):
    """(lineno, name) of every call to ``parse_names`` inside async def ``fn`` that runs on the
    loop with the flag ON (see the module docstring for the recognised offload shapes)."""
    flag_vars = set()
    offloaded_defs = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and _is_flag_call(node.value):
            flag_vars.update(t.id for t in node.targets if isinstance(t, ast.Name))
        if isinstance(node, ast.Call) and _is_offload_call(node):
            for arg in list(node.args) + [k.value for k in node.keywords]:
                if isinstance(arg, ast.Name):
                    offloaded_defs.add(arg.id)
    hits = []

    def visit_block(stmts, exempt):
        for stmt in stmts:
            visit(stmt, exempt)
            if isinstance(stmt, ast.If) and _always_exits(stmt.body):
                polarity = _flag_polarity(stmt.test, flag_vars)
                if polarity == "on":
                    exempt = True  # everything after `if flag: return ...` is flag-OFF only

    def visit(node, exempt):
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
            return  # scanned on its own / not executed here
        if isinstance(node, ast.FunctionDef):
            if node.name in offloaded_defs:
                return  # its body runs on the worker the offload call hands it to
            visit_block(node.body, exempt)
            return
        if isinstance(node, ast.If):
            polarity = _flag_polarity(node.test, flag_vars)
            visit(node.test, exempt)
            visit_block(node.body, exempt or polarity == "off")
            visit_block(node.orelse, exempt or polarity == "on")
            return
        if isinstance(node, ast.Call):
            if _is_offload_call(node):
                visit(node.func, exempt)
                for arg in list(node.args) + [k.value for k in node.keywords]:
                    if isinstance(arg, ast.Lambda):
                        continue  # the lambda body runs on the worker
                    visit(arg, exempt)
                return
            if _call_name(node.func) in parse_names and not exempt:
                hits.append((node.lineno, _call_name(node.func)))
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                if value and all(isinstance(v, ast.stmt) for v in value):
                    visit_block(value, exempt)
                else:
                    for v in value:
                        if isinstance(v, ast.AST):
                            visit(v, exempt)
            elif isinstance(value, ast.AST):
                visit(value, exempt)

    visit_block(fn.body, False)
    return hits


def _scan_services(parse_names):
    """{(file, 'Class.func' or 'func'): [(lineno, name), ...]} over app/services."""
    found = {}
    for path in sorted(SERVICES.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            hits = _inline_parse_calls(node, parse_names)
            if hits:
                owner = parents.get(node)
                qual = ("%s.%s" % (owner.name, node.name)) if isinstance(owner, ast.ClassDef) else node.name
                found[(path.name, qual)] = hits
    return found


def _transitive_parse_helpers():
    """Every sync function name in app/services that constructs a BeautifulSoup, directly or
    through another such function (a name-level closure, so it is deliberately broad)."""
    calls_by_def = {}
    for path in sorted(SERVICES.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                names = {_call_name(c.func) for c in ast.walk(node) if isinstance(c, ast.Call)}
                calls_by_def.setdefault(node.name, set()).update(n for n in names if n)
    helpers = set(_DIRECT_PARSE_NAMES)
    changed = True
    while changed:
        changed = False
        for name, called in calls_by_def.items():
            if name not in helpers and called & helpers:
                helpers.add(name)
                changed = True
    return frozenset(helpers)


# MUST STAY EMPTY (ruling): no async def in app/services may run a parse on the loop.
_DIRECT_ALLOWLIST = frozenset()

# The transitive scan also reaches url_extraction_service.extract_from_url, which calls
# extract_amazon_data / extract_noon_data / extract_generic_data (each builds a soup) inline.
# The reviewer did not name it and the ruling's scope does not list it, so it is allowlisted
# here and reported to the orchestrator as a scope question. Remove this entry if the
# orchestrator brings it into scope.
_TRANSITIVE_ALLOWLIST = frozenset({("url_extraction_service.py", "extract_from_url")})


def test_w04c_no_async_def_parses_inline_outside_an_offload_call():
    """RED today: the ruling's AST guard (direct names, EMPTY allowlist)."""
    found = {k: v for k, v in _scan_services(_DIRECT_PARSE_NAMES).items() if k not in _DIRECT_ALLOWLIST}
    assert not found, (
        "W0-4c: async defs in app/services still call BeautifulSoup / extract_price_from_html / "
        "extract_jsonld_price on the event loop with %s ON: %s"
        % (FLAG, json.dumps({"%s::%s" % k: v for k, v in sorted(found.items())}))
    )


def test_w04c_no_async_def_reaches_a_soup_helper_inline():
    """RED today: the same guard over the transitive soup-building helpers, so moving only the
    BeautifulSoup line (and leaving _bolo_jsonld_main_price / _bolo_has_jsonld_product inline,
    each of which builds its own soup) cannot pass."""
    found = {
        k: v for k, v in _scan_services(_transitive_parse_helpers()).items()
        if k not in _TRANSITIVE_ALLOWLIST
    }
    assert not found, (
        "W0-4c: async defs still reach a soup-building helper on the event loop with %s ON: %s"
        % (FLAG, json.dumps({"%s::%s" % k: v for k, v in sorted(found.items())}))
    )


def test_w04c_ast_scanner_self_check():
    """PIN: the scanner accepts every legitimate offload shape and flags every inline one, so the
    two guards above cannot pass vacuously."""
    ok_shapes = '''
async def a(h):
    if price_parse_offload_enabled():
        x = await asyncio.to_thread(extract_price_from_html, h)
    else:
        x = extract_price_from_html(h)
async def b(h):
    if _price_parse_offload_enabled():
        return await asyncio.to_thread(extract_price_from_html, h)
    return extract_price_from_html(h)
async def c(h):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, lambda: BeautifulSoup(h, "html.parser"))
async def d(h):
    def _block():
        return BeautifulSoup(h, "html.parser")
    if price_parse_offload_enabled():
        return await _run_parse_offloaded(_block)
    return BeautifulSoup(h, "html.parser")
async def e(h):
    _off = price_parse_offload_enabled()
    if not _off:
        return extract_jsonld_price(h)
    return await _parse_offload(extract_jsonld_price, h)
async def k(h):
    if price_parse_offload_enabled():
        return await _run_in_parse_pool(functools.partial(extract_price_from_html, h))
    return extract_price_from_html(h)
'''
    bad_shapes = '''
async def f(h):
    return BeautifulSoup(h, "html.parser")
async def g(h):
    if price_parse_offload_enabled():
        x = await asyncio.to_thread(extract_price_from_html, h)
    y = extract_jsonld_price(h)
async def i(h):
    def _block():
        return BeautifulSoup(h, "html.parser")
    return _block()
'''
    good = [n for n in ast.parse(ok_shapes).body if isinstance(n, ast.AsyncFunctionDef)]
    bad = [n for n in ast.parse(bad_shapes).body if isinstance(n, ast.AsyncFunctionDef)]
    assert {fn.name: _inline_parse_calls(fn, _DIRECT_PARSE_NAMES) for fn in good} == {
        n: [] for n in "abcdek"
    }
    flagged = {fn.name: bool(_inline_parse_calls(fn, _DIRECT_PARSE_NAMES)) for fn in bad}
    assert flagged == {"f": True, "g": True, "i": True}, flagged
    # And it recognises the two shipped W0-4 sites as compliant.
    shipped = _scan_services(_DIRECT_PARSE_NAMES)
    assert ("price_service.py", "fetch_page_price") not in shipped
    assert ("structured_comparison_service.py", "_extract_price_from_html_maybe_offloaded") not in shipped


# ===========================================================================
# W0-4d: a dedicated, bounded parse pool used by every offloaded site
# ===========================================================================


@pytest.mark.parametrize("site", sorted(_ALL_SITES))
def test_w04d_every_offloaded_parse_runs_on_the_price_parse_pool(monkeypatch, site):
    """RED today: the three shipped sites hand the parse to the shared default executor
    (asyncio.to_thread), whose threads are not 'price-parse-*'; the W0-4c sites parse inline."""
    monkeypatch.setenv(FLAG, "true")
    make_coro, calls, check = _arm_site(monkeypatch, site, mode="instant")

    result = asyncio.run(make_coro())

    assert check(result), "precondition: %s must still produce its result, got %r" % (site, result)
    assert calls, "precondition: %s must run its parse helper" % site
    names = [c[1] for c in calls]
    assert all(n.startswith("price-parse") for n in names), (
        "W0-4d: under %s, %s ran its parse on threads %r; every offloaded parse must run on the "
        "dedicated 'price-parse' pool" % (FLAG, site, names)
    )


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
@pytest.mark.parametrize("site", sorted(_ALL_SITES))
def test_offloaded_parse_sees_the_callers_resolved_category(monkeypatch, site, flag_on):
    """PIN (green today at every site, both flag states): the parse must run in a COPY of the
    caller's context. scs._get_price sets the resolved pair category in a ContextVar
    (price_service._resolved_category_ctx) that the extractors read to pick their identity
    axes. asyncio.to_thread copies the context, which is why the reviewer measured 0/828
    different on the async leg. loop.run_in_executor(pool, fn) does NOT copy it, so the
    reviewer's own W0-4d sketch (run_in_executor(_parse_pool, partial(...))) would silently
    drop the category under the flag and change results. The dedicated pool must be entered
    through contextvars.copy_context().run (or equivalent)."""
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    make_coro, calls, check = _arm_site(monkeypatch, site, mode="instant")

    async def with_category():
        ps.set_resolved_price_category("fragrance")
        return await make_coro()

    result = asyncio.run(with_category())

    assert check(result), "precondition: %s must still produce its result, got %r" % (site, result)
    assert calls, "precondition: %s must run its parse helper" % site
    seen = [c[2] for c in calls]
    assert seen == ["fragrance"] * len(calls), (
        "%s (flag %s): the parse saw the resolved-category ContextVar as %r; it must see the "
        "caller's 'fragrance'" % (site, "ON" if flag_on else "OFF", seen)
    )


def test_w04d_parse_is_not_queued_behind_a_saturated_default_pool(monkeypatch):
    """RED today: with the production default executor (40 workers) saturated by 40 sleeping
    jobs, a flagged fetch_page_price waits for a free default worker before its parse starts."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_same_site_fetch)
    calls = _install_extract_stub(monkeypatch, ps, mode="sleep")
    blocker_seconds = 1.5

    async def scenario():
        loop = asyncio.get_running_loop()
        install_default_executor(loop)  # the app's startup pool: 40 workers, 'qaren-worker'
        blockers = [loop.run_in_executor(None, time.sleep, blocker_seconds) for _ in range(40)]
        await asyncio.sleep(0.1)
        started = time.perf_counter()
        result = await ps.fetch_page_price(_URL, _PRODUCT_NAME, "BHD")
        elapsed = time.perf_counter() - started
        await asyncio.gather(*blockers)
        return result, elapsed

    result, elapsed = asyncio.run(scenario())

    assert result is not None and result.get("amount") == 45.0
    assert len(calls) == 1
    assert elapsed <= 2 * _PARSE_SECONDS, (
        "W0-4d: a flagged fetch_page_price took %.2fs for a %.2fs parse while the default pool "
        "was saturated; the parse queued behind %0.1fs adapter-style jobs instead of running on "
        "its own pool" % (elapsed, _PARSE_SECONDS, blocker_seconds)
    )


def _concurrency_probe(monkeypatch, seconds):
    """Patch the fetch_page_price parse with a stub that tracks how many run at once."""
    state = {"active": 0, "max": 0, "started": 0}
    lock = threading.Lock()

    def stub(html, product_name, currency, domain, url, **kwargs):
        with lock:
            state["active"] += 1
            state["started"] += 1
            state["max"] = max(state["max"], state["active"])
        try:
            time.sleep(seconds)
        finally:
            with lock:
                state["active"] -= 1
        return {"amount": 45.0, "currency": "BHD", "retailer": domain, "url": url,
                "title": _PRODUCT_NAME, "estimated": False, "source_method": "page_scrape"}

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_same_site_fetch)
    monkeypatch.setattr(ps, "extract_price_from_html", stub)
    return state, lock


def _cancelled_awaits_scenario(monkeypatch):
    """Ten flagged fetch_page_price awaits, all cancelled together after 50 ms while their 0.4 s
    parses are running or waiting for a slot (the shape of a price race losing its deadline).
    They are cancelled in ONE synchronous pass rather than by ten separate wait_for timers, so
    the result cannot depend on the order in which ten near-identical timers fire. Returns the
    probe state once every parse that was ever started has finished."""
    monkeypatch.setenv(FLAG, "true")
    state, lock = _concurrency_probe(monkeypatch, seconds=0.4)

    async def scenario():
        tasks = [
            asyncio.ensure_future(
                ps.fetch_page_price("%s?n=%d" % (_URL, i), _PRODUCT_NAME, "BHD")
            )
            for i in range(10)
        ]
        await asyncio.sleep(0.05)
        for t in tasks:
            t.cancel()
        settled = await asyncio.gather(*tasks, return_exceptions=True)
        outcomes = [
            "cancelled" if isinstance(r, asyncio.CancelledError) else "completed:%r" % (r,)
            for r in settled
        ]
        # Let any queued-but-orphaned parse get picked up and finish (4 waves x 0.4 s max).
        deadline = time.perf_counter() + 6.0
        await asyncio.sleep(0.6)
        while time.perf_counter() < deadline:
            with lock:
                if state["active"] == 0:
                    break
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.6)
        with lock:
            quiet = state["active"] == 0
        return outcomes, quiet

    outcomes, quiet = asyncio.run(scenario())
    assert outcomes == ["cancelled"] * 10, "precondition: every await must be cancelled, got %r" % (
        outcomes,
    )
    assert quiet, "precondition: every started parse must have finished before measuring"
    return state


def test_w04d_cancelled_awaits_leave_at_most_pool_size_parses_in_flight(monkeypatch):
    """RED today: every cancelled await leaves its parse running on the default pool, so ten
    timed-out fetches leave ten parses in flight. With the bounded pool at most
    PRICE_PARSE_MAX_WORKERS (default 4) may run."""
    state = _cancelled_awaits_scenario(monkeypatch)
    assert state["max"] <= 4, (
        "W0-4d: after 10 cancelled awaits, %d parses ran at once (%d started); the bounded pool "
        "allows at most PRICE_PARSE_MAX_WORKERS=4" % (state["max"], state["started"])
    )


def test_w04d_cancelled_awaits_waiting_for_a_slot_never_start_their_parse(monkeypatch):
    """RED today: on the shared default pool all ten cancelled awaits start their parse (10
    started) and every one runs to completion as an orphan nobody will read. With the bounded
    parse pool only PRICE_PARSE_MAX_WORKERS of them may ever start: an await cancelled while
    waiting for a slot must never run its parse. (MEASURED on a prototype: this holds with the
    pool alone, because cancelling a run_in_executor await cancels a still-queued executor
    future, and it holds with the semaphore; the semaphore itself is pinned by the
    submission-depth test below.)"""
    state = _cancelled_awaits_scenario(monkeypatch)
    assert state["started"] <= 4, (
        "W0-4d: 10 awaits cancelled after 50 ms still started %d parses; an await cancelled "
        "while waiting for a price-parse slot must never run its parse, so at most "
        "PRICE_PARSE_MAX_WORKERS=4 may start" % state["started"]
    )


def test_w04d_semaphore_bounds_jobs_submitted_to_the_parse_pool(monkeypatch):
    """RED today (no price-parse pool receives anything). The semaphore half of W0-4d: the
    ruling requires an asyncio.Semaphore of the pool's size in FRONT of the pool, so queued
    parses wait in asyncio (cheap, cancellable) instead of piling up inside the executor's work
    queue. Observable, design-agnostic: count jobs submitted to a 'price-parse' executor and
    not yet finished, at every submit. With 20 concurrent flagged parses the semaphore keeps
    that at <= PRICE_PARSE_MAX_WORKERS (4). MEASURED on a prototype: a pool WITHOUT the
    semaphore reaches 20 here (so the test pins the semaphore, not just the pool)."""
    monkeypatch.setenv(FLAG, "true")
    _concurrency_probe(monkeypatch, seconds=0.1)
    depth = {"outstanding": 0, "max": 0, "submitted": 0}
    lock = threading.Lock()
    original_submit = concurrent.futures.ThreadPoolExecutor.submit

    def counting_submit(self, fn, *args, **kwargs):
        if not str(getattr(self, "_thread_name_prefix", "")).startswith("price-parse"):
            return original_submit(self, fn, *args, **kwargs)
        with lock:
            depth["outstanding"] += 1
            depth["submitted"] += 1
            depth["max"] = max(depth["max"], depth["outstanding"])
        future = original_submit(self, fn, *args, **kwargs)

        def _done(_future):
            with lock:
                depth["outstanding"] -= 1

        future.add_done_callback(_done)
        return future

    monkeypatch.setattr(concurrent.futures.ThreadPoolExecutor, "submit", counting_submit)

    async def scenario():
        return await asyncio.gather(*(
            ps.fetch_page_price("%s?n=%d" % (_URL, i), _PRODUCT_NAME, "BHD") for i in range(20)
        ))

    results = asyncio.run(scenario())

    assert all(r and r.get("amount") == 45.0 for r in results), "precondition: all 20 must price"
    assert depth["submitted"] == 20, (
        "W0-4d: under %s the 20 parses must be submitted to the 'price-parse' pool; it received "
        "%d" % (FLAG, depth["submitted"])
    )
    assert depth["max"] <= 4, (
        "W0-4d: %d parse jobs were queued in the price-parse pool at once; the asyncio.Semaphore "
        "in front of it must hold that to PRICE_PARSE_MAX_WORKERS=4" % depth["max"]
    )


@pytest.mark.parametrize(
    "env_value, expected",
    [(None, 4), ("2", 2), (" 3 ", 3), ("0", 1), ("-3", 1), ("99", 16), ("not-a-number", 4),
     ("inf", 4)],
    ids=["unset-4", "2", "padded-3", "0-clamps-to-1", "negative-clamps-to-1", "99-clamps-to-16",
         "junk-defaults-to-4", "inf-defaults-to-4"],
)
def test_w04d_pool_size_follows_env_default_4_clamped_1_to_16(monkeypatch, env_value, expected):
    """RED today: 20 concurrent flagged parses all run at once on the default pool. The pool
    must cap concurrency at PRICE_PARSE_MAX_WORKERS (default 4, clamped 1..16). An unparsable
    value falling back to 4 is this test's reading of 'default 4'; 'inf' falling back to 4 (not
    clamping to 16) applies the session-65d standing rule that a numeric env knob must reject
    non-finite values."""
    monkeypatch.setenv(FLAG, "true")
    if env_value is not None:
        monkeypatch.setenv(POOL_ENV, env_value)
    state, _lock = _concurrency_probe(monkeypatch, seconds=0.25)

    async def scenario():
        return await asyncio.gather(*(
            ps.fetch_page_price("%s?n=%d" % (_URL, i), _PRODUCT_NAME, "BHD") for i in range(20)
        ))

    results = asyncio.run(scenario())

    assert all(r and r.get("amount") == 45.0 for r in results), "precondition: all 20 must price"
    assert state["max"] == expected, (
        "W0-4d: %s=%r ran %d parses at once; expected exactly %d"
        % (POOL_ENV, env_value, state["max"], expected)
    )


def test_w04d_pool_and_semaphore_survive_a_new_event_loop(monkeypatch):
    """PIN (green today): the lazily created semaphore must not bind to the first loop. A
    module-level asyncio.Semaphore reused by a second asyncio.run raises 'is bound to a
    different event loop' as soon as it has to wait. Both runs here are contended (8 parses)."""
    monkeypatch.setenv(FLAG, "true")
    _concurrency_probe(monkeypatch, seconds=0.1)

    async def scenario():
        return await asyncio.gather(*(
            ps.fetch_page_price("%s?n=%d" % (_URL, i), _PRODUCT_NAME, "BHD") for i in range(8)
        ))

    first = asyncio.run(scenario())
    second = asyncio.run(scenario())
    assert all(r and r.get("amount") == 45.0 for r in first + second)


def test_w04d_flag_off_never_creates_the_parse_pool(monkeypatch):
    """PIN (green today): flag OFF the parse stays inline, so no price-parse pool may exist."""
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_same_site_fetch)
    calls = _install_extract_stub(monkeypatch, ps, mode="instant")
    result = asyncio.run(ps.fetch_page_price(_URL, _PRODUCT_NAME, "BHD"))
    assert result and result.get("amount") == 45.0
    assert all(not c[1].startswith("price-parse") for c in calls)
    pools = [
        name for module in (ps, scs, ues) for name, value in vars(module).items()
        if isinstance(value, concurrent.futures.ThreadPoolExecutor)
        and str(getattr(value, "_thread_name_prefix", "")).startswith("price-parse")
    ]
    assert not pools, "flag OFF created a price-parse pool: %r" % pools


# ===========================================================================
# tests_that_prove_nothing: flag-ON result identity on REAL markup (kills mutation M6)
# ===========================================================================


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=True, default=repr))


# CI budget, not a behaviour change (PR #196; a per-test time budget, NOT a #185-class stale-module
# defect). This node runs ~1,300 real extract_price_from_html calls (~125M Python calls, identical in
# count in every suite order measured) and CI runs the whole free tier under --cov=app with a per-test
# --timeout=60. MEASURED:
# 47-52 s alone under coverage on the dev box, and on the CI runner it was cut at 60 s just short of
# the end of the fixture list. The per-test marker overrides the CLI budget for this node only, the
# same way tests/test_retro_w1_1.py marks its end-to-end class; every assertion below is unchanged.
@pytest.mark.timeout(600)
def test_flag_on_extraction_is_identical_over_every_fixture_page(monkeypatch):
    """PIN (green today, must stay green): the existing flag-ON identity test covers ONE
    synthetic EUR page, and the reviewer's mutation M6 (build the shared soup with 'lxml' only
    when the flag is ON) survived the whole of tests/test_price_parse_offload.py. This runs
    extract_price_from_html over every committed HTML fixture (162 files at base, real
    retailer markup), both exact-gate modes and two ask currencies, flag OFF vs flag ON, and
    requires identical results plus an 'html.parser' soup on every construction under the
    flag. MEASURED at base: 648 comparisons, 146 non-None, 0 differing, parsers {'html.parser'}.
    It is also the in-repo stand-in for the reviewer's untracked corpus run (0/1656)."""
    import scripts.verify_flag_byte_identity as harness

    files = sorted(FIX.rglob("*.html"))
    assert len(files) >= 100, "precondition: the fixture corpus shrank to %d pages" % len(files)
    parsers = []
    original = bs4.BeautifulSoup.__init__

    def spy(self, *args, **kwargs):
        if os.environ.get(FLAG) == "true":
            parsers.append(args[1] if len(args) > 1 else kwargs.get("features"))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(bs4.BeautifulSoup, "__init__", spy)
    compared = non_none = 0
    differing = []
    for path in files:
        html = path.read_text(encoding="utf-8", errors="replace")
        query = harness.derive_page_query({"url": "https://x.example/p/" + path.name}, html)
        for gate in ("false", "true"):
            monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
            for currency in ("BHD", "USD"):
                args = (html, query, currency, "x.example", "https://x.example/p/1")
                monkeypatch.setenv(FLAG, "false")
                off = _canonical(ps.extract_price_from_html(*args))
                monkeypatch.setenv(FLAG, "true")
                on = _canonical(ps.extract_price_from_html(*args))
                compared += 1
                non_none += off is not None
                if on != off:
                    differing.append((path.name, gate, currency))

    assert non_none >= 100, "precondition: only %d of %d extractions priced" % (non_none, compared)
    assert not differing, "flag ON changed %d of %d extractions: %r" % (
        len(differing), compared, differing[:10])
    assert parsers and set(parsers) == {"html.parser"}, (
        "under %s every soup must be built with 'html.parser' (mutation M6): %r"
        % (FLAG, sorted(set(map(str, parsers))))
    )


# ===========================================================================
# minor: CPU-bound heartbeat (a GIL-holding parse), bound on the max loop gap
# ===========================================================================


@pytest.mark.parametrize("site", sorted(_ALL_SITES))
def test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag(monkeypatch, site):
    """PIN for the three shipped sites (green today), RED for the five W0-4c sites.

    The existing heartbeat tests stub the parse with time.sleep, which releases the GIL, so
    they prove placement, not loop latency. Here the stub is a pure-Python busy loop that never
    sleeps. The max gap between heartbeats must stay under _MAX_LOOP_GAP_SECONDS. An inline
    parse, or a C-level parse that never releases the GIL, gives a gap of about _BUSY_SECONDS."""
    monkeypatch.setenv(FLAG, "true")
    make_coro, calls, check = _arm_site(monkeypatch, site, mode="busy")

    result, max_gap, elapsed = asyncio.run(_measure_max_loop_gap(make_coro()))

    assert check(result), "precondition: %s must still produce its result, got %r" % (site, result)
    assert calls, "precondition: %s must run its parse helper" % site
    assert elapsed >= _BUSY_SECONDS * 0.8, "precondition: the busy parse must dominate (%.2fs)" % (
        elapsed,
    )
    assert max_gap <= _MAX_LOOP_GAP_SECONDS, (
        "%s: a CPU-bound %.0f ms parse froze the event loop for %.0f ms (bound %.0f ms) under %s"
        % (site, _BUSY_SECONDS * 1000, max_gap * 1000, _MAX_LOOP_GAP_SECONDS * 1000, FLAG)
    )


# ===========================================================================
# W0-4b: the 3 MB fetch cap
# ===========================================================================


class _BigResp:
    def __init__(self, status_code=200, text=None):
        self.status_code = status_code
        self.text = text


def _patch_curl_get(monkeypatch, response):
    import curl_cffi.requests as curl_requests

    seen = []

    def fake_get(url, **kwargs):
        seen.append(url)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(curl_requests, "get", fake_get)
    return seen


def test_w04b_price_fetch_max_bytes_constant_is_3mb():
    """RED today: the constant the ruling names does not exist."""
    assert getattr(ps, "PRICE_FETCH_MAX_BYTES", None) == CAP, (
        "W0-4b: price_service.PRICE_FETCH_MAX_BYTES must be %d, got %r"
        % (CAP, getattr(ps, "PRICE_FETCH_MAX_BYTES", None))
    )


def test_w04b_curl_fetch_html_truncates_at_3mb_under_flag(monkeypatch):
    """RED today: curl_fetch_html returns the whole 5 MB body."""
    monkeypatch.setenv(FLAG, "true")
    body = "a" * BIG_BODY_CHARS
    _patch_curl_get(monkeypatch, _BigResp(200, body))

    html = asyncio.run(ps.curl_fetch_html(_URL))

    assert html is not None and html == body[:CAP], (
        "W0-4b: under %s curl_fetch_html returned %s chars; it must truncate at %d"
        % (FLAG, None if html is None else len(html), CAP)
    )


def test_w04b_curl_fetch_html_flag_off_passes_the_body_through_whole(monkeypatch):
    """PIN (green today and after): flag OFF a 5 MB body comes back untruncated."""
    body = "b" * BIG_BODY_CHARS
    _patch_curl_get(monkeypatch, _BigResp(200, body))
    html = asyncio.run(ps.curl_fetch_html(_URL))
    assert html is not None and len(html) == BIG_BODY_CHARS and html == body


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
def test_w04b_curl_fetch_html_miss_shapes_unchanged(monkeypatch, flag_on):
    """PIN: a non-200 and a raising GET still return None, and a short 200 body is returned
    verbatim, with the flag either way."""
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    _patch_curl_get(monkeypatch, _BigResp(404, "nope"))
    assert asyncio.run(ps.curl_fetch_html(_URL)) is None
    _patch_curl_get(monkeypatch, RuntimeError("boom"))
    assert asyncio.run(ps.curl_fetch_html(_URL)) is None
    _patch_curl_get(monkeypatch, _BigResp(200, "<html>short</html>"))
    assert asyncio.run(ps.curl_fetch_html(_URL)) == "<html>short</html>"


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
def test_w04b_same_site_fetch_cap_unchanged(monkeypatch, flag_on):
    """PIN: curl_fetch_html_same_site already caps at 3_000_000 and keeps doing so."""
    if flag_on:
        monkeypatch.setenv(FLAG, "true")

    async def _valid(url):
        return True

    import app.utils.url_validator as uv

    monkeypatch.setattr(uv, "_validate_url_offloop_or_sync", _valid)
    _patch_curl_get(monkeypatch, _BigResp(200, "c" * BIG_BODY_CHARS))
    html = asyncio.run(ps.curl_fetch_html_same_site(_URL, _DOMAIN))
    assert html is not None and len(html) == CAP


def test_w04b_lazy_backfill_caller_flag_off_scans_the_whole_search_page(monkeypatch):
    """PIN (green today and after), the OTHER curl_fetch_html caller:
    structured_comparison_service._lazy_bh_pdp_backfill curls a retailer SEARCH page and
    regex-scans the whole body for an in-domain /product/ href. Flag OFF that scan must still
    see an href sitting past 3,000,000 chars. (Flag ON the ruling caps curl_fetch_html for every
    caller, so such an href is no longer seen; that consequence is recorded in the red report,
    not asserted here.)"""
    domain = "bahrain.sharafdg.com"
    href = "https://%s/product/testbrand-aqua-edp-100ml/" % domain
    body = "<html><body>" + ("x" * 3_500_000) + '<a href="%s">p</a></body></html>' % href
    _patch_curl_get(monkeypatch, _BigResp(200, body))

    async def _search(query, num_results=5):
        if domain in query:
            return {"organic": [{"link": "https://%s/?s=testbrand" % domain, "title": "search"}]}
        return {"organic": []}

    monkeypatch.setattr(scs, "search_web", _search)
    monkeypatch.setattr(scs, "validate_scrape_url", lambda url: True)
    monkeypatch.setattr(scs, "score_source", lambda link, category: 2.0)

    extra = asyncio.run(scs._lazy_bh_pdp_backfill([], _PRODUCT_NAME, "fragrance"))

    assert [e[0] for e in extra] == [href], extra


_RENDER_SETUPS = {"firecrawl": _setup_firecrawl, "scrapedo": _setup_scrapedo}


def _arm_render_leg(monkeypatch, leg, html):
    make_coro, _module = _RENDER_SETUPS[leg](monkeypatch, html=html)
    attempts = _provider_attempts_sink(monkeypatch)
    seen = []

    def stub(html_in, product_name, currency, domain, url, **kwargs):
        seen.append(len(html_in))
        return {"amount": 45.0, "currency": "BHD", "retailer": domain, "url": url,
                "title": _PRODUCT_NAME, "estimated": False, "source_method": "page_scrape"}

    monkeypatch.setattr(scs, "extract_price_from_html", stub)
    return make_coro, seen, attempts


@pytest.mark.parametrize("leg", sorted(_RENDER_SETUPS))
def test_w04b_render_leg_parse_input_capped_at_3mb_under_flag(monkeypatch, leg):
    """RED today: the render leg hands the whole 5 MB vendor body to the parse."""
    monkeypatch.setenv(FLAG, "true")
    make_coro, seen, _attempts = _arm_render_leg(monkeypatch, leg, "d" * BIG_BODY_CHARS)

    result = asyncio.run(make_coro())

    assert result and result.get("value") == 45.0
    assert seen == [CAP], (
        "W0-4b: under %s the %s leg handed the parse %r chars; it must be capped at %d"
        % (FLAG, leg, seen, CAP)
    )


@pytest.mark.parametrize("leg", sorted(_RENDER_SETUPS))
def test_w04b_render_leg_flag_off_parses_the_whole_body(monkeypatch, leg):
    """PIN (green today and after): flag OFF the parse sees the full 5 MB body."""
    make_coro, seen, _attempts = _arm_render_leg(monkeypatch, leg, "e" * BIG_BODY_CHARS)
    result = asyncio.run(make_coro())
    assert result and result.get("value") == 45.0
    assert seen == [BIG_BODY_CHARS]


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
@pytest.mark.parametrize("leg", sorted(_RENDER_SETUPS))
def test_w04b_render_leg_telemetry_reports_the_raw_body(monkeypatch, leg, flag_on):
    """PIN (green today): the cap bounds only the parse input. The provider-attempt row keeps
    html_kb of the body the vendor actually returned, so the G4 telemetry does not fork when the
    flag flips."""
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    make_coro, _seen, attempts = _arm_render_leg(monkeypatch, leg, "f" * BIG_BODY_CHARS)
    asyncio.run(make_coro())
    assert [a.get("html_kb") for a in attempts] == [BIG_BODY_CHARS // 1024], attempts


# ===========================================================================
# R-W04 fixer: pins for the retro adversary's tests_that_prove_nothing rows.
# test_w04c_site_result_identical_flag_on_vs_off compares only a site's RETURN value, and two
# of its fixtures cannot see a wrong argument inside the flag-ON branch (the extract_with_ai LLM
# stub answers fixed JSON whatever the prompt; the pharmacy page is not one the query-name gate
# decides). The cap pins used one body size (5 MB), and only the value 'true' reached
# url_extraction_service's local flag reader. Each test below closes one of those holes.
# ===========================================================================


def _setup_extract_with_ai_capturing(monkeypatch):
    """_setup_extract_with_ai, plus a list of every prompt the LLM stub receives."""
    make_coro, _module = _setup_extract_with_ai(monkeypatch)
    prompts = []
    answer = ues._llm_breaker.guarded_llm_create

    async def _capturing(client, **kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return await answer(client, **kwargs)

    monkeypatch.setattr(ues, "_llm_breaker", types.SimpleNamespace(guarded_llm_create=_capturing))
    return make_coro, prompts


def test_w04c_extract_with_ai_sends_the_same_prompt_flag_on_vs_off(monkeypatch):
    """PIN: the offloaded block's (title, text) pair must reach the SAME prompt slots as the
    inline block's. The flag-OFF prompt is anchored first: the page <title> sits in the
    'Page Title:' slot and the visible text (nav/footer/script/style stripped) in the content
    slot. Then flag ON must send the byte-identical prompt."""
    make_coro, prompts = _setup_extract_with_ai_capturing(monkeypatch)
    off_result = asyncio.run(make_coro())
    monkeypatch.setenv(FLAG, "true")
    on_result = asyncio.run(make_coro())

    assert off_result == on_result and off_result.get("price") == 24.89
    assert len(prompts) == 2, prompts
    off, on = prompts
    assert (
        "\nPage Title: Kensington Wireless Presenter | Store\n\nPage Content (truncated):\n"
        in off
    ), off
    content = off.split("Page Content (truncated):\n", 1)[1]
    assert content.startswith(
        "Kensington Wireless Presenter | Store\n"
        "Kensington Wireless Presenter K33272WW\nPrice: 24.890 BHD\n"
    ), content[:200]
    assert "menu" not in content and "foot" not in content, content[:200]
    assert on == off, "flag ON sent a different LLM prompt than flag OFF:\nON:  %r\nOFF: %r" % (
        on[:400], off[:400],
    )


# A brand-FIELD-only JSON-LD match whose NAME is an unrelated same-brand product. The S4 gate in
# extract_jsonld_price decides this page: with an empty query_name (pre-S4) the 7 BHD price is
# accepted; with the query name armed it is rejected. So _try_pharmacy_urls returns None only if
# it passes query_name=full_name in the flag state under test.
_PHARMACY_UNRELATED_PAGE = """<html><head>
<script type="application/ld+json">
{"@type": "Product", "name": "Omega-3 Fish Oil Capsules x60",
 "brand": {"@type": "Brand", "name": "HealthAid"},
 "offers": {"@type": "Offer", "price": 7, "priceCurrency": "BHD",
            "availability": "https://schema.org/InStock"}}
</script></head><body><p>Omega-3 Fish Oil</p></body></html>"""
_PHARMACY_QUERY = "HealthAid Vitamin D3 1000iu Tablet Pack of 120"


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
def test_w04c_pharmacy_passes_the_query_name_gate_in_both_flag_states(monkeypatch, flag_on):
    """PIN: _try_pharmacy_urls must arm extract_jsonld_price's query-name gate (B1) with the
    flag in either state, so an unrelated same-brand product on the page is never priced."""
    ungated = ps.extract_jsonld_price(_PHARMACY_UNRELATED_PAGE, "HealthAid", "BHD")
    gated = ps.extract_jsonld_price(
        _PHARMACY_UNRELATED_PAGE, "HealthAid", "BHD", query_name=_PHARMACY_QUERY,
    )
    assert ungated and ungated.get("amount") == 7.0 and gated is None, (
        "precondition: the fixture page must be one the query-name gate decides "
        "(ungated %r, gated %r)" % (ungated, gated)
    )

    class _Resp:
        status_code = 200
        text = _PHARMACY_UNRELATED_PAGE

    class _Client(_FakeAsyncClient):
        async def get(self, url, **kwargs):
            return _Resp()

    monkeypatch.setattr(ps.httpx, "AsyncClient", _Client)
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    result = asyncio.run(ps._try_pharmacy_urls(
        [("https://www.example-pharmacy-w04.bh/p/omega-3", "Example Pharmacy")],
        "HealthAid", "BHD", full_name=_PHARMACY_QUERY,
    ))
    assert result is None, (
        "flag %s: _try_pharmacy_urls priced an unrelated same-brand product %r, so the "
        "query-name gate was not armed" % ("ON" if flag_on else "OFF", result)
    )


_FLAG_READER_VALUES = [
    None, "", "true", "TRUE", " True ", "1", "yes", "YES", "on", " On ",
    "false", "0", "no", "off", "2", "enabled", "truee", "y",
]


@pytest.mark.parametrize(
    "value", _FLAG_READER_VALUES, ids=lambda v: "unset" if v is None else repr(v),
)
def test_w04_the_three_flag_readers_agree(monkeypatch, value):
    """PIN: price_service, structured_comparison_service and url_extraction_service each read
    ENABLE_PRICE_PARSE_OFFLOAD with their own one-liner. All three must accept exactly the same
    values (strip + lower in {'true', '1', 'yes', 'on'}); a reader that drifts would offload one
    site and not another under the same Railway value."""
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    expected = value is not None and value.strip().lower() in ("true", "1", "yes", "on")
    got = {
        "price_service": ps.price_parse_offload_enabled(),
        "structured_comparison_service": scs._price_parse_offload_enabled(),
        "url_extraction_service": ues._price_parse_offload_enabled(),
    }
    assert got == dict.fromkeys(got, expected), (value, got)


@pytest.mark.parametrize("value", ["1", "yes", "on"])
@pytest.mark.parametrize("site", sorted(_W04C_SITES))
def test_w04c_site_offloads_under_every_accepted_flag_value(monkeypatch, site, value):
    """PIN: every W0-4c site honours the non-'true' spellings the readers accept."""
    monkeypatch.setenv(FLAG, value)
    make_coro, calls, check = _arm_site(monkeypatch, site, mode="instant")
    result = asyncio.run(make_coro())
    assert check(result), "precondition: %s must still produce its result, got %r" % (site, result)
    names = [c[1] for c in calls]
    assert names and all(n.startswith("price-parse") for n in names), (site, value, names)


_CAP_BOUNDARY_SIZES = [CAP - 1, CAP, CAP + 1, 3_500_000, 4_110_284]


def _numbered_body(size):
    """A body whose every prefix is distinct, so a wrong slice cannot compare equal."""
    unit = "0123456789abcdef"
    return (unit * (size // len(unit) + 1))[:size]


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
@pytest.mark.parametrize("size", _CAP_BOUNDARY_SIZES)
def test_w04b_curl_fetch_html_cap_boundary(monkeypatch, size, flag_on):
    """PIN: under the flag every body is cut to exactly min(len, 3,000,000), including the
    3-4.1 MB band the real corpus occupies (its largest page is 4,110,284 chars); flag OFF
    every body passes through whole."""
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    body = _numbered_body(size)
    _patch_curl_get(monkeypatch, _BigResp(200, body))
    html = asyncio.run(ps.curl_fetch_html(_URL))
    expected = body[:CAP] if flag_on else body
    assert html is not None and len(html) == len(expected) and html == expected, (
        size, flag_on, None if html is None else len(html),
    )


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
@pytest.mark.parametrize("size", _CAP_BOUNDARY_SIZES)
@pytest.mark.parametrize("leg", sorted(_RENDER_SETUPS))
def test_w04b_render_leg_cap_boundary(monkeypatch, leg, size, flag_on):
    """PIN: the render-leg parse input is min(len, 3,000,000) under the flag and the whole
    body flag OFF, at every size around and above the cap."""
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    make_coro, seen, _attempts = _arm_render_leg(monkeypatch, leg, _numbered_body(size))
    result = asyncio.run(make_coro())
    assert result and result.get("value") == 45.0
    assert seen == [min(size, CAP) if flag_on else size], (leg, size, flag_on, seen)
