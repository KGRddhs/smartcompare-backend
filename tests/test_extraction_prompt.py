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
