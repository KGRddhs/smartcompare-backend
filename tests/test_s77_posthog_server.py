"""S77 POSTHOG part B -- backend server capture, the analytics preference toggle,
optional B2 person deletion and the bounded shutdown flush. RED tests.

Sources (binding order): .qa-s77/RULINGS_S77_POSTHOG.md PH1-PH11 > the review rulings
PR1-PR19 of .qa-s77/POSTHOG_SPEC_REVIEW.md > .qa-s77/POSTHOG_UNIT_SPEC.md (2.6 server
half, 4, 5, 8, 9 b-tests, 10). Base: main 18121839.

CONTRACT these tests pin (GREEN implements exactly these names):

  app/services/product_analytics_service.py (NEW; `import posthog` ONLY inside a
  function body, never at module level):
    posthog_server_capture_enabled() -> bool   ENABLE_POSTHOG_SERVER_CAPTURE read PER
        CALL with .strip().lower() in ("true", "1", "yes", "on") (the repo idiom,
        database_service.search_log_truth_enabled / db_offload.sync_db_offload_enabled)
        AND POSTHOG_PROJECT_API_KEY non-blank.
    posthog_person_delete_enabled() -> bool    ENABLE_POSTHOG_PERSON_DELETE, same idiom.
    async capture_compare_completed(*, user_id, comparison_id, full_response,
        input_type=None, preferences=None)      -> event "server_compare_completed"
    async capture_compare_failed(*, user_id, input_type, query, error_message,
        duration_ms, cost)                      -> event "server_compare_failed"
    ANALYTICS_PREF_CACHE_TTL_SECONDS = 300, ANALYTICS_PREF_CACHE_MAX_ENTRIES = 2048
        (module globals read at call time).
    _reset_state_for_tests()                    drops the client singleton, the
        preference cache and the in-process deleted-user set (repo precedent:
        database_service._reset_client_cache_for_tests).
    The client is built lazily, ONCE, inside asyncio.to_thread (the first
    `import posthog` included), as posthog.Posthog(<key>, host=POSTHOG_HOST or
    "https://eu.i.posthog.com", sync_mode=False, disable_geoip=True,
    enable_exception_autocapture=False, on_error=<logs "[POSTHOG] send failed: %s"
    type only, WARNING>, before_send=<drops "$ip">, ...); logging.getLogger("posthog")
    is set to CRITICAL at construction. A capture failure logs
    "[POSTHOG] capture skipped: <Type>" at WARNING and never raises.
  app/services/feedback_service.py: track_after_persist(..., input_type=None) captures
    BEFORE the falsy-id return, only when full_response.get("success") is True;
    save_comparison_and_track_cohort passes its own input_type.
  app/services/database_service.py: log_search captures server_compare_failed only
    for success False AND a user_id; success rows capture nothing.
  app/api/text_routes.py: the three direct track_after_persist calls pass
    input_type "text", "text", "text_stream" (PR12).
  app/api/auth_routes.py: PreferenceTogglesBody accepts analytics_enabled alone (PR16)
    and stores it in users.preferences; DELETE /account with B2 ON marks the user
    deleted in-process BEFORE the erase, then (fire-and-forget, off the response)
    flushes an EXISTING client via asyncio.to_thread(client.flush, timeout_seconds=2)
    and POSTs {POSTHOG_API_HOST or https://eu.posthog.com}/api/projects/
    {POSTHOG_PROJECT_ID}/persons/bulk_delete with distinct_ids [user_id],
    delete_events true, Authorization Bearer POSTHOG_PERSONAL_API_KEY, timeout 5 s,
    through httpx (AsyncClient or Client); failures logged by type with "[POSTHOG]".
  app/main.py: POSTHOG_SHUTDOWN_FLUSH_TIMEOUT = 1.0 and an @app.on_event("shutdown")
    _flush_product_analytics registered AFTER _drain_background_tasks; it runs
    client.flush(timeout_seconds=POSTHOG_SHUTDOWN_FLUSH_TIMEOUT) in asyncio.to_thread
    under wait_for(..., POSTHOG_SHUTDOWN_FLUSH_TIMEOUT + 0.25); no client -> no-op.
  requirements.in: posthog==7.60.1; requirements.txt: posthog==7.60.1 + backoff, distro.

Hermetic (PR19): the posthog package is replaced for EVERY test in this file by a
recording fake served from a monkeypatched sys.meta_path finder (no real client can
be constructed); sys.modules is touched through monkeypatch, and the fake entries the
import creates are popped at teardown. The service singleton is reset before and
after each test. Sentinels are plain words built at runtime; no key-shaped literal.
Nothing under app/ is imported at module top.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import importlib
import importlib.abc
import importlib.machinery
import json
import logging
import re
import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from tests._retro_r_mig_sql import install_network_guard

REPO = Path(__file__).resolve().parents[1]
APP_DIR = REPO / "app"
_SVC = "app.services.product_analytics_service"
_SVC_FILE = APP_DIR / "services" / "product_analytics_service.py"

USER = "user-s77-ph"
OTHER_USER = "user-s77-other"
CID = "cmp-s77-ph"
EU_INGEST = "https://eu.i.posthog.com"
EU_API = "https://eu.posthog.com"
PROJECT_ID = "41077"

# Sentinels (plain words; never key-shaped).
S_EMAIL = "s77-sentinel-email@example.invalid"
S_NAME = "S77SENTINELDISPLAYNAME"
S_TOKEN = "S77SENTINELACCESSTOKEN"
S_REASON = "S77SENTINELVERDICTREASON"
S_DECL = "S77SENTINELDECLARATION"
S_TRADE = "S77SENTINELTRADEOFF"
S_PROS = "S77SENTINELPROS"
S_CONS = "S77SENTINELCONS"
S_FACT = "S77SENTINELFACTCHECK"
S_CRIT = "S77SENTINELCRITIQUE"
S_PREF = "S77SENTINELBUDGETPREF"
S_URLTOK = "S77SENTINELURLTOKEN"
S_FRAG = "S77SENTINELFRAGMENT"
S_RAISE = "S77SENTINELEXCEPTIONTEXT"
S_ERRTXT = "S77SENTINELDELETIONERROR"

NEW_ENV_NAMES = (
    "ENABLE_POSTHOG_SERVER_CAPTURE",
    "POSTHOG_PROJECT_API_KEY",
    "POSTHOG_HOST",
    "ENABLE_POSTHOG_PERSON_DELETE",
    "POSTHOG_PERSONAL_API_KEY",
    "POSTHOG_PROJECT_ID",
    "POSTHOG_API_HOST",
)
RELATED_ENV_NAMES = (
    "ENABLE_SEARCH_LOG_TRUTH",
    "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
    "ENABLE_SYNC_DB_OFFLOAD",
    "ENABLE_ASYNC_REDIS_OFFLOAD",
)

REQUIRED_COMPLETED_KEYS = frozenset({
    "comparison_id", "saved", "input_type", "category",
    "product_a", "product_b", "winner_name", "winner_index",
    "price_a", "price_b", "currency_a", "currency_b",
    "price_found_a", "price_found_b",
    "partial", "partial_stage", "latency_ms", "cost_usd",
    "cached", "comparison_quality", "cache_hit", "query",
})
OPTIONAL_COMPLETED_KEYS = frozenset({"source_method_a", "source_method_b", "model_downgraded"})
FAILED_KEYS = frozenset({"input_type", "latency_ms", "cost_usd", "query", "error_class"})
# Library-reserved "$" keys a caller may legitimately pass; "$ip" is never one.
ALLOWED_DOLLAR_KEYS = frozenset({"$geoip_disable", "$process_person_profile"})


def _project_key() -> str:
    return "ph" + "c_" + ("s77projectkey" * 4)[:43]


def _personal_key() -> str:
    return "ph" + "x_" + "S77PERSONALKEY" + ("q" * 20)


# ---------------------------------------------------------------------------
# The posthog fake (served by a meta-path finder; records everything)
# ---------------------------------------------------------------------------


class _PHState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.imports: list = []
        self.constructions: list = []
        self.captures: list = []
        self.flushes: list = []
        self.other: list = []
        self.capture_raises = None
        self.construct_raises = None
        self.flush_hook = None
        self.order = None

    def _rec(self, bucket, entry) -> None:
        with self.lock:
            bucket.append(entry)

    def touched(self) -> bool:
        return bool(self.imports or self.constructions or self.captures
                    or self.flushes or self.other)


def _safe_copy(value):
    try:
        return copy.deepcopy(value)
    except Exception:  # noqa: BLE001
        return dict(value) if isinstance(value, dict) else value


def _make_fake_module(name: str, state: _PHState) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__dict__["__fake_posthog__"] = True

    class FakePosthog:
        def __init__(self, *args, **kwargs):
            state._rec(state.constructions, {
                "args": args, "kwargs": dict(kwargs), "thread": threading.get_ident(),
            })
            if state.order is not None:
                state.order.append("construct")
            if state.construct_raises is not None:
                raise state.construct_raises

        def capture(self, *args, **kwargs):
            state._rec(state.captures, {
                "args": _safe_copy(args), "kwargs": _safe_copy(kwargs),
                "thread": threading.get_ident(),
            })
            if state.capture_raises is not None:
                raise state.capture_raises
            return "fake-uuid"

        def flush(self, *args, **kwargs):
            state._rec(state.flushes, {
                "args": args, "kwargs": dict(kwargs), "thread": threading.get_ident(),
            })
            if state.order is not None:
                state.order.append("flush")
            if state.flush_hook is not None:
                state.flush_hook(*args, **kwargs)

        def shutdown(self, *args, **kwargs):
            state._rec(state.other, "client.shutdown")

        def __getattr__(self, attr):
            if attr.startswith("__"):
                raise AttributeError(attr)
            state._rec(state.other, "client." + attr)
            return lambda *a, **k: None

    def _module_getattr(attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        state._rec(state.other, "module." + attr)
        raise AttributeError(attr)

    mod.Posthog = FakePosthog
    mod.Client = FakePosthog
    mod.VERSION = "7.60.1"
    mod.__getattr__ = _module_getattr
    return mod


class _FakePosthogFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, state: _PHState) -> None:
        self.state = state

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "posthog" or fullname.startswith("posthog."):
            self.state._rec(self.state.imports, (fullname, threading.get_ident()))
            return importlib.machinery.ModuleSpec(
                fullname, self, is_package=(fullname == "posthog"),
            )
        return None

    def create_module(self, spec):
        return _make_fake_module(spec.name, self.state)

    def exec_module(self, module):
        return None


def _is_posthog_key(name: str) -> bool:
    return name == "posthog" or name.startswith("posthog.")


@pytest.fixture(autouse=True)
def ph(monkeypatch):
    """Every test in this file: the real posthog package is unreachable."""
    state = _PHState()
    for name in [k for k in list(sys.modules) if _is_posthog_key(k)]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "meta_path", [_FakePosthogFinder(state)] + list(sys.meta_path))
    yield state
    for name in [k for k in list(sys.modules) if _is_posthog_key(k)]:
        if getattr(sys.modules.get(name), "__fake_posthog__", False):
            sys.modules.pop(name, None)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in NEW_ENV_NAMES + RELATED_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"S77 POSTHOG tests must never touch the network: {attempts}"


def _try_svc():
    try:
        return importlib.import_module(_SVC)
    except ModuleNotFoundError as exc:
        if exc.name == _SVC:
            return None
        raise


@pytest.fixture(autouse=True)
def _svc_reset(ph):
    ph_logger = logging.getLogger("posthog")
    prior_level = ph_logger.level
    mod = _try_svc()
    if mod is not None:
        reset = getattr(mod, "_reset_state_for_tests", None)
        if reset is None:
            pytest.fail(f"{_SVC} must expose _reset_state_for_tests() (PR19 singleton reset)")
        reset()
    yield
    mod = sys.modules.get(_SVC)
    if mod is not None and getattr(mod, "_reset_state_for_tests", None) is not None:
        mod._reset_state_for_tests()
    ph_logger.setLevel(prior_level)


def _svc():
    mod = _try_svc()
    if mod is None:
        pytest.fail(
            f"{_SVC} does not exist -- S77 POSTHOG part B (server capture) is not "
            "implemented (spec 4.3)."
        )
    return mod


def _need(mod, name):
    value = getattr(mod, name, None)
    if value is None:
        pytest.fail(f"{mod.__name__}.{name} is missing (S77 POSTHOG contract; see module docstring)")
    return value


def _enable_capture(monkeypatch, host=None) -> None:
    monkeypatch.setenv("ENABLE_POSTHOG_SERVER_CAPTURE", "true")
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", _project_key())
    if host is not None:
        monkeypatch.setenv("POSTHOG_HOST", host)


def _enable_person_delete(monkeypatch, api_host=None) -> None:
    monkeypatch.setenv("ENABLE_POSTHOG_PERSON_DELETE", "true")
    monkeypatch.setenv("POSTHOG_PERSONAL_API_KEY", _personal_key())
    monkeypatch.setenv("POSTHOG_PROJECT_ID", PROJECT_ID)
    if api_host is not None:
        monkeypatch.setenv("POSTHOG_API_HOST", api_host)


def _event_of(rec):
    kwargs = rec["kwargs"]
    if "event" in kwargs:
        return kwargs["event"]
    return rec["args"][0] if rec["args"] else None


def _events(state: _PHState, name=None):
    out = []
    for rec in list(state.captures):
        ev = _event_of(rec)
        if name is None or ev == name:
            out.append((ev, rec["kwargs"].get("distinct_id"), rec["kwargs"].get("properties")))
    return out


def _only_props(state, name):
    evs = _events(state, name)
    assert len(evs) == 1, f"expected exactly one {name!r} capture, got {_events(state)!r}"
    _ev, distinct_id, props = evs[0]
    assert isinstance(props, dict), f"{name} properties must be a dict, got {props!r}"
    return distinct_id, props


def _plain_keys(props):
    dollar = {k for k in props if isinstance(k, str) and k.startswith("$")}
    assert "$ip" not in props, f"a capture carries $ip: {props!r}"
    assert dollar <= ALLOWED_DOLLAR_KEYS, f"unexpected $-keys in properties: {sorted(dollar)!r}"
    return set(props) - dollar


def _em_dash() -> str:
    return chr(0x2014)


# ---------------------------------------------------------------------------
# A recording fake Supabase client
# ---------------------------------------------------------------------------


class _FakeNoRows(Exception):
    pass


class _Resp:
    def __init__(self, data):
        self.data = data
        self.count = None


class _FakeQuery:
    def __init__(self, db, table):
        self._db = db
        self._table = table
        self._ops = []

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)

        def _op(*args, **kwargs):
            self._ops.append((attr, args, kwargs))
            return self
        return _op

    def execute(self):
        names = [op[0] for op in self._ops]
        with self._db.lock:
            self._db.executes.append((self._table, tuple(names), threading.get_ident()))
        if "insert" in names:
            payload = copy.deepcopy(next(op for op in self._ops if op[0] == "insert")[1][0])
            with self._db.lock:
                self._db.inserts.append((self._table, payload))
            return _Resp([dict(payload, id="row-s77")] if isinstance(payload, dict) else [])
        if self._table == "users":
            if self._db.users_raises is not None:
                raise self._db.users_raises
            row = copy.deepcopy(self._db.users_row)
            if "single" in names:
                if row is None:
                    raise _FakeNoRows("JSON object requested, multiple (or no) rows returned")
                return _Resp(row)
            if "maybe_single" in names:
                return _Resp(row)
            return _Resp([row] if row is not None else [])
        return _Resp([])


_DEFAULT_ROW = {"preferences": {}}


class _FakeDB:
    def __init__(self, users_row=_DEFAULT_ROW, users_raises=None):
        self.lock = threading.Lock()
        self.users_row = users_row
        self.users_raises = users_raises
        self.tables: list = []
        self.executes: list = []
        self.inserts: list = []
        self.other: list = []

    def table(self, name):
        with self.lock:
            self.tables.append(name)
        return _FakeQuery(self, name)

    def from_(self, name):
        return self.table(name)

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        with self.lock:
            self.other.append(attr)
        return MagicMock(name="fake-supabase." + attr)

    def user_reads(self):
        return [e for e in self.executes if e[0] == "users"]


def _install_db(monkeypatch, db: _FakeDB) -> _FakeDB:
    from app.services import auth_service, database_service

    def factory(*_a, **_k):
        return db

    monkeypatch.setattr(database_service, "get_supabase_client", factory)
    monkeypatch.setattr(database_service, "get_admin_supabase_client", factory)
    monkeypatch.setattr(auth_service, "get_admin_client", factory)
    svc = sys.modules.get(_SVC)
    if svc is not None:
        for name in ("get_supabase_client", "get_admin_supabase_client", "get_admin_client"):
            if hasattr(svc, name):
                monkeypatch.setattr(svc, name, factory)
    return db


# ---------------------------------------------------------------------------
# Fixtures for full_response / track_after_persist follow-ups
# ---------------------------------------------------------------------------


def _price(amount, currency, source_method=None):
    if amount is None:
        price = {"amount": None, "currency": currency, "unavailable": True, "reason": "pending_genuine"}
    else:
        price = {
            "amount": amount, "currency": currency, "retailer": "Example Store",
            "url": "https://store.example.com/p/1?ref=" + S_URLTOK, "in_stock": True,
        }
    if source_method is not None:
        price["source_method"] = source_method
    return price


def _full_response(*, success=True, partial=None, partial_stage=None,
                   source_methods=("shopify_json", "serper_shopping"),
                   model_downgraded=True, query="iPhone 15 vs Galaxy S24",
                   brand_a="Apple", name_a="iPhone 15", brand_b="Samsung",
                   name_b="Galaxy S24", winner_name="Apple iPhone 15",
                   amount_a=299.0, amount_b=289.5):
    sm_a, sm_b = source_methods
    metadata = {
        "query": query, "region": "bahrain", "elapsed_ms": 12345, "elapsed_seconds": 12.35,
        "total_cost": 0.0123, "cached": False, "comparison_quality": "normal",
        "cache_hit": True, "genuine_from_cache": False,
        "fact_check": {"product_0": {"note": S_FACT}, "product_1": {}},
        "cohort_injected": True,
        "_verdict_critique": {"critique": S_CRIT},
    }
    if partial is not None:
        metadata["partial"] = partial
    if partial_stage is not None:
        metadata["partial_stage"] = partial_stage
    if model_downgraded:
        metadata["model_downgraded"] = True
    return {
        "success": success,
        "query": query,
        "category": "smartphones",
        "overview": {
            "winner": {
                "product_index": 0, "name": winner_name, "declaration": S_DECL,
                "reason": S_REASON, "key_tradeoff": S_TRADE, "margin": "clear",
            },
            "products": [
                {"brand": brand_a, "name": name_a, "variant": "",
                 "price": _price(amount_a, "BHD", sm_a), "pros": [S_PROS], "cons": [S_CONS],
                 "overall_score": 8.1},
                {"brand": brand_b, "name": name_b, "variant": "",
                 "price": _price(amount_b, "BHD", sm_b), "pros": [S_PROS], "cons": [S_CONS],
                 "overall_score": 7.9},
            ],
        },
        "metadata": metadata,
        "user": {"email": S_EMAIL, "display_name": S_NAME, "access_token": S_TOKEN},
    }


def _failure_payload():
    from app.services.structured_comparison_service import TIMEOUT_FRIENDLY_MESSAGE
    return {"success": False, "error": TIMEOUT_FRIENDLY_MESSAGE, "code": "STREAM_TIMEOUT",
            "total_cost": 0.01, "query": "iPhone 15 vs Galaxy S24"}


def _patch_followups(monkeypatch):
    """Record the four existing track_after_persist follow-ups (no DB, no Redis)."""
    from app.services import feedback_service as fs
    import app.services.referral_service as rs

    calls: list = []

    async def _del(key):
        calls.append(("delete_cached", key))
        return True

    async def _track_event(*args, **kwargs):
        calls.append(("track_event", args, kwargs))
        return {"success": True, "id": "evt-s77"}

    async def _crit(comparison_id, crit):
        calls.append(("critique", comparison_id, crit))

    class _Referral:
        async def try_trigger_loop2(self, **kwargs):
            calls.append(("loop2", kwargs))

    monkeypatch.setattr(fs, "_delete_cached_async", _del)
    monkeypatch.setattr(fs, "track_event", _track_event)
    monkeypatch.setattr(fs, "_persist_verdict_critique", _crit)
    monkeypatch.setattr(rs, "ReferralService", _Referral)
    return calls


def _expected_followups(user_id=USER, cid=CID):
    return [
        ("delete_cached", f"home:savings:{user_id}"),
        ("track_event", (), {
            "user_id": user_id, "event_type": "comparison_completed",
            "event_data": {"cohort_injected": True}, "comparison_id": cid,
        }),
        ("critique", cid, {"critique": S_CRIT}),
        ("loop2", {"invitee_user_id": user_id, "comparison_id": cid}),
    ]


async def _log_failure(*, user_id=USER, success=False, error_message=None, query=None,
                       input_type="text_stream", cost=0.0123, duration_ms=30000):
    from app.services import database_service
    await database_service.log_search(
        query=query if query is not None else "iPhone 15 vs Galaxy S24",
        input_type=input_type, user_id=user_id, products_found=None, success=success,
        error_message=error_message, cost=cost, duration_ms=duration_ms,
    )


def _expected_search_log_record(*, error_message, user_id=USER, query="iPhone 15 vs Galaxy S24",
                                 success=False):
    record = {
        "query": query, "input_type": "text_stream", "products_found": [],
        "success": success, "cost": 0.0123, "duration_ms": 30000,
    }
    if user_id:
        record["user_id"] = user_id
    if error_message:
        record["error_message"] = error_message
    return record


async def _settle(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return predicate()


async def _drain_background(timeout=5.0):
    from app.utils.async_utils import _BACKGROUND_TASKS
    loop = asyncio.get_running_loop()
    pending = {t for t in list(_BACKGROUND_TASKS) if not t.done() and t.get_loop() is loop}
    if pending:
        await asyncio.wait(pending, timeout=timeout)


# ===========================================================================
# 1 -- flag readers (read per call; the repo truthy idiom)
# ===========================================================================

_TRUTH_ROWS = [
    (None, False), ("", False), ("false", False), ("False", False), ("0", False),
    ("no", False), ("off", False), ("maybe", False), ("enabled", False),
    ("true", True), ("TRUE", True), (" true ", True), ("True", True),
    ("1", True), ("yes", True), ("on", True),
]


def _set_or_del(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize("raw,expected", _TRUTH_ROWS, ids=[repr(r[0]) for r in _TRUTH_ROWS])
def test_capture_flag_reader_rows(monkeypatch, raw, expected):
    """ENABLE_POSTHOG_SERVER_CAPTURE: .strip().lower() in ("true","1","yes","on"),
    with the project key present so only the flag decides."""
    svc = _svc()
    reader = _need(svc, "posthog_server_capture_enabled")
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", _project_key())
    _set_or_del(monkeypatch, "ENABLE_POSTHOG_SERVER_CAPTURE", raw)
    assert reader() is expected


@pytest.mark.parametrize("raw,expected", _TRUTH_ROWS, ids=[repr(r[0]) for r in _TRUTH_ROWS])
def test_person_delete_flag_reader_rows(monkeypatch, raw, expected):
    """ENABLE_POSTHOG_PERSON_DELETE: same idiom, with both B2 vars present."""
    svc = _svc()
    reader = _need(svc, "posthog_person_delete_enabled")
    monkeypatch.setenv("POSTHOG_PERSONAL_API_KEY", _personal_key())
    monkeypatch.setenv("POSTHOG_PROJECT_ID", PROJECT_ID)
    _set_or_del(monkeypatch, "ENABLE_POSTHOG_PERSON_DELETE", raw)
    assert reader() is expected


def test_flag_readers_are_read_per_call(monkeypatch):
    svc = _svc()
    capture = _need(svc, "posthog_server_capture_enabled")
    delete = _need(svc, "posthog_person_delete_enabled")
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", _project_key())
    monkeypatch.setenv("POSTHOG_PERSONAL_API_KEY", _personal_key())
    monkeypatch.setenv("POSTHOG_PROJECT_ID", PROJECT_ID)
    for value, expected in (("true", True), ("false", False), ("on", True), ("", False)):
        monkeypatch.setenv("ENABLE_POSTHOG_SERVER_CAPTURE", value)
        monkeypatch.setenv("ENABLE_POSTHOG_PERSON_DELETE", value)
        assert capture() is expected, f"capture reader cached a stale value at {value!r}"
        assert delete() is expected, f"delete reader cached a stale value at {value!r}"


@pytest.mark.parametrize("key", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_capture_reader_is_false_without_a_project_key(monkeypatch, key):
    """Spec 4.3: enabled = flag truthy AND POSTHOG_PROJECT_API_KEY non-blank."""
    svc = _svc()
    reader = _need(svc, "posthog_server_capture_enabled")
    monkeypatch.setenv("ENABLE_POSTHOG_SERVER_CAPTURE", "true")
    _set_or_del(monkeypatch, "POSTHOG_PROJECT_API_KEY", key)
    assert reader() is False


def test_capture_functions_are_coroutines():
    import inspect
    svc = _svc()
    for name in ("capture_compare_completed", "capture_compare_failed"):
        assert inspect.iscoroutinefunction(_need(svc, name)), f"{name} must be async"


# ===========================================================================
# 2 -- flag-OFF identity (pins that hold at base)
# ===========================================================================


@pytest.mark.asyncio
async def test_flag_off_track_after_persist_is_byte_identical(monkeypatch, ph):
    """Every new name unset: the four follow-ups are exactly today's, no posthog
    import, no client, no users read. HOLDS AT BASE."""
    from app.services import feedback_service as fs
    db = _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    await fs.track_after_persist(CID, full_response=_full_response(), user_id=USER)
    assert calls == _expected_followups()
    assert not ph.touched(), (
        f"flag OFF touched posthog: imports={ph.imports} constructions={ph.constructions} "
        f"captures={ph.captures} other={ph.other}"
    )
    assert db.tables == [] and db.other == [], f"flag OFF made a DB call: {db.tables} {db.other}"


@pytest.mark.asyncio
async def test_flag_off_track_after_persist_falsy_id_still_returns_early(monkeypatch, ph):
    from app.services import feedback_service as fs
    db = _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    await fs.track_after_persist(None, full_response=_full_response(), user_id=USER)
    assert calls == []
    assert not ph.touched()
    assert db.tables == []


@pytest.mark.asyncio
async def test_flag_off_log_search_failure_row_is_byte_identical(monkeypatch, ph):
    """Every new name unset: one search_logs insert with today's record, nothing else.
    HOLDS AT BASE."""
    from app.services.structured_comparison_service import TIMEOUT_FRIENDLY_MESSAGE
    db = _install_db(monkeypatch, _FakeDB())
    await _log_failure(error_message=TIMEOUT_FRIENDLY_MESSAGE)
    assert db.tables == ["search_logs"], f"unexpected tables: {db.tables}"
    assert db.inserts == [("search_logs", _expected_search_log_record(
        error_message=TIMEOUT_FRIENDLY_MESSAGE))]
    assert not ph.touched()


@pytest.mark.parametrize("key", [None, "", "   "], ids=["key-unset", "key-empty", "key-blank"])
@pytest.mark.asyncio
async def test_flag_on_without_key_is_a_no_op(monkeypatch, ph, key):
    """No key = no-op even with the flag ON: no import, no client, no users read.
    HOLDS AT BASE."""
    from app.services import feedback_service as fs
    from app.services.structured_comparison_service import TIMEOUT_FRIENDLY_MESSAGE
    monkeypatch.setenv("ENABLE_POSTHOG_SERVER_CAPTURE", "true")
    _set_or_del(monkeypatch, "POSTHOG_PROJECT_API_KEY", key)
    db = _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    await fs.track_after_persist(CID, full_response=_full_response(), user_id=USER)
    await _log_failure(error_message=TIMEOUT_FRIENDLY_MESSAGE)
    assert calls == _expected_followups()
    assert not ph.touched(), f"blank key touched posthog: {ph.imports} {ph.constructions}"
    assert db.tables == ["search_logs"]


def _module_level_posthog_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits = []

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Import):
                hits.extend(a.name for a in child.names if _is_posthog_key(a.name))
            elif isinstance(child, ast.ImportFrom) and child.module and _is_posthog_key(child.module):
                hits.append(child.module)
            walk(child)
    walk(tree)
    return hits


def test_no_app_module_imports_posthog_at_module_level():
    """Flag OFF must never import the library: no app/ file imports posthog outside
    a function body. HOLDS AT BASE (and must keep holding)."""
    offenders = {}
    for path in sorted(APP_DIR.rglob("*.py")):
        hits = _module_level_posthog_imports(path)
        if hits:
            offenders[path.relative_to(REPO).as_posix()] = hits
    assert offenders == {}, f"module-level posthog import(s): {offenders}"


def test_service_module_imports_posthog_only_inside_a_function():
    """The new module exists, names posthog, and imports it lazily (spec 4.3)."""
    if not _SVC_FILE.is_file():
        pytest.fail(f"{_SVC_FILE.relative_to(REPO).as_posix()} does not exist (spec 4.3)")
    source = _SVC_FILE.read_text(encoding="utf-8")
    assert _module_level_posthog_imports(_SVC_FILE) == []
    tree = ast.parse(source)
    lazy = [
        n for n in ast.walk(tree)
        if (isinstance(n, ast.Import) and any(_is_posthog_key(a.name) for a in n.names))
        or (isinstance(n, ast.ImportFrom) and n.module and _is_posthog_key(n.module))
    ]
    assert lazy, "the service never imports posthog (lazily) at all"


# ===========================================================================
# 3 -- server_compare_completed (spec 4.3 + PH8/PH9/PH10, PR3)
# ===========================================================================


@pytest.mark.asyncio
async def test_completed_event_properties_are_exactly_the_spec_table(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    distinct_id, props = _only_props(ph, "server_compare_completed")
    assert distinct_id == USER, f"distinct_id must be the user id string, got {distinct_id!r}"
    keys = _plain_keys(props)
    assert keys == REQUIRED_COMPLETED_KEYS | OPTIONAL_COMPLETED_KEYS, (
        f"missing={sorted((REQUIRED_COMPLETED_KEYS | OPTIONAL_COMPLETED_KEYS) - keys)} "
        f"extra={sorted(keys - REQUIRED_COMPLETED_KEYS - OPTIONAL_COMPLETED_KEYS)}"
    )
    expected = {
        "comparison_id": CID, "saved": True, "input_type": "text", "category": "smartphones",
        "product_a": "Apple iPhone 15", "product_b": "Samsung Galaxy S24",
        "winner_name": "Apple iPhone 15", "winner_index": 0,
        "price_a": 299.0, "price_b": 289.5, "currency_a": "BHD", "currency_b": "BHD",
        "price_found_a": True, "price_found_b": True,
        "latency_ms": 12345, "cost_usd": 0.0123, "cached": False,
        "comparison_quality": "normal", "cache_hit": True,
        "source_method_a": "shopify_json", "source_method_b": "serper_shopping",
        "model_downgraded": True, "query": "iPhone 15 vs Galaxy S24",
    }
    wrong = {k: (props.get(k), v) for k, v in expected.items() if props.get(k) != v}
    assert wrong == {}, f"property values (got, expected): {wrong}"
    assert props["partial"] in (False, None)
    assert props["partial_stage"] is None


@pytest.mark.asyncio
async def test_completed_optional_keys_are_omitted_when_absent(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(
        user_id=USER, comparison_id=CID, preferences={},
        full_response=_full_response(source_methods=("shopify_json", None),
                                     model_downgraded=False, amount_b=None),
    )
    _d, props = _only_props(ph, "server_compare_completed")
    keys = _plain_keys(props)
    assert keys == REQUIRED_COMPLETED_KEYS | {"source_method_a"}, sorted(keys)
    assert props["price_b"] is None and props["price_found_b"] is False
    assert props["currency_b"] == "BHD"


@pytest.mark.asyncio
async def test_completed_partial_is_captured_with_its_stage(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(
        user_id=USER, comparison_id=CID, preferences={},
        full_response=_full_response(partial=True, partial_stage="verdict"),
    )
    _d, props = _only_props(ph, "server_compare_completed")
    assert props["partial"] is True and props["partial_stage"] == "verdict"


@pytest.mark.asyncio
async def test_completed_caps_query_200_and_names_120(monkeypatch, ph):
    """PH9: query <= 200 chars, product names and winner name <= 120 each."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    long_query = "q" * 500
    await capture(
        user_id=USER, comparison_id=CID, preferences={},
        full_response=_full_response(query=long_query, brand_a="B" * 10, name_a="N" * 300,
                                     brand_b="C" * 10, name_b="M" * 300, winner_name="W" * 300),
    )
    _d, props = _only_props(ph, "server_compare_completed")
    assert isinstance(props["query"], str) and 0 < len(props["query"]) <= 200
    assert long_query.startswith(props["query"])
    full_a, full_b = "B" * 10 + " " + "N" * 300, "C" * 10 + " " + "M" * 300
    for key, full in (("product_a", full_a), ("product_b", full_b), ("winner_name", "W" * 300)):
        value = props[key]
        assert isinstance(value, str) and 0 < len(value) <= 120, f"{key} len={len(value or '')}"
        assert full.startswith(value), f"{key} is not a prefix of the resolved name"


@pytest.mark.asyncio
async def test_completed_url_query_is_reduced_to_scheme_host_path(monkeypatch, ph):
    """PH9: a link loses its query and fragment."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    url = "https://shop.example.com/products/abc-123?variant=9&utm_source=" + S_URLTOK + "#" + S_FRAG
    await capture(user_id=USER, comparison_id=CID, preferences={},
                  full_response=_full_response(query=url))
    _d, props = _only_props(ph, "server_compare_completed")
    assert props["query"] == "https://shop.example.com/products/abc-123"


@pytest.mark.asyncio
async def test_completed_links_inside_a_text_query_are_reduced(monkeypatch, ph):
    """PH9 / PH6: every pasted link inside the query is shortened; no token survives."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    query = ("https://a.example.com/x/1?t=" + S_URLTOK + " vs https://b.example.com/y/2#" + S_FRAG)
    await capture(user_id=USER, comparison_id=CID, preferences={},
                  full_response=_full_response(query=query))
    _d, props = _only_props(ph, "server_compare_completed")
    assert S_URLTOK not in props["query"] and S_FRAG not in props["query"]
    assert "https://a.example.com/x/1" in props["query"]
    assert "https://b.example.com/y/2" in props["query"]


@pytest.mark.asyncio
async def test_completed_never_carries_identity_or_prose(monkeypatch, ph):
    """PH8 / spec 4.3 'Never': no email, name, token, verdict prose, pros/cons,
    preferences, fact_check or _verdict_critique anywhere in the capture call."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    prefs = {"analytics_enabled": True, "budget": S_PREF, "email": S_EMAIL, "display_name": S_NAME}
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=prefs)
    assert len(_events(ph, "server_compare_completed")) == 1
    blob = json.dumps([{"args": r["args"], "kwargs": r["kwargs"]} for r in ph.captures], default=str)
    leaked = [s for s in (S_EMAIL, S_NAME, S_TOKEN, S_REASON, S_DECL, S_TRADE, S_PROS, S_CONS,
                          S_FACT, S_CRIT, S_PREF, S_URLTOK, _project_key()) if s in blob]
    assert leaked == [], f"capture carries forbidden content: {leaked}"
    for rec in ph.captures:
        props = rec["kwargs"].get("properties") or {}
        assert "$set" not in props and "$set_once" not in props


@pytest.mark.parametrize("user_id", [None, ""], ids=["none", "empty"])
@pytest.mark.asyncio
async def test_no_user_id_means_no_event(monkeypatch, ph, user_id):
    """PH10: anonymous = nothing captured, no client, no preference read."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB())
    await capture(user_id=user_id, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert ph.captures == [] and ph.constructions == []
    assert db.user_reads() == []


@pytest.mark.asyncio
async def test_track_after_persist_captures_once_and_keeps_the_followups(monkeypatch, ph):
    """b3: flag ON + key -> exactly one server_compare_completed per call; the four
    follow-ups are byte-identical to flag OFF."""
    from app.services import feedback_service as fs
    _svc()
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    await fs.track_after_persist(CID, full_response=_full_response(), user_id=USER)
    assert calls == _expected_followups()
    distinct_id, props = _only_props(ph, "server_compare_completed")
    assert distinct_id == USER
    assert props["comparison_id"] == CID and props["saved"] is True
    assert props["input_type"] == "text", "input_type defaults to 'text' (spec 4.3)"


@pytest.mark.asyncio
async def test_track_after_persist_passes_input_type_through(monkeypatch, ph):
    from app.services import feedback_service as fs
    _svc()
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    _patch_followups(monkeypatch)
    await fs.track_after_persist(CID, full_response=_full_response(), user_id=USER,
                                 input_type="text_stream")
    _d, props = _only_props(ph, "server_compare_completed")
    assert props["input_type"] == "text_stream"


@pytest.mark.asyncio
async def test_track_after_persist_captures_unsaved_before_the_falsy_id_return(monkeypatch, ph):
    """Spec 4.3: delivered-but-unsaved compares are visible with saved False; the
    existing early return still skips the four follow-ups."""
    from app.services import feedback_service as fs
    _svc()
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    await fs.track_after_persist(None, full_response=_full_response(), user_id=USER)
    assert calls == []
    _d, props = _only_props(ph, "server_compare_completed")
    assert props["saved"] is False and props["comparison_id"] is None


@pytest.mark.parametrize("truth", [None, "true"], ids=["truth-unset", "truth-on"])
@pytest.mark.asyncio
async def test_success_false_never_emits_completed(monkeypatch, ph, truth):
    """PR3: a success False payload reaching track_after_persist captures nothing
    there, in both ENABLE_SEARCH_LOG_TRUTH states; the stream's log_search row is
    the only event (TRUTH ON writes success=False, TRUTH OFF writes a success row
    that captures nothing -- the PR4 limit). Control: a success True payload
    captures exactly one completed event."""
    from app.services import feedback_service as fs
    _svc()
    _set_or_del(monkeypatch, "ENABLE_SEARCH_LOG_TRUTH", truth)
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    failure = _failure_payload()
    # What the stream writes for a success:False terminal (text_routes.py:1220-1258).
    await _log_failure(success=(truth is None), error_message=failure["error"])
    await fs.track_after_persist(None, full_response=failure, user_id=USER)
    await fs.track_after_persist(CID, full_response=failure, user_id=USER)
    assert _events(ph, "server_compare_completed") == []
    expected_failed = 0 if truth is None else 1
    assert len(_events(ph, "server_compare_failed")) == expected_failed
    assert [c[0] for c in calls] == ["delete_cached", "track_event", "loop2"], (
        f"the CID follow-ups of a success False payload changed: {calls!r}"
    )
    await fs.track_after_persist(CID, full_response=_full_response(), user_id=USER)
    assert len(_events(ph, "server_compare_completed")) == 1, "control: success True must capture"


@pytest.mark.asyncio
async def test_composite_passes_its_own_input_type(monkeypatch, ph):
    """PR12: save_comparison_and_track_cohort hands its input_type to track_after_persist."""
    from app.services import feedback_service as fs
    seen = []

    async def _persist(**kwargs):
        return "cmp-composite"

    async def _track(comparison_id, **kwargs):
        seen.append((comparison_id, kwargs))

    monkeypatch.setattr(fs, "persist_comparison", _persist)
    monkeypatch.setattr(fs, "track_after_persist", _track)
    await fs.save_comparison_and_track_cohort(
        full_response=_full_response(), query="q", input_type="camera", user_id=USER,
    )
    assert len(seen) == 1
    assert seen[0][1].get("input_type") == "camera", f"composite kwargs: {seen[0][1]!r}"


def test_text_routes_direct_callers_pass_input_type_explicitly():
    """PR12: text_routes.py:744 / :931 / :1279 -> "text", "text", "text_stream"."""
    path = APP_DIR / "api" / "text_routes.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name != "track_after_persist":
            continue
        value = None
        for kw in node.keywords:
            if kw.arg == "input_type":
                value = kw.value.value if isinstance(kw.value, ast.Constant) else ast.unparse(kw.value)
        calls.append((node.lineno, value))
    calls.sort()
    assert len(calls) == 3, f"expected the three direct callers, found {calls}"
    assert [v for _l, v in calls] == ["text", "text", "text_stream"], calls


# ===========================================================================
# 4 -- server_compare_failed from log_search (spec 4.3, PH9, PH10)
# ===========================================================================


def _messages():
    from app.services.structured_comparison_service import (
        INTERNAL_ERROR_FRIENDLY_MESSAGE,
        LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
        TIMEOUT_FRIENDLY_MESSAGE,
    )
    dash = _em_dash()
    return {
        "timeout-friendly": (TIMEOUT_FRIENDLY_MESSAGE, "timeout"),
        "content-unavailable": ("We don't compare this category", "content_unavailable"),
        "insufficient-data": (
            "Comparison data was incomplete " + dash + " choose different products.",
            "insufficient_data",
        ),
        "internal-error": (INTERNAL_ERROR_FRIENDLY_MESSAGE, "other"),
        "llm-unavailable": (LLM_UNAVAILABLE_FRIENDLY_MESSAGE, "other"),
        "default-failed": ("Comparison failed", "other"),
        "none": (None, "other"),
    }


_MESSAGE_IDS = ["timeout-friendly", "content-unavailable", "insufficient-data",
                "internal-error", "llm-unavailable", "default-failed", "none"]


@pytest.mark.parametrize("case", _MESSAGE_IDS)
@pytest.mark.asyncio
async def test_log_search_failure_emits_failed_with_a_coarse_error_class(monkeypatch, ph, case):
    """The real failure messages log_search receives (text_routes._failure_log_message
    passes the human sentence, never the code) map to the four classes."""
    _svc()
    message, expected_class = _messages()[case]
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB())
    await _log_failure(error_message=message, input_type="text_stream")
    distinct_id, props = _only_props(ph, "server_compare_failed")
    assert distinct_id == USER
    assert _plain_keys(props) == FAILED_KEYS, sorted(props)
    assert props["error_class"] == expected_class
    assert props["input_type"] == "text_stream"
    assert props["latency_ms"] == 30000 and props["cost_usd"] == 0.0123
    if message:
        assert message not in json.dumps(props, default=str), "the raw message was captured"
    # The insert is unchanged by the hook.
    assert db.inserts == [("search_logs", _expected_search_log_record(error_message=message))]


@pytest.mark.asyncio
async def test_log_search_success_rows_capture_nothing(monkeypatch, ph):
    _svc()
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await _log_failure(success=True, error_message="partial:verdict")
    assert _events(ph) == []
    await _log_failure(success=False, error_message="Comparison failed")
    assert len(_events(ph, "server_compare_failed")) == 1, "control: a failure row must capture"


@pytest.mark.asyncio
async def test_log_search_anonymous_failure_captures_nothing(monkeypatch, ph):
    """PH10 on the failure hook."""
    _svc()
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB())
    await _log_failure(user_id=None, error_message="Comparison failed")
    assert _events(ph) == [] and ph.constructions == []
    assert db.user_reads() == []
    await _log_failure(user_id=USER, error_message="Comparison failed")
    assert len(_events(ph, "server_compare_failed")) == 1, "control"


@pytest.mark.asyncio
async def test_failed_query_is_capped_and_links_reduced(monkeypatch, ph):
    _svc()
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await _log_failure(error_message="Comparison failed", query="z" * 450)
    url = "https://shop.example.com/a/b?session=" + S_URLTOK + "#" + S_FRAG
    await _log_failure(error_message="Comparison failed", query=url)
    evs = _events(ph, "server_compare_failed")
    assert len(evs) == 2
    first, second = evs[0][2]["query"], evs[1][2]["query"]
    assert 0 < len(first) <= 200 and ("z" * 450).startswith(first)
    assert second == "https://shop.example.com/a/b"


# ===========================================================================
# 5 -- client construction (PH8, PR13, PR14)
# ===========================================================================


@pytest.mark.asyncio
async def test_client_constructor_kwargs(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert len(ph.constructions) == 1, f"constructions: {ph.constructions}"
    rec = ph.constructions[0]
    kwargs, args = rec["kwargs"], rec["args"]
    key = kwargs.get("project_api_key", args[0] if args else None)
    assert key == _project_key()
    assert kwargs.get("host") == EU_INGEST, f"host default must be EU ingestion, got {kwargs.get('host')!r}"
    assert "disable_geoip" in kwargs and kwargs["disable_geoip"] is True
    assert "enable_exception_autocapture" in kwargs, "pass enable_exception_autocapture explicitly (PH8)"
    assert kwargs["enable_exception_autocapture"] is False
    assert "sync_mode" in kwargs and kwargs["sync_mode"] is False
    assert callable(kwargs.get("on_error")), "on_error must be set (PR14)"
    assert callable(kwargs.get("before_send")), "before_send must be set (PH8)"


@pytest.mark.asyncio
async def test_client_host_honours_posthog_host(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch, host="https://ph-ingest.example.test")
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert ph.constructions and ph.constructions[0]["kwargs"].get("host") == "https://ph-ingest.example.test"


@pytest.mark.asyncio
async def test_before_send_drops_ip(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    before_send = ph.constructions[0]["kwargs"]["before_send"]
    msg = {"event": "server_compare_completed", "distinct_id": USER,
           "properties": {"$ip": "203.0.113.9", "keep": 1}}
    out = before_send(copy.deepcopy(msg))
    assert isinstance(out, dict), "before_send must return the event (None drops it)"
    assert "$ip" not in (out.get("properties") or {})
    assert (out.get("properties") or {}).get("keep") == 1
    bare = before_send({"event": "x", "distinct_id": USER})
    assert isinstance(bare, dict)


@pytest.mark.asyncio
async def test_on_error_logs_the_type_only(monkeypatch, ph, caplog):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    on_error = ph.constructions[0]["kwargs"]["on_error"]
    batch = [{"event": "server_compare_completed", "properties": {"query": S_URLTOK}}]
    with caplog.at_level(logging.DEBUG):
        on_error(RuntimeError(S_RAISE), batch)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(r.getMessage() == "[POSTHOG] send failed: RuntimeError" for r in warnings), (
        [r.getMessage() for r in caplog.records]
    )
    assert S_RAISE not in caplog.text and S_URLTOK not in caplog.text


@pytest.mark.asyncio
async def test_posthog_library_logger_is_silenced_to_critical(monkeypatch, ph):
    """PR14: library ERROR logs must not become Sentry events."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    logging.getLogger("posthog").setLevel(logging.NOTSET)
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert ph.constructions, "no client was built"
    assert logging.getLogger("posthog").level == logging.CRITICAL


@pytest.mark.asyncio
async def test_first_import_and_construction_run_off_the_loop(monkeypatch, ph):
    """PR13: the first `import posthog` and the constructor run in asyncio.to_thread."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    loop_thread = threading.get_ident()
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert ph.imports, "posthog was never imported"
    assert all(t != loop_thread for _n, t in ph.imports), f"import on the loop thread: {ph.imports}"
    assert ph.constructions and ph.constructions[0]["thread"] != loop_thread, (
        "the client was constructed on the event-loop thread"
    )


@pytest.mark.asyncio
async def test_concurrent_first_captures_build_one_client(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await asyncio.gather(*[
        capture(user_id=f"{USER}-{i}", comparison_id=f"{CID}-{i}",
                full_response=_full_response(), preferences={})
        for i in range(5)
    ])
    assert len(ph.constructions) == 1, f"singleton built {len(ph.constructions)} times"
    assert len(_events(ph, "server_compare_completed")) == 5


@pytest.mark.asyncio
async def test_a_raising_client_is_swallowed_and_logged_by_type(monkeypatch, ph, caplog):
    """The caller never sees the exception; the WARNING names the type only."""
    from app.services import feedback_service as fs
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    calls = _patch_followups(monkeypatch)
    ph.capture_raises = RuntimeError(S_RAISE)
    with caplog.at_level(logging.DEBUG):
        await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
        await fs.track_after_persist(CID, full_response=_full_response(), user_id=USER)
    assert len(ph.captures) == 2, "control: both captures reached the client"
    assert calls == _expected_followups(), "a raising capture broke the existing follow-ups"
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert "[POSTHOG] capture skipped: RuntimeError" in msgs, msgs
    for needle in (S_RAISE, "iPhone 15 vs Galaxy S24", _project_key()):
        assert needle not in caplog.text, f"log carries {needle[:12]!r}..."


@pytest.mark.asyncio
async def test_a_raising_constructor_is_swallowed(monkeypatch, ph, caplog):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    ph.construct_raises = ValueError(S_RAISE)
    with caplog.at_level(logging.DEBUG):
        await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert ph.constructions, "control: construction was attempted"
    assert S_RAISE not in caplog.text


# ===========================================================================
# 6 -- the opt-out (spec 2.6 server half, PR5)
# ===========================================================================


@pytest.mark.asyncio
async def test_route_preferences_opt_out_skips_without_a_read(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB(users_row={"preferences": {"analytics_enabled": True}}))
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(),
                  preferences={"analytics_enabled": False})
    assert _events(ph) == []
    assert db.user_reads() == [], "route preferences were supplied; no users read allowed"
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(),
                  preferences={"analytics_enabled": True})
    assert len(_events(ph, "server_compare_completed")) == 1, "control"
    assert db.user_reads() == []


@pytest.mark.asyncio
async def test_read_preference_opt_out_skips(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB(users_row={"preferences": {"analytics_enabled": False}}))
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert db.user_reads(), "no users.preferences read happened"
    assert _events(ph) == []


@pytest.mark.parametrize("row", [{"preferences": {}}, {"preferences": None},
                                 {"preferences": {"analytics_enabled": True}}],
                         ids=["no-key", "null-prefs", "explicit-true"])
@pytest.mark.asyncio
async def test_read_preference_default_is_on(monkeypatch, ph, row):
    """PH2: the switch defaults ON; only an explicit False opts out."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB(users_row=row))
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert len(_events(ph, "server_compare_completed")) == 1


@pytest.mark.parametrize("failure", ["missing-row", "read-error"])
@pytest.mark.asyncio
async def test_missing_row_or_read_error_is_opted_out(monkeypatch, ph, failure):
    """PR5: a missing row means opted out; a failed read fails closed, never raises."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    if failure == "missing-row":
        db = _FakeDB(users_row=None)
    else:
        db = _FakeDB(users_raises=RuntimeError(S_RAISE))
    _install_db(monkeypatch, db)
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert db.user_reads(), "the preference read never happened"
    assert _events(ph) == []


@pytest.mark.asyncio
async def test_preference_read_runs_off_the_loop_with_offload_unset(monkeypatch, ph):
    """PR5 / b8b: ENABLE_SYNC_DB_OFFLOAD unset (prod) -> run_db would read INLINE;
    the read must still run on a worker thread (asyncio.to_thread)."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB())
    loop_thread = threading.get_ident()
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    reads = db.user_reads()
    assert reads, "no users read happened"
    assert all(t != loop_thread for _tb, _ops, t in reads), "users.preferences read ran on the loop"
    assert len(_events(ph, "server_compare_completed")) == 1


@pytest.mark.asyncio
async def test_preference_cache_hits_within_the_ttl(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    assert _need(svc, "ANALYTICS_PREF_CACHE_TTL_SECONDS") == 300
    assert _need(svc, "ANALYTICS_PREF_CACHE_MAX_ENTRIES") == 2048
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB())
    for _ in range(3):
        await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert len(db.user_reads()) == 1, f"cache miss on repeat: {len(db.user_reads())} reads"
    await capture(user_id=OTHER_USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert len(db.user_reads()) == 2, "the cache must be per user"
    assert len(_events(ph, "server_compare_completed")) == 4


@pytest.mark.asyncio
async def test_preference_cache_ttl_and_size_are_read_at_call_time(monkeypatch, ph):
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _need(svc, "ANALYTICS_PREF_CACHE_TTL_SECONDS")
    _enable_capture(monkeypatch)
    db = _install_db(monkeypatch, _FakeDB())
    monkeypatch.setattr(svc, "ANALYTICS_PREF_CACHE_TTL_SECONDS", 0)
    for _ in range(2):
        await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert len(db.user_reads()) == 2, "TTL 0 must re-read"
    svc._reset_state_for_tests()
    db2 = _install_db(monkeypatch, _FakeDB())
    monkeypatch.setattr(svc, "ANALYTICS_PREF_CACHE_TTL_SECONDS", 300)
    monkeypatch.setattr(svc, "ANALYTICS_PREF_CACHE_MAX_ENTRIES", 2)
    for uid in ("u-a", "u-b", "u-c", "u-a"):
        await capture(user_id=uid, comparison_id=CID, full_response=_full_response(), preferences=None)
    assert len(db2.user_reads()) == 4, "a 2-entry cache must evict u-a after u-c"


# ===========================================================================
# 7 -- PUT /api/v1/auth/preference-toggles (PR16)
# ===========================================================================

_TOGGLES = "/api/v1/auth/preference-toggles"
_TOGGLE_USER = {"id": "u-s77-toggle", "email": S_EMAIL, "access_token": "tok"}


def _put_toggles(body, existing):
    from fastapi.testclient import TestClient

    from app.api import auth_routes
    from app.main import app

    captured = []
    user_client = MagicMock()
    select_chain = user_client.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value = MagicMock(data={"preferences": copy.deepcopy(existing)})

    def _update(payload):
        captured.append(copy.deepcopy(payload))
        inner = MagicMock()
        inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
        return inner

    user_client.table.return_value.update.side_effect = _update
    app.dependency_overrides[auth_routes.get_current_user] = lambda: dict(_TOGGLE_USER)
    try:
        with patch.object(auth_routes, "get_user_supabase_client", return_value=user_client), \
                patch.object(auth_routes, "get_admin_supabase_client", return_value=MagicMock()):
            resp = TestClient(app).put(_TOGGLES, json=body, headers={"Authorization": "Bearer tok"})
    finally:
        app.dependency_overrides.pop(auth_routes.get_current_user, None)
    return resp, captured


@pytest.mark.parametrize("value", [False, True])
def test_toggles_accepts_analytics_enabled_alone(value):
    existing = {"budget": "mid", "notifications_enabled": True}
    resp, captured = _put_toggles({"analytics_enabled": value}, existing)
    assert resp.status_code == 200, resp.text
    assert captured == [{"preferences": {"budget": "mid", "notifications_enabled": True,
                                         "analytics_enabled": value}}]


def test_toggles_stores_analytics_next_to_another_key():
    resp, captured = _put_toggles({"analytics_enabled": False, "notifications_enabled": False}, {})
    assert resp.status_code == 200, resp.text
    assert captured == [{"preferences": {"analytics_enabled": False, "notifications_enabled": False}}]


@pytest.mark.parametrize("body", [{}, {"analytics_enabled": None}, {"analytics_enabled": "banana"}],
                         ids=["empty", "analytics-null", "analytics-banana"])
def test_toggles_still_rejects_bodies_without_a_value(body):
    """PIN (holds at base): nothing provided -> 422, nothing written."""
    resp, captured = _put_toggles(body, {"budget": "mid"})
    assert resp.status_code == 422, resp.text
    assert captured == []


# ===========================================================================
# 8 -- the account-deletion route: flag-OFF identity and B2 (PH4, PR2)
# ===========================================================================


class _SendRecorder:
    """Intercepts every httpx send to a non-testserver host (async and sync)."""

    def __init__(self, monkeypatch):
        self.requests: list = []
        self.raise_exc = None
        self.status = 202
        self.json_body = {"events_queued_for_deletion": 7, "deletion_errors": []}
        self.gate = None
        self.order = None
        real_async = httpx.AsyncClient.send
        real_sync = httpx.Client.send
        recorder = self

        async def async_send(client_self, request, *args, **kwargs):
            if request.url.host == "testserver":
                return await real_async(client_self, request, *args, **kwargs)
            recorder._record(request, "async")
            if recorder.gate is not None:
                await recorder.gate.wait()
            if recorder.raise_exc is not None:
                raise recorder.raise_exc
            return httpx.Response(recorder.status, json=recorder.json_body, request=request)

        def sync_send(client_self, request, *args, **kwargs):
            if request.url.host == "testserver":
                return real_sync(client_self, request, *args, **kwargs)
            recorder._record(request, "sync")
            if recorder.raise_exc is not None:
                raise recorder.raise_exc
            return httpx.Response(recorder.status, json=recorder.json_body, request=request)

        monkeypatch.setattr(httpx.AsyncClient, "send", async_send)
        monkeypatch.setattr(httpx.Client, "send", sync_send)

    def _record(self, request, kind):
        try:
            body = json.loads(request.content.decode("utf-8")) if request.content else None
        except ValueError:
            body = request.content
        self.requests.append({
            "kind": kind, "method": request.method, "url": str(request.url),
            "headers": dict(request.headers), "body": body,
            "timeout": dict(request.extensions.get("timeout") or {}),
            "thread": threading.get_ident(),
        })
        if self.order is not None:
            self.order.append("post")


async def _delete_account(user=None, timeout=5.0):
    from app.api import auth_routes
    from app.main import app

    app.dependency_overrides[auth_routes.get_current_user] = lambda: dict(
        user or {"id": USER, "email": S_EMAIL, "access_token": "tok"})
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await asyncio.wait_for(
                client.delete("/api/v1/auth/account", headers={"Authorization": "Bearer t"}),
                timeout=timeout,
            )
    finally:
        app.dependency_overrides.pop(auth_routes.get_current_user, None)


def _patch_erase(monkeypatch, order=None, probe=None, raises=None):
    from app.api import auth_routes
    erased = []

    async def _erase(user_id):
        erased.append(user_id)
        if order is not None:
            order.append("erase")
        if probe is not None:
            await probe(user_id)
        if raises is not None:
            raise raises

    monkeypatch.setattr(auth_routes, "delete_user_account", _erase)
    return erased


@pytest.mark.asyncio
async def test_flag_off_deletion_route_is_byte_identical(monkeypatch, ph):
    """Every new name unset: same response, one erase, no new background task, no
    posthog, no outbound request. HOLDS AT BASE."""
    from app.api import auth_routes
    sends = _SendRecorder(monkeypatch)
    erased = _patch_erase(monkeypatch)
    labels = []
    real_ff = auth_routes.fire_and_forget

    def _ff(coro, label):
        labels.append(label)
        return real_ff(coro, label)

    monkeypatch.setattr(auth_routes, "fire_and_forget", _ff)
    resp = await _delete_account()
    await _drain_background()
    await asyncio.sleep(0.2)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True, "message": "Account and all associated data deleted"}
    assert erased == [USER]
    assert labels == [], f"flag OFF scheduled new background work: {labels}"
    assert sends.requests == []
    assert not ph.touched()


@pytest.mark.parametrize("missing", ["flag", "personal-key", "project-id"])
@pytest.mark.asyncio
async def test_b2_needs_the_flag_and_both_vars(monkeypatch, ph, missing):
    """B2 OFF or half-configured -> no bulk_delete request. HOLDS AT BASE."""
    _enable_person_delete(monkeypatch)
    name = {"flag": "ENABLE_POSTHOG_PERSON_DELETE", "personal-key": "POSTHOG_PERSONAL_API_KEY",
            "project-id": "POSTHOG_PROJECT_ID"}[missing]
    monkeypatch.delenv(name, raising=False)
    sends = _SendRecorder(monkeypatch)
    _patch_erase(monkeypatch)
    resp = await _delete_account()
    await _drain_background()
    await asyncio.sleep(0.2)
    assert resp.status_code == 200, resp.text
    assert sends.requests == []


@pytest.mark.parametrize("api_host", [None, "https://ph-private.example.test"],
                         ids=["default-eu", "custom-host"])
@pytest.mark.asyncio
async def test_b2_posts_bulk_delete_after_the_erase(monkeypatch, ph, caplog, api_host):
    """PH4 / spec 4.5: one POST, the exact URL, body, bearer and 5 s timeout; the key
    is never logged."""
    _svc()
    _enable_person_delete(monkeypatch, api_host=api_host)
    order: list = []
    sends = _SendRecorder(monkeypatch)
    sends.order = order
    _patch_erase(monkeypatch, order=order)
    with caplog.at_level(logging.DEBUG):
        resp = await _delete_account()
        await _drain_background()
        await _settle(lambda: len(sends.requests) >= 1)
    assert resp.status_code == 200, resp.text
    assert len(sends.requests) == 1, f"requests: {sends.requests}"
    req = sends.requests[0]
    host = api_host or EU_API
    assert req["method"] == "POST"
    assert req["url"].rstrip("/") == f"{host}/api/projects/{PROJECT_ID}/persons/bulk_delete"
    assert req["headers"].get("authorization") == "Bearer " + _personal_key()
    assert isinstance(req["body"], dict), req["body"]
    assert req["body"].get("distinct_ids") == [USER]
    assert req["body"].get("delete_events") is True
    assert S_EMAIL not in json.dumps(req["body"])
    assert req["timeout"].get("read") == 5.0, req["timeout"]
    assert all(v is None or v <= 5.0 for v in req["timeout"].values()), req["timeout"]
    assert order.index("erase") < order.index("post"), order
    assert _personal_key() not in caplog.text


@pytest.mark.asyncio
async def test_b2_flushes_an_existing_client_off_loop_before_the_post(monkeypatch, ph):
    """PR2: asyncio.to_thread(client.flush, timeout_seconds=2) BEFORE bulk_delete."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _enable_person_delete(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=OTHER_USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert len(ph.constructions) == 1, "control: the client exists"
    order: list = []
    ph.order = order
    sends = _SendRecorder(monkeypatch)
    sends.order = order
    _patch_erase(monkeypatch, order=order)
    loop_thread = threading.get_ident()
    resp = await _delete_account()
    await _drain_background()
    await _settle(lambda: len(sends.requests) >= 1)
    assert resp.status_code == 200, resp.text
    assert len(ph.flushes) == 1, f"flushes: {ph.flushes}"
    fl = ph.flushes[0]
    ts = fl["kwargs"].get("timeout_seconds", fl["args"][0] if fl["args"] else None)
    assert ts == 2, f"flush timeout_seconds must be 2, got {ts!r}"
    assert fl["thread"] != loop_thread, "client.flush ran on the event-loop thread"
    assert "flush" in order and "post" in order and order.index("flush") < order.index("post"), order


@pytest.mark.asyncio
async def test_b2_without_a_client_posts_without_building_one(monkeypatch, ph):
    """B2 is activated BEFORE capture (PH4): no client -> no flush, no construction."""
    _svc()
    _enable_person_delete(monkeypatch)
    sends = _SendRecorder(monkeypatch)
    _patch_erase(monkeypatch)
    resp = await _delete_account()
    await _drain_background()
    await _settle(lambda: len(sends.requests) >= 1)
    assert resp.status_code == 200
    assert len(sends.requests) == 1
    assert ph.constructions == [] and ph.flushes == []


@pytest.mark.asyncio
async def test_b2_marks_the_user_deleted_before_the_erase(monkeypatch, ph):
    """PR2: a capture racing the erase, and any later capture, skips the user."""
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _enable_person_delete(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    _SendRecorder(monkeypatch)

    async def _probe(user_id):
        await capture(user_id=user_id, comparison_id="cmp-race", full_response=_full_response(),
                      preferences={})

    _patch_erase(monkeypatch, probe=_probe)
    resp = await _delete_account()
    await _drain_background()
    assert resp.status_code == 200, resp.text
    await capture(user_id=USER, comparison_id="cmp-after", full_response=_full_response(),
                  preferences={})
    assert [e for e in _events(ph) if e[1] == USER] == [], "a deleted user was captured"
    await capture(user_id=OTHER_USER, comparison_id=CID, full_response=_full_response(), preferences={})
    assert len([e for e in _events(ph) if e[1] == OTHER_USER]) == 1, "control: others still captured"


@pytest.mark.asyncio
async def test_b2_runs_off_the_response_path(monkeypatch, ph):
    """Spec 4.5: fire-and-forget -- the response does not wait for PostHog."""
    _svc()
    _enable_person_delete(monkeypatch)
    sends = _SendRecorder(monkeypatch)
    sends.gate = asyncio.Event()
    _patch_erase(monkeypatch)
    try:
        resp = await _delete_account(timeout=3.0)
    except asyncio.TimeoutError:
        pytest.fail("DELETE /account waited for the PostHog bulk_delete (must be fire-and-forget)")
    finally:
        sends.gate.set()
    assert resp.status_code == 200
    await _drain_background()
    await _settle(lambda: len(sends.requests) >= 1)
    assert len(sends.requests) == 1


@pytest.mark.asyncio
async def test_b2_failed_erase_sends_nothing(monkeypatch, ph):
    """The user row still exists -> no PostHog deletion. HOLDS AT BASE."""
    _enable_person_delete(monkeypatch)
    sends = _SendRecorder(monkeypatch)
    _patch_erase(monkeypatch, raises=RuntimeError(S_RAISE))
    resp = await _delete_account()
    await _drain_background()
    await asyncio.sleep(0.2)
    assert resp.status_code == 500
    assert sends.requests == []


@pytest.mark.parametrize("mode", ["transport-error", "http-403", "deletion-errors"])
@pytest.mark.asyncio
async def test_b2_failures_are_logged_by_type_and_counts_only(monkeypatch, ph, caplog, mode):
    _svc()
    _enable_person_delete(monkeypatch)
    sends = _SendRecorder(monkeypatch)
    if mode == "transport-error":
        sends.raise_exc = httpx.ConnectError(S_RAISE)
    elif mode == "http-403":
        sends.status = 403
        sends.json_body = {"detail": S_ERRTXT}
    else:
        sends.json_body = {"events_queued_for_deletion": 7,
                           "deletion_errors": [{"distinct_id": USER, "error": S_ERRTXT}]}
    _patch_erase(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        resp = await _delete_account()
        await _drain_background()
        await _settle(lambda: len(sends.requests) >= 1)
        await asyncio.sleep(0.1)
    assert resp.status_code == 200, "a PostHog failure must never fail the deletion"
    assert len(sends.requests) == 1
    for needle in (S_RAISE, S_ERRTXT, _personal_key()):
        assert needle not in caplog.text, f"log carries {needle[:14]!r}..."
    if mode != "deletion-errors":
        warns = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("[POSTHOG]" in m for m in warns), warns
    if mode == "transport-error":
        assert any("ConnectError" in r.getMessage() for r in caplog.records)


# ===========================================================================
# 9 -- shutdown flush (spec 4.4, PR13)
# ===========================================================================


def _registered_shutdown_handler_names():
    """Duck-typed as in tests/test_shutdown_drain.py (local 0.115 vs pinned 0.141)."""
    import app.main as app_main
    handlers = getattr(app_main.app.router, "on_shutdown", None)
    if handlers:
        return [getattr(f, "__name__", repr(f)) for f in handlers]
    lines = (APP_DIR / "main.py").read_text(encoding="utf-8").splitlines()
    names = []
    for index, line in enumerate(lines):
        if 'on_event("shutdown")' not in line and "on_event('shutdown')" not in line:
            continue
        for following in lines[index + 1: index + 5]:
            stripped = following.strip()
            if stripped.startswith("async def ") or stripped.startswith("def "):
                names.append(stripped.split("def ", 1)[1].split("(", 1)[0].strip())
                break
    return names


def _main_attr(name):
    import app.main as app_main
    value = getattr(app_main, name, None)
    if value is None:
        pytest.fail(f"app.main.{name} is missing (spec 4.4 / PR13 shutdown flush)")
    return value


def test_shutdown_flush_is_registered_after_the_w16_drain():
    names = _registered_shutdown_handler_names()
    assert "_drain_background_tasks" in names, names
    assert "_flush_product_analytics" in names, f"no _flush_product_analytics handler: {names}"
    assert names.index("_flush_product_analytics") > names.index("_drain_background_tasks"), names


def test_shutdown_flush_timeout_is_one_second():
    value = _main_attr("POSTHOG_SHUTDOWN_FLUSH_TIMEOUT")
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    assert value == 1.0


@pytest.mark.asyncio
async def test_shutdown_flush_without_a_client_does_nothing(monkeypatch, ph):
    handler = _main_attr("_flush_product_analytics")
    _svc()
    _enable_capture(monkeypatch)
    started = time.monotonic()
    await handler()
    assert time.monotonic() - started < 0.5
    assert not ph.touched(), f"no client existed, yet: {ph.imports} {ph.constructions} {ph.flushes}"


@pytest.mark.asyncio
async def test_shutdown_flush_flushes_the_client_off_loop(monkeypatch, ph):
    handler = _main_attr("_flush_product_analytics")
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    loop_thread = threading.get_ident()
    await handler()
    assert len(ph.flushes) == 1, ph.flushes
    fl = ph.flushes[0]
    ts = fl["kwargs"].get("timeout_seconds", fl["args"][0] if fl["args"] else None)
    assert ts == 1.0, f"flush must get timeout_seconds=POSTHOG_SHUTDOWN_FLUSH_TIMEOUT, got {ts!r}"
    assert fl["thread"] != loop_thread, "client.flush ran on the event-loop thread"


@pytest.mark.asyncio
async def test_shutdown_flush_is_bounded_by_the_timeout_plus_a_quarter(monkeypatch, ph, caplog):
    """A flush that ignores its own timeout is abandoned at T + 0.25 s; a flush that
    honours T completes (the outer bound is not tighter than the inner one)."""
    import app.main as app_main
    handler = _main_attr("_flush_product_analytics")
    _main_attr("POSTHOG_SHUTDOWN_FLUSH_TIMEOUT")
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})
    monkeypatch.setattr(app_main, "POSTHOG_SHUTDOWN_FLUSH_TIMEOUT", 0.2)

    honoured = []

    def _honour(*args, **kwargs):
        ts = kwargs.get("timeout_seconds", args[0] if args else None)
        time.sleep(ts if isinstance(ts, (int, float)) else 0.2)
        honoured.append(True)

    ph.flush_hook = _honour
    await handler()
    assert honoured == [True], "a flush that honours its timeout was cut off by the outer bound"

    release = threading.Event()
    ph.flush_hook = lambda *a, **k: release.wait(3.0)
    try:
        with caplog.at_level(logging.DEBUG):
            started = time.monotonic()
            await handler()
            elapsed = time.monotonic() - started
    finally:
        release.set()
    assert elapsed < 0.2 + 0.25 + 0.6, f"shutdown flush not bounded: {elapsed:.2f}s"
    assert elapsed >= 0.2, f"outer bound tighter than the flush timeout: {elapsed:.2f}s"
    assert any("TimeoutError" in r.getMessage() for r in caplog.records
               if r.levelno >= logging.WARNING), [r.getMessage() for r in caplog.records]


@pytest.mark.asyncio
async def test_shutdown_flush_swallows_a_raising_flush(monkeypatch, ph, caplog):
    handler = _main_attr("_flush_product_analytics")
    svc = _svc()
    capture = _need(svc, "capture_compare_completed")
    _enable_capture(monkeypatch)
    _install_db(monkeypatch, _FakeDB())
    await capture(user_id=USER, comparison_id=CID, full_response=_full_response(), preferences={})

    def _boom(*a, **k):
        raise RuntimeError(S_RAISE)

    ph.flush_hook = _boom
    with caplog.at_level(logging.DEBUG):
        await handler()
    assert len(ph.flushes) == 1
    assert S_RAISE not in caplog.text
    assert any("RuntimeError" in r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)


# ===========================================================================
# 10 -- dependency pins (requirements read as text)
# ===========================================================================


def _req_lines(name):
    return [ln.strip() for ln in (REPO / name).read_text(encoding="utf-8-sig").splitlines()]


def _via_block(lines, pin_prefix):
    for index, line in enumerate(lines):
        if line.startswith(pin_prefix):
            block = []
            for following in lines[index + 1:]:
                if not following.startswith("#"):
                    break
                block.append(following)
            return line, " ".join(block)
    return None, ""


def test_requirements_in_pins_posthog_7_60_1():
    lines = _req_lines("requirements.in")
    pins = [ln for ln in lines if re.match(r"^posthog\b", ln, re.IGNORECASE)]
    assert pins == ["posthog==7.60.1"], f"requirements.in posthog lines: {pins}"


def test_requirements_txt_locks_posthog_and_its_new_transitives():
    lines = _req_lines("requirements.txt")
    assert "posthog==7.60.1" in lines, "requirements.txt does not lock posthog==7.60.1"
    for dep in ("backoff", "distro"):
        line, via = _via_block(lines, dep + "==")
        assert line is not None, f"requirements.txt does not lock {dep} (posthog dependency)"
        assert "posthog" in via, f"{line}: its 'via' block does not name posthog: {via!r}"
