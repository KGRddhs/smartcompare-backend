"""Task A7 (genuine-price KPI wave, 2026-07-02) — ourshopee demoted to "dead".

apios.ourshopee.com has NO search-by-name route: /api/search (the adapter's
URL) plus 5 plausible variants (get_search_products / getSearchProducts /
search_product / searchProduct / getSearch) all 404 while the API family is
alive (api/product_detail?sku=PN1497 and api/getTopSelling -> 200, BHD). The
round-4 discovery crack documented only getTopSelling / getallcategoryItems /
product_detail — none searchable by name — and the Next.js App Router
storefront fetches server-side, so no client chunk carries an apios search
path to lift. Without search-by-name the adapter can never resolve an
arbitrary product; the live row only wasted a fan-out slot per
electronics/other/makeup/fashion request.

Demotion is the canonical liveness-gate write (status="dead" in
data/bh_gcc_sources.json — build_source_registry_data's idempotent merge
preserves it; _load_catalog_rows admits only "live"). The adapter + dispatch
stay in rest_json_service.py (the panda.sa precedent: dead row, code retained
for a future re-crack via browser XHR capture).

RE-PROMOTION TRAP: scripts/verify_bh_gcc_sources.py treats api-backed rows as
live off a storefront-200 (it never probes the search API), so a blind gate
re-run would resurrect this row. test_ourshopee_row_is_dead_in_data_file is
the tripwire — if it fires after a gate run, re-probe the search route before
accepting the promotion.
"""
import json

from app.services import source_router as sr


def _real_rows():
    return json.loads(sr._CATALOG_DATA_PATH.read_text(encoding="utf-8"))


def test_ourshopee_row_is_dead_in_data_file():
    row = next(r for r in _real_rows() if r.get("domain") == "ourshopee.com")
    assert row["status"] == "dead"


def test_rest_json_mechanism_not_dead_wired_by_demotion():
    # The demotion must NOT dead-wire fetch_rest_json_price: >=1 live rest_json
    # row must survive (test_live_data_file_routes_all_wired_mechanisms guards
    # the same invariant per-mechanism; this pins the ourshopee exclusion).
    live = [r["domain"] for r in _real_rows()
            if r.get("mechanism") == "rest_json" and r.get("status") == "live"]
    assert "ourshopee.com" not in live
    assert live


def test_loader_does_not_admit_ourshopee(monkeypatch):
    # Real data file + flag ON — the exact admission path the prod registry uses.
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    domains = {s.domain for s in sr._load_catalog_rows()}
    assert "ourshopee.com" not in domains


def test_selectors_never_return_ourshopee(monkeypatch):
    # Registry as prod assembles it flag-ON (literals + admitted catalog rows):
    # neither the rest_json selector (its old mechanism) nor the plain-curl
    # selector (mechanism-drift guard) may hand the cascade an ourshopee slot.
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    registry = sr._LITERAL_ROWS + sr._load_catalog_rows()
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", registry)
    for cat in ("electronics", "other", "makeup", "fashion"):
        rest = {s.domain for s in sr.get_restjson_sources_for_category(cat)}
        assert "ourshopee.com" not in rest, cat
        curl = {s.domain for s in sr.get_curl_pagescrape_sources_for_category(cat)}
        assert "ourshopee.com" not in curl, cat
