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


# ── Structured Logging tests ──

def test_structured_formatter_outputs_json():
    """StructuredFormatter produces valid JSON log lines."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="Hello %s", args=("world",), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Hello world"
    assert "timestamp" in parsed
    assert parsed["module"] == "test"


def test_structured_formatter_includes_exception():
    """StructuredFormatter includes exception info when present."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="Failed", args=(), exc_info=sys.exc_info(),
        )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "exception" in parsed
    assert "ValueError: test error" in parsed["exception"]


def test_structured_formatter_includes_request_id():
    """StructuredFormatter includes request_id when present on record."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="with request", args=(), exc_info=None,
    )
    record.request_id = "req-abc-123"
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["request_id"] == "req-abc-123"


def test_structured_formatter_omits_null_request_id():
    """StructuredFormatter omits request_id when not set."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="no request id", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "request_id" not in parsed


def test_configure_logging_sets_level():
    """configure_logging applies the requested log level."""
    from app.middleware.logging_config import configure_logging

    configure_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG

    # Reset
    configure_logging("INFO")
    assert root.level == logging.INFO


def test_configure_logging_quiets_noisy_libraries():
    """configure_logging sets httpx/httpcore to WARNING."""
    from app.middleware.logging_config import configure_logging

    configure_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING

    # Reset
    configure_logging("INFO")
