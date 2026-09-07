"""
Auth Service - Supabase Authentication

W0-2 (LS-REQUEST-PATH-BLOCKING-02 / -04, CR-PERFORMANCE-03) --
ENABLE_SUPABASE_CLIENT_REUSE builds every Supabase client in this module on the
ONE shared httpx transport owned by `database_service` (that module owns the
transport, the flag helper and the ClientOptions builder, so both service
modules use the SAME SSLContext and connection pool).

Only the SERVICE-ROLE client is memoised. The ANON client is rebuilt on EVERY
call, deliberately -- see `get_auth_client` for why (Fable MUST-FIX ruling
2026-09-07: a memoised anon client takes on the last signed-in user's identity).
"""
import asyncio
import hashlib
import logging
import os
import threading
from typing import Optional, Dict, Tuple
from supabase import create_client, Client

from app.services.cache_service import redis_client, _redis_offload_enabled
from app.services.database_service import (
    record_preference_history,
    build_supabase_client_options,
    supabase_client_reuse_enabled,
)
from app.utils.async_utils import fire_and_forget
from app.utils.db_offload import run_db  # M13-05 ENABLE_SYNC_DB_OFFLOAD

logger = logging.getLogger(__name__)

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


# --- W0-2: ENABLE_SUPABASE_CLIENT_REUSE client memo ------------------------
# Neither client below was memoised, so EVERY authed request paid a fresh
# `create_client` (~215 ms of blocking TLS setup) ON the event loop -- in
# `verify_token` the construction sits outside `run_db`, so it blocks the loop
# even with ENABLE_SYNC_DB_OFFLOAD on.
#
# This memo holds ONLY the SERVICE-ROLE client (`get_admin_client`). It stays
# keyed by (url, key) so a key rotation cannot serve a stale client and so an
# anon key can never land here by accident. `get_auth_client` deliberately does
# NOT use it: the shared transport already removes ~100% of the construction
# cost (216.62 ms -> 0.12 ms measured, .qa-w0/_rv_probe_cost.py), so memoising
# the anon client buys nothing and costs cross-user auth-state safety.
_CLIENT_MEMO: Dict[Tuple[str, str], Client] = {}
_CLIENT_MEMO_LOCK = threading.Lock()


def _build_client(url: str, key: str) -> Client:
    """Construct ONE Supabase client on the shared transport (flag ON only).

    `build_supabase_client_options()` returns None when the shared transport
    could not be built (fail-open, see `database_service.get_shared_httpx_client`);
    this then degrades to today's bare `create_client(url, key)` instead of
    letting an httpx/h2 environment failure escape into the request path.
    """
    options = build_supabase_client_options()
    if options is not None:
        return create_client(url, key, options=options)
    return create_client(url, key)


def _memoised_client(url: str, key: str) -> Client:
    """Return the process-wide SERVICE-ROLE client for (url, key), building it
    once on the shared transport. Double-checked under a lock so concurrent
    `run_db` threads cannot build two.

    Safe for the service-role key ONLY: the only calls ever made on those
    clients are `auth.admin.*` (GoTrueAdminAPI), which take their token as an
    argument and never store a session or emit SIGNED_IN / TOKEN_REFRESHED, so
    the client's identity cannot be re-pointed by one caller and then read by
    the next. See `get_auth_client` for the anon-client hazard.
    """
    memo_key = (url, key)
    client = _CLIENT_MEMO.get(memo_key)
    if client is not None:
        return client
    with _CLIENT_MEMO_LOCK:
        client = _CLIENT_MEMO.get(memo_key)
        if client is None:
            client = _build_client(url, key)
            _CLIENT_MEMO[memo_key] = client
    return client


def _reset_client_cache_for_tests() -> None:
    """Drop the memoised clients. Test-only hook (W0-2); never called from
    production code. The shared transport is owned by `database_service` and is
    dropped by its own hook of the same name."""
    with _CLIENT_MEMO_LOCK:
        _CLIENT_MEMO.clear()


def get_auth_client() -> Client:
    """Get Supabase client for auth operations (uses anon key).

    W0-2: under ENABLE_SUPABASE_CLIENT_REUSE (read per call) this returns a
    FRESH client on EVERY call, built on the shared httpx transport. It is
    NEVER memoised -- that is the binding Fable ruling of 2026-09-07, and this
    is why.

    Nine of this module's ten call sites are auth-STATE operations, not token
    checks: `sign_up`, `sign_in_with_password` (login, plus the password checks
    behind a password change and an email change), `refresh_session`,
    `sign_out`, `sign_in_with_id_token`, `resend`, `reset_password_email`.
    supabase-py stamps the signed-in user's identity onto the CLIENT OBJECT on
    each of those:

      * `supabase_auth/_sync/gotrue_client.py:342-343` (pinned 2.31.0 wheel;
        :341-342 on the installed 2.28.0) -- a successful sign-in does
        `_save_session(session)` then `_notify_all_subscribers("SIGNED_IN", ...)`;
      * `supabase/_sync/client.py:99` registers `Client._listen_to_auth_events`
        as that subscriber, and `:334-346` resets `_postgrest` / `_storage` and
        writes `self.options.headers["Authorization"] = Bearer <that user JWT>`.

    So on a process-wide client the LAST sign-in becomes the client's identity.
    `sign_out()` takes no caller token at all (`gotrue_client.py:779-798`
    pinned, :778-797 installed): it reads the session off the client's OWN
    storage and calls `admin.sign_out(access_token, scope="global")`. On a
    shared client one user's logout would therefore GLOBALLY revoke whoever
    signed in last, across all their devices, while leaving the actual caller's
    upstream session alive -- and any postgrest call made through that client
    would run as that other user.

    The memo would buy nothing anyway: on the shared transport a fresh client
    costs ~0.12 ms against ~216 ms today (.qa-w0/_rv_probe_cost.py, n=20), i.e.
    the whole CR-PERFORMANCE-03 win comes from `ClientOptions(httpx_client=)`,
    not from caching the object.

    `verify_token` is the one call site that passes the token explicitly
    (`client.auth.get_user(access_token)`) and would have been safe either way.
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    if supabase_client_reuse_enabled():
        return _build_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_admin_client() -> Client:
    """Get Supabase client with service role (admin operations).

    W0-2: memoised under ENABLE_SUPABASE_CLIENT_REUSE (read per call). Safe to
    memoise, unlike the anon client above: the only calls ever made on it are
    `auth.admin.*` (GoTrueAdminAPI), which take their token as an argument and
    never store a session or emit SIGNED_IN, so this client's identity is
    always the service-role key.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    if supabase_client_reuse_enabled():
        return _memoised_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
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
        # W1-4 (LS-CACHE-REDIS-03 / MB-NETWORK-CONTRACT-02) -- purely ADDITIVE
        # machine-readable marker for the TRANSIENT class. `/auth/refresh` maps
        # THIS code, and only this code, to 503; every other failure stays 401.
        # Without it the route cannot tell a Supabase blip from a genuinely
        # invalid token, so one blip 401s every user holding an expiring token
        # straight into the mobile forced-logout listener. Every other caller
        # ignores unknown keys, and no other branch's shape or message moves.
        return {
            "success": False,
            "error": "Connection failed. Please try again.",
            "code": "UPSTREAM_UNAVAILABLE",
        }
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


def logout_upstream_revocation_enabled() -> bool:
    """W1-4 -- True iff logout actually revokes the session UPSTREAM (default OFF).

    Read PER CALL from `os.getenv` (the `price_service.exact_gate_enabled`
    idiom) so Railway can flip it without a restart; never cached at import.

    Flag OFF, or no refresh token supplied, is today's exact path: the access
    token is blacklisted in Redis for 1 h and a bare `sign_out()` is made on a
    freshly built anon client that holds NO session, which gotrue turns into a
    silent no-op. The flag exists because sending the refresh token in the
    logout body is a CLIENT change that reaches devices only with the next OTA,
    so flag ON is INERT until then.
    """
    return os.getenv("ENABLE_LOGOUT_UPSTREAM_REVOCATION", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


async def logout_user(access_token: str, refresh_token: Optional[str] = None) -> Dict:
    """Logout user -- revoke token via Redis blacklist + Supabase sign_out.

    W1-4 (LS-CACHE-REDIS-03). `sign_out` reads the session off the CLIENT's own
    storage (`supabase_auth/_sync/gotrue_client.py`: `session = self.get_session()`
    then `if access_token: self.admin.sign_out(access_token, scope)`), and this
    client is built fresh per call and holds nothing -- so today's bare call
    revokes NOTHING and the refresh token outlives the 1 h blacklist upstream.

    Under `ENABLE_LOGOUT_UPSTREAM_REVOCATION`, and only when the caller supplied
    a refresh token, we `set_session(access, refresh)` first so gotrue has a
    session to end, then `sign_out({"scope": "local"})`.

    Two pinned SDK facts (supabase / supabase-auth 2.31.0):

    * The options DICT is mandatory. The real signature is
      `sign_out(self, options: Optional[SignOutOptions] = None)`, so
      `sign_out(scope="local")` raises `TypeError` -- which the broad except
      below would swallow while still reporting success, i.e. a silent no-op
      that LOOKS fixed. And the body does `options or {"scope": "global"}`, so
      passing nothing signs the user out on EVERY device. `local` revokes
      exactly the session just ended, which is what the finding asks for;
      "sign out everywhere" is a separate product feature.
    * `set_session` has real side effects. It decodes the access token
      (`access_token.split(".")[1]` -> `decode_jwt`), so a non-JWT string
      RAISES; and on an ALREADY-EXPIRED access token it calls
      `_refresh_access_token(refresh_token)`, which ROTATES the refresh token
      (otherwise it makes a `get_user` round trip). So logout now makes ONE
      upstream call it never made before, and on the expired path revocation
      happens via that rotation plus the `sign_out` on the NEW session rather
      than `sign_out` on the old one. The old refresh token is dead either way.

    The catch stays broad and the response stays `{"success": True}` -- the
    local blacklist has been written and the client ignores this response
    anyway -- but a failure is logged at WARNING and never implies that
    upstream revocation happened.
    """
    upstream_revocation = bool(refresh_token) and logout_upstream_revocation_enabled()
    try:
        # Add token to revocation blacklist (TTL = 1 hour, matching Supabase default JWT expiry)
        _revoke_token(access_token)

        client = get_auth_client()
        if upstream_revocation:
            client.auth.set_session(access_token, refresh_token)
            client.auth.sign_out({"scope": "local"})
        else:
            client.auth.sign_out()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        # The access token IS blacklisted locally (that write precedes this
        # call and has its own guard); what failed is the UPSTREAM leg, so the
        # refresh token was NOT revoked at Supabase. Never let a
        # TypeError-shaped mistake pass silently as success again.
        logger.warning(
            "[auth] logout upstream leg failed (%s): %s: %s -- access token is "
            "blacklisted locally for 1 h, but the session was NOT revoked upstream",
            "set_session+sign_out(local)" if upstream_revocation else "sign_out",
            type(e).__name__,
            e,
        )
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
