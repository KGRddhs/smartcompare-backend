"""Gender-flanker leak — "Gents" vs "Ladies" (pronoun-decoupled, PR#32 extension).

GROUND TRUTH (reproduced through the SAME runtime selector the orchestrator runs,
`price_service._selection_match`): a fragrance "<X> Gents" vs "<X> Ladies" WRONGLY MATCHED
(=True) — the exact class PR#32 fixed for him/her. "gents"/"ladies" sit in
`_FRAGRANCE_PADDING_TOKENS` (the subset check ignores them) but were ABSENT from BOTH the
strict `_GENDER_MEN_TOKENS`/`_GENDER_WOMEN_TOKENS` AND `_pronoun_gender_of`, so the
`_gender_mismatch` CONTRADICTION axis never fired on Gents/Ladies. Common in the local
Arabic houses (e.g. "Ajmal Aristocrat For Him/Her" also ship "... Gents/... Ladies").

THE FIX (inert unless ENABLE_EXACT_PRICE_GATE AND ENABLE_VARIANT_DESCRIPTOR_AXES are both
true — `variant_descriptor_axes_enabled()`. ENABLE_EXACT_PRICE_GATE defaults ON when unset,
so ENABLE_VARIANT_DESCRIPTOR_AXES (default OFF) is the only real switch; its prod state is
UNVERIFIED):
extend the SEPARATE `_pronoun_gender_of` (gents->men, ladies->women) — the SAME decoupled
axis PR#32 added for him/her. It feeds ONLY the contradiction axis (`_vd_gender_mismatch`,
via `VariantDescriptor.gender_pronoun`). `_gender_of` stays STRICT, so the femme-asymmetry
(`_vd_feminine_query_unconfirmed`) and the empty-core/identity logic are UNCHANGED.

STRICT GENDER WINS: `_vd_gender_mismatch` consults the pronoun gender ONLY when the strict
gender is None. Without that, a strict-gender title carrying a stray opposite catalogue
word ("Versace Eros Pour Femme - Gents") read as ambiguous and a strict contradiction that
main rejected passed at BOTH the selection gate and the backstop_identity_verdict chokepoint.

SCOPE: the contradiction axis runs for fragrances, makeup/skincare/haircare and fashion, so
Gents/Ladies now also reject in beauty and fashion (Casio Edifice Gents vs Ladies Watch;
212 Men vs 212 Ladies in makeup) — pinned below.

Flag OFF -> gender_pronoun is None -> byte-identical old behaviour (Gents vs Ladies still leaks).
"""
import socket

import pytest

from app.services import price_service
from app.services.price_service import _selection_match, backstop_identity_verdict

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Block (and FAIL the test on) any non-loopback connect or DNS lookup."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def _host(address):
        if isinstance(address, tuple) and address:
            return str(address[0])
        return str(address)

    def _is_local(sock, address):
        if getattr(socket, "AF_UNIX", None) is not None and sock.family == socket.AF_UNIX:
            return True
        return _host(address) in _LOOPBACK_HOSTS

    def guarded_connect(self, address):
        if _is_local(self, address):
            return real_connect(self, address)
        attempts.append(("connect", _host(address)))
        raise OSError("network access blocked in this test module")

    def guarded_connect_ex(self, address):
        if _is_local(self, address):
            return real_connect_ex(self, address)
        attempts.append(("connect_ex", _host(address)))
        raise OSError("network access blocked in this test module")

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is None or str(host) in _LOOPBACK_HOSTS:
            return real_getaddrinfo(host, *args, **kwargs)
        attempts.append(("getaddrinfo", str(host)))
        raise OSError("DNS lookup blocked in this test module")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    yield
    if attempts:
        pytest.fail(f"test attempted network access: {attempts}")


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


# A strict-gender title with a stray OPPOSITE catalogue word on one side. Main rejects
# every pair at both call sites; the pronoun must not downgrade the strict gender.
# These two are rejected at SELECTION only through the contradiction axis
# (_vd_gender_mismatch), so their selection pins go red if the pronoun is let win.
_STRICT_CONTRADICTION_VIA_MISMATCH_AXIS = [
    ("Versace Eros Pour Homme", "Versace Eros Pour Femme - Gents", "Versace"),
    ("Dior Sauvage For Men", "Dior Sauvage For Women Gents", "Dior"),
]
# A strict-women query: the femme-asymmetry already rejects it at SELECTION on main, so
# only its BACKSTOP pin has mutation power; its selection pin is a no-regression guard.
_FEMME_QUERY_VS_HOMME_LADIES = ("Versace Eros Pour Femme", "Versace Eros Pour Homme Ladies", "Versace")
_STRICT_CONTRADICTION_WITH_STRAY_WORD = _STRICT_CONTRADICTION_VIA_MISMATCH_AXIS + [
    _FEMME_QUERY_VS_HOMME_LADIES,
]


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

    def test_gents_vs_ladies_rejected_at_backstop(self, flag_on):
        assert backstop_identity_verdict(
            "Ajmal Aristocrat Gents", "Ajmal Aristocrat Ladies", "fragrances", brand="Ajmal",
        ) == (False, "not_exact:gender")

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

    # --- GUARD: one-sided gender omission must STILL match ---------------------
    def test_one_sided_gents_candidate_still_matches_base_query(self, flag_on):
        # A contradiction needs BOTH sides stated: a base query vs a "Gents" candidate
        # must pass at both call sites (fails if the both-stated requirement is dropped).
        assert _selection_match(
            "Ajmal Aristocrat", "Ajmal Aristocrat Gents", "fragrances",
            candidate_brand="Ajmal",
        ) is True
        assert backstop_identity_verdict(
            "Ajmal Aristocrat", "Ajmal Aristocrat Gents", "fragrances", brand="Ajmal",
        ) == (True, None)

    # --- TOKENIZATION: a name token must NOT false-trigger the pronoun ----------
    def test_gentleman_name_not_a_gender(self, flag_on):
        # "Gentleman"/"Gentlemen" (Givenchy line NAME) fold to their own token, never 'gents'.
        assert price_service._pronoun_gender_of("Givenchy Gentleman") is None
        assert price_service._pronoun_gender_of("Givenchy Gentlemen Society") is None
        assert price_service._pronoun_gender_of("Givenchy Gentleman Boisee") is None

    def test_gentleman_query_does_not_contradict_one_sided_ladies_candidate(self, flag_on):
        # If "Gentleman" were read as a men's word it would contradict "Ladies" and
        # reject; as a plain name token the Ladies side is one-sided and still matches.
        assert _selection_match(
            "Givenchy Gentleman", "Givenchy Gentleman Ladies", "fragrances",
            candidate_brand="Givenchy",
        ) is True

    # --- GUARD: the gender axis stays out of non-gendered categories -----------
    def test_no_regression_electronics_has_no_gender_axis(self, flag_on):
        # Scope guard: the pronoun IS extracted for an electronics title, but the
        # contradiction axis is scoped to fragrance/beauty/fashion, so it never reports
        # "gender" there (fails if the axis is widened to every category).
        q = price_service.extract_variant_descriptor("Galaxy S24 Gents Edition", "electronics")
        c = price_service.extract_variant_descriptor("Galaxy S24 Ladies Edition", "electronics")
        assert (q.gender_pronoun, c.gender_pronoun) == ("men", "women")
        assert price_service._descriptor_axis_mismatch(q, c, "electronics") != "gender"


class TestStrictGenderWins:
    @pytest.mark.parametrize("query,candidate,brand", _STRICT_CONTRADICTION_VIA_MISMATCH_AXIS)
    def test_selection_rejects(self, flag_on, query, candidate, brand):
        assert _selection_match(query, candidate, "fragrances", candidate_brand=brand) is False

    def test_no_regression_femme_query_vs_homme_ladies_rejected_at_selection(self, flag_on):
        # No-regression guard (ruling-mandated pin): the strict femme-asymmetry rejects this
        # at selection on main and under every gender_mismatch mutation, so it cannot fail
        # when the strict-wins fix is removed. Its backstop twin below carries the power.
        query, candidate, brand = _FEMME_QUERY_VS_HOMME_LADIES
        assert _selection_match(query, candidate, "fragrances", candidate_brand=brand) is False

    @pytest.mark.parametrize("query,candidate,brand", _STRICT_CONTRADICTION_WITH_STRAY_WORD)
    def test_backstop_rejects_as_gender(self, flag_on, query, candidate, brand):
        assert backstop_identity_verdict(
            query, candidate, "fragrances", brand=brand,
        ) == (False, "not_exact:gender")

    def test_fashion_selection_and_backstop_reject(self, flag_on):
        q, c = "Dior Sauvage For Men", "Dior Sauvage For Women Gents"
        assert _selection_match(q, c, "fashion", candidate_brand="Dior") is False
        assert backstop_identity_verdict(q, c, "fashion", brand="Dior") == (
            False, "not_exact:gender")

    def test_strict_agreement_survives_stray_opposite_word(self, flag_on):
        # Strict men on both sides; the candidate's stray "Ladies" must not override its
        # strict gender (fails if the pronoun is allowed to win over the strict gender).
        q, c = "Dior Sauvage For Men", "Dior Sauvage For Men Ladies"
        assert _selection_match(q, c, "fragrances", candidate_brand="Dior") is True
        assert backstop_identity_verdict(q, c, "fragrances", brand="Dior") == (True, None)


class TestPronounTokenization:
    @pytest.mark.parametrize("title", [
        "Tom Ford Oud Wood Ladies & Gents",
        "Oud for Him and Her",
        "Ajmal Aristocrat for Ladies and Gents",
    ])
    def test_both_genders_is_ambiguous(self, flag_on, title):
        assert price_service._pronoun_gender_of(title) is None

    def test_ladies_query_vs_ladies_and_gents_candidate_matches(self, flag_on):
        # A "Ladies & Gents" title is ambiguous (None), so it cannot contradict a Ladies
        # query (fails if a two-gender title resolves to one side).
        assert _selection_match(
            "Tom Ford Oud Wood Ladies", "Tom Ford Oud Wood Ladies & Gents", "fragrances",
            candidate_brand="Tom Ford",
        ) is True

    @pytest.mark.parametrize("title,expected", [
        ("Ajmal Aristocrat Gent's", "men"),
        ("Ajmal Aristocrat Ladies'", "women"),
        ("Ajmal Aristocrat Ｇｅｎｔｓ", "men"),  # full-width Gents
        ("AJMAL ARISTOCRAT GENTS", "men"),
    ])
    def test_apostrophe_and_fullwidth_fold_to_the_token(self, flag_on, title, expected):
        assert price_service._pronoun_gender_of(title) == expected

    def test_apostrophe_forms_reject_at_selection(self, flag_on):
        assert _selection_match(
            "Ajmal Aristocrat Gent's", "Ajmal Aristocrat Ladies'", "fragrances",
            candidate_brand="Ajmal",
        ) is False

    @pytest.mark.parametrize("title", [
        "Ajmal Aristocrat Gentsx",
        "Ajmal Aristocrat Xladies",
        "Megents Oud",
        "Sladies Musk",
    ])
    def test_word_token_not_substring(self, flag_on, title):
        assert price_service._pronoun_gender_of(title) is None


class TestFashionBeautyScope:
    def test_fashion_gents_vs_ladies_watch_rejected(self, flag_on):
        q, c = "Casio Edifice Gents Watch", "Casio Edifice Ladies Watch"
        assert _selection_match(q, c, "fashion", candidate_brand="Casio") is False
        assert backstop_identity_verdict(q, c, "fashion", brand="Casio") == (
            False, "not_exact:gender")

    def test_makeup_men_vs_ladies_rejected(self, flag_on):
        q, c = "Carolina Herrera 212 Men", "Carolina Herrera 212 Ladies"
        assert _selection_match(q, c, "makeup", candidate_brand="Carolina Herrera") is False
        assert backstop_identity_verdict(q, c, "makeup", brand="Carolina Herrera") == (
            False, "not_exact:gender")

    @pytest.mark.parametrize("q,c", [
        ("Casio Edifice Gents Watch", "Casio Edifice Gent's Watch"),
        ("Casio Edifice Ladies Watch", "Casio Edifice Ladies' Watch"),
    ])
    def test_fashion_same_pronoun_gender_matches_across_spellings(self, flag_on, q, c):
        # Both sides carry ONLY a pronoun gender (strict None) and it AGREES after folding,
        # so neither call site may reject (fails if the contradiction axis fires on any
        # both-stated pair instead of on a conflicting one).
        assert (price_service._pronoun_gender_of(q) ==
                price_service._pronoun_gender_of(c) is not None)
        assert _selection_match(q, c, "fashion", candidate_brand="Casio") is True
        assert backstop_identity_verdict(q, c, "fashion", brand="Casio") == (True, None)


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

    def test_ladies_query_vs_base_matches_flag_off(self, flag_off):
        assert _selection_match(
            "Ajmal Aristocrat Ladies", "Ajmal Aristocrat", "fragrances",
            candidate_brand="Ajmal",
        ) is True

    def test_fashion_gents_vs_ladies_unchanged_flag_off(self, flag_off):
        assert _selection_match(
            "Casio Edifice Gents Watch", "Casio Edifice Ladies Watch", "fashion",
            candidate_brand="Casio",
        ) is True

    @pytest.mark.parametrize("query,candidate,brand", _STRICT_CONTRADICTION_VIA_MISMATCH_AXIS)
    def test_no_regression_strict_contradiction_rejected_flag_off(
            self, flag_off, query, candidate, brand):
        # No-regression guard: flag OFF the pronoun is None, so the strict contradiction
        # rejects through the mismatch axis exactly as on main. By construction it cannot
        # fail when the (flag-gated) fix is removed; it goes red if the selection chain
        # stops consulting _vd_gender_mismatch.
        assert _selection_match(query, candidate, "fragrances", candidate_brand=brand) is False
