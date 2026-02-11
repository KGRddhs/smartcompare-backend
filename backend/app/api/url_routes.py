"""
URL Comparison Routes - Compare products from retailer URLs
Supports: lite, full, and v3 modes
"""
import logging
import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.url_extraction_service import (
    extract_from_url,
    detect_retailer,
    SUPPORTED_RETAILERS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/url", tags=["url-comparison"])


class URLCompareRequest(BaseModel):
    url1: str
    url2: str
    region: str = "bahrain"
    mode: str = "v3"


@router.get("/retailers")
async def list_supported_retailers():
    """List all supported retailers."""
    return {
        "retailers": [
            {
                "key": key,
                "name": info["name"],
                "region": info["region"],
                "currency": info["currency"]
            }
            for key, info in SUPPORTED_RETAILERS.items()
        ],
        "note": "Unlisted retailers will use generic extraction"
    }


@router.get("/extract")
async def extract_product_get(url: str = Query(...)):
    """Extract product info from a single URL."""
    result = await extract_from_url(url)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/compare")
async def compare_urls(request: URLCompareRequest):
    """
    Compare two products from URLs.
    
    **Modes:**
    - `v3`: Complete data with validation (recommended)
    - `lite`: Fast & cheap
    - `full`: Most detailed
    """
    return await _do_url_comparison(
        request.url1,
        request.url2,
        request.region,
        request.mode
    )


@router.get("/compare")
async def compare_urls_get(
    url1: str = Query(..., description="First product URL"),
    url2: str = Query(..., description="Second product URL"),
    region: str = Query("bahrain"),
    mode: str = Query("v3", description="'lite', 'full', or 'v3'")
):
    """GET version for easy testing."""
    return await _do_url_comparison(url1, url2, region, mode)


async def _do_url_comparison(url1: str, url2: str, region: str, mode: str):
    """Execute URL comparison."""
    start_time = time.time()
    
    try:
        # Extract both products
        import asyncio
        results = await asyncio.gather(
            extract_from_url(url1),
            extract_from_url(url2),
            return_exceptions=True
        )
        
        products = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"URL {i+1}: {str(result)}")
            elif not result.get("success"):
                errors.append(f"URL {i+1}: {result.get('error', 'Extraction failed')}")
            else:
                products.append(result["product"])
        
        if len(products) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract both products. Errors: {errors}"
            )
        
        # Compare using selected mode
        if mode == "v3":
            from app.services.comparison_service_v3 import compare_products, validate_and_fix_product
            
            # Validate products
            for i, p in enumerate(products):
                products[i] = validate_and_fix_product(
                    p, 
                    p.get("name", "Unknown"),
                    p.get("category", "electronics"),
                    region,
                    {"bahrain": "BHD", "saudi": "SAR", "uae": "AED"}.get(region, "USD"),
                    {}
                )
            
            comparison = await compare_products(products[0], products[1], region)
            
        elif mode == "lite":
            from app.services.lite_comparison_service import compare_products_lite
            comparison = await compare_products_lite(products[0], products[1])
            
        else:
            from app.services.extraction_service import generate_comparison
            comparison = await generate_comparison(products[0], products[1], region)
        
        elapsed = time.time() - start_time
        
        return {
            "success": True,
            "mode": mode,
            "products": products,
            "comparison": comparison,
            "winner_index": comparison.get("winner_index", 0),
            "winner_reason": comparison.get("winner_reason", ""),
            "recommendation": comparison.get("recommendation", ""),
            "key_differences": comparison.get("key_differences", []),
            "source_urls": [url1, url2],
            "metadata": {
                "elapsed_seconds": round(elapsed, 2),
                "mode": mode
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect")
async def detect_retailer_endpoint(url: str = Query(...)):
    """Detect retailer from URL."""
    retailer = detect_retailer(url)
    return {
        "url": url,
        "retailer": retailer,
        "supported": retailer["key"] != "unknown"
    }
