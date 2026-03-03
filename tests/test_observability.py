"""Tests for observability -- Sentry init, error handler, structured logging."""
import pytest
import json
import logging
from unittest.mock import patch, MagicMock


# ── Sentry init tests ──

def test_sentry_init_disabled_when_no_dsn():
    """init_sentry() is a no-op when SENTRY_DSN is empty."""
    with patch.dict("os.environ", {"SENTRY_DSN": ""}, clear=False):
        with patch("sentry_sdk.init") as mock_init:
            from app.services.sentry_service import init_sentry
            init_sentry()
            mock_init.assert_not_called()


def test_sentry_init_called_with_dsn():
    """init_sentry() calls sentry_sdk.init when DSN is set."""
    with patch.dict("os.environ", {"SENTRY_DSN": "https://abc@sentry.io/123"}, clear=False):
        with patch("sentry_sdk.init") as mock_init:
            # Need to reload the module to pick up new env
            import importlib
            import app.services.sentry_service as mod
            importlib.reload(mod)
            mod.init_sentry()
            mock_init.assert_called_once()
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["dsn"] == "https://abc@sentry.io/123"
            assert call_kwargs["send_default_pii"] is False
