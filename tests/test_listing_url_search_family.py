"""Source-quality fix — is_non_pdp_listing_url must catch the WordPress/
WooCommerce search-URL family (sharafdg `?s=<q>&post_type=product`), so a
genuine price scraped from a search-results page is NOT cached as a PDP.

Warmer-gate diagnosis: a genuine local_bhd price arrived on a sharafdg `?s=`
search URL, which the substring-based classifier missed → it passed
should_cache_price + select_best → risked being cached as a real PDP. The fix
uses parse_qs EXACT-key matching (a bare `s=` substring would collide with real
PDP params colors=/variants=/flags=/items=).
"""
from __future__ import annotations

import pytest

from app.services.source_router import is_non_pdp_listing_url


@pytest.mark.parametrize("url", [
    "https://bahrain.sharafdg.com/?s=Samsung+Galaxy+S24&post_type=product",
    "https://bahrain.sharafdg.com/?s=Samsung",
    "https://somewpstore.com/?post_type=product&s=iphone",
    "https://shop.example.com/?product_cat=fragrances",
    "https://shop.example.com/?s=perfume&post_type=product",
    "https://www.noon.com/search?q=Lacoste+L1212",
    "https://www.google.com/search?ibp=oshop&q=Samsung+Galaxy+S24",
    "https://store.example.com/catalogsearch/result/",  # Magento, no q=
    "https://shop.example.com/?q=perfume",
])
def test_search_listing_urls_are_dropped(url):
    assert is_non_pdp_listing_url(url) is True, url


@pytest.mark.parametrize("url", [
    # Real PDPs — MUST stay False (no over-catch).
    "https://www.extra.com/en-bh/p/apple-iphone-15-256gb-black/p/100350330",
    "https://bahrain.ounass.com/shop-valentino-beauty-donna-born-in-roma-edp",
    "https://shop.example.com/product/x?colors=black",
    "https://shop.example.com/products/y?variants=123",
    "https://shop.example.com/dp/z?flags=new&items=1",
    "https://shop.example.com/product/w?size=100ml&sku=ABC",
])
def test_real_pdps_are_kept(url):
    assert is_non_pdp_listing_url(url) is False, url
