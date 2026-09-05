"""
Text Comparison Routes - API endpoints for text-based product comparisons
"""
import json
import logging
import os
import time
from typing import Any, List, Optional, Dict, AsyncGenerator
from fastapi import APIRouter, HTTPException, Path, Query, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

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
from app.services.usage_service import (
    consume_comparison_credit,
    refund_comparison_credit,
    record_lifetime_comparison,
    anon_usage_gate_enabled,
    valid_device_fingerprint,
    check_anon_usage_allowed,
    record_anon_comparison,
)
from app.utils.async_utils import fire_and_forget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/text", tags=["text-comparison"])


def preverdict_disconnect_abort_enabled() -> bool:
    """True iff a PRE-verdict SSE disconnect closes the orchestrator generator
    instead of draining it (M18 CD-interactions-01 Half B, default OFF).

    Half A of that finding (refund the gate-reserved credit and skip metering
    when the client left before the final payload) is UNFLAGGED — it is a pure
    accounting correction with no result fork for legitimate completed traffic.
    This flag covers only the RESOURCE half: with it ON the route stops pulling
    from `compare_from_text_streaming` and awaits its `aclose()`, so the
    default-unbounded verdict/critique/moderation OpenAI tail is not paid for a
    comparison nobody will read. Read PER CALL from os.getenv (the
    ``price_service.exact_gate_enabled`` idiom) so Railway flips it without a
    restart, and so flag OFF is byte-identical to the M13-35 drain.
    """
    return os.getenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


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
    # M13-25: mirror the GET twin's length caps so the POST body cannot be used
    # as an unauthenticated log-flood / search_logs row-bloat primitive (FastAPI
    # applies no default body-size limit). q=500, product_a/b=80 match GET;
    # region + selected_category are bounded to their real value ranges.
    query: Optional[str] = Field(default=None, max_length=500)
    product_a: Optional[str] = Field(default=None, max_length=80)
    product_b: Optional[str] = Field(default=None, max_length=80)
    region: str = Field(default="bahrain", max_length=20)
    include_specs: bool = True
    include_reviews: bool = True
    include_pros_cons: bool = True
    selected_category: Optional[str] = Field(default=None, max_length=40)

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

    # Usage gate for authenticated users. M13-37: consume the daily/monthly credit
    # ATOMICALLY at the gate (was a TOCTOU — read here, increment fire-and-forget
    # after, so N parallel requests all read the same value and all passed).
    usage_consumed = False
    if user and user.get("id"):
        usage_check = await consume_comparison_credit(user["id"], user.get("access_token", ""))
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
        usage_consumed = usage_check.get("consumed", False)

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
        # M13-37: the work failed after the gate reserved a credit — refund it
        # for EVERY failure surface so a failed comparison never burns the user's
        # daily allowance (parity with the legacy record-only-on-success flow).
        # This MUST fire BEFORE _surface_comparison_failure: that call RAISES
        # HTTPException for TIMEOUT/INSUFFICIENT_DATA/generic codes (only
        # CONTENT_UNAVAILABLE returns a dict), so a refund placed after it is
        # unreachable on exactly the common cold-path failures.
        if usage_consumed and user and user.get("id"):
            fire_and_forget(
                refund_comparison_credit(user["id"]),
                label="usage_refund.text.post",
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
        # M13-37: daily/monthly were reserved atomically at the gate; only the
        # Supabase lifetime counter remains to be written (fire-and-forget).
        fire_and_forget(
            record_lifetime_comparison(user_id, user.get("access_token", "")),
            label="record_lifetime.text.post",
        )

    return result


@router.get("/compare")
@limiter.limit("10/minute")
async def text_compare_get(
    request: Request,
    q: Optional[str] = Query(None, max_length=500, description="Legacy single-string query, e.g., 'iPhone 15 vs S24'"),
    product_a: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit first product, paired with product_b"),
    product_b: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit second product, paired with product_a"),
    region: str = Query("bahrain", max_length=20, description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    selected_category: Optional[str] = Query(None, max_length=40, description="User-selected category hint"),
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

    # Usage gate for authenticated users. M13-37: atomic consume at the gate
    # (same TOCTOU fix as POST /compare).
    usage_consumed = False
    if user and user.get("id"):
        usage_check = await consume_comparison_credit(user["id"], user.get("access_token", ""))
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
        usage_consumed = usage_check.get("consumed", False)

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
        # M13-37: refund the gate-reserved credit on a failed comparison — BEFORE
        # _surface_comparison_failure, which RAISES for TIMEOUT/INSUFFICIENT_DATA/
        # generic (only CONTENT_UNAVAILABLE returns a dict), so a refund after it
        # is unreachable on the common cold-path failures.
        if usage_consumed and user and user.get("id"):
            fire_and_forget(
                refund_comparison_credit(user["id"]),
                label="usage_refund.text.get",
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
        # M13-37: daily/monthly reserved at the gate; write only lifetime here.
        fire_and_forget(
            record_lifetime_comparison(user_id, user.get("access_token", "")),
            label="record_lifetime.text.get",
        )

    return result


@router.get("/compare/stream")
@limiter.limit("10/minute")
async def text_compare_stream(
    request: Request,
    q: Optional[str] = Query(None, max_length=500, description="Legacy single-string query, e.g., 'iPhone 15 vs S24'"),
    product_a: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit first product, paired with product_b"),
    product_b: Optional[str] = Query(None, max_length=80, description="Bundle B: explicit second product, paired with product_a"),
    region: str = Query("bahrain", max_length=20, description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    selected_category: Optional[str] = Query(None, max_length=40, description="User-selected category hint"),
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

    # Usage gate for authenticated users. M13-37: atomic consume at the gate
    # (same TOCTOU fix as POST/GET /compare). usage_consumed is captured by the
    # event_generator closure so it can refund on a streaming error.
    usage_consumed = False
    if user and user.get("id"):
        usage_check = await consume_comparison_credit(user["id"], user.get("access_token", ""))
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
        usage_consumed = usage_check.get("consumed", False)

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
        complete_after_client_gone = False
        had_error = False
        client_gone = False

        # M13-35: the post-stream side effects (quota metering, history save,
        # analytics) MUST run even if the client drops the socket AFTER the
        # verdict/complete events — by then it already has the entire comparison
        # and the OpenAI/Serper spend is already made, so an early `return` on
        # disconnect was a free, repeatable metering bypass. The whole loop is
        # wrapped in try/finally, the final payload is captured BEFORE the
        # disconnect check, and a disconnect drains (not abandons) the generator
        # so the payload is fully captured. Side effects then fire in the finally,
        # keyed on whether the payload was produced.
        #
        # M18 CD-interactions-01: that drain also made the M13-37 refund
        # unreachable for a PRE-verdict drop — the generator ran to completion,
        # so `complete_response` was set and the finally took the METERING
        # branch, burning a free credit for a result the user never received.
        # `complete_after_client_gone` records WHEN the payload landed relative
        # to the client leaving: `client_gone` is set on the iteration the
        # disconnect is first observed, and the capture below runs before that
        # check on the same iteration, which is exactly why M13-35's post-verdict
        # case still meters.
        #
        # The orchestrator generator is BOUND (not inlined into the `async for`)
        # so Half B can close it explicitly. It is closed ONLY on the Half-B
        # abort path: with the flag OFF this route makes exactly the same calls
        # on `_stream` as it did before M18, so flag-OFF behaviour is unchanged.
        _stream = service.compare_from_text_streaming(
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
        try:
            async for event_type, data in _stream:
                # Capture the final payload BEFORE the disconnect check. `complete`
                # is the canonical final-payload event; `settle_complete` is the
                # Bundle E equivalent emitted right after `verdict` and carries the
                # same payload — capturing it means a disconnect right after the
                # verdict still has the full response to meter + persist.
                if event_type in ("complete", "settle_complete"):
                    if complete_response is None:
                        # Latch on the FIRST final payload: a settle_complete
                        # delivered while still connected pins this False even if
                        # the duplicate `complete` arrives post-disconnect.
                        complete_after_client_gone = client_gone
                    complete_response = data
                if event_type == "error":
                    had_error = True

                if client_gone:
                    # Client already left: keep draining so the final payload is
                    # captured, but stop pushing bytes to a dead socket.
                    continue
                if await request.is_disconnected():
                    logger.info(f"[SSE] Client disconnected during stream for query: {q}")
                    client_gone = True
                    if complete_response is None and preverdict_disconnect_abort_enabled():
                        # Half B (dark): nobody will read this comparison, so stop
                        # driving the orchestrator instead of paying for its
                        # default-unbounded verdict/critique/moderation tail. A
                        # bare `break` is NOT enough — leaving an `async for` does
                        # not call aclose(), and CPython's async-generator
                        # finalizer runs the orchestrator's finally later and
                        # non-deterministically. Closing here throws GeneratorExit
                        # into it now, so M13-30's `_get_price` finally cancels its
                        # prefetch tasks at the break.
                        await _stream.aclose()
                        break
                    continue

                yield f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
        finally:
            # Fire-and-forget logging once the stream (or the client) is done.
            duration_ms = int((time.time() - start_time) * 1000)
            user_id = user.get("id") if user else None

            if complete_response and not had_error and not complete_after_client_gone:
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
                    # M13-37: daily/monthly reserved at the gate; lifetime only here.
                    fire_and_forget(
                        record_lifetime_comparison(user_id, user.get("access_token", "")),
                        label="record_lifetime.text_stream",
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
                # M13-37: the stream errored after the gate reserved a credit —
                # refund it so a failed comparison does not burn a daily credit.
                if usage_consumed and user_id:
                    fire_and_forget(
                        refund_comparison_credit(user_id),
                        label="usage_refund.text_stream",
                    )
            else:
                # M13-37 parity: no metered final payload and no explicit error
                # event — a mid-stream raise, a cancel (this finally runs on
                # CancelledError/GeneratorExit too), or (M18) a payload that only
                # landed AFTER the client was already gone, whether the generator
                # drained to it or Half B closed it. The gate reserved a credit
                # that was never metered, so refund it — matching
                # the legacy record-only-on-success behaviour and closing the last
                # leak the POST/GET fix left on the streaming route.
                if usage_consumed and user_id:
                    fire_and_forget(
                        refund_comparison_credit(user_id),
                        label="usage_refund.text_stream.incomplete",
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
    # M13-03: anonymous freemium gate (dark, ENABLE_ANON_USAGE_GATE default OFF).
    # This is an unauthenticated endpoint that runs a full paid comparison, so a
    # caller could bypass the 3-lifetime/10-monthly tier by never signing in.
    # With the flag ON we meter anonymous callers by their (regex-validated)
    # X-Device-Fingerprint. Flag-OFF leaves device_fp None -> byte-identical.
    device_fp = None
    if anon_usage_gate_enabled():
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

    if device_fp:
        fire_and_forget(record_anon_comparison(device_fp), label="record_anon.quick")

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
    _admin: bool = Depends(verify_admin_key),
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


# ============================================
# Issue #55 — DELETE /text/cache actually clears what the LIVE price path wrote
# ============================================
# The flush is the documented remedy for a poisoned price, but it deleted the
# LEGACY size-agnostic `get_price_cache_key(...)` while `_get_price` keys L1 with
# `build_size_aware_price_cache_key(...)`. It also never touched the 30-day
# `nogenuine:{price_key}` sentinel or the L2 `product_prices` row that
# `_get_price` re-promotes into L1 on the very next request — and it reported
# `"deleted": true` regardless, because `delete_cached` returns True for any
# Redis call that does not raise. An operator believed the cache was clear when
# it was not.

FLUSH_REGION = "bahrain"


def flush_live_price_key_enabled() -> bool:
    """True iff DELETE /text/cache clears the keys the LIVE price path writes
    (issue #55, default OFF).

    Flag ON: the flush also deletes the size-aware L1 price key(s) that
    `structured_comparison_service._get_price` actually writes, the
    `nogenuine:` sentinel derived from each of them, and the L2
    `product_prices` rows for the flushed region — and reports, per key,
    whether a readable value was present before the delete.

    Flag OFF: byte-identical to the pre-#55 route — the same three legacy keys,
    the same `{"key": ..., "deleted": ...}` shape, the same top-level body, no
    Supabase call and no extra Redis read. (The tuple-unpack repair above the
    branch is the ONE unflagged change; see its comment.)

    Read PER CALL from `os.getenv` (the `price_service.exact_gate_enabled`
    idiom) so Railway flips it without a restart; never cached at import.
    """
    return os.getenv("ENABLE_FLUSH_LIVE_PRICE_KEY", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _flush_price_cache_keys(
    brand: str, name: str, variant: Optional[str], region: str,
    q: str, product_info: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Every L1 price key this product could be cached under, most-live first.

    Ordered + de-duplicated (a sizeless/qualifierless product collapses all
    three onto ONE key — `build_size_aware_price_cache_key` falls back to the
    legacy builder when no identity token is found — so the caller issues a
    single delete, not three).

    1. The LIVE key: the same builder, `search_query` and canonicalized
       `category` `_fetch_product_data` -> `_get_price` uses, so the identity
       token (EDP / 100ml / 256GB / FE) matches the poisoned entry.
    2. The raw-`q` key: the operator's own query text under the best-effort
       `_infer_category_from_query`, in case the parser normalized an axis out
       of `search_query`/`category` that the raw query still carries.
    3. The LEGACY size-agnostic key, so an entry warmed before the size-aware
       key existed is still cleared.

    Deleting a superset is safe: every candidate is a price key for THIS
    product+region — nothing here can reach a different product's slot.
    """
    from app.services.extraction_service import (
        get_price_cache_key, canonicalize_category,
    )
    from app.services.price_service import (
        build_size_aware_price_cache_key, _infer_category_from_query,
    )

    info = product_info or {}
    keys: List[str] = []

    def _add(key: Optional[str]) -> None:
        if key and key not in keys:
            keys.append(key)

    # Mirrors structured_comparison_service._fetch_product_data exactly.
    search_query = info.get("search_query") or f"{brand} {name} {variant or ''}"
    _add(build_size_aware_price_cache_key(
        brand, name, variant, region, search_query,
        category=canonicalize_category(info.get("category")),
    ))
    _add(build_size_aware_price_cache_key(
        brand, name, variant, region, q,
        category=_infer_category_from_query(q),
    ))
    _add(get_price_cache_key(brand, name, variant, region))
    return keys


def _flush_delete_key(key: str) -> Dict[str, Any]:
    """Delete one cache key and report HONESTLY what happened.

    `delete_cached` returns True for any Redis call that does not raise, so it
    cannot tell "removed a poisoned entry" from "the key was never there".
    `existed` is a pre-delete read: True = a readable JSON value was present.
    """
    from app.services.cache_service import delete_cached, get_cached
    try:
        existed = get_cached(key) is not None
    except Exception:  # noqa: BLE001 — an unreadable probe must not fail the flush
        existed = None
    return {"key": key, "existed": existed, "deleted": delete_cached(key)}


async def _flush_l2_price_rows(price_keys: List[str], region: str) -> List[Dict[str, Any]]:
    """Delete the L2 `product_prices` rows for each price key in `region`.

    Without this the row survives and `_get_price` re-promotes it into L1 on the
    very next request, so the flush would undo itself. `migrations/012` defines
    only `prices_select` / `prices_insert` policies — the service-role admin
    client bypasses RLS, so REPORT the affected row count rather than assume the
    delete landed, and never let a Supabase failure 500 the route.
    """
    from app.services.database_service import get_admin_supabase_client
    from app.utils.db_offload import run_db

    out: List[Dict[str, Any]] = []
    for key in price_keys:
        entry: Dict[str, Any] = {"product_key": key, "region": region}
        try:
            client = get_admin_supabase_client()
            # Both loop-varying names are bound as defaults so the thunk cannot
            # close over a later iteration's value (run_db may run it on a
            # worker thread when ENABLE_SYNC_DB_OFFLOAD is on).
            response = await run_db(lambda c=client, k=key: (
                c.table("product_prices")
                .delete()
                .eq("product_key", k)
                .eq("region", region)
                .execute()
            ))
            rows = getattr(response, "data", None)
            entry["ok"] = True
            # None = the client returned no representation; the delete may still
            # have landed. Reported as unknown, never as 0.
            entry["rows_deleted"] = len(rows) if isinstance(rows, list) else None
        except Exception as e:  # noqa: BLE001 — reported, not raised (issue #55)
            logger.warning("[FLUSH] L2 product_prices delete failed for %s: %s", key, e)
            entry["ok"] = False
            entry["rows_deleted"] = None
            entry["error"] = str(e)[:300]
        out.append(entry)
    return out


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
    # UNFLAGGED defect repair (issue #55): `parse_product_query` returns
    # `(result, usage)` — every other caller unpacks the tuple, this one did
    # not, so `parsed.get(...)` raised AttributeError and the endpoint 500'd on
    # EVERY real call. (The existing admin-auth test passed only because its
    # mock returns a bare dict.) There is no legitimate input for which the old
    # line returned anything at all, so there is no behaviour to preserve; the
    # unpack is tolerant of both shapes so a dict-returning mock still works.
    if isinstance(parsed, tuple):
        parsed = parsed[0] if parsed else {}
    if not isinstance(parsed, dict):
        parsed = {}
    products = parsed.get("products", [])
    if not products:
        return {"success": False, "error": "Could not parse product name"}

    p = products[0]
    brand, name, variant = p["brand"], p["name"], p.get("variant")

    if not flush_live_price_key_enabled():
        keys = {
            "price": get_price_cache_key(brand, name, variant, FLUSH_REGION),
            "specs": get_specs_cache_key(brand, name, variant),
            "reviews": get_reviews_cache_key(brand, name, variant),
        }

        deleted = {}
        for label, key in keys.items():
            deleted[label] = {"key": key, "deleted": delete_cached(key)}

        return {"success": True, "product": f"{brand} {name}", "flushed": deleted}

    from app.services.price_service import negative_cache_key
    from app.services import cache_service

    price_keys = _flush_price_cache_keys(brand, name, variant, FLUSH_REGION, q, p)

    flushed: Dict[str, Any] = {
        # `price` stays the LIVE key so an existing consumer reading
        # flushed.price.key now sees the key the price path actually writes.
        "price": _flush_delete_key(price_keys[0]),
        "price_additional": [_flush_delete_key(k) for k in price_keys[1:]],
        "negative_cache": [
            _flush_delete_key(negative_cache_key(k)) for k in price_keys
        ],
        "specs": _flush_delete_key(get_specs_cache_key(brand, name, variant)),
        "reviews": _flush_delete_key(get_reviews_cache_key(brand, name, variant)),
    }

    l2 = await _flush_l2_price_rows(price_keys, FLUSH_REGION)

    cache_configured = bool(getattr(cache_service, "redis_client", None))
    notes: List[str] = []
    if not cache_configured:
        notes.append(
            "Redis is not configured in this process — no L1 key was removed."
        )
    if any(not row.get("ok") for row in l2):
        notes.append(
            "One or more L2 product_prices deletes FAILED; the stale row can be "
            "re-promoted into L1 on the next request."
        )
    if any(row.get("ok") and row.get("rows_deleted") is None for row in l2):
        notes.append(
            "An L2 delete returned no row representation — the affected row "
            "count is UNKNOWN, not zero."
        )

    return {
        # Honest: False the moment any leg of the flush could not be completed.
        "success": cache_configured and all(row.get("ok") for row in l2),
        "product": f"{brand} {name}",
        "region": FLUSH_REGION,
        "flushed": flushed,
        "l2_product_prices": l2,
        "cache_configured": cache_configured,
        "notes": notes,
    }


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

