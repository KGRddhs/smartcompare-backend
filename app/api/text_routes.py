"""
Text Comparison Routes - API endpoints for text-based product comparisons
"""
import json
import logging
import time
from typing import Optional, Dict, AsyncGenerator
from fastapi import APIRouter, HTTPException, Path, Query, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator

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
from app.utils.async_utils import fire_and_forget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/text", tags=["text-comparison"])


# ============================================
# Request/Response Models
# ============================================

class TextCompareRequest(BaseModel):
    """Request for text-based comparison.

    Accepts two shapes (dual-shape Pydantic pattern, spec § 5.1):
      - Legacy: {"query": "iPhone 15 vs Galaxy S24"}
      - New:    {"product_a": "iPhone 15", "product_b": "Galaxy S24"}

    Sending both or neither raises 422. When product_a + product_b are
    provided, they are concatenated into `query` so the rest of the
    handler is shape-agnostic; the explicit pair is also surfaced via
    a separate kwarg to skip parse_product_query() downstream.
    """
    query: Optional[str] = None
    product_a: Optional[str] = None
    product_b: Optional[str] = None
    region: str = "bahrain"
    include_specs: bool = True
    include_reviews: bool = True
    include_pros_cons: bool = True
    selected_category: Optional[str] = None

    @model_validator(mode="after")
    def normalize_shape(self) -> "TextCompareRequest":
        has_pair = bool(self.product_a and self.product_a.strip()
                        and self.product_b and self.product_b.strip())
        has_query = bool(self.query and self.query.strip())
        if has_pair and has_query:
            raise ValueError("Send EITHER query OR product_a+product_b, not both")
        if not has_pair and not has_query:
            raise ValueError("Send product_a+product_b OR query")
        if has_pair:
            self.query = f"{self.product_a.strip()} vs {self.product_b.strip()}"
        return self


class QuickCompareRequest(BaseModel):
    """Quick comparison with just product names"""
    product1: str
    product2: str
    region: str = "bahrain"


# WS1 (genuine-bh-latency bundle, D2) — map a non-success comparison result to
# the right wire surface. Replaces the old blanket `HTTPException(400)` that
# collapsed EVERY failure code (including TIMEOUT) into BAD_REQUEST.
#
# Contract (error_handler.py unwraps a structured detail dict, preserving the
# code even on a 503 — verified against http_exception_handler):
#   - CONTENT_UNAVAILABLE → return the structured dict as-is at HTTP 200
#     (Bundle B content-safety surface; FE reads the body, not the status).
#   - TIMEOUT             → HTTPException(503, {code:"TIMEOUT", error}) → the
#     unified envelope surfaces code:"TIMEOUT" (transient/retryable), NOT 400.
#   - everything else (INSUFFICIENT_DATA, parser-failure, generic) → HTTP 400.
#
# Returns a dict to early-return (CONTENT_UNAVAILABLE) or raises HTTPException.
def _surface_comparison_failure(result: Dict):
    code = result.get("code")
    error_msg = result.get("error", "Comparison failed")
    if code == "CONTENT_UNAVAILABLE":
        # Preserve the structured body (FE matches the spec contract). Wrapping
        # in HTTPException would drop the layer/extra keys via str(detail).
        return result
    if code == "TIMEOUT":
        # D2 — transient timeout. Structured detail so the envelope keeps
        # code:"TIMEOUT" (error_handler overrides the 503→FEATURE_DISABLED
        # default when a code is supplied). 503, NOT 400.
        raise HTTPException(
            status_code=503,
            detail={"code": "TIMEOUT", "error": error_msg},
        )
    # INSUFFICIENT_DATA + parser-failure + anything unrecognized → 400. Keep
    # the structured code where present so the FE can branch (e.g. show the
    # "choose different products" copy for INSUFFICIENT_DATA).
    if code:
        raise HTTPException(
            status_code=400,
            detail={"code": code, "error": error_msg},
        )
    raise HTTPException(status_code=400, detail=error_msg)


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

    # Dual-shape: explicit pair bypasses parse_product_query() in the service
    # (wired via explicit_pair= kwarg in Phase 2). Stored here for forward use.
    explicit_pair = None
    if body.product_a and body.product_b:
        explicit_pair = (body.product_a.strip(), body.product_b.strip())

    result = await service.compare_from_text(
        query=body.query,
        region=body.region,
        include_specs=body.include_specs,
        include_reviews=body.include_reviews,
        include_pros_cons=body.include_pros_cons,
        selected_category=body.selected_category,
        user_preferences=user_prefs,
        user_id=user.get("id") if user else None,
        explicit_pair=explicit_pair,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not result.get("success"):
        # Log failed search — Bundle D 2.B.6 WRAP: failure-path log; silent
        # fail = no record of why a comparison crashed.
        fire_and_forget(
            log_search(
                query=body.query, input_type="text",
                user_id=user.get("id") if user else None,
                success=False, error_message=result.get("error"),
                duration_ms=duration_ms,
            ),
            label="log_search.text.post.failure",
        )
        # WS1 (D2) — map the failure code to its proper wire surface
        # (CONTENT_UNAVAILABLE→200 body, TIMEOUT→503, else→400). Replaces the
        # old blanket 400 that hid TIMEOUT behind BAD_REQUEST. A best-available
        # PARTIAL has success:true so it never reaches this branch.
        surfaced = _surface_comparison_failure(result)
        if surfaced is not None:
            return surfaced

    # Extract product names for logging
    product_names = [f"{p.get('brand', '')} {p.get('name', '')}".strip()
                     for p in result.get("products", [])]

    user_id = user.get("id") if user else None

    # Fire-and-forget: log search + save history — Bundle D 2.B.6 WRAP
    # (log_search fail = lost analytics; save_comparison fail = missing
    # history row; record_comparison fail = wrong free-tier counter).
    fire_and_forget(
        log_search(
            query=body.query, input_type="text", user_id=user_id,
            products_found=product_names, success=True,
            cost=result.get("metadata", {}).get("total_cost", 0),
            duration_ms=duration_ms,
        ),
        label="log_search.text.post.success",
    )
    if user_id:
        fire_and_forget(
            save_comparison_and_track_cohort(
                full_response=result, query=body.query,
                input_type="text", user_id=user_id,
            ),
            label="save_comparison.text.post",
        )
        fire_and_forget(
            record_comparison(user_id, user.get("access_token", "")),
            label="record_comparison.text.post",
        )

    return result


@router.get("/compare")
@limiter.limit("10/minute")
async def text_compare_get(
    request: Request,
    q: Optional[str] = Query(None, max_length=500, description="Legacy single-string query, e.g., 'iPhone 15 vs S24'"),
    product_a: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit first product, paired with product_b"),
    product_b: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit second product, paired with product_a"),
    region: str = Query("bahrain", description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    selected_category: Optional[str] = Query(None, description="User-selected category hint"),
    user: Optional[Dict] = Depends(get_optional_user),
):
    """GET version of text comparison for easy testing.

    Dual-shape (Bundle B § 5.1) — matches the POST + streaming endpoints:
      - ?q=iPhone+15+vs+Galaxy+S24                     (legacy single-string)
      - ?product_a=iPhone+15&product_b=Galaxy+S24      (Bundle B pair)
    Sending both or neither raises 422. When the pair is provided, q is
    synthesized as "{product_a} vs {product_b}" so the orchestrator stays
    shape-agnostic.
    """
    has_pair = bool(product_a and product_a.strip() and product_b and product_b.strip())
    has_query = bool(q and q.strip())
    if has_pair and has_query:
        raise HTTPException(
            status_code=422,
            detail="Send EITHER q OR product_a+product_b, not both",
        )
    if not has_pair and not has_query:
        raise HTTPException(
            status_code=422,
            detail="Send product_a+product_b OR q",
        )
    explicit_pair = None
    if has_pair:
        explicit_pair = (product_a.strip(), product_b.strip())
        q = f"{product_a.strip()} vs {product_b.strip()}"

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
        explicit_pair=explicit_pair,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not result.get("success"):
        # Bundle D 2.B.6 WRAP: GET-handler failure-path log.
        fire_and_forget(
            log_search(
                query=q, input_type="text",
                user_id=user.get("id") if user else None,
                success=False, error_message=result.get("error"),
                duration_ms=duration_ms,
            ),
            label="log_search.text.get.failure",
        )
        # WS1 (D2) — same code→surface mapping as the POST handler. TIMEOUT→503,
        # CONTENT_UNAVAILABLE→200 body, else→400. The old blanket 400 was the
        # bug that surfaced a hard-cap TIMEOUT as BAD_REQUEST with scary copy.
        surfaced = _surface_comparison_failure(result)
        if surfaced is not None:
            return surfaced

    product_names = [f"{p.get('brand', '')} {p.get('name', '')}".strip()
                     for p in result.get("products", [])]

    user_id = user.get("id") if user else None

    # Fire-and-forget: log search + save history — Bundle D 2.B.6 WRAP.
    fire_and_forget(
        log_search(
            query=q, input_type="text", user_id=user_id,
            products_found=product_names, success=True,
            cost=result.get("metadata", {}).get("total_cost", 0),
            duration_ms=duration_ms,
        ),
        label="log_search.text.get.success",
    )
    if user_id:
        fire_and_forget(
            save_comparison_and_track_cohort(
                full_response=result, query=q,
                input_type="text", user_id=user_id,
            ),
            label="save_comparison.text.get",
        )
        fire_and_forget(
            record_comparison(user_id, user.get("access_token", "")),
            label="record_comparison.text.get",
        )

    return result


@router.get("/compare/stream")
@limiter.limit("10/minute")
async def text_compare_stream(
    request: Request,
    q: Optional[str] = Query(None, max_length=500, description="Legacy single-string query, e.g., 'iPhone 15 vs S24'"),
    product_a: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit first product, paired with product_b"),
    product_b: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit second product, paired with product_a"),
    region: str = Query("bahrain", description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    selected_category: Optional[str] = Query(None, description="User-selected category hint"),
    user: Optional[Dict] = Depends(get_optional_user),
):
    """SSE streaming version of text comparison. Returns Server-Sent Events.

    Dual-shape (Bundle B sec 5.1) — same mutual-exclusion rules as POST /compare:
      - ?q=iPhone+15+vs+Galaxy+S24                     (legacy single-string)
      - ?product_a=iPhone+15&product_b=Galaxy+S24      (Bundle B pair)
    Both shapes hit L1 + L3 identically. Pair shape forwards explicit_pair
    so the service skips parse_product_query().
    """
    # Dual-shape validation — surfaces before StreamingResponse construction
    # so clients get a clean 422, not a partial event stream.
    has_pair = bool(product_a and product_a.strip() and product_b and product_b.strip())
    has_query = bool(q and q.strip())
    if has_pair and has_query:
        raise HTTPException(
            status_code=422,
            detail="Send EITHER q OR product_a+product_b, not both",
        )
    if not has_pair and not has_query:
        raise HTTPException(
            status_code=422,
            detail="Send product_a+product_b OR q",
        )

    explicit_pair = None
    if has_pair:
        explicit_pair = (product_a.strip(), product_b.strip())
        q = f"{product_a.strip()} vs {product_b.strip()}"

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
            explicit_pair=explicit_pair,
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
            # Bundle D 2.B.6 WRAP: post-stream analytics; silent fail = wrong
            # KPI numbers + missing history rows.
            fire_and_forget(
                log_search(
                    query=q, input_type="text_stream", user_id=user_id,
                    products_found=product_names, success=True,
                    cost=complete_response.get("metadata", {}).get("total_cost", 0),
                    duration_ms=duration_ms,
                ),
                label="log_search.text_stream.success",
            )
            if user_id:
                fire_and_forget(
                    save_comparison_and_track_cohort(
                        full_response=complete_response, query=q,
                        input_type="text_stream", user_id=user_id,
                    ),
                    label="save_comparison.text_stream",
                )
                fire_and_forget(
                    record_comparison(user_id, user.get("access_token", "")),
                    label="record_comparison.text_stream",
                )
        elif had_error:
            # Bundle D 2.B.6 WRAP: failure-path log on streaming.
            fire_and_forget(
                log_search(
                    query=q, input_type="text_stream", user_id=user_id,
                    success=False, error_message="Streaming comparison failed",
                    duration_ms=duration_ms,
                ),
                label="log_search.text_stream.failure",
            )

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


@router.get("/price-kpi")
@limiter.limit("30/minute")
async def price_kpi(
    request: Request,
    q: str = Query(..., max_length=200, description="Single-product query"),
    region: str = Query("bahrain", max_length=20),
    nocache: bool = Query(True, description="Bypass cache (COLD KPI); false = WARMED"),
):
    """SINGLE-PRODUCT price resolution for the usable_exact_genuine KPI (external
    review #1). The KPI cannot use /compare (it rejects a query resolving to <2
    products). This runs the REAL parser (`parse_product_query`) + the full price
    cascade (`_get_price`) + the `is_price_showable(enforce_correctness=True)`
    display backstop, and returns a ``{products: [{price}]}`` body the KPI harness
    reads at index 0 — so the metric is measured through the real ASGI app + parser,
    not a fabricated mock. Internal/measurement surface; rate-limited.
    """
    from app.services.extraction_service import parse_product_query
    from app.services.price_service import (
        is_price_showable, make_pending_price, public_price_view,
        _infer_category_from_query,
    )
    service = get_comparison_service()
    try:
        parsed, _usage = await parse_product_query(q)
    except Exception:  # noqa: BLE001 — a parser failure falls back to a naive single product
        parsed = {}
    products = (parsed or {}).get("products") or []
    p0 = products[0] if products else {}
    brand = (p0.get("brand") or "").strip()
    name = (p0.get("name") or q).strip()
    variant = p0.get("variant")
    category = (p0.get("category") or _infer_category_from_query(q) or "other")
    search_query = (f"{brand} {name} {variant or ''}".strip()) or q
    full_name = (f"{brand} {name}".strip()) or q

    price = await service._get_price(brand, name, variant, region, search_query, nocache, category)

    showable = (
        isinstance(price, dict)
        and price.get("unavailable") is not True
        and is_price_showable(full_name, price, category, enforce_correctness=True)
    )
    if not showable:
        price = make_pending_price(
            currency=(price.get("currency") if isinstance(price, dict) else None) or "BHD",
            reason="pending_genuine",
        )

    public = public_price_view(price)
    return {
        "success": True,
        "query": q,
        "category": category,
        "products": [{"brand": brand, "name": name, "category": category, "price": public}],
        # `overview.products[0].price` is the shape the KPI's usable_exact_genuine_for_product reads.
        "overview": {"products": [{"price": public}]},
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

