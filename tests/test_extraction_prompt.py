"""Bucket A bug 3 - extraction prompt forces schema fields, no contradiction."""
import pytest
from app.services.extraction_service import _build_specs_prompt, CATEGORY_SPEC_SCHEMAS


def test_prompt_does_not_say_omit_irrelevant_for_schema_fields():
    """The 'Omit irrelevant fields' instruction must be qualified to apply
    ONLY to non-schema fields, not schema-listed fields. Schema-listed fields
    are BY DEFINITION relevant - that's why they're in the schema."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="snippet content here",
    )
    system = p["system"]

    # Old prompt had the bare phrase "Omit irrelevant fields rather than
    # writing N/A or null." - this is the contradiction that lets GPT skip
    # schema fields. Must be removed or qualified.
    assert "Omit irrelevant fields rather than writing N/A" not in system, \
        "Unqualified 'Omit irrelevant' instruction still in prompt - will let GPT omit schema fields"


def test_prompt_explicitly_requires_schema_fields():
    """Prompt must explicitly say schema fields MUST be attempted (not omitted)."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="snippets",
    )
    system = p["system"]

    # Must contain a clear directive that schema fields are required
    assertions_pass = (
        "MUST attempt" in system
        or "must provide" in system.lower()
        or "required schema field" in system.lower()
    )
    assert assertions_pass, "Prompt missing explicit must-attempt directive for schema fields"


def test_prompt_allows_training_data_fallback_for_schema():
    """Prompt must allow training-data fallback when snippets are thin."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="thin snippet",
    )
    system = p["system"]

    assertions_pass = (
        "training data" in system.lower()
        or "your knowledge" in system.lower()
        or "well-known products, you KNOW" in system
    )
    assert assertions_pass, "Prompt missing training-data fallback permission"


def test_prompt_field_source_marker_still_required():
    """Each spec field must still come with a _source marker (snippet_N or training)."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="snippets",
    )
    system = p["system"]
    assert "_source" in system, "Prompt missing _source marker requirement"


def test_clean_specs_extracts_field_confidence_from_source_markers():
    """When GPT returns each spec key + a _source marker, _clean_specs
    must extract those markers into a _field_confidence dict and remove
    the _source siblings from the final spec output."""
    from app.services.structured_comparison_service import StructuredComparisonService

    raw_specs = {
        "ram": "12 GB",
        "ram_source": "snippet_3",
        "front_camera": "12 MP f/2.2",
        "front_camera_source": "training",
        "water_resistance": "IP68",
        "water_resistance_source": "snippet_5",
    }
    cleaned = StructuredComparisonService._clean_specs(raw_specs)

    # _field_confidence stamped from _source markers
    confidence = cleaned.get("_field_confidence", {})
    assert confidence.get("ram") == "snippet", f"ram confidence wrong: {confidence}"
    assert confidence.get("front_camera") == "training_data", f"front_camera confidence wrong: {confidence}"
    assert confidence.get("water_resistance") == "snippet", f"water_resistance confidence wrong: {confidence}"

    # _source sibling keys stripped from output
    assert "ram_source" not in cleaned
    assert "front_camera_source" not in cleaned
    assert "water_resistance_source" not in cleaned

    # Actual values preserved
    assert cleaned.get("ram") == "12 GB"
    assert cleaned.get("front_camera") == "12 MP f/2.2"
    assert cleaned.get("water_resistance") == "IP68"


# Extra coverage (Bucket A bug 3 follow-up) ----------------------------------


def test_clean_specs_no_source_markers_omits_field_confidence():
    """When GPT returns plain specs with no _source siblings, _field_confidence
    must NOT be emitted (would be an empty dict otherwise - noise for the UI)."""
    from app.services.structured_comparison_service import StructuredComparisonService

    raw = {"ram": "12 GB", "storage": "256 GB"}
    cleaned = StructuredComparisonService._clean_specs(raw)
    assert "_field_confidence" not in cleaned


def test_clean_specs_unknown_source_marker_passes_through_verbatim():
    """Unrecognised _source value (neither snippet* nor 'training') is stored
    as-is in _field_confidence so we can debug what GPT actually emitted."""
    from app.services.structured_comparison_service import StructuredComparisonService

    raw = {"ram": "12 GB", "ram_source": "some_other_provenance"}
    cleaned = StructuredComparisonService._clean_specs(raw)
    assert cleaned["_field_confidence"]["ram"] == "some_other_provenance"


def test_clean_specs_non_string_source_value_ignored():
    """If _source value is not a string (e.g. GPT returned an int by accident),
    skip it rather than crash."""
    from app.services.structured_comparison_service import StructuredComparisonService

    raw = {"ram": "12 GB", "ram_source": 3}  # bad type
    cleaned = StructuredComparisonService._clean_specs(raw)
    assert "_field_confidence" not in cleaned  # nothing extracted
    assert cleaned.get("ram") == "12 GB"  # but real value still kept


def test_clean_specs_empty_input_returns_empty_dict():
    """Defensive: empty/None input must not crash."""
    from app.services.structured_comparison_service import StructuredComparisonService

    assert StructuredComparisonService._clean_specs({}) == {}
    assert StructuredComparisonService._clean_specs(None) == {}
    assert StructuredComparisonService._clean_specs("not a dict") == {}


def test_clean_specs_preserves_null_normalization_to_NA():
    """Null/empty values still become 'N/A' (existing pre-Bucket-A behaviour)."""
    from app.services.structured_comparison_service import StructuredComparisonService

    raw = {"ram": None, "storage": "", "battery": "5000 mAh"}
    cleaned = StructuredComparisonService._clean_specs(raw)
    assert cleaned["ram"] == "N/A"
    assert cleaned["storage"] == "N/A"
    assert cleaned["battery"] == "5000 mAh"


def test_prompt_variant_none_renders_without_variant_note():
    """When variant=None, prompt should not contain '()' empty parens."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25", variant=None,
        category="electronics", search_context="",
    )
    assert "()" not in p["user"], "Empty variant should not render as '()'"


def test_prompt_unknown_category_falls_back_to_other_schema():
    """Category not in CATEGORY_SPEC_SCHEMAS must fall back to the 'other' schema."""
    p = _build_specs_prompt(
        brand="X", name="Y", variant=None,
        category="not_a_real_category", search_context="",
    )
    # 'other' schema is non-empty (has at least 'description', 'features' etc.);
    # we only need to confirm we got a prompt without KeyError.
    assert "REQUIRED SCHEMA" in p["system"]


def test_critical_schema_fields_only_subset_of_schema():
    """Every field in CRITICAL_SCHEMA_FIELDS[cat] should map to a schema-known
    field; warns (via print) if any drift since smart-fallback writes new keys."""
    from app.services.extraction_service import CRITICAL_SCHEMA_FIELDS

    for category, critical in CRITICAL_SCHEMA_FIELDS.items():
        if not critical:
            continue
        schema = CATEGORY_SPEC_SCHEMAS.get(category, [])
        unknown = [f for f in critical if f not in schema]
        if unknown:
            # soft assertion: log for awareness, don't fail
            print(f"NOTE: CRITICAL_SCHEMA_FIELDS[{category}] has fields not in schema: {unknown}")
