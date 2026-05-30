"""Bundle D Phase 2.6 — tests for /api/v1/profile/* editorial endpoints.

Test counts per dispatcher anchor:
- /profile/recent-decisions: 4 cases (empty, 1-row, 3-rows, schema_version=1 excluded)
- /profile/monthly-stats:    4 cases (threshold-not-met, threshold-met, prior-month excluded, bonus credits graceful)
- /profile/priorities-weighted: 4 cases (empty, with sensitivity, uniform fallback, bad data tolerance)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# =============================================================================
# Shared fixtures
# =============================================================================


def _fake_user(user_id: str = "test-user-id"):
    async def _override():
        return {"id": user_id, "email": "test@qaren.app", "access_token": "fake-token"}
    return _override


def _comparison_row(
    winner_idx: int,
    p0_name: str = "iPhone 15",
    p0_brand: str = "Apple",
    p0_price: float = 329.0,
    p1_name: str = "Galaxy S24",
    p1_brand: str = "Samsung",
    p1_price: float = 299.0,
    *,
    id_: str = "comp-1",
    created_at: str = "2026-05-23T10:00:00Z",
):
    return {
        "id": id_,
        "created_at": created_at,
        "full_response": {
            "winner_index": winner_idx,
            "products": [
                {"brand": p0_brand, "name": p0_name,
                 "price": {"amount": p0_price, "currency": "BHD"}},
                {"brand": p1_brand, "name": p1_name,
                 "price": {"amount": p1_price, "currency": "BHD"}},
            ],
        },
    }


@pytest.fixture(autouse=True)
def _flush_overrides():
    yield
    app.dependency_overrides.clear()


# =============================================================================
# /api/v1/profile/recent-decisions
# =============================================================================


class TestRecentDecisions:

    def test_zero_comparisons_returns_empty_state(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = []
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["empty_state"] is True
        assert body["recent"] == []
        assert body["cta_text_key"] == "profile.recent_decisions.empty_cta"

    def test_one_row_returns_one_recent_entry(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(winner_idx=0, id_="x")]
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = rows
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["empty_state"] is False
        assert len(body["recent"]) == 1
        entry = body["recent"][0]
        assert entry["comparison_id"] == "x"
        assert entry["winner_name"] == "Apple iPhone 15"
        assert entry["runner_up_name"] == "Samsung Galaxy S24"
        assert entry["created_at"] == "2026-05-23T10:00:00Z"

    def test_three_rows_returns_three_recent_entries(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [
            _comparison_row(winner_idx=0, id_="a", created_at="2026-05-23T10:00:00Z"),
            _comparison_row(winner_idx=1, id_="b", created_at="2026-05-22T10:00:00Z",
                          p0_name="Pixel 8", p1_name="iPhone 14"),
            _comparison_row(winner_idx=0, id_="c", created_at="2026-05-21T10:00:00Z",
                          p0_brand="Sony", p0_name="WH-1000XM5",
                          p1_brand="Bose", p1_name="QC Ultra"),
        ]
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = rows
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["empty_state"] is False
        assert len(body["recent"]) == 3
        assert [e["comparison_id"] for e in body["recent"]] == ["a", "b", "c"]
        assert body["recent"][2]["winner_name"] == "Sony WH-1000XM5"

    def test_schema_version_2_filter_applied(self):
        """Verifies .eq('schema_version', 2) is in the SELECT chain."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        all_eq_calls: list[tuple] = []
        comparisons_table_mock = MagicMock()

        def _record_eq(*args, **kwargs):
            all_eq_calls.append(args)
            return comparisons_table_mock.select.return_value.eq.return_value
        comparisons_table_mock.select.return_value.eq.side_effect = _record_eq
        comparisons_table_mock.select.return_value.eq.return_value.eq.side_effect = _record_eq
        comp_resp = MagicMock(); comp_resp.data = []
        comparisons_table_mock.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp

        supabase = MagicMock()
        supabase.table.return_value = comparisons_table_mock

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        assert ("schema_version", 2) in all_eq_calls, (
            f"schema_version=2 filter not applied; recorded eq calls: {all_eq_calls}"
        )


# =============================================================================
# /api/v1/profile/monthly-stats
# =============================================================================


class TestMonthlyStats:

    def _patch_supabase(self, comp_rows: list[dict], rr_rows: list[dict]):
        comp_resp = MagicMock(); comp_resp.data = comp_rows
        rr_resp = MagicMock(); rr_resp.data = rr_rows

        def _table_dispatch(name):
            m = MagicMock()
            if name == "comparisons":
                m.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = comp_resp
            elif name == "referral_redemptions":
                m.select.return_value.eq.return_value.gte.return_value.execute.return_value = rr_resp
            return m
        supabase = MagicMock()
        supabase.table.side_effect = _table_dispatch
        return supabase

    def test_threshold_not_met_count_under_3(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(winner_idx=0, p0_price=200, p1_price=250)]
        supabase = self._patch_supabase(rows, [])

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/monthly-stats", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["decisions_count"] == 1
        assert body["threshold_met"] is False
        assert body["savings_bhd"] == 50.0  # 250 - 200
        assert body["bonus_credits_this_month"] == 0
        assert body["month"]  # YYYY-MM string present

    def test_threshold_met_3_rows_with_savings(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [
            _comparison_row(winner_idx=0, p0_price=100, p1_price=150, id_="a"),  # 50
            _comparison_row(winner_idx=1, p0_price=300, p1_price=200, id_="b"),  # 100
            _comparison_row(winner_idx=0, p0_price=80, p1_price=120, id_="c"),   # 40
        ]
        # 1 referral redemption for 5 loop2 credits granted this month
        rr_rows = [{"loop2_comparisons_granted": 5, "created_at": "2026-05-15T10:00:00Z"}]
        supabase = self._patch_supabase(rows, rr_rows)

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/monthly-stats", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["decisions_count"] == 3
        assert body["threshold_met"] is True
        assert body["savings_bhd"] == 190.0
        assert body["bonus_credits_this_month"] == 5

    def test_prior_month_rows_excluded_via_gte(self):
        """Verifies the comparisons SELECT calls .gte('created_at', <month-start>).
        Recording the gte() args proves the filter is wired.
        """
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        gte_call_args: list[tuple] = []
        comparisons_mock = MagicMock()
        rr_mock = MagicMock()

        def _record_gte(*args, **kwargs):
            gte_call_args.append(args)
            return comparisons_mock.select.return_value.eq.return_value.eq.return_value.gte.return_value

        comp_resp = MagicMock(); comp_resp.data = []
        comparisons_mock.select.return_value.eq.return_value.eq.return_value.gte.side_effect = _record_gte
        comparisons_mock.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = comp_resp

        rr_resp = MagicMock(); rr_resp.data = []
        rr_mock.select.return_value.eq.return_value.gte.return_value.execute.return_value = rr_resp

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: (
            comparisons_mock if name == "comparisons" else rr_mock
        )

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/monthly-stats", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        # gte called once with ('created_at', '<isoformat string>')
        assert any(a[0] == "created_at" for a in gte_call_args)
        # The isoformat string is the first day of current UTC month
        month_iso = next(a[1] for a in gte_call_args if a[0] == "created_at")
        assert "T00:00:00" in month_iso  # midnight
        assert month_iso.endswith("+00:00")  # UTC tz

    def test_bonus_credits_graceful_on_referral_query_failure(self):
        """If referral_redemptions read fails, bonus_credits_this_month=0
        — endpoint does NOT 500. Frontend hides credits portion."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [
            _comparison_row(winner_idx=0, p0_price=100, p1_price=150, id_="a"),
            _comparison_row(winner_idx=0, p0_price=200, p1_price=220, id_="b"),
            _comparison_row(winner_idx=0, p0_price=80, p1_price=100, id_="c"),
        ]
        comp_resp = MagicMock(); comp_resp.data = rows

        # referral_redemptions raises
        def _table_dispatch(name):
            m = MagicMock()
            if name == "comparisons":
                m.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = comp_resp
            elif name == "referral_redemptions":
                m.select.return_value.eq.return_value.gte.return_value.execute.side_effect = RuntimeError("DB down")
            return m
        supabase = MagicMock()
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/monthly-stats", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["decisions_count"] == 3
        assert body["threshold_met"] is True
        assert body["bonus_credits_this_month"] == 0  # graceful zero


# =============================================================================
# /api/v1/profile/priorities-weighted
# =============================================================================


class TestPrioritiesWeighted:

    def _patch_users(self, prefs: dict, behavior_profile: dict):
        user_resp = MagicMock()
        user_resp.data = {"preferences": prefs, "behavior_profile": behavior_profile}
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        return supabase

    def test_empty_priorities_and_empty_sensitivity_returns_empty_state(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = self._patch_users({}, {})

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/priorities-weighted", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["empty_state"] is True
        assert body["priorities"] == []

    def test_priorities_with_sensitivity_weights(self):
        """Priorities populated AND dim_sensitivity has matching weights →
        weights are normalized as relative shares summing to ~100 (B3 Path A)."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = self._patch_users(
            prefs={"priorities": ["camera_quality", "battery_life", "build_quality"]},
            behavior_profile={
                "dimension_sensitivity": {
                    "camera_quality": 0.95,
                    "battery_life": 0.78,
                    "build_quality": 0.62,
                    "price": 0.40,  # not in priorities — should NOT appear
                },
            },
        )

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/priorities-weighted", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["empty_state"] is False
        assert len(body["priorities"]) == 3
        keys = [p["key"] for p in body["priorities"]]
        assert keys == ["camera_quality", "battery_life", "build_quality"]
        # Sum-to-100 Hamilton largest-remainder normalization (Path A R2).
        # total = 0.95+0.78+0.62 = 2.35
        #   camera_quality: 0.95/2.35*100 = 40.4255 → floor 40, frac 0.4255
        #   battery_life:   0.78/2.35*100 = 33.1915 → floor 33, frac 0.1915
        #   build_quality:  0.62/2.35*100 = 26.3830 → floor 26, frac 0.3830
        # floors sum = 99 → 1 leftover → largest remainder = camera_quality → 41.
        weights = {p["key"]: p["weight"] for p in body["priorities"]}
        assert weights["camera_quality"] == 41
        assert weights["battery_life"] == 33
        assert weights["build_quality"] == 26
        # Hamilton invariant: weights ALWAYS sum to exactly 100.
        assert sum(weights.values()) == 100
        for p in body["priorities"]:
            assert 0 <= p["weight"] <= 100
            assert p["label_key"] == f"priorities.{p['key']}"

    def test_priorities_without_sensitivity_uses_uniform(self):
        """preferences.priorities populated but behavior_profile.dimension_sensitivity
        is empty/missing → uniform weight 100 across all priorities."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = self._patch_users(
            prefs={"priorities": ["price", "quality", "latest_features"]},
            behavior_profile={},
        )

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/priorities-weighted", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["empty_state"] is False
        assert len(body["priorities"]) == 3
        # Sum-to-100 (B3 Path A): 3 equal weights → ~33 each
        weights = [p["weight"] for p in body["priorities"]]
        assert all(30 <= w <= 36 for w in weights)
        assert 97 <= sum(weights) <= 103

    def test_bad_dim_sensitivity_data_tolerated(self):
        """Garbage in dimension_sensitivity (None values, non-numeric strings)
        is filtered out — endpoint does NOT crash, returns valid response."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = self._patch_users(
            prefs={"priorities": ["camera_quality", "battery_life"]},
            behavior_profile={
                "dimension_sensitivity": {
                    "camera_quality": None,                    # filtered out
                    "battery_life": "garbage",                 # filtered out
                    "irrelevant_key": "more_garbage",          # filtered out
                },
            },
        )

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/priorities-weighted", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # All weights filtered → falls through to uniform 1.0 each, sum-to-100 → ~50 each
        assert body["empty_state"] is False
        assert len(body["priorities"]) == 2
        weights = [p["weight"] for p in body["priorities"]]
        assert all(45 <= w <= 55 for w in weights)
        assert 97 <= sum(weights) <= 103
