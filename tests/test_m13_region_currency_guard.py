"""M13-11 — response-chokepoint region-currency guard (ENABLE_REGION_CURRENCY_GUARD).

Eight adapters hard-code BHD and ignore their currency parameter, and nothing in
the fan-out / is_price_showable / response_builder compares a price's currency to
the request region. So a region=saudi_arabia compare could serve a BHD 25.0 (10x
wrong when read as SAR) and render 'BHD 25.0' to a Saudi user. The buildable fix
is ONE guard at the response chokepoint: pend any price whose currency != the
region currency, behind a default-OFF flag.

Runs against ``response_builder.build_comparison_response`` (no network).
"""
from app.services.response_builder import build_comparison_response


def _product(name, amount, cur):
    return {
        "name": name, "full_name": name, "category": "electronics",
        "price": {
            "amount": amount, "currency": cur, "source_method": "local_bhd",
            "retailer": "noon", "url": "https://noon.com/p", "title": name,
            "in_stock": True,
        },
    }


def _prices(resp):
    return [
        ((p.get("price") or {}).get("amount"),
         (p.get("price") or {}).get("currency"),
         (p.get("price") or {}).get("unavailable"))
        for p in resp["products"]
    ]


def test_m13_11_flag_off_leaves_bhd_price_for_sar_region(monkeypatch):
    """Flag OFF: a BHD price on a saudi_arabia request is unchanged (byte-identical)."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "false")
    pd = [_product("Alpha Phone", 25.0, "BHD"), _product("Beta Phone", 250.0, "SAR")]
    resp = build_comparison_response(product_data=pd, region="saudi_arabia")
    assert _prices(resp) == [(25.0, "BHD", None), (250.0, "SAR", None)]


def test_m13_11_flag_on_pends_mismatched_currency(monkeypatch):
    """Flag ON: the BHD price on a saudi_arabia (SAR) request pends; the matching
    SAR price passes through."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha Phone", 25.0, "BHD"), _product("Beta Phone", 250.0, "SAR")]
    resp = build_comparison_response(product_data=pd, region="saudi_arabia")
    prices = _prices(resp)
    # The BHD price pended: no amount, region currency, unavailable.
    assert prices[0] == (None, "SAR", True), prices
    # The SAR price (matches the region) is untouched.
    assert prices[1] == (250.0, "SAR", None), prices


def test_m13_11_flag_on_bahrain_bhd_price_unaffected(monkeypatch):
    """Flag ON but region=bahrain: a BHD price matches the region currency and is
    NOT pended (no over-pend on the home market)."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha Phone", 25.0, "BHD")]
    resp = build_comparison_response(product_data=pd, region="bahrain")
    assert _prices(resp) == [(25.0, "BHD", None)]
