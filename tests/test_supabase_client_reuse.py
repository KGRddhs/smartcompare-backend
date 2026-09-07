"""W0-2 (SESSION 65) -- RED tests for Supabase client reuse + bounded timeouts.

Findings: LS-REQUEST-PATH-BLOCKING-02 / -04, CR-PERFORMANCE-03.

What is wrong today (measured on this tree, not assumed):

  1. `auth_service.get_auth_client()` and `auth_service.get_admin_client()` build
     a BRAND NEW `supabase.create_client(...)` on EVERY call, and
     `database_service.get_user_supabase_client(token)` does the same per
     request. `create_client` costs ~215 ms on this box (~450 ms with the
     `.postgrest.auth()` touch) and ~100% of that is httpx's default TLS setup
     (a fresh SSLContext + certifi CA bundle load). It runs ON the event loop --
     `auth_service.verify_token` builds the client at :256 and only then awaits
     `run_db(...)` -- so on single-worker uvicorn it is pure blocking CPU in the
     request path.

  2. No construction site passes `ClientOptions`, so every postgrest session
     inherits `DEFAULT_POSTGREST_CLIENT_TIMEOUT = 120` for BOTH read and
     connect. A hung Supabase parks a request-path thread for two minutes.

The fix ships behind `ENABLE_SUPABASE_CLIENT_REUSE` (default OFF) plus the
`SUPABASE_POSTGREST_TIMEOUT_SECONDS` knob. Neither is read by any code today,
so the flag-ON tests below fail on an ASSERTION about today's behaviour (a
count, a timeout number, an object identity) -- never on a missing symbol.

VERSION LABEL: the SDK shapes asserted here were probed on the INSTALLED,
OFF-LOCK supabase 2.28.0 / postgrest 2.28.0 / httpx 0.27.0 (the lock pins
2.31.0 / 0.28.1). Cross-checked against the PINNED 2.31.0 wheels unpacked in
`.qa-w0/wheels`: the `ClientOptions.httpx_client` field, the
`DEFAULT_POSTGREST_CLIENT_TIMEOUT = 120` constant and the
`self.session = http_client or Client(...)` adoption line are identical on both.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.auth_routes import get_current_user
from app.main import app
from app.services import auth_service, database_service

FLAG = "ENABLE_SUPABASE_CLIENT_REUSE"
TIMEOUT_ENV = "SUPABASE_POSTGREST_TIMEOUT_SECONDS"

FAKE_URL = "https://w0-2-probe.supabase.co"
FAKE_ANON = "w0-2-anon-key"
FAKE_SERVICE = "w0-2-service-key"

# Measured on this tree at base -- see test_flag_off_construction_unchanged
# for the call-by-call derivation.
BASE_CREATE_CLIENT_CALLS = 3

# postgrest/constants.py: DEFAULT_POSTGREST_CLIENT_TIMEOUT = 120
LIBRARY_DEFAULT_POSTGREST_TIMEOUT = 120


# ---------------------------------------------------------------------------
# stubs + fixtures
# ---------------------------------------------------------------------------


class _StubResponse:
    """Minimal postgrest response: `.data` is an empty dict.

    Empty is deliberate -- every consumer on the two routes driven below treats
    it as "no row" and takes its own fail-open branch, so the routes return 200
    with no endpoint-specific mock wiring:
      * `auth_service.get_user_profile`      -> falsy `.data` -> /auth/me fallback
      * `usage_service._get_user_tier_info`  -> `result.data or {}` -> free tier
      * `usage_service._get_active_referral_bonus` -> `resp.data or []` -> 0
    """

    data: Any = {}


class _StubSupabaseClient:
    """Chainable stand-in for `supabase.Client`; any `.execute()` -> _StubResponse.

    Chains on BOTH attribute access and call, because the two shapes the code
    under test uses are different:
      * the routes do `client.table("x").select(...).execute()`
        -- attribute, then CALL;
      * `database_service.get_user_supabase_client` (:53) does
        `client.postgrest.auth(token)` -- attribute, then ATTRIBUTE.
    Returning a bare function from `__getattr__` (as this stub first did) only
    models the first shape and makes the second raise
    `AttributeError: 'function' object has no attribute 'auth'`, i.e. a
    WRONG-reason failure. Returning `self` plus a `__call__` that returns `self`
    models both.
    """

    def __call__(self, *a, **k):
        return self

    def __getattr__(self, name: str):
        if name == "execute":
            return lambda *a, **k: _StubResponse()
        return self


def _reset_impl_caches() -> None:
    """Drop the memoised clients + shared transport the W0-2 implementation
    introduces. REQUIRED hook name on BOTH service modules:
    ``_reset_client_cache_for_tests()`` (Fable review 2026-09-07). A no-op at
    base, where the hook does not exist -- but without it test 1's counting
    STUB client would be memoised under the flag and served to test 2, which
    would then fail for the WRONG reason (AttributeError on the stub)."""
    for mod in (auth_service, database_service):
        hook = getattr(mod, "_reset_client_cache_for_tests", None)
        if callable(hook):
            hook()


@pytest.fixture(autouse=True)
def _isolate_module_state(monkeypatch):
    """Reset every piece of cross-test state this unit touches.

    `database_service._admin_client` is ALREADY a module-level singleton today
    (database_service.py:24), so without this reset the "pin the number you
    measure at base" gate would be collection-order dependent.
    """
    database_service._admin_client = None
    _reset_impl_caches()

    for mod in (auth_service, database_service):
        monkeypatch.setattr(mod, "SUPABASE_URL", FAKE_URL, raising=False)
        monkeypatch.setattr(mod, "SUPABASE_ANON_KEY", FAKE_ANON, raising=False)
        monkeypatch.setattr(mod, "SUPABASE_SERVICE_KEY", FAKE_SERVICE, raising=False)

    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(TIMEOUT_ENV, raising=False)

    yield

    database_service._admin_client = None
    _reset_impl_caches()
    app.dependency_overrides.clear()


def _fake_user(user_id: str = "w0-2-user"):
    async def _override():
        return {"id": user_id, "email": "w0-2@qaren.app", "access_token": "fake-jwt"}

    return _override


def _drive_two_routes_twice() -> List[Dict[str, Any]]:
    """Hit GET /auth/me and GET /usage/status twice each; return the
    `create_client` call log captured across BOTH service modules.

    Patch targets matter: `auth_service.py:10` and `database_service.py:12`
    both do `from supabase import create_client`, so patching
    `supabase.create_client` would count ZERO.
    """
    calls: List[Dict[str, Any]] = []

    def _counting_create_client(url, key, options=None, **kwargs):
        calls.append({"url": url, "key": key, "options": options})
        return _StubSupabaseClient()

    app.dependency_overrides[get_current_user] = _fake_user()
    headers = {"Authorization": "Bearer fake-jwt"}

    with patch("app.services.auth_service.create_client", new=_counting_create_client), \
         patch("app.services.database_service.create_client", new=_counting_create_client), \
         TestClient(app) as client:
        for _ in range(2):
            r = client.get("/api/v1/auth/me", headers=headers)
            assert r.status_code == 200, r.text
        for _ in range(2):
            r = client.get("/api/v1/usage/status", headers=headers)
            assert r.status_code == 200, r.text

    return calls


# ---------------------------------------------------------------------------
# 1. construction count
# ---------------------------------------------------------------------------


def test_create_client_called_at_most_once_per_key_kind(monkeypatch):
    """RED: with the reuse flag ON, four authenticated requests must build at
    most two Supabase clients (one anon + one admin); today they build one per
    `auth_service.get_admin_client()` call because that function memoises
    nothing.
    """
    monkeypatch.setenv(FLAG, "true")

    calls = _drive_two_routes_twice()

    assert len(calls) <= 2, (
        f"{FLAG}=true still built {len(calls)} Supabase clients across 4 requests "
        f"(keys: {[c['key'] for c in calls]}). Each construction is ~215 ms of "
        "blocking TLS setup ON the event loop."
    )


# ---------------------------------------------------------------------------
# 2. bounded postgrest timeout
# ---------------------------------------------------------------------------


def test_postgrest_timeout_is_bounded_when_env_set(monkeypatch):
    """RED: `SUPABASE_POSTGREST_TIMEOUT_SECONDS=8` must bound the postgrest
    session on BOTH service modules' clients; today no construction site passes
    `ClientOptions`, so both inherit the library default of 120 s on read AND
    connect.

    Uses the REAL `supabase.create_client` -- it performs no network I/O
    (verified in the spike by monkeypatching `socket.getaddrinfo` to raise;
    nothing raised), so a fake URL/key is safe and offline.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "8")

    db_timeout = database_service.get_admin_supabase_client().postgrest.session.timeout
    auth_timeout = auth_service.get_admin_client().postgrest.session.timeout

    assert db_timeout.read is not None and db_timeout.read <= 10, (
        f"database_service admin client postgrest READ timeout is {db_timeout.read}s "
        f"with {TIMEOUT_ENV}=8 set (want <= 10)"
    )
    assert auth_timeout.read is not None and auth_timeout.read <= 10, (
        f"auth_service admin client postgrest READ timeout is {auth_timeout.read}s "
        f"with {TIMEOUT_ENV}=8 set (want <= 10)"
    )
    assert db_timeout.connect is not None and db_timeout.connect <= 5, (
        f"database_service admin client postgrest CONNECT timeout is "
        f"{db_timeout.connect}s with {TIMEOUT_ENV}=8 set (want <= 5)"
    )


# ---------------------------------------------------------------------------
# 3. per-user JWT isolation on top of a memoised anon client
# ---------------------------------------------------------------------------


def test_user_scoped_clients_do_not_share_jwt(monkeypatch):
    """RED: with the reuse flag ON the anon client must be memoised, and two
    concurrently-built user-scoped clients must still each carry their own JWT
    while the shared client carries neither.

    Today `get_auth_client()` returns a fresh object on every call, so the FIRST
    assertion (memoisation identity) is the red. The JWT-isolation assertions
    that follow already hold today and are the invariant the implementation must
    not break: the token lands on the per-request POSTGREST client's own
    `headers` (`postgrest/base_client.py:54`), never on the transport session --
    `postgrest.session.headers['authorization']` carries the ANON KEY, which is
    exactly why sharing one `httpx.Client` cannot bleed a JWT.
    """
    monkeypatch.setenv(FLAG, "true")

    shared_a = auth_service.get_auth_client()
    shared_b = auth_service.get_auth_client()
    assert shared_a is shared_b, (
        f"{FLAG}=true but auth_service.get_auth_client() still returns a NEW "
        "client on every call (no memoisation), so every request pays a fresh "
        "TLS/SSLContext build on the event loop."
    )

    built: Dict[str, Any] = {}
    barrier = threading.Barrier(2)
    errors: List[BaseException] = []

    def _build(token: str) -> None:
        try:
            barrier.wait(timeout=10)
            built[token] = database_service.get_user_supabase_client(token)
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=_build, args=(t,)) for t in ("TOKEN_A", "TOKEN_B")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"concurrent user-client construction raised: {errors!r}"

    client_a = built["TOKEN_A"]
    client_b = built["TOKEN_B"]

    assert client_a.postgrest.headers["Authorization"] == "Bearer TOKEN_A"
    assert client_b.postgrest.headers["Authorization"] == "Bearer TOKEN_B"

    shared_auth = shared_a.postgrest.session.headers.get("authorization", "")
    assert "TOKEN_A" not in shared_auth and "TOKEN_B" not in shared_auth, (
        f"the shared/memoised anon client leaked a user JWT: {shared_auth!r}"
    )


# ---------------------------------------------------------------------------
# 4. flag-OFF pin (GREEN by design -- this is the no-change guard)
# ---------------------------------------------------------------------------


def test_flag_off_construction_unchanged():
    """GREEN at base and at head: with the flag unset, the construction count
    and the timeouts must be exactly today's.

    Base count = 3, measured on this tree, NOT assumed:
      * GET /auth/me -> auth_routes.get_me -> auth_service.get_user_profile ->
        auth_service.get_admin_client() -> create_client. Not memoised, so
        2 requests = 2 constructions.
      * GET /usage/status -> usage_service.get_usage_status ->
        _get_user_tier_info + _get_active_referral_bonus, both via
        database_service.get_admin_supabase_client(), which IS memoised on
        `_admin_client` -> 1 construction for the pair of requests.
    """
    assert FLAG not in os.environ

    calls = _drive_two_routes_twice()
    assert len(calls) == BASE_CREATE_CLIENT_CALLS, (
        f"flag-OFF construction count moved: {len(calls)} != "
        f"{BASE_CREATE_CLIENT_CALLS} (keys: {[c['key'] for c in calls]})"
    )
    assert all(c["options"] is None for c in calls), (
        f"flag-OFF must pass NO ClientOptions -- got {[c['options'] for c in calls]}"
    )

    database_service._admin_client = None
    timeout = database_service.get_admin_supabase_client().postgrest.session.timeout
    assert timeout.read == LIBRARY_DEFAULT_POSTGREST_TIMEOUT
    assert timeout.connect == LIBRARY_DEFAULT_POSTGREST_TIMEOUT


# ---------------------------------------------------------------------------
# 5. design-A consequences, pinned so they cannot happen silently
#    (Fable review amendments 2026-09-07 -- both are BINDING decisions)
# ---------------------------------------------------------------------------


def test_shared_transport_bounds_the_auth_leg_too(monkeypatch):
    """RED: under design A there is ONE shared `httpx.Client`, so
    `SUPABASE_POSTGREST_TIMEOUT_SECONDS` is ONE timeout for postgrest AND
    gotrue. Turning the flag on therefore DELIBERATELY moves the auth leg off
    httpx's 5.0 s default and onto the knob's value (8 s here) -- a LOOSENING of
    the auth ceiling.

    That is a decision, not an accident (spike hazard 2), so it is pinned here:
    if a future implementation quietly leaves gotrue on its own transport, or
    quietly changes what the knob means for auth, this test says so.

    Today the assertion fails on the measured 5.0 s httpx default, because no
    construction site passes `ClientOptions` at all.

    Attribute name: `_http_client` is the gotrue base client's adopted-session
    field on BOTH the installed 2.28.0 and the PINNED 2.31.0
    (`supabase_auth/_sync/gotrue_base_api.py:25` --
    `self._http_client = http_client or Client(...)`; spike section 1b).

    Uses the REAL `supabase.create_client` -- it performs no network I/O
    (verified in `.qa-w0/w0-2-spike.md` by monkeypatching `socket.getaddrinfo`
    to raise; nothing raised), so a fake URL/key is safe and offline.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "8")

    auth_transport_timeout = auth_service.get_auth_client().auth._http_client.timeout

    assert auth_transport_timeout.read == 8.0, (
        f"{FLAG}=true with {TIMEOUT_ENV}=8 must put the gotrue leg on the SHARED "
        f"httpx client, so its READ timeout must be the knob's 8.0s -- got "
        f"{auth_transport_timeout.read}s (httpx's own default is 5.0s, i.e. no "
        "shared transport was threaded through ClientOptions(httpx_client=...))."
    )
    assert auth_transport_timeout.connect == 3.0, (
        f"the shared transport must be built with connect=3.0 -- got "
        f"{auth_transport_timeout.connect}s on the auth leg"
    )


def test_client_options_fresh_per_construction_but_transport_shared(monkeypatch):
    """RED: under the flag every construction must pass a FRESH `ClientOptions`
    object that carries the SAME shared `httpx.Client`.

    Spike hazard 1 is why the options object cannot be shared:
    `supabase/_sync/client.py:72` does `self.options = copy.copy(options)` -- a
    SHALLOW copy -- so a module-level options object hands every client the SAME
    `options.storage`. With `persist_session=True` (the default) one user's
    sign-in `Session` is written into that shared `SyncMemoryStorage` and the
    NEXT `Client.create()` reads it back (`:113`) and stamps that JWT into its
    own headers (`:122-124`). That is a genuine cross-user JWT bleed, and it
    comes from sharing the OPTIONS object, not from sharing the transport.

    So the contract is: fresh options, shared `httpx_client`, distinct
    `storage`. Design A (Fable review 2026-09-07): pass ONLY `httpx_client=`
    under the flag -- `postgrest_client_timeout` / `storage_client_timeout` are
    inert once a shared client is adopted AND emit a DeprecationWarning on the
    pinned 2.31.0 -- so the bound lives on the shared client itself.

    Today `database_service.get_user_supabase_client` calls
    `create_client(URL, ANON_KEY)` positionally with no `options=` at all, so
    the FIRST assertion below is the red.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "8")

    captured: List[Any] = []

    def _recording_create_client(url, key, options=None, **kwargs):
        captured.append(options)
        return _StubSupabaseClient()

    with patch("app.services.auth_service.create_client", new=_recording_create_client), \
         patch("app.services.database_service.create_client", new=_recording_create_client):
        database_service.get_user_supabase_client("TOKEN_X")
        database_service.get_user_supabase_client("TOKEN_Y")

    assert len(captured) == 2, (
        "precondition: two user-scoped clients must still be constructed "
        f"per request under the flag (design A keeps this at ~0.06 ms), got "
        f"{len(captured)}"
    )

    opts_x, opts_y = captured

    assert opts_x is not None, (
        "flag ON but no ClientOptions/shared transport passed to create_client"
    )
    assert opts_y is not None, (
        "flag ON but no ClientOptions/shared transport passed to create_client "
        "on the SECOND construction"
    )
    assert opts_x is not opts_y, (
        "a SHARED ClientOptions object was passed to both constructions -- "
        "supabase shallow-copies options, so both clients would share "
        "options.storage, which is the cross-user JWT-bleed carrier (spike "
        "hazard 1). Build a fresh ClientOptions per construction."
    )
    assert opts_x.httpx_client is not None, (
        "ClientOptions was passed but carries no httpx_client -- design A "
        "requires ONE shared httpx.Client so a construction costs ~0.06 ms "
        "instead of ~450 ms of TLS setup on the event loop"
    )
    assert opts_x.httpx_client is opts_y.httpx_client, (
        "the two constructions got DIFFERENT httpx clients "
        f"({opts_x.httpx_client!r} vs {opts_y.httpx_client!r}) -- the transport "
        "(and therefore the SSLContext and the connection pool) must be shared"
    )
    assert opts_x.storage is not opts_y.storage, (
        "the two constructions share one options.storage -- a sign-in on one "
        "user's client would be read back into the next user's client "
        "(spike hazard 1, cross-user JWT bleed)"
    )
