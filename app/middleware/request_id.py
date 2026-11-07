"""Request ID middleware -- generates or preserves request correlation IDs."""
import ipaddress
import logging
import os
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# S81-24 MS4 HOP-PROBE: a dark echo line (ENABLE_HOP_PROBE_LOG, default OFF,
# read per request) on the two cheapest unauthenticated GET paths only. It
# carries counts and booleans only: never an IP, a hash or a header value.
HOP_PROBE_PATHS = ("/health", "/api/v1/app/version")
_HOP_FLAG = "ENABLE_HOP_PROBE_LOG"
# uvicorn's proxy-headers trust list; the line reports the NAME's presence
# only (the value is never read), so an operator knows whether request.client
# is the TCP peer or a header-derived address (R-S24-23).
_UVICORN_TRUST_ENV = "FORWARDED_ALLOW_IPS"


def hop_probe_log_enabled() -> bool:
    """The house idiom, read per request (never cached)."""
    return os.getenv(_HOP_FLAG, "false").strip().lower() in ("true", "1", "yes", "on")


def _parsed_ip(value):
    if value is None:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _flag(value) -> str:
    return "true" if value else "false"


def _log_hop_probe(request) -> None:
    """One INFO line about the forwarding headers versus the peer; never
    raises (a failure logs nothing)."""
    try:
        headers = request.headers
        client = request.client
        peer = _parsed_ip(client.host) if client is not None else None
        xff = [part.strip() for part in (headers.get("x-forwarded-for") or "").split(",")]
        xff = [part for part in xff if part]
        leftmost = _parsed_ip(xff[0]) if xff else None
        rightmost = _parsed_ip(xff[-1]) if xff else None
        real_raw = headers.get("x-real-ip")
        real = _parsed_ip(real_raw)
        logger.info(
            "[HOP_PROBE] xff_entries=%d xff_leftmost_is_peer=%s xff_rightmost_is_peer=%s "
            "xff_leftmost_public=%s x_real_ip_present=%s x_real_ip_is_peer=%s "
            "x_real_ip_public=%s forwarded_present=%s cf_present=%s peer_public=%s "
            "uvicorn_forwarded_allow_ips_set=%s",
            len(xff),
            _flag(peer is not None and leftmost is not None and leftmost == peer),
            _flag(peer is not None and rightmost is not None and rightmost == peer),
            _flag(leftmost is not None and leftmost.is_global),
            _flag(real_raw is not None),
            _flag(peer is not None and real is not None and real == peer),
            _flag(real is not None and real.is_global),
            _flag(headers.get("forwarded") is not None),
            _flag(headers.get("cf-connecting-ip") is not None),
            _flag(peer is not None and peer.is_global),
            _flag(_UVICORN_TRUST_ENV in os.environ),
        )
    except Exception:  # noqa: BLE001 -- the probe never affects a request
        pass


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        if hop_probe_log_enabled() and request.method == "GET" and request.url.path in HOP_PROBE_PATHS:
            _log_hop_probe(request)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
