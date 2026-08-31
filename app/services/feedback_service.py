"""
Feedback Service - Save comparison feedback and track user events
"""
import logging
from typing import Dict, List, Optional

from app.services.database_service import get_supabase_client, save_comparison
from app.services.model_config import critic_model

logger = logging.getLogger(__name__)


async def save_comparison_and_track_cohort(
    *,
    full_response: Dict,
    query: str,
    input_type: str,
    user_id: str,
) -> None:
    """Fire-and-forget: save the comparison, then log a `cohort_injected`
    user_events row joined by comparison_id (powers vw_cohort_feedback_lift),
    then attempt the referral Loop 2 trigger if the user has an unredeemed
    invite.

    Sequenced (not parallel) because event + Loop 2 both need the saved
    comparison's id. Errors swallowed — never break the user-facing flow.
    """
    try:
        # G6 integration fix: _verdict_critique is an INTERNAL key — pop it
        # before the comparisons insert so history + the public share read
        # (which serve full_response verbatim) never carry critique internals.
        _crit = (full_response.get("metadata") or {}).pop("_verdict_critique", None)
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
            # I3.2 — persist the self-critique row now that the FK target
            # (comparison_id) exists. The orchestrator threads the critique
            # into metadata._verdict_critique only when ENABLE_SELF_CRITIQUE
            # was ON and a critique ran; absent otherwise. Best-effort —
            # persist_critique swallows its own errors, never blocks.
            if isinstance(_crit, dict):
                await _persist_verdict_critique(comparison_id, _crit)
            # Referral Loop 2 — only fires when the user has an unredeemed
            # invite AND this is their first comparison AND abuse checks pass.
            # Self-contained no-op for organic users (most calls).
            try:
                from app.services.referral_service import ReferralService

                await ReferralService().try_trigger_loop2(
                    invitee_user_id=user_id,
                    comparison_id=comparison_id,
                )
            except Exception as loop2_exc:  # noqa: BLE001
                logger.warning(f"Loop 2 trigger failed (silent): {loop2_exc}")
    except Exception as e:
        logger.warning(f"save_comparison_and_track_cohort failed (silent): {e}")


async def _persist_verdict_critique(comparison_id: str, crit_meta: Dict) -> None:
    """I3.2 — reconstruct a CritiqueResult from the response metadata
    `_verdict_critique` dict and write the verdict_critiques row. Best-effort:
    persist_critique swallows its own DB errors; this wrapper guards the
    reconstruction so a malformed dict can't break the save flow."""
    try:
        from app.services.verdict_critique_service import (
            CritiqueResult,
            persist_critique,
        )

        tokens = int(crit_meta.get("critic_tokens_used", 0) or 0)
        critique = CritiqueResult(
            axis_scores=dict(crit_meta.get("axis_scores") or {}),
            needs_regen=bool(crit_meta.get("needs_regen", False)),
            low_axes=list(crit_meta.get("low_axes") or []),
            regen_reason=crit_meta.get("regen_reason"),
            critic_model=crit_meta.get("critic_model") or critic_model(),
            # tokens_used is a computed property; split back into prompt-only
            # (the exact split isn't persisted — total is what the row stores).
            usage={"prompt_tokens": tokens, "completion_tokens": 0},
        )
        await persist_critique(
            comparison_id=comparison_id,
            critique=critique,
            regenerated=bool(crit_meta.get("regenerated", False)),
        )
    except Exception as exc:  # noqa: BLE001 — observability write, never fatal
        logger.warning(f"verdict_critique persist failed (silent): {exc}")


async def save_feedback(
    user_id: Optional[str],
    comparison_id: Optional[str],
    useful: bool,
    mattered_most: List[str],
    change_suggestion: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict:
    """
    Save comparison feedback to Supabase. Fire-and-forget safe.

    Returns dict with success status. Never raises.

    M13-29: when the caller is authenticated (user_id + access_token) the write
    goes through the RLS-scoped user client instead of the service-role client.
    Anonymous writes keep using the service-role client (unchanged). The
    load-bearing forgery control is the UUID validation on comparison_id at the
    route layer — migrations/010 INSERT policies do not constrain comparison_id,
    so the user client alone would not stop it (recorded follow-up).
    """
    try:
        if user_id and access_token:
            from app.services.database_service import get_user_supabase_client
            client = get_user_supabase_client(access_token)
        else:
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
