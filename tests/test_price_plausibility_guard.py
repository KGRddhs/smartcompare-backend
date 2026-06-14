"""S3-reopen T1 refinement (team-lead Decision-F 2026-06-14) — the price
trustworthiness gate is ABSOLUTE plausibility, NOT deviation-from-GPT-estimate.

The GPT training estimate is the weakest signal in the system; it must NEVER be
the arbiter that vetoes a real cited price. A 2-3x deviation from the guess is
ambiguous — it is EITHER a legitimately-different real price (the guess is just
wrong) OR a mis-extraction (an EPP installment "BHD 48.332/month", an accessory,
a wrong variant). We must not trade "no estimation" for "wrong scrape", so the
gate is absolute category plausibility:

  - plausible real price  -> trust it (return over the estimate), even if it
    differs wildly from the GPT guess (the guess being wrong is WHY we don't
    trust it as a judge).
  - implausible real price -> it is a wrong-scrape; DROP it (do not promote),
    fall to the estimate (tier-8) — surfacing a garbage scrape is as bad as a
    fake estimate; the absolute guard picks the lesser evil.

`is_price_plausible(amount_bhd, category)` anchors on
scoring_service.PRICE_TIERS_BY_CATEGORY (the real per-category BHD breakpoints):
reject amount<=0, below 0.1x the budget breakpoint, or above 3x the luxury
breakpoint. Unknown/'other' categories are permissive (only amount>0) since
their magnitude is unbounded (cars to snacks).
"""

import pytest

from app.services.price_service import is_price_plausible


class TestElectronicsBounds:
    def test_legit_iphone_price_plausible(self):
        # ~245 BHD real iPhone — squarely inside electronics tiers (mid/premium).
        assert is_price_plausible(244.990, "electronics") is True

    def test_legit_deviant_high_phone_plausible(self):
        # A real flagship at 300 BHD that deviates 3x from a bad 100 BHD GPT
        # guess is STILL plausible — the guess is wrong, not the price.
        assert is_price_plausible(300.0, "electronics") is True

    def test_midrange_electronics_not_overrejected(self):
        # The guard is category-absolute (not per-model) and deliberately WIDE:
        # 48 BHD is a plausible electronics price (cheap earbuds/accessory), so
        # it is NOT rejected on amount alone. The EPP installment-as-iPhone case
        # ("BHD 48.332/month") is handled UPSTREAM by the microdata
        # installment-skip — this guard only catches gross category outliers, it
        # must never over-reject a legitimately mid-range price.
        assert is_price_plausible(48.332, "electronics") is True

    def test_absurdly_low_phone_implausible(self):
        # iPhone @ 5 BHD — below 0.1 x budget breakpoint (100*0.1=10). Wrong
        # scrape (a cable, an accessory, a typo). Rejected.
        assert is_price_plausible(5.0, "electronics") is False

    def test_absurdly_high_phone_implausible(self):
        # iPhone @ 9000 BHD — above 3 x luxury breakpoint (2000*3=6000). Wrong
        # scrape (a bundle, a B2B pallet, a currency error). Rejected.
        assert is_price_plausible(9000.0, "electronics") is False

    def test_zero_and_negative_implausible(self):
        assert is_price_plausible(0.0, "electronics") is False
        assert is_price_plausible(-5.0, "electronics") is False


class TestSupplementsBounds:
    def test_legit_supplement_plausible(self):
        # 18 BHD vitamin D — inside supplements tiers (budget=11/mid=30).
        assert is_price_plausible(18.0, "supplements") is True

    def test_absurdly_low_supplement_implausible(self):
        # 0.5 BHD — below 0.1 x supplements budget breakpoint (11*0.1=1.1).
        assert is_price_plausible(0.5, "supplements") is False

    def test_absurdly_high_supplement_implausible(self):
        # supplements luxury breakpoint is inf (top_tier folded). Falls back to
        # the next-lowest finite breakpoint (premium=60) x a wider ceiling so a
        # genuinely-expensive supplement is not over-rejected, but 9000 BHD is.
        assert is_price_plausible(9000.0, "supplements") is False


class TestUnknownCategoryPermissive:
    @pytest.mark.parametrize("cat", ["other", "unknown-xyz", "", None])
    def test_unknown_category_only_rejects_nonpositive(self, cat):
        # 'other' spans cars (5000+) to snacks (2) — magnitude is unbounded, so
        # the guard is permissive: only amount>0 is required.
        assert is_price_plausible(5000.0, cat) is True
        assert is_price_plausible(2.0, cat) is True
        assert is_price_plausible(0.0, cat) is False
        assert is_price_plausible(-1.0, cat) is False


class TestNoneAmount:
    def test_none_amount_implausible(self):
        assert is_price_plausible(None, "electronics") is False
