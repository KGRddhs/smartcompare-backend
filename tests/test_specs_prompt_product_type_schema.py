"""L2.12 — Tests for per-product-type schema injection in `_build_specs_prompt`.

When `detect_product_type(name, category)` returns a specific subtype
(e.g., `electronics.phone`, `electronics.washer`, `fragrances.niche`) the
prompt MUST use that subtype's schema instead of the broad category schema.
This way an iPhone gets display/processor/ram/... while a washing machine
gets capacity_kg/spin_rpm/energy_class.

Backwards-compat: when the product is ambiguous (no keyword hit) the
function falls back to the category-level CATEGORY_SPEC_SCHEMAS field list
exactly as before.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.extraction_service import _build_specs_prompt
from app.services.product_type_router import (
    PRODUCT_TYPE_SCHEMAS,
    get_schema_for_type,
)


def _system(prompt: dict) -> str:
    return prompt["system"]


def test_phone_prompt_uses_electronics_phone_schema():
    prompt = _build_specs_prompt(
        "Apple", "iPhone 15 Pro", "256GB", "electronics", "search context here"
    )
    sys = _system(prompt)
    phone_fields = get_schema_for_type("electronics.phone")
    for field in ("display", "rear_camera", "front_camera", "battery"):
        assert field in phone_fields
        assert field in sys


def test_washer_prompt_uses_electronics_washer_schema_not_phone_schema():
    prompt = _build_specs_prompt(
        "Samsung", "WW90T504DAB Washing Machine", "9kg",
        "electronics", "search context",
    )
    sys = _system(prompt)
    washer_fields = get_schema_for_type("electronics.washer")
    # Check the REQUIRED SCHEMA section explicitly (not the static prefix
    # which has rear_camera mentioned in inline examples).
    schema_block_start = sys.find("REQUIRED SCHEMA:")
    schema_block_end = sys.find("CATEGORY-SPECIFIC GUIDANCE")
    assert schema_block_start > 0 and schema_block_end > schema_block_start
    schema_block = sys[schema_block_start:schema_block_end]

    assert "capacity_kg" in washer_fields and '"capacity_kg"' in schema_block
    assert "spin_rpm" in washer_fields and '"spin_rpm"' in schema_block
    # Phone-specific fields MUST NOT appear in the washer SCHEMA block
    assert '"rear_camera"' not in schema_block
    assert '"front_camera"' not in schema_block


def test_fragrance_niche_prompt_includes_perfumer_field():
    prompt = _build_specs_prompt(
        "Creed", "Aventus", "100ml", "fragrances", "search context"
    )
    sys = _system(prompt)
    niche_fields = get_schema_for_type("fragrances.niche")
    assert "perfumer" in niche_fields and "perfumer" in sys


def test_unknown_product_in_known_category_falls_to_first_subtype():
    """An ambiguous electronics product gets the first electronics.* subtype
    schema. Better than nothing — at least the field list is electronics-shaped
    instead of the broad 'other'."""
    prompt = _build_specs_prompt(
        "ObscureBrand", "Mystery Gadget", "", "electronics", "search context"
    )
    sys = _system(prompt)
    # Should land on electronics.phone (first declared subtype) since it's the
    # detect_product_type fallback for unknown electronics inputs
    expected_first_subtype = "electronics.phone"
    expected_fields = get_schema_for_type(expected_first_subtype)
    # At least 50% of the schema fields should be referenced in the prompt
    populated = sum(1 for f in expected_fields if f in sys)
    assert populated >= len(expected_fields) // 2


def test_other_category_keeps_broad_schema():
    """A category not in PRODUCT_TYPE_SCHEMAS keeps the existing 'other'
    fallback path (no regression)."""
    prompt = _build_specs_prompt(
        "Generic", "Random Item", "", "other", "search context"
    )
    sys = _system(prompt)
    # Just verify the function still returns a non-empty system prompt
    assert "CATEGORY: other" in sys
    assert "REQUIRED SCHEMA" in sys


def test_schema_injection_preserves_static_prefix():
    """The static prefix used for OpenAI prompt-caching MUST still come
    first — otherwise the cache-hit rate craters."""
    prompt = _build_specs_prompt(
        "Apple", "iPhone 15 Pro", "256GB", "electronics", "search context"
    )
    sys = _system(prompt)
    # SPECS_SYSTEM_STATIC_PREFIX starts with "You are a product spec extraction expert..."
    # — we just confirm it's not been moved or truncated by the L2.12 patch
    assert sys.startswith("You are") or sys.startswith("\nYou are")
    # CATEGORY/SCHEMA section comes AFTER the static prefix
    assert sys.find("CATEGORY:") > 100


def test_supplement_product_type_uses_specific_schema():
    """Whey protein → supplements.protein → includes protein_g_serving etc."""
    prompt = _build_specs_prompt(
        "Optimum Nutrition", "Gold Standard Whey Protein", "2lb",
        "supplements", "search context",
    )
    sys = _system(prompt)
    protein_fields = get_schema_for_type("supplements.protein")
    assert "protein_g_serving" in protein_fields and "protein_g_serving" in sys


def test_vitamin_d_uses_vitamin_schema_not_protein():
    prompt = _build_specs_prompt(
        "NOW Foods", "Vitamin D 5000 IU", "240 softgels",
        "supplements", "search context",
    )
    sys = _system(prompt)
    vitamin_fields = get_schema_for_type("supplements.vitamin")
    assert "dose_iu_mcg" in vitamin_fields and "dose_iu_mcg" in sys
    # Should NOT include protein-specific fields
    assert "protein_g_serving" not in sys
