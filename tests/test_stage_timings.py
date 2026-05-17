"""DEBUG_STAGE_TIMINGS env flag adds per-stage timing to metadata."""
import os
import pytest
from unittest.mock import AsyncMock, patch

from app.services.structured_comparison_service import (
    get_comparison_service,
    StructuredComparisonService,
)


@pytest.mark.asyncio
async def test_stage_timings_present_when_flag_on(monkeypatch):
    """When DEBUG_STAGE_TIMINGS=true, response metadata includes
    stage_timings_ms with the expected keys per product."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")

    # Reset the cached flag so the test's monkeypatch takes effect
    import app.services.structured_comparison_service as scs
    scs._DEBUG_STAGE_TIMINGS = None

    # Patch the network-going helpers so the test is offline
    with patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "8 GB"}),
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch.object(
        StructuredComparisonService, "_get_reviews",
        new=AsyncMock(return_value={"summary": "test", "pros": [], "cons": []}),
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating",
        new=AsyncMock(return_value={"rating": 4.5, "review_count": 100, "rating_verified": True, "rating_source": {}}),
    ), patch(
        "app.services.structured_comparison_service.search_web",
        new=AsyncMock(return_value={"organic": []}),
    ), patch(
        "app.services.structured_comparison_service.parse_product_query",
        new=AsyncMock(return_value=(
            {
                "products": [
                    {"brand": "Apple", "name": "iPhone 17", "variant": None, "category": "electronics"},
                    {"brand": "Samsung", "name": "Galaxy S25 Ultra", "variant": None, "category": "electronics"},
                ],
                "comparison_type": "value",
            },
            {"prompt_tokens": 0, "completion_tokens": 0},
        )),
    ), patch(
        "app.services.structured_comparison_service.generate_comparison",
        new=AsyncMock(return_value=(
            {
                "winner_index": 0,
                "winner_declaration": "Apple iPhone 17",
                "winner_reason": "Better all-rounder",
                "key_tradeoff": "Price vs performance",
                "value_context": "",
                "best_for": {},
                "personalized_insights": [],
                "product_0_pros": [],
                "product_0_cons": [],
                "product_1_pros": [],
                "product_1_cons": [],
            },
            {"prompt_tokens": 0, "completion_tokens": 0},
        )),
    ):
        svc = get_comparison_service()
        response = await svc.compare_from_text(
            query="iPhone 17 vs Galaxy S25 Ultra",
            region="bahrain",
        )

    metadata = response.get("metadata") or {}
    timings = metadata.get("stage_timings_ms")
    assert timings is not None, "stage_timings_ms missing when flag enabled"
    assert isinstance(timings, dict), f"expected dict, got {type(timings)}"

    # Per-product timing keys (list-of-dicts, one per product)
    products_timings = timings.get("per_product")
    assert isinstance(products_timings, list), "per_product missing"
    assert len(products_timings) == 2, f"expected 2 products, got {len(products_timings)}"

    expected_keys = {"unified_search_ms", "specs_ms", "price_ms",
                     "reviews_ms", "rating_ms"}
    for i, p in enumerate(products_timings):
        missing = expected_keys - set(p.keys())
        assert not missing, f"product {i} missing keys: {missing}"
        for k in expected_keys:
            assert isinstance(p[k], (int, float)), f"product {i} {k} is not numeric"
            assert p[k] >= 0, f"product {i} {k} is negative"

    # Top-level orchestrator timings
    expected_top = {"total_ms", "scoring_ms", "verdict_ms", "response_build_ms"}
    missing_top = expected_top - set(timings.keys())
    assert not missing_top, f"orchestrator-level keys missing: {missing_top}"


@pytest.mark.asyncio
async def test_stage_timings_absent_when_flag_off(monkeypatch):
    """When DEBUG_STAGE_TIMINGS is unset or false, metadata.stage_timings_ms
    must NOT be present (zero observability surface in prod)."""
    monkeypatch.delenv("DEBUG_STAGE_TIMINGS", raising=False)

    # Reset the cached flag so this test sees the unset env
    import app.services.structured_comparison_service as scs
    scs._DEBUG_STAGE_TIMINGS = None

    with patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "8 GB"}),
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch.object(
        StructuredComparisonService, "_get_reviews",
        new=AsyncMock(return_value={"summary": "test", "pros": [], "cons": []}),
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating",
        new=AsyncMock(return_value={"rating": 4.5, "review_count": 100, "rating_verified": True, "rating_source": {}}),
    ), patch(
        "app.services.structured_comparison_service.search_web",
        new=AsyncMock(return_value={"organic": []}),
    ), patch(
        "app.services.structured_comparison_service.parse_product_query",
        new=AsyncMock(return_value=(
            {
                "products": [
                    {"brand": "Apple", "name": "iPhone 17", "variant": None, "category": "electronics"},
                    {"brand": "Samsung", "name": "Galaxy S25 Ultra", "variant": None, "category": "electronics"},
                ],
                "comparison_type": "value",
            },
            {"prompt_tokens": 0, "completion_tokens": 0},
        )),
    ), patch(
        "app.services.structured_comparison_service.generate_comparison",
        new=AsyncMock(return_value=(
            {
                "winner_index": 0,
                "winner_declaration": "Apple iPhone 17",
                "winner_reason": "Better all-rounder",
                "key_tradeoff": "Price vs performance",
                "value_context": "",
                "best_for": {},
                "personalized_insights": [],
                "product_0_pros": [],
                "product_0_cons": [],
                "product_1_pros": [],
                "product_1_cons": [],
            },
            {"prompt_tokens": 0, "completion_tokens": 0},
        )),
    ):
        svc = get_comparison_service()
        response = await svc.compare_from_text(
            query="iPhone 17 vs Galaxy S25 Ultra",
            region="bahrain",
        )

    metadata = response.get("metadata") or {}
    assert "stage_timings_ms" not in metadata, \
        "stage_timings_ms leaked into prod response (flag was off)"
