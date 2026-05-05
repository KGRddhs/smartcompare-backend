"""Referral system HTTP layer.

Endpoints:
- POST   /api/v1/referrals/share              (auth)         B2.1
- GET    /api/v1/referrals/status             (auth)         B2.2
- GET    /api/v1/referrals/invite/{token}     (auth-OPTIONAL) B3.1
- POST   /api/v1/referrals/invite/{token}/quiz (auth-OPTIONAL) B3.4

Design contract: docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
Plan tasks: B2.1, B2.2, B3.1, B3.4.

Feature flag: every endpoint is gated by ``ENABLE_REFERRAL_SYSTEM``
(env var, default OFF in code per design 9.2). When OFF, all endpoints
respond with 503 — frontend doesn't expose UI yet either, but the gate
prevents direct curl probing during canary. Conftest flips it ON for
unit tests so the existing GREEN suite keeps passing.

NOTE: this module deliberately does NOT use ``from __future__ import
annotations`` — FastAPI's parameter resolver re-evaluates body model
annotations at registration time and stringified Pydantic forward refs
trip the resolver with ``PydanticUndefinedAnnotation`` on Python 3.12.
"""
import os
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.api.auth_routes import (
    VALID_BRAND_ATTITUDE,
    VALID_BUDGET,
    VALID_PRIORITIES,
    get_current_user,
    get_optional_user,
)
from app.middleware.rate_limiter import limiter
from app.services.referral_service import (
    ReferralService,
    WeeklyInviteCapExceeded,
)


def _is_referral_enabled() -> bool:
    """Read ENABLE_REFERRAL_SYSTEM at request time. Default OFF for safe
    rollback — Ahmed flips this to ``true`` in Railway during canary."""
    return os.getenv("ENABLE_REFERRAL_SYSTEM", "false").strip().lower() == "true"


def _require_referral_enabled() -> None:
    """Dependency that raises 503 when the feature flag is off."""
    if not _is_referral_enabled():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "FEATURE_DISABLED",
                "error": "Referral system is not enabled in this environment.",
            },
        )


router = APIRouter(prefix="/api/v1/referrals", tags=["referrals"])

ShareTarget = Literal["whatsapp", "copy", "x", "telegram", "snapchat", "other"]

# Invitee quiz brand-attitude enum — design 3.6 spec uses a 3-option set
# distinct from the onboarding VALID_BRAND_ATTITUDE. Kept separate so the
# invitee quiz doesn't widen the user-facing onboarding contract.
VALID_QUIZ_BRAND_ATTITUDE = {
    "trust_known_brands",
    "open_to_emerging",
    "value_first",
} | set(VALID_BRAND_ATTITUDE)


class SharePrivacy(BaseModel):
    """Per-share privacy toggles surfaced in the ShareBottomSheet UI
    (design 3.3). show_budget is intentionally absent — always false."""

    model_config = {"extra": "ignore"}  # silently drop unknown fields like show_budget

    show_name: bool = True
    show_result: bool = True
    show_reasons: bool = True


class ShareRequest(BaseModel):
    comparison_id: str = Field(..., min_length=1, max_length=128)
    share_target: ShareTarget
    device_fingerprint_hash: Optional[str] = Field(default=None, max_length=128)
    privacy: Optional[SharePrivacy] = None


class InviteeQuizRequest(BaseModel):
    priority: str = Field(..., min_length=1, max_length=64)
    budget: str = Field(..., min_length=1, max_length=32)
    brand_attitude: str = Field(..., min_length=1, max_length=64)
    non_negotiable: Optional[str] = Field(default=None, max_length=256)

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_PRIORITIES)}")
        return v

    @field_validator("budget")
    @classmethod
    def _validate_budget(cls, v: str) -> str:
        if v not in VALID_BUDGET:
            raise ValueError(f"budget must be one of {sorted(VALID_BUDGET)}")
        return v

    @field_validator("brand_attitude")
    @classmethod
    def _validate_brand_attitude(cls, v: str) -> str:
        if v not in VALID_QUIZ_BRAND_ATTITUDE:
            raise ValueError(
                f"brand_attitude must be one of {sorted(VALID_QUIZ_BRAND_ATTITUDE)}"
            )
        return v


# ============================================
# B2.1 — POST /share — referrer initiates a share, Loop 1 fires
# ============================================


@router.post("/share", status_code=201)
@limiter.limit("10/minute")
async def share_comparison(
    request: Request,
    body: ShareRequest,
    user: dict = Depends(get_current_user),
    _flag: None = Depends(_require_referral_enabled),
):
    """Create a referral invite and grant the referrer a Deep Review credit.

    Returns ``{success, invite_id, share_link, weekly_invites_used,
    weekly_invites_remaining, ...}`` per design Section 3.4.
    """
    service = ReferralService(access_token=user.get("access_token"))
    privacy_dict = body.privacy.model_dump() if body.privacy else None
    try:
        result = await service.create_invite(
            referrer_user_id=user["id"],
            comparison_id=body.comparison_id,
            share_target=body.share_target,
            device_fingerprint_hash=body.device_fingerprint_hash,
            privacy=privacy_dict,
        )
    except WeeklyInviteCapExceeded:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "WEEKLY_INVITE_CAP",
                "error": "You've used your 3 gifts this week. New invites refresh weekly.",
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "error": str(exc)},
        )

    return {"success": True, **result}


# ============================================
# B2.2 — GET /status — referrer's referral state
# ============================================


@router.get("/status")
async def get_referral_status(
    request: Request,
    user: dict = Depends(get_current_user),
    _flag: None = Depends(_require_referral_enabled),
):
    """Return weekly + bonus + lifetime + credits state."""
    service = ReferralService(access_token=user.get("access_token"))
    status = await service.get_status(user_id=user["id"])
    # Top-level response shape per design Section 3.10 + plan B2.2
    return status


# ============================================
# B3.1 — GET /invite/{token} — anon invitee landing
# ============================================


@router.get("/invite/{share_token}")
async def resolve_invite(
    share_token: str,
    ref: str,
    user: Optional[dict] = Depends(get_optional_user),
    _flag: None = Depends(_require_referral_enabled),
):
    """Resolve an invite link to referrer + sanitized comparison.

    Auth-optional (PDF #6 — gradual commitment, no signup gate before result).
    Strips personalization (preferences, budget) from the comparison before
    returning it.
    """
    service = ReferralService()
    resolved = await service.resolve_invite(share_token=share_token, ref_code=ref)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "error": "Invite link not found or expired"},
        )
    return resolved


# ============================================
# B3.4 — POST /invite/{token}/quiz — anon personalized rescoring
# ============================================


@router.post("/invite/{share_token}/quiz")
async def submit_invitee_quiz(
    share_token: str,
    body: InviteeQuizRequest,
    user: Optional[dict] = Depends(get_optional_user),
    _flag: None = Depends(_require_referral_enabled),
):
    """Re-score a comparison with the invitee's quiz answers.

    Anon-friendly: no PII stored pre-signup. Returns the same comparison
    response shape as /text/compare but with ``personalization.scoring_method
    = "invitee_quiz"``.
    """
    service = ReferralService()
    result = await service.run_invitee_quiz(
        share_token=share_token,
        priority=body.priority,
        budget=body.budget,
        brand_attitude=body.brand_attitude,
        non_negotiable=body.non_negotiable,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "error": "Invite not found"},
        )
    return result
