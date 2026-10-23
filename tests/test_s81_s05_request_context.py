"""S81-05 REQUEST-CONTEXT - the frozen RED file (ENABLE_REQUEST_CONTEXT_HEADERS).

Unit S81-05 (PLAN_S81 M1, lane B). Spec: .qa-s80/S81-05_UNIT_SPEC.md (sha
7df306bc...), its adversarial review .qa-s80/S81-05_SPEC_REVIEW.md and the
orchestrator rulings specs/RULINGS_S81_05.md (session-81 state folder).
Precedence: the rulings, then the review corrections, then the spec. Base
84c861f68ba3b23606c69ce2d1f78597e2f3037b.

What the rulings change against the spec rows:
  * R-S05-1: legacy_hash / device_lookup_keys are DROPPED. Spec R13 is gone;
    P8 pins that no such name exists. The unit ships device_key only.
  * R-S05-2: X-Compare-Request-Id is normalised to lower case before the uuid4
    round trip (R6 accepts upper case and returns the lower-case form).
  * R-S05-3: header_state(name) -> "absent" | "malformed" | "ok" (constants,
    never a value), bound in the same atomic bind (R13 here).
  * R-S05-4: atomic bind: every header is parsed into locals first, the
    ContextVars are set only after every parse finished; the except arm sets
    every value to None and every state to "malformed" (R20 atomic variants).
  * R-S05-5: innermost pure-ASGI middleware, added just before CORS (R25).
  * R-S05-8: the three new files join .github/black-clean-paths.txt (R28).
  * R-S05-9: P4 is reduced to the 401 and 404 envelopes.
  * C3: R26 drives the fresh app with httpx.ASGITransport inside ONE
    asyncio.run, with a sleep before the spawned task's record is read.
  * C11: _ScopeSpy records every dict read and write path.

Row kinds:
  * R rows fail at base on an AssertionError ONLY: a missing module or name is
    read through _mod / _leaf / _mw / _fn and asserted, never raised.
  * P rows are green at base and run with the FULL unit configuration present
    (flag OFF spellings, the pepper set, all three headers valid) plus call
    recorders where a gated mutant exists (ruling B1, session 79).

Header names in the leaf: header_state is called with the leaf's own constants
HEADER_CONSENT_VERSION / HEADER_DEVICE_FINGERPRINT / HEADER_COMPARE_REQUEST_ID
(spec 2.2: the lower-case bytes names); outside a bound request every state is
"absent".

Hermetic: no network (the conftest netguard is on; every request is driven in
process), no .env, no credential. Every fingerprint, uuid and pepper is
synthetic and built at run time. Pure ASCII.
"""

from __future__ import annotations

import ast
import asyncio
import contextvars
import hashlib
import hmac
import importlib
import importlib.util
import itertools
import json
import logging
import os
import re
import uuid
from pathlib import Path

import pytest

import app.main as app_main  # DOTENV hazard: app.main is imported first

FLAG = "ENABLE_REQUEST_CONTEXT_HEADERS"
PEPPER_ENV = "DEVICE_KEY_PEPPER"
DEFAULT_LIMITS_FLAG = "ENABLE_DEFAULT_RATE_LIMITS"
LEAF_NAME = "app.utils.request_context"
MW_NAME = "app.middleware.request_context"
LEAF_LOGGER = "app.utils.request_context"
MW_LOGGER = "app.middleware.request_context"

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
SCRIPTS_DIR = ROOT / "scripts"
LEAF_PATH = APP_DIR / "utils" / "request_context.py"
MW_PATH = APP_DIR / "middleware" / "request_context.py"
MAIN_PATH = APP_DIR / "main.py"
AUTH_ROUTES_PATH = APP_DIR / "api" / "auth_routes.py"
BLACK_PATHS = ROOT / ".github" / "black-clean-paths.txt"

H_CONSENT = b"x-ai-consent-version"
H_FP = b"x-device-fingerprint"
H_ID = b"x-compare-request-id"

FP_A = "ab" * 32
FP_B = "cd" * 32
UID_A = str(uuid.uuid4())
UID_B = str(uuid.uuid4())
PEPPER = "s05" + "-pepper-" + "synthetic"
BAD = "s05" + "bad" + "sentinel"
NIL_UUID = str(uuid.UUID(int=0))
V1_SHAPED = "abcdefab-cdef-1abc-8def-abcdefabcdef"
VARIANT_C = "abcdefab-cdef-4abc-cdef-abcdefabcdef"
WARN_TEXT = (
    "[REQUEST-CONTEXT] DEVICE_KEY_PEPPER unset or blank; "
    "device keys disabled (fail closed)"
)
STATES = ("absent", "malformed", "ok")
ABSENT3 = ("absent", "absent", "absent")
NONE3 = (None, None, None)

BASE_STACK = [
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    "ErrorHandlerMiddleware",
    "CORSMiddleware",
]
NEW_STACK = BASE_STACK + ["RequestContextMiddleware"]
NEW_STACK_DEFAULT_LIMITS = [
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    "ErrorHandlerMiddleware",
    "SlowAPIASGIMiddleware",
    "CORSMiddleware",
    "RequestContextMiddleware",
]

FALSY = [
    pytest.param(None, id="unset"),
    pytest.param("", id="empty"),
    pytest.param("false", id="false"),
    pytest.param("0", id="zero"),
    pytest.param("no", id="no"),
    pytest.param("off", id="off"),
    pytest.param(" FALSE ", id="padded-FALSE"),
]


def _valid_headers():
    return [
        (H_CONSENT, b"3"),
        (H_FP, FP_A.encode("ascii")),
        (H_ID, UID_A.encode("ascii")),
    ]


def _hmac(pepper, fp):
    return hmac.new(
        pepper.encode("utf-8"), fp.encode("ascii"), hashlib.sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# helpers: a missing symbol is an assertion, never an ImportError
# ---------------------------------------------------------------------------


def _mod(name):
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return None
    if spec is None:
        return None
    try:
        return importlib.import_module(name)
    except Exception:  # noqa: BLE001 - a broken new module reads as missing
        return None


def _leaf():
    mod = _mod(LEAF_NAME)
    assert mod is not None, "S81-05 leaf app/utils/request_context.py missing"
    return mod


def _mw():
    mod = _mod(MW_NAME)
    assert (
        mod is not None
    ), "S81-05 middleware app/middleware/request_context.py missing"
    assert callable(
        getattr(mod, "RequestContextMiddleware", None)
    ), "RequestContextMiddleware missing"
    return mod


def _fn(mod, name):
    f = getattr(mod, name, None)
    assert callable(f), f"S81-05 {name} missing from {mod.__name__}"
    return f


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def _header_names(leaf):
    return (
        getattr(leaf, "HEADER_CONSENT_VERSION", H_CONSENT),
        getattr(leaf, "HEADER_DEVICE_FINGERPRINT", H_FP),
        getattr(leaf, "HEADER_COMPARE_REQUEST_ID", H_ID),
    )


def _values(leaf):
    return (
        _fn(leaf, "consent_version")(),
        _fn(leaf, "device_fingerprint")(),
        _fn(leaf, "compare_request_id")(),
    )


def _states(leaf):
    hs = getattr(leaf, "header_state", None)
    if not callable(hs):
        return None
    return tuple(hs(n) for n in _header_names(leaf))


@pytest.fixture(autouse=True)
def _s05_env(monkeypatch):
    import app.main  # noqa: F401  (DOTENV hazard: app.main first)

    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(PEPPER_ENV, raising=False)
    monkeypatch.delenv(DEFAULT_LIMITS_FLAG, raising=False)
    leaf = _mod(LEAF_NAME)
    reset = getattr(leaf, "_reset_pepper_warning", None) if leaf else None
    if callable(reset):
        reset()
    yield
    if callable(reset):
        reset()


class _Recorder:
    """A downstream ASGI app that records the objects and the context."""

    def __init__(self, leaf, *, event=None, entered=None, exc=None, inner=None):
        self.leaf = leaf
        self.event = event
        self.entered = entered
        self.exc = exc
        self.inner = inner
        self.calls = []

    async def __call__(self, scope, receive, send):
        if self.entered is not None:
            self.entered()
        if self.event is not None:
            await self.event.wait()
        record = {"scope": scope, "receive": receive, "send": send}
        record["values"] = _values(self.leaf)
        record["states"] = _states(self.leaf)
        if self.inner is not None:
            await self.inner()
            record["values_after_inner"] = _values(self.leaf)
            record["states_after_inner"] = _states(self.leaf)
        self.calls.append(record)
        if self.exc is not None:
            raise self.exc


class _ScopeSpy(dict):
    """A scope that records every read and write path (review C11)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads = []

    def __getitem__(self, key):
        self.reads.append(("getitem", key))
        return super().__getitem__(key)

    def get(self, key, default=None):
        self.reads.append(("get", key))
        return super().get(key, default)

    def __contains__(self, key):
        self.reads.append(("contains", key))
        return super().__contains__(key)

    def setdefault(self, key, default=None):
        self.reads.append(("setdefault", key))
        return super().setdefault(key, default)

    def __setitem__(self, key, value):
        self.reads.append(("setitem", key))
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        self.reads.append(("delitem", key))
        return super().__delitem__(key)

    def pop(self, key, *default):
        self.reads.append(("pop", key))
        return super().pop(key, *default)

    def update(self, *args, **kwargs):
        self.reads.append(("update", None))
        return super().update(*args, **kwargs)

    def __iter__(self):
        self.reads.append(("iter", None))
        return super().__iter__()

    def keys(self):
        self.reads.append(("keys", None))
        return super().keys()

    def items(self):
        self.reads.append(("items", None))
        return super().items()

    def values(self):
        self.reads.append(("values", None))
        return super().values()

    def copy(self):
        self.reads.append(("copy", None))
        return super().copy()


class _GetenvRec:
    def __init__(self, real):
        self.real = real
        self.names = []

    def __call__(self, key, default=None):
        self.names.append(key)
        return self.real(key, default)


def _endpoints():
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    return receive, send


def _scope(headers, type_="http"):
    return {"type": type_, "method": "GET", "path": "/s05", "headers": headers}


def _call(mw, scope, receive, send):
    async def go():
        await mw(scope, receive, send)

    asyncio.run(go())


def _wrap_counter(monkeypatch, mwmod, name):
    assert hasattr(mwmod, name), f"middleware does not import {name}"
    real = getattr(mwmod, name)
    calls = []

    def wrapper(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(mwmod, name, wrapper)
    return calls


_counter = itertools.count()


def _fresh_main(monkeypatch):
    """Execute the real app/main.py into a private module (test_retro_w1_9)."""
    import dotenv

    import app.middleware.logging_config as logging_config
    import app.services.sentry_service as sentry_service

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(logging_config, "configure_logging", lambda *a, **k: None)
    monkeypatch.setattr(sentry_service, "init_sentry", lambda *a, **k: None)
    name = f"_s81_s05_main_{next(_counter)}"
    spec = importlib.util.spec_from_file_location(name, app_main.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _names(app):
    return [m.cls.__name__ for m in app.user_middleware]


# ===========================================================================
# RED rows
# ===========================================================================


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, False, id="unset"),
        pytest.param("", False, id="empty"),
        pytest.param("false", False, id="false"),
        pytest.param("0", False, id="zero"),
        pytest.param("no", False, id="no"),
        pytest.param("off", False, id="off"),
        pytest.param("garbage", False, id="garbage"),
        pytest.param("true", True, id="true"),
        pytest.param("1", True, id="one"),
        pytest.param("yes", True, id="yes"),
        pytest.param("on", True, id="on"),
        pytest.param(" TRUE ", True, id="padded-TRUE"),
        pytest.param("On", True, id="On"),
    ],
)
def test_s05_r01_flag_reader_per_call(monkeypatch, value, expected):
    reader = _fn(_leaf(), "request_context_headers_enabled")
    monkeypatch.delenv(FLAG, raising=False)
    assert reader() is False
    _set_flag(monkeypatch, value)
    assert reader() is expected
    # read per call: a change after import flips the result both ways
    monkeypatch.setenv(FLAG, "true")
    assert reader() is True
    monkeypatch.setenv(FLAG, "off")
    assert reader() is False


@pytest.mark.parametrize(
    "raw,expected",
    [("0", 0), ("3", 3), ("03", 3), ("007", 7), ("999", 999)],
    ids=["0", "3", "03", "007", "999"],
)
def test_s05_r02_consent_valid(raw, expected):
    got = _fn(_leaf(), "parse_consent_version")(raw)
    assert got == expected
    assert type(got) is int


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("1000", id="1000"),
        pytest.param("12345", id="12345"),
        pytest.param("-1", id="minus"),
        pytest.param("+3", id="plus"),
        pytest.param(" 3", id="lead-space"),
        pytest.param("3 ", id="trail-space"),
        pytest.param("3.0", id="decimal"),
        pytest.param("1e2", id="exp"),
        pytest.param("0x3", id="hex"),
        pytest.param(chr(0x663), id="arabic-indic"),
        pytest.param(chr(0xFF13), id="fullwidth"),
        pytest.param("3\n", id="trail-lf"),
        pytest.param("abc", id="abc"),
        pytest.param(b"3", id="bytes"),
        pytest.param(3, id="int"),
        pytest.param(3.0, id="float"),
        pytest.param(True, id="bool"),
    ],
)
def test_s05_r03_consent_invalid(raw):
    assert _fn(_leaf(), "parse_consent_version")(raw) is None


@pytest.mark.parametrize("raw", ["ab" * 32, "0f" * 32, "e" * 64], ids=["ab", "0f", "e"])
def test_s05_r04_fp_valid(raw):
    assert _fn(_leaf(), "parse_device_fingerprint")(raw) == raw


_FP_INVALID = [
    pytest.param(None, id="none"),
    pytest.param("", id="empty"),
    pytest.param("AB" * 32, id="upper"),
    pytest.param("a" * 63, id="63"),
    pytest.param("a" * 65, id="65"),
    pytest.param("ab" * 32 + "\n", id="trail-lf"),
    pytest.param(" " + "ab" * 32, id="lead-space"),
    pytest.param("g" * 64, id="non-hex"),
    pytest.param("a" * 31 + "-" + "a" * 32, id="dash"),
    pytest.param(12345, id="int"),
    pytest.param(("ab" * 32).encode("ascii"), id="bytes"),
]


@pytest.mark.parametrize("raw", _FP_INVALID)
def test_s05_r05_fp_invalid(raw):
    assert _fn(_leaf(), "parse_device_fingerprint")(raw) is None


@pytest.mark.parametrize("form", ["lower", "upper", "mixed"])
def test_s05_r06_request_id_valid(form):
    parse = _fn(_leaf(), "parse_compare_request_id")
    for _ in range(3):
        u = str(uuid.uuid4())
        if form == "lower":
            raw = u
        elif form == "upper":
            raw = u.upper()
        else:
            raw = "".join(c.upper() if i % 2 else c for i, c in enumerate(u))
        got = parse(raw)
        # R-S05-2: normalised to lower case, the canonical form is stored
        assert got == u
        assert type(got) is str


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("{" + UID_A + "}", id="braces"),
        pytest.param(UID_A.replace("-", ""), id="hex32"),
        pytest.param("urn:uuid:" + UID_A, id="urn"),
        pytest.param(V1_SHAPED, id="v1"),
        pytest.param(V1_SHAPED.upper(), id="v1-upper"),
        pytest.param(VARIANT_C, id="variant-c"),
        pytest.param(NIL_UUID, id="nil"),
        pytest.param(UID_A + " ", id="trail-space"),
        pytest.param(" " + UID_A, id="lead-space"),
        pytest.param("x" * 36, id="non-hex"),
        pytest.param(uuid.UUID(UID_A), id="uuid-object"),
        pytest.param(UID_A.encode("ascii"), id="bytes"),
        pytest.param(UID_A + "\n", id="trail-lf"),
    ],
)
def test_s05_r07_request_id_invalid(raw):
    assert _fn(_leaf(), "parse_compare_request_id")(raw) is None


def test_s05_r08_one_regex_object():
    import app.api.auth_routes as auth_routes

    leaf = _leaf()
    leaf_re = getattr(leaf, "DEVICE_FINGERPRINT_RE", None)
    assert leaf_re is not None, "leaf DEVICE_FINGERPRINT_RE missing"
    assert auth_routes._DEVICE_FINGERPRINT_RE is leaf_re
    assert leaf_re.pattern == r"^[a-f0-9]{64}$"
    assert leaf_re.flags == re.compile(r"^[a-f0-9]{64}$").flags
    # re.compile caches identical patterns, so identity alone cannot tell a
    # re-import from a second local compile: pin the source shape too.
    tree = ast.parse(AUTH_ROUTES_PATH.read_text(encoding="utf-8"))
    imported = [
        (a.name, a.asname)
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == LEAF_NAME
        for a in n.names
    ]
    assert imported == [("DEVICE_FINGERPRINT_RE", "_DEVICE_FINGERPRINT_RE")]
    assigned = [
        t.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Name)
    ]
    assert "_DEVICE_FINGERPRINT_RE" not in assigned


@pytest.mark.parametrize(
    "pepper_value", [PEPPER, "  " + PEPPER + "\t"], ids=["plain", "padded"]
)
def test_s05_r09_device_key_hmac(monkeypatch, pepper_value):
    dk = _fn(_leaf(), "device_key")
    monkeypatch.setenv(PEPPER_ENV, pepper_value)
    want = _hmac(PEPPER, FP_A)
    got = dk(FP_A)
    assert got == want
    assert re.fullmatch(r"[0-9a-f]{64}", got)
    assert got != FP_A
    assert got != hashlib.sha256(FP_A.encode("ascii")).hexdigest()
    assert dk(FP_B) == _hmac(PEPPER, FP_B) != got
    assert [dk(FP_A) for _ in range(3)] == [want] * 3
    other = PEPPER + "-two"
    monkeypatch.setenv(PEPPER_ENV, other)
    assert dk(FP_A) == _hmac(other, FP_A) != want


@pytest.mark.parametrize(
    "pepper_value",
    [None, "", "   ", "\t"],
    ids=["unset", "empty", "spaces", "tab"],
)
def test_s05_r10_device_key_fail_closed(monkeypatch, caplog, pepper_value):
    leaf = _leaf()
    dk = _fn(leaf, "device_key")
    reset = _fn(leaf, "_reset_pepper_warning")
    reset()
    if pepper_value is None:
        monkeypatch.delenv(PEPPER_ENV, raising=False)
    else:
        monkeypatch.setenv(PEPPER_ENV, pepper_value)
    caplog.set_level(logging.DEBUG, logger=LEAF_LOGGER)
    assert [dk(FP_A) for _ in range(3)] == [None] * 3
    recs = [r for r in caplog.records if r.name == LEAF_LOGGER]
    assert len(recs) == 1, [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.WARNING
    assert recs[0].getMessage() == WARN_TEXT
    assert FP_A not in caplog.text
    reset()
    assert dk(FP_A) is None
    recs = [r for r in caplog.records if r.name == LEAF_LOGGER]
    assert len(recs) == 2


@pytest.mark.parametrize("raw", _FP_INVALID)
def test_s05_r11_device_key_invalid_fp(monkeypatch, caplog, raw):
    dk = _fn(_leaf(), "device_key")
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    rec = _GetenvRec(os.getenv)
    monkeypatch.setattr(os, "getenv", rec)
    caplog.set_level(logging.DEBUG)
    assert dk(raw) is None
    assert PEPPER_ENV not in rec.names
    assert [r for r in caplog.records if r.name == LEAF_LOGGER] == []


def test_s05_r12_pepper_never_leaks(monkeypatch, caplog):
    leaf = _leaf()
    dk = _fn(leaf, "device_key")
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    caplog.set_level(logging.DEBUG)
    outs = [dk(FP_A), dk("zz"), dk(None)]
    for out in outs:
        assert out is None or PEPPER not in out
    assert PEPPER not in repr(outs)
    states = _states(leaf)
    assert states is not None, "header_state missing"
    assert PEPPER not in repr(states)
    monkeypatch.delenv(PEPPER_ENV, raising=False)
    assert dk(FP_A) is None
    assert PEPPER not in caplog.text


_R13_CASES = [
    pytest.param([], ABSENT3, NONE3, id="none"),
    pytest.param("valid", ("ok", "ok", "ok"), (3, FP_A, UID_A), id="all-ok"),
    pytest.param(
        [(H_CONSENT, BAD.encode()), (H_FP, FP_A.encode())],
        ("malformed", "ok", "absent"),
        (None, FP_A, None),
        id="mixed",
    ),
    pytest.param(
        [(H_ID, UID_A.upper().encode())],
        ("absent", "absent", "ok"),
        (None, None, UID_A),
        id="upper-id",
    ),
    pytest.param(
        [(H_FP, BAD.encode()), (H_FP, FP_A.encode())],
        ("absent", "malformed", "absent"),
        NONE3,
        id="dup-first-bad",
    ),
    pytest.param(
        [(H_FP, b"\xff" * 64), (H_CONSENT, b"\xd9\xa3")],
        ("malformed", "malformed", "absent"),
        NONE3,
        id="high-bytes",
    ),
    pytest.param(
        [(H_ID, ("{" + UID_A + "}").encode())],
        ("absent", "absent", "malformed"),
        NONE3,
        id="braced-id",
    ),
]


@pytest.mark.parametrize("headers,states,values", _R13_CASES)
def test_s05_r13_header_state(monkeypatch, headers, states, values):
    """R-S05-3: a constant state per header, bound with the values."""
    leaf = _leaf()
    mwmod = _mw()
    assert callable(getattr(leaf, "header_state", None)), "header_state missing"
    if headers == "valid":
        headers = _valid_headers()
    monkeypatch.setenv(FLAG, "true")
    rec = _Recorder(leaf)
    mw = mwmod.RequestContextMiddleware(rec)
    receive, send = _endpoints()
    after = {}

    async def go():
        await mw(_scope(headers), receive, send)
        after["states"] = _states(leaf)
        after["values"] = _values(leaf)

    asyncio.run(go())
    assert len(rec.calls) == 1
    got = rec.calls[0]["states"]
    for s in got:
        assert type(s) is str and s in STATES, repr(s)
    assert got == states
    assert rec.calls[0]["values"] == values
    assert after["states"] == ABSENT3
    assert after["values"] == NONE3


def test_s05_r14_accessors_default_none():
    leaf = _leaf()

    def read():
        return _values(leaf), _states(leaf)

    vals, states = contextvars.Context().run(read)
    assert vals == NONE3
    assert states == ABSENT3


@pytest.mark.parametrize(
    "present",
    [
        pytest.param((True, False, False), id="consent"),
        pytest.param((False, True, False), id="fp"),
        pytest.param((False, False, True), id="request-id"),
        pytest.param((True, True, True), id="all"),
    ],
)
def test_s05_r15_flag_on_binds_inside(monkeypatch, present):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    full = _valid_headers()
    headers = [h for h, keep in zip(full, present) if keep]
    expected = tuple(v if keep else None for v, keep in zip((3, FP_A, UID_A), present))
    rec = _Recorder(leaf)
    mw = mwmod.RequestContextMiddleware(rec)
    receive, send = _endpoints()
    scope = _scope(headers)
    _call(mw, scope, receive, send)
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["values"] == expected
    assert call["scope"] is scope
    assert call["receive"] is receive
    assert call["send"] is send


_R16_CASES = []
for _name, _bads in (
    ("consent", [BAD.encode(), b"1000", b"\xd9\xa3"]),
    ("fp", [BAD.encode(), ("AB" * 32).encode(), b"\xff" * 64]),
    ("request-id", [BAD.encode(), ("{" + UID_A + "}").encode(), b"\xff" * 36]),
):
    for _i, _bad in enumerate(_bads):
        _R16_CASES.append(pytest.param(_name, _bad, id=f"{_name}-{_i}"))


@pytest.mark.parametrize("which,bad", _R16_CASES)
def test_s05_r16_flag_on_malformed_is_none(monkeypatch, caplog, which, bad):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    name = {"consent": H_CONSENT, "fp": H_FP, "request-id": H_ID}[which]
    caplog.set_level(logging.DEBUG)
    rec = _Recorder(leaf)
    mw = mwmod.RequestContextMiddleware(rec)
    receive, send = _endpoints()
    _call(mw, _scope([(name, bad)]), receive, send)
    assert len(rec.calls) == 1
    assert rec.calls[0]["values"] == NONE3
    names = {LEAF_LOGGER, MW_LOGGER}
    assert [r for r in caplog.records if r.name in names] == []
    text = bad.decode("latin-1")
    assert BAD not in caplog.text
    assert text not in caplog.text
    assert PEPPER not in caplog.text


@pytest.mark.parametrize("mode", ["returns", "raises"])
def test_s05_r17_reset_on_return_and_raise(monkeypatch, mode):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    exc = RuntimeError("s05-downstream") if mode == "raises" else None
    rec = _Recorder(leaf, exc=exc)
    mw = mwmod.RequestContextMiddleware(rec)
    receive, send = _endpoints()
    out = {}

    async def go():
        out["before"] = (_values(leaf), _states(leaf))
        if exc is None:
            await mw(_scope(_valid_headers()), receive, send)
        else:
            with pytest.raises(RuntimeError) as info:
                await mw(_scope(_valid_headers()), receive, send)
            out["exc"] = info.value
        out["after"] = (_values(leaf), _states(leaf))

    asyncio.run(go())
    assert out["before"] == (NONE3, ABSENT3)
    assert rec.calls[0]["values"] == (3, FP_A, UID_A)
    assert rec.calls[0]["states"] == ("ok", "ok", "ok")
    assert out["after"] == (NONE3, ABSENT3)
    if exc is not None:
        assert out["exc"] is exc


def test_s05_r17_nested_restores_outer(monkeypatch):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    receive, send = _endpoints()
    inner_rec = _Recorder(leaf)
    inner_mw = mwmod.RequestContextMiddleware(inner_rec)
    headers_b = [
        (H_CONSENT, b"7"),
        (H_FP, FP_B.encode()),
        (H_ID, UID_B.encode()),
    ]

    async def inner():
        await inner_mw(_scope(headers_b), receive, send)

    outer_rec = _Recorder(leaf, inner=inner)
    outer_mw = mwmod.RequestContextMiddleware(outer_rec)
    out = {}

    async def go():
        await outer_mw(_scope(_valid_headers()), receive, send)
        out["after"] = (_values(leaf), _states(leaf))

    asyncio.run(go())
    assert inner_rec.calls[0]["values"] == (7, FP_B, UID_B)
    assert outer_rec.calls[0]["values"] == (3, FP_A, UID_A)
    assert outer_rec.calls[0]["values_after_inner"] == (3, FP_A, UID_A)
    assert outer_rec.calls[0]["states_after_inner"] == ("ok", "ok", "ok")
    assert out["after"] == (NONE3, ABSENT3)


@pytest.mark.parametrize(
    "headers,expected",
    [
        pytest.param(
            [(H_FP, FP_A.encode()), (H_FP, FP_B.encode())],
            (None, FP_A, None),
            id="fp-first-valid",
        ),
        pytest.param(
            [(H_FP, b"zz"), (H_FP, FP_A.encode())],
            NONE3,
            id="fp-first-bad",
        ),
        pytest.param(
            [(H_CONSENT, b"3"), (H_CONSENT, b"7")],
            (3, None, None),
            id="consent-first-valid",
        ),
        pytest.param(
            [(H_CONSENT, b"zz"), (H_CONSENT, b"3")],
            NONE3,
            id="consent-first-bad",
        ),
        pytest.param(
            [(H_ID, UID_A.encode()), (H_ID, UID_B.encode())],
            (None, None, UID_A),
            id="id-first-valid",
        ),
        pytest.param(
            [(H_ID, b"zz"), (H_ID, UID_A.encode())],
            NONE3,
            id="id-first-bad",
        ),
    ],
)
def test_s05_r18_first_occurrence_wins(monkeypatch, headers, expected):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    rec = _Recorder(leaf)
    receive, send = _endpoints()
    _call(mwmod.RequestContextMiddleware(rec), _scope(headers), receive, send)
    assert rec.calls[0]["values"] == expected


@pytest.mark.parametrize("kind", ["lifespan", "websocket"])
def test_s05_r19_non_http_scopes_pass_through(monkeypatch, kind):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    binds = _wrap_counter(monkeypatch, mwmod, "bind_from_headers")
    if kind == "lifespan":
        scope = {"type": "lifespan"}
    else:
        scope = _scope(_valid_headers(), type_="websocket")
    rec = _Recorder(leaf)
    receive, send = _endpoints()
    _call(mwmod.RequestContextMiddleware(rec), scope, receive, send)
    assert len(rec.calls) == 1
    assert rec.calls[0]["values"] == NONE3
    assert rec.calls[0]["scope"] is scope
    assert rec.calls[0]["receive"] is receive
    assert rec.calls[0]["send"] is send
    assert binds == []


_MISSING = object()


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param(_MISSING, id="missing"),
        pytest.param(None, id="none"),
        pytest.param("junk", id="str"),
        pytest.param(12345, id="int"),
        pytest.param([b"x"], id="bare-bytes-item"),
        pytest.param([(H_CONSENT,)], id="one-tuple"),
        pytest.param([(H_CONSENT, 3)], id="int-value"),
        pytest.param([(3, b"3")], id="int-name"),
    ],
)
def test_s05_r20_bind_is_total(monkeypatch, headers):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    scope = {"type": "http", "method": "GET", "path": "/s05"}
    if headers is not _MISSING:
        scope["headers"] = headers
    rec = _Recorder(leaf)
    receive, send = _endpoints()
    try:
        _call(mwmod.RequestContextMiddleware(rec), scope, receive, send)
    except Exception as exc:  # noqa: BLE001 - a raise is the defect
        raise AssertionError(f"bind is not total: {type(exc).__name__}") from exc
    assert len(rec.calls) == 1
    assert rec.calls[0]["values"] == NONE3
    states = rec.calls[0]["states"]
    assert states is not None, "header_state missing"
    for s in states:
        assert s in ("absent", "malformed"), states


@pytest.mark.parametrize(
    "raiser",
    [
        "parse_consent_version",
        "parse_device_fingerprint",
        "parse_compare_request_id",
    ],
)
def test_s05_r20_atomic_bind_when_a_parser_raises(monkeypatch, raiser):
    """R-S05-4 / C2: a valid header parsed BEFORE the raising one must not
    survive the request (the set-as-you-parse leak, measured by the review)."""
    leaf = _leaf()
    mwmod = _mw()
    assert hasattr(leaf, raiser), f"{raiser} missing"
    monkeypatch.setenv(FLAG, "true")
    hits = []

    def boom(*args, **kwargs):
        hits.append(args)
        raise ValueError("s05-parser-defect")

    monkeypatch.setattr(leaf, raiser, boom)
    rec = _Recorder(leaf)
    receive, send = _endpoints()
    mw = mwmod.RequestContextMiddleware(rec)
    out = {}

    async def go():
        await mw(_scope(_valid_headers()), receive, send)
        out["after"] = (_values(leaf), _states(leaf))

    try:
        asyncio.run(go())
    except Exception as exc:  # noqa: BLE001 - a raise is the defect
        raise AssertionError(f"bind is not total: {type(exc).__name__}") from exc
    assert hits, f"{raiser} was not called through the leaf namespace"
    assert len(rec.calls) == 1
    assert rec.calls[0]["values"] == NONE3
    assert rec.calls[0]["states"] == ("malformed", "malformed", "malformed")
    assert out["after"] == (NONE3, ABSENT3)


def test_s05_r21_concurrent_isolation(monkeypatch):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    receive, send = _endpoints()
    headers_b = [
        (H_CONSENT, b"7"),
        (H_FP, FP_B.encode()),
        (H_ID, UID_B.encode()),
    ]
    reads = {}

    async def go():
        both_in = asyncio.Event()
        both_read = asyncio.Event()
        seen = {"in": 0, "read": 0}

        def downstream(key):
            async def app(scope, receive_, send_):
                seen["in"] += 1
                if seen["in"] == 2:
                    both_in.set()
                await both_in.wait()
                await asyncio.sleep(0)
                # both requests are bound at this point: a module-global
                # store shows the second request's values to the first
                reads[key] = _values(leaf)
                seen["read"] += 1
                if seen["read"] == 2:
                    both_read.set()
                await both_read.wait()

            return app

        mw_a = mwmod.RequestContextMiddleware(downstream("a"))
        mw_b = mwmod.RequestContextMiddleware(downstream("b"))
        await asyncio.gather(
            mw_a(_scope(_valid_headers()), receive, send),
            mw_b(_scope(headers_b), receive, send),
        )

    asyncio.run(go())
    assert reads["a"] == (3, FP_A, UID_A)
    assert reads["b"] == (7, FP_B, UID_B)


@pytest.mark.parametrize("value", FALSY)
def test_s05_r22_flag_off_reads_nothing(monkeypatch, value):
    leaf = _leaf()
    mwmod = _mw()
    _set_flag(monkeypatch, value)
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    binds = _wrap_counter(monkeypatch, mwmod, "bind_from_headers")
    resets = _wrap_counter(monkeypatch, mwmod, "reset_request_context")
    spy = _ScopeSpy(_scope(_valid_headers()))
    rec = _Recorder(leaf)
    mw = mwmod.RequestContextMiddleware(rec)
    receive, send = _endpoints()
    getenv_rec = _GetenvRec(os.getenv)

    async def go():
        real = os.getenv
        os.getenv = getenv_rec
        try:
            await mw(spy, receive, send)
        finally:
            os.getenv = real

    asyncio.run(go())
    assert spy.reads == []
    assert getenv_rec.names == [FLAG]
    assert binds == [] and resets == []
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["scope"] is spy
    assert call["receive"] is receive
    assert call["send"] is send
    assert call["values"] == NONE3
    assert call["states"] == ABSENT3


def test_s05_r23_flag_on_reads_flag_once(monkeypatch):
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    binds = _wrap_counter(monkeypatch, mwmod, "bind_from_headers")
    resets = _wrap_counter(monkeypatch, mwmod, "reset_request_context")
    spy = _ScopeSpy(_scope(_valid_headers()))
    rec = _Recorder(leaf)
    mw = mwmod.RequestContextMiddleware(rec)
    receive, send = _endpoints()
    getenv_rec = _GetenvRec(os.getenv)

    async def go():
        real = os.getenv
        os.getenv = getenv_rec
        try:
            await mw(spy, receive, send)
        finally:
            os.getenv = real

    asyncio.run(go())
    assert getenv_rec.names == [FLAG]
    kinds = {k for k, _ in spy.reads}
    keys = {key for _, key in spy.reads}
    assert kinds <= {"get", "getitem", "contains"}, spy.reads
    assert keys <= {"type", "headers"}, spy.reads
    assert len(binds) == 1 and len(resets) == 1
    assert rec.calls[0]["values"] == (3, FP_A, UID_A)
    assert rec.calls[0]["scope"] is spy


def _calls_in(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


def _app_imports(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("app"):
            out.append(n.module)
        elif isinstance(n, ast.Import):
            out.extend(a.name for a in n.names if a.name.startswith("app"))
    return out


def test_s05_r24_sources_never_log():
    assert MW_PATH.is_file(), "app/middleware/request_context.py missing"
    assert LEAF_PATH.is_file(), "app/utils/request_context.py missing"
    mw_tree = ast.parse(MW_PATH.read_text(encoding="utf-8"))
    leaf_tree = ast.parse(LEAF_PATH.read_text(encoding="utf-8"))

    mw_imports = []
    for n in ast.walk(mw_tree):
        if isinstance(n, ast.Import):
            mw_imports.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            mw_imports.append(n.module or "")
    assert "logging" not in mw_imports and "warnings" not in mw_imports
    names = {n.id for n in ast.walk(mw_tree) if isinstance(n, ast.Name)}
    assert not names & {"logger", "logging", "print", "warnings"}, names
    assert _app_imports(mw_tree) == [LEAF_NAME]

    assert _app_imports(leaf_tree) == []
    warn_calls = []
    for call in _calls_in(leaf_tree):
        f = call.func
        if isinstance(f, ast.Name):
            assert f.id != "print", "print in the leaf"
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if f.value.id == "logger":
                warn_calls.append(call)
            if f.value.id == "logging":
                assert f.attr == "getLogger", f"logging.{f.attr} in the leaf"
            assert f.value.id != "warnings", "warnings call in the leaf"
    assert len(warn_calls) == 1, [ast.dump(c) for c in warn_calls]
    only = warn_calls[0]
    assert only.func.attr == "warning"
    assert only.keywords == []
    assert len(only.args) == 1
    assert isinstance(only.args[0], ast.Constant)
    assert isinstance(only.args[0].value, str)


@pytest.mark.parametrize(
    "mode", ["imported", "fresh-unset", "fresh-true", "fresh-default-limits"]
)
def test_s05_r25_stack_registration(monkeypatch, mode):
    if mode == "imported":
        assert _names(app_main.app) == NEW_STACK
        return
    if mode == "fresh-true":
        monkeypatch.setenv(FLAG, "true")
    if mode == "fresh-default-limits":
        monkeypatch.setenv(DEFAULT_LIMITS_FLAG, "true")
    module = _fresh_main(monkeypatch)
    expected = NEW_STACK_DEFAULT_LIMITS if mode == "fresh-default-limits" else NEW_STACK
    assert _names(module.app) == expected


def _probe_app(monkeypatch, leaf, bg):
    from fastapi import Depends
    from fastapi.responses import StreamingResponse

    module = _fresh_main(monkeypatch)

    def snap():
        fp = leaf.device_fingerprint()
        return {
            "consent": leaf.consent_version(),
            "fp": fp,
            "rid": leaf.compare_request_id(),
            "dk": leaf.device_key(fp),
            "states": list(_states(leaf) or ()),
        }

    def sync_dep():
        return snap()

    async def async_dep():
        return snap()

    async def later():
        await asyncio.sleep(0.05)
        bg["task"] = snap()

    async def probe_async(
        s_dep: dict = Depends(sync_dep), a_dep: dict = Depends(async_dep)
    ):
        loop = asyncio.get_running_loop()
        bg["handle"] = loop.create_task(later())
        return {
            "route": snap(),
            "sync_dep": s_dep,
            "async_dep": a_dep,
            "to_thread": await asyncio.to_thread(snap),
            "executor": await loop.run_in_executor(None, snap),
        }

    def probe_sync():
        return snap()

    async def probe_astream():
        async def agen():
            yield json.dumps(snap()) + "\n"
            await asyncio.sleep(0)
            yield json.dumps(snap()) + "\n"

        return StreamingResponse(agen(), media_type="text/plain")

    async def probe_sstream():
        def gen():
            yield json.dumps(snap()) + "\n"
            yield json.dumps(snap()) + "\n"

        return StreamingResponse(gen(), media_type="text/plain")

    module.app.add_api_route("/s05probe/async", probe_async, methods=["GET"])
    module.app.add_api_route("/s05probe/sync", probe_sync, methods=["GET"])
    module.app.add_api_route("/s05probe/astream", probe_astream, methods=["GET"])
    module.app.add_api_route("/s05probe/sstream", probe_sstream, methods=["GET"])
    return module


@pytest.mark.parametrize("flag_value", ["true", None], ids=["true", "unset"])
def test_s05_r26_end_to_end_through_main(monkeypatch, flag_value):
    import httpx

    leaf = _leaf()
    _mw()
    bg = {}
    module = _probe_app(monkeypatch, leaf, bg)
    _set_flag(monkeypatch, flag_value)
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    headers = {
        "X-AI-Consent-Version": "3",
        "X-Device-Fingerprint": FP_A,
        "X-Compare-Request-Id": UID_A,
        "X-Request-ID": "s05-e2e",
    }
    out = {}

    async def drive():
        transport = httpx.ASGITransport(app=module.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            for path in ("async", "sync", "astream", "sstream"):
                out[path] = await client.get(f"/s05probe/{path}", headers=headers)
            await asyncio.sleep(0.15)

    asyncio.run(drive())
    on = {
        "consent": 3,
        "fp": FP_A,
        "rid": UID_A,
        "dk": _hmac(PEPPER, FP_A),
        "states": ["ok", "ok", "ok"],
    }
    none = {
        "consent": None,
        "fp": None,
        "rid": None,
        "dk": None,
        "states": list(ABSENT3),
    }
    want = on if flag_value == "true" else none
    for path in out:
        assert out[path].status_code == 200, (path, out[path].text[:300])
    body = out["async"].json()
    assert body["route"] == want
    assert body["sync_dep"] == want
    assert body["async_dep"] == want
    assert body["to_thread"] == want
    assert body["executor"] == none  # stated limit: run_in_executor copies no context
    assert out["sync"].json() == want
    for path in ("astream", "sstream"):
        lines = [json.loads(x) for x in out[path].text.splitlines() if x]
        assert lines == [want, want], path
    assert bg.get("task") == want


def test_s05_r27_pepper_is_a_sanitized_credential():
    from tests import _env_safety

    assert PEPPER_ENV in _env_safety.CREDENTIALS_UNSET
    env = {PEPPER_ENV: PEPPER, "KEEP_ME": "1"}
    changed = _env_safety.neutralize_credentials(env)
    assert PEPPER_ENV not in env
    assert PEPPER_ENV in changed and changed[PEPPER_ENV] is None
    assert env["KEEP_ME"] == "1"


def test_s05_r28_new_files_join_the_black_ratchet():
    """R-S05-8 (D03 F1-7 precedent): the three new files are allowlisted."""
    entries = {
        line.strip()
        for line in BLACK_PATHS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    for path in (
        "app/utils/request_context.py",
        "app/middleware/request_context.py",
        "tests/test_s81_s05_request_context.py",
    ):
        assert path in entries, f"{path} missing from .github/black-clean-paths.txt"


# ===========================================================================
# PIN rows (green at base)
# ===========================================================================


def _py_files(*roots):
    for root in roots:
        if root.is_dir():
            yield from sorted(root.rglob("*.py"))


_ALLOWED_CTX_FILES = {
    "app/utils/request_context.py",
    "app/middleware/request_context.py",
    "app/main.py",
    "app/api/auth_routes.py",
}


def test_s05_p01_no_consumer_in_app():
    """Nothing reads the ContextVars yet. Each consumer unit (S81-06 / S81-09 /
    S81-22) lists this node as its deliberate pin change (R-S05-10)."""
    for path in _py_files(APP_DIR, SCRIPTS_DIR):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        if "request_context" in text:
            assert rel in _ALLOWED_CTX_FILES, rel
        for needle in (
            "device_key_pepper",
            "x-ai-consent-version",
            "x-compare-request-id",
            "header_state",
        ):
            if needle in low:
                assert rel in {
                    "app/utils/request_context.py",
                    "app/middleware/request_context.py",
                }, (rel, needle)
        if "request_context" not in text:
            continue
        tree = ast.parse(text)
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module == LEAF_NAME:
                got = {a.name for a in n.names}
                if rel == "app/middleware/request_context.py":
                    assert got <= {
                        "bind_from_headers",
                        "request_context_headers_enabled",
                        "reset_request_context",
                    }, got
                elif rel == "app/api/auth_routes.py":
                    assert got == {"DEVICE_FINGERPRINT_RE"}, got
                else:
                    raise AssertionError(f"{rel} imports the leaf: {got}")
            if isinstance(n, ast.ImportFrom) and n.module == MW_NAME:
                assert rel == "app/main.py", rel
                assert {a.name for a in n.names} == {"RequestContextMiddleware"}
            if isinstance(n, ast.Import):
                for a in n.names:
                    assert a.name not in (LEAF_NAME, MW_NAME), (rel, a.name)
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                if n.value in (LEAF_NAME, MW_NAME):
                    raise AssertionError(f"{rel} names {n.value} as a string")


_CTX_HEADER_NAMES = {
    "x-ai-consent-version",
    "x-device-fingerprint",
    "x-compare-request-id",
    "x_ai_consent_version",
    "x_device_fingerprint",
    "x_compare_request_id",
}


def test_s05_p02_openapi_declares_no_context_header():
    schema = app_main.app.openapi()
    found = []
    for path, ops in schema.get("paths", {}).items():
        for method, op in ops.items():
            if not isinstance(op, dict):
                continue
            for p in op.get("parameters", []) or []:
                if str(p.get("name", "")).lower() in _CTX_HEADER_NAMES:
                    found.append((path, method, p.get("name")))
    assert found == []


def test_s05_p03_cors_config_literal():
    entries = [
        m for m in app_main.app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    ]
    assert len(entries) == 1
    assert dict(entries[0].kwargs) == {
        "allow_origins": app_main.ALLOWED_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Admin-Key",
            "X-Request-ID",
        ],
    }
    assert tuple(entries[0].args) == ()


# P4 literals recorded at base 84c861f6 in state (a), twice byte-identical.
P4_RECORDS = {
    "/api/v1/s05-no-such-route": [
        404,
        '{"detail":"Not Found"}',
        [
            ["content-length", "22"],
            [
                "content-security-policy",
                "default-src 'none'; " "frame-ancestors 'none'",
            ],
            ["content-type", "application/json"],
            ["permissions-policy", "camera=(), microphone=(), " "geolocation=()"],
            ["referrer-policy", "strict-origin-when-cross-origin"],
            ["strict-transport-security", "max-age=31536000; " "includeSubDomains"],
            ["x-content-type-options", "nosniff"],
            ["x-frame-options", "DENY"],
            ["x-request-id", "s05-fixed-request-id"],
            ["x-xss-protection", "1; mode=block"],
        ],
    ],
    "/api/v1/usage/status": [
        401,
        '{"success":false,"error":"Authorization '
        "header "
        'missing","code":"AUTH_REQUIRED","request_id":"s05-fixed-request-id"}',
        [
            ["content-length", "115"],
            [
                "content-security-policy",
                "default-src 'none'; frame-ancestors " "'none'",
            ],
            ["content-type", "application/json"],
            ["permissions-policy", "camera=(), microphone=(), " "geolocation=()"],
            ["referrer-policy", "strict-origin-when-cross-origin"],
            ["strict-transport-security", "max-age=31536000; includeSubDomains"],
            ["x-content-type-options", "nosniff"],
            ["x-frame-options", "DENY"],
            ["x-request-id", "s05-fixed-request-id"],
            ["x-xss-protection", "1; mode=block"],
        ],
    ],
}


def _p4_state(monkeypatch, state):
    headers = {"X-Request-ID": "s05-fixed-request-id"}
    if state == "a":
        monkeypatch.delenv(FLAG, raising=False)
        monkeypatch.delenv(PEPPER_ENV, raising=False)
        return headers
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    if state == "b":
        monkeypatch.setenv(FLAG, "false")
    else:
        monkeypatch.setenv(FLAG, "true")
    if state in ("b", "c"):
        headers.update(
            {
                "X-AI-Consent-Version": "3",
                "X-Device-Fingerprint": FP_A,
                "X-Compare-Request-Id": UID_A,
            }
        )
    else:
        headers.update(
            {
                "X-AI-Consent-Version": BAD,
                "X-Device-Fingerprint": "AB" * 32,
                "X-Compare-Request-Id": "{" + UID_A + "}",
            }
        )
    return headers


def _p4_record(resp):
    hdrs = sorted(
        [k.lower(), v] for k, v in resp.headers.items() if k.lower() != "date"
    )
    return [resp.status_code, resp.content.decode("latin-1"), hdrs]


@pytest.mark.parametrize("state", ["a", "b", "c", "d"])
@pytest.mark.parametrize(
    "path",
    ["/api/v1/usage/status", "/api/v1/s05-no-such-route"],
    ids=["401", "404"],
)
def test_s05_p04_response_bytes_literal(monkeypatch, state, path):
    from fastapi.testclient import TestClient

    headers = _p4_state(monkeypatch, state)
    client = TestClient(app_main.app)
    got = _p4_record(client.get(path, headers=headers))
    assert got == P4_RECORDS[path]


@pytest.mark.parametrize("flag_value", [None, "true"], ids=["unset", "true"])
@pytest.mark.parametrize(
    "path",
    ["/api/v1/usage/status", "/api/v1/s05-no-such-route"],
    ids=["401", "404"],
)
def test_s05_p05_no_header_value_logged(monkeypatch, caplog, flag_value, path):
    from fastapi.testclient import TestClient

    _set_flag(monkeypatch, flag_value)
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    bad_consent = "zz" + "9"
    headers = {
        "X-AI-Consent-Version": bad_consent,
        "X-Device-Fingerprint": FP_A,
        "X-Compare-Request-Id": UID_A,
    }
    caplog.set_level(logging.DEBUG)
    resp = TestClient(app_main.app).get(path, headers=headers)
    assert resp.status_code in (401, 404)
    for sentinel in (FP_A, UID_A, bad_consent, PEPPER):
        assert sentinel not in caplog.text, sentinel


class _StubRequest:
    def __init__(self, value):
        self.headers = {} if value is None else {"X-Device-Fingerprint": value}


def test_s05_p06_fp_readers_unchanged():
    import app.api.auth_routes as auth_routes
    import app.api.referral_routes as referral_routes
    import app.services.usage_service as usage_service

    inputs = [FP_A, "AB" * 32, "a" * 63, "", None, FP_A + "\n"]
    got_auth = [
        auth_routes._read_valid_device_fingerprint(_StubRequest(v)) for v in inputs
    ]
    assert got_auth == [FP_A, None, None, "", None, FP_A + "\n"]
    got_usage = [usage_service.valid_device_fingerprint(v) for v in inputs]
    assert got_usage == [FP_A, None, None, None, None, FP_A + "\n"]
    assert usage_service._DEVICE_FINGERPRINT_RE.pattern == r"^[a-f0-9]{64}$"
    field = referral_routes.ShareRequest.model_fields["device_fingerprint_hash"]
    patterns = [getattr(m, "pattern", None) for m in field.metadata]
    assert r"^[a-f0-9]{64}$" in patterns, field.metadata


def test_s05_p07_route_header_reads_untouched():
    needle = 'valid_device_fingerprint(request.headers.get("x-device-fingerprint"))'
    for rel in ("app/api/image_routes.py", "app/api/text_routes.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert text.count(needle) == 1, rel
    auth = AUTH_ROUTES_PATH.read_text(encoding="utf-8")
    assert auth.count('request.headers.get("X-Device-Fingerprint")') == 1


def test_s05_p08_no_dual_hash_names():
    """R-S05-1: legacy_hash / device_lookup_keys are dropped from this unit
    (the transition is S81-08 + S81-09's dual-VALUE design)."""
    leaf = _mod(LEAF_NAME)
    if leaf is not None:
        assert not hasattr(leaf, "legacy_hash")
        assert not hasattr(leaf, "device_lookup_keys")
    for path in _py_files(APP_DIR, SCRIPTS_DIR):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        assert "legacy_hash" not in text, rel
        assert "device_lookup_keys" not in text, rel


# ===========================================================================
# Additive PIN rows written by GREEN (GATE_S81_05 GC-1 / GC-2); the rows above
# are the frozen RED bytes (sha ecdb5792...), unchanged.
# ===========================================================================

_P19_SPELLINGS = (
    ("x-ai-consent-version", "X-AI-Consent-Version", "X-AI-CONSENT-VERSION"),
    ("x-device-fingerprint", "X-Device-Fingerprint", "X-DEVICE-FINGERPRINT"),
    ("x-compare-request-id", "X-Compare-Request-Id", "X-COMPARE-REQUEST-ID"),
)
_P19_OTHER_NAMES = ("x-request-id", "", b"x-unknown", "x-device", None, 3)


@pytest.mark.parametrize(
    "headers,expected",
    [
        pytest.param("valid", ("ok", "ok", "ok"), id="all-ok"),
        pytest.param(
            [(H_CONSENT, BAD.encode()), (H_FP, FP_A.encode())],
            ("malformed", "ok", "absent"),
            id="mixed",
        ),
        pytest.param(
            [(H_ID, ("{" + UID_A + "}").encode())],
            ("absent", "absent", "malformed"),
            id="braced-id",
        ),
    ],
)
def test_s05_p19_header_state_accepts_str_names(monkeypatch, headers, expected):
    """GC-1: header_state takes the str header names too, case-insensitively,
    and agrees with the bytes constants; other names read "absent"."""
    leaf = _leaf()
    mwmod = _mw()
    hs = _fn(leaf, "header_state")
    if headers == "valid":
        headers = _valid_headers()
    monkeypatch.setenv(FLAG, "true")
    seen = {}

    async def downstream(scope, receive_, send_):
        seen["bytes"] = _states(leaf)
        seen["str"] = tuple(tuple(hs(s) for s in names) for names in _P19_SPELLINGS)
        seen["other"] = tuple(hs(o) for o in _P19_OTHER_NAMES)

    receive, send = _endpoints()
    _call(mwmod.RequestContextMiddleware(downstream), _scope(headers), receive, send)
    assert seen["bytes"] == expected
    assert seen["str"] == tuple((s, s, s) for s in expected)
    assert seen["other"] == ("absent",) * len(_P19_OTHER_NAMES)
    # outside a bound request every spelling reads "absent"
    for names in _P19_SPELLINGS:
        assert [hs(s) for s in names] == ["absent"] * 3


@pytest.mark.parametrize(
    "which,index",
    [
        pytest.param(H_CONSENT, 0, id="consent"),
        pytest.param(H_FP, 1, id="fp"),
        pytest.param(H_ID, 2, id="request-id"),
    ],
)
def test_s05_p20_empty_header_is_malformed(monkeypatch, which, index):
    """GC-2: a header sent with an EMPTY value is "malformed" (it was sent
    without a valid value), never "absent"; its value reads None."""
    leaf = _leaf()
    mwmod = _mw()
    monkeypatch.setenv(FLAG, "true")
    rec = _Recorder(leaf)
    receive, send = _endpoints()
    scope = _scope([(which, b"")])
    _call(mwmod.RequestContextMiddleware(rec), scope, receive, send)
    expected = ["absent", "absent", "absent"]
    expected[index] = "malformed"
    assert len(rec.calls) == 1
    assert rec.calls[0]["values"] == NONE3
    assert rec.calls[0]["states"] == tuple(expected)


# ===========================================================================
# Fix round 1 rows (RULINGS_FIX1_S81_05 F1-1); every row above is unchanged.
# ===========================================================================

# A pepper str that cannot be UTF-8 encoded: the POSIX surrogateescape form of
# a non-UTF-8 env byte (0xff), and a padded lone high surrogate. Built at run
# time so the file stays pure ASCII.
_FX1_UNENCODABLE = (
    pytest.param("s05" + chr(0xDCFF) + "pepper", id="surrogateescape"),
    pytest.param("  " + chr(0xD800) + "s05\t", id="lone-high"),
)
_FX1_NEVER_LOGGED = ("surrogate", "codec", "UnicodeEncodeError", "UnicodeError")


@pytest.mark.parametrize("pepper_value", _FX1_UNENCODABLE)
def test_s05_fx1_device_key_fails_closed_on_unencodable_pepper(
    monkeypatch, caplog, pepper_value
):
    """F1-1: a pepper that cannot be UTF-8 encoded fails CLOSED: device_key
    returns None (it never raises) and logs the SAME once-per-process WARNING
    naming DEVICE_KEY_PEPPER, never the value, never the exception text.
    os.getenv is patched for the pepper name only (the r11 pattern): it is what
    os.environ hands back for a non-UTF-8 env byte on POSIX."""
    leaf = _leaf()
    dk = _fn(leaf, "device_key")
    reset = _fn(leaf, "_reset_pepper_warning")
    reset()
    real_getenv = os.getenv

    def _getenv(key, default=None):
        if key == PEPPER_ENV:
            return pepper_value
        return real_getenv(key, default)

    monkeypatch.setattr(os, "getenv", _getenv)
    caplog.set_level(logging.DEBUG, logger=LEAF_LOGGER)
    outs, raised = [], []
    for _ in range(3):
        try:
            outs.append(dk(FP_A))
        except Exception as exc:  # noqa: BLE001 - a raise is the defect
            raised.append(type(exc).__name__)
    assert raised == [], raised
    assert outs == [None] * 3
    recs = [r for r in caplog.records if r.name == LEAF_LOGGER]
    assert len(recs) == 1, [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.WARNING
    assert recs[0].getMessage() == WARN_TEXT
    assert PEPPER_ENV in recs[0].getMessage()
    assert recs[0].exc_info is None
    assert pepper_value.strip() not in caplog.text
    for needle in _FX1_NEVER_LOGGED + (FP_A,):
        assert needle not in caplog.text
    # an invalid fingerprint still reads None
    assert dk("zz") is None
    # the latch is per process: after the seam resets it, one more WARNING
    reset()
    assert dk(FP_A) is None
    recs = [r for r in caplog.records if r.name == LEAF_LOGGER]
    assert len(recs) == 2


# ===========================================================================
# Rebase-round row (the rebase onto e1878dd8; re-verifier minor m1, mutant
# RV10); every row above is unchanged.
# ===========================================================================

# Upper / mixed case bytes spellings of the three header names (index order
# of _header_names: consent, fingerprint, request id).
_RB1_UPPER_BYTES = (
    (b"X-AI-Consent-Version", b"X-AI-CONSENT-VERSION"),
    (b"X-Device-Fingerprint", b"X-DEVICE-FINGERPRINT"),
    (b"X-Compare-Request-Id", b"X-COMPARE-REQUEST-ID"),
)


def test_s05_rb1_upper_case_bytes_name_reads_absent_and_binds_nothing(
    monkeypatch,
):
    """F1-2 / stated limit 13 (re-verifier m1, kills RV10: bytes-name case
    folding put back): bytes header names are compared as EXACT bytes.
    (a) A scope whose three header names are upper / mixed case bytes binds
    nothing: every value None, every state "absent". (b) Inside a request
    bound from the lower-case names, every upper / mixed case bytes spelling
    (bytes and bytearray) reads "absent" while the lower-case constants and
    the str spellings read "ok". Full configuration present (flag ON, the
    pepper set to a synthetic value)."""
    leaf = _leaf()
    mwmod = _mw()
    hs = _fn(leaf, "header_state")
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV, PEPPER)
    lows = (H_CONSENT, H_FP, H_ID)
    valid = dict(_valid_headers())
    # (a) upper / mixed case bytes names in the scope bind nothing
    for spelling in (0, 1):
        rec = _Recorder(leaf)
        receive, send = _endpoints()
        headers = [(_RB1_UPPER_BYTES[i][spelling], valid[lows[i]]) for i in range(3)]
        _call(mwmod.RequestContextMiddleware(rec), _scope(headers), receive, send)
        assert len(rec.calls) == 1
        assert rec.calls[0]["values"] == NONE3
        assert rec.calls[0]["states"] == ABSENT3
        assert tuple(hs(s) for s in (x[spelling] for x in _RB1_UPPER_BYTES)) == ABSENT3
    # (b) bound from the lower-case names: only the exact bytes match
    seen = {}

    async def downstream(scope, receive_, send_):
        seen["values"] = _values(leaf)
        seen["lower"] = tuple(hs(n) for n in lows)
        seen["upper"] = tuple(tuple(hs(s) for s in x) for x in _RB1_UPPER_BYTES)
        seen["upper_ba"] = tuple(
            tuple(hs(bytearray(s)) for s in x) for x in _RB1_UPPER_BYTES
        )
        seen["str"] = tuple(
            tuple(hs(s.decode("ascii")) for s in x) for x in _RB1_UPPER_BYTES
        )

    receive, send = _endpoints()
    _call(
        mwmod.RequestContextMiddleware(downstream),
        _scope(_valid_headers()),
        receive,
        send,
    )
    assert seen["values"] == (3, FP_A, UID_A)
    assert seen["lower"] == ("ok", "ok", "ok")
    assert seen["upper"] == (("absent", "absent"),) * 3
    assert seen["upper_ba"] == (("absent", "absent"),) * 3
    assert seen["str"] == (("ok", "ok"),) * 3
    # outside a bound request every spelling reads "absent"
    for x in _RB1_UPPER_BYTES:
        assert [hs(s) for s in x] == ["absent", "absent"]
