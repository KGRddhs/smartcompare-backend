"""
SmartCompare Backend - Main Application
With structured text comparison
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import routes after env vars are loaded
from app.api.routes import router as api_router
from app.api.auth_routes import router as auth_router
from app.api.text_routes import router as text_router

# Create FastAPI app
app = FastAPI(
    title="SmartCompare API",
    description="AI-powered product comparison API with structured data extraction",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (allow mobile app to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)       # /api/v1/compare, /api/v1/history, etc.
app.include_router(auth_router)      # /api/v1/auth/login, /api/v1/auth/register, etc.
app.include_router(text_router)      # /api/v1/text/compare - NEW structured comparison


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "SmartCompare API",
        "version": "2.0.0",
        "features": [
            "Image comparison (Vision AI)",
            "Text comparison (Structured extraction)",
            "GCC regional pricing",
            "User authentication"
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
