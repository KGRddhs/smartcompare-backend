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
    category: str | None = None,
    winner_declaration: str | None = None,
    p0_specs: dict | None = None,
    p1_specs: dict | None = None,
    p0_image_url: str | None = "__UNSET__",  # sentinel: don't add key when "__UNSET__"
    p1_image_url: str | None = "__UNSET__",
    created_at: str = "2026-05-23T00:00:00Z",
):
    """Shape a comparison row matching `comparisons.full_response` v2 contract.

    Bundle E B4.3b: category / winner_declaration / per-product specs / created_at
    are optional fixture knobs so smart-pick extension tests can drive the
    `category` / `verdict_short` / `sub` / `updated_at` extraction paths.
    """
    p0 = {
        "brand": p0_brand,
        "name": p0_name,
        "price": {"amount": p0_price, "currency": "BHD"},
    }
    p1 = {
        "brand": p1_brand,
        "name": p1_name,
        "price": {"amount": p1_price, "currency": "BHD"},
    }
    if p0_image_url != "__UNSET__":
        p0["image_url"] = p0_image_url
    if p1_image_url != "__UNSET__":
        p1["image_url"] = p1_image_url
    full = {
        "winner_index": winner_idx,
        "products": [p0, p1],
        "scoring": {"dimension_winners": dim_winners or {}},
    }
    if category is not None:
        full["category"] = category
    if winner_declaration is not None:
        full["overview"] = {"winner": {"declaration": winner_declaration}}
    if p0_specs is not None or p1_specs is not None:
        full["specs"] = {
            "products": [
                {"brand": p0_brand, "name": p0_name, "specs": p0_specs or {}},
                {"brand": p1_brand, "name": p1_name, "specs": p1_specs or {}},
            ],
        }
    return {
        "id": id_,
        "created_at": created_at,
        "full_response": full,
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
# /api/v1/home/savings — issue #116: SQL-side aggregate behind
# ENABLE_HOME_SAVINGS_AGGREGATE (default OFF)
# =============================================================================


def _rpc_supabase(rpc_rows=None, rpc_calls=None, rpc_raises=None, table_rows=None,
                  table_raises=None):
    """Stub supabase client recording .rpc() calls and optionally serving the
    legacy .table('comparisons') chain (for fallback-path tests)."""
    import threading as _threading

    supabase = MagicMock()

    def _rpc(name, params=None):
        m = MagicMock()

        def _execute():
            if rpc_calls is not None:
                rpc_calls.append((name, params, _threading.current_thread()))
            if rpc_raises is not None:
                raise rpc_raises
            resp = MagicMock()
            resp.data = rpc_rows if rpc_rows is not None else []
            return resp
        m.execute.side_effect = _execute
        return m
    supabase.rpc.side_effect = _rpc

    def _table_dispatch(name):
        m = MagicMock()
        if name == "users":
            user_resp = MagicMock(); user_resp.data = {"preferences": {}}
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        else:
            chain = m.select.return_value.eq.return_value.eq.return_value
            if table_raises is not None:
                chain.execute.side_effect = table_raises
            else:
                comp_resp = MagicMock(); comp_resp.data = table_rows or []
                chain.execute.return_value = comp_resp
        return m
    supabase.table.side_effect = _table_dispatch
    return supabase


class TestHomeSavingsAggregate:
    """Issue #116 — /home/savings must not pull every full_response blob."""

    def _call(self, supabase):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()
        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            return client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})

    def test_savings_query_does_not_select_full_response(self, monkeypatch):
        """Flag ON: no .select() containing full_response may run — the
        aggregate is computed server-side."""
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        select_args: list = []
        supabase = _rpc_supabase(rpc_rows=[{"savings_bhd": 0, "decisions_count": 0}])
        inner_dispatch = supabase.table.side_effect

        def _spy_table(name):
            m = inner_dispatch(name)
            orig_select = m.select.side_effect or (lambda *a, **k: m.select.return_value)

            def _spy_select(*a, **k):
                select_args.append(a)
                return orig_select(*a, **k)
            m.select.side_effect = _spy_select
            return m
        supabase.table.side_effect = _spy_table

        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        flat = [arg for call_ in select_args for arg in call_]
        assert not any("full_response" in str(a) for a in flat), (
            f"savings still selects full_response: {select_args}"
        )

    def test_savings_uses_sql_aggregate_rpc(self, monkeypatch):
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        rpc_calls: list = []
        supabase = _rpc_supabase(
            rpc_rows=[{"savings_bhd": 12.5, "decisions_count": 4}],
            rpc_calls=rpc_calls,
        )
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert len(rpc_calls) == 1, f"expected exactly one rpc call, got {rpc_calls}"
        name, params, _ = rpc_calls[0]
        assert name == "home_savings_aggregate"
        assert params == {"p_user_id": "test-user-id"}
        table_names = [c.args[0] for c in supabase.table.call_args_list]
        assert "comparisons" not in table_names, (
            f"flag ON must not scan comparisons; table() calls: {table_names}"
        )
        body = resp.json()
        assert body == {"savings_bhd": 12.5, "decisions_count": 4, "threshold_met": True}

    def test_savings_query_is_bounded(self, monkeypatch):
        """RPC path: the round trip returns exactly ONE aggregate row — cost
        does not grow with the user's history."""
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        rpc_calls: list = []
        supabase = _rpc_supabase(
            rpc_rows=[{"savings_bhd": 999.99, "decisions_count": 1000}],
            rpc_calls=rpc_calls,
        )
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert len(rpc_calls) == 1
        # A 1000-comparison user still costs one row, not 1000 blobs.
        assert resp.json()["decisions_count"] == 1000

    def test_savings_offloads_via_run_db_when_flag_on(self, monkeypatch):
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
        from app.utils import db_offload
        real_to_thread = db_offload.asyncio.to_thread
        calls = {"n": 0}

        async def spy_to_thread(fn, *a, **k):
            calls["n"] += 1
            return await real_to_thread(fn, *a, **k)
        monkeypatch.setattr(db_offload.asyncio, "to_thread", spy_to_thread)

        supabase = _rpc_supabase(rpc_rows=[{"savings_bhd": 1.0, "decisions_count": 1}])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert calls["n"] >= 1, "rpc execute did not route through asyncio.to_thread"

    def test_savings_inline_when_offload_flag_off(self, monkeypatch):
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
        from app.utils import db_offload
        real_to_thread = db_offload.asyncio.to_thread
        calls = {"n": 0}

        async def spy_to_thread(fn, *a, **k):
            calls["n"] += 1
            return await real_to_thread(fn, *a, **k)
        monkeypatch.setattr(db_offload.asyncio, "to_thread", spy_to_thread)

        supabase = _rpc_supabase(rpc_rows=[{"savings_bhd": 1.0, "decisions_count": 1}])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert calls["n"] == 0, "flag OFF must run the rpc inline (byte-identical)"

    def test_savings_redis_uses_async_dispatch_when_flag_on(self, monkeypatch):
        """ENABLE_ASYNC_REDIS_OFFLOAD=true routes _redis_get/_redis_set through
        asyncio.to_thread via a home_routes-local dispatch (so this patch on
        home_routes._redis_get intercepts BOTH branches)."""
        monkeypatch.delenv("ENABLE_HOME_SAVINGS_AGGREGATE", raising=False)
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
        import asyncio as _asyncio
        real_to_thread = _asyncio.to_thread
        calls = {"n": 0}

        async def spy_to_thread(fn, *a, **k):
            calls["n"] += 1
            return await real_to_thread(fn, *a, **k)
        monkeypatch.setattr(_asyncio, "to_thread", spy_to_thread)

        supabase = _rpc_supabase(table_rows=[])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert calls["n"] >= 2, (
            "redis get+set must dispatch via asyncio.to_thread when "
            "ENABLE_ASYNC_REDIS_OFFLOAD is on"
        )

    def test_savings_redis_inline_when_flag_off(self, monkeypatch):
        monkeypatch.delenv("ENABLE_HOME_SAVINGS_AGGREGATE", raising=False)
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
        import asyncio as _asyncio
        real_to_thread = _asyncio.to_thread
        calls = {"n": 0}

        async def spy_to_thread(fn, *a, **k):
            calls["n"] += 1
            return await real_to_thread(fn, *a, **k)
        monkeypatch.setattr(_asyncio, "to_thread", spy_to_thread)

        supabase = _rpc_supabase(table_rows=[])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert calls["n"] == 0, "OFF branch must stay inline on the event loop"

    def test_savings_payload_shape_unchanged(self, monkeypatch):
        """Flag ON returns exactly the legacy keys, savings rounded to 2dp."""
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        supabase = _rpc_supabase(rpc_rows=[{"savings_bhd": "123.456", "decisions_count": 3}])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body.keys()) == {"savings_bhd", "decisions_count", "threshold_met"}
        assert body["savings_bhd"] == 123.46
        assert body["decisions_count"] == 3
        assert body["threshold_met"] is True

    def test_savings_rpc_failure_falls_back_to_legacy_scan(self, monkeypatch):
        """Migration 036 not applied (rpc raises) must NOT zero the banner —
        the endpoint degrades to the inline scan (spec_spine fallback pattern)."""
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        supabase = _rpc_supabase(
            rpc_raises=RuntimeError("function home_savings_aggregate does not exist"),
            table_rows=[_comparison_row(winner_idx=0, p0_price=200, p1_price=250)],
        )
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decisions_count"] == 1
        assert body["savings_bhd"] == 50.0

    def test_savings_db_failure_returns_empty_payload_not_500(self, monkeypatch):
        """Both the rpc AND the legacy scan raising still yields 200 + zeros."""
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        supabase = _rpc_supabase(
            rpc_raises=RuntimeError("db down"),
            table_raises=RuntimeError("db down"),
        )
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {
            "savings_bhd": 0.0, "decisions_count": 0, "threshold_met": False,
        }

    def test_savings_zero_rows_returns_threshold_not_met(self, monkeypatch):
        monkeypatch.setenv("ENABLE_HOME_SAVINGS_AGGREGATE", "true")
        supabase = _rpc_supabase(rpc_rows=[{"savings_bhd": 0, "decisions_count": 0}])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["threshold_met"] is False
        assert body["savings_bhd"] == 0.0
        assert body["decisions_count"] == 0

    # ------------------------------------------------------------------
    # Python-path parity pins (flag OFF) — the rules the SQL mirrors.
    # ------------------------------------------------------------------

    def test_savings_skips_non_bhd_rows(self):
        row = _comparison_row(winner_idx=0, p0_price=100, p1_price=150)
        row["full_response"]["products"][0]["price"]["currency"] = "SAR"
        supabase = MagicMock()
        _patch_supabase_comparisons(supabase, [row])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decisions_count"] == 0
        assert body["savings_bhd"] == 0.0

    def test_savings_skips_bad_winner_index(self):
        row = _comparison_row(winner_idx=2, p0_price=100, p1_price=150)
        supabase = MagicMock()
        _patch_supabase_comparisons(supabase, [row])
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decisions_count"] == 0
        assert body["savings_bhd"] == 0.0

    def test_savings_never_negative(self):
        # Winner pricier than loser: contributes 0.0, counted, never negative.
        supabase = MagicMock()
        _patch_supabase_comparisons(
            supabase, [_comparison_row(winner_idx=0, p0_price=300, p1_price=100)]
        )
        resp = self._call(supabase)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["savings_bhd"] == 0.0
        assert body["decisions_count"] == 1

    # ------------------------------------------------------------------
    # Static guard on the migration SQL — the unit tests cannot execute
    # Postgres, so pin the load-bearing predicates textually.
    # ------------------------------------------------------------------

    def test_migration_sql_mirrors_python_rules(self):
        from pathlib import Path
        sql_path = (
            Path(__file__).resolve().parent.parent
            / "migrations" / "036_home_savings_aggregate.sql"
        )
        assert sql_path.exists(), "migrations/036_home_savings_aggregate.sql missing"
        sql = sql_path.read_text(encoding="utf-8")
        assert "home_savings_aggregate" in sql
        assert "GREATEST" in sql, "must clamp negative savings to 0"
        assert "'BHD'" in sql, "must enforce the BHD-only rule on both sides"
        assert "schema_version" in sql, "must filter schema_version = 2"
        assert "SECURITY INVOKER" in sql, (
            "must be SECURITY INVOKER so RLS keeps a caller inside their own rows"
        )
        assert "COALESCE" in sql, "zero rows must yield 0, not NULL"


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

    def test_dimension_sensitivity_fallback_when_priorities_empty(self):
        """Dispatcher 2026-05-23 ack: when preferences.priorities is empty
        (user skipped onboarding step 9), the endpoint falls back to the
        TOP entry of behavior_profile.dimension_sensitivity and uses that
        as the synthesized priority for priority_match scoring.
        """
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # Comparison where the winner won the 'camera_quality_score' dim
        rows = [_comparison_row(
            winner_idx=0,
            p0_brand="Apple", p0_name="iPhone 15",
            p1_brand="Samsung", p1_name="Galaxy S24",
            dim_winners={"camera_quality_score": "Apple iPhone 15"},
        )]
        supabase = MagicMock()
        # NO priorities in preferences; HAS dimension_sensitivity with
        # camera_quality as the TOP entry (weight 0.8)
        user_resp = MagicMock()
        user_resp.data = {
            "preferences": {},
            "behavior_profile": {
                "dimension_sensitivity": {
                    "camera_quality": 0.8,
                    "battery": 0.3,
                    "price": 0.1,
                },
            },
        }
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
        pick = body["smart_pick"]
        # The fallback synthesized 'camera_quality' as the priority →
        # priority_match should fire because the winner won the
        # 'camera_quality_score' dim.
        assert pick["reason_key"] == "home.smart_pick.reason.priority_match"
        assert pick["reason_params"]["priority"] == "camera_quality"

    def test_empty_priorities_and_empty_dim_sensitivity_falls_to_recent(self):
        """When BOTH preferences.priorities AND behavior_profile.dimension_sensitivity
        are empty/missing, the endpoint falls through to recent_winner (NOT
        empty state, as long as there's at least one v2 comparison)."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(winner_idx=0)]
        supabase = MagicMock()
        user_resp = MagicMock()
        user_resp.data = {
            "preferences": {},
            "behavior_profile": {"dimension_sensitivity": {}},
        }
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

    # -------------------------------------------------------------------------
    # Bundle E B4.3b — JSX-wins extension fields
    # -------------------------------------------------------------------------
    def test_extension_fields_present_when_data_available(self):
        """Per JSX HomeScreen.jsx:438-501, SmartPickCard renders a category
        eyebrow pill, an 'Updated today' chip, per-product `sub` (e.g. '128GB'),
        and a short verdict sentence. Bundle E B4.3b extends the response with
        `category`, `updated_at`, `products[*].sub`, and `verdict_short` —
        populated from the underlying comparison row when present.
        """
        from app.api.auth_routes import get_current_user
        from datetime import datetime, timezone
        app.dependency_overrides[get_current_user] = _fake_user()

        # created_at 30 minutes ago — should yield rel string like "Updated 30m ago"
        # or similar based on the server-side helper.
        now = datetime.now(timezone.utc)
        recent_iso = now.isoformat()

        rows = [_comparison_row(
            winner_idx=0,
            p0_brand="Apple", p0_name="iPhone 15", p0_price=329.0,
            p1_brand="Samsung", p1_name="Galaxy S24", p1_price=299.0,
            category="electronics",
            winner_declaration=(
                "iPhone 15 takes this round — sharper photo pipeline and a faster A17 "
                "chip beat the Galaxy S24 on every benchmark we cared about."
            ),
            p0_specs={"storage": "128GB", "color": "Black"},
            p1_specs={"storage": "256GB", "color": "Phantom Black"},
            created_at=recent_iso,
        )]
        user_resp = MagicMock(); user_resp.data = {"preferences": {"priorities": ["price"]}}
        comp_resp = MagicMock(); comp_resp.data = rows

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase = MagicMock()
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        pick = resp.json()["smart_pick"]
        assert pick is not None

        # category — top-level on smart_pick
        assert pick["category"] == "electronics"

        # updated_at — server-computed rel string (short form)
        assert isinstance(pick["updated_at"], str)
        assert len(pick["updated_at"]) > 0
        # Should reflect "just now" / "Xm ago" / "Today" — never raw ISO
        assert "T" not in pick["updated_at"], (
            f"updated_at should be a rel string, not raw ISO: {pick['updated_at']!r}"
        )

        # per-product sub — storage spec when available
        assert "winner_sub" in pick
        assert "runner_up_sub" in pick
        assert pick["winner_sub"] == "128GB"
        assert pick["runner_up_sub"] == "256GB"

        # verdict_short — truncated winner_declaration (no banned scary vocab)
        vs = pick["verdict_short"]
        assert isinstance(vs, str) and len(vs) > 0
        assert len(vs) <= 160, f"verdict_short too long: {len(vs)} chars: {vs!r}"
        # First few words must match the source declaration prefix
        assert vs.lower().startswith("iphone 15 takes")

    def test_extension_fields_null_when_data_absent(self):
        """When the underlying full_response lacks category / verdict /
        product specs, the extension fields are NULL — frontend hides the
        surround. Per dispatcher rule: 'don't fabricate.'
        """
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # Minimal row — no category, no winner_declaration, no specs
        rows = [_comparison_row(winner_idx=0)]
        user_resp = MagicMock(); user_resp.data = {"preferences": {}}
        comp_resp = MagicMock(); comp_resp.data = rows

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase = MagicMock()
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        pick = resp.json()["smart_pick"]
        assert pick is not None
        # Fields must be PRESENT but NULL — frontend then skips render lines
        assert pick["category"] is None
        assert pick["winner_sub"] is None
        assert pick["runner_up_sub"] is None
        assert pick["verdict_short"] is None
        # updated_at always computed from comparisons.created_at (always present
        # in DB-shaped row) → never null even when other fields are.
        assert isinstance(pick["updated_at"], str)

    def test_legacy_fields_survive_one_release_cycle(self):
        """Bundle E backwards-compat: the legacy {winner_name, runner_up_name,
        winner_price_bhd, runner_up_price_bhd, reason_key, reason_params} fields
        survive alongside the new {category, updated_at, winner_sub,
        runner_up_sub, verdict_short} — one release cycle (same pattern as
        scoring_v2)."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(winner_idx=0, category="skincare")]
        user_resp = MagicMock(); user_resp.data = {"preferences": {}}
        comp_resp = MagicMock(); comp_resp.data = rows

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase = MagicMock()
        supabase.table.side_effect = _table_dispatch

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        pick = resp.json()["smart_pick"]
        # Legacy fields still emitted
        for legacy_key in (
            "winner_name", "runner_up_name", "winner_price_bhd",
            "runner_up_price_bhd", "reason_key", "reason_params",
        ):
            assert legacy_key in pick, (
                f"legacy field {legacy_key!r} must survive one release cycle; "
                f"pick keys: {sorted(pick.keys())}"
            )


# =============================================================================
# Bundle E S3 A3 — /home/smart-pick image_url extension
# =============================================================================


class TestHomeSmartPickImageUrl:
    """Bundle E S3 A3 — winner_image_url + runner_up_image_url extracted from
    the comparison row's products[*].image_url field (string OR null).

    Source of truth: smart_pick reads `comparisons.full_response`. Old rows
    saved BEFORE S3 deploy lack image_url → null. New rows have it.

    Contract for A4 (FE consumer):
      smart_pick.winner_image_url: string | null
      smart_pick.runner_up_image_url: string | null
    """

    def _setup_smart_pick_row(self, supabase, comp_resp, priorities=None):
        """Helper — wire up the table dispatch for smart-pick tests."""
        prefs = {"priorities": priorities} if priorities else {}
        user_resp = MagicMock()
        user_resp.data = {"preferences": prefs}

        def _table_dispatch(name):
            m = MagicMock()
            if name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
            else:
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            return m
        supabase.table.side_effect = _table_dispatch

    def test_both_products_have_image_urls_emitted_to_payload(self):
        """Both products in the source comparison have image_url strings →
        smart_pick.{winner,runner_up}_image_url are those strings."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(
            winner_idx=0,
            p0_brand="Apple", p0_name="iPhone 15",
            p1_brand="Samsung", p1_name="Galaxy S24",
            p0_image_url="https://example.com/iphone15.jpg",
            p1_image_url="https://example.com/galaxy.jpg",
        )]
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = rows
        self._setup_smart_pick_row(supabase, comp_resp)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        pick = resp.json()["smart_pick"]
        assert pick is not None
        assert pick["winner_image_url"] == "https://example.com/iphone15.jpg"
        assert pick["runner_up_image_url"] == "https://example.com/galaxy.jpg"

    def test_both_products_missing_image_url_emits_null(self):
        """Legacy comparison row saved BEFORE S3 deploy lacks image_url keys
        entirely → endpoint emits null for both (FE renders placeholder)."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # Default _comparison_row helper omits image_url keys (sentinel)
        rows = [_comparison_row(
            winner_idx=1,
            p0_brand="Apple", p0_name="iPhone 15",
            p1_brand="Samsung", p1_name="Galaxy S24",
        )]
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = rows
        self._setup_smart_pick_row(supabase, comp_resp)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        pick = resp.json()["smart_pick"]
        assert pick is not None
        assert pick["winner_image_url"] is None
        assert pick["runner_up_image_url"] is None
        # Keys MUST be present (FE relies on shape)
        assert "winner_image_url" in pick
        assert "runner_up_image_url" in pick

    def test_mixed_winner_has_image_runner_up_null(self):
        """One product has image_url, other doesn't — emit string + null."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # winner_idx=0 has image; winner_idx=1 (loser) does not
        rows = [_comparison_row(
            winner_idx=0,
            p0_brand="Apple", p0_name="iPhone 15",
            p1_brand="Samsung", p1_name="Galaxy S24",
            p0_image_url="https://example.com/iphone15.jpg",
            p1_image_url=None,  # explicitly null
        )]
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = rows
        self._setup_smart_pick_row(supabase, comp_resp)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        pick = resp.json()["smart_pick"]
        assert pick is not None
        assert pick["winner_image_url"] == "https://example.com/iphone15.jpg"
        assert pick["runner_up_image_url"] is None

    def test_empty_state_does_not_carry_image_url_keys(self):
        """When empty_state=True (no eligible comparisons), smart_pick is None
        and the endpoint MUST NOT fabricate image_url fields somewhere weird."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = []
        self._setup_smart_pick_row(supabase, comp_resp)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["empty_state"] is True
        assert body["smart_pick"] is None
        # Defensive — top-level body should NOT have image_url keys leaked
        assert "winner_image_url" not in body
        assert "runner_up_image_url" not in body

    def test_winner_runner_up_swap_when_winner_idx_is_1(self):
        """winner_idx=1 means products[1] is winner, products[0] is runner-up.
        winner_image_url must follow the WINNER, not the array index."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row(
            winner_idx=1,  # Samsung wins
            p0_brand="Apple", p0_name="iPhone 15",
            p1_brand="Samsung", p1_name="Galaxy S24",
            p0_image_url="https://example.com/iphone15.jpg",   # runner-up image
            p1_image_url="https://example.com/galaxy.jpg",      # winner image
        )]
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = rows
        self._setup_smart_pick_row(supabase, comp_resp)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        pick = resp.json()["smart_pick"]
        assert pick["winner_name"] == "Samsung Galaxy S24"
        assert pick["winner_image_url"] == "https://example.com/galaxy.jpg"
        assert pick["runner_up_name"] == "Apple iPhone 15"
        assert pick["runner_up_image_url"] == "https://example.com/iphone15.jpg"

    def test_invalid_image_url_types_emit_null(self):
        """If full_response.products[i].image_url is somehow non-string
        (legacy malformed row, lone int / dict / list), endpoint emits null
        rather than passing through the bad value."""
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        # Hand-craft a row with malformed image_url values
        row = _comparison_row(winner_idx=0, p0_brand="A", p0_name="X", p1_brand="B", p1_name="Y")
        row["full_response"]["products"][0]["image_url"] = 42         # int
        row["full_response"]["products"][1]["image_url"] = {"u": "x"}  # dict
        supabase = MagicMock()
        comp_resp = MagicMock(); comp_resp.data = [row]
        self._setup_smart_pick_row(supabase, comp_resp)

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        pick = resp.json()["smart_pick"]
        assert pick["winner_image_url"] is None
        assert pick["runner_up_image_url"] is None


# =============================================================================
# /api/v1/home/trending
# =============================================================================


class TestHomeTrending:

    def test_curated_list_seeds_correctly_for_bahrain(self):
        """Default region (bahrain) returns the curated list with non-empty entries.

        Bundle E B4.3a reshape per JSX-wins doctrine (HomeScreen.jsx:608-651):
        response ships {tag, a, b, count} plus legacy {query, view_count} for
        one release cycle (backwards-compat — same pattern as scoring_v2).
        """
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending?region=bahrain")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["region"] == "bahrain"
        assert len(body["trending"]) > 0
        first = body["trending"][0]
        # Bundle E JSX-wins shape — required fields
        assert "tag" in first, f"missing 'tag' (category) per JSX. keys: {list(first.keys())}"
        assert "a" in first, f"missing 'a' (product A) per JSX. keys: {list(first.keys())}"
        assert "b" in first, f"missing 'b' (product B) per JSX. keys: {list(first.keys())}"
        assert "count" in first, f"missing 'count' per JSX. keys: {list(first.keys())}"
        assert isinstance(first["tag"], str) and first["tag"]
        assert isinstance(first["a"], str) and first["a"]
        assert isinstance(first["b"], str) and first["b"]
        assert isinstance(first["count"], int)
        # Legacy backwards-compat (one release cycle)
        assert "query" in first, "legacy 'query' must survive one release cycle"
        assert "view_count" in first, "legacy 'view_count' must survive one release cycle"
        assert first["view_count"] == first["count"]
        assert first["region"] == "bahrain"

    def test_pre_split_a_and_b_match_query(self):
        """The new 'a' and 'b' fields are pre-split from the curated query.

        For a curated entry `"iPhone 15 vs Samsung Galaxy S24"`, the response
        must ship `a="iPhone 15"` + `b="Samsung Galaxy S24"`. Split is by
        " vs " (case-insensitive) so frontend never does this fragile parsing.
        """
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending?region=bahrain")
        assert resp.status_code == 200
        body = resp.json()
        for entry in body["trending"]:
            recombined = f"{entry['a']} vs {entry['b']}".lower()
            assert entry["query"].lower() == recombined, (
                f"a/b reconstruction mismatch: a={entry['a']!r} b={entry['b']!r} "
                f"query={entry['query']!r}"
            )

    def test_tag_is_a_known_category(self):
        """The 'tag' field is one of the 9 known Qaren categories.

        Matches CATEGORY_SPEC_SCHEMAS keys (electronics/skincare/supplements/
        makeup/haircare/fragrances/fashion/grocery/other), displayed
        title-cased per JSX HomeScreen.jsx:609.
        """
        known_tags = {
            "Electronics", "Skincare", "Supplements", "Makeup", "Haircare",
            "Fragrances", "Fashion", "Grocery", "Other",
        }
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending?region=bahrain")
        body = resp.json()
        for entry in body["trending"]:
            assert entry["tag"] in known_tags, (
                f"unknown tag {entry['tag']!r} for query {entry['query']!r}; "
                f"expected one of {sorted(known_tags)}"
            )

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
