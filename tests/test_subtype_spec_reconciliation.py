"""Issue #59 â€” subtype spec keys must land in their canonical homes.

``_build_specs_prompt`` asks GPT for the SUBTYPE field list
(``PRODUCT_TYPE_SCHEMAS``), but ``extract_specs`` cleans the response against the
CATEGORY list (``CATEGORY_SPEC_SCHEMAS``). Every subtype-named key the model was
told to fill was therefore dropped and its canonical home stamped ``"N/A"`` â€”
which then fired the paid smart-fallback / Tier-2 / Tier-3 refill cascade on a
field the model had already answered.

Only fragrances had a reconciliation (two aliases). These tests pin the
generalised version, and pin that fragrance behavior is unchanged.

They also pin the second half: a category non-negotiable that a subtype genuinely
cannot have (a TV has no battery or rear camera) must not be chased by the paid
cascade at all.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import extraction_service
from app.services.extraction_service import (
    CATEGORY_SPEC_SCHEMAS,
    CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE,
    SUBTYPE_SPEC_ALIASES,
    extract_specs,
    non_negotiable_fields_for,
)
from app.services.product_type_router import PRODUCT_TYPE_SCHEMAS


def _mock_openai_returning(payload: dict):
    """Build a client whose completion returns exactly ``payload`` as JSON.

    ``extract_specs`` resolves its client through ``get_client()``, so tests
    patch that rather than the module-level ``client`` singleton.
    """
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    # Plain ints, not MagicMocks â€” the cache-telemetry helper compares these.
    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 50
    usage.total_tokens = 150
    usage.prompt_tokens_cached = 0
    usage.prompt_tokens_details = None
    response.usage = usage

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


class TestAliasMapIntegrity:
    """The map must reference only real keys on both sides â€” a typo here
    silently reintroduces the bug it exists to fix."""

    def test_every_subtype_key_exists_in_the_router(self):
        unknown = sorted(set(SUBTYPE_SPEC_ALIASES) - set(PRODUCT_TYPE_SCHEMAS))
        assert not unknown, f"alias table names subtypes that do not exist: {unknown}"

    def test_alias_sources_are_fields_the_subtype_prompt_actually_asks_for(self):
        bad = []
        for subtype, aliases in SUBTYPE_SPEC_ALIASES.items():
            asked = set(PRODUCT_TYPE_SCHEMAS[subtype])
            for alias_key in aliases:
                if alias_key not in asked:
                    bad.append(f"{subtype}.{alias_key}")
        assert not bad, f"alias sources the prompt never requests: {bad}"

    def test_alias_targets_are_canonical_fields_of_that_category(self):
        bad = []
        for subtype, aliases in SUBTYPE_SPEC_ALIASES.items():
            category = subtype.split(".", 1)[0]
            canonical = set(CATEGORY_SPEC_SCHEMAS.get(category, []))
            for alias_key, canonical_key in aliases.items():
                if canonical_key not in canonical:
                    bad.append(f"{subtype}.{alias_key} -> {canonical_key}")
        assert not bad, f"alias targets that are not canonical fields: {bad}"


class TestSubtypeValuesReachCanonicalFields:
    """The core defect: a value GPT returned under its subtype name must not be
    thrown away."""

    @pytest.mark.asyncio
    async def test_skincare_serum_hero_active_becomes_active_ingredient(self):
        payload = {
            "brand": "CeraVe", "model": "Resurfacing Retinol Serum", "variant": None,
            "category": "skincare",
            "hero_active": "Retinol",
            "vol_ml": "30",
        }
        with patch.object(extraction_service, "get_client", return_value=_mock_openai_returning(payload)):
            specs, _usage = await extract_specs("CeraVe", "Resurfacing Retinol Serum", None, "skincare", "search context")
        assert specs["active_ingredient"] == "Retinol"
        assert specs["volume"] == "30"

    @pytest.mark.asyncio
    async def test_makeup_foundation_shade_range_count_becomes_shade_range(self):
        payload = {
            "brand": "Fenty", "model": "Pro Filt'r Foundation", "variant": None,
            "category": "makeup",
            "shade_range_count": "50 shades",
            "vol_ml": "32",
        }
        with patch.object(extraction_service, "get_client", return_value=_mock_openai_returning(payload)):
            specs, _usage = await extract_specs("Fenty", "Pro Filt'r Foundation", None, "makeup", "search context")
        assert specs["shade_range"] == "50 shades"
        assert specs["volume"] == "32"

    @pytest.mark.asyncio
    async def test_supplements_vitamin_dose_becomes_dosage(self):
        payload = {
            "brand": "Nature Made", "model": "Vitamin D3 1000 IU", "variant": None,
            "category": "supplements",
            "dose_iu_mcg": "1000 IU",
            "form": "Softgel",
        }
        with patch.object(extraction_service, "get_client", return_value=_mock_openai_returning(payload)):
            specs, _usage = await extract_specs("Nature Made", "Vitamin D3 1000 IU", None, "supplements", "search context")
        assert specs["dosage"] == "1000 IU"
        assert specs["form"] == "Softgel"


class TestFragranceBehaviorUnchanged:
    """The pre-existing two-entry fragrance reconciliation must survive
    generalisation byte-for-byte in effect."""

    @pytest.mark.asyncio
    async def test_fragrance_aliases_still_map(self):
        payload = {
            "brand": "Dior", "model": "Sauvage", "variant": None, "category": "fragrances",
            "longevity_hrs": "8",
            "volume_ml": "100",
        }
        with patch.object(extraction_service, "get_client", return_value=_mock_openai_returning(payload)):
            specs, _usage = await extract_specs("Dior", "Sauvage", None, "fragrances", "search context")
        assert specs["longevity"] == "8"
        assert specs["volume"] == "100"

    @pytest.mark.asyncio
    async def test_canonical_value_wins_over_alias(self):
        """If GPT emitted BOTH, the canonical one stays authoritative."""
        payload = {
            "brand": "Dior", "model": "Sauvage", "variant": None, "category": "fragrances",
            "longevity": "10 hours",
            "longevity_hrs": "8",
        }
        with patch.object(extraction_service, "get_client", return_value=_mock_openai_returning(payload)):
            specs, _usage = await extract_specs("Dior", "Sauvage", None, "fragrances", "search context")
        assert specs["longevity"] == "10 hours"

    @pytest.mark.asyncio
    async def test_blank_alias_does_not_overwrite(self):
        payload = {
            "brand": "Dior", "model": "Sauvage", "variant": None, "category": "fragrances",
            "longevity": "10 hours",
            "longevity_hrs": "",
        }
        with patch.object(extraction_service, "get_client", return_value=_mock_openai_returning(payload)):
            specs, _usage = await extract_specs("Dior", "Sauvage", None, "fragrances", "search context")
        assert specs["longevity"] == "10 hours"


class TestInapplicableNonNegotiables:
    """A TV has no battery, processor, RAM or rear camera. Chasing those through
    the paid Tier-2/Tier-3 cascade burns Serper credits and a gpt-4o call on a
    spec that cannot exist."""

    def test_tv_drops_the_inapplicable_electronics_non_negotiables(self):
        fields = non_negotiable_fields_for("electronics", "electronics.tv")
        for impossible in ("battery", "processor", "ram", "rear_camera"):
            assert impossible not in fields

    def test_phone_keeps_every_electronics_non_negotiable(self):
        fields = non_negotiable_fields_for("electronics", "electronics.phone")
        assert set(fields) == set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["electronics"])

    def test_unknown_subtype_falls_back_to_the_category_list(self):
        fields = non_negotiable_fields_for("electronics", "electronics.default")
        assert set(fields) == set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["electronics"])

    def test_none_subtype_falls_back_to_the_category_list(self):
        fields = non_negotiable_fields_for("skincare", None)
        assert set(fields) == set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["skincare"])

    def test_override_never_invents_a_field(self):
        """An override may only REMOVE fields, never add ones the cascade would
        then chase without a schema home."""
        for category, base in CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE.items():
            for subtype in [k for k in PRODUCT_TYPE_SCHEMAS if k.startswith(f"{category}.")]:
                resolved = non_negotiable_fields_for(category, subtype)
                assert set(resolved) <= set(base), (
                    f"{subtype} resolved a non-negotiable outside the category list"
                )
