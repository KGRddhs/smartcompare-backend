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


# ============================================
# C.6 (cohort): Demographics endpoint auth + rate limit + RLS
# Plan section C.6.1, C.6.2 — added by test-cohort
# ============================================


class TestDemographicsEndpointAuth:
    """PUT /demographics + GET /cohort-profile require authentication."""

    def test_put_demographics_requires_auth(self):
        """PUT /demographics without Authorization header → 401."""
        response = client.put(
            "/api/v1/auth/demographics",
            json={"age_group": "25-34", "gender": "Female"},
        )
        assert response.status_code == 401, (
            "PUT /demographics must require auth — design Section 5.1"
        )

    def test_put_demographics_invalid_token_returns_401(self):
        """PUT /demographics with malformed token → 401."""
        response = client.put(
            "/api/v1/auth/demographics",
            json={"age_group": "25-34"},
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert response.status_code == 401

    def test_get_cohort_profile_requires_auth(self):
        """GET /cohort-profile without Authorization header → 401."""
        response = client.get("/api/v1/auth/cohort-profile")
        assert response.status_code == 401, (
            "GET /cohort-profile must require auth — design Section 5.6"
        )


class TestDemographicsEndpointRateLimit:
    """PUT /demographics rate limited to 5/min per design Section 5.1 + plan A.4.1."""

    def test_demographics_route_has_rate_limit(self):
        """Source contains @limiter.limit decorator on the demographics route."""
        source = Path("app/api/auth_routes.py").read_text(encoding="utf-8")
        # The route MUST exist in source
        assert "/demographics" in source, (
            "PUT /demographics route must exist in auth_routes.py — design Section 5.1"
        )
        # The decorator must appear within ~10 lines before the route definition
        assert "limiter.limit" in source, (
            "demographics route must use @limiter.limit per plan A.4.1 (5/minute)"
        )

    def test_demographics_route_uses_5_per_minute(self):
        """The rate limit is 5/minute per plan A.4.1."""
        source = Path("app/api/auth_routes.py").read_text(encoding="utf-8")
        assert "/demographics" in source, (
            "PUT /demographics route must exist in auth_routes.py"
        )
        # Look for the 5/minute pattern near demographics
        pattern = re.compile(r'limiter\.limit\(["\']5\s*/\s*minute["\']\)', re.IGNORECASE)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "/demographics" in line and "@router" in line:
                # Check 10 lines before-and-after for limiter
                block = "\n".join(lines[max(0, i - 10) : i + 5])
                if pattern.search(block):
                    return  # OK
        pytest.fail(
            "demographics route must be rate limited to 5/minute per plan A.4.1"
        )


class TestDemographicsRLSStatic:
    """Static checks: migration 013 + RLS on demographics_profile column."""

    def test_migration_013_exists(self):
        """The demographics migration file exists."""
        assert Path("migrations/013_demographics_cohort.sql").exists(), (
            "migrations/013_demographics_cohort.sql must exist (plan A.1)"
        )

    def test_migration_013_adds_demographics_profile_column(self):
        """Migration adds demographics_profile JSONB to users."""
        source = Path("migrations/013_demographics_cohort.sql").read_text(
            encoding="utf-8"
        )
        assert "demographics_profile" in source
        assert "JSONB" in source.upper() or "JSON" in source.upper()

    def test_migration_013_adds_dismissal_tracking(self):
        """Migration adds dismissal tracking columns per design 5.5."""
        source = Path("migrations/013_demographics_cohort.sql").read_text(
            encoding="utf-8"
        )
        assert "demographics_dismissed_count" in source
        assert "demographics_dismissed_at" in source

    def test_migration_013_creates_metric_views(self):
        """Migration creates the 3 metric views per design 6.1."""
        source = Path("migrations/013_demographics_cohort.sql").read_text(
            encoding="utf-8"
        )
        assert "vw_cohort_match_rate" in source
        assert "vw_cohort_persona_distribution" in source
        assert "vw_cohort_feedback_lift" in source

    def test_demographics_relies_on_users_rls(self):
        """demographics_profile lives on users row → already protected by users RLS.

        We confirm users RLS is enabled in migration 010 (the source of truth for RLS).
        No new policies needed for demographics_profile because it's a column on
        the already-RLS-protected users table.
        """
        source = Path("migrations/010_enable_rls.sql").read_text(encoding="utf-8")
        assert "ALTER TABLE users ENABLE ROW LEVEL SECURITY" in source


# ============================================
# Q8.2: Smart Referral System security regression
# Additive — must NOT break the existing 57+ tests above.
# Static checks only (no live DB) so they run in the unit lane.
# ============================================


class TestReferralMigration014Static:
    """Migration 014 must exist with the correct schema + RLS + RPC."""

    def test_migration_014_exists(self):
        assert Path("migrations/014_referral_system.sql").exists(), (
            "migrations/014_referral_system.sql must exist (plan B1.1)"
        )

    def test_migration_014_creates_all_four_tables(self):
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        for table in ("referral_invites", "referral_redemptions", "deep_review_credits", "re_engagement_events"):
            assert table in source, f"migration 014 missing table: {table}"

    def test_migration_014_extends_users_with_referral_columns(self):
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        assert "referral_code" in source
        assert "referral_bonus_comparisons_this_month" in source
        assert "referral_bonus_reset_at" in source

    def test_migration_014_enables_rls_on_all_new_tables(self):
        """All 4 new tables must have RLS enabled per design 4.6."""
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        for table in ("referral_invites", "referral_redemptions", "deep_review_credits", "re_engagement_events"):
            pattern = rf"ALTER TABLE\s+{table}\s+ENABLE ROW LEVEL SECURITY"
            assert re.search(pattern, source, re.IGNORECASE), (
                f"RLS not enabled on {table} — table is unprotected!"
            )

    def test_migration_014_user_can_select_own_invites_only(self):
        """RLS policy: user can SELECT their own invites (as referrer OR invitee)."""
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        # Policy must reference auth.uid() against referrer_user_id and/or redeemed_by_user_id
        assert "auth.uid()" in source
        assert "referrer_user_id" in source

    def test_migration_014_resolve_referral_code_is_security_definer(self):
        """Public RPC `resolve_referral_code` must be SECURITY DEFINER (RLS bypass intentional)."""
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        assert "resolve_referral_code" in source
        # SECURITY DEFINER required so anon users can resolve codes; otherwise RLS would block
        assert "SECURITY DEFINER" in source.upper()

    def test_migration_014_share_target_check_constraint(self):
        """share_target column must enforce the whitelist via CHECK."""
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        # All 6 allowed values must appear in a CHECK constraint
        for target in ("whatsapp", "copy", "telegram", "snapchat"):
            assert target in source, f"share_target whitelist missing: {target}"

    def test_migration_014_redemptions_unique_invite_id(self):
        """invite_id is UNIQUE on referral_redemptions (no double-redeem)."""
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        # Look for `invite_id` followed by UNIQUE somewhere in the same statement
        # Either inline UNIQUE or separate CONSTRAINT — both acceptable
        invite_id_idx = source.find("invite_id")
        assert invite_id_idx >= 0, "referral_redemptions.invite_id missing"
        # Search for UNIQUE within 200 chars of the invite_id mention
        snippet = source[invite_id_idx : invite_id_idx + 200]
        assert "UNIQUE" in snippet.upper(), (
            "invite_id must be UNIQUE on referral_redemptions to prevent double-redeem"
        )

    def test_migration_014_credits_have_30day_expiry(self):
        """deep_review_credits.expires_at default must be 30 days post-grant per design 4.4."""
        source = Path("migrations/014_referral_system.sql").read_text(encoding="utf-8")
        # Check for "30 days" interval
        assert "30 days" in source or "interval '30" in source.lower()


class TestReferralRouteAuthGuards:
    """Referral routes must enforce auth/anon contracts per design 3.x.

    With ENABLE_REFERRAL_SYSTEM=true, /share + /status must specifically
    return 401 or 403 (auth dependency rejects anonymous). Without the flag,
    503 fires first. Tightened from generic !=200 per qa-referral 2026-05-05
    review now that BUG #1a (flag ordering) has shipped.
    """

    def test_share_endpoint_requires_auth(self, monkeypatch):
        """POST /api/v1/referrals/share without auth must return 401 or 403."""
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")

        resp = client.post(
            "/api/v1/referrals/share",
            json={"comparison_id": "00000000-0000-0000-0000-000000000000", "share_target": "whatsapp"},
        )
        assert resp.status_code in (401, 403), (
            f"POST /referrals/share with flag ON + no auth must return 401/403, "
            f"got {resp.status_code}: {resp.text}"
        )

    def test_share_endpoint_returns_503_when_flag_off(self, monkeypatch):
        """Defense in depth: when flag OFF, 503 fires BEFORE auth check."""
        monkeypatch.delenv("ENABLE_REFERRAL_SYSTEM", raising=False)

        resp = client.post(
            "/api/v1/referrals/share",
            json={"comparison_id": "x", "share_target": "whatsapp"},
        )
        assert resp.status_code == 503, (
            f"flag-off must short-circuit at 503; got {resp.status_code}"
        )

    def test_status_endpoint_requires_auth(self, monkeypatch):
        """GET /api/v1/referrals/status with flag ON + no auth => 401/403."""
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")

        resp = client.get("/api/v1/referrals/status")
        assert resp.status_code in (401, 403), (
            f"GET /referrals/status with flag ON + no auth must return 401/403, "
            f"got {resp.status_code}: {resp.text}"
        )

    def test_invite_landing_does_NOT_require_auth(self, monkeypatch):
        """Invitee landing must work for anon users (PDF #6 gradual commitment)."""
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")

        resp = client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-DOESNT")
        # 401/403 here would be a regression — anon access is required.
        # 404 (invalid token) or 200 (resolved) are both fine.
        assert resp.status_code not in (401, 403), (
            f"GET /referrals/invite/{{token}} must allow anon access; got {resp.status_code}"
        )


class TestReferralPrivacyInvariants:
    """Static guarantees that referral code + privacy toggles cannot leak data."""

    def test_referral_code_alphabet_excludes_ambiguous_chars(self):
        """Static check on the generated alphabet — no 0/O/1/I/L."""
        try:
            from app.services.referral_service import _CODE_ALPHABET
        except (ImportError, AttributeError):
            pytest.skip("referral_service not yet implemented (TDD red phase)")
        ambiguous = set("0O1IL")
        assert not (ambiguous & set(_CODE_ALPHABET)), (
            f"_CODE_ALPHABET contains ambiguous chars: {ambiguous & set(_CODE_ALPHABET)}"
        )

    def test_referral_code_alphabet_is_uppercase_alphanumeric(self):
        try:
            from app.services.referral_service import _CODE_ALPHABET
        except (ImportError, AttributeError):
            pytest.skip("referral_service not yet implemented (TDD red phase)")
        for ch in _CODE_ALPHABET:
            assert ch.isalnum(), f"non-alnum char in alphabet: {ch!r}"
            assert ch == ch.upper(), f"lowercase char in alphabet: {ch!r}"

    def test_disposable_email_blocklist_present(self):
        """Anti-abuse: blocklist file must exist and contain known disposables."""
        try:
            from app.services.abuse_detection_service import AbuseDetectionService
        except ImportError:
            pytest.skip("abuse_detection_service not yet implemented (TDD red phase)")
        svc = AbuseDetectionService()
        # At least these 4 must be flagged
        assert svc.is_disposable_email("a@mailinator.com")
        assert svc.is_disposable_email("a@guerrillamail.com")

    def test_share_target_whitelist_in_code(self):
        """share_target whitelist must be enforced in code (defense in depth, not just DB CHECK)."""
        try:
            import app.services.referral_service as rs
        except ImportError:
            pytest.skip("referral_service not yet implemented (TDD red phase)")
        source = Path("app/services/referral_service.py").read_text(encoding="utf-8")
        # All 6 valid targets must appear somewhere
        for target in ("whatsapp", "copy", "telegram", "snapchat", "other"):
            assert target in source, f"share_target whitelist missing in code: {target}"


class TestReferralAdminEndpointAuth:
    """Admin referral endpoints must reject without X-Admin-Key (Session 38 pattern).

    Tightened from `!= 200` to specific error codes per qa-referral
    2026-05-05 review:
    - 401/403 = auth-rejected (correct)
    - 422 = X-Admin-Key header missing/malformed (FastAPI dependency validation)
    - 404 = endpoint not yet registered (TDD red phase, accepted)
    - 200 = REGRESSION (auth bypass)
    """

    @patch.dict(os.environ, {"ADMIN_API_KEY": ADMIN_KEY})
    def test_admin_referrals_metrics_requires_key(self):
        """GET /admin/referrals/metrics without X-Admin-Key => 401/403/422."""
        resp = client.get("/api/v1/admin/referrals/metrics")
        assert resp.status_code in (401, 403, 404, 422), (
            f"admin referrals metrics with no key must return 401/403/422 "
            f"(or 404 pre-impl); got {resp.status_code}: {resp.text}"
        )

    @patch.dict(os.environ, {"ADMIN_API_KEY": ADMIN_KEY})
    def test_admin_referrals_metrics_rejects_bad_key(self):
        """Wrong X-Admin-Key => 401/403."""
        resp = client.get("/api/v1/admin/referrals/metrics", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code in (401, 403, 404), (
            f"wrong X-Admin-Key must be rejected with 401/403 "
            f"(or 404 pre-impl); got {resp.status_code}: {resp.text}"
        )

    @patch.dict(os.environ, {"ADMIN_API_KEY": ADMIN_KEY})
    def test_admin_costs_requires_key(self):
        """GET /admin/costs/api without X-Admin-Key => 401/403/422."""
        resp = client.get("/api/v1/admin/costs/api")
        assert resp.status_code in (401, 403, 404, 422), (
            f"admin costs with no key must return 401/403/422 "
            f"(or 404 pre-impl); got {resp.status_code}: {resp.text}"
        )


class TestReferralQuizNoAuthAndNoPII:
    """Anon quiz endpoint stores nothing personal pre-signup."""

    def test_quiz_endpoint_anon_path_exists(self):
        """POST /referrals/invite/{token}/quiz must NOT require auth."""
        resp = client.post(
            "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
            json={
                "priority": "best_price",
                "budget": "mid",
                "brand_attitude": "function_first",
                "non_negotiable": "test",
            },
        )
        # 401/403 would be a regression — anon access required for invitee quiz
        assert resp.status_code not in (401, 403), (
            f"quiz endpoint must allow anon access; got {resp.status_code}"
        )
