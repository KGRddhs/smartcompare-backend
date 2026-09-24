"""Retro-fix R-MAIN / W1-9c -- RED phase.

Spec: the retroactive adversary report on W1-9 (PR #152, "429 contract on both
classes"), defect 2, plus the orchestrator's binding ruling:

  W1-9c: under ENABLE_DEFAULT_RATE_LIMITS register
      ``slowapi.middleware.SlowAPIASGIMiddleware`` (async-aware) instead of
      ``SlowAPIMiddleware``, so the 21 default-limited (undecorated) routes 429
      with the project envelope + ``code`` + ``Retry-After``. It stays INSIDE
      the flag: flag OFF must be byte-identical (no rate-limit middleware at
      all).

Re-measured here on the pinned venv (slowapi 0.1.10, fastapi 0.141.1,
starlette 1.6.0) with the flag ON and the real ``app/main.py``:
``SlowAPIMiddleware.sync_check_limits`` calls slowapi's own
``_rate_limit_exceeded_handler`` because ours is a coroutine, so the 11th
``GET /health`` returns ``{"error":"Rate limit exceeded: 10 per 1 minute"}``
with NO ``success``/``code``/``request_id``/``retry_after_seconds`` and NO
``Retry-After``. With ``SlowAPIASGIMiddleware`` swapped in, the same call
returns the full envelope, ``code: RATE_LIMITED``, ``Retry-After: 60`` and
``retry_after_seconds: 60``.

SPEC DISAGREEMENT (measured, recorded for the orchestrator): on the pinned
stack the blanket default reaches only the three APP-LEVEL routes
(``/health``, ``/``, ``/favicon.ico``). Every router-included route is an
``_IncludedRouter`` entry without ``.endpoint``, which slowapi exempts in both
middlewares -- so the swap fixes the 429 SHAPE on those three routes and does
not make the "21 undecorated routes" limited. See
``TestW19cMeasuredRouterExemption``.

HOW THE FLAG-ON APP IS BUILT. ``app/main.py`` reads the flag once, at import.
Re-importing ``app.main`` would replace the app object every other test holds,
so each flag-ON test executes the REAL ``app/main.py`` source into a FRESH,
private module object (``importlib.util.spec_from_file_location``), leaving
``sys.modules["app.main"]`` untouched. The routers and the limiter are the
shared singletons the production import uses. ``load_dotenv``,
``configure_logging`` and ``init_sentry`` are stubbed for that exec only, so it
cannot re-read ``.env`` over the test's flag, clear pytest's log handlers, or
start Sentry. The conftest autouse ``_reset_rate_limiter`` gives every test an
empty window.

Zero network: an autouse guard blocks every non-loopback ``connect`` and
``getaddrinfo`` and fails the test on any attempt.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import itertools
import socket
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app.main as app_main

FLAG = "ENABLE_DEFAULT_RATE_LIMITS"
DEFAULT_LIMIT_PER_MINUTE = 10  # ANON_LIMIT = "10/minute"
_ENVELOPE_KEYS = {"success", "error", "code", "request_id", "retry_after_seconds"}


# ---------------------------------------------------------------------------
# Zero-network guard (autouse)
# ---------------------------------------------------------------------------

_LOOPBACK_NAMES = {"localhost", "testserver", "", None}


def _is_loopback(host) -> bool:
    if isinstance(host, (bytes, bytearray)):
        host = bytes(host).decode("latin-1")
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _host(addr):
        return addr[0] if isinstance(addr, tuple) else addr

    def guarded_connect(self, addr):
        if not _is_loopback(_host(addr)):
            attempts.append(("connect", repr(addr)))
            raise OSError(f"zero-network guard: blocked connect to {addr!r}")
        return real_connect(self, addr)

    def guarded_connect_ex(self, addr):
        if not _is_loopback(_host(addr)):
            attempts.append(("connect_ex", repr(addr)))
            raise OSError(f"zero-network guard: blocked connect_ex to {addr!r}")
        return real_connect_ex(self, addr)

    def guarded_gai(host, *args, **kwargs):
        if not _is_loopback(host):
            attempts.append(("getaddrinfo", repr(host)))
            raise OSError(f"zero-network guard: blocked getaddrinfo({host!r})")
        return real_gai(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    yield
    assert not attempts, f"test attempted network access: {attempts}"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_counter = itertools.count()


def _fresh_main(monkeypatch, flag_on: bool, flag_value: str | None = None):
    """Execute the real app/main.py into a private module with the flag set.

    ``flag_value`` (when given) is written verbatim; otherwise ``flag_on``
    selects "true" or an unset variable.
    """
    import dotenv

    import app.middleware.logging_config as logging_config
    import app.services.sentry_service as sentry_service

    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    elif flag_on:
        monkeypatch.setenv(FLAG, "true")
    else:
        monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(logging_config, "configure_logging", lambda *a, **k: None)
    monkeypatch.setattr(sentry_service, "init_sentry", lambda *a, **k: None)

    name = f"_retro_w1_9_main_{next(_counter)}"
    spec = importlib.util.spec_from_file_location(name, app_main.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _middleware_names(app) -> list[str]:
    return [m.cls.__name__ for m in app.user_middleware]


def _drive(client, path: str, n: int, method: str = "get", **kwargs):
    return [getattr(client, method)(path, **kwargs) for _ in range(n)]


def _assert_contract_429(resp):
    assert resp.status_code == 429, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert set(body) >= _ENVELOPE_KEYS, (
        f"the default-limit 429 is not the project envelope: {body!r} "
        f"(headers={dict(resp.headers)!r}). SlowAPIMiddleware discards the async "
        "rate_limit_handler and serves slowapi's bare body."
    )
    assert body["success"] is False
    assert body["code"] == "RATE_LIMITED", body
    assert body["request_id"] and body["request_id"] != "unknown", body
    seconds = body["retry_after_seconds"]
    assert isinstance(seconds, int) and not isinstance(seconds, bool), body
    assert 0 < seconds <= 61, body
    assert resp.headers.get("retry-after") == str(seconds), (
        f"Retry-After header {resp.headers.get('retry-after')!r} != body "
        f"retry_after_seconds {seconds!r}"
    )
    # Still inside RequestIDMiddleware + SecurityHeadersMiddleware.
    assert resp.headers.get("x-request-id") == body["request_id"]
    assert resp.headers.get("x-content-type-options") == "nosniff"


# ===========================================================================
# RED -- flag ON: the undecorated routes' 429 carries the contract
# ===========================================================================


class TestW19cFlagOnDefaultLimitCarriesTheContract:
    def test_flag_on_registers_the_async_aware_middleware(self, monkeypatch):
        """RED today: the flag registers SlowAPIMiddleware (BaseHTTPMiddleware,
        sync_check_limits), which cannot await our coroutine handler."""
        module = _fresh_main(monkeypatch, flag_on=True)
        names = _middleware_names(module.app)
        assert "SlowAPIASGIMiddleware" in names, names
        assert "SlowAPIMiddleware" not in names, names

    def test_health_11th_call_is_the_envelope_with_retry_after(self, monkeypatch):
        """RED today: call 11 returns {"error": "Rate limit exceeded: 10 per 1
        minute"} with no code, no request_id and no Retry-After."""
        module = _fresh_main(monkeypatch, flag_on=True)
        client = TestClient(module.app)
        responses = _drive(client, "/health", DEFAULT_LIMIT_PER_MINUTE + 1)
        assert [r.status_code for r in responses[:DEFAULT_LIMIT_PER_MINUTE]] == [200] * 10
        _assert_contract_429(responses[-1])

    @pytest.mark.parametrize("path", ["/", "/favicon.ico"])
    def test_other_app_level_routes_429_with_the_contract(self, monkeypatch, path):
        """RED today: the other app-level undecorated routes share the same
        bare-body 429. (Router-included routes are NOT reached by the default
        limit at all on the pinned stack -- see TestW19cMeasuredRouterExemption.)"""
        module = _fresh_main(monkeypatch, flag_on=True)
        client = TestClient(module.app)
        responses = _drive(client, path, DEFAULT_LIMIT_PER_MINUTE + 1)
        assert responses[0].status_code in (200, 204), (path, responses[0].status_code)
        _assert_contract_429(responses[-1])


class TestW19cMeasuredRouterExemption:
    """MEASUREMENT PIN (green today) -- records a SPEC DISAGREEMENT for the
    orchestrator; it is not a behaviour the fix should preserve by choice.

    The adversary report and the ruling speak of "the 21 default-limited
    routes". On the PINNED stack (fastapi 0.141.1 / starlette 1.6.0 /
    slowapi 0.1.10) ``app.routes`` holds 14 ``_IncludedRouter`` entries with
    no ``.endpoint``; slowapi's ``_find_route_handler`` therefore returns None
    for every router-included path and ``_should_exempt(None)`` is True -- in
    BOTH ``SlowAPIMiddleware`` and ``SlowAPIASGIMiddleware``. Only the three
    app-level routes (``/health``, ``/``, ``/favicon.ico``) ever meet the
    blanket default. Measured: flag ON, ``GET /api/v1/app/version`` x 11 is
    200 x 11 today AND with the ASGI middleware swapped in.

    If the orchestrator rules that the router routes MUST carry the default
    limit, that is a different design (a handler lookup that descends into
    ``_IncludedRouter``) and THIS class is the one to invert.
    """

    @pytest.mark.parametrize(
        "path", ["/api/v1/app/version", "/api/v1/legal/privacy", "/api/v1/usage/status"]
    )
    def test_slowapi_cannot_resolve_a_router_route_handler(self, path):
        from slowapi.middleware import _find_route_handler

        scope = {
            "type": "http", "path": path, "method": "GET", "root_path": "",
            "headers": [], "query_string": b"",
        }
        assert _find_route_handler(app_main.app.routes, scope) is None

    @pytest.mark.parametrize("path", ["/health", "/", "/favicon.ico"])
    def test_slowapi_resolves_the_app_level_routes(self, path):
        from slowapi.middleware import _find_route_handler

        scope = {
            "type": "http", "path": path, "method": "GET", "root_path": "",
            "headers": [], "query_string": b"",
        }
        assert _find_route_handler(app_main.app.routes, scope) is not None

    def test_router_route_is_not_default_limited_flag_on(self, monkeypatch):
        module = _fresh_main(monkeypatch, flag_on=True)
        client = TestClient(module.app)
        statuses = [r.status_code for r in _drive(client, "/api/v1/app/version", 12)]
        assert statuses == [200] * 12, statuses


# ===========================================================================
# PINS -- flag OFF is byte-identical; flag-ON decorated routes are unchanged
# ===========================================================================


class TestW19cFlagOffIdentity:
    """PINS (green today and must stay green): no rate-limit middleware at all."""

    EXPECTED_STACK = [
        "RequestIDMiddleware",
        "SecurityHeadersMiddleware",
        "ErrorHandlerMiddleware",
        "CORSMiddleware",
    ]

    def test_imported_app_has_no_rate_limit_middleware(self):
        assert _middleware_names(app_main.app) == self.EXPECTED_STACK

    def test_fresh_exec_flag_off_matches_the_imported_app(self, monkeypatch):
        module = _fresh_main(monkeypatch, flag_on=False)
        assert _middleware_names(module.app) == self.EXPECTED_STACK

    @pytest.mark.parametrize("value", ["", "0", "false", "off", "no"])
    def test_falsy_flag_values_register_nothing(self, monkeypatch, value):
        module = _fresh_main(monkeypatch, flag_on=False, flag_value=value)
        assert _middleware_names(module.app) == self.EXPECTED_STACK

    def test_undecorated_routes_are_never_throttled_flag_off(self, monkeypatch):
        module = _fresh_main(monkeypatch, flag_on=False)
        client = TestClient(module.app)
        for path in ("/health", "/api/v1/app/version"):
            statuses = [r.status_code for r in _drive(client, path, 15)]
            assert statuses == [200] * 15, (path, statuses)

    def test_health_payload_flag_off_is_unchanged(self, monkeypatch):
        module = _fresh_main(monkeypatch, flag_on=False)
        resp = TestClient(module.app).get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["message"] == "Qaren API is running"
        assert "retry-after" not in resp.headers
        assert not any(h.lower().startswith("x-ratelimit") for h in resp.headers)


class TestW19cFlagOnPins:
    """PINS (green today under SlowAPIMiddleware; must stay green under the
    ASGI middleware): what the swap must NOT change."""

    def test_successful_default_limited_response_has_no_ratelimit_headers(self, monkeypatch):
        """headers_enabled stays False: no X-RateLimit-* / Retry-After on a 200."""
        module = _fresh_main(monkeypatch, flag_on=True)
        resp = TestClient(module.app).get("/health")
        assert resp.status_code == 200
        assert "retry-after" not in resp.headers
        assert not any(h.lower().startswith("x-ratelimit") for h in resp.headers)

    def test_default_limit_still_fires_at_the_eleventh_call(self, monkeypatch):
        """The limit value and key are unchanged: 10 pass, the 11th is 429."""
        module = _fresh_main(monkeypatch, flag_on=True)
        client = TestClient(module.app)
        statuses = [r.status_code for r in _drive(client, "/health", 12)]
        assert statuses == [200] * 10 + [429, 429], statuses

    def test_router_decorated_route_is_unreachable_by_the_default_and_keeps_its_contract(
        self, monkeypatch
    ):
        """FIX-ROUND-2 rewrite (the old name claimed "exempt because
        decorated", which is vacuous on the pinned stack). What IS true on
        fastapi 0.141.1 / slowapi 0.1.10, and what this pins:

        (1) POST /api/v1/feedback is a ROUTER route. slowapi's
            _find_route_handler returns None for it (the _IncludedRouter entry
            has no .endpoint), so the middleware never reaches it at all -- it
            is exempted as UNRESOLVABLE, whether or not it is decorated. The
            decorator-exemption branch (_route_limits) is never consulted.
        (2) Its OWN @limiter.limit("30/minute") contract holds with the flag
            ON: 30 x 200 (so no 10/min default ever applied), then a 429 with
            the envelope + Retry-After from the decorator path.
        """
        from slowapi.middleware import _find_route_handler

        import app.api.feedback_routes as feedback_routes

        monkeypatch.setattr(feedback_routes, "save_feedback", AsyncMock(return_value=None))

        def _discard(coro, *args, **kwargs):
            coro.close()

        monkeypatch.setattr(feedback_routes, "fire_and_forget", _discard)
        module = _fresh_main(monkeypatch, flag_on=True)
        scope = {
            "type": "http", "path": "/api/v1/feedback", "method": "POST",
            "root_path": "", "headers": [], "query_string": b"",
        }
        assert _find_route_handler(module.app.routes, scope) is None, (
            "slowapi now resolves a router route: the blanket default can reach "
            "router routes, so the W1-9d / single-chunk analysis must be redone"
        )
        client = TestClient(module.app)
        responses = _drive(client, "/api/v1/feedback", 31, method="post", json={"useful": True})
        statuses = [r.status_code for r in responses]
        assert statuses[:30] == [200] * 30, statuses
        _assert_contract_429(responses[30])


# ===========================================================================
# STATED LIMIT (fix round 2): SlowAPIASGIMiddleware on the pinned slowapi
# 0.1.10 re-sends the held http.response.start before EVERY body message, so a
# MULTI-CHUNK response on a route the default limiter reaches breaks with the
# flag ON. Accepted as a stated limit (follow-up W1-9d) because every route the
# default limiter can reach today is single-chunk -- pinned here.
# ===========================================================================


# The app-level routes the blanket default can reach. On Railway
# (RAILWAY_ENVIRONMENT set) docs, ReDoc and the OpenAPI schema are disabled
# (M13-21), so it is exactly these three; locally and in this suite the four
# FastAPI docs routes are registered too and are reachable as well.
_REACHABLE_ON_RAILWAY = {"/health", "/", "/favicon.ico"}
_DOCS_ROUTES = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def _asgi_messages(asgi_app, path: str) -> list:
    """Drive one GET through the raw ASGI app and return every sent message."""
    import asyncio

    sent: list = []
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": path, "raw_path": path.encode(),
        "root_path": "", "query_string": b"", "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000), "server": ("testserver", 80),
    }

    delivered: list = []

    async def receive():
        # The request body once; afterwards park like a live client (a
        # StreamingResponse listens for disconnect and is cancelled when done).
        if not delivered:
            delivered.append(True)
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.Event().wait()

    async def send(message):
        sent.append(message)

    # A private loop, never installed as the thread's current loop, so no
    # later test inherits (or loses) an event loop because of this helper.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(asgi_app(scope, receive, send))
    finally:
        loop.close()
    return sent


def _default_limiter_reachable_paths(app) -> set:
    """Every app-level route slowapi's _find_route_handler can resolve and
    _should_exempt does not exempt: the exact set the blanket default meets."""
    from slowapi.middleware import _should_exempt

    paths = set()
    for route in app.routes:
        if not hasattr(route, "endpoint"):
            continue  # _IncludedRouter / Mount: unresolvable -> exempt
        if not _should_exempt(app.state.limiter, route.endpoint):
            paths.add(route.path)
    return paths


def _messages_into_slowapi(app, path: str) -> tuple[list, list]:
    """Drive one GET through the flag-ON app with a recorder spliced in
    DIRECTLY under SlowAPIASGIMiddleware. Returns (the messages the middleware
    RECEIVED from the app below it, the messages the whole app SENT). The
    outer BaseHTTPMiddleware layers (ErrorHandler, SecurityHeaders, RequestID)
    re-frame the body, so only the inner boundary shows the chunking the
    middleware actually has to handle."""
    from slowapi.middleware import SlowAPIASGIMiddleware

    if app.middleware_stack is None:
        app.middleware_stack = app.build_middleware_stack()
    node = app.middleware_stack
    while node is not None and not isinstance(node, SlowAPIASGIMiddleware):
        node = getattr(node, "app", None)
    assert node is not None, "SlowAPIASGIMiddleware not found in the built stack"
    inner = node.app
    received: list = []

    async def recorder(scope, receive, send):
        async def recording_send(message):
            received.append(message)
            await send(message)

        await inner(scope, receive, recording_send)

    node.app = recorder
    try:
        outer = _asgi_messages(app, path)
    finally:
        node.app = inner
    return received, outer


class TestW19cStatedLimitSingleChunk:
    def test_on_railway_the_default_limiter_reaches_only_three_app_level_routes(
        self, monkeypatch
    ):
        """Production config. If this set grows (an undecorated app-level route,
        or slowapi learning to see through _IncludedRouter), prove the new
        route single-chunk before widening it -- see follow-up W1-9d."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        module = _fresh_main(monkeypatch, flag_on=True)
        assert _default_limiter_reachable_paths(module.app) == _REACHABLE_ON_RAILWAY

    def test_off_railway_only_the_docs_routes_are_added(self, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        module = _fresh_main(monkeypatch, flag_on=True)
        assert _default_limiter_reachable_paths(module.app) == (
            _REACHABLE_ON_RAILWAY | _DOCS_ROUTES
        )

    @pytest.mark.parametrize("path", sorted(_REACHABLE_ON_RAILWAY | _DOCS_ROUTES))
    def test_every_reachable_route_is_single_chunk_under_the_asgi_middleware(
        self, monkeypatch, path
    ):
        """Flag ON: the app below SlowAPIASGIMiddleware answers every reachable
        route with exactly one http.response.start and exactly one
        http.response.body (no more_body) -- the only shape the pinned
        middleware passes through intact -- and the whole app sends exactly
        one start with a 200/204."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        module = _fresh_main(monkeypatch, flag_on=True)
        assert "SlowAPIASGIMiddleware" in _middleware_names(module.app)
        received, outer = _messages_into_slowapi(module.app, path)
        kinds = [m["type"] for m in received]
        assert kinds == ["http.response.start", "http.response.body"], (path, kinds)
        assert not received[1].get("more_body", False), path
        outer_starts = [m for m in outer if m["type"] == "http.response.start"]
        assert len(outer_starts) == 1, (path, [m["type"] for m in outer])
        assert outer_starts[0]["status"] in (200, 204), (path, outer_starts[0]["status"])

    def test_pinned_slowapi_breaks_a_multi_chunk_non_exempt_response(self):
        """MEASUREMENT PIN of the stated limit, on a scratch app (not ours):
        a 2-chunk StreamingResponse on a default-limited route makes the pinned
        SlowAPIASGIMiddleware emit http.response.start TWICE. If slowapi is
        upgraded and this goes red, the limit is gone and W1-9d can drop it."""
        from fastapi import FastAPI
        from fastapi.responses import StreamingResponse
        from slowapi import Limiter
        from slowapi.middleware import SlowAPIASGIMiddleware
        from slowapi.util import get_remote_address

        scratch = FastAPI()
        scratch.state.limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
        scratch.add_middleware(SlowAPIASGIMiddleware)

        @scratch.get("/stream")
        async def stream():
            async def gen():
                yield b"chunk-1\n"
                yield b"chunk-2\n"

            return StreamingResponse(gen(), media_type="text/plain")

        kinds = [m["type"] for m in _asgi_messages(scratch, "/stream")]
        assert kinds.count("http.response.start") >= 2, kinds
