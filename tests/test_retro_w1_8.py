"""R-W18 RED — retro-fix of W1-8 adapter-drop visibility (units W1-8b / W1-8c /
W1-8d). Spec: the retroactive adversary report for "W1-8 adapter-drop
visibility (PR #143, merge 64f33913, UNFLAGGED)" plus the orchestrator's
binding rulings. LOGGING ONLY, UNFLAGGED: nothing here may change a price or a
return value, so every red test below also asserts the return value the changed
function produces, and the PINS section asserts today's return values directly.

What is RED today and why (each reproduced on the pinned venv at 1c6f6796):

  W1-8b  The three fan-out scrapers (_curl_scraper / _firecrawl_scraper /
         _scrapedo_scraper) catch their own fetch exception and log it at DEBUG
         (prod runs LOG_LEVEL=INFO), so a fan-out where every scraper failed is
         indistinguishable from twelve honest misses, and fan_out's
         failed_count stays 0 for them (probe P1: failed_count=0, zero INFO
         lines). Required: one INFO line per failure,
         `[ADAPTER DROP] fanout:<kind>:<retailer_domain>: ERROR <Type>`, domain
         only, never the URL. And the Tier-1.5 wave loop logs ONE INFO summary
         per wave (completed, failed_count, cancelled_count, elapsed), including
         on its TimeoutError branch with the still-pending count.

  W1-8c  The three consume `except asyncio.TimeoutError` branches (sitemap,
         jsonapi, the _new_adapter_specs loop) are silent (probe P3). Required:
         `[ADAPTER DROP] <family>: CONSUME-BOUND after <bound>s`.
         `_timeout_none` cannot see an inner timeout the adapter swallowed
         (probe P2). Required: `SLOW-MISS after <elapsed>s` when the adapter
         returns None at/after adapter_inner_ceiling() - 0.5 (fast misses and
         hits stay silent). Its TimeoutError branch reports the WRAP timeout for
         a TimeoutError the adapter raised itself 10 ms in (probe P5: "TIMEOUT
         after 10.0s"). Required: `TIMEOUT after <elapsed>s` only when
         elapsed >= timeout - 0.05, else `ERROR TimeoutError (adapter-raised)`.
         Cancellation stays UNLOGGED.

  W1-8d  The ERROR line writes str(exc) verbatim: probe P4 produced a
         200,136-character record with the proxy password and a raw newline.
         Required: `_safe_exc(exc)` — userinfo + query stripped from every
         http(s) URL, newlines -> spaces, truncated to 200 chars.

Every adapter/scraper/fetch here is a STUB. An autouse guard blocks every
non-loopback getaddrinfo/connect and fails the test on any attempt, and points
every proxy variable at a closed loopback port for the C-level (libcurl) path.

Run:
  PYTHONIOENCODING=utf-8 python -m pytest tests/test_retro_w1_8.py -q
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
import contextlib
import logging
import re
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

import app.services.structured_comparison_service as scs
from app.services.adapter_timeouts import adapter_inner_ceiling
from app.services.price_service import fan_out_price_lookup
from app.services.structured_comparison_service import _timeout_none

_SCS_LOGGER = scs.logger.name
_DROP = "[ADAPTER DROP]"


# ---------------------------------------------------------------------------
# Zero-network guard (autouse). Blocks every non-loopback resolve/connect at the
# Python socket layer and records the attempt; the test FAILS on any attempt.
# Proxy variables cover the libcurl path, which does not use Python sockets.
# ---------------------------------------------------------------------------
def _is_loopback(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if host in (None, "", "localhost", "::1"):
        return True
    return str(host).startswith("127.")


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: list = []
    real_gai = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _gai(host, *a, **k):
        if not _is_loopback(host):
            attempts.append(("getaddrinfo", host))
            raise socket.gaierror(-2, "R-W18 test: network blocked")
        return real_gai(host, *a, **k)

    def _host(address):
        return address[0] if isinstance(address, tuple) and address else None

    def _connect(self, address):
        if _host(address) is not None and not _is_loopback(_host(address)):
            attempts.append(("connect", address))
            raise OSError("R-W18 test: network blocked")
        return real_connect(self, address)

    def _connect_ex(self, address):
        if _host(address) is not None and not _is_loopback(_host(address)):
            attempts.append(("connect_ex", address))
            raise OSError("R-W18 test: network blocked")
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(var, "http://127.0.0.1:9")
    yield attempts
    assert attempts == [], f"a test attempted the network: {attempts}"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _scs_info(caplog) -> list[logging.LogRecord]:
    return [
        r for r in caplog.records
        if r.name == _SCS_LOGGER and r.levelno >= logging.INFO
    ]


def _drops(caplog) -> list[str]:
    return [r.getMessage() for r in _scs_info(caplog) if _DROP in r.getMessage()]


def _assert_grep_stable(msg: str) -> None:
    assert "\n" not in msg and "\r" not in msg, (
        f"a drop line must be ONE grep-stable line: {msg!r}"
    )


# Fixed grep tokens (Fable red-gate ruling 3). Every new line must match its
# token EXACTLY (re.fullmatch), so a looser form cannot pass.
_NUM = r"\d+(?:\.\d+)?"


def _fanout_drop_re(kind: str, domain: str, exc_type: str) -> str:
    # `[ADAPTER DROP] fanout:<kind>:<retailer_domain>: ERROR <Type>` + the
    # optional `: <_safe_exc text>` tail.
    return rf"\[ADAPTER DROP\] fanout:{kind}:{re.escape(domain)}: ERROR {exc_type}(?:: .*)?"


_WAVE_SUMMARY_RE = re.compile(
    rf"\[FANOUT\] wave=(curl|render) completed=(\d+) failed=(\d+) cancelled=(\d+) elapsed={_NUM}"
)


# ===========================================================================
# W1-8b — fan-out scraper failures reach INFO under the drop prefix
# ===========================================================================
_URL = "https://www.sharafdg.com/product/apple-iphone-15-128gb?utm_source=x&token=SECRETTOKEN"


@pytest.mark.asyncio
async def test_w18b_curl_scraper_fetch_error_logs_one_info_drop_line_domain_only(
    monkeypatch, caplog
):
    """RED: `_curl_scraper` logs its fetch exception at DEBUG only. Required:
    exactly one INFO `[ADAPTER DROP] fanout:curl:<retailer_domain>: ERROR
    <Type>` line that never carries the URL (path or query).

    SCOPE (R-W18 fixer, adversary row 1): this pins the ESCAPED-exception
    branch only — an exception that gets past fetch_page_price (a parser /
    content-safety bug). A real transport failure never raises here (every
    fetch layer swallows it); that production shape is pinned through the REAL
    stack by test_w18b_real_curl_transport_failure_reaches_one_fetch_fail_line."""
    caplog.set_level(logging.DEBUG, logger=_SCS_LOGGER)

    async def _boom(url, full_name, currency):
        raise RuntimeError("fetch blew up")

    monkeypatch.setattr(scs, "fetch_page_price", _boom)

    result = await scs._curl_scraper(_URL, "Apple iPhone 15 128GB", "BHD", "sharafdg.com")

    assert result is None, "logging only: a failed curl fetch must still return None"
    drops = _drops(caplog)
    assert len(drops) == 1, f"expected exactly one INFO drop line, got {drops}"
    msg = drops[0]
    assert re.fullmatch(_fanout_drop_re("curl", "sharafdg.com", "RuntimeError"), msg), msg
    _assert_grep_stable(msg)
    for info in (r.getMessage() for r in _scs_info(caplog)):
        assert "/product/" not in info and "SECRETTOKEN" not in info and "https://" not in info, (
            f"an INFO line carries the scraped URL (domain only, never the URL): {info!r}"
        )


@pytest.mark.asyncio
async def test_w18b_firecrawl_scraper_fetch_error_logs_one_info_drop_line(
    monkeypatch, caplog
):
    """RED: `_firecrawl_scraper` logs its fetch exception at DEBUG only.
    Escaped-exception (bug) branch only; the production transport-failure shape
    (the service returns (None, 0)) is pinned through the real service by
    test_w18b_real_render_transport_failure_reaches_one_fetch_fail_line."""
    caplog.set_level(logging.DEBUG, logger=_SCS_LOGGER)
    recorded: list[dict] = []
    monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: True)
    monkeypatch.setattr(scs, "_provider_gate_ok_async", AsyncMock(return_value=True))
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: recorded.append(kw))

    async def _raise(url):
        raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr(scs.firecrawl_service, "scrape_page_with_status", _raise)

    result = await scs._firecrawl_scraper(_URL, "Apple iPhone 15 128GB", "BHD", "bolo.bh")

    assert result is None
    assert [r["outcome"] for r in recorded] == ["timeout"], (
        f"the provider-attempt record is unchanged by this unit: {recorded}"
    )
    drops = _drops(caplog)
    assert len(drops) == 1, f"expected exactly one INFO drop line, got {drops}"
    assert re.fullmatch(_fanout_drop_re("firecrawl", "bolo.bh", "ReadTimeout"), drops[0]), drops[0]
    _assert_grep_stable(drops[0])
    assert "/product/" not in drops[0] and "SECRETTOKEN" not in drops[0]


@pytest.mark.asyncio
async def test_w18b_scrapedo_scraper_fetch_error_logs_one_info_drop_line(
    monkeypatch, caplog
):
    """RED: `_scrapedo_scraper` logs its fetch exception at DEBUG only.
    Escaped-exception (bug) branch only; see the real-service twin
    test_w18b_real_render_transport_failure_reaches_one_fetch_fail_line."""
    caplog.set_level(logging.DEBUG, logger=_SCS_LOGGER)
    recorded: list[dict] = []
    monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: True)
    monkeypatch.setattr(scs, "_provider_gate_ok_async", AsyncMock(return_value=True))
    monkeypatch.setattr(scs, "validate_scrape_url", lambda u: True)
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: recorded.append(kw))

    async def _raise(url):
        raise ConnectionResetError("peer reset")

    monkeypatch.setattr(scs.scrapedo_service, "render_page_with_status", _raise)

    result = await scs._scrapedo_scraper(_URL, "Apple iPhone 15 128GB", "BHD", "nasserpharmacy.com")

    assert result is None
    assert [r["outcome"] for r in recorded] == ["timeout"]
    drops = _drops(caplog)
    assert len(drops) == 1, f"expected exactly one INFO drop line, got {drops}"
    assert re.fullmatch(
        _fanout_drop_re("scrapedo", "nasserpharmacy.com", "ConnectionResetError"), drops[0]
    ), drops[0]
    _assert_grep_stable(drops[0])
    assert "/product/" not in drops[0] and "SECRETTOKEN" not in drops[0]


@pytest.mark.asyncio
async def test_w18b_probe_p1_inverted_three_failing_curl_scrapers_three_drop_lines(
    monkeypatch, caplog
):
    """RED (probe P1 inverted): three production curl scrapers whose fetch raises,
    raced through the real `fan_out_price_lookup`, give three INFO drop lines,
    one per retailer domain. The fan_out return value is UNCHANGED:
    failed_count stays 0 (the scraper still swallows the exception), best None.
    Escaped-exception (bug) branch; the production transport shape through the
    same real fan_out is test_w18b_real_curl_transport_failure_reaches_one_fetch_fail_line."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _boom(url, full_name, currency):
        raise RuntimeError("fetch blew up")

    monkeypatch.setattr(scs, "fetch_page_price", _boom)
    domains = ("a-store.bh", "b-store.bh", "c-store.bh")
    scrapers = [
        (lambda _p, d=d: scs._curl_scraper(f"https://{d}/p/x", "Glorious Model O", "BHD", d))
        for d in domains
    ]

    res = await fan_out_price_lookup(
        {"full_name": "Glorious Model O"}, scrapers=scrapers, scraping_mode="hard"
    )

    assert (res["best"], res["alternates"], res["failed_count"], res["cancelled_count"]) == (
        None, [], 0, 0
    ), f"return value must not change: {res}"
    drops = _drops(caplog)
    assert len(drops) == 3, f"expected one drop line per failed scraper, got {drops}"
    for d in domains:
        assert sum(
            bool(re.fullmatch(_fanout_drop_re("curl", d, "RuntimeError"), m)) for m in drops
        ) == 1, (d, drops)


# --- the Tier-1.5 wave loop (call site of fan_out_price_lookup) -----------------
def _price_harness(monkeypatch):
    """Drive the real `_get_price` to the Tier-1.5 wave loop with every network
    leg stubbed. Mirrors tests/test_curl_before_render_budget.py's harness."""
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
    monkeypatch.setattr(
        scs, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": [], "shopping_region": "bahrain"}),
    )
    monkeypatch.setattr(scs, "extract_price_from_shopping", lambda *a, **k: None)
    monkeypatch.setattr(scs, "get_official_domain", lambda *a, **k: None)
    monkeypatch.setattr(scs, "fetch_shopify_price", AsyncMock(return_value=None))
    for sel in (
        "get_shopify_sources_for_category", "get_algolia_sources_for_category",
        "get_sitemap_sources_for_category", "get_jsonapi_sources_for_category",
        "get_woo_sources_for_category", "get_salla_sources_for_category",
        "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
        "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
        "get_noon_sources_for_category", "get_gcc_shopify_pagescrape_sources_for_category",
    ):
        monkeypatch.setattr(scs, sel, lambda cat: [])
    monkeypatch.setattr(
        scs, "search_web",
        AsyncMock(return_value={"organic": [
            {"link": "https://bahrain.sharafdg.com/product/iphone-15/"}
        ]}),
    )
    tier2 = asyncio.Event()

    async def _tier2_reached(*a, **k):
        # Tier 2 is where the cascade would reach OpenAI. Signal and park, so
        # the test can cancel _get_price here without any network.
        tier2.set()
        await asyncio.sleep(30)
        return {"organic": []}

    monkeypatch.setattr(scs, "search_price_organic", _tier2_reached)
    svc = scs.get_comparison_service()
    monkeypatch.setattr(svc, "_save_price_to_db", MagicMock(), raising=False)
    return svc, tier2


def _dummy_scraper(_product):  # never awaited by the stub fan_out below
    raise AssertionError("the stub fan_out must not run scrapers")


def _winner(failed: int, cancelled: int, elapsed: float = 0.42) -> dict:
    return {
        "best": {
            "raw_data": {"amount": 244.990, "currency": "BHD",
                         "retailer": "bahrain.sharafdg.com",
                         "source_method": "page_scrape_jsonld"},
            "source_method": "page_scrape_jsonld",
        },
        "alternates": [], "cancelled_count": cancelled,
        "failed_count": failed, "elapsed_seconds": elapsed,
    }


def _miss(failed: int, cancelled: int, elapsed: float = 0.31) -> dict:
    return {"best": None, "alternates": [], "cancelled_count": cancelled,
            "failed_count": failed, "elapsed_seconds": elapsed}


def _has_count(msg: str, word: str, n: int) -> bool:
    # Tightened to the fixed token (ruling 3): exactly `<word>=<n>`.
    return bool(re.search(rf"(?<![\w]){word}={n}(?!\d)", msg))


def _wave_summaries(caplog) -> list[str]:
    """Per-wave summary lines: INFO on the scs logger, each one EXACTLY
    `[FANOUT] wave=<kind> completed=<n> failed=<n> cancelled=<n>
    elapsed=<seconds>` (ruling 3). Any INFO line that mentions the summary's
    words but does not fullmatch the token fails the test outright, so a
    looser form cannot slip through."""
    out = []
    for r in _scs_info(caplog):
        m = r.getMessage()
        if m.startswith("[FANOUT]") and " TIMEOUT " not in m:
            assert _WAVE_SUMMARY_RE.fullmatch(m), f"summary off-token: {m!r}"
            out.append(m)
    return out


async def _run_get_price(svc, tier2: asyncio.Event, *, until_tier2: bool):
    task = asyncio.ensure_future(svc._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    ))
    if not until_tier2:
        return await asyncio.wait_for(task, timeout=20)
    waiter = asyncio.ensure_future(tier2.wait())
    done, _ = await asyncio.wait({task, waiter}, timeout=20, return_when=asyncio.FIRST_COMPLETED)
    reached = tier2.is_set()
    for t in (task, waiter):
        if not t.done():
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
    return reached


@pytest.mark.asyncio
async def test_w18b_wave_summary_line_carries_failed_and_cancelled_counts(
    monkeypatch, caplog
):
    """RED: the fan_out call site logs no per-wave summary; failed_count has no
    reader. A curl wave whose fan_out reports failed_count=2, cancelled_count=1
    must produce exactly ONE INFO summary naming the curl wave with both
    counts, completed and elapsed. The returned price is UNCHANGED."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc, tier2 = _price_harness(monkeypatch)
    waves: list[str] = []

    def _build(*, candidate_urls, full_name, currency, scraping_mode, wave="all"):
        waves.append(wave)
        return [_dummy_scraper] if wave == "curl" else []

    monkeypatch.setattr(scs, "_build_escalation_scrapers", _build)

    async def _fan(product, *, scrapers, scraping_mode):
        return _winner(failed=2, cancelled=1)

    monkeypatch.setattr(scs, "fan_out_price_lookup", _fan)

    result = await _run_get_price(svc, tier2, until_tier2=False)

    assert result is not None and result["amount"] == pytest.approx(244.990)
    assert result["source_method"] == "page_scrape_jsonld"
    assert result["retailer"] == "bahrain.sharafdg.com"
    assert waves == ["curl"], waves
    summaries = _wave_summaries(caplog)
    assert len(summaries) == 1, f"expected ONE summary for the one wave, got {summaries}"
    msg = summaries[0]
    assert msg.startswith("[FANOUT] wave=curl "), f"the summary must name its wave: {msg!r}"
    assert _has_count(msg, "failed", 2), f"failed_count=2 missing: {msg!r}"
    assert _has_count(msg, "cancelled", 1), f"cancelled_count=1 missing: {msg!r}"
    _assert_grep_stable(msg)


@pytest.mark.asyncio
async def test_w18b_one_wave_summary_per_wave_curl_miss_then_render(
    monkeypatch, caplog
):
    """RED: a curl-wave miss (failed 3) followed by a render-wave win (failed 0,
    cancelled 2) gives exactly TWO summaries, one per wave, each carrying that
    wave's own counts. The render winner is returned unchanged."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc, tier2 = _price_harness(monkeypatch)
    monkeypatch.setattr(
        scs, "_build_escalation_scrapers",
        lambda *, candidate_urls, full_name, currency, scraping_mode, wave="all": [_dummy_scraper],
    )
    calls: list[int] = []

    async def _fan(product, *, scrapers, scraping_mode):
        calls.append(1)
        return _miss(failed=3, cancelled=0) if len(calls) == 1 else _winner(failed=0, cancelled=2)

    monkeypatch.setattr(scs, "fan_out_price_lookup", _fan)

    result = await _run_get_price(svc, tier2, until_tier2=False)

    assert len(calls) == 2
    assert result is not None and result["amount"] == pytest.approx(244.990)
    summaries = _wave_summaries(caplog)
    assert len(summaries) == 2, f"expected one summary per wave, got {summaries}"
    curl = [m for m in summaries if m.startswith("[FANOUT] wave=curl ")]
    render = [m for m in summaries if m.startswith("[FANOUT] wave=render ")]
    assert len(curl) == 1 and len(render) == 1, summaries
    assert _has_count(curl[0], "failed", 3) and _has_count(curl[0], "cancelled", 0), curl[0]
    assert _has_count(render[0], "failed", 0) and _has_count(render[0], "cancelled", 2), render[0]


@pytest.mark.asyncio
async def test_w18b_wave_timeout_branch_logs_summary_with_still_pending_count(
    monkeypatch, caplog
):
    """RED: when the shared budget cancels a wave (the wait_for TimeoutError
    branch) fan_out returns nothing, so its counts are lost; the branch must
    still log ONE INFO summary for that wave with the still-pending count. Two
    curl scrapers, a fan_out that never finishes, a 1.0s budget -> pending 2.
    The cascade still falls through to Tier 2 exactly as today."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "1.0")
    svc, tier2 = _price_harness(monkeypatch)

    def _build(*, candidate_urls, full_name, currency, scraping_mode, wave="all"):
        return [_dummy_scraper, _dummy_scraper] if wave == "curl" else []

    monkeypatch.setattr(scs, "_build_escalation_scrapers", _build)

    async def _fan_hangs(product, *, scrapers, scraping_mode):
        await asyncio.sleep(30)

    monkeypatch.setattr(scs, "fan_out_price_lookup", _fan_hangs)

    reached = await _run_get_price(svc, tier2, until_tier2=True)

    assert reached, "the budget-cancelled wave must still fall through to Tier 2"
    pending = [
        r.getMessage() for r in _scs_info(caplog)
        if "pending" in r.getMessage().lower() and "curl" in r.getMessage()
    ]
    assert len(pending) == 1, f"expected ONE timeout summary for the curl wave, got {pending}"
    assert re.fullmatch(rf"\[FANOUT\] wave=curl TIMEOUT pending=2 elapsed={_NUM}", pending[0]), (
        pending[0]
    )
    _assert_grep_stable(pending[0])
    # the budget-cancelled wave never returned, so it emits NO normal summary.
    assert _wave_summaries(caplog) == []


# ===========================================================================
# W1-8c — the drop taxonomy: CONSUME-BOUND, SLOW-MISS, honest TIMEOUT
# ===========================================================================
@pytest.mark.asyncio
async def test_w18c_consume_bound_logs_one_line_per_family_and_keeps_cancel_silent(
    monkeypatch, caplog
):
    """RED (probe P3, driven through the REAL consume branches rather than the
    probe's isolated gather): when the consume's outer bound fires before the
    per-source 10s wraps, each family's `except asyncio.TimeoutError` branch
    must log ONE `[ADAPTER DROP] <family>: CONSUME-BOUND after <bound>s` line
    (sitemap, jsonapi, and a _new_adapter_specs family). The per-source tasks
    it cancels stay UNLOGGED, and the consume still yields None so the cascade
    proceeds to discovery/Tier 2 as today.

    The outer bound is shrunk by clamping `_pre_reserve_remaining` for the
    consume cap only (`_ADAPTER_TIMEOUT + 2.0`) to 0.3s, which is the shape the
    genuine-priority flag produces from a nearly spent race budget."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc, tier2 = _price_harness(monkeypatch)
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(scs, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs, "get_sitemap_sources_for_category",
                        lambda cat: [SimpleNamespace(domain="bolo.bh")])
    monkeypatch.setattr(scs, "get_jsonapi_sources_for_category",
                        lambda cat: [SimpleNamespace(domain="nasserpharmacy.com")])
    monkeypatch.setattr(scs, "get_woo_sources_for_category",
                        lambda cat: [SimpleNamespace(domain="woo-store.bh")])
    # R-W18 fixer (adversary N05): a SECOND _new_adapter_specs family, so a
    # line hard-coded to one family name cannot pass.
    monkeypatch.setattr(scs, "get_salla_sources_for_category",
                        lambda cat: [SimpleNamespace(domain="salla-store.bh")])

    async def _slow_named(*a, **k):
        await asyncio.sleep(5)
        return None

    monkeypatch.setattr(scs, "fetch_bolo_price", _slow_named, raising=False)
    monkeypatch.setattr(scs, "fetch_nasser_price", _slow_named, raising=False)
    monkeypatch.setattr(scs, "fetch_woocommerce_store_api_price", _slow_named, raising=False)
    monkeypatch.setattr(scs, "fetch_salla_api_price", _slow_named, raising=False)
    consume_cap = scs._ADAPTER_TIMEOUT + 2.0
    real_reserve = scs._pre_reserve_remaining
    monkeypatch.setattr(
        scs, "_pre_reserve_remaining",
        lambda cap, dl: 0.3 if cap == consume_cap else real_reserve(cap, dl),
    )

    task = asyncio.ensure_future(svc._get_price(
        brand="elf", name="SuperHydrate Moisturizer", variant=None,
        region="bahrain", search_query="elf SuperHydrate Moisturizer",
        nocache=True, category="makeup",
    ))
    waiter = asyncio.ensure_future(tier2.wait())
    await asyncio.wait({task, waiter}, timeout=20, return_when=asyncio.FIRST_COMPLETED)
    reached = tier2.is_set()
    for t in (task, waiter):
        if not t.done():
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t

    assert reached, "a consume-bound miss must still fall through (consume returns None)"
    drops = _drops(caplog)
    for family in ("sitemap", "jsonapi", "woo", "salla"):
        lines = [
            m for m in drops
            if re.fullmatch(rf"\[ADAPTER DROP\] {family}: CONSUME-BOUND after {_NUM}s", m)
        ]
        assert len(lines) == 1, f"{family}: expected ONE CONSUME-BOUND line, got {drops}"
        bound = re.fullmatch(r"\[ADAPTER DROP\] \w+: CONSUME-BOUND after (\d+(?:\.\d+)?)s", lines[0])
        assert bound and float(bound.group(1)) == pytest.approx(0.3, abs=0.051), lines[0]
        _assert_grep_stable(lines[0])
    for label in ("sitemap:bolo.bh", "jsonapi:nasserpharmacy.com", "woo:woo-store.bh",
                  "salla:salla-store.bh"):
        assert not [m for m in drops if f"{_DROP} {label}:" in m], (
            f"the cancelled per-source task {label} must stay unlogged: {drops}"
        )


@pytest.mark.asyncio
async def test_w18c_slow_miss_near_inner_ceiling_logs_one_slow_miss_line(
    monkeypatch, caplog
):
    """RED (probe P2, reshaped): an adapter that swallows its own inner timeout
    returns a plain None AT the inner ceiling. `_timeout_none` must log ONE
    `[ADAPTER DROP] <label>: SLOW-MISS after <elapsed>s` when the None arrives at
    or after adapter_inner_ceiling() - 0.5. PRICE_RACE_TIMEOUT=1.0 makes the
    ceiling 1.0s (its floor), so the threshold is 0.5s and a 0.7s miss is slow.
    The return value stays None."""
    monkeypatch.setenv("PRICE_RACE_TIMEOUT", "1.0")
    assert adapter_inner_ceiling() == pytest.approx(1.0)
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _swallowed_inner_timeout():
        await asyncio.sleep(0.7)
        return None

    result = await _timeout_none(lambda: _swallowed_inner_timeout(), 5.0, label="unbxd:extra.com")

    assert result is None
    drops = _drops(caplog)
    assert len(drops) == 1, f"expected ONE SLOW-MISS line, got {drops}"
    m = re.fullmatch(
        r"\[ADAPTER DROP\] unbxd:extra\.com: SLOW-MISS after (\d+(?:\.\d+)?)s", drops[0]
    )
    assert m, f"wrong shape: {drops[0]!r}"
    assert 0.5 <= float(m.group(1)) < 5.0, drops[0]


@pytest.mark.asyncio
async def test_w18c_adapter_raised_timeouterror_is_not_a_wrap_timeout(caplog):
    """RED (probe P5 inverted): a TimeoutError the adapter raised itself 10 ms
    into a 10 s wrap is a bug, not load. It must log `ERROR TimeoutError
    (adapter-raised)` and never `TIMEOUT after 10.0s`. Return value None."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _raises_own_timeout():
        await asyncio.sleep(0.01)
        raise TimeoutError("inner wait_for fired")

    result = await _timeout_none(lambda: _raises_own_timeout(), 10.0, label="noon:noon.com")

    assert result is None
    drops = _drops(caplog)
    assert len(drops) == 1, drops
    assert ": TIMEOUT after" not in drops[0], f"misclassified as a wrap timeout: {drops[0]!r}"
    assert re.fullmatch(
        r"\[ADAPTER DROP\] noon:noon\.com: ERROR TimeoutError \(adapter-raised\)", drops[0]
    ), drops[0]
    _assert_grep_stable(drops[0])


# ===========================================================================
# W1-8d — the ERROR line is bounded and scrubbed
# ===========================================================================
_SECRET_URL = "https://user:hunter2@proxy.example:22225/?api_key=SECRET"


@pytest.mark.asyncio
async def test_w18d_probe_p4_inverted_error_line_is_bounded_scrubbed_single_line(caplog):
    """RED (probe P4 inverted): a 200 KB exception message carrying a proxy URL
    with userinfo + an api_key query and a newline must produce ONE drop line
    under 400 chars with no password, no query secret, no newline, and still
    the exception type and the label."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    body = "<html>" + ("X" * 200_000) + "</html>"

    async def _raise():
        raise ValueError(f"bad payload from {_SECRET_URL}\n{body}")

    result = await _timeout_none(lambda: _raise(), 1.0, label="rest_json:x.bh")

    assert result is None
    drops = _drops(caplog)
    assert len(drops) == 1, [d[:120] for d in drops]
    msg = drops[0]
    assert len(msg) < 400, f"drop line is {len(msg)} chars"
    assert "hunter2" not in msg and "SECRET" not in msg, msg[:400]
    _assert_grep_stable(msg)
    assert msg.startswith(f"{_DROP} rest_json:x.bh: ERROR ValueError"), msg[:200]


def test_w18d_safe_exc_strips_userinfo_and_query_from_every_url():
    """RED: `_safe_exc` does not exist. Contract: str(exc) with userinfo AND the
    whole query string removed from every http(s) URL (host and path kept),
    newlines -> spaces, <= 200 chars. NOTE (measured): the W1-1 Sentry helpers
    do not satisfy this — `_scrub_query_string` redacts only q/query/email/
    search/text, so `api_key=SECRET` survives it, and nothing strips userinfo."""
    exc = RuntimeError(
        "GET https://alice:pw123@api.example.com/v1/items?key=abc&x=1 failed\n"
        "retry http://bob:pw456@mirror.example.org/feed?token=zzz"
    )
    out = scs._safe_exc(exc)
    assert isinstance(out, str) and len(out) <= 200, out
    for leaked in ("alice", "pw123", "key=abc", "x=1", "bob", "pw456", "token=zzz"):
        assert leaked not in out, f"{leaked!r} leaked: {out!r}"
    assert "\n" not in out
    assert "api.example.com/v1/items" in out and "mirror.example.org/feed" in out, out


def test_w18d_safe_exc_truncates_and_leaves_plain_messages_alone():
    """RED: `_safe_exc` does not exist. A plain short message is returned as
    str(exc); a long one is cut to 200 chars."""
    assert scs._safe_exc(ValueError("bad price 'abc'")) == "bad price 'abc'"
    assert len(scs._safe_exc(ValueError("Z" * 5000))) <= 200
    assert scs._safe_exc(ValueError("line one\nline two")) == "line one line two"


def test_w18d_safe_exc_edge_shapes():
    """GREEN-phase pin of the local regex's edges: a stray '@' inside a
    password cannot leak its tail (userinfo runs to the LAST '@' before the
    host), a fragment is dropped with the query, the other Unicode line breaks
    collapse too, and the scrub runs BEFORE the 200-char cut (a URL straddling
    the cut never exposes its credentials)."""
    out = scs._safe_exc(RuntimeError("x https://u:p@ss@h.example/a?k=v#tok=frag y"))
    assert out == "x https://h.example/a y", out
    assert scs._safe_exc(RuntimeError("a\u2028b\x0bc\r\nd")) == "a b c d"
    # 179 + 1 + len("https://user:hunter2") == 200: a truncate-THEN-scrub
    # implementation would cut just before the '@' and leak the credentials.
    straddle = RuntimeError(("Z" * 179) + " https://user:hunter2@proxy.example/?api_key=SECRET")
    cut = scs._safe_exc(straddle)
    assert len(cut) == 200 and "hunter2" not in cut and "user" not in cut, cut

    class _BadStr(Exception):
        def __str__(self):
            raise RuntimeError("no str")

    assert scs._safe_exc(_BadStr()) == "<unprintable _BadStr>"


_P4_MSG = f"bad payload from {_SECRET_URL}\n" + ("<html>" + "X" * 200_000 + "</html>")


def _setup_render_scraper(monkeypatch, kind: str, exc: Exception) -> None:
    async def _raise(*a, **k):
        raise exc

    monkeypatch.setattr(scs, "_provider_gate_ok_async", AsyncMock(return_value=True))
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: None)
    if kind == "curl":
        monkeypatch.setattr(scs, "fetch_page_price", _raise)
    elif kind == "firecrawl":
        monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: True)
        monkeypatch.setattr(scs.firecrawl_service, "scrape_page_with_status", _raise)
    else:
        monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: True)
        monkeypatch.setattr(scs, "validate_scrape_url", lambda u: True)
        monkeypatch.setattr(scs.scrapedo_service, "render_page_with_status", _raise)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["curl", "firecrawl", "scrapedo"])
async def test_w18d_fanout_drop_lines_go_through_safe_exc(monkeypatch, caplog, kind):
    """Ruling (2): `_safe_exc` is applied to the new fanout drop lines too. The
    P4 probe shape through each production scraper gives ONE bounded,
    scrubbed, single-line drop that still names kind, domain and type."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    _setup_render_scraper(monkeypatch, kind, ValueError(_P4_MSG))
    fn = {"curl": scs._curl_scraper, "firecrawl": scs._firecrawl_scraper,
          "scrapedo": scs._scrapedo_scraper}[kind]

    assert await fn(_URL, "x", "BHD", "bolo.bh") is None
    drops = _drops(caplog)
    assert len(drops) == 1, [d[:120] for d in drops]
    msg = drops[0]
    assert len(msg) < 400, f"drop line is {len(msg)} chars"
    assert "hunter2" not in msg and "SECRET" not in msg, msg[:400]
    _assert_grep_stable(msg)
    assert re.fullmatch(_fanout_drop_re(kind, "bolo.bh", "ValueError"), msg), msg[:200]


@pytest.mark.asyncio
async def test_w18b_wave_summary_completed_is_scrapers_minus_failed_minus_cancelled(
    monkeypatch, caplog
):
    """Ruling (3): completed = the scrapers that returned (None or a value)
    before the wave ended = wave size - failed - cancelled. Three curl
    scrapers, fan_out reports failed 1 / cancelled 1 -> completed=1."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc, tier2 = _price_harness(monkeypatch)
    monkeypatch.setattr(
        scs, "_build_escalation_scrapers",
        lambda *, candidate_urls, full_name, currency, scraping_mode, wave="all": (
            [_dummy_scraper] * 3 if wave == "curl" else []
        ),
    )

    async def _fan(product, *, scrapers, scraping_mode):
        return _winner(failed=1, cancelled=1)

    monkeypatch.setattr(scs, "fan_out_price_lookup", _fan)

    result = await _run_get_price(svc, tier2, until_tier2=False)

    assert result is not None and result["amount"] == pytest.approx(244.990)
    summaries = _wave_summaries(caplog)
    assert len(summaries) == 1, summaries
    m = _WAVE_SUMMARY_RE.fullmatch(summaries[0])
    assert m and m.groups()[:4] == ("curl", "1", "1", "1"), summaries[0]


# ===========================================================================
# PINS — behaviour that must NOT change (all GREEN today)
# ===========================================================================
@pytest.mark.asyncio
async def test_pin_curl_scraper_hit_returns_the_same_candidate_and_is_silent(
    monkeypatch, caplog
):
    """PIN: a successful curl fetch returns the fan_out candidate dict exactly
    as today and emits no drop line."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    monkeypatch.setattr(scs, "_converted_provenance_enabled", lambda: False)
    page = {"amount": 244.99, "currency": "BHD", "title": "Apple iPhone 15 128GB",
            "source_method": "page_scrape_jsonld", "url": "https://sharafdg.com/p/1"}

    async def _hit(url, full_name, currency):
        return dict(page)

    monkeypatch.setattr(scs, "fetch_page_price", _hit)

    out = await scs._curl_scraper("https://sharafdg.com/p/1", "Apple iPhone 15 128GB", "BHD", "sharafdg.com")

    assert out == {
        "value": 244.99,
        "source_method": "page_scrape_jsonld",
        "rank": scs._RANK_PAGE_SCRAPE_JSONLD,
        "raw_data": {**page, "retailer": "sharafdg.com"},
    }
    assert _drops(caplog) == []


@pytest.mark.asyncio
async def test_pin_scraper_misses_are_not_drops(monkeypatch, caplog):
    """PIN: a scraper MISS (HTML fetched but no price / provider unavailable)
    returns None and logs no drop line.

    R-W18 fixer (adversary defect 1): fetch_page_price returning None means NO
    HTML was obtained (transport error, wall, non-2xx, blocked URL) — that is
    the production fetch-failure shape and is now a FETCH-FAIL line (pinned
    below and in test_w18b_curl_no_html_is_one_fetch_fail_line). A MISS is
    `{"_got_html": True}` (HTML, no price) or a price dict without an amount."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: False)
    monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: False)

    for miss in ({"_got_html": True}, {}, {"amount": None, "currency": "BHD"}):
        monkeypatch.setattr(scs, "fetch_page_price", AsyncMock(return_value=miss))
        assert await scs._curl_scraper(_URL, "x", "BHD", "sharafdg.com") is None
    assert await scs._firecrawl_scraper(_URL, "x", "BHD", "bolo.bh") is None
    assert await scs._scrapedo_scraper(_URL, "x", "BHD", "bolo.bh") is None
    assert _drops(caplog) == []


@pytest.mark.asyncio
async def test_pin_timeout_none_fast_miss_and_slow_hit_stay_silent(monkeypatch, caplog):
    """PIN: under the SAME shrunk ceiling as the SLOW-MISS red test, a FAST miss
    (None at ~0s) and a SLOW HIT (value at 0.7s) both stay silent and return
    exactly what the adapter returned."""
    monkeypatch.setenv("PRICE_RACE_TIMEOUT", "1.0")
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _fast_miss():
        return None

    async def _slow_hit():
        await asyncio.sleep(0.7)
        return {"amount": 12.5, "currency": "BHD"}

    assert await _timeout_none(lambda: _fast_miss(), 5.0, label="woo:a.bh") is None
    assert await _timeout_none(lambda: _slow_hit(), 5.0, label="woo:b.bh") == {
        "amount": 12.5, "currency": "BHD"
    }
    assert _drops(caplog) == []


@pytest.mark.asyncio
async def test_pin_default_ceiling_a_subsecond_miss_is_not_slow(monkeypatch, caplog):
    """PIN: with the shipped ceiling (9.0s -> threshold 8.5s) a 0.7s miss is an
    ordinary miss and stays silent — SLOW-MISS must key on the real ceiling,
    not fire on every miss."""
    monkeypatch.delenv("PRICE_RACE_TIMEOUT", raising=False)
    assert adapter_inner_ceiling() == pytest.approx(9.0)
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _miss():
        await asyncio.sleep(0.7)
        return None

    assert await _timeout_none(lambda: _miss(), 5.0, label="salla:c.bh") is None
    assert _drops(caplog) == []


@pytest.mark.asyncio
async def test_pin_real_wrap_timeout_is_still_a_timeout_line(caplog):
    """PIN: a genuine wrap timeout is still one `TIMEOUT after <n>s` line (never
    ERROR), and <n> is the real duration (~the wrap), returning None. Also an
    adapter-raised TimeoutError AT the wrap bound (elapsed >= timeout - 0.05)
    is still a TIMEOUT."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _hang():
        await asyncio.sleep(5)

    async def _raise_at_bound():
        await asyncio.sleep(0.29)
        raise TimeoutError("inner bound")

    assert await _timeout_none(lambda: _hang(), 0.3, label="occ:d.bh") is None
    assert await _timeout_none(lambda: _raise_at_bound(), 0.3, label="occ:e.bh") is None
    drops = _drops(caplog)
    assert len(drops) == 2, drops
    for d, label in zip(drops, ("occ:d.bh", "occ:e.bh"), strict=True):
        m = re.fullmatch(rf"\[ADAPTER DROP\] {re.escape(label)}: TIMEOUT after (\d+(?:\.\d+)?)s", d)
        assert m, f"wrong shape: {d!r}"
        assert 0.2 <= float(m.group(1)) < 3.0, d


@pytest.mark.asyncio
async def test_w18c_timeout_line_reports_the_measured_elapsed_not_the_wrap(caplog):
    """GREEN-phase pin: the TIMEOUT line carries the MEASURED elapsed, not the
    configured wrap. An adapter that blocks the event loop for 0.6 s inside a
    0.3 s wrap makes the wrap fire late; the line must say ~0.6 s (the loop-lag
    the old `{timeout}` text hid), and the return value stays None."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    import time as _time

    async def _blocks_then_hangs():
        _time.sleep(0.6)  # deliberately blocks the loop past the wrap
        await asyncio.sleep(5)

    assert await _timeout_none(lambda: _blocks_then_hangs(), 0.3, label="occ:g.bh") is None
    drops = _drops(caplog)
    assert len(drops) == 1, drops
    m = re.fullmatch(r"\[ADAPTER DROP\] occ:g\.bh: TIMEOUT after (\d+(?:\.\d+)?)s", drops[0])
    assert m, drops[0]
    assert float(m.group(1)) >= 0.55, f"reported the wrap, not the elapsed: {drops[0]!r}"


@pytest.mark.asyncio
async def test_pin_cancellation_still_propagates_and_is_unlogged(caplog):
    """PIN (mirrors the unit's own cancellation pin with the new timing in
    place): an outer cancel of a slow `_timeout_none` leaves the task
    CANCELLED and logs nothing — no SLOW-MISS, no TIMEOUT, no ERROR."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _slow():
        await asyncio.sleep(5)
        return None

    task = asyncio.ensure_future(_timeout_none(lambda: _slow(), 10.0, label="noon:f.bh"))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
    assert _drops(caplog) == []


@pytest.mark.asyncio
async def test_pin_fan_out_counts_unchanged_for_real_raisers():
    """PIN: fan_out_price_lookup's own counting is untouched by this unit — a
    raising scraper still counts as failed, a miss does not."""

    async def _raises(_p):
        raise RuntimeError("x")

    async def _misses(_p):
        return None

    res = await fan_out_price_lookup({"full_name": "x"}, scrapers=[_raises, _misses],
                                     scraping_mode="hard")
    assert (res["best"], res["failed_count"], res["cancelled_count"]) == (None, 1, 0)


# ===========================================================================
# R-W18 FIXER — the adversary's defects and prove-nothing rows, folded into pins
# ===========================================================================
_FETCH_FAIL_CURL_RE = r"\[ADAPTER DROP\] fanout:curl:{d}: FETCH-FAIL no-html"
_FETCH_FAIL_RENDER_RE = r"\[ADAPTER DROP\] fanout:{kind}:{d}: FETCH-FAIL status={status}"


def _fanout_drops(caplog) -> list[str]:
    return [m for m in _drops(caplog) if m.startswith(f"{_DROP} fanout:")]


@pytest.mark.asyncio
async def test_w18b_real_curl_transport_failure_reaches_one_fetch_fail_line(
    monkeypatch, caplog
):
    """Adversary defect 1 (major), reproduced then inverted: ONLY the lowest
    transport call is stubbed (curl_cffi.requests.get raising a curl Timeout);
    curl_fetch_html_same_site, fetch_page_price, _curl_scraper and
    fan_out_price_lookup are all REAL. The fetch layer swallows the error
    (WARNING + None), so the scraper's `except` never runs — before this fix
    the wave produced ZERO `[ADAPTER DROP] fanout:` lines. Required: exactly
    one `FETCH-FAIL no-html` line per failed scraper, domain only, and the
    fan_out return value unchanged."""
    import app.services.price_service as ps
    import curl_cffi.requests as curl_requests

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(
        "app.utils.url_validator._validate_url_offloop_or_sync", AsyncMock(return_value=True)
    )
    calls: list[str] = []

    def _transport_timeout(url, *a, **k):
        calls.append(url)
        raise curl_requests.exceptions.Timeout("Failed to perform, curl: (28) Operation timed out")

    monkeypatch.setattr(curl_requests, "get", _transport_timeout)
    domains = ("a-store.bh", "b-store.bh")
    scrapers = [
        (lambda _p, d=d: scs._curl_scraper(f"https://{d}/p/x?token=SECRETTOKEN", "X", "BHD", d))
        for d in domains
    ]

    res = await fan_out_price_lookup({"full_name": "X"}, scrapers=scrapers, scraping_mode="hard")

    assert (res["best"], res["alternates"], res["failed_count"], res["cancelled_count"]) == (
        None, [], 0, 0
    ), f"return value must not change: {res}"
    assert len(calls) == 2, f"the real transport must have been reached: {calls}"
    service_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "curl_fetch_html_same_site failed" in r.getMessage()
    ]
    assert len(service_warnings) == 2, "the fetch layer swallowed the error (the defect's premise)"
    drops = _fanout_drops(caplog)
    assert len(drops) == 2, f"expected one FETCH-FAIL line per failed scraper, got {drops}"
    for d in domains:
        assert sum(bool(re.fullmatch(_FETCH_FAIL_CURL_RE.format(d=re.escape(d)), m))
                   for m in drops) == 1, (d, drops)
    for info in (r.getMessage() for r in _scs_info(caplog)):
        assert "/p/x" not in info and "SECRETTOKEN" not in info and "https://" not in info, info


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["firecrawl", "scrapedo"])
async def test_w18b_real_render_transport_failure_reaches_one_fetch_fail_line(
    monkeypatch, caplog, kind
):
    """Adversary defect 1, render half: ONLY httpx.AsyncClient.post/get is
    stubbed (ConnectTimeout); firecrawl_service.scrape_page_with_status /
    scrapedo_service.render_page_with_status are REAL and return (None, 0).
    Required: ONE `FETCH-FAIL status=0` line naming kind + domain, the
    provider-attempt record unchanged ("timeout"), the return value None."""
    caplog.set_level(logging.INFO)
    recorded: list[dict] = []
    monkeypatch.setattr(scs, "_provider_gate_ok_async", AsyncMock(return_value=True))
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: recorded.append(kw))
    monkeypatch.setattr(scs, "validate_scrape_url", lambda u: True)
    for name in ("record_usage", "record_failure", "record_success"):
        monkeypatch.setattr(scs, name, lambda *a, **k: None)
    svc = scs.firecrawl_service if kind == "firecrawl" else scs.scrapedo_service
    monkeypatch.setattr(svc, "is_available", lambda: True)
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-dummy")
    monkeypatch.setenv("SCRAPEDO_API_TOKEN", "sd-test-dummy")
    posts: list[int] = []

    async def _connect_timeout(self, *a, **k):
        posts.append(1)
        raise httpx.ConnectTimeout("connect timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", _connect_timeout)
    monkeypatch.setattr(httpx.AsyncClient, "get", _connect_timeout)
    fn = scs._firecrawl_scraper if kind == "firecrawl" else scs._scrapedo_scraper

    assert await fn(_URL, "x", "BHD", "a-store.bh") is None
    assert posts == [1], "the real service must have reached the (stubbed) transport"
    assert [r["outcome"] for r in recorded] == ["timeout"], recorded
    drops = _fanout_drops(caplog)
    assert len(drops) == 1, drops
    assert re.fullmatch(
        _FETCH_FAIL_RENDER_RE.format(kind=kind, d=re.escape("a-store.bh"), status=0), drops[0]
    ), drops[0]
    _assert_grep_stable(drops[0])
    assert "/product/" not in drops[0] and "SECRETTOKEN" not in drops[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["firecrawl", "scrapedo"])
async def test_w18b_render_fetch_fail_carries_status_and_200_empty_is_a_miss(
    monkeypatch, caplog, kind
):
    """The render FETCH-FAIL line fires for every no-HTML non-200 return and
    carries the status (0 transport, 429/503 throttle, 403 wall), so the W5
    reader can bucket load vs walls. A 200 with no usable HTML is an honest
    miss (upstream error page / tiny body) and stays silent. Return None."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    monkeypatch.setattr(scs, "_provider_gate_ok_async", AsyncMock(return_value=True))
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: None)
    monkeypatch.setattr(scs, "validate_scrape_url", lambda u: True)
    for name in ("record_usage", "record_failure", "record_success"):
        monkeypatch.setattr(scs, name, lambda *a, **k: None)
    svc = scs.firecrawl_service if kind == "firecrawl" else scs.scrapedo_service
    monkeypatch.setattr(svc, "is_available", lambda: True)
    fn = scs._firecrawl_scraper if kind == "firecrawl" else scs._scrapedo_scraper
    attr = "scrape_page_with_status" if kind == "firecrawl" else "render_page_with_status"

    for status in (429, 403, 200):
        caplog.clear()
        ret = (None, status) if kind == "firecrawl" else (None, status, 5)
        monkeypatch.setattr(svc, attr, AsyncMock(return_value=ret))
        assert await fn(_URL, "x", "BHD", "bolo.bh") is None
        drops = _fanout_drops(caplog)
        if status == 200:
            assert drops == [], f"a 200-without-HTML is a miss, not a fetch failure: {drops}"
        else:
            assert len(drops) == 1 and re.fullmatch(
                _FETCH_FAIL_RENDER_RE.format(kind=kind, d=re.escape("bolo.bh"), status=status),
                drops[0],
            ), drops


@pytest.mark.asyncio
async def test_w18b_curl_no_html_is_one_fetch_fail_line(monkeypatch, caplog):
    """fetch_page_price returning None (no HTML obtained) is ONE FETCH-FAIL
    line; the return value stays None."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    monkeypatch.setattr(scs, "fetch_page_price", AsyncMock(return_value=None))

    assert await scs._curl_scraper(_URL, "x", "BHD", "sharafdg.com") is None
    drops = _drops(caplog)
    assert len(drops) == 1 and re.fullmatch(
        _FETCH_FAIL_CURL_RE.format(d=re.escape("sharafdg.com")), drops[0]
    ), drops


@pytest.mark.asyncio
async def test_w18b_wave_timeout_pending_counts_only_unfinished_scrapers(monkeypatch, caplog):
    """Adversary defect 2 (reproduced: `pending=4` with 3 of 4 finished),
    inverted through the REAL _get_price and the REAL fan_out_price_lookup:
    three scrapers miss instantly, one hangs, the 1.0s budget cancels the wave
    -> `pending=1`. The cascade still falls through to Tier 2 and every
    scraper still ran exactly as before."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "1.0")
    svc, tier2 = _price_harness(monkeypatch)
    state = {"fast_done": 0, "hang_started": 0}

    async def _fast_miss(_p):
        state["fast_done"] += 1
        return None

    async def _hang(_p):
        state["hang_started"] += 1
        await asyncio.sleep(30)

    def _build(*, candidate_urls, full_name, currency, scraping_mode, wave="all"):
        return [_fast_miss, _fast_miss, _fast_miss, _hang] if wave == "curl" else []

    monkeypatch.setattr(scs, "_build_escalation_scrapers", _build)

    reached = await _run_get_price(svc, tier2, until_tier2=True)

    assert reached
    assert state == {"fast_done": 3, "hang_started": 1}, state
    lines = [r.getMessage() for r in _scs_info(caplog) if r.getMessage().startswith("[FANOUT]")]
    assert len(lines) == 1, lines
    assert re.fullmatch(rf"\[FANOUT\] wave=curl TIMEOUT pending=1 elapsed={_NUM}", lines[0]), lines


@pytest.mark.asyncio
async def test_w18b_counting_wrapper_is_return_and_raise_identical():
    """The pending counter wraps each scraper; it must hand fan_out exactly
    what the scraper returns or raises (so best/alternates/failed_count are
    identical), count returns and raises, and never count a cancellation."""
    box = [0]
    cand = {"value": 1.0, "source_method": "page_scrape_jsonld", "rank": 90, "raw_data": {}}

    async def _hit(_p):
        return cand

    async def _boom(_p):
        raise RuntimeError("x")

    async def _none(_p):
        return None

    async def _hang(_p):
        await asyncio.sleep(30)

    wrapped = [scs._count_finished(f, box) for f in (_boom, _none, _hit)]
    assert await wrapped[2]({}) is cand
    assert await wrapped[1]({}) is None
    with pytest.raises(RuntimeError):
        await wrapped[0]({})
    assert box == [3]
    task = asyncio.ensure_future(scs._count_finished(_hang, box)({}))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert box == [3], "a cancelled scraper did not finish and must stay pending"
    box[0] = 0
    res = await fan_out_price_lookup({"full_name": "x"}, scrapers=wrapped, scraping_mode="hard")
    assert res["best"] is cand and res["failed_count"] == 1 and res["cancelled_count"] == 0, res


@pytest.mark.asyncio
async def test_w18b_wave_summary_elapsed_is_measured(monkeypatch, caplog):
    """Adversary N11: the summary's elapsed must be the wave's measured wall.
    A fan_out that takes 0.3s must report elapsed >= 0.25."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc, tier2 = _price_harness(monkeypatch)
    monkeypatch.setattr(
        scs, "_build_escalation_scrapers",
        lambda *, candidate_urls, full_name, currency, scraping_mode, wave="all": (
            [_dummy_scraper] if wave == "curl" else []
        ),
    )

    async def _fan(product, *, scrapers, scraping_mode):
        await asyncio.sleep(0.3)
        return _winner(failed=0, cancelled=0)

    monkeypatch.setattr(scs, "fan_out_price_lookup", _fan)

    result = await _run_get_price(svc, tier2, until_tier2=False)

    assert result is not None and result["amount"] == pytest.approx(244.990)
    summaries = _wave_summaries(caplog)
    assert len(summaries) == 1, summaries
    elapsed = float(summaries[0].rsplit("elapsed=", 1)[1])
    assert 0.25 <= elapsed < 5.0, summaries[0]


@pytest.mark.asyncio
async def test_w18c_consume_bound_inline_sitemap_branch_names_its_bound(monkeypatch, caplog):
    """Adversary N08: the sitemap INLINE branch (prefetch skipped at kickoff)
    must also record the bound it waited under. `_sitemap_price_fetchers`
    maps nothing at kickoff (no prefetch key) and bolo.bh at consume time, so
    the inline gather runs under the 0.3s bound -> ONE
    `sitemap: CONSUME-BOUND after 0.30s` line; the cascade still falls
    through; the cancelled per-source task stays unlogged."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc, tier2 = _price_harness(monkeypatch)
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(scs, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs, "get_sitemap_sources_for_category",
                        lambda cat: [SimpleNamespace(domain="bolo.bh")])

    async def _slow(*a, **k):
        await asyncio.sleep(5)
        return None

    calls = {"n": 0}

    def _fetchers():
        calls["n"] += 1
        return {} if calls["n"] == 1 else {"bolo.bh": _slow}

    monkeypatch.setattr(scs, "_sitemap_price_fetchers", _fetchers)
    consume_cap = scs._ADAPTER_TIMEOUT + 2.0
    real_reserve = scs._pre_reserve_remaining
    monkeypatch.setattr(
        scs, "_pre_reserve_remaining",
        lambda cap, dl: 0.3 if cap == consume_cap else real_reserve(cap, dl),
    )

    task = asyncio.ensure_future(svc._get_price(
        brand="elf", name="SuperHydrate Moisturizer", variant=None,
        region="bahrain", search_query="elf SuperHydrate Moisturizer",
        nocache=True, category="makeup",
    ))
    waiter = asyncio.ensure_future(tier2.wait())
    await asyncio.wait({task, waiter}, timeout=20, return_when=asyncio.FIRST_COMPLETED)
    reached = tier2.is_set()
    for t in (task, waiter):
        if not t.done():
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t

    assert reached
    assert calls["n"] >= 2, "the inline branch must have run (fetchers consulted again at consume)"
    drops = _drops(caplog)
    lines = [m for m in drops if m.startswith(f"{_DROP} sitemap: CONSUME-BOUND")]
    assert len(lines) == 1, drops
    m = re.fullmatch(r"\[ADAPTER DROP\] sitemap: CONSUME-BOUND after (\d+(?:\.\d+)?)s", lines[0])
    assert m and float(m.group(1)) == pytest.approx(0.3, abs=0.051), lines[0]
    assert not [d for d in drops if d.startswith(f"{_DROP} sitemap:bolo.bh:")], drops


@pytest.mark.asyncio
async def test_w18c_adapter_raised_timeout_well_inside_the_wrap_is_not_load(caplog):
    """Adversary N01: the wrap-vs-adapter-raised margin is `timeout - 0.05`.
    A TimeoutError the adapter raises at 0.85s of a 1.0s wrap (85% in) is
    still adapter-raised, never a wrap TIMEOUT. Return None."""
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _raise_late_own():
        await asyncio.sleep(0.85)
        raise TimeoutError("own inner bound")

    assert await _timeout_none(lambda: _raise_late_own(), 1.0, label="occ:h.bh") is None
    drops = _drops(caplog)
    assert drops == ["[ADAPTER DROP] occ:h.bh: ERROR TimeoutError (adapter-raised)"], drops


@pytest.mark.asyncio
async def test_w18c_slow_miss_threshold_is_ceiling_minus_half_a_second(monkeypatch, caplog):
    """Adversary N02/N03: SLOW-MISS keys on exactly adapter_inner_ceiling() - 0.5.
    PRICE_RACE_TIMEOUT=3.0 -> ceiling 2.0 -> threshold 1.5s. A None at 1.25s
    stays silent (a `ceiling * 0.5` = 1.0 or a `- 0.9` = 1.1 threshold would
    fire), a None at 1.6s is ONE SLOW-MISS. Both return None."""
    monkeypatch.setenv("PRICE_RACE_TIMEOUT", "3.0")
    assert adapter_inner_ceiling() == pytest.approx(2.0)
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)

    async def _miss_after(d):
        await asyncio.sleep(d)
        return None

    assert await _timeout_none(lambda: _miss_after(1.25), 5.0, label="woo:i.bh") is None
    assert _drops(caplog) == [], "a miss below ceiling - 0.5 must stay silent"
    assert await _timeout_none(lambda: _miss_after(1.6), 5.0, label="woo:j.bh") is None
    drops = _drops(caplog)
    assert len(drops) == 1 and re.fullmatch(
        r"\[ADAPTER DROP\] woo:j\.bh: SLOW-MISS after (\d+(?:\.\d+)?)s", drops[0]
    ), drops


def test_w18d_safe_exc_fixer_shapes():
    """Adversary defect 4 + N04 + N07: upper-case schemes, a fragment-only
    secret, a '/', '?' or '#' inside an unencoded password, a non-http proxy
    scheme, and an '@' inside a query must never leak credentials or secrets."""
    cases = {
        "GET HTTPS://USER:PW1@H.EXAMPLE/P?API_KEY=S1 x": "GET HTTPS://H.EXAMPLE/P x",
        "via https://h.example/cb#access_token=S5 y": "via https://h.example/cb y",
        "via https://user:pa/ss2@proxy.example:22225/x y": "via https://proxy.example:22225/x y",
        "via socks5://user:pw6@proxy.example:1080 y": "via socks5://proxy.example:1080 y",
    }
    for raw, want in cases.items():
        assert scs._safe_exc(RuntimeError(raw)) == want, raw
    for raw, secrets in {
        "via https://user:pa?ss3@proxy.example/x y": ("user", "pa", "ss3"),
        "via https://user:pa#ss4@proxy.example/x y": ("user", "pa", "ss4"),
        "via https://h.example/a?email=x@y.com&k=S8 y": ("S8", "email", "y.com"),
    }.items():
        out = scs._safe_exc(RuntimeError(raw))
        assert not any(s in out for s in secrets), (raw, out)
        assert out.startswith("via https://") and out.endswith(" y"), out


def test_w18d_safe_exc_is_linear_on_pathological_text():
    """The broadened scheme match must stay linear: 200 KB of letters with no
    '://' (the shape an unbounded scheme quantifier would make quadratic) and
    other adversarial shapes each scrub in well under a second."""
    import time as _time

    for text in ("a" * 200_000, "https://" + "a@" * 100_000, "https://" * 25_000,
                 ("https://" + "a" * 50 + " ") * 4000):
        t0 = _time.perf_counter()
        out = scs._safe_exc(RuntimeError(text))
        assert len(out) <= 200
        assert _time.perf_counter() - t0 < 1.0, text[:20]
