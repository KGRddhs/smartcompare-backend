"""B1 (S80) -- the UNFLAGGED half (R-A1(a), R0-2): the two allowlist widenings and the
three optional 027 correctness fields on FeedbackRequest (spec section 5.2, the W3-1 pattern).

RED rows fail at base 81df2b64 on an AssertionError only (a 422/200 status or a missing
kwarg asserted through getattr / inspect); PIN rows are green at base. Hermetic: the
Supabase client is patched, every write is recorded in memory. Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import feedback_routes as fr
from app.main import app

NEW_MATTERED = ("wrong_product", "missing_info", "unclear_reasons", "slow", "wrong_winner", "unsure")
NEW_EVENTS = ("scan_start", "scan_identity_resolved", "scan_comparison_ready", "scan_failed",
              "scan_cancelled", "image_load_failed")
CORRECTNESS_FIELDS = ("winner_correct", "price_correct", "specs_correct")
CORRECTNESS_VALUES = ("correct", "wrong", "unsure")
# The base lists at 81df2b64 (recorded literals; F7 pins append-only).
BASE_MATTERED = ["price", "specs", "reviews", "brand", "value", "warranty", "ratings",
                 "accurate", "detailed", "fast"]
BASE_EVENTS = [
    "save", "share", "source_click", "tab_switch", "feedback_submit", "result_view_duration",
    "compare_entry_view", "compare_cancelled", "compare_entry_paywall_banner_view",
    "compare_entry_paywall_banner_tap", "compare_entry_content_block", "compare_entry_submit",
    "compare_entry_paste_split", "compare_entry_mode_autoswitch", "compare_entry_ready",
    "share_sheet_opened", "share_completed", "demographics_submitted", "demographics_dismissed",
    "onboarding_started", "onboarding_step_completed", "onboarding_completed",
    "spec_expand", "result_abandon", "screenshot",
]
DARK_ERA_EVENTS = ("compare_entry_view", "compare_entry_submit", "compare_entry_ready",
                   "share_sheet_opened", "onboarding_started", "spec_expand", "screenshot")
UUID = "12345678-1234-4123-8123-123456789abc"


def _done(value=None):
    async def _r():
        return value
    return _r()


@pytest.fixture(autouse=True)
def _limiter_off():
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prior


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def save_rec(monkeypatch):
    """Record every save_feedback call at the route (kwargs) and swallow the coroutine."""
    calls = []

    def _rec(**kw):
        calls.append(dict(kw))
        return _done({"success": True})

    def _ff(coro, label=None, **_k):
        coro.close()

    monkeypatch.setattr(fr, "save_feedback", _rec)
    monkeypatch.setattr(fr, "fire_and_forget", _ff)
    return calls


def _recording_client():
    resp = MagicMock()
    resp.data = [{"id": "fb-1"}]
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value = resp
    return client


def _record_of(client):
    return client.table.return_value.insert.call_args[0][0]


# ---------------------------------------------------------------- F1 / F2 (RED)

@pytest.mark.parametrize("value", NEW_MATTERED)
def test_b1_f1_new_mattered_most_values_accepted(client, value):
    with patch("app.services.feedback_service.get_supabase_client", return_value=_recording_client()):
        resp = client.post("/api/v1/feedback", json={"useful": False, "mattered_most": [value]})
    assert resp.status_code == 200, (value, resp.status_code, resp.text[:200])
    assert value in fr.VALID_MATTERED_MOST


@pytest.mark.parametrize("name", NEW_EVENTS)
def test_b1_f2_new_event_types_accepted(client, name):
    with patch("app.services.feedback_service.get_supabase_client", return_value=_recording_client()):
        resp = client.post("/api/v1/events", json={"events": [{"event_type": name, "event_data": {}}]})
    assert resp.status_code == 200, (name, resp.status_code, resp.text[:200])
    assert name in fr.VALID_EVENT_TYPES


# ---------------------------------------------------------------- F3 (RED)

@pytest.mark.parametrize("field", CORRECTNESS_FIELDS)
@pytest.mark.parametrize("value", CORRECTNESS_VALUES)
def test_b1_f3_correctness_fields_accepted_and_written(client, save_rec, field, value):
    resp = client.post("/api/v1/feedback", json={"useful": True, "mattered_most": ["price"], field: value})
    assert resp.status_code == 200, resp.text[:200]
    assert len(save_rec) == 1, save_rec
    assert save_rec[0].get(field) == value, (field, save_rec[0])
    # The REAL save_feedback writes the field into the record only when sent.
    from app.services import feedback_service as fs
    params = inspect.signature(fs.save_feedback).parameters
    assert field in params, sorted(params)
    rc = _recording_client()
    with patch("app.services.feedback_service.get_supabase_client", return_value=rc):
        out = asyncio.run(fs.save_feedback(user_id=None, comparison_id=None, useful=True,
                                           mattered_most=["price"], **{field: value}))
    assert out.get("success") is True, out
    record = _record_of(rc)
    assert record.get(field) == value, record
    for other in CORRECTNESS_FIELDS:
        if other != field:
            assert other not in record, record


# ---------------------------------------------------------------- F4 (RED)

@pytest.mark.parametrize("bad", ["maybe", 1, True])
def test_b1_f4_off_enum_value_422s(client, save_rec, bad):
    resp = client.post("/api/v1/feedback", json={"useful": True, "mattered_most": ["price"],
                                                 "winner_correct": bad})
    assert resp.status_code == 422, (bad, resp.status_code, resp.text[:200])
    body = resp.json()
    assert body.get("code") == "VALIDATION_ERROR" or "detail" in body, body
    assert save_rec == [], save_rec


# ---------------------------------------------------------------- F5 / F6 / F7 (PIN)

def test_b1_f5_four_field_body_record_identical():
    from app.services import feedback_service as fs
    rc = _recording_client()
    with patch("app.services.feedback_service.get_supabase_client", return_value=rc):
        out = asyncio.run(fs.save_feedback(user_id=None, comparison_id=UUID, useful=True,
                                           mattered_most=["price"], change_suggestion="x"))
    assert out.get("success") is True, out
    assert _record_of(rc) == {"useful": True, "mattered_most": ["price"], "comparison_id": UUID,
                              "change_suggestion": "x"}


def test_b1_f6_existing_pins_hold(client):
    with patch("app.services.feedback_service.get_supabase_client", return_value=_recording_client()):
        for value in BASE_MATTERED:
            assert client.post("/api/v1/feedback", json={"useful": True, "mattered_most": [value]}
                               ).status_code == 200, value
        assert client.post("/api/v1/feedback", json={"useful": True, "mattered_most": ["bogus"]}
                           ).status_code == 422
        assert client.post("/api/v1/feedback", json={"useful": True, "mattered_most": []}
                           ).status_code == 200
        assert client.post("/api/v1/events", json={"events": [{"event_type": "hacker_event"}]}
                           ).status_code == 422
    assert "comparison_wall_time" not in fr.VALID_EVENT_TYPES
    for name in DARK_ERA_EVENTS:
        assert name in fr.VALID_EVENT_TYPES, name


def test_b1_f7_allowlists_append_only():
    assert fr.VALID_MATTERED_MOST[:len(BASE_MATTERED)] == BASE_MATTERED
    assert fr.VALID_EVENT_TYPES[:len(BASE_EVENTS)] == BASE_EVENTS
    assert len(set(fr.VALID_MATTERED_MOST)) == len(fr.VALID_MATTERED_MOST)
    assert len(set(fr.VALID_EVENT_TYPES)) == len(fr.VALID_EVENT_TYPES)
