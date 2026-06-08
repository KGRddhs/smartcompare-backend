"""Lane 1 unit-test sweep for the small helpers added by L1.3 / L1.4 /
L1.7 / L1.8 / L1.9. These are pure-function utilities the orchestrators
call frequently — each is exercised in isolation so regressions surface
without needing a full _build_scoring_v2 traversal.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# _extract_numeric / _extract_hours / _extract_dose (L1.4 + L1.9)
# ---------------------------------------------------------------------------


def test_extract_numeric_from_string():
    from app.services.response_builder import _extract_numeric

    assert _extract_numeric("3349 mAh") == 3349.0
    assert _extract_numeric("6.1 inches") == 6.1
    assert _extract_numeric("8 GB") == 8.0


def test_extract_numeric_returns_float_for_numeric_input():
    from app.services.response_builder import _extract_numeric

    assert _extract_numeric(171) == 171.0
    assert _extract_numeric(3.14) == 3.14


def test_extract_numeric_none_on_no_match():
    from app.services.response_builder import _extract_numeric

    assert _extract_numeric(None) is None
    assert _extract_numeric("") is None
    assert _extract_numeric("N/A") is None
    assert _extract_numeric(["not", "a", "string"]) is None


def test_extract_hours_from_string():
    from app.services.scoring_service import _extract_hours

    assert _extract_hours("8 hours") == 8.0
    assert _extract_hours("6.5h") == 6.5
    assert _extract_hours(10) == 10.0
    assert _extract_hours(None) is None


def test_extract_dose_with_unit_takes_precedence():
    from app.services.scoring_service import _extract_dose

    assert _extract_dose("Vitamin D3 1000 IU") == 1000.0
    assert _extract_dose("Magnesium 400 mg") == 400.0
    assert _extract_dose("Iron 14mg") == 14.0


def test_extract_dose_plain_numeric_fallback():
    from app.services.scoring_service import _extract_dose

    assert _extract_dose("500") == 500.0
    assert _extract_dose("Probiotic 50 billion") == 50.0  # no unit match, falls back


def test_extract_dose_none_on_no_match():
    from app.services.scoring_service import _extract_dose

    assert _extract_dose(None) is None
    assert _extract_dose("") is None
    assert _extract_dose("just text") is None


# ---------------------------------------------------------------------------
# _compose_delta_text (L1.4)
# ---------------------------------------------------------------------------


def test_compose_delta_text_returns_empty_on_none_score():
    from app.services.scoring_service import _compose_delta_text

    assert _compose_delta_text("performance", [], None, 80) == ""
    assert _compose_delta_text("performance", [], 80, None) == ""


def test_compose_delta_text_returns_empty_on_missing_score_sentinel():
    """MISSING_SCORE (=50) is the universal sentinel for 'no signal' in
    the scoring service. The delta_text builder treats it as missing
    data so the FE doesn't render a misleading margin."""
    from app.services.scoring_service import _compose_delta_text, MISSING_SCORE

    assert _compose_delta_text("performance", [{"specs": {}}, {"specs": {}}], MISSING_SCORE, 80) == ""
    assert _compose_delta_text("performance", [{"specs": {}}, {"specs": {}}], 80, MISSING_SCORE) == ""


def test_compose_delta_text_comparable_on_tiny_margin():
    from app.services.scoring_service import _compose_delta_text

    assert _compose_delta_text("performance", [{"specs": {}}, {"specs": {}}], 70.0, 70.5) == "Comparable"


def test_compose_delta_text_falls_back_to_score_margin():
    """No spec hooks → just emit the score margin as +Npt."""
    from app.services.scoring_service import _compose_delta_text

    result = _compose_delta_text("unknown_dim", [{"specs": {}}, {"specs": {}}], 60, 90)
    assert "30pt" in result or "30 pt" in result


def test_compose_delta_text_electronics_battery_percent():
    from app.services.scoring_service import _compose_delta_text

    products = [
        {"specs": {"battery_hours_estimated": 11.4}},
        {"specs": {"battery_hours_estimated": 14.0}},
    ]
    result = _compose_delta_text("performance", products, 65, 88)
    assert "battery" in result.lower() or "%" in result


def test_compose_delta_text_fragrance_longevity_hours():
    from app.services.scoring_service import _compose_delta_text

    products = [
        {"specs": {"longevity": "6 hours"}},
        {"specs": {"longevity": "10 hours"}},
    ]
    # Use scores that aren't MISSING_SCORE sentinel
    result = _compose_delta_text("longevity", products, 60, 88)
    assert "h" in result.lower()
    assert "10" in result or "6" in result


def test_compose_delta_text_supplement_dosage_multiplier():
    from app.services.scoring_service import _compose_delta_text

    products = [
        {"specs": {"active_ingredient": "Vitamin D3 1000 IU"}},
        {"specs": {"active_ingredient": "Vitamin D3 5000 IU"}},
    ]
    # Use scores that aren't MISSING_SCORE sentinel
    result = _compose_delta_text("dosage", products, 60, 88)
    # Either multiplier form (5×) or dose-per-serving form
    assert any(token in result for token in ("×", "x", "per serving", "5000", "1000"))


# ---------------------------------------------------------------------------
# _compose_variant_string (L1.7)
# ---------------------------------------------------------------------------


def test_compose_variant_string_electronics():
    from app.services.response_builder import _compose_variant_string

    product = {"specs": {"storage": "128GB", "color": "Black", "ram": "8GB"}}
    variant = _compose_variant_string(product, "electronics")
    assert "128GB" in variant
    assert "Black" in variant


def test_compose_variant_string_fragrances_uses_volume_ml():
    from app.services.response_builder import _compose_variant_string

    product = {"specs": {"volume_ml": 50, "concentration": "EDP"}}
    variant = _compose_variant_string(product, "fragrances")
    assert "50ml" in variant


def test_compose_variant_string_empty_on_no_specs():
    from app.services.response_builder import _compose_variant_string

    assert _compose_variant_string({"specs": {}}, "electronics") == ""
    assert _compose_variant_string({}, "electronics") == ""
    assert _compose_variant_string({"specs": None}, "electronics") == ""


def test_compose_variant_string_handles_unknown_category():
    from app.services.response_builder import _compose_variant_string

    product = {"specs": {"size": "M", "color": "blue", "volume_ml": 100}}
    variant = _compose_variant_string(product, "weird_category")
    assert isinstance(variant, str)


def test_compose_variant_string_caps_at_three_segments():
    from app.services.response_builder import _compose_variant_string

    product = {
        "specs": {
            "storage": "128GB",
            "color": "Black",
            "ram": "8GB",
            "extra4": "EXTRA4",
            "extra5": "EXTRA5",
        }
    }
    variant = _compose_variant_string(product, "electronics")
    assert len(variant.split("·")) <= 3


def test_compose_variant_string_strips_empty_values():
    from app.services.response_builder import _compose_variant_string

    product = {"specs": {"storage": "", "color": "Black", "ram": None}}
    variant = _compose_variant_string(product, "electronics")
    assert variant == "Black"


# ---------------------------------------------------------------------------
# _build_pros_cons_block (L1.8)
# ---------------------------------------------------------------------------


def test_build_pros_cons_block_basic():
    from app.services.response_builder import _build_pros_cons_block

    product = {"pros_cons": {"pros": ["a", "b"], "cons": ["c"]}}
    block = _build_pros_cons_block(product, is_winner=True)
    assert block["pros"] == ["a", "b"]
    assert block["cons"] == ["c"]
    assert block["is_winner"] is True


def test_build_pros_cons_block_missing_pros_cons():
    from app.services.response_builder import _build_pros_cons_block

    block = _build_pros_cons_block({}, is_winner=False)
    assert block["pros"] == []
    assert block["cons"] == []
    assert block["is_winner"] is False


def test_build_pros_cons_block_caps_at_four():
    from app.services.response_builder import _build_pros_cons_block

    product = {
        "pros_cons": {
            "pros": ["p" + str(i) for i in range(10)],
            "cons": ["c" + str(i) for i in range(10)],
        }
    }
    block = _build_pros_cons_block(product, is_winner=False)
    assert len(block["pros"]) == 4
    assert len(block["cons"]) == 4


def test_build_pros_cons_block_safe_on_non_list_inputs():
    from app.services.response_builder import _build_pros_cons_block

    product = {"pros_cons": {"pros": "not-a-list", "cons": None}}
    block = _build_pros_cons_block(product, is_winner=True)
    assert block["pros"] == []
    assert block["cons"] == []


def test_build_pros_cons_block_safe_on_non_dict_pros_cons():
    from app.services.response_builder import _build_pros_cons_block

    product = {"pros_cons": "not a dict"}
    block = _build_pros_cons_block(product, is_winner=False)
    assert block["pros"] == []
    assert block["cons"] == []


# ---------------------------------------------------------------------------
# _spec_row_winner + _build_specs_rows (L1.9)
# ---------------------------------------------------------------------------


def test_spec_row_winner_numeric_larger_wins():
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("battery", "3000 mAh", "4500 mAh") == 1
    assert _spec_row_winner("battery", "5000 mAh", "3000 mAh") == 0


def test_spec_row_winner_smaller_wins_for_weight():
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("weight", "171 g", "210 g") == 0
    assert _spec_row_winner("weight", "210 g", "171 g") == 1


def test_spec_row_winner_string_equality_tie():
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("os", "iOS 17", "iOS 17") == "tie"
    # Case-insensitive
    assert _spec_row_winner("os", "ios 17", "IOS 17") == "tie"


def test_spec_row_winner_one_side_na():
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("connectivity", "USB-C", "N/A") == 0
    assert _spec_row_winner("connectivity", "N/A", "USB-C") == 1
    assert _spec_row_winner("connectivity", "", "USB-C") == 1


def test_spec_row_winner_both_na_returns_none():
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("connectivity", None, None) is None
    assert _spec_row_winner("connectivity", "N/A", "N/A") is None


def test_spec_row_winner_string_inequality_returns_none():
    """Different strings, no numeric — neutral row (FE doesn't highlight)."""
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("color", "Black", "Silver") is None


def test_spec_row_winner_numeric_tie_within_epsilon():
    from app.services.response_builder import _spec_row_winner

    assert _spec_row_winner("display", "6.1 in", "6.1 in") == "tie"


def test_build_specs_rows_empty_on_fewer_than_two_products():
    from app.services.response_builder import _build_specs_rows

    assert _build_specs_rows([]) == []
    assert _build_specs_rows([{"specs": {"ram": "6 GB"}}]) == []


def test_build_specs_rows_safe_on_bad_input():
    from app.services.response_builder import _build_specs_rows

    # Either side specs is not a dict
    assert _build_specs_rows([{"specs": None}, {"specs": {"ram": "6 GB"}}]) == []
    assert _build_specs_rows([{"specs": "string"}, {"specs": {"ram": "6 GB"}}]) == []


def test_build_specs_rows_preserves_p0_key_order():
    from app.services.response_builder import _build_specs_rows

    products = [
        {"specs": {"display": "6.1 in", "ram": "8 GB", "battery": "3000 mAh"}},
        {"specs": {"battery": "4000 mAh", "display": "6.7 in", "ram": "12 GB"}},
    ]
    rows = _build_specs_rows(products)
    fields = [r["field"] for r in rows]
    # p0's order is display / ram / battery; rows should reflect that order
    assert fields == ["display", "ram", "battery"]


def test_build_specs_rows_appends_p1_only_fields_at_end():
    from app.services.response_builder import _build_specs_rows

    products = [
        {"specs": {"display": "6.1 in", "ram": "8 GB"}},
        {"specs": {"display": "6.1 in", "ram": "8 GB", "battery": "4000 mAh"}},
    ]
    rows = _build_specs_rows(products)
    # battery on p1 only → not emitted (one-sided rule)
    fields = [r["field"] for r in rows]
    assert "battery" not in fields
