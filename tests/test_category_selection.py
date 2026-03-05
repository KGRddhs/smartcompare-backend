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


# ============================================
# Task 2: API parameter tests
# ============================================

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)


def test_api_accepts_selected_category_param():
    """API endpoint accepts selected_category parameter without 422"""
    with patch("app.api.text_routes.get_comparison_service") as mock_svc:
        mock_service = mock_svc.return_value
        mock_service.compare_from_text = AsyncMock(return_value={
            "success": True, "products": [], "comparison": {},
            "category_used": "electronics", "category_switched": False,
        })
        response = client.get(
            "/api/v1/text/compare",
            params={"q": "iPhone 15 vs Galaxy S24", "selected_category": "electronics"}
        )
        # Should not be 422 (validation error)
        assert response.status_code != 422


def test_api_accepts_null_selected_category():
    """API endpoint works without selected_category (backwards compatible)"""
    with patch("app.api.text_routes.get_comparison_service") as mock_svc:
        mock_service = mock_svc.return_value
        mock_service.compare_from_text = AsyncMock(return_value={
            "success": True, "products": [], "comparison": {},
            "category_used": "electronics", "category_switched": False,
        })
        response = client.get(
            "/api/v1/text/compare",
            params={"q": "iPhone 15 vs Galaxy S24"}
        )
        assert response.status_code != 422


def test_api_passes_selected_category_to_service():
    """API passes selected_category to service.compare_from_text()"""
    with patch("app.api.text_routes.get_comparison_service") as mock_svc:
        mock_service = mock_svc.return_value
        mock_service.compare_from_text = AsyncMock(return_value={
            "success": True, "products": [], "comparison": {},
            "category_used": "makeup", "category_switched": True,
            "original_category": "electronics",
        })
        client.get(
            "/api/v1/text/compare",
            params={"q": "MAC lipstick vs Dior lipstick", "selected_category": "makeup"}
        )
        # Verify selected_category was passed to the service
        call_kwargs = mock_service.compare_from_text.call_args
        assert call_kwargs is not None
        # Check it was passed as keyword arg
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs.get("selected_category") == "makeup"


# ============================================
# Task 3: Category switching logic tests
# ============================================

def test_category_switching_response_fields():
    """Service response includes category switching fields when mismatch"""
    with patch("app.api.text_routes.get_comparison_service") as mock_svc:
        mock_service = mock_svc.return_value
        mock_service.compare_from_text = AsyncMock(return_value={
            "success": True, "products": [], "comparison": {},
            "category_used": "makeup", "category_switched": True,
            "original_category": "electronics",
        })
        response = client.get(
            "/api/v1/text/compare",
            params={"q": "MAC lipstick vs Dior lipstick", "selected_category": "electronics"}
        )
        data = response.json()
        assert data.get("category_used") == "makeup"
        assert data.get("category_switched") is True
        assert data.get("original_category") == "electronics"


def test_no_switch_response_fields():
    """Service response has no switch when categories match"""
    with patch("app.api.text_routes.get_comparison_service") as mock_svc:
        mock_service = mock_svc.return_value
        mock_service.compare_from_text = AsyncMock(return_value={
            "success": True, "products": [], "comparison": {},
            "category_used": "electronics", "category_switched": False,
            "original_category": None,
        })
        response = client.get(
            "/api/v1/text/compare",
            params={"q": "iPhone 15 vs Galaxy S24", "selected_category": "electronics"}
        )
        data = response.json()
        assert data.get("category_used") == "electronics"
        assert data.get("category_switched") is False
        assert data.get("original_category") is None


# ============================================
# Task 5: Parser prompt category detection tests
# ============================================

def test_parser_prompt_includes_new_categories():
    """PRODUCT_PARSER_PROMPT includes the 4 new categories"""
    from app.services.extraction_service import PRODUCT_PARSER_PROMPT
    assert "makeup" in PRODUCT_PARSER_PROMPT
    assert "skincare" in PRODUCT_PARSER_PROMPT
    assert "haircare" in PRODUCT_PARSER_PROMPT
    assert "fragrances" in PRODUCT_PARSER_PROMPT


def test_parser_prompt_has_detection_rules():
    """PRODUCT_PARSER_PROMPT has detection rules for new categories"""
    from app.services.extraction_service import PRODUCT_PARSER_PROMPT
    # Should have examples/hints for each new category
    assert "lipstick" in PRODUCT_PARSER_PROMPT.lower() or "foundation" in PRODUCT_PARSER_PROMPT.lower()
    assert "moisturizer" in PRODUCT_PARSER_PROMPT.lower() or "serum" in PRODUCT_PARSER_PROMPT.lower()
    assert "shampoo" in PRODUCT_PARSER_PROMPT.lower() or "conditioner" in PRODUCT_PARSER_PROMPT.lower()
    assert "perfume" in PRODUCT_PARSER_PROMPT.lower() or "cologne" in PRODUCT_PARSER_PROMPT.lower()
