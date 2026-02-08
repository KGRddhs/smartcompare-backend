"""
Auth Routes - Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services.auth_service import (
    register_user,
    login_user,
    refresh_session,
    verify_token,
    get_user_profile,
    logout_user,
    request_password_reset
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ============================================
# Request/Response Models
# ============================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    success: bool
    user: Optional[dict] = None
    session: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ============================================
# Auth Dependency
# ============================================

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Dependency to get current authenticated user.
    Extracts and verifies JWT from Authorization header.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use: Bearer <token>"
        )
    
    token = parts[1]
    user = await verify_token(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    return user


async def get_optional_user(authorization: Optional[str] = Header(None)):
    """
    Optional auth - returns user if authenticated, None otherwise.
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if not authorization:
        return None
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        token = parts[1]
        return await verify_token(token)
    except:
        return None


# ============================================
# Auth Endpoints
# ============================================

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user.
    
    - Email must be valid
    - Password must be at least 6 characters
    """
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )
    
    result = await register_user(request.email, request.password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Registration failed")
        )
    
    return result


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    
    Returns access_token and refresh_token on success.
    """
    result = await login_user(request.email, request.password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Login failed")
        )
    
    return result


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: RefreshRequest):
    """
    Refresh an expired access token using refresh token.
    """
    result = await refresh_session(request.refresh_token)
    
    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Failed to refresh session")
        )
    
    return result


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout current user.
    """
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get current user's profile.
    """
    profile = await get_user_profile(current_user["id"])
    
    if profile:
        return {
            "success": True,
            "user": {
                "id": profile["id"],
                "email": profile["email"],
                "subscription_tier": profile.get("subscription_tier", "free"),
                "created_at": profile.get("created_at")
            }
        }
    
    return {
        "success": True,
        "user": current_user
    }


@router.post("/password-reset")
async def password_reset(request: PasswordResetRequest):
    """
    Request password reset email.
    """
    result = await request_password_reset(request.email)
    
    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If an account with that email exists, a reset link has been sent."
    }


@router.get("/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    """
    Verify if current token is valid.
    Useful for checking auth status on app startup.
    """
    return {
        "success": True,
        "valid": True,
        "user": current_user
    }
