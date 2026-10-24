"""
URL Comparison Routes - API endpoints for URL-based product comparisons
"""
import asyncio
import logging
import time
from typing import Dict, Optional
from urllib.parse import urlsplit
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
# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2): the flag reader, the pre-gate helpers
# and the refusal copy live in the service (one definition each).
from app.services.url_extraction_service import (
    NOT_PRODUCT_PAGE_MESSAGE,
    _host_only,
    url_mode_v2_enabled,
    url_pre_gate_view,
)
from app.api.auth_routes import get_optional_user
# B1 (S80, ENABLE_RESULT_STATUS_METADATA): one status message per delivery exit (telemetry
# only: the URL envelope carries no metadata and is never stamped, R0-1 / B4).
from app.services.sentry_service import capture_result_status
# W2-1: ONE definition of the flag for the whole unit (see the helper's
# docstring in text_routes). url_routes deliberately does not re-parse the env.
from app.api.text_routes import paid_route_metering_enabled
# U13: the paid-route guards, ONE definition each in text_routes (R7).
from app.api.text_routes import require_paid_route_admin, require_paid_route_user
# R-METER (W2-1c): the text route's failure-code -> wire mapping, shared so a
# failed URL verdict surfaces exactly like a failed text comparison.
from app.api.text_routes import _surface_comparison_failure
from app.services.feedback_service import save_comparison_and_track_cohort
# W4-13 T8: by name, so tests patch url_routes.log_search.
from app.services.database_service import log_search, search_log_truth_enabled
from app.api.text_routes import (
    _failure_log_message,
    _log_products_found,
    _search_log_synthetic_kwargs,
)
from app.services.usage_service import (
    consume_comparison_credit,
    refund_comparison_credit,
    record_lifetime_comparison,
)
from app.utils.async_utils import fire_and_forget
# S81-06 ANTHROPIC-ROUTER: the consent entry gate (R-S06-3) and its copy.
from app.services import llm_router as _llm_router
from app.services.structured_comparison_service import LLM_UNAVAILABLE_FRIENDLY_MESSAGE

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


# B4 URL-MODE-V2: the deadline around compare_from_urls under the flag (a module
# constant read at call time; the client's own cap is 35 s, api.ts).
_URL_COMPARE_DEADLINE_SECONDS = 25.0
# The coded per-url failures that ship as 400 + additive field / reason.
_URL_V2_REFUSAL_CODES = ("NOT_PRODUCT_PAGE", "STORE_UNREADABLE", "UNRESOLVED_PRODUCT")
# RULINGS_FIX4_B4 F4-1: the client's validateUrl bound (TwoInputShell.tsx URL_MAX);
# the pre-gate refuses a longer pasted link before any parse (reason url_too_long).
_URL_V2_MAX_LINK_CHARS = 2048


def _url_pre_gate(url1: str, url2: str) -> Optional[Dict[str, str]]:
    """The $0 pre-gate, FLAG-FREE (called only when the route read the flag ON):
    a link longer than _URL_V2_MAX_LINK_CHARS (checked FIRST, before any parse;
    F4-1), a link whose PATH is a storefront root / search / cart / checkout /
    account / category page, or a pair equal after normalisation (each link's
    query parsed ONCE for both, url_pre_gate_view). Returns
    {"field": "url1"|"url2"|"both", "reason": "url_too_long"|<class>|"same_url"}
    (url1's class wins when both links are refused), else None."""
    long1, long2 = (isinstance(u, str) and len(u) > _URL_V2_MAX_LINK_CHARS
                    for u in (url1, url2))
    if long1 or long2:
        field = "both" if long1 and long2 else ("url1" if long1 else "url2")
        return {"field": field, "reason": "url_too_long"}
    r1, key1 = url_pre_gate_view(url1)
    r2, key2 = url_pre_gate_view(url2)
    if r1 is not None or r2 is not None:
        if r1 is not None and r2 is not None:
            field = "both"
        else:
            field = "url1" if r1 is not None else "url2"
        return {"field": field, "reason": r1 or r2}
    if key1 and key1 == key2:
        return {"field": "both", "reason": "same_url"}
    return None


def _raise_url_refusal(code: str, error: str, field: str, reason: str) -> None:
    """The B4 400: a structured detail the error handler surfaces with the additive
    `field` / `reason` keys (scoped to the three B4 codes, flag ON). ONE INFO line,
    constants only (never a url)."""
    logger.info("[URL-V2] refused code=%s field=%s reason=%s", code, field, reason)
    raise HTTPException(
        status_code=400,
        detail={"code": code, "error": error, "field": field, "reason": reason},
    )


async def _compare_with_deadline(url1, url2, region, selected_category) -> Dict:
    """B4: compare_from_urls under the 25 s deadline; an expiry is a coded TIMEOUT
    RESULT (never a raise), which the shared text mapping ships as the structured
    503 build 3 already maps. Any other exception propagates to the caller's
    base exception arm."""
    try:
        return await asyncio.wait_for(
            compare_from_urls(url1, url2, region, selected_category, url_mode_v2=True),
            timeout=_URL_COMPARE_DEADLINE_SECONDS,
        )
    except asyncio.TimeoutError:
        from app.services.structured_comparison_service import TIMEOUT_FRIENDLY_MESSAGE
        logger.warning("[URL-V2] deadline %.1fs hit", _URL_COMPARE_DEADLINE_SECONDS)
        return {"success": False, "code": "TIMEOUT", "error": TIMEOUT_FRIENDLY_MESSAGE}


def _url_log_query(url1, url2) -> str:
    """W4-13 T8 (ruling R4): each url as scheme + host (+ an explicit port) +
    path; the query string, the fragment AND the userinfo (`user:pass@`) are
    DROPPED -- tracking/session tokens and credentials never land in an
    analytics table. A malformed url gives '' for its half, never a raise."""
    def _one(u) -> str:
        try:
            p = urlsplit(u if isinstance(u, str) else "")
            _ = p.port  # ValueError on a malformed port
        except ValueError:
            return ""
        if not p.scheme or not p.hostname:
            return ""
        return f"{p.scheme}://{p.netloc.rpartition('@')[2]}{p.path}"
    return f"{_one(url1)} vs {_one(url2)}"


# W4-13 T8, post-green ruling R9(a): the '<2 products' exit's message is a
# route-owned code constant (url_extraction_service.py:596) -- no exception
# text can reach it -- so the failure ROW logs it verbatim. Every other
# codeless message still takes the W4-9 floor.
_URL_FEW_PRODUCTS_MESSAGE = "Could not extract both products"


def _url_failure_log_message(result) -> str:
    if (isinstance(result, dict) and not result.get("code")
            and result.get("error") == _URL_FEW_PRODUCTS_MESSAGE):
        return _URL_FEW_PRODUCTS_MESSAGE
    return _failure_log_message(result) or "Comparison failed"


async def _compare_urls_metered(
    url1: str,
    url2: str,
    region: str,
    selected_category: Optional[str],
    user: Optional[Dict],
    search_log_extra: Optional[Dict] = None,
    url_mode_v2: bool = False,
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

    B4 (``url_mode_v2=True``, passed only when the route read the flag ON): the
    comparison runs under the 25 s deadline (_compare_with_deadline) and the
    three coded per-url failures ship as the 400 with `field` / `reason`; each is
    a non-delivery through the SAME failure exit below (R-A3: refund once, no
    lifetime bump, no history row, the failure row with the code's constant).
    """
    # S81-06 (R-S06-3 / GC-4): the consent entry gate of both verbs, BEFORE the
    # credit reserve (nothing consumed, nothing to refund): the coded 503
    # LLM_UNAVAILABLE envelope. Every role flag OFF: five getenv reads.
    if _llm_router.compare_refuses_for_consent():
        logger.info("[ROUTER] consent update required at compare entry")
        raise HTTPException(
            status_code=503,
            detail={"code": "LLM_UNAVAILABLE", "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE},
        )
    _start = time.time()
    usage_consumed = await _reserve_comparison_credit(user)
    user_id = user.get("id") if user else None
    _truth = search_log_truth_enabled()

    def _url_row(label: str, **kw) -> None:
        # W4-13 T8: every url row is built AFTER its refund and before the
        # raise/return (ruling C3); only ever called under flag 1.
        fire_and_forget(
            log_search(
                query=_url_log_query(url1, url2), input_type="url", user_id=user_id,
                duration_ms=int((time.time() - _start) * 1000),
                **kw, **(search_log_extra or {}),
            ),
            label=label,
        )

    try:
        if url_mode_v2:
            result = await _compare_with_deadline(url1, url2, region, selected_category)
        else:
            result = await compare_from_urls(url1, url2, region, selected_category)
    except Exception:
        if usage_consumed and user_id:
            fire_and_forget(
                refund_comparison_credit(user_id),
                label="usage_refund.url.compare.exception",
            )
        if _truth:
            _url_row("log_search.url.exception", success=False,
                     error_message="url_compare_exception")  # never str(e)
        raise

    if not result.get("success"):
        # The `<2 products` and failed-verdict (R-METER W2-1c) exits. Refund
        # BEFORE raising -- the M13-37 lesson:
        # a refund placed after a call that raises is unreachable dead code.
        if usage_consumed and user_id:
            fire_and_forget(
                refund_comparison_credit(user_id),
                label="usage_refund.url.compare.failure",
            )
        if _truth:
            # R1 + R9(a): the route's own '<2 products' literal verbatim; any
            # other codeless message takes the W4-9 floor.
            _url_row("log_search.url.failure", success=False,
                     error_message=_url_failure_log_message(result))
        # R-METER (W2-1c): only a CODED failure (the failed-verdict
        # LLM_UNAVAILABLE result) rides the text route's mapping, which raises
        # the structured `{code, error}` 503 the error handler lifts to the top
        # level. A code-less result (the `<2 products` exit) keeps main's bare-
        # string 400 below, byte-identical: W4-9's codeless allowlist in that
        # mapping would redact its message to INTERNAL_ERROR.
        # B4: the three coded per-url failures keep their field / reason (the
        # shared mapping would drop them); TIMEOUT takes the mapping's 503.
        if url_mode_v2 and result.get("code") in _URL_V2_REFUSAL_CODES:
            _raise_url_refusal(
                result["code"], result.get("error") or "",
                result.get("field") or "both", result.get("reason") or "unknown",
            )
        if result.get("code"):
            surfaced = _surface_comparison_failure(result)
            if surfaced is not None:
                return surfaced
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

    if _truth:
        _url_row(
            "log_search.url.success", success=True,
            products_found=_log_products_found(result),
        )

    # B1 (S80): the route's own wall as compare_ms (the envelope has no elapsed_ms).
    capture_result_status(result, "url", compare_ms=int((time.time() - _start) * 1000))
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


@router.post("/extract", dependencies=[Depends(require_paid_route_admin)])
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
    # R-A1(b), UNFLAGGED log-only: the host, never the pasted path or query.
    logger.info("URL extraction request: host=%s", _host_only(body.url))

    if not await _validate_url_offloop_or_sync(body.url):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    result = await extract_from_url(body.url)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to extract product data")
        )
    
    return result


@router.get("/extract", dependencies=[Depends(require_paid_route_admin)])
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


@router.post("/compare", dependencies=[Depends(require_paid_route_user)])
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
    # R-A1(b), UNFLAGGED log-only: the hosts, never the pasted paths or queries.
    logger.info("URL comparison request: %s vs %s", _host_only(body.url1), _host_only(body.url2))
    # B4: ENABLE_URL_MODE_V2 read ONCE per request; the bool is threaded down.
    v2 = url_mode_v2_enabled()

    # The SSRF guard is free and runs BEFORE the gate, so a blocked URL stays a
    # pre-gate 400 with nothing reserved and nothing to refund.
    if not await _validate_url_offloop_or_sync(body.url1) or not await _validate_url_offloop_or_sync(body.url2):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    if v2:
        # B4 pre-gate: after the SSRF 400, BEFORE the credit reserve ($0, no row).
        refusal = _url_pre_gate(body.url1, body.url2)
        if refusal:
            _raise_url_refusal("NOT_PRODUCT_PAGE", NOT_PRODUCT_PAGE_MESSAGE,
                               refusal["field"], refusal["reason"])
        return await _compare_urls_metered(
            body.url1, body.url2, body.region, body.selected_category, user,
            search_log_extra=_search_log_synthetic_kwargs(request), url_mode_v2=True,
        )

    return await _compare_urls_metered(
        body.url1, body.url2, body.region, body.selected_category, user,
        search_log_extra=_search_log_synthetic_kwargs(request),
    )


@router.get("/compare", dependencies=[Depends(require_paid_route_user)])
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
    # B4: ENABLE_URL_MODE_V2 read ONCE per request; the bool is threaded down.
    v2 = url_mode_v2_enabled()
    if not await _validate_url_offloop_or_sync(url1) or not await _validate_url_offloop_or_sync(url2):
        raise HTTPException(status_code=400, detail="URL blocked by security policy")

    if v2:
        # B4 pre-gate: after the SSRF 400, BEFORE the credit reserve ($0, no row).
        refusal = _url_pre_gate(url1, url2)
        if refusal:
            _raise_url_refusal("NOT_PRODUCT_PAGE", NOT_PRODUCT_PAGE_MESSAGE,
                               refusal["field"], refusal["reason"])
        return await _compare_urls_metered(
            url1, url2, region, selected_category, user,
            search_log_extra=_search_log_synthetic_kwargs(request), url_mode_v2=True,
        )

    return await _compare_urls_metered(
        url1, url2, region, selected_category, user,
        search_log_extra=_search_log_synthetic_kwargs(request),
    )


# U13e (EO-01, W0 = guard): no app caller, not paid; extends the admin set to six verbs. The
# anonymous half of EO-01 is closed while ENABLE_COMPARE_AUTH_REQUIRED is on (refused before the
# SSRF guard resolves DNS on the loop); the signed-in half (POST/GET /url/compare) stays until
# ENABLE_OFFLOOP_DNS_RESOLVE.
@router.post("/detect", dependencies=[Depends(require_paid_route_admin)])
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


@router.get("/detect", dependencies=[Depends(require_paid_route_admin)])
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
