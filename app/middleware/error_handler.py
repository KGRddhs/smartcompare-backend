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
}


def _get_request_id(request: Request) -> str:
    """Extract request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def _build_error_response(status_code: int, message: str, request_id: str) -> JSONResponse:
    """Build standardized error JSON response."""
    code = STATUS_CODE_MAP.get(status_code, "SERVER_ERROR")
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": message,
            "code": code,
            "request_id": request_id,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with unified format."""
    return _build_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        request_id=_get_request_id(request),
    )


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


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded with unified format."""
    return _build_error_response(
        status_code=429,
        message="Rate limit exceeded. Please try again later.",
        request_id=_get_request_id(request),
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
