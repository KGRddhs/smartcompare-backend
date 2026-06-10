"""
Feedback Routes - Comparison feedback and event tracking endpoints
"""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.api.auth_routes import get_optional_user
from app.middleware.rate_limiter import limiter
from app.services.feedback_service import save_feedback, track_events_batch
from app.utils.async_utils import fire_and_forget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])

VALID_MATTERED_MOST = [
    "price", "specs", "reviews", "brand", "value", "warranty", "ratings"
]

# Allowlist of event_type values accepted by POST /events. This MUST be a
# SUPERSET of every event_type the mobile app fires via trackEvent/trackEvents
# (api.ts) — an unknown type 422-rejects the WHOLE batch, silently dropping
# the events server-side. tests/test_events_allowlist_superset.py greps the FE
# src/ call sites and fails if any literal event_type is missing here.
#
# NOTE: comparison_wall_time is intentionally NOT here — it is a Sentry
# captureMessage (wallTimeInstrumentation.ts), not an /events write.
VALID_EVENT_TYPES = [
    # Generic / legacy.
    "save", "share", "source_click", "tab_switch",
    "feedback_submit", "result_view_duration",
    # Home compare-entry funnel (Bundle B two-input UX, HomeScreen.tsx).
    "compare_entry_view",
    "compare_entry_paywall_banner_view",
    "compare_entry_paywall_banner_tap",
    "compare_entry_content_block",
    "compare_entry_submit",
    "compare_entry_paste_split",
    "compare_entry_mode_autoswitch",
    "compare_entry_ready",
    # Results screen (ResultsScreen.tsx) — share funnel + demographics modal.
    "share_sheet_opened",
    "share_completed",
    "demographics_submitted",
    "demographics_dismissed",
    # Onboarding funnel (OnboardingScreen.tsx / onboarding/OnboardingFlow.tsx).
    "onboarding_started",
    "onboarding_step_completed",
    "onboarding_completed",
    # Bundle B B.1 (F3.5) — pain-workflow signals emitted from the mobile
    # StreamingProductCard. These land in user_events; the backend
    # pain_workflow derivation (B.2, pain_workflow_service) maps them onto
    # pain_workflow_events.signal_type later.
    "spec_expand",      # user expanded the spec list past the 3-row preview (too_many_specs)
    "result_abandon",   # card unmounted before the verdict stage (abandonment mid-stream)
    "screenshot",       # user screenshotted the comparison (share-intent / decision-capture)
]

MAX_BATCH_SIZE = 50


# ============================================
# Request Models
# ============================================

class FeedbackRequest(BaseModel):
    useful: bool
    comparison_id: Optional[str] = None
    mattered_most: List[str] = Field(default_factory=list)
    change_suggestion: Optional[str] = Field(None, max_length=1000)

    @field_validator("mattered_most")
    @classmethod
    def validate_mattered_most(cls, v: List[str]) -> List[str]:
        for item in v:
            if item not in VALID_MATTERED_MOST:
                raise ValueError(
                    f"Invalid mattered_most item: {item}. "
                    f"Must be one of {VALID_MATTERED_MOST}"
                )
        return v


class EventItem(BaseModel):
    event_type: str
    event_data: dict = Field(default_factory=dict)
    comparison_id: Optional[str] = None

    @field_validator("event_data")
    @classmethod
    def validate_event_data_size(cls, v: dict) -> dict:
        if len(json.dumps(v, default=str)) > 10_000:
            raise ValueError("event_data too large (max 10KB)")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type: {v}. Must be one of {VALID_EVENT_TYPES}"
            )
        return v


class EventBatchRequest(BaseModel):
    events: List[EventItem] = Field(..., max_length=MAX_BATCH_SIZE)


# ============================================
# Endpoints
# ============================================

@router.post("/feedback")
@limiter.limit("30/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    user=Depends(get_optional_user),
):
    """
    Submit feedback on a comparison result.
    Auth is optional — anonymous feedback accepted.
    """
    user_id = user.get("id") if user else None

    # Fire-and-forget — Bundle D 2.B.6 WRAP: feedback is an audit-grade
    # write; silent failures must surface to Sentry via the done callback.
    fire_and_forget(
        save_feedback(
            user_id=user_id,
            comparison_id=body.comparison_id,
            useful=body.useful,
            mattered_most=body.mattered_most,
            change_suggestion=body.change_suggestion,
        ),
        label="save_feedback",
    )

    return {"success": True, "message": "Feedback received"}


@router.post("/events")
@limiter.limit("60/minute")
async def track_events(
    request: Request,
    body: EventBatchRequest,
    user=Depends(get_optional_user),
):
    """
    Batch track user events.
    Auth is optional — anonymous events accepted.
    Max 50 events per request.
    """
    user_id = user.get("id") if user else None

    events = []
    for evt in body.events:
        events.append({
            "user_id": user_id,
            "event_type": evt.event_type,
            "event_data": evt.event_data,
            "comparison_id": evt.comparison_id,
        })

    # Fire-and-forget — Bundle D 2.B.6 WRAP: event tracking failures
    # were previously invisible; logger.warning on done callback surfaces
    # them in Sentry without breaking the response.
    fire_and_forget(track_events_batch(events), label="track_events_batch")

    return {"success": True, "message": f"{len(events)} events received"}
