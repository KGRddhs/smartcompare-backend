"""Tests for app/services/referral_service.py — code generation, invite creation, weekly cap, Loop 1.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
sections 2 + 4 + 7 and plan tasks B1.2, B2.1, B2.2.

Written FIRST (red phase). Backend implements to make these green.

Coverage gate: ≥80% on app/services/referral_service.py.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# B1.2 — Referral code generation (pure unit, no DB)
# ============================================


class TestReferralCodeGeneration:
    """Plan B1.2 step 1 — code format/alphabet/uniqueness."""

    def test_code_format_is_qr_dash_six_chars(self):
        from app.services.referral_service import generate_referral_code

        code = generate_referral_code()
        assert code.startswith("QR-"), f"expected QR- prefix, got {code!r}"
        assert len(code) == 9, f"expected 9 chars (QR- + 6), got {len(code)}: {code!r}"
        assert code[3:].isalnum(), f"body must be alphanumeric, got {code[3:]!r}"

    def test_code_excludes_ambiguous_chars(self):
        """No 0/O/1/I/L per design Section 4.1."""
        from app.services.referral_service import generate_referral_code

        ambiguous = set("0O1IL")
        for _ in range(200):
            code = generate_referral_code()
            body = code[3:]
            offenders = ambiguous & set(body)
            assert not offenders, f"code {code!r} contains ambiguous chars {offenders}"

    def test_code_is_uppercase(self):
        from app.services.referral_service import generate_referral_code

        for _ in range(50):
            code = generate_referral_code()
            assert code == code.upper(), f"code must be uppercase, got {code!r}"

    def test_codes_are_unique_across_calls(self):
        """1000 codes => 32^6 = 1.07B possible => collisions extremely unlikely."""
        from app.services.referral_service import generate_referral_code

        codes = {generate_referral_code() for _ in range(1000)}
        assert len(codes) > 990, f"only {len(codes)}/1000 unique — alphabet too small or RNG broken"


# ============================================
# B1.2 step 4 — ensure_code_for_user idempotency
# ============================================


class TestEnsureCodeForUser:
    """When a user already has a code, return it; otherwise generate + persist."""

    @pytest.mark.asyncio
    async def test_returns_existing_code_when_set(self):
        from app.services.referral_service import ReferralService

        existing = MagicMock()
        existing.data = {"referral_code": "QR-ABC234"}

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = existing

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            code = await svc.ensure_code_for_user("user-1")

        assert code == "QR-ABC234"
        # Update should NOT have been called
        client.table.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_generates_and_writes_code_when_missing(self):
        from app.services.referral_service import ReferralService

        existing = MagicMock()
        existing.data = {"referral_code": None}

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = existing
        # update success
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            code = await svc.ensure_code_for_user("user-2")

        assert code.startswith("QR-")
        assert len(code) == 9
        # Update should have been called once with the new code
        client.table.return_value.update.assert_called_once()
        update_args = client.table.return_value.update.call_args[0][0]
        assert update_args["referral_code"] == code


# ============================================
# B2.1 — POST /api/v1/referrals/share — create_invite
# ============================================


class TestCreateInvite:
    """Loop 1 fires immediately: row inserted + Deep Review credit granted + share_link returned."""

    @pytest.mark.asyncio
    async def test_create_invite_returns_invite_id_and_share_link(self):
        from app.services.referral_service import ReferralService

        # Mock chained Supabase calls
        client = MagicMock()
        # weekly cap: 0 invites this week
        weekly_count = MagicMock()
        weekly_count.count = 0
        # ensure_code returns existing
        existing_user = MagicMock()
        existing_user.data = {"referral_code": "QR-TESTXY"}
        # comparison ownership
        comp_data = MagicMock()
        comp_data.data = {"id": "cmp-1", "user_id": "user-1", "share_token": "tok-22-chars-aaaaaaaaaa"}
        # invite insert returns row
        invite_row = MagicMock()
        invite_row.data = [{"id": "invite-uuid-1"}]

        # Default fallthrough — set side_effects on each chain
        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                # weekly cap path: select(...).eq(...).gte(...).execute()
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly_count
                # insert path
                t.insert.return_value.execute.return_value = invite_row
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp_data
            elif name == "deep_review_credits":
                t.insert.return_value.execute.return_value = MagicMock(data=[{"id": "credit-1"}])
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.create_invite(
                referrer_user_id="user-1",
                comparison_id="cmp-1",
                share_target="whatsapp",
                device_fingerprint_hash="dev-1",
            )

        assert result["invite_id"] == "invite-uuid-1"
        assert "share_link" in result
        assert "ref=QR-TESTXY" in result["share_link"]
        assert "tok-22-chars-aaaaaaaaaa" in result["share_link"]

    @pytest.mark.asyncio
    async def test_create_invite_grants_loop1_deep_review_credit(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        weekly_count = MagicMock(count=0)
        existing_user = MagicMock(data={"referral_code": "QR-LOOP12"})
        comp = MagicMock(data={"id": "c1", "user_id": "u1", "share_token": "tok-aaaaaaaaaaaaaaaaaa"})
        invite_row = MagicMock(data=[{"id": "i1"}])

        # Track inserts to deep_review_credits
        credit_inserts = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly_count
                t.insert.return_value.execute.return_value = invite_row
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp
            elif name == "deep_review_credits":
                def capture_insert(payload):
                    credit_inserts.append(payload)
                    inner = MagicMock()
                    inner.execute.return_value = MagicMock(data=[{"id": "cred-1"}])
                    return inner
                t.insert.side_effect = capture_insert
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            await svc.create_invite(
                referrer_user_id="u1",
                comparison_id="c1",
                share_target="copy",
            )

        assert len(credit_inserts) == 1, f"expected 1 credit insert, got {len(credit_inserts)}"
        payload = credit_inserts[0]
        assert payload["user_id"] == "u1"
        assert payload["source"] == "share_loop1"

    @pytest.mark.asyncio
    async def test_create_invite_rejects_4th_within_seven_days(self):
        from app.services.referral_service import ReferralService, WeeklyInviteCapExceeded

        client = MagicMock()
        weekly_count = MagicMock(count=3)  # already at cap

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly_count
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            with pytest.raises(WeeklyInviteCapExceeded):
                await svc.create_invite(
                    referrer_user_id="u1",
                    comparison_id="c1",
                    share_target="whatsapp",
                )

    @pytest.mark.asyncio
    async def test_create_invite_rejects_unowned_comparison(self):
        """User A cannot create an invite from User B's comparison."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        weekly_count = MagicMock(count=0)
        existing_user = MagicMock(data={"referral_code": "QR-OWNED1"})
        # comparison owned by a DIFFERENT user
        foreign_comp = MagicMock(data={"id": "c1", "user_id": "different-user", "share_token": "tok"})

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly_count
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = foreign_comp
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            with pytest.raises(ValueError, match="not owned"):
                await svc.create_invite(
                    referrer_user_id="user-1",
                    comparison_id="c1",
                    share_target="whatsapp",
                )

    @pytest.mark.asyncio
    async def test_share_target_must_be_in_allowed_set(self):
        """share_target check constraint (whatsapp/copy/x/telegram/snapchat/other) — service validates pre-DB."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        weekly_count = MagicMock(count=0)
        existing_user = MagicMock(data={"referral_code": "QR-VALID7"})
        comp = MagicMock(data={"id": "c1", "user_id": "u1", "share_token": "tok"})

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly_count
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            with pytest.raises(ValueError, match="share_target"):
                await svc.create_invite(
                    referrer_user_id="u1",
                    comparison_id="c1",
                    share_target="facebook",  # NOT in allowed set
                )


# ============================================
# B2.2 — GET /api/v1/referrals/status — get_status
# ============================================


class TestGetReferralStatus:
    """Returns weekly + bonus + lifetime + code state."""

    @pytest.mark.asyncio
    async def test_status_returns_all_fields(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()

        weekly = MagicMock(count=2)
        existing_user = MagicMock(data={
            "referral_code": "QR-STATU1",
            "referral_bonus_comparisons_this_month": 5,
        })
        # 3 valid (non-expired, non-consumed) credits
        credits = MagicMock(count=3)
        # 1 lifetime redemption
        lifetime = MagicMock(count=1)

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "deep_review_credits":
                # filter chain: select.eq(user_id).is_(consumed_at, null).gt(expires_at, now).execute()
                chain = t.select.return_value.eq.return_value
                chain.is_.return_value.gt.return_value.execute.return_value = credits
            elif name == "referral_redemptions":
                t.select.return_value.eq.return_value.execute.return_value = lifetime
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            status = await svc.get_status("u1")

        assert status["weekly_invites_used"] == 2
        assert status["weekly_invites_remaining"] == 1  # 3 cap - 2 used
        assert status["monthly_bonus_comparisons"] == 5
        assert status["deep_review_credits_available"] == 3
        assert status["total_lifetime_redemptions"] == 1
        assert status["referral_code"] == "QR-STATU1"

    @pytest.mark.asyncio
    async def test_status_lazy_creates_code_when_missing(self):
        """First-time user has no code — status endpoint should mint one."""
        from app.services.referral_service import ReferralService

        client = MagicMock()

        # Initial select returns no code
        no_code_user = MagicMock(data={
            "referral_code": None,
            "referral_bonus_comparisons_this_month": 0,
        })
        # After update completes, second select call would get the code, but we just check
        # that update was invoked with a generated code.
        weekly = MagicMock(count=0)
        credits = MagicMock(count=0)
        lifetime = MagicMock(count=0)

        update_payloads = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = no_code_user
                def capture(payload):
                    update_payloads.append(payload)
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner
                t.update.side_effect = capture
            elif name == "deep_review_credits":
                t.select.return_value.eq.return_value.is_.return_value.gt.return_value.execute.return_value = credits
            elif name == "referral_redemptions":
                t.select.return_value.eq.return_value.execute.return_value = lifetime
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            status = await svc.get_status("u-new")

        # A code was minted via update
        assert len(update_payloads) >= 1, "lazy code creation must have updated users.referral_code"
        minted = update_payloads[0]["referral_code"]
        assert minted.startswith("QR-")
        assert status["referral_code"] == minted
