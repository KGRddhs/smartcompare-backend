"""FIX 4 — park a genuine Tier-1 Serper-shopping price that carries a LISTING url
(Google-Shopping "local": ibp=oshop / prds=localA) instead of short-circuiting,
so the real-PDP direct adapters (woo/shopify/algolia) can serve a SHOWABLE genuine
BHD price for the local Arabic houses.

This locks the two contracts the cascade branch relies on:
  1. the flag `_park_listing_url_tier1_enabled()` (default ON, OFF -> byte-identical)
  2. `_is_listing_url` classifies the Google-Shopping "local" URLs as listing URLs
     (so the park branch fires) while a real merchant PDP is NOT a listing url (so a
     genuine PDP price still short-circuits).
The end-to-end cascade behaviour (park -> woo wins) is exercised by the warm
harness; here we pin the branch predicates so a refactor can't silently break them.
"""
import pytest

from app.services.price_service import _is_listing_url
from app.services.structured_comparison_service import _park_listing_url_tier1_enabled


# --- flag contract --------------------------------------------------------
def test_flag_default_on(monkeypatch):
    monkeypatch.delenv("ENABLE_PARK_LISTING_URL_TIER1", raising=False)
    assert _park_listing_url_tier1_enabled() is True


@pytest.mark.parametrize("val", ["false", "0", "no", "off", ""])
def test_flag_off_values(monkeypatch, val):
    monkeypatch.setenv("ENABLE_PARK_LISTING_URL_TIER1", val)
    assert _park_listing_url_tier1_enabled() is False


@pytest.mark.parametrize("val", ["true", "1", "yes", "on"])
def test_flag_on_values(monkeypatch, val):
    monkeypatch.setenv("ENABLE_PARK_LISTING_URL_TIER1", val)
    assert _park_listing_url_tier1_enabled() is True


# --- the Google-Shopping "local" URLs ARE listing URLs (park branch fires) ---
@pytest.mark.parametrize("url", [
    "https://www.google.com/search?ibp=oshop&q=Lattafa+Khamrah+100ml&prds=localAnnotations",
    "https://www.google.com/search?ibp=oshop&q=Rasasi+Hawas+For+Him+100ml&prds=localA",
    "https://www.google.com/search?ibp=oshop&q=Al+Haramain+Amber+Oud+Gold+Edition+100ml&prds=localA",
])
def test_google_shopping_local_urls_are_listing(url):
    assert _is_listing_url(url) is True


# --- a real merchant PDP is NOT a listing URL (genuine short-circuit preserved) ---
@pytest.mark.parametrize("url", [
    "https://alhajisbahrain.com/products/lattafa-khamrah-edp-100ml",
    "https://alibaksh.com/product/al-haramain-amber-oud-gold-edition-100ml",
    "https://fragrancebh.com/product/rasasi-hawas-for-him-edp-100ml",
])
def test_merchant_pdp_urls_are_not_listing(url):
    assert _is_listing_url(url) is False
