"""Backend-owned internals tests for referral_service.

Closes the collision-retry path qa-referral flagged in their first
review pass (`ensure_code_for_user` lines 157-167). The contract tests
in `tests/test_referral_service.py` cover the happy path and the
"existing code → return existing" path; this file covers the retry
loop's three branches: one collision-then-success, repeated collisions
exhausting all 5 retries, and a non-collision exception (re-raise).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _build_client_with_no_existing_code() -> MagicMock:
    """Common fixture: select returns referral_code=None for the user."""
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"referral_code": None}
    )
    return client


class TestEnsureCodeCollisionRetry:
    """Cover lines 157-167 of referral_service.py — the unique-violation
    retry loop after generate_referral_code() emits a colliding value."""

    @pytest.mark.asyncio
    async def test_one_collision_then_success(self):
        """First update raises duplicate-key; second update succeeds."""
        from app.services.referral_service import ReferralService

        client = _build_client_with_no_existing_code()
        # First update raises a DuplicateKeyError-like exception, then
        # subsequent calls succeed silently.
        update_mock = MagicMock()
        call_count = {"n": 0}

        def execute_side_effect():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("duplicate key value violates unique constraint")
            return MagicMock(data=[{}])

        update_mock.execute.side_effect = execute_side_effect
        client.table.return_value.update.return_value.eq.return_value = update_mock

        with patch(
            "app.services.referral_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReferralService()
            code = await svc.ensure_code_for_user("u-collide-once")

        assert code.startswith("QR-")
        assert call_count["n"] == 2, "expected exactly 1 retry (2 total attempts)"

    @pytest.mark.asyncio
    async def test_repeated_collisions_exhaust_5_retries(self):
        """All 5 attempts collide → service raises RuntimeError."""
        from app.services.referral_service import ReferralService

        client = _build_client_with_no_existing_code()
        update_mock = MagicMock()
        update_mock.execute.side_effect = Exception(
            "duplicate key value violates unique constraint \"users_referral_code_key\""
        )
        client.table.return_value.update.return_value.eq.return_value = update_mock

        with patch(
            "app.services.referral_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReferralService()
            with pytest.raises(RuntimeError, match="5 attempts"):
                await svc.ensure_code_for_user("u-always-collide")

        # exactly 5 attempts before raising
        assert update_mock.execute.call_count == 5

    @pytest.mark.asyncio
    async def test_non_collision_exception_re_raises_immediately(self):
        """A non-unique-violation error must propagate, not retry."""
        from app.services.referral_service import ReferralService

        client = _build_client_with_no_existing_code()
        update_mock = MagicMock()
        # An error that is NOT a duplicate-key collision (e.g. RLS denial)
        update_mock.execute.side_effect = Exception(
            "permission denied for table users"
        )
        client.table.return_value.update.return_value.eq.return_value = update_mock

        with patch(
            "app.services.referral_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReferralService()
            with pytest.raises(Exception, match="permission denied"):
                await svc.ensure_code_for_user("u-rls-blocked")

        # Failed on first attempt, no retry
        assert update_mock.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_collision_message_case_insensitive(self):
        """Retry triggers on either 'duplicate key' OR 'unique' in any case."""
        from app.services.referral_service import ReferralService

        client = _build_client_with_no_existing_code()
        update_mock = MagicMock()
        call_count = {"n": 0}

        def execute_side_effect():
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Capitalised, includes 'UNIQUE' but not 'duplicate key'
                raise Exception("UNIQUE constraint failed: users.referral_code")
            return MagicMock(data=[{}])

        update_mock.execute.side_effect = execute_side_effect
        client.table.return_value.update.return_value.eq.return_value = update_mock

        with patch(
            "app.services.referral_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReferralService()
            code = await svc.ensure_code_for_user("u-unique-only")

        assert code.startswith("QR-")
        assert call_count["n"] == 2
