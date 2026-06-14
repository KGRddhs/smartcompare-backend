"""S3 electronics-authority (prod-verify fix, prong b — piece 2) — LAZY
per-retailer PDP backfill.

When the combined `site:` discovery + sitelink-harvest yields ZERO genuine-BH
PDP for a genuine-BH electronics retailer (sharafdg/microless), fire ONE
per-retailer `site:<domain> <query>` Serper query (bounded budget):
  - microless ranks its /product/ PDPs as primary → harvest them.
  - sharafdg returns a WP SEARCH page (not a PDP) → curl it + extract the first
    /product/ link from the HTML → that PDP.
Gated on the zero-genuine-BH-PDP condition so it never fires when the cheap path
(combined + sitelinks) already reached a genuine PDP.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestLazyBackfill:
    async def test_no_backfill_when_harvest_has_bh_pdp(self):
        """Lazy gate: when a genuine-BH PDP is already harvested, backfill fires
        ZERO Serper calls."""
        import app.services.structured_comparison_service as scs
        existing = [(
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black/",
            "bahrain.sharafdg.com", "registry", 3.0,
        )]
        search_mock = AsyncMock(return_value={"organic": []})
        with patch.object(scs, "search_web", search_mock):
            extra = await scs._lazy_bh_pdp_backfill(
                existing, "Apple iPhone 15", "electronics",
            )
        assert search_mock.await_count == 0, "backfill fired a Serper call despite an existing BH PDP"
        assert extra == []

    async def test_microless_pdp_backfilled_when_missing(self):
        """No BH PDP harvested → per-retailer query surfaces microless /product/
        PDPs → harvested."""
        import app.services.structured_comparison_service as scs

        async def fake_search(query, *a, **k):
            if "microless" in query:
                return {"organic": [
                    {"link": "https://bahrain.microless.com/product/apple-macbook-air-m3-13mrxv3/",
                     "title": "Apple MacBook Air M3-13 MRXV3 8GB/256GB"},
                ]}
            return {"organic": []}  # sharafdg etc → nothing

        with patch.object(scs, "search_web", new=AsyncMock(side_effect=fake_search)), \
             patch.object(scs, "curl_fetch_html", new=AsyncMock(return_value=None)):
            extra = await scs._lazy_bh_pdp_backfill(
                [], "Apple MacBook Air M3", "electronics",
            )
        links = [e[0] for e in extra]
        assert any("microless.com/product/apple-macbook-air-m3" in l for l in links), (
            f"microless PDP not backfilled; got {links}"
        )

    async def test_sharafdg_pdp_extracted_from_search_html(self):
        """sharafdg per-retailer query returns a SEARCH page → curl it → extract
        the first /product/ link from the HTML."""
        import app.services.structured_comparison_service as scs

        async def fake_search(query, *a, **k):
            if "sharafdg" in query:
                # Serper returns the WP search page, NOT a PDP.
                return {"organic": [
                    {"link": "https://bahrain.sharafdg.com/?q=iphone+15&post_type=product",
                     "title": "iphone 15 - Sharaf DG Bahrain"},
                ]}
            return {"organic": []}

        SEARCH_HTML = """<html><body>
          <a href="https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black-with-facetime/">iPhone 15 128GB Black</a>
          <a href="https://bahrain.sharafdg.com/product/apple-iphone-15-pro-max-1tb/">iPhone 15 Pro Max</a>
        </body></html>"""

        with patch.object(scs, "search_web", new=AsyncMock(side_effect=fake_search)), \
             patch.object(scs, "curl_fetch_html", new=AsyncMock(return_value=SEARCH_HTML)):
            extra = await scs._lazy_bh_pdp_backfill(
                [], "Apple iPhone 15", "electronics",
            )
        links = [e[0] for e in extra]
        # the base PDP is extracted; the Pro Max is variant-rejected.
        assert any("apple-iphone-15-128gb-black" in l for l in links), (
            f"sharafdg base PDP not extracted from search HTML; got {links}"
        )
        assert not any("pro-max" in l for l in links), (
            f"Pro Max variant leaked from search HTML: {links}"
        )

    async def test_backfill_pdp_passes_variant_filter(self):
        """A backfilled microless PDP that is a wrong variant is rejected."""
        import app.services.structured_comparison_service as scs

        async def fake_search(query, *a, **k):
            if "microless" in query:
                return {"organic": [
                    {"link": "https://bahrain.microless.com/product/apple-iphone-15-pro-max-512gb/",
                     "title": "Apple iPhone 15 Pro Max 512GB"},
                ]}
            return {"organic": []}

        with patch.object(scs, "search_web", new=AsyncMock(side_effect=fake_search)), \
             patch.object(scs, "curl_fetch_html", new=AsyncMock(return_value=None)):
            extra = await scs._lazy_bh_pdp_backfill(
                [], "Apple iPhone 15", "electronics",
            )
        links = [e[0] for e in extra]
        assert not any("pro-max" in l for l in links), (
            f"a Pro Max backfill leaked for a base-15 query: {links}"
        )
