"""Bundle-next #15 — 2nd-product CategoryProfile extraction DEPTH.

Prod fixtures show per-product extraction-depth VARIANCE: on makeup the 2nd
product (L'Oreal) populated 4 fields vs the 1st (Maybelline) 7 — not the F3.1
blank-symmetry bug (both use the same schema), but the model under-extracting the
fields each product's search context DOES contain. Root cause: _build_specs_prompt's
CATEGORY-SPECIFIC GUIDANCE only directed 4 of 9 categories (electronics/fashion/
supplements/fragrances) — makeup/skincare/haircare/grocery/other got NO
field-seeking guidance, so the model left targetable fields null.

Fix: per-category guidance for ALL 9 categories so the model actively seeks each
category's REAL schema fields from BOTH products' contexts (lifts the thinner
side). This is data-availability bounded — guidance says "include when present",
NEVER "always fill". The two assertions the dispatcher required:
  (a) guidance covers all 9 categories + references real schema fields, AND
  (b) the no-fabrication invariant still holds (omit-when-absent + _source).
"""

import pytest

from app.services.extraction_service import (
    _build_specs_prompt,
    CATEGORY_SPEC_SCHEMAS,
    SPECS_SYSTEM_STATIC_PREFIX,
)

_NINE = [
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
]


def _system_for(category: str) -> str:
    return _build_specs_prompt("Brand", "Model", "", category, "ctx").get("system", "")


def _guidance_block(category: str) -> str:
    """ONLY the CATEGORY-SPECIFIC GUIDANCE block (lowercased) — so field-name
    assertions can't false-pass on the schema list / extraction examples
    elsewhere in the system prompt."""
    sys = _system_for(category)
    # Match the header tolerant of a parenthetical suffix after "GUIDANCE".
    if "CATEGORY-SPECIFIC GUIDANCE" not in sys:
        return ""
    block = sys.split("CATEGORY-SPECIFIC GUIDANCE", 1)[1]
    # Stop at the drug-database section / user prompt if present.
    for stop in ("BAHRAIN DRUG DATABASE", "<USER_INPUT>", "SEARCH CONTEXT:"):
        block = block.split(stop, 1)[0]
    return block.lower()


# ----------------------------------- (a) guidance covers all 9 categories ---

class TestGuidanceCoversAllNine:
    @pytest.mark.parametrize("category", _NINE)
    def test_guidance_mentions_category(self, category):
        # Each category gets a dedicated guidance LINE inside the guidance block.
        block = _guidance_block(category)
        assert block, "CATEGORY-SPECIFIC GUIDANCE block missing"
        assert category in block, f"no per-category guidance line for {category}"

    @pytest.mark.parametrize("category", ["makeup", "skincare", "haircare", "grocery"])
    def test_previously_missing_categories_now_have_guidance(self, category):
        # These 4 had NO guidance line before (the gap). The guidance block must
        # now name the category AND reference >=2 of its real schema fields, so
        # the model knows WHICH fields to seek from each product's context.
        block = _guidance_block(category)
        schema = CATEGORY_SPEC_SCHEMAS[category]
        hits = [f for f in schema if f.replace("_", " ") in block or f in block]
        assert len(hits) >= 2, f"{category} guidance references <2 schema fields: {hits}"

    def test_makeup_guidance_targets_the_gap_fields(self):
        # The prod gap was the 2nd makeup product missing skin_type/vegan/spf.
        # Guidance should name the makeup depth fields so they're sought for BOTH.
        block = _guidance_block("makeup")
        targets = ["finish", "coverage", "skin", "spf", "shade", "vegan", "cruelty"]
        present = [t for t in targets if t in block]
        assert len(present) >= 3, f"makeup guidance too thin: {present}"


# ------------------------------- (b) no-fabrication invariant preserved ---

class TestNoFabricationPreserved:
    def test_omit_when_genuinely_absent_rule_present(self):
        # The static prefix's no-fabrication rule MUST still be present (the
        # added field-seeking guidance must not override it).
        low = SPECS_SYSTEM_STATIC_PREFIX.lower()
        assert "only return null" in low and "genuinely don't know" in low

    def test_source_marker_requirement_present(self):
        # The _source accountability marker (snippet_N | training) is the
        # anti-fabrication mechanism — must remain.
        low = SPECS_SYSTEM_STATIC_PREFIX.lower()
        assert "_source" in low
        assert "snippet" in low and "training" in low

    @pytest.mark.parametrize("category", _NINE)
    def test_guidance_does_not_demand_fabrication(self, category):
        # The per-category guidance must NOT say "always fill" / "never leave
        # blank" / "make up" — it directs WHICH fields to SEEK, not to invent.
        block = _guidance_block(category)
        for bad in ["always fill", "never leave blank", "make up", "fabricate",
                    "fill every field", "guess the"]:
            assert bad not in block, f"{category} guidance tempts fabrication: '{bad}'"

    def test_na_literal_still_forbidden(self):
        # "NEVER return the literal string 'N/A'" rule preserved (FE filters N/A,
        # but the prompt forbidding it keeps the payload clean).
        low = SPECS_SYSTEM_STATIC_PREFIX.lower()
        assert "n/a" in low  # the forbidding rule mentions it


# ----------------------------------------- symmetry: same schema both sides ---

class TestSymmetricSchemaTargeting:
    @pytest.mark.parametrize("category", _NINE)
    def test_same_schema_fields_for_any_product(self, category):
        # Two different products in the same category get the IDENTICAL schema in
        # their prompt (depth comes from context, not asymmetric targeting).
        s1 = _build_specs_prompt("Maybelline", "Fit Me", "", category, "ctx-A")["system"]
        s2 = _build_specs_prompt("L'Oreal", "True Match", "", category, "ctx-B")["system"]
        # The REQUIRED SCHEMA block (the field list) is identical across products.
        def _schema_block(s):
            return s.split("REQUIRED SCHEMA:", 1)[1].split("CATEGORY-SPECIFIC", 1)[0]
        assert _schema_block(s1) == _schema_block(s2)
