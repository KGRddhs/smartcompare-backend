"""Tests for B5.2 — ReengagementService selector + 3 detectors.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
section 3.9 + plan task B5.2.

Selector logic (max 1/week per user):
  IF saved-product sentiment shifted ≥10% in last 7d → 'decision_insight'
  ELIF cohort_divergence(governorate) ≥ 5 users + 40% picked differently → 'cohort_curiosity'
  ELIF comparison.created_at == 14d ago AND no retrospective sent → 'decision_retrospective'
  ELSE skip

Cost guards:
- decision_insight: only check products in top-100 globally most-saved
- 7-day cap is HARD — never violated
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# B5.2 — class shape
# ============================================


class TestReengagementServiceShape:
    def test_class_importable(self):
        from app.services.reengagement_service import ReengagementService  # noqa: F401

    def test_has_required_methods(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        for method in (
            "evaluate",
            "_check_decision_insight",
            "_check_cohort_curiosity",
            "_check_decision_retrospective",
            "_recent_push",
        ):
            assert hasattr(svc, method), f"missing method: {method}"


# ============================================
# 7-day cap (hard requirement)
# ============================================


class TestSevenDayCap:
    """No user gets more than 1 push per 7-day window."""

    @pytest.mark.asyncio
    async def test_recent_push_within_7d_returns_none(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u1", "notifications_enabled": True}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=True), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock) as mock_insight:
            result = await svc.evaluate(user)
            assert result is None
            # Detectors should NOT be called once 7d cap is hit
            mock_insight.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_recent_push_runs_detectors(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u2", "notifications_enabled": True}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=None) as mock_insight, \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock, return_value=None), \
             patch.object(svc, "_check_decision_retrospective", new_callable=AsyncMock, return_value=None):
            await svc.evaluate(user)
            mock_insight.assert_called_once()


# ============================================
# Selector priority order
# ============================================


class TestSelectorPriority:
    """When multiple detectors fire, decision_insight wins, then cohort, then retrospective."""

    @pytest.mark.asyncio
    async def test_decision_insight_wins_over_cohort(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "notifications_enabled": True}

        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}
        cohort_payload = {"event_type": "cohort_curiosity", "title": "A", "body": "B", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload), \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock, return_value=cohort_payload):
            result = await svc.evaluate(user)
            assert result is not None
            assert result["event_type"] == "decision_insight"

    @pytest.mark.asyncio
    async def test_cohort_wins_over_retrospective_when_insight_skips(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "notifications_enabled": True}

        cohort_payload = {"event_type": "cohort_curiosity", "title": "A", "body": "B", "deep_link_url": "u://"}
        retro_payload = {"event_type": "decision_retrospective", "title": "C", "body": "D", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=None), \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock, return_value=cohort_payload), \
             patch.object(svc, "_check_decision_retrospective", new_callable=AsyncMock, return_value=retro_payload):
            result = await svc.evaluate(user)
            assert result["event_type"] == "cohort_curiosity"

    @pytest.mark.asyncio
    async def test_no_detectors_fire_returns_none(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "notifications_enabled": True}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=None), \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock, return_value=None), \
             patch.object(svc, "_check_decision_retrospective", new_callable=AsyncMock, return_value=None):
            result = await svc.evaluate(user)
            assert result is None


# ============================================
# Decision Insight detector
# ============================================


class TestDecisionInsightDetector:
    @pytest.mark.asyncio
    async def test_sentiment_shift_above_10pct_fires(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "saved_products": [{"id": "iphone-15", "last_sentiment": 0.50}]}

        # Patch internal helpers
        with patch.object(svc, "_get_user_saved_products", new_callable=AsyncMock, return_value=user["saved_products"]), \
             patch.object(svc, "_get_top_100_saved_globally", new_callable=AsyncMock, return_value={"iphone-15"}), \
             patch.object(svc, "_compute_current_sentiment", new_callable=AsyncMock, return_value=0.65):  # 15% shift

            result = await svc._check_decision_insight(user)
            assert result is not None
            assert result["event_type"] == "decision_insight"

    @pytest.mark.asyncio
    async def test_sentiment_shift_below_10pct_does_not_fire(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "saved_products": [{"id": "p1", "last_sentiment": 0.50}]}

        with patch.object(svc, "_get_user_saved_products", new_callable=AsyncMock, return_value=user["saved_products"]), \
             patch.object(svc, "_get_top_100_saved_globally", new_callable=AsyncMock, return_value={"p1"}), \
             patch.object(svc, "_compute_current_sentiment", new_callable=AsyncMock, return_value=0.55):  # 5% shift

            result = await svc._check_decision_insight(user)
            assert result is None

    @pytest.mark.asyncio
    async def test_product_not_in_top_100_skipped(self):
        """COST GUARD: skip products not in global top-100."""
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "saved_products": [{"id": "obscure-product", "last_sentiment": 0.50}]}

        with patch.object(svc, "_get_user_saved_products", new_callable=AsyncMock, return_value=user["saved_products"]), \
             patch.object(svc, "_get_top_100_saved_globally", new_callable=AsyncMock, return_value={"iphone-15", "galaxy-s24"}), \
             patch.object(svc, "_compute_current_sentiment", new_callable=AsyncMock) as mock_compute:

            result = await svc._check_decision_insight(user)
            assert result is None
            # _compute_current_sentiment should NOT be called for non-top-100 products
            mock_compute.assert_not_called()


# ============================================
# Cohort Curiosity detector
# ============================================


class TestCohortCuriosityDetector:
    @pytest.mark.asyncio
    async def test_5_users_40pct_diff_fires(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "governorate": "Capital", "recent_comparisons": [{"id": "c1", "winner": "A"}]}

        with patch.object(svc, "_count_cohort_divergence", new_callable=AsyncMock, return_value={"users": 6, "divergence_pct": 0.45}):
            result = await svc._check_cohort_curiosity(user)
            assert result is not None
            assert result["event_type"] == "cohort_curiosity"

    @pytest.mark.asyncio
    async def test_below_threshold_does_not_fire(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u", "governorate": "Capital", "recent_comparisons": [{"id": "c1", "winner": "A"}]}

        with patch.object(svc, "_count_cohort_divergence", new_callable=AsyncMock, return_value={"users": 3, "divergence_pct": 0.30}):
            result = await svc._check_cohort_curiosity(user)
            assert result is None


# ============================================
# Decision Retrospective detector
# ============================================


class TestDecisionRetrospectiveDetector:
    @pytest.mark.asyncio
    async def test_14_days_old_comparison_fires(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u"}
        # Comparison from exactly 14 days ago with no retrospective sent yet
        with patch.object(svc, "_find_14d_comparison_no_retrospective", new_callable=AsyncMock, return_value={"id": "c14", "products": [{"name": "iPhone"}]}):
            result = await svc._check_decision_retrospective(user)
            assert result is not None
            assert result["event_type"] == "decision_retrospective"

    @pytest.mark.asyncio
    async def test_no_eligible_comparison_does_not_fire(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u"}
        with patch.object(svc, "_find_14d_comparison_no_retrospective", new_callable=AsyncMock, return_value=None):
            result = await svc._check_decision_retrospective(user)
            assert result is None
