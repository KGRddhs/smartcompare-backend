"""Tests for ENABLE_REFERRAL_SYSTEM feature-flag gate on referral routes.

Pattern matches Session 41 cohort flag: default OFF in code, conftest
flips ON for unit tests so the existing GREEN suite keeps passing,
production absence of the env var leaves the feature OFF until Ahmed
flips it on Railway during canary (plan Q8.3).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestReferralFlagDefault:
    def test_flag_default_off_in_code(self, monkeypatch):
        """Production absence of ENABLE_REFERRAL_SYSTEM means OFF."""
        monkeypatch.delenv("ENABLE_REFERRAL_SYSTEM", raising=False)
        from app.api import referral_routes

        # Reload reads the env var fresh
        assert referral_routes._is_referral_enabled() is False, (
            "code default must be OFF for safe rollback"
        )

    def test_flag_explicit_true_enables(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")
        from app.api import referral_routes

        assert referral_routes._is_referral_enabled() is True

    def test_flag_explicit_false_disables(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "false")
        from app.api import referral_routes

        assert referral_routes._is_referral_enabled() is False


class TestReferralRoutesReturn503WhenDisabled:
    """When the flag is off, every /referrals/* endpoint must return 503."""

    def test_share_returns_503_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "false")
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "user-test", "email": "u@test.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            resp = client.post(
                "/api/v1/referrals/share",
                json={
                    "comparison_id": "00000000-0000-0000-0000-000000000000",
                    "share_target": "whatsapp",
                },
                headers={"Authorization": "Bearer tok"},
            )
            assert resp.status_code == 503, resp.text
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_503_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "false")
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "u", "email": "u@t.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            resp = client.get(
                "/api/v1/referrals/status",
                headers={"Authorization": "Bearer tok"},
            )
            assert resp.status_code == 503
        finally:
            app.dependency_overrides.clear()

    def test_invite_returns_503_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "false")
        resp = client.get(
            "/api/v1/referrals/invite/sometoken123456789?ref=QR-AAAAAA"
        )
        assert resp.status_code == 503

    def test_quiz_returns_503_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "false")
        resp = client.post(
            "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
            json={
                "priority": "best_price",
                "budget": "mid",
                "brand_attitude": "function_first",
                "non_negotiable": "size",
            },
        )
        assert resp.status_code == 503


class TestReferralRoutesWorkWhenFlagOn:
    """Conftest sets ENABLE_REFERRAL_SYSTEM=true so the existing 13 route
    tests stay GREEN. This test re-asserts that the 503 only applies when
    the flag is OFF — sanity check the gate doesn't accidentally fire on
    truthy values."""

    def test_status_does_not_503_when_enabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")
        from app.api.auth_routes import get_current_user

        async def fake_user():
            return {"id": "u", "email": "u@t.com", "access_token": "tok"}

        app.dependency_overrides[get_current_user] = fake_user
        try:
            with patch("app.api.referral_routes.ReferralService") as MockSvc:
                MockSvc.return_value.get_status = AsyncMock(return_value={
                    "weekly_invites_used": 0,
                    "weekly_invites_remaining": 3,
                    "monthly_bonus_comparisons": 0,
                    "deep_review_credits_available": 0,
                    "total_lifetime_redemptions": 0,
                    "referral_code": "QR-OK1234",
                })

                resp = client.get(
                    "/api/v1/referrals/status",
                    headers={"Authorization": "Bearer tok"},
                )
                assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()
