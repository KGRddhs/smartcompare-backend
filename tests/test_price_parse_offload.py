"""W0-4 red tests - parse once, off the loop (LS-CONCURRENCY-LIMITS-01 + CR-PERFORMANCE-01).

Two defects, one flag (``ENABLE_PRICE_PARSE_OFFLOAD``, default OFF, read nowhere today):

1. **Parse count.** ``price_service.extract_price_from_html`` (:12987) builds its own
   ``BeautifulSoup`` at :13056 and then calls ``extract_jsonld_price`` (:10598) up to three
   times (:13092 target currency, :13097 USD retry, :13112 the M13-40 accept-any-currency
   pass), and EACH of those re-parses the same bytes at :10642. On the shipped default
   (``ENABLE_JSONLD_FIRST`` ON) a page whose JSON-LD Offer is denominated in neither the ask
   currency nor USD therefore pays for FOUR full html.parser passes over the same document -
   MEASURED here, not assumed (see ``_EUR_JSONLD_PAGE``).

2. **Where the parse runs.** Every async caller invokes that pure-sync, CPU-bound parse
   INLINE on the event loop: ``price_service.fetch_page_price`` (:14090) and
   ``structured_comparison_service._firecrawl_scraper`` (:1643) / ``_scrapedo_scraper``
   (:1722). On the single uvicorn worker one page parse stalls every other in-flight request
   for its whole duration.

The flag is expected to make (a) ``extract_price_from_html`` parse ONCE and pass the soup into
``extract_jsonld_price(..., soup=...)``, and (b) the async call sites wrap the parse in
``await asyncio.to_thread(...)``. Flag OFF must stay byte-identical: four soups, inline call.

RED-TEST CONTRACT (why these fail on an assertion, never an ImportError): nothing in this file
imports a symbol the implementation has yet to add. Setting ``ENABLE_PRICE_PARSE_OFFLOAD`` is a
no-op today - no code reads it - so every "under flag" test exercises the EXISTING runtime
function and fails on the measured number (4 soups, 0 heartbeat ticks, the loop thread's own
ident). The flag-OFF tests are pins: they are expected to pass today AND after the change.

VERSION LABELLING (local pip is OFF-LOCK): local ``beautifulsoup4 4.14.3`` vs the pinned
``beautifulsoup4==4.15.0``. The only shape these tests depend on is ``BeautifulSoup.__init__``
being an instance method on the class (patchable, one call per construction); that was verified
by reading the PINNED wheel (``pip download beautifulsoup4==4.15.0 --no-deps -d .qa-w0/wheels``
-> ``bs4/__init__.py``: ``class BeautifulSoup(Tag):`` / ``def __init__(``), recorded in
``.qa-w0/_bs4_pinned_shape.txt``. No claim here rests on the local build.
"""

import asyncio
import os
import sys
import threading
import time

import bs4
import pytest

from app.services import price_service as ps
from app.services import structured_comparison_service as scs

FLAG = "ENABLE_PRICE_PARSE_OFFLOAD"

# A page whose JSON-LD Offer is EUR while the ask is BHD. This is the shape that walks all
# three extract_jsonld_price passes (target -> USD -> M13-40 accept-any), i.e. the full
# four-soup cost, and it still returns a real converted price so the count is measured on a
# SUCCESSFUL capture rather than on a dead page.
_EUR_JSONLD_PAGE = """<html><head><title>Testbrand Aqua EDP 100ml</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
"name":"Testbrand Aqua EDP 100ml","brand":{"@type":"Brand","name":"Testbrand"},
"offers":{"@type":"Offer","price":"45.00","priceCurrency":"EUR",
"availability":"https://schema.org/InStock"}}</script>
</head><body><p>45,00 EUR</p></body></html>"""

_PRODUCT_NAME = "Testbrand Aqua EDP 100ml"
_DOMAIN = "example-w04.com"
_URL = "https://example-w04.com/p/1"

# MEASURED at base (2026-09-07, this worktree, origin/main 67e9e26 == 76ace90):
# extract_price_from_html over _EUR_JSONLD_PAGE constructs BeautifulSoup 4 times -
# price_service.py:13056 once, price_service.py:10642 three times (from :13092/:13097/:13112).
_BASE_SOUPS = 4

# The unit's own target: one parse per extraction.
_TARGET_SOUPS = 1

# The sleeping-parse stub's duration, and the heartbeat interval used to observe the loop.
_PARSE_SECONDS = 0.30
_TICK_SECONDS = 0.05
# 0.30s / 0.05s = 6 ticks in the ideal case; 4 leaves headroom for Windows' ~15.6ms timer
# granularity (same threshold rationale as W0-1's Fable-reviewed tick bound). Today: 0.
_MIN_TICKS_OFF_LOOP = 4


@pytest.fixture(autouse=True)
def _w04_env_sandbox(monkeypatch):
    """Pin the environment this unit's behaviour depends on.

    * ``ENABLE_PRICE_PARSE_OFFLOAD`` removed by default - each test opts in.
    * ``ENABLE_JSONLD_FIRST`` forced to its SHIPPED DEFAULT (ON). It is default-ON in code, but
      it also gates the third ``extract_jsonld_price`` pass, so the base soup count would be 3
      instead of 4 if an ambient ``.env`` turned it off. Forcing it makes the measurement
      independent of the developer's environment.
    * ``ENABLE_NOT_A_PDP_FILTER`` removed - ON it can classify this synthetic page as
      not-a-PDP and return before the cascade ever runs.
    """
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    yield


def _install_soup_counter(monkeypatch):
    """Count every ``BeautifulSoup`` construction; return the list of caller ``file:line``."""
    calls = []
    original = bs4.BeautifulSoup.__init__

    def counting_init(self, *args, **kwargs):
        frame = sys._getframe(1)
        calls.append(
            "%s:%d" % (os.path.basename(frame.f_code.co_filename), frame.f_lineno)
        )
        return original(self, *args, **kwargs)

    monkeypatch.setattr(bs4.BeautifulSoup, "__init__", counting_init)
    return calls


def _install_sleeping_parse(monkeypatch, module):
    """Replace ``module.extract_price_from_html`` with a 300ms sleeping stub.

    Returns the list of thread idents the stub ran on. The stub stands in for the real
    CPU-bound parse: what matters is that it is a pure-sync callable that takes wall time, so
    an inline call holds the loop and an ``asyncio.to_thread`` call does not.

    NOTE for the implementer: this patches the MODULE GLOBAL, so the offload must resolve the
    name at call time (``await asyncio.to_thread(extract_price_from_html, ...)``), not capture
    a private alias at import.
    """
    threads = []

    def sleeping_parse(html, product_name, currency, domain, url, **kwargs):
        threads.append(threading.get_ident())
        time.sleep(_PARSE_SECONDS)
        return {
            "amount": 45.0,
            "currency": "BHD",
            "retailer": domain,
            "url": url,
            "title": _PRODUCT_NAME,
            "estimated": False,
            "source_method": "page_scrape",
        }

    monkeypatch.setattr(module, "extract_price_from_html", sleeping_parse)
    return threads


async def _measure_loop_ticks(awaitable, tick=_TICK_SECONDS):
    """Run a ``tick``-second heartbeat concurrently with ``awaitable``.

    Returns (result, ticks_during, elapsed_seconds, loop_thread_ident). A parse that runs ON
    the loop pins ticks at 0 for its whole duration; an off-loop parse lets the heartbeat run.
    """
    ticks = 0
    stop = False

    async def _heartbeat():
        nonlocal ticks
        while not stop:
            await asyncio.sleep(tick)
            ticks += 1

    hb = asyncio.create_task(_heartbeat())
    await asyncio.sleep(0.01)  # let the heartbeat actually enter its first sleep
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


async def _stub_fetch_html(url, domain, **kwargs):
    """Stand in for ``curl_fetch_html_same_site`` - returns bytes, costs no wall time."""
    return "<html><body>stub page for W0-4</body></html>"


async def _stub_firecrawl_scrape(url):
    return "<html><body>stub page for W0-4</body></html>", 200


async def _stub_scrapedo_render(url):
    """Stand in for ``scrapedo_service.render_page_with_status``.

    Shape matched to the REAL call at structured_comparison_service.py:1692 -
    ``html, status, cost = await scrapedo_service.render_page_with_status(url)`` - a
    THREE-tuple (the firecrawl leg unpacks two). ``cost`` must be > 0 so the leg takes
    the billed branch (``record_usage("scrapedo", count=cost)``), which is the shipped
    path for a 200.
    """
    return "<html><body>stub page for W0-4</body></html>", 200, 5


# ---------------------------------------------------------------------------
# 1. Parse once (CR-PERFORMANCE-01)
# ---------------------------------------------------------------------------


def test_extract_price_from_html_parses_once_under_flag(monkeypatch):
    """RED today: one extraction builds FOUR BeautifulSoup trees over the same bytes."""
    monkeypatch.setenv(FLAG, "true")
    soups = _install_soup_counter(monkeypatch)

    price = ps.extract_price_from_html(
        _EUR_JSONLD_PAGE, _PRODUCT_NAME, "BHD", _DOMAIN, _URL,
    )

    # Preconditions - the fixture must exercise the full three-pass JSON-LD ladder and still
    # capture, so the count below is the cost of a SUCCESSFUL extraction, not of a dead page.
    assert price is not None and price.get("amount"), (
        "precondition: the EUR JSON-LD fixture must still yield a price, got %r" % (price,)
    )
    assert price["original_currency"] == "EUR", (
        "precondition: the M13-40 accept-any-currency pass must be the one that captured "
        "(that is what walks all three extract_jsonld_price calls), got %r"
        % (price.get("original_currency"),)
    )

    # THE RED ASSERTION.
    assert len(soups) == _TARGET_SOUPS, (
        "CR-PERFORMANCE-01: extract_price_from_html parsed the same %d-byte document %d "
        "times (expected %d under %s). Parses: %s"
        % (len(_EUR_JSONLD_PAGE), len(soups), _TARGET_SOUPS, FLAG, soups)
    )


def test_flag_off_four_soups_and_inline(monkeypatch):
    """PIN (green today and after the implementation): flag OFF is byte-identical - four
    soups, and the parse runs on the CALLER's thread."""
    soups = _install_soup_counter(monkeypatch)
    price = ps.extract_price_from_html(
        _EUR_JSONLD_PAGE, _PRODUCT_NAME, "BHD", _DOMAIN, _URL,
    )
    assert price is not None and price.get("amount") == pytest.approx(18.45, abs=0.5)
    assert len(soups) == _BASE_SOUPS, (
        "flag OFF must keep today's parse count exactly (%d): got %d - %s"
        % (_BASE_SOUPS, len(soups), soups)
    )

    # The async half of the same pin: with the flag off, fetch_page_price calls the parse
    # inline, so it runs on the event loop's own thread and the loop cannot tick.
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_fetch_html)
    threads = _install_sleeping_parse(monkeypatch, ps)
    result, ticks, elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(ps.fetch_page_price(_URL, _PRODUCT_NAME, "BHD"))
    )
    assert result is not None and result.get("amount") == 45.0
    assert threads == [loop_thread], (
        "flag OFF must keep the parse on the caller's thread: parse ran on %r, loop is %r"
        % (threads, loop_thread)
    )
    # A stray tick can land on a slow runner between reading `before` and the first yield, while an off-loop parse yields >= 4 ticks, so <= 1 still pins the inline behaviour.
    assert ticks <= 1, (
        "flag OFF pin: the inline parse must still hold the loop for its whole duration "
        "(<= 1 tick expected, got %d in %.2fs)" % (ticks, elapsed)
    )


def test_flag_on_price_dict_is_identical_to_flag_off(monkeypatch):
    """PIN: parsing once must not change WHAT is extracted, only how many times."""
    monkeypatch.delenv(FLAG, raising=False)
    off = ps.extract_price_from_html(_EUR_JSONLD_PAGE, _PRODUCT_NAME, "BHD", _DOMAIN, _URL)
    monkeypatch.setenv(FLAG, "true")
    on = ps.extract_price_from_html(_EUR_JSONLD_PAGE, _PRODUCT_NAME, "BHD", _DOMAIN, _URL)
    assert on == off, (
        "the parse-once flag must be extraction-neutral: flag ON produced %r, flag OFF %r"
        % (on, off)
    )


# ---------------------------------------------------------------------------
# 2. Off the loop (LS-CONCURRENCY-LIMITS-01) - price_service.fetch_page_price
# ---------------------------------------------------------------------------


def test_fetch_page_price_does_not_block_the_loop_under_flag(monkeypatch):
    """RED today: the sync price parse runs INLINE on the event loop, so a 50ms heartbeat
    cannot tick once for the whole parse."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_fetch_html)
    threads = _install_sleeping_parse(monkeypatch, ps)

    result, ticks, elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(ps.fetch_page_price(_URL, _PRODUCT_NAME, "BHD"))
    )

    assert result is not None and result.get("amount") == 45.0, (
        "precondition: the stubbed fetch+parse must still produce a price, got %r" % (result,)
    )
    assert len(threads) == 1, (
        "precondition: the parse must be called exactly once, got %d" % len(threads)
    )
    assert elapsed >= _PARSE_SECONDS * 0.8, (
        "precondition: the sleeping parse stub must dominate the call, elapsed %.2fs" % elapsed
    )

    # THE RED ASSERTION.
    assert ticks >= _MIN_TICKS_OFF_LOOP, (
        "LS-CONCURRENCY-LIMITS-01: fetch_page_price parsed the page ON the event loop - a "
        "%.0fms heartbeat ticked %d times (expected >=%d) while the parse held the loop for "
        "%.2fs. On the single uvicorn worker every other in-flight request waits that long "
        "per page parsed." % (_TICK_SECONDS * 1000, ticks, _MIN_TICKS_OFF_LOOP, elapsed)
    )


def test_parse_runs_off_the_caller_thread_under_flag(monkeypatch):
    """RED today: the parse executes on the event loop's OWN thread."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _stub_fetch_html)
    threads = _install_sleeping_parse(monkeypatch, ps)

    result, _ticks, _elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(ps.fetch_page_price(_URL, _PRODUCT_NAME, "BHD"))
    )

    assert result is not None, "precondition: fetch_page_price must return the stub price"
    assert len(threads) == 1, (
        "precondition: the parse must be called exactly once, got %d" % len(threads)
    )

    # THE RED ASSERTION.
    assert threads[0] != loop_thread, (
        "LS-CONCURRENCY-LIMITS-01: the html parse ran on the event-loop thread (%r) instead "
        "of a worker thread under %s" % (loop_thread, FLAG)
    )


# ---------------------------------------------------------------------------
# 3. Off the loop - structured_comparison_service render call sites (:1643 / :1722)
# ---------------------------------------------------------------------------


def _stub_firecrawl_scraper_deps(monkeypatch):
    """Make ``_firecrawl_scraper`` reachable with no network, no budget, no Redis."""
    monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: True)
    monkeypatch.setattr(
        scs.firecrawl_service, "scrape_page_with_status", _stub_firecrawl_scrape
    )

    async def _gate_ok(provider):
        return True

    monkeypatch.setattr(scs, "_provider_gate_ok_async", _gate_ok)
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kwargs: None)
    monkeypatch.setattr(scs, "record_usage", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_success", lambda *a, **k: None)


def test_firecrawl_scraper_does_not_block_the_loop_under_flag(monkeypatch):
    """RED today: the SECOND async call site (structured_comparison_service.py:1643) parses
    inline too - the fan-out render legs stall the loop exactly like fetch_page_price."""
    monkeypatch.setenv(FLAG, "true")
    _stub_firecrawl_scraper_deps(monkeypatch)
    threads = _install_sleeping_parse(monkeypatch, scs)

    result, ticks, elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(
            scs._firecrawl_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)
        )
    )

    assert result is not None and result.get("value") == 45.0, (
        "precondition: the stubbed firecrawl leg must still produce a candidate, got %r"
        % (result,)
    )
    assert len(threads) == 1, (
        "precondition: the parse must be called exactly once, got %d" % len(threads)
    )

    # THE RED ASSERTION.
    assert ticks >= _MIN_TICKS_OFF_LOOP, (
        "LS-CONCURRENCY-LIMITS-01: _firecrawl_scraper parsed the rendered page ON the event "
        "loop - a %.0fms heartbeat ticked %d times (expected >=%d) over %.2fs."
        % (_TICK_SECONDS * 1000, ticks, _MIN_TICKS_OFF_LOOP, elapsed)
    )


def test_flag_off_firecrawl_scraper_parses_inline(monkeypatch):
    """PIN (green today and after): flag OFF keeps the render-leg parse inline."""
    _stub_firecrawl_scraper_deps(monkeypatch)
    threads = _install_sleeping_parse(monkeypatch, scs)

    result, ticks, elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(
            scs._firecrawl_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)
        )
    )

    assert result is not None and result.get("value") == 45.0
    assert threads == [loop_thread], (
        "flag OFF must keep the parse on the caller's thread: parse ran on %r, loop is %r"
        % (threads, loop_thread)
    )
    # A stray tick can land on a slow runner between reading `before` and the first yield, while an off-loop parse yields >= 4 ticks, so <= 1 still pins the inline behaviour.
    assert ticks <= 1, (
        "flag OFF pin: the inline parse must still hold the loop (<= 1 tick expected, got "
        "%d in %.2fs)" % (ticks, elapsed)
    )


def _stub_scrapedo_scraper_deps(monkeypatch):
    """Make ``_scrapedo_scraper`` reachable with no network, no budget, no Redis.

    Mirrors ``_stub_firecrawl_scraper_deps`` one-for-one on the scrapedo names, plus the
    ONE dependency the firecrawl leg does not have: ``validate_scrape_url`` (:1688).
    That helper is pure (no DNS, no network) and already returns True for ``_URL``, so
    stubbing it is belt-and-braces - it keeps this red test's failure anchored on the
    tick assertion even if the URL gate's rules change.
    """
    monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: True)
    monkeypatch.setattr(
        scs.scrapedo_service, "render_page_with_status", _stub_scrapedo_render
    )
    monkeypatch.setattr(scs, "validate_scrape_url", lambda url: True)

    async def _gate_ok(provider):
        return True

    monkeypatch.setattr(scs, "_provider_gate_ok_async", _gate_ok)
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kwargs: None)
    monkeypatch.setattr(scs, "record_usage", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_success", lambda *a, **k: None)


def test_scrapedo_scraper_does_not_block_the_loop_under_flag(monkeypatch):
    """RED today: the THIRD async call site (structured_comparison_service.py:1722) parses
    inline too - the residential-proxy render leg stalls the loop exactly like the
    firecrawl leg and like fetch_page_price."""
    monkeypatch.setenv(FLAG, "true")
    _stub_scrapedo_scraper_deps(monkeypatch)
    threads = _install_sleeping_parse(monkeypatch, scs)

    result, ticks, elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(
            scs._scrapedo_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)
        )
    )

    assert result is not None and result.get("value") == 45.0, (
        "precondition: the stubbed scrapedo leg must still produce a candidate, got %r"
        % (result,)
    )
    assert len(threads) == 1, (
        "precondition: the parse must be called exactly once, got %d" % len(threads)
    )

    # THE RED ASSERTION.
    assert ticks >= _MIN_TICKS_OFF_LOOP, (
        "LS-CONCURRENCY-LIMITS-01: _scrapedo_scraper parsed the rendered page ON the event "
        "loop (structured_comparison_service.py:1722) - a %.0fms heartbeat ticked %d times "
        "(expected >=%d) over %.2fs."
        % (_TICK_SECONDS * 1000, ticks, _MIN_TICKS_OFF_LOOP, elapsed)
    )


def test_flag_off_scrapedo_scraper_parses_inline(monkeypatch):
    """PIN (green today and after): flag OFF keeps the scrapedo render-leg parse inline."""
    _stub_scrapedo_scraper_deps(monkeypatch)
    threads = _install_sleeping_parse(monkeypatch, scs)

    result, ticks, elapsed, loop_thread = asyncio.run(
        _measure_loop_ticks(
            scs._scrapedo_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)
        )
    )

    assert result is not None and result.get("value") == 45.0
    assert threads == [loop_thread], (
        "flag OFF must keep the parse on the caller's thread: parse ran on %r, loop is %r"
        % (threads, loop_thread)
    )
    # A stray tick can land on a slow runner between reading `before` and the first yield, while an off-loop parse yields >= 4 ticks, so <= 1 still pins the inline behaviour.
    assert ticks <= 1, (
        "flag OFF pin: the inline parse must still hold the loop (<= 1 tick expected, got "
        "%d in %.2fs)" % (ticks, elapsed)
    )
