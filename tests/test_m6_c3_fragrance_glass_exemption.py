"""M6 UNIT C3 — the ACCESSORY_KEYWORDS "glass" over-rejection for fragrances.

MEASURED (M0 A4 side finding): a scentsplit variant "'Ilm - 2ml Glass Spray"
at 16.99 USD is unreachable for ANY query including its own exact name, because
"glass" lives in ACCESSORY_KEYWORDS (tempered-glass / screen-protector vocab)
and ``is_accessory_for_category`` has no fragrance-scoped exemption for it — the
way it already exempts "skin" on pharmacy categories and "keyboard" on laptops.
A 2ml glass-spray decant IS the product on a decanting-house PDP.

Behind ENABLE_FRAGRANCE_GLASS_EXEMPTION (default OFF): when the orchestrator-
resolved category is fragrances, a bare "glass" keyword hit alone must NOT
classify the title as an accessory. Mirrors the EXISTING pharmacy-"skin" /
laptop-"keyboard" scoped-exemption pattern exactly. Any OTHER accessory keyword
still flags, so a genuine fragrance accessory the existing logic caught another
way (e.g. a "glass case") stays rejectable.

No live network — ``is_accessory_for_category`` is a pure string function.
"""

import pytest

from app.services.price_service import is_accessory_for_category

_FLAG = "ENABLE_FRAGRANCE_GLASS_EXEMPTION"


class TestFragranceGlassExemption:
    def test_flag_off_is_byte_identical_scentsplit_variant_still_rejected(
        self, monkeypatch
    ):
        """Flag OFF (unset) preserves the exact shipped behavior: the measured
        scentsplit "'Ilm - 2ml Glass Spray" fragrance variant is still an
        accessory (the "glass" token flags it)."""
        monkeypatch.delenv(_FLAG, raising=False)
        assert (
            is_accessory_for_category("'Ilm - 2ml Glass Spray", "fragrances")
            is True
        )

    def test_flag_on_scentsplit_variant_not_accessory(self, monkeypatch):
        """Flag ON: a fragrance-category glass-spray decant is the product, not
        an accessory."""
        monkeypatch.setenv(_FLAG, "true")
        assert (
            is_accessory_for_category("'Ilm - 2ml Glass Spray", "fragrances")
            is False
        )

    def test_flag_on_glass_bottle_and_glass_decant_phrases_not_accessory(
        self, monkeypatch
    ):
        """Flag ON: the "glass bottle" / "glass decant" phrasings on a fragrance
        title are also lifted (only the "glass" token was the trigger)."""
        monkeypatch.setenv(_FLAG, "true")
        assert (
            is_accessory_for_category("Aventus 10ml Glass Bottle", "fragrances")
            is False
        )
        assert (
            is_accessory_for_category("Oud Wood Glass Decant 5ml", "fragrances")
            is False
        )

    def test_flag_on_non_fragrance_glass_screen_protector_still_accessory(
        self, monkeypatch
    ):
        """Flag ON but NON-fragrance category: a "glass screen protector" is
        still an accessory — the exemption is scoped to fragrances only."""
        monkeypatch.setenv(_FLAG, "true")
        assert (
            is_accessory_for_category(
                "Tempered Glass Screen Protector", "electronics"
            )
            is True
        )

    def test_flag_on_other_accessory_keyword_still_flags_on_fragrances(
        self, monkeypatch
    ):
        """Flag ON, fragrance category: only "glass"-token-alone is lifted. Any
        OTHER accessory keyword (e.g. "case") still flags a fragrance title, so a
        genuine glass ACCESSORY the existing logic caught another way stays
        rejectable."""
        monkeypatch.setenv(_FLAG, "true")
        assert (
            is_accessory_for_category("Glass Atomizer Travel Case", "fragrances")
            is True
        )

    def test_flag_off_non_fragrance_glass_still_accessory(self, monkeypatch):
        """Flag OFF, non-fragrance: unchanged — "glass" still an accessory."""
        monkeypatch.delenv(_FLAG, raising=False)
        assert (
            is_accessory_for_category(
                "Tempered Glass Screen Protector", "electronics"
            )
            is True
        )
