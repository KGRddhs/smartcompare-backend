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

import httpx
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

    @pytest.mark.asyncio
    async def test_no_token_skips_silently(self):
        from app.services.push_service import send_reengagement_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value=None):

            await send_reengagement_push(
                user_id="u",
                event_type="decision_insight",
                title="t", body="b", deep_link_url="qaren://x",
            )
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_failure_does_not_crash(self):
        """Network errors swallowed for re-engagement too."""
        from app.services.push_service import send_reengagement_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock, side_effect=httpx.ConnectError("dns")), \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[X]"):

            # Should NOT raise
            await send_reengagement_push(
                user_id="u",
                event_type="cohort_curiosity",
                title="t", body="b", deep_link_url="qaren://x",
            )


# ============================================
# Generic send_push (the simple wrapper)
# ============================================


class TestSendPushGeneric:
    @pytest.mark.asyncio
    async def test_send_push_with_data_payload(self):
        from app.services.push_service import send_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[U]"):

            await send_push(user_id="u", title="Hello", body="World", data={"foo": "bar"})

            mock_send.assert_called_once()
            payload = mock_send.call_args[0][0]
            assert payload["to"] == "ExponentPushToken[U]"
            assert payload["title"] == "Hello"
            assert payload["body"] == "World"
            assert payload["data"] == {"foo": "bar"}
            assert payload["sound"] == "default"

    @pytest.mark.asyncio
    async def test_send_push_default_data_is_empty_dict(self):
        from app.services.push_service import send_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[U]"):

            await send_push(user_id="u", title="T", body="B")

            payload = mock_send.call_args[0][0]
            assert payload["data"] == {}

    @pytest.mark.asyncio
    async def test_send_push_no_token_short_circuits(self):
        from app.services.push_service import send_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value=None):

            await send_push(user_id="u", title="T", body="B")
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_push_swallows_errors(self):
        from app.services.push_service import send_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock, side_effect=Exception("boom")), \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[X]"):

            # Should NOT raise
            await send_push(user_id="u", title="T", body="B")


# ============================================
# send_loop2_push edge cases (covers line 67 — None referrer guard)
# ============================================


class TestSendLoop2PushEdgeCases:
    @pytest.mark.asyncio
    async def test_none_referrer_id_is_no_op(self):
        """If referrer_user_id is None (rare, guard), short-circuit without lookup."""
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock) as mock_token:

            await send_loop2_push(
                referrer_user_id=None,
                invitee_display_name="Sarah",
                bonus_amount=5,
            )

            mock_token.assert_not_called()
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_language_when_lookup_returns_none(self):
        """If _get_user_language returns None, default to English."""
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[X]"), \
             patch("app.services.push_service._get_user_language", new_callable=AsyncMock, return_value=None):

            await send_loop2_push(referrer_user_id="r", invitee_display_name="Sara", bonus_amount=5)

            payload = mock_send.call_args[0][0]
            # English fallback => no Arabic chars
            text = payload["title"] + payload["body"]
            has_arabic = any(0x0600 <= ord(c) <= 0x06FF for c in text)
            assert not has_arabic, f"None language should default to English, got: {text!r}"

    @pytest.mark.asyncio
    async def test_empty_invitee_name_uses_friend_fallback(self):
        from app.services.push_service import send_loop2_push

        with patch("app.services.push_service._send_to_expo", new_callable=AsyncMock) as mock_send, \
             patch("app.services.push_service._get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[X]"), \
             patch("app.services.push_service._get_user_language", new_callable=AsyncMock, return_value="English"):

            await send_loop2_push(referrer_user_id="r", invitee_display_name="", bonus_amount=5)

            payload = mock_send.call_args[0][0]
            assert "friend" in payload["title"].lower()


# ============================================
# Internal helpers (covers _get_user_push_token + _get_user_language + _send_to_expo)
# ============================================


class TestInternalHelpers:
    @pytest.mark.asyncio
    async def test_get_user_push_token_returns_value(self):
        from app.services.push_service import _get_user_push_token

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"expo_push_token": "ExponentPushToken[ABC]"}
        )

        with patch("app.services.push_service.get_admin_supabase_client", return_value=client):
            tok = await _get_user_push_token("u")

        assert tok == "ExponentPushToken[ABC]"

    @pytest.mark.asyncio
    async def test_get_user_push_token_handles_missing(self):
        from app.services.push_service import _get_user_push_token

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={})

        with patch("app.services.push_service.get_admin_supabase_client", return_value=client):
            tok = await _get_user_push_token("u")

        assert tok is None

    @pytest.mark.asyncio
    async def test_get_user_push_token_swallows_db_errors(self):
        from app.services.push_service import _get_user_push_token

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("schema mismatch")

        with patch("app.services.push_service.get_admin_supabase_client", return_value=client):
            tok = await _get_user_push_token("u")

        assert tok is None

    @pytest.mark.asyncio
    async def test_get_user_language_returns_arabic(self):
        from app.services.push_service import _get_user_language

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"preferences": {"language": "Arabic"}}
        )

        with patch("app.services.push_service.get_admin_supabase_client", return_value=client):
            lang = await _get_user_language("u")

        assert lang == "Arabic"

    @pytest.mark.asyncio
    async def test_get_user_language_default_english(self):
        from app.services.push_service import _get_user_language

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"preferences": {}}
        )

        with patch("app.services.push_service.get_admin_supabase_client", return_value=client):
            lang = await _get_user_language("u")

        assert lang == "English"

    @pytest.mark.asyncio
    async def test_get_user_language_swallows_db_errors(self):
        from app.services.push_service import _get_user_language

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("db down")

        with patch("app.services.push_service.get_admin_supabase_client", return_value=client):
            lang = await _get_user_language("u")

        assert lang == "English"

    @pytest.mark.asyncio
    async def test_send_to_expo_posts_to_expo_url(self):
        from app.services.push_service import _send_to_expo, _EXPO_PUSH_URL

        # Mock httpx.AsyncClient context manager
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.push_service.httpx.AsyncClient", return_value=mock_client_instance):
            await _send_to_expo({"to": "tok", "title": "T", "body": "B"})

        mock_client_instance.post.assert_called_once()
        call_url = mock_client_instance.post.call_args[0][0]
        assert call_url == _EXPO_PUSH_URL

    @pytest.mark.asyncio
    async def test_send_to_expo_raises_on_non_2xx(self):
        from app.services.push_service import _send_to_expo

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "500 server error", request=MagicMock(), response=MagicMock(status_code=500)
        ))

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.push_service.httpx.AsyncClient", return_value=mock_client_instance):
            with pytest.raises(httpx.HTTPStatusError):
                await _send_to_expo({"to": "tok", "title": "T", "body": "B"})
