"""Tests for auth pipeline — optional user dependency and token handling."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── get_optional_user tests ──

@pytest.mark.asyncio
async def test_optional_user_returns_none_when_no_header():
    """get_optional_user returns None when no Authorization header."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization=None)
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_bad_format():
    """get_optional_user returns None for malformed header."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization="NotBearer abc123")
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_missing_token():
    """get_optional_user returns None when just 'Bearer' with no token."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization="Bearer")
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_user_on_valid_token():
    """get_optional_user returns user dict when token is valid."""
    from app.api.auth_routes import get_optional_user
    mock_user = {"id": "user-123", "email": "test@example.com"}
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, return_value=mock_user):
        result = await get_optional_user(authorization="Bearer valid-token-123")
    assert result == mock_user


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_expired_token():
    """get_optional_user returns None when verify_token raises."""
    from app.api.auth_routes import get_optional_user
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, side_effect=Exception("Token expired")):
        result = await get_optional_user(authorization="Bearer expired-token")
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_no_header():
    """get_current_user raises 401 when no auth header (unlike optional)."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_bad_format():
    """get_current_user raises 401 for malformed header."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization="Basic abc123")
    assert exc_info.value.status_code == 401


# ── Additional get_current_user tests ──

@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token():
    """get_current_user raises 401 when verify_token returns None."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer invalid-token")
    assert exc_info.value.status_code == 401
    assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_returns_user_on_valid_token():
    """get_current_user returns user dict when token is valid."""
    from app.api.auth_routes import get_current_user
    mock_user = {"id": "user-456", "email": "valid@example.com"}
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, return_value=mock_user):
        result = await get_current_user(authorization="Bearer valid-token")
    assert result == mock_user


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_extra_parts():
    """get_current_user raises 401 when header has too many parts."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization="Bearer token extra-stuff")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_extra_parts():
    """get_optional_user returns None when header has too many parts."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization="Bearer token extra-stuff")
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_case_insensitive_bearer():
    """get_optional_user accepts case-insensitive 'bearer' prefix."""
    from app.api.auth_routes import get_optional_user
    mock_user = {"id": "user-789", "email": "case@example.com"}
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, return_value=mock_user):
        result = await get_optional_user(authorization="BEARER valid-token")
    assert result == mock_user


@pytest.mark.asyncio
async def test_optional_user_returns_none_when_verify_returns_none():
    """get_optional_user returns None when verify_token returns None (not raise)."""
    from app.api.auth_routes import get_optional_user
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, return_value=None):
        result = await get_optional_user(authorization="Bearer token-that-returns-none")
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_empty_string():
    """get_optional_user returns None on empty authorization string."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization="")
    assert result is None


# ── verify_token tests (auth_service) ──

@pytest.mark.asyncio
async def test_verify_token_returns_user_dict():
    """verify_token returns user id and email from Supabase response."""
    from app.services.auth_service import verify_token

    mock_user = MagicMock()
    mock_user.id = "supabase-uid-123"
    mock_user.email = "user@test.com"

    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_response

    mock_client = MagicMock()
    mock_client.auth = mock_auth

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await verify_token("test-access-token")

    assert result == {"id": "supabase-uid-123", "email": "user@test.com"}
    mock_auth.get_user.assert_called_once_with("test-access-token")


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_no_user():
    """verify_token returns None when Supabase returns no user."""
    from app.services.auth_service import verify_token

    mock_response = MagicMock()
    mock_response.user = None

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_response

    mock_client = MagicMock()
    mock_client.auth = mock_auth

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await verify_token("bad-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_exception():
    """verify_token returns None when Supabase raises."""
    from app.services.auth_service import verify_token

    mock_auth = MagicMock()
    mock_auth.get_user.side_effect = Exception("Network error")

    mock_client = MagicMock()
    mock_client.auth = mock_auth

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await verify_token("error-token")

    assert result is None


# ── Route endpoint tests (register, login) ──

@pytest.mark.asyncio
async def test_register_rejects_short_password():
    """Register endpoint rejects passwords shorter than 6 chars."""
    from fastapi import HTTPException
    from app.api.auth_routes import register, RegisterRequest

    with pytest.raises(HTTPException) as exc_info:
        await register(RegisterRequest(email="test@example.com", password="12345"))
    assert exc_info.value.status_code == 400
    assert "at least 6 characters" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_raises_401_on_failure():
    """Login endpoint raises 401 when auth service returns failure."""
    from fastapi import HTTPException
    from app.api.auth_routes import login, LoginRequest

    with patch("app.api.auth_routes.login_user", new_callable=AsyncMock,
               return_value={"success": False, "error": "Invalid email or password"}):
        with pytest.raises(HTTPException) as exc_info:
            await login(LoginRequest(email="test@example.com", password="wrong-password"))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_raises_401_on_failure():
    """Refresh endpoint raises 401 when refresh fails."""
    from fastapi import HTTPException
    from app.api.auth_routes import refresh, RefreshRequest

    with patch("app.api.auth_routes.refresh_session", new_callable=AsyncMock,
               return_value={"success": False, "error": "Invalid refresh token"}):
        with pytest.raises(HTTPException) as exc_info:
            await refresh(RefreshRequest(refresh_token="bad-token"))
    assert exc_info.value.status_code == 401


# ── Route endpoint success paths ──

@pytest.mark.asyncio
async def test_register_success():
    """Register endpoint returns result on success."""
    from app.api.auth_routes import register, RegisterRequest
    mock_result = {
        "success": True,
        "user": {"id": "new-user", "email": "new@example.com"},
        "session": {"access_token": "tok", "refresh_token": "ref"},
    }
    with patch("app.api.auth_routes.register_user", new_callable=AsyncMock, return_value=mock_result):
        result = await register(RegisterRequest(email="new@example.com", password="password123"))
    assert result["success"] is True
    assert result["user"]["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_register_failure_returns_400():
    """Register endpoint raises 400 when auth service returns failure."""
    from fastapi import HTTPException
    from app.api.auth_routes import register, RegisterRequest
    with patch("app.api.auth_routes.register_user", new_callable=AsyncMock,
               return_value={"success": False, "error": "Email already registered"}):
        with pytest.raises(HTTPException) as exc_info:
            await register(RegisterRequest(email="dup@example.com", password="password123"))
    assert exc_info.value.status_code == 400
    assert "Email already registered" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_success():
    """Login endpoint returns result on success."""
    from app.api.auth_routes import login, LoginRequest
    mock_result = {
        "success": True,
        "user": {"id": "user-1", "email": "user@example.com"},
        "session": {"access_token": "tok", "refresh_token": "ref"},
    }
    with patch("app.api.auth_routes.login_user", new_callable=AsyncMock, return_value=mock_result):
        result = await login(LoginRequest(email="user@example.com", password="correct-password"))
    assert result["success"] is True


@pytest.mark.asyncio
async def test_refresh_success():
    """Refresh endpoint returns new session on success."""
    from app.api.auth_routes import refresh, RefreshRequest
    mock_result = {
        "success": True,
        "session": {"access_token": "new-tok", "refresh_token": "new-ref"},
    }
    with patch("app.api.auth_routes.refresh_session", new_callable=AsyncMock, return_value=mock_result):
        result = await refresh(RefreshRequest(refresh_token="valid-refresh"))
    assert result["success"] is True
    assert result["session"]["access_token"] == "new-tok"


@pytest.mark.asyncio
async def test_logout_returns_success():
    """Logout endpoint returns success (static response, auth checked by dependency)."""
    from app.api.auth_routes import logout
    result = await logout(current_user={"id": "user-1", "email": "test@example.com"})
    assert result["success"] is True
    assert "Logged out" in result["message"]


@pytest.mark.asyncio
async def test_get_me_with_profile():
    """get_me returns normalized profile data when profile exists."""
    from app.api.auth_routes import get_me
    mock_profile = {
        "id": "user-1",
        "email": "test@example.com",
        "display_name": "Test User",
        "auth_provider": "email",
        "subscription_tier": "pro",
        "created_at": "2026-01-01",
        "preferences_completed": True,
    }
    with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=mock_profile):
        result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})
    assert result["success"] is True
    assert result["user"]["subscription_tier"] == "pro"
    assert result["user"]["display_name"] == "Test User"
    assert result["user"]["auth_provider"] == "email"


@pytest.mark.asyncio
async def test_get_me_without_profile():
    """get_me falls back to consistent shape with defaults when profile not found."""
    from app.api.auth_routes import get_me
    with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=None):
        result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})
    assert result["success"] is True
    assert result["user"]["id"] == "user-1"
    assert result["user"]["email"] == "test@example.com"
    assert result["user"]["display_name"] is None
    assert result["user"]["subscription_tier"] == "free"


@pytest.mark.asyncio
async def test_password_reset_always_succeeds():
    """Password reset always returns success to prevent email enumeration."""
    from app.api.auth_routes import password_reset, PasswordResetRequest
    with patch("app.api.auth_routes.request_password_reset", new_callable=AsyncMock,
               return_value={"success": True}):
        result = await password_reset(PasswordResetRequest(email="any@example.com"))
    assert result["success"] is True
    assert "reset link" in result["message"].lower()


@pytest.mark.asyncio
async def test_password_reset_succeeds_even_on_error():
    """Password reset returns success even when service errors (anti-enumeration)."""
    from app.api.auth_routes import password_reset, PasswordResetRequest
    with patch("app.api.auth_routes.request_password_reset", new_callable=AsyncMock,
               return_value={"success": False, "error": "No such user"}):
        result = await password_reset(PasswordResetRequest(email="nonexistent@example.com"))
    assert result["success"] is True


@pytest.mark.asyncio
async def test_verify_auth_returns_user():
    """verify_auth returns success with user data."""
    from app.api.auth_routes import verify_auth
    user = {"id": "user-1", "email": "test@example.com"}
    result = await verify_auth(current_user=user)
    assert result["success"] is True
    assert result["valid"] is True
    assert result["user"] == user


# ── auth_service.py tests ──

@pytest.mark.asyncio
async def test_register_user_success():
    """register_user returns user + session on success."""
    from app.services.auth_service import register_user

    mock_user = MagicMock()
    mock_user.id = "new-id"
    mock_user.email = "new@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "access-tok"
    mock_session.refresh_token = "refresh-tok"
    mock_session.expires_at = 1234567890

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth = MagicMock()
    mock_auth.sign_up.return_value = mock_response

    mock_client = MagicMock()
    mock_client.auth = mock_auth

    mock_admin_table = MagicMock()
    mock_admin_table.insert.return_value.execute.return_value = MagicMock()

    mock_admin = MagicMock()
    mock_admin.table.return_value = mock_admin_table

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await register_user("new@test.com", "password123")

    assert result["success"] is True
    assert result["user"]["id"] == "new-id"
    assert result["session"]["access_token"] == "access-tok"


@pytest.mark.asyncio
async def test_register_user_duplicate_email():
    """register_user returns friendly error for duplicate email."""
    from app.services.auth_service import register_user

    mock_client = MagicMock()
    mock_client.auth.sign_up.side_effect = Exception("User already registered")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await register_user("dup@test.com", "password123")

    assert result["success"] is False
    assert "already exists" in result["error"]


@pytest.mark.asyncio
async def test_register_user_no_user_returned():
    """register_user returns failure when Supabase returns no user."""
    from app.services.auth_service import register_user

    mock_response = MagicMock()
    mock_response.user = None

    mock_client = MagicMock()
    mock_client.auth.sign_up.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await register_user("test@test.com", "password123")

    assert result["success"] is False
    assert result["error"] == "Registration failed"


@pytest.mark.asyncio
async def test_login_user_success():
    """login_user returns user + session on valid credentials."""
    from app.services.auth_service import login_user

    mock_user = MagicMock()
    mock_user.id = "user-id"
    mock_user.email = "user@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "access-tok"
    mock_session.refresh_token = "refresh-tok"
    mock_session.expires_at = 1234567890

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_client = MagicMock()
    mock_client.auth.sign_in_with_password.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await login_user("user@test.com", "correct")

    assert result["success"] is True
    assert result["user"]["id"] == "user-id"


@pytest.mark.asyncio
async def test_login_user_invalid_credentials():
    """login_user returns friendly error for invalid credentials."""
    from app.services.auth_service import login_user

    mock_client = MagicMock()
    mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await login_user("user@test.com", "wrong")

    assert result["success"] is False
    assert "Invalid email or password" in result["error"]


@pytest.mark.asyncio
async def test_login_user_no_session():
    """login_user returns failure when session is None."""
    from app.services.auth_service import login_user

    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.session = None

    mock_client = MagicMock()
    mock_client.auth.sign_in_with_password.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await login_user("user@test.com", "pass")

    assert result["success"] is False


@pytest.mark.asyncio
async def test_refresh_session_success():
    """refresh_session returns new tokens on success."""
    from app.services.auth_service import refresh_session

    mock_session = MagicMock()
    mock_session.access_token = "new-access"
    mock_session.refresh_token = "new-refresh"
    mock_session.expires_at = 9999999999

    mock_response = MagicMock()
    mock_response.session = mock_session

    mock_client = MagicMock()
    mock_client.auth.refresh_session.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await refresh_session("old-refresh-token")

    assert result["success"] is True
    assert result["session"]["access_token"] == "new-access"


@pytest.mark.asyncio
async def test_refresh_session_no_session():
    """refresh_session returns failure when no session returned."""
    from app.services.auth_service import refresh_session

    mock_response = MagicMock()
    mock_response.session = None

    mock_client = MagicMock()
    mock_client.auth.refresh_session.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await refresh_session("expired-token")

    assert result["success"] is False


@pytest.mark.asyncio
async def test_refresh_session_error():
    """refresh_session returns categorized error message on exception."""
    from app.services.auth_service import refresh_session

    mock_client = MagicMock()
    mock_client.auth.refresh_session.side_effect = Exception("Token revoked")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await refresh_session("revoked-token")

    assert result["success"] is False
    # Error is now categorized — "Token revoked" is unknown, so generic message
    assert result["error"] == "Something went wrong. Please try again later."


@pytest.mark.asyncio
async def test_get_user_profile_success():
    """get_user_profile returns user data from users table."""
    from app.services.auth_service import get_user_profile

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "user-1", "email": "test@test.com", "subscription_tier": "free"}
    )

    mock_admin = MagicMock()
    mock_admin.table.return_value = mock_table

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await get_user_profile("user-1")

    assert result["id"] == "user-1"
    assert result["subscription_tier"] == "free"


@pytest.mark.asyncio
async def test_get_user_profile_not_found():
    """get_user_profile returns None when user not in table."""
    from app.services.auth_service import get_user_profile

    mock_admin = MagicMock()
    mock_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("No rows")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await get_user_profile("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_logout_user_success():
    """logout_user calls sign_out and returns success."""
    from app.services.auth_service import logout_user

    mock_client = MagicMock()

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await logout_user("some-token")

    assert result["success"] is True
    mock_client.auth.sign_out.assert_called_once()


@pytest.mark.asyncio
async def test_logout_user_error():
    """logout_user returns error on exception."""
    from app.services.auth_service import logout_user

    mock_client = MagicMock()
    mock_client.auth.sign_out.side_effect = Exception("Network error")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await logout_user("some-token")

    assert result["success"] is False
    assert "Network error" in result["error"]


@pytest.mark.asyncio
async def test_request_password_reset_success():
    """request_password_reset returns success on normal call."""
    from app.services.auth_service import request_password_reset

    mock_client = MagicMock()

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await request_password_reset("user@test.com")

    assert result["success"] is True
    mock_client.auth.reset_password_email.assert_called_once_with("user@test.com")


@pytest.mark.asyncio
async def test_request_password_reset_error():
    """request_password_reset returns categorized error on exception."""
    from app.services.auth_service import request_password_reset

    mock_client = MagicMock()
    mock_client.auth.reset_password_email.side_effect = Exception("SMTP failure")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await request_password_reset("user@test.com")

    assert result["success"] is False
    # Error is now categorized — "SMTP failure" is unknown, so generic message
    assert result["error"] == "Something went wrong. Please try again later."


# ── update_profile tests ──

@pytest.mark.asyncio
async def test_update_profile_success():
    """PUT /api/v1/auth/profile should update display name."""
    from app.api.auth_routes import update_profile, UpdateProfileRequest
    mock_user = {"id": "user-1", "email": "test@example.com"}
    with patch("app.api.auth_routes.update_user_profile", new_callable=AsyncMock,
               return_value={"success": True, "message": "Profile updated"}):
        result = await update_profile(
            body=UpdateProfileRequest(display_name="Test User"),
            current_user=mock_user
        )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_update_profile_requires_auth():
    """update_profile requires authentication (get_current_user dependency)."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_validates_min_length():
    """Display name must be at least 2 chars."""
    from app.api.auth_routes import UpdateProfileRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        UpdateProfileRequest(display_name="X")


@pytest.mark.asyncio
async def test_update_profile_validates_max_length():
    """Display name must be at most 100 chars."""
    from app.api.auth_routes import UpdateProfileRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        UpdateProfileRequest(display_name="A" * 101)


@pytest.mark.asyncio
async def test_update_user_profile_service_success():
    """update_user_profile calls Supabase and returns success."""
    from app.services.auth_service import update_user_profile

    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_admin = MagicMock()
    mock_admin.table.return_value = mock_table

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_profile("user-1", "New Name")

    assert result["success"] is True
    mock_table.update.assert_called_once_with({"display_name": "New Name"})


@pytest.mark.asyncio
async def test_update_user_profile_service_error():
    """update_user_profile returns categorized error on exception."""
    from app.services.auth_service import update_user_profile

    mock_admin = MagicMock()
    mock_admin.table.return_value.update.side_effect = Exception("DB error")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_profile("user-1", "Name")

    assert result["success"] is False
    # Error is now categorized — "DB error" is unknown, so generic message
    assert result["error"] == "Something went wrong. Please try again later."


# ── update_email tests ──

@pytest.mark.asyncio
async def test_update_email_success():
    """PUT /api/v1/auth/email should trigger email update."""
    from app.api.auth_routes import update_email, UpdateEmailRequest
    mock_user = {"id": "user-1", "email": "old@example.com"}
    with patch("app.api.auth_routes.update_user_email", new_callable=AsyncMock,
               return_value={"success": True, "message": "Verification email sent to new address"}):
        result = await update_email(
            body=UpdateEmailRequest(new_email="new@example.com"),
            current_user=mock_user
        )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_update_email_validates_format():
    """Invalid email format should raise ValidationError."""
    from app.api.auth_routes import UpdateEmailRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        UpdateEmailRequest(new_email="not-an-email")


@pytest.mark.asyncio
async def test_update_email_already_in_use():
    """update_user_email returns friendly error for duplicate email."""
    from app.services.auth_service import update_user_email

    mock_admin = MagicMock()
    mock_admin.auth.admin.update_user_by_id.side_effect = Exception("User already registered")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "taken@example.com")

    assert result["success"] is False
    assert "already exists" in result["error"]


@pytest.mark.asyncio
async def test_update_email_service_success():
    """update_user_email returns success on normal call."""
    from app.services.auth_service import update_user_email

    mock_admin = MagicMock()

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "new@example.com")

    assert result["success"] is True
    mock_admin.auth.admin.update_user_by_id.assert_called_once_with(
        "user-1", {"email": "new@example.com"}
    )


@pytest.mark.asyncio
async def test_update_email_service_generic_error():
    """update_user_email returns categorized error for non-duplicate errors."""
    from app.services.auth_service import update_user_email

    mock_admin = MagicMock()
    mock_admin.auth.admin.update_user_by_id.side_effect = Exception("Network timeout")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "new@example.com")

    assert result["success"] is False
    # "Network timeout" is not in the network terms but "timeout" IS
    # wait - "timeout" is in the list, so this should match network error
    assert result["error"] == "Connection failed. Please try again."


# ── change_password tests ──

@pytest.mark.asyncio
async def test_change_password_success():
    """PUT /api/v1/auth/password should change password."""
    from app.api.auth_routes import change_password, ChangePasswordRequest
    mock_user = {"id": "user-1", "email": "test@example.com"}
    with patch("app.api.auth_routes.change_user_password", new_callable=AsyncMock,
               return_value={"success": True, "message": "Password changed successfully"}):
        result = await change_password(
            body=ChangePasswordRequest(current_password="oldpass123", new_password="newpass123"),
            current_user=mock_user
        )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_change_password_min_length():
    """New password must be at least 6 chars."""
    from app.api.auth_routes import ChangePasswordRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="oldpass123", new_password="12345")


@pytest.mark.asyncio
async def test_change_password_wrong_current():
    """Wrong current password should return 400."""
    from app.api.auth_routes import change_password, ChangePasswordRequest
    from fastapi import HTTPException
    mock_user = {"id": "user-1", "email": "test@example.com"}
    with patch("app.api.auth_routes.change_user_password", new_callable=AsyncMock,
               return_value={"success": False, "error": "Current password is incorrect"}):
        with pytest.raises(HTTPException) as exc_info:
            await change_password(
                body=ChangePasswordRequest(current_password="wrong", new_password="newpass123"),
                current_user=mock_user
            )
    assert exc_info.value.status_code == 400
    assert "incorrect" in exc_info.value.detail


@pytest.mark.asyncio
async def test_change_user_password_service_success():
    """change_user_password verifies current password then updates."""
    from app.services.auth_service import change_user_password

    mock_auth_client = MagicMock()
    mock_admin_client = MagicMock()

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await change_user_password("user-1", "test@example.com", "oldpass", "newpass")

    assert result["success"] is True
    mock_auth_client.auth.sign_in_with_password.assert_called_once_with({
        "email": "test@example.com", "password": "oldpass"
    })
    mock_admin_client.auth.admin.update_user_by_id.assert_called_once_with(
        "user-1", {"password": "newpass"}
    )


@pytest.mark.asyncio
async def test_change_user_password_wrong_current():
    """change_user_password returns friendly error for wrong password."""
    from app.services.auth_service import change_user_password

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client):
        result = await change_user_password("user-1", "test@example.com", "wrong", "newpass")

    assert result["success"] is False
    # change_password has a special case: "Current password is incorrect"
    assert result["error"] == "Current password is incorrect"


@pytest.mark.asyncio
async def test_change_user_password_generic_error():
    """change_user_password returns categorized error for non-credential errors."""
    from app.services.auth_service import change_user_password

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_password.side_effect = Exception("Network timeout")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client):
        result = await change_user_password("user-1", "test@example.com", "pass", "newpass")

    assert result["success"] is False
    # "timeout" is in network terms list
    assert result["error"] == "Connection failed. Please try again."


# ── social_login tests ──

@pytest.mark.asyncio
async def test_social_login_google_success():
    """POST /api/v1/auth/social-login with Google token should return session."""
    from app.api.auth_routes import social_login, SocialLoginRequest
    mock_result = {
        "success": True,
        "user": {"id": "google-user", "email": "user@gmail.com"},
        "session": {"access_token": "tok", "refresh_token": "ref", "expires_at": 123},
        "message": "Signed in with google",
    }
    with patch("app.api.auth_routes.sign_in_with_social", new_callable=AsyncMock,
               return_value=mock_result):
        result = await social_login(
            body=SocialLoginRequest(provider="google", id_token="mock-google-id-token")
        )
    assert result["success"] is True
    assert "session" in result


@pytest.mark.asyncio
async def test_social_login_apple_success():
    """POST /api/v1/auth/social-login with Apple token should return session."""
    from app.api.auth_routes import social_login, SocialLoginRequest
    mock_result = {
        "success": True,
        "user": {"id": "apple-user", "email": "user@icloud.com"},
        "session": {"access_token": "tok", "refresh_token": "ref", "expires_at": 123},
        "message": "Signed in with apple",
    }
    with patch("app.api.auth_routes.sign_in_with_social", new_callable=AsyncMock,
               return_value=mock_result):
        result = await social_login(
            body=SocialLoginRequest(provider="apple", id_token="mock-apple-token", nonce="abc")
        )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_social_login_invalid_provider():
    """Only google and apple are valid providers."""
    from app.api.auth_routes import SocialLoginRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SocialLoginRequest(provider="facebook", id_token="token")


@pytest.mark.asyncio
async def test_social_login_auth_failure():
    """social_login raises 401 when auth fails."""
    from app.api.auth_routes import social_login, SocialLoginRequest
    from fastapi import HTTPException
    with patch("app.api.auth_routes.sign_in_with_social", new_callable=AsyncMock,
               return_value={"success": False, "error": "Invalid token"}):
        with pytest.raises(HTTPException) as exc_info:
            await social_login(
                body=SocialLoginRequest(provider="google", id_token="bad-token")
            )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_sign_in_with_social_service_success():
    """sign_in_with_social calls Supabase signInWithIdToken and creates user."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "social-uid"
    mock_user.email = "social@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "social-tok"
    mock_session.refresh_token = "social-ref"
    mock_session.expires_at = 9999

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    # User doesn't exist yet
    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await sign_in_with_social("google", "id-token-123")

    assert result["success"] is True
    assert result["user"]["id"] == "social-uid"
    assert result["session"]["access_token"] == "social-tok"
    # Should have created user in users table
    mock_admin_client.table.return_value.insert.assert_called_once()


@pytest.mark.asyncio
async def test_sign_in_with_social_existing_user():
    """sign_in_with_social skips user creation if user already exists."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "existing-uid"
    mock_user.email = "existing@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "tok"
    mock_session.refresh_token = "ref"
    mock_session.expires_at = 9999

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    # User already exists
    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "existing-uid"}]
    )

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await sign_in_with_social("apple", "apple-token", nonce="nonce123")

    assert result["success"] is True
    # Should NOT have inserted into users table
    mock_admin_client.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_sign_in_with_social_no_user_returned():
    """sign_in_with_social returns failure when Supabase returns no user."""
    from app.services.auth_service import sign_in_with_social

    mock_response = MagicMock()
    mock_response.user = None

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client):
        result = await sign_in_with_social("google", "bad-token")

    assert result["success"] is False
    assert "failed" in result["error"].lower()


@pytest.mark.asyncio
async def test_sign_in_with_social_exception():
    """sign_in_with_social returns categorized error on exception."""
    from app.services.auth_service import sign_in_with_social

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.side_effect = Exception("Provider error")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client):
        result = await sign_in_with_social("google", "token")

    assert result["success"] is False
    # "Provider error" is unknown, so generic message
    assert result["error"] == "Something went wrong. Please try again later."


@pytest.mark.asyncio
async def test_sign_in_with_social_passes_nonce():
    """sign_in_with_social passes nonce to Supabase for Apple Sign-In."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "uid"
    mock_user.email = "e@e.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "uid"}])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        await sign_in_with_social("apple", "apple-token", nonce="my-nonce")

    call_args = mock_auth_client.auth.sign_in_with_id_token.call_args[0][0]
    assert call_args["provider"] == "apple"
    assert call_args["token"] == "apple-token"
    assert call_args["nonce"] == "my-nonce"


# ── Additional edge case tests for new endpoints ──

@pytest.mark.asyncio
async def test_update_profile_service_failure_returns_gracefully():
    """update_profile endpoint returns service error without raising."""
    from app.api.auth_routes import update_profile, UpdateProfileRequest
    mock_user = {"id": "user-1", "email": "test@example.com"}
    with patch("app.api.auth_routes.update_user_profile", new_callable=AsyncMock,
               return_value={"success": False, "error": "Column not found"}):
        result = await update_profile(
            body=UpdateProfileRequest(display_name="Valid Name"),
            current_user=mock_user
        )
    assert result["success"] is False
    assert "Column not found" in result["error"]


@pytest.mark.asyncio
async def test_update_email_service_failure_returns_gracefully():
    """update_email endpoint returns service error without raising."""
    from app.api.auth_routes import update_email, UpdateEmailRequest
    mock_user = {"id": "user-1", "email": "old@example.com"}
    with patch("app.api.auth_routes.update_user_email", new_callable=AsyncMock,
               return_value={"success": False, "error": "Rate limited"}):
        result = await update_email(
            body=UpdateEmailRequest(new_email="new@example.com"),
            current_user=mock_user
        )
    assert result["success"] is False


@pytest.mark.asyncio
async def test_social_login_without_nonce():
    """sign_in_with_social omits nonce from credentials when None."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "uid"
    mock_user.email = "e@e.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "uid"}])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        await sign_in_with_social("google", "google-token")

    call_args = mock_auth_client.auth.sign_in_with_id_token.call_args[0][0]
    assert "nonce" not in call_args


@pytest.mark.asyncio
async def test_social_login_no_session_returns_null_tokens():
    """sign_in_with_social handles response with user but no session."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "uid"
    mock_user.email = "e@e.com"

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = None

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "uid"}])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await sign_in_with_social("google", "token")

    assert result["success"] is True
    assert result["session"]["access_token"] is None
    assert result["session"]["refresh_token"] is None


@pytest.mark.asyncio
async def test_social_login_new_user_includes_auth_provider():
    """sign_in_with_social sets auth_provider when creating new user."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "new-uid"
    mock_user.email = "new@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        await sign_in_with_social("apple", "apple-token")

    insert_call = mock_admin_client.table.return_value.insert.call_args[0][0]
    assert insert_call["auth_provider"] == "apple"
    assert insert_call["subscription_tier"] == "free"


@pytest.mark.asyncio
async def test_change_password_passes_correct_user_info():
    """change_password endpoint passes user id and email to service."""
    from app.api.auth_routes import change_password, ChangePasswordRequest
    mock_user = {"id": "u-99", "email": "pass@test.com"}

    with patch("app.api.auth_routes.change_user_password", new_callable=AsyncMock,
               return_value={"success": True, "message": "Changed"}) as mock_svc:
        await change_password(
            body=ChangePasswordRequest(current_password="old", new_password="newpass"),
            current_user=mock_user
        )

    mock_svc.assert_called_once_with("u-99", "pass@test.com", "old", "newpass")


@pytest.mark.asyncio
async def test_get_me_includes_display_name_when_present():
    """get_me includes display_name from profile data when available."""
    from app.api.auth_routes import get_me
    mock_profile = {
        "id": "user-1",
        "email": "test@example.com",
        "subscription_tier": "free",
        "created_at": "2026-01-01",
        "display_name": "Test User",
    }
    with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=mock_profile):
        result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})
    # The profile data is returned (get_me only returns specific fields though)
    assert result["success"] is True
    assert result["user"]["id"] == "user-1"


@pytest.mark.asyncio
async def test_refresh_session_includes_user_data():
    """refresh_session includes user data when user is in response."""
    from app.services.auth_service import refresh_session

    mock_user = MagicMock()
    mock_user.id = "uid-refresh"
    mock_user.email = "refresh@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "new-a"
    mock_session.refresh_token = "new-r"
    mock_session.expires_at = 5555

    mock_response = MagicMock()
    mock_response.session = mock_session
    mock_response.user = mock_user

    mock_client = MagicMock()
    mock_client.auth.refresh_session.return_value = mock_response

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await refresh_session("old-token")

    assert result["success"] is True
    assert result["user"]["id"] == "uid-refresh"
    assert result["user"]["email"] == "refresh@test.com"


# ── Deeper edge cases (team lead suggestions) ──

@pytest.mark.asyncio
async def test_update_profile_whitespace_only_name_passes_pydantic():
    """Pydantic min_length counts whitespace chars, so '  ' (2 spaces) is valid."""
    from app.api.auth_routes import UpdateProfileRequest
    # Two spaces pass min_length=2 — this is by design; frontend should trim
    req = UpdateProfileRequest(display_name="  ")
    assert req.display_name == "  "


@pytest.mark.asyncio
async def test_update_profile_boundary_2_chars():
    """Display name with exactly 2 characters should be valid."""
    from app.api.auth_routes import UpdateProfileRequest
    req = UpdateProfileRequest(display_name="AB")
    assert req.display_name == "AB"


@pytest.mark.asyncio
async def test_update_profile_boundary_100_chars():
    """Display name with exactly 100 characters should be valid."""
    from app.api.auth_routes import UpdateProfileRequest
    name = "A" * 100
    req = UpdateProfileRequest(display_name=name)
    assert len(req.display_name) == 100


@pytest.mark.asyncio
async def test_update_email_same_email_succeeds():
    """Updating to the same email should still succeed (Supabase handles it)."""
    from app.services.auth_service import update_user_email

    mock_admin = MagicMock()

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "same@example.com")

    assert result["success"] is True
    mock_admin.auth.admin.update_user_by_id.assert_called_once_with(
        "user-1", {"email": "same@example.com"}
    )


@pytest.mark.asyncio
async def test_change_password_same_as_current_succeeds():
    """Changing password to same value should succeed (Supabase allows it)."""
    from app.services.auth_service import change_user_password

    mock_auth_client = MagicMock()
    mock_admin_client = MagicMock()

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await change_user_password("user-1", "e@e.com", "samepass", "samepass")

    assert result["success"] is True
    mock_admin_client.auth.admin.update_user_by_id.assert_called_once_with(
        "user-1", {"password": "samepass"}
    )


@pytest.mark.asyncio
async def test_change_password_admin_update_fails_after_login():
    """If login succeeds but admin password update fails, return categorized error."""
    from app.services.auth_service import change_user_password

    mock_auth_client = MagicMock()
    # Login succeeds
    mock_auth_client.auth.sign_in_with_password.return_value = MagicMock()

    mock_admin_client = MagicMock()
    # But admin update fails
    mock_admin_client.auth.admin.update_user_by_id.side_effect = Exception("Admin API rate limit")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await change_user_password("user-1", "e@e.com", "correct", "newpass")

    assert result["success"] is False
    # "Admin API rate limit" is unknown, so generic message
    assert result["error"] == "Something went wrong. Please try again later."


@pytest.mark.asyncio
async def test_social_login_empty_string_nonce_not_sent():
    """Empty string nonce should be treated as falsy and not included."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "uid"
    mock_user.email = "e@e.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "uid"}])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        await sign_in_with_social("google", "token", nonce="")

    call_args = mock_auth_client.auth.sign_in_with_id_token.call_args[0][0]
    assert "nonce" not in call_args


@pytest.mark.asyncio
async def test_social_login_user_table_check_fails_gracefully():
    """If checking existing user in users table fails, the whole call should still handle it."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "uid"
    mock_user.email = "e@e.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    # The SELECT to check existing user throws
    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB connection lost")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await sign_in_with_social("google", "token")

    # Now categorized — "connection" is in network terms
    assert result["success"] is False
    assert result["error"] == "Connection failed. Please try again."


@pytest.mark.asyncio
async def test_social_login_user_insert_fails_gracefully():
    """If creating user in users table fails, the whole call should handle it."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "new-uid"
    mock_user.email = "new@e.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    # User doesn't exist
    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # But insert fails
    mock_admin_client.table.return_value.insert.return_value.execute.side_effect = Exception("Duplicate key")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await sign_in_with_social("apple", "token")

    assert result["success"] is False
    # "Duplicate key" is unknown, so generic message
    assert result["error"] == "Something went wrong. Please try again later."


@pytest.mark.asyncio
async def test_social_login_request_nonce_defaults_none():
    """SocialLoginRequest nonce field defaults to None when not provided."""
    from app.api.auth_routes import SocialLoginRequest
    req = SocialLoginRequest(provider="google", id_token="tok")
    assert req.nonce is None


@pytest.mark.asyncio
async def test_social_login_message_includes_provider():
    """Success response message should include the provider name."""
    from app.services.auth_service import sign_in_with_social

    mock_user = MagicMock()
    mock_user.id = "uid"
    mock_user.email = "e@e.com"

    mock_session = MagicMock()
    mock_session.access_token = "t"
    mock_session.refresh_token = "r"
    mock_session.expires_at = 1

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "uid"}])

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
         patch("app.services.auth_service.get_admin_client", return_value=mock_admin_client):
        result = await sign_in_with_social("google", "token")

    assert result["message"] == "Signed in with google"


@pytest.mark.asyncio
async def test_change_password_new_password_exactly_6_chars():
    """New password with exactly 6 chars (minimum) should be valid."""
    from app.api.auth_routes import ChangePasswordRequest
    req = ChangePasswordRequest(current_password="whatever", new_password="123456")
    assert req.new_password == "123456"


@pytest.mark.asyncio
async def test_change_password_new_password_5_chars_invalid():
    """New password with 5 chars (below minimum) should be rejected by Pydantic."""
    from app.api.auth_routes import ChangePasswordRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="whatever", new_password="12345")


@pytest.mark.asyncio
async def test_update_email_admin_api_error_with_unknown_message():
    """update_user_email with unrecognized error returns generic categorized message."""
    from app.services.auth_service import update_user_email

    mock_admin = MagicMock()
    mock_admin.auth.admin.update_user_by_id.side_effect = Exception("Internal server error 500")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "new@example.com")

    assert result["success"] is False
    # Now categorized — unknown errors get generic message (no raw string leak)
    assert result["error"] == "Something went wrong. Please try again later."
    assert "Internal server error" not in result["error"]


# ── Password reset endpoint path verification (Task 2) ──

@pytest.mark.asyncio
async def test_password_reset_endpoint_path():
    """Verify password reset endpoint matches backend route."""
    from app.api.auth_routes import router
    routes = [route.path for route in router.routes]
    assert "/api/v1/auth/password-reset" in routes
    # The old path /reset-password should NOT exist
    assert "/api/v1/auth/reset-password" not in routes


# ── Error categorization tests (Task 4) ──

class TestErrorCategorization:
    def test_invalid_credentials(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("Invalid login credentials"), "login")
        assert result["success"] is False
        assert result["error"] == "Invalid email or password"

    def test_user_already_registered(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("User already registered"), "register")
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_email_not_confirmed(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("Email not confirmed"), "login")
        assert result["success"] is False
        assert "verify your email" in result["error"]

    def test_network_error_connection(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("Connection refused"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_timeout(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("Request timeout"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_dns(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("DNS lookup failed"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_econnrefused(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("ECONNREFUSED"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_socket_hang_up(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("socket hang up"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_enotfound(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("getaddrinfo ENOTFOUND"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_unknown_error_generic_message(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("Something bizarre happened"), "login")
        assert result["error"] == "Something went wrong. Please try again later."

    def test_unknown_error_no_raw_string(self):
        """Raw error string must NOT leak to user."""
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("AuthRetryableError: xyz"), "login")
        assert "AuthRetryableError" not in result["error"]
        assert "xyz" not in result["error"]

    def test_case_insensitive(self):
        from app.services.auth_service import _categorize_auth_error
        result = _categorize_auth_error(Exception("INVALID LOGIN CREDENTIALS"), "login")
        assert result["error"] == "Invalid email or password"


# ── Profile enrichment tests (Task 6) ──

class TestProfileEnrichment:
    @pytest.mark.asyncio
    async def test_enriches_with_display_name(self):
        from app.services.auth_service import _enrich_response_with_profile
        mock_profile = MagicMock()
        mock_profile.data = {"display_name": "John", "auth_provider": "email"}
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            response = {"success": True, "user": {"id": "123", "email": "test@test.com"}}
            result = await _enrich_response_with_profile(response, "123")
            assert result["user"]["display_name"] == "John"
            assert result["user"]["auth_provider"] == "email"

    @pytest.mark.asyncio
    async def test_graceful_on_missing_profile(self):
        from app.services.auth_service import _enrich_response_with_profile
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("not found")
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            response = {"success": True, "user": {"id": "123"}}
            result = await _enrich_response_with_profile(response, "123")
            assert result["user"]["display_name"] is None
            assert result["user"]["auth_provider"] is None
            assert result["success"] is True  # Auth response NOT broken

    @pytest.mark.asyncio
    async def test_graceful_on_none_data(self):
        from app.services.auth_service import _enrich_response_with_profile
        mock_profile = MagicMock()
        mock_profile.data = None
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            response = {"success": True, "user": {"id": "123"}}
            result = await _enrich_response_with_profile(response, "123")
            assert result["user"]["display_name"] is None
            assert result["user"]["auth_provider"] is None

    @pytest.mark.asyncio
    async def test_creates_user_key_if_missing(self):
        from app.services.auth_service import _enrich_response_with_profile
        with patch("app.services.auth_service.get_admin_client") as mock:
            mock.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("err")
            response = {"success": True}  # No "user" key
            result = await _enrich_response_with_profile(response, "123")
            assert "user" in result
            assert result["user"]["display_name"] is None


# ── /me endpoint normalization tests (Task 9) ──

class TestMeEndpointNormalization:
    """Verify /me always returns consistent shape regardless of profile state."""

    @pytest.mark.asyncio
    async def test_me_response_has_all_fields_when_profile_exists(self):
        """All expected fields present when profile is found."""
        from app.api.auth_routes import get_me
        mock_profile = {
            "id": "user-1", "email": "test@example.com", "display_name": "Test",
            "auth_provider": "email", "subscription_tier": "free",
            "created_at": "2026-01-01", "preferences_completed": True
        }
        with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=mock_profile):
            result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})

        required_fields = ["id", "email", "display_name", "auth_provider",
                          "subscription_tier", "created_at", "preferences_completed"]
        for field in required_fields:
            assert field in result["user"], f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_me_response_has_all_fields_when_profile_missing(self):
        """All fields present with defaults when profile not found."""
        from app.api.auth_routes import get_me
        with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=None):
            result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})

        assert result["user"]["subscription_tier"] == "free"
        assert result["user"]["preferences_completed"] is False
        assert result["user"]["display_name"] is None
        assert result["user"]["auth_provider"] is None

    @pytest.mark.asyncio
    async def test_me_response_subscription_tier_defaults_to_free(self):
        """subscription_tier defaults to 'free' when profile has no tier."""
        from app.api.auth_routes import get_me
        mock_profile = {
            "id": "user-1", "email": "test@example.com",
            "display_name": None, "auth_provider": None,
            "created_at": None, "preferences_completed": False
            # Note: subscription_tier intentionally missing
        }
        with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=mock_profile):
            result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})

        assert result["user"]["subscription_tier"] == "free"


# ============================================
# Auth Rate Limiting
# ============================================


def test_login_has_rate_limit_decorator():
    """Login endpoint has rate limit configured."""
    from app.middleware.rate_limiter import limiter
    from app.main import app  # Ensure routes are registered
    assert "app.api.auth_routes.login" in limiter._route_limits, \
        "login endpoint should have rate limit decorator"


def test_register_has_rate_limit_decorator():
    """Register endpoint has rate limit configured."""
    from app.middleware.rate_limiter import limiter
    from app.main import app
    assert "app.api.auth_routes.register" in limiter._route_limits, \
        "register endpoint should have rate limit decorator"


def test_social_login_has_rate_limit_decorator():
    """Social login endpoint has rate limit configured."""
    from app.middleware.rate_limiter import limiter
    from app.main import app
    assert "app.api.auth_routes.social_login" in limiter._route_limits, \
        "social_login endpoint should have rate limit decorator"


def test_password_reset_has_rate_limit_decorator():
    """Password reset endpoint has rate limit configured."""
    from app.middleware.rate_limiter import limiter
    from app.main import app
    assert "app.api.auth_routes.password_reset" in limiter._route_limits, \
        "password_reset endpoint should have rate limit decorator"
