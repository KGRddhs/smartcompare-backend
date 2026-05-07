"""Daily cron entrypoint — sends 24h-before-expiry reminder push for
referral bonus credits.

Schedule: once per day. Iterates referral_redemptions where
expires_at falls in the next 24h AND consumed_at IS NULL AND
expiry_reminder_sent_at IS NULL. For each row, sends a localized push
to the referrer ("Don't forget — your X bonus comparisons expire
tomorrow."), then stamps expiry_reminder_sent_at = NOW() to enforce
idempotency on retry.

Path-(a) invariant (plan task 35): this cron does NOT mutate any
counters. Entitlement is computed live from referral_redemptions in
usage_service. The cron's only job is the push.

Hard caps to keep cost predictable:
- ≤1000 rows per run (LIMIT in fetch query + defensive slice).
- 1 push per redemption row, ever (expiry_reminder_sent_at flag).

Feature flag: ENABLE_BONUS_EXPIRY_PUSHES (default OFF in code; flip in
Railway during canary). When OFF, fetch returns immediately without
sending pushes.

Plan task 36.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.database_service import get_admin_supabase_client
from app.services.push_service import send_push

logger = logging.getLogger(__name__)


# Hard cap on rows processed per cron run.
_MAX_ROWS_PER_RUN = 1000

# 24h reminder window — find rows expiring within this many hours.
_REMINDER_WINDOW_HOURS = 24


def _flag_enabled() -> bool:
    """Feature flag: ENABLE_BONUS_EXPIRY_PUSHES (default OFF in code,
    flipped ON in Railway during canary). Mirrors the
    ENABLE_REENGAGEMENT_PUSHES pattern."""
    return os.getenv("ENABLE_BONUS_EXPIRY_PUSHES", "false").lower() == "true"


async def _fetch_expiring_redemptions(
    client, *, window_hours: int = _REMINDER_WINDOW_HOURS, limit: int = _MAX_ROWS_PER_RUN
) -> list[dict[str, Any]]:
    """Return unconsumed, un-notified referral_redemptions rows with
    expires_at falling between now and now+window_hours.

    Filters (path-(a) idempotency invariants):
    - expires_at > now (ignore already-expired rows; no point reminding)
    - expires_at <= now + 24h
    - consumed_at IS NULL (consumed bonuses don't need a reminder)
    - expiry_reminder_sent_at IS NULL (idempotency — don't re-send)
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=window_hours)
    try:
        resp = (
            client.table("referral_redemptions")
            .select(
                "id, referrer_user_id, invitee_user_id, "
                "loop2_comparisons_granted, expires_at, consumed_at, "
                "expiry_reminder_sent_at"
            )
            .gt("expires_at", now.isoformat())
            .lte("expires_at", end.isoformat())
            .is_("consumed_at", "null")
            .is_("expiry_reminder_sent_at", "null")
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_expire_bonuses] fetch failed: %s", exc)
        return []


async def _mark_reminder_sent(client, *, redemption_id: str) -> None:
    """Stamp expiry_reminder_sent_at = NOW() so the cron never re-sends."""
    try:
        client.table("referral_redemptions").update(
            {"expiry_reminder_sent_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", redemption_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[cron_expire_bonuses] mark-sent failed for %s: %s", redemption_id, exc
        )


def _reminder_copy(grant_amount: int) -> tuple[str, str]:
    """English copy for the 24h expiry reminder. Localization could be
    extended later via push_service language helpers, but the simple
    inline copy keeps this cron self-contained.
    """
    title = "Your bonus comparisons expire tomorrow"
    body = (
        f"Don't forget — your {grant_amount} bonus comparisons expire in 24 hours."
    )
    return title, body


async def _send_reminder(row: dict[str, Any]) -> None:
    """Fire-and-forget reminder push. Errors are logged, never raised."""
    referrer_id = row.get("referrer_user_id")
    if not referrer_id:
        return
    grant_amount = int(row.get("loop2_comparisons_granted") or 0)
    title, body = _reminder_copy(grant_amount)
    try:
        await send_push(
            user_id=referrer_id,
            title=title,
            body=body,
            data={
                "url": "qaren://profile/referrals",
                "type": "bonus_expiry_reminder",
                "redemption_id": row.get("id"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[cron_expire_bonuses] reminder push failed for redemption=%s: %s",
            row.get("id"), exc,
        )


async def main() -> None:
    """Cron entrypoint. Idempotent — safe to retry on transient failure."""
    if not _flag_enabled():
        logger.info(
            "[cron_expire_bonuses] ENABLE_BONUS_EXPIRY_PUSHES=false, skipping run"
        )
        return

    client = get_admin_supabase_client()
    rows = await _fetch_expiring_redemptions(client)
    if not rows:
        logger.info("[cron_expire_bonuses] no expiring redemptions this run")
        return

    # Defensive slice in case a patched fetcher in tests returns >cap.
    rows = rows[:_MAX_ROWS_PER_RUN]

    sent = 0
    for row in rows:
        await _send_reminder(row)
        await _mark_reminder_sent(client, redemption_id=row["id"])
        sent += 1

    logger.info(
        "[cron_expire_bonuses] processed %d rows, sent %d reminder pushes",
        len(rows), sent,
    )


# Alias for backwards-compat with test contract (some callers use `run`).
run = main


if __name__ == "__main__":
    asyncio.run(main())
