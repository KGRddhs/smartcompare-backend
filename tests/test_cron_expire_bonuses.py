"""Tests for plan task 36 — scripts/cron_expire_bonuses.py.

Path-(a) invariant: the cron does NOT mutate any counters.
Entitlement is computed live from referral_redemptions in usage_service
(filtered by expires_at > now() AND consumed_at IS NULL). The cron's
ONLY job is the 24h-before-expiry reminder push.

Contract:
- Finds redemptions with expires_at within next 24h AND consumed_at IS NULL
  AND expiry_reminder_sent_at IS NULL (idempotent — re-running won't re-send).
- Sends Expo push: localized 24h reminder.
- Stamps expiry_reminder_sent_at via UPDATE on referral_redemptions.
- Pagination + cap at 1000 rows per run.

Pattern follows tests/test_cron_reengagement.py + scripts/cron_reengagement.py.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Flip the cron feature flag ON for the test module — production keeps
# it OFF in code default; flipped in Railway during canary.
os.environ["ENABLE_BONUS_EXPIRY_PUSHES"] = "true"


# ============================================
# Module + entrypoint exists
# ============================================


class TestCronExpireBonusesEntrypoint:
    def test_module_importable(self):
        from scripts import cron_expire_bonuses  # noqa: F401

    def test_entrypoint_exists(self):
        from scripts import cron_expire_bonuses

        assert hasattr(cron_expire_bonuses, "main") or hasattr(
            cron_expire_bonuses, "run"
        ), "scripts/cron_expire_bonuses.py must expose main() or run() entrypoint"


# ============================================
# 24h-before-expiry reminder push
# ============================================


class TestExpiryReminderPush:
    @pytest.mark.asyncio
    async def test_queries_referral_redemptions_for_expiring_rows(self):
        """Cron must touch referral_redemptions table to find rows expiring soon."""
        from scripts import cron_expire_bonuses

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        for m in (
            "select", "eq", "gte", "lte", "lt", "gt", "is_", "limit", "order",
            "update", "in_",
        ):
            getattr(mock_table, m).return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        with patch(
            "scripts.cron_expire_bonuses.get_admin_supabase_client",
            return_value=mock_client,
        ):
            entry = (
                getattr(cron_expire_bonuses, "main", None)
                or cron_expire_bonuses.run
            )
            await entry()

        table_args = [c.args[0] for c in mock_client.table.call_args_list]
        assert "referral_redemptions" in table_args, (
            "Cron must query referral_redemptions for expiring rows"
        )

    @pytest.mark.asyncio
    async def test_sends_push_per_expiring_redemption(self):
        from scripts import cron_expire_bonuses

        soon = (datetime.now(timezone.utc) + timedelta(hours=20)).isoformat()
        rows = [
            {
                "id": "red-1",
                "referrer_user_id": "ref-1",
                "invitee_user_id": "inv-1",
                "loop2_comparisons_granted": 5,
                "expires_at": soon,
                "consumed_at": None,
                "expiry_reminder_sent_at": None,
            },
            {
                "id": "red-2",
                "referrer_user_id": "ref-2",
                "invitee_user_id": "inv-2",
                "loop2_comparisons_granted": 10,
                "expires_at": soon,
                "consumed_at": None,
                "expiry_reminder_sent_at": None,
            },
        ]

        push_mock = AsyncMock()
        with patch(
            "scripts.cron_expire_bonuses._fetch_expiring_redemptions",
            new_callable=AsyncMock,
            return_value=rows,
        ), patch(
            "scripts.cron_expire_bonuses.send_push", push_mock,
        ), patch(
            "scripts.cron_expire_bonuses._mark_reminder_sent",
            new_callable=AsyncMock,
        ):
            entry = (
                getattr(cron_expire_bonuses, "main", None)
                or cron_expire_bonuses.run
            )
            await entry()

        assert push_mock.await_count == 2, (
            f"expected one push per row, got {push_mock.await_count}"
        )

    @pytest.mark.asyncio
    async def test_filter_excludes_already_notified_rows(self):
        """STRENGTHENED PER QA F1: assert the DB query filter actually
        applies `.is_("expiry_reminder_sent_at", "null")` — not just that
        push count is zero when the upstream returns []. Without this,
        a future regression that drops the IS NULL filter would pass."""
        from scripts import cron_expire_bonuses

        redemptions_table = MagicMock()
        for m in (
            "select", "eq", "gt", "gte", "lt", "lte", "is_", "limit",
            "order", "update", "in_",
        ):
            getattr(redemptions_table, m).return_value = redemptions_table
        redemptions_table.execute.return_value = MagicMock(data=[])

        client = MagicMock()
        client.table.return_value = redemptions_table

        with patch(
            "scripts.cron_expire_bonuses.get_admin_supabase_client",
            return_value=client,
        ), patch(
            "scripts.cron_expire_bonuses.send_push", new_callable=AsyncMock,
        ):
            entry = (
                getattr(cron_expire_bonuses, "main", None)
                or cron_expire_bonuses.run
            )
            await entry()

        # Assert the IS NULL filter on expiry_reminder_sent_at was applied
        # (not just that no pushes fired — that's trivial when data is []).
        is_null_args = [c.args[0] for c in redemptions_table.is_.call_args_list]
        assert "expiry_reminder_sent_at" in is_null_args, (
            "Cron's fetch query MUST filter `.is_('expiry_reminder_sent_at', 'null')` "
            "to enforce idempotency (plan task 36 invariant). Without this filter, "
            "the cron would re-send pushes on every run."
        )
        # Also assert the consumed_at IS NULL filter (consumed bonuses don't
        # need a reminder).
        assert "consumed_at" in is_null_args, (
            "Cron's fetch query MUST filter `.is_('consumed_at', 'null')` so "
            "consumed bonuses don't trigger a reminder."
        )

    @pytest.mark.asyncio
    async def test_marks_reminder_sent_after_push(self):
        """After sending, cron must stamp expiry_reminder_sent_at to prevent re-send."""
        from scripts import cron_expire_bonuses

        soon = (datetime.now(timezone.utc) + timedelta(hours=20)).isoformat()
        row = {
            "id": "red-1",
            "referrer_user_id": "ref-1",
            "invitee_user_id": "inv-1",
            "loop2_comparisons_granted": 5,
            "expires_at": soon,
            "consumed_at": None,
            "expiry_reminder_sent_at": None,
        }

        mark_mock = AsyncMock()
        with patch(
            "scripts.cron_expire_bonuses._fetch_expiring_redemptions",
            new_callable=AsyncMock,
            return_value=[row],
        ), patch(
            "scripts.cron_expire_bonuses.send_push", new_callable=AsyncMock,
        ), patch(
            "scripts.cron_expire_bonuses._mark_reminder_sent", mark_mock,
        ):
            entry = (
                getattr(cron_expire_bonuses, "main", None)
                or cron_expire_bonuses.run
            )
            await entry()

        assert mark_mock.await_count == 1, (
            "Cron must mark expiry_reminder_sent_at after sending push"
        )


# ============================================
# Pagination cap (defense-in-depth)
# ============================================


class TestCronPaginationCap:
    @pytest.mark.asyncio
    async def test_caps_at_1000_pushes_per_run(self):
        """Contract per QA F3: cap can be at QUERY level (LIMIT 1000) OR
        at LOOP level (break after 1000 pushes). Either way, push count
        per run must be ≤ 1000. We test the OUTPUT bound, not the
        impl path — both are valid."""
        from scripts import cron_expire_bonuses

        large = [
            {
                "id": f"red-{i}",
                "referrer_user_id": f"ref-{i}",
                "invitee_user_id": f"inv-{i}",
                "loop2_comparisons_granted": 5,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=20)
                ).isoformat(),
                "consumed_at": None,
                "expiry_reminder_sent_at": None,
            }
            for i in range(5000)
        ]

        push_mock = AsyncMock()
        with patch(
            "scripts.cron_expire_bonuses._fetch_expiring_redemptions",
            new_callable=AsyncMock,
            return_value=large,
        ), patch(
            "scripts.cron_expire_bonuses.send_push", push_mock,
        ), patch(
            "scripts.cron_expire_bonuses._mark_reminder_sent",
            new_callable=AsyncMock,
        ):
            entry = (
                getattr(cron_expire_bonuses, "main", None)
                or cron_expire_bonuses.run
            )
            await entry()

        assert push_mock.await_count <= 1000, (
            f"Cron must cap at 1000 pushes per run, got {push_mock.await_count}"
        )


# ============================================
# Cron does NOT mutate counters (path-(a) invariant)
# ============================================


class TestCronDoesNotMutateUserCounters:
    """Per team-lead decision: cron sends push only. It MUST NOT touch
    `users.referral_bonus_comparisons_this_month`. usage_service computes
    entitlement live from redemption rows."""

    def test_cron_source_does_not_mutate_users_counter(self):
        import inspect
        from scripts import cron_expire_bonuses

        src = inspect.getsource(cron_expire_bonuses)
        assert "referral_bonus_comparisons_this_month" not in src, (
            "Cron must NOT decrement referral_bonus_comparisons_this_month "
            "(path-(a) invariant: source of truth is referral_redemptions table)"
        )
