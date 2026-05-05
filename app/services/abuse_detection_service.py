"""Abuse detection for the referral Loop 2 trigger.

Three lightweight controls (design Section 7):
1. Same device + email binding — invitee uses the same
   ``device_fingerprint_hash`` the referrer used at share time.
2. Disposable email blocklist — invitee's email domain is on the public
   throwaway list.
3. Real-action gate — invitee's first comparison must take >30s
   (start to result-view) AND have a non-spam query.

The service does NOT raise exceptions on Redis/DB unavailability —
``evaluate_invite`` returns ``{passed, flagged_reason}`` and callers
audit-log + skip the reward without halting the comparison. Plan B4.1.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)


# Disposable email domains. Curated short list — covers the >90% of
# fraud volume the project will see at MVP scale; replace with the
# `disposable-email-domains` PyPI package when abuse data shows we need
# the full ~5K-domain list.
_DISPOSABLE_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "tempmail.com",
        "10minutemail.com",
        "throwawaymail.com",
        "yopmail.com",
        "trashmail.com",
        "fakeinbox.com",
        "sharklasers.com",
        "getnada.com",
        "maildrop.cc",
        "dispostable.com",
        "mintemail.com",
        "spam4.me",
        "tempinbox.com",
    }
)

# Spam queries that hit the comparison endpoint as cheap test traffic.
# Real-action gate checks the invitee's first comparison query against
# this set after lowercasing + stripping.
_SPAM_QUERIES: frozenset[str] = frozenset(
    {
        "test",
        "asdf",
        "asdfg",
        "asdfgh",
        "1234",
        "12345",
        "qwerty",
        "hello",
        "hi",
        "abc",
        "abcd",
    }
)

_REAL_ACTION_MIN_SECONDS = 30


# Reason codes returned by evaluate_invite — also used by audit log entries.
REASON_SAME_DEVICE = "SAME_DEVICE"
REASON_DISPOSABLE_EMAIL = "DISPOSABLE_EMAIL"
REASON_BELOW_THRESHOLD = "BELOW_REAL_ACTION_THRESHOLD"


class AbuseDetectionService:
    """Per-invite anti-abuse evaluator. Stateless apart from the DB lookup
    used to fetch the referrer's saved device hash."""

    def __init__(self):
        # Admin client — abuse evaluation is system-side, not user-scoped.
        self.client = get_admin_supabase_client()

    # ---------- Control 1 — same device ----------

    def is_same_device(
        self, referrer_id: str, invitee_device_hash: Optional[str]
    ) -> bool:
        """True iff both sides have a hash and they match.

        Missing data on either side returns False (don't false-positive on
        web-only users who lack a device fingerprint).
        """
        if not invitee_device_hash:
            return False
        ref_hash = self._get_referrer_device_hash(referrer_id)
        if not ref_hash:
            return False
        return invitee_device_hash == ref_hash

    def _get_referrer_device_hash(self, referrer_id: str) -> Optional[str]:
        """Most-recent ``referral_invites.device_fingerprint_hash`` for the
        referrer. Returns None on any error or empty result."""
        try:
            resp = (
                self.client.table("referral_invites")
                .select("device_fingerprint_hash")
                .eq("referrer_user_id", referrer_id)
                .not_.is_("device_fingerprint_hash", "null")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                return None
            return rows[0].get("device_fingerprint_hash")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[abuse] referrer device-hash lookup failed: %s", exc)
            return None

    # ---------- Control 2 — disposable email ----------

    def is_disposable_email(self, email: str) -> bool:
        """True if email's domain is in the throwaway blocklist (case-insensitive)."""
        if not email or "@" not in email:
            return False
        domain = email.rsplit("@", 1)[-1].strip().lower()
        return domain in _DISPOSABLE_EMAIL_DOMAINS

    # ---------- Control 3 — real-action gate ----------

    def passes_real_action_gate(self, comparison_id: str) -> bool:
        """True iff the comparison ran for >30s and the query is non-spam.

        Fails closed when the comparison can't be loaded or timestamps are
        missing — we'd rather skip a marginal reward than reward a fake.
        """
        comp = self._load_comparison(comparison_id)
        if not comp:
            return False

        query = (comp.get("query") or "").strip().lower()
        if not query or query in _SPAM_QUERIES:
            return False

        started_at = comp.get("started_at")
        viewed_at = comp.get("result_viewed_at")
        if not started_at or not viewed_at:
            return False

        duration = self._duration_seconds(started_at, viewed_at)
        if duration is None:
            return False
        return duration > _REAL_ACTION_MIN_SECONDS

    def _load_comparison(self, comparison_id: str) -> Optional[dict[str, Any]]:
        """Fetch the comparison row used by the real-action gate.

        Tests patch this method directly so the implementation can evolve
        (e.g. switch to a Redis snapshot of timing data) without changing
        the contract.
        """
        try:
            resp = (
                self.client.table("comparisons")
                .select("id, query, started_at, result_viewed_at")
                .eq("id", comparison_id)
                .single()
                .execute()
            )
            return resp.data
        except Exception as exc:  # noqa: BLE001
            logger.warning("[abuse] comparison %s lookup failed: %s", comparison_id, exc)
            return None

    @staticmethod
    def _duration_seconds(start: str, end: str) -> Optional[float]:
        """Parse two ISO-8601 timestamps and return ``end - start`` in seconds.

        Returns None if either is unparseable. Trailing ``Z`` is normalised to
        ``+00:00`` so ``datetime.fromisoformat`` accepts it on Python 3.10+.
        """
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return (e - s).total_seconds()
        except (ValueError, TypeError):
            return None

    # ---------- evaluate_invite — orchestrator ----------

    def evaluate_invite(
        self, invite: dict[str, Any], invitee: dict[str, Any]
    ) -> dict[str, Any]:
        """Run all 3 controls and return ``{passed, flagged_reason}``.

        Priority order on multi-fail: SAME_DEVICE > DISPOSABLE_EMAIL >
        BELOW_REAL_ACTION_THRESHOLD. Same-device wins because it's the
        most actionable signal (one human running both sides).
        """
        referrer_id = invite.get("referrer_user_id")
        invitee_device_hash = invitee.get("device_fingerprint_hash")

        if referrer_id and self.is_same_device(referrer_id, invitee_device_hash):
            return {"passed": False, "flagged_reason": REASON_SAME_DEVICE}

        email = invitee.get("email") or ""
        if self.is_disposable_email(email):
            return {"passed": False, "flagged_reason": REASON_DISPOSABLE_EMAIL}

        comparison_id = invite.get("invitee_first_comparison_id")
        if not comparison_id or not self.passes_real_action_gate(comparison_id):
            return {"passed": False, "flagged_reason": REASON_BELOW_THRESHOLD}

        return {"passed": True, "flagged_reason": None}
