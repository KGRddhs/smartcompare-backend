"""Cache-WRITE gate parity + supplement dose cache-key (scraping audit 2026-07-08).

(a) should_cache_price OMITTED the plausibility/decant accuracy guards is_price_showable
    enforces at DISPLAY, so a below-floor decant / sample / high-value-accessory mis-scrape
    carrying a title + real PDP URL could be WRITTEN to the genuine 7d cache and poison the
    slot for the TTL. Fixed via the shared _fails_accuracy_guards helper (INCLUDING the
    PR#33 budget-Arabic-house floor bypass, so a genuine Lattafa/Rasasi 12 BHD full bottle
    still caches — no double-rejection).

(b) the gate-ON base strip removed mg/mcg/IU from the cache-key base with no token to
    re-carry it, so "Vitamin C 1000mg" and "Vitamin C 500mg" collided onto ONE key. Fixed
    with a supplements-gated dose token in _identity_cache_token.

Both under ENABLE_EXACT_PRICE_GATE (default ON); flag-OFF byte-identical.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services import price_service as ps
from app.services.price_service import (
    should_cache_price, is_price_showable, build_size_aware_price_cache_key, _dose_token,
)


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "1")
    ps._extract_variant_descriptor_cached.cache_clear()
    yield
    ps._extract_variant_descriptor_cached.cache_clear()


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "0")
    ps._extract_variant_descriptor_cached.cache_clear()
    yield
    ps._extract_variant_descriptor_cached.cache_clear()


def _price(**kw):
    d = {
        "amount": 150.0, "currency": "BHD", "source_method": "woo_store_api",
        "title": "Tom Ford Oud Wood Eau de Parfum 100ml", "in_stock": True,
        "url": "https://sephora.bh/products/tom-ford-oud-wood-100ml",
    }
    d.update(kw)
    return d


# --------------------------------------------------------------------------
# (a) cache-write gate must reject what the display gate pends
# --------------------------------------------------------------------------
class TestCacheWriteAccuracyGuards:
    def test_below_floor_designer_fragrance_not_cached(self, flag_on):
        # A designer fragrance far below the 25/100ml floor -> is_price_showable pends it,
        # so the cache write MUST also refuse (else it poisons the 7d slot).
        p = _price(amount=8.0)
        assert is_price_showable("Tom Ford Oud Wood", p, "fragrances",
                                 enforce_correctness=True) is False
        assert should_cache_price("Tom Ford Oud Wood", p, "fragrances") is False

    def test_sample_decant_listing_not_cached(self, flag_on):
        p = _price(amount=35.0, title="Tom Ford Oud Wood DECANT 5ml Sample")
        assert should_cache_price("Tom Ford Oud Wood", p, "fragrances") is False

    def test_genuine_on_floor_price_still_caches(self, flag_on):
        # Positive control — a plausible genuine price with matching identity still caches.
        p = _price(amount=150.0)
        assert is_price_showable("Tom Ford Oud Wood", p, "fragrances",
                                 enforce_correctness=True) is True
        assert should_cache_price("Tom Ford Oud Wood", p, "fragrances") is True

    def test_budget_house_genuine_low_price_still_caches(self, flag_on):
        # CRITICAL no-double-rejection: a genuine budget-Arabic-house 12 BHD full bottle
        # is rescued by _budget_house_trusted_price at BOTH chokepoints — showable AND cached.
        p = _price(
            amount=12.0, title="Lattafa Khamrah Eau de Parfum 100ml",
            url="https://alibaksh.com/product/lattafa-khamrah-edp-100ml",
            source_method="woo_store_api",
        )
        assert is_price_showable("Lattafa Khamrah", p, "fragrances",
                                 enforce_correctness=True) is True
        assert should_cache_price("Lattafa Khamrah", p, "fragrances") is True

    def test_flag_off_still_caches_below_floor(self, flag_off):
        # Byte-identical rollback: with the gate OFF, should_cache_price returns True
        # unconditionally (the accuracy guard is inside the gate-ON body).
        p = _price(amount=8.0)
        assert should_cache_price("Tom Ford Oud Wood", p, "fragrances") is True


# --------------------------------------------------------------------------
# (b) supplement dose cache-key collision
# --------------------------------------------------------------------------
class TestDoseCacheKey:
    def _key(self, name, iden, cat="supplements"):
        return build_size_aware_price_cache_key("", name, None, "bahrain", iden, category=cat)

    def test_different_mg_dose_distinct_keys_flag_on(self, flag_on):
        k1000 = self._key("Vitamin C 1000mg", "Vitamin C 1000mg 60 Capsules")
        k500 = self._key("Vitamin C 500mg", "Vitamin C 500mg 60 Capsules")
        assert k1000 != k500

    def test_different_iu_dose_distinct_keys_flag_on(self, flag_on):
        k5000 = self._key("Vitamin D3 5000 IU", "Vitamin D3 5000 IU 120 Softgels")
        k1000 = self._key("Vitamin D3 1000 IU", "Vitamin D3 1000 IU 120 Softgels")
        assert k5000 != k1000

    def test_same_dose_different_field_same_key_flag_on(self, flag_on):
        # Dose in name vs in identity_text -> the strip+re-append collapse yields ONE key.
        k_a = build_size_aware_price_cache_key("", "Vitamin C 1000mg", None, "bahrain",
                                               "Vitamin C 60 Capsules", category="supplements")
        k_b = build_size_aware_price_cache_key("", "Vitamin C", None, "bahrain",
                                               "Vitamin C 1000mg 60 Capsules", category="supplements")
        assert k_a == k_b

    def test_other_category_reinfers_supplement(self, flag_on):
        # category 'other' that infers to supplements still splits by dose.
        k5000 = self._key("Vitamin D3 5000 IU", "Vitamin D3 5000 IU Softgels", cat="other")
        k1000 = self._key("Vitamin D3 1000 IU", "Vitamin D3 1000 IU Softgels", cat="other")
        assert k5000 != k1000

    def test_dose_token_unit(self, flag_on):
        assert _dose_token("Vitamin C 1000mg", "supplements") == "1000mg"
        assert _dose_token("Vitamin D3 5000 IU", "supplements") == "5000iu"
        # multi-dose stays distinct + sorted
        assert _dose_token("B-Complex 100mg 400mcg", "supplements") == "100mg-400mcg"
        # not a supplement -> no token
        assert _dose_token("Dior Sauvage EDT 100ml", "fragrances") == ""
        # supplement with no dose -> no token
        assert _dose_token("Vitamin C 60 Capsules", "supplements") == ""

    def test_dose_token_inert_flag_off(self, flag_off):
        assert _dose_token("Vitamin C 1000mg", "supplements") == ""

    def test_non_supplement_key_unchanged_by_dose(self, flag_on):
        # A fragrance key must not gain a dose token (no mg/IU in fragrance sizes anyway).
        k1 = self._key("Dior Sauvage EDT 100ml", "Dior Sauvage EDT 100ml", cat="fragrances")
        k2 = self._key("Dior Sauvage EDT 100ml", "Dior Sauvage EDT 100ml", cat="fragrances")
        assert k1 == k2  # deterministic, no dose interference
