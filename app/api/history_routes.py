"""
History Routes - Comparison history endpoints
"""
import hmac
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import Optional

from app.api.auth_routes import get_current_user
from app.services.database_service import (
    get_user_comparisons,
    get_comparison_by_id,
    get_user_comparison_count,
    delete_comparison,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/comparisons", tags=["history"])


def _extract_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


@router.get("/history")
async def list_comparisons(
    search: Optional[str] = Query(None, description="Filter by query text"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user),
    token: Optional[str] = Depends(_extract_token),
):
    """List user's comparison history, paginated and searchable."""
    comparisons = await get_user_comparisons(
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
        search=search,
        access_token=token,
    )

    summaries = []
    for c in comparisons:
        summaries.append({
            "id": c.get("id"),
            "query": c.get("query"),
            "product_names": c.get("product_names", []),
            "input_type": c.get("input_type", "text"),
            "created_at": c.get("created_at"),
        })

    total = await get_user_comparison_count(current_user["id"], access_token=token)

    return {
        "success": True,
        "comparisons": summaries,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{comparison_id}")
async def get_comparison(
    comparison_id: UUID,
    current_user: dict = Depends(get_current_user),
    token: Optional[str] = Depends(_extract_token),
):
    """Get a single comparison with full response data."""
    comparison = await get_comparison_by_id(str(comparison_id), access_token=token)

    # Merge 404/403 -- single 404 for both missing and unauthorized (M1, L2)
    if not comparison or not hmac.compare_digest(
        str(comparison.get("user_id", "")),
        current_user["id"]
    ):
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "success": True,
        "comparison": {
            "id": comparison.get("id"),
            "query": comparison.get("query"),
            "product_names": comparison.get("product_names", []),
            "input_type": comparison.get("input_type", "text"),
            "full_response": comparison.get("full_response"),
            "created_at": comparison.get("created_at"),
        },
    }


@router.delete("/{comparison_id}")
async def remove_comparison(
    comparison_id: UUID,
    current_user: dict = Depends(get_current_user),
    token: Optional[str] = Depends(_extract_token),
):
    """Delete a comparison from history (ownership check)."""
    comparison = await get_comparison_by_id(str(comparison_id), access_token=token)

    # Merge 404/403 -- single 404 (M1, L2)
    if not comparison or not hmac.compare_digest(
        str(comparison.get("user_id", "")),
        current_user["id"]
    ):
        raise HTTPException(status_code=404, detail="Comparison not found")

    deleted = await delete_comparison(str(comparison_id), current_user["id"], access_token=token)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete comparison")

    return {"success": True}
