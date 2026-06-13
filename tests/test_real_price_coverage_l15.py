"""L1.5 (Bundle B S3 'Sources') — real-price-coverage runtime metric.

The prod-runtime counterpart to L4's eval estimate-share (no double-build — L4
owns the eval-side % via eval_runner; L1.5 owns the LIVE per-category gauge in
/admin/costs). Fire-and-forget Redis counters, fail-open, mirroring the F1.6
tier1_5_hit_rate pattern in cache_service.py.

`record_price_outcome(category, source_method)` classifies the settled price:
  - "estimated"  → source_method contains "estimate" (gpt_training_estimate, …)
  - "real"       → everything else (local_bhd, page_scrape, shopify_json,
                   converted_usd, firecrawl, scrapedo_rendered, page_scrape_jsonld …)
`get_real_price_coverage(days, categories)` → {category: {real, estimated,
total, real_share}} over the trailing window (single mget, fail-open).

Tests drive a fake Redis (the cache_service test pattern). Free-tier safe.
"""

import pytest

import app.services.cache_service as cs


class FakeRedis:
    """Minimal incr/expire/mget Redis double (mirrors test_tier15_hit_rate)."""

    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def expire(self, key, ttl):
        return True

    def mget(self, *keys):
        if len(keys) == 1 and isinstance(keys[0], (list, tuple)):
            keys = keys[0]
        return [self.store.get(k) for k in keys]


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cs, "redis_client", fake)
    return fake


# --- classification ------------------------------------------------------

class TestRecordPriceOutcome:
    @pytest.mark.parametrize(
        "method,bucket",
        [
            ("local_bhd", "real"),
            ("page_scrape", "real"),
            ("shopify_json", "real"),
            ("converted_usd", "real"),
            ("firecrawl", "real"),
            ("scrapedo_rendered", "real"),
            ("page_scrape_jsonld", "real"),
            ("gpt_training_estimate", "estimated"),
            ("estimated", "estimated"),
        ],
    )
    def test_classifies_source_method(self, fake_redis, method, bucket):
        cs.record_price_outcome("electronics", method)
        cov = cs.get_real_price_coverage(days=7, categories=["electronics"])
        assert cov["electronics"][bucket] == 1
        other = "estimated" if bucket == "real" else "real"
        assert cov["electronics"][other] == 0

    def test_none_or_empty_method_counts_estimated(self, fake_redis):
        """A missing source_method is conservatively 'estimated' (no real price
        was proven)."""
        cs.record_price_outcome("grocery", None)
        cs.record_price_outcome("grocery", "")
        cov = cs.get_real_price_coverage(days=7, categories=["grocery"])
        assert cov["grocery"]["estimated"] == 2
        assert cov["grocery"]["real"] == 0

    def test_real_share_computed(self, fake_redis):
        for _ in range(3):
            cs.record_price_outcome("fragrances", "shopify_json")
        cs.record_price_outcome("fragrances", "gpt_training_estimate")
        cov = cs.get_real_price_coverage(days=7, categories=["fragrances"])
        f = cov["fragrances"]
        assert f["real"] == 3
        assert f["estimated"] == 1
        assert f["total"] == 4
        assert f["real_share"] == pytest.approx(0.75)


# --- aggregation + fail-open --------------------------------------------

class TestGetRealPriceCoverage:
    def test_zeroed_block_when_redis_down(self, monkeypatch):
        monkeypatch.setattr(cs, "redis_client", None)
        cov = cs.get_real_price_coverage(days=7, categories=["electronics", "grocery"])
        assert cov["electronics"] == {"real": 0, "estimated": 0, "total": 0, "real_share": 0.0}
        assert cov["grocery"]["total"] == 0

    def test_default_categories_present(self, fake_redis):
        cov = cs.get_real_price_coverage(days=7)
        for cat in ("electronics", "grocery", "supplements", "makeup",
                    "skincare", "haircare", "fragrances", "fashion", "other"):
            assert cat in cov

    def test_record_is_fire_and_forget_no_redis(self, monkeypatch):
        """record_price_outcome must never raise when Redis is None."""
        monkeypatch.setattr(cs, "redis_client", None)
        cs.record_price_outcome("electronics", "local_bhd")  # no exception
