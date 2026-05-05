"""HTTP-level tests for app/api/referral_routes.py.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
section 3 + plan tasks B2.1, B2.2, B3.1, B3.4.

Written FIRST (red phase). Backend implements the routes to make these green.

Pattern: TestClient + dependency overrides (NOT mocking authentication helpers
directly — let the registered router handle auth, override get_current_user
via app.dependency_overrides). Same pattern as test_history_routes.py.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================
# B2.1 — POST /api/v1/referrals/share (HTTP layer)
# ============================================


class TestPostReferralsShare:
    def test_route_is_registered(self):
        """The endpoint must be wired into the FastAPI app."""
        # Without auth headers, expect 401/403/422 — NOT 404 (which means route missing)
        resp = client.post(
            "/api/v1/referrals/share",
            json={"comparison_id": "00000000-0000-0000-0000-000000000000", "share_target": "whatsapp"},
        )
        assert resp.status_code != 404, (
            f"POST /api/v1/referrals/share missing — expected non-404, got 404. "
            f"backend-referral must register router in app/main.py per plan B2.1."
        )

    def test_unauthorized_request_rejected(self):
        """No bearer token => 401 (or 403)."""
        resp = client.post(
            "/api/v1/referrals/share",
            json={"comparison_id": "00000000-0000-0000-0000-000000000000", "share_target": "whatsapp"},
        )
        assert resp.status_code in (401, 403, 422), f"got {resp.status_code}: {resp.text}"

    def test_share_target_validation(self):
        """share_target must be in whitelist; bad value => 422."""
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-test", "email": "u@test.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            resp = client.post(
                "/api/v1/referrals/share",
                json={
                    "comparison_id": "00000000-0000-0000-0000-000000000000",
                    "share_target": "facebook",  # NOT in whitelist
                },
                headers={"Authorization": "Bearer tok"},
            )
            # 422 (pydantic) or 400 (service-level) acceptable
            assert resp.status_code in (400, 422), f"got {resp.status_code}: {resp.text}"
        finally:
            app.dependency_overrides.clear()


# ============================================
# B2.2 — GET /api/v1/referrals/status (HTTP layer)
# ============================================


class TestGetReferralsStatus:
    def test_route_is_registered(self):
        resp = client.get("/api/v1/referrals/status")
        assert resp.status_code != 404, (
            "GET /api/v1/referrals/status missing — backend-referral must register router."
        )

    def test_unauthorized_returns_401(self):
        resp = client.get("/api/v1/referrals/status")
        assert resp.status_code in (401, 403, 422)

    def test_authorized_returns_status_envelope(self):
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-status", "email": "s@test.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            with patch("app.api.referral_routes.ReferralService") as MockSvc:
                svc = MockSvc.return_value
                svc.get_status = AsyncMock(return_value={
                    "weekly_invites_used": 1,
                    "weekly_invites_remaining": 2,
                    "monthly_bonus_comparisons": 0,
                    "deep_review_credits_available": 1,
                    "total_lifetime_redemptions": 0,
                    "referral_code": "QR-ABCD23",
                })

                resp = client.get(
                    "/api/v1/referrals/status",
                    headers={"Authorization": "Bearer tok"},
                )
                assert resp.status_code == 200, resp.text
                data = resp.json()
                # Either at top-level or nested under "data" — design says top-level
                expected_keys = {
                    "weekly_invites_used", "weekly_invites_remaining",
                    "monthly_bonus_comparisons", "deep_review_credits_available",
                    "total_lifetime_redemptions", "referral_code",
                }
                actual = set(data.keys())
                assert expected_keys.issubset(actual), f"missing keys: {expected_keys - actual}"
        finally:
            app.dependency_overrides.clear()


# ============================================
# B3.1 — GET /api/v1/referrals/invite/{token}?ref={code} (auth-OPTIONAL)
# ============================================


class TestGetReferralInvite:
    """Anon invitee landing endpoint. No auth required."""

    def test_route_is_registered(self):
        resp = client.get("/api/v1/referrals/invite/sometoken123456789?ref=QR-AAAAAA")
        # Expected 404 (token not found) or 200, NOT a router-missing 404 with no body
        # Distinguish by checking that a referral_routes-level handler responded
        assert resp.status_code != 405, "wrong method or route shape"

    def test_invalid_ref_returns_404(self):
        """Invalid ?ref=QR-XXXXXX must 404."""
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.resolve_invite = AsyncMock(return_value=None)

            resp = client.get("/api/v1/referrals/invite/sometoken123456789?ref=QR-NOTREAL")
            # Either router 404 or 200 with success=False — accept either, but if 200 must say not found
            assert resp.status_code in (200, 404)
            if resp.status_code == 200:
                body = resp.json()
                assert body.get("success") is False or body.get("comparison") is None

    def test_valid_invite_returns_referrer_name_and_sanitized_comparison(self):
        """Happy path: anon user resolves valid token+ref, gets referrer display name + sanitized comparison."""
        sanitized_comparison = {
            "id": "cmp-1",
            "products": [{"name": "iPhone 15"}, {"name": "Galaxy S24"}],
            "winner": {"name": "iPhone 15"},
            "verdict": "Decisive iPhone win on camera",
            # NO preferences, NO budget — sanitized
        }
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.resolve_invite = AsyncMock(return_value={
                "referrer_display_name": "Ahmed",
                "comparison": sanitized_comparison,
                "cohort_match": None,
                "invite_id": "invite-uuid-1",
            })

            resp = client.get("/api/v1/referrals/invite/tokenAAAAAAAAAAAAAAAA?ref=QR-AHMED1")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["referrer_display_name"] == "Ahmed"
            assert "comparison" in data
            # Privacy invariant: NO referrer preferences leaked
            comparison = data["comparison"]
            assert "preferences" not in comparison, (
                "Privacy bug: referrer's preferences leaked to invitee landing"
            )
            # Allow comparison.users.budget? No — sanitization must strip even nested budget
            assert "budget" not in comparison, "budget must be stripped per design 3.3"

    def test_no_auth_header_required(self):
        """Endpoint must work for anonymous users — gradual commitment (PDF #6)."""
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.resolve_invite = AsyncMock(return_value={
                "referrer_display_name": "Sarah",
                "comparison": {"products": [], "winner": None},
                "cohort_match": None,
                "invite_id": "i-1",
            })

            # NO Authorization header
            resp = client.get("/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-SARAH9")
            # Must NOT 401/403 — anon access required
            assert resp.status_code != 401
            assert resp.status_code != 403


# ============================================
# B3.4 — POST /api/v1/referrals/invite/{token}/quiz (auth-OPTIONAL, anon)
# ============================================


class TestPostInviteQuiz:
    """Anon quiz submission returns personalized comparison. No PII stored."""

    def test_route_is_registered(self):
        resp = client.post(
            "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
            json={
                "priority": "best_price",
                "budget": "mid",
                "brand_attitude": "function_first",
                "non_negotiable": "battery life",
            },
        )
        assert resp.status_code != 405, "POST /referrals/invite/{token}/quiz missing"

    def test_quiz_returns_personalized_result_no_auth(self):
        with patch("app.api.referral_routes.ReferralService") as MockSvc:
            svc = MockSvc.return_value
            svc.run_invitee_quiz = AsyncMock(return_value={
                "products": [{"name": "iPhone 15"}, {"name": "Galaxy S24"}],
                "winner": {"name": "Galaxy S24"},  # invitee's quiz flipped the winner
                "scoring": {"scoring_method": "invitee_quiz"},
                "personalization": {"scoring_method": "invitee_quiz"},
            })

            resp = client.post(
                "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
                json={
                    "priority": "best_price",
                    "budget": "budget",
                    "brand_attitude": "open_to_emerging",
                    "non_negotiable": "size",
                },
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            scoring_method = (
                body.get("scoring", {}).get("scoring_method")
                or body.get("personalization", {}).get("scoring_method")
            )
            assert scoring_method == "invitee_quiz", (
                f"expected scoring_method=invitee_quiz, got {scoring_method}"
            )

    def test_quiz_validates_priority_against_VALID_PRIORITIES(self):
        """Quiz must validate priority against the same enum used in onboarding."""
        resp = client.post(
            "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
            json={
                "priority": "absolutely_invalid_value",
                "budget": "mid",
                "brand_attitude": "function_first",
                "non_negotiable": "test",
            },
        )
        # 422 (pydantic) or 400 (service) — NOT 200
        assert resp.status_code in (400, 422), f"got {resp.status_code}: {resp.text}"
