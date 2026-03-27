"""Tests for security hardening features -- SSRF protection, headers, admin auth."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.utils.url_validator import validate_external_url


client = TestClient(app)
ADMIN_KEY = "test-admin-key-secure-123"


@pytest.fixture(autouse=True)
def mock_admin_key():
    """Mock admin key for all tests."""
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY}):
        yield


# ============================================
# SSRF Protection Tests (url_validator.py)
# ============================================

class TestSSRFProtection:
    """Test SSRF protection in validate_external_url()."""

    def test_valid_external_url_passes(self):
        """Valid external HTTPS URL passes validation."""
        assert validate_external_url("https://example.com/product/123") is True

    def test_valid_gcc_retailer_url_passes(self):
        """Valid GCC retailer URL passes validation."""
        # Mock DNS resolution to avoid network dependency
        mock_addr_info = [
            (2, 1, 6, '', ('104.21.75.123', 443)),  # Public Cloudflare IP
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr_info):
            assert validate_external_url("https://ounass.bh/product/123") is True

    def test_valid_http_url_passes(self):
        """HTTP (not just HTTPS) URLs are allowed."""
        assert validate_external_url("http://example.com/page") is True

    def test_blocks_ftp_scheme(self):
        """Non-HTTP schemes are blocked (ftp://)."""
        assert validate_external_url("ftp://example.com/file.txt") is False

    def test_blocks_file_scheme(self):
        """Non-HTTP schemes are blocked (file://)."""
        assert validate_external_url("file:///etc/passwd") is False

    def test_blocks_javascript_scheme(self):
        """Non-HTTP schemes are blocked (javascript:)."""
        assert validate_external_url("javascript:alert(1)") is False

    def test_blocks_data_scheme(self):
        """Non-HTTP schemes are blocked (data:)."""
        assert validate_external_url("data:text/html,<script>alert(1)</script>") is False

    def test_blocks_localhost(self):
        """Localhost (loopback) is blocked."""
        assert validate_external_url("http://localhost/admin") is False

    def test_blocks_127_0_0_1(self):
        """127.0.0.1 (loopback) is blocked."""
        assert validate_external_url("http://127.0.0.1/admin") is False

    def test_blocks_127_1(self):
        """127.0.0.1 shorthand (127.1) is blocked."""
        assert validate_external_url("http://127.1/admin") is False

    def test_blocks_private_ip_10_x(self):
        """Private IP 10.x.x.x is blocked."""
        assert validate_external_url("http://10.0.0.1/internal") is False

    def test_blocks_private_ip_192_168(self):
        """Private IP 192.168.x.x is blocked."""
        assert validate_external_url("http://192.168.1.1/router") is False

    def test_blocks_private_ip_172_16(self):
        """Private IP 172.16.x.x (Docker) is blocked."""
        assert validate_external_url("http://172.16.0.1/container") is False

    def test_blocks_private_ip_172_31(self):
        """Private IP 172.31.x.x (upper range) is blocked."""
        assert validate_external_url("http://172.31.255.254/internal") is False

    def test_blocks_link_local_169_254(self):
        """Link-local IP 169.254.x.x is blocked."""
        assert validate_external_url("http://169.254.169.254/metadata") is False

    def test_blocks_ipv6_loopback(self):
        """IPv6 loopback (::1) is blocked."""
        assert validate_external_url("http://[::1]/admin") is False

    def test_blocks_ipv6_private(self):
        """IPv6 private addresses are blocked."""
        assert validate_external_url("http://[fd00::1]/internal") is False

    def test_blocks_empty_url(self):
        """Empty URL is rejected."""
        assert validate_external_url("") is False

    def test_blocks_no_scheme(self):
        """URL without scheme is rejected."""
        assert validate_external_url("example.com/page") is False

    def test_blocks_malformed_url(self):
        """Malformed URL is rejected."""
        assert validate_external_url("not a url at all") is False

    def test_blocks_url_with_no_hostname(self):
        """URL with missing hostname is rejected."""
        assert validate_external_url("https:///path") is False

    def test_dns_rebinding_attack_blocked(self):
        """DNS rebinding: public domain resolving to private IP is blocked."""
        # Mock DNS to return private IP for a public domain
        mock_addr_info = [
            (2, 1, 6, '', ('192.168.1.1', 80)),  # Private IP result
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr_info):
            assert validate_external_url("https://evil.example.com/page") is False

    def test_dns_rebinding_loopback_blocked(self):
        """DNS rebinding: domain resolving to loopback is blocked."""
        mock_addr_info = [
            (2, 1, 6, '', ('127.0.0.1', 80)),
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr_info):
            assert validate_external_url("https://rebinding.example.com/page") is False

    def test_dns_rebinding_link_local_blocked(self):
        """DNS rebinding: domain resolving to link-local is blocked."""
        mock_addr_info = [
            (2, 1, 6, '', ('169.254.169.254', 80)),
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr_info):
            assert validate_external_url("https://metadata.example.com/latest") is False

    def test_dns_resolution_failure_blocked(self):
        """Unresolvable hostnames are blocked."""
        import socket
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("Name resolution failed")):
            assert validate_external_url("https://does-not-exist.invalid/page") is False

    def test_multiple_ips_any_private_blocks(self):
        """If ANY resolved IP is private, URL is blocked."""
        # Domain resolves to both public and private IPs
        mock_addr_info = [
            (2, 1, 6, '', ('1.2.3.4', 80)),       # Public IP
            (2, 1, 6, '', ('10.0.0.1', 80)),      # Private IP
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr_info):
            assert validate_external_url("https://multi-ip.example.com/page") is False

    def test_all_public_ips_passes(self):
        """Domain with multiple public IPs passes."""
        mock_addr_info = [
            (2, 1, 6, '', ('1.2.3.4', 80)),
            (2, 1, 6, '', ('5.6.7.8', 80)),
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr_info):
            assert validate_external_url("https://cdn.example.com/file") is True

    def test_exception_during_validation_blocked(self):
        """Any exception during validation fails closed (blocked)."""
        with patch("ipaddress.ip_address", side_effect=Exception("Unexpected error")):
            assert validate_external_url("https://example.com/page") is False


# ============================================
# Security Headers Tests (middleware/security.py)
# ============================================

class TestSecurityHeaders:
    """Test security headers middleware adds all required headers."""

    def test_strict_transport_security_header(self):
        """Strict-Transport-Security header is present."""
        resp = client.get("/health")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in resp.headers["Strict-Transport-Security"]

    def test_content_security_policy_header(self):
        """Content-Security-Policy header is present."""
        resp = client.get("/health")
        assert "Content-Security-Policy" in resp.headers
        csp = resp.headers["Content-Security-Policy"]
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_x_content_type_options_header(self):
        """X-Content-Type-Options: nosniff header is present."""
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_header(self):
        """X-Frame-Options: DENY header is present."""
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy_header(self):
        """Referrer-Policy header is present."""
        resp = client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_x_xss_protection_header(self):
        """X-XSS-Protection header is present."""
        resp = client.get("/health")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_permissions_policy_header(self):
        """Permissions-Policy header is present and restrictive."""
        resp = client.get("/health")
        assert "Permissions-Policy" in resp.headers
        policy = resp.headers["Permissions-Policy"]
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy

    def test_security_headers_on_404(self):
        """Security headers present even on error responses."""
        resp = client.get("/nonexistent-endpoint-404")
        assert resp.status_code == 404
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "Strict-Transport-Security" in resp.headers

    def test_security_headers_on_post(self):
        """Security headers present on POST responses."""
        # Use a real endpoint that exists (will fail auth, but that's ok)
        resp = client.post("/api/v1/feedback", json={"comparison_id": "test", "rating": 1})
        # Any response code is fine, just check headers
        assert "X-Content-Type-Options" in resp.headers
        assert "X-Frame-Options" in resp.headers
        assert "Strict-Transport-Security" in resp.headers


# ============================================
# Admin Auth Tests (admin_routes.py)
# ============================================

class TestAdminAuth:
    """Test admin endpoints require X-Admin-Key header with correct value."""

    def test_admin_costs_requires_header(self):
        """GET /api/v1/admin/costs requires X-Admin-Key header."""
        resp = client.get("/api/v1/admin/costs")
        assert resp.status_code in (403, 422)  # 422 if missing, 403 if invalid

    def test_admin_costs_rejects_wrong_key(self):
        """GET /api/v1/admin/costs rejects incorrect key."""
        resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": "wrong-key"})
        assert resp.status_code == 403

    def test_admin_costs_accepts_correct_key(self):
        """GET /api/v1/admin/costs accepts correct key."""
        # Mock dependencies so we don't need real Supabase
        with patch("app.api.admin_routes.get_usage_summary", return_value={"providers": {}, "circuit_breakers": {}}), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200

    def test_admin_daily_stats_requires_auth(self):
        """GET /api/v1/admin/stats/daily requires admin auth."""
        resp = client.get("/api/v1/admin/stats/daily")
        assert resp.status_code in (403, 422)

    def test_admin_daily_stats_rejects_wrong_key(self):
        """GET /api/v1/admin/stats/daily rejects wrong key."""
        resp = client.get("/api/v1/admin/stats/daily", headers={"X-Admin-Key": "invalid"})
        assert resp.status_code == 403

    def test_admin_popular_queries_requires_auth(self):
        """GET /api/v1/admin/stats/popular requires admin auth."""
        resp = client.get("/api/v1/admin/stats/popular")
        assert resp.status_code in (403, 422)

    def test_admin_cost_trends_requires_auth(self):
        """GET /api/v1/admin/stats/costs requires admin auth."""
        resp = client.get("/api/v1/admin/stats/costs")
        assert resp.status_code in (403, 422)

    def test_admin_error_stats_requires_auth(self):
        """GET /api/v1/admin/stats/errors requires admin auth."""
        resp = client.get("/api/v1/admin/stats/errors")
        assert resp.status_code in (403, 422)

    def test_admin_product_stats_requires_auth(self):
        """GET /api/v1/admin/stats/products requires admin auth."""
        resp = client.get("/api/v1/admin/stats/products")
        assert resp.status_code in (403, 422)

    def test_verify_admin_key_uses_timing_safe_comparison(self):
        """verify_admin_key uses hmac.compare_digest (timing-safe)."""
        # This is a code inspection test - verify the function uses hmac.compare_digest
        import inspect
        from app.api.admin_routes import verify_admin_key
        source = inspect.getsource(verify_admin_key)
        assert "hmac.compare_digest" in source, "Admin auth must use timing-safe comparison"

    def test_empty_admin_key_env_rejects_all(self):
        """If ADMIN_API_KEY is empty, all requests are rejected."""
        with patch.dict("os.environ", {"ADMIN_API_KEY": ""}):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 403

    def test_admin_key_case_sensitive(self):
        """Admin key comparison is case-sensitive."""
        with patch("app.api.admin_routes.get_usage_summary", return_value={"providers": {}, "circuit_breakers": {}}), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            # Correct key
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            # Wrong case
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY.upper()})
            assert resp.status_code == 403


# ============================================
# Cache/Parse Admin Protection (text_routes.py)
# ============================================

class TestCacheParseAdminProtection:
    """Test DELETE /cache and GET /parse require admin auth."""

    def test_delete_cache_requires_admin_auth(self):
        """DELETE /api/v1/text/cache requires admin auth."""
        resp = client.delete("/api/v1/text/cache?q=iPhone")
        assert resp.status_code in (403, 422)

    def test_delete_cache_rejects_wrong_key(self):
        """DELETE /api/v1/text/cache rejects wrong admin key."""
        resp = client.delete("/api/v1/text/cache?q=iPhone", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code == 403

    def test_delete_cache_accepts_correct_key(self):
        """DELETE /api/v1/text/cache accepts correct admin key."""
        # Mock parse_product_query to avoid live GPT call (imported inside endpoint)
        with patch("app.services.extraction_service.parse_product_query") as mock_parse:
            mock_parse.return_value = {
                "products": [{"brand": "Apple", "name": "iPhone 15", "variant": None}]
            }
            resp = client.delete("/api/v1/text/cache?q=iPhone+15", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("success") is True

    def test_parse_query_requires_admin_auth(self):
        """GET /api/v1/text/parse requires admin auth."""
        resp = client.get("/api/v1/text/parse?q=iPhone+15")
        assert resp.status_code in (403, 422)

    def test_parse_query_rejects_wrong_key(self):
        """GET /api/v1/text/parse rejects wrong admin key."""
        resp = client.get("/api/v1/text/parse?q=iPhone+15", headers={"X-Admin-Key": "invalid"})
        assert resp.status_code == 403

    def test_parse_query_accepts_correct_key(self):
        """GET /api/v1/text/parse accepts correct admin key."""
        # Mock parse_product_query to avoid live GPT call (imported inside endpoint)
        with patch("app.services.extraction_service.parse_product_query") as mock_parse:
            mock_parse.return_value = {
                "products": [{"brand": "Apple", "name": "iPhone 15"}],
                "category": "electronics"
            }
            resp = client.get("/api/v1/text/parse?q=iPhone+15+vs+S24", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert "parsed" in data
            assert data["query"] == "iPhone 15 vs S24"


# ============================================
# Integration Tests (Combined Security)
# ============================================

class TestSecurityIntegration:
    """Integration tests combining multiple security features."""

    def test_admin_endpoint_has_security_headers(self):
        """Admin endpoints include security headers even when auth fails."""
        resp = client.get("/api/v1/admin/costs")
        # Should fail auth but still have security headers
        assert resp.status_code in (403, 422)
        assert "X-Content-Type-Options" in resp.headers
        assert "Strict-Transport-Security" in resp.headers

    def test_admin_endpoint_with_correct_auth_has_headers(self):
        """Admin endpoints with correct auth still include security headers."""
        with patch("app.api.admin_routes.get_usage_summary", return_value={"providers": {}, "circuit_breakers": {}}), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            assert "X-Content-Type-Options" in resp.headers
            assert "Strict-Transport-Security" in resp.headers
            assert "Content-Security-Policy" in resp.headers

    def test_timing_attack_resistance(self):
        """Admin key comparison should be timing-safe (hmac.compare_digest)."""
        # Verify hmac.compare_digest is used (inspected in earlier test)
        # Here we just verify behavior: wrong keys always return 403
        import time
        wrong_keys = ["a", "ab", "abc", "wrong-key", "x" * 100]
        times = []
        for wrong_key in wrong_keys:
            start = time.perf_counter()
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": wrong_key})
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            assert resp.status_code == 403
        # All responses should be 403 (can't reliably test timing in unit tests)

    def test_ssrf_protection_integrated(self):
        """SSRF protection is used when fetching external URLs."""
        # This is tested in other modules that use validate_external_url
        # Here we just verify the function is importable and works
        from app.utils.url_validator import validate_external_url
        assert validate_external_url("https://example.com") is True
        assert validate_external_url("http://127.0.0.1") is False
        assert validate_external_url("http://10.0.0.1") is False
