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
import base64
import hashlib
import json
import logging
import os
import threading
from typing import Optional, Dict, Tuple
import httpx
from supabase import create_client, Client, ClientOptions
from supabase_auth.errors import AuthApiError, AuthRetryableError, AuthUnknownError

from app.services.cache_service import redis_client, _redis_offload_enabled
from app.services.consent_service import (
    TERMS_ACCEPTANCE_REQUIRED,
    TERMS_ACCEPTANCE_REQUIRED_MESSAGE,
    consent_columns,
    consent_required_enabled,
)
from app.services.database_service import (
    record_preference_history,
    build_supabase_client_options,
    get_shared_httpx_client,
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

    W1-4c (R-AUTH retro, UNFLAGGED -- a server-side client that auto-refreshes
    is a defect with no legitimate reader): on BOTH branches the anon client is
    built with `auto_refresh_token=False, persist_session=False`. The SDK
    default (True) makes every `_save_session` (login, refresh, set_session)
    arm a daemon `threading.Timer` for `expires_in - 10 s` on this throw-away
    client; when it fires it spends the refresh token that was just handed to
    the DEVICE and re-arms forever (measured: the server posted the device's
    token upstream unprompted). With `persist_session=False` the session lives
    in `_in_memory_session`, which `get_session()` / `sign_out()` still read,
    so the flag-ON logout's set_session + sign_out path keeps working.

    The options are built HERE, with the constructor, not via the shared
    `build_supabase_client_options()` (database_service's admin and
    user-scoped clients use it and are out of this ruling), and never via
    `ClientOptions.replace(...)`: its body is `auto_refresh_token or
    self.auto_refresh_token`, so `False` cannot be set that way (measured).
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    if supabase_client_reuse_enabled():
        # Same fail-open as `_build_client`: no shared transport -> the SDK's
        # own per-client transport, never no client at all.
        return create_client(
            SUPABASE_URL, SUPABASE_ANON_KEY,
            options=_anon_client_options(get_shared_httpx_client()),
        )
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=_anon_client_options(None))


def _anon_client_options(httpx_client: Optional[httpx.Client]) -> ClientOptions:
    """W1-4c -- a FRESH options object per anon client (fresh `storage`, see
    `database_service.build_supabase_client_options` for why sharing one is a
    cross-user bleed) that never auto-refreshes and never persists a session."""
    if httpx_client is None:
        return ClientOptions(auto_refresh_token=False, persist_session=False)
    return ClientOptions(
        httpx_client=httpx_client, auto_refresh_token=False, persist_session=False,
    )


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


# The TRANSIENT upstream class, by exception text (W1-4). Shared with the W3-6
# recovery path so both routes draw the "blip vs verdict" line in one place.
_TRANSIENT_AUTH_ERROR_TERMS = (
    "network", "connection", "timeout", "dns", "econnrefused",
    "socket hang up", "enotfound", "failed to fetch", "no network"
)


def _upstream_unavailable_result() -> Dict:
    return {
        "success": False,
        "error": "Connection failed. Please try again.",
        "code": "UPSTREAM_UNAVAILABLE",
    }


# #198 -- the EXPECTED CLIENT class, by exception text, for exceptions that
# carry no `.status` (complete_password_recovery re-wraps as Exception(str(e))).
# Lower-case fragments of the gotrue wordings measured on the pinned
# supabase-auth 2.31.0 (str(e) is the message only, never the code). The three
# early-return wordings of `_categorize_auth_error` ("invalid login
# credentials", "user already registered", "email not confirmed") are omitted:
# they return before the generic branch. Every entry is pinned by a row in
# tests/test_auth_error_log_hygiene.py.
_EXPECTED_CLIENT_AUTH_ERROR_TERMS = (
    "invalid refresh token", "refresh token not found", "already used",
    "invalid jwt", "token is expired", "invalid token", "user not found",
    "already been registered", "new password should be different",
    "password should be at least",
)

# #198 R11 -- a 4xx that signals a SERVER-SIDE credential or configuration
# failure is an application error, not a client verdict: it stays ERROR (a
# Sentry event). Lower-case fragments: Kong's 401 "Invalid API key" / "No API
# key found in request" (a wrong or missing Supabase key), gotrue's 403
# not_admin "User not allowed", and gotrue config states ("Signups not allowed
# for this instance", "Email logins are disabled", "... is disabled"). Every
# entry is pinned by a row in tests/test_auth_error_log_hygiene.py.
_SERVER_SIDE_AUTH_ERROR_TERMS = (
    "invalid api key", "no api key found", "not allowed", "not_admin",
    "is disabled", "are disabled",
)


def _is_expected_client_auth_error(e: Exception) -> bool:
    """#198 -- a client verdict (bad/expired token, bad input), not an app error.

    R11 carve-out FIRST: AuthSessionMissingError (our code called the SDK
    without a session) and any server-side credential/config wording above
    are never a client verdict, whatever the status. Then an int `.status`
    (gotrue's AuthApiError / CustomAuthError) decides alone: 4xx except 429
    (429 and 5xx stay the transient/error class). Only an exception without
    one falls back to the expected-client message fragments.
    """
    error_msg = str(e).lower()
    if type(e).__name__ == "AuthSessionMissingError":
        return False
    if any(term in error_msg for term in _SERVER_SIDE_AUTH_ERROR_TERMS):
        return False
    status = getattr(e, "status", None)
    if isinstance(status, int) and not isinstance(status, bool):
        return 400 <= status < 500 and status != 429
    return any(term in error_msg for term in _EXPECTED_CLIENT_AUTH_ERROR_TERMS)


def _categorize_auth_error(e: Exception, context: str = "operation") -> Dict:
    """Categorize auth errors into user-friendly messages."""
    error_msg = str(e).lower()
    if "invalid login credentials" in error_msg:
        return {"success": False, "error": "Invalid email or password"}
    elif "user already registered" in error_msg:
        return {"success": False, "error": "An account with this email already exists"}
    elif "email not confirmed" in error_msg:
        return {"success": False, "error": "Please verify your email before logging in"}
    elif any(term in error_msg for term in _TRANSIENT_AUTH_ERROR_TERMS):
        # W1-4 (LS-CACHE-REDIS-03 / MB-NETWORK-CONTRACT-02) -- purely ADDITIVE
        # machine-readable marker for the TRANSIENT class. `/auth/refresh` maps
        # THIS code, and only this code, to 503; every other failure stays 401.
        # Without it the route cannot tell a Supabase blip from a genuinely
        # invalid token, so one blip 401s every user holding an expiring token
        # straight into the mobile forced-logout listener. Every other caller
        # ignores unknown keys, and no other branch's shape or message moves.
        return _upstream_unavailable_result()
    else:
        # #198 -- exception TYPE only, never str(e) (an auth SDK exception can
        # carry a credential), no exc_info. An expected client failure is a
        # WARNING (a Sentry breadcrumb), anything else an ERROR (an event).
        # R12: PRE-FORMATTED, no record args, so Sentry's logentry.message
        # differs per (context, type) and each pair groups as its own issue.
        if _is_expected_client_auth_error(e):
            logger.warning(
                "[auth] " + context + " rejected upstream: " + type(e).__name__
                + " status=" + str(getattr(e, "status", None))
            )
        else:
            logger.error("Auth error in " + context + ": " + type(e).__name__)
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


def _is_transient_upstream_status(status: object) -> bool:
    """429 (gotrue's per-IP rate limit -- shared by the whole fleet, since every
    refresh leaves from the Railway IP) or any 5xx."""
    return isinstance(status, int) and not isinstance(status, bool) and (
        status == 429 or status >= 500
    )


def _is_transient_refresh_error(e: BaseException) -> bool:
    """W1-4b (R-AUTH retro, UNFLAGGED) -- classify a refresh failure by its TYPE.

    `_categorize_auth_error` matches substrings of `str(e)`, and the real SDK
    outage shapes mostly miss them (measured against a loopback gotrue on the
    pinned supabase_auth 2.31.0 / httpx 0.28.1: 429, 500, 502, 503, 520, 522,
    544, a dropped socket and a real ~5 s hang -- `ReadTimeout('timed out')`
    has no 'timeout' in it -- all came out 401, i.e. a forced logout on both
    client builds). The transient class is:

    * `AuthRetryableError` -- the SDK's own type for 502/503/504/520-524/530
      and for a `RuntimeError` in the transport;
    * `httpx.TransportError` -- every timeout / connect / read / protocol
      error; they escape `gotrue_base_api._request` UNWRAPPED (it only catches
      `HTTPStatusError` and `RuntimeError`);
    * `AuthApiError` with `.status` 429 or >= 500 (a JSON error body);
    * `AuthUnknownError` built from a 429 / 5xx whose body is not JSON (a
      gateway / Cloudflare HTML page). MEASURED: its `.original_error` is the
      `JSONDecodeError` from `response.json()`, not the `HTTPStatusError`; the
      status error is the implicit `__context__` (`raise handle_exception(e)`
      inside `except HTTPStatusError`), so both are inspected.

    Everything else -- 400 refresh_token_not_found / already_used, 401, 403,
    404 session_not_found, 422, a 400 HTML page, missing config, any non-SDK
    exception -- is NOT transient and keeps today's path (the substring
    categoriser, then 401).
    """
    if isinstance(e, (AuthRetryableError, httpx.TransportError)):
        return True
    if isinstance(e, AuthApiError):
        return _is_transient_upstream_status(getattr(e, "status", None))
    if isinstance(e, AuthUnknownError):
        for inner in (getattr(e, "original_error", None), e.__context__):
            if isinstance(inner, httpx.HTTPStatusError):
                return _is_transient_upstream_status(inner.response.status_code)
    return False


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


async def register_user(email: str, password: str, *, consent: Optional[Dict] = None) -> Dict:
    """
    Register a new user with email and password.
    Returns user data and session on success.

    W3-16: ``consent`` (from ``consent_service.consent_from_fields``) is written
    into the users row only when ENABLE_CONSENT_PERSIST is on; flag OFF keeps the
    insert dict byte-identical.
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
                "subscription_tier": "free",
                **consent_columns(consent),
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
        # W1-4b: the TYPE decides first. The result dict is byte-identical to
        # the substring branch's transient dict, so `/auth/refresh` maps it to
        # 503 REFRESH_UPSTREAM_UNAVAILABLE exactly as before; every other shape
        # falls through to today's categoriser unchanged. Scoped to THIS
        # caller only -- login/register/password-reset/social keep their dicts.
        if _is_transient_refresh_error(e):
            logger.warning(
                "[auth] refresh upstream unavailable (transient): %s", type(e).__name__
            )
            return {
                "success": False,
                "error": "Connection failed. Please try again.",
                "code": "UPSTREAM_UNAVAILABLE",
            }
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

    Flag OFF is today's exact path: the access token is blacklisted in Redis
    for 1 h and a bare `sign_out()` is made on a freshly built anon client that
    holds NO session, which gotrue turns into a silent no-op.

    Flag ON (R-AUTH retro, Fable red-gate ruling 1): a VALID bearer is revoked
    upstream by the ACCESS token -- `admin.sign_out(access_token, "local")` --
    whether or not the body carried a refresh token, so the flag acts for every
    installed build, not only after the OTA (the refresh-token VALUE never
    reached Supabase on this path anyway: gotrue revokes by the JWT's session).
    An EXPIRED bearer plus a refresh token takes the rotation path (ruling 2,
    see `logout_user`).
    """
    return os.getenv("ENABLE_LOGOUT_UPSTREAM_REVOCATION", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


async def logout_user(
    access_token: str,
    refresh_token: Optional[str] = None,
    access_token_expired: bool = False,
) -> Dict:
    """Logout user -- revoke token via Redis blacklist + Supabase sign_out.

    W1-4 (LS-CACHE-REDIS-03). `sign_out` reads the session off the CLIENT's own
    storage (`supabase_auth/_sync/gotrue_client.py`: `session = self.get_session()`
    then `if access_token: self.admin.sign_out(access_token, scope)`), and this
    client is built fresh per call and holds nothing -- so today's bare call
    revokes NOTHING and the refresh token outlives the 1 h blacklist upstream.

    Under `ENABLE_LOGOUT_UPSTREAM_REVOCATION` (R-AUTH retro, Fable red-gate
    rulings 1 and 2 -- they replace PR #139's set_session-then-sign_out for the
    valid-bearer case):

    * VALID bearer (the route's normal path): `auth.admin.sign_out(access_token,
      "local")` -- the exact call the SDK's own `sign_out` makes once a session
      is stored -- with or without a refresh token. No `set_session`, no
      `GET /user`, and the refresh-token VALUE is never sent upstream.
    * EXPIRED bearer + refresh token (`access_token_expired=True`, reached only
      through the route's expired-bearer branch): `set_session(access, refresh)`
      -- whose expired branch ROTATES the pair upstream (POST /token) -- then
      `sign_out({"scope": "local"})` on the new session. A pair gotrue rejects
      still returns success (the local blacklist is written) and logs ONE
      WARNING carrying the exception TYPE only.

    Both upstream legs run OFF the event loop (`asyncio.to_thread`: the path is
    already gated by this flag, so the offload does not also wait on
    ENABLE_SYNC_DB_OFFLOAD). Flag OFF keeps today's inline bare `sign_out()`.

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
    upstream_revocation = logout_upstream_revocation_enabled()
    expired_rotation = upstream_revocation and access_token_expired and bool(refresh_token)
    try:
        # Add token to revocation blacklist (TTL = 1 hour, matching Supabase default JWT expiry)
        _revoke_token(access_token)

        if expired_rotation:
            await asyncio.to_thread(_sign_out_expired_pair, access_token, refresh_token)
        elif upstream_revocation:
            await asyncio.to_thread(_sign_out_by_access_token, access_token)
        else:
            client = get_auth_client()
            client.auth.sign_out()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        if expired_rotation:
            # TYPE only: this leg handles an expired JWT AND a live refresh
            # token, and a rejected pair's message is not worth a credential.
            logger.warning(
                "[auth] logout upstream leg failed (set_session+sign_out(local), "
                "expired access token): %s -- access token is blacklisted locally "
                "for 1 h, but the session was NOT revoked upstream",
                type(e).__name__,
            )
            return {"success": True, "message": "Logged out successfully"}
        # The access token IS blacklisted locally (that write precedes this
        # call and has its own guard); what failed is the UPSTREAM leg, so the
        # refresh token was NOT revoked at Supabase. Never let a
        # TypeError-shaped mistake pass silently as success again.
        # SCRUB THE MESSAGE. `set_session` can raise
        # `UserDoesntExist(access_token)` (supabase_auth `_sync/gotrue_client.py`:
        # `user_response = self.get_user(access_token)` -> `if user_response is
        # None: raise UserDoesntExist(access_token)`), and that exception's
        # `str()` IS THE BEARER TOKEN -- measured, not assumed. Interpolating the
        # exception raw would write a live credential into the logs, and from
        # there into Sentry: exactly the class of defect this wave exists to
        # close. Only the upstream leg can carry one, so redact both tokens by
        # value before formatting.
        detail = str(e)
        for secret, label in ((access_token, "<access_token>"),
                              (refresh_token, "<refresh_token>")):
            if secret:
                detail = detail.replace(secret, label)
        logger.warning(
            "[auth] logout upstream leg failed (%s): %s: %s -- access token is "
            "blacklisted locally for 1 h, but the session was NOT revoked upstream",
            "admin.sign_out(local)" if upstream_revocation else "sign_out",
            type(e).__name__,
            detail,
        )
        return {"success": True, "message": "Logged out successfully"}


def _sign_out_by_access_token(access_token: str) -> None:
    """Flag-ON VALID-bearer upstream leg (runs in a worker thread): revoke the
    caller's session -- and only that one, `scope="local"` -- by its JWT.
    POST /auth/v1/logout?scope=local with `Authorization: Bearer <access>`."""
    get_auth_client().auth.admin.sign_out(access_token, "local")


def _sign_out_expired_pair(access_token: str, refresh_token: str) -> None:
    """Flag-ON EXPIRED-bearer upstream leg (runs in a worker thread). On an
    expired access token `set_session` calls `_refresh_access_token`, which
    rotates the pair upstream (the presented refresh token dies there); the
    `sign_out` then ends the NEW session with `scope="local"`. The client never
    auto-refreshes and keeps the session in memory only (W1-4c)."""
    client = get_auth_client()
    client.auth.set_session(access_token, refresh_token)
    client.auth.sign_out({"scope": "local"})


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


async def sign_in_with_social(
    provider: str, id_token: str, nonce: str = None, *, consent: Optional[Dict] = None
) -> Dict:
    """Sign in with social provider via Supabase's signInWithIdToken.

    W3-16: a NEW account (no users row yet) with ENABLE_CONSENT_REQUIRED on and
    no ``consent`` is refused before our row is written. Existing accounts are
    never gated.
    """
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
            if consent is None and consent_required_enabled():
                return {
                    "success": False,
                    "code": TERMS_ACCEPTANCE_REQUIRED,
                    "error": TERMS_ACCEPTANCE_REQUIRED_MESSAGE,
                }
            admin.table("users").insert({
                "id": response.user.id,
                "email": response.user.email,
                "auth_provider": provider,
                "subscription_tier": "free",
                **consent_columns(consent),
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


def password_reset_deep_link_enabled() -> bool:
    """W3-6 -- True iff the reset email is told to return to the app (default OFF).

    Read PER CALL (the `logout_upstream_revocation_enabled` idiom) so Railway can
    flip it without a restart. It ships dark because GoTrue honours `redirect_to`
    only when the value is on the Supabase project's Redirect-URL allow-list (a
    dashboard step); off the list it silently falls back to the Site URL.
    """
    return os.getenv("ENABLE_PASSWORD_RESET_DEEP_LINK", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def password_reset_redirect_url() -> str:
    """W3-6 -- where the recovery link sends the user (read per call)."""
    return os.getenv("PASSWORD_RESET_REDIRECT_URL", "qaren://reset-password").strip() or (
        "qaren://reset-password"
    )


async def request_password_reset(email: str) -> Dict:
    """Send password reset email.

    W3-6: under `ENABLE_PASSWORD_RESET_DEEP_LINK` the SDK's `options` dict
    (`reset_password_email(email, options=None)` on supabase-auth 2.28.0) carries
    `redirect_to`, which becomes the `?redirect_to=` query param of
    `POST /auth/v1/recover`. Flag OFF is today's exact one-positional call.
    """
    try:
        client = get_auth_client()
        if password_reset_deep_link_enabled():
            client.auth.reset_password_email(
                email, {"redirect_to": password_reset_redirect_url()}
            )
        else:
            client.auth.reset_password_email(email)
        return {
            "success": True,
            "message": "Password reset email sent"
        }
    except Exception as e:
        return _categorize_auth_error(e, "password_reset")


def _recovery_token_invalid() -> Dict:
    return {
        "success": False,
        "code": "RECOVERY_TOKEN_INVALID",
        "error": "This reset link is no longer valid.",
    }


def _recovery_amr_methods(access_token: str) -> Optional[list]:
    """The `amr` method names in the token payload, or None if undecodable.

    NOT a verification: the signature and expiry were already checked upstream
    by `get_user`. GoTrue strips the base64 `=` padding, so it is restored here.
    """
    try:
        seg = access_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))
        return [str(m.get("method")) for m in claims.get("amr", []) if isinstance(m, dict)]
    except Exception:
        return None


def _is_upstream_unavailable(e: Exception, scrubbed_text: str) -> bool:
    """W3-6 -- True iff a `get_user` failure is a TRANSPORT/upstream blip, not a
    verdict on the token.

    Measured on the pinned supabase-auth 2.31.0: a connect/DNS/read-timeout
    failure escapes `get_user` as the raw `httpx.TransportError` (whose text,
    e.g. "[Errno 11001] getaddrinfo failed", the W1-4 term list misses), and a
    GoTrue 5xx arrives as `AuthRetryableError`; an invalid/expired token is a
    4xx `AuthApiError`, which is never transient whatever its text says. The
    W1-4 text class covers anything else. `scrubbed_text` has the token removed
    first: base64 can spell "dns" by chance.
    """
    if isinstance(e, (httpx.TransportError, AuthRetryableError)):
        return True
    if isinstance(e, AuthApiError):
        return False
    lowered = scrubbed_text.lower()
    return any(term in lowered for term in _TRANSIENT_AUTH_ERROR_TERMS)


async def complete_password_recovery(access_token: str, new_password: str) -> Dict:
    """W3-6 -- set a new password with the access token from a recovery link.

    Order: local blacklist (a spent token cannot be replayed here) -> upstream
    `get_user` verification -> fail-closed AMR gate (only a session minted from
    a RECOVERY link may rotate the password; any other live bearer would be a
    "change password without the current one" door) -> the same admin write
    `change_user_password` makes -> blacklist the token.

    A transport/upstream failure during `get_user` is NOT a verdict on the
    token: it returns the W1-4 `UPSTREAM_UNAVAILABLE` shape (retryable), never
    `RECOVERY_TOKEN_INVALID` (which sends the user back for a new email).

    The token never reaches a log: `UserDoesntExist(access_token)`'s `str()` IS
    the bearer on this SDK, so every exception text is scrubbed by value.
    """
    try:
        if await _is_token_revoked_async(access_token):
            logger.warning("[auth] password recovery rejected: token already spent")
            return _recovery_token_invalid()

        client = get_auth_client()
        try:
            user_response = await run_db(lambda: client.auth.get_user(access_token))
        except Exception as e:
            scrubbed = str(e).replace(access_token, "<access_token>")
            if _is_upstream_unavailable(e, scrubbed):
                # A blip is not a verdict: the link is still good, so the
                # screen keeps the form and the user can retry.
                logger.warning(
                    "[auth] password recovery upstream unavailable: %s: %s",
                    type(e).__name__,
                    scrubbed,
                )
                return _upstream_unavailable_result()
            logger.warning(
                "[auth] password recovery rejected: upstream verification failed: %s: %s",
                type(e).__name__,
                scrubbed,
            )
            return _recovery_token_invalid()
        if user_response is None or getattr(user_response, "user", None) is None:
            return _recovery_token_invalid()

        methods = _recovery_amr_methods(access_token)
        if not methods or "recovery" not in methods:
            logger.warning(
                "[auth] password recovery rejected: amr=%s",
                methods if methods is not None else "<undecodable>",
            )
            return _recovery_token_invalid()

        user_id = user_response.user.id
        admin = get_admin_client()
        await run_db(
            lambda: admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
        )
        _revoke_token(access_token)
        return {"success": True, "message": "Password updated"}
    except Exception as e:
        return _categorize_auth_error(
            Exception(str(e).replace(access_token, "<access_token>")), "password_recovery"
        )


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
            if ttl <= 0:
                # W1-9b (R-AUTH retro, UNFLAGGED): a locked count with no
                # positive TTL is never "locked forever". -1 = the arming was
                # lost (a key stuck like this never expired and nothing clears
                # it, because the lock blocks the successful login that would);
                # -2 / 0 = it expired or is expiring between the two round
                # trips. Re-arm the window now and report it, so the 429 always
                # carries a real Retry-After. A failed re-arm keeps the lock
                # and is retried on the next check.
                try:
                    redis_client.expire(key, LOCKOUT_WINDOW_SECONDS)
                except Exception:
                    pass
                ttl = LOCKOUT_WINDOW_SECONDS
            return {"locked": True, "retry_after": ttl}
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
        # W1-9b (R-AUTH retro, UNFLAGGED): ARM FIRST, then count. `SET key 0 NX
        # EX <window>` creates the key WITH its window in one command (a no-op
        # while a window is live), so the INCR below can never make a counter
        # that lacks one. The old INCR-then-EXPIRE-if-count==1 pair lost the
        # window whenever the EXPIRE (or the client's view of an applied INCR)
        # was lost, and five failures over ANY span then locked the account for
        # good. Both commands exist on upstash-redis 1.7.0 and redis-py.
        redis_client.set(key, 0, nx=True, ex=LOCKOUT_WINDOW_SECONDS)
        count = redis_client.incr(key)
        # Backstop for the two counters the SET NX cannot arm: a legacy key
        # already stuck WITHOUT a TTL (SET NX is a no-op on an existing key),
        # and a key that expired between the SET and the INCR (INCR recreates
        # it TTL-less). `EXPIRE ... NX` sets the window only when the key has
        # none, so a live window is never extended. Its own guard: a failure
        # here must not turn an applied count into "attempts 0".
        try:
            redis_client.expire(key, LOCKOUT_WINDOW_SECONDS, nx=True)
        except Exception:
            pass
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
