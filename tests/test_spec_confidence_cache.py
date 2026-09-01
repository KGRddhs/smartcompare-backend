"""Issue #107 — carry spec citation confidence across the specs cache.

Spec-citation verification is dead on every cache hit: `_get_specs` writes the
L1/L2 cache BEFORE attaching `_search_snippets`, so a warm comparison verifies
its citations against an empty snippet list and every `snippet_N`-cited field
lands on "unverified" (production rows: specs_verified=0, specs_likely=0 on
24/24 sides). The fix persists the DERIVED map `_spec_citation_confidence`
(the exact `verify_spec_citations` return shape) inside the cached specs dict,
behind ENABLE_SPEC_CONFIDENCE_CACHE (default OFF, read per call).

No network, no paid calls: extract_specs / cache get+set / fire-and-forget are
all stubbed at the module seams `_cache_get_async` / `_cache_set_async`
reference in both offload branches.
"""
import copy

import pytest

import app.services.structured_comparison_service as scs
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    get_comparison_service,
)
from app.services.fact_check_service import build_fact_check
from app.services.response_builder import _build_specs_rows


FLAG = "ENABLE_SPEC_CONFIDENCE_CACHE"

# A snippet that verifies "4422 mAh" under the v1 rubric (bare significant
# digits present as substrings).
_SNIPPET = "samsung galaxy s25 ultra battery 4422 mah, all-day life"


@pytest.fixture
def quiet_flags(monkeypatch):
    """Neutralise sibling flags so verdicts are deterministic."""
    for name in (
        "ENABLE_SPEC_SPINE",
        "ENABLE_ASYNC_REDIS_OFFLOAD",
        "ENABLE_CITATION_RUBRIC_V2",
        "ENABLE_SPECS_NO_FABRICATION",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def flag_on(quiet_flags, monkeypatch):
    monkeypatch.setenv(FLAG, "true")


@pytest.fixture
def flag_off(quiet_flags, monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)


class _ExtractSpy:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return dict(self.payload), {"prompt_tokens": 1, "completion_tokens": 1}


def _swallow_fire_and_forget(coro, label=None, **_kw):
    # Close the save_specs coroutine so no "never awaited" warning and no
    # Supabase call.
    try:
        coro.close()
    except Exception:  # noqa: BLE001 — best-effort in tests
        pass


def _wire(monkeypatch, *, l1_cached=None, extracted=None, snippet=_SNIPPET):
    """Stub every seam _get_specs touches. Returns (spy, set_calls)."""
    spy = _ExtractSpy(
        extracted
        if extracted is not None
        else {"battery": "4422 mAh", "battery_source": "snippet_1"}
    )
    set_calls = []

    def _fake_get_cached(key):
        return copy.deepcopy(l1_cached)

    def _fake_set_cached(key, value, ttl):
        # Deep-copy AT CALL TIME: the ordering bug under test is precisely
        # "the dict is mutated after the cache write", so capturing a live
        # reference would lie about what was persisted.
        set_calls.append((key, copy.deepcopy(value), ttl))
        return True

    monkeypatch.setattr(scs, "get_cached", _fake_get_cached)
    monkeypatch.setattr(scs, "set_cached", _fake_set_cached)
    monkeypatch.setattr(scs, "extract_specs", spy)
    monkeypatch.setattr(scs, "_fire_and_forget", _swallow_fire_and_forget)
    monkeypatch.setattr(
        StructuredComparisonService,
        "_format_numbered_search_results",
        lambda self, results: (f"1. {snippet}", [snippet]),
    )
    return spy, set_calls


async def _run_get_specs(nocache=True):
    svc = get_comparison_service()
    return await svc._get_specs(
        "Samsung", "Galaxy S25 Ultra", None, "electronics",
        "Samsung Galaxy S25 Ultra", nocache=nocache, search_results={},
    )


# ---------------------------------------------------------------------------
# 1. Cold path: the derived map is in the payload the cache write persists.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cold_path_attaches_citation_confidence_before_cache_write(
    flag_on, monkeypatch
):
    spy, set_calls = _wire(monkeypatch)
    out = await _run_get_specs(nocache=True)

    assert len(spy.calls) == 1
    assert len(set_calls) == 1
    _key, payload, _ttl = set_calls[0]
    assert payload.get("_spec_citation_confidence") == {"battery": "verified"}
    # The snippets digest itself must NOT be persisted (3KB/product, and the
    # stale-snippet cross-request hazard the derived map exists to remove).
    assert "_search_snippets" not in payload
    # The returned dict carries the same map for this request's fact-check.
    assert out.get("_spec_citation_confidence") == {"battery": "verified"}


# ---------------------------------------------------------------------------
# 2. L1 cache hit: the map round-trips intact, with no extraction call.
#    NOTE: at base this is GREEN (the early return passes the dict through
#    unmodified) — the issue's RED prediction for this case is wrong; the red
#    coverage is carried by cases 1, 3, 6 and 7. Kept as the pass-through pin.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_l1_cache_hit_returns_citation_confidence(flag_on, monkeypatch):
    cached = {
        "battery": "4422 mAh",
        "battery_source": "snippet_1",
        "_spec_citation_confidence": {"battery": "verified"},
    }
    spy, _set_calls = _wire(monkeypatch, l1_cached=cached)
    out = await _run_get_specs(nocache=False)

    assert spy.calls == []
    assert out["_cached"] is True
    assert out.get("_spec_citation_confidence") == {"battery": "verified"}


# ---------------------------------------------------------------------------
# 3. Warm fact-check: a cached map produces non-zero verified/likely counts
#    (reproduces the 24/24 production zero-rows when red).
# ---------------------------------------------------------------------------
def test_warm_comparison_reports_nonzero_specs_verified(flag_on):
    raw_specs = {
        "battery": "4422 mAh",
        "battery_source": "snippet_1",
        "storage": "256 GB",
        "storage_source": "snippet_2",
        "_spec_citation_confidence": {"battery": "verified", "storage": "likely"},
    }
    # Warm path: no _search_snippets key — exactly what the cache returns.
    search_snippets = raw_specs.pop("_search_snippets", [])
    result = {"specs": raw_specs}
    result["_spec_confidence"] = scs._compute_spec_confidence(
        raw_specs, search_snippets, [], "Samsung Galaxy S25 Ultra",
    )
    fact_check = build_fact_check(result)
    assert fact_check["specs_verified"] == 1
    assert fact_check["specs_likely"] == 1


# ---------------------------------------------------------------------------
# 4. Legacy cache entry (neither snippets nor map): today's behaviour holds.
# ---------------------------------------------------------------------------
def test_legacy_cache_entry_without_citation_confidence_falls_back(flag_on):
    raw_specs = {
        "battery": "4422 mAh",
        "battery_source": "snippet_1",
        "storage": "256 GB",
        "storage_source": "snippet_2",
    }
    search_snippets = raw_specs.pop("_search_snippets", [])
    result = {"specs": raw_specs}
    result["_spec_confidence"] = scs._compute_spec_confidence(
        raw_specs, search_snippets, [], "Samsung Galaxy S25 Ultra",
    )
    assert result["_spec_confidence"] == {
        "battery": "unverified",
        "storage": "unverified",
    }
    fact_check = build_fact_check(result)
    assert fact_check["specs_verified"] == 0
    assert fact_check["specs_likely"] == 0
    assert fact_check["specs_unverified"] == 2


# ---------------------------------------------------------------------------
# 5. Enrichment-cascade fields stay OUT of the fact-check counts (both flag
#    modes) — _spec_confidence is frozen before the Tier-2/Tier-3 cascade and
#    labelling cascade fields would move _score_reliability's denominator.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("flag_value", [None, "true"])
def test_enrichment_added_fields_stay_out_of_counts(
    quiet_flags, monkeypatch, flag_value
):
    if flag_value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag_value)

    raw_specs = {"battery": "4422 mAh", "battery_source": "snippet_1"}
    result = {"specs": raw_specs}
    result["_spec_confidence"] = scs._compute_spec_confidence(
        raw_specs, [_SNIPPET], [], "Samsung Galaxy S25 Ultra",
    )
    # Simulate the smart-fallback / Tier-2 / Tier-3 cascade adding a field
    # AFTER _spec_confidence was frozen.
    raw_specs["front_camera"] = "12 MP"

    assert "front_camera" not in result["_spec_confidence"]
    fact_check = build_fact_check(result)
    total = (
        fact_check["specs_verified"]
        + fact_check["specs_likely"]
        + fact_check["specs_flagged"]
        + fact_check["specs_unverified"]
    )
    assert total == 1  # battery only — the cascade field is not counted


# ---------------------------------------------------------------------------
# 6. _clean_specs must carry the map through (it strips all other _ keys).
# ---------------------------------------------------------------------------
def test_clean_specs_preserves_citation_confidence(flag_on):
    cleaned = StructuredComparisonService._clean_specs(
        {
            "battery": "4422 mAh",
            "_spec_citation_confidence": {"battery": "verified"},
        }
    )
    assert cleaned.get("_spec_citation_confidence") == {"battery": "verified"}
    assert cleaned["battery"] == "4422 mAh"


# ---------------------------------------------------------------------------
# 7. The enriched re-cache payload keeps the map (and still strips the
#    transients). Composes the REAL pipeline order: _clean_specs runs before
#    the re-cache reads result["specs"], so a _clean_specs strip would
#    silently overwrite a good cache entry with one missing the key.
# ---------------------------------------------------------------------------
def test_enriched_recache_payload_carries_citation_confidence(flag_on):
    specs = {
        "battery": "4422 mAh",
        "battery_source": "snippet_1",
        "_spec_citation_confidence": {"battery": "verified"},
        "_search_snippets": [_SNIPPET],
        "_cached": True,
        "_cache_source": "db",
    }
    cleaned = StructuredComparisonService._clean_specs(specs)
    payload = scs._enriched_recache_payload(cleaned)
    assert payload.get("_spec_citation_confidence") == {"battery": "verified"}
    for transient in ("_search_snippets", "_cached", "_cache_source"):
        assert transient not in payload

    # The strip contract holds even when the transients reach the payload
    # builder directly (no _clean_specs in front).
    direct = scs._enriched_recache_payload(
        {"a": 1, "_search_snippets": [], "_cached": True, "_cache_source": "db"}
    )
    assert direct == {"a": 1}


# ---------------------------------------------------------------------------
# 8. The map never becomes a specs-comparison ROW (response_builder's
#    _-prefix filter). NOTE (out of scope, pre-existing): products[i].specs
#    passes the raw dict through at response_builder.py:1650, so _-prefixed
#    maps (today: _field_confidence) DO appear there; this test pins the rows
#    filter the issue names.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("flag_value", [None, "true"])
def test_citation_confidence_never_reaches_api_payload(
    quiet_flags, monkeypatch, flag_value
):
    if flag_value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag_value)

    products = [
        {
            "specs": {
                "battery": "4422 mAh",
                "_spec_citation_confidence": {"battery": "verified"},
            }
        },
        {
            "specs": {
                "battery": "5000 mAh",
                "_spec_citation_confidence": {"battery": "likely"},
            }
        },
    ]
    rows = _build_specs_rows(products)
    fields = [row["field"] for row in rows]
    assert "battery" in fields  # sanity: real fields still render
    assert "_spec_citation_confidence" not in fields
    assert not any(f.startswith("_") for f in fields)


# ---------------------------------------------------------------------------
# 9. Flag OFF: byte-identical to today at every touched seam. Must be green
#    from the first commit and stay green.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_flag_off_cold_path_writes_no_citation_confidence(
    flag_off, monkeypatch
):
    spy, set_calls = _wire(monkeypatch)
    out = await _run_get_specs(nocache=True)

    assert len(spy.calls) == 1
    assert len(set_calls) == 1
    _key, payload, _ttl = set_calls[0]
    assert "_spec_citation_confidence" not in payload
    assert "_search_snippets" not in payload  # write happens before attach
    assert "_spec_citation_confidence" not in out
    assert out["_search_snippets"] == [_SNIPPET]
    assert out["_cached"] is False


@pytest.mark.asyncio
async def test_flag_off_l1_hit_specs_verified_stays_zero(flag_off, monkeypatch):
    """The production symptom, pinned: a warm comparison scores 0 verified."""
    cached = {
        "battery": "4422 mAh",
        "battery_source": "snippet_1",
        # Even a map written while the flag WAS on is ignored with it off.
        "_spec_citation_confidence": {"battery": "verified"},
    }
    spy, _set_calls = _wire(monkeypatch, l1_cached=cached)
    out = await _run_get_specs(nocache=False)
    assert spy.calls == []

    raw_specs = out
    search_snippets = raw_specs.pop("_search_snippets", [])
    result = {"specs": raw_specs}
    result["_spec_confidence"] = scs._compute_spec_confidence(
        raw_specs, search_snippets, [], "Samsung Galaxy S25 Ultra",
    )
    fact_check = build_fact_check(result)
    assert fact_check["specs_verified"] == 0
    assert fact_check["specs_likely"] == 0


def test_flag_off_clean_specs_strips_citation_confidence(flag_off):
    cleaned = StructuredComparisonService._clean_specs(
        {
            "battery": "4422 mAh",
            "_spec_citation_confidence": {"battery": "verified"},
        }
    )
    assert "_spec_citation_confidence" not in cleaned
    assert cleaned["battery"] == "4422 mAh"


def test_flag_off_enriched_recache_payload_drops_citation_confidence(flag_off):
    specs = {
        "battery": "4422 mAh",
        "_spec_citation_confidence": {"battery": "verified"},
        "_search_snippets": [_SNIPPET],
    }
    cleaned = StructuredComparisonService._clean_specs(specs)
    payload = scs._enriched_recache_payload(cleaned)
    assert "_spec_citation_confidence" not in payload
    assert "_search_snippets" not in payload
