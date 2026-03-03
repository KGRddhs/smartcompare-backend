# Design: Production Readiness — Security, Observability, Analytics, CI/CD

**Date:** 2026-03-03
**Status:** Approved

## Problem

SmartCompare has solid features but zero production hardening:
- CORS allows all origins (`["*"]`) with credentials — security vulnerability
- No rate limiting — anyone can spam the API and burn Serper/OpenAI credits
- No security headers — vulnerable to clickjacking, XSS, MIME sniffing
- No error monitoring — exceptions vanish into Railway logs
- No structured logging — debugging production issues requires scrolling raw logs
- No global exception handler — each endpoint handles errors differently
- No analytics — `search_logs` table collects data but no way to query it
- No CI/CD — tests only run manually, no PR checks
- Rate limit config defined in `config.py` (`free_tier_daily_limit=5`) but never enforced

## Approach

Four workstreams, all free-tier services:
1. **Security & Middleware** — CORS fix, security headers, rate limiting (Upstash Redis), request IDs
2. **Observability** — Sentry (free, 5K errors/mo), global exception handler, structured logging
3. **Analytics** — Admin API endpoints querying `search_logs` + `products` tables
4. **CI/CD** — GitHub Actions running 194 unit tests + syntax/type checks on every PR

## Constraints

- **Budget:** Free tier only (Sentry free, GitHub Actions free, Upstash Redis already paid)
- **Zero regression:** All 194 existing unit tests must continue passing
- **New test coverage:** 80% target for all new code
- **No new paid services**

---

## Team Structure: 3 Opus Agents

### File Ownership (exclusive write access)

| Agent | Owns |
|-------|------|
| Agent 1: Security | `app/main.py` (middleware section), `app/middleware/security.py`, `app/middleware/rate_limiter.py`, `app/middleware/request_id.py`, `requirements.txt` (final merge) |
| Agent 2: Observability | `app/middleware/error_handler.py`, `app/middleware/logging_config.py`, `app/services/sentry_service.py` |
| Agent 3: Analytics & CI | `app/api/admin_routes.py`, `app/services/analytics_service.py`, `.github/workflows/ci.yml` |

**Shared file protocol:** Agent 1 is gatekeeper for `main.py` and `requirements.txt`. Agents 2 and 3 create their components in separate files and notify Agent 1 to register them.

### QA Circle

```
Agent 1 (Security) ──QAs──> Agent 2 (Observability)
Agent 2 (Observability) ──QAs──> Agent 3 (Analytics & CI)
Agent 3 (Analytics & CI) ──QAs──> Agent 1 (Security)
```

### Dependency Graph

```
Agent 1 (Security)  ──────────────> parallel start, builds middleware layer
Agent 2 (Observability) ──────────> parallel start, builds error handler + logging
Agent 3 (Analytics & CI) ─────────> parallel start, builds admin endpoints + CI

Agent 1 waits for Agent 2 + Agent 3 to finish → registers their middleware + routes in main.py
```

### Idle Protocol

When an agent finishes their primary work and waits for QA results:
1. Write red-green tests for their feature (target 80% coverage)
2. If tests are done, wait for QA assignment

When QA finds issues:
1. Send specific feedback to the original agent
2. Original agent fixes issues
3. QA agent re-reviews
4. Loop until approved

### Completion Criteria (ALL must pass before team disbands)

1. All 194 existing tests still pass (zero regressions)
2. Each agent's new code has tests at 80%+ coverage
3. Each QA pair has approved — all issues resolved
4. `python -m py_compile` passes on every modified `.py` file
5. Agent 1 confirms all middleware registered and `main.py` clean
6. All new endpoints respond correctly (manual curl verification)

---

## Agent 1: Security & Middleware Lead

### Task 1.1: Fix CORS

**File:** `app/main.py` (lines 47-54)

Replace wildcard CORS:
```python
ALLOWED_ORIGINS = [
    "https://smartcompare-backend-production.up.railway.app",
    "http://localhost:8000",
    "http://localhost:19006",  # Expo web
    "exp://localhost:8081",    # Expo Go
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"],
)
```

Note: React Native mobile apps don't send Origin headers (native HTTP, not browser), so CORS only affects web-based access. The mobile app will work regardless.

### Task 1.2: Security Headers Middleware

**New file:** `app/middleware/security.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
```

### Task 1.3: Rate Limiting

**New file:** `app/middleware/rate_limiter.py`

Use `slowapi` with Upstash Redis backend (already have `UPSTASH_REDIS_URL` and `UPSTASH_REDIS_TOKEN`):

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
import os

# Use Upstash Redis for distributed rate limiting
redis_url = os.getenv("UPSTASH_REDIS_URL", "")
redis_token = os.getenv("UPSTASH_REDIS_TOKEN", "")

# Build Redis URL for slowapi (needs redis:// scheme)
if redis_url and redis_token:
    # Upstash REST URL → Redis URL conversion
    storage_uri = f"redis://default:{redis_token}@{redis_url.replace('https://', '').replace('http://', '')}:6379"
else:
    storage_uri = "memory://"  # Fallback for local dev

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=["100/day", "10/minute"],
)
```

Apply to endpoints in routes:
- Anonymous: `10/minute`, `100/day`
- Authenticated: `30/minute`, `300/day`
- Admin endpoints: `60/minute` (higher for dashboards)

Rate limit key function that checks auth:
```python
def get_rate_limit_key(request: Request) -> str:
    # If authenticated, use user ID (higher limits)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Extract user from token (lightweight check)
        return f"user:{auth_header[7:20]}"  # First 20 chars of token as key
    return get_remote_address(request)
```

### Task 1.4: Request ID Middleware

**New file:** `app/middleware/request_id.py`

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### Task 1.5: Register Everything in main.py

After Agents 2 and 3 deliver their components:
```python
# Middleware order (outermost first):
# 1. Request ID (generates ID for all downstream)
# 2. Security headers
# 3. Error handler (catches exceptions from downstream)
# 4. Rate limiter
# 5. CORS (innermost)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
# slowapi exception handler + state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# CORS last (innermost)
app.add_middleware(CORSMiddleware, ...)

# Register admin routes
app.include_router(admin_router, prefix="/api/v1/admin")
```

### Task 1.6: Request Size Limits

Add to relevant endpoints:
- Query string `q` param: max 500 characters
- Image upload: already has 10MB limit (keep)
- Add `max_content_length` check in middleware for POST bodies

### Tests (Agent 1 writes)

**File:** `tests/test_security_middleware.py`

Target tests:
- CORS: allowed origin gets headers, disallowed origin rejected
- Security headers: all 6 headers present on every response
- Rate limiting: under limit succeeds, over limit returns 429, different keys have separate limits
- Request ID: generated when missing, preserved when provided, present in response
- Request size: oversized query rejected with 400

---

## Agent 2: Observability (Sentry + Logging + Error Handling)

### Task 2.1: Sentry Integration

**New file:** `app/services/sentry_service.py`

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
import os
import logging

logger = logging.getLogger(__name__)

def init_sentry():
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("SENTRY_DSN not set, Sentry disabled")
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=0.1,  # 10% of requests traced (free tier friendly)
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
        release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
        send_default_pii=False,  # Don't send user emails/IPs
    )
    logger.info("Sentry initialized")
```

**Env var:** Add `SENTRY_DSN` to Railway (user creates free Sentry project, gets DSN).

Sentry is opt-in — if `SENTRY_DSN` is empty, everything works without it. Zero cost unless configured.

### Task 2.2: Global Exception Handler

**New file:** `app/middleware/error_handler.py`

```python
import logging
import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")

            # Log with structured context
            logger.error(
                f"Unhandled exception: {type(exc).__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                },
                exc_info=True,
            )

            # Send to Sentry (if configured)
            sentry_sdk.capture_exception(exc)

            # Return clean error (don't leak internals)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "request_id": request_id,
                },
            )
```

### Task 2.3: Structured Logging Configuration

**New file:** `app/middleware/logging_config.py`

```python
import logging
import sys
import json
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Remove None values
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        return json.dumps(log_entry)

def configure_logging(level: str = "INFO"):
    """Configure structured JSON logging for production."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add structured handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

Call `configure_logging()` from `main.py` at startup (Agent 1 registers this).

### Task 2.4: Update Existing Loggers

No changes needed to existing files — they already use `logger = logging.getLogger(__name__)`. The structured formatter in Task 2.3 applies globally. The only change is calling `configure_logging()` at app startup (Agent 1 handles this in main.py).

### Tests (Agent 2 writes)

**File:** `tests/test_observability.py`

Target tests:
- Error handler: unhandled exception returns 500 JSON with request_id, does not leak stack trace
- Error handler: HTTPException passes through unchanged
- Structured formatter: outputs valid JSON, includes required fields
- Sentry init: works with empty DSN (disabled), works with valid DSN
- Logging config: sets correct level, quiets noisy libraries

---

## Agent 3: Analytics & CI/CD

### Task 3.1: Analytics Service

**New file:** `app/services/analytics_service.py`

Query `search_logs` and `products` tables via Supabase client:

```python
from app.services.database_service import get_supabase_client
from datetime import datetime, timezone, timedelta

async def get_daily_stats(days: int = 30) -> dict:
    """Comparisons count, cost, errors by day."""
    client = get_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = client.table("search_logs").select("*").gte("created_at", since).execute()
    # Aggregate by day...

async def get_popular_queries(limit: int = 20) -> list:
    """Top queries by frequency."""
    client = get_supabase_client()
    result = client.table("search_logs").select("query, input_type").execute()
    # Count and rank...

async def get_cost_trends(days: int = 30) -> dict:
    """Cost trends, avg cost per comparison."""
    client = get_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = client.table("search_logs").select("cost, created_at, success").gte("created_at", since).execute()
    # Aggregate...

async def get_error_stats(days: int = 7) -> dict:
    """Error rate, common errors."""
    client = get_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = client.table("search_logs").select("success, error_message, created_at").gte("created_at", since).execute()
    # Aggregate...

async def get_product_stats(limit: int = 20) -> dict:
    """Most compared products, category breakdown."""
    client = get_supabase_client()
    result = client.table("products").select("canonical_name, brand, category, updated_at").execute()
    # Count and rank...
```

### Task 3.2: Admin API Endpoints

**New file:** `app/api/admin_routes.py`

Protected by `X-Admin-Key` header (simple API key, no JWT overhead):

```python
from fastapi import APIRouter, Header, HTTPException
import os

router = APIRouter(tags=["admin"])

def verify_admin_key(x_admin_key: str = Header(...)):
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin key")

@router.get("/stats/daily")
async def daily_stats(days: int = 30, _=Depends(verify_admin_key)):
    return await get_daily_stats(days)

@router.get("/stats/popular")
async def popular_queries(limit: int = 20, _=Depends(verify_admin_key)):
    return await get_popular_queries(limit)

@router.get("/stats/costs")
async def cost_trends(days: int = 30, _=Depends(verify_admin_key)):
    return await get_cost_trends(days)

@router.get("/stats/errors")
async def error_stats(days: int = 7, _=Depends(verify_admin_key)):
    return await get_error_stats(days)

@router.get("/stats/products")
async def product_stats(limit: int = 20, _=Depends(verify_admin_key)):
    return await get_product_stats(limit)
```

**Env var:** Add `ADMIN_API_KEY` to Railway (any random string).

### Task 3.3: GitHub Actions CI

**New file:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt && pip install pytest pytest-asyncio pytest-timeout

      - name: Syntax check
        run: python -m py_compile app/main.py && find app -name "*.py" -exec python -m py_compile {} +

      - name: Run unit tests
        run: python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=60

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: SmartCompareApp/package-lock.json

      - name: Install frontend deps
        run: cd SmartCompareApp && npm ci

      - name: TypeScript check
        run: cd SmartCompareApp && npx tsc --noEmit
        continue-on-error: true  # 7 pre-existing errors as of Feb 18
```

### Tests (Agent 3 writes)

**File:** `tests/test_analytics.py`

Target tests:
- Admin auth: valid key succeeds, invalid key returns 403, missing key returns 422
- Daily stats: returns correct structure, handles empty search_logs
- Popular queries: correct ranking, respects limit param
- Cost trends: correct aggregation, handles zero-cost entries
- Error stats: correct error rate calculation
- Product stats: category breakdown correct

**File:** `tests/test_ci_syntax.py` (optional — validates py_compile works on all files)

---

## New Environment Variables

| Variable | Where | Example | Required |
|----------|-------|---------|----------|
| `SENTRY_DSN` | Railway | `https://abc@o123.ingest.sentry.io/456` | No (disabled if empty) |
| `ADMIN_API_KEY` | Railway | Any random 32+ char string | Yes (for admin endpoints) |

Existing variables unchanged. `UPSTASH_REDIS_URL` and `UPSTASH_REDIS_TOKEN` reused for rate limiting.

## New Dependencies

| Package | Purpose | Agent |
|---------|---------|-------|
| `sentry-sdk[fastapi]` | Error monitoring | Agent 2 |
| `slowapi` | Rate limiting | Agent 1 |

## Files Created

| File | Agent | Purpose |
|------|-------|---------|
| `app/middleware/__init__.py` | Agent 1 | Package init (already exists but empty) |
| `app/middleware/security.py` | Agent 1 | Security headers middleware |
| `app/middleware/rate_limiter.py` | Agent 1 | Rate limiting setup |
| `app/middleware/request_id.py` | Agent 1 | Request ID middleware |
| `app/middleware/error_handler.py` | Agent 2 | Global exception handler |
| `app/middleware/logging_config.py` | Agent 2 | Structured logging config |
| `app/services/sentry_service.py` | Agent 2 | Sentry SDK init |
| `app/api/admin_routes.py` | Agent 3 | Analytics API endpoints |
| `app/services/analytics_service.py` | Agent 3 | Analytics SQL queries |
| `.github/workflows/ci.yml` | Agent 3 | GitHub Actions CI pipeline |
| `tests/test_security_middleware.py` | Agent 1 | Security + rate limit tests |
| `tests/test_observability.py` | Agent 2 | Error handler + logging tests |
| `tests/test_analytics.py` | Agent 3 | Analytics endpoint tests |

## Files Modified

| File | Agent | Changes |
|------|-------|---------|
| `app/main.py` | Agent 1 | CORS fix, register all middleware + admin routes, call configure_logging() |
| `app/middleware/__init__.py` | Agent 1 | Export middleware classes |
| `requirements.txt` | Agent 1 | Add `sentry-sdk[fastapi]`, `slowapi` |
