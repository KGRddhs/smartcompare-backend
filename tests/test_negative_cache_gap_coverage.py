"""Gap coverage for the Phase 1.3 negative-cache decision (Faithful-Results).

Pre-authored (dispatcher ruling D-R4) against Backend's committed Phase 1.3
work. Backend's tests/test_negative_cache_structural_gap.py covers the happy
paths + the main edge cases (estimated/converted/pending -> True; genuine ->
False; None -> True; validation_rejected -> False). This file adds the BRANCH
coverage Backend's set leaves open, so the integrated Wave-2 run on QA's tree
hits 80%+ on should_negative_cache:

  - a dict carrying NO source_method key (blank) -> dead-end (True)
  - an UNRECOGNIZED non-genuine method -> dead-end (True)
  - the defensive guard: a method that is in the genuine set BUT also carries a
    'converted'/'estimate' token is NOT treated as genuine -> dead-end (True)
  - negative_cache_key round-trips an already-size-aware price key unchanged

Pure functions, no network, no cost.
"""
from __future__ import annotations

import pytest

from app.services.price_service import (
    negative_cache_key,
    should_negative_cache,
    _GENUINE_BH_SOURCE_METHODS,
)


class TestShouldNegativeCacheGaps:
    def test_dict_without_source_method_is_dead_end(self):
        # A resolved-price dict that carries no method key at all -> we could not
        # vouch for a genuine BH price -> negative-cache it. (Backend tested None,
        # not a dict-without-method.)
        assert should_negative_cache({"amount": 80.0, "currency": "BHD"}) is True

    def test_blank_source_method_is_dead_end(self):
        assert should_negative_cache({"amount": 80.0, "source_method": ""}) is True
        assert should_negative_cache({"amount": 80.0, "source_method": "   "}) is True

    def test_unknown_non_genuine_method_is_dead_end(self):
        # A method we don't recognize is NOT genuine -> dead-end (so a future
        # provider string can't silently dodge the negative cache).
        assert should_negative_cache(
            {"amount": 80.0, "source_method": "some_future_unknown_method"}
        ) is True

    def test_genuine_token_with_converted_substring_is_dead_end(self):
        # Defensive guard: even if a method is (hypothetically) in the genuine set
        # but ALSO carries the 'converted' token, it must NOT count as genuine.
        # Simulate by constructing a method that contains a genuine apex + token.
        assert should_negative_cache(
            {"amount": 85.0, "source_method": "page_scrape_jsonld_converted"}
        ) is True

    def test_genuine_token_with_estimate_substring_is_dead_end(self):
        assert should_negative_cache(
            {"amount": 85.0, "source_method": "local_bhd_estimate"}
        ) is True

    @pytest.mark.parametrize("method", sorted(_GENUINE_BH_SOURCE_METHODS))
    def test_every_pure_genuine_method_is_not_dead_end(self, method):
        # Mirror of the genuine set: each pure genuine method must NOT negative-
        # cache (so a real BH price is never sentinel-suppressed). This pins the
        # not-dead-end branch across the WHOLE set, not just the 3 Backend spot-
        # checked.
        assert should_negative_cache({"amount": 100.0, "source_method": method}) is False

    def test_case_insensitive_method_matching(self):
        # Methods are lowercased before comparison — an upper/mixed-case genuine
        # method still resolves as genuine (not a dead-end).
        assert should_negative_cache({"amount": 80.0, "source_method": "LOCAL_BHD"}) is False
        # And an upper-case estimated is still a dead-end.
        assert should_negative_cache({"amount": 70.0, "source_method": "ESTIMATED"}) is True


class TestNegativeCacheKeyGaps:
    def test_namespaces_a_size_aware_key_unchanged(self):
        # Task 1.4 size-aware keys must pass through verbatim under the nogenuine:
        # prefix (so the structural gap is per product+size+region).
        k = "price:bahrain:iphone_15_256gb"
        assert negative_cache_key(k) == "nogenuine:price:bahrain:iphone_15_256gb"

    def test_distinct_size_keys_yield_distinct_sentinels(self):
        # The 256GB and 128GB variants must NOT share a negative-cache sentinel
        # (otherwise a gap on one would suppress the other).
        a = negative_cache_key("price:bahrain:iphone_15_256gb")
        b = negative_cache_key("price:bahrain:iphone_15_128gb")
        assert a != b
