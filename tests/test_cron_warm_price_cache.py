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


# --------------------------------------------------------------------------- #
# WS4/D6 — structural warmer catalog + off-clock budget env exports            #
# --------------------------------------------------------------------------- #
def test_warmer_catalog_covers_tom_ford_pair():
    """The bundle's repro pair (Tom Ford Ombre Leather + Tobacco Vanille) must be
    in the real data/warmer_catalog.json so it warms on every run."""
    cat = warmer.load_warmer_catalog()
    assert cat, "warmer_catalog.json must load a non-empty query list"
    queries = [(q.get("query") or "") for q in cat]
    assert any(
        "Ombre Leather" in q and "Tobacco Vanille" in q for q in queries
    ), "Tom Ford Ombre Leather vs Tobacco Vanille pair missing from warmer catalog"
    # structural categories present (fragrance / haircare / gadget coverage)
    cats = {(q.get("category") or "").lower() for q in cat}
    assert "fragrances" in cats and "haircare" in cats and "electronics" in cats


def test_warmer_catalog_load_missing_file_is_safe(tmp_path):
    """A missing catalog file -> [] (warmer still runs on the gold set)."""
    assert warmer.load_warmer_catalog(tmp_path / "nope.json") == []


def test_merge_catalog_appends_and_dedups():
    gold = [
        {"query": "Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille"},
        {"query": "iPhone 15 vs Galaxy S24"},
    ]
    catalog = [
        {"query": "Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille"},  # dup
        {"query": "Olaplex No.3 vs K18 Mask"},                            # new
        {"query": ""},                                                     # skipped
    ]
    merged = warmer._merge_catalog(gold, catalog)
    qs = [m["query"].lower() for m in merged]
    # the dup appears exactly once (the gold copy), the new one appended last
    assert qs.count("tom ford ombre leather vs tom ford tobacco vanille") == 1
    assert "olaplex no.3 vs k18 mask" in qs
    assert merged[-1]["query"] == "Olaplex No.3 vs K18 Mask"
    assert len(merged) == 3


def test_warmer_exports_off_clock_render_budget():
    """The warmer module sets FAN_OUT_BUDGET_SECONDS=35 (and the render-scraper
    timeouts) at import so the off-clock render wave can finish a slow SPA."""
    import os
    assert os.environ.get("FAN_OUT_BUDGET_SECONDS") == "35"
    # setdefault — present and >= live default
    assert int(os.environ.get("FIRECRAWL_TIMEOUT", "0")) >= 30
    assert int(os.environ.get("SCRAPEDO_TIMEOUT", "0")) >= 15
    # the existing off-clock price clock is still raised
    assert os.environ.get("PRICE_RACE_TIMEOUT") == "60"


def test_main_merges_catalog_into_run(monkeypatch):
    """End-to-end (mocked service): the Tom Ford catalog pair is warmed even when
    the gold subset selection wouldn't include it."""
    monkeypatch.setenv("ENABLE_PRICE_CACHE_WARMER", "true")
    monkeypatch.setenv("WARMER_SUBSET", "smoke20")
    monkeypatch.setenv("MAX_QUERIES_PER_RUN", "50")
    # gold selection returns just one unrelated query (no Tom Ford pair)
    monkeypatch.setattr(warmer, "load_gold_truth", lambda: {"queries": []})
    monkeypatch.setattr(
        warmer, "select_queries",
        lambda gold, subset=None: [{"id": "g1", "query": "iPhone vs Galaxy"}],
    )
    monkeypatch.setattr("app.services.cache_service.redis_client", None, raising=False)

    warmed: list = []

    async def _fake_warm_one(record):
        warmed.append(record["query"])
        return {"genuine": 0, "converted": 0, "estimated": 0, "none": 0}

    monkeypatch.setattr(warmer, "_warm_one", _fake_warm_one)
    asyncio.run(warmer.main())
    assert any(
        "Ombre Leather" in q and "Tobacco Vanille" in q for q in warmed
    ), "Tom Ford catalog pair was not warmed despite the merge"
    assert "iPhone vs Galaxy" in warmed  # gold query still warmed
