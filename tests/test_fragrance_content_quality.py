# tests/test_fragrance_content_quality.py
import pytest
pytest.importorskip("app.services.text_sanitize")  # collection-safe until WS-A lands
from app.services.text_sanitize import strip_score_internals, has_score_internals


# WS-A — score internals
@pytest.mark.parametrize("leak", [
    "Versace Eros leads on the overall score by 4.0 points.",
    "Tom Ford wins with a 10.7-point higher overall score.",
    "Strong presentation score of 100.",
    "Scores 87/100 overall.",
])
def test_strip_score_internals_removes_known_leaks(leak):
    out = strip_score_internals(leak)
    assert not has_score_internals(out), out


def test_strip_score_internals_keeps_clean_facts():
    txt = "Longer-lasting on skin with a warmer drydown."
    assert strip_score_internals(txt) == txt


# WS-A — Task A2: base verdict prompt must not instruct numeric score cites
from app.services.extraction_service import COMPARISON_SYSTEM  # the base constant


def test_base_prompt_forbids_numeric_score_cite():
    low = COMPARISON_SYSTEM.lower()
    assert "specific number or fact" not in low      # :615 schema
    assert "numeric advantage" not in low            # :645 rule
    assert "internal score" in low                   # the new negative rule is present


# WS-A — Task A3: build_scores_summary feeds GPT qualitative relatives, no raw numbers
from app.services.scoring_service import get_scoring_service


def test_scores_summary_has_no_raw_numbers():
    sr = {
        "scores": {
            "product_0": {"overall": 87, "breakdown": {"longevity_score": 80}},
            "product_1": {"overall": 76, "breakdown": {"longevity_score": 70}},
        },
        "winner_index": 0,
        "win_margin": 11,
        "dimension_winners": {},
    }
    out = get_scoring_service().build_scores_summary(sr, ["A", "B"])
    assert "/100" not in out
    assert "11 points" not in out and "by 11" not in out
    assert not any(ch.isdigit() for ch in out)


# WS-A — Task A4: deterministic partial verdict is qualitative (no score margin)
from app.services.structured_comparison_service import get_comparison_service


def test_deterministic_partial_verdict_no_score_margin():
    out = get_comparison_service()._deterministic_partial_verdict(
        {},
        {"scores": {"product_0": {"overall": 80}, "product_1": {"overall": 70}}, "winner_index": 0},
        ["Eros", "Sauvage"],
        [],
    )
    r = out["winner_reason"].lower()
    assert "points" not in r
    assert "overall score" not in r
    assert "Eros" in out["winner_reason"]
