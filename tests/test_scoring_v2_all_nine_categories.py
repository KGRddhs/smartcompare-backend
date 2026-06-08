"""Lane 1 idle-time expansion — full 9-category coverage sweep.

Pre-pin every Lane 1 invariant against ALL 9 categories so the M2 merge
can't quietly regress one of the 6 long-tail categories that weren't
covered by L1.2's electronics / fragrances / supplements fixtures.

Fixtures captured from production 2026-06-08 via:
    curl "https://web-production-58776.up.railway.app/api/v1/text/compare
          ?q=<query>&region=bahrain&nocache=true"

Asserted per fixture:
- (a) scoring_v2.dimensions has 3 core + ≥1 category-specific dim
- (b) every emitted dim has populated winner OR both score_a/score_b
- (c) scoring_v2.factual_verdict.line1/line2 populated
- (d) confidence_legs / confidence_details 3-leg shape
- (e) overview.products[i].variant is a string
- (f) overview.products[i].pros_cons populated with is_winner flag
- (g) specs.specs_comparison.rows is a list (may be empty for thin-spec
      categories like fashion)

Note: the captured `other` fixture got auto-classified to `grocery` by
the production PRODUCT_PARSER_PROMPT (SodaStream Terra → grocery). The
test treats it as grocery — but the file name + fixture preserve the
edge case for future category-switch regression analysis.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import _build_scoring_v2, build_comparison_response
from app.services.scoring_service import CATEGORY_DIMENSIONS
from tests.fixtures.lane1._helpers import build_inputs


# Per-category expected dim keys — the `_score` suffix stripped per L1.3.
# Loaded dynamically from CATEGORY_DIMENSIONS so the test stays in sync
# with future schema changes.
def _expected_category_dim_keys(category: str) -> set[str]:
    raw = CATEGORY_DIMENSIONS.get(category, [])
    return {k[:-6] if k.endswith("_score") else k for k in raw}


CATEGORY_FIXTURES = [
    # (fixture_filename, declared_category)
    # 3 original fixtures from L1.2
    ("iphone15_vs_galaxys24_response.json", "electronics"),
    ("tomford_vs_creed_response.json", "fragrances"),
    ("now_vs_solgar_response.json", "supplements"),
    # 6 idle-time fixtures captured 2026-06-08
    ("grocery_response.json", "grocery"),
    ("makeup_response.json", "makeup"),
    ("skincare_response.json", "skincare"),
    ("haircare_response.json", "haircare"),
    ("fashion_response.json", "fashion"),
    # `other` query (SodaStream vs Aarke) got auto-classified to `grocery`
    # by PRODUCT_PARSER_PROMPT — assert against grocery, not other.
    ("other_response.json", "grocery"),
]


# ---------------------------------------------------------------------------
# Invariant (a) — at least one category-specific dim surfaces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,category", CATEGORY_FIXTURES)
def test_scoring_v2_emits_category_dim_for_all_nine_categories(filename, category):
    pd, sr, cat, wi = build_inputs(filename)
    # Override the category if the parser reclassified — the test pins
    # what the LIVE category-flow ships, not what the user typed.
    actual_cat = cat or category
    v2 = _build_scoring_v2(pd, sr, actual_cat, wi)
    dim_keys = {d.get("key") for d in v2.get("dimensions", []) or []}
    expected = _expected_category_dim_keys(actual_cat)
    assert dim_keys & expected, (
        f"{filename} ({actual_cat}) dim_keys={dim_keys!r} contains none of "
        f"the expected category-specific dims {expected!r}"
    )


# ---------------------------------------------------------------------------
# Invariant (b) — every dim has winner OR scores
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,category", CATEGORY_FIXTURES)
def test_every_emitted_dim_renders_a_row(filename, category):
    pd, sr, cat, wi = build_inputs(filename)
    v2 = _build_scoring_v2(pd, sr, cat or category, wi)
    dims = v2.get("dimensions") or []
    assert dims, f"{filename} emitted zero dims"
    for d in dims:
        sa, sb = d.get("score_a"), d.get("score_b")
        winner = d.get("winner")
        assert winner is not None or (sa is not None and sb is not None), (
            f"{filename} dim {d.get('key')!r} has no winner AND no score pair: {d!r}"
        )


# ---------------------------------------------------------------------------
# Invariant (c) — factual_verdict line1+line2 populated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,category", CATEGORY_FIXTURES)
def test_factual_verdict_line1_line2_populated_all_nine_categories(filename, category):
    pd, sr, cat, wi = build_inputs(filename)
    v2 = _build_scoring_v2(pd, sr, cat or category, wi)
    fv = v2.get("factual_verdict") or {}
    assert fv.get("line1"), f"{filename} line1 empty"
    assert fv.get("line2"), f"{filename} line2 empty"
    assert len(fv["line1"]) > 10
    assert len(fv["line2"]) > 10


# ---------------------------------------------------------------------------
# Invariant (d) — confidence_legs / confidence_details
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,category", CATEGORY_FIXTURES)
def test_confidence_legs_and_details_for_all_nine_categories(filename, category):
    pd, sr, cat, wi = build_inputs(filename)
    v2 = _build_scoring_v2(pd, sr, cat or category, wi)
    legs = v2.get("confidence_legs") or {}
    for leg in ("price", "reviews", "specs"):
        assert leg in legs, f"{filename} confidence_legs missing {leg!r}"
        assert legs[leg] in ("strong", "acceptable", "weak"), (
            f"{filename} confidence_legs.{leg}={legs[leg]!r} not in enum"
        )
    details = v2.get("confidence_details") or {}
    for leg in ("price", "reviews", "specs"):
        assert leg in details, f"{filename} confidence_details missing {leg!r}"
        assert isinstance(details[leg], dict)


# ---------------------------------------------------------------------------
# Invariant (e) + (f) + (g) — overview + specs full-response shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,category", CATEGORY_FIXTURES)
def test_full_response_shape_for_all_nine_categories(filename, category):
    """End-to-end: every overview/specs contract must hold across all 9
    categories. Drives `build_comparison_response()` rather than just the
    v2 builder so any cross-cutting concerns (variant composition,
    pros_cons block, specs_comparison.rows) are exercised."""
    pd, sr, cat, wi = build_inputs(filename)
    actual_cat = cat or category
    resp = build_comparison_response(
        products=pd,
        comparison={"winner_index": wi},
        scoring_result=sr,
        category_used=actual_cat,
    )

    # Overview shape ---------------------------------------------------
    ov_products = resp["overview"]["products"]
    assert len(ov_products) >= 2
    for op in ov_products:
        # (e) variant string
        assert "variant" in op
        assert isinstance(op["variant"], str)
        # (f) pros_cons block
        pc = op.get("pros_cons")
        assert isinstance(pc, dict)
        assert "pros" in pc
        assert "cons" in pc
        assert "is_winner" in pc
        assert isinstance(pc["is_winner"], bool)
    # Exactly one winner
    winners = [op["pros_cons"]["is_winner"] for op in ov_products]
    assert winners.count(True) == 1, (
        f"{filename}: expected exactly one winner; got {winners!r}"
    )

    # Specs shape ------------------------------------------------------
    sc = resp["specs"]["specs_comparison"]
    assert isinstance(sc, dict)
    assert "rows" in sc
    assert isinstance(sc["rows"], list)
    # Each row (when present) has the required shape — but `rows` MAY be
    # empty for thin-spec categories like fashion where the AI extraction
    # didn't produce shared spec fields between the two products.
    for row in sc["rows"]:
        assert "field" in row
        assert "p0_value" in row
        assert "p1_value" in row
        assert "winner" in row
        assert row["winner"] in (0, 1, "tie", None)


# ---------------------------------------------------------------------------
# Cross-category forbidden-vocab sweep — no scary copy / no leakage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,category", CATEGORY_FIXTURES)
def test_no_scary_vocab_in_lane1_strings(filename, category):
    forbidden = [
        "couldn't",
        "try again",
        "failed to",
        "estimated",
        "reference price",
        "approximate",
    ]
    pd, sr, cat, wi = build_inputs(filename)
    actual_cat = cat or category
    resp = build_comparison_response(
        products=pd,
        comparison={"winner_index": wi},
        scoring_result=sr,
        category_used=actual_cat,
    )
    v2 = resp.get("scoring_v2") or {}

    # factual_verdict
    fv = v2.get("factual_verdict") or {}
    for key in ("line1", "line2"):
        text = (fv.get(key) or "").lower()
        for word in forbidden:
            assert word not in text, (
                f"{filename} factual_verdict.{key} contains forbidden {word!r}: {text!r}"
            )

    # dim delta_text
    for d in v2.get("dimensions", []):
        text = (d.get("delta_text") or "").lower()
        for word in forbidden:
            assert word not in text, (
                f"{filename} dim {d.get('key')} delta_text contains forbidden {word!r}: {text!r}"
            )

    # Overview value_context
    for op in resp["overview"]["products"]:
        vc = (op.get("value_context") or "").lower()
        for word in forbidden:
            assert word not in vc, (
                f"{filename} overview value_context contains forbidden {word!r}: {vc!r}"
            )
