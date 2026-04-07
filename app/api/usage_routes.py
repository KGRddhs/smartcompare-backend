"""Usage status endpoint for freemium tier tracking."""
from fastapi import APIRouter, Depends
from app.services.usage_service import get_usage_status
from app.api.auth_routes import get_current_user

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get("/status")
async def usage_status(current_user: dict = Depends(get_current_user)):
    """Get current usage counts and limits for the authenticated user."""
    return await get_usage_status(
        user_id=current_user["id"],
        access_token=current_user.get("access_token", ""),
    )
