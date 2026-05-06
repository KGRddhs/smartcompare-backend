"""Re-engagement push selector + 3 detectors.

Replaces price-drop spam with content-rich, decision-relevant pushes:
- Decision Insight — review sentiment shifted ≥10% on a saved product
- Cohort Curiosity — ≥5 same-governorate users picked differently
- Decision Retrospective — 14-day "how'd it work out?" check-in

Selector picks at most 1/week per user, in priority order:
``decision_insight > cohort_curiosity > decision_retrospective``.

Cost guards (design Section 9.4 risk #1):
- Decision Insight only checks products in the global top-100 most-saved
  set (precomputed daily). Per-user check is skipped if the user's
  saved product isn't in that set — keeps Serper cost bounded.
- Detectors are async and fail-closed (None) on any DB/Redis error.

Plan tasks B5.2 + B5.3.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)


_RECENT_PUSH_WINDOW_DAYS = 7
_DECISION_INSIGHT_SHIFT_THRESHOLD = 0.10  # 10% sentiment delta
_COHORT_MIN_USERS = 5
_COHORT_MIN_DIVERGENCE_PCT = 0.40
_RETRO_AGE_DAYS = 14
_RETRO_AGE_TOLERANCE_DAYS = 1


PushPayload = dict[str, Any]


class ReengagementService:
    """Per-user re-engagement evaluator. Stateless; one instance per cron run."""

    def __init__(self):
        self.client = get_admin_supabase_client()

    async def evaluate(self, user: dict[str, Any]) -> Optional[PushPayload]:
        """Decide which (if any) push to send to ``user`` today.

        Returns the PushPayload chosen by the highest-priority detector,
        or None when:
        - the 7-day per-user cap is hit, OR
        - the user's master ``notifications_enabled`` toggle is OFF, OR
        - all 3 sub-toggles (notification_types) are OFF, OR
        - no detector fires.

        The master toggle is also enforced upstream by the cron's
        eligibility query — checking it here is defense-in-depth so a
        direct call to ``evaluate`` (e.g. from tests or future
        integrations) honours the user's preference.
        """
        prefs = (user.get("preferences") or {})
        # Missing key = treated as ON (default ON per design 9.2).
        if prefs.get("notifications_enabled") is False:
            return None

        if await self._recent_push(user):
            return None

        # Per-type sub-toggles. Missing key = ON. Missing parent dict = all ON.
        types = prefs.get("notification_types") or {}
        gated_detectors = []
        if types.get("decision_insight", True):
            gated_detectors.append(self._check_decision_insight)
        if types.get("cohort_curiosity", True):
            gated_detectors.append(self._check_cohort_curiosity)
        if types.get("decision_retrospective", True):
            gated_detectors.append(self._check_decision_retrospective)

        for detector in gated_detectors:
            payload = await detector(user)
            if payload:
                return payload
        return None

    # ---------- 7-day cap ----------

    async def _recent_push(self, user: dict[str, Any]) -> bool:
        """True if user already received a push within the last 7 days."""
        try:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=_RECENT_PUSH_WINDOW_DAYS)
            ).isoformat()
            resp = (
                self.client.table("re_engagement_events")
                .select("id", count="exact")
                .eq("user_id", user.get("id"))
                .gte("triggered_at", cutoff)
                .execute()
            )
            return (resp.count or 0) > 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("[reengagement] _recent_push failed: %s", exc)
            # Fail closed — better to skip than spam on a transient error.
            return True

    # ---------- Decision Insight ----------

    async def _check_decision_insight(
        self, user: dict[str, Any]
    ) -> Optional[PushPayload]:
        saved = await self._get_user_saved_products(user)
        if not saved:
            return None

        top_100 = await self._get_top_100_saved_globally()
        for product in saved[:3]:  # most-recent 3 saved
            product_id = product.get("id")
            if product_id not in top_100:
                continue
            current = await self._compute_current_sentiment(product_id)
            previous = product.get("last_sentiment")
            if current is None or previous is None:
                continue
            if abs(current - previous) >= _DECISION_INSIGHT_SHIFT_THRESHOLD:
                return self._build_insight_payload(user, product, current, previous)
        return None

    # ---------- Cohort Curiosity ----------

    async def _check_cohort_curiosity(
        self, user: dict[str, Any]
    ) -> Optional[PushPayload]:
        governorate = user.get("governorate")
        recent = user.get("recent_comparisons") or []
        if not governorate or not recent:
            return None
        result = await self._count_cohort_divergence(user, recent[0])
        if not result:
            return None
        users = result.get("users", 0)
        divergence = result.get("divergence_pct", 0.0)
        if users >= _COHORT_MIN_USERS and divergence >= _COHORT_MIN_DIVERGENCE_PCT:
            return self._build_cohort_payload(user, users, governorate)
        return None

    # ---------- Decision Retrospective ----------

    async def _check_decision_retrospective(
        self, user: dict[str, Any]
    ) -> Optional[PushPayload]:
        comparison = await self._find_14d_comparison_no_retrospective(user)
        if not comparison:
            return None
        return self._build_retrospective_payload(user, comparison)

    # ---------- detector helpers (patched by tests) ----------

    async def _get_user_saved_products(
        self, user: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """User's saved products, most-recent first.

        Concrete persistence schema TBD — for MVP, callers can pass
        ``user["saved_products"]`` precomputed from the cron's user fetch.
        """
        return user.get("saved_products") or []

    async def _get_top_100_saved_globally(self) -> set[str]:
        """Global top-100 most-saved product ids — cost guard for the
        sentiment recomputation step. Cron should warm this once per run."""
        try:
            # Reach into Redis cache; recompute lives in the cron's prelude.
            from app.services.cache_service import _redis_get
            import json

            raw = _redis_get("reengagement:top100_saved_products")
            if raw:
                return set(json.loads(raw))
            return set()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[reengagement] top-100 lookup failed: %s", exc)
            return set()

    async def _compute_current_sentiment(self, product_id: str) -> Optional[float]:
        """Sentiment score in [0, 1] from the cached review snapshot.

        Returns None when no snapshot is available — detector then skips
        the product (no false-positive fires from missing data).
        """
        try:
            resp = (
                self.client.table("product_reviews")
                .select("sentiment_score")
                .eq("product_id", product_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                return None
            return rows[0].get("sentiment_score")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[reengagement] sentiment lookup failed: %s", exc)
            return None

    async def _count_cohort_divergence(
        self, user: dict[str, Any], comparison: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Count how many same-governorate users ran the same comparison
        recently and what fraction picked a DIFFERENT winner."""
        # MVP: use cohort-aware aggregation in user_events. Concrete query
        # left as DB integration work; tests patch this method directly.
        return None

    async def _find_14d_comparison_no_retrospective(
        self, user: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """User's comparison from ~14 days ago that hasn't had a retrospective
        push sent for it yet."""
        try:
            target = datetime.now(timezone.utc) - timedelta(days=_RETRO_AGE_DAYS)
            from_ = (target - timedelta(days=_RETRO_AGE_TOLERANCE_DAYS)).isoformat()
            to_ = (target + timedelta(days=_RETRO_AGE_TOLERANCE_DAYS)).isoformat()
            resp = (
                self.client.table("comparisons")
                .select("id, full_response, created_at")
                .eq("user_id", user.get("id"))
                .gte("created_at", from_)
                .lte("created_at", to_)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                return None
            comp = rows[0]

            # Skip if a retrospective for this comparison was already sent.
            sent = (
                self.client.table("re_engagement_events")
                .select("id", count="exact")
                .eq("user_id", user.get("id"))
                .eq("event_type", "decision_retrospective")
                .eq("comparison_id", comp["id"])
                .execute()
            )
            if (sent.count or 0) > 0:
                return None
            return comp
        except Exception as exc:  # noqa: BLE001
            logger.warning("[reengagement] retro lookup failed: %s", exc)
            return None

    # ---------- payload builders ----------

    def _user_language(self, user: dict[str, Any]) -> str:
        return (user.get("preferences") or {}).get("language") or "English"

    def _build_insight_payload(
        self,
        user: dict[str, Any],
        product: dict[str, Any],
        current: float,
        previous: float,
    ) -> PushPayload:
        product_name = product.get("name") or "Your saved product"
        is_arabic = self._user_language(user) == "Arabic"
        if is_arabic:
            title = f"تحديث على {product_name}"
            body = "مراجعات جديدة، صورة جديدة. اعد الفحص قبل ما تشتري."
        else:
            title = f"{product_name} update: new reviews shifted the picture."
            body = "Re-check before buying."
        product_id = product.get("id") or ""
        return {
            "event_type": "decision_insight",
            "title": title,
            "body": body,
            "deep_link_url": f"qaren://comparison/{product_id}?banner=insight",
            "comparison_id": product_id,
            "metadata": {"sentiment_previous": previous, "sentiment_current": current},
        }

    def _build_cohort_payload(
        self, user: dict[str, Any], n_users: int, governorate: str
    ) -> PushPayload:
        is_arabic = self._user_language(user) == "Arabic"
        if is_arabic:
            title = f"{n_users} ناس في {governorate} اختاروا غيرك هالأسبوع."
            body = "ليش؟"
        else:
            title = f"{n_users} people near you chose differently this week."
            body = "Why?"
        return {
            "event_type": "cohort_curiosity",
            "title": title,
            "body": body,
            "deep_link_url": "qaren://cohort/divergence",
            "metadata": {"governorate": governorate, "users": n_users},
        }

    def _build_retrospective_payload(
        self, user: dict[str, Any], comparison: dict[str, Any]
    ) -> PushPayload:
        full = comparison.get("full_response") or {}
        winner = (full.get("winner") or {}).get("name") or "your decision"
        is_arabic = self._user_language(user) == "Arabic"
        if is_arabic:
            title = f"مر 14 يوم على قرارك."
            body = f"كيف طلع {winner}؟ ساعد ناس ثاني محتارة."
        else:
            title = "14 days since your call."
            body = f"How'd {winner} turn out? Help the next person decide."
        comp_id = comparison.get("id", "")
        return {
            "event_type": "decision_retrospective",
            "title": title,
            "body": body,
            "deep_link_url": f"qaren://comparison/{comp_id}?banner=retrospective",
            "comparison_id": comp_id,
        }
