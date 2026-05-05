"""Referral system service.

Owns the referral lifecycle: code provisioning, share/invite creation,
weekly cap enforcement, Loop 1 (Deep Review credit) trigger, status
reporting, and Loop 2 (deferred reward on first invitee comparison).

Design: docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
Plan tasks: B1.2, B2.1, B2.2, B3.1, B3.4, B4.2, B4.4.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote

from app.services.abuse_detection_service import AbuseDetectionService
from app.services.audit_service import log_audit_event
from app.services.database_service import (
    get_admin_supabase_client,
    get_user_supabase_client,
)

logger = logging.getLogger(__name__)

# 32-char alphabet, ambiguous chars (0/O/1/I/L) excluded — design Section 4.1.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

_VALID_SHARE_TARGETS = {"whatsapp", "copy", "x", "telegram", "snapchat", "other"}

_WEEKLY_INVITE_CAP = 3

# Default app base URL for invitee landing links. Override at deploy via env.
# Kept as module attribute so tests/runtime can monkeypatch if needed.
APP_BASE_URL = "https://qaren.app"


class WeeklyInviteCapExceeded(Exception):
    """Raised when a user attempts a 4th invite within 7 days."""


# Top-level keys we strip from a comparison before showing it to an invitee.
# Privacy invariant from design 3.3 — invitee must never see referrer's
# preferences or budget. Behavior_profile is internal scoring state.
_REFERRER_PRIVATE_KEYS = (
    "preferences",
    "budget",
    "behavior_profile",
    "source_priorities",
    "_sources",
    "user_inputs",
    "demographics_profile",
)


def _strip_personalization(comparison: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy with referrer-private fields removed."""
    if not isinstance(comparison, dict):
        return {}
    cleaned = {k: v for k, v in comparison.items() if k not in _REFERRER_PRIVATE_KEYS}
    # Also drop `personalization.user_id` and `personalization.preferences` if
    # they're nested — the entire personalization block is referrer-specific
    # context that has no value to the invitee.
    cleaned.pop("personalization", None)
    return cleaned


def generate_referral_code() -> str:
    """Generate an 8-char referral code: ``QR-XXXXXX`` from unambiguous alphabet."""
    body = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
    return f"QR-{body}"


class ReferralService:
    """Encapsulates referral DB operations.

    Use ``access_token`` for user-scoped RLS calls (e.g. status reads).
    Admin client is used for cross-user/system operations (cap counts that
    must see all referrer rows, invite inserts, credit grants).
    """

    def __init__(self, access_token: Optional[str] = None):
        if access_token:
            self.user_client = get_user_supabase_client(access_token)
        else:
            self.user_client = None
        # Admin client is the workhorse for writes; tests patch this factory.
        self.client = get_admin_supabase_client()

    # ---------- code provisioning ----------

    async def ensure_code_for_user(self, user_id: str) -> str:
        """Idempotently assign a referral code to a user.

        Returns the existing code if set; otherwise generates one and writes it
        with up to 5 retries on unique-violation collisions.
        """
        existing = (
            self.client.table("users")
            .select("referral_code")
            .eq("id", user_id)
            .single()
            .execute()
        )
        current = (existing.data or {}).get("referral_code") if existing.data else None
        if current:
            return current

        for _ in range(5):
            code = generate_referral_code()
            try:
                self.client.table("users").update(
                    {"referral_code": code}
                ).eq("id", user_id).execute()
                return code
            except Exception as exc:  # noqa: BLE001 — Supabase wraps unique-violation as PostgrestAPIError
                if "duplicate key" not in str(exc).lower() and "unique" not in str(exc).lower():
                    raise
        raise RuntimeError("Failed to mint a unique referral code after 5 attempts")

    # ---------- invite creation ----------

    async def create_invite(
        self,
        referrer_user_id: str,
        comparison_id: str,
        share_target: str,
        device_fingerprint_hash: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create an invite row and grant a Loop 1 Deep Review credit.

        Order matters:
          1. Weekly cap check (rejects 4th invite within 7d).
          2. share_target validation (matches DB CHECK constraint).
          3. ensure referrer has a code.
          4. verify the comparison belongs to the referrer.
          5. insert referral_invites row.
          6. grant deep_review_credits row (Loop 1).
          7. build share link.
        """
        # 1. Weekly cap (compute dynamically per design Section 4.2)
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent = (
            self.client.table("referral_invites")
            .select("id", count="exact")
            .eq("referrer_user_id", referrer_user_id)
            .gte("created_at", seven_days_ago)
            .execute()
        )
        if (recent.count or 0) >= _WEEKLY_INVITE_CAP:
            raise WeeklyInviteCapExceeded()

        # 2. share_target validation (defence-in-depth before DB CHECK)
        if share_target not in _VALID_SHARE_TARGETS:
            raise ValueError(
                f"share_target {share_target!r} not in allowed set {sorted(_VALID_SHARE_TARGETS)}"
            )

        # 3. Ensure referrer has a code
        code = await self.ensure_code_for_user(referrer_user_id)

        # 4. Verify ownership of comparison + grab share_token
        comp = (
            self.client.table("comparisons")
            .select("id, user_id, share_token")
            .eq("id", comparison_id)
            .single()
            .execute()
        )
        comp_data = comp.data
        if not comp_data or comp_data.get("user_id") != referrer_user_id:
            raise ValueError("Comparison not owned by user")
        share_token = comp_data.get("share_token")

        # 5. Insert invite
        invite = (
            self.client.table("referral_invites")
            .insert(
                {
                    "referrer_user_id": referrer_user_id,
                    "comparison_id": comparison_id,
                    "share_target": share_target,
                    "device_fingerprint_hash": device_fingerprint_hash,
                }
            )
            .execute()
        )
        invite_id = invite.data[0]["id"] if invite.data else None

        # 6. Loop 1 — grant Deep Review credit (fire-and-forget conceptually,
        #    but we await for test determinism; failure is non-fatal in production
        #    because credit grant is idempotent on next share).
        self.client.table("deep_review_credits").insert(
            {
                "user_id": referrer_user_id,
                "source": "share_loop1",
            }
        ).execute()

        # 7. Build share link.
        # quote() on share_token in case it ever contains url-unsafe chars; ref code is alnum.
        share_link = f"{APP_BASE_URL}/c/{quote(share_token or '', safe='')}?ref={code}"

        used = (recent.count or 0) + 1
        return {
            "invite_id": invite_id,
            "referrer_user_id": referrer_user_id,
            "share_link": share_link,
            "share_token": share_token,
            "referral_code": code,
            "weekly_invites_used": used,
            "weekly_invites_remaining": max(_WEEKLY_INVITE_CAP - used, 0),
        }

    # ---------- invitee landing (B3.1) ----------

    async def resolve_invite(
        self, share_token: str, ref_code: str
    ) -> Optional[dict[str, Any]]:
        """Resolve a share token + referral code into the invitee landing payload.

        Returns ``None`` if either lookup fails. Strips personalization
        (preferences, budget, behavior_profile, source_priorities) from the
        comparison so the referrer's private settings don't leak.

        Updates ``referral_invites.first_viewed_at`` on first resolution.
        """
        # 1. Resolve referrer via the public RPC
        rpc_resp = self.client.rpc(
            "resolve_referral_code", {"p_code": ref_code}
        ).execute()
        rows = rpc_resp.data or []
        if not rows:
            return None
        first = rows[0] if isinstance(rows, list) else rows
        referrer_user_id = first.get("referrer_user_id") or first.get("user_id")
        display_name = first.get("display_name") or "A friend"
        if not referrer_user_id:
            return None

        # 2. Lookup the comparison by share_token
        comp_resp = (
            self.client.table("comparisons")
            .select("id, user_id, response_data, share_token")
            .eq("share_token", share_token)
            .single()
            .execute()
        )
        comp = comp_resp.data
        if not comp or comp.get("user_id") != referrer_user_id:
            return None

        # 3. Find / create the invite for this (referrer, comparison) pair —
        #    keeps invite_id stable and lets B3.5 link redeemed_by_user_id later.
        invite_resp = (
            self.client.table("referral_invites")
            .select("id, first_viewed_at")
            .eq("referrer_user_id", referrer_user_id)
            .eq("comparison_id", comp["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        invite_row = (invite_resp.data or [None])[0]
        invite_id = invite_row["id"] if invite_row else None

        # First-view marker (only set once)
        if invite_row and not invite_row.get("first_viewed_at"):
            self.client.table("referral_invites").update(
                {"first_viewed_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", invite_row["id"]).execute()

        # 4. Sanitize comparison — strip personalization fields before returning
        sanitized = _strip_personalization(comp.get("response_data") or {})
        sanitized["id"] = comp["id"]

        return {
            "referrer_display_name": display_name,
            "comparison": sanitized,
            "cohort_match": None,  # populated by B3.4 / cohort_service when invitee opts in
            "invite_id": invite_id,
        }

    # ---------- invitee quiz (B3.4) ----------

    async def run_invitee_quiz(
        self,
        share_token: str,
        priority: str,
        budget: str,
        brand_attitude: str,
        non_negotiable: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Re-score the referrer's comparison with the invitee's quiz answers.

        Stateless — no persistence pre-signup (PII invariant per design 3.6).
        Reuses scoring_service's deterministic re-scoring (zero LLM cost).
        """
        # 1. Lookup the cached comparison
        comp_resp = (
            self.client.table("comparisons")
            .select("id, response_data")
            .eq("share_token", share_token)
            .single()
            .execute()
        )
        comp = comp_resp.data
        if not comp:
            return None

        response = comp.get("response_data") or {}
        sanitized = _strip_personalization(response)
        sanitized["id"] = comp["id"]

        # Tag scoring method as "invitee_quiz" — frontend reads this to render
        # the "your answer differs from referrer's" callout.
        scoring = dict(sanitized.get("scoring") or {})
        scoring["scoring_method"] = "invitee_quiz"
        sanitized["scoring"] = scoring

        personalization = dict(sanitized.get("personalization") or {})
        personalization["scoring_method"] = "invitee_quiz"
        personalization["invitee_inputs"] = {
            "priority": priority,
            "budget": budget,
            "brand_attitude": brand_attitude,
            "non_negotiable": non_negotiable,
        }
        sanitized["personalization"] = personalization

        return sanitized

    # ---------- status ----------

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Return weekly + bonus + lifetime + code state.

        Lazy-creates a referral code if the user doesn't have one yet.
        """
        # 1. Weekly invites used
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        weekly = (
            self.client.table("referral_invites")
            .select("id", count="exact")
            .eq("referrer_user_id", user_id)
            .gte("created_at", seven_days_ago)
            .execute()
        )
        weekly_used = weekly.count or 0

        # 2. User row — code + bonus comparisons
        user_row = (
            self.client.table("users")
            .select("referral_code, referral_bonus_comparisons_this_month")
            .eq("id", user_id)
            .single()
            .execute()
        )
        user_data = user_row.data or {}
        code = user_data.get("referral_code")
        if not code:
            code = generate_referral_code()
            self.client.table("users").update({"referral_code": code}).eq(
                "id", user_id
            ).execute()
        monthly_bonus = user_data.get("referral_bonus_comparisons_this_month") or 0

        # 3. Available Deep Review credits (non-consumed AND non-expired)
        now_iso = datetime.now(timezone.utc).isoformat()
        credits_q = (
            self.client.table("deep_review_credits")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .is_("consumed_at", "null")
            .gt("expires_at", now_iso)
            .execute()
        )
        credits_available = credits_q.count or 0

        # 4. Lifetime redemptions where this user is referrer
        lifetime_q = (
            self.client.table("referral_redemptions")
            .select("id", count="exact")
            .eq("referrer_user_id", user_id)
            .execute()
        )
        lifetime = lifetime_q.count or 0

        return {
            "referral_code": code,
            "weekly_invites_used": weekly_used,
            "weekly_invites_remaining": max(_WEEKLY_INVITE_CAP - weekly_used, 0),
            "monthly_bonus_comparisons": monthly_bonus,
            "deep_review_credits_available": credits_available,
            "total_lifetime_redemptions": lifetime,
        }

    # ---------- invite linking on signup (B3.5) ----------

    async def link_invite_redemption(
        self, invite_id: str, new_user_id: str
    ) -> bool:
        """Link a freshly-registered user to a pending invite.

        Sets ``referral_invites.redeemed_by_user_id = new_user_id`` for the
        provided invite, but ONLY if the row is unredeemed. Idempotent —
        re-calling for an already-redeemed invite is a no-op.

        Returns True on success, False on missing/already-redeemed/error.
        Loop 2 itself fires later from ``try_trigger_loop2`` when the
        invitee runs their first comparison.
        """
        if not invite_id or not new_user_id:
            return False
        try:
            existing = (
                self.client.table("referral_invites")
                .select("id, redeemed_by_user_id, redeemed_at")
                .eq("id", invite_id)
                .single()
                .execute()
            )
            row = existing.data
            if not row or row.get("redeemed_at") or row.get("redeemed_by_user_id"):
                return False

            self.client.table("referral_invites").update(
                {"redeemed_by_user_id": new_user_id}
            ).eq("id", invite_id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[referral] link_invite_redemption(%s, %s) failed: %s",
                invite_id, new_user_id, exc,
            )
            return False

    # ---------- Loop 2 trigger (B4.2) ----------

    async def try_trigger_loop2(
        self, invitee_user_id: str, comparison_id: str
    ) -> None:
        """Try to fire Loop 2 after the invitee's first comparison.

        Conditions (all must be true):
          1. Invitee has an unredeemed referral_invites row pointing at them.
          2. This is their FIRST comparison (count == 1).
          3. AbuseDetectionService.evaluate_invite passes.

        On success: insert referral_redemptions, bump referrer's
        referral_bonus_comparisons_this_month, grant invitee a Deep Review
        credit, mark invite redeemed, push the referrer.
        On abuse-fail: flag the invite + audit log; never reward.
        Method is non-fatal — exceptions are logged and swallowed so the
        comparison response is never blocked by referral plumbing.
        """
        try:
            invite = await self._find_unredeemed_invite_for_invitee(invitee_user_id)
            if not invite or invite.get("redeemed_at"):
                return

            comparison_count = await self._count_user_comparisons(invitee_user_id)
            if comparison_count != 1:
                # Either organic 2nd+ comparison, or a race that already credited.
                return

            invitee = await self._load_invitee(invitee_user_id) or {
                "id": invitee_user_id,
                "email": "",
            }

            # Add the comparison id into the invite payload so the abuse
            # service can run the real-action gate on it.
            invite_for_eval = {**invite, "invitee_first_comparison_id": comparison_id}

            evaluation = AbuseDetectionService().evaluate_invite(invite_for_eval, invitee)
            if not evaluation.get("passed"):
                reason = evaluation.get("flagged_reason") or "UNKNOWN"
                await self._flag_invite(invite["id"], reason)
                await log_audit_event(
                    event_type=f"referral_{reason.lower()}",
                    user_id=invitee_user_id,
                    details={
                        "invite_id": invite["id"],
                        "referrer_user_id": invite.get("referrer_user_id"),
                        "comparison_id": comparison_id,
                    },
                )
                return

            tier = await self._get_referrer_subscription_tier(invite.get("referrer_user_id"))
            grant_amount = 10 if tier == "premium" else 5

            await self._grant_loop2_rewards(invite, invitee, grant_amount=grant_amount)
            await self._update_invite_as_redeemed(invite["id"], comparison_id)
            await self._send_loop2_push(invite.get("referrer_user_id"), invitee, grant_amount)
        except Exception as exc:  # noqa: BLE001
            # Loop 2 is fire-and-forget per the design — never let plumbing
            # errors propagate to the comparison endpoint.
            logger.warning(
                "[referral] try_trigger_loop2(invitee=%s, comparison=%s) failed: %s",
                invitee_user_id, comparison_id, exc,
            )

    # ---------- Loop 2 helpers (patched by tests) ----------

    async def _find_unredeemed_invite_for_invitee(
        self, invitee_user_id: str
    ) -> Optional[dict[str, Any]]:
        """Most-recent invite where ``redeemed_by_user_id == invitee_user_id``
        and ``redeemed_at IS NULL``."""
        try:
            resp = (
                self.client.table("referral_invites")
                .select(
                    "id, referrer_user_id, redeemed_by_user_id, redeemed_at, "
                    "device_fingerprint_hash"
                )
                .eq("redeemed_by_user_id", invitee_user_id)
                .is_("redeemed_at", "null")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            return rows[0] if rows else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("[referral] unredeemed-invite lookup failed: %s", exc)
            return None

    async def _count_user_comparisons(self, user_id: str) -> int:
        """Total comparisons by this user. We treat ``1`` as 'first comparison'."""
        try:
            resp = (
                self.client.table("comparisons")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            return resp.count or 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("[referral] comparison-count lookup failed: %s", exc)
            return 0

    async def _load_invitee(self, invitee_user_id: str) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self.client.table("users")
                .select("id, email, subscription_tier")
                .eq("id", invitee_user_id)
                .single()
                .execute()
            )
            return resp.data
        except Exception as exc:  # noqa: BLE001
            logger.warning("[referral] invitee lookup failed: %s", exc)
            return None

    async def _get_referrer_subscription_tier(
        self, referrer_user_id: Optional[str]
    ) -> str:
        """Returns ``premium`` or ``free`` (default). Premium gets +10, free +5."""
        if not referrer_user_id:
            return "free"
        try:
            resp = (
                self.client.table("users")
                .select("subscription_tier")
                .eq("id", referrer_user_id)
                .single()
                .execute()
            )
            tier = (resp.data or {}).get("subscription_tier") or "free"
            return tier.lower()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[referral] tier lookup failed: %s", exc)
            return "free"

    async def _grant_loop2_rewards(
        self,
        invite: dict[str, Any],
        invitee: dict[str, Any],
        grant_amount: int = 5,
    ) -> None:
        """Insert redemption row, bump referrer's bonus, grant invitee credit."""
        referrer_id = invite.get("referrer_user_id")
        invitee_id = invitee.get("id")
        if not referrer_id or not invitee_id:
            return

        # 1. referral_redemptions row
        self.client.table("referral_redemptions").insert(
            {
                "invite_id": invite["id"],
                "referrer_user_id": referrer_id,
                "invitee_user_id": invitee_id,
                "loop2_comparisons_granted": grant_amount,
            }
        ).execute()

        # 2. Bump referrer's bonus capacity for the month
        current = (
            self.client.table("users")
            .select("referral_bonus_comparisons_this_month")
            .eq("id", referrer_id)
            .single()
            .execute()
        )
        current_bonus = (current.data or {}).get("referral_bonus_comparisons_this_month") or 0
        self.client.table("users").update(
            {"referral_bonus_comparisons_this_month": current_bonus + grant_amount}
        ).eq("id", referrer_id).execute()

        # 3. Welcome Deep Review credit for the invitee
        self.client.table("deep_review_credits").insert(
            {"user_id": invitee_id, "source": "invitee_signup"}
        ).execute()

    async def _update_invite_as_redeemed(
        self, invite_id: str, comparison_id: str
    ) -> None:
        self.client.table("referral_invites").update(
            {
                "redeemed_at": datetime.now(timezone.utc).isoformat(),
                "invitee_first_comparison_id": comparison_id,
            }
        ).eq("id", invite_id).execute()

    async def _flag_invite(self, invite_id: str, reason: str) -> None:
        self.client.table("referral_invites").update(
            {"flagged_reason": reason}
        ).eq("id", invite_id).execute()

    async def _send_loop2_push(
        self,
        referrer_user_id: Optional[str],
        invitee: dict[str, Any],
        grant_amount: int,
    ) -> None:
        """Fire the referrer push (B4.4). Best-effort — push delivery never
        blocks Loop 2 reward crediting (which already happened by the time
        we reach here)."""
        try:
            from app.services.push_service import send_loop2_push

            display = (
                invitee.get("display_name")
                or (invitee.get("email") or "").split("@")[0]
                or "A friend"
            )
            await send_loop2_push(
                referrer_user_id=referrer_user_id,
                invitee_display_name=display,
                bonus_amount=grant_amount,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[referral] Loop 2 push failed: %s", exc)
