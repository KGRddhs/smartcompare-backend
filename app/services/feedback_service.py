"""
Feedback Service - Save comparison feedback and track user events
"""
import logging
from typing import Dict, List, Optional

from app.services.database_service import get_supabase_client

logger = logging.getLogger(__name__)


async def save_feedback(
    user_id: Optional[str],
    comparison_id: Optional[str],
    useful: bool,
    mattered_most: List[str],
    change_suggestion: Optional[str] = None,
) -> dict:
    """
    Save comparison feedback to Supabase. Fire-and-forget safe.

    Returns dict with success status. Never raises.
    """
    try:
        client = get_supabase_client()
        record: Dict = {
            "useful": useful,
            "mattered_most": mattered_most,
        }
        if user_id:
            record["user_id"] = user_id
        if comparison_id:
            record["comparison_id"] = comparison_id
        if change_suggestion:
            record["change_suggestion"] = change_suggestion

        response = client.table("comparison_feedback").insert(record).execute()
        return {"success": True, "id": response.data[0]["id"] if response.data else None}
    except Exception as e:
        logger.warning(f"Error saving feedback: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def track_event(
    user_id: Optional[str],
    event_type: str,
    event_data: dict,
    comparison_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict:
    """
    Track a single user event. Fire-and-forget safe.

    Returns dict with success status. Never raises.
    """
    try:
        client = get_supabase_client()
        record: Dict = {
            "event_type": event_type,
            "event_data": event_data,
        }
        if user_id:
            record["user_id"] = user_id
        if comparison_id:
            record["comparison_id"] = comparison_id
        if session_id:
            record["session_id"] = session_id

        response = client.table("user_events").insert(record).execute()
        return {"success": True, "id": response.data[0]["id"] if response.data else None}
    except Exception as e:
        logger.warning(f"Error tracking event: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def track_events_batch(events: List[dict]) -> List[dict]:
    """
    Batch insert multiple user events. Fire-and-forget safe.

    Each event dict should have: event_type, event_data, and optionally
    user_id, comparison_id, session_id.

    Returns list of result dicts. Never raises.
    """
    try:
        client = get_supabase_client()
        records = []
        for evt in events:
            record: Dict = {
                "event_type": evt["event_type"],
                "event_data": evt.get("event_data", {}),
            }
            if evt.get("user_id"):
                record["user_id"] = evt["user_id"]
            if evt.get("comparison_id"):
                record["comparison_id"] = evt["comparison_id"]
            if evt.get("session_id"):
                record["session_id"] = evt["session_id"]
            records.append(record)

        response = client.table("user_events").insert(records).execute()
        return [{"success": True, "id": r["id"]} for r in (response.data or [])]
    except Exception as e:
        logger.warning(f"Error batch tracking events: {e}", exc_info=True)
        return [{"success": False, "error": str(e)}]
