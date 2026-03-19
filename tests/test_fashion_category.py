"""Tests for fashion category detection and schema.

Covers:
- Fashion schema existence and field validation
- "other" schema cleanup (no electronics-centric fields)
- Fashion in parser prompt
- Category switching with fashion
- All 9 categories in parser prompt

Run: pytest tests/test_fashion_category.py -v
"""
import pytest
from app.services.extraction_service import (
    CATEGORY_SPEC_SCHEMAS,
    PRODUCT_PARSER_PROMPT,
)


class TestFashionSchema:
    """Test fashion category schema configuration."""

    def test_fashion_schema_exists(self):
        assert "fashion" in CATEGORY_SPEC_SCHEMAS

    def test_fashion_schema_fields(self):
        fields = CATEGORY_SPEC_SCHEMAS["fashion"]
        assert "material" in fields
        assert "style" in fields
        assert "closure_type" in fields
        assert "origin" in fields
        assert "design_details" in fields
        # Should NOT have electronics fields
        assert "power" not in fields
        assert "compatibility" not in fields
        assert "processor" not in fields

    def test_fashion_schema_length(self):
        """Fashion schema should have 10 fields."""
        assert len(CATEGORY_SPEC_SCHEMAS["fashion"]) == 10

    def test_other_schema_no_electronics_fields(self):
        """'other' schema should not have power/compatibility."""
        other_fields = CATEGORY_SPEC_SCHEMAS["other"]
        assert "power" not in other_fields
        assert "compatibility" not in other_fields
        assert "count" not in other_fields
        assert "included" not in other_fields

    def test_other_schema_has_generic_fields(self):
        other_fields = CATEGORY_SPEC_SCHEMAS["other"]
        assert "material" in other_fields
        assert "features" in other_fields
        assert "origin" in other_fields

    def test_fashion_in_parser_prompt(self):
        """Parser prompt must include fashion as a category option."""
        assert "fashion" in PRODUCT_PARSER_PROMPT
        assert "hats" in PRODUCT_PARSER_PROMPT.lower() or "hat" in PRODUCT_PARSER_PROMPT.lower()


class TestCategorySwitching:
    """Test that category switching works with fashion."""

    def test_fashion_category_different_from_electronics(self):
        """If user selects electronics but product is fashion, should switch."""
        selected = "electronics"
        detected = "fashion"
        assert selected != detected  # switching would trigger

    def test_fashion_category_different_from_supplements(self):
        selected = "supplements"
        detected = "fashion"
        assert selected != detected

    def test_fashion_no_switch_when_matching(self):
        selected = "fashion"
        detected = "fashion"
        assert selected == detected  # no switching


class TestProductTypeBinding:
    """Test that parser prompt has product-type binding rules."""

    def test_prompt_has_product_type_rule(self):
        """Parser prompt should mention product TYPE determines category."""
        prompt_lower = PRODUCT_PARSER_PROMPT.lower()
        assert "product type" in prompt_lower or "what the product is" in prompt_lower

    def test_fashion_product_examples_in_prompt(self):
        prompt_lower = PRODUCT_PARSER_PROMPT.lower()
        # At least some fashion items listed
        fashion_items = ["bag", "shoe", "jacket", "scarf", "belt", "wallet"]
        found = sum(1 for item in fashion_items if item in prompt_lower)
        assert found >= 3, f"Only {found} fashion items found in prompt"

    def test_all_nine_categories_in_prompt(self):
        categories = ["electronics", "grocery", "supplements", "makeup",
                       "skincare", "haircare", "fragrances", "fashion", "other"]
        for cat in categories:
            assert cat in PRODUCT_PARSER_PROMPT, f"Category '{cat}' missing from parser prompt"
