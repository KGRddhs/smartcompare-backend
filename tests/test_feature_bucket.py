"""Unit tests for app.utils.feature_bucket.

Asserts:
1. djb2 is deterministic.
2. hash_bucket boundary cases (percent <= 0, >= 100, empty id).
3. Determinism + monotonic ramp (in at 10% → in at 50% → in at 100%).
4. Even distribution at 50% over 1000 random ids (~500 ± 10%).

Cross-language parity (Python ↔ TypeScript) lives in
`tests/test_feature_bucket_parity.py` so the parity fixture file can
fail loudly without obscuring local logic bugs.
"""
from __future__ import annotations

import pytest

from app.utils.feature_bucket import djb2, hash_bucket


class TestDjb2:
    def test_deterministic(self):
        assert djb2("user-abc") == djb2("user-abc")
        assert djb2("") == djb2("")

    def test_different_inputs_different_hashes(self):
        assert djb2("user-abc") != djb2("user-abd")
        assert djb2("a") != djb2("b")

    def test_returns_non_negative_int(self):
        for s in ["user-1", "user-99", "short", "a-much-longer-id-string"]:
            h = djb2(s)
            assert isinstance(h, int)
            assert h >= 0
            assert h < 2**32  # 32-bit unsigned range


class TestHashBucketBoundaries:
    def test_percent_zero_or_negative_returns_false(self):
        assert hash_bucket("user-1", 0) is False
        assert hash_bucket("user-1", -10) is False

    def test_percent_100_or_above_returns_true(self):
        assert hash_bucket("user-1", 100) is True
        assert hash_bucket("user-1", 150) is True

    def test_empty_or_none_id_returns_false(self):
        assert hash_bucket("", 50) is False
        assert hash_bucket(None, 50) is False


class TestHashBucketDeterminism:
    def test_same_inputs_same_output(self):
        first = hash_bucket("user-stable-1", 50)
        for _ in range(100):
            assert hash_bucket("user-stable-1", 50) == first

    def test_monotonic_ramp(self):
        """If percent grows, in-bucket users only grow (never shrink)."""
        ids = [f"user-{i}" for i in range(1000)]
        in_10 = {u for u in ids if hash_bucket(u, 10)}
        in_50 = {u for u in ids if hash_bucket(u, 50)}
        in_100 = {u for u in ids if hash_bucket(u, 100)}
        assert in_10 <= in_50, "user in at 10% must be in at 50%"
        assert in_50 <= in_100, "user in at 50% must be in at 100%"


class TestHashBucketDistribution:
    def test_distribution_at_50_percent(self):
        """1000 random ids at percent=50 → ~500 trues (±10%)."""
        trues = 0
        for i in range(1000):
            id_ = f"rnd-{i}-{(i * 7919) % 1000}"
            if hash_bucket(id_, 50):
                trues += 1
        assert 400 <= trues <= 600, f"expected ~500 ± 100, got {trues}"

    def test_distribution_at_10_percent(self):
        trues = 0
        for i in range(1000):
            id_ = f"rnd-{i}-{(i * 7919) % 1000}"
            if hash_bucket(id_, 10):
                trues += 1
        assert 50 <= trues <= 150, f"expected ~100 ± 50, got {trues}"
