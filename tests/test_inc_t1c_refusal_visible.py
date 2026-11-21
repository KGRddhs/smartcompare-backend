"""INC-T1c REFUSAL-VISIBLE: frozen RED rows (spec INC_T1C_UNIT_SPEC.md).

Migration 054 makes the database refuse a change to the eleven users entitlement
columns that does not come from the server role: SQLSTATE 42501, the fixed message
"users entitlement columns are server-managed (INC-T1b)". The server writes as the
service role and should never be refused; if a missed path is, the except arm of
that writer must make it VISIBLE and COUNTABLE:

* ONE fixed ERROR line ``DB_GUARD_REFUSED site=<name>`` (no id, no row data, no
  exception text), from the stdlib leaf ``app.utils.db_guard``;
* a per-process counter, exposed on ``/health`` as ``db_guard_refusals``;
* the arm keeps its return value / raise and its own existing log line.

Row classes: RED rows fail at base on an AssertionError only (the helper is read
through find_spec / getattr). PIN rows are green at base (the arm behaviour under a
refusal, measured at base afde168f). NEG rows (a non-42501 error, a 42501 without
the guard message, a successful write) are green at base and kill an over-matching
build. No database, no network: every client is the in-file fake below.
"""
from __future__ import annotations

import ast
import asyncio
import importlib
import importlib.util
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from postgrest.exceptions import APIError

ROOT = Path(__file__).resolve().parents[1]
HELPER = "app.utils.db_guard"
GUARD_MESSAGE = "users entitlement columns are server-managed (INC-T1b)"
LINE_PREFIX = "DB_GUARD_REFUSED site="
FP_PRIMARY = "a" * 64
FP_LEGACY = "b" * 64

# site name -> the except arm it names (file, function)
SITES = {
    "auth_routes.register_device_fp": ("app/api/auth_routes.py", "register"),
    "auth_routes.legacy_device_fp": ("app/api/auth_routes.py", "_inherit_device_counter_with_legacy"),
    "auth_routes.social_device_fp": ("app/api/auth_routes.py", "_apply_social_device_fingerprint"),
    "auth_routes.push_token": ("app/api/auth_routes.py", "update_push_token"),
    "auth_routes.reengagement_subs": ("app/api/auth_routes.py", "update_reengagement_subs"),
    "auth_routes.preference_toggles": ("app/api/auth_routes.py", "update_preference_toggles"),
    "auth_service.register_user": ("app/services/auth_service.py", "register_user"),
    "auth_service.social_login": ("app/services/auth_service.py", "sign_in_with_social"),
    "auth_service.update_profile": ("app/services/auth_service.py", "update_user_profile"),
    "auth_service.save_preferences": ("app/services/auth_service.py", "save_user_preferences"),
    "database_service.create_user": ("app/services/database_service.py", "create_user"),
    "database_service.update_subscription": ("app/services/database_service.py", "update_user_subscription"),
    "database_service.delete_user_cascade": ("app/services/database_service.py", "delete_user_data_cascade"),
    "database_service.save_demographics": ("app/services/database_service.py", "save_user_demographics"),
    "database_service.save_attribution": ("app/services/database_service.py", "save_user_attribution"),
    "referral_service.ensure_code": ("app/services/referral_service.py", "ensure_code_for_user"),
    "referral_service.status_code": ("app/services/referral_service.py", "get_status"),
    "referral_service.loop2_rewards": ("app/services/referral_service.py", "try_trigger_loop2"),
    "usage_service.bonus_reset": ("app/services/usage_service.py", "_maybe_reset_referral_bonus"),
    "usage_service.lifetime_increment": ("app/services/usage_service.py", "record_lifetime_comparison"),
    "usage_service.comparison_increment": ("app/services/usage_service.py", "record_comparison"),
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


def _count() -> int:
    fn = getattr(_helper(), "refusal_count", None)
    return fn() if callable(fn) else -1


@pytest.fixture(autouse=True)
def _reset_db_guard_state():
    """GC-7 (the #417 lesson): the leaf counts refusals in process-global state, so every
    test here starts and ends at zero through the leaf's test seam _reset_guard_state()
    (the llm_credential_health._reset_credential_health_state pattern): no refusal this
    file records reaches a later file's /health body. A no-op while the leaf or the seam
    is absent (base): read through find_spec / getattr, never an import error."""
    def _reset():
        fn = getattr(_helper(), "_reset_guard_state", None)
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
    if kind == "guard":
        return APIError({"code": "42501", "message": GUARD_MESSAGE, "details": details, "hint": None})
    if kind == "other_code":
        return APIError({"code": "57014", "message": "canceling statement due to statement timeout",
                         "details": details, "hint": None})
    if kind == "other_message":
        return APIError({"code": "42501", "message": "permission denied for table users",
                         "details": details, "hint": None})
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


def _guard_records(caplog):
    return [r for r in caplog.records if r.getMessage().startswith("DB_GUARD_REFUSED")]


# ---------------------------------------------------------------------------
# drivers: (monkeypatch, fake client, user id) -> outcome
# ---------------------------------------------------------------------------

def _app():
    from app.main import app
    return app


def _route_call(mp, fake, uid, method, path, body):
    from fastapi.testclient import TestClient
    import app.api.auth_routes as ar
    app = _app()

    async def _user():
        return {"id": uid, "email": "t1c@example.com", "access_token": "t1c-" + uuid.uuid4().hex}

    mp.setattr(ar, "get_user_supabase_client", lambda _token: fake)
    mp.setattr(ar, "get_admin_supabase_client", lambda: fake)
    app.dependency_overrides[ar.get_current_user] = _user
    try:
        resp = getattr(TestClient(app), method)(path, json=body, headers={"Authorization": "Bearer t1c"})
    finally:
        app.dependency_overrides.pop(ar.get_current_user, None)
    return ("return", (resp.status_code, resp.json()))


def _d_register_device_fp(mp, fake, uid):
    from fastapi.testclient import TestClient
    import app.api.auth_routes as ar
    mp.delenv("ENABLE_LEGACY_FINGERPRINT_READER", raising=False)
    result = {"success": True, "user": {"id": uid, "email": "t1c@example.com"},
              "session": {"access_token": None, "refresh_token": None, "expires_at": None},
              "message": "Registration successful"}
    mp.setattr(ar, "register_user", AsyncMock(return_value=result))
    mp.setattr(ar, "get_admin_supabase_client", lambda: fake)
    resp = TestClient(_app()).post(
        "/api/v1/auth/register",
        json={"email": "t1c-" + uuid.uuid4().hex[:8] + "@example.com", "password": "Abcdefgh12"},
        headers={"X-Device-Fingerprint": FP_PRIMARY},
    )
    return ("return", (resp.status_code, resp.json().get("success")))


def _d_legacy_device_fp(mp, fake, uid):
    import app.api.auth_routes as ar
    return _outcome(lambda: ar._inherit_device_counter_with_legacy(
        fake, FP_PRIMARY, FP_LEGACY, uid, floor=0, site="register"))


def _d_social_device_fp(mp, fake, uid):
    import app.api.auth_routes as ar
    mp.delenv("ENABLE_LEGACY_FINGERPRINT_READER", raising=False)
    mp.setattr(ar, "get_admin_supabase_client", lambda: fake)
    req = SimpleNamespace(headers={"X-Device-Fingerprint": FP_PRIMARY})
    return _outcome(lambda: ar._apply_social_device_fingerprint(req, uid))


def _d_push_token(mp, fake, uid):
    return _route_call(mp, fake, uid, "put", "/api/v1/auth/push-token",
                       {"expo_push_token": "ExponentPushToken[T1C]"})


def _d_reengagement_subs(mp, fake, uid):
    return _route_call(mp, fake, uid, "put", "/api/v1/auth/reengagement-subs",
                       {"decision_insights": True, "peer_decision_updates": False,
                        "decision_retrospectives": True})


def _d_preference_toggles(mp, fake, uid):
    return _route_call(mp, fake, uid, "put", "/api/v1/auth/preference-toggles",
                       {"notifications_enabled": True})


def _auth_client(uid):
    user = SimpleNamespace(id=uid, email="t1c@example.com")
    resp = SimpleNamespace(user=user, session=None)
    return SimpleNamespace(auth=SimpleNamespace(sign_up=lambda _c: resp,
                                                sign_in_with_id_token=lambda _c: resp))


def _d_register_user(mp, fake, uid):
    import app.services.auth_service as svc
    mp.setattr(svc, "get_auth_client", lambda: _auth_client(uid))
    mp.setattr(svc, "get_admin_client", lambda: fake)
    return _outcome(lambda: _run(svc.register_user("t1c@example.com", "Abcdefgh12")))


def _d_social_login(mp, fake, uid):
    import app.services.auth_service as svc
    mp.delenv("ENABLE_CONSENT_REQUIRED", raising=False)
    mp.setattr(svc, "get_auth_client", lambda: _auth_client(uid))
    mp.setattr(svc, "get_admin_client", lambda: fake)
    return _outcome(lambda: _run(svc.sign_in_with_social("apple", "h.p.s")))


def _d_update_profile(mp, fake, uid):
    import app.services.auth_service as svc
    mp.setattr(svc, "get_admin_client", lambda: fake)
    return _outcome(lambda: _run(svc.update_user_profile(uid, "T1C")))


def _d_save_preferences(mp, fake, uid):
    import app.services.auth_service as svc
    mp.setattr(svc, "get_admin_client", lambda: fake)
    mp.setattr(svc, "fire_and_forget", lambda coro, _label=None: coro.close())
    return _outcome(lambda: _run(svc.save_user_preferences(uid, {"priorities": ["price"]})))


def _ds(mp, fake):
    import app.services.database_service as ds
    mp.setattr(ds, "get_supabase_client", lambda: fake)
    mp.setattr(ds, "get_admin_supabase_client", lambda: fake)
    return ds


def _d_create_user(mp, fake, uid):
    ds = _ds(mp, fake)
    return _outcome(lambda: _run(ds.create_user("t1c@example.com")))


def _d_update_subscription(mp, fake, uid):
    ds = _ds(mp, fake)
    return _outcome(lambda: _run(ds.update_user_subscription(uid, "premium")))


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


def _referral(mp, fake):
    import app.services.referral_service as rs
    mp.setattr(rs, "get_admin_supabase_client", lambda: fake)
    return rs, rs.ReferralService()


def _d_ensure_code(mp, fake, uid):
    _rs, svc = _referral(mp, fake)
    return _outcome(lambda: _run(svc.ensure_code_for_user(uid)))


def _d_status_code(mp, fake, uid):
    _rs, svc = _referral(mp, fake)
    return _outcome(lambda: _run(svc.get_status(uid)))


def _d_loop2_rewards(mp, fake, uid):
    rs, svc = _referral(mp, fake)
    mp.delenv("ENABLE_DEVICE_DAILY_QUOTA", raising=False)
    invite = {"id": "inv-" + uuid.uuid4().hex, "referrer_user_id": _uid(), "redeemed_at": None}
    mp.setattr(svc, "_find_unredeemed_invite_for_invitee", AsyncMock(return_value=invite))
    mp.setattr(svc, "_count_user_comparisons", AsyncMock(return_value=1))
    mp.setattr(svc, "_load_invitee", AsyncMock(return_value={"id": uid, "email": ""}))
    mp.setattr(svc, "_referrer_device_lifetime_count", AsyncMock(return_value=0))
    mp.setattr(svc, "_get_referrer_subscription_tier", AsyncMock(return_value="free"))
    mp.setattr(svc, "_update_invite_as_redeemed", AsyncMock(return_value=None))
    mp.setattr(svc, "_send_loop2_push", AsyncMock(return_value=None))
    mp.setattr(rs, "AbuseDetectionService",
               lambda: SimpleNamespace(evaluate_invite=lambda _i, _u: {"passed": True}))
    return _outcome(lambda: _run(svc.try_trigger_loop2(uid, "cmp-" + uuid.uuid4().hex)))


def _d_bonus_reset(mp, fake, uid):
    import app.services.usage_service as us
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return _outcome(lambda: us._maybe_reset_referral_bonus(fake, uid, {"referral_bonus_reset_at": past}))


def _d_lifetime_increment(mp, fake, uid):
    import app.services.usage_service as us
    fake.refuse_rpcs = ("increment_lifetime_comparisons",)
    mp.setattr(us, "get_admin_supabase_client", lambda: fake)
    return _outcome(lambda: _run(us.record_lifetime_comparison(uid, "t1c")))


def _d_comparison_increment(mp, fake, uid):
    import app.services.usage_service as us
    fake.refuse_rpcs = ("increment_lifetime_comparisons",)
    mp.setattr(us, "get_admin_supabase_client", lambda: fake)
    mp.setattr(us, "redis_client", None)
    return _outcome(lambda: _run(us.record_comparison(uid, "t1c")))


def _d_behavior_profile(mp, fake, uid):
    """INC-T1d TD-9: fakes for get_supabase_client, run_db and
    behavior_service.build_behavior_profile; the users update raises."""
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
    "auth_routes.register_device_fp": _d_register_device_fp,
    "auth_routes.legacy_device_fp": _d_legacy_device_fp,
    "auth_routes.social_device_fp": _d_social_device_fp,
    "auth_routes.push_token": _d_push_token,
    "auth_routes.reengagement_subs": _d_reengagement_subs,
    "auth_routes.preference_toggles": _d_preference_toggles,
    "auth_service.register_user": _d_register_user,
    "auth_service.social_login": _d_social_login,
    "auth_service.update_profile": _d_update_profile,
    "auth_service.save_preferences": _d_save_preferences,
    "database_service.create_user": _d_create_user,
    "database_service.update_subscription": _d_update_subscription,
    "database_service.delete_user_cascade": _d_delete_user_cascade,
    "database_service.save_demographics": _d_save_demographics,
    "database_service.save_attribution": _d_save_attribution,
    "referral_service.ensure_code": _d_ensure_code,
    "referral_service.status_code": _d_status_code,
    "referral_service.loop2_rewards": _d_loop2_rewards,
    "usage_service.bonus_reset": _d_bonus_reset,
    "usage_service.lifetime_increment": _d_lifetime_increment,
    "usage_service.comparison_increment": _d_comparison_increment,
    "structured_comparison_service.behavior_profile": _d_behavior_profile,
}


_GENERIC = {"success": False, "error": "Something went wrong. Please try again later."}


def _same_raise(outcome, exc):
    return outcome[0] == "raise" and outcome[1] is exc


def _bonus_zeroed(outcome, _exc):
    if outcome[0] != "return":
        return False
    data = outcome[1]
    rolled = datetime.fromisoformat(data["referral_bonus_reset_at"])
    return data["referral_bonus_comparisons_this_month"] == 0 and rolled > datetime.now(timezone.utc)


def _social_diag(outcome, exc):
    expected = {"success": False,
                "error": f"[B4-BE-DIAG] supabase_error={str(exc)[:300]} exc_type={type(exc).__name__}"}
    return outcome == ("return", expected)


def _http_500(error_text):
    def _check(outcome, _exc):
        if outcome[0] != "return":
            return False
        status, body = outcome[1]
        if not isinstance(body, dict):
            return False
        # the error middleware envelope measured at base: success / error / code / request_id
        fields = {k: body.get(k) for k in ("success", "error", "code")}
        return (status == 500 and fields == {"success": False, "error": error_text, "code": "INTERNAL_ERROR"}
                and set(body) == {"success", "error", "code", "request_id"})
    return _check


def _returns(value):
    return lambda outcome, _exc: outcome == ("return", value)


# site -> (outcome check under the refusal, (level, prefix) of the arm's own line or None)
EXPECTED = {
    "auth_routes.register_device_fp": (_returns((200, True)),
                                       (logging.WARNING, "device-fp inheritance failed (silent): ")),
    "auth_routes.legacy_device_fp": (_returns(None),
                                     (logging.WARNING, "[LEGACY-FP] site=register inherit failed: APIError")),
    "auth_routes.social_device_fp": (_returns(None),
                                     (logging.WARNING, "device-fp social apply failed (silent): APIError")),
    "auth_routes.push_token": (_http_500("Failed to register push token"),
                               (logging.WARNING, "push token update failed for ")),
    "auth_routes.reengagement_subs": (_http_500("Failed to update notification preferences"),
                                      (logging.WARNING, "[AUTH] reengagement-subs update failed for ")),
    "auth_routes.preference_toggles": (_http_500("Failed to update preferences"),
                                       (logging.WARNING, "[AUTH] preference-toggles update failed for ")),
    "auth_service.register_user": (_returns(_GENERIC), (logging.ERROR, "Auth error in register: APIError")),
    "auth_service.social_login": (_social_diag, (logging.ERROR, "Auth error in social_login: APIError")),
    "auth_service.update_profile": (_returns(_GENERIC), (logging.ERROR, "Auth error in update_profile: APIError")),
    "auth_service.save_preferences": (_returns({"success": False, "error": "Failed to save preferences"}),
                                      (logging.ERROR, "[AUTH] save_user_preferences failed for user ")),
    "database_service.create_user": (_returns(None), (logging.ERROR, "Error creating user: ")),
    "database_service.update_subscription": (_returns(False), (logging.ERROR, "Error updating subscription: ")),
    "database_service.delete_user_cascade": (_same_raise, (logging.ERROR, "Error in cascade delete for user ")),
    "database_service.save_demographics": (_returns({"success": False, "error": "Failed to save demographics"}),
                                           (logging.ERROR, "[DB] save_user_demographics failed for user ")),
    "database_service.save_attribution": (_returns({"success": False, "error": "Failed to save attribution"}),
                                          (logging.ERROR, "[DB] save_user_attribution failed for user ")),
    "referral_service.ensure_code": (_same_raise, None),
    "referral_service.status_code": (_same_raise, None),
    "referral_service.loop2_rewards": (_returns(None), (logging.WARNING, "[referral] try_trigger_loop2(invitee=")),
    "usage_service.bonus_reset": (_bonus_zeroed, (logging.WARNING, "[usage] referral bonus reset failed for ")),
    "usage_service.lifetime_increment": (_returns(None), (logging.ERROR, "Failed to record lifetime comparison for ")),
    "usage_service.comparison_increment": (_returns(None), (logging.ERROR, "Failed to record comparison usage for ")),
    "structured_comparison_service.behavior_profile": (_returns(None),
                                                       (logging.WARNING, "Failed to update behavior profile: ")),
}


def _drive(site, kind, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    sentinel = _sentinel()
    exc = None if kind == "success" else _err(kind, sentinel)
    fake = _FakeClient(exc)
    uid = _uid()
    before = _count()
    outcome = DRIVERS[site](monkeypatch, fake, uid)
    after = _count()
    return SimpleNamespace(outcome=outcome, exc=exc, fake=fake, uid=uid, sentinel=sentinel,
                           delta=after - before, records=list(caplog.records))


# ---------------------------------------------------------------------------
# T-rows: the census
# ---------------------------------------------------------------------------

def test_t00_driver_and_expectation_tables_cover_every_site():
    """PIN: the in-file tables agree (a typo in a site name fails here, not silently)."""
    assert set(DRIVERS) == set(SITES) == set(EXPECTED)
    assert len(SITES) == 22


def _site_calls():
    """Every note_if_guard_refusal(<exc>, "<site>") call in app/: (file, enclosing function, site)."""
    found = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(func):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name != "note_if_guard_refusal":
                    continue
                site = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else None
                found.append((rel, func.name, site))
    return found


def test_t01_every_site_is_called_once_from_its_arm():
    """RED: each site literal appears in exactly one note_if_guard_refusal call, inside the
    function that owns its except arm, and no other site exists in app/."""
    calls = _site_calls()
    sites = [c[2] for c in calls]
    assert sorted(sites) == sorted(SITES), sorted(set(sites) ^ set(SITES))
    for rel, func, site in calls:
        assert SITES[site] == (rel, func), (site, rel, func)


# ---------------------------------------------------------------------------
# H-rows: the helper leaf
# ---------------------------------------------------------------------------

def test_h01_helper_surface_and_the_054_literal():
    """RED: the leaf exists with its surface; its message is the 054 refusal text."""
    mod = _helper()
    assert mod is not None, HELPER + " is missing"
    for name in ("is_guard_refusal", "note_refusal", "note_if_guard_refusal", "refusal_count", "guard_snapshot"):
        assert callable(getattr(mod, name, None)), name
    assert getattr(mod, "GUARD_SQLSTATE", None) == "42501"
    assert getattr(mod, "GUARD_MESSAGE", None) == GUARD_MESSAGE
    sql = (ROOT / "migrations/054_users_entitlement_guard.sql").read_text(encoding="utf-8")
    assert sql.count("MESSAGE = '" + GUARD_MESSAGE + "'") == 2


def test_h02_is_guard_refusal_truth_table():
    """RED: only a 42501 carrying the guard message is a refusal; nothing raises."""
    fn = getattr(_helper(), "is_guard_refusal", None)
    assert callable(fn), "is_guard_refusal missing"
    s = _sentinel()
    assert fn(_err("guard", s)) is True
    assert fn(_err("other_code", s)) is False
    assert fn(_err("other_message", s)) is False
    assert fn(Exception(GUARD_MESSAGE)) is False
    assert fn(None) is False

    class _Hostile(Exception):
        def __getattribute__(self, name):
            raise RuntimeError("no attributes")
    assert fn(_Hostile()) is False


def test_h03_note_refusal_line_counter_and_snapshot(caplog):
    """RED: one fixed ERROR line, no exc_info, the counter and last_at move."""
    mod = _helper()
    assert mod is not None, HELPER + " is missing"
    caplog.set_level(logging.DEBUG)
    before = mod.refusal_count()
    mod.note_refusal("probe.site_1")
    recs = _guard_records(caplog)
    assert [r.getMessage() for r in recs] == [LINE_PREFIX + "probe.site_1"]
    assert recs[0].levelno == logging.ERROR and recs[0].exc_info is None and not recs[0].args
    assert mod.refusal_count() == before + 1
    snap = mod.guard_snapshot()["db_guard_refusals"]
    assert snap["count"] == before + 1
    datetime.fromisoformat(snap["last_at"])


def test_h04_a_site_that_is_not_a_fixed_name_never_reaches_the_line(caplog):
    """RED: a site carrying an id or spaces is logged as site=invalid."""
    mod = _helper()
    assert mod is not None, HELPER + " is missing"
    caplog.set_level(logging.DEBUG)
    uid = _uid()
    mod.note_refusal("users " + uid)
    mod.note_refusal(None)
    msgs = [r.getMessage() for r in _guard_records(caplog)]
    assert msgs == [LINE_PREFIX + "invalid", LINE_PREFIX + "invalid"]


def test_h05_note_if_guard_refusal_returns_and_never_raises(caplog):
    """RED: True and one line for the refusal; False and no line otherwise."""
    fn = getattr(_helper(), "note_if_guard_refusal", None)
    assert callable(fn), "note_if_guard_refusal missing"
    caplog.set_level(logging.DEBUG)
    s = _sentinel()
    assert fn(_err("other_code", s), "probe.neg") is False
    assert fn(_err("other_message", s), "probe.neg") is False
    assert fn(None, "probe.neg") is False
    assert _guard_records(caplog) == []
    assert fn(_err("guard", s), "probe.pos") is True
    assert [r.getMessage() for r in _guard_records(caplog)] == [LINE_PREFIX + "probe.pos"]


def test_h06_helper_is_a_stdlib_leaf():
    """RED: the leaf imports no app module and no third-party package."""
    path = ROOT / "app/utils/db_guard.py"
    assert path.is_file(), "app/utils/db_guard.py missing"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "logging", "re", "threading", "datetime", "typing"}, roots


def test_h07_health_carries_the_counter():
    """RED: the MON1 house shape (GC-1): /health has NO db_guard_refusals key while
    nothing was refused; after one refusal (a fixed site) it carries exactly
    {count: 1, last_at: <str>}; status and message keep their values."""
    from fastapi.testclient import TestClient
    client = TestClient(_app())
    body = client.get("/health").json()
    assert body.get("status") == "healthy" and body.get("message") == "MYEZ API is running"
    assert "db_guard_refusals" not in body, body.get("db_guard_refusals")
    mod = _helper()
    assert mod is not None, HELPER + " is missing"
    mod.note_refusal("probe.health")
    body2 = client.get("/health").json()
    assert body2.get("status") == "healthy" and body2.get("message") == "MYEZ API is running"
    snap = body2.get("db_guard_refusals")
    assert isinstance(snap, dict), sorted(body2)
    assert sorted(snap) == ["count", "last_at"], snap
    count = snap["count"]
    assert isinstance(count, int) and not isinstance(count, bool) and count == 1, snap
    assert isinstance(snap["last_at"], str), snap
    datetime.fromisoformat(snap["last_at"])


# ---------------------------------------------------------------------------
# S-rows: per site, the refusal is visible once (RED) and the arm is unchanged (PIN)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("site", sorted(SITES))
def test_s01_refusal_logs_the_line_once_and_counts(site, monkeypatch, caplog):
    """RED: exactly one ERROR DB_GUARD_REFUSED site=<site>; the counter moves by one."""
    run = _drive(site, "guard", monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    recs = [r for r in run.records if r.getMessage().startswith("DB_GUARD_REFUSED")]
    assert [r.getMessage() for r in recs] == [LINE_PREFIX + site], [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.ERROR
    assert run.delta == 1, run.delta


@pytest.mark.parametrize("site", sorted(SITES))
def test_s02_the_line_carries_no_id_and_no_exception_text(site, monkeypatch, caplog):
    """RED: the line holds no user id, no row data, no message, no traceback."""
    run = _drive(site, "guard", monkeypatch, caplog)
    recs = [r for r in run.records if r.getMessage().startswith("DB_GUARD_REFUSED")]
    assert len(recs) == 1, [r.getMessage() for r in recs]
    msg = recs[0].getMessage()
    for needle in (run.uid, run.sentinel, GUARD_MESSAGE, "42501", "APIError"):
        assert needle not in msg, needle
    assert recs[0].exc_info is None and not recs[0].args


@pytest.mark.parametrize("site", sorted(SITES))
def test_p01_the_arm_keeps_its_outcome_and_its_own_line(site, monkeypatch, caplog):
    """PIN (green at base): under the refusal the arm returns / raises as before and logs
    its own line once, at its own level."""
    run = _drive(site, "guard", monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    check, own = EXPECTED[site]
    assert check(run.outcome, run.exc), run.outcome
    if own is not None:
        level, prefix = own
        hits = [r for r in run.records if r.getMessage().startswith(prefix)]
        assert len(hits) == 1, [r.getMessage() for r in run.records]
        assert hits[0].levelno == level


@pytest.mark.parametrize("kind", ["other_code", "other_message", "success"])
@pytest.mark.parametrize("site", sorted(SITES))
def test_n01_no_line_and_no_count_without_the_guard_refusal(site, kind, monkeypatch, caplog):
    """NEG: a non-42501 error, a 42501 without the guard message, and a successful write
    log no DB_GUARD_REFUSED line and leave the counter alone."""
    run = _drive(site, kind, monkeypatch, caplog)
    assert run.fake.writes, "the driver never reached the users write"
    assert [r for r in run.records if r.getMessage().startswith("DB_GUARD_REFUSED")] == []
    assert run.delta == 0, run.delta
