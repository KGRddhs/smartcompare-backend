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


@pytest.fixture(autouse=True)
def stub_tier15_hit_rate():
    """F1.6 — /admin/costs now calls get_tier15_hit_rate (Redis). I5.1/I5.0 add
    get_tier15_source_hits + get_burn_status (also Redis). Default-stub all
    three so the existing endpoint tests stay fast + network-free; the
    dedicated tests below override these with their own patch."""
    with patch("app.api.admin_routes.get_tier15_hit_rate", return_value={}), \
         patch("app.api.admin_routes.get_tier15_source_hits", return_value={}), \
         patch("app.api.admin_routes.get_burn_status", return_value={
             "used": 0, "limit": 2200, "threshold": 1760,
             "fraction": 0.0, "over_threshold": False,
         }):
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

    def test_tier1_5_hit_rate_block_present(self):
        """F1.6 — /admin/costs surfaces a tier1_5_hit_rate block (7-day,
        per-category) from the Redis escalation counters."""
        mock_summary = {"providers": {}, "circuit_breakers": {}}
        fake_agg = {
            "electronics": {"attempts": 8, "hits": 6, "hit_rate": 0.75},
            "grocery": {"attempts": 2, "hits": 0, "hit_rate": 0.0},
        }
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None), \
             patch("app.api.admin_routes.get_tier15_hit_rate", return_value=fake_agg):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert "tier1_5_hit_rate" in data
            block = data["tier1_5_hit_rate"]
            assert block["window_days"] == 7
            assert block["by_category"]["electronics"]["hit_rate"] == 0.75
            assert block["by_category"]["grocery"]["attempts"] == 2

    def test_tier1_5_hit_rate_fail_open(self):
        """If the aggregate raises (Redis hiccup), the endpoint still 200s
        with an empty by_category + by_source block."""
        mock_summary = {"providers": {}, "circuit_breakers": {}}
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None), \
             patch("app.api.admin_routes.get_tier15_hit_rate", side_effect=Exception("redis down")):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert data["tier1_5_hit_rate"]["by_category"] == {}
            assert data["tier1_5_hit_rate"]["by_source"] == {}

    def test_tier1_5_by_source_block_present(self):
        """I5.1 — /admin/costs surfaces the per-domain source-hit breakdown so
        the registry-vs-legacy attribution residual is visible."""
        mock_summary = {"providers": {}, "circuit_breakers": {}}
        fake_sources = {"shopalmoayyed.com": 9, "talabat.com": 3}
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None), \
             patch("app.api.admin_routes.get_tier15_hit_rate", return_value={}), \
             patch("app.api.admin_routes.get_tier15_source_hits", return_value=fake_sources):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert data["tier1_5_hit_rate"]["by_source"] == fake_sources

    def test_serper_burn_block_present(self):
        """I5.0 — /admin/costs surfaces the Serper burn status (run-integrity
        canary for the 80% ceiling)."""
        mock_summary = {"providers": {}, "circuit_breakers": {}}
        fake_burn = {
            "used": 1800, "limit": 2200, "threshold": 1760,
            "fraction": 0.8182, "over_threshold": True,
        }
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None), \
             patch("app.api.admin_routes.get_burn_status", return_value=fake_burn):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert data["serper_burn"] == fake_burn
            assert data["serper_burn"]["over_threshold"] is True

    def test_serper_burn_fail_open(self):
        """If burn-status raises, the endpoint still 200s with an empty block."""
        mock_summary = {"providers": {}, "circuit_breakers": {}}
        with patch("app.api.admin_routes.get_usage_summary", return_value=mock_summary), \
             patch("app.api.admin_routes.get_supabase_client", return_value=None), \
             patch("app.api.admin_routes.get_burn_status", side_effect=Exception("redis down")):
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert data["serper_burn"] == {}

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
