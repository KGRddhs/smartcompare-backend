"""Tests for Phase 2 / Task 2.1 — lifetime device-bound invite cap.

Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.2 + § 4.7
Plan: docs/plans/2026-05-12-bundle-bcd-consolidated.md § Task 2.1

Cap shape:
  - 3 LIFETIME successful referrals per device fingerprint (not per user).
  - Enforced inside ``ReferralService.try_trigger_loop2`` BEFORE grant.
  - Aggregation: ``SUM(lifetime_invites_consumed) FROM users WHERE
    device_fingerprint_hash = referrer.device_fingerprint_hash``.
  - A bad actor who logs out and creates a fresh account on the same phone
    still hits the same 3 cap because the SUM is keyed on device, not user.

Implementation contract:
  - ``LIFETIME_CAP = 3`` module-level constant in referral_service.
  - New helper ``_referrer_device_lifetime_count(referrer_user_id) -> int``
    returns the aggregated count for the referrer's device (0 if the
    referrer has no fingerprint — fail-OPEN since pre-fingerprint users
    were grandfathered in by Bundle A Migration 021).
  - ``try_trigger_loop2`` short-circuits with no reward when count ≥ cap.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLifetimeCapConstant:
    def test_lifetime_cap_constant_is_three(self):
        from app.services.referral_service import LIFETIME_CAP

        assert LIFETIME_CAP == 3


class TestReferrerDeviceLifetimeCountHelper:
    """Helper aggregates lifetime_invites_consumed across all users sharing
    the referrer's device_fingerprint_hash."""

    @pytest.mark.asyncio
    async def test_aggregates_across_users_on_same_device(self):
        from app.services.referral_service import ReferralService

        svc = ReferralService()

        # The impl calls .table("users") twice — once for the referrer
        # fingerprint lookup, then once to aggregate. Each call returns a
        # fresh chain whose .execute() yields the appropriate response.
        referrer_resp = MagicMock(data={"device_fingerprint_hash": "device-abc"})
        sum_resp = MagicMock(data=[
            {"lifetime_invites_consumed": 2},
            {"lifetime_invites_consumed": 1},
        ])

        chain_referrer = MagicMock()
        chain_referrer.select.return_value = chain_referrer
        chain_referrer.eq.return_value = chain_referrer
        chain_referrer.single.return_value = chain_referrer
        chain_referrer.execute.return_value = referrer_resp

        chain_agg = MagicMock()
        chain_agg.select.return_value = chain_agg
        chain_agg.eq.return_value = chain_agg
        chain_agg.execute.return_value = sum_resp

        mock_client = MagicMock()
        mock_client.table.side_effect = [chain_referrer, chain_agg]
        svc.client = mock_client

        count = await svc._referrer_device_lifetime_count("referrer-1")
        assert count == 3

    @pytest.mark.asyncio
    async def test_returns_zero_when_referrer_has_no_fingerprint(self):
        """Pre-fingerprint users (Bundle A grandfathering) fail OPEN — they
        can still send invites since we cannot device-bind their cap."""
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        mock_client = MagicMock()
        referrer_resp = MagicMock(data={"device_fingerprint_hash": None})

        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.single.return_value = chain
        chain.execute.return_value = referrer_resp
        mock_client.table.return_value = chain
        svc.client = mock_client

        count = await svc._referrer_device_lifetime_count("referrer-no-fp")
        assert count == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_referrer_not_found(self):
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        mock_client = MagicMock()

        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.single.return_value = chain
        chain.execute.side_effect = Exception("not found")
        mock_client.table.return_value = chain
        svc.client = mock_client

        count = await svc._referrer_device_lifetime_count("ghost")
        assert count == 0


class TestLifetimeCapEnforcement:
    """try_trigger_loop2 must short-circuit when the referrer's device has
    already consumed the lifetime cap."""

    @pytest.mark.asyncio
    async def test_rejects_at_3_on_device(self):
        from app.services.referral_service import ReferralService

        invite = {
            "id": "invite-cap-1",
            "referrer_user_id": "ref-cap-1",
            "redeemed_by_user_id": "invitee-cap-1",
            "redeemed_at": None,
            "invitee_first_comparison_id": None,
            "device_fingerprint_hash": "shared-device",
        }

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch.object(svc, "_load_invitee", new_callable=AsyncMock, return_value={"id": "invitee-cap-1", "email": "x@gmail.com"}), \
             patch.object(svc, "_referrer_device_lifetime_count", new_callable=AsyncMock, return_value=3), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant, \
             patch.object(svc, "_update_invite_as_redeemed", new_callable=AsyncMock) as mock_update, \
             patch.object(svc, "_send_loop2_push", new_callable=AsyncMock) as mock_push:

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": True, "flagged_reason": None}

            await svc.try_trigger_loop2(invitee_user_id="invitee-cap-1", comparison_id="cmp-cap-1")

            mock_grant.assert_not_called()
            mock_update.assert_not_called()
            mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_under_3(self):
        from app.services.referral_service import ReferralService

        invite = {
            "id": "invite-ok-1",
            "referrer_user_id": "ref-ok-1",
            "redeemed_by_user_id": "invitee-ok-1",
            "redeemed_at": None,
            "invitee_first_comparison_id": None,
            "device_fingerprint_hash": "device-ok",
        }

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch.object(svc, "_load_invitee", new_callable=AsyncMock, return_value={"id": "invitee-ok-1", "email": "x@gmail.com"}), \
             patch.object(svc, "_referrer_device_lifetime_count", new_callable=AsyncMock, return_value=2), \
             patch.object(svc, "_get_referrer_subscription_tier", new_callable=AsyncMock, return_value="free"), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant, \
             patch.object(svc, "_update_invite_as_redeemed", new_callable=AsyncMock) as mock_update, \
             patch.object(svc, "_send_loop2_push", new_callable=AsyncMock) as mock_push:

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": True, "flagged_reason": None}

            await svc.try_trigger_loop2(invitee_user_id="invitee-ok-1", comparison_id="cmp-ok-1")

            mock_grant.assert_called_once()
            mock_update.assert_called_once()
            mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_flags_invite_with_device_lifetime_cap_reached_reason(self):
        """When the cap blocks, the invite gets audit-logged + flagged so we
        can debug attribution drops and so abuse analytics see the rejection."""
        from app.services.referral_service import ReferralService

        invite = {
            "id": "invite-cap-2",
            "referrer_user_id": "ref-cap-2",
            "redeemed_by_user_id": "invitee-cap-2",
            "redeemed_at": None,
            "invitee_first_comparison_id": None,
            "device_fingerprint_hash": "shared-device-2",
        }

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch.object(svc, "_load_invitee", new_callable=AsyncMock, return_value={"id": "invitee-cap-2", "email": "x@gmail.com"}), \
             patch.object(svc, "_referrer_device_lifetime_count", new_callable=AsyncMock, return_value=5), \
             patch.object(svc, "_flag_invite", new_callable=AsyncMock) as mock_flag, \
             patch("app.services.referral_service.log_audit_event", new_callable=AsyncMock) as mock_audit, \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock):

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": True, "flagged_reason": None}

            await svc.try_trigger_loop2(invitee_user_id="invitee-cap-2", comparison_id="cmp-cap-2")

            mock_flag.assert_called_once_with(invite["id"], "DEVICE_LIFETIME_CAP_REACHED")
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs
            assert call_kwargs.get("event_type") == "referral_device_lifetime_cap_reached"
