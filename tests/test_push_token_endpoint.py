"""Tests for PUT /api/v1/auth/push-token + notifications_enabled +
notification_types in UserPreferencesRequest.

Closes the F5.4 backend asks from frontend-referral:
1. PUT /api/v1/auth/push-token writes ``users.expo_push_token``
2. UserPreferencesRequest accepts notifications_enabled (Optional[bool])
3. UserPreferencesRequest accepts notification_types (Optional[dict],
   field_validator whitelists 3 keys: decision_insight,
   cohort_curiosity, decision_retrospective)
4. ReengagementService detectors short-circuit when their respective
   sub-toggle is OFF (read from user.preferences.notification_types).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================
# PUT /api/v1/auth/push-token — endpoint shape
# ============================================


class TestPushTokenEndpoint:
    def test_route_is_registered(self):
        """PUT /api/v1/auth/push-token must exist (non-404 even without auth)."""
        resp = client.put(
            "/api/v1/auth/push-token",
            json={"expo_push_token": "ExponentPushToken[ABC]"},
        )
        assert resp.status_code != 404, (
            f"PUT /api/v1/auth/push-token missing — got {resp.status_code}"
        )

    def test_unauthorized_request_rejected(self):
        resp = client.put(
            "/api/v1/auth/push-token",
            json={"expo_push_token": "ExponentPushToken[ABC]"},
        )
        assert resp.status_code in (401, 403, 422)

    def test_authorized_persists_token_via_user_client(self):
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-1", "email": "u@t.com", "access_token": "tok"}

        captured_updates = []

        def capture_update(payload):
            captured_updates.append(payload)
            inner = MagicMock()
            inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
            return inner

        # Mock both clients so we can verify which one was used.
        user_client = MagicMock()
        user_client.table.return_value.update.side_effect = capture_update
        admin_client = MagicMock()  # should NOT be used (RLS path required)

        app.dependency_overrides[get_current_user] = fake_user
        try:
            with patch(
                "app.api.auth_routes.get_user_supabase_client",
                return_value=user_client,
            ), patch(
                "app.api.auth_routes.get_admin_supabase_client",
                return_value=admin_client,
            ):
                resp = client.put(
                    "/api/v1/auth/push-token",
                    json={"expo_push_token": "ExponentPushToken[REAL]"},
                    headers={"Authorization": "Bearer tok"},
                )
            assert resp.status_code == 200, resp.text
            assert len(captured_updates) == 1
            assert captured_updates[0] == {"expo_push_token": "ExponentPushToken[REAL]"}
        finally:
            app.dependency_overrides.clear()

    def test_empty_token_rejected(self):
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "u", "email": "u@t.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            resp = client.put(
                "/api/v1/auth/push-token",
                json={"expo_push_token": ""},
                headers={"Authorization": "Bearer tok"},
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_oversized_token_rejected(self):
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "u", "email": "u@t.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            resp = client.put(
                "/api/v1/auth/push-token",
                json={"expo_push_token": "x" * 300},  # > 256 max_length
                headers={"Authorization": "Bearer tok"},
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ============================================
# UserPreferencesRequest extension
# ============================================


class TestNotificationsEnabledField:
    def test_field_accepts_bool(self):
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            notifications_enabled=False,
        )
        assert req.notifications_enabled is False

    def test_default_is_none(self):
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
        )
        assert getattr(req, "notifications_enabled", "MISSING") is None


class TestNotificationTypesField:
    def test_accepts_three_known_keys(self):
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            notification_types={
                "decision_insight": True,
                "cohort_curiosity": False,
                "decision_retrospective": True,
            },
        )
        assert req.notification_types == {
            "decision_insight": True,
            "cohort_curiosity": False,
            "decision_retrospective": True,
        }

    def test_unknown_keys_stripped_by_validator(self):
        """Defense in depth — extra keys silently dropped."""
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            notification_types={
                "decision_insight": True,
                "malicious_field": "danger",
                "another_unknown": 42,
            },
        )
        # Only the known key survives
        assert "malicious_field" not in req.notification_types
        assert "another_unknown" not in req.notification_types
        assert req.notification_types == {"decision_insight": True}

    def test_values_coerced_to_bool(self):
        """Truthiness coerced — 1 / 0 / "x" / "" all become True/False."""
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            notification_types={
                "decision_insight": 1,
                "cohort_curiosity": 0,
                "decision_retrospective": "yes",
            },
        )
        assert req.notification_types["decision_insight"] is True
        assert req.notification_types["cohort_curiosity"] is False
        assert req.notification_types["decision_retrospective"] is True


# ============================================
# ReengagementService honours sub-toggles
# ============================================


class TestReengagementSubToggles:
    """Each detector should short-circuit when its specific sub-toggle is OFF.
    Master ``notifications_enabled=False`` is enforced upstream by the cron's
    eligibility query, but defense-in-depth: ``evaluate(user)`` should also
    skip if all detectors are off OR the master toggle is off in the user
    preferences blob.
    """

    @pytest.mark.asyncio
    async def test_master_toggle_off_returns_none(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {
            "id": "u",
            "preferences": {"notifications_enabled": False},
        }
        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock) as mock_insight, \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock) as mock_curiosity, \
             patch.object(svc, "_check_decision_retrospective", new_callable=AsyncMock) as mock_retro:
            result = await svc.evaluate(user)
            assert result is None
            # When master is off, NO detector should be called.
            mock_insight.assert_not_called()
            mock_curiosity.assert_not_called()
            mock_retro.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.reengagement_service._flag_on", return_value=True)
    async def test_decision_insight_skipped_when_subtoggle_off(self, _mock_flag):
        # Bundle D Task 2.B.7 — `_flag_on()` is the global kill-switch.
        # It's fail-CLOSED (False unless `ENABLE_REENGAGEMENT_PUSHES`
        # explicitly set in env). The 3 sub-toggle tests don't care
        # about the flag; they care about per-detector gating.
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {
            "id": "u",
            "preferences": {
                "notifications_enabled": True,
                "notification_types": {
                    "decision_insight": False,
                    "cohort_curiosity": True,
                    "decision_retrospective": True,
                },
            },
        }
        # Cohort detector returns a payload — it should win since insight is off.
        cohort_payload = {"event_type": "cohort_curiosity", "title": "T", "body": "B", "deep_link_url": "u://"}

        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value={"event_type": "decision_insight"}) as mock_insight, \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock, return_value=cohort_payload):
            result = await svc.evaluate(user)
            assert result is not None
            assert result["event_type"] == "cohort_curiosity"
            # Insight detector must have been SKIPPED (sub-toggle off).
            mock_insight.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_subtoggles_off_returns_none(self):
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {
            "id": "u",
            "preferences": {
                "notifications_enabled": True,
                "notification_types": {
                    "decision_insight": False,
                    "cohort_curiosity": False,
                    "decision_retrospective": False,
                },
            },
        }
        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False):
            result = await svc.evaluate(user)
            assert result is None

    @pytest.mark.asyncio
    @patch("app.services.reengagement_service._flag_on", return_value=True)
    async def test_missing_preferences_treats_as_all_on(self, _mock_flag):
        """Backwards compat — users with no notification_types blob keep
        the current behaviour (all detectors run). Bundle D Task 2.B.7
        mocks `_flag_on=True` because the kill-switch is OFF in test env
        (fail-CLOSED)."""
        from app.services.reengagement_service import ReengagementService

        svc = ReengagementService()
        user = {"id": "u"}  # no preferences key

        insight_payload = {"event_type": "decision_insight", "title": "T", "body": "B", "deep_link_url": "u://"}
        with patch.object(svc, "_recent_push", new_callable=AsyncMock, return_value=False), \
             patch.object(svc, "_check_decision_insight", new_callable=AsyncMock, return_value=insight_payload) as mock_insight, \
             patch.object(svc, "_check_cohort_curiosity", new_callable=AsyncMock, return_value=None), \
             patch.object(svc, "_check_decision_retrospective", new_callable=AsyncMock, return_value=None):
            result = await svc.evaluate(user)
            assert result is not None
            assert result["event_type"] == "decision_insight"
            mock_insight.assert_called_once()


# ============================================
# PUT /api/v1/auth/reengagement-subs (Bundle D Task 2.B.7, R18)
# ============================================


class TestReengagementSubsEndpoint:
    """Per anchor R18 — new endpoint exposes the 3 user-facing toggle labels
    (plural keys: decision_insights / peer_decision_updates /
    decision_retrospectives) and translates server-side to the existing
    singular keys in users.preferences.notification_types.
    """

    def test_route_is_registered(self):
        """PUT /api/v1/auth/reengagement-subs must exist (non-404 unauth)."""
        resp = client.put(
            "/api/v1/auth/reengagement-subs",
            json={
                "decision_insights": True,
                "peer_decision_updates": True,
                "decision_retrospectives": True,
            },
        )
        assert resp.status_code != 404, (
            f"PUT /api/v1/auth/reengagement-subs missing — got {resp.status_code}"
        )

    def test_unauthorized_request_rejected(self):
        resp = client.put(
            "/api/v1/auth/reengagement-subs",
            json={
                "decision_insights": True,
                "peer_decision_updates": True,
                "decision_retrospectives": True,
            },
        )
        assert resp.status_code in (401, 403, 422)

    def test_all_three_fields_required(self):
        """Pydantic rejects partial bodies — every toggle must be specified."""
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "u", "email": "u@t.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            resp = client.put(
                "/api/v1/auth/reengagement-subs",
                json={"decision_insights": True},  # missing 2 fields
                headers={"Authorization": "Bearer tok"},
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_authorized_translates_plural_keys_to_singular(self):
        """Backend writes singular `decision_insight` / `cohort_curiosity` /
        `decision_retrospective` keys so reengagement_service short-circuits
        keep working unchanged."""
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-1", "email": "u@t.com", "access_token": "tok"}

        captured_updates = []

        # The endpoint does read-modify-write: SELECT then UPDATE.
        select_result = MagicMock(data={"preferences": {"budget": "mid"}})

        def capture_update(payload):
            captured_updates.append(payload)
            inner = MagicMock()
            inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
            return inner

        user_client = MagicMock()
        user_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = select_result
        user_client.table.return_value.update.side_effect = capture_update

        admin_client = MagicMock()  # should NOT be used

        app.dependency_overrides[get_current_user] = fake_user
        try:
            with patch(
                "app.api.auth_routes.get_user_supabase_client",
                return_value=user_client,
            ), patch(
                "app.api.auth_routes.get_admin_supabase_client",
                return_value=admin_client,
            ):
                resp = client.put(
                    "/api/v1/auth/reengagement-subs",
                    json={
                        "decision_insights": True,
                        "peer_decision_updates": False,
                        "decision_retrospectives": True,
                    },
                    headers={"Authorization": "Bearer tok"},
                )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            # Body returns the SINGULAR backend keys
            assert data["notification_types"] == {
                "decision_insight": True,
                "cohort_curiosity": False,
                "decision_retrospective": True,
            }
            # The UPDATE preserved other preference keys (budget)
            assert len(captured_updates) == 1
            written_prefs = captured_updates[0]["preferences"]
            assert written_prefs["budget"] == "mid"
            assert written_prefs["notification_types"] == {
                "decision_insight": True,
                "cohort_curiosity": False,
                "decision_retrospective": True,
            }
        finally:
            app.dependency_overrides.clear()

    def test_preserves_other_preferences_keys(self):
        """Read-modify-write must NOT blast other preferences fields."""
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-1", "email": "u@t.com", "access_token": "tok"}

        existing_prefs = {
            "budget": "premium",
            "priorities": ["price", "quality"],
            "lifestyle": ["gamer"],
            "brand_attitude": "function_first",
            "ai_sharing_enabled": True,
            "notifications_enabled": True,
        }
        select_result = MagicMock(data={"preferences": existing_prefs})
        captured_updates = []

        def capture_update(payload):
            captured_updates.append(payload)
            inner = MagicMock()
            inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
            return inner

        user_client = MagicMock()
        user_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = select_result
        user_client.table.return_value.update.side_effect = capture_update

        app.dependency_overrides[get_current_user] = fake_user
        try:
            with patch(
                "app.api.auth_routes.get_user_supabase_client",
                return_value=user_client,
            ):
                resp = client.put(
                    "/api/v1/auth/reengagement-subs",
                    json={
                        "decision_insights": False,
                        "peer_decision_updates": False,
                        "decision_retrospectives": False,
                    },
                    headers={"Authorization": "Bearer tok"},
                )
            assert resp.status_code == 200
            written = captured_updates[0]["preferences"]
            # All pre-existing keys preserved
            for k in ("budget", "priorities", "lifestyle", "brand_attitude",
                      "ai_sharing_enabled", "notifications_enabled"):
                assert k in written, f"key {k!r} dropped by read-modify-write"
            assert written["budget"] == "premium"
            assert written["priorities"] == ["price", "quality"]
            # And our 3 toggles are now all False
            assert written["notification_types"] == {
                "decision_insight": False,
                "cohort_curiosity": False,
                "decision_retrospective": False,
            }
        finally:
            app.dependency_overrides.clear()

    def test_non_bool_values_coerced(self):
        """`decision_insights: 1` / `0` / `"true"` should validate (Pydantic
        coerces) and end up as True/False in the written dict."""
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-1", "email": "u@t.com", "access_token": "tok"}

        select_result = MagicMock(data={"preferences": {}})
        captured_updates = []

        def capture_update(payload):
            captured_updates.append(payload)
            inner = MagicMock()
            inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
            return inner

        user_client = MagicMock()
        user_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = select_result
        user_client.table.return_value.update.side_effect = capture_update

        app.dependency_overrides[get_current_user] = fake_user
        try:
            with patch(
                "app.api.auth_routes.get_user_supabase_client",
                return_value=user_client,
            ):
                resp = client.put(
                    "/api/v1/auth/reengagement-subs",
                    json={
                        "decision_insights": 1,
                        "peer_decision_updates": 0,
                        "decision_retrospectives": True,
                    },
                    headers={"Authorization": "Bearer tok"},
                )
            assert resp.status_code == 200
            written_types = captured_updates[0]["preferences"]["notification_types"]
            assert written_types["decision_insight"] is True
            assert written_types["cohort_curiosity"] is False
            assert written_types["decision_retrospective"] is True
        finally:
            app.dependency_overrides.clear()
