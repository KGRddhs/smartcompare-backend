"""Wave B-FIX BF2 — the two MED leak classes from the coverage-driven sweep
(waveb_leak.json L3 + L4).

L3 — query_confirmed_structured_code accepted MEASURE-shaped tokens (100ML,
2LB, 2XL, 1TB) and short FAMILY stems (AF1) as the retailer's exact-model
assertion, waiving the variant-add fence at BOTH override ends (the A3 algolia
matcher override and the B0 should_cache_price parity override). And a LEGIT
shared code (L1212) waived the fence for a kids/GS / gift-set / tester /
decant title — a confirmed code asserts the MODEL, never the sellable UNIT.
Tighten (shared validator, so the two ends never drift):
  - a token that parses as a pure measure/clothing size confirms NOTHING;
  - a code without a >=2-digit run (family stem "AF1") confirms NOTHING;
  - the override is suppressed when the surface ADDS a kids/gs/gift/set/
    tester/decant marker the query never stated (bounded list, asymmetric).
The L1212 sanctioned unlock (descriptive 6thstreet title through the write
gate) is re-pinned here so the tighten can never over-reach it.

L4 — "shadow" sat in _COLOR_EDITION_TOKENS, collapsing the Nike AF1 Shadow
SILHOUETTE (a distinct, ~+20%-pricier SKU) onto the base AF1 for the colour
-alias categories. Removed for FASHION (it now discriminates BOTH ways, like
the fontanka/twist analogues that were never colour words); kept for
ELECTRONICS via a scoped extension set ("Shadow Black" is a real OEM colour —
HP/Realme listings must not start over-rejecting: the tighten's own
over-rejection is the next blind spot).
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    _selection_match,
    query_confirmed_structured_code,
    should_cache_price,
)
from app.services.algolia_service import _match_algolia_hit
from app.services.magento_graphql_service import _best_match
from app.services.woocommerce_service import _match_woo_product


@pytest.fixture(autouse=True)
def _exact_gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _pdp_price(**over):
    """Minimal cache-gate price dict (valid PDP url, in stock, genuine BHD)."""
    base = {
        "amount": 45.0, "currency": "BHD", "retailer": "store-example-bh.com",
        "url": "https://store-example-bh.com/product/item-slug/",
        "in_stock": True, "estimated": False, "source_method": "local_bhd",
        "confidence": 0.9,
    }
    base.update(over)
    return base


def _algolia_hit(name, brand, sku=None, style_code=None):
    hit = {"name": name, "brand_name": brand,
           "price": [{"BHD": {"default": 45.0}}]}
    if sku is not None:
        hit["sku"] = sku
    if style_code is not None:
        hit["style_code"] = style_code
    return hit


# ---------------------------------------------------------------------------
# L3 (a) — the shared validator: measure shapes + family stems confirm nothing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code,query_words", [
    ("100ML", {"dior", "sauvage", "100ml"}),          # fragrance size
    ("90ml", {"black", "opium", "90ml"}),
    ("2LB", {"whey", "protein", "2lb"}),              # supplement weight
    ("1TB", {"macbook", "1tb"}),                      # storage
    ("2XL", {"tee", "2xl"}),                          # clothing size
])
def test_measure_shaped_codes_confirm_nothing(code, query_words):
    """A size/weight/storage/clothing-size token asserts a SIZE, not a model —
    it must never engage the variant-add waiver."""
    assert query_confirmed_structured_code(code, query_words) == ""


@pytest.mark.parametrize("code,query_words", [
    ("AF1", {"nike", "af1", "white"}),   # family stem (Air Force 1 line)
    ("AM1", {"nike", "am1"}),            # family stem (Air Max 1 line)
])
def test_family_stem_without_two_digit_run_confirms_nothing(code, query_words):
    """A short family STEM names a LINE (base/Kids/GS/LV8 all share it), not an
    exact SKU — require a >=2-digit run."""
    assert query_confirmed_structured_code(code, query_words) == ""


def test_sanctioned_model_codes_still_confirm():
    """The real structured model codes keep confirming (the L1212 unlock +
    the hyphen-folded Nike style code pinned at the adapter end)."""
    assert query_confirmed_structured_code(
        "L1212", {"lacoste", "l1212", "polo"}) == "L1212"
    assert query_confirmed_structured_code(
        "NKCW4554-001", {"nike", "nkcw4554001"}) == "NKCW4554-001"


# ---------------------------------------------------------------------------
# L3 (b) — sweep repros through the REAL ends (cache gate + algolia matchers)
# ---------------------------------------------------------------------------

def test_sauvage_elixir_measure_code_never_caches():
    """Sweep repro: the Elixir flanker rode structured_code='100ML' through the
    B0 cache override ('elixir' is not a concentration word, so no axis fires)."""
    p = _pdp_price(title="Sauvage Elixir 100ml", brand="Dior",
                   structured_code="100ML")
    assert should_cache_price("Dior Sauvage 100ml", p, "fragrances") is False


def test_af1_kids_gs_family_code_never_caches():
    """Sweep repro: the kids/GS segment is deliberately NOT fashion padding;
    the family-stem code waived exactly that rejection."""
    p = _pdp_price(title="AF1 Kids GS White Sneakers", brand="Nike",
                   structured_code="AF1")
    assert should_cache_price("Nike AF1 White", p, "fashion") is False


def test_algolia_measure_sku_stem_never_matches():
    """Adapter end of the same class: sku '100ML_X' pre-underscore stem."""
    hit = _algolia_hit("Sauvage Elixir 100ml", "Dior", sku="100ML_X")
    assert _match_algolia_hit(
        [hit], "Dior Sauvage 100ml", resolved_category="fragrances") is None


def test_algolia_af1_kids_sku_never_matches():
    hit = _algolia_hit("AF1 Kids GS White Sneakers", "Nike", sku="AF1_KIDS")
    assert _match_algolia_hit(
        [hit], "Nike AF1 White", resolved_category="fashion") is None


# ---------------------------------------------------------------------------
# L3 (c) — kids/gift-set/tester/decant adds suppress the override even under a
# LEGIT confirmed code (both ends), asymmetric (a query stating it is fine)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("title", [
    "L1212 Polo Gift Set with Cap",                # sweep repro
    "Logo Detail Polo T-Shirt Kids",
    "Logo Detail Polo T-Shirt GS",
    "Logo Detail Polo T-Shirt Tester",
    "Logo Detail Polo T-Shirt Decant",
])
def test_variant_marker_add_suppresses_cache_override(title):
    p = _pdp_price(title=title, brand="Lacoste", structured_code="L1212")
    assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is False


def test_variant_marker_add_suppresses_adapter_override():
    hit = _algolia_hit("L1212 Polo Gift Set", "Lacoste", sku="L1212_White",
                       style_code="L1212")
    assert _match_algolia_hit(
        [hit], "Lacoste L1212 Polo", resolved_category="fashion") is None


def test_query_stating_the_marker_is_not_suppressed():
    """Asymmetry pin: the suppression fires only on tokens the title ADDS —
    a gift-set QUERY still unlocks a descriptive gift-set title via the code."""
    p = _pdp_price(title="Logo Detail Short Sleeves Polo T-Shirt Gift Set",
                   brand="Lacoste", structured_code="L1212")
    assert should_cache_price("Lacoste L1212 Polo Gift Set", p, "fashion") is True


def test_l1212_sanctioned_unlock_still_passes():
    """THE sanctioned unlock (kpi-fash-005 write gate): the descriptive
    6thstreet title still caches via the confirmed code after the tighten."""
    p = _pdp_price(title="Logo Detail Short Sleeves Polo T-Shirt",
                   brand="Lacoste", structured_code="L1212")
    assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is True


# ---------------------------------------------------------------------------
# L4 — "shadow" is a fashion SILHOUETTE, not a colour: both directions
# ---------------------------------------------------------------------------

def test_af1_shadow_leak_rejected_selection():
    assert _selection_match(
        "Nike Air Force 1 White", "Nike Air Force 1 Shadow White",
        "fashion", candidate_brand="Nike") is False


def test_af1_shadow_leak_rejected_full_chains():
    """Sweep repro: every acceptance chain + the write gate refuse the Shadow
    silhouette for the base (numberless) query."""
    woo_payload = [{
        "name": "Nike Air Force 1 Shadow White",
        "permalink": "https://store-example-bh.com/product/af1-shadow-white/",
        "is_in_stock": True,
        "prices": {"price": "45000", "currency_minor_unit": 3,
                   "currency_code": "BHD"},
    }]
    assert _match_woo_product(
        woo_payload, "Nike Air Force 1 White", "BHD",
        resolved_category="fashion") is None
    nodes = [{"name": "Nike Air Force 1 Shadow White", "brand": "Nike",
              "price": 45.0, "currency": "BHD", "in_stock": True,
              "url_key": "af1-shadow-white"}]
    assert _best_match(
        nodes, "Nike Air Force 1 White", resolved_category="fashion") is None
    p = _pdp_price(title="Nike Air Force 1 Shadow White", brand="Nike")
    assert should_cache_price("Nike Air Force 1 White", p, "fashion") is False


def test_shadow_query_still_accepts_shadow_title():
    """The token discriminates, it does not over-reject: a Shadow query keeps
    matching the Shadow product end-to-end."""
    assert _selection_match(
        "Nike Air Force 1 Shadow White", "Nike Air Force 1 Shadow White",
        "fashion", candidate_brand="Nike") is True
    woo_payload = [{
        "name": "Nike Air Force 1 Shadow White",
        "permalink": "https://store-example-bh.com/product/af1-shadow-white/",
        "is_in_stock": True,
        "prices": {"price": "45000", "currency_minor_unit": 3,
                   "currency_code": "BHD"},
    }]
    assert _match_woo_product(
        woo_payload, "Nike Air Force 1 Shadow White", "BHD",
        resolved_category="fashion") is not None
    p = _pdp_price(title="Nike Air Force 1 Shadow White", brand="Nike")
    assert should_cache_price(
        "Nike Air Force 1 Shadow White", p, "fashion") is True


def test_shadow_query_rejects_base_title():
    """Converse direction: the base AF1 must not be served under a Shadow
    query (pre-fix the colour strip erased the query's own discriminator)."""
    assert _selection_match(
        "Nike Air Force 1 Shadow White", "Nike Air Force 1 White Sneakers",
        "fashion", candidate_brand="Nike") is False


def test_fontanka_twist_analogues_still_reject():
    """'shadow' now behaves exactly like the sibling silhouette names that were
    never colour words (the sweep's verified analogues)."""
    for silhouette in ("Fontanka", "Twist"):
        assert _selection_match(
            "Nike Air Force 1 White",
            f"Nike Air Force 1 {silhouette} White",
            "fashion", candidate_brand="Nike") is False


def test_electronics_shadow_colour_still_tolerated():
    """Bounded scope: 'Shadow Black' is a REAL OEM colour for electronics —
    the fashion tighten must not start over-rejecting genuine colour-suffixed
    electronics listings (kept via the electronics-scoped colour extension)."""
    assert _selection_match(
        "HP Victus 15 Gaming Laptop",
        "HP Victus 15 Gaming Laptop Shadow Black",
        "electronics", candidate_brand="HP") is True
