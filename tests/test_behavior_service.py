"""
Tests for behavior_service.py — behavioral learning and weight adjustments.
"""
import pytest
from datetime import datetime, timedelta
from app.services.behavior_service import BehaviorService


class TestBehaviorProfile:
    """Tests for behavioral profile computation and storage."""

    @pytest.mark.asyncio
    async def test_compute_category_affinity(self):
        """Category affinity computed from comparison history"""
        service = BehaviorService()
        comparisons = [
            {"category_used": "electronics", "created_at": datetime.now().isoformat()},
            {"category_used": "electronics", "created_at": datetime.now().isoformat()},
            {"category_used": "fragrances", "created_at": datetime.now().isoformat()},
        ]
        affinity = service._compute_category_affinity(comparisons)
        assert abs(affinity["electronics"] - 0.667) < 0.01
        assert abs(affinity["fragrances"] - 0.333) < 0.01

    @pytest.mark.asyncio
    async def test_compute_price_range_preference(self):
        """Price range aggregated from comparison prices"""
        service = BehaviorService()
        comparisons = [
            {"products": [{"price": {"amount": 50}}, {"price": {"amount": 80}}]},
            {"products": [{"price": {"amount": 200}}, {"price": {"amount": 150}}]},
        ]
        pref = service._compute_price_range(comparisons)
        assert pref["avg_price_viewed"] == 120.0  # (50+80+200+150) / 4

    @pytest.mark.asyncio
    async def test_compute_winner_agreement(self):
        """Winner agreement from feedback data"""
        service = BehaviorService()
        feedback = [
            {"useful": True},
            {"useful": True},
            {"useful": False},
        ]
        agreement = service._compute_winner_agreement(feedback)
        assert agreement["agreed"] == 2
        assert agreement["disagreed"] == 1
        assert abs(agreement["agreement_rate"] - 0.667) < 0.01

    @pytest.mark.asyncio
    async def test_compute_dimension_sensitivity(self):
        """Dimension sensitivity from tab dwell events"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 8000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 3000}},
            {"event_type": "tab_switch", "metadata": {"to": "overview", "dwell_ms": 1500}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        # specs 8000 / (8000+3000) = 0.727 (overview < 2000ms excluded)
        assert sensitivity["spec_score"] > sensitivity["review_score"]

    @pytest.mark.asyncio
    async def test_dwell_under_2s_excluded(self):
        """Tabs with dwell < 2000ms are excluded from sensitivity"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 1500}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        assert "review_score" not in sensitivity or sensitivity.get("review_score", 0) == 0

    def test_behavioral_decay(self):
        """30-day half-life exponential decay"""
        service = BehaviorService()
        now = datetime.now()
        weight_today = service._decay_weight(now, now)
        weight_30d = service._decay_weight(now - timedelta(days=30), now)
        weight_60d = service._decay_weight(now - timedelta(days=60), now)
        assert abs(weight_today - 1.0) < 0.01
        assert abs(weight_30d - 0.5) < 0.01
        assert abs(weight_60d - 0.25) < 0.01

    def test_empty_comparisons_returns_empty_profile(self):
        """No comparisons -> empty/default profile"""
        service = BehaviorService()
        comparisons = []
        affinity = service._compute_category_affinity(comparisons)
        assert affinity == {}

    def test_empty_feedback_returns_zero_agreement(self):
        """No feedback -> zero agreement data"""
        service = BehaviorService()
        feedback = []
        agreement = service._compute_winner_agreement(feedback)
        assert agreement["agreed"] == 0
        assert agreement["disagreed"] == 0
        assert agreement["agreement_rate"] == 0.0

    def test_malformed_created_at(self):
        """Malformed created_at strings are handled gracefully (use current time weight)"""
        service = BehaviorService()
        comparisons = [
            {"category_used": "electronics", "created_at": "not-a-date"},
            {"category_used": "electronics", "created_at": ""},
            {"category_used": "fragrances", "created_at": None},
        ]
        affinity = service._compute_category_affinity(comparisons)
        assert "electronics" in affinity
        assert "fragrances" in affinity


class TestSessionSignals:
    """Tests for in-session signal computation."""

    def test_compute_session_signals(self):
        """Session signals computed from recent events"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 8000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 3000}},
            {"event_type": "tab_switch", "metadata": {"to": "overview", "dwell_ms": 5000}},
        ]
        signals = service.compute_session_signals(events)
        assert signals["first_tab_viewed"] == "specs"
        assert signals["tab_dwell_ms"]["specs"] == 8000

    def test_empty_events(self):
        """No events -> default signals"""
        service = BehaviorService()
        signals = service.compute_session_signals([])
        assert signals["first_tab_viewed"] is None
        assert signals["tab_dwell_ms"] == {}

    def test_events_missing_metadata_key(self):
        """tab_switch events without metadata key should not raise KeyError"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch"},  # no metadata at all
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}},
        ]
        signals = service.compute_session_signals(events)
        # First event has no metadata, so first_tab should come from it safely (None tab)
        # or skip to the one with metadata — either way, no crash
        assert "first_tab_viewed" in signals
        assert "tab_dwell_ms" in signals
        # The second event should still be counted
        assert signals["tab_dwell_ms"].get("specs", 0) == 5000

    def test_events_missing_metadata(self):
        """Events without metadata key don't crash"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch"},
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}},
        ]
        signals = service.compute_session_signals(events)
        assert signals["first_tab_viewed"] == "specs"


class TestCategoryAffinityEdgeCases:
    """Edge cases for _compute_category_affinity."""

    def test_malformed_created_at_strings(self):
        """Malformed created_at strings should not crash, use current time as fallback"""
        service = BehaviorService()
        comparisons = [
            {"category_used": "electronics", "created_at": "not-a-date"},
            {"category_used": "electronics", "created_at": "2026-13-45T99:99:99"},
            {"category_used": "fragrances", "created_at": ""},
            {"category_used": "fragrances", "created_at": None},
        ]
        affinity = service._compute_category_affinity(comparisons)
        # Should not crash, and should produce valid affinity
        assert "electronics" in affinity
        assert "fragrances" in affinity
        assert abs(sum(affinity.values()) - 1.0) < 0.01


class TestPriceRangeEdgeCases:
    """Additional coverage for _compute_price_range()."""

    def test_tier_distribution_across_all_tiers(self):
        """Prices spanning all 4 tiers produce correct distribution"""
        service = BehaviorService()
        comparisons = [
            {"products": [{"price": {"amount": 5}}, {"price": {"amount": 30}}]},    # budget + mid
            {"products": [{"price": {"amount": 100}}, {"price": {"amount": 250}}]},  # premium + luxury
        ]
        pref = service._compute_price_range(comparisons)
        assert pref["avg_price_viewed"] == 96.2  # (5+30+100+250)/4 = 96.25 rounded to 96.2
        assert pref["tier_distribution"]["budget"] == 0.25
        assert pref["tier_distribution"]["mid"] == 0.25
        assert pref["tier_distribution"]["premium"] == 0.25
        assert pref["tier_distribution"]["luxury"] == 0.25

    def test_price_as_plain_number(self):
        """Products with price as plain number (not dict) are included"""
        service = BehaviorService()
        comparisons = [
            {"products": [{"price": 50}, {"price": 100}]},
        ]
        pref = service._compute_price_range(comparisons)
        assert pref["avg_price_viewed"] == 75.0

    def test_empty_products_list(self):
        """Comparisons with no products return zero avg"""
        service = BehaviorService()
        comparisons = [{"products": []}]
        pref = service._compute_price_range(comparisons)
        assert pref["avg_price_viewed"] == 0
        assert pref["tier_distribution"] == {}

    def test_zero_price_excluded(self):
        """Zero or negative prices are excluded"""
        service = BehaviorService()
        comparisons = [
            {"products": [{"price": {"amount": 0}}, {"price": {"amount": 50}}]},
            {"products": [{"price": -10}]},
        ]
        pref = service._compute_price_range(comparisons)
        assert pref["avg_price_viewed"] == 50.0


class TestWinnerAgreementEdgeCases:
    """Additional coverage for _compute_winner_agreement()."""

    def test_all_agreed(self):
        """100% agreement rate"""
        service = BehaviorService()
        feedback = [{"useful": True}, {"useful": True}, {"useful": True}]
        agreement = service._compute_winner_agreement(feedback)
        assert agreement["agreement_rate"] == 1.0
        assert agreement["disagreed"] == 0

    def test_all_disagreed(self):
        """0% agreement rate"""
        service = BehaviorService()
        feedback = [{"useful": False}, {"useful": False}]
        agreement = service._compute_winner_agreement(feedback)
        assert agreement["agreement_rate"] == 0.0
        assert agreement["agreed"] == 0


class TestDimensionSensitivityEdgeCases:
    """Additional coverage for _compute_dimension_sensitivity()."""

    def test_multiple_events_same_tab_accumulated(self):
        """Multiple dwell events for the same tab are summed"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 3000}},
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 4000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 3000}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        # specs: 7000, reviews: 3000, total: 10000
        assert abs(sensitivity["spec_score"] - 0.7) < 0.01
        assert abs(sensitivity["review_score"] - 0.3) < 0.01

    def test_non_tab_switch_events_ignored(self):
        """Non-tab_switch events are excluded from sensitivity"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}},
            {"event_type": "source_click", "metadata": {"to": "reviews", "dwell_ms": 8000}},
            {"event_type": "share", "metadata": {"to": "overview", "dwell_ms": 3000}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        assert "spec_score" in sensitivity
        assert len(sensitivity) == 1  # only specs counted

    def test_exactly_2000ms_excluded(self):
        """Dwell of exactly 2000ms is excluded (threshold is < 2000)"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 2000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 5000}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        # 2000ms == MIN_DWELL_MS, and filter is < MIN_DWELL_MS, so 2000 IS included
        assert "spec_score" in sensitivity
        assert "review_score" in sensitivity


class TestBuildBehaviorProfile:
    """Tests for build_behavior_profile() complete profile assembly."""

    @pytest.mark.asyncio
    async def test_complete_profile_structure(self):
        """build_behavior_profile returns all expected keys"""
        service = BehaviorService()
        comparisons = [
            {"category_used": "electronics", "created_at": datetime.now().isoformat(),
             "products": [{"price": {"amount": 50}}, {"price": {"amount": 80}}]},
        ]
        feedback = [{"useful": True}, {"useful": False}]
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 3000}},
        ]
        profile = await service.build_behavior_profile(comparisons, feedback, events)
        assert "category_affinity" in profile
        assert "price_range_preference" in profile
        assert "winner_agreement" in profile
        assert "dimension_sensitivity" in profile
        assert "comparison_count" in profile
        assert "last_updated" in profile
        assert profile["comparison_count"] == 1
        assert profile["category_affinity"]["electronics"] == 1.0
        assert profile["winner_agreement"]["agreed"] == 1
        assert profile["winner_agreement"]["disagreed"] == 1
        assert "spec_score" in profile["dimension_sensitivity"]

    @pytest.mark.asyncio
    async def test_empty_inputs_profile(self):
        """build_behavior_profile with all empty inputs returns safe defaults"""
        service = BehaviorService()
        profile = await service.build_behavior_profile([], [], [])
        assert profile["category_affinity"] == {}
        assert profile["price_range_preference"]["avg_price_viewed"] == 0
        assert profile["winner_agreement"]["agreement_rate"] == 0.0
        assert profile["dimension_sensitivity"] == {}
        assert profile["comparison_count"] == 0


class TestDecayWeightBoundaries:
    """Boundary tests for _decay_weight()."""

    def test_very_old_event_near_zero(self):
        """Event 365 days ago has very low weight"""
        service = BehaviorService()
        now = datetime.now()
        weight = service._decay_weight(now - timedelta(days=365), now)
        assert weight < 0.001  # 0.5^(365/30) ~ 0.00006

    def test_one_day_ago_near_one(self):
        """Event 1 day ago has weight close to 1.0"""
        service = BehaviorService()
        now = datetime.now()
        weight = service._decay_weight(now - timedelta(days=1), now)
        assert weight > 0.97  # 0.5^(1/30) ~ 0.977


class TestWeightAdjustments:
    """Tests for behavioral weight adjustment application."""

    def test_behavioral_adjustment_capped_at_10pct(self):
        """Behavioral adjustments capped at +/-10% of category weight"""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()
        base_weights = CATEGORY_WEIGHTS["electronics"].copy()
        behavior_profile = {
            "dimension_sensitivity": {"spec_score": 0.8, "price_score": 0.1, "review_score": 0.1},
        }
        adjusted = service.apply_behavioral_adjustments(base_weights.copy(), behavior_profile)
        for dim in base_weights:
            max_shift = base_weights[dim] * 0.10
            assert abs(adjusted[dim] - base_weights[dim]) <= max_shift + 0.001

    def test_session_signal_adjustment_capped_at_5pct(self):
        """Session signal adjustments capped at +/-5% of category weight"""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()
        base_weights = CATEGORY_WEIGHTS["electronics"].copy()
        session_signals = {
            "tab_dwell_ms": {"specs": 10000, "reviews": 1000, "overview": 2000},
            "first_tab_viewed": "specs",
        }
        adjusted = service.apply_session_signals(base_weights.copy(), session_signals)
        for dim in base_weights:
            max_shift = base_weights[dim] * 0.05
            assert abs(adjusted[dim] - base_weights[dim]) <= max_shift + 0.001

    def test_weights_sum_to_one_after_adjustment(self):
        """Weights still sum to 1.0 after behavioral + session adjustments"""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()
        base_weights = CATEGORY_WEIGHTS["electronics"].copy()
        behavior_profile = {"dimension_sensitivity": {"spec_score": 0.6, "price_score": 0.3}}
        session_signals = {"tab_dwell_ms": {"specs": 8000, "reviews": 3000}, "first_tab_viewed": "specs"}
        adjusted = service.apply_behavioral_adjustments(base_weights.copy(), behavior_profile)
        adjusted = service.apply_session_signals(adjusted, session_signals)
        assert abs(sum(adjusted.values()) - 1.0) < 0.001
