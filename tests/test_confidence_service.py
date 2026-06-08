"""L2.1 — Tests for `confidence_service.py` (pure-function signal computation, no I/O).

Asserts behavior under the confidence-driven escalation matrix:
- price: multi-source agreement / training-estimate deviation / retailer score
- specs: ratio of populated schema fields
- reviews: combined review-count + source-count signal
- should_escalate: True when level=="low"
"""

import pytest

from app.services.confidence_service import (
    compute_price_confidence,
    compute_reviews_confidence,
    compute_specs_confidence,
    should_escalate,
)


# ---------- price confidence ----------

def test_price_confidence_high_when_two_retailers_within_20pct():
    sources = [
        {"src": "serper_shopping", "amount": 142.12, "retailer_score": 0.9},
        {"src": "curl:carrefour.com.bh", "amount": 145.00, "retailer_score": 0.8},
    ]
    result = compute_price_confidence(sources, training_estimate=140.0)
    assert result["level"] == "high"


def test_price_confidence_low_when_single_source_deviates_40pct():
    sources = [{"src": "serper_shopping", "amount": 20.0, "retailer_score": 0.5}]
    result = compute_price_confidence(sources, training_estimate=120.0)
    assert result["level"] == "low"
    # spec L2.1 step1 expected substring is "deviation"
    assert any("deviation" in r for r in result["reasons"])


def test_price_confidence_no_sources_returns_low():
    result = compute_price_confidence([], training_estimate=100.0)
    assert result["level"] == "low"
    assert "no_sources" in result["reasons"]
    assert result["median"] is None


def test_price_confidence_only_amounts_missing_returns_low():
    sources = [{"src": "serper_shopping", "amount": None, "retailer_score": 0.9}]
    result = compute_price_confidence(sources, training_estimate=100.0)
    assert result["level"] == "low"
    assert "no_amounts" in result["reasons"]


def test_price_confidence_single_source_low_retailer_score_is_low():
    """Single source with weak retailer score should flag low (two reasons triggered)."""
    sources = [{"src": "serper_shopping", "amount": 120.0, "retailer_score": 0.4}]
    result = compute_price_confidence(sources, training_estimate=120.0)
    # only_one_source + low_retailer_score → 2 reasons → low
    assert result["level"] == "low"
    assert "only_one_source" in result["reasons"]
    assert "low_retailer_score" in result["reasons"]


def test_price_confidence_single_source_high_retailer_score_is_medium():
    """Official-domain single source within training estimate → medium (not low)."""
    sources = [{"src": "page_scrape:apple.com", "amount": 329.0, "retailer_score": 1.0}]
    result = compute_price_confidence(sources, training_estimate=320.0)
    assert result["level"] == "medium"


def test_price_confidence_median_is_sorted_middle():
    sources = [
        {"src": "a", "amount": 100.0, "retailer_score": 0.9},
        {"src": "b", "amount": 200.0, "retailer_score": 0.9},
        {"src": "c", "amount": 150.0, "retailer_score": 0.9},
    ]
    result = compute_price_confidence(sources, training_estimate=150.0)
    assert result["median"] == 150.0


def test_price_confidence_disagreement_flagged():
    """Two sources too far apart (>20% from median) flagged as disagreement."""
    sources = [
        {"src": "a", "amount": 100.0, "retailer_score": 0.9},
        {"src": "b", "amount": 200.0, "retailer_score": 0.9},
    ]
    result = compute_price_confidence(sources, training_estimate=150.0)
    # median is one of the values (one will be exactly within 20%, the other won't)
    # both will be outside 0.8*median..1.2*median if the spread is too wide
    assert "sources_disagree" in result["reasons"]


# ---------- specs confidence ----------

def test_specs_confidence_high_when_80pct_fields_populated():
    schema_fields = [
        "display", "processor", "ram", "storage", "battery", "rear_camera",
        "front_camera", "os", "weight", "water_resistance",
    ]
    populated = {f: "value" for f in schema_fields[:9]}  # 9/10 = 90%
    result = compute_specs_confidence(populated, schema_fields)
    assert result["level"] == "high"
    assert result["populated_count"] == 9
    assert result["schema_size"] == 10
    assert result["ratio"] == 0.9


def test_specs_confidence_medium_at_50pct():
    schema_fields = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    populated = {f: "v" for f in schema_fields[:5]}
    result = compute_specs_confidence(populated, schema_fields)
    assert result["level"] == "medium"
    assert result["ratio"] == 0.5


def test_specs_confidence_low_at_30pct():
    schema_fields = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    populated = {f: "v" for f in schema_fields[:3]}
    result = compute_specs_confidence(populated, schema_fields)
    assert result["level"] == "low"


def test_specs_confidence_empty_schema():
    result = compute_specs_confidence({}, [])
    assert result["level"] == "low"
    assert "no_schema" in result["reasons"]


def test_specs_confidence_empty_value_treated_as_missing():
    """Empty string / None should not count as populated."""
    schema_fields = ["a", "b", "c", "d"]
    populated = {"a": "val", "b": "", "c": None, "d": "val"}
    result = compute_specs_confidence(populated, schema_fields)
    assert result["populated_count"] == 2
    assert result["ratio"] == 0.5


# ---------- reviews confidence ----------

def test_reviews_confidence_high_when_both_products_have_many_reviews():
    result = compute_reviews_confidence(review_count_p0=500, review_count_p1=200, sources_count=2)
    assert result["level"] == "high"


def test_reviews_confidence_medium_at_30_reviews():
    result = compute_reviews_confidence(review_count_p0=30, review_count_p1=50, sources_count=1)
    assert result["level"] == "medium"


def test_reviews_confidence_low_when_under_20():
    result = compute_reviews_confidence(review_count_p0=5, review_count_p1=100, sources_count=1)
    # min(5, 100)=5 → low
    assert result["level"] == "low"


def test_reviews_confidence_high_requires_multi_source():
    """500+ reviews but only 1 source returns medium, not high (per spec)."""
    result = compute_reviews_confidence(review_count_p0=500, review_count_p1=400, sources_count=1)
    # min=400 but sources_count<2 → not high → medium (since min>20)
    assert result["level"] == "medium"


# ---------- escalation gate ----------

def test_should_escalate_true_for_low_level():
    assert should_escalate({"level": "low", "reasons": ["only_one_source"]}) is True


def test_should_escalate_false_for_medium():
    assert should_escalate({"level": "medium"}) is False


def test_should_escalate_false_for_high():
    assert should_escalate({"level": "high"}) is False


def test_should_escalate_handles_missing_key():
    """If a confidence_obj has no 'level', do NOT escalate (conservative)."""
    assert should_escalate({}) is False
