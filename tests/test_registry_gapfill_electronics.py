"""S3-genuine gap-fill — electronics registry corrections (team-lead research).

Verified live (Decision-F, 2026-06-14):
- luluhypermarket.com (bare host) -> RETARGET to gcc.luluhypermarket.com: the
  bare host's catalog is en-ae/AED; gcc + /en-bh/ serves BHD (the AED-vs-BHD
  host bug = THE electronics keystone). www.luluhypermarket.com now redirects to
  gcc.luluhypermarket.com/en-bh/ (BHD-dominant).
- jumboelectronics.com -> DELETE: 114-byte parked /lander redirect, 0 shop
  signals (200-but-not-a-store; a dead site: row starves the limit=8 discovery).
- behbehani.com -> DELETE: brochure splash (3.6KB), no shop.

godukkan.com + bahrain.microless.com ADD + the SPA downgrades are HELD pending
the Serper rotation (need a live PDP curl to Decision-F-confirm before adding).
"""

import pytest

from app.services.source_router import SOURCE_REGISTRY, score_source


def _domains():
    return {s.domain for s in SOURCE_REGISTRY}


class TestLuluRetarget:
    def test_gcc_lulu_registered(self):
        assert "gcc.luluhypermarket.com" in _domains()

    def test_bare_lulu_removed(self):
        """The bare host (AED catalog) must NOT remain — it yields nothing in BHD."""
        assert "luluhypermarket.com" not in _domains()

    def test_gcc_lulu_is_bahrain_allcat(self):
        by = {s.domain: s for s in SOURCE_REGISTRY}
        s = by["gcc.luluhypermarket.com"]
        assert s.tier == "bahrain"
        assert s.weight == 3.0
        assert s.categories == ()  # broad: electronics+grocery+pharmacy+beauty

    def test_gcc_lulu_scores_bahrain_weight(self):
        # all-category source scores 3.0 for any category
        assert score_source("https://gcc.luluhypermarket.com/en-bh/x/p/1", "electronics") == 3.0
        assert score_source("https://gcc.luluhypermarket.com/en-bh/x/p/1", "grocery") == 3.0


class TestDeadElectronicsDeleted:
    @pytest.mark.parametrize("domain", ["jumboelectronics.com", "behbehani.com"])
    def test_dead_store_removed(self, domain):
        assert domain not in _domains()
