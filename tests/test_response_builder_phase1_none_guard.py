"""Regression — PYTHON-FASTAPI-J (Sentry event ecaa64acab224c599c9aba3bb92dfc89).

Sprint A merge `ec2751b` crashed prod on every `/text/compare` because L2's
per-race timeout contract sets `product_data[i][<key>]=None` on TimeoutError,
and 2 downstream call sites used the unsafe `.get("reviews", {}).get(...)`
pattern. `.get(key, {})` returns the SECOND argument only when the key is
absent — when the key is PRESENT with value None it returns None, which
then `.get(...)`s into AttributeError.

The L2 timeout contract applies to all 4 Phase 1 races: specs, price,
reviews, image_url. This test pins None-safe rendering for each.

Reverted at `9ff81f5`. Fix:
- response_builder.py:963: `(pd.get("reviews") or {}).get("review_summary", ...)`
- structured_comparison_service.py:1609: same pattern (streaming path mirror)
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.response_builder import build_comparison_response


def _minimal_product_data(reviews=None, specs=None, price=None, image_url=None):
    """Return product_data shaped to surface each None case independently."""
    return [
        {
            "brand": "B0", "name": "P0", "full_name": "B0 P0",
            "category": "electronics",
            "price": price,
            "best_price": (price or {}).get("amount") if isinstance(price, dict) else None,
            "specs": specs,
            "reviews": reviews,
            "image_url": image_url,
            "rating": None,
            "rating_source": None,
            "review_count": 0,
            "fact_check": {},
        },
        {
            "brand": "B1", "name": "P1", "full_name": "B1 P1",
            "category": "electronics",
            "price": price,
            "best_price": (price or {}).get("amount") if isinstance(price, dict) else None,
            "specs": specs,
            "reviews": reviews,
            "image_url": image_url,
            "rating": None,
            "rating_source": None,
            "review_count": 0,
            "fact_check": {},
        },
    ]


def _minimal_scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 60.0}, "product_1": {"overall": 50.0}},
        "tradeoff_pairs": [],
        "value_badges": [],
        "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {},
        "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.",
        "key_differences": [],
    }


# ---------- core regression: reviews=None must not crash ----------

def test_build_comparison_response_handles_reviews_none():
    """L2 per-race timeout sets product_data[i]['reviews'] = None — response
    builder MUST NOT AttributeError on `.get('reviews', {}).get(...)`.
    Regression for PYTHON-FASTAPI-J."""
    product_data = _minimal_product_data(reviews=None)
    response = build_comparison_response(
        query="A vs B",
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None,
        region="bahrain",
        api_calls=4,
        elapsed_seconds=1.5,
        total_cost=0.01,
        gpt_calls=2,
        serper_calls=1,
        from_cache=False,
        verdict_validation={},
    )
    assert response["success"] is True or "reviews" in response
    review_products = response["reviews"]["products"]
    assert len(review_products) == 2
    for rp in review_products:
        assert rp["review_summary"]["overall_sentiment"] == "mixed"
        assert rp["review_summary"]["review_volume"] == "minimal"


def test_reviews_present_but_review_summary_missing_uses_fallback():
    """`reviews` dict exists but lacks `review_summary` — empty-dict fallback."""
    product_data = _minimal_product_data(
        reviews={"common_praises": ["good"], "common_complaints": []},
    )
    response = build_comparison_response(
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={}, query="q",
    )
    for rp in response["reviews"]["products"]:
        assert rp["review_summary"]["overall_sentiment"] == "mixed"


def test_reviews_with_review_summary_renders_actual_data():
    """Happy path — `reviews.review_summary` populated; fallback NOT used."""
    rs = {
        "overall_sentiment": "positive",
        "consensus": "great battery",
        "highlights": [],
        "review_volume": "high",
        "agreement_level": "strong",
    }
    product_data = _minimal_product_data(reviews={"review_summary": rs})
    response = build_comparison_response(
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={}, query="q",
    )
    for rp in response["reviews"]["products"]:
        assert rp["review_summary"]["overall_sentiment"] == "positive"
        assert rp["review_summary"]["consensus"] == "great battery"


# ---------- companion regressions for the other 3 Phase 1 keys ----------

def test_build_comparison_response_handles_specs_none():
    """L2 timeout can also set pd['specs']=None. Surface MUST NOT crash."""
    product_data = _minimal_product_data(specs=None)
    response = build_comparison_response(
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={}, query="q",
    )
    # specs.products carries the (possibly None) specs through, doesn't crash
    assert "specs" in response
    assert len(response["specs"]["products"]) == 2


def test_build_comparison_response_handles_price_none():
    """pd['price']=None timeout case must produce a non-crashing response."""
    product_data = _minimal_product_data(price=None)
    response = build_comparison_response(
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={}, query="q",
    )
    assert "overview" in response


def test_build_comparison_response_handles_image_url_none():
    """pd['image_url']=None timeout case must produce a non-crashing response."""
    product_data = _minimal_product_data(image_url=None)
    response = build_comparison_response(
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={}, query="q",
    )
    overview_products = response["overview"]["products"]
    assert len(overview_products) == 2
    for op in overview_products:
        # image_url passes through as None — not a crash
        assert op.get("image_url") is None


# ---------- all 4 None simultaneously ----------

def test_build_comparison_response_handles_all_phase1_keys_none():
    """Worst-case: every Phase 1 race timed out. Must still produce a
    structurally-valid response (success can be true OR false — what we
    forbid is the AttributeError crash)."""
    product_data = _minimal_product_data(
        reviews=None, specs=None, price=None, image_url=None,
    )
    response = build_comparison_response(
        product_data=product_data,
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={}, query="q",
    )
    assert "metadata" in response
    assert response["reviews"]["products"][0]["review_summary"]["overall_sentiment"] == "mixed"


# ---------- timeout floor pin ----------

def test_phase1_timeouts_reviews_at_least_10s():
    """Documentation invariant — reviews timeout floor lifted to 10s per
    measured post-D2 reviews_ms = 4-5s + headroom (Session 51 evidence in
    memory/feedback_measure_before_optimize.md). Lower floor trips on cold
    cache and re-exposes PYTHON-FASTAPI-J."""
    import inspect

    from app.services.structured_comparison_service import StructuredComparisonService

    source = inspect.getsource(StructuredComparisonService._fetch_product_data)
    assert "_PHASE1_TIMEOUTS" in source
    # Reviews must be >= 10s
    assert '"reviews": 10.0' in source or "'reviews': 10.0" in source, (
        "reviews timeout floor below 10s — risks re-tripping PYTHON-FASTAPI-J"
    )
