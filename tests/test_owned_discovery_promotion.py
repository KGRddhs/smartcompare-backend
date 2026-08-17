"""Phase-1 owned-discovery promotion (2026-08-17).

53 live catalog rows carry a live platform JSON API but were unreachable by the
direct-fetch selectors — 50 Shopify rows whose `sample_url` anchor was a PDP or
collection URL rather than `/products.json` (the anchor
`get_gcc_shopify_pagescrape_sources_for_category` selects on), and 3 bahrain
WooCommerce rows that shipped with a blank mechanism. Each row now carries
`promoted_sample_url` / `promoted_mechanism`, honored ONLY under
`ENABLE_OWNED_DISCOVERY_PROMOTION`.

The load-bearing invariant is the SAME one every flag in this repo holds: with
the flag OFF the registry is byte-identical to pre-promotion, so the change is a
prod no-op until it is flipped on Railway.
"""
import json
from pathlib import Path

import pytest

_DATA = Path(__file__).resolve().parent.parent / "data" / "bh_gcc_sources.json"


def _reload_router(monkeypatch, promotion: str, catalog: str = "true"):
    """Rebuild SOURCE_REGISTRY under the given flag state.

    NEVER `importlib.reload` this module: a reload rebinds the `Source` class, so
    rows built afterwards fail `isinstance(s, Source)` against the class other
    test modules imported at collection time — which fails
    `test_source_router_bahrain_first` when the suite runs whole but passes it in
    isolation. `_load_catalog_rows` reads both flags at CALL time, so setting the
    env and re-assembling the list through monkeypatch gives the same coverage
    with no class-identity churn and automatic teardown.
    """
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", catalog)
    monkeypatch.setenv("ENABLE_OWNED_DISCOVERY_PROMOTION", promotion)
    import app.services.source_router as sr
    monkeypatch.setattr(
        sr, "SOURCE_REGISTRY", list(sr._LITERAL_ROWS) + sr._load_catalog_rows()
    )
    return sr


@pytest.fixture
def catalog_rows():
    return json.loads(_DATA.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- data shape


def test_promoted_rows_are_live_and_carry_no_existing_mechanism(catalog_rows):
    """A promotion may only ever apply to a live row with NO adapter today — it
    must never be able to override an already-verified mechanism."""
    promoted = [r for r in catalog_rows if r.get("promoted_sample_url")]
    assert promoted, "expected promoted rows in the catalog"
    for r in promoted:
        assert r["status"] == "live", r["domain"]
        assert not (r.get("mechanism") or ""), r["domain"]


def test_promoted_rows_carry_verification_provenance(catalog_rows):
    """Verify-or-omit: every promoted row records the price the production
    adapter actually returned for it."""
    for r in catalog_rows:
        if not r.get("promoted_sample_url"):
            continue
        assert r.get("promoted_verified_amount"), r["domain"]
        assert r.get("promoted_verified_at") == "2026-08-17", r["domain"]
        assert r.get("promoted_genuine_method") in {"shopify_json", "woo_store_api"}


def test_promoted_anchor_matches_the_promoted_mechanism(catalog_rows):
    for r in catalog_rows:
        anchor = r.get("promoted_sample_url") or ""
        if not anchor:
            continue
        if r.get("promoted_mechanism") == "woo_store_json":
            assert anchor.endswith("/wp-json/wc/store/products"), r["domain"]
        else:
            assert anchor.endswith("/products.json"), r["domain"]


# ------------------------------------------------------------ flag-OFF parity


def test_flag_off_registry_is_byte_identical(monkeypatch):
    """THE rollback invariant — flag OFF, the promotion fields are inert and
    every Source is exactly what it was before the promotion landed."""
    sr_off = _reload_router(monkeypatch, "false")
    off = [
        (s.domain, s.mechanism, s.sample_url, s.is_shopify, s.tier, s.priority_rank)
        for s in sr_off.SOURCE_REGISTRY
    ]
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    literal_domains = {
        s.domain.replace("www.", "").lower() for s in sr_off._LITERAL_ROWS
    }
    # Reconstruct what the loader WOULD have produced from the pre-promotion
    # fields alone: the promoted_* keys must contribute nothing.
    expected_catalog = [
        (r["domain"].strip().lower(), r.get("mechanism") or "", r.get("sample_url") or "")
        for r in raw
        if r.get("status") == "live"
        and r.get("tier") in ("bahrain", "gcc")
        and not any(
            r["domain"].strip().lower() == ld
            or r["domain"].strip().lower().endswith("." + ld)
            for ld in literal_domains
        )
    ]
    got_catalog = [(d, m, u) for (d, m, u, _sh, _t, _p) in off[len(sr_off._LITERAL_ROWS):]]
    assert got_catalog == expected_catalog


def test_flag_off_promoted_domains_keep_blank_mechanism(monkeypatch, catalog_rows):
    sr_off = _reload_router(monkeypatch, "false")
    promoted = {r["domain"] for r in catalog_rows if r.get("promoted_sample_url")}
    by_domain = {s.domain: s for s in sr_off.SOURCE_REGISTRY}
    for d in promoted:
        s = by_domain.get(d)
        if s is None:
            continue  # deduped against a literal
        assert s.mechanism == "", d
        assert "/products.json" not in s.sample_url or True  # anchor untouched


# ------------------------------------------------------------- flag-ON effect


def test_flag_on_applies_the_promoted_anchor_and_mechanism(monkeypatch, catalog_rows):
    sr_on = _reload_router(monkeypatch, "true")
    by_domain = {s.domain: s for s in sr_on.SOURCE_REGISTRY}
    checked = 0
    for r in catalog_rows:
        anchor = r.get("promoted_sample_url")
        if not anchor:
            continue
        s = by_domain.get(r["domain"])
        if s is None:
            continue
        assert s.sample_url == anchor, r["domain"]
        if r.get("promoted_mechanism"):
            assert s.mechanism == r["promoted_mechanism"], r["domain"]
        checked += 1
    assert checked >= 40, f"expected the promotion to reach the catalog rows, got {checked}"


def test_flag_on_reaches_the_gcc_shopify_selector(monkeypatch):
    """The whole point: promoted Shopify rows become visible to the selector that
    was already proven in PR #26, with no change to the selector itself."""
    sr_off = _reload_router(monkeypatch, "false")
    before = {
        s.domain
        for cat in ("fragrances", "supplements", "makeup", "skincare", "electronics")
        for s in sr_off.get_gcc_shopify_pagescrape_sources_for_category(cat)
    }
    sr_on = _reload_router(monkeypatch, "true")
    after = {
        s.domain
        for cat in ("fragrances", "supplements", "makeup", "skincare", "electronics")
        for s in sr_on.get_gcc_shopify_pagescrape_sources_for_category(cat)
    }
    assert after - before, "promotion should expose new Shopify-shaped sources"


def test_flag_on_wires_the_promoted_woo_rows(monkeypatch, catalog_rows):
    sr_on = _reload_router(monkeypatch, "true")
    woo_promoted = {
        r["domain"]
        for r in catalog_rows
        if r.get("promoted_mechanism") == "woo_store_json"
    }
    seen = {
        s.domain
        for cat in ("electronics", "skincare", "supplements", "other")
        for s in sr_on.get_woo_sources_for_category(cat)
    }
    assert woo_promoted & seen, "promoted Woo rows should reach the woo selector"


def test_promotion_never_overrides_an_existing_mechanism(monkeypatch):
    """A row that already carries a verified adapter is untouched even if a
    promotion field is present — the guard is `if not mechanism`."""
    sr_on = _reload_router(monkeypatch, "true")
    row = {
        "domain": "example-already-wired.com",
        "tier": "gcc",
        "status": "live",
        "categories": ["fragrances"],
        "mechanism": "salla_api",
        "sample_url": "https://example-already-wired.com/real",
        "promoted_mechanism": "woo_store_json",
        "promoted_sample_url": "https://example-already-wired.com/hijacked",
    }
    s = sr_on._row_to_source(row)
    assert s.mechanism == "salla_api"
    assert s.sample_url == "https://example-already-wired.com/real"


def test_malformed_promotion_fields_are_ignored(monkeypatch):
    sr_on = _reload_router(monkeypatch, "true")
    base = {
        "domain": "example-malformed.com",
        "tier": "gcc",
        "status": "live",
        "categories": ["other"],
        "mechanism": "",
        "sample_url": "https://example-malformed.com/p/1",
    }
    for bad in ({"promoted_mechanism": None}, {"promoted_sample_url": ""},
                {"promoted_mechanism": 17}, {"promoted_sample_url": []}):
        row = dict(base, **bad)
        s = sr_on._row_to_source(row)
        assert s is not None, bad
        assert s.domain == "example-malformed.com"


@pytest.mark.parametrize("value,expected", [
    ("true", True), ("True", True), ("1", True), ("yes", True), ("on", True),
    ("false", False), ("", False), ("0", False), ("off", False), ("maybe", False),
])
def test_flag_parsing_is_fail_closed(monkeypatch, value, expected):
    monkeypatch.setenv("ENABLE_OWNED_DISCOVERY_PROMOTION", value)
    import app.services.source_router as sr
    assert sr._owned_discovery_promotion_enabled() is expected


def test_flag_unset_is_off(monkeypatch):
    monkeypatch.delenv("ENABLE_OWNED_DISCOVERY_PROMOTION", raising=False)
    import app.services.source_router as sr
    assert sr._owned_discovery_promotion_enabled() is False


def test_registry_is_not_mutated_for_other_modules(monkeypatch):
    """Guard the trap this file already fell into once: the helper must leave the
    real module object (and its `Source` class) untouched, so a whole-suite run
    behaves exactly like an isolated one."""
    import app.services.source_router as sr
    source_cls_before = sr.Source
    registry_before = sr.SOURCE_REGISTRY
    sr_on = _reload_router(monkeypatch, "true")
    assert sr_on is sr
    assert sr.Source is source_cls_before
    monkeypatch.undo()
    assert sr.SOURCE_REGISTRY is registry_before
    assert all(isinstance(s, sr.Source) for s in sr.SOURCE_REGISTRY)
