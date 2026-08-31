"""M13-29 — anonymous feedback/events writes use the service-role client with a
client-supplied comparison_id, so a caller can pin rows to another user's
comparison_id harvested from a share link (RLS can't stop a service-role write).

Load-bearing fix: UUID-validate comparison_id at the Pydantic layer (rejecting
arbitrary strings before they reach PostgREST). Defense-in-depth: route the write
through get_user_supabase_client(access_token) when the caller is authenticated.

NOTE (follow-up, NOT fixed here): migrations/010_enable_rls.sql:48-58 INSERT
policies allow user_id IS NULL and never constrain comparison_id, so the
user-scoped client alone does NOT stop the forgery — the UUID validation is the
load-bearing control. Migrations are out of scope for this wave.
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
async def test_save_feedback_uses_user_client_when_authenticated(monkeypatch):
    """An authenticated write (user_id + access_token) goes through the
    RLS-scoped client, not the service-role client."""
    user_client = MagicMock()
    user_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "row-1"}]
    )
    admin_client = MagicMock()
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
    assert got.get("user_tok") == "tok-abc"
    user_client.table.assert_called_with("comparison_feedback")
    admin_client.table.assert_not_called()


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
