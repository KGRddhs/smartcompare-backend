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


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_get_storage_uri(),
    default_limits=[DAILY_LIMIT, ANON_LIMIT],
    # Test bypass: pytest sets RATE_LIMITER_ENABLED=false so direct route-call
    # tests (which pass MagicMock for `request`) don't hit slowapi's
    # `isinstance(request, Request)` check. Production absence of the env var
    # leaves the limiter active.
    enabled=os.getenv("RATE_LIMITER_ENABLED", "true").lower() != "false",
)
