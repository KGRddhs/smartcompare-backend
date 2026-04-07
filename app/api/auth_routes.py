"""
Auth Routes - Authentication endpoints
"""
import asyncio
import hashlib
import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Literal, Optional
from starlette.requests import Request
from app.middleware.rate_limiter import limiter

from app.services.auth_service import (
    register_user,
    login_user,
    refresh_session,
    verify_token,
    get_user_profile,
    logout_user,
    request_password_reset,
    update_user_profile,
    update_user_email,
    change_user_password,
    sign_in_with_social,
    get_user_preferences,
    save_user_preferences,
    delete_user_account,
    resend_verification_email,
    check_account_locked,
    track_failed_login,
    clear_failed_logins,
)
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ============================================
# Request/Response Models
# ============================================

def _validate_password_strength(password: str) -> str:
    """Validate password meets strength requirements."""
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    return password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)


class UpdateEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=10)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v):
        return _validate_password_strength(v)


VALID_PRIORITIES = ["price", "quality", "brand_reputation", "durability", "latest_features", "ease_of_use", "eco_friendly", "health_safety"]
VALID_BUDGET = ["budget", "mid", "premium"]
VALID_LIFESTYLE = ["gamer", "photographer", "fitness_enthusiast", "vegan", "sensitive_skin", "parent", "student", "professional", "outdoor_adventurer", "minimalist", "tech_enthusiast"]
VALID_BRAND_ATTITUDE = ["brand_loyal", "function_first", "best_of_both"]


class UserPreferencesRequest(BaseModel):
    priorities: List[str] = Field(..., min_length=1, max_length=3)
    budget: str
    lifestyle: List[str] = Field(default_factory=list)
    brand_attitude: str

    @field_validator("priorities")
    @classmethod
    def validate_priorities(cls, v: List[str]) -> List[str]:
        for p in v:
            if p not in VALID_PRIORITIES:
                raise ValueError(f"Invalid priority: {p}. Must be one of {VALID_PRIORITIES}")
        return v

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: str) -> str:
        if v not in VALID_BUDGET:
            raise ValueError(f"Invalid budget: {v}. Must be one of {VALID_BUDGET}")
        return v

    @field_validator("lifestyle")
    @classmethod
    def validate_lifestyle(cls, v: List[str]) -> List[str]:
        for tag in v:
            if tag not in VALID_LIFESTYLE:
                raise ValueError(f"Invalid lifestyle tag: {tag}. Must be one of {VALID_LIFESTYLE}")
        return v

    @field_validator("brand_attitude")
    @classmethod
    def validate_brand_attitude(cls, v: str) -> str:
        if v not in VALID_BRAND_ATTITUDE:
            raise ValueError(f"Invalid brand_attitude: {v}. Must be one of {VALID_BRAND_ATTITUDE}")
        return v


# Alias for backward compatibility with tests
PreferencesRequest = UserPreferencesRequest


class SocialLoginRequest(BaseModel):
    provider: Literal["google", "apple"]
    id_token: str
    nonce: Optional[str] = None  # Apple Sign-In uses nonce


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
    except Exception:
        return None


# ============================================
# Auth Endpoints
# ============================================

@router.post("/register", response_model=AuthResponse)
@limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest):
    """
    Register a new user.

    - Email must be valid
    - Password must be at least 10 characters with uppercase, lowercase, and number
    """
    result = await register_user(body.email, body.password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Registration failed")
        )
    
    return result


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """
    Login with email and password.

    Returns access_token and refresh_token on success.
    """
    # Check brute-force lockout BEFORE attempting login
    lockout = await check_account_locked(body.email)
    if lockout["locked"]:
        asyncio.create_task(log_audit_event(
            event_type="brute_force_lockout",
            ip_address=request.client.host if request.client else None,
            endpoint="/api/v1/auth/login",
            details={"email_hash": hashlib.sha256(body.email.lower().encode()).hexdigest()[:16]}
        ))
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Account temporarily locked due to too many failed attempts",
                "code": "ACCOUNT_LOCKED",
                "retry_after": lockout["retry_after"]
            }
        )

    result = await login_user(body.email, body.password)

    if not result["success"]:
        await track_failed_login(body.email)
        asyncio.create_task(log_audit_event(
            event_type="login_failed",
            ip_address=request.client.host if request.client else None,
            endpoint="/api/v1/auth/login",
            details={"reason": result.get("error", "unknown")}
        ))
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Login failed")
        )

    # Success — clear lockout counter
    await clear_failed_logins(body.email)
    asyncio.create_task(log_audit_event(
        event_type="login_success",
        user_id=result.get("user", {}).get("id"),
        ip_address=request.client.host if request.client else None,
        endpoint="/api/v1/auth/login",
    ))
    return result


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, body: RefreshRequest):
    """
    Refresh an expired access token using refresh token.
    """
    result = await refresh_session(body.refresh_token)
    
    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Failed to refresh session")
        )
    
    return result


@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Logout current user.
    """
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            await logout_user(token)
    except Exception as e:
        logger.warning(f"Logout sign-out failed (non-critical): {e}")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    try:
        # get_user_profile returns raw Supabase row dict or None
        profile = await get_user_profile(current_user["id"])
        if profile:
            return {
                "success": True,
                "user": {
                    "id": current_user["id"],
                    "email": current_user.get("email"),
                    "display_name": profile.get("display_name"),
                    "auth_provider": profile.get("auth_provider"),
                    "subscription_tier": profile.get("subscription_tier", "free"),
                    "created_at": profile.get("created_at"),
                    "preferences_completed": profile.get("preferences_completed", False),
                }
            }
    except Exception as e:
        logger.warning(f"Profile lookup failed for {current_user['id']}: {e}")

    # Fallback: return consistent shape with defaults
    return {
        "success": True,
        "user": {
            "id": current_user["id"],
            "email": current_user.get("email"),
            "display_name": None,
            "auth_provider": None,
            "subscription_tier": "free",
            "created_at": None,
            "preferences_completed": False,
        }
    }


@router.post("/password-reset")
@limiter.limit("3/minute")
async def password_reset(request: Request, body: PasswordResetRequest):
    """
    Request password reset email.
    """
    result = await request_password_reset(body.email)
    
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


@router.put("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user display name."""
    result = await update_user_profile(current_user["id"], body.display_name)
    return result


@router.put("/email")
async def update_email(
    body: UpdateEmailRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user email. Requires current password for verification."""
    result = await update_user_email(
        current_user["id"], current_user["email"],
        body.current_password, str(body.new_email)
    )
    if not result["success"]:
        status = 400 if "password" in result.get("error", "").lower() else 500
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.put("/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change password. Requires current password for verification."""
    result = await change_user_password(
        current_user["id"], current_user["email"],
        body.current_password, body.new_password
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/social-login")
@limiter.limit("10/minute")
async def social_login(request: Request, body: SocialLoginRequest):
    """Authenticate via Google or Apple ID token. Creates account if new."""
    result = await sign_in_with_social(body.provider, body.id_token, body.nonce)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.delete("/account")
@limiter.limit("1/minute")
async def delete_account(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Delete user account and all associated data (App Store requirement)."""
    try:
        await delete_user_account(current_user["id"])
        return {"success": True, "message": "Account and all associated data deleted"}
    except Exception as e:
        logger.error(f"Account deletion failed for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Account deletion failed")


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(request: Request, body: PasswordResetRequest):
    """Resend email verification link."""
    try:
        await resend_verification_email(body.email)
        return {"success": True, "message": "Verification email sent if account exists"}
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        # Always return success to avoid email enumeration
        return {"success": True, "message": "Verification email sent if account exists"}


# ============================================
# Preferences Endpoints
# ============================================

@router.get("/preferences")
async def get_preferences(current_user: dict = Depends(get_current_user)):
    """Get current user's preferences."""
    result = await get_user_preferences(current_user["id"])
    if result is None:
        return {"success": True, "preferences": {}, "preferences_completed": False}
    # If result is a structured response from get_user_preferences
    if isinstance(result, dict) and "success" in result:
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "Preferences not found"))
        return result
    # If result is raw preferences dict (e.g. from direct DB query)
    return {"success": True, "preferences": result, "preferences_completed": bool(result)}


@router.put("/preferences")
async def save_preferences(
    body: UserPreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save or update user preferences. All 4 fields are mandatory."""
    preferences = body.model_dump()
    result = await save_user_preferences(current_user["id"], preferences)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to save preferences"))
    return result
