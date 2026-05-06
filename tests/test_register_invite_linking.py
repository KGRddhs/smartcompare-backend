"""Tests for B3.5 — POST /register accepts invite_id and links the row.

After this is in place, the Loop 2 chain finally connects:
  invite created -> invitee signs up with invite_id -> referral_invites
  row gets redeemed_by_user_id -> invitee runs first comparison ->
  try_trigger_loop2 finds the unredeemed row pointing at them -> Loop 2.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLinkInviteToUser:
    """ReferralService.link_invite_to_user(user_id, invite_id) — pure unit tests.

    Param order matches plan B3.5 Step 3: user first, invite second.
    """

    @pytest.mark.asyncio
    async def test_links_unredeemed_invite_to_new_user(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        # invite exists, unredeemed
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "i-1", "redeemed_by_user_id": None, "redeemed_at": None}
        )
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "i-1"}]
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_to_user("user-99", "i-1")

        assert ok is True
        # Update was called with redeemed_by_user_id
        update_payload = client.table.return_value.update.call_args[0][0]
        assert update_payload == {"redeemed_by_user_id": "user-99"}

    @pytest.mark.asyncio
    async def test_skips_already_redeemed_invite(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "i-1", "redeemed_by_user_id": "someone", "redeemed_at": None}
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_to_user("user-99", "i-1")

        assert ok is False
        client.table.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_invite_with_redeemed_at_set(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": "i-1",
                "redeemed_by_user_id": None,
                "redeemed_at": "2026-05-05T10:00:00Z",
            }
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_to_user("user-99", "i-1")

        assert ok is False
        client.table.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_invite_returns_false(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_to_user("user-99", "i-missing")

        assert ok is False

    @pytest.mark.asyncio
    async def test_empty_args_return_false(self):
        from app.services.referral_service import ReferralService

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=MagicMock()):
            svc = ReferralService()
            assert await svc.link_invite_to_user("user-99", "") is False
            assert await svc.link_invite_to_user("", "invite-1") is False
            assert await svc.link_invite_to_user("", "") is False

    @pytest.mark.asyncio
    async def test_db_error_returns_false_no_raise(self):
        """Linker must never propagate exceptions — signup is the priority."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = RuntimeError(
            "supabase down"
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_to_user("user-99", "i-1")

        assert ok is False


class TestRegisterRequestAcceptsInviteId:
    def test_invite_id_accepted_when_provided(self):
        from app.api.auth_routes import RegisterRequest

        req = RegisterRequest(
            email="x@example.com",
            password="ValidPass123!",
            invite_id="00000000-0000-0000-0000-000000000000",
        )
        assert req.invite_id == "00000000-0000-0000-0000-000000000000"

    def test_invite_id_optional(self):
        from app.api.auth_routes import RegisterRequest

        req = RegisterRequest(email="x@example.com", password="ValidPass123!")
        assert req.invite_id is None
