"""L2.3 — Tests for `product_type_router.py` (25+ product-type schemas).

Maps product name + category -> "<category>.<sub_type>" key with a tailored
spec schema. Keyword-based detection; GPT fallback for unknowns added in L2.4.
"""

import pytest

from app.services.product_type_router import (
    PRODUCT_TYPE_KEYWORDS,
    PRODUCT_TYPE_SCHEMAS,
    detect_product_type,
    get_schema_for_type,
)


# ---------- electronics ----------

def test_detect_phone_from_iphone():
    assert detect_product_type("iPhone 15 Pro", "electronics") == "electronics.phone"


def test_detect_phone_from_galaxy_s():
    assert detect_product_type("Samsung Galaxy S24", "electronics") == "electronics.phone"


def test_detect_tv_from_lg_oled():
    assert detect_product_type("LG OLED55C3", "electronics") == "electronics.tv"


def test_detect_tv_from_qled():
    assert detect_product_type("Samsung 65 QLED 4K TV", "electronics") == "electronics.tv"


def test_detect_laptop_from_macbook():
    assert detect_product_type("MacBook Pro 14", "electronics") == "electronics.laptop"


def test_detect_tablet_from_ipad():
    assert detect_product_type("iPad Air M2", "electronics") == "electronics.tablet"


def test_detect_smartwatch_from_apple_watch():
    assert (
        detect_product_type("Apple Watch Series 9", "electronics")
        == "electronics.smartwatch"
    )


def test_detect_headphones_from_airpods():
    assert (
        detect_product_type("AirPods Pro 2", "electronics") == "electronics.headphones"
    )


def test_detect_speaker_from_sonos():
    assert detect_product_type("Sonos One SL", "electronics") == "electronics.speaker"


def test_detect_washer():
    assert (
        detect_product_type("Samsung WW90T504DAB Washing Machine", "electronics")
        == "electronics.washer"
    )


def test_detect_ac():
    assert detect_product_type("Carrier 1.5T Split AC", "electronics") == "electronics.ac"


# ---------- F2.1: AC / appliance schema enrichment ----------
# The PRODUCT_PARSER electronics enum (extraction_service.py:84) maps every
# AC phrasing -> category=electronics; detect_product_type then routes them to
# electronics.ac. These pin the full routing chain plus the coverage_sqm field
# added so AC specs extract without falling through to the Tier 2/3 cascade
# (stream-hard-cap memo, 2026-06-09).

@pytest.mark.parametrize(
    "query",
    [
        "Carrier 1.5 ton split AC",
        "LG Dual Inverter AC",
        "Daikin Inverter AC 24000 BTU",
        "Midea Window AC",
        "Gree 2 ton air conditioner",
    ],
)
def test_ac_phrasings_route_to_electronics_ac(query):
    assert detect_product_type(query, "electronics") == "electronics.ac"


def test_ac_schema_has_coverage_sqm():
    """coverage_sqm (room-size coverage) drives AC sizing — must be extractable."""
    schema = get_schema_for_type("electronics.ac")
    assert "coverage_sqm" in schema


def test_ac_schema_preserves_core_fields():
    """Enrichment must not drop the existing AC spec fields."""
    schema = get_schema_for_type("electronics.ac")
    for f in ("capacity_btu", "energy_class", "inverter", "refrigerant"):
        assert f in schema, f"AC schema missing {f!r}"


def test_detect_refrigerator():
    assert (
        detect_product_type("LG Side by Side Refrigerator", "electronics")
        == "electronics.refrigerator"
    )


def test_detect_vacuum_from_dyson():
    assert detect_product_type("Dyson V15 Detect", "electronics") == "electronics.vacuum"


def test_detect_gaming_console_from_ps5():
    assert detect_product_type("PS5 Slim Console", "electronics") == "electronics.gaming_console"


# ---------- supplements ----------

def test_detect_vitamin_d():
    assert detect_product_type("Vitamin D 5000 IU", "supplements") == "supplements.vitamin"


def test_detect_protein_supplement():
    assert (
        detect_product_type("Optimum Nutrition Gold Standard Whey Protein", "supplements")
        == "supplements.protein"
    )


def test_detect_fish_oil():
    assert detect_product_type("Nordic Naturals Omega 3", "supplements") == "supplements.fish_oil"


def test_detect_preworkout():
    assert detect_product_type("C4 Pre-Workout", "supplements") == "supplements.preworkout"


# ---------- fragrances ----------

def test_detect_fragrance_edp():
    assert (
        detect_product_type("Tom Ford Black Orchid Eau de Parfum 50ml", "fragrances")
        == "fragrances.edp"
    )


def test_detect_fragrance_edt():
    assert (
        detect_product_type("Dior Sauvage Eau de Toilette 100ml", "fragrances")
        == "fragrances.edt"
    )


def test_detect_fragrance_niche_creed():
    assert detect_product_type("Creed Aventus 100ml", "fragrances") == "fragrances.niche"


# ---------- makeup / skincare / haircare ----------

def test_detect_makeup_foundation():
    assert (
        detect_product_type("Fenty Beauty Pro Filt'r Foundation", "makeup")
        == "makeup.foundation"
    )


def test_detect_skincare_sunscreen():
    assert (
        detect_product_type("La Roche-Posay Anthelios SPF 50+", "skincare")
        == "skincare.sunscreen"
    )


def test_detect_haircare_shampoo():
    assert (
        detect_product_type("Olaplex No.4 Bond Maintenance Shampoo", "haircare")
        == "haircare.shampoo"
    )


# ---------- fashion / grocery ----------

def test_detect_fashion_bag():
    assert detect_product_type("Louis Vuitton Neverfull Tote", "fashion") == "fashion.bag"


def test_detect_fashion_shoe_sneaker():
    assert detect_product_type("Nike Air Force 1", "fashion") == "fashion.shoe"


def test_detect_grocery_olive_oil():
    assert detect_product_type("Bertolli Extra Virgin Olive Oil", "grocery") == "grocery.oil"


# ---------- schema retrieval ----------

def test_get_schema_for_phone_has_required_fields():
    schema = get_schema_for_type("electronics.phone")
    expected_fields = [
        "display", "processor", "ram", "storage", "battery", "rear_camera",
        "front_camera", "os", "weight",
    ]
    for f in expected_fields:
        assert f in schema, f"phone schema missing {f!r}"


def test_get_schema_for_washer_has_capacity():
    schema = get_schema_for_type("electronics.washer")
    assert "capacity_kg" in schema
    assert "spin_rpm" in schema


def test_get_schema_for_protein():
    schema = get_schema_for_type("supplements.protein")
    assert "protein_g_serving" in schema
    assert "calories" in schema


def test_get_schema_for_fragrance_edp():
    schema = get_schema_for_type("fragrances.edp")
    assert "longevity_hrs" in schema
    assert "sillage" in schema
    assert "notes_top" in schema


def test_get_schema_for_unknown_returns_empty_list():
    assert get_schema_for_type("unknown.unknown") == []


def test_schema_uniqueness_phone_vs_washer():
    """Different product types must have distinguishing fields."""
    phone = set(get_schema_for_type("electronics.phone"))
    washer = set(get_schema_for_type("electronics.washer"))
    assert "rear_camera" in phone and "rear_camera" not in washer
    assert "capacity_kg" in washer and "capacity_kg" not in phone


def test_minimum_25_product_type_schemas():
    """Per design: 25 product-type schemas."""
    assert len(PRODUCT_TYPE_SCHEMAS) >= 25


def test_all_keyword_keys_have_schemas():
    """Every product-type with keyword detection must have a schema."""
    for type_key in PRODUCT_TYPE_KEYWORDS:
        # multivitamin keyword maps may legitimately fall under supplements.vitamin
        # in detection, but the schema lookup should still exist
        assert type_key in PRODUCT_TYPE_SCHEMAS, f"no schema for {type_key}"


# ---------- fallback / category default ----------

def test_unknown_product_in_known_category_falls_to_first_subtype():
    """Unknown electronics product falls to the first electronics.* subtype."""
    result = detect_product_type("Some Obscure Gadget XYZ", "electronics")
    # category-specific fallback uses first match for the category
    assert result.startswith("electronics.")


def test_completely_unknown_category_returns_category_default():
    """No matching keywords AND no candidates for the category -> '<cat>.default'."""
    result = detect_product_type("XYZ123", "totally_made_up_category")
    assert result == "totally_made_up_category.default"
