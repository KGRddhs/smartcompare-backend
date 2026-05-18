"""Bundle C — structured_comparison_service tests (Section C plan, task C.2.1).

Covers:
  - C.2.1 — `_classify_comparison_quality` 3-state classifier
    (`normal` / `weak` / `weird`) per spec § 2e.

These tests stay RED until the A.x weird-comparison detector + classifier land.

Triggers for `weird` per spec § 2e:
  - Products span unrelated categories (`cat_a != cat_b`).
  - >50% of one product's specs are missing AFTER 3-tier fallback.
  - Prices differ by 10×+ order of magnitude.

`weak` is the moderate-spec-gap fallback (one product 60–80% spec coverage,
other higher). `normal` is everything else.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "scenario,expected",
    [
        # — category mismatch → weird —
        (
            dict(
                cat_a="electronics", cat_b="fragrances",
                spec_coverage_a=1.0, spec_coverage_b=1.0,
                price_a=100, price_b=120,
            ),
            "weird",
        ),
        # — >50% specs missing on product A post-Tier-3 → weird —
        (
            dict(
                cat_a="electronics", cat_b="electronics",
                spec_coverage_a=0.3, spec_coverage_b=1.0,
                price_a=100, price_b=120,
            ),
            "weird",
        ),
        # — >50% specs missing on product B post-Tier-3 → weird —
        (
            dict(
                cat_a="skincare", cat_b="skincare",
                spec_coverage_a=1.0, spec_coverage_b=0.4,
                price_a=20, price_b=30,
            ),
            "weird",
        ),
        # — 10× price spread → weird —
        (
            dict(
                cat_a="electronics", cat_b="electronics",
                spec_coverage_a=1.0, spec_coverage_b=1.0,
                price_a=10, price_b=200,
            ),
            "weird",
        ),
        # — exactly 10× → weird (boundary, exclusive vs inclusive; spec § 2e says "10×+") —
        (
            dict(
                cat_a="fashion", cat_b="fashion",
                spec_coverage_a=1.0, spec_coverage_b=1.0,
                price_a=10, price_b=100,
            ),
            "weird",
        ),
        # — moderate spec gap → weak —
        (
            dict(
                cat_a="electronics", cat_b="electronics",
                spec_coverage_a=0.6, spec_coverage_b=0.9,
                price_a=100, price_b=200,
            ),
            "weak",
        ),
        # — moderate spec gap on product A → weak —
        (
            dict(
                cat_a="haircare", cat_b="haircare",
                spec_coverage_a=0.9, spec_coverage_b=0.7,
                price_a=15, price_b=20,
            ),
            "weak",
        ),
        # — all normal → normal —
        (
            dict(
                cat_a="electronics", cat_b="electronics",
                spec_coverage_a=1.0, spec_coverage_b=0.9,
                price_a=100, price_b=140,
            ),
            "normal",
        ),
        # — small price spread + good coverage → normal —
        (
            dict(
                cat_a="fragrances", cat_b="fragrances",
                spec_coverage_a=0.85, spec_coverage_b=0.85,
                price_a=80, price_b=120,
            ),
            "normal",
        ),
    ],
)
def test_comparison_quality_classifier(scenario, expected):
    """Spec § 2e: 3-state classifier — normal / weak / weird."""
    try:
        from app.services.structured_comparison_service import (  # type: ignore
            _classify_comparison_quality,
        )
    except ImportError:
        pytest.fail(
            "RED: A.x not yet shipped — _classify_comparison_quality missing "
            "from app.services.structured_comparison_service"
        )
        return
    assert _classify_comparison_quality(**scenario) == expected


def test_comparison_quality_returns_one_of_three_states():
    """Invariant: classifier always returns from the 3-state enum."""
    try:
        from app.services.structured_comparison_service import (  # type: ignore
            _classify_comparison_quality,
        )
    except ImportError:
        pytest.fail("RED: _classify_comparison_quality not yet shipped")
        return
    out = _classify_comparison_quality(
        cat_a="electronics", cat_b="electronics",
        spec_coverage_a=1.0, spec_coverage_b=1.0,
        price_a=100, price_b=110,
    )
    assert out in {"normal", "weak", "weird"}


def test_comparison_quality_in_response_metadata_payload():
    """Spec § 2e: backend emits `comparison_quality` field somewhere in the
    response payload (metadata or scoring_v2). Integration-shape test.

    RED until the value is wired into `build_comparison_response`.
    """
    try:
        from app.services.response_builder import build_comparison_response  # type: ignore
    except ImportError:
        pytest.skip("response_builder not importable")
        return

    # Smoke shape — caller must pass `comparison_quality` through and builder
    # must echo it back to a user-discoverable place (metadata or scoring_v2).
    try:
        response = build_comparison_response(
            products=[
                {"name": "iPhone", "specs": {}, "price": {"amount": 100}},
                {"name": "Galaxy", "specs": {}, "price": {"amount": 100}},
            ],
            comparison={"winner_index": 0},
            metadata={"comparison_quality": "weird"},
        )
    except TypeError:
        pytest.fail(
            "RED: build_comparison_response signature does not yet accept "
            "metadata.comparison_quality — Bundle C §2e wiring incomplete"
        )
        return

    # Search for the key anywhere user-discoverable
    quality_value = None
    metadata = (response.get("metadata", {}) or {})
    scoring_v2 = (response.get("scoring_v2", {}) or {})
    if "comparison_quality" in metadata:
        quality_value = metadata["comparison_quality"]
    elif "comparison_quality" in scoring_v2:
        quality_value = scoring_v2["comparison_quality"]
    assert quality_value == "weird", (
        "RED: comparison_quality not propagated to response. "
        f"metadata={metadata}, scoring_v2={scoring_v2}"
    )
