"""UNIT A3 (U0.3) - the no-fabrication guard for specs (ENABLE_SPECS_NO_FABRICATION).

MEASURED DEFECT: the specs system prompt ORDERS the model to fall back to its
training data when the Serper snippet digest is thin, and `extract_specs` caches
the result for 7 days. Reviews are already guarded (REVIEWS_EXTRACTION_SYSTEM:
"If you cannot cite a snippet, do NOT include the claim") and go EMPTY instead;
only SPECS are fabricated.

These tests pin all three arms of the flag:

  (a) flag ON + empty/thin search context  -> nothing fabricated; unsupported
      schema fields are OMITTED (never stamped "N/A") and the specs dict is
      marked evidence-limited via the internal `_evidence_limited` marker.
  (b) flag ON + rich snippets              -> specs extracted normally, pinned
      against the RECORDED Serper digest in
      tests/fixtures/serper_oudwood_organic.json.
  (c) flag OFF                             -> the prompt is byte-identical to
      main, including the exact training-data-fallback substring that lives at
      extraction_service.py:515-516.

No live OpenAI calls anywhere here (the key 429s) - every test goes through
prompt construction or a mocked completion.
"""
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import extraction_service
from app.services.extraction_service import (
    CATEGORY_SPEC_SCHEMAS,
    SPECS_SYSTEM_STATIC_PREFIX,
    _build_specs_prompt,
    extract_specs,
)

FIXTURES = Path(__file__).parent / "fixtures"

# The EXACT rule pair that lives at app/services/extraction_service.py:515-516.
# This is the defect: line two ORDERS the training-data fallback.
MAIN_TRAINING_FALLBACK_RULES = (
    "- For fields explicitly listed in the schema below, you MUST attempt to "
    "provide a value. These fields are required for the category and cannot be omitted.\n"
    "- Use snippets as your primary source. If snippets don't mention a required "
    "schema field, fall back to your training data (you know specs for well-known "
    "products like phones, supplements, fragrances)."
)


def _mock_openai_returning(payload: dict):
    """Client whose completion returns exactly `payload` as JSON.

    `extract_specs` resolves its client through `get_client()`, so tests
    monkeypatch that rather than the module-level singleton.
    """
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
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


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SPECS_NO_FABRICATION", raising=False)


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "true")


def _recorded_snippet_digest(limit: int = 5) -> str:
    """Rebuild the [snippet_N] digest exactly as the orchestrator does.

    Mirrors `StructuredComparisonService._format_numbered_search_results`
    (structured_comparison_service.py:6939-6951) over a RECORDED Serper
    payload, so the "rich snippets" arm is pinned against real captured data
    rather than an invented string.
    """
    raw = json.loads(
        io.open(FIXTURES / "serper_oudwood_organic.json", encoding="utf-8").read()
    )
    formatted = []
    for i, r in enumerate(raw.get("organic", [])[:limit]):
        formatted.append(f"[snippet_{i+1}] {r.get('title', '')}\n   {r.get('snippet', '')}")
    return "\n".join(formatted)


# ---------------------------------------------------------------------------
# (c) FLAG OFF - byte-identical to main
# ---------------------------------------------------------------------------

class TestFlagOffIsByteIdentical:

    def test_flag_defaults_off_in_code(self, flag_off):
        """House rule: feature flags ship OFF and flip in Railway."""
        assert extraction_service.specs_no_fabrication_enabled() is False

    def test_flag_off_prompt_carries_the_exact_515_516_substring(self, flag_off):
        p = _build_specs_prompt("Apple", "iPhone 17", "256 GB", "electronics", "ctx")
        assert MAIN_TRAINING_FALLBACK_RULES in p["system"]

    def test_flag_off_prompt_uses_the_unmodified_static_prefix(self, flag_off):
        p = _build_specs_prompt("Apple", "iPhone 17", "", "electronics", "ctx")
        assert p["system"].startswith(SPECS_SYSTEM_STATIC_PREFIX)

    def test_static_prefix_constant_still_orders_the_fallback(self):
        """The module constant itself is untouched - the flag must not edit
        main's prompt in place, only select a different one."""
        assert MAIN_TRAINING_FALLBACK_RULES in SPECS_SYSTEM_STATIC_PREFIX
        assert "\"training\" if from your own knowledge" in SPECS_SYSTEM_STATIC_PREFIX

    @pytest.mark.asyncio
    async def test_flag_off_still_stamps_na_and_keeps_training_values(
        self, flag_off, monkeypatch
    ):
        """Main behaviour: a training-sourced value is KEPT, an absent field is
        stamped "N/A", and no evidence marker is emitted."""
        payload = {
            "brand": "Tom Ford",
            "model": "Oud Wood",
            "variant": "50 ml",
            "category": "fragrances",
            "concentration": "EDP",
            "concentration_source": "training",
            "longevity": "8-10 hours",
            "longevity_source": "training",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs(
            "Tom Ford", "Oud Wood", "50 ml", "fragrances", ""
        )
        assert specs["concentration"] == "EDP"
        assert specs["concentration_source"] == "training"
        assert specs["longevity"] == "8-10 hours"
        # every other schema field is stamped, not omitted
        assert specs["scent_family"] == "N/A"
        assert "_evidence_limited" not in specs


# ---------------------------------------------------------------------------
# (a) FLAG ON - the prompt forbids the fallback
# ---------------------------------------------------------------------------

class TestFlagOnPrompt:

    def test_flag_on_drops_the_training_fallback_order(self, flag_on):
        p = _build_specs_prompt("Apple", "iPhone 17", "", "electronics", "ctx")
        assert MAIN_TRAINING_FALLBACK_RULES not in p["system"]
        assert "fall back to your training data" not in p["system"]

    def test_flag_on_forbids_training_as_a_source_value(self, flag_on):
        p = _build_specs_prompt("Apple", "iPhone 17", "", "electronics", "ctx")
        system = p["system"]
        # The examples must stop demonstrating _source="training".
        assert '_source="training"' not in system
        assert '"training" if from your own knowledge' not in system

    def test_flag_on_orders_omission_of_unsupported_fields(self, flag_on):
        p = _build_specs_prompt("Apple", "iPhone 17", "", "electronics", "ctx")
        system = p["system"].lower()
        assert "omit" in system
        assert "snippet" in system

    def test_flag_on_keeps_the_shared_normalisation_principles(self, flag_on):
        """Only the training-data fallback changes - unit/format discipline
        (the part that has nothing to do with provenance) is shared."""
        p = _build_specs_prompt("Apple", "iPhone 17", "", "electronics", "ctx")
        assert "Unit consistency" in p["system"]
        assert "Brand-prefix omission in model field" in p["system"]

    def test_flag_on_static_prefix_is_still_cacheable(self, flag_on):
        """The >=1024-token auto-caching prefix must survive the flag."""
        tiktoken = pytest.importorskip("tiktoken")
        enc = tiktoken.encoding_for_model("gpt-4o-mini")
        p = _build_specs_prompt("Apple", "iPhone 17", "", "electronics", "ctx")
        static = p["system"].split("CATEGORY:")[0]
        assert len(enc.encode(static)) >= 1024

    def test_flag_on_static_prefix_is_identical_across_categories(self, flag_on):
        a = _build_specs_prompt("X", "Y", "", "electronics", "ctx")["system"]
        b = _build_specs_prompt("X", "Y", "", "supplements", "ctx")["system"]
        assert a.split("CATEGORY:")[0] == b.split("CATEGORY:")[0]


# ---------------------------------------------------------------------------
# (a) FLAG ON + empty/thin context - nothing fabricated
# ---------------------------------------------------------------------------

class TestFlagOnThinContextFabricatesNothing:

    @pytest.mark.asyncio
    async def test_training_sourced_fields_are_omitted(self, flag_on, monkeypatch):
        payload = {
            "brand": "Tom Ford",
            "model": "Oud Wood",
            "variant": "50 ml",
            "category": "fragrances",
            "concentration": "EDP",
            "concentration_source": "training",
            "longevity": "8-10 hours",
            "longevity_source": "training",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("Tom Ford", "Oud Wood", "50 ml", "fragrances", "")
        assert "concentration" not in specs
        assert "concentration_source" not in specs
        assert "longevity" not in specs
        assert specs["_evidence_limited"] is True

    @pytest.mark.asyncio
    async def test_field_with_no_source_at_all_is_omitted(self, flag_on, monkeypatch):
        payload = {
            "brand": "Apple",
            "model": "iPhone 17",
            "variant": "256 GB",
            "category": "electronics",
            "battery": "3349 mAh",  # no battery_source -> unsupported
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("Apple", "iPhone 17", "256 GB", "electronics", "")
        assert "battery" not in specs

    @pytest.mark.asyncio
    async def test_no_field_is_ever_stamped_na(self, flag_on, monkeypatch):
        payload = {
            "brand": "Apple",
            "model": "iPhone 17",
            "variant": "",
            "category": "electronics",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("Apple", "iPhone 17", "", "electronics", "")
        assert "N/A" not in specs.values()

    @pytest.mark.asyncio
    async def test_a_literal_na_with_a_citation_is_still_omitted(
        self, flag_on, monkeypatch
    ):
        payload = {
            "brand": "Apple",
            "model": "iPhone 17",
            "variant": "",
            "category": "electronics",
            "ram": "N/A",
            "ram_source": "snippet_1",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("Apple", "iPhone 17", "", "electronics", "")
        assert "ram" not in specs

    @pytest.mark.asyncio
    async def test_identity_meta_keys_survive(self, flag_on, monkeypatch):
        """brand/model/variant/category come from the USER's own query, not
        from the model's knowledge - they are never fabrication."""
        payload = {
            "brand": "Apple",
            "model": "iPhone 17",
            "variant": "256 GB",
            "category": "electronics",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("Apple", "iPhone 17", "256 GB", "electronics", "")
        assert specs["brand"] == "Apple"
        assert specs["model"] == "iPhone 17"
        assert specs["variant"] == "256 GB"

    @pytest.mark.asyncio
    async def test_marker_is_absent_when_nothing_was_dropped(
        self, flag_on, monkeypatch
    ):
        payload = {
            "brand": "Tom Ford",
            "model": "Oud Wood",
            "variant": "50 ml",
            "category": "fragrances",
        }
        payload.update({f: "x" for f in CATEGORY_SPEC_SCHEMAS["fragrances"]})
        payload.update(
            {f"{f}_source": "snippet_1" for f in CATEGORY_SPEC_SCHEMAS["fragrances"]}
        )
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("Tom Ford", "Oud Wood", "50 ml", "fragrances", "")
        assert "_evidence_limited" not in specs

    @pytest.mark.asyncio
    async def test_marker_is_internal_and_never_rendered(self, flag_on, monkeypatch):
        """The marker rides the existing internal-key convention (`_cached`,
        `_spec_confidence`, ...) so response_builder's `field.startswith("_")`
        filter drops it - it is not a new user-facing response key."""
        from app.services.response_builder import _build_specs_rows

        payload = {
            "brand": "A", "model": "B", "variant": "", "category": "electronics",
            "ram": "8 GB", "ram_source": "snippet_1",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs("A", "B", "", "electronics", "")
        assert specs["_evidence_limited"] is True  # something WAS dropped
        rows = _build_specs_rows([{"specs": specs}, {"specs": dict(specs)}])
        assert rows, "the cited field must still render"
        assert all(not r["field"].startswith("_") for r in rows)


# ---------------------------------------------------------------------------
# (b) FLAG ON + rich recorded snippets - specs extracted normally
# ---------------------------------------------------------------------------

class TestFlagOnRichSnippetsStillExtract:

    def test_the_recorded_digest_is_actually_rich(self):
        """Guard the guard: if the fixture ever thins out, arm (b) would pass
        vacuously."""
        digest = _recorded_snippet_digest()
        assert digest.count("[snippet_") >= 5
        assert "Oud Wood" in digest
        assert len(digest) > 400

    @pytest.mark.asyncio
    async def test_snippet_cited_fields_survive_intact(self, flag_on, monkeypatch):
        digest = _recorded_snippet_digest()
        payload = {
            "brand": "Tom Ford",
            "model": "Oud Wood",
            "variant": "50 ml",
            "category": "fragrances",
            "concentration": "EDP",
            "concentration_source": "snippet_3",
            "notes_top": "Cardamom, rosewood",
            "notes_top_source": "snippet_1",
            "scent_family": "Woody",
            "scent_family_source": "snippet_5",
            # unsupported - must still drop, even in a rich digest
            "sillage": "Heavy",
            "sillage_source": "training",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs(
            "Tom Ford", "Oud Wood", "50 ml", "fragrances", digest
        )
        assert specs["concentration"] == "EDP"
        assert specs["concentration_source"] == "snippet_3"
        assert specs["notes_top"] == "Cardamom, rosewood"
        assert specs["notes_top_source"] == "snippet_1"
        assert specs["scent_family"] == "Woody"
        assert "sillage" not in specs

    @pytest.mark.asyncio
    async def test_list_values_still_join_under_the_flag(self, flag_on, monkeypatch):
        payload = {
            "brand": "Tom Ford", "model": "Oud Wood", "variant": "", "category": "fragrances",
            "notes_top": ["Oud", "Cardamom", "Rosewood"],
            "notes_top_source": "snippet_1",
        }
        monkeypatch.setattr(
            extraction_service, "get_client", lambda: _mock_openai_returning(payload)
        )
        specs, _ = await extract_specs(
            "Tom Ford", "Oud Wood", "", "fragrances", _recorded_snippet_digest()
        )
        assert specs["notes_top"] == "Oud, Cardamom, Rosewood"

    @pytest.mark.asyncio
    async def test_the_digest_reaches_the_model_unchanged(self, flag_on, monkeypatch):
        """The guard must not silently shrink the evidence it is judging."""
        digest = _recorded_snippet_digest()
        client = _mock_openai_returning(
            {"brand": "Tom Ford", "model": "Oud Wood", "variant": "", "category": "fragrances"}
        )
        monkeypatch.setattr(extraction_service, "get_client", lambda: client)
        await extract_specs("Tom Ford", "Oud Wood", "", "fragrances", digest)
        user_msg = client.chat.completions.create.await_args.kwargs["messages"][1]["content"]
        assert "[snippet_1]" in user_msg
        assert "[snippet_5]" in user_msg


# ---------------------------------------------------------------------------
# Flag parsing - per-call getenv, never cached at import
# ---------------------------------------------------------------------------

class TestFlagIsReadPerCall:

    def test_flag_flips_within_one_process(self, monkeypatch):
        monkeypatch.delenv("ENABLE_SPECS_NO_FABRICATION", raising=False)
        assert extraction_service.specs_no_fabrication_enabled() is False
        monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "true")
        assert extraction_service.specs_no_fabrication_enabled() is True
        monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "false")
        assert extraction_service.specs_no_fabrication_enabled() is False

    @pytest.mark.parametrize("raw", ["true", "TRUE", " True ", "1", "yes", "on"])
    def test_truthy_spellings(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", raw)
        assert extraction_service.specs_no_fabrication_enabled() is True

    @pytest.mark.parametrize("raw", ["false", "0", "no", "off", "", "  ", "banana"])
    def test_falsy_spellings(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", raw)
        assert extraction_service.specs_no_fabrication_enabled() is False

    def test_env_is_not_snapshotted_at_import(self):
        """os.getenv must be called inside the helper (the price_service
        `exact_gate_enabled` idiom), not read once at module load."""
        import inspect
        src = inspect.getsource(extraction_service.specs_no_fabrication_enabled)
        assert "getenv" in src or "environ" in src
