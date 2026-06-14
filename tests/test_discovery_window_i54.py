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

    def test_shopalmoayyed_needs_limit_8_after_microless_add(self):
        # History: the dead-row purge (behbehani/jumbo) briefly let shopalmoayyed
        # fit at limit=4 (idx 3). The S3 PDP-curl add of bahrain.microless.com
        # (curl-verified electronics, idx 3) re-displaced it to idx 4 — so it's
        # OUT of limit=4 again but IN the PROD limit=8 window. This re-justifies
        # why the prod discovery call uses limit=8 (not just forward-headroom —
        # shopalmoayyed actively needs it). bahrain-electronics order now:
        # [0] gcc.lulu [1] sharafdg [2] extra [3] microless [4] shopalmoayyed.
        q4 = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=4
        )
        assert "site:shopalmoayyed.com" not in q4  # idx 4 — outside limit=4
        q8 = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=8
        )
        assert "site:shopalmoayyed.com" in q8  # idx 4 — inside limit=8 (PROD)

    def test_limit_8_still_single_query_or_chain(self):
        q = build_site_discovery_query(
            "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=8
        )
        # One query string, OR-joined site: operators, no junk.
        assert q.startswith("Carrier 1.5 ton AC site:")
        assert " OR " in q
        assert not q.endswith(" OR ")
        assert "site:OR" not in q
        # 5 live bahrain-electronics sources now (gcc.lulu, sharafdg, extra,
        # microless, shopalmoayyed — after the dead-row purge of behbehani+jumbo
        # and the PDP-curl add of microless) → 5 site: ops, within the limit=8
        # ceiling (still room for future additions).
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
