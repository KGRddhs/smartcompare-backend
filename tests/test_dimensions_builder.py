"""
Bundle E Task 1.3 RED — build_dimensions_v2() emits the self-describing
dimensions[] contract from design § Decision 2.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 1.3,
      § Test-1.3)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 2.

Contract under test:

    def build_dimensions_v2(
        products_data: list[dict],         # already-extracted product dicts
        scoring_result: dict,              # output of compute_scores()
        category: str,                     # e.g. "electronics" / "skincare"
    ) -> list[dict]:
        \"\"\"Returns a list of Dimension-shaped dicts (matches
        app.models.scoring_v2.Dimension keys: key, label, score_a,
        score_b, delta_text, confidence, is_core). Ordered: 3 core
        dimensions first, then 0..3 contextual dimensions.\"\"\"

Invariants (design § Decision 2):

  1. ALWAYS emits exactly 3 core dimensions (price, reviews, value) with
     is_core=True. Never fewer.
  2. NEVER emits a contextual dimension where EITHER product is missing
     the data. Design quote: "A dimension is never emitted if either
     product lacks the data. No empty bars. Ever."
  3. Build/Reliability dimension is emitted ONLY when both products have
     brand_reputation + warranty signals.
  4. Popularity is emitted ONLY when both products have review_count > 50.
  5. Category-specific contextual dimensions (DPI for mice, RGB for
     keyboards, actives for skincare, etc.) only when BOTH products
     have that spec.
  6. Cross-category comparisons (mouse vs skincare) emit ONLY the 3
     universal core dims — no category-specific extras.
  7. Order: core dimensions first (price, reviews, value), contextual
     dimensions follow.
  8. Each dimension's delta_text is factual (no banned evaluative
     words: best, pick, excellent, great, recommend, winner, worst,
     better, worse, beats, smart, good, choose).

RED→GREEN trajectory:
  - At HEAD: `build_dimensions_v2` does not yet exist in
    app.services.scoring_service → ImportError at module-import time.
    All test methods fail at collection.
  - After Agent A lands Task 1.3: all assertions pass.

Note on contract inference:
  The plan task list (§ Test-1.3) specifies the BEHAVIOR but not the
  exact call signature. I have inferred `(products_data, scoring_result,
  category)` from the existing `ScoringService.compute_scores` signature
  + Decision 2 contract. If Agent A's commit uses a different signature,
  Agent A may either adjust the impl to match these tests OR open a
  send-back with the preferred signature and I will rewrite. This is
  intentional — TDD discipline is "write the test, let the test drive
  the API shape", not "guess and hope".
"""

from __future__ import annotations

import re
import pytest

# RED gate — ImportError until Agent A lands Task 1.3.
from app.services.scoring_service import build_dimensions_v2  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures — fully-populated, partial, and cross-category product pairs
# ---------------------------------------------------------------------------

# 13-word banned vocabulary from Agent A's pre-read (QA log 16:17) and
# repeated in dispatcher's Task #10 brief. Whole-word match, case-insensitive.
BANNED_WORDS = frozenset({
    "best", "pick", "excellent", "great", "recommend", "winner", "worst",
    "better", "worse", "beats", "smart", "good", "choose",
})
BANNED_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")\b",
    flags=re.IGNORECASE,
)


def _mouse(name: str, price: float, rating: float, review_count: int,
           dpi: int | None, brand_rep: str | None = "established",
           warranty_years: int | None = 2, **specs):
    """Build a mouse product dict mirroring the real extraction shape."""
    spec_dict = {"dpi": dpi} if dpi is not None else {}
    spec_dict.update(specs)
    return {
        "brand": "Glorious" if "glorious" in name.lower() else "Ducky",
        "name": name,
        "category": "electronics",
        "price": {"amount": price, "currency": "BHD", "estimated": False},
        "rating": rating,
        "review_count": review_count,
        "specs": spec_dict,
        "brand_reputation": brand_rep,
        "warranty_years": warranty_years,
    }


def _skincare(name: str, price: float, rating: float, review_count: int,
              actives: str | None = "niacinamide", **specs):
    spec_dict = {"actives": actives} if actives is not None else {}
    spec_dict.update(specs)
    return {
        "brand": "The Ordinary",
        "name": name,
        "category": "skincare",
        "price": {"amount": price, "currency": "BHD", "estimated": False},
        "rating": rating,
        "review_count": review_count,
        "specs": spec_dict,
        "brand_reputation": "established",
        "warranty_years": None,  # skincare has no warranty signal
    }


def _scoring_result_two_products():
    """Realistic scoring_result shape returned by compute_scores."""
    return {
        "scores": {
            "product_0": {"overall": 87, "breakdown": {}, "weights_used": {}},
            "product_1": {"overall": 82, "breakdown": {}, "weights_used": {}},
        },
        "winner_index": 0,
        "win_margin": 5,
        "scoring_method": "category_weighted",
    }


# ---------------------------------------------------------------------------
# Test 1 — Always emits the 3 core dimensions
# ---------------------------------------------------------------------------

class TestThreeCoreDimensionsAlwaysEmitted:

    def test_full_data_emits_at_least_3_core_dims(self):
        products = [
            _mouse("Glorious Model O", price=22.0, rating=4.6, review_count=1200, dpi=12000),
            _mouse("Ducky One 2 Mini", price=52.0, rating=4.4, review_count=800, dpi=None),
        ]
        # Note: Ducky has no DPI, so the contextual DPI dim is skipped.
        # Core 3 must still emit.
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        core = [d for d in result if d["is_core"]]
        assert len(core) == 3, (
            f"expected 3 core dims, got {len(core)}: keys={[d['key'] for d in core]}"
        )

    def test_core_dim_keys_are_exactly_price_reviews_value(self):
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        core_keys = {d["key"] for d in result if d["is_core"]}
        assert core_keys == {"price", "reviews", "value"}, (
            f"core key set mismatch: got {core_keys}, expected {{price, reviews, value}}"
        )

    def test_core_dims_emit_even_with_minimal_data(self):
        """Even with bare-minimum data — no review counts, no specs,
        no brand reputation — the 3 core dims MUST still emit. Design
        explicitly: "Every product has a price (or estimated), every
        product can be reviewed (or marked 'limited reviews'), Value
        is deterministic from the other two."
        """
        minimal_a = {
            "brand": "BrandA", "name": "ProductA", "category": "electronics",
            "price": {"amount": 30.0, "currency": "BHD", "estimated": True},
            "rating": None, "review_count": None, "specs": {},
            "brand_reputation": None, "warranty_years": None,
        }
        minimal_b = {
            "brand": "BrandB", "name": "ProductB", "category": "electronics",
            "price": {"amount": 35.0, "currency": "BHD", "estimated": True},
            "rating": None, "review_count": None, "specs": {},
            "brand_reputation": None, "warranty_years": None,
        }
        result = build_dimensions_v2([minimal_a, minimal_b], _scoring_result_two_products(), "electronics")
        core_keys = {d["key"] for d in result if d["is_core"]}
        assert core_keys == {"price", "reviews", "value"}, (
            f"core dims absent on minimal data: got {core_keys}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Skips contextual dim when either product lacks data
# ---------------------------------------------------------------------------

class TestContextualDimSkippedWhenDataMissing:

    def test_dpi_dim_skipped_when_one_product_lacks_dpi(self):
        """Glorious has DPI 12000; Ducky has no DPI → DPI contextual
        dimension must NOT appear in the result list."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=None),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        emitted_keys = {d["key"] for d in result}
        assert "dpi" not in emitted_keys, (
            f"DPI emitted despite missing-on-Ducky: keys={emitted_keys}"
        )

    def test_dpi_dim_NOT_emitted_post_L1_rewrite(self):
        """Lane 1 L1.3 (2026-06-08) — dropped the hand-coded `_dim_dpi`
        builder. Electronics now uses the CATEGORY_DIMENSIONS lookup +
        scoring_result.breakdown path. The legacy `dpi` key is gone."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        emitted_keys = {d["key"] for d in result}
        assert "dpi" not in emitted_keys, (
            f"DPI dim leaked post-L1.3 rewrite (should be gone): keys={emitted_keys}"
        )

    def test_popularity_dim_skipped_when_either_review_count_le_50(self):
        """Design § Decision 2: Popularity emits only when both products
        have review_count > 50."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, review_count=1200, dpi=None),
            _mouse("Niche Brand X", 25.0, 4.0, review_count=30, dpi=None),  # ≤50
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        emitted_keys = {d["key"] for d in result}
        assert "popularity" not in emitted_keys, (
            f"Popularity emitted despite low-review-count side: keys={emitted_keys}"
        )

    def test_popularity_dim_NOT_emitted_post_L1_rewrite(self):
        """Lane 1 L1.3 (2026-06-08) — dropped the hand-coded `_dim_popularity`
        builder. Electronics now uses CATEGORY_DIMENSIONS lookup;
        review-count signal is folded into the existing `reviews` core
        dim instead of a separate `popularity` row."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, review_count=1200, dpi=None),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, review_count=800, dpi=None),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        emitted_keys = {d["key"] for d in result}
        assert "popularity" not in emitted_keys

    def test_build_quality_dim_skipped_when_one_lacks_warranty(self):
        """Design § Decision 2: Build/Reliability needs brand reputation
        + warranty signals on BOTH products."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=None, warranty_years=2),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=None, warranty_years=None),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        emitted_keys = {d["key"] for d in result}
        assert "build_quality" not in emitted_keys, (
            f"Build emitted despite Ducky lacking warranty: keys={emitted_keys}"
        )

    def test_no_zero_score_dimension_ever(self):
        """Across ANY contextual dim that DID emit, both score_a and
        score_b must be non-zero. Design: "No empty bars. Ever."
        """
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        for dim in result:
            assert dim["score_a"] > 0 and dim["score_b"] > 0, (
                f"zero-score dim emitted: {dim}"
            )


# ---------------------------------------------------------------------------
# Test 3 — Cross-category emits ONLY universal dims
# ---------------------------------------------------------------------------

class TestCrossCategoryUniversalDimsOnly:
    """When the user accidentally compares apples-to-oranges (mouse vs
    skincare), no category-specific dimension can apply. The result
    must be the 3 core dims and nothing else.

    Note: production code rejects this earlier with `category_switched`,
    but `build_dimensions_v2` is a pure function that must not crash
    on mixed inputs — defensive contract.
    """

    def test_mouse_vs_skincare_emits_only_core_dims(self):
        mouse_product = _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000)
        skincare_product = _skincare("Niacinamide 10%", 5.0, 4.5, 2000, actives="niacinamide")
        # Caller passes whichever category — "other" is the conservative
        # fallback when the categories disagree. Both should produce
        # only core dims.
        for cat in ("electronics", "skincare", "other"):
            result = build_dimensions_v2(
                [mouse_product, skincare_product], _scoring_result_two_products(), cat
            )
            keys = {d["key"] for d in result}
            assert keys == {"price", "reviews", "value"}, (
                f"category={cat}: cross-category emitted non-universal "
                f"dim. keys={keys}"
            )

    def test_same_category_can_still_emit_contextual(self):
        """Sanity: this isn't a regression of the contextual path —
        same-category WITH shared per-dim scores still gets the
        contextual dim. Lane 1 L1.3 (2026-06-08) — contextual dims now
        come from `scoring_result.scores.product_i.breakdown[dim_key]`
        rather than spec presence (DPI/popularity were the legacy
        electronics extras)."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        sr = _scoring_result_two_products()
        sr["scores"]["product_0"]["breakdown"] = {
            "performance_score": 88,
            "build_quality_score": 80,
            "feature_score": 75,
        }
        sr["scores"]["product_1"]["breakdown"] = {
            "performance_score": 70,
            "build_quality_score": 78,
            "feature_score": 72,
        }
        result = build_dimensions_v2(products, sr, "electronics")
        assert len(result) > 3, (
            "same-category with populated scoring breakdown should emit "
            f">3 dims; got: {[d['key'] for d in result]}"
        )


# ---------------------------------------------------------------------------
# Test 4 — delta_text is always factual (no banned words)
# ---------------------------------------------------------------------------

class TestDeltaTextIsFactual:

    def test_no_banned_words_in_any_delta_text(self):
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        for dim in result:
            match = BANNED_PATTERN.search(dim["delta_text"])
            assert match is None, (
                f"banned word '{match.group(0)}' in delta_text for "
                f"dim '{dim['key']}': {dim['delta_text']!r}"
            )

    def test_no_banned_words_under_close_call_scoring(self):
        """Tight margins must not goad the builder into evaluative
        language to break a tie."""
        tight = _scoring_result_two_products()
        tight["scores"]["product_0"]["overall"] = 82
        tight["scores"]["product_1"]["overall"] = 81
        tight["win_margin"] = 1
        products = [
            _mouse("Glorious Model O", 22.0, 4.5, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 24.0, 4.4, 1100, dpi=12000),
        ]
        result = build_dimensions_v2(products, tight, "electronics")
        for dim in result:
            assert BANNED_PATTERN.search(dim["delta_text"]) is None, (
                f"banned word in close-call delta_text for {dim['key']}: "
                f"{dim['delta_text']!r}"
            )

    def test_delta_text_non_empty_string(self):
        """Each dim's delta_text must be a non-empty string. Empty
        strings in copy ship literally as a blank row — visual bug."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        for dim in result:
            assert isinstance(dim["delta_text"], str) and dim["delta_text"].strip(), (
                f"empty/invalid delta_text on dim {dim['key']}: {dim['delta_text']!r}"
            )


# ---------------------------------------------------------------------------
# Test 5 — Ordering: core dimensions first
# ---------------------------------------------------------------------------

class TestOrdering:

    def test_core_dims_appear_before_contextual(self):
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        # Find the index of the first contextual dim; assert no core
        # dim appears after it.
        first_contextual = next((i for i, d in enumerate(result) if not d["is_core"]), len(result))
        for i in range(first_contextual, len(result)):
            assert not result[i]["is_core"], (
                f"core dim '{result[i]['key']}' at index {i} appears AFTER "
                f"contextual dim at index {first_contextual}"
            )

    def test_total_dimensions_capped_at_6(self):
        """ScoringV2 enforces ≤6 dims at the model layer; the builder
        must produce output that satisfies the consumer."""
        products = [
            _mouse("Glorious Model O", 22.0, 4.6, 1200, dpi=12000, rgb=True, switches="Kailh"),
            _mouse("Ducky One 2 Mini", 52.0, 4.4, 800, dpi=8000, rgb=True, switches="Cherry"),
        ]
        result = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
        assert len(result) <= 6, (
            f"builder emitted {len(result)} dims > 6 — exceeds ScoringV2 cap. "
            f"keys: {[d['key'] for d in result]}"
        )


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-1.3 run:
#     python -m pytest tests/test_dimensions_builder.py -v
#     → ImportError on `build_dimensions_v2` → 1 collection error → RED
#
# Post-Task-1.3: ~16 assertions across 5 test classes. Coverage target
# ≥80% on `build_dimensions_v2`.
