"""I5.5 (Bundle B S2) — category-aware authorized/gcc discovery.

The prod price-escalation discovery (`_get_price`, ssc) hard-coded the
authorized + gcc discovery queries to FASHION/luxury retailer strings:
  retailer_query = "<product> farfetch OR ssense OR net-a-porter"
  gcc_query      = "<product> ounass OR bloomingdales dubai OR namshi"
— nonsense for an air-conditioner. An AC should look at noon / amazon.ae /
sharafdg (gcc electronics), not Ounass.

I5.5 builds both queries from the registry per category via
`build_site_discovery_query(..., tier="gcc")` / `tier="global"`. Fashion still
gets ounass/bloomingdales/tryano (they ARE the fashion gcc tier); electronics
gets noon/amazon.ae/sharafdg. Counterfeit safety is unchanged (every candidate
is still gated post-fetch by score_source >= 1.5).

This test pins the prod call-site: the authorized/gcc discovery queries are
built per-category from the registry, and the old hard-coded fashion strings
are gone from the non-fashion path.
"""

import inspect
import re

import pytest

from app.services.source_router import build_site_discovery_query
from app.services.structured_comparison_service import StructuredComparisonService


_GET_PRICE_SRC = inspect.getsource(StructuredComparisonService._get_price)


class TestHardcodedFashionStringsRemoved:
    def test_no_hardcoded_farfetch_ssense_netaporter(self):
        assert "farfetch OR ssense OR net-a-porter" not in _GET_PRICE_SRC, (
            "I5.5: the authorized discovery query must be registry-built "
            "per-category, not a hard-coded fashion string"
        )

    def test_no_hardcoded_ounass_bloomingdales_namshi(self):
        assert "ounass OR bloomingdales dubai OR namshi" not in _GET_PRICE_SRC, (
            "I5.5: the gcc discovery query must be registry-built per-category"
        )


class TestProdBuildsGccAndAuthorizedFromRegistry:
    def test_gcc_query_built_via_build_site_discovery_query_gcc_tier(self):
        # There must be a build_site_discovery_query(..., tier="gcc", ...) call.
        assert re.search(
            r'build_site_discovery_query\([^)]*tier="gcc"', _GET_PRICE_SRC, re.S
        ), "I5.5: gcc discovery must use build_site_discovery_query(tier='gcc')"

    def test_authorized_query_built_via_build_site_discovery_query_global_tier(self):
        assert re.search(
            r'build_site_discovery_query\([^)]*tier="global"', _GET_PRICE_SRC, re.S
        ), "I5.5: authorized discovery must use build_site_discovery_query(tier='global')"


class TestCategoryCorrectness:
    """The registry queries themselves must route correctly per category —
    proves the behavior the prod change delivers."""

    def test_electronics_gcc_is_not_fashion(self):
        q = build_site_discovery_query("Carrier 1.5T AC", "electronics", tier="gcc", limit=8)
        assert "site:noon.com" in q and "site:amazon.ae" in q and "site:sharafdg.com" in q
        # No fashion-luxury retailers for an AC.
        assert "ounass" not in q and "bloomingdales" not in q and "farfetch" not in q

    def test_fashion_gcc_still_gets_luxury_retailers(self):
        # Fashion legitimately keeps its luxury gcc retailers (they ARE the
        # fashion gcc tier) — the change is category-aware, not anti-fashion.
        q = build_site_discovery_query("Gucci bag", "fashion", tier="gcc", limit=8)
        assert "site:ounass.com" in q
        assert "site:bloomingdales.ae" in q

    def test_electronics_global_is_brand_officials(self):
        q = build_site_discovery_query("iPhone 15", "electronics", tier="global", limit=8)
        # global tier = brand officials + marketplaces, not fashion boutiques.
        assert "site:apple.com" in q or "site:samsung.com" in q
        assert "farfetch" not in q and "net-a-porter" not in q
