"""M20 #99 (M18 PO-recorded-01) — the winner card must NAME and PRAISE the
deterministic winner, never GPT's pick.

`build_comparison_response` overrides `winner_index` with the deterministic
scoring winner but historically shipped GPT's `winner_declaration` /
`winner_reason` / `key_tradeoff` untouched, so on a disagreement the card
highlighted product A while the headline named and praised product B (recorded
M18 rows `11651c1d` / `f79c5403`). The app reads `overview.winner.name` for the
headline AND for the Share message, so the contradiction ships to other people.

This repair is UNFLAGGED: `winner_index` is ALREADY deterministic in production,
so the only rows it can touch are rows that are already self-contradictory.
Tests 5 and 6 pin the untouched paths.
"""
import pytest

from app.services.response_builder import build_comparison_response


_WINNER = "Manama Pickles Achbara Sauce"
_LOSER = "Manama Pickles Maabooch Kuwaiti Red 250g"


def _products(names=(_WINNER, _LOSER)):
    return [
        {"name": names[0], "category": "grocery",
         "price": {"amount": 1.5, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.5, "review_count": 80, "specs": {"weight": "250 g"}},
        {"name": names[1], "category": "grocery",
         "price": {"amount": 1.7, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.4, "review_count": 60, "specs": {"weight": "250 g"}},
    ]


def _scoring_result(winner_index):
    return {
        "scores": {
            "product_0": {"overall": 74.0, "breakdown": {"price_score": 74.0}},
            "product_1": {"overall": 74.0, "breakdown": {"price_score": 74.0}},
        },
        "winner_index": winner_index,
        "win_margin": 0.0,
        "is_cross_tier": False,
    }


def _comparison(gpt_winner_index, *, declaration=None, reason=None, tradeoff=None):
    names = (_WINNER, _LOSER)
    w = names[gpt_winner_index]
    return {
        "winner_index": gpt_winner_index,
        "winner_declaration": declaration if declaration is not None else f"{w} wins on flavor",
        "winner_reason": reason if reason is not None else f"{w} has the richer flavor.",
        "key_tradeoff": tradeoff if tradeoff is not None else f"{names[1 - gpt_winner_index]} is cheaper.",
    }


def _build(**kwargs):
    base = dict(
        product_data=_products(),
        category_used="grocery",
    )
    base.update(kwargs)
    return build_comparison_response(**base)


@pytest.fixture(autouse=True)
def _prose_reconcile_off(monkeypatch):
    """This file pins the UNFLAGGED repair only — the richer deterministic
    template prose lives behind ENABLE_WINNER_PROSE_RECONCILE (see
    tests/test_winner_prose_reconciliation.py)."""
    monkeypatch.delenv("ENABLE_WINNER_PROSE_RECONCILE", raising=False)
    yield


# ---------------------------------------------------------------------------
# Mismatch — every winner-facing field must track the deterministic winner
# ---------------------------------------------------------------------------

def test_mismatch_winner_name_is_deterministic_product():
    """RED at 17cb981: overview.winner.name ships GPT's winner_declaration,
    which names the LOSING product."""
    resp = _build(comparison=_comparison(1), scoring_result=_scoring_result(0))
    assert resp["overview"]["winner"]["product_index"] == 0
    assert resp["overview"]["winner"]["name"] == _WINNER


def test_mismatch_declaration_is_dropped():
    """RED at 17cb981: the declaration is GPT's sentence about the loser."""
    resp = _build(comparison=_comparison(1), scoring_result=_scoring_result(0))
    assert resp["overview"]["winner"]["declaration"] == ""


def test_mismatch_reason_never_names_the_loser():
    """RED at 17cb981: the reason (and its top-level `recommendation` alias)
    praises the loser by name."""
    resp = _build(
        comparison=_comparison(
            1, reason=f"{_LOSER} has the richer flavor."),
        scoring_result=_scoring_result(0),
    )
    reason = resp["overview"]["winner"]["reason"]
    assert "Maabooch" not in reason
    assert "Maabooch" not in resp["recommendation"]
    assert reason == f"{_WINNER} is the stronger overall pick."
    assert resp["recommendation"] == reason


def test_mismatch_bc_comparison_winner_index_is_reindexed():
    """RED at 17cb981: the BC `comparison` alias keeps GPT's stale index."""
    resp = _build(comparison=_comparison(1), scoring_result=_scoring_result(0))
    assert resp["comparison"]["winner_index"] == resp["winner_index"] == 0


def test_mismatch_key_tradeoff_never_names_the_loser():
    """RED at 17cb981: GPT's key_tradeoff is written from the INVERTED
    orientation — it frames the shipped winner as the runner-up and names the
    loser as the better pick."""
    resp = _build(
        comparison=_comparison(
            1, tradeoff=f"{_LOSER} is the better everyday pick."),
        scoring_result=_scoring_result(0),
    )
    assert "Maabooch" not in resp["overview"]["winner"]["key_tradeoff"]


# ---------------------------------------------------------------------------
# No mismatch — payload identical to today
# ---------------------------------------------------------------------------

def test_no_mismatch_overview_winner_unchanged():
    """Agreement is the common path: GPT prose ships untouched, exactly as at
    17cb981 (declaration text is still the `name`)."""
    resp = _build(comparison=_comparison(0), scoring_result=_scoring_result(0))
    assert resp["overview"]["winner"] == {
        "product_index": 0,
        "name": f"{_WINNER} wins on flavor",
        "declaration": f"{_WINNER} wins on flavor",
        "reason": f"{_WINNER} has the richer flavor.",
        "key_tradeoff": f"{_LOSER} is cheaper.",
        "margin": 0.0,
    }
    assert resp["comparison"]["winner_index"] == 0


def test_shared_brand_token_reason_survives():
    """Guard against token-matching over-scrub: both products share the brand
    tokens "Manama Pickles", so only a FULL-name containment check is safe."""
    resp = _build(
        comparison=_comparison(
            1, reason=f"{_WINNER} has the richer flavor."),
        scoring_result=_scoring_result(0),
    )
    assert resp["overview"]["winner"]["reason"] == f"{_WINNER} has the richer flavor."


def test_empty_product_names_does_not_raise():
    """Legacy fixtures pass product_names=[]; the loser lookup must not
    IndexError and the name degrades to ""."""
    resp = _build(
        comparison=_comparison(1),
        scoring_result=_scoring_result(0),
        product_names=[],
    )
    assert resp["overview"]["winner"]["name"] == ""
    assert resp["winner_index"] == 0


def test_scoring_winner_none_leaves_gpt_prose_untouched():
    """Legacy / scoring-disabled mode (no deterministic winner): GPT's index and
    prose both stand, exactly as at 17cb981."""
    resp = _build(
        comparison=_comparison(1),
        scoring_result={"scores": {}},
    )
    assert resp["winner_index"] == 1
    assert resp["overview"]["winner"]["declaration"] == f"{_LOSER} wins on flavor"
    assert resp["overview"]["winner"]["reason"] == f"{_LOSER} has the richer flavor."
