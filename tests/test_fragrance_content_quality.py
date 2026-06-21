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


# ---------------------------------------------------------------------------
# WS-D — grammatical, non-mangled review-praise prose
# build_review_praise's REAL signature is build_review_praise(reviews) where
# reviews = {"review_summary": {"overall_sentiment": ..., "highlights": [...]}}.
# ---------------------------------------------------------------------------
def _reviews_with_highlights(points):
    """Wrap positive highlight strings in the dict shape build_review_praise reads."""
    return {
        "review_summary": {
            "overall_sentiment": "positive",
            "highlights": [{"sentiment": "positive", "point": p} for p in points],
        }
    }


@pytest.mark.parametrize("lead", [
    "has a sweet, citrusy opening",
    "Known for its luxurious scent",
    "lasts all day",
])
def test_review_praise_grammar_on_hard_leads(lead):
    """D1: a verb/relative/participial lead must NOT be glued straight after
    'highlight' ('Owners consistently highlight has a...' is ungrammatical)."""
    from app.services.review_service import build_review_praise
    out = build_review_praise(_reviews_with_highlights([lead])) or ""
    assert out, "expected a praise line"
    low = out.lower()
    assert "highlight has" not in low, out
    assert "highlight known for" not in low, out
    assert "highlight lasts" not in low, out
    # The clause's words must still be present (reframed, not dropped).
    first_word = lead.split()[0].lower()
    assert first_word in low, out


def test_review_praise_keeps_noun_phrase_highlight_glue():
    """D1: a plain noun-phrase lead still reads with the 'highlight' glue."""
    from app.services.review_service import build_review_praise
    out = build_review_praise(_reviews_with_highlights(["rich sillage that fills a room"])) or ""
    assert out, "expected a praise line"
    assert out.lower().startswith("owners consistently highlight"), out


def test_lower_first_preserves_proper_nouns_and_acronyms():
    """D2: _lower_first must not corrupt brands ('Creed') or acronyms ('GPS')."""
    from app.services.review_service import _lower_first
    assert _lower_first("Creed Aventus is bold").startswith("Creed"), "brand lowercased"
    assert _lower_first("GPS-grade sealing").startswith("GPS"), "acronym lowercased"
    # A plain capitalized common-word lead still lowercases (sentence-merge case).
    assert _lower_first("Amazing scent") == "amazing scent"


# WS-D — Task D3: kill the interior "Per <domain>:" / "Per :" artifact in praise.
# clean_review_citations runs BEFORE praise and rewrites an INTERIOR bare [N] into
# "Per <domain>: " mid-sentence; _strip_attribution only stripped a start-anchored
# prefix, so an interior "Per <domain>:" (and the leftover "Per :" once the bare
# domain is scrubbed) survived into the built praise. Reproduce through the REAL
# two-step pipeline (clean_review_citations -> build_review_praise).
def test_review_praise_no_interior_per_domain_artifact():
    """D3: an interior citation that clean_review_citations turns into a
    'Per <domain>:' fragment must NOT leak into the built praise."""
    from app.services.review_service import (
        clean_review_citations,
        build_review_praise,
    )
    reviews = {
        "review_summary": {
            "overall_sentiment": "positive",
            "consensus": "",  # force praise to come from the highlight, not fallback
            "highlights": [
                # Noun-phrase lead (keeps the 'highlight {clause}' frame) with an
                # INTERIOR [2] marker -> clean_review_citations injects
                # "Per fragrantica.com: " mid-sentence.
                {
                    "sentiment": "positive",
                    "point": "Rich amber drydown [2] with strong sillage all evening",
                },
            ],
        }
    }
    search_results = [
        {"link": "https://www.example.com/a"},
        {"link": "https://fragrantica.com/x"},  # index 2 -> fragrantica.com
    ]
    cleaned = clean_review_citations(reviews, search_results)
    # Precondition: the interior artifact really was injected.
    assert "Per fragrantica.com:" in cleaned["review_summary"]["highlights"][0]["point"]

    praise = build_review_praise(cleaned) or ""
    assert praise, "expected a praise line built from the positive highlight"
    low = praise.lower()
    assert "per " not in low, praise          # no "Per <domain>:" / "Per :" lead-in
    assert "per:" not in low, praise          # no collapsed "Per:" fragment
    assert "fragrantica" not in low, praise   # domain token fully gone
    # The real praise words survive (clause reframed, not dropped).
    assert "amber" in low and "sillage" in low, praise


def test_strip_attribution_removes_interior_per_domain():
    """D3 (unit): _strip_attribution strips an interior 'Per <domain>:' and any
    leftover 'Per :' fragment, not only a start-anchored prefix."""
    from app.services.review_service import _strip_attribution
    # Interior occurrence (multi-dot domain too).
    out = _strip_attribution("A sweet opening Per bn.boots.com: that lasts all day")
    assert "per " not in out.lower() and "boots" not in out.lower(), out
    assert "sweet opening" in out and "lasts all day" in out, out
    # Already-fragmented leftover (domain previously eaten).
    out2 = _strip_attribution("Rich amber drydown Per : with strong sillage")
    assert "per" not in out2.lower(), out2
    assert "amber drydown" in out2 and "strong sillage" in out2, out2
    # Start-anchored prefix still stripped (preserve current good behavior).
    out3 = _strip_attribution("Per fragrantica.com: deep and long-lasting")
    assert out3 == "deep and long-lasting", out3
    # False-positive guard: a real "per" usage with no domain TLD survives.
    out4 = _strip_attribution("lasts per the bottle description all day")
    assert out4 == "lasts per the bottle description all day", out4


# ---------------------------------------------------------------------------
# WS-E — Task E1: fragrance subtype spec keys survive extract_specs (SA-1).
# The fragrance subtype prompt (PRODUCT_TYPE_SCHEMAS["fragrances.*"]) asks GPT
# for `longevity_hrs` / `volume_ml`, but extract_specs filters to the canonical
# CATEGORY_SPEC_SCHEMAS["fragrances"] keys (`longevity` / `volume`), so the
# subtype-named values were silently dropped to "N/A". Alias them through the
# filter onto their canonical homes. Scope = fragrances only (no new schema
# fields; projection_m DEFERRED — canonical schema has no metric-projection
# home, sillage is a descriptive field).
# ---------------------------------------------------------------------------
import json as _json
from unittest.mock import patch as _patch, AsyncMock as _AsyncMock, MagicMock as _MagicMock


def _mock_specs_client(content_dict):
    """Build a get_client() mock whose chat.completions.create returns the
    given JSON spec dict (the extract_specs GPT-output contract)."""
    resp = _MagicMock()
    resp.choices = [_MagicMock()]
    resp.choices[0].message.content = _json.dumps(content_dict)
    resp.usage = _MagicMock(prompt_tokens=10, completion_tokens=10)
    client = _AsyncMock()
    client.chat.completions.create = _AsyncMock(return_value=resp)
    return client


@pytest.mark.asyncio
async def test_extract_specs_aliases_fragrance_subtype_keys():
    """A fragrance GPT response carrying subtype-named keys (longevity_hrs,
    volume_ml) must reconcile onto the canonical longevity/volume rather than
    being filtered out to 'N/A'."""
    from app.services import extraction_service

    gpt_out = {
        "brand": "Creed",
        "model": "Aventus",
        "variant": "EDP",
        "category": "fragrances",
        "scent_family": "Fruity Chypre",
        # Subtype-named keys (what the fragrances.* prompt asks for) — NO canonical
        # `longevity`/`volume` present, so without the alias these drop to N/A.
        "longevity_hrs": "8",
        "volume_ml": "100",
    }
    with _patch(
        "app.services.extraction_service.get_client",
        return_value=_mock_specs_client(gpt_out),
    ):
        cleaned, _usage = await extraction_service.extract_specs(
            brand="Creed", name="Aventus", variant="EDP",
            category="fragrances", search_context="some context",
        )

    assert cleaned["longevity"] == "8", cleaned
    assert cleaned["volume"] == "100", cleaned
    assert cleaned["scent_family"] == "Fruity Chypre", cleaned


@pytest.mark.asyncio
async def test_extract_specs_canonical_key_wins_over_subtype_alias():
    """If GPT emits BOTH the canonical key and its subtype alias, the canonical
    value is authoritative — the alias must not clobber it."""
    from app.services import extraction_service

    gpt_out = {
        "brand": "Dior", "model": "Sauvage", "variant": "EDT",
        "category": "fragrances",
        "longevity": "10 hours",   # canonical present
        "longevity_hrs": "6",      # stale alias must NOT override
        "volume": "60 ml",
    }
    with _patch(
        "app.services.extraction_service.get_client",
        return_value=_mock_specs_client(gpt_out),
    ):
        cleaned, _usage = await extraction_service.extract_specs(
            brand="Dior", name="Sauvage", variant="EDT",
            category="fragrances", search_context="ctx",
        )

    assert cleaned["longevity"] == "10 hours", cleaned
    assert cleaned["volume"] == "60 ml", cleaned


@pytest.mark.asyncio
async def test_extract_specs_alias_is_fragrance_scoped():
    """The subtype-key alias is fragrance-scoped — a non-fragrance category
    with an unrelated `_hrs` key is unaffected (no cross-category leakage)."""
    from app.services import extraction_service

    gpt_out = {
        "brand": "Apple", "model": "iPhone 15", "variant": "",
        "category": "electronics",
        "display": "6.1 inch OLED",
        "battery_hrs": "20",  # an electronics key; NOT a fragrance alias target
    }
    with _patch(
        "app.services.extraction_service.get_client",
        return_value=_mock_specs_client(gpt_out),
    ):
        cleaned, _usage = await extraction_service.extract_specs(
            brand="Apple", name="iPhone 15", variant="",
            category="electronics", search_context="ctx",
        )

    # No fragrance `longevity`/`volume` keys injected into an electronics result.
    assert "longevity" not in cleaned, cleaned
    assert "volume" not in cleaned, cleaned
