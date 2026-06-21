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


# WS-C — Task C1: verdict-safe price projection. The dict handed to the GPT
# verdict (json.dumps'd) must NEVER carry a pending product's raw amount, and
# the projection must be a COPY (the original product dict stays intact).
from app.services.extraction_service import _verdict_safe_product


def test_verdict_safe_product_strips_pending_amount_without_mutating():
    """An `estimated` price is NOT showable → the verdict copy must have
    amount=None (so json.dumps can't leak it), while the ORIGINAL dict keeps
    its 80.0 amount (copy, not in-place mutation)."""
    p = {
        "name": "Oud Wood",
        "full_name": "Tom Ford Oud Wood",
        "price": {"amount": 80.0, "currency": "BHD", "source_method": "estimated"},
    }
    out = _verdict_safe_product(p)
    # The verdict-facing copy hides the amount.
    assert out["price"].get("amount") is None, out["price"]
    assert out["price"].get("unavailable") is True, out["price"]
    # The ORIGINAL is untouched (copy-on-write, not mutation).
    assert p["price"]["amount"] == 80.0
    # It is a distinct object (defensive: not the same price dict reference).
    assert out["price"] is not p["price"]


def test_verdict_safe_product_preserves_showable_price():
    """A genuine `local_bhd` price IS showable → amount preserved unchanged."""
    p = {
        "name": "Sauvage",
        "full_name": "Dior Sauvage 100ml",
        "price": {
            "amount": 32.5,
            "currency": "BHD",
            "source_method": "local_bhd",
            "retailer": "noon",
        },
    }
    out = _verdict_safe_product(p)
    assert out["price"].get("amount") == 32.5
    assert out["price"].get("source_method") == "local_bhd"
    # Original intact regardless.
    assert p["price"]["amount"] == 32.5


# WS-C — Task C2: COMPARISON_SYSTEM must forbid price/value claims about a
# product whose price is unavailable/null (the verdict-safe projection from C1
# hides the amount; this clause keeps GPT from inventing a price/value claim
# anyway). Static prompt audit — collection-safe, no network.
def test_comparison_system_forbids_price_claims_when_pending():
    low = COMPARISON_SYSTEM.lower()
    assert "do not make any price" in low
    assert "unavailable" in low and "non-price" in low


# WS-C — Task C3: fail-closed price-adjective drop. A product whose price is
# pending (unavailable=True) must NOT carry any pro/con asserting a price
# adjective (premium price / affordable / cheaper / great value / ...) — those
# render beside a "Pricing lands in a future update" card and read as a
# contradiction. Defense-in-depth beside C1 (which hides the amount from GPT)
# and C2 (which tells GPT not to invent one). A SHOWABLE product's price
# adjectives are left untouched.
def test_response_builder_drops_price_adjective_for_pending_product():
    p_show = _a5_product(
        "Versace Eros",
        pros=["Great value for the longevity you get.", "Warm, long-lasting drydown."],
        cons=["Sweeter than some prefer."],
    )
    p_pend = _a5_product(
        "Dior Sauvage",
        pros=["Fresh, versatile opening."],
        cons=["Premium price point.", "Common in crowds."],
    )
    # Force product[1] pending — already-pending prices are preserved by the
    # response_builder normalization (its own `unavailable is True` skip), so
    # this deterministically reaches the C3 drop without relying on the
    # is_price_showable heuristics.
    p_pend["price"] = {
        "amount": None,
        "currency": "BHD",
        "unavailable": True,
        "reason": "pending_genuine",
    }
    p_pend["best_price"] = None
    p_pend["retailer"] = None

    resp = build_comparison_response(
        query="Versace Eros vs Dior Sauvage",
        product_data=[p_show, p_pend],
        scoring_result=_a5_scoring(),
        comparison={"winner_index": 0, "winner_reason": "Eros is the stronger pick."},
        region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0, gpt_calls=0,
        serper_calls=0, from_cache=False, verdict_validation={},
    )

    # The pended product's price-adjective con is dropped; the clean con survives.
    pend = resp["overview"]["products"][1]
    assert "Premium price point." not in pend["cons"], pend["cons"]
    assert "Common in crowds." in pend["cons"], pend["cons"]
    # The block mirror + legacy alias are scrubbed too (same canonical list).
    assert "Premium price point." not in pend["pros_cons"]["cons"]
    legacy_pend = resp["products"][1]
    assert "Premium price point." not in (legacy_pend.get("cons") or [])

    # The SHOWABLE product keeps its price-adjective pro untouched.
    show = resp["overview"]["products"][0]
    assert "Great value for the longevity you get." in show["pros"], show["pros"]
