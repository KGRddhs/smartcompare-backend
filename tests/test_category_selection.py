"""
Tests for category selection feature.

Covers:
- New category schema validation (makeup, skincare, haircare, fragrances)
- Schema edge cases (duplicates, types, field counts)
- Spec prompt building for new categories
- API parameter acceptance (selected_category)
- Category switching response fields
- Parser prompt category detection
- Live GPT extraction for new categories (live_unit marker)

Run free tests:   pytest tests/test_category_selection.py -v -m "not live_unit"
Run live tests:   pytest tests/test_category_selection.py -v -m live_unit  (~$0.02)
Run all:          pytest tests/test_category_selection.py -v
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS


# ============================================
# Schema Existence & Field Validation
# ============================================

class TestSchemaExistence:
    """Verify all category schemas exist with correct structure."""

    def test_new_category_schemas_exist(self):
        """All 4 new schemas must be defined."""
        assert "makeup" in CATEGORY_SPEC_SCHEMAS
        assert "skincare" in CATEGORY_SPEC_SCHEMAS
        assert "haircare" in CATEGORY_SPEC_SCHEMAS
        assert "fragrances" in CATEGORY_SPEC_SCHEMAS

    def test_existing_schemas_unchanged(self):
        """Existing schemas must not be broken by adding new ones."""
        assert "electronics" in CATEGORY_SPEC_SCHEMAS
        assert "grocery" in CATEGORY_SPEC_SCHEMAS
        assert "supplements" in CATEGORY_SPEC_SCHEMAS
        assert "other" in CATEGORY_SPEC_SCHEMAS
        # Check a few key fields still exist
        assert "display" in CATEGORY_SPEC_SCHEMAS["electronics"]
        assert "processor" in CATEGORY_SPEC_SCHEMAS["electronics"]
        assert "active_ingredient" in CATEGORY_SPEC_SCHEMAS["supplements"]

    def test_total_category_count(self):
        """Should have 9 total categories (4 existing + 4 beauty + fashion)."""
        assert len(CATEGORY_SPEC_SCHEMAS) == 9

    def test_all_schemas_are_lists(self):
        """All schemas should be lists of field names."""
        for key, schema in CATEGORY_SPEC_SCHEMAS.items():
            assert isinstance(schema, list), f"Schema '{key}' is not a list"
            assert all(isinstance(f, str) for f in schema), \
                f"Schema '{key}' has non-string fields"

    def test_no_duplicate_fields_in_any_schema(self):
        """No schema should contain duplicate field names."""
        for category, fields in CATEGORY_SPEC_SCHEMAS.items():
            assert len(fields) == len(set(fields)), \
                f"Schema '{category}' has duplicate fields: " \
                f"{[f for f in fields if fields.count(f) > 1]}"

    def test_all_field_names_are_snake_case(self):
        """All field names should follow snake_case convention."""
        import re
        for category, fields in CATEGORY_SPEC_SCHEMAS.items():
            for field in fields:
                assert re.match(r'^[a-z][a-z0-9_]*$', field), \
                    f"Field '{field}' in '{category}' is not snake_case"


class TestMakeupSchema:
    """Makeup schema field validation."""

    def test_required_fields(self):
        makeup = CATEGORY_SPEC_SCHEMAS["makeup"]
        for field in ["shade_range", "finish", "coverage", "skin_type", "volume"]:
            assert field in makeup, f"Missing '{field}'"

    def test_minimum_field_count(self):
        assert len(CATEGORY_SPEC_SCHEMAS["makeup"]) >= 10

    def test_has_cruelty_free(self):
        """GCC market relevance: cruelty_free is important."""
        assert "cruelty_free" in CATEGORY_SPEC_SCHEMAS["makeup"]

    def test_has_waterproof(self):
        assert "waterproof" in CATEGORY_SPEC_SCHEMAS["makeup"]

    def test_has_vegan(self):
        assert "vegan" in CATEGORY_SPEC_SCHEMAS["makeup"]


class TestSkincareSchema:
    """Skincare schema field validation."""

    def test_required_fields(self):
        skincare = CATEGORY_SPEC_SCHEMAS["skincare"]
        for field in ["skin_type", "skin_concern", "active_ingredient", "volume"]:
            assert field in skincare, f"Missing '{field}'"

    def test_minimum_field_count(self):
        assert len(CATEGORY_SPEC_SCHEMAS["skincare"]) >= 9

    def test_has_fragrance_free(self):
        """Important for sensitive skin products."""
        assert "fragrance_free" in CATEGORY_SPEC_SCHEMAS["skincare"]

    def test_has_spf(self):
        assert "spf" in CATEGORY_SPEC_SCHEMAS["skincare"]


class TestHaircareSchema:
    """Haircare schema field validation."""

    def test_required_fields(self):
        haircare = CATEGORY_SPEC_SCHEMAS["haircare"]
        for field in ["hair_type", "hair_concern", "sulfate_free", "volume"]:
            assert field in haircare, f"Missing '{field}'"

    def test_minimum_field_count(self):
        assert len(CATEGORY_SPEC_SCHEMAS["haircare"]) >= 9

    def test_has_paraben_free(self):
        assert "paraben_free" in CATEGORY_SPEC_SCHEMAS["haircare"]

    def test_has_silicone_free(self):
        assert "silicone_free" in CATEGORY_SPEC_SCHEMAS["haircare"]


class TestFragrancesSchema:
    """Fragrances schema field validation."""

    def test_required_fields(self):
        fragrances = CATEGORY_SPEC_SCHEMAS["fragrances"]
        for field in ["scent_family", "notes_top", "notes_heart", "notes_base", "longevity"]:
            assert field in fragrances, f"Missing '{field}'"

    def test_minimum_field_count(self):
        assert len(CATEGORY_SPEC_SCHEMAS["fragrances"]) >= 9

    def test_has_concentration(self):
        """EDT vs EDP vs Parfum is critical for fragrances."""
        assert "concentration" in CATEGORY_SPEC_SCHEMAS["fragrances"]

    def test_has_sillage(self):
        assert "sillage" in CATEGORY_SPEC_SCHEMAS["fragrances"]

    def test_has_season(self):
        assert "season" in CATEGORY_SPEC_SCHEMAS["fragrances"]


# ============================================
# Spec Prompt Building Tests
# ============================================

class TestSpecPromptBuilding:
    """Verify _build_specs_prompt uses correct schema for each category."""

    def test_makeup_prompt_contains_makeup_fields(self):
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("MAC", "Ruby Woo", "", "makeup", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert "shade_range" in prompt
        assert "finish" in prompt
        assert "coverage" in prompt

    def test_skincare_prompt_contains_skincare_fields(self):
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("CeraVe", "Moisturizing Cream", "", "skincare", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert "skin_concern" in prompt
        assert "active_ingredient" in prompt

    def test_haircare_prompt_contains_haircare_fields(self):
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("Olaplex", "No. 3", "", "haircare", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert "hair_type" in prompt
        assert "sulfate_free" in prompt

    def test_fragrances_prompt_contains_fragrance_fields(self):
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("Chanel", "No. 5", "", "fragrances", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert "scent_family" in prompt
        assert "notes_top" in prompt
        assert "longevity" in prompt

    def test_unknown_category_falls_back_to_other(self):
        """Unknown category should fall back to 'other' schema."""
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("Brand", "Product", "", "nonexistent", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert "dimensions" in prompt
        assert "weight" in prompt

    def test_makeup_prompt_does_not_contain_electronics_schema_fields(self):
        """Makeup prompt JSON schema should NOT contain electronics-specific fields."""
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("MAC", "Ruby Woo", "", "makeup", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert '"processor": null' not in prompt
        assert '"ram": null' not in prompt
        assert '"rear_camera": null' not in prompt

    def test_fragrances_prompt_does_not_contain_supplement_schema_fields(self):
        """Fragrances prompt schema should NOT contain supplement-specific fields."""
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("Chanel", "No. 5", "", "fragrances", "test context")
        prompt = result["system"] if isinstance(result, dict) else result
        assert '"dosage": null' not in prompt
        assert '"serving_size": null' not in prompt

    def test_prompt_includes_brand_and_name(self):
        """Prompt should reference the product brand and name."""
        from app.services.extraction_service import _build_specs_prompt
        result = _build_specs_prompt("MAC", "Ruby Woo Lipstick", "Retro Matte", "makeup", "context")
        prompt_text = (result["system"] + result["user"]) if isinstance(result, dict) else result
        assert "MAC" in prompt_text
        assert "Ruby Woo" in prompt_text


# ============================================
# API Parameter Tests
# ============================================

from app.main import app
client = TestClient(app)


class TestAPIParameter:
    """Test selected_category parameter acceptance in the API."""

    def test_api_accepts_selected_category_param(self):
        """GET /api/v1/text/compare should accept selected_category without 422."""
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
            assert response.status_code != 422

    def test_api_accepts_null_selected_category(self):
        """API works without selected_category (backward compat)."""
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

    def test_api_passes_selected_category_to_service(self):
        """selected_category param should be forwarded to compare_from_text()."""
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
            call_kwargs = mock_service.compare_from_text.call_args
            assert call_kwargs is not None
            if call_kwargs.kwargs:
                assert call_kwargs.kwargs.get("selected_category") == "makeup"

    def test_api_accepts_invalid_category_without_422(self):
        """Invalid category values should not cause 422 (validation at service level)."""
        with patch("app.api.text_routes.get_comparison_service") as mock_svc:
            mock_service = mock_svc.return_value
            mock_service.compare_from_text = AsyncMock(return_value={
                "success": True, "products": [], "comparison": {},
                "category_used": "electronics", "category_switched": False,
            })
            response = client.get(
                "/api/v1/text/compare",
                params={"q": "iPhone 15 vs Galaxy S24", "selected_category": "nonexistent"}
            )
            assert response.status_code != 422


# ============================================
# Category Switching Response Tests
# ============================================

class TestCategorySwitchingResponse:
    """Test category switching fields in API response."""

    def test_category_switching_response_fields(self):
        """Response includes switching fields when mismatch."""
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

    def test_no_switch_response_fields(self):
        """Response has no switch when categories match."""
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

    def test_each_new_category_in_response(self):
        """Each new category can appear as category_used in response."""
        for cat in ["makeup", "skincare", "haircare", "fragrances"]:
            with patch("app.api.text_routes.get_comparison_service") as mock_svc:
                mock_service = mock_svc.return_value
                mock_service.compare_from_text = AsyncMock(return_value={
                    "success": True, "products": [], "comparison": {},
                    "category_used": cat, "category_switched": False,
                })
                response = client.get(
                    "/api/v1/text/compare",
                    params={"q": "product1 vs product2", "selected_category": cat}
                )
                data = response.json()
                assert data.get("category_used") == cat, \
                    f"Expected category_used='{cat}', got {data.get('category_used')}"


# ============================================
# Parser Prompt Tests (blocked until Task #11)
# ============================================

class TestParserPrompt:
    """PRODUCT_PARSER_PROMPT should include new categories."""

    def test_parser_prompt_includes_new_categories(self):
        from app.services.extraction_service import PRODUCT_PARSER_PROMPT
        assert "makeup" in PRODUCT_PARSER_PROMPT
        assert "skincare" in PRODUCT_PARSER_PROMPT
        assert "haircare" in PRODUCT_PARSER_PROMPT
        assert "fragrances" in PRODUCT_PARSER_PROMPT

    def test_parser_prompt_has_detection_rules(self):
        from app.services.extraction_service import PRODUCT_PARSER_PROMPT
        prompt_lower = PRODUCT_PARSER_PROMPT.lower()
        assert "lipstick" in prompt_lower or "foundation" in prompt_lower or "mascara" in prompt_lower
        assert "moisturizer" in prompt_lower or "serum" in prompt_lower or "cleanser" in prompt_lower
        assert "shampoo" in prompt_lower or "conditioner" in prompt_lower
        assert "perfume" in prompt_lower or "cologne" in prompt_lower

    def test_parser_prompt_still_has_existing_categories(self):
        """Existing categories should not be removed from prompt."""
        from app.services.extraction_service import PRODUCT_PARSER_PROMPT
        assert "electronics" in PRODUCT_PARSER_PROMPT
        assert "grocery" in PRODUCT_PARSER_PROMPT
        assert "supplements" in PRODUCT_PARSER_PROMPT


# ============================================
# Live GPT Extraction Tests (cost: ~$0.02 total)
# ============================================

@pytest.mark.live_unit
@pytest.mark.asyncio
async def test_makeup_extraction_live():
    """Extract makeup specs using new schema (live GPT call ~$0.005)."""
    from app.services.extraction_service import extract_specs

    specs = await extract_specs(
        brand="MAC",
        name="Ruby Woo Lipstick",
        variant="",
        category="makeup",
        search_context="MAC Ruby Woo lipstick retro matte finish iconic red shade full coverage long-wearing"
    )

    # extract_specs returns (result, usage) tuple since Session 22
    if isinstance(specs, tuple):
        specs = specs[0]
    assert isinstance(specs, dict), f"Expected dict, got {type(specs)}"
    makeup_fields = ["finish", "shade_range", "coverage", "skin_type", "waterproof",
                     "long_lasting", "cruelty_free", "vegan", "volume"]
    found = [f for f in makeup_fields if f in specs]
    assert len(found) >= 1, f"No makeup fields found in specs. Keys: {list(specs.keys())}"


@pytest.mark.live_unit
@pytest.mark.asyncio
async def test_skincare_extraction_live():
    """Extract skincare specs using new schema (live GPT call ~$0.005)."""
    from app.services.extraction_service import extract_specs

    specs = await extract_specs(
        brand="CeraVe",
        name="Moisturizing Cream",
        variant="",
        category="skincare",
        search_context="CeraVe moisturizing cream for dry skin hyaluronic acid ceramides fragrance free 16 oz"
    )

    if isinstance(specs, tuple):
        specs = specs[0]
    assert isinstance(specs, dict)
    skincare_fields = ["skin_type", "skin_concern", "active_ingredient", "fragrance_free", "volume"]
    found = [f for f in skincare_fields if f in specs]
    assert len(found) >= 1, f"No skincare fields found in specs. Keys: {list(specs.keys())}"


@pytest.mark.live_unit
@pytest.mark.asyncio
async def test_haircare_extraction_live():
    """Extract haircare specs using new schema (live GPT call ~$0.005)."""
    from app.services.extraction_service import extract_specs

    specs = await extract_specs(
        brand="Olaplex",
        name="No. 3 Hair Perfector",
        variant="",
        category="haircare",
        search_context="Olaplex No. 3 hair perfector treatment damaged hair bond repair sulfate free paraben free 100ml"
    )

    if isinstance(specs, tuple):
        specs = specs[0]
    assert isinstance(specs, dict)
    haircare_fields = ["hair_type", "hair_concern", "sulfate_free", "paraben_free", "volume"]
    found = [f for f in haircare_fields if f in specs]
    assert len(found) >= 1, f"No haircare fields found in specs. Keys: {list(specs.keys())}"


@pytest.mark.live_unit
@pytest.mark.asyncio
async def test_fragrance_extraction_live():
    """Extract fragrance specs using new schema (live GPT call ~$0.005)."""
    from app.services.extraction_service import extract_specs

    specs = await extract_specs(
        brand="Chanel",
        name="No. 5",
        variant="Eau de Parfum",
        category="fragrances",
        search_context="Chanel No. 5 eau de parfum classic floral aldehyde perfume rose jasmine sandalwood 100ml"
    )

    if isinstance(specs, tuple):
        specs = specs[0]
    assert isinstance(specs, dict)
    fragrance_fields = ["scent_family", "notes_top", "notes_heart", "notes_base",
                        "longevity", "concentration"]
    found = [f for f in fragrance_fields if f in specs]
    assert len(found) >= 1, f"No fragrance fields found in specs. Keys: {list(specs.keys())}"
