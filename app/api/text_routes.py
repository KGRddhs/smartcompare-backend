"""
Text Comparison Routes - API endpoints for text-based product comparisons
"""
import asyncio
import json
import logging
import time
from typing import Optional, Dict, AsyncGenerator
from fastapi import APIRouter, HTTPException, Path, Query, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.structured_comparison_service import (
    get_comparison_service,
    get_regional_prices
)
from app.api.auth_routes import get_optional_user
from app.api.admin_routes import verify_admin_key
from app.services.auth_service import get_user_preferences
from app.services.database_service import save_comparison, log_search
from app.services.feedback_service import save_comparison_and_track_cohort
from app.middleware.rate_limiter import limiter
from app.services.usage_service import check_usage_allowed, record_comparison

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/text", tags=["text-comparison"])


# ============================================
# Request/Response Models
# ============================================

class TextCompareRequest(BaseModel):
    """Request for text-based comparison"""
    query: str  # e.g., "iPhone 15 vs Galaxy S24"
    region: str = "bahrain"
    include_specs: bool = True
    include_reviews: bool = True
    include_pros_cons: bool = True


class QuickCompareRequest(BaseModel):
    """Quick comparison with just product names"""
    product1: str
    product2: str
    region: str = "bahrain"


# ============================================
# Endpoints
# ============================================


@router.post("/compare")
@limiter.limit("10/minute")
async def text_compare(request: Request, body: TextCompareRequest, user: Optional[Dict] = Depends(get_optional_user)):
    """
    Compare products from natural language query.

    Examples:
    - "iPhone 15 vs Galaxy S24"
    - "compare Nido milk with Almarai"
    - "MacBook Air M3 vs Dell XPS 13"

    Returns structured comparison with:
    - Product specs
    - Regional prices (GCC)
    - Reviews summary
    - Pros/cons
    - Winner recommendation
    """
    logger.info(f"Text comparison request: {body.query}")

    service = get_comparison_service()
    start_time = time.time()

    # Fetch user preferences if authenticated
    user_prefs = None
    if user:
        prefs_result = await get_user_preferences(user["id"])
        if prefs_result.get("success") and prefs_result.get("preferences_completed"):
            user_prefs = prefs_result.get("preferences")

    if user and not user_prefs:
        logger.warning(
            f"[PREFS] Authenticated user {user.get('id', 'unknown')} has no preferences. "
            f"prefs_result: {prefs_result}"
        )

    # Usage check for authenticated users
    if user and user.get("id"):
        usage_check = await check_usage_allowed(user["id"], user.get("access_token", ""))
        if not usage_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": f"Comparison limit reached ({usage_check['reason']})",
                    "code": "USAGE_LIMIT",
                    "tier": usage_check["tier"],
                    "remaining": usage_check["remaining"],
                }
            )

    result = await service.compare_from_text(
        query=body.query,
        region=body.region,
        include_specs=body.include_specs,
        include_reviews=body.include_reviews,
        include_pros_cons=body.include_pros_cons,
        user_preferences=user_prefs,
        user_id=user.get("id") if user else None,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not result.get("success"):
        # Log failed search
        asyncio.create_task(log_search(
            query=body.query, input_type="text",
            user_id=user.get("id") if user else None,
            success=False, error_message=result.get("error"),
            duration_ms=duration_ms,
        ))
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    # Extract product names for logging
    product_names = [f"{p.get('brand', '')} {p.get('name', '')}".strip()
                     for p in result.get("products", [])]

    user_id = user.get("id") if user else None

    # Fire-and-forget: log search + save history
    asyncio.create_task(log_search(
        query=body.query, input_type="text", user_id=user_id,
        products_found=product_names, success=True,
        cost=result.get("metadata", {}).get("total_cost", 0),
        duration_ms=duration_ms,
    ))
    if user_id:
        asyncio.create_task(save_comparison_and_track_cohort(
            full_response=result, query=body.query,
            input_type="text", user_id=user_id,
        ))
        asyncio.create_task(record_comparison(user_id, user.get("access_token", "")))

    return result


@router.get("/compare")
@limiter.limit("10/minute")
async def text_compare_get(
    request: Request,
    q: str = Query(..., max_length=500, description="Comparison query, e.g., 'iPhone 15 vs S24'"),
    region: str = Query("bahrain", description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    selected_category: Optional[str] = Query(None, description="User-selected category hint"),
    user: Optional[Dict] = Depends(get_optional_user),
):
    """GET version of text comparison for easy testing."""
    service = get_comparison_service()
    start_time = time.time()

    # Fetch user preferences if authenticated
    user_prefs = None
    if user:
        prefs_result = await get_user_preferences(user["id"])
        if prefs_result.get("success") and prefs_result.get("preferences_completed"):
            user_prefs = prefs_result.get("preferences")

    if user and not user_prefs:
        logger.warning(
            f"[PREFS] Authenticated user {user.get('id', 'unknown')} has no preferences. "
            f"prefs_result: {prefs_result}"
        )

    # Usage check for authenticated users
    if user and user.get("id"):
        usage_check = await check_usage_allowed(user["id"], user.get("access_token", ""))
        if not usage_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": f"Comparison limit reached ({usage_check['reason']})",
                    "code": "USAGE_LIMIT",
                    "tier": usage_check["tier"],
                    "remaining": usage_check["remaining"],
                }
            )

    result = await service.compare_from_text(
        query=q,
        region=region,
        include_specs=specs,
        include_reviews=reviews,
        include_pros_cons=pros_cons,
        nocache=nocache,
        selected_category=selected_category,
        user_preferences=user_prefs,
        user_id=user.get("id") if user else None,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not result.get("success"):
        asyncio.create_task(log_search(
            query=q, input_type="text",
            user_id=user.get("id") if user else None,
            success=False, error_message=result.get("error"),
            duration_ms=duration_ms,
        ))
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    product_names = [f"{p.get('brand', '')} {p.get('name', '')}".strip()
                     for p in result.get("products", [])]

    user_id = user.get("id") if user else None

    # Fire-and-forget: log search + save history
    asyncio.create_task(log_search(
        query=q, input_type="text", user_id=user_id,
        products_found=product_names, success=True,
        cost=result.get("metadata", {}).get("total_cost", 0),
        duration_ms=duration_ms,
    ))
    if user_id:
        asyncio.create_task(save_comparison_and_track_cohort(
            full_response=result, query=q,
            input_type="text", user_id=user_id,
        ))
        asyncio.create_task(record_comparison(user_id, user.get("access_token", "")))

    return result


@router.get("/compare/stream")
@limiter.limit("10/minute")
async def text_compare_stream(
    request: Request,
    q: str = Query(..., max_length=500, description="Comparison query, e.g., 'iPhone 15 vs S24'"),
    region: str = Query("bahrain", description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    selected_category: Optional[str] = Query(None, description="User-selected category hint"),
    user: Optional[Dict] = Depends(get_optional_user),
):
    """SSE streaming version of text comparison. Returns Server-Sent Events."""
    service = get_comparison_service()
    start_time = time.time()

    # Fetch user preferences if authenticated
    user_prefs = None
    if user:
        prefs_result = await get_user_preferences(user["id"])
        if prefs_result.get("success") and prefs_result.get("preferences_completed"):
            user_prefs = prefs_result.get("preferences")

    if user and not user_prefs:
        logger.warning(
            f"[PREFS] Authenticated user {user.get('id', 'unknown')} has no preferences. "
            f"prefs_result: {prefs_result}"
        )

    # Usage check for authenticated users
    if user and user.get("id"):
        usage_check = await check_usage_allowed(user["id"], user.get("access_token", ""))
        if not usage_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": f"Comparison limit reached ({usage_check['reason']})",
                    "code": "USAGE_LIMIT",
                    "tier": usage_check["tier"],
                    "remaining": usage_check["remaining"],
                }
            )

    # Bundle E Task 2.5 § Decision 8 — event-type contract documented here
    # so future readers see the wire shape without grep'ing the service.
    # The route handler is event-type-agnostic (lines below stream whatever
    # the orchestrator yields), so adding a new event type to
    # `compare_from_text_streaming()` requires no change here.
    #
    # Bundle E event types (orchestrator → client):
    #   status, specs, prices, reviews,
    #   first_paint          → "core dims ready, paint the UI"
    #   scores, verdict,
    #   settle_update        → `{field, new_value, source_rank}` (higher-trust
    #                          value arrived for a specific field; fade in)
    #   confidence_upgrade   → `{dimension_key, new_confidence}` (e.g. price
    #                          confidence promoted gray → emerald)
    #   settle_complete      → settle window closed, no more updates
    #   complete             → BACKWARD COMPAT — duplicate of settle_complete
    #                          for current EAS builds; remove in Bundle F
    #   error                → terminal failure event
    _BUNDLE_E_EVENT_TYPES = {  # noqa: F841 — kept as a doc breadcrumb
        "status", "specs", "prices", "reviews",
        "first_paint", "scores", "verdict",
        "settle_update", "confidence_upgrade",
        "settle_complete", "complete", "error",
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        complete_response = None
        had_error = False

        async for event_type, data in service.compare_from_text_streaming(
            query=q,
            region=region,
            include_specs=specs,
            include_reviews=reviews,
            include_pros_cons=pros_cons,
            nocache=nocache,
            selected_category=selected_category,
            user_preferences=user_prefs,
            user_id=user.get("id") if user else None,
        ):
            if await request.is_disconnected():
                logger.info(f"[SSE] Client disconnected during stream for query: {q}")
                return

            # `complete` is the canonical final-payload event for analytics
            # (post-stream logging below). `settle_complete` is the Bundle E
            # equivalent; both carry the same payload — favour `complete`
            # for the analytics hook so older clients still work.
            if event_type == "complete":
                complete_response = data
            if event_type == "error":
                had_error = True

            yield f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"

        # Fire-and-forget logging after stream completes
        duration_ms = int((time.time() - start_time) * 1000)
        user_id = user.get("id") if user else None

        if complete_response and not had_error:
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in complete_response.get("products", [])
            ]
            asyncio.create_task(log_search(
                query=q, input_type="text_stream", user_id=user_id,
                products_found=product_names, success=True,
                cost=complete_response.get("metadata", {}).get("total_cost", 0),
                duration_ms=duration_ms,
            ))
            if user_id:
                asyncio.create_task(save_comparison_and_track_cohort(
                    full_response=complete_response, query=q,
                    input_type="text_stream", user_id=user_id,
                ))
                asyncio.create_task(record_comparison(user_id, user.get("access_token", "")))
        elif had_error:
            asyncio.create_task(log_search(
                query=q, input_type="text_stream", user_id=user_id,
                success=False, error_message="Streaming comparison failed",
                duration_ms=duration_ms,
            ))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/quick")
@limiter.limit("10/minute")
async def quick_compare(request: Request, body: QuickCompareRequest):
    """
    Quick comparison when you already know both product names.

    Example:
    {
        "product1": "iPhone 15 Pro",
        "product2": "Samsung Galaxy S24 Ultra",
        "region": "bahrain"
    }
    """
    query = f"{body.product1} vs {body.product2}"

    service = get_comparison_service()
    result = await service.compare_from_text(
        query=query,
        region=body.region,
        include_specs=True,
        include_reviews=True,
        include_pros_cons=True
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    return result


@router.get("/prices/{product}")
@limiter.limit("20/minute")
async def get_gcc_prices(
    request: Request,
    product: str = Path(..., max_length=100),
    variant: Optional[str] = Query(None, max_length=50, description="Product variant, e.g., '256GB'")
):
    """
    Get prices for a product across all GCC regions.
    
    Example: /api/v1/text/prices/iPhone%2015%20Pro?variant=256GB
    
    Returns prices in: Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman
    """
    # Parse product string to extract brand/name
    parts = product.strip().split(" ", 1)
    if len(parts) == 1:
        brand = ""
        name = parts[0]
    else:
        # Common brand detection
        known_brands = ["apple", "samsung", "google", "sony", "lg", "huawei", "xiaomi", "oppo", "vivo", "oneplus"]
        if parts[0].lower() in known_brands:
            brand = parts[0]
            name = parts[1] if len(parts) > 1 else ""
        else:
            brand = ""
            name = product
    
    search_query = f"{brand} {name} {variant or ''}".strip()
    
    result = await get_regional_prices(brand, name, variant, search_query)
    
    return {
        "product": product,
        "variant": variant,
        "search_query": search_query,
        **result
    }


@router.delete("/cache")
async def flush_product_cache(
    q: str = Query(..., max_length=500, description="Product query, e.g., 'rtx 3090'"),
    _admin: bool = Depends(verify_admin_key),
):
    """
    Flush cached price/specs/reviews for a product.
    Useful after fixing pricing bugs to clear stale data.
    """
    from app.services.extraction_service import (
        parse_product_query, get_price_cache_key, get_specs_cache_key, get_reviews_cache_key
    )
    from app.services.cache_service import delete_cached

    parsed = await parse_product_query(q + " vs placeholder")
    products = parsed.get("products", [])
    if not products:
        return {"success": False, "error": "Could not parse product name"}

    p = products[0]
    brand, name, variant = p["brand"], p["name"], p.get("variant")

    keys = {
        "price": get_price_cache_key(brand, name, variant, "bahrain"),
        "specs": get_specs_cache_key(brand, name, variant),
        "reviews": get_reviews_cache_key(brand, name, variant),
    }

    deleted = {}
    for label, key in keys.items():
        deleted[label] = {"key": key, "deleted": delete_cached(key)}

    return {"success": True, "product": f"{brand} {name}", "flushed": deleted}


@router.get("/parse")
async def parse_query(
    q: str = Query(..., max_length=500, description="Query to parse, e.g., 'iPhone 15 vs S24'"),
    _admin: bool = Depends(verify_admin_key),
):
    """
    Debug endpoint: Parse a query without running full comparison.
    
    Returns extracted product information.
    """
    from app.services.extraction_service import parse_product_query
    
    result = await parse_product_query(q)
    return {
        "query": q,
        "parsed": result
    }

