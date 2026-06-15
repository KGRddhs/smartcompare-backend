"""WS1 (D2) — route-level failure → HTTP surface mapping.

Pins `_surface_comparison_failure` (text_routes) + the error_handler unwrap so
the D2 contract can't regress:
  - CONTENT_UNAVAILABLE → returned as a 200 body (dict), code preserved.
  - TIMEOUT             → HTTPException(503) with structured detail; the
    unified envelope surfaces code:"TIMEOUT" (NOT the 503 default
    FEATURE_DISABLED).
  - INSUFFICIENT_DATA   → HTTPException(400), code preserved.
  - unrecognized code   → HTTPException(400), code preserved.
  - no code             → HTTPException(400), plain string detail.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

import pytest
from fastapi import HTTPException

from app.api.text_routes import _surface_comparison_failure
from app.middleware.error_handler import (
    STATUS_CODE_MAP,
    _is_structured_detail,
)


class TestSurfaceComparisonFailureHelper:
    def test_content_unavailable_returns_body(self):
        result = {"success": False, "code": "CONTENT_UNAVAILABLE",
                  "error": "blocked", "layer": "L1"}
        out = _surface_comparison_failure(result)
        assert out is result  # returned as-is for a 200 early-return

    def test_timeout_raises_503_with_code(self):
        result = {"success": False, "code": "TIMEOUT", "error": "soft msg"}
        with pytest.raises(HTTPException) as exc:
            _surface_comparison_failure(result)
        assert exc.value.status_code == 503
        assert isinstance(exc.value.detail, dict)
        assert exc.value.detail["code"] == "TIMEOUT"
        assert exc.value.detail["error"] == "soft msg"

    def test_insufficient_data_raises_400_with_code(self):
        result = {"success": False, "code": "INSUFFICIENT_DATA", "error": "incomplete"}
        with pytest.raises(HTTPException) as exc:
            _surface_comparison_failure(result)
        assert exc.value.status_code == 400
        assert exc.value.detail["code"] == "INSUFFICIENT_DATA"

    def test_unknown_code_raises_400_with_code(self):
        result = {"success": False, "code": "WEIRD", "error": "x"}
        with pytest.raises(HTTPException) as exc:
            _surface_comparison_failure(result)
        assert exc.value.status_code == 400
        assert exc.value.detail["code"] == "WEIRD"

    def test_no_code_raises_400_plain(self):
        result = {"success": False, "error": "Comparison failed"}
        with pytest.raises(HTTPException) as exc:
            _surface_comparison_failure(result)
        assert exc.value.status_code == 400
        assert exc.value.detail == "Comparison failed"


class TestErrorHandlerPreserves503Timeout:
    """The D2 mechanism rests on error_handler overriding the 503-default code
    when a structured detail supplies its own. Pin both halves."""

    def test_503_default_is_feature_disabled(self):
        # The bare default (no structured detail) is FEATURE_DISABLED — this is
        # exactly why TIMEOUT must travel as a structured detail.
        assert STATUS_CODE_MAP[503] == "FEATURE_DISABLED"

    def test_structured_timeout_detail_is_recognized(self):
        detail = {"code": "TIMEOUT", "error": "soft"}
        assert _is_structured_detail(detail) is True

    @pytest.mark.asyncio
    async def test_handler_surfaces_timeout_code_on_503(self):
        """End-to-end of the unwrap: a 503 HTTPException carrying
        {code:TIMEOUT} yields a body with code 'TIMEOUT', not FEATURE_DISABLED."""
        from app.middleware.error_handler import http_exception_handler

        class _Req:
            class state:  # noqa: N801 — minimal stub
                request_id = "req-test"

        exc = HTTPException(status_code=503, detail={"code": "TIMEOUT", "error": "soft"})
        resp = await http_exception_handler(_Req(), exc)
        assert resp.status_code == 503
        import json
        body = json.loads(bytes(resp.body).decode())
        assert body["code"] == "TIMEOUT"
        assert body["success"] is False
        assert body["error"] == "soft"
