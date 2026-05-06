"""Tests for B6.1 + B6.2 — admin referral metrics + cost dashboard.

Auth: every endpoint must require X-Admin-Key. Mocking strategy: patch
get_admin_supabase_client + api_budget_service.get_usage_summary so we
exercise the routing + aggregation logic without hitting real Supabase
or Redis.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _set_admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")


def _admin_headers() -> dict:
    return {"X-Admin-Key": "test-admin-key"}


# ============================================
# B6.1 — Auth gating
# ============================================


class TestAdminAuthRequired:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/admin/referrals/metrics",
            "/api/v1/admin/referrals/viral",
            "/api/v1/admin/referrals/cohort_uplift",
            "/api/v1/admin/referrals/abuse",
            "/api/v1/admin/costs/subscriptions",
            "/api/v1/admin/costs/api",
            "/api/v1/admin/costs/function_map",
            "/api/v1/admin/costs/gauges",
        ],
    )
    def test_no_key_rejected(self, path):
        resp = client.get(path)
        # Either 422 (missing header) or 403 (bad key) is acceptable;
        # the contract is: anonymous users CANNOT read these.
        assert resp.status_code in (401, 403, 422), (
            f"{path} must reject unauthenticated requests, got {resp.status_code}"
        )

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/admin/referrals/metrics",
            "/api/v1/admin/costs/function_map",
        ],
    )
    def test_wrong_key_rejected(self, path):
        resp = client.get(path, headers={"X-Admin-Key": "WRONG"})
        assert resp.status_code == 403


# ============================================
# B6.1 — /referrals/metrics
# ============================================


class TestReferralsMetrics:
    def test_returns_invites_redemptions_and_conversion(self):
        client_mock = MagicMock()
        # invites_week query
        client_mock.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            count=12, data=[{"referrer_user_id": "r1"}, {"referrer_user_id": "r2"}, {"referrer_user_id": "r1"}],
        )
        # lifetime queries
        client_mock.table.return_value.select.return_value.execute.return_value = MagicMock(count=100)

        with patch(
            "app.api.admin_routes.get_admin_supabase_client",
            return_value=client_mock,
        ):
            resp = client.get(
                "/api/v1/admin/referrals/metrics", headers=_admin_headers()
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "invites" in body
        assert "redemptions" in body
        assert "conversion_rate" in body
        assert "active_referrers_month" in body
        assert body["invites"]["week"] >= 0
        assert 0 <= body["conversion_rate"]["lifetime"] <= 1


# ============================================
# B6.1 — /referrals/viral
# ============================================


class TestReferralsViral:
    def test_returns_weekly_series_with_k(self):
        client_mock = MagicMock()
        # data path: invites returns list of dicts
        client_mock.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(
            data=[{"referrer_user_id": "r1"}, {"referrer_user_id": "r2"}], count=1,
        )

        with patch(
            "app.api.admin_routes.get_admin_supabase_client",
            return_value=client_mock,
        ):
            resp = client.get(
                "/api/v1/admin/referrals/viral?weeks=4", headers=_admin_headers()
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["weeks"] == 4
        assert len(body["series"]) == 4
        for week in body["series"]:
            assert "k" in week
            assert "avg_invites_per_referrer" in week
            assert "conversion_rate" in week

    def test_weeks_clamped(self):
        with patch(
            "app.api.admin_routes.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            # Out-of-range weeks must 422 from the Query validator
            resp = client.get(
                "/api/v1/admin/referrals/viral?weeks=999", headers=_admin_headers()
            )
        assert resp.status_code == 422


# ============================================
# B6.1 — /referrals/cohort_uplift
# ============================================


class TestReferralsCohortUplift:
    def test_returns_referred_and_organic_blocks(self):
        client_mock = MagicMock()
        # Default mock returns empty data — endpoint should still respond.
        client_mock.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with patch(
            "app.api.admin_routes.get_admin_supabase_client",
            return_value=client_mock,
        ):
            resp = client.get(
                "/api/v1/admin/referrals/cohort_uplift", headers=_admin_headers()
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "referred" in body
        assert "organic" in body
        assert "retention_rate" in body["referred"]
        assert "retention_rate" in body["organic"]
        assert "avg_comparisons" in body["referred"]


# ============================================
# B6.1 — /referrals/abuse
# ============================================


class TestReferralsAbuse:
    def test_returns_flagged_invites_and_audit(self):
        client_mock = MagicMock()
        client_mock.table.return_value.select.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "i1", "flagged_reason": "SAME_DEVICE"},
                {"id": "i2", "flagged_reason": "DISPOSABLE_EMAIL"},
                {"id": "i3", "flagged_reason": "SAME_DEVICE"},
            ]
        )
        client_mock.table.return_value.select.return_value.like.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"event_type": "referral_same_device", "user_id": "u1"},
            ]
        )

        with patch(
            "app.api.admin_routes.get_admin_supabase_client",
            return_value=client_mock,
        ):
            resp = client.get(
                "/api/v1/admin/referrals/abuse", headers=_admin_headers()
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "flagged_invites" in body
        assert "audit_events" in body
        assert "counts_by_reason" in body
        assert body["counts_by_reason"]["SAME_DEVICE"] == 2
        assert body["counts_by_reason"]["DISPOSABLE_EMAIL"] == 1


# ============================================
# B6.2 — /costs/* endpoints
# ============================================


class TestCostsSubscriptions:
    def test_returns_static_subscription_list(self):
        resp = client.get(
            "/api/v1/admin/costs/subscriptions", headers=_admin_headers()
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body and len(body["items"]) >= 5
        assert "total_monthly_usd" in body
        assert body["total_monthly_usd"] > 0


class TestCostsApi:
    def test_returns_openai_total_and_daily_burn(self):
        client_mock = MagicMock()
        client_mock.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "created_at": "2026-05-04T10:00:00Z",
                    "full_response": {"metadata": {"total_cost": 0.0086}},
                },
                {
                    "created_at": "2026-05-05T11:00:00Z",
                    "full_response": {"metadata": {"total_cost": 0.0019}},
                },
            ]
        )

        with patch(
            "app.api.admin_routes.get_admin_supabase_client",
            return_value=client_mock,
        ), patch(
            "app.api.admin_routes.get_usage_summary",
            return_value={
                "providers": {"firecrawl": {"used": 12, "limit": 450}},
                "circuit_breakers": {},
            },
        ):
            resp = client.get(
                "/api/v1/admin/costs/api", headers=_admin_headers()
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["openai_paid_usd"] > 0
        assert len(body["daily_burn"]) == 2
        assert body["scrapers"]["firecrawl"]["used"] == 12


class TestCostsFunctionMap:
    def test_returns_static_map(self):
        resp = client.get(
            "/api/v1/admin/costs/function_map", headers=_admin_headers()
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        # Must include OpenAI + Serper + Firecrawl + Scrape.do at minimum
        services = {item["service"] for item in body["items"]}
        assert any("OpenAI" in s for s in services)
        assert any("Serper" in s for s in services)
        assert any("Firecrawl" in s for s in services)


class TestCostsGauges:
    def test_returns_4_gauges_with_pct(self):
        with patch(
            "app.services.cache_service._redis_get", return_value="500000"
        ), patch(
            "app.api.admin_routes.get_usage_summary",
            return_value={
                "providers": {
                    "firecrawl": {"used": 150, "limit": 450},
                    "scrapedo": {"used": 200, "limit": 900},
                    "serper": {"used": 800, "limit": 2200},
                },
                "circuit_breakers": {},
            },
        ):
            resp = client.get(
                "/api/v1/admin/costs/gauges", headers=_admin_headers()
            )
        assert resp.status_code == 200
        body = resp.json()
        for gauge_name in (
            "openai_4o_today",
            "firecrawl_lifetime",
            "scrapedo_month",
            "serper_lifetime",
        ):
            assert gauge_name in body
            assert "used" in body[gauge_name]
            assert "cap" in body[gauge_name]
            assert "pct" in body[gauge_name]
        # 500K / 1M = 50%
        assert body["openai_4o_today"]["pct"] == 50.0
