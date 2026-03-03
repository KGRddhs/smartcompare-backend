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
