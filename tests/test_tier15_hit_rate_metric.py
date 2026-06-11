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


# ---------- I5.1: per-domain source-hit aggregation ----------
# F1.6 already writes tier15:source_hits:{domain}:{YYYYMMDD}; F1.7 deferred the
# *surfacing* to S2. get_tier15_source_hits aggregates the trailing window into
# a {domain: hits} map (hits>0 only), so /admin/costs shows WHICH registry vs
# legacy domains produced the Tier-1.5 wins.


def test_source_hits_aggregate_explicit_domains(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    fake_redis.store[f"tier15:source_hits:shopalmoayyed.com:{today}"] = 5
    fake_redis.store[f"tier15:source_hits:talabat.com:{today}"] = 3

    out = cs.get_tier15_source_hits(days=7, domains=["shopalmoayyed.com", "talabat.com", "noon.com"])
    assert out["shopalmoayyed.com"] == 5
    assert out["talabat.com"] == 3
    # Domains with zero hits are omitted (keeps the dashboard line readable).
    assert "noon.com" not in out


def test_source_hits_sums_multiple_days(fake_redis):
    now = _dt.datetime.now(_dt.timezone.utc)
    d0 = now.strftime("%Y%m%d")
    d1 = (now - _dt.timedelta(days=1)).strftime("%Y%m%d")
    fake_redis.store[f"tier15:source_hits:talabat.com:{d0}"] = 2
    fake_redis.store[f"tier15:source_hits:talabat.com:{d1}"] = 4

    out = cs.get_tier15_source_hits(days=7, domains=["talabat.com"])
    assert out["talabat.com"] == 6


def test_source_hits_default_domains_from_registry(fake_redis):
    """With no explicit domain list, the aggregator probes the source registry
    (registry bucket) so the dashboard works without a hand-maintained list.
    F3: default return is now bucketed {registry, legacy}."""
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    # shopalmoayyed.com is a registry Bahrain electronics source.
    fake_redis.store[f"tier15:source_hits:shopalmoayyed.com:{today}"] = 7

    out = cs.get_tier15_source_hits(days=7)
    assert out["registry"].get("shopalmoayyed.com") == 7


def test_source_hits_sorted_descending(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    fake_redis.store[f"tier15:source_hits:talabat.com:{today}"] = 2
    fake_redis.store[f"tier15:source_hits:shopalmoayyed.com:{today}"] = 9
    fake_redis.store[f"tier15:source_hits:noon.com:{today}"] = 5

    out = cs.get_tier15_source_hits(
        days=7, domains=["talabat.com", "shopalmoayyed.com", "noon.com"]
    )
    # Insertion order reflects hit-count descending (top winner first).
    assert list(out.keys()) == ["shopalmoayyed.com", "noon.com", "talabat.com"]


def test_source_hits_fail_open_without_redis(monkeypatch):
    monkeypatch.setattr(cs, "redis_client", None)
    out = cs.get_tier15_source_hits(days=7, domains=["talabat.com"])
    assert out == {}


def test_source_hits_empty_when_no_hits(fake_redis):
    out = cs.get_tier15_source_hits(days=7, domains=["talabat.com", "noon.com"])
    assert out == {}


# ---------- G1 finding F2: subdomain win must land under registry apex ----------
# The writer recorded the raw winning host (uae.sharafdg.com) while the reader
# probed apex keys (sharafdg.com) → 3 hits showed as by_source 0. The fix
# normalizes the recorded domain to the matched registry apex at the
# record_tier15_hit call site (source_router.match_registry_apex, suffix-match
# like score_source).

def test_match_registry_apex_normalizes_subdomain():
    from app.services.source_router import match_registry_apex
    # A regional subdomain of a registry apex collapses to the apex.
    assert match_registry_apex("uae.sharafdg.com") == "sharafdg.com"
    assert match_registry_apex("www.noon.com") == "noon.com"
    # An exact apex stays itself.
    assert match_registry_apex("talabat.com") == "talabat.com"
    # An unknown / off-registry host is returned unchanged (lowercased, www-stripped).
    assert match_registry_apex("uae.example-random.com") == "uae.example-random.com"


def test_record_tier15_hit_normalizes_subdomain_to_apex(fake_redis):
    """When the winning retailer host is a registry-apex subdomain, the
    source_hits counter must land under the apex so by_source counts it."""
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    # record_tier15_hit normalizes the domain it receives (the caller passes the
    # raw host; cache_service applies match_registry_apex).
    cs.record_tier15_hit("electronics", "uae.sharafdg.com")
    # Lands under the apex, NOT under the raw subdomain.
    assert fake_redis.store.get(f"tier15:source_hits:sharafdg.com:{today}") == 1
    assert f"tier15:source_hits:uae.sharafdg.com:{today}" not in fake_redis.store


# ---------- G1 finding F3: by_source must SEE legacy_fallback wins ----------
# The reader defaulted to registry domains only, so legacy-whitelist wins
# (farfetch/ssense/net-a-porter-class, recorded with route="legacy_fallback")
# were written but never read — the F1.7 registry-vs-legacy question was
# unanswerable by construction. Fix: bucketed return {registry, legacy}, with
# the default domain set covering BOTH registry apexes and the legacy whitelist.

def test_source_hits_bucketed_shape(fake_redis):
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    fake_redis.store[f"tier15:source_hits:shopalmoayyed.com:{today}"] = 4   # registry
    fake_redis.store[f"tier15:source_hits:farfetch.com:{today}"] = 2        # legacy whitelist
    out = cs.get_tier15_source_hits(days=7)
    assert set(out.keys()) == {"registry", "legacy"}
    assert out["registry"].get("shopalmoayyed.com") == 4
    assert out["legacy"].get("farfetch.com") == 2


def test_source_hits_legacy_win_visible(fake_redis):
    """A legacy-fallback win must appear in the legacy bucket (the whole point
    of F3)."""
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    fake_redis.store[f"tier15:source_hits:net-a-porter.com:{today}"] = 3
    out = cs.get_tier15_source_hits(days=7)
    assert out["legacy"].get("net-a-porter.com") == 3


def test_source_hits_explicit_domains_still_supported_flat(fake_redis):
    """Passing an explicit `domains=` list keeps the simple flat {domain: hits}
    return — back-compat for callers that probe a known set (the bucketing only
    applies to the default registry+legacy probe)."""
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    fake_redis.store[f"tier15:source_hits:talabat.com:{today}"] = 5
    out = cs.get_tier15_source_hits(days=7, domains=["talabat.com", "noon.com"])
    assert out == {"talabat.com": 5}
