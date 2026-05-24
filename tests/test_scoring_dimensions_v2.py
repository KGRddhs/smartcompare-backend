"""Bundle D Task 2.B.3 (A.8.1) — build_dimensions_v2 CATEGORY_DIMENSIONS adapter.

Reading 1 (minimal): electronics keeps the 3 hand-coded _dim_X builders
(fresh values from raw specs with category-specific delta_text). All
OTHER same-category pairs use the generic _dim_from_category_lookup
adapter driven by CATEGORY_DIMENSIONS + scoring_result["scores"].
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


class TestElectronicsKeepsHandCodedBuilders:
    """Reading 1 contract — electronics still uses _dim_dpi / _popularity /
    _build_quality so we don't regress the rich delta_text on the most
    common category.
    """

    def test_electronics_includes_dpi_dim_with_delta_text(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "electronics")
        dims = build_dimensions_v2(products, scoring_result={}, category="electronics")
        keys = [d["key"] for d in dims]
        assert "dpi" in keys
        dpi_dim = next(d for d in dims if d["key"] == "dpi")
        assert "DPI" in dpi_dim["delta_text"]
        assert dpi_dim["confidence"] == "high"

    def test_electronics_includes_popularity_dim(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "electronics")
        dims = build_dimensions_v2(products, scoring_result={}, category="electronics")
        assert any(d["key"] == "popularity" for d in dims)

    def test_electronics_does_NOT_use_generic_lookup(self):
        """Electronics should NOT pull dims from CATEGORY_DIMENSIONS lookup
        — that path is reserved for non-electronics categories."""
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "electronics")
        dims = build_dimensions_v2(products, scoring_result={}, category="electronics")
        keys = [d["key"] for d in dims]
        # Generic-lookup dim keys end in "_score" (CATEGORY_DIMENSIONS naming);
        # electronics hand-coded dims use shorter keys (dpi, popularity, build_quality)
        assert "performance_score" not in keys, (
            "electronics should NOT use generic CATEGORY_DIMENSIONS lookup"
        )


class TestNonElectronicsUsesGenericAdapter:
    """Reading 1 — non-electronics categories drive their 3 extra dims
    from CATEGORY_DIMENSIONS[category] + scoring_result['scores']."""

    def test_skincare_uses_category_dimensions_lookup(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("skincare", "skincare")
        scoring_result = {
            "scores": {
                "product_0": {
                    "actives_score": 75,
                    "evidence_score": 80,
                    "skin_compat_score": 70,
                    "formulation_score": 60,
                    "sensory_score": 65,
                    "results_value_score": 55,
                },
                "product_1": {
                    "actives_score": 65,
                    "evidence_score": 70,
                    "skin_compat_score": 75,
                    "formulation_score": 70,
                    "sensory_score": 60,
                    "results_value_score": 50,
                },
            }
        }
        dims = build_dimensions_v2(products, scoring_result, category="skincare")
        keys = [d["key"] for d in dims]
        # Core 3 always present
        assert "price" in keys
        assert "reviews" in keys
        assert "value" in keys
        # At least one skincare-specific dim is present
        skincare_dim_keys = {"actives_score", "evidence_score", "skin_compat_score", "formulation_score", "sensory_score"}
        assert any(k in skincare_dim_keys for k in keys), (
            f"Expected at least one skincare-specific dim in {keys}"
        )

    def test_supplements_pulls_efficacy_score_from_lookup(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("supplements", "supplements")
        scoring_result = {
            "scores": {
                "product_0": {"efficacy_score": 80, "safety_score": 75, "dosage_score": 70},
                "product_1": {"efficacy_score": 60, "safety_score": 80, "dosage_score": 65},
            }
        }
        dims = build_dimensions_v2(products, scoring_result, category="supplements")
        keys = [d["key"] for d in dims]
        assert "efficacy_score" in keys
        efficacy_dim = next(d for d in dims if d["key"] == "efficacy_score")
        assert efficacy_dim["score_a"] == 80
        assert efficacy_dim["score_b"] == 60
        assert efficacy_dim["label"] == "Efficacy"

    def test_skincare_skips_dim_with_missing_signals(self):
        """A.4.9 silent omission contract — when both products have None /
        MISSING_SCORE for a dim, the adapter returns None and the
        downstream filter drops the row."""
        from app.services.scoring_service import build_dimensions_v2, MISSING_SCORE

        products = _make_products("skincare", "skincare")
        scoring_result = {
            "scores": {
                "product_0": {
                    "actives_score": None,  # both None → omitted
                    "evidence_score": 80,
                    "skin_compat_score": 70,
                },
                "product_1": {
                    "actives_score": None,
                    "evidence_score": 70,
                    "skin_compat_score": 75,
                },
            }
        }
        dims = build_dimensions_v2(products, scoring_result, category="skincare")
        keys = [d["key"] for d in dims]
        assert "actives_score" not in keys, "missing-both-products dim must be omitted"
        # Other dims still present
        assert any(k in {"evidence_score", "skin_compat_score"} for k in keys)


class TestCrossCategoryFallback:
    """When products are from different categories, only the core 3 dims
    ship — neither hand-coded nor generic adapter runs."""

    def test_cross_category_returns_only_core_dims(self):
        from app.services.scoring_service import build_dimensions_v2

        products = _make_products("electronics", "skincare")
        dims = build_dimensions_v2(products, scoring_result={}, category="electronics")
        # Only core 3 — no DPI, no electronics extras
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
