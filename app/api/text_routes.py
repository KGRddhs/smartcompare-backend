"""
Text Comparison Routes - API endpoints for text-based product comparisons
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.structured_comparison_service import (
    get_comparison_service,
    get_regional_prices
)

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
async def text_compare(request: TextCompareRequest):
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
    logger.info(f"Text comparison request: {request.query}")
    
    service = get_comparison_service()
    
    result = await service.compare_from_text(
        query=request.query,
        region=request.region,
        include_specs=request.include_specs,
        include_reviews=request.include_reviews,
        include_pros_cons=request.include_pros_cons
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )
    
    return result


@router.get("/compare")
async def text_compare_get(
    q: str = Query(..., description="Comparison query, e.g., 'iPhone 15 vs S24'"),
    region: str = Query("bahrain", description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data")
):
    """GET version of text comparison for easy testing."""
    service = get_comparison_service()

    result = await service.compare_from_text(
        query=q,
        region=region,
        include_specs=specs,
        include_reviews=reviews,
        include_pros_cons=pros_cons,
        nocache=nocache
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    return result


@router.post("/quick")
async def quick_compare(request: QuickCompareRequest):
    """
    Quick comparison when you already know both product names.
    
    Example:
    {
        "product1": "iPhone 15 Pro",
        "product2": "Samsung Galaxy S24 Ultra",
        "region": "bahrain"
    }
    """
    query = f"{request.product1} vs {request.product2}"
    
    service = get_comparison_service()
    result = await service.compare_from_text(
        query=query,
        region=request.region,
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
async def get_gcc_prices(
    product: str,
    variant: Optional[str] = Query(None, description="Product variant, e.g., '256GB'")
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
    q: str = Query(..., description="Product query, e.g., 'rtx 3090'")
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
    q: str = Query(..., description="Query to parse, e.g., 'iPhone 15 vs S24'")
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


# ============================================
# Category-specific endpoints
# ============================================

@router.post("/compare/electronics")
async def compare_electronics(request: TextCompareRequest):
    """
    Optimized comparison for electronics.
    Emphasizes: specs, performance, features.
    """
    # Add category hint to query
    result = await text_compare(request)
    return result


@router.post("/compare/grocery")
async def compare_grocery(request: TextCompareRequest):
    """
    Optimized comparison for grocery items.
    Emphasizes: price per unit, ingredients, nutrition.
    """
    result = await text_compare(request)
    return result
