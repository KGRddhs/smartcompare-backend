"""S81-04c REFUSAL-LOG-HYGIENE: the frozen RED file (spec S81-04c section 5 as amended
by RULINGS_S81_04C R-04C-12..27 and the brief R-04C-1..11).

An ``api_budget_service.LLMUnavailableError`` (or any subclass) that reaches one of the
eight request-path except arms logs ONE WARNING by type (``<prefix>: <TypeName>``, no
exc_info, no exception text). Group A (parse, verdict, camera vision, url extract)
changes with every role flag OFF only (role ON is already WARNING by type, S81-06 GC-3);
group B (specs, price, price fallback, reviews) changes in both flag states (R-04C-12).
Every delivery, refund, status, raise / return flow, ``any_role_enabled()`` read
sequence and every NON-class record stays byte-identical (R-04C-3 / -4 / -5).

RED = fails at base a74caba7 on an AssertionError only. PIN = green at base, FULL
configuration (ruling B1: the S81-06 knob set, ENABLE_SONNET_ESCALATION,
ENABLE_OPENAI_PRE_V3, ENABLE_REQUEST_CONTEXT_HEADERS, every role flag in each PIN_OFF
spelling) plus the read / log recorder. Hermetic: fake OpenAI clients, no network, no
.env, synthetic values built at run time; every ENABLE_* is deleted first and set
explicitly per row. Pure ASCII: the em dash of the W1-3 message is chr(0x2014).
"""

import app.main  # noqa: F401  (first: the dotenv guard, tests/_env_safety)

import asyncio
import hashlib
import json
import logging
import os
import pathlib
import subprocess
import sys
import types

import pytest
from fastapi.testclient import TestClient

from app.api import image_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.middleware.rate_limiter import limiter
from app.services import api_budget_service as abs_
from app.services import extraction_service as es
from app.services import llm_router
from app.services import llm_spend_breaker as sb
from app.services import openai_service as osvc
from app.services import url_extraction_service as urlsvc
from app.services import usage_service

ROOT = pathlib.Path(__file__).resolve().parents[1]

ROLE_FLAGS = (
    "ENABLE_ANTHROPIC_TEXT",
    "ENABLE_ANTHROPIC_VISION",
    "ENABLE_ANTHROPIC_VERDICT",
    "ENABLE_ANTHROPIC_CRITIC",
    "ENABLE_ANTHROPIC_MODERATION",
)
ROLE_ON_FLAG = "ENABLE_ANTHROPIC_CRITIC"
PIN_OFF = (None, "", "false", "0", "off", " FALSE ")
SYN_ANTH = "syn" + "thetic" + "-anthropic-" + "s04c"
HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
KNOBS = {
    "ANTHROPIC_API_KEY": SYN_ANTH,
    "ANTHROPIC_MAX_RETRIES": "1",
    "ANTHROPIC_MODEL_TEXT": HAIKU,
    "ANTHROPIC_MODEL_VISION": HAIKU,
    "ANTHROPIC_MODEL_VERDICT": HAIKU,
    "ANTHROPIC_MODEL_CRITIC": HAIKU,
    "ANTHROPIC_MODEL_MODERATION": HAIKU,
    "ANTHROPIC_MODEL_ESCALATION": SONNET,
    "ANTHROPIC_CALL_DEADLINE_SECONDS": "17.5",
    "ANTHROPIC_CLASSIFY_LLM_TIMEOUT": "3.25",
    "ANTHROPIC_VISION_TIMEOUT_SECONDS": "13.75",
    "ANTHROPIC_TAIL_RESERVE_SECONDS": "4.25",
}

# The W1-3 denial message (api_budget_service.py:1009), the em dash built at run time.
W13_TEXT = (
    "openai circuit breaker denied admission " + chr(0x2014) + " dispatch suppressed"
)
SUB_TEXT = "synthetic sub refusal text"
PLAIN_TEXT = "synthetic plain failure text"
ZERO = {"prompt_tokens": 0, "completion_tokens": 0}
CAMERA_USER = "s04c-camera-user"
JPEG = b"\xff\xd8" + b"\x00" * 64
VISION_500_LITERAL = "Image analysis failed. Please try again."


class _S04cSubRefusal(abs_.LLMUnavailableError):
    """A test-local subclass: the arm must print ITS name (R-04C-6)."""


ARMS = (
    "parse",
    "specs",
    "price",
    "price_training",
    "reviews",
    "verdict",
    "url_extract",
)
ALL_ARMS = ARMS + ("camera",)
GROUP_A = ("parse", "verdict", "url_extract", "camera")
GROUP_B = ("specs", "price", "price_training", "reviews")
PREFIX = {
    "parse": "Product parsing error",
    "specs": "Specs extraction error",
    "price": "Price extraction error",
    "price_training": "Price fallback error",
    "reviews": "Reviews extraction error",
    "verdict": "Comparison generation error",
    "url_extract": "AI extraction error",
    "camera": "[IMAGE] Vision call failed",
}
LOGGER = {
    a: "app.services.extraction_service"
    for a in ("parse", "specs", "price", "price_training", "reviews", "verdict")
}
LOGGER["url_extract"] = "app.services.url_extraction_service"
LOGGER["camera"] = "app.api.image_routes"
WATCHED = sorted(
    set(LOGGER.values())
    | {"app.services.openai_service", "app.services.llm_spend_breaker"}
)

# The base record of a NON-class exception (RuntimeError(PLAIN_TEXT)), measured at
# a74caba7 (spec 1.3): (level, exc_info?, getMessage(), str(record.msg)).
P1_BASE = {
    "parse": ("ERROR", True, "Product parsing error: " + PLAIN_TEXT, None),
    "specs": (
        "ERROR",
        False,
        "Specs extraction error: RuntimeError: " + PLAIN_TEXT,
        "Specs extraction error: %s",
    ),
    "price": (
        "ERROR",
        False,
        "Price extraction error: RuntimeError: " + PLAIN_TEXT,
        "Price extraction error: %s",
    ),
    "price_training": (
        "ERROR",
        False,
        "Price fallback error: RuntimeError: " + PLAIN_TEXT,
        "Price fallback error: %s",
    ),
    "reviews": ("ERROR", True, "Reviews extraction error: " + PLAIN_TEXT, None),
    "verdict": ("ERROR", True, "Comparison generation error: " + PLAIN_TEXT, None),
    "url_extract": (
        "ERROR",
        False,
        "AI extraction error: RuntimeError",
        "AI extraction error: %s",
    ),
    "camera": ("ERROR", False, "[IMAGE] Vision call failed: " + PLAIN_TEXT, None),
}

P1 = {
    "name": "iPhone 17",
    "brand": "Apple",
    "category": "electronics",
    "specs": {"battery": "3500 mAh"},
    "reviews": {"average_rating": 4.5, "review_summary": {"consensus": "Solid phone."}},
}
P2 = {
    "name": "Galaxy S25",
    "brand": "Samsung",
    "category": "electronics",
    "specs": {"battery": "4000 mAh"},
    "reviews": {"average_rating": 4.4},
}
HTML = (
    "<html><head><title>Apple iPhone 17 256GB</title></head><body>"
    "<h1>Apple iPhone 17</h1><p>Price 312.500 BHD.</p></body></html>"
)


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------
def _run(coro):
    return asyncio.run(coro)


async def _capture(coro):
    """('ok', value) or ('raised', exc): a RED never escapes as an error."""
    try:
        return "ok", await coro
    except Exception as e:  # noqa: BLE001
        return "raised", e


class _Completions:
    def __init__(self, exc=None, reply=None):
        self.exc, self.reply, self.calls = exc, reply, 0

    async def create(self, **_kw):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.reply


class _FakeClient:
    def __init__(self, exc=None, reply=None):
        self.completions = _Completions(exc, reply)
        self.chat = types.SimpleNamespace(completions=self.completions)

    def with_options(self, **_kw):
        return self


def _no_content_reply():
    msg = types.SimpleNamespace(
        content=None, refusal="synthetic vision refusal", role="assistant"
    )
    ch = types.SimpleNamespace(message=msg, finish_reason="stop", index=0)
    usage = types.SimpleNamespace(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        prompt_tokens_details=types.SimpleNamespace(cached_tokens=0),
    )
    return types.SimpleNamespace(choices=[ch], usage=usage, model="gpt-4o-mini")


class _Recorder(logging.Handler):
    """One ordered list: ('read', value) from any_role_enabled and
    ('log', logger, level, exc_info?, getMessage(), str(msg)) from the watched loggers.
    """

    def __init__(self, events):
        super().__init__(level=logging.DEBUG)
        self.events = events

    def emit(self, record):
        self.events.append(
            (
                "log",
                record.name,
                record.levelname,
                bool(record.exc_info),
                record.getMessage(),
                str(record.msg),
            )
        )


class _RootErrors(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records = []

    def emit(self, record):
        self.records.append((record.name, record.levelname, record.getMessage()))


@pytest.fixture(autouse=True)
def _s04c_env(monkeypatch):
    for k in list(os.environ):
        if (
            k.startswith("ENABLE_")
            or k.startswith("ANTHROPIC_")
            or k.startswith("LLM_SPEND_")
        ):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(limiter, "enabled", False)
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()
    yield
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()


@pytest.fixture
def rec(monkeypatch):
    events = []
    real = llm_router.any_role_enabled

    def _reader():
        v = real()
        events.append(("read", v))
        return v

    monkeypatch.setattr(llm_router, "any_role_enabled", _reader)
    handler = _Recorder(events)
    prev = {}
    for name in WATCHED:
        lg = logging.getLogger(name)
        prev[name] = (lg.level, lg.disabled)
        lg.disabled = False
        lg.setLevel(logging.DEBUG)
        lg.addHandler(handler)
    root_errors = _RootErrors()
    logging.getLogger().addHandler(root_errors)
    ns = types.SimpleNamespace(events=events, root_errors=root_errors)
    yield ns
    for name in WATCHED:
        lg = logging.getLogger(name)
        lg.removeHandler(handler)
        lg.setLevel(prev[name][0])
        lg.disabled = prev[name][1]
    logging.getLogger().removeHandler(root_errors)


def _full_config(mp, state, off_value=None):
    """FULL configuration (ruling B1). state 'off': every role flag = off_value;
    state 'on': ENABLE_ANTHROPIC_CRITIC + ENABLE_OPENAI_PRE_V3 (any_role_enabled()
    True, every site still OpenAI, nothing refuses)."""
    for k, v in KNOBS.items():
        mp.setenv(k, v)
    mp.setenv("ENABLE_SONNET_ESCALATION", "true")
    mp.setenv("ENABLE_OPENAI_PRE_V3", "true")
    mp.setenv("ENABLE_REQUEST_CONTEXT_HEADERS", "true")
    for name in ROLE_FLAGS:
        if off_value is None:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, off_value)
    if state == "on":
        mp.setenv(ROLE_ON_FLAG, "true")


def _source(mp, kind):
    """The class source of a row; returns the fake OpenAI client."""
    if kind == "w13":
        mp.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
        mp.setattr(abs_, "_openai_dispatch_admission", lambda: (False, False, False))
        return _FakeClient(exc=AssertionError("dispatched past a W1-3 denial"))
    if kind == "spend":
        mp.setenv("ENABLE_LLM_SPEND_BREAKER", "true")

        async def _admit(*_a, **_k):
            sb._refuse_dispatch("live", 1.0, 0.1)

        mp.setattr(sb, "admit_openai_dispatch", _admit)
        return _FakeClient(exc=AssertionError("dispatched past a spend refusal"))
    if kind == "sub":
        return _FakeClient(exc=_S04cSubRefusal(SUB_TEXT))
    if kind == "runtime":
        return _FakeClient(exc=RuntimeError(PLAIN_TEXT))
    if kind == "v2":
        mp.setenv("ENABLE_VISION_IDENTITY_V2", "true")
        return _FakeClient(reply=_no_content_reply())
    raise AssertionError(kind)  # pragma: no cover


async def _drive(arm, mp, fake):
    getc = lambda *a, **k: fake  # noqa: E731
    if arm == "url_extract":
        mp.setattr(urlsvc, "get_client", getc)
        return await urlsvc.extract_with_ai(
            "https://www.example-retailer.test/p/iphone-17",
            HTML,
            {"key": "generic", "name": "Example"},
        )
    mp.setattr(es, "get_client", getc)
    if arm == "parse":
        return await es.parse_product_query("iPhone 17 vs Galaxy S25")
    if arm == "specs":
        return await es.extract_specs(
            "Apple", "iPhone 17", "256GB", "electronics", "[snippet_1] battery 3500 mAh"
        )
    if arm == "price":
        return await es.extract_price(
            "Apple", "iPhone 17", None, "bahrain", "[snippet_1] 312.500 BHD"
        )
    if arm == "price_training":
        return await es.extract_price_from_training_data(
            "Apple", "iPhone 17", None, "bahrain"
        )
    if arm == "reviews":
        return await es.extract_reviews(
            "Apple", "iPhone 17", None, "[snippet_1] great phone"
        )
    if arm == "verdict":
        from app.services.model_router_service import model_router

        async def _gm(*_a, **_k):
            return "gpt-4o"

        async def _ru(*_a, **_k):
            return None

        mp.setattr(model_router, "get_model", _gm)
        mp.setattr(model_router, "record_usage", _ru)
        return await es.generate_comparison(
            P1, P2, "bahrain", category="electronics", scores_summary="P1 72 / P2 70"
        )
    raise AssertionError(arm)  # pragma: no cover


def run_arm(arm, mp, kind):
    fake = _source(mp, kind)
    return _run(_capture(_drive(arm, mp, fake)))


class _Ledger:
    def __init__(self):
        self.consumes, self.refunds, self.anon_refunds, self.labels = [], [], [], []

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)

        async def _r():
            return {
                "allowed": True,
                "reason": None,
                "tier": "free",
                "consumed": True,
                "consumed_keys": None,
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
            }

        return _r()

    def refund(self, user_id, consumed_keys=None, *_a, **_kw):
        self.refunds.append((user_id, consumed_keys))

        async def _r():
            return None

        return _r()

    def anon_refund(self, device_fp, consumed_keys=None, *_a, **_kw):
        self.anon_refunds.append((device_fp, consumed_keys))

        async def _r():
            return None

        return _r()


def run_camera(mp, kind, *, anon=False):
    """POST /api/v1/image/identify (authed by default, metering ON) with the class
    source of the row; returns (response, ledger)."""
    fake = _source(mp, kind)
    mp.setattr(osvc, "client", fake)
    mp.setenv("ENABLE_PAID_ROUTE_METERING", "true")
    led = _Ledger()
    for mod in (usage_service, image_routes):
        mp.setattr(mod, "consume_comparison_credit", led.consume, raising=False)
        mp.setattr(mod, "refund_comparison_credit", led.refund, raising=False)
    mp.setattr(image_routes, "refund_anon_comparison_credit", led.anon_refund)
    real_ff = image_routes.fire_and_forget

    def _ff(coro, *a, **kw):
        led.labels.append(kw.get("label"))
        return real_ff(coro, *a, **kw)

    mp.setattr(image_routes, "fire_and_forget", _ff)
    headers = {}
    if anon:
        mp.setenv("ENABLE_ANON_USAGE_GATE", "true")
        fp = hashlib.sha256(b"s04c-synthetic-device").hexdigest()
        headers["x-device-fingerprint"] = fp
        keys = {"daily": "anon:daily:" + fp[:8]}

        async def _allowed(_fp):
            return {
                "allowed": True,
                "consumed": True,
                "consumed_keys": keys,
                "reason": None,
                "tier": "anonymous",
                "remaining": {"daily": 2},
            }

        mp.setattr(image_routes, "check_anon_usage_allowed", _allowed)
        app.dependency_overrides[get_optional_user] = lambda: None
        led.anon_keys = keys
        led.fp = fp
    else:
        app.dependency_overrides[get_optional_user] = lambda: {
            "id": CAMERA_USER,
            "email": "s04c@example.test",
            "access_token": "s04c-" + "bearer",
        }
    try:
        client = TestClient(app, raise_server_exceptions=False)
        files = [("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)]
        resp = client.post("/api/v1/image/identify", files=files, headers=headers)
    finally:
        app.dependency_overrides.pop(get_optional_user, None)
    return resp, led


def arm_logs(events, arm):
    """The arm's records: (level, exc_info?, getMessage(), str(msg))."""
    return [
        e[2:]
        for e in events
        if e[0] == "log" and e[1] == LOGGER[arm] and e[4].startswith(PREFIX[arm])
    ]


def by_type(arm, type_name):
    return [("WARNING", False, PREFIX[arm] + ": " + type_name, PREFIX[arm] + ": %s")]


def _fields(resp):
    try:
        return resp.json()
    except ValueError:  # pragma: no cover
        return {"raw": resp.text[:300]}


# ---------------------------------------------------------------------------
# P0: the synthetic texts stay clear of the verdict 429 matcher (R-04C-17)
# ---------------------------------------------------------------------------
def test_p0_synthetic_texts_avoid_the_verdict_matcher():
    """PIN (R-04C-17): no synthetic exception text holds '429', 'rate' or 'quota'
    (extraction_service.py:2702-2706 would run the verdict fallback dispatch)."""
    for text in (W13_TEXT, SUB_TEXT, PLAIN_TEXT):
        low = text.lower()
        assert not any(w in low for w in ("429", "rate", "quota")), text


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ARMS)
def test_r1_class_refusal_warns_by_type_role_off(monkeypatch, rec, arm):
    """R1 RED: W1-3 denial, every role flag OFF (FULL config): the arm logs ONE
    WARNING '<prefix>: LLMUnavailableError', no exc_info, no exception text."""
    _full_config(monkeypatch, "off")
    run_arm(arm, monkeypatch, "w13")
    got = arm_logs(rec.events, arm)
    assert got == by_type(arm, "LLMUnavailableError"), got
    assert all("dispatch suppressed" not in g[2] for g in got), got


def test_r2_camera_refusal_warns_by_type_role_off(monkeypatch, rec):
    """R2 RED: /api/v1/image/identify (authed, metering ON), W1-3 denial, role
    flags OFF: the vision arm logs ONE WARNING by type."""
    _full_config(monkeypatch, "off")
    resp, _led = run_camera(monkeypatch, "w13")
    got = arm_logs(rec.events, "camera")
    assert got == by_type("camera", "LLMUnavailableError"), (got, resp.status_code)


@pytest.mark.parametrize("arm", ALL_ARMS)
def test_r3_subclass_prints_its_own_name(monkeypatch, rec, arm):
    """R3 RED (R-04C-6): role flags OFF, a subclass raised by the fake create: one
    WARNING '<prefix>: _S04cSubRefusal', exc_info None, no exception text."""
    _full_config(monkeypatch, "off")
    if arm == "camera":
        run_camera(monkeypatch, "sub")
    else:
        run_arm(arm, monkeypatch, "sub")
    got = arm_logs(rec.events, arm)
    assert got == by_type(arm, "_S04cSubRefusal"), got
    assert all("synthetic sub" not in g[2] for g in got), got


@pytest.mark.parametrize("arm", GROUP_B)
def test_r4_group_b_role_on_warns_by_type(monkeypatch, rec, arm):
    """R4 RED (R-04C-12, group B in both states): role ON (CRITIC + PRE_V3), W1-3
    denial: one WARNING by type."""
    _full_config(monkeypatch, "on")
    run_arm(arm, monkeypatch, "w13")
    got = arm_logs(rec.events, arm)
    assert got == by_type(arm, "LLMUnavailableError"), got


def test_r5_vision_v2_no_content_warns_by_type(monkeypatch, rec):
    """R5 RED: ENABLE_VISION_IDENTITY_V2 ON, a no-content reply: the camera arm logs
    WARNING by type after the '[VISION_V2] no content' WARNING; status 503."""
    _full_config(monkeypatch, "off")
    resp, _led = run_camera(monkeypatch, "v2")
    assert resp.status_code == 503, resp.status_code
    seq = [
        e
        for e in rec.events
        if e[0] == "log"
        and (
            e[4].startswith("[VISION_V2] no content")
            or (e[1] == LOGGER["camera"] and e[4].startswith(PREFIX["camera"]))
        )
    ]
    assert [e[4] for e in seq][:1] == [
        "[VISION_V2] no content: finish_reason=stop refused=True"
    ], seq
    assert [e[2:] for e in seq[1:]] == by_type("camera", "LLMUnavailableError"), seq


def test_r6_spend_refusal_warns_by_type_after_the_spend_line(monkeypatch, rec):
    """R6 RED: ENABLE_LLM_SPEND_BREAKER ON + the admit calling the REAL _refuse_dispatch:
    at the parse arm the '[SPEND] ... dispatch refused' WARNING then the arm's WARNING by
    type; no ERROR record anywhere in the run."""
    _full_config(monkeypatch, "off")
    st, out = run_arm("parse", monkeypatch, "spend")
    assert st == "ok", out
    seq = [
        e
        for e in rec.events
        if e[0] == "log"
        and (e[4].startswith("[SPEND]") or e[4].startswith(PREFIX["parse"]))
    ]
    assert len(seq) == 2, seq
    spend, arm = seq
    assert spend[1] == "app.services.llm_spend_breaker" and spend[2] == "WARNING"
    assert spend[4].startswith("[SPEND] lane=live cap reached")
    assert spend[4].endswith("dispatch refused"), spend
    assert arm[2:] == by_type("parse", "LLMUnavailableError")[0], arm
    assert rec.root_errors.records == [], rec.root_errors.records


_SENTRY_CHILD = r"""
import asyncio, json, logging, os, sys, types
sys.path.insert(0, sys.argv[1])
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
for k in list(os.environ):
    if k.startswith("ENABLE_") or k.startswith("ANTHROPIC_") or k.startswith("LLM_SPEND_"):
        del os.environ[k]
import app.main  # noqa: F401
os.environ["SENTRY_DSN"] = "https://" + "s04cpublic" + "@" + "o0.ingest.example.invalid/1"
import sentry_sdk
from sentry_sdk.transport import Transport
EVENTS = []
class _Mem(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            ev = item.get_event()
            if ev is not None:
                EVENTS.append(ev)
    def flush(self, timeout, callback=None):
        return None
    def kill(self):
        return None
_real = sentry_sdk.init
def _init(*a, **kw):
    kw["transport"] = _Mem
    return _real(*a, **kw)
sentry_sdk.init = _init
from app.services.sentry_service import init_sentry
init_sentry()
from app.services import api_budget_service as abs_
from app.services import extraction_service as es
os.environ["ENABLE_LLM_PREFLIGHT_BREAKER"] = "true"
abs_._openai_dispatch_admission = lambda: (False, False, False)
class _Comp:
    calls = 0
    async def create(self, **kw):
        _Comp.calls += 1
        raise AssertionError("dispatched past a W1-3 denial")
fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=_Comp()))
es.get_client = lambda *a, **k: fake
out = asyncio.run(es.parse_product_query("iPhone 17 vs Galaxy S25"))
logging.getLogger("s04c.marker").error("s04c marker")
sentry_sdk.flush(timeout=5)
def _msg(ev):
    le = ev.get("logentry") or {}
    return str(le.get("formatted") or le.get("message") or ev.get("message") or "")
msgs = [_msg(ev) for ev in EVENTS]
print("RESULT " + json.dumps({
    "active": bool(sentry_sdk.get_client().is_active()),
    "marker": sum(1 for m in msgs if m == "s04c marker"),
    "arm": sum(1 for m in msgs if m.startswith("Product parsing error")),
    "dispatches": _Comp.calls,
    "delivered": out[0] == {"products": [], "error": es.PARSE_PRODUCT_QUERY_ERROR},
}))
"""


def test_r7_no_sentry_event_for_a_refusal():
    """R7 RED (R-04C-14): a child process (python -I, recording transport, the REAL
    init_sentry()) drives the parse arm with a W1-3 denial, then logs one marker at
    ERROR: exactly ONE marker event and ZERO events whose message starts with the arm's
    prefix (counted by prefix, never by total)."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("ENABLE_") and k not in ("SENTRY_DSN", "LIVE")
    }
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-I", "-c", _SENTRY_CHILD, str(ROOT)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, "child produced no RESULT rc=%s: %s" % (
        proc.returncode,
        proc.stderr[-1500:],
    )
    out = json.loads(lines[-1][len("RESULT ") :])
    assert out["active"] is True and out["dispatches"] == 0, out
    assert out["delivered"] is True, out
    assert out["marker"] == 1, out
    assert out["arm"] == 0, out


# ---------------------------------------------------------------------------
# PIN rows (FULL configuration + the read / log recorder)
# ---------------------------------------------------------------------------
P1_CASES = [(a, "off", None) for a in ALL_ARMS]
P1_CASES += [("parse", "off", v) for v in PIN_OFF if v is not None]
P1_CASES += [(a, "on", None) for a in ALL_ARMS]


@pytest.mark.parametrize("arm,state,off_value", P1_CASES)
def test_p1_non_class_record_byte_identical(monkeypatch, rec, arm, state, off_value):
    """P1 PIN (R-04C-5): RuntimeError(PLAIN_TEXT) at the arm keeps the base record
    (level, exc_info, message, template) in both flag states; the camera keeps 500."""
    _full_config(monkeypatch, state, off_value)
    if arm == "camera":
        resp, _led = run_camera(monkeypatch, "runtime")
        assert resp.status_code == 500, resp.status_code
        assert _fields(resp).get("error") == VISION_500_LITERAL, _fields(resp)
    else:
        st, _out = run_arm(arm, monkeypatch, "runtime")
        assert st == "ok", _out
    level, exc, message, msg = P1_BASE[arm]
    assert arm_logs(rec.events, arm) == [(level, exc, message, msg or message)]


W13_DELIVERY = {
    "parse": ({"products": [], "error": "product parsing unavailable"}, ZERO),
    "specs": ({"brand": "Apple", "model": "iPhone 17", "error": W13_TEXT}, ZERO),
    "price": ({"amount": None, "currency": "BHD", "error": W13_TEXT}, ZERO),
    "price_training": ({"amount": None, "currency": "BHD", "error": W13_TEXT}, ZERO),
    "reviews": (
        {"average_rating": None, "error": "reviews extraction unavailable"},
        ZERO,
    ),
    "verdict": ({"winner_index": 0, "error": "verdict generation unavailable"}, ZERO),
    "url_extract": {"error": W13_TEXT},
}


@pytest.mark.parametrize("state", ("off", "on"))
@pytest.mark.parametrize("arm", ALL_ARMS)
def test_p2_delivery_identity(monkeypatch, rec, arm, state):
    """P2 PIN (R-04C-3): W1-3 denial: the delivered value is the base literal; role
    ON the verdict and url arms re-raise the class (role OFF: the base dict, NOT
    raised); the camera answers the coded 503."""
    _full_config(monkeypatch, state)
    if arm == "camera":
        resp, _led = run_camera(monkeypatch, "w13")
        body = _fields(resp)
        assert resp.status_code == 503, (resp.status_code, body)
        assert body.get("code") == "LLM_UNAVAILABLE" and body.get("success") is False
        return
    st, out = run_arm(arm, monkeypatch, "w13")
    if state == "on" and arm in ("verdict", "url_extract"):
        assert st == "raised", out
        assert type(out) is abs_.LLMUnavailableError and str(out) == W13_TEXT, out
    else:
        assert st == "ok", out
        assert out == W13_DELIVERY[arm], out


P3_CASES = [
    (a, k, s) for a in ALL_ARMS for k in ("w13", "runtime") for s in ("off", "on")
]


@pytest.mark.parametrize("arm,kind,state", P3_CASES)
def test_p3_any_role_read_sequence(monkeypatch, rec, arm, kind, state):
    """P3 PIN (R-04C-4 / R-04C-18, measured under the FULL config at base): A1 / A2 /
    A4 exactly one any_role_enabled() read BEFORE the arm's record; group B none; the
    camera exactly two reads, the second before the arm's record."""
    _full_config(monkeypatch, state)
    if arm == "camera":
        run_camera(monkeypatch, kind)
    else:
        run_arm(arm, monkeypatch, kind)
    seq = [
        e
        for e in rec.events
        if e[0] == "read"
        or (e[0] == "log" and e[1] == LOGGER[arm] and e[4].startswith(PREFIX[arm]))
    ]
    shape = [e[0] for e in seq]
    v = state == "on"
    if arm in GROUP_B:
        assert shape == ["log"], seq
    elif arm == "camera":
        assert shape == ["read", "read", "log"], seq
        assert [e[1] for e in seq[:2]] == [v, v], seq
    else:
        assert shape == ["read", "log"], seq
        assert seq[0][1] is v, seq


@pytest.mark.parametrize("state", ("off", "on"))
@pytest.mark.parametrize("kind", ("w13", "runtime"))
def test_p4_camera_refunds_and_status(monkeypatch, rec, kind, state):
    """P4 PIN (R-04C-3): authed camera: one consume, one refund (uid, None), the
    fire_and_forget labels == the vision_exception label; 503 LLM_UNAVAILABLE for the
    class, 500 + the literal for a RuntimeError."""
    _full_config(monkeypatch, state)
    resp, led = run_camera(monkeypatch, kind)
    body = _fields(resp)
    assert led.consumes == [CAMERA_USER], led.consumes
    assert led.refunds == [(CAMERA_USER, None)], led.refunds
    assert led.anon_refunds == [], led.anon_refunds
    assert led.labels == ["usage_refund.image.vision_exception"], led.labels
    if kind == "w13":
        assert resp.status_code == 503, (resp.status_code, body)
        assert body.get("code") == "LLM_UNAVAILABLE", body
    else:
        assert resp.status_code == 500, (resp.status_code, body)
        assert body.get("error") == VISION_500_LITERAL, body


def test_p5_camera_anon_refund(monkeypatch, rec):
    """P5 PIN (R-04C-3; R-04C-20): pins a path production does NOT take today:
    ENABLE_COMPARE_AUTH_REQUIRED is ON on web (ledger line 316), so
    require_paid_route_user (image_routes.py:205) refuses an anonymous camera call
    before the arm. Here (auth-required unset, ENABLE_ANON_USAGE_GATE ON, metering ON,
    a synthetic fingerprint) a W1-3 denial refunds the anon credit ONCE with the
    consumed keys, under the anon vision_exception label; status 503."""
    _full_config(monkeypatch, "off")
    resp, led = run_camera(monkeypatch, "w13", anon=True)
    assert resp.status_code == 503, (resp.status_code, _fields(resp))
    assert led.consumes == [] and led.refunds == [], (led.consumes, led.refunds)
    assert led.anon_refunds == [(led.fp, led.anon_keys)], led.anon_refunds
    assert led.labels == ["usage_refund.image.anon.vision_exception"], led.labels


@pytest.mark.parametrize("arm", GROUP_A)
def test_p6_role_on_class_rows_unchanged(monkeypatch, rec, arm):
    """P6 PIN: role ON + W1-3: the S81-06 WARNING by type and the role-ON delivery
    (verdict / url re-raise; camera 503; parse the base tuple)."""
    _full_config(monkeypatch, "on")
    if arm == "camera":
        resp, _led = run_camera(monkeypatch, "w13")
        assert resp.status_code == 503, resp.status_code
    else:
        st, out = run_arm(arm, monkeypatch, "w13")
        if arm == "parse":
            assert (st, out) == ("ok", W13_DELIVERY["parse"]), (st, out)
        else:
            assert st == "raised" and type(out) is abs_.LLMUnavailableError, (st, out)
    assert arm_logs(rec.events, arm) == by_type(arm, "LLMUnavailableError")
