"""
API Routes - Main endpoints for SmartCompare
"""
import os
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.services.comparison_service import compare_products, quick_compare
from app.services.cache_service import (
    check_rate_limit,
    increment_user_daily_usage,
    check_monthly_budget,
    health_check as cache_health_check,
    get_user_daily_usage
)
from app.models.schemas import (
    ComparisonResponse,
    ComparisonRequest,
    ComparisonError,
    RateLimitStatus,
    CostStatus,
    SubscriptionStatus
)

router = APIRouter(prefix="/api/v1", tags=["comparisons"])


# Temporary directory for uploaded images
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)


def get_temp_user():
    """
    Temporary user for development.
    In production, this will be replaced with real auth.
    """
    return {
        "id": "dev-user-001",
        "email": "dev@smartcompare.app",
        "subscription_tier": "free"
    }


@router.post("/compare", response_model=ComparisonResponse)
async def compare_endpoint(
    images: List[UploadFile] = File(..., description="2-4 product images"),
    country: str = "Bahrain"
):
    """
    Compare 2-4 products from uploaded images.
    
    - Upload 2-4 product images (JPEG, PNG)
    - AI identifies products and finds current prices
    - Returns comparison with winner recommendation
    
    **Rate Limits:**
    - Free tier: 5 comparisons/day
    - Premium: Unlimited
    """
    
    # Get current user (dev mode)
    user = get_temp_user()
    is_premium = user["subscription_tier"] == "premium"
    
    # Check rate limit
    rate_status = check_rate_limit(user["id"], is_premium)
    if not rate_status["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily limit reached",
                "limit": rate_status["daily_limit"],
                "current": rate_status["current_usage"],
                "message": "Upgrade to Premium for unlimited comparisons"
            }
        )
    
    # Check monthly budget
    budget_status = check_monthly_budget(100.0)
    if not budget_status["allowed"]:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable due to high demand. Please try again later."
        )
    
    # Validate number of images
    if len(images) < 2:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least 2 product images"
        )
    if len(images) > 4:
        raise HTTPException(
            status_code=400,
            detail="Maximum 4 product images allowed"
        )
    
    # Validate image types
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    for img in images:
        if img.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type: {img.content_type}. Allowed: JPEG, PNG"
            )
    
    # Save images temporarily and prepare for processing
    image_data_list = []
    temp_files = []
    
    try:
        for img in images:
            # Read image bytes
            content = await img.read()
            
            # Save to temp file (for debugging/logging if needed)
            ext = ".jpg" if "jpeg" in img.content_type else ".png"
            temp_path = TEMP_DIR / f"{uuid.uuid4()}{ext}"
            temp_path.write_bytes(content)
            temp_files.append(temp_path)
            
            # Prepare image data for processing
            image_data_list.append({
                "bytes": content,
                "mime_type": img.content_type
            })
        
        # Run comparison
        result = await compare_products(image_data_list, country)
        
        # Increment usage on success
        if result.get("success"):
            increment_user_daily_usage(user["id"])
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )
    
    finally:
        # Clean up temp files
        for temp_path in temp_files:
            try:
                temp_path.unlink()
            except:
                pass


@router.post("/compare/quick", response_model=ComparisonResponse)
async def quick_compare_endpoint(
    request: ComparisonRequest
):
    """
    Quick comparison when products are already known.
    No image upload required.
    
    **Request body:**
    ```json
    {
        "products": [
            {"brand": "Nido", "name": "Full Cream Milk Powder", "size": "2.5kg"},
            {"brand": "Almarai", "name": "Milk Powder", "size": "2.5kg"}
        ],
        "country": "Bahrain"
    }
    ```
    """
    
    # Get current user (dev mode)
    user = get_temp_user()
    is_premium = user["subscription_tier"] == "premium"
    
    # Check rate limit
    rate_status = check_rate_limit(user["id"], is_premium)
    if not rate_status["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily limit reached",
                "limit": rate_status["daily_limit"],
                "current": rate_status["current_usage"],
                "message": "Upgrade to Premium for unlimited comparisons"
            }
        )
    
    if len(request.products) < 2:
        raise HTTPException(status_code=400, detail="At least 2 products required")
    
    try:
        # Convert Pydantic models to dicts
        products = [p.model_dump() for p in request.products]
        
        result = await quick_compare(
            products[0],
            products[1],
            request.country
        )
        
        # Increment usage on success
        if result.get("success"):
            increment_user_daily_usage(user["id"])
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/subscription/status", response_model=SubscriptionStatus)
async def subscription_status():
    """Get current user's subscription status and daily usage."""
    
    user = get_temp_user()
    is_premium = user["subscription_tier"] == "premium"
    daily_usage = get_user_daily_usage(user["id"])
    daily_limit = None if is_premium else 5
    
    return {
        "user_id": user["id"],
        "email": user["email"],
        "subscription_tier": user["subscription_tier"],
        "daily_usage": daily_usage,
        "daily_limit": daily_limit,
        "remaining_comparisons": None if is_premium else max(0, 5 - daily_usage)
    }


@router.get("/rate-limit/status", response_model=RateLimitStatus)
async def rate_limit_status():
    """Check current rate limit status."""
    
    user = get_temp_user()
    is_premium = user["subscription_tier"] == "premium"
    
    return check_rate_limit(user["id"], is_premium)


@router.get("/cost/status", response_model=CostStatus)
async def cost_status():
    """Get current monthly API cost status (admin endpoint)."""
    
    return check_monthly_budget(100.0)


@router.get("/health/services")
async def services_health():
    """Detailed health check for all services."""
    
    # Check cache/Redis
    cache_status = cache_health_check()
    
    # Check OpenAI (simple validation)
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_status = "configured" if openai_key.startswith("sk-") else "not configured"
    
    # Check Serper
    serper_key = os.getenv("SERPER_API_KEY", "")
    serper_status = "configured" if serper_key else "not configured"
    
    return {
        "status": "healthy" if cache_status["status"] == "healthy" else "degraded",
        "services": {
            "cache": cache_status,
            "openai": {"status": openai_status},
            "serper": {"status": serper_status}
        }
    }
