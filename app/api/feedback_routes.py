"""
Feedback Routes - Comparison feedback and event tracking endpoints
"""
import asyncio
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.api.auth_routes import get_optional_user
from app.middleware.rate_limiter import limiter
from app.services.feedback_service import save_feedback, track_events_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])

VALID_MATTERED_MOST = [
    "price", "specs", "reviews", "brand", "value", "warranty", "ratings"
]

VALID_EVENT_TYPES = [
    "save", "share", "source_click", "tab_switch",
    "feedback_submit", "result_view_duration"
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

    # Fire-and-forget
    asyncio.create_task(save_feedback(
        user_id=user_id,
        comparison_id=body.comparison_id,
        useful=body.useful,
        mattered_most=body.mattered_most,
        change_suggestion=body.change_suggestion,
    ))

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

    # Fire-and-forget
    asyncio.create_task(track_events_batch(events))

    return {"success": True, "message": f"{len(events)} events received"}
