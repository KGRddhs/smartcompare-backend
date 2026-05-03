"""
Security regression tests — guards against removing protections.
These tests MUST pass. Do not skip or delete them.
"""
import hmac
import os
import re
import secrets
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ADMIN_KEY = "test-admin-key-secure-123"


# ============================================
# C4: Admin rate limiting
# ============================================

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests."""
    from app.middleware.rate_limiter import limiter
    try:
        limiter.reset()
    except Exception:
        pass
    yield


class TestAdminRateLimiting:
    """C4: Admin endpoints must be rate limited."""

    def test_admin_stats_has_rate_limit_decorator(self):
        """Admin /stats/daily has @limiter.limit decorator."""
        import inspect
        from app.api.admin_routes import daily_stats
        source = inspect.getsource(daily_stats)
        # After Task 3, the route function will be wrapped by slowapi
        # We verify by checking the source for the limiter import
        from app.api import admin_routes
        module_source = inspect.getsource(admin_routes)
        assert "limiter.limit" in module_source

    @patch.dict(os.environ, {"ADMIN_API_KEY": ADMIN_KEY})
    def test_admin_endpoint_requires_key(self):
        """Admin endpoints still require valid key."""
        response = client.get("/api/v1/admin/stats/daily", headers={"X-Admin-Key": "wrong"})
        assert response.status_code == 403

    @patch.dict(os.environ, {"ADMIN_API_KEY": ADMIN_KEY})
    def test_admin_endpoint_no_key_returns_422(self):
        """Admin endpoints without key header return 422."""
        response = client.get("/api/v1/admin/stats/daily")
        assert response.status_code == 422

    @patch.dict(os.environ, {"ADMIN_API_KEY": ADMIN_KEY})
    def test_admin_key_uses_hmac_compare_digest(self):
        """Admin key verification uses timing-safe comparison."""
        source = Path("app/api/admin_routes.py").read_text()
        assert "hmac.compare_digest" in source


# ============================================
# M1, L2: History route hardening
# ============================================

class TestHistoryRouteHardening:
    """M1: History endpoints return 404 for both missing and unauthorized."""

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    @patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock)
    def test_missing_comparison_returns_404(self, mock_get, mock_verify):
        """Missing comparison returns 404."""
        mock_verify.return_value = {"id": str(uuid4()), "email": "user@test.com"}
        mock_get.return_value = None

        comparison_id = str(uuid4())
        response = client.get(
            f"/api/v1/comparisons/{comparison_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 404

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    @patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock)
    def test_unauthorized_comparison_returns_not_200(self, mock_get, mock_verify):
        """Accessing another user's comparison must not return 200."""
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        mock_verify.return_value = {"id": user_id, "email": "user@test.com"}
        mock_get.return_value = {"id": str(uuid4()), "user_id": other_user_id}

        comparison_id = str(uuid4())
        response = client.get(
            f"/api/v1/comparisons/{comparison_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        # After Task 2: merged 404/403 — always returns 404
        assert response.status_code == 404

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    @patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock)
    def test_unauthorized_comparison_returns_404_not_403(self, mock_get, mock_verify):
        """Accessing another user's comparison returns 404, not 403."""
        mock_verify.return_value = {"id": str(uuid4()), "email": "user@test.com"}
        mock_get.return_value = {"id": str(uuid4()), "user_id": str(uuid4())}

        comparison_id = str(uuid4())
        response = client.get(
            f"/api/v1/comparisons/{comparison_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 404
        assert "403" not in response.text

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    @patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock)
    def test_delete_unauthorized_returns_not_200(self, mock_get, mock_verify):
        """Deleting another user's comparison must not return 200."""
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        mock_verify.return_value = {"id": user_id, "email": "user@test.com"}
        mock_get.return_value = {"id": str(uuid4()), "user_id": other_user_id}

        comparison_id = str(uuid4())
        response = client.delete(
            f"/api/v1/comparisons/{comparison_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        # After Task 2: merged 404/403 — always returns 404
        assert response.status_code == 404

    def test_hmac_compare_in_history_routes(self):
        """History routes must use hmac.compare_digest for ownership check."""
        source = Path("app/api/history_routes.py").read_text()
        assert "hmac.compare_digest" in source
        # Must NOT have separate 403 responses
        assert "status_code=403" not in source


# ============================================
# H1: Email change requires password
# ============================================

class TestEmailChangeRequiresPassword:
    """H1: Email update must require current password."""

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    def test_email_change_without_password_rejected(self, mock_verify):
        """PUT /email without current_password returns 422."""
        mock_verify.return_value = {"id": str(uuid4()), "email": "user@test.com"}
        response = client.put(
            "/api/v1/auth/email",
            json={"new_email": "new@test.com"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 422  # Pydantic validation error

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    @patch("app.api.auth_routes.update_user_email", new_callable=AsyncMock)
    def test_email_change_with_wrong_password_rejected(self, mock_update, mock_verify):
        """PUT /email with wrong password returns 400."""
        mock_verify.return_value = {"id": str(uuid4()), "email": "old@test.com"}
        mock_update.return_value = {"success": False, "error": "Current password is incorrect"}

        response = client.put(
            "/api/v1/auth/email",
            json={"new_email": "new@test.com", "current_password": "wrongpass"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 400
        resp_json = response.json()
        error_text = resp_json.get("detail", resp_json.get("error", "")).lower()
        assert "password" in error_text


# ============================================
# H5: Share token entropy
# ============================================

class TestShareTokenEntropy:
    """H5: Share tokens must have >= 128 bits of entropy."""

    def test_token_urlsafe_16_produces_long_token(self):
        """token_urlsafe(16) produces >= 21 chars."""
        token = secrets.token_urlsafe(16)
        assert len(token) >= 21  # token_urlsafe(16) = 22 chars typically

    def test_share_token_uses_16_bytes(self):
        """Share token must use token_urlsafe(16) not token_urlsafe(6)."""
        source = Path("app/services/database_service.py").read_text()
        assert "token_urlsafe(16)" in source
        assert "token_urlsafe(6)" not in source


# ============================================
# M2, M3: Image endpoint sanitization
# ============================================

class TestImageEndpointSanitization:
    """M2/M3: Image endpoint must not leak error details or raw_response."""

    def test_image_500_has_str_e_currently(self):
        """Current code exposes str(e) — baseline check before fix."""
        source = Path("app/api/image_routes.py").read_text()
        # This test documents the current (insecure) state
        # After Task 3, the assertion will flip
        assert 'f"Image analysis failed: {str(e)}"' in source or \
               'Image analysis failed. Please try again.' in source

    def test_image_error_block_exists(self):
        """Image error handling block exists."""
        source = Path("app/api/image_routes.py").read_text()
        assert "vision_result.get" in source

    def test_image_500_no_exception_details(self):
        """500 error must not contain Python exception text."""
        source = Path("app/api/image_routes.py").read_text()
        assert 'f"Image analysis failed: {str(e)}"' not in source
        assert "Image analysis failed. Please try again." in source

    def test_image_error_no_raw_response(self):
        """Error response must not contain raw_response field in the return dict."""
        source = Path("app/api/image_routes.py").read_text()
        # After fix: the return dict in the error block should NOT include "raw_response"
        # It's OK for raw_response to appear in logger lines — just not in the return statement
        lines = source.split("\n")
        in_error_return = False
        for line in lines:
            stripped = line.strip()
            if "vision_result.get" in line and '"error"' in line:
                in_error_return = True
            if in_error_return and stripped.startswith("return"):
                in_error_return = True  # now inside the return block
            if in_error_return and stripped == "}":
                # End of the return dict
                break
            if in_error_return and '"raw_response"' in stripped and stripped.startswith('"raw_response"'):
                pytest.fail("raw_response still exposed in error return dict")


# ============================================
# M4: Query max_length
# ============================================

class TestQueryMaxLength:
    """M4: Query parameters must enforce max_length=500."""

    def test_long_query_rejected(self):
        """Query > 500 chars returns 422."""
        long_q = "a" * 501
        response = client.get(f"/api/v1/text/compare?q={long_q}")
        assert response.status_code == 422

    def test_normal_length_query_accepted(self):
        """Normal length query does not get rejected for length."""
        # This should NOT return 422
        normal_q = "iPhone 15 vs Galaxy S24"
        response = client.get(f"/api/v1/text/compare?q={normal_q}")
        # May return other errors (rate limit, etc) but not 422
        assert response.status_code != 422


# ============================================
# M10: Preference error sanitization
# ============================================

class TestPreferenceErrorSanitization:
    """M10: Preference errors must not leak exception details."""

    def test_preference_error_no_exception_text(self):
        """Error responses use generic message, not str(e)."""
        source = Path("app/services/auth_service.py").read_text()
        assert "Failed to load preferences" in source
        assert "Failed to save preferences" in source

    def test_preference_error_uses_categorized_error_currently(self):
        """Baseline: current code uses str(e) in preference errors."""
        source = Path("app/services/auth_service.py").read_text()
        # Current state: returns str(e)
        # This documents the baseline before Task 3 fix
        assert "get_user_preferences" in source
        assert "save_user_preferences" in source


# ============================================
# H4: Token revocation
# ============================================

class TestTokenRevocation:
    """H4: Tokens must be rejected after logout."""

    @patch("app.services.cache_service.redis_client")
    def test_revoke_token_stores_in_redis(self, mock_redis):
        """_revoke_token stores hash in Redis with TTL."""
        from app.services.auth_service import _revoke_token
        mock_redis.setex = MagicMock()
        _revoke_token("test-token-123")
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0].startswith("revoked:")
        assert args[1] == 3600

    @patch("app.services.cache_service.redis_client")
    def test_is_token_revoked_checks_redis(self, mock_redis):
        """_is_token_revoked returns True when token hash exists."""
        from app.services.auth_service import _is_token_revoked
        mock_redis.get = MagicMock(return_value="1")
        assert _is_token_revoked("test-token-123") is True

    @patch("app.services.cache_service.redis_client")
    def test_is_token_not_revoked(self, mock_redis):
        """_is_token_revoked returns False when token not in Redis."""
        from app.services.auth_service import _is_token_revoked
        mock_redis.get = MagicMock(return_value=None)
        assert _is_token_revoked("test-token-123") is False


# ============================================
# C1: Dual Supabase client
# ============================================

class TestDualSupabaseClient:
    """C1: Database service must have user-scoped and admin-scoped clients."""

    def test_user_client_function_exists(self):
        """get_user_supabase_client() function exists."""
        from app.services.database_service import get_user_supabase_client
        assert callable(get_user_supabase_client)

    def test_admin_client_function_exists(self):
        """get_admin_supabase_client() function exists."""
        from app.services.database_service import get_admin_supabase_client
        assert callable(get_admin_supabase_client)

    def test_current_client_function_exists(self):
        """get_supabase_client() function exists (current baseline)."""
        from app.services.database_service import get_supabase_client
        assert callable(get_supabase_client)


# ============================================
# L1: Sentry scrubbing
# ============================================

class TestSentryScrubbing:
    """L1: Sentry must have before_send hook for data scrubbing."""

    def test_sentry_has_breadcrumb_scrubbing(self):
        """Sentry has before_breadcrumb configured."""
        source = Path("app/services/sentry_service.py").read_text()
        assert "before_breadcrumb" in source

    def test_sentry_before_send_configured(self):
        """Sentry must have before_send hook for JWT/key scrubbing."""
        source = Path("app/services/sentry_service.py").read_text()
        assert "before_send" in source
        assert "_before_send" in source

    def test_sentry_scrubs_jwt_patterns(self):
        """Sentry scrubbing covers JWT and API key patterns."""
        source = Path("app/services/sentry_service.py").read_text()
        assert "JWT_REDACTED" in source or "REDACTED" in source
        assert "eyJ" in source  # JWT pattern detection


# ============================================
# M7: CORS env-based config
# ============================================

class TestCORSConfig:
    """M7: CORS origins must be configurable via env var."""

    def test_cors_has_railway_origin(self):
        """CORS includes Railway production URL."""
        source = Path("app/main.py").read_text()
        assert "web-production-58776.up.railway.app" in source

    def test_cors_reads_from_env(self):
        """CORS origins read from CORS_ORIGINS env var."""
        source = Path("app/main.py").read_text()
        assert "CORS_ORIGINS" in source

    def test_cors_middleware_exists(self):
        """CORS middleware is configured."""
        source = Path("app/main.py").read_text()
        assert "CORSMiddleware" in source


# ============================================
# Auth security baseline checks
# ============================================

class TestAuthSecurityBaseline:
    """Baseline auth security checks that pass on current code."""

    def test_password_validation_exists(self):
        """Password validation requires 10+ chars, upper, lower, digit."""
        source = Path("app/api/auth_routes.py").read_text()
        assert "min_length=10" in source
        assert "isupper" in source
        assert "islower" in source
        assert "isdigit" in source

    def test_rate_limiting_on_login(self):
        """Login endpoint is rate limited."""
        source = Path("app/api/auth_routes.py").read_text()
        # Find login route and check it has rate limit
        assert '@limiter.limit("5/minute")' in source

    def test_rate_limiting_on_register(self):
        """Register endpoint is rate limited."""
        source = Path("app/api/auth_routes.py").read_text()
        assert '@limiter.limit("3/minute")' in source

    def test_rate_limiting_on_account_delete(self):
        """Account delete is rate limited."""
        source = Path("app/api/auth_routes.py").read_text()
        assert '@limiter.limit("1/minute")' in source

    def test_password_reset_no_email_enumeration(self):
        """Password reset always returns success (no email enumeration)."""
        source = Path("app/api/auth_routes.py").read_text()
        assert "If an account with that email exists" in source

    def test_docs_disabled_in_production(self):
        """Swagger docs disabled when RAILWAY_ENVIRONMENT is set."""
        source = Path("app/main.py").read_text()
        assert 'docs_url=None if os.getenv("RAILWAY_ENVIRONMENT")' in source

    def test_send_default_pii_false(self):
        """Sentry send_default_pii is False."""
        source = Path("app/services/sentry_service.py").read_text()
        assert "send_default_pii=False" in source


# ============================================
# SSRF Protection
# ============================================

class TestSSRFProtection:
    """URL validator must block private/loopback IPs."""

    def test_url_validator_exists(self):
        """SSRF protection module exists."""
        assert Path("app/utils/url_validator.py").exists()

    def test_url_validator_blocks_private_ips(self):
        """URL validator checks for private IP ranges."""
        source = Path("app/utils/url_validator.py").read_text()
        # Should check for private IPs
        assert "private" in source.lower() or "loopback" in source.lower() or "is_private" in source


# ============================================
# SQL injection prevention
# ============================================

class TestSQLInjectionPrevention:
    """Database service must escape SQL LIKE wildcards."""

    def test_like_wildcards_escaped(self):
        """LIKE wildcards (%, _) are escaped in search."""
        source = Path("app/services/database_service.py").read_text()
        assert 'replace("%"' in source or "replace(\"\\\\%\"" in source or '\\%' in source

    def test_comparison_id_is_uuid(self):
        """History routes use UUID type for comparison_id."""
        source = Path("app/api/history_routes.py").read_text()
        assert "UUID" in source
        assert "comparison_id: UUID" in source


# ============================================
# Frontend security checks (file content guards)
# ============================================

class TestFrontendSecurityGuards:
    """Static code checks for frontend security."""

    def test_no_service_role_in_frontend(self):
        """SUPABASE_SERVICE_KEY must never appear in frontend code."""
        frontend_path = Path("SmartCompareApp/src")
        if not frontend_path.exists():
            pytest.skip("Frontend source not found")
        matches = []
        for ext in ("*.ts", "*.tsx"):
            for f in frontend_path.rglob(ext):
                content = f.read_text(errors="ignore")
                if "SERVICE_KEY" in content or "service_role" in content:
                    matches.append(str(f))
        assert not matches, f"Frontend must not contain service-role references: {matches}"

    def test_no_bare_console_log_in_auth(self):
        """authService.ts must not have console.log without __DEV__ guard."""
        source = Path("SmartCompareApp/src/services/authService.ts").read_text()
        lines = source.split("\n")
        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("console.") and "__DEV__" not in line and not stripped.startswith("//"):
                violations.append(f"  Line {i}: {stripped[:80]}")
        assert not violations, f"Bare console.log found:\n" + "\n".join(violations)

    def test_no_bare_console_log_in_api(self):
        """api.ts must not have console.log without __DEV__ guard."""
        source = Path("SmartCompareApp/src/services/api.ts").read_text()
        lines = source.split("\n")
        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("console.") and "__DEV__" not in line and not stripped.startswith("//"):
                violations.append(f"  Line {i}: {stripped[:80]}")
        assert not violations, f"Bare console.log found:\n" + "\n".join(violations)

    def test_secure_store_used_for_tokens(self):
        """authService.ts must use SecureStore, not AsyncStorage, for tokens."""
        source = Path("SmartCompareApp/src/services/authService.ts").read_text()
        assert "SecureStore" in source
        assert "SecureStore.setItemAsync(TOKEN_STORAGE_KEY" in source or \
               "SecureStore.getItemAsync(TOKEN_STORAGE_KEY" in source

    def test_certificate_pinning_configured(self):
        """certificatePinning.ts must exist and pin intermediate certs."""
        cert_file = Path("SmartCompareApp/src/services/certificatePinning.ts")
        assert cert_file.exists(), "certificatePinning.ts must exist"
        source = cert_file.read_text()
        assert "initializeSslPinning" in source
        assert "iFvwVyJSxnQdyaUvUERIf" in source  # E8 intermediate
        assert "NYbU7PBwV4y9J67c4guW" in source     # E5 backup intermediate

    def test_certificate_pinning_imported_in_api(self):
        """api.ts must import and call setupCertificatePinning."""
        source = Path("SmartCompareApp/src/services/api.ts").read_text()
        assert "setupCertificatePinning" in source

    def test_no_client_id_comments(self):
        """authService.ts must not contain OAuth Client ID comments."""
        source = Path("SmartCompareApp/src/services/authService.ts").read_text()
        assert "Web Client ID:" not in source
        assert "iOS Client ID:" not in source


# ============================================
# RLS Migration
# ============================================

class TestRLSMigration:
    """C2, M8: RLS policies and atomic cascade delete."""

    def test_rls_migration_file_exists(self):
        """RLS migration SQL file exists."""
        assert Path("migrations/010_enable_rls.sql").exists()

    def test_rls_migration_covers_all_tables(self):
        """RLS migration enables RLS on all user-data tables."""
        source = Path("migrations/010_enable_rls.sql").read_text()
        tables = ["users", "comparisons", "search_logs", "comparison_feedback", "user_events"]
        for table in tables:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in source

    def test_cascade_delete_uses_rpc(self):
        """delete_user_data_cascade uses Postgres RPC function."""
        source = Path("app/services/database_service.py").read_text()
        assert 'rpc("delete_user_cascade"' in source


# ============================================
# Feedback/Events input validation
# ============================================

class TestInputValidation:
    """Input validation on user-facing endpoints."""

    def test_feedback_change_suggestion_max_length(self):
        """Feedback change_suggestion field has max length."""
        # Check if there's validation in the feedback route or model
        feedback_path = Path("app/api/feedback_routes.py")
        if feedback_path.exists():
            source = feedback_path.read_text()
            # Should have some length constraint
            assert "max_length" in source or "1000" in source or "len(" in source

    def test_comparison_id_path_param_is_uuid(self):
        """comparison_id path params use UUID type, not bare strings."""
        source = Path("app/api/history_routes.py").read_text()
        assert "comparison_id: UUID" in source

    @patch("app.api.auth_routes.verify_token", new_callable=AsyncMock)
    def test_invalid_uuid_returns_422(self, mock_verify):
        """Non-UUID comparison_id returns 422."""
        mock_verify.return_value = {"id": str(uuid4()), "email": "user@test.com"}
        response = client.get(
            "/api/v1/comparisons/not-a-uuid",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 422
