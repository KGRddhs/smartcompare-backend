"""
URL Comparison Routes - API endpoints for URL-based product comparisons
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.services.url_extraction_service import (
    extract_from_url,
    compare_from_urls,
    detect_retailer,
    SUPPORTED_RETAILERS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/url", tags=["url-comparison"])


# ============================================
# Request/Response Models
# ============================================

class URLExtractRequest(BaseModel):
    """Request to extract product from URL"""
    url: str


class URLCompareRequest(BaseModel):
    """Request to compare products from URLs"""
    url1: str
    url2: str
    region: str = "bahrain"


class MultiURLCompareRequest(BaseModel):
    """Request to compare multiple products from URLs"""
    urls: List[str]
    region: str = "bahrain"


# ============================================
# Endpoints
# ============================================

@router.get("/retailers")
async def list_supported_retailers():
    """
    List all supported retailers for URL extraction.
    
    Returns retailers with their domains, regions, and currencies.
    """
    return {
        "retailers": [
            {
                "key": key,
                "name": info["name"],
                "region": info["region"],
                "currency": info["currency"],
                "example_domains": [key]
            }
            for key, info in SUPPORTED_RETAILERS.items()
        ],
        "note": "URLs from unlisted retailers will still be processed using generic extraction."
    }


@router.post("/extract")
async def extract_product(request: URLExtractRequest):
    """
    Extract product information from a single URL.
    
    Supports major GCC retailers:
    - Amazon (amazon.ae, amazon.sa)
    - Noon (noon.com)
    - Carrefour
    - Sharaf DG
    - Lulu Hypermarket
    - And more...
    
    Returns structured product data including:
    - Brand, name, variant
    - Price and currency
    - Specifications
    - Reviews/ratings
    - Images
    """
    logger.info(f"URL extraction request: {request.url}")
    
    result = await extract_from_url(request.url)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to extract product data")
        )
    
    return result


@router.get("/extract")
async def extract_product_get(
    url: str = Query(..., description="Product URL to extract")
):
    """GET version of extract for easy testing."""
    result = await extract_from_url(url)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to extract product data")
        )
    
    return result


@router.post("/compare")
async def compare_urls(request: URLCompareRequest):
    """
    Compare two products from their URLs.
    
    Example:
    {
        "url1": "https://amazon.ae/dp/B0CHX1W1XY",
        "url2": "https://noon.com/uae-en/samsung-galaxy-s24/N123456",
        "region": "bahrain"
    }
    
    Returns full comparison with:
    - Extracted product data for both
    - Price comparison
    - Specs comparison
    - Winner recommendation
    - Key differences
    """
    logger.info(f"URL comparison request: {request.url1} vs {request.url2}")
    
    result = await compare_from_urls(
        request.url1,
        request.url2,
        request.region
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )
    
    return result


@router.get("/compare")
async def compare_urls_get(
    url1: str = Query(..., description="First product URL"),
    url2: str = Query(..., description="Second product URL"),
    region: str = Query("bahrain", description="Region for pricing context")
):
    """GET version of compare for easy testing."""
    result = await compare_from_urls(url1, url2, region)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )
    
    return result


@router.post("/detect")
async def detect_retailer_endpoint(request: URLExtractRequest):
    """
    Detect retailer from URL without full extraction.
    
    Useful for validating URLs before processing.
    """
    retailer = detect_retailer(request.url)
    
    return {
        "url": request.url,
        "retailer": retailer,
        "supported": retailer["key"] != "unknown"
    }


@router.get("/detect")
async def detect_retailer_get(
    url: str = Query(..., description="URL to detect retailer")
):
    """GET version of detect for easy testing."""
    retailer = detect_retailer(url)
    
    return {
        "url": url,
        "retailer": retailer,
        "supported": retailer["key"] != "unknown"
    }


# ============================================
# Multi-product comparison (future)
# ============================================

@router.post("/compare/multi")
async def compare_multiple_urls(request: MultiURLCompareRequest):
    """
    Compare multiple products from URLs (2-4 products).
    
    Example:
    {
        "urls": [
            "https://amazon.ae/dp/product1",
            "https://noon.com/product2",
            "https://sharafdg.com/product3"
        ],
        "region": "bahrain"
    }
    """
    if len(request.urls) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 URLs required for comparison"
        )
    
    if len(request.urls) > 4:
        raise HTTPException(
            status_code=400,
            detail="Maximum 4 URLs allowed for comparison"
        )
    
    # For now, just compare first two
    # TODO: Implement multi-product comparison
    result = await compare_from_urls(
        request.urls[0],
        request.urls[1],
        request.region
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )
    
    return result
