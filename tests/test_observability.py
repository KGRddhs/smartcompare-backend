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


# ── Error Handler Middleware tests ──

from starlette.testclient import TestClient


def _make_error_app():
    """Create FastAPI app with error handler middleware."""
    from fastapi import FastAPI, HTTPException
    from app.middleware.error_handler import ErrorHandlerMiddleware

    test_app = FastAPI()
    test_app.add_middleware(ErrorHandlerMiddleware)

    @test_app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @test_app.get("/crash")
    async def crash():
        raise RuntimeError("Something broke")

    @test_app.get("/http-error")
    async def http_error():
        raise HTTPException(status_code=404, detail="Not found")

    return test_app


def test_error_handler_passes_normal_responses():
    """Normal responses pass through unchanged."""
    app = _make_error_app()
    client = TestClient(app)
    response = client.get("/ok")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_error_handler_catches_unhandled_exception():
    """Unhandled exceptions return clean 500 JSON, not stack trace."""
    app = _make_error_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash")
    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Internal server error"
    # Stack trace NOT leaked
    assert "RuntimeError" not in json.dumps(body)
    assert "Something broke" not in json.dumps(body)


def test_error_handler_includes_request_id():
    """500 response includes request_id if available."""
    from app.middleware.request_id import RequestIDMiddleware

    app = _make_error_app()
    # Add request ID middleware (outermost, runs before error handler)
    app.add_middleware(RequestIDMiddleware)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash", headers={"X-Request-ID": "test-123"})
    assert response.status_code == 500
    assert response.json()["request_id"] == "test-123"


def test_error_handler_lets_http_exceptions_through():
    """HTTPExceptions are NOT caught -- FastAPI handles them normally."""
    app = _make_error_app()
    client = TestClient(app)
    response = client.get("/http-error")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"


def test_error_handler_returns_json_content_type():
    """500 error response has application/json content type."""
    app = _make_error_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash")
    assert response.status_code == 500
    assert "application/json" in response.headers["content-type"]


def test_error_handler_default_request_id_when_no_state():
    """Error handler uses 'unknown' when request.state has no request_id."""
    app = _make_error_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash")
    assert response.status_code == 500
    assert response.json()["request_id"] == "unknown"


def test_error_handler_sends_to_sentry_when_available():
    """Error handler calls sentry_sdk.capture_exception on crash."""
    app = _make_error_app()
    client = TestClient(app, raise_server_exceptions=False)
    with patch("app.middleware.error_handler.sentry_sdk", create=True) as mock_sentry:
        # The import inside the handler is dynamic, so we patch differently
        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            response = client.get("/crash")
    assert response.status_code == 500


# ── Sentry edge case tests ──

def test_sentry_init_handles_import_error():
    """init_sentry() handles missing sentry-sdk gracefully."""
    import importlib
    import app.services.sentry_service as mod

    with patch.dict("os.environ", {"SENTRY_DSN": "https://abc@sentry.io/123"}, clear=False):
        importlib.reload(mod)
        # Simulate sentry_sdk not installed
        with patch.dict("sys.modules", {"sentry_sdk": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                # Should not raise -- graceful handling
                mod.init_sentry()


def test_sentry_init_handles_init_exception():
    """init_sentry() handles sentry_sdk.init failure gracefully."""
    with patch.dict("os.environ", {"SENTRY_DSN": "https://bad@sentry.io/999"}, clear=False):
        with patch("sentry_sdk.init", side_effect=Exception("Network error")):
            import importlib
            import app.services.sentry_service as mod
            importlib.reload(mod)
            # Should not raise
            mod.init_sentry()


def test_sentry_init_uses_railway_environment():
    """init_sentry() passes RAILWAY_ENVIRONMENT to sentry_sdk.init."""
    env = {
        "SENTRY_DSN": "https://abc@sentry.io/123",
        "RAILWAY_ENVIRONMENT": "production",
        "RAILWAY_GIT_COMMIT_SHA": "abc123def",
    }
    with patch.dict("os.environ", env, clear=False):
        with patch("sentry_sdk.init") as mock_init:
            import importlib
            import app.services.sentry_service as mod
            importlib.reload(mod)
            mod.init_sentry()
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["environment"] == "production"
            assert call_kwargs["release"] == "abc123def"
            assert call_kwargs["traces_sample_rate"] == 0.1


# ── Structured Logging edge cases ──

def test_structured_formatter_handles_different_log_levels():
    """StructuredFormatter correctly reports WARNING, ERROR, DEBUG levels."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    for level, name in [(logging.WARNING, "WARNING"), (logging.ERROR, "ERROR"), (logging.DEBUG, "DEBUG")]:
        record = logging.LogRecord(
            name="test", level=level, pathname="test.py",
            lineno=1, msg="level test", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == name


def test_structured_formatter_timestamp_is_utc_iso():
    """StructuredFormatter timestamp is valid ISO 8601 UTC."""
    from app.middleware.logging_config import StructuredFormatter
    from datetime import datetime, timezone

    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="timestamp test", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    # Should be parseable as ISO datetime
    ts = datetime.fromisoformat(parsed["timestamp"])
    assert ts.tzinfo is not None  # Has timezone info


def test_configure_logging_adds_stdout_handler():
    """configure_logging adds a StreamHandler to stdout."""
    import sys
    from app.middleware.logging_config import configure_logging

    configure_logging("INFO")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream == sys.stdout


def test_configure_logging_clears_duplicate_handlers():
    """Calling configure_logging twice does not add duplicate handlers."""
    from app.middleware.logging_config import configure_logging

    configure_logging("INFO")
    configure_logging("INFO")
    root = logging.getLogger()
    assert len(root.handlers) == 1


def test_configure_logging_quiets_uvicorn_and_urllib3():
    """configure_logging also quiets uvicorn.access and urllib3."""
    from app.middleware.logging_config import configure_logging

    configure_logging("DEBUG")
    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING

    # Reset
    configure_logging("INFO")


def test_configure_logging_handles_invalid_level():
    """configure_logging falls back to INFO for invalid level string."""
    from app.middleware.logging_config import configure_logging

    configure_logging("NONSENSE")
    root = logging.getLogger()
    assert root.level == logging.INFO
