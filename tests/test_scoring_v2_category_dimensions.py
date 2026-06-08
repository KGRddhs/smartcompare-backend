"""Lane 1 Task L1.1 / L1.3 — v2.dimensions must source from CATEGORY_DIMENSIONS.

Current prod emits a generic 3-4 dim array (`price`, `reviews`, `value`,
`popularity`) for every category, dropping the per-category dim list (e.g.
fragrances should expose `character`, `longevity`, `projection`).

These tests are RED on the current Bundle D implementation and turn GREEN
after Task L1.3's `build_dimensions_v2` rewrite + `_dim_from_category_lookup`
bugfix (must read `scores.product_i.breakdown[dim_key]` rather than the
nonexistent `scores.product_i[dim_key]`).
"""
from __future__ import annotations

import pytest

from app.services.response_builder import _build_scoring_v2
from tests.fixtures.lane1._helpers import build_inputs


def _dim_keys(scoring_v2: dict) -> list[str]:
    return [d.get("key") for d in scoring_v2.get("dimensions", []) or []]


# ---------------------------------------------------------------------------
# Electronics
# ---------------------------------------------------------------------------


def test_scoring_v2_emits_category_dimensions_for_electronics():
    """Electronics v2 must surface at least one of the category-specific
    `CATEGORY_DIMENSIONS['electronics']` dims — performance / build_quality /
    feature / ecosystem / futureproof — not just the generic `popularity`
    fallback."""
    pd, sr, cat, wi = build_inputs("iphone15_vs_galaxys24_response.json")
    v2 = _build_scoring_v2(pd, sr, cat, wi)
    keys = _dim_keys(v2)
    expected_any = {
        "performance",
        "build_quality",
        "feature",
        "ecosystem",
        "futureproof",
        # The CATEGORY_DIMENSIONS keys have a `_score` suffix; accept either
        # form so the v2 adapter can normalise as it sees fit.
        "performance_score",
        "build_quality_score",
        "feature_score",
        "ecosystem_score",
        "futureproof_score",
    }
    assert any(k in expected_any for k in keys), (
        f"electronics dim_keys={keys!r} contains no category-specific dim; "
        "expected at least one of performance / build_quality / feature / "
        "ecosystem / futureproof"
    )


def test_scoring_v2_dims_have_populated_winner_for_electronics():
    """Every dim emitted MUST expose either `winner` ∈ {0,1,'tie'} or a
    pair of non-null `score_a` / `score_b` so the frontend can derive a
    winner. Prod regression: silent-omission contract drops dims with
    both scores `None`, which currently swallows ALL electronics
    category dims because the upstream lookup reads the wrong path."""
    pd, sr, cat, wi = build_inputs("iphone15_vs_galaxys24_response.json")
    v2 = _build_scoring_v2(pd, sr, cat, wi)
    dims = v2.get("dimensions", []) or []
    assert dims, "electronics scoring_v2 emitted zero dims"
    for dim in dims:
        sa, sb = dim.get("score_a"), dim.get("score_b")
        winner = dim.get("winner")
        # At least one of the contracts must hold so the FE renders a row.
        assert winner is not None or (
            sa is not None and sb is not None
        ), f"dim {dim.get('key')!r} has no winner AND no score pair: {dim!r}"


# ---------------------------------------------------------------------------
# Fragrances — proves the bug isn't electronics-only
# ---------------------------------------------------------------------------


def test_scoring_v2_emits_category_dimensions_for_fragrances():
    pd, sr, cat, wi = build_inputs("tomford_vs_creed_response.json")
    v2 = _build_scoring_v2(pd, sr, cat, wi)
    keys = _dim_keys(v2)
    expected_any = {
        "character",
        "longevity",
        "projection",
        "versatility",
        "wear_value",
        "presentation",
        "character_score",
        "longevity_score",
        "projection_score",
        "versatility_score",
        "wear_value_score",
        "presentation_score",
    }
    assert any(k in expected_any for k in keys), (
        f"fragrances dim_keys={keys!r} contains no category-specific dim"
    )


# ---------------------------------------------------------------------------
# Supplements — third category proves the fix generalises
# ---------------------------------------------------------------------------


def test_scoring_v2_emits_category_dimensions_for_supplements():
    pd, sr, cat, wi = build_inputs("now_vs_solgar_response.json")
    v2 = _build_scoring_v2(pd, sr, cat, wi)
    keys = _dim_keys(v2)
    expected_any = {
        "efficacy",
        "safety",
        "dosage",
        "serving_value",
        "form",
        "trust",
        "efficacy_score",
        "safety_score",
        "dosage_score",
        "serving_value_score",
        "form_score",
        "trust_score",
    }
    assert any(k in expected_any for k in keys), (
        f"supplements dim_keys={keys!r} contains no category-specific dim"
    )
