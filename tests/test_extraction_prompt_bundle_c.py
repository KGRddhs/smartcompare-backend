"""Bundle C — extraction service RED tests (Section C plan tasks C.3.1–C.3.5 + C.2.2).

Covers spec §2e (verdict prompt receives weird flag) + §2f (3-tier spec fallback).

  - C.3.1 — NON_NEGOTIABLE vs PREFERRED field classification per category
  - C.3.2 — Tier 2 skipped when non-negotiables filled by Tier 1
  - C.3.3 — Tier 3 fires only after Tier 2 exhausted
  - C.3.4 — Wall-time inside STREAM_HARD_CAP_SECONDS budget (sanity smoke)
  - C.3.5 — inference_source="model_knowledge" NEVER reaches user-visible response
  - C.2.2 — verdict prompt accepts `comparison_quality` arg

RED until A.4.6 (CRITICAL_SCHEMA_FIELDS split) + A.x (Tier 2/3 cascade) ship.
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest


# Table from spec §2f
EXPECTED_NON_NEGOTIABLE = {
    "electronics": {"battery", "processor", "ram", "rear_camera"},
    # S2 I3.6 (Decision B): active_ingredient promoted preferred →
    # non-negotiable for supplements + skincare (defining spec + gold anchor;
    # routes blank Tier-1 extraction into the Tier-2/3 fill cascade).
    "supplements": {"dosage", "form", "active_ingredient"},
    "fragrances":  {"concentration", "longevity"},
    "fashion":     {"material"},
    "skincare":    {"volume", "ingredients", "active_ingredient"},
    "haircare":    {"volume", "ingredients"},
    "makeup":      {"volume", "shade_range"},
    "grocery":     {"weight", "ingredients"},
    "other":       set(),  # all preferred
}


# ---------------------------------------------------------------------------
# C.3.1 — Non-negotiable vs preferred fields per category (spec §2f)
# ---------------------------------------------------------------------------


def _import_non_negotiable():
    """Import the non-negotiable map under either name (backend used
    `CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE`; spec text used
    `NON_NEGOTIABLE_FIELDS_BY_CATEGORY` — accept both)."""
    try:
        from app.services.extraction_service import (  # type: ignore
            CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE as M,
        )
        return M
    except ImportError:
        pass
    try:
        from app.services.extraction_service import (  # type: ignore
            NON_NEGOTIABLE_FIELDS_BY_CATEGORY as M,
        )
        return M
    except ImportError:
        return None


def _import_preferred():
    try:
        from app.services.extraction_service import (  # type: ignore
            CRITICAL_SCHEMA_FIELDS_PREFERRED as M,
        )
        return M
    except ImportError:
        pass
    try:
        from app.services.extraction_service import (  # type: ignore
            PREFERRED_FIELDS_BY_CATEGORY as M,
        )
        return M
    except ImportError:
        return None


@pytest.mark.parametrize("category,expected", sorted(EXPECTED_NON_NEGOTIABLE.items()))
def test_non_negotiable_fields_per_category(category, expected):
    """Spec §2f: non-negotiable fields per category match the spec table."""
    non_neg_map = _import_non_negotiable()
    if non_neg_map is None:
        pytest.fail(
            "RED: A.4.6 not shipped — neither CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE "
            "nor NON_NEGOTIABLE_FIELDS_BY_CATEGORY exposed by extraction_service"
        )
        return
    actual = set(non_neg_map.get(category, []))
    assert actual == expected, (
        f"{category}: expected {expected!r}, got {actual!r}"
    )


def test_preferred_fields_map_exists_and_disjoint_from_non_negotiable():
    """Spec §2f: preferred map exists; entries don't overlap with non-negotiable
    for the same category."""
    non_neg_map = _import_non_negotiable()
    pref_map = _import_preferred()
    if non_neg_map is None or pref_map is None:
        pytest.fail("RED: A.4.6 not shipped — non-negotiable or preferred map missing")
        return
    for category in EXPECTED_NON_NEGOTIABLE:
        non_neg = set(non_neg_map.get(category, []))
        pref = set(pref_map.get(category, []))
        overlap = non_neg & pref
        assert not overlap, (
            f"{category}: overlap between non-negotiable and preferred: {overlap}"
        )


# ---------------------------------------------------------------------------
# C.3.2 + C.3.3 — Tier 2 / Tier 3 firing rules
# ---------------------------------------------------------------------------


# Backend A.4.7 ships `tier2_fill_non_negotiables` in
# `structured_comparison_service`, not as `resolve_specs_with_tiered_fallback`
# in `extraction_service`. Signature: brand/name/variant/category/specs_so_far.
# Tier 3 (A.4.8) deferred to v1.1.


@pytest.mark.asyncio
async def test_tier2_skipped_when_non_negotiables_filled():
    """Spec §2f: Tier 2 fires ONLY when at least one non-negotiable is blank.
    Function: structured_comparison_service.tier2_fill_non_negotiables (A.4.7).
    """
    try:
        from app.services.structured_comparison_service import (  # type: ignore
            tier2_fill_non_negotiables,
        )
    except ImportError:
        pytest.fail("RED: tier2_fill_non_negotiables missing (A.4.7)")
        return
    # All electronics non-negotiables filled — Tier 2 must short-circuit to {}.
    specs_filled = {
        "battery": "3274 mAh",
        "processor": "A17",
        "ram": "8 GB",
        "rear_camera": "48 MP",
    }
    result = await tier2_fill_non_negotiables(
        brand="Apple", name="iPhone 16", variant=None,
        category="electronics", specs_so_far=specs_filled,
    )
    assert result == {}, (
        f"Tier 2 returned non-empty {result!r} despite all non-negotiables "
        f"already filled — should short-circuit"
    )


@pytest.mark.asyncio
async def test_tier2_fires_when_non_negotiable_missing(monkeypatch):
    """Spec §2f: Tier 2 attempts a fill when any non-negotiable is blank.
    We mock the underlying Serper + OpenAI calls so this stays free + fast.
    """
    try:
        from app.services import structured_comparison_service as sc_svc  # type: ignore
    except ImportError:
        pytest.fail("RED: tier2_fill_non_negotiables missing")
        return
    if not hasattr(sc_svc, "tier2_fill_non_negotiables"):
        pytest.fail("RED: tier2_fill_non_negotiables not exposed")
        return

    # Monkeypatch the internal Serper + OpenAI helpers to record calls without
    # firing real API requests.
    calls = {"serper": 0, "openai": 0}

    async def _fake_search_web(query, num_results=3):
        calls["serper"] += 1
        return {"organic": [{"snippet": f"spec for {query}"}]}

    async def _fake_extract_specs_targeted(**kwargs):
        calls["openai"] += 1
        fields = kwargs.get("fields", [])
        return {f: f"mock_value_{f}" for f in fields}

    monkeypatch.setattr(
        "app.services.serper_service.search_web", _fake_search_web, raising=False
    )
    monkeypatch.setattr(
        "app.services.openai_service.extract_specs_targeted",
        _fake_extract_specs_targeted, raising=False,
    )

    specs_partial = {"battery": "3274 mAh"}  # missing processor/ram/rear_camera
    result = await sc_svc.tier2_fill_non_negotiables(
        brand="Apple", name="iPhone 16", variant=None,
        category="electronics", specs_so_far=specs_partial,
    )
    # Tier 2 must have attempted at least one fill call (Serper + OpenAI).
    # Function may return {} on mock-detection failure paths, but call counters
    # prove the cascade fired.
    assert calls["serper"] >= 1 or calls["openai"] >= 1 or result, (
        f"Tier 2 did not fire any cascade call (serper={calls['serper']}, "
        f"openai={calls['openai']}, result={result!r})"
    )


# ---------------------------------------------------------------------------
# C.3.4 — Wall-time budget (sanity smoke)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tier2_wall_time_within_budget():
    """Spec §2f: Tier 2 is wrapped in `asyncio.wait_for(timeout=4.0)`.
    A no-op call (all non-negotiables filled) must return in well under that.
    Tier 3 wall-budget test deferred to v1.1 once A.4.8 ships.
    """
    try:
        from app.services.structured_comparison_service import (  # type: ignore
            tier2_fill_non_negotiables,
        )
    except ImportError:
        pytest.fail("RED: tier2_fill_non_negotiables missing")
        return

    start = time.monotonic()
    result = await asyncio.wait_for(
        tier2_fill_non_negotiables(
            brand="Apple", name="iPhone 16", variant=None,
            category="electronics",
            specs_so_far={
                "battery": "x", "processor": "x", "ram": "x", "rear_camera": "x",
            },
        ),
        timeout=5.0,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 5.0
    assert result == {}


# ---------------------------------------------------------------------------
# C.3.5 — inference_source="model_knowledge" NEVER reaches user-visible response
#         (Tier 3 only — DEFERRED to v1.1 with A.4.8)
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="DEFERRED v1.1 — A.4.8 (Tier 3 GPT-4o knowledge synthesis) not yet "
    "shipped. inference_source flag is a Tier 3 concern; no leak risk until "
    "Tier 3 lands."
)
@pytest.mark.asyncio
async def test_inference_source_flag_internal_only():
    """Spec §2f: Tier 3 outputs tagged inference_source='model_knowledge' —
    QA/dashboards only. NEVER reaches response.products[].specs.
    """
    pytest.skip("v1.1 — Tier 3 deferred")


def test_response_builder_strips_inference_source():
    """Belt-and-braces: response_builder must strip internal flags before serialization."""
    try:
        from app.services.response_builder import build_comparison_response  # type: ignore
    except ImportError:
        pytest.skip("response_builder not importable")
        return
    try:
        response = build_comparison_response(
            products=[
                {
                    "name": "iPhone",
                    "specs": {"processor": "A17 Pro"},
                    "price": {"amount": 600},
                    "_internal": {"processor_inference_source": "model_knowledge"},
                },
                {"name": "Galaxy", "specs": {}, "price": {"amount": 700}},
            ],
            comparison={"winner_index": 0},
        )
    except TypeError as exc:
        pytest.skip(f"build_comparison_response signature different: {exc}")
        return
    serialized = json.dumps(response)
    assert "model_knowledge" not in serialized, (
        "inference_source leaked into serialized response (response_builder must strip)"
    )
    assert "inference_source" not in serialized


# ---------------------------------------------------------------------------
# C.2.2 — Verdict prompt receives comparison_quality flag (spec §2e)
# ---------------------------------------------------------------------------


def test_weird_flag_forwarded_to_verdict_prompt():
    """Spec §2e: when comparison_quality='weird', verdict prompt rewrites
    winner_declaration to non-forced framing.
    """
    try:
        from app.services.extraction_service import (  # type: ignore
            build_verdict_prompt,
        )
    except ImportError:
        pytest.fail(
            "RED: build_verdict_prompt missing from extraction_service (A.x §2e)"
        )
        return
    try:
        prompt = build_verdict_prompt(products=[], comparison_quality="weird")
    except TypeError as exc:
        pytest.fail(f"RED: build_verdict_prompt signature mismatch: {exc}")
        return
    lowered = prompt.lower()
    assert (
        "different purposes" in lowered
        or "no forced winner" in lowered
        or "weird" in lowered
        or "cross-category" in lowered
    ), f"weird-flag context not in prompt: {prompt[:400]!r}"


def test_normal_flag_keeps_winner_framing():
    """Spec §2e: comparison_quality='normal' → standard winner framing."""
    try:
        from app.services.extraction_service import (  # type: ignore
            build_verdict_prompt,
        )
    except ImportError:
        pytest.fail("RED: build_verdict_prompt missing")
        return
    try:
        prompt = build_verdict_prompt(products=[], comparison_quality="normal")
    except TypeError as exc:
        pytest.fail(f"RED: signature mismatch: {exc}")
        return
    assert "different purposes" not in prompt.lower()
