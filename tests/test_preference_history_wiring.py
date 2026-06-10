"""F3.4 — user_preference_history write wiring.

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md (Lane F3.4)
Preflight: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.2 / § 7
Migration: migrations/029_user_preference_history.sql

Two surfaces under test:

1. `database_service.record_preference_history(user_id, preferences, change_source)`
   — the service-role INSERT helper (029 RLS posture: service-role-only writes).
   Validates `change_source` against the 5-value enum BEFORE the DB round-trip,
   fail-soft on any error (returns bool, never raises into the caller).

2. `auth_service.save_user_preferences(user_id, preferences, change_source=...)`
   — must fire-and-forget a history snapshot AFTER a successful preferences
   UPDATE, and must NOT fire one when the UPDATE itself fails.

These are unit tests with mocked Supabase clients — no live DB. The live
INSERT path is exercised post-029-apply via the migration 029 live_db class.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.database_service import (
    VALID_PREFERENCE_CHANGE_SOURCES,
    record_preference_history,
)


# ---------------------------------------------------------------------------
# record_preference_history — the DB-write helper
# ---------------------------------------------------------------------------

def test_valid_change_sources_match_migration_029_enum():
    """The Python-side allowlist MUST equal the 029 CHECK enum exactly —
    a drift would let a write through that the DB then rejects (or vice versa)."""
    assert VALID_PREFERENCE_CHANGE_SOURCES == {
        "manual_edit",
        "cohort_default",
        "onboarding_initial",
        "import_from_demographics",
        "system_correction",
    }


@pytest.mark.asyncio
async def test_record_preference_history_inserts_expected_shape():
    prefs = {"priorities": ["price", "battery"], "budget": "mid"}
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "h1"}])
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        ok = await record_preference_history("u1", prefs, "manual_edit")

    assert ok is True
    mock_client.table.assert_called_once_with("user_preference_history")
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["user_id"] == "u1"
    assert insert_arg["preferences"] == prefs
    assert insert_arg["change_source"] == "manual_edit"
    # created_at is DB-defaulted; helper must NOT send a client clock value
    # (avoids clock-skew rows). So the insert payload should omit created_at.
    assert "created_at" not in insert_arg


@pytest.mark.asyncio
async def test_record_preference_history_rejects_unknown_change_source():
    """An out-of-enum change_source must be rejected BEFORE any DB call so we
    don't burn a round-trip on a guaranteed CHECK rejection."""
    mock_client = MagicMock()
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        ok = await record_preference_history("u1", {"a": 1}, "totally_made_up")

    assert ok is False
    mock_client.table.assert_not_called()


@pytest.mark.asyncio
async def test_record_preference_history_uses_service_role_client():
    """029 is service-role-only write (no anon/authenticated INSERT policy).
    The helper must use the admin (service-role) client, never the user client."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "h1"}])
    mock_admin = MagicMock()
    mock_admin.table.return_value = mock_table

    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_admin,
    ) as admin_spy:
        await record_preference_history("u1", {"a": 1}, "cohort_default")

    admin_spy.assert_called_once()


@pytest.mark.asyncio
async def test_record_preference_history_swallows_db_exception(caplog):
    """A DB blip must NOT raise into the fire-and-forget caller — return False,
    log, move on (the preferences UPDATE itself already succeeded)."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.side_effect = RuntimeError("db blip")
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        ok = await record_preference_history("u1", {"a": 1}, "manual_edit")

    assert ok is False
    assert any(
        "preference" in r.message.lower() or "history" in r.message.lower()
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_record_preference_history_handles_none_preferences():
    """A None/empty preferences snapshot is still recorded as '{}' — the column
    is NOT NULL in 029, so the helper must coerce None to an empty dict rather
    than send NULL (which the DB would reject)."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "h1"}])
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        ok = await record_preference_history("u1", None, "system_correction")

    assert ok is True
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["preferences"] == {}


# ---------------------------------------------------------------------------
# save_user_preferences — fire-and-forget integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_user_preferences_fires_history_on_success():
    """After a successful UPDATE, save_user_preferences must fire-and-forget a
    history snapshot carrying the supplied change_source."""
    from app.services import auth_service

    mock_admin = MagicMock()
    # .table("users").update(...).eq(...).execute() chain
    mock_admin.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[{"id": "u1"}])
    )

    prefs = {"priorities": ["price"], "budget": "budget"}

    with patch.object(auth_service, "get_admin_client", return_value=mock_admin), patch(
        "app.services.auth_service.record_preference_history"
    ) as rec, patch("app.services.auth_service.fire_and_forget") as faf:
        result = await auth_service.save_user_preferences(
            "u1", prefs, change_source="manual_edit"
        )

    assert result["success"] is True
    # fire_and_forget must have been called once wrapping the history coro.
    faf.assert_called_once()
    # The coroutine passed to fire_and_forget must be record_preference_history(...)
    rec.assert_called_once_with("u1", prefs, "manual_edit")


@pytest.mark.asyncio
async def test_save_user_preferences_defaults_change_source_to_manual_edit():
    """Back-compat: existing callers that don't pass change_source get
    'manual_edit' (the PUT /preferences UI path is the default caller)."""
    from app.services import auth_service

    mock_admin = MagicMock()
    mock_admin.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[{"id": "u1"}])
    )

    with patch.object(auth_service, "get_admin_client", return_value=mock_admin), patch(
        "app.services.auth_service.record_preference_history"
    ) as rec, patch("app.services.auth_service.fire_and_forget"):
        await auth_service.save_user_preferences("u1", {"x": 1})

    rec.assert_called_once_with("u1", {"x": 1}, "manual_edit")


@pytest.mark.asyncio
async def test_save_user_preferences_does_not_fire_history_on_update_failure():
    """When the UPDATE raises, no history snapshot should be recorded — we must
    not log a preference change that did not persist."""
    from app.services import auth_service

    mock_admin = MagicMock()
    mock_admin.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        RuntimeError("update failed")
    )

    with patch.object(auth_service, "get_admin_client", return_value=mock_admin), patch(
        "app.services.auth_service.fire_and_forget"
    ) as faf:
        result = await auth_service.save_user_preferences("u1", {"x": 1})

    assert result["success"] is False
    faf.assert_not_called()
