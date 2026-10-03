"""U8b (S71) fix-round pins: four mutants of the deletion path that the frozen
RED file (tests/test_account_deletion_u8b.py, UG2) cannot see.

SPEC: docs/investigations/2026-10-03-session-71-state/U8B_ACCOUNT_DELETION_SPEC.md
R6 (purge the per-user caches; ENABLE_ASYNC_REDIS_OFFLOAD dispatches off-loop)
and R7 (no exception text in the two deletion log lines, finding F-LOG).

The backend adversary measured these mutants surviving the whole kill set:
  MD1 -- `exc_info=True` added to the cascade log call (database_service);
  MD2 -- `exc_info=True` added to the route log call (auth_routes);
         either one puts the PostgREST traceback, whose APIError text carries
         `details` = "Failing row contains (...)", into the log record;
  MS  -- the SQLSTATE falls back to the exception text
         (`getattr(e, "code", None) or str(e)`);
  MG  -- the purge always runs inline, ignoring ENABLE_ASYNC_REDIS_OFFLOAD;
  MW  -- the purge's failure WARNING logs the exception text, not its type.
Each test below kills one of them (measured in the fix round).

Mocks only: no database, network or Redis is touched. The sentinel is a plain
word, never a key-shaped string.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests._retro_r_mig_sql import install_network_guard

SENTINEL = "U8B_FIX_SENTINEL_ROW"
USER_ID = "user-u8b-fix"


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"U8b fix pins must never touch the network: {attempts}"


def _api_error(code="23502"):
    from postgrest.exceptions import APIError

    return APIError({
        "message": "null value in column violates not-null constraint",
        "code": code,
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


def _traceback_requests(log_mock: MagicMock) -> list[str]:
    """Every logger call that would attach a traceback or a stack to the record."""
    bad = []
    for name, _args, kwargs in log_mock.method_calls:
        if name == "exception":
            bad.append("logger.exception(...)")
        if kwargs.get("exc_info"):
            bad.append(f"logger.{name}(..., exc_info={kwargs['exc_info']!r})")
        if kwargs.get("stack_info"):
            bad.append(f"logger.{name}(..., stack_info={kwargs['stack_info']!r})")
    return bad


class _CaptureHandler(logging.Handler):
    """Formats every record WITH its traceback, as a real log handler would."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        self.texts: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.texts.append(self.format(record))


class _captured:
    """Attach a capture handler to one real module logger at DEBUG, restore after."""

    def __init__(self, lg: logging.Logger) -> None:
        self.lg = lg
        self.handler = _CaptureHandler()

    def __enter__(self) -> _CaptureHandler:
        self._level, self._disabled = self.lg.level, self.lg.disabled
        self.lg.setLevel(logging.DEBUG)
        self.lg.disabled = False
        self.lg.addHandler(self.handler)
        return self.handler

    def __exit__(self, *exc) -> None:
        self.lg.removeHandler(self.handler)
        self.lg.setLevel(self._level)
        self.lg.disabled = self._disabled


def _admin_client() -> MagicMock:
    admin = MagicMock()
    admin.auth.admin.delete_user.return_value = None
    return admin


# ---------------------------------------------------------------------------
# R7 -- MD1: the cascade log line never attaches the traceback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cascade_failure_log_requests_no_traceback():
    """MD1: the cascade except arm logs with no exc_info / stack_info and no
    logger.exception: the APIError traceback text carries the failing row."""
    from postgrest.exceptions import APIError

    from app.services import database_service

    client = MagicMock()
    client.rpc.return_value.execute.side_effect = _api_error()
    with patch.object(database_service, "get_admin_supabase_client", return_value=client), \
            patch.object(database_service, "logger") as log:
        with pytest.raises(APIError):
            await database_service.delete_user_data_cascade(USER_ID)
    assert log.error.called, "the cascade failure is no longer logged at all"
    bad = _traceback_requests(log)
    assert not bad, f"the cascade log line attaches the traceback: {bad}"


@pytest.mark.asyncio
async def test_cascade_failure_formatted_log_record_carries_no_row_details():
    """MD1, end to end: through a real logging handler that formats the record
    WITH any attached traceback, no text carries the PostgREST details."""
    from postgrest.exceptions import APIError

    from app.services import database_service

    client = MagicMock()
    client.rpc.return_value.execute.side_effect = _api_error()
    with patch.object(database_service, "get_admin_supabase_client", return_value=client), \
            _captured(database_service.logger) as cap:
        with pytest.raises(APIError):
            await database_service.delete_user_data_cascade(USER_ID)
    assert cap.texts, "no log record was emitted for the cascade failure"
    leaked = [t for t in cap.texts if SENTINEL in t]
    assert not leaked, f"a formatted cascade log record carries the failing row: {leaked}"
    assert any("23502" in t for t in cap.texts), cap.texts


# ---------------------------------------------------------------------------
# R7 -- MS: the SQLSTATE slot never falls back to the exception text
# ---------------------------------------------------------------------------

def _codeless_errors():
    import httpx

    return [
        RuntimeError(f"rpc transport failed for {SENTINEL}@example.invalid"),
        httpx.ConnectError(f"connect to https://{SENTINEL}.invalid/rest/v1/rpc failed"),
        _api_error(code=None),
    ]


@pytest.mark.parametrize("idx", [0, 1, 2], ids=["RuntimeError", "httpx.ConnectError", "APIError-code-None"])
@pytest.mark.asyncio
async def test_cascade_failure_without_a_sqlstate_logs_no_exception_text(idx):
    """MS: an exception with no (or a None) `.code` -- a transport error, a
    RuntimeError, an APIError without a code -- logs its TYPE only; the SQLSTATE
    slot must never fall back to str(e)."""
    from app.services import database_service

    exc = _codeless_errors()[idx]
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = exc
    with patch.object(database_service, "get_admin_supabase_client", return_value=client), \
            patch.object(database_service, "logger") as log:
        with pytest.raises(type(exc)):
            await database_service.delete_user_data_cascade(USER_ID)
    lines = _rendered(log)
    assert lines, "the cascade failure is no longer logged at all"
    leaked = [ln for ln in lines if SENTINEL in ln]
    assert not leaked, f"the cascade log line carries the exception text: {leaked}"
    assert any(type(exc).__name__ in ln for ln in lines), lines


# ---------------------------------------------------------------------------
# R7 -- MD2: the route log line never attaches the traceback
# ---------------------------------------------------------------------------

def _delete_via_route(log_patch):
    from fastapi.testclient import TestClient

    from app.main import app

    with patch("app.api.auth_routes.verify_token",
               return_value={"id": USER_ID, "email": "u8b-fix@example.invalid"}), \
            patch("app.api.auth_routes.delete_user_account", new=AsyncMock(side_effect=_api_error())), \
            patch("app.middleware.rate_limiter.limiter.enabled", False), \
            log_patch as log:
        response = TestClient(app).delete(
            "/api/v1/auth/account", headers={"Authorization": "Bearer u8b-fix-token"}
        )
    return response, log


def test_delete_route_failure_log_requests_no_traceback():
    """MD2: the route except arm logs with no exc_info / stack_info and no
    logger.exception, and still answers 500 without the row details."""
    response, log = _delete_via_route(patch("app.api.auth_routes.logger"))
    assert response.status_code == 500, response.text
    assert SENTINEL not in response.text
    assert log.error.called, "the route failure is no longer logged at all"
    bad = _traceback_requests(log)
    assert not bad, f"the route log line attaches the traceback: {bad}"


def test_delete_route_failure_formatted_log_record_carries_no_row_details():
    """MD2, end to end: a real handler on the auth_routes logger formats every
    record WITH any traceback; none carries the PostgREST details."""
    from app.api import auth_routes

    cap_ctx = _captured(auth_routes.logger)
    response, cap = _delete_via_route(cap_ctx)
    assert response.status_code == 500, response.text
    assert cap.texts, "no log record was emitted for the route failure"
    leaked = [t for t in cap.texts if SENTINEL in t]
    assert not leaked, f"a formatted route log record carries the failing row: {leaked}"


# ---------------------------------------------------------------------------
# R6 -- MG: ENABLE_ASYNC_REDIS_OFFLOAD really moves the purge off the loop
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("offload", [None, "true"], ids=["offload-unset", "offload-true"])
def test_purge_runs_off_the_event_loop_only_under_the_offload_flag(monkeypatch, offload):
    """MG: with ENABLE_ASYNC_REDIS_OFFLOAD=true every delete_cached call runs on a
    worker thread (not the event-loop thread); with it unset every call runs
    inline on the loop thread (the R6 shape, the repo idiom)."""
    if offload is None:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    else:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", offload)
    from app.services import auth_service

    threads: list[int] = []
    loop_thread: list[int] = []

    def _record(key):
        threads.append(threading.get_ident())
        return True

    async def _run():
        loop_thread.append(threading.get_ident())
        return await auth_service.delete_user_account(USER_ID)

    with patch("app.services.database_service.delete_user_data_cascade",
               new=AsyncMock(return_value=True)), \
            patch("app.services.auth_service.get_admin_client", return_value=_admin_client()), \
            patch("app.services.auth_service.delete_cached", side_effect=_record):
        assert asyncio.run(_run()) is True
    assert len(threads) == 5, threads
    on_loop = [t == loop_thread[0] for t in threads]
    if offload is None:
        assert all(on_loop), "with the flag unset the purge must run inline (R6)"
    else:
        assert not any(on_loop), (
            "with ENABLE_ASYNC_REDIS_OFFLOAD=true a purge call ran ON the event-loop thread"
        )


# ---------------------------------------------------------------------------
# R6 -- MW: the purge failure WARNING names the exception type only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_purge_failure_warning_names_only_the_exception_type(monkeypatch):
    """MW: when delete_cached raises, the fail-soft WARNING logs the exception
    TYPE, never its text, and no traceback is attached."""
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    from app.services import auth_service

    with patch("app.services.database_service.delete_user_data_cascade",
               new=AsyncMock(return_value=True)), \
            patch("app.services.auth_service.get_admin_client", return_value=_admin_client()), \
            patch("app.services.auth_service.delete_cached",
                  side_effect=RuntimeError(f"redis down at {SENTINEL}")), \
            patch.object(auth_service, "logger") as log:
        assert await auth_service.delete_user_account(USER_ID) is True
    lines = _rendered(log)
    leaked = [ln for ln in lines if SENTINEL in ln]
    assert not leaked, f"the purge WARNING carries the exception text: {leaked}"
    warns = [ln for ln in lines if "RuntimeError" in ln]
    assert len(warns) == 5, lines
    assert not _traceback_requests(log), _traceback_requests(log)
