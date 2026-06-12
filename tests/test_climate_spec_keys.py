"""Tests for S2 I2.4 — Gulf-climate `heat_stability` spec key.

H8 (dossier §2): 7/82 winner-fails carry a Gulf-climate rationale
("shine control lasts well through humid days"). The verdict needs a spec
signal it can reference. We add `heat_stability` to the makeup / skincare /
fragrances schemas — BOTH the category-level CATEGORY_SPEC_SCHEMAS list AND
the PRODUCT_TYPE_SCHEMAS subtypes (the subtype path overrides the category
list for nearly every real query, so a category-only key would be dead).

NO new scoring dimension is created — deterministic scoring is untouched.
The key is extraction signal + verdict-prompt awareness only.
"""

from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
from app.services.product_type_router import (
    PRODUCT_TYPE_SCHEMAS,
    detect_product_type,
    get_schema_for_type,
)

CLIMATE_KEY = "heat_stability"
CLIMATE_CATEGORIES = ("makeup", "skincare", "fragrances")


def test_heat_stability_in_category_schemas():
    for cat in CLIMATE_CATEGORIES:
        assert CLIMATE_KEY in CATEGORY_SPEC_SCHEMAS[cat], (
            f"{CLIMATE_KEY} missing from CATEGORY_SPEC_SCHEMAS[{cat!r}]"
        )


def test_heat_stability_not_in_other_categories():
    """Climate key is scoped to the three heat-sensitive beauty categories —
    it must NOT leak into electronics/grocery/etc."""
    for cat in ("electronics", "grocery", "supplements", "fashion", "haircare", "other"):
        assert CLIMATE_KEY not in CATEGORY_SPEC_SCHEMAS[cat]


def test_heat_stability_in_relevant_subtype_schemas():
    """The subtype path overrides the category list — so the key must be in
    the makeup/skincare/fragrances subtypes too, else it never extracts."""
    expected_subtypes = [
        k for k in PRODUCT_TYPE_SCHEMAS
        if k.split(".", 1)[0] in CLIMATE_CATEGORIES
    ]
    assert expected_subtypes  # sanity: there ARE such subtypes
    for st in expected_subtypes:
        assert CLIMATE_KEY in PRODUCT_TYPE_SCHEMAS[st], (
            f"{CLIMATE_KEY} missing from PRODUCT_TYPE_SCHEMAS[{st!r}]"
        )


def test_real_query_resolves_schema_with_climate_key():
    """End-to-end: a typical foundation / serum / EDP query resolves to a
    subtype schema that includes heat_stability."""
    cases = [
        ("Maybelline Fit Me Foundation", "makeup"),
        ("The Ordinary Niacinamide Serum", "skincare"),
        ("Dior Sauvage Eau de Parfum", "fragrances"),
    ]
    for name, cat in cases:
        type_key = detect_product_type(name, cat)
        fields = get_schema_for_type(type_key)
        assert CLIMATE_KEY in fields, (
            f"{name!r} -> {type_key!r} schema lacks {CLIMATE_KEY}"
        )


def test_heat_stability_not_in_unrelated_subtypes():
    for st, fields in PRODUCT_TYPE_SCHEMAS.items():
        if st.split(".", 1)[0] in CLIMATE_CATEGORIES:
            continue
        assert CLIMATE_KEY not in fields, f"{CLIMATE_KEY} leaked into {st!r}"
