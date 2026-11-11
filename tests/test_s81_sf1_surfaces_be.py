"""S81-SF1 SURFACES-BE -- the frozen RED file (spec section 5 as amended by RULINGS_S81_SF1).

Flags: ENABLE_FEEDBACK_V2 + ENABLE_SURFACES_FIELD (new names, default OFF, read per call)
and the knob APP_SURFACES_LIVE. Unflagged by ruling: the four appended event types and the
per-type property filter with its value rules (R-SF1-20 / R-SF1-38), the three narrowed
except-arm log lines (R-SF1-27).

RED rows fail at base 18cb9e04 on an AssertionError only: a missing symbol, kwarg, file or
model field is asserted through getattr / inspect.signature / Path.exists first. PIN rows are
green at base and run with the FULL companion configuration (the flags OFF with
APP_SURFACES_LIVE set, the request-context headers ON with a synthetic pepper, the W4-13
marker and the S81-10 gate in both states where they apply) plus recorders on the insert
payloads (ruling B1). Hermetic: every Supabase client is a recording MagicMock, no network,
synthetic ids built at run time. Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
import typing
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app  # noqa: F401 - import first (the dotenv guard), then monkeypatch
from app.api import feedback_routes as fr
from app.api import referral_routes as rr
from app.api import version_routes as vr
from app.services import database_service as ds
from app.services import feedback_service as fs
from app.services import referral_service as rs
from app.utils import request_context as rc

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "migrations"
ROLLBACK = MIG / "rollback"

ARROW = chr(0x2192)  # the wire loc separator of the VALIDATION_ERROR envelope
PFX = "Validation error: body " + ARROW + " "
MISSING_USEFUL = PFX + "useful: Field required"
SHARE_EXPECTED = "'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'"
SHARE_BASE = PFX + "share_target: Input should be " + SHARE_EXPECTED
SHARE_V2 = (PFX + "share_target: Input should be 'whatsapp', 'copy', 'x', 'telegram', "
            "'snapchat', 'other', 'sms', 'email' or 'more'")
EVENT_SIZE_MSG = (PFX + "events " + ARROW + " 0 " + ARROW
                  + " event_data: Value error, event_data too large (max 10KB)")
EVENT_CRID_MSG = (PFX + "events " + ARROW + " 0 " + ARROW
                  + " compare_request_id: Value error, compare_request_id must be a valid UUID")
NO_ANSWER = "feedback body carries no answer"

BASE_EVENTS_31 = [
    "save", "share", "source_click", "tab_switch", "feedback_submit", "result_view_duration",
    "compare_entry_view", "compare_cancelled", "compare_entry_paywall_banner_view",
    "compare_entry_paywall_banner_tap", "compare_entry_content_block", "compare_entry_submit",
    "compare_entry_paste_split", "compare_entry_mode_autoswitch", "compare_entry_ready",
    "share_sheet_opened", "share_completed", "demographics_submitted", "demographics_dismissed",
    "onboarding_started", "onboarding_step_completed", "onboarding_completed",
    "spec_expand", "result_abandon", "screenshot",
    "scan_start", "scan_identity_resolved", "scan_comparison_ready", "scan_failed",
    "scan_cancelled", "image_load_failed",
]
NEW_EVENTS = ["category_coming_soon_tap", "share_channel_selected", "share_target_opened",
              "store_cta_tap"]
ALLOWLIST = {
    "category_coming_soon_tap": frozenset({"category"}),
    "share_channel_selected": frozenset({"channel"}),
    "share_target_opened": frozenset({"share_target"}),
    "store_cta_tap": frozenset({"merchant_id"}),
}
NINE = ("whatsapp", "copy", "x", "telegram", "snapchat", "other", "sms", "email", "more")
SIX = NINE[:6]
BASE_SAVE_KWARGS = ["user_id", "comparison_id", "useful", "mattered_most", "change_suggestion",
                    "access_token", "winner_correct", "price_correct", "specs_correct"]
NEW_SAVE_KWARGS = ["identity_correct", "wrong_side", "preference", "correction", "source",
                   "compare_request_id"]
LOG_SEARCH_PARAMS = ["query", "input_type", "user_id", "products_found", "success",
                     "error_message", "cost", "duration_ms", "is_synthetic"]
BASE_VERSION = {"min_version": "1.0.0", "latest_version": "1.0.0", "force_update": False,
                "update_url_ios": "", "update_url_android": ""}
FIVE = list(BASE_VERSION)

ON = ["true", " TRUE ", "1", "yes", "On"]
OFF = [None, "", "false", "0", "off", "no", " FALSE "]
OFF_EXTRA = OFF + ["2", "enabled"]

UUID = str(uuid.uuid4())  # synthetic, built at run time
UUID2 = str(uuid.uuid4())
CORRECTION = "Dior Sauvage EDT"
MARKER = "sf1-row-marker-" + uuid.uuid4().hex[:6]

_FLAG_NAMES = ("ENABLE_FEEDBACK_V2", "ENABLE_SURFACES_FIELD", "APP_SURFACES_LIVE",
               "ENABLE_REQUEST_CONTEXT_HEADERS", "ENABLE_FRAGRANCE_ONLY_GATE",
               "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", "ENABLE_SYNC_DB_OFFLOAD",
               "ENABLE_DEVICE_DAILY_QUOTA", "APP_MIN_VERSION", "APP_LATEST_VERSION",
               "APP_FORCE_UPDATE", "APP_STORE_URL", "PLAY_STORE_URL")


# ---------------------------------------------------------------- fixtures / helpers

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in _FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    tokens = rc.bind_from_headers([])
    yield
    rc.reset_request_context(tokens)
    limiter.enabled = prior


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _full_config(monkeypatch, v2=None, surfaces="true"):
    """The B1 companion configuration: every companion flag / knob set, v2 as given."""
    _set(monkeypatch, "ENABLE_FEEDBACK_V2", v2)
    _set(monkeypatch, "ENABLE_SURFACES_FIELD", surfaces)
    monkeypatch.setenv("APP_SURFACES_LIVE", "skincare,makeup")
    monkeypatch.setenv("ENABLE_REQUEST_CONTEXT_HEADERS", "true")
    monkeypatch.setenv("DEVICE_KEY_PEPPER", "sf1-pepper-" + uuid.uuid4().hex[:8])


def _attr(mod, name):
    value = getattr(mod, name, None)
    assert value is not None, "%s.%s is missing" % (mod.__name__, name)
    return value


def _client():
    return TestClient(app)


async def _noop_impl():
    return {"success": True}


def _noop():
    return _noop_impl()


@pytest.fixture
def save_rec(monkeypatch):
    """Record every save_feedback call at the route (kwargs, in order)."""
    calls = []

    def _rec(**kw):
        calls.append(list(kw.items()))
        return _noop()

    def _ff(coro, label=None, **_k):
        coro.close()

    monkeypatch.setattr(fr, "save_feedback", _rec)
    monkeypatch.setattr(fr, "fire_and_forget", _ff)
    return calls


@pytest.fixture
def run_ff(monkeypatch):
    """fire_and_forget recorder: the coroutine is kept and run after the request."""
    pending = []

    def _ff(coro, label=None, **_k):
        pending.append(coro)

    monkeypatch.setattr(fr, "fire_and_forget", _ff)

    def _drain():
        out = [asyncio.run(c) for c in pending]
        pending.clear()
        return out

    yield _drain
    for coro in pending:
        coro.close()


@pytest.fixture
def events_rec(monkeypatch):
    calls = []

    def _rec(events):
        calls.append([dict(e) for e in events])
        return _noop()

    def _ff(coro, label=None, **_k):
        coro.close()

    monkeypatch.setattr(fr, "track_events_batch", _rec)
    monkeypatch.setattr(fr, "fire_and_forget", _ff)
    return calls


def _recording_client(raise_exc=None):
    resp = MagicMock()
    resp.data = [{"id": "sf1-row"}]
    client = MagicMock()
    if raise_exc is not None:
        client.table.return_value.insert.return_value.execute.side_effect = raise_exc
    else:
        client.table.return_value.insert.return_value.execute.return_value = resp
    return client


def _record_of(client):
    return client.table.return_value.insert.call_args[0][0]


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        # One record reaches this handler once per logger it propagates through.
        if not any(r is record for r in self.records):
            self.records.append(record)


@pytest.fixture
def logs():
    handler = _ListHandler()
    loggers = [logging.getLogger(), fs.logger, ds.logger, fr.logger, rs.logger,
               logging.getLogger("app")]
    saved = []
    seen = set()
    for lg in loggers:
        if id(lg) in seen:
            continue
        seen.add(id(lg))
        saved.append((lg, lg.level))
        lg.setLevel(logging.DEBUG)
        lg.addHandler(handler)
    yield handler.records
    for lg, level in saved:
        lg.removeHandler(handler)
        lg.setLevel(level)


def _formatted(record):
    """The message plus any traceback text, as a handler would write it."""
    return logging.Formatter("%(name)s %(levelname)s %(message)s").format(record)


def _post_feedback(client, body=None, raw=None):
    if raw is not None:
        return client.post("/api/v1/feedback", content=raw,
                           headers={"content-type": "application/json"})
    return client.post("/api/v1/feedback", json=body)


def _assert_envelope(resp, status, error):
    assert resp.status_code == status, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert body["success"] is False, body
    assert body["code"] == "VALIDATION_ERROR", body
    assert body["error"] == error, body["error"]
    assert isinstance(body.get("request_id"), str), body


def _model_errors(model, data):
    try:
        model.model_validate(data)
    except ValidationError as exc:
        return json.loads(exc.json(include_url=False))
    return "ok"


def _bind_request_id(value):
    return rc.bind_from_headers([(rc.HEADER_COMPARE_REQUEST_ID, value.encode("ascii"))])


# ---------------------------------------------------------------- readers R01-R04

def _reader_table(fn, monkeypatch, name):
    for v in ON:
        _set(monkeypatch, name, v)
        assert fn() is True, (name, v)
    for v in OFF_EXTRA:
        _set(monkeypatch, name, v)
        assert fn() is False, (name, v)


def test_r01_feedback_v2_reader(monkeypatch):
    fn = _attr(fs, "feedback_v2_enabled")
    assert callable(fn)
    _reader_table(fn, monkeypatch, "ENABLE_FEEDBACK_V2")


def test_r02_log_search_reader_parity(monkeypatch):
    local = _attr(ds, "_feedback_v2_enabled")
    public = _attr(fs, "feedback_v2_enabled")
    _reader_table(local, monkeypatch, "ENABLE_FEEDBACK_V2")
    for v in ON + OFF_EXTRA + ["TRUE", "  on  ", "garbage"]:
        _set(monkeypatch, "ENABLE_FEEDBACK_V2", v)
        assert local() is public(), v


def test_r03_surfaces_reader(monkeypatch):
    fn = _attr(vr, "surfaces_field_enabled")
    _reader_table(fn, monkeypatch, "ENABLE_SURFACES_FIELD")


def test_r04_surfaces_knob_parse(monkeypatch):
    fn = _attr(vr, "surfaces_live")
    cases = [
        (None, (False, False)), ("", (False, False)), (",,,", (False, False)),
        ("fashion", (False, False)), ("skincare;makeup", (False, False)),
        ("skincare", (True, False)), (" Makeup , SKINCARE ", (True, True)),
        ("makeup,fragrances,electronics", (False, True)),
    ]
    for knob, (sk, mk) in cases:
        _set(monkeypatch, "APP_SURFACES_LIVE", knob)
        out = fn()
        assert out == {"skincare": sk, "makeup": mk}, (knob, out)
        assert list(out) == ["skincare", "makeup"], out
        assert all(type(v) is bool for v in out.values()), out


# ---------------------------------------------------------------- /app/version R05-R08

def test_r05_version_surfaces_on(monkeypatch):
    client = _client()
    monkeypatch.setenv("APP_SURFACES_LIVE", "skincare")
    for v in ON:
        monkeypatch.setenv("ENABLE_SURFACES_FIELD", v)
        resp = client.get("/api/v1/app/version")
        assert resp.status_code == 200
        body = resp.json()
        assert body == dict(BASE_VERSION, surfaces={"skincare": True, "makeup": False}), (v, body)
        assert list(body) == FIVE + ["surfaces"], list(body)
        assert '"skincare":true' in resp.text and '"makeup":false' in resp.text, resp.text


def test_r05b_version_surfaces_on_knob_unset(monkeypatch):
    """R-SF1-33: flag ON, knob unset -> the key present with both values false."""
    client = _client()
    monkeypatch.setenv("ENABLE_SURFACES_FIELD", "true")
    for knob in (None, "", "  "):
        _set(monkeypatch, "APP_SURFACES_LIVE", knob)
        body = client.get("/api/v1/app/version").json()
        assert body.get("surfaces") == {"skincare": False, "makeup": False}, (knob, body)


def test_r06_version_key_order_both_flags(monkeypatch):
    monkeypatch.setenv("ENABLE_SURFACES_FIELD", "true")
    monkeypatch.setenv("ENABLE_FRAGRANCE_ONLY_GATE", "true")
    monkeypatch.setenv("APP_SURFACES_LIVE", "makeup")
    body = _client().get("/api/v1/app/version").json()
    assert list(body) == FIVE + ["surfaces", "categories_live"], list(body)
    assert body["surfaces"] == {"skincare": False, "makeup": True}


class _OsRecorder:
    def __init__(self, real):
        self._real = real
        self.names = []

    def getenv(self, name, *args, **kwargs):
        self.names.append(name)
        return self._real.getenv(name, *args, **kwargs)

    def __getattr__(self, item):
        return getattr(self._real, item)


@pytest.mark.parametrize("gate", [None, "true"])
@pytest.mark.parametrize("off", OFF)
def test_p07_version_off_identity(monkeypatch, off, gate):
    _full_config(monkeypatch, v2="true", surfaces=off)
    _set(monkeypatch, "ENABLE_FRAGRANCE_ONLY_GATE", gate)
    recorder = _OsRecorder(vr.os)
    monkeypatch.setattr(vr, "os", recorder)
    resp = _client().get("/api/v1/app/version")
    assert resp.status_code == 200
    expected = dict(BASE_VERSION)
    if gate:
        expected["categories_live"] = ["fragrances"]
    assert resp.json() == expected, resp.json()
    assert list(resp.json()) == list(expected)
    assert "APP_SURFACES_LIVE" not in recorder.names, recorder.names
    assert "APP_MIN_VERSION" in recorder.names  # the recorder is live


def test_r08_unknown_chip_never_on_wire(monkeypatch):
    monkeypatch.setenv("ENABLE_SURFACES_FIELD", "true")
    monkeypatch.setenv("APP_SURFACES_LIVE", "skincare,fashion,makeup,FRAGRANCES,electronics")
    body = _client().get("/api/v1/app/version").json()
    assert "surfaces" in body, body
    assert set(body["surfaces"]) == {"skincare", "makeup"}, body
    assert body["surfaces"] == {"skincare": True, "makeup": True}


# ---------------------------------------------------------------- /feedback OFF pins P10-P12

P10_BODIES = [
    ("empty", {}, None, MISSING_USEFUL),
    ("bad_cid", {"comparison_id": "bad"}, None, MISSING_USEFUL),
    ("new_no_useful", {"identity_correct": "correct", "source": "contact"}, None, MISSING_USEFUL),
    ("useful_null", {"useful": None}, None, PFX + "useful: Input should be a valid boolean"),
    ("useful_str", {"useful": "maybe"}, None,
     PFX + "useful: Input should be a valid boolean, unable to interpret input"),
    ("list", [1], None,
     "Validation error: body: Input should be a valid dictionary or object to extract fields from"),
    ("str", "x", None,
     "Validation error: body: Input should be a valid dictionary or object to extract fields from"),
    ("null", None, b"null", "Validation error: body: Field required"),
    ("bad_json", None, b"{", PFX + "1: JSON decode error"),
    ("two_errs", {"useful": True, "mattered_most": ["bogus"], "comparison_id": "bad"}, None,
     PFX + "comparison_id: Value error, comparison_id must be a valid UUID"),
    ("cs_long", {"useful": True, "change_suggestion": "x" * 1001}, None,
     PFX + "change_suggestion: String should have at most 1000 characters"),
]

P10_MODEL = {
    "empty": [{"type": "missing", "loc": ["useful"], "msg": "Field required", "input": {}}],
    "bad_cid": [
        {"type": "missing", "loc": ["useful"], "msg": "Field required",
         "input": {"comparison_id": "bad"}},
        {"type": "value_error", "loc": ["comparison_id"],
         "msg": "Value error, comparison_id must be a valid UUID", "input": "bad",
         "ctx": {"error": "comparison_id must be a valid UUID"}},
    ],
    "new_no_useful": [{"type": "missing", "loc": ["useful"], "msg": "Field required",
                       "input": {"identity_correct": "correct", "source": "contact"}}],
    "useful_null": [{"type": "bool_type", "loc": ["useful"],
                     "msg": "Input should be a valid boolean", "input": None}],
    "useful_str": [{"type": "bool_parsing", "loc": ["useful"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": "maybe"}],
}


@pytest.mark.parametrize("off", OFF)
def test_p10_feedback_off_422_bytes(monkeypatch, save_rec, off):
    _full_config(monkeypatch, v2=off)
    client = _client()
    for name, body, raw, error in P10_BODIES:
        resp = _post_feedback(client, body=body, raw=raw)
        _assert_envelope(resp, 422, error)
    for name, expected in P10_MODEL.items():
        data = [b for n, b, _r, _e in P10_BODIES if n == name][0]
        assert _model_errors(fr.FeedbackRequest, data) == expected, name
    assert save_rec == []


EXTRAS_BODY = {"useful": True, "correction": "x" * 500, "compare_request_id": "zzz",
               "source": "bogus", "identity_correct": "bogus", "wrong_side": 7,
               "preference": "x"}


@pytest.mark.parametrize("off", OFF)
def test_p11_feedback_off_accepts_and_drops(monkeypatch, save_rec, off):
    _full_config(monkeypatch, v2=off)
    resp = _post_feedback(_client(), body=EXTRAS_BODY)
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == {"success": True, "message": "Feedback received"}
    assert len(save_rec) == 1, save_rec
    assert [k for k, _v in save_rec[0]] == BASE_SAVE_KWARGS, save_rec[0]
    assert dict(save_rec[0]) == {
        "user_id": None, "comparison_id": None, "useful": True, "mattered_most": [],
        "change_suggestion": None, "access_token": None, "winner_correct": None,
        "price_correct": None, "specs_correct": None,
    }


@pytest.mark.parametrize("off", OFF)
def test_p12_feedback_off_stored_row(monkeypatch, run_ff, off):
    _full_config(monkeypatch, v2=off)
    rec = _recording_client()
    monkeypatch.setattr(fs, "get_supabase_client", lambda: rec)
    body = {"useful": True, "mattered_most": ["price"], "comparison_id": UUID,
            "change_suggestion": "s", "winner_correct": "correct",
            "identity_correct": "wrong", "wrong_side": "first", "preference": "second",
            "correction": CORRECTION, "source": "contact", "compare_request_id": UUID2}
    resp = _post_feedback(_client(), body=body)
    assert resp.status_code == 200, resp.text[:300]
    out = run_ff()
    assert out == [{"success": True, "id": "sf1-row"}], out
    record = _record_of(rec)
    assert record == {"useful": True, "mattered_most": ["price"], "comparison_id": UUID,
                      "change_suggestion": "s", "winner_correct": "correct"}, record
    assert list(record) == ["useful", "mattered_most", "comparison_id", "change_suggestion",
                            "winner_correct"]


# ---------------------------------------------------------------- /feedback ON R13-R16

@pytest.mark.parametrize("on", ON)
def test_r13_feedback_on_accepts_v2(monkeypatch, save_rec, on):
    _full_config(monkeypatch, v2=on)
    body = {"identity_correct": "wrong", "wrong_side": "first", "preference": "second",
            "correction": "  " + CORRECTION + "  ", "compare_request_id": UUID.upper()}
    resp = _post_feedback(_client(), body=body)
    assert resp.status_code == 200, resp.text[:300]
    assert len(save_rec) == 1
    kw = dict(save_rec[0])
    for name in BASE_SAVE_KWARGS:
        assert name in kw, name
    expected = {"useful": None, "identity_correct": "wrong", "wrong_side": "first",
                "preference": "second", "correction": CORRECTION, "source": "result",
                "compare_request_id": UUID}
    for name, value in expected.items():
        assert kw.get(name, "<absent>") == value, (name, kw.get(name, "<absent>"))


def _assert_v2_signature():
    params = inspect.signature(fs.save_feedback).parameters
    missing = [n for n in NEW_SAVE_KWARGS if n not in params]
    assert not missing, "save_feedback lacks %s" % missing
    for n in NEW_SAVE_KWARGS:
        assert params[n].default is None, n


def test_r14_feedback_on_stored_row(monkeypatch):
    _assert_v2_signature()
    monkeypatch.setenv("ENABLE_FEEDBACK_V2", "true")
    rec = _recording_client()
    monkeypatch.setattr(fs, "get_supabase_client", lambda: rec)
    out = asyncio.run(fs.save_feedback(
        user_id=None, comparison_id=UUID, useful=None, mattered_most=[],
        identity_correct="wrong", wrong_side="both", preference="neither",
        correction=CORRECTION, source="result", compare_request_id=UUID2))
    assert out["success"] is True, out
    record = _record_of(rec)
    assert "useful" not in record, record
    assert record == {"mattered_most": [], "comparison_id": UUID, "identity_correct": "wrong",
                      "wrong_side": "both", "preference": "neither", "correction": CORRECTION,
                      "source": "result", "compare_request_id": UUID2}, record
    rec2 = _recording_client()
    monkeypatch.setattr(fs, "get_supabase_client", lambda: rec2)
    asyncio.run(fs.save_feedback(user_id=None, comparison_id=None, useful=False,
                                 mattered_most=[], source="contact"))
    assert _record_of(rec2) == {"useful": False, "mattered_most": [], "source": "contact"}


def _err(resp):
    assert resp.status_code == 422, (resp.status_code, resp.text[:300])
    return resp.json()["error"]


def test_r15_feedback_on_422s(monkeypatch, save_rec):
    _full_config(monkeypatch, v2="true")
    client = _client()
    ok = _post_feedback(client, body={"useful": True, "correction": "   "})
    assert ok.status_code == 200, ok.text[:300]
    assert dict(save_rec[-1]).get("correction", "<absent>") is None, save_rec[-1]
    assert _err(_post_feedback(client, body={"useful": True, "correction": "x" * 81})) == (
        PFX + "correction: String should have at most 80 characters")
    for field, bad in (("identity_correct", "maybe"), ("wrong_side", "third"),
                       ("preference", "both"), ("source", "admin")):
        msg = _err(_post_feedback(client, body={"useful": True, field: bad}))
        assert msg.startswith(PFX + field + ": Input should be "), (field, msg)
    assert _err(_post_feedback(client, body={"useful": True, "compare_request_id": "bad"})) == (
        PFX + "compare_request_id: Value error, compare_request_id must be a valid UUID")
    assert _err(_post_feedback(client, body={"useful": "maybe"})) == (
        PFX + "useful: Input should be a valid boolean, unable to interpret input")


def test_r15b_correction_control_chars_and_raw_cap(monkeypatch, save_rec):
    """R-SF1-34: C0 + DEL refused under ON; the raw input capped at 1,000 chars before strip."""
    _full_config(monkeypatch, v2="true")
    client = _client()
    padded = " " * 990 + "Dior"
    ok = _post_feedback(client, body={"useful": True, "correction": padded})
    assert ok.status_code == 200, ok.text[:300]
    assert dict(save_rec[-1]).get("correction") == "Dior", save_rec[-1]
    for bad in ("Dior" + chr(0), "a" + chr(0x7F) + "b", "a" + chr(9) + "b",
                "a" + chr(10) + "b", chr(0x1B) + "Dior", " " * 1001 + "Dior"):
        msg = _err(_post_feedback(client, body={"useful": True, "correction": bad}))
        assert msg.startswith(PFX + "correction: "), (repr(bad[:8]), msg)


def test_r15c_empty_body_under_on(monkeypatch, save_rec):
    """R-SF1-32: ON, a body with no answer field -> 422 'feedback body carries no answer'."""
    _full_config(monkeypatch, v2="true")
    client = _client()
    for body in ({}, {"source": "contact", "compare_request_id": UUID, "comparison_id": UUID2},
                 {"correction": "   "}, {"mattered_most": []}, {"change_suggestion": ""}):
        msg = _err(_post_feedback(client, body=body))
        assert msg.endswith(NO_ANSWER), (body, msg)
    for body in ({"preference": "unsure"}, {"useful": False}, {"mattered_most": ["price"]},
                 {"change_suggestion": "s"}, {"winner_correct": "wrong"},
                 {"correction": CORRECTION}):
        resp = _post_feedback(client, body=body)
        assert resp.status_code == 200, (body, resp.text[:300])
    assert save_rec and len(save_rec) == 6


def test_r16_feedback_on_contact_source(monkeypatch, save_rec):
    _full_config(monkeypatch, v2="true")
    client = _client()
    assert _post_feedback(client, body={"useful": True, "source": "contact"}).status_code == 200
    assert _post_feedback(client, body={"useful": True}).status_code == 200
    assert len(save_rec) == 2, save_rec
    assert dict(save_rec[0]).get("source") == "contact", save_rec[0]
    assert dict(save_rec[1]).get("source") == "result", save_rec[1]


# ---------------------------------------------------------------- /events R20-R27

def test_r20_event_types_appended():
    names = list(fr.VALID_EVENT_TYPES)
    assert names[:31] == BASE_EVENTS_31
    assert names[31:] == NEW_EVENTS, names[31:]
    assert len(set(names)) == len(names)


def test_r21_property_allowlist_dict():
    table = getattr(fr, "EVENT_PROPERTY_ALLOWLIST", None)
    assert table == ALLOWLIST, table
    for name, keys in table.items():
        assert isinstance(keys, frozenset), name
        assert name in fr.VALID_EVENT_TYPES, name


def _batch(*items):
    return {"events": [dict(i) for i in items]}


VALID_FOUR = [
    ("category_coming_soon_tap", {"category": "skincare", "extra": 1}, {"category": "skincare"}),
    ("share_channel_selected", {"channel": "sms", "label": "x"}, {"channel": "sms"}),
    ("share_target_opened", {"share_target": "more", "n": 2}, {"share_target": "more"}),
    ("store_cta_tap", {"merchant_id": "noon.com", "url": "sf1-url-value", "price": 9},
     {"merchant_id": "noon.com"}),
]


@pytest.mark.parametrize("off", OFF)
def test_r22_new_types_accepted_off(monkeypatch, events_rec, logs, off):
    """The widening AND the filter are unflagged (R-SF1-38): OFF filters the four types."""
    _full_config(monkeypatch, v2=off)
    body = _batch(*[{"event_type": t, "event_data": d} for t, d, _e in VALID_FOUR])
    resp = _client().post("/api/v1/events", json=body)
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == {"success": True, "message": "4 events received"}
    assert events_rec == [[{"user_id": None, "event_type": t, "event_data": e,
                            "comparison_id": None} for t, _d, e in VALID_FOUR]], events_rec
    msgs = [r.getMessage() for r in logs if r.getMessage().startswith("[EVENTS]")]
    assert sorted(msgs) == sorted("[EVENTS] properties dropped type=%s n=%d"
                                  % (t, len(d) - len(e)) for t, d, e in VALID_FOUR), msgs


@pytest.mark.parametrize("state", [None, "true"])
def test_r23_property_filter(monkeypatch, events_rec, logs, state):
    _full_config(monkeypatch, v2=state)
    body = _batch(
        {"event_type": "store_cta_tap",
         "event_data": {"merchant_id": "noon.com", "url": "sf1-url-value", "price": 9}},
        {"event_type": "share_target_opened", "event_data": {"share_target": "sms", "x": 1}},
        {"event_type": "share", "event_data": {"a": 1, "b": "sf1-keep"}},
    )
    resp = _client().post("/api/v1/events", json=body)
    assert resp.status_code == 200, resp.text[:300]
    data = [e["event_data"] for e in events_rec[0]]
    assert data == [{"merchant_id": "noon.com"}, {"share_target": "sms"},
                    {"a": 1, "b": "sf1-keep"}], data
    events_lines = [r for r in logs if r.getMessage().startswith("[EVENTS]")]
    msgs = [r.getMessage() for r in events_lines]
    assert msgs == ["[EVENTS] properties dropped type=store_cta_tap n=2",
                    "[EVENTS] properties dropped type=share_target_opened n=1"], msgs
    assert all(r.levelno == logging.INFO for r in events_lines)
    for r in logs:
        text = _formatted(r)
        for value in ("noon.com", "sf1-url-value", "sf1-keep"):
            assert value not in text, text


VALUE_CASES = (
    [("store_cta_tap", "merchant_id", v, True) for v in ("noon.com", "bh.boutiqaat.com")]
    + [("store_cta_tap", "merchant_id", v, False)
       for v in ("https://noon.com/p/1", "Noon.com", "m1", 9, "noon.com/path", "", None)]
    + [("category_coming_soon_tap", "category", v, True) for v in ("skincare", "makeup")]
    + [("category_coming_soon_tap", "category", v, False)
       for v in ("fragrances", "SKINCARE", 1, "")]
    + [("share_target_opened", "share_target", v, True) for v in NINE]
    + [("share_target_opened", "share_target", v, False) for v in ("facebook", "SMS", 3)]
    + [("share_channel_selected", "channel", v, True) for v in NINE]
    + [("share_channel_selected", "channel", v, False) for v in ("facebook", "Copy", True)]
)


@pytest.mark.parametrize("state", [None, "true"])
@pytest.mark.parametrize("etype,key,value,kept", VALUE_CASES)
def test_r23b_property_value_rules(monkeypatch, events_rec, logs, state, etype, key, value,
                                   kept):
    """R-SF1-20: a value failing its rule drops the key and counts in the INFO n."""
    _full_config(monkeypatch, v2=state)
    resp = _client().post("/api/v1/events",
                          json=_batch({"event_type": etype, "event_data": {key: value}}))
    assert resp.status_code == 200, resp.text[:300]
    stored = events_rec[0][0]["event_data"]
    msgs = [r.getMessage() for r in logs if r.getMessage().startswith("[EVENTS]")]
    if kept:
        assert stored == {key: value}, stored
        assert msgs == [], msgs
    else:
        assert stored == {}, stored
        assert msgs == ["[EVENTS] properties dropped type=%s n=1" % etype], msgs


@pytest.mark.parametrize("off", OFF)
def test_p24_events_off_identity(monkeypatch, events_rec, off):
    _full_config(monkeypatch, v2=off)
    body = _batch({"event_type": "save", "event_data": {"a": 1}, "compare_request_id": "bad"},
                  {"event_type": "share", "comparison_id": UUID, "compare_request_id": UUID2})
    resp = _client().post("/api/v1/events", json=body)
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == {"success": True, "message": "2 events received"}
    assert events_rec == [[
        {"user_id": None, "event_type": "save", "event_data": {"a": 1}, "comparison_id": None},
        {"user_id": None, "event_type": "share", "event_data": {}, "comparison_id": UUID},
    ]], events_rec
    for d in events_rec[0]:
        assert list(d) == ["user_id", "event_type", "event_data", "comparison_id"]


def test_r25_events_on_request_id(monkeypatch, events_rec):
    _full_config(monkeypatch, v2="true")
    client = _client()
    body = _batch({"event_type": "save", "compare_request_id": UUID.upper()},
                  {"event_type": "share"})
    resp = client.post("/api/v1/events", json=body)
    assert resp.status_code == 200, resp.text[:300]
    first, second = events_rec[0]
    assert first.get("compare_request_id") == UUID, first
    assert "compare_request_id" not in second, second
    bad = client.post("/api/v1/events",
                      json=_batch({"event_type": "save", "compare_request_id": "bad"}))
    assert bad.status_code == 422, bad.text[:300]
    assert bad.json()["error"] == EVENT_CRID_MSG, bad.json()["error"]
    rec = _recording_client()
    monkeypatch.setattr(fs, "get_supabase_client", lambda: rec)
    asyncio.run(fs.track_events_batch([
        {"event_type": "save", "event_data": {}, "compare_request_id": UUID},
        {"event_type": "share", "event_data": {}},
    ]))
    records = _record_of(rec)
    assert records[0].get("compare_request_id") == UUID, records
    assert "compare_request_id" not in records[1], records


@pytest.mark.parametrize("off", OFF)
def test_p26_events_batch_off_records(monkeypatch, off):
    _full_config(monkeypatch, v2=off)
    rec = _recording_client()
    monkeypatch.setattr(fs, "get_supabase_client", lambda: rec)
    asyncio.run(fs.track_events_batch([
        {"user_id": "sf1-p26", "event_type": "save", "event_data": {"a": 1},
         "comparison_id": UUID},
        {"event_type": "share", "event_data": {}, "session_id": "sf1-session"},
        {"user_id": None, "event_type": "tab_switch", "comparison_id": None},
    ]))
    assert _record_of(rec) == [
        {"event_type": "save", "event_data": {"a": 1}, "user_id": "sf1-p26",
         "comparison_id": UUID},
        {"event_type": "share", "event_data": {}, "session_id": "sf1-session"},
        {"event_type": "tab_switch", "event_data": {}},
    ]


def test_r27_size_cap_before_filter(monkeypatch, events_rec):
    _full_config(monkeypatch, v2="true")
    big = {"merchant_id": "noon.com", "blob": "v" * 10_001}
    resp = _client().post("/api/v1/events",
                          json=_batch({"event_type": "store_cta_tap", "event_data": big}))
    assert resp.status_code == 422, resp.text[:300]
    assert resp.json()["error"] == EVENT_SIZE_MSG, resp.json()["error"][:300]
    assert events_rec == []


# ---------------------------------------------------------------- /referrals/share P30-P33

class _FakeReferralService:
    calls: list = []

    def __init__(self, access_token=None):
        pass

    async def create_invite(self, **kw):
        _FakeReferralService.calls.append(kw)
        return {"invite_id": "sf1-invite", "share_link": "sf1-link"}


@pytest.fixture
def share_client(monkeypatch):
    from app.api.auth_routes import get_current_user

    _FakeReferralService.calls = []
    monkeypatch.setattr(rr, "ReferralService", _FakeReferralService)
    app.dependency_overrides[get_current_user] = lambda: {"id": "sf1-share", "access_token": None}
    try:
        yield _client()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


P30_VALUES = ["sms", "email", "more", "foo", 5, None, "WhatsApp", True]


@pytest.mark.parametrize("off", OFF)
def test_p30_share_off_422_bytes(monkeypatch, share_client, off):
    _full_config(monkeypatch, v2=off)
    for value in P30_VALUES:
        resp = share_client.post("/api/v1/referrals/share",
                                 json={"comparison_id": "sf1-c1", "share_target": value})
        _assert_envelope(resp, 422, SHARE_BASE)
        expected = [{"type": "literal_error", "loc": ["share_target"],
                     "msg": "Input should be " + SHARE_EXPECTED, "input": value,
                     "ctx": {"expected": SHARE_EXPECTED}}]
        got = _model_errors(rr.ShareRequest, {"comparison_id": "sf1-c1", "share_target": value})
        assert got == expected, (value, got)
    for value in SIX:
        resp = share_client.post("/api/v1/referrals/share",
                                 json={"comparison_id": "sf1-c1", "share_target": value})
        assert resp.status_code == 201, (value, resp.text[:200])
    assert [c["share_target"] for c in _FakeReferralService.calls] == list(SIX)


def test_r31_share_on_widened(monkeypatch, share_client):
    _full_config(monkeypatch, v2="true")
    for value in ("sms", "email", "more"):
        resp = share_client.post("/api/v1/referrals/share",
                                 json={"comparison_id": "sf1-c1", "share_target": value})
        assert resp.status_code == 201, (value, resp.text[:300])
    assert [c["share_target"] for c in _FakeReferralService.calls] == ["sms", "email", "more"]
    resp = share_client.post("/api/v1/referrals/share",
                             json={"comparison_id": "sf1-c1", "share_target": "facebook"})
    _assert_envelope(resp, 422, SHARE_V2)


class _Reached(Exception):
    pass


def _service_probe(target):
    svc = rs.ReferralService.__new__(rs.ReferralService)
    svc.client = MagicMock()

    async def _ensure(_uid):
        raise _Reached()

    svc.ensure_code_for_user = _ensure
    try:
        asyncio.run(svc.create_invite(referrer_user_id="sf1-r32", comparison_id="sf1-c",
                                      share_target=target))
    except Exception as exc:  # noqa: BLE001 - the probe classifies the outcome
        return exc
    return None


def test_r32_service_share_targets(monkeypatch):
    monkeypatch.delenv("ENABLE_FEEDBACK_V2", raising=False)
    off = _service_probe("sms")
    assert isinstance(off, ValueError), off
    assert str(off) == ("share_target 'sms' not in allowed set ['copy', 'other', 'snapchat', "
                        "'telegram', 'whatsapp', 'x']"), str(off)
    monkeypatch.setenv("ENABLE_FEEDBACK_V2", "true")
    for target in ("sms", "email", "more", "whatsapp"):
        got = _service_probe(target)
        assert isinstance(got, _Reached), (target, repr(got))
    bad = _service_probe("facebook")
    assert isinstance(bad, ValueError), bad
    assert str(bad) == ("share_target 'facebook' not in allowed set ['copy', 'email', 'more', "
                        "'other', 'sms', 'snapchat', 'telegram', 'whatsapp', 'x']"), str(bad)


@pytest.mark.parametrize("state", [None, "true"])
def test_p33_code_redeem_other(monkeypatch, state):
    _full_config(monkeypatch, v2=state)
    client = MagicMock()
    found = MagicMock()
    found.data = {"id": "sf1-referrer", "referral_code": "QR-ABCDEF"}
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = found
    inserted = MagicMock()
    inserted.data = [{"id": "sf1-invite"}]
    client.table.return_value.insert.return_value.execute.return_value = inserted
    monkeypatch.setattr(rs, "get_admin_supabase_client", lambda: client)
    out = asyncio.run(rs.resolve_code_to_invite_id("QR-ABCDEF", "sf1-invitee"))
    assert out == "sf1-invite"
    assert _record_of(client)["share_target"] == "other"


# ---------------------------------------------------------------- log_search R40-R42

def _log_search_record(monkeypatch, **kw):
    rec = _recording_client()
    monkeypatch.setattr(ds, "get_supabase_client", lambda: rec)
    asyncio.run(ds.log_search("sf1 query", input_type="text", user_id="sf1-ls",
                              products_found=["a", "b"], success=True, error_message=None,
                              cost=0.01, duration_ms=12, **kw))
    return _record_of(rec)


BASE_LOG_RECORD = {"query": "sf1 query", "input_type": "text", "products_found": ["a", "b"],
                   "success": True, "cost": 0.01, "duration_ms": 12, "user_id": "sf1-ls"}


def test_r40_log_search_on_bound_id(monkeypatch):
    _full_config(monkeypatch, v2="true")
    rid = str(uuid.uuid4())
    tokens = _bind_request_id(rid.upper())
    try:
        assert rc.compare_request_id() == rid
        record = _log_search_record(monkeypatch)
    finally:
        rc.reset_request_context(tokens)
    assert record.get("compare_request_id") == rid, record
    assert record == dict(BASE_LOG_RECORD, compare_request_id=rid), record
    record = _log_search_record(monkeypatch)
    assert "compare_request_id" not in record, record


@pytest.mark.parametrize("marker", [None, "true"])
@pytest.mark.parametrize("off", OFF)
def test_p41_log_search_off_identity(monkeypatch, off, marker):
    _full_config(monkeypatch, v2=off)
    _set(monkeypatch, "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", marker)
    calls = []
    real = rc.compare_request_id

    def _rec():
        calls.append(1)
        return real()

    monkeypatch.setattr(rc, "compare_request_id", _rec)
    tokens = _bind_request_id(str(uuid.uuid4()))
    try:
        record = _log_search_record(monkeypatch, is_synthetic=True)
    finally:
        rc.reset_request_context(tokens)
    expected = dict(BASE_LOG_RECORD)
    if marker:
        expected["is_synthetic"] = True
    assert record == expected, record
    assert list(record) == list(expected)
    assert calls == [], calls


def test_p42_log_search_signature():
    assert list(inspect.signature(ds.log_search).parameters) == LOG_SEARCH_PARAMS


# ---------------------------------------------------------------- migrations R50-R54

def _one(folder, num):
    return sorted(p.name for p in folder.glob(num + "_*.sql"))


def _code(path):
    text = path.read_text(encoding="ascii")
    lines = [ln for ln in text.split("\n") if not ln.strip().startswith("--")]
    return re.sub(r"\s+", " ", "\n".join(lines)).strip().lower()


def _nospace(path):
    return re.sub(r"\s+", "", _code(path))


def _dollar_parts(text):
    """(outside, bodies): the $$-delimited DO bodies and the rest of a compact text."""
    parts = text.split("$$")
    return parts[0::2], parts[1::2]


F046 = "046_comparison_feedback_v2.sql"
F049 = "049_share_target_and_request_ids.sql"


def _require(path):
    assert path.exists(), "%s is missing" % path.name
    return path


def test_r50_migration_files_once():
    assert _one(MIG, "046") == [F046], _one(MIG, "046")
    assert _one(MIG, "049") == [F049], _one(MIG, "049")
    assert _one(ROLLBACK, "046") == [F046], _one(ROLLBACK, "046")
    assert _one(ROLLBACK, "049") == [F049], _one(ROLLBACK, "049")
    for path in (MIG / F046, MIG / F049, ROLLBACK / F046, ROLLBACK / F049):
        # A Windows autocrlf checkout turns LF into CRLF (the r06 lexicon noise class):
        # the committed bytes are LF, so only a CR outside a CRLF pair is refused here.
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        assert all(b < 128 for b in raw), path.name
        assert b"\r" not in raw, path.name
        assert raw.endswith(b"\n"), path.name
        code = _code(path)
        assert code.startswith("begin;"), path.name
        assert code.count("begin;") == 1 and code.count("commit;") == 1, path.name
    for path in (MIG / F046, MIG / F049):
        code = _code(path)
        # R-SF1-30 / R-SF1-31: lock_timeout first inside the transaction, NOTIFY at the end.
        assert code.startswith("begin; set local lock_timeout = '5s';"), code[:80]
        assert code.endswith("commit; notify pgrst, 'reload schema';"), code[-80:]


def test_r51_046_text():
    path = _require(MIG / F046)
    code = _code(path)
    ns = _nospace(path)
    for col, typ in (("identity_correct", "text null"), ("wrong_side", "text null"),
                     ("preference", "text null"), ("correction", "text null"),
                     ("source", "text not null default 'result'"),
                     ("compare_request_id", "uuid null")):
        assert "add column if not exists %s %s" % (col, typ) in code, col
    for name, check in (
            ("identity_correct", "check(identity_correctin('correct','wrong','unsure'))"),
            ("wrong_side", "check(wrong_sidein('first','second','both'))"),
            ("preference", "check(preferencein('first','second','neither','unsure'))"),
            ("correction", "check(char_length(correction)<=80)"),
            ("source", "check(sourcein('result','contact'))")):
        assert "addconstraintcomparison_feedback_%s_check%s" % (name, check) in ns, name
    assert ("createindexifnotexistsidx_comparison_feedback_requestonpublic.comparison_feedback"
            "(compare_request_id)wherecompare_request_idisnotnull") in ns
    outside, bodies = _dollar_parts(code)
    assert all("drop not null" not in seg for seg in outside), "DROP NOT NULL outside a DO"
    guarded = [b for b in bodies if "alter column useful drop not null" in b]
    assert len(guarded) == 1, len(guarded)
    assert "is_nullable" in guarded[0]
    # R-SF1-36: the comment the rollback reads, written only where NOT NULL was dropped.
    assert "comment on column public.comparison_feedback.useful is 'sf1_dropped_not_null'" in (
        guarded[0])
    assert code.count("sf1_dropped_not_null") == 1
    assert "add column if not exists price_correct" not in code
    for forbidden in ("create function", "create or replace function", "security definer",
                      "create policy", "grant ", "revoke "):
        assert forbidden not in code, forbidden


def test_r52_049_text():
    path = _require(MIG / F049)
    code = _code(path)
    ns = _nospace(path)
    _outside, bodies = _dollar_parts(ns)
    guard = [b for b in bodies if "dropconstraint%i" in b]
    assert len(guard) == 1, len(guard)
    body = guard[0]
    for needle in ("pg_constraint", "contype='c'", "ilike'%share_target%'", "<>1then",
                   "raiseexception"):
        assert needle in body, needle
    # exactly one live CHECK or RAISE, before the dynamic DROP (never "= 0").
    check_at = body.index("<>1then")
    assert body.index("raiseexception", check_at) < body.index("dropconstraint%i"), body
    assert "raise exception" in code
    nine = ",".join("'%s'" % v for v in NINE)
    assert "addconstraintreferral_invites_share_target_checkcheck(share_targetin(%s))" % nine in ns
    assert code.count("add column if not exists compare_request_id uuid null") == 2
    assert "alter table public.user_events add column if not exists compare_request_id" in code
    assert "alter table public.search_logs add column if not exists compare_request_id" in code
    for idx, table in (("idx_user_events_request", "user_events"),
                       ("idx_search_logs_request", "search_logs")):
        assert ("createindexifnotexists%sonpublic.%s(compare_request_id)"
                "wherecompare_request_idisnotnull" % (idx, table)) in ns, idx
    for forbidden in ("create function", "create or replace function", "security definer",
                      "create policy", "grant ", "revoke "):
        assert forbidden not in code, forbidden


def test_r53_rollbacks():
    r46 = _code(_require(ROLLBACK / F046))
    for col in ("identity_correct", "wrong_side", "preference", "correction", "source",
                "compare_request_id"):
        assert "drop column if exists %s" % col in r46, col
    assert r46.count("drop column") == 6, r46.count("drop column")
    outside, bodies = _dollar_parts(r46)
    assert all("set not null" not in seg for seg in outside)
    gated = [b for b in bodies if "alter column useful set not null" in b]
    assert len(gated) == 1, len(gated)
    assert "sf1_dropped_not_null" in gated[0] and "col_description" in gated[0], gated[0]
    assert "useful is null" in gated[0] and "raise exception" in gated[0]
    assert "comment on column public.comparison_feedback.useful is null" in r46
    r49 = _code(_require(ROLLBACK / F049))
    r49ns = re.sub(r"\s+", "", r49)
    assert "raise exception" in r49
    assert "share_targetin('sms','email','more')" in r49ns
    six = ",".join("'%s'" % v for v in SIX)
    assert "addconstraintreferral_invites_share_target_checkcheck(share_targetin(%s))" % six in (
        r49ns)
    assert "alter table public.user_events drop column if exists compare_request_id" in r49
    assert "alter table public.search_logs drop column if exists compare_request_id" in r49


def _values(ns, col):
    m = re.search(r"check\(%sin\(([^)]*)\)\)" % col, ns)
    assert m, col
    return tuple(v.strip("'") for v in m.group(1).split(","))


def test_r54_parity():
    ns46 = _nospace(_require(MIG / F046))
    assert _values(ns46, "identity_correct") == tuple(_attr(fr, "IDENTITY_VALUES"))
    assert _values(ns46, "wrong_side") == tuple(_attr(fr, "WRONG_SIDE_VALUES"))
    assert _values(ns46, "preference") == tuple(_attr(fr, "PREFERENCE_VALUES"))
    assert _values(ns46, "source") == tuple(_attr(fr, "FEEDBACK_SOURCES"))
    assert _attr(fr, "CORRECTION_MAX_CHARS") == 80
    ns49 = _nospace(_require(MIG / F049))
    widened = _values(ns49, "share_target")
    assert widened == NINE
    assert tuple(_attr(rr, "WIDENED_SHARE_TARGETS")) == NINE
    assert tuple(_attr(rr, "BASE_SHARE_TARGETS")) == SIX
    assert sorted(_attr(rs, "_WIDENED_SHARE_TARGETS")) == sorted(NINE)
    assert typing.get_args(_attr(rr, "ShareTargetV2")) == NINE
    assert typing.get_args(rr.ShareTarget) == SIX


# ---------------------------------------------------------------- privacy P60-P62, R70

def test_p60_correction_readers():
    text = (ROOT / "scripts" / "cron_learning.py").read_text(encoding="utf-8")
    m = re.search(r'^FEEDBACK_COLUMNS\s*=\s*"([^"]*)"', text, re.M)
    assert m, "FEEDBACK_COLUMNS literal not found"
    cols = m.group(1).split(",")
    assert "correction" not in cols and "compare_request_id" not in cols, cols
    literal = re.compile(r"""["']correction["']""")
    star = re.compile(r"""comparison_feedback["']\)\s*\.select\(\s*["']\*["']""")
    hits, stars = set(), set()
    for folder in ("app", "scripts"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            src = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(ROOT).as_posix()
            if literal.search(src):
                hits.add(rel)
            if star.search(src):
                stars.add(rel)
    assert hits <= {"app/api/feedback_routes.py", "app/services/feedback_service.py"}, hits
    assert stars == set(), stars


def test_p61_log_hygiene_on(monkeypatch, logs, run_ff):
    _full_config(monkeypatch, v2="true")
    rec = _recording_client()
    monkeypatch.setattr(fs, "get_supabase_client", lambda: rec)
    client = _client()
    resp = _post_feedback(client, body={"useful": True, "correction": CORRECTION,
                                        "compare_request_id": UUID})
    assert resp.status_code == 200, resp.text[:300]
    resp = client.post("/api/v1/events", json=_batch(
        {"event_type": "store_cta_tap", "compare_request_id": UUID2,
         "event_data": {"merchant_id": "noon.com", "url": "sf1-url-value"}}))
    assert resp.status_code == 200, resp.text[:300]
    run_ff()
    rid = str(uuid.uuid4())
    tokens = _bind_request_id(rid)
    try:
        record = _log_search_record(monkeypatch)
    finally:
        rc.reset_request_context(tokens)
    assert record.get("compare_request_id") == rid
    for r in logs:
        text = _formatted(r)
        for value in (CORRECTION, UUID, UUID2, rid, "noon.com", "sf1-url-value",
                      "skincare,makeup"):
            assert value not in text, (value, text[:200])


def _api_error():
    from postgrest.exceptions import APIError

    return APIError({"message": "null value in column", "code": "23502",
                     "details": "Failing row contains (sf1-row, " + CORRECTION + ", "
                                + MARKER + ").", "hint": None})


@pytest.mark.parametrize("state", [None, "true"])
def test_r70_failure_arms_log_constants(monkeypatch, logs, state):
    """R-SF1-27: the three except arms log constants only, in both flag states."""
    _full_config(monkeypatch, v2=state)
    monkeypatch.setattr(fs, "get_supabase_client", lambda: _recording_client(_api_error()))
    monkeypatch.setattr(ds, "get_supabase_client", lambda: _recording_client(_api_error()))
    out = asyncio.run(fs.save_feedback(user_id=None, comparison_id=None, useful=True,
                                       mattered_most=[], change_suggestion=CORRECTION))
    assert out["success"] is False
    asyncio.run(fs.track_events_batch([{"event_type": "save", "event_data": {"m": MARKER}}]))
    asyncio.run(ds.log_search(MARKER, user_id="sf1-r70"))
    warn = [r for r in logs if r.levelno >= logging.WARNING]
    by_name = {r.name for r in warn}
    assert {fs.logger.name, ds.logger.name} <= by_name, by_name
    fb = [r.getMessage() for r in warn if r.name == fs.logger.name]
    assert "[FEEDBACK] save failed type=APIError code=23502" in fb, fb
    for r in warn:
        msg = r.getMessage()
        assert "type=APIError" in msg and "code=23502" in msg, msg
    for r in logs:
        text = _formatted(r)
        assert MARKER not in text, text[:300]
        assert CORRECTION not in text, text[:300]
        assert "Failing row" not in text, text[:300]


def test_p62_client_line_and_fence():
    src = ROOT / "SmartCompareApp" / "src"
    needle = "trackEvent('category_coming_soon_tap'"
    hits = []
    for path in sorted(src.rglob("*.ts*")):
        count = path.read_text(encoding="utf-8", errors="replace").count(needle)
        if count:
            hits.append((path.relative_to(ROOT).as_posix(), count))
    assert hits == [("SmartCompareApp/src/screens/HomeScreen.tsx", 1)], hits
    assert "category_coming_soon_tap" in fr.VALID_EVENT_TYPES
    launch = (src / "services" / "launchSurfaces.ts").read_text(encoding="utf-8")
    assert "category_coming_soon_tap" not in launch
