"""M21 W4 adapter-rates — CD-wave-diffs-08 residual.

Wave 3 widened ENABLE_EXTENDED_FALLBACK_RATES to the Shopify catalog gate in
price_service, but the 8 direct-adapter convertibility gates still read the
BASE ``FALLBACK_RATES`` table (or, for salla, a hand-copied 9-currency mirror
set), so with the flag ON a TRY/PLN/CAD-priced store is STILL dropped by the
adapters — a canary of the flag under-measures on adapter-covered hosts.

Fix under test: one shared ``exchange_rate_service.is_convertible(currency)``
(membership in ``effective_fallback_rates()``, EXACT — no case folding, so each
adapter's flag-OFF behaviour is byte-identical to its old
``x in FALLBACK_RATES`` gate) consumed by all 8 adapter gates.

Pins, per adapter (parametrized):
  - flag OFF (unset): a TRY candidate is dropped — byte-identical to base.
  - flag OFF: a USD candidate still converts (driver control — proves each
    driver reaches PAST the gate, so a flag-ON None is the gate, not the rig).
  - flag ON: a TRY candidate converts at the FALLBACK_RATES_EXTENDED rate.
    RED at base for 7 of 8 adapters (rest_json's gate only fires when
    _convert_to_bhd — which already reads the effective table — returned the
    amount unchanged, so rest_json is behaviour-neutral and already green;
    it is included so the consolidation onto is_convertible() stays pinned).

DELIBERATE flag-OFF deviation (spec-directed): salla's local ``_CONVERTIBLE``
mirror was a STALE copy of FALLBACK_RATES (9 currencies; the base table gained
SGD/JPY/CNY/INR in Bug 4 and the mirror never followed). Replacing the mirror
with the shared helper means a flag-OFF SGD salla hit now converts like every
sibling adapter instead of being dropped — pinned explicitly below.

Offline — no network (curl_cffi patched), no paid APIs.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import MagicMock, patch

_FX = Path(__file__).parent / "fixtures" / "bh_gcc"

FLAG = "ENABLE_EXTENDED_FALLBACK_RATES"
TRY_RATE = 0.0094   # FALLBACK_RATES_EXTENDED["TRY"]
USD_RATE = 0.376    # FALLBACK_RATES["USD"]
SGD_RATE = 0.282    # FALLBACK_RATES["SGD"] — absent from salla's stale mirror

# A product name outside every plausibility-guard family (not high-value, not
# fragrance/haircare/supplement, no accessory/sample/decant token) so the only
# thing separating None from a price dict at the driver level is the gate.
PRODUCT = "Nivea Soft Cream 200ml"
AMOUNT = 400.0  # TRY -> 3.76 BHD, USD -> 150.4 BHD, SGD -> 112.8 BHD


def _load_fixture(name):
    return json.loads((_FX / f"{name}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Shared helper contract
# ---------------------------------------------------------------------------

class TestIsConvertibleHelper:
    def _helper(self):
        from app.services import exchange_rate_service as ers
        assert hasattr(ers, "is_convertible"), (
            "exchange_rate_service.is_convertible() is missing — the 8 adapter "
            "gates need one shared effective-table membership helper"
        )
        return ers.is_convertible

    def test_flag_off_is_exact_base_membership(self, monkeypatch):
        monkeypatch.delenv(FLAG, raising=False)
        is_convertible = self._helper()
        from app.services.exchange_rate_service import FALLBACK_RATES
        for code in FALLBACK_RATES:
            assert is_convertible(code), code
        # extended currencies NOT convertible while the flag is unset
        for code in ("TRY", "PLN", "CAD", "JOD"):
            assert not is_convertible(code), code
        # exact membership — no case folding, no None/empty admission (mirrors
        # the byte-identical `x in FALLBACK_RATES` semantics of every old gate)
        assert not is_convertible(None)
        assert not is_convertible("")
        assert not is_convertible("usd")

    def test_flag_on_admits_extended_tail(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        is_convertible = self._helper()
        from app.services.exchange_rate_service import (
            FALLBACK_RATES, FALLBACK_RATES_EXTENDED,
        )
        for code in FALLBACK_RATES:
            assert is_convertible(code), code
        for code in FALLBACK_RATES_EXTENDED:
            assert is_convertible(code), code
        assert not is_convertible("XXX")
        assert not is_convertible("try")  # still exact — no folding

    def test_effective_equals_base_when_unset(self, monkeypatch):
        monkeypatch.delenv(FLAG, raising=False)
        from app.services.exchange_rate_service import (
            FALLBACK_RATES, effective_fallback_rates,
        )
        assert effective_fallback_rates() == FALLBACK_RATES


# ---------------------------------------------------------------------------
# Per-adapter drivers — each returns the adapter's price dict (or None) for a
# candidate priced ``amount`` in ``currency``, with everything else valid.
# ---------------------------------------------------------------------------

def _fake_resp(status=200, text="", json_obj=None):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text if text else json.dumps(json_obj)
    resp.json = MagicMock(return_value=json_obj)
    return resp


async def _drive_occ(currency, amount, monkeypatch):
    from app.services import occ_service as occ
    prod = {
        "name": PRODUCT,
        "price": {"value": amount, "currencyIso": currency},
        "url": "/p/nivea-soft-200ml",
    }
    return occ._build_price(
        prod, "virginmegastore.bh", "https://www.virginmegastore.bh", PRODUCT)


async def _drive_magento(currency, amount, monkeypatch):
    from app.services import magento_graphql_service as mg
    node = {"currency": currency, "value": amount, "name": PRODUCT, "in_stock": True}
    return mg._finalize_magento_price(
        node, "example-store.com", "https://example-store.com/p/nivea", PRODUCT, "BHD")


async def _drive_rest_json(currency, amount, monkeypatch):
    from app.services import rest_json_service as rj
    return rj._stamp_genuine_or_converted(amount, currency, "BHD")


async def _drive_woocommerce(currency, amount, monkeypatch):
    from app.services import woocommerce_service as woo
    products = [{
        "name": PRODUCT,
        "prices": {
            "price": str(int(amount * 100)),
            "currency_code": currency,
            "currency_minor_unit": 2,
        },
        "permalink": "https://example-store.com/product/nivea-soft-200ml",
        "is_in_stock": True,
    }]
    return woo._match_woo_product(products, PRODUCT, "BHD")


async def _drive_salla(currency, amount, monkeypatch):
    import app.services.salla_service as salla
    import curl_cffi.requests as curl_requests
    storefront = '<html><script>window.ctx={"store":{"name":"t","id":424242}};</script></html>'
    api_payload = {"data": [{
        "name": PRODUCT,
        "price": amount,
        "currency": currency,
        "url": "https://teststore.example/p/1",
        "is_out_of_stock": False,
        "brand": None, "sku": None, "gtin": None,
    }]}

    def fake_get(url, *args, **kwargs):
        if "api.salla.dev" in url:
            return _fake_resp(json_obj=api_payload)
        return _fake_resp(text=storefront)

    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)
    monkeypatch.setattr(salla, "ENABLE_PAGE_SCRAPE", True, raising=False)
    salla._STORE_ID_CACHE.clear()
    return await salla.fetch_salla_api_price("teststore.example", PRODUCT)


async def _drive_unbxd(currency, amount, monkeypatch):
    import app.services.unbxd_service as un
    store = dict(un.UNBXD_STORES["extra.com"])
    store["currency"] = currency
    store["genuine"] = False
    monkeypatch.setitem(un.UNBXD_STORES, "extra.com", store)
    payload = _load_fixture("unbxd_extra_bh")
    # Re-price the matched fixture hit so plausibility guards can never mask
    # the gate (iPhone is a HIGH-VALUE query: converted amount must be >= 50).
    payload["response"]["products"][0]["sellingPrice"] = amount
    with patch("app.services.unbxd_service.is_circuit_closed", return_value=True), \
         patch("curl_cffi.requests.get", MagicMock(return_value=_fake_resp(json_obj=payload))):
        return await un.fetch_unbxd_price(
            "extra.com", "Apple iPhone 17 Pro Max 256GB", "electronics")


async def _drive_algolia(currency, amount, monkeypatch):
    import app.services.algolia_service as alg
    domain = "bahrain.sharafdg.com"
    store = dict(alg.ALGOLIA_EXPLICIT_STORES[domain])
    store["currency"] = currency
    store["genuine"] = False
    monkeypatch.setitem(alg.ALGOLIA_EXPLICIT_STORES, domain, store)
    payload = _load_fixture("algolia_sharafdg_bh")
    payload["hits"][0]["price"] = amount  # flat-float shape; see driver note above
    with patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True), \
         patch("app.services.algolia_service.is_circuit_closed", return_value=True), \
         patch("curl_cffi.requests.post", MagicMock(return_value=_fake_resp(json_obj=payload))):
        return await alg.fetch_algolia_price(
            domain, "Apple iPhone 15 128GB", "electronics")


async def _drive_shopify_ucp(currency, amount, monkeypatch):
    import app.services.shopify_pdp_service as sp
    from app.services import price_service as ps
    monkeypatch.setenv("ENABLE_UCP_JSON_PRICE", "true")
    # Variant binding is orthogonal to the currency gate — force priced[0].
    monkeypatch.setattr(ps, "variant_min_guard_enabled", lambda: False)
    product = {
        "title": PRODUCT,
        "vendor": "",
        "domain": "shop.example",
        "product_url": "https://shop.example/products/nivea-soft-200ml",
        "priced_variants": [{
            "variant": {"id": 1, "title": "Default Title"},
            "amount": amount,
            "currency": currency,
            "currency_source": "merchant",
            "list_price": None,
        }],
    }

    async def fake_fetch(pdp_url, **kwargs):
        return product

    monkeypatch.setattr(sp, "fetch_ucp_json_product", fake_fetch)
    # Empty product_name deliberately skips the identity-match block — this
    # drives ONLY the currency gate + conversion tail.
    return await sp.fetch_ucp_json_price(
        "https://shop.example/products/nivea-soft-200ml", "")


# unbxd/algolia ride real captured fixtures whose matched hits are iPhones
# (HIGH-VALUE queries, 50-BHD floor) — so their amounts are raised to keep the
# converted figure above every plausibility floor in BOTH currencies.
_DRIVERS = {
    "occ": (_drive_occ, AMOUNT),
    "magento": (_drive_magento, AMOUNT),
    "rest_json": (_drive_rest_json, AMOUNT),
    "woocommerce": (_drive_woocommerce, AMOUNT),
    "salla": (_drive_salla, AMOUNT),
    "unbxd": (_drive_unbxd, 40000.0),
    "algolia": (_drive_algolia, 40000.0),
    "shopify_ucp": (_drive_shopify_ucp, AMOUNT),
}

ADAPTERS = sorted(_DRIVERS)


# ---------------------------------------------------------------------------
# Flag OFF — byte-identical to base: TRY dropped, USD converts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", ADAPTERS)
async def test_flag_off_try_candidate_dropped(adapter, monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    driver, amount = _DRIVERS[adapter]
    out = await driver("TRY", amount, monkeypatch)
    assert out is None, (
        f"{adapter}: flag OFF must keep base behaviour — an un-rated TRY "
        f"candidate is dropped, never shipped (got {out!r})"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", ADAPTERS)
async def test_flag_off_usd_candidate_converts(adapter, monkeypatch):
    """Driver control: proves each rig reaches PAST the gate at base, so the
    TRY assertions above/below are about the gate, not a broken fixture."""
    monkeypatch.delenv(FLAG, raising=False)
    driver, amount = _DRIVERS[adapter]
    out = await driver("USD", amount, monkeypatch)
    assert out is not None, f"{adapter}: USD control candidate must convert"
    assert out.get("original_currency") == "USD"
    assert out["currency"] == "BHD"
    assert out["source_method"] == "converted_usd"
    expected = amount * USD_RATE
    assert out["amount"] == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# Flag ON — the defect: adapters must admit the extended tail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", ADAPTERS)
async def test_flag_on_try_candidate_converts(adapter, monkeypatch):
    """CD-wave-diffs-08 residual — RED at base for every adapter but rest_json:
    the gate reads base FALLBACK_RATES (or salla's stale mirror), so the TRY
    candidate is dropped even though _convert_to_bhd would convert it."""
    monkeypatch.setenv(FLAG, "true")
    driver, amount = _DRIVERS[adapter]
    out = await driver("TRY", amount, monkeypatch)
    assert out is not None, (
        f"{adapter}: with {FLAG}=true a TRY candidate must convert — a None "
        f"here is the base-table gate swallowing the flag (the canary "
        f"under-measure this unit exists to fix)"
    )
    assert out.get("original_currency") == "TRY"
    assert out["currency"] == "BHD"
    assert out["source_method"] == "converted_usd"
    expected = amount * TRY_RATE
    assert out["amount"] == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# salla — the stale hand-copied mirror is REPLACED, not duplicated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_salla_stale_mirror_replaced_sgd_converts_flag_off(monkeypatch):
    """DELIBERATE flag-OFF deviation (spec-directed, documented in the module
    docstring above): salla's _CONVERTIBLE hand-copy predated Bug 4's addition
    of SGD/JPY/CNY/INR to FALLBACK_RATES, so a flag-OFF SGD hit was dropped on
    salla alone. Routing salla through the shared helper aligns it with every
    sibling adapter's base table."""
    monkeypatch.delenv(FLAG, raising=False)
    out = await _drive_salla("SGD", AMOUNT, monkeypatch)
    assert out is not None, (
        "salla: SGD is in base FALLBACK_RATES — the stale 9-currency mirror "
        "set must be gone (replaced by is_convertible), not duplicated"
    )
    assert out.get("original_currency") == "SGD"
    assert out["amount"] == pytest.approx(AMOUNT * SGD_RATE, rel=1e-3)


def test_salla_mirror_set_deleted():
    """The hand-copied set itself must be deleted so it cannot drift again."""
    import app.services.salla_service as salla
    assert not hasattr(salla, "_CONVERTIBLE"), (
        "salla_service._CONVERTIBLE still exists — the mirror-set idiom must "
        "be replaced by exchange_rate_service.is_convertible, not kept beside it"
    )
