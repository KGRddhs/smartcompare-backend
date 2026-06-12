"""I5.3 (Bundle B S2) — registry dead-domain replacement (Decision F: verify-or-delete).

Control-calibrated liveness 2026-06-11 (dispatcher safety rail — a sandbox DNS
block reads identically to a dead domain, so a control set must pass in the
same env before any "dead" verdict, and NXDOMAIN must be distinguished from a
403 bot-defense which is ALIVE):

  CONTROL (same env): google.com 200, shopalmoayyed.com 200 → sandbox not blocked.
  DEAD = NXDOMAIN (curl exit 6 "Could not resolve host" + socket.gethostbyname
         gaierror): lulu.com.bh, sharafdg.com.bh, extra.com.bh, carrefourbh.com,
         carrefour.com.bh, geant.com.bh, eroselectronics.com.
  ALIVE (DNS→IP + 200): luluhypermarket.com (192.185.171.105; earlier 403 was a
         Cloudflare challenge = alive-defended, kept), bahrain.sharafdg.com
         (104.18.31.100; 6 JSON-LD blocks + 258 BHD), extra.com (104.18.14.223;
         3 JSON-LD + BHD /ar-bh), behbehani.com (18.185.202.132),
         jumboelectronics.com (76.223.54.146).

Decision F "never fabricate" cuts both ways — never fabricate liveness AND
never fabricate death. Every committed domain is NXDOMAIN-proven dead or
IP+200-proven alive.
"""

import pytest

from app.services.source_router import (
    SOURCE_REGISTRY,
    get_sources_for_category,
    score_source,
)


_REGISTRY_DOMAINS = {s.domain for s in SOURCE_REGISTRY}

# Domains proven NXDOMAIN 2026-06-11 — must NOT appear in the registry.
_DEAD_NXDOMAIN = {
    "lulu.com.bh",
    "sharafdg.com.bh",
    "extra.com.bh",
    "carrefourbh.com",
    "geant.com.bh",
    "eroselectronics.com",
}

# Replacements proven alive (DNS→IP + HTTP 200) — must appear in the registry.
_LIVE_REPLACEMENTS = {
    "luluhypermarket.com",
    "bahrain.sharafdg.com",
    "extra.com",
}


class TestDeadDomainsRemoved:
    @pytest.mark.parametrize("dead", sorted(_DEAD_NXDOMAIN))
    def test_dead_nxdomain_not_in_registry(self, dead):
        assert dead not in _REGISTRY_DOMAINS, (
            f"{dead} is NXDOMAIN (proven 2026-06-11) — must not be a registry "
            f"row (it starves the limit=4 discovery window with a dead site:)"
        )


class TestLiveReplacementsPresent:
    @pytest.mark.parametrize("live", sorted(_LIVE_REPLACEMENTS))
    def test_live_replacement_in_registry(self, live):
        assert live in _REGISTRY_DOMAINS, f"{live} (alive 2026-06-11) must replace its dead predecessor"

    def test_luluhypermarket_all_categories_weight_3(self):
        # lulu.com.bh was all-category bahrain weight 3.0; replacement inherits.
        for cat in ("electronics", "supplements", "grocery", "fashion"):
            assert score_source(f"https://www.luluhypermarket.com/x", category=cat) == 3.0

    def test_bahrain_sharafdg_electronics_weight_3(self):
        # sharafdg.com.bh was electronics-only bahrain 3.0; replacement inherits.
        assert score_source("https://bahrain.sharafdg.com/product/p1", category="electronics") == 3.0
        # Category filtering preserved (electronics-only → 0.5 for supplements).
        assert score_source("https://bahrain.sharafdg.com/product/p1", category="supplements") == 0.5

    def test_extra_com_electronics_weight_3(self):
        assert score_source("https://www.extra.com/ar-bh/product/p1", category="electronics") == 3.0

    def test_bahrain_sharafdg_in_electronics_discovery(self):
        domains = [s.domain for s in get_sources_for_category("electronics")]
        assert "bahrain.sharafdg.com" in domains
        assert "extra.com" in domains
        # The dead predecessors are gone.
        assert "sharafdg.com.bh" not in domains
        assert "extra.com.bh" not in domains


class TestKeptLiveDomains:
    def test_behbehani_kept(self):
        # behbehani.com proven alive → stays (electronics+fashion bahrain 3.0).
        assert score_source("https://behbehani.com/product/p1", category="electronics") == 3.0

    def test_jumbo_kept(self):
        assert score_source("https://jumboelectronics.com/product/p1", category="electronics") == 3.0
