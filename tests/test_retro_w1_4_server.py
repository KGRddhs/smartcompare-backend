"""R-AUTH retro-fix, unit W1-4 server (refresh 503 + logout revocation) -- RED phase.

Spec: the retroactive adversary report for ``W1-4 server`` (PR #139) plus the
server-side defect in the ``W1-4 client half`` report (PR #140), under the
orchestrator's binding rulings:

* **W1-4b -- UNFLAGGED.** ``/auth/refresh`` must classify a refresh failure by
  its TYPE, not by a substring of ``str(e)``. The transient/upstream class is
  ``supabase_auth.errors.AuthRetryableError``, every ``httpx.TransportError``
  (timeouts, connect/read errors, a dropped connection) and the upstream 5xx /
  429 shapes gotrue really produces. Everything else stays 401. The existing
  substring branch may stay as a fallback (node 1 of
  ``tests/test_auth_refresh_and_revocation.py`` still pins it).
* **W1-4c -- UNFLAGGED.** A server-side Supabase client never auto-refreshes:
  ``ClientOptions(auto_refresh_token=False, persist_session=False)`` on BOTH
  branches of ``get_auth_client``, so no SDK ``Timer`` thread is ever started
  and the server never spends a refresh token it has already handed to a
  device.
* **W1-4 server minor -- stays under ``ENABLE_LOGOUT_UPSTREAM_REVOCATION``.**
  With the flag ON, logout revokes upstream by the ACCESS token
  (``admin.sign_out(access_token, "local")``) whether or not the body carried
  a refresh token -- the refresh-token VALUE never reached Supabase on the
  valid-token path anyway.

HOW THE DEFECTS ARE MEASURED -- the reviewer's probe, re-run
------------------------------------------------------------
Every W1-4b / W1-4c / logout node drives the REAL pinned SDK
(supabase / supabase_auth 2.31.0, httpx 0.28.1) through the REAL
``auth_service`` functions and, where the route is the contract, through the
REAL ``POST /api/v1/auth/refresh`` / ``POST /api/v1/auth/logout`` in the ASGI
app. The only thing faked is gotrue itself: ``_FakeGoTrue`` is a
``ThreadingHTTPServer`` on 127.0.0.1 that answers ``/auth/v1/token``,
``/auth/v1/user`` and ``/auth/v1/logout`` with whatever shape a node asks for
(a status + JSON/text body, a dropped socket, a hang past the SDK timeout).
``auth_service.SUPABASE_URL`` is pointed at it, so the SDK builds its real
exception objects from real HTTP. Nodes that need a shape a loopback server
cannot produce (a Linux name-resolution failure, a TLS EOF) raise a real
``httpx`` exception object from a stub ``client.auth.refresh_session`` -- i.e.
the exception the SDK would let escape unwrapped, because
``gotrue_base_api._request`` only catches ``HTTPStatusError`` and
``RuntimeError``.

Measured on this tree (origin/main 1c6f6796, pinned venv): see the per-node
docstrings. Summary: the table's RED rows are 401 today and must be 503 after;
the PIN rows pass today and must still pass after.

SDK TRAP FOR THE GREEN PHASE (measured, recorded here so nobody trips on it)
---------------------------------------------------------------------------
``supabase.lib.client_options.SyncClientOptions.replace(auto_refresh_token=False)``
CANNOT turn auto-refresh off: its body is
``auto_refresh_token or self.auto_refresh_token``, so ``False`` falls through to
the existing ``True``. The same is true of ``persist_session``. Build the
options with the constructor (``SyncClientOptions(httpx_client=...,
auto_refresh_token=False, persist_session=False)``) or set the attributes on
the fresh object; the W1-4c nodes below measure the Timer, not the kwarg, so a
``.replace(...)`` implementation stays red.

ZERO NETWORK: an autouse guard blocks every non-loopback ``connect`` and every
non-loopback ``getaddrinfo`` and FAILS the node on any attempt.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import itertools
import json
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import auth_routes
from app.api.auth_routes import get_current_user
from app.main import app
from app.services import auth_service, cache_service, database_service

REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
LOGOUT_FLAG = "ENABLE_LOGOUT_UPSTREAM_REVOCATION"
REUSE_FLAG = "ENABLE_SUPABASE_CLIENT_REUSE"

UPSTREAM_CODE = "REFRESH_UPSTREAM_UNAVAILABLE"
AUTH_REQUIRED = "AUTH_REQUIRED"
API_VERSION_HEADER = {"X-Supabase-Api-Version": "2024-01-01"}

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}


# ===========================================================================
# autouse: zero network
# ===========================================================================
@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback connect / getaddrinfo; fail the node on any
    attempt (recorded, then asserted at teardown, because an SDK or a thread
    may swallow the OSError we raise)."""
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


# ===========================================================================
# SDK auto-refresh Timer bookkeeping
# ===========================================================================
def _is_supabase_timer(thread: threading.Thread) -> bool:
    fn = getattr(thread, "function", None)
    return isinstance(thread, threading.Timer) and (
        getattr(fn, "__module__", "") or ""
    ).startswith("supabase_auth")


def _live_supabase_timers() -> List[threading.Thread]:
    return [t for t in threading.enumerate() if _is_supabase_timer(t) and t.is_alive()]


@pytest.fixture(autouse=True)
def _cancel_leaked_sdk_timers():
    """Today's code LEAKS SDK auto-refresh timers (that is W1-4c). Cancel every
    one this node left behind so none fires later against a dead port."""
    before = set(_live_supabase_timers())
    yield
    for t in _live_supabase_timers():
        if t not in before:
            t.cancel()


# ===========================================================================
# the fake gotrue
# ===========================================================================
_USER_ID = "00000000-0000-4000-8000-000000000001"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_jwt(exp_offset_seconds: int = 3600, sub: str = _USER_ID, tag: str = "") -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": sub,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + exp_offset_seconds,
        "session_id": "sess-" + (tag or "x"),
    }
    return ".".join([
        _b64url(json.dumps(header).encode()),
        _b64url(json.dumps(payload).encode()),
        _b64url(("sig-" + tag).encode()),
    ])


def _user_json(user_id: str = _USER_ID) -> Dict[str, Any]:
    return {
        "id": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": "retro-w14@example.invalid",
        "app_metadata": {"provider": "email"},
        "user_metadata": {},
        "created_at": "2026-01-01T00:00:00Z",
    }


class _FakeGoTrue:
    """A loopback gotrue. ``behaviour[route]`` is one of:

    * ``("ok",)``                     -- 200 with a fresh session / user / 204 logout
    * ``("json", status, body, extra_headers)``
    * ``("text", status, text, content_type)``
    * ``("close",)``                  -- drop the socket without a response
    * ``("sleep", seconds)``          -- hang, then drop
    """

    def __init__(self, expires_in: int = 3600) -> None:
        self.requests: List[Dict[str, Any]] = []
        self.expires_in = expires_in
        self.behaviour: Dict[str, tuple] = {
            "refresh": ("ok",),
            "password": ("ok",),
            "user": ("ok",),
            "logout": ("ok",),
        }
        self._rt_counter = itertools.count(1)
        self._lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_a, **_k):  # silence stderr
                return

            def _record(self) -> Dict[str, Any]:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw.decode() or "null")
                except ValueError:
                    body = raw.decode(errors="replace")
                entry = {
                    "method": self.command,
                    "path": parts.path,
                    "query": {k: v[0] for k, v in parse_qs(parts.query).items()},
                    "authorization": self.headers.get("Authorization"),
                    "body": body,
                    "t": time.time(),
                }
                with fake._lock:
                    fake.requests.append(entry)
                return entry

            def _send(self, status: int, payload: Optional[bytes], ctype: str, extra: Optional[dict] = None):
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload or b"")))
                self.end_headers()
                if payload:
                    self.wfile.write(payload)

            def _dispatch(self, route: str, ok_payload):
                spec = fake.behaviour.get(route, ("ok",))
                kind = spec[0]
                if kind == "ok":
                    status, payload = ok_payload()
                    if payload is None:
                        self._send(status, None, "application/json")
                    else:
                        self._send(status, json.dumps(payload).encode(), "application/json")
                elif kind == "json":
                    _k, status, body, extra = spec
                    self._send(status, json.dumps(body).encode(), "application/json", extra)
                elif kind == "text":
                    _k, status, text, ctype = spec
                    self._send(status, text.encode(), ctype)
                elif kind == "close":
                    self.close_connection = True
                elif kind == "sleep":
                    time.sleep(spec[1])
                    self.close_connection = True
                else:  # pragma: no cover - test bug
                    raise AssertionError("unknown fake behaviour " + repr(spec))

            def do_POST(self):  # noqa: N802
                entry = self._record()
                path, query = entry["path"], entry["query"]
                if path == "/auth/v1/token" and query.get("grant_type") == "refresh_token":
                    self._dispatch("refresh", lambda: (200, fake._session_json()))
                elif path == "/auth/v1/token" and query.get("grant_type") == "password":
                    self._dispatch("password", lambda: (200, fake._session_json()))
                elif path == "/auth/v1/logout":
                    self._dispatch("logout", lambda: (204, None))
                else:
                    self._send(404, b'{"message":"not found"}', "application/json")

            def do_GET(self):  # noqa: N802
                entry = self._record()
                if entry["path"] == "/auth/v1/user":
                    self._dispatch("user", lambda: (200, _user_json()))
                else:
                    self._send(404, b'{"message":"not found"}', "application/json")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return "http://127.0.0.1:" + str(self.server.server_address[1])

    def _session_json(self) -> Dict[str, Any]:
        n = next(self._rt_counter)
        now = int(time.time())
        return {
            "access_token": make_jwt(self.expires_in, tag="at" + str(n)),
            "token_type": "bearer",
            "expires_in": self.expires_in,
            "expires_at": now + self.expires_in,
            "refresh_token": "RT-ISSUED-" + str(n),
            "user": _user_json(),
        }

    def calls(self, path: str, **query) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                r for r in self.requests
                if r["path"] == path and all(r["query"].get(k) == v for k, v in query.items())
            ]

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def gotrue(monkeypatch):
    fake = _FakeGoTrue()
    monkeypatch.setattr(auth_service, "SUPABASE_URL", fake.url)
    monkeypatch.setattr(auth_service, "SUPABASE_ANON_KEY", "retro-w14-anon-key")

    def _no_admin():
        raise RuntimeError("admin client disabled in retro W1-4 tests")

    # refresh_session / login_user read preferences through the SERVICE-ROLE
    # client inside their own try; a raise here keeps every node on the fake.
    monkeypatch.setattr(auth_service, "get_admin_client", _no_admin)
    yield fake
    fake.close()


@pytest.fixture(params=["reuse_off", "reuse_on"])
def reuse_branch(request, monkeypatch):
    """BOTH branches of ``get_auth_client`` (W1-4c ruling)."""
    if request.param == "reuse_on":
        monkeypatch.setenv(REUSE_FLAG, "true")
    else:
        monkeypatch.delenv(REUSE_FLAG, raising=False)
    database_service._reset_client_cache_for_tests()
    auth_service._reset_client_cache_for_tests()
    yield request.param
    database_service._reset_client_cache_for_tests()
    auth_service._reset_client_cache_for_tests()


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    monkeypatch.delenv(LOGOUT_FLAG, raising=False)
    monkeypatch.delenv(REUSE_FLAG, raising=False)
    yield


class _BlacklistRedis:
    def __init__(self) -> None:
        self.setex_calls: List[tuple] = []

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))

    def get(self, key):
        return None


@pytest.fixture
def blacklist(monkeypatch):
    fake = _BlacklistRedis()
    monkeypatch.setattr(cache_service, "redis_client", fake)
    return fake


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _run(coro):
    return asyncio.run(coro)


# ===========================================================================
# W1-4b -- the transient table (RED today: 401, must be 503)
# ===========================================================================
# Real SDK shapes, produced by the fake gotrue answering POST /auth/v1/token.
# Each row: (id, behaviour, the exception the SDK raises today, today's status).
_RED_REAL_SHAPES = [
    ("429_json_rate_limit",
     ("json", 429, {"code": "over_request_rate_limit", "message": "Request rate limit reached"}, API_VERSION_HEADER)),
    ("429_html",
     ("text", 429, "<html><body>Too Many Requests</body></html>", "text/html")),
    ("500_json_unexpected_failure",
     ("json", 500, {"code": "unexpected_failure", "message": "Unexpected failure, please check server logs for more information"}, API_VERSION_HEADER)),
    ("500_html",
     ("text", 500, "<html><body>Internal Server Error</body></html>", "text/html")),
    ("502_bad_gateway",
     ("text", 502, "<html><body>502 Bad Gateway</body></html>", "text/html")),
    ("503_json",
     ("json", 503, {"message": "Service Unavailable"}, {})),
    ("503_envoy_text",
     ("text", 503, "upstream connect error or disconnect/reset before headers. reset reason: overflow", "text/plain")),
    ("520_cloudflare",
     ("text", 520, "<html><body>Web server is returning an unknown error</body></html>", "text/html")),
    ("522_cloudflare",
     ("text", 522, "<html><body>Connection timed out</body></html>", "text/html")),
    ("544_request_timed_out",
     ("json", 544, {"code": "request_timeout", "message": "Request timed out"}, API_VERSION_HEADER)),
    ("dropped_connection", ("close",)),
]


@pytest.mark.parametrize(
    "behaviour", [row[1] for row in _RED_REAL_SHAPES], ids=[row[0] for row in _RED_REAL_SHAPES]
)
def test_w1_4b_real_upstream_outage_shape_is_503_not_401(client, gotrue, behaviour):
    """W1-4b RED. A real Supabase outage shape, produced by the real pinned SDK
    against the fake gotrue, reaches the REAL ``/auth/refresh`` route.

    MEASURED TODAY (origin/main 1c6f6796): every row is **401 AUTH_REQUIRED**.
    The SDK already types 502/503/520/522 as ``AuthRetryableError``; 429/500/544
    arrive as ``AuthApiError`` with ``.status``; the HTML 429/500 bodies arrive
    as ``AuthUnknownError`` wrapping the ``httpx.HTTPStatusError``; the dropped
    socket escapes ``_request`` unwrapped as ``httpx.RemoteProtocolError``. The
    substring classifier sees none of them, and on BOTH client builds a 401 from
    /auth/refresh is a forced logout.
    """
    gotrue.behaviour["refresh"] = behaviour
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-DEVICE-B-TABLE"})
    body = resp.json()
    assert gotrue.calls("/auth/v1/token", grant_type="refresh_token"), (
        "the fake gotrue was never reached -- the node measured nothing"
    )
    assert resp.status_code == 503 and body.get("code") == UPSTREAM_CODE, (
        "a transient upstream shape must be 503 " + UPSTREAM_CODE
        + " (the device keeps its session); got " + str(resp.status_code) + " " + resp.text
    )


def test_w1_4b_real_hang_past_sdk_timeout_is_503_not_401(client, gotrue):
    """W1-4b RED. A REAL hang: the fake holds the socket past the SDK's own
    httpx timeout (5.0 s default on the flag-OFF branch). The SDK raises
    ``httpx.ReadTimeout('timed out')`` -- and ``'timed out'`` does not contain
    the substring ``'timeout'``, so today this is **401**. (~5 s node.)
    """
    gotrue.behaviour["refresh"] = ("sleep", 7.0)
    t0 = time.monotonic()
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-DEVICE-B-HANG"})
    elapsed = time.monotonic() - t0
    assert elapsed < 7.0, "the SDK timeout did not fire before the fake gave up; elapsed %.2f s" % elapsed
    assert resp.status_code == 503 and resp.json().get("code") == UPSTREAM_CODE, (
        "an SDK timeout is transient; got " + str(resp.status_code) + " " + resp.text
    )


def _synthetic_transient_exceptions():
    from supabase_auth.errors import AuthApiError, AuthRetryableError

    return [
        ("httpx_ReadTimeout_linux", httpx.ReadTimeout("The read operation timed out")),
        ("httpx_ConnectTimeout_tls_handshake", httpx.ConnectTimeout("_ssl.c:989: The handshake operation timed out")),
        ("httpx_PoolTimeout", httpx.PoolTimeout("timed out")),
        ("httpx_WriteTimeout", httpx.WriteTimeout("timed out")),
        ("httpx_ConnectError_eai_again", httpx.ConnectError("[Errno -3] Temporary failure in name resolution")),
        ("httpx_ConnectError_eai_noname", httpx.ConnectError("[Errno -2] Name or service not known")),
        ("httpx_ReadError_ssl_eof", httpx.ReadError("EOF occurred in violation of protocol (_ssl.c:2427)")),
        ("httpx_RemoteProtocolError", httpx.RemoteProtocolError("Server disconnected without sending a response.")),
        ("AuthRetryableError_503", AuthRetryableError("Service Unavailable", 503)),
        ("AuthRetryableError_502", AuthRetryableError("Bad Gateway", 502)),
        ("AuthRetryableError_transport_0", AuthRetryableError("Event loop is closed", 0)),
        ("AuthApiError_429", AuthApiError("Request rate limit reached", 429, "over_request_rate_limit")),
        ("AuthApiError_500", AuthApiError("Unexpected failure", 500, "unexpected_failure")),
    ]


_SYNTH = _synthetic_transient_exceptions()


class _RaisingAuth:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.calls: List[str] = []

    def refresh_session(self, refresh_token=None):
        self.calls.append("refresh_session")
        raise self._exc


class _Client:
    def __init__(self, auth) -> None:
        self.auth = auth


@pytest.mark.parametrize("exc", [e for _i, e in _SYNTH], ids=[i for i, _e in _SYNTH])
def test_w1_4b_transient_exception_type_is_503_not_401(client, monkeypatch, exc):
    """W1-4b RED. Shapes a loopback fake cannot produce (Linux resolver and TLS
    messages) and the typed SDK classes themselves, raised from
    ``client.auth.refresh_session`` INSIDE ``auth_service.refresh_session`` so the
    real classifier runs. MEASURED TODAY: every row is **401**; the ruling makes
    the TYPE (``AuthRetryableError``, ``httpx.TransportError``,
    ``AuthApiError`` with status 429 or >= 500) the discriminator.
    """
    auth = _RaisingAuth(exc)
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: _Client(auth))
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-DEVICE-B-SYNTH"})
    assert auth.calls == ["refresh_session"], "the stub was not reached"
    assert resp.status_code == 503 and resp.json().get("code") == UPSTREAM_CODE, (
        type(exc).__name__ + "(" + str(exc) + ") is transient; got "
        + str(resp.status_code) + " " + resp.text
    )


# ===========================================================================
# W1-4b PINS -- shapes that are 503 today and must stay 503
# ===========================================================================
def test_w1_4b_pin_504_gateway_timeout_stays_503(client, gotrue):
    """PIN (green today): a real 504 from the fake -> AuthRetryableError whose
    message ('Gateway Timeout') happens to contain 'timeout'. Must stay 503."""
    gotrue.behaviour["refresh"] = ("text", 504, "<html>504 Gateway Time-out</html>", "text/html")
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-504"})
    assert resp.status_code == 503 and resp.json().get("code") == UPSTREAM_CODE, resp.text


def test_w1_4b_pin_connection_refused_stays_503(client, monkeypatch):
    """PIN (green today): SUPABASE_URL points at a closed loopback port ->
    httpx.ConnectError (message carries 'connection'/'refused'). Must stay 503."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    monkeypatch.setattr(auth_service, "SUPABASE_URL", "http://127.0.0.1:" + str(port))
    monkeypatch.setattr(auth_service, "SUPABASE_ANON_KEY", "retro-w14-anon-key")
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-REFUSED"})
    assert resp.status_code == 503 and resp.json().get("code") == UPSTREAM_CODE, resp.text


@pytest.mark.parametrize("exc", [
    httpx.ReadError("[Errno 104] Connection reset by peer"),
    httpx.ReadError("[WinError 10054] An existing connection was forcibly closed by the remote host"),
    ConnectionError("connection timeout"),
], ids=["reset_linux", "reset_windows", "substring_connection_timeout"])
def test_w1_4b_pin_substring_transients_stay_503(client, monkeypatch, exc):
    """PIN (green today): the shapes the substring branch already catches."""
    auth = _RaisingAuth(exc)
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: _Client(auth))
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-SUBSTR"})
    assert resp.status_code == 503 and resp.json().get("code") == UPSTREAM_CODE, resp.text


# ===========================================================================
# W1-4b PINS -- every NON-transient shape stays 401 (the anti-overreach half)
# ===========================================================================
_PIN_REAL_401 = [
    ("400_refresh_token_not_found",
     ("json", 400, {"code": "refresh_token_not_found", "message": "Invalid Refresh Token: Refresh Token Not Found"}, API_VERSION_HEADER)),
    ("400_refresh_token_already_used",
     ("json", 400, {"code": "refresh_token_already_used", "message": "Invalid Refresh Token: Already Used"}, API_VERSION_HEADER)),
    ("400_legacy_invalid_grant",
     ("json", 400, {"error": "invalid_grant", "error_description": "Invalid Refresh Token: Refresh Token Not Found"}, {})),
    ("401_bad_jwt",
     ("json", 401, {"code": "bad_jwt", "message": "invalid JWT"}, API_VERSION_HEADER)),
    ("403_forbidden",
     ("json", 403, {"code": "user_banned", "message": "User is banned"}, API_VERSION_HEADER)),
    ("404_session_not_found",
     ("json", 404, {"code": "session_not_found", "message": "Session from session_id claim in JWT does not exist"}, API_VERSION_HEADER)),
    ("422_validation_failed",
     ("json", 422, {"code": "validation_failed", "message": "refresh_token is required"}, API_VERSION_HEADER)),
    ("400_html_body",
     ("text", 400, "<html>Bad Request</html>", "text/html")),
]


@pytest.mark.parametrize(
    "behaviour", [row[1] for row in _PIN_REAL_401], ids=[row[0] for row in _PIN_REAL_401]
)
def test_w1_4b_pin_real_non_transient_shape_stays_401(client, gotrue, behaviour):
    """PIN (green today): a genuine token verdict from gotrue is 401 AUTH_REQUIRED
    today and must stay 401 -- the client MUST sign out on these."""
    gotrue.behaviour["refresh"] = behaviour
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-401"})
    assert gotrue.calls("/auth/v1/token", grant_type="refresh_token"), "fake never reached"
    assert resp.status_code == 401 and resp.json().get("code") == AUTH_REQUIRED, resp.text


def _synthetic_non_transient():
    from supabase_auth.errors import (
        AuthApiError,
        AuthInvalidJwtError,
        AuthSessionMissingError,
        AuthWeakPasswordError,
    )

    return [
        ("AuthApiError_400_not_found", AuthApiError("Invalid Refresh Token: Refresh Token Not Found", 400, "refresh_token_not_found")),
        ("AuthApiError_400_already_used", AuthApiError("Invalid Refresh Token: Already Used", 400, "refresh_token_already_used")),
        ("AuthApiError_401", AuthApiError("invalid JWT", 401, "bad_jwt")),
        ("AuthApiError_403", AuthApiError("User is banned", 403, "user_banned")),
        ("AuthApiError_404_session", AuthApiError("Session not found", 404, "session_not_found")),
        ("AuthSessionMissingError", AuthSessionMissingError()),
        ("AuthInvalidJwtError", AuthInvalidJwtError("Invalid JWT structure")),
        ("AuthWeakPasswordError_422", AuthWeakPasswordError("weak", 422, ["length"])),
        ("plain_Exception_invalid_token", Exception("Invalid Refresh Token: Refresh Token Not Found")),
        ("TypeError", TypeError("refresh_session() got an unexpected keyword argument")),
        ("KeyError", KeyError("session")),
    ]


_SYNTH_401 = _synthetic_non_transient()


@pytest.mark.parametrize("exc", [e for _i, e in _SYNTH_401], ids=[i for i, _e in _SYNTH_401])
def test_w1_4b_pin_non_transient_exception_stays_401(client, monkeypatch, exc):
    """PIN (green today): every non-transient class stays 401 AUTH_REQUIRED."""
    auth = _RaisingAuth(exc)
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: _Client(auth))
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-SYNTH-401"})
    assert resp.status_code == 401 and resp.json().get("code") == AUTH_REQUIRED, (
        type(exc).__name__ + " must stay 401; got " + str(resp.status_code) + " " + resp.text
    )


def test_w1_4b_pin_missing_config_and_no_session_stay_401(client, monkeypatch, gotrue):
    """PIN (green today): (a) get_auth_client's own ValueError for missing
    SUPABASE_URL/ANON_KEY and (b) a 200 with no session stay 401."""
    monkeypatch.setattr(auth_service, "SUPABASE_URL", None)
    resp_a = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-NOCONF"})
    assert resp_a.status_code == 401 and resp_a.json().get("code") == AUTH_REQUIRED, resp_a.text

    class _NoSession:
        session = None
        user = None

    class _Auth:
        def refresh_session(self, refresh_token=None):
            return _NoSession()

    monkeypatch.setattr(auth_service, "get_auth_client", lambda: _Client(_Auth()))
    resp_b = client.post(REFRESH_URL, json={"refresh_token": "RT-PIN-NOSESSION"})
    assert resp_b.status_code == 401 and resp_b.json().get("code") == AUTH_REQUIRED, resp_b.text


def test_w1_4b_pin_refresh_success_shape_unchanged(client, gotrue):
    """PIN (green today): a successful refresh through the real SDK returns the
    rotated pair the fake issued, in today's shape."""
    resp = client.post(REFRESH_URL, json={"refresh_token": "RT-DEVICE-OK"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["session"]["refresh_token"] == "RT-ISSUED-1"
    assert body["session"]["access_token"].count(".") == 2
    assert body["user"] == {"id": _USER_ID, "email": "retro-w14@example.invalid", "preferences_completed": False}
    posted = gotrue.calls("/auth/v1/token", grant_type="refresh_token")
    assert posted and posted[0]["body"] == {"refresh_token": "RT-DEVICE-OK"}


# ===========================================================================
# W1-4b PINS -- every OTHER caller of the categoriser is byte-identical
# ===========================================================================
_OTHER_CALLER_TABLE = [
    # (id, exception factory, login/register/password_reset result, social_login result)
    ("AuthRetryableError_503",
     lambda: __import__("supabase_auth.errors", fromlist=["x"]).AuthRetryableError("Service Unavailable", 503),
     {"success": False, "error": "Something went wrong. Please try again later."},
     {"success": False, "error": "[B4-BE-DIAG] supabase_error=Service Unavailable exc_type=AuthRetryableError"}),
    ("httpx_ReadTimeout",
     lambda: httpx.ReadTimeout("The read operation timed out"),
     {"success": False, "error": "Something went wrong. Please try again later."},
     {"success": False, "error": "[B4-BE-DIAG] supabase_error=The read operation timed out exc_type=ReadTimeout"}),
    ("AuthApiError_429",
     lambda: __import__("supabase_auth.errors", fromlist=["x"]).AuthApiError("Request rate limit reached", 429, "over_request_rate_limit"),
     {"success": False, "error": "Something went wrong. Please try again later."},
     {"success": False, "error": "[B4-BE-DIAG] supabase_error=Request rate limit reached exc_type=AuthApiError"}),
    ("substring_connection",
     lambda: ConnectionError("connection timeout"),
     {"success": False, "error": "Connection failed. Please try again.", "code": "UPSTREAM_UNAVAILABLE"},
     {"success": False, "error": "Connection failed. Please try again.", "code": "UPSTREAM_UNAVAILABLE"}),
    ("invalid_credentials",
     lambda: __import__("supabase_auth.errors", fromlist=["x"]).AuthApiError("Invalid login credentials", 400, "invalid_credentials"),
     {"success": False, "error": "Invalid email or password"},
     {"success": False, "error": "Invalid email or password"}),
]


class _AllRaisingAuth:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def __getattr__(self, name):
        def _raise(*_a, **_k):
            raise self._exc
        return _raise


@pytest.mark.parametrize(
    "factory,expected,expected_social",
    [(r[1], r[2], r[3]) for r in _OTHER_CALLER_TABLE],
    ids=[r[0] for r in _OTHER_CALLER_TABLE],
)
def test_w1_4b_pin_other_callers_keep_todays_result(monkeypatch, factory, expected, expected_social):
    """PIN (green today): the ruling is scoped to the REFRESH path. login,
    register, password reset and social login keep today's exact dicts for the
    very shapes the refresh path starts treating as transient."""
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: _Client(_AllRaisingAuth(factory())))
    assert _run(auth_service.login_user("a@example.invalid", "pw")) == expected
    assert _run(auth_service.register_user("a@example.invalid", "pw")) == expected
    assert _run(auth_service.request_password_reset("a@example.invalid")) == expected
    assert _run(auth_service.sign_in_with_social("google", "h.p.s", None)) == expected_social


# ===========================================================================
# W1-4c -- server-side clients never auto-refresh (RED today)
# ===========================================================================
def test_w1_4c_refresh_starts_no_sdk_auto_refresh_timer(gotrue, reuse_branch):
    """W1-4c RED, both ``get_auth_client`` branches. MEASURED TODAY: one
    ``auth_service.refresh_session`` leaves ONE live daemon
    ``threading.Timer`` (``SyncGoTrueClient._start_auto_refresh_token.<locals>
    .refresh_token_function``) armed for ``expires_in - 10`` s on a throw-away
    client -- when it fires it spends the refresh token just handed to the
    device, then re-arms forever."""
    before = set(_live_supabase_timers())
    result = _run(auth_service.refresh_session("RT-DEVICE-C-1"))
    assert result.get("success") is True, result
    leaked = [t for t in _live_supabase_timers() if t not in before]
    assert not leaked, (
        "refresh_session left " + str(len(leaked)) + " SDK auto-refresh Timer(s) alive ["
        + reuse_branch + "]: " + repr([(t.name, getattr(t, "interval", None)) for t in leaked])
    )


def test_w1_4c_login_starts_no_sdk_auto_refresh_timer(gotrue, reuse_branch):
    """W1-4c RED, both branches. Same leak on ``sign_in_with_password``:
    ``login_user`` hands the session to the device and the server keeps a Timer
    that will spend that device's refresh token."""
    before = set(_live_supabase_timers())
    result = _run(auth_service.login_user("retro-w14@example.invalid", "Correct-Horse-9"))
    assert result.get("success") is True, result
    leaked = [t for t in _live_supabase_timers() if t not in before]
    assert not leaked, (
        "login_user left " + str(len(leaked)) + " SDK auto-refresh Timer(s) alive [" + reuse_branch + "]"
    )


def test_w1_4c_server_never_spends_the_token_it_handed_to_the_device(gotrue):
    """W1-4c RED, behavioural (the reviewer's probe, shortened). The fake issues
    sessions with ``expires_in=12``. The SDK computes ``expire_in`` from
    ``round(time.time())`` against the fake's ``int(time.time())``, so it lands
    on 11 or 12 and the timer is armed at 1-2 s (an ``expires_in`` of 11 is
    FLAKY: it can land on 10, which the SDK treats as "margin 0.5" and arms at
    9.5 s -- measured). After ONE ``refresh_session`` the server must make
    exactly ONE POST /token, and must NEVER present the refresh token it
    returned to the device.

    MEASURED TODAY: a second POST /token arrives within ~2 s with no request in
    flight, presenting the device's token. The node polls up to 4 s (returns as
    soon as the leak shows).
    """
    gotrue.expires_in = 12
    result = _run(auth_service.refresh_session("RT-DEVICE-C-OLD"))
    assert result.get("success") is True, result
    device_token = result["session"]["refresh_token"]
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if len(gotrue.calls("/auth/v1/token", grant_type="refresh_token")) > 1:
            break
        time.sleep(0.1)
    posted = gotrue.calls("/auth/v1/token", grant_type="refresh_token")
    presented = [p["body"].get("refresh_token") for p in posted if isinstance(p["body"], dict)]
    assert device_token not in presented, (
        "the SERVER spent the refresh token it had just returned to the device ("
        + device_token + "); tokens presented upstream: " + repr(presented)
    )
    assert presented == ["RT-DEVICE-C-OLD"], (
        "exactly one upstream refresh (the caller's) was expected; got " + repr(presented)
    )


def test_w1_4c_failed_logout_leg_leaves_no_timer(client, gotrue, blacklist, monkeypatch):
    """W1-4c RED (flag ON). The fake drops the socket on POST /auth/v1/logout.
    MEASURED TODAY: ``set_session`` arms an SDK Timer, ``admin.sign_out`` raises
    ``httpx.RemoteProtocolError`` (not ``AuthApiError``, so ``sign_out``'s own
    ``suppress`` does not catch it) before ``_remove_session`` runs, and the
    Timer survives -- the server keeps refreshing the session the user just
    logged out of while the route reports success."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    gotrue.behaviour["logout"] = ("close",)
    access = make_jwt(3600, tag="logout-fail")
    app.dependency_overrides[get_current_user] = lambda: {"id": _USER_ID, "email": "x@example.invalid", "access_token": access}
    before = set(_live_supabase_timers())
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-DEVICE-LOGOUT-FAIL"},
                       headers={"Authorization": "Bearer " + access})
    assert resp.status_code == 200 and resp.json() == {"success": True, "message": "Logged out successfully"}
    assert gotrue.calls("/auth/v1/logout"), "the upstream logout leg was never attempted"
    leaked = [t for t in _live_supabase_timers() if t not in before]
    assert not leaked, (
        "a failed upstream logout leg left " + str(len(leaked)) + " SDK auto-refresh Timer(s) alive"
    )


def test_w1_4c_pin_get_auth_client_still_fresh_per_call(gotrue, reuse_branch):
    """PIN (green today): the anon client is never memoised on either branch
    (Fable ruling 2026-09-07) -- W1-4c must not turn it into a shared object."""
    a = auth_service.get_auth_client()
    b = auth_service.get_auth_client()
    assert a is not b and a.auth is not b.auth


# ===========================================================================
# W1-4 server minor -- flag ON revokes by the ACCESS token (RED today)
# ===========================================================================
def _override_user(access: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": _USER_ID, "email": "retro-w14@example.invalid", "access_token": access,
    }


@pytest.mark.parametrize("body_kind", ["no_body", "empty_object", "null_refresh_token"])
def test_w1_4_minor_flag_on_revokes_upstream_without_refresh_token(client, gotrue, blacklist, monkeypatch, body_kind):
    """RED (flag ON). Every installed build logs out WITHOUT a refresh token in
    the body. The ruling: revoke by the access token regardless --
    POST /auth/v1/logout?scope=local with ``Authorization: Bearer <access>``.
    MEASURED TODAY: zero upstream requests (bare ``sign_out()`` on an empty
    client is a no-op)."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    access = make_jwt(3600, tag="minor-" + body_kind)
    _override_user(access)
    headers = {"Authorization": "Bearer " + access}
    if body_kind == "no_body":
        resp = client.post(LOGOUT_URL, headers=headers)
    elif body_kind == "empty_object":
        resp = client.post(LOGOUT_URL, json={}, headers=headers)
    else:
        resp = client.post(LOGOUT_URL, json={"refresh_token": None}, headers=headers)
    assert resp.status_code == 200 and resp.json() == {"success": True, "message": "Logged out successfully"}
    logouts = gotrue.calls("/auth/v1/logout")
    assert [(r["query"].get("scope"), r["authorization"]) for r in logouts] == [("local", "Bearer " + access)], (
        "flag ON must revoke the caller's session upstream by its access token (scope=local); "
        "upstream traffic was " + repr([(r["method"], r["path"], r["query"]) for r in gotrue.requests])
    )
    key = "revoked:" + hashlib.sha256(access.encode()).hexdigest()
    assert (key, 3600, "1") in blacklist.setex_calls, "the 1 h Redis blacklist write must survive"


def test_w1_4_minor_pin_flag_on_with_refresh_token_revokes_local(client, gotrue, blacklist, monkeypatch):
    """PIN (green today): flag ON with a refresh token in the body revokes the
    session upstream with scope=local by the access token -- exactly one
    logout call, never scope=global. The refresh-token VALUE is not what
    revokes (measured: it is never sent to /logout)."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    access = make_jwt(3600, tag="pin-rt")
    _override_user(access)
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-SENTINEL-111"},
                       headers={"Authorization": "Bearer " + access})
    assert resp.status_code == 200 and resp.json() == {"success": True, "message": "Logged out successfully"}
    logouts = gotrue.calls("/auth/v1/logout")
    assert [(r["query"].get("scope"), r["authorization"]) for r in logouts] == [("local", "Bearer " + access)]
    assert all("RT-SENTINEL-111" not in json.dumps(r["body"]) for r in logouts)


@pytest.mark.parametrize("body", [None, {}, {"refresh_token": "RT-FLAG-OFF"}], ids=["no_body", "empty", "with_rt"])
def test_w1_4_minor_pin_flag_off_makes_zero_upstream_calls(client, gotrue, blacklist, body):
    """PIN (green today): flag OFF is byte-identical -- no upstream request at
    all, today's body, the 1 h blacklist write."""
    access = make_jwt(3600, tag="off")
    _override_user(access)
    headers = {"Authorization": "Bearer " + access}
    resp = client.post(LOGOUT_URL, headers=headers) if body is None else client.post(LOGOUT_URL, json=body, headers=headers)
    assert resp.status_code == 200 and resp.json() == {"success": True, "message": "Logged out successfully"}
    assert gotrue.requests == [], "flag OFF must make zero upstream calls; got " + repr(gotrue.requests)
    key = "revoked:" + hashlib.sha256(access.encode()).hexdigest()
    assert (key, 3600, "1") in blacklist.setex_calls


def test_w1_4_minor_pin_flag_on_upstream_500_still_reports_success(client, gotrue, blacklist, monkeypatch):
    """PIN (green today): a failed upstream leg never changes the response."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    gotrue.behaviour["logout"] = ("json", 500, {"message": "boom"}, {})
    access = make_jwt(3600, tag="up500")
    _override_user(access)
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-UP500"}, headers={"Authorization": "Bearer " + access})
    assert resp.status_code == 200 and resp.json() == {"success": True, "message": "Logged out successfully"}


# ===========================================================================
# W1-4 server scrub pins (report defect 4: tests-only; green today)
# ===========================================================================
def test_w1_4_pin_route_backstop_logs_type_only(client, monkeypatch, caplog):
    """PIN (green today) -- kills the reviewer's mutation M7 (raw ``e`` in the
    route backstop): the backstop must log the exception TYPE, never its text,
    because ``UserDoesntExist(access_token)``'s ``str()`` is the bearer."""
    from supabase_auth.errors import UserDoesntExist

    secret = "eyJhbGciOi.RETROBACKSTOPSECRET.sig"

    async def _boom(_access, _refresh=None):
        raise UserDoesntExist(secret)

    monkeypatch.setattr(auth_routes, "logout_user", _boom)
    _override_user(secret)
    with caplog.at_level(logging.DEBUG):
        resp = client.post(LOGOUT_URL, headers={"Authorization": "Bearer " + secret})
    assert resp.status_code == 200
    emitted = "\n".join(r.getMessage() for r in caplog.records)
    assert secret not in emitted and "RETROBACKSTOPSECRET" not in emitted, emitted[:400]
    assert "UserDoesntExist" in emitted


def test_w1_4_pin_logout_user_scrubs_both_tokens(monkeypatch, caplog):
    """PIN (green today) -- kills mutation M9 (refresh-token redaction dropped).
    Every upstream entry point on the stub raises a message carrying BOTH
    tokens, so the pin holds whichever SDK call the flag-ON path makes
    (``set_session``, ``sign_out`` or ``admin.sign_out``)."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    access = "eyJhbGciOi.RETROSCRUBACCESS.sig"
    refresh = "RETROSCRUBREFRESH"
    exc = Exception("bad " + refresh + " for " + access)

    class _Admin:
        def sign_out(self, *_a, **_k):
            raise exc

    class _Auth(_AllRaisingAuth):
        admin = _Admin()

    monkeypatch.setattr(auth_service, "get_auth_client", lambda: _Client(_Auth(exc)))
    monkeypatch.setattr(auth_service, "_revoke_token", lambda _t: None)
    with caplog.at_level(logging.DEBUG, logger="app.services.auth_service"):
        result = _run(auth_service.logout_user(access, refresh))
    assert result == {"success": True, "message": "Logged out successfully"}
    emitted = "\n".join(r.getMessage() for r in caplog.records)
    assert access not in emitted and refresh not in emitted, emitted[:400]
    assert "<refresh_token>" in emitted and "<access_token>" in emitted, emitted[:400]
