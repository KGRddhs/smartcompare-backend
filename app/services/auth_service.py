"""
Auth Service - Supabase Authentication
"""
import os
from typing import Optional, Dict
from supabase import create_client, Client

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
            
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                },
                "session": {
                    "access_token": response.session.access_token if response.session else None,
                    "refresh_token": response.session.refresh_token if response.session else None,
                    "expires_at": response.session.expires_at if response.session else None,
                },
                "message": "Registration successful"
            }
        else:
            return {
                "success": False,
                "error": "Registration failed"
            }
            
    except Exception as e:
        error_message = str(e)
        if "User already registered" in error_message:
            return {"success": False, "error": "Email already registered"}
        if "Password should be at least" in error_message:
            return {"success": False, "error": "Password must be at least 6 characters"}
        return {"success": False, "error": error_message}


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
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                }
            }
        else:
            return {
                "success": False,
                "error": "Login failed"
            }
            
    except Exception as e:
        error_message = str(e)
        if "Invalid login credentials" in error_message:
            return {"success": False, "error": "Invalid email or password"}
        return {"success": False, "error": error_message}


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
                result["user"] = {
                    "id": response.user.id,
                    "email": response.user.email,
                }
            return result
        else:
            return {"success": False, "error": "Failed to refresh session"}

    except Exception as e:
        return {"success": False, "error": str(e)}


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
        print(f"Token verification failed: {e}")
        return None


async def get_user_profile(user_id: str) -> Optional[Dict]:
    """Get user profile from our users table."""
    try:
        admin = get_admin_client()
        response = admin.table("users").select("*").eq("id", user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error getting user profile: {e}")
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

        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_at": response.session.expires_at if response.session else None,
            },
            "message": f"Signed in with {provider}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return {"success": False, "error": "Current password is incorrect"}
        return {"success": False, "error": error_msg}


async def update_user_email(user_id: str, new_email: str) -> Dict:
    """Update email via Supabase Admin API (sends verification to new email)."""
    try:
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(user_id, {"email": new_email})
        return {"success": True, "message": "Verification email sent to new address"}
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            return {"success": False, "error": "Email already in use"}
        return {"success": False, "error": error_msg}


async def update_user_profile(user_id: str, display_name: str) -> Dict:
    """Update display name in users table."""
    try:
        client = get_admin_client()
        client.table("users").update({
            "display_name": display_name
        }).eq("id", user_id).execute()
        return {"success": True, "message": "Profile updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
        return {"success": False, "error": str(e)}
