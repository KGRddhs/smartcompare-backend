"""
Unified error handler -- standardizes ALL error responses to consistent JSON format.

Response format:
{
    "success": false,
    "error": "Human-readable message",
    "code": "ERROR_CODE",
    "request_id": "uuid"
}
"""
import logging
import time
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Map HTTP status codes to error codes
STATUS_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "SERVER_ERROR",
    503: "FEATURE_DISABLED",
}


def _get_request_id(request: Request) -> str:
    """Extract request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def _build_error_response(
    status_code: int,
    message: str,
    request_id: str,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    """Build standardized error JSON response.

    ``retry_after_seconds`` is ADDITIVE and defaults to ``None``: when it is
    None the response is byte-identical to what every other caller has always
    produced. When supplied (the 429 path, W1-9) the same single value is
    emitted BOTH as the RFC 7231 ``Retry-After`` delta-seconds header and as a
    ``retry_after_seconds`` body field, so the two can never disagree.
    """
    code = STATUS_CODE_MAP.get(status_code, "SERVER_ERROR")
    content = {
        "success": False,
        "error": message,
        "code": code,
        "request_id": request_id,
    }
    headers = None
    if retry_after_seconds is not None:
        content["retry_after_seconds"] = retry_after_seconds
        headers = {"Retry-After": str(retry_after_seconds)}
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers,
    )


def _is_structured_detail(detail: object) -> bool:
    """Recognise the project's structured-detail pattern.

    Routes raise ``HTTPException(status, detail={"code": "X", "error": "msg"})``
    so the unified envelope surfaces ``code`` + ``error`` cleanly. We only
    unwrap when BOTH keys are present (or at minimum one of ``error`` /
    ``message``) so other dict-shaped details (e.g. Pydantic-style
    ``{"loc": [...], "msg": "..."}``) still serialize via the legacy
    ``str(detail)`` path. Per qa-referral: don't regress 422 validation
    error shape.
    """
    if not isinstance(detail, dict):
        return False
    has_message_key = (
        isinstance(detail.get("error"), str) or isinstance(detail.get("message"), str)
    )
    has_code_key = isinstance(detail.get("code"), str)
    return has_message_key or has_code_key


def _detail_retry_after(detail: object) -> int | None:
    """The retry window a structured 429 detail carries, or None.

    The brute-force account lockout (``_account_locked_response`` and the
    inline raise in POST /auth/login) computes its own window and puts it in the
    detail as ``retry_after``. W1-9: surface it on the wire under the SAME
    contract as the slowapi 429 -- ``Retry-After`` header + ``retry_after_seconds``
    field -- so the client sees ONE shape for both 429 classes. Only a positive
    int counts; a bool (an int in Python), a string, a float, zero or a negative
    value degrades to today's response rather than shipping a lie.
    """
    if not isinstance(detail, dict):
        return None
    value = detail.get("retry_after")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with unified format.

    Structured details (``{"code": "X", "error": "msg"}``) raised by referral
    routes for 429/400/503/404 are unwrapped to top-level. Plain string
    details and Pydantic-shaped dicts fall through to ``str(detail)``.
    """
    detail = exc.detail
    code = STATUS_CODE_MAP.get(exc.status_code, "SERVER_ERROR")
    if _is_structured_detail(detail):
        # detail is a dict; mypy/runtime safe access
        message = str(detail.get("error") or detail.get("message") or detail)
        if isinstance(detail.get("code"), str):
            code = detail["code"]
    else:
        message = str(detail)

    # W1-9 (ruling 4): a 429 whose structured detail carries a usable
    # retry_after gets the same additive header + field as the slowapi path.
    retry_after = _detail_retry_after(detail) if exc.status_code == 429 else None
    content = {
        "success": False,
        "error": message,
        "code": code,
        "request_id": _get_request_id(request),
    }
    headers = None
    if retry_after is not None:
        content["retry_after_seconds"] = retry_after
        headers = {"Retry-After": str(retry_after)}
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with unified format."""
    # Summarize validation errors into a readable message
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = " → ".join(str(loc) for loc in first.get("loc", []))
        msg = first.get("msg", "Invalid value")
        message = f"Validation error: {field}: {msg}"
    else:
        message = "Invalid request"

    return _build_error_response(
        status_code=422,
        message=message,
        request_id=_get_request_id(request),
    )


def _retry_after_seconds(request: Request) -> int | None:
    """Seconds until the tripped limit's window resets, or None if unknown.

    Reuses slowapi rather than reinventing it. slowapi stashes the limit it
    tripped on as ``request.state.view_rate_limit`` -- MEASURED on the real app,
    a ``(RateLimitItem, [key, scope])`` pair -- BEFORE raising, and its own
    ``_inject_headers`` turns that into a delta with
    ``int(1 + reset_time - time.time())`` over the limiter storage's real window
    stats. We mirror that arithmetic exactly (its ``+ 1`` is a deliberate
    round-UP: without it a truncated delta sends the client back a fraction of a
    second EARLY, straight into another 429) instead of flipping
    ``headers_enabled=True`` on the Limiter, which -- also measured -- would put
    ``X-RateLimit-*`` and ``Retry-After`` on every SUCCESSFUL response of every
    limited route.

    MEASURED consequence, recorded because it deviates from this unit's spec:
    that ``+ 1`` means a 60 s window can yield **61**, not <= 60 (sampled over 40
    fresh 1/minute windows here: {61: 22, 60: 18}). The value is bounded at
    ``window + 1`` below, so an epoch -- ``Retry-After: 1788874942``, which is
    worse than no header at all -- is refused rather than shipped.
    """
    state = getattr(request.state, "view_rate_limit", None)
    if not state:
        return None

    limit_item, args = state[0], state[1]
    limiter = request.app.state.limiter
    reset_time, _remaining = limiter.limiter.get_window_stats(limit_item, *args)

    seconds = int(1 + reset_time - time.time())
    if seconds <= 0 or seconds > limit_item.get_expiry() + 1:
        # Already elapsed, or a window the tripped limit cannot possibly have
        # produced (a storage returning an epoch). Say nothing rather than lie.
        return None
    return seconds


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded with unified format.

    Additive since W1-9: the 429 carries the real retry window as both a
    ``Retry-After`` header and a ``retry_after_seconds`` body field, so a client
    that trips a limit knows when to come back instead of hammering or giving up.

    Fail-safe: if the window cannot be read for ANY reason (storage error,
    missing state, a slowapi shape change) we log and return today's exact 429.
    A rate-limit response must never become a 500.
    """
    try:
        retry_after = _retry_after_seconds(request)
    except Exception as exc_window:  # noqa: BLE001 - a 429 must never 500
        logger.warning(
            f"Rate-limit retry window unreadable "
            f"({type(exc_window).__name__}: {exc_window}); serving 429 without it"
        )
        retry_after = None

    return _build_error_response(
        status_code=429,
        message="Rate limit exceeded. Please try again later.",
        request_id=_get_request_id(request),
        retry_after_seconds=retry_after,
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return clean 500 responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            request_id = _get_request_id(request)

            logger.error(
                f"Unhandled {type(exc).__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
                exc_info=True,
            )

            # Send to Sentry if available
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass

            return _build_error_response(
                status_code=500,
                message="Internal server error",
                request_id=request_id,
            )
