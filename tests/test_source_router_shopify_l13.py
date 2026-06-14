"""L1.3 (Bundle B S3 'Sources') — Shopify-platform registry tagging.

The Shopify direct-discovery cascade lever needs to know WHICH Bahrain registry
domains are Shopify stores (so it can hit their `/products.json` directly,
free, before the Serper site: discovery). This adds:
  - `Source.is_shopify: bool = False` (default → every legacy row unchanged)
  - shopalmoayyed.com + bh.asgharali.com tagged is_shopify=True (the two
    control-calibrated Shopify BH stores; L1_DIAGNOSTIC_bh_scrapeability.md)
  - `get_shopify_sources_for_category(category)` → bahrain-tier Shopify sources
    matching the category, in registry order.

Free-tier safe — pure registry inspection, no network.
"""

import pytest

from app.services.source_router import (
    SOURCE_REGISTRY,
    Source,
    get_shopify_sources_for_category,
    get_sources_for_category,
)


class TestIsShopifyFlag:
    def test_source_has_is_shopify_field_default_false(self):
        """A bare Source defaults is_shopify=False (legacy rows unchanged)."""
        s = Source("example.com", "bahrain", (), 3.0)
        assert s.is_shopify is False

    def test_known_shopify_domains_tagged(self):
        by_domain = {s.domain: s for s in SOURCE_REGISTRY}
        assert by_domain["shopalmoayyed.com"].is_shopify is True
        assert by_domain["bh.asgharali.com"].is_shopify is True

    def test_non_shopify_domains_not_tagged(self):
        by_domain = {s.domain: s for s in SOURCE_REGISTRY}
        # SPA incumbents + pharmacies are NOT Shopify (must not be probed via
        # /products.json — they'd 404 / waste a fetch). lulu retargeted to the
        # gcc/en-bh storefront (SAP Hybris, not Shopify).
        assert by_domain["bahrain.sharafdg.com"].is_shopify is False
        assert by_domain["gcc.luluhypermarket.com"].is_shopify is False
        assert by_domain["nasserpharmacy.com"].is_shopify is False

    def test_every_shopify_row_is_bahrain_tier(self):
        """Shopify direct-discovery is a Bahrain-price lever — every tagged row
        must be a bahrain-tier source (the cascade only iterates bahrain-tier
        Shopify sources)."""
        for s in SOURCE_REGISTRY:
            if s.is_shopify:
                assert s.tier == "bahrain", f"{s.domain} is_shopify but tier={s.tier}"


class TestGetShopifySourcesForCategory:
    def test_electronics_includes_almoayyed(self):
        domains = [s.domain for s in get_shopify_sources_for_category("electronics")]
        assert "shopalmoayyed.com" in domains

    def test_fragrances_includes_asgharali(self):
        domains = [s.domain for s in get_shopify_sources_for_category("fragrances")]
        assert "bh.asgharali.com" in domains

    def test_returns_only_shopify_sources(self):
        for cat in ("electronics", "fragrances", "grocery", "skincare"):
            for s in get_shopify_sources_for_category(cat):
                assert s.is_shopify is True
                assert s.tier == "bahrain"

    def test_category_filter_respected(self):
        """almoayyed is electronics-only — it must NOT surface for fragrances."""
        frag = [s.domain for s in get_shopify_sources_for_category("fragrances")]
        assert "shopalmoayyed.com" not in frag

    def test_unknown_category_returns_list(self):
        # Never raises; returns a (possibly empty) list.
        assert isinstance(get_shopify_sources_for_category("nonsense"), list)

    def test_subset_of_category_sources(self):
        """Shopify sources for a category are a subset of all price sources for
        it (sanity: the helper is a filtered view of the registry)."""
        all_elec = {s.domain for s in get_sources_for_category("electronics", usage="price")}
        shop_elec = {s.domain for s in get_shopify_sources_for_category("electronics")}
        assert shop_elec.issubset(all_elec)
