"""Fragrance gender-flanker CONTRADICTION fix — pronoun-decoupled him/her.

GROUND TRUTH (reproduced through the SAME runtime selector the orchestrator runs,
`price_service._selection_match`): fragrance gender flankers "Burberry Her" vs
"Burberry Him" WRONGLY MATCHED (=True) because "him"/"her" sit in
`_FRAGRANCE_PADDING_TOKENS` (subset ignores them) AND were EXCLUDED from
`_GENDER_MEN_TOKENS`/`_GENDER_WOMEN_TOKENS` — so the `_gender_mismatch` CONTRADICTION
axis never fired on Her/Him.

THE FIX (flag-gated behind `variant_descriptor_axes_enabled()` /
ENABLE_VARIANT_DESCRIPTOR_AXES, ON in prod): a SEPARATE `_pronoun_gender_of` (him→men,
her→women) feeds ONLY the contradiction axis (`_vd_gender_mismatch`, via the new
`VariantDescriptor.gender_pronoun` field). `_gender_of` stays STRICT — so the
femme-asymmetry (`_vd_feminine_query_unconfirmed`) and the empty-core/identity logic are
UNCHANGED. That decoupling is why Her≡Him is fixed WITHOUT (a) over-rejecting a "For Her"
query vs its base and (b) leaking "Woman" vs "Her". Flag OFF → gender_pronoun is None →
byte-identical old behaviour (Her vs Him still leaks True).

Env monkeypatch + LRU-cache-clear style mirrors tests/test_serper_multikey_failover.py.
"""
import pytest

from app.services import price_service
from app.services.price_service import _selection_match


def _clear_descriptor_cache():
    price_service._extract_variant_descriptor_cached.cache_clear()


@pytest.fixture
def flag_on(monkeypatch):
    """Prod configuration: exact gate + variant-descriptor axes both ON."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "1")
    _clear_descriptor_cache()
    yield
    _clear_descriptor_cache()


@pytest.fixture
def flag_off(monkeypatch):
    """Axes flag UNSET (default) — the pre-fix behaviour (gender_pronoun is None)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.delenv("ENABLE_VARIANT_DESCRIPTOR_AXES", raising=False)
    _clear_descriptor_cache()
    yield
    _clear_descriptor_cache()


# ---------------------------------------------------------------------------
# FLAG ON — the fix is active
# ---------------------------------------------------------------------------
class TestFlagOnContradiction:
    def test_burberry_her_vs_him_rejected(self, flag_on):
        # THE leak, now fixed: opposite-gender flankers contradict -> reject.
        assert _selection_match(
            "Burberry Her", "Burberry Him", "fragrances", candidate_brand="Burberry",
        ) is False

    def test_burberry_him_vs_her_rejected_both_directions(self, flag_on):
        assert _selection_match(
            "Burberry Him", "Burberry Her", "fragrances", candidate_brand="Burberry",
        ) is False

    def test_narciso_for_her_vs_for_him_rejected(self, flag_on):
        assert _selection_match(
            "Narciso Rodriguez For Her", "Narciso Rodriguez For Him",
            "fragrances", candidate_brand="Narciso Rodriguez",
        ) is False

    def test_pour_homme_vs_pour_femme_rejected(self, flag_on):
        # Strict-gender contradiction (unchanged) still rejects.
        assert _selection_match(
            "Versace Eros Pour Homme", "Versace Eros Pour Femme", "fragrances",
            candidate_brand="Versace",
        ) is False

    # --- DECOUPLING GUARDS: no new over-rejection, no new leak -----------------
    def test_her_flanker_query_vs_base_still_matches(self, flag_on):
        # DECOUPLING: a "For Her" query must NOT be pushed into the femme-asymmetry by
        # the pronoun, so it still tolerates its gender-omitting base (no over-rejection).
        assert _selection_match(
            "Narciso Rodriguez For Her", "Narciso Rodriguez", "fragrances",
            candidate_brand="Narciso Rodriguez",
        ) is True

    def test_her_flagship_vs_base_still_matches(self, flag_on):
        # Elie Saab Le Parfum IS the canonical women's flagship — "For Her" vs the bare
        # base is the SAME product and must still match (the deep-review over-rejection).
        assert _selection_match(
            "Elie Saab Le Parfum For Her", "Elie Saab Le Parfum", "fragrances",
            candidate_brand="Elie Saab",
        ) is True

    def test_woman_query_vs_her_not_leaked(self, flag_on):
        # DECOUPLING: promoting her->women must NOT collapse a DISTINCT "Woman" product
        # into "Her"; the strict femme-asymmetry still rejects the empty-core match.
        assert _selection_match(
            "Burberry Woman", "Burberry Her", "fragrances", candidate_brand="Burberry",
        ) is False

    # --- GUARDS: one-sided gender omission must STILL match --------------------
    def test_sauvage_base_vs_for_him_still_matches(self, flag_on):
        assert _selection_match(
            "Dior Sauvage", "Dior Sauvage For Him", "fragrances", candidate_brand="Dior",
        ) is True

    def test_bleu_de_chanel_base_vs_pour_homme_still_matches(self, flag_on):
        assert _selection_match(
            "Bleu de Chanel", "Bleu de Chanel Pour Homme", "fragrances",
            candidate_brand="Chanel",
        ) is True

    # --- TOKENIZATION: a brand/name token must NOT false-trigger the pronoun ----
    def test_cher_name_not_a_gender(self, flag_on):
        # "Cher" folds to token 'cher' (not 'her') -> gender_pronoun None -> matches self.
        assert price_service._pronoun_gender_of("Cher Eau de Parfum") is None
        assert price_service._pronoun_gender_of("Terre d Hermes") is None

    # --- GUARDS: other categories UNCHANGED -----------------------------------
    def test_makeup_men_vs_for_him_unchanged(self, flag_on):
        assert _selection_match(
            "Nivea Men Cream", "Nivea Cream For Him", "makeup", candidate_brand="Nivea",
        ) is False

    def test_electronics_s24_vs_fe_unchanged(self, flag_on):
        assert _selection_match(
            "Galaxy S24", "Galaxy S24 FE", "electronics", candidate_brand="Samsung",
        ) is False


# ---------------------------------------------------------------------------
# FLAG OFF — byte-identical pre-fix behaviour (gender_pronoun is None)
# ---------------------------------------------------------------------------
class TestFlagOffByteIdentical:
    def test_burberry_her_vs_him_still_leaks_true(self, flag_off):
        assert _selection_match(
            "Burberry Her", "Burberry Him", "fragrances", candidate_brand="Burberry",
        ) is True

    def test_woman_vs_her_rejected_same_as_prod(self, flag_off):
        # The strict femme-asymmetry already rejects this on main (unchanged flag-OFF).
        assert _selection_match(
            "Burberry Woman", "Burberry Her", "fragrances", candidate_brand="Burberry",
        ) is False

    def test_her_query_vs_base_matches_same_as_prod(self, flag_off):
        assert _selection_match(
            "Narciso Rodriguez For Her", "Narciso Rodriguez", "fragrances",
            candidate_brand="Narciso Rodriguez",
        ) is True

    def test_electronics_s24_vs_fe_unchanged(self, flag_off):
        assert _selection_match(
            "Galaxy S24", "Galaxy S24 FE", "electronics", candidate_brand="Samsung",
        ) is False

    def test_pronoun_gender_of_inert_flag_off(self, flag_off):
        assert price_service._pronoun_gender_of("Burberry Her") is None
        assert price_service._pronoun_gender_of("Burberry Him") is None
