"""Tests for security middleware -- headers, rate limiting, request IDs."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient


# ── Request ID tests ──

def _make_test_app():
    """Create minimal FastAPI app with middleware for testing."""
    from fastapi import FastAPI, Request
    from app.middleware.request_id import RequestIDMiddleware

    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/test")
    async def test_endpoint(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return test_app


def test_request_id_generated_when_missing():
    """Middleware generates UUID request ID when none provided."""
    app = _make_test_app()
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    # Response header has request ID
    assert "X-Request-ID" in response.headers
    rid = response.headers["X-Request-ID"]
    # Valid UUID format (8-4-4-4-12)
    assert len(rid.split("-")) == 5
    # Endpoint received it in request.state
    assert response.json()["request_id"] == rid


def test_request_id_preserved_when_provided():
    """Middleware preserves client-provided request ID."""
    app = _make_test_app()
    client = TestClient(app)
    my_id = "my-custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": my_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == my_id
    assert response.json()["request_id"] == my_id
