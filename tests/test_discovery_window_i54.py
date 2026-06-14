"""I5.4 (Bundle B S2) — discovery window widening.

ORIGINAL I5.4 (2026-06-11): after I5.3 the electronics bahrain registry order was
  [0] luluhypermarket.com [1] bahrain.sharafdg.com [2] extra.com
  [3] behbehani.com [4] jumboelectronics.com [5] shopalmoayyed.com
and the prod discovery (`_get_price`, ssc) sliced with `limit=4`, dropping index
4-5 — so shopalmoayyed.com (the F1.5 appliance/AC JSON-LD source) was NEVER
queried. I5.4 bumped the PROD call-site limit 4→8.

S3-GENUINE GAP-FILL UPDATE (Decision-F, 2026-06-14): the gap-fill DELETED the two
dead early-window rows (behbehani.com idx 3 + jumboelectronics.com idx 4 — both
200-but-not-a-store), so the live order collapsed to
  [0] gcc.luluhypermarket.com [1] bahrain.sharafdg.com [2] extra.com
  [3] shopalmoayyed.com
shopalmoayyed now sits at index 3 — inside even a limit=4 window. The limit=8
PROD call is KEPT as forward-headroom (future bahrain-electronics additions push
the count back above 4), but it is no longer load-bearing for shopalmoayyed.
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

    def test_limit_4_now_reaches_shopalmoayyed_after_deadrow_purge(self):
        # SUPERSEDES the old "limit=4 did NOT reach" pin. The original I5.4 bug
        # was that two dead rows (behbehani idx3 + jumbo idx4) occupied the early
        # window and pushed shopalmoayyed past index 3. The S3-genuine gap-fill
        # DELETED both, so shopalmoayyed now sits at index 3 — inside the limit=4
        # window. (The limit=8 PROD call is kept as forward-headroom only.)
        q4 = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=4
        )
        assert "site:shopalmoayyed.com" in q4

    def test_limit_8_still_single_query_or_chain(self):
        q = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=8
        )
        # One query string, OR-joined site: operators, no junk.
        assert q.startswith("Carrier 1.5 ton AC site:")
        assert " OR " in q
        assert not q.endswith(" OR ")
        assert "site:OR" not in q
        # 4 live bahrain-electronics sources after the S3-genuine dead-row purge
        # (was 6; behbehani+jumbo deleted) → 4 site: ops, still within the
        # limit=8 ceiling (room for future additions).
        n = q.count("site:")
        assert 2 < n <= 8

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
