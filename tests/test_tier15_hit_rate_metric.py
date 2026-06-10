"""F1.6 — tier1_5_hit_rate Redis counters + /admin/costs aggregate.

Counters (cache_service helpers, fire-and-forget, fail-open, 30d TTL):
  tier15:attempts:{category}:{YYYYMMDD}      — escalation entered the scrape pool
  tier15:hits:{category}:{YYYYMMDD}          — a scraped winner was returned
  tier15:source_hits:{domain}:{YYYYMMDD}     — which domain won

`get_tier15_hit_rate(days=7)` aggregates the trailing window into a
per-category {attempts, hits, hit_rate} block surfaced under
/admin/costs -> tier1_5_hit_rate.
"""

import datetime as _dt

import pytest

import app.services.cache_service as cs


class _FakeRedis:
    """Minimal in-memory stand-in for the upstash/redis client."""

    def __init__(self):
        self.store = {}
        self.expiries = {}

    def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def expire(self, key, seconds):
        self.expiries[key] = seconds
        return True

    def get(self, key):
        v = self.store.get(key)
        return None if v is None else str(v)

    def mget(self, *keys):
        # Accept both mget("a","b") and mget(["a","b"]).
        if len(keys) == 1 and isinstance(keys[0], (list, tuple)):
            keys = tuple(keys[0])
        out = []
        for k in keys:
            v = self.store.get(k)
            out.append(None if v is None else str(v))
        return out


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(cs, "redis_client", fake)
    return fake


# ---------- counter recording ----------

def test_record_attempt_increments_category_counter(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    cs.record_tier15_attempt("electronics")
    assert fake_redis.store[f"tier15:attempts:electronics:{today}"] == 1
    # 30d TTL set.
    assert fake_redis.expiries[f"tier15:attempts:electronics:{today}"] == 30 * 86400


def test_record_hit_increments_category_and_source(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    cs.record_tier15_hit("electronics", "sharafdg.com.bh")
    assert fake_redis.store[f"tier15:hits:electronics:{today}"] == 1
    assert fake_redis.store[f"tier15:source_hits:sharafdg.com.bh:{today}"] == 1


def test_record_hit_without_domain_only_category(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    cs.record_tier15_hit("fashion", None)
    assert fake_redis.store[f"tier15:hits:fashion:{today}"] == 1
    # No source_hits key created for a None domain.
    assert not any(k.startswith("tier15:source_hits:") for k in fake_redis.store)


def test_counters_fail_open_without_redis(monkeypatch):
    """No redis client -> recording is a silent no-op (never raises)."""
    monkeypatch.setattr(cs, "redis_client", None)
    cs.record_tier15_attempt("electronics")
    cs.record_tier15_hit("electronics", "lulu.com.bh")
    # Nothing to assert beyond "did not raise".


# ---------- aggregate ----------

def test_hit_rate_aggregate_per_category(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    # 4 attempts, 3 hits for electronics today.
    fake_redis.store[f"tier15:attempts:electronics:{today}"] = 4
    fake_redis.store[f"tier15:hits:electronics:{today}"] = 3
    # 2 attempts, 0 hits for grocery today.
    fake_redis.store[f"tier15:attempts:grocery:{today}"] = 2

    agg = cs.get_tier15_hit_rate(days=7, categories=["electronics", "grocery"])

    assert agg["electronics"]["attempts"] == 4
    assert agg["electronics"]["hits"] == 3
    assert agg["electronics"]["hit_rate"] == pytest.approx(0.75)
    assert agg["grocery"]["attempts"] == 2
    assert agg["grocery"]["hits"] == 0
    assert agg["grocery"]["hit_rate"] == 0.0


def test_hit_rate_aggregate_sums_multiple_days(fake_redis):
    now = _dt.datetime.now(_dt.timezone.utc)
    d0 = now.strftime("%Y%m%d")
    d1 = (now - _dt.timedelta(days=1)).strftime("%Y%m%d")
    fake_redis.store[f"tier15:attempts:electronics:{d0}"] = 2
    fake_redis.store[f"tier15:hits:electronics:{d0}"] = 1
    fake_redis.store[f"tier15:attempts:electronics:{d1}"] = 2
    fake_redis.store[f"tier15:hits:electronics:{d1}"] = 2

    agg = cs.get_tier15_hit_rate(days=7, categories=["electronics"])
    assert agg["electronics"]["attempts"] == 4
    assert agg["electronics"]["hits"] == 3
    assert agg["electronics"]["hit_rate"] == pytest.approx(0.75)


def test_hit_rate_zero_attempts_is_zero_rate(fake_redis):
    agg = cs.get_tier15_hit_rate(days=7, categories=["makeup"])
    assert agg["makeup"]["attempts"] == 0
    assert agg["makeup"]["hits"] == 0
    assert agg["makeup"]["hit_rate"] == 0.0


def test_hit_rate_aggregate_fail_open_without_redis(monkeypatch):
    monkeypatch.setattr(cs, "redis_client", None)
    agg = cs.get_tier15_hit_rate(days=7, categories=["electronics"])
    # Returns a well-formed zeroed block, never raises.
    assert agg["electronics"]["attempts"] == 0
    assert agg["electronics"]["hit_rate"] == 0.0
