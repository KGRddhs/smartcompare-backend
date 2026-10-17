"""Sign in with Apple: authorization-code exchange and refresh-token revocation (B3-B, S79).

Behind ENABLE_APPLE_TOKEN_REVOCATION (default OFF, read PER CALL by
`apple_token_revocation_enabled`). Callers in `auth_service`:

- social-login (Apple, with the client's `authorization_code`):
  `exchange_authorization_code` makes ONE POST to APPLE_TOKEN_URL (no retry on
  the sign-in path) and returns Apple's JSON object, or None;
- account deletion: `revoke_refresh_token` POSTs the stored refresh token to
  APPLE_REVOKE_URL, at most two attempts (the second only after a transport
  error, a total-bound TimeoutError, 429 or 5xx); True only on a 200.

Neither function ever raises: every failure is logged and turned into None /
False, so the sign-in and the deletion never fail because of Apple.

Configuration: the four SIWA_ENV_NAMES, read per call and stripped; any
missing or empty name disables the Apple step with one WARNING that names the
variables (never a value). APPLE_SIWA_CLIENT_ID has no default. The private
key is accepted as a PEM with real newlines, a PEM whose newlines arrived as
the two characters backslash + n (single-line editors), or the base64 of the
whole .p8 file (all whitespace stripped before a strict decode).

Client secret: a fresh ES256 JWT per call (CLIENT_SECRET_TTL_SECONDS = 300,
claims iss/iat/exp/aud/sub, header exactly alg + kid). It is never cached, so
no secret outlives its TTL.

Bound (ruling B3): httpx's timeout is per phase and per socket read, so it is
not a bound on its own; every Apple call therefore runs under
asyncio.wait_for(..., _CALL_DEADLINE) (6 s) with the httpx timeout
_HTTP_TIMEOUT (5 s) inside. Sign-in cost at most about 6 s; deletion at most
about 12 s.

Logging (spec 2.7): INFO or WARNING only, never exc_info; the arguments are
constants, ints (attempt number, HTTP status), comma-joined variable NAMES and
type(exc).__name__. Never logged: the authorization code, any token, the
client secret, the key or any line of it, either id_token or its claims,
Apple's response body, the email, the user id.

Test seams (production value): _TRANSPORT (None = httpx's default
transport), _now (time.time), _HTTP_TIMEOUT (5.0), _CALL_DEADLINE (6.0).

Test hazard (gate ruling GB4): APPLE_SIWA_PRIVATE_KEY is listed in
tests/_env_safety.CREDENTIALS_UNSET, so every import-time
load_dotenv(override=True) (app.main and the extraction services) re-runs the
conftest credential sanitizer and strips it again. A test sets the key only
AFTER the first app import.
"""
import asyncio
import base64
import binascii
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx
import jwt

logger = logging.getLogger(__name__)

APPLE_AUDIENCE = "https://appleid.apple.com"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"

SIWA_ENV_NAMES = (
    "APPLE_SIWA_TEAM_ID",
    "APPLE_SIWA_KEY_ID",
    "APPLE_SIWA_PRIVATE_KEY",
    "APPLE_SIWA_CLIENT_ID",
)
CLIENT_SECRET_TTL_SECONDS = 300

# Test seams (spec 2.6, gate ruling GB3).
_TRANSPORT: Optional[httpx.AsyncBaseTransport] = None
_now = time.time
_HTTP_TIMEOUT = 5.0
_CALL_DEADLINE = 6.0

# The PEM check uses the armour prefix only (the pre-commit hook refuses the
# full private-key header in any added line).
_PEM_PREFIX = "-----BEGIN"
_MAX_REVOKE_ATTEMPTS = 2


def apple_token_revocation_enabled() -> bool:
    """B3-B flag, read PER CALL (never cached at import); default OFF."""
    return os.getenv("ENABLE_APPLE_TOKEN_REVOCATION", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _siwa_config() -> Optional[Dict[str, str]]:
    """The four stripped SIWA values, or None (one WARNING naming the missing ones)."""
    values = {name: (os.getenv(name) or "").strip() for name in SIWA_ENV_NAMES}
    missing = [name for name in SIWA_ENV_NAMES if not values[name]]
    if missing:
        logger.warning("[SIWA] config missing: %s", ",".join(missing))
        return None
    return values


def _normalise_private_key(raw: str) -> str:
    """The .p8 as PEM text; ValueError (no key material in it) when unparseable."""
    text = (raw or "").strip()
    if text.startswith(_PEM_PREFIX):
        if "\n" not in text and "\\n" in text:
            text = text.replace("\\n", "\n")
        return text
    try:
        decoded = base64.b64decode("".join(text.split()), validate=True).decode("ascii")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise ValueError("unparseable private key") from None
    decoded = decoded.strip()
    if not decoded.startswith(_PEM_PREFIX):
        raise ValueError("unparseable private key")
    return decoded


def build_client_secret(config: Dict[str, str], now: Optional[float] = None) -> str:
    """A fresh ES256 client-secret JWT for Apple's token / revoke endpoints.

    Raises whatever normalising or signing raises (ValueError for an
    unparseable key, InvalidKeyError for a key of the wrong type); the callers
    log the exception type and abandon the Apple step."""
    issued = int(_now()) if now is None else int(now)
    claims = {
        "iss": config["APPLE_SIWA_TEAM_ID"],
        "iat": issued,
        "exp": issued + CLIENT_SECRET_TTL_SECONDS,
        "aud": APPLE_AUDIENCE,
        "sub": config["APPLE_SIWA_CLIENT_ID"],
    }
    signing_pem = _normalise_private_key(config["APPLE_SIWA_PRIVATE_KEY"])
    return jwt.encode(
        claims,
        signing_pem,
        algorithm="ES256",
        headers={"kid": config["APPLE_SIWA_KEY_ID"], "typ": None},
    )


async def _post_form(url: str, form: Dict[str, str]) -> httpx.Response:
    """One form POST, bounded in TOTAL by _CALL_DEADLINE (ruling B3)."""

    async def _send() -> httpx.Response:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, transport=_TRANSPORT) as client:
            return await client.post(url, data=form)

    return await asyncio.wait_for(_send(), _CALL_DEADLINE)


def _signed_form(config: Dict[str, str], step: Dict[str, str]) -> Optional[Dict[str, str]]:
    """client_id + a fresh client_secret + the step's fields, or None (logged)."""
    try:
        client_secret = build_client_secret(config)
    except Exception as exc:  # noqa: BLE001 -- type only, never the key
        logger.warning("[SIWA] client secret build failed: %s", type(exc).__name__)
        return None
    return {"client_id": config["APPLE_SIWA_CLIENT_ID"], "client_secret": client_secret, **step}


def _usable_token_response(response: httpx.Response) -> Optional[Dict[str, Any]]:
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 -- a non-JSON body is "unusable"
        return None
    if not isinstance(body, dict):
        return None
    refresh = body.get("refresh_token")
    if not (isinstance(refresh, str) and refresh and isinstance(body.get("id_token"), str)):
        return None
    return body


async def exchange_authorization_code(code: str) -> Optional[Dict[str, Any]]:
    """Exchange an Apple authorization code (single shot); Apple's JSON or None. Never raises."""
    config = _siwa_config()
    if config is None:
        return None
    form = _signed_form(config, {"code": code, "grant_type": "authorization_code"})
    if form is None:
        return None
    try:
        response = await _post_form(APPLE_TOKEN_URL, form)
    except Exception as exc:  # noqa: BLE001 -- transport error or the total bound
        logger.warning("[SIWA] exchange failed: %s", type(exc).__name__)
        return None
    if response.status_code != 200:
        logger.warning("[SIWA] exchange status=%d", response.status_code)
        return None
    body = _usable_token_response(response)
    if body is None:
        logger.warning("[SIWA] exchange response unusable")
        return None
    logger.info("[SIWA] exchange status=%d", 200)
    return body


def _retryable_status(status: int) -> bool:
    return status == 429 or status >= 500


async def revoke_refresh_token(token: str) -> bool:
    """Revoke a stored Apple refresh token; True only on a 200. Never raises.

    At most two attempts; the second only after a transport error
    (httpx.HTTPError), the total bound (TimeoutError), 429 or 5xx. No sleep
    between them; one client secret serves both (TTL 300 s)."""
    config = _siwa_config()
    if config is None:
        return False
    form = _signed_form(config, {"token": token, "token_type_hint": "refresh_token"})
    if form is None:
        return False
    for attempt in range(1, _MAX_REVOKE_ATTEMPTS + 1):
        try:
            response = await _post_form(APPLE_REVOKE_URL, form)
        except Exception as exc:  # noqa: BLE001 -- type only
            logger.warning("[SIWA] revoke attempt=%d failed: %s", attempt, type(exc).__name__)
            if isinstance(exc, (httpx.HTTPError, asyncio.TimeoutError)):
                continue
            return False
        status = response.status_code
        if status == 200:
            logger.info("[SIWA] revoke attempt=%d status=%d", attempt, 200)
            return True
        logger.warning("[SIWA] revoke attempt=%d status=%d", attempt, status)
        if not _retryable_status(status):
            return False
    return False
