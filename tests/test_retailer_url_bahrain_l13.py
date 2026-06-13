"""L1.3 (Bundle B S3 'Sources') — Bahrain-correct direct-retailer URLs.

`build_retailer_url` maps a retailer source-name substring to a search-URL
template in `RETAILER_SEARCH_URLS`. Before S3, two BH-relevant keys pointed at
the WRONG GCC country:
  - `sharaf dg` -> uae.sharafdg.com   (registry uses bahrain.sharafdg.com)
  - `extra`     -> extra.com/en-sa    (Saudi, not Bahrain)

L1.3 corrects these to Bahrain and adds direct search-URL patterns for the
verified-live BH retailers (control-calibrated in
`L1_DIAGNOSTIC_bh_scrapeability.md`) so the Tier 1.5 cascade can build a
Bahrain product/search URL directly when Serper `site:` discovery is thin —
fewer Serper calls, more real BH prices.

Decision-F note: every domain asserted here was control-calibrated live
(HTTP 200 + BHD product content) in the same env. No domain is asserted that
was not verified.

All assertions are pure-string (no network). Free-tier safe.
"""

import re

import pytest

from app.services.price_service import build_retailer_url, has_retailer_url


# --- Helper -----------------------------------------------------------------

def _url(source: str, product: str = "iPhone 15") -> str:
    u = build_retailer_url(source, product)
    assert u is not None, f"expected a URL for source={source!r}"
    return u


# --- BH-correction of existing wrong-country mappings -----------------------

class TestBahrainCorrection:
    def test_sharaf_dg_maps_to_bahrain_subdomain(self):
        """'Sharaf DG' must build a bahrain.sharafdg.com URL (registry domain),
        NOT the uae.sharafdg.com it used pre-S3."""
        u = _url("Sharaf DG", "Sony WH-1000XM5")
        assert "bahrain.sharafdg.com" in u
        assert "uae.sharafdg.com" not in u

    def test_extra_maps_to_bahrain_not_saudi(self):
        """'Extra' must NOT resolve to the /en-sa (Saudi) storefront."""
        u = _url("Extra", "Samsung QN90C")
        assert "/en-sa" not in u
        # Bahrain-correct: extra.com without a Saudi locale lock.
        assert "extra.com" in u

    def test_query_is_url_encoded(self):
        """Spaces in the product name are percent-encoded in the built URL."""
        u = _url("Sharaf DG", "Sony WH 1000XM5")
        assert " " not in u
        assert "Sony" in u  # token survives encoding


# --- New verified-live BH retailers -----------------------------------------

class TestNewBahrainRetailers:
    @pytest.mark.parametrize(
        "source,needle",
        [
            ("shopalmoayyed", "shopalmoayyed.com"),
            ("Al Moayyed", "shopalmoayyed.com"),
            ("Bahrain Pharmacy", "bahrainpharmacy.com"),
            ("Asghar Ali", "asgharali.com"),
        ],
    )
    def test_new_bh_retailer_builds_url(self, source, needle):
        u = _url(source, "Panadol")
        assert needle in u

    @pytest.mark.parametrize(
        "source,needle",
        [
            ("shopalmoayyed", "shopalmoayyed.com"),
            ("Bahrain Pharmacy", "bahrainpharmacy.com"),
        ],
    )
    def test_new_bh_retailer_recognized_by_has_retailer_url(self, source, needle):
        assert has_retailer_url(source) is True


# --- Every BH-tier search URL is a real https URL ---------------------------

class TestUrlWellFormedness:
    @pytest.mark.parametrize(
        "source",
        ["Sharaf DG", "Extra", "shopalmoayyed", "Bahrain Pharmacy",
         "Nasser Pharmacy", "Lulu", "Asghar Ali"],
    )
    def test_built_url_is_https_and_has_query(self, source):
        u = build_retailer_url(source, "Vitamin D3")
        assert u is not None, f"{source} should build a URL"
        assert u.startswith("https://"), f"{source} -> {u}"
        # template carried the encoded query token
        assert "Vitamin" in u


# --- Regression: pre-existing mappings unchanged ----------------------------

class TestNoRegressionOnExistingMappings:
    @pytest.mark.parametrize(
        "source,needle",
        [
            ("Amazon", "amazon.com"),
            ("Noon", "noon.com"),
            ("iHerb", "iherb.com"),
            ("Best Buy", "bestbuy.com"),
            ("Nasser Pharmacy", "nasserpharmacy.com"),
        ],
    )
    def test_existing_retailer_still_maps(self, source, needle):
        assert needle in _url(source, "Galaxy S24")

    def test_unknown_returns_none(self):
        assert build_retailer_url("Totally Unknown Store XYZ", "iPhone 15") is None

    def test_empty_returns_none(self):
        assert build_retailer_url("", "iPhone 15") is None
