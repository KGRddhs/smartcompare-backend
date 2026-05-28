"""Regression tests for B-S1.YELLOW — display.governorate on /auth/cohort-profile.

Frontend ProfileHeaderRow (ProfileScreen.jsx:34-51) renders the subtitle as
"{governorate} · GCC" / "GCC" fallback. Backend already stores governorate in
users.demographics (onboarding Step 04 write target); these tests pin that
get_display_profile() echoes it back as an Optional[str] so the owner sees
their own region.

Privacy invariant (qaren-cohort skill) restricts governorate from GPT prompt
content, not from a user's own display of their own typed answer.
"""
from __future__ import annotations

from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Same FAKE_PRIORS shape as tests/test_cohort_service.py — kept inline so this
# file is self-contained and stays green even if the canonical fixture moves.
FAKE_PRIORS = {
    "version": "1.0",
    "built_at": "2026-05-03T12:00:00Z",
    "total_responses": 397,
    "cohorts": {
        "25-34|Female|Northern|Arabic": {
            "n": 23,
            "confidence": "high",
            "demographics": {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            },
            "modal": {
                "top_deciding_factor": "Quality",
                "spend_bracket": "25-50 BHD",
            },
            "distribution": {},
            "persona_label": "Quality-first focused buyer",
        },
        "25-34|Male|Capital|English": {
            "n": 12,
            "confidence": "medium",
            "demographics": {
                "age_group": "25-34",
                "gender": "Male",
                "governorate": "Capital",
                "language": "English",
            },
            "modal": {
                "top_deciding_factor": "Brand",
                "spend_bracket": "100-250 BHD",
            },
            "distribution": {},
            "persona_label": "Premium brand-loyal buyer",
        },
    },
    "fallback_aggregates": {
        "25-34|Female|Arabic": {
            "n": 35,
            "confidence": "high",
            "demographics": {
                "age_group": "25-34",
                "gender": "Female",
                "language": "Arabic",
            },
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Quality-first focused buyer",
        },
        "all": {
            "n": 397,
            "confidence": "high",
            "demographics": {},
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Balanced shopper",
        },
    },
}


@pytest.fixture
def fake_service():
    from app.services.cohort_service import CohortService

    svc = CohortService.__new__(CohortService)
    svc._cohorts = FAKE_PRIORS
    return svc


# ============================================
# Service-level: get_display_profile() echoes governorate
# ============================================


class TestDisplayGovernorate:
    def test_governorate_present_when_user_typed_it(self, fake_service):
        """Demographics with governorate='Northern' → display.governorate == 'Northern'."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert display is not None
        assert "governorate" in display, "F-S1.5d depends on this key being present"
        assert display["governorate"] == "Northern"

    def test_governorate_present_for_broadened_match(self, fake_service):
        """User typed Manama but only the age|gender|language fallback matches.

        Display still echoes the user's typed governorate — broadened match
        means the cohort priors fell back, not that the user didn't type a
        governorate.
        """
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Manama",  # no matching cohort → broadened_governorate
                "language": "Arabic",
            }
        )
        assert display is not None
        assert display["match_quality"] == "broadened_governorate"
        assert display["governorate"] == "Manama"

    def test_governorate_none_when_omitted(self, fake_service):
        """No governorate key at all → display.governorate is None (fallback to 'GCC' on FE)."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "language": "Arabic",
            }
        )
        assert display is not None
        assert "governorate" in display
        assert display["governorate"] is None

    def test_governorate_none_when_explicit_none(self, fake_service):
        """Explicit None on governorate → display.governorate is None."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": None,
                "language": "Arabic",
            }
        )
        assert display is not None
        assert display["governorate"] is None

    def test_governorate_none_when_prefer_not_to_say(self, fake_service):
        """SKIP_SENTINELS-matching governorate value → display.governorate is None.

        'Prefer not to say' is treated as missing by _key_part(); we should NOT
        leak that exact sentinel string to the UI as a 'region'.
        """
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Prefer not to say",
                "language": "Arabic",
            }
        )
        assert display is not None
        assert display["governorate"] is None

    def test_governorate_none_when_arabic_prefer_not_to_say(self, fake_service):
        """Arabic sentinel for 'Prefer not to say' is also treated as missing."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "أفضل عدم الإجابة",
                "language": "Arabic",
            }
        )
        assert display is not None
        assert display["governorate"] is None

    def test_governorate_stripped_of_whitespace(self, fake_service):
        """Whitespace around governorate is stripped (consistent with _key_part)."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Male",
                "governorate": "  Capital  ",
                "language": "English",
            }
        )
        assert display is not None
        # User typed Capital with stray whitespace → echoed back trimmed.
        assert display["governorate"] == "Capital"


# ============================================
# Regression: other display fields untouched
# ============================================


class TestDisplayShapeRegression:
    def test_existing_fields_still_present_with_governorate(self, fake_service):
        """Adding governorate must NOT drop persona_label/n/modal/match_quality/confidence."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert display is not None
        # F-S1.5d reads governorate; existing consumers read these:
        for key in ("persona_label", "n", "modal", "match_quality", "confidence"):
            assert key in display, f"display.{key} regression: existing UI consumers read this"
        assert display["persona_label"] == "Quality-first focused buyer"
        assert display["n"] == 23
        assert display["match_quality"] == "exact"
        assert display["confidence"] == "high"


# ============================================
# Route-level: GET /auth/cohort-profile shape
# ============================================


class TestGetCohortProfileGovernorate:
    @pytest.mark.asyncio
    async def test_route_returns_governorate_when_present(self):
        """Real cohort_service through the route → response.display.governorate present."""
        from app.api.auth_routes import get_cohort_profile

        mock_user = {"id": "user-gov-1", "email": "test@example.com"}
        fake_demo = {
            "age_group": "25-34",
            "gender": "Female",
            "governorate": "Northern",
            "language": "Arabic",
        }

        cohort_svc = MagicMock(
            get_display_profile=MagicMock(
                return_value={
                    "persona_label": "Quality-first focused buyer",
                    "n": 23,
                    "modal": {"top_deciding_factor": "Quality"},
                    "match_quality": "exact",
                    "confidence": "high",
                    "governorate": "Northern",
                }
            )
        )

        with patch(
            "app.api.auth_routes.get_user_demographics",
            new_callable=AsyncMock,
            return_value=fake_demo,
        ), patch("app.api.auth_routes.get_cohort_service", return_value=cohort_svc):
            result = await get_cohort_profile(current_user=mock_user)

        assert result["display"] is not None
        assert result["display"]["governorate"] == "Northern"

    @pytest.mark.asyncio
    async def test_route_returns_null_display_when_no_demographics(self):
        """No demographics row → response.display is None (route stays unchanged)."""
        from app.api.auth_routes import get_cohort_profile

        mock_user = {"id": "user-gov-2", "email": "test@example.com"}

        with patch(
            "app.api.auth_routes.get_user_demographics",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_cohort_profile(current_user=mock_user)

        # Frontend falls back to 'GCC' subtitle when display is null.
        assert result["display"] is None
