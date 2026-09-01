"""Bundle E — endpoint-shape contract tests vs JSX-consumer expectations.

Purpose
-------
The B4.3a/b shape audit (commits `dca8067` + `3bb31bd`) caught two endpoint-vs-
JSX mismatches manually — but only because they were searched for. Future
JSX changes can silently drift past the backend until a frontend lane wires
the screen and notices a missing field. This test pins each editorial
endpoint to a declarative manifest of fields the JSX consumer renders.

The manifest is the SPEC. Source of truth: `docs/claude-design-handoff/
ui_kits/mobile/*.jsx`. When a JSX file changes, update the matching manifest
entry first — the failing tests then drive the backend update under the
canonical TDD-cycle pattern (303bdf8).

Coverage
--------
Six endpoints:
  GET /api/v1/home/savings            ← HomeScreen.jsx SavingsBanner
  GET /api/v1/home/smart-pick         ← HomeScreen.jsx SmartPickCard
  GET /api/v1/home/trending           ← HomeScreen.jsx TrendingNearYou
  GET /api/v1/profile/recent-decisions ← ProfileScreen.jsx RecentDecisions
                                         + HistoryScreen.jsx HeroStats marquee
  GET /api/v1/profile/monthly-stats   ← ProfileScreen.jsx MonthStrip
  GET /api/v1/profile/priorities-weighted ← ProfileScreen.jsx PrioritiesInline

Each test:
1. Mocks the underlying Supabase + Redis stack so we hit a deterministic
   "happy-path" response shape (the same fixture pattern as
   test_home_routes.py / test_profile_routes.py).
2. Asserts every field in the per-endpoint MANIFEST is present in the
   top-level response (or in the first item if the manifest is keyed
   `*.item`).
3. Flags any newly-added endpoint that lacks a manifest entry (forces
   maintenance discipline — see test_all_editorial_endpoints_have_manifest).

The manifest deliberately stays minimal — it pins ONLY the fields the JSX
*renders*, not internal/optional fields. Adding a field to the backend
response without a matching JSX consumer is fine and won't fail this suite.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._route_introspection import (
    assert_route_table_visible,
    route_method_paths,
)


client = TestClient(app)


# =============================================================================
# Per-endpoint MANIFEST — pinned to JSX-consumer field references.
# When a JSX changes, update the matching entry here FIRST, then drive the
# backend update via TDD-cycle.
#
# Manifest schema:
#   "top_level": [field, ...]            ← required keys on the response body
#   "item":      [field, ...]            ← required keys on each list item
#                                          (skipped if the relevant collection
#                                          is empty in the happy-path fixture)
#   "item_path": "<dot.path.to.list>"    ← where to find the list to drill into
# =============================================================================

ENDPOINT_MANIFEST: dict[str, dict] = {
    # ---------------- /home ----------------
    # Source: HomeScreen.jsx SavingsBanner (line 573-605).
    # Renders: "~240 BHD shopped smarter" + "Across 8 decisions"
    # FE reads: savings_bhd, decisions_count. threshold_met gates render.
    "GET /api/v1/home/savings": {
        "top_level": ["savings_bhd", "decisions_count", "threshold_met"],
        "item_path": None,
        "item": [],
    },

    # Source: HomeScreen.jsx SmartPickCard (line 438-501) + B4.3b extension.
    # Renders: category eyebrow + "Updated today" chip + winner/runner_up
    # PickTile w/ name+sub+price + verdict sentence. JSX-wins: category,
    # updated_at, *_sub, verdict_short are *required* fields (null-when-absent
    # — frontend hides surround, but the KEY must be present).
    "GET /api/v1/home/smart-pick": {
        "top_level": ["smart_pick", "empty_state"],
        "item_path": "smart_pick",
        "item": [
            # Legacy 6 (one-release-cycle compat)
            "comparison_id",
            "winner_name", "runner_up_name",
            "winner_price_bhd", "runner_up_price_bhd",
            "reason_key", "reason_params",
            # Bundle E B4.3b JSX-wins extension fields
            "category", "updated_at",
            "winner_sub", "runner_up_sub",
            "verdict_short",
        ],
    },

    # Source: HomeScreen.jsx TrendingNearYou (line 608-651) + B4.3a reshape.
    # JSX renders per row: [category pill] productA vs productB [count ↗].
    "GET /api/v1/home/trending": {
        "top_level": ["trending", "region"],
        "item_path": "trending",
        "item": [
            # Bundle E B4.3a JSX-wins fields
            "tag", "a", "b", "count",
            # Legacy compat (one release cycle)
            "query", "view_count", "region",
        ],
    },

    # ---------------- /profile ----------------
    # Source: ProfileScreen.jsx RecentDecisions (line 122-161) +
    #         HistoryScreen.jsx HeroStats marquee MarqueeCard (line 111-152).
    # JSX renders: tone/winner-per-side/ago are FE-derived from
    # winner_name/runner_up_name/created_at — only the three base fields
    # are spec-pinned here.
    "GET /api/v1/profile/recent-decisions": {
        "top_level": ["recent", "empty_state"],
        "item_path": "recent",
        "item": ["comparison_id", "winner_name", "runner_up_name", "created_at"],
    },

    # Source: ProfileScreen.jsx MonthStrip (line 202-221).
    # Renders three Stat tiles: "27 decisions this month / 240 BHD shopped
    # smarter / +5 Bonus credits". FE reads decisions_count/savings_bhd/
    # bonus_credits_this_month, gates via threshold_met.
    "GET /api/v1/profile/monthly-stats": {
        "top_level": [
            "month",
            "decisions_count",
            "savings_bhd",
            "bonus_credits_this_month",
            "threshold_met",
        ],
        "item_path": None,
        "item": [],
    },

    # Source: ProfileScreen.jsx PrioritiesInline (line 163-200).
    # Renders bars: 0-1 float weights, label per priority.
    # Backend ships 0-100 ints + label_key (i18n) — FE adapts via Math.round.
    "GET /api/v1/profile/priorities-weighted": {
        "top_level": ["priorities", "empty_state"],
        "item_path": "priorities",
        "item": ["key", "label_key", "weight"],
    },
}


# =============================================================================
# Shared fixtures — minimal happy-path Supabase + Redis stubs.
# =============================================================================


def _fake_user(user_id: str = "shape-test-user"):
    async def _override():
        return {"id": user_id, "email": "shape@qaren.app", "access_token": "fake-token"}
    return _override


def _patched_redis():
    """Bypass Redis entirely — _redis_get returns None so the endpoint
    always recomputes; _redis_set is a no-op."""
    return (
        patch("app.api.home_routes._redis_get", return_value=None),
        patch("app.api.home_routes._redis_set", return_value=True),
        patch("app.api.profile_routes._redis_get", return_value=None),
        patch("app.api.profile_routes._redis_set", return_value=True),
    )


def _comparison_row_full() -> dict:
    """A maximally-populated v2 comparison row that exercises every
    extension-field path in the smart-pick + recent-decisions endpoints.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": "shape-comp-1",
        "created_at": now_iso,
        "full_response": {
            "winner_index": 0,
            "category": "electronics",
            "products": [
                {
                    "brand": "Apple", "name": "iPhone 15",
                    "price": {"amount": 329.0, "currency": "BHD"},
                },
                {
                    "brand": "Samsung", "name": "Galaxy S24",
                    "price": {"amount": 299.0, "currency": "BHD"},
                },
            ],
            "scoring": {"dimension_winners": {"camera_quality_score": "Apple iPhone 15"}},
            "overview": {
                "winner": {
                    "declaration": (
                        "iPhone 15 takes this round on photo quality and "
                        "chip performance, edging the Galaxy S24 by ~30 BHD."
                    ),
                },
            },
            "specs": {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15",
                     "specs": {"storage": "128GB"}},
                    {"brand": "Samsung", "name": "Galaxy S24",
                     "specs": {"storage": "256GB"}},
                ],
            },
        },
    }


def _patch_supabase_for_home(rows: list[dict], prefs: dict):
    """Wire home_routes Supabase reads — users prefs + comparisons table."""
    user_resp = MagicMock(); user_resp.data = {"preferences": prefs}
    comp_resp = MagicMock(); comp_resp.data = rows

    def _table_dispatch(name):
        m = MagicMock()
        if name == "users":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        else:
            # savings: select → eq → eq → execute
            m.select.return_value.eq.return_value.eq.return_value.execute.return_value = comp_resp
            # smart-pick: select → eq → eq → order → limit → execute
            m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
        return m
    supabase = MagicMock()
    supabase.table.side_effect = _table_dispatch
    return supabase


def _patch_supabase_for_profile(
    rows: list[dict],
    prefs: dict,
    behavior_profile: dict,
    rr_rows: list[dict] | None = None,
):
    """Wire profile_routes Supabase reads — users (prefs+behavior_profile),
    comparisons (recent / month-bounded), referral_redemptions."""
    user_resp = MagicMock()
    user_resp.data = {"preferences": prefs, "behavior_profile": behavior_profile}
    comp_resp = MagicMock(); comp_resp.data = rows
    rr_resp = MagicMock(); rr_resp.data = rr_rows or []

    def _table_dispatch(name):
        m = MagicMock()
        if name == "users":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        elif name == "referral_redemptions":
            m.select.return_value.eq.return_value.gte.return_value.execute.return_value = rr_resp
        else:
            # recent-decisions: select → eq → eq → order → limit → execute
            m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
            # monthly-stats: select → eq → eq → gte → execute
            m.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = comp_resp
        return m
    supabase = MagicMock()
    supabase.table.side_effect = _table_dispatch
    return supabase


@pytest.fixture(autouse=True)
def _flush_overrides():
    yield
    app.dependency_overrides.clear()


# =============================================================================
# Shape contract tests — one per endpoint, plus a maintenance guard.
# =============================================================================


def _assert_shape_against_manifest(body: dict, manifest: dict, endpoint: str) -> None:
    """Walk the manifest and assert every required field is present in body."""
    for field in manifest["top_level"]:
        assert field in body, (
            f"{endpoint} response missing top-level field {field!r}. "
            f"Body keys: {sorted(body.keys())}. "
            f"This means JSX consumes the field but the endpoint doesn't provide it. "
            f"Fix: extend the endpoint, OR update ENDPOINT_MANIFEST if the JSX no "
            f"longer reads it."
        )
    item_path = manifest.get("item_path")
    item_fields = manifest.get("item") or []
    if not item_path or not item_fields:
        return
    # Walk dot-path to find the list/object
    target = body
    for segment in item_path.split("."):
        if not isinstance(target, dict):
            return
        target = target.get(segment)
        if target is None:
            return
    items = target if isinstance(target, list) else [target]
    if not items:
        return  # empty fixture path — skip item assertions
    for i, item in enumerate(items[:1]):  # first item only — shape is uniform
        if not isinstance(item, dict):
            continue
        for field in item_fields:
            assert field in item, (
                f"{endpoint} response item[{i}] (path={item_path}) missing field "
                f"{field!r}. Item keys: {sorted(item.keys())}. "
                f"JSX consumes this field — extend the endpoint OR update the manifest."
            )


class TestHomeShapesVsJSX:

    def test_savings_shape_matches_manifest(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row_full() for _ in range(3)]  # threshold-met
        supabase = _patch_supabase_for_home(rows, {})

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        _assert_shape_against_manifest(
            resp.json(),
            ENDPOINT_MANIFEST["GET /api/v1/home/savings"],
            "GET /api/v1/home/savings",
        )

    def test_smart_pick_shape_matches_manifest(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row_full()]
        supabase = _patch_supabase_for_home(rows, {"priorities": ["price"]})

        with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # smart_pick can be None (empty_state); the manifest test only fires
        # when the happy path has a populated pick.
        assert body["smart_pick"] is not None, (
            "shape test fixture should produce a populated smart_pick; "
            "if you got empty_state=True, the fixture data shape regressed."
        )
        _assert_shape_against_manifest(
            body,
            ENDPOINT_MANIFEST["GET /api/v1/home/smart-pick"],
            "GET /api/v1/home/smart-pick",
        )

    def test_trending_shape_matches_manifest(self):
        # trending is auth-optional — no dependency override needed.
        with patch("app.api.home_routes._redis_get", return_value=None), \
             patch("app.api.home_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/home/trending?region=bahrain")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["trending"]) > 0, (
            "shape test requires curated bahrain entries — if empty, the "
            "trending_curated.json regressed."
        )
        _assert_shape_against_manifest(
            body,
            ENDPOINT_MANIFEST["GET /api/v1/home/trending"],
            "GET /api/v1/home/trending",
        )


class TestProfileShapesVsJSX:

    def test_recent_decisions_shape_matches_manifest(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row_full()]
        supabase = _patch_supabase_for_profile(rows, prefs={}, behavior_profile={})

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["recent"]) > 0, "shape test fixture should produce ≥1 recent entry"
        _assert_shape_against_manifest(
            body,
            ENDPOINT_MANIFEST["GET /api/v1/profile/recent-decisions"],
            "GET /api/v1/profile/recent-decisions",
        )

    def test_monthly_stats_shape_matches_manifest(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        rows = [_comparison_row_full() for _ in range(3)]
        supabase = _patch_supabase_for_profile(
            rows, prefs={}, behavior_profile={},
            rr_rows=[{"loop2_comparisons_granted": 5, "created_at": "2026-05-15T10:00:00Z"}],
        )

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/monthly-stats", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        _assert_shape_against_manifest(
            resp.json(),
            ENDPOINT_MANIFEST["GET /api/v1/profile/monthly-stats"],
            "GET /api/v1/profile/monthly-stats",
        )

    def test_priorities_weighted_shape_matches_manifest(self):
        from app.api.auth_routes import get_current_user
        app.dependency_overrides[get_current_user] = _fake_user()

        supabase = _patch_supabase_for_profile(
            rows=[],
            prefs={"priorities": ["quality", "price", "durable"]},
            behavior_profile={
                "dimension_sensitivity": {"quality": 0.9, "price": 0.6, "durable": 0.5},
            },
        )

        with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
             patch("app.api.profile_routes._redis_get", return_value=None), \
             patch("app.api.profile_routes._redis_set", return_value=True):
            resp = client.get("/api/v1/profile/priorities-weighted", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["priorities"]) > 0, "shape test fixture should produce ≥1 priority"
        _assert_shape_against_manifest(
            body,
            ENDPOINT_MANIFEST["GET /api/v1/profile/priorities-weighted"],
            "GET /api/v1/profile/priorities-weighted",
        )


class TestManifestMaintenance:

    def test_every_editorial_endpoint_has_a_manifest(self):
        """Maintenance guard — surface newly-added editorial endpoints
        that bypass this contract test by accident.

        Walks the FastAPI route table and asserts every GET route under
        /api/v1/home or /api/v1/profile has a matching ENDPOINT_MANIFEST
        entry. New endpoints must add a manifest entry — even if the body
        is empty, it forces the author to think about which JSX consumes it.
        """
        # POSITIVE CONTROL FIRST — this is a negative assertion and would pass
        # vacuously against an empty route table. On the pinned fastapi 0.141 a
        # bare `for route in app.routes` sees `_IncludedRouter` wrappers with no
        # `.path`, so the getattr-defended loop that used to live here found
        # ZERO editorial routes and this guard silently stopped guarding.
        # See tests/_route_introspection.py.
        editorial_routes: list[str] = []
        for entry in assert_route_table_visible(app):
            if "GET" not in entry.methods:
                continue
            if entry.path.startswith("/api/v1/home/") or entry.path.startswith(
                "/api/v1/profile/"
            ):
                editorial_routes.append(f"GET {entry.path}")

        assert editorial_routes, (
            "No /home or /profile GET routes were visible at all — route "
            "introspection is blind, not the manifest. See "
            "tests/_route_introspection.py."
        )
        missing = [r for r in editorial_routes if r not in ENDPOINT_MANIFEST]
        assert not missing, (
            f"Editorial endpoint(s) added without a manifest entry: {missing}. "
            f"Add an entry to ENDPOINT_MANIFEST in this file pinned to the "
            f"JSX consumer fields, OR explicitly add to the manifest with empty "
            f"lists if the endpoint has no JSX consumer."
        )

    def test_manifest_does_not_reference_phantom_endpoints(self):
        """The reverse guard — every ENDPOINT_MANIFEST key must match an
        actual mounted route. Catches stale manifest entries after an
        endpoint is removed."""
        # This one fails LOUDLY on a blind walk (every manifest key looks
        # phantom) — that was CI failure #2 of the M19 trio, reporting
        # "Current /home + /profile GET routes: []" for six mounted endpoints.
        # The positive control keeps the diagnosis in the message.
        assert_route_table_visible(app)
        registered_routes = route_method_paths(app)

        phantom = [k for k in ENDPOINT_MANIFEST if k not in registered_routes]
        assert not phantom, (
            f"ENDPOINT_MANIFEST keys that don't match a mounted route: {phantom}. "
            f"Remove the stale entry, OR fix the path. Current /home + /profile "
            f"GET routes: "
            f"{sorted(r for r in registered_routes if '/home/' in r or '/profile/' in r)}"
        )
