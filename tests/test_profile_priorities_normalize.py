"""Bundle E — B3.1 regression test for `_normalize_weights_to_100`.

Plan reference: `docs/plans/bundle-e-visual-fidelity.md` § B3.1.

The Path A R1 implementation divided by MAX, which produced bars that
visually summed to a number other than 100 (Ahmed flagged on device:
"Bar sums to 99 but the math behind it is not working").

Path A R2 (commit `4aa9cff`) switched to largest-remainder (Hamilton)
rounding so the integer weights ALWAYS sum to exactly 100 — not 99,
not 101 — regardless of input cardinality or weight distribution.

This unit test pins the algorithm. It targets the pure function directly
(no FastAPI / Supabase / Redis stack) so it stays fast (<10ms) and is
robust against route-handler refactors.

Cases:
1. Three equal weights — uniform 100/3 distribution with leftover routed
   to the largest fractional remainders, insertion-order tie-break.
2. Skewed weights — sum-not-max contract.
3. Single non-zero weight — the non-zero key absorbs the full 100.
4. Empty input — empty dict out.
5. All-zero — uniform fallback path produces sum=100 even when total≤0.
6. Two-key parity — both ~50 with one absorbing the leftover.

All cases assert (a) sum is exactly 100, (b) values are 0..100, (c) the
specific shape we ship to PrioritiesInline.
"""
from __future__ import annotations

import pytest

from app.api.profile_routes import _normalize_weights_to_100


class TestNormalizeWeightsToSum100:

    def test_three_equal_weights_sum_to_100(self):
        """Per plan spec: {quality:1, price:1, durable:1} → sum=100, each ~33."""
        out = _normalize_weights_to_100({"quality": 1.0, "price": 1.0, "durable": 1.0})
        assert sum(out.values()) == 100
        # Hamilton remainders for 1/1/1: floors = 33/33/33 = 99, leftover 1
        # All fractional remainders equal — insertion-order tie-break gives
        # the leftover to the first key.
        assert out == {"quality": 34, "price": 33, "durable": 33}

    def test_skewed_weights_sum_to_100(self):
        """Per plan spec: {quality:5, price:2, durable:1} → sum=100."""
        out = _normalize_weights_to_100({"quality": 5.0, "price": 2.0, "durable": 1.0})
        assert sum(out.values()) == 100
        # 5/8=62.5 floor 62, 2/8=25 floor 25, 1/8=12.5 floor 12 → sum=99
        # Leftover 1 to largest remainder: quality (.5) and durable (.5) tie
        # — insertion-order tie-break sends leftover to quality.
        assert out["quality"] in (62, 63)
        assert out["price"] == 25
        assert out["durable"] in (12, 13)
        # Exactly one of the two .5-remainder keys absorbed the leftover.
        assert (out["quality"] == 63) ^ (out["durable"] == 13)

    def test_single_non_zero_absorbs_full_100(self):
        """Per plan spec: {quality:5, price:0, durable:0} → {quality:100, ...}."""
        out = _normalize_weights_to_100({"quality": 5.0, "price": 0.0, "durable": 0.0})
        assert sum(out.values()) == 100
        assert out["quality"] == 100
        assert out["price"] == 0
        assert out["durable"] == 0

    def test_empty_input_yields_empty_dict(self):
        """Defensive — empty raw_weights returns empty dict (caller hides UI)."""
        assert _normalize_weights_to_100({}) == {}

    def test_all_none_filtered_to_empty(self):
        """All-None values are filtered out before normalization."""
        assert _normalize_weights_to_100({"a": None, "b": None}) == {}

    def test_all_zero_uses_uniform_fallback_sums_to_100(self):
        """When total<=0 (all zeros), uniform fallback still produces sum=100.

        Three keys all zero → 100/3 = 33 each (99 total) + 1 leftover routed
        by insertion order → {a: 34, b: 33, c: 33}.
        """
        out = _normalize_weights_to_100({"a": 0.0, "b": 0.0, "c": 0.0})
        assert sum(out.values()) == 100
        assert out["a"] == 34  # first insertion absorbs leftover
        assert out["b"] == 33
        assert out["c"] == 33

    def test_two_keys_unequal_sum_to_100(self):
        """{a: 3, b: 1} → {a: 75, b: 25}."""
        out = _normalize_weights_to_100({"a": 3.0, "b": 1.0})
        assert sum(out.values()) == 100
        assert out == {"a": 75, "b": 25}

    def test_divides_by_sum_not_max(self):
        """Regression test against the Path A R1 bug — divides by SUM.

        If the implementation divided by MAX (the pre-R2 bug), then
        {a:1, b:1, c:1} would yield {a:100, b:100, c:100} = sum 300.
        Path A R2 divides by SUM=3 → {a:34, b:33, c:33} = sum 100.
        """
        out = _normalize_weights_to_100({"a": 1.0, "b": 1.0, "c": 1.0})
        assert sum(out.values()) == 100, (
            f"Path A R1 regression — expected sum=100, got {sum(out.values())}. "
            f"This means the normalize function reverted to dividing by MAX."
        )

    def test_no_value_exceeds_100(self):
        """Defensive — clamp to [0, 100] even with unusual inputs."""
        # Tiny non-zero among large keys — share is <1%, floors to 0
        out = _normalize_weights_to_100({"big": 1000.0, "tiny": 0.001})
        for v in out.values():
            assert 0 <= v <= 100
        assert sum(out.values()) == 100

    def test_no_negative_values(self):
        """Defensive — clamp lower bound to 0."""
        # The function filters None but accepts negative floats; the floor
        # logic could theoretically produce -1 with adversarial inputs
        # because of the leftover-distribution step. The clamp at end
        # ensures we never ship a negative bar to the frontend.
        out = _normalize_weights_to_100({"a": 1.0, "b": 2.0, "c": 3.0})
        for k, v in out.items():
            assert v >= 0, f"key {k} got negative weight {v}"

    def test_four_priorities_sum_to_100(self):
        """4-key case — Hamilton extends naturally beyond 3."""
        out = _normalize_weights_to_100({
            "quality": 4.0, "price": 3.0, "durable": 2.0, "brand": 1.0,
        })
        assert sum(out.values()) == 100
        # 4/10=40, 3/10=30, 2/10=20, 1/10=10 exact — no remainder
        assert out == {"quality": 40, "price": 30, "durable": 20, "brand": 10}
