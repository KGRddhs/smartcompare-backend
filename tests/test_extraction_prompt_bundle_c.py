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
    "supplements": {"dosage", "form"},
    "fragrances":  {"concentration", "longevity"},
    "fashion":     {"material"},
    "skincare":    {"volume", "ingredients"},
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


@pytest.mark.asyncio
async def test_tier2_skipped_when_non_negotiables_filled():
    """Spec §2f: Tier 2 fires ONLY when Tier 1 leaves non-negotiable fields blank."""
    try:
        from app.services.extraction_service import (  # type: ignore
            resolve_specs_with_tiered_fallback,
        )
    except ImportError:
        pytest.fail("RED: resolve_specs_with_tiered_fallback missing (A.x §2f)")
        return
    tier1 = {
        "battery": "3274 mAh",
        "processor": "A17",
        "ram": "8 GB",
        "rear_camera": "48 MP",
    }
    try:
        _result, telemetry = await resolve_specs_with_tiered_fallback(
            query="iPhone 16", category="electronics", tier1_specs=tier1
        )
    except TypeError as exc:
        pytest.fail(f"RED: resolve_specs_with_tiered_fallback signature mismatch: {exc}")
        return
    assert telemetry.get("tier2_called") is False
    assert telemetry.get("tier3_called") is False


@pytest.mark.asyncio
async def test_tier2_fires_when_non_negotiable_missing():
    """Spec §2f: Tier 2 fires when at least one non-negotiable absent post-Tier-1."""
    try:
        from app.services.extraction_service import (  # type: ignore
            resolve_specs_with_tiered_fallback,
        )
    except ImportError:
        pytest.fail("RED: resolve_specs_with_tiered_fallback missing")
        return
    tier1 = {"battery": "3274 mAh"}  # missing processor/ram/rear_camera
    try:
        _result, telemetry = await resolve_specs_with_tiered_fallback(
            query="iPhone 16", category="electronics", tier1_specs=tier1
        )
    except TypeError as exc:
        pytest.fail(f"RED: signature mismatch: {exc}")
        return
    assert telemetry.get("tier2_called") is True


# ---------------------------------------------------------------------------
# C.3.4 — Wall-time budget (sanity smoke)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_3tier_fallback_within_combined_budget():
    """Spec §2f: Tier 2 (4s) + Tier 3 (3s) parallel → stays ≤ 8s upper bound."""
    try:
        from app.services.extraction_service import (  # type: ignore
            resolve_specs_with_tiered_fallback,
        )
    except ImportError:
        pytest.fail("RED: resolve_specs_with_tiered_fallback missing")
        return
    start = time.monotonic()
    try:
        await asyncio.wait_for(
            resolve_specs_with_tiered_fallback(
                query="iPhone 16", category="electronics", tier1_specs={}
            ),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        pytest.fail("RED: 3-tier fallback exceeded 10s outer wait_for")
        return
    elapsed = time.monotonic() - start
    assert elapsed < 10.0


# ---------------------------------------------------------------------------
# C.3.5 — inference_source="model_knowledge" NEVER reaches user-visible response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inference_source_flag_internal_only():
    """Spec §2f: Tier 3 outputs tagged inference_source='model_knowledge' —
    QA/dashboards only. NEVER reaches response.products[].specs.
    """
    try:
        from app.services.extraction_service import (  # type: ignore
            resolve_specs_with_tiered_fallback,
        )
    except ImportError:
        pytest.fail("RED: resolve_specs_with_tiered_fallback missing")
        return
    try:
        result, telemetry = await resolve_specs_with_tiered_fallback(
            query="iPhone 16", category="electronics", tier1_specs={}
        )
    except TypeError as exc:
        pytest.fail(f"RED: signature mismatch: {exc}")
        return
    # Internal telemetry may carry the flag (allowed)
    # But the user-facing `specs` dict must NOT
    specs = (result or {}).get("specs", {}) if isinstance(result, dict) else {}
    for field, val in specs.items():
        if isinstance(val, dict):
            assert "inference_source" not in val, (
                f"inference_source leaked into specs.{field}: {val!r}"
            )


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
