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
