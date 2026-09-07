"""W1-4 (SESSION 65) RED tests -- refresh 503-vs-401, and a logout that
actually revokes.

Findings: ``LS-CACHE-REDIS-03``, ``MB-NETWORK-CONTRACT-02``.
Flag: ``ENABLE_LOGOUT_UPSTREAM_REVOCATION`` (default OFF) gates the LOGOUT half
only. The REFRESH half ships UNFLAGGED -- it is activation precondition (1) for
the other session's merged ``ENABLE_STRICT_OPTIONAL_AUTH`` (PR #138), and behind
a dark flag it could never satisfy that precondition.

Written BEFORE the implementation. Every red node fails on an ASSERTION about
behaviour measured through an EXISTING runtime path (a status code, a top-level
envelope key, an ordered call log recorded by a stub installed over a symbol
that already exists) -- never on an ImportError or an AttributeError for a
symbol that does not exist yet.

--------------------------------------------------------------------------
WHAT IS WRONG TODAY (measured on this tree at dd6ecb3a)
--------------------------------------------------------------------------

(1) ``auth_routes.py:606-612`` -- ``result = await refresh_session(...)`` then
    ``if not result["success"]: raise HTTPException(401, ...)``. EVERY failure
    becomes 401, a transient upstream one included.
    ``auth_service._categorize_auth_error`` (``:164-192``) already separates the
    transient class at ``:173-177`` (network / connection / timeout / dns /
    econnrefused / socket hang up / enotfound / failed to fetch / no network ->
    "Connection failed. Please try again.") but returns NO machine-readable
    marker, so the route cannot tell it from a genuinely invalid token. On
    phones that 401 drives the forced-logout listener: one Supabase blip signs
    out every user holding an expiring token.

(2) ``auth_service.logout_user`` (``:407-419``) blacklists the ACCESS token in
    Redis for 1 h and then calls ``client.auth.sign_out()`` on a FRESHLY BUILT
    anon client that holds no session. Real gotrue ``sign_out`` reads the
    session off the client's OWN storage
    (``supabase_auth/_sync/gotrue_client.py``: ``session = self.get_session()``;
    ``if access_token: self.admin.sign_out(access_token, scope)``), so with no
    stored session it is a silent no-op -- and any raise is swallowed while the
    route still reports success. The REFRESH token therefore stays valid
    upstream: past the 1 h blacklist TTL a stolen refresh token still mints new
    sessions.

--------------------------------------------------------------------------
THE ENVELOPE TRAP (cost two nodes in W2-1)
--------------------------------------------------------------------------

``main.py:149`` registers ``error_handler.http_exception_handler``, which
unwraps a structured ``detail`` into a TOP-LEVEL
``{success, error, code, request_id}``. So every assertion below reads
``body["code"]``, never ``body["detail"]["code"]``. Sibling pin:
``tests/test_m13_03_paid_work_gating.py:132``.

Second half of the same trap: ``error_handler.STATUS_CODE_MAP[503]`` is
``"FEATURE_DISABLED"``. A bare ``HTTPException(503, "message")`` therefore ships
``code == "FEATURE_DISABLED"``, NOT the code this unit specifies. The fix must
raise the STRUCTURED detail
``{"code": "REFRESH_UPSTREAM_UNAVAILABLE", "error": ...}`` so the handler
overrides the map. Node 1 asserts the code, so a bare 503 fails it.

--------------------------------------------------------------------------
TWO PLACES THIS FILE DEVIATES FROM THE UNIT SPEC, WITH EVIDENCE
--------------------------------------------------------------------------

(A) ``sign_out(scope="local")`` IS NOT A CALL THE PINNED SDK ACCEPTS.
    Measured on the installed supabase 2.28.0 and unchanged in shape on the
    lock's 2.31.0 pin (``requirements.txt:156-158``)::

        SyncGoTrueClient.sign_out(self, options: Optional[SignOutOptions] = None)

    ``SignOutOptions`` is a TypedDict ``{"scope": Literal["global","local","others"]}``
    and the body does ``signout_options = options or {"scope": "global"}``.
    There is no ``scope`` parameter. ``client.auth.sign_out(scope="local")``
    raises ``TypeError: sign_out() got an unexpected keyword argument 'scope'``
    -- which ``logout_user``'s bare ``except Exception`` swallows, leaving the
    caller with today's silent no-op AND a success message.

    So the stub below declares the REAL signature (``options=None``) and lets
    Python raise on any other keyword, exactly as production would. The tests
    pin the SCOPE VALUE that reaches the SDK (resolved through
    ``_signout_scope``, which mirrors the SDK's own ``or {"scope": "global"}``
    default), NOT a kwarg spelling. A stub that accepted ``scope="local"`` would
    go green over a production TypeError; this one cannot.

(B) NODE 6 CANNOT PIN "401 ON A TRANSIENT ERROR WHEN THE FLAG IS OFF".
    The spec's node 6 says flag OFF is "byte-identical to today on BOTH routes",
    but its own Defect-1 section rules that the refresh half ships UNFLAGGED
    precisely so it is live for the other session's precondition. Both cannot
    hold: with the refresh fix unflagged, a transient failure is 503 whatever
    ``ENABLE_LOGOUT_UPSTREAM_REVOCATION`` says. Node 6 therefore pins what is
    actually invariant under the flag:
      * ``/auth/logout`` flag OFF, refresh token IN the body -> today's path
        exactly (bare ``sign_out()``, no ``set_session``, the 1 h Redis
        blacklist write, today's body);
      * ``/auth/refresh`` flag OFF, genuinely invalid token -> still 401
        ``AUTH_REQUIRED``.
    Node 2 carries the unflagged half of the same guarantee.

--------------------------------------------------------------------------
ISOLATION
--------------------------------------------------------------------------

Every node uses DISTINCT user ids, access tokens and refresh tokens, so no
Redis blacklist key, no upstream token record and no slowapi bucket is ever
shared. ``conftest._reset_rate_limiter`` already clears the in-memory slowapi
window before each test, and no node spends more than 2 of ``/refresh``'s
10/min; ``/logout`` carries no limiter decorator and
``ENABLE_DEFAULT_RATE_LIMITS`` is default OFF, so ``SlowAPIMiddleware`` is not
registered. conftest is NOT modified by this unit.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

import pytest
from fastapi.testclient import TestClient

from app.api.auth_routes import get_current_user
from app.main import app
from app.services import auth_service, cache_service

FLAG = "ENABLE_LOGOUT_UPSTREAM_REVOCATION"

REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"

# The 503 contract this unit introduces.
UPSTREAM_CODE = "REFRESH_UPSTREAM_UNAVAILABLE"
# error_handler.STATUS_CODE_MAP[401]
AUTH_REQUIRED = "AUTH_REQUIRED"
# error_handler.STATUS_CODE_MAP[503] -- what a BARE 503 would ship.
FEATURE_DISABLED = "FEATURE_DISABLED"

# auth_service._revoke_token: setex(f"revoked:{sha256}", 3600, "1")
BLACKLIST_TTL_SECONDS = 3600


# ---------------------------------------------------------------------------
# stubs
# ---------------------------------------------------------------------------
class UpstreamTokenStore:
    """Models gotrue's SERVER-SIDE refresh-token store.

    This is the thing the finding is about: the Redis blacklist covers the
    ACCESS token for 1 h, but nothing today touches the refresh token upstream.
    Revocation is modelled the way real gotrue does it -- per refresh token for
    ``scope="local"``, per USER for ``scope="global"`` -- so the two-device pin
    in node 4 can tell the two apart instead of trusting a kwarg.
    """

    def __init__(self) -> None:
        self._owner: Dict[str, str] = {}
        self._revoked: set = set()

    def issue(self, user_id: str, refresh_token: str) -> str:
        self._owner[refresh_token] = user_id
        return refresh_token

    def is_valid(self, refresh_token: str) -> bool:
        return refresh_token in self._owner and refresh_token not in self._revoked

    def revoke_one(self, refresh_token: str) -> None:
        self._revoked.add(refresh_token)

    def revoke_all_for_user(self, user_id: str) -> None:
        for token, owner in self._owner.items():
            if owner == user_id:
                self._revoked.add(token)


class _StubSession:
    def __init__(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = 4102444800  # 2100-01-01, far past any test clock


class _StubAuthResponse:
    def __init__(self, session: Optional[_StubSession]) -> None:
        self.session = session
        # Deliberately None: a truthy `.user` sends `auth_service.refresh_session`
        # into `get_admin_client().table("users")...execute()`, i.e. a real
        # network call to the neutralized `.invalid` Supabase host. Absent
        # `.user` keeps every node offline while exercising the same route code.
        self.user = None


class StubGoTrueAuth:
    """Stand-in for ``client.auth`` with the PINNED SDK's real signatures.

    ``sign_out`` deliberately declares ``options=None`` and nothing else, so a
    ``sign_out(scope="local")`` implementation raises ``TypeError`` here exactly
    as it would in production (see deviation (A) in the module docstring).
    """

    def __init__(self, upstream: UpstreamTokenStore, calls: List[Tuple[str, tuple, dict]]) -> None:
        self._upstream = upstream
        self.calls = calls
        # What `_save_session` would have stored; None until set_session runs.
        self._session: Optional[_StubSession] = None
        self.refresh_error: Optional[BaseException] = None
        self.refresh_returns_no_session: bool = False

    # -- refresh -----------------------------------------------------------
    def refresh_session(self, refresh_token: Optional[str] = None) -> _StubAuthResponse:
        self.calls.append(("refresh_session", (refresh_token,), {}))
        if self.refresh_error is not None:
            raise self.refresh_error
        if self.refresh_returns_no_session:
            return _StubAuthResponse(None)
        if not self._upstream.is_valid(refresh_token or ""):
            raise Exception("Invalid Refresh Token: Refresh Token Not Found")
        return _StubAuthResponse(_StubSession("rotated-access-" + str(refresh_token), str(refresh_token)))

    # -- logout ------------------------------------------------------------
    def set_session(self, access_token: str, refresh_token: str) -> _StubAuthResponse:
        self.calls.append(("set_session", (access_token, refresh_token), {}))
        self._session = _StubSession(access_token, refresh_token)
        return _StubAuthResponse(self._session)

    def sign_out(self, options: Optional[dict] = None) -> None:
        self.calls.append(("sign_out", (), {"options": options}))
        scope = _signout_scope(options)
        if self._session is None:
            # Today's reality: nothing stored -> gotrue has nothing to revoke.
            return
        if scope == "global":
            owner = self._upstream._owner.get(self._session.refresh_token)
            if owner:
                self._upstream.revoke_all_for_user(owner)
        else:
            self._upstream.revoke_one(self._session.refresh_token)


class StubSupabaseClient:
    def __init__(self, auth: StubGoTrueAuth) -> None:
        self.auth = auth


class FakeRedis:
    """Records the blacklist write ``auth_service._revoke_token`` performs."""

    def __init__(self) -> None:
        self.setex_calls: List[Tuple[str, int, str]] = []
        self.store: Dict[str, str] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.setex_calls.append((key, ttl, value))
        self.store[key] = value

    def get(self, key: str) -> Optional[str]:
        return self.store.get(key)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _signout_scope(options: Any) -> str:
    """Resolve the scope the SDK would use -- mirrors gotrue's own default."""
    if isinstance(options, dict) and isinstance(options.get("scope"), str):
        return options["scope"]
    return "global"


def _names(calls: List[Tuple[str, tuple, dict]]) -> List[str]:
    return [name for name, _a, _k in calls]


def _blacklist_key(access_token: str) -> str:
    return "revoked:" + hashlib.sha256(access_token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    """Every node states its own flag value; never inherit the ambient env."""
    monkeypatch.delenv(FLAG, raising=False)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def upstream():
    return UpstreamTokenStore()


@pytest.fixture
def gotrue(monkeypatch, upstream):
    """Install the stub over ``auth_service.get_auth_client``.

    That symbol EXISTS today (``auth_service.py:102``) and both code paths under
    test already call it, so this is an interception of a live runtime path, not
    a scaffold for something unwritten.
    """
    calls: List[Tuple[str, tuple, dict]] = []
    auth = StubGoTrueAuth(upstream, calls)
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: StubSupabaseClient(auth))
    return auth


@pytest.fixture
def fake_redis(monkeypatch):
    """``_revoke_token`` imports ``redis_client`` INSIDE the function body, so
    patching the module attribute is what the call actually resolves."""
    fake = FakeRedis()
    monkeypatch.setattr(cache_service, "redis_client", fake)
    return fake


def _authenticate_as(user_id: str, access_token: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user_id,
        "email": user_id + "@w1-4.invalid",
        "access_token": access_token,
    }


# ===========================================================================
# NODE 1 -- a transient upstream failure must be 503, not 401 (UNFLAGGED)
# ===========================================================================
def test_node1_transient_upstream_failure_is_503_not_401(client, gotrue, upstream):
    """LS-CACHE-REDIS-03 / MB-NETWORK-CONTRACT-02.

    Drives the REAL ``POST /api/v1/auth/refresh`` route through the ASGI app.
    The stub raises from ``client.auth.refresh_session``, i.e. INSIDE
    ``auth_service.refresh_session``'s own try/except, so the REAL
    ``_categorize_auth_error`` runs and takes its EXISTING network branch
    (``auth_service.py:173-177`` matches both "connection" and "timeout").

    NOTE on the patch target -- deliberately NOT ``auth_routes.refresh_session``.
    ``auth_routes.py:26-30`` does ``from app.services.auth_service import (...
    refresh_session ...)``, so that name is a module-level rebinding in
    ``app.api.auth_routes`` and patching it WOULD intercept the route. But a
    patched-to-raise route-level symbol never reaches the categoriser: the
    exception escapes the route as an unhandled 500, which is NOT the 401 this
    finding is about. Patching one layer lower is the only way to measure the
    real 401-vs-503 decision.

    RED TODAY: 401 / AUTH_REQUIRED.
    """
    refresh_token = "w1-4-n1-refresh"
    upstream.issue("user-n1", refresh_token)
    gotrue.refresh_error = ConnectionError("connection timeout")

    resp = client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    body = resp.json()

    assert resp.status_code == 503, (
        "a transient Supabase failure must be 503, not a token verdict; got "
        + str(resp.status_code) + " " + resp.text
    )
    # Top-level, NOT body["detail"]["code"] -- http_exception_handler unwraps.
    assert body.get("code") == UPSTREAM_CODE, (
        "expected top-level code " + UPSTREAM_CODE + " (a BARE HTTPException(503) "
        "ships " + FEATURE_DISABLED + " from STATUS_CODE_MAP); got " + repr(body)
    )
    assert body.get("success") is False, repr(body)


# ===========================================================================
# NODE 2 -- a genuinely invalid refresh token STILL 401s (the anti-overreach pin)
# ===========================================================================
def test_node2_invalid_refresh_token_still_401(client, gotrue, upstream):
    """GREEN TODAY and must stay green: the 503 mapping must cover ONLY the
    transient class. Both real failure shapes are exercised:

      (a) upstream rejects the token   -> ``_categorize_auth_error`` else-branch
      (b) ``response.session is None`` -> ``{"success": False,
                                             "error": "Failed to refresh session"}``

    Distinct tokens per shape; 2 requests, well inside ``/refresh``'s 10/min.
    """
    # (a) rejected token -- never issued upstream, so the stub raises the real
    #     gotrue message. No network term in it -> the else-branch -> 401.
    resp_a = client.post(REFRESH_URL, json={"refresh_token": "w1-4-n2-never-issued"})
    assert resp_a.status_code == 401, (
        "an invalid refresh token must stay 401; got " + str(resp_a.status_code)
        + " " + resp_a.text
    )
    assert resp_a.json().get("code") == AUTH_REQUIRED, resp_a.text

    # (b) no session on the response object.
    upstream.issue("user-n2", "w1-4-n2-no-session")
    gotrue.refresh_returns_no_session = True
    resp_b = client.post(REFRESH_URL, json={"refresh_token": "w1-4-n2-no-session"})
    assert resp_b.status_code == 401, (
        "a session-less refresh response must stay 401; got "
        + str(resp_b.status_code) + " " + resp_b.text
    )
    assert resp_b.json().get("code") == AUTH_REQUIRED, resp_b.text


# ===========================================================================
# NODE 3 -- flag ON + refresh token in the body -> set_session THEN sign_out(local)
# ===========================================================================
def test_node3_flag_on_sets_session_then_signs_out_local(
    client, gotrue, upstream, fake_redis, monkeypatch
):
    """RED TODAY: the call log is exactly ``["sign_out"]`` -- no ``set_session``,
    so gotrue has no session to revoke and the call is a silent no-op.

    The ORDER matters and is why the stub records an ordered log rather than
    two booleans: ``sign_out`` reads the session off the client's own storage,
    so a ``sign_out`` that runs BEFORE ``set_session`` revokes nothing at all.
    """
    monkeypatch.setenv(FLAG, "true")
    access = "w1-4-n3-access"
    refresh = "w1-4-n3-refresh"
    upstream.issue("user-n3", refresh)
    _authenticate_as("user-n3", access)

    resp = client.post(
        LOGOUT_URL,
        json={"refresh_token": refresh},
        headers={"Authorization": "Bearer " + access},
    )
    assert resp.status_code == 200, resp.text

    names = _names(gotrue.calls)
    assert "set_session" in names, (
        "flag ON with a refresh token in the body must call set_session before "
        "sign_out, or gotrue has nothing to revoke; call log was " + repr(names)
    )
    assert "sign_out" in names, "sign_out must still be called; log " + repr(names)
    assert names.index("set_session") < names.index("sign_out"), (
        "set_session must precede sign_out; call log was " + repr(names)
    )

    set_call = [c for c in gotrue.calls if c[0] == "set_session"][0]
    assert set_call[1] == (access, refresh), (
        "set_session must receive (access_token, refresh_token) positionally, "
        "matching the pinned SDK signature; got " + repr(set_call)
    )

    signout_call = [c for c in gotrue.calls if c[0] == "sign_out"][0]
    assert _signout_scope(signout_call[2].get("options")) == "local", (
        "BINDING RULING: scope must be 'local', not 'global' -- see the unit "
        "spec. Resolved scope was "
        + _signout_scope(signout_call[2].get("options"))
        + " from " + repr(signout_call[2])
    )

    # The 1 h access-token blacklist is unchanged by the flag.
    assert (_blacklist_key(access), BLACKLIST_TTL_SECONDS, "1") in fake_redis.setex_calls, (
        "the Redis blacklist write must survive the revocation change; got "
        + repr(fake_redis.setex_calls)
    )


# ===========================================================================
# NODE 4 -- the local-not-global pin: device B survives device A's logout
# ===========================================================================
def test_node4_flag_on_logout_is_local_second_device_survives(
    client, gotrue, upstream, fake_redis, monkeypatch
):
    """Two devices, ONE user.

    (a) device A's refresh token must be REVOKED upstream after A logs out --
        RED TODAY (nothing upstream is touched, so it stays valid);
    (b) device B's refresh token must STILL WORK -- GREEN today (vacuously) and
        the assertion that makes a future switch to ``scope="global"`` fail
        loudly instead of silently signing people out of their tablets.

    (b) is measured END TO END: B's token is driven back through the real
    ``POST /api/v1/auth/refresh`` route and must return 200.
    """
    monkeypatch.setenv(FLAG, "true")
    user = "user-n4"
    access_a = "w1-4-n4-access-A"
    refresh_a = "w1-4-n4-refresh-A"
    refresh_b = "w1-4-n4-refresh-B"
    upstream.issue(user, refresh_a)
    upstream.issue(user, refresh_b)
    _authenticate_as(user, access_a)

    resp = client.post(
        LOGOUT_URL,
        json={"refresh_token": refresh_a},
        headers={"Authorization": "Bearer " + access_a},
    )
    assert resp.status_code == 200, resp.text

    assert not upstream.is_valid(refresh_a), (
        "device A's OWN refresh token must be revoked upstream by logout -- "
        "this is the finding; call log was " + repr(_names(gotrue.calls))
    )
    assert upstream.is_valid(refresh_b), (
        "device B's refresh token must be UNTOUCHED (scope='local', not "
        "'global'); it was revoked, so logout signed the user out everywhere"
    )

    resp_b = client.post(REFRESH_URL, json={"refresh_token": refresh_b})
    assert resp_b.status_code == 200, (
        "device B must still be able to refresh after device A logs out; got "
        + str(resp_b.status_code) + " " + resp_b.text
    )
    assert resp_b.json().get("success") is True, resp_b.text


# ===========================================================================
# NODE 5 -- flag ON, NO refresh token in the body -> today's path exactly
# ===========================================================================
def test_node5_flag_on_without_refresh_token_is_todays_path(
    client, gotrue, upstream, fake_redis, monkeypatch
):
    """GREEN today and after. Sending the refresh token is a CLIENT change that
    reaches devices only with the next OTA, so flag ON must be inert for every
    client that does not send one -- blacklist write only, ``set_session``
    never called.

    Both no-body shapes are exercised, with DISTINCT users and tokens, because
    the implementation may declare the body as ``Optional[LogoutRequest] = None``
    (no body at all) or as a model with an optional field (``{}``):
      (a) no request body at all;
      (b) an explicit empty JSON object.
    """
    monkeypatch.setenv(FLAG, "true")

    # (a) no body at all
    access_a = "w1-4-n5-access-nobody"
    _authenticate_as("user-n5a", access_a)
    resp_a = client.post(LOGOUT_URL, headers={"Authorization": "Bearer " + access_a})
    assert resp_a.status_code == 200, resp_a.text
    assert resp_a.json() == {"success": True, "message": "Logged out successfully"}, resp_a.text

    # (b) explicit empty object
    access_b = "w1-4-n5-access-emptybody"
    _authenticate_as("user-n5b", access_b)
    resp_b = client.post(
        LOGOUT_URL, json={}, headers={"Authorization": "Bearer " + access_b}
    )
    assert resp_b.status_code == 200, resp_b.text
    assert resp_b.json() == {"success": True, "message": "Logged out successfully"}, resp_b.text

    assert "set_session" not in _names(gotrue.calls), (
        "with no refresh token in the body the path must be exactly today's; "
        "call log was " + repr(_names(gotrue.calls))
    )
    assert _names(gotrue.calls) == ["sign_out", "sign_out"], (
        "exactly one bare sign_out per logout, as today; got "
        + repr(_names(gotrue.calls))
    )
    for key in (_blacklist_key(access_a), _blacklist_key(access_b)):
        assert (key, BLACKLIST_TTL_SECONDS, "1") in fake_redis.setex_calls, (
            "the 1 h blacklist write must still happen; got "
            + repr(fake_redis.setex_calls)
        )


# ===========================================================================
# NODE 6 -- flag OFF pin (see deviation (B) in the module docstring)
# ===========================================================================
def test_node6_flag_off_is_todays_behaviour_on_both_routes(
    client, gotrue, upstream, fake_redis, monkeypatch
):
    """GREEN today and after.

    ``/auth/logout`` flag OFF with a refresh token IN the body must ignore it
    entirely -- bare ``sign_out()`` (options None -> the SDK's own 'global'
    default, i.e. the call shape today makes), no ``set_session``, the refresh
    token untouched upstream, the 1 h Redis blacklist write, today's body.

    ``/auth/refresh`` flag OFF with a genuinely invalid token must still be 401
    ``AUTH_REQUIRED``. The TRANSIENT->503 mapping is deliberately NOT pinned to
    flag OFF here: the unit spec rules the refresh half UNFLAGGED, so it is live
    regardless of this flag. Node 1 owns that assertion.
    """
    monkeypatch.setenv(FLAG, "false")
    user = "user-n6"
    access = "w1-4-n6-access"
    refresh = "w1-4-n6-refresh"
    upstream.issue(user, refresh)
    _authenticate_as(user, access)

    resp = client.post(
        LOGOUT_URL,
        json={"refresh_token": refresh},
        headers={"Authorization": "Bearer " + access},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True, "message": "Logged out successfully"}, resp.text

    assert _names(gotrue.calls) == ["sign_out"], (
        "flag OFF must make exactly today's single bare sign_out call; got "
        + repr(gotrue.calls)
    )
    assert gotrue.calls[0][1] == () and gotrue.calls[0][2] == {"options": None}, (
        "flag OFF must call sign_out() with no arguments at all; got "
        + repr(gotrue.calls[0])
    )
    assert upstream.is_valid(refresh), (
        "flag OFF must not revoke anything upstream -- that is the whole point "
        "of the flag being OFF"
    )
    assert (_blacklist_key(access), BLACKLIST_TTL_SECONDS, "1") in fake_redis.setex_calls, (
        "the 1 h Redis blacklist write is today's behaviour and must survive; "
        "got " + repr(fake_redis.setex_calls)
    )

    # /auth/refresh under the same flag state: an invalid token is still 401.
    resp_r = client.post(REFRESH_URL, json={"refresh_token": "w1-4-n6-never-issued"})
    assert resp_r.status_code == 401, (
        "flag OFF, invalid refresh token -> still 401; got "
        + str(resp_r.status_code) + " " + resp_r.text
    )
    assert resp_r.json().get("code") == AUTH_REQUIRED, resp_r.text
