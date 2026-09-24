"""Retro-fix R-MAIN / W1-1b + W1-1c -- RED phase.

Spec: the retroactive adversary report on W1-1 (PR #142, "admin key + Sentry
scrub"), plus the orchestrator's binding rulings for this group:

  W1-1b (BLOCKING, live, UNFLAGGED): ``init_sentry`` passes
      ``before_send_transaction`` and that hook applies the SAME request-region
      scrub as ``_before_send`` -- so a sampled performance TRANSACTION never
      carries ``X-Admin-Key`` (nor a bare ``Authorization`` / ``Cookie``).
      ``_before_send`` is never called for transactions, and the SDK's own
      header filter (sentry-sdk 2.68.1 ``SENSITIVE_HEADERS``) does not list
      ``x-admin-key``. Re-measured here on the pinned venv: with the REAL
      ``init_sentry()`` and an in-memory transport, ``GET
      /api/v1/admin/stats/daily`` and ``GET /admin/cohort.html`` with the
      correct ``X-Admin-Key`` each ship a transaction whose
      ``request.headers["x-admin-key"]`` is the key verbatim.

  W1-1c (UNFLAGGED): the ``/admin/*`` mount's Basic branch catches
      ``ValueError`` / ``UnicodeError`` (``binascii.Error`` is a SUBCLASS of
      ``ValueError``, not the reverse) so a raw >= 0x80 byte in the Basic
      payload never 500s. Re-measured: ``b"Basic \\xff\\xfe"``,
      ``b"Basic \\xc3\\xa9"`` and ``b"basic \\xff"`` each return 500 with
      ``ValueError: string argument should contain only ASCII characters``
      raised from ``base64.b64decode`` at ``app/main.py`` (``__call__``).

Every RED test fails on an assertion about behaviour that is absent today; the
PIN tests pass today and must keep passing after GREEN.

Zero network: an autouse guard blocks every non-loopback ``connect`` and every
non-loopback ``getaddrinfo`` and fails the test on any attempt. The end-to-end
Sentry run happens in a CHILD process (the SDK's Starlette/FastAPI integrations
patch framework classes process-wide and cannot be undone, so they must never
be installed in the shared pytest process); the child installs the same guard
and reports every attempt back, and the parent fails on any.
"""
from __future__ import annotations

import base64
import copy
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# NO module-level binding of any app.services.sentry_service attribute (fix
# round 2). tests/test_observability.py -- which sorts BEFORE this file in
# CI's alphabetical `pytest tests/` order -- calls
# importlib.reload(app.services.sentry_service), which rebinds _before_send /
# init_sentry to NEW function objects in the same module object. A name
# imported here at collection time would then be the stale pre-reload object
# and every identity assert against init_sentry's kwargs would fail. Every
# attribute is therefore read through the module object at CALL time.


def _sentry_module():
    """The live app.services.sentry_service module (same object across reloads)."""
    import importlib

    return importlib.import_module("app.services.sentry_service")


def _before_send(event, hint):
    """Call the CURRENT sentry_service._before_send (resolved at call time)."""
    return _sentry_module()._before_send(event, hint)


REPO_ROOT = Path(__file__).resolve().parents[1]

# A NON-hex, non-JWT admin key, so the generic pattern scrub
# (``[a-f0-9]{32,}``, JWT, sk-proj, fc-) cannot hide a miss: only a
# header-name redaction removes it.
PROBE_KEY = "PROBEadminKEY_zz9-notHex-Q"
TRACE_ID = "4c1f8e2a9b3d4c5e6f708192a3b4c5d6"  # 32 lowercase hex, like uuid4().hex
SPAN_ID = "a1b2c3d4e5f60718"


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


def _captured_init_kwargs(monkeypatch) -> dict:
    """Call the REAL init_sentry() with sentry_sdk.init replaced by a recorder."""
    import sentry_sdk

    sentry_service = _sentry_module()

    captured: dict = {}

    def fake_init(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setenv("SENTRY_DSN", "https://public@o0.ingest.sentry.io/1")
    monkeypatch.setattr(sentry_sdk, "init", fake_init)
    sentry_service.init_sentry()
    assert captured, "init_sentry did not call sentry_sdk.init"
    return captured


def _transaction_hook(monkeypatch):
    hook = _captured_init_kwargs(monkeypatch).get("before_send_transaction")
    if hook is None:
        pytest.fail(
            "init_sentry passes no before_send_transaction, so a sampled "
            "performance transaction reaches Sentry with request.headers "
            "untouched by our scrub -- X-Admin-Key ships verbatim (W1-1b)."
        )
    assert callable(hook), f"before_send_transaction is not callable: {hook!r}"
    return hook


def _transaction_event(headers: dict | None = None, status_code: int = 200) -> dict:
    """A transaction event in the shape sentry-sdk 2.68.1 builds for an ASGI request."""
    return {
        "type": "transaction",
        "transaction": "app.api.admin_routes.daily_stats",
        "transaction_info": {"source": "component"},
        "contexts": {
            "trace": {
                "trace_id": TRACE_ID,
                "span_id": SPAN_ID,
                "parent_span_id": "0f1e2d3c4b5a6978",
                "op": "http.server",
                "status": "ok",
                "origin": "auto.http.starlette",
            },
            "response": {"status_code": status_code},
        },
        "request": {
            "url": "http://testserver/api/v1/admin/stats/daily",
            "query_string": "q=my%20private%20search&limit=5",
            "method": "GET",
            "headers": dict(
                headers
                if headers is not None
                else {
                    "X-Admin-Key": PROBE_KEY,
                    "Authorization": f"Basic {PROBE_KEY}",
                    "Cookie": f"sid={PROBE_KEY}",
                    "User-Agent": "probe/1.0",
                    "host": "testserver",
                }
            ),
        },
        "spans": [
            {
                "trace_id": TRACE_ID,
                "span_id": "1122334455667788",
                "parent_span_id": SPAN_ID,
                "op": "middleware.starlette",
                "description": "RequestIDMiddleware",
            }
        ],
        "start_timestamp": 1790000000.0,
        "timestamp": 1790000000.25,
    }


# ===========================================================================
# W1-1b -- unit level: the hook exists, is wired, and scrubs the request region
# ===========================================================================


class TestW11bTransactionHookIsWired:
    def test_init_sentry_passes_before_send_transaction(self, monkeypatch):
        """RED today: init_sentry passes before_send only."""
        kwargs = _captured_init_kwargs(monkeypatch)
        assert kwargs.get("before_send_transaction") is not None, (
            "init_sentry does not pass before_send_transaction; transactions "
            "bypass _before_send entirely (measured on sentry-sdk 2.68.1)."
        )
        assert callable(kwargs["before_send_transaction"])

    def test_other_init_options_are_unchanged(self, monkeypatch):
        """PIN (green today): the error-event hook and every other option stay."""
        kwargs = _captured_init_kwargs(monkeypatch)
        # Resolved through the module NOW, not at collection time: a reload by
        # an earlier test file must not break this identity (fix round 2).
        assert kwargs["before_send"] is _sentry_module()._before_send
        assert kwargs["include_local_variables"] is False
        assert kwargs["send_default_pii"] is False
        assert kwargs["traces_sample_rate"] == 0.1
        assert kwargs["before_breadcrumb"] is not None
        for integration in kwargs["integrations"]:
            codes = getattr(integration, "failed_request_status_codes", None)
            if codes is not None:
                assert 503 not in codes and 500 in codes


class TestW11bTransactionHookScrubsTheRequestRegion:
    @pytest.mark.parametrize(
        "header_name",
        [
            "X-Admin-Key",
            "x-admin-key",
            "X-ADMIN-KEY",
            "Authorization",
            "authorization",
            "Cookie",
            "cookie",
        ],
    )
    def test_sensitive_header_is_redacted_case_insensitively(self, monkeypatch, header_name):
        """RED today (no hook). Same names, same case-insensitivity, same
        '[REDACTED]' marker as _before_send's header scrub."""
        hook = _transaction_hook(monkeypatch)
        event = _transaction_event({header_name: PROBE_KEY, "User-Agent": "probe/1.0"})
        out = hook(event, {})
        assert out is not None, "the hook dropped the transaction instead of scrubbing it"
        assert out["request"]["headers"][header_name] == "[REDACTED]"
        assert PROBE_KEY not in json.dumps(out)

    def test_request_region_matches_before_send(self, monkeypatch):
        """RED today. 'The same request-region scrub': whatever _before_send
        does to event['request'], the transaction hook does identically, so
        the two can never drift."""
        hook = _transaction_hook(monkeypatch)
        event = _transaction_event()
        expected = _before_send(copy.deepcopy(event), {})["request"]
        out = hook(copy.deepcopy(event), {})
        assert out is not None
        assert out["request"] == expected
        # And the scrub is real, not vacuous:
        assert PROBE_KEY not in json.dumps(out["request"])
        assert out["request"]["query_string"] == "q=[QUERY_REDACTED]&limit=5"

    def test_trace_correlation_and_spans_survive(self, monkeypatch):
        """RED today (no hook). A transaction whose trace_id is rewritten to
        [TOKEN_REDACTED] is dropped by Relay -- the scrub must stay in the
        request region and leave the trace, spans and non-secret headers alone."""
        hook = _transaction_hook(monkeypatch)
        event = _transaction_event()
        original = copy.deepcopy(event)
        out = hook(event, {})
        assert out is not None
        assert out["type"] == "transaction"
        assert out["contexts"]["trace"] == original["contexts"]["trace"]
        assert out["spans"] == original["spans"]
        assert out["transaction"] == original["transaction"]
        assert out["request"]["headers"]["User-Agent"] == "probe/1.0"
        assert out["request"]["method"] == "GET"
        assert out["request"]["url"] == original["request"]["url"]

    def test_503_transaction_is_not_dropped(self, monkeypatch):
        """RED today (no hook). _before_send drops 503 ERROR events on purpose;
        that drop must not be applied to performance transactions."""
        hook = _transaction_hook(monkeypatch)
        out = hook(_transaction_event(status_code=503), {})
        assert out is not None, "the 503-drop leaked into the transaction hook"
        assert out["request"]["headers"]["X-Admin-Key"] == "[REDACTED]"


class TestBeforeSendUnchanged:
    """PINS (green today): the error-event hook's behaviour does not move."""

    def test_error_event_headers_still_redacted(self):
        ev = {
            "level": "error",
            "contexts": {"response": {"status_code": 500}},
            "request": {"headers": {"X-Admin-Key": PROBE_KEY, "User-Agent": "u"}},
        }
        out = _before_send(ev, {})
        assert out["request"]["headers"] == {"X-Admin-Key": "[REDACTED]", "User-Agent": "u"}

    def test_error_event_503_still_dropped(self):
        assert _before_send({"contexts": {"response": {"status_code": 503}}}, {}) is None

    def test_error_event_trace_ids_still_restored(self):
        ev = {"contexts": {"trace": {"trace_id": TRACE_ID, "span_id": SPAN_ID}}}
        out = _before_send(ev, {})
        assert out["contexts"]["trace"]["trace_id"] == TRACE_ID
        assert out["contexts"]["trace"]["span_id"] == SPAN_ID


# ===========================================================================
# W1-1b -- end to end through the REAL init_sentry() and the real SDK pipeline
# ===========================================================================

_CHILD = r'''
import ipaddress, json, os, socket, sys
ATTEMPTS = []
def _loop(h):
    if isinstance(h, (bytes, bytearray)): h = bytes(h).decode("latin-1")
    if h in ("localhost", "testserver", "", None): return True
    try: return ipaddress.ip_address(str(h).split("%", 1)[0]).is_loopback
    except ValueError: return False
_c, _cx, _g = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
def _h(a): return a[0] if isinstance(a, tuple) else a
def connect(self, a):
    if not _loop(_h(a)): ATTEMPTS.append(("connect", repr(a))); raise OSError("blocked")
    return _c(self, a)
def connect_ex(self, a):
    if not _loop(_h(a)): ATTEMPTS.append(("connect_ex", repr(a))); raise OSError("blocked")
    return _cx(self, a)
def gai(h, *a, **k):
    if not _loop(h): ATTEMPTS.append(("getaddrinfo", repr(h))); raise OSError("blocked")
    return _g(h, *a, **k)
socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, gai

sys.path.insert(0, os.getcwd())
from tests._env_safety import neutralize_credentials, install_dotenv_guard
neutralize_credentials(); install_dotenv_guard()

import sentry_sdk
from sentry_sdk.transport import Transport
ITEMS = []
class _MemoryTransport(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            ITEMS.append((item.type, item.get_bytes().decode("utf-8", "replace")))
    def flush(self, timeout, callback=None):
        pass
    def kill(self):
        pass
_real_init = sentry_sdk.init
def _init(*a, **kw):
    kw["transport"] = _MemoryTransport
    kw["traces_sample_rate"] = 1.0
    return _real_init(*a, **kw)
sentry_sdk.init = _init

from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import app.main as app_main
import app.api.admin_routes as admin_routes
admin_routes.get_daily_stats = AsyncMock(return_value={"days": []})

# The key travels by ENV, never argv: sentry-sdk's ArgvIntegration copies
# sys.argv into every event's extra.sys.argv (measured), which would be a
# harness-made leak, not a product one.
KEY = os.environ.pop("RETRO_W11B_PROBE_KEY")
os.environ["ADMIN_API_KEY"] = KEY
os.environ["SENTRY_DSN"] = "https://public@o0.ingest.sentry.io/1"
from app.services.sentry_service import init_sentry
init_sentry()
if sentry_sdk.get_client().options.get("transport") is not _MemoryTransport:
    print("RESULT " + json.dumps({"fatal": "real init_sentry() did not initialise the SDK"}))
    sys.exit(0)

import base64
basic = "Basic " + base64.b64encode(("operator:" + KEY).encode()).decode()
CASES = {
    "admin_route_x_admin_key": ("/api/v1/admin/stats/daily", {"X-Admin-Key": KEY}),
    "admin_mount_x_admin_key": ("/admin/cohort.html", {"X-Admin-Key": KEY}),
    "admin_mount_basic": ("/admin/cohort.html", {"Authorization": basic}),
    "bare_authorization_and_cookie": (
        "/health", {"Authorization": "Bearer " + KEY, "Cookie": "sid=" + KEY}),
}
client = TestClient(app_main.app)
out = {}
for name, (path, headers) in CASES.items():
    ITEMS.clear()
    status = client.get(path, headers=headers).status_code
    sentry_sdk.flush()
    txs = []
    for kind, body in ITEMS:
        if kind == "transaction":
            doc = json.loads(body)
            txs.append({
                "trace_id": ((doc.get("contexts") or {}).get("trace") or {}).get("trace_id"),
                "header_names": sorted(((doc.get("request") or {}).get("headers") or {}).keys()),
            })
    out[name] = {
        "status": status,
        "items": [[kind, KEY in body] for kind, body in ITEMS],
        "transactions": txs,
    }
out["_network_attempts"] = ATTEMPTS
print("RESULT " + json.dumps(out))
'''


@pytest.fixture(scope="module")
def e2e_sentry():
    """Run the real init_sentry() + real SDK + real app in a child process."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("SENTRY_DSN", None)
    env["RETRO_W11B_PROBE_KEY"] = PROBE_KEY
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=840,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, (
        f"child produced no RESULT (rc={proc.returncode}).\n"
        f"stderr tail:\n{proc.stderr[-3000:]}\nstdout tail:\n{proc.stdout[-2000:]}"
    )
    result = json.loads(lines[-1][len("RESULT "):])
    assert "fatal" not in result, result
    return result


def _leaking_items(case: dict) -> list:
    return [kind for kind, leaked in case["items"] if leaked]


@pytest.mark.timeout(900)
class TestW11bEndToEnd:
    def test_admin_route_transaction_carries_no_admin_key(self, e2e_sentry):
        """RED today: key_in_tx=True on GET /api/v1/admin/stats/daily."""
        case = e2e_sentry["admin_route_x_admin_key"]
        assert case["status"] == 200, case
        assert _leaking_items(case) == [], (
            f"the admin key left the process in envelope item(s) "
            f"{_leaking_items(case)} -- a sampled transaction carries "
            f"request.headers['x-admin-key'] verbatim. items={case['items']}"
        )

    def test_admin_mount_transaction_carries_no_admin_key(self, e2e_sentry):
        """RED today: key_in_tx=True on GET /admin/cohort.html via X-Admin-Key."""
        case = e2e_sentry["admin_mount_x_admin_key"]
        assert case["status"] == 200, case
        assert _leaking_items(case) == [], (
            f"the admin key left the process in envelope item(s) "
            f"{_leaking_items(case)}. items={case['items']}"
        )

    def test_bare_authorization_and_cookie_never_leave(self, e2e_sentry):
        """PIN (green today via the SDK's own header filter): a bare
        Authorization / Cookie on a transaction ships no secret."""
        case = e2e_sentry["bare_authorization_and_cookie"]
        assert case["status"] == 200, case
        assert _leaking_items(case) == [], case

    def test_basic_auth_on_mount_does_not_leak(self, e2e_sentry):
        """PIN (green today): Basic credentials on the mount ship no secret."""
        case = e2e_sentry["admin_mount_basic"]
        assert case["status"] == 200, case
        assert _leaking_items(case) == [], case

    def test_transactions_are_still_sent_with_valid_trace_ids(self, e2e_sentry):
        """PIN (green today): the fix scrubs, it does not DROP. Every request
        still yields exactly one transaction whose trace_id is a real 32-hex id
        (a redacted trace_id orphans the trace), and the request region is not
        blanked (non-secret headers are still present)."""
        for name in (
            "admin_route_x_admin_key",
            "admin_mount_x_admin_key",
            "admin_mount_basic",
            "bare_authorization_and_cookie",
        ):
            txs = e2e_sentry[name]["transactions"]
            assert len(txs) == 1, (name, e2e_sentry[name])
            assert re.fullmatch(r"[0-9a-f]{32}", txs[0]["trace_id"] or ""), (name, txs)
            assert "user-agent" in txs[0]["header_names"], (name, txs)

    def test_child_made_no_network_attempt(self, e2e_sentry):
        assert e2e_sentry["_network_attempts"] == []


# ===========================================================================
# W1-1c -- the /admin/* mount's Basic branch never 500s
# ===========================================================================

STATIC_PATH = "/admin/cohort.html"


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestW11cRawNonAsciiBasicHeader:
    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param(b"Basic \xff\xfe", id="raw-ff-fe"),
            pytest.param(b"Basic \xc3\xa9", id="raw-utf8-e-acute"),
            pytest.param(b"basic \xff", id="lowercase-scheme-raw-ff"),
            pytest.param(b"Basic b3A6\xff", id="ascii-prefix-then-raw-ff"),
        ],
    )
    def test_raw_non_ascii_basic_payload_is_401(self, client, monkeypatch, raw):
        """RED today: 500 (ValueError from base64.b64decode escapes the
        ``except (binascii.Error, UnicodeDecodeError)``)."""
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        resp = client.get(STATIC_PATH, headers={"Authorization": raw})
        assert resp.status_code == 401, (
            f"expected the mount's 401 reject, got {resp.status_code}: "
            f"{resp.text[:200]!r}. A 500 here is one Sentry error event per "
            "anonymous request on an unauthenticated, unrate-limited mount."
        )
        assert resp.headers.get("www-authenticate") == 'Basic realm="Qaren Admin"'


class TestW11cMountPins:
    """PINS (green today): every other mount outcome is byte-for-byte unchanged."""

    def test_correct_basic_password_serves(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        creds = base64.b64encode(f"anyuser:{PROBE_KEY}".encode()).decode()
        resp = client.get(STATIC_PATH, headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_correct_x_admin_key_serves(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        resp = client.get(STATIC_PATH, headers={"X-Admin-Key": PROBE_KEY})
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        "authz",
        [
            pytest.param("Basic " + base64.b64encode(b"op:wrong").decode(), id="wrong-password"),
            pytest.param("Basic !!!!", id="ascii-garbage"),
            pytest.param("Basic " + base64.b64encode(b"op:\xff").decode(), id="b64-of-non-utf8"),
            pytest.param(
                "Basic " + base64.b64encode("op:é".encode()).decode(), id="b64-non-ascii-pw"
            ),
            pytest.param("Basic " + base64.b64encode(b"no-colon").decode(), id="no-colon"),
            pytest.param("Bearer abc", id="not-basic"),
        ],
    )
    def test_other_rejects_are_still_401_with_challenge(self, client, monkeypatch, authz):
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        resp = client.get(STATIC_PATH, headers={"Authorization": authz})
        assert resp.status_code == 401
        assert resp.text == "Unauthorized"
        assert resp.headers.get("www-authenticate") == 'Basic realm="Qaren Admin"'

    def test_no_credentials_is_401(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        resp = client.get(STATIC_PATH)
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate") == 'Basic realm="Qaren Admin"'

    def test_unconfigured_admin_key_is_still_503(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_API_KEY", "")
        resp = client.get(STATIC_PATH, headers={"Authorization": b"Basic \xff\xfe"})
        assert resp.status_code == 503
        assert resp.text == "Admin not configured"

    @pytest.mark.parametrize(
        "exc",
        [
            pytest.param(ValueError("serving-time boom"), id="ValueError"),
            pytest.param(UnicodeError("serving-time boom"), id="UnicodeError"),
        ],
    )
    def test_serving_error_on_authenticated_basic_request_is_not_a_401(
        self, client, monkeypatch, exc
    ):
        """FIX-ROUND-2 pin (adversary mutant C5 survived every node). The W1-1c
        try wraps ONLY the base64/UTF-8 decode. If the partition, the
        compare_digest and super().__call__ were moved back inside the try
        with ``except (ValueError, UnicodeError): pass``, an error raised while
        SERVING a correctly authenticated request would be swallowed and the
        operator would get the 401 Basic challenge instead of the real 500.
        Here the parent StaticFiles.__call__ raises after a CORRECT Basic
        password: the response must be the error path, never the 401."""
        import importlib

        admin_mount_cls = importlib.import_module("app.main")._AdminAuthenticatedStaticFiles
        parent = admin_mount_cls.__mro__[1]
        served: list = []

        async def exploding_serve(self, scope, receive, send):
            served.append(scope["path"])
            raise exc

        monkeypatch.setattr(parent, "__call__", exploding_serve)
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        creds = base64.b64encode(f"anyuser:{PROBE_KEY}".encode()).decode()
        resp = client.get(STATIC_PATH, headers={"Authorization": f"Basic {creds}"})
        assert served == [STATIC_PATH], "the correct password never reached super().__call__"
        assert resp.status_code != 401, (
            "a serving-time error on an AUTHENTICATED request was swallowed into "
            "the 401 Basic challenge -- the W1-1c try must wrap only the decode"
        )
        assert resp.status_code == 500, (resp.status_code, resp.text[:200])
        assert "www-authenticate" not in resp.headers

    def test_non_ascii_x_admin_key_is_still_401(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_API_KEY", PROBE_KEY)
        resp = client.get(STATIC_PATH, headers={"X-Admin-Key": b"\xff\xfe"})
        assert resp.status_code == 401

    def test_b64decode_raises_plain_valueerror_on_this_python(self):
        """MEASUREMENT PIN: the library behaviour W1-1c exists for. A raw
        non-ASCII str makes base64.b64decode raise ValueError that is NOT a
        binascii.Error, which is why the current except clause misses it."""
        import binascii

        with pytest.raises(ValueError) as excinfo:
            base64.b64decode("\xff\xfe")
        assert not isinstance(excinfo.value, binascii.Error)
        assert issubclass(binascii.Error, ValueError)
