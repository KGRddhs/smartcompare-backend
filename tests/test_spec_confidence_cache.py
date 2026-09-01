"""Issue #107 — carry spec citation confidence ACROSS the specs cache so the
citation layer runs on WARM traffic (ENABLE_SPEC_CONFIDENCE_CACHE, default OFF).

Today the citation check is computed on a cold extract and lost on the 7d cache
write (`_get_specs` writes the cache BEFORE attaching `_search_snippets`), so
every warm hit renders confidence that was never verified: `specs_verified=0`
and `specs_likely=0` on every cached comparison.

All offline/deterministic — cache, DB and LLM layers are monkeypatched stubs.
Run: python -m pytest tests/test_spec_confidence_cache.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app.services.structured_comparison_service as scs
import app.services.product_data_service as pds
from app.services.structured_comparison_service import StructuredComparisonService
from app.services.fact_check_service import build_fact_check
from app.services.response_builder import _build_specs_rows


# The transient keys the enriched re-cache block strips (mirrors the inline
# comprehension at the `_specs_enriched_by_fallback` write-back).
_TRANSIENT = ("_search_snippets", "_cached", "_cache_source")


def _resolver():
    """The citation-confidence resolution the fact-check pass uses.

    Post-#107 this is `_resolve_citation_confidence` (prefers a cached
    `_spec_citation_confidence` map when the flag is ON). At base it does not
    exist yet, so we fall back to the raw `verify_spec_citations` call the
    inline block makes today — which makes the RED failure the REAL defect
    (warm traffic scores against an empty snippet list), not an import error.
    """
    return getattr(scs, "_resolve_citation_confidence", None) or scs.verify_spec_citations


def _strip_transient():
    """The enriched re-cache payload builder. Post-#107 the block uses the
    extracted `_strip_transient_spec_keys`; at base, reproduce the inline
    dict comprehension verbatim."""
    fn = getattr(scs, "_strip_transient_spec_keys", None)
    if fn is not None:
        return fn
    return lambda specs: {
        k: v for k, v in (specs or {}).items() if k not in _TRANSIENT
    }


@pytest.fixture
def service():
    return StructuredComparisonService()


def _stub_specs_layers(monkeypatch, service, *, l1=None, extract_result=None,
                       snippets=None, captured=None):
    """Stub every network/cache dependency of `_get_specs`."""
    async def fake_cache_get(key):
        return dict(l1) if l1 is not None else None

    async def fake_cache_set(key, value, ttl):
        if captured is not None:
            captured.append((key, dict(value), ttl))

    async def fake_get_cached_specs(key):
        return None

    async def fake_save_specs(*a, **k):
        return None

    async def fake_extract_specs(*a, **k):
        if extract_result is None:
            raise AssertionError("extract_specs must NOT be called on a cache hit")
        return dict(extract_result), {}

    monkeypatch.setattr(scs, "_cache_get_async", fake_cache_get)
    monkeypatch.setattr(scs, "_cache_set_async", fake_cache_set)
    monkeypatch.setattr(pds, "get_cached_specs", fake_get_cached_specs)
    monkeypatch.setattr(pds, "save_specs", fake_save_specs)
    monkeypatch.setattr(scs, "extract_specs", fake_extract_specs)
    monkeypatch.setattr(
        service, "_format_numbered_search_results",
        lambda results: ("ctx", list(snippets or [])),
    )


class TestSpecConfidenceCache:

    # ------------------------------------------------------------------ cold
    @pytest.mark.asyncio
    async def test_cold_path_attaches_citation_confidence_before_cache_write(
        self, service, monkeypatch
    ):
        """Flag ON: the payload written to the specs cache carries the derived
        `_spec_citation_confidence` map (so warm traffic can reuse it)."""
        monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        captured = []
        _stub_specs_layers(
            monkeypatch, service,
            extract_result={"battery": "4422 mAh", "battery_source": "snippet_1"},
            snippets=["The handset packs a 4422 mAh battery."],
            captured=captured,
        )
        await service._get_specs(
            "Apple", "iPhone 16", None, "electronics", "q",
            search_results={"organic": []},
        )
        assert captured, "cache write did not happen"
        payload = captured[0][1]
        assert payload.get("_spec_citation_confidence") == {"battery": "verified"}
        # snippets themselves are still never persisted
        assert "_search_snippets" not in payload

    # ------------------------------------------------------------------ warm
    @pytest.mark.asyncio
    async def test_l1_cache_hit_returns_citation_confidence(
        self, service, monkeypatch
    ):
        """Flag ON: an L1 hit returns the persisted map intact, with no
        re-extract (pin — the round-trip is what #107 makes meaningful)."""
        monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        cached = {
            "battery": "4422 mAh", "battery_source": "snippet_1",
            "_spec_citation_confidence": {"battery": "verified"},
        }
        _stub_specs_layers(monkeypatch, service, l1=cached)
        result = await service._get_specs(
            "Apple", "iPhone 16", None, "electronics", "q",
            search_results={"organic": []},
        )
        assert result["_spec_citation_confidence"] == {"battery": "verified"}
        assert result["_cached"] is True

    def test_warm_comparison_reports_nonzero_specs_verified(self, monkeypatch):
        """Flag ON: a warm comparison (no `_search_snippets`, cached
        `_spec_citation_confidence` present) produces non-zero
        specs_verified/specs_likely — reproduces the 24/24 production rows
        where both were 0."""
        monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        raw_specs = {
            "battery": "4422 mAh", "battery_source": "snippet_1",
            "storage": "256GB", "storage_source": "snippet_2",
            "_spec_citation_confidence": {"battery": "verified", "storage": "likely"},
        }
        # Mirror the fact-check block: pop snippets (absent on warm), resolve.
        search_snippets = raw_specs.pop("_search_snippets", [])
        citation_confidence = _resolver()(raw_specs, search_snippets)
        result = {"_spec_confidence": dict(citation_confidence)}
        fc = build_fact_check(result)
        assert fc["specs_verified"] == 1
        assert fc["specs_likely"] == 1

    def test_legacy_cache_entry_without_citation_confidence_falls_back(
        self, monkeypatch
    ):
        """Flag ON: a cache entry written by the OLD shape (neither
        `_search_snippets` nor `_spec_citation_confidence`) must not crash and
        must NOT silently read as verified — every field scores 'unverified'
        (today's warm behaviour, preserved for legacy entries)."""
        monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        raw_specs = {
            "battery": "4422 mAh", "battery_source": "snippet_1",
            "storage": "256GB",
        }
        search_snippets = raw_specs.pop("_search_snippets", [])
        confidence = _resolver()(raw_specs, search_snippets)
        assert confidence == {"battery": "unverified", "storage": "unverified"}

    # ------------------------------------------------- scope boundary (pin)
    @pytest.mark.parametrize("flag_on", [False, True])
    def test_enrichment_added_fields_stay_out_of_counts(self, monkeypatch, flag_on):
        """A field added by the smart-fallback/Tier-2/Tier-3 cascade AFTER
        `_spec_confidence` was frozen is absent from the fact-check counts, in
        BOTH flag modes (deliberate scope boundary of #107)."""
        if flag_on:
            monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        else:
            monkeypatch.delenv("ENABLE_SPEC_CONFIDENCE_CACHE", raising=False)
        result = {
            "_spec_confidence": {"battery": "verified"},
            "specs": {"battery": "4422 mAh", "storage": "256GB"},  # storage = enrichment-added
        }
        fc = build_fact_check(result)
        assert fc["specs_verified"] == 1
        assert fc["specs_likely"] == 0
        assert fc["specs_unverified"] == 0
        assert fc["specs_flagged"] == 0

    # -------------------------------------------------------- _clean_specs
    def test_clean_specs_preserves_citation_confidence(self, service, monkeypatch):
        """Flag ON: `_clean_specs` re-adds `_spec_citation_confidence` next to
        `_field_confidence` — without this the enriched re-cache overwrites a
        good cache entry with one missing the key."""
        monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        cleaned = service._clean_specs({
            "battery": "4422 mAh",
            "_spec_citation_confidence": {"battery": "verified"},
        })
        assert cleaned.get("_spec_citation_confidence") == {"battery": "verified"}

    def test_enriched_recache_payload_carries_citation_confidence(
        self, service, monkeypatch
    ):
        """Flag ON: the enriched re-cache payload (post-`_clean_specs`, post
        transient-key strip) still carries `_spec_citation_confidence` and
        still lacks `_search_snippets`/`_cached`/`_cache_source`."""
        monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        # the display dict the re-cache block reads is _clean_specs output...
        cleaned = service._clean_specs({
            "battery": "4422 mAh",
            "battery_source": "snippet_1",
            "_spec_citation_confidence": {"battery": "verified"},
        })
        # ...plus whatever transient keys are still on the dict at that point
        cleaned.update({"_cached": True, "_cache_source": "db",
                        "_search_snippets": ["snippet text"]})
        payload = _strip_transient()(cleaned)
        assert payload.get("_spec_citation_confidence") == {"battery": "verified"}
        for k in _TRANSIENT:
            assert k not in payload

    # ------------------------------------------------------------ API leak
    @pytest.mark.parametrize("flag_on", [False, True])
    def test_citation_confidence_never_reaches_api_payload(self, monkeypatch, flag_on):
        """`_spec_citation_confidence` is a private key: the response builder's
        `_`-prefix filter keeps it out of the spec rows (pin)."""
        if flag_on:
            monkeypatch.setenv("ENABLE_SPEC_CONFIDENCE_CACHE", "true")
        else:
            monkeypatch.delenv("ENABLE_SPEC_CONFIDENCE_CACHE", raising=False)
        specs = {
            "battery": "4422 mAh",
            "_spec_citation_confidence": {"battery": "verified"},
        }
        rows = _build_specs_rows([{"specs": dict(specs)}, {"specs": dict(specs)}])
        fields = {r["field"] for r in rows}
        assert "_spec_citation_confidence" not in fields
        assert "battery" in fields

    # ------------------------------------------------- flag-OFF identity pin
    @pytest.mark.asyncio
    async def test_flag_off_byte_identical(self, service, monkeypatch):
        """REQUIRED flag-OFF identity pin: with ENABLE_SPEC_CONFIDENCE_CACHE
        unset, nothing writes or preserves `_spec_citation_confidence` anywhere
        and a warm comparison still reports specs_verified == 0."""
        monkeypatch.delenv("ENABLE_SPEC_CONFIDENCE_CACHE", raising=False)

        # (1) cold path: cache payload has no citation-confidence key
        captured = []
        _stub_specs_layers(
            monkeypatch, service,
            extract_result={"battery": "4422 mAh", "battery_source": "snippet_1"},
            snippets=["The handset packs a 4422 mAh battery."],
            captured=captured,
        )
        result = await service._get_specs(
            "Apple", "iPhone 16", None, "electronics", "q",
            search_results={"organic": []},
        )
        assert captured and "_spec_citation_confidence" not in captured[0][1]
        assert "_spec_citation_confidence" not in result

        # (2) _clean_specs strips the key exactly as today
        cleaned = service._clean_specs({
            "battery": "4422 mAh",
            "_spec_citation_confidence": {"battery": "verified"},
        })
        assert "_spec_citation_confidence" not in cleaned

        # (3) warm resolution ignores any cached map -> 0 verified, 0 likely
        raw_specs = {
            "battery": "4422 mAh", "battery_source": "snippet_1",
            "_spec_citation_confidence": {"battery": "verified"},
        }
        confidence = _resolver()(raw_specs, raw_specs.pop("_search_snippets", []))
        fc = build_fact_check({"_spec_confidence": dict(confidence)})
        assert fc["specs_verified"] == 0
        assert fc["specs_likely"] == 0
