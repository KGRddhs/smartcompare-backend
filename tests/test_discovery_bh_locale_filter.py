"""Discovery BH-locale + listing filter (Genuine-BH latency+warmer bundle WS3/D8).

Pure-function tests for the render-wave candidate filter in source_router:
  - is_wrong_locale_url — extended with noon-style bare-REGION path segments
    (/egypt-, /saudi-, /cairo/, …) on top of the existing xx-yy GCC locale segs.
  - is_non_pdp_listing_url — drops category/search/listing surfaces (no single
    price) while keeping PDP / Shopify product URLs.

No network, no Serper/Firecrawl — string predicates only."""

import pytest

from app.services.source_router import (
    is_wrong_locale_url,
    is_non_pdp_listing_url,
    rewrite_to_bh_locale,
)


# --------------------------------------------------------------------------- #
# is_wrong_locale_url — wrong-REGION (noon bare-path) drops                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url", [
    "https://www.noon.com/egypt-en/perfume/tom-ford-ombre-leather/p123",
    "https://www.noon.com/saudi-en/beauty/some-fragrance/N456",
    "https://www.noon.com/uae-en/beauty/some-fragrance/N456",
    "https://www.noon.com/oman-en/x/p1",
    "https://www.noon.com/kuwait-en/x/p1",
    "https://www.noon.com/qatar-en/x/p1",
    "https://www.example.com/ksa/product/x",
    "https://www.example.com/cairo/product/x",
])
def test_wrong_region_path_dropped(url):
    assert is_wrong_locale_url(url) is True


@pytest.mark.parametrize("url", [
    # explicit BH region/locale — KEEP
    "https://www.noon.com/bahrain-en/perfume/tom-ford-ombre-leather/p123",
    "https://bahrain.ounass.com/shop-tom-ford-ombre-leather/p-118",
    "https://www.extra.com/en-bh/perfume/tom-ford/product/12345",
    "https://www.alhajisbahrain.com/products/tom-ford-ombre-leather",
    # locale-neutral PDP (no region marker at all) — never drop a maybe-BH page
    "https://www.somebrand.com/product/tom-ford-ombre-leather",
])
def test_bh_or_neutral_kept(url):
    assert is_wrong_locale_url(url) is False


@pytest.mark.parametrize("url", [
    # existing xx-yy wrong-GCC-locale form still drops (no regression)
    "https://www.extra.com/en-sa/perfume/tom-ford/product/12345",
    "https://www.sharafdg.com/ar-ae/product/x",
    "https://www.lulu.com/en-om/product/x",
])
def test_existing_xx_yy_locale_still_dropped(url):
    assert is_wrong_locale_url(url) is True


def test_empty_and_garbage_url_safe():
    assert is_wrong_locale_url("") is False
    assert is_wrong_locale_url(None) is False  # type: ignore[arg-type]
    assert is_non_pdp_listing_url("") is False
    assert is_non_pdp_listing_url(None) is False  # type: ignore[arg-type]


def test_lulu_bh_region_keep_not_rewritten_away():
    """A noon-style /bahrain-en/ URL is already BH — is_wrong_locale_url keeps it
    and rewrite_to_bh_locale is a no-op (None) since it's not a wrong-locale seg."""
    url = "https://www.luluhypermarket.com/en-bh/p/nutella-750g/p123"
    assert is_wrong_locale_url(url) is False
    assert rewrite_to_bh_locale(url) is None


# --------------------------------------------------------------------------- #
# is_non_pdp_listing_url — listing/search/category drops, PDP keeps            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url", [
    "https://www.extra.com/en-bh/c/phones",
    "https://www.lulu.com/en-bh/category/fragrances",
    "https://bahrain.ounass.com/search?q=tom+ford",
    "https://www.example.com/collections/fragrances",   # Shopify collection (NOT a product)
    "https://www.example.com/store?query=tom+ford",     # search via ?query=
])
def test_listing_search_category_dropped(url):
    assert is_non_pdp_listing_url(url) is True


def test_pdp_marker_wins_over_query_marker():
    """A PDP path marker (/p/) wins even when a listing query param co-occurs."""
    assert is_non_pdp_listing_url("https://www.example.com/p/listing?page=2") is False


@pytest.mark.parametrize("url", [
    # tier15 regression fix — /shop/ and /store/ are NOT listing markers: Apple
    # PDPs live at apple.com/shop/<product>, Microsoft Store PDPs at /store/.
    "https://www.apple.com/shop/iphone-15",
    "https://www.example.com/en-bh/shop/perfume",
    # /brand/ and /sale/ removed too (collide inside product slugs) — kept.
    "https://www.example.com/brand/tom-ford",
    "https://www.example.com/sale/perfume",
])
def test_delisted_markers_now_kept(url):
    """These path tokens are too false-positive-prone on official brand sites —
    kept (a maybe-PDP must not be dropped). Genuine category/search surfaces are
    still caught by the high-confidence markers + the query markers."""
    assert is_non_pdp_listing_url(url) is False


@pytest.mark.parametrize("url", [
    "https://www.extra.com/en-bh/perfume/tom-ford/product/12345",
    "https://www.alhajisbahrain.com/products/tom-ford-ombre-leather",   # Shopify PDP
    "https://bahrain.ounass.com/shop-tom-ford/p-118",                   # /p/ PDP
    "https://www.example.com/item/12345",
    "https://www.example.com/dp/B0XYZ",
    # locale-neutral, marker-free → never drop a maybe-PDP
    "https://www.somebrand.com/tom-ford-ombre-leather-edp-100ml",
    "https://www.somebrand.com/",
])
def test_pdp_and_neutral_kept(url):
    assert is_non_pdp_listing_url(url) is False


def test_pdp_marker_wins_over_listing_token():
    """A Shopify product nested under a collection path keeps the PDP signal."""
    url = "https://www.alhajisbahrain.com/collections/frags/products/ombre-leather"
    assert is_non_pdp_listing_url(url) is False


def test_search_query_param_dropped_on_neutral_path():
    url = "https://www.example.com/en-bh/results?search=tom+ford"
    assert is_non_pdp_listing_url(url) is True
