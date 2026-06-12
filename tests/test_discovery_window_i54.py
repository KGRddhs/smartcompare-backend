"""I5.4 (Bundle B S2) — discovery window widening.

After I5.3 made all the early-window bahrain-electronics domains live, the
electronics bahrain registry order is:
  [0] luluhypermarket.com [1] bahrain.sharafdg.com [2] extra.com
  [3] behbehani.com [4] jumboelectronics.com [5] shopalmoayyed.com
The prod price-escalation discovery (`_get_price`, ssc) built the `site:`
query with `limit=4`, slicing off index 4-5 — so shopalmoayyed.com
(appliances/AC, the F1.5-verified Shopify JSON-LD source) was NEVER queried.

I5.4 bumps the PROD call-site limit 4→8 (same single Serper call, just a
longer OR-chain) so every live bahrain-electronics source — including
shopalmoayyed.com and the fragrance source bh.asgharali.com — is reachable.
The `build_site_discovery_query` default stays 4 (no other caller changes).
"""

import re

import pytest

from app.services.source_router import (
    build_site_discovery_query,
    get_sources_for_category,
)


class TestWindowReachesShopalmoayyed:
    def test_limit_8_electronics_includes_shopalmoayyed(self):
        q = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=8
        )
        assert "site:shopalmoayyed.com" in q, (
            "limit=8 must reach shopalmoayyed.com (index 5) — the F1.5 "
            "appliance/AC JSON-LD source the electronics 0/14 fix needs"
        )

    def test_limit_4_did_NOT_reach_shopalmoayyed(self):
        # Documents the bug I5.4 fixes: the old window stopped at index 3.
        q4 = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=4
        )
        assert "site:shopalmoayyed.com" not in q4

    def test_limit_8_still_single_query_or_chain(self):
        q = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=8
        )
        # One query string, OR-joined site: operators, no junk.
        assert q.startswith("Carrier 1.5 ton AC site:")
        assert " OR " in q
        assert not q.endswith(" OR ")
        assert "site:OR" not in q
        # 6 live bahrain-electronics sources today → 6 site: ops (<=8).
        n = q.count("site:")
        assert 4 < n <= 8

    def test_limit_8_fragrances_includes_bh_asgharali(self):
        # bh.asgharali.com is a bahrain fragrance source that also benefits
        # from the wider window.
        q = build_site_discovery_query(
            "Tom Ford Oud Wood", "fragrances", tier="bahrain", limit=8
        )
        assert "site:bh.asgharali.com" in q


class TestProdCallSiteUsesLimit8:
    """Regression guard: the prod price-escalation discovery call must pass
    limit=8, not 4 — otherwise shopalmoayyed silently drops out of the window
    again. We assert against the source text of _get_price (the call is inline,
    not a separate function, so we pin the literal)."""

    def test_get_price_discovery_call_passes_limit_8(self):
        import inspect
        from app.services.structured_comparison_service import (
            StructuredComparisonService,
        )

        src = inspect.getsource(StructuredComparisonService._get_price)
        # Find the build_site_discovery_query(...) call and assert limit=8.
        m = re.search(
            r"build_site_discovery_query\((?:[^()]|\([^()]*\))*?\)", src, re.S
        )
        assert m, "build_site_discovery_query call not found in _get_price"
        call = m.group(0)
        assert "limit=8" in call, (
            f"prod discovery call must use limit=8 (I5.4); found: {call!r}"
        )
