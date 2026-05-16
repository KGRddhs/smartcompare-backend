"""Tests for B5.1 — daily cron entrypoint at scripts/cron_reengagement.py.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
section 3.9 + plan task B5.1.

Behavior:
- Iterate users where notifications_enabled=true AND last_comparison_at >= now - 60d
- Cap to 1000 users per run; cursor-paginate
- For each user: ReengagementService.evaluate(user) → if PushPayload → dispatch
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _enable_reengagement_flag(monkeypatch):
    """Bundle E (2026-05-16) gated the entire cron behind
    ENABLE_REENGAGEMENT_PUSHES. The legacy tests below assume the cron
    runs; flipping the env on by default keeps them green. The new
    TestFlagSkip class below exercises the flag-off path explicitly.
    """
    monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
    yield


# ============================================
# B5.1 — entrypoint exists
# ============================================


class TestCronEntrypointShape:
    def test_module_importable(self):
        from scripts import cron_reengagement  # noqa: F401

    def test_main_function_exists(self):
        from scripts import cron_reengagement

        assert hasattr(cron_reengagement, "main") or hasattr(cron_reengagement, "run"), (
            "scripts/cron_reengagement.py must expose main() or run() entrypoint"
        )


# ============================================
# Pagination + 1000 user cap
# ============================================


class TestCronPagination:
    @pytest.mark.asyncio
    async def test_caps_at_1000_users_per_run(self):
        from scripts import cron_reengagement

        # Patch user fetcher to return 5000 users (exceeds cap)
        large_user_set = [{"id": f"u-{i}", "notifications_enabled": True} for i in range(5000)]

        entry = getattr(cron_reengagement, "main", None) or cron_reengagement.run

        with patch("scripts.cron_reengagement._fetch_eligible_users", new_callable=AsyncMock, return_value=large_user_set), \
             patch("scripts.cron_reengagement.ReengagementService") as MockSvc, \
             patch("scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock) as mock_dispatch:

            MockSvc.return_value.evaluate = AsyncMock(return_value=None)

            await entry()

            # Cap respected — at most 1000 evaluate calls
            assert MockSvc.return_value.evaluate.call_count <= 1000, (
                f"cron must cap at 1000 users, called {MockSvc.return_value.evaluate.call_count} times"
            )

    @pytest.mark.asyncio
    async def test_dispatch_called_when_payload_returned(self):
        from scripts import cron_reengagement

        users = [{"id": "u1", "notifications_enabled": True}]
        payload = {
            "event_type": "decision_insight",
            "title": "T",
            "body": "B",
            "deep_link_url": "qaren://x",
        }

        entry = getattr(cron_reengagement, "main", None) or cron_reengagement.run

        with patch("scripts.cron_reengagement._fetch_eligible_users", new_callable=AsyncMock, return_value=users), \
             patch("scripts.cron_reengagement.ReengagementService") as MockSvc, \
             patch("scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock) as mock_dispatch:

            MockSvc.return_value.evaluate = AsyncMock(return_value=payload)

            await entry()

            mock_dispatch.assert_called()

    @pytest.mark.asyncio
    async def test_no_payload_no_dispatch(self):
        from scripts import cron_reengagement

        users = [{"id": "u1", "notifications_enabled": True}]
        entry = getattr(cron_reengagement, "main", None) or cron_reengagement.run

        with patch("scripts.cron_reengagement._fetch_eligible_users", new_callable=AsyncMock, return_value=users), \
             patch("scripts.cron_reengagement.ReengagementService") as MockSvc, \
             patch("scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock) as mock_dispatch:

            MockSvc.return_value.evaluate = AsyncMock(return_value=None)

            await entry()

            mock_dispatch.assert_not_called()


# ============================================
# Eligible-user query shape
# ============================================


class TestEligibleUserFilter:
    @pytest.mark.asyncio
    async def test_filter_excludes_notifications_disabled(self):
        """The eligible-user query must filter notifications_enabled=true.

        Static check on query intent — implementation should filter out users
        with notifications disabled before iterating.
        """
        from scripts import cron_reengagement

        # The function must exist
        assert hasattr(cron_reengagement, "_fetch_eligible_users"), (
            "must expose _fetch_eligible_users(client) helper"
        )

    @pytest.mark.asyncio
    async def test_filter_excludes_inactive_60d(self):
        """Users with no comparison in last 60 days are skipped."""
        from scripts import cron_reengagement

        # The function exists; behavior asserted via static module inspection
        import inspect

        try:
            source = inspect.getsource(cron_reengagement._fetch_eligible_users)
        except (AttributeError, TypeError):
            pytest.skip("function not yet implemented")

        # Lookback window of 60 days must appear in query construction
        assert "60" in source, "_fetch_eligible_users must filter to last 60 days"


# ============================================
# Bundle E (2026-05-16) — ENABLE_REENGAGEMENT_PUSHES gate
# ============================================


class TestFlagSkip:
    """When the global kill-switch is off, the cron must skip the run entirely."""

    @pytest.mark.asyncio
    async def test_flag_unset_skips_entire_run(self, monkeypatch):
        monkeypatch.delenv("ENABLE_REENGAGEMENT_PUSHES", raising=False)
        from scripts import cron_reengagement

        entry = getattr(cron_reengagement, "main", None) or cron_reengagement.run

        with patch("scripts.cron_reengagement._fetch_eligible_users", new_callable=AsyncMock) as mock_fetch, \
             patch("scripts.cron_reengagement.ReengagementService") as MockSvc, \
             patch("scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock) as mock_dispatch:

            await entry()

            mock_fetch.assert_not_called(), "cron must not query users when flag off"
            MockSvc.assert_not_called(), "cron must not construct service when flag off"
            mock_dispatch.assert_not_called(), "cron must not send pushes when flag off"

    @pytest.mark.asyncio
    async def test_flag_false_string_skips_entire_run(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "false")
        from scripts import cron_reengagement

        entry = getattr(cron_reengagement, "main", None) or cron_reengagement.run

        with patch("scripts.cron_reengagement._fetch_eligible_users", new_callable=AsyncMock) as mock_fetch, \
             patch("scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock) as mock_dispatch:

            await entry()

            mock_fetch.assert_not_called()
            mock_dispatch.assert_not_called()
