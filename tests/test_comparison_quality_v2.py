"""M21 weird-label unit (M18 findings PO-verdict-text-09 + PO-prompts-02).

Flag: ENABLE_COMPARISON_QUALITY_V2 (default OFF, read per call).

PO-verdict-text-09 — Rule 2 in the comparison-quality classifier returned
"weird" whenever post-fallback spec coverage was under 50%, contradicting its
own docstring ("'weird' must reflect a genuinely suspect pairing, never just
sparse early-pipeline data") and making "weird" the modal label on real
traffic (14 of 15 recorded rows). Under the flag, that gap returns the honest
sparse-data label "weak"; "weird" is reserved for the structural triggers
(cross-category, 10x price spread).

PO-prompts-02 — the verdict stack demanded decisiveness with NO evidence
condition and never wired the computed quality into the prompt
(generate_comparison hardcoded comparison_quality="normal"). Under the flag,
the orchestrator feeds detect_comparison_quality(post_fallback=True) into
generate_comparison; "weak" injects a thin-evidence hedging clause, and the
self-critique regen loop stops treating an honest hedge as a defect
(hedging_score is exempt from the regen trigger on weak/weird data).

Flag OFF must be byte-identical to the legacy behaviour — pinned below.
"""
import asyncio
import inspect
import json
from unittest.mock import AsyncMock, patch

import pytest

import app.services.structured_comparison_service as scs
import app.services.extraction_service as es
import app.services.verdict_critique_service as vcs


def _product(name, category="fragrances", price=100.0, specs=None):
    return {
        "name": name,
        "category_used": category,
        "price": {"amount": price, "currency": "BHD"},
        "specs": specs if specs is not None else {},
    }


FULL_SPECS = {f"f{i}": f"v{i}" for i in range(8)}  # >= expected for any category


# ---------------------------------------------------------------------------
# Classifier: sparse post-fallback data -> "weak" under the flag
# ---------------------------------------------------------------------------

class TestDetectComparisonQualityV2:
    def test_v2_sparse_specs_post_fallback_is_weak_not_weird(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        products = [
            _product("TOM FORD Noir", specs={}),
            _product("TOM FORD Noir Extreme", specs={}),
        ]
        assert scs.detect_comparison_quality(products, post_fallback=True) == "weak"

    def test_flag_off_preserves_legacy_weird_on_sparse_specs(self, monkeypatch):
        monkeypatch.delenv("ENABLE_COMPARISON_QUALITY_V2", raising=False)
        products = [
            _product("TOM FORD Noir", specs={}),
            _product("TOM FORD Noir Extreme", specs={}),
        ]
        assert scs.detect_comparison_quality(products, post_fallback=True) == "weird"

    def test_v2_cross_category_still_weird(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        products = [
            _product("iPhone 16", category="electronics", specs=FULL_SPECS),
            _product("Sauvage EDP", category="fragrances", specs=FULL_SPECS),
        ]
        assert scs.detect_comparison_quality(products, post_fallback=True) == "weird"

    def test_v2_10x_price_spread_still_weird(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        products = [
            _product("Cheap Pickles", category="grocery", price=1.0, specs=FULL_SPECS),
            _product("Fancy Pickles", category="grocery", price=15.0, specs=FULL_SPECS),
        ]
        assert scs.detect_comparison_quality(products, post_fallback=True) == "weird"

    def test_v2_full_specs_same_category_normal(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        products = [
            _product("A", specs=FULL_SPECS),
            _product("B", specs=FULL_SPECS),
        ]
        assert scs.detect_comparison_quality(products, post_fallback=True) == "normal"


class TestClassifyComparisonQualityV2:
    """Explicit-args classifier (test-bundle-c contract) mirrors the fix."""

    def test_v2_sparse_coverage_is_weak(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        out = scs._classify_comparison_quality(
            cat_a="fragrances", cat_b="fragrances",
            spec_coverage_a=0.2, spec_coverage_b=0.9,
            price_a=50.0, price_b=60.0,
        )
        assert out == "weak"

    def test_flag_off_sparse_coverage_stays_weird(self, monkeypatch):
        monkeypatch.delenv("ENABLE_COMPARISON_QUALITY_V2", raising=False)
        out = scs._classify_comparison_quality(
            cat_a="fragrances", cat_b="fragrances",
            spec_coverage_a=0.2, spec_coverage_b=0.9,
            price_a=50.0, price_b=60.0,
        )
        assert out == "weird"

    def test_v2_structural_triggers_still_weird(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        assert scs._classify_comparison_quality(
            cat_a="electronics", cat_b="fragrances",
            spec_coverage_a=1.0, spec_coverage_b=1.0,
            price_a=50.0, price_b=60.0,
        ) == "weird"
        assert scs._classify_comparison_quality(
            cat_a="grocery", cat_b="grocery",
            spec_coverage_a=1.0, spec_coverage_b=1.0,
            price_a=1.0, price_b=25.0,
        ) == "weird"


# ---------------------------------------------------------------------------
# verdict_comparison_quality — the signal the orchestrator feeds the prompt
# ---------------------------------------------------------------------------

class TestVerdictComparisonQuality:
    def test_flag_off_returns_normal_always(self, monkeypatch):
        monkeypatch.delenv("ENABLE_COMPARISON_QUALITY_V2", raising=False)
        products = [_product("A", specs={}), _product("B", specs={})]
        assert scs.verdict_comparison_quality(products) == "normal"

    def test_flag_on_returns_post_fallback_quality(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        sparse = [_product("A", specs={}), _product("B", specs={})]
        assert scs.verdict_comparison_quality(sparse) == "weak"
        cross = [
            _product("A", category="electronics", specs=FULL_SPECS),
            _product("B", category="fragrances", specs=FULL_SPECS),
        ]
        assert scs.verdict_comparison_quality(cross) == "weird"

    def test_never_raises_on_garbage(self, monkeypatch):
        monkeypatch.setenv("ENABLE_COMPARISON_QUALITY_V2", "true")
        assert scs.verdict_comparison_quality(None) == "normal"
        assert scs.verdict_comparison_quality([{"specs": "not-a-dict"}]) == "normal"

    def test_orchestrator_paths_wire_the_signal(self):
        """Both verdict call paths must compute the signal (not hardcode
        'normal'): pin by source so the wiring cannot silently regress."""
        # The sync body lives in _compare_from_text_impl (compare_from_text is
        # the L2.7 outer-cap wrapper).
        sync_src = inspect.getsource(
            scs.StructuredComparisonService._compare_from_text_impl
        )
        stream_src = inspect.getsource(
            scs.StructuredComparisonService.compare_from_text_streaming
        )
        assert "verdict_comparison_quality" in sync_src
        assert "verdict_comparison_quality" in stream_src


# ---------------------------------------------------------------------------
# Verdict prompt: weak injects the thin-evidence hedging clause
# ---------------------------------------------------------------------------

class TestWeakVerdictPrompt:
    def test_weak_injects_thin_evidence_clause(self):
        prompt = es.build_verdict_prompt(
            products=[_product("A"), _product("B")],
            comparison_quality="weak",
        )
        assert "THIN-EVIDENCE CONTEXT" in prompt
        assert "hedg" in prompt.lower()  # explicit permission to hedge honestly

    def test_normal_has_no_thin_evidence_clause(self):
        prompt = es.build_verdict_prompt(
            products=[_product("A"), _product("B")],
            comparison_quality="normal",
        )
        assert "THIN-EVIDENCE CONTEXT" not in prompt

    def test_weird_keeps_weird_clause_without_weak_clause(self):
        prompt = es.build_verdict_prompt(
            products=[_product("A"), _product("B")],
            comparison_quality="weird",
        )
        assert "WEIRD-COMPARISON CONTEXT" in prompt
        assert "THIN-EVIDENCE CONTEXT" not in prompt

    def test_generate_comparison_forwards_quality(self):
        """generate_comparison must pass its comparison_quality through to
        build_verdict_prompt instead of hardcoding 'normal'."""
        captured = {}
        real_build = es.build_verdict_prompt

        def _capture(*args, **kwargs):
            captured.update(kwargs)
            return real_build(*args, **kwargs)

        stub_client = AsyncMock()
        stub_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("no paid calls in tests")
        )
        with patch.object(es, "build_verdict_prompt", side_effect=_capture), \
             patch.object(es, "get_client", return_value=stub_client):
            result = asyncio.run(
                es.generate_comparison(
                    _product("A"), _product("B"), "bahrain",
                    comparison_quality="weak",
                )
            )
        assert captured.get("comparison_quality") == "weak"
        # generate_comparison never raises — error sentinel comes back.
        assert isinstance(result, tuple) or isinstance(result, dict)


# ---------------------------------------------------------------------------
# Self-critique: an honest hedge on thin data is not a regen trigger
# ---------------------------------------------------------------------------

def _critique(hedging=10, bias=10):
    scores = {
        "bias_score": bias,
        "vagueness_score": 10,
        "hedging_score": hedging,
        "missing_citation_score": 10,
        "pain_workflow_align_score": 10,
    }
    low = [a for a in vcs.CRITIQUE_AXES if scores[a] < vcs.CRITIQUE_THRESHOLD]
    return vcs.CritiqueResult(
        axis_scores=scores,
        needs_regen=bool(low),
        low_axes=low,
        regen_reason="; ".join(low) if low else None,
        critic_model="gpt-4o-mini",
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )


class TestCritiqueHedgingExemption:
    def _run(self, critique, comparison_quality):
        regenerate = AsyncMock(return_value={"winner_reason": "regen", "winner_index": 0})
        with patch.object(vcs, "is_self_critique_enabled", return_value=True), \
             patch.object(vcs, "critique_verdict", AsyncMock(return_value=critique)):
            outcome = asyncio.run(
                vcs.critique_and_maybe_regenerate(
                    comparison={"winner_reason": "orig", "winner_index": 0},
                    product_names=["A", "B"],
                    regenerate=regenerate,
                    comparison_quality=comparison_quality,
                )
            )
        return outcome, regenerate

    def test_low_hedging_on_weak_data_does_not_regen(self):
        outcome, regenerate = self._run(_critique(hedging=3), "weak")
        assert outcome.regenerated is False
        regenerate.assert_not_awaited()
        # The critique itself is preserved for persistence/observability.
        assert outcome.critique is not None
        assert outcome.critique.axis_scores["hedging_score"] == 3

    def test_low_hedging_on_normal_data_still_regens(self):
        outcome, regenerate = self._run(_critique(hedging=3), "normal")
        assert outcome.regenerated is True
        regenerate.assert_awaited_once()

    def test_low_bias_on_weak_data_still_regens(self):
        outcome, regenerate = self._run(_critique(hedging=10, bias=2), "weak")
        assert outcome.regenerated is True
        regenerate.assert_awaited_once()
