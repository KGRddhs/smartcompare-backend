"""
Share Routes - Public comparison sharing endpoints
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Path
from starlette.requests import Request

from app.api.auth_routes import get_current_user
from app.services.database_service import create_share_token, get_shared_comparison, ShareTokenError
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/share", tags=["sharing"])

SHARE_BASE_URL = "https://web-production-58776.up.railway.app/api/v1/share"


@router.post("/{comparison_id}")
@limiter.limit("10/minute")
async def share_comparison(
    request: Request,
    comparison_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Generate a share link for a comparison. Requires ownership."""
    try:
        token = await create_share_token(str(comparison_id), current_user["id"])
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized to share this comparison")
    except ShareTokenError as exc:
        # Persistence failure (schema drift, RLS, transient DB outage).
        # 500 with cause beats a misleading 404 — the underlying issue is
        # already logged at ERROR by the service layer.
        logger.error(f"Share token creation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"code": "SHARE_TOKEN_FAILED", "error": "Failed to create share link"},
        )

    if not token:
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "success": True,
        "share_token": token,
        "share_url": f"{SHARE_BASE_URL}/{token}",
    }


@router.get("/{token}")
@limiter.limit("30/minute")
async def view_shared_comparison(
    request: Request,
    token: str = Path(..., pattern=r"^[A-Za-z0-9_-]{18,30}$"),
):
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
