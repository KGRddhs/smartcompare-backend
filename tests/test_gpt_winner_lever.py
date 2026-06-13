"""S3 intervention #2 — GPT-qualitative-winner lever (FLAG-GATED default OFF).

Mechanism: the deterministic spec-scorer has a CAPABILITY CEILING — it ranks
numeric spec fields + cheapness, but gold rewards qualitative quality (camera,
ecosystem, heritage, justified premium) the numbers can't express (probe-pinned).
The GPT verdict CAN see those, but today build_comparison_response FORCES the
deterministic winner (the H1 fix) and the verdict prompt is told "do NOT
contradict the scoring data" — so the qualitative signal is suppressed.

#2 lets the GPT verdict emit an INDEPENDENT winner (judged purely on the product
facts, NOT the deterministic scores) with a self-reported `grounded` flag and a
cited basis. When ENABLE_GPT_WINNER is ON, build_comparison_response uses the GPT
independent winner ONLY IF it is GROUNDED (no free guessing — the no-estimation
guardrail) and valid; otherwise the deterministic winner stands (current
behavior). Default OFF => byte-identical to today.

ADOPTION GATE (smoke20→full-200, not in this file): flip ON in prod ONLY IF
winner accuracy UP AND factual_pass >= .94 AND no axis regresses.
"""
import pytest

from app.services import response_builder
from app.services.response_builder import build_comparison_response


def _products():
    return [
        {"name": "iPhone 15", "category": "electronics",
         "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.7, "review_count": 1200,
         "specs": {"ram": "6 GB", "storage": "128 GB"}},
        {"name": "Galaxy S24", "category": "electronics",
         "price": {"amount": 280, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.6, "review_count": 1500,
         "specs": {"ram": "8 GB", "storage": "128 GB"}},
    ]


def _scoring_result(winner_index):
    return {
        "scores": {
            "product_0": {"overall": 60.0, "breakdown": {"performance_score": 60.0}},
            "product_1": {"overall": 80.0, "breakdown": {"performance_score": 80.0}},
        },
        "winner_index": winner_index,
        "win_margin": 20.0,
        "is_cross_tier": False,
    }


def _comparison(winner_index=1, *, indep=None, grounded=None, basis=None):
    c = {"winner_index": winner_index, "winner_declaration": "x",
         "winner_reason": "y", "key_tradeoff": "z"}
    if indep is not None:
        c["independent_winner_index"] = indep
    if grounded is not None:
        c["independent_winner_grounded"] = grounded
    if basis is not None:
        c["independent_winner_basis"] = basis
    return c


@pytest.fixture
def gpt_winner_on(monkeypatch):
    monkeypatch.setenv("ENABLE_GPT_WINNER", "true")
    yield


@pytest.fixture
def gpt_winner_off(monkeypatch):
    monkeypatch.delenv("ENABLE_GPT_WINNER", raising=False)
    yield


# ---------------------------------------------------------------------------
# Default OFF — deterministic winner stands (current behavior)
# ---------------------------------------------------------------------------

def test_flag_off_uses_deterministic_winner(gpt_winner_off):
    """Flag OFF: deterministic winner (1) stands even if GPT independently
    picked 0 — byte-identical to today's H1 behavior."""
    resp = build_comparison_response(
        product_data=_products(),
        comparison=_comparison(winner_index=1, indep=0, grounded=True, basis="camera"),
        scoring_result=_scoring_result(1),
        category_used="electronics",
    )
    assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1


# ---------------------------------------------------------------------------
# Flag ON — GPT independent winner used only when GROUNDED
# ---------------------------------------------------------------------------

def test_flag_on_grounded_gpt_winner_does_not_override(gpt_winner_on):
    """S3 L3 v2 (e) — LOG-ONLY. Flag ON + a GROUNDED GPT independent winner that
    DISAGREES is LOGGED for S3.1 but must NOT override — the shipped winner stays
    the genuine deterministic argmax (no consistency trap)."""
    import logging
    resp = build_comparison_response(
        product_data=_products(),
        comparison=_comparison(winner_index=1, indep=0, grounded=True,
                               basis="iPhone camera + iOS ecosystem"),
        scoring_result=_scoring_result(1),
        category_used="electronics",
    )
    assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1, (
        "v2: a grounded GPT disagreement is logged, NOT an override — deterministic stands"
    )


def test_flag_on_grounded_disagreement_is_logged(gpt_winner_on, caplog):
    """The grounded disagreement emits a GPT_WINNER_DISAGREES log (the S3.1
    cross-check signal)."""
    import logging
    with caplog.at_level(logging.INFO):
        build_comparison_response(
            product_data=_products(),
            comparison=_comparison(winner_index=1, indep=0, grounded=True, basis="camera"),
            scoring_result=_scoring_result(1),
            category_used="electronics",
        )
    assert any("GPT_WINNER_DISAGREES" in r.message for r in caplog.records), (
        "a grounded disagreement must be logged for S3.1 investigation"
    )


def test_flag_on_ungrounded_gpt_winner_ignored(gpt_winner_on):
    """Flag ON but GPT self-reports NOT grounded (it was guessing) → the
    deterministic winner stands. This is the no-estimation guardrail."""
    resp = build_comparison_response(
        product_data=_products(),
        comparison=_comparison(winner_index=1, indep=0, grounded=False,
                               basis="gut feeling"),
        scoring_result=_scoring_result(1),
        category_used="electronics",
    )
    assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1, (
        "an ungrounded (guessed) GPT winner must NOT override — no-estimation guardrail"
    )


def test_flag_on_missing_independent_winner_falls_back(gpt_winner_on):
    """Flag ON but the verdict didn't emit an independent winner (older prompt /
    parse miss) → deterministic stands."""
    resp = build_comparison_response(
        product_data=_products(),
        comparison=_comparison(winner_index=1),  # no independent_* keys
        scoring_result=_scoring_result(1),
        category_used="electronics",
    )
    assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1


def test_flag_on_invalid_independent_index_ignored(gpt_winner_on):
    """A malformed independent_winner_index (out of range / non-int) is ignored;
    deterministic stands. Defensive — never crash, never trust garbage."""
    for bad in (2, -1, None, "0", 1.5):
        resp = build_comparison_response(
            product_data=_products(),
            comparison=_comparison(winner_index=1, indep=bad, grounded=True, basis="x"),
            scoring_result=_scoring_result(1),
            category_used="electronics",
        )
        assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1, (
            f"invalid independent index {bad!r} must be ignored"
        )


def test_flag_on_grounded_but_agrees_is_noop(gpt_winner_on):
    """Flag ON + grounded GPT winner that AGREES with deterministic → winner
    unchanged (no spurious flip, no crash)."""
    resp = build_comparison_response(
        product_data=_products(),
        comparison=_comparison(winner_index=1, indep=1, grounded=True, basis="specs"),
        scoring_result=_scoring_result(1),
        category_used="electronics",
    )
    assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1


# ---------------------------------------------------------------------------
# Producer side — flag-gated prompt augmentation
# ---------------------------------------------------------------------------

def test_prompt_block_present_only_when_flag_on(monkeypatch):
    """The independent-winner instruction block is added to the verdict prompt
    ONLY when the flag is on — flag-off keeps the prompt byte-identical."""
    from app.services import extraction_service
    block = extraction_service._build_independent_winner_block()
    assert "independent_winner_index" in block
    assert "independent_winner_grounded" in block
    # no-estimation guardrail language present
    assert "grounded" in block.lower() and "guess" in block.lower()

    monkeypatch.setenv("ENABLE_GPT_WINNER", "true")
    assert extraction_service._gpt_winner_lever_enabled() is True
    monkeypatch.delenv("ENABLE_GPT_WINNER", raising=False)
    assert extraction_service._gpt_winner_lever_enabled() is False
