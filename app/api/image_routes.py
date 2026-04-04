"""
Image Comparison Routes - Camera/photo-based product identification and comparison

Endpoints:
  POST /api/v1/image/identify  — Identify products from 1-4 images
    - 1 product found: returns product info, frontend asks for second
    - 2+ products found: auto-runs full comparison via structured_comparison_service
"""
import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Request

from app.services.openai_service import identify_products
from app.services.structured_comparison_service import StructuredComparisonService
from app.api.auth_routes import get_optional_user
from app.services.database_service import log_search, save_comparison
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

# Supported image MIME types for OpenAI Vision
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _detect_mime_type(content: bytes, fallback: str = "image/jpeg") -> str:
    """Detect image MIME type from magic bytes."""
    if len(content) >= 2 and content[:2] == b"\xff\xd8":
        return "image/jpeg"
    if len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if len(content) >= 6 and content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    # HEIC/HEIF detection: ftyp box with heic/heix/hevc/mif1 brand
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"mif1"):
            return "image/heic"
    return fallback


router = APIRouter(prefix="/api/v1/image", tags=["image-comparison"])

# Temp dir for uploaded images (cleaned up after each request)
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)


@router.post("/identify")
@limiter.limit("10/minute")
async def identify_and_compare(
    request: Request,
    images: List[UploadFile] = File(..., description="1-4 product images"),
    region: str = Query("bahrain", description="Region for price search"),
    nocache: bool = Query(False, description="Bypass price/spec cache"),
    user: Optional[Dict] = Depends(get_optional_user),
):
    """
    Identify products from uploaded images, then compare if 2+ found.

    Returns one of:
      - action="need_second_product" + products[] (1 product identified)
      - action="comparison" + full ComparisonResult (2+ products identified)
      - action="error" (0 products or processing failure)
    """
    logger.info(f"[IMAGE] Received {len(images)} image(s) for identification")
    start_time = time.time()

    # Validate image count
    if len(images) < 1:
        raise HTTPException(status_code=400, detail="At least 1 image is required.")
    if len(images) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 images allowed.")

    # Read and validate images
    image_data_list = []
    for i, img in enumerate(images):
        content = await img.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"Image {i+1} is empty.")
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Image {i+1} exceeds 10MB limit.")

        # Detect MIME type from magic bytes, fall back to upload header
        content_type = _detect_mime_type(content, img.content_type or "image/jpeg")

        if content_type not in SUPPORTED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Image {i+1} has unsupported format ({content_type}). "
                       f"Please use JPEG, PNG, WebP, or GIF."
            )

        image_data_list.append({"bytes": content, "mime_type": content_type})
        logger.info(f"[IMAGE]   Image {i+1}: {len(content)} bytes, {content_type}")

    # Step 1: Vision identification (single GPT call for all images)
    try:
        vision_result = await identify_products(image_data_list)
    except Exception as e:
        logger.error(f"[IMAGE] Vision call failed: {e}")
        raise HTTPException(status_code=500, detail="Image analysis failed. Please try again.")

    if vision_result.get("error"):
        logger.error(f"[IMAGE] Vision parse error: {vision_result['error']}")
        if vision_result.get("raw_response"):
            logger.debug(f"[IMAGE] Raw response (server-only): {vision_result['raw_response']}")
        return {
            "success": False,
            "action": "error",
            "error": "Could not identify products in the image. Please try a clearer photo.",
            "vision_cost": vision_result.get("cost", 0),
        }

    products = vision_result.get("products", [])
    vision_cost = vision_result.get("cost", 0)

    # Enrich product name with size_or_count if vision detected it
    # e.g., name="Vitamin D-3" + size_or_count="360 Softgels" → name="Vitamin D-3 360 Softgels"
    for p in products:
        size_or_count = p.get("size_or_count")
        if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
            p["name"] = f"{p['name']} {size_or_count}".strip()

    product_names = [f"{p.get('brand', '')} {p.get('name', '')}" for p in products]
    logger.info(f"[IMAGE] Identified {len(products)} product(s): {product_names}")

    # --- 0 products ---
    if len(products) == 0:
        return {
            "success": False,
            "action": "error",
            "error": "No products could be identified in the image(s). Try a clearer photo.",
            "vision_cost": vision_cost,
        }

    # --- 1 product ---
    if len(products) == 1:
        product = products[0]
        return {
            "success": True,
            "action": "need_second_product",
            "products": products,
            "message": f"Identified: {product['brand']} {product['name']}. "
                       f"Take another photo or type a product to compare with.",
            "vision_cost": vision_cost,
        }

    # --- 2+ products: auto-compare ---
    p1 = products[0]
    p2 = products[1]
    query = f"{p1['brand']} {p1['name']} vs {p2['brand']} {p2['name']}"
    logger.info(f"[IMAGE] Auto-comparing: {query}")

    try:
        service = StructuredComparisonService()
        result = await service.compare_from_text(query, region=region, vision_products=products, nocache=nocache)

        # Inject vision metadata
        if result.get("metadata"):
            result["metadata"]["input_method"] = "camera"
            result["metadata"]["vision_cost"] = vision_cost
            result["metadata"]["total_cost"] = round(
                result["metadata"].get("total_cost", 0) + vision_cost, 6
            )
            result["metadata"]["identified_products"] = products
        else:
            result["metadata"] = {
                "input_method": "camera",
                "vision_cost": vision_cost,
                "identified_products": products,
            }

        result["action"] = "comparison"

        duration_ms = int((time.time() - start_time) * 1000)
        user_id = user.get("id") if user else None

        # Fire-and-forget: log search + save history
        asyncio.create_task(log_search(
            query=query, input_type="camera", user_id=user_id,
            products_found=product_names, success=True,
            cost=result.get("metadata", {}).get("total_cost", 0),
            duration_ms=duration_ms,
        ))
        if user_id:
            asyncio.create_task(save_comparison(
                full_response=result, query=query,
                input_type="camera", user_id=user_id,
            ))

        return result

    except Exception as e:
        logger.error(f"[IMAGE] Comparison failed after identification: {e}", exc_info=True)

        duration_ms = int((time.time() - start_time) * 1000)
        asyncio.create_task(log_search(
            query=query, input_type="camera",
            user_id=user.get("id") if user else None,
            products_found=product_names, success=False,
            error_message=str(e), duration_ms=duration_ms,
        ))

        # Still return the identified products so frontend can fall back to text compare
        return {
            "success": False,
            "action": "comparison_failed",
            "error": str(e),
            "products": products,
            "vision_cost": vision_cost,
            "message": "Products identified but comparison failed. You can compare them via text.",
        }
