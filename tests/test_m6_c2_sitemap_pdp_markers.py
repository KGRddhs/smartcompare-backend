"""M6 UNIT C2 — generalize the sitemap builder PDP-URL recognition behind
ENABLE_SITEMAP_PDP_MARKERS_V2 (default OFF).

MEASURED (M5, ``scratchpad/m5/measure-sitemap/REPORT.md``): the shipped
``_is_pdp_url`` / ``_PDP_PATH_MARKERS`` recognizes only Shopify ``/products/`` and
the bolo/boutiqaat ``/p/``. So:
  - WooCommerce ``/product/`` (singular — alibaksh, perfumeqatar, ouddubai),
  - Magento ``<slug>.html`` (klinq),
  - the Salla ``/{slug}/p{id}`` shape (reef),
index ZERO real PDPs (5/12 hosts). Worse, reef indexes its ``/p/about`` and
``/p/locations`` CONTENT pages as FALSE PDPs (they match the broad ``/p/``) while
its real ``/{slug}/p{id}`` PDP is dropped. Only 7/12 (58%) have their GT PDP
recognized as a PDP at all.

V2 (``ENABLE_SITEMAP_PDP_MARKERS_V2``, default OFF — it changes what the off-clock
builder indexes) recognizes ``/product/`` + a ``.html`` leaf + the Salla
``/{slug}/p{id}`` shape, and EXCLUDES the ``/p/{static-page}`` content class via a
curated stoplist WITHOUT over-excluding real ``/p/`` PDPs (bolo/boutiqaat).

Real URL shapes are drawn from the M5 GT (``scratchpad/m5/measure-sitemap``) and
``_proof/disc/sitemap_cache/*.json``. No live network — ``_is_pdp_url`` is pure.
"""

import pytest

import app.services.sitemap_discovery_service as sd

_FLAG = "ENABLE_SITEMAP_PDP_MARKERS_V2"

# --- Real GT PDP URLs (one per platform, from the M5 gt_names.json). ----------
SHOPIFY_PDP = "https://yusufbhaifragrances.com/products/dior-sauvage"
WOO_PDP = "https://alibaksh.com/product/roberto-cavalli-uomo-verde-assoluto-m-edp-100ml/"
WOO_PDP_2 = "https://perfumeqatar.com/product/hot-water-for-men-edt-110ml-by-davidoff/"
WOO_PDP_3 = "https://ouddubai.ae/product/bakhoor-samawat/"
MAGENTO_PDP = "https://klinq.com/en/dior-miss-dior-edp.html"
MAGENTO_NEXT_PDP = "https://www.goldenscent.com/en/p/tom-ford-oud-wood-eau-de-parfum-for-men-and-women.html"
SALLA_PDP = "https://reefperfumes.com/en/reef-33/p1243364177"
BOUTIQAAT_PDP = "https://www.boutiqaat.com/en-bh/dior-sauvage-edp-100ml-12345/p/"

# --- reef /p/{static-page} CONTENT pages (must be EXCLUDED). ------------------
REEF_ABOUT = "https://reefperfumes.com/en/p/about"
REEF_LOCATIONS = "https://reefperfumes.com/en/p/locations"
REEF_ABOUT_AR = "https://reefperfumes.com/ar/p/about"


# ===========================================================================
# Flag OFF — byte-identical to the shipped Shopify + /p/ recognition.
# ===========================================================================
class TestPdpMarkersV2Off:
    @pytest.fixture(autouse=True)
    def _flag_off(self, monkeypatch):
        monkeypatch.delenv(_FLAG, raising=False)

    def test_shopify_products_recognized(self):
        assert sd._is_pdp_url(SHOPIFY_PDP) is True

    def test_boutiqaat_trailing_p_recognized(self):
        assert sd._is_pdp_url(BOUTIQAAT_PDP) is True

    def test_woo_product_singular_NOT_recognized(self):
        # the measured gap: /product/ (singular) is invisible to the shipped markers
        assert sd._is_pdp_url(WOO_PDP) is False
        assert sd._is_pdp_url(WOO_PDP_2) is False
        assert sd._is_pdp_url(WOO_PDP_3) is False

    def test_magento_html_NOT_recognized(self):
        assert sd._is_pdp_url(MAGENTO_PDP) is False

    def test_salla_slug_pid_NOT_recognized(self):
        # /p1243364177 has no slash after p, so the /p/ marker does NOT match it
        assert sd._is_pdp_url(SALLA_PDP) is False

    def test_reef_p_about_content_IS_indexed_as_false_pdp(self):
        # the shipped bug the V2 flag repairs: /p/about matches the broad /p/ marker
        assert sd._is_pdp_url(REEF_ABOUT) is True

    def test_collection_still_excluded(self):
        assert sd._is_pdp_url("https://shop.com/collections/all") is False


# ===========================================================================
# Flag ON — the generalized recognizer.
# ===========================================================================
class TestPdpMarkersV2On:
    @pytest.fixture(autouse=True)
    def _flag_on(self, monkeypatch):
        monkeypatch.setenv(_FLAG, "on")

    # --- every platform's GT PDP is now recognized. ---
    def test_shopify_still_recognized(self):
        assert sd._is_pdp_url(SHOPIFY_PDP) is True

    def test_woo_product_singular_recognized(self):
        assert sd._is_pdp_url(WOO_PDP) is True
        assert sd._is_pdp_url(WOO_PDP_2) is True
        assert sd._is_pdp_url(WOO_PDP_3) is True

    def test_magento_html_leaf_recognized(self):
        assert sd._is_pdp_url(MAGENTO_PDP) is True

    def test_magento_next_p_html_recognized(self):
        assert sd._is_pdp_url(MAGENTO_NEXT_PDP) is True

    def test_salla_slug_pid_recognized(self):
        assert sd._is_pdp_url(SALLA_PDP) is True

    def test_boutiqaat_trailing_p_still_recognized(self):
        # a real /p/ PDP (p is the LAST segment) must NOT be over-excluded
        assert sd._is_pdp_url(BOUTIQAAT_PDP) is True

    # --- the /p/{static-page} content class is EXCLUDED. ---
    def test_reef_p_about_excluded(self):
        assert sd._is_pdp_url(REEF_ABOUT) is False

    def test_reef_p_locations_excluded(self):
        assert sd._is_pdp_url(REEF_LOCATIONS) is False

    def test_reef_p_about_arabic_locale_excluded(self):
        assert sd._is_pdp_url(REEF_ABOUT_AR) is False

    # --- the shipped non-PDP exclusions still hold. ---
    def test_collections_still_excluded(self):
        assert sd._is_pdp_url("https://shop.com/collections/all") is False

    def test_category_marker_still_excluded(self):
        # a .html leaf under a known non-PDP /category/ path is still NOT a PDP
        assert sd._is_pdp_url("https://klinq.com/en/category/fragrances.html") is False

    def test_non_html_non_marker_path_not_a_pdp(self):
        # a bare content path with none of the PDP shapes is not indexed
        assert sd._is_pdp_url("https://shop.com/en/about-us") is False


class TestPdpMarkersV2FlagReader:
    def test_reader_default_off(self, monkeypatch):
        monkeypatch.delenv(_FLAG, raising=False)
        assert sd.pdp_markers_v2_enabled() is False

    @pytest.mark.parametrize("val", ["true", "1", "yes", "on", "ON", " True "])
    def test_reader_truthy(self, monkeypatch, val):
        monkeypatch.setenv(_FLAG, val)
        assert sd.pdp_markers_v2_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "off", ""])
    def test_reader_falsy(self, monkeypatch, val):
        monkeypatch.setenv(_FLAG, val)
        assert sd.pdp_markers_v2_enabled() is False

    def test_read_per_call_not_cached(self, monkeypatch):
        monkeypatch.delenv(_FLAG, raising=False)
        assert sd._is_pdp_url(WOO_PDP) is False  # OFF
        monkeypatch.setenv(_FLAG, "on")
        assert sd._is_pdp_url(WOO_PDP) is True  # ON, same process — no import cache
