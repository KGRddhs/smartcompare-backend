"""Bundle C § 2e A.4.5 — comparison_quality detector + verdict-prompt instruction.

Per design § 2e + plan A.4.5: emit `comparison_quality: 'normal'|'weak'|'weird'`
based on three rules:
  - 'weird' when products span unrelated categories (category_used mismatch).
  - 'weird' when >50% of one product's specs are missing AFTER 3-tier fallback.
  - 'weird' when prices differ by 10×+ order of magnitude.
  - otherwise 'weak' (softer thresholds for missing specs) or 'normal'.

When 'weird', the verdict prompt is instructed to REWRITE winner_declaration
into a non-forced framing ("These products serve different purposes — ..."),
NEVER trigger a UI banner per critical rule #1.

Companion to test-bundle-c's C.2.2 tests in tests/test_extraction_prompt_bundle_c.py
(test_weird_flag_forwarded_to_verdict_prompt + test_normal_flag_keeps_winner_framing).
"""
import pytest

from app.services import structured_comparison_service as scs
from app.services import extraction_service


# ---------------------------------------------------------------------------
# detect_comparison_quality — 3-state classifier
# ---------------------------------------------------------------------------


def test_normal_when_same_category_similar_prices_and_specs():
    products = [
        {"name": "iPhone 16", "category_used": "electronics",
         "specs": {"battery": "3274", "processor": "A17", "ram": "8", "rear_camera": "48", "front_camera": "12", "weight": "171"},
         "price": {"amount": 350.0}},
        {"name": "Galaxy S25", "category_used": "electronics",
         "specs": {"battery": "4000", "processor": "Snap8", "ram": "12", "rear_camera": "50", "front_camera": "12", "weight": "168"},
         "price": {"amount": 280.0}},
    ]
    assert scs.detect_comparison_quality(products) == "normal"


def test_weird_when_categories_mismatch():
    products = [
        {"name": "iPhone 16", "category_used": "electronics",
         "specs": {"battery": "3274"}, "price": {"amount": 350.0}},
        {"name": "CeraVe cream", "category_used": "skincare",
         "specs": {"volume": "100"}, "price": {"amount": 8.0}},
    ]
    assert scs.detect_comparison_quality(products) == "weird"


def test_weird_when_10x_price_spread():
    """Per spec § 2e: prices differ by 10× order of magnitude → weird."""
    products = [
        {"name": "A", "category_used": "electronics",
         "specs": {"battery": "3274", "processor": "A17", "ram": "8", "rear_camera": "48"},
         "price": {"amount": 5.0}},
        {"name": "B", "category_used": "electronics",
         "specs": {"battery": "4000", "processor": "S25", "ram": "12", "rear_camera": "50"},
         "price": {"amount": 500.0}},
    ]
    assert scs.detect_comparison_quality(products) == "weird"


def test_weird_when_50pct_specs_missing_post_fallback():
    """Per spec § 2e: >50% of one product's specs missing AFTER 3-tier
    fallback → weird (only fires when post_fallback=True)."""
    products = [
        {"name": "X", "category_used": "electronics",
         "specs": {"battery": "3274"},  # 1 of 6 → 83% missing
         "price": {"amount": 350.0}},
        {"name": "Y", "category_used": "electronics",
         "specs": {"battery": "4000", "processor": "S25", "ram": "12", "rear_camera": "50", "front_camera": "12", "weight": "168"},
         "price": {"amount": 280.0}},
    ]
    assert scs.detect_comparison_quality(products, post_fallback=True) == "weird"


def test_weak_pre_fallback_lets_tier2_try_first():
    """Same sparse specs BEFORE 3-tier fallback ran — classifier shouldn't
    jump to 'weird' yet; Tier 2/3 might still fill the gaps."""
    products = [
        {"name": "X", "category_used": "electronics",
         "specs": {"battery": "3274"},
         "price": {"amount": 350.0}},
        {"name": "Y", "category_used": "electronics",
         "specs": {"battery": "4000", "processor": "S25", "ram": "12", "rear_camera": "50"},
         "price": {"amount": 280.0}},
    ]
    out = scs.detect_comparison_quality(products, post_fallback=False)
    # Not 'weird' yet — could be 'normal' or 'weak' depending on threshold
    assert out in {"normal", "weak"}


def test_normal_when_under_2x_price_spread():
    """2x price spread is NOT 10x — should not trigger weird."""
    products = [
        {"name": "A", "category_used": "electronics",
         "specs": {"battery": "3274", "processor": "A17", "ram": "8", "rear_camera": "48"},
         "price": {"amount": 250.0}},
        {"name": "B", "category_used": "electronics",
         "specs": {"battery": "4000", "processor": "S25", "ram": "12", "rear_camera": "50"},
         "price": {"amount": 450.0}},
    ]
    assert scs.detect_comparison_quality(products) == "normal"


def test_detector_handles_missing_price_data_gracefully():
    """Missing prices shouldn't crash — fall back to category check only."""
    products = [
        {"name": "A", "category_used": "electronics", "specs": {"battery": "3274"}},
        {"name": "B", "category_used": "electronics", "specs": {"battery": "4000"}},
    ]
    out = scs.detect_comparison_quality(products)
    assert out in {"normal", "weak", "weird"}


def test_detector_returns_normal_for_fewer_than_2_products():
    """Single-product edge case must not crash."""
    assert scs.detect_comparison_quality([{"name": "lonely"}]) == "normal"


# ---------------------------------------------------------------------------
# build_verdict_prompt — surfaces weird flag to GPT
# ---------------------------------------------------------------------------


def test_build_verdict_prompt_weird_includes_non_forced_framing():
    """Spec § 2e: when comparison_quality='weird', verdict prompt rewrites
    winner_declaration into a non-forced 'different purposes' framing."""
    prompt = extraction_service.build_verdict_prompt(
        products=[
            {"name": "iPhone", "category_used": "electronics"},
            {"name": "CeraVe", "category_used": "skincare"},
        ],
        comparison_quality="weird",
    )
    lowered = prompt.lower()
    assert any(kw in lowered for kw in [
        "different purposes",
        "no forced winner",
        "weird",
        "cross-category",
    ]), f"weird framing not in prompt: {prompt[:400]!r}"


def test_build_verdict_prompt_normal_keeps_standard_framing():
    """Spec § 2e: comparison_quality='normal' → no special weird-context block."""
    prompt = extraction_service.build_verdict_prompt(
        products=[
            {"name": "A", "category_used": "electronics"},
            {"name": "B", "category_used": "electronics"},
        ],
        comparison_quality="normal",
    )
    assert "different purposes" not in prompt.lower()
    assert "cross-category" not in prompt.lower()


def test_build_verdict_prompt_default_is_normal():
    """Backwards-compat: calling build_verdict_prompt without
    comparison_quality kwarg behaves identically to the 'normal' case."""
    p_default = extraction_service.build_verdict_prompt(products=[])
    p_normal = extraction_service.build_verdict_prompt(
        products=[], comparison_quality="normal"
    )
    assert p_default == p_normal


def test_build_verdict_prompt_no_ui_banner_directive():
    """Critical rule #1: NEVER instruct the model to surface a banner.
    The weird-flag rewrites text, not UI structure."""
    prompt = extraction_service.build_verdict_prompt(
        products=[], comparison_quality="weird",
    )
    lowered = prompt.lower()
    assert "show banner" not in lowered
    assert "info banner" not in lowered
    assert "display warning" not in lowered


def test_build_verdict_prompt_no_forbidden_words():
    """FIVE rules: no 'estimated' / 'reference price' / scary copy in prompt text."""
    prompt = extraction_service.build_verdict_prompt(
        products=[], comparison_quality="weird",
    )
    lowered = prompt.lower()
    for forbidden in ["reference price", "couldn't", "try again", "failed to"]:
        assert forbidden not in lowered, f"forbidden phrase {forbidden!r} in verdict prompt"
