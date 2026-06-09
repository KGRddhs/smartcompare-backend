"""Regression test for B0-E Item 3 — `preferences_completed` lookup
silently-swallowed exception now emits a `logger.warning`.

B0-UnfinishedBiz audit Bucket 5 flagged three `except Exception: pass`
sites in `app/services/auth_service.py` (login / refresh_session /
sign_in_with_social) that silently dropped Supabase failures during
the `preferences_completed` field fetch. Zero user-facing symptoms
(prefs default to False), but a real observability gap during incidents.

The fix adds `logger.warning("[auth] preferences_completed lookup
failed: %s", e)` before the default-to-False fallthrough at each site.
"""
from __future__ import annotations

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-svc")


@pytest.mark.asyncio
async def test_login_logs_warning_when_preferences_lookup_raises(caplog):
    """`login_user` emits WARNING when the Supabase prefs lookup raises.

    Auth still succeeds with `preferences_completed=False` (existing
    contract preserved); the warning gives us a Sentry/Railway log line
    we can grep on during incidents.
    """
    from app.services import auth_service

    # Mock auth_client.sign_in_with_password — successful login
    fake_auth = MagicMock()
    fake_session = MagicMock(access_token="at", refresh_token="rt", expires_at=999)
    fake_user = MagicMock(id="user-abc", email="x@x.com")
    fake_auth.auth.sign_in_with_password.return_value = MagicMock(
        user=fake_user, session=fake_session
    )

    # Mock admin client — table().select().eq().single().execute() raises
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = RuntimeError(
        "supabase unreachable"
    )

    # Avoid hitting _enrich_response_with_profile during the test
    with patch.object(auth_service, "get_auth_client", return_value=fake_auth), \
         patch.object(auth_service, "get_admin_client", return_value=fake_admin), \
         patch.object(auth_service, "_enrich_response_with_profile",
                      side_effect=lambda r, _uid: r), \
         caplog.at_level(logging.WARNING, logger="app.services.auth_service"):
        result = await auth_service.login_user("x@x.com", "pw")

    assert result["success"] is True
    assert result["user"]["preferences_completed"] is False  # default-on-failure preserved
    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING
        and "preferences_completed lookup failed" in r.getMessage()
    ]
    assert len(warnings) == 1, (
        f"Expected exactly one WARNING about preferences_completed lookup; "
        f"got {len(warnings)}. All records: {[r.getMessage() for r in caplog.records]}"
    )
    assert "supabase unreachable" in warnings[0].getMessage()
