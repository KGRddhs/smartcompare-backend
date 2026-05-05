"""Backend-owned unit tests for abuse_detection_service internals.

Complements tests/test_abuse_detection.py (test-referral lane) by covering
the parsing helpers and DB-failure paths that the contract tests don't
exercise. Brings coverage on app/services/abuse_detection_service.py
above the 80% gate.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.abuse_detection_service import (
    AbuseDetectionService,
    REASON_BELOW_THRESHOLD,
)


class TestDurationSecondsParser:
    """_duration_seconds is the only timestamp parser; cover its edge cases."""

    def test_iso_with_z_suffix(self):
        result = AbuseDetectionService._duration_seconds(
            "2026-05-05T10:00:00Z", "2026-05-05T10:01:30Z"
        )
        assert result == 90.0

    def test_iso_with_offset(self):
        result = AbuseDetectionService._duration_seconds(
            "2026-05-05T10:00:00+00:00", "2026-05-05T10:00:45+00:00"
        )
        assert result == 45.0

    def test_iso_mixed_offsets(self):
        # Both UTC effectively
        result = AbuseDetectionService._duration_seconds(
            "2026-05-05T10:00:00Z", "2026-05-05T13:00:00+03:00"
        )
        # 13:00 +03:00 == 10:00 UTC, so duration is 0
        assert result == 0.0

    def test_invalid_start_returns_none(self):
        assert AbuseDetectionService._duration_seconds("not-a-date", "2026-05-05T10:00:00Z") is None

    def test_invalid_end_returns_none(self):
        assert AbuseDetectionService._duration_seconds("2026-05-05T10:00:00Z", "garbage") is None

    def test_empty_strings_return_none(self):
        # passes_real_action_gate guards None/empty upstream, but the parser
        # itself should also handle empties gracefully via the fromisoformat
        # ValueError branch.
        assert AbuseDetectionService._duration_seconds("", "") is None


class TestRealActionGateMissingTimestamps:
    """Cover the early-return branches in passes_real_action_gate."""

    def test_no_query_fails(self):
        svc = AbuseDetectionService()
        with patch.object(
            svc,
            "_load_comparison",
            return_value={
                "id": "c1",
                "query": "",
                "started_at": "2026-05-05T10:00:00Z",
                "result_viewed_at": "2026-05-05T10:01:00Z",
            },
        ):
            assert svc.passes_real_action_gate("c1") is False

    def test_no_started_at_fails(self):
        svc = AbuseDetectionService()
        with patch.object(
            svc,
            "_load_comparison",
            return_value={
                "id": "c1",
                "query": "iPhone vs Galaxy",
                "started_at": None,
                "result_viewed_at": "2026-05-05T10:01:00Z",
            },
        ):
            assert svc.passes_real_action_gate("c1") is False

    def test_no_viewed_at_fails(self):
        svc = AbuseDetectionService()
        with patch.object(
            svc,
            "_load_comparison",
            return_value={
                "id": "c1",
                "query": "iPhone vs Galaxy",
                "started_at": "2026-05-05T10:00:00Z",
                "result_viewed_at": None,
            },
        ):
            assert svc.passes_real_action_gate("c1") is False

    def test_unparseable_timestamps_fail(self):
        svc = AbuseDetectionService()
        with patch.object(
            svc,
            "_load_comparison",
            return_value={
                "id": "c1",
                "query": "iPhone vs Galaxy",
                "started_at": "garbage-date",
                "result_viewed_at": "2026-05-05T10:01:00Z",
            },
        ):
            assert svc.passes_real_action_gate("c1") is False


class TestEvaluateInviteEdges:
    """Cover the branches in evaluate_invite that the contract tests don't."""

    def test_missing_comparison_id_flags_real_action(self):
        """When invitee_first_comparison_id is None, fail closed with BELOW_REAL_ACTION_THRESHOLD."""
        svc = AbuseDetectionService()
        invite = {"referrer_user_id": "r1", "invitee_first_comparison_id": None}
        invitee = {"id": "u", "email": "real@gmail.com", "device_fingerprint_hash": "x"}
        with patch.object(svc, "is_same_device", return_value=False), patch.object(
            svc, "is_disposable_email", return_value=False
        ):
            result = svc.evaluate_invite(invite, invitee)
        assert result["passed"] is False
        assert result["flagged_reason"] == REASON_BELOW_THRESHOLD


class TestDBLookupFailures:
    """Cover the exception branches in the Supabase lookup helpers."""

    def test_referrer_device_hash_db_error_returns_none(self):
        svc = AbuseDetectionService()
        # Patch the chained Supabase builder to raise on .execute()
        broken = MagicMock()
        broken.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.side_effect = RuntimeError(
            "supabase down"
        )
        svc.client = broken
        assert svc._get_referrer_device_hash("r1") is None

    def test_referrer_device_hash_no_rows_returns_none(self):
        svc = AbuseDetectionService()
        empty = MagicMock()
        empty.data = []
        svc.client = MagicMock()
        svc.client.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value = (
            empty
        )
        assert svc._get_referrer_device_hash("r1") is None

    def test_load_comparison_db_error_returns_none(self):
        svc = AbuseDetectionService()
        broken = MagicMock()
        broken.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = RuntimeError(
            "supabase down"
        )
        svc.client = broken
        assert svc._load_comparison("c1") is None
