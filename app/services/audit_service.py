"""Audit logging service — fire-and-forget security event recording."""
import logging
from typing import Optional
from datetime import datetime, timezone

from app.services.database_service import get_admin_supabase_client

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
        admin_access, usage_limit_hit, injection_attempt
    """
    try:
        client = get_admin_supabase_client()
        client.table("admin_audit_log").insert({
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log audit event '{event_type}': {e}")
