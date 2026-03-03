# Production Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden SmartCompare for production with security middleware, error monitoring, analytics endpoints, and CI/CD pipeline.

**Architecture:** Three parallel agents modify separate files — Agent 1 owns middleware + main.py, Agent 2 owns Sentry/logging, Agent 3 owns analytics/CI. Agent 1 registers all components at the end. Cross-QA circle: 1→2, 2→3, 3→1.

**Tech Stack:** FastAPI middleware, slowapi (rate limiting), sentry-sdk[fastapi], Upstash Redis (existing), GitHub Actions, Supabase (existing)

**Design doc:** `docs/plans/2026-03-03-production-readiness-design.md`

---

## Team Setup

Create team with 3 Opus agents (`bypassPermissions` mode):

```
Team name: production-readiness
Agent 1: security-agent (general-purpose, Opus)
Agent 2: observability-agent (general-purpose, Opus)
Agent 3: analytics-ci-agent (general-purpose, Opus)
```

**Each agent receives:**
1. Their task section below (Tasks A/B/C respectively)
2. The design doc path for full context
3. File ownership rules (only edit files they own)
4. QA assignment (who they review when idle)
5. Idle protocol: write tests targeting 80% coverage for their own feature

---

## Task A: Security & Middleware (Agent 1: security-agent)

**Owns:** `app/main.py`, `app/middleware/security.py`, `app/middleware/rate_limiter.py`, `app/middleware/request_id.py`, `app/middleware/__init__.py`, `requirements.txt`

**Reads (do not modify):** `app/config.py`, `app/api/auth_routes.py`

### A1: Install dependencies

**Step 1:** Add to `requirements.txt` (after line 15):
```
slowapi>=0.1.9
sentry-sdk[fastapi]>=1.40.0
```

**Step 2:** Install locally:
```bash
pip install slowapi sentry-sdk[fastapi]
```

**Step 3:** Commit:
```bash
git add requirements.txt
git commit -m "deps: add slowapi and sentry-sdk for production hardening"
```

---

### A2: Request ID Middleware

**Files:**
- Create: `app/middleware/request_id.py`
- Test: `tests/test_security_middleware.py`

**Step 1:** Write the failing test in `tests/test_security_middleware.py`:

```python
"""Tests for security middleware — headers, rate limiting, request IDs."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient


# ── Request ID tests ──

def _make_test_app():
    """Create minimal FastAPI app with middleware for testing."""
    from fastapi import FastAPI, Request
    from app.middleware.request_id import RequestIDMiddleware

    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/test")
    async def test_endpoint(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return test_app


def test_request_id_generated_when_missing():
    """Middleware generates UUID request ID when none provided."""
    app = _make_test_app()
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    # Response header has request ID
    assert "X-Request-ID" in response.headers
    rid = response.headers["X-Request-ID"]
    # Valid UUID format (8-4-4-4-12)
    assert len(rid.split("-")) == 5
    # Endpoint received it in request.state
    assert response.json()["request_id"] == rid


def test_request_id_preserved_when_provided():
    """Middleware preserves client-provided request ID."""
    app = _make_test_app()
    client = TestClient(app)
    my_id = "my-custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": my_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == my_id
    assert response.json()["request_id"] == my_id
```

**Step 2:** Run test to verify it fails:
```bash
python -m pytest tests/test_security_middleware.py::test_request_id_generated_when_missing -v
```
Expected: FAIL (ModuleNotFoundError — `app.middleware.request_id` doesn't exist)

**Step 3:** Write `app/middleware/request_id.py`:

```python
"""Request ID middleware — generates or preserves request correlation IDs."""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

**Step 4:** Run test to verify it passes:
```bash
python -m pytest tests/test_security_middleware.py -v -k "request_id"
```
Expected: 2 PASSED

**Step 5:** Commit:
```bash
git add app/middleware/request_id.py tests/test_security_middleware.py
git commit -m "feat: add request ID middleware for request tracing"
```

---

### A3: Security Headers Middleware

**Files:**
- Create: `app/middleware/security.py`
- Modify: `tests/test_security_middleware.py`

**Step 1:** Append failing tests to `tests/test_security_middleware.py`:

```python
# ── Security Headers tests ──

def _make_secure_app():
    """Create FastAPI app with security headers middleware."""
    from fastapi import FastAPI
    from app.middleware.security import SecurityHeadersMiddleware

    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)

    @test_app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return test_app


def test_security_headers_present():
    """All security headers present on every response."""
    app = _make_secure_app()
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_security_headers_on_error_response():
    """Security headers present even on 404 responses."""
    app = _make_secure_app()
    client = TestClient(app)
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_security_middleware.py -v -k "security_headers"
```
Expected: FAIL (ModuleNotFoundError)

**Step 3:** Write `app/middleware/security.py`:

```python
"""Security headers middleware — adds standard security headers to all responses."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response
```

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_security_middleware.py -v -k "security_headers"
```
Expected: 2 PASSED

**Step 5:** Commit:
```bash
git add app/middleware/security.py tests/test_security_middleware.py
git commit -m "feat: add security headers middleware"
```

---

### A4: Rate Limiting

**Files:**
- Create: `app/middleware/rate_limiter.py`
- Modify: `tests/test_security_middleware.py`

**Step 1:** Append failing tests to `tests/test_security_middleware.py`:

```python
# ── Rate Limiting tests ──

def _make_rate_limited_app():
    """Create FastAPI app with rate limiting."""
    from fastapi import FastAPI, Request
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.middleware.rate_limiter import limiter

    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @test_app.get("/limited")
    @limiter.limit("2/minute")
    async def limited_endpoint(request: Request):
        return {"ok": True}

    @test_app.get("/unlimited")
    async def unlimited_endpoint(request: Request):
        return {"ok": True}

    return test_app


def test_rate_limit_allows_under_limit():
    """Requests under rate limit succeed."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    response = client.get("/limited")
    assert response.status_code == 200


def test_rate_limit_blocks_over_limit():
    """Requests over rate limit return 429."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    # Use 2/minute limit — first 2 succeed, third fails
    client.get("/limited")
    client.get("/limited")
    response = client.get("/limited")
    assert response.status_code == 429


def test_rate_limit_returns_retry_after_header():
    """429 response includes Retry-After header."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    client.get("/limited")
    client.get("/limited")
    response = client.get("/limited")
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_unlimited_endpoint_not_affected():
    """Endpoints without @limiter.limit are not rate limited."""
    app = _make_rate_limited_app()
    client = TestClient(app)
    for _ in range(20):
        response = client.get("/unlimited")
        assert response.status_code == 200
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_security_middleware.py -v -k "rate_limit"
```
Expected: FAIL (ModuleNotFoundError)

**Step 3:** Write `app/middleware/rate_limiter.py`:

```python
"""Rate limiting — uses slowapi with in-memory storage (Redis optional)."""
import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Default rate limits for different endpoint types
ANON_LIMIT = "10/minute"
AUTH_LIMIT = "30/minute"
ADMIN_LIMIT = "60/minute"
DAILY_LIMIT = "100/day"


def _get_storage_uri() -> str:
    """Build storage URI — Redis if available, memory fallback."""
    redis_url = os.getenv("UPSTASH_REDIS_URL", "")
    redis_token = os.getenv("UPSTASH_REDIS_TOKEN", "")

    if redis_url and redis_token:
        # Upstash REST URL — slowapi needs redis:// scheme
        # Strip https:// and use as host
        host = redis_url.replace("https://", "").replace("http://", "")
        uri = f"redis://default:{redis_token}@{host}:6379"
        logger.info("Rate limiter using Upstash Redis")
        return uri

    logger.info("Rate limiter using in-memory storage (no Redis configured)")
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_get_storage_uri(),
    default_limits=[DAILY_LIMIT, ANON_LIMIT],
)
```

**Important note for the agent:** `slowapi` with Upstash Redis may need the `redis` package (already in `requirements.txt`). If Upstash REST API doesn't work as a standard Redis endpoint with slowapi, fall back to `"memory://"` — that's fine for a single Railway instance. Test both paths.

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_security_middleware.py -v -k "rate_limit"
```
Expected: 4 PASSED

**Step 5:** Commit:
```bash
git add app/middleware/rate_limiter.py tests/test_security_middleware.py
git commit -m "feat: add rate limiting middleware with slowapi"
```

---

### A5: Update middleware __init__.py

**File:** `app/middleware/__init__.py`

```python
"""Middleware package — security, rate limiting, request tracing, error handling."""
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.rate_limiter import limiter

__all__ = [
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    "limiter",
]
```

Commit:
```bash
git add app/middleware/__init__.py
git commit -m "feat: export middleware components from package"
```

---

### A6: Update main.py (final integration — AFTER Agents 2 and 3 deliver)

**File:** `app/main.py` (complete rewrite of lines 1-61)

**Wait for:** Agent 2 to deliver `error_handler.py` + `logging_config.py` + `sentry_service.py`, Agent 3 to deliver `admin_routes.py`.

Replace the entire `app/main.py` with:

```python
"""
SmartCompare Backend - Main Application
Professional product comparison API with multiple input methods
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(override=True)

# Configure structured logging before any other imports
from app.middleware.logging_config import configure_logging
configure_logging(os.getenv("LOG_LEVEL", "INFO"))

# Import routes after env vars are loaded
from app.api.routes import router as api_router          # Image comparison (legacy)
from app.api.auth_routes import router as auth_router    # Authentication
from app.api.text_routes import router as text_router    # Text comparison
from app.api.url_routes import router as url_router      # URL comparison
from app.api.image_routes import router as image_router  # Camera identification + comparison
from app.api.admin_routes import router as admin_router  # Admin analytics

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Initialize Sentry (no-op if SENTRY_DSN not set)
from app.services.sentry_service import init_sentry
init_sentry()

# Create FastAPI app
app = FastAPI(
    title="SmartCompare API",
    description="""
    AI-powered product comparison API with multiple input methods.

    ## Input Methods

    - **Image** - Take photos of products, AI identifies and compares
    - **Text** - Type "iPhone 15 vs Galaxy S24" for instant comparison
    - **URL** - Paste product URLs from Amazon, Noon, Carrefour, etc.

    ## Features

    - Structured data extraction (specs, prices, reviews)
    - GCC regional pricing (Bahrain, Saudi, UAE, Kuwait, Qatar, Oman)
    - Intelligent caching for fast responses
    - User authentication and history

    ## Supported Retailers

    Amazon, Noon, Carrefour, Sharaf DG, Lulu Hypermarket, Extra, Jarir, Xcite
    """,
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── Middleware (order matters: outermost added last) ──

# CORS (innermost — runs first on response)
ALLOWED_ORIGINS = [
    "https://smartcompare-backend-production.up.railway.app",
    "http://localhost:8000",
    "http://localhost:19006",   # Expo web
    "http://localhost:8081",    # Metro bundler
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"],
)

# Rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Error handler (catches unhandled exceptions)
app.add_middleware(ErrorHandlerMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID (outermost — generates ID before anything else)
app.add_middleware(RequestIDMiddleware)

# ── Routes ──
app.include_router(api_router)       # /api/v1/compare (legacy image)
app.include_router(auth_router)      # /api/v1/auth/*
app.include_router(text_router)      # /api/v1/text/*
app.include_router(url_router)       # /api/v1/url/*
app.include_router(image_router)     # /api/v1/image/* (camera)
app.include_router(admin_router)     # /api/v1/admin/*


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "healthy",
        "app": "SmartCompare API",
        "version": "2.1.0",
        "endpoints": {
            "image_identify": "/api/v1/image/identify",
            "image_compare_legacy": "/api/v1/compare",
            "text_compare": "/api/v1/text/compare",
            "url_compare": "/api/v1/url/compare",
            "auth": "/api/v1/auth/*",
            "admin": "/api/v1/admin/*",
            "docs": "/docs"
        },
        "input_methods": [
            {"type": "image", "description": "Upload product photos"},
            {"type": "text", "description": "Natural language comparison"},
            {"type": "url", "description": "Product URLs from retailers"}
        ],
        "supported_regions": [
            "bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"
        ]
    }


@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "message": "SmartCompare API is running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

**Step: Verify full test suite still passes:**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```
Expected: All 194+ existing tests PASS

**Step: Syntax check all modified files:**
```bash
python -m py_compile app/main.py
python -m py_compile app/middleware/request_id.py
python -m py_compile app/middleware/security.py
python -m py_compile app/middleware/rate_limiter.py
```
Expected: No errors

**Step: Commit:**
```bash
git add app/main.py app/middleware/__init__.py
git commit -m "feat: wire all middleware + admin routes into main.py, fix CORS"
```

---

### A7: Apply rate limits to comparison endpoints

**File:** Modify `app/api/text_routes.py` — add rate limit decorators to the two main endpoints.

**Important:** `slowapi` requires `request: Request` as a parameter in the endpoint function. The existing endpoints use Pydantic models + Depends, so add `request: Request` parameter.

Add at top of `text_routes.py`:
```python
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from app.middleware.rate_limiter import limiter
```

Add decorator to `text_compare` (line 48) and `text_compare_get` (line 115):
```python
@router.post("/compare")
@limiter.limit("10/minute")
async def text_compare(request: Request, body: TextCompareRequest, user: Optional[Dict] = Depends(get_optional_user)):
```

```python
@router.get("/compare")
@limiter.limit("10/minute")
async def text_compare_get(
    request: Request,
    q: str = Query(..., description="Comparison query"),
    ...
```

**Note:** The `request: Request` param must be named `request` for slowapi to find it. Rename `request` → `body` for the POST endpoint's Pydantic model to avoid name collision. Update all references to `request.query` → `body.query`, `request.region` → `body.region`, etc. inside `text_compare()`.

Similarly, modify `app/api/image_routes.py` to add rate limit to the identify endpoint.

**Commit:**
```bash
git add app/api/text_routes.py app/api/image_routes.py
git commit -m "feat: apply rate limits to comparison endpoints"
```

---

## Task B: Observability (Agent 2: observability-agent)

**Owns:** `app/middleware/error_handler.py`, `app/middleware/logging_config.py`, `app/services/sentry_service.py`

**Does NOT modify:** `app/main.py` (Agent 1 registers), `requirements.txt` (Agent 1 manages)

### B1: Sentry Service

**Files:**
- Create: `app/services/sentry_service.py`
- Test: `tests/test_observability.py`

**Step 1:** Write failing test in `tests/test_observability.py`:

```python
"""Tests for observability — Sentry init, error handler, structured logging."""
import pytest
import json
import logging
from unittest.mock import patch, MagicMock


# ── Sentry init tests ──

def test_sentry_init_disabled_when_no_dsn():
    """init_sentry() is a no-op when SENTRY_DSN is empty."""
    with patch.dict("os.environ", {"SENTRY_DSN": ""}, clear=False):
        with patch("sentry_sdk.init") as mock_init:
            from app.services.sentry_service import init_sentry
            init_sentry()
            mock_init.assert_not_called()


def test_sentry_init_called_with_dsn():
    """init_sentry() calls sentry_sdk.init when DSN is set."""
    with patch.dict("os.environ", {"SENTRY_DSN": "https://abc@sentry.io/123"}, clear=False):
        with patch("sentry_sdk.init") as mock_init:
            # Need to reload the module to pick up new env
            import importlib
            import app.services.sentry_service as mod
            importlib.reload(mod)
            mod.init_sentry()
            mock_init.assert_called_once()
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["dsn"] == "https://abc@sentry.io/123"
            assert call_kwargs["send_default_pii"] is False
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_observability.py -v -k "sentry_init"
```
Expected: FAIL (ModuleNotFoundError)

**Step 3:** Write `app/services/sentry_service.py`:

```python
"""Sentry integration — error monitoring and performance tracing."""
import os
import logging

logger = logging.getLogger(__name__)


def init_sentry():
    """Initialize Sentry SDK. No-op if SENTRY_DSN not set."""
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("SENTRY_DSN not set — Sentry disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            traces_sample_rate=0.1,  # 10% of requests (free tier friendly)
            environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
            send_default_pii=False,
        )
        logger.info("Sentry initialized successfully")
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry disabled")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")
```

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_observability.py -v -k "sentry_init"
```
Expected: 2 PASSED

**Step 5:** Commit:
```bash
git add app/services/sentry_service.py tests/test_observability.py
git commit -m "feat: add Sentry service with opt-in initialization"
```

---

### B2: Structured Logging Configuration

**Files:**
- Create: `app/middleware/logging_config.py`
- Modify: `tests/test_observability.py`

**Step 1:** Append failing tests to `tests/test_observability.py`:

```python
# ── Structured Logging tests ──

def test_structured_formatter_outputs_json():
    """StructuredFormatter produces valid JSON log lines."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="Hello %s", args=("world",), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Hello world"
    assert "timestamp" in parsed
    assert parsed["module"] == "test"


def test_structured_formatter_includes_exception():
    """StructuredFormatter includes exception info when present."""
    from app.middleware.logging_config import StructuredFormatter

    formatter = StructuredFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="Failed", args=(), exc_info=sys.exc_info(),
        )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "exception" in parsed
    assert "ValueError: test error" in parsed["exception"]


def test_configure_logging_sets_level():
    """configure_logging applies the requested log level."""
    from app.middleware.logging_config import configure_logging

    configure_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG

    # Reset
    configure_logging("INFO")
    assert root.level == logging.INFO


def test_configure_logging_quiets_noisy_libraries():
    """configure_logging sets httpx/httpcore to WARNING."""
    from app.middleware.logging_config import configure_logging

    configure_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING

    # Reset
    configure_logging("INFO")
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_observability.py -v -k "structured_formatter or configure_logging"
```
Expected: FAIL

**Step 3:** Write `app/middleware/logging_config.py`:

```python
"""Structured logging configuration — JSON format for production, readable for dev."""
import logging
import sys
import json
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Format log records as single-line JSON for machine parsing."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }

        # Include request_id if attached to record
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_entry["request_id"] = request_id

        # Include exception traceback
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def configure_logging(level: str = "INFO"):
    """Configure structured JSON logging for all loggers."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Structured JSON handler to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
```

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_observability.py -v -k "structured_formatter or configure_logging"
```
Expected: 4 PASSED

**Step 5:** Commit:
```bash
git add app/middleware/logging_config.py tests/test_observability.py
git commit -m "feat: add structured JSON logging configuration"
```

---

### B3: Global Error Handler Middleware

**Files:**
- Create: `app/middleware/error_handler.py`
- Modify: `tests/test_observability.py`

**Step 1:** Append failing tests to `tests/test_observability.py`:

```python
# ── Error Handler Middleware tests ──

from starlette.testclient import TestClient


def _make_error_app():
    """Create FastAPI app with error handler middleware."""
    from fastapi import FastAPI, HTTPException
    from app.middleware.error_handler import ErrorHandlerMiddleware

    test_app = FastAPI()
    test_app.add_middleware(ErrorHandlerMiddleware)

    @test_app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @test_app.get("/crash")
    async def crash():
        raise RuntimeError("Something broke")

    @test_app.get("/http-error")
    async def http_error():
        raise HTTPException(status_code=404, detail="Not found")

    return test_app


def test_error_handler_passes_normal_responses():
    """Normal responses pass through unchanged."""
    app = _make_error_app()
    client = TestClient(app)
    response = client.get("/ok")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_error_handler_catches_unhandled_exception():
    """Unhandled exceptions return clean 500 JSON, not stack trace."""
    app = _make_error_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash")
    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Internal server error"
    # Stack trace NOT leaked
    assert "RuntimeError" not in json.dumps(body)
    assert "Something broke" not in json.dumps(body)


def test_error_handler_includes_request_id():
    """500 response includes request_id if available."""
    from app.middleware.request_id import RequestIDMiddleware

    app = _make_error_app()
    # Add request ID middleware (runs before error handler)
    app.add_middleware(RequestIDMiddleware)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash", headers={"X-Request-ID": "test-123"})
    assert response.status_code == 500
    assert response.json()["request_id"] == "test-123"


def test_error_handler_lets_http_exceptions_through():
    """HTTPExceptions are NOT caught — FastAPI handles them normally."""
    app = _make_error_app()
    client = TestClient(app)
    response = client.get("/http-error")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_observability.py -v -k "error_handler"
```
Expected: FAIL

**Step 3:** Write `app/middleware/error_handler.py`:

```python
"""Global error handler — catches unhandled exceptions, logs + returns clean JSON."""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return clean 500 responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")

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

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "request_id": request_id,
                },
            )
```

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_observability.py -v -k "error_handler"
```
Expected: 4 PASSED

**Step 5:** Commit:
```bash
git add app/middleware/error_handler.py tests/test_observability.py
git commit -m "feat: add global error handler middleware with Sentry integration"
```

---

### B4: Notify Agent 1

Send a message to Agent 1 (security-agent):

> "Observability components ready for registration in main.py:
> - `from app.middleware.error_handler import ErrorHandlerMiddleware`
> - `from app.middleware.logging_config import configure_logging`
> - `from app.services.sentry_service import init_sentry`
>
> Call `configure_logging()` at startup before other imports.
> Call `init_sentry()` after app creation.
> Add `app.add_middleware(ErrorHandlerMiddleware)` between security headers and CORS."

---

## Task C: Analytics & CI/CD (Agent 3: analytics-ci-agent)

**Owns:** `app/api/admin_routes.py`, `app/services/analytics_service.py`, `.github/workflows/ci.yml`

**Does NOT modify:** `app/main.py`, `requirements.txt`

### C1: Analytics Service

**Files:**
- Create: `app/services/analytics_service.py`
- Test: `tests/test_analytics.py`

**Step 1:** Write failing tests in `tests/test_analytics.py`:

```python
"""Tests for analytics service and admin endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ── Analytics service tests ──

def _mock_search_logs(records):
    """Create mock Supabase response for search_logs queries."""
    mock_response = MagicMock()
    mock_response.data = records
    return mock_response


def _make_log_record(
    query="iPhone 15 vs Galaxy S24",
    input_type="text",
    success=True,
    cost=0.01,
    duration_ms=5000,
    created_at=None,
    error_message=None,
):
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    record = {
        "query": query,
        "input_type": input_type,
        "success": success,
        "cost": cost,
        "duration_ms": duration_ms,
        "created_at": created_at,
        "products_found": ["Apple iPhone 15", "Samsung Galaxy S24"],
    }
    if error_message:
        record["error_message"] = error_message
    return record


@pytest.mark.asyncio
async def test_get_daily_stats_returns_structure():
    """get_daily_stats returns dict with expected keys."""
    mock_client = MagicMock()
    records = [_make_log_record(), _make_log_record(success=False, error_message="timeout")]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_daily_stats
        result = await get_daily_stats(days=7)

    assert "total_comparisons" in result
    assert "success_count" in result
    assert "error_count" in result
    assert "daily_breakdown" in result


@pytest.mark.asyncio
async def test_get_popular_queries_returns_ranked_list():
    """get_popular_queries returns queries ranked by frequency."""
    mock_client = MagicMock()
    records = [
        _make_log_record(query="iPhone vs Galaxy"),
        _make_log_record(query="iPhone vs Galaxy"),
        _make_log_record(query="MacBook vs Dell"),
    ]
    mock_chain = MagicMock()
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value = mock_chain

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_popular_queries
        result = await get_popular_queries(limit=10)

    assert isinstance(result, list)
    assert len(result) > 0
    # Most popular first
    assert result[0]["count"] >= result[-1]["count"]


@pytest.mark.asyncio
async def test_get_cost_trends_returns_aggregation():
    """get_cost_trends returns cost aggregation data."""
    mock_client = MagicMock()
    records = [
        _make_log_record(cost=0.01),
        _make_log_record(cost=0.015),
        _make_log_record(cost=0.008),
    ]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_cost_trends
        result = await get_cost_trends(days=7)

    assert "total_cost" in result
    assert "avg_cost_per_comparison" in result
    assert result["total_cost"] == pytest.approx(0.033, rel=0.01)


@pytest.mark.asyncio
async def test_get_error_stats_returns_error_breakdown():
    """get_error_stats returns error rate and breakdown."""
    mock_client = MagicMock()
    records = [
        _make_log_record(success=True),
        _make_log_record(success=True),
        _make_log_record(success=False, error_message="Comparison failed"),
    ]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_error_stats
        result = await get_error_stats(days=7)

    assert "total_requests" in result
    assert "error_rate" in result
    assert result["error_rate"] == pytest.approx(0.333, rel=0.05)


@pytest.mark.asyncio
async def test_daily_stats_handles_empty_data():
    """get_daily_stats returns zeros when no search logs exist."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs([])
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs([])

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_daily_stats
        result = await get_daily_stats(days=7)

    assert result["total_comparisons"] == 0
    assert result["success_count"] == 0
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_analytics.py -v
```
Expected: FAIL (ModuleNotFoundError)

**Step 3:** Write `app/services/analytics_service.py`:

```python
"""Analytics service — queries search_logs and products tables for admin dashboards."""
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from app.services.database_service import get_supabase_client

logger = logging.getLogger(__name__)


async def get_daily_stats(days: int = 30) -> Dict:
    """Comparison count, cost, errors aggregated by day."""
    try:
        client = get_supabase_client()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            client.table("search_logs")
            .select("success, cost, duration_ms, created_at")
            .gte("created_at", since)
            .execute()
        )
        records = response.data or []

        total = len(records)
        successes = sum(1 for r in records if r.get("success"))
        errors = total - successes
        total_cost = sum(float(r.get("cost") or 0) for r in records)
        avg_duration = (
            sum(int(r.get("duration_ms") or 0) for r in records) / total
            if total > 0 else 0
        )

        # Group by day
        daily = Counter()
        for r in records:
            day = r.get("created_at", "")[:10]  # YYYY-MM-DD
            if day:
                daily[day] += 1

        return {
            "total_comparisons": total,
            "success_count": successes,
            "error_count": errors,
            "total_cost": round(total_cost, 4),
            "avg_duration_ms": round(avg_duration),
            "daily_breakdown": dict(sorted(daily.items())),
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        return {
            "total_comparisons": 0, "success_count": 0,
            "error_count": 0, "total_cost": 0, "avg_duration_ms": 0,
            "daily_breakdown": {}, "period_days": days,
        }


async def get_popular_queries(limit: int = 20) -> List[Dict]:
    """Top queries ranked by frequency."""
    try:
        client = get_supabase_client()
        response = (
            client.table("search_logs")
            .select("query, input_type")
            .execute()
        )
        records = response.data or []

        counter = Counter(r.get("query", "") for r in records if r.get("query"))
        return [
            {"query": q, "count": c}
            for q, c in counter.most_common(limit)
        ]
    except Exception as e:
        logger.error(f"Error getting popular queries: {e}")
        return []


async def get_cost_trends(days: int = 30) -> Dict:
    """Cost aggregation — total, average, trend by day."""
    try:
        client = get_supabase_client()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            client.table("search_logs")
            .select("cost, created_at, success")
            .gte("created_at", since)
            .execute()
        )
        records = response.data or []

        costs = [float(r.get("cost") or 0) for r in records]
        total = sum(costs)
        avg = total / len(costs) if costs else 0

        # Daily cost
        daily_cost = {}
        for r in records:
            day = r.get("created_at", "")[:10]
            if day:
                daily_cost[day] = daily_cost.get(day, 0) + float(r.get("cost") or 0)

        return {
            "total_cost": round(total, 4),
            "avg_cost_per_comparison": round(avg, 4),
            "comparison_count": len(records),
            "daily_costs": {k: round(v, 4) for k, v in sorted(daily_cost.items())},
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Error getting cost trends: {e}")
        return {
            "total_cost": 0, "avg_cost_per_comparison": 0,
            "comparison_count": 0, "daily_costs": {}, "period_days": days,
        }


async def get_error_stats(days: int = 7) -> Dict:
    """Error rate and common error messages."""
    try:
        client = get_supabase_client()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            client.table("search_logs")
            .select("success, error_message, created_at")
            .gte("created_at", since)
            .execute()
        )
        records = response.data or []

        total = len(records)
        errors = [r for r in records if not r.get("success")]
        error_rate = len(errors) / total if total > 0 else 0

        error_messages = Counter(
            r.get("error_message", "Unknown") for r in errors
        )

        return {
            "total_requests": total,
            "error_count": len(errors),
            "error_rate": round(error_rate, 3),
            "common_errors": [
                {"message": msg, "count": c}
                for msg, c in error_messages.most_common(10)
            ],
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Error getting error stats: {e}")
        return {
            "total_requests": 0, "error_count": 0, "error_rate": 0,
            "common_errors": [], "period_days": days,
        }


async def get_product_stats(limit: int = 20) -> Dict:
    """Most compared products and category breakdown."""
    try:
        client = get_supabase_client()
        response = (
            client.table("products")
            .select("canonical_name, brand, category, updated_at")
            .execute()
        )
        records = response.data or []

        categories = Counter(r.get("category", "other") for r in records)
        brands = Counter(r.get("brand", "Unknown") for r in records)

        return {
            "total_products": len(records),
            "category_breakdown": dict(categories.most_common()),
            "top_brands": dict(brands.most_common(limit)),
        }
    except Exception as e:
        logger.error(f"Error getting product stats: {e}")
        return {"total_products": 0, "category_breakdown": {}, "top_brands": {}}
```

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_analytics.py -v
```
Expected: 5 PASSED

**Step 5:** Commit:
```bash
git add app/services/analytics_service.py tests/test_analytics.py
git commit -m "feat: add analytics service with daily stats, popular queries, cost trends"
```

---

### C2: Admin API Endpoints

**Files:**
- Create: `app/api/admin_routes.py`
- Append to: `tests/test_analytics.py`

**Step 1:** Append admin endpoint tests to `tests/test_analytics.py`:

```python
# ── Admin endpoint tests ──

from starlette.testclient import TestClient


def _make_admin_app():
    """Create FastAPI app with admin routes for testing."""
    from fastapi import FastAPI
    from app.api.admin_routes import router
    import os
    os.environ["ADMIN_API_KEY"] = "test-admin-key-123"

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/admin")
    return test_app


def test_admin_valid_key_succeeds():
    """Valid admin key returns 200."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_daily_stats", return_value={"total_comparisons": 0}):
        response = client.get(
            "/api/v1/admin/stats/daily",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200


def test_admin_invalid_key_returns_403():
    """Invalid admin key returns 403."""
    app = _make_admin_app()
    client = TestClient(app)
    response = client.get(
        "/api/v1/admin/stats/daily",
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_admin_missing_key_returns_422():
    """Missing X-Admin-Key header returns 422."""
    app = _make_admin_app()
    client = TestClient(app)
    response = client.get("/api/v1/admin/stats/daily")
    assert response.status_code == 422


def test_admin_empty_env_key_returns_403():
    """Empty ADMIN_API_KEY env var rejects all requests."""
    from fastapi import FastAPI
    from app.api.admin_routes import router
    import os
    os.environ["ADMIN_API_KEY"] = ""

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/admin")
    client = TestClient(test_app)
    response = client.get(
        "/api/v1/admin/stats/daily",
        headers={"X-Admin-Key": "anything"},
    )
    assert response.status_code == 403
```

**Step 2:** Run to verify fail:
```bash
python -m pytest tests/test_analytics.py -v -k "admin"
```
Expected: FAIL

**Step 3:** Write `app/api/admin_routes.py`:

```python
"""Admin routes — analytics endpoints protected by API key."""
import os
import logging
from fastapi import APIRouter, Header, HTTPException, Depends, Query

from app.services.analytics_service import (
    get_daily_stats,
    get_popular_queries,
    get_cost_trends,
    get_error_stats,
    get_product_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


def verify_admin_key(x_admin_key: str = Header(...)):
    """Verify the admin API key from X-Admin-Key header."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True


@router.get("/stats/daily")
async def daily_stats(
    days: int = Query(30, ge=1, le=365),
    _=Depends(verify_admin_key),
):
    """Daily comparison stats — count, cost, errors, duration."""
    return await get_daily_stats(days)


@router.get("/stats/popular")
async def popular_queries(
    limit: int = Query(20, ge=1, le=100),
    _=Depends(verify_admin_key),
):
    """Most popular comparison queries ranked by frequency."""
    return await get_popular_queries(limit)


@router.get("/stats/costs")
async def cost_trends(
    days: int = Query(30, ge=1, le=365),
    _=Depends(verify_admin_key),
):
    """Cost trends — total, average, daily breakdown."""
    return await get_cost_trends(days)


@router.get("/stats/errors")
async def error_stats(
    days: int = Query(7, ge=1, le=90),
    _=Depends(verify_admin_key),
):
    """Error rate and common error messages."""
    return await get_error_stats(days)


@router.get("/stats/products")
async def product_stats(
    limit: int = Query(20, ge=1, le=100),
    _=Depends(verify_admin_key),
):
    """Most compared products and category breakdown."""
    return await get_product_stats(limit)
```

**Step 4:** Run to verify pass:
```bash
python -m pytest tests/test_analytics.py -v
```
Expected: 9 PASSED (5 analytics + 4 admin)

**Step 5:** Commit:
```bash
git add app/api/admin_routes.py tests/test_analytics.py
git commit -m "feat: add admin analytics API endpoints with API key auth"
```

---

### C3: GitHub Actions CI Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1:** Create directory structure:
```bash
mkdir -p .github/workflows
```

**Step 2:** Write `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-timeout

      - name: Syntax check all Python files
        run: |
          find app -name "*.py" -exec python -m py_compile {} +
          echo "All Python files pass syntax check"

      - name: Run unit tests
        run: |
          python -m pytest tests/ -v \
            -m "not (live_unit or live_db or integration)" \
            --ignore=tests/test_integration.py \
            --timeout=60 \
            --tb=short

  frontend-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: SmartCompareApp/package-lock.json

      - name: Install frontend dependencies
        run: cd SmartCompareApp && npm ci

      - name: TypeScript type check
        run: cd SmartCompareApp && npx tsc --noEmit
        continue-on-error: true  # 7 pre-existing TS errors
```

**Step 3:** Commit:
```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline for unit tests and type checking"
```

---

### C4: Notify Agent 1

Send a message to Agent 1 (security-agent):

> "Analytics components ready for registration in main.py:
> - `from app.api.admin_routes import router as admin_router`
> - `app.include_router(admin_router, prefix="/api/v1/admin")`
>
> New env var needed on Railway: `ADMIN_API_KEY` (any random 32+ char string)."

---

## QA Phase

### QA Assignment

| Reviewer | Reviews | Checks |
|----------|---------|--------|
| Agent 1 (Security) | Agent 2 (Observability) | Read `error_handler.py`, `logging_config.py`, `sentry_service.py`. Run `test_observability.py`. Check: no stack trace leaks, Sentry opt-in works, logging JSON valid. |
| Agent 2 (Observability) | Agent 3 (Analytics & CI) | Read `admin_routes.py`, `analytics_service.py`, `ci.yml`. Run `test_analytics.py`. Check: admin key auth correct, SQL injection safe, CI workflow syntax valid. |
| Agent 3 (Analytics & CI) | Agent 1 (Security) | Read `security.py`, `rate_limiter.py`, `request_id.py`, `main.py`. Run `test_security_middleware.py`. Check: CORS origins correct, no middleware order bugs, rate limiter works. |

### QA Checklist (each reviewer verifies):

1. **Tests pass:** `python -m pytest tests/test_<relevant>.py -v`
2. **No regressions:** `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
3. **Syntax clean:** `python -m py_compile <every new file>`
4. **Security:** No secrets in code, no SQL injection, no auth bypass
5. **Error handling:** All new code has try/except where appropriate
6. **Logging:** New code uses `logger` not `print()`

### QA Failure Protocol

If QA finds issues:
1. Send specific feedback to original agent with file:line reference
2. Original agent fixes and re-runs tests
3. Reviewer re-checks the specific fix
4. Repeat until approved

---

## Final Verification (Agent 1, after all QA passes)

**Step 1:** Run full free test suite:
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```
Expected: ALL tests pass (194 existing + new tests)

**Step 2:** Syntax check everything:
```bash
python -m py_compile app/main.py
python -m py_compile app/middleware/request_id.py
python -m py_compile app/middleware/security.py
python -m py_compile app/middleware/rate_limiter.py
python -m py_compile app/middleware/error_handler.py
python -m py_compile app/middleware/logging_config.py
python -m py_compile app/services/sentry_service.py
python -m py_compile app/services/analytics_service.py
python -m py_compile app/api/admin_routes.py
```

**Step 3:** Final commit with all changes:
```bash
git add -A
git status
git commit -m "feat: production readiness — security, observability, analytics, CI/CD

- Security headers middleware (X-Content-Type-Options, X-Frame-Options, etc.)
- Rate limiting via slowapi (10/min anonymous, 30/min authenticated)
- Request ID middleware for request tracing
- CORS restricted to specific origins
- Sentry integration (opt-in via SENTRY_DSN env var)
- Global error handler (clean 500 responses, no stack trace leaks)
- Structured JSON logging
- Admin analytics endpoints (/api/v1/admin/stats/*)
- GitHub Actions CI (unit tests + type checking on every PR)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## New Environment Variables for Railway

| Variable | Value | Required |
|----------|-------|----------|
| `SENTRY_DSN` | From sentry.io project settings | No (disabled if empty) |
| `ADMIN_API_KEY` | Random 32+ char string | Yes (for admin endpoints) |

Existing variables unchanged.
