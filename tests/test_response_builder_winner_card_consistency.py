"""Issue #99 — the winner card must name and praise the DETERMINISTIC winner.

The H1 override in `response_builder.build_comparison_response` replaces only
`winner_index` when the deterministic scoring winner disagrees with GPT's
prose-derived pick. Every narrative field (`overview.winner.name`,
`.declaration`, `.reason`, the mirrored top-level `recommendation`) and the BC
alias `comparison["winner_index"]` still came from GPT, so a shared card could
highlight product A while naming and praising product B.

These tests pin ONE source of truth: on mismatch every winner-facing field
agrees with `winner_index`; with no mismatch the payload is unchanged.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import build_comparison_response


def _products(names):
    """Minimal two-product payload — the winner card only needs names."""
    return [
        {
            "name": n,
            "specs": {},
            "price": {
                "amount": 3.5,
                "currency": "BHD",
                "source_method": "local_bhd",
                "title": n,
                "url": "https://store.bh/p/x",
            },
        }
        for n in names
    ]


def _build(*, names, scoring_winner, gpt_winner, declaration="", reason="",
           tradeoff=None, product_names=None):
    comparison = {"winner_index": gpt_winner}
    if declaration:
        comparison["winner_declaration"] = declaration
    if reason:
        comparison["winner_reason"] = reason
    if tradeoff is not None:
        comparison["key_tradeoff"] = tradeoff
    kwargs = {}
    if product_names is not None:
        kwargs["product_names"] = product_names
    return build_comparison_response(
        products=_products(names),
        comparison=comparison,
        scoring_result={"winner_index": scoring_winner},
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _prose_reconcile_off(monkeypatch):
    """This file pins the UNFLAGGED safety repair only. The richer deterministic
    template prose lives behind ENABLE_WINNER_PROSE_RECONCILE (default OFF) and
    is covered by tests/test_winner_prose_reconciliation.py; clearing the env
    here keeps these cases honest if the flag is ever exported in a shell."""
    monkeypatch.delenv("ENABLE_WINNER_PROSE_RECONCILE", raising=False)
    yield


# ---------------------------------------------------------------------------
# 1-4, 8 — mismatch: everything must follow the deterministic winner
# ---------------------------------------------------------------------------

def test_mismatch_winner_name_is_deterministic_product():
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=0,
        gpt_winner=1,
        declaration="Product B wins on flavor",
    )
    assert result["overview"]["winner"]["name"] == "Product A"


def test_mismatch_declaration_is_dropped():
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=0,
        gpt_winner=1,
        declaration="Product B wins on flavor",
    )
    assert result["overview"]["winner"]["declaration"] == ""


def test_mismatch_reason_never_names_the_loser():
    winner = "Manama Pickles Achbara Sauce"
    loser = "Manama Pickles Maabooch Kuwaiti Red 250g"
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=1,
        reason=f"{loser} has the richer flavor.",
    )
    assert "Maabooch" not in result["overview"]["winner"]["reason"]
    assert "Maabooch" not in result["recommendation"]
    assert result["overview"]["winner"]["reason"] == f"{winner} is the stronger overall pick."


def test_mismatch_bc_comparison_winner_index_is_reindexed():
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=0,
        gpt_winner=1,
        declaration="Product B wins on flavor",
    )
    assert result["comparison"]["winner_index"] == 0
    assert result["winner_index"] == 0


def test_mismatch_key_tradeoff_never_names_the_loser():
    winner = "Manama Pickles Achbara Sauce"
    loser = "Manama Pickles Maabooch Kuwaiti Red 250g"
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=1,
        tradeoff=f"{loser} is the better pick if you want heat.",
    )
    assert loser not in result["overview"]["winner"]["key_tradeoff"]
    assert "Maabooch" not in result["overview"]["winner"]["key_tradeoff"]
    assert result["overview"]["winner"]["key_tradeoff"] == ""


def test_mismatch_key_tradeoff_dropped_even_when_it_names_the_winner():
    """The containment check could never catch this one: on a mismatch GPT
    writes key_tradeoff from the INVERTED orientation, framing the SHIPPED
    winner as the runner-up. The sentence names the WINNER, so a loser-name
    check passed it straight through — and the card then told the reader its
    own pick was the compromise."""
    winner = "Manama Pickles Achbara Sauce"
    loser = "Manama Pickles Maabooch Kuwaiti Red 250g"
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=1,
        tradeoff=f"{winner} costs more for a similar jar.",
    )
    assert result["overview"]["winner"]["key_tradeoff"] == ""


# ---------------------------------------------------------------------------
# The load-bearing pin — the repair must never regress to a containment check
# ---------------------------------------------------------------------------

_PHRASINGS = [
    ("full_name", "{loser} offers a noticeably richer flavour for the price."),
    ("pronoun", "It offers a noticeably richer flavour for the price."),
    ("short_name", "Budget Pickle wins on everyday value."),
    ("brand_fragment", "The Budget option is the better everyday buy."),
    ("subject_free", "Delivers a richer flavour at a lower price point."),
]


@pytest.mark.parametrize("label,template", _PHRASINGS, ids=[p[0] for p in _PHRASINGS])
def test_mismatch_drops_every_gpt_reason_phrasing(label, template):
    """REGRESSION FENCE against re-introducing a loser-name containment check.

    Measured against the containment implementation, 4 of these 5 shipped the
    loser-praise VERBATIM into overview.winner.reason and the top-level
    recommendation (which fan out to Home's verdict_short, History and the
    Share text); only `full_name` was caught. The cap that makes containment
    structurally weak is real: extraction_service holds winner_reason to 20
    words while a full product name runs 5-6, so the prompt pushes the model
    away from the one string a containment check can see.

    On a mismatch GPT wrote this prose to justify ITS pick, so by construction
    it argues for the product we did not choose. Every phrasing must be
    dropped, whatever it happens to name."""
    winner = "Manama Pickles Achbara Sauce"
    loser = "Budget Pickle Co Everyday Jar 500g"
    reason = template.format(loser=loser)
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=1,
        reason=reason,
    )
    expected = f"{winner} is the stronger overall pick."
    assert result["overview"]["winner"]["reason"] == expected
    assert result["recommendation"] == expected
    # the BC alias reads the same source field and must not keep the original
    assert result["comparison"]["winner_reason"] == expected
    assert reason not in (
        result["overview"]["winner"]["reason"],
        result["recommendation"],
        result["comparison"]["winner_reason"],
    )


# ---------------------------------------------------------------------------
# 5, 6 — guards: green before AND after
# ---------------------------------------------------------------------------

def test_no_mismatch_overview_winner_unchanged():
    """No disagreement -> byte-identical to today's output (declaration and
    reason still GPT's, `name` still the declaration text)."""
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=0,
        gpt_winner=0,
        declaration="Product A wins on flavor",
        reason="Product A has the richer flavor.",
        tradeoff="Product B is milder.",
    )
    assert result["overview"]["winner"] == {
        "product_index": 0,
        "name": "Product A wins on flavor",
        "declaration": "Product A wins on flavor",
        "reason": "Product A has the richer flavor.",
        "key_tradeoff": "Product B is milder.",
        "margin": 0,
    }


def test_shared_brand_token_reason_survives_on_agreement():
    """Guard against over-scrub. The two products share the brand tokens
    "Manama Pickles"; a reason naming only the winner must survive.

    RETARGETED from the MISMATCH path to the AGREEMENT path. It previously
    asserted survival on a mismatch, which only held while the repair used a
    loser-FULL-name containment check — and that check let 4 of 5 realistic
    loser-praising phrasings through (see
    `test_mismatch_drops_every_gpt_reason_phrasing`), so the reason is now
    dropped unconditionally on a mismatch. Agreement is where "GPT prose
    survives untouched" is the actual contract, and it is where the over-scrub
    risk this test exists to catch actually lives."""
    winner = "Manama Pickles Achbara Sauce"
    loser = "Manama Pickles Maabooch Kuwaiti Red 250g"
    reason = f"{winner} carries a cleaner, brighter finish."
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=0,
        reason=reason,
    )
    assert result["overview"]["winner"]["reason"] == reason
    assert result["recommendation"] == reason


def test_shared_brand_token_mismatch_fallback_names_the_winner():
    """The mismatch counterpart to the test above: the fallback that replaces
    GPT's reason names the DETERMINISTIC winner and never the loser, even
    though the two product names share the "Manama Pickles" brand prefix."""
    winner = "Manama Pickles Achbara Sauce"
    loser = "Manama Pickles Maabooch Kuwaiti Red 250g"
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=1,
        reason=f"{winner} carries a cleaner, brighter finish.",
    )
    reason = result["overview"]["winner"]["reason"]
    assert reason == f"{winner} is the stronger overall pick."
    assert loser not in reason


def test_agreement_path_prose_is_untouched_end_to_end():
    """#99 clause 5, pinned across EVERY surface the reason fans out to. No
    mismatch means no payload change — this is the invariant the unconditional
    drop must not widen. Byte-identical to the pre-#99 output."""
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=1,
        gpt_winner=1,
        declaration="Product B wins on flavor",
        reason="Product B has the richer flavor.",
        tradeoff="Product A is milder.",
    )
    assert result["overview"]["winner"]["reason"] == "Product B has the richer flavor."
    assert result["overview"]["winner"]["declaration"] == "Product B wins on flavor"
    assert result["overview"]["winner"]["name"] == "Product B wins on flavor"
    assert result["overview"]["winner"]["key_tradeoff"] == "Product A is milder."
    assert result["recommendation"] == "Product B has the richer flavor."
    assert result["comparison"]["winner_reason"] == "Product B has the richer flavor."
    assert result["comparison"]["key_tradeoff"] == "Product A is milder."
    assert result["comparison"]["winner_declaration"] == "Product B wins on flavor"
    assert result["winner_index"] == 1


def test_scoring_winner_none_leaves_gpt_prose_untouched():
    """Legacy fixtures / scoring-disabled mode: with no deterministic winner
    there is nothing to override, so GPT's index AND prose both stand."""
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=None,
        gpt_winner=1,
        declaration="Product B wins on flavor",
        reason="Product B has the richer flavor.",
        tradeoff="Product A is milder.",
    )
    assert result["winner_index"] == 1
    assert result["overview"]["winner"]["declaration"] == "Product B wins on flavor"
    assert result["overview"]["winner"]["reason"] == "Product B has the richer flavor."
    assert result["overview"]["winner"]["key_tradeoff"] == "Product A is milder."


# ---------------------------------------------------------------------------
# 7 — legacy fixture edge case
# ---------------------------------------------------------------------------

def test_empty_product_names_does_not_raise():
    result = _build(
        names=["Product A", "Product B"],
        scoring_winner=0,
        gpt_winner=1,
        declaration="Product B wins on flavor",
        product_names=[],
    )
    assert result["overview"]["winner"]["name"] == ""
