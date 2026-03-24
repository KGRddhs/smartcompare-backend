"""
SmartCompare Backend - Main Application
Professional product comparison API with multiple input methods
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(override=True)

# Configure structured logging before any other imports
from app.middleware.logging_config import configure_logging
configure_logging(os.getenv("LOG_LEVEL", "INFO"))

# Import routes after env vars are loaded
from app.api.auth_routes import router as auth_router    # Authentication
from app.api.text_routes import router as text_router    # Text comparison
from app.api.url_routes import router as url_router      # URL comparison
from app.api.image_routes import router as image_router  # Camera identification + comparison
from app.api.admin_routes import router as admin_router  # Admin analytics
from app.api.feedback_routes import router as feedback_router  # Feedback + events
from app.api.history_routes import router as history_router  # Comparison history
from app.api.share_routes import router as share_router  # Comparison sharing

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import limiter
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

# -- Middleware (order matters: outermost added last) --

# CORS (innermost -- runs first on response)
ALLOWED_ORIGINS = [
    "https://web-production-58776.up.railway.app",
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

# Exception handlers (unified error format)
app.state.limiter = limiter
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    rate_limit_handler,
)
from fastapi.exceptions import RequestValidationError

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Error handler (catches unhandled exceptions)
app.add_middleware(ErrorHandlerMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID (outermost -- generates ID before anything else)
app.add_middleware(RequestIDMiddleware)

# -- Routes --
app.include_router(auth_router)      # /api/v1/auth/*
app.include_router(text_router)      # /api/v1/text/*
app.include_router(url_router)       # /api/v1/url/*
app.include_router(image_router)     # /api/v1/image/* (camera)
app.include_router(admin_router, prefix="/api/v1/admin")  # /api/v1/admin/*
app.include_router(feedback_router)  # /api/v1/feedback, /api/v1/events
app.include_router(history_router)  # /api/v1/comparisons/*
app.include_router(share_router)   # /api/v1/share/*


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "healthy",
        "app": "SmartCompare API",
        "version": "2.1.0",
        "endpoints": {
            "image_identify": "/api/v1/image/identify",
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


# Cold-start prevention: Railway supports cron jobs to keep the service warm.
# Set up a Railway cron service that pings GET /health every 5 minutes:
#   Schedule: */5 * * * *
#   Command:  curl -sf https://smartcompare-backend-production.up.railway.app/health
# This prevents the ~10-20s cold start penalty on first request after idle.

@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "message": "SmartCompare API is running"
    }


@app.get("/health/render-test")
async def render_test():
    """Diagnostic: test JS rendering providers (Cloudflare Browser Rendering + Microlink).

    Tests credential availability and live rendering of a simple page.
    Remove this endpoint after confirming the setup works.
    """
    import httpx
    import asyncio
    import time

    results = {
        "cloudflare": {"configured": False, "status": None, "error": None, "html_size": 0, "latency_ms": 0},
        "microlink": {"configured": False, "status": None, "error": None, "html_size": 0, "latency_ms": 0},
    }

    test_url = "https://www.hermes.com/us/en/category/women/bags-and-small-leather-goods/bags-and-clutches/"

    # --- Cloudflare Browser Rendering ---
    cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    results["cloudflare"]["configured"] = bool(cf_account and cf_token)

    if cf_account and cf_token:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/browser-rendering/content",
                    headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                    json={"url": test_url, "gotoOptions": {"waitUntil": "networkidle0"}},
                )
                results["cloudflare"]["status"] = resp.status_code
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        html = data.get("result", "") or data.get("html", "") or resp.text
                    except Exception:
                        html = resp.text
                    results["cloudflare"]["html_size"] = len(html)
                    # Check for price-like content
                    results["cloudflare"]["has_price_data"] = "$" in html or "price" in html.lower()[:5000]
                else:
                    results["cloudflare"]["error"] = resp.text[:300]
        except Exception as e:
            results["cloudflare"]["error"] = str(e)
        results["cloudflare"]["latency_ms"] = int((time.monotonic() - start) * 1000)

    # --- Microlink ---
    ml_key = os.environ.get("MICROLINK_API_KEY")
    results["microlink"]["configured"] = True  # works without key (free tier)
    results["microlink"]["has_api_key"] = bool(ml_key)

    start = time.monotonic()
    try:
        headers = {}
        if ml_key:
            headers["x-api-key"] = ml_key
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.microlink.io",
                params={"url": test_url, "prerender": "true"},
                headers=headers,
            )
            results["microlink"]["status"] = resp.status_code
            if resp.status_code == 200:
                data = resp.json()
                html = data.get("data", {}).get("html", "")
                results["microlink"]["html_size"] = len(html)
                results["microlink"]["has_price_data"] = "$" in html or "price" in html.lower()[:5000]
                results["microlink"]["microlink_status"] = data.get("status")
            else:
                results["microlink"]["error"] = resp.text[:300]
    except Exception as e:
        results["microlink"]["error"] = str(e)
    results["microlink"]["latency_ms"] = int((time.monotonic() - start) * 1000)

    # --- Feature flags + credential debug ---
    results["feature_flags"] = {
        "ENABLE_PAGE_SCRAPE": os.environ.get("ENABLE_PAGE_SCRAPE", "true"),
        "ENABLE_JS_RENDER": os.environ.get("ENABLE_JS_RENDER", "true"),
        "RENDER_PROVIDER": os.environ.get("RENDER_PROVIDER", "both"),
    }
    # Masked credentials for debugging (first 6 + last 4 chars only)
    def _mask(val):
        if not val:
            return None
        if len(val) <= 10:
            return val[:2] + "***"
        return val[:6] + "..." + val[-4:]
    results["credentials_debug"] = {
        "cf_account_id": _mask(cf_account),
        "cf_token": _mask(cf_token),
        "cf_account_id_len": len(cf_account) if cf_account else 0,
        "cf_token_len": len(cf_token) if cf_token else 0,
    }

    return results


@app.get("/health/render-price-test")
async def render_price_test(url: str = "https://www.chanel.com/us/fashion/handbags/c/1x1x1/"):
    """Diagnostic: render a URL via Cloudflare and attempt price extraction.

    Tests the full pipeline: render → extract JSON-LD/OG/microdata.
    Remove after confirming setup works.
    """
    import httpx
    import time
    from urllib.parse import urlparse
    from app.services.structured_comparison_service import get_comparison_service

    svc = get_comparison_service()
    result = {"url": url, "domain": urlparse(url).netloc.replace("www.", "")}

    # Step 1: Render via Cloudflare
    start = time.monotonic()
    rendered_html = await svc._fetch_rendered_html(url)
    result["render_latency_ms"] = int((time.monotonic() - start) * 1000)
    result["rendered"] = rendered_html is not None
    result["html_size"] = len(rendered_html) if rendered_html else 0

    if rendered_html:
        # Check what structured data exists
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(rendered_html, 'html.parser')

        # JSON-LD scripts
        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        result["jsonld_count"] = len(jsonld_scripts)
        result["jsonld_preview"] = [s.string[:200] if s.string else "" for s in jsonld_scripts[:3]]

        # OG meta tags
        og_price = soup.find('meta', property='og:price:amount')
        og_currency = soup.find('meta', property='og:price:currency')
        result["og_price"] = og_price.get('content') if og_price else None
        result["og_currency"] = og_currency.get('content') if og_currency else None

        # Microdata
        price_spans = soup.find_all(attrs={"itemprop": "price"})
        result["microdata_prices"] = [
            {"content": s.get("content", s.text[:50])} for s in price_spans[:3]
        ]

        # Try actual extraction
        price = svc._extract_price_from_html(rendered_html, "Chanel Classic Flap", "BHD", result["domain"], url)
        result["extracted_price"] = price

        # HTML snippet around "price" keyword (all occurrences)
        html_lower = rendered_html.lower()
        price_snippets = []
        search_start = 0
        while len(price_snippets) < 5:
            idx = html_lower.find('price', search_start)
            if idx == -1:
                break
            price_snippets.append(rendered_html[max(0, idx-30):idx+100])
            search_start = idx + 10
        result["price_snippets"] = price_snippets

        # Also check for currency symbols
        for sym in ['$', '£', '€', 'BHD', 'USD']:
            idx = rendered_html.find(sym)
            if idx >= 0:
                result[f"found_{sym}"] = rendered_html[max(0, idx-30):idx+50]
    else:
        result["error"] = "Cloudflare render returned no HTML"

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
