"""S81-08b LEGACY-FINGERPRINT-READER: the RED file (11 RED rows, 14 PIN rows).

Unit: S81-08b (lane B backend, additive, FLAGGED). Flag ENABLE_LEGACY_FINGERPRINT_READER (new
name, default OFF, read per call as the FIRST statement of the gated predicate).
Authorities, in precedence order: RULINGS_S81_08B.md (R-S08B-1..11 and its Measurement rulings),
then the corrections of .qa-s80/S81-08b_SPEC_REVIEW.md, then .qa-s80/S81-08b_UNIT_SPEC.md
(sections 2, 5 and 6).

Scope (R-S08B-1): the two request-time stored-row matches only, POST /api/v1/auth/register and
the W3-3 social apply (both through _inherit_device_counter). Under the flag, when the request
carries a valid X-Device-Fingerprint-Legacy header that differs from X-Device-Fingerprint, the
match reads users.device_fingerprint_hash IN (NEW, LEGACY) with ONE select ordered desc, limit 1
(R-S08B-4), and the update stores the NEW value only (no upgrade-on-match). An invalid or absent
legacy header is dropped silently (R-S08B-6). The share route, SAME_DEVICE and the referral
device lifetime cap are untouched and pinned (P8, P11, P12; mutants M18-M20, R-S08B-7).

Base: 86d5a24d (origin/main at RED). The spec measured at ea3aef15; S81-14 (#373) touched no
file this unit reads (app/api/auth_routes.py, app/api/referral_routes.py,
app/services/referral_service.py, app/services/abuse_detection_service.py,
app/services/sentry_service.py and app/utils/request_context.py are byte-identical between the
two shas), so every app cite of the spec holds at 86d5a24d. CLAUDE.md moved: the Feature Flags
paragraph is :341, the S81-04 row :494 and the S81-14 row :497 at 86d5a24d.

Literal call lists (R-S08B-8; review C7): REG_BASE, SOCIAL_BASE_NULL and SOCIAL_BASE_OWNED below
were RECORDED AT BASE 86d5a24d with THIS file's evaluating FakeDB and its own tie-free seeds (the
spec probe's recording client returned a fixed row regardless of filters, so only the call SHAPE
transferred from probe_out.json; the update values are this file's).

Hermetic: app.main is imported first; no network, no .env, no credential; every fingerprint is
sha256 of a synthetic byte string and every id a nil-shaped uuid, both built at run time; the
slowapi limiter is disabled per test; the unit flag is deleted by an autouse fixture and every
row sets every flag it depends on explicitly (B1: the flag-OFF / no-op PIN rows run under the
FULL configuration of spec 2.6 plus a call recorder). Missing production symbols are read with
getattr(auth_routes, name, None) and asserted, so every RED row fails at base on an
AssertionError only. This file carries no backslash and no byte above 127 (control characters
are built with chr()).

Row map (node prefix -> row):
  test_r1_  R1  flag reader idiom                  test_p1_  P1  flag OFF identity, register
  test_r2_  R2  legacy helper truth table          test_p2_  P2  build-3 identity, register
  test_r3_  R3  register dual read, legacy max     test_p3_  P3  invalid / equal legacy, register
  test_r4_  R4  register stores NEW, NEW max       test_p4_  P4  legacy without a valid NEW
  test_r5_  R5  social dual read with floor        test_p5_  P5  social identity, no upgrade
  test_r6_  R6  register INFO line, no values      test_p6_  P6  social with W3-3 OFF
  test_r6pre_   R6 precondition (C12), PIN         test_p7_  P7  social build-3 identity
  test_r7_  R7  social INFO line                   test_p8_  P8  share untouched (M18)
  test_r8_  R8  top=new / top=none                 test_p9_  P9  Sentry redaction
  test_r9_  R9  dual failure silent and typed      test_p10_ P10 OpenAPI
  test_r10_ R10 one reader in app/                 test_p11_ P11 SAME_DEVICE untouched (M19)
  test_r11_ R11 CLAUDE.md row                      test_p12_ P12 lifetime cap untouched (M20)
                                                   test_p13_ P13 base functions byte-identical
                                                   test_p14_ P14 leaf import shape + names rule
"""
import ast
import asyncio
import copy
import hashlib
import json
import logging
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import auth_routes

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
SCRIPTS_DIR = ROOT / "scripts"
AUTH_ROUTES_PATH = APP_DIR / "api" / "auth_routes.py"
CLAUDE_MD = ROOT / "CLAUDE.md"
NL = chr(10)

FLAG = "ENABLE_LEGACY_FINGERPRINT_READER"
W33_FLAG = "ENABLE_SOCIAL_DEVICE_FINGERPRINT"
CTX_FLAG = "ENABLE_REQUEST_CONTEXT_HEADERS"
REFERRAL_FLAG = "ENABLE_REFERRAL_SYSTEM"
PEPPER_ENV = "DEVICE_KEY_PEPPER"
PRIMARY = "X-Device-Fingerprint"
LEGACY = "X-Device-Fingerprint-Legacy"
LOG_TAG = "[LEGACY-FP]"
AUTH_LOGGER = "app.api.auth_routes"

# Synthetic values, built at run time (personal-data rule).
NEW = hashlib.sha256(b"s81-08b-new").hexdigest()
LEG = hashlib.sha256(b"s81-08b-legacy").hexdigest()
OTHER = hashlib.sha256(b"s81-08b-other").hexdigest()
UID = str(uuid.UUID(int=0x8B1))
SIB_LEG = str(uuid.UUID(int=0x8B2))
SIB_NEW = str(uuid.UUID(int=0x8B3))
SIB_OTHER = str(uuid.UUID(int=0x8B4))
REF_UID = str(uuid.UUID(int=0x8B5))
INV_UID = str(uuid.UUID(int=0x8B6))
CMP_ID = str(uuid.UUID(int=0x8B7))
EMAIL = "s81-08b@example.com"
PASSWORD = "S81bPass" + "word9"

OFF_SPELLINGS = (None, "", "false", "0", "off", "no", "garbage")
ON_SPELLINGS = ("true", "TRUE", " true ", "1", "yes", "on")

REG_PAYLOAD = {
    "success": True,
    "user": {"id": UID, "email": EMAIL},
    "session": {"access_token": "s81-08b-access", "refresh_token": "s81-08b-refresh"},
    "message": "ok",
}
# The flag-OFF base response body of POST /register (response_model=AuthResponse), recorded at base.
REG_BODY = {
    "success": True,
    "user": {"id": UID, "email": EMAIL},
    "session": {"access_token": "s81-08b-access", "refresh_token": "s81-08b-refresh"},
    "message": "ok",
    "error": None,
}
SOCIAL_REQ = {"provider": "google", "id_token": "s81-08b-synthetic-id-token"}
SOCIAL_PAYLOAD = {
    "success": True,
    "user": {"id": UID, "email": EMAIL, "preferences_completed": False},
    "session": {"access_token": "s81-08b-access", "refresh_token": "s81-08b-refresh"},
    "message": "Signed in with google",
}
# social_login returns the service result unchanged: the base body, recorded at base.
SOCIAL_BODY = {
    "success": True,
    "user": {"id": UID, "email": EMAIL, "preferences_completed": False},
    "session": {"access_token": "s81-08b-access", "refresh_token": "s81-08b-refresh"},
    "message": "Signed in with google",
}

# ---------------------------------------------------------------------------------------------
# Literal call lists RECORDED AT BASE 86d5a24d with this file's FakeDB and seeds (R-S08B-8).
# REG_BASE: _reg_seed() (LEG:3, NEW:1, OTHER:9) -> the base read is .eq(NEW) and writes 1.
REG_BASE = [
    ["table", ["users"]],
    ["select", ["lifetime_comparisons_used"]],
    ["eq", ["device_fingerprint_hash", NEW]],
    ["order", ["lifetime_comparisons_used"], {"desc": True}],
    ["limit", [1]],
    ["execute", []],
    ["table", ["users"]],
    ["update", [{"device_fingerprint_hash": NEW, "lifetime_comparisons_used": 1}]],
    ["eq", ["id", UID]],
    ["execute", []],
]
# SOCIAL_BASE_NULL: _social_seed() (own NULL lcu 1, NEW:2, LEG:4, OTHER:9) -> max(1, 2) = 2.
SOCIAL_BASE_NULL = [
    ["table", ["users"]],
    ["select", ["device_fingerprint_hash, lifetime_comparisons_used"]],
    ["eq", ["id", UID]],
    ["limit", [1]],
    ["execute", []],
    ["table", ["users"]],
    ["select", ["lifetime_comparisons_used"]],
    ["eq", ["device_fingerprint_hash", NEW]],
    ["order", ["lifetime_comparisons_used"], {"desc": True}],
    ["limit", [1]],
    ["execute", []],
    ["table", ["users"]],
    ["update", [{"device_fingerprint_hash": NEW, "lifetime_comparisons_used": 2}]],
    ["eq", ["id", UID]],
    ["execute", []],
]
# SOCIAL_BASE_OWNED: the own row already carries a hash -> the own read only, early return.
SOCIAL_BASE_OWNED = [
    ["table", ["users"]],
    ["select", ["device_fingerprint_hash, lifetime_comparisons_used"]],
    ["eq", ["id", UID]],
    ["limit", [1]],
    ["execute", []],
]


def _reg_legacy(lcu):
    """The flag-ON register call list of spec 2.2 (one dual read, the NEW value stored)."""
    return [
        ["table", ["users"]],
        ["select", ["lifetime_comparisons_used, device_fingerprint_hash"]],
        ["in_", ["device_fingerprint_hash", [NEW, LEG]]],
        ["order", ["lifetime_comparisons_used"], {"desc": True}],
        ["limit", [1]],
        ["execute", []],
        ["table", ["users"]],
        ["update", [{"device_fingerprint_hash": NEW, "lifetime_comparisons_used": lcu}]],
        ["eq", ["id", UID]],
        ["execute", []],
    ]


def _social_legacy(lcu):
    """The flag-ON social call list: the own read (5), the dual read (6), the update (4)."""
    return [
        ["table", ["users"]],
        ["select", ["device_fingerprint_hash, lifetime_comparisons_used"]],
        ["eq", ["id", UID]],
        ["limit", [1]],
        ["execute", []],
        ["table", ["users"]],
        ["select", ["lifetime_comparisons_used, device_fingerprint_hash"]],
        ["in_", ["device_fingerprint_hash", [NEW, LEG]]],
        ["order", ["lifetime_comparisons_used"], {"desc": True}],
        ["limit", [1]],
        ["execute", []],
        ["table", ["users"]],
        ["update", [{"device_fingerprint_hash": NEW, "lifetime_comparisons_used": lcu}]],
        ["eq", ["id", UID]],
        ["execute", []],
    ]


def _reg_seed():
    """Tie-free: the NEW-only read finds 1, the dual read finds 3 (LEG), OTHER never matches."""
    return {
        "users": [
            {"id": UID, "device_fingerprint_hash": None, "lifetime_comparisons_used": 0},
            {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_comparisons_used": 3},
            {"id": SIB_NEW, "device_fingerprint_hash": NEW, "lifetime_comparisons_used": 1},
            {"id": SIB_OTHER, "device_fingerprint_hash": OTHER, "lifetime_comparisons_used": 9},
        ]
    }


def _social_seed(own_hash=None, own_lcu=1):
    """Tie-free: own row, NEW:2, LEG:4, OTHER:9."""
    return {
        "users": [
            {"id": UID, "device_fingerprint_hash": own_hash, "lifetime_comparisons_used": own_lcu},
            {"id": SIB_NEW, "device_fingerprint_hash": NEW, "lifetime_comparisons_used": 2},
            {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_comparisons_used": 4},
            {"id": SIB_OTHER, "device_fingerprint_hash": OTHER, "lifetime_comparisons_used": 9},
        ]
    }


# ---------------------------------------------------------------------------------------------
# FakeDB: an in-memory PostgREST stand-in that EVALUATES eq / in_ / not_.is_ / order(desc) /
# limit / single over seeded rows, applies update payloads, and RECORDS every builder call as
# [method, args] or [method, args, kwargs] in call order (spec 2.7). raise_on = method names
# whose presence in a query makes its execute() raise RuntimeError(raise_message).


class _Result:
    def __init__(self, data):
        self.data = data
        self.count = None


class FakeDB:
    def __init__(self, tables, raise_on=(), raise_message="s81-08b fake failure"):
        self.tables = {name: [dict(r) for r in rows] for name, rows in tables.items()}
        self.calls = []
        self.updates = []
        self.raise_on = frozenset(raise_on)
        self.raise_message = raise_message

    def record(self, method, args, kwargs=None):
        entry = [method, copy.deepcopy(list(args))]
        if kwargs:
            entry.append(copy.deepcopy(dict(kwargs)))
        self.calls.append(entry)

    def table(self, *args, **kwargs):
        self.record("table", args, kwargs)
        return _Query(self, args[0])

    def table_names(self):
        return [c[1][0] for c in self.calls if c[0] == "table"]


class _NotBuilder:
    def __init__(self, query):
        self._q = query

    def is_(self, *args, **kwargs):
        self._q.db.record("not_.is_", args, kwargs)
        self._q.used.add("not_.is_")
        self._q.filters.append(("not_is", args[0], args[1]))
        return self._q


class _Query:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self.columns = None
        self.filters = []
        self.order_by = None
        self.limit_n = None
        self.single_row = False
        self.payload = None
        self.used = set()

    def _step(self, method, args, kwargs):
        self.db.record(method, args, kwargs)
        self.used.add(method)

    def select(self, *args, **kwargs):
        self._step("select", args, kwargs)
        self.columns = [c.strip() for c in str(args[0]).split(",")] if args else None
        return self

    def eq(self, *args, **kwargs):
        self._step("eq", args, kwargs)
        self.filters.append(("eq", args[0], args[1]))
        return self

    def in_(self, *args, **kwargs):
        self._step("in_", args, kwargs)
        self.filters.append(("in", args[0], list(args[1])))
        return self

    @property
    def not_(self):
        return _NotBuilder(self)

    def order(self, *args, **kwargs):
        self._step("order", args, kwargs)
        self.order_by = (args[0], bool(kwargs.get("desc", False)))
        return self

    def limit(self, *args, **kwargs):
        self._step("limit", args, kwargs)
        self.limit_n = int(args[0])
        return self

    def single(self, *args, **kwargs):
        self._step("single", args, kwargs)
        self.single_row = True
        return self

    def update(self, *args, **kwargs):
        self._step("update", args, kwargs)
        self.payload = dict(args[0])
        return self

    def _matches(self, row):
        for op, col, val in self.filters:
            have = row.get(col)
            if op == "eq" and have != val:
                return False
            if op == "in" and have not in val:
                return False
            if op == "not_is" and val == "null" and have is None:
                return False
        return True

    def execute(self, *args, **kwargs):
        self._step("execute", args, kwargs)
        if self.used & self.db.raise_on:
            raise RuntimeError(self.db.raise_message)
        rows = self.db.tables.setdefault(self.name, [])
        hit = [r for r in rows if self._matches(r)]
        if self.payload is not None:
            for r in hit:
                r.update(self.payload)
            self.db.updates.append((self.name, copy.deepcopy(self.payload)))
            return _Result([dict(r) for r in hit])
        if self.order_by is not None:
            col, desc = self.order_by
            hit = sorted(hit, key=lambda r: r.get(col) or 0, reverse=desc)
        if self.limit_n is not None:
            hit = hit[: self.limit_n]
        if self.columns is not None and self.columns != ["*"]:
            hit = [{c: r.get(c) for c in self.columns} for r in hit]
        else:
            hit = [dict(r) for r in hit]
        if self.single_row:
            return _Result(hit[0] if hit else None)
        return _Result(hit)


# ---------------------------------------------------------------------------------------------
# A request stand-in whose header mapping records every read (R2: OFF reads nothing).


class _RecordingHeaders:
    def __init__(self, values, explode=False):
        self._values = {str(k).lower(): v for k, v in values.items()}
        self.reads = []
        self._explode = explode

    def _read(self, key):
        self.reads.append(key)
        if self._explode:
            raise RuntimeError("s81-08b header read failure")

    def get(self, key, default=None):
        self._read(key)
        return self._values.get(str(key).lower(), default)

    def __getitem__(self, key):
        self._read(key)
        return self._values[str(key).lower()]

    def __contains__(self, key):
        self._read(key)
        return str(key).lower() in self._values

    def getlist(self, key):
        self._read(key)
        value = self._values.get(str(key).lower())
        return [] if value is None else [value]

    def keys(self):
        self._read("<keys>")
        return list(self._values)

    def items(self):
        self._read("<items>")
        return list(self._values.items())

    def __iter__(self):
        self._read("<iter>")
        return iter(list(self._values))

    def __len__(self):
        self._read("<len>")
        return len(self._values)


class _RecordingRequest:
    def __init__(self, values, explode=False):
        self.recorder = _RecordingHeaders(values, explode=explode)
        self.touches = 0

    @property
    def headers(self):
        self.touches += 1
        return self.recorder


# ---------------------------------------------------------------------------------------------
# Fixtures and drivers


@pytest.fixture(autouse=True)
def _no_limiter():
    """register is 3/minute, social-login 10/minute: disable slowapi for this file only."""
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prior


@pytest.fixture(autouse=True)
def _unit_flag_unset(monkeypatch):
    """Never inherit the ambient env: every row sets the unit flag itself."""
    monkeypatch.delenv(FLAG, raising=False)
    yield


@pytest.fixture
def full(monkeypatch):
    """Spec 2.6 FULL configuration (B1). app.main is imported at module top, so the
    DEVICE_KEY_PEPPER set here survives the dotenv guard (CREDENTIALS_UNSET)."""
    monkeypatch.setenv(W33_FLAG, "true")
    monkeypatch.setenv(CTX_FLAG, "true")
    monkeypatch.setenv(REFERRAL_FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV, "s81-08b-" + "synthetic-pepper")
    monkeypatch.delenv("ENABLE_CONSENT_REQUIRED", raising=False)
    monkeypatch.delenv("ENABLE_APPLE_TOKEN_REVOCATION", raising=False)
    return monkeypatch


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def _debug(caplog):
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=AUTH_LOGGER)


def _register(db, headers):
    with patch.object(
        auth_routes, "register_user", new=AsyncMock(return_value=copy.deepcopy(REG_PAYLOAD))
    ), patch.object(auth_routes, "get_admin_supabase_client", return_value=db) as factory:
        resp = TestClient(app).post(
            "/api/v1/auth/register",
            json={"email": EMAIL, "password": PASSWORD},
            headers=headers,
        )
    return resp, factory


def _social(db, headers):
    with patch.object(
        auth_routes,
        "sign_in_with_social",
        new=AsyncMock(return_value=copy.deepcopy(SOCIAL_PAYLOAD)),
    ), patch.object(auth_routes, "get_admin_supabase_client", return_value=db) as factory:
        resp = TestClient(app).post("/api/v1/auth/social-login", json=SOCIAL_REQ, headers=headers)
    return resp, factory


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _tagged(caplog):
    return [
        (r.levelname, r.getMessage()) for r in caplog.records if LOG_TAG in r.getMessage()
    ]


def _log_text(caplog):
    parts = [caplog.text]
    for r in caplog.records:
        parts.append(r.getMessage())
        if r.exc_text:
            parts.append(r.exc_text)
    return NL.join(parts)


def _assert_no_values_logged(caplog):
    """R6 sentinel over R3-R9 (UID kept: test_r6pre_ measured no base line carries it)."""
    text = _log_text(caplog)
    assert NEW not in text, "a log line carries the NEW fingerprint"
    assert LEG not in text, "a log line carries the legacy fingerprint"
    assert UID not in text, "a log line carries the user id"


def _no_legacy_in_updates(db):
    return all(LEG not in json.dumps(payload) for _, payload in db.updates)


def _invalid_legacy_values():
    return [
        ("upper", LEG.upper()),
        ("len63", LEG[:63]),
        ("len65", LEG + "0"),
        ("trailing-newline", LEG + NL),
        ("empty", ""),
        ("leading-space", " " + LEG),
        ("non-ascii", chr(0xE9) * 64),
        ("non-hex", "g" * 64),
    ]


# ===================================================================================== RED rows


def test_r1_flag_reader_idiom(monkeypatch):
    fn = getattr(auth_routes, "legacy_fingerprint_reader_enabled", None)
    assert callable(fn), "R1: auth_routes.legacy_fingerprint_reader_enabled is missing"
    for value in OFF_SPELLINGS:
        _set_flag(monkeypatch, value)
        assert fn() is False, ("R1 OFF spelling", value)
    for value in ON_SPELLINGS:
        _set_flag(monkeypatch, value)
        assert fn() is True, ("R1 ON spelling", value)
    _set_flag(monkeypatch, "true")
    first = fn()
    _set_flag(monkeypatch, "false")
    second = fn()
    assert (first, second) == (True, False), "R1: the flag must be read per call"


def test_r2_legacy_helper_truth_table(monkeypatch, caplog):
    fn = getattr(auth_routes, "_read_valid_legacy_fingerprint", None)
    assert callable(fn), "R2: auth_routes._read_valid_legacy_fingerprint is missing"
    assert LEG.upper() != LEG and NEW != LEG
    _debug(caplog)
    _set_flag(monkeypatch, "true")
    assert fn(_RecordingRequest({LEGACY: LEG, PRIMARY: NEW}), NEW) == LEG, "R2 valid legacy"
    for label, value in _invalid_legacy_values():
        assert fn(_RecordingRequest({LEGACY: value, PRIMARY: NEW}), NEW) is None, ("R2", label)
    assert fn(_RecordingRequest({PRIMARY: NEW}), NEW) is None, "R2 absent legacy"
    assert fn(_RecordingRequest({LEGACY: LEG, PRIMARY: LEG}), LEG) is None, "R2 legacy == fp"
    exploding = _RecordingRequest({LEGACY: LEG, PRIMARY: NEW}, explode=True)
    assert fn(exploding, NEW) is None, "R2 a raising header read returns None"
    noisy = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == AUTH_LOGGER]
    assert noisy == [], ("R2: the legacy reader never logs (R-S08B-6)", noisy)
    for value in OFF_SPELLINGS:
        _set_flag(monkeypatch, value)
        req = _RecordingRequest({LEGACY: LEG, PRIMARY: NEW})
        assert fn(req, NEW) is None, ("R2 OFF returns None", value)
        assert (req.touches, req.recorder.reads) == (0, []), ("R2 OFF reads no header", value)


def test_r3_register_dual_read_legacy_max(full, caplog):
    _debug(caplog)
    _set_flag(full, "true")
    db = FakeDB(_reg_seed())
    resp, factory = _register(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert resp.json() == REG_BODY
    assert db.calls == _reg_legacy(3), db.calls
    assert db.updates == [("users", {"device_fingerprint_hash": NEW, "lifetime_comparisons_used": 3})]
    assert _no_legacy_in_updates(db)
    assert factory.call_count == 1
    _assert_no_values_logged(caplog)


def test_r4_register_stores_new_when_new_holds_max(full, caplog):
    _debug(caplog)
    _set_flag(full, "true")
    db = FakeDB(
        {
            "users": [
                {"id": UID, "device_fingerprint_hash": None, "lifetime_comparisons_used": 0},
                {"id": SIB_NEW, "device_fingerprint_hash": NEW, "lifetime_comparisons_used": 5},
                {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_comparisons_used": 3},
            ]
        }
    )
    resp, _ = _register(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert resp.json() == REG_BODY
    assert db.calls == _reg_legacy(5), db.calls
    assert db.updates == [("users", {"device_fingerprint_hash": NEW, "lifetime_comparisons_used": 5})]
    assert _no_legacy_in_updates(db)
    _assert_no_values_logged(caplog)


@pytest.mark.parametrize("own_lcu,expected", [(1, 4), (6, 6)], ids=["own1-device4", "own6-floor"])
def test_r5_social_dual_read_with_floor(full, caplog, own_lcu, expected):
    _debug(caplog)
    _set_flag(full, "true")
    db = FakeDB(
        {
            "users": [
                {"id": UID, "device_fingerprint_hash": None, "lifetime_comparisons_used": own_lcu},
                {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_comparisons_used": 4},
            ]
        }
    )
    resp, factory = _social(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert resp.json() == SOCIAL_BODY
    assert db.calls == _social_legacy(expected), db.calls
    assert db.updates == [
        ("users", {"device_fingerprint_hash": NEW, "lifetime_comparisons_used": expected})
    ]
    assert _no_legacy_in_updates(db)
    assert factory.call_count == 1
    _assert_no_values_logged(caplog)


def test_r6pre_base_paths_log_no_user_id(full, caplog):
    """PIN (R-S08B-8 / review C12): measured FIRST at base, no log line on the register and
    social paths carries the user id, so the R6 sentinel keeps UID (else NEW / LEG only)."""
    _debug(caplog)
    _set_flag(full, "false")
    _register(FakeDB(_reg_seed()), {PRIMARY: NEW, LEGACY: LEG})
    _social(FakeDB(_social_seed()), {PRIMARY: NEW, LEGACY: LEG})
    _social(FakeDB(_social_seed(own_hash=LEG, own_lcu=3)), {PRIMARY: NEW, LEGACY: LEG})
    _register(FakeDB(_reg_seed()), {PRIMARY: NEW.upper(), LEGACY: LEG})
    text = _log_text(caplog)
    assert caplog.records, "the capture saw no record at all (the sentinel would be vacuous)"
    assert UID not in text, "a base log line carries the user id"


def test_r6_register_info_line_constants_only(full, caplog):
    _debug(caplog)
    _set_flag(full, "true")
    db = FakeDB(_reg_seed())
    resp, _ = _register(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert _tagged(caplog) == [("INFO", "[LEGACY-FP] site=register top=legacy")], _tagged(caplog)
    tagged_records = [r for r in caplog.records if LOG_TAG in r.getMessage()]
    assert [r.name for r in tagged_records] == [AUTH_LOGGER]
    _assert_no_values_logged(caplog)


def test_r7_social_info_line(full, caplog):
    _debug(caplog)
    _set_flag(full, "true")
    db = FakeDB(
        {
            "users": [
                {"id": UID, "device_fingerprint_hash": None, "lifetime_comparisons_used": 1},
                {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_comparisons_used": 4},
            ]
        }
    )
    resp, _ = _social(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert _tagged(caplog) == [("INFO", "[LEGACY-FP] site=social top=legacy")], _tagged(caplog)
    _assert_no_values_logged(caplog)


@pytest.mark.parametrize("case", ["new-max", "no-rows"])
def test_r8_top_new_and_top_none(full, caplog, case):
    _debug(caplog)
    _set_flag(full, "true")
    rows = [{"id": UID, "device_fingerprint_hash": None, "lifetime_comparisons_used": 0}]
    if case == "new-max":
        rows += [
            {"id": SIB_NEW, "device_fingerprint_hash": NEW, "lifetime_comparisons_used": 5},
            {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_comparisons_used": 3},
        ]
        label, lcu = "new", 5
    else:
        rows += [
            {"id": SIB_OTHER, "device_fingerprint_hash": OTHER, "lifetime_comparisons_used": 9},
        ]
        label, lcu = "none", 0
    db = FakeDB({"users": rows})
    resp, _ = _register(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert _tagged(caplog) == [("INFO", "[LEGACY-FP] site=register top=" + label)], _tagged(caplog)
    assert db.updates == [("users", {"device_fingerprint_hash": NEW, "lifetime_comparisons_used": lcu})]
    assert db.calls == _reg_legacy(lcu), db.calls
    _assert_no_values_logged(caplog)


@pytest.mark.parametrize("site", ["register", "social"])
def test_r9_dual_failure_is_silent_and_typed(full, caplog, site):
    _debug(caplog)
    _set_flag(full, "true")
    headers = {PRIMARY: NEW, LEGACY: LEG}
    if site == "register":
        db = FakeDB(_reg_seed(), raise_on={"in_"}, raise_message="boom " + LEG)
        resp, _ = _register(db, headers)
        body = REG_BODY
    else:
        db = FakeDB(_social_seed(), raise_on={"in_"}, raise_message="boom " + LEG)
        resp, _ = _social(db, headers)
        body = SOCIAL_BODY
    assert resp.status_code == 200, resp.text
    assert resp.json() == body
    expected = [("WARNING", "[LEGACY-FP] site=" + site + " inherit failed: RuntimeError")]
    assert _tagged(caplog) == expected, _tagged(caplog)
    messages = [r.getMessage() for r in caplog.records]
    assert not any("device-fp inheritance failed" in m for m in messages)
    assert not any("device-fp social apply failed" in m for m in messages)
    assert db.updates == [], "a failed dual read writes nothing"
    _assert_no_values_logged(caplog)


def test_r10_one_legacy_reader_in_app():
    hits = sorted(
        p.relative_to(ROOT).as_posix()
        for p in APP_DIR.rglob("*.py")
        if "x-device-fingerprint-legacy" in p.read_text(encoding="utf-8", errors="replace").lower()
    )
    assert hits == ["app/api/auth_routes.py"], ("R10: files reading the legacy header", hits)
    tree = ast.parse(AUTH_ROUTES_PATH.read_text(encoding="utf-8"))
    fns = [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "_read_valid_legacy_fingerprint"
    ]
    assert len(fns) == 1, "R10: exactly one _read_valid_legacy_fingerprint"
    body = list(fns[0].body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    assert body, "R10: empty helper"
    first = body[0]
    calls = [
        n
        for n in ast.walk(first)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "legacy_fingerprint_reader_enabled"
    ]
    assert calls, "R10: the flag read must be the FIRST statement of the helper"
    names = {n.id for n in ast.walk(first) if isinstance(n, ast.Name)}
    assert "request" not in names, "R10: the first statement must not touch the request"


ROW_HEAD = "**SESSION 81 flag (S81-08b"
ROW_CAP = 8000
# Spec R11 tokens (case-sensitive identifiers) plus the R-S08B-2 activation tokens.
R11_EXACT = (
    "ENABLE_LEGACY_FINGERPRINT_READER",
    "X-Device-Fingerprint-Legacy",
    "SAME_DEVICE",
    "2027-03-31",
    "S81-08",
    "S81-08c",
    "OTA",
    "ENABLE_REQUEST_CONTEXT_HEADERS",
)
# Spec R11 words (case-insensitive) plus R-S08B-2 (dated ledger line, independent of request
# context) and R-S08B-10 (the index claim marked reasoned).
R11_WORDS = ("register", "social", "rollback", "ledger", "independent", "reasoned")
# R-S08B-10: "after S81-08 merges" is dropped.
R11_FORBIDDEN = ("after s81-08 merges",)


def test_r11_claude_md_row():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    at = text.find(NL + ROW_HEAD)
    assert at != -1, "R11: no column-0 SESSION 81 flag (S81-08b ...) paragraph in CLAUDE.md"
    start = at + 1
    ends = [
        i
        for i in (text.find(NL + "**SESSION", start), text.find(NL + "## ", start))
        if i != -1
    ]
    end = min(ends) if ends else len(text)
    row = text[start:end]
    assert len(row) <= ROW_CAP, ("R11: the row slice is not bounded (R-S08B-9)", len(row))
    for token in R11_EXACT:
        assert token in row, ("R11 token", token)
    low = row.lower()
    for word in R11_WORDS:
        assert word in low, ("R11 word", word)
    for bad in R11_FORBIDDEN:
        assert bad not in low, ("R11 forbidden", bad)
    flags_lines = [ln for ln in text.split(NL) if ln.startswith("**Feature Flags:**")]
    assert len(flags_lines) == 1, "R11: one Feature Flags paragraph"
    assert FLAG in flags_lines[0], "R11: the Feature Flags paragraph names the flag"


# ===================================================================================== PIN rows


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=lambda v: "unset" if v is None else repr(v))
def test_p1_flag_off_identity_register(full, caplog, value):
    _debug(caplog)
    _set_flag(full, value)
    db = FakeDB(_reg_seed())
    resp, factory = _register(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert resp.json() == REG_BODY
    assert db.calls == REG_BASE, db.calls
    assert factory.call_count == 1
    assert _tagged(caplog) == []


@pytest.mark.parametrize("value", ON_SPELLINGS, ids=repr)
def test_p2_build3_identity_register(full, caplog, value):
    _debug(caplog)
    _set_flag(full, value)
    db = FakeDB(_reg_seed())
    resp, factory = _register(db, {PRIMARY: NEW})
    assert resp.status_code == 200, resp.text
    assert resp.json() == REG_BODY
    assert db.calls == REG_BASE, db.calls
    assert factory.call_count == 1
    assert _tagged(caplog) == []


@pytest.mark.parametrize("case", ["upper", "len63", "len65", "empty", "non-hex", "equal-new"])
def test_p3_invalid_or_equal_legacy_register(full, caplog, case):
    _debug(caplog)
    _set_flag(full, "true")
    legacy = {
        "upper": LEG.upper(),
        "len63": LEG[:63],
        "len65": LEG + "0",
        "empty": "",
        "non-hex": "g" * 64,
        "equal-new": NEW,
    }[case]
    db = FakeDB(_reg_seed())
    resp, factory = _register(db, {PRIMARY: NEW, LEGACY: legacy})
    assert resp.status_code == 200, resp.text
    assert resp.json() == REG_BODY
    assert db.calls == REG_BASE, db.calls
    assert factory.call_count == 1
    assert _tagged(caplog) == []


@pytest.mark.parametrize("route", ["register", "social"])
@pytest.mark.parametrize("primary", ["absent", "upper", "len63", "empty"])
@pytest.mark.parametrize("value", ["false", "true"])
def test_p4_legacy_without_valid_new(full, caplog, route, primary, value):
    _debug(caplog)
    _set_flag(full, value)
    headers = {LEGACY: LEG}
    if primary == "upper":
        headers[PRIMARY] = NEW.upper()
    elif primary == "len63":
        headers[PRIMARY] = NEW[:63]
    elif primary == "empty":
        headers[PRIMARY] = ""
    if route == "register":
        db = FakeDB(_reg_seed())
        resp, factory = _register(db, headers)
        assert resp.json() == REG_BODY
    else:
        db = FakeDB(_social_seed())
        resp, factory = _social(db, headers)
        assert resp.json() == SOCIAL_BODY
    assert resp.status_code == 200, resp.text
    assert db.calls == [], db.calls
    assert factory.call_count == 0
    assert _tagged(caplog) == []


@pytest.mark.parametrize(
    "case", ["off-own-null", "off-own-legacy", "on-own-legacy", "on-own-new"]
)
def test_p5_social_identity_no_upgrade(full, caplog, case):
    _debug(caplog)
    _set_flag(full, "false" if case.startswith("off") else "true")
    own_hash = {"null": None, "legacy": LEG, "new": NEW}[case.rsplit("-", 1)[1]]
    db = FakeDB(_social_seed(own_hash=own_hash, own_lcu=1 if own_hash is None else 3))
    resp, factory = _social(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert resp.json() == SOCIAL_BODY
    expected = SOCIAL_BASE_NULL if own_hash is None else SOCIAL_BASE_OWNED
    assert db.calls == expected, db.calls
    if own_hash is not None:
        assert db.updates == [], "no upgrade-on-match (R-S08B-4)"
    assert factory.call_count == 1
    assert _tagged(caplog) == []


@pytest.mark.parametrize("w33", [None, "false"], ids=["w33-unset", "w33-false"])
def test_p6_social_with_w33_off(full, caplog, w33):
    _debug(caplog)
    if w33 is None:
        full.delenv(W33_FLAG, raising=False)
    else:
        full.setenv(W33_FLAG, w33)
    _set_flag(full, "true")
    db = FakeDB(_social_seed())
    resp, factory = _social(db, {PRIMARY: NEW, LEGACY: LEG})
    assert resp.status_code == 200, resp.text
    assert resp.json() == SOCIAL_BODY
    assert factory.call_count == 0
    assert db.calls == []
    assert _tagged(caplog) == []


@pytest.mark.parametrize("value", ON_SPELLINGS, ids=repr)
def test_p7_social_build3_identity(full, caplog, value):
    _debug(caplog)
    _set_flag(full, value)
    db = FakeDB(_social_seed())
    resp, factory = _social(db, {PRIMARY: NEW})
    assert resp.status_code == 200, resp.text
    assert resp.json() == SOCIAL_BODY
    assert db.calls == SOCIAL_BASE_NULL, db.calls
    assert factory.call_count == 1
    assert _tagged(caplog) == []


@pytest.mark.parametrize("case", ["upper", "len63", "equal-new"])
def test_p7_social_invalid_or_equal_legacy(full, caplog, case):
    _debug(caplog)
    _set_flag(full, "true")
    legacy = {"upper": LEG.upper(), "len63": LEG[:63], "equal-new": NEW}[case]
    db = FakeDB(_social_seed())
    resp, factory = _social(db, {PRIMARY: NEW, LEGACY: legacy})
    assert resp.status_code == 200, resp.text
    assert resp.json() == SOCIAL_BODY
    assert db.calls == SOCIAL_BASE_NULL, db.calls
    assert _tagged(caplog) == []


SHARE_RESULT = {"invite_id": "s81-08b-invite", "share_link": "https://example.invalid/i/s81-08b"}


@pytest.mark.parametrize("case", ["body-new", "body-absent", "body-upper"])
@pytest.mark.parametrize("value", ["false", "true"])
def test_p8_share_untouched(full, case, value):
    _set_flag(full, value)
    body = {"comparison_id": CMP_ID, "share_target": "copy"}
    if case == "body-new":
        body["device_fingerprint_hash"] = NEW
    elif case == "body-upper":
        body["device_fingerprint_hash"] = NEW.upper()

    async def _user():
        return {"id": REF_UID, "email": EMAIL, "access_token": "s81-08b-access"}

    app.dependency_overrides[auth_routes.get_current_user] = _user
    try:
        with patch("app.api.referral_routes.ReferralService") as svc_cls:
            svc = svc_cls.return_value
            svc.create_invite = AsyncMock(return_value=dict(SHARE_RESULT))
            resp = TestClient(app).post(
                "/api/v1/referrals/share",
                json=body,
                headers={PRIMARY: NEW, LEGACY: LEG},
            )
    finally:
        app.dependency_overrides.pop(auth_routes.get_current_user, None)
    if case == "body-upper":
        assert resp.status_code == 422, resp.text
        assert svc.create_invite.await_count == 0
        return
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"success": True, **SHARE_RESULT}
    assert svc.create_invite.await_count == 1
    assert svc.create_invite.await_args.args == ()
    assert svc.create_invite.await_args.kwargs == {
        "referrer_user_id": REF_UID,
        "comparison_id": CMP_ID,
        "share_target": "copy",
        "device_fingerprint_hash": NEW if case == "body-new" else None,
        "show_name": True,
        "show_result": True,
        "show_reasons": True,
    }


@pytest.mark.parametrize("header", ["x-device-fingerprint-legacy", "X-Device-Fingerprint-Legacy"])
@pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
def test_p9_sentry_filters_legacy_header(hook, header):
    from app.services import sentry_service

    fn = getattr(sentry_service, hook)
    event = {"request": {"headers": {"host": "testserver", header: LEG}}}
    out = fn(copy.deepcopy(event), {})
    assert out is not None
    assert out["request"]["headers"][header] == "[Filtered]"
    assert LEG not in json.dumps(out, default=str)


@pytest.mark.parametrize("value", ["false", "true"])
def test_p10_openapi_declares_no_fingerprint_parameter(monkeypatch, value):
    _set_flag(monkeypatch, value)
    prior = app.openapi_schema
    app.openapi_schema = None
    try:
        schema = app.openapi()
    finally:
        app.openapi_schema = prior
    found = []
    for path, ops in schema.get("paths", {}).items():
        for method, op in ops.items():
            if not isinstance(op, dict):
                continue
            for p in op.get("parameters", []) or []:
                if "fingerprint" in str(p.get("name", "")).lower():
                    found.append((path, method, p.get("name")))
    assert found == []
    assert "fingerprint-legacy" not in json.dumps(schema).lower()


@pytest.mark.parametrize("value", ["false", "true"])
def test_p11_same_device_untouched(full, value):
    from app.services import abuse_detection_service as ads
    from app.services import referral_service as rs

    _set_flag(full, value)
    db = FakeDB(
        {
            "users": [
                {
                    "id": INV_UID,
                    "email": "s81-08b-invitee@example.com",
                    "subscription_tier": "free",
                    "display_name": None,
                    "device_fingerprint_hash": NEW,
                    "lifetime_comparisons_used": 0,
                }
            ],
            "referral_invites": [
                {
                    "referrer_user_id": REF_UID,
                    "device_fingerprint_hash": NEW,
                    "created_at": "2026-10-01T00:00:00+00:00",
                }
            ],
        }
    )
    with patch.object(rs, "get_admin_supabase_client", return_value=db), patch.object(
        ads, "get_admin_supabase_client", return_value=db
    ):
        invitee = _run(rs.ReferralService()._load_invitee(INV_UID))
        verdict = ads.AbuseDetectionService().evaluate_invite(
            {"referrer_user_id": REF_UID, "invitee_first_comparison_id": None}, invitee
        )
    assert db.calls == [
        ["table", ["users"]],
        ["select", ["id, email, subscription_tier, display_name"]],
        ["eq", ["id", INV_UID]],
        ["single", []],
        ["execute", []],
    ], db.calls
    assert sorted(invitee) == ["display_name", "email", "id", "subscription_tier"]
    assert "referral_invites" not in db.table_names()
    assert verdict.get("flagged_reason") != "SAME_DEVICE", verdict


@pytest.mark.parametrize("value", ["false", "true"])
def test_p12_device_lifetime_cap_untouched(full, value):
    from app.services import referral_service as rs

    _set_flag(full, value)
    db = FakeDB(
        {
            "users": [
                {"id": REF_UID, "device_fingerprint_hash": LEG, "lifetime_invites_consumed": 1},
                {"id": SIB_LEG, "device_fingerprint_hash": LEG, "lifetime_invites_consumed": 2},
                {"id": SIB_NEW, "device_fingerprint_hash": NEW, "lifetime_invites_consumed": 5},
            ]
        }
    )
    with patch.object(rs, "get_admin_supabase_client", return_value=db):
        count = _run(rs.ReferralService()._referrer_device_lifetime_count(REF_UID))
    assert db.calls == [
        ["table", ["users"]],
        ["select", ["device_fingerprint_hash"]],
        ["eq", ["id", REF_UID]],
        ["single", []],
        ["execute", []],
        ["table", ["users"]],
        ["select", ["lifetime_invites_consumed"]],
        ["eq", ["device_fingerprint_hash", LEG]],
        ["execute", []],
    ], db.calls
    assert count == 3


# Spec 1.11 base shas (LF, ast.get_source_segment), grouped by four so no digit run is long.
P13_SHAS = {
    "_read_valid_device_fingerprint": (
        "06a6 5002 9474 75c5 4d5d 0a41 134b 2501 d015 2617 f604 fe95 dfbe aebb db9f 9bec"
    ),
    "_inherit_device_counter": (
        "11c4 de26 aaed 05f3 9e26 c220 3f42 67f5 4126 887a 00f3 2c64 064c 2cf6 6612 da04"
    ),
}


@pytest.mark.parametrize("name", sorted(P13_SHAS))
def test_p13_base_functions_byte_identical(name):
    text = AUTH_ROUTES_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    nodes = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    ]
    assert len(nodes) == 1, name
    segment = ast.get_source_segment(text, nodes[0])
    got = hashlib.sha256(segment.encode("utf-8")).hexdigest()
    assert got == "".join(P13_SHAS[name].split()), (name, got)


def _py_texts(*roots):
    for root in roots:
        if root.is_dir():
            for path in sorted(root.rglob("*.py")):
                yield path.relative_to(ROOT).as_posix(), path.read_text(
                    encoding="utf-8", errors="replace"
                )


def test_p14_leaf_import_shape():
    from app.utils import request_context as leaf

    tree = ast.parse(AUTH_ROUTES_PATH.read_text(encoding="utf-8"))
    imported = [
        (a.name, a.asname)
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == "app.utils.request_context"
        for a in n.names
    ]
    assert imported == [("DEVICE_FINGERPRINT_RE", "_DEVICE_FINGERPRINT_RE")], imported
    plain = [
        a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.Import)
        for a in n.names
        if a.name.startswith("app.utils.request_context")
    ]
    assert plain == []
    assigned = set()
    for n in ast.walk(tree):
        targets = []
        if isinstance(n, ast.Assign):
            targets = n.targets
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            targets = [n.target]
        for t in targets:
            for sub in ast.walk(t):
                if isinstance(sub, ast.Name):
                    assigned.add(sub.id)
    assert "_DEVICE_FINGERPRINT_RE" not in assigned, "r08: never reassigned"
    assert auth_routes._DEVICE_FINGERPRINT_RE is leaf.DEVICE_FINGERPRINT_RE
    assert leaf.DEVICE_FINGERPRINT_RE.pattern == "^[a-f0-9]{64}$"


def test_p14_names_rule():
    auth = AUTH_ROUTES_PATH.read_text(encoding="utf-8")
    assert auth.count('request.headers.get("X-Device-Fingerprint")') == 1, "p07"
    low = auth.lower()
    for needle in ("device_key_pepper", "x-ai-consent-version", "x-compare-request-id", "header_state"):
        assert needle not in low, ("p01 needle in auth_routes", needle)
    banned = ("legacy" + "_hash", "device" + "_lookup_keys")
    for rel, text in _py_texts(APP_DIR, SCRIPTS_DIR):
        for name in banned:
            assert name not in text, ("p08 name", rel, name)
