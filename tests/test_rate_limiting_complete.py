"""Tests verifying rate limiting on all public endpoints."""
import pytest
import uuid
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limiter state between tests."""
    from app.middleware.rate_limiter import limiter
    try:
        limiter.reset()
    except Exception:
        pass
    yield
    try:
        limiter.reset()
    except Exception:
        pass


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestRateLimitCoverage:
    """Verify every public endpoint has rate limiting configured."""

    def test_prices_endpoint_rate_limited(self, client):
        """GET /api/v1/text/prices/{product} should be rate limited."""
        for _ in range(25):
            resp = client.get("/api/v1/text/prices/test-product")
            if resp.status_code == 429:
                break
        assert resp.status_code == 429, "Prices endpoint should be rate limited"

    def test_url_detect_post_rate_limited(self, client):
        """POST /api/v1/url/detect should be rate limited."""
        for _ in range(25):
            resp = client.post("/api/v1/url/detect", json={"url": "https://example.com"})
            if resp.status_code == 429:
                break
        assert resp.status_code == 429, "URL detect POST should be rate limited"

    def test_url_detect_get_rate_limited(self, client):
        """GET /api/v1/url/detect should be rate limited."""
        for _ in range(25):
            resp = client.get("/api/v1/url/detect?url=https://example.com")
            if resp.status_code == 429:
                break
        assert resp.status_code == 429, "URL detect GET should be rate limited"

    def test_history_list_has_rate_limit(self):
        """GET /api/v1/comparisons/history should be registered with rate limiter."""
        from app.middleware.rate_limiter import limiter
        from app.api import history_routes  # noqa: ensure module loaded
        assert "app.api.history_routes.list_comparisons" in limiter._route_limits

    def test_history_get_has_rate_limit(self):
        """GET /api/v1/comparisons/{id} should be registered with rate limiter."""
        from app.middleware.rate_limiter import limiter
        from app.api import history_routes  # noqa
        assert "app.api.history_routes.get_comparison" in limiter._route_limits

    def test_history_delete_has_rate_limit(self):
        """DELETE /api/v1/comparisons/{id} should be registered with rate limiter."""
        from app.middleware.rate_limiter import limiter
        from app.api import history_routes  # noqa
        assert "app.api.history_routes.remove_comparison" in limiter._route_limits

    def test_share_create_has_rate_limit(self):
        """POST /api/v1/share/{id} should be registered with rate limiter."""
        from app.middleware.rate_limiter import limiter
        from app.api import share_routes  # noqa
        assert "app.api.share_routes.share_comparison" in limiter._route_limits

    def test_share_view_rate_limited(self, client):
        """GET /api/v1/share/{token} should be rate limited."""
        for _ in range(35):
            resp = client.get("/api/v1/share/abcdefghijklmnopqrstuv")
            if resp.status_code == 429:
                break
        assert resp.status_code == 429, "Share view should be rate limited"

    def test_auth_refresh_rate_limited(self, client):
        """POST /api/v1/auth/refresh should be rate limited."""
        for _ in range(15):
            resp = client.post("/api/v1/auth/refresh",
                               json={"refresh_token": "fake"})
            if resp.status_code == 429:
                break
        assert resp.status_code == 429, "Auth refresh should be rate limited"


class TestUrlDetectSsrf:
    """Verify SSRF protection on /url/detect endpoint."""

    def test_detect_blocks_private_ip(self, client):
        resp = client.post("/api/v1/url/detect", json={"url": "http://127.0.0.1/admin"})
        assert resp.status_code == 400
        body = resp.json()
        msg = body.get("detail", "") or body.get("error", "")
        assert "blocked" in msg.lower() or "security" in msg.lower()

    def test_detect_blocks_metadata_ip(self, client):
        resp = client.post("/api/v1/url/detect", json={"url": "http://169.254.169.254/latest/meta-data/"})
        assert resp.status_code == 400

    def test_detect_get_blocks_private_ip(self, client):
        resp = client.get("/api/v1/url/detect?url=http://127.0.0.1/admin")
        assert resp.status_code == 400

    def test_detect_allows_valid_url(self, client):
        resp = client.post("/api/v1/url/detect", json={"url": "https://amazon.ae/dp/B123"})
        assert resp.status_code == 200


class TestInputValidationGaps:
    """Verify input validation on previously unvalidated params."""

    def test_prices_product_max_length(self, client):
        long_product = "a" * 200
        resp = client.get(f"/api/v1/text/prices/{long_product}")
        assert resp.status_code == 422, "Product name >100 chars should be rejected"

    def test_history_search_max_length(self, client):
        long_search = "a" * 200
        resp = client.get(f"/api/v1/comparisons/history?search={long_search}",
                          headers={"Authorization": "Bearer fake"})
        # Should either be 422 (validation) or 401 (auth) — not 500
        assert resp.status_code in (401, 422)

    def test_share_token_format_validation(self, client):
        resp = client.get("/api/v1/share/invalid!@#$%token")
        assert resp.status_code == 422, "Invalid share token format should be rejected"
