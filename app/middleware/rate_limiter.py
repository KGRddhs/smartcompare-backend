"""Rate limiting -- uses slowapi with in-memory storage (Redis optional)."""
import ipaddress
import os
import logging
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)


# M13-02: proxy-aware client identification, behind a default-OFF flag.
#
# get_remote_address returns the TCP peer, which on Railway is the edge proxy —
# so every caller hashes to ONE limiter key and every admin_audit_log row records
# the proxy IP. With ENABLE_PROXY_AWARE_RATELIMIT ON we key on the leftmost,
# IP-validated X-Forwarded-For entry instead (the originating client). The same
# helper feeds the audit ip_address field so the two never drift.
#
# Read PER CALL via os.getenv (never cached at import), so flag-OFF is
# byte-identical to today and Railway can flip it without a redeploy.
def _proxy_aware_enabled() -> bool:
    return os.getenv("ENABLE_PROXY_AWARE_RATELIMIT", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _leftmost_xff_ip(request: Request) -> Optional[str]:
    """Return the leftmost, validated IP from X-Forwarded-For, or None.

    XFF is `client, proxy1, proxy2, …`; the leftmost hop is the originating
    client. Anything that is not a valid IPv4/IPv6 address is rejected so a
    spoofed/garbage header can never become the key or an audit value.
    """
    raw = request.headers.get("x-forwarded-for", "")
    if not raw:
        return None
    candidate = raw.split(",", 1)[0].strip()
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _rate_limit_key(request: Request) -> str:
    """slowapi key_func. Flag-OFF: exactly get_remote_address (today). Flag-ON:
    the leftmost validated XFF, falling back to the TCP peer when absent/bad."""
    if _proxy_aware_enabled():
        ip = _leftmost_xff_ip(request)
        if ip:
            return ip
    return get_remote_address(request)


def audit_client_ip(request: Request) -> Optional[str]:
    """Client IP for admin_audit_log.ip_address, sharing the same XFF helper as
    the limiter key. Flag-OFF is byte-identical to the previous inline
    `request.client.host if request.client else None`."""
    if _proxy_aware_enabled():
        ip = _leftmost_xff_ip(request)
        if ip:
            return ip
    return request.client.host if request.client else None


# M13-01 (closeout gate): the blanket ANON_LIMIT default fires on EVERY
# undecorated route once SlowAPIMiddleware is registered. Under the shipped
# default (ENABLE_PROXY_AWARE_RATELIMIT OFF) the limiter key is the shared
# Railway edge-proxy IP, so a 10/min default is ONE deployment-wide bucket per
# URL path — it would 429 the hot app-open reads (/app/version, /usage/status,
# /auth/me, /auth/verify) and the infra endpoints (/health, /, /favicon.ico) for
# ALL users the moment aggregate traffic on a path tops 10/min. That is a
# self-inflicted availability regression, so the blanket default is gated behind
# a NEW default-OFF flag and SlowAPIMiddleware is only registered when it is ON
# (see app/main.py). Read PER CALL via os.getenv so the gate is byte-identical
# to 674034e when OFF. ACTIVATION PRECONDITION: flip this ONLY together with a
# verified ENABLE_PROXY_AWARE_RATELIMIT so the key is per-client, never the
# shared proxy IP. The credential-route protection (explicit @limiter.limit +
# account lockout on PUT /auth/{email,password}) rides its own decorators and is
# LIVE regardless of this flag.
def _default_rate_limits_enabled() -> bool:
    return os.getenv("ENABLE_DEFAULT_RATE_LIMITS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

# Default rate limits for different endpoint types
ANON_LIMIT = "10/minute"
AUTH_LIMIT = "30/minute"
ADMIN_LIMIT = "60/minute"
DAILY_LIMIT = "100/day"


def _get_storage_uri() -> str:
    """Build storage URI -- memory for simplicity and reliability."""
    # Upstash uses a REST API, not standard Redis protocol.
    # slowapi expects a Redis connection via redis:// scheme, which
    # is incompatible with Upstash REST. Use in-memory storage --
    # acceptable for a single Railway instance.
    logger.info("Rate limiter using in-memory storage")
    return "memory://"


# M13-01: default_limits only fire once SlowAPIMiddleware is registered in
# app.main. They apply per-URL-path (slowapi keys them on the request path)
# and — until the M13-02 proxy-aware key_func is flipped ON — under the shared
# Railway edge-proxy IP, i.e. one bucket per path for the whole deployment. A
# deployment-wide *daily* ceiling (the old DAILY_LIMIT=100/day) would therefore
# throttle the read-heavy undecorated routes that the app hits on every open
# (GET /usage/status, /auth/me, /auth/verify, /app/version, /legal/*) to 100
# requests/DAY across ALL users — a self-inflicted outage. The per-minute burst
# window (ANON_LIMIT) resets each minute, still caps network-speed abuse, and
# matches the regime the already-decorated hot path (/text/compare = 10/min)
# has run under in production. The two credential-checking PUT routes get their
# own tighter explicit 5/min limit in auth_routes.
limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=_get_storage_uri(),
    default_limits=[ANON_LIMIT],
)
