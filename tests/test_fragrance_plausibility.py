"""#17 B1 — fragrance size-plausibility guard.

The shipped accuracy guards (`is_implausible_high_value_price`) only floor
HIGH-VALUE electronics (reject <50 BHD for phone/laptop/console). A prod-smoke
hard-cap PARTIAL surfaced an implausibly-LOW fragrance converted price — Tom
Ford Ombré Leather 19.93 BHD (~$53), a sample/decant-grade listing whose genuine
full bottle is ~80 BHD. There was no fragrance analog, so the cascade served the
sample as the genuine price.

`is_implausible_low_fragrance_price(product_name, amount_bhd, title=None)` is the
fragrance analog. It is SIZE-AWARE: fragrances legitimately vary by size (a 30ml
decant is cheap by design), so the floor scales with the DETECTED/EXPECTED size
rather than being a blanket BHD floor. It is gated to DESIGNER/NICHE fragrance
brands, where a full bottle is reliably expensive, so a genuinely-cheap
mass-market body spray is never floored. Non-fragrance products are untouched, so
`is_implausible_high_value_price` and the wrong-SKU converted-deviation guard are
not regressed.

Three load-bearing invariants (team-lead spec):
  1. an implausibly-low FULL-SIZE designer fragrance is REJECTED;
  2. a genuine 30ml priced as a 30ml is KEPT;
  3. non-fragrance products are unaffected.
"""

import pytest

from app.services.price_service import (
    is_fragrance_query,
    is_implausible_low_fragrance_price,
    is_implausible_high_value_price,
)


class TestFragranceDetection:
    def test_designer_brand_without_product_word_detected(self):
        # "Tom Ford Ombré Leather" omits "perfume"/"edp" but is a fragrance.
        assert is_fragrance_query("Tom Ford Ombré Leather") is True
        assert is_fragrance_query("Creed Aventus") is True

    def test_generic_fragrance_product_word_detected(self):
        assert is_fragrance_query("Dior Sauvage Eau de Parfum") is True
        assert is_fragrance_query("some cologne 100ml") is True
        assert is_fragrance_query("Lattafa Asad perfume") is True

    def test_high_value_electronics_not_a_fragrance(self):
        # A phone is never a fragrance — keeps the two guards mutually exclusive.
        assert is_fragrance_query("iPhone 15 Pro Max") is False
        assert is_fragrance_query("Samsung Galaxy S24") is False

    def test_non_fragrance_categories_not_detected(self):
        assert is_fragrance_query("Nike Air Max") is False
        assert is_fragrance_query("Vitamin D3 5000 IU") is False
        assert is_fragrance_query("") is False


class TestImplausibleLowFragranceRejected:
    def test_prod_smoke_ombre_leather_sample_rejected(self):
        # The exact prod-smoke case: a designer fragrance, no size in the title,
        # at 19.93 BHD — below the 100ml full-bottle floor (25). REJECTED.
        assert is_implausible_low_fragrance_price(
            "Tom Ford Ombré Leather", 19.93, title="Tom Ford Ombré Leather"
        ) is True

    def test_full_size_designer_below_floor_rejected(self):
        # An explicit 100ml designer fragrance under the floor is a sample/decant.
        assert is_implausible_low_fragrance_price(
            "Creed Aventus", 14.0, title="Creed Aventus EDP 100ml"
        ) is True

    def test_size_unspecified_defaults_to_full_bottle_basis(self):
        # No size anywhere → flagship 100ml basis → 25 BHD floor.
        assert is_implausible_low_fragrance_price("Dior Sauvage", 12.0) is True

    def test_tiny_decant_price_for_full_bottle_rejected(self):
        # A 100ml-basis listing at a 5ml-decant price is clearly wrong.
        assert is_implausible_low_fragrance_price(
            "Chanel Bleu de Chanel", 8.0, title="Chanel Bleu de Chanel 100ml"
        ) is True


class TestGenuineSmallSizeKept:
    def test_genuine_30ml_priced_as_30ml_kept(self):
        # A 30ml floor is 25 * 30/100 = 7.5 BHD. A genuine 30ml at ~25 BHD is
        # comfortably above it — KEPT (the load-bearing false-positive guard).
        assert is_implausible_low_fragrance_price(
            "Tom Ford Ombré Leather", 25.0, title="Tom Ford Ombré Leather EDP 30ml"
        ) is False

    def test_genuine_small_decant_kept(self):
        # A genuine 10ml travel decant — floor 2.5 BHD; a 6 BHD decant is kept.
        assert is_implausible_low_fragrance_price(
            "Creed Aventus", 6.0, title="Creed Aventus 10ml decant"
        ) is False

    def test_genuine_full_bottle_at_real_price_kept(self):
        # The genuine ~80 BHD Ombré Leather full bottle — well above floor, KEPT.
        assert is_implausible_low_fragrance_price(
            "Tom Ford Ombré Leather", 80.0, title="Tom Ford Ombré Leather 100ml"
        ) is False

    def test_query_size_used_when_title_silent(self):
        # Title has no size; the query says 50ml → floor 12.5; a 20 BHD 50ml is
        # kept (above floor), but a 5 BHD 50ml would be rejected.
        assert is_implausible_low_fragrance_price(
            "Dior Sauvage 50ml", 20.0, title="Dior Sauvage"
        ) is False
        assert is_implausible_low_fragrance_price(
            "Dior Sauvage 50ml", 5.0, title="Dior Sauvage"
        ) is True


class TestNonFragranceUnaffected:
    def test_electronics_untouched_by_fragrance_guard(self):
        # A cheap phone accessory is handled by is_implausible_high_value_price,
        # NOT this guard — the fragrance guard returns False for electronics.
        assert is_implausible_low_fragrance_price("iPhone 15", 11.9) is False
        assert is_implausible_low_fragrance_price(
            "Samsung Galaxy S24", 11.9, title="Galaxy S24 case"
        ) is False

    def test_supplement_untouched(self):
        assert is_implausible_low_fragrance_price("Vitamin D3 5000 IU", 4.0) is False

    def test_generic_fashion_untouched(self):
        assert is_implausible_low_fragrance_price("Nike Air Max", 30.0) is False


class TestMassMarketFragranceNotFloored:
    def test_cheap_body_spray_not_a_designer_brand_kept(self):
        # A generic body spray IS a fragrance, but NOT a designer/niche brand, so
        # it can be genuinely cheap — the guard must not floor it.
        assert is_implausible_low_fragrance_price(
            "Generic body spray", 3.0, title="Generic body spray 200ml"
        ) is False

    def test_axe_body_spray_kept(self):
        assert is_implausible_low_fragrance_price(
            "Axe body spray", 2.5, title="Axe Dark Temptation body spray"
        ) is False


class TestEdgeCases:
    @pytest.mark.parametrize("amount", [None, 0.0, -5.0])
    def test_missing_or_nonpositive_amount_not_rejected(self, amount):
        # Nothing to reject — parity with is_implausible_high_value_price.
        assert is_implausible_low_fragrance_price("Creed Aventus", amount) is False

    def test_empty_product_name_not_rejected(self):
        assert is_implausible_low_fragrance_price("", 5.0) is False


class TestGuardsMutuallyExclusive:
    def test_high_value_guard_unchanged_for_phone(self):
        # Sanity: the existing high-value guard still fires for a cheap phone.
        assert is_implausible_high_value_price("iPhone 15", 11.9) is True

    def test_high_value_guard_false_for_fragrance(self):
        # The high-value guard does NOT fire for a fragrance (it isn't high-value),
        # which is exactly why the fragrance analog was needed.
        assert is_implausible_high_value_price("Tom Ford Ombré Leather", 19.93) is False
