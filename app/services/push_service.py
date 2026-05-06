"""Expo Push wrapper for Loop 2 + re-engagement notifications.

Fire-and-forget by design: every public function swallows transport
errors after logging so a failed push never crashes the caller. Plan
tasks B4.4 and B5.3.

Push token + language are stored on ``users`` (``expo_push_token``,
``preferences->>'language'``). The HTTP layer to Expo is encapsulated
in ``_send_to_expo``; tests patch it directly.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_HTTP_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


# ---------- public API ----------


async def send_push(
    *,
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict[str, Any]] = None,
) -> None:
    """Generic single-recipient Expo push. Silently no-ops if the user
    has no token. Errors are logged, never raised."""
    token = await _get_user_push_token(user_id)
    if not token:
        return
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }
    try:
        await _send_to_expo(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[push] send_push failed for user=%s: %s", user_id, exc)


async def send_loop2_push(
    *,
    referrer_user_id: Optional[str],
    invitee_display_name: str,
    bonus_amount: int,
) -> None:
    """Loop 2 referrer push — design Section 3.8.

    Localised to the referrer's preference (English / Arabic). The
    invitee's display name is interpolated into the body text; bonus
    amount is the +5 (free) or +10 (premium) capacity bump.
    """
    if not referrer_user_id:
        return

    token = await _get_user_push_token(referrer_user_id)
    if not token:
        return

    language = (await _get_user_language(referrer_user_id)) or "English"
    title, body = _loop2_copy(language, invitee_display_name, bonus_amount)
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": {"url": "qaren://profile/referrals", "type": "loop2"},
    }
    try:
        await _send_to_expo(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[push] Loop 2 push failed for referrer=%s: %s", referrer_user_id, exc)


async def send_reengagement_push(
    *,
    user_id: str,
    event_type: str,
    title: str,
    body: str,
    deep_link_url: str,
) -> None:
    """Generic re-engagement push (design Section 3.9). The selector in
    ``reengagement_service.py`` has already chosen the localised copy
    and deep-link target; we just send."""
    token = await _get_user_push_token(user_id)
    if not token:
        return
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": {"url": deep_link_url, "type": event_type},
    }
    try:
        await _send_to_expo(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[push] reengagement push failed for user=%s: %s", user_id, exc)


# ---------- internals (patched by tests) ----------


async def _get_user_push_token(user_id: str) -> Optional[str]:
    """Read ``users.expo_push_token`` for the user. Returns None on any
    error, missing column, or empty token (graceful degradation)."""
    try:
        client = get_admin_supabase_client()
        resp = (
            client.table("users")
            .select("expo_push_token")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return (resp.data or {}).get("expo_push_token") or None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[push] no token for %s: %s", user_id, exc)
        return None


async def _get_user_language(user_id: str) -> str:
    """Read ``preferences.language`` for the user; default English."""
    try:
        client = get_admin_supabase_client()
        resp = (
            client.table("users")
            .select("preferences")
            .eq("id", user_id)
            .single()
            .execute()
        )
        prefs = (resp.data or {}).get("preferences") or {}
        return prefs.get("language") or "English"
    except Exception as exc:  # noqa: BLE001
        logger.debug("[push] language lookup failed for %s: %s", user_id, exc)
        return "English"


async def _send_to_expo(payload: dict[str, Any]) -> None:
    """POST a single-message body to Expo Push. Tests patch this directly."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as http:
        response = await http.post(
            _EXPO_PUSH_URL,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        # Expo returns 200 with per-message status — non-200 is a transport
        # failure we want surfaced to the caller's try/except.
        response.raise_for_status()


# ---------- copy ----------


def _loop2_copy(language: str, invitee_display_name: str, bonus: int) -> tuple[str, str]:
    """Return (title, body) for the Loop 2 push in the user's language."""
    name = invitee_display_name or "Your friend"
    if language == "Arabic":
        title = f"{name} قررت بفضلك"
        body = f"+{bonus} مقارنات إضافية هذا الشهر."
    else:
        title = f"{name} decided thanks to you."
        body = f"+{bonus} comparisons added this month."
    return title, body
