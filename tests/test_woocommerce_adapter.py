"""Offline, fixture-based unit tests for fetch_woocommerce_store_api_price (R1).

NO network — monkeypatches woocommerce_service.curl_requests.get to return the
captured Store-API fixture bytes. Asserts the load-bearing contract from
docs/plans/2026-06-25-bh-gcc-source-BUILD-SPEC.md §2.1:

  * minor-unit MATRIX (BHD m3, BHD m2, AED m0, OMR m1) — a hardcoded divisor
    10x/100x-errors a real store, so every fixture's per-response
    currency_minor_unit must be honored.
  * genuine (native BHD → "woo_store_api") vs converted (any other GCC ccy →
    literal "converted_usd" + original_currency).
  * variable-product price=null → price_range.min_amount fallback.
  * stock edge: iworld OOS+purchasable (is_in_stock False is authoritative).
  * html.unescape on the title.
  * strict-title no-fab: a wrong-brand query yields None (never a wrong price).
  * error paths: non-200 / garbage body / empty list / ENABLE_PAGE_SCRAPE off →
    None, never raises.
"""
import asyncio
import copy
import json
import os
from pathlib import Path

import pytest

import app.services.woocommerce_service as woo
from app.services.woocommerce_service import fetch_woocommerce_store_api_price

_FIX = Path(__file__).parent / "fixtures" / "bh_gcc"


def _load(name):
    return json.loads((_FIX / name).read_text(encoding="utf-8"))


class _FakeResp:
    def __init__(self, payload, status_code=200, raise_json=False):
        self._payload = payload
        self.status_code = status_code
        self._raise_json = raise_json
        self.text = "" if raise_json else json.dumps(payload)

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


def _patch_get(monkeypatch, payload, status_code=200, raise_json=False):
    """Patch the module-level curl_requests.get to return a fixed fake response.

    Captures the call so header/param assertions are possible.
    """
    calls = {}

    def fake_get(url, *a, **kw):
        calls["url"] = url
        calls["params"] = kw.get("params")
        calls["headers"] = kw.get("headers")
        return _FakeResp(payload, status_code=status_code, raise_json=raise_json)

    monkeypatch.setattr(woo.curl_requests, "get", fake_get)
    return calls


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------
# minor-unit MATRIX + genuine-vs-converted
# --------------------------------------------------------------------------

def test_genuine_bhd_minor_unit_3(monkeypatch):
    """alibaksh: BHD minor_unit=3 → 10000/1000 = 10.000 BHD, woo_store_api."""
    _patch_get(monkeypatch, _load("woo_alibaksh_bh.json"))
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh 100ml"))
    assert res is not None
    assert res["amount"] == pytest.approx(10.0)
    assert res["currency"] == "BHD"
    assert res["source_method"] == "woo_store_api"
    assert res["estimated"] is False
    assert "original_currency" not in res
    assert res["retailer"] == "alibaksh.com"
    assert res["url"].startswith("https://alibaksh.com/product/")
    assert res["title"] == "Rayhaan Pharaoh 100ml"
    assert 0.7 <= res["confidence"] <= 0.95


def test_genuine_bhd_minor_unit_2(monkeypatch):
    """smellsoreal: BHD minor_unit=2 (NOT 3) → 2400/100 = 24.000 BHD.

    The load-bearing minor-unit trap — a hardcoded /1000 would yield 2.400.
    """
    _patch_get(monkeypatch, _load("woo_smellsoreal_bh_m2.json"))
    res = _run(fetch_woocommerce_store_api_price("bh-en.smellsoreal.com", "Blossom"))
    assert res is not None
    assert res["amount"] == pytest.approx(24.0)
    assert res["currency"] == "BHD"
    assert res["source_method"] == "woo_store_api"


def test_converted_aed_minor_unit_0(monkeypatch):
    """kbeautybliss: AED minor_unit=0 → 2450/1 = 2450 AED → converted_usd.

    minor_unit=0 means NO division at all; a hardcoded /100 would be 24.5.
    """
    # Query carries "Skin"/"Mask" so the is_accessory guard (title contains the
    # "skin" accessory keyword) does not drop this legitimate skincare hit.
    _patch_get(monkeypatch, _load("woo_kbeautybliss_ae_m0.json"))
    res = _run(fetch_woocommerce_store_api_price(
        "kbeautybliss.com", "Shark CryoGlow Under-Eye Skin Mask"))
    assert res is not None
    assert res["currency"] == "BHD"
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "AED"
    # 2450 AED * 0.1024 = 250.88 BHD
    assert res["amount"] == pytest.approx(250.88, abs=0.01)


def test_converted_omr_minor_unit_1(monkeypatch):
    """mobpcom: OMR minor_unit=1 → 999/10 = 99.9 OMR → converted_usd.

    minor_unit=1 (one decimal) — a hardcoded /1000 would yield 0.999.
    """
    # Full SKU title isolates the Gen-2 hit (the shorter Nova-5/3/1 titles also
    # strict-match a bare "Arctis Nova 7" query because numbers_match ignores the
    # single-digit "7"; the adapter then picks the cheapest, which is correct but
    # not the unit we want to assert here).
    _patch_get(monkeypatch, _load("woo_mobpcom_om.json"))
    res = _run(fetch_woocommerce_store_api_price(
        "mobpcom.com", "SS Arctis Nova 7 Wireless Gen 2 Gaming Headset"))
    assert res is not None
    assert res["currency"] == "BHD"
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "OMR"
    # 99.9 OMR * 0.977 = 97.602 BHD
    assert res["amount"] == pytest.approx(97.602, abs=0.01)


# --------------------------------------------------------------------------
# variable-product price-null → price_range.min_amount
# --------------------------------------------------------------------------

def test_variable_product_price_null_uses_price_range_min(monkeypatch):
    """prices.price null on a variable product → fall back to price_range.min_amount
    (also minor-unit). iworld 14-inch MacBook Pro: min 998987 / 1000 = 998.987 BHD."""
    fx = copy.deepcopy(_load("woo_iworld_bh.json"))
    # 14-inch MacBook Pro is index 1; null its price, keep the range.
    target = fx[1]
    assert target["prices"]["price_range"]["min_amount"] == "998987"
    target["prices"]["price"] = None
    _patch_get(monkeypatch, fx)
    res = _run(fetch_woocommerce_store_api_price("iworld.bh", "14-inch MacBook Pro M5"))
    assert res is not None
    assert res["amount"] == pytest.approx(998.987)
    assert res["currency"] == "BHD"
    assert res["source_method"] == "woo_store_api"


def test_price_and_range_both_null_skips_to_none(monkeypatch):
    fx = copy.deepcopy(_load("woo_alibaksh_bh.json"))
    fx[0]["prices"]["price"] = None
    fx[0]["prices"]["price_range"] = None
    _patch_get(monkeypatch, fx)
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh 100ml"))
    assert res is None


# --------------------------------------------------------------------------
# stock edge + html.unescape
# --------------------------------------------------------------------------

def test_oos_purchasable_reports_out_of_stock(monkeypatch):
    """iworld 16-inch MacBook Pro: is_in_stock False, is_purchasable True.
    in_stock must follow is_in_stock (the OOS-backorder edge)."""
    _patch_get(monkeypatch, _load("woo_iworld_bh.json"))
    res = _run(fetch_woocommerce_store_api_price("iworld.bh", "16-inch MacBook Pro M5"))
    assert res is not None
    assert res["in_stock"] is False
    assert res["source_method"] == "woo_store_api"


def test_html_unescape_title(monkeypatch):
    """name carries HTML entities (&#038;) → unescaped in the returned title."""
    _patch_get(monkeypatch, _load("woo_kbeautybliss_ae_m0.json"))
    res = _run(fetch_woocommerce_store_api_price(
        "kbeautybliss.com", "Shark CryoGlow Under-Eye Skin Mask"))
    assert res is not None
    assert "&#038;" not in res["title"]
    assert "&" in res["title"]  # the entity decoded to a literal ampersand


# --------------------------------------------------------------------------
# no-fab: wrong-brand strict-title rejection
# --------------------------------------------------------------------------

def test_wrong_brand_query_returns_none(monkeypatch):
    """A query that strict-title-mismatches every hit → None (never a wrong price)."""
    _patch_get(monkeypatch, _load("woo_alibaksh_bh.json"))
    res = _run(fetch_woocommerce_store_api_price(
        "alibaksh.com", "Sony PlayStation 5 Console"))
    assert res is None


def test_empty_data_returns_none(monkeypatch):
    _patch_get(monkeypatch, [])
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh"))
    assert res is None


# --------------------------------------------------------------------------
# error paths — never raises
# --------------------------------------------------------------------------

def test_non_200_returns_none(monkeypatch):
    _patch_get(monkeypatch, [], status_code=403)
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh"))
    assert res is None


def test_garbage_body_returns_none(monkeypatch):
    _patch_get(monkeypatch, None, status_code=200, raise_json=True)
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh"))
    assert res is None


def test_network_exception_returns_none(monkeypatch):
    def boom(url, *a, **kw):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(woo.curl_requests, "get", boom)
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh"))
    assert res is None


def test_page_scrape_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(woo, "ENABLE_PAGE_SCRAPE", False)
    # get should never be called; if it is, this would still pass via empty —
    # but assert the gate short-circuits before any fetch.
    called = {"n": 0}

    def fake_get(url, *a, **kw):
        called["n"] += 1
        return _FakeResp(_load("woo_alibaksh_bh.json"))

    monkeypatch.setattr(woo.curl_requests, "get", fake_get)
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh 100ml"))
    assert res is None
    assert called["n"] == 0


# --------------------------------------------------------------------------
# WAF default headers + endpoint
# --------------------------------------------------------------------------

def test_waf_headers_and_endpoint(monkeypatch):
    calls = _patch_get(monkeypatch, _load("woo_alibaksh_bh.json"))
    _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh 100ml"))
    assert "wp-json/wc/store" in calls["url"]
    headers = calls["headers"] or {}
    # WAF headers default-on (unlock ownperfumes/purpleorchid/fragrancebh).
    assert headers.get("Referer", "").startswith("https://alibaksh.com")
    assert "Sec-Fetch-Site" in headers
    assert headers.get("Accept") == "application/json"


def test_v1_fallback_on_404(monkeypatch):
    """Unversioned path 404 → retry the /wc/store/v1/ path."""
    seq = []

    def fake_get(url, *a, **kw):
        seq.append(url)
        if "/wc/store/v1/" in url:
            return _FakeResp(_load("woo_alibaksh_bh.json"), status_code=200)
        return _FakeResp([], status_code=404)

    monkeypatch.setattr(woo.curl_requests, "get", fake_get)
    res = _run(fetch_woocommerce_store_api_price("alibaksh.com", "Rayhaan Pharaoh 100ml"))
    assert res is not None
    assert any("/wc/store/v1/" in u for u in seq)
