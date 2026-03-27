"""
Share Routes - Public comparison sharing endpoints
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends

from app.api.auth_routes import get_current_user
from app.services.database_service import create_share_token, get_shared_comparison

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/share", tags=["sharing"])

SHARE_BASE_URL = "https://web-production-58776.up.railway.app/api/v1/share"


@router.post("/{comparison_id}")
async def share_comparison(
    comparison_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Generate a share link for a comparison. Requires ownership."""
    try:
        token = await create_share_token(str(comparison_id), current_user["id"])
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized to share this comparison")

    if not token:
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "success": True,
        "share_token": token,
        "share_url": f"{SHARE_BASE_URL}/{token}",
    }


@router.get("/{token}")
async def view_shared_comparison(token: str):
    """View a shared comparison. No auth required."""
    comparison = await get_shared_comparison(token)

    if not comparison:
        raise HTTPException(status_code=404, detail="Shared comparison not found")

    return {
        "success": True,
        "comparison": {
            "query": comparison.get("query"),
            "product_names": comparison.get("product_names", []),
            "input_type": comparison.get("input_type", "text"),
            "full_response": comparison.get("full_response"),
            "created_at": comparison.get("created_at"),
        },
    }
