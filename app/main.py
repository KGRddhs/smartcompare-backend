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

# -- Middleware (order matters: outermost added last) --

# CORS (innermost -- runs first on response)
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

# Request ID (outermost -- generates ID before anything else)
app.add_middleware(RequestIDMiddleware)

# -- Routes --
app.include_router(api_router)       # /api/v1/compare (legacy image)
app.include_router(auth_router)      # /api/v1/auth/*
app.include_router(text_router)      # /api/v1/text/*
app.include_router(url_router)       # /api/v1/url/*
app.include_router(image_router)     # /api/v1/image/* (camera)
app.include_router(admin_router, prefix="/api/v1/admin")  # /api/v1/admin/*


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
