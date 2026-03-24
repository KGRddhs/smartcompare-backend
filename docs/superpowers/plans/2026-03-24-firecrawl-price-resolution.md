# Firecrawl Price Resolution + Cascade Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace broken Cloudflare/Microlink JS rendering with Firecrawl + Scrape.do, add circuit breakers, credit tracking, input validation, and cost observability so luxury/brand-exclusive product prices are real instead of estimated.

**Architecture:** Gated price cascade with 4 layers of defense: Firecrawl Smart Wait (official sites) → authorized retailers (curl_cffi) → GCC retailers (curl_cffi) → Scrape.do rendering fallback. Each layer guarded by circuit breakers and credit budgets stored in Redis. Admin cost dashboard for monitoring burn rate.

**Tech Stack:** Python 3.12, FastAPI, httpx, Upstash Redis, Firecrawl API, Scrape.do API, pytest

**Spec:** `docs/superpowers/specs/2026-03-24-firecrawl-price-resolution-design.md`

---

## File Map

### New Files
| File | Responsibility |
|------|---------------|
| `app/services/api_budget_service.py` | Credit tracking + circuit breakers for external APIs (Firecrawl, Scrape.do, Serper) |
| `app/services/firecrawl_service.py` | Thin async wrapper around Firecrawl `/v1/scrape` API |
| `app/services/scrapedo_service.py` | Thin async wrapper around Scrape.do `render=true` API |
| `tests/test_api_budget_service.py` | Budget tracking, circuit breaker states, Redis keys, exhaustion |
| `tests/test_firecrawl_service.py` | Firecrawl API mocking, Smart Wait, price extraction, errors |
| `tests/test_scrapedo_service.py` | Scrape.do rendering mock, HTML extraction, errors |
| `tests/test_cascade_hardening.py` | Full cascade flow: gates, early returns, leak prevention, conditional 1.5d |
| `tests/test_input_validation.py` | Price query validation, URL validation, edge cases |
| `tests/test_cost_dashboard.py` | Admin `/costs` endpoint format, auth, calculations |

### Modified Files
| File | Changes |
|------|---------|
| `app/services/structured_comparison_service.py` | Add Gate 0/2, wire Firecrawl (1.5a), Scrape.do (1.5d), expand GCC retailers, remove Cloudflare/Microlink, add `failed_curl_urls` tracking, add `_validate_price_query()`, `_validate_scrape_url()` |
| `app/api/admin_routes.py` | Add `GET /api/v1/admin/costs` endpoint |
| `app/main.py` | Remove 3 diagnostic endpoints (lines 157-399) |
| `tests/test_js_rendering.py` | Replace Cloudflare/Microlink tests with Firecrawl/Scrape.do integration |
| `tests/test_page_scraping.py` | Update `_fetch_page_price` flow (no more JS_ONLY_DOMAINS) |
| `tests/test_luxury_price_tiers.py` | Add expanded GCC retailers, Firecrawl tier |

---

## Agent Team Assignment

| Agent | Tasks | Role |
|-------|-------|------|
| **backend-1** | Tasks 1, 2, 3 | New services: api_budget_service, firecrawl_service, scrapedo_service |
| **backend-2** | Tasks 4, 5, 6 | Cascade integration: wire into structured_comparison_service, admin endpoint, cleanup |
| **test-writer** | Tasks 7, 8, 9 | Tests for all new code: budget, firecrawl, scrapedo, cascade, validation, dashboard |
| **qa-reviewer** | Task 10 | Cross-QA all work: run full test suite, review each agent's output, send back if subpar |

**Dependency order:** Phase 0 (validation spike) first. Tasks 1-3 can run in parallel. Task 4 depends on Tasks 1-3. Tasks 5-6 depend on Task 4. Tasks 7-9 can start in parallel with Tasks 1-3 (TDD: write tests first). Task 10 runs after all others complete.

---

## Phase 0: Validation Spike (team lead, before any code)

**Purpose:** Confirm Firecrawl + Scrape.do actually work on luxury domains before building a whole cascade around them. If they fail, the design needs revision BEFORE implementation.

- [ ] **Step 1: Sign up for Firecrawl** at https://firecrawl.dev — free tier gives 500 lifetime scrapes
- [ ] **Step 2: Get API key** from dashboard, set locally: `export FIRECRAWL_API_KEY=fc-...`
- [ ] **Step 3: Test 3 luxury URLs via curl**

```bash
# Louis Vuitton product page
curl -s -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://us.louisvuitton.com/eng-us/products/neverfull-mm-monogram-nvprod4900001v","formats":["html"],"waitFor":5000}' \
  | python -c "import sys,json; d=json.load(sys.stdin); html=d.get('data',{}).get('html',''); print(f'Size: {len(html)} bytes'); print('Has price:','$' in html or 'price' in html.lower()[:5000])"

# Hermes product page
curl -s -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.hermes.com/us/en/product/birkin-30-bag-H078277CK89/","formats":["html"],"waitFor":5000}' \
  | python -c "import sys,json; d=json.load(sys.stdin); html=d.get('data',{}).get('html',''); print(f'Size: {len(html)} bytes'); print('Has price:','$' in html or 'price' in html.lower()[:5000])"

# Chanel product page
curl -s -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.chanel.com/us/fashion/handbags/c/1x1x1/","formats":["html"],"waitFor":5000}' \
  | python -c "import sys,json; d=json.load(sys.stdin); html=d.get('data',{}).get('html',''); print(f'Size: {len(html)} bytes'); print('Has price:','$' in html or 'price' in html.lower()[:5000])"
```

- [ ] **Step 4: Evaluate results**
  - If 2+ of 3 return price data → proceed with implementation
  - If 1 of 3 → proceed with caution, note which domains fail
  - If 0 of 3 → STOP. Revisit design. Consider expanding GCC retailer coverage as primary strategy instead.

- [ ] **Step 5: Test Scrape.do** (optional, sign up at https://scrape.do — 1,000/mo free)

```bash
curl -s "https://api.scrape.do?token=$SCRAPEDO_API_TOKEN&url=https://ounass.com/search?q=louis+vuitton&render=true" \
  | python -c "import sys; html=sys.stdin.read(); print(f'Size: {len(html)} bytes'); print('Has price:', 'BHD' in html or 'price' in html.lower()[:5000])"
```

- [ ] **Step 6: Document results** in a comment on this plan or in the team chat before proceeding.

---

## Task 1: API Budget Service (backend-1)

**Files:**
- Create: `app/services/api_budget_service.py`
- Test: `tests/test_api_budget_service.py` (written by test-writer, Task 7)

**Context:** This service manages credit tracking and circuit breakers for Firecrawl, Scrape.do, and Serper. Uses Upstash Redis for atomic counters.

**IMPORTANT:** `cache_service.py` does NOT have a `_get_redis_client()` function. It has module-level helper functions: `_redis_get(key)`, `_redis_set(key, value, ex)`, `_redis_incr(key)`, `_redis_expire(key, seconds)`. The budget service MUST use these functions instead of raw Redis calls. The helpers handle error logging and return safe defaults (None/0/False) when Redis is unavailable.

- [ ] **Step 1: Read `app/services/cache_service.py`** to confirm the helper function signatures: `_redis_get(key) -> Optional[str]`, `_redis_set(key, value, ex=None) -> bool`, `_redis_incr(key) -> int`, `_redis_expire(key, seconds) -> bool`.

- [ ] **Step 2: Create `app/services/api_budget_service.py`** using cache_service helpers:

```python
"""API Budget Service — credit tracking + circuit breakers for external APIs.

Uses cache_service helpers (_redis_get, _redis_set, _redis_incr, _redis_expire)
for Redis access. Gracefully degrades if Redis is unavailable.
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any

from app.services.cache_service import _redis_get, _redis_set, _redis_incr, _redis_expire

logger = logging.getLogger(__name__)

# Provider configurations — budgets and thresholds
PROVIDER_CONFIGS = {
    "firecrawl": {
        "monthly_limit": 450,       # 500 free, save 50 buffer
        "warn_at": 400,
        "is_lifetime": True,        # Lifetime credits, not monthly-resetting
    },
    "scrapedo": {
        "monthly_limit": 900,       # 1,000/mo free, save 100 buffer
        "warn_at": 800,
        "is_lifetime": False,       # Monthly reset
    },
    "serper": {
        "monthly_limit": 2200,      # 2,500 credits, save 300 buffer
        "warn_at": 2000,
        "is_lifetime": True,
    },
}

# Circuit breaker config
CB_FAILURE_THRESHOLD = 3           # consecutive failures to trip
CB_RECOVERY_TIMEOUT = 600          # 10 min cooldown
CB_HALF_OPEN_MAX_CALLS = 1         # 1 test call in half-open

# Circuit breaker states
CB_CLOSED = "closed"
CB_OPEN = "open"
CB_HALF_OPEN = "half_open"

# TTL for circuit breaker state keys (1 hour)
_CB_TTL = 3600
# TTL for monthly budget keys (35 days)
_MONTHLY_TTL = 35 * 24 * 3600


def _budget_key(provider: str) -> str:
    """Redis key for budget counter."""
    config = PROVIDER_CONFIGS.get(provider, {})
    if config.get("is_lifetime"):
        return f"budget:{provider}:lifetime"
    month = datetime.utcnow().strftime("%Y-%m")
    return f"budget:{provider}:{month}"


def _circuit_key(provider: str) -> str:
    """Redis key for circuit breaker state."""
    return f"circuit:{provider}"


def has_budget(provider: str) -> bool:
    """Check if provider has remaining budget. Returns True if Redis unavailable (fail-open)."""
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return False
    try:
        raw = _redis_get(_budget_key(provider))
        if raw is None:
            return True  # No usage yet or Redis down
        used = int(raw)
        remaining = config["monthly_limit"] - used
        if remaining <= 0:
            logger.warning(f"[BUDGET] {provider} budget exhausted ({used}/{config['monthly_limit']})")
            return False
        if used >= config.get("warn_at", float("inf")):
            logger.warning(f"[BUDGET] {provider} budget warning ({used}/{config['monthly_limit']})")
        return True
    except Exception as e:
        logger.warning(f"[BUDGET] Error checking {provider}: {e}")
        return True  # fail-open


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


def is_circuit_closed(provider: str) -> bool:
    """Check if circuit breaker allows calls. Returns True if Redis unavailable (fail-open)."""
    try:
        raw = _redis_get(_circuit_key(provider))
        if not raw:
            return True  # No state = closed
        state = json.loads(raw)
        if state["state"] == CB_CLOSED:
            return True
        if state["state"] == CB_OPEN:
            # Check recovery timeout
            if time.time() - state.get("tripped_at", 0) >= CB_RECOVERY_TIMEOUT:
                # Transition to half-open
                state["state"] = CB_HALF_OPEN
                state["half_open_calls"] = 0
                _redis_set(_circuit_key(provider), json.dumps(state), ex=_CB_TTL)
                logger.info(f"[CIRCUIT] {provider} transitioning to half-open")
                return True
            return False
        if state["state"] == CB_HALF_OPEN:
            return state.get("half_open_calls", 0) < CB_HALF_OPEN_MAX_CALLS
        return True
    except Exception as e:
        logger.warning(f"[CIRCUIT] Error checking {provider}: {e}")
        return True


def record_failure(provider: str) -> None:
    """Record a failure (429, 503, timeout, connection refused/error). May trip circuit breaker.

    Call this on: 429, 503, timeout (status=0), connection refused (status=0).
    Do NOT call on: 200-no-price, 404, 403 (domain-level blocks, not service-level).
    """
    try:
        key = _circuit_key(provider)
        raw = _redis_get(key)
        state = json.loads(raw) if raw else {"state": CB_CLOSED, "failure_count": 0}

        state["failure_count"] = state.get("failure_count", 0) + 1
        state["last_failure_at"] = time.time()

        if state["failure_count"] >= CB_FAILURE_THRESHOLD:
            state["state"] = CB_OPEN
            state["tripped_at"] = time.time()
            logger.warning(f"[CIRCUIT] {provider} breaker TRIPPED after {state['failure_count']} failures")

        _redis_set(key, json.dumps(state), ex=_CB_TTL)
    except Exception as e:
        logger.warning(f"[CIRCUIT] Error recording failure for {provider}: {e}")


def record_success(provider: str) -> None:
    """Record success. Resets failure count. Closes half-open breaker."""
    try:
        key = _circuit_key(provider)
        raw = _redis_get(key)
        if not raw:
            return
        state = json.loads(raw)
        if state["state"] == CB_HALF_OPEN:
            logger.info(f"[CIRCUIT] {provider} breaker CLOSED after successful test call")
        state["state"] = CB_CLOSED
        state["failure_count"] = 0
        _redis_set(key, json.dumps(state), ex=_CB_TTL)
    except Exception as e:
        logger.warning(f"[CIRCUIT] Error recording success for {provider}: {e}")


def get_usage_summary() -> Dict[str, Any]:
    """Get usage summary for all providers (admin dashboard)."""
    result = {}
    for provider, config in PROVIDER_CONFIGS.items():
        used = 0
        try:
            raw = _redis_get(_budget_key(provider))
            if raw is not None:
                used = int(raw)
        except Exception:
            pass
        result[provider] = {
            "used": used,
            "limit": config["monthly_limit"],
            "remaining": max(0, config["monthly_limit"] - used),
            "is_lifetime": config.get("is_lifetime", False),
        }
        if config.get("is_lifetime"):
            result[provider]["lifetime_used"] = used

    # Circuit breaker states
    breakers = {}
    for provider in PROVIDER_CONFIGS:
        state_data = {"state": CB_CLOSED, "failures": 0}
        try:
            raw = _redis_get(_circuit_key(provider))
            if raw:
                s = json.loads(raw)
                state_data = {"state": s.get("state", CB_CLOSED), "failures": s.get("failure_count", 0)}
        except Exception:
            pass
        breakers[provider] = state_data

    return {"providers": result, "circuit_breakers": breakers}
```

- [ ] **Step 4: Run syntax check**
```bash
python -m py_compile app/services/api_budget_service.py
```
Expected: No output (success)

- [ ] **Step 5: Commit**
```bash
git add app/services/api_budget_service.py
git commit -m "feat: add API budget service with credit tracking and circuit breakers"
```

---

## Task 2: Firecrawl Service (backend-1)

**Files:**
- Create: `app/services/firecrawl_service.py`
- Test: `tests/test_firecrawl_service.py` (written by test-writer, Task 8)

**Context:** Firecrawl's `/v1/scrape` endpoint accepts a URL and returns rendered content. We need the `html` format to feed into the existing `_extract_price_from_html()` method in `structured_comparison_service.py`. The API key comes from `FIRECRAWL_API_KEY` env var. If not set, all calls return None (graceful skip).

**Firecrawl API docs:** `POST https://api.firecrawl.dev/v1/scrape` with `Authorization: Bearer <key>`, body: `{"url": "...", "formats": ["html"], "waitFor": 5000}`. The `waitFor` param tells Firecrawl to wait up to N ms for dynamic content (Smart Wait). Response: `{"success": true, "data": {"html": "...", "metadata": {...}}}`.

- [ ] **Step 1: Create `app/services/firecrawl_service.py`**

```python
"""Firecrawl Service — thin async wrapper around Firecrawl /v1/scrape API.

Firecrawl renders JavaScript SPAs with Smart Wait, capturing XHR-loaded content
that Cloudflare/Microlink miss. Used as Tier 1.5a for official brand sites.
"""
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_TIMEOUT = 15  # seconds — Smart Wait needs time for XHR
FIRECRAWL_WAIT_MS = 5000  # ms to wait for dynamic content after page load


def is_available() -> bool:
    """Check if Firecrawl is configured (API key present)."""
    enabled = os.environ.get("ENABLE_FIRECRAWL", "true").lower() != "false"
    has_key = bool(os.environ.get("FIRECRAWL_API_KEY"))
    return enabled and has_key


async def scrape_page(url: str) -> Optional[str]:
    """Scrape a URL via Firecrawl and return rendered HTML.

    Returns None if:
    - API key not configured
    - API returns error
    - Response has no HTML content

    Raises no exceptions — all errors are logged and return None.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=FIRECRAWL_TIMEOUT) as client:
            resp = await client.post(
                FIRECRAWL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["html"],
                    "waitFor": FIRECRAWL_WAIT_MS,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    html = data.get("data", {}).get("html", "")
                    if html and len(html) > 500:
                        logger.info(f"[FIRECRAWL] Got {len(html)//1024}KB HTML from {url}")
                        return html
                    else:
                        logger.info(f"[FIRECRAWL] Empty/short response from {url}")
                else:
                    logger.warning(f"[FIRECRAWL] API error: {data.get('error', 'unknown')}")
                return None

            # Return status code for circuit breaker classification
            logger.warning(f"[FIRECRAWL] HTTP {resp.status_code} for {url}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"[FIRECRAWL] Timeout ({FIRECRAWL_TIMEOUT}s) for {url}")
        return None
    except Exception as e:
        logger.warning(f"[FIRECRAWL] Error: {e}")
        return None


async def scrape_page_with_status(url: str) -> tuple[Optional[str], int]:
    """Like scrape_page but also returns HTTP status code for circuit breaker decisions.

    Returns (html_or_none, status_code). Status 0 means connection/timeout error.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None, 0

    try:
        async with httpx.AsyncClient(timeout=FIRECRAWL_TIMEOUT) as client:
            resp = await client.post(
                FIRECRAWL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["html"],
                    "waitFor": FIRECRAWL_WAIT_MS,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    html = data.get("data", {}).get("html", "")
                    if html and len(html) > 500:
                        logger.info(f"[FIRECRAWL] Got {len(html)//1024}KB HTML from {url}")
                        return html, 200
                return None, 200  # 200 but no usable content

            logger.warning(f"[FIRECRAWL] HTTP {resp.status_code} for {url}")
            return None, resp.status_code

    except httpx.TimeoutException:
        logger.warning(f"[FIRECRAWL] Timeout ({FIRECRAWL_TIMEOUT}s) for {url}")
        return None, 0
    except Exception as e:
        logger.warning(f"[FIRECRAWL] Error: {e}")
        return None, 0
```

- [ ] **Step 2: Run syntax check**
```bash
python -m py_compile app/services/firecrawl_service.py
```

- [ ] **Step 3: Commit**
```bash
git add app/services/firecrawl_service.py
git commit -m "feat: add Firecrawl service for Smart Wait SPA price scraping"
```

---

## Task 3: Scrape.do Service (backend-1)

**Files:**
- Create: `app/services/scrapedo_service.py`
- Test: `tests/test_scrapedo_service.py` (written by test-writer, Task 8)

**Context:** Scrape.do's API is simpler: `GET https://api.scrape.do?token=<key>&url=<url>&render=true`. Returns raw rendered HTML. We parse with the existing `_extract_price_from_html()`. Token from `SCRAPEDO_API_TOKEN` env var.

- [ ] **Step 1: Create `app/services/scrapedo_service.py`**

```python
"""Scrape.do Service — thin async wrapper around Scrape.do rendering API.

Scrape.do renders JavaScript pages with residential proxies and anti-bot bypass.
Used as Tier 1.5d fallback when curl_cffi fails to extract prices from retailer pages.
"""
import os
import logging
import httpx
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

SCRAPEDO_API_URL = "https://api.scrape.do"
SCRAPEDO_TIMEOUT = 15  # seconds — render=true needs time


def is_available() -> bool:
    """Check if Scrape.do is configured (API token present)."""
    enabled = os.environ.get("ENABLE_SCRAPEDO", "true").lower() != "false"
    has_token = bool(os.environ.get("SCRAPEDO_API_TOKEN"))
    return enabled and has_token


async def render_page(url: str) -> Optional[str]:
    """Render a URL via Scrape.do and return HTML.

    Returns None if token not configured, API error, or empty response.
    Raises no exceptions.
    """
    token = os.environ.get("SCRAPEDO_API_TOKEN")
    if not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=SCRAPEDO_TIMEOUT) as client:
            resp = await client.get(
                SCRAPEDO_API_URL,
                params={
                    "token": token,
                    "url": url,
                    "render": "true",
                },
            )

            if resp.status_code == 200:
                html = resp.text
                if html and len(html) > 500:
                    logger.info(f"[SCRAPEDO] Got {len(html)//1024}KB HTML from {url}")
                    return html
                logger.info(f"[SCRAPEDO] Empty/short response from {url}")
                return None

            logger.warning(f"[SCRAPEDO] HTTP {resp.status_code} for {url}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"[SCRAPEDO] Timeout ({SCRAPEDO_TIMEOUT}s) for {url}")
        return None
    except Exception as e:
        logger.warning(f"[SCRAPEDO] Error: {e}")
        return None


async def render_page_with_status(url: str) -> tuple[Optional[str], int]:
    """Like render_page but returns (html_or_none, status_code) for circuit breaker."""
    token = os.environ.get("SCRAPEDO_API_TOKEN")
    if not token:
        return None, 0

    try:
        async with httpx.AsyncClient(timeout=SCRAPEDO_TIMEOUT) as client:
            resp = await client.get(
                SCRAPEDO_API_URL,
                params={
                    "token": token,
                    "url": url,
                    "render": "true",
                },
            )

            if resp.status_code == 200:
                html = resp.text
                if html and len(html) > 500:
                    logger.info(f"[SCRAPEDO] Got {len(html)//1024}KB HTML from {url}")
                    return html, 200
                return None, 200

            logger.warning(f"[SCRAPEDO] HTTP {resp.status_code} for {url}")
            return None, resp.status_code

    except httpx.TimeoutException:
        logger.warning(f"[SCRAPEDO] Timeout ({SCRAPEDO_TIMEOUT}s) for {url}")
        return None, 0
    except Exception as e:
        logger.warning(f"[SCRAPEDO] Error: {e}")
        return None, 0
```

- [ ] **Step 2: Run syntax check**
```bash
python -m py_compile app/services/scrapedo_service.py
```

- [ ] **Step 3: Commit**
```bash
git add app/services/scrapedo_service.py
git commit -m "feat: add Scrape.do service for JS rendering fallback"
```

---

## Task 4: Wire New Services into Price Cascade (backend-2)

**Files:**
- Modify: `app/services/structured_comparison_service.py`

**Context:** This is the core integration task. You're modifying the existing `_get_price()` method (starts at line 1173) and `_fetch_page_price()` (line 2368). Read the ENTIRE `_get_price()` method first (lines 1173-1510) to understand the full flow. Also read the spec at `docs/superpowers/specs/2026-03-24-firecrawl-price-resolution-design.md` for the cascade architecture.

**IMPORTANT:** The file is ~2800 lines. Only modify the specific methods listed below. Do NOT restructure other code.

- [ ] **Step 1: Read the full `_get_price()` method** (lines 1173-1510) and `_fetch_page_price()` (lines 2368-2418). Understand every tier and how they chain.

- [ ] **Step 2: Add imports at top of file** (after existing imports, around line 31):

```python
from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed,
)
from app.services import firecrawl_service, scrapedo_service
```

**NOTE:** `urlparse` is already imported at line 14 (`from urllib.parse import urlparse`). Do NOT add it again.

- [ ] **Step 3: Replace `ENABLE_JS_RENDER` with new feature flags** (around line 35):

Remove:
```python
ENABLE_JS_RENDER = os.environ.get("ENABLE_JS_RENDER", "true").lower() != "false"
```

The `ENABLE_PAGE_SCRAPE` flag stays. Firecrawl and Scrape.do availability is checked via their `is_available()` functions.

- [ ] **Step 4: Add input validation methods** to the `StructuredComparisonService` class (after `_extract_domain()`, around line 1696):

```python
    @staticmethod
    def _validate_price_query(brand: str, name: str, region: str) -> bool:
        """Gate 0: Reject garbage queries before wasting API credits."""
        full_name = f"{brand} {name}".strip()
        if len(full_name) < 3 or len(full_name) > 200:
            logger.warning(f"[PRICE] Gate 0: rejected query (length {len(full_name)}): {full_name[:50]}")
            return False
        if not full_name[0].isalpha():
            logger.warning(f"[PRICE] Gate 0: rejected query (starts non-alpha): {full_name[:50]}")
            return False
        if region not in GCC_REGIONS:
            logger.warning(f"[PRICE] Gate 0: rejected region: {region}")
            return False
        return True

    @staticmethod
    def _validate_scrape_url(url: str) -> bool:
        """Reject URLs that waste rendering credits (search/category pages)."""
        if not url:
            return False
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc or "." not in parsed.netloc:
                return False
            path_lower = parsed.path.lower()
            blocked_patterns = ["/search", "/category", "/collection", "/c/", "/s?k=", "/browse"]
            # NOTE: "/shop/" intentionally excluded — many GCC retailers use /shop/ in product URLs
            if any(p in path_lower for p in blocked_patterns):
                logger.info(f"[PRICE] URL validation: rejected non-product URL: {url[:80]}")
                return False
            return True
        except Exception:
            return False
```

- [ ] **Step 5: Expand GCC_LUXURY_RETAILERS** (line 1647):

Replace the existing `GCC_LUXURY_RETAILERS` set:
```python
    GCC_LUXURY_RETAILERS = {
        "ounass.ae", "ounass.com", "namshi.com", "bloomingdales.ae",
        "level-shoes.com", "harveynichols.com", "galerieslafayette.ae",
        "theluxurycloset.com", "boutique1.com",
    }
```

- [ ] **Step 6: Add Gate 0 at start of `_get_price()`** (right after line 1182, before cache check):

```python
        # Gate 0: Input validation
        if not self._validate_price_query(brand, name, region):
            return {
                "amount": 0, "currency": "BHD", "estimated": True,
                "source_method": "validation_rejected",
            }
```

- [ ] **Step 7: Modify Tier 1.5a to use Firecrawl** (lines 1274-1295):

Replace the existing Tier 1.5a block. After `if official_domain:` (line 1276), the new logic:

```python
            if official_domain:
                logger.info(f"[PRICE] Tier 1.5a: trying official domain {official_domain}")
                try:
                    official_results = await search_web(f"{full_name} site:{official_domain}")
                    self.api_calls += 1
                    self._track_cost(0.001)
                    if official_results and official_results.get("organic"):
                        for organic_item in official_results["organic"][:2]:
                            page_url = organic_item.get("link")
                            if not page_url or not self._validate_scrape_url(page_url):
                                continue

                            # Try Firecrawl first (Smart Wait catches XHR-loaded prices)
                            if firecrawl_service.is_available() and is_circuit_closed("firecrawl") and has_budget("firecrawl"):
                                html, status = await firecrawl_service.scrape_page_with_status(page_url)
                                # Always count usage if we got a 200 (API credit was spent)
                                if status == 200:
                                    record_usage("firecrawl")
                                if html:
                                    record_success("firecrawl")
                                    price = self._extract_price_from_html(html, full_name, currency, official_domain, page_url)
                                    if price:
                                        price["source_method"] = "firecrawl"
                                        price["retailer"] = official_domain
                                        logger.info(f"[PRICE] Tier 1.5a: Firecrawl price {currency} {price['amount']} from {official_domain}")
                                        set_cached(cache_key, price, PRICE_CACHE_TTL)
                                        price["_cached"] = False
                                        return price
                                elif status in (429, 503) or status == 0:
                                    record_failure("firecrawl")
                                # If Firecrawl got 200 but no price, that's NOT a circuit failure — continue

                            # Fallback: curl_cffi for non-SPA official sites
                            page_price = await self._fetch_page_price(page_url, full_name, currency)
                            if page_price and page_price.get("amount"):
                                page_price.pop("_got_html", None)  # Clean up internal marker
                                page_price["retailer"] = official_domain
                                logger.info(f"[PRICE] Tier 1.5a: official price {currency} {page_price['amount']} from {official_domain}")
                                set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                                page_price["_cached"] = False
                                return page_price
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5a failed: {e}")
```

- [ ] **Step 8: Add `failed_curl_urls` tracking in Tier 1.5b/c and Tier 1.5d**

Before the Tier 1.5 block (after `tier15_budget = self.TIER_15_BUDGET_TIMEOUT`), add:
```python
            failed_curl_urls = []  # URLs where curl got HTML but no price — Scrape.do candidates
```

In Tier 1.5b, after the parallel `asyncio.gather` for page prices (around line 1325), track URLs where curl got HTML but no price (`_got_html` marker):
```python
                            for i, pp in enumerate(page_prices):
                                if isinstance(pp, dict) and pp.get("amount"):
                                    pp["_retailer_domain"] = retailer_urls[i][1]
                                    valid_prices.append(pp)
                                elif isinstance(pp, dict) and pp.get("_got_html"):
                                    # curl_cffi got HTML but no price — JS render may help
                                    failed_curl_urls.append(retailer_urls[i][0])
                                # If pp is None (curl failed) or Exception → NOT a Scrape.do candidate
```

Similarly in Tier 1.5c, after `_fetch_page_price`:
```python
                                    gcc_price = await self._fetch_page_price(link, full_name, currency)
                                    if gcc_price and gcc_price.get("amount"):
                                        # ... existing return logic ...
                                    elif gcc_price and gcc_price.get("_got_html"):
                                        failed_curl_urls.append(link)
                                    # If gcc_price is None → curl itself failed, don't retry with Scrape.do
```

After the existing Tier 1.5c block (before `logger.info(f"[PRICE] Tier 1.5 cascade complete..."`), add Tier 1.5d:

```python
                    # --- Tier 1.5d: Scrape.do rendering fallback ---
                    # Only fires if curl_cffi found URLs but extraction failed (not timeouts)
                    elapsed = time.monotonic() - tier15_start
                    if (failed_curl_urls and elapsed < tier15_budget
                            and scrapedo_service.is_available()
                            and is_circuit_closed("scrapedo") and has_budget("scrapedo")):
                        # Prioritize GCC retailer URLs (more likely to have prices in rendered DOM)
                        gcc_domains = self.GCC_LUXURY_RETAILERS
                        sorted_urls = sorted(
                            failed_curl_urls,
                            key=lambda u: 0 if urlparse(u).netloc.replace("www.", "") in gcc_domains else 1,
                        )
                        for retry_url in sorted_urls[:2]:
                            if not self._validate_scrape_url(retry_url):
                                continue
                            retry_domain = urlparse(retry_url).netloc.replace("www.", "")
                            logger.info(f"[PRICE] Tier 1.5d: Scrape.do retry on {retry_domain}")
                            html, status = await scrapedo_service.render_page_with_status(retry_url)
                            # Always count usage on 200 (API credit spent even if no price)
                            if status == 200:
                                record_usage("scrapedo")
                            if html:
                                record_success("scrapedo")
                                price = self._extract_price_from_html(html, full_name, currency, retry_domain, retry_url)
                                if price:
                                    price["source_method"] = "scrapedo_rendered"
                                    logger.info(f"[PRICE] Tier 1.5d: Scrape.do price {currency} {price['amount']} from {retry_domain}")
                                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                                    price["_cached"] = False
                                    return price
                            elif status in (429, 503) or status == 0:
                                record_failure("scrapedo")
                                break  # Don't burn another credit if provider is struggling
```

- [ ] **Step 9: Simplify `_fetch_page_price()`** (lines 2368-2418):

Remove the JS rendering fallback (the `if ENABLE_JS_RENDER:` block). Firecrawl and Scrape.do are now called from `_get_price()` directly. `_fetch_page_price()` becomes curl_cffi only:

```python
    async def _fetch_page_price(
        self,
        url: str,
        product_name: str,
        currency: str = "BHD",
    ) -> Optional[Dict[str, Any]]:
        """Fetch a product page via curl_cffi and extract price from structured data.

        Uses _extract_price_from_html() for JSON-LD/OG/microdata parsing.
        Gated by ENABLE_PAGE_SCRAPE feature flag.
        JS rendering (Firecrawl/Scrape.do) is handled at the cascade level in _get_price().

        Returns:
            - Dict with price data if found
            - {"_got_html": True} if curl_cffi fetched HTML but no price (Scrape.do candidate)
            - None if curl_cffi failed to fetch (not a Scrape.do candidate)
        """
        if not ENABLE_PAGE_SCRAPE:
            return None

        domain = urlparse(url).netloc.replace("www.", "")
        html = await self._curl_fetch_html(url)
        if html:
            price = self._extract_price_from_html(html, product_name, currency, domain, url)
            if price:
                logger.info(f"[PRICE] Page scrape: curl_cffi price {currency} {price['amount']} from {domain}")
                return price
            logger.info(f"[PRICE] Page scrape: curl_cffi no structured data from {domain}")
            return {"_got_html": True}  # Signal: HTML fetched but no price — JS render may help

        return None  # curl_cffi itself failed — JS render won't help either
```

- [ ] **Step 10: Remove dead code**

Delete:
- `_fetch_rendered_html()` method (lines 2203-2280)
- `JS_ONLY_DOMAINS` set (lines 1656-1661)
- `JS_RENDER_TIMEOUT` constant (line 1663)
- `ENABLE_JS_RENDER` import/constant (line 35)

- [ ] **Step 11: Run syntax check**
```bash
python -m py_compile app/services/structured_comparison_service.py
```

- [ ] **Step 12: Run existing tests to check for regressions**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x --timeout=60
```
Expected: Some test failures in `test_js_rendering.py` (expected — tests reference removed code). All OTHER tests should pass.

- [ ] **Step 13: Commit**
```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: wire Firecrawl + Scrape.do into price cascade with gates and validation"
```

---

## Task 5: Admin Cost Dashboard Endpoint (backend-2)

**Files:**
- Modify: `app/api/admin_routes.py`
- Test: `tests/test_cost_dashboard.py` (written by test-writer, Task 9)

**Context:** Add a `GET /api/v1/admin/costs` endpoint. Reads from `api_budget_service.get_usage_summary()` + Supabase for OpenAI cost aggregation. Protected by same `verify_admin_key` as other admin routes.

- [ ] **Step 1: Read `app/api/admin_routes.py`** to understand existing pattern (already shown above — uses `verify_admin_key` dependency).

- [ ] **Step 2: Add the cost endpoint** at the bottom of `app/api/admin_routes.py`:

```python
from datetime import datetime
from app.services.api_budget_service import get_usage_summary
from app.services.database_service import get_supabase_client


@router.get("/costs")
async def api_costs(_=Depends(verify_admin_key)):
    """API cost dashboard — provider budgets, circuit breakers, monthly spend."""
    summary = get_usage_summary()

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0).isoformat()

    # OpenAI cost: sum from comparisons table this month
    openai_cost = 0.0
    try:
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table("comparisons").select("metadata").gte("created_at", month_start).execute()
            for row in (result.data or []):
                meta = row.get("metadata") or {}
                openai_cost += meta.get("total_cost", 0)
    except Exception as e:
        logger.warning(f"[ADMIN] Failed to fetch OpenAI costs: {e}")

    # Comparison count this month
    comp_count = 0
    try:
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table("comparisons").select("id", count="exact").gte("created_at", month_start).execute()
            comp_count = result.count or 0
    except Exception:
        pass

    summary["openai"] = {"cost_usd": round(openai_cost, 4), "source": "comparisons.metadata.total_cost"}
    summary["comparisons_this_month"] = comp_count
    summary["avg_cost_per_comparison"] = round(openai_cost / comp_count, 4) if comp_count > 0 else 0
    summary["fixed_costs_monthly"] = 30.00  # Railway $5 + Supabase $25
    summary["estimated_monthly_total"] = round(summary["fixed_costs_monthly"] + openai_cost, 2)
    summary["period"] = datetime.utcnow().strftime("%Y-%m")

    return summary
```

**NOTE:** The `datetime` and `get_supabase_client` imports are added at the top-level of the file, NOT inside the function body. This also enables correct mocking in tests.

- [ ] **Step 4: Run syntax check**
```bash
python -m py_compile app/api/admin_routes.py
```

- [ ] **Step 5: Commit**
```bash
git add app/api/admin_routes.py
git commit -m "feat: add admin cost dashboard endpoint for provider budget monitoring"
```

---

## Task 6: Remove Diagnostic Endpoints + Dead Code (backend-2)

**Files:**
- Modify: `app/main.py` (remove lines 157-399: three diagnostic endpoints)

**Context:** The 3 diagnostic endpoints (`/health/render-test`, `/health/render-price-test`, `/health/scrape-test`) were temporary for Session 30 investigation. Now that we've confirmed Cloudflare rendering can't solve luxury SPA prices, these are dead code.

- [ ] **Step 1: Read `app/main.py` lines 150-400** to identify exact boundaries of the 3 diagnostic endpoints.

- [ ] **Step 2: Delete the 3 endpoints** — remove everything from `@app.get("/health/render-test")` through the end of `scrape_test()`. Keep the `/health` basic endpoint intact (line 148-154).

- [ ] **Step 3: Clean up any orphaned imports** in `main.py` that were only used by diagnostic endpoints (e.g., `httpx` if no other code uses it there).

- [ ] **Step 4: Run syntax check**
```bash
python -m py_compile app/main.py
```

- [ ] **Step 5: Run the full test suite (excluding live tests)**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x --timeout=60
```
Expected: Tests pass EXCEPT `test_js_rendering.py` (will be fixed in Task 9).

- [ ] **Step 6: Commit**
```bash
git add app/main.py
git commit -m "chore: remove diagnostic render/scrape endpoints (replaced by Firecrawl)"
```

---

## Task 7: Tests — API Budget Service (test-writer)

**Files:**
- Create: `tests/test_api_budget_service.py`

**Context:** Test the credit tracking and circuit breaker logic in `app/services/api_budget_service.py`. The service imports `_redis_get`/`_redis_set`/`_redis_incr`/`_redis_expire` from `cache_service.py`. Mock these helpers directly.

- [ ] **Step 1: Create `tests/test_api_budget_service.py`**

Test these scenarios (target: 20+ tests):

**Budget tracking:**
- `has_budget()` returns True when under limit
- `has_budget()` returns False when at/over limit
- `has_budget()` returns True when Redis unavailable (fail-open)
- `record_usage()` increments counter
- `record_usage()` handles Redis errors gracefully
- Lifetime key vs monthly key paths
- `get_usage_summary()` returns correct structure for all providers
- Monthly key includes correct YYYY-MM format
- Warning logged when usage exceeds `warn_at` threshold

**Circuit breaker:**
- `is_circuit_closed()` returns True for fresh provider (no state)
- `record_failure()` increments failure count
- 3 failures trips breaker (state → open)
- `is_circuit_closed()` returns False when open
- After recovery timeout, transitions to half-open
- `record_success()` closes half-open breaker
- `is_circuit_closed()` returns True when Redis unavailable (fail-open)
- `record_failure()` handles Redis errors gracefully
- Connection refused (status 0) trips circuit breaker

```python
"""Tests for API budget service — credit tracking + circuit breakers."""
import json
import time
import pytest
from unittest.mock import patch, MagicMock, call

from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed, get_usage_summary,
    PROVIDER_CONFIGS, CB_FAILURE_THRESHOLD, CB_RECOVERY_TIMEOUT,
    CB_CLOSED, CB_OPEN, CB_HALF_OPEN,
    _budget_key, _circuit_key,
)


# Mock the cache_service helpers that api_budget_service imports
_MOCK_STORE = {}  # Simulates Redis key-value store


@pytest.fixture
def mock_redis_helpers():
    """Mock _redis_get/_redis_set/_redis_incr/_redis_expire at the api_budget_service module level."""
    store = {}

    def fake_get(key):
        return store.get(key)

    def fake_set(key, value, ex=None):
        store[key] = value
        return True

    def fake_incr(key):
        val = int(store.get(key, 0)) + 1
        store[key] = str(val)
        return val

    def fake_expire(key, seconds):
        return True

    with patch("app.services.api_budget_service._redis_get", side_effect=fake_get) as m_get, \
         patch("app.services.api_budget_service._redis_set", side_effect=fake_set) as m_set, \
         patch("app.services.api_budget_service._redis_incr", side_effect=fake_incr) as m_incr, \
         patch("app.services.api_budget_service._redis_expire", side_effect=fake_expire) as m_expire:
        yield {"get": m_get, "set": m_set, "incr": m_incr, "expire": m_expire, "store": store}


class TestHasBudget:
    def test_under_limit(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = "100"
        assert has_budget("firecrawl") is True

    def test_at_limit(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = str(PROVIDER_CONFIGS["firecrawl"]["monthly_limit"])
        assert has_budget("firecrawl") is False

    def test_over_limit(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = "9999"
        assert has_budget("firecrawl") is False

    def test_no_usage_yet(self, mock_redis_helpers):
        # No key in store = first use
        assert has_budget("firecrawl") is True

    def test_unknown_provider(self, mock_redis_helpers):
        assert has_budget("nonexistent") is False

    def test_redis_error_fail_open(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            assert has_budget("firecrawl") is True


class TestRecordUsage:
    def test_increments_counter(self, mock_redis_helpers):
        record_usage("firecrawl")
        mock_redis_helpers["incr"].assert_called_once()

    def test_sets_ttl_for_monthly_provider(self, mock_redis_helpers):
        record_usage("scrapedo")  # monthly, not lifetime
        mock_redis_helpers["expire"].assert_called_once()

    def test_no_ttl_for_lifetime_provider(self, mock_redis_helpers):
        record_usage("firecrawl")  # lifetime
        mock_redis_helpers["expire"].assert_not_called()

    def test_redis_error_no_crash(self):
        with patch("app.services.api_budget_service._redis_incr", side_effect=Exception("Redis down")):
            record_usage("firecrawl")  # should not raise


class TestCircuitBreaker:
    def test_fresh_provider_is_closed(self, mock_redis_helpers):
        assert is_circuit_closed("firecrawl") is True

    def test_single_failure_stays_closed(self, mock_redis_helpers):
        record_failure("firecrawl")
        raw = mock_redis_helpers["store"].get(_circuit_key("firecrawl"))
        state = json.loads(raw)
        assert state["state"] == CB_CLOSED
        assert state["failure_count"] == 1

    def test_threshold_failures_trips_breaker(self, mock_redis_helpers):
        # Pre-load state with failures just below threshold
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_CLOSED, "failure_count": CB_FAILURE_THRESHOLD - 1
        })
        record_failure("firecrawl")
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["state"] == CB_OPEN

    def test_open_breaker_blocks_calls(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_OPEN, "failure_count": 3, "tripped_at": time.time()
        })
        assert is_circuit_closed("firecrawl") is False

    def test_open_transitions_to_half_open_after_timeout(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_OPEN, "failure_count": 3,
            "tripped_at": time.time() - CB_RECOVERY_TIMEOUT - 1
        })
        assert is_circuit_closed("firecrawl") is True

    def test_success_closes_half_open(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_HALF_OPEN, "failure_count": 0, "half_open_calls": 0
        })
        record_success("firecrawl")
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["state"] == CB_CLOSED

    def test_redis_error_fail_open(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            assert is_circuit_closed("firecrawl") is True


class TestUsageSummary:
    def test_returns_all_providers(self, mock_redis_helpers):
        summary = get_usage_summary()
        for provider in PROVIDER_CONFIGS:
            assert provider in summary["providers"]
            assert "used" in summary["providers"][provider]
            assert "limit" in summary["providers"][provider]
            assert "remaining" in summary["providers"][provider]

    def test_returns_circuit_breaker_states(self, mock_redis_helpers):
        summary = get_usage_summary()
        assert "circuit_breakers" in summary
        for provider in PROVIDER_CONFIGS:
            assert provider in summary["circuit_breakers"]
```

- [ ] **Step 2: Run tests**
```bash
python -m pytest tests/test_api_budget_service.py -v
```
Expected: ALL PASS

- [ ] **Step 3: Commit**
```bash
git add tests/test_api_budget_service.py
git commit -m "test: add API budget service tests (credit tracking + circuit breakers)"
```

---

## Task 8: Tests — Firecrawl + Scrape.do Services (test-writer)

**Files:**
- Create: `tests/test_firecrawl_service.py`
- Create: `tests/test_scrapedo_service.py`

**Context:** Mock httpx calls — never call real APIs. Test both `scrape_page()` (simple) and `scrape_page_with_status()` (returns status for circuit breaker). Follow patterns in existing `tests/test_js_rendering.py` for mocking async httpx.

- [ ] **Step 1: Create `tests/test_firecrawl_service.py`** (target: 12+ tests)

Test scenarios:
- Returns HTML on successful 200 response
- Returns None when API key not set
- Returns None on empty/short response
- Returns None on API error (success: false)
- Returns None on timeout
- Returns (None, 429) on rate limit
- Returns (None, 503) on server error
- Returns (html, 200) on success with status
- `is_available()` returns True when key set + enabled
- `is_available()` returns False when key missing
- `is_available()` returns False when ENABLE_FIRECRAWL=false

```python
"""Tests for Firecrawl service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.services.firecrawl_service import scrape_page, scrape_page_with_status, is_available


SAMPLE_HTML = "<html><body>" + "x" * 1000 + "</body></html>"


@pytest.fixture
def mock_env_key():
    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
        yield


class TestIsAvailable:
    def test_available_with_key(self):
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}):
            assert is_available() is True

    def test_unavailable_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            assert is_available() is False

    def test_unavailable_when_disabled(self):
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key", "ENABLE_FIRECRAWL": "false"}):
            assert is_available() is False


class TestScrapePage:
    @pytest.mark.asyncio
    async def test_returns_html_on_success(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": SAMPLE_HTML}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await scrape_page("https://example.com/product")
            assert result == SAMPLE_HTML

    @pytest.mark.asyncio
    async def test_returns_none_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = await scrape_page("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": False, "error": "blocked"}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, mock_env_key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_short_html(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": "<html></html>"}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await scrape_page("https://example.com/product")
            assert result is None


class TestScrapePageWithStatus:
    @pytest.mark.asyncio
    async def test_returns_html_and_200(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": SAMPLE_HTML}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            html, status = await scrape_page_with_status("https://example.com")
            assert html == SAMPLE_HTML
            assert status == 200

    @pytest.mark.asyncio
    async def test_returns_none_and_429(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 429

    @pytest.mark.asyncio
    async def test_returns_none_and_0_on_timeout(self, mock_env_key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 0
```

- [ ] **Step 2: Create `tests/test_scrapedo_service.py`** (target: 10+ tests)

```python
"""Tests for Scrape.do service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.services.scrapedo_service import render_page, render_page_with_status, is_available


SAMPLE_HTML = "<html><body>" + "x" * 1000 + "</body></html>"


@pytest.fixture
def mock_env_token():
    with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "test-token"}):
        yield


class TestIsAvailable:
    def test_available_with_token(self):
        with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "tok"}):
            assert is_available() is True

    def test_unavailable_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            assert is_available() is False

    def test_unavailable_when_disabled(self):
        with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "tok", "ENABLE_SCRAPEDO": "false"}):
            assert is_available() is False


class TestRenderPage:
    @pytest.mark.asyncio
    async def test_returns_html_on_success(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await render_page("https://example.com/product")
            assert result == SAMPLE_HTML

    @pytest.mark.asyncio
    async def test_returns_none_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            result = await render_page("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_short_html(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html></html>"

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await render_page("https://example.com/product")
            assert result is None


class TestRenderPageWithStatus:
    @pytest.mark.asyncio
    async def test_returns_html_and_200(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            html, status = await render_page_with_status("https://example.com")
            assert html == SAMPLE_HTML
            assert status == 200

    @pytest.mark.asyncio
    async def test_returns_none_and_429(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 429

    @pytest.mark.asyncio
    async def test_returns_none_and_0_on_timeout(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 0
```

- [ ] **Step 3: Run all new tests**
```bash
python -m pytest tests/test_firecrawl_service.py tests/test_scrapedo_service.py -v
```

- [ ] **Step 4: Commit**
```bash
git add tests/test_firecrawl_service.py tests/test_scrapedo_service.py
git commit -m "test: add Firecrawl + Scrape.do service tests"
```

---

## Task 9: Tests — Cascade Hardening, Validation, Dashboard + Update Existing Tests (test-writer)

**Files:**
- Create: `tests/test_cascade_hardening.py`
- Create: `tests/test_input_validation.py`
- Create: `tests/test_cost_dashboard.py`
- Modify: `tests/test_js_rendering.py` (update for Firecrawl/Scrape.do)
- Modify: `tests/test_luxury_price_tiers.py` (add expanded GCC retailers)

**Context:** These tests verify the integration layer. The cascade tests mock all external services and verify the FLOW — that gates prevent unnecessary calls, that tiers short-circuit correctly, and that `failed_curl_urls` feeds Tier 1.5d only when appropriate.

- [ ] **Step 1: Create `tests/test_input_validation.py`** (target: 12+ tests)

```python
"""Tests for price query and URL validation."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


class TestValidatePriceQuery:
    def test_valid_query(self):
        assert StructuredComparisonService._validate_price_query("Apple", "iPhone 15", "bahrain") is True

    def test_empty_brand_and_name(self):
        assert StructuredComparisonService._validate_price_query("", "", "bahrain") is False

    def test_too_short(self):
        assert StructuredComparisonService._validate_price_query("A", "", "bahrain") is False

    def test_too_long(self):
        assert StructuredComparisonService._validate_price_query("A" * 201, "", "bahrain") is False

    def test_starts_with_number(self):
        assert StructuredComparisonService._validate_price_query("123", "product", "bahrain") is False

    def test_invalid_region(self):
        assert StructuredComparisonService._validate_price_query("Apple", "iPhone", "antarctica") is False

    def test_all_valid_regions(self):
        for region in ["bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"]:
            assert StructuredComparisonService._validate_price_query("Test", "Product", region) is True


class TestValidateScrapeUrl:
    def test_valid_product_url(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/product/123") is True

    def test_rejects_search_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/search?q=test") is False

    def test_rejects_category_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/category/shoes") is False

    def test_rejects_collection_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/collection/summer") is False

    def test_rejects_empty(self):
        assert StructuredComparisonService._validate_scrape_url("") is False

    def test_rejects_no_scheme(self):
        assert StructuredComparisonService._validate_scrape_url("example.com/product") is False

    def test_rejects_ftp(self):
        assert StructuredComparisonService._validate_scrape_url("ftp://example.com/file") is False

    def test_accepts_http(self):
        assert StructuredComparisonService._validate_scrape_url("http://example.com/product/1") is True
```

- [ ] **Step 2: Create `tests/test_cascade_hardening.py`** (target: 15+ tests)

Test the cascade flow by mocking services. Key scenarios:
- Gate 0 rejects invalid input before any API call
- Tier 1 success stops cascade (no Firecrawl/Scrape.do called)
- Firecrawl called when circuit closed + budget available
- Firecrawl NOT called when circuit open
- Firecrawl NOT called when budget exhausted
- Firecrawl 429 trips circuit breaker
- Firecrawl 200-no-price does NOT trip breaker
- Tier 1.5d only fires when `failed_curl_urls` is non-empty
- Tier 1.5d respects its own circuit breaker
- Tier 1.5d prioritizes GCC retailer URLs
- Time budget stops cascade when exceeded
- `source_method` tags correctly set: "firecrawl", "scrapedo_rendered"

- [ ] **Step 3: Create `tests/test_cost_dashboard.py`** (target: 6+ tests)

```python
"""Tests for admin cost dashboard endpoint."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)
ADMIN_KEY = "test-admin-key"


@pytest.fixture(autouse=True)
def mock_admin_key():
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY}):
        yield


class TestCostDashboard:
    def test_returns_provider_budgets(self):
        with patch("app.api.admin_routes.get_usage_summary", return_value={
            "providers": {"firecrawl": {"used": 10, "limit": 450, "remaining": 440}},
            "circuit_breakers": {"firecrawl": {"state": "closed", "failures": 0}},
        }), patch("app.api.admin_routes.get_supabase_client", return_value=None):
            # NOTE: get_supabase_client is imported at module level in admin_routes.py,
            # so we mock it on the admin_routes module, not database_service
            resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})
            assert resp.status_code == 200
            data = resp.json()
            assert "providers" in data
            assert "circuit_breakers" in data
            assert "period" in data

    def test_requires_admin_key(self):
        resp = client.get("/api/v1/admin/costs")
        assert resp.status_code in (403, 422)

    def test_rejects_wrong_key(self):
        resp = client.get("/api/v1/admin/costs", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code == 403
```

- [ ] **Step 4: Update `tests/test_js_rendering.py`**

Replace Cloudflare/Microlink test references with Firecrawl/Scrape.do. Remove tests for `_fetch_rendered_html()` (deleted), `JS_ONLY_DOMAINS` (deleted), `RENDER_PROVIDER` (deleted). Add tests verifying `_fetch_page_price()` now uses curl_cffi only (no JS render fallback).

- [ ] **Step 5: Update `tests/test_luxury_price_tiers.py`**

Add tests for the expanded `GCC_LUXURY_RETAILERS` set (harveynichols.com, galerieslafayette.ae, theluxurycloset.com, boutique1.com).

- [ ] **Step 6: Run all tests**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=60
```
Expected: ALL PASS (0 failures)

- [ ] **Step 7: Commit**
```bash
git add tests/test_cascade_hardening.py tests/test_input_validation.py tests/test_cost_dashboard.py tests/test_js_rendering.py tests/test_luxury_price_tiers.py
git commit -m "test: add cascade hardening, validation, and cost dashboard tests"
```

---

## Task 10: Cross-QA Review (qa-reviewer)

**Files:** ALL files from Tasks 1-9

**Context:** You are the quality gate. Every agent's work must meet these criteria before the team can dissolve. Run every check below. If ANY check fails, send the work back to the responsible agent with specific failure details.

- [ ] **Step 1: Run full test suite**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=120
```
**Criteria:** 0 failures. If any test fails, identify which agent's code caused it and send back.

- [ ] **Step 2: Run syntax check on all new/modified files**
```bash
python -m py_compile app/services/api_budget_service.py
python -m py_compile app/services/firecrawl_service.py
python -m py_compile app/services/scrapedo_service.py
python -m py_compile app/services/structured_comparison_service.py
python -m py_compile app/api/admin_routes.py
python -m py_compile app/main.py
```
**Criteria:** All pass with no output.

- [ ] **Step 3: Verify cascade leak prevention**

Read `app/services/structured_comparison_service.py` and verify:
- [ ] Every tier has an early return on success (no fall-through)
- [ ] Firecrawl is only called when `is_circuit_closed("firecrawl")` AND `has_budget("firecrawl")` AND `firecrawl_service.is_available()`
- [ ] Scrape.do is only called when `failed_curl_urls` is non-empty AND circuit closed AND budget available
- [ ] `record_failure()` is called on 429/503/timeout only, NOT on 200-no-price
- [ ] `record_usage()` is called BEFORE `record_success()` (only on actual API call, not when price extraction fails)
- [ ] `_validate_scrape_url()` is called before every Firecrawl/Scrape.do call
- [ ] Gate 0 (`_validate_price_query()`) is the FIRST thing in `_get_price()`
- [ ] `source_method` tags: "firecrawl" for Tier 1.5a, "scrapedo_rendered" for Tier 1.5d, "page_scrape" for curl_cffi

- [ ] **Step 4: Verify dead code removal**
- [ ] `_fetch_rendered_html()` method is deleted
- [ ] `JS_ONLY_DOMAINS` set is deleted
- [ ] `JS_RENDER_TIMEOUT` constant is deleted
- [ ] `ENABLE_JS_RENDER` is removed
- [ ] 3 diagnostic endpoints removed from `app/main.py`
- [ ] No remaining references to `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `MICROLINK_API_KEY`, `RENDER_PROVIDER` in non-test Python files

- [ ] **Step 5: Verify test coverage meets 80%**

Check each new file has adequate test coverage:
- `api_budget_service.py`: budget tracking + circuit breaker + summary (20+ tests)
- `firecrawl_service.py`: all code paths including errors/timeouts (12+ tests)
- `scrapedo_service.py`: all code paths (10+ tests)
- Cascade integration: gates, early returns, conditional 1.5d (15+ tests)
- Input validation: boundary cases for both validators (12+ tests)
- Cost dashboard: endpoint auth + response format (6+ tests)

Total new tests target: **75+**

- [ ] **Step 6: Verify no regressions in existing test count**

The existing suite has ~1088 free unit tests. After changes, run:
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=120 | tail -5
```
**Criteria:** Total test count should be ~1088 + 75 new = ~1163. Exact count may vary due to test_js_rendering.py changes.

- [ ] **Step 7: Final commit message**

If all checks pass:
```bash
git log --oneline -10
```
Verify clean commit history with descriptive messages. No "fixup" or "wip" commits.

---

## Post-Implementation Checklist

After all tasks complete and QA passes:

- [ ] Update CLAUDE.md: replace Cloudflare/Microlink references with Firecrawl/Scrape.do, update env vars, add new test files to registry
- [ ] Update MEMORY.md: add Session 31 notes about Firecrawl integration
- [ ] Run validation spike: `curl` Firecrawl with 3 luxury URLs to confirm Smart Wait (see spec doc)
- [ ] Set `FIRECRAWL_API_KEY` and `SCRAPEDO_API_TOKEN` in Railway env vars
- [ ] Deploy to Railway: `git push origin main`
- [ ] Verify with: `curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=Louis+Vuitton+Neverfull+vs+Chanel+Classic+Flap&nocache=true"`
- [ ] Check cost dashboard: `curl -H "X-Admin-Key: $ADMIN_API_KEY" https://web-production-58776.up.railway.app/api/v1/admin/costs`
