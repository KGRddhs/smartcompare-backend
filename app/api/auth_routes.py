"""
Auth Routes - Authentication endpoints
"""
import asyncio
import hashlib
import logging
import re
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, List, Literal, Optional
from starlette.requests import Request
from app.middleware.rate_limiter import limiter

# Bundle A §1.1 — invite-code format. QR-XXXXXX with unambiguous alphabet
# matching app/services/referral_service.py::_CODE_ALPHABET (no 0/1/I/L/O).
_INVITE_CODE_RE = re.compile(r"^QR-[A-HJ-NP-Z2-9]{6}$")

# H5 (audit 2026-05-22) — SHA-256 hex format for X-Device-Fingerprint header.
# Frontend `deviceFingerprint.ts` computes SHA-256(appId|osBuildId|nonce) and
# emits 64-char lowercase hex. Anything else is dropped at the register
# endpoint to prevent fingerprint forging / inheritance poisoning of the
# Migration 021 anti-farming counter.
_DEVICE_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")

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
from app.services.cohort_service import get_cohort_service
from app.services.database_service import (
    save_user_demographics,
    get_user_demographics,
    save_user_attribution,
    get_user_supabase_client,
    get_admin_supabase_client,
)
from datetime import datetime, timezone

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
    # Optional referral invite UUID — set when the user signed up via an
    # invite link's quiz flow (design 3.7, plan B3.5). Backend links the
    # referral_invites row so Loop 2 fires on the user's first comparison.
    invite_id: Optional[str] = Field(default=None, max_length=64)
    # Bundle A §1.1 — typed-at-Register referral code (vs. deep-link invite_id).
    invite_code: Optional[str] = Field(default=None, max_length=16)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password_strength(v)

    @field_validator("invite_code")
    @classmethod
    def validate_invite_code_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not _INVITE_CODE_RE.match(v):
            raise ValueError("INVITE_CODE_INVALID")
        return v


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


VALID_PRIORITIES = [
    # Original 8 priority enum values (preserved for backwards compat)
    "price", "quality", "brand_reputation", "durability", "latest_features",
    "ease_of_use", "eco_friendly", "health_safety",
    # Cohort-derived enum values (added Session 41 — cohort_service.seed_preferences emits these)
    "best_price", "quality_reliability", "trusted_brand", "warranty_support",
    "design_aesthetics", "value_for_money",
]
VALID_BUDGET = ["budget", "mid", "premium", "luxury", "top_tier"]
VALID_LIFESTYLE = ["gamer", "photographer", "fitness_enthusiast", "vegan", "sensitive_skin", "parent", "student", "professional", "outdoor_adventurer", "minimalist", "tech_enthusiast"]
VALID_BRAND_ATTITUDE = [
    "brand_loyal", "function_first", "best_of_both",
    # Cohort-derived value (Session 41)
    "trust_known_brands",
]


_VALID_NOTIFICATION_TYPES = {
    "decision_insight",
    "cohort_curiosity",
    "decision_retrospective",
}


class UserPreferencesRequest(BaseModel):
    priorities: List[str] = Field(..., min_length=1, max_length=3)
    budget: str
    lifestyle: List[str] = Field(default_factory=list)
    brand_attitude: str
    # Per-user AI Quality Improvement Program toggle (PDPL opt-out, design 6.1).
    # None = unset = default ON (data-sharing project). False = opt out (private project).
    ai_sharing_enabled: Optional[bool] = None
    # F5.4 — re-engagement notifications master toggle. None = unset = default ON
    # (matches re-engagement-cron eligibility filter; pattern from design 9.2).
    notifications_enabled: Optional[bool] = None
    # F5.4 — per-type sub-toggles for the 3 re-engagement detectors. The
    # field_validator below whitelists the 3 known keys + coerces values to
    # bool; missing key is treated as ON downstream by reengagement_service.
    notification_types: Optional[dict] = None

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

    @field_validator("notification_types")
    @classmethod
    def _whitelist_notification_types(cls, v: Optional[dict]) -> Optional[dict]:
        """Whitelist the 3 known re-engagement event types and coerce values
        to bool. Unknown keys are silently dropped — defense in depth, same
        pattern as ShareRequest.privacy in referral_routes."""
        if not v:
            return v
        return {k: bool(val) for k, val in v.items() if k in _VALID_NOTIFICATION_TYPES}


# Alias for backward compatibility with tests
PreferencesRequest = UserPreferencesRequest


class DemographicsBody(BaseModel):
    """Request payload for PUT /demographics. All 5 fields optional.

    `language` and `country` are auto-derived server-side when missing
    (Accept-Language → language; CF-IPCountry → country).
    """
    age_group: Optional[str] = Field(default=None, max_length=64)
    gender: Optional[str] = Field(default=None, max_length=64)
    governorate: Optional[str] = Field(default=None, max_length=64)
    language: Optional[str] = Field(default=None, max_length=64)
    country: Optional[str] = Field(default=None, max_length=64)


class AttributionBody(BaseModel):
    """Request payload for POST /attribution. Onboarding step 11
    ("Where did you hear about us?") — single source enum.

    Pydantic Literal rejects unknown values with HTTP 422. The DB CHECK
    constraint from migration 019 mirrors this enum as defense-in-depth.
    """
    model_config = {"extra": "ignore"}
    source: Literal["friend", "instagram", "tiktok", "app_store", "google", "other"]


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
    - Optional invite_id links the user to a pending referral invite (B3.5).
      Loop 2 itself fires later when the invitee runs their first comparison
      (handled by save_comparison_and_track_cohort).
    - Bundle A §1.1: optional invite_code (typed at Register) is resolved
      server-side into a referral_invites row before link_invite_to_user.
    - Bundle A §1.5: X-Device-Fingerprint header locks the new user's
      lifetime_comparisons_used counter to the highest value seen on this
      device. Re-signups on the same device inherit prior usage so the
      free tier can't be reset by deleting the account.
    """
    result = await register_user(body.email, body.password)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Registration failed")
        )

    new_user_id = (result.get("user") or {}).get("id")

    # §1.5 — device fingerprint inheritance (best-effort, never blocks signup)
    # H5 (audit 2026-05-22): validate the header is a real SHA-256 hex hash
    # before using it. Without this, a malicious client could send any string
    # (empty, garbage, or another user's known hash) to poison or inherit
    # `lifetime_comparisons_used` counters — defeating the Migration 021
    # anti-farming gate. Legitimate clients (deviceFingerprint.ts) always
    # produce 64-char lowercase hex. Invalid values are dropped silently
    # so signup never blocks on a misconfigured/tampered client.
    fp = request.headers.get("X-Device-Fingerprint")
    if fp and not _DEVICE_FINGERPRINT_RE.match(fp):
        logger.info(
            "device-fp header rejected: invalid format (expected 64-char hex), len=%d",
            len(fp),
        )
        fp = None
    if fp and new_user_id:
        try:
            admin_client = get_admin_supabase_client()
            prior = (
                admin_client.table("users")
                .select("lifetime_comparisons_used")
                .eq("device_fingerprint_hash", fp)
                .order("lifetime_comparisons_used", desc=True)
                .limit(1)
                .execute()
            )
            inherited = 0
            if prior.data:
                inherited = prior.data[0].get("lifetime_comparisons_used", 0) or 0
            admin_client.table("users").update(
                {
                    "device_fingerprint_hash": fp,
                    "lifetime_comparisons_used": inherited,
                }
            ).eq("id", new_user_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"device-fp inheritance failed (silent): {exc}")

    # §1.1 — resolve typed invite_code → invite_id if invite_id not supplied
    resolved_invite_id = body.invite_id
    if body.invite_code and not resolved_invite_id and new_user_id:
        from app.services import referral_service
        resolved_invite_id = await referral_service.resolve_code_to_invite_id(
            body.invite_code, new_user_id,
        )
        if resolved_invite_id is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Invite code not found",
                    "code": "INVITE_CODE_NOT_FOUND",
                },
            )

    # B3.5 — link invite to the new user (fire-and-forget, never blocks signup).
    # We resolve the function via app.services.referral_service so test-referral
    # can patch either `app.services.referral_service.link_invite_to_user` OR
    # `app.api.auth_routes.link_invite_to_user`. Module-attribute access (rather
    # than a top-of-file `from ... import`) makes the first patch path work.
    if resolved_invite_id and new_user_id:
        try:
            from app.services import referral_service
            await referral_service.link_invite_to_user(
                new_user_id, resolved_invite_id,
            )
        except Exception as exc:  # noqa: BLE001
            # Linker failure must not break signup — Loop 2 just won't fire.
            logger.warning(f"link_invite_to_user failed (silent): {exc}")

    # Bundle A §1.8 — audit-log code redemptions for abuse forensics.
    # Only when the user typed a code (not invite_id deep-link); the invite
    # row already encodes the deep-link path. Details deliberately omit PII —
    # the user_id field handles identity, code + invite_id are sufficient
    # for forensic correlation.
    if body.invite_code and resolved_invite_id and new_user_id:
        asyncio.create_task(log_audit_event(
            event_type="invite_code_redeemed",
            user_id=new_user_id,
            ip_address=request.client.host if request.client else None,
            endpoint="/api/v1/auth/register",
            details={
                "invite_code": body.invite_code,
                "invite_id": resolved_invite_id,
            },
        ))

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
    """Refresh an expired access token using a refresh token.

    Rotation behaviour (Bundle D Task 1.B.3, R9):

    Supabase Auth rotates refresh tokens on every successful call to
    `/refresh` — the old refresh token is invalidated and a new one is
    returned in the `session.refresh_token` of the response. This means
    each refresh token is **single-use**.

    If two concurrent clients race to refresh with the same token, only
    one wins; the loser gets a 401 (`invalid refresh token`). Deduping
    is therefore a CLIENT-SIDE responsibility — the mobile app must hold
    a module-scope singleton Promise around the refresh call so parallel
    401 handlers cooperate on one network round-trip (see Frontend
    commit `03b9139` for the React Native mutex).

    The backend itself does NOT cache refresh attempts (no shared state
    here, by design — we trust Supabase Auth as the source of truth and
    avoid double-rotation issues that would come from caching).
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


def _flip_inferred_sources(new_prefs: dict, existing: Optional[dict]) -> dict:
    """Compute updated _sources dict: changed fields flip inferred → user_stated.

    Per design 5.3 + plan A.4.3: when a user edits a previously-seeded preference,
    the source flips so future seeding can't overwrite the user's choice.

    - If no existing preferences: all populated fields → user_stated.
    - If existing has _sources: copy then flip changed fields to user_stated.
    - If existing has values but no _sources (legacy): treat as user_stated.
    """
    existing_sources = (existing or {}).get("_sources") or {}
    fields = ("priorities", "budget", "lifestyle", "brand_attitude")

    out: dict[str, Any] = {}
    for f in fields:
        existing_value = (existing or {}).get(f)
        new_value = new_prefs.get(f)
        if existing is None:
            # Brand new prefs — all entries are user-stated by definition
            out[f] = "user_stated"
        elif new_value != existing_value:
            # User changed this field — always user_stated
            out[f] = "user_stated"
        else:
            # Unchanged — preserve prior source (or assume user_stated if absent)
            out[f] = existing_sources.get(f, "user_stated")
    # Lifestyle stays None when empty list AND was previously None (cohort-seeded)
    if not new_prefs.get("lifestyle") and existing_sources.get("lifestyle") is None:
        out["lifestyle"] = None
    return out


@router.put("/preferences")
async def save_preferences(
    body: UserPreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save or update user preferences. All 4 fields are mandatory.

    Tracks `_sources` to distinguish user-stated vs cohort-inferred values:
    edits to previously-inferred fields flip their source to user_stated so
    future demographics-driven seeding doesn't overwrite the user's choice.
    """
    preferences = body.model_dump()
    user_id = current_user["id"]

    # Read existing prefs to compute source flips
    existing_response = await get_user_preferences(user_id)
    existing_prefs = None
    if isinstance(existing_response, dict):
        if existing_response.get("success"):
            existing_prefs = existing_response.get("preferences") or None
        elif "preferences" not in existing_response:
            existing_prefs = existing_response  # raw dict path
    elif existing_response is not None:
        existing_prefs = existing_response

    preferences["_sources"] = _flip_inferred_sources(preferences, existing_prefs)

    result = await save_user_preferences(user_id, preferences)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to save preferences"))
    return result


# ============================================
# F5.4 — Expo Push token registration
# ============================================


class PushTokenBody(BaseModel):
    """Body for PUT /api/v1/auth/push-token. The Expo token format is
    ``ExponentPushToken[XXXXX...]`` — about 40 chars typical, capped at
    256 to leave headroom for future Expo token formats."""

    expo_push_token: str = Field(..., min_length=1, max_length=256)


@router.put("/push-token")
@limiter.limit("10/minute")
async def update_push_token(
    request: Request,
    body: PushTokenBody,
    current_user: dict = Depends(get_current_user),
):
    """Register or update the user's Expo push token (idempotent).

    Writes to ``users.expo_push_token`` (column from migration 015).
    Uses the user-scoped Supabase client so RLS policies enforce that
    users can only update their own row. Loop 2 + re-engagement pushes
    pick up the new token via ``push_service._get_user_push_token``.
    """
    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )
    try:
        client.table("users").update(
            {"expo_push_token": body.expo_push_token}
        ).eq("id", current_user["id"]).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"push token update failed for {current_user['id']}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "error": "Failed to register push token"},
        )
    return {"success": True}


# ============================================
# F5.4 — Re-engagement notification sub-toggles (Bundle D Task 2.B.7, R18)
# ============================================

# Bundle D + design § 11 Default #6 — Profile screen exposes 3 friendlier
# user-facing labels:
#   - "Decision Insights"              → backend key `decision_insight`
#   - "Peer decision updates"          → backend key `cohort_curiosity`
#   - "14-day decision retrospectives" → backend key `decision_retrospective`
#
# The body shape uses the user-facing PLURAL key names (matches the design
# doc and the Frontend toggle labels). Server-side we translate to the
# existing SINGULAR keys in users.preferences.notification_types so the
# `reengagement_service.py` short-circuit logic in `evaluate()` keeps
# working unchanged.
_REENG_KEY_MAP = {
    "decision_insights": "decision_insight",
    "peer_decision_updates": "cohort_curiosity",
    "decision_retrospectives": "decision_retrospective",
}


class ReengagementSubsBody(BaseModel):
    """Body for PUT /api/v1/auth/reengagement-subs. All 3 toggles required.

    Maps to the 3 detectors in `reengagement_service.py`. Updates ONLY
    the `users.preferences.notification_types` sub-dict — does NOT touch
    other preference fields (priorities, budget, lifestyle, brand_attitude,
    ai_sharing_enabled, notifications_enabled).
    """

    decision_insights: bool
    peer_decision_updates: bool
    decision_retrospectives: bool


@router.put("/reengagement-subs")
@limiter.limit("10/minute")
async def update_reengagement_subs(
    request: Request,
    body: ReengagementSubsBody,
    current_user: dict = Depends(get_current_user),
):
    """Update the user's re-engagement notification sub-toggles.

    Reads-modifies-writes `users.preferences.notification_types` so we
    preserve other preference keys. Uses the user-scoped Supabase client
    so RLS enforces row ownership.
    """
    access_token = current_user.get("access_token")
    client = (
        get_user_supabase_client(access_token) if access_token
        else get_admin_supabase_client()
    )
    user_id = current_user["id"]

    # Map FE-facing plural keys → reengagement_service singular keys
    payload = body.model_dump()
    new_types = {
        backend_key: bool(payload[fe_key])
        for fe_key, backend_key in _REENG_KEY_MAP.items()
    }

    try:
        # Read-modify-write so we don't blast other preferences fields
        row_resp = client.table("users").select("preferences").eq(
            "id", user_id
        ).single().execute()
        current_prefs = (row_resp.data or {}).get("preferences") or {}
        current_prefs["notification_types"] = new_types
        client.table("users").update(
            {"preferences": current_prefs}
        ).eq("id", user_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[AUTH] reengagement-subs update failed for %s: %s: %r",
            user_id, type(exc).__name__, exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "error": "Failed to update notification preferences",
            },
        )
    return {"success": True, "notification_types": new_types}


# ============================================
# Demographics + cohort profile (migration 013)
# ============================================


def _derive_language(request: Request, payload_language: Optional[str]) -> str:
    """Resolve language from explicit payload or Accept-Language header."""
    if payload_language:
        return payload_language
    accept = (request.headers.get("accept-language") or "").lower()
    if accept.startswith("ar"):
        return "Arabic"
    if accept.startswith("en"):
        return "English"
    return "Both equally"


def _derive_country(request: Request, payload_country: Optional[str]) -> str:
    """Resolve country from explicit payload or Cloudflare CF-IPCountry header."""
    if payload_country:
        return payload_country
    cf_country = (request.headers.get("cf-ipcountry") or "").upper().strip()
    if cf_country == "BH":
        return "Bahrain"
    return cf_country or "Bahrain"


@router.put("/demographics")
@limiter.limit("5/minute")
async def save_demographics(
    request: Request,
    body: DemographicsBody,
    current_user: dict = Depends(get_current_user),
):
    """Persist demographics_profile + match cohort + seed prefs (one-shot).

    Auto-detects language and country from request headers when not provided.
    Stores the cohort_match snapshot inside demographics_profile so subsequent
    requests can render the cohort priors block without re-matching.

    If the user has no preferences (or all sources are inferred), seeds them
    from the cohort modal. Never overwrites user_stated preferences.
    """
    user_id = current_user["id"]
    payload = body.model_dump(exclude_none=False)
    payload["language"] = _derive_language(request, payload.get("language"))
    payload["country"] = _derive_country(request, payload.get("country"))

    cohort_svc = get_cohort_service()
    match = cohort_svc.match(payload)

    profile = {
        **payload,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "cohort_match": (
            {
                "cohort_key": match.cohort_key,
                "match_quality": match.match_quality,
                "confidence": match.confidence,
                "n": match.n,
                "persona_label": match.persona_label,
            }
            if match
            else None
        ),
    }

    save_result = await save_user_demographics(user_id, profile)
    if not save_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=save_result.get("error", "Failed to save demographics"),
        )

    # Seed preferences when the user hasn't taken ownership yet
    existing_prefs_response = await get_user_preferences(user_id)
    existing_prefs = None
    if isinstance(existing_prefs_response, dict):
        if existing_prefs_response.get("success"):
            existing_prefs = existing_prefs_response.get("preferences") or None
        elif "preferences" not in existing_prefs_response:
            existing_prefs = existing_prefs_response

    if cohort_svc.should_seed(existing_prefs):
        seeded = cohort_svc.seed_preferences(payload)
        if seeded:
            await save_user_preferences(user_id, seeded)

    return {
        "success": True,
        "cohort_match": profile["cohort_match"],
    }


@router.get("/cohort-profile")
async def get_cohort_profile(current_user: dict = Depends(get_current_user)):
    """Return the display payload for the Profile screen 'style profile' card.

    `display` is None when the user hasn't submitted demographics OR the
    cohort match is too weak (population fallback / low confidence).
    """
    user_id = current_user["id"]
    demographics = await get_user_demographics(user_id)
    if not demographics:
        return {"display": None}

    cohort_svc = get_cohort_service()
    display = cohort_svc.get_display_profile(demographics)
    return {"display": display}


# ============================================
# Attribution (migration 019, plan task 8)
# ============================================


@router.post("/attribution")
@limiter.limit("30/minute")
async def save_attribution(
    request: Request,
    body: AttributionBody,
    current_user: dict = Depends(get_current_user),
):
    """Persist the user's answer to onboarding step 11 (attribution source).

    Resubmits overwrite — last write wins. Pydantic Literal validates the
    enum at request time; the DB CHECK constraint from migration 019
    enforces the same set as defense-in-depth.
    """
    user_id = current_user["id"]
    result = await save_user_attribution(user_id, body.source)
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to save attribution"),
        )
    return {"success": True}
