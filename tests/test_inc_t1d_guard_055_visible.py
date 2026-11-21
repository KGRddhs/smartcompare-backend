"""INC-T1d GUARD-055-VISIBLE: frozen RED rows (spec INC_T1D_UNIT_SPEC.md, gate GATE_INC_T1D.md).

Migration 055 (INC-SEC-1) refuses a change to the six users profile columns that does
not come from the server role with the same SQLSTATE 42501 as migration 054 and its own
fixed message "users profile columns are server-managed (INC-SEC-1)". INC-T1c matches
only the 054 text, so a 055 refusal stays silent. INC-T1d makes it visible and tells it
apart, in the stdlib leaf ``app.utils.db_guard``:

* ``is_guard_refusal`` accepts exactly the two fixed texts (``GUARD_MESSAGES``);
* a 055 refusal logs ONE fixed ERROR line ``DB_GUARD_REFUSED site=<site> guard=055``
  (the module constant tail, never built from an argument); a 054 refusal keeps
  ``DB_GUARD_REFUSED site=<site>`` byte-identical (TD-1);
* ``count_055`` joins the /health ``db_guard_refusals`` object only once a 055 refusal
  was recorded; ``count`` stays the total (TD-2);
* the seventh 055 writer, structured_comparison_service._update_behavior_profile (the
  behavior_profile column), gains the INC-T1c call in its except arm (TD-8).

Row classes: RED rows fail at base on an AssertionError only (the leaf's new surface is
read through find_spec / getattr / .get). PIN rows are green at base: the arm outcomes
under a 055 refusal (measured at base aa35e959), and the B1 no-count rows, run with a
recorder on db_guard.note_refusal (the unit has no flag, knob or credential, so the full
configuration is the leaf as built plus that recorder). Self-contained: copies of the
INC-T1c fake client, drivers and expectation helpers; no import of the INC-T1c test
module. No database, no network: every client is the in-file fake below.
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import logging
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from postgrest.exceptions import APIError

ROOT = Path(__file__).resolve().parents[1]
HELPER = "app.utils.db_guard"
GUARD_MESSAGE = "users entitlement columns are server-managed (INC-T1b)"
GUARD_MESSAGE_055 = "users profile columns are server-managed (INC-SEC-1)"
PRIVILEGE_MESSAGE = "permission denied for table users"
LINE_PREFIX = "DB_GUARD_REFUSED site="
TAIL_055 = " guard=055"

# The seven 055 writers (spec section 1 census + TD-8): site name -> its except arm.
SITES = {
    "auth_service.register_user": ("app/services/auth_service.py", "register_user"),
    "auth_service.social_login": ("app/services/auth_service.py", "sign_in_with_social"),
    "database_service.create_user": ("app/services/database_service.py", "create_user"),
    "database_service.delete_user_cascade": ("app/services/database_service.py", "delete_user_data_cascade"),
    "database_service.save_demographics": ("app/services/database_service.py", "save_user_demographics"),
    "database_service.save_attribution": ("app/services/database_service.py", "save_user_attribution"),
    "structured_comparison_service.behavior_profile": ("app/services/structured_comparison_service.py",
                                                       "_update_behavior_profile"),
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _helper():
    if importlib.util.find_spec(HELPER) is None:
        return None
    return importlib.import_module(HELPER)


def _attr(name):
    return getattr(_helper(), name, None)


def _count() -> int:
    fn = _attr("refusal_count")
    return fn() if callable(fn) else -1


def _inner() -> dict:
    """The inner db_guard_refusals object of guard_snapshot(); {} when absent."""
    fn = _attr("guard_snapshot")
    snap = fn() if callable(fn) else None
    inner = snap.get("db_guard_refusals") if isinstance(snap, dict) else None
    return inner if isinstance(inner, dict) else {}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@pytest.fixture(autouse=True)
def _reset_db_guard_state():
    """GC-7 (the #417 lesson): the leaf counts refusals in process-global state, so every
    test here starts and ends at zero through the leaf's test seam _reset_guard_state();
    no refusal this file records reaches a later file's /health body. Read through
    find_spec / getattr: a no-op while the seam is absent, never an import error."""
    def _reset():
        fn = _attr("_reset_guard_state")
        if callable(fn):
            fn()
    _reset()
    yield
    _reset()


def _sentinel() -> str:
    return "sentinel-" + uuid.uuid4().hex


def _uid() -> str:
    return str(uuid.uuid4())


def _err(kind: str, sentinel: str) -> APIError:
    details = "Failing row contains (" + sentinel + ")"
    if kind == "g055":
        return APIError({"code": "42501", "message": GUARD_MESSAGE_055, "details": details, "hint": None})
    if kind == "g054":
        return APIError({"code": "42501", "message": GUARD_MESSAGE, "details": details, "hint": None})
    if kind == "privilege":
        return APIError({"code": "42501", "message": PRIVILEGE_MESSAGE, "details": details, "hint": None})
    if kind == "in_details":
        return APIError({"code": "42501", "message": PRIVILEGE_MESSAGE,
                         "details": details + " " + GUARD_MESSAGE_055, "hint": None})
    if kind == "timeout_055":
        return APIError({"code": "57014", "message": GUARD_MESSAGE_055, "details": details, "hint": None})
    raise AssertionError(kind)


_WRITE_OPS = ("update", "insert", "upsert", "delete")


class _Chain:
    """A PostgREST builder chain: every step returns self; execute() answers."""

    def __init__(self, client, table=None, rpc=None):
        self._client = client
        self._table = table
        self._rpc = rpc
        self._ops = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _step(*_a, **_k):
            self._ops.append(name)
            return self
        return _step

    def execute(self):
        c = self._client
        is_write = (self._table == "users" and any(o in _WRITE_OPS for o in self._ops)) or (
            self._rpc is not None and self._rpc in c.refuse_rpcs)
        if is_write:
            c.writes.append(self._table or self._rpc)
            if c.exc is not None:
                raise c.exc
            return SimpleNamespace(data=[{}], count=0)
        data = c.reads.get(self._table)
        if data is None:
            data = {} if "single" in self._ops else []
        return SimpleNamespace(data=data, count=0)


class _FakeClient:
    def __init__(self, exc, refuse_rpcs=(), reads=None):
        self.exc = exc
        self.refuse_rpcs = tuple(refuse_rpcs)
        self.reads = dict(reads or {})
        self.writes = []

    def table(self, name):
        return _Chain(self, table=name)

    def rpc(self, name, _params=None):
        return _Chain(self, rpc=name)


def _outcome(fn):
    try:
        return ("return", fn())
    except Exception as exc:  # noqa: BLE001
        return ("raise", exc)


def _run(coro):
    return asyncio.run(coro)


def _guard_lines(records):
    return [r for r in records if r.getMessage().startswith("DB_GUARD_REFUSED")]


def _record_note_refusal(monkeypatch):
    """B1 recorder: every call that reaches db_guard.note_refusal, forwarded unchanged."""
    calls = []
    mod = _helper()
    original = getattr(mod, "note_refusal", None)
    if callable(original):
        def _recorder(*args, **kwargs):
            calls.append((args, kwargs))
            return original(*args, **kwargs)
        monkeypatch.setattr(mod, "note_refusal", _recorder)
    return calls


# ---------------------------------------------------------------------------
# drivers: (monkeypatch, fake client, user id) -> outcome
# ---------------------------------------------------------------------------

def _app():
    from app.main import app
    return app


def _auth_client(uid):
    user = SimpleNamespace(id=uid, email="t1d@example.com")
    resp = SimpleNamespace(user=user, session=None)
    return SimpleNamespace(auth=SimpleNamespace(sign_up=lambda _c: resp,
                                                sign_in_with_id_token=lambda _c: resp))


def _d_register_user(mp, fake, uid):
    import app.services.auth_service as svc
    mp.setattr(svc, "get_auth_client", lambda: _auth_client(uid))
    mp.setattr(svc, "get_admin_client", lambda: fake)
    return _outcome(lambda: _run(svc.register_user("t1d@example.com", "Abcdefgh12")))


def _d_social_login(mp, fake, uid):
    import app.services.auth_service as svc
    mp.delenv("ENABLE_CONSENT_REQUIRED", raising=False)
    mp.setattr(svc, "get_auth_client", lambda: _auth_client(uid))
    mp.setattr(svc, "get_admin_client", lambda: fake)
    return _outcome(lambda: _run(svc.sign_in_with_social("apple", "h.p.s")))


def _ds(mp, fake):
    import app.services.database_service as ds
    mp.setattr(ds, "get_supabase_client", lambda: fake)
    mp.setattr(ds, "get_admin_supabase_client", lambda: fake)
    return ds


def _d_create_user(mp, fake, uid):
    ds = _ds(mp, fake)
    return _outcome(lambda: _run(ds.create_user("t1d@example.com")))


def _d_delete_user_cascade(mp, fake, uid):
    ds = _ds(mp, fake)
    fake.refuse_rpcs = ("delete_user_cascade",)
    return _outcome(lambda: _run(ds.delete_user_data_cascade(uid)))


def _d_save_demographics(mp, fake, uid):
    ds = _ds(mp, fake)
    return _outcome(lambda: _run(ds.save_user_demographics(uid, {"age_band": "25-34"})))


def _d_save_attribution(mp, fake, uid):
    ds = _ds(mp, fake)
    return _outcome(lambda: _run(ds.save_user_attribution(uid, "instagram")))


def _d_behavior_profile(mp, fake, uid):
    """TD-9: fakes for get_supabase_client, run_db and behavior_service.build_behavior_profile;
    the three reads answer empty and the users update raises the fake APIError."""
    import app.services.behavior_service as bs
    import app.services.structured_comparison_service as scs
    mp.delenv("ENABLE_BEHAVIOR_PROFILE_REBUILD", raising=False)
    _ds(mp, fake)

    async def _inline_run_db(call):
        return call()

    mp.setattr(scs, "run_db", _inline_run_db)
    profile = {"category_affinity": {"fragrances": 1.0}}
    mp.setattr(bs, "get_behavior_service",
               lambda: SimpleNamespace(build_behavior_profile=AsyncMock(return_value=profile)))
    return _outcome(lambda: _run(scs.StructuredComparisonService._update_behavior_profile(None, uid)))


DRIVERS = {
    "auth_service.register_user": _d_register_user,
    "auth_service.social_login": _d_social_login,
    "database_service.create_user": _d_create_user,
    "database_service.delete_user_cascade": _d_delete_user_cascade,
    "database_service.save_demographics": _d_save_demographics,
    "database_service.save_attribution": _d_save_attribution,
    "structured_comparison_service.behavior_profile": _d_behavior_profile,
}


_GENERIC = {"success": False, "error": "Something went wrong. Please try again later."}


def _same_raise(outcome, exc):
    return outcome[0] == "raise" and outcome[1] is exc


def _social_diag(outcome, exc):
    expected = {"success": False,
                "error": f"[B4-BE-DIAG] supabase_error={str(exc)[:300]} exc_type={type(exc).__name__}"}
    return outcome == ("return", expected)


def _returns(value):
    return lambda outcome, _exc: outcome == ("return", value)


# site -> (outcome check under the 055 refusal, (level, prefix) of the arm's own line), at base
EXPECTED = {
    "auth_service.register_user": (_returns(_GENERIC), (logging.ERROR, "Auth error in register: APIError")),
    "auth_service.social_login": (_social_diag, (logging.ERROR, "Auth error in social_login: APIError")),
    "database_service.create_user": (_returns(None), (logging.ERROR, "Error creating user: ")),
    "database_service.delete_user_cascade": (_same_raise, (logging.ERROR, "Error in cascade delete for user ")),
    "database_service.save_demographics": (_returns({"success": False, "error": "Failed to save demographics"}),
                                           (logging.ERROR, "[DB] save_user_demographics failed for user ")),
    "database_service.save_attribution": (_returns({"success": False, "error": "Failed to save attribution"}),
                                          (logging.ERROR, "[DB] save_user_attribution failed for user ")),
    "structured_comparison_service.behavior_profile": (_returns(None),
                                                       (logging.WARNING, "Failed to update behavior profile: ")),
}


def _drive(site, kind, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    sentinel = _sentinel()
    exc = None if kind == "success" else _err(kind, sentinel)
    fake = _FakeClient(exc)
    uid = _uid()
    calls = _record_note_refusal(monkeypatch)
    before = _count()
    outcome = DRIVERS[site](monkeypatch, fake, uid)
    after = _count()
    return SimpleNamespace(outcome=outcome, exc=exc, fake=fake, uid=uid, sentinel=sentinel, calls=calls,
                           delta=after - before, inner=_inner(), records=list(caplog.records))


# ---------------------------------------------------------------------------
# G-rows: the leaf
# ---------------------------------------------------------------------------

def test_g00_the_two_migration_texts_share_the_sqlstate_and_differ():
    """PIN: migration 055 raises its fixed text twice and 054 its own twice, each with
    ERRCODE 42501; the two texts differ."""
    sql055 = (ROOT / "migrations/055_app_user_access_tightening.sql").read_text(encoding="utf-8")
    sql054 = (ROOT / "migrations/054_users_entitlement_guard.sql").read_text(encoding="utf-8")
    assert sql055.count("MESSAGE = '" + GUARD_MESSAGE_055 + "'") == 2
    assert sql054.count("MESSAGE = '" + GUARD_MESSAGE + "'") == 2
    assert sql055.count("ERRCODE = '42501'") == 2 and sql054.count("ERRCODE = '42501'") == 2
    assert GUARD_MESSAGE_055 != GUARD_MESSAGE
    assert GUARD_MESSAGE not in GUARD_MESSAGE_055 and GUARD_MESSAGE_055 not in GUARD_MESSAGE


def test_g01_the_two_texts_are_leaf_constants_and_the_old_ones_stay():
    """RED: GUARD_MESSAGE_055 is the 055 text, GUARD_MESSAGES is exactly the tuple
    (054 text, 055 text), GUARD_055_TAIL is the fixed tail; the INC-T1c constants stay."""
    mod = _helper()
    assert mod is not None, HELPER + " is missing"
    assert getattr(mod, "GUARD_MESSAGE_055", None) == GUARD_MESSAGE_055
    messages = getattr(mod, "GUARD_MESSAGES", None)
    assert isinstance(messages, tuple) and len(messages) == 2, messages
    assert messages == (GUARD_MESSAGE, GUARD_MESSAGE_055), messages
    assert getattr(mod, "GUARD_055_TAIL", None) == TAIL_055
    assert getattr(mod, "GUARD_SQLSTATE", None) == "42501"
    assert getattr(mod, "GUARD_MESSAGE", None) == GUARD_MESSAGE
    assert getattr(mod, "LINE_PREFIX", None) == LINE_PREFIX


def test_g02_is_guard_refusal_accepts_exactly_the_two_texts():
    """RED: a 42501 carrying the 055 text or the 054 text is a refusal; the privilege
    text, the 055 text only in details, another SQLSTATE with the 055 text, a plain
    exception carrying the text, None and a hostile object are not; nothing raises."""
    fn = _attr("is_guard_refusal")
    assert callable(fn), "is_guard_refusal missing"
    s = _sentinel()
    assert fn(_err("g055", s)) is True
    assert fn(_err("g054", s)) is True
    assert fn(_err("privilege", s)) is False
    assert fn(_err("in_details", s)) is False
    assert fn(_err("timeout_055", s)) is False
    assert fn(Exception(GUARD_MESSAGE_055)) is False
    assert fn(None) is False

    class _Hostile(Exception):
        def __getattribute__(self, name):
            raise RuntimeError("no attributes")
    assert fn(_Hostile()) is False


def test_g03_a_055_refusal_logs_its_own_line_once(caplog):
    """RED: note_if_guard_refusal(<055 refusal>, site) is True and logs ONE ERROR line
    DB_GUARD_REFUSED site=<site> guard=055 (no args, no exc_info); the total moves by one."""
    fn = _attr("note_if_guard_refusal")
    assert callable(fn), "note_if_guard_refusal missing"
    caplog.set_level(logging.DEBUG)
    before = _count()
    assert fn(_err("g055", _sentinel()), "probe.p055") is True
    recs = _guard_lines(caplog.records)
    assert [r.getMessage() for r in recs] == [LINE_PREFIX + "probe.p055" + TAIL_055], \
        [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.ERROR and recs[0].exc_info is None and not recs[0].args
    assert _count() == before + 1


def test_g04_count_055_joins_the_snapshot_only_once_one_was_recorded():
    """RED: one 055 refusal -> {count 1, last_at <str>, count_055 1}; a 054 then a 055 ->
    count 2, count_055 1; reset, a 055, reset, a 054 -> count 1 and no count_055 key."""
    note = _attr("note_if_guard_refusal")
    reset = _attr("_reset_guard_state")
    assert callable(note) and callable(reset), "leaf surface missing"
    s = _sentinel()
    reset()
    assert note(_err("g055", s), "probe.g04") is True
    inner = _inner()
    assert sorted(inner) == ["count", "count_055", "last_at"], inner
    assert _is_int(inner["count"]) and inner["count"] == 1, inner
    assert _is_int(inner["count_055"]) and inner["count_055"] == 1, inner
    assert isinstance(inner["last_at"], str), inner
    datetime.fromisoformat(inner["last_at"])
    reset()
    assert note(_err("g054", s), "probe.g04") is True
    assert note(_err("g055", s), "probe.g04") is True
    inner = _inner()
    assert inner.get("count") == 2 and inner.get("count_055") == 1, inner
    reset()
    assert note(_err("g055", s), "probe.g04") is True
    reset()
    assert note(_err("g054", s), "probe.g04") is True
    inner = _inner()
    assert sorted(inner) == ["count", "last_at"] and inner.get("count") == 1, inner


def test_g05_health_carries_count_055_after_a_055_refusal():
    """RED: GET /health has no db_guard_refusals key at zero; after one 055 refusal the
    body carries exactly {count: 1, count_055: 1, last_at: <str>}; status and message
    keep their values."""
    from fastapi.testclient import TestClient
    client = TestClient(_app())
    body = client.get("/health").json()
    assert body.get("status") == "healthy" and body.get("message") == "MYEZ API is running"
    assert "db_guard_refusals" not in body, body.get("db_guard_refusals")
    fn = _attr("note_if_guard_refusal")
    assert callable(fn), "note_if_guard_refusal missing"
    fn(_err("g055", _sentinel()), "probe.health055")
    body2 = client.get("/health").json()
    assert body2.get("status") == "healthy" and body2.get("message") == "MYEZ API is running"
    snap = body2.get("db_guard_refusals")
    assert isinstance(snap, dict), sorted(body2)
    assert sorted(snap) == ["count", "count_055", "last_at"], snap
    assert _is_int(snap["count"]) and snap["count"] == 1, snap
    assert _is_int(snap["count_055"]) and snap["count_055"] == 1, snap
    assert isinstance(snap["last_at"], str), snap
    datetime.fromisoformat(snap["last_at"])


def test_g06_note_refusal_takes_a_guard_and_the_tail_is_a_constant(caplog):
    """RED: note_refusal has a guard parameter defaulting to "054" (read before any call);
    guard "055" adds the fixed tail and counts one 055; any other value ("054", "055 "+id,
    55, None, "055"+newline) logs exactly the 054 line and leaves count_055 alone."""
    fn = _attr("note_refusal")
    assert callable(fn), "note_refusal missing"
    params = inspect.signature(fn).parameters
    guard = params.get("guard")
    assert guard is not None and guard.default == "054", list(params)
    caplog.set_level(logging.DEBUG)
    fn("probe.g", "055")
    assert [r.getMessage() for r in _guard_lines(caplog.records)] == [LINE_PREFIX + "probe.g" + TAIL_055]
    assert _inner().get("count_055") == 1, _inner()
    caplog.clear()
    uid = _uid()
    others = ("054", "055 " + uid, 55, None, "055" + chr(10))
    for value in others:
        fn("probe.g", value)
    msgs = [r.getMessage() for r in _guard_lines(caplog.records)]
    assert msgs == [LINE_PREFIX + "probe.g"] * len(others), msgs
    inner = _inner()
    assert inner.get("count_055") == 1 and inner.get("count") == 1 + len(others), inner


# ---------------------------------------------------------------------------
# E-rows: per 055 writer, the refusal is visible once (RED) and the arm is unchanged (PIN)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("site", sorted(SITES))
def test_e01_a_055_refusal_logs_the_tailed_line_once_and_counts(site, monkeypatch, caplog):
    """RED: exactly one ERROR DB_GUARD_REFUSED site=<site> guard=055; the total moves by
    one and count_055 is 1."""
    run = _drive(site, "g055", monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    recs = _guard_lines(run.records)
    assert [r.getMessage() for r in recs] == [LINE_PREFIX + site + TAIL_055], [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.ERROR
    assert run.delta == 1, run.delta
    assert run.inner.get("count_055") == 1, run.inner


@pytest.mark.parametrize("site", sorted(SITES))
def test_e02_the_055_line_carries_no_id_and_no_exception_text(site, monkeypatch, caplog):
    """RED: the line holds no user id, no row data, no 055 text, no migration id, no
    SQLSTATE, no exception type; no record args, no traceback."""
    run = _drive(site, "g055", monkeypatch, caplog)
    recs = _guard_lines(run.records)
    assert len(recs) == 1, [r.getMessage() for r in recs]
    msg = recs[0].getMessage()
    for needle in (run.uid, run.sentinel, GUARD_MESSAGE_055, "INC-SEC-1", "42501", "APIError"):
        assert needle not in msg, needle
    assert recs[0].exc_info is None and not recs[0].args


@pytest.mark.parametrize("site", sorted(SITES))
def test_e03_under_a_055_refusal_the_arm_keeps_its_outcome_and_its_own_line(site, monkeypatch, caplog):
    """PIN (green at base): under the 055 refusal the arm returns / raises as measured at
    base and logs its own line once, at its own level."""
    run = _drive(site, "g055", monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    check, (level, prefix) = EXPECTED[site]
    assert check(run.outcome, run.exc), run.outcome
    hits = [r for r in run.records if r.getMessage().startswith(prefix)]
    assert len(hits) == 1, [r.getMessage() for r in run.records]
    assert hits[0].levelno == level


# ---------------------------------------------------------------------------
# B-rows: B1 pins with the recorder on db_guard.note_refusal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["privilege", "in_details", "success"])
@pytest.mark.parametrize("site", sorted(SITES))
def test_b01_no_note_no_line_and_no_count_without_a_guard_text(site, kind, monkeypatch, caplog):
    """PIN B1: the privilege text, the 055 text only in details and a successful write
    reach no note_refusal (the recorder stays empty), log no DB_GUARD_REFUSED line and
    leave the counters alone."""
    run = _drive(site, kind, monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    assert run.calls == [], run.calls
    assert _guard_lines(run.records) == []
    assert run.delta == 0, run.delta
    assert "count_055" not in run.inner, run.inner


@pytest.mark.parametrize("site", sorted(SITES))
def test_b02_a_054_refusal_keeps_its_line_byte_identical(site, monkeypatch, caplog):
    """PIN B1 (the 054 path, TD-1): a 054 refusal reaches note_refusal once and logs
    exactly DB_GUARD_REFUSED site=<site> (no guard field), ERROR, no args, no exc_info;
    the total moves by one and no count_055 key appears."""
    run = _drive(site, "g054", monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    recs = _guard_lines(run.records)
    assert [r.getMessage() for r in recs] == [LINE_PREFIX + site], [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.ERROR and recs[0].exc_info is None and not recs[0].args
    assert len(run.calls) == 1, run.calls
    assert run.delta == 1, run.delta
    assert "count_055" not in run.inner, run.inner
