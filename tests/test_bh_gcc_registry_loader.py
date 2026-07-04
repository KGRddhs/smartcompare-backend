"""BH/GCC source-build — Wave A foundation: registry loader, consolidation
normalization, genuine-method set, and the new per-mechanism selectors.

Pins the zero-regression-by-construction invariant (the loader admits ONLY
liveness-promoted rows) + the consolidation maps + the fan-out cap.
"""
import collections
import importlib
import json

import pytest

from app.services import source_router as sr
from scripts import build_source_registry_data as build


def test_live_data_file_routes_all_wired_mechanisms():
    # Verification F2 — catch DEAD-WIRING against the REAL data file. Every adapter
    # mechanism the cascade DISPATCHES must have >=1 live row, else the adapter is
    # built-but-unreachable. The cascade-wiring tests monkeypatch SYNTHETIC rows, so
    # they CANNOT catch this; this reads data/bh_gcc_sources.json directly.
    rows = json.loads(sr._CATALOG_DATA_PATH.read_text(encoding="utf-8"))
    by_mech = collections.Counter(
        r.get("mechanism") for r in rows if r.get("status") == "live"
    )
    # The 5 LIVE-WIRED new mechanisms each route to >=1 live row.
    for mech in ("woo_store_json", "salla_api", "occ_rest", "magento_graphql", "rest_json"):
        assert by_mech.get(mech, 0) >= 1, f"{mech} adapter is DEAD-WIRED (0 live rows)"
    # unbxd is intentionally NOT yet routed: extra.com (its only store) is a LITERAL,
    # and wiring it as mechanism="unbxd" would activate the path in BOTH flag states
    # (breaking the ships-dormant guarantee + introducing flag-OFF regressions). It
    # is built + tested + F1-fixed + ready; extra.com already yields genuine BHD via
    # discovery, so direct-wiring is a deferred $0 optimization. If this becomes >0,
    # update the cascade test + the handoff (the deferred-wiring case changed).
    assert by_mech.get("unbxd", 0) == 0, (
        "unbxd now has live rows — wire-in is no longer the documented deferred case"
    )


# ---------------------------------------------------------------------------
# Loader admission (verify-or-omit) — only status="live" enters the registry
# ---------------------------------------------------------------------------

def _row(**over):
    base = {
        "domain": "example-bh.com", "tier": "bahrain", "weight": 3.0,
        "categories": ["fragrances"], "mechanism": "woo_store_json",
        "is_shopify": False, "is_algolia": False, "is_render_only": False,
        "currency": "BHD", "sample_url": "https://example-bh.com/p/x",
        "priority_rank": 5, "status": "live",
    }
    base.update(over)
    return base


def test_row_to_source_admits_live():
    s = sr._row_to_source(_row(status="live"))
    assert s is not None and s.domain == "example-bh.com"
    assert s.tier == "bahrain" and s.mechanism == "woo_store_json"
    assert s.priority_rank == 5 and s.currency == "BHD"
    assert s.categories == ("fragrances",)


@pytest.mark.parametrize("status", ["provider-test-candidate", "render-only", "dead", ""])
def test_row_to_source_rejects_unpromoted(status):
    # The whole zero-regression guarantee: nothing but a live row is admitted.
    assert sr._row_to_source(_row(status=status)) is None


def test_row_to_source_rejects_malformed():
    assert sr._row_to_source({"status": "live"}) is None          # no domain
    assert sr._row_to_source(_row(tier="planet-mars")) is None     # bad tier
    assert sr._row_to_source("not-a-dict") is None
    assert sr._row_to_source(_row(categories="fragrances")) is None  # str not list


def test_flag_off_ships_dormant(monkeypatch, tmp_path):
    # The activation flag default-OFF → ZERO catalog rows even if the file has
    # live rows (the build ships dormant; registry == literals).
    import json
    monkeypatch.delenv("ENABLE_BH_GCC_CATALOG_SOURCES", raising=False)
    f = tmp_path / "bh_gcc_sources.json"
    f.write_text(json.dumps([_row(status="live")]), encoding="utf-8")
    monkeypatch.setattr(sr, "_CATALOG_DATA_PATH", f)
    assert sr._load_catalog_rows() == []  # flag OFF → nothing loads


def test_flag_on_admits_live(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    f = tmp_path / "bh_gcc_sources.json"
    f.write_text(json.dumps([_row(domain="flagged-bh.com", status="live")]), encoding="utf-8")
    monkeypatch.setattr(sr, "_CATALOG_DATA_PATH", f)
    assert {s.domain for s in sr._load_catalog_rows()} == {"flagged-bh.com"}


def test_registry_is_literals_when_no_live_rows(monkeypatch, tmp_path):
    # With the flag ON, a file where every row is unpromoted still admits ZERO.
    import json
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    data = [_row(status="provider-test-candidate"), _row(domain="x.com", status="render-only")]
    f = tmp_path / "bh_gcc_sources.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(sr, "_CATALOG_DATA_PATH", f)
    assert sr._load_catalog_rows() == []  # zero admitted → registry == literals


def test_loader_dedups_against_literals(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    # nasserpharmacy.com is a literal — a live catalog dup must be skipped.
    data = [_row(domain="nasserpharmacy.com", status="live"),
            _row(domain="fresh-new-bh.com", status="live")]
    f = tmp_path / "bh_gcc_sources.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(sr, "_CATALOG_DATA_PATH", f)
    loaded = {s.domain for s in sr._load_catalog_rows()}
    assert "nasserpharmacy.com" not in loaded
    assert "fresh-new-bh.com" in loaded


def test_loader_failopen_on_missing_file(monkeypatch):
    from pathlib import Path
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    monkeypatch.setattr(sr, "_CATALOG_DATA_PATH", Path("/no/such/file__.json"))
    assert sr._load_catalog_rows() == []  # never raises


# ---------------------------------------------------------------------------
# Consolidation normalization (mechanism / tier / category maps)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("adapter,cat_mech,want_mech,want_method", [
    ("fetch_woocommerce_store_api_price", "json_api", "woo_store_json", "woo_store_api"),
    ("fetch_salla_api_price", "json_api", "salla_api", "salla_api"),
    ("fetch_occ_rest_price", "json_api", "occ_rest", "occ_rest_bhd"),
    ("fetch_alshaya_graphql_price", "json_api", "magento_graphql", "magento_graphql_bhd"),
    ("fetch_magento_graphql_price", "json_api", "magento_graphql", "magento_graphql_bhd"),
    ("fetch_rest_json_price", "json_api", "rest_json", "rest_json_bhd"),
    ("fetch_shopify_price (is_shopify=True)", "shopify_products_json", "shopify", "shopify_json"),
    ("fetch_algolia_price", "algolia", "algolia", "local_bhd"),
    ("fetch_page_price", "curl_jsonld", "", "page_scrape_jsonld"),   # plain drop-in
    ("render tier Firecrawl", "render_required", "render", ""),
])
def test_mechanism_map(adapter, cat_mech, want_mech, want_method):
    mf = build._mechanism_and_flags({"integration_adapter": adapter, "mechanism": cat_mech})
    assert mf["mechanism"] == want_mech
    assert mf["genuine_method"] == want_method
    if want_mech == "shopify":
        assert mf["is_shopify"] is True
    if want_mech == "algolia":
        assert mf["is_algolia"] is True
    if want_mech == "render":
        assert mf["is_render_only"] is True


@pytest.mark.parametrize("currency,country,tier,weight", [
    ("BHD", "BH", "bahrain", 3.0),
    ("BHD", "KSA", "bahrain", 3.0),   # BHD currency wins regardless of country
    ("SAR", "KSA", "gcc", 1.5),
    ("AED", "UAE", "gcc", 1.5),
    ("USD", "", "gcc", 1.5),          # never global (would downgrade genuine)
])
def test_tier_weight(currency, country, tier, weight):
    assert build._tier_weight(currency, country) == (tier, weight)


def test_category_canon():
    assert build._canon_categories(["beauty"]) == ["makeup", "skincare"]
    assert build._canon_categories(["sports-nutrition", "vitamins"]) == ["supplements"]
    assert build._canon_categories(["oud", "perfume", "fragrances"]) == ["fragrances"]
    assert build._canon_categories(["mobiles", "laptops"]) == ["electronics"]
    assert build._canon_categories(["jewelry", "footwear"]) == ["fashion"]
    assert build._canon_categories(["totally-unknown-token"]) == []  # dropped


def test_consolidation_runs_and_dedups_literals():
    rows = build.consolidate()
    assert len(rows) > 200  # ~370 after dedup
    domains = {r["domain"] for r in rows}
    # literal-overlap excluded
    assert "nasserpharmacy.com" not in domains
    assert "bn.boots.com" not in domains
    assert "noon.com" not in domains
    # every row defaults to NOT-live (only the gate promotes)
    assert all(r["status"] in ("provider-test-candidate", "render-only") for r in rows)
    # no row mapped to global tier
    assert all(r["tier"] in ("bahrain", "gcc") for r in rows)


# ---------------------------------------------------------------------------
# New per-mechanism selectors + fan-out cap
# ---------------------------------------------------------------------------

def _mk(domain, mechanism, tier="bahrain", cats=("fragrances",), prank=100):
    return sr.Source(domain, tier, cats, 3.0 if tier == "bahrain" else 1.5,
                     mechanism=mechanism, priority_rank=prank, status="live")


def test_selectors_filter_by_mechanism_and_span_both_tiers(monkeypatch):
    rows = [
        _mk("bh-woo.com", "woo_store_json", "bahrain"),
        _mk("ksa-woo.com", "woo_store_json", "gcc"),
        _mk("bh-salla.com", "salla_api", "bahrain"),
        _mk("global-x.com", "woo_store_json", "global"),  # must be excluded
    ]
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", rows)
    woo = [s.domain for s in sr.get_woo_sources_for_category("fragrances")]
    assert woo == ["bh-woo.com", "ksa-woo.com"]   # bahrain before gcc, global excluded
    salla = [s.domain for s in sr.get_salla_sources_for_category("fragrances")]
    assert salla == ["bh-salla.com"]


def test_fanout_cap_and_priority_order(monkeypatch):
    # 10 bahrain woo rows; cap K=3 keeps the 3 lowest priority_rank.
    rows = [_mk(f"woo{i}.com", "woo_store_json", "bahrain", prank=10 - i) for i in range(10)]
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", rows)
    monkeypatch.setenv("BH_GCC_FANOUT_K", "3")
    got = [s.domain for s in sr.get_woo_sources_for_category("fragrances")]
    assert len(got) == 3
    # lowest priority_rank first (woo9=rank1, woo8=rank2, woo7=rank3)
    assert got == ["woo9.com", "woo8.com", "woo7.com"]


def test_category_filter(monkeypatch):
    rows = [_mk("a.com", "salla_api", cats=("supplements",)),
            _mk("b.com", "salla_api", cats=("fragrances",))]
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", rows)
    assert [s.domain for s in sr.get_salla_sources_for_category("fragrances")] == ["b.com"]


# ---------------------------------------------------------------------------
# Wave B2 (recon_fashion rank-5) — sample_url must be liveness-probe fetchable
# ---------------------------------------------------------------------------
# Round-3 magento/rest_json catalog rows carried pseudo-annotated sample_pdp_urls
# ("https://host/en/ (price via GraphQL by phrase/sku)") that verify_bh_gcc_sources
# can NEVER fetch — the rows false-dead forever (the footlocker built-but-dead
# class). The generator sanitizes to the leading http(s) token; the real data
# file must carry only fetchable-shaped URLs (or "").

def test_clean_sample_url_strips_pseudo_annotation():
    clean = build._clean_sample_url
    assert clean(
        "https://www.footlocker.com.bh/en/ (price via GraphQL by phrase/sku)"
    ) == "https://www.footlocker.com.bh/en/"
    assert clean("https://www.panda.sa/en (product via API id/sku)") == \
        "https://www.panda.sa/en"
    # untouched: already-clean URLs
    assert clean("https://x.bh/p/1") == "https://x.bh/p/1"
    # non-URL pseudo strings / empties → "" (probe reports "no sample_url",
    # never burns a fetch on garbage)
    assert clean("price via GraphQL by phrase/sku") == ""
    assert clean("") == ""
    assert clean(None) == ""


def test_real_file_sample_urls_are_fetchable_shaped():
    rows = json.loads(sr._CATALOG_DATA_PATH.read_text(encoding="utf-8"))
    bad = [
        r["domain"] for r in rows
        if r.get("sample_url")
        and (" " in r["sample_url"] or not r["sample_url"].startswith("http"))
    ]
    assert bad == [], f"unfetchable pseudo sample_urls: {bad}"
