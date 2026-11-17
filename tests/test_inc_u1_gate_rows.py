"""INC-U1 LINK-RESULT (ENABLE_URL_LINK_RESULT) -- the PIN rows (S97 lane).

Spec: INC_U1_UNIT_SPEC.md section 9 (PIN rows P01..P09) as amended by
RULINGS_INC_U1.md (U-10: P10 pins the flag-OFF success and 403 compares free of any
link path or query in every log record) and the relay ruling ORCH-U1-B (P11: the
link path never calls price_service.curl_fetch_html_same_site or any other
browser-imitating client, in any flag state). Base: 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9.

Every row is green at base and must stay green at head. B1 rule: every flag-OFF row
runs in each OFF spelling (unset, "", "false", "0", "off", "garbage", " FALSE ")
WITH the full configuration present (metering and search-log truth ON, an authed
user, ENABLE_URL_WINNER_GUARD, ENABLE_RESULT_GATE, ENABLE_PRODUCT_RESOLVER and
ENABLE_OPENAI_EGRESS_STOP ON where the path allows, ENABLE_URL_MODE_V2 ON on the V2
rows) and recorders over the fetch headers and timeout, the retry
(price_service.curl_fetch_html_same_site), product_resolver.resolve_lexicon, the
generate_comparison kwargs and the save kwargs, so a "not gated" mutant is killed.
The flag-OFF success bodies are recorded literals (measured at base).

The harness is the RED file's (tests/test_inc_u1_link_result.py), imported by name.
"""
from __future__ import annotations

import app.main  # noqa: F401  -- FIRST: the dotenv hazard (common brief)

import asyncio
import gzip
import inspect
import logging

import pytest

from app.api import home_routes, profile_routes, url_routes
from app.services import url_extraction_service as ues
from tests.test_inc_u1_link_result import (  # noqa: F401 -- fixtures re-used
    BASE_HEADERS,
    EGRESS,
    FLAG,
    GATE,
    GUARD,
    HOST1,
    H,
    OFF_VALUES,
    RESOLVER,
    URL1,
    URL2,
    V2,
    PAGE_A,
    PAGE_B,
    VERDICT_ERROR,
    _u1_env,
    call,
    client,
    full,
    ok,
    page,
    page_reads,
    set_env,
    status,
    u10_assert_no_link_text,
    u10_run,
)

FULL_ON = {"guard": "true", "gate": "true", "resolver": "true", "egress": "true"}
NEW_PRODUCT_KEYS = ("link_key", "pros", "cons", "rating", "review_count")
NEW_PRICE_KEYS = ("source_method", "estimate_bhd", "estimate_basis", "original_amount",
                  "original_currency", "unavailable", "reason")

# Measured at base 5cd93c6a with the P01 / P02 configuration (see the rows).
P01_BODY: dict = {'success': True,
 'products': [{'brand': 'Dior',
               'name': 'Sauvage Eau de Parfum 100ml',
               'full_name': 'Sauvage Eau de Parfum 100ml',
               'variant': None,
               'category': 'fragrances',
               'price': {'amount': '30.000',
                         'currency': 'BHD',
                         'retailer': 'shop-a.example',
                         'url': 'https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken',
                         'in_stock': None},
               'specs': {},
               'reviews': {'rating': '4.5', 'count': '120'},
               'image_url': 'https://cdn.shop-a.example/a.jpg',
               'source_url': 'https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken',
               'retailer': {'key': 'unknown',
                            'domain': 'shop-a.example',
                            'name': 'shop-a.example',
                            'region': 'unknown',
                            'currency': 'USD'}},
              {'brand': 'Chanel',
               'name': 'Bleu de Chanel Eau de Parfum 100ml',
               'full_name': 'Bleu de Chanel Eau de Parfum 100ml',
               'variant': None,
               'category': 'fragrances',
               'price': {'amount': '45.500',
                         'currency': 'BHD',
                         'retailer': 'shop-b.example',
                         'url': 'https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken',
                         'in_stock': None},
               'specs': {},
               'reviews': {'rating': '4.8', 'count': '300'},
               'image_url': 'https://cdn.shop-b.example/b.jpg',
               'source_url': 'https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken',
               'retailer': {'key': 'unknown',
                            'domain': 'shop-b.example',
                            'name': 'shop-b.example',
                            'region': 'unknown',
                            'currency': 'USD'}}],
 'comparison': {'winner_index': 0,
                'winner_declaration': '',
                'winner_reason': 'Dior Sauvage Eau de Parfum 100ml is the stronger '
                                 'overall pick.',
                'key_tradeoff': '',
                'specs_comparison': {'product_0_advantages': ['brighter opening'],
                                     'product_1_advantages': ['longer wear'],
                                     'similar': ['EDP']},
                'product_0_pros': ['fresh opening', 7, None, '   '],
                'product_0_cons': ['shorter wear'],
                'product_1_pros': ['long wear'],
                'product_1_cons': ['heavier', {'x': 1}]},
 'winner_index': 0,
 'recommendation': '',
 'key_differences': [],
 'category_used': 'fragrances',
 'source_urls': ['https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken',
                 'https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken']}
P02_BODY: dict = {'success': True,
 'products': [{'brand': 'Dior',
               'name': 'Sauvage Eau de Parfum 100ml',
               'full_name': 'Sauvage Eau de Parfum 100ml',
               'variant': None,
               'category': 'fragrances',
               'price': {'amount': '30.000',
                         'currency': 'BHD',
                         'retailer': 'shop-a.example',
                         'url': 'https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken',
                         'in_stock': None},
               'specs': {},
               'reviews': {'rating': '4.5', 'count': '120'},
               'image_url': 'https://cdn.shop-a.example/a.jpg',
               'source_url': 'https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken',
               'retailer': {'key': 'unknown',
                            'domain': 'shop-a.example',
                            'name': 'shop-a.example',
                            'region': 'unknown',
                            'currency': 'USD'}},
              {'brand': 'Chanel',
               'name': 'Bleu de Chanel Eau de Parfum 100ml',
               'full_name': 'Bleu de Chanel Eau de Parfum 100ml',
               'variant': None,
               'category': 'fragrances',
               'price': {'amount': '45.500',
                         'currency': 'BHD',
                         'retailer': 'shop-b.example',
                         'url': 'https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken',
                         'in_stock': None},
               'specs': {},
               'reviews': {'rating': '4.8', 'count': '300'},
               'image_url': 'https://cdn.shop-b.example/b.jpg',
               'source_url': 'https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken',
               'retailer': {'key': 'unknown',
                            'domain': 'shop-b.example',
                            'name': 'shop-b.example',
                            'region': 'unknown',
                            'currency': 'USD'}}],
 'comparison': {'winner_index': 0,
                'winner_declaration': '',
                'winner_reason': 'Dior Sauvage Eau de Parfum 100ml is the stronger '
                                 'overall pick.',
                'key_tradeoff': '',
                'specs_comparison': {'product_0_advantages': ['brighter opening'],
                                     'product_1_advantages': ['longer wear'],
                                     'similar': ['EDP']},
                'product_0_pros': ['fresh opening', 7, None, '   '],
                'product_0_cons': ['shorter wear'],
                'product_1_pros': ['long wear'],
                'product_1_cons': ['heavier', {'x': 1}]},
 'winner_index': 0,
 'recommendation': 'Dior Sauvage Eau de Parfum 100ml is the stronger overall pick.',
 'key_differences': ['brighter opening', 'longer wear'],
 'category_used': 'fragrances',
 'source_urls': ['https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken',
                 'https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken']}
P01_GEN_KWARGS = ('category', 'score_winner_index', 'scores_summary')
P02_GEN_KWARGS = ('category', 'score_winner_index', 'scores_summary')


def _strip_rid(body):
    return {k: v for k, v in body.items() if k != "request_id"} if isinstance(body, dict) else body


def _assert_base_requests(h):
    assert h.pages.requests, "no page request recorded"
    for req in h.pages.requests:
        sent = {k: req["headers"].get(k) for k in BASE_HEADERS}
        assert sent == BASE_HEADERS, req
        assert req["timeout"] and set(req["timeout"].values()) == {30.0}, req["timeout"]


def _run_off(monkeypatch, client, flag, *, v2=None, verb="POST", **kw):
    cfg = dict(FULL_ON)
    cfg.update(kw)
    h = full(monkeypatch, H(), flag=flag, v2=v2, **cfg)
    return call(client, verb=verb), h


# ===========================================================================
# P01 / P02 the flag-OFF success bodies
# ===========================================================================
@pytest.mark.parametrize("verb", ["POST", "GET"])
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_p01_off_v1_success_body_is_the_base_literal(monkeypatch, client, caplog, flag, verb):
    """PIN P01: flag OFF on V1 (guard, gate, resolver, egress stop ON): the success
    body equals the base literal; the save query is f"{url1} vs {url2}"; no retry, no
    resolver call; the base fetch headers and 30 s timeout; the base verdict kwargs."""
    caplog.set_level(logging.INFO)
    resp, h = _run_off(monkeypatch, client, flag, verb=verb)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    assert resp.json() == P01_BODY, resp.json()
    assert len(h.ledger.saves) == 1, h.ledger.saves
    assert h.ledger.saves[0].get("query") == f"{URL1} vs {URL2}", h.ledger.saves[0]
    assert h.retry_calls == [] and h.resolver_calls == [], (h.retry_calls, h.resolver_calls)
    assert tuple(sorted(h.gen_calls[0])) == P01_GEN_KWARGS, h.gen_calls
    _assert_base_requests(h)
    assert page_reads(caplog) == []


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_p02_off_v2_success_body_is_the_base_literal(monkeypatch, client, caplog, flag):
    """PIN P02: flag OFF with ENABLE_URL_MODE_V2 ON (guard, gate, resolver, egress stop
    ON): the success body equals the base literal; no retry, no resolver call."""
    caplog.set_level(logging.INFO)
    resp, h = _run_off(monkeypatch, client, flag, v2="true")
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    assert resp.json() == P02_BODY, resp.json()
    assert len(h.ledger.saves) == 1, h.ledger.saves
    assert h.ledger.saves[0].get("query") == f"{URL1} vs {URL2}", h.ledger.saves[0]
    assert h.retry_calls == [] and h.resolver_calls == [], (h.retry_calls, h.resolver_calls)
    assert tuple(sorted(h.gen_calls[0])) == P02_GEN_KWARGS, h.gen_calls
    _assert_base_requests(h)
    assert page_reads(caplog) == []


# ===========================================================================
# P03 the verdict error dict
# ===========================================================================
@pytest.mark.parametrize("egress", [None, "true"])
@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_p03_off_verdict_error_dict_is_the_503_with_one_refund(monkeypatch, client, flag, v2,
                                                               egress):
    """PIN P03: flag OFF, an error dict from the verdict: 503 LLM_UNAVAILABLE and one
    refund (V1 and V2, egress stop OFF and ON): never a degraded 200."""
    resp, h = _run_off(monkeypatch, client, flag, v2=v2, egress=egress, verdict=VERDICT_ERROR)
    assert resp.status_code == 503, (resp.status_code, resp.text[:300])
    assert resp.json().get("code") == "LLM_UNAVAILABLE", resp.json()
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    assert h.ledger.saves == [], h.ledger.saves
    assert h.retry_calls == [] and h.resolver_calls == []


# ===========================================================================
# P04 the fetch headers and timeout
# ===========================================================================
@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_p04_off_fetch_headers_keep_br_and_the_30s_timeout(monkeypatch, client, flag, v2):
    """PIN P04: flag OFF, fetch_page (V1) and _fetch_page_v2 (V2) send the base headers
    ("gzip, deflate, br") under the 30.0 s timeout; _fetch_page_v2's default call
    shape is unchanged."""
    resp, h = _run_off(monkeypatch, client, flag, v2=v2)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    _assert_base_requests(h)
    assert len(h.pages.requests) == 2, h.pages.requests


def test_p04b_fetch_page_v2_default_result_keys(monkeypatch):
    """PIN P04b: _fetch_page_v2(url) with no keyword returns the base key set."""
    h = full(monkeypatch, H(), flag="true")
    out = asyncio.run(ues._fetch_page_v2(URL1))
    assert sorted(out) == ["error_type", "final_url", "outcome", "status", "text"], out
    assert out["outcome"] == "ok" and out["status"] == 200, out
    _assert_base_requests(h)


# ===========================================================================
# P05 the codeless failure
# ===========================================================================
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_p05_off_fetch_failure_is_the_codeless_400(monkeypatch, client, caplog, flag):
    """PIN P05: flag OFF on V1, a 403: the codeless 400 "Could not extract both
    products", one refund, no retry, and the one ERROR line by host and type."""
    caplog.set_level(logging.INFO)
    pages = {URL1: status(403), URL2: (200, {"content-type": "text/html"}, "<html></html>")}
    resp, h = _run_off(monkeypatch, client, flag, pages=pages)
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    assert _strip_rid(resp.json()) == {"success": False, "code": "BAD_REQUEST",
                                       "error": "Could not extract both products"}, resp.json()
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    assert h.retry_calls == [], h.retry_calls
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR
            and r.name == "app.services.url_extraction_service"]
    assert msgs == [f"Failed to fetch URL host {HOST1}: HTTPStatusError"], msgs


# ===========================================================================
# P06 no new key, no new line
# ===========================================================================
@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_p06_off_no_page_read_line_and_no_new_key(monkeypatch, client, caplog, flag, v2):
    """PIN P06: flag OFF: no URL_PAGE_READ record, no metadata key, no link_key / pros /
    cons / rating / review_count product key, no new price key."""
    caplog.set_level(logging.INFO)
    resp, _ = _run_off(monkeypatch, client, flag, v2=v2)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert "metadata" not in body, body.get("metadata")
    for p in body.get("products") or []:
        for key in NEW_PRODUCT_KEYS:
            assert key not in p, (key, p)
        for key in NEW_PRICE_KEYS:
            assert key not in (p.get("price") or {}), (key, p.get("price"))
    assert page_reads(caplog) == []


# ===========================================================================
# P07 the admin extract routes never take the flag
# ===========================================================================
@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_p07_admin_extract_with_the_flag_on_returns_the_base_result(monkeypatch, client,
                                                                   caplog, verb):
    """PIN P07: /api/v1/url/extract with the flag ON returns exactly the flag-OFF result;
    no retry, no resolver call, no URL_PAGE_READ record."""
    caplog.set_level(logging.INFO)

    def extract():
        if verb == "GET":
            return client.get("/api/v1/url/extract", params={"url": URL1})
        return client.post("/api/v1/url/extract", json={"url": URL1})

    full(monkeypatch, H(), flag=None, **FULL_ON)
    off = extract()
    h = full(monkeypatch, H(), flag="true", **FULL_ON)
    on = extract()
    assert off.status_code == 200 and on.status_code == 200, (off.text[:200], on.text[:200])
    assert on.json() == off.json(), (on.json(), off.json())
    assert h.retry_calls == [] and h.resolver_calls == [], (h.retry_calls, h.resolver_calls)
    _assert_base_requests(h)
    assert page_reads(caplog) == []


# ===========================================================================
# P08 the deadline wrapper's default call shape
# ===========================================================================
@pytest.mark.parametrize("flag", [None, "true"])
def test_p08_compare_with_deadline_default_passes_url_mode_v2_true(monkeypatch, flag):
    """PIN P08: _compare_with_deadline(url1, url2, region, category) calls
    compare_from_urls with exactly url_mode_v2=True (no other keyword), whatever the
    flag reads."""
    set_env(monkeypatch, FLAG, flag)
    seen = []

    async def rec(*a, **kw):
        seen.append((a, dict(kw)))
        return {"success": True}
    monkeypatch.setattr(url_routes, "compare_from_urls", rec)
    out = asyncio.run(url_routes._compare_with_deadline(URL1, URL2, "bahrain", None))
    assert out == {"success": True}
    assert seen == [((URL1, URL2, "bahrain", None), {"url_mode_v2": True})], seen


# ===========================================================================
# P09 the saved-row readers
# ===========================================================================
def _row(c0="BHD", c1="BHD", metadata=None):
    row = {"winner_index": 1, "products": [
        {"name": "A", "price": {"amount": 30.0, "currency": c0}},
        {"name": "B", "price": {"amount": 20.0, "currency": c1}}]}
    if metadata is not None:
        row["metadata"] = metadata
    return row


def test_p09_saved_row_readers_unchanged_on_an_unstamped_row():
    """PIN P09: home _result_status_supported and both _extract_winner_loser_prices read
    an unstamped BHD row as a decision with its prices, skip a non-BHD pair, and skip
    a stamped non-supported row."""
    assert home_routes._result_status_supported(_row()) is True
    assert home_routes._result_status_supported(_row(metadata={"query": "a vs b"})) is True
    for reader in (home_routes._extract_winner_loser_prices,
                   profile_routes._extract_winner_loser_prices):
        assert reader(_row()) == (20.0, 30.0)
        assert reader(_row(metadata={"query": "a vs b", "input_type": "url"})) == (20.0, 30.0)
        assert reader(_row(c0="SAR")) == (None, None)
        assert reader(_row(metadata={"result_status": "abstain"})) == (None, None)


# ===========================================================================
# P10 (U-10): the flag-OFF success and 403 compares print no link path or query
# ===========================================================================
@pytest.mark.parametrize("scenario", ["success", "http_403"])
def test_p10_u10_off_success_and_403_logs_carry_no_link_text(monkeypatch, client, caplog,
                                                            scenario):
    """PIN P10 (U-10): flag OFF, the success compare (the save run for real) and the 403
    compare: no captured record carries the link's path segment or query token."""
    resp, h, _inserted = u10_run(monkeypatch, client, caplog, "off", scenario)
    assert resp.status_code == (200 if scenario == "success" else 400), resp.text[:300]
    if scenario == "success":
        assert len(h.ledger.saves) == 1, h.ledger.saves
    assert h.retry_calls == []
    u10_assert_no_link_text(caplog)


# ===========================================================================
# P11 (ORCH-U1-B): the link path never calls curl_fetch_html_same_site
# ===========================================================================
P11_SCENARIOS = ("success", "http_401", "http_403", "http_429", "challenge", "timeout",
                 "http_503", "br")


def _p11_pages(scenario):
    import httpx
    pages = {URL1: ok(PAGE_A), URL2: ok(PAGE_B)}
    if scenario.startswith("http_"):
        pages[URL1] = status(int(scenario[5:]))
    elif scenario == "challenge":
        pages[URL1] = ok(page("Just a moment...", body="Checking your browser."))
    elif scenario == "timeout":
        pages[URL1] = httpx.ReadTimeout
    elif scenario == "br":
        pages[URL1] = ok(gzip.compress(PAGE_A.encode("utf-8")), {"content-encoding": "br"})
    return pages


@pytest.mark.parametrize("scenario", P11_SCENARIOS)
@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("flag", OFF_VALUES + ["true"])
def test_p11_link_path_never_calls_the_curl_helper(monkeypatch, client, flag, v2, scenario):
    """PIN P11 (ORCH-U1-B): in every flag state (each OFF spelling and ON, V1 and V2,
    the guard, gate, resolver and egress stop ON) and on every page outcome (success,
    401 / 403 / 429, challenge, timeout, 503, br), the recorder on
    price_service.curl_fetch_html_same_site is never called."""
    resp, h = _run_off(monkeypatch, client, flag, v2=v2, pages=_p11_pages(scenario))
    assert resp.status_code in (200, 400, 503), (resp.status_code, resp.text[:300])
    assert h.retry_calls == [], h.retry_calls


def test_p11b_link_modules_name_no_browser_imitating_client():
    """PIN P11b (ORCH-U1-B): url_extraction_service and url_routes never name
    curl_fetch_html_same_site, curl_cffi or an impersonate argument."""
    for module in (ues, url_routes):
        src = inspect.getsource(module)
        for word in ("curl_fetch_html_same_site", "curl_cffi", "impersonate"):
            assert word not in src, (module.__name__, word)
