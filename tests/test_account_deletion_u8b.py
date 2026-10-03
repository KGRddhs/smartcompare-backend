"""U8b (S71, MYEZ Apple launch lane): backend half of account deletion.

SPEC: docs/investigations/2026-10-03-session-71-state/U8B_ACCOUNT_DELETION_SPEC.md
sections 5.2 and 5.3 (backend half), R6 (purge the per-user caches, finding
F-CACHE) and R7 (no exception text in the deletion log lines, finding F-LOG),
as corrected by C7 and ruled by UR1-UR15.

Mocks only: the Supabase admin clients, the cascade and delete_cached are stubs
patched at the importing module name; no database, network or Redis is
touched. The sentinel is a plain word (never a key-shaped string). Log
assertions patch the module logger with a MagicMock and render every call
(args[0] % args[1:] when there are args), so they do not depend on caplog
propagation. Nothing this unit creates is imported at module top.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests._retro_r_mig_sql import install_network_guard

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL = "U8B_SENTINEL_ROW_DETAILS"
USER_ID = "user-u8b"
FIVE_TEMPLATES = (
    "home:savings:{user_id}",
    "home:smart_pick:{user_id}",
    "profile_recent:{user_id}",
    "monthly_stats:{user_id}",
    "priorities_weighted:{user_id}",
)
FIVE_KEYS = sorted(t.format(user_id=USER_ID) for t in FIVE_TEMPLATES)


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"U8b backend tests must never touch the network: {attempts}"


def _api_error():
    from postgrest.exceptions import APIError

    return APIError({
        "message": "null value in column violates not-null constraint",
        "code": "23502",
        "hint": None,
        "details": f"Failing row contains ({SENTINEL}).",
    })


def _rendered(log_mock: MagicMock) -> list[str]:
    out = []
    for _name, args, _kwargs in log_mock.method_calls:
        if not args:
            continue
        try:
            out.append(str(args[0]) % args[1:] if len(args) > 1 else str(args[0]))
        except (TypeError, ValueError):
            out.append(" ".join(str(a) for a in args))
    return out


def _admin_client(events: list[str] | None = None, side_effect=None) -> MagicMock:
    admin = MagicMock()

    def _delete_user(uid):
        if events is not None:
            events.append("auth_delete")
        if side_effect is not None:
            raise side_effect
        return None

    admin.auth.admin.delete_user.side_effect = _delete_user
    return admin


# ---------------------------------------------------------------------------
# 5.2 RED -- R7: no exception text in the deletion log lines (F-LOG)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cascade_rpc_failure_logs_no_postgrest_details(monkeypatch):
    """U8b 5.2 / R7: a PostgREST APIError from the cascade RPC is re-raised and
    no log line carries its `details` (the user's row); the SQLSTATE is logged."""
    from postgrest.exceptions import APIError

    from app.services import database_service

    client = MagicMock()
    client.rpc.return_value.execute.side_effect = _api_error()
    with patch.object(database_service, "get_admin_supabase_client", return_value=client), \
            patch.object(database_service, "logger") as log:
        with pytest.raises(APIError):
            await database_service.delete_user_data_cascade(USER_ID)
    lines = _rendered(log)
    leaked = [ln for ln in lines if SENTINEL in ln]
    assert not leaked, f"cascade log line carries the PostgREST details: {leaked}"
    assert any("23502" in ln for ln in lines), f"no log line carries the SQLSTATE 23502: {lines}"
    log.exception.assert_not_called()


def test_delete_route_failure_logs_no_exception_text(monkeypatch):
    """U8b 5.2 / R7: DELETE /api/v1/auth/account on a failing deletion returns
    500 "Account deletion failed" and logs no exception text."""
    from fastapi.testclient import TestClient

    from app.main import app

    with patch("app.api.auth_routes.verify_token",
               return_value={"id": USER_ID, "email": "u8b@example.invalid"}), \
            patch("app.api.auth_routes.delete_user_account", new=AsyncMock(side_effect=_api_error())), \
            patch("app.middleware.rate_limiter.limiter.enabled", False), \
            patch("app.api.auth_routes.logger") as log:
        response = TestClient(app).delete(
            "/api/v1/auth/account", headers={"Authorization": "Bearer u8b-token"}
        )
    assert response.status_code == 500, response.text
    body = response.json()
    # app/main.py http_exception_handler renders HTTPException.detail as "error"
    # ({"success": false, "error": ..., "code": "SERVER_ERROR"}), measured at base.
    assert "Account deletion failed" in (body.get("detail"), body.get("error")), body
    assert SENTINEL not in response.text
    lines = _rendered(log)
    leaked = [ln for ln in lines if SENTINEL in ln]
    assert not leaked, f"route log line carries the exception text: {leaked}"


# ---------------------------------------------------------------------------
# 5.2 RED -- R6: purge the five per-user caches (F-CACHE)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("offload", [None, "true"], ids=["offload-unset", "offload-true"])
@pytest.mark.asyncio
async def test_delete_user_account_purges_the_five_per_user_caches(monkeypatch, offload):
    """U8b 5.2 / R6: delete_user_account calls delete_cached with exactly the
    five per-user keys, inline and with ENABLE_ASYNC_REDIS_OFFLOAD=true."""
    if offload is None:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    else:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", offload)
    from app.services import auth_service

    with patch("app.services.database_service.delete_user_data_cascade",
               new=AsyncMock(return_value=True)), \
            patch("app.services.auth_service.get_admin_client", return_value=_admin_client()), \
            patch("app.services.auth_service.delete_cached", create=True) as dc:
        assert await auth_service.delete_user_account(USER_ID) is True
    keys = sorted(c.args[0] for c in dc.call_args_list)
    assert keys == FIVE_KEYS, f"purged keys {keys} != {FIVE_KEYS}"


@pytest.mark.asyncio
async def test_delete_order_is_cascade_then_purge_then_auth_delete(monkeypatch):
    """U8b 5.2 / R6: the order is cascade, the five cache purges, auth delete."""
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    from app.services import auth_service

    events: list[str] = []

    async def _cascade(uid):
        events.append("cascade")
        return True

    with patch("app.services.database_service.delete_user_data_cascade", new=_cascade), \
            patch("app.services.auth_service.get_admin_client", return_value=_admin_client(events)), \
            patch("app.services.auth_service.delete_cached", create=True,
                  side_effect=lambda key: events.append("purge")):
        assert await auth_service.delete_user_account(USER_ID) is True
    assert events == ["cascade"] + ["purge"] * 5 + ["auth_delete"], events


@pytest.mark.asyncio
async def test_cache_purge_failure_never_blocks_the_auth_delete(monkeypatch):
    """U8b 5.2 / R6, C7: every key is attempted although each purge raises, and
    the auth delete still runs once; the deletion returns True."""
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    from app.services import auth_service

    admin = _admin_client()
    with patch("app.services.database_service.delete_user_data_cascade",
               new=AsyncMock(return_value=True)), \
            patch("app.services.auth_service.get_admin_client", return_value=admin), \
            patch("app.services.auth_service.delete_cached", create=True,
                  side_effect=RuntimeError("redis down")) as dc:
        assert await auth_service.delete_user_account(USER_ID) is True
    assert dc.call_count == 5, f"delete_cached called {dc.call_count} times, expected 5 (C7)"
    admin.auth.admin.delete_user.assert_called_once_with(USER_ID)


def test_purge_key_templates_match_their_writers():
    """U8b 5.2 / R6: DELETED_USER_CACHE_KEY_TEMPLATES is exactly the five
    templates, and each one is written as an f-string by home_routes or
    profile_routes (the drift pin)."""
    from app.services import auth_service

    templates = getattr(auth_service, "DELETED_USER_CACHE_KEY_TEMPLATES", None)
    assert templates is not None, (
        "U8b: app.services.auth_service.DELETED_USER_CACHE_KEY_TEMPLATES does not exist"
    )
    assert len(templates) == 5 and set(templates) == set(FIVE_TEMPLATES), templates
    src = "".join(
        (REPO_ROOT / "app" / "api" / name).read_text(encoding="utf-8")
        for name in ("home_routes.py", "profile_routes.py")
    )
    missing = [t for t in templates if f'f"{t}"' not in src]
    assert not missing, f"no writer f-string for {missing}"


# ---------------------------------------------------------------------------
# 5.3 PIN -- green at base and at head
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cascade_failure_skips_purge_and_auth_delete(monkeypatch):
    """U8b 5.3: if the cascade raises, no cache purge and no auth delete run,
    and the exception propagates."""
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    from app.services import auth_service

    admin = _admin_client()
    with patch("app.services.database_service.delete_user_data_cascade",
               new=AsyncMock(side_effect=RuntimeError("cascade failed"))), \
            patch("app.services.auth_service.get_admin_client", return_value=admin), \
            patch("app.services.auth_service.delete_cached", create=True) as dc:
        with pytest.raises(RuntimeError, match="cascade failed"):
            await auth_service.delete_user_account(USER_ID)
    dc.assert_not_called()
    admin.auth.admin.delete_user.assert_not_called()


@pytest.mark.asyncio
async def test_auth_delete_failure_propagates_after_the_cascade(monkeypatch):
    """U8b 5.3: if the auth delete raises, delete_user_account raises, after
    the cascade ran exactly once."""
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    from app.services import auth_service

    cascade = AsyncMock(return_value=True)
    admin = _admin_client(side_effect=RuntimeError("auth delete failed"))
    with patch("app.services.database_service.delete_user_data_cascade", new=cascade), \
            patch("app.services.auth_service.get_admin_client", return_value=admin), \
            patch("app.services.auth_service.delete_cached", create=True):
        with pytest.raises(RuntimeError, match="auth delete failed"):
            await auth_service.delete_user_account(USER_ID)
    cascade.assert_awaited_once_with(USER_ID)
    admin.auth.admin.delete_user.assert_called_once_with(USER_ID)


def test_delete_route_keeps_rate_limit_and_auth():
    """U8b 5.3 / R7: the route keeps @router.delete("/account"),
    @limiter.limit("1/minute") directly above `async def delete_account`, and
    Depends(get_current_user)."""
    src = (REPO_ROOT / "app" / "api" / "auth_routes.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.search(
        r'@router\.delete\("/account"\)\n@limiter\.limit\("1/minute"\)\nasync def delete_account\(',
        src,
    )
    assert m, "delete_account lost its route decorator or its 1/minute rate limit"
    sig = src[m.end(): src.find(":\n", m.end())]
    assert "Depends(get_current_user)" in sig, sig
