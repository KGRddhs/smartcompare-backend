"""
Auth Service - Supabase Authentication
"""
import asyncio
import hashlib
import logging
import os
from typing import Optional, Dict
from supabase import create_client, Client

from app.services.cache_service import redis_client, _redis_offload_enabled
from app.services.database_service import record_preference_history
from app.utils.async_utils import fire_and_forget
from app.utils.db_offload import run_db  # M13-05 ENABLE_SYNC_DB_OFFLOAD

logger = logging.getLogger(__name__)

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def get_auth_client() -> Client:
    """Get Supabase client for auth operations (uses anon key)"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_admin_client() -> Client:
    """Get Supabase client with service role (admin operations)"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _categorize_auth_error(e: Exception, context: str = "operation") -> Dict:
    """Categorize auth errors into user-friendly messages."""
    error_msg = str(e).lower()
    if "invalid login credentials" in error_msg:
        return {"success": False, "error": "Invalid email or password"}
    elif "user already registered" in error_msg:
        return {"success": False, "error": "An account with this email already exists"}
    elif "email not confirmed" in error_msg:
        return {"success": False, "error": "Please verify your email before logging in"}
    elif any(term in error_msg for term in [
        "network", "connection", "timeout", "dns", "econnrefused",
        "socket hang up", "enotfound", "failed to fetch", "no network"
    ]):
        return {"success": False, "error": "Connection failed. Please try again."}
    else:
        logger.error(f"Auth error in {context}: {e}")
        # Bundle E B4 diagnostic (2026-05-26, Ahmed Sentry-sampling issue):
        # When Sentry sample rate drops the event, we have no way to see the
        # underlying Supabase rejection. Surface the raw exception text in the
        # response for `social_login` context only, prefixed [B4-BE-DIAG] for
        # grep. The FE's [B4-DIAG] wrapper surfaces this directly on-screen so
        # Ahmed (or any tester) can read the actual failure mode without log
        # forensics. REMOVE this branch after B4 ships green + clean.
        if context == "social_login":
            return {
                "success": False,
                "error": f"[B4-BE-DIAG] supabase_error={str(e)[:300]} exc_type={type(e).__name__}",
            }
        return {"success": False, "error": "Something went wrong. Please try again later."}


async def _enrich_response_with_profile(response: Dict, user_id: str) -> Dict:
    """Add display_name and auth_provider from public.users to auth response.
    Never fails — returns None defaults if profile unavailable."""
    display_name = None
    auth_provider = None
    try:
        admin = get_admin_client()
        profile = admin.table("users").select("display_name, auth_provider").eq("id", user_id).single().execute()
        if profile.data:
            display_name = profile.data.get("display_name")
            auth_provider = profile.data.get("auth_provider")
    except Exception as e:
        logger.warning(f"Could not fetch profile for {user_id}: {e}")

    if "user" not in response:
        response["user"] = {}
    response["user"]["display_name"] = display_name
    response["user"]["auth_provider"] = auth_provider
    return response


async def register_user(email: str, password: str) -> Dict:
    """
    Register a new user with email and password.
    Returns user data and session on success.
    """
    try:
        client = get_auth_client()
        response = client.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Create user record in our users table
            admin = get_admin_client()
            admin.table("users").insert({
                "id": response.user.id,
                "email": email,
                "subscription_tier": "free"
            }).execute()

            result = {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "preferences_completed": False,
                },
                "session": {
                    "access_token": response.session.access_token if response.session else None,
                    "refresh_token": response.session.refresh_token if response.session else None,
                    "expires_at": response.session.expires_at if response.session else None,
                },
                "message": "Registration successful"
            }
            result = await _enrich_response_with_profile(result, result["user"]["id"])
            return result
        else:
            return {
                "success": False,
                "error": "Registration failed"
            }
            
    except Exception as e:
        return _categorize_auth_error(e, "register")


async def login_user(email: str, password: str) -> Dict:
    """
    Login user with email and password.
    Returns session tokens on success.
    """
    try:
        client = get_auth_client()
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            # Fetch preferences_completed from users table
            prefs_completed = False
            try:
                admin = get_admin_client()
                row = admin.table("users").select("preferences_completed").eq(
                    "id", response.user.id
                ).single().execute()
                if row.data:
                    prefs_completed = row.data.get("preferences_completed", False)
            except Exception as e:
                logger.warning("[auth] preferences_completed lookup failed: %s", e)
                # Default to False if lookup fails

            result = {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "preferences_completed": prefs_completed,
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                }
            }
            result = await _enrich_response_with_profile(result, result["user"]["id"])
            return result
        else:
            return {
                "success": False,
                "error": "Login failed"
            }

    except Exception as e:
        return _categorize_auth_error(e, "login")


async def refresh_session(refresh_token: str) -> Dict:
    """Refresh an expired session using refresh token."""
    try:
        client = get_auth_client()
        response = client.auth.refresh_session(refresh_token)

        if response.session:
            result = {
                "success": True,
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                }
            }
            # Include user data so frontend can update stored user
            if response.user:
                prefs_completed = False
                try:
                    admin = get_admin_client()
                    row = admin.table("users").select("preferences_completed").eq(
                        "id", response.user.id
                    ).single().execute()
                    if row.data:
                        prefs_completed = row.data.get("preferences_completed", False)
                except Exception as e:
                    logger.warning("[auth] preferences_completed lookup failed: %s", e)
                result["user"] = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "preferences_completed": prefs_completed,
                }
            return result
        else:
            return {"success": False, "error": "Failed to refresh session"}

    except Exception as e:
        return _categorize_auth_error(e, "refresh")


async def verify_token(access_token: str) -> Optional[Dict]:
    """
    Verify JWT token and return user data.
    Returns None if token is invalid or revoked.

    H4 (audit 2026-05-22): also returns `access_token` so endpoints that
    need the user-scoped Supabase client (RLS-enforced) can pass it to
    `get_user_supabase_client(token)`. Previously omitted; callers like
    auth_routes.py:752 (push_token) read `current_user.get("access_token")`
    which was always None, so the ternary always fell through to
    `get_admin_supabase_client()` — silently bypassing RLS. The .eq("id", ...)
    filter limited blast radius but the documented security model
    (dual-client / RLS-enforced for user writes) was not actually realized.

    Security note: do NOT log the full `current_user` dict at any call
    site (it now contains a secret). Existing log statements use only
    `current_user['id']` — verified safe at audit time.
    """
    try:
        # Check revocation blacklist first (fast Redis lookup). #115: the GET
        # runs on EVERY authed request BEFORE the Supabase round trip, so it is
        # dispatched off-loop under ENABLE_ASYNC_REDIS_OFFLOAD (inline when OFF).
        if await _is_token_revoked_async(access_token):
            logger.info("Token rejected: revoked via logout")
            return None

        client = get_auth_client()
        response = await run_db(lambda: client.auth.get_user(access_token))

        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "access_token": access_token,
            }
        return None

    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_user_profile(user_id: str) -> Optional[Dict]:
    """Get user profile from our users table."""
    try:
        admin = get_admin_client()
        response = admin.table("users").select("*").eq("id", user_id).single().execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return None


async def logout_user(access_token: str) -> Dict:
    """Logout user -- revoke token via Redis blacklist + Supabase sign_out."""
    try:
        # Add token to revocation blacklist (TTL = 1 hour, matching Supabase default JWT expiry)
        _revoke_token(access_token)

        client = get_auth_client()
        client.auth.sign_out()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        # Even if Supabase sign_out fails, token is blacklisted
        logger.warning(f"Supabase sign_out failed (token still revoked): {e}")
        return {"success": True, "message": "Logged out successfully"}


def _revoke_token(token: str) -> None:
    """Add token hash to Redis revocation list with 1-hour TTL."""
    try:
        from app.services.cache_service import redis_client
        if redis_client:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            redis_client.setex(f"revoked:{token_hash}", 3600, "1")
    except Exception as e:
        logger.warning(f"Failed to revoke token in Redis (non-fatal): {e}")


def _is_token_revoked(token: str) -> bool:
    """Check if token has been revoked."""
    try:
        from app.services.cache_service import redis_client
        if redis_client:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            return redis_client.get(f"revoked:{token_hash}") is not None
        return False  # Fail-open if Redis unavailable
    except Exception:
        return False  # Fail-open


async def _is_token_revoked_async(token: str) -> bool:
    """#115 — offload dispatch for the revocation GET (ENABLE_ASYNC_REDIS_OFFLOAD).

    Dispatch lives in THIS module and references the module-level
    `_is_token_revoked` in BOTH branches (the cache_service.py design note), so a
    test that patches `auth_service._is_token_revoked` intercepts both. Flag OFF
    -> the sync call runs inline to completion with no scheduler yield ->
    byte-identical to the pre-change call. Fail-open is inherited: the sync
    helper returns False on any Redis error and never raises."""
    if _redis_offload_enabled():
        return await asyncio.to_thread(_is_token_revoked, token)
    return _is_token_revoked(token)


async def sign_in_with_social(provider: str, id_token: str, nonce: str = None) -> Dict:
    """Sign in with social provider via Supabase's signInWithIdToken."""
    try:
        auth_client = get_auth_client()

        # TEMP trace (Bundle D Phase 3 device-leg): confirms token shape at
        # backend ingress so we can distinguish frontend-bug (1-segment opaque
        # token) vs Supabase-config-issue (3-segment proper JWT). Token head
        # (first 20 chars) is the unsigned header section — safe to log; full
        # token + signature never reach this line.
        logger.info(
            f"[SOCIAL_LOGIN_TRACE] provider={provider} "
            f"token_len={len(id_token)} "
            f"token_segs={id_token.count('.') + 1} "
            f"token_head={id_token[:20]} "
            f"nonce_present={nonce is not None}"
        )

        credentials = {"provider": provider, "token": id_token}
        if nonce:
            credentials["nonce"] = nonce

        response = auth_client.auth.sign_in_with_id_token(credentials)

        if not response.user:
            return {"success": False, "error": "Authentication failed"}

        # Ensure user exists in our users table
        admin = get_admin_client()
        existing = admin.table("users").select("id").eq("id", response.user.id).execute()
        if not existing.data:
            admin.table("users").insert({
                "id": response.user.id,
                "email": response.user.email,
                "auth_provider": provider,
                "subscription_tier": "free",
            }).execute()

        # Fetch preferences_completed
        prefs_completed = False
        try:
            prefs_row = admin.table("users").select("preferences_completed").eq(
                "id", response.user.id
            ).single().execute()
            if prefs_row.data:
                prefs_completed = prefs_row.data.get("preferences_completed", False)
        except Exception as e:
            logger.warning("[auth] preferences_completed lookup failed: %s", e)

        result = {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "preferences_completed": prefs_completed,
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_at": response.session.expires_at if response.session else None,
            },
            "message": f"Signed in with {provider}"
        }
        result = await _enrich_response_with_profile(result, result["user"]["id"])
        return result
    except Exception as e:
        return _categorize_auth_error(e, "social_login")


async def change_user_password(user_id: str, email: str, current_password: str, new_password: str) -> Dict:
    """Verify current password then update to new password."""
    try:
        # Verify current password by attempting login
        auth_client = get_auth_client()
        auth_client.auth.sign_in_with_password({"email": email, "password": current_password})

        # Update password via admin API
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
        return {"success": True, "message": "Password changed successfully"}
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid login credentials" in error_msg:
            return {"success": False, "error": "Current password is incorrect"}
        return _categorize_auth_error(e, "change_password")


async def update_user_email(user_id: str, current_email: str, current_password: str, new_email: str) -> Dict:
    """Update email via Supabase Admin API. Requires password verification first."""
    try:
        # Verify current password before allowing email change
        auth_client = get_auth_client()
        auth_client.auth.sign_in_with_password({"email": current_email, "password": current_password})

        # Password verified -- proceed with email update
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(user_id, {"email": new_email})
        return {"success": True, "message": "Verification email sent to new address"}
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid login credentials" in error_msg:
            return {"success": False, "error": "Current password is incorrect"}
        return _categorize_auth_error(e, "update_email")


async def update_user_profile(user_id: str, display_name: str) -> Dict:
    """Update display name in users table."""
    try:
        client = get_admin_client()
        client.table("users").update({
            "display_name": display_name
        }).eq("id", user_id).execute()
        return {"success": True, "message": "Profile updated"}
    except Exception as e:
        return _categorize_auth_error(e, "update_profile")


async def get_user_preferences(user_id: str) -> Dict:
    """Get user preferences from the users table."""
    try:
        admin = get_admin_client()
        # #115 — called on all three compare routes; route the blocking
        # .execute() through run_db (ENABLE_SYNC_DB_OFFLOAD; inline when OFF).
        response = await run_db(lambda: admin.table("users").select(
            "preferences, preferences_completed"
        ).eq("id", user_id).single().execute())
        if response.data:
            return {
                "success": True,
                "preferences": response.data.get("preferences", {}),
                "preferences_completed": response.data.get("preferences_completed", False),
            }
        return {"success": False, "error": "User not found"}
    except Exception as e:
        logger.error(f"[AUTH] get_user_preferences failed for user {user_id}: {e}")
        return {"success": False, "error": "Failed to load preferences"}


async def save_user_preferences(
    user_id: str,
    preferences: Dict,
    change_source: str = "manual_edit",
) -> Dict:
    """Save user preferences and mark preferences_completed=true.

    Uses the service-role admin client by design — `users` has RLS, and
    the same row UPDATE works under either admin or user-scoped clients,
    but admin avoids token-refresh races during onboarding (Bundle D
    Task 1.B.2 investigation 2026-05-23 — see commit message).

    After a successful UPDATE, fire-and-forget a snapshot into
    user_preference_history (Migration 029, Bundle B B.1) so the eval loop
    can correlate preference changes with verdict quality over time.
    `change_source` identifies which path produced the change (PUT
    /preferences edit -> 'manual_edit'; cohort modal seed ->
    'cohort_default'). The history write is non-blocking and fail-soft:
    a failure there never affects the preferences save itself, and it only
    fires on the success path so a failed UPDATE leaves no phantom snapshot.
    """
    try:
        admin = get_admin_client()
        admin.table("users").update({
            "preferences": preferences,
            "preferences_completed": True,
        }).eq("id", user_id).execute()
        fire_and_forget(
            record_preference_history(user_id, preferences, change_source),
            "record_preference_history",
        )
        return {"success": True, "message": "Preferences saved"}
    except Exception as e:
        # Bundle D Task 1.B.2 — log exception class + repr so Sentry shows
        # the actual cause (DB CHECK rejection vs network vs RLS) instead
        # of just str(e) which can collapse to a generic message.
        logger.error(
            "[AUTH] save_user_preferences failed for user %s: %s: %r",
            user_id,
            type(e).__name__,
            e,
        )
        return {"success": False, "error": "Failed to save preferences"}


async def delete_user_account(user_id: str) -> bool:
    """Delete user account and all associated data."""
    from app.services.database_service import delete_user_data_cascade
    # First delete all user data
    await delete_user_data_cascade(user_id)
    # Then delete the auth user via admin client
    admin = get_admin_client()
    admin.auth.admin.delete_user(user_id)
    return True


async def resend_verification_email(email: str) -> bool:
    """Resend email verification link."""
    client = get_auth_client()
    client.auth.resend({"type": "signup", "email": email})
    return True


async def request_password_reset(email: str) -> Dict:
    """Send password reset email."""
    try:
        client = get_auth_client()
        client.auth.reset_password_email(email)
        return {
            "success": True,
            "message": "Password reset email sent"
        }
    except Exception as e:
        return _categorize_auth_error(e, "password_reset")


# ============================================
# Brute-Force Lockout
# ============================================

def _login_attempt_key(email: str) -> str:
    """Hash email for Redis key to avoid storing PII in cache."""
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:16]
    return f"failed_login:{email_hash}"


async def check_account_locked(email: str) -> dict:
    """Check if account is locked due to too many failed login attempts.

    Returns: {"locked": bool, "retry_after": int (seconds) or 0}
    Fails open if Redis unavailable (does not block users).
    """
    if not redis_client:
        return {"locked": False, "retry_after": 0}
    try:
        key = _login_attempt_key(email)
        attempts = redis_client.get(key)
        if attempts and int(attempts) >= LOCKOUT_THRESHOLD:
            ttl = redis_client.ttl(key)
            return {"locked": True, "retry_after": max(ttl, 0)}
        return {"locked": False, "retry_after": 0}
    except Exception:
        return {"locked": False, "retry_after": 0}


async def track_failed_login(email: str) -> dict:
    """Increment failed login counter. Returns lockout status.

    Returns: {"locked": bool, "attempts": int}
    """
    if not redis_client:
        return {"locked": False, "attempts": 0}
    try:
        key = _login_attempt_key(email)
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, LOCKOUT_WINDOW_SECONDS)
        return {"locked": count >= LOCKOUT_THRESHOLD, "attempts": count}
    except Exception:
        return {"locked": False, "attempts": 0}


async def clear_failed_logins(email: str) -> None:
    """Reset failed login counter after successful login."""
    if not redis_client:
        return
    try:
        redis_client.delete(_login_attempt_key(email))
    except Exception:
        pass
