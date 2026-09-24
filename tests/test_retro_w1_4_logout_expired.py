"""R-AUTH retro-fix, W1-4 -- the EXPIRED-bearer logout path (GREEN-phase pins).

Spec: the W1-4 CLIENT-half adversary report's server alternative ("let
/auth/logout accept a presented but expired Bearer when the flag is on and a
refresh_token is in the body"), bound by the Fable red-gate ruling 2 for group
R-AUTH:

* flag ``ENABLE_LOGOUT_UPSTREAM_REVOCATION`` ON + an EXPIRED Bearer JWT + a
  ``refresh_token`` in the JSON body -> the route ACCEPTS the request (today:
  401 from ``get_current_user`` before ``logout_user`` runs), blacklists the
  presented access token as today, then ``set_session(access, refresh)`` (the
  SDK's expired branch rotates the pair upstream: POST /token) and
  ``sign_out({"scope": "local"})`` (POST /logout?scope=local on the NEW
  session) -- all OFF the event-loop thread;
* a pair gotrue rejects still returns 200 and logs ONE warning carrying the
  exception TYPE only;
* an expired Bearer with NO refresh token keeps today's 401, and flag OFF keeps
  today's exact 401 for an expired Bearer;
* no token value appears in any log line.

Every node drives the REAL route and the REAL pinned SDK (supabase /
supabase_auth 2.31.0) against the loopback fake gotrue from
``tests/test_retro_w1_4_server.py``; gotrue's ``GET /user`` answers the expired
JWT with its real 401 ``bad_jwt`` shape, so ``verify_token`` rejects it exactly
as production would.

ZERO NETWORK: an autouse guard blocks every non-loopback ``connect`` and
``getaddrinfo`` and fails the node on any attempt.
"""
from __future__ import annotations

import hashlib
import logging
import socket
import threading
from typing import Any, List

import pytest
from fastapi.testclient import TestClient

from app.api import auth_routes
from app.main import app
from app.services import auth_service, cache_service, database_service
from tests.test_retro_w1_4_server import (
    API_VERSION_HEADER,
    _FakeGoTrue,
    _live_supabase_timers,
    make_jwt,
)

LOGOUT_URL = "/api/v1/auth/logout"
LOGOUT_FLAG = "ENABLE_LOGOUT_UPSTREAM_REVOCATION"
REUSE_FLAG = "ENABLE_SUPABASE_CLIENT_REUSE"
OK_BODY = {"success": True, "message": "Logged out successfully"}

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}

# gotrue's real answer to GET /user with an expired JWT.
_EXPIRED_JWT_USER_REPLY = (
    "json", 401,
    {"code": "bad_jwt", "message": "invalid JWT: unable to parse or verify signature, token has invalid claims: token is expired"},
    API_VERSION_HEADER,
)


# ===========================================================================
# autouse: zero network
# ===========================================================================
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


@pytest.fixture(autouse=True)
def _cancel_leaked_sdk_timers():
    before = set(_live_supabase_timers())
    yield
    for t in _live_supabase_timers():
        if t not in before:
            t.cancel()


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    monkeypatch.delenv(LOGOUT_FLAG, raising=False)
    monkeypatch.delenv(REUSE_FLAG, raising=False)
    yield


@pytest.fixture
def gotrue(monkeypatch):
    fake = _FakeGoTrue()
    fake.behaviour["user"] = _EXPIRED_JWT_USER_REPLY
    monkeypatch.setattr(auth_service, "SUPABASE_URL", fake.url)
    monkeypatch.setattr(auth_service, "SUPABASE_ANON_KEY", "retro-w14-expired-anon-key")

    def _no_admin():
        raise RuntimeError("admin client disabled in retro W1-4 expired-logout tests")

    monkeypatch.setattr(auth_service, "get_admin_client", _no_admin)
    yield fake
    fake.close()


@pytest.fixture(params=["reuse_off", "reuse_on"])
def reuse_branch(request, monkeypatch):
    if request.param == "reuse_on":
        monkeypatch.setenv(REUSE_FLAG, "true")
    else:
        monkeypatch.delenv(REUSE_FLAG, raising=False)
    database_service._reset_client_cache_for_tests()
    auth_service._reset_client_cache_for_tests()
    yield request.param
    database_service._reset_client_cache_for_tests()
    auth_service._reset_client_cache_for_tests()


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


def _posts(fake: _FakeGoTrue) -> List[tuple]:
    return [(r["path"], r["query"]) for r in fake.requests if r["method"] == "POST"]


def _blacklist_key(token: str) -> str:
    return "revoked:" + hashlib.sha256(token.encode()).hexdigest()


def _emitted(caplog) -> str:
    return "\n".join(r.getMessage() for r in caplog.records)


# ===========================================================================
# the ruling's red test 2: expired Bearer + refresh_token + flag ON
# ===========================================================================
def test_expired_bearer_with_refresh_token_rotates_then_signs_out_local(
    client, gotrue, blacklist, monkeypatch, caplog, reuse_branch
):
    """Flag ON, expired Bearer, refresh token in the body: 200, the presented
    access token is blacklisted, and the fake sees POST /token (the presented
    refresh token) THEN POST /logout?scope=local by the NEW access token. Both
    ``get_auth_client`` branches (W1-4c: the rotation still works with
    ``persist_session=False``); no SDK Timer survives; no token value in any
    log line."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    expired = make_jwt(-120, tag="exp-" + reuse_branch)
    refresh = "RT-DEVICE-EXPIRED-" + reuse_branch
    before = set(_live_supabase_timers())
    with caplog.at_level(logging.DEBUG):
        resp = client.post(LOGOUT_URL, json={"refresh_token": refresh},
                           headers={"Authorization": "Bearer " + expired})
    assert resp.status_code == 200 and resp.json() == OK_BODY, (resp.status_code, resp.text)

    assert _posts(gotrue) == [
        ("/auth/v1/token", {"grant_type": "refresh_token"}),
        ("/auth/v1/logout", {"scope": "local"}),
    ], "expected the rotation then a LOCAL sign-out; upstream POSTs were " + repr(_posts(gotrue))
    token_call = gotrue.calls("/auth/v1/token", grant_type="refresh_token")[0]
    assert token_call["body"] == {"refresh_token": refresh}
    logout_call = gotrue.calls("/auth/v1/logout")[0]
    assert logout_call["authorization"].startswith("Bearer ")
    new_access = logout_call["authorization"][len("Bearer "):]
    assert new_access != expired, "sign_out must end the ROTATED session, not the expired one"

    assert (_blacklist_key(expired), 3600, "1") in blacklist.setex_calls, (
        "the presented (expired) access token must be blacklisted as today"
    )
    leaked = [t for t in _live_supabase_timers() if t not in before]
    assert not leaked, "the expired-path logout left an SDK auto-refresh Timer alive"

    emitted = _emitted(caplog)
    for secret in (expired, refresh, new_access, "RT-ISSUED-1"):
        assert secret not in emitted, "a token value reached the logs: " + emitted[:400]


def test_expired_bearer_rejected_pair_still_200_one_type_only_warning(
    client, gotrue, blacklist, monkeypatch, caplog
):
    """A pair gotrue rejects (400 refresh_token_not_found on /token): still 200
    (the local blacklist is done), no /logout attempted, exactly ONE WARNING
    from the service carrying the exception TYPE and no token value."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    gotrue.behaviour["refresh"] = (
        "json", 400,
        {"code": "refresh_token_not_found", "message": "Invalid Refresh Token: Refresh Token Not Found"},
        API_VERSION_HEADER,
    )
    expired = make_jwt(-120, tag="exp-rejected")
    refresh = "RT-DEVICE-REJECTED-PAIR"
    with caplog.at_level(logging.DEBUG):
        resp = client.post(LOGOUT_URL, json={"refresh_token": refresh},
                           headers={"Authorization": "Bearer " + expired})
    assert resp.status_code == 200 and resp.json() == OK_BODY, resp.text
    assert _posts(gotrue) == [("/auth/v1/token", {"grant_type": "refresh_token"})], _posts(gotrue)
    assert (_blacklist_key(expired), 3600, "1") in blacklist.setex_calls

    # (verify_token's own pre-existing "Token verification failed" WARNING for
    # the expired JWT precedes this; it is today's line and carries no token.)
    warnings = [r for r in caplog.records
                if r.name == "app.services.auth_service" and r.levelno == logging.WARNING
                and "logout" in r.getMessage()]
    assert len(warnings) == 1, "exactly one logout WARNING; got " + repr([r.getMessage() for r in warnings])
    assert "AuthApiError" in warnings[0].getMessage(), warnings[0].getMessage()
    emitted = _emitted(caplog)
    assert expired not in emitted and refresh not in emitted, emitted[:400]
    assert "Refresh Token Not Found" not in warnings[0].getMessage(), (
        "the expired-path warning carries the exception TYPE only"
    )


def test_expired_path_upstream_leg_runs_off_the_event_loop(client, gotrue, blacklist, monkeypatch):
    """Thread-ident pin: the SDK's set_session / sign_out run in a worker
    thread, never on the thread that runs the route coroutine."""
    from supabase_auth import SyncGoTrueClient

    monkeypatch.setenv(LOGOUT_FLAG, "true")
    seen = {"loop": [], "set_session": [], "sign_out": []}
    real_set_session = SyncGoTrueClient.set_session
    real_sign_out = SyncGoTrueClient.sign_out
    real_logout_user = auth_routes.logout_user

    def _set_session(self, *a, **k):
        seen["set_session"].append(threading.get_ident())
        return real_set_session(self, *a, **k)

    def _sign_out(self, *a, **k):
        seen["sign_out"].append(threading.get_ident())
        return real_sign_out(self, *a, **k)

    async def _logout_user(*a, **k):
        seen["loop"].append(threading.get_ident())
        return await real_logout_user(*a, **k)

    monkeypatch.setattr(SyncGoTrueClient, "set_session", _set_session)
    monkeypatch.setattr(SyncGoTrueClient, "sign_out", _sign_out)
    monkeypatch.setattr(auth_routes, "logout_user", _logout_user)

    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-DEVICE-THREAD"},
                       headers={"Authorization": "Bearer " + make_jwt(-120, tag="exp-thread")})
    assert resp.status_code == 200, resp.text
    assert seen["loop"] and seen["set_session"] and seen["sign_out"], seen
    assert seen["set_session"][0] != seen["loop"][0] and seen["sign_out"][0] != seen["loop"][0], (
        "the upstream leg ran on the event-loop thread: " + repr(seen)
    )


# ===========================================================================
# today's 401 is kept everywhere else
# ===========================================================================
def _unauth_signature(resp) -> tuple:
    body = resp.json()
    return resp.status_code, body.get("code"), body.get("error"), body.get("success")


@pytest.mark.parametrize("body", [None, {}, {"refresh_token": None}, {"refresh_token": ""}, {"refresh_token": 123}],
                         ids=["no_body", "empty", "null_rt", "empty_rt", "non_string_rt"])
def test_flag_on_expired_bearer_without_refresh_token_keeps_todays_401(client, gotrue, blacklist, monkeypatch, body):
    """Flag ON, expired Bearer, no usable refresh token -> today's exact 401
    (compared against the flag-OFF answer to the SAME request); nothing is
    posted upstream and nothing is blacklisted."""
    expired = make_jwt(-120, tag="exp-nort")
    headers = {"Authorization": "Bearer " + expired}

    def _send():
        return client.post(LOGOUT_URL, headers=headers) if body is None else client.post(LOGOUT_URL, json=body, headers=headers)

    off = _send()
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    on = _send()
    assert _unauth_signature(on) == _unauth_signature(off), (on.text, off.text)
    assert on.status_code == 401 and on.json().get("code") == "AUTH_REQUIRED", on.text
    assert _posts(gotrue) == [], _posts(gotrue)
    assert blacklist.setex_calls == []


def test_flag_off_expired_bearer_with_refresh_token_is_todays_exact_401(client, gotrue, blacklist):
    """Flag OFF: an expired Bearer + refresh token is today's 401 -- no upstream
    POST, no blacklist write, ``logout_user`` never reached."""
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-FLAG-OFF-EXPIRED"},
                       headers={"Authorization": "Bearer " + make_jwt(-120, tag="exp-off")})
    body = resp.json()
    assert resp.status_code == 401 and body.get("code") == "AUTH_REQUIRED", resp.text
    assert body.get("error") == "Invalid or expired token", resp.text
    assert _posts(gotrue) == [] and blacklist.setex_calls == []


@pytest.mark.parametrize("bearer_kind", ["unexpired_but_rejected", "not_a_jwt", "no_exp_claim"])
def test_flag_on_only_an_expired_jwt_takes_the_expired_branch(client, gotrue, blacklist, monkeypatch, bearer_kind):
    """Anti-overreach: with the flag ON and a refresh token in the body, a
    Bearer that is rejected for any reason OTHER than expiry keeps today's 401
    (e.g. a revoked session whose JWT has not expired, or garbage)."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    if bearer_kind == "unexpired_but_rejected":
        bearer = make_jwt(3600, tag="live-but-rejected")
    elif bearer_kind == "not_a_jwt":
        bearer = "not-a-jwt-token"
    else:
        bearer = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln"  # {"sub": "x"}, no exp
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-OVERREACH"},
                       headers={"Authorization": "Bearer " + bearer})
    assert resp.status_code == 401 and resp.json().get("code") == "AUTH_REQUIRED", resp.text
    assert _posts(gotrue) == [] and blacklist.setex_calls == []


def test_w1_4c_anon_client_never_auto_refreshes_nor_persists(gotrue, reuse_branch):
    """W1-4c option pin, both ``get_auth_client`` branches: the anon client is
    built with ``auto_refresh_token=False`` AND ``persist_session=False`` (the
    Timer nodes in test_retro_w1_4_server.py measure the first; this pins the
    second, which no behavioural node can see), and the reuse branch still
    rides the ONE shared transport."""
    c = auth_service.get_auth_client()
    assert c.options.auto_refresh_token is False and c.options.persist_session is False
    assert c.auth._auto_refresh_token is False and c.auth._persist_session is False
    if reuse_branch == "reuse_on":
        assert c.options.httpx_client is not None
        assert c.options.httpx_client is database_service.get_shared_httpx_client()
    else:
        assert c.options.httpx_client is None


def test_unverified_expiry_parser_edges():
    """The branch picker only: exp in the past -> True; future / missing /
    non-numeric / boolean / malformed -> False."""
    import base64
    import json

    def tok(payload) -> str:
        enc = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        return "eyJhbGciOiJIUzI1NiJ9." + enc + ".sig"

    assert auth_routes._unverified_jwt_is_expired(make_jwt(-5)) is True
    assert auth_routes._unverified_jwt_is_expired(make_jwt(3600)) is False
    assert auth_routes._unverified_jwt_is_expired(tok({"sub": "x"})) is False
    assert auth_routes._unverified_jwt_is_expired(tok({"exp": "1"})) is False
    assert auth_routes._unverified_jwt_is_expired(tok({"exp": True})) is False
    assert auth_routes._unverified_jwt_is_expired(tok([1, 2])) is False
    assert auth_routes._unverified_jwt_is_expired("a.b") is False
    assert auth_routes._unverified_jwt_is_expired("a.!!!.c") is False
