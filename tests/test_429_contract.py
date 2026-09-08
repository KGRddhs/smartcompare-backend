"""W1-9 — a 429 that tells the client when to come back.

Findings ``LS-FAILURE-MODES-COST-12`` / ``LS-RATELIMIT-KEY-08``. Backend half.

The defect: ``app/middleware/error_handler.py::rate_limit_handler`` builds its
own envelope and never emits ``Retry-After`` nor a ``retry_after_seconds`` body
field, so a client that trips a limit — the first thing a launch-day spike
produces — has no idea when to come back and either hammers or gives up.

MEASURED on the slowapi ACTUALLY INSTALLED here (**0.1.9**; ``requirements.txt``
pins **0.1.10** — local-vs-lock drift, so CI settles the pinned number):

* ``request.state.view_rate_limit`` IS populated when our handler runs, in the
  REAL app on a REAL decorated route. Shape is a 2-tuple
  ``(RateLimitItemPerMinute, ['<key>', '<scope>'])`` — e.g.
  ``(3 per 1 minute, ['testclient', '/api/v1/auth/password-reset'])`` — and
  ``limiter.limiter.get_window_stats(item, *args)`` returns
  ``WindowStats(reset_time=<epoch float>, remaining=0)``.
  (slowapi sets it in ``__evaluate_limits`` BEFORE raising ``RateLimitExceeded``.)
* slowapi's own ``Retry-After`` is **delta-seconds**, not an epoch: with
  ``headers_enabled=True`` a 3/minute route emitted ``retry-after: 60`` while
  ``x-ratelimit-reset`` was the epoch ``1788874500.96``. Its formula is
  ``int((1 + reset_time) - time.time())``.

⚠ ONE MEASURED DISAGREEMENT WITH THE SPEC, recorded not worked around: the spec
says the delta must be "a positive integer ≤ the window length". slowapi's own
formula carries a deliberate ``+1`` rounding-up guard, so on a 60 s window it
yields **61** most of the time — sampled 60 fresh windows on a 1/minute route:
``{60: 10, 61: 50}``. Matching slowapi exactly (which the spec's own "compute
the retry window the same way slowapi does" instruction requires) therefore
cannot satisfy ``<= 60``. These tests bound the value at ``window + 1`` and say
so; an implementation may also clamp to the window — both pass.

Blast-radius ruling pinned by ``test_successful_response_carries_no_ratelimit_headers``:
we must NOT flip ``headers_enabled=True`` on the Limiter. Measured why — with it
on, the **200** response also carried ``x-ratelimit-limit/remaining/reset`` AND
``retry-after: 61``, i.e. a response-shape change across every limited route.

Free tier: no network. The route's service call is mocked; the limiter uses
in-memory storage and conftest's autouse ``_reset_rate_limiter`` gives each test
a clean window.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.rate_limiter import limiter

# POST /api/v1/auth/password-reset is decorated @limiter.limit("3/minute"),
# takes no auth dependency, and its only side effect is one awaited service
# call we mock. So the 4th call in a window is a pure 429 from the handler
# under test, with no paid work and no live Supabase call.
_ROUTE = "/api/v1/auth/password-reset"
_BODY = {"email": "w19-429-contract@example.com"}
_LIMIT_AMOUNT = 3
_WINDOW_SECONDS = 60  # "3/minute"; measured via view_rate_limit[0].get_expiry()


@pytest.fixture()
def client(monkeypatch):
    """TestClient on the REAL app with the route's service call mocked."""
    monkeypatch.setattr(
        "app.api.auth_routes.request_password_reset",
        AsyncMock(return_value={"success": True, "message": "sent"}),
    )
    with TestClient(app) as tc:
        yield tc


def _drive_to_429(client):
    """Spend the window and return (successful_responses, first_429)."""
    oks = []
    for _ in range(_LIMIT_AMOUNT + 3):
        resp = client.post(_ROUTE, json=_BODY)
        if resp.status_code == 429:
            return oks, resp
        assert resp.status_code == 200, (
            f"unexpected pre-429 status {resp.status_code}: {resp.text}"
        )
        oks.append(resp)
    raise AssertionError(
        f"route never 429'd after {_LIMIT_AMOUNT + 3} calls — limiter not engaged"
    )


def _header(resp, name):
    """Case-insensitive header lookup returning None when absent."""
    for k, v in resp.headers.items():
        if k.lower() == name.lower():
            return v
    return None


# ---------------------------------------------------------------- test 1 (RED)
def test_429_carries_retry_after_header(client):
    """A limited route pushed past its limit answers 429 with a Retry-After
    header that parses as a positive integer bounded by the window.

    RED today: the header is absent entirely (measured — today's 429 carries
    only the request-id and the security headers).

    The bound is ``window + 1``, not ``window``: see the module docstring's
    recorded spec disagreement. A delta-seconds value is what RFC 7231 requires;
    an epoch (~1.78e9) would be worse than no header at all, and the upper bound
    is what rejects it.
    """
    _oks, resp = _drive_to_429(client)

    raw = _header(resp, "Retry-After")
    assert raw is not None, (
        "429 carries no Retry-After header — the client has no idea when to "
        f"come back. Headers seen: {dict(resp.headers)}"
    )

    try:
        seconds = int(raw)
    except (TypeError, ValueError):  # pragma: no cover — asserted below
        pytest.fail(
            f"Retry-After must be delta-seconds per RFC 7231, got {raw!r}. An "
            "HTTP-date would also be legal but the client half expects an int."
        )

    assert seconds > 0, f"Retry-After must be positive, got {seconds}"
    assert seconds <= _WINDOW_SECONDS + 1, (
        f"Retry-After {seconds} exceeds the {_WINDOW_SECONDS}s window (+1 for "
        "slowapi's rounding guard) — that smells like an epoch, not a delta"
    )


# ---------------------------------------------------------------- test 2 (RED)
def test_429_body_carries_retry_after_seconds_equal_to_header(client):
    """The body carries ``retry_after_seconds``, an int equal to the header.

    RED today: the key is absent from the envelope.

    Equality is the real assertion — it forces ONE computation feeding both
    surfaces. Two independent ``time.time()`` reads would disagree by 1 at a
    second boundary and hand the client two different answers.
    """
    _oks, resp = _drive_to_429(client)
    body = resp.json()

    assert "retry_after_seconds" in body, (
        f"429 body has no retry_after_seconds: {body}"
    )
    value = body["retry_after_seconds"]
    assert isinstance(value, int) and not isinstance(value, bool), (
        f"retry_after_seconds must be an int, got {type(value).__name__}: {value!r}"
    )
    assert value > 0, f"retry_after_seconds must be positive, got {value}"

    raw = _header(resp, "Retry-After")
    assert raw is not None, "header missing — see test 1"
    assert int(raw) == value, (
        f"header Retry-After={raw!r} disagrees with body "
        f"retry_after_seconds={value} — compute the window ONCE"
    )


# ------------------------------------------------------------ test 3 (PIN)
def test_429_envelope_shape_is_preserved(client):
    """The unified envelope is additive-only: ``success`` false, ``error``,
    ``code``, ``request_id`` all survive.

    ``code`` stays whatever the 429 path emits today — ``STATUS_CODE_MAP[429]``
    is ``RATE_LIMITED`` (measured on the live response).

    Green today; it is here to fail if the fix rebuilds the response instead of
    extending it.
    """
    _oks, resp = _drive_to_429(client)
    body = resp.json()

    assert body.get("success") is False, body
    assert isinstance(body.get("error"), str) and body["error"], body
    assert body.get("code") == "RATE_LIMITED", body
    assert isinstance(body.get("request_id"), str) and body["request_id"], body
    # request_id must be the real one from the middleware, echoed in the header.
    assert body["request_id"] == _header(resp, "X-Request-ID"), body


# ------------------------------------------------------- test 4a (fail-safe)
def test_window_stats_failure_still_returns_todays_429(client, monkeypatch):
    """Fail-safe: if the window stats cannot be read, the response is today's
    exact 429 — same envelope, no header, and never a 500.

    A rate-limit response must never become a server error. This is the
    ``try/except`` the spec's mutation check removes.

    NOTE (honest): with no implementation this passes vacuously — nothing reads
    window stats yet, so nothing can raise. ``test_handler_reads_window_stats``
    below is the non-vacuous half and IS red today.
    """
    boom_calls = []

    def _boom(*args, **kwargs):
        boom_calls.append(args)
        raise RuntimeError("storage unreachable")

    monkeypatch.setattr(limiter.limiter, "get_window_stats", _boom, raising=False)

    _oks, resp = _drive_to_429(client)

    assert resp.status_code == 429, (
        f"window-stats failure escalated to {resp.status_code} — a rate-limit "
        f"response must never 500. Body: {resp.text}"
    )
    body = resp.json()
    assert body.get("success") is False, body
    assert body.get("code") == "RATE_LIMITED", body
    assert isinstance(body.get("error"), str) and body["error"], body
    assert isinstance(body.get("request_id"), str) and body["request_id"], body
    assert _header(resp, "Retry-After") is None, (
        "a Retry-After was emitted even though the window stats raised — the "
        "value cannot be trustworthy"
    )
    assert "retry_after_seconds" not in body, (
        f"retry_after_seconds present despite unreadable window stats: {body}"
    )


# ------------------------------------------------------ test 4b (RED, non-vacuous)
def test_handler_reads_window_stats(client, monkeypatch):
    """The 429 path actually consults the limiter's window stats.

    RED today: ``rate_limit_handler`` reads nothing — it returns a constant
    message — so ``get_window_stats`` is never called on the 429 path.

    This is what makes the fail-safe test above mean something. It also pins the
    SOURCE of the number: the real remaining window from the limiter's storage,
    which is how slowapi's own ``_inject_headers`` computes it. Deriving the
    delta from ``RateLimitExceeded.limit``'s expiry instead would always report
    the FULL window rather than the time actually left, which is a different and
    wrong answer.
    """
    calls = []
    real = limiter.limiter.get_window_stats

    def _spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(limiter.limiter, "get_window_stats", _spy, raising=False)

    _oks, resp = _drive_to_429(client)

    assert resp.status_code == 429, resp.text
    assert calls, (
        "get_window_stats was never called while building the 429 — the handler "
        "is not reading the real retry window from the limiter's storage"
    )


# ------------------------------------------------------------ test 5 (PIN)
def test_successful_response_carries_no_ratelimit_headers(client):
    """Blast-radius ruling: a SUCCESSFUL response on a limited route carries no
    ``X-RateLimit-*`` and no ``Retry-After``.

    Green today; it must stay green. It fails the moment someone "fixes" this
    unit by flipping ``headers_enabled=True`` on the Limiter — measured, that
    injects ``x-ratelimit-limit/remaining/reset`` AND ``retry-after: 61`` onto
    every 200 of every limited route, a response-shape change across 60+
    endpoints for a unit that is about the 429.
    """
    oks, _resp429 = _drive_to_429(client)
    assert oks, "no successful response captured before the 429"

    for ok in oks:
        leaked = sorted(
            k for k in ok.headers.keys() if k.lower().startswith("x-ratelimit")
        )
        assert not leaked, (
            f"successful response leaked rate-limit headers {leaked} — the "
            "Limiter's headers_enabled must stay OFF"
        )
        assert _header(ok, "Retry-After") is None, (
            "successful response carries Retry-After — headers_enabled leaked "
            "onto the 200 path"
        )

# ============================================================ lockout path
# Ruling 4 in the spec's FABLE RULINGS (binding) + the adversary's major:
# the app's SECOND 429 class -- the brute-force account lockout raised by
# POST /auth/login, PUT /auth/email and PUT /auth/password via
# `_account_locked_response` -- computes its own retry window, puts it in the
# structured HTTPException detail as `retry_after`, and `http_exception_handler`
# silently dropped it (measured: the 300 never reached the wire). Same finding,
# second path, on the credential routes where a hammering client matters most.
# The client half (W3-14) needs ONE contract, so the lockout 429 must emit the
# SAME `Retry-After` header and `retry_after_seconds` body field as the
# slowapi path above -- never a second field name.

import asyncio
import json
import time

from fastapi import HTTPException
from starlette.requests import Request as _StarletteRequest

from app.middleware.error_handler import http_exception_handler


def _bare_request():
    """A minimal Starlette Request whose state carries no request_id."""
    return _StarletteRequest(
        {"type": "http", "method": "GET", "path": "/x", "headers": [], "query_string": b""}
    )


def _handle(status, detail):
    """Run http_exception_handler directly and return (status, headers, body)."""
    resp = asyncio.run(http_exception_handler(_bare_request(), HTTPException(status, detail=detail)))
    return resp.status_code, {k.lower(): v for k, v in resp.headers.items()}, json.loads(resp.body)


# ---------------------------------------------------------------- lockout (RED)
def test_lockout_429_carries_the_same_retry_after_contract(client, monkeypatch):
    """POST /auth/login while the account is locked answers 429 ACCOUNT_LOCKED
    with `Retry-After: 300` and `retry_after_seconds: 300` -- the value the
    route already computed. RED today: http_exception_handler drops it.

    Drives the REAL route with only the lockout check mocked, so the 429 comes
    from the real raise site and the real handler.
    """
    monkeypatch.setattr(
        "app.api.auth_routes.check_account_locked",
        AsyncMock(return_value={"locked": True, "retry_after": 300}),
    )
    # The lockout branch fires an audit write; stub it so this test can never
    # reach a real Supabase client (it produced a live getaddrinfo without this).
    monkeypatch.setattr("app.api.auth_routes.log_audit_event", AsyncMock(return_value=None))
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "w19-locked@example.com", "password": "Whatever123"},
    )
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert body.get("code") == "ACCOUNT_LOCKED", body
    assert body.get("success") is False, body
    assert isinstance(body.get("error"), str) and body["error"], body
    assert isinstance(body.get("request_id"), str) and body["request_id"], body
    assert _header(resp, "Retry-After") == "300", (
        f"lockout 429 lost its retry window: headers={dict(resp.headers)}"
    )
    assert body.get("retry_after_seconds") == 300, body


# ------------------------------------------------------- lockout pins (green)
def test_structured_429_without_retry_after_is_unchanged():
    """A structured 429 detail that carries no retry_after gets today's exact
    envelope: no header, no field. The addition is strictly additive."""
    status, headers, body = _handle(429, {"error": "slow down", "code": "THROTTLED"})
    assert status == 429
    assert body == {"success": False, "error": "slow down", "code": "THROTTLED", "request_id": "unknown"}
    assert "retry-after" not in headers


def test_non_429_detail_with_a_stray_retry_after_is_ignored():
    """retry_after is only meaningful on a 429; a 400 carrying one by accident
    must not grow a Retry-After header."""
    status, headers, body = _handle(400, {"error": "bad", "code": "BAD_INPUT", "retry_after": 30})
    assert status == 400
    assert "retry-after" not in headers
    assert "retry_after_seconds" not in body


@pytest.mark.parametrize("bad", [0, -5, "soon", True, 3.5, None])
def test_lockout_429_with_an_unusable_retry_after_says_nothing(bad):
    """Only a positive int is a retry window. Zero, negatives, strings, bools
    (a bool IS an int in Python -- excluded on purpose), floats and None all
    degrade to today's 429 rather than shipping a lie."""
    status, headers, body = _handle(429, {"error": "locked", "code": "ACCOUNT_LOCKED", "retry_after": bad})
    assert status == 429
    assert body.get("code") == "ACCOUNT_LOCKED"
    assert "retry-after" not in headers, headers
    assert "retry_after_seconds" not in body, body


# --------------------------------------------- sanity-guard pins (adversary minor)
def test_storage_epoch_is_refused_not_shipped(client, monkeypatch):
    """If the limiter's storage ever reports an EPOCH instead of a reset time,
    the delta would be ~1.7e9 seconds. That is worse than no header at all
    (the spec's own words), so the guard must say nothing. Pinned because
    deleting the guard left the suite green (adversary, reproduced)."""
    monkeypatch.setattr(
        limiter.limiter, "get_window_stats",
        lambda *a, **k: (time.time() + 1_700_000_000, 0), raising=False,
    )
    _oks, resp = _drive_to_429(client)
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert body.get("code") == "RATE_LIMITED", body
    assert _header(resp, "Retry-After") is None, dict(resp.headers)
    assert "retry_after_seconds" not in body, body


def test_already_elapsed_window_is_refused_not_shipped(client, monkeypatch):
    """A reset time already in the past would yield a zero or negative delta.
    Never ship it -- serve today's 429 without a window."""
    monkeypatch.setattr(
        limiter.limiter, "get_window_stats",
        lambda *a, **k: (time.time() - 5, 0), raising=False,
    )
    _oks, resp = _drive_to_429(client)
    assert resp.status_code == 429, resp.text
    assert resp.json().get("code") == "RATE_LIMITED"
    assert _header(resp, "Retry-After") is None, dict(resp.headers)
    assert "retry_after_seconds" not in resp.json()

