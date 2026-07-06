"""Launch coverage fix (2026-07-06) — orphaned Shopify-shaped catalog rows.

~40 gcc catalog rows (rasasistore.com / sa.ajmal.com / swissarabian.com / … —
the local GCC perfume houses) are Shopify stores the build classifier left with a
BLANK mechanism (page_scrape_jsonld, is_shopify=False), so NO direct-fetch
selector reached them and their only consumer was the slow Serper `site:`
discovery — the "Ajmal Aristocrat vs Rasasi Hawas" dead-end. Their liveness
anchor `sample_url` IS the store's /products.json endpoint, so
get_gcc_shopify_pagescrape_sources_for_category selects exactly them (already
live-verified for the Shopify mechanism) and routes them through
fetch_shopify_price ($0 / Serper-free; gcc → converted_usd, currency-honest).

These pin the SELECTOR contract (the wiring into _new_adapter_specs +
_consume_adapter_prefetch reuses the existing shared machinery unchanged) and the
flag-OFF byte-identity guarantee.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services import source_router
from app.services.source_router import (
    Source,
    get_gcc_shopify_pagescrape_sources_for_category,
    get_curl_pagescrape_sources_for_category,
    _fanout_k,
)


def _src(domain, tier="gcc", cats=("fragrances",), **kw):
    """Build a Source with the given kwargs; `mechanism` defaults to '' (blank)."""
    weight = kw.pop("weight", 1.5)
    return Source(domain, tier, tuple(cats), weight, **kw)


class TestShopifyGccSelector:
    def test_matches_only_products_json_blank_rows(self, monkeypatch):
        reg = [
            _src("rasasistore.com", sample_url="https://rasasistore.com/products.json",
                 priority_rank=62, currency="AED"),
            _src("swissarabian.com", sample_url="https://swissarabian.com/products.json",
                 priority_rank=64, currency="USD"),
            # PDP-only blank row -> NOT a /products.json anchor -> excluded (a bare
            # apex has no domain->price path, so firing shopify at it is wasteful).
            _src("pdponly.com", sample_url="https://pdponly.com/products/slug", priority_rank=10),
            # literal-like row (no sample_url) -> excluded.
            _src("lit.com", tier="bahrain", cats=(), sample_url=""),
        ]
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", reg)
        got = [s.domain for s in get_gcc_shopify_pagescrape_sources_for_category("fragrances")]
        assert got == ["rasasistore.com", "swissarabian.com"]  # priority_rank order

    def test_excludes_shopify_algolia_mechanism_tier_category(self, monkeypatch):
        reg = [
            _src("shop.com", is_shopify=True, sample_url="https://shop.com/products.json"),
            _src("alg.com", is_algolia=True, sample_url="https://alg.com/products.json"),
            _src("glob.com", tier="global", sample_url="https://glob.com/products.json"),
            _src("woo.com", mechanism="woo_store_json", sample_url="https://woo.com/products.json"),
            _src("elec.com", cats=("electronics",), sample_url="https://elec.com/products.json"),
        ]
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", reg)
        assert get_gcc_shopify_pagescrape_sources_for_category("fragrances") == []

    def test_bahrain_ordered_before_gcc_then_priority(self, monkeypatch):
        reg = [
            _src("gcc-a.com", tier="gcc", sample_url="https://gcc-a.com/products.json", priority_rank=5),
            _src("bh-b.com", tier="bahrain", sample_url="https://bh-b.com/products.json", priority_rank=99),
        ]
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", reg)
        got = [s.domain for s in get_gcc_shopify_pagescrape_sources_for_category("fragrances")]
        assert got == ["bh-b.com", "gcc-a.com"]  # bahrain first despite larger rank

    def test_k_capped(self, monkeypatch):
        reg = [
            _src(f"s{i}.com", sample_url=f"https://s{i}.com/products.json", priority_rank=i)
            for i in range(20)
        ]
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", reg)
        got = get_gcc_shopify_pagescrape_sources_for_category("fragrances")
        assert len(got) == _fanout_k()

    def test_empty_categories_matches_all(self, monkeypatch):
        reg = [_src("all.com", cats=(), sample_url="https://all.com/products.json")]
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", reg)
        got = [s.domain for s in get_gcc_shopify_pagescrape_sources_for_category("fragrances")]
        assert got == ["all.com"]


class TestFlagOffByteIdentity:
    def test_no_literal_row_carries_products_json_anchor(self):
        """The flag-OFF byte-identity guarantee: SOURCE_REGISTRY == _LITERAL_ROWS,
        and the selector matches ONLY rows with a /products.json sample_url — no
        literal carries one, so the selector returns [] until the catalog loads."""
        for s in source_router._LITERAL_ROWS:
            assert "/products.json" not in (s.sample_url or ""), s.domain

    def test_selector_empty_against_literals_only_registry(self, monkeypatch):
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", source_router._LITERAL_ROWS)
        for cat in ("fragrances", "skincare", "makeup", "supplements", "other"):
            assert get_gcc_shopify_pagescrape_sources_for_category(cat) == []


class TestSupplementsSelectorUnchanged:
    def test_curl_pagescrape_still_bahrain_only(self, monkeypatch):
        """The pre-existing supplements curl-pagescrape selector stays bahrain-only
        (the new selector is additive, not a replacement) — a gcc blank row is NOT
        admitted by it."""
        reg = [
            _src("bh-supp.com", tier="bahrain", cats=("supplements",),
                 sample_url="https://bh-supp.com/product/x"),
            _src("gcc-supp.com", tier="gcc", cats=("supplements",),
                 sample_url="https://gcc-supp.com/products.json"),
        ]
        monkeypatch.setattr(source_router, "SOURCE_REGISTRY", reg)
        got = [s.domain for s in get_curl_pagescrape_sources_for_category("supplements")]
        assert got == ["bh-supp.com"]


class TestCatalogDataContract:
    """Pin the real data-file expectation the wiring relies on: the failing
    pair's houses are present as blank-mechanism /products.json rows."""

    def test_failing_pair_houses_are_products_json_rows(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "data" / "bh_gcc_sources.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        by_domain = {r.get("domain"): r for r in rows}
        for dom in ("rasasistore.com", "sa.ajmal.com", "swissarabian.com"):
            r = by_domain.get(dom)
            assert r is not None, f"{dom} missing from catalog"
            assert (r.get("mechanism") or "") == "", f"{dom} not blank-mechanism"
            assert not r.get("is_shopify"), f"{dom} unexpectedly is_shopify"
            assert "/products.json" in (r.get("sample_url") or ""), f"{dom} not a /products.json anchor"
            assert "fragrances" in (r.get("categories") or []), f"{dom} not a fragrance row"
