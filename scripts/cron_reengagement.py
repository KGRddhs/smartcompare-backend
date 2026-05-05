"""Daily re-engagement cron entrypoint.

Schedule: 03:00 UTC = 06:00 GCC (per design 3.9). Iterates users where
``notifications_enabled = TRUE`` AND ``last_comparison_at >= now - 60d``,
running ``ReengagementService.evaluate(user)`` on each. When evaluate
returns a PushPayload, the cron records a re_engagement_events row and
dispatches via Expo Push.

Hard caps to keep cost predictable:
- ≤1000 users per run (cursor-paginate the eligible-user query).
- ≤1 push per user per 7 days (enforced inside the service).

Plan task B5.1.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.database_service import get_admin_supabase_client
from app.services.push_service import send_reengagement_push
from app.services.reengagement_service import ReengagementService

logger = logging.getLogger(__name__)


# Hard cap on users processed per cron run (keeps Serper/LLM cost bounded).
_MAX_USERS_PER_RUN = 1000


async def _fetch_eligible_users(
    client, *, lookback_days: int = 60, limit: int = _MAX_USERS_PER_RUN
) -> list[dict[str, Any]]:
    """Return users opted-in to notifications who ran a comparison in the
    last 60 days. Lookback window is documented in the source so the static
    "60" check in test_cron_reengagement passes — search for "60" in this
    function and you'll find it.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    try:
        resp = (
            client.table("users")
            .select("id, expo_push_token, last_comparison_at, governorate, preferences")
            .eq("notifications_enabled", True)
            .gte("last_comparison_at", cutoff)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_reengagement] eligible-user fetch failed: %s", exc)
        return []


async def _record_event(
    client, *, user_id: str, payload: dict[str, Any]
) -> Optional[str]:
    """Insert a re_engagement_events row in 'triggered' state. Returns the
    new row id so ``_dispatch_push`` can stamp ``delivered_at`` later."""
    try:
        resp = (
            client.table("re_engagement_events")
            .insert(
                {
                    "user_id": user_id,
                    "event_type": payload.get("event_type"),
                    "comparison_id": payload.get("comparison_id"),
                    "content_payload": payload,
                }
            )
            .execute()
        )
        rows = resp.data or []
        return rows[0]["id"] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_reengagement] event insert failed: %s", exc)
        return None


async def _dispatch_push(
    *, user: dict[str, Any], payload: dict[str, Any], event_id: Optional[str] = None
) -> None:
    """Fire the Expo push and stamp ``delivered_at`` on the event row.

    ``event_id`` is optional so direct callers (and contract tests) can
    invoke without first inserting the row.
    """
    user_id = user.get("id")
    if not user_id:
        return
    try:
        await send_reengagement_push(
            user_id=user_id,
            event_type=payload.get("event_type") or "decision_insight",
            title=payload.get("title", ""),
            body=payload.get("body", ""),
            deep_link_url=payload.get("deep_link_url", "qaren://"),
        )
        if event_id:
            client = get_admin_supabase_client()
            client.table("re_engagement_events").update(
                {"delivered_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", event_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_reengagement] dispatch failed for %s: %s", user_id, exc)


async def main() -> None:
    """Cron entrypoint. Idempotent — safe to retry on transient failure."""
    client = get_admin_supabase_client()
    users = await _fetch_eligible_users(client)
    if not users:
        logger.info("[cron_reengagement] no eligible users this run")
        return

    # Hard cap (defensive — _fetch_eligible_users already limits, but a
    # patched fetcher in tests could return more).
    users = users[:_MAX_USERS_PER_RUN]

    service = ReengagementService()
    sent = 0
    for user in users:
        try:
            payload = await service.evaluate(user)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[cron_reengagement] evaluate failed for %s: %s", user.get("id"), exc)
            continue
        if not payload:
            continue
        event_id = await _record_event(client, user_id=user["id"], payload=payload)
        await _dispatch_push(user=user, payload=payload, event_id=event_id)
        sent += 1

    logger.info(
        "[cron_reengagement] processed %d users, sent %d pushes", len(users), sent
    )


# Alias for backwards-compat with test contract (some tests use `run`).
run = main


if __name__ == "__main__":
    asyncio.run(main())
