"""Tests for B4.2 — Loop 2 trigger in comparison post-hook.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
section 1 (architecture INVITEE FLOW) + plan task B4.2.

When a signed-in invitee completes their FIRST comparison after signup AND
abuse checks pass, Loop 2 fires:
1. Insert referral_redemptions row
2. Increment referrer's referral_bonus_comparisons_this_month by 5 (Free) or 10 (Premium)
3. Insert deep_review_credits for invitee (source='invitee_signup')
4. Update invite: redeemed_at + invitee_first_comparison_id
5. Send push to referrer (B4.4)

If abuse check fails: invite.flagged_reason set; audit log; no Loop 2 fire.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# B4.2 — try_trigger_loop2 service method
# ============================================


class TestTryTriggerLoop2Shape:
    """Method must exist on ReferralService."""

    def test_method_exists(self):
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        assert hasattr(svc, "try_trigger_loop2"), (
            "ReferralService.try_trigger_loop2(invitee_user_id, comparison_id) must exist"
        )


class TestLoop2HappyPath:
    """All 3 abuse checks pass + first comparison + unredeemed invite => Loop 2 fires."""

    @pytest.mark.asyncio
    async def test_first_comparison_after_signup_grants_bonus(self):
        from app.services.referral_service import ReferralService

        # Mock invite found (redeemed_by_user_id matches; redeemed_at IS NULL)
        invite = {
            "id": "invite-1",
            "referrer_user_id": "referrer-1",
            "redeemed_by_user_id": "invitee-1",
            "redeemed_at": None,
            "invitee_first_comparison_id": None,
            "device_fingerprint_hash": "ref-device",
        }

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant, \
             patch.object(svc, "_update_invite_as_redeemed", new_callable=AsyncMock) as mock_update, \
             patch.object(svc, "_send_loop2_push", new_callable=AsyncMock) as mock_push, \
             patch.object(svc, "_load_invitee", new_callable=AsyncMock, return_value={"id": "invitee-1", "email": "real@gmail.com"}):

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": True, "flagged_reason": None}

            await svc.try_trigger_loop2(invitee_user_id="invitee-1", comparison_id="cmp-1")

            mock_grant.assert_called_once()
            mock_update.assert_called_once()
            mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_premium_referrer_grants_10_not_5(self):
        from app.services.referral_service import ReferralService

        invite = {
            "id": "invite-2",
            "referrer_user_id": "premium-ref",
            "redeemed_by_user_id": "invitee-2",
            "redeemed_at": None,
            "invitee_first_comparison_id": None,
        }

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch.object(svc, "_load_invitee", new_callable=AsyncMock, return_value={"id": "invitee-2", "email": "x@gmail.com"}), \
             patch.object(svc, "_get_referrer_subscription_tier", new_callable=AsyncMock, return_value="premium"), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant, \
             patch.object(svc, "_update_invite_as_redeemed", new_callable=AsyncMock), \
             patch.object(svc, "_send_loop2_push", new_callable=AsyncMock):

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": True, "flagged_reason": None}

            await svc.try_trigger_loop2(invitee_user_id="invitee-2", comparison_id="cmp-2")

            # _grant_loop2_rewards called with grant_amount=10 for premium
            args, kwargs = mock_grant.call_args
            grant_amount = kwargs.get("grant_amount") or (args[2] if len(args) > 2 else None)
            assert grant_amount == 10, f"Premium referrer should get +10, got {grant_amount!r}"


class TestLoop2NoFirePaths:
    """Loop 2 must NOT fire under various skip conditions."""

    @pytest.mark.asyncio
    async def test_second_comparison_does_not_fire(self):
        """If invitee already has >1 comparison, Loop 2 has already fired or is irrelevant."""
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value={"id": "i", "redeemed_at": None}), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=2), \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant:
            await svc.try_trigger_loop2(invitee_user_id="u", comparison_id="c")
            mock_grant.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_invite_does_not_fire(self):
        """User signed up organically (no invite) => no Loop 2."""
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=None), \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant:
            await svc.try_trigger_loop2(invitee_user_id="u", comparison_id="c")
            mock_grant.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_redeemed_invite_does_not_re_fire(self):
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        # invite.redeemed_at already set
        invite = {"id": "i", "redeemed_at": "2026-05-05T10:00:00Z"}
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant:
            await svc.try_trigger_loop2(invitee_user_id="u", comparison_id="c")
            mock_grant.assert_not_called()

    @pytest.mark.asyncio
    async def test_abuse_check_failure_flags_invite(self):
        """Same-device abuse: flag invite, no Loop 2 fire."""
        from app.services.referral_service import ReferralService

        invite = {
            "id": "invite-fraud",
            "referrer_user_id": "ref",
            "redeemed_by_user_id": "fraud",
            "redeemed_at": None,
            "device_fingerprint_hash": "same-device",
        }

        svc = ReferralService()
        with patch.object(svc, "_find_unredeemed_invite_for_invitee", new_callable=AsyncMock, return_value=invite), \
             patch.object(svc, "_count_user_comparisons", new_callable=AsyncMock, return_value=1), \
             patch.object(svc, "_load_invitee", new_callable=AsyncMock, return_value={"id": "fraud", "email": "f@gmail.com"}), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch.object(svc, "_flag_invite", new_callable=AsyncMock) as mock_flag, \
             patch.object(svc, "_grant_loop2_rewards", new_callable=AsyncMock) as mock_grant, \
             patch("app.services.referral_service.log_audit_event", new_callable=AsyncMock) as mock_audit:

            MockAbuse.return_value.evaluate_invite.return_value = {
                "passed": False, "flagged_reason": "SAME_DEVICE",
            }

            await svc.try_trigger_loop2(invitee_user_id="fraud", comparison_id="cmp")

            mock_grant.assert_not_called()
            mock_flag.assert_called_once()
            # Audit log must be called for abuse events
            assert mock_audit.called, "abuse-flagged invite must be audited"
