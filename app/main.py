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
from app.api.legal_routes import router as legal_router  # Legal (privacy, terms)
from app.api.version_routes import router as version_router  # App version check
from app.api.usage_routes import router as usage_router      # Usage tracking
from app.api.referral_routes import router as referral_router  # Referral system
from app.api.home_routes import router as home_router          # Phase 2.5 editorial HomeScreen sections
from app.api.profile_routes import router as profile_router    # Phase 2.6 editorial ProfileScreen sections

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize Sentry (no-op if SENTRY_DSN not set)
from app.services.sentry_service import init_sentry
init_sentry()

# Announce the resolved OpenAI model ids once, so a running deployment is
# self-identifying: which model served a request is otherwise only knowable by
# reading the code at that commit. Ids come from model_config and are
# env-overridable (OPENAI_MODEL_VERDICT / _STANDARD / _VISION / _CRITIC /
# _MODERATION); see #58.
import logging as _logging
from app.services.model_config import resolved_models as _resolved_models
_logging.getLogger(__name__).info(
    "[models] " + " ".join(f"{role}={mid}" for role, mid in sorted(_resolved_models().items()))
)

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
    docs_url=None if os.getenv("RAILWAY_ENVIRONMENT") else "/docs",
    redoc_url=None if os.getenv("RAILWAY_ENVIRONMENT") else "/redoc",
)

# -- Middleware (order matters: outermost added last) --

# CORS (innermost -- runs first on response)
_DEFAULT_ORIGINS = [
    "https://web-production-58776.up.railway.app",
    "http://localhost:8000",
    "http://localhost:19006",   # Expo web
    "http://localhost:8081",    # Metro bundler
]

def _get_allowed_origins() -> list:
    """Get CORS origins from env var or defaults."""
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    return _DEFAULT_ORIGINS

ALLOWED_ORIGINS = _get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"],
)

# M13-01: register SlowAPIMiddleware so the limiter's default_limits actually
# fire on the routes WITHOUT an explicit @limiter.limit decorator. Without this
# the 21 undecorated routes (PUT /auth/password, PUT /auth/email, /usage/status,
# the referral invite endpoints, …) had no rate limit at all. Decorated routes
# stay exempt (slowapi's _should_exempt lets their decorator handle them, no
# double-limit). Added here — inside RequestIDMiddleware — so a 429 still carries
# the request_id and the security headers.
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(legal_router)   # /api/v1/legal/*
app.include_router(version_router) # /api/v1/app/*
app.include_router(usage_router)   # /api/v1/usage/*
app.include_router(referral_router)  # /api/v1/referrals/*
app.include_router(home_router)      # /api/v1/home/* (savings, smart-pick, trending)
app.include_router(profile_router)   # /api/v1/profile/* (recent-decisions, monthly-stats, priorities-weighted)

# Static admin assets — serves cohort dashboard at /admin/cohort.html
# (The admin endpoints these pages call are still under /api/v1/admin/*.)
#
# Auth model: the StaticFiles mount is wrapped to require the admin key
# via EITHER `X-Admin-Key` header (curl / scripts) OR HTTP Basic auth
# (browsers — the WWW-Authenticate response triggers the native prompt).
# Without this gate, /admin/*.html shells were world-readable even though
# the underlying /api/v1/admin/* JSON endpoints were protected.
import base64
import binascii
import hmac as _hmac
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.types import Receive, Scope, Send
from starlette.responses import Response as _Response


class _AdminAuthenticatedStaticFiles(StaticFiles):
    """StaticFiles subclass that gates every request on the admin key.

    Accepts the key from `X-Admin-Key` header (timing-safe compare) or
    from HTTP Basic auth's password field (any username). On miss, returns
    401 + `WWW-Authenticate: Basic` so a browser prompts the operator.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await super().__call__(scope, receive, send)
            return

        expected = os.getenv("ADMIN_API_KEY", "")
        if not expected:
            # Misconfigured deploy — refuse to serve admin pages at all.
            await _Response("Admin not configured", status_code=503)(scope, receive, send)
            return

        # Header lookup is case-insensitive per HTTP/1.1.
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

        x_admin = headers.get("x-admin-key", "")
        if x_admin and _hmac.compare_digest(x_admin, expected):
            await super().__call__(scope, receive, send)
            return

        authz = headers.get("authorization", "")
        if authz.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(authz[6:]).decode("utf-8")
                _, _, password = decoded.partition(":")
                if password and _hmac.compare_digest(password, expected):
                    await super().__call__(scope, receive, send)
                    return
            except (binascii.Error, UnicodeDecodeError):
                pass

        await _Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Qaren Admin"'},
        )(scope, receive, send)


_static_dir = _Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount(
        "/admin",
        _AdminAuthenticatedStaticFiles(directory=str(_static_dir / "admin"), html=True),
        name="admin-static",
    )

_favicon_path = _static_dir / "favicon.png"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    if _favicon_path.exists():
        return FileResponse(str(_favicon_path), media_type="image/png")
    from fastapi import Response
    return Response(status_code=204)


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
        "message": "Qaren API is running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
