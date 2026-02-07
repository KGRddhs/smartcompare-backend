"""
API Routes - Main endpoints for SmartCompare (with database integration)
"""
import os
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.services.comparison_service import compare_products, quick_compare
from app.services.cache_service import (
    check_rate_limit,
    increment_user_daily_usage,
    check_monthly_budget,
    health_check as cache_health_check,
    get_user_daily_usage
)
from app.services.database_service import (
    save_comparison,
    get_user_comparisons,
    get_comparison_by_id,
    get_user_comparison_count,
    health_check as db_health_check,
    create_user,
    get_user_by_email
)
from app.models.schemas import (
    ComparisonResponse,
    ComparisonRequest,
    ComparisonError,
    RateLimitStatus,
    CostStatus,
    SubscriptionStatus,
    ComparisonHistoryResponse,
    ComparisonHistoryItem
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["comparisons"])

# Temporary directory for uploaded images
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

# Dev user ID (will be replaced with real auth later)
DEV_USER_ID = None


async def get_or_create_dev_user():
    """
    Get or create a development user.
    In production, this will be replaced with real JWT auth.
    """
    global DEV_USER_ID
    
    if DEV_USER_ID:
        return {
            "id": DEV_USER_ID,
            "email": "dev@smartcompare.app",
            "subscription_tier": "free"
        }
    
    # Try to get existing dev user
    dev_email = "dev@smartcompare.app"
    user = await get_user_by_email(dev_email)
    
    if user:
        DEV_USER_ID = user["id"]
        return user
    
    # Create dev user
    user = await create_user(dev_email, "free")
    if user:
        DEV_USER_ID = user["id"]
        return user
    
    # Fallback if DB fails
    return {
        "id": "dev-user-fallback",
        "email": dev_email,
        "subscription_tier": "free"
    }


@router.post("/compare", response_model=ComparisonResponse)
async def compare_endpoint(
    images: List[UploadFile] = File(..., description="2-4 product images"),
    country: str = Query("Bahrain", description="Country for price search")
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
    
    logger.info(f"Received comparison request with {len(images)} images")
    
    # Get current user
    user = await get_or_create_dev_user()
    is_premium = user["subscription_tier"] == "premium"
    
    # Check rate limit
    rate_status = check_rate_limit(user["id"], is_premium)
    if not rate_status["allowed"]:
        logger.warning(f"Rate limit exceeded for user {user['id']}")
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
        logger.error("Monthly budget exceeded!")
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
    
    # Prepare images for processing
    image_data_list = []
    temp_files = []
    
    try:
        for img in images:
            # Read image bytes
            content = await img.read()
            
            # Validate image size (max 10MB)
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image too large: {img.filename}. Maximum size is 10MB."
                )
            
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
            
            logger.info(f"Processed image: {img.filename} ({len(content)} bytes)")
        
        # Run comparison
        logger.info("Starting AI comparison...")
        result = await compare_products(image_data_list, country)
        
        if result.get("success"):
            # Increment usage
            increment_user_daily_usage(user["id"])
            
            # Save to database
            try:
                saved = await save_comparison(
                    user_id=user["id"],
                    products=result["products"],
                    winner_index=result["winner_index"],
                    recommendation=result["recommendation"],
                    key_differences=result["key_differences"],
                    data_source=result["data_freshness"],
                    total_cost=result["total_cost"]
                )
                if saved:
                    logger.info(f"Comparison saved with ID: {saved['id']}")
            except Exception as e:
                logger.error(f"Failed to save comparison to DB: {e}")
            
            logger.info(f"Comparison successful. Winner: Product {result['winner_index'] + 1}, Cost: ${result['total_cost']:.6f}")
        else:
            logger.error(f"Comparison failed: {result.get('error')}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in comparison: {e}")
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
async def quick_compare_endpoint(request: ComparisonRequest):
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
    
    logger.info(f"Quick comparison request: {len(request.products)} products")
    
    # Get current user
    user = await get_or_create_dev_user()
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
        
        if result.get("success"):
            # Increment usage
            increment_user_daily_usage(user["id"])
            
            # Save to database
            try:
                await save_comparison(
                    user_id=user["id"],
                    products=result["products"],
                    winner_index=result["winner_index"],
                    recommendation=result["recommendation"],
                    key_differences=result["key_differences"],
                    data_source=result["data_freshness"],
                    total_cost=result["total_cost"]
                )
            except Exception as e:
                logger.error(f"Failed to save comparison: {e}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick comparison error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/comparisons/history", response_model=ComparisonHistoryResponse)
async def comparison_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's comparison history"""
    
    user = await get_or_create_dev_user()
    
    comparisons = await get_user_comparisons(user["id"], limit, offset)
    total = await get_user_comparison_count(user["id"])
    
    return {
        "comparisons": comparisons,
        "total": total,
        "page": (offset // limit) + 1,
        "per_page": limit
    }


@router.get("/comparisons/{comparison_id}")
async def get_comparison(comparison_id: str):
    """Get a specific comparison by ID"""
    
    comparison = await get_comparison_by_id(comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    return comparison


@router.get("/subscription/status", response_model=SubscriptionStatus)
async def subscription_status():
    """Get current user's subscription status and daily usage."""
    
    user = await get_or_create_dev_user()
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
    
    user = await get_or_create_dev_user()
    is_premium = user["subscription_tier"] == "premium"
    
    return check_rate_limit(user["id"], is_premium)


@router.get("/cost/status", response_model=CostStatus)
async def cost_status():
    """Get current monthly API cost status."""
    
    return check_monthly_budget(100.0)


@router.get("/health/services")
async def services_health():
    """Detailed health check for all services."""
    
    # Check cache/Redis
    cache_status = cache_health_check()
    
    # Check database
    db_status = await db_health_check()
    
    # Check OpenAI (simple validation)
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_status = "configured" if openai_key.startswith("sk-") else "not configured"
    
    # Check Serper
    serper_key = os.getenv("SERPER_API_KEY", "")
    serper_status = "configured" if serper_key else "not configured"
    
    overall = "healthy"
    if cache_status["status"] != "healthy" or db_status["status"] != "healthy":
        overall = "degraded"
    
    return {
        "status": overall,
        "services": {
            "database": db_status,
            "cache": cache_status,
            "openai": {"status": openai_status},
            "serper": {"status": serper_status}
        }
    }
