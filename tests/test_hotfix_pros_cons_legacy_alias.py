"""
Bundle C v1.1 § 1a defensive regression — pros/cons readable via BOTH paths.

Context (Session 52, post-merge T+~3h):
  PROS_POP_DIAGNOSTIC + PROS_RESPONSE_DIAG both proved product_data[i]
  has `pros_cons: {pros:[4], cons:[4]}` nested at response_builder
  entry. The canonical v2 path `overview.products[i].pros / .cons`
  was always flat (lines 533-534 read pros_cons.pros and write flat
  top-level pros). But the LEGACY top-level alias
  `result["products"] = product_data` (line 622) shipped RAW
  product_data with nested `pros_cons` only — no flat `pros`/`cons`.

  qa's parser-ambiguity confusion this session (their 3rd retraction)
  traced to checking the wrong path. §1a was PROD-CONFIRMED working
  via v2; this defensive fix prevents the SAME ambiguity for any
  future consumer reading the legacy alias.

Fix: in-place project flat `pros`/`cons` onto each product_data dict
BEFORE assignment to legacy alias. Pure additive — v2 path unchanged,
nested `pros_cons` retained.
"""

from typing import Any, Dict, List

import pytest

from app.services.response_builder import build_comparison_response


def _make_product_data() -> List[Dict[str, Any]]:
    return [
        {
            "brand": "Apple",
            "name": "iPhone 15",
            "price": {"amount": 449, "currency": "BHD", "source_method": "converted_usd"},
            "rating": 4.6,
            "review_count": 1200,
            "specs": {"display": "OLED 6.1\""},
            "pros_cons": {
                "pros": ["A16 chip", "OLED display", "12MP rear", "iOS ecosystem"],
                "cons": ["Lightning port", "No always-on display"],
            },
        },
        {
            "brand": "Samsung",
            "name": "Galaxy S24",
            "price": {"amount": 380, "currency": "BHD", "source_method": "converted_usd"},
            "rating": 4.5,
            "review_count": 980,
            "specs": {"display": "Dynamic AMOLED 6.2\""},
            "pros_cons": {
                "pros": ["120Hz panel", "USB-C", "50MP camera", "S Pen support"],
                "cons": ["Slower charging vs iPhone", "Bloatware"],
            },
        },
    ]


def _make_scoring_result() -> Dict[str, Any]:
    return {
        "scores": {
            "product_0": {"overall": 78, "breakdown": {"value_score": 60}},
            "product_1": {"overall": 75, "breakdown": {"value_score": 65}},
        },
        "dimension_winners": {},
        "winner_index": 0,
        "win_margin": 3,
        "price_tiers": {"iPhone 15": "premium", "Galaxy S24": "premium"},
        "is_cross_tier": False,
        "category_weights": {},
    }


def _make_comparison() -> Dict[str, Any]:
    return {
        "winner_index": 0,
        "winner_declaration": "iPhone 15",
        "winner_reason": "Stronger long-term OS support and resale value",
        "key_tradeoff": "Galaxy ships USB-C and a 120Hz panel",
        "value_context": {"product_0": "Solid premium pick", "product_1": "Aggressive specs at the price"},
        "best_for": {"product_0": "iOS users", "product_1": "Android tinkerers"},
        "specs_comparison": {},
    }


def _build(pd_list):
    return build_comparison_response(
        product_data=pd_list,
        comparison=_make_comparison(),
        scoring_result=_make_scoring_result(),
        product_names=["iPhone 15", "Galaxy S24"],
        tradeoffs=[],
        confidence={"overall_confidence": "medium"},
        verdict_validation={"is_valid": True, "issues": []},
        user_preferences=None,
        from_cache=False,
        query="iPhone 15 vs Galaxy S24",
        region="bahrain",
        category_used="electronics",
        category_switched=False,
        original_category=None,
        total_cost=0.01,
        api_calls=4,
        gpt_calls=3,
        serper_calls=1,
        elapsed_seconds=12.5,
    )


class TestProsConsLegacyAliasFlattening:
    """Regression: BOTH the v2 (overview.products) and legacy (top-level
    products) read paths must return populated `pros`/`cons` arrays
    when product_data carries `pros_cons` nested."""

    def test_overview_products_pros_flat(self):
        result = _build(_make_product_data())

        # v2 shape — overview.products[i].pros / .cons flat (regression)
        assert len(result["overview"]["products"][0]["pros"]) == 4
        assert len(result["overview"]["products"][0]["cons"]) == 2
        assert len(result["overview"]["products"][1]["pros"]) == 4
        assert len(result["overview"]["products"][1]["cons"]) == 2
        assert "A16 chip" in result["overview"]["products"][0]["pros"]
        assert "120Hz panel" in result["overview"]["products"][1]["pros"]

    def test_legacy_products_alias_pros_flat(self):
        """THE FIX: legacy `result['products']` alias used to ship raw
        product_data WITHOUT flat pros/cons. Any consumer reading
        `product.pros` (flat) got undefined → length 0. Now projects
        flat pros/cons onto product_data dicts in-place."""
        result = _build(_make_product_data())

        assert "products" in result
        assert len(result["products"][0]["pros"]) == 4, (
            f"Legacy alias must expose flat `pros` (got: {result['products'][0].get('pros')!r})"
        )
        assert len(result["products"][0]["cons"]) == 2
        assert len(result["products"][1]["pros"]) == 4
        assert len(result["products"][1]["cons"]) == 2
        assert "A16 chip" in result["products"][0]["pros"]
        assert "Lightning port" in result["products"][0]["cons"]
        # Nested pros_cons still present (backwards compat for nested-reader consumers)
        assert result["products"][0]["pros_cons"]["pros"] == result["products"][0]["pros"]

    def test_idempotent_when_flat_already_set(self):
        """If a caller pre-populates flat `pros` on product_data we
        honor it rather than overwrite. Defensive guard for any future
        upstream that already projects."""
        pd_list = _make_product_data()
        pd_list[0]["pros"] = ["pre-set pro"]
        pd_list[0]["cons"] = ["pre-set con"]

        result = _build(pd_list)

        # Pre-set value preserved on legacy alias.
        assert result["products"][0]["pros"] == ["pre-set pro"]
        assert result["products"][0]["cons"] == ["pre-set con"]
        # Untouched product still gets projection from pros_cons.
        assert len(result["products"][1]["pros"]) == 4

    def test_pros_cons_missing_yields_empty_lists(self):
        """If product_data has no pros_cons key at all, both paths
        return empty arrays without crashing (no KeyError, no None)."""
        pd_list = _make_product_data()
        pd_list[0].pop("pros_cons", None)
        pd_list[1].pop("pros_cons", None)

        result = _build(pd_list)

        # Both paths return [] (never None, never KeyError).
        assert result["overview"]["products"][0]["pros"] == []
        assert result["overview"]["products"][0]["cons"] == []
        assert result["products"][0]["pros"] == []
        assert result["products"][0]["cons"] == []
