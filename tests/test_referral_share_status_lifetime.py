"""RED tests for Phase 2 Tasks 2.4 + 2.5 — share/status endpoints migrate
from weekly to lifetime counters.

Spec:
- docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.7
- docs/plans/2026-05-12-bundle-bcd-consolidated.md Tasks 2.4, 2.5

Contract changes (BREAKING — pre-launch, no callers depend on weekly fields):

1. /share (`ReferralService.create_invite`) response shape:
   - REMOVES: `weekly_invites_used`, `weekly_invites_remaining`
   - ADDS:    `lifetime_invites_remaining` (informational; FE gates UI on this)
   - INVARIANT: share path NO LONGER UPDATEs `users.lifetime_invites_consumed`.
                That column is incremented only at Loop 2 success.

2. /status (`ReferralService.get_status`) response shape:
   - REMOVES: `weekly_invites_used`, `weekly_invites_remaining`
   - ADDS:    `lifetime_invites_used` (= users.lifetime_invites_consumed),
              `lifetime_invites_remaining` (= max(0, LIFETIME_CAP - used))

Test pattern: route Supabase mocks by TABLE name (not call order) so the
test stays robust when backend-bcd adds a new `users` query for lifetime
count without us having to re-walk the mock chain.

Pattern mirrors tests/test_referral_share_privacy.py + test_referral_service.py.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _routed_table_mock(table_responses: dict[str, list]):
    """Build a MagicMock supabase client whose .table(name).execute() returns
    the next queued response for ``name``.

    Each value in ``table_responses`` is a list of MagicMock execute results
    that will be popped in FIFO order. The chain methods (.select, .insert,
    .update, .eq, .single, .gte, .gt, .is_) are routed back to the same
    chain so any chain length is supported.
    """
    chains: dict[str, MagicMock] = {}

    def make_chain(name: str) -> MagicMock:
        if name in chains:
            return chains[name]
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        chain.is_.return_value = chain
        chain.gt.return_value = chain
        chain.gte.return_value = chain
        chain.single.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain

        responses = table_responses.get(name, [])

        def execute():
            if responses:
                return responses.pop(0)
            return MagicMock(count=0, data=[])

        chain.execute.side_effect = execute
        chains[name] = chain
        return chain

    client = MagicMock()
    client.table.side_effect = make_chain
    return client


# ============================================
# Task 2.4 — /share endpoint contract
# ============================================


class TestShareResponseShapeLifetime:
    """The dict returned by ReferralService.create_invite must use the
    lifetime field names from design § 4.7."""

    @pytest.mark.asyncio
    async def test_response_includes_lifetime_invites_remaining(self):
        """The new informational field must be present on every share response.

        Computation: ``max(0, LIFETIME_CAP - users.lifetime_invites_consumed)``.
        """
        from app.services.referral_service import LIFETIME_CAP, ReferralService

        client = _routed_table_mock({
            "referral_invites": [
                MagicMock(count=0, data=[]),      # weekly cap query
                MagicMock(data=[{"id": "invite-1"}]),  # insert
            ],
            "comparisons": [
                MagicMock(data={"id": "cmp-1", "user_id": "user-1", "share_token": "tok123"}),
            ],
            "deep_review_credits": [
                MagicMock(data=[{"id": "credit-1"}]),
            ],
            "users": [
                # Backend-bcd will add a query here to read lifetime_invites_consumed.
                # We provide a value so the new path resolves to 2 remaining.
                MagicMock(data={"lifetime_invites_consumed": 1}),
            ],
        })

        svc = ReferralService()
        svc.client = client
        with patch.object(svc, "ensure_code_for_user", return_value="QR-EXIST1"):
            resp = await svc.create_invite(
                referrer_user_id="user-1",
                comparison_id="cmp-1",
                share_target="whatsapp",
                device_fingerprint_hash="fp-share-1",
                privacy=None,
            )

        assert "lifetime_invites_remaining" in resp, (
            f"design § 4.7: /share must return lifetime_invites_remaining. "
            f"Got keys: {sorted(resp.keys())}"
        )
        # Sanity: the value must be in [0, LIFETIME_CAP]
        assert 0 <= resp["lifetime_invites_remaining"] <= LIFETIME_CAP

    @pytest.mark.asyncio
    async def test_response_does_not_include_legacy_weekly_fields(self):
        """The breaking-change: weekly_invites_used/remaining are gone."""
        from app.services.referral_service import ReferralService

        client = _routed_table_mock({
            "referral_invites": [
                MagicMock(count=0, data=[]),
                MagicMock(data=[{"id": "invite-2"}]),
            ],
            "comparisons": [
                MagicMock(data={"id": "cmp-2", "user_id": "user-2", "share_token": "tok2"}),
            ],
            "deep_review_credits": [
                MagicMock(data=[{"id": "credit-2"}]),
            ],
            "users": [
                MagicMock(data={"lifetime_invites_consumed": 0}),
            ],
        })

        svc = ReferralService()
        svc.client = client
        with patch.object(svc, "ensure_code_for_user", return_value="QR-EXIST1"):
            resp = await svc.create_invite(
                referrer_user_id="user-2",
                comparison_id="cmp-2",
                share_target="copy",
                device_fingerprint_hash="fp-share-2",
                privacy=None,
            )

        assert "weekly_invites_used" not in resp, (
            "design § 4.7: legacy weekly_invites_used must be removed from "
            f"/share response. Got keys: {sorted(resp.keys())}"
        )
        assert "weekly_invites_remaining" not in resp, (
            "design § 4.7: legacy weekly_invites_remaining must be removed"
        )

    @pytest.mark.asyncio
    async def test_share_does_not_update_users_lifetime_invites_consumed(self):
        """Critical invariant: share path must NOT increment the counter.

        Per design § 4.7 the counter is consumed ONLY at Loop 2 success
        (test_referral_lifetime_cap.py TestSignupDecrement). If the share
        path also touched it, the cap would be triggered by attempted
        shares rather than successful referrals, breaking the model.
        """
        from app.services.referral_service import ReferralService

        update_payloads_users: list[dict] = []

        chains: dict[str, MagicMock] = {}

        def make_chain(name: str) -> MagicMock:
            if name in chains:
                return chains[name]
            chain = MagicMock()
            chain.select.return_value = chain
            chain.insert.return_value = chain
            chain.delete.return_value = chain
            chain.eq.return_value = chain
            chain.is_.return_value = chain
            chain.gt.return_value = chain
            chain.gte.return_value = chain
            chain.single.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain

            def update_capture(payload):
                if name == "users":
                    update_payloads_users.append(payload)
                return chain

            chain.update.side_effect = update_capture

            responses = {
                "referral_invites": [
                    MagicMock(count=0, data=[]),
                    MagicMock(data=[{"id": "invite-3"}]),
                ],
                "comparisons": [
                    MagicMock(data={"id": "cmp-3", "user_id": "user-3", "share_token": "tok3"}),
                ],
                "deep_review_credits": [
                    MagicMock(data=[{"id": "credit-3"}]),
                ],
                "users": [
                    MagicMock(data={"lifetime_invites_consumed": 0}),
                ],
            }.get(name, [])

            def execute(_responses=responses):
                if _responses:
                    return _responses.pop(0)
                return MagicMock(count=0, data=[])

            chain.execute.side_effect = execute
            chains[name] = chain
            return chain

        client = MagicMock()
        client.table.side_effect = make_chain

        svc = ReferralService()
        svc.client = client
        with patch.object(svc, "ensure_code_for_user", return_value="QR-CONSM3"):
            await svc.create_invite(
                referrer_user_id="user-3",
                comparison_id="cmp-3",
                share_target="x",
                device_fingerprint_hash="fp-share-3",
                privacy=None,
            )

        for payload in update_payloads_users:
            assert "lifetime_invites_consumed" not in payload, (
                f"design § 4.7 invariant: share path must not increment "
                f"lifetime_invites_consumed. Saw update payload: {payload}"
            )


# ============================================
# Task 2.5 — /status endpoint contract
# ============================================


class TestStatusResponseShapeLifetime:
    """ReferralService.get_status must surface lifetime_invites_used /
    lifetime_invites_remaining and drop the weekly equivalents."""

    @staticmethod
    def _status_client(lifetime_consumed: int = 0, *,
                       monthly_bonus: int = 0,
                       credits: int = 0,
                       redemptions: int = 0,
                       referral_code: str = "QR-STATS5"):
        """Build a routed client that returns sane defaults for get_status."""
        return _routed_table_mock({
            "referral_invites": [
                MagicMock(count=0, data=[]),  # weekly count (legacy; may be removed)
            ],
            "users": [
                MagicMock(data={
                    "referral_code": referral_code,
                    "referral_bonus_comparisons_this_month": monthly_bonus,
                    "lifetime_invites_consumed": lifetime_consumed,
                }),
            ],
            "deep_review_credits": [
                MagicMock(count=credits, data=[]),
            ],
            "referral_redemptions": [
                MagicMock(count=redemptions, data=[]),
            ],
        })

    @pytest.mark.asyncio
    async def test_status_returns_lifetime_invites_used(self):
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        svc.client = self._status_client(lifetime_consumed=2)

        status = await svc.get_status("user-stats-5")

        assert "lifetime_invites_used" in status, (
            f"design § 4.7: /status must return lifetime_invites_used. "
            f"Got keys: {sorted(status.keys())}"
        )
        assert status["lifetime_invites_used"] == 2

    @pytest.mark.asyncio
    async def test_status_returns_lifetime_invites_remaining(self):
        from app.services.referral_service import LIFETIME_CAP, ReferralService

        svc = ReferralService()
        svc.client = self._status_client(lifetime_consumed=1)

        status = await svc.get_status("user-stats-6")

        assert "lifetime_invites_remaining" in status
        assert status["lifetime_invites_remaining"] == max(0, LIFETIME_CAP - 1)

    @pytest.mark.asyncio
    async def test_status_lifetime_remaining_floored_at_zero_when_over_cap(self):
        """Defense: if lifetime_invites_consumed somehow exceeds LIFETIME_CAP
        (manual DB edit, audit-event replay), remaining must clamp to 0 not
        go negative."""
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        svc.client = self._status_client(lifetime_consumed=99)

        status = await svc.get_status("user-stats-7")
        assert status["lifetime_invites_remaining"] == 0

    @pytest.mark.asyncio
    async def test_status_does_not_include_legacy_weekly_fields(self):
        """Breaking change: weekly_invites_used/remaining removed."""
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        svc.client = self._status_client(lifetime_consumed=0)

        status = await svc.get_status("user-stats-8")

        assert "weekly_invites_used" not in status, (
            "design § 4.7: legacy weekly_invites_used removed from /status"
        )
        assert "weekly_invites_remaining" not in status

    @pytest.mark.asyncio
    async def test_status_preserves_referral_code_and_bonus_fields(self):
        """Regression: only the weekly→lifetime fields are migrated. All other
        keys (`referral_code`, `monthly_bonus_comparisons`,
        `deep_review_credits_available`, `total_lifetime_redemptions`)
        must remain intact."""
        from app.services.referral_service import ReferralService

        svc = ReferralService()
        svc.client = self._status_client(
            lifetime_consumed=1,
            monthly_bonus=4,
            credits=2,
            redemptions=5,
            referral_code="QR-STATS9",
        )

        status = await svc.get_status("user-stats-9")

        assert status["referral_code"] == "QR-STATS9"
        assert status["monthly_bonus_comparisons"] == 4
        assert status["deep_review_credits_available"] == 2
        assert status["total_lifetime_redemptions"] == 5
