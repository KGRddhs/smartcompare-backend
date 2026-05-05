"""Tests for F2.3 backend support — share privacy block.

ShareRequest accepts an optional ``privacy`` block. resolve_invite reads
``referral_invites.privacy`` and conditions the invitee response:
- show_name=False  -> referrer_display_name = "A friend"
- show_result=False -> drop winner_index / winner from sanitized comparison
- show_reasons=False -> drop verdict + tradeoffs
- show_budget is ALWAYS false (locked off per design 3.3); enforced by
  the existing _strip_personalization helper.

Schema: referral_invites.privacy JSONB, default
``{"show_name": true, "show_result": true, "show_reasons": true}``.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================
# ShareRequest accepts privacy block
# ============================================


class TestShareRequestPrivacyShape:
    """Per must-fix #4: privacy is FLAT on ShareRequest, not nested."""

    def test_default_all_toggles_are_true(self):
        from app.api.referral_routes import ShareRequest

        req = ShareRequest(comparison_id="cmp-1", share_target="whatsapp")
        assert req.show_name is True
        assert req.show_result is True
        assert req.show_reasons is True

    def test_each_toggle_can_be_disabled(self):
        from app.api.referral_routes import ShareRequest

        req = ShareRequest(
            comparison_id="cmp-1",
            share_target="whatsapp",
            show_name=False,
            show_result=False,
            show_reasons=False,
        )
        assert req.show_name is False
        assert req.show_result is False
        assert req.show_reasons is False

    def test_show_budget_field_rejected(self):
        """show_budget is locked off per design 3.3 + PDF #8 — extra='forbid'
        on ShareRequest rejects malicious clients trying to send it."""
        from app.api.referral_routes import ShareRequest

        with pytest.raises(Exception):  # ValidationError or ValueError
            ShareRequest(
                comparison_id="cmp-1",
                share_target="whatsapp",
                show_budget=True,
            )


# ============================================
# resolve_invite honors privacy block
# ============================================


class TestResolveInviteHonorsPrivacy:
    """When privacy fields are False, the invitee view must hide them."""

    @pytest.mark.asyncio
    async def test_show_name_false_returns_a_friend(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        # rpc returns referrer
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref-1", "display_name": "Ahmed"}]
        )
        # comparison lookup
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": "cmp-1",
                "user_id": "ref-1",
                "share_token": "tok",
                "response_data": {
                    "products": [{"name": "iPhone"}, {"name": "Galaxy"}],
                    "winner": {"name": "iPhone"},
                    "winner_index": 0,
                    "verdict": "Decisive iPhone win",
                    "comparison": {"recommendation": "Buy iPhone"},
                    "key_differences": ["Camera", "Battery"],
                },
            }
        )
        # invite row with show_name=False
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "inv-1",
                    "first_viewed_at": "2026-05-05T10:00:00Z",
                    "privacy": {"show_name": False, "show_result": True, "show_reasons": True},
                }
            ]
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="tok", ref_code="QR-AHMED1")

        assert result is not None
        assert result["referrer_display_name"] == "A friend", (
            "show_name=False must mask referrer's name"
        )

    @pytest.mark.asyncio
    async def test_show_result_false_drops_winner(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref", "display_name": "Sarah"}]
        )
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": "c",
                "user_id": "ref",
                "share_token": "tok",
                "response_data": {
                    "products": [{"name": "A"}, {"name": "B"}],
                    "winner": {"name": "A"},
                    "winner_index": 0,
                    "verdict": "A wins",
                },
            }
        )
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "i",
                    "first_viewed_at": "2026-05-05T10:00:00Z",
                    "privacy": {"show_name": True, "show_result": False, "show_reasons": True},
                }
            ]
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="tok", ref_code="QR-SARAH1")

        assert result is not None
        comparison = result["comparison"]
        assert "winner" not in comparison, "show_result=False must drop winner"
        assert "winner_index" not in comparison, "show_result=False must drop winner_index"

    @pytest.mark.asyncio
    async def test_show_reasons_false_drops_verdict_and_tradeoffs(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref", "display_name": "X"}]
        )
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": "c",
                "user_id": "ref",
                "share_token": "tok",
                "response_data": {
                    "products": [{"name": "A"}, {"name": "B"}],
                    "winner": {"name": "A"},
                    "verdict": "Detailed verdict prose here",
                    "comparison": {"recommendation": "Buy A", "tradeoffs": "B is cheaper"},
                    "key_differences": ["Price", "Camera"],
                },
            }
        )
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "i",
                    "first_viewed_at": "2026-05-05T10:00:00Z",
                    "privacy": {"show_name": True, "show_result": True, "show_reasons": False},
                }
            ]
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="tok", ref_code="QR-X")

        assert result is not None
        comparison = result["comparison"]
        assert "verdict" not in comparison, "show_reasons=False must drop verdict"
        assert "key_differences" not in comparison, "show_reasons=False must drop key_differences"

    @pytest.mark.asyncio
    async def test_default_privacy_keeps_everything_visible(self):
        """Backwards compat: invites without privacy field (or with all True)
        keep current behavior — referrer name + winner + verdict visible."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref", "display_name": "Mark"}]
        )
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": "c",
                "user_id": "ref",
                "share_token": "tok",
                "response_data": {
                    "products": [{"name": "A"}],
                    "winner": {"name": "A"},
                    "verdict": "A wins",
                },
            }
        )
        # No privacy field on the invite row (legacy or default)
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "i", "first_viewed_at": "2026-05-05T10:00:00Z"}]
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="tok", ref_code="QR-MARK1")

        assert result is not None
        assert result["referrer_display_name"] == "Mark"
        assert "winner" in result["comparison"]
        assert "verdict" in result["comparison"]


# ============================================
# create_invite persists the privacy block
# ============================================


class TestCreateInvitePersistsPrivacy:
    @pytest.mark.asyncio
    async def test_share_endpoint_passes_privacy_to_service(self):
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-1", "email": "u@t.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user

        captured = {}

        async def fake_create_invite(**kwargs):
            captured.update(kwargs)
            return {
                "invite_id": "i-1",
                "referrer_user_id": "user-1",
                "share_link": "https://qaren.app/c/tok?ref=QR-X",
                "share_token": "tok",
                "referral_code": "QR-X",
                "weekly_invites_used": 1,
                "weekly_invites_remaining": 2,
            }

        try:
            with patch("app.api.referral_routes.ReferralService") as MockSvc:
                MockSvc.return_value.create_invite = AsyncMock(side_effect=fake_create_invite)

                resp = client.post(
                    "/api/v1/referrals/share",
                    json={
                        "comparison_id": "00000000-0000-0000-0000-000000000000",
                        "share_target": "whatsapp",
                        "show_name": False,
                        "show_result": True,
                        "show_reasons": False,
                    },
                    headers={"Authorization": "Bearer tok"},
                )
                assert resp.status_code == 201, resp.text
                # Service must receive the 3 flat kwargs after must-fix #4
                assert captured.get("show_name") is False
                assert captured.get("show_result") is True
                assert captured.get("show_reasons") is False
        finally:
            app.dependency_overrides.clear()
