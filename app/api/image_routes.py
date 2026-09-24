"""
Image Comparison Routes - Camera/photo-based product identification and comparison

Endpoints:
  POST /api/v1/image/identify  — Identify products from 1-4 images
    - 1 product found: returns product info, frontend asks for second
    - 2+ products found: auto-runs full comparison via structured_comparison_service
"""
import hashlib
import logging
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Request

from app.services.openai_service import identify_products
from app.services.structured_comparison_service import StructuredComparisonService
from app.api.auth_routes import get_optional_user
from app.services.database_service import log_search, save_comparison
from app.services.feedback_service import save_comparison_and_track_cohort
from app.middleware.rate_limiter import limiter
from app.services.usage_service import (
    anon_usage_gate_enabled,
    valid_device_fingerprint,
    check_anon_usage_allowed,
    record_anon_comparison,
    consume_comparison_credit,
    refund_comparison_credit,
    refund_anon_comparison_credit,
    record_lifetime_comparison,
)
# W2-1: ONE definition of the flag for the whole unit (see the helper's
# docstring). image_routes/url_routes deliberately do not re-parse the env.
from app.api.text_routes import paid_route_metering_enabled
from app.utils.async_utils import fire_and_forget

logger = logging.getLogger(__name__)

# R-METER (W2-1b, M13-26 class, UNFLAGGED): the ONLY value the camera route
# ever sends in place of a code-less unsuccessful comparison's `error`.
# compare_from_text's generic except-branch returns `{success: False,
# error: str(e)}`, and str(e) of an OpenAI client error carries the masked key
# tail, org and quota text -- so that string must never reach the client.
CAMERA_UNSUCCESSFUL_CONSTANT_ERROR = "comparison unavailable"


def camera_failure_envelope_enabled() -> bool:
    """True iff an UNSUCCESSFUL camera comparison is served as a failure
    envelope instead of today's `action: "comparison"` body
    (R-METER W2-1b, `ENABLE_CAMERA_FAILURE_ENVELOPE`, default OFF).

    Flag OFF: the pre-OTA client (97b5f15) keeps receiving exactly today's
    body for a `success: False` result -- the result dict plus the camera
    metadata and `action: "comparison"` (only a code-less result's `error`
    value is replaced, unflagged, by `CAMERA_UNSUCCESSFUL_CONSTANT_ERROR`).
    Flag ON: the route returns the same `action: "comparison_failed"`
    envelope exit 6 already ships (so the client's existing
    fall-back-to-text branch handles it), carrying the result's own `code`.

    Read PER CALL from `os.getenv` so Railway flips it without a restart.
    """
    return os.getenv("ENABLE_CAMERA_FAILURE_ENVELOPE", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _camera_failure_envelope(result: Dict, request: Request, products: list,
                             vision_cost) -> Dict:
    """The body an UNSUCCESSFUL comparison gets under
    ENABLE_CAMERA_FAILURE_ENVELOPE: exit 6's `comparison_failed` shape (the
    client already branches on it and falls back to text compare), carrying
    the result's own `code` -- INTERNAL_ERROR for a code-less failure, whose
    `error` is the constant, never str(e)."""
    code = result.get("code")
    envelope = {
        "success": False,
        "action": "comparison_failed",
        "error": result.get("error") if code else CAMERA_UNSUCCESSFUL_CONSTANT_ERROR,
        "code": code or "INTERNAL_ERROR",
        "request_id": getattr(request.state, "request_id", "unknown"),
        "products": products,
        "vision_cost": vision_cost,
        "message": "Products identified but comparison failed. You can compare them via text.",
    }
    if result.get("layer"):
        envelope["layer"] = result["layer"]
    return envelope

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

    # M13-03: anonymous freemium gate (dark, ENABLE_ANON_USAGE_GATE default OFF).
    # /image/identify runs a paid Vision call + a full comparison for anonymous
    # callers with no tier check. With the flag ON we meter anonymous callers by
    # their (regex-validated) X-Device-Fingerprint before the Vision call.
    # Flag-OFF (or an authenticated caller) leaves device_fp None -> byte-identical.
    device_fp = None
    # R-METER (W2-1d): True only when the anon gate actually DEBITED a credit
    # AND ENABLE_PAID_ROUTE_METERING is ON -- then each non-delivery exit
    # below gives it back via `_refund_anon_credit`. Metering OFF keeps today's
    # anon accounting exactly (debit at the gate, no refund anywhere).
    anon_credit_refundable = False
    anon_consumed_keys = None
    if anon_usage_gate_enabled() and not user:
        device_fp = valid_device_fingerprint(request.headers.get("x-device-fingerprint"))
        if device_fp:
            usage_check = await check_anon_usage_allowed(device_fp)
            if not usage_check["allowed"]:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": f"Comparison limit reached ({usage_check['reason']})",
                        "code": "USAGE_LIMIT",
                        "tier": usage_check["tier"],
                        "remaining": usage_check["remaining"],
                    },
                )
            if paid_route_metering_enabled() and usage_check.get("consumed", False):
                anon_credit_refundable = True
                anon_consumed_keys = usage_check.get("consumed_keys")

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

    # W2-1 (MB-RECONCILE-01): the AUTHENTICATED freemium gate, mirroring
    # `text_routes.text_compare` (`:193`). This route runs a paid GPT-4o Vision
    # call AND a full comparison for a signed-in user with NO tier check at all
    # -- the M13-03 anon gate above is a different, default-OFF,
    # fingerprint-keyed path that explicitly no-ops when `user` is truthy.
    #
    # Placed AFTER image validation and BEFORE the Vision call: the five 400s
    # above are pre-gate (nothing reserved, nothing to refund), and everything
    # paid is below. Flag OFF: `consume_comparison_credit` is never called and
    # `_refund_reserved_credit` is a no-op, so the route is byte-identical.
    usage_user_id = user.get("id") if user else None
    usage_consumed = False
    _refund_state = {"done": False}

    def _refund_reserved_credit(label: str) -> None:
        """Give the gate-reserved credit back, AT MOST ONCE per request.

        The double-charge trap this closes: the routine "one bottle in frame"
        exit and the two "bad photo" exits are the ones a real user hits, so a
        MISSING refund burns a free comparison for no product -- while a refund
        that fires twice on one request silently grants a credit. The
        `_refund_state` latch makes the second call a no-op, so every exit can
        refund unconditionally without auditing what ran before it.
        """
        if not usage_consumed or not usage_user_id or _refund_state["done"]:
            return
        _refund_state["done"] = True
        fire_and_forget(refund_comparison_credit(usage_user_id), label=label)

    _anon_refund_state = {"done": False}

    def _refund_anon_credit(label: str) -> None:
        """R-METER (W2-1d): give the ANON gate's debited credit back, at most
        once per request, on a non-delivery exit. `refund_anon_comparison_credit`
        had no caller at all, so under ENABLE_PAID_ROUTE_METERING every failed
        anonymous camera attempt burned a free credit for nothing. Only armed
        when the gate debited AND metering is ON (`anon_credit_refundable`).

        Deliberately NOT wired (recorded follow-ups for issue #128): the five
        image-validation 400s above -- the anon debit happens BEFORE them -- and
        the moderation-exception re-raise.
        """
        if not anon_credit_refundable or not device_fp or _anon_refund_state["done"]:
            return
        _anon_refund_state["done"] = True
        fire_and_forget(
            refund_anon_comparison_credit(device_fp, anon_consumed_keys), label=label
        )

    if paid_route_metering_enabled() and usage_user_id:
        usage_check = await consume_comparison_credit(
            usage_user_id, user.get("access_token", "")
        )
        if not usage_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": f"Comparison limit reached ({usage_check['reason']})",
                    "code": "USAGE_LIMIT",
                    "tier": usage_check["tier"],
                    "remaining": usage_check["remaining"],
                },
            )
        usage_consumed = usage_check.get("consumed", False)

    # Step 1: Vision identification (single GPT call for all images)
    try:
        vision_result = await identify_products(image_data_list)
    except Exception as e:
        logger.error(f"[IMAGE] Vision call failed: {e}")
        # Non-delivery exit 1 of 6.
        _refund_reserved_credit("usage_refund.image.vision_exception")
        _refund_anon_credit("usage_refund.image.anon.vision_exception")
        raise HTTPException(status_code=500, detail="Image analysis failed. Please try again.")

    if vision_result.get("error"):
        logger.error(f"[IMAGE] Vision parse error: {vision_result['error']}")
        if vision_result.get("raw_response"):
            logger.debug(f"[IMAGE] Raw response (server-only): {vision_result['raw_response']}")
        # Non-delivery exit 2 of 6.
        _refund_reserved_credit("usage_refund.image.vision_parse_error")
        _refund_anon_credit("usage_refund.image.anon.vision_parse_error")
        return {
            "success": False,
            "action": "error",
            "error": "Could not identify products in the image. Please try a clearer photo.",
            "vision_cost": vision_result.get("cost", 0),
        }

    # L4 content safety — moderate vision output BEFORE compare flow. If a
    # vision-identified product trips moderation (weapons / adult / etc),
    # return the existing graceful 'need_second_product' shape so the frontend
    # renders "Sharper match coming up" copy. Failing open on moderation API
    # exception per Build Principle #4.
    # Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md sec 5.2.
    import hashlib as _hashlib
    from app.services.content_safety_service import get_content_safety_service
    from app.services.audit_service import log_content_blocked

    _safety = get_content_safety_service()
    # W2-1: this is the ONE external call in the window between the vision
    # try/except above and the comparison try/except below, so before the gate
    # existed nothing here could cost anything. Now a raise would leave the
    # gate-reserved credit consumed with no product delivered, so refund and
    # re-raise -- `_refund_reserved_credit` is latched, so this can never
    # double-refund alongside the exits that follow. (Residual, deliberate and
    # narrow: a raise in the PURE-PYTHON parsing between here and the next try
    # is not covered; closing that needs a ~170-line re-indent of a live route,
    # which is not worth the regression risk inside a clean comm gate.)
    try:
        _l4 = await _safety.moderate_vision_output(vision_result)
    except Exception:
        _refund_reserved_credit("usage_refund.image.moderation_exception")
        raise
    if not _l4.allowed:
        _hash_input = " ".join(
            f"{p.get('brand', '')} {p.get('name', '')}".strip()
            for p in vision_result.get("products", [])
        )
        # Bundle D 2.B.6 WRAP: content-safety audit; silent fail = compliance gap.
        fire_and_forget(
            log_content_blocked(
                layer="vision_moderation",
                query_hash=_hashlib.sha256(_hash_input.encode("utf-8")).hexdigest(),
            ),
            label="audit.vision_moderation_blocked",
        )
        # Non-delivery exit 3 of 6.
        _refund_reserved_credit("usage_refund.image.moderation_blocked")
        _refund_anon_credit("usage_refund.image.anon.moderation_blocked")
        return {
            "success": False,
            "action": "need_second_product",
            "products": [],
            "message": "Sharper match coming up — try a clearer photo or a different product.",
            "vision_cost": vision_result.get("cost", 0),
            "code": "CONTENT_UNAVAILABLE",
            "layer": "vision_moderation",
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
        # Non-delivery exit 4 of 6.
        _refund_reserved_credit("usage_refund.image.zero_products")
        _refund_anon_credit("usage_refund.image.anon.zero_products")
        return {
            "success": False,
            "action": "error",
            "error": "No products could be identified in the image(s). Try a clearer photo.",
            "vision_cost": vision_cost,
        }

    # --- 1 product ---
    if len(products) == 1:
        product = products[0]
        # Non-delivery exit 5 of 6 -- and the one an ordinary user hits most
        # often, so the refund here is what keeps a single-bottle photo free.
        _refund_reserved_credit("usage_refund.image.need_second_product")
        _refund_anon_credit("usage_refund.image.anon.need_second_product")
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
    query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
    logger.info(f"[IMAGE] Auto-comparing: query_hash={query_hash} length={len(query)}")

    try:
        service = StructuredComparisonService()
        result = await service.compare_from_text(query, region=region, vision_products=products, nocache=nocache)

        # R-METER (W2-1b): compare_from_text mostly RETURNS its failures
        # (`success: False` + TIMEOUT / INSUFFICIENT_DATA / LLM_UNAVAILABLE /
        # CONTENT_UNAVAILABLE, or the code-less generic except-branch) instead
        # of raising, and this route never read `success` -- it served every
        # one of them as a delivered comparison.
        comparison_unsuccessful = not result.get("success")
        if comparison_unsuccessful and not result.get("code") and "error" in result:
            # UNFLAGGED (M13-26 class): a code-less failure's `error` is the
            # service's str(e) -- measured carrying an OpenAI key tail. Only
            # that one value changes; every other key is untouched.
            result["error"] = CAMERA_UNSUCCESSFUL_CONSTANT_ERROR
        # Under ENABLE_PAID_ROUTE_METERING an unsuccessful result is a
        # NON-delivery: refund, no lifetime bump, no history row, failure log.
        unsuccessful_not_billed = (
            comparison_unsuccessful and paid_route_metering_enabled()
        )

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

        if unsuccessful_not_billed:
            # Non-delivery exit 7 (R-METER W2-1b): the comparison ran and
            # returned a failure. The body is still decided by the envelope
            # flag below, so metering ON alone moves the accounting only.
            fire_and_forget(
                log_search(
                    query=query, input_type="camera", user_id=user_id,
                    products_found=product_names, success=False,
                    error_message=result.get("code") or CAMERA_UNSUCCESSFUL_CONSTANT_ERROR,
                    cost=result.get("metadata", {}).get("total_cost", 0),
                    duration_ms=duration_ms,
                ),
                label="log_search.camera.unsuccessful",
            )
            _refund_reserved_credit("usage_refund.image.comparison_unsuccessful")
            _refund_anon_credit("usage_refund.image.anon.comparison_unsuccessful")
            if camera_failure_envelope_enabled():
                return _camera_failure_envelope(result, request, products, vision_cost)
            return result

        # Fire-and-forget: log search + save history — Bundle D 2.B.6 WRAP
        # (search-log fail = lost analytics; save-comparison fail = missing
        # history row for the user).
        fire_and_forget(
            log_search(
                query=query, input_type="camera", user_id=user_id,
                products_found=product_names, success=True,
                cost=result.get("metadata", {}).get("total_cost", 0),
                duration_ms=duration_ms,
            ),
            label="log_search.camera.success",
        )
        if user_id:
            fire_and_forget(
                save_comparison_and_track_cohort(
                    full_response=result, query=query,
                    input_type="camera", user_id=user_id,
                ),
                label="save_comparison.camera",
            )
            # W2-1: the DELIVERY exit -- the one path that keeps the credit and
            # must never refund. The daily+monthly credit was reserved
            # atomically at the gate; only the Supabase lifetime counter is
            # left, exactly as `text_compare` does it.
            if usage_consumed:
                fire_and_forget(
                    record_lifetime_comparison(user_id, user.get("access_token", "")),
                    label="record_lifetime.image",
                )

        # M13-03: meter the anonymous device only when a real comparison ran.
        if device_fp:
            fire_and_forget(record_anon_comparison(device_fp), label="record_anon.image")

        if comparison_unsuccessful and camera_failure_envelope_enabled():
            # Metering OFF, envelope ON: the body says what happened; the
            # accounting above is today's (history + success log) by design --
            # the no-bill half belongs to ENABLE_PAID_ROUTE_METERING.
            return _camera_failure_envelope(result, request, products, vision_cost)
        return result

    except Exception as e:
        logger.error(f"[IMAGE] Comparison failed after identification: {e}", exc_info=True)

        duration_ms = int((time.time() - start_time) * 1000)
        # Bundle D 2.B.6 WRAP: failure-path log is doubly important; silent
        # fail here = no record of why the camera flow crashed.
        fire_and_forget(
            log_search(
                query=query, input_type="camera",
                user_id=user.get("id") if user else None,
                products_found=product_names, success=False,
                error_message=str(e), duration_ms=duration_ms,
            ),
            label="log_search.camera.failure",
        )

        # Non-delivery exit 6 of 6.
        _refund_reserved_credit("usage_refund.image.comparison_failed")
        _refund_anon_credit("usage_refund.image.anon.comparison_failed")

        # M13-26: never surface str(e) to the client — it embeds hostnames, table
        # names, Postgres codes and upstream URLs. Return the unified error
        # envelope (constant message + code + request_id), keeping str(e) only in
        # the log/Sentry path above and the fire-and-forget log_search error. The
        # action + products keys stay so the frontend can still fall back to text
        # compare (mirrors _surface_comparison_failure in text_routes.py).
        return {
            "success": False,
            "action": "comparison_failed",
            "error": "Products identified — comparing them is unavailable right now.",
            "code": "INTERNAL_ERROR",
            "request_id": getattr(request.state, "request_id", "unknown"),
            "products": products,
            "vision_cost": vision_cost,
            "message": "Products identified but comparison failed. You can compare them via text.",
        }
