"""Bundle C § 1b A.3.2 — _build_factual_verdict pure-template builder.

Per design § 1b + plan A.3.2 + qa-bundle-c D.1.3 evidence
(`docs/investigations/2026-05-17-bundle-c-cold-cache-evidence.md`):
the missing `factual_verdict` on every comparison is caused by
`_build_scoring_v2` simply not emitting the key. Pure-template fix —
zero GPT cost — composes line1 + line2 from existing fields:
  line1 = winner declaration with strongest factual delta
          (price gap / rating gap / top dim margin)
  line2 = runner-up's strongest counter-fact (best dim runner-up wins)

Must respect the FIVE critical rules — no scary copy, no backend
internals, no "estimated" / "reference price" leaking into the strings.
"""
import pytest

from app.services import response_builder


def _scoring(overall_a: int = 75, overall_b: int = 80) -> dict:
    return {
        "scores": {
            "product_0": {"overall": overall_a, "breakdown": {}, "tier": "mid"},
            "product_1": {"overall": overall_b, "breakdown": {}, "tier": "mid"},
        },
    }


# ---------------------------------------------------------------------------
# _build_factual_verdict — basic shape
# ---------------------------------------------------------------------------


def test_builder_returns_dict_with_line1_and_line2():
    products = [
        {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": 4.5},
        {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": 4.4},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(75, 82), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 70, "score_b": 88,
             "delta_text": "20% cheaper", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews", "score_a": 85, "score_b": 84,
             "delta_text": "0.1 stars higher", "confidence": "high", "is_core": True},
        ],
    )
    assert isinstance(fv, dict)
    assert isinstance(fv.get("line1"), str) and len(fv["line1"]) > 0
    assert isinstance(fv.get("line2"), str) and len(fv["line2"]) > 0


def test_builder_returns_none_when_fewer_than_2_products():
    fv = response_builder._build_factual_verdict(
        [{"name": "alone"}], scoring_result=_scoring(), winner_index=0, dimensions=[],
    )
    assert fv is None


# ---------------------------------------------------------------------------
# line1 — strongest factual delta drives the winner declaration
# ---------------------------------------------------------------------------


def test_line1_uses_price_gap_when_price_is_largest_delta():
    """When the price gap dominates (e.g. winner is 40% cheaper),
    line1 should anchor on price."""
    products = [
        {"name": "iPhone 16", "price": {"amount": 500.0}, "rating": 4.5},
        {"name": "Galaxy S25", "price": {"amount": 300.0}, "rating": 4.4},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(75, 82), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 65, "score_b": 90,
             "delta_text": "40% cheaper", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews", "score_a": 85, "score_b": 84,
             "delta_text": "0.1 stars higher", "confidence": "high", "is_core": True},
        ],
    )
    # Winner name should appear, and the price gap fact should anchor line1
    assert "Galaxy S25" in fv["line1"]
    line1 = fv["line1"].lower()
    assert any(kw in line1 for kw in ["cheaper", "less", "%"])


def test_line1_uses_rating_gap_when_rating_is_largest_delta():
    """When prices are similar but rating gap is large, line1 anchors on rating."""
    products = [
        {"name": "Product A", "price": {"amount": 100.0}, "rating": 3.5},
        {"name": "Product B", "price": {"amount": 102.0}, "rating": 4.8},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(70, 88), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 80, "score_b": 79,
             "delta_text": "2% more", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews", "score_a": 60, "score_b": 88,
             "delta_text": "1.3 stars higher", "confidence": "high", "is_core": True},
        ],
    )
    assert "Product B" in fv["line1"]
    line1 = fv["line1"].lower()
    assert any(kw in line1 for kw in ["star", "rating", "review"])


def test_line1_uses_top_dim_margin_when_dim_dominates():
    """When dim margins exceed price/rating signal, line1 anchors on the dim."""
    products = [
        {"name": "Product A", "price": {"amount": 100.0}, "rating": 4.5},
        {"name": "Product B", "price": {"amount": 100.0}, "rating": 4.5},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(60, 88), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 85, "score_b": 85,
             "delta_text": "Same price", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews", "score_a": 85, "score_b": 85,
             "delta_text": "Same rating", "confidence": "high", "is_core": True},
            {"key": "build_quality", "label": "Build", "score_a": 50, "score_b": 95,
             "delta_text": "Sturdier construction", "confidence": "high"},
        ],
    )
    assert "Product B" in fv["line1"]


# ---------------------------------------------------------------------------
# line2 — runner-up's strongest counter-fact
# ---------------------------------------------------------------------------


def test_line2_anchors_on_runner_up_strength():
    """line2 should reference the runner-up's strongest winning dim
    (a place where the loser actually beats the winner)."""
    products = [
        {"name": "Product A", "price": {"amount": 500.0}, "rating": 4.8},
        {"name": "Product B", "price": {"amount": 200.0}, "rating": 4.2},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(82, 78), winner_index=0,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 60, "score_b": 95,
             "delta_text": "60% cheaper", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews", "score_a": 90, "score_b": 80,
             "delta_text": "0.6 stars higher", "confidence": "high", "is_core": True},
        ],
    )
    # Winner is Product A (rating); line2 should mention runner-up B's
    # strength (price — B is cheaper).
    assert "Product B" in fv["line2"]


def test_line2_differs_from_line1():
    products = [
        {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": 4.5},
        {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": 4.4},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(75, 82), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 70, "score_b": 88,
             "delta_text": "20% cheaper", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews", "score_a": 88, "score_b": 80,
             "delta_text": "0.1 stars higher", "confidence": "high", "is_core": True},
        ],
    )
    assert fv["line1"] != fv["line2"]


# ---------------------------------------------------------------------------
# FIVE critical rules — forbidden user-facing strings
# ---------------------------------------------------------------------------


def test_line1_line2_never_contain_estimated_word():
    """Critical rule #3: no 'estimated' / 'reference price' / 'approximate'
    in user-facing strings even when one product's source_method='estimated'."""
    products = [
        {"name": "Product A", "price": {"amount": 100.0, "source_method": "estimated"},
         "rating": 4.5},
        {"name": "Product B", "price": {"amount": 60.0, "source_method": "firecrawl"},
         "rating": 4.4},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(75, 82), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 65, "score_b": 90,
             "delta_text": "40% cheaper", "confidence": "high", "is_core": True},
        ],
    )
    for line in (fv["line1"], fv["line2"]):
        low = line.lower()
        assert "estimated" not in low
        assert "reference price" not in low
        assert "approximate" not in low


def test_line1_line2_no_scary_copy():
    """Critical rule #5: forbidden EN vocabulary — couldn't / try again /
    Failed to. Mirror Arabic forbidden words skipped here (covered by
    i18n tests on frontend)."""
    products = [
        {"name": "Product A", "price": {"amount": 100.0}, "rating": 4.5},
        {"name": "Product B", "price": {"amount": 80.0}, "rating": 4.4},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(75, 82), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 70, "score_b": 88,
             "delta_text": "20% cheaper", "confidence": "high", "is_core": True},
        ],
    )
    for line in (fv["line1"], fv["line2"]):
        low = line.lower()
        assert "couldn't" not in low
        assert "try again" not in low
        assert "failed to" not in low


def test_line1_line2_no_backend_internals():
    """Critical rule #2: never expose coefficients, cap percentages, raw
    scores, or shift math in user-facing strings."""
    products = [
        {"name": "Product A", "price": {"amount": 100.0}, "rating": 4.5},
        {"name": "Product B", "price": {"amount": 80.0}, "rating": 4.4},
    ]
    fv = response_builder._build_factual_verdict(
        products, scoring_result=_scoring(75, 82), winner_index=1,
        dimensions=[
            {"key": "price", "label": "Price", "score_a": 70, "score_b": 88,
             "delta_text": "20% cheaper", "confidence": "high", "is_core": True},
        ],
    )
    forbidden = ["coefficient", "weight_score", "cap_percent", "shift_magnitude",
                 "calibrate", "raw_score"]
    for line in (fv["line1"], fv["line2"]):
        low = line.lower()
        for word in forbidden:
            assert word not in low, f"{word!r} leaked into user-facing line: {line!r}"


# ---------------------------------------------------------------------------
# Integration — _build_scoring_v2 must now emit factual_verdict
# ---------------------------------------------------------------------------


def test_scoring_v2_always_emits_factual_verdict_for_populated_comparisons():
    """qa-bundle-c D.1.3 confirmed: every probe returned scoring_v2 with
    NO factual_verdict key. Post-A.3.2, the key must always populate."""
    products = [
        {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": 4.5},
        {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": 4.4},
    ]
    scoring_v2 = response_builder._build_scoring_v2(
        product_data=products,
        scoring_result=_scoring(75, 82),
        category="electronics",
        winner_index=1,
    )
    assert "factual_verdict" in scoring_v2
    fv = scoring_v2["factual_verdict"]
    assert fv is not None
    assert fv.get("line1")
    assert fv.get("line2")


def test_scoring_v2_factual_verdict_under_sparse_data():
    """Edge case: when both prices and ratings are sparse, factual_verdict
    still emits a non-empty line1+line2 (falls back to dim margin or a
    neutral 'comparable' phrasing). MUST NOT crash."""
    products = [
        {"name": "Product A", "price": None, "rating": None},
        {"name": "Product B", "price": None, "rating": None},
    ]
    scoring_v2 = response_builder._build_scoring_v2(
        product_data=products,
        scoring_result=_scoring(75, 80),
        category="electronics",
        winner_index=1,
    )
    assert "factual_verdict" in scoring_v2
    fv = scoring_v2["factual_verdict"]
    # Both lines must be non-empty strings (template falls back to dim
    # margin or a neutral phrasing — NEVER crashes, never empty).
    assert isinstance(fv.get("line1"), str) and len(fv["line1"]) > 0
    assert isinstance(fv.get("line2"), str) and len(fv["line2"]) > 0


def test_legacy_diagnostic_silent_after_fix(caplog, monkeypatch):
    """The A.2.2 diagnostic (FACTUAL_VERDICT_DIAGNOSTIC) should stop firing
    once the builder populates factual_verdict — proves we resolved the
    root cause, not just masked it."""
    import logging
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(response_builder, "_FACTUAL_VERDICT_DIAG_FLAG", None, raising=False)
    products = [
        {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": 4.5},
        {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": 4.4},
    ]
    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        response_builder._build_scoring_v2(
            product_data=products,
            scoring_result=_scoring(75, 82),
            category="electronics",
            winner_index=1,
        )
    assert "FACTUAL_VERDICT_DIAGNOSTIC" not in caplog.text
