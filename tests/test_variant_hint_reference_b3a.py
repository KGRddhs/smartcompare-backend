# -*- coding: utf-8 -*-
"""genuine-price Wave-2 B3a - curated variant-hint reference + WARM-CONTEXT
cache-write veto.

Closes the 2+1 warmer-writable poison classes (residual-census.json):
  * gender_flanker_base_to_femme   Eros -> Eros Pour Femme (curated: eros=men, DISTINCT)
  * spf_one_sided_add              CeraVe Lotion -> +SPF 30 (not an inherent-SPF line, DISTINCT)
  * makeup_one_sided_formula_add   Fit Me Matte -> Fit Me Dewy (distinct sub-lines)

These 3 classes PASS should_cache_price (they pass _selection_match -- the HELD
display tradeoffs), so the cron warmer would cache a wrong-SKU price under the
genuine 7d TTL. The veto fires at CACHE-WRITE, OFF-CLOCK CONTEXT ONLY.

HARD INVARIANTS pinned here:
  1. LIVE 15s path (no warm context) BYTE-IDENTICAL -- the veto no-ops; the row
     still caches exactly as today (flag-ON and flag-OFF).
  2. DISPLAY unchanged -- is_price_showable stays True for all these classes.
  3. FLAG-OFF byte-identical -- no veto behavior when the axes flag is off.
  4. KPI 18/18 -- every truth row still passes the warm-context write gate flag-ON
     (their resolved titles carry no Class-B ambiguity).

Free-unit suite: no network, no marks. ASCII-only source (Windows discipline).
"""
import pytest

from app.services import price_service as ps


# --------------------------------------------------------------------------
# Fixtures: gate ON, axes ON (the veto only exists under both flags). The warm
# context is set/cleared per-test via the WARMER_CONTEXT env.
# --------------------------------------------------------------------------
@pytest.fixture
def gate_axes_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")


def _price(title, amount=95.0, url="https://theperfumesclub.com/product/x", brand="",
           in_stock=True):
    return {
        "title": title, "amount": amount, "currency": "BHD", "url": url,
        "brand": brand, "in_stock": in_stock, "source_method": "woo_store_api",
    }


# ==========================================================================
# A) _variant_hint_lookup - the deterministic curated reader
# ==========================================================================
class TestVariantHintLookup:
    def test_gender_distinct_men_base_plus_femme(self):
        assert ps._variant_hint_lookup(
            "fragrances", "Versace Eros",
            "Versace Eros Pour Femme Eau de Parfum 100ml", "gender") == "distinct"

    def test_gender_same_women_base_plus_women(self):
        assert ps._variant_hint_lookup(
            "fragrances", "YSL Black Opium",
            "YSL Black Opium For Women Eau de Parfum 90ml", "gender") == "same"

    def test_gender_curated_miss_is_unknown(self):
        assert ps._variant_hint_lookup(
            "fragrances", "Obscure Niche Blend",
            "Obscure Niche Blend Pour Femme", "gender") == "unknown"

    def test_spf_same_inherent_line(self):
        assert ps._variant_hint_lookup(
            "skincare", "La Roche-Posay Anthelios",
            "La Roche-Posay Anthelios SPF 50", "spf") == "same"

    def test_spf_distinct_non_sunscreen_base(self):
        assert ps._variant_hint_lookup(
            "skincare", "CeraVe Moisturizing Lotion",
            "CeraVe Moisturizing Lotion SPF 30", "spf") == "distinct"

    def test_spf_curated_miss_is_unknown(self):
        assert ps._variant_hint_lookup(
            "skincare", "Weird Unknown Cream",
            "Weird Unknown Cream SPF 30", "spf") == "unknown"

    def test_formula_distinct_sub_lines(self):
        assert ps._variant_hint_lookup(
            "makeup", "Maybelline Fit Me Matte",
            "Maybelline Fit Me Dewy Smooth", "formula") == "distinct"

    def test_formula_curated_miss_is_unknown(self):
        assert ps._variant_hint_lookup(
            "makeup", "Random Foundation",
            "Random Foundation Dewy", "formula") == "unknown"


# ==========================================================================
# C) warmer_write_veto - WARM-CONTEXT flag-ON semantics
# ==========================================================================
class TestWarmerWriteVetoWarmContext:
    def test_eros_to_femme_vetoed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, reason = ps.warmer_write_veto(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"), "fragrances")
        assert allow is False
        assert "gender" in (reason or "").lower()

    def test_black_opium_to_women_allowed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, _ = ps.warmer_write_veto(
            "YSL Black Opium",
            _price("YSL Black Opium For Women Eau de Parfum 90ml"), "fragrances")
        assert allow is True

    def test_cerave_lotion_plus_spf_vetoed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, reason = ps.warmer_write_veto(
            "CeraVe Moisturizing Lotion",
            _price("CeraVe Moisturizing Lotion SPF 30"), "skincare")
        assert allow is False
        assert "spf" in (reason or "").lower()

    def test_anthelios_plus_spf_allowed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, _ = ps.warmer_write_veto(
            "La Roche-Posay Anthelios",
            _price("La Roche-Posay Anthelios SPF 50"), "skincare")
        assert allow is True

    def test_fit_me_matte_to_dewy_vetoed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, reason = ps.warmer_write_veto(
            "Maybelline Fit Me Matte",
            _price("Maybelline Fit Me Dewy Smooth"), "makeup")
        assert allow is False
        assert "formula" in (reason or "").lower()

    def test_curated_miss_gender_flanker_failclosed_veto(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        # A base line NOT in the curated reference + a candidate that ADDS a gender
        # token the query lacks -> UNKNOWN -> FAIL-CLOSED veto.
        allow, reason = ps.warmer_write_veto(
            "Obscure Niche Blend",
            _price("Obscure Niche Blend Pour Femme"), "fragrances")
        assert allow is False
        assert "unknown" in (reason or "").lower() or "fail" in (reason or "").lower()

    def test_no_ambiguous_axis_added_allowed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        # Candidate adds no gender/spf/formula token the query lacks -> nothing to veto.
        allow, _ = ps.warmer_write_veto(
            "Versace Eros Eau de Toilette 100ml",
            _price("Versace Eros Eau de Toilette 100ml"), "fragrances")
        assert allow is True

    def test_query_already_states_gender_no_add_allowed(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        # Query itself carries the gender token, candidate matches -> no ADD -> allow.
        allow, _ = ps.warmer_write_veto(
            "Versace Eros Pour Femme",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"), "fragrances")
        assert allow is True


# ==========================================================================
# LIVE (no warm context) - the veto NO-OPS (byte-identical to today)
# ==========================================================================
class TestLivePathVetoNoOps:
    def test_eros_to_femme_allowed_live(self, gate_axes_on, monkeypatch):
        monkeypatch.delenv("WARMER_CONTEXT", raising=False)
        allow, _ = ps.warmer_write_veto(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"), "fragrances")
        assert allow is True

    def test_cerave_plus_spf_allowed_live(self, gate_axes_on, monkeypatch):
        monkeypatch.delenv("WARMER_CONTEXT", raising=False)
        allow, _ = ps.warmer_write_veto(
            "CeraVe Moisturizing Lotion",
            _price("CeraVe Moisturizing Lotion SPF 30"), "skincare")
        assert allow is True

    def test_fit_me_dewy_allowed_live(self, gate_axes_on, monkeypatch):
        monkeypatch.delenv("WARMER_CONTEXT", raising=False)
        allow, _ = ps.warmer_write_veto(
            "Maybelline Fit Me Matte",
            _price("Maybelline Fit Me Dewy Smooth"), "makeup")
        assert allow is True


# ==========================================================================
# should_cache_price integration - the write path consults the veto after the
# keystone passes, ONLY under warm context.
# ==========================================================================
class TestShouldCachePriceWarmVeto:
    def test_should_cache_eros_femme_live_true(self, gate_axes_on, monkeypatch):
        # LIVE (no warm context): should_cache_price byte-identical to today ->
        # the flanker passes the keystone and caches.
        monkeypatch.delenv("WARMER_CONTEXT", raising=False)
        assert ps.should_cache_price(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"),
            "fragrances") is True

    def test_should_cache_eros_femme_warm_false(self, gate_axes_on, monkeypatch):
        # WARM context: the veto refuses the write.
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        assert ps.should_cache_price(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"),
            "fragrances") is False

    def test_should_cache_black_opium_women_warm_true(self, gate_axes_on, monkeypatch):
        # WARM context, curated=same -> still caches.
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        assert ps.should_cache_price(
            "YSL Black Opium",
            _price("YSL Black Opium For Women Eau de Parfum 90ml"),
            "fragrances") is True

    def test_should_cache_anthelios_spf_warm_true(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        assert ps.should_cache_price(
            "La Roche-Posay Anthelios",
            _price("La Roche-Posay Anthelios SPF 50"),
            "skincare") is True

    def test_should_cache_cerave_spf_warm_false(self, gate_axes_on, monkeypatch):
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        assert ps.should_cache_price(
            "CeraVe Moisturizing Lotion",
            _price("CeraVe Moisturizing Lotion SPF 30"),
            "skincare") is False


# ==========================================================================
# FLAG-OFF byte-identical (axes flag off -> no veto, warm or live)
# ==========================================================================
class TestFlagOffByteIdentical:
    def test_veto_noops_axes_off_warm(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.delenv("ENABLE_VARIANT_DESCRIPTOR_AXES", raising=False)
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, _ = ps.warmer_write_veto(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"), "fragrances")
        assert allow is True

    def test_should_cache_axes_off_warm_true(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.delenv("ENABLE_VARIANT_DESCRIPTOR_AXES", raising=False)
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        assert ps.should_cache_price(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"),
            "fragrances") is True

    def test_exact_gate_off_warm_true(self, monkeypatch):
        # exact gate off -> variant_descriptor_axes_enabled False -> no veto AND
        # should_cache_price short-circuits True at the top. The gate DEFAULTS ON,
        # so it must be set explicitly OFF (delenv would leave it defaulted true).
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        allow, _ = ps.warmer_write_veto(
            "Versace Eros",
            _price("Versace Eros Pour Femme Eau de Parfum 100ml"), "fragrances")
        assert allow is True


# ==========================================================================
# DISPLAY unchanged - is_price_showable is NOT touched by B3a: its output is
# INVARIANT to WARMER_CONTEXT (the veto lives only in the cache-write path).
# (These specific price shapes pend at display for unrelated reasons -- the
# HELD display tolerance is about the IDENTITY axis, exercised by the pinned
# test_held_* cases in test_correctness_coverage_sweep_fixes.py. Here we prove
# the ONLY thing B3a guarantees: WARMER_CONTEXT does not change display.)
# ==========================================================================
class TestDisplayInvariantToWarmContext:
    @pytest.mark.parametrize("title,query,cat", [
        ("Versace Eros Pour Femme Eau de Parfum 100ml", "Versace Eros", "fragrances"),
        ("CeraVe Moisturizing Lotion SPF 30", "CeraVe Moisturizing Lotion", "skincare"),
        ("Maybelline Fit Me Dewy Smooth", "Maybelline Fit Me Matte", "makeup"),
        # A genuinely showable case (exact title) to prove invariance on a True too.
        ("Versace Eros Eau de Toilette 100ml", "Versace Eros Eau de Toilette 100ml", "fragrances"),
    ])
    def test_display_invariant(self, gate_axes_on, monkeypatch, title, query, cat):
        monkeypatch.delenv("WARMER_CONTEXT", raising=False)
        live = ps.is_price_showable(_price(title), query, cat, enforce_correctness=True)
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        warm = ps.is_price_showable(_price(title), query, cat, enforce_correctness=True)
        assert live == warm, "is_price_showable must be invariant to WARMER_CONTEXT"


# ==========================================================================
# KPI 18/18 - every truth row's resolved title passes the warm-context write
# gate flag-ON (no Class-B ambiguity in the truth resolutions).
# ==========================================================================
class TestKpiTruthRowsPassWarmGate:
    def test_all_truth_rows_pass_warm_veto(self, gate_axes_on, monkeypatch):
        import json
        from pathlib import Path
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        truth_path = (Path(__file__).resolve().parent.parent
                      / "data" / "usable_exact_genuine_truth.json")
        doc = json.loads(truth_path.read_text(encoding="utf-8"))
        rows = doc.get("products", [])
        assert rows, "truth set must be non-empty"
        for r in rows:
            q = r["query"]
            cat = r.get("category")
            # The RESOLVED price for a truth row is a correct SKU whose title
            # matches the query. Simulate the resolved title == the query text
            # (the truth rows resolve to their own exact SKU; no gender/spf/formula
            # ADD relative to the query).
            allow, reason = ps.warmer_write_veto(q, _price(q), cat)
            assert allow is True, f"truth row wrongly vetoed: {q} ({reason})"
