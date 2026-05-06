"""Tests for POST /api/v1/auth/attribution (plan task 8).

Contract:
- Accepts source enum: friend, instagram, tiktok, app_store, google, other
- Rejects invalid source (Pydantic 422)
- Requires auth (current_user dep)
- Rate limited 30/min via slowapi
- Writes to users.attribution_source via database_service helper

Pattern follows tests/test_auth_demographics.py (direct route call with
MagicMock request, current_user dict supplied directly).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError


# ============================================
# AttributionBody pydantic model
# ============================================


class TestAttributionBody:
    def test_body_accepts_friend(self):
        from app.api.auth_routes import AttributionBody

        b = AttributionBody(source="friend")
        assert b.source == "friend"

    def test_body_accepts_all_six_sources(self):
        from app.api.auth_routes import AttributionBody

        for src in ("friend", "instagram", "tiktok", "app_store", "google", "other"):
            b = AttributionBody(source=src)
            assert b.source == src

    def test_body_rejects_unknown_source(self):
        from app.api.auth_routes import AttributionBody

        with pytest.raises(ValidationError):
            AttributionBody(source="myspace")

    def test_body_rejects_empty_source(self):
        from app.api.auth_routes import AttributionBody

        with pytest.raises(ValidationError):
            AttributionBody(source="")

    def test_body_rejects_extra_fields(self):
        """Defense in depth: extra='ignore' or 'forbid' — no PII smuggling."""
        from app.api.auth_routes import AttributionBody

        # If extra='forbid', this raises; if extra='ignore', extra is dropped.
        # Either contract is acceptable — just not 'allow'.
        try:
            b = AttributionBody(source="friend", malicious="x")
            assert not hasattr(b, "malicious")
        except ValidationError:
            pass  # forbid is also fine


# ============================================
# Endpoint exists + uses auth dependency
# ============================================


class TestAttributionEndpointShape:
    def test_endpoint_function_exists(self):
        from app.api import auth_routes

        assert hasattr(auth_routes, "save_attribution"), (
            "POST /attribution endpoint not yet implemented (task 8)"
        )

    def test_endpoint_uses_get_current_user_dependency(self):
        import inspect
        from app.api import auth_routes

        src = inspect.getsource(auth_routes.save_attribution)
        assert "get_current_user" in src, (
            "save_attribution must use Depends(get_current_user) for auth"
        )

    def test_endpoint_has_rate_limiter(self):
        """Per design 6.* + plan task 8: rate-limited 30/min per route.

        The codebase convention (matches /demographics, /push-token, etc.) is
        @router.post("/path") then @limiter.limit("X/minute") on the line
        below — both decorators wrap the same async def. We assert the
        limiter decorator + rate string appear within ~120 chars after the
        route path string in the source file.
        """
        from pathlib import Path

        src = Path("app/api/auth_routes.py").read_text(encoding="utf-8")
        idx = src.find('"/attribution"')
        assert idx >= 0, "POST /attribution route not declared"
        # Slice around the route path: 50 chars before (to catch a limiter
        # placed ABOVE @router.post if convention shifts) + 200 chars after
        # (to catch the standard codebase order where limiter sits below).
        decorator_window = src[max(0, idx - 50):idx + 200]
        assert "@limiter.limit" in decorator_window, (
            "POST /attribution must be rate limited via @limiter.limit "
            "(decorator must wrap the same async def — see /demographics for pattern)"
        )
        assert '"30/minute"' in decorator_window or "'30/minute'" in decorator_window, (
            "POST /attribution rate limit must be 30/minute per plan task 8"
        )


# ============================================
# Happy path
# ============================================


class TestAttributionHappyPath:
    @pytest.mark.asyncio
    async def test_persists_source_to_users_table(self):
        from app.api.auth_routes import save_attribution, AttributionBody

        mock_user = {"id": "user-1", "email": "test@example.com"}
        body = AttributionBody(source="instagram")
        request = MagicMock()
        request.headers = {}

        save_mock = AsyncMock(return_value={"success": True})
        with patch(
            "app.api.auth_routes.save_user_attribution",
            save_mock,
        ):
            result = await save_attribution(
                request=request, body=body, current_user=mock_user
            )

        assert result["success"] is True
        # Helper called with (user_id, source) in some order
        assert save_mock.await_count == 1
        called_args = save_mock.await_args
        # Accept either positional or kwargs — implementation flexibility
        if called_args.args:
            assert "user-1" in called_args.args
            assert "instagram" in called_args.args
        else:
            kwargs = called_args.kwargs
            assert kwargs.get("user_id") == "user-1"
            assert kwargs.get("source") == "instagram"

    @pytest.mark.asyncio
    async def test_response_shape(self):
        from app.api.auth_routes import save_attribution, AttributionBody

        mock_user = {"id": "user-2"}
        body = AttributionBody(source="friend")
        request = MagicMock()
        request.headers = {}

        with patch(
            "app.api.auth_routes.save_user_attribution",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            result = await save_attribution(
                request=request, body=body, current_user=mock_user
            )

        assert isinstance(result, dict)
        assert "success" in result


# ============================================
# Idempotency — re-submit overwrites prior value
# ============================================


class TestAttributionIdempotency:
    @pytest.mark.asyncio
    async def test_resubmit_overwrites(self):
        """User can resubmit attribution (e.g. after re-onboarding) — last write wins."""
        from app.api.auth_routes import save_attribution, AttributionBody

        mock_user = {"id": "user-3"}
        request = MagicMock()
        request.headers = {}

        save_mock = AsyncMock(return_value={"success": True})
        with patch("app.api.auth_routes.save_user_attribution", save_mock):
            await save_attribution(
                request=request,
                body=AttributionBody(source="instagram"),
                current_user=mock_user,
            )
            await save_attribution(
                request=request,
                body=AttributionBody(source="tiktok"),
                current_user=mock_user,
            )

        assert save_mock.await_count == 2


# ============================================
# Helper exists in database_service
# ============================================


class TestSaveUserAttributionHelper:
    @pytest.mark.asyncio
    async def test_helper_exists_in_database_service(self):
        from app.services import database_service

        assert hasattr(database_service, "save_user_attribution"), (
            "database_service.save_user_attribution must exist (used by /attribution route)"
        )

    @pytest.mark.asyncio
    async def test_helper_returns_success_dict_shape(self):
        """Helper conforms to {success: bool, error?: str} contract."""
        from app.services import database_service

        with patch.object(
            database_service, "get_admin_supabase_client"
        ) as mock_client_factory:
            mock_table = MagicMock()
            mock_table.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock_client = MagicMock()
            mock_client.table.return_value = mock_table
            mock_client_factory.return_value = mock_client

            result = await database_service.save_user_attribution(
                user_id="user-1", source="friend"
            )

        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_helper_returns_failure_on_db_error(self):
        from app.services import database_service

        with patch.object(
            database_service, "get_admin_supabase_client"
        ) as mock_client_factory:
            mock_client_factory.side_effect = Exception("DB down")

            result = await database_service.save_user_attribution(
                user_id="user-1", source="friend"
            )

        assert result["success"] is False
        assert "error" in result
