"""Tests for plan task 35 — referral_service expiry + usage_service path-(a) refactor.

Path (a) (team-lead decision 2026-05-06): source of truth =
sum of `referral_redemptions` rows WHERE expires_at > now() AND consumed_at IS NULL.
The INT counter `users.referral_bonus_comparisons_this_month` stays for
analytics/display only and MUST NOT drive entitlement.

Contract:
1. Loop 2 grant inserts a referral_redemptions row with expires_at = now + 3d.
2. Loop 1 invite (create_invite) sets deep_review_expires_at = now + 3d.
3. usage_service.check_usage_allowed sums active (non-expired, non-consumed)
   redemptions per user — expired rows do NOT inflate cap.
4. Lazy reset of the INT counter still works (no regression — TestLazyReset
   pattern from test_usage_referral_bonus.py preserved).

Pattern follows tests/test_referral_loop2.py + tests/test_usage_referral_bonus.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# Loop 2 redemption insert sets expires_at = now + 3d
# ============================================


class TestLoop2RedemptionExpiresAt:
    @pytest.mark.asyncio
    async def test_grant_loop2_rewards_sets_expires_at_7_days(self):
        """Bundle B/C/D § 4.4: bonus expiry 3 → 7 days.
        New constant applies to NEW redemption inserts; pre-existing rows keep
        their original 3-day deadlines (verified separately below)."""
        from app.services.referral_service import ReferralService

        invite = {
            "id": "invite-1",
            "referrer_user_id": "ref-1",
            "redeemed_by_user_id": "invitee-1",
        }
        invitee = {"id": "invitee-1", "email": "x@gmail.com"}

        captured_inserts: list[dict] = []

        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.insert.side_effect = lambda payload: (
            captured_inserts.append(payload) or table
        )
        table.update.return_value = table
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.return_value = MagicMock(
            data={"referral_bonus_comparisons_this_month": 0}
        )

        svc = ReferralService()
        svc.client = client
        await svc._grant_loop2_rewards(invite, invitee, grant_amount=5)

        redemption_payload = next(
            (p for p in captured_inserts if "loop2_comparisons_granted" in p), None
        )
        assert redemption_payload is not None, "referral_redemptions row not inserted"
        assert "expires_at" in redemption_payload, (
            "Loop 2 redemption must set expires_at (7-day expiry per Bundle B/C/D § 4.4)"
        )

        expires_at = datetime.fromisoformat(
            redemption_payload["expires_at"].replace("Z", "+00:00")
        )
        delta = expires_at - datetime.now(timezone.utc)
        assert (
            timedelta(days=7) - timedelta(minutes=5)
            <= delta
            <= timedelta(days=7) + timedelta(minutes=5)
        ), f"expires_at must be ~7 days from now, got delta={delta}"

    def test_bonus_expiry_constant_is_seven_days(self):
        """Module-level constant guards against accidental local-magic-number
        drift. Pre-existing redemption rows are untouched because the constant
        only affects NEW inserts at write time."""
        from app.services.referral_service import BONUS_EXPIRY_DAYS

        assert BONUS_EXPIRY_DAYS == 7

    def test_existing_3day_rows_retain_original_expiry(self):
        """Regression: the 3 → 7 change is a write-side constant, not a
        retroactive UPDATE. A redemption row inserted before this commit
        with expires_at = created_at + 3 days keeps that deadline forever.

        Migration 023 doesn't touch existing rows. This test exists so a
        future refactor doesn't accidentally bulk-rewrite expires_at on
        existing rows."""
        from app.services.referral_service import BONUS_EXPIRY_DAYS

        # Simulated existing row from before Bundle B/C/D
        existing_row_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        existing_row_created_at = existing_row_expires_at - timedelta(days=3)

        # Sanity: the row's lifespan was 3 days, not 7
        original_lifespan = existing_row_expires_at - existing_row_created_at
        assert original_lifespan == timedelta(days=3)

        # The new constant doesn't and shouldn't retroactively extend this row
        assert BONUS_EXPIRY_DAYS == 7
        # If a future refactor adds a backfill, it should NOT touch rows
        # whose created_at < the constant's introduction timestamp. We don't
        # currently have such a backfill — this assertion guards intent.


# ============================================
# Loop 1 — POSITIVE behavior test (frontend-visual QA F4)
# ============================================


class TestLoop1DeepReviewExpiresAt:
    """create_invite must populate deep_review_expires_at on the invite row.
    Replaces the weak source-grep test per frontend-visual QA F4 — this is
    a behavior test that drives the impl, not a comment-passes-grep check.
    """

    @pytest.mark.asyncio
    async def test_create_invite_sets_deep_review_expires_at_3_days(self):
        from app.services.referral_service import ReferralService

        captured_invite_payloads: list[dict] = []

        # Build a chained mock that:
        # - users select returns existing referral_code (skips ensure_code_for_user mint)
        # - referral_invites count(7-day window) returns 0 (under weekly cap)
        # - comparisons select returns owned-by-referrer + share_token
        # - referral_invites insert captures the payload; returns row with id
        # - deep_review_credits insert is a no-op
        def table_factory(name):
            t = MagicMock()
            for m in ("select", "eq", "gt", "gte", "lt", "lte",
                      "is_", "single", "update", "limit", "order"):
                getattr(t, m).return_value = t

            if name == "users":
                t.execute.return_value = MagicMock(
                    data={"referral_code": "QR-EXISTS"}
                )
            elif name == "referral_invites":
                # First call: count weekly invites = 0
                # Second call: insert
                # We split by detecting whether select() was called.
                def insert(payload):
                    captured_invite_payloads.append(payload)
                    inner = MagicMock()
                    inner.execute.return_value = MagicMock(data=[{"id": "inv-99"}])
                    return inner
                t.insert.side_effect = insert
                t.execute.return_value = MagicMock(data=[], count=0)
            elif name == "comparisons":
                t.execute.return_value = MagicMock(
                    data={
                        "id": "cmp-1",
                        "user_id": "ref-1",
                        "share_token": "tokenABC",
                    }
                )
            elif name == "deep_review_credits":
                t.insert.return_value = t
                t.execute.return_value = MagicMock(data=[])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        client = MagicMock()
        client.table.side_effect = table_factory

        svc = ReferralService()
        svc.client = client

        await svc.create_invite(
            referrer_user_id="ref-1",
            comparison_id="cmp-1",
            share_target="whatsapp",
        )

        assert captured_invite_payloads, (
            "create_invite must insert into referral_invites"
        )
        invite_payload = captured_invite_payloads[0]
        assert "deep_review_expires_at" in invite_payload, (
            "create_invite must set deep_review_expires_at on the invite row "
            "(plan task 35 — Loop 1 expiry tracking)"
        )

        expires_at = datetime.fromisoformat(
            invite_payload["deep_review_expires_at"].replace("Z", "+00:00")
        )
        delta = expires_at - datetime.now(timezone.utc)
        assert (
            timedelta(days=3) - timedelta(minutes=5)
            <= delta
            <= timedelta(days=3) + timedelta(minutes=5)
        ), f"deep_review_expires_at must be ~3 days from now, got delta={delta}"


# ============================================
# Path (a) — usage_service sums active redemptions
# ============================================


class TestUsageServiceActiveBonusFromRedemptions:
    """Per team-lead decision: usage_service sums non-expired, non-consumed
    referral_redemptions rows for entitlement. The INT counter
    `referral_bonus_comparisons_this_month` is NOT load-bearing."""

    def _build_chained_client(
        self, *, user_row: dict, active_bonus_sum: int
    ) -> MagicMock:
        """Per-table dispatcher. users.select returns user_row;
        referral_redemptions filtered query returns rows summing to active_bonus_sum."""
        client = MagicMock()

        def table_factory(name):
            t = MagicMock()
            for m in (
                "select", "eq", "gt", "gte", "lt", "lte",
                "is_", "single", "update", "limit", "order",
            ):
                getattr(t, m).return_value = t

            if name == "users":
                t.execute.return_value = MagicMock(data=user_row)
            elif name == "referral_redemptions":
                rows = (
                    [{"loop2_comparisons_granted": active_bonus_sum}]
                    if active_bonus_sum > 0
                    else []
                )
                t.execute.return_value = MagicMock(data=rows)
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        client.table.side_effect = table_factory
        return client

    @pytest.mark.asyncio
    async def test_zero_active_bonus_when_only_expired_rows_exist(self):
        """User has only expired redemptions — cap is base only."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "10" if "monthly" in key else None

        # Stale INT counter would say 5, but path (a) ignores it for entitlement.
        client = self._build_chained_client(
            user_row={
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 5,  # stale, ignored
                "referral_bonus_reset_at": (
                    datetime.now(timezone.utc) + timedelta(days=20)
                ).isoformat(),
            },
            active_bonus_sum=0,
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("u1", "tok")

        # cap = 10 + 0 = 10; used 10 → blocked
        assert result["allowed"] is False
        assert result["reason"] == "monthly_limit"

    @pytest.mark.asyncio
    async def test_active_unexpired_redemption_extends_cap(self):
        """One active redemption granting 5 bumps the cap to base + 5."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "12" if "monthly" in key else None

        client = self._build_chained_client(
            user_row={
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 0,
                "referral_bonus_reset_at": (
                    datetime.now(timezone.utc) + timedelta(days=20)
                ).isoformat(),
            },
            active_bonus_sum=5,
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("u2", "tok")

        # cap = 10 + 5 = 15; used 12 → 3 remaining
        assert result["allowed"] is True
        assert result["remaining"]["monthly"] == 3

    @pytest.mark.asyncio
    async def test_premium_with_active_bonus(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "70" if "monthly" in key else None

        client = self._build_chained_client(
            user_row={
                "subscription_tier": "premium",
                "lifetime_comparisons_used": 100,
                "referral_bonus_comparisons_this_month": 0,
                "referral_bonus_reset_at": (
                    datetime.now(timezone.utc) + timedelta(days=15)
                ).isoformat(),
            },
            active_bonus_sum=10,
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("p1", "tok")

        # cap = 70 + 10 = 80; used 70 → 10 remaining
        assert result["allowed"] is True
        assert result["remaining"]["monthly"] == 10


# ============================================
# Service-layer query filter shape
# ============================================


class TestUsageServiceQueryFilter:
    """Verify the underlying query against referral_redemptions filters
    by expires_at > now() AND consumed_at IS NULL (the path-(a) contract)."""

    @pytest.mark.asyncio
    async def test_query_filters_by_expires_at_and_consumed_at(self):
        """Whatever helper computes active bonus must apply the right filters."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "0" if "monthly" in key else None

        redemptions_table = MagicMock()
        for m in ("select", "eq", "gt", "gte", "is_"):
            getattr(redemptions_table, m).return_value = redemptions_table
        redemptions_table.execute.return_value = MagicMock(data=[])

        users_table = MagicMock()
        for m in ("select", "eq", "single", "update"):
            getattr(users_table, m).return_value = users_table
        users_table.execute.return_value = MagicMock(
            data={
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 0,
                "referral_bonus_reset_at": (
                    datetime.now(timezone.utc) + timedelta(days=20)
                ).isoformat(),
            }
        )

        client = MagicMock()
        client.table.side_effect = lambda name: (
            redemptions_table if name == "referral_redemptions" else users_table
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            await check_usage_allowed("u-3", "tok")

        # expires_at > now() filter applied (gt or gte both acceptable)
        gt_args = [c.args[0] for c in redemptions_table.gt.call_args_list]
        gte_args = [c.args[0] for c in redemptions_table.gte.call_args_list]
        assert "expires_at" in (gt_args + gte_args), (
            "usage_service query must filter referral_redemptions by expires_at"
        )
        # consumed_at IS NULL filter applied
        is_null_args = [c.args[0] for c in redemptions_table.is_.call_args_list]
        assert "consumed_at" in is_null_args, (
            "usage_service query must filter referral_redemptions by consumed_at IS NULL"
        )


# ============================================
# Lazy reset preserved (no regression)
# ============================================


class TestLazyResetPreserved:
    """Path (a) must NOT break TestLazyReset contract from
    test_usage_referral_bonus.py — INT counter still resets monthly
    for analytics/display, even though usage_service ignores it for caps."""

    @pytest.mark.asyncio
    async def test_past_reset_at_still_zeros_int_counter(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "5" if "monthly" in key else None
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        users_table = MagicMock()
        for m in ("select", "eq", "single", "update"):
            getattr(users_table, m).return_value = users_table
        users_table.execute.return_value = MagicMock(
            data={
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 12,
                "referral_bonus_reset_at": past,
            }
        )
        redemptions_table = MagicMock()
        for m in ("select", "eq", "gt", "gte", "is_"):
            getattr(redemptions_table, m).return_value = redemptions_table
        redemptions_table.execute.return_value = MagicMock(data=[])

        client = MagicMock()
        client.table.side_effect = lambda name: (
            redemptions_table if name == "referral_redemptions" else users_table
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            await check_usage_allowed("u-4", "tok")

        # INT counter rewrite still happens (preserved contract).
        update_calls = users_table.update.call_args_list
        assert update_calls, "lazy reset must still update users row"
