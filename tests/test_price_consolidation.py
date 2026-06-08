"""L2.8 — Tests for cross-validation price consolidation.

`consolidate_price_sources()` merges multiple candidate prices (Tier 1
Serper, Tier 1.5 page scrapes, Tier 2 GPT) into a single best-estimate
amount. Outliers >2 sigma from the median are dropped before re-computing
the median of the remaining sources.
"""

import math

import pytest

from app.services.price_service import consolidate_price_sources


def test_price_consolidation_drops_outlier():
    sources = [
        {"src": "lulu.com.bh", "amount": 145.00, "retailer_score": 3.0},
        {"src": "carrefour.com.bh", "amount": 142.00, "retailer_score": 3.0},
        {"src": "amazon.ae", "amount": 20.00, "retailer_score": 1.5},  # bad
    ]
    result = consolidate_price_sources(sources)
    assert result is not None
    # Median of remaining {142, 145} = 143.5
    assert result["amount"] == pytest.approx(143.5)
    assert "outlier_dropped" in result["flags"]
    assert result["cross_validation"] == "passed"


def test_price_consolidation_no_outliers_returns_clean():
    sources = [
        {"src": "a", "amount": 100.0},
        {"src": "b", "amount": 105.0},
        {"src": "c", "amount": 95.0},
    ]
    result = consolidate_price_sources(sources)
    assert result["amount"] == pytest.approx(100.0)
    assert "outlier_dropped" not in result["flags"]
    assert result["cross_validation"] == "passed"


def test_price_consolidation_empty_returns_none():
    assert consolidate_price_sources([]) is None


def test_price_consolidation_single_source_returns_it():
    """One source: no median calc needed, return as-is."""
    sources = [{"src": "lulu.com.bh", "amount": 145.0, "retailer_score": 3.0}]
    result = consolidate_price_sources(sources)
    assert result["amount"] == pytest.approx(145.0)
    assert result["cross_validation"] == "single_source"


def test_price_consolidation_two_sources_within_band_passes():
    """Two sources within 20% of each other: median, no outlier flag."""
    sources = [
        {"src": "a", "amount": 100.0},
        {"src": "b", "amount": 108.0},
    ]
    result = consolidate_price_sources(sources)
    assert result["amount"] == pytest.approx(104.0)
    assert "outlier_dropped" not in result["flags"]


def test_price_consolidation_two_sources_disagree_flagged():
    """Two sources >20% apart: returned but flagged as disagreement."""
    sources = [
        {"src": "a", "amount": 100.0},
        {"src": "b", "amount": 200.0},
    ]
    result = consolidate_price_sources(sources)
    assert result is not None
    assert "sources_disagree" in result["flags"]
    # Median (statistical, mean of middle two for n=2) = 150.0
    assert result["amount"] == pytest.approx(150.0)


def test_price_consolidation_ignores_missing_amounts():
    sources = [
        {"src": "a", "amount": 100.0},
        {"src": "b", "amount": None},
        {"src": "c", "amount": 105.0},
        {"src": "d"},  # no amount key
    ]
    result = consolidate_price_sources(sources)
    assert result["amount"] == pytest.approx(102.5)
    assert result["cross_validation"] == "passed"


def test_price_consolidation_returns_source_count():
    sources = [
        {"src": "a", "amount": 100.0},
        {"src": "b", "amount": 105.0},
    ]
    result = consolidate_price_sources(sources)
    assert result["sources_count"] == 2


def test_price_consolidation_all_outliers_drops_to_single_or_pair():
    """Wide spread but odd-length list — even after >2σ drop, at least one
    source remains so the function returns a number (not None)."""
    sources = [
        {"src": "a", "amount": 50.0},
        {"src": "b", "amount": 100.0},
        {"src": "c", "amount": 150.0},
    ]
    result = consolidate_price_sources(sources)
    assert result is not None
    assert result["amount"] > 0
