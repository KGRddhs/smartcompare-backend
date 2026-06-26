#!/usr/bin/env python3
"""Consolidate the 4 BH/GCC discovery catalogs into ONE normalized registry data
file (data/bh_gcc_sources.json) that app/services/source_router._load_catalog_rows
reads.

BH/GCC source-build (2026-06-25). The 4 discovery catalogs
(data/bh_gcc_source_candidates{,_round2,_round3,_round4}.json) are the IMMUTABLE
provenance — this script never writes them back. It maps each catalog row to the
FINAL Source field values (tier/weight/categories/mechanism/flags/currency/
sample_url/priority_rank/status), dedups (against the registry literals AND across
rounds), and writes the consolidated list.

STATUS: every row defaults to "provider-test-candidate" (NOT live) → the loader
admits ZERO rows until scripts/verify_source_registry.py promotes them to "live".
IDEMPOTENT: re-running MERGES by domain, preserving any status already written by
the liveness gate (a verdict is never clobbered).

Usage:  python -m scripts.build_source_registry_data
        python -m scripts.build_source_registry_data --stats   (print distribution, no write)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
_CATALOGS = [
    _DATA / "bh_gcc_source_candidates.json",
    _DATA / "bh_gcc_source_candidates_round2.json",
    _DATA / "bh_gcc_source_candidates_round3.json",
    _DATA / "bh_gcc_source_candidates_round4.json",
]
_OUT = _DATA / "bh_gcc_sources.json"

# --- Canonical categories -------------------------------------------------
_CANON = {
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
}
# Catalog token -> one OR more canonical categories. Unknown tokens are dropped.
_CATEGORY_MAP: Dict[str, tuple] = {
    # pass-through canonicals
    **{c: (c,) for c in _CANON},
    # fragrance family
    "perfume": ("fragrances",), "perfumes": ("fragrances",), "oud": ("fragrances",),
    "incense": ("fragrances",), "bukhoor": ("fragrances",), "bakhoor": ("fragrances",),
    "designer-fragrance": ("fragrances",), "hair-mist": ("fragrances",),
    "gift-sets": ("fragrances",),
    # beauty splits into makeup+skincare
    "beauty": ("makeup", "skincare"),
    # supplements / health / sports
    "sports-nutrition": ("supplements",), "sports": ("supplements",),
    "health": ("supplements",), "pharmacy": ("supplements", "skincare"),
    "vitamins": ("supplements",),
    # electronics family
    "mobiles": ("electronics",), "mobile": ("electronics",),
    "mobile-accessories": ("electronics",), "laptops": ("electronics",),
    "appliances": ("electronics",), "home-appliances": ("electronics",),
    "gaming": ("electronics",), "gaming-pc": ("electronics",), "gadgets": ("electronics",),
    "computing": ("electronics",), "printers": ("electronics",), "components": ("electronics",),
    "headphones": ("electronics",), "watches": ("electronics",), "accessories": ("electronics",),
    # fashion family
    "jewelry": ("fashion",), "jewellery": ("fashion",), "eyewear": ("fashion",),
    "footwear": ("fashion",), "apparel": ("fashion",),
    # grocery family
    "food": ("grocery",), "fresh": ("grocery",), "fmcg": ("grocery",),
    "dairy": ("grocery",), "supermarket": ("grocery",), "household": ("grocery",),
    "saffron": ("grocery",),
    # other / out-of-taxonomy
    "home": ("other",), "baby": ("other",), "kids": ("other",), "toys": ("other",),
    "books": ("other",), "stationery": ("other",), "general": ("other",),
    "maker": ("other",), "general-merchandise": ("other",), "pet": ("other",),
    "pets": ("other",),
}

# --- Mechanism / tier -----------------------------------------------------
_BH_CURRENCY = {"BHD"}
_GCC_COUNTRIES = {"KSA", "SA", "UAE", "AE", "KW", "QA", "OM"}
_GCC_CURRENCIES = {"SAR", "AED", "KWD", "QAR", "OMR", "USD"}
# Verification F6 — price AGGREGATORS (not single-retailer PDPs): a multi-currency
# meta-search whose "price" is a cross-store min, not a genuine shelf price. Skip
# them entirely (they would mis-rank + never yield a clean genuine BH price).
_AGGREGATOR_DOMAINS = {"pricena.com", "kanbkam.com"}


def _adapter_token(integration_adapter: str) -> str:
    """First fetch_* token of the catalog's integration_adapter, lower."""
    s = (integration_adapter or "").replace("NEW:", "").strip()
    for tok in s.replace("(", " ").replace(")", " ").split():
        t = tok.strip().lower()
        if t.startswith("fetch_") or t in ("sitemap", "render", "firecrawl", "cron_index_sitemaps", "algolia_service"):
            return t
    return s.split("(")[0].strip().lower()


def _mechanism_and_flags(row: dict) -> Optional[dict]:
    """Map a catalog row -> {mechanism, is_shopify, is_algolia, is_render_only,
    genuine_method}. Returns None for rows that should be skipped entirely (e.g.
    nasser/boutiqaat literals are deduped later, but their mechanism still maps).

    The integration_adapter token is the PRIMARY signal; catalog `mechanism` is
    secondary. Drop-in curl/sitemap/next_data rows map to mechanism="" (plain
    registry rows that ride the EXISTING Serper-discovery + fetch_page_price /
    fetch_shopify_price paths — no direct selector, no per-domain fetcher needed).
    """
    cat_mech = str(row.get("mechanism") or "").lower()
    adapter = _adapter_token(row.get("integration_adapter", ""))

    # Render-tier — loaded inert (is_render_only), never flipped live this build.
    if cat_mech == "render_required" or adapter in ("render", "firecrawl"):
        return {"mechanism": "render", "is_shopify": False, "is_algolia": False,
                "is_render_only": True, "genuine_method": ""}

    # Shopify drop-in (existing fetch_shopify_price /products.json).
    if cat_mech == "shopify_products_json" or adapter == "fetch_shopify_price":
        return {"mechanism": "shopify", "is_shopify": True, "is_algolia": False,
                "is_render_only": False, "genuine_method": "shopify_json"}

    # Algolia (explicit-key path; is_algolia flag).
    if cat_mech == "algolia" or adapter in ("fetch_algolia_price", "algolia_service"):
        return {"mechanism": "algolia", "is_shopify": False, "is_algolia": True,
                "is_render_only": False, "genuine_method": "local_bhd"}

    # NEW direct-fetch adapters (json_api mechanism, disambiguated by adapter).
    if adapter == "fetch_woocommerce_store_api_price":
        return {"mechanism": "woo_store_json", "is_shopify": False, "is_algolia": False,
                "is_render_only": False, "genuine_method": "woo_store_api"}
    if adapter == "fetch_salla_api_price":
        return {"mechanism": "salla_api", "is_shopify": False, "is_algolia": False,
                "is_render_only": False, "genuine_method": "salla_api"}
    if adapter == "fetch_occ_rest_price":
        return {"mechanism": "occ_rest", "is_shopify": False, "is_algolia": False,
                "is_render_only": False, "genuine_method": "occ_rest_bhd"}
    if adapter in ("fetch_alshaya_graphql_price", "fetch_magento_graphql_price"):
        return {"mechanism": "magento_graphql", "is_shopify": False, "is_algolia": False,
                "is_render_only": False, "genuine_method": "magento_graphql_bhd"}
    if adapter == "fetch_rest_json_price":
        return {"mechanism": "rest_json", "is_shopify": False, "is_algolia": False,
                "is_render_only": False, "genuine_method": "rest_json_bhd"}

    # nasser literal (already in registry — deduped) but if present map to json_api.
    if adapter == "fetch_nasser_price":
        return {"mechanism": "json_api", "is_shopify": False, "is_algolia": False,
                "is_render_only": False, "genuine_method": "local_bhd"}

    # Everything else — plain curl/sitemap/next_data drop-in (rides Serper
    # discovery + fetch_page_price; genuine BHD stamps page_scrape_jsonld).
    return {"mechanism": "", "is_shopify": False, "is_algolia": False,
            "is_render_only": False, "genuine_method": "page_scrape_jsonld"}


def _tier_weight(currency: str, country: str) -> tuple:
    cur = (currency or "").upper().strip()
    ctry = (country or "").upper().strip()
    # Verification F6 — BAHRAIN tier (3.0, authoritative) ONLY for a genuine BHD
    # source: a BHD-currency store, OR a BH-country store whose currency is
    # unknown/blank. A BH-country row carrying an EXPLICIT foreign currency
    # (USD/AED/SAR/QAR — country merely defaulted to BH in R1) must NOT get the 3.0
    # authoritativeness weight (it over-ranks a true BH source in cross-validation);
    # it is a gcc/converted source.
    if cur == "BHD":
        return "bahrain", 3.0
    if (ctry == "BH" or ctry == "BAHRAIN") and not cur:
        return "bahrain", 3.0
    if ctry in _GCC_COUNTRIES or cur in _GCC_CURRENCIES:
        return "gcc", 1.5
    # Unknown — default to gcc (NEVER global: _is_genuine_bh_candidate downgrades
    # a global-tier domain's genuine scrape to converted).
    return "gcc", 1.5


def _canon_categories(cats) -> List[str]:
    if not isinstance(cats, list):
        return []
    out: List[str] = []
    for c in cats:
        for mapped in _CATEGORY_MAP.get(str(c).lower().strip(), ()):  # drop unknown
            if mapped not in out:
                out.append(mapped)
    return out


def _norm_domain(domain: str) -> str:
    return (domain or "").replace("https://", "").replace("http://", "").split("/")[0]\
        .replace("www.", "").strip().lower()


def _literal_domains() -> set:
    """Apex domains of the registry literals (so the consolidation excludes
    overlap up front — the loader dedups again as a backstop)."""
    try:
        from app.services.source_router import _LITERAL_ROWS
        return {s.domain.replace("www.", "").lower() for s in _LITERAL_ROWS}
    except Exception:  # noqa: BLE001
        return set()


def consolidate() -> List[dict]:
    literal_domains = _literal_domains()
    by_domain: Dict[str, dict] = {}
    for cat_path in _CATALOGS:
        try:
            rows = json.loads(cat_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: could not read {cat_path.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(rows, list):
            rows = list(rows.values())[0] if isinstance(rows, dict) else []
        for row in rows:
            domain = _norm_domain(row.get("domain", ""))
            if not domain:
                continue
            # F6 — skip price aggregators (not retailer PDPs).
            if domain in _AGGREGATOR_DOMAINS:
                continue
            # Dedup against literals (suffix-aware) + across rounds (first wins).
            if any(domain == ld or domain.endswith("." + ld) for ld in literal_domains):
                continue
            if domain in by_domain:
                continue
            mf = _mechanism_and_flags(row)
            if mf is None:
                continue
            tier, weight = _tier_weight(row.get("currency", ""), row.get("country", "BH"))
            # is_shopify is a BAHRAIN-only direct-fetch lever (get_shopify_sources_
            # for_category filters tier=="bahrain"; the invariant "every is_shopify
            # row is bahrain-tier" is pinned by test_source_router_shopify_l13). A
            # GCC Shopify store is never shopify-direct-fetched, so demote it to a
            # PLAIN discovery row (rides Serper site: + fetch_page_price) — keeps the
            # invariant + still contributes the source.
            if mf["is_shopify"] and tier != "bahrain":
                mf = {
                    "mechanism": "", "is_shopify": False, "is_algolia": False,
                    "is_render_only": False, "genuine_method": "page_scrape_jsonld",
                }
            try:
                prank = int(row.get("priority_rank", 100))
            except (TypeError, ValueError):
                prank = 100
            status = "render-only" if mf["is_render_only"] else "provider-test-candidate"
            by_domain[domain] = {
                "domain": domain,
                "tier": tier,
                "weight": weight,
                "categories": _canon_categories(row.get("categories")),
                "mechanism": mf["mechanism"],
                "is_shopify": mf["is_shopify"],
                "is_algolia": mf["is_algolia"],
                "is_render_only": mf["is_render_only"],
                "currency": (row.get("currency") or "").upper().strip(),
                "country": (row.get("country") or "BH").upper().strip(),
                "genuine_method": mf["genuine_method"],
                "sample_url": row.get("sample_pdp_url") or row.get("sample_url") or "",
                "priority_rank": prank,
                "status": status,
            }
    return sorted(by_domain.values(), key=lambda r: (r["tier"], r["priority_rank"], r["domain"]))


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    rows = consolidate()

    # IDEMPOTENT MERGE — preserve any liveness status already written.
    if _OUT.exists():
        try:
            prior = {r["domain"]: r for r in json.loads(_OUT.read_text(encoding="utf-8"))}
        except Exception:  # noqa: BLE001
            prior = {}
        for r in rows:
            p = prior.get(r["domain"])
            if p and p.get("status") in ("live", "render-only", "dead"):
                r["status"] = p["status"]

    if "--stats" in argv:
        import collections
        print(f"consolidated rows: {len(rows)}")
        print("by tier:", dict(collections.Counter(r["tier"] for r in rows)))
        print("by mechanism:", dict(collections.Counter(r["mechanism"] or "(plain)" for r in rows)))
        print("by status:", dict(collections.Counter(r["status"] for r in rows)))
        print("BHD genuine candidates:", sum(1 for r in rows if r["currency"] == "BHD" and not r["is_render_only"]))
        return 0

    _OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(rows)} rows -> {_OUT.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
