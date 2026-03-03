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


# ── Security Headers tests ──

def _make_secure_app():
    """Create FastAPI app with security headers middleware."""
    from fastapi import FastAPI
    from app.middleware.security import SecurityHeadersMiddleware

    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)

    @test_app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return test_app


def test_security_headers_present():
    """All security headers present on every response."""
    app = _make_secure_app()
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_security_headers_on_error_response():
    """Security headers present even on 404 responses."""
    app = _make_secure_app()
    client = TestClient(app)
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


# ── Rate Limiting tests ──

def _make_rate_limited_app():
    """Create FastAPI app with rate limiting."""
    from fastapi import FastAPI, Request
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.middleware.rate_limiter import limiter

    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @test_app.get("/limited")
    @limiter.limit("2/minute")
    async def limited_endpoint(request: Request):
        return {"ok": True}

    @test_app.get("/unlimited")
    async def unlimited_endpoint(request: Request):
        return {"ok": True}

    return test_app


def test_rate_limit_allows_under_limit():
    """Requests under rate limit succeed."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    response = client.get("/limited")
    assert response.status_code == 200


def test_rate_limit_blocks_over_limit():
    """Requests over rate limit return 429."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    # Use 2/minute limit -- first 2 succeed, third fails
    client.get("/limited")
    client.get("/limited")
    response = client.get("/limited")
    assert response.status_code == 429


def test_rate_limit_returns_error_detail():
    """429 response includes error detail."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    client.get("/limited")
    client.get("/limited")
    response = client.get("/limited")
    assert response.status_code == 429
    body = response.json()
    assert "error" in body or "detail" in body


def test_unlimited_endpoint_not_affected():
    """Endpoints without @limiter.limit are not rate limited."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    for _ in range(20):
        response = client.get("/unlimited")
        assert response.status_code == 200
