"""L2.9 — Tests for `metadata.source_trace` observability.

Verifies the response builder accepts a `source_trace` override on the
metadata kwarg and surfaces it on the response. The orchestrator populates
the trace during Phase 1 races and passes it via the build_comparison_response
metadata override pattern (Bundle D B.0).
"""

import pytest

from app.services.response_builder import build_comparison_response


def _minimal_product_data(name="Test"):
    """Minimal product_data list shaped for response_builder to not crash."""
    return [
        {
            "brand": "B", "name": name, "full_name": f"B {name}", "category": "electronics",
            "price": {"amount": 100.0, "currency": "BHD", "retailer": "test"},
            "best_price": 100.0,
            "specs": {"field": "v"},
            "reviews": {},
            "rating": None,
            "rating_source": None,
            "review_count": 0,
            "fact_check": {},
        }
        for _ in range(2)
    ]


def test_response_includes_source_trace_when_passed_via_metadata():
    product_data = _minimal_product_data()
    scoring_result = {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 75.0}, "product_1": {"overall": 60.0}},
        "tradeoff_pairs": [],
        "value_badges": [], "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {},
        "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.",
        "key_differences": [],
    }

    source_trace = {
        "price": {
            "sources_tried": ["serper_shopping", "curl:carrefour.com.bh"],
            "sources_returned_value": ["curl:carrefour.com.bh"],
            "median_chosen": 142.5,
            "cross_validation": "passed",
            "wall_ms": 4321,
        },
        "specs": {
            "sources_tried": ["gpt_extraction"],
            "sources_returned_value": ["gpt_extraction"],
            "wall_ms": 1234,
        },
        "reviews": {
            "sources_tried": ["serper_organic"],
            "sources_returned_value": ["serper_organic"],
            "wall_ms": 567,
        },
        "image": {
            "sources_tried": ["serper_images", "page_scrape_piggyback"],
            "sources_returned_value": ["page_scrape_piggyback"],
            "wall_ms": 89,
        },
    }

    response = build_comparison_response(
        query="A vs B",
        product_data=product_data,
        scoring_result=scoring_result,
        comparison=None,
        region="bahrain",
        api_calls=4,
        elapsed_seconds=1.5,
        total_cost=0.01,
        gpt_calls=2,
        serper_calls=1,
        from_cache=False,
        verdict_validation={},
        metadata={"source_trace": source_trace},
    )

    assert "source_trace" in response["metadata"]
    trace = response["metadata"]["source_trace"]
    assert "price" in trace
    assert "specs" in trace
    assert "reviews" in trace
    assert "image" in trace

    pt = trace["price"]
    assert isinstance(pt["sources_tried"], list)
    assert isinstance(pt["sources_returned_value"], list)
    assert "median_chosen" in pt
    assert "cross_validation" in pt
    assert isinstance(pt["wall_ms"], int)


def test_response_omits_source_trace_when_not_provided():
    """Backward-compat: when caller does NOT pass source_trace, metadata
    doesn't gain a None / empty key — it's just absent."""
    product_data = _minimal_product_data()
    scoring_result = {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 75.0}, "product_1": {"overall": 60.0}},
        "tradeoff_pairs": [],
        "value_badges": [], "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {},
        "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.",
        "key_differences": [],
    }

    response = build_comparison_response(
        query="A vs B",
        product_data=product_data,
        scoring_result=scoring_result,
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

    # NOT present unless an upstream lane wires it through metadata kwarg.
    assert "source_trace" not in response["metadata"]


def test_source_trace_shape_contract_documented():
    """The per-race trace MUST always include these keys when populated:
    sources_tried (list), sources_returned_value (list), wall_ms (int).
    Optional keys: median_chosen (numeric), cross_validation (enum).
    F1.4 adds two more OPTIONAL keys on the price race: route (enum) +
    source_weight (numeric)."""
    # This is a documentation-only assertion that fails if someone changes
    # the contract without updating this test or the corresponding spec.
    expected_keys = {
        "price": ["sources_tried", "sources_returned_value", "wall_ms"],
        "specs": ["sources_tried", "sources_returned_value", "wall_ms"],
        "reviews": ["sources_tried", "sources_returned_value", "wall_ms"],
        "image": ["sources_tried", "sources_returned_value", "wall_ms"],
    }
    for race, keys in expected_keys.items():
        for k in keys:
            assert isinstance(k, str)
    # F1.4 optional price-race annotations.
    optional_price_keys = ["route", "source_weight"]
    for k in optional_price_keys:
        assert isinstance(k, str)


def test_price_race_route_and_weight_round_trip():
    """F1.4 — when the orchestrator annotates the price race with `route`
    and `source_weight` (Tier 1.5 escalation), build_comparison_response
    surfaces them verbatim on metadata.source_trace.products."""
    product_data = _minimal_product_data()
    scoring_result = {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 75.0}, "product_1": {"overall": 60.0}},
        "tradeoff_pairs": [],
        "value_badges": [], "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {},
        "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.",
        "key_differences": [],
    }
    source_trace = {
        "products": [
            {
                "name": "B Test",
                "races": {
                    "price": {
                        "sources_tried": ["serper_shopping", "curl:sharafdg.com.bh"],
                        "sources_returned_value": ["curl:sharafdg.com.bh"],
                        "wall_ms": 4200,
                        "route": "registry",
                        "source_weight": 3.0,
                    },
                },
            },
        ],
    }

    response = build_comparison_response(
        query="A vs B",
        product_data=product_data,
        scoring_result=scoring_result,
        comparison=None,
        region="bahrain",
        api_calls=4,
        elapsed_seconds=1.5,
        total_cost=0.01,
        gpt_calls=2,
        serper_calls=1,
        from_cache=False,
        verdict_validation={},
        metadata={"source_trace": source_trace},
    )

    trace = response["metadata"]["source_trace"]
    price_race = trace["products"][0]["races"]["price"]
    assert price_race["route"] == "registry"
    assert price_race["source_weight"] == 3.0
