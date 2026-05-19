"""Bundle C § 2f Step 1 — split CRITICAL_SCHEMA_FIELDS into non-negotiable
+ preferred layers.

Per design § 2f + plan A.4.6: the existing flat CRITICAL_SCHEMA_FIELDS
dict is split into two layers so the 3-tier spec fallback orchestration
(A.4.7 Tier 2, A.4.8 Tier 3) can target ONLY the non-negotiable fields
when chasing missing specs — the preferred layer is best-effort and
accepted-missing.

Per-category split per design § 2f table.

Backwards-compat: the legacy CRITICAL_SCHEMA_FIELDS export is preserved
as the union of non-negotiable + preferred so structured_comparison_service
smart-fallback (Tier 1) covers the same field set as before.
"""
import pytest

from app.services.extraction_service import (
    CRITICAL_SCHEMA_FIELDS,
    CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE,
    CRITICAL_SCHEMA_FIELDS_PREFERRED,
)


# ---------------------------------------------------------------------------
# Per-category non-negotiable + preferred sets per spec § 2f
# ---------------------------------------------------------------------------


def test_electronics_non_negotiable():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["electronics"]) == {
        "battery", "processor", "ram", "rear_camera",
    }


def test_electronics_preferred():
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["electronics"]) == {
        "front_camera", "water_resistance", "os", "weight",
    }


def test_supplements_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["supplements"]) == {
        "dosage", "form",
    }
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["supplements"]) == {
        "count", "serving_size", "active_ingredient",
    }


def test_fragrances_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["fragrances"]) == {
        "concentration", "longevity",
    }
    # Spec lists `notes_top/heart/base` as one entry — we split into three
    # discrete schema fields so the Tier 2 fallback can target each.
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["fragrances"]) == {
        "sillage", "notes_top", "notes_heart", "notes_base", "season",
    }


def test_fashion_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["fashion"]) == {"material"}
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["fashion"]) == {
        "origin", "style", "closure_type", "care_instructions",
    }


def test_skincare_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["skincare"]) == {
        "volume", "ingredients",
    }
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["skincare"]) == {
        "skin_type", "active_ingredient", "spf",
    }


def test_haircare_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["haircare"]) == {
        "volume", "ingredients",
    }
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["haircare"]) == {
        "hair_type", "scent", "sulfate_free",
    }


def test_makeup_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["makeup"]) == {
        "volume", "shade_range",
    }
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["makeup"]) == {
        "finish", "coverage", "cruelty_free", "spf",
    }


def test_grocery_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["grocery"]) == {
        "weight", "ingredients",
    }
    # Spec lists `nutrition_*` — we use the discrete schema keys.
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["grocery"]) == {
        "nutrition_protein", "nutrition_calories", "nutrition_fat",
        "nutrition_carbs", "origin", "organic",
    }


def test_other_split_has_no_non_negotiables():
    # Spec § 2f: 'other' category has no non-negotiables; all preferred.
    assert CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE.get("other", []) == []


# ---------------------------------------------------------------------------
# Backwards-compat — legacy CRITICAL_SCHEMA_FIELDS is the union per category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", [
    "electronics", "supplements", "fragrances", "fashion",
    "skincare", "haircare", "makeup", "grocery", "other",
])
def test_legacy_critical_fields_is_union(category):
    """The flat CRITICAL_SCHEMA_FIELDS export remains valid — it's the
    union of non-negotiable + preferred so smart-fallback Tier 1
    (currently driven from this list) keeps targeting the same field
    set as before A.4.6."""
    union = set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE.get(category, [])) | set(
        CRITICAL_SCHEMA_FIELDS_PREFERRED.get(category, [])
    )
    assert set(CRITICAL_SCHEMA_FIELDS.get(category, [])) == union, (
        f"{category}: CRITICAL_SCHEMA_FIELDS != non_negotiable ∪ preferred"
    )


def test_no_field_appears_in_both_layers():
    """A field is either non-negotiable OR preferred — never both."""
    for category in CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE:
        nn = set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE[category])
        pref = set(CRITICAL_SCHEMA_FIELDS_PREFERRED.get(category, []))
        overlap = nn & pref
        assert not overlap, (
            f"{category}: fields appear in both layers: {overlap}"
        )
