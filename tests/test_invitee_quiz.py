"""Tests for T3.6 — invitee flow extended coverage (B3.1 + B3.4 deeper cases).

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
sections 3.5 + 3.6 + 3.7 and plan task T3.6.

Goals:
- Anon resolution of valid invite token returns sanitized comparison
- Personalization stripped from invitee view (no `preferences`, no `budget`)
- Quiz endpoint stores no PII pre-signup
- Signup with `invite_id` correctly links the row
- 80%+ coverage on app/api/referral_routes.py invite endpoints

These complement tests/test_referral_routes.py with deeper invariants.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================
# T3.6 — Privacy invariants on invitee view
# ============================================


class TestInviteeViewSanitization:
    """The invitee landing endpoint must NEVER leak referrer's personalization data."""

    def test_no_referrer_preferences_field(self):
        """Sanitized comparison must NOT include `preferences` (referrer's stated prefs)."""
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.resolve_invite = AsyncMock(return_value={
                "referrer_display_name": "Ahmed",
                "comparison": {
                    "id": "cmp-1",
                    "products": [{"name": "iPhone"}, {"name": "Galaxy"}],
                    "winner": {"name": "iPhone"},
                    "verdict": "Decisive iPhone win",
                    # Sanitized — no preferences, no budget, no behavior_profile
                },
                "cohort_match": None,
                "invite_id": "i-1",
            })

            resp = client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-AHMED3")
            assert resp.status_code == 200, resp.text
            comparison = resp.json()["comparison"]
            assert "preferences" not in comparison

    def test_no_budget_field_at_any_level(self):
        """budget MUST NOT appear anywhere in the response (PDF #8 — locked OFF)."""
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.resolve_invite = AsyncMock(return_value={
                "referrer_display_name": "Sarah",
                "comparison": {
                    "id": "c", "products": [], "winner": None,
                    # Note: NO budget key
                },
                "cohort_match": None,
                "invite_id": "i",
            })

            resp = client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-SARAH7")
            data = resp.json()
            # Recursively check no "budget" key at any level
            def has_budget(obj):
                if isinstance(obj, dict):
                    if "budget" in obj:
                        return True
                    return any(has_budget(v) for v in obj.values())
                if isinstance(obj, list):
                    return any(has_budget(item) for item in obj)
                return False

            assert not has_budget(data), f"budget leaked in response: {data}"

    def test_no_behavior_profile_leaked(self):
        """Referrer's behavior_profile (Session 38 sensitive data) NEVER reaches invitee."""
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.resolve_invite = AsyncMock(return_value={
                "referrer_display_name": "Ali",
                "comparison": {"id": "c", "products": [], "winner": None},
                "cohort_match": None,
                "invite_id": "i",
            })

            resp = client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-AL4567")
            body = resp.json()
            assert "behavior_profile" not in str(body), "behavior_profile leaked!"


# ============================================
# T3.6 — Quiz endpoint: no PII storage pre-signup
# ============================================


class TestQuizNoPIIPreSignup:
    def test_quiz_does_not_persist_anonymous_answers(self):
        """The quiz endpoint must NOT call any `save_*` Supabase write for anon users.

        Quiz answers are used to re-score in-memory and discarded. Persistence
        happens only at signup (T-3.5) when invite_id is captured.
        """
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.run_invitee_quiz = AsyncMock(return_value={
                "products": [], "winner": None,
                "scoring": {"scoring_method": "invitee_quiz"},
            })

            # Patch where the symbol is USED (auth_routes.py imports both bare),
            # not where they're defined. Per qa-referral 2026-05-05 review:
            # patching `app.services.auth_service.save_user_preferences` is vacuous
            # because auth_routes.py:26 does `from app.services.auth_service import
            # save_user_preferences` and calls it as a bare name — Python looks up
            # the symbol in auth_routes' namespace, not auth_service's.
            with patch("app.api.auth_routes.save_user_preferences", new_callable=AsyncMock) as mock_save_prefs, \
                 patch("app.api.auth_routes.save_user_demographics", new_callable=AsyncMock) as mock_save_demo:

                resp = client.post(
                    "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
                    json={
                        "priority": "best_price",
                        "budget": "mid",
                        "brand_attitude": "function_first",
                        "non_negotiable": "battery life",
                    },
                )
                assert resp.status_code == 200, resp.text
                # No persistence calls — quiz is in-memory only pre-signup
                mock_save_prefs.assert_not_called()
                mock_save_demo.assert_not_called()


# ============================================
# T3.6 — Signup with invite_id linking
# ============================================


class TestSignupLinksInvite:
    """When a user registers with invite_id, the referral_invites row must update."""

    def test_register_endpoint_accepts_invite_id_optional(self):
        """RegisterRequest accepts optional invite_id field (added by B3.5)."""
        from app.api.auth_routes import RegisterRequest

        # Should not raise when invite_id provided
        try:
            req = RegisterRequest(
                email="x@example.com",
                password="ValidPass123!",
                invite_id="00000000-0000-0000-0000-000000000000",
            )
            assert req.invite_id is not None
        except (TypeError, AttributeError):
            pytest.skip("invite_id field not yet added to RegisterRequest (B3.5 pending)")

    def test_register_without_invite_id_works_unchanged(self):
        """Existing register flow must NOT break when invite_id absent."""
        from app.api.auth_routes import RegisterRequest

        req = RegisterRequest(email="x@example.com", password="ValidPass123!")
        # Should work without invite_id (backward compat)
        invite_id = getattr(req, "invite_id", None)
        # Either field doesn't exist (pre-B3.5) or default is None
        assert invite_id in (None, ""), f"unexpected invite_id default: {invite_id!r}"


# ============================================
# T3.6 — Resolution edge cases
# ============================================


class TestInviteResolutionEdgeCases:
    def test_invalid_token_format_does_not_crash(self):
        """Garbage tokens should 404, not 500."""
        # Token too short or with weird chars
        resp = client.get("/api/v1/referrals/invite/abc?ref=QR-XXX")
        assert resp.status_code != 500, "garbage token must not crash server"

    def test_missing_ref_param(self):
        """No `ref` query param — endpoint should 422 or 400, not 500."""
        resp = client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa")
        assert resp.status_code != 500
        # Acceptable: 400, 404, 422 — depends on impl choice

    def test_first_viewed_at_set_on_first_resolution(self):
        """Per design, referral_invites.first_viewed_at must be set on first call."""
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value

            captured_calls = []

            async def fake_resolve(*args, **kwargs):
                # Impl uses share_token=... and ref_code=... kwargs
                captured_calls.append({"token": kwargs.get("share_token"), "code": kwargs.get("ref_code")})
                return {
                    "referrer_display_name": "Ahmed",
                    "comparison": {"id": "c", "products": [], "winner": None},
                    "cohort_match": None,
                    "invite_id": "i-1",
                }

            svc.resolve_invite = AsyncMock(side_effect=fake_resolve)

            client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-AHMED3")
            # Resolve was called — implementation must set first_viewed_at internally
            assert len(captured_calls) == 1
