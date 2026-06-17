"""Guards that a cached price PRESERVES its source_method on round-trip.

A4 dependency (eval --read-cache, Phase 7.2): the cache-reading eval credits
genuine-BH-share by reading `price.source_method` from cached prices. If the
price cache ever stored a stripped/normalized value that dropped or re-stamped
`source_method`, a genuine `page_scrape_jsonld` price served from cache would
read as no-provenance and genuine-share would silently under-report.

cache_price -> get_cached_price JSON-round-trips the whole price dict today
(via set_cached/get_cached). This pins that invariant so a future "normalize
the cached value" change can't break the warmer's genuine-share measurement.

Uses a dict-backed fake for the Redis layer (cache_service is fail-open: with
redis_client None it no-ops), so this is a pure in-process round-trip — no
network, no live Redis.
"""
from __future__ import annotations

import json

import pytest

from app.services import cache_service
from scripts.eval_runner import GENUINE_BH_SOURCE_METHODS


@pytest.fixture
def fake_redis(monkeypatch):
    """Back cache_service's _redis_get/_redis_set with an in-process dict so
    set_cached/get_cached actually round-trip (the real client is None in unit
    tests, which would make every get a fail-open miss)."""
    store: dict[str, str] = {}

    def _set(key: str, value: str, ex=None) -> bool:
        store[key] = value
        return True

    def _get(key: str):
        return store.get(key)

    # A non-None marker so any `if redis_client:` guard in the helpers passes.
    monkeypatch.setattr(cache_service, "redis_client", object())
    monkeypatch.setattr(cache_service, "_redis_set", _set)
    monkeypatch.setattr(cache_service, "_redis_get", _get)
    return store


def test_cache_price_preserves_source_method(fake_redis):
    price = {"amount": 79.5, "currency": "BHD", "retailer": "alhajis",
             "url": "https://alhajis.com/p/123", "source_method": "page_scrape_jsonld"}
    assert cache_service.cache_price("Tom Ford Tobacco Vanille", "bahrain", price) is True
    got = cache_service.get_cached_price("Tom Ford Tobacco Vanille", "bahrain")
    assert got is not None
    assert got["source_method"] == "page_scrape_jsonld"
    # Full fidelity — amount/currency/retailer/url all survive the round-trip.
    assert got["amount"] == 79.5
    assert got["currency"] == "BHD"
    assert got["retailer"] == "alhajis"
    assert got["url"] == "https://alhajis.com/p/123"


@pytest.mark.parametrize("method", sorted(GENUINE_BH_SOURCE_METHODS))
def test_every_genuine_method_survives_cache_roundtrip(method, fake_redis):
    """Each genuine-BH method the eval credits must survive the cache round-trip
    intact — otherwise --read-cache under-reports genuine-share for that source."""
    price = {"amount": 100.0, "currency": "BHD", "source_method": method}
    cache_service.cache_price(f"prod-{method}", "bahrain", price)
    got = cache_service.get_cached_price(f"prod-{method}", "bahrain")
    assert got["source_method"] == method
    # And the eval would still classify it as genuine after the round-trip.
    assert got["source_method"] in GENUINE_BH_SOURCE_METHODS


def test_converted_and_estimated_methods_also_preserved(fake_redis):
    """Non-genuine methods must round-trip unchanged too (so the eval's
    converted/estimated buckets stay accurate, not silently re-bucketed)."""
    for method in ("converted_usd", "estimated"):
        cache_service.cache_price(f"x-{method}", "bahrain",
                                  {"amount": 85.0, "source_method": method})
        got = cache_service.get_cached_price(f"x-{method}", "bahrain")
        assert got["source_method"] == method


def test_roundtrip_value_is_json_clean(fake_redis):
    """The stored blob is valid JSON carrying source_method (defends the
    serialization seam set_cached uses)."""
    price = {"amount": 50.0, "currency": "BHD", "source_method": "local_bhd"}
    cache_service.cache_price("groc", "bahrain", price)
    key = cache_service.get_price_cache_key("groc", "bahrain")
    raw = fake_redis[key]
    parsed = json.loads(raw)
    assert parsed["source_method"] == "local_bhd"
