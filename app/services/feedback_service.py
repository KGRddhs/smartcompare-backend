"""
Feedback Service - Save comparison feedback and track user events
"""
import logging
from typing import Dict, List, Optional

from app.services.database_service import get_supabase_client, save_comparison

logger = logging.getLogger(__name__)


async def save_comparison_and_track_cohort(
    *,
    full_response: Dict,
    query: str,
    input_type: str,
    user_id: str,
) -> None:
    """Fire-and-forget: save the comparison, then log a `cohort_injected`
    user_events row joined by comparison_id (powers vw_cohort_feedback_lift).

    Sequenced (not parallel) because the event row needs the saved
    comparison's id. Errors swallowed -- never break the user-facing flow.
    """
    try:
        saved = await save_comparison(
            full_response=full_response, query=query,
            input_type=input_type, user_id=user_id,
        )
        comparison_id = (saved or {}).get("id")
        cohort_injected = (full_response.get("metadata") or {}).get("cohort_injected", False)
        if comparison_id:
            await track_event(
                user_id=user_id,
                event_type="comparison_completed",
                event_data={"cohort_injected": bool(cohort_injected)},
                comparison_id=comparison_id,
            )
    except Exception as e:
        logger.warning(f"save_comparison_and_track_cohort failed (silent): {e}")


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
