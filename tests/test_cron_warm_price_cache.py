"""Unit tests for the background price-cache warmer cron (Bundle B S3).

All heavy deps (gold load, comparison service, Redis) are mocked — no network,
no Serper/OpenAI, no real cache writes."""
import asyncio

import scripts.cron_warm_price_cache as warmer


class _FakeSvc:
    def __init__(self, products):
        self._products = products

    async def compare_from_text(self, query, region="bahrain", nocache=True):
        return {"products": self._products}


def _gold(n):
    return {"queries": [
        {"id": f"q{i}", "query": f"A{i} vs B{i}", "region": "bahrain"}
        for i in range(n)
    ]}


def _patch_service(monkeypatch, products):
    import app.services.structured_comparison_service as scs
    monkeypatch.setattr(scs, "get_comparison_service", lambda: _FakeSvc(products))


def test_flag_off_skips(monkeypatch):
    monkeypatch.delenv("ENABLE_PRICE_CACHE_WARMER", raising=False)
    assert asyncio.run(warmer.main()) is None


def test_flag_on_warms_and_tallies(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_CACHE_WARMER", "true")
    monkeypatch.setenv("WARMER_SUBSET", "full")
    monkeypatch.setenv("MAX_QUERIES_PER_RUN", "2")
    monkeypatch.setattr(warmer, "load_gold_truth", lambda: _gold(2))
    monkeypatch.setattr(warmer, "select_queries", lambda gold, subset=None: gold["queries"])
    monkeypatch.setattr("app.services.cache_service.redis_client", None, raising=False)
    _patch_service(monkeypatch, [
        {"name": "A", "price": {"amount": 244.99, "source_method": "page_scrape_jsonld"}},
        {"name": "B", "price": {"amount": 126.34, "source_method": "converted_usd"}},
    ])
    out = asyncio.run(warmer.main())
    assert out == {"genuine": 2, "converted": 2, "estimated": 0, "none": 0}


def test_estimated_and_none_tallied(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_CACHE_WARMER", "1")
    monkeypatch.setenv("MAX_QUERIES_PER_RUN", "1")
    monkeypatch.setattr(warmer, "load_gold_truth", lambda: _gold(1))
    monkeypatch.setattr(warmer, "select_queries", lambda gold, subset=None: gold["queries"])
    monkeypatch.setattr("app.services.cache_service.redis_client", None, raising=False)
    _patch_service(monkeypatch, [
        {"name": "A", "price": {"amount": 5.0, "source_method": "estimated"}},
        {"name": "B", "price": {"amount": None, "source_method": "validation_rejected"}},
    ])
    out = asyncio.run(warmer.main())
    assert out["estimated"] == 1 and out["none"] == 1 and out["genuine"] == 0


def test_warm_one_never_raises(monkeypatch):
    class _Boom:
        async def compare_from_text(self, *a, **k):
            raise RuntimeError("scraper pool exploded")
    import app.services.structured_comparison_service as scs
    monkeypatch.setattr(scs, "get_comparison_service", lambda: _Boom())
    # a thrown service must be swallowed into an all-zero tally, not propagate
    out = asyncio.run(warmer._warm_one({"query": "X vs Y"}))
    assert out == {"genuine": 0, "converted": 0, "estimated": 0, "none": 0}


def test_rotation_window_bounds_and_wraps(monkeypatch):
    monkeypatch.setattr("app.services.cache_service.redis_client", None, raising=False)
    queries = [{"id": str(i), "query": str(i)} for i in range(5)]
    win = warmer._rotation_window(queries, 2)
    assert len(win) == 2
    # size >= n returns the whole catalog
    assert len(warmer._rotation_window(queries, 9)) == 5
    # empty catalog is safe
    assert warmer._rotation_window([], 3) == []
