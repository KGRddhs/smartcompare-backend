"""BH/GCC source-build — the latent _match_shopify_product converted-stamp fix.

Before the fix, a NON-BHD Shopify store's price was _convert_to_bhd'd but still
stamped source_method="shopify_json" (a genuine method) — banking a converted
AED/SAR figure as a genuine BH price for 7 days and inflating the genuine-share
KPI. The fix stamps "converted_usd" when conversion happened. A native-BHD store
must STILL stamp the genuine "shopify_json".
"""
from app.services.price_service import _match_shopify_product, _GENUINE_BH_SOURCE_METHODS


def _catalog(store_currency, price="100.000"):
    return {
        "_store_currency": store_currency,
        "products": [
            {
                "title": "Test Widget",
                "handle": "test-widget",
                "variants": [{"price": price, "available": True, "title": "Default"}],
            }
        ],
    }


def test_native_bhd_store_stamps_genuine_shopify_json():
    price = _match_shopify_product(_catalog("BHD"), "Test Widget", "BHD", "bh-store.com")
    assert price is not None
    assert price["source_method"] == "shopify_json"
    assert price["source_method"] in _GENUINE_BH_SOURCE_METHODS
    assert price["currency"] == "BHD"


def test_converted_store_stamps_converted_usd_not_genuine():
    # AED store, BHD target → conversion happens → must NOT be a genuine stamp.
    price = _match_shopify_product(_catalog("AED"), "Test Widget", "BHD", "ae-store.com")
    assert price is not None, "AED is convertible (in FALLBACK_RATES) → should resolve"
    assert price["source_method"] == "converted_usd"
    assert price["source_method"] not in _GENUINE_BH_SOURCE_METHODS
    assert price["currency"] == "BHD"
    assert price["original_currency"] == "AED"
