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
    # S2 I3.6 (Decision B, 2026-06-11): active_ingredient promoted
    # preferred → NON-NEGOTIABLE. The active ingredient (e.g. "Probiotic",
    # "Vitamin C") is the single most defining spec for a supplement, and
    # the gold set anchors on it — promoting it routes it into the
    # Tier-2/Tier-3 fallback `missing` list so a blank Tier-1 extraction is
    # filled rather than left at specs_score=0.0 (supp-010 root cause).
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["supplements"]) == {
        "dosage", "form", "active_ingredient",
    }
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["supplements"]) == {
        "count", "serving_size",
    }


def test_fragrances_split():
    # B1 invariant: NON_NEGOTIABLE stays byte-stable {concentration, longevity}.
    # scent_family is added to PREFERRED only (rides the existing batched
    # _smart_fallback_extract — NOT the per-field Serper+GPT NON_NEGOTIABLE
    # fan-out), so it must NOT appear in the non-negotiable set.
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["fragrances"]) == {
        "concentration", "longevity",
    }
    assert "scent_family" not in CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["fragrances"]
    # Spec lists `notes_top/heart/base` as one entry — we split into three
    # discrete schema fields so the Tier 2 fallback can target each. B1 adds
    # scent_family (the single most defining fragrance trait after concentration).
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["fragrances"]) == {
        "scent_family", "sillage", "notes_top", "notes_heart", "notes_base", "season",
    }


def test_fashion_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["fashion"]) == {"material"}
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["fashion"]) == {
        "origin", "style", "closure_type", "care_instructions",
    }


def test_skincare_split():
    # S2 I3.6 (Decision B, 2026-06-11): active_ingredient promoted
    # preferred → NON-NEGOTIABLE. The active (e.g. "Vitamin C", "Retinol")
    # is the defining spec a skincare buyer compares on, and the gold set
    # anchors on it — promotion routes it into the Tier-2/Tier-3 fallback
    # `missing` list (skin-012 root cause: specs_score=0.0 because Tier-1
    # left active_ingredient blank and the fallback never targeted it).
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["skincare"]) == {
        "volume", "ingredients", "active_ingredient",
    }
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["skincare"]) == {
        "skin_type", "spf",
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


# ---------------------------------------------------------------------------
# S2 I3.6 — coverage-math invariant (dispatcher condition for the
# active_ingredient promotion): _product_spec_coverage MUST be unaffected by
# the non-negotiable promotion. It counts filled spec VALUES against
# _EXPECTED_SPEC_FIELD_COUNT[category] — it never reads the non-negotiable
# set — so promoting active_ingredient preferred→non-negotiable cannot move
# the weird-classifier coverage ratio. This pins that property so a future
# edit that wires the non-negotiable set into coverage would fail loudly.
# ---------------------------------------------------------------------------

def test_product_spec_coverage_unaffected_by_promotion():
    from app.services.structured_comparison_service import (
        _product_spec_coverage,
        _EXPECTED_SPEC_FIELD_COUNT,
    )

    # A supplements product with active_ingredient filled + one other field.
    supp = {
        "category": "supplements",
        "specs": {"active_ingredient": "Probiotic", "dosage": "10B CFU"},
    }
    filled, expected = _product_spec_coverage(supp)
    # 2 non-empty values; expected = the category's _EXPECTED count (NOT the
    # non-negotiable list length, which active_ingredient just joined).
    assert filled == 2, f"expected 2 filled values, got {filled}"
    assert expected == _EXPECTED_SPEC_FIELD_COUNT["supplements"], (
        "coverage denominator must be _EXPECTED_SPEC_FIELD_COUNT, NOT the "
        f"non-negotiable set — got {expected}"
    )

    # Same property for skincare (the other promoted category).
    skin = {
        "category": "skincare",
        "specs": {"active_ingredient": "Vitamin C", "volume": "30ml", "spf": "30"},
    }
    filled_s, expected_s = _product_spec_coverage(skin)
    assert filled_s == 3
    assert expected_s == _EXPECTED_SPEC_FIELD_COUNT["skincare"]

    # And the denominator is byte-stable across categories regardless of how
    # many fields are now non-negotiable (proves the decoupling explicitly).
    assert _EXPECTED_SPEC_FIELD_COUNT["supplements"] == 5
    assert _EXPECTED_SPEC_FIELD_COUNT["skincare"] == 5
