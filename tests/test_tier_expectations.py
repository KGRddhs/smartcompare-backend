"""Bundle C § 3b — TIER_EXPECTATIONS extends to 5 tiers.

Per design § 3b + plan A.5.2: TIER_EXPECTATIONS adds `luxury: 0.88` and
`top_tier: 0.90`, re-splitting today's `luxury=0.85` into the two
top-tier quality-delivery expectations.

Used by the value-formula cross-tier path to penalize a product whose
delivery falls below the expected quality bar for its detected tier.
"""
from app.services.scoring_service import TIER_EXPECTATIONS


def test_tier_expectations_5_tiers():
    """Spec § 3b: 5-tier expectations with luxury re-split into luxury+top_tier."""
    assert TIER_EXPECTATIONS["budget"] == 0.60
    assert TIER_EXPECTATIONS["mid"] == 0.70
    assert TIER_EXPECTATIONS["premium"] == 0.80
    assert TIER_EXPECTATIONS["luxury"] == 0.88   # was 0.85 in legacy 4-tier
    assert TIER_EXPECTATIONS["top_tier"] == 0.90


def test_tier_expectations_strictly_monotonic():
    """Quality expectation must rise monotonically with tier — top_tier
    products are held to a higher bar than luxury, etc."""
    order = ["budget", "mid", "premium", "luxury", "top_tier"]
    values = [TIER_EXPECTATIONS[t] for t in order]
    for a, b in zip(values, values[1:]):
        assert a < b, f"TIER_EXPECTATIONS not monotonic: {values}"


def test_tier_expectations_values_in_unit_interval():
    """All expectations live in the (0, 1] range — they're a quality
    fraction, not a score."""
    for tier, val in TIER_EXPECTATIONS.items():
        assert 0.0 < val <= 1.0, f"{tier}={val} outside (0,1]"
