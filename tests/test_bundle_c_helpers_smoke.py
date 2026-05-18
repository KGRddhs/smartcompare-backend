"""Smoke test for tests/_bundle_c_helpers.py (Section C task C.0.1)."""
import pytest

from tests._bundle_c_helpers import (
    assert_no_forbidden_strings,
    assert_no_magnitude_fields,
    assert_response_clean_of_forbidden_strings,
    collect_user_visible_strings,
)


def test_forbidden_string_detected_estimated():
    with pytest.raises(AssertionError, match="estimated"):
        assert_no_forbidden_strings("This price is estimated")


def test_forbidden_string_detected_couldnt():
    with pytest.raises(AssertionError, match="couldn't"):
        assert_no_forbidden_strings("We couldn't fetch the price")


def test_forbidden_string_detected_arabic_failure():
    with pytest.raises(AssertionError, match="فشل"):
        assert_no_forbidden_strings("حدث فشل في التحميل")


def test_clean_string_passes():
    assert_no_forbidden_strings("Better value for your priority")


def test_empty_string_passes():
    assert_no_forbidden_strings("")


def test_magnitude_field_detected_top_level():
    with pytest.raises(AssertionError, match="magnitude"):
        assert_no_magnitude_fields({"applied_shifts": [{"magnitude": 0.3}]})


def test_magnitude_field_detected_nested():
    with pytest.raises(AssertionError, match="coefficient"):
        assert_no_magnitude_fields(
            {"scoring_v2": {"personalization": {"coefficient": 1.2}}}
        )


def test_magnitude_field_detected_in_list():
    with pytest.raises(AssertionError, match="cap_pct"):
        assert_no_magnitude_fields(
            [{"name": "perf", "cap_pct": 30}, {"name": "build"}]
        )


def test_clean_payload_passes():
    assert_no_magnitude_fields(
        {"applied_shifts": [{"dim_display": "performance", "direction": "up"}]}
    )


def test_empty_payload_passes():
    assert_no_magnitude_fields({})
    assert_no_magnitude_fields([])
    assert_no_magnitude_fields(None)


def test_collect_user_visible_strings_pulls_from_factual_verdict():
    response = {
        "products": [
            {
                "pros": ["fast charging"],
                "cons": ["fragile back"],
                "verdict_text": "Solid daily driver",
                "scoring_v2": {"value_match_caption": "Within your range"},
            }
        ],
        "comparison": {
            "winner_declaration": "iPhone wins on battery life.",
            "winner_reason": "Longer screen-on time across tests.",
        },
        "scoring_v2": {
            "factual_verdict": {
                "line1": "iPhone 16 leads by 12% on battery.",
                "line2": "Galaxy edges 0.3 stars in reviews.",
            }
        },
    }
    visible = collect_user_visible_strings(response)
    joined = " ".join(visible)
    assert "fast charging" in joined
    assert "12%" in joined
    assert "Galaxy edges" in joined


def test_assert_response_clean_passes_on_normal_payload():
    response = {
        "products": [
            {"pros": ["fast charging"], "cons": ["fragile back"]},
        ],
        "comparison": {"winner_declaration": "iPhone wins."},
    }
    assert_response_clean_of_forbidden_strings(response)


def test_assert_response_clean_fires_on_estimated_in_verdict():
    response = {
        "comparison": {"winner_declaration": "Price is estimated at 100 BHD."},
    }
    with pytest.raises(AssertionError, match="estimated"):
        assert_response_clean_of_forbidden_strings(response)
