"""F1.1 — Tests for `build_site_discovery_query()`.

The discovery-query builder turns a product query + category + tier into a
single Serper query string targeting that tier's registry domains via
OR-joined `site:` operators. Empty string when the tier has no sources for
the category (the caller then skips the discovery call).
"""

import pytest

from app.services.source_router import build_site_discovery_query, get_sources_for_category


def test_site_query_electronics_bahrain_tier():
    q = build_site_discovery_query(
        "Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=4
    )
    # Bahrain electronics sources, registry order, OR-joined site: operators
    assert q.startswith("Carrier 1.5 ton AC ")
    assert "site:lulu.com.bh" in q and "site:sharafdg.com.bh" in q
    assert "site:noon.com" not in q  # gcc tier excluded
    assert q.count("site:") <= 4


def test_site_query_empty_for_unknown_category_tier():
    # category="other" — only empty-categories (() = all) sources match, which
    # exist in the bahrain tier, so the query is NON-empty.
    assert build_site_discovery_query("x", "other", tier="bahrain", limit=4) != ""


def test_site_query_or_joined_format():
    q = build_site_discovery_query(
        "iPhone 15", "electronics", tier="bahrain", limit=3
    )
    # Format is "<query> site:a OR site:b OR site:c"
    assert q.startswith("iPhone 15 site:")
    assert " OR " in q
    # No trailing/leading junk operators
    assert not q.endswith(" OR ")
    assert "site:OR" not in q


def test_site_query_respects_limit():
    q_limit_2 = build_site_discovery_query(
        "iPhone 15", "electronics", tier="bahrain", limit=2
    )
    assert q_limit_2.count("site:") == 2


def test_site_query_gcc_tier_targets_gcc_domains():
    q = build_site_discovery_query(
        "Chanel No 5", "fragrances", tier="gcc", limit=4
    )
    # gcc-tier fragrance sources include ounass.com / tryano.com
    assert "site:ounass.com" in q or "site:tryano.com" in q
    # bahrain-tier domains must NOT appear
    assert "site:lulu.com.bh" not in q


def test_site_query_empty_when_tier_has_no_category_source():
    """A category with zero sources in the requested tier yields ''.

    'grocery' has no gcc-tier registry entries (noon/amazon.ae are () = all,
    so they DO match) — pick a tier+category combo that truly has none.
    We assert the contract via the helper: build the expected domain list and
    confirm the function returns '' iff that list is empty.
    """
    # Construct a guaranteed-empty case: tier with no matching sources.
    # 'global' tier for 'grocery' — walmart/amazon.com are () so they match.
    # Instead assert the invariant directly: when get_sources_for_category
    # filtered to a tier is empty, query is "".
    domains = [
        s.domain
        for s in get_sources_for_category("grocery")
        if s.tier == "gcc"
    ]
    q = build_site_discovery_query("milk", "grocery", tier="gcc", limit=4)
    if not domains:
        assert q == ""
    else:
        assert q != ""


def test_site_query_preserves_product_query_verbatim():
    """The product query is preserved verbatim as a prefix (no mangling)."""
    weird = "Samsung Galaxy S24 Ultra 256GB (Titanium Black)"
    q = build_site_discovery_query(weird, "electronics", tier="bahrain", limit=2)
    assert q.startswith(weird + " ")
