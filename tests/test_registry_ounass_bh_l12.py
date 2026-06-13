"""L1.2 (Bundle B S3 'Sources') — bahrain.ounass.com registry add.

ounass.com is already a registry GCC row (fashion/fragrances/makeup). Its
Bahrain subdomain `bahrain.ounass.com` is verified-live + curl-extractable:
product pages expose static Product JSON-LD with priceCurrency=BHD (confirmed
end-to-end — extract_price_from_html pulls 80 BHD from the captured fixture,
once the L1.4 brand-field fix lets the brand match). Adding it as a bahrain-tier
3.0 source gives the cascade a real-BHD luxury source for fragrances/fashion/
makeup — consistent with Ahmed's "facts, no estimation" directive (this domain
PRODUCES real prices via the free curl path, unlike the Landmark fashion SPAs).

Decision-F: control-calibrated live same-session (google.com + shopalmoayyed.com
200; bahrain.ounass.com 200 + BHD product JSON-LD). Pre-approved by Ahmed for
verified-live BH domains. Free-tier safe.
"""

import pytest

from app.services.source_router import (
    SOURCE_REGISTRY,
    get_sources_for_category,
    score_source,
)


def test_bahrain_ounass_registered_as_bahrain_tier():
    by_domain = {s.domain: s for s in SOURCE_REGISTRY}
    assert "bahrain.ounass.com" in by_domain
    s = by_domain["bahrain.ounass.com"]
    assert s.tier == "bahrain"
    assert s.weight == 3.0


def test_bahrain_ounass_categories():
    by_domain = {s.domain: s for s in SOURCE_REGISTRY}
    s = by_domain["bahrain.ounass.com"]
    for cat in ("fragrances", "fashion", "makeup"):
        assert cat in s.categories


@pytest.mark.parametrize("category", ["fragrances", "fashion", "makeup"])
def test_bahrain_ounass_scores_bahrain_weight(category):
    """A bahrain.ounass.com URL scores the bahrain-tier weight (3.0) in its
    categories — outranks the GCC ounass.com apex (1.5)."""
    assert score_source("https://bahrain.ounass.com/x.html", category) == 3.0


def test_bahrain_ounass_in_bahrain_tier_discovery():
    """It surfaces in the bahrain-tier sources for fragrances (so the Bahrain
    site: discovery query can include it)."""
    bh_frag = [
        s.domain
        for s in get_sources_for_category("fragrances", usage="price")
        if s.tier == "bahrain"
    ]
    assert "bahrain.ounass.com" in bh_frag


def test_gcc_ounass_apex_still_present():
    """The original GCC ounass.com row is untouched (additive change)."""
    by_domain = {s.domain: s for s in SOURCE_REGISTRY}
    assert "ounass.com" in by_domain
    assert by_domain["ounass.com"].tier == "gcc"
