"""Rate limiting -- uses slowapi with in-memory storage (Redis optional)."""
import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

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
    key_func=get_remote_address,
    storage_uri=_get_storage_uri(),
    default_limits=[ANON_LIMIT],
)
