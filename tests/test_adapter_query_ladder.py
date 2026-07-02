"""R1 adapter RETRIEVAL-TERM LADDER (genuine-price KPI Wave B3).

Store search APIs are AND-restrictive: the full canonical name
("Yves Saint Laurent Black Opium Eau de Parfum 90ml") returns 0 rows on every
live-probed store while the model-core term ("Black Opium") returns the EXACT
SKU (recon_cascade R1: theperfumesclub 48.000 BHD in-stock via the Woo Store
API; klinq 39.38 via magento_graphql_bhd). The ladder widens RETRIEVAL only —
acceptance still runs the full strict/_selection_match chain against the
ORIGINAL product_name, so a flanker retrieved by the wider core term is still
rejected.

Pins (offline, NO network — transport seams monkeypatched):
  (a) build_adapter_search_terms semantics per category, incl. the
      numeric-axis PIN: for electronics/fashion the core drops ONLY
      brand + padding and NEVER a digit-bearing token.
  (b) woo Store API round-trip: full-term -> [], core-term -> the REAL
      perfumesclub payload -> 48.000 BHD woo_store_api returned.
  (c) flanker leak pins: core-term retrieval returning ONLY the
      "EDP Extreme 90ml" / "Le Parfum 90 ml" siblings -> None (rejected).
  (d) latency pin: NO second request when the first response carries rows —
      even when none of them match.
  (e) flag-OFF (ENABLE_ADAPTER_QUERY_LADDER=false) byte-identity: single
      full-term request only.
  (f) wiring pins for salla / magento shape-B / algolia explicit-store.
"""
import asyncio
import json

import pytest
from unittest.mock import patch

import app.services.woocommerce_service as woo
import app.services.salla_service as salla
import app.services.magento_graphql_service as mg
import app.services.algolia_service as alg
from app.services.price_service import build_adapter_search_terms


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    # Env-independent: adapters gated by ENABLE_PAGE_SCRAPE; ladder default ON.
    monkeypatch.setattr(woo, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(salla, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(alg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.delenv("ENABLE_ADAPTER_QUERY_LADDER", raising=False)


# ---------------------------------------------------------------------------
# (a) term builder
# ---------------------------------------------------------------------------

FULL_YSL = "Yves Saint Laurent Black Opium Eau de Parfum 90ml"


def test_terms_fragrance_full_then_core():
    assert build_adapter_search_terms(FULL_YSL, "fragrances") == [
        FULL_YSL, "Black Opium",
    ]


def test_terms_fragrance_lancome():
    full = "Lancome La Vie Est Belle Eau de Parfum 100ml"
    assert build_adapter_search_terms(full, "fragrances") == [
        full, "La Vie Est Belle",
    ]


def test_terms_fragrance_prada():
    full = "Prada Luna Rossa Carbon Eau de Toilette 100ml"
    assert build_adapter_search_terms(full, "fragrances") == [
        full, "Luna Rossa Carbon",
    ]


def test_terms_fragrance_oz_size_and_two_word_brand():
    full = "Carolina Herrera Good Girl Eau de Parfum 2.7 oz"
    assert build_adapter_search_terms(full, "fragrances") == [full, "Good Girl"]


def test_terms_fragrance_gender_padding_dropped():
    full = "Dior Sauvage For Men Eau de Toilette 100ml"
    assert build_adapter_search_terms(full, "fragrances") == [full, "Sauvage"]


def test_terms_electronics_core_keeps_model_and_storage():
    """PIN (numeric-axis categories): core drops ONLY brand + padding —
    model + storage digit tokens ALWAYS survive."""
    full = "Samsung Galaxy S25 256GB"
    assert build_adapter_search_terms(full, "electronics") == [
        full, "Galaxy S25 256GB",
    ]


def test_terms_electronics_digit_bearing_padding_kept():
    """PIN: even a digit-bearing PADDING word ("5G") is never dropped for
    electronics — only pure word padding ("Smartphone") is."""
    full = "Samsung Galaxy S24 Ultra 5G Smartphone 256GB"
    assert build_adapter_search_terms(full, "electronics") == [
        full, "Galaxy S24 Ultra 5G 256GB",
    ]


def test_terms_fashion_digit_tokens_kept():
    full = "Nike Air Force 1 '07 White"
    assert build_adapter_search_terms(full, "fashion") == [
        full, "Air Force 1 '07 White",
    ]


def test_terms_other_category_reinfers_fragrance():
    # Mirror of _selection_match's explicit-"other" re-inference.
    assert build_adapter_search_terms(FULL_YSL, "other") == [
        FULL_YSL, "Black Opium",
    ]


def test_terms_dedupe_when_core_equals_full():
    assert build_adapter_search_terms("Black Opium", "fragrances") == ["Black Opium"]


def test_terms_never_empty_or_one_char_core():
    # Brand + concentration + size strip everything -> NO core emitted.
    assert build_adapter_search_terms("YSL EDP 90ml", "fragrances") == ["YSL EDP 90ml"]


def test_terms_full_name_always_untouched_first():
    full = "  Yves Saint Laurent   Black Opium Eau de Parfum 90ml"
    terms = build_adapter_search_terms(full, "fragrances")
    assert terms[0] == full  # verbatim, never normalized (flag-OFF byte-identity)


def test_terms_flag_off_returns_full_only(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_QUERY_LADDER", "false")
    assert build_adapter_search_terms(FULL_YSL, "fragrances") == [FULL_YSL]


# ---------------------------------------------------------------------------
# (b)-(e) woo Store API round-trip — the REAL perfumesclub payload
# (recon_cascade evidence 2026-07-02: minor-unit-3 BHD, in-stock)
# ---------------------------------------------------------------------------

WOO_QUERY = "YSL Black Opium EDP 90 ml"  # strict=True form (recon-pinned)
WOO_CORE = "Black Opium"


def _pc_row(name, slug):
    return {
        "name": name,
        "permalink": f"https://theperfumesclub.com/product/{slug}/",
        "is_in_stock": True,
        "prices": {
            "price": "48000",
            "currency_code": "BHD",
            "currency_minor_unit": 3,
        },
    }


# Exact SKU deliberately NOT first — the matcher must pick it, not position 0.
PERFUMESCLUB_ROWS = [
    _pc_row("YSL Black Opium (W) EDP Extreme 90ml", "ysl-black-opium-w-edp-extreme-90ml"),
    _pc_row("YSL Black Opium (W) EDP 90 ml", "ysl-black-opium-w-edp-90-ml"),
    _pc_row("YSL Black Opium (W) Le Parfum 90 ml", "ysl-black-opium-w-le-parfum-90-ml"),
]

PERFUMESCLUB_FLANKERS_ONLY = [PERFUMESCLUB_ROWS[0], PERFUMESCLUB_ROWS[2]]


class _FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _patch_woo_router(monkeypatch, routes):
    """Route woo GETs by params['search']; unknown term -> empty list.
    Returns the ordered list of search terms requested."""
    calls = []

    def fake_do_get(url, params, headers):
        term = (params or {}).get("search")
        calls.append(term)
        return _FakeResp(routes.get(term, []))

    monkeypatch.setattr(woo, "_do_get", fake_do_get)
    return calls


def test_woo_ladder_recovers_exact_sku_on_core_term(monkeypatch):
    calls = _patch_woo_router(monkeypatch, {
        WOO_QUERY: [],
        WOO_CORE: PERFUMESCLUB_ROWS,
    })
    res = _run(woo.fetch_woocommerce_store_api_price(
        "theperfumesclub.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert calls == [WOO_QUERY, WOO_CORE]
    assert res is not None
    assert res["amount"] == pytest.approx(48.0)
    assert res["currency"] == "BHD"
    assert res["source_method"] == "woo_store_api"
    assert res["title"] == "YSL Black Opium (W) EDP 90 ml"
    assert res["in_stock"] is True
    assert res["retailer"] == "theperfumesclub.com"
    assert res["url"].endswith("/ysl-black-opium-w-edp-90-ml/")


def test_woo_core_term_flankers_still_rejected(monkeypatch):
    """(c) widening retrieval cannot widen acceptance: siblings only -> None."""
    _patch_woo_router(monkeypatch, {
        WOO_QUERY: [],
        WOO_CORE: PERFUMESCLUB_FLANKERS_ONLY,
    })
    res = _run(woo.fetch_woocommerce_store_api_price(
        "theperfumesclub.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert res is None


def test_woo_no_second_get_when_full_term_returns_rows(monkeypatch):
    """(d) latency pin: rows on the FULL term -> exactly one search."""
    calls = _patch_woo_router(monkeypatch, {WOO_QUERY: PERFUMESCLUB_ROWS})
    res = _run(woo.fetch_woocommerce_store_api_price(
        "theperfumesclub.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert res is not None
    assert calls == [WOO_QUERY]


def test_woo_no_second_get_when_rows_do_not_match(monkeypatch):
    """(d) pin: UNMATCHED rows are still rows — never retry on a non-empty
    response (0 usable rows == 0 ROWS, not 0 matches)."""
    unrelated = [_pc_row("Dior Sauvage EDT 100 ml", "dior-sauvage-edt-100-ml")]
    calls = _patch_woo_router(monkeypatch, {
        WOO_QUERY: unrelated,
        WOO_CORE: PERFUMESCLUB_ROWS,  # would match — must never be requested
    })
    res = _run(woo.fetch_woocommerce_store_api_price(
        "theperfumesclub.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert res is None
    assert calls == [WOO_QUERY]


def test_woo_flag_off_single_full_term_request(monkeypatch):
    """(e) flag-OFF byte-identity: one request, the full term, no ladder."""
    monkeypatch.setenv("ENABLE_ADAPTER_QUERY_LADDER", "false")
    calls = _patch_woo_router(monkeypatch, {
        WOO_QUERY: [],
        WOO_CORE: PERFUMESCLUB_ROWS,  # reachable only via the ladder
    })
    res = _run(woo.fetch_woocommerce_store_api_price(
        "theperfumesclub.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert res is None
    assert calls == [WOO_QUERY]


# ---------------------------------------------------------------------------
# (f) salla wiring
# ---------------------------------------------------------------------------

def _salla_item(name):
    return {
        "name": name,
        "price": 48.0,
        "currency": "BHD",
        "url": "https://reefperfumes.com/p/black-opium",
        "is_out_of_stock": False,
    }


def _patch_salla_router(monkeypatch, routes):
    calls = []

    def fake_get(url, *a, **kw):
        term = (kw.get("params") or {}).get("keyword")
        calls.append(term)
        return _FakeResp({"data": routes.get(term, [])})

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)
    return calls


def test_salla_ladder_retries_once_on_empty(monkeypatch):
    salla._STORE_ID_CACHE.clear()
    salla._STORE_ID_CACHE["reefperfumes.com"] = "254895921"
    calls = _patch_salla_router(monkeypatch, {
        WOO_QUERY: [],
        WOO_CORE: [_salla_item("YSL Black Opium EDP 90 ml")],
    })
    res = _run(salla.fetch_salla_api_price(
        "reefperfumes.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert calls == [WOO_QUERY, WOO_CORE]
    assert res is not None
    assert res["amount"] == pytest.approx(48.0)
    assert res["source_method"] == "salla_api"


def test_salla_no_retry_when_rows_returned(monkeypatch):
    salla._STORE_ID_CACHE.clear()
    salla._STORE_ID_CACHE["reefperfumes.com"] = "254895921"
    calls = _patch_salla_router(monkeypatch, {
        WOO_QUERY: [_salla_item("Some Other Perfume 50ml")],
        WOO_CORE: [_salla_item("YSL Black Opium EDP 90 ml")],
    })
    res = _run(salla.fetch_salla_api_price(
        "reefperfumes.com", WOO_QUERY, resolved_category="fragrances",
    ))
    assert res is None
    assert calls == [WOO_QUERY]


# ---------------------------------------------------------------------------
# (f) magento shape-B wiring (klinq — recon-proven 39.38 BHD genuine)
# ---------------------------------------------------------------------------

KLINQ_ITEM = {
    "name": "Black Opium EDP",
    "sku": "YSL-BO-EDP",
    "url_key": "yves-saint-laurent-black-opium-edp",
    "stock_status": "IN_STOCK",
    "brand_name": "Yves Saint Laurent",
    "price_range": {
        "minimum_price": {
            "final_price": {"value": 39.38, "currency": "BHD"},
            "regular_price": {"value": 39.38, "currency": "BHD"},
        }
    },
}

MG_QUERY = "Yves Saint Laurent Black Opium"
MG_CORE = "Black Opium"


def _patch_magento_router(monkeypatch, routes):
    calls = []

    async def fake_post(url, query, variables, headers):
        term = variables.get("phrase")
        calls.append(term)
        return {"data": {"products": {"items": routes.get(term, [])}}}

    monkeypatch.setattr(mg, "_post_graphql", fake_post)
    return calls


def test_magento_ladder_recovers_klinq_black_opium(monkeypatch):
    calls = _patch_magento_router(monkeypatch, {
        MG_QUERY: [],
        MG_CORE: [KLINQ_ITEM],
    })
    res = _run(mg.fetch_magento_graphql_price(
        "klinq.com", MG_QUERY, resolved_category="fragrances",
    ))
    assert calls == [MG_QUERY, MG_CORE]
    assert res is not None
    assert res["amount"] == pytest.approx(39.38)
    assert res["source_method"] == "magento_graphql_bhd"
    assert res["url"] == "https://klinq.com/yves-saint-laurent-black-opium-edp.html"


def test_magento_no_retry_when_rows_returned(monkeypatch):
    other = dict(KLINQ_ITEM, name="Libre EDP", url_key="ysl-libre-edp")
    calls = _patch_magento_router(monkeypatch, {
        MG_QUERY: [other],
        MG_CORE: [KLINQ_ITEM],
    })
    res = _run(mg.fetch_magento_graphql_price(
        "klinq.com", MG_QUERY, resolved_category="fragrances",
    ))
    assert res is None
    assert calls == [MG_QUERY]


# ---------------------------------------------------------------------------
# (f) algolia explicit-store wiring (en-bh.6thstreet.com)
# ---------------------------------------------------------------------------

AF1_QUERY = "Nike Air Force 1 '07 White"
AF1_CORE = "Air Force 1 '07 White"

SIXTHSTREET_HIT = {
    "name": "Air Force 1 '07 Sneakers - White",
    "brand": "Nike",
    "price": [{"BHD": {"default": 45.0}}],
    "url": "https://en-bh.6thstreet.com/nike-air-force-1-07-white.html",
    "in_stock": 1,
}


def _patch_algolia_router(monkeypatch, routes):
    calls = []

    async def fake_explicit(store, query):
        calls.append(query)
        return routes.get(query, [])

    monkeypatch.setattr(alg, "_algolia_query_explicit", fake_explicit)
    return calls


def test_algolia_explicit_ladder_retries_on_empty(monkeypatch):
    calls = _patch_algolia_router(monkeypatch, {
        AF1_QUERY: [],
        AF1_CORE: [SIXTHSTREET_HIT],
    })
    with patch("app.services.algolia_service.is_circuit_closed", return_value=True), \
         patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True):
        res = _run(alg.fetch_algolia_price(
            "en-bh.6thstreet.com", AF1_QUERY, "fashion",
        ))
    assert calls == [AF1_QUERY, AF1_CORE]
    assert res is not None
    assert res["amount"] == pytest.approx(45.0)
    assert res["source_method"] == "local_bhd"


def test_algolia_explicit_no_retry_when_hits_returned(monkeypatch):
    other = dict(SIXTHSTREET_HIT, name="Winflo 11 Sneakers - Black", brand="Nike")
    calls = _patch_algolia_router(monkeypatch, {
        AF1_QUERY: [other],
        AF1_CORE: [SIXTHSTREET_HIT],
    })
    with patch("app.services.algolia_service.is_circuit_closed", return_value=True), \
         patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True):
        res = _run(alg.fetch_algolia_price(
            "en-bh.6thstreet.com", AF1_QUERY, "fashion",
        ))
    assert res is None
    assert calls == [AF1_QUERY]
