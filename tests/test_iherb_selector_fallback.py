"""F2.2 — iHerb selector-fallback tightening (Bundle B S1).

When iHerb's search page no longer exposes the proprietary
`data-ga-brand-name`/`data-ga-discount-price` anchor attributes, the legacy
selector returns zero cards and `fetch_iherb_price` returns None — which sends
the caller into the 5–15s Firecrawl/Scrape.do fan-out (stream-hard-cap memo,
2026-06-09). These tests pin a schema.org-microdata fallback
(`meta[itemprop="price"]` inside `div.product-inner`) that parses the price
from the same page WITHOUT extra network calls, so the fan-out is avoided.

All tests are free-tier: `curl_cffi.requests.get` is mocked with recorded HTML
fixtures (captured from bh.iherb.com 2026-06-10, trimmed). No live calls.
"""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import price_service


FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class _FakeResp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _patch_curl(html: str, status_code: int = 200):
    """Patch the curl_cffi.requests.get used inside fetch_iherb_price."""
    fake = _FakeResp(html, status_code)
    # fetch_iherb_price imports `from curl_cffi import requests as curl_requests`
    # inside the function body, so patch the source module attribute.
    import curl_cffi
    return patch.object(curl_cffi.requests, "get", return_value=fake)


# ---------------------------------------------------------------------------
# The fallback path (the F2.2 fix)
# ---------------------------------------------------------------------------

def test_microdata_fallback_parses_price_when_ga_cards_absent():
    """data-ga-* attrs gone, but schema.org price microdata present → price."""
    html = _load("iherb_microdata_only.html")
    with _patch_curl(html):
        result = _run(price_service.fetch_iherb_price(
            "NOW Vitamin D3 5000", "NOW Foods",
            "NOW Foods Vitamin D-3 5000 IU 120 Softgels", "bh", "BHD",
        ))
    assert result is not None, "microdata fallback should recover a price"
    assert result["amount"] == 3.852
    assert result["currency"] == "BHD"
    assert result["retailer"] == "iHerb"
    assert result["estimated"] is False
    assert "/pr/" in result["url"]
    assert result["source_method"] == "converted_usd"


def test_microdata_fallback_brand_matches_correct_product():
    """Fallback must honour brand matching, not just grab the first card."""
    html = _load("iherb_microdata_only.html")
    with _patch_curl(html):
        result = _run(price_service.fetch_iherb_price(
            "Solgar Vitamin D3 5000", "Solgar",
            "Solgar Vitamin D3 Cholecalciferol 5000 IU 120 Softgels", "bh", "BHD",
        ))
    assert result is not None
    # Solgar card price, not NOW (3.852) or California Gold (1.565).
    assert result["amount"] == 5.049
    assert "solgar" in result["url"].lower()


# ---------------------------------------------------------------------------
# Regression guards — existing behaviour unchanged
# ---------------------------------------------------------------------------

def test_ga_cards_still_parse_unchanged():
    """Pages that still expose data-ga-* must parse exactly as before."""
    html = _load("iherb_ga_cards.html")
    with _patch_curl(html):
        result = _run(price_service.fetch_iherb_price(
            "NOW Vitamin D3 5000", "NOW Foods",
            "NOW Foods Vitamin D-3 5000 IU 120 Softgels", "bh", "BHD",
        ))
    assert result is not None
    assert result["amount"] == 3.852
    assert result["retailer"] == "iHerb"


def test_no_products_returns_none():
    """No GA cards AND no microdata → None (caller's tiers take over)."""
    html = _load("iherb_no_products.html")
    with _patch_curl(html):
        result = _run(price_service.fetch_iherb_price(
            "XYZ Fake Vitamin", "XYZ", "XYZ Fake Vitamin", "bh", "BHD",
        ))
    assert result is None


def test_non_200_status_returns_none():
    """A blocked/Cloudflare response (non-200) returns None without parsing."""
    html = _load("iherb_microdata_only.html")
    with _patch_curl(html, status_code=403):
        result = _run(price_service.fetch_iherb_price(
            "NOW Vitamin D3 5000", "NOW Foods",
            "NOW Foods Vitamin D-3 5000 IU", "bh", "BHD",
        ))
    assert result is None


def test_microdata_fallback_no_brand_match_returns_none():
    """Microdata present but no card matches the requested brand → None."""
    html = _load("iherb_microdata_only.html")
    with _patch_curl(html):
        result = _run(price_service.fetch_iherb_price(
            "Thorne Vitamin D", "Thorne", "Thorne Vitamin D 5000", "bh", "BHD",
        ))
    assert result is None
