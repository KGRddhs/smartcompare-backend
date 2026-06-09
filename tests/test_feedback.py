"""
Tests for feedback and event tracking endpoints + service.
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient


# ============================================
# Service unit tests
# ============================================

class TestFeedbackService:
    """Tests for app.services.feedback_service functions."""

    @pytest.mark.asyncio
    async def test_save_feedback_success(self):
        """save_feedback inserts record and returns success."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "fb-123"}]

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import save_feedback
            result = await save_feedback(
                user_id="user-1",
                comparison_id="comp-1",
                useful=True,
                mattered_most=["price", "specs"],
                change_suggestion="More detail on battery",
            )
        assert result["success"] is True
        assert result["id"] == "fb-123"
        insert_arg = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_arg["useful"] is True
        assert insert_arg["user_id"] == "user-1"
        assert insert_arg["comparison_id"] == "comp-1"
        assert insert_arg["mattered_most"] == ["price", "specs"]
        assert insert_arg["change_suggestion"] == "More detail on battery"

    @pytest.mark.asyncio
    async def test_save_feedback_anonymous(self):
        """save_feedback works without user_id."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "fb-anon"}]
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import save_feedback
            result = await save_feedback(
                user_id=None, comparison_id=None,
                useful=False, mattered_most=[],
            )
        assert result["success"] is True
        insert_arg = mock_client.table.return_value.insert.call_args[0][0]
        assert "user_id" not in insert_arg
        assert "comparison_id" not in insert_arg

    @pytest.mark.asyncio
    async def test_save_feedback_db_error(self):
        """save_feedback returns failure on DB error, never raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB down")

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import save_feedback
            result = await save_feedback(
                user_id=None, comparison_id=None,
                useful=True, mattered_most=[],
            )
        assert result["success"] is False
        assert "DB down" in result["error"]

    @pytest.mark.asyncio
    async def test_track_event_success(self):
        """track_event inserts a single event."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "evt-1"}]
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import track_event
            result = await track_event(
                user_id="u1", event_type="save",
                event_data={"product": "iPhone"}, comparison_id="c1",
            )
        assert result["success"] is True
        assert result["id"] == "evt-1"

    @pytest.mark.asyncio
    async def test_track_event_db_error(self):
        """track_event returns failure on DB error, never raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("timeout")

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import track_event
            result = await track_event(
                user_id=None, event_type="share", event_data={},
            )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_track_events_batch_success(self):
        """track_events_batch inserts multiple events."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "e1"}, {"id": "e2"}]
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import track_events_batch
            results = await track_events_batch([
                {"event_type": "save", "event_data": {}, "user_id": "u1"},
                {"event_type": "share", "event_data": {"via": "whatsapp"}},
            ])
        assert len(results) == 2
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_track_events_batch_db_error(self):
        """track_events_batch returns failure on DB error, never raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("fail")

        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            from app.services.feedback_service import track_events_batch
            results = await track_events_batch([
                {"event_type": "save", "event_data": {}},
            ])
        assert results[0]["success"] is False


# ============================================
# Route / endpoint tests
# ============================================

@pytest.fixture
def client():
    """Create a test client with mocked Supabase."""
    from app.main import app
    return TestClient(app)


class TestFeedbackEndpoint:
    """Tests for POST /api/v1/feedback."""

    def test_feedback_success_anonymous(self, client):
        """Anonymous feedback returns 200."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={
                "useful": True,
                "mattered_most": ["price"],
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_feedback_with_all_fields(self, client):
        """Feedback with all optional fields returns 200."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={
                "useful": False,
                "comparison_id": "00000000-0000-0000-0000-000000000001",
                "mattered_most": ["specs", "reviews", "brand"],
                "change_suggestion": "Add warranty info",
            })
        assert resp.status_code == 200

    def test_feedback_missing_useful_field(self, client):
        """Missing required 'useful' field returns 422."""
        resp = client.post("/api/v1/feedback", json={
            "mattered_most": ["price"],
        })
        assert resp.status_code == 422

    def test_feedback_invalid_mattered_most(self, client):
        """Invalid mattered_most item returns 422."""
        resp = client.post("/api/v1/feedback", json={
            "useful": True,
            "mattered_most": ["invalid_item"],
        })
        assert resp.status_code == 422

    def test_feedback_empty_mattered_most_ok(self, client):
        """Empty mattered_most list is valid."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={
                "useful": True,
            })
        assert resp.status_code == 200

    def test_feedback_returns_200_even_on_db_error(self, client):
        """Endpoint returns 200 even if DB save would fail (fire-and-forget)."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB err")
        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            resp = client.post("/api/v1/feedback", json={
                "useful": True,
            })
        # Fire-and-forget: the endpoint returns before the task runs
        assert resp.status_code == 200


class TestEventsEndpoint:
    """Tests for POST /api/v1/events."""

    def test_events_single_event(self, client):
        """Single event in batch returns 200."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={
                "events": [{"event_type": "save", "event_data": {"product": "iPhone"}}],
            })
        assert resp.status_code == 200
        assert "1 events received" in resp.json()["message"]

    def test_events_multiple_events(self, client):
        """Multiple events in batch returns 200."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={
                "events": [
                    {"event_type": "save"},
                    {"event_type": "share"},
                    {"event_type": "tab_switch", "event_data": {"tab": "specs"}},
                ],
            })
        assert resp.status_code == 200
        assert "3 events received" in resp.json()["message"]

    def test_events_invalid_event_type(self, client):
        """Invalid event_type returns 422."""
        resp = client.post("/api/v1/events", json={
            "events": [{"event_type": "hacker_event"}],
        })
        assert resp.status_code == 422

    def test_events_empty_batch_ok(self, client):
        """Empty events list is valid."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={"events": []})
        assert resp.status_code == 200
        assert "0 events received" in resp.json()["message"]

    def test_events_batch_too_large(self, client):
        """More than 50 events returns 422."""
        events = [{"event_type": "save"} for _ in range(51)]
        resp = client.post("/api/v1/events", json={"events": events})
        assert resp.status_code == 422

    def test_events_missing_events_field(self, client):
        """Missing required 'events' field returns 422."""
        resp = client.post("/api/v1/events", json={})
        assert resp.status_code == 422

    def test_events_returns_200_even_on_db_error(self, client):
        """Endpoint returns 200 even if DB batch would fail (fire-and-forget)."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB err")
        with patch("app.services.feedback_service.get_supabase_client", return_value=mock_client):
            resp = client.post("/api/v1/events", json={
                "events": [{"event_type": "save"}],
            })
        assert resp.status_code == 200

    def test_all_valid_event_types_accepted(self, client):
        """Every valid event type is accepted."""
        valid_types = [
            "save", "share", "source_click", "tab_switch",
            "feedback_submit", "result_view_duration",
            # B.1 F3.5 — pain-workflow signals fired from StreamingProductCard
            "spec_expand", "result_abandon", "screenshot",
        ]
        with patch("app.services.feedback_service.get_supabase_client"):
            for et in valid_types:
                resp = client.post("/api/v1/events", json={
                    "events": [{"event_type": et}],
                })
                assert resp.status_code == 200, f"Failed for event_type={et}"


class TestPainWorkflowEventTypes:
    """B.1 F3.5 — the 3 pain-workflow signal types fired from
    StreamingProductCard must be accepted by POST /api/v1/events so the
    backend pain_workflow derivation (B.2) has raw user_events to read."""

    def test_spec_expand_accepted(self, client):
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={
                "events": [{
                    "event_type": "spec_expand",
                    "event_data": {"stage": "specs", "hidden_spec_count": 4},
                    "comparison_id": "00000000-0000-0000-0000-000000000001",
                }],
            })
        assert resp.status_code == 200

    def test_result_abandon_accepted(self, client):
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={
                "events": [{
                    "event_type": "result_abandon",
                    "event_data": {"stage": "prices"},
                }],
            })
        assert resp.status_code == 200

    def test_screenshot_accepted(self, client):
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={
                "events": [{
                    "event_type": "screenshot",
                    "event_data": {"stage": "verdict"},
                }],
            })
        assert resp.status_code == 200

    def test_pain_workflow_types_in_constant(self):
        """The allowlist constant itself must contain all 3 (guards against a
        future edit that drops one and silently breaks the mobile wire)."""
        from app.api.feedback_routes import VALID_EVENT_TYPES
        for et in ("spec_expand", "result_abandon", "screenshot"):
            assert et in VALID_EVENT_TYPES, f"{et} missing from VALID_EVENT_TYPES"

    def test_all_valid_mattered_most_accepted(self, client):
        """Every valid mattered_most item is accepted."""
        valid_items = ["price", "specs", "reviews", "brand", "value", "warranty", "ratings"]
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={
                "useful": True,
                "mattered_most": valid_items,
            })
        assert resp.status_code == 200


# ============================================
# Additional coverage: edge cases
# ============================================

class TestFeedbackEdgeCases:
    """Additional coverage for feedback edge cases."""

    def test_feedback_invalid_json_body(self, client):
        """Non-JSON body returns 422."""
        resp = client.post(
            "/api/v1/feedback",
            content="not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_feedback_extra_fields_ignored(self, client):
        """Extra unexpected fields should be ignored (Pydantic default)."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={
                "useful": True,
                "mattered_most": ["price"],
                "unexpected_field": "should be ignored",
                "another_extra": 42,
            })
        assert resp.status_code == 200

    def test_feedback_long_change_suggestion(self, client):
        """change_suggestion respects max_length=1000."""
        text_at_limit = "A" * 1000
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={
                "useful": True,
                "change_suggestion": text_at_limit,
            })
        assert resp.status_code == 200

    def test_feedback_change_suggestion_over_limit(self, client):
        """change_suggestion over 1000 chars is rejected."""
        long_text = "A" * 1001
        resp = client.post("/api/v1/feedback", json={
            "useful": True,
            "change_suggestion": long_text,
        })
        assert resp.status_code == 422

    def test_events_batch_exactly_50(self, client):
        """Exactly 50 events (at the limit) should succeed."""
        events = [{"event_type": "save"} for _ in range(50)]
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/events", json={"events": events})
        assert resp.status_code == 200
        assert "50 events received" in resp.json()["message"]

    def test_events_invalid_json_body(self, client):
        """Non-JSON body returns 422."""
        resp = client.post(
            "/api/v1/events",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_feedback_useful_false_accepted(self, client):
        """Useful=False is a valid value."""
        with patch("app.services.feedback_service.get_supabase_client"):
            resp = client.post("/api/v1/feedback", json={"useful": False})
        assert resp.status_code == 200

    def test_feedback_useful_null_rejected(self, client):
        """Useful=null should be rejected (field is required bool)."""
        resp = client.post("/api/v1/feedback", json={"useful": None})
        assert resp.status_code == 422
