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


def test_shared_brand_token_reason_survives():
    """The two products share a brand token; the reason names only the winner.
    Token-matching would nuke it — full-name containment must not."""
    winner = "Manama Pickles Achbara Sauce"
    loser = "Manama Pickles Maabooch Kuwaiti Red 250g"
    reason = f"{winner} carries a cleaner, brighter finish."
    result = _build(
        names=[winner, loser],
        scoring_winner=0,
        gpt_winner=1,
        reason=reason,
    )
    assert result["overview"]["winner"]["reason"] == reason
    assert result["recommendation"] == reason


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
