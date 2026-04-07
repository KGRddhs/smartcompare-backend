"""
URL Comparison Routes - API endpoints for URL-based product comparisons
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from starlette.requests import Request

from app.middleware.rate_limiter import limiter
from app.utils.url_validator import validate_external_url

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
@limiter.limit("10/minute")
async def extract_product(request: Request, body: URLExtractRequest):
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
    logger.info(f"URL extraction request: {body.url}")

    if not validate_external_url(body.url):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    result = await extract_from_url(body.url)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to extract product data")
        )
    
    return result


@router.get("/extract")
@limiter.limit("10/minute")
async def extract_product_get(
    request: Request,
    url: str = Query(..., description="Product URL to extract")
):
    """GET version of extract for easy testing."""
    if not validate_external_url(url):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    result = await extract_from_url(url)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to extract product data")
        )
    
    return result


@router.post("/compare")
@limiter.limit("10/minute")
async def compare_urls(request: Request, body: URLCompareRequest):
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
    logger.info(f"URL comparison request: {body.url1} vs {body.url2}")

    if not validate_external_url(body.url1) or not validate_external_url(body.url2):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    result = await compare_from_urls(
        body.url1,
        body.url2,
        body.region
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )
    
    return result


@router.get("/compare")
@limiter.limit("10/minute")
async def compare_urls_get(
    request: Request,
    url1: str = Query(..., description="First product URL"),
    url2: str = Query(..., description="Second product URL"),
    region: str = Query("bahrain", description="Region for pricing context")
):
    """GET version of compare for easy testing."""
    if not validate_external_url(url1) or not validate_external_url(url2):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    result = await compare_from_urls(url1, url2, region)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )
    
    return result


@router.post("/detect")
@limiter.limit("20/minute")
async def detect_retailer_endpoint(request: Request, body: URLExtractRequest):
    """
    Detect retailer from URL without full extraction.

    Useful for validating URLs before processing.
    """
    if not validate_external_url(body.url):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    retailer = detect_retailer(body.url)

    return {
        "url": body.url,
        "retailer": retailer,
        "supported": retailer["key"] != "unknown"
    }


@router.get("/detect")
@limiter.limit("20/minute")
async def detect_retailer_get(
    request: Request,
    url: str = Query(..., description="URL to detect retailer")
):
    """GET version of detect for easy testing."""
    if not validate_external_url(url):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    retailer = detect_retailer(url)

    return {
        "url": url,
        "retailer": retailer,
        "supported": retailer["key"] != "unknown"
    }
