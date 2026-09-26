"""#198 RED -- expected client 401s are logged at ERROR with the raw ``str(e)``.

Unit spec: ``.qa-s68/AUTH_198_SPEC.md`` (session 68). UNFLAGGED by ruling:
log hygiene with no legitimate reader of the old line.

--------------------------------------------------------------------------
WHAT IS WRONG AT BASE 61585c58 (measured through pytest, netguard on)
--------------------------------------------------------------------------

``auth_service._categorize_auth_error``'s generic branch does
``logger.error(f"Auth error in {context}: {e}")`` for EVERY context, so

* ``_categorize_auth_error(AuthApiError("Invalid Refresh Token: Refresh Token
  Not Found", 400, "refresh_token_not_found"), "refresh")`` emits ONE record,
  level ERROR, message ``Auth error in refresh: Invalid Refresh Token: Refresh
  Token Not Found`` (exc_info None), and returns the generic dict;
* ``POST /api/v1/auth/refresh`` with a garbage refresh token answers 401
  ``AUTH_REQUIRED`` "Something went wrong. Please try again later." -- correct --
  and leaves that same ERROR record, which the Sentry LoggingIntegration
  (default ``event_level=logging.ERROR`` on the pinned sentry-sdk 2.68.1) turns
  into an error EVENT: the 2026-09-24 14:07:22 UTC probe issue;
* ``RuntimeError("boom secret=abc")`` logs ``Auth error in refresh: boom
  secret=abc`` -- the exception VALUE, which on the auth path can carry a
  credential (the R-W0/R-AUTH rule the ``[auth]`` WARNING lines already obey).

--------------------------------------------------------------------------
THE CONTRACT THESE NODES PIN (spec section 1)
--------------------------------------------------------------------------

* expected client failure (never a server-side credential/config failure --
  R11 carve-out, see T13; then ``.status`` an int in 400..499 except 429, not
  a bool; else a status-less exception whose lower-cased text carries an
  expected-client term) -> ONE WARNING
  ``[auth] <context> rejected upstream: <Type> status=<status>`` -- TYPE only;
* anything else -> ONE ERROR ``Auth error in <context>: <Type>`` -- the base
  prefix kept, TYPE only, no ``exc_info``;
* the three message-matched early returns and the transient branch log nothing
  (unchanged); every RETURNED dict is byte-identical to base in every branch,
  including the social_login ``[B4-BE-DIAG]`` RESPONSE (kept; two
  ``tests/test_auth_interceptor.py`` nodes are red BY CHOICE on it).

Base dicts: asserted as the literal dicts the base source shows; each was
measured at 61585c58 in a detached scratch worktree (every context x status
400/401/403/404/422 -> the generic dict, social_login -> the DIAG string).

--------------------------------------------------------------------------
RED / PIN
--------------------------------------------------------------------------

RED (fail at base): T1, T2 (x9 contexts), T3 (x9 contexts), T7.
PIN (green at base, must stay green): T4, T5 (x6), T6 (x4), T8, T9 (x3).
GREEN-phase pins (ruling R3/R4, added with the fix): T11 -- one status-less
row per ``_EXPECTED_CLIENT_AUTH_ERROR_TERMS`` entry (no dead entries); T12 --
an int status decides alone (429/5xx carrying a term stay ERROR), a bool
status is not a status.
FIXER-phase pins (adversary rows): T3's ``record_text`` also reads the
record's ``extra=`` attributes and ``stack_info`` (both shipped by Sentry's
LoggingIntegration) and T3 asserts ``stack_info is None``; T2 carries a 499
row and T12 a 399 row, so both outer boundaries of ``400 <= status < 500``
are pinned.
FIX-ROUND-2 pins (Fable rulings R11/R12): T13 -- a SERVER-SIDE credential or
config 4xx (``AuthSessionMissingError``, or text carrying an entry of
``_SERVER_SIDE_AUTH_ERROR_TERMS``) is ONE TYPE-only ERROR whatever its status,
the carve-out precedes the status rule, one row per entry, and a plain
expected 400/401 is still a WARNING; the carve-out also precedes the
expected-client fragment fallback (one STATUS-LESS row per entry whose text
carries both a server-side term and "invalid token" -> ERROR, fix round 3,
re-adversary); T14 -- both lines are PRE-FORMATTED
(``record.args`` empty, ``record.msg == record.getMessage()``), so Sentry's
``logentry.message`` differs per (context, type).

Two deliberate deviations from the spec's wording, both so a PIN is really
green at base (reported to the orchestrator):
* T4 -- the base ERROR record is ``Auth error in refresh: boom``; it does NOT
  contain ``RuntimeError``, so "contains RuntimeError" cannot be a base-green
  pin. T4 pins the count, the level, the base prefix and ``exc_info is None``;
  the TYPE-in-the-ERROR-record half is asserted by T3 (RED).
* T9 -- the social_login LOG half ("same WARNING/ERROR rule, no str(e) in the
  log") is RED at base, so it lives in T2[social_login] and T3[social_login];
  T9 pins only the unchanged DIAG RESPONSE.

--------------------------------------------------------------------------
T10 -- the green's mutation table (run from byte snapshots, spec gate (b))
--------------------------------------------------------------------------

row  mutation of the green                               must redden
(i)  log ``str(e)`` / the message instead of the TYPE     T1, T2, T3, T7
(ii) classify by message only (drop the status rule)      T2 (status-4xx
     -> a 4xx with an unknown message logs ERROR               opaque rows)
(iii) treat 429 as expected client                         T6 (429/5xx row)
(iv) ``exc_info=True`` on the ERROR                         T3 (exc_info /
     -> the record carries the exception value                caplog.text), T4
(v)  ``_EXPECTED_CLIENT_AUTH_ERROR_TERMS`` emptied          T2 (status-less
                                                             SDK-message rows)
(vi) helper returns constant False                          T1, T2, T7
(vii) helper returns constant True                          T3, T4, T6 (429/5xx)

Measured on a PROTOTYPE of the section-1 design in a detached scratch worktree
at 61585c58 (never in this worktree): prototype 35 passed; each row above
reddened exactly the listed nodes (i 20, ii 9, iii 1, iv 10, v 9, vi 11,
vii 11 failed).

ZERO NETWORK: an autouse guard blocks every non-loopback ``connect`` /
``getaddrinfo`` and fails the node on any attempt (the process-wide netguard
plugin is the second layer).
"""
from __future__ import annotations

import inspect
import logging
import os
import re
import socket
from types import SimpleNamespace
from typing import Any, List

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import auth_service

try:  # the pinned SDK class (supabase-auth 2.31.0): AuthApiError(message, status, code)
    from supabase_auth.errors import AuthApiError as _SdkAuthApiError
except ImportError:  # pragma: no cover - fallback keeps the message path exercised
    _SdkAuthApiError = None


class _FallbackAuthApiError(Exception):
    """Plain-Exception stand-in with the SDK's ``.status`` / ``.code`` shape."""

    def __init__(self, message: str, status: int, code: Any) -> None:
        Exception.__init__(self, message)
        self.message = message
        self.status = status
        self.code = code


def api_error(message: str, status: int, code: Any) -> Exception:
    if _SdkAuthApiError is not None:
        return _SdkAuthApiError(message, status, code)
    return _FallbackAuthApiError(message, status, code)


API_ERROR_TYPE = type(api_error("x", 400, None)).__name__

LOGGER = "app.services.auth_service"
REFRESH_URL = "/api/v1/auth/refresh"

CONTEXTS = [
    "register", "login", "refresh", "social_login", "change_password",
    "update_email", "update_profile", "password_reset", "password_recovery",
]

# Base dicts (auth_service.py:224-256 at 61585c58, measured).
GENERIC = {"success": False, "error": "Something went wrong. Please try again later."}
TRANSIENT = {
    "success": False,
    "error": "Connection failed. Please try again.",
    "code": "UPSTREAM_UNAVAILABLE",
}


def base_dict(exc: Exception, context: str) -> dict:
    """The dict the base generic branch returns for ``exc`` in ``context``."""
    if context == "social_login":
        return {
            "success": False,
            "error": "[B4-BE-DIAG] supabase_error=" + str(exc)[:300]
            + " exc_type=" + type(exc).__name__,
        }
    return dict(GENERIC)


# The SDK messages measured on the pinned supabase-auth 2.31.0 (handle_exception
# over in-memory httpx.HTTPStatusError objects built from the gotrue JSON bodies
# the repo's own fake-gotrue tables use). str(e) is the message ONLY -- the code
# is never in it.
REFRESH_NOT_FOUND = "Invalid Refresh Token: Refresh Token Not Found"
REFRESH_ALREADY_USED = "Invalid Refresh Token: Already Used"
BAD_JWT_EXPIRED = (
    "invalid JWT: unable to parse or verify signature, token has invalid claims: "
    "token is expired"
)

# An upstream reason no message term can match -- only the STATUS says it is a
# client verdict (T10 row ii).
OPAQUE = "Opaque upstream reason QX-198"
CLIENT_STATUSES = [
    (400, "refresh_token_not_found"),
    (401, "bad_jwt"),
    (403, "user_banned"),
    (404, "session_not_found"),
    (422, "validation_failed"),
    # The rule's UPPER boundary (R4: 400 <= status < 500): without a 4xx above
    # 422 a narrowed bound such as ``status < 430`` stays green (fixer row).
    (499, None),
]

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}


# ---------------------------------------------------------------------------
# autouse: zero network
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: List[str] = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _host_of(address: Any) -> str:
        if isinstance(address, tuple) and address:
            return str(address[0])
        return str(address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is None or str(host) in _LOOPBACK_HOSTS:
            return real_getaddrinfo(host, *args, **kwargs)
        attempts.append("getaddrinfo:" + str(host))
        raise OSError("zero-network guard: getaddrinfo(" + str(host) + ") blocked")

    def guarded_connect(self, address):
        if self.family == getattr(socket, "AF_UNIX", object()) or _host_of(address) in _LOOPBACK_HOSTS:
            return real_connect(self, address)
        attempts.append("connect:" + _host_of(address))
        raise OSError("zero-network guard: connect(" + _host_of(address) + ") blocked")

    def guarded_connect_ex(self, address):
        if self.family == getattr(socket, "AF_UNIX", object()) or _host_of(address) in _LOOPBACK_HOSTS:
            return real_connect_ex(self, address)
        attempts.append("connect_ex:" + _host_of(address))
        raise OSError("zero-network guard: connect_ex(" + _host_of(address) + ") blocked")

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    yield
    assert not attempts, "zero-network guard: non-loopback network attempted: " + repr(attempts)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def categorize(caplog, exc: Exception, context: str) -> dict:
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        return auth_service._categorize_auth_error(exc, context)


def module_records(caplog) -> list:
    return [r for r in caplog.records if r.name == LOGGER]


def error_records(caplog) -> list:
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


def warning_records(caplog) -> list:
    return [r for r in module_records(caplog) if r.levelno == logging.WARNING]


def describe(records) -> list:
    return [(r.name, r.levelname, r.getMessage()) for r in records]


# The attributes every LogRecord carries (plus the two a Formatter adds);
# anything else on a record came from ``extra=`` or a filter.
_STANDARD_RECORD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def record_extras(record) -> dict:
    """What ``extra=`` put on the record -- the part Sentry's LoggingIntegration
    ships as ``event["extra"]`` / breadcrumb ``data`` (``_extra_from_record``)."""
    return {k: v for k, v in vars(record).items() if k not in _STANDARD_RECORD_ATTRS}


def record_text(record) -> str:
    """The text a handler (Sentry's included) can read off one record: the
    message, the template, the args, the exception (exc_info / exc_text), the
    stack_info text and every ``extra=`` attribute. It cannot see frame LOCALS
    (Sentry attaches them to a stack_info / exc_info stacktrace when
    ``include_local_variables`` is on) -- T3 pins ``exc_info is None`` and
    ``stack_info is None`` for that half."""
    parts = [record.getMessage(), str(record.msg), repr(record.args)]
    if record.exc_info:
        parts.append(repr(record.exc_info))
    if getattr(record, "exc_text", None):
        parts.append(str(record.exc_text))
    if getattr(record, "stack_info", None):
        parts.append(str(record.stack_info))
    parts.append(repr(record_extras(record)))
    return "\n".join(parts)


# ===========================================================================
# T1 RED -- the refresh probe from the issue
# ===========================================================================
def test_refresh_invalid_token_logs_one_warning_type_only_and_no_error(caplog):
    """The exact exception the 2026-09-24 orchestrator probe produced."""
    exc = api_error(REFRESH_NOT_FOUND, 400, "refresh_token_not_found")
    result = categorize(caplog, exc, "refresh")

    assert error_records(caplog) == [], (
        "an invalid refresh token is an expected client 401, not an application "
        "error: an ERROR record is present (Sentry ships it as an error event): "
        + repr(describe(error_records(caplog)))
    )
    leaked = [m for m in describe(caplog.records) if "Refresh Token Not Found" in m[2]]
    assert leaked == [], "the exception message reached a log record: " + repr(leaked)
    warnings = warning_records(caplog)
    assert len(warnings) == 1, (
        "expected exactly one WARNING from " + LOGGER + "; got "
        + repr(describe(module_records(caplog)))
    )
    assert API_ERROR_TYPE in warnings[0].getMessage(), (
        "the WARNING must name the exception TYPE; got " + warnings[0].getMessage()
    )
    assert result == GENERIC, "the returned dict must stay byte-identical to base: " + repr(result)


# ===========================================================================
# T2 RED -- no expected client failure is logged at ERROR, in any context
# ===========================================================================
@pytest.mark.parametrize("context", CONTEXTS)
def test_expected_client_error_never_logs_at_error_in_any_context(caplog, context):
    """Two families per context:

    * STATUS rows: a 4xx ``AuthApiError`` whose message no term can match --
      only the status rule classifies it (kills T10 row ii);
    * STATUS-LESS rows: a plain ``Exception`` carrying a measured SDK message
      (what ``complete_password_recovery`` hands the categoriser -- it re-wraps
      as ``Exception(str(e))``, dropping ``.status``) -- only the message tuple
      classifies it (kills T10 row v).
    """
    cases = [api_error(OPAQUE + " " + str(status), status, code) for status, code in CLIENT_STATUSES]
    cases += [Exception(REFRESH_NOT_FOUND), Exception(REFRESH_ALREADY_USED), Exception(BAD_JWT_EXPIRED)]

    violations = []
    for exc in cases:
        result = categorize(caplog, exc, context)
        label = type(exc).__name__ + "(" + str(exc)[:40] + ") status=" + str(getattr(exc, "status", None))
        errors = describe(error_records(caplog))
        if errors:
            violations.append(label + ": ERROR record present " + repr(errors))
        leaked = [m for m in describe(caplog.records) if str(exc) in m[2]]
        if leaked:
            violations.append(label + ": message present in a record " + repr(leaked))
        warnings = warning_records(caplog)
        if len(warnings) != 1 or type(exc).__name__ not in warnings[0].getMessage():
            violations.append(
                label + ": expected one TYPE-only WARNING, got " + repr(describe(module_records(caplog)))
            )
        expected = base_dict(exc, context)
        if result != expected:
            violations.append(label + ": dict moved " + repr(result) + " != base " + repr(expected))

    assert violations == [], (
        "context " + context + ": expected client failures must log one TYPE-only "
        "WARNING and no ERROR (" + str(len(violations)) + " violations):\n"
        + "\n".join(violations)
    )


# ===========================================================================
# T3 RED -- a credential in the exception argument reaches no record
# ===========================================================================
@pytest.mark.parametrize("context", CONTEXTS)
def test_credential_in_the_exception_argument_never_reaches_any_record(caplog, context):
    secrets_by_case = [
        (api_error("Bearer eyJhbGciOi.secret-tail", 401, "bad_jwt"),
         ["eyJhbGciOi", "secret-tail"]),
        (RuntimeError("upstream said api_key=sk-live-000 boom"),
         ["sk-live-000", "api_key=", "upstream said"]),
    ]
    violations = []
    for exc, secrets in secrets_by_case:
        categorize(caplog, exc, context)
        label = type(exc).__name__
        for record in caplog.records:
            text = record_text(record)
            for secret in secrets:
                if secret in text:
                    violations.append(
                        label + ": " + repr(secret) + " in a " + record.levelname + " record: "
                        + record.getMessage()
                    )
            if record.exc_info is not None:
                violations.append(label + ": a " + record.levelname + " record carries exc_info")
            if record.stack_info is not None:
                # Sentry turns stack_info into a stacktrace that carries frame
                # locals (the exception included) under include_local_variables.
                violations.append(label + ": a " + record.levelname + " record carries stack_info")
        for secret in secrets:
            if secret in caplog.text:
                violations.append(label + ": " + repr(secret) + " in caplog.text")
        if isinstance(exc, RuntimeError):
            errors = error_records(caplog)
            if len(errors) != 1 or "RuntimeError" not in errors[0].getMessage():
                violations.append(
                    "RuntimeError: expected one ERROR record naming the TYPE, got "
                    + repr(describe(errors))
                )

    assert violations == [], (
        "context " + context + ": the exception value (which can carry a credential) "
        "must never reach a log record:\n" + "\n".join(violations)
    )


# ===========================================================================
# T4 PIN -- an unexpected exception still logs ERROR with the base prefix
# ===========================================================================
def test_unexpected_exception_still_logs_error_with_the_base_prefix(caplog):
    result = categorize(caplog, RuntimeError("boom"), "refresh")
    errors = [r for r in module_records(caplog) if r.levelno >= logging.ERROR]
    assert len(errors) == 1, "expected exactly one ERROR record; got " + repr(describe(caplog.records))
    assert errors[0].levelno == logging.ERROR, errors[0].levelname
    assert errors[0].getMessage().startswith("Auth error in refresh: "), errors[0].getMessage()
    assert errors[0].exc_info is None, "the ERROR record must not carry exc_info"
    assert warning_records(caplog) == [], (
        "an unexpected exception is not an expected client failure: "
        + repr(describe(warning_records(caplog)))
    )
    assert result == GENERIC, repr(result)


# ===========================================================================
# T5 PIN -- the three message-matched early returns
# ===========================================================================
_EARLY_RETURNS = [
    ("plain_invalid_login", Exception("Invalid login credentials"), "login",
     {"success": False, "error": "Invalid email or password"}),
    ("sdk_invalid_login", api_error("Invalid login credentials", 400, "invalid_credentials"), "login",
     {"success": False, "error": "Invalid email or password"}),
    ("plain_already_registered", Exception("User already registered"), "register",
     {"success": False, "error": "An account with this email already exists"}),
    ("sdk_already_registered", api_error("User already registered", 422, "user_already_exists"), "register",
     {"success": False, "error": "An account with this email already exists"}),
    ("plain_email_not_confirmed", Exception("Email not confirmed"), "login",
     {"success": False, "error": "Please verify your email before logging in"}),
    ("sdk_email_not_confirmed", api_error("Email not confirmed", 400, "email_not_confirmed"), "login",
     {"success": False, "error": "Please verify your email before logging in"}),
]


@pytest.mark.parametrize(
    "exc,context,expected", [row[1:] for row in _EARLY_RETURNS], ids=[row[0] for row in _EARLY_RETURNS]
)
def test_message_matched_branches_return_the_base_dicts_and_log_nothing(caplog, exc, context, expected):
    result = categorize(caplog, exc, context)
    assert result == expected, repr(result)
    assert module_records(caplog) == [], (
        "a message-matched early return logs nothing at base: " + repr(describe(module_records(caplog)))
    )


# ===========================================================================
# T6 PIN -- the transient branch is unchanged; 429 / 5xx are never "expected"
# ===========================================================================
class _RaisingAuth:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def refresh_session(self, refresh_token=None):
        raise self._exc


def test_transient_branch_unchanged_substring(caplog):
    result = categorize(caplog, Exception("connection reset"), "refresh")
    assert result == TRANSIENT, repr(result)
    assert result == auth_service._upstream_unavailable_result(), repr(result)
    assert error_records(caplog) == [], repr(describe(error_records(caplog)))


@pytest.mark.parametrize(
    "status,message,code",
    [(429, "Request rate limit reached", "over_request_rate_limit"),
     (503, "Service Unavailable", None)],
    ids=["429", "503"],
)
def test_transient_branch_unchanged_refresh_type_classifier(caplog, monkeypatch, status, message, code):
    """429 / 5xx through ``refresh_session``'s TYPE classifier -> the transient
    dict and its existing WARNING, never an ERROR."""
    import asyncio

    exc = api_error(message, status, code)
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: SimpleNamespace(auth=_RaisingAuth(exc)))
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        result = asyncio.run(auth_service.refresh_session("RT-198-T6"))
    assert result == TRANSIENT, repr(result)
    msgs = [m for _n, lvl, m in describe(module_records(caplog)) if lvl == "WARNING"]
    assert msgs == ["[auth] refresh upstream unavailable (transient): " + type(exc).__name__], repr(msgs)
    assert error_records(caplog) == [], repr(describe(error_records(caplog)))


def test_transient_branch_unchanged_429_and_5xx_are_not_expected_client(caplog):
    """Through the categoriser directly (login): a 429 / 5xx ``AuthApiError``
    whose text carries no transient term reaches the generic branch -- it must
    stay ERROR (never the expected-client WARNING). Kills T10 rows iii / vii."""
    for status, message, code in [
        (429, "Request rate limit reached", "over_request_rate_limit"),
        (500, "Unexpected failure, please check server logs for more information", "unexpected_failure"),
    ]:
        exc = api_error(message, status, code)
        result = categorize(caplog, exc, "login")
        errors = [r for r in module_records(caplog) if r.levelno >= logging.ERROR]
        assert len(errors) == 1 and errors[0].getMessage().startswith("Auth error in login: "), (
            "status " + str(status) + " is not an expected client failure: "
            + repr(describe(caplog.records))
        )
        assert warning_records(caplog) == [], repr(describe(warning_records(caplog)))
        assert result == GENERIC, repr(result)


# ===========================================================================
# T7 RED -- the route-level probe from the issue
# ===========================================================================
def test_route_level_invalid_refresh_probe_creates_no_error_record(caplog, monkeypatch):
    def _raise():
        raise api_error(REFRESH_NOT_FOUND, 400, "refresh_token_not_found")

    monkeypatch.setattr(auth_service, "get_auth_client", _raise)
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        with TestClient(app) as client:
            resp = client.post(REFRESH_URL, json={"refresh_token": "garbage-refresh-token-198"})
    body = resp.json()

    assert resp.status_code == 401, resp.text
    assert body.get("code") == "AUTH_REQUIRED", resp.text
    assert body.get("error") == GENERIC["error"], resp.text
    assert body.get("success") is False, resp.text

    assert error_records(caplog) == [], (
        "an invalid-refresh probe must create NO ERROR record (any logger) -- that "
        "record is the Sentry issue in #198: " + repr(describe(error_records(caplog)))
    )
    warnings = [m for n, lvl, m in describe(caplog.records) if n == LOGGER and lvl == "WARNING"]
    assert warnings == ["[auth] refresh rejected upstream: " + API_ERROR_TYPE + " status=400"], repr(warnings)


# ===========================================================================
# T8 PIN -- the Sentry logging integration keeps ERROR as its event level
# ===========================================================================
def test_sentry_logging_integration_keeps_error_as_the_event_level():
    import sentry_sdk.integrations as sentry_integrations
    from sentry_sdk.integrations import logging as sentry_logging

    # The installed SDK's default: WARNING stays a breadcrumb.
    assert sentry_logging.DEFAULT_EVENT_LEVEL == logging.ERROR
    signature = inspect.signature(sentry_logging.LoggingIntegration.__init__)
    assert signature.parameters["event_level"].default == logging.ERROR
    assert signature.parameters["level"].default <= logging.WARNING
    assert "sentry_sdk.integrations.logging.LoggingIntegration" in sentry_integrations._DEFAULT_INTEGRATIONS

    # This repo never overrides it: no LoggingIntegration(...) anywhere in app/,
    # the default integrations are never switched off, logging is never disabled.
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(auth_service.__file__)))
    offenders = []
    for root, _dirs, files in os.walk(app_dir):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for pattern in (r"LoggingIntegration\s*\(", r"default_integrations\s*=\s*False",
                            r"disabled_integrations\s*=", r"ignore_logger\s*\("):
                if re.search(pattern, text):
                    offenders.append(os.path.relpath(path, app_dir) + ": " + pattern)
    assert offenders == [], "Sentry logging overridden: " + repr(offenders)

    sentry_path = os.path.join(app_dir, "services", "sentry_service.py")
    with open(sentry_path, encoding="utf-8") as fh:
        source = fh.read()
    assert "sentry_sdk.init(" in source
    assert "event_level" not in source, "sentry_service must not set an event_level"


# ===========================================================================
# T9 PIN -- the social_login B4-BE-DIAG RESPONSE is unchanged
# ===========================================================================
@pytest.mark.parametrize(
    "exc",
    [RuntimeError("Provider error"),
     api_error("Opaque provider rejection", 400, "validation_failed"),
     RuntimeError("x" * 400)],
    ids=["runtime", "sdk_400", "truncated_300"],
)
def test_social_login_diag_response_unchanged(caplog, exc):
    result = categorize(caplog, exc, "social_login")
    assert result == {
        "success": False,
        "error": "[B4-BE-DIAG] supabase_error=" + str(exc)[:300] + " exc_type=" + type(exc).__name__,
    }, repr(result)
    assert result["error"].startswith("[B4-BE-DIAG] supabase_error=")
    assert result["error"].endswith(" exc_type=" + type(exc).__name__)


# ===========================================================================
# T11 (green, ruling R3) -- every _EXPECTED_CLIENT_AUTH_ERROR_TERMS entry is
# pinned by its own status-less row; no dead entries, no unpinned entries
# ===========================================================================
# One row per tuple entry. Each message carries THAT fragment and no other
# entry's, so deleting any single entry reddens exactly its row. The wordings
# are the gotrue messages measured on the pinned supabase-auth 2.31.0 (or the
# isolating fragment of one).
_TERM_ROWS = [
    ("invalid refresh token", "Invalid Refresh Token"),
    ("refresh token not found", "Refresh Token Not Found"),
    ("already used", "Already Used"),
    ("invalid jwt", "invalid JWT: unable to parse or verify signature"),
    ("token is expired", "token is expired"),
    ("invalid token", "Invalid token"),
    ("user not found", "User not found"),
    ("already been registered", "A user with this email address has already been registered"),
    ("new password should be different", "New password should be different from the old password."),
    ("password should be at least", "Password should be at least 6 characters."),
]


def test_every_expected_client_term_has_exactly_one_pinning_row():
    terms = auth_service._EXPECTED_CLIENT_AUTH_ERROR_TERMS
    assert sorted(terms) == sorted(t for t, _m in _TERM_ROWS), (
        "every tuple entry needs a row below and every row a tuple entry: " + repr(terms)
    )
    for term, message in _TERM_ROWS:
        assert term == term.lower() and term, repr(term)
        others = [t for t in terms if t != term and t in message.lower()]
        assert term in message.lower() and others == [], (term, message, others)


@pytest.mark.parametrize("term,message", _TERM_ROWS, ids=[t for t, _m in _TERM_ROWS])
def test_status_less_exception_carrying_the_term_logs_one_type_only_warning(caplog, term, message):
    exc = Exception(message)
    result = categorize(caplog, exc, "password_recovery")
    assert error_records(caplog) == [], repr(describe(error_records(caplog)))
    assert [m for _n, lvl, m in describe(module_records(caplog))] == [
        "[auth] password_recovery rejected upstream: Exception status=None"
    ], repr(describe(module_records(caplog)))
    assert result == GENERIC, repr(result)


# ===========================================================================
# T12 (green, rulings R3/R4) -- an int status decides alone; the fragments
# are consulted only when the exception carries no int status
# ===========================================================================
class _StatusCarrier(Exception):
    def __init__(self, message: str, status: Any) -> None:
        Exception.__init__(self, message)
        self.status = status


@pytest.mark.parametrize("status", [399, 429, 500, 503])
def test_a_non_client_status_is_an_error_even_when_the_text_carries_a_term(caplog, status):
    """399 and 500 are the R4 rule's two outer boundaries (a widened bound such
    as ``399 <= status`` or ``status <= 500`` reddens its row)."""
    exc = api_error(REFRESH_ALREADY_USED, status, None)
    result = categorize(caplog, exc, "refresh")
    assert [m for _n, lvl, m in describe(module_records(caplog))] == [
        "Auth error in refresh: " + API_ERROR_TYPE
    ], repr(describe(module_records(caplog)))
    assert error_records(caplog)[0].levelno == logging.ERROR
    assert result == GENERIC, repr(result)


def test_a_bool_status_is_not_a_status_so_the_fragments_decide(caplog):
    exc = _StatusCarrier(REFRESH_ALREADY_USED, True)
    result = categorize(caplog, exc, "refresh")
    assert error_records(caplog) == [], repr(describe(error_records(caplog)))
    assert [m for _n, lvl, m in describe(module_records(caplog))] == [
        "[auth] refresh rejected upstream: _StatusCarrier status=True"
    ], repr(describe(module_records(caplog)))
    assert result == GENERIC, repr(result)


# ===========================================================================
# T13 (fix round 2, ruling R11) -- a SERVER-SIDE credential/config 4xx stays
# ERROR: the carve-out runs BEFORE the status rule
# ===========================================================================
try:  # the pinned SDK's own HTTP-error mapper (supabase-auth 2.31.0)
    import httpx as _httpx
    from supabase_auth.helpers import handle_exception as _sdk_handle_exception
except ImportError:  # pragma: no cover - fallback keeps the ordering row meaningful
    _httpx = None
    _sdk_handle_exception = None

try:
    from supabase_auth.errors import AuthSessionMissingError as _SdkSessionMissing
except ImportError:  # pragma: no cover - the carve-out keys on the TYPE NAME
    class AuthSessionMissingError(Exception):  # noqa: N818 - mirrors the SDK name
        def __init__(self) -> None:
            Exception.__init__(self, "Auth session missing!")
            self.status = 400

    _SdkSessionMissing = AuthSessionMissingError

# One row per _SERVER_SIDE_AUTH_ERROR_TERMS entry; each message carries THAT
# fragment and no other entry's (and no expected-client fragment), so deleting
# any single entry reddens exactly its row. Measured through the pinned SDK's
# handle_exception over in-memory HTTPStatusErrors: "Invalid API key" and "No
# API key found in request" (Kong 401 bodies -> AuthApiError status 401),
# "User not allowed" (gotrue 403, code not_admin), "Email logins are disabled"
# and "Manual linking is disabled" (gotrue 422 config states). str(e) is the
# message only, so "not_admin" matches only text that embeds the code.
_SERVER_TERM_ROWS = [
    ("invalid api key", "Invalid API key"),
    ("no api key found", "No API key found in request"),
    ("not allowed", "User not allowed"),
    ("not_admin", "Forbidden (code=not_admin)"),
    ("is disabled", "Manual linking is disabled"),
    ("are disabled", "Email logins are disabled"),
]
# 401/403 as ruled, plus 422 (gotrue's status for the config states).
_SERVER_STATUSES = [401, 403, 422]


def assert_one_type_only_error(caplog, context: str, exc: Exception, label: str) -> None:
    records = module_records(caplog)
    assert [(r.levelname, r.getMessage()) for r in records] == [
        ("ERROR", "Auth error in " + context + ": " + type(exc).__name__)
    ], label + ": expected one TYPE-only ERROR and no WARNING, got " + repr(describe(records))
    assert warning_records(caplog) == [], label
    for record in caplog.records:
        assert str(exc) not in record_text(record), label + ": the message reached a record"


def test_every_server_side_term_has_exactly_one_pinning_row():
    terms = auth_service._SERVER_SIDE_AUTH_ERROR_TERMS
    assert sorted(terms) == sorted(t for t, _m in _SERVER_TERM_ROWS), (
        "every carve-out entry needs a row below and every row an entry: " + repr(terms)
    )
    expected_terms = auth_service._EXPECTED_CLIENT_AUTH_ERROR_TERMS
    for term, message in _SERVER_TERM_ROWS:
        assert term == term.lower() and term, repr(term)
        others = [t for t in terms if t != term and t in message.lower()]
        client = [t for t in expected_terms if t in message.lower()]
        assert term in message.lower() and others == [] and client == [], (term, message, others, client)


@pytest.mark.parametrize("term,message", _SERVER_TERM_ROWS, ids=[t for t, _m in _SERVER_TERM_ROWS])
def test_server_side_4xx_carrying_the_term_logs_one_type_only_error(caplog, term, message):
    for status in _SERVER_STATUSES:
        exc = api_error(message, status, None)
        result = categorize(caplog, exc, "login")
        assert_one_type_only_error(caplog, "login", exc, term + " status=" + str(status))
        assert result == GENERIC, repr(result)


def test_auth_session_missing_error_is_an_error_not_a_client_verdict(caplog):
    """The SDK raises it (status 400) when OUR code calls without a session --
    e.g. ``refresh_session("")`` -- a programming state, not a client verdict."""
    exc = _SdkSessionMissing()
    assert getattr(exc, "status", None) == 400, "precondition: the status rule alone would say WARNING"
    result = categorize(caplog, exc, "change_password")
    assert_one_type_only_error(caplog, "change_password", exc, "AuthSessionMissingError")
    assert result == GENERIC, repr(result)


def test_the_server_side_carve_out_precedes_the_status_rule(caplog):
    """A Kong 401 'Invalid API key' (a wrong Supabase key) through the SDK's own
    mapper: an int client status the status rule would call a WARNING."""
    if _sdk_handle_exception is not None:
        request = _httpx.Request("POST", "http://127.0.0.1:9/auth/v1/token")
        response = _httpx.Response(401, json={"message": "Invalid API key"}, request=request)
        exc = _sdk_handle_exception(_httpx.HTTPStatusError("kong", request=request, response=response))
    else:  # pragma: no cover
        exc = api_error("Invalid API key", 401, None)
    assert getattr(exc, "status", None) == 401 and str(exc) == "Invalid API key", (type(exc), str(exc))
    result = categorize(caplog, exc, "login")
    assert_one_type_only_error(caplog, "login", exc, "Kong 401 Invalid API key")
    assert auth_service._is_expected_client_auth_error(exc) is False
    assert result == GENERIC, repr(result)


@pytest.mark.parametrize("term,message", _SERVER_TERM_ROWS, ids=[t for t, _m in _SERVER_TERM_ROWS])
def test_the_carve_out_also_precedes_the_expected_client_fragments(caplog, term, message):
    """A STATUS-LESS exception (what complete_password_recovery hands the
    categoriser -- it re-wraps as ``Exception(str(e))``, ruling R2) whose text
    carries BOTH a server-side term and an expected-client fragment is still an
    ERROR: R11's carve-out returns False whenever the text carries a term, so
    it precedes the fragment fallback as well as the status rule (re-adversary
    rows: a carve-out consulted only for int-status exceptions, or fragments
    that win for status-less ones, both redden here)."""
    exc = Exception(message + ": Invalid token")
    assert getattr(exc, "status", None) is None, "precondition: no status, so only the texts decide"
    client = [t for t in auth_service._EXPECTED_CLIENT_AUTH_ERROR_TERMS if t in str(exc).lower()]
    assert client == ["invalid token"], "precondition: exactly one expected-client fragment: " + repr(client)
    result = categorize(caplog, exc, "password_recovery")
    assert_one_type_only_error(caplog, "password_recovery", exc, term + " status-less + invalid token")
    assert auth_service._is_expected_client_auth_error(exc) is False
    assert result == GENERIC, repr(result)


def test_a_plain_expected_client_4xx_is_still_a_warning(caplog):
    for exc in (api_error(REFRESH_NOT_FOUND, 400, "refresh_token_not_found"),
                api_error(BAD_JWT_EXPIRED, 401, "bad_jwt")):
        result = categorize(caplog, exc, "refresh")
        assert [(r.levelname, r.getMessage()) for r in module_records(caplog)] == [
            ("WARNING", "[auth] refresh rejected upstream: " + API_ERROR_TYPE
             + " status=" + str(exc.status))
        ], repr(describe(module_records(caplog)))
        assert error_records(caplog) == [], repr(describe(error_records(caplog)))
        assert result == GENERIC, repr(result)


# ===========================================================================
# T14 (fix round 2, ruling R12) -- both lines PRE-FORMATTED, no record args,
# so Sentry's logentry.message differs per (context, type)
# ===========================================================================
def test_both_log_lines_are_preformatted_with_no_record_args(caplog):
    cases = [
        (api_error(REFRESH_NOT_FOUND, 400, "refresh_token_not_found"), "refresh", logging.WARNING,
         "[auth] refresh rejected upstream: " + API_ERROR_TYPE + " status=400"),
        (Exception(REFRESH_ALREADY_USED), "password_recovery", logging.WARNING,
         "[auth] password_recovery rejected upstream: Exception status=None"),
        (RuntimeError("boom"), "update_profile", logging.ERROR, "Auth error in update_profile: RuntimeError"),
    ]
    for exc, context, level, message in cases:
        categorize(caplog, exc, context)
        records = module_records(caplog)
        assert len(records) == 1 and records[0].levelno == level, repr(describe(records))
        record = records[0]
        assert not record.args, "a record must carry NO args (R12): " + repr(record.args)
        assert record.msg == record.getMessage() == message, (record.msg, record.getMessage())


def test_each_context_and_type_pair_logs_its_own_message(caplog):
    """What Sentry groups on: with no args, logentry.message IS record.msg, so
    distinct (context, type) pairs must produce distinct record.msg values."""
    seen = {}
    for context in CONTEXTS:
        for exc in (RuntimeError("x"), KeyError("y")):
            categorize(caplog, exc, context)
            errors = [r for r in module_records(caplog) if r.levelno == logging.ERROR]
            assert len(errors) == 1, repr(describe(module_records(caplog)))
            seen[(context, type(exc).__name__)] = errors[0].msg
    assert len(set(seen.values())) == len(seen) == 2 * len(CONTEXTS), repr(seen)
