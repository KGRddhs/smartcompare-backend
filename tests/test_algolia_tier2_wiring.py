"""S3 #21/#1 — Tier-2 Algolia cascade wiring (L1 owns registry + call-site).

Verifies:
  - get_algolia_sources_for_category returns the 6thStreet row for its
    categories (fashion/fragrances/makeup/skincare/haircare), empty otherwise.
  - the _get_price Tier-2 Algolia call-site short-circuits on a genuine BHD hit
    (local_bhd), positioned AFTER Shopify-json and BEFORE Serper discovery.
  - a None Algolia result falls through (cascade continues).
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch


class TestAlgoliaRegistryHelper:
    def test_6thstreet_for_fashion_only(self):
        # L2 verify-or-omit (2026-06-14): the harvested 6thStreet index is
        # FASHION/FOOTWEAR ONLY — beauty queries return junk (lipstick->0,
        # "Dior Sauvage"->backpacks). So 6thStreet serves ONLY fashion.
        from app.services.source_router import get_algolia_sources_for_category
        domains = [s.domain for s in get_algolia_sources_for_category("fashion")]
        assert "en-bh.6thstreet.com" in domains, "6thStreet missing for fashion"

    def test_6thstreet_NOT_for_beauty_or_electronics(self):
        from app.services.source_router import get_algolia_sources_for_category
        # beauty + fragrances are NOT 6thStreet's (the Algolia harvest yields no
        # genuine beauty); they ride render-tier + Shopify-fragrance rows.
        for cat in ("fragrances", "makeup", "skincare", "haircare", "electronics", "grocery"):
            domains = [s.domain for s in get_algolia_sources_for_category(cat)]
            assert "en-bh.6thstreet.com" not in domains, (
                f"6thStreet wrongly serves {cat} — it's fashion-only"
            )

    def test_6thstreet_is_bahrain_tier_algolia(self):
        from app.services.source_router import registry_tier, SOURCE_REGISTRY
        assert registry_tier("en-bh.6thstreet.com") == "bahrain"
        row = next(s for s in SOURCE_REGISTRY if s.domain == "en-bh.6thstreet.com")
        assert row.is_algolia is True
        assert row.is_shopify is False


@pytest.mark.asyncio
class TestAlgoliaTier2CallSite:
    async def _make_svc_at_escalation(self):
        """A service stubbed so _get_price reaches the Tier-1.5 escalation with
        a low-confidence Tier-1 (forces escalation) for a fragrance query."""
        from app.services.structured_comparison_service import get_comparison_service
        return get_comparison_service()

    async def test_genuine_algolia_hit_short_circuits(self, monkeypatch):
        import app.services.structured_comparison_service as scs

        svc = scs.get_comparison_service()

        # Force escalation + no Tier-1 shopping price + no Shopify hit so we
        # reach the Algolia call-site cleanly.
        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        # Shopify direct returns nothing.
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        # Serper shopping (Tier 1) returns no price.
        async def no_shopping(*a, **k):
            return None
        monkeypatch.setattr(svc, "_get_serper_shopping_price", no_shopping, raising=False)

        # Algolia returns a genuine BHD hit.
        async def fake_algolia(domain, product_name, category="other"):
            return {
                "amount": 32.0, "currency": "BHD", "retailer": "en-bh.6thstreet.com",
                "url": "https://en-bh.6thstreet.com/product/x", "in_stock": True,
                "estimated": False, "source_method": "local_bhd", "confidence": 0.9,
            }
        monkeypatch.setattr(
            "app.services.algolia_service.fetch_algolia_price", fake_algolia
        )
        # Discovery must NOT be reached — make it loud if it is.
        async def boom_search(*a, **k):
            raise AssertionError("discovery reached — Algolia did not short-circuit")
        monkeypatch.setattr(scs, "search_web", boom_search)

        # FASHION query — 6thStreet is fashion-only (L2 verify-or-omit).
        price = await svc._get_price(
            brand="Nike", name="Air Max SC", variant=None, region="bahrain",
            search_query="Nike Air Max SC", nocache=True, category="fashion",
        )
        assert price is not None
        assert price["source_method"] == "local_bhd"
        assert abs(price["amount"] - 32.0) < 0.01
        assert price["retailer"] == "en-bh.6thstreet.com"

    async def test_algolia_miss_falls_through(self, monkeypatch):
        """No Algolia hit → cascade continues to discovery (not short-circuited)."""
        import app.services.structured_comparison_service as scs

        svc = scs.get_comparison_service()
        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])

        async def fake_algolia_none(domain, product_name, category="other"):
            return None
        monkeypatch.setattr(
            "app.services.algolia_service.fetch_algolia_price", fake_algolia_none
        )
        reached = {"discovery": False}
        async def marker_search(*a, **k):
            reached["discovery"] = True
            return {"organic": [], "shopping": []}
        monkeypatch.setattr(scs, "search_web", marker_search)

        # FASHION so the Algolia block RUNS (6thStreet is fashion-only) and its
        # None result falls through to discovery (not skipped-because-no-source).
        await svc._get_price(
            brand="Nike", name="Air Max SC", variant=None, region="bahrain",
            search_query="Nike Air Max SC", nocache=True, category="fashion",
        )
        # Algolia returned None → discovery WAS reached (fell through).
        assert reached["discovery"] is True
