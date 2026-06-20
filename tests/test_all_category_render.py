"""All-9-category render audit (Task B2, Phase 1 — AUDIT-ONLY).

be-render-owned. $0 — pure deterministic / definition assertions, NO live API.

Pins the audit matrix in `docs/plans/2026-06-20-allcat-audit-matrix.md`:
  1. `compute_scores` breakdown keys == `CATEGORY_DIMENSIONS[cat]` (per-product
     category drives it — the line this bundle's write-back makes correct).
  2. `extract_specs`'s render filter + `build_category_profile` key off
     `CATEGORY_SPEC_SCHEMAS[cat]`, render in SCHEMA ORDER, with NO cross-category
     leakage.
  3. `CATEGORY_FAIRNESS[cat]` basis resolves (fashion/other → unit=None → no
     like-for-like caption).
  4. `build_dimensions_v2` routes same-category through `CATEGORY_DIMENSIONS[cat]`.

Plus a documenting test for **G1** (the one HIGH-severity gap found): the
subtype-prompt fields silently dropped by the category-schema filter. That test
ASSERTS the gap exists today (so it stays visible) and is marked so it flips to a
regression guard if/when G1 is fixed in a later bundle.

These tests are deliberately NON-MUTATING — they verify current behaviour and the
GREEN routing baseline; they do not require any shared-file edit.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.scoring_service import (
    CATEGORY_DIMENSIONS,
    CATEGORY_DIMENSION_WEIGHTS,
    ScoringService,
    build_dimensions_v2,
)
from app.services.extraction_service import (
    CATEGORY_SPEC_SCHEMAS,
    build_category_profile,
)
from app.services.price_service import CATEGORY_FAIRNESS, fairness_for_category
from app.services.product_type_router import (
    PRODUCT_TYPE_SCHEMAS,
    detect_product_type,
    get_schema_for_type,
)

ALL_CATEGORIES = [
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
]

# Categories whose fairness basis is a real comparable unit (a like-for-like
# caption renders). fashion/other deliberately have no comparable axis.
LIKE_FOR_LIKE_CATEGORIES = {
    "electronics", "grocery", "supplements", "makeup",
    "skincare", "haircare", "fragrances",
}
NO_BASIS_CATEGORIES = {"fashion", "other"}


def _pair(category: str):
    """A minimal explicit pair carrying the resolved per-product category."""
    p0 = {
        "brand": "BrandA", "name": "Prod A", "category": category,
        "price": {"amount": 100, "currency": "BHD"},
        "rating": 4.5, "review_count": 200, "specs": {},
    }
    p1 = {
        "brand": "BrandB", "name": "Prod B", "category": category,
        "price": {"amount": 120, "currency": "BHD"},
        "rating": 4.0, "review_count": 150, "specs": {},
    }
    return p0, p1


# ---------------------------------------------------------------------------
# Structural baseline — all 9 categories present + well-formed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_category_present_in_all_definition_tables(category):
    assert category in CATEGORY_DIMENSIONS
    assert category in CATEGORY_DIMENSION_WEIGHTS
    assert category in CATEGORY_SPEC_SCHEMAS
    assert category in CATEGORY_FAIRNESS


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_dims_are_six_with_weights_summing_to_one(category):
    dims = CATEGORY_DIMENSIONS[category]
    weights = CATEGORY_DIMENSION_WEIGHTS[category]
    assert len(dims) == 6
    assert set(dims) == set(weights.keys())
    assert round(sum(weights.values()), 4) == 1.0


# ---------------------------------------------------------------------------
# Matrix col 1 — compute_scores breakdown keys == CATEGORY_DIMENSIONS[cat]
# (the per-product `category` field drives this — the write-back target)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_compute_scores_breakdown_keys_match_category_dimensions(category):
    svc = ScoringService()
    p0, p1 = _pair(category)
    result = svc.compute_scores([p0, p1])
    expected = set(CATEGORY_DIMENSIONS[category])
    for pk in ("product_0", "product_1"):
        breakdown_keys = set(result["scores"][pk]["breakdown"].keys())
        assert breakdown_keys == expected, (
            f"{category}: breakdown {breakdown_keys} != dims {expected}"
        )


def test_compute_scores_capital_case_routes_correctly():
    """Keystone: a capital-cased per-product category still routes to its dims
    (not 'other'). Proves the write-back value can be capital-cased safely."""
    svc = ScoringService()
    p0, p1 = _pair("Fragrances")  # capital F
    result = svc.compute_scores([p0, p1])
    keys = set(result["scores"]["product_0"]["breakdown"].keys())
    assert "longevity_score" in keys and "projection_score" in keys
    assert "build_score" not in keys  # the 'other' tell must be absent


# ---------------------------------------------------------------------------
# Matrix col 4 — build_dimensions_v2 same-category routing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_build_dimensions_v2_routes_same_category(category):
    svc = ScoringService()
    p0, p1 = _pair(category)
    result = svc.compute_scores([p0, p1])
    dims_v2 = build_dimensions_v2([p0, p1], result, category)
    # 3 core (price/reviews/value) + contextual, capped at 8.
    assert 3 <= len(dims_v2) <= 8
    keys = [d.get("key") for d in dims_v2]
    assert keys[:3] == ["price", "reviews", "value"]
    if category not in ("other",):
        # A non-'other' category surfaces at least one of its own contextual dims
        # (i.e. it did NOT collapse to the generic price/reviews/value-only set).
        assert len(dims_v2) > 3, f"{category} collapsed to core-only dims"


# ---------------------------------------------------------------------------
# Matrix col 2/3 — spec schema render: schema order + NO cross-category leakage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_category_profile_schema_order_and_no_leakage(category):
    schema = CATEGORY_SPEC_SCHEMAS[category]
    # Populate the first 3 schema fields + inject 2 FOREIGN fields that must NOT render.
    foreign_pool = ["processor", "scent_family", "hair_type", "shade_range", "capacity_kg"]
    foreign = [f for f in foreign_pool if f not in schema][:2]
    specs = {schema[0]: "V0", schema[1]: "V1", schema[2]: "V2"}
    for f in foreign:
        specs[f] = "LEAK_" + f

    profile = build_category_profile(category, specs)
    rendered = [fld["key"] for fld in profile["fields"]]

    # No foreign field leaked through.
    assert not [k for k in rendered if k in foreign], f"{category} leaked {foreign}"
    # Rendered keys are a subset of the schema, in schema order.
    assert rendered == [k for k in schema if k in rendered]
    assert profile["category"] == category


def test_category_profile_canonicalizes_capital_case():
    profile = build_category_profile(
        "Fragrances",
        {"scent_family": "Woody", "notes_top": "Bergamot", "longevity": "8h"},
    )
    assert profile["category"] == "fragrances"
    assert [f["key"] for f in profile["fields"]] == ["scent_family", "notes_top", "longevity"]


def test_category_profile_unknown_falls_back_to_other():
    profile = build_category_profile("bogus_category", {"material": "Steel"})
    assert profile["category"] == "other"
    # 'material' is in the 'other' schema → renders.
    assert any(f["key"] == "material" for f in profile["fields"])


# ---------------------------------------------------------------------------
# Matrix col 5 — fairness basis (fashion/other → unit=None → no caption)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_fairness_basis_present_or_absent_per_design(category):
    spec = fairness_for_category(category)
    if category in LIKE_FOR_LIKE_CATEGORIES:
        assert spec["unit"] is not None, f"{category} should have a like-for-like unit"
    else:
        assert category in NO_BASIS_CATEGORIES
        assert spec["unit"] is None, f"{category} must have no comparable unit"


def test_fairness_canonicalizes_and_falls_back():
    assert fairness_for_category("Fragrances")["unit"] == "ml"
    assert fairness_for_category("FASHION")["unit"] is None
    # Unknown / None → the unit=None 'other' spec (safe passthrough).
    assert fairness_for_category("bogus")["unit"] is None
    assert fairness_for_category(None)["unit"] is None


# ---------------------------------------------------------------------------
# G1 (HIGH-severity gap) — DOCUMENTING test.
# The subtype prompt fields silently dropped by the category-schema filter.
# This test ASSERTS the gap exists today so it stays visible; if a later bundle
# fixes G1 (extract_specs filters on the subtype schema), this flips RED and
# becomes a prompt to convert it into a survival regression guard.
# ---------------------------------------------------------------------------

# Subtypes that today drop 100% of their prompt fields at the extract_specs filter.
_FULLY_DROPPED_SUBTYPES = [
    "electronics.tv", "electronics.ac", "electronics.washer",
    "electronics.refrigerator", "supplements.protein", "supplements.preworkout",
    "fashion.watch",
]


@pytest.mark.parametrize("type_key", _FULLY_DROPPED_SUBTYPES)
def test_G1_subtype_fields_fully_dropped_by_category_filter(type_key):
    """KNOWN GAP (audit G1): these subtypes' prompted fields share ZERO names
    with their category schema, so extract_specs strips all of them → empty
    Specs table. Documented in the audit matrix; deferral/scope is dispatcher's
    call. When fixed, this assertion flips and should become a survival guard."""
    category = type_key.split(".")[0]
    subtype_fields = set(get_schema_for_type(type_key))
    category_schema = set(CATEGORY_SPEC_SCHEMAS[category])
    survivors = subtype_fields & category_schema
    assert subtype_fields, f"{type_key} should have a subtype schema"
    assert not survivors, (
        f"G1 APPEARS FIXED for {type_key}: {survivors} now survive the filter — "
        f"convert this documenting test into a survival regression guard."
    )


def test_G1_fragrances_survive_enough_for_this_bundle():
    """Fragrances are the catfix DoD focus — confirm the fragrance render is
    adequate WITHOUT a G1 fix: scent_family + notes + sillage + concentration
    survive the category filter for the EDP/niche subtypes (the dropped
    longevity_hrs/volume_ml have category-schema equivalents longevity/volume).
    So G1 does NOT block this bundle for fragrances."""
    for type_key in ("fragrances.edp", "fragrances.niche"):
        subtype_fields = set(get_schema_for_type(type_key))
        survivors = subtype_fields & set(CATEGORY_SPEC_SCHEMAS["fragrances"])
        for must in ("scent_family", "notes_top", "notes_heart", "notes_base",
                     "sillage", "concentration"):
            assert must in survivors, f"{type_key}: {must} unexpectedly dropped"


def test_G1_real_query_detection_fires_subtype():
    """Sanity: detect_product_type actually fires the subtypes for real queries,
    so G1 is reachable in production (not a dead code path)."""
    assert detect_product_type("Sony Bravia QLED", "electronics") == "electronics.tv"
    assert detect_product_type("Omega Seamaster watch", "fashion") == "fashion.watch"
    assert detect_product_type("Optimum whey protein", "supplements") == "supplements.protein"
