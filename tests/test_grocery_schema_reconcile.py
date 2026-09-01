"""M18 PO-prompts-06 + PO-prompts-07 — grocery-schema reconciliation.

PO-prompts-06: CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE['grocery'] demanded
'weight', but CATEGORY_SPEC_SCHEMAS['grocery'] defines 'size' — so the
prompt never asks for 'weight', extract_specs' schema filter drops any
volunteered 'weight', and every cold grocery compare fires paid
Tier-2 (Serper+GPT) and Tier-3 (gpt-4o) chases for a field that can
never be filled. Fix: 'weight' -> 'size'. The fence tests here make the
whole drift class impossible for every category.

PO-prompts-07: the prod-default specs prompt (SPECS_SYSTEM_STATIC_PREFIX,
flag OFF) taught off-schema keys in its worked examples — Example 4
fragrance used a single 'notes' field (schema has only
notes_top/notes_heart/notes_base) and Example 6 skincare used
'volume_ml' (schema key is 'volume', which is NON-NEGOTIABLE for
skincare) — so a model imitating the examples emits keys the filter
silently drops, then the paid refill cascade re-buys the values. The
flag-ON EVIDENCE_ONLY_EXAMPLES copies were already corrected; these
tests pin the flag-OFF copies to the same schema keys.
"""
from __future__ import annotations

import re

from app.services.extraction_service import (
    CATEGORY_SPEC_SCHEMAS,
    CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE,
    CRITICAL_SCHEMA_FIELDS_PREFERRED,
    SPECS_SYSTEM_STATIC_PREFIX,
)


# ---------------------------------------------------------------------------
# PO-prompts-06 — the fence: every chased field must exist in its schema
# ---------------------------------------------------------------------------


def test_non_negotiable_fields_exist_in_category_schema():
    """Every NON_NEGOTIABLE field must be a member of its category's
    CATEGORY_SPEC_SCHEMAS list — otherwise Tier-2/Tier-3 pay to chase a
    field the prompt never requests and the filter always drops.
    RED at base: grocery lists 'weight' but the schema defines 'size'."""
    drift = {}
    for category, fields in CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE.items():
        schema = set(CATEGORY_SPEC_SCHEMAS.get(category, []))
        missing = [f for f in fields if f not in schema]
        if missing:
            drift[category] = missing
    assert not drift, (
        f"NON_NEGOTIABLE fields absent from their category schema "
        f"(unfillable paid chase): {drift}"
    )


def test_preferred_fields_exist_in_category_schema():
    """Same fence for the PREFERRED map (smart-fallback chases these)."""
    drift = {}
    for category, fields in CRITICAL_SCHEMA_FIELDS_PREFERRED.items():
        schema = set(CATEGORY_SPEC_SCHEMAS.get(category, []))
        missing = [f for f in fields if f not in schema]
        if missing:
            drift[category] = missing
    assert not drift, (
        f"PREFERRED fields absent from their category schema: {drift}"
    )


def test_grocery_non_negotiable_is_size_and_ingredients():
    """PO-prompts-06 direct pin: grocery chases 'size' (the schema key),
    never the off-schema 'weight'."""
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["grocery"]) == {
        "size", "ingredients",
    }


# ---------------------------------------------------------------------------
# PO-prompts-07 — prod-default worked examples must use schema keys
# ---------------------------------------------------------------------------


def test_prod_prompt_example4_uses_fragrance_note_pyramid_keys():
    """Example 4 (fragrance) must teach the schema's notes_top /
    notes_heart / notes_base, never a bare 'notes' key (aliased nowhere,
    dropped by the extract_specs filter)."""
    bare_notes_lines = re.findall(
        r"^\s*notes:\s", SPECS_SYSTEM_STATIC_PREFIX, flags=re.MULTILINE
    )
    assert not bare_notes_lines, (
        "prod-default prompt still teaches the off-schema 'notes' key"
    )
    for key in ("notes_top:", "notes_heart:", "notes_base:"):
        assert key in SPECS_SYSTEM_STATIC_PREFIX, (
            f"Example 4 should model the schema key {key!r}"
        )


def test_prod_prompt_example6_uses_schema_volume_key():
    """Example 6 (skincare) must teach 'volume' (NON-NEGOTIABLE for
    skincare), never 'volume_ml' (only a fragrance-subtype alias — for
    skincare the filter drops it and Tier-2/3 re-buy the value)."""
    volume_ml_lines = re.findall(
        r"^\s*volume_ml:\s", SPECS_SYSTEM_STATIC_PREFIX, flags=re.MULTILINE
    )
    assert not volume_ml_lines, (
        "prod-default prompt still teaches the off-schema 'volume_ml' key"
    )
    assert re.search(
        r'^\s*volume:\s*"500 ml"', SPECS_SYSTEM_STATIC_PREFIX, flags=re.MULTILINE
    ), "Example 6 should model the schema key 'volume'"
