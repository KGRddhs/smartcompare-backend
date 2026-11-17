"""M13-29 — anonymous feedback/events writes use the service-role client with a
client-supplied comparison_id, so a caller can pin rows to another user's
comparison_id harvested from a share link (RLS can't stop a service-role write).

Load-bearing fix: UUID-validate comparison_id at the Pydantic layer (rejecting
arbitrary strings before they reach PostgREST).

INC-SEC-1 (C2, C2b, ruling R-C): migration 055 removes every app-role write to
comparison_feedback, so the server writes with its own key for every caller and the
user client is never built; feedback_service._owned_comparison_id keeps the ownership
rule (a comparison_id the caller may not name is dropped, the row is still written).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.api.feedback_routes import FeedbackRequest, EventItem

_VALID_UUID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture()
def client():
    return TestClient(app)


# ---- Pydantic-layer UUID validation ----------------------------------------

def test_model_rejects_non_uuid_comparison_id():
    with pytest.raises(ValidationError):
        FeedbackRequest(useful=True, comparison_id="not-a-uuid")


def test_model_rejects_injection_string_comparison_id():
    with pytest.raises(ValidationError):
        FeedbackRequest(useful=True, comparison_id="1 OR 1=1")


def test_model_accepts_valid_uuid():
    m = FeedbackRequest(useful=True, comparison_id=_VALID_UUID)
    assert m.comparison_id == _VALID_UUID


def test_model_accepts_none_and_empty():
    assert FeedbackRequest(useful=True).comparison_id is None
    assert FeedbackRequest(useful=True, comparison_id="").comparison_id is None


# ---- EventItem / POST /events: the higher-volume vector the finding names ---
# (closeout gap: only FeedbackRequest was validated in the front-door wave; the
# /events path writes evt.comparison_id to user_events via the service-role
# client, so an unvalidated string is the same forgery/injection primitive.)

def test_event_item_rejects_non_uuid_comparison_id():
    with pytest.raises(ValidationError):
        EventItem(event_type="save", comparison_id="not-a-uuid")


def test_event_item_rejects_injection_string_comparison_id():
    with pytest.raises(ValidationError):
        EventItem(event_type="save", comparison_id="1 OR 1=1")


def test_event_item_accepts_valid_uuid_none_empty():
    assert EventItem(event_type="save", comparison_id=_VALID_UUID).comparison_id == _VALID_UUID
    assert EventItem(event_type="save").comparison_id is None
    assert EventItem(event_type="save", comparison_id="").comparison_id is None


def test_http_events_invalid_comparison_id_is_422(client, monkeypatch):
    """POST /events with a forged/injection comparison_id is rejected at
    validation before track_events_batch ever writes to user_events."""
    batch = AsyncMock(return_value=[{"success": True}])
    monkeypatch.setattr("app.api.feedback_routes.track_events_batch", batch)
    resp = client.post(
        "/api/v1/events",
        json={"events": [{"event_type": "save", "comparison_id": "1 OR 1=1"}]},
    )
    assert resp.status_code == 422, resp.text
    batch.assert_not_awaited()


# ---- HTTP: invalid comparison_id -> 422, valid -> 200 (fire-and-forget) -----

def test_http_invalid_comparison_id_is_422(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.feedback_routes.save_feedback", AsyncMock(return_value={"success": True})
    )
    resp = client.post("/api/v1/feedback", json={"useful": True, "comparison_id": "abc123"})
    assert resp.status_code == 422, resp.text


def test_http_valid_comparison_id_ok(client, monkeypatch):
    saver = AsyncMock(return_value={"success": True})
    monkeypatch.setattr("app.api.feedback_routes.save_feedback", saver)
    resp = client.post(
        "/api/v1/feedback", json={"useful": True, "comparison_id": _VALID_UUID}
    )
    assert resp.status_code == 200, resp.text


# ---- user-scoped client when authenticated ---------------------------------

@pytest.mark.asyncio
async def test_save_feedback_uses_service_client_when_authenticated(monkeypatch):
    """INC-SEC-1 C2 (R-C, inverted): an authenticated write (user_id + access_token)
    goes through the service-role client; the RLS-scoped user client is never built."""
    user_client = MagicMock()
    admin_client = MagicMock()
    admin_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "row-1"}]
    )
    got = {}

    def _fake_user_client(tok):
        got["user_tok"] = tok
        return user_client

    monkeypatch.setattr(
        "app.services.database_service.get_user_supabase_client", _fake_user_client
    )
    monkeypatch.setattr("app.services.feedback_service.get_supabase_client", lambda: admin_client)

    from app.services.feedback_service import save_feedback

    await save_feedback(
        user_id="u1", comparison_id=_VALID_UUID, useful=True,
        mattered_most=[], access_token="tok-abc",
    )
    assert "user_tok" not in got
    user_client.table.assert_not_called()
    admin_client.table.assert_called_with("comparison_feedback")


@pytest.mark.asyncio
async def test_save_feedback_uses_admin_client_when_anonymous(monkeypatch):
    """An anonymous write (no access_token) still uses the service-role client —
    byte-identical to today, so anonymous feedback keeps working."""
    admin_client = MagicMock()
    admin_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "row-1"}]
    )
    monkeypatch.setattr("app.services.feedback_service.get_supabase_client", lambda: admin_client)

    from app.services.feedback_service import save_feedback

    await save_feedback(user_id=None, comparison_id=None, useful=True, mattered_most=[])
    admin_client.table.assert_called_with("comparison_feedback")
