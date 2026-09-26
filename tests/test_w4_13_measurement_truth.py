"""W4-13 -- `search_logs` records what happened, and the admin readers skip the
probe traffic.

Findings: PO-RECORDED-MEASURED-01 / -07 / -10 / -11 (-17 stays OPEN, Q5),
PO-CATEGORIES-I18N-13, LS-MEASURED-EVIDENCE-07 / -08.
Spec: .qa-s68/specs/W4_13_UNIT_SPEC.md + its adversarial review + Fable's
binding rulings (W4_13_FABLE_RULINGS.md). Base measured: 61585c58; RED phase
re-measured at ac887e2d (= 61585c58 + PR #202, auth only).

Two per-call flags, both default OFF, plus one secret knob:

* ``ENABLE_SEARCH_LOG_TRUTH`` (flag 1) -- what gets written: failure rows carry
  the orchestrator's top-level ``total_cost``; a delivered partial carries
  ``error_message='partial:<stage>'`` (Q4); the stream's ``success:False``
  TERMINAL payloads log a failure (T3); the stream ``error`` row carries the
  event's own text + cost (T4); the stream ``else`` branch writes ONE failure
  row keyed on ``client_gone`` (T5, ruling C4); the camera failure rows carry
  total + vision (T6/T7, ruling C9); ``/url/compare`` writes rows (T8) and
  ``POST /text/quick`` writes rows (T9, ruling Q7/D1). Every NEW row sits AFTER
  its refund ``fire_and_forget`` and before the raise (ruling C3).
* ``ENABLE_SEARCH_LOG_SYNTHETIC_MARKER`` (flag 2, precondition migration 042)
  -- ``log_search`` writes ``is_synthetic``; every site passes the caller's
  classification (header ``X-Qaren-Synthetic`` == ``SEARCH_LOG_SYNTHETIC_TOKEN``,
  both non-empty, bytes compare -- ruling C2); the four admin readers drop
  ``is_synthetic is True`` rows and report ``synthetic_excluded``.
* ``SEARCH_LOG_SYNTHETIC_TOKEN`` -- the dedicated low-privilege secret (Q3);
  ``X-Qaren-Synthetic`` is redacted by the Sentry request scrub (D4).

Node classes (each docstring opens with its class):

RED        fails at HEAD on an ASSERTION naming the absent behaviour (a missing
           symbol is looked up with getattr INSIDE the body, never a
           collection-time ImportError).
PIN        green at HEAD and must stay green (flag-OFF byte identity etc.).
PIN-ON     green at HEAD with the flags ON -- the ON design must not move it.
GREEN-PIN  needs a new symbol: fails at HEAD by design (asserted absent).

Every node sets the flags + token explicitly (autouse ``_clean_flags``), sends a
fixed ``X-Request-ID`` on every TestClient request (ruling C7), and records
``log_search`` at CALL time. Zero network: autouse socket/DNS guard plus
``curl_cffi.requests.get``. New symbols are imported inside test bodies.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import copy
import ipaddress
import math
import socket
from pathlib import Path

import httpx
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api import image_routes, url_routes
from app.api import text_routes as tr
from app.api.auth_routes import get_optional_user
from app.main import app
from app.services import (
    analytics_service,
    database_service,
    sentry_service,
    structured_comparison_service as scs,
)
from scripts import eval_runner
from tests.test_retro_w2_1 import Ledger, _stub_camera, _vision

REPO_ROOT = Path(__file__).resolve().parent.parent

TRUTH = "ENABLE_SEARCH_LOG_TRUTH"
MARKER = "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER"
TOKEN = "SEARCH_LOG_SYNTHETIC_TOKEN"
HEADER = "X-Qaren-Synthetic"
METER = "ENABLE_PAID_ROUTE_METERING"
ABORT = "ENABLE_PREVERDICT_DISCONNECT_ABORT"
TOK = "w413-synthetic-token"
RID = "w4-13-fixed-request-id"
JPEG = b"\xff\xd8" + b"\x00" * 64

INT = "<int>"  # normalised duration_ms


# ---------------------------------------------------------------------------
# autouse: zero network, clean flags, limiter off, overrides restored
# ---------------------------------------------------------------------------
def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host)
    if host in ("localhost", "testserver", "testclient", "test", ""):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Copied from test_retro_w2_1._zero_network, plus curl_cffi.requests.get."""
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _addr_ok(address) -> bool:
        if isinstance(address, (str, bytes)):
            return True
        if isinstance(address, tuple) and address:
            return _is_loopback_host(address[0])
        return False

    def guarded_connect(self, address):
        if not _addr_ok(address):
            attempts.append(("connect", repr(address)))
            raise OSError(f"W4-13 zero-network guard: connect {address!r}")
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        if not _addr_ok(address):
            attempts.append(("connect_ex", repr(address)))
            raise OSError(f"W4-13 zero-network guard: connect_ex {address!r}")
        return real_connect_ex(self, address)

    def guarded_gai(host, *args, **kwargs):
        if not _is_loopback_host(host):
            attempts.append(("getaddrinfo", repr(host)))
            raise socket.gaierror(f"W4-13 zero-network guard: {host!r}")
        return real_gai(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    try:
        import curl_cffi.requests as _cc

        def _no_curl(*a, **kw):
            attempts.append(("curl_cffi.requests.get", repr(a[:1])))
            raise OSError("W4-13 zero-network guard: curl_cffi.requests.get")
        monkeypatch.setattr(_cc, "get", _no_curl)
    except ImportError:  # pragma: no cover - curl_cffi is pinned in CI
        pass
    yield attempts
    assert not attempts, f"test attempted network access: {attempts!r}"


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    for name in (TRUTH, MARKER, TOKEN, METER, ABORT,
                 "ENABLE_CAMERA_FAILURE_ENVELOPE", "ENABLE_ANON_USAGE_GATE",
                 "ENABLE_COMPARISON_ID_ECHO", "ENABLE_LLM_PREFLIGHT_BREAKER",
                 "ENABLE_STRICT_OPTIONAL_AUTH", "ENABLE_SYNC_DB_OFFLOAD",
                 "ENABLE_OFFLOOP_DNS_RESOLVE"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _limiter_off():
    from app.middleware.rate_limiter import limiter
    prior = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = prior


@pytest.fixture(autouse=True)
def _restore_overrides():
    saved = dict(app.dependency_overrides)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _flags(monkeypatch, *, truth=False, marker=False, token=None):
    for name, on in ((TRUTH, truth), (MARKER, marker)):
        if on:
            monkeypatch.setenv(name, "true")
        else:
            monkeypatch.delenv(name, raising=False)
    if token is None:
        monkeypatch.delenv(TOKEN, raising=False)
    else:
        monkeypatch.setenv(TOKEN, token)


# ---------------------------------------------------------------------------
# recorders
# ---------------------------------------------------------------------------
def _done(value=None):
    async def _r():
        return value
    return _r()


class _Rec:
    """A sync stand-in for `log_search`: records kwargs at CALL time and returns
    a finished coroutine (the production sites are fire_and_forget(coro))."""

    def __init__(self):
        self.calls: list = []

    def __call__(self, *a, **kw):
        assert not a, f"log_search must be called with keywords only, got {a!r}"
        self.calls.append(dict(kw))
        return _done()


def _norm(kw: dict) -> dict:
    """Normalise duration_ms to INT after asserting it is an int (ruling C7)."""
    out = dict(kw)
    if "duration_ms" in out:
        assert isinstance(out["duration_ms"], int) and not isinstance(out["duration_ms"], bool), out
        out["duration_ms"] = INT
    return out


def _capture_ff(labels: list):
    def _ff(coro, label):
        labels.append(label)
        with contextlib.suppress(Exception):
            coro.close()
    return _ff


class _Counter:
    """A row builder that RAISES (ruling C3) and counts its calls."""

    def __init__(self):
        self.n = 0

    def __call__(self, *a, **kw):
        self.n += 1
        raise RuntimeError("W4-13 C3 probe: row builder raised")


# ---------------------------------------------------------------------------
# fixtures of the orchestrator's payload shapes
# ---------------------------------------------------------------------------
DELIVERED = {"success": True,
             "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
             "metadata": {"total_cost": 0.01}}
PARTIAL = {"success": True,
           "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
           "metadata": {"partial": True, "partial_stage": "post_gather", "total_cost": 0.02}}
PARTIAL_NO_STAGE = {"success": True,
                    "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
                    "metadata": {"partial": True, "total_cost": 0.02}}
FAIL_ID = {"success": False, "code": "INSUFFICIENT_DATA",
           "error": "Comparison data was incomplete - choose different products.",
           "elapsed_seconds": 30.0, "total_cost": 0.017, "api_calls": 3}
FAIL_TO = {"success": False, "code": "TIMEOUT", "error": scs.TIMEOUT_FRIENDLY_MESSAGE,
           "elapsed_seconds": 30.0, "total_cost": 0.021}
FAIL_LLM = {"success": False, "code": "LLM_UNAVAILABLE",
            "error": scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE, "elapsed_seconds": 0.0,
            "total_cost": 0.0, "api_calls": 0}
FAIL_GENERIC_SAFE = {"success": False, "error": tr._DEFAULT_FAILURE_MESSAGE, "total_cost": 0.005}
FAIL_CONTENT = {"success": False, "code": "CONTENT_UNAVAILABLE",
                "error": "We don't compare this category", "layer": "moderation_api"}
FAIL_BOTH_KEYS = {"success": False, "code": "INSUFFICIENT_DATA", "error": "x",
                  "total_cost": 0.017, "metadata": {"total_cost": 0.5}}
LEAK = "Incorrect API key provided: sk-proj-W413PROBE"

ST_TERMINAL = {"success": False, "error": "The comparison took too long.", "code": "STREAM_TIMEOUT",
               "partial": True, "elapsed_seconds": 30.1, "total_cost": 0.03, "api_calls": 4}
ID_TERMINAL = dict(FAIL_ID)
MOD_TERMINAL = dict(FAIL_CONTENT)
ERR_EVENT = {"success": False, "code": "INTERNAL_ERROR",
             "error": scs.INTERNAL_ERROR_FRIENDLY_MESSAGE, "total_cost": 0.04}


def _term(payload):
    return [("status", {}), ("settle_complete", payload), ("complete", payload)]


SIX = [("status", {}), ("specs", {}), ("prices", {}), ("verdict", {}),
       ("settle_complete", DELIVERED), ("complete", DELIVERED)]

AUTHED = {"id": "w4-13-user", "email": "w413@example.test", "access_token": "w413-tok"}


# ---------------------------------------------------------------------------
# drivers (one per surface)
# ---------------------------------------------------------------------------
def _wire_text_user(monkeypatch, *, user, consumed=True, allowed=True):
    async def _prefs(uid):
        return {"success": True, "preferences_completed": True, "preferences": {}}

    async def _usage(uid, tok):
        return {"allowed": allowed, "reason": "daily", "tier": "free", "consumed": consumed,
                "remaining": {"daily": 5, "monthly": 5, "lifetime_free": 0}}
    monkeypatch.setattr(tr, "get_user_preferences", _prefs)
    monkeypatch.setattr(tr, "consume_comparison_credit", _usage)
    monkeypatch.setattr(tr, "refund_comparison_credit", lambda *a, **k: _done())
    monkeypatch.setattr(tr, "record_lifetime_comparison", lambda *a, **k: _done())
    monkeypatch.setattr(tr, "save_comparison_and_track_cohort", lambda *a, **k: _done())
    app.dependency_overrides[get_optional_user] = (lambda: user)


def _sync(monkeypatch, client, verb, result, *, user=None, headers=None, raises=False):
    """POST or GET /api/v1/text/compare with a stub orchestrator."""
    rec, labels = _Rec(), []

    class _Svc:
        async def compare_from_text(self, *a, **kw):
            if raises:
                raise RuntimeError("W4-13 probe: sync raise")
            return copy.deepcopy(result)
    monkeypatch.setattr(tr, "get_comparison_service", lambda: _Svc())
    monkeypatch.setattr(tr, "log_search", rec)
    monkeypatch.setattr(tr, "fire_and_forget", _capture_ff(labels))
    _wire_text_user(monkeypatch, user=user)
    h = {"X-Request-ID": RID}
    h.update(headers or {})
    if verb == "post":
        r = client.post("/api/v1/text/compare", json={"query": "a vs b"}, headers=h)
    else:
        r = client.get("/api/v1/text/compare", params={"q": "a vs b"}, headers=h)
    return r, rec.calls, labels


def _quick(monkeypatch, client, result=None, *, headers=None, raises=False):
    rec, labels = _Rec(), []

    class _Svc:
        async def compare_from_text(self, *a, **kw):
            if raises:
                raise RuntimeError(LEAK)
            return copy.deepcopy(result)
    monkeypatch.setattr(tr, "get_comparison_service", lambda: _Svc())
    monkeypatch.setattr(tr, "log_search", rec)
    monkeypatch.setattr(tr, "fire_and_forget", _capture_ff(labels))
    h = {"X-Request-ID": RID}
    h.update(headers or {})
    r = client.post("/api/v1/text/quick", json={"product1": "p1", "product2": "p2"}, headers=h)
    return r, rec.calls, labels


class _StreamSvc:
    def __init__(self, events, raise_after=None):
        self.events = events
        self.raise_after = raise_after
        self.closed = False

    async def compare_from_text_streaming(self, **kw):
        try:
            for i, ev in enumerate(self.events):
                if self.raise_after is not None and i == self.raise_after:
                    raise RuntimeError("W4-13 probe: mid-stream raise")
                yield copy.deepcopy(ev)
        finally:
            self.closed = True


class _AcloseRaisesSvc(_StreamSvc):
    """test_m18_preverdict_disconnect_refund._AcloseRaisesService: CancelledError
    out of aclose() only."""

    async def compare_from_text_streaming(self, **kw):
        try:
            for ev in self.events:
                yield copy.deepcopy(ev)
        except GeneratorExit:
            self.closed = True
            raise asyncio.CancelledError()


class _FakeReq:
    def __init__(self, disconnect_after=10 ** 6, headers=None):
        self.calls = 0
        self.disconnect_after = disconnect_after
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.disconnect_after


async def _stream(monkeypatch, events, *, disconnect_after=10 ** 6, raise_after=None,
                  user=None, consumed=True, headers=None, svc=None):
    rec, labels = _Rec(), []
    service = svc or _StreamSvc(events, raise_after)
    monkeypatch.setattr(tr, "get_comparison_service", lambda: service)
    monkeypatch.setattr(tr, "log_search", rec)
    monkeypatch.setattr(tr, "fire_and_forget", _capture_ff(labels))
    _wire_text_user(monkeypatch, user=user, consumed=consumed)
    resp = await tr.text_compare_stream(
        request=_FakeReq(disconnect_after, headers), q="A vs B", product_a=None, product_b=None,
        region="bahrain", specs=True, reviews=True, pros_cons=True, nocache=False,
        selected_category=None, user=user,
    )
    chunks, raised = [], None
    try:
        async for c in resp.body_iterator:
            chunks.append(c)
    except BaseException as e:  # noqa: BLE001 - CancelledError is a BaseException
        raised = type(e).__name__
    return {"calls": rec.calls, "labels": labels, "raised": raised, "chunks": chunks}


class _CamLedger(Ledger):
    def __init__(self):
        super().__init__()
        self.calls: list = []

    def log_search(self, **kw):
        self.calls.append(dict(kw))
        return super().log_search(**kw)


def _camera(monkeypatch, client, *, result=None, raises=False, meter=False, user=None,
            headers=None):
    if meter:
        monkeypatch.setenv(METER, "true")
    ledger = _CamLedger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result,
                 compare_raises=raises)
    monkeypatch.setattr(image_routes, "log_search", ledger.log_search)
    app.dependency_overrides[get_optional_user] = (lambda: user)
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    h = {"X-Request-ID": RID}
    h.update(headers or {})
    r = client.post("/api/v1/image/identify", files=files, headers=h)
    return r, ledger.calls, ledger.labels


URL_OK = {"success": True, "products": [{"brand": "Ab", "name": "one"}, {"brand": "", "name": "two"}],
          "comparison": {}, "winner_index": 0, "recommendation": "", "key_differences": [],
          "category_used": "other", "source_urls": ["https://x.test/a", "https://x.test/b"]}
URL_FEW = {"success": False, "error": "Could not extract both products", "details": []}
URL_LLM = {"success": False, "code": "LLM_UNAVAILABLE", "error": scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE}
URL_SECRET = "W4-13 url internals: postgres://svc@db.internal:5432"


def _url(monkeypatch, client, *, result=None, raises=False, user=None, meter=False,
         valid=True, allowed=True, headers=None, verb="post",
         url1="https://x.test/a", url2="https://x.test/b"):
    rec, labels = _Rec(), []
    if meter:
        monkeypatch.setenv(METER, "true")

    async def _validate(u):
        return valid
    monkeypatch.setattr(url_routes, "_validate_url_offloop_or_sync", _validate)

    async def _cmp(*a, **kw):
        if raises:
            raise RuntimeError(URL_SECRET)
        return copy.deepcopy(result)
    monkeypatch.setattr(url_routes, "compare_from_urls", _cmp)
    monkeypatch.setattr(url_routes, "log_search", rec, raising=False)
    monkeypatch.setattr(database_service, "log_search", rec)
    monkeypatch.setattr(url_routes, "fire_and_forget", _capture_ff(labels))

    async def _usage(uid, tok):
        return {"allowed": allowed, "reason": "daily", "tier": "free", "consumed": True,
                "remaining": {"daily": 0, "monthly": 0, "lifetime_free": 0}}
    monkeypatch.setattr(url_routes, "consume_comparison_credit", _usage)
    monkeypatch.setattr(url_routes, "refund_comparison_credit", lambda *a, **k: _done())
    monkeypatch.setattr(url_routes, "record_lifetime_comparison", lambda *a, **k: _done())
    monkeypatch.setattr(url_routes, "save_comparison_and_track_cohort", lambda *a, **k: _done())
    app.dependency_overrides[get_optional_user] = (lambda: user)
    h = {"X-Request-ID": RID}
    h.update(headers or {})
    if verb == "get":
        # The GET handler has its own search_log_extra plumbing (adversary
        # round-1 N10): drive it through the real route, not the POST twin.
        r = client.get("/api/v1/url/compare", params={"url1": url1, "url2": url2}, headers=h)
    else:
        r = client.post("/api/v1/url/compare", json={"url1": url1, "url2": url2}, headers=h)
    return r, rec.calls, labels


# ---------------------------------------------------------------------------
# HEAD kwargs of every site (measured at 61585c58 and ac887e2d, spec 1c)
# ---------------------------------------------------------------------------
CAM_Q = "B0 N0 vs B1 N1"
CAM_P = ["B0 N0", "B1 N1"]
HEAD_KW = {
    "post_success": ([{"query": "a vs b", "input_type": "text", "user_id": None,
                       "products_found": ["A 1", "B 2"], "success": True, "cost": 0.01,
                       "duration_ms": INT}], ["log_search.text.post.success"]),
    "post_failure": ([{"query": "a vs b", "input_type": "text", "user_id": None, "success": False,
                       "error_message": FAIL_ID["error"], "duration_ms": INT}],
                     ["log_search.text.post.failure"]),
    "get_success": ([{"query": "a vs b", "input_type": "text", "user_id": None,
                      "products_found": ["A 1", "B 2"], "success": True, "cost": 0.01,
                      "duration_ms": INT}], ["log_search.text.get.success"]),
    "get_failure": ([{"query": "a vs b", "input_type": "text", "user_id": None, "success": False,
                      "error_message": FAIL_ID["error"], "duration_ms": INT}],
                    ["log_search.text.get.failure"]),
    "stream_success": ([{"query": "A vs B", "input_type": "text_stream", "user_id": None,
                         "products_found": ["A 1", "B 2"], "success": True, "cost": 0.01,
                         "duration_ms": INT}], ["log_search.text_stream.success"]),
    "stream_failure": ([{"query": "A vs B", "input_type": "text_stream", "user_id": None,
                         "success": False, "error_message": "Streaming comparison failed",
                         "duration_ms": INT}], ["log_search.text_stream.failure"]),
    "stream_terminal_failure": ([{"query": "A vs B", "input_type": "text_stream", "user_id": None,
                                  "products_found": [], "success": True, "cost": 0,
                                  "duration_ms": INT}], ["log_search.text_stream.success"]),
    "stream_incomplete": ([], []),
    "camera_success": ([{"query": CAM_Q, "input_type": "camera", "user_id": None,
                         "products_found": CAM_P, "success": True, "cost": 0.013,
                         "duration_ms": INT}], ["log_search.camera.success"]),
    "camera_unsuccessful": ([{"query": CAM_Q, "input_type": "camera", "user_id": None,
                              "products_found": CAM_P, "success": False,
                              "error_message": "INSUFFICIENT_DATA", "cost": 0,
                              "duration_ms": INT}], ["log_search.camera.unsuccessful"]),
    "camera_exception": ([{"query": CAM_Q, "input_type": "camera", "user_id": None,
                           "products_found": CAM_P, "success": False,
                           "error_message": "retro W2-1 probe: comparison unavailable",
                           "duration_ms": INT}], ["log_search.camera.failure"]),
    "url_success": ([], []),
    "url_failure": ([], []),
    "url_exception": ([], []),
    "url_get_success": ([], []),
    "url_get_failure": ([], []),
    "url_get_exception": ([], []),
    "quick_success": ([], []),
    "quick_failure": ([], []),
    "quick_exception": ([], []),
}
SITES = list(HEAD_KW)


def _drive_site(monkeypatch, client, site, *, headers=None):
    """Run one logging site; returns (log calls, labels). Anonymous caller."""
    hdr = dict(headers or {})
    if site in ("post_success", "get_success"):
        _, calls, labels = _sync(monkeypatch, client, site.split("_")[0], DELIVERED, headers=hdr)
    elif site in ("post_failure", "get_failure"):
        _, calls, labels = _sync(monkeypatch, client, site.split("_")[0], FAIL_ID, headers=hdr)
    elif site.startswith("stream_"):
        events = {"stream_success": _term(DELIVERED),
                  "stream_failure": [("status", {}), ("error", dict(ERR_EVENT))],
                  "stream_terminal_failure": _term(ID_TERMINAL),
                  "stream_incomplete": SIX}[site]
        out = asyncio.run(_stream(monkeypatch, events, headers=hdr,
                                  raise_after=(1 if site == "stream_incomplete" else None)))
        calls, labels = out["calls"], out["labels"]
    elif site.startswith("camera_"):
        kw = {"camera_success": {"result": DELIVERED},
              "camera_unsuccessful": {"result": FAIL_ID, "meter": True},
              "camera_exception": {"raises": True}}[site]
        _, calls, labels = _camera(monkeypatch, client, headers=hdr, **kw)
    elif site.startswith("url_"):
        verb = "get" if site.startswith("url_get_") else "post"
        kw = {"success": {"result": URL_OK}, "failure": {"result": URL_FEW},
              "exception": {"raises": True}}[site.rsplit("_", 1)[1]]
        _, calls, labels = _url(monkeypatch, client, headers=hdr, verb=verb, **kw)
    else:
        kw = {"quick_success": {"result": DELIVERED}, "quick_failure": {"result": FAIL_ID},
              "quick_exception": {"raises": True}}[site]
        _, calls, labels = _quick(monkeypatch, client, headers=hdr, **kw)
    return calls, [lb for lb in labels if lb.startswith("log_search")]


# ===========================================================================
# 1-2  flag readers
# ===========================================================================
_TRUE = ("true", "TRUE", " true ", "1", "yes", "on")
_FALSE = ("false", "0", "", "garbage")


@pytest.mark.parametrize("name,env", [
    ("search_log_truth_enabled", TRUTH),
    ("search_log_synthetic_marker_enabled", MARKER),
])
def test_search_log_flag_readers_are_per_call_and_parse(monkeypatch, name, env):
    """GREEN-PIN (tests 1 + 2): `database_service.<name>()` is the ONE reader of
    its flag, read per call with the `.strip().lower() in (true,1,yes,on)` idiom
    (M21: a reader without strip/lower reddens the ' true ' / 'TRUE' rows).
    Absent at HEAD by design."""
    reader = getattr(database_service, name, None)
    assert callable(reader), f"database_service.{name} (the {env} reader) is absent"
    monkeypatch.delenv(env, raising=False)
    assert reader() is False, "unset must read False"
    for v in _TRUE:
        monkeypatch.setenv(env, v)
        assert reader() is True, f"{env}={v!r} must read True"
    for v in _FALSE:
        monkeypatch.setenv(env, v)
        assert reader() is False, f"{env}={v!r} must read False"
    monkeypatch.setenv(env, "true")
    assert reader() is True
    monkeypatch.setenv(env, "off")
    assert reader() is False, "per call: the second call must see the new value"


# ===========================================================================
# 3-8  the four admin readers under flag 2
# ===========================================================================
def _fake_client(rows, seen):
    from unittest.mock import MagicMock

    c = MagicMock()

    def table(name):
        seen.append(("table", name))
        t = MagicMock()

        def select(cols):
            seen.append(("select", cols))
            q = MagicMock()
            q.gte.return_value = q
            q.eq.return_value = q
            q.execute.return_value = MagicMock(data=[dict(r) for r in rows])
            return q
        t.select.side_effect = select
        return t
    c.table.side_effect = table
    return c


_PROBE = [{"query": "product1 vs product2", "input_type": "text", "success": True, "cost": 0,
           "duration_ms": 0, "created_at": "2026-09-01T00:00:00+00:00", "error_message": None,
           "is_synthetic": True} for _ in range(10)]
_ORGANIC = [{"query": "macbook air m3 vs dell xps 13", "input_type": "text_stream", "success": True,
             "cost": 0.012, "duration_ms": 22000, "created_at": "2026-09-01T00:00:00+00:00",
             "error_message": None, "is_synthetic": False} for _ in range(2)]
_PROBE_FAILING = [dict(r, success=False, error_message="blocked", query="something") for r in _PROBE]

HEAD_SELECTS = [
    "success, cost, duration_ms, created_at",
    "query, input_type",
    "cost, created_at, success",
    "success, error_message, created_at",
]


async def _readers(monkeypatch, rows):
    seen: list = []
    monkeypatch.setattr(analytics_service, "get_supabase_client", lambda: _fake_client(rows, seen))
    out = {
        "daily": await analytics_service.get_daily_stats(30),
        "popular": await analytics_service.get_popular_queries(20),
        "cost": await analytics_service.get_cost_trends(30),
        "errors": await analytics_service.get_error_stats(7),
    }
    out["selects"] = [s[1] for s in seen if s[0] == "select"]
    return out


@pytest.mark.asyncio
async def test_daily_stats_excludes_marked_synthetic_rows_flag_on(monkeypatch):
    """RED (test 3): 10 marked probe rows at 0 ms + 2 organic rows at 22,000 ms
    -> avg 22000 over 2 rows, synthetic_excluded 10. HEAD: 3667 / 12 (measured)."""
    _flags(monkeypatch, marker=True)
    d = (await _readers(monkeypatch, _PROBE + _ORGANIC))["daily"]
    assert d["avg_duration_ms"] == 22000, f"synthetic rows still dilute the average: {d}"
    assert d["total_comparisons"] == 2, d
    assert d["success_count"] == 2 and d["error_count"] == 0, d
    assert d["total_cost"] == 0.024, d
    assert d.get("synthetic_excluded") == 10, f"no synthetic_excluded count: {d}"


@pytest.mark.asyncio
async def test_popular_queries_top_is_organic_flag_on(monkeypatch):
    """RED (test 4): the probe string must not top the popular list.
    HEAD: [0] == {'query': 'product1 vs product2', 'count': 10}. Reads the
    LIFETIME table (no window, review B4)."""
    _flags(monkeypatch, marker=True)
    p = (await _readers(monkeypatch, _PROBE + _ORGANIC))["popular"]
    assert p == [{"query": "macbook air m3 vs dell xps 13", "count": 2}], p


@pytest.mark.asyncio
async def test_cost_trends_and_error_stats_exclude_synthetic_flag_on(monkeypatch):
    """RED (test 5): cost trends over the kept rows (2, avg 0.012) and error
    stats over the variant whose 10 marked rows FAIL with 'blocked'
    (2 requests, rate 0.0, no common errors). HEAD: 0.002 / 12 and 0.833."""
    _flags(monkeypatch, marker=True)
    c = (await _readers(monkeypatch, _PROBE + _ORGANIC))["cost"]
    assert c["comparison_count"] == 2, c
    assert c["avg_cost_per_comparison"] == 0.012, c
    assert c["total_cost"] == 0.024, c
    assert c.get("synthetic_excluded") == 10, c
    e = (await _readers(monkeypatch, _PROBE_FAILING + _ORGANIC))["errors"]
    assert e["total_requests"] == 2, e
    assert e["error_count"] == 0 and e["error_rate"] == 0.0, e
    assert e["common_errors"] == [], e
    assert e.get("synthetic_excluded") == 10, e


@pytest.mark.asyncio
async def test_null_and_missing_is_synthetic_rows_still_count(monkeypatch):
    """PIN-ON (test 6, COUNTS ONLY - it does not assert synthetic_excluded):
    under flag 2 a row WITHOUT the key, one with None and one with False are all
    kept -- the rule is `is not True`, never falsy (M17 reddens it). Green at
    HEAD, which counts every row."""
    _flags(monkeypatch, marker=True)
    base = {"query": "q", "input_type": "text", "success": True, "cost": 0.01,
            "duration_ms": 1000, "created_at": "2026-09-01T00:00:00+00:00", "error_message": None}
    rows = [dict(base), dict(base, is_synthetic=None), dict(base, is_synthetic=False)]
    out = await _readers(monkeypatch, rows)
    assert out["daily"]["total_comparisons"] == 3, out["daily"]
    assert out["daily"]["avg_duration_ms"] == 1000, out["daily"]
    assert out["popular"] == [{"query": "q", "count": 3}], out["popular"]
    assert out["cost"]["comparison_count"] == 3, out["cost"]
    assert out["errors"]["total_requests"] == 3, out["errors"]


@pytest.mark.asyncio
async def test_readers_select_is_synthetic_only_under_flag_on(monkeypatch):
    """RED (test 7): under flag 2 each of the four select strings is the HEAD
    string + ', is_synthetic' (so the filter can see the column)."""
    _flags(monkeypatch, marker=True)
    out = await _readers(monkeypatch, _ORGANIC)
    assert out["selects"] == [s + ", is_synthetic" for s in HEAD_SELECTS], out["selects"]


@pytest.mark.asyncio
async def test_readers_flag_off_byte_identical(monkeypatch):
    """PIN (test 8): flags unset -- the HEAD select strings exactly, and the
    marked rows still counted (3667 / 12, product1 vs product2 x10, 0.002,
    0.833), no synthetic_excluded key. M16 (marker reader forced True) reddens."""
    _flags(monkeypatch, token=TOK)
    out = await _readers(monkeypatch, _PROBE + _ORGANIC)
    assert out["selects"] == HEAD_SELECTS, out["selects"]
    d = out["daily"]
    assert d == {"total_comparisons": 12, "success_count": 12, "error_count": 0, "total_cost": 0.024,
                 "avg_duration_ms": 3667, "daily_breakdown": {"2026-09-01": 12}, "period_days": 30}, d
    assert out["popular"][0] == {"query": "product1 vs product2", "count": 10}, out["popular"]
    assert out["cost"]["avg_cost_per_comparison"] == 0.002, out["cost"]
    assert "synthetic_excluded" not in out["cost"]
    e = (await _readers(monkeypatch, _PROBE_FAILING + _ORGANIC))["errors"]
    assert e["error_rate"] == 0.833, e
    assert "synthetic_excluded" not in e


# ===========================================================================
# 9-11  the writer
# ===========================================================================
def _insert_capture(monkeypatch):
    from unittest.mock import MagicMock

    inserted: list = []
    cl = MagicMock()
    tbl = MagicMock()

    def _insert(rec):
        inserted.append(dict(rec))
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=[])))
    tbl.insert.side_effect = _insert
    cl.table.return_value = tbl
    monkeypatch.setattr(database_service, "get_supabase_client", lambda: cl)
    return inserted


async def _call_log_search(**kw):
    try:
        await database_service.log_search(**kw)
    except TypeError as e:
        pytest.fail(f"log_search does not accept is_synthetic: {e}")


HEAD_RECORD_KEYS = {"query", "input_type", "products_found", "success", "cost", "duration_ms"}


@pytest.mark.asyncio
async def test_log_search_writes_is_synthetic_only_when_marker_flag_on(monkeypatch):
    """RED (test 9): flag 2 ON -- True -> record['is_synthetic'] is True, False ->
    False, None -> no key. HEAD raises TypeError (unknown kwarg)."""
    _flags(monkeypatch, marker=True)
    inserted = _insert_capture(monkeypatch)
    await _call_log_search(query="q1", duration_ms=1, is_synthetic=True)
    await _call_log_search(query="q2", duration_ms=1, is_synthetic=False)
    await _call_log_search(query="q3", duration_ms=1, is_synthetic=None)
    assert [r.get("is_synthetic", "ABSENT") for r in inserted] == [True, False, "ABSENT"], inserted


@pytest.mark.asyncio
async def test_log_search_record_flag_off_identical(monkeypatch):
    """RED (test 10, relabelled by ruling C6): flag 2 OFF + is_synthetic=True
    passed -> NO key; the record key sets equal HEAD's (p02_records). M18 (key
    written without the flag check) reddens. HEAD raises TypeError."""
    _flags(monkeypatch)
    inserted = _insert_capture(monkeypatch)
    await _call_log_search(query="q", success=False, error_message="x", duration_ms=5, is_synthetic=True)
    await _call_log_search(query="q2", user_id="u1", success=True, cost=0.01, duration_ms=7,
                           is_synthetic=True)
    assert set(inserted[0]) == HEAD_RECORD_KEYS | {"error_message"}, inserted[0]
    assert set(inserted[1]) == HEAD_RECORD_KEYS | {"user_id"}, inserted[1]


def _log_search_calls():
    out = []
    for path in sorted((REPO_ROOT / "app").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                if name == "log_search":
                    out.append((str(path.relative_to(REPO_ROOT)), node.lineno,
                                {k.arg for k in node.keywords if k.arg}))
    return out


def test_every_log_search_call_site_passes_duration_ms():
    """PIN (test 11, replaces LS-07's 'make duration_ms required', which would
    break four existing pins): every `log_search(` call under app/ passes
    duration_ms as a keyword. >= 9 sites at HEAD; the green adds T3/T5/T8/T9."""
    calls = _log_search_calls()
    assert len(calls) >= 9, calls
    missing = [(p, ln) for p, ln, kws in calls if "duration_ms" not in kws]
    assert not missing, f"log_search call(s) without duration_ms: {missing}"


# ===========================================================================
# 12-16  synthetic classification (flag 2)
# ===========================================================================
def test_synthetic_header_with_matching_token_marks_the_row(monkeypatch, client):
    """RED (test 12): POST /text/compare with X-Qaren-Synthetic == the token ->
    the row carries is_synthetic True. HEAD passes no such kwarg."""
    _flags(monkeypatch, marker=True, token=TOK)
    r, calls, _ = _sync(monkeypatch, client, "post", DELIVERED, headers={HEADER: TOK})
    assert r.status_code == 200
    assert len(calls) == 1 and calls[0].get("is_synthetic", "ABSENT") is True, calls


@pytest.mark.parametrize("token,header", [
    (TOK, None),            # header absent
    (TOK, "wrong-value"),   # wrong value
    (None, TOK),            # token unset, header present
    (None, None),           # token unset AND header absent (C2: b''==b'' is True)
], ids=["header_absent", "wrong_value", "token_unset_header_present", "token_unset_header_absent"])
def test_missing_wrong_or_unset_token_is_organic(monkeypatch, client, token, header):
    """RED (test 13 + ruling C2): every non-matching case logs is_synthetic False
    -- an explicit False, never absent. The last case is the empty-secret trap:
    hmac.compare_digest(b'', b'') is True (measured), so without the non-empty
    guards (M25) flipping flag 2 before the token is set would mark EVERY
    request synthetic. M19 (header alone) reddens the token-unset row."""
    _flags(monkeypatch, marker=True, token=token)
    r, calls, _ = _sync(monkeypatch, client, "post", DELIVERED,
                        headers=({HEADER: header} if header is not None else {}))
    assert r.status_code == 200
    assert len(calls) == 1 and calls[0].get("is_synthetic", "ABSENT") is False, calls


def test_non_ascii_synthetic_header_never_raises(monkeypatch, client):
    """RED (test 14, relabelled by ruling C6): a header whose bytes start 0xFF
    arrives DECODED as a non-ASCII str (measured: ords 195, 191 -- TestClient
    does not deliver the raw byte). A `str` compare_digest raises TypeError on
    it (measured), so the bytes/surrogateescape compare is required (M20; no
    broad except may hide it, ruling C11). Expected: status == the no-header
    status (200), no 500, is_synthetic False."""
    _flags(monkeypatch, marker=True, token=TOK)
    seen = {}

    def _dep(request: Request):
        seen["hdr"] = request.headers.get(HEADER.lower())
        return None
    r0, _, _ = _sync(monkeypatch, client, "post", DELIVERED)
    r, calls, _ = _sync(monkeypatch, client, "post", DELIVERED, headers={HEADER: b"\xfftok"})
    calls = list(calls)  # snapshot: the probe request below reuses the same recorder
    app.dependency_overrides[get_optional_user] = _dep
    client.post("/api/v1/text/compare", json={"query": "a vs b"},
                headers={"X-Request-ID": RID, HEADER: b"\xfftok"})
    assert seen.get("hdr") and any(ord(ch) > 127 for ch in seen["hdr"]), (
        f"precondition: the header must arrive as a non-ASCII str, got {seen!r}")
    assert r.status_code == r0.status_code == 200, (r.status_code, r.text[:200])
    assert len(calls) == 1 and calls[0].get("is_synthetic", "ABSENT") is False, calls


@pytest.mark.parametrize("site", SITES)
def test_marker_reaches_every_site(monkeypatch, client, site):
    """RED (test 15; ruling C5 turns flag 1 ON too, the T5/T8/T9 rows only exist
    under it): with both flags ON, the token set and the matching header, every
    row every site writes carries is_synthetic True. HEAD: the kwarg is absent
    everywhere, and the url/quick/stream-incomplete sites write nothing."""
    _flags(monkeypatch, truth=True, marker=True, token=TOK)
    calls, _ = _drive_site(monkeypatch, client, site, headers={HEADER: TOK})
    assert calls, f"[{site}] wrote no search_logs row"
    assert all(c.get("is_synthetic", "ABSENT") is True for c in calls), calls


@pytest.mark.parametrize("site", SITES)
def test_flags_off_no_new_kwargs_at_any_site(monkeypatch, client, site):
    """PIN (test 16): flags unset, token + header PRESENT -- every site's kwargs
    and log labels equal HEAD's (spec 1c), the url + quick sites make zero calls.
    M15 (truth reader forced True) and M16 (marker forced True) redden it."""
    _flags(monkeypatch, token=TOK)
    calls, labels = _drive_site(monkeypatch, client, site, headers={HEADER: TOK})
    exp_calls, exp_labels = HEAD_KW[site]
    assert [_norm(c) for c in calls] == exp_calls, calls
    assert labels == exp_labels, labels


# ===========================================================================
# 17-26  failure cost and outcomes (flag 1)
# ===========================================================================
_COST_CASES = [
    ("insufficient", FAIL_ID, 0.017, 400),
    ("timeout", FAIL_TO, 0.021, 503),
    ("llm_unavailable", FAIL_LLM, 0.0, 503),
    ("generic_safe", FAIL_GENERIC_SAFE, 0.005, 400),
    ("content_unavailable", FAIL_CONTENT, 0.0, 200),
    ("top_level_wins_over_metadata", FAIL_BOTH_KEYS, 0.017, 400),
    ("nan", dict(FAIL_ID, total_cost=float("nan")), 0.0, 400),
    ("inf", dict(FAIL_ID, total_cost=float("inf")), 0.0, 400),
    ("negative", dict(FAIL_ID, total_cost=-1), 0.0, 400),
    ("bool", dict(FAIL_ID, total_cost=True), 0.0, 400),
    ("str", dict(FAIL_ID, total_cost="0.3"), 0.0, 400),
]


@pytest.mark.parametrize("verb", ["post", "get"])
@pytest.mark.parametrize("case,result,cost,status", _COST_CASES, ids=[c[0] for c in _COST_CASES])
def test_post_and_get_failure_logs_carry_total_cost(monkeypatch, client, verb, case, result, cost, status):
    """RED (test 17; M1/M2 POST/GET threading, M3 metadata-first, M4 bad values):
    under flag 1 the failure row carries cost = top-level total_cost, else
    metadata.total_cost, else 0.0; NaN/inf/negative/bool/str -> 0.0. The
    error_message and the wire status are unchanged. HEAD passes no cost."""
    _flags(monkeypatch, truth=True)
    r, calls, _ = _sync(monkeypatch, client, verb, result)
    assert r.status_code == status, (r.status_code, r.text[:200])
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    kw = calls[0]
    assert "cost" in kw, f"[{verb}/{case}] the failure row carries no cost: {kw}"
    assert type(kw["cost"]) is float and math.isfinite(kw["cost"]), kw
    assert kw["cost"] == cost, kw
    assert kw["error_message"] == result.get("error"), kw


# ===========================================================================
# C3 totality: an int too large for a float (adversary round-1 defect 1)
# ===========================================================================
HUGE = 10 ** 400  # float(HUGE) raises OverflowError


def test_cost_builders_are_total_over_an_overflowing_int():
    """PIN (ruling C3; adversary round-1 defect 1 -- mutation 'unguarded
    float(v) in _log_cost_value' reddens it): the cost builders never raise on
    an int too large for a float. The top-level rung falls through to the next
    rung exactly as a non-finite value does; a big-but-representable int still
    converts."""
    assert tr._log_cost_value(HUGE) is None
    assert tr._log_cost_value(10 ** 300) == 1e300
    assert tr._failure_log_cost({"total_cost": HUGE}) == 0.0
    assert tr._failure_log_cost({"total_cost": HUGE, "metadata": {"total_cost": 0.5}}) == 0.5
    assert tr._failure_log_cost({"metadata": {"total_cost": HUGE}}) == 0.0
    assert image_routes._camera_log_cost({"total_cost": HUGE}, 0.003) == 0.003
    assert image_routes._camera_log_cost({"total_cost": 0.017}, HUGE) == 0.017


@pytest.mark.parametrize("surface", ["post", "get", "quick", "camera", "stream_terminal"])
def test_overflowing_int_cost_never_changes_the_response(monkeypatch, client, surface):
    """PIN (HARD rule: flag 1 never changes a client-visible byte; ruling C3;
    adversary round-1 defect 1 measured 400 -> 500 SERVER_ERROR under flag 1
    on POST, GET and /text/quick): a failure result whose total_cost is an int
    too large for a float answers with the SAME status + body (or SSE chunks)
    under flag 1 as under flag OFF, the refund still fires, and the row is
    still written with a finite cost."""
    res = dict(FAIL_ID, total_cost=HUGE)

    def _run():
        if surface in ("post", "get"):
            r, calls, labels = _sync(monkeypatch, client, surface, res, user=AUTHED)
            return (r.status_code, r.json()), calls, labels
        if surface == "quick":
            r, calls, labels = _quick(monkeypatch, client, res)
            return (r.status_code, r.json()), calls, labels
        if surface == "camera":
            r, calls, labels = _camera(monkeypatch, client, result=copy.deepcopy(res), meter=True,
                                       user=AUTHED)
            return (r.status_code, r.json()), calls, labels
        out = asyncio.run(_stream(monkeypatch, _term(copy.deepcopy(res)), user=AUTHED))
        return (out["raised"], out["chunks"]), out["calls"], out["labels"]

    _flags(monkeypatch)
    wire_off, _, _ = _run()
    _flags(monkeypatch, truth=True)
    wire_on, calls, labels = _run()
    assert wire_on == wire_off, (surface, wire_off, wire_on)
    refund = {"post": "usage_refund.text.post", "get": "usage_refund.text.get",
              "camera": "usage_refund.image.comparison_unsuccessful"}.get(surface)
    if refund:
        assert refund in labels, labels
    rows = [c for c in calls if c.get("success") is False]
    assert len(rows) == 1, calls
    assert type(rows[0]["cost"]) is float and math.isfinite(rows[0]["cost"]), rows
    assert rows[0]["cost"] == (0.003 if surface == "camera" else 0.0), rows


@pytest.mark.asyncio
@pytest.mark.parametrize("case,payload,cost", [
    ("stream_timeout", ST_TERMINAL, 0.03),
    ("insufficient_data", ID_TERMINAL, 0.017),
    ("moderation_refusal", MOD_TERMINAL, 0.0),
], ids=["stream_timeout", "insufficient_data", "moderation_refusal"])
async def test_stream_success_false_terminal_logs_a_failure(monkeypatch, case, payload, cost):
    """RED (test 18, T3; M5 removes the branch, M6 also skips billing, M27 keeps
    products_found): a TERMINAL settle_complete/complete payload with success
    False logs ONE failure row under log_search.text_stream.terminal_failure,
    error_message == payload['error'], cost as listed, no products_found -- and
    the history save + lifetime record STILL fire (current billing,
    CD-wave-diffs-02 = W4-13b). HEAD: success True, cost 0 (measured)."""
    _flags(monkeypatch, truth=True)
    out = await _stream(monkeypatch, _term(payload), user=AUTHED)
    calls, labels = out["calls"], out["labels"]
    assert "log_search.text_stream.success" not in labels, labels
    assert labels.count("log_search.text_stream.terminal_failure") == 1, labels
    assert len(calls) == 1, calls
    kw = calls[0]
    assert kw["success"] is False, kw
    assert kw["error_message"] == payload["error"], kw
    assert kw.get("cost") == cost, kw
    assert "products_found" not in kw, kw
    assert "save_comparison.text_stream" in labels and "record_lifetime.text_stream" in labels, (
        f"billing must be unchanged here (W4-13b owns it): {labels}")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["dict_event", "non_dict_event"])
async def test_stream_error_event_log_carries_error_text_and_cost(monkeypatch, case):
    """RED (test 19, T4; M7): the error row carries the LAST error event's own
    text + cost. A non-dict event is never captured (ruling C3) -> the constant
    and 0.0, and the refund still fires. HEAD: the constant and no cost."""
    _flags(monkeypatch, truth=True)
    ev = dict(ERR_EVENT) if case == "dict_event" else "a bare string"
    out = await _stream(monkeypatch, [("status", {}), ("error", ev)], user=AUTHED)
    calls, labels = out["calls"], out["labels"]
    assert out["raised"] is None, out["raised"]
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    kw = calls[0]
    if case == "dict_event":
        assert kw["error_message"] == scs.INTERNAL_ERROR_FRIENDLY_MESSAGE, kw
        assert kw.get("cost") == 0.04, kw
    else:
        assert kw["error_message"] == "Streaming comparison failed", kw
        assert kw.get("cost") == 0.0, kw
    assert "usage_refund.text_stream" in labels, labels


@pytest.mark.parametrize("surface", ["post", "get", "stream", "camera", "post_no_stage"])
def test_partial_success_logs_partial_marker(monkeypatch, client, surface):
    """RED (test 20, T2 / Q4; M8): a delivered partial keeps success True and its
    cost, and carries error_message 'partial:<stage>' ('partial:unknown' without
    a stage). Camera cost = 0.02 + vision 0.003 = 0.023 (ruling C6: the route
    adds vision into metadata.total_cost). HEAD: no error_message."""
    _flags(monkeypatch, truth=True)
    if surface in ("post", "get", "post_no_stage"):
        res = PARTIAL_NO_STAGE if surface == "post_no_stage" else PARTIAL
        _, calls, _ = _sync(monkeypatch, client, surface.split("_")[0], res)
        cost = 0.02
    elif surface == "stream":
        calls = asyncio.run(_stream(monkeypatch, _term(PARTIAL)))["calls"]
        cost = 0.02
    else:
        _, calls, _ = _camera(monkeypatch, client, result=PARTIAL)
        cost = 0.023
    note = "partial:unknown" if surface == "post_no_stage" else "partial:post_gather"
    assert len(calls) == 1, calls
    kw = calls[0]
    assert kw["success"] is True, kw
    assert kw.get("error_message") == note, kw
    assert kw.get("cost") == cost, kw


@pytest.mark.asyncio
@pytest.mark.parametrize("halfb", [False, True], ids=["drain", "half_b_abort"])
async def test_stream_client_gone_before_complete_logs_one_failure_row(monkeypatch, halfb):
    """RED (test 21, T5 + ruling C4 + C3; M9 removes it, M10 logs success True,
    M29 keys on complete_response, M26 moves it before the refund): the client
    left before the final payload (disconnect_after=0), authed + consumed ->
    exactly ONE row, success False, 'client_gone_before_complete', label
    log_search.text_stream.incomplete, AFTER usage_refund.text_stream.incomplete;
    no history, no lifetime. Drain: cost 0.01 (the payload landed after the
    client left). Half-B ON (measured: 1 event yielded, complete_response None):
    the SAME message, cost 0.0. HEAD: zero rows."""
    _flags(monkeypatch, truth=True)
    if halfb:
        monkeypatch.setenv(ABORT, "true")
    out = await _stream(monkeypatch, SIX, disconnect_after=0, user=AUTHED)
    calls, labels = out["calls"], out["labels"]
    assert len(calls) == 1, f"expected exactly one row, got {calls}"
    kw = calls[0]
    assert kw["success"] is False and kw["error_message"] == "client_gone_before_complete", kw
    assert kw.get("cost") == (0.0 if halfb else 0.01), kw
    assert "products_found" not in kw, kw
    assert "usage_refund.text_stream.incomplete" in labels, labels
    assert labels.index("usage_refund.text_stream.incomplete") < labels.index(
        "log_search.text_stream.incomplete"), f"the row must sit AFTER the refund (C3): {labels}"
    assert "save_comparison.text_stream" not in labels and "record_lifetime.text_stream" not in labels


@pytest.mark.asyncio
async def test_stream_incomplete_logs_one_failure_row(monkeypatch):
    """RED (test 22, T5; M9): a mid-stream RuntimeError (client still there) ->
    one row, success False, 'stream_incomplete', cost 0.0, and the exception
    still propagates. HEAD: zero rows."""
    _flags(monkeypatch, truth=True)
    out = await _stream(monkeypatch, _term(DELIVERED), raise_after=1)
    assert out["raised"] == "RuntimeError", out["raised"]
    assert len(out["calls"]) == 1, out["calls"]
    kw = out["calls"][0]
    assert kw["success"] is False and kw["error_message"] == "stream_incomplete", kw
    assert kw.get("cost") == 0.0, kw
    assert out["labels"] == ["log_search.text_stream.incomplete"], out["labels"]


@pytest.mark.asyncio
@pytest.mark.parametrize("abort_on", [False, True], ids=["abort_off", "abort_on"])
async def test_refund_survives_an_aclose_that_raises_flag_on_twin(monkeypatch, abort_on):
    """RED (ruling Q1: the flag-ON twin of test_m18_preverdict_disconnect_refund
    ::test_refund_survives_an_aclose_that_raises, whose `not any(log_search)`
    stays the flag-OFF pin): under flag 1 an aclose() that raises
    CancelledError still leaves the refund AND exactly one failure row, the row
    AFTER the refund; nothing is metered. HEAD: zero rows."""
    _flags(monkeypatch, truth=True)
    if abort_on:
        monkeypatch.setenv(ABORT, "true")
    out = await _stream(monkeypatch, SIX, disconnect_after=0, user=AUTHED,
                        svc=_AcloseRaisesSvc(SIX))
    labels = out["labels"]
    assert "usage_refund.text_stream.incomplete" in labels, labels
    logs = [lb for lb in labels if lb.startswith("log_search")]
    assert logs == ["log_search.text_stream.incomplete"], labels
    assert labels.index("usage_refund.text_stream.incomplete") < labels.index(logs[0]), labels
    assert len(out["calls"]) == 1 and out["calls"][0]["success"] is False, out["calls"]
    assert not any(lb.startswith(("save_comparison", "record_lifetime")) for lb in labels), labels


_STREAM_OFF = {
    "delivered": (dict(events=_term(DELIVERED)), HEAD_KW["stream_success"][0],
                  ["log_search.text_stream.success"]),
    "partial": (dict(events=_term(PARTIAL)),
                [{"query": "A vs B", "input_type": "text_stream", "user_id": None,
                  "products_found": ["A 1", "B 2"], "success": True, "cost": 0.02, "duration_ms": INT}],
                ["log_search.text_stream.success"]),
    "stream_timeout_terminal": (dict(events=_term(ST_TERMINAL)), HEAD_KW["stream_terminal_failure"][0],
                                ["log_search.text_stream.success"]),
    "insufficient_terminal": (dict(events=_term(ID_TERMINAL)), HEAD_KW["stream_terminal_failure"][0],
                              ["log_search.text_stream.success"]),
    "moderation_terminal": (dict(events=_term(MOD_TERMINAL)), HEAD_KW["stream_terminal_failure"][0],
                            ["log_search.text_stream.success"]),
    "error_event": (dict(events=[("status", {}), ("error", dict(ERR_EVENT))]),
                    HEAD_KW["stream_failure"][0], ["log_search.text_stream.failure"]),
    "preverdict_disconnect_anon": (dict(events=SIX, disconnect_after=0), [], []),
    "preverdict_disconnect_authed": (dict(events=SIX, disconnect_after=0, user=AUTHED), [],
                                     ["usage_refund.text_stream.incomplete"]),
    "midstream_raise": (dict(events=_term(DELIVERED), raise_after=1), [], []),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", list(_STREAM_OFF))
async def test_stream_flag_off_outcomes_identical(monkeypatch, scenario):
    """PIN (test 23, mirrors test_m18_preverdict_disconnect_refund:294): flags
    unset -- every stream scenario gives exactly the HEAD labels and kwargs,
    including ZERO rows on disconnect / raise. M15 reddens it."""
    _flags(monkeypatch, token=TOK)
    kwargs, exp_calls, exp_labels = _STREAM_OFF[scenario]
    out = await _stream(monkeypatch, headers={HEADER: TOK}, **kwargs)
    assert [_norm(c) for c in out["calls"]] == exp_calls, out["calls"]
    assert out["labels"] == exp_labels, out["labels"]


@pytest.mark.parametrize("site", ["post_success", "get_success", "stream_success", "camera_success"])
def test_delivered_non_partial_rows_unchanged(monkeypatch, client, site):
    """PIN-ON (test 24): a delivered NON-partial row under flag 1 ON equals the
    HEAD kwargs (T2 adds a note to partials only)."""
    _flags(monkeypatch, truth=True)
    calls, labels = _drive_site(monkeypatch, client, site)
    assert [_norm(c) for c in calls] == HEAD_KW[site][0], calls
    assert labels == HEAD_KW[site][1], labels


@pytest.mark.parametrize("surface", ["post", "get", "camera"])
def test_partial_rows_flag_off_carry_no_note(monkeypatch, client, surface):
    """PIN (T2's flag-OFF half; mutations HK-24p / HK-24c -- the partial note
    shipped UNFLAGGED on the POST / camera row -- redden it; the stream twin is
    test 23 [partial]): flags unset, token + header present, a delivered
    PARTIAL row carries exactly HEAD's kwargs -- no error_message, HEAD cost."""
    _flags(monkeypatch, token=TOK)
    if surface == "camera":
        _, calls, _ = _camera(monkeypatch, client, result=PARTIAL, headers={HEADER: TOK})
        exp = [{"query": CAM_Q, "input_type": "camera", "user_id": None, "products_found": CAM_P,
                "success": True, "cost": 0.023, "duration_ms": INT}]
    else:
        _, calls, _ = _sync(monkeypatch, client, surface, PARTIAL, headers={HEADER: TOK})
        exp = [{"query": "a vs b", "input_type": "text", "user_id": None,
                "products_found": ["A 1", "B 2"], "success": True, "cost": 0.02, "duration_ms": INT}]
    assert [_norm(c) for c in calls] == exp, calls


@pytest.mark.parametrize("meter,success", [(True, False), (False, True)],
                         ids=["metering_on", "metering_off"])
def test_camera_unsuccessful_log_cost_is_total_plus_vision(monkeypatch, client, meter, success):
    """RED (test 25, T6 + ruling C9; M11, M3): INSUFFICIENT_DATA total_cost 0.017
    + vision 0.003 -> cost 0.02 (top-level + vision, no double count); success
    stays HEAD's (False under metering, True -- R-METER's pinned design --
    without). HEAD: cost 0 (the key it reads is always absent)."""
    _flags(monkeypatch, truth=True)
    _, calls, _ = _camera(monkeypatch, client, result=FAIL_ID, meter=meter)
    assert len(calls) == 1, calls
    assert calls[0]["success"] is success, calls
    assert calls[0].get("cost") == 0.02, calls


CAM_RAISE_TEXT = "retro W2-1 probe: comparison unavailable"  # tests.test_retro_w2_1's raise


def test_camera_exception_log_carries_vision_cost(monkeypatch, client):
    """RED (test 26, T7; M11): the comparison raises -> the failure row carries
    cost == vision_cost 0.003 (the comparison's own spend is unknowable). Under
    flag 1 its error_message is the constant 'camera_exception' (post-green
    ruling R9(b): R1's floor covers the camera EXCEPTION row too -- the spec's
    'str(e) unchanged' is superseded). HEAD: no cost kwarg."""
    _flags(monkeypatch, truth=True)
    r, calls, _ = _camera(monkeypatch, client, raises=True)
    assert r.status_code == 200
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    assert calls[0].get("cost") == 0.003, calls
    assert calls[0]["error_message"] == "camera_exception", calls


@pytest.mark.parametrize("truth", [False, True], ids=["flag_off", "flag_on"])
def test_camera_exception_row_message_is_a_constant_only_under_flag_on(monkeypatch, client, truth):
    """PIN (post-green ruling R9(b); mutation 'str(e) under flag 1' reddens
    [flag_on], mutation 'constant unflagged' reddens [flag_off]): an exception
    message is exactly the class R1 targets (R-METER measured an OpenAI key tail
    in a camera str(e)), so under flag 1 the camera EXCEPTION row logs the
    constant 'camera_exception' (mirroring url_compare_exception /
    quick_compare_exception) and never the exception text. Flag OFF keeps
    today's str(e) byte-identically -- the pre-existing leak the flag closes."""
    _flags(monkeypatch, truth=truth)
    r, calls, labels = _camera(monkeypatch, client, raises=True)
    assert r.status_code == 200, r.text[:200]
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    assert [lb for lb in labels if lb.startswith("log_search")] == ["log_search.camera.failure"], labels
    if truth:
        assert calls[0]["error_message"] == "camera_exception", calls
        assert CAM_RAISE_TEXT not in repr(calls), calls
    else:
        assert calls[0]["error_message"] == CAM_RAISE_TEXT, calls
        assert "cost" not in calls[0], calls


# ===========================================================================
# 27-31  /url/compare (flag 1)
# ===========================================================================
def test_url_compare_success_writes_one_log_row(monkeypatch, client):
    """RED (test 27, T8; M12, M14): a delivered URL comparison writes one row:
    input_type 'url', success True, products_found from the result, query =
    scheme+host+path of each url (query string + fragment DROPPED), an int
    duration_ms, label log_search.url.success. HEAD: zero rows."""
    _flags(monkeypatch, truth=True)
    r, calls, labels = _url(monkeypatch, client, result=URL_OK,
                            url1="https://x.test/a?utm=1&sid=abc#f", url2="https://x.test/b#frag")
    assert r.status_code == 200, r.text[:200]
    assert len(calls) == 1, f"no url row: {calls}"
    kw = _norm(calls[0])
    assert kw["input_type"] == "url" and kw["success"] is True, kw
    assert kw["products_found"] == ["Ab one", "two"], kw
    assert kw["query"] == "https://x.test/a vs https://x.test/b", kw
    assert kw["duration_ms"] == INT, kw
    assert labels == ["log_search.url.success"], labels


_URL_FAIL = [
    # post-green ruling R9(a): the '<2 products' exit's message is a route-owned
    # code constant (url_extraction_service.py:596), not exception text, so the
    # ROW logs that literal VERBATIM (the floor applies to anything else).
    ("few_products", dict(result=URL_FEW), 400, "Could not extract both products",
     "usage_refund.url.compare.failure", "log_search.url.failure"),
    ("llm_unavailable", dict(result=URL_LLM), 503, scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
     "usage_refund.url.compare.failure", "log_search.url.failure"),
    ("exception", dict(raises=True), 500, "url_compare_exception",
     "usage_refund.url.compare.exception", "log_search.url.exception"),
]


@pytest.mark.parametrize("authed_meter", [False, True], ids=["anon", "authed_metered"])
@pytest.mark.parametrize("case,kw,status,msg,refund,label", _URL_FAIL, ids=[c[0] for c in _URL_FAIL])
def test_url_compare_failure_and_exception_rows(monkeypatch, client, authed_meter,
                                                case, kw, status, msg, refund, label):
    """RED (test 28, T8 + ruling C3; M12, M13 str(e), M26 row before refund, M28
    row after the raise): each non-delivery exit writes ONE failure row with a
    constant message (never the exception text; a codeless result passes the
    W4-9 floor, red-gate ruling R1), the status is unchanged, and
    with metering ON + authed the row is recorded AFTER its refund label.
    HEAD: zero rows."""
    _flags(monkeypatch, truth=True)
    r, calls, labels = _url(monkeypatch, client, user=(AUTHED if authed_meter else None),
                            meter=authed_meter, **kw)
    assert r.status_code == status, (r.status_code, r.text[:200])
    assert len(calls) == 1, f"[{case}] no url failure row: {calls}"
    c = calls[0]
    assert c["success"] is False and c["input_type"] == "url", c
    assert c["error_message"] == msg, c
    assert URL_SECRET not in repr(c) and "postgres://" not in repr(c), c
    assert label in labels, labels
    if authed_meter:
        assert refund in labels, labels
        assert labels.index(refund) < labels.index(label), f"row must follow the refund (C3): {labels}"


@pytest.mark.parametrize("case", ["success", "failure", "exception"])
def test_url_compare_flag_off_writes_no_row(monkeypatch, client, case):
    """PIN (test 29): flags unset -> /url/compare writes no row on any exit."""
    _flags(monkeypatch, token=TOK)
    kw = {"success": dict(result=URL_OK), "failure": dict(result=URL_FEW),
          "exception": dict(raises=True)}[case]
    _, calls, labels = _url(monkeypatch, client, headers={HEADER: TOK}, **kw)
    assert calls == [], calls
    assert not any(lb.startswith("log_search") for lb in labels), labels


@pytest.mark.parametrize("case", ["ssrf_blocked_400", "usage_limit_429"])
def test_url_pre_gate_400_and_429_write_no_row(monkeypatch, client, case):
    """PIN-ON (test 30): the pre-gate SSRF 400 and the 429 USAGE_LIMIT ran no
    comparison, so they write no row even under both flags."""
    _flags(monkeypatch, truth=True, marker=True, token=TOK)
    if case == "ssrf_blocked_400":
        r, calls, _ = _url(monkeypatch, client, result=URL_OK, valid=False)
        assert r.status_code == 400
    else:
        r, calls, _ = _url(monkeypatch, client, result=URL_OK, user=AUTHED, meter=True, allowed=False)
        assert r.status_code == 429
    assert calls == [], calls


@pytest.mark.parametrize("who", ["anon", "authed"])
@pytest.mark.parametrize("verb", ["post", "get"])
@pytest.mark.parametrize("case", ["success", "failure", "exception"])
def test_url_rows_carry_the_callers_user_id(monkeypatch, client, who, verb, case):
    """PIN (red-gate ruling R4 'pass user_id'; adversary round-1 N9: a url row
    builder passing user_id=None reddens every authed node): under flag 1 the
    url row of every exit, on both verbs, carries the caller's id from
    get_optional_user, and None for an anonymous caller like every other
    site."""
    _flags(monkeypatch, truth=True)
    kw = {"success": dict(result=URL_OK), "failure": dict(result=URL_FEW),
          "exception": dict(raises=True)}[case]
    user = AUTHED if who == "authed" else None
    _, calls, _ = _url(monkeypatch, client, user=user, verb=verb, **kw)
    assert len(calls) == 1, calls
    assert "user_id" in calls[0], calls
    assert calls[0]["user_id"] == (AUTHED["id"] if user else None), calls


@pytest.mark.parametrize("header,expected", [(TOK, True), ("not-the-token", False)],
                         ids=["matching", "wrong"])
def test_url_get_row_carries_the_synthetic_classification(monkeypatch, client, header, expected):
    """PIN (adversary round-1 N10: dropping `search_log_extra=` from the GET
    /api/v1/url/compare handler reddens both nodes -- the kwarg vanishes): the
    GET verb classifies its row exactly as the POST verb does, True for the
    matching token and an explicit False otherwise."""
    _flags(monkeypatch, truth=True, marker=True, token=TOK)
    r, calls, _ = _url(monkeypatch, client, result=URL_OK, verb="get", headers={HEADER: header})
    assert r.status_code == 200, r.text[:200]
    assert len(calls) == 1, calls
    assert calls[0].get("is_synthetic", "ABSENT") is expected, calls


def test_url_log_query_strips_query_and_fragment():
    """GREEN-PIN (test 31; M14): `url_routes._url_log_query(url1, url2)` keeps
    scheme + host + path and drops the query string and fragment (tracking /
    session tokens must not land in an analytics table); a malformed url gives
    '' for its half, never a raise. Absent at HEAD by design."""
    fn = getattr(url_routes, "_url_log_query", None)
    assert callable(fn), "url_routes._url_log_query is absent"
    assert fn("https://x.test/p?utm=1&sid=abc#f", "https://x.test/q") == "https://x.test/p vs https://x.test/q"
    bad = fn("http://[::1", "https://x.test/q")
    assert isinstance(bad, str) and "[::1" not in bad and bad.endswith("https://x.test/q"), bad


# ===========================================================================
# R1  the W4-9 codeless floor on every failure row (red-gate ruling R1)
# ===========================================================================
R1_LEAK = "boom sk-live-000"
R1_CODELESS = {"success": False, "error": R1_LEAK, "total_cost": 0.004}


@pytest.mark.parametrize("surface", ["post", "get", "url", "quick", "stream_terminal"])
def test_codeless_failure_row_is_floored_under_flag_on(monkeypatch, client, surface):
    """PIN (red-gate ruling R1; M30b = bypass the floor): under flag 1 a
    CODELESS failure whose text is not a reviewed sentence ('boom sk-live-000')
    logs INTERNAL_ERROR_FRIENDLY_MESSAGE -- the SAME `_is_codeless_safe_message`
    floor the response uses, no second allowlist -- on T1 (POST/GET), T3 (the
    stream terminal), T8 (url) and T9 (quick). Coded messages stay unchanged
    (test 17); T4's error event is already floored by W4-9 before capture."""
    _flags(monkeypatch, truth=True)
    if surface in ("post", "get"):
        _, calls, _ = _sync(monkeypatch, client, surface, R1_CODELESS)
    elif surface == "url":
        _, calls, _ = _url(monkeypatch, client, result=R1_CODELESS)
    elif surface == "quick":
        _, calls, _ = _quick(monkeypatch, client, R1_CODELESS)
    else:
        calls = asyncio.run(_stream(monkeypatch, _term(R1_CODELESS)))["calls"]
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    assert calls[0]["error_message"] == scs.INTERNAL_ERROR_FRIENDLY_MESSAGE, calls
    assert "sk-live" not in repr(calls), calls


@pytest.mark.parametrize("verb", ["post", "get"])
def test_codeless_failure_row_keeps_the_raw_text_flag_off(monkeypatch, client, verb):
    """PIN (red-gate ruling R1, flag OFF): today's `result.get('error')` is
    written byte-identically. This DOCUMENTS the pre-existing str(e)-in-
    search_logs leak that flag 1 closes -- it is never fixed unflagged."""
    _flags(monkeypatch)
    _, calls, _ = _sync(monkeypatch, client, verb, R1_CODELESS)
    assert len(calls) == 1 and calls[0]["error_message"] == R1_LEAK, calls
    assert "cost" not in calls[0], calls


# ===========================================================================
# R3  the camera failure cost, three rungs (red-gate ruling R3)
# ===========================================================================
_CAM_RUNGS = [
    ("rung1_top_level_plus_vision", FAIL_ID, 0.02),
    ("rung1_top_level_wins_over_metadata", FAIL_BOTH_KEYS, 0.02),
    ("rung2_metadata_as_is", {"success": False, "code": "INSUFFICIENT_DATA", "error": "x",
                              "metadata": {"total_cost": 0.01}}, 0.013),
    ("rung3_vision_alone", FAIL_CONTENT, 0.003),
]


@pytest.mark.parametrize("case,result,cost", _CAM_RUNGS, ids=[c[0] for c in _CAM_RUNGS])
def test_camera_unsuccessful_cost_three_rungs(monkeypatch, client, case, result, cost):
    """PIN (red-gate ruling R3; mutation 'drop rung 3' reddens rung3): the
    camera.unsuccessful row (metering ON) logs rung 1 top-level total_cost +
    vision 0.003 (no double count even when metadata also carries a cost),
    else rung 2 metadata.total_cost AS-IS (the route already added vision:
    0.01 -> 0.013), else rung 3 vision alone (a moderation refusal carries no
    total_cost -- the vision call was still paid, so never 0.0)."""
    _flags(monkeypatch, truth=True)
    _, calls, _ = _camera(monkeypatch, client, result=copy.deepcopy(result), meter=True)
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    assert calls[0].get("cost") == cost, calls


# ===========================================================================
# R4  the url row's query drops userinfo and keeps the port (ruling R4)
# ===========================================================================
def test_url_log_query_drops_userinfo_and_keeps_the_port():
    """PIN (red-gate ruling R4; mutation 'keep userinfo' reddens it, and so
    does dropping the port): `user:pass@` never lands in search_logs; an
    explicit port is kept; a malformed port gives '' for that half."""
    fn = url_routes._url_log_query
    got = fn("https://user:s3cret@x.test:8443/p?sid=1#f", "http://tok@y.test/q")
    assert got == "https://x.test:8443/p vs http://y.test/q", got
    assert "s3cret" not in got and "user" not in got and "tok" not in got, got
    assert fn("http://x.test:notaport/p", "https://x.test/q") == " vs https://x.test/q"


# ===========================================================================
# R9(a)  the url '<2 products' row logs its own literal verbatim
# ===========================================================================
_URL_FEW_LIT = "Could not extract both products"


@pytest.mark.parametrize("case,error,logged", [
    ("the_literal", _URL_FEW_LIT, _URL_FEW_LIT),
    ("literal_plus_exception_tail", _URL_FEW_LIT + ": " + R1_LEAK, None),
    ("literal_padded", " " + _URL_FEW_LIT, None),
    ("other_codeless_text", "boom sk-live-000", None),
], ids=["the_literal", "literal_plus_exception_tail", "literal_padded", "other_codeless_text"])
def test_url_failure_row_logs_only_its_own_literal_verbatim(monkeypatch, client, case, error, logged):
    """PIN (post-green ruling R9(a); mutation 'floor the literal' reddens
    [the_literal], mutations 'prefix / strip match' redden the near misses):
    under flag 1 a CODELESS url failure whose message IS the route-owned
    literal logs it verbatim; one whose message is anything else (the literal
    with an exception tail, padded, or other text) logs
    INTERNAL_ERROR_FRIENDLY_MESSAGE. The 400 body is unchanged either way."""
    _flags(monkeypatch, truth=True)
    r, calls, _ = _url(monkeypatch, client, result={"success": False, "error": error, "details": []})
    assert r.status_code == 400, (r.status_code, r.text[:200])
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    assert calls[0]["error_message"] == (logged or scs.INTERNAL_ERROR_FRIENDLY_MESSAGE), calls
    assert "sk-live" not in repr(calls), calls


def test_url_few_products_literal_is_the_services_own_constant():
    """PIN (post-green ruling R9(a)): the literal url_routes passes through
    verbatim is byte-for-byte the one url_extraction_service returns on its
    '<2 products' exit, so a copy edit in the service cannot silently turn the
    verbatim row into the floor constant (or the reverse)."""
    lit = getattr(url_routes, "_URL_FEW_PRODUCTS_MESSAGE", None)
    assert lit == _URL_FEW_LIT, lit
    src = (REPO_ROOT / "app" / "services" / "url_extraction_service.py").read_text(encoding="utf-8")
    assert f'"error": "{lit}"' in src, "url_extraction_service no longer returns the literal"


# ===========================================================================
# T9  POST /api/v1/text/quick (ruling Q7 / D1)
# ===========================================================================
@pytest.mark.parametrize("case", ["success", "coded_failure", "codeless_failure", "exception"])
def test_quick_compare_writes_rows_flag_on(monkeypatch, client, case):
    """RED (ruling Q7/D1, T9): the paid anonymous /text/quick writes a row under
    flag 1: input_type 'text', cost from the result, an int duration_ms. The
    coded failure keeps the result's reviewed message; a codeless failure and a
    raise never log the exception text. Status unchanged (200 / 400 / 400 /
    500). HEAD: zero rows (measured, review D1)."""
    _flags(monkeypatch, truth=True)
    spec = {
        "success": (dict(result=DELIVERED), 200, True, 0.01, "log_search.text.quick.success"),
        "coded_failure": (dict(result=FAIL_ID), 400, False, 0.017, "log_search.text.quick.failure"),
        "codeless_failure": (dict(result={"success": False, "error": LEAK, "total_cost": 0.004}), 400,
                             False, 0.004, "log_search.text.quick.failure"),
        "exception": (dict(raises=True), 500, False, 0.0, "log_search.text.quick.exception"),
    }[case]
    kw, status, success, cost, label = spec
    r, calls, labels = _quick(monkeypatch, client, **kw)
    assert r.status_code == status, (r.status_code, r.text[:200])
    assert len(calls) == 1, f"[{case}] /text/quick wrote no row: {calls}"
    c = _norm(calls[0])
    assert c["input_type"] == "text" and c["query"] == "p1 vs p2", c
    assert c["success"] is success and c.get("cost") == cost and c["duration_ms"] == INT, c
    assert "sk-proj" not in repr(c), f"the exception/str(e) text reached the row: {c}"
    if case == "success":
        assert c["products_found"] == ["A 1", "B 2"] and "error_message" not in c, c
    elif case == "coded_failure":
        assert c["error_message"] == FAIL_ID["error"], c
    else:
        assert isinstance(c.get("error_message"), str) and c["error_message"], c
    assert labels == [label], labels


# ===========================================================================
# R7  a delivery row is total and sits AFTER its metering (quick + url)
# ===========================================================================
_ODD_DELIVERED = {
    "metadata_none": dict(DELIVERED, metadata=None),
    "metadata_str": dict(DELIVERED, metadata="x"),
    "products_int": dict(DELIVERED, products=5),
    "products_none": dict(DELIVERED, products=None),
    # adversary round-1 N5: a LIST whose items are not all dicts -- only the
    # per-item isinstance filter in _log_products_found keeps this a 200.
    "products_mixed": dict(DELIVERED, products=[None, "s", 7, {"brand": "A", "name": "1"}]),
}


@pytest.mark.parametrize("case", list(_ODD_DELIVERED))
def test_quick_success_row_never_changes_the_response(monkeypatch, client, case):
    """PIN (ruling R7, adversary defect 1; round-1 N5: products_mixed reddens
    when the per-item isinstance(p, dict) filter is dropped): the /text/quick
    delivery row is TOTAL over the result -- a success result whose metadata
    is None / not a dict, whose products is not a list, or whose products
    list holds None / str / int items still answers 200 with the SAME body
    under flag 1 as under flag OFF (HEAD's quick success path never reads
    metadata or products). Before the fix, metadata None raised AttributeError
    after record_anon and turned the 200 into a 500 under flag 1 only. The row
    is still written: cost 0 and products_found [] for the unreadable parts."""
    _flags(monkeypatch)
    r_off, calls_off, _ = _quick(monkeypatch, client, _ODD_DELIVERED[case])
    _flags(monkeypatch, truth=True)
    r_on, calls_on, labels = _quick(monkeypatch, client, _ODD_DELIVERED[case])
    assert r_off.status_code == 200 and calls_off == [], (r_off.status_code, calls_off)
    assert r_on.status_code == 200, (r_on.status_code, r_on.text[:200])
    assert r_on.json() == r_off.json()
    assert labels == ["log_search.text.quick.success"], labels
    c = calls_on[0]
    assert c["success"] is True, c
    if case.startswith("metadata"):
        assert c["cost"] == 0 and c["products_found"] == ["A 1", "B 2"], c
    elif case == "products_mixed":
        assert c["products_found"] == ["A 1"] and c["cost"] == 0.01, c
    else:
        assert c["products_found"] == [] and c["cost"] == 0.01, c


_URL_ODD_PRODUCTS = {
    "products_int": (5, []),
    "products_none": (None, []),
    "products_mixed": ([None, "s", 7, {"brand": "Ab", "name": "one"}], ["Ab one"]),
}


@pytest.mark.parametrize("case", list(_URL_ODD_PRODUCTS))
def test_url_success_row_never_changes_the_response(monkeypatch, client, case):
    """PIN (ruling R7; adversary round-1 N5: dropping the per-item
    isinstance(p, dict) filter in _log_products_found reddens products_mixed):
    the /url/compare delivery row is total over `products` -- a non-list
    products, or a list holding None / str / int items, answers 200 with the
    same body under flag 1 as OFF, and the row keeps only the dict items."""
    products, found = _URL_ODD_PRODUCTS[case]
    odd = dict(URL_OK, products=products)
    _flags(monkeypatch)
    r_off, calls_off, _ = _url(monkeypatch, client, result=odd)
    _flags(monkeypatch, truth=True)
    r_on, calls_on, labels = _url(monkeypatch, client, result=odd)
    assert r_off.status_code == 200 and calls_off == [], (r_off.status_code, calls_off)
    assert r_on.status_code == 200, (r_on.status_code, r_on.text[:200])
    assert r_on.json() == r_off.json()
    assert labels == ["log_search.url.success"], labels
    assert calls_on[0]["products_found"] == found, calls_on


FP64 = "ab" * 32


def test_quick_success_row_sits_after_record_anon(monkeypatch, client):
    """PIN (adversary prove-nothing row 2; mutation 'row before the metering'
    reddens it): with the anonymous gate ON and a valid fingerprint, the
    /text/quick delivery row is recorded AFTER record_anon.quick, so the
    analytics builder can never stand in front of the metering call."""
    _flags(monkeypatch, truth=True)
    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")

    async def _allowed(fp):
        return {"allowed": True, "reason": "daily", "tier": "anon", "remaining": {}}
    monkeypatch.setattr(tr, "check_anon_usage_allowed", _allowed)
    monkeypatch.setattr(tr, "record_anon_comparison", lambda fp: _done())
    r, calls, labels = _quick(monkeypatch, client, DELIVERED, headers={"X-Device-Fingerprint": FP64})
    assert r.status_code == 200, r.text[:200]
    assert labels == ["record_anon.quick", "log_search.text.quick.success"], labels
    assert len(calls) == 1 and calls[0]["success"] is True, calls


def test_url_success_row_sits_after_its_metering(monkeypatch, client):
    """PIN (adversary prove-nothing row 2; mutation 'row before the metering'
    reddens it): with metering ON and an authed caller, the /url/compare
    delivery row is recorded AFTER save_comparison.url and record_lifetime.url."""
    _flags(monkeypatch, truth=True)
    r, calls, labels = _url(monkeypatch, client, result=URL_OK, user=AUTHED, meter=True)
    assert r.status_code == 200, r.text[:200]
    assert labels == ["save_comparison.url", "record_lifetime.url", "log_search.url.success"], labels
    assert len(calls) == 1 and calls[0]["success"] is True, calls


# ===========================================================================
# 15b  flag 2 alone (flag 1 OFF): the marker reaches every flag-OFF-branch row
# ===========================================================================
@pytest.mark.parametrize("site", SITES)
def test_marker_alone_adds_exactly_is_synthetic_to_head_rows(monkeypatch, client, site):
    """PIN (adversary prove-nothing row 1; mutations 'drop **_syn' at the
    flag-OFF branch of POST failure, GET failure, camera unsuccessful, stream
    error and camera exception each redden their node): with flag 2 ON + token
    + matching header and flag 1 OFF (a flag-1 rollback while flag 2 stays
    active), every site writes EXACTLY HEAD's rows and labels, each row with
    is_synthetic True added -- and the flag-1-only sites (url, quick, stream
    incomplete) still write nothing."""
    _flags(monkeypatch, marker=True, token=TOK)
    calls, labels = _drive_site(monkeypatch, client, site, headers={HEADER: TOK})
    exp_calls, exp_labels = HEAD_KW[site]
    assert [_norm(c) for c in calls] == [dict(c, is_synthetic=True) for c in exp_calls], calls
    assert labels == exp_labels, labels


# ===========================================================================
# C3  a raising row builder never skips a refund
# ===========================================================================
_C3_SITES = ["post_failure", "get_failure", "stream_error", "stream_incomplete",
             "camera_unsuccessful", "camera_exception", "camera_exception_anon",
             "url_failure", "url_exception"]
_C3_REFUND = {
    "post_failure": "usage_refund.text.post",
    "get_failure": "usage_refund.text.get",
    "stream_error": "usage_refund.text_stream",
    "stream_incomplete": "usage_refund.text_stream.incomplete",
    "camera_unsuccessful": "usage_refund.image.comparison_unsuccessful",
    "camera_exception": "usage_refund.image.comparison_failed",
    "camera_exception_anon": "usage_refund.image.anon.comparison_failed",
    "url_failure": "usage_refund.url.compare.failure",
    "url_exception": "usage_refund.url.compare.exception",
}
_BUILDERS = ("_failure_log_cost", "_camera_log_cost", "_url_log_query")


@pytest.mark.parametrize("site", _C3_SITES)
def test_raising_row_builder_still_fires_the_refund(monkeypatch, client, site):
    """RED (ruling C3, LOAD-BEARING; M26 = a new row built BEFORE its refund):
    every new/changed failure row is built AFTER its refund fire_and_forget, so
    a row builder that raises can never skip the refund. The builder must
    actually run (count >= 1) and the refund label must still be recorded.
    HEAD: the builder does not exist, so it is never called.
    Fable ruling R11(a) (adversary r2 X11b -- the T7 block moved BEFORE the
    camera refunds survived 234/234): the camera EXCEPTION row joins the set.
    Its builder is image_routes._log_cost_value(vision_cost); a raise there
    must still leave the reserved-credit refund (authed + metering) and the
    anon-credit refund (anon gate + metering + fingerprint)."""
    _flags(monkeypatch, truth=True)
    raiser = _Counter()
    for mod in (tr, image_routes, url_routes):
        for name in _BUILDERS:
            monkeypatch.setattr(mod, name, raiser, raising=False)
    if site in ("camera_exception", "camera_exception_anon"):
        anon = site == "camera_exception_anon"
        monkeypatch.setattr(image_routes, "_log_cost_value", raiser)
        monkeypatch.setenv(METER, "true")
        if anon:
            monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")
        ledger = _CamLedger()
        _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_raises=True)
        app.dependency_overrides[get_optional_user] = (lambda: None if anon else AUTHED)
        files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
        h = {"X-Request-ID": RID}
        if anon:
            h["X-Device-Fingerprint"] = FP64
        client.post("/api/v1/image/identify", files=files, headers=h)
        labels = ledger.labels
    elif site in ("post_failure", "get_failure"):
        _, _, labels = _sync(monkeypatch, client, site.split("_")[0], FAIL_ID, user=AUTHED)
    elif site == "stream_error":
        labels = asyncio.run(_stream(monkeypatch, [("status", {}), ("error", dict(ERR_EVENT))],
                                     user=AUTHED))["labels"]
    elif site == "stream_incomplete":
        labels = asyncio.run(_stream(monkeypatch, SIX, disconnect_after=0, user=AUTHED))["labels"]
    elif site == "camera_unsuccessful":
        monkeypatch.setenv(METER, "true")
        ledger = _CamLedger()
        _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=FAIL_ID)
        app.dependency_overrides[get_optional_user] = (lambda: AUTHED)
        files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
        client.post("/api/v1/image/identify", files=files, headers={"X-Request-ID": RID})
        labels = ledger.labels
    else:
        kw = dict(result=URL_FEW) if site == "url_failure" else dict(raises=True)
        _, _, labels = _url(monkeypatch, client, user=AUTHED, meter=True, **kw)
    assert raiser.n >= 1, f"[{site}] no truth-row builder ran (T1/T4/T5/T6/T7/T8 absent)"
    assert _C3_REFUND[site] in labels, f"[{site}] a raising row builder skipped the refund: {labels}"


# ===========================================================================
# R11(b)-(d)  the deliberate predicates (adversary r2 prove-nothing rows)
# ===========================================================================
NO_SUCCESS_KEY = {"products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
                  "metadata": {"total_cost": 0.01}}


def test_stream_terminal_without_a_success_key_keeps_heads_success_row(monkeypatch):
    """PIN-ON (Fable ruling R11(b); adversary r2 X7 -- T3's predicate
    `complete_response.get('success') is False` weakened to the falsy
    `not complete_response.get('success')` survived 234/234 -- reddens it):
    T3's `is False` is deliberate. A terminal settle_complete/complete payload
    WITHOUT a `success` key is not a success:False terminal, so under flag 1 it
    keeps HEAD's success row (products, metadata cost, the success label) --
    identical to flag OFF -- and the SSE bytes do not move."""
    _flags(monkeypatch)
    off = asyncio.run(_stream(monkeypatch, _term(NO_SUCCESS_KEY)))
    _flags(monkeypatch, truth=True)
    on = asyncio.run(_stream(monkeypatch, _term(NO_SUCCESS_KEY)))
    head_row = HEAD_KW["stream_success"][0]
    assert [_norm(c) for c in off["calls"]] == head_row, off["calls"]
    assert [_norm(c) for c in on["calls"]] == head_row, on["calls"]
    assert on["labels"] == off["labels"] == ["log_search.text_stream.success"], on["labels"]
    assert on["chunks"] == off["chunks"] and on["raised"] is off["raised"] is None


def test_a_zero_top_level_total_cost_is_a_valid_cost(monkeypatch, client):
    """PIN (Fable ruling R11(c); adversary r2 X14 -- `_log_cost_value`'s
    `v < 0` weakened to `v <= 0` survived 234/234 -- reddens it): a top-level
    total_cost of exactly 0.0 is a VALID cost, never a missing one, so it never
    falls through to metadata.total_cost. With metadata 0.02 beside it the
    failure row logs 0.0 (POST under flag 1), and the camera rung 1 logs
    0.0 + vision, not metadata's 0.02."""
    assert tr._log_cost_value(0.0) == 0.0 and tr._log_cost_value(0) == 0.0
    both = {"total_cost": 0.0, "metadata": {"total_cost": 0.02}}
    assert tr._failure_log_cost(both) == 0.0
    assert image_routes._camera_log_cost(both, 0.003) == 0.003
    _flags(monkeypatch, truth=True)
    res = dict(FAIL_ID, total_cost=0.0, metadata={"total_cost": 0.02})
    r, calls, _ = _sync(monkeypatch, client, "post", res)
    assert r.status_code == 400, (r.status_code, r.text[:200])
    assert len(calls) == 1 and calls[0]["success"] is False, calls
    assert type(calls[0]["cost"]) is float and calls[0]["cost"] == 0.0, calls


@pytest.mark.parametrize("partial", [1, "yes"], ids=["int_1", "str_yes"])
def test_partial_truthy_but_not_true_is_not_a_partial(monkeypatch, client, partial):
    """PIN-ON (Fable ruling R11(d); adversary r2 X15 -- `_partial_log_note`'s
    `md.get('partial') is True` weakened to truthy survived 234/234 -- reddens
    it): only `metadata.partial is True` (W4-4's own stamp) is a partial. A
    truthy-but-not-True value (1, 'yes') writes NO 'partial:' note: under flag
    1 the delivered row equals HEAD's delivered row exactly."""
    md = {"partial": partial, "partial_stage": "post_gather", "total_cost": 0.02}
    assert tr._partial_log_note({"metadata": dict(md)}) == {}
    _flags(monkeypatch, truth=True)
    _, calls, labels = _sync(monkeypatch, client, "post", dict(DELIVERED, metadata=md))
    assert [_norm(c) for c in calls] == [{
        "query": "a vs b", "input_type": "text", "user_id": None, "products_found": ["A 1", "B 2"],
        "success": True, "cost": 0.02, "duration_ms": INT}], calls
    assert labels == ["log_search.text.post.success"], labels


# ===========================================================================
# D4  the token never reaches Sentry
# ===========================================================================
@pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
@pytest.mark.parametrize("spelling", [HEADER, HEADER.lower()])
def test_sentry_scrubs_the_synthetic_header(hook, spelling):
    """RED (ruling Q3/D4): X-Qaren-Synthetic carries the secret token, so the
    shared request-region scrub (`sentry_service._scrub_request_region`; the
    review's `_scrub_request` is this function) redacts it in BOTH hooks, any
    case. HEAD redacts only authorization / x-admin-key / cookie (measured)."""
    fn = getattr(sentry_service, hook)
    ev = {"request": {"headers": {spelling: "tok123", "Accept": "a"}}}
    out = fn(ev, None)
    assert out["request"]["headers"][spelling] == "[REDACTED]", out["request"]["headers"]
    assert out["request"]["headers"]["Accept"] == "a"


# ===========================================================================
# 32-33  the eval harness
# ===========================================================================
_EVAL_Q = [{"id": "w413-q1", "query": "a vs b", "category": "electronics", "region": "bahrain",
            "max_wall_seconds": 25.0}]
HEAD_EVAL_HEADERS = {"accept", "accept-encoding", "connection", "host", "user-agent"}


async def _eval_headers():
    seen: list = []

    def handler(request):
        seen.append({k.lower(): v for k, v in request.headers.items()})
        return httpx.Response(200, json={"success": True})
    await eval_runner.run_eval(_EVAL_Q * 2, base_url="http://test", transport=httpx.MockTransport(handler))
    return seen


@pytest.mark.asyncio
async def test_eval_runner_sends_synthetic_header_when_token_set(monkeypatch):
    """RED (test 32): with SEARCH_LOG_SYNTHETIC_TOKEN set, every eval request
    carries X-Qaren-Synthetic == the token. HEAD sends no such header."""
    _flags(monkeypatch, token=TOK)
    seen = await _eval_headers()
    assert len(seen) == 2
    assert all(h.get(HEADER.lower()) == TOK for h in seen), seen


@pytest.mark.asyncio
async def test_eval_runner_no_header_without_token(monkeypatch):
    """PIN (test 33; M22 always-send reddens it): token unset -> the request
    header set equals HEAD's exactly."""
    _flags(monkeypatch)
    seen = await _eval_headers()
    assert seen and all(set(h) == HEAD_EVAL_HEADERS for h in seen), seen


# ===========================================================================
# 34  phones: nothing client-visible changes in any flag state
# ===========================================================================
def _client_surface(monkeypatch, client):
    saved = app.openapi_schema
    app.openapi_schema = None
    try:
        spec = app.openapi()
    finally:
        app.openapi_schema = saved
    paths = {p: spec["paths"].get(p) for p in (
        "/api/v1/text/compare", "/api/v1/text/compare/stream", "/api/v1/text/quick",
        "/api/v1/url/compare", "/api/v1/image/identify")}
    hdr = {HEADER: TOK}
    bodies = {}
    for name, fn in (
        ("post_success", lambda: _sync(monkeypatch, client, "post", DELIVERED, headers=hdr)),
        ("post_failure", lambda: _sync(monkeypatch, client, "post", FAIL_ID, headers=hdr)),
        ("url_success", lambda: _url(monkeypatch, client, result=URL_OK, headers=hdr)),
        ("url_failure", lambda: _url(monkeypatch, client, result=URL_FEW, headers=hdr)),
        ("url_get_success", lambda: _url(monkeypatch, client, result=URL_OK, headers=hdr,
                                         verb="get")),
        ("quick_success", lambda: _quick(monkeypatch, client, DELIVERED, headers=hdr)),
    ):
        r = fn()[0]
        bodies[name] = (r.status_code, r.json())
    sse = asyncio.run(_stream(monkeypatch, _term(PARTIAL), headers=hdr))["chunks"]
    sse_err = asyncio.run(_stream(monkeypatch, [("status", {}), ("error", dict(ERR_EVENT))],
                                  headers=hdr))["chunks"]
    return paths, bodies, sse, sse_err


def test_no_client_visible_change_in_any_flag_state(monkeypatch, client):
    """PIN (test 34 + ruling C7): the OpenAPI paths/params of every touched
    route, the status + JSON of the stubbed POST success/failure, url
    success/failure and quick success (fixed X-Request-ID), and the SSE event
    sequence are EQUAL across flags OFF and both flags ON + token + header.
    Only the server-side analytics insert may differ."""
    _flags(monkeypatch, token=TOK)
    off = _client_surface(monkeypatch, client)
    _flags(monkeypatch, truth=True, marker=True, token=TOK)
    on = _client_surface(monkeypatch, client)
    assert off[0] == on[0], "OpenAPI surface changed with the flags"
    assert off[1] == on[1], (off[1], on[1])
    assert off[2] == on[2] and off[3] == on[3], "SSE sequence changed with the flags"
    assert all(p is not None for p in off[0].values()), off[0]
