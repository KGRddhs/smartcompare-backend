"""Deep-review coverage fixes — the sharafdg Algolia + extra.com Unbxd genuine-BHD
adapters were built but unwired. Pin that the registry now routes them.
"""
from __future__ import annotations

from app.services.source_router import (
    get_algolia_sources_for_category, _direct_fetch_sources,
)


def _hosts(sources):
    return {getattr(s, "domain", "") for s in sources}


def test_sharafdg_is_an_electronics_algolia_source():
    hosts = _hosts(get_algolia_sources_for_category("electronics"))
    assert "bahrain.sharafdg.com" in hosts


def test_extra_is_an_electronics_unbxd_source():
    hosts = _hosts(_direct_fetch_sources("electronics", "unbxd"))
    assert "extra.com" in hosts
