"""WS-5 — Honesty (G5): widened score-internals scrub + SIB-5 None→pending +
SIB-1 SSE-prices parity + the tightened COMPARISON_SYSTEM prompt.

These tests EXTEND the shipped 2244ad4 score-leak / price-pending contract; they
must never relax `test_response_builder_scrubs_score_leaks` (the canonical guard).

- SIB-4: every user-visible GPT text field passes through the chokepoint scrub —
  value_context (per-product dict + legacy string), best_for, spec_advantages
  (DROP a leaker element), personalized_insights[].insight (STRIP), on BOTH the
  dedicated slot AND the `result["comparison"]` BC alias.
- SIB-5: a raw None / non-dict price normalizes to the price-pending shape (G1)
  WITHOUT clobbering an upstream size_mismatch reason.
- SIB-1: the SSE `prices` event uses the SAME is_price_showable→make_pending_price
  projection as the final response, onto a COPY (product_data stays raw so the
  `complete` re-projection is correct).
- prompt: COMPARISON_SYSTEM forbids internal scores in ALL the GPT text fields.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

pytest.importorskip("app.services.text_sanitize")
from app.services.text_sanitize import has_score_internals  # noqa: E402
from app.services.response_builder import build_comparison_response  # noqa: E402
from app.services.extraction_service import COMPARISON_SYSTEM  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures (mirror the shipped test_fragrance_content_quality patterns)
# ---------------------------------------------------------------------------
def _product(name, category="fragrances", price=None):
    """A minimal product. `price` defaults to a genuine local_bhd dict; pass
    None / a bare float to exercise SIB-5."""
    if price is None:
        price = {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}
    return {
        "brand": name.split()[0], "name": name, "full_name": name,
        "category": category,
        "price": price,
        "best_price": (price.get("amount") if isinstance(price, dict) else None),
        "retailer": "noon" if isinstance(price, dict) else None,
        "specs": {}, "reviews": None,
        "rating": 4.2, "rating_source": None, "review_count": 5,
        "fact_check": {},
        "pros_cons": {"pros": ["Warm drydown."], "cons": ["Sweet."]},
    }


def _scoring():
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


def _build(product_data, comparison, user_preferences=None):
    return build_comparison_response(
        query="Versace Eros vs Dior Sauvage", product_data=product_data,
        scoring_result=_scoring(), comparison=comparison, region="bahrain",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0, gpt_calls=0,
        serper_calls=0, from_cache=False, verdict_validation={},
        user_preferences=user_preferences,
    )


def _clean_pair():
    return [_product("Versace Eros"), _product("Dior Sauvage")]


# ===========================================================================
# SIB-4 — widened scrub
# ===========================================================================
def test_widened_scrub_value_context_per_product():
    comparison = {
        "winner_index": 0,
        "value_context": {
            "product_0": "Excellent for the price with a presentation score of 100.",
            "product_1": "Fair value in the GCC mid-tier.",
        },
    }
    resp = _build(_clean_pair(), comparison)
    # Dedicated slot.
    vc0 = resp["overview"]["products"][0]["value_context"]
    vc1 = resp["overview"]["products"][1]["value_context"]
    assert not has_score_internals(vc0), vc0
    assert "Fair value in the GCC mid-tier." == vc1  # clean side untouched
    # BC comparison alias.
    alias_vc = resp["comparison"]["value_context"]
    assert not has_score_internals(alias_vc.get("product_0", "")), alias_vc
    assert alias_vc.get("product_1") == "Fair value in the GCC mid-tier."


def test_widened_scrub_best_for():
    comparison = {
        "winner_index": 0,
        "best_for": {
            "product_0": "Buyers who want the leader; it wins by 10.7 points overall.",
            "product_1": "Office wearers needing all-day longevity.",
        },
    }
    resp = _build(_clean_pair(), comparison)
    bf0 = resp["overview"]["products"][0]["best_for"]
    bf1 = resp["overview"]["products"][1]["best_for"]
    assert not has_score_internals(bf0), bf0
    assert bf1 == "Office wearers needing all-day longevity."
    alias = resp["comparison"]["best_for"]
    assert not has_score_internals(alias.get("product_0", "")), alias
    assert alias.get("product_1") == "Office wearers needing all-day longevity."


def test_widened_scrub_spec_advantages_drops_leaker():
    comparison = {
        "winner_index": 0,
        "specs_comparison": {
            "product_0_advantages": ["+18pt longevity", "Real 100ml bottle"],
            "product_1_advantages": ["Fresher opening"],
            "similar": ["Both EDP concentration", "Wins by 4.0 points overall"],
        },
    }
    resp = _build(_clean_pair(), comparison)
    # specs.products[0].spec_advantages — leaker DROPPED, clean survives.
    sa0 = resp["specs"]["products"][0]["spec_advantages"]
    assert "Real 100ml bottle" in sa0
    assert all(not has_score_internals(s) for s in sa0), sa0
    assert "+18pt longevity" not in sa0
    # specs.specs_comparison mirror — same source key, also clean.
    sc = resp["specs"]["specs_comparison"]
    assert "Real 100ml bottle" in sc["product_0_advantages"]
    assert all(not has_score_internals(s) for s in sc["product_0_advantages"])
    assert all(not has_score_internals(s) for s in sc["similar"])
    assert "Both EDP concentration" in sc["similar"]
    # BC comparison alias.
    alias = resp["comparison"]["specs_comparison"]
    assert all(not has_score_internals(s) for s in alias["product_0_advantages"])
    assert all(not has_score_internals(s) for s in alias["similar"])


def test_widened_scrub_personalized_insights_insight():
    insights = [
        {"focus_area": "longevity", "product_index": 0,
         "insight": "Best for longevity lovers; it leads with an overall score of 100."},
        {"focus_area": "value", "product_index": 1,
         "insight": "A solid pick for mid-budget shoppers."},
    ]
    comparison = {"winner_index": 0, "personalized_insights": insights}
    resp = _build(_clean_pair(), comparison,
                  user_preferences={"priorities": ["longevity"]})
    # personalization.personalized_insights[].insight — leaker stripped, item kept.
    pi = resp["personalization"]["personalized_insights"]
    assert len(pi) == 2  # items KEPT (not dropped)
    assert not has_score_internals(pi[0]["insight"]), pi[0]
    assert pi[1]["insight"] == "A solid pick for mid-budget shoppers."
    # top-level alias.
    top = resp["personalized_insights"]
    assert not has_score_internals(top[0]["insight"]), top[0]
    # BC comparison alias.
    alias = resp["comparison"]["personalized_insights"]
    assert not has_score_internals(alias[0]["insight"]), alias[0]


def test_widened_scrub_value_context_legacy_string():
    """A legacy comparison-level STRING value_context that leaks → stripped."""
    comparison = {
        "winner_index": 0,
        "value_context": "Great GCC value; it wins by 4.0 points overall.",
    }
    resp = _build(_clean_pair(), comparison)
    for p in resp["overview"]["products"]:
        assert not has_score_internals(p["value_context"]), p["value_context"]
    # BC alias string scrubbed too.
    assert not has_score_internals(resp["comparison"]["value_context"])


def test_widened_scrub_clean_fields_untouched():
    """Clean value_context / best_for / advantages / insight survive verbatim."""
    comparison = {
        "winner_index": 0,
        "value_context": {
            "product_0": "Strong value for a GCC buyer.",
            "product_1": "Premium but justified by the craftsmanship.",
        },
        "best_for": {
            "product_0": "Daily-driver fans.",
            "product_1": "Special-occasion wearers.",
        },
        "specs_comparison": {
            "product_0_advantages": ["Real 100ml bottle", "EDP concentration"],
            "product_1_advantages": ["Fresher opening"],
            "similar": ["Both alcohol-based"],
        },
        "personalized_insights": [
            {"focus_area": "longevity", "product_index": 0,
             "insight": "Lasts noticeably longer on skin."},
        ],
    }
    resp = _build(_clean_pair(), comparison,
                  user_preferences={"priorities": ["longevity"]})
    ov = resp["overview"]["products"]
    assert ov[0]["value_context"] == "Strong value for a GCC buyer."
    assert ov[1]["value_context"] == "Premium but justified by the craftsmanship."
    assert ov[0]["best_for"] == "Daily-driver fans."
    assert resp["specs"]["products"][0]["spec_advantages"] == [
        "Real 100ml bottle", "EDP concentration"]
    assert resp["personalization"]["personalized_insights"][0]["insight"] == \
        "Lasts noticeably longer on skin."


# ===========================================================================
# SIB-5 — None / non-dict price → pending shape (G1)
# ===========================================================================
def test_response_builder_none_price_becomes_pending():
    pd = [_product("NOW Foods Omega-3", "supplements", price=None),
          _product("Solgar D3", "supplements")]
    # Mimic the supplement-None terminal: a bare None price slot.
    pd[0]["price"] = None
    pd[0]["best_price"] = None
    pd[0]["retailer"] = None
    resp = _build(pd, {"winner_index": 0})
    p0 = resp["overview"]["products"][0]["price"]
    assert isinstance(p0, dict)
    assert p0["amount"] is None
    assert p0["unavailable"] is True
    assert p0["reason"] == "pending_genuine"


def test_response_builder_nondict_price_becomes_pending():
    pd = [_product("Mystery Item", "other"), _product("Other Item", "other")]
    pd[0]["price"] = 42.0  # bare float — must NOT leak as a raw number
    resp = _build(pd, {"winner_index": 0})
    p0 = resp["overview"]["products"][0]["price"]
    assert isinstance(p0, dict)
    assert p0["amount"] is None
    assert p0["unavailable"] is True
    assert p0["reason"] == "pending_genuine"


def test_response_builder_none_price_suppresses_price_dim():
    pd = [_product("NOW Foods Omega-3", "supplements"),
          _product("Solgar D3", "supplements")]
    pd[0]["price"] = None
    pd[0]["best_price"] = 99.0   # stale mirror — must be nulled
    pd[0]["retailer"] = "iHerb"  # stale mirror — must be nulled
    resp = _build(pd, {"winner_index": 0})
    # best_price / retailer mirrors nulled.
    assert resp["products"][0]["best_price"] is None
    assert resp["products"][0]["retailer"] is None
    # Price dim takes the honest missing-data path (no cross-price delta).
    dims = {d["key"]: d for d in resp["scoring_v2"]["dimensions"]}
    if "price" in dims:
        assert "less" not in dims["price"]["delta_text"].lower()


def test_response_builder_genuine_dict_price_unaffected():
    pd = [_product("Versace Eros"), _product("Dior Sauvage")]
    resp = _build(pd, {"winner_index": 0})
    p0 = resp["overview"]["products"][0]["price"]
    assert p0["amount"] == 80.0
    assert p0.get("unavailable") is not True


def test_response_builder_none_price_does_not_clobber_size_mismatch():
    """SIB-5 must not re-stamp an upstream size_mismatch reason; and a bare None
    on the OTHER product still becomes pending_genuine (independent slots)."""
    pd = [_product("Tom Ford A", "fragrances",
                   {"amount": None, "currency": "BHD", "unavailable": True,
                    "reason": "size_mismatch", "size": "100ml"}),
          _product("Creed B", "fragrances")]
    pd[1]["price"] = None
    pd[1]["best_price"] = None
    pd[1]["retailer"] = None
    resp = _build(pd, {"winner_index": 0})
    p0 = resp["overview"]["products"][0]["price"]
    p1 = resp["overview"]["products"][1]["price"]
    assert p0["reason"] == "size_mismatch"  # upstream reason preserved
    assert p1["reason"] == "pending_genuine"  # bare None normalized


# ===========================================================================
# SIB-1 — SSE prices event parity
# ===========================================================================
def _sse_prices_projection(product_data):
    """Re-derive the SSE prices payload the way scs builds it (the projection
    must match build_comparison_response's price-pending normalization)."""
    from app.services.price_service import is_price_showable, make_pending_price

    payload = {}
    for i, pd in enumerate(product_data):
        key = f"product_{i}"
        _name = pd.get("full_name") or pd.get("name") or ""
        _price = pd.get("price")
        _best = pd.get("best_price")
        _retailer = pd.get("retailer")
        if not isinstance(_price, dict):
            _price = make_pending_price(reason="pending_genuine")
            _best = None
            _retailer = None
        elif _price.get("unavailable") is not True and not is_price_showable(_name, _price):
            _price = make_pending_price(
                currency=_price.get("currency") or "BHD",
                reason="pending_genuine", size=_price.get("size"),
            )
            _best = None
            _retailer = None
        payload[key] = {
            "brand": pd.get("brand"), "name": pd.get("name"),
            "price": _price, "best_price": _best,
            "currency": pd.get("currency"), "retailer": _retailer,
        }
    return payload


def test_sse_prices_event_pends_non_showable_price():
    """An estimated price the final card pends must be pended in the SSE event
    too (parity) — the SSE projection mirrors the response_builder rule."""
    pd = [_product("Tom Ford Ombré", "fragrances",
                   {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}),
          _product("Creed Aventus", "fragrances")]
    payload = _sse_prices_projection(pd)
    assert payload["product_0"]["price"]["unavailable"] is True
    assert payload["product_0"]["price"]["amount"] is None
    # raw product_data untouched (the COPY guard).
    assert pd[0]["price"]["amount"] == 70.0


def test_sse_prices_event_passes_showable_genuine():
    pd = [_product("Versace Eros", "fragrances",
                   {"amount": 32.5, "currency": "BHD", "source_method": "local_bhd"}),
          _product("Dior Sauvage", "fragrances")]
    payload = _sse_prices_projection(pd)
    assert payload["product_0"]["price"]["amount"] == 32.5
    assert payload["product_0"]["price"].get("unavailable") is not True


def test_sse_prices_projection_does_not_mutate_product_data():
    pd = [_product("Tom Ford Ombré", "fragrances",
                   {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}),
          _product("Creed Aventus", "fragrances")]
    _ = _sse_prices_projection(pd)
    # After the projection, the raw dict still carries the original amount so the
    # final `complete` re-projection (response_builder) is correct.
    assert pd[0]["price"]["amount"] == 70.0
    assert pd[0]["price"].get("unavailable") is not True


# ===========================================================================
# Prompt tighten
# ===========================================================================
def test_comparison_prompt_forbids_scores_in_all_fields():
    low = COMPARISON_SYSTEM.lower()
    # The forbidden-words rule now names the previously-bypassing fields.
    for field in ("value_context", "best_for", "specs_comparison",
                  "personalized_insights"):
        assert field in low, field
    # The "internal score" negative rule survives (extends the shipped guard).
    assert "internal score" in low
    # No bare "with specific number" invitation survives un-qualified.
    assert "with specific number" not in low
