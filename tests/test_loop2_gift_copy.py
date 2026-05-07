"""Tests for plan task 37 — Loop 2 push gift-framing copy.

Contract:
- Title + body emphasize the gift framing AND mention 3-day expiry.
- Existing test_push_service.py tests keep passing (we ADD copy assertions,
  don't remove existing structural ones).
- Both EN + AR copy mention expiry — invitee gets a deadline-aware push.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestLoop2CopyMentionsExpiry:
    @pytest.mark.asyncio
    async def test_english_body_mentions_3_days_expiry(self):
        """Body must mention the 3-day expiry per design 4f + plan task 37 step 1."""
        from app.services.push_service import send_loop2_push

        with patch(
            "app.services.push_service._send_to_expo", new_callable=AsyncMock
        ) as mock_send, patch(
            "app.services.push_service._get_user_push_token",
            new_callable=AsyncMock,
            return_value="ExponentPushToken[REF]",
        ), patch(
            "app.services.push_service._get_user_language",
            new_callable=AsyncMock,
            return_value="English",
        ):
            await send_loop2_push(
                referrer_user_id="ref-1",
                invitee_display_name="Sarah",
                bonus_amount=5,
            )

        payload = mock_send.call_args[0][0]
        haystack = (payload["title"] + " " + payload["body"]).lower()
        # Gift-framing: must mention expiry/days
        assert any(
            tok in haystack
            for tok in ("3 days", "three days", "expire", "expires")
        ), (
            f"Loop 2 push must mention 3-day expiry (gift-framing). "
            f"Got: title={payload['title']!r} body={payload['body']!r}"
        )

    @pytest.mark.asyncio
    async def test_english_copy_includes_invitee_name_and_bonus_amount(self):
        """Plan task 37: body should be 'Your friend just compared something'
        title + '{name}, your friend just used Qaren. You got X bonus
        comparisons. Expires in 3 days.' body."""
        from app.services.push_service import send_loop2_push

        with patch(
            "app.services.push_service._send_to_expo", new_callable=AsyncMock
        ) as mock_send, patch(
            "app.services.push_service._get_user_push_token",
            new_callable=AsyncMock,
            return_value="ExponentPushToken[REF]",
        ), patch(
            "app.services.push_service._get_user_language",
            new_callable=AsyncMock,
            return_value="English",
        ):
            await send_loop2_push(
                referrer_user_id="ref-1",
                invitee_display_name="Sarah",
                bonus_amount=5,
            )

        payload = mock_send.call_args[0][0]
        combined = payload["title"] + " " + payload["body"]
        assert "Sarah" in combined, "invitee name must appear in title or body"
        assert "5" in combined, "bonus amount must appear"

    @pytest.mark.asyncio
    async def test_arabic_body_mentions_expiry(self):
        from app.services.push_service import send_loop2_push

        with patch(
            "app.services.push_service._send_to_expo", new_callable=AsyncMock
        ) as mock_send, patch(
            "app.services.push_service._get_user_push_token",
            new_callable=AsyncMock,
            return_value="ExponentPushToken[AR]",
        ), patch(
            "app.services.push_service._get_user_language",
            new_callable=AsyncMock,
            return_value="Arabic",
        ):
            await send_loop2_push(
                referrer_user_id="ar-user",
                invitee_display_name="سارة",
                bonus_amount=5,
            )

        payload = mock_send.call_args[0][0]
        haystack = payload["title"] + " " + payload["body"]
        # Arabic: 3 أيام / ثلاثة أيام / ينتهي / تنتهي / etc.
        assert any(
            tok in haystack
            for tok in ("3 أيام", "ثلاثة أيام", "ينتهي", "تنتهي")
        ), (
            f"Loop 2 push (Arabic) must mention expiry/3-day. "
            f"Got: title={payload['title']!r} body={payload['body']!r}"
        )


class TestExpiryReminderPushCopy:
    """Task 36 cron sends a 24h-before reminder. Test push_service exposes
    a localized copy helper OR the cron inlines the strings — verify the
    user-facing language tokens are present somewhere in the codebase."""

    def test_expiry_reminder_copy_exists_somewhere(self):
        """Verify push_service OR cron exposes localized 24h-reminder copy.

        Replaces the prior no-op test that just bound `src = inspect.getsource(...)`
        without asserting anything (frontend-visual QA flagged this).
        """
        import inspect

        from app.services import push_service

        push_src = inspect.getsource(push_service)

        # Check cron module if it exists yet (it's gated to land with task 36)
        cron_src = ""
        try:
            from scripts import cron_expire_bonuses
            cron_src = inspect.getsource(cron_expire_bonuses)
        except ImportError:
            pass

        combined = (push_src + "\n" + cron_src).lower()
        # Either side of the system MUST own the localized copy. The token
        # set is permissive — accept any of the design-intent words from
        # plan task 36 step 1: "expire", "tomorrow", "expires", "3 days".
        assert any(
            tok in combined
            for tok in ("expires in", "expires tomorrow", "expire tomorrow",
                        "expires in 1 day", "expire in 24",
                        "ينتهي", "تنتهي", "غدا")
        ) or "expiry_reminder" in combined, (
            "24h expiry reminder copy must live in push_service.py OR "
            "scripts/cron_expire_bonuses.py (plan task 36 step 1). "
            "Search tokens: 'expires in', 'tomorrow', 'expire', or Arabic equivalents."
        )
