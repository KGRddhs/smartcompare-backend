"""INC-U1 LINK-RESULT fix round 1 (ENABLE_URL_LINK_RESULT) -- the fix-1 rows (S97 lane).

Gate: GATE_INC_U1.md section FIX ROUND 1 RULINGS FX-1..FX-5 (A-1 F1 / F2 / F3 / F5,
A-2 F1). The two frozen files (tests/test_inc_u1_link_result.py,
tests/test_inc_u1_gate_rows.py) never change; their helpers are imported read-only.

- FX-1: under the flag a retailer default currency applies only on that retailer's own
  single-country domain (host == key or a subdomain of it); a multi-country key
  (carrefour, luluhypermarket, noon.com, sharafdg.com, jarir.com, extra.com) never gives a
  default: the price is pending currency_unknown, no BHD amount, no metadata.query.
  amazon.com itself keeps USD converted and captioned. Flag OFF unchanged.
- FX-2: a challenge title is refused as reason challenge before the status branch, for
  any status: zero retries, URL_PAGE_READ challenge=yes retry=none, zero LLM calls, one
  refund.
- FX-3: no metadata.query when a product name is the V1 placeholder or not a usable
  title.
- FX-4: the BHD kind writes currency "BHD" exactly; the page's raw label is kept in
  original_currency when it differs.

Rows marked RED fail at the GREEN head dc19c18d on an AssertionError only; rows marked
PIN are green there and after the fix. Synthetic hosts and pages only; no network, no
database, no credential literal.
"""
from __future__ import annotations

import app.main  # noqa: F401  -- FIRST: the dotenv hazard (common brief)

import logging

import pytest

from app.services import text_sanitize
from app.services import url_extraction_service as ues
from tests.test_inc_u1_link_result import (  # noqa: F401  -- fixtures by name
    CHALLENGE, H, HOST1, PAGE_A, PAGE_B, PAGE_READ_RE, SU_MSG, URL1, URL2, _assert_no_detour,
    _link_on, _u1_env, _unit_ran, assert_wire_refusal, call, client, full, node, ok, page,
    page_reads, products_of, service_refusal, status,
)

# ---------------------------------------------------------------------------
# pages on retailer hosts
# ---------------------------------------------------------------------------
AMZ_TR = "https://www.amazon.com.tr/dp/B0FIXONE01"
AMZ_US = "https://www.amazon.com/dp/B0FIXONE02"
AMZ_PAGE = ("<html><head><title>Amazon page</title></head><body>"
            '<span id="productTitle">Dior Sauvage Eau de Parfum 100ml</span>'
            '<span class="a-price-whole">4,500</span></body></html>')
GENERIC_NO_CURRENCY = page("Bleu de Chanel EDP 100ml | Store", [node(
    "Bleu de Chanel Eau de Parfum 100ml", brand="Chanel", price="520.00")])

# Hosts a SUPPORTED_RETAILERS key matches by substring whose sites span countries (or
# that are another country's domain): no retailer default currency under the flag.
MULTI_COUNTRY_URLS = [
    "https://www.carrefouruae.com/mafuae/en/p/123456",
    "https://www.luluhypermarket.com/en-ae/p/123456",
    "https://bahrain.sharafdg.com/product/fix-one-123/",
    "https://www.jarir.com/kw-en/fix-one-123.html",
    "https://www.extra.com/en-om/p/123456",
]
MULTI_COUNTRY_IDS = ["carrefouruae", "lulu-en-ae", "sharafdg-bahrain", "jarir-kw", "extra-om"]
EMPTY_PAGE = "<html><head></head><body>hello</body></html>"


def _no_history_query(body, h):
    assert "query" not in (body.get("metadata") or {}), body.get("metadata")
    for saved in h.ledger.saves:
        meta = (saved.get("full_response") or {}).get("metadata") or {}
        assert "query" not in meta, saved


def _pending_currency_unknown(price):
    assert price.get("amount") is None, price
    assert price.get("unavailable") is True, price
    assert price.get("reason") == "currency_unknown", price
    assert price.get("currency") == "BHD", price
    assert "source_method" not in price, price


# ===========================================================================
# FX-1 the retailer default currency only on its own single-country domain
# ===========================================================================
def test_fx1a_amazon_other_country_domain_is_pending_not_usd(monkeypatch, client):
    """RED FX-1a: amazon.com.tr matches the amazon.com key by substring but is not
    amazon.com: no USD default, the price is pending currency_unknown (no BHD amount,
    no converted_usd), and the pair carries no metadata.query (no History row)."""
    h = full(monkeypatch, H(), pages={AMZ_TR: ok(AMZ_PAGE), URL2: ok(PAGE_B)})
    body, products = products_of(call(client, url1=AMZ_TR, url2=URL2))
    _unit_ran(h)
    _pending_currency_unknown(products[0].get("price") or {})
    assert (products[0].get("price") or {}).get("original_currency") is None, products[0]
    _no_history_query(body, h)
    _link_on()


@pytest.mark.parametrize("url", MULTI_COUNTRY_URLS, ids=MULTI_COUNTRY_IDS)
def test_fx1b_multi_country_retailer_without_a_stated_currency_is_pending(monkeypatch,
                                                                          client, url):
    """RED FX-1b: a host of a multi-country retailer key (carrefour / luluhypermarket /
    sharafdg.com / jarir.com / extra.com) whose page states no currency gets no retailer
    default: pending currency_unknown, no BHD amount, no metadata.query."""
    h = full(monkeypatch, H(), pages={url: ok(GENERIC_NO_CURRENCY), URL2: ok(PAGE_A)})
    body, products = products_of(call(client, url1=url, url2=URL2))
    _unit_ran(h)
    _pending_currency_unknown(products[0].get("price") or {})
    _no_history_query(body, h)
    _link_on()


def test_fx1c_amazon_com_itself_keeps_usd_converted_and_captioned(monkeypatch, client):
    """PIN FX-1c: amazon.com itself (its own single-country domain) keeps the USD
    default: 4500 USD ships as 1692.0 BHD, source_method converted_usd, original_amount
    4500, original_currency USD."""
    h = full(monkeypatch, H(), pages={AMZ_US: ok(AMZ_PAGE), URL2: ok(PAGE_B)})
    _, products = products_of(call(client, url1=AMZ_US, url2=URL2))
    _unit_ran(h)
    price = products[0].get("price") or {}
    assert price.get("amount") == 1692.0, price
    assert price.get("currency") == "BHD", price
    assert price.get("source_method") == "converted_usd", price
    assert price.get("original_amount") == 4500, price
    assert price.get("original_currency") == "USD", price
    _link_on()


def test_fx1d_flag_off_retailer_hosts_unchanged(monkeypatch, client):
    """PIN FX-1d (flag OFF identity): with the flag OFF the amazon.com.tr / carrefouruae
    pair ships the base bodies: amount 4500.0 USD and "520.00" BHD, no metadata key."""
    crf = MULTI_COUNTRY_URLS[0]
    h = full(monkeypatch, H(), flag=None, pages={AMZ_TR: ok(AMZ_PAGE), crf: ok(GENERIC_NO_CURRENCY)})
    body, products = products_of(call(client, url1=AMZ_TR, url2=crf))
    assert all(c["kwargs"].get("link_result") is not True for c in h.cfu_calls), h.cfu_calls
    p0, p1 = (products[0].get("price") or {}), (products[1].get("price") or {})
    assert (p0.get("amount"), p0.get("currency")) == (4500.0, "USD"), p0
    assert (p1.get("amount"), p1.get("currency")) == ("520.00", "BHD"), p1
    assert "metadata" not in body, body.get("metadata")


def test_fx1e_stated_currency_helper_single_country_rule():
    """RED FX-1e: the helper gives a retailer default only for host == key or a
    subdomain of it, never for a multi-country key, and a stated currency always wins."""
    fn = getattr(ues, "_link_stated_currency", None)
    assert callable(fn), "INC-U1: _link_stated_currency missing"

    def r(url):
        found = ues.detect_retailer(url)
        assert isinstance(found, dict), url
        return found
    assert fn(None, r("https://www.amazon.com/dp/x")) == "USD"
    assert fn(None, r("https://smile.amazon.com/dp/x")) == "USD"
    assert fn(None, r("https://www.amazon.ae/dp/x")) == "AED"
    assert fn(None, r("https://www.amazon.sa/dp/x")) == "SAR"
    assert fn(None, r("https://www.xcite.com/p/x")) == "KWD"
    assert fn(None, r("https://www.amazon.com.tr/dp/x")) is None
    assert fn(None, r("https://www.amazon.com.au/dp/x")) is None
    assert fn(None, r("https://www.xcite.com.sa/p/x")) is None
    assert fn(None, r("https://www.noon.com/uae-en/p/x")) is None
    for url in MULTI_COUNTRY_URLS:
        assert fn(None, r(url)) is None, url
    assert fn("AED", r("https://www.carrefouruae.com/p/x")) == "AED"
    assert fn(None, {"key": "generic", "domain": "shop-a.example"}) is None


# ===========================================================================
# FX-2 a challenge page is refused before the status branch
# ===========================================================================
def _host_reads(caplog, host):
    out = []
    for rec in page_reads(caplog):
        m = PAGE_READ_RE.match(rec.getMessage())
        assert m is not None, rec.getMessage()
        if m.group("host") == host:
            out.append(m.groupdict())
    return out


@pytest.mark.parametrize("code", [403, 429, 500, 502, 503])
def test_fx2a_challenge_title_on_a_non_2xx_is_challenge_without_retry(monkeypatch, client,
                                                                      caplog, code):
    """RED FX-2a: a challenge title served with a 403 / 429 / 5xx is STORE_UNREADABLE
    reason challenge on the service result, ONE request (no retry), URL_PAGE_READ
    challenge=yes retry=none, no retry log line, zero LLM calls, one refund."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(logging.getLogger("httpx"), "level", logging.WARNING)
    monkeypatch.setattr(logging.getLogger("httpcore"), "level", logging.WARNING)
    h = full(monkeypatch, H(), pages={URL1: status(code, CHALLENGE), URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "challenge",
                                  "error": SU_MSG}, h.cfu_calls
    assert len([r for r in h.pages.requests if r["url"] == URL1]) == 1, h.pages.requests
    reads = _host_reads(caplog, HOST1)
    assert len(reads) == 1, reads
    assert (reads[0]["challenge"], reads[0]["retry"]) == ("yes", "none"), reads[0]
    assert not [r for r in caplog.records if "retry host=" in r.getMessage()], [
        r.getMessage() for r in caplog.records if "retry host=" in r.getMessage()]
    assert h.llm_calls == [] and h.gen_calls == [], (h.llm_calls, h.gen_calls)
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


def test_fx2b_challenge_503_under_v2_reaches_the_wire_as_challenge(monkeypatch, client):
    """RED FX-2b: with ENABLE_URL_MODE_V2 also ON the 503 challenge reaches the wire as
    field url1, reason challenge (never http_5xx), one request, one refund."""
    h = full(monkeypatch, H(), v2="true", pages={URL1: status(503, CHALLENGE),
                                                 URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert (body.get("code"), body.get("field"), body.get("reason")) == (
        "STORE_UNREADABLE", "url1", "challenge"), body
    assert len([r for r in h.pages.requests if r["url"] == URL1]) == 1, h.pages.requests
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


@pytest.mark.parametrize("code", [403, 503])
def test_fx2c_plain_refusal_bodies_keep_their_frozen_reasons(monkeypatch, client, code):
    """PIN FX-2c: a body without a challenge title keeps the frozen outcome: 403
    refused with one request; 503 then 200 is one retry that delivers."""
    if code == 403:
        h = full(monkeypatch, H(), pages={URL1: status(403), URL2: ok(PAGE_B)})
        resp = call(client)
        assert service_refusal(h)["reason"] == "refused", h.cfu_calls
        assert len([r for r in h.pages.requests if r["url"] == URL1]) == 1
    else:
        h = full(monkeypatch, H(), pages={URL1: [status(503), ok(PAGE_A)], URL2: ok(PAGE_B)})
        products_of(call(client))
        assert len([r for r in h.pages.requests if r["url"] == URL1]) == 2
    _link_on()


# ===========================================================================
# FX-3 no metadata.query for a placeholder name
# ===========================================================================
def test_fx3a_unknown_product_placeholder_gets_no_history_query(monkeypatch, client):
    """RED FX-3a: a page with no usable title (V1 names it "Unknown Product") under the
    flag with the result gate OFF: a 200 with no metadata.query and no save carrying
    one."""
    h = full(monkeypatch, H(), pages={URL1: ok(EMPTY_PAGE), URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    body = resp.json()
    names = [p.get("name") for p in body.get("products") or []]
    assert "Unknown Product" in names, names
    _no_history_query(body, h)
    _link_on()


def _adapt_pair(name0, name1):
    fn = getattr(ues, "_link_result_adapt", None)
    assert callable(fn), "INC-U1: _link_result_adapt missing"
    products = [
        {"name": name0, "brand": "Dior", "price": {"amount": "30.000", "currency": "BHD"}},
        {"name": name1, "brand": "Chanel", "price": {"amount": "45.500", "currency": "BHD"}},
    ]
    extras = [{"currency_code": "BHD"}, {"currency_code": "BHD"}]
    return fn({"products": products, "comparison": {}}, extras, False)


@pytest.mark.parametrize("placeholder", ["Unknown Product", "unknown", "N/A", "", None,
                                         "  this product. "])
def test_fx3b_adapter_writes_no_query_for_a_placeholder_name(placeholder):
    """RED FX-3b: the adapter writes no metadata when either name is a placeholder or
    not a usable title."""
    for pair in ((placeholder, "Bleu de Chanel EDP"), ("Sauvage EDP", placeholder)):
        body = _adapt_pair(*pair)
        assert "metadata" not in body, (pair, body.get("metadata"))


def test_fx3c_adapter_writes_the_query_for_real_names():
    """PIN FX-3c: two usable names keep the metadata {query, input_type url}."""
    body = _adapt_pair("Sauvage EDP", "Bleu de Chanel EDP")
    want0 = text_sanitize.dedup_brand_name("Dior", "Sauvage EDP")
    want1 = text_sanitize.dedup_brand_name("Chanel", "Bleu de Chanel EDP")
    assert body.get("metadata") == {"query": f"{want0} vs {want1}", "input_type": "url"}


# ===========================================================================
# FX-4 the BHD kind writes currency "BHD" exactly
# ===========================================================================
ARABIC_BD = chr(0x62F) + "." + chr(0x628)


@pytest.mark.parametrize("label", ["BD", "bhd", ARABIC_BD], ids=["BD", "bhd", "arabic"])
def test_fx4a_bhd_kind_writes_the_exact_code_and_keeps_the_raw_label(monkeypatch, client,
                                                                     label):
    """RED FX-4a: a page price labelled "BD" / "bhd" / the Arabic dinar sign ships with
    currency "BHD" exactly, the amount unchanged, the page label in
    original_currency; the pair keeps its metadata.query."""
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="30.000",
                         currency=label)])
    h = full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    body, products = products_of(call(client))
    _unit_ran(h)
    price = products[0].get("price") or {}
    assert price.get("currency") == "BHD", price
    assert price.get("original_currency") == label, price
    assert price.get("amount") == "30.000", price
    assert "source_method" not in price and "unavailable" not in price, price
    assert "query" in (body.get("metadata") or {}), body.get("metadata")
    _link_on()


def test_fx4b_exact_bhd_label_adds_no_original_currency(monkeypatch, client):
    """PIN FX-4b: an exact "BHD" label adds no original_currency (R07 holds)."""
    h = full(monkeypatch, H())
    _, products = products_of(call(client))
    _unit_ran(h)
    assert "original_currency" not in (products[0].get("price") or {}), products[0]
    _link_on()
