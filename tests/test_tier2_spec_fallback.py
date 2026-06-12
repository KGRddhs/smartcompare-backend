"""Bundle C § 2f A.4.7 — Tier 2 spec fallback (targeted per missing non-negotiable).

Per design § 2f Step 2 + plan A.4.7: when Tier 1 + smart-fallback leave
NON_NEGOTIABLE schema fields blank, Tier 2 fires one targeted Serper
+ GPT-mini extract per missing field. Parallel, 4s wall hard cap,
0.5s per-field budget, 1 retry per field. Silent omission per § 2h
on timeout / failure — no exception escapes.

Wall-budget discipline (CRITICAL per team-lead):
- Tier 2 fires ONLY when non-negotiables remain blank — most happy-
  path comparisons skip it entirely (zero added latency).
- 4s outer asyncio.wait_for caps the worst case.
- Stays inside the existing STREAM_HARD_CAP_SECONDS=25 outer wait.
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.services.structured_comparison_service import tier2_fill_non_negotiables


@pytest.mark.asyncio
async def test_tier2_returns_empty_when_no_non_negotiables_missing():
    """Happy path: when all non-negotiable fields are already filled,
    Tier 2 short-circuits with an empty dict — no Serper/GPT calls."""
    specs_so_far = {
        "battery": "3274 mAh", "processor": "A17 Pro",
        "ram": "8 GB", "rear_camera": "48 MP",
    }
    out = await tier2_fill_non_negotiables(
        brand="Apple", name="iPhone 16", variant=None,
        category="electronics", specs_so_far=specs_so_far,
    )
    assert out == {}


@pytest.mark.asyncio
async def test_tier2_returns_empty_for_unknown_category():
    """Unknown category → no non-negotiables → no-op."""
    out = await tier2_fill_non_negotiables(
        brand="X", name="Y", variant=None,
        category="other",  # 'other' has no non-negotiables per §2f
        specs_so_far={},
    )
    assert out == {}


@pytest.mark.asyncio
async def test_tier2_fires_for_missing_non_negotiable(monkeypatch):
    """When a non-negotiable is blank, Tier 2 issues a targeted GPT
    call and merges the result. Mocked end-to-end with no live API."""
    specs_so_far = {"processor": "A17 Pro"}  # battery, ram, rear_camera missing

    async def _fake_extract(*, brand, name, variant, category, fields, context):
        # Mock GPT returns values for the missing fields
        return {"battery": "3274 mAh", "ram": "8 GB", "rear_camera": "48 MP"}

    async def _fake_search(*args, **kwargs):
        return {"organic": [{"snippet": "iPhone 16 spec sheet"}]}

    with patch(
        "app.services.openai_service.extract_specs_targeted",
        new=_fake_extract,
    ):
        with patch(
            "app.services.serper_service.search_web",
            new=_fake_search,
        ):
            out = await tier2_fill_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics", specs_so_far=specs_so_far,
            )
    assert out == {"battery": "3274 mAh", "ram": "8 GB", "rear_camera": "48 MP"}


@pytest.mark.asyncio
async def test_tier2_respects_4s_wall_cap(monkeypatch):
    """Per spec § 2f: 4s outer wall. Slow GPT must NOT block past that."""
    async def _slow_extract(*args, **kwargs):
        await asyncio.sleep(10.0)  # would exceed wall
        return {"battery": "never"}

    async def _fake_search(*args, **kwargs):
        return {"organic": [{"snippet": "x"}]}

    with patch(
        "app.services.openai_service.extract_specs_targeted",
        new=_slow_extract,
    ):
        with patch(
            "app.services.serper_service.search_web",
            new=_fake_search,
        ):
            start = asyncio.get_event_loop().time()
            out = await tier2_fill_non_negotiables(
                brand="X", name="Y", variant=None,
                category="electronics", specs_so_far={},
            )
            elapsed = asyncio.get_event_loop().time() - start
    assert out == {}, "timeout must yield empty dict per silent-omit contract"
    assert elapsed < 5.0, (
        f"Tier 2 exceeded 4s wall cap: elapsed={elapsed:.2f}s"
    )


@pytest.mark.asyncio
async def test_tier2_silent_on_exception(monkeypatch):
    """Per spec § 2h: any exception from Serper or GPT → empty dict.
    NO exception escapes."""
    async def _raising(*args, **kwargs):
        raise RuntimeError("simulated upstream failure")

    with patch(
        "app.services.openai_service.extract_specs_targeted",
        new=_raising,
    ):
        with patch(
            "app.services.serper_service.search_web",
            new=_raising,
        ):
            out = await tier2_fill_non_negotiables(
                brand="X", name="Y", variant=None,
                category="electronics", specs_so_far={},
            )
    assert out == {}


@pytest.mark.asyncio
async def test_tier2_only_fills_blank_fields_does_not_overwrite():
    """When Tier 1 already filled a field, Tier 2 must not overwrite it.
    Only blank/missing/N/A fields are candidates."""
    specs_so_far = {
        "processor": "A17 Pro",  # filled
        "ram": "N/A",            # treated as missing
        "battery": "",           # treated as missing
        # rear_camera missing entirely
    }

    called_with_fields: list = []

    async def _fake_extract(*, brand, name, variant, category, fields, context):
        # Tier 2 fires ONE call per missing field (parallel), so we record
        # each call's `fields` arg. Verify processor is NEVER asked for
        # (it's already populated).
        called_with_fields.append(list(fields))
        assert "processor" not in fields, (
            f"Tier 2 incorrectly tried to refill 'processor': fields={fields}"
        )
        # Each call has exactly one field (per-field parallel architecture)
        assert len(fields) == 1, f"expected single-field call; got {fields}"
        field = fields[0]
        values = {"battery": "3274mAh", "ram": "8GB", "rear_camera": "48MP"}
        return {field: values.get(field)} if field in values else {}

    async def _fake_search(*args, **kwargs):
        return {"organic": [{"snippet": "x"}]}

    with patch(
        "app.services.openai_service.extract_specs_targeted",
        new=_fake_extract,
    ):
        with patch(
            "app.services.serper_service.search_web",
            new=_fake_search,
        ):
            out = await tier2_fill_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics", specs_so_far=specs_so_far,
            )
    # Output contains only the newly-filled fields (not processor)
    assert "processor" not in out
    assert set(out.keys()) == {"battery", "ram", "rear_camera"}
    # And the parallel calls collectively covered exactly the missing set.
    flat_called = {f for fields in called_with_fields for f in fields}
    assert flat_called == {"battery", "ram", "rear_camera"}


# ---------------------------------------------------------------------------
# S2 I3.6 (Decision B) — active_ingredient now NON-NEGOTIABLE for supp+skin,
# so a blank active_ingredient enters the Tier-2 fill cascade. These pin the
# fill-ATTEMPT coverage for the probiotic / vitamin-C-serum class that
# scored specs_score=0.0 in the S1 baseline (supp-010, skin-012).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier2_targets_active_ingredient_for_probiotic():
    """supp-010 class: a probiotic with blank active_ingredient. Post-
    promotion, Tier 2 MUST attempt to fill active_ingredient (it's now
    non-negotiable), where pre-S2 it was preferred-only and skipped."""
    specs_so_far = {"dosage": "10 billion CFU", "form": "Capsule"}  # active_ingredient blank

    called_with_fields: list = []

    async def _fake_extract(*, brand, name, variant, category, fields, context):
        called_with_fields.append(list(fields))
        field = fields[0]
        return {field: "Probiotic"} if field == "active_ingredient" else {}

    async def _fake_search(*args, **kwargs):
        return {"organic": [{"snippet": "Culturelle probiotic Lactobacillus"}]}

    with patch("app.services.openai_service.extract_specs_targeted", new=_fake_extract):
        with patch("app.services.serper_service.search_web", new=_fake_search):
            out = await tier2_fill_non_negotiables(
                brand="Culturelle", name="Daily Probiotic", variant=None,
                category="supplements", specs_so_far=specs_so_far,
            )
    flat_called = {f for fields in called_with_fields for f in fields}
    assert "active_ingredient" in flat_called, (
        f"Tier 2 did not target active_ingredient for a probiotic — the I3.6 "
        f"promotion is not wired: fields attempted={flat_called}"
    )
    assert out.get("active_ingredient") == "Probiotic"


@pytest.mark.asyncio
async def test_tier2_targets_active_ingredient_for_vitamin_c_serum():
    """skin-012 class: a vitamin-C serum with blank active_ingredient.
    Post-promotion Tier 2 attempts it (skincare non-negotiable now)."""
    specs_so_far = {"volume": "30ml", "ingredients": "Aqua, Ascorbic Acid"}  # active_ingredient blank

    called_with_fields: list = []

    async def _fake_extract(*, brand, name, variant, category, fields, context):
        called_with_fields.append(list(fields))
        field = fields[0]
        return {field: "Vitamin C"} if field == "active_ingredient" else {}

    async def _fake_search(*args, **kwargs):
        return {"organic": [{"snippet": "Garnier Vitamin C serum brightening"}]}

    with patch("app.services.openai_service.extract_specs_targeted", new=_fake_extract):
        with patch("app.services.serper_service.search_web", new=_fake_search):
            out = await tier2_fill_non_negotiables(
                brand="Garnier", name="Vitamin C Serum", variant=None,
                category="skincare", specs_so_far=specs_so_far,
            )
    flat_called = {f for fields in called_with_fields for f in fields}
    assert "active_ingredient" in flat_called, (
        f"Tier 2 did not target active_ingredient for a vitamin-C serum — "
        f"I3.6 promotion not wired: fields attempted={flat_called}"
    )
    assert out.get("active_ingredient") == "Vitamin C"
