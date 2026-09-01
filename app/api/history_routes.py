"""
History Routes - Comparison history endpoints
"""
import hmac
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from starlette.requests import Request
from typing import Optional

from app.api.auth_routes import get_current_user
from app.services.cache_service import delete_cached
from app.services.database_service import (
    get_user_comparisons,
    get_comparison_by_id,
    get_user_comparison_count,
    delete_comparison,
)
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/comparisons", tags=["history"])


def _extract_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def _extract_winner_index(full_response) -> Optional[int]:
    """Pull winner_index from full_response.metadata or .comparison; null-safe."""
    if not isinstance(full_response, dict):
        return None
    metadata = full_response.get("metadata")
    if isinstance(metadata, dict) and "winner_index" in metadata:
        return metadata["winner_index"]
    comparison = full_response.get("comparison")
    if isinstance(comparison, dict) and "winner_index" in comparison:
        return comparison["winner_index"]
    return None


def _safe_image_url(product) -> Optional[str]:
    """Mirror of `home_routes._safe_image_url` / `profile_routes._safe_image_url`.

    Returns the image URL when it's a non-empty http(s) string; None
    otherwise. Defensive vs malformed legacy rows holding ints / dicts /
    garbage / dangerous schemes (javascript:, data:).
    """
    raw = product.get("image_url") if isinstance(product, dict) else None
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    if not (stripped.startswith("http://") or stripped.startswith("https://")):
        return None
    return stripped


def _extract_winner_runner_up_image_urls(
    full_response, winner_index: Optional[int],
) -> tuple[Optional[str], Optional[str]]:
    """Return (winner_image_url, runner_up_image_url) for a history row.

    Locked shape with L2 (Wave 2 b565a38). Derived via winner_index against
    full_response.products[*]. Returns (None, None) whenever the shape gap
    prevents deterministic winner/runner-up identification — same key
    contract as the existing /home/smart-pick + /profile/recent-decisions
    surfaces: keys always present, None when undeterminable.
    """
    if winner_index not in (0, 1):
        return (None, None)
    if not isinstance(full_response, dict):
        return (None, None)
    products = full_response.get("products") or []
    if not isinstance(products, list) or len(products) < 2:
        return (None, None)
    loser_index = 1 - winner_index
    return (
        _safe_image_url(products[winner_index] or {}),
        _safe_image_url(products[loser_index] or {}),
    )


@router.get("/history")
@limiter.limit("30/minute")
async def list_comparisons(
    request: Request,
    search: Optional[str] = Query(None, max_length=100, description="Filter by query text"),
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
        full = c.get("full_response")
        winner_index = _extract_winner_index(full)
        # Wave 2 — per-row image_url derived from full_response.products[*]
        # via winner_index + _safe_image_url gate. Always ship both keys
        # (None when undeterminable) so FE consumer can rely on presence.
        winner_image_url, runner_up_image_url = (
            _extract_winner_runner_up_image_urls(full, winner_index)
        )
        summaries.append({
            "id": c.get("id"),
            "query": c.get("query"),
            "product_names": c.get("product_names", []),
            "input_type": c.get("input_type", "text"),
            "winner_index": winner_index,
            "winner_image_url": winner_image_url,
            "runner_up_image_url": runner_up_image_url,
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
@limiter.limit("20/minute")
async def get_comparison(
    request: Request,
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
@limiter.limit("20/minute")
async def remove_comparison(
    request: Request,
    comparison_id: UUID,
    current_user: dict = Depends(get_current_user),
    token: Optional[str] = Depends(_extract_token),
):
    """Delete a comparison from history (ownership check).

    Legacy v1 rows are visible to this endpoint (`include_legacy=True`) so
    that users can clean up stale, unrenderable history. The GET endpoint
    still hides v1 rows. See Bundle A design §5.2.
    """
    comparison = await get_comparison_by_id(
        str(comparison_id), access_token=token, include_legacy=True
    )

    # Merge 404/403 -- single 404 (M1, L2)
    if not comparison or not hmac.compare_digest(
        str(comparison.get("user_id", "")),
        current_user["id"]
    ):
        raise HTTPException(status_code=404, detail="Comparison not found")

    deleted = await delete_comparison(str(comparison_id), current_user["id"], access_token=token)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete comparison")

    # Wave 2 (c) — bust dependent caches so the deleted row stops winning
    # /home/smart-pick (cache_key=home:smart_pick:{user_id}, 5min TTL) and
    # stops appearing in /profile/recent-decisions (cache_key=profile_recent:
    # {user_id}, 5min TTL). Device walk image #13: stale iPhone 14 pick after
    # delete reproduced exactly this race. Fail-soft: delete_cached swallows
    # Redis errors so a Redis outage doesn't fail an otherwise-successful
    # delete; the worst case is up to 5min of stale display.
    user_id = current_user["id"]
    delete_cached(f"home:smart_pick:{user_id}")
    delete_cached(f"profile_recent:{user_id}")
    # #116 — savings now carries a long bust-on-write TTL; a deleted comparison
    # must stop counting toward the banner immediately, not at TTL expiry.
    delete_cached(f"home:savings:{user_id}")

    return {"success": True}
