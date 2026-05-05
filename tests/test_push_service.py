"""Tests for B4.4 — push_service.py (Expo Push wrapper).

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
sections 3.8 (Loop 2 push) + 3.9 (re-engagement push) + plan task B4.4.

Push payload requirements:
- Title + body localized to recipient's preferred language (EN or AR)
- Deep link URL passed through `data.url` field for Expo handling
- Recipient's expo push token retrieved from users table
- Failures should be logged but not crash the caller (fire-and-forget)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# B4.4 — Module + class shape
# ============================================


class TestPushServiceShape:
    def test_module_importable(self):
        from app.services import push_service  # noqa: F401

    def test_send_push_function_exists(self):
        from app.services.push_service import send_push  # noqa: F401


# ============================================
# Loop 2 push (referrer-side)
# ============================================


class TestSendLoop2Push:
    """Loop 2 fires => push referrer with invitee name + bonus amount."""

    @pytest.mark.asyncio
    async def test_loop2_payload_includes_localized_title_and_body(self):
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[REF]"), \
             patch("app.services.push_service._get_user_language", new_callable=AsyncMock, return_value="English"):

            await send_loop2_push(
                referrer_user_id="ref-1",
                invitee_display_name="Sarah",
                bonus_amount=5,
            )

            mock_send.assert_called_once()
            payload = mock_send.call_args[0][0]
            # Token + title/body present
            assert payload["to"] == "ExponentPushToken[REF]"
            assert "Sarah" in payload["title"] + payload["body"], (
                "invitee name must appear in title or body"
            )
            assert "5" in payload["title"] + payload["body"], (
                "bonus amount must appear"
            )

    @pytest.mark.asyncio
    async def test_arabic_user_gets_arabic_copy(self):
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[AR]"), \
             patch("app.services.push_service._get_user_language", new_callable=AsyncMock, return_value="Arabic"):

            await send_loop2_push(
                referrer_user_id="ar-user",
                invitee_display_name="سارة",
                bonus_amount=5,
            )

            payload = mock_send.call_args[0][0]
            # Should contain at least one Arabic character
            text = payload["title"] + payload["body"]
            has_arabic = any(0x0600 <= ord(c) <= 0x06FF for c in text)
            assert has_arabic, f"Arabic user must get Arabic copy, got: {text!r}"

    @pytest.mark.asyncio
    async def test_no_push_token_silently_skips(self):
        """User without push token (e.g. opted out) — fire-and-forget no-op."""
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value=None), \
             patch("app.services.push_service._get_user_language", new_callable=AsyncMock, return_value="English"):

            # Should NOT raise
            await send_loop2_push(
                referrer_user_id="no-token",
                invitee_display_name="Sara",
                bonus_amount=5,
            )

            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_failure_does_not_crash_caller(self):
        """Network errors swallowed — fire-and-forget."""
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock, side_effect=Exception("network")), \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[X]"), \
             patch("app.services.push_service._get_user_language", new_callable=AsyncMock, return_value="English"):

            # Should NOT raise
            await send_loop2_push(referrer_user_id="r", invitee_display_name="S", bonus_amount=5)


# ============================================
# Re-engagement push (B5.3 — generic dispatcher)
# ============================================


class TestSendReengagementPush:
    @pytest.mark.asyncio
    async def test_decision_insight_payload_shape(self):
        from app.services.push_service import send_reengagement_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[U]"):

            await send_reengagement_push(
                user_id="u1",
                event_type="decision_insight",
                title="iPhone update: new reviews shifted the picture.",
                body="Re-check before buying.",
                deep_link_url="qaren://comparison/cmp-1?banner=insight",
            )

            mock_send.assert_called_once()
            payload = mock_send.call_args[0][0]
            assert payload["title"]
            assert payload["body"]
            # Deep link must propagate through Expo's data field
            assert payload.get("data", {}).get("url") == "qaren://comparison/cmp-1?banner=insight"
