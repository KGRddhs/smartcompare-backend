"""Task C1 — price-pending normalization in build_comparison_response.

The shared chokepoint (sync + streaming) must replace a non-showable price with
the price-pending shape so the FE renders a "pricing in a future update" line
instead of a misleading amount. Showable prices pass through unchanged.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.response_builder import build_comparison_response


def _product(name, category, price):
    return {
        "brand": name.split()[0], "name": name, "full_name": name,
        "category": category,
        "price": price,
        "best_price": (price or {}).get("amount") if isinstance(price, dict) else None,
        "retailer": (price or {}).get("retailer") if isinstance(price, dict) else None,
        "specs": {}, "reviews": None,
        "rating": 4.2, "rating_source": None, "review_count": 5,
        "fact_check": {},
    }


def _scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 60.0}, "product_1": {"overall": 50.0}},
        "tradeoff_pairs": [], "value_badges": [],
        "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {}, "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.", "key_differences": [],
    }


def _build(product_data):
    return build_comparison_response(
        query="A vs B", product_data=product_data, scoring_result=_scoring(),
        comparison=None, region="bahrain", api_calls=0, elapsed_seconds=0.0,
        total_cost=0.0, gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={},
    )


def _overview_prices(response):
    return [p.get("price") for p in response["overview"]["products"]]


def test_estimated_fragrance_becomes_pending():
    pd = [
        _product("Tom Ford Ombré Leather", "fragrances",
                 {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}),
        _product("Creed Aventus", "fragrances",
                 {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}),
    ]
    resp = _build(pd)
    p0, p1 = _overview_prices(resp)
    assert p0["amount"] is None
    assert p0["unavailable"] is True
    assert p0["reason"] == "pending_genuine"
    # Genuine price on the other side is untouched.
    assert p1["amount"] == 80.0
    assert p1.get("unavailable") is not True


def test_sample_decant_flagged_becomes_pending():
    pd = [
        _product("Tom Ford Ombré Leather", "fragrances",
                 {"amount": 60.0, "currency": "BHD", "source_method": "converted_usd",
                  "title": "Tom Ford Ombré Leather decant 5ml", "size": "5ml"}),
        _product("Creed Aventus", "fragrances",
                 {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}),
    ]
    resp = _build(pd)
    p0, _ = _overview_prices(resp)
    assert p0["amount"] is None
    assert p0["unavailable"] is True
    assert p0["reason"] == "pending_genuine"
    # Size carried through for the FE context line.
    assert p0.get("size") == "5ml"


def test_sample_grade_low_fragrance_price_becomes_pending():
    # Ombré 19.93 with no size → below designer full-bottle floor.
    pd = [
        _product("Tom Ford Ombré Leather", "fragrances",
                 {"amount": 19.93, "currency": "BHD", "source_method": "converted_usd",
                  "title": "Tom Ford Ombré Leather"}),
        _product("Creed Aventus", "fragrances",
                 {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}),
    ]
    resp = _build(pd)
    p0, _ = _overview_prices(resp)
    assert p0["amount"] is None and p0["unavailable"] is True


def test_genuine_bhd_passes_through():
    pd = [
        _product("Tom Ford Ombré Leather", "fragrances",
                 {"amount": 79.5, "currency": "BHD", "source_method": "page_scrape_jsonld"}),
        _product("Creed Aventus", "fragrances",
                 {"amount": 244.99, "currency": "BHD", "source_method": "shopify_json"}),
    ]
    resp = _build(pd)
    p0, p1 = _overview_prices(resp)
    assert p0["amount"] == 79.5 and p0.get("unavailable") is not True
    assert p1["amount"] == 244.99 and p1.get("unavailable") is not True


def test_converted_usd_real_price_shown():
    pd = [
        _product("Tom Ford Ombré Leather", "fragrances",
                 {"amount": 85.0, "currency": "BHD", "source_method": "converted_usd",
                  "title": "Tom Ford Ombré Leather 100ml"}),
        _product("Creed Aventus", "fragrances",
                 {"amount": 90.0, "currency": "BHD", "source_method": "local_bhd"}),
    ]
    resp = _build(pd)
    p0, _ = _overview_prices(resp)
    assert p0["amount"] == 85.0 and p0.get("unavailable") is not True


def test_electronics_genuine_unaffected():
    pd = [
        _product("iPhone 15 Pro", "electronics",
                 {"amount": 399.0, "currency": "BHD", "source_method": "local_bhd"}),
        _product("Samsung Galaxy S24", "electronics",
                 {"amount": 349.0, "currency": "BHD", "source_method": "converted_usd"}),
    ]
    resp = _build(pd)
    p0, p1 = _overview_prices(resp)
    assert p0["amount"] == 399.0 and p0.get("unavailable") is not True
    assert p1["amount"] == 349.0 and p1.get("unavailable") is not True


def test_pending_price_kills_cross_price_dimension_delta():
    """When one price is pending (amount=None), the price/value dims must take
    the honest missing-data path — no cross-price 'X less' delta surfaces."""
    pd = [
        _product("Tom Ford Ombré Leather", "fragrances",
                 {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}),
        _product("Creed Aventus", "fragrances",
                 {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}),
    ]
    resp = _build(pd)
    dims = {d["key"]: d for d in resp["scoring_v2"]["dimensions"]}
    # Price dim must be on the limited-data path, not a "BHD x less" delta.
    assert dims["price"]["confidence"] == "low"
    assert "less" not in dims["price"]["delta_text"].lower()
