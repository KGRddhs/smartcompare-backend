"""Tests for app/services/abuse_detection_service.py.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
section 7 + plan task B4.1.

Three controls:
1. Same device + email binding — invitee with same device_fingerprint_hash as
   referrer => SAME_DEVICE
2. Disposable email blocklist — domain matches public list (e.g. mailinator.com)
   => DISPOSABLE_EMAIL
3. Real-action gate — invitee's first comparison must have
   (result_viewed_at - started_at) > 30s and a non-spam query =>
   BELOW_REAL_ACTION_THRESHOLD if it doesn't

Written FIRST (red phase). Backend implements
app/services/abuse_detection_service.py to make these green.

Coverage gate: ≥80% on the new file.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# B4.1 — AbuseDetectionService class API
# ============================================


class TestAbuseDetectionServiceShape:
    """The class must expose the methods the plan specifies."""

    def test_class_is_importable(self):
        from app.services.abuse_detection_service import AbuseDetectionService  # noqa: F401

    def test_has_required_methods(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        for method in ("is_same_device", "is_disposable_email", "passes_real_action_gate", "evaluate_invite"):
            assert hasattr(svc, method), f"AbuseDetectionService missing method: {method}"


# ============================================
# Control 1 — Same-device detection
# ============================================


class TestSameDeviceDetection:
    """Referrer + invitee using same device_fingerprint_hash => flagged."""

    def test_same_hash_returns_true(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        with patch.object(svc, "_get_referrer_device_hash", return_value="abc123"):
            assert svc.is_same_device(referrer_id="r1", invitee_device_hash="abc123") is True

    def test_different_hash_returns_false(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        with patch.object(svc, "_get_referrer_device_hash", return_value="abc123"):
            assert svc.is_same_device(referrer_id="r1", invitee_device_hash="def456") is False

    def test_missing_invitee_hash_returns_false(self):
        """If invitee didn't fingerprint (e.g., web), don't flag."""
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        with patch.object(svc, "_get_referrer_device_hash", return_value="abc123"):
            assert svc.is_same_device(referrer_id="r1", invitee_device_hash=None) is False

    def test_missing_referrer_hash_returns_false(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        with patch.object(svc, "_get_referrer_device_hash", return_value=None):
            assert svc.is_same_device(referrer_id="r1", invitee_device_hash="abc123") is False


# ============================================
# Control 2 — Disposable email blocklist
# ============================================


class TestDisposableEmailDetection:
    """Email domain in blocklist => flagged."""

    @pytest.mark.parametrize(
        "email",
        [
            "test@mailinator.com",
            "abuse@guerrillamail.com",
            "throwaway@tempmail.com",
            "junk@10minutemail.com",
        ],
    )
    def test_known_disposable_domains_flagged(self, email):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        assert svc.is_disposable_email(email) is True, f"{email!r} should be flagged disposable"

    @pytest.mark.parametrize(
        "email",
        [
            "user@gmail.com",
            "ahmed@hotmail.com",
            "sarah@yahoo.com",
            "person@outlook.com",
            "real@protonmail.com",
            "ahmeddeniro2100@gmail.com",
        ],
    )
    def test_legitimate_domains_pass(self, email):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        assert svc.is_disposable_email(email) is False, f"{email!r} should NOT be flagged"

    def test_case_insensitive(self):
        """Email domain match must be case-insensitive."""
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        assert svc.is_disposable_email("test@MAILINATOR.COM") is True
        assert svc.is_disposable_email("Test@MailInator.Com") is True

    def test_invalid_email_returns_false(self):
        """Malformed email shouldn't crash; treat as not-disposable (separate validation problem)."""
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        assert svc.is_disposable_email("not-an-email") is False
        assert svc.is_disposable_email("") is False


# ============================================
# Control 3 — Real-action gate
# ============================================


class TestRealActionGate:
    """Comparison duration < 30s OR spam query => fails gate."""

    def test_below_30s_fails(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        comparison = {
            "id": "c1",
            "query": "iPhone 15 vs Galaxy S24",
            "started_at": "2026-05-05T10:00:00Z",
            "result_viewed_at": "2026-05-05T10:00:15Z",  # 15 seconds
        }
        with patch.object(svc, "_load_comparison", return_value=comparison):
            assert svc.passes_real_action_gate("c1") is False

    def test_above_30s_passes(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        comparison = {
            "id": "c1",
            "query": "iPhone 15 vs Galaxy S24",
            "started_at": "2026-05-05T10:00:00Z",
            "result_viewed_at": "2026-05-05T10:01:00Z",  # 60 seconds
        }
        with patch.object(svc, "_load_comparison", return_value=comparison):
            assert svc.passes_real_action_gate("c1") is True

    @pytest.mark.parametrize("spam_query", ["test", "asdf", "asdfg", "1234", "qwerty"])
    def test_spam_queries_fail(self, spam_query):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        comparison = {
            "id": "c1",
            "query": spam_query,
            "started_at": "2026-05-05T10:00:00Z",
            "result_viewed_at": "2026-05-05T10:01:00Z",  # 60s, but spam query
        }
        with patch.object(svc, "_load_comparison", return_value=comparison):
            assert svc.passes_real_action_gate("c1") is False

    def test_missing_comparison_fails(self):
        """If comparison can't be loaded, fail closed (don't reward)."""
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        with patch.object(svc, "_load_comparison", return_value=None):
            assert svc.passes_real_action_gate("c-missing") is False


# ============================================
# evaluate_invite — orchestrator
# ============================================


class TestEvaluateInvite:
    """All 3 controls combined into a single decision."""

    def test_all_pass_returns_passed_true(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        invite = {
            "referrer_user_id": "r1",
            "device_fingerprint_hash": "ref-device",
            "invitee_first_comparison_id": "c1",
        }
        invitee = {"id": "u-invitee", "email": "real@gmail.com", "device_fingerprint_hash": "different-device"}

        with patch.object(svc, "is_same_device", return_value=False), \
             patch.object(svc, "is_disposable_email", return_value=False), \
             patch.object(svc, "passes_real_action_gate", return_value=True):
            result = svc.evaluate_invite(invite, invitee)

        assert result["passed"] is True
        assert result["flagged_reason"] is None

    def test_same_device_short_circuits(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        invite = {"referrer_user_id": "r1", "invitee_first_comparison_id": "c1"}
        invitee = {"id": "u-invitee", "email": "real@gmail.com", "device_fingerprint_hash": "ref-device"}

        with patch.object(svc, "is_same_device", return_value=True), \
             patch.object(svc, "is_disposable_email", return_value=False), \
             patch.object(svc, "passes_real_action_gate", return_value=True):
            result = svc.evaluate_invite(invite, invitee)

        assert result["passed"] is False
        assert result["flagged_reason"] == "SAME_DEVICE"

    def test_disposable_email_flagged(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        invite = {"referrer_user_id": "r1", "invitee_first_comparison_id": "c1"}
        invitee = {"id": "u-invitee", "email": "abuse@mailinator.com", "device_fingerprint_hash": "x"}

        with patch.object(svc, "is_same_device", return_value=False), \
             patch.object(svc, "is_disposable_email", return_value=True), \
             patch.object(svc, "passes_real_action_gate", return_value=True):
            result = svc.evaluate_invite(invite, invitee)

        assert result["passed"] is False
        assert result["flagged_reason"] == "DISPOSABLE_EMAIL"

    def test_below_real_action_threshold_flagged(self):
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        invite = {"referrer_user_id": "r1", "invitee_first_comparison_id": "c1"}
        invitee = {"id": "u-invitee", "email": "real@gmail.com", "device_fingerprint_hash": "x"}

        with patch.object(svc, "is_same_device", return_value=False), \
             patch.object(svc, "is_disposable_email", return_value=False), \
             patch.object(svc, "passes_real_action_gate", return_value=False):
            result = svc.evaluate_invite(invite, invitee)

        assert result["passed"] is False
        assert result["flagged_reason"] == "BELOW_REAL_ACTION_THRESHOLD"

    def test_priority_order_same_device_first(self):
        """When multiple checks fail, SAME_DEVICE wins (most actionable signal)."""
        from app.services.abuse_detection_service import AbuseDetectionService

        svc = AbuseDetectionService()
        invite = {"referrer_user_id": "r1", "invitee_first_comparison_id": "c1"}
        invitee = {"id": "u", "email": "abuse@mailinator.com", "device_fingerprint_hash": "x"}

        with patch.object(svc, "is_same_device", return_value=True), \
             patch.object(svc, "is_disposable_email", return_value=True), \
             patch.object(svc, "passes_real_action_gate", return_value=False):
            result = svc.evaluate_invite(invite, invitee)

        assert result["passed"] is False
        # Document the priority: SAME_DEVICE first
        assert result["flagged_reason"] == "SAME_DEVICE"
