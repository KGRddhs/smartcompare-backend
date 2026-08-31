"""Audit logging service — fire-and-forget security event recording."""
import logging
from typing import Optional
from datetime import datetime, timezone

from app.services.database_service import get_admin_supabase_client
from app.utils.db_offload import run_db  # M13-05 ENABLE_SYNC_DB_OFFLOAD

logger = logging.getLogger(__name__)


async def log_audit_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    endpoint: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Log a security-relevant event to admin_audit_log table.

    This function is designed to be called via asyncio.create_task()
    so it never blocks the request. Errors are logged, not raised.

    Event types:
        login_success, login_failed, account_deleted, email_changed,
        password_changed, rate_limit_exceeded, brute_force_lockout,
        admin_access, usage_limit_hit, injection_attempt, content_blocked
    """
    try:
        client = get_admin_supabase_client()
        await run_db(lambda: client.table("admin_audit_log").insert({
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute())
    except Exception as e:
        logger.error(f"Failed to log audit event '{event_type}': {e}")


# Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 5.2
_CONTENT_BLOCK_LAYERS = frozenset({
    "query_prefilter",
    "image_filter",
    "moderation_api",
    "vision_moderation",
})


async def log_content_blocked(layer: str, query_hash: str) -> None:
    """Log a content_blocked event to admin_audit_log.

    Privacy invariant: we log a SHA-256 hash of the offending input, never
    the raw input (spec § 5.2). Caller is responsible for hashing before
    calling this helper.

    Args:
        layer: which moderation layer rejected the input. One of:
            "query_prefilter", "image_filter", "moderation_api",
            "vision_moderation".
        query_hash: SHA-256 hex digest of the offending input (64 chars).
    """
    if layer not in _CONTENT_BLOCK_LAYERS:
        logger.warning(f"log_content_blocked called with unknown layer {layer!r}; allowing through")
    await log_audit_event(
        event_type="content_blocked",
        details={"layer": layer, "query_hash": query_hash},
    )
