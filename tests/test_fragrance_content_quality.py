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


# WS-A — Task A5: response_builder fail-closed score-internals scrub (the chokepoint)
import os as _os

_os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from app.services.response_builder import build_comparison_response


def _a5_product(name, pros, cons=None):
    return {
        "brand": name.split()[0], "name": name, "full_name": name,
        "category": "fragrances",
        "price": {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"},
        "best_price": 80.0, "retailer": "noon",
        "specs": {}, "reviews": None,
        "rating": 4.2, "rating_source": None, "review_count": 5,
        "fact_check": {},
        "pros_cons": {"pros": list(pros), "cons": list(cons or [])},
    }


def _a5_scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 87.0}, "product_1": {"overall": 76.0}},
        "win_margin": 11.0,
        "tradeoff_pairs": [], "value_badges": [],
        "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {}, "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.", "key_differences": [],
    }


def test_response_builder_scrubs_score_leaks():
    pd = [
        _a5_product(
            "Versace Eros",
            pros=["Strong presentation score of 100.", "Warm, long-lasting drydown."],
            cons=["Sweeter than some prefer."],
        ),
        _a5_product(
            "Dior Sauvage",
            pros=["Fresh, versatile opening."],
            cons=["Common in crowds."],
        ),
    ]
    comparison = {
        "winner_index": 0,
        "winner_reason": "Versace Eros leads on the overall score by 4.0 points.",
        "winner_declaration": "Versace Eros wins with a 10.7-point higher overall score.",
        "key_tradeoff": "Eros scores 87/100 overall vs a fresher rival.",
    }
    resp = build_comparison_response(
        query="Versace Eros vs Dior Sauvage", product_data=pd,
        scoring_result=_a5_scoring(), comparison=comparison, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0, gpt_calls=0,
        serper_calls=0, from_cache=False, verdict_validation={},
    )

    # Top-level recommendation + overview.winner.reason are clean and non-empty.
    assert not has_score_internals(resp["recommendation"]), resp["recommendation"]
    winner = resp["overview"]["winner"]
    assert not has_score_internals(winner["reason"]), winner["reason"]
    assert winner["reason"].strip(), "fallback reason must be non-empty"
    # Declaration / name / key_tradeoff also scrubbed.
    assert not has_score_internals(winner["declaration"]), winner["declaration"]
    assert not has_score_internals(winner["name"]), winner["name"]
    assert not has_score_internals(winner["key_tradeoff"]), winner["key_tradeoff"]

    # The leaking pro is dropped from the rendered pros (overview + legacy alias),
    # the clean pro survives, and clean cons are untouched.
    ov0 = resp["overview"]["products"][0]
    assert "Strong presentation score of 100." not in ov0["pros"]
    assert "Warm, long-lasting drydown." in ov0["pros"]
    assert not any(has_score_internals(s) for s in ov0["pros"])
    assert ov0["pros_cons"]["pros"] == ov0["pros"]  # block mirror also scrubbed
    assert ov0["cons"] == ["Sweeter than some prefer."]

    legacy0 = resp["products"][0]
    assert not any(has_score_internals(s) for s in (legacy0.get("pros") or []))
    assert "Strong presentation score of 100." not in (legacy0.get("pros") or [])

    # WS-A review-gate fix — the BC `comparison` alias also ships in the payload;
    # scrub its winner_reason/winner_declaration/key_tradeoff (without the fix it
    # carried the raw leak even though the FE renders overview/recommendation).
    comp = resp["comparison"]
    assert not has_score_internals(comp["winner_reason"]), comp["winner_reason"]
    assert not has_score_internals(comp["winner_declaration"]), comp["winner_declaration"]
    assert not has_score_internals(comp["key_tradeoff"]), comp["key_tradeoff"]


# WS-B — Task B1: _compose_delta_text never emits a "+Npt" / "point" unit for
# fragrance dims. The bar magnitude carries the signal; the caption is qualitative.
from app.services.scoring_service import _compose_delta_text


def _has_point_unit(text: str) -> bool:
    """True if the caption leaks a score point-unit. Guards against the bare
    'pt' / 'point' tokens without false-positiving on letters embedded in
    real words (none of the qualitative phrases contain 'pt' or 'point')."""
    import re

    return bool(re.search(r"\bpts?\b|\bpoints?\b|\d\s*pt", text, re.I))


@pytest.mark.parametrize(
    "dim_key",
    ["character", "versatility", "presentation", "longevity", "projection", "wear_value"],
)
def test_compose_delta_text_no_point_unit_for_fragrance_dims(dim_key):
    """Empty-spec path (the one that previously fell to '+{margin}pt {label}')
    must now return a qualitative phrase or '' — never a point-unit."""
    empty = [{"specs": {}}, {"specs": {}}]
    out = _compose_delta_text(dim_key, empty, 60, 88)  # 28-pt margin previously
    assert "pt" not in out.lower(), (dim_key, out)
    assert "point" not in out.lower(), (dim_key, out)
    assert not _has_point_unit(out), (dim_key, out)


def test_compose_delta_text_longevity_real_spec_phrase_survives():
    """The legitimate longevity spec-fact branch ('{a}h vs {b}h') must remain."""
    products = [
        {"specs": {"longevity": "6 hours"}},
        {"specs": {"longevity": "10 hours"}},
    ]
    out = _compose_delta_text("longevity", products, 60, 88)
    assert "10h vs 6h" == out, out
    assert "pt" not in out.lower() and "point" not in out.lower(), out


def test_compose_delta_text_projection_reads_sillage_field():
    """SA-4: the projection branch must read the REAL schema field 'sillage'
    (there is no 'projection' spec field) and phrase it qualitatively."""
    products = [
        {"specs": {"sillage": "Heavy"}},
        {"specs": {"sillage": "Moderate"}},
    ]
    out = _compose_delta_text("projection", products, 88, 60)
    assert "Heavy" in out and "Moderate" in out, out
    assert "projection" in out.lower(), out
    assert "pt" not in out.lower() and "point" not in out.lower(), out
