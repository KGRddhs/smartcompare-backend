"""Local code-review (PR #9) follow-up.

FIXED here (each reproduces through the SAME runtime selector the orchestrator runs,
each fix paired with a GUARD that it opens no new leak):
  #2 OVER-REJECT  — an oz-labelled NON-fragrance (CeraVe 8 oz == 236 ml) was
                    snapped to a luxury fragrance bottle size (250) and falsely
                    mismatched its ml-labelled listing of the SAME product.
  #4 OVER-REJECT  — makeup kept pure connective stopwords ("in"/"to"/...) as
                    identity, over-rejecting the common "<product> in <shade>" title.

INVESTIGATED, INTENTIONALLY NOT CHANGED:
  #1 (fragrance gender) — a base/men's query CAN still match a women's flanker
                    ("Versace Eros" -> "Eros Pour Femme"). A symmetric gender rule
                    fixes that narrow leak but mass-over-rejects every WOMEN's-BASE
                    fragrance ("Black Opium" -> "Black Opium For Women" is the SAME
                    product) — gender tokens cannot tell a flanker from a women's-base
                    descriptor. The asymmetry is the correct trade; the tests below
                    PIN the accepted behaviour so it is a conscious decision, not drift.
"""
import os
import pytest

from app.services.price_service import (
    _selection_match,
    _size_ml_mismatch,
    _weight_or_volume_mismatch,
)


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    """The correctness gate is ON by default in prod; pin it for these tests so a
    local `.env` / OS env that disabled it cannot silently no-op the assertions."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


# ---------------------------------------------------------------------------
# #1 — fragrance gender (INVESTIGATED; asymmetry intentionally kept). These tests
# PIN the accepted trade so the behaviour can only change by a conscious edit.
# ---------------------------------------------------------------------------
class TestFragranceGenderAsymmetryAccepted:
    def test_womens_base_descriptor_must_match(self):
        # WHY #1 is not symmetrized: Black Opium IS a women's fragrance, so a genuine
        # candidate that adds the "For Women" descriptor is the SAME product and MUST
        # match. A symmetric "reject when one side states women's" rule would pend this
        # (and every women's-base fragrance) — a far larger over-rejection than the leak.
        assert _selection_match(
            "YSL Black Opium EDP 90ml",
            "YSL Black Opium Eau de Parfum For Women 90ml",
            "fragrances", candidate_brand="YSL",
        ) is True

    def test_known_accepted_men_base_to_femme_flanker_leak(self):
        # DOCUMENTED ACCEPTED LEAK: a men's/base query still matches its women's
        # flanker because gender tokens cannot distinguish it from the women's-base
        # case above. If this ever flips to False, the symmetric rule was (re)introduced
        # and the women's-base test above will be failing too — revisit together.
        assert _selection_match(
            "Versace Eros", "Versace Eros Pour Femme", "fragrances",
            candidate_brand="Versace",
        ) is True

    # --- GUARDS: behaviours that DO hold -----------------------------------
    def test_guard_pour_homme_bestseller_still_matches_base(self):
        # The dominant genuine case: a men's "Pour Homme" query matching a genuine
        # gender-OMITTING base PDP must STILL match (men's/base tolerance preserved).
        assert _selection_match(
            "Bleu de Chanel Pour Homme", "Bleu de Chanel", "fragrances",
            candidate_brand="Chanel",
        ) is True

    def test_guard_femme_query_still_requires_femme_candidate(self):
        # Original _feminine_query_unconfirmed behaviour preserved: a femme query
        # matching a gender-omitting base candidate stays rejected.
        assert _selection_match(
            "Versace Eros Pour Femme", "Versace Eros", "fragrances",
            candidate_brand="Versace",
        ) is False

    def test_guard_same_product_no_gender_matches(self):
        assert _selection_match(
            "Versace Eros", "Versace Eros Eau de Toilette", "fragrances",
            candidate_brand="Versace",
        ) is True

    def test_guard_two_femme_match(self):
        assert _selection_match(
            "Versace Eros Pour Femme", "Versace Eros Pour Femme EDP", "fragrances",
            candidate_brand="Versace",
        ) is True


# ---------------------------------------------------------------------------
# #2 — oz→fragrance-bottle snap applied cross-category (over-rejection)
# ---------------------------------------------------------------------------
class TestOzMlCrossCategorySnap:
    def test_skincare_oz_matches_equivalent_ml(self):
        # 8 fl oz == 236.6 ml; a genuine "236 ml" listing of the SAME product must
        # match (the snap pushed 8oz -> 250 and falsely mismatched).
        assert _selection_match(
            "CeraVe Moisturizing Lotion 8 oz",
            "CeraVe Moisturizing Lotion 236 ml",
            "skincare", candidate_brand="CeraVe",
        ) is True

    def test_size_axis_oz_ml_equivalent_non_fragrance(self):
        # direct axis: 8oz vs 236ml is the SAME size for a non-fragrance.
        assert _size_ml_mismatch(
            "CeraVe Lotion 8 oz", "CeraVe Lotion 236 ml", "skincare",
        ) is False

    # --- GUARDS -------------------------------------------------------------
    def test_guard_real_size_difference_still_rejects(self):
        assert _selection_match(
            "CeraVe Moisturizing Lotion 88 ml",
            "CeraVe Moisturizing Lotion 236 ml",
            "skincare", candidate_brand="CeraVe",
        ) is False
        assert _size_ml_mismatch(
            "CeraVe Lotion 88 ml", "CeraVe Lotion 236 ml", "skincare",
        ) is True

    def test_guard_fragrance_snap_unchanged(self):
        # Fragrance path is unchanged: 3.4 oz snaps to 100 ml (match), 100 vs 50 rejects.
        assert _size_ml_mismatch("Sauvage 3.4 oz", "Sauvage 100 ml", "fragrances") is False
        assert _size_ml_mismatch("Sauvage 100 ml", "Sauvage 50 ml", "fragrances") is True


# ---------------------------------------------------------------------------
# #4 — makeup kept pure connective stopwords as identity (over-rejection)
# ---------------------------------------------------------------------------
class TestMakeupStopwordOverRejection:
    def test_makeup_in_shade_title_matches(self):
        # "<Brand> <Product> in <Shade>" is the canonical makeup title; the query
        # omits the connective "in". Must match the SAME shade.
        assert _selection_match(
            "NARS Lipstick Dolce Vita",
            "NARS Lipstick in Dolce Vita",
            "makeup", candidate_brand="NARS",
        ) is True

    # --- GUARD: a genuinely different shade must still reject ---------------
    def test_guard_different_shade_still_rejects(self):
        assert _selection_match(
            "NARS Lipstick Dolce Vita",
            "NARS Lipstick in Orgasm",
            "makeup", candidate_brand="NARS",
        ) is False


# ---------------------------------------------------------------------------
# #2b — lb->g conversion rounding over-rejection (weight axis; surfaced by the
# adversarial workflow as a preexisting bug in the same family as #2).
# ---------------------------------------------------------------------------
class TestLbToGramConversionRounding:
    def test_protein_lb_matches_equivalent_grams(self):
        # 5 lb == 2267.96 g; the genuine "2270 g" label of the SAME tub must match
        # (the exact-equality weight axis over-rejected it).
        assert _selection_match(
            "Optimum Nutrition Gold Standard Whey 5lb",
            "Optimum Nutrition Gold Standard Whey 2270g",
            "supplements", candidate_brand="Optimum Nutrition",
        ) is True

    def test_weight_axis_lb_grams_equivalent(self):
        assert _weight_or_volume_mismatch("Whey 5lb", "Whey 2270g") is False
        assert _weight_or_volume_mismatch("Whey 5lb", "Whey 2.27kg") is False

    # --- GUARDS -------------------------------------------------------------
    def test_guard_different_lb_sizes_still_reject(self):
        assert _selection_match(
            "Optimum Nutrition Gold Standard Whey 2lb",
            "Optimum Nutrition Gold Standard Whey 5lb",
            "supplements", candidate_brand="Optimum Nutrition",
        ) is False
        assert _weight_or_volume_mismatch("Whey 5lb", "Whey 2kg") is True

    def test_guard_native_grams_stay_exact(self):
        # No lb token anywhere → grams compared EXACTLY (no spurious 1% merge).
        assert _weight_or_volume_mismatch("Cream 500g", "Cream 505g") is True
        assert _weight_or_volume_mismatch("Cream 500g", "Cream 500g") is False
