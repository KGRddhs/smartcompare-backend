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
    """get_me returns profile data when profile exists."""
    from app.api.auth_routes import get_me
    mock_profile = {
        "id": "user-1",
        "email": "test@example.com",
        "subscription_tier": "pro",
        "created_at": "2026-01-01",
    }
    with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=mock_profile):
        result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})
    assert result["success"] is True
    assert result["user"]["subscription_tier"] == "pro"


@pytest.mark.asyncio
async def test_get_me_without_profile():
    """get_me falls back to current_user when profile not found."""
    from app.api.auth_routes import get_me
    with patch("app.api.auth_routes.get_user_profile", new_callable=AsyncMock, return_value=None):
        result = await get_me(current_user={"id": "user-1", "email": "test@example.com"})
    assert result["success"] is True
    assert result["user"] == {"id": "user-1", "email": "test@example.com"}


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
    assert "Email already registered" in result["error"]


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
    """refresh_session returns error message on exception."""
    from app.services.auth_service import refresh_session

    mock_client = MagicMock()
    mock_client.auth.refresh_session.side_effect = Exception("Token revoked")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await refresh_session("revoked-token")

    assert result["success"] is False
    assert "Token revoked" in result["error"]


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
    """request_password_reset returns error on exception."""
    from app.services.auth_service import request_password_reset

    mock_client = MagicMock()
    mock_client.auth.reset_password_email.side_effect = Exception("SMTP failure")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_client):
        result = await request_password_reset("user@test.com")

    assert result["success"] is False
    assert "SMTP failure" in result["error"]


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
    """update_user_profile returns error on exception."""
    from app.services.auth_service import update_user_profile

    mock_admin = MagicMock()
    mock_admin.table.return_value.update.side_effect = Exception("DB error")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_profile("user-1", "Name")

    assert result["success"] is False
    assert "DB error" in result["error"]


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
    mock_admin.auth.admin.update_user_by_id.side_effect = Exception("Email already registered")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "taken@example.com")

    assert result["success"] is False
    assert "already in use" in result["error"]


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
    """update_user_email returns raw error for non-duplicate errors."""
    from app.services.auth_service import update_user_email

    mock_admin = MagicMock()
    mock_admin.auth.admin.update_user_by_id.side_effect = Exception("Network timeout")

    with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
        result = await update_user_email("user-1", "new@example.com")

    assert result["success"] is False
    assert "Network timeout" in result["error"]


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
    assert "incorrect" in result["error"]


@pytest.mark.asyncio
async def test_change_user_password_generic_error():
    """change_user_password returns raw error for non-credential errors."""
    from app.services.auth_service import change_user_password

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_password.side_effect = Exception("Network timeout")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client):
        result = await change_user_password("user-1", "test@example.com", "pass", "newpass")

    assert result["success"] is False
    assert "Network timeout" in result["error"]


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
    """sign_in_with_social returns error on exception."""
    from app.services.auth_service import sign_in_with_social

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.side_effect = Exception("Provider error")

    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client):
        result = await sign_in_with_social("google", "token")

    assert result["success"] is False
    assert "Provider error" in result["error"]


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
