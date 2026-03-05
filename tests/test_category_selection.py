"""Tests for category selection feature"""
import pytest
from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS


# ============================================
# Task 1: Schema existence and field tests
# ============================================

def test_new_category_schemas_exist():
    """Verify all 4 new schemas are defined"""
    assert "makeup" in CATEGORY_SPEC_SCHEMAS
    assert "skincare" in CATEGORY_SPEC_SCHEMAS
    assert "haircare" in CATEGORY_SPEC_SCHEMAS
    assert "fragrances" in CATEGORY_SPEC_SCHEMAS


def test_makeup_schema_fields():
    """Verify makeup schema has required fields"""
    makeup = CATEGORY_SPEC_SCHEMAS["makeup"]
    required_fields = ["shade_range", "finish", "coverage", "skin_type", "volume"]
    for field in required_fields:
        assert field in makeup
    assert len(makeup) >= 10  # At least 10 fields


def test_skincare_schema_fields():
    """Verify skincare schema has required fields"""
    skincare = CATEGORY_SPEC_SCHEMAS["skincare"]
    required_fields = ["skin_type", "skin_concern", "active_ingredient", "volume"]
    for field in required_fields:
        assert field in skincare
    assert len(skincare) >= 9


def test_haircare_schema_fields():
    """Verify haircare schema has required fields"""
    haircare = CATEGORY_SPEC_SCHEMAS["haircare"]
    required_fields = ["hair_type", "hair_concern", "sulfate_free", "volume"]
    for field in required_fields:
        assert field in haircare
    assert len(haircare) >= 9


def test_fragrances_schema_fields():
    """Verify fragrances schema has required fields"""
    fragrances = CATEGORY_SPEC_SCHEMAS["fragrances"]
    required_fields = ["scent_family", "notes_top", "notes_heart", "notes_base", "longevity"]
    for field in required_fields:
        assert field in fragrances
    assert len(fragrances) >= 9


def test_existing_schemas_unchanged():
    """Verify existing schemas are not accidentally modified"""
    assert "electronics" in CATEGORY_SPEC_SCHEMAS
    assert "grocery" in CATEGORY_SPEC_SCHEMAS
    assert "supplements" in CATEGORY_SPEC_SCHEMAS
    assert "other" in CATEGORY_SPEC_SCHEMAS
    # Check a few key fields still exist
    assert "display" in CATEGORY_SPEC_SCHEMAS["electronics"]
    assert "processor" in CATEGORY_SPEC_SCHEMAS["electronics"]
    assert "active_ingredient" in CATEGORY_SPEC_SCHEMAS["supplements"]


def test_all_schemas_are_lists():
    """All schemas should be lists of field names"""
    for key, schema in CATEGORY_SPEC_SCHEMAS.items():
        assert isinstance(schema, list), f"Schema '{key}' is not a list"
        assert all(isinstance(f, str) for f in schema), f"Schema '{key}' has non-string fields"


def test_total_category_count():
    """Should have 8 total categories (4 existing + 4 new)"""
    assert len(CATEGORY_SPEC_SCHEMAS) == 8
