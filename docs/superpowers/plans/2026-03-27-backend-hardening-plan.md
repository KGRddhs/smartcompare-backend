# Backend Hardening & Architecture Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all security vulnerabilities, concurrency race conditions, input validation gaps, and decompose the 3,453-line service file into focused modules.

**Architecture:** 4 parallel agents working on independent file sets. Security + Validation agent handles all route/middleware fixes. Concurrency agent fixes singleton state and atomic operations. Decomposition agent extracts 5 new service modules from the monolith. QA agent writes all new tests and cross-validates.

**Tech Stack:** Python 3.12, FastAPI, Supabase, Upstash Redis, httpx, Pydantic v2

**Spec:** `docs/superpowers/specs/2026-03-27-backend-hardening-design.md`

---

## File Map

### New Files
| File | Purpose | Created By |
|------|---------|------------|
| `app/utils/url_validator.py` | SSRF protection — validate external URLs | Task 1 |
| `app/services/exchange_rate_service.py` | Daily exchange rates with Redis cache + fallback | Task 3 |
| `app/services/price_service.py` | Price cascade extracted from monolith | Task 4 |
| `app/services/rating_service.py` | Rating pipeline extracted from monolith | Task 4 |
| `app/services/review_service.py` | Review pipeline + cleaning extracted | Task 4 |
| `app/services/fact_check_service.py` | Fact-checking extracted from monolith | Task 4 |
| `app/services/response_builder.py` | Unified response assembly (eliminates duplication) | Task 4 |
| `tests/test_security_hardening.py` | Tests for Tasks 1-2 | Task 5 |
| `tests/test_concurrency_fixes.py` | Tests for Task 3 | Task 5 |
| `tests/test_exchange_rate_service.py` | Tests for exchange rate service | Task 5 |
| `tests/test_decomposed_services.py` | Tests for extracted modules | Task 5 |

### Modified Files
| File | Changes | Modified By |
|------|---------|-------------|
| `app/api/text_routes.py` | Admin auth on cache/parse, SSE disconnect detection | Task 1 |
| `app/api/admin_routes.py` | Timing-safe key comparison | Task 1 |
| `app/main.py` | Disable docs in production | Task 1 |
| `app/middleware/security.py` | Add HSTS + CSP headers | Task 1 |
| `app/api/auth_routes.py` | Fix logout to call sign_out | Task 2 |
| `app/api/feedback_routes.py` | Field length limits, event data size limit | Task 2 |
| `app/api/url_routes.py` | SSRF validation, rate limiting | Task 2 |
| `app/services/database_service.py` | LIKE wildcard escaping | Task 2 |
| `app/services/sentry_service.py` | Token redaction in breadcrumbs | Task 2 |
| `app/api/history_routes.py` | UUID validation on comparison_id | Task 2 |
| `app/api/share_routes.py` | UUID validation on comparison_id | Task 2 |
| `app/services/structured_comparison_service.py` | Remove singleton, extract modules, import new services | Tasks 3, 4 |
| `app/services/scoring_service.py` | Return price_tiers from method, not self | Task 3 |
| `app/services/cache_service.py` | Atomic INCRBYFLOAT | Task 3 |
| `app/services/api_budget_service.py` | Atomic INCRBY | Task 3 |
| `app/services/trust_validation_service.py` | Fix flagged counter logic | Task 3 |

---

## Task 1: Security Hardening (Agent: Security)

**Files:**
- Create: `app/utils/url_validator.py`
- Modify: `app/api/text_routes.py:374-423`
- Modify: `app/api/admin_routes.py:22-27`
- Modify: `app/main.py:64-65`
- Modify: `app/middleware/security.py:1-19`

### C1 — Auth on cache flush & parse endpoints

- [ ] **Step 1: Add admin auth to DELETE /cache**

In `app/api/text_routes.py`, add the import at the top with other imports:

```python
from app.api.admin_routes import verify_admin_key
```

Then change line 374-377 from:

```python
@router.delete("/cache")
async def flush_product_cache(
    q: str = Query(..., description="Product query, e.g., 'rtx 3090'")
):
```

to:

```python
@router.delete("/cache")
async def flush_product_cache(
    q: str = Query(..., description="Product query, e.g., 'rtx 3090'"),
    _admin: bool = Depends(verify_admin_key),
):
```

- [ ] **Step 2: Add admin auth to GET /parse**

In the same file, change line 408-411 from:

```python
@router.get("/parse")
async def parse_query(
    q: str = Query(..., description="Query to parse, e.g., 'iPhone 15 vs S24'")
):
```

to:

```python
@router.get("/parse")
async def parse_query(
    q: str = Query(..., description="Query to parse, e.g., 'iPhone 15 vs S24'"),
    _admin: bool = Depends(verify_admin_key),
):
```

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile app/api/text_routes.py`
Expected: No output (clean compile)

### C2 — SSRF protection

- [ ] **Step 4: Create url_validator.py**

Create `app/utils/__init__.py` (empty) and `app/utils/url_validator.py`:

```python
"""URL validation — prevents SSRF by rejecting private/internal URLs."""
import ipaddress
import socket
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Allowlisted schemes
_ALLOWED_SCHEMES = {"http", "https"}


def validate_external_url(url: str) -> bool:
    """Validate that a URL points to a public external host.

    Rejects:
    - Private IPs (10.x, 172.16-31.x, 192.168.x)
    - Localhost (127.x)
    - Link-local (169.254.x)
    - Cloud metadata (169.254.169.254)
    - Non-http(s) schemes
    - Unresolvable hostnames

    Returns True if URL is safe to fetch, False otherwise.
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in _ALLOWED_SCHEMES:
            logger.warning(f"[SSRF] Blocked URL with scheme: {parsed.scheme}")
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP
        try:
            addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        except socket.gaierror:
            logger.warning(f"[SSRF] Cannot resolve hostname: {hostname}")
            return False

        for addr_info in addr_infos:
            ip_str = addr_info[4][0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                logger.warning(f"[SSRF] Blocked private/reserved IP: {ip} for host: {hostname}")
                return False

        return True

    except Exception as e:
        logger.error(f"[SSRF] URL validation error: {e}")
        return False
```

- [ ] **Step 5: Apply SSRF validation to url_routes.py**

In `app/api/url_routes.py`, add import:

```python
from app.utils.url_validator import validate_external_url
```

In the `extract_product` function (line 84), add validation before the `extract_from_url` call:

```python
    logger.info(f"URL extraction request: {request.url}")

    if not validate_external_url(str(request.url)):
        raise HTTPException(
            status_code=400,
            detail="URL points to a private or internal address"
        )

    result = await extract_from_url(request.url)
```

Apply the same validation in the GET `/extract` endpoint and both `/compare` endpoints.

- [ ] **Step 6: Verify syntax**

Run: `python -m py_compile app/utils/url_validator.py && python -m py_compile app/api/url_routes.py`
Expected: No output (clean compile)

### C3 — Timing-safe admin key

- [ ] **Step 7: Fix admin key comparison**

In `app/api/admin_routes.py`, add import at top:

```python
import hmac
```

Change lines 22-27 from:

```python
def verify_admin_key(x_admin_key: str = Header(...)):
    """Verify the admin API key from X-Admin-Key header."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True
```

to:

```python
def verify_admin_key(x_admin_key: str = Header(...)):
    """Verify the admin API key from X-Admin-Key header."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True
```

- [ ] **Step 8: Verify syntax**

Run: `python -m py_compile app/api/admin_routes.py`
Expected: No output

### C4 — Disable docs in production

- [ ] **Step 9: Conditional docs URLs**

In `app/main.py`, change lines 64-65 from:

```python
    docs_url="/docs",
    redoc_url="/redoc"
```

to:

```python
    docs_url=None if os.getenv("RAILWAY_ENVIRONMENT") else "/docs",
    redoc_url=None if os.getenv("RAILWAY_ENVIRONMENT") else "/redoc",
```

(`os` is already imported in main.py)

- [ ] **Step 10: Verify syntax**

Run: `python -m py_compile app/main.py`
Expected: No output

### Security headers — HSTS + CSP

- [ ] **Step 11: Add HSTS and CSP to security middleware**

In `app/middleware/security.py`, add after line 16 (after Permissions-Policy):

```python
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
```

- [ ] **Step 12: Verify syntax**

Run: `python -m py_compile app/middleware/security.py`
Expected: No output

### SSE disconnect detection

- [ ] **Step 13: Add disconnect check to SSE generator**

In `app/api/text_routes.py`, the `event_generator()` function (line 242). Change the async for loop body to check for disconnect:

```python
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
        ):
            if await request.is_disconnected():
                logger.info(f"[SSE] Client disconnected mid-stream for query: {q}")
                return

            if event_type == "complete":
                complete_response = data
            if event_type == "error":
                had_error = True

            yield f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
```

- [ ] **Step 14: Verify syntax and commit Task 1**

Run: `python -m py_compile app/api/text_routes.py`
Expected: No output

```bash
git add app/utils/__init__.py app/utils/url_validator.py app/api/text_routes.py app/api/admin_routes.py app/main.py app/middleware/security.py
git commit -m "feat: security hardening — admin auth, SSRF protection, timing-safe keys, HSTS/CSP, SSE disconnect"
```

---

## Task 2: Input Validation & Endpoint Hardening (Agent: Validation)

**Files:**
- Modify: `app/api/auth_routes.py:266-271`
- Modify: `app/api/feedback_routes.py:35-69`
- Modify: `app/api/url_routes.py:64-149`
- Modify: `app/services/database_service.py:182-183`
- Modify: `app/services/sentry_service.py:8-35`
- Modify: `app/api/history_routes.py:60,87`
- Modify: `app/api/share_routes.py:19`

### I1 — Fix logout to actually sign out

- [ ] **Step 1: Call logout_user in logout endpoint**

In `app/api/auth_routes.py`, change lines 266-271 from:

```python
@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout current user.
    """
    return {"success": True, "message": "Logged out successfully"}
```

to:

```python
@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Logout current user — invalidates Supabase session.
    """
    # Extract token from Authorization header to invalidate the correct session
    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ")[1] if " " in auth_header else None
    if token:
        try:
            await logout_user(token)
        except Exception as e:
            logger.warning(f"Logout sign_out failed (non-critical): {e}")
    return {"success": True, "message": "Logged out successfully"}
```

Ensure `Request` is imported from `fastapi` (check existing imports) and `logout_user` is imported from `app.services.auth_service`.

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/api/auth_routes.py`
Expected: No output

### I2 + I3 — Field length limits and event data size

- [ ] **Step 3: Add max_length to change_suggestion**

In `app/api/feedback_routes.py`, change line 39 from:

```python
    change_suggestion: Optional[str] = None
```

to:

```python
    change_suggestion: Optional[str] = Field(None, max_length=1000)
```

- [ ] **Step 4: Add event_data size validator**

In `app/api/feedback_routes.py`, add `import json` at the top. Then add a validator to `EventItem` class after the existing `validate_event_type` (after line 65):

```python
    @field_validator("event_data")
    @classmethod
    def validate_event_data_size(cls, v: dict) -> dict:
        if len(json.dumps(v, default=str)) > 10_000:
            raise ValueError("event_data too large (max 10KB)")
        return v
```

- [ ] **Step 5: Verify syntax**

Run: `python -m py_compile app/api/feedback_routes.py`
Expected: No output

### I4 — Rate limit URL endpoints

- [ ] **Step 6: Add rate limiting to URL routes**

In `app/api/url_routes.py`, add imports:

```python
from app.middleware.rate_limiter import limiter
from starlette.requests import Request
```

Add `@limiter.limit("10/minute")` decorator and `request: Request` parameter to:
- `POST /extract` (line 64)
- `GET /extract` (line 97)
- `POST /compare` (line 113)
- `GET /compare` (line 149)

Example for POST /extract:

```python
@router.post("/extract")
@limiter.limit("10/minute")
async def extract_product(request: Request, body: URLExtractRequest):
```

Note: the `request` parameter must be named `request` for slowapi to detect it. Rename the existing `request: URLExtractRequest` parameter to `body` to avoid conflict.

- [ ] **Step 7: Verify syntax**

Run: `python -m py_compile app/api/url_routes.py`
Expected: No output

### I5 — LIKE wildcard escaping

- [ ] **Step 8: Escape LIKE wildcards in search**

In `app/services/database_service.py`, change line 182-183 from:

```python
        if search:
            query = query.ilike("query", f"%{search}%")
```

to:

```python
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.ilike("query", f"%{escaped}%")
```

- [ ] **Step 9: Verify syntax**

Run: `python -m py_compile app/services/database_service.py`
Expected: No output

### I6 — Sentry breadcrumb token redaction

- [ ] **Step 10: Add before_breadcrumb hook**

In `app/services/sentry_service.py`, add a breadcrumb filter function before `init_sentry()`:

```python
import re

def _strip_tokens_from_breadcrumb(breadcrumb, hint):
    """Remove API tokens from breadcrumb URLs to prevent log exposure."""
    if breadcrumb.get("category") == "httplib" and "data" in breadcrumb:
        url = breadcrumb["data"].get("url", "")
        if url:
            breadcrumb["data"]["url"] = re.sub(
                r'token=[^&]+', 'token=REDACTED', url
            )
    return breadcrumb
```

Then in `sentry_sdk.init()`, add the hook:

```python
        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            traces_sample_rate=0.1,
            environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
            send_default_pii=False,
            before_breadcrumb=_strip_tokens_from_breadcrumb,
        )
```

- [ ] **Step 11: Verify syntax**

Run: `python -m py_compile app/services/sentry_service.py`
Expected: No output

### I8 — UUID validation on path params

- [ ] **Step 12: Change comparison_id to UUID type**

In `app/api/history_routes.py`, add import:

```python
from uuid import UUID
```

Change the GET endpoint (line 60) parameter from `comparison_id: str` to `comparison_id: UUID`.
Change the DELETE endpoint (line 87) parameter from `comparison_id: str` to `comparison_id: UUID`.

In `app/api/share_routes.py`, add import:

```python
from uuid import UUID
```

Change the POST endpoint (line 19) parameter from `comparison_id: str` to `comparison_id: UUID`.

Pass `str(comparison_id)` when calling database functions that expect a string.

- [ ] **Step 13: Verify syntax and commit Task 2**

Run:
```bash
python -m py_compile app/api/auth_routes.py
python -m py_compile app/api/feedback_routes.py
python -m py_compile app/api/url_routes.py
python -m py_compile app/services/database_service.py
python -m py_compile app/services/sentry_service.py
python -m py_compile app/api/history_routes.py
python -m py_compile app/api/share_routes.py
```

Expected: All clean

```bash
git add app/api/auth_routes.py app/api/feedback_routes.py app/api/url_routes.py app/services/database_service.py app/services/sentry_service.py app/api/history_routes.py app/api/share_routes.py
git commit -m "feat: input validation hardening — logout fix, field limits, rate limits, LIKE escape, UUID validation"
```

---

## Task 3: Concurrency Fixes + Exchange Rates (Agent: Concurrency)

**Files:**
- Create: `app/services/exchange_rate_service.py`
- Modify: `app/services/structured_comparison_service.py:197-202,3446-3453`
- Modify: `app/services/scoring_service.py:633-707`
- Modify: `app/services/cache_service.py:307-322`
- Modify: `app/services/api_budget_service.py:87-98`
- Modify: `app/services/trust_validation_service.py:10-74`

### C5 — Remove comparison service singleton

- [ ] **Step 1: Change get_comparison_service to return new instance**

In `app/services/structured_comparison_service.py`, replace lines 3446-3453:

```python
_service_instance = None

def get_comparison_service() -> StructuredComparisonService:
    """Get or create the comparison service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = StructuredComparisonService()
    return _service_instance
```

with:

```python
def get_comparison_service() -> StructuredComparisonService:
    """Create a new comparison service instance per request.

    Not a singleton — each request gets its own instance to prevent
    race conditions on mutable state (total_cost, _shopping_items_cache).
    """
    return StructuredComparisonService()
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output

### C6 — Remove mutable state from ScoringService

- [ ] **Step 3: Refactor _normalize_scores to return price_tiers**

In `app/services/scoring_service.py`, change `_normalize_scores()` (line 633-707).

Replace lines 644-651:

```python
        self._price_tiers = []
        for rs in raw_scores:
            price = rs.get("price_raw")
            if price is not None and price > 0:
                self._price_tiers.append(self._detect_price_tier(price))
            else:
                self._price_tiers.append("mid")
        self._is_cross_tier_flag = self._is_cross_tier(self._price_tiers)
```

with:

```python
        price_tiers = []
        for rs in raw_scores:
            price = rs.get("price_raw")
            if price is not None and price > 0:
                price_tiers.append(self._detect_price_tier(price))
            else:
                price_tiers.append("mid")
        is_cross_tier_flag = self._is_cross_tier(price_tiers)
```

Then on line 676, change:

```python
            self._compute_value_score(spec_scores[i], price_scores[i], self._price_tiers[i], self._is_cross_tier_flag)
```

to:

```python
            self._compute_value_score(spec_scores[i], price_scores[i], price_tiers[i], is_cross_tier_flag)
```

Change the return statement at line 707 from `return normalized` to:

```python
        return normalized, price_tiers, is_cross_tier_flag
```

Then find all callers of `_normalize_scores()` in the same file and update them to unpack the tuple. Search for `self._normalize_scores(` and change from:

```python
normalized = self._normalize_scores(raw_scores, products_data, category)
```

to:

```python
normalized, price_tiers, is_cross_tier = self._normalize_scores(raw_scores, products_data, category)
```

Also find any later references to `self._price_tiers` or `self._is_cross_tier_flag` in `compute_scores()` and replace with the local variables. Pass `price_tiers` as a parameter to any method that currently reads `self._price_tiers`.

- [ ] **Step 4: Remove self._price_tiers initialization from __init__ if present**

Search for `self._price_tiers` in `__init__` and remove it. Also remove `self._is_cross_tier_flag` if present.

- [ ] **Step 5: Verify syntax**

Run: `python -m py_compile app/services/scoring_service.py`
Expected: No output

### C7 — Atomic Redis operations

- [ ] **Step 6: Fix add_api_cost with INCRBYFLOAT**

In `app/services/cache_service.py`, replace lines 307-322:

```python
def add_api_cost(cost: float) -> float:
    """Add to monthly API cost tracker."""
    if not redis_client:
        return 0.0

    month = datetime.now().strftime("%Y-%m")
    key = f"cost:{month}"

    try:
        current = get_monthly_cost()
        new_total = current + cost
        _redis_set(key, str(new_total), ex=32 * 86400)
        return new_total
    except Exception as e:
        logger.error(f"Error adding API cost: {e}")
        return 0.0
```

with:

```python
def add_api_cost(cost: float) -> float:
    """Add to monthly API cost tracker (atomic operation)."""
    if not redis_client:
        return 0.0

    month = datetime.now().strftime("%Y-%m")
    key = f"cost:{month}"

    try:
        new_total = redis_client.incrbyfloat(key, cost)
        _redis_expire(key, 32 * 86400)
        return float(new_total)
    except Exception as e:
        logger.error(f"Error adding API cost: {e}")
        return 0.0
```

- [ ] **Step 7: Fix record_usage with INCRBY**

In `app/services/api_budget_service.py`, replace lines 87-98:

```python
def record_usage(provider: str, count: int = 1) -> None:
    """Record API usage after successful call."""
    try:
        key = _budget_key(provider)
        for _ in range(count):
            _redis_incr(key)
        # Set TTL for monthly keys
        config = PROVIDER_CONFIGS.get(provider, {})
        if not config.get("is_lifetime"):
            _redis_expire(key, _MONTHLY_TTL)
    except Exception as e:
        logger.warning(f"[BUDGET] Error recording {provider}: {e}")
```

with:

```python
def record_usage(provider: str, count: int = 1) -> None:
    """Record API usage after successful call (atomic operation)."""
    try:
        key = _budget_key(provider)
        if redis_client:
            redis_client.incrby(key, count)
        else:
            # Fallback to individual increments via helper
            for _ in range(count):
                _redis_incr(key)
        # Set TTL for monthly keys
        config = PROVIDER_CONFIGS.get(provider, {})
        if not config.get("is_lifetime"):
            _redis_expire(key, _MONTHLY_TTL)
    except Exception as e:
        logger.warning(f"[BUDGET] Error recording {provider}: {e}")
```

- [ ] **Step 8: Verify syntax**

Run:
```bash
python -m py_compile app/services/cache_service.py
python -m py_compile app/services/api_budget_service.py
```
Expected: No output

### I13 — Fix trust validation flagged counter

- [ ] **Step 9: Add contradiction detection logic**

In `app/services/trust_validation_service.py`, replace the dimension loop (lines 48-59):

```python
    for dim in dims:
        s0 = b0.get(dim, MISSING_SCORE)
        s1 = b1.get(dim, MISSING_SCORE)
        if s0 is None or s1 is None or s0 == MISSING_SCORE or s1 == MISSING_SCORE:
            continue

        gap = abs(s0 - s1)
        if gap < 3.0:
            # Scores are essentially tied — any strong claim is overclaiming
            softened += 1
        else:
            validated += 1
```

with:

```python
    # Determine score-based winner direction for contradiction detection
    verdict_winner = verdict.get("winner_index", 0)

    for dim in dims:
        s0 = b0.get(dim, MISSING_SCORE)
        s1 = b1.get(dim, MISSING_SCORE)
        if s0 is None or s1 is None or s0 == MISSING_SCORE or s1 == MISSING_SCORE:
            continue

        gap = abs(s0 - s1)
        if gap < 3.0:
            softened += 1
        else:
            # Check if GPT verdict winner contradicts the score leader for this dimension
            score_dim_leader = 0 if s0 > s1 else 1
            if score_dim_leader != verdict_winner and gap >= 10.0:
                # Significant contradiction: scores clearly favor one product
                # but GPT's overall winner is the other
                flagged += 1
            else:
                validated += 1
```

- [ ] **Step 10: Verify syntax**

Run: `python -m py_compile app/services/trust_validation_service.py`
Expected: No output

### Exchange Rate Service

- [ ] **Step 11: Create exchange_rate_service.py**

Create `app/services/exchange_rate_service.py`:

```python
"""Exchange rate service — daily rates with Redis cache + hardcoded fallback."""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.services.cache_service import _redis_get, _redis_set

logger = logging.getLogger(__name__)

# Free API — no key needed, ECB data, reliable
_API_URL = "https://api.frankfurter.app/latest"

# Fallback rates (last known good values, updated 2026-03-27)
_FALLBACK_RATES_TO_BHD = {
    "USD": 0.3760,
    "EUR": 0.4100,
    "GBP": 0.4750,
    "SAR": 0.1003,
    "AED": 0.1024,
    "KWD": 1.2300,
    "QAR": 0.1033,
    "OMR": 0.9770,
    "BHD": 1.0,
}

_CACHE_TTL = 86400  # 24 hours


async def get_rate(from_currency: str, to_currency: str = "BHD") -> float:
    """Get exchange rate between two currencies.

    Fetches daily from frankfurter.app, caches in Redis for 24h.
    Falls back to hardcoded rates if API and cache both fail.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    # Try cached rates first
    rates = await _get_cached_rates()
    if rates:
        return _compute_rate(rates, from_currency, to_currency)

    # Fetch fresh rates
    rates = await _fetch_rates()
    if rates:
        return _compute_rate(rates, from_currency, to_currency)

    # Fallback to hardcoded
    logger.warning(f"[EXCHANGE] Using fallback rates for {from_currency}->{to_currency}")
    return _compute_rate(_FALLBACK_RATES_TO_BHD, from_currency, to_currency)


async def _get_cached_rates() -> Optional[dict]:
    """Get rates from Redis cache."""
    import json
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"exchange_rates:{today}"
    data = _redis_get(key)
    if data:
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


async def _fetch_rates() -> Optional[dict]:
    """Fetch fresh rates from frankfurter.app and cache them."""
    import json
    currencies = "BHD,SAR,AED,KWD,QAR,OMR,EUR,GBP"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _API_URL,
                params={"from": "USD", "to": currencies},
            )
            resp.raise_for_status()
            data = resp.json()

        rates = data.get("rates", {})
        # Add USD=1.0 (base currency)
        rates["USD"] = 1.0

        # Cache for 24h
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"exchange_rates:{today}"
        _redis_set(key, json.dumps(rates), ex=_CACHE_TTL)

        logger.info(f"[EXCHANGE] Fetched fresh rates: {len(rates)} currencies")
        return rates

    except Exception as e:
        logger.warning(f"[EXCHANGE] Failed to fetch rates: {e}")
        return None


def _compute_rate(rates: dict, from_currency: str, to_currency: str) -> float:
    """Compute cross-rate between any two currencies via USD."""
    # If rates are BHD-based (fallback), use directly
    if "USD" in rates and isinstance(rates.get("USD"), (int, float)):
        # Rates are relative to USD
        from_rate = rates.get(from_currency, 1.0)
        to_rate = rates.get(to_currency, 1.0)
        if from_rate == 0:
            return 1.0
        return to_rate / from_rate

    # Fallback: direct BHD lookup
    from_bhd = rates.get(from_currency, 1.0)
    to_bhd = rates.get(to_currency, 1.0)
    if from_bhd == 0:
        return 1.0
    return to_bhd / from_bhd
```

- [ ] **Step 12: Verify syntax and commit Task 3**

Run: `python -m py_compile app/services/exchange_rate_service.py`
Expected: No output

```bash
git add app/services/exchange_rate_service.py app/services/structured_comparison_service.py app/services/scoring_service.py app/services/cache_service.py app/services/api_budget_service.py app/services/trust_validation_service.py
git commit -m "feat: concurrency fixes — remove singleton, atomic Redis ops, trust flagging, exchange rate service"
```

---

## Task 4: File Decomposition (Agent: Decomposition)

> **IMPORTANT:** This task depends on Task 3 completing first (C5 changes the singleton in `structured_comparison_service.py`). Wait for Task 3's commit before starting.

**Files:**
- Create: `app/services/price_service.py`
- Create: `app/services/rating_service.py`
- Create: `app/services/review_service.py`
- Create: `app/services/fact_check_service.py`
- Create: `app/services/response_builder.py`
- Modify: `app/services/structured_comparison_service.py` (remove extracted code, add imports)

### Extraction approach

Read the full `app/services/structured_comparison_service.py` file. For each module below:
1. Identify all functions listed for extraction
2. Identify all constants/class variables used by those functions
3. Identify all imports needed by those functions
4. Extract to new file with proper imports
5. Replace original functions with imports from new module
6. Verify each extraction compiles

**Key rule:** Functions that need the orchestrator's per-request state (e.g., `self._shopping_items_cache`) must receive it as a parameter. Convert `self.method()` patterns to module-level functions with explicit parameters.

- [ ] **Step 1: Read the full structured_comparison_service.py**

Read the entire file to identify exact line ranges for extraction. Map out which functions call which, which constants they use, and which imports they need.

- [ ] **Step 2: Extract price_service.py**

Create `app/services/price_service.py` containing:
- All price-related functions: `_fetch_price_data()`, `_fetch_page_price()`, `_curl_fetch_html()`, `_extract_price_from_html()`, `_fetch_pharmacy_price()`, iHerb methods, `_convert_to_bhd()`, `_parse_price_string()`, `_validate_price_query()`, `_validate_scrape_url()`, `_is_luxury_brand()`, `_is_supplement_query()`
- All price-related constants: `COUNTERFEIT_KEYWORDS`, `OFFICIAL_BRAND_DOMAINS`, `LUXURY_BRANDS`, `GCC_RETAILER_DOMAINS`, `TRUSTED_RETAILERS`, `SUPPLEMENT_BRANDS`, `IHERB_BASE_URL`, currency constants
- Convert from `self.method()` to standalone functions. Pass `shopping_items_cache` dict as parameter where needed.
- Update `_convert_to_bhd()` to use `exchange_rate_service.get_rate()` with hardcoded fallback.

Run: `python -m py_compile app/services/price_service.py`

- [ ] **Step 3: Extract rating_service.py**

Create `app/services/rating_service.py` containing:
- `_fetch_ratings()`, `_extract_shopping_rating()`, `_build_retailer_url()`, rating consensus logic
- `TRUSTED_RATING_RETAILERS`, `LUXURY_FASHION_RETAILERS`
- Pass `shopping_items_cache` as parameter.

Run: `python -m py_compile app/services/rating_service.py`

- [ ] **Step 4: Extract review_service.py**

Create `app/services/review_service.py` containing:
- `_fetch_reviews()`, `_clean_review_content()`, `_clean_review_citations()`
- Fix M5: Update `_clean_review_citations()` to process `review_summary.highlights[].point` format
- Fix M6: Remove dead code processing `detailed_praises`/`detailed_complaints`

Run: `python -m py_compile app/services/review_service.py`

- [ ] **Step 5: Extract fact_check_service.py**

Create `app/services/fact_check_service.py` containing:
- `_fact_check_product()` and all sub-functions (citation verification, shopping cross-check, review sentiment check, price deviation check)
- Confidence computation logic

Run: `python -m py_compile app/services/fact_check_service.py`

- [ ] **Step 6: Create response_builder.py**

Create `app/services/response_builder.py` containing:

```python
"""Response builder — unified response assembly for sync and streaming paths."""
from typing import Dict, Any, List, Optional


def build_comparison_response(
    product_data: List[Dict[str, Any]],
    comparison: Dict[str, Any],
    scoring_result: Dict[str, Any],
    behavior_profile: Optional[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]],
    from_cache: bool,
    query: str,
    region: str,
    category: str,
    total_cost: float,
    api_calls: int,
    duration_ms: int,
    category_switched: bool = False,
    selected_category: Optional[str] = None,
    trust_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the full comparison response dict.

    Called by both compare_from_text() and compare_from_text_streaming().
    Includes backward compatibility aliases.
    """
    # ... Extract the response assembly logic from compare_from_text() lines ~385-502
    # Build: overview, specs, reviews, scoring, personalization, metadata
    # Add backward compat: products, comparison, winner_index, recommendation, key_differences
    ...
```

The actual body should be extracted from the duplicated code in `compare_from_text()` (around lines 385-502). This is a direct extraction — copy the logic, parameterize the inputs that were previously accessed via `self` or local variables.

Run: `python -m py_compile app/services/response_builder.py`

- [ ] **Step 7: Update structured_comparison_service.py**

In the orchestrator file:
1. Remove all extracted functions and constants
2. Add imports at the top:

```python
from app.services.price_service import fetch_price_data, convert_to_bhd, parse_price_string, is_luxury_brand, is_supplement_query, validate_price_query
from app.services.rating_service import fetch_ratings
from app.services.review_service import fetch_reviews, clean_review_content, clean_review_citations
from app.services.fact_check_service import fact_check_product
from app.services.response_builder import build_comparison_response
```

3. Replace response assembly code in both `compare_from_text()` and `compare_from_text_streaming()` with a single call to `build_comparison_response()`
4. Update internal method calls to use imported functions

- [ ] **Step 8: Verify the orchestrator compiles**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output

- [ ] **Step 9: Run existing tests to verify nothing broke**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x`
Expected: All 1,398+ tests pass. If any fail due to import path changes, fix the imports in the test files.

- [ ] **Step 10: Commit Task 4**

```bash
git add app/services/price_service.py app/services/rating_service.py app/services/review_service.py app/services/fact_check_service.py app/services/response_builder.py app/services/structured_comparison_service.py
git commit -m "refactor: decompose monolith into price, rating, review, fact-check, response-builder modules"
```

---

## Task 5: Tests + Cross-QA (Agent: QA)

> **IMPORTANT:** This task depends on Tasks 1-4 all completing first. Wait for all commits before starting.

**Files:**
- Create: `tests/test_security_hardening.py`
- Create: `tests/test_concurrency_fixes.py`
- Create: `tests/test_exchange_rate_service.py`
- Create: `tests/test_decomposed_services.py`

- [ ] **Step 1: Create test_security_hardening.py**

```python
"""Tests for security hardening — C1-C4 + headers + SSE disconnect."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.utils.url_validator import validate_external_url


class TestSSRFProtection:
    """C2 — SSRF validator tests."""

    def test_rejects_localhost(self):
        assert validate_external_url("http://localhost/secret") is False

    def test_rejects_127_0_0_1(self):
        assert validate_external_url("http://127.0.0.1/admin") is False

    def test_rejects_private_10_x(self):
        assert validate_external_url("http://10.0.0.1/internal") is False

    def test_rejects_private_172_16(self):
        assert validate_external_url("http://172.16.0.1/") is False

    def test_rejects_private_192_168(self):
        assert validate_external_url("http://192.168.1.1/") is False

    def test_rejects_cloud_metadata(self):
        assert validate_external_url("http://169.254.169.254/latest/meta-data/") is False

    def test_rejects_non_http_scheme(self):
        assert validate_external_url("ftp://example.com/file") is False
        assert validate_external_url("file:///etc/passwd") is False

    def test_allows_public_https(self):
        assert validate_external_url("https://www.amazon.com/product/123") is True

    def test_allows_gcc_retailers(self):
        assert validate_external_url("https://www.ounass.com/product") is True


class TestAdminAuthOnEndpoints:
    """C1 — Cache flush and parse require admin key."""

    def test_cache_flush_requires_admin_key(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.delete("/api/v1/text/cache", params={"q": "test"})
        assert resp.status_code in (403, 422)  # 403 no key, 422 missing header

    def test_parse_requires_admin_key(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/api/v1/text/parse", params={"q": "test"})
        assert resp.status_code in (403, 422)


class TestTimingSafeAdminKey:
    """C3 — Admin key uses hmac.compare_digest."""

    def test_uses_hmac_compare_digest(self):
        import hmac
        from app.api.admin_routes import verify_admin_key
        # Verify the function source uses hmac.compare_digest
        import inspect
        source = inspect.getsource(verify_admin_key)
        assert "hmac.compare_digest" in source


class TestSecurityHeaders:
    """HSTS and CSP headers present."""

    def test_hsts_header_present(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert "strict-transport-security" in resp.headers

    def test_csp_header_present(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert "content-security-policy" in resp.headers
```

Run: `python -m pytest tests/test_security_hardening.py -v`
Expected: All pass

- [ ] **Step 2: Create test_concurrency_fixes.py**

```python
"""Tests for concurrency fixes — C5-C7 + I13."""
import pytest
from unittest.mock import patch, MagicMock


class TestComparisonServiceNotSingleton:
    """C5 — Each call returns a new instance."""

    def test_returns_different_instances(self):
        from app.services.structured_comparison_service import get_comparison_service
        svc1 = get_comparison_service()
        svc2 = get_comparison_service()
        assert svc1 is not svc2

    def test_instances_have_independent_state(self):
        from app.services.structured_comparison_service import get_comparison_service
        svc1 = get_comparison_service()
        svc2 = get_comparison_service()
        svc1.total_cost = 0.05
        assert svc2.total_cost == 0.0


class TestScoringServiceNormalize:
    """C6 — _normalize_scores returns price_tiers, not self."""

    def test_normalize_returns_tuple(self):
        from app.services.scoring_service import get_scoring_service
        svc = get_scoring_service()
        raw_scores = [
            {"price_raw": 50, "spec_raw": 70, "review_raw": 4.2, "reliability_raw": 80, "popularity_raw": 60},
            {"price_raw": 80, "spec_raw": 65, "review_raw": 4.0, "reliability_raw": 75, "popularity_raw": 55},
        ]
        products = [{"price": {"amount": 50}}, {"price": {"amount": 80}}]
        result = svc._normalize_scores(raw_scores, products, "electronics")
        assert isinstance(result, tuple)
        assert len(result) == 3  # normalized, price_tiers, is_cross_tier

    def test_no_price_tiers_on_self(self):
        from app.services.scoring_service import get_scoring_service
        svc = get_scoring_service()
        assert not hasattr(svc, "_price_tiers") or svc._price_tiers is None


class TestAtomicCostTracking:
    """C7 — add_api_cost uses INCRBYFLOAT."""

    @patch("app.services.cache_service.redis_client")
    def test_uses_incrbyfloat(self, mock_redis):
        mock_redis.incrbyfloat.return_value = 0.05
        from app.services.cache_service import add_api_cost
        result = add_api_cost(0.05)
        mock_redis.incrbyfloat.assert_called_once()
        assert result == 0.05


class TestAtomicBudgetTracking:
    """C7 — record_usage uses INCRBY."""

    @patch("app.services.api_budget_service.redis_client", new_callable=MagicMock)
    @patch("app.services.api_budget_service._redis_expire")
    def test_uses_incrby_for_count(self, mock_expire, mock_redis):
        from app.services.api_budget_service import record_usage
        record_usage("serper", count=5)
        mock_redis.incrby.assert_called_once()
        call_args = mock_redis.incrby.call_args
        assert call_args[0][1] == 5  # count argument


class TestTrustValidationFlagged:
    """I13 — flagged counter increments on contradictions."""

    def test_flagged_increments_on_contradiction(self):
        from app.services.trust_validation_service import validate_verdict
        verdict = {"winner_index": 0}
        scoring_result = {
            "winner_index": 0,
            "scores": {
                "product_0": {"breakdown": {"performance": 40, "display": 45, "camera": 50, "battery": 55, "value": 60, "software": 65}},
                "product_1": {"breakdown": {"performance": 80, "display": 85, "camera": 90, "battery": 75, "value": 70, "software": 80}},
            }
        }
        result = validate_verdict(verdict, scoring_result, "electronics")
        assert result["claims_flagged"] > 0

    def test_no_flags_when_aligned(self):
        from app.services.trust_validation_service import validate_verdict
        verdict = {"winner_index": 0}
        scoring_result = {
            "winner_index": 0,
            "scores": {
                "product_0": {"breakdown": {"performance": 80, "display": 75, "camera": 85, "battery": 70, "value": 90, "software": 80}},
                "product_1": {"breakdown": {"performance": 60, "display": 55, "camera": 65, "battery": 50, "value": 70, "software": 60}},
            }
        }
        result = validate_verdict(verdict, scoring_result, "electronics")
        assert result["claims_flagged"] == 0
```

Run: `python -m pytest tests/test_concurrency_fixes.py -v`
Expected: All pass

- [ ] **Step 3: Create test_exchange_rate_service.py**

```python
"""Tests for exchange rate service."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
class TestExchangeRateService:

    @patch("app.services.exchange_rate_service._redis_get", return_value=None)
    @patch("app.services.exchange_rate_service._redis_set")
    @patch("app.services.exchange_rate_service.httpx.AsyncClient")
    async def test_fetches_and_caches_rates(self, mock_client_cls, mock_set, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"rates": {"BHD": 0.376, "SAR": 3.75, "AED": 3.67}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        from app.services.exchange_rate_service import get_rate
        rate = await get_rate("USD", "BHD")
        assert isinstance(rate, float)
        assert rate > 0
        mock_set.assert_called_once()

    @patch("app.services.exchange_rate_service._redis_get")
    async def test_returns_cached_rate(self, mock_get):
        mock_get.return_value = json.dumps({"USD": 1.0, "BHD": 0.376, "SAR": 3.75})
        from app.services.exchange_rate_service import get_rate
        rate = await get_rate("USD", "BHD")
        assert isinstance(rate, float)
        assert rate > 0

    @patch("app.services.exchange_rate_service._redis_get", return_value=None)
    @patch("app.services.exchange_rate_service.httpx.AsyncClient", side_effect=Exception("Network error"))
    async def test_falls_back_to_hardcoded_on_failure(self, mock_client, mock_get):
        from app.services.exchange_rate_service import get_rate
        rate = await get_rate("USD", "BHD")
        assert isinstance(rate, float)
        assert 0.3 < rate < 0.5  # Reasonable BHD range

    @patch("app.services.exchange_rate_service._redis_get", return_value=None)
    @patch("app.services.exchange_rate_service._redis_set")
    @patch("app.services.exchange_rate_service.httpx.AsyncClient")
    async def test_same_currency_returns_1(self, mock_client, mock_set, mock_get):
        from app.services.exchange_rate_service import get_rate
        rate = await get_rate("BHD", "BHD")
        assert rate == 1.0
```

Run: `python -m pytest tests/test_exchange_rate_service.py -v`
Expected: All pass

- [ ] **Step 4: Create test_decomposed_services.py**

```python
"""Tests for decomposed service modules."""
import pytest
from unittest.mock import patch, MagicMock


class TestPriceServiceStandalone:
    """Price service functions work independently."""

    def test_validate_price_query_rejects_short(self):
        from app.services.price_service import validate_price_query
        assert validate_price_query("ab") is False

    def test_validate_price_query_accepts_valid(self):
        from app.services.price_service import validate_price_query
        assert validate_price_query("iPhone 15 Pro") is True

    def test_is_luxury_brand_detects_gucci(self):
        from app.services.price_service import is_luxury_brand
        assert is_luxury_brand("Gucci") is True

    def test_is_luxury_brand_rejects_samsung(self):
        from app.services.price_service import is_luxury_brand
        assert is_luxury_brand("Samsung") is False

    def test_is_supplement_query_detects_vitamin(self):
        from app.services.price_service import is_supplement_query
        assert is_supplement_query("Vitamin D3 vs Vitamin C") is True


class TestReviewServiceCleaning:
    """Review service cleans current format, not dead legacy fields."""

    def test_clean_review_citations_processes_highlights(self):
        from app.services.review_service import clean_review_citations
        review = {
            "review_summary": {
                "highlights": [
                    {"point": "Great battery [snippet_1]", "sentiment": "positive"}
                ]
            }
        }
        snippets = {"snippet_1": "https://example.com"}
        result = clean_review_citations(review, snippets)
        # Should replace [snippet_1] with domain attribution
        highlight = result["review_summary"]["highlights"][0]["point"]
        assert "[snippet_1]" not in highlight


class TestResponseBuilder:
    """Response builder produces consistent output."""

    def test_build_response_has_required_keys(self):
        from app.services.response_builder import build_comparison_response
        result = build_comparison_response(
            product_data=[
                {"brand": "Apple", "name": "iPhone 15", "price": {"amount": 300, "currency": "BHD"}},
                {"brand": "Samsung", "name": "Galaxy S24", "price": {"amount": 280, "currency": "BHD"}},
            ],
            comparison={"winner_index": 0, "recommendation": "iPhone wins"},
            scoring_result={"scores": {}, "winner_index": 0},
            behavior_profile=None,
            user_preferences=None,
            from_cache=False,
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
            category="electronics",
            total_cost=0.01,
            api_calls=3,
            duration_ms=2500,
        )
        assert "overview" in result
        assert "specs" in result
        assert "scoring" in result
        assert "metadata" in result
        # Backward compat aliases
        assert "products" in result
```

Run: `python -m pytest tests/test_decomposed_services.py -v`
Expected: All pass

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All 1,398+ existing tests pass plus new tests

- [ ] **Step 6: Commit Task 5**

```bash
git add tests/test_security_hardening.py tests/test_concurrency_fixes.py tests/test_exchange_rate_service.py tests/test_decomposed_services.py
git commit -m "test: add tests for security hardening, concurrency fixes, exchange rates, decomposed services"
```

---

## Cross-QA Assignments

After all tasks are committed:

| Reviewer | Reviews | What to check |
|----------|---------|---------------|
| Security agent | Task 2 (Validation) | Input validation correct, rate limits applied, UUID handling |
| Validation agent | Task 1 (Security) | SSRF covers all private ranges, auth properly applied, headers correct |
| Concurrency agent | Task 4 (Decomposition) | Imports correct, no broken references, state properly passed as params |
| QA agent | Task 3 (Concurrency) | Atomic ops correct, singleton removal clean, trust flagging logic sound |

Each reviewer reads the modified files and runs: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x`

If any issue found: send work back to original agent for rework. Do NOT mark complete until all QA passes.

---

## Final Validation

After all cross-QA passes:

```bash
# Full unit test suite
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Syntax check all modified files
python -m py_compile app/main.py
python -m py_compile app/api/text_routes.py
python -m py_compile app/api/admin_routes.py
python -m py_compile app/api/auth_routes.py
python -m py_compile app/api/feedback_routes.py
python -m py_compile app/api/url_routes.py
python -m py_compile app/api/history_routes.py
python -m py_compile app/api/share_routes.py
python -m py_compile app/middleware/security.py
python -m py_compile app/services/structured_comparison_service.py
python -m py_compile app/services/scoring_service.py
python -m py_compile app/services/cache_service.py
python -m py_compile app/services/api_budget_service.py
python -m py_compile app/services/trust_validation_service.py
python -m py_compile app/services/sentry_service.py
python -m py_compile app/services/database_service.py
python -m py_compile app/services/exchange_rate_service.py
python -m py_compile app/services/price_service.py
python -m py_compile app/services/rating_service.py
python -m py_compile app/services/review_service.py
python -m py_compile app/services/fact_check_service.py
python -m py_compile app/services/response_builder.py
python -m py_compile app/utils/url_validator.py

# TypeScript check (frontend untouched, should still be clean)
cd SmartCompareApp && npx tsc --noEmit
```
