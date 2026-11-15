"""INC-I1 PICTURE-MUST-MATCH (the S95-FIX incident lane) RED file B: the noon adapter's
PDP JSON-LD image, the scs wiring of the guard identity and the price-page override.

Spec: .qa-s80/INC-I1_UNIT_SPEC.md (sha256 5539e844...) sections 1.4, 2.4, 2.5, 2.8 and
5.3, as amended by the batch rulings RULINGS_INC_I1.md and the review
.qa-s80/INC-I1_SPEC_REVIEW.md: I1-R14 (under ENABLE_IMAGE_RELEVANCE_GUARD the price-page
override also requires https), I1-R20 (B-R03 also drives a q=-shaped product with a
brand; B-P01 uses N1, the image B-R01 proves the ON path copies) and the review's R-2
(B-P01 kills M24; B-P05 kills M25 / M26).

RED rows (test_r*) fail at base on an AssertionError only (no symbol of the unit is read:
the rows assert on the price dict, the recorded call and the result). PIN rows (test_p*)
are green at base and run with the full configuration (the knob set,
ENABLE_EXACT_PRICE_GATE true as in production, the HTTP / call recorders installed).

Hermetic: noon HTTP goes through a local fake of noon._http_get (the breaker quiet, the
politeness pause a no-op); every scs Phase-1 / Phase-2 leg and the cascade are patched.
Sentinels are built at run time; image paths carry no digit run of eight or more; the
banned-host sentinel is concatenated. Pure ASCII, LF.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import app.services.noon_service as noon  # noqa: E402
from app.services import jsonld_widen  # noqa: E402
from app.services import price_service  # noqa: E402

FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
KNOB = "IMAGE_RELEVANCE_CANDIDATES"
DG = "ENABLE_DATA_GUARDS_V2"
V2 = "ENABLE_IMAGE_PIPELINE_V2"
_QUIET = (
    "ENABLE_KB_FIRST_SERVE",
    "ENABLE_UNIFIED_SEARCH_BOUND",
    "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT",
    "ENABLE_PHASE2_RESIDUAL_GUARD",
    "ENABLE_PHASE2_CACHED_RATING",
    "ENABLE_JSONLD_RATING",
)


def _https(host, path):
    return "https://" + host + path


NOON_CDN = "f.nooncdn.com"
N1 = _https(NOON_CDN, "/p/pzsku/ZT1/45/_/x1/a1.jpg?width=1200")
N2 = _https(NOON_CDN, "/p/pzsku/ZT1/45/_/x2/a2.jpg?width=1200")
N3 = _https(NOON_CDN, "/p/pzsku/ZT1/45/_/x3/a3.jpg?width=1200")
SKU = "NZT1A"
PDP_URL = "https://www.noon.com/bahrain-en/s/ZT1/p/"
CASCADE = _https("img.example.com", "/cascade.jpg")
HTTP_PAGE_IMG = "http://" + "shop.example.com" + "/page.jpg"
FIMGS_IMG = _https("fim" + "gs.net", "/mdimg/perfume/375x500.77.jpg")
NOON_KEYS = {
    "amount",
    "currency",
    "retailer",
    "url",
    "estimated",
    "source_method",
    "title",
    "confidence",
    "in_stock",
    "seller",
    "brand",
}
BASE_KEYS = {"region", "page_scrape_image", "organic_results", "search_payload"}
BASE_CALL = {
    "region": "bahrain",
    "page_scrape_image": None,
    "organic_results": [],
    "search_payload": {"organic": []},
}
_MISSING = object()

HIT = {
    "name": "iPhone 15 256GB Blue 5G With FaceTime - Middle East Version",
    "brand": "Apple",
    "sku": SKU,
    "url": "iphone-15-256gb-blue-5g-with-facetime-middle-east-version",
    "price": 447.29,
    "sale_price": 294.23,
    "is_buyable": True,
    "store_name": "Synth-Seller",
}

TYGER = {
    "brand": "",
    "name": "Tyger",
    "variant": None,
    "category": "fragrances",
    "search_query": "Tyger",
    "_explicit": True,
}
DIOR_Q = {
    "brand": "Dior",
    "name": "Sauvage",
    "variant": "EDP",
    "category": "fragrances",
    "search_query": "Dior Sauvage EDP",
}
CAMERA = {
    "brand": "Synthbrand",
    "name": "Alpha",
    "variant": None,
    "category": "other",
    "search_query": "Synthbrand Alpha",
    "_vision": True,
}


def _product(image=_MISSING):
    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "iPhone 15 256GB Blue 5G With FaceTime - Middle East Version",
        "brand": {"@type": "Brand", "name": "Apple"},
        "sku": SKU,
        "offers": [
            {
                "@type": "Offer",
                "price": "294.23",
                "priceCurrency": "BHD",
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {"@type": "Organization", "name": "Synth-Seller"},
            }
        ],
    }
    if image is not _MISSING:
        product["image"] = image
    return product


def _pdp_html(product):
    return (
        "<html><head><title>x</title>"
        '<script type="application/ld+json">'
        + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList"})
        + "</script>"
        '<script type="application/ld+json">'
        + json.dumps(product)
        + "</script></head><body>page</body></html>"
    )


class FakeResp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _install_http(monkeypatch, hits, pdp_pages):
    calls = []

    def fake(url, headers=None, timeout=None):
        calls.append({"url": url, "headers": dict(headers or {})})
        if "/_svc/catalog/api/v3/search" in url:
            return FakeResp(200, {"hits": list(hits), "nbHits": len(hits)})
        for sku, page in pdp_pages.items():
            if "/%s/p/" % sku in url:
                return FakeResp(200, None, text=page)
        return FakeResp(404, None, text="not found")

    monkeypatch.setattr(noon, "_http_get", fake)
    return calls


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    """The flags this file reads are deleted (conftest loads the developer .env with
    override) and set per row; the exact gate is ON as in production; the noon breaker
    and politeness pause are quiet (no Redis, no sleep)."""
    for name in (FLAG, KNOB, DG, V2) + _QUIET:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setattr(noon, "is_circuit_closed", lambda provider: True)
    monkeypatch.setattr(noon, "record_failure", MagicMock())
    monkeypatch.setattr(noon, "record_success", MagicMock())

    async def _no_pause():
        return None

    monkeypatch.setattr(noon, "_polite_sleep", _no_pause)
    monkeypatch.setattr(noon, "ENABLE_PAGE_SCRAPE", True)


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _noon(monkeypatch, image=_MISSING, flag=None):
    _set(monkeypatch, FLAG, flag)
    calls = _install_http(monkeypatch, [HIT], {SKU: _pdp_html(_product(image))})
    out = asyncio.run(
        noon.fetch_noon_price(
            "noon.com", "iPhone 15 256GB", "BHD", resolved_category="electronics"
        )
    )
    return out, calls


def _scs_fetch(monkeypatch, product, *, partial_slot=None, price=None, cascade=CASCADE):
    """_fetch_product_data with every leg patched; returns (result, recorded image calls)."""
    from app.services import structured_comparison_service as scs

    service = scs.get_comparison_service()
    calls = []

    async def _image(*args, **kwargs):
        calls.append((args, dict(kwargs)))
        return cascade

    rating = {
        "rating": None,
        "review_count": None,
        "rating_verified": False,
        "rating_source": None,
    }
    monkeypatch.setattr(
        service, "_get_specs", AsyncMock(return_value={"size": "100 ml"})
    )
    monkeypatch.setattr(
        service, "_get_price", AsyncMock(return_value=dict(price) if price else None)
    )
    monkeypatch.setattr(
        service, "_get_reviews", AsyncMock(return_value={"review_summary": {}})
    )
    monkeypatch.setattr(service, "_get_verified_rating", AsyncMock(return_value=rating))
    monkeypatch.setattr(service, "_smart_fallback_extract", AsyncMock(return_value={}))
    monkeypatch.setattr(scs, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs, "get_product_image_url", _image)
    monkeypatch.setattr(scs, "tier2_fill_non_negotiables", AsyncMock(return_value={}))
    monkeypatch.setattr(
        scs, "tier3_synthesize_non_negotiables", AsyncMock(return_value={})
    )
    result = asyncio.run(
        service._fetch_product_data(
            dict(product),
            region="bahrain",
            include_specs=True,
            include_reviews=True,
            nocache=True,
            partial_slot=partial_slot,
        )
    )
    return result, calls


def _noon_price(image_url):
    return {
        "amount": 30.0,
        "currency": "BHD",
        "retailer": "noon.com",
        "url": PDP_URL,
        "estimated": False,
        "source_method": "page_scrape_jsonld",
        "title": "Tyger",
        "confidence": 0.9,
        "image_url": image_url,
    }


def _other_price(image_url):
    return {
        "amount": 30.0,
        "currency": "BHD",
        "retailer": "shop.example.com",
        "url": _https("shop.example.com", "/p/tyger"),
        "image_url": image_url,
    }


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------


def test_r01_noon_copies_the_first_https_raster(monkeypatch):
    """B-R01 (I1-7): flag ON copies the PDP's first https raster JSON-LD image as
    image_url; every other key and the request sequence equal the flag-OFF run."""
    monkeypatch.setenv(KNOB, "7")
    off, calls_off = _noon(monkeypatch, [N1, N2, N3], flag=None)
    on, calls_on = _noon(monkeypatch, [N1, N2, N3], flag="true")
    assert off is not None and on is not None
    assert on.get("image_url") == N1
    assert {k: v for k, v in on.items() if k != "image_url"} == off
    assert [c["url"] for c in calls_on] == [c["url"] for c in calls_off]


NOON_SHAPES = [
    (
        "http_then_https",
        ["http://" + NOON_CDN + "/p/a.jpg", _https(NOON_CDN, "/p/b.png")],
        _https(NOON_CDN, "/p/b.png"),
    ),
    (
        "imageobject_list",
        [{"@type": "ImageObject", "url": _https(NOON_CDN, "/p/c.jpg")}],
        _https(NOON_CDN, "/p/c.jpg"),
    ),
    (
        "imageobject_dict",
        {"@type": "ImageObject", "contentUrl": _https(NOON_CDN, "/p/d.webp")},
        _https(NOON_CDN, "/p/d.webp"),
    ),
    (
        "string",
        _https(NOON_CDN, "/p/f.jpg?width=1200"),
        _https(NOON_CDN, "/p/f.jpg?width=1200"),
    ),
]


@pytest.mark.parametrize(
    "image,want", [s[1:] for s in NOON_SHAPES], ids=[s[0] for s in NOON_SHAPES]
)
def test_r02_noon_image_shapes(monkeypatch, image, want):
    """B-R02: the schema.org image shapes (a list with an http first member, an
    ImageObject list, an ImageObject dict, a bare string)."""
    out, _calls = _noon(monkeypatch, image, flag="true")
    assert out is not None
    assert out.get("image_url") == want


def test_r03_scs_passes_the_identity_under_the_flag(monkeypatch):
    """B-R03 (+ I1-R20 / C-2): under the flag the one cascade call gains `relevance`
    with the Step-1 brand, the line (the product name), the canonical category and the
    slot; everything else is the base call."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "7")
    _result, calls = _scs_fetch(monkeypatch, TYGER, partial_slot=1)
    assert len(calls) == 1, calls
    args, kwargs = calls[0]
    assert args == ("Tyger",)
    assert kwargs == dict(
        BASE_CALL,
        relevance={"brand": "", "line": "Tyger", "category": "fragrances", "slot": 1},
    )
    _result, calls = _scs_fetch(monkeypatch, TYGER, partial_slot=None)
    assert len(calls) == 1, calls
    assert calls[0][1].get("relevance") == {
        "brand": "",
        "line": "Tyger",
        "category": "fragrances",
        "slot": None,
    }
    _result, calls = _scs_fetch(monkeypatch, DIOR_Q, partial_slot=0)
    assert len(calls) == 1, calls
    args, kwargs = calls[0]
    assert args == ("Dior Sauvage EDP",)
    assert kwargs == dict(
        BASE_CALL,
        relevance={
            "brand": "Dior",
            "line": "Sauvage",
            "category": "fragrances",
            "slot": 0,
        },
    )


def test_r04_override_requires_https_under_the_flag(monkeypatch):
    """I1-R14: under the guard an http page image never replaces the cascade picture
    (ENABLE_DATA_GUARDS_V2 OFF and ON); an https page image still does."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "7")
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_other_price(HTTP_PAGE_IMG))
    assert result["image_url"] == CASCADE
    monkeypatch.setenv(DG, "true")
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_other_price(HTTP_PAGE_IMG))
    assert result["image_url"] == CASCADE
    monkeypatch.delenv(DG, raising=False)
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_noon_price(N1))
    assert result["image_url"] == N1


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", [None, "false"])
def test_p01_noon_flag_off_full_config(monkeypatch, flag):
    """B-P01 (F5): flag OFF with an https image (N1) in the JSON-LD and the knob set:
    no image_url key, the base key set."""
    monkeypatch.setenv(KNOB, "7")
    out, _calls = _noon(monkeypatch, [N1, N2, N3], flag=flag)
    assert out is not None
    assert "image_url" not in out
    assert set(out) == NOON_KEYS


@pytest.mark.parametrize("flag", [None, "false"])
def test_p02_scs_flag_off_exact_call(monkeypatch, flag):
    """B-P02 (F1): flag OFF, the knob set: one call, the bare positional name and exactly
    the four base keywords with their base values."""
    _set(monkeypatch, FLAG, flag)
    monkeypatch.setenv(KNOB, "7")
    result, calls = _scs_fetch(monkeypatch, TYGER, partial_slot=1)
    assert len(calls) == 1, calls
    args, kwargs = calls[0]
    assert args == ("Tyger",)
    assert set(kwargs) == BASE_KEYS
    assert kwargs["page_scrape_image"] is None
    assert kwargs == BASE_CALL
    assert result["image_url"] == CASCADE


def test_p03_scs_camera_product_never_gets_the_identity(monkeypatch):
    """B-P03 (F1, I1-1): flag ON, the knob set: a camera product's call carries exactly
    the base keywords."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "7")
    _result, calls = _scs_fetch(monkeypatch, CAMERA, partial_slot=0)
    assert len(calls) == 1, calls
    args, kwargs = calls[0]
    assert args == ("Synthbrand Alpha",)
    assert set(kwargs) == BASE_KEYS


def test_p04_override_branches_for_a_noon_image(monkeypatch):
    """B-P04 (spec 1.4, Q4): a noon-shaped price with N1: V2 OFF + DG OFF -> N1; DG ON
    -> N1; V2 ON -> the cascade picture (D08's host allowlist refuses f.nooncdn.com)."""
    monkeypatch.setenv(KNOB, "7")
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_noon_price(N1))
    assert result["image_url"] == N1
    monkeypatch.setenv(DG, "true")
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_noon_price(N1))
    assert result["image_url"] == N1
    monkeypatch.delenv(DG, raising=False)
    monkeypatch.setenv(V2, "true")
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_noon_price(N1))
    assert result["image_url"] == CASCADE
    brand_domains = price_service.OFFICIAL_BRAND_DOMAINS
    assert jsonld_widen.allowed_image_url(N1, PDP_URL, brand_domains) is None
    assert jsonld_widen.allowed_image_url(N1, N1) == N1


NOON_REJECTS = [
    ("svg", [_https(NOON_CDN, "/p/e.svg")]),
    ("ip_host", [_https("10.0.0.1", "/g.jpg")]),
    ("none", None),
    ("missing", _MISSING),
    ("http_only", ["http://" + NOON_CDN + "/p/h.jpg"]),
    ("non_public_host", [_https("img.example.test", "/i.jpg")]),
    ("denied_host", [FIMGS_IMG]),
]


@pytest.mark.parametrize(
    "image", [r[1] for r in NOON_REJECTS], ids=[r[0] for r in NOON_REJECTS]
)
def test_p05_noon_image_rejects(monkeypatch, image):
    """B-P05: flag ON, an image the D08 policy refuses (svg, an IP or non-public host,
    http only, a banned host, none, missing): no image_url key (kills M25 / M26)."""
    monkeypatch.setenv(KNOB, "7")
    out, _calls = _noon(monkeypatch, image, flag="true")
    assert out is not None
    assert "image_url" not in out


@pytest.mark.parametrize("flag", [None, "false"])
def test_p06_override_flag_off_keeps_the_base_branches(monkeypatch, flag):
    """I1-R14, the OFF side: with the guard OFF the base override still lets an http
    page image replace the cascade picture (V2 OFF, DG OFF: production today)."""
    _set(monkeypatch, FLAG, flag)
    monkeypatch.setenv(KNOB, "7")
    result, _calls = _scs_fetch(monkeypatch, TYGER, price=_other_price(HTTP_PAGE_IMG))
    assert result["image_url"] == HTTP_PAGE_IMG
