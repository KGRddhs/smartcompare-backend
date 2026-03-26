"""
Auth Service - Supabase Authentication
"""
import logging
import os
from typing import Optional, Dict
from supabase import create_client, Client

logger = logging.getLogger(__name__)

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
            except Exception:
                pass  # Default to False if lookup fails

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
                except Exception:
                    pass
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
    Returns None if token is invalid.
    """
    try:
        client = get_auth_client()
        response = client.auth.get_user(access_token)
        
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
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
    """Logout user and invalidate session."""
    try:
        client = get_auth_client()
        client.auth.sign_out()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def sign_in_with_social(provider: str, id_token: str, nonce: str = None) -> Dict:
    """Sign in with social provider via Supabase's signInWithIdToken."""
    try:
        auth_client = get_auth_client()

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
        except Exception:
            pass

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


async def update_user_email(user_id: str, new_email: str) -> Dict:
    """Update email via Supabase Admin API (sends verification to new email)."""
    try:
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(user_id, {"email": new_email})
        return {"success": True, "message": "Verification email sent to new address"}
    except Exception as e:
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
        response = admin.table("users").select(
            "preferences, preferences_completed"
        ).eq("id", user_id).single().execute()
        if response.data:
            return {
                "success": True,
                "preferences": response.data.get("preferences", {}),
                "preferences_completed": response.data.get("preferences_completed", False),
            }
        return {"success": False, "error": "User not found"}
    except Exception as e:
        logger.error(f"[AUTH] get_user_preferences failed for user {user_id}: {e}")
        return {"success": False, "error": str(e)}


async def save_user_preferences(user_id: str, preferences: Dict) -> Dict:
    """Save user preferences and mark preferences_completed=true."""
    try:
        admin = get_admin_client()
        admin.table("users").update({
            "preferences": preferences,
            "preferences_completed": True,
        }).eq("id", user_id).execute()
        return {"success": True, "message": "Preferences saved"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
