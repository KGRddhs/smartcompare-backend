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
