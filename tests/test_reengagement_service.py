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

Bundle E (2026-05-16) added two outer gates that fire BEFORE the existing
selector logic:
- ENABLE_REENGAGEMENT_PUSHES global kill-switch (fail-closed).
- REENGAGEMENT_CANARY_PERCENT bucket gate (djb2 parity with featureBucket.ts).
The pre-Bundle-E test suite above assumed both gates were absent; the
shared autouse fixture below turns the flag ON for the legacy tests so
they keep passing, and the new TestFlagGate / TestCanaryGate classes
exercise the gates explicitly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _enable_reengagement_flag(monkeypatch):
    """Default: flag ON so legacy detector tests still exercise the path
    they were written for. Tests that need flag-off behaviour use
    monkeypatch.delenv inside the test body."""
    monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
    yield


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


# ============================================
# Bundle E (2026-05-16) — ENABLE_REENGAGEMENT_PUSHES flag gate
# ============================================


class TestFlagGate:
    """Fail-CLOSED: unset/false flag must short-circuit evaluate() to None."""

    @pytest.mark.asyncio
    async def test_flag_unset_returns_none(self, monkeypatch):
        monkeypatch.delenv("ENABLE_REENGAGEMENT_PUSHES", raising=False)
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        # User would otherwise be eligible — the gate must beat the detectors.
        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}
        user = {"id": "u-eligible", "notifications_enabled": True}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload) as mock_insight:
            result = await svc.evaluate(user)
            assert result is None, "flag off must produce no push"
            mock_insight.assert_not_called(), "detectors must not run when flag is off"

    @pytest.mark.asyncio
    async def test_flag_false_string_returns_none(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "false")
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u-eligible", "notifications_enabled": True}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value={"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}):
            result = await svc.evaluate(user)
            assert result is None

    @pytest.mark.asyncio
    async def test_flag_on_with_eligible_user_fires_detectors(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}
        user = {"id": "u-eligible", "notifications_enabled": True}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload):
            result = await svc.evaluate(user)
            assert result is not None
            assert result["event_type"] == "decision_insight"


# ============================================
# Bundle E (2026-05-16) — REENGAGEMENT_CANARY_PERCENT bucket gate
# ============================================


class TestCanaryGate:
    """Canary % gates evaluate() after the flag passes. Deterministic per user_id."""

    @pytest.mark.asyncio
    async def test_canary_zero_percent_blocks_all_users(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
        monkeypatch.setenv("REENGAGEMENT_CANARY_PERCENT", "0")
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload) as mock_insight:
            for i in range(50):
                user = {"id": f"u-{i}", "notifications_enabled": True}
                result = await svc.evaluate(user)
                assert result is None
            mock_insight.assert_not_called(), "canary 0% must short-circuit before detectors"

    @pytest.mark.asyncio
    async def test_canary_100_percent_lets_everyone_through(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
        monkeypatch.setenv("REENGAGEMENT_CANARY_PERCENT", "100")
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload):
            sent = 0
            for i in range(50):
                user = {"id": f"u-{i}", "notifications_enabled": True}
                result = await svc.evaluate(user)
                if result is not None:
                    sent += 1
            assert sent == 50, f"canary 100% should pass all 50 users, got {sent}"

    @pytest.mark.asyncio
    async def test_canary_default_is_100(self, monkeypatch):
        """Unset REENGAGEMENT_CANARY_PERCENT defaults to 100 — flag is the only switch."""
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
        monkeypatch.delenv("REENGAGEMENT_CANARY_PERCENT", raising=False)
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload):
            user = {"id": "u-typical", "notifications_enabled": True}
            result = await svc.evaluate(user)
            assert result is not None

    @pytest.mark.asyncio
    async def test_canary_50_percent_deterministic_per_user(self, monkeypatch):
        """Same user must always land in the same bucket across calls."""
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
        monkeypatch.setenv("REENGAGEMENT_CANARY_PERCENT", "50")
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        insight_payload = {"event_type": "decision_insight", "title": "X", "body": "Y", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload):
            user = {"id": "stable-user-1", "notifications_enabled": True}
            first = await svc.evaluate(user)
            for _ in range(20):
                assert await svc.evaluate(user) == first, "bucket must be stable per user_id"
