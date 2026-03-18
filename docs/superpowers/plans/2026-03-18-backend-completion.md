# Backend Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore missing history endpoints, add comparison sharing, standardize error responses, add auth rate limits, and clean up URL stub.

**Architecture:** New `history_routes.py` and `share_routes.py` route files, unified error middleware in existing `error_handler.py`, rate limit decorators on auth endpoints. All DB functions already exist except share token and single-comparison fetch.

**Tech Stack:** FastAPI, Supabase (PostgreSQL), slowapi, Python 3.12, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-backend-completion-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `app/api/history_routes.py` | 3 endpoints: list history, get single comparison, delete comparison |
| `app/api/share_routes.py` | 2 endpoints: create share link, view shared comparison |
| `tests/test_history_routes.py` | Tests for history route endpoints |
| `tests/test_share_routes.py` | Tests for share route endpoints |
| `tests/test_error_middleware.py` | Tests for unified error response format |

### Modified Files
| File | Changes |
|------|---------|
| `app/main.py` | Register 2 new routers, replace slowapi 429 handler |
| `app/middleware/error_handler.py` | Add HTTPException + ValidationError + RateLimitExceeded handlers |
| `app/api/auth_routes.py` | Add `@limiter.limit()` decorators on 4 endpoints |
| `app/api/url_routes.py` | Delete `/compare/multi` endpoint + `MultiURLCompareRequest` model |
| `app/services/database_service.py` | Add `create_share_token()`, `get_shared_comparison()`, `get_user_comparison_count()` updates |

---

## Execution Strategy: 2 Rounds of Claude Agent Teams

### Round 1: History Routes + Error Middleware + Auth Rate Limits + URL Cleanup
- **Agent A (backend-core):** Tasks 1, 3, 4, 5
- **Agent B (test-core):** Tasks 2, 6, 7
- Cross-QA: Each agent reviews the other's files before team dissolves

### Round 2: Share Routes + Final QA
- **Agent A (backend-share):** Tasks 8 (DB migration FIRST), 9 (share routes + DB functions)
- **Agent B (test-share):** Tasks 10 (share tests), 11 (full regression)
- Cross-QA: Full regression + cross-review
- **CRITICAL:** DB migration (Task 8) must complete before share routes (Task 9) — `share_token` column must exist.

---

## Task 1: Create History Routes

**Files:**
- Create: `app/api/history_routes.py`
- Modify: `app/main.py:18-101` (add import + router registration)

- [ ] **Step 1: Create `app/api/history_routes.py`**

```python
"""
History Routes - Comparison history endpoints (restored from deleted routes.py)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from app.api.auth_routes import get_current_user
from app.services.database_service import (
    get_user_comparisons,
    get_comparison_by_id,
    get_user_comparison_count,
    delete_comparison,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/comparisons", tags=["history"])


@router.get("/history")
async def list_comparisons(
    search: Optional[str] = Query(None, description="Filter by query text"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user),
):
    """List user's comparison history, paginated and searchable."""
    comparisons = await get_user_comparisons(
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
        search=search,
    )

    # Strip full_response from list view (too large)
    summaries = []
    for c in comparisons:
        summaries.append({
            "id": c.get("id"),
            "query": c.get("query"),
            "product_names": c.get("product_names", []),
            "input_type": c.get("input_type", "text"),
            "created_at": c.get("created_at"),
        })

    total = await get_user_comparison_count(current_user["id"])

    return {
        "success": True,
        "comparisons": summaries,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{comparison_id}")
async def get_comparison(
    comparison_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a single comparison with full response data."""
    comparison = await get_comparison_by_id(comparison_id)

    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    if comparison.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this comparison")

    return {
        "success": True,
        "comparison": {
            "id": comparison.get("id"),
            "query": comparison.get("query"),
            "product_names": comparison.get("product_names", []),
            "input_type": comparison.get("input_type", "text"),
            "full_response": comparison.get("full_response"),
            "created_at": comparison.get("created_at"),
        },
    }


@router.delete("/{comparison_id}")
async def remove_comparison(
    comparison_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a comparison from history (ownership check)."""
    # First check it exists and belongs to user
    comparison = await get_comparison_by_id(comparison_id)

    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    if comparison.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comparison")

    deleted = await delete_comparison(comparison_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete comparison")

    return {"success": True}
```

- [ ] **Step 2: Register the router in `app/main.py`**

Add after the `feedback_routes` import:
```python
from app.api.history_routes import router as history_router  # Comparison history
```

Add after `app.include_router(feedback_router)`:
```python
app.include_router(history_router)  # /api/v1/comparisons/*
```

- [ ] **Step 3: Syntax check**

Run: `python -m py_compile app/api/history_routes.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add app/api/history_routes.py app/main.py
git commit -m "feat: restore history routes (broken since Session 22 routes.py deletion)"
```

---

## Task 2: Write History Route Tests

**Files:**
- Create: `tests/test_history_routes.py`

- [ ] **Step 1: Write tests for all 3 history endpoints**

```python
"""Tests for history route endpoints (GET list, GET single, DELETE)."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


MOCK_USER = {"id": "user-123", "email": "test@example.com"}
MOCK_OTHER_USER = {"id": "user-999", "email": "other@example.com"}

MOCK_COMPARISON = {
    "id": "comp-abc",
    "query": "iPhone 15 vs Galaxy S24",
    "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
    "input_type": "text",
    "user_id": "user-123",
    "full_response": {
        "success": True,
        "products": [
            {"brand": "Apple", "name": "iPhone 15"},
            {"brand": "Samsung", "name": "Galaxy S24"},
        ],
        "comparison": {"winner_index": 0},
    },
    "created_at": "2026-03-18T10:00:00Z",
}

MOCK_COMPARISON_LIST = [
    {
        "id": "comp-abc",
        "query": "iPhone 15 vs Galaxy S24",
        "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {"products": []},
        "created_at": "2026-03-18T10:00:00Z",
    },
    {
        "id": "comp-def",
        "query": "Pixel 9 vs Galaxy S24",
        "product_names": ["Google Pixel 9", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {"products": []},
        "created_at": "2026-03-17T10:00:00Z",
    },
]


def _get_test_client():
    """Create test client with mocked auth."""
    from app.main import app
    return TestClient(app)


# ============================================
# GET /api/v1/comparisons/history
# ============================================


def test_list_history_requires_auth():
    """GET /history without auth returns 401."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/history")
    assert resp.status_code == 401


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=MOCK_COMPARISON_LIST)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_list_history_success(mock_auth, mock_get, mock_count):
    """GET /history returns paginated comparison summaries."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/history", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["comparisons"]) == 2
    assert data["total"] == 2
    assert data["limit"] == 20
    assert data["offset"] == 0
    # Summaries should NOT include full_response
    assert "full_response" not in data["comparisons"][0]


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=MOCK_COMPARISON_LIST)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_list_history_with_search(mock_auth, mock_get, mock_count):
    """GET /history?search=iphone passes search to DB."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/history?search=iphone", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    mock_get.assert_called_once_with(user_id="user-123", limit=20, offset=0, search="iphone")


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=MOCK_COMPARISON_LIST)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_list_history_pagination(mock_auth, mock_get, mock_count):
    """GET /history?limit=5&offset=10 passes pagination params."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/history?limit=5&offset=10", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    mock_get.assert_called_once_with(user_id="user-123", limit=5, offset=10, search=None)
    data = resp.json()
    assert data["limit"] == 5
    assert data["offset"] == 10


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=0)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=[])
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_list_history_empty(mock_auth, mock_get, mock_count):
    """GET /history with no comparisons returns empty list."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/history", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["comparisons"] == []
    assert data["total"] == 0


def test_list_history_limit_validation():
    """GET /history?limit=999 rejects invalid limit."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/history?limit=999", headers={"Authorization": "Bearer fake"})
    assert resp.status_code in (401, 422)  # 401 if auth checked first, 422 if validation first


# ============================================
# GET /api/v1/comparisons/{id}
# ============================================


def test_get_comparison_requires_auth():
    """GET /comparisons/{id} without auth returns 401."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/comp-abc")
    assert resp.status_code == 401


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_get_comparison_success(mock_auth, mock_get):
    """GET /comparisons/{id} returns full comparison with full_response."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["comparison"]["id"] == "comp-abc"
    assert "full_response" in data["comparison"]
    assert data["comparison"]["full_response"]["success"] is True


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_get_comparison_not_found(mock_auth, mock_get):
    """GET /comparisons/{id} returns 404 if not found."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/nonexistent", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 404


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_OTHER_USER)
def test_get_comparison_forbidden(mock_auth, mock_get):
    """GET /comparisons/{id} returns 403 if not owner."""
    client = _get_test_client()
    resp = client.get("/api/v1/comparisons/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 403


# ============================================
# DELETE /api/v1/comparisons/{id}
# ============================================


def test_delete_comparison_requires_auth():
    """DELETE /comparisons/{id} without auth returns 401."""
    client = _get_test_client()
    resp = client.delete("/api/v1/comparisons/comp-abc")
    assert resp.status_code == 401


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=True)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_delete_comparison_success(mock_auth, mock_get, mock_del):
    """DELETE /comparisons/{id} deletes owned comparison."""
    client = _get_test_client()
    resp = client.delete("/api/v1/comparisons/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_del.assert_called_once_with("comp-abc", "user-123")


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_delete_comparison_not_found(mock_auth, mock_get):
    """DELETE /comparisons/{id} returns 404 if not found."""
    client = _get_test_client()
    resp = client.delete("/api/v1/comparisons/nonexistent", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 404


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_OTHER_USER)
def test_delete_comparison_forbidden(mock_auth, mock_get):
    """DELETE /comparisons/{id} returns 403 if not owner."""
    client = _get_test_client()
    resp = client.delete("/api/v1/comparisons/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 403


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=False)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
@patch("app.api.history_routes.get_current_user", return_value=MOCK_USER)
def test_delete_comparison_db_failure(mock_auth, mock_get, mock_del):
    """DELETE /comparisons/{id} returns 500 if DB delete fails."""
    client = _get_test_client()
    resp = client.delete("/api/v1/comparisons/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 500
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_history_routes.py -v`
Expected: All 15 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_history_routes.py
git commit -m "test: add 15 tests for history route endpoints"
```

---

## Task 3: Unified Error Response Middleware

**Files:**
- Modify: `app/middleware/error_handler.py`
- Modify: `app/main.py:30-31,83-84` (replace slowapi handler)

- [ ] **Step 1: Rewrite `app/middleware/error_handler.py`**

Replace the entire file with:

```python
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
```

- [ ] **Step 2: Update `app/main.py` to use new handlers**

Replace the slowapi import and handler registration. Change:
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
```
to:
```python
from slowapi.errors import RateLimitExceeded
```

Replace:
```python
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```
with:
```python
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    rate_limit_handler,
)
from fastapi.exceptions import RequestValidationError

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```

Also add `HTTPException` to the fastapi import at the top:
```python
from fastapi import FastAPI, HTTPException
```

- [ ] **Step 3: Syntax check both files**

Run: `python -m py_compile app/middleware/error_handler.py && python -m py_compile app/main.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add app/middleware/error_handler.py app/main.py
git commit -m "feat: unified error response format with error codes"
```

---

## Task 4: Auth Rate Limiting

**Files:**
- Modify: `app/api/auth_routes.py:27,197,210,236,285` (add limiter decorators)

- [ ] **Step 1: Add limiter import to `app/api/auth_routes.py`**

Add after line 7 (`from typing import ...`):
```python
from starlette.requests import Request
from app.middleware.rate_limiter import limiter
```

- [ ] **Step 2: Add rate limit decorators to 4 endpoints**

Add `@limiter.limit("5/minute")` above `async def login(...)`:
```python
@router.post("/login")
@limiter.limit("5/minute")
async def login(body: LoginRequest, request: Request):
```
Note: `request: Request` parameter MUST be added — slowapi requires it.

Add `@limiter.limit("3/minute")` above `async def register(...)`:
```python
@router.post("/register")
@limiter.limit("3/minute")
async def register(body: RegisterRequest, request: Request):
```

Add `@limiter.limit("10/minute")` above `async def social_login(...)`:
```python
@router.post("/social-login")
@limiter.limit("10/minute")
async def social_login(body: SocialLoginRequest, request: Request):
```

Add `@limiter.limit("3/minute")` above `async def password_reset(...)`:
```python
@router.post("/password-reset")
@limiter.limit("3/minute")
async def password_reset(body: PasswordResetRequest, request: Request):
```

- [ ] **Step 3: Syntax check**

Run: `python -m py_compile app/api/auth_routes.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add app/api/auth_routes.py
git commit -m "feat: add rate limits to auth endpoints (login 5/min, register 3/min)"
```

---

## Task 5: Delete URL Multi-Compare Stub

**Files:**
- Modify: `app/api/url_routes.py` (delete lines ~37-41 and ~203-250)

- [ ] **Step 1: Remove `MultiURLCompareRequest` model**

Delete the class:
```python
class MultiURLCompareRequest(BaseModel):
    """Request to compare multiple products from URLs"""
    urls: List[str]
    region: str = "bahrain"
```

- [ ] **Step 2: Remove the `/compare/multi` endpoint**

Delete the entire section starting with `# Multi-product comparison (future)` through the end of the `compare_multiple_urls` function.

- [ ] **Step 3: Clean up unused imports if any**

Check if `List` is still used after removing `MultiURLCompareRequest`. If not used elsewhere, remove from imports.

- [ ] **Step 4: Syntax check**

Run: `python -m py_compile app/api/url_routes.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/api/url_routes.py
git commit -m "fix: remove unimplemented URL multi-compare stub endpoint"
```

---

## Task 6: Error Middleware Tests

**Files:**
- Create: `tests/test_error_middleware.py`

- [ ] **Step 1: Write tests for unified error format**

```python
"""Tests for unified error response middleware."""
import pytest
from fastapi.testclient import TestClient


def _get_test_client():
    from app.main import app
    return TestClient(app)


# ============================================
# Error format validation
# ============================================


def test_404_returns_unified_format():
    """Non-existent endpoint returns unified error format."""
    client = _get_test_client()
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "NOT_FOUND"
    assert "error" in data
    assert "request_id" in data


def test_422_validation_error_format():
    """Invalid request body returns VALIDATION_ERROR code."""
    client = _get_test_client()
    # POST to compare with invalid body (missing required fields)
    resp = client.post("/api/v1/text/compare", json={})
    # text/compare accepts JSON body with query field
    assert resp.status_code == 422
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "VALIDATION_ERROR"
    assert "request_id" in data


def test_401_returns_auth_required():
    """Auth-required endpoint without token returns AUTH_REQUIRED."""
    client = _get_test_client()
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "AUTH_REQUIRED"


def test_error_response_has_request_id():
    """All error responses include request_id."""
    client = _get_test_client()
    resp = client.get("/api/v1/nonexistent")
    data = resp.json()
    assert "request_id" in data
    assert data["request_id"] != "unknown"


def test_405_method_not_allowed():
    """Wrong HTTP method returns unified format."""
    client = _get_test_client()
    resp = client.patch("/api/v1/auth/login")
    assert resp.status_code == 405
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "METHOD_NOT_ALLOWED"


def test_health_endpoint_not_affected():
    """Health check still returns normal response (not error format)."""
    client = _get_test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    # Should NOT have error format fields
    assert "code" not in data


def test_error_format_fields():
    """Error responses have exactly: success, error, code, request_id."""
    client = _get_test_client()
    resp = client.get("/api/v1/nonexistent")
    data = resp.json()
    expected_keys = {"success", "error", "code", "request_id"}
    assert set(data.keys()) == expected_keys


# ============================================
# Rate limit error format
# ============================================


def test_rate_limit_error_format():
    """Verify rate limit handler is registered (indirect test)."""
    # We can't easily trigger 429 in unit tests without many requests.
    # Instead, test that the handler function produces correct format.
    from app.middleware.error_handler import _build_error_response
    resp = _build_error_response(429, "Rate limit exceeded", "test-id")
    import json
    data = json.loads(resp.body.decode())
    assert data["success"] is False
    assert data["code"] == "RATE_LIMITED"
    assert data["request_id"] == "test-id"


def test_build_error_response_unknown_status():
    """Unknown status codes default to SERVER_ERROR."""
    from app.middleware.error_handler import _build_error_response
    resp = _build_error_response(418, "I'm a teapot", "test-id")
    import json
    data = json.loads(resp.body.decode())
    assert data["code"] == "SERVER_ERROR"
    assert data["error"] == "I'm a teapot"


def test_build_error_response_all_status_codes():
    """Verify all mapped status codes produce correct error codes."""
    from app.middleware.error_handler import _build_error_response, STATUS_CODE_MAP
    for status, code in STATUS_CODE_MAP.items():
        resp = _build_error_response(status, "test", "req-1")
        import json
        data = json.loads(resp.body.decode())
        assert data["code"] == code, f"Status {status} should map to {code}"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_error_middleware.py -v`
Expected: All 10 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_error_middleware.py
git commit -m "test: add 10 tests for unified error response middleware"
```

---

## Task 7: Auth Rate Limit Tests

**Files:**
- Modify: `tests/test_auth_interceptor.py` (add rate limit tests at end)

- [ ] **Step 1: Add rate limit tests to existing auth test file**

Append to end of `tests/test_auth_interceptor.py`:

```python
# ============================================
# Auth Rate Limiting
# ============================================


def test_login_has_rate_limit_decorator():
    """Login endpoint has rate limit configured."""
    from app.api.auth_routes import login
    # slowapi stores limits in function attributes
    assert hasattr(login, "__rate_limit__") or hasattr(login, "_rate_limits"), \
        "login endpoint should have rate limit decorator"


def test_register_has_rate_limit_decorator():
    """Register endpoint has rate limit configured."""
    from app.api.auth_routes import register
    assert hasattr(register, "__rate_limit__") or hasattr(register, "_rate_limits"), \
        "register endpoint should have rate limit decorator"


def test_social_login_has_rate_limit_decorator():
    """Social login endpoint has rate limit configured."""
    from app.api.auth_routes import social_login
    assert hasattr(social_login, "__rate_limit__") or hasattr(social_login, "_rate_limits"), \
        "social_login endpoint should have rate limit decorator"


def test_password_reset_has_rate_limit_decorator():
    """Password reset endpoint has rate limit configured."""
    from app.api.auth_routes import password_reset
    assert hasattr(password_reset, "__rate_limit__") or hasattr(password_reset, "_rate_limits"), \
        "password_reset endpoint should have rate limit decorator"
```

- [ ] **Step 2: Run the new tests**

Run: `python -m pytest tests/test_auth_interceptor.py -v -k "rate_limit"`
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_interceptor.py
git commit -m "test: add 4 rate limit verification tests for auth endpoints"
```

---

## Task 8: Database Migration for Share Token

**Files:**
- Create: `migrations/add_share_token.sql` (reference file for manual execution)

- [ ] **Step 1: Create migration file**

```sql
-- Migration: Add share_token column to comparisons table
-- Date: 2026-03-18
-- Session: 24

-- Apply
ALTER TABLE comparisons ADD COLUMN IF NOT EXISTS share_token VARCHAR(12) DEFAULT NULL UNIQUE;
CREATE INDEX IF NOT EXISTS idx_comparisons_share_token ON comparisons(share_token) WHERE share_token IS NOT NULL;

-- Rollback (run manually if needed):
-- DROP INDEX IF EXISTS idx_comparisons_share_token;
-- ALTER TABLE comparisons DROP COLUMN IF EXISTS share_token;
```

- [ ] **Step 2: Execute migration via Supabase**

Run in Supabase SQL Editor (project `qulajmyxdbdkchvecmvc`) or via MCP tool:
```sql
ALTER TABLE comparisons ADD COLUMN IF NOT EXISTS share_token VARCHAR(12) DEFAULT NULL UNIQUE;
CREATE INDEX IF NOT EXISTS idx_comparisons_share_token ON comparisons(share_token) WHERE share_token IS NOT NULL;
```

- [ ] **Step 3: Commit migration file**

```bash
git add migrations/add_share_token.sql
git commit -m "db: add share_token column to comparisons table"
```

---

## Task 9: Create Share Routes

**Files:**
- Create: `app/api/share_routes.py`
- Modify: `app/services/database_service.py` (add `create_share_token`, `get_shared_comparison`)
- Modify: `app/main.py` (register router)

- [ ] **Step 1: Add share DB functions to `app/services/database_service.py`**

Add after the `delete_comparison` function (around line 198):

```python
async def create_share_token(comparison_id: str, user_id: str) -> Optional[str]:
    """
    Generate a share token for a comparison.
    Verifies ownership. Returns existing token if already shared.
    Retries on collision (max 3 attempts).
    """
    import secrets

    try:
        client = get_supabase_client()

        # Fetch comparison and verify ownership
        comparison = await get_comparison_by_id(comparison_id)
        if not comparison:
            return None
        if comparison.get("user_id") != user_id:
            raise PermissionError("Not authorized to share this comparison")

        # Return existing token if already shared
        existing_token = comparison.get("share_token")
        if existing_token:
            return existing_token

        # Generate and store token (retry on collision)
        for attempt in range(3):
            token = secrets.token_urlsafe(6)  # 8 chars
            try:
                response = (
                    client.table("comparisons")
                    .update({"share_token": token})
                    .eq("id", comparison_id)
                    .eq("user_id", user_id)
                    .execute()
                )
                if response.data:
                    return token
            except Exception as e:
                if "unique" in str(e).lower() and attempt < 2:
                    continue  # Retry with new token
                raise

        return None
    except PermissionError:
        raise
    except Exception as e:
        logger.warning(f"Error creating share token: {e}", exc_info=True)
        return None


async def get_shared_comparison(share_token: str) -> Optional[Dict]:
    """
    Get a shared comparison by share token. No auth required.
    Strips personalization fields from full_response.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .select("id, query, product_names, input_type, full_response, created_at")
            .eq("share_token", share_token)
            .single()
            .execute()
        )
        if not response.data:
            return None

        data = response.data

        # Strip personalization fields from full_response
        full_response = data.get("full_response", {})
        if isinstance(full_response, dict):
            for key in ("personalized", "personalization_factors", "personalization_prompt"):
                full_response.pop(key, None)
            data["full_response"] = full_response

        return data
    except Exception as e:
        logger.warning(f"Error getting shared comparison: {e}", exc_info=True)
        return None
```

- [ ] **Step 2: Create `app/api/share_routes.py`**

```python
"""
Share Routes - Public comparison sharing endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.api.auth_routes import get_current_user
from app.services.database_service import create_share_token, get_shared_comparison

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/share", tags=["sharing"])

SHARE_BASE_URL = "https://web-production-58776.up.railway.app/api/v1/share"


@router.post("/{comparison_id}")
async def share_comparison(
    comparison_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate a share link for a comparison. Requires ownership."""
    try:
        token = await create_share_token(comparison_id, current_user["id"])
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized to share this comparison")

    if not token:
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "success": True,
        "share_token": token,
        "share_url": f"{SHARE_BASE_URL}/{token}",
    }


@router.get("/{token}")
async def view_shared_comparison(token: str):
    """View a shared comparison. No auth required."""
    comparison = await get_shared_comparison(token)

    if not comparison:
        raise HTTPException(status_code=404, detail="Shared comparison not found")

    return {
        "success": True,
        "comparison": {
            "query": comparison.get("query"),
            "product_names": comparison.get("product_names", []),
            "input_type": comparison.get("input_type", "text"),
            "full_response": comparison.get("full_response"),
            "created_at": comparison.get("created_at"),
        },
    }
```

- [ ] **Step 3: Register share router in `app/main.py`**

Add import:
```python
from app.api.share_routes import router as share_router  # Comparison sharing
```

Add router registration:
```python
app.include_router(share_router)  # /api/v1/share/*
```

- [ ] **Step 4: Syntax check all 3 files**

Run: `python -m py_compile app/api/share_routes.py && python -m py_compile app/services/database_service.py && python -m py_compile app/main.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/api/share_routes.py app/services/database_service.py app/main.py
git commit -m "feat: add comparison sharing with public share links"
```

---

## Task 10: Share Route Tests

**Files:**
- Create: `tests/test_share_routes.py`

- [ ] **Step 1: Write tests for share endpoints + DB functions**

```python
"""Tests for share route endpoints (POST create, GET view) and DB functions."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


MOCK_USER = {"id": "user-123", "email": "test@example.com"}
MOCK_OTHER_USER = {"id": "user-999", "email": "other@example.com"}

MOCK_COMPARISON = {
    "id": "comp-abc",
    "query": "iPhone 15 vs Galaxy S24",
    "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
    "input_type": "text",
    "user_id": "user-123",
    "share_token": None,
    "full_response": {
        "success": True,
        "products": [{"brand": "Apple", "name": "iPhone 15"}],
        "personalized": True,
        "personalization_factors": ["price", "quality"],
    },
    "created_at": "2026-03-18T10:00:00Z",
}

MOCK_SHARED = {
    "id": "comp-abc",
    "query": "iPhone 15 vs Galaxy S24",
    "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
    "input_type": "text",
    "full_response": {
        "success": True,
        "products": [{"brand": "Apple", "name": "iPhone 15"}],
    },
    "created_at": "2026-03-18T10:00:00Z",
}


def _get_test_client():
    from app.main import app
    return TestClient(app)


# ============================================
# POST /api/v1/share/{comparison_id}
# ============================================


def test_share_requires_auth():
    """POST /share/{id} without auth returns 401."""
    client = _get_test_client()
    resp = client.post("/api/v1/share/comp-abc")
    assert resp.status_code == 401


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, return_value="abc12xyz")
@patch("app.api.share_routes.get_current_user", return_value=MOCK_USER)
def test_share_success(mock_auth, mock_create):
    """POST /share/{id} returns share token and URL."""
    client = _get_test_client()
    resp = client.post("/api/v1/share/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["share_token"] == "abc12xyz"
    assert "abc12xyz" in data["share_url"]


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, side_effect=PermissionError("Not authorized"))
@patch("app.api.share_routes.get_current_user", return_value=MOCK_USER)
def test_share_forbidden(mock_auth, mock_create):
    """POST /share/{id} returns 403 if not owner."""
    client = _get_test_client()
    resp = client.post("/api/v1/share/comp-abc", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 403


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, return_value=None)
@patch("app.api.share_routes.get_current_user", return_value=MOCK_USER)
def test_share_not_found(mock_auth, mock_create):
    """POST /share/{id} returns 404 if comparison doesn't exist."""
    client = _get_test_client()
    resp = client.post("/api/v1/share/nonexistent", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 404


# ============================================
# GET /api/v1/share/{token}
# ============================================


@patch("app.api.share_routes.get_shared_comparison", new_callable=AsyncMock, return_value=MOCK_SHARED)
def test_view_shared_success(mock_get):
    """GET /share/{token} returns comparison without auth."""
    client = _get_test_client()
    resp = client.get("/api/v1/share/abc12xyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["comparison"]["query"] == "iPhone 15 vs Galaxy S24"
    # Personalization fields should be stripped
    assert "personalized" not in data["comparison"].get("full_response", {})
    assert "personalization_factors" not in data["comparison"].get("full_response", {})


@patch("app.api.share_routes.get_shared_comparison", new_callable=AsyncMock, return_value=None)
def test_view_shared_invalid_token(mock_get):
    """GET /share/{token} returns 404 for invalid token."""
    client = _get_test_client()
    resp = client.get("/api/v1/share/invalid_token")
    assert resp.status_code == 404


def test_view_shared_no_auth_needed():
    """GET /share/{token} doesn't require Authorization header."""
    client = _get_test_client()
    # Should not return 401 (may return 404 since token doesn't exist)
    resp = client.get("/api/v1/share/sometoken")
    assert resp.status_code != 401


# ============================================
# DB function tests
# ============================================


def test_get_shared_comparison_strips_personalization():
    """get_shared_comparison removes personalization keys from full_response."""
    import asyncio
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.data = {
        "id": "comp-abc",
        "query": "test",
        "product_names": [],
        "input_type": "text",
        "full_response": {
            "products": [],
            "personalized": True,
            "personalization_factors": ["price"],
            "personalization_prompt": "some prompt",
        },
        "created_at": "2026-01-01",
    }

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import get_shared_comparison
        result = asyncio.get_event_loop().run_until_complete(get_shared_comparison("token123"))

    assert result is not None
    fr = result["full_response"]
    assert "personalized" not in fr
    assert "personalization_factors" not in fr
    assert "personalization_prompt" not in fr
    assert "products" in fr  # Non-personalization fields preserved


def test_create_share_token_ownership_check():
    """create_share_token raises PermissionError for wrong user."""
    import asyncio

    mock_comparison = {
        "id": "comp-abc",
        "user_id": "user-123",
        "share_token": None,
    }

    with patch("app.services.database_service.get_comparison_by_id", new_callable=AsyncMock, return_value=mock_comparison):
        from app.services.database_service import create_share_token
        with pytest.raises(PermissionError):
            asyncio.get_event_loop().run_until_complete(
                create_share_token("comp-abc", "wrong-user")
            )


def test_create_share_token_returns_existing():
    """create_share_token returns existing token if already shared."""
    import asyncio

    mock_comparison = {
        "id": "comp-abc",
        "user_id": "user-123",
        "share_token": "existing_tok",
    }

    with patch("app.services.database_service.get_comparison_by_id", new_callable=AsyncMock, return_value=mock_comparison):
        from app.services.database_service import create_share_token
        result = asyncio.get_event_loop().run_until_complete(
            create_share_token("comp-abc", "user-123")
        )
        assert result == "existing_tok"


def test_create_share_token_not_found():
    """create_share_token returns None if comparison doesn't exist."""
    import asyncio

    with patch("app.services.database_service.get_comparison_by_id", new_callable=AsyncMock, return_value=None):
        from app.services.database_service import create_share_token
        result = asyncio.get_event_loop().run_until_complete(
            create_share_token("nonexistent", "user-123")
        )
        assert result is None
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_share_routes.py -v`
Expected: All 12 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_share_routes.py
git commit -m "test: add 12 tests for share route endpoints and DB functions"
```

---

## Task 11: Full Regression Test + Final QA

- [ ] **Step 1: Run the complete free test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All tests pass (717 existing + ~41 new = ~758 total)

- [ ] **Step 2: Syntax check all modified files**

Run:
```bash
python -m py_compile app/api/history_routes.py
python -m py_compile app/api/share_routes.py
python -m py_compile app/middleware/error_handler.py
python -m py_compile app/api/auth_routes.py
python -m py_compile app/api/url_routes.py
python -m py_compile app/main.py
python -m py_compile app/services/database_service.py
```
Expected: All pass (no output)

- [ ] **Step 3: Verify no import errors**

Run: `python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: Session 24 backend completion — all tests pass"
```

---

## Summary

| Task | What | Tests | Agent |
|------|------|-------|-------|
| 1 | History routes (3 endpoints) | — | Round 1, Agent A |
| 2 | History route tests | 15 | Round 1, Agent B |
| 3 | Unified error middleware | — | Round 1, Agent A |
| 4 | Auth rate limits | — | Round 1, Agent A |
| 5 | Delete URL multi-compare stub | — | Round 1, Agent A |
| 6 | Error middleware tests | 10 | Round 1, Agent B |
| 7 | Auth rate limit tests | 4 | Round 1, Agent B |
| 8 | DB migration for share token | — | Round 2, Agent A (FIRST) |
| 9 | Share routes + DB functions | — | Round 2, Agent A |
| 10 | Share route tests | 12 | Round 2, Agent B |
| 11 | Full regression + QA | — | Round 2, Both |

**Total new tests:** ~41
**Total test suite after:** ~758
