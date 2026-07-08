"""Fragrance gender-flanker leak — "Gents" vs "Ladies" (pronoun-decoupled, PR#32 extension).

GROUND TRUTH (reproduced through the SAME runtime selector the orchestrator runs,
`price_service._selection_match`): a fragrance "<X> Gents" vs "<X> Ladies" WRONGLY MATCHED
(=True) — the exact class PR#32 fixed for him/her. "gents"/"ladies" sit in
`_FRAGRANCE_PADDING_TOKENS` (the subset check ignores them) but were ABSENT from BOTH the
strict `_GENDER_MEN_TOKENS`/`_GENDER_WOMEN_TOKENS` AND `_pronoun_gender_of`, so the
`_gender_mismatch` CONTRADICTION axis never fired on Gents/Ladies. Common in the local
Arabic houses (e.g. "Ajmal Aristocrat For Him/Her" also ship "... Gents/... Ladies").

THE FIX (flag-gated behind `variant_descriptor_axes_enabled()` / ENABLE_VARIANT_DESCRIPTOR_AXES,
ON in prod): extend the SEPARATE `_pronoun_gender_of` (gents->men, ladies->women) — the SAME
decoupled axis PR#32 added for him/her. It feeds ONLY the contradiction axis
(`_vd_gender_mismatch`, via `VariantDescriptor.gender_pronoun`). `_gender_of` stays STRICT,
so the femme-asymmetry (`_vd_feminine_query_unconfirmed`) and the empty-core/identity logic
are UNCHANGED. That decoupling is why Gents!=Ladies is caught WITHOUT (a) over-rejecting a
"Ladies" query vs its gender-omitting base and (b) collapsing a distinct "Woman" into "Ladies".
Flag OFF -> gender_pronoun is None -> byte-identical old behaviour (Gents vs Ladies still leaks).
"""
import pytest

from app.services import price_service
from app.services.price_service import _selection_match


def _clear_descriptor_cache():
    price_service._extract_variant_descriptor_cached.cache_clear()


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "1")
    _clear_descriptor_cache()
    yield
    _clear_descriptor_cache()


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.delenv("ENABLE_VARIANT_DESCRIPTOR_AXES", raising=False)
    _clear_descriptor_cache()
    yield
    _clear_descriptor_cache()


# ---------------------------------------------------------------------------
# FLAG ON — the fix is active
# ---------------------------------------------------------------------------
class TestFlagOnContradiction:
    def test_gents_vs_ladies_rejected(self, flag_on):
        # THE leak, now fixed: opposite-gender flankers contradict -> reject.
        assert _selection_match(
            "Ajmal Aristocrat Gents", "Ajmal Aristocrat Ladies", "fragrances",
            candidate_brand="Ajmal",
        ) is False

    def test_ladies_vs_gents_rejected_both_directions(self, flag_on):
        assert _selection_match(
            "Ajmal Aristocrat Ladies", "Ajmal Aristocrat Gents", "fragrances",
            candidate_brand="Ajmal",
        ) is False

    def test_gents_vs_ladies_second_brand(self, flag_on):
        assert _selection_match(
            "Burberry Gents", "Burberry Ladies", "fragrances", candidate_brand="Burberry",
        ) is False

    # Cross-vocabulary contradiction: pronoun-gender vs strict-gender still contradicts.
    def test_gents_vs_pour_femme_rejected(self, flag_on):
        assert _selection_match(
            "Armaf Club de Nuit Gents", "Armaf Club de Nuit Pour Femme", "fragrances",
            candidate_brand="Armaf",
        ) is False

    def test_ladies_vs_for_him_rejected(self, flag_on):
        # ladies(women) query vs him(men) candidate — cross pronoun contradiction.
        assert _selection_match(
            "Lattafa Yara Ladies", "Lattafa Yara For Him", "fragrances",
            candidate_brand="Lattafa",
        ) is False

    # --- DECOUPLING GUARDS: no new over-rejection, no new leak -----------------
    def test_ladies_flanker_query_vs_base_still_matches(self, flag_on):
        # DECOUPLING: a "Ladies" query must NOT be pushed into the femme-asymmetry by the
        # pronoun, so it still tolerates its gender-omitting base (no over-rejection).
        assert _selection_match(
            "Ajmal Aristocrat Ladies", "Ajmal Aristocrat", "fragrances",
            candidate_brand="Ajmal",
        ) is True

    def test_woman_query_vs_ladies_unchanged_by_pronoun(self, flag_on):
        # The STRICT femme-asymmetry already rejects a strict-women query whose candidate
        # does not strictly confirm women (same as "Woman" vs "Her" in PR#32). The pronoun
        # add must NOT change this (ladies is a pronoun-women candidate, strict None).
        assert _selection_match(
            "Burberry Woman", "Burberry Ladies", "fragrances", candidate_brand="Burberry",
        ) is False

    # --- GUARDS: one-sided gender omission must STILL match --------------------
    def test_base_vs_gents_still_matches(self, flag_on):
        assert _selection_match(
            "Ajmal Aristocrat", "Ajmal Aristocrat Gents", "fragrances",
            candidate_brand="Ajmal",
        ) is True

    # --- TOKENIZATION: a name token must NOT false-trigger the pronoun ----------
    def test_gentleman_name_not_a_gender(self, flag_on):
        # "Gentleman"/"Gentlemen" (Givenchy line NAME) fold to their own token, never 'gents'.
        assert price_service._pronoun_gender_of("Givenchy Gentleman") is None
        assert price_service._pronoun_gender_of("Givenchy Gentlemen Society") is None

    def test_gentleman_vs_gentleman_intense_still_matches(self, flag_on):
        # Regression: the fix must not make Givenchy Gentleman read as a men's pronoun that
        # spuriously contradicts anything — a base vs sub-line stays governed by other axes.
        assert price_service._pronoun_gender_of("Givenchy Gentleman Boisee") is None

    def test_gladiator_not_a_gender(self, flag_on):
        assert price_service._pronoun_gender_of("Gladiator Intense") is None

    # --- GUARDS: other categories UNCHANGED -----------------------------------
    def test_electronics_unchanged(self, flag_on):
        assert _selection_match(
            "Galaxy S24", "Galaxy S24 FE", "electronics", candidate_brand="Samsung",
        ) is False


# ---------------------------------------------------------------------------
# FLAG OFF — byte-identical pre-fix behaviour (gender_pronoun is None)
# ---------------------------------------------------------------------------
class TestFlagOffByteIdentical:
    def test_gents_vs_ladies_still_leaks_true(self, flag_off):
        assert _selection_match(
            "Ajmal Aristocrat Gents", "Ajmal Aristocrat Ladies", "fragrances",
            candidate_brand="Ajmal",
        ) is True

    def test_pronoun_gender_of_inert_flag_off(self, flag_off):
        assert price_service._pronoun_gender_of("Ajmal Aristocrat Gents") is None
        assert price_service._pronoun_gender_of("Ajmal Aristocrat Ladies") is None

    def test_ladies_query_vs_base_matches_same_as_prod(self, flag_off):
        assert _selection_match(
            "Ajmal Aristocrat Ladies", "Ajmal Aristocrat", "fragrances",
            candidate_brand="Ajmal",
        ) is True
