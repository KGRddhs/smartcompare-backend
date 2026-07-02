"""Wave C C3 — the noon-BH direct catalog+PDP adapter (fetch_noon_price).

CONTRACT (recon_electronics.json `noon_contract`, live-proven 2026-07-02 +
recon_fragrances.json noon PDPs; kpiE2E RS-5 = wire noon as a first-class
adapter instead of relying on organic retrieval):

  SEARCH  GET /_svc/catalog/api/v3/search?q=&limit=10 with the HARD-PINNED
          ``x-locale: en-bh`` header — without it the response is the KSA/SAR
          catalog with an IDENTICAL shape and NO currency field (the silent
          wrong-currency failure mode). Currency is PINNED BHD from the header
          (the ALGOLIA_EXPLICIT_STORES pinned-currency pattern).
  MATCH   the FULL gate chain (counterfeit / accessory-for-category /
          numbers_match / strict-or-selection_primary_admits fence /
          variant_mismatch / _selection_match) with candidate_brand =
          hits[].brand or "" (brand is NULLABLE — the Switch-2 bundle).
  PDP     GET /bahrain-en/{slug}/{sku}/p/ → Product JSON-LD. AUTHORITY RULE:
          offers[0] IS the buy-box (live-proven: offers[0].price 294.23 == the
          PLP sale_price; offers[1] 266.09 = a CHEAPER non-buy-box seller that
          min() would mis-select) — advance in noon's OWN offer order ONLY past
          an offer a fail-closed guard rejects (non-BHD / refurbished-renewed
          condition / explicit OOS / the implausible-low fragrance floor);
          NEVER min(offers[].price).

LATENCY BUDGET (the A5 footlocker-literal report language): the literal
``Source("noon.com", "bahrain", ..., mechanism="noon_catalog")`` row loads
flag-independently — tagging it wires exactly ONE bounded source into the
K-capped (``BH_GCC_FANOUT_K``, default 6) ``noon_catalog`` selector; the
prefetch wraps it in the per-source 10s ``_timeout_none`` (overlapped with the
~6s serper_shopping wait) and the adapter itself is politeness-spaced +
request-capped, so the addition is 1 bounded K-capped source per category,
never an unbounded fan-out widening. The row is placed AFTER the existing
gcc-tier ``is_render_only`` noon literal (untouched — recon failure-mode 7),
so ``registry_tier``/``score_source`` still resolve noon.com at the FIRST
(gcc, 1.5) row: noon stays SECONDARY authority (recon failure-mode 5 — keep
sharafdg/extra ranked above it) and the pinned
``test_noon_stays_gcc_tier_not_promoted`` invariant holds.

All HTTP mocked (fixtures = the recon live proofs); breaker + politeness
patched so NO prod Redis breaker/cache write ever fires from this file.
Run: python -m pytest tests/test_noon_adapter.py -q
"""
import json
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import MagicMock

import app.services.noon_service as noon
from app.services.noon_service import (
    fetch_noon_price,
    _match_noon_hits,
    _parse_hit_amount,
    _hit_fields,
    _select_offer,
    _extract_product_jsonld,
    _SEARCH_HEADERS,
    _NOON_SPACING_RANGE,
    _MAX_REQUESTS_PER_CALL,
)


# ---------------------------------------------------------------------------
# Fixtures — from the recon live proofs (2026-07-02)
# ---------------------------------------------------------------------------

IPHONE_HIT = {
    # search BHD live proof: N53432838A price 447.29 sale 294.23 is_buyable
    "name": "iPhone 15 256GB Blue 5G With FaceTime - Middle East Version",
    "brand": "Apple",
    "sku": "N53432838A",
    "url": "iphone-15-256gb-blue-5g-with-facetime-middle-east-version",
    "price": 447.29,
    "sale_price": 294.23,
    "is_buyable": True,
    "store_name": "Viola-UAE",
}

IPHONE_PDP_PRODUCT = {
    # PDP JSON-LD live proof: offers[0] 294.23 BHD InStock seller Viola-UAE ==
    # the buy-box; offers[1] 266.09 = the cheaper non-buy-box seller.
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "iPhone 15 256GB Blue 5G With FaceTime - Middle East Version",
    "brand": {"@type": "Brand", "name": "Apple"},
    "sku": "N53432838A",
    "offers": [
        {
            "@type": "Offer", "price": "294.23", "priceCurrency": "BHD",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@type": "Organization", "name": "Viola-UAE"},
        },
        {
            "@type": "Offer", "price": "266.09", "priceCurrency": "BHD",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@type": "Organization", "name": "cheaper-non-buybox"},
        },
    ],
}

CARBON_HIT = {
    # recon_fragrances: noon N12660141A Luna Rossa Carbon EDT 100ml
    "name": "Luna Rossa Carbon EDT 100ml",
    "brand": "PRADA",
    "sku": "N12660141A",
    "url": "luna-rossa-carbon-edt-100ml",
    "price": 26.8,
    "sale_price": None,
    "is_buyable": True,
    "store_name": "noon",
}

CARBON_PDP_PRODUCT = {
    # offers order per the live proof: 24.12 (first-party noon) and 24.06 sit
    # UNDER the 25-BHD/100ml designer floor; 26.8 is the first above-floor
    # in-stock offer in noon's own order (NOT the min — 24.06 is cheaper).
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Luna Rossa Carbon EDT 100ml",
    "brand": {"@type": "Brand", "name": "PRADA"},
    "sku": "N12660141A",
    "offers": [
        {"@type": "Offer", "price": "24.12", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "seller": {"@type": "Organization", "name": "noon"}},
        {"@type": "Offer", "price": "24.06", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "seller": {"@type": "Organization", "name": "third-party-a"}},
        {"@type": "Offer", "price": "26.8", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "seller": {"@type": "Organization", "name": "third-party-b"}},
        {"@type": "Offer", "price": "27.81", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "seller": {"@type": "Organization", "name": "third-party-c"}},
    ],
}


def _pdp_html(product: dict) -> str:
    return (
        "<html><head><title>x</title>"
        '<script type="application/ld+json">'
        + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList"})
        + "</script>"
        '<script type="application/ld+json">'
        + json.dumps(product)
        + "</script></head><body>page</body></html>"
    )


def _search_payload(hits):
    return {"hits": list(hits), "nbHits": len(hits)}


class FakeResp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _install_http(monkeypatch, search_results, pdp_pages=None, calls=None):
    """Route noon HTTP through a fake.

    ``search_results``: list consumed per search call (payload dict → 200 JSON;
    FakeResp → as-is; Exception → raised = transport failure). Exhausted list
    reuses the last entry. ``pdp_pages``: {sku: html-or-FakeResp}.
    Returns the calls list ({url, headers} per request).
    """
    calls = calls if calls is not None else []
    pdp_pages = pdp_pages or {}
    state = {"i": 0}

    def fake(url, headers=None, timeout=None):
        calls.append({"url": url, "headers": dict(headers or {})})
        if "/_svc/catalog/api/v3/search" in url:
            i = min(state["i"], len(search_results) - 1)
            state["i"] += 1
            entry = search_results[i]
            if isinstance(entry, Exception):
                raise entry
            if isinstance(entry, FakeResp):
                return entry
            return FakeResp(200, entry)
        for sku, page in pdp_pages.items():
            if f"/{sku}/p/" in url:
                if isinstance(page, FakeResp):
                    return page
                return FakeResp(200, None, text=page)
        return FakeResp(404, None, text="not found")

    monkeypatch.setattr(noon, "_http_get", fake)
    return calls


@pytest.fixture(autouse=True)
def breaker(monkeypatch):
    """Quiet the breaker (NO prod Redis writes from unit tests) + politeness
    pause recorder. Individual tests re-patch to assert breaker behaviour."""
    state = {"pauses": 0, "failure": MagicMock(), "success": MagicMock()}
    monkeypatch.setattr(noon, "is_circuit_closed", lambda p: True)
    monkeypatch.setattr(noon, "record_failure", state["failure"])
    monkeypatch.setattr(noon, "record_success", state["success"])

    async def _fake_pause():
        state["pauses"] += 1

    monkeypatch.setattr(noon, "_polite_sleep", _fake_pause)
    return state


# ---------------------------------------------------------------------------
# 1. The x-locale header HARD PIN (silent-SAR failure mode 1)
# ---------------------------------------------------------------------------

def test_search_headers_pin_en_bh_locale():
    # The module constant itself is the first line of defence.
    assert _SEARCH_HEADERS["x-locale"] == "en-bh"
    assert _SEARCH_HEADERS["x-platform"] == "web"
    assert _SEARCH_HEADERS["x-mp"] == "noon"
    assert "application/json" in _SEARCH_HEADERS["accept"]


@pytest.mark.asyncio
async def test_header_on_every_search_request(monkeypatch):
    """EVERY search request (both ladder terms) carries x-locale: en-bh —
    without it noon serves the SAR catalog with an identical shape and no
    currency field anywhere (unit-testable failure mode 1)."""
    monkeypatch.setattr(
        noon, "build_adapter_search_terms",
        lambda name, cat=None: [name, "core term"],
    )
    calls = _install_http(
        monkeypatch,
        search_results=[_search_payload([]), _search_payload([])],
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None  # zero rows on both terms
    search_calls = [c for c in calls if "/search" in c["url"]]
    assert len(search_calls) == 2
    for c in search_calls:
        assert c["headers"].get("x-locale") == "en-bh", (
            "silent-SAR hazard: a search request went out WITHOUT the "
            "x-locale: en-bh header"
        )


# ---------------------------------------------------------------------------
# 2. BHD pinning + genuine method + full happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_happy_path_iphone_genuine_bhd(monkeypatch):
    _install_http(
        monkeypatch,
        search_results=[_search_payload([IPHONE_HIT])],
        pdp_pages={"N53432838A": _pdp_html(IPHONE_PDP_PRODUCT)},
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is not None
    assert out["currency"] == "BHD"
    # Reuses the JSON-LD page-scrape genuine method — no new method plumbing,
    # no eval-parity mirror needed (page_scrape_jsonld ∈ _GENUINE_BH_SOURCE_METHODS).
    assert out["source_method"] == "page_scrape_jsonld"
    assert out["estimated"] is False
    assert out["retailer"] == "noon.com"
    assert out["url"] == (
        "https://www.noon.com/bahrain-en/"
        "iphone-15-256gb-blue-5g-with-facetime-middle-east-version/N53432838A/p/"
    )
    assert out["in_stock"] is True
    assert out["title"].startswith("iPhone 15 256GB")
    assert out["brand"] == "Apple"
    # failure mode 5 — the marketplace seller is stamped in the metadata.
    assert out["seller"] == "Viola-UAE"


def test_genuine_method_is_in_the_genuine_set():
    from app.services.price_service import _GENUINE_BH_SOURCE_METHODS
    assert "page_scrape_jsonld" in _GENUINE_BH_SOURCE_METHODS


# ---------------------------------------------------------------------------
# 3. AUTHORITY RULE — offers[0] buy-box, NEVER min(price)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_buy_box_not_min(monkeypatch):
    """offers[0] 294.23 (the buy-box == the PLP sale_price) wins over the
    CHEAPER offers[1] 266.09 — min() would mis-select the non-buy-box seller."""
    _install_http(
        monkeypatch,
        search_results=[_search_payload([IPHONE_HIT])],
        pdp_pages={"N53432838A": _pdp_html(IPHONE_PDP_PRODUCT)},
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is not None
    assert out["amount"] == pytest.approx(294.23), (
        "min(offers[].price) mis-selection — the buy-box offers[0] must win"
    )


def test_select_offer_unit_buy_box_first():
    sel = _select_offer(
        IPHONE_PDP_PRODUCT["offers"], "iPhone 15 256GB",
        IPHONE_PDP_PRODUCT["name"],
    )
    assert sel is not None
    assert sel["offer_index"] == 0
    assert sel["amount"] == pytest.approx(294.23)
    assert sel["seller"] == "Viola-UAE"


# ---------------------------------------------------------------------------
# 4. sale_price-null fallback (iPad-M3-class rows)
# ---------------------------------------------------------------------------

def test_parse_hit_amount_sale_price_null_falls_back_to_price():
    assert _parse_hit_amount({"price": 276.57, "sale_price": None}) == pytest.approx(276.57)
    # sale present → sale wins (the CURRENT shelf price)
    assert _parse_hit_amount({"price": 447.29, "sale_price": 294.23}) == pytest.approx(294.23)
    # garbage / non-positive → None (never a fabricated amount)
    assert _parse_hit_amount({"price": 0, "sale_price": None}) is None
    assert _parse_hit_amount({"price": True, "sale_price": None}) is None
    assert _parse_hit_amount({}) is None


# ---------------------------------------------------------------------------
# 5. refurb / renewed / bundle rejection
# ---------------------------------------------------------------------------

def test_refurbished_offer_row_skipped_new_offer_wins():
    offers = [
        {"@type": "Offer", "price": "200.00", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "itemCondition": "https://schema.org/RefurbishedCondition",
         "seller": {"name": "refurb-seller"}},
        dict(IPHONE_PDP_PRODUCT["offers"][0]),
    ]
    sel = _select_offer(offers, "iPhone 15 256GB", IPHONE_PDP_PRODUCT["name"])
    assert sel is not None
    assert sel["amount"] == pytest.approx(294.23)
    assert sel["offer_index"] == 1


def test_all_refurb_offers_yield_none():
    offers = [
        {"@type": "Offer", "price": "200.00", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "itemCondition": "https://schema.org/RefurbishedCondition"},
        {"@type": "Offer", "price": "210.00", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "itemCondition": "renewed"},
    ]
    assert _select_offer(offers, "iPhone 15 256GB", "iPhone 15 256GB Blue") is None


def test_refurbished_prefixed_listing_rejected_at_match():
    """'Refurbished - ...' listings are SEPARATE noon skus (recon variant &
    condition handling) — the condition token-add must reject at the matcher."""
    hit = dict(IPHONE_HIT)
    hit["name"] = "Refurbished - iPhone 15 256GB Blue 5G With FaceTime"
    assert _match_noon_hits([hit], "iPhone 15 256GB", "electronics") == []


def test_bundle_sku_rejected_token_add_and_console_accepted():
    """The Mario-Kart-bundle live proof: a BUNDLE is a separate sellable sku —
    the keystone token-add rejection must hold. The genuine console title (with
    tolerated electronics padding adds) must still pass — BOTH directions."""
    bundle = {
        "name": "Nintendo Switch 2 + Mario Kart World Bundle",
        "brand": None,  # brand CAN BE NULL (live-proven on this exact sku)
        "sku": "N70183207V",
        "url": "nintendo-switch-2-mario-kart-world-bundle",
        "price": 243.49, "sale_price": None,
        "is_buyable": True, "store_name": "callmateonline",
    }
    console = {
        "name": "Nintendo Switch 2 Gaming Console 256GB Black",
        "brand": None,
        "sku": "N99999999A",
        "url": "nintendo-switch-2-gaming-console-256gb-black",
        "price": 225.0, "sale_price": None,
        "is_buyable": True, "store_name": "noon",
    }
    matches = _match_noon_hits([bundle, console], "Nintendo Switch 2", "electronics")
    skus = [m["sku"] for m in matches]
    assert "N70183207V" not in skus, "bundle sku must be token-add-rejected"
    assert "N99999999A" in skus, "the genuine console must not be over-rejected"


# ---------------------------------------------------------------------------
# 6. brand-null → candidate_brand ""
# ---------------------------------------------------------------------------

def test_hit_fields_brand_null_maps_to_empty_string():
    fields = _hit_fields({"name": "X", "brand": None, "sku": "N1", "url": "x",
                          "price": 1.0, "sale_price": None, "is_buyable": True})
    assert fields["brand"] == ""


# ---------------------------------------------------------------------------
# 7. retrieval-term ladder integration (adapter contract + F2 politeness)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ladder_zero_rows_tries_core_term(monkeypatch):
    monkeypatch.setattr(
        noon, "build_adapter_search_terms",
        lambda name, cat=None: [name, "iPhone core"],
    )
    calls = _install_http(
        monkeypatch,
        search_results=[_search_payload([]), _search_payload([IPHONE_HIT])],
        pdp_pages={"N53432838A": _pdp_html(IPHONE_PDP_PRODUCT)},
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is not None
    assert len([c for c in calls if "/search" in c["url"]]) == 2


@pytest.mark.asyncio
async def test_ladder_rows_but_no_match_never_second_request(monkeypatch):
    monkeypatch.setattr(
        noon, "build_adapter_search_terms",
        lambda name, cat=None: [name, "core"],
    )
    wrong = {"name": "Galaxy Z Fold 7 512GB", "brand": "Samsung", "sku": "N2",
             "url": "galaxy-z-fold-7", "price": 700.0, "sale_price": None,
             "is_buyable": True, "store_name": "noon"}
    calls = _install_http(monkeypatch, search_results=[_search_payload([wrong])])
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert len([c for c in calls if "/search" in c["url"]]) == 1, (
        "rows returned — matched or not — must never trigger the second term"
    )


@pytest.mark.asyncio
async def test_ladder_transport_failure_stops_no_core_retry(monkeypatch):
    """F2 politeness — a TRANSPORT failure stops the ladder; never a core-term
    retry against an erroring store (the woo/salla None-sentinel semantics)."""
    monkeypatch.setattr(
        noon, "build_adapter_search_terms",
        lambda name, cat=None: [name, "core"],
    )
    calls = _install_http(
        monkeypatch, search_results=[RuntimeError("boom"), _search_payload([IPHONE_HIT])],
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert len([c for c in calls if "/search" in c["url"]]) == 1


# ---------------------------------------------------------------------------
# 8. wrong-brand fence integration (the central selection_primary_admits fence)
# ---------------------------------------------------------------------------

def test_wrong_brand_noon_hit_rejected_fence():
    """A cross-brand same-model-word fashion hit must be rejected by the
    strict-or-selection-primary fence (candidate_brand contradicts the query's
    padding-brand token); the SAME title under the CORRECT brand passes —
    both directions pinned."""
    golden_goose = {
        "name": "Superstar White Sneakers", "brand": "Golden Goose",
        "sku": "N3", "url": "gg-superstar", "price": 145.0,
        "sale_price": None, "is_buyable": True, "store_name": "noon",
    }
    adidas = dict(golden_goose)
    adidas["brand"] = "Adidas"
    adidas["sku"] = "N4"

    matches = _match_noon_hits(
        [golden_goose, adidas], "Adidas Superstar White", "fashion")
    skus = [m["sku"] for m in matches]
    assert "N3" not in skus, "wrong-brand hit leaked through the fence"
    assert "N4" in skus, "correct-brand hit over-rejected"


# ---------------------------------------------------------------------------
# 9. silent-SAR / non-BHD offer fail-closed
# ---------------------------------------------------------------------------

def test_non_bhd_offer_rejected_fail_closed():
    sar_only = [
        {"@type": "Offer", "price": "2499.00", "priceCurrency": "SAR",
         "availability": "https://schema.org/InStock"},
    ]
    assert _select_offer(sar_only, "iPhone 15 256GB", "iPhone 15 256GB") is None
    # mixed: the SAR offer is skipped, the BHD one (later in noon's order) wins
    mixed = sar_only + [dict(IPHONE_PDP_PRODUCT["offers"][0])]
    sel = _select_offer(mixed, "iPhone 15 256GB", "iPhone 15 256GB")
    assert sel is not None and sel["amount"] == pytest.approx(294.23)


# ---------------------------------------------------------------------------
# 10. OOS offer rows skipped (fail-closed availability)
# ---------------------------------------------------------------------------

def test_oos_buy_box_advances_to_in_stock_offer():
    offers = [
        {"@type": "Offer", "price": "294.23", "priceCurrency": "BHD",
         "availability": "http://schema.org/OutOfStock"},
        {"@type": "Offer", "price": "299.00", "priceCurrency": "BHD",
         "availability": "https://schema.org/InStock",
         "seller": {"name": "second"}},
    ]
    sel = _select_offer(offers, "iPhone 15 256GB", "iPhone 15 256GB Blue")
    assert sel is not None
    assert sel["offer_index"] == 1
    assert sel["in_stock"] is True


# ---------------------------------------------------------------------------
# 11. the 25-BHD/100ml designer floor interplay (recon_fragrances)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fragrance_floor_advances_past_sub_floor_offers(monkeypatch):
    """Luna Rossa Carbon live proof: the buy-box 24.12 (first-party noon) and
    24.06 sit UNDER the 25-BHD/100ml designer floor — the guard advances in
    noon's OWN order to the first above-floor in-stock offer (26.8), which is
    NOT the min (24.06 is cheaper). Authority order preserved, floor enforced."""
    _install_http(
        monkeypatch,
        search_results=[_search_payload([CARBON_HIT])],
        pdp_pages={"N12660141A": _pdp_html(CARBON_PDP_PRODUCT)},
    )
    out = await fetch_noon_price(
        "noon.com", "Prada Luna Rossa Carbon Eau de Toilette 100ml", "BHD",
        resolved_category="fragrances",
    )
    assert out is not None
    assert out["amount"] == pytest.approx(26.8), (
        "must be the FIRST above-floor offer in noon's order — never the "
        "sub-floor buy-box (24.12) and never the min (24.06)"
    )
    assert out["source_method"] == "page_scrape_jsonld"
    assert out["in_stock"] is True


# ---------------------------------------------------------------------------
# 12. flag-OFF byte-identity + selector / registry row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disabled_by_page_scrape_flag(monkeypatch):
    calls = _install_http(monkeypatch, search_results=[_search_payload([IPHONE_HIT])])
    monkeypatch.setattr(noon, "ENABLE_PAGE_SCRAPE", False)
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert calls == [], "flag OFF must be a no-op — zero HTTP"


@pytest.mark.asyncio
async def test_unknown_domain_returns_none(monkeypatch):
    calls = _install_http(monkeypatch, search_results=[_search_payload([IPHONE_HIT])])
    out = await fetch_noon_price("not-noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert calls == []


def test_selector_returns_literal_row_flag_independently(monkeypatch):
    """The noon literal Source row loads FLAG-INDEPENDENTLY (a literal row is
    never gated by ENABLE_BH_GCC_CATALOG_SOURCES — the PR#13 lesson, stated
    deliberately): 1 bounded K-capped source for exactly (electronics,
    fragrances, fashion, other)."""
    monkeypatch.delenv("ENABLE_BH_GCC_CATALOG_SOURCES", raising=False)
    from app.services.source_router import (
        get_noon_sources_for_category, _fanout_k, SOURCE_REGISTRY,
    )
    for cat in ("electronics", "fragrances", "fashion", "other"):
        srcs = get_noon_sources_for_category(cat)
        assert [s.domain for s in srcs] == ["noon.com"], cat
        assert srcs[0].mechanism == "noon_catalog"
        assert srcs[0].tier == "bahrain"
        assert srcs[0].currency == "BHD"
        assert len(srcs) <= _fanout_k()
    for cat in ("grocery", "supplements", "makeup", "skincare", "haircare"):
        assert get_noon_sources_for_category(cat) == [], cat

    # recon failure-mode 7: the existing gcc-tier is_render_only literal is
    # UNTOUCHED — both rows coexist; registry_tier/score_source resolve at the
    # FIRST (gcc) row so noon is NOT promoted to authoritative.
    gcc_rows = [s for s in SOURCE_REGISTRY
                if s.domain == "noon.com" and s.tier == "gcc"]
    assert len(gcc_rows) == 1
    assert gcc_rows[0].is_render_only is True
    assert gcc_rows[0].mechanism == ""

    from app.services.source_router import registry_tier, score_source
    assert registry_tier("noon.com") == "gcc"  # NOT promoted (pinned elsewhere too)
    assert score_source(
        "https://www.noon.com/bahrain-en/x/N1/p/", "electronics") == 1.5


def test_noon_mechanism_is_a_direct_adapter_mechanism():
    """noon_catalog must be classified a DIRECT adapter mechanism so the
    bahrain-tier row is never mistaken for a discovery-only source (which
    would perturb the _pf_eligible discovery-prefetch invariants)."""
    import app.services.structured_comparison_service as scs
    assert "noon_catalog" in scs._DIRECT_ADAPTER_MECHANISMS


# ---------------------------------------------------------------------------
# 13. circuit breaker (recon failure mode 3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circuit_open_returns_none_no_http(monkeypatch, breaker):
    calls = _install_http(monkeypatch, search_results=[_search_payload([IPHONE_HIT])])
    monkeypatch.setattr(noon, "is_circuit_closed", lambda p: False)
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert calls == []


@pytest.mark.asyncio
async def test_429_records_failure(monkeypatch, breaker):
    _install_http(monkeypatch, search_results=[FakeResp(429, None, "slow down")])
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert breaker["failure"].called
    assert breaker["failure"].call_args[0][0] == noon._NOON_PROVIDER


@pytest.mark.asyncio
async def test_5xx_records_failure_transport_too(monkeypatch, breaker):
    _install_http(monkeypatch, search_results=[FakeResp(503, None, "down")])
    await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                           resolved_category="electronics")
    assert breaker["failure"].called

    breaker["failure"].reset_mock()
    _install_http(monkeypatch, search_results=[RuntimeError("net down")])
    await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                           resolved_category="electronics")
    assert breaker["failure"].called


@pytest.mark.asyncio
async def test_200_records_success(monkeypatch, breaker):
    _install_http(
        monkeypatch,
        search_results=[_search_payload([IPHONE_HIT])],
        pdp_pages={"N53432838A": _pdp_html(IPHONE_PDP_PRODUCT)},
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is not None
    assert breaker["success"].called


# ---------------------------------------------------------------------------
# 14. politeness — spacing + per-run request cap (recon failure mode 3)
# ---------------------------------------------------------------------------

def test_spacing_range_pinned():
    assert _NOON_SPACING_RANGE == (0.8, 1.2)
    assert _MAX_REQUESTS_PER_CALL == 4


@pytest.mark.asyncio
async def test_pause_between_requests(monkeypatch, breaker):
    """search → PDP = 2 requests = exactly 1 politeness pause between them."""
    _install_http(
        monkeypatch,
        search_results=[_search_payload([IPHONE_HIT])],
        pdp_pages={"N53432838A": _pdp_html(IPHONE_PDP_PRODUCT)},
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is not None
    assert breaker["pauses"] == 1


@pytest.mark.asyncio
async def test_per_run_request_cap(monkeypatch):
    """The per-call HTTP request count is HARD-capped: 2 ladder searches + PDP
    confirms can never exceed _MAX_REQUESTS_PER_CALL even when every PDP 404s."""
    monkeypatch.setattr(
        noon, "build_adapter_search_terms",
        lambda name, cat=None: [name, "core"],
    )
    many_hits = []
    for i in range(6):
        h = dict(IPHONE_HIT)
        h["sku"] = f"N5343283{i}A"
        h["url"] = f"iphone-15-256gb-variant-{i}"
        many_hits.append(h)
    # first term zero rows → second term returns 6 matchable hits; every PDP
    # 404s so the confirm loop keeps trying until a bound stops it.
    calls = _install_http(
        monkeypatch,
        search_results=[_search_payload([]), _search_payload(many_hits)],
        pdp_pages={},  # every PDP → 404
    )
    out = await fetch_noon_price("noon.com", "iPhone 15 256GB", "BHD",
                                 resolved_category="electronics")
    assert out is None
    assert len(calls) <= _MAX_REQUESTS_PER_CALL


# ---------------------------------------------------------------------------
# 15. JSON-LD extraction robustness
# ---------------------------------------------------------------------------

def test_extract_product_jsonld_finds_product_among_blocks():
    html = _pdp_html(IPHONE_PDP_PRODUCT)
    node = _extract_product_jsonld(html)
    assert node is not None
    assert node["sku"] == "N53432838A"


def test_extract_product_jsonld_handles_graph_and_garbage():
    graph_doc = {"@context": "https://schema.org",
                 "@graph": [{"@type": "WebSite"}, IPHONE_PDP_PRODUCT]}
    html = (
        '<script type="application/ld+json">{not json</script>'
        '<script type="application/ld+json">'
        + json.dumps(graph_doc) + "</script>"
    )
    node = _extract_product_jsonld(html)
    assert node is not None and node.get("sku") == "N53432838A"
    assert _extract_product_jsonld("<html>no ldjson</html>") is None
    assert _extract_product_jsonld("") is None


# ---------------------------------------------------------------------------
# 16. cascade wiring — the family-spec consume short-circuits on a noon hit
# ---------------------------------------------------------------------------

_ALL_SELECTORS = (
    "get_shopify_sources_for_category", "get_algolia_sources_for_category",
    "get_sitemap_sources_for_category", "get_jsonapi_sources_for_category",
    "get_woo_sources_for_category", "get_salla_sources_for_category",
    "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
    "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
    "get_noon_sources_for_category",
)


@pytest.mark.asyncio
async def test_noon_genuine_hit_short_circuits_cascade(monkeypatch):
    """Mirror of test_woo_genuine_hit_short_circuits: a genuine noon
    page_scrape_jsonld hit through the data-driven `_new_adapter_specs`
    machinery short-circuits BEFORE Serper discovery. Cache/DB writes are
    neutralized (no prod write from a unit test)."""
    import app.services.structured_comparison_service as scs
    from app.services.source_router import Source
    svc = scs.get_comparison_service()

    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)
    for name in _ALL_SELECTORS:
        if name != "get_noon_sources_for_category":
            monkeypatch.setattr(scs, name, lambda c: [])
    monkeypatch.setattr(
        scs, "get_noon_sources_for_category",
        lambda c: [Source("noon.com", "bahrain", ("electronics",), 1.5,
                          mechanism="noon_catalog", currency="BHD")],
    )

    async def fake_noon(domain, product_name, currency="BHD", **kwargs):
        return {
            "amount": 294.23, "currency": "BHD", "retailer": "noon.com",
            "url": "https://www.noon.com/bahrain-en/iphone-15-256gb/N53432838A/p/",
            "in_stock": True, "title": "iPhone 15 256GB Blue - Middle East Version",
            "brand": "Apple", "estimated": False,
            "source_method": "page_scrape_jsonld", "confidence": 0.9,
        }
    monkeypatch.setattr(scs, "fetch_noon_price", fake_noon)

    async def boom_search(*a, **k):
        raise AssertionError("discovery reached — noon did not short-circuit")
    monkeypatch.setattr(scs, "search_web", boom_search)

    price = await svc._get_price(
        brand="Apple", name="iPhone 15", variant="256GB", region="bahrain",
        search_query="iPhone 15 256GB", nocache=True, category="electronics",
    )
    assert price is not None
    assert price["source_method"] == "page_scrape_jsonld"
    assert price["retailer"] == "noon.com"
    assert abs(price["amount"] - 294.23) < 0.01
