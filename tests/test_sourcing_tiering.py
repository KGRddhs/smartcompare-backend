"""Phase 1 Task 1.5 — sourcing tiering (Serper-light discovery → genuine render).

F1.4 settled the head-to-head: Firecrawl `enhanced` does NOT crack Cloudflare;
Scrape.do `super` does but is $249/mo (OUT of scope). The free-tier model is:
  - Serper = LIGHT discovery (find candidate BH URLs) + lighter lookups.
  - genuine curl/page-scrape + (when available) firecrawl/scrapedo = HEAVY render.
  - the cascade MUST prefer a genuine BH price over a converted/estimated one
    REGARDLESS of price/rank ("MOST AUTHORITATIVE not lowest").

D3 is MEASURE-ONLY this cycle — NO provider rewire. So this module pins the
EXISTING tiering CONTRACT (the authority ordering + the genuine predicate) so a
future refactor can't silently invert it. The selection function is `_select_best`
over `{value, source_method, rank, raw_data}` candidates.
"""

import pytest

from app.services.price_service import (
    _select_best,
    _is_genuine_bh_candidate,
    _GENUINE_BH_SOURCE_METHODS,
)


def _cand(value, source_method, rank=0, retailer=None):
    raw = {"source_method": source_method}
    if retailer:
        raw["retailer"] = retailer
    return {"value": value, "source_method": source_method, "rank": rank, "raw_data": raw}


# ---------------------------------------------- the genuine predicate ---

class TestGenuinePredicate:
    def test_local_bhd_is_genuine(self):
        assert _is_genuine_bh_candidate(_cand(80, "local_bhd")) is True

    def test_page_scrape_jsonld_is_genuine(self):
        assert _is_genuine_bh_candidate(_cand(244.99, "page_scrape_jsonld")) is True

    def test_converted_usd_is_not_genuine(self):
        assert _is_genuine_bh_candidate(_cand(85, "converted_usd")) is False

    def test_estimated_is_not_genuine(self):
        assert _is_genuine_bh_candidate(_cand(70, "estimated")) is False

    def test_global_tier_domain_never_genuine(self):
        # apple-phantom guard: a global-tier domain stamped genuine is still not a
        # real BH price.
        c = _cand(198.9, "page_scrape_jsonld", retailer="apple.com")
        assert _is_genuine_bh_candidate(c) is False


# ------------------------------------------ authority ordering (tiering) ---

class TestAuthorityOrdering:
    def test_genuine_beats_converted_even_when_pricier(self):
        # The CORE tiering contract: a genuine BH price wins over a cheaper
        # converted one (authority, not lowest). Prod-verify regression: a
        # converted 198.9 was beating a genuine 244.99.
        converted = _cand(198.9, "converted_usd", rank=85, retailer="apple.com")
        genuine = _cand(244.99, "page_scrape_jsonld", rank=85, retailer="sharafdg.com")
        assert _select_best([converted, genuine]) is genuine

    def test_genuine_beats_converted_even_when_lower_rank(self):
        converted = _cand(90, "converted_usd", rank=99, retailer="amazon.com")
        genuine = _cand(95, "local_bhd", rank=10, retailer="lulu.bh")
        assert _select_best([converted, genuine]) is genuine

    def test_among_genuine_higher_rank_wins(self):
        lo = _cand(100, "local_bhd", rank=10, retailer="lulu.bh")
        hi = _cand(110, "page_scrape_jsonld", rank=90, retailer="sharafdg.com")
        assert _select_best([lo, hi]) is hi

    def test_among_genuine_same_rank_lower_price_wins(self):
        cheap = _cand(100, "local_bhd", rank=50, retailer="lulu.bh")
        dear = _cand(130, "local_bhd", rank=50, retailer="sharafdg.com")
        assert _select_best([cheap, dear]) is cheap

    def test_only_converted_available_returns_converted(self):
        # When there is NO genuine candidate, the cascade still returns the best
        # converted one (it later becomes the parked converted_fallback +
        # negative-cache, Task 1.3).
        c1 = _cand(90, "converted_usd", rank=50)
        c2 = _cand(85, "converted_usd", rank=50)
        winner = _select_best([c1, c2])
        assert winner in (c1, c2)
        assert _is_genuine_bh_candidate(winner) is False

    def test_empty_candidates_returns_none(self):
        assert _select_best([]) is None


# ------------------------------------------------- Serper-light marker ---

class TestSerperLightDiscovery:
    def test_discovery_query_is_a_single_site_query(self):
        """Serper's role is LIGHT discovery — build_site_discovery_query produces
        ONE `site:` query string (a single ~1-credit lookup), not a heavy
        multi-call extraction."""
        from app.services.source_router import build_site_discovery_query
        q = build_site_discovery_query("iPhone 15 256GB", "electronics")
        # A non-empty discovery query string (or None when no BH sources for the
        # category) — never a list of many queries.
        assert q is None or isinstance(q, str)
        if isinstance(q, str):
            assert "site:" in q.lower()
