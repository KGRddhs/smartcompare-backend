"""Bundle D Phase 2.5 — tests for /api/v1/home/* editorial endpoints.

Test counts per dispatcher anchor:
- /home/savings:    4 cases (threshold-not-met, threshold-met-with-savings,
                    threshold-met-with-zero-net-savings, schema_version=1 excluded)
- /home/smart-pick: 4 cases (new-user empty-state, returning-user-with-priorities,
                    returning-user-no-priorities, all-v1-hidden edge case)
- /home/trending:   3 cases (curated list seeds correctly, region fallback, shape stable)
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
    """Return an async dependency override that yields the canonical user dict."""
    async def _override():
        return {"id": user_id, "email": "test@qaren.app", "access_token": "fake-token"}
    return _override


def _patch_supabase_users_prefs(client_mock, prefs_dict: dict | None):
    """Wire `client.table('users').select(...).eq(...).single().execute()`
    to return a `MagicMock` with the given preferences dict (or None)."""
    user_resp = MagicMock()
    user_resp.data = {"preferences": prefs_dict} if prefs_dict is not None else {}
    # The chain: table().select().eq().single().execute()
    client_mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp


def _patch_supabase_comparisons(client_mock, rows: list[dict]):
    """Wire the comparisons-select chain to return `rows`.

    NOTE: this is called AFTER `_patch_supabase_users_prefs`. We use a
    side_effect to differentiate calls — `table('users')` vs
    `table('comparisons')` — because both end up calling `.execute()`.
    """
    comp_resp = MagicMock()
    comp_resp.data = rows

    # We need the chain that ends in `.execute()` on the comparisons path
    # to return `comp_resp`. The savings endpoint calls
    # client.table('comparisons').select('full_response').eq(...).eq(...).execute()
    # The smart-pick endpoint calls
    # client.table('comparisons').select('id, full_response, created_at').eq(...).eq(...).order(...).limit(...).execute()

    user_resp = MagicMock()
    user_resp.data = {"preferences": getattr(client_mock, "_prefs_data", {}) or {}}

    def _table_dispatch(name):
        m = MagicMock()
        if name == "users":
            # users → select → eq → single → execute returns prefs
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        else:
            # comparisons — both savings + smart-pick paths end at .execute()
            chain = m.select.return_value.eq.return_value.eq.return_value
            chain.execute.return_value = comp_resp
            chain.order.return_value.limit.return_value.execute.return_value = comp_resp
        return m
    client_mock.table.side_effect = _table_dispatch


def _comparison_row(
    winner_idx: int,
    p0_name: str = "Apple iPhone 15",
    p0_brand: str = "Apple",
    p0_price: float = 329.0,
    p1_name: str = "Galaxy S24",
    p1_brand: str = "Samsung",
    p1_price: float = 299.0,
    *,
    id_: str = "comp-1",
    dim_winners: dict | None = None,
):
    """Shape a comparison row matching `comparisons.full_response` v2 contract."""
    return {
        "id": id_,
        "created_at": "2026-05-23T00:00:00Z",
        "full_response": {
            "winner_index": winner_idx,
            "products": [
                {
                    "brand": p0_brand,
                    "name": p0_name,
                    "price": {"amount": p0_price, "currency": "BHD"},
                },
                {
                    "brand": p1_brand,
                    "name": p1_name,
                    "price": {"amount": p1_price, "currency": "BHD"},
                },
            ],
            "scoring": {"dimension_winners": dim_winners or {}},
        },
    }


@pytest.fixture(autouse=True)
def _flush_overrides_and_cache():
    """Per-test cleanup of dependency overrides + Redis stub."""
    yield
    app.dependency_overrides.clear()


# =============================================================================
# /api/v1/home/savings
# =============================================================================


class TestHomeSavings:

    def test_threshold_not_met_returns_threshold_met_false(self):
        """Anchor case: decisions_count=1 → threshold_met=False (FE hides banner)."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(winner_idx=0, p0_price=200, p1_price=250)]
        supabase = MagicMock()
        _patch_supabase_comparisons(supabase, rows)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decisions_count"] == 1
        assert body["threshold_met"] is False
        assert body["savings_bhd"] == 50.0  # 250 - 200 = 50

    def test_threshold_met_with_real_savings(self):
        """4 winning-cheaper rows → savings_bhd > 0, threshold_met=True."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [
            _comparison_row(winner_idx=0, p0_price=100, p1_price=150, id_="a"),  # 50 saved
            _comparison_row(winner_idx=0, p0_price=200, p1_price=220, id_="b"),  # 20 saved
            _comparison_row(winner_idx=1, p0_price=400, p1_price=300, id_="c"),  # 100 saved
            _comparison_row(winner_idx=1, p0_price=80, p1_price=75, id_="d"),    # 5 saved
        ]
        supabase = MagicMock()
        _patch_supabase_comparisons(supabase, rows)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decisions_count"] == 4
        assert body["threshold_met"] is True
        assert body["savings_bhd"] == 175.0  # 50 + 20 + 100 + 5

    def test_threshold_met_with_zero_net_savings(self):
        """User who consistently picks pricier winner → 0 saved, banner still shown
        when count >= 3."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # All winners are PRICIER than losers — max(0, ...) clamps to 0
        rows = [
            _comparison_row(winner_idx=0, p0_price=150, p1_price=100, id_="a"),  # 0 saved (loser cheaper)
            _comparison_row(winner_idx=0, p0_price=200, p1_price=180, id_="b"),  # 0 saved
            _comparison_row(winner_idx=1, p0_price=80, p1_price=120, id_="c"),   # 0 saved
        ]
        supabase = MagicMock()
        _patch_supabase_comparisons(supabase, rows)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["savings_bhd"] == 0.0
        assert body["decisions_count"] == 3
        assert body["threshold_met"] is True

    def test_only_v2_rows_aggregated(self):
        """Schema_version=1 rows MUST NOT appear in the aggregate.

        Verifies the .eq('schema_version', 2) filter is applied on the
        SELECT chain by capturing the eq() call args on the comparisons
        table mock.
        """
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # Build a comparisons mock that records each .eq() call
        comparisons_table_mock = MagicMock()
        all_eq_calls: list[tuple] = []

        def _record_eq(*args, **kwargs):
            all_eq_calls.append(args)
            return comparisons_table_mock.select.return_value.eq.return_value
        comparisons_table_mock.select.return_value.eq.side_effect = _record_eq
        # First-level eq returns a chain that also has .eq().execute()
        comp_resp = MagicMock(); comp_resp.data = [_comparison_row(winner_idx=0, p0_price=200, p1_price=250)]
        comparisons_table_mock.select.return_value.eq.return_value.eq.side_effect = _record_eq
        comparisons_table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = comp_resp

        user_resp = MagicMock(); user_resp.data = {"preferences": {}}
        users_table_mock = MagicMock()
        users_table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: (
            users_table_mock if name == "users" else comparisons_table_mock
        )

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        # One of the eq() calls must be ('schema_version', 2)
        assert ("schema_version", 2) in all_eq_calls, (
            f"schema_version=2 filter not applied; recorded eq calls: {all_eq_calls}"
        )


# =============================================================================
# /api/v1/home/smart-pick
# =============================================================================


class TestHomeSmartPick:

    def test_new_user_zero_comparisons_returns_empty_state(self):
        """New user (no comparisons) → empty_state=True + cta_text_key set."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = MagicMock()
        _patch_supabase_comparisons(supabase, [])  # zero rows
        # Also patch the users prefs read
        user_resp = MagicMock(); user_resp.data = {"preferences": {}}

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                comp_resp = MagicMock(); comp_resp.data = []
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["empty_state"] is True
        assert body["smart_pick"] is None
        assert body["cta_text_key"] == "home.smart_pick.empty_cta"

    def test_returning_user_with_priorities_matches_dim_winner(self):
        """User with priorities=['camera_quality'] + comparison whose winner
        won the 'camera_quality_score' dim → priority_match reason."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # Build a row where winner_index=0 won the camera_quality dim
        rows = [_comparison_row(
            winner_idx=0,
            p0_brand="Apple", p0_name="iPhone 15",
            p1_brand="Samsung", p1_name="Galaxy S24",
            dim_winners={"camera_quality_score": "Apple iPhone 15"},
        )]
        supabase = MagicMock()
        user_resp = MagicMock(); user_resp.data = {"preferences": {"priorities": ["camera_quality", "price"]}}
        comp_resp = MagicMock(); comp_resp.data = rows

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["empty_state"] is False
        assert body["smart_pick"] is not None
        pick = body["smart_pick"]
        assert pick["winner_name"] == "Apple iPhone 15"
        assert pick["runner_up_name"] == "Samsung Galaxy S24"
        assert pick["reason_key"] == "home.smart_pick.reason.priority_match"
        assert pick["reason_params"]["priority"] == "camera_quality"

    def test_returning_user_no_priorities_falls_back_to_recent_winner(self):
        """User with empty priorities but with comparisons → reason_key
        = 'recent_winner' (NOT priority_match)."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(winner_idx=1, p0_brand="A", p0_name="X", p1_brand="B", p1_name="Y")]
        supabase = MagicMock()
        user_resp = MagicMock(); user_resp.data = {"preferences": {}}  # no priorities
        comp_resp = MagicMock(); comp_resp.data = rows

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["empty_state"] is False
        assert body["smart_pick"]["reason_key"] == "home.smart_pick.reason.recent_winner"
        # No priority param when there's no priority match
        assert body["smart_pick"]["reason_params"] == {}

    def test_all_v1_rows_hidden_returns_empty_state(self):
        """Per Migration 026 invariant — v1 rows are filtered out by the
        SELECT chain at .eq('schema_version', 2). If user's ONLY rows
        are v1, the query returns empty → empty_state=True."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = MagicMock()
        user_resp = MagicMock(); user_resp.data = {"preferences": {"priorities": ["price"]}}
        # Query returns ZERO rows because .eq('schema_version', 2) filtered v1 out
        comp_resp = MagicMock(); comp_resp.data = []

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["empty_state"] is True
        assert body["smart_pick"] is None


# =============================================================================
# /api/v1/home/trending
# =============================================================================


class TestHomeTrending:

    def test_curated_list_seeds_correctly_for_bahrain(self):
        """Default region (bahrain) returns the curated list with non-empty entries."""
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending?region=bahrain")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["region"] == "bahrain"
        assert len(body["trending"]) > 0
        # Validate response shape per entry
        first = body["trending"][0]
        assert set(first.keys()) == {"query", "view_count", "region"}
        assert first["region"] == "bahrain"
        assert isinstance(first["view_count"], int)
        assert isinstance(first["query"], str)

    def test_region_fallback_when_missing(self):
        """No `?region=` → fall back to default (bahrain) when user is
        unauthenticated."""
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["region"] == "bahrain"  # default fallback

    def test_invalid_region_falls_back_to_default(self):
        """Unknown region → fall back to default, not 400."""
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending?region=mars")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["region"] == "bahrain"
