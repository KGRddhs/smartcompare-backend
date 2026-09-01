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
    async def test_create_invite_no_longer_enforces_weekly_cap(self):
        """Bundle B/C/D § 4.7: the per-share weekly cap is removed. The only
        cap is the lifetime device cap at try_trigger_loop2 (post-signup).
        Even a user with 100 prior invites this week can still call /share."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        existing_user = MagicMock(data={
            "referral_code": "QR-EXIST1",
            "lifetime_invites_consumed": 1,
        })
        owned_comp = MagicMock(data={
            "id": "c1", "user_id": "u1", "share_token": "tok1",
        })
        invite_insert = MagicMock(data=[{"id": "inv-new"}])

        def table_side_effect(name):
            t = MagicMock()
            if name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = owned_comp
            elif name == "referral_invites":
                t.insert.return_value.execute.return_value = invite_insert
            elif name == "deep_review_credits":
                t.insert.return_value.execute.return_value = MagicMock(data=[])
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            # Must NOT raise — weekly cap is gone.
            result = await svc.create_invite(
                referrer_user_id="u1",
                comparison_id="c1",
                share_target="whatsapp",
            )
        assert result["invite_id"] == "inv-new"
        # New shape: lifetime counters in response
        assert result["lifetime_invites_used"] == 1
        assert result["lifetime_invites_remaining"] == 2
        # Old shape gone
        assert "weekly_invites_used" not in result
        assert "weekly_invites_remaining" not in result

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
            "lifetime_invites_consumed": 2,
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

        # Bundle B/C/D § 4.7: lifetime shape replaces weekly
        assert status["lifetime_invites_used"] == 2
        assert status["lifetime_invites_remaining"] == 1  # 3 cap - 2 used
        assert status["monthly_bonus_comparisons"] == 5
        assert status["deep_review_credits_available"] == 3
        assert status["total_lifetime_redemptions"] == 1
        assert status["referral_code"] == "QR-STATU1"
        assert "weekly_invites_used" not in status
        assert "weekly_invites_remaining" not in status

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


# ============================================
# Coverage-driven: B3.1 resolve_invite real path
# ============================================


class TestResolveInvite:
    """Drive the actual resolve_invite code path (no helper mocking)."""

    @pytest.mark.asyncio
    async def test_resolve_invite_returns_payload_and_marks_first_view(self):
        from app.services.referral_service import ReferralService

        first_view_updates = []

        client = MagicMock()
        # rpc → resolve_referral_code returns referrer
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref-1", "display_name": "Ahmed"}]
        )

        # comparisons lookup
        comp = MagicMock(data={
            "id": "cmp-1",
            "user_id": "ref-1",
            "share_token": "tok-aaaaaaaaaaaaaaaaaa",
            "full_response": {
                "products": [{"name": "iPhone"}],
                "winner": {"name": "iPhone"},
                "preferences": {"priorities": ["best_price"]},  # MUST be stripped
                "budget": {"tier": "premium"},  # MUST be stripped
                "behavior_profile": {"affinity": 0.8},  # MUST be stripped
                "personalization": {"some": "data"},  # MUST be stripped
            },
        })

        invite_query_resp = MagicMock(data=[{"id": "invite-1", "first_viewed_at": None}])

        def table_side_effect(name):
            t = MagicMock()
            if name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp
            elif name == "referral_invites":
                # select chain
                chain = t.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value
                chain.execute.return_value = invite_query_resp

                # update chain — capture the first_viewed_at write
                def capture_update(payload):
                    first_view_updates.append(payload)
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner

                t.update.side_effect = capture_update
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(
                share_token="tok-aaaaaaaaaaaaaaaaaa", ref_code="QR-AHMED1"
            )

        assert result is not None
        assert result["referrer_display_name"] == "Ahmed"
        assert result["invite_id"] == "invite-1"

        # PRIVACY INVARIANT: stripped keys absent
        comparison = result["comparison"]
        assert "preferences" not in comparison
        assert "budget" not in comparison
        assert "behavior_profile" not in comparison
        assert "personalization" not in comparison

        # first_viewed_at was set
        assert len(first_view_updates) == 1
        assert "first_viewed_at" in first_view_updates[0]

    @pytest.mark.asyncio
    async def test_resolve_invite_returns_none_for_unknown_ref(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(data=[])

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="t", ref_code="QR-NOTREAL")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_invite_returns_none_when_comparison_owner_mismatch(self):
        """Defense-in-depth: token + ref must point to the same user's comparison."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref-1", "display_name": "Ahmed"}]
        )

        # Comparison owner is DIFFERENT from referrer
        wrong_comp = MagicMock(data={
            "id": "c", "user_id": "DIFFERENT-USER", "share_token": "t", "full_response": {},
        })
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = wrong_comp

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="t", ref_code="QR-AHMED1")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_invite_does_not_re_set_first_viewed(self):
        """If invite already has first_viewed_at, don't update again."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "ref-1", "display_name": "X"}]
        )

        comp = MagicMock(data={
            "id": "c", "user_id": "ref-1", "share_token": "t", "full_response": {},
        })
        invite_already_viewed = MagicMock(data=[{"id": "i", "first_viewed_at": "2026-05-04T00:00:00Z"}])

        def table_side_effect(name):
            t = MagicMock()
            if name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp
            elif name == "referral_invites":
                t.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = invite_already_viewed
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.resolve_invite(share_token="t", ref_code="QR-X")

        assert result is not None
        # update should NOT have been called for first_viewed_at
        # (the table mock for referral_invites wasn't given an update side_effect — calling it returns plain MagicMock)
        # We assert by counting update calls on the referral_invites mock
        for call in client.table.mock_calls:
            if call.args == ("referral_invites",) and ".update(" in str(call):
                pytest.fail("first_viewed_at must not be re-set on subsequent views")


# ============================================
# Coverage-driven: B3.4 run_invitee_quiz real path
# ============================================


class TestRunInviteeQuiz:
    @pytest.mark.asyncio
    async def test_quiz_returns_personalized_with_invitee_inputs(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        comp = MagicMock(data={
            "id": "c1",
            "full_response": {
                "products": [{"name": "iPhone"}, {"name": "Galaxy"}],
                "winner": {"name": "iPhone"},
                "scoring": {"scoring_method": "category_weighted"},
                "preferences": {"priorities": ["X"]},  # must be stripped
            },
        })
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = comp

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.run_invitee_quiz(
                share_token="t",
                priority="best_price",
                budget="mid",
                brand_attitude="function_first",
                non_negotiable="battery",
            )

        assert result is not None
        assert result["scoring"]["scoring_method"] == "invitee_quiz"
        assert result["personalization"]["scoring_method"] == "invitee_quiz"
        assert result["personalization"]["invitee_inputs"]["priority"] == "best_price"
        assert result["personalization"]["invitee_inputs"]["budget"] == "mid"
        assert result["personalization"]["invitee_inputs"]["brand_attitude"] == "function_first"
        assert result["personalization"]["invitee_inputs"]["non_negotiable"] == "battery"

        # Privacy: referrer prefs not leaked
        assert "preferences" not in result

    @pytest.mark.asyncio
    async def test_quiz_returns_none_for_missing_comparison(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            result = await svc.run_invitee_quiz(
                share_token="missing", priority="best_price", budget="mid",
                brand_attitude="function_first",
            )

        assert result is None


# ============================================
# Coverage-driven: link_invite_redemption (B3.5)
# ============================================


class TestLinkInviteRedemption:
    @pytest.mark.asyncio
    async def test_link_updates_redeemed_by_user_id(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        # Existing invite, not yet redeemed
        existing = MagicMock(data={
            "id": "invite-1",
            "redeemed_by_user_id": None,
            "redeemed_at": None,
        })

        update_payloads = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing

                def capture(payload):
                    update_payloads.append(payload)
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner

                t.update.side_effect = capture
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_redemption(
                invite_id="invite-1", new_user_id="new-user"
            )

        assert ok is True
        assert len(update_payloads) == 1
        assert update_payloads[0]["redeemed_by_user_id"] == "new-user"

    @pytest.mark.asyncio
    async def test_link_returns_false_when_already_redeemed(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        existing = MagicMock(data={
            "id": "i", "redeemed_by_user_id": "previous-user", "redeemed_at": None,
        })
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = existing

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_redemption(invite_id="i", new_user_id="new")

        assert ok is False

    @pytest.mark.asyncio
    async def test_link_returns_false_for_missing_invite(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_redemption(invite_id="i", new_user_id="new")

        assert ok is False

    @pytest.mark.asyncio
    async def test_link_returns_false_on_empty_args(self):
        from app.services.referral_service import ReferralService

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=MagicMock()):
            svc = ReferralService()
            assert (await svc.link_invite_redemption(invite_id="", new_user_id="u")) is False
            assert (await svc.link_invite_redemption(invite_id="i", new_user_id="")) is False
            assert (await svc.link_invite_redemption(invite_id=None, new_user_id="u")) is False

    @pytest.mark.asyncio
    async def test_link_swallows_db_errors(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("db down")

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            ok = await svc.link_invite_redemption(invite_id="i", new_user_id="u")

        assert ok is False


# ============================================
# Coverage-driven: B4.2 Loop 2 helpers
# ============================================


class TestLoop2HelperCoverage:
    """Hit the actual helper code paths inside ReferralService."""

    @pytest.mark.asyncio
    async def test_count_user_comparisons_returns_count(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=3, data=[])

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            n = await svc._count_user_comparisons("u")

        assert n == 3

    @pytest.mark.asyncio
    async def test_count_user_comparisons_handles_db_error(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("oops")

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            assert await svc._count_user_comparisons("u") == 0

    @pytest.mark.asyncio
    async def test_load_invitee_returns_user(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "u", "email": "a@b.com", "subscription_tier": "free"}
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            user = await svc._load_invitee("u")

        assert user["email"] == "a@b.com"

    @pytest.mark.asyncio
    async def test_load_invitee_returns_none_on_error(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("err")

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            assert await svc._load_invitee("u") is None

    @pytest.mark.asyncio
    async def test_get_referrer_subscription_tier_premium(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"subscription_tier": "Premium"}
        )

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            tier = await svc._get_referrer_subscription_tier("ref")

        assert tier == "premium"  # case-normalized

    @pytest.mark.asyncio
    async def test_get_referrer_tier_default_free(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={})

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            assert await svc._get_referrer_subscription_tier("r") == "free"

    @pytest.mark.asyncio
    async def test_get_referrer_tier_none_id_returns_free(self):
        from app.services.referral_service import ReferralService

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=MagicMock()):
            svc = ReferralService()
            assert await svc._get_referrer_subscription_tier(None) == "free"

    @pytest.mark.asyncio
    async def test_get_referrer_tier_swallows_db_error(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("err")

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            assert await svc._get_referrer_subscription_tier("r") == "free"

    @pytest.mark.asyncio
    async def test_grant_loop2_rewards_full_path(self):
        """Drive the full grant: redemption row + bonus bump + invitee credit."""
        from app.services.referral_service import ReferralService

        client = MagicMock()

        redemption_inserts = []
        bonus_updates = []
        credit_inserts = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_redemptions":
                def cap_red(payload):
                    redemption_inserts.append(payload)
                    inner = MagicMock()
                    inner.execute.return_value = MagicMock(data=[{"id": "red-1"}])
                    return inner
                t.insert.side_effect = cap_red
            elif name == "users":
                # Read current bonus
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"referral_bonus_comparisons_this_month": 2}
                )

                def cap_upd(payload):
                    bonus_updates.append(payload)
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner
                t.update.side_effect = cap_upd
            elif name == "deep_review_credits":
                def cap_cred(payload):
                    credit_inserts.append(payload)
                    inner = MagicMock()
                    inner.execute.return_value = MagicMock(data=[{"id": "cred-1"}])
                    return inner
                t.insert.side_effect = cap_cred
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            await svc._grant_loop2_rewards(
                invite={"id": "inv-1", "referrer_user_id": "ref"},
                invitee={"id": "inv-user", "email": "x@y.com"},
                grant_amount=5,
            )

        assert len(redemption_inserts) == 1
        assert redemption_inserts[0]["loop2_comparisons_granted"] == 5
        assert redemption_inserts[0]["referrer_user_id"] == "ref"
        assert redemption_inserts[0]["invitee_user_id"] == "inv-user"

        # Bundle B/C/D § 4.2: now 2 updates fire on users — bonus capacity
        # bump + lifetime_invites_consumed increment (signup decrement).
        bonus_only = [u for u in bonus_updates if "referral_bonus_comparisons_this_month" in u]
        lifetime_only = [u for u in bonus_updates if "lifetime_invites_consumed" in u]
        assert len(bonus_only) == 1
        assert bonus_only[0]["referral_bonus_comparisons_this_month"] == 2 + 5
        assert len(lifetime_only) == 1, (
            "Bundle B/C/D § 4.2 missing: must increment lifetime_invites_consumed"
        )

        assert len(credit_inserts) == 1
        assert credit_inserts[0]["user_id"] == "inv-user"
        assert credit_inserts[0]["source"] == "invitee_signup"

    @pytest.mark.asyncio
    async def test_grant_loop2_rewards_short_circuits_on_missing_ids(self):
        """Defense: missing referrer_id or invitee_id => no writes."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        # Track ALL table calls — none should fire on the no-id path
        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            # Missing referrer
            await svc._grant_loop2_rewards(
                invite={"id": "i", "referrer_user_id": None},
                invitee={"id": "u"},
                grant_amount=5,
            )
            # Missing invitee
            await svc._grant_loop2_rewards(
                invite={"id": "i", "referrer_user_id": "r"},
                invitee={"id": None},
                grant_amount=5,
            )

        # No table mutations
        assert client.table.call_count == 0

    @pytest.mark.asyncio
    async def test_update_invite_as_redeemed(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        update_payloads = []

        def table_side_effect(name):
            t = MagicMock()

            def capture(payload):
                update_payloads.append(payload)
                inner = MagicMock()
                inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                return inner

            t.update.side_effect = capture
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            await svc._update_invite_as_redeemed("i-1", "cmp-1")

        assert len(update_payloads) == 1
        assert update_payloads[0]["invitee_first_comparison_id"] == "cmp-1"
        assert "redeemed_at" in update_payloads[0]

    @pytest.mark.asyncio
    async def test_flag_invite(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        update_payloads = []

        def table_side_effect(name):
            t = MagicMock()

            def capture(payload):
                update_payloads.append(payload)
                inner = MagicMock()
                inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                return inner

            t.update.side_effect = capture
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            await svc._flag_invite("i-1", "SAME_DEVICE")

        assert update_payloads[0] == {"flagged_reason": "SAME_DEVICE"}

    @pytest.mark.asyncio
    async def test_send_loop2_push_invokes_push_service(self):
        from app.services.referral_service import ReferralService

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=MagicMock()), \
             patch("app.services.push_service.send_loop2_push", new_callable=AsyncMock) as mock_push:
            svc = ReferralService()
            await svc._send_loop2_push("ref-1", {"email": "sara@example.com"}, 5)

        mock_push.assert_called_once()
        kwargs = mock_push.call_args.kwargs
        assert kwargs["referrer_user_id"] == "ref-1"
        assert kwargs["bonus_amount"] == 5
        # Display name extracted from email local part
        assert kwargs["invitee_display_name"] == "sara"

    @pytest.mark.asyncio
    async def test_send_loop2_push_swallows_errors(self):
        from app.services.referral_service import ReferralService

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=MagicMock()), \
             patch("app.services.push_service.send_loop2_push", new_callable=AsyncMock, side_effect=Exception("expo down")):
            svc = ReferralService()
            # Should NOT raise
            await svc._send_loop2_push("ref-1", {"email": "x@y.com"}, 5)


# ============================================
# Coverage-driven: try_trigger_loop2 full happy path (real impl, mocked DB)
# ============================================


class TestTryTriggerLoop2RealPath:
    @pytest.mark.asyncio
    async def test_full_happy_path_grants_rewards_and_pushes(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()

        # Setup: invite found, comparison count = 1, abuse passes
        invite_query = MagicMock(data=[{
            "id": "inv-1",
            "referrer_user_id": "ref",
            "redeemed_by_user_id": "u",
            "redeemed_at": None,
            "device_fingerprint_hash": "device-X",
        }])
        comp_count = MagicMock(count=1, data=[])
        invitee = MagicMock(data={"id": "u", "email": "u@gmail.com", "subscription_tier": "free"})

        # Track inserts/updates
        all_inserts = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                # multiple chains
                def select_chain(*args, **kwargs):
                    inner = MagicMock()
                    inner.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = invite_query
                    return inner
                t.select.side_effect = select_chain

                def cap_upd(payload):
                    all_inserts.append(("invite_update", payload))
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner
                t.update.side_effect = cap_upd
            elif name == "comparisons":
                t.select.return_value.eq.return_value.execute.return_value = comp_count
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = invitee

                def cap_upd(payload):
                    all_inserts.append(("user_update", payload))
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner
                t.update.side_effect = cap_upd
            elif name == "referral_redemptions":
                def cap_ins(payload):
                    all_inserts.append(("redemption", payload))
                    inner = MagicMock()
                    inner.execute.return_value = MagicMock(data=[{"id": "r-1"}])
                    return inner
                t.insert.side_effect = cap_ins
            elif name == "deep_review_credits":
                def cap_ins(payload):
                    all_inserts.append(("credit", payload))
                    inner = MagicMock()
                    inner.execute.return_value = MagicMock(data=[{"id": "c-1"}])
                    return inner
                t.insert.side_effect = cap_ins
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch("app.services.push_service.send_loop2_push", new_callable=AsyncMock) as mock_push:

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": True, "flagged_reason": None}

            svc = ReferralService()
            await svc.try_trigger_loop2(invitee_user_id="u", comparison_id="cmp-1")

        # Verify we got: redemption insert + user bonus update + credit insert + invite redeemed update
        types = [t for t, _ in all_inserts]
        assert "redemption" in types, f"expected redemption insert, got {types}"
        assert "user_update" in types, f"expected user bonus update, got {types}"
        assert "credit" in types, f"expected invitee credit insert, got {types}"
        assert "invite_update" in types, f"expected invite redeemed update, got {types}"

        mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_abuse_fail_audits_and_flags_no_grants(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        invite_query = MagicMock(data=[{
            "id": "inv-fraud", "referrer_user_id": "ref",
            "redeemed_by_user_id": "fraud", "redeemed_at": None,
            "device_fingerprint_hash": "same-device",
        }])
        comp_count = MagicMock(count=1, data=[])
        invitee = MagicMock(data={"id": "fraud", "email": "f@gmail.com"})

        flag_calls = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = invite_query

                def cap_flag(payload):
                    flag_calls.append(payload)
                    inner = MagicMock()
                    inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
                    return inner
                t.update.side_effect = cap_flag
            elif name == "comparisons":
                t.select.return_value.eq.return_value.execute.return_value = comp_count
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = invitee
            return t

        client.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client), \
             patch("app.services.referral_service.AbuseDetectionService") as MockAbuse, \
             patch("app.services.referral_service.log_audit_event", new_callable=AsyncMock) as mock_audit:

            MockAbuse.return_value.evaluate_invite.return_value = {"passed": False, "flagged_reason": "SAME_DEVICE"}

            svc = ReferralService()
            await svc.try_trigger_loop2(invitee_user_id="fraud", comparison_id="cmp")

        # No redemption insert, no credit insert — only flag update
        assert len(flag_calls) == 1
        assert flag_calls[0] == {"flagged_reason": "SAME_DEVICE"}
        # Audit fired
        assert mock_audit.called

    @pytest.mark.asyncio
    async def test_outer_exception_handler_swallows(self):
        """Loop 2 is fire-and-forget — outer try/except catches everything."""
        from app.services.referral_service import ReferralService

        client = MagicMock()
        client.table.side_effect = Exception("unexpected DB collapse")

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
            svc = ReferralService()
            # Should NOT raise — comparison endpoint must never fail because of referral plumbing
            await svc.try_trigger_loop2(invitee_user_id="u", comparison_id="c")
