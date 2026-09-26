"""W0-4e / W0-4f / W0-4g red tests: the follow-ups of the merged R-W04 retro (PR #196).

Spec: .qa-s68/W0_4EFG_SPEC.md (session 68). Everything stays under the EXISTING
ENABLE_PRICE_PARSE_OFFLOAD (default OFF, read per call; no new flag). Flag OFF must stay
byte-identical to 61585c58.

  W0-4e  structured_comparison_service._lazy_bh_pdp_backfill curls a retailer SEARCH page and
         regex-scans it for an in-domain /product/ href. Under the flag curl_fetch_html caps
         every caller at PRICE_FETCH_MAX_BYTES (3,000,000 chars), so an href past the cap is
         lost. Design: ``curl_fetch_html(url, *, cap=True)``; the backfill passes ``cap=False``
         (the ONLY such site in app/). W0-4e2 (Fable R11): under the flag the scan of the
         uncapped page runs ON the event loop in slices of scs._W04_SCAN_CHUNK chars (+
         _W04_SCAN_OVERLAP), a match kept only by the slice it starts in, one
         ``asyncio.sleep(0)`` per slice; no pool (re holds the GIL for a whole findall, so a
         pool thread never freed the loop). Flag OFF: the base single ``re.findall`` inline.
         The ``_accept`` loop stays on the event loop in both states.
  W0-4f  url_extraction_service.extract_from_url runs extract_amazon_data /
         extract_noon_data / extract_generic_data (each builds a soup) INLINE on the loop.
         Design: select the extractor (module global, call time); under the flag cap the
         html at PRICE_FETCH_MAX_BYTES right after the fetch (the SAME capped html reaches
         extract_with_ai) and run the extractor through price_service.run_parse_offloaded;
         flag OFF the extractor runs inline on the whole body.
  W0-4g  pool instrumentation: price_service._PRICE_PARSE_STATS counters maintained by
         run_parse_offloaded, price_service.price_parse_pool_stats(), a
         ``[PRICE-PARSE] pool built workers=N`` INFO line once per pool build, and
         /health's ``price_parse_pool`` key once the pool exists (absent flag OFF). Plus the
         four r1-adversary test-side gaps (H1-H4), each a pin that kills a named mutant.

Row kinds (each test docstring starts with one): RED fails at 61585c58 on an assertion about
the absent behaviour; PIN is green at 61585c58 and must stay green; KILL is a PIN whose proof
is its named mutant going red. A symbol that does not exist yet is looked up inside the test
(getattr / inspect) and its absence is reported with pytest.fail, never an AttributeError or
TypeError escaping the test body.

Zero network: the autouse ``_zero_network`` fixture blocks every non-loopback socket connect
and getaddrinfo and replaces ``curl_cffi.requests.get`` (libcurl never reaches the Python
socket layer). Fixture pages are synthetic; no corpus file is read.
"""

import ast
import asyncio
import concurrent.futures
import copy
import hashlib
import importlib
import inspect
import json
import logging
import os
import re
import socket
import threading
import time
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.services import price_service as ps
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as ues

FLAG = "ENABLE_PRICE_PARSE_OFFLOAD"
POOL_ENV = "PRICE_PARSE_MAX_WORKERS"
CAP = 3_000_000
SIZES = [CAP - 1, CAP, CAP + 1, 3_500_000]
ACCEPTED_ON_VALUES = ["true", "1", "yes", "on"]

REPO = Path(__file__).resolve().parent.parent
APP_DIR = REPO / "app"

_PRODUCT_NAME = "Testbrand Aqua EDP 100ml"
_DOMAIN = "example-w04.com"
_URL = "https://example-w04.com/p/1"
_BD = "bahrain.sharafdg.com"
_HREF = "https://%s/product/testbrand-aqua-edp-100ml/" % _BD
_SEARCH_LINK = "https://%s/?s=testbrand" % _BD

_STATS_KEYS = {"jobs_total", "waiting", "running", "peak_waiting", "peak_running"}


def _ps():
    """app.services.price_service as sys.modules holds it NOW. Issue #185 class: a test earlier
    in the one-process CI order (tests/test_platform_router.py) deletes price_service from
    sys.modules, so a later import builds a FRESH module; structured_comparison_service's
    call-time ``from app.services import price_service``, url_extraction_service's call-time
    ``from app.services.price_service import ...`` and /health's ``sys.modules.get`` all read
    the CURRENT module, so every patch and every read here targets that one too."""
    return importlib.import_module("app.services.price_service")


def _modules():
    """Every module that can hold a price-parse pool: the collection-time binding, the
    current price_service, and the two callers."""
    out = []
    for module in (ps, _ps(), scs, ues):
        if all(module is not m for m in out):
            out.append(module)
    return out


# ---------------------------------------------------------------------------
# Autouse fixtures (the pattern of tests/test_retro_w0_4.py)
# ---------------------------------------------------------------------------

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "", None, "testserver"}


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
            raise OSError("W0-4efg zero-network guard: blocked connect to %r" % (host,))
        return real_connect(self, address)

    def guard_connect_ex(self, address):
        host = _host_of(address)
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host not in _LOOPBACK:
            attempts.append(("connect_ex", host))
            raise OSError("W0-4efg zero-network guard: blocked connect_ex to %r" % (host,))
        return real_connect_ex(self, address)

    def guard_getaddrinfo(host, *args, **kwargs):
        name = host.decode("ascii", "replace") if isinstance(host, bytes) else host
        if name not in _LOOPBACK:
            attempts.append(("getaddrinfo", name))
            raise socket.gaierror("W0-4efg zero-network guard: blocked getaddrinfo(%r)" % (name,))
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)

    import curl_cffi.requests as curl_requests

    def curl_guard(*args, **kwargs):
        attempts.append(("curl_cffi.get", args[:1]))
        raise RuntimeError("W0-4efg zero-network guard: blocked curl_cffi.requests.get")

    monkeypatch.setattr(curl_requests, "get", curl_guard)
    yield
    assert not attempts, "W0-4efg zero-network guard: the test attempted network I/O: %r" % (
        attempts,
    )


@pytest.fixture(autouse=True)
def _w04_env(monkeypatch):
    """Each test opts in to the flag; the extractor environment is the shipped default."""
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
    """Drop any price-parse pool / parse semaphore BY TYPE (never by name), and zero any
    parse-stats counter dict BY SHAPE (a dict carrying jobs_total/waiting/running), so every
    test sees a pool built afresh and counters that start at 0."""
    for module in _modules():
        for name, value in list(vars(module).items()):
            if isinstance(value, concurrent.futures.ThreadPoolExecutor) and str(
                getattr(value, "_thread_name_prefix", "")
            ).startswith("price-parse"):
                value.shutdown(wait=False, cancel_futures=True)
                setattr(module, name, None)
            elif isinstance(value, asyncio.Semaphore) and "parse" in name.lower():
                setattr(module, name, None)
            elif isinstance(value, dict) and {"jobs_total", "waiting", "running"} <= set(value):
                for key in list(value):
                    if isinstance(value[key], int) and not isinstance(value[key], bool):
                        value[key] = 0


@pytest.fixture(autouse=True)
def _fresh_parse_pool():
    _reset_parse_pools()
    yield
    _reset_parse_pools()


def _price_parse_pools():
    return [
        name for module in _modules() for name, value in vars(module).items()
        if isinstance(value, concurrent.futures.ThreadPoolExecutor)
        and str(getattr(value, "_thread_name_prefix", "")).startswith("price-parse")
    ]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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


def _numbered_body(size):
    """A body whose every prefix is distinct, so a wrong slice cannot compare equal."""
    unit = "0123456789abcdef"
    return (unit * (size // len(unit) + 1))[:size]


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


# ===========================================================================
# W0-4e: the lazy-backfill search-page scan
# ===========================================================================


def _search_page(filler_chars, extra_links=()):
    links = "".join('<a href="%s">x</a>' % link for link in extra_links)
    return (
        "<html><body>" + ("x" * filler_chars)
        + '<a href="%s">p</a>' % _HREF
        + '<a href="https://other-shop.example/product/testbrand-aqua-edp-100ml/">o</a>'
        + '<a href="%s">dup</a>' % _HREF
        + links + "</body></html>"
    )


class _ReProxy:
    """Stands in for structured_comparison_service's module global ``re``: records the thread
    of every ``findall`` / ``finditer`` over the /product/ href pattern (the backfill's scan:
    one findall flag OFF, one finditer per slice flag ON), delegates all else to the real
    module. With ``scanned`` it also keeps the string each scan call received (Fable R14: the
    slice lengths). Scoped to scs only, never the global ``re`` module."""

    def __init__(self, real, sink, events=None, scanned=None):
        self._real = real
        self._sink = sink
        self._events = events
        self._scanned = scanned

    def __getattr__(self, name):
        return getattr(self._real, name)

    def _record(self, pattern, string):
        if "/product/" in str(getattr(pattern, "pattern", pattern)):
            self._sink.append(threading.current_thread().name)
            if self._events is not None:
                self._events.append("scan")
            if self._scanned is not None:
                self._scanned.append(string)

    def findall(self, pattern, string, flags=0):
        self._record(pattern, string)
        return self._real.findall(pattern, string, flags)

    def finditer(self, pattern, string, flags=0):
        self._record(pattern, string)
        return self._real.finditer(pattern, string, flags)


class _SliceRecordingPage(str):
    """A search page that records the key of every SLICE taken of it (Fable R14: the slice
    offsets). ``curl_fetch_html(..., cap=False)`` hands the response text back as the same
    object under the flag, so the backfill's ``html[start:end]`` lands here; a slice of it
    is a plain ``str``, so the regex sees ordinary strings."""

    def __new__(cls, value, keys):
        page = super().__new__(cls, value)
        page._keys = keys
        return page

    def __getitem__(self, key):
        if isinstance(key, slice):
            self._keys.append(key)
        return str.__getitem__(self, key)


def _arm_backfill(monkeypatch, body, accept_threads=None):
    """Stub the backfill's I/O (Serper, curl) and gates. Returns the /product/ scan thread sink."""
    _patch_curl_get(monkeypatch, _BigResp(200, body))

    async def _search(query, num_results=5):
        if _BD in query:
            return {"organic": [{"link": _SEARCH_LINK, "title": "search"}]}
        return {"organic": []}

    def _validate(url):
        if accept_threads is not None:
            accept_threads.append(("validate_scrape_url", threading.current_thread().name))
        return True

    def _score(link, category):
        if accept_threads is not None:
            accept_threads.append(("score_source", threading.current_thread().name))
        return 2.0

    monkeypatch.setattr(scs, "search_web", _search)
    monkeypatch.setattr(scs, "validate_scrape_url", _validate)
    monkeypatch.setattr(scs, "score_source", _score)
    scan_threads = []
    monkeypatch.setattr(scs, "re", _ReProxy(re, scan_threads))
    return scan_threads


def _run_backfill():
    extra = asyncio.run(scs._lazy_bh_pdp_backfill([], _PRODUCT_NAME, "fragrance"))
    return [e[0] for e in extra]


def test_w04e_flag_on_backfill_scan_sees_an_href_past_3mb(monkeypatch):
    """RED at 61585c58: under the flag curl_fetch_html caps EVERY caller at 3,000,000 chars, so
    the backfill's scan of a curled search page whose only in-domain /product/ href sits after
    3,500,000 chars finds nothing (measured: extra == []). The backfill must fetch with
    cap=False and still find it (the base OFF pin's body, flag ON)."""
    monkeypatch.setenv(FLAG, "true")
    _arm_backfill(monkeypatch, _search_page(3_500_000))

    links = _run_backfill()

    assert links == [_HREF], (
        "W0-4e: flag ON, the backfill's search-page scan returned %r; the only in-domain "
        "/product/ href sits after 3,500,000 chars and must still be found (the backfill "
        "exempts itself from the 3 MB cap with curl_fetch_html(..., cap=False))" % (links,)
    )


# The base backfill pattern, byte for byte (61585c58). Hard-coded here, never read from scs,
# so a changed pattern in either flag state diverges from this reference.
_BASE_SCAN_PATTERN = r'href=["\'](https?://[^"\']*?/product/[^"\']+)["\']'
_E2_PAGE_CHARS = 5_012_345  # about 5 MB, deliberately not a multiple of the chunk


def _scan_constants():
    chunk = getattr(scs, "_W04_SCAN_CHUNK", None)
    overlap = getattr(scs, "_W04_SCAN_OVERLAP", None)
    if not isinstance(chunk, int) or not isinstance(overlap, int):
        pytest.fail(
            "W0-4e2: structured_comparison_service has no int _W04_SCAN_CHUNK / "
            "_W04_SCAN_OVERLAP (got %r / %r); the flag-ON backfill scan must be chunked"
            % (chunk, overlap)
        )
    return chunk, overlap


def _bd_href(slug):
    return "https://%s/product/%s/" % (_BD, slug)


def _placed_page(total, placements):
    """A page of ``total`` filler chars with ``href="<url>">`` written so each MATCH starts at
    exactly the given absolute offset (the regex match begins at the 'h' of href). A placement
    is ``(offset, url)`` or ``(offset, url, opener, closer)``: ``opener`` replaces ``href="``
    (e.g. ``HREF='``) and ``closer`` the closing quote, for the mixed-case rows."""
    buf = bytearray(b"x" * total)
    for placement in placements:
        offset, url = placement[0], placement[1]
        opener, closer = (placement[2], placement[3]) if len(placement) == 4 else ('href="', '"')
        piece = ("%s%s%s>" % (opener, url, closer)).encode("ascii")
        assert buf[offset:offset + len(piece)] == b"x" * len(piece), "fixture overlap at %d" % offset
        buf[offset:offset + len(piece)] = piece
    return buf.decode("ascii")


def _e2a_case(name):
    chunk, overlap = _scan_constants()
    n = _E2_PAGE_CHARS
    if name == "href-at-chunk-minus-1":
        return n, [(chunk - 1, _bd_href("at-chunk-minus-1"))]
    if name == "href-at-chunk":
        return n, [(chunk, _bd_href("at-chunk"))]
    if name == "href-at-chunk-plus-1":
        return n, [(chunk + 1, _bd_href("at-chunk-plus-1"))]
    if name == "href-spanning-the-first-boundary":
        return n, [(chunk - 40, _bd_href("testbrand-aqua-edp-100ml-spanning-the-first-boundary"))]
    if name == "same-href-on-both-sides-of-a-boundary":
        return n, [(chunk - 500, _HREF), (chunk + 500, _HREF)]
    if name == "every-boundary":
        placements = []
        for k in range(1, n // chunk + 1):
            b = k * chunk
            placements += [
                (b - 300, _bd_href("before-%d" % k)),
                (b - 40, _bd_href("span-%d-testbrand-aqua-edp-100ml" % k)),
                (b + 100, _bd_href("after-%d" % k)),
            ]
            if b + overlap - 200 < n - 200:
                placements.append((b + overlap - 200, _bd_href("tail-%d" % k)))
        return n, placements
    if name == "300-spread":
        step = n // 300
        return n, [(i * step + (i * 7919) % 1000, _bd_href("spread-%03d" % i)) for i in range(300)]
    if name == "page-shorter-than-one-chunk":
        return 400_000, [(1_000, _bd_href("short-a")), (200_000, _HREF), (399_000, _bd_href("short-b"))]
    if name == "long-href-spanning-a-boundary":
        # Fable R15a: an in-domain href of about 4,000 chars (a long query string) starting
        # 1,000 chars before the first boundary, so about 3,000 of its chars sit past it; only
        # an overlap longer than that keeps it whole (OVERLAP=100 loses it), plus a short
        # control after it.
        query = "&".join("utm_p%03d=v%03d" % (i, i) for i in range(285))
        long_href = _bd_href("testbrand-aqua-edp-100ml") + "?" + query
        assert 3_900 <= len(long_href) <= 4_200, len(long_href)
        return n, [(chunk - 1_000, long_href), (chunk + 20_000, _bd_href("after-the-long-href"))]
    if name == "mixed-case-around-the-boundaries":
        # Upper/mixed-case attribute, scheme, host and /Product/ segment, both quote kinds
        # (mixed on one href): HREF= spanning the first boundary, /Product/ starting at the
        # second boundary + 1, one in the second slice's overlap tail, one spanning the third
        # boundary, plus one all-lowercase control. The base pattern runs with re.IGNORECASE
        # in BOTH branches; a case-sensitive scan keeps only the control. Rows past the page
        # end are dropped, so a larger CHUNK (an equivalent tuning) keeps a valid fixture.
        placements = [
            (chunk - 700, "HTTPS://%s/PRODUCT/MIXED-ALL-UPPER/" % _BD.upper(), 'Href="', '"'),
            (chunk - 40, _bd_href("mixed-upper-attr-spanning-the-first-boundary"), 'HREF="', '"'),
            (chunk + 900, _bd_href("mixed-lowercase-control"), 'href="', '"'),
            (2 * chunk + 1, "https://%s/Product/mixed-capital-product-segment/" % _BD, "href='", "'"),
            (2 * chunk + overlap - 200,
             "hTtPs://%s/pRoDuCt/mixed-in-the-overlap-tail/" % _BD.upper(), 'hReF="', '"'),
            (3 * chunk - 25, "Http://%s/PRODUCT/mixed-quotes-spanning-the-third/" % _BD, "HREF='", '"'),
        ]
        return n, [p for p in placements if p[0] + 200 < n]
    raise AssertionError(name)


def _arm_backfill_raw(monkeypatch, body):
    """Arm the backfill so EVERY in-domain match reaches ``validate_scrape_url`` (it records and
    rejects, so ``_seen`` never dedupes): the recorded list is the raw scan result, in order,
    duplicates kept."""
    _arm_backfill(monkeypatch, body)
    raw = []

    def _record(url):
        raw.append(url)
        return False

    monkeypatch.setattr(scs, "validate_scrape_url", _record)
    return raw


_E2A_CASES = [
    "href-at-chunk-minus-1",
    "href-at-chunk",
    "href-at-chunk-plus-1",
    "href-spanning-the-first-boundary",
    "same-href-on-both-sides-of-a-boundary",
    "every-boundary",
    "300-spread",
    "page-shorter-than-one-chunk",
    "mixed-case-around-the-boundaries",
    "long-href-spanning-a-boundary",
]


@pytest.mark.parametrize("case", _E2A_CASES)
def test_w04e2_flag_on_chunked_scan_is_identical_to_findall(monkeypatch, case):
    """KILL (E2a, Fable R11 + R15a): the flag-ON chunked scan returns EXACTLY
    re.findall(base pattern, page, re.IGNORECASE) and the flag-OFF list, in order with
    duplicates kept, on about-5 MB pages with a match starting at CHUNK-1 / CHUNK / CHUNK+1,
    one spanning the first boundary, the same href on both sides of a boundary, matches at and
    around every boundary, 300 spread, a page shorter than one chunk, mixed-case hrefs
    (``HREF=``, ``HTTPS``, ``/Product/``, both quote kinds) across the boundaries, and an
    about-4,000-char href spanning the first boundary. Kills OVERLAP=0 (a spanning match is
    lost), OVERLAP=100 (the long href is lost), the start-in-slice dedupe dropped (an
    overlap-tail match is collected twice), a changed pattern, and re.IGNORECASE dropped in
    EITHER branch (the mixed-case row)."""
    total, placements = _e2a_case(case)
    page = _placed_page(total, placements)
    expected = re.findall(_BASE_SCAN_PATTERN, page, re.IGNORECASE)
    assert expected == [p[1] for p in sorted(placements)], "fixture: findall saw %d of %d" % (
        len(expected), len(placements),
    )
    if case.startswith("mixed-case"):
        case_sensitive = re.findall(_BASE_SCAN_PATTERN, page)
        assert len(case_sensitive) == 1 < len(expected), (
            "fixture: the mixed-case row must need re.IGNORECASE (case-sensitive findall saw "
            "%d of %d)" % (len(case_sensitive), len(expected))
        )

    raw_off = _arm_backfill_raw(monkeypatch, page)
    _run_backfill()
    monkeypatch.setenv(FLAG, "true")
    raw_on = _arm_backfill_raw(monkeypatch, page)
    _run_backfill()

    assert raw_off == expected, "flag OFF scan diverged from re.findall (%d vs %d)" % (
        len(raw_off), len(expected),
    )
    assert raw_on == expected, (
        "W0-4e2: flag ON, the chunked scan returned %d match(es), re.findall %d (case %s); "
        "first difference at index %r" % (
            len(raw_on), len(expected), case,
            next((i for i, (a, b) in enumerate(zip(raw_on, expected)) if a != b),
                 min(len(raw_on), len(expected))),
        )
    )


@pytest.mark.parametrize("case", _E2A_CASES)
def test_w04e2_flag_on_scan_slices_are_bounded_and_cover_the_page(monkeypatch, case):
    """KILL (Fable R14, deterministic, no timing): flag ON, over the E2a fixture pages, the
    backfill scans exactly ceil(n/CHUNK) slices; slice i is ``page[start:end]`` with the
    starts exactly ``range(0, n, CHUNK)`` and each end ``min(start + CHUNK + OVERLAP, n)``, so
    no scan call sees more than CHUNK + OVERLAP chars and together they cover [0, n) with the
    ruled overlap. The offsets come from the page itself (it records every slice key taken of
    it), the lengths from the ``re`` recorder. Kills a slice without its end bound
    (``html[start:]``: the first slice scans the whole page before its first yield, the inline
    stall W0-4e2 removes) and a wrong step (``range(0, n, CHUNK * 2)``)."""
    chunk, overlap = _scan_constants()
    total, placements = _e2a_case(case)
    text = _placed_page(total, placements)
    n = len(text)
    slice_keys = []
    page = _SliceRecordingPage(text, slice_keys)
    monkeypatch.setenv(FLAG, "true")
    raw_on = _arm_backfill_raw(monkeypatch, page)
    scanned = []
    scan_threads = []
    monkeypatch.setattr(scs, "re", _ReProxy(re, scan_threads, scanned=scanned))

    _run_backfill()

    expected_bounds = [(start, min(start + chunk + overlap, n)) for start in range(0, n, chunk)]
    lengths = [len(s) for s in scanned]
    assert len(scanned) == -(-n // chunk) == len(expected_bounds), (
        "W0-4e2: flag ON, %d scan call(s) over a %d-char page; expected ceil(n/CHUNK) = %d"
        % (len(scanned), n, -(-n // chunk))
    )
    assert max(lengths) <= chunk + overlap, (
        "W0-4e2: flag ON, a scan call received %d chars (> CHUNK + OVERLAP = %d); slice "
        "lengths %r" % (max(lengths), chunk + overlap, lengths)
    )
    taken = [key.indices(n) for key in slice_keys]
    assert [(a, b) for a, b, _step in taken] == expected_bounds and all(
        step == 1 for _a, _b, step in taken
    ), (
        "W0-4e2: flag ON, the page was sliced at %r; expected %r (starts range(0, n, CHUNK), "
        "ends min(start + CHUNK + OVERLAP, n))" % (taken, expected_bounds)
    )
    assert lengths == [b - a for a, b in expected_bounds], (lengths, expected_bounds)
    assert all(s == text[a:b] for s, (a, b) in zip(scanned, expected_bounds)), (
        "W0-4e2: a scan call did not receive its slice's text"
    )
    assert set(scan_threads) == {"MainThread"}, scan_threads
    assert raw_on == re.findall(_BASE_SCAN_PATTERN, text, re.IGNORECASE)


def test_w04e2_scan_constants_are_the_ruled_values():
    """PIN (Fable R15b): ``_W04_SCAN_CHUNK == 1_000_000`` and ``_W04_SCAN_OVERLAP == 65_536``
    by value. pr_text and CLAUDE.md quote them as a contract (1 MB turns; an href up to
    65,536 chars is never lost at a boundary), so neither may drift silently. CHUNK=2_000_000
    keeps every identity row green (a tuning equivalent) and reddens only this pin."""
    chunk, overlap = _scan_constants()
    assert (chunk, overlap) == (1_000_000, 65_536), (
        "W0-4e2: _W04_SCAN_CHUNK / _W04_SCAN_OVERLAP are %r / %r; the ruled values are "
        "1_000_000 / 65_536" % (chunk, overlap)
    )


class _AsyncioProxy:
    """Stands in for structured_comparison_service's module global ``asyncio``: records every
    ``sleep`` delay into ``events`` and awaits the REAL asyncio.sleep; all else delegates."""

    def __init__(self, real, events):
        self._real = real
        self._events = events
        self._real_sleep = real.sleep

    def __getattr__(self, name):
        return getattr(self._real, name)

    async def sleep(self, delay, *args, **kwargs):
        self._events.append(("sleep", delay))
        return await self._real_sleep(delay, *args, **kwargs)


@pytest.mark.parametrize("flag_value", [None, "true"], ids=["unset", "true"])
def test_w04e2_flag_on_scan_yields_the_loop_once_per_slice(monkeypatch, flag_value):
    """KILL (E2b, Fable R11): over a ~5 MB page, flag ON the backfill scans ceil(n/CHUNK)
    slices on the event loop and awaits ``asyncio.sleep(0)`` after EVERY slice (the events
    alternate scan, sleep(0), scan, sleep(0), ...), so >= ceil(n/CHUNK) sleep(0) calls; flag
    OFF it scans ONCE (the base findall) and never sleeps. Kills the sleep removed and a
    whole-page findall with a single sleep (1 < ceil(n/CHUNK))."""
    _set_flag(monkeypatch, flag_value)
    chunk, _overlap = _scan_constants()
    body = _search_page(_E2_PAGE_CHARS)
    _arm_backfill(monkeypatch, body)
    events = []
    scan_threads = []
    monkeypatch.setattr(scs, "re", _ReProxy(re, scan_threads, events))
    monkeypatch.setattr(scs, "asyncio", _AsyncioProxy(asyncio, events))

    links = _run_backfill()

    assert links == [_HREF], links
    assert scan_threads and set(scan_threads) == {"MainThread"}, scan_threads
    sleeps = [e for e in events if e != "scan"]
    if flag_value is None:
        assert events == ["scan"], (
            "flag OFF must run the base single findall and never sleep, got %r" % (events,)
        )
        return
    slices = -(-len(body) // chunk)
    zero_sleeps = [e for e in sleeps if e == ("sleep", 0)]
    assert len(zero_sleeps) >= slices, (
        "W0-4e2: flag ON, %d sleep(0) call(s) over a %d-char page; the chunked scan must yield "
        "at least ceil(n/CHUNK) = %d times" % (len(zero_sleeps), len(body), slices)
    )
    assert events == ["scan", ("sleep", 0)] * slices, (
        "W0-4e2: flag ON, the scan/yield sequence was %r; expected one slice then one sleep(0), "
        "%d times" % (events[:12], slices)
    )


def test_w04e2_flag_on_backfill_never_reaches_the_price_parse_pool(monkeypatch):
    """PIN (Fable R11: the pool offload of this site is REMOVED): flag ON, the backfill finds
    the href past 3,500,000 chars with every scan slice on MainThread, makes ZERO calls to
    price_service.run_parse_offloaded (module or package attribute) and builds no pool."""
    monkeypatch.setenv(FLAG, "true")
    scan_threads = _arm_backfill(monkeypatch, _search_page(3_500_000))
    spy_calls = []

    async def _spy(fn, *args, **kwargs):
        spy_calls.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr(_ps(), "run_parse_offloaded", _spy)
    package_ps = importlib.import_module("app.services").price_service
    if package_ps is not _ps():
        monkeypatch.setattr(package_ps, "run_parse_offloaded", _spy)

    links = _run_backfill()

    assert links == [_HREF], links
    assert len(scan_threads) >= 2 and set(scan_threads) == {"MainThread"}, scan_threads
    assert spy_calls == [], "W0-4e2: the flag-ON backfill submitted %d job(s) to the pool" % (
        len(spy_calls),
    )
    assert _price_parse_pools() == [], _price_parse_pools()


@pytest.mark.parametrize("flag_value", [None, "false"], ids=["unset", "false"])
def test_w04e_flag_off_backfill_scan_inline_whole_page_no_pool(monkeypatch, flag_value):
    """PIN: flag OFF (and unset) the backfill scans the WHOLE page (an href past 3,500,000
    chars is found), the scan runs on MainThread, and no price-parse pool is ever built."""
    _set_flag(monkeypatch, flag_value)
    scan_threads = _arm_backfill(monkeypatch, _search_page(3_500_000))
    spy_calls = []

    async def _spy(fn, *args, **kwargs):
        spy_calls.append(fn)
        raise AssertionError("flag OFF reached price_service.run_parse_offloaded")

    monkeypatch.setattr(_ps(), "run_parse_offloaded", _spy)

    links = _run_backfill()

    assert links == [_HREF], links
    assert scan_threads and set(scan_threads) == {"MainThread"}, scan_threads
    assert spy_calls == [], spy_calls
    assert _price_parse_pools() == [], "flag OFF built a price-parse pool: %r" % (
        _price_parse_pools(),
    )


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag-off", "flag-on"])
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("cap", [True, False], ids=["cap-True", "cap-False"])
def test_w04e_curl_fetch_html_cap_kwarg(monkeypatch, cap, size, flag_on):
    """RED at 61585c58 (every row): curl_fetch_html(url) has no ``cap`` keyword, so the call
    below cannot be made (TypeError); the absence is reported before the call. Contract:
    ``cap`` is KEYWORD-ONLY with default True; flag ON + cap=True -> exactly
    min(len, 3,000,000); flag ON + cap=False -> the whole body; flag OFF -> the whole body
    whatever ``cap`` says (the base statements)."""
    params = inspect.signature(_ps().curl_fetch_html).parameters
    param = params.get("cap")
    if param is None:
        pytest.fail(
            "W0-4e: price_service.curl_fetch_html%s has no keyword-only 'cap' parameter, so the "
            "backfill cannot exempt itself from the 3 MB cap (behaviour absent)"
            % (inspect.signature(_ps().curl_fetch_html),)
        )
    assert param.kind is inspect.Parameter.KEYWORD_ONLY and param.default is True, (
        "W0-4e: 'cap' must be keyword-only with default True, got kind=%s default=%r"
        % (param.kind, param.default)
    )
    if flag_on:
        monkeypatch.setenv(FLAG, "true")
    body = _numbered_body(size)
    _patch_curl_get(monkeypatch, _BigResp(200, body))

    html = asyncio.run(_ps().curl_fetch_html(_URL, cap=cap))

    expected = body[:CAP] if (flag_on and cap) else body
    assert html is not None and len(html) == len(expected) and html == expected, (
        "W0-4e: flag %s cap=%r size=%d returned %s chars; expected %d"
        % ("ON" if flag_on else "OFF", cap, size, None if html is None else len(html),
           len(expected))
    )


def _cap_exemptions():
    """{(file name, enclosing def)} of every call to curl_fetch_html in app/**/*.py passing a
    ``cap=`` keyword whose value is not the literal True."""
    found = set()
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else "")
            if name != "curl_fetch_html":
                continue
            for kw in node.keywords:
                if kw.arg != "cap":
                    continue
                if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    continue
                owner = parents.get(node)
                while owner is not None and not isinstance(
                    owner, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    owner = parents.get(owner)
                found.add((path.name, owner.name if owner is not None else "<module>"))
    return found


def test_w04e_exactly_one_caller_exempts_itself_from_the_cap():
    """RED at 61585c58 (measured: empty set). The cap stays the default for every caller; the
    ONLY exemption in app/ is structured_comparison_service._lazy_bh_pdp_backfill. A second
    exemption later turns this red too."""
    found = _cap_exemptions()
    assert found == {("structured_comparison_service.py", "_lazy_bh_pdp_backfill")}, (
        "W0-4e: the set of (file, def) passing cap=<not True> to curl_fetch_html is %r; it must "
        "be exactly {('structured_comparison_service.py', '_lazy_bh_pdp_backfill')}"
        % (sorted(found),)
    )


@pytest.mark.parametrize("filler", [2_000, 3_500_000], ids=["small-page", "page-past-3mb"])
def test_w04e_backfill_result_identical_flag_on_vs_off(monkeypatch, filler):
    """PIN (small-page) / RED at 61585c58 (page-past-3mb: flag ON returns [] where OFF returns
    [href]). The backfill's ``extra`` list (order, dedup, out-of-domain rejection) must be the
    same list with the flag unset and ON."""
    body = _search_page(filler)
    _arm_backfill(monkeypatch, body)
    off = _run_backfill()
    monkeypatch.setenv(FLAG, "true")
    _arm_backfill(monkeypatch, body)
    on = _run_backfill()

    assert off == [_HREF], "precondition: flag OFF must yield %r, got %r" % (_HREF, off)
    assert on == off, "W0-4e: flag ON returned %r, flag OFF %r (filler %d chars)" % (
        on, off, filler,
    )


@pytest.mark.parametrize("flag_value", [None, "true"], ids=["unset", "true"])
def test_w04e_backfill_accept_loop_stays_on_the_loop(monkeypatch, flag_value):
    """PIN: the per-match ``_accept`` loop (validate_scrape_url, score_source, the append) runs
    on the event loop (MainThread) in both flag states (flag ON after the chunked scan;
    Fable R11 removed the scan's pool offload). Kills '_accept moved onto a worker thread'."""
    _set_flag(monkeypatch, flag_value)
    accept_threads = []
    _arm_backfill(monkeypatch, _search_page(2_000), accept_threads=accept_threads)

    links = _run_backfill()

    assert links == [_HREF], links
    kinds = {k for k, _ in accept_threads}
    assert {"validate_scrape_url", "score_source"} <= kinds, accept_threads
    assert {n for _, n in accept_threads} == {"MainThread"}, (
        "W0-4e: the _accept helpers ran on %r; they must stay on the event loop"
        % (sorted({n for _, n in accept_threads}),)
    )


# ===========================================================================
# W0-4f: extract_from_url's three extractors
# ===========================================================================

_AMAZON_URL = "https://www.amazon.ae/dp/B0W04F0001"
_NOON_URL = "https://www.noon.com/uae-en/testbrand-aqua-w04f/N0W04F/p/"
_GENERIC_URL = "https://shop.example-w04f.com/products/testbrand-aqua-w04f"

_AMAZON_PAGE = """<html><head><title>Amazon.ae: Testbrand Aqua Widget W04F</title></head><body>
<span id="productTitle"> Testbrand Aqua Widget W04F </span>
<span class="a-price-whole">1,234</span>
<span class="a-icon-alt">4.5 out of 5 stars</span>
<span id="acrCustomerReviewText">1,024 ratings</span>
<img id="landingImage" src="https://img.example-w04f.com/w04f.jpg">
<ul class="a-unordered-list a-vertical a-spacing-mini"><li>Feature one</li><li>Feature two</li></ul>
</body></html>"""

_AMAZON_PAGE_NO_PRICE = """<html><head><title>Amazon.ae</title></head><body>
<span id="productTitle"> Testbrand Aqua Widget W04F </span>
</body></html>"""

_NOON_PAGE = """<html><head><title>Noon</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
"name":"Testbrand Aqua Noon W04F","description":"A test product","image":"https://img.example-w04f.com/n.jpg",
"brand":{"@type":"Brand","name":"Testbrand"},
"offers":{"@type":"Offer","price":"199.00","priceCurrency":"AED","availability":"https://schema.org/InStock"},
"aggregateRating":{"@type":"AggregateRating","ratingValue":"4.2","reviewCount":"87"}}</script>
</head><body><h1>Testbrand Aqua Noon W04F</h1></body></html>"""

_NOON_PAGE_NO_PRICE = """<html><head><title>Noon</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
"name":"Testbrand Aqua Noon W04F","brand":{"@type":"Brand","name":"Testbrand"}}</script>
</head><body><h1>Testbrand Aqua Noon W04F</h1></body></html>"""

_GENERIC_PAGE = """<html><head><title>Testbrand Aqua Generic W04F | Shop</title>
<meta property="og:title" content="Testbrand Aqua Generic W04F">
<meta property="og:image" content="https://img.example-w04f.com/g.jpg">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
"name":"Testbrand Aqua Generic W04F","brand":"Testbrand",
"offers":[{"@type":"Offer","price":"45.500","priceCurrency":"BHD"}]}</script>
</head><body><p>Testbrand Aqua Generic W04F</p></body></html>"""

_GENERIC_PAGE_NO_PRICE = """<html><head><title>Testbrand Aqua Generic W04F | Shop</title>
<meta property="og:title" content="Testbrand Aqua Generic W04F">
</head><body><p>Testbrand Aqua Generic W04F</p></body></html>"""

# branch -> (url, extractor global name, structured page, needs-ai page, expected title, price)
_BRANCHES = {
    "amazon": (_AMAZON_URL, "extract_amazon_data", _AMAZON_PAGE, _AMAZON_PAGE_NO_PRICE,
               "Testbrand Aqua Widget W04F", 1234.0),
    "noon": (_NOON_URL, "extract_noon_data", _NOON_PAGE, _NOON_PAGE_NO_PRICE,
             "Testbrand Aqua Noon W04F", "199.00"),
    "generic": (_GENERIC_URL, "extract_generic_data", _GENERIC_PAGE, _GENERIC_PAGE_NO_PRICE,
                "Testbrand Aqua Generic W04F", "45.500"),
}

_AI_ANSWER = {"price": 42.5, "currency": "BHD", "brand": "Testbrand",
              "specs": {"size": "100ml"}, "category": "fragrances"}


def _arm_extract_from_url(monkeypatch, branch, page, record_threads=True):
    """Stub fetch_page (the page), wrap the branch's extractor (module global) to record its
    thread, and stub extract_with_ai with a deterministic answer that records len(html).
    Returns (url, extractor_threads, ai_calls)."""
    url, extractor_name, _s, _n, _t, _p = _BRANCHES[branch]

    async def _fetch(u):
        return page

    monkeypatch.setattr(ues, "fetch_page", _fetch)
    threads = []
    original = getattr(ues, extractor_name)

    def _wrapper(html, u):
        if record_threads:
            threads.append(threading.current_thread().name)
        return original(html, u)

    monkeypatch.setattr(ues, extractor_name, _wrapper)
    ai_calls = []

    async def _ai(u, html, retailer):
        ai_calls.append(len(html))
        return dict(_AI_ANSWER)

    monkeypatch.setattr(ues, "extract_with_ai", _ai)
    return url, threads, ai_calls


@pytest.mark.parametrize("value", ACCEPTED_ON_VALUES)
@pytest.mark.parametrize("branch", sorted(_BRANCHES))
def test_w04f_extract_from_url_extractor_runs_on_the_price_parse_pool(monkeypatch, branch, value):
    """RED at 61585c58: extract_from_url calls its extractor (each builds a soup) inline on the
    event loop in both flag states. Under every accepted flag value (true|1|yes|on; F10 folded
    in) the extractor must run on the price-parse pool. The page's structured data is
    complete, so extract_with_ai is never reached."""
    monkeypatch.setenv(FLAG, value)
    _url, _name, page, _n, title, price = _BRANCHES[branch]
    url, threads, ai_calls = _arm_extract_from_url(monkeypatch, branch, page)

    result = asyncio.run(ues.extract_from_url(url))

    assert result.get("success") is True, result
    assert result["product"]["full_name"] == title and result["product"]["price"]["amount"] == price, (
        "precondition: the %s fixture must extract (%r, %r), got %r" % (branch, title, price, result)
    )
    assert ai_calls == [], "precondition: structured data is complete, AI must not run"
    assert threads, "precondition: the %s extractor must run" % branch
    assert all(n.startswith("price-parse") for n in threads), (
        "W0-4f: %s=%r, extract_from_url ran %s's extractor on thread(s) %r; it must run on the "
        "price-parse pool" % (FLAG, value, branch, threads)
    )


@pytest.mark.parametrize("branch", sorted(_BRANCHES))
def test_w04f_extract_from_url_flag_off_extractor_inline_on_main_thread(monkeypatch, branch):
    """PIN: flag OFF (unset) the extractor runs inline on MainThread over the whole body and
    no price-parse pool is ever built."""
    _url, _name, page, _n, title, price = _BRANCHES[branch]
    url, threads, ai_calls = _arm_extract_from_url(monkeypatch, branch, page)

    result = asyncio.run(ues.extract_from_url(url))

    assert result.get("success") is True and result["product"]["full_name"] == title, result
    assert ai_calls == []
    assert threads == ["MainThread"], threads
    assert _price_parse_pools() == [], _price_parse_pools()


@pytest.mark.parametrize("arm", ["structured", "needs_ai"])
@pytest.mark.parametrize("branch", sorted(_BRANCHES))
def test_w04f_extract_from_url_result_identical_flag_on_vs_off(monkeypatch, branch, arm):
    """PIN: extract_from_url's result is the same JSON (sort_keys) with the flag unset and ON,
    for each branch, with complete structured data and with a page that needs the (stubbed,
    deterministic) AI extraction."""
    _url, _name, page, page_no_price, _t, _p = _BRANCHES[branch]
    chosen = page if arm == "structured" else page_no_price
    url, _threads, ai_calls = _arm_extract_from_url(monkeypatch, branch, chosen)
    off = asyncio.run(ues.extract_from_url(url))
    monkeypatch.setenv(FLAG, "true")
    on = asyncio.run(ues.extract_from_url(url))

    assert off.get("success") is True, off
    if arm == "needs_ai":
        assert len(ai_calls) == 2 and off["product"]["price"]["amount"] == 42.5, (ai_calls, off)
    else:
        assert ai_calls == [], ai_calls
    assert json.dumps(on, sort_keys=True) == json.dumps(off, sort_keys=True), (
        "W0-4f: %s/%s flag ON %r != flag OFF %r" % (branch, arm, on, off)
    )


def _arm_generic_len_recorder(monkeypatch, body, extractor_result):
    """Generic branch; fetch_page returns ``body``; the generic extractor is replaced by a stub
    recording len(html); extract_with_ai records len(html)."""
    async def _fetch(u):
        return body

    monkeypatch.setattr(ues, "fetch_page", _fetch)
    seen = []

    def _stub(html, u):
        seen.append(len(html))
        return dict(extractor_result)

    monkeypatch.setattr(ues, "extract_generic_data", _stub)
    ai_seen = []

    async def _ai(u, html, retailer):
        ai_seen.append(len(html))
        return dict(_AI_ANSWER)

    monkeypatch.setattr(ues, "extract_with_ai", _ai)
    return seen, ai_seen


@pytest.mark.parametrize("size", SIZES)
def test_w04f_extract_from_url_caps_the_parse_input_under_the_flag(monkeypatch, size):
    """RED at 61585c58 for the rows past the cap (3,000,001 and 3,500,000: the extractor gets
    the whole body); the rows at or below the cap (2,999,999 and 3,000,000) are boundary PINs,
    green at 61585c58. Flag ON the extractor's input is exactly min(len, 3,000,000)."""
    monkeypatch.setenv(FLAG, "true")
    seen, _ai_seen = _arm_generic_len_recorder(
        monkeypatch, _numbered_body(size), {"title": "T W04F", "price": 5.0},
    )

    result = asyncio.run(ues.extract_from_url(_GENERIC_URL))

    assert result.get("success") is True, result
    assert seen == [min(size, CAP)], (
        "W0-4f: flag ON, a %d-char page handed the extractor %r chars; the parse input must "
        "be capped at %d" % (size, seen, CAP)
    )


@pytest.mark.parametrize("size", SIZES)
def test_w04f_extract_from_url_flag_off_parses_the_whole_body(monkeypatch, size):
    """PIN (F5b): flag OFF the extractor receives the whole body at every size."""
    seen, _ai_seen = _arm_generic_len_recorder(
        monkeypatch, _numbered_body(size), {"title": "T W04F", "price": 5.0},
    )
    result = asyncio.run(ues.extract_from_url(_GENERIC_URL))
    assert result.get("success") is True, result
    assert seen == [size], seen


def test_w04f_extract_with_ai_receives_capped_html_on_and_whole_body_off(monkeypatch):
    """RED at 61585c58 (the flag-ON half: extract_with_ai receives 3,500,000 chars). A page the
    extractor cannot price (so extract_with_ai runs): flag ON the SAME capped html (3,000,000
    chars) reaches extract_with_ai; flag OFF the whole 3,500,000-char body does."""
    size = 3_500_000
    seen, ai_seen = _arm_generic_len_recorder(monkeypatch, _numbered_body(size), {})
    off = asyncio.run(ues.extract_from_url(_GENERIC_URL))
    assert off.get("success") is True and seen == [size] and ai_seen == [size], (seen, ai_seen)

    monkeypatch.setenv(FLAG, "true")
    del seen[:], ai_seen[:]
    on = asyncio.run(ues.extract_from_url(_GENERIC_URL))

    assert on.get("success") is True, on
    assert ai_seen == [CAP], (
        "W0-4f: flag ON, extract_with_ai received %r chars; it must receive the same capped "
        "html the extractor parsed (%d)" % (ai_seen, CAP)
    )


@pytest.mark.parametrize("flag_value", [None, "true"], ids=["unset", "true"])
def test_w04f_extract_from_url_honours_a_monkeypatched_extractor_in_both_flag_states(
    monkeypatch, flag_value,
):
    """PIN: ``monkeypatch.setattr(ues, 'extract_generic_data', fake)`` is what runs, flag ON
    and OFF (the extractor is a module global resolved at CALL time; kills an import-time
    alias)."""
    _set_flag(monkeypatch, flag_value)

    async def _fetch(u):
        return _GENERIC_PAGE

    monkeypatch.setattr(ues, "fetch_page", _fetch)
    calls = []

    def fake(html, u):
        calls.append(u)
        return {"title": "Fake W04F Title", "price": 7.0, "currency": "BHD"}

    monkeypatch.setattr(ues, "extract_generic_data", fake)

    result = asyncio.run(ues.extract_from_url(_GENERIC_URL))

    assert calls == [_GENERIC_URL], calls
    assert result["product"]["full_name"] == "Fake W04F Title", result
    assert result["product"]["price"]["amount"] == 7.0, result


def test_w04f_extractor_exception_propagates_with_the_same_type_in_both_flag_states(monkeypatch):
    """PIN: a ValueError raised inside the extractor surfaces from extract_from_url as the same
    ValueError (same message) with the flag unset and ON (run_parse_offloaded re-raises the
    worker's exception)."""
    async def _fetch(u):
        return _GENERIC_PAGE

    monkeypatch.setattr(ues, "fetch_page", _fetch)

    def boom(html, u):
        raise ValueError("w04f extractor boom")

    monkeypatch.setattr(ues, "extract_generic_data", boom)
    with pytest.raises(ValueError, match="^w04f extractor boom$"):
        asyncio.run(ues.extract_from_url(_GENERIC_URL))
    monkeypatch.setenv(FLAG, "true")
    with pytest.raises(ValueError, match="^w04f extractor boom$"):
        asyncio.run(ues.extract_from_url(_GENERIC_URL))


@pytest.mark.parametrize("site", ["extract_from_url"])
def test_w04ef_new_sites_resolve_price_service_through_the_package_attribute(monkeypatch, site):
    """KILL (fixer-3, adversary N5; Fable ruling R2). Flag ON, the NEW offload site resolves
    price_service through the PACKAGE ATTRIBUTE at call time
    (``from app.services import price_service as _w04_ps``), exactly as scs's existing
    offload sites do, so production and tests cannot diverge under the #185 sys.modules
    re-import class. The package attribute ``app.services.price_service`` is replaced by a
    stub (sys.modules keeps the real module): the stub's run_parse_offloaded and its
    PRICE_FETCH_MAX_BYTES = 1234 must be what runs. Kills the
    ``from app.services.price_service import PRICE_FETCH_MAX_BYTES, run_parse_offloaded`` form
    (it resolves sys.modules: the real pool runs, the stub records nothing, the cap is 3 MB).
    The lazy_bh_pdp_backfill row left with Fable R11 (that site no longer offloads; its
    pool-free pin is test_w04e2_flag_on_backfill_never_reaches_the_price_parse_pool)."""
    monkeypatch.setenv(FLAG, "true")
    package = importlib.import_module("app.services")
    real = _ps()
    calls = []

    async def _recording(fn, *args, **kwargs):
        calls.append(fn)
        return fn(*args, **kwargs)

    stub = types.SimpleNamespace(PRICE_FETCH_MAX_BYTES=1234, run_parse_offloaded=_recording)
    if site == "extract_from_url":
        seen, _ai_seen = _arm_generic_len_recorder(
            monkeypatch, _numbered_body(5_000), {"title": "T W04F", "price": 5.0},
        )
        monkeypatch.setattr(package, "price_service", stub)
        result = asyncio.run(ues.extract_from_url(_GENERIC_URL))
        assert result.get("success") is True, result
        assert seen == [1234], (
            "W0-4f: extract_from_url capped the parse input at %r chars; the cap must be read "
            "from the package attribute app.services.price_service (stub cap 1234)" % (seen,)
        )
    assert len(calls) == 1, (
        "W0-4f: flag ON, %s submitted %d job(s) to the package attribute's "
        "run_parse_offloaded; it must resolve price_service via ``from app.services import "
        "price_service`` at call time (R2), never via sys.modules" % (site, len(calls))
    )
    assert importlib.import_module("app.services.price_service") is real
    assert _price_parse_pools() == [], "the real price-parse pool ran: %r" % (_price_parse_pools(),)


@pytest.mark.parametrize("flag_value", [None, "false"], ids=["unset", "false"])
@pytest.mark.parametrize("branch", sorted(_BRANCHES))
def test_w04f_flag_off_never_reaches_run_parse_offloaded_from_extract_from_url(
    monkeypatch, branch, flag_value,
):
    """PIN: flag OFF, extract_from_url makes ZERO calls to price_service.run_parse_offloaded
    and its extractor runs on MainThread (kills an unconditional offload)."""
    _set_flag(monkeypatch, flag_value)
    spy_calls = []

    async def _spy(fn, *args, **kwargs):
        spy_calls.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr(_ps(), "run_parse_offloaded", _spy)
    _url, _name, page, _n, title, _p = _BRANCHES[branch]
    url, threads, _ai_calls = _arm_extract_from_url(monkeypatch, branch, page)

    result = asyncio.run(ues.extract_from_url(url))

    assert result.get("success") is True and result["product"]["full_name"] == title, result
    assert spy_calls == [], spy_calls
    assert threads == ["MainThread"], threads


# ===========================================================================
# W0-4g: pool instrumentation
# ===========================================================================


def _require_stats_fn():
    fn = getattr(_ps(), "price_parse_pool_stats", None)
    if fn is None:
        pytest.fail(
            "W0-4g: price_service has no price_parse_pool_stats(); nothing exposes the "
            "price-parse pool's queue depth / waiters for the canary (behaviour absent)"
        )
    return fn


def _stub_fetch_page_price_parse(monkeypatch):
    async def _same_site(url, domain, **kwargs):
        return "<html><body>stub page for W0-4g</body></html>"

    def _extract(html, product_name, currency, domain, url, **kwargs):
        return {"amount": 45.0, "currency": "BHD", "retailer": domain, "url": url,
                "title": _PRODUCT_NAME, "estimated": False, "source_method": "page_scrape"}

    monkeypatch.setattr(_ps(), "curl_fetch_html_same_site", _same_site)
    monkeypatch.setattr(_ps(), "extract_price_from_html", _extract)


def _one_flagged_parse(monkeypatch):
    """ONE flagged parse through a real offload site (fetch_page_price), building the pool."""
    monkeypatch.setenv(FLAG, "true")
    _stub_fetch_page_price_parse(monkeypatch)
    result = asyncio.run(_ps().fetch_page_price(_URL, _PRODUCT_NAME, "BHD"))
    assert result and result.get("amount") == 45.0, result
    assert _price_parse_pools(), "precondition: a flagged parse must build the price-parse pool"


# What the design yields after one uncontended flagged parse with the default pool size.
# peak_waiting is 0 (Fable ruling R1): ``waiting`` counts only a job BLOCKED on the
# semaphore (sem.locked() right before acquire), so one uncontended parse never waits;
# peak_waiting >= 1 on /health means queueing happened.
_AFTER_ONE_PARSE = {"workers": 4, "queued": 0, "jobs_total": 1, "waiting": 0, "running": 0,
                    "peak_waiting": 0, "peak_running": 1}


def test_w04g_pool_stats_is_none_until_the_pool_is_built(monkeypatch):
    """RED at 61585c58 (price_parse_pool_stats does not exist). With no pool built (fresh, and
    after a flag-OFF parse) it returns None; it never builds the pool itself."""
    fn = _require_stats_fn()
    assert fn() is None, "W0-4g: no pool exists yet, stats must be None, got %r" % (fn(),)
    _stub_fetch_page_price_parse(monkeypatch)
    asyncio.run(_ps().fetch_page_price(_URL, _PRODUCT_NAME, "BHD"))  # flag OFF: inline
    assert fn() is None, "after a flag-OFF parse stats must still be None, got %r" % (fn(),)
    assert _price_parse_pools() == [], "price_parse_pool_stats() built the pool"


def test_w04g_pool_stats_after_one_flagged_parse(monkeypatch):
    """RED at 61585c58 (price_parse_pool_stats does not exist). After ONE flagged parse on a
    fresh pool: exactly _AFTER_ONE_PARSE (workers = PRICE_PARSE_MAX_WORKERS default 4, the
    executor's own queue 0, one job, nothing waiting or running, peak_waiting 0, peak_running 1)."""
    fn = _require_stats_fn()
    _one_flagged_parse(monkeypatch)
    assert fn() == _AFTER_ONE_PARSE, "W0-4g: stats after one flagged parse: %r, expected %r" % (
        fn(), _AFTER_ONE_PARSE,
    )


def test_w04g_pool_stats_is_a_pure_read_returning_a_fresh_dict(monkeypatch):
    """KILL (fixer-3, adversary N26). price_parse_pool_stats() is a PURE read (spec 3a): it
    never writes the module counters and returns a fresh dict each call. Kills the stats fn
    returning the shared _PRICE_PARSE_STATS dict after writing workers/queued into it (the
    module counters gain the two keys, and a caller's write lands in the live counters).
    Production-equivalent for /health's serialization; pinned because the spec says pure."""
    fn = _require_stats_fn()
    _one_flagged_parse(monkeypatch)
    counters_before = dict(_ps()._PRICE_PARSE_STATS)
    first = fn()
    assert set(_ps()._PRICE_PARSE_STATS) == _STATS_KEYS, (
        "W0-4g: price_parse_pool_stats() wrote into the module counters: %r"
        % (sorted(_ps()._PRICE_PARSE_STATS),)
    )
    assert first is not _ps()._PRICE_PARSE_STATS, "stats returned the live counter dict"
    first["jobs_total"] = 999
    first["waiting"] = 999
    assert _ps()._PRICE_PARSE_STATS == counters_before, _ps()._PRICE_PARSE_STATS
    assert fn() == _AFTER_ONE_PARSE, fn()


async def _wait_for_stats(fn, predicate, timeout=5.0):
    deadline = time.perf_counter() + timeout
    last = None
    while time.perf_counter() < deadline:
        last = fn()
        if last is not None and predicate(last):
            return dict(last), True
        await asyncio.sleep(0.005)
    return (dict(last) if last else last), False


def test_w04g_pool_stats_peak_waiting_and_running_under_a_saturating_burst(monkeypatch):
    """RED at 61585c58 (price_parse_pool_stats does not exist). Pool size 1
    (PRICE_PARSE_MAX_WORKERS=1), three concurrent offloaded parses blocked on a
    threading.Event: while held, running == 1, waiting == 2 and the executor's own queue is 0
    (the semaphore keeps the other two in asyncio); after release jobs_total == 3,
    peak_waiting == 2, peak_running == 1, waiting == running == 0."""
    fn = _require_stats_fn()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(POOL_ENV, "1")
    release = threading.Event()

    def blocker(i):
        release.wait(10)
        return i

    async def scenario():
        tasks = [asyncio.ensure_future(_ps().run_parse_offloaded(blocker, i)) for i in range(3)]
        try:
            held, ok = await _wait_for_stats(
                fn, lambda s: s["running"] == 1 and s["waiting"] == 2,
            )
        finally:
            release.set()
        results = await asyncio.gather(*tasks)
        return held, ok, results, fn()

    held, ok, results, final = asyncio.run(scenario())

    assert results == [0, 1, 2], results
    assert ok, "W0-4g: never observed running == 1 and waiting == 2 while held; last %r" % (held,)
    assert held["queued"] == 0 and held["workers"] == 1, held
    assert final["jobs_total"] == 3 and final["peak_waiting"] == 2 and final["peak_running"] == 1, (
        final
    )
    assert final["waiting"] == 0 and final["running"] == 0 and final["queued"] == 0, final


def test_w04g_cancelled_waiter_never_leaks_a_waiting_count(monkeypatch):
    """RED at 61585c58 (price_parse_pool_stats does not exist). Pool size 1: job A holds the
    only slot, job B waits on the semaphore and is cancelled. B must leave waiting at 0, never
    count as a job, and never release a slot it did not take: afterwards two new blocked jobs
    still run one at a time (running 1, waiting 1, the executor queue 0)."""
    fn = _require_stats_fn()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(POOL_ENV, "1")
    first, second = threading.Event(), threading.Event()

    def blocker(ev):
        ev.wait(10)
        return "done"

    async def scenario():
        snaps = {}
        a = c = d = None
        ok_a = ok_b = ok_p = False
        try:
            a = asyncio.ensure_future(_ps().run_parse_offloaded(blocker, first))
            snaps["a_running"], ok_a = await _wait_for_stats(fn, lambda s: s["running"] == 1)
            b = asyncio.ensure_future(_ps().run_parse_offloaded(blocker, first))
            snaps["b_waiting"], ok_b = await _wait_for_stats(fn, lambda s: s["waiting"] == 1)
            b.cancel()
            try:
                await b
            except asyncio.CancelledError:
                pass
            snaps["after_cancel"] = dict(fn())
            first.set()
            await a
            snaps["after_a"] = dict(fn())
            c = asyncio.ensure_future(_ps().run_parse_offloaded(blocker, second))
            d = asyncio.ensure_future(_ps().run_parse_offloaded(blocker, second))
            snaps["probe"], ok_p = await _wait_for_stats(
                fn, lambda s: s["running"] + s["waiting"] == 2 and s["jobs_total"] >= 2,
            )
            await asyncio.sleep(0.05)
            snaps["probe_settled"] = dict(fn())
        finally:
            first.set()
            second.set()
        await asyncio.gather(*[t for t in (a, c, d) if t is not None], return_exceptions=True)
        snaps["final"] = dict(fn())
        return snaps, (ok_a, ok_b, ok_p)

    snaps, oks = asyncio.run(scenario())

    assert all(oks), "precondition: the scenario states were not all reached: %r %r" % (oks, snaps)
    ac = snaps["after_cancel"]
    assert ac["waiting"] == 0 and ac["running"] == 1 and ac["jobs_total"] == 1, (
        "W0-4g: a cancelled waiter leaked into the counters: %r" % (ac,)
    )
    aa = snaps["after_a"]
    assert aa["waiting"] == 0 and aa["running"] == 0 and aa["jobs_total"] == 1, aa
    pr = snaps["probe_settled"]
    assert pr["running"] == 1 and pr["waiting"] == 1 and pr["queued"] == 0, (
        "W0-4g: after the cancelled waiter, two new jobs on a size-1 pool ran %r; the "
        "cancelled waiter must not have released a slot it never took" % (pr,)
    )
    fin = snaps["final"]
    assert fin["waiting"] == 0 and fin["running"] == 0 and fin["jobs_total"] == 3, fin


def test_w04g_a_raising_parse_gives_its_slot_back_and_leaves_running_at_0(monkeypatch):
    """KILL (fixer, adversary ADV_A / ADV_B). Pool size 1: a parse whose function raises
    ValueError re-raises it from run_parse_offloaded, leaves running == waiting == 0 and
    returns its only semaphore slot, so the NEXT parse on the same loop runs (bounded by a
    2 s wait_for). Kills: the slot released only on success (ADV_B: the next parse blocks
    forever, one leaked slot per extractor exception) and the running decrement outside the
    finally (ADV_A: running stays 1). The R-W04 cancel pins bound concurrency from ABOVE, so a
    leaked slot (fewer parses) can never turn them red; this pin bounds it from below."""
    fn = _require_stats_fn()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(POOL_ENV, "1")

    def boom():
        raise ValueError("W0-4g extractor failure")

    async def scenario():
        with pytest.raises(ValueError):
            await _ps().run_parse_offloaded(boom)
        after_exc = dict(fn())
        try:
            nxt = await asyncio.wait_for(_ps().run_parse_offloaded(lambda: 7), 2.0)
        except asyncio.TimeoutError:
            nxt = "TIMEOUT: the next parse never got the slot; last stats %r" % (fn(),)
        return after_exc, nxt, dict(fn())

    after_exc, nxt, final = asyncio.run(scenario())

    assert after_exc["running"] == 0 and after_exc["waiting"] == 0, (
        "W0-4g: a raising parse leaked into the counters: %r" % (after_exc,)
    )
    assert after_exc["jobs_total"] == 1, after_exc
    assert nxt == 7, (
        "W0-4g: after one raising parse on a size-1 pool the next parse did not run: %r "
        "(the semaphore slot must be released in a finally)" % (nxt,)
    )
    assert final["running"] == 0 and final["waiting"] == 0 and final["jobs_total"] == 2, final


def test_w04g_cancelled_running_parse_releases_its_slot_and_shows_as_queued(monkeypatch):
    """KILL (fixer, adversary ADV_A / ADV_B / ADV_C and the '`queued` is 0 by construction'
    defect). Pool size 1: job A's parse is RUNNING on the only pool thread when its await is
    cancelled (the shape of a wait_for cap firing). As with ``async with sem``, the cancel
    releases A's slot and decrements running while A's thread stays busy; job B then acquires
    at once (waiting 0), is counted running, and its work item sits in the EXECUTOR queue:
    {running: 1, waiting: 0, queued: 1}, and it STAYS so until A's thread frees up. So a
    queued > 0 that persists across /health polls means orphaned parses from cancelled awaits
    are holding pool threads (a single sample can also catch the transient queued 1 of an
    ordinary semaphore hand-off, measured with no cancel at 2 and 4 workers). Kills: the slot kept on
    cancel (ADV_B: B blocks, waiting 1), running not decremented on cancel (ADV_A: running
    2), and a hard-coded queued (ADV_C: queued 0)."""
    fn = _require_stats_fn()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(POOL_ENV, "1")
    a_started, a_release, b_release = threading.Event(), threading.Event(), threading.Event()

    def job_a():
        a_started.set()
        a_release.wait(10)
        return "a"

    def job_b():
        b_release.wait(10)
        return "b"

    async def scenario():
        snaps = {}
        b = None
        ok_b = False
        try:
            a = asyncio.ensure_future(_ps().run_parse_offloaded(job_a))
            deadline = time.perf_counter() + 5.0
            while not a_started.is_set() and time.perf_counter() < deadline:
                await asyncio.sleep(0.005)
            snaps["a_started"] = a_started.is_set()
            snaps["a_running"] = dict(fn())
            a.cancel()
            try:
                await a
            except asyncio.CancelledError:
                pass
            snaps["after_cancel"] = dict(fn())
            b = asyncio.ensure_future(_ps().run_parse_offloaded(job_b))
            snaps["orphan"], ok_b = await _wait_for_stats(
                fn, lambda s: s["queued"] == 1 and s["running"] == 1 and s["waiting"] == 0,
                timeout=3.0,
            )
            snaps["orphan_latest"] = dict(fn())
        finally:
            a_release.set()
            b_release.set()
        try:
            snaps["b_result"] = await asyncio.wait_for(b, 5.0) if b is not None else None
        except asyncio.TimeoutError:
            snaps["b_result"] = "TIMEOUT: job B never got a slot; last stats %r" % (fn(),)
        snaps["final"] = dict(fn())
        return snaps, ok_b

    snaps, ok_b = asyncio.run(scenario())

    assert snaps["a_started"], "precondition: job A never started on the pool thread"
    assert snaps["a_running"]["running"] == 1 and snaps["a_running"]["queued"] == 0, snaps
    ac = snaps["after_cancel"]
    assert ac["running"] == 0 and ac["waiting"] == 0 and ac["jobs_total"] == 1, (
        "W0-4g: cancelling an await whose parse was running must release its slot and "
        "decrement running (the async-with-sem contract): %r" % (ac,)
    )
    assert ok_b, (
        "W0-4g: after A's await was cancelled mid-parse, job B must acquire the released slot "
        "at once and queue in the executor behind A's orphaned parse ({running: 1, waiting: 0, "
        "queued: 1}); observed %r" % (snaps["orphan_latest"],)
    )
    assert snaps["b_result"] == "b", snaps
    fin = snaps["final"]
    assert fin == {"workers": 1, "queued": 0, "jobs_total": 2, "waiting": 0, "running": 0,
                   "peak_waiting": 0, "peak_running": 1}, fin


def _health_body():
    response = TestClient(app_main.app).get("/health")
    assert response.status_code == 200, response.status_code
    return response.json()


def _without_lag(body):
    return {k: v for k, v in body.items() if not k.startswith("loop_lag")}


def test_w04g_health_has_no_price_parse_pool_key_before_the_pool_exists():
    """PIN: with no pool built, /health carries no 'price_parse_pool' key and keeps status /
    message byte-unchanged (flag OFF /health is byte-identical to 61585c58)."""
    body = _health_body()
    assert "price_parse_pool" not in body, body
    assert body.get("status") == "healthy" and body.get("message") == "Qaren API is running", body
    assert set(body) == {"status", "message", "loop_lag_ms", "loop_lag_max_ms",
                         "loop_lag_max_60s_ms"}, sorted(body)


def test_w04g_health_carries_price_parse_pool_after_a_flagged_parse(monkeypatch):
    """RED at 61585c58 (measured: the key is absent even after the pool is built). Once a
    flagged parse has built the pool, /health carries 'price_parse_pool' with the dict of
    price_parse_pool_stats() (the shape of G2)."""
    _one_flagged_parse(monkeypatch)
    body = _health_body()
    assert "price_parse_pool" in body, (
        "W0-4g: the price-parse pool exists but /health has no 'price_parse_pool' key "
        "(keys %r); the canary cannot watch the pool's queue depth" % (sorted(body),)
    )
    assert body["price_parse_pool"] == _AFTER_ONE_PARSE, body["price_parse_pool"]
    assert body.get("status") == "healthy" and body.get("message") == "Qaren API is running"


_STATS_ERRORS = {
    "AttributeError": (AttributeError, "'ThreadPoolExecutor' object has no attribute '_work_queue'"),
    "TypeError": (TypeError, "'NoneType' object is not subscriptable"),
    "KeyError": (KeyError, "jobs_total"),
    "RuntimeError": (RuntimeError, "dictionary changed size during iteration"),
    "ValueError": (ValueError, "stats unavailable"),
}


@pytest.mark.parametrize("error", sorted(_STATS_ERRORS))
def test_w04g_health_survives_a_raising_pool_stats_fn(monkeypatch, error):
    """KILL (fixer, adversary ADV_D; fixer-3, adversary N1). The pool exists but
    price_parse_pool_stats raises (realistic triggers: the private ThreadPoolExecutor attrs
    _max_workers / _work_queue change shape in a future Python, or a stats dict mutated
    mid-read): price_parse_pool_snapshot() returns {} and /health still answers 200 with the
    base keys only, for EVERY Exception subclass. Kills the snapshot's try/except removed (the
    exception escapes and /health fails) and the catch narrowed to one type (N1: except
    AttributeError lets the other four rows escape)."""
    snapshot = getattr(app_main, "price_parse_pool_snapshot", None)
    if snapshot is None:
        pytest.fail("W0-4g: app.main has no price_parse_pool_snapshot() (behaviour absent)")
    _one_flagged_parse(monkeypatch)

    def raising_stats():
        exc_type, message = _STATS_ERRORS[error]
        raise exc_type(message)

    monkeypatch.setattr(_ps(), "price_parse_pool_stats", raising_stats)
    try:
        snap = snapshot()
    except Exception as exc:  # noqa: BLE001 - the pin reports the escape as a failure
        pytest.fail("W0-4g: price_parse_pool_snapshot() let the stats error escape: %r" % (exc,))
    assert snap == {}, snap
    body = _health_body()
    assert set(body) == {"status", "message", "loop_lag_ms", "loop_lag_max_ms",
                         "loop_lag_max_60s_ms"}, sorted(body)
    assert body.get("status") == "healthy" and body.get("message") == "Qaren API is running"


def _function_body_source(fn):
    source = inspect.getsource(fn)
    return source, (source.split("\n", 1)[1] if "\n" in source else "")


def _import_nodes(fn):
    tree = ast.parse(inspect.getsource(fn).lstrip())
    return [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]


def test_w04g_health_handler_stays_a_pure_dict_read():
    """PIN: the /health handler stays a pure dict read (the checks of
    tests/test_health_loop_lag.py::test_health_handler_is_a_pure_dict_read) plus no import
    statement inside it; when price_parse_pool_snapshot exists (green), it too carries no
    import statement and no await (it must read sys.modules, never trigger an import)."""
    source, body = _function_body_source(app_main.health_check)
    assert "await " not in body, source
    for forbidden in ("asyncio.sleep", "requests.", "httpx.", "get_cached", "execute("):
        assert forbidden not in body, (forbidden, source)
    assert "import " not in body, "the /health handler carries an import statement:\n" + source
    assert _import_nodes(app_main.health_check) == []
    snapshot = getattr(app_main, "price_parse_pool_snapshot", None)
    if snapshot is not None:
        snap_source, snap_body = _function_body_source(snapshot)
        assert _import_nodes(snapshot) == [], (
            "price_parse_pool_snapshot must not import (read sys.modules):\n" + snap_source
        )
        assert "await " not in snap_body, snap_source


def test_w04g_pool_build_logs_one_grep_stable_info_line(monkeypatch, caplog):
    """RED at 61585c58 (no such line). Building the pool logs exactly ONE INFO record
    '[PRICE-PARSE] pool built workers=4' (grep-stable); a second flagged parse on the built
    pool logs nothing more."""
    pattern = re.compile(r"^\[PRICE-PARSE\] pool built workers=(\d+)$")
    with caplog.at_level(logging.INFO, logger=_ps().logger.name):
        _one_flagged_parse(monkeypatch)
        after_first = [r for r in caplog.records if pattern.match(r.getMessage())]
        asyncio.run(_ps().fetch_page_price(_URL + "?n=2", _PRODUCT_NAME, "BHD"))
        after_second = [r for r in caplog.records if pattern.match(r.getMessage())]
    assert len(after_first) == 1, (
        "W0-4g: building the price-parse pool logged %d '[PRICE-PARSE] pool built workers=N' "
        "records; expected exactly 1" % len(after_first)
    )
    rec = after_first[0]
    assert rec.levelno == logging.INFO and pattern.match(rec.getMessage()).group(1) == "4", (
        rec.levelname, rec.getMessage(),
    )
    assert len(after_second) == 1, "a second parse on the built pool logged the line again (%d)" % (
        len(after_second),
    )


def test_w04g_flag_off_health_body_byte_identical_after_off_path_parses(monkeypatch):
    """PIN: flag OFF, parses through _extract_price_from_html_maybe_offloaded and
    extract_from_url leave /health (minus the loop-lag numbers) unchanged and without the
    'price_parse_pool' key; no pool is built."""
    before = _without_lag(_health_body())
    page = """<html><head><title>%s</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
"name":"%s","brand":{"@type":"Brand","name":"Testbrand"},
"offers":{"@type":"Offer","price":"45.000","priceCurrency":"BHD",
"availability":"https://schema.org/InStock"}}</script></head><body></body></html>""" % (
        _PRODUCT_NAME, _PRODUCT_NAME,
    )
    priced = asyncio.run(scs._extract_price_from_html_maybe_offloaded(
        page, _PRODUCT_NAME, "BHD", _DOMAIN, _URL,
    ))
    assert priced and priced.get("amount") == 45.0, priced
    url, _threads, _ai = _arm_extract_from_url(monkeypatch, "generic", _GENERIC_PAGE)
    assert asyncio.run(ues.extract_from_url(url)).get("success") is True
    after = _health_body()

    assert "price_parse_pool" not in after, after
    assert json.dumps(_without_lag(after), sort_keys=True) == json.dumps(before, sort_keys=True)
    assert _price_parse_pools() == [], _price_parse_pools()


# ===========================================================================
# W0-4g: the r1 adversary's four test-side gaps (KILL rows)
# ===========================================================================


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


def _render_leg(monkeypatch, leg, html):
    """Arm the firecrawl / scrapedo render leg over ``html``; the parse records len(html)."""
    if leg == "firecrawl":
        async def _scrape(url):
            return html, 200

        monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: True)
        monkeypatch.setattr(scs.firecrawl_service, "scrape_page_with_status", _scrape)
        make = lambda: scs._firecrawl_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)  # noqa: E731
    else:
        async def _render(url):
            return html, 200, 5

        monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: True)
        monkeypatch.setattr(scs.scrapedo_service, "render_page_with_status", _render)
        monkeypatch.setattr(scs, "validate_scrape_url", lambda url: True)
        make = lambda: scs._scrapedo_scraper(_URL, _PRODUCT_NAME, "BHD", _DOMAIN)  # noqa: E731
    _stub_render_gates(monkeypatch)
    _provider_attempts_sink(monkeypatch)
    seen = []

    def stub(html_in, product_name, currency, domain, url, **kwargs):
        seen.append(len(html_in))
        return {"amount": 45.0, "currency": "BHD", "retailer": domain, "url": url,
                "title": _PRODUCT_NAME, "estimated": False, "source_method": "page_scrape"}

    monkeypatch.setattr(scs, "extract_price_from_html", stub)
    return make, seen


@pytest.mark.parametrize("value", ["1", "yes", "on", " TRUE "],
                         ids=["1", "yes", "on", "padded-TRUE"])
@pytest.mark.parametrize("site", ["curl", "firecrawl", "scrapedo"])
def test_w04g_curl_cap_and_render_caps_fire_under_every_accepted_flag_value(
    monkeypatch, site, value,
):
    """KILL N_curl_cap_flag_true_only_literal (PIN, green at 61585c58): the curl_fetch_html cap
    and BOTH render-leg caps fire under every accepted flag spelling, not only 'true'. A
    3,500,000-char body is cut to exactly 3,000,000 chars."""
    monkeypatch.setenv(FLAG, value)
    body = _numbered_body(3_500_000)
    if site == "curl":
        _patch_curl_get(monkeypatch, _BigResp(200, body))
        html = asyncio.run(_ps().curl_fetch_html(_URL))
        assert html is not None and html == body[:CAP], (
            "%s=%r: curl_fetch_html returned %s chars; the cap must fire at %d"
            % (FLAG, value, None if html is None else len(html), CAP)
        )
    else:
        make, seen = _render_leg(monkeypatch, site, body)
        result = asyncio.run(make())
        assert result and result.get("value") == 45.0, result
        assert seen == [CAP], "%s=%r: the %s leg handed the parse %r chars; cap %d" % (
            FLAG, value, site, seen, CAP,
        )


def _long_ai_page():
    paras = "".join(
        "<p>Paragraph %03d of the W04G long page: Testbrand Aqua EDP detail text.</p>" % i
        for i in range(150)
    )
    return (
        "<html><head><title>Testbrand Aqua Long Page | Store</title><script>var x=1;</script>"
        "<style>p{}</style></head><body><nav>menu</nav>" + paras + "<footer>foot</footer>"
        "</body></html>"
    )


def test_w04g_extract_with_ai_prompt_identical_on_vs_off_past_the_4000_char_truncation(monkeypatch):
    """KILL N_ues_text_trunc_on (PIN, green at 61585c58): a page whose visible text is >= 6,000
    chars, so the 4,000-char truncation of the prompt's content slot is inside the pinned
    region. The captured prompts are byte-equal flag OFF vs ON and the content slot is exactly
    4,000 chars in both."""
    import bs4

    page = _long_ai_page()
    visible = bs4.BeautifulSoup(page, "html.parser").get_text(separator="\n", strip=True)
    assert len(visible) >= 6000, "precondition: visible text is only %d chars" % len(visible)

    class _Msg:
        content = '{"title": "Testbrand Aqua", "price": 24.89, "currency": "BHD"}'

    class _Choice:
        message = _Msg()

    class _Response:
        choices = [_Choice()]

    prompts = []

    async def _guarded(client, **kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return _Response()

    monkeypatch.setattr(ues, "get_client", lambda: object())
    monkeypatch.setattr(ues, "_llm_breaker", types.SimpleNamespace(guarded_llm_create=_guarded))
    retailer = {"name": "Example", "region": "bahrain", "currency": "BHD", "key": "example"}

    off_result = asyncio.run(ues.extract_with_ai(_URL, page, retailer))
    monkeypatch.setenv(FLAG, "true")
    on_result = asyncio.run(ues.extract_with_ai(_URL, page, retailer))

    assert off_result == on_result and off_result.get("price") == 24.89
    assert len(prompts) == 2, prompts
    slots = []
    for prompt in prompts:
        content = prompt.split("Page Content (truncated):\n", 1)[1]
        content = content.split("\n\nExtract and return ONLY valid JSON:", 1)[0]
        slots.append(content)
    assert [len(s) for s in slots] == [4000, 4000], (
        "the prompt's content slot must be exactly 4,000 chars flag OFF and ON, got %r"
        % ([len(s) for s in slots],)
    )
    assert slots[0].startswith("Testbrand Aqua Long Page | Store\nParagraph 000"), slots[0][:120]
    assert prompts[1] == prompts[0], "flag ON sent a different prompt than flag OFF past 4,000 chars"


# --- the harness (scripts/verify_flag_byte_identity.py) ------------------------------------

_PROBE_FLAG = "ENABLE_W04G_HARNESS_PROBE"


def _live_price_service():
    """The price_service module main() imports at CALL time (issue #185 class: resolve it
    immediately before patching, never at collection)."""
    return importlib.import_module("app.services.price_service")


def _tiny_corpus(tmp_path):
    rows = []
    for i, (url, name) in enumerate([
        ("https://shop-a.example/products/atlas-oud", "Atlas Oud Noir 50ml"),
        ("https://shop-b.example/products/meridian-amber", "Meridian Amber Veil 100ml"),
    ]):
        page = tmp_path / ("w04gpage%d.html" % i)
        page.write_text("<html><head><title>%s</title></head><body></body></html>" % name,
                        encoding="utf-8")
        rows.append({"url": url, "path": str(page), "name": name, "page_currency": "BHD"})
    manifest = tmp_path / "w04gmanifest.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(manifest)


def _install_env_spy(monkeypatch):
    def spy(html, query, currency, domain, url, **kwargs):
        return {"amount": 1.0, "probe": os.environ.get(_PROBE_FLAG), "url": url}

    monkeypatch.setattr(_live_price_service(), "extract_price_from_html", spy)


def _run_main(argv):
    import scripts.verify_flag_byte_identity as vfbi

    try:
        return vfbi.main(argv)
    except SystemExit as exc:
        pytest.fail("verify_flag_byte_identity.main(%r) exited %r" % (argv, exc.code))


@pytest.fixture
def _harness(monkeypatch, tmp_path):
    monkeypatch.setenv(_PROBE_FLAG, "w04g-teardown-sentinel")
    monkeypatch.delenv(_PROBE_FLAG)
    manifest = _tiny_corpus(tmp_path)
    _install_env_spy(monkeypatch)
    base_path = tmp_path / "w04gbase.json"
    assert _run_main(["--corpus", manifest, "--out", str(base_path)]) == 0
    base = json.loads(base_path.read_text(encoding="utf-8"))
    assert len(base["results"]) == 8, "precondition: 2 pages x 2 gates x 2 legs"
    return manifest, base


@pytest.mark.parametrize("shape", ["fewer", "extra"])
def test_w04g_harness_compare_counts_records_missing_on_either_side(
    _harness, tmp_path, capsys, shape,
):
    """KILL N_harness_compare_intersection_only (PIN, green at 61585c58): --compare counts a
    record missing on EITHER side. The other payload with one record fewer -> 'DIFFERING
    RECORDS 1 of 8'; with one EXTRA record -> 'DIFFERING RECORDS 1 of 9'; exit 1 both times."""
    manifest, base = _harness
    other = copy.deepcopy(base)
    if shape == "fewer":
        dropped = other["results"].pop(0)
        expected = "DIFFERING RECORDS 1 of 8"
        named = dropped["url"]
    else:
        added = copy.deepcopy(other["results"][0])
        added["url"] = "https://shop-z.example/products/extra-record"
        other["results"].append(added)
        expected = "DIFFERING RECORDS 1 of 9"
        named = added["url"]
    other_path = tmp_path / ("w04g%s.json" % shape)
    other_path.write_text(json.dumps(other, sort_keys=True, indent=1), encoding="utf-8")
    capsys.readouterr()

    rc = _run_main(["--corpus", manifest, "--compare", str(other_path)])
    out = capsys.readouterr().out

    assert rc == 1, out
    assert "equal=False" in out and expected in out, (
        "--compare against a payload with one record %s must report %r:\n%s"
        % ("fewer" if shape == "fewer" else "extra", expected, out)
    )
    assert named in out and "MISSING" in out, out


def test_w04g_harness_compare_against_a_non_payload_json_is_unequal_and_exits_1(
    _harness, tmp_path, capsys,
):
    """KILL N_harness_compare_whole_payload_not_results (PIN, green at 61585c58): --compare
    against a JSON with no 'results' key ({"foo": 1}) compares this run against NOTHING, never
    against itself: equal=False, all 8 records differ, exit 1."""
    manifest, base = _harness
    other_path = tmp_path / "w04gnotapayload.json"
    other_path.write_text(json.dumps({"foo": 1}), encoding="utf-8")
    capsys.readouterr()

    rc = _run_main(["--corpus", manifest, "--compare", str(other_path)])
    out = capsys.readouterr().out

    assert rc == 1, out
    assert "equal=False" in out and "DIFFERING RECORDS 8 of 8" in out, out
    empty = hashlib.sha256(json.dumps([], sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    assert "other=%s" % empty in out, out
