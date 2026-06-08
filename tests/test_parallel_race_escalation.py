"""L2.5 — Tests for confidence-driven escalation predicate.

Asserts the legacy `is_luxury_brand()` gate is replaced by
`_should_escalate_price_scrape(...)`, which uses `confidence_service` to
decide whether to enter the Tier 1.5 page-scrape cascade for ANY category.

Net effect: Xiaomi 14 / iPhone (mainstream electronics) with a 20-BHD bogus
Tier-1 result now escalates to Tier 1.5 just like Tom Ford used to. The
luxury-only gate becomes a confidence-only gate.
"""

import os

# Provide a dummy key so openai_service import doesn't blow up on the
# module-level singleton client init (same pattern as L2.4 tests).
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.structured_comparison_service import _should_escalate_price_scrape


def test_escalates_when_single_source_deviates_40pct():
    """Tom Ford 20 BHD vs 120 training estimate -> must escalate."""
    sources = [{"src": "serper_shopping", "amount": 20.0, "retailer_score": 0.4}]
    assert _should_escalate_price_scrape(sources, training_estimate=120.0) is True


def test_no_escalation_when_two_sources_agree_within_20pct():
    """Carrefour BH 145 + Lulu BH 142 -> no escalation needed."""
    sources = [
        {"src": "serper_shopping", "amount": 142.12, "retailer_score": 0.9},
        {"src": "curl:lulu.com.bh", "amount": 145.00, "retailer_score": 1.0},
    ]
    assert _should_escalate_price_scrape(sources, training_estimate=140.0) is False


def test_escalates_for_any_category_not_just_luxury():
    """Non-luxury electronics (Xiaomi 14 at 50 BHD vs 700-ish training)
    used to be blocked by the is_luxury_brand() gate. Now confidence-driven
    escalation fires for it too.
    """
    sources = [{"src": "serper_shopping", "amount": 50.0, "retailer_score": 0.5}]
    assert (
        _should_escalate_price_scrape(sources, training_estimate=700.0, brand="Xiaomi")
        is True
    )


def test_escalates_when_no_sources():
    """Zero Serper hits -> escalate (this was previously the only
    non-luxury escalation path)."""
    assert _should_escalate_price_scrape([], training_estimate=100.0) is True


def test_no_escalation_when_official_domain_single_source_matches_training():
    """page_scrape:apple.com at 329 BHD vs 320 training -> medium confidence,
    no escalation."""
    sources = [{"src": "page_scrape:apple.com", "amount": 329.0, "retailer_score": 1.0}]
    assert _should_escalate_price_scrape(sources, training_estimate=320.0) is False


def test_no_escalation_without_training_estimate_when_two_sources_agree():
    """If no training estimate is available, two-source agreement alone
    is enough to skip escalation (high confidence)."""
    sources = [
        {"src": "a", "amount": 100.0, "retailer_score": 0.9},
        {"src": "b", "amount": 102.0, "retailer_score": 0.9},
    ]
    assert _should_escalate_price_scrape(sources, training_estimate=None) is False


def test_escalates_when_single_source_low_retailer_score_no_training_est():
    """Single source from a weak retailer with no training data -> low
    confidence (two reasons) -> escalate."""
    sources = [{"src": "serper_shopping", "amount": 50.0, "retailer_score": 0.3}]
    assert _should_escalate_price_scrape(sources, training_estimate=None) is True


def test_does_not_raise_on_brand_arg():
    """`brand` is accepted (legacy compat with the luxury gate signature)
    but is purely a hint — escalation decisions are driven by confidence
    metrics, not brand recognition."""
    sources = [
        {"src": "a", "amount": 145.0, "retailer_score": 0.9},
        {"src": "b", "amount": 142.0, "retailer_score": 0.9},
    ]
    # Should not crash; should not change decision based on brand
    decision_without = _should_escalate_price_scrape(sources, training_estimate=140.0)
    decision_with = _should_escalate_price_scrape(
        sources, training_estimate=140.0, brand="Apple"
    )
    assert decision_without == decision_with is False
