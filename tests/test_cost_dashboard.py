"""Tests for admin cost dashboard endpoint."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)
ADMIN_KEY = "test-admin-key"


@pytest.fixture(autouse=True)
def mock_admin_key():
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY}):
        yield


class TestCostDashboard:
    def test_returns_provider_budgets(self):
        mock_summary = {
            "providers": {
                "firecrawl": {"used": 10, "limit": 450, "remaining": 440, "is_lifetime": True},
                "scrapedo": {"used": 5, "limit": 900, "remaining": 895, "is_lifetime": False},
                "serper": {"used": 100, "limit": 2200, "remaining": 2100, "is_lifetime": True},
            },
            "circuit_breakers": {
                "firecrawl": {"state": "closed", "failures": 0},
                "scrapedo": {"state": "closed", "failures": 0},
                "serper": {"state": "closed", "failures": 0},
            },
        }
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert "providers" in data
            assert "circuit_breakers" in data
            assert "period" in data
            assert "openai" in data
            assert "comparisons_this_month" in data
            assert "avg_cost_per_comparison" in data
            assert "fixed_costs_monthly" in data
            assert "estimated_monthly_total" in data

    def test_requires_admin_key(self):
        resp = client.get("/api/v1/admin/costs")
        assert resp.status_code in (403, 422)

    def test_rejects_wrong_key(self):
        resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code == 403

    def test_fixed_costs_value(self):
        mock_summary = {
            "providers": {}, "circuit_breakers": {},
        }
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            data = resp.json()
            assert data["fixed_costs_monthly"] == 30.00

    def test_zero_comparisons_avg_cost(self):
        mock_summary = {
            "providers": {}, "circuit_breakers": {},
        }
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            data = resp.json()
            assert data["avg_cost_per_comparison"] == 0
            assert data["comparisons_this_month"] == 0

    def test_supabase_error_graceful(self):
        """Supabase errors should not crash the endpoint."""
        mock_summary = {
            "providers": {}, "circuit_breakers": {},
        }
        mock_supabase = MagicMock()
        mock_supabase.table.side_effect = Exception("Supabase down")
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=mock_supabase):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert data["openai"]["cost_usd"] == 0

    def test_period_format(self):
        mock_summary = {
            "providers": {}, "circuit_breakers": {},
        }
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            data = resp.json()
            # Period should be YYYY-MM format
            assert len(data["period"]) == 7
            assert data["period"][4] == "-"

    def test_openai_cost_with_data(self):
        """When Supabase returns comparison data, costs are summed."""
        mock_summary = {
            "providers": {}, "circuit_breakers": {},
        }
        mock_supabase = MagicMock()
        # First call: metadata query
        mock_result_meta = MagicMock()
        mock_result_meta.data = [
            {"metadata": {"total_cost": 0.01}},
            {"metadata": {"total_cost": 0.015}},
        ]
        # Second call: count query
        mock_result_count = MagicMock()
        mock_result_count.data = []
        mock_result_count.count = 2

        mock_table = MagicMock()
        call_count = {"n": 0}
        def select_side_effect(*args, **kwargs):
            call_count["n"] += 1
            mock_gte = MagicMock()
            if call_count["n"] == 1:
                mock_gte.execute.return_value = mock_result_meta
            else:
                mock_gte.execute.return_value = mock_result_count
            mock_select = MagicMock()
            mock_select.gte.return_value = mock_gte
            return mock_select
        mock_table.select.side_effect = select_side_effect
        mock_supabase.table.return_value = mock_table

        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=mock_supabase):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            data = resp.json()
            assert data["openai"]["cost_usd"] == 0.025
            assert data["comparisons_this_month"] == 2
            assert data["avg_cost_per_comparison"] == 0.0125
