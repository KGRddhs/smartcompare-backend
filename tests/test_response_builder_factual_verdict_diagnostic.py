"""Bundle C § 1b — diagnostic logging hook for missing factual_verdict.

Per design § 1b + plan A.2.2: when response_builder._build_scoring_v2()
emits scoring_v2 without a populated factual_verdict (line1 + line2),
log a FACTUAL_VERDICT_DIAGNOSTIC marker so post-deploy probes confirm
whether the builder is genuinely missing vs gated by a flag.

Flag-gated on DEBUG_STAGE_TIMINGS=true per A.10.1 cleanup invariant —
zero prod overhead with flag off.
"""
import logging
import pytest

from app.services import response_builder


def _make_scoring_result(overall_a: int = 75, overall_b: int = 80) -> dict:
    return {
        "scores": {
            "product_0": {"overall": overall_a, "breakdown": {}, "tier": "mid"},
            "product_1": {"overall": overall_b, "breakdown": {}, "tier": "mid"},
        },
    }


def _make_products() -> list:
    # Note: scoring_service dim builders expect rating as a top-level float
    # (not the nested {score, count} dict from product.rating). This matches
    # the legacy `product_data` shape passed into build_dimensions_v2.
    return [
        {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": 4.5},
        {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": 4.4},
    ]


def test_logs_when_factual_verdict_none(caplog, monkeypatch):
    """When _build_scoring_v2 emits without populated factual_verdict
    (current state per § 1b — builder missing), the diagnostic fires."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(response_builder, "_FACTUAL_VERDICT_DIAG_FLAG", None, raising=False)

    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        scoring_v2 = response_builder._build_scoring_v2(
            product_data=_make_products(),
            scoring_result=_make_scoring_result(),
            category="electronics",
            winner_index=1,
        )

    assert "FACTUAL_VERDICT_DIAGNOSTIC" in caplog.text, (
        "Expected FACTUAL_VERDICT_DIAGNOSTIC log marker when factual_verdict missing/None"
    )
    # Must surface winner_index and product context for diagnosis
    assert "winner_index" in caplog.text or "winner_idx" in caplog.text


def test_no_log_when_flag_off(caplog, monkeypatch):
    """Per A.10.1 + measure-before-optimize: diagnostic MUST be flag-gated."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    monkeypatch.setattr(response_builder, "_FACTUAL_VERDICT_DIAG_FLAG", None, raising=False)

    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        response_builder._build_scoring_v2(
            product_data=_make_products(),
            scoring_result=_make_scoring_result(),
            category="electronics",
            winner_index=1,
        )

    assert "FACTUAL_VERDICT_DIAGNOSTIC" not in caplog.text


def test_no_log_when_factual_verdict_populated(caplog, monkeypatch):
    """When (in the future, post A.3.2) factual_verdict has line1+line2,
    the diagnostic must NOT fire — only fires for the missing/None case.

    We simulate the future state by monkey-patching the helper to return
    a populated factual_verdict dict — proves the diagnostic correctly
    reads the emitted dict before firing.
    """
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(response_builder, "_FACTUAL_VERDICT_DIAG_FLAG", None, raising=False)

    # Monkey-patch the future _build_factual_verdict (will exist after A.3.2).
    # Until then, we patch a private attr the diagnostic check reads from.
    monkeypatch.setattr(
        response_builder,
        "_factual_verdict_present_in_scoring_v2",
        lambda sv2: True,
        raising=False,
    )

    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        response_builder._build_scoring_v2(
            product_data=_make_products(),
            scoring_result=_make_scoring_result(),
            category="electronics",
            winner_index=1,
        )

    assert "FACTUAL_VERDICT_DIAGNOSTIC" not in caplog.text


def test_short_circuit_when_fewer_than_2_products(caplog, monkeypatch):
    """Sub-2-product path returns {} early — diagnostic must NOT fire
    (would be noise; not the real bug)."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(response_builder, "_FACTUAL_VERDICT_DIAG_FLAG", None, raising=False)

    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        result = response_builder._build_scoring_v2(
            product_data=[{"name": "lone product"}],
            scoring_result=_make_scoring_result(),
            category="electronics",
            winner_index=0,
        )

    assert result == {}
    assert "FACTUAL_VERDICT_DIAGNOSTIC" not in caplog.text
