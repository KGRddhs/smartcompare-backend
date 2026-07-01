"""Genuine-price KPI session — pinned regression tests for the two offline-safe
landings:

  1. occ_service candidate_brand wiring (fix-ladder keystone #1/#2) — thread the
     SAP-Commerce OCC `manufacturer` into BOTH strict_title_match + _selection_match
     so a genuine BH retailer PDP that lists a device by MODEL LINE ("iPad Air M2
     128GB", no "Apple") is recovered, while a wrong-brand candidate still rejects.
  2. _cache_price_identity_ok Wave-2 hardening — the cache-READ chokepoint now also
     runs the bounded _category_type_added flanker check (matching the display
     chokepoint is_price_showable), closing the flagship-concentration flanker leak
     on the cache-read path WITHOUT over-rejecting descriptive/brand-omitted titles.

Both are flag-gated by ENABLE_EXACT_PRICE_GATE (byte-identical when OFF).
"""
import pytest


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _occ_node(name, brand, val=199.99, stock="inStock"):
    node = {
        "name": name,
        "price": {"value": val, "currency": "BHD"},
        "stock": {"stockLevelStatus": stock},
    }
    if brand is not None:
        node["manufacturer"] = brand
    return node


# ---------------------------------------------------------------------------
# 1. occ candidate_brand wiring
# ---------------------------------------------------------------------------

def test_occ_brand_omitted_model_line_pdp_is_selected():
    """A genuine model-line PDP ("iPad Air M2 11-inch 128GB Blue", brand=Apple in
    the OCC manufacturer field but not the title) is now SELECTED — the missing
    "apple" title word no longer rejects it (candidate_brand drops it)."""
    from app.services.occ_service import _select_product
    payload = {"products": [_occ_node("iPad Air M2 11-inch 128GB Blue", "Apple")]}
    r = _select_product(payload, "Apple iPad Air M2 128GB", "electronics")
    assert r is not None and r.get("name") == "iPad Air M2 11-inch 128GB Blue"


def test_occ_wrong_brand_generic_model_rejected():
    """candidate_brand only drops the CANDIDATE's own brand — a wrong-brand
    candidate keeps the query brand required and _selection_match rejects it."""
    from app.services.occ_service import _select_product
    payload = {"products": [_occ_node("Galaxy Tab S9 128GB", "Samsung")]}
    assert _select_product(payload, "Apple iPad Air M2 128GB", "electronics") is None


def test_occ_missing_manufacturer_reverts_to_legacy_brand_required():
    """No manufacturer field -> candidate_brand="" -> legacy brand-required
    behaviour (a brand-omitted title is rejected). No regression from the wiring."""
    from app.services.occ_service import _select_product
    payload = {"products": [_occ_node("iPad Air M2 11-inch 128GB Blue", None)]}
    assert _select_product(payload, "Apple iPad Air M2 128GB", "electronics") is None


def test_occ_variant_add_guard_holds_even_with_brand_dropped():
    """The alongside _selection_match variant-add guard still rejects a higher
    variant (iPhone 15 -> iPhone 15 Pro Max) even when the brand token is dropped."""
    from app.services.occ_service import _select_product
    payload = {"products": [_occ_node("iPhone 15 Pro Max 256GB", "Apple")]}
    assert _select_product(payload, "Apple iPhone 15 256GB", "electronics") is None


def test_occ_wiring_flag_off_is_byte_identical(monkeypatch):
    """With the gate OFF, candidate_brand is a no-op: strict_title_match still
    requires every query word including "apple", so the brand-omitted model-line
    title is REJECTED exactly as the pre-wiring code did (byte-identical legacy)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    from app.services.occ_service import _select_product
    payload = {"products": [_occ_node("iPad Air M2 11-inch 128GB Blue", "Apple")]}
    r = _select_product(payload, "Apple iPad Air M2 128GB", "electronics")
    assert r is None


# ---------------------------------------------------------------------------
# 2. _cache_price_identity_ok Wave-2 hardening
# ---------------------------------------------------------------------------

def test_cache_read_rejects_flagship_concentration_flanker():
    """Cache-READ now rejects a flagship-concentration flanker (Sauvage EDT ->
    Sauvage Parfum) via _category_type_added — previously served (axis-only)."""
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"title": "Dior Sauvage Parfum 100ml"}, "", "Dior Sauvage Eau de Toilette 100ml",
        "fragrances",
    ) is False


def test_cache_read_rejects_supplement_type_flanker():
    """Whey -> Whey Isolate (a supplement TYPE add) is rejected on cache-read."""
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"title": "Optimum Nutrition Gold Standard Whey Isolate"}, "",
        "Optimum Nutrition Gold Standard Whey", "supplements",
    ) is False


def test_cache_read_accepts_descriptive_electronics_title():
    """A genuine DESCRIPTIVE title (extra colour/SIM/packaging words) must NOT be
    over-invalidated on cache-read (would re-resolve every cold hit + defeat warmer)."""
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"title": "Samsung Galaxy S24 256GB Dual SIM Phantom Black"}, "",
        "Samsung Galaxy S24 256GB", "electronics",
    ) is True


def test_cache_read_accepts_brand_omitted_fragrance_title():
    """A brand-omitted sephora-style genuine title still serves from cache."""
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"title": "Black Opium Eau de Parfum 90ml"}, "", "YSL Black Opium EDP 90ml",
        "fragrances",
    ) is True


def test_cache_read_still_rejects_wrong_axis():
    """The pre-existing axis-only backstop is preserved (S24 -> S24 FE storage/
    variant leak still rejected on cache-read)."""
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"title": "Samsung Galaxy S24 FE 256GB"}, "", "Samsung Galaxy S24 256GB",
        "electronics",
    ) is False


def test_cache_read_titleless_is_served():
    """A title-less cached price has nothing to verify -> served (benign)."""
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"amount": 45.0}, "", "YSL Black Opium EDP 90ml", "fragrances",
    ) is True


def test_cache_read_flag_off_is_noop(monkeypatch):
    """Gate OFF -> _cache_price_identity_ok is a pure no-op (True), byte-identical."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    from app.services.structured_comparison_service import _cache_price_identity_ok
    assert _cache_price_identity_ok(
        {"title": "Dior Sauvage Parfum 100ml"}, "", "Dior Sauvage Eau de Toilette 100ml",
        "fragrances",
    ) is True
