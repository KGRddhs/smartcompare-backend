"""
URL Comparison Routes - API endpoints for URL-based product comparisons
"""
import logging
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from starlette.requests import Request

from app.middleware.rate_limiter import limiter
# W0-1 (P0 LS-REQUEST-PATH-BLOCKING-01): these handlers are `async def`, so the
# SSRF guard's synchronous getaddrinfo used to resolve ON the event loop --
# an unauthenticated caller could freeze the single uvicorn worker for the OS
# resolver timeout per URL. `_validate_url_offloop_or_sync` resolves in the
# dedicated `dns-resolve` pool under ENABLE_OFFLOOP_DNS_RESOLVE and falls back
# to the byte-identical inline sync call when the flag is OFF.
from app.utils.url_validator import _validate_url_offloop_or_sync

from app.services.url_extraction_service import (
    extract_from_url,
    compare_from_urls,
    detect_retailer,
    SUPPORTED_RETAILERS
)
from app.api.auth_routes import get_optional_user
# W2-1: ONE definition of the flag for the whole unit (see the helper's
# docstring in text_routes). url_routes deliberately does not re-parse the env.
from app.api.text_routes import paid_route_metering_enabled
from app.services.feedback_service import save_comparison_and_track_cohort
from app.services.usage_service import (
    consume_comparison_credit,
    refund_comparison_credit,
    record_lifetime_comparison,
)
from app.utils.async_utils import fire_and_forget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/url", tags=["url-comparison"])


async def _reserve_comparison_credit(user: Optional[Dict]) -> bool:
    """Consume ONE freemium credit for an authenticated caller, or 429.

    W2-1 (MB-RECONCILE-01): `/url/compare` has no user dependency at all
    today, so an out-of-credits user gets two paid extractions plus a paid
    verdict call for free. This is `text_routes.text_compare`'s gate (`:193`)
    verbatim -- same atomic consume, same 429 `USAGE_LIMIT` envelope -- shared
    by the POST and GET twins so they can never drift apart.

    Returns True when a credit was actually reserved (and therefore must be
    refunded if the work then fails). Flag OFF, or an anonymous caller: no
    call is made at all and the answer is False.
    """
    if not paid_route_metering_enabled():
        return False
    user_id = user.get("id") if user else None
    if not user_id:
        return False
    usage_check = await consume_comparison_credit(user_id, user.get("access_token", ""))
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
    return bool(usage_check.get("consumed", False))


async def _compare_urls_metered(
    url1: str,
    url2: str,
    region: str,
    selected_category: Optional[str],
    user: Optional[Dict],
) -> Dict:
    """Run the URL comparison under the freemium gate, then persist it.

    ONE body for both verbs. Exactly one consume and AT MOST one refund per
    request: the credit is reserved once above, and each of the two
    non-delivery exits below (the `<2 products` 400 and an exception out of
    `compare_from_urls`) refunds it exactly once before leaving. The delivery
    exit keeps the credit and writes the history row instead.

    MB-NETWORK-CONTRACT-14: a successful URL comparison wrote NO history row,
    so it never appeared in the History tab. Flag ON mirrors the text path --
    fire-and-forget `save_comparison_and_track_cohort(input_type="url")` plus
    the Supabase lifetime counter.
    """
    usage_consumed = await _reserve_comparison_credit(user)
    user_id = user.get("id") if user else None

    try:
        result = await compare_from_urls(url1, url2, region, selected_category)
    except Exception:
        if usage_consumed and user_id:
            fire_and_forget(
                refund_comparison_credit(user_id),
                label="usage_refund.url.compare.exception",
            )
        raise

    if not result.get("success"):
        # The `<2 products` exit. Refund BEFORE raising -- the M13-37 lesson:
        # a refund placed after a call that raises is unreachable dead code.
        if usage_consumed and user_id:
            fire_and_forget(
                refund_comparison_credit(user_id),
                label="usage_refund.url.compare.failure",
            )
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    if paid_route_metering_enabled() and user_id:
        fire_and_forget(
            save_comparison_and_track_cohort(
                full_response=result, query=f"{url1} vs {url2}",
                input_type="url", user_id=user_id,
            ),
            label="save_comparison.url",
        )
        if usage_consumed:
            fire_and_forget(
                record_lifetime_comparison(user_id, user.get("access_token", "")),
                label="record_lifetime.url",
            )

    return result


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
    # MB-RECONCILE-07, UNFLAGGED: the URL path threw the category chip away.
    # `compare_from_urls` hardcoded `None` into `_resolve_pair_category`, so a
    # URL-mode compare could never honour a user category even when the LLM
    # abstained with "other". Optional and defaulted to None = the value that
    # was hardcoded, so an existing caller sees no change.
    selected_category: Optional[str] = Field(
        None, max_length=40, description="User-selected category hint"
    )



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

    if not await _validate_url_offloop_or_sync(body.url):
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
    if not await _validate_url_offloop_or_sync(url):
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
async def compare_urls(
    request: Request,
    body: URLCompareRequest,
    user: Optional[Dict] = Depends(get_optional_user),
):
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

    # The SSRF guard is free and runs BEFORE the gate, so a blocked URL stays a
    # pre-gate 400 with nothing reserved and nothing to refund.
    if not await _validate_url_offloop_or_sync(body.url1) or not await _validate_url_offloop_or_sync(body.url2):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    return await _compare_urls_metered(
        body.url1, body.url2, body.region, body.selected_category, user
    )


@router.get("/compare")
@limiter.limit("10/minute")
async def compare_urls_get(
    request: Request,
    url1: str = Query(..., description="First product URL"),
    url2: str = Query(..., description="Second product URL"),
    region: str = Query("bahrain", description="Region for pricing context"),
    selected_category: Optional[str] = Query(
        None, max_length=40, description="User-selected category hint"
    ),
    user: Optional[Dict] = Depends(get_optional_user),
):
    """GET version of compare for easy testing."""
    if not await _validate_url_offloop_or_sync(url1) or not await _validate_url_offloop_or_sync(url2):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    return await _compare_urls_metered(
        url1, url2, region, selected_category, user
    )


@router.post("/detect")
@limiter.limit("20/minute")
async def detect_retailer_endpoint(request: Request, body: URLExtractRequest):
    """
    Detect retailer from URL without full extraction.

    Useful for validating URLs before processing.
    """
    if not await _validate_url_offloop_or_sync(body.url):
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
    if not await _validate_url_offloop_or_sync(url):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    retailer = detect_retailer(url)

    return {
        "url": url,
        "retailer": retailer,
        "supported": retailer["key"] != "unknown"
    }
