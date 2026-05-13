"""
Bundle E Task 1.5 RED — fact_check_service emits per-dimension confidence
only; `overall_confidence` dropped; `data_freshness` flagged only when
the comparison data is genuinely shaky.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 1.5,
      § Test-1.5)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 7.

Existing function (`app.services.fact_check_service.build_fact_check`)
currently returns a dict with `overall_confidence: "low"|"medium"|"high"`
which the frontend renders as an apologetic red pill at the top of
Results. Decision 7 strips that pill entirely — overall_confidence MUST
NOT appear in the returned dict.

A NEW function `is_data_freshness_shaky(fact_check_results)` returns
True ONLY when at least 2 of these conditions hold across the
comparison:
  - no real prices on either product (both price_verified is False)
  - no reviews on either product (both review_sentiment_consistent is None)
  - all-estimated specs (both products have specs_verified + specs_likely == 0)

When True, the frontend shows a positive-framed gray inline notice
"Fresh listing — some data still settling. Tap to refresh." When False,
no notice at all (no apologetic banner — the visual default is clean).

Test classes:
  1. TestOverallConfidenceDropped — `build_fact_check(product)` no
     longer emits `overall_confidence`. Old callers may still depend on
     other keys (specs_verified, price_verified, ...) — those stay.
  2. TestDataFreshnessShakyPredicate — `is_data_freshness_shaky([fc_a,
     fc_b])` returns True ONLY when ≥2 shakiness conditions hold; False
     for 0 or 1 condition.
  3. TestDataFreshnessFalseOnNormalData — happy path: realistic
     fact_check pair → False (no apologetic banner shipped).

RED→GREEN trajectory:
  - At HEAD: `is_data_freshness_shaky` does not exist → ImportError →
    RED. `build_fact_check` STILL emits `overall_confidence` → its
    test_overall_confidence_dropped tests fail with KeyError-style
    assertion.
  - Post-Task-1.5: all assertions pass.
"""

from __future__ import annotations

import pytest

from app.services.fact_check_service import build_fact_check
# RED gate — this import does not yet exist.
from app.services.fact_check_service import is_data_freshness_shaky  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — overall_confidence is no longer emitted
# ---------------------------------------------------------------------------

class TestOverallConfidenceDropped:
    """Design § Decision 7: drop `overall_confidence` from the
    build_fact_check return shape. Per-dimension confidence stays
    (per design line 337: "Per-dimension `confidence: low` is
    communicated visually via the bar opacity + ≈ prefix")."""

    def _normal_product(self):
        """A typical product dict with all the internal _ prefixed
        keys that build_fact_check pops + uses."""
        return {
            "brand": "Glorious",
            "name": "Model O",
            "_spec_confidence": {"weight": "verified", "dpi": "verified"},
            "_review_verification": {
                "sentiment_consistent": True, "deviation": 0.1
            },
            "_price_verification": {
                "price_verified": True, "deviation_pct": 5.0,
                "source_count": 3,
            },
        }

    def test_overall_confidence_not_in_return_dict(self):
        product = self._normal_product()
        result = build_fact_check(product)
        assert "overall_confidence" not in result, (
            f"overall_confidence still emitted: {result}"
        )

    def test_per_field_keys_still_emitted(self):
        """Removing overall_confidence MUST NOT remove the per-field
        verification keys downstream consumers still rely on. The new
        contract is: same keys MINUS overall_confidence."""
        product = self._normal_product()
        result = build_fact_check(product)
        required_keys = {
            "specs_verified", "specs_likely", "specs_flagged",
            "specs_unverified", "price_verified", "price_deviation_pct",
            "review_sentiment_consistent", "review_rating_deviation",
        }
        missing = required_keys - set(result.keys())
        assert not missing, (
            f"non-overall-confidence keys disappeared: {missing}"
        )

    def test_works_on_low_confidence_inputs(self):
        """Even when historically overall_confidence would have been
        'low' (flagged specs, inconsistent sentiment), the new return
        omits overall_confidence — the frontend renders a per-dimension
        signal instead via bar opacity."""
        product = {
            "brand": "Brand",
            "name": "Product",
            "_spec_confidence": {"weight": "flagged"},
            "_review_verification": {
                "sentiment_consistent": False, "deviation": 1.5
            },
            "_price_verification": {
                "price_verified": False, "deviation_pct": None,
                "source_count": 0,
            },
        }
        result = build_fact_check(product)
        assert "overall_confidence" not in result, (
            f"overall_confidence STILL emitted on low-confidence input: {result}"
        )


# ---------------------------------------------------------------------------
# Test 2 — is_data_freshness_shaky predicate
# ---------------------------------------------------------------------------

class TestDataFreshnessShakyPredicate:
    """Design § Decision 7 line 332: shakiness fires only when ≥2 of:
    no real prices on either, no reviews on either, all-estimated
    specs. Less than 2 → predicate is False → frontend renders no
    apologetic banner."""

    def _fc_with(self, price_verified=True, sentiment_consistent=True,
                 specs_verified=2, specs_likely=1, **extras):
        """Build a build_fact_check-shaped dict directly."""
        return {
            "specs_verified": specs_verified,
            "specs_likely": specs_likely,
            "specs_flagged": 0,
            "specs_unverified": 0,
            "price_verified": price_verified,
            "price_deviation_pct": 5.0,
            "review_sentiment_consistent": sentiment_consistent,
            "review_rating_deviation": 0.1,
            **extras,
        }

    def test_returns_false_when_zero_shakiness_conditions(self):
        """Healthy data on both products → no banner."""
        fc_a = self._fc_with()
        fc_b = self._fc_with()
        assert is_data_freshness_shaky([fc_a, fc_b]) is False

    def test_returns_false_when_one_condition_only(self):
        """One condition alone is not enough — the predicate requires
        ≥2 to fire. This is what makes the banner rare and meaningful."""
        # Condition A: no real prices on either
        only_no_prices = [
            self._fc_with(price_verified=False),
            self._fc_with(price_verified=False),
        ]
        assert is_data_freshness_shaky(only_no_prices) is False, (
            f"single-condition (no prices) triggered banner: {only_no_prices}"
        )

    def test_returns_true_when_two_conditions(self):
        """No real prices on either + no reviews on either → ≥2
        conditions → banner."""
        shaky = [
            self._fc_with(price_verified=False, sentiment_consistent=None),
            self._fc_with(price_verified=False, sentiment_consistent=None),
        ]
        assert is_data_freshness_shaky(shaky) is True, (
            f"≥2-condition predicate did NOT trigger banner: {shaky}"
        )

    def test_returns_true_when_three_conditions(self):
        """All three: no prices, no reviews, all-estimated specs."""
        very_shaky = [
            self._fc_with(price_verified=False, sentiment_consistent=None,
                          specs_verified=0, specs_likely=0,
                          specs_unverified=3),
            self._fc_with(price_verified=False, sentiment_consistent=None,
                          specs_verified=0, specs_likely=0,
                          specs_unverified=3),
        ]
        assert is_data_freshness_shaky(very_shaky) is True

    def test_one_sided_does_not_trigger(self):
        """The design says "no real prices on EITHER", "no reviews on
        EITHER" — i.e. BOTH products must lack. A single product with
        bad data shouldn't blame the whole comparison."""
        one_sided = [
            self._fc_with(price_verified=False, sentiment_consistent=None,
                          specs_verified=0, specs_likely=0,
                          specs_unverified=3),
            self._fc_with(),  # healthy
        ]
        assert is_data_freshness_shaky(one_sided) is False, (
            f"one-sided bad data triggered banner: {one_sided}"
        )

    def test_handles_empty_or_single_list(self):
        """Defensive: predicate must not crash on empty or single-item
        input. Comparison flows always have 2 products, but the helper
        is reachable from other paths — return False for malformed
        input rather than raise."""
        assert is_data_freshness_shaky([]) is False
        assert is_data_freshness_shaky([self._fc_with()]) is False


# ---------------------------------------------------------------------------
# Test 3 — Normal data → no banner (regression guard)
# ---------------------------------------------------------------------------

class TestDataFreshnessFalseOnNormalData:
    """The whole point of Decision 7 is "no apologetic banner by
    default". This class is the regression guard — realistic-but-
    imperfect fact_check pairs must NOT trigger the banner."""

    def test_partial_specs_but_real_prices_and_reviews_is_not_shaky(self):
        """Missing some specs is normal (extraction misses some fields).
        With real prices + real reviews on both, no banner."""
        partial_specs = [
            {
                "specs_verified": 1, "specs_likely": 1,
                "specs_flagged": 0, "specs_unverified": 2,
                "price_verified": True, "price_deviation_pct": 8.0,
                "review_sentiment_consistent": True,
                "review_rating_deviation": 0.2,
            },
            {
                "specs_verified": 1, "specs_likely": 0,
                "specs_flagged": 0, "specs_unverified": 3,
                "price_verified": True, "price_deviation_pct": 6.0,
                "review_sentiment_consistent": True,
                "review_rating_deviation": 0.1,
            },
        ]
        assert is_data_freshness_shaky(partial_specs) is False

    def test_estimated_price_but_real_reviews_is_not_shaky(self):
        """One product with estimated price + real reviews on both is
        ONE condition (no real price on EITHER fails — only one side has
        no real price). Still False."""
        one_estimated = [
            {
                "specs_verified": 2, "specs_likely": 1,
                "specs_flagged": 0, "specs_unverified": 0,
                "price_verified": False,  # estimated
                "price_deviation_pct": None,
                "review_sentiment_consistent": True,
                "review_rating_deviation": 0.1,
            },
            {
                "specs_verified": 2, "specs_likely": 1,
                "specs_flagged": 0, "specs_unverified": 0,
                "price_verified": True,  # real
                "price_deviation_pct": 5.0,
                "review_sentiment_consistent": True,
                "review_rating_deviation": 0.1,
            },
        ]
        # "no real prices on either" predicate requires BOTH to be False,
        # so this is 0 conditions → False.
        assert is_data_freshness_shaky(one_estimated) is False


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-1.5 run:
#     python -m pytest tests/test_fact_check_service_v2.py -v
#     → ImportError on `is_data_freshness_shaky` → 1 collection error → RED
#
# Post-Task-1.5: 3 test classes, ~11 assertions. Coverage target ≥80%
# on the two changed surfaces in fact_check_service.
