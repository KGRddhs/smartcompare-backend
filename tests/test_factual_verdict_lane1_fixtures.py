"""Lane 1 L1.5 — factual_verdict line1/line2 regression net using prod fixtures.

The Bundle C A.3.2 builder (test_response_builder_factual_verdict.py) ships
in prod and populates line1/line2 against synthetic inputs. This file pins
the contract against REAL prod responses for 3 categories so the L1.3
dimension rewrite doesn't quietly degrade the verdict copy.

After L1.3 the dim list surfaces category-specific dims (performance /
build_quality / longevity / etc.), so the `_runner_up_dim_candidate` path
in `_format_line2` now resolves to category-aware strings like
`"Galaxy S24 pulls ahead on Build quality."` instead of falling back to
the generic price/rating tail.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import _build_scoring_v2
from tests.fixtures.lane1._helpers import build_inputs


def _factual_verdict(filename: str):
    pd, sr, cat, wi = build_inputs(filename)
    v2 = _build_scoring_v2(pd, sr, cat, wi)
    return v2.get("factual_verdict") or {}


# ---------------------------------------------------------------------------
# line1 — winner anchor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected_names",
    [
        (
            "iphone15_vs_galaxys24_response.json",
            ("iPhone", "Galaxy", "Samsung", "Apple"),
        ),
        (
            "tomford_vs_creed_response.json",
            ("Black Orchid", "Aventus", "Tom Ford", "Creed"),
        ),
        (
            "now_vs_solgar_response.json",
            ("NOW", "Solgar", "Vitamin D3", "D3"),
        ),
    ],
)
def test_factual_verdict_line1_references_a_product(filename, expected_names):
    fv = _factual_verdict(filename)
    line1 = fv.get("line1") or ""
    assert line1, f"line1 empty for {filename}"
    assert any(n in line1 for n in expected_names), (
        f"line1 doesn't reference any of {expected_names!r}: {line1!r}"
    )


# ---------------------------------------------------------------------------
# line2 — counter-fact must be substantive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "iphone15_vs_galaxys24_response.json",
        "tomford_vs_creed_response.json",
        "now_vs_solgar_response.json",
    ],
)
def test_factual_verdict_line2_populated(filename):
    fv = _factual_verdict(filename)
    line2 = fv.get("line2") or ""
    assert line2, f"line2 empty for {filename}"
    assert len(line2) > 10, f"line2 too short for {filename}: {line2!r}"


def test_factual_verdict_line1_line2_differ_for_electronics():
    fv = _factual_verdict("iphone15_vs_galaxys24_response.json")
    line1 = fv.get("line1") or ""
    line2 = fv.get("line2") or ""
    assert line1 and line2
    assert line1 != line2


# ---------------------------------------------------------------------------
# Copy contract — no scary words, no backend leakage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "iphone15_vs_galaxys24_response.json",
        "tomford_vs_creed_response.json",
        "now_vs_solgar_response.json",
    ],
)
def test_factual_verdict_no_forbidden_copy(filename):
    fv = _factual_verdict(filename)
    forbidden = [
        "couldn't",
        "try again",
        "failed",
        "estimated",
        "reference price",
        "approximate",
        "coefficient",
        "missing_score",
    ]
    for line_name in ("line1", "line2"):
        line = (fv.get(line_name) or "").lower()
        for word in forbidden:
            assert word not in line, (
                f"{filename} {line_name} contains forbidden {word!r}: {line!r}"
            )
