"""Bundle E Lane 1 L1.3 — build_dimensions_v2 CATEGORY_DIMENSIONS adapter.

Superseded the Bundle D `Reading 1` design (electronics kept hand-coded
_dim_dpi/_popularity/_build_quality, non-electronics emitted `<dim>_score`
keys). Lane 1 L1.3 unifies all 9 categories on the CATEGORY_DIMENSIONS
lookup and emits dim keys WITHOUT the `_score` suffix so the frontend
renders `performance` / `efficacy` / `longevity` etc.

Also fixes the upstream regression where `_dim_from_category_lookup`
read `scoring_result.scores.product_i[dim_key]` instead of the actual
production path `scoring_result.scores.product_i.breakdown[dim_key]`,
which caused every non-electronics v2.dimensions payload to silently
collapse to `['price','reviews','value']`.
"""
from __future__ import annotations

import pytest


def _make_products(cat_a: str, cat_b: str, price_a: int = 100, price_b: int = 110):
    return [
        {
            "name": "A", "brand": "X",
            "category": cat_a,
            "specs": {"dpi": 460},
            "price": {"amount": price_a, "currency": "BHD"},
            "rating": 4.5, "review_count": 1500,
            "warranty_years": 1,
        },
        {
            "name": "B", "brand": "Y",
            "category": cat_b,
            "specs": {"dpi": 415},
            "price": {"amount": price_b, "currency": "BHD"},
            "rating": 4.3, "review_count": 1200,
            "warranty_years": 2,
        },
    ]


def _scoring_result(category: str, breakdowns: tuple[dict, dict]) -> dict:
    """Wrap per-product breakdowns in the live scores shape so the L1.3
    rewrite of `_dim_from_category_lookup` (now reading
    `scores.product_i.breakdown[dim_key]`) resolves them."""
    return {
        "scores": {
            "product_0": {"overall": 75, "breakdown": breakdowns[0]},
            "product_1": {"overall": 65, "breakdown": breakdowns[1]},
        }
    }


class TestElectronicsUsesCategoryDimensionsLookup:
    """L1.3 — electronics joins the unified path. All 9 categories now
    flow through `_dim_from_category_lookup` so the v2 tab surfaces the
    same CATEGORY_DIMENSIONS-driven dim list regardless of category.
    """

    def test_electronics_includes_performance_dim(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "electronics")
        sr = _scoring_result(
            "electronics",
            (
                {
                    "performance_score": 88,
                    "value_score": 70,
                    "build_quality_score": 80,
                    "feature_score": 75,
                    "ecosystem_score": 60,
                    "futureproof_score": 65,
                },
                {
                    "performance_score": 70,
                    "value_score": 65,
                    "build_quality_score": 78,
                    "feature_score": 72,
                    "ecosystem_score": 55,
                    "futureproof_score": 60,
                },
            ),
        )
        dims = build_dimensions_v2(products, sr, category="electronics")
        keys = [d["key"] for d in dims]
        assert "performance" in keys
        perf = next(d for d in dims if d["key"] == "performance")
        assert perf["label"] == "Performance"
        assert perf["score_a"] == 88
        assert perf["score_b"] == 70
        # Suffix is stripped — frontend renders short key
        assert "performance_score" not in keys

    def test_electronics_drops_legacy_dpi_and_popularity_dims(self):
        """The Bundle D hand-coded `_dim_dpi` / `_dim_popularity` builders
        are no longer wired into v2 — their keys must not show up regardless
        of how rich the input products are."""
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "electronics")
        sr = _scoring_result(
            "electronics",
            (
                {"performance_score": 88, "build_quality_score": 80, "feature_score": 75},
                {"performance_score": 70, "build_quality_score": 78, "feature_score": 72},
            ),
        )
        dims = build_dimensions_v2(products, sr, category="electronics")
        keys = [d["key"] for d in dims]
        assert "dpi" not in keys
        assert "popularity" not in keys


class TestNonElectronicsUsesCategoryDimensionsLookup:
    def test_skincare_uses_category_dimensions_lookup(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("skincare", "skincare")
        sr = _scoring_result(
            "skincare",
            (
                {
                    "actives_score": 75,
                    "evidence_score": 80,
                    "skin_compat_score": 70,
                    "formulation_score": 60,
                    "sensory_score": 65,
                    "results_value_score": 55,
                },
                {
                    "actives_score": 65,
                    "evidence_score": 70,
                    "skin_compat_score": 75,
                    "formulation_score": 70,
                    "sensory_score": 60,
                    "results_value_score": 50,
                },
            ),
        )
        dims = build_dimensions_v2(products, sr, category="skincare")
        keys = [d["key"] for d in dims]
        # Core 3 always present
        assert "price" in keys
        assert "reviews" in keys
        assert "value" in keys
        # At least one skincare-specific dim is present (no `_score` suffix)
        skincare_dim_keys = {"actives", "evidence", "skin_compat", "formulation", "sensory"}
        assert any(k in skincare_dim_keys for k in keys), (
            f"Expected at least one skincare-specific dim in {keys}"
        )

    def test_supplements_pulls_efficacy_from_lookup(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("supplements", "supplements")
        sr = _scoring_result(
            "supplements",
            (
                {"efficacy_score": 80, "safety_score": 75, "dosage_score": 70},
                {"efficacy_score": 60, "safety_score": 80, "dosage_score": 65},
            ),
        )
        dims = build_dimensions_v2(products, sr, category="supplements")
        keys = [d["key"] for d in dims]
        assert "efficacy" in keys
        efficacy_dim = next(d for d in dims if d["key"] == "efficacy")
        assert efficacy_dim["score_a"] == 80
        assert efficacy_dim["score_b"] == 60
        assert efficacy_dim["label"] == "Efficacy"

    def test_skincare_skips_dim_with_missing_signals(self):
        """A.4.9 silent omission contract — when both products have None /
        MISSING_SCORE for a dim, the adapter returns None and the
        downstream filter drops the row."""
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("skincare", "skincare")
        sr = _scoring_result(
            "skincare",
            (
                {
                    "actives_score": None,  # both None → omitted
                    "evidence_score": 80,
                    "skin_compat_score": 70,
                },
                {
                    "actives_score": None,
                    "evidence_score": 70,
                    "skin_compat_score": 75,
                },
            ),
        )
        dims = build_dimensions_v2(products, sr, category="skincare")
        keys = [d["key"] for d in dims]
        assert "actives" not in keys, "missing-both-products dim must be omitted"
        assert any(k in {"evidence", "skin_compat"} for k in keys)


class TestCrossCategoryFallback:
    """When products are from different categories, only the core 3 dims
    ship — the category-lookup branch is skipped."""

    def test_cross_category_returns_only_core_dims(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "skincare")
        dims = build_dimensions_v2(products, scoring_result={}, category="electronics")
        # Only core 3 — no category extras
        assert {d["key"] for d in dims} == {"price", "reviews", "value"}


class TestLabelMap:
    """The label map covers all 9 categories x 6 dims grid (54 keys)."""

    def test_label_map_covers_all_category_dim_keys(self):
        from app.services.scoring_service import (
            CATEGORY_DIMENSIONS,
            _DIMENSION_LABELS,
        )

        all_dim_keys = set()
        for dims in CATEGORY_DIMENSIONS.values():
            all_dim_keys.update(dims)

        missing = all_dim_keys - set(_DIMENSION_LABELS.keys())
        assert not missing, f"Label map missing entries for: {missing}"


class TestBreakdownPathFix:
    """L1.3 — `_dim_from_category_lookup` must read
    `scores.product_i.breakdown[dim_key]` (live shape). Legacy fixtures
    that pre-date the breakdown wrap (flat `scores.product_i[dim_key]`)
    should still resolve."""

    def test_resolves_breakdown_nested_path(self):
        from app.services.scoring_service import _dim_from_category_lookup

        sr = {
            "scores": {
                "product_0": {"breakdown": {"longevity_score": 90}},
                "product_1": {"breakdown": {"longevity_score": 70}},
            }
        }
        dim = _dim_from_category_lookup("longevity_score", sr, products_data=None)
        assert dim is not None
        assert dim["key"] == "longevity"  # `_score` suffix stripped
        assert dim["score_a"] == 90
        assert dim["score_b"] == 70

    def test_resolves_flat_legacy_path(self):
        from app.services.scoring_service import _dim_from_category_lookup

        sr = {
            "scores": {
                "product_0": {"longevity_score": 90},
                "product_1": {"longevity_score": 70},
            }
        }
        dim = _dim_from_category_lookup("longevity_score", sr, products_data=None)
        assert dim is not None
        assert dim["key"] == "longevity"
        assert dim["score_a"] == 90
        assert dim["score_b"] == 70
