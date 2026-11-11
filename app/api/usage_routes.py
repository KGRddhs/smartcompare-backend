"""Usage status endpoint for freemium tier tracking."""
from fastapi import APIRouter, Depends
from app.services.usage_service import (
    device_daily_quota_enabled,
    device_quota_kwargs,
    get_device_usage_status,
    get_usage_status,
)
from app.api.auth_routes import get_current_user

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get("/status")
async def usage_status(current_user: dict = Depends(get_current_user)):
    """Get current usage counts and limits for the authenticated user."""
    # S81-09: under ENABLE_DEVICE_DAILY_QUOTA (read per call, first) the
    # quota-path status, keyed on the request's bound X-Device-Fingerprint
    # (device_quota_kwargs reads the S81-05 ContextVar; the route never reads
    # the header and never names the leaf itself).
    if device_daily_quota_enabled():
        return await get_device_usage_status(
            user_id=current_user["id"],
            access_token=current_user.get("access_token", ""),
            **device_quota_kwargs(),
        )
    return await get_usage_status(
        user_id=current_user["id"],
        access_token=current_user.get("access_token", ""),
    )
