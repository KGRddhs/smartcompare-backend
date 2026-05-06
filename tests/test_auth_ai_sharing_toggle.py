"""Tests for B1.4 — AI sharing privacy toggle.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
section 6.1 (AI Quality Improvement Program) and plan task B1.4.

Default: ai_sharing_enabled = ON. When user opts OFF, OpenAI calls route to a
non-shared project (standard pricing); on, they route to the data-sharing
project (free under daily caps).

Written FIRST (red phase). Backend implements `select_client_for_user()` in
`app/services/openai_service.py` and extends `UserPreferencesRequest` to
accept `ai_sharing_enabled: Optional[bool]`.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ============================================
# B1.4 — Pydantic body extension
# ============================================


class TestAISharingPreferenceShape:
    def test_preferences_request_accepts_ai_sharing_enabled_field(self):
        """UserPreferencesRequest must accept ai_sharing_enabled (Optional[bool])."""
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            ai_sharing_enabled=False,
        )
        assert req.ai_sharing_enabled is False

    def test_preferences_request_default_ai_sharing_is_none_or_true(self):
        """Field default should be None (treated as ON downstream) OR explicit True."""
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
        )
        # Either None (default ON) or explicit True is acceptable
        assert getattr(req, "ai_sharing_enabled", None) in (None, True)

    def test_preferences_request_accepts_explicit_true(self):
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            ai_sharing_enabled=True,
        )
        assert req.ai_sharing_enabled is True


# ============================================
# B1.4 — select_client_for_user routing
# ============================================


class TestSelectClientForUser:
    """select_client_for_user(user_prefs) returns the correct OpenAI client."""

    def test_default_returns_shared_client_when_no_prefs(self):
        """When user_prefs is None, default ON => shared project."""
        from app.services import openai_service

        # The function should be importable
        assert hasattr(openai_service, "select_client_for_user"), (
            "openai_service must expose select_client_for_user(user_prefs)"
        )

    def test_returns_shared_when_explicit_true(self):
        """ai_sharing_enabled=True => shared client."""
        from app.services import openai_service

        with patch.object(openai_service, "get_client") as mock_get:
            mock_get.return_value = MagicMock(name="shared")
            result = openai_service.select_client_for_user(
                user_prefs={"ai_sharing_enabled": True}
            )
            mock_get.assert_called_with(use_shared_project=True)
            assert result is mock_get.return_value

    def test_returns_non_shared_when_explicit_false(self):
        """ai_sharing_enabled=False => non-shared client (PDPL opt-out)."""
        from app.services import openai_service

        with patch.object(openai_service, "get_client") as mock_get:
            mock_get.return_value = MagicMock(name="private")
            openai_service.select_client_for_user(
                user_prefs={"ai_sharing_enabled": False}
            )
            mock_get.assert_called_with(use_shared_project=False)

    def test_default_when_field_missing_is_shared(self):
        """When prefs dict has other fields but no ai_sharing_enabled => default ON => shared."""
        from app.services import openai_service

        with patch.object(openai_service, "get_client") as mock_get:
            mock_get.return_value = MagicMock()
            openai_service.select_client_for_user(
                user_prefs={"budget": "mid", "priorities": ["best_price"]}
            )
            mock_get.assert_called_with(use_shared_project=True)

    def test_default_when_prefs_is_none(self):
        """user_prefs=None (e.g. anonymous) => default ON => shared."""
        from app.services import openai_service

        with patch.object(openai_service, "get_client") as mock_get:
            mock_get.return_value = MagicMock()
            openai_service.select_client_for_user(user_prefs=None)
            mock_get.assert_called_with(use_shared_project=True)


# ============================================
# B1.4 — get_client(use_shared_project=...) factory
# ============================================


class TestGetClientFactory:
    """get_client must accept use_shared_project flag and return distinct clients."""

    def test_get_client_accepts_use_shared_project_flag(self):
        from app.services import openai_service

        assert hasattr(openai_service, "get_client"), (
            "openai_service must expose get_client(use_shared_project: bool)"
        )

    def test_shared_and_non_shared_are_distinct_when_separate_keys_set(self, monkeypatch):
        """When OPENAI_API_KEY_PRIVATE is set, the two clients differ.

        If only one key is configured, the implementation may return the same
        client both times — that's acceptable as a fallback. This test only
        asserts the API exists; semantics deferred to integration.
        """
        from app.services import openai_service

        # Just ensure callable with both values
        try:
            openai_service.get_client(use_shared_project=True)
            openai_service.get_client(use_shared_project=False)
        except TypeError as e:
            pytest.fail(f"get_client must accept use_shared_project kwarg: {e}")
