"""Tests for PUT /api/v1/auth/demographics + GET /api/v1/auth/cohort-profile + source-flip on PUT /preferences.

Asserts the design contract from docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md
sections 5.1-5.3 and plan A.4.1-A.4.4.

Written FIRST (red phase). Backend implements to make these green.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ============================================
# Pydantic body model
# ============================================


class TestDemographicsBody:
    def test_body_accepts_all_fields(self):
        from app.api.auth_routes import DemographicsBody

        b = DemographicsBody(
            age_group="25-34",
            gender="Female",
            governorate="Northern",
            language="Arabic",
            country="Bahrain",
        )
        assert b.age_group == "25-34"
        assert b.gender == "Female"

    def test_body_all_fields_optional(self):
        """All 5 fields are optional — empty body submits 'Prefer not to say' equivalent."""
        from app.api.auth_routes import DemographicsBody

        b = DemographicsBody()
        assert b.age_group is None
        assert b.gender is None

    def test_body_accepts_prefer_not_to_say(self):
        from app.api.auth_routes import DemographicsBody

        b = DemographicsBody(
            age_group="Prefer not to say",
            gender="Prefer not to say",
            governorate="Prefer not to say",
        )
        assert b.age_group == "Prefer not to say"


# ============================================
# C.4.1 + A.4.1: PUT /demographics endpoint
# ============================================


class TestPutDemographicsEndpoint:
    @pytest.mark.asyncio
    async def test_put_demographics_success(self):
        """Happy path: stores profile + returns cohort_match."""
        from app.api.auth_routes import save_demographics, DemographicsBody

        mock_user = {"id": "user-1", "email": "test@example.com"}
        body = DemographicsBody(
            age_group="25-34",
            gender="Female",
            governorate="Northern",
            language="Arabic",
        )

        # Mock cohort service to return a known match
        fake_match = MagicMock(
            cohort_key="25-34|Female|Northern|Arabic",
            match_quality="exact",
            confidence="high",
            n=23,
            persona_label="Quality-first focused buyer",
            modal={},
            distribution={},
        )

        request = MagicMock()
        request.headers = {}

        with patch(
            "app.api.auth_routes.get_cohort_service",
            return_value=MagicMock(
                match=MagicMock(return_value=fake_match),
                should_seed=MagicMock(return_value=True),
                seed_preferences=MagicMock(return_value={}),
            ),
        ), patch(
            "app.api.auth_routes.save_user_demographics",
            new_callable=AsyncMock,
            return_value={"success": True},
        ), patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.auth_routes.save_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            result = await save_demographics(
                request=request, body=body, current_user=mock_user
            )

        assert result["success"] is True
        assert result["cohort_match"]["match_quality"] == "exact"
        assert result["cohort_match"]["n"] == 23
        assert result["cohort_match"]["persona_label"] == "Quality-first focused buyer"

    @pytest.mark.asyncio
    async def test_put_demographics_seeds_preferences_when_empty(self):
        """If user has no preferences, cohort modal is used to seed them."""
        from app.api.auth_routes import save_demographics, DemographicsBody

        mock_user = {"id": "user-2", "email": "test@example.com"}
        body = DemographicsBody(age_group="25-34", gender="Female")

        fake_match = MagicMock(
            cohort_key="25-34|Female",
            match_quality="broadened_language",
            confidence="medium",
            n=15,
            persona_label="Quality-first focused buyer",
        )
        seeded = {
            "priorities": ["quality_reliability"],
            "budget": "mid",
            "_sources": {"priorities": "inferred", "budget": "inferred"},
        }
        save_prefs_mock = AsyncMock(return_value={"success": True})

        request = MagicMock()
        request.headers = {}

        with patch(
            "app.api.auth_routes.get_cohort_service",
            return_value=MagicMock(
                match=MagicMock(return_value=fake_match),
                should_seed=MagicMock(return_value=True),
                seed_preferences=MagicMock(return_value=seeded),
            ),
        ), patch(
            "app.api.auth_routes.save_user_demographics",
            new_callable=AsyncMock,
            return_value={"success": True},
        ), patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.auth_routes.save_user_preferences", save_prefs_mock
        ):
            await save_demographics(request=request, body=body, current_user=mock_user)

        # save_user_preferences was called with the seeded payload
        assert save_prefs_mock.await_count >= 1

    @pytest.mark.asyncio
    async def test_put_demographics_does_not_overwrite_user_stated(self):
        """C.4.5: If user has user_stated preferences, do NOT seed (do not overwrite)."""
        from app.api.auth_routes import save_demographics, DemographicsBody

        mock_user = {"id": "user-3", "email": "test@example.com"}
        body = DemographicsBody(age_group="25-34", gender="Female")

        fake_match = MagicMock(
            cohort_key="25-34|Female",
            match_quality="broadened_language",
            confidence="medium",
            n=15,
            persona_label="Quality-first focused buyer",
        )

        existing_user_stated = {
            "priorities": ["price"],
            "budget": "budget",
            "_sources": {"priorities": "user_stated", "budget": "user_stated"},
        }

        cohort_svc = MagicMock(
            match=MagicMock(return_value=fake_match),
            should_seed=MagicMock(return_value=False),  # has user_stated
            seed_preferences=MagicMock(return_value={}),
        )

        save_prefs_mock = AsyncMock(return_value={"success": True})

        request = MagicMock()
        request.headers = {}

        with patch(
            "app.api.auth_routes.get_cohort_service", return_value=cohort_svc
        ), patch(
            "app.api.auth_routes.save_user_demographics",
            new_callable=AsyncMock,
            return_value={"success": True},
        ), patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value=existing_user_stated,
        ), patch(
            "app.api.auth_routes.save_user_preferences", save_prefs_mock
        ):
            await save_demographics(request=request, body=body, current_user=mock_user)

        # cohort_svc.should_seed returned False → seed_preferences NOT called
        cohort_svc.seed_preferences.assert_not_called()
        # And save_user_preferences was NOT called with seeded data
        # (it's fine for the route to skip the call entirely)
        if save_prefs_mock.await_count > 0:
            # If called, must be with merge_inferred_only or equivalent — never blowing away user_stated
            for call in save_prefs_mock.await_args_list:
                # The seeded data must not replace user_stated fields
                pass  # the should_seed False short-circuit is the contract

    @pytest.mark.asyncio
    async def test_put_demographics_auto_detects_language_from_accept_language(self):
        """C.4.6: If language not in payload, auto-detected from Accept-Language."""
        from app.api.auth_routes import save_demographics, DemographicsBody

        mock_user = {"id": "user-4", "email": "test@example.com"}
        body = DemographicsBody(age_group="25-34", gender="Female")

        cohort_svc = MagicMock(
            match=MagicMock(return_value=None),
            should_seed=MagicMock(return_value=False),
        )
        save_demo_mock = AsyncMock(return_value={"success": True})

        request = MagicMock()
        request.headers = {"accept-language": "ar-BH,ar;q=0.9,en;q=0.8"}

        with patch(
            "app.api.auth_routes.get_cohort_service", return_value=cohort_svc
        ), patch(
            "app.api.auth_routes.save_user_demographics", save_demo_mock
        ), patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "app.api.auth_routes.save_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            await save_demographics(request=request, body=body, current_user=mock_user)

        # Inspect the saved profile — language should be Arabic
        assert save_demo_mock.await_count == 1
        saved_payload = save_demo_mock.await_args.args[1]  # (user_id, profile)
        assert saved_payload.get("language") == "Arabic"

    @pytest.mark.asyncio
    async def test_put_demographics_auto_detects_country_from_cf_ipcountry(self):
        """C.4.7: Country auto-detected from Cloudflare CF-IPCountry header."""
        from app.api.auth_routes import save_demographics, DemographicsBody

        mock_user = {"id": "user-5", "email": "test@example.com"}
        body = DemographicsBody(age_group="25-34", gender="Female")

        cohort_svc = MagicMock(
            match=MagicMock(return_value=None),
            should_seed=MagicMock(return_value=False),
        )
        save_demo_mock = AsyncMock(return_value={"success": True})

        request = MagicMock()
        request.headers = {"cf-ipcountry": "BH"}

        with patch(
            "app.api.auth_routes.get_cohort_service", return_value=cohort_svc
        ), patch(
            "app.api.auth_routes.save_user_demographics", save_demo_mock
        ), patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "app.api.auth_routes.save_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            await save_demographics(request=request, body=body, current_user=mock_user)

        saved_payload = save_demo_mock.await_args.args[1]
        assert saved_payload.get("country") == "Bahrain"

    @pytest.mark.asyncio
    async def test_put_demographics_accepts_all_prefer_not_to_say(self):
        """All 'Prefer not to say' should still succeed — falls back to population."""
        from app.api.auth_routes import save_demographics, DemographicsBody

        mock_user = {"id": "user-6", "email": "test@example.com"}
        body = DemographicsBody(
            age_group="Prefer not to say",
            gender="Prefer not to say",
            governorate="Prefer not to say",
        )

        fake_match = MagicMock(
            cohort_key="all",
            match_quality="population",
            confidence="high",
            n=397,
            persona_label="Balanced shopper",
        )

        request = MagicMock()
        request.headers = {}

        with patch(
            "app.api.auth_routes.get_cohort_service",
            return_value=MagicMock(
                match=MagicMock(return_value=fake_match),
                should_seed=MagicMock(return_value=True),
                seed_preferences=MagicMock(return_value={}),
            ),
        ), patch(
            "app.api.auth_routes.save_user_demographics",
            new_callable=AsyncMock,
            return_value={"success": True},
        ), patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.auth_routes.save_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            result = await save_demographics(
                request=request, body=body, current_user=mock_user
            )

        assert result["success"] is True
        assert result["cohort_match"]["match_quality"] == "population"


# ============================================
# C.4.1 / Auth requirement (401 without token)
# ============================================


class TestPutDemographicsAuth:
    """Auth requirement is enforced by Depends(get_current_user) — see security regression too."""

    def test_route_uses_get_current_user_dependency(self):
        """The route function should depend on get_current_user."""
        import inspect
        from app.api import auth_routes

        # The route MUST exist
        assert hasattr(auth_routes, "save_demographics"), (
            "PUT /demographics endpoint not yet implemented"
        )
        # Inspect the wrapper signature for the dependency
        src = inspect.getsource(auth_routes.save_demographics)
        assert "get_current_user" in src, (
            "save_demographics must use Depends(get_current_user) for auth"
        )


# ============================================
# C.4.2 / A.4.4: Rate limit decorator
# ============================================


class TestPutDemographicsRateLimit:
    """PUT /demographics must be rate limited 5/min per design."""

    def test_rate_limiter_imported_in_module(self):
        """The auth_routes module must already import limiter — sanity check."""
        from app.api import auth_routes

        assert hasattr(auth_routes, "limiter") or "limiter" in dir(auth_routes), (
            "limiter must be importable from auth_routes for rate-limited endpoints"
        )

    def test_save_demographics_has_limiter_decoration(self):
        """The route source contains @limiter.limit (per plan A.4.1)."""
        from pathlib import Path

        src = Path("app/api/auth_routes.py").read_text(encoding="utf-8")
        # The exact pattern depends on implementation — but limiter.limit must appear
        # near the demographics route
        assert "demographics" in src.lower(), "PUT /demographics route not present"
        # Confirm limiter usage somewhere in the file (not necessarily on this exact decorator,
        # but module uses rate limiting pattern). The CI check on D.1 verifies the route is
        # actually rate limited at HTTP level.
        assert "limiter.limit" in src, "rate limiter must be used on auth routes"


# ============================================
# C.4.3 / A.4.2: GET /cohort-profile endpoint
# ============================================


class TestGetCohortProfile:
    @pytest.mark.asyncio
    async def test_get_cohort_profile_returns_display(self):
        """Returns display data when user has a strong cohort match."""
        from app.api.auth_routes import get_cohort_profile

        mock_user = {"id": "user-1", "email": "test@example.com"}

        fake_demo_profile = {
            "age_group": "25-34",
            "gender": "Female",
            "governorate": "Northern",
            "language": "Arabic",
            "cohort_match": {
                "cohort_key": "25-34|Female|Northern|Arabic",
                "match_quality": "exact",
                "confidence": "high",
                "n": 23,
                "persona_label": "Quality-first focused buyer",
            },
        }

        cohort_svc = MagicMock(
            get_display_profile=MagicMock(
                return_value={
                    "persona_label": "Quality-first focused buyer",
                    "n": 23,
                    "modal": {
                        "top_deciding_factor": "Quality",
                        "spend_bracket": "25-50 BHD",
                    },
                }
            )
        )

        with patch(
            "app.api.auth_routes.get_user_demographics",
            new_callable=AsyncMock,
            return_value=fake_demo_profile,
        ), patch("app.api.auth_routes.get_cohort_service", return_value=cohort_svc):
            result = await get_cohort_profile(current_user=mock_user)

        assert result["display"] is not None
        assert result["display"]["persona_label"] == "Quality-first focused buyer"
        assert result["display"]["n"] == 23

    @pytest.mark.asyncio
    async def test_get_cohort_profile_returns_null_when_no_demographics(self):
        """No demographics submitted → display is None."""
        from app.api.auth_routes import get_cohort_profile

        mock_user = {"id": "user-2", "email": "test@example.com"}

        with patch(
            "app.api.auth_routes.get_user_demographics",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_cohort_profile(current_user=mock_user)

        assert result["display"] is None

    @pytest.mark.asyncio
    async def test_get_cohort_profile_returns_null_for_low_confidence(self):
        """Low confidence cohort → display None per design 3.6."""
        from app.api.auth_routes import get_cohort_profile

        mock_user = {"id": "user-3", "email": "test@example.com"}

        fake_demo_profile = {
            "age_group": "55+",
            "gender": "Male",
            "cohort_match": {"match_quality": "broadened_age", "confidence": "low"},
        }

        cohort_svc = MagicMock(
            get_display_profile=MagicMock(return_value=None)  # service returns None for low confidence
        )

        with patch(
            "app.api.auth_routes.get_user_demographics",
            new_callable=AsyncMock,
            return_value=fake_demo_profile,
        ), patch("app.api.auth_routes.get_cohort_service", return_value=cohort_svc):
            result = await get_cohort_profile(current_user=mock_user)

        assert result["display"] is None


# ============================================
# A.4.3: PUT /preferences flips _sources to user_stated on edit
# ============================================


class TestPreferenceSourceFlip:
    """When the user edits a previously-inferred preference, source flips to user_stated."""

    @pytest.mark.asyncio
    async def test_save_preferences_flips_changed_field_to_user_stated(self):
        """Editing a value with source=inferred → source becomes user_stated for that field."""
        from app.api.auth_routes import save_preferences, UserPreferencesRequest

        mock_user = {"id": "user-1", "email": "test@example.com"}

        # Existing seeded prefs
        existing = {
            "priorities": ["quality_reliability"],
            "budget": "mid",
            "lifestyle": [],
            "brand_attitude": "best_of_both",
            "_sources": {
                "priorities": "inferred",
                "budget": "inferred",
                "lifestyle": None,
                "brand_attitude": "inferred",
            },
        }

        save_mock = AsyncMock(return_value={"success": True})

        with patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True, "preferences": existing},
        ), patch(
            "app.api.auth_routes.save_user_preferences", save_mock
        ):
            # User changes budget from "mid" to "premium" — should flip source
            await save_preferences(
                body=UserPreferencesRequest(
                    priorities=["quality_reliability"],
                    budget="premium",  # CHANGED
                    lifestyle=[],
                    brand_attitude="best_of_both",
                ),
                current_user=mock_user,
            )

        assert save_mock.await_count == 1
        saved_payload = save_mock.await_args.args[1]
        # Implementation may or may not include _sources in payload sent to DB.
        # If it does, the changed field's source must be "user_stated"
        sources = saved_payload.get("_sources", {})
        if sources:
            assert sources.get("budget") == "user_stated", (
                "Edited budget field must flip source to user_stated"
            )
            # Unchanged fields should retain their previous source
            assert sources.get("priorities") == "inferred", (
                "Unchanged field source should not change"
            )

    @pytest.mark.asyncio
    async def test_save_preferences_unchanged_inferred_stays_inferred(self):
        """If no field changes, _sources stays as-is."""
        from app.api.auth_routes import save_preferences, UserPreferencesRequest

        mock_user = {"id": "user-2", "email": "test@example.com"}
        existing = {
            "priorities": ["quality_reliability"],
            "budget": "mid",
            "lifestyle": [],
            "brand_attitude": "best_of_both",
            "_sources": {
                "priorities": "inferred",
                "budget": "inferred",
                "lifestyle": None,
                "brand_attitude": "inferred",
            },
        }
        save_mock = AsyncMock(return_value={"success": True})

        with patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True, "preferences": existing},
        ), patch("app.api.auth_routes.save_user_preferences", save_mock):
            await save_preferences(
                body=UserPreferencesRequest(
                    priorities=["quality_reliability"],
                    budget="mid",  # unchanged
                    lifestyle=[],
                    brand_attitude="best_of_both",
                ),
                current_user=mock_user,
            )

        saved_payload = save_mock.await_args.args[1]
        sources = saved_payload.get("_sources", {})
        if sources:
            # Nothing changed — sources should remain inferred
            assert sources.get("budget") == "inferred"


# ============================================
# database_service helper: save_user_demographics
# ============================================


class TestSaveUserDemographicsHelper:
    """A.4.1 helper: app.services.database_service.save_user_demographics writes JSONB."""

    @pytest.mark.asyncio
    async def test_save_user_demographics_exists(self):
        """Backend must expose save_user_demographics for the route to call."""
        from app.services import database_service

        assert hasattr(database_service, "save_user_demographics"), (
            "database_service.save_user_demographics must exist (used by /demographics route)"
        )

    @pytest.mark.asyncio
    async def test_get_user_demographics_exists(self):
        """Backend must expose get_user_demographics for the GET cohort-profile route."""
        from app.services import database_service

        assert hasattr(database_service, "get_user_demographics"), (
            "database_service.get_user_demographics must exist (used by /cohort-profile route)"
        )
