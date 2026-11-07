"""Scrape.do Service — thin async wrapper around Scrape.do rendering API.

Scrape.do renders JavaScript pages (Tier 1.5d) for render-only SPA pages when curl
fetched HTML with no price. Its super / residential-proxy mode is retired under the
robots policy (challenge = stop; owner decision 12): it runs only when
ENABLE_SCRAPEDO_SUPER is true; an unset name means OFF (S81-23b; the legacy
name is no longer read).
"""
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

SCRAPEDO_API_URL = "https://api.scrape.do"
# seconds — render=true needs time. Env-driven (Genuine-BH bundle WS3/D5): the
# OFF-CLOCK warmer raises SCRAPEDO_TIMEOUT (e.g. 35) so the residential-proxy
# render can finish a slow SPA inside its 35s FAN_OUT_BUDGET; live keeps the 15s
# default (the request clock bounds it there). Read at import; the warmer sets
# the env before importing the service. NOTE: a longer timeout does NOT defeat an
# anti-bot wall (the WS3 capability trace found CF "you have been blocked"
# interstitials, and sephora.me /bh-en returns a 403 AkamaiGHost block, regardless
# of budget; bolo/boutiqaat were since cracked to $0 curl/sitemap adapters).
SCRAPEDO_TIMEOUT = int(os.getenv("SCRAPEDO_TIMEOUT", "15"))


# Bundle C § 1c diagnostic flag — flag-gated, zero prod overhead with off.
# Cached at process init; tests reset via monkeypatch on _PRICE_PIPELINE_DIAG_FLAG.
_PRICE_PIPELINE_DIAG_FLAG = None


def _diag_enabled() -> bool:
    global _PRICE_PIPELINE_DIAG_FLAG
    if _PRICE_PIPELINE_DIAG_FLAG is None:
        _PRICE_PIPELINE_DIAG_FLAG = (
            os.environ.get("DEBUG_STAGE_TIMINGS", "false").lower() == "true"
        )
    return _PRICE_PIPELINE_DIAG_FLAG


# Scrape.do "super" mode (the super=true residential-proxy request option plus a
# geoCode) is RETIRED under the robots policy
# (docs/policies/2026-08-31-robots-unreadable-ruling.md: a challenge is a stop,
# never a target; owner decision 12; S81-23). OFF, a request carries exactly
# {token, url, render: "true"}; ON adds super=true + geoCode (billed about 10-25
# credits per request against about 5; A7 meters it against the 900/mo budget).
# Read PER CALL by scrapedo_super_enabled(): ENABLE_SCRAPEDO_SUPER set uses the
# house idiom (strip + lower, truthy set; "false" is a kill switch); UNSET means
# OFF. S81-23b (2026-11-07, after the owner's dated unset line of the legacy name
# on web and price-warmer) deleted the S81-23 transition branch that read the
# legacy name while the new one was unset. _SUPER_FLAGS is no longer a cache; it
# stays declared for the reset_super_flags_cache() hook that tests and scripts
# still call.
_SUPER_FLAGS = None

_SCRAPEDO_SUPER_TRUTHY = ("true", "1", "yes", "on")


def scrapedo_super_enabled() -> bool:
    """S81-23: the Scrape.do super-mode gate, read PER CALL (never cached).

    ENABLE_SCRAPEDO_SUPER set: the house idiom (strip + lower, truthy set), so
    "false" / "0" / "off" / "" turn super mode off. ENABLE_SCRAPEDO_SUPER unset:
    OFF (S81-23b; the legacy name is no longer read)."""
    raw = os.getenv("ENABLE_SCRAPEDO_SUPER")
    if raw is None:
        return False
    return raw.strip().lower() in _SCRAPEDO_SUPER_TRUTHY


def _super_params() -> dict:
    """Return the extra GET params for a Scrape.do request: {"super":"true",
    "geoCode":<code>} when scrapedo_super_enabled(), else {} (the cost-neutral
    default). Read per call since S81-23; a fresh dict each time."""
    if not scrapedo_super_enabled():
        return {}
    return {
        "super": "true",
        "geoCode": os.environ.get("SCRAPEDO_GEOCODE", "bh"),
    }


def _super_enabled() -> bool:
    """SINGLE source of truth for the super-mode gate, shared by the request
    params (_super_params) and the routing reader
    (source_router._super_routing_enabled, which gates the lone requires_super
    row, sephora.me). Delegates to scrapedo_super_enabled() (S81-23)."""
    return scrapedo_super_enabled()


def reset_super_flags_cache() -> None:
    """Test hook, kept for compatibility: the flags are read per call since
    S81-23, so clearing _SUPER_FLAGS changes no outcome."""
    global _SUPER_FLAGS
    _SUPER_FLAGS = None


def _log_invocation(url: str) -> None:
    """Read-only diagnostic — surface credit + breaker state at call site
    for the §1c price-pipeline regression investigation. Never raises."""
    if not _diag_enabled():
        return
    try:
        from app.services import api_budget_service
        logger.info(
            "PRICE_PIPELINE_DIAG scrapedo_invocation url=%s credits_remaining=%s breaker_state=%s",
            url,
            api_budget_service.get_remaining("scrapedo"),
            api_budget_service.get_breaker_state("scrapedo"),
        )
    except Exception:  # noqa: BLE001 — diagnostic must never raise
        pass


def is_available() -> bool:
    """Check if Scrape.do is configured (API token present)."""
    enabled = os.environ.get("ENABLE_SCRAPEDO", "true").lower() != "false"
    has_token = bool(os.environ.get("SCRAPEDO_API_TOKEN"))
    return enabled and has_token


async def render_page(url: str) -> Optional[str]:
    """Render a URL via Scrape.do and return HTML.

    Returns None if token not configured, API error, or empty response.
    Raises no exceptions.
    """
    token = os.environ.get("SCRAPEDO_API_TOKEN")
    if not token:
        return None

    _log_invocation(url)

    try:
        async with httpx.AsyncClient(timeout=SCRAPEDO_TIMEOUT) as client:
            resp = await client.get(
                SCRAPEDO_API_URL,
                params={
                    "token": token,
                    "url": url,
                    "render": "true",
                    **_super_params(),  # WS-G: {} when OFF (default) -> byte-identical
                },
            )

            if resp.status_code == 200:
                html = resp.text
                if html and len(html) > 500:
                    logger.info(f"[SCRAPEDO] Got {len(html)//1024}KB HTML from {url}")
                    return html
                logger.info(f"[SCRAPEDO] Empty/short response from {url}")
                return None

            logger.warning(f"[SCRAPEDO] HTTP {resp.status_code} for {url}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"[SCRAPEDO] Timeout ({SCRAPEDO_TIMEOUT}s) for {url}")
        return None
    except Exception as e:
        logger.warning(f"[SCRAPEDO] Error: {e}")
        return None


def _parse_request_cost(resp) -> int:
    """A7 — read the per-request credit cost Scrape.do bills via the
    `Scrape.do-Request-Cost` response header. Defaults to 5 (a render=true
    request) when the header is absent or unparseable. Never raises."""
    try:
        return int(resp.headers.get("Scrape.do-Request-Cost", 5))
    except (TypeError, ValueError):
        return 5


async def render_page_with_status(url: str) -> tuple[Optional[str], int, int]:
    """Like render_page but returns (html_or_none, status_code, cost) where cost
    is the real credit count Scrape.do billed.

    A7 — cost is 0 on the NO-REQUEST paths (token missing, timeout, generic
    exception — no `resp`, 0 credits billed) and the metered header value (fallback
    5) wherever a `resp` exists (200 with html, 200 with no usable content, and a
    billed non-200 like 400/404/410/429/503). The caller meters this via
    record_usage("scrapedo", count=cost)."""
    token = os.environ.get("SCRAPEDO_API_TOKEN")
    if not token:
        return None, 0, 0

    _log_invocation(url)

    try:
        async with httpx.AsyncClient(timeout=SCRAPEDO_TIMEOUT) as client:
            resp = await client.get(
                SCRAPEDO_API_URL,
                params={
                    "token": token,
                    "url": url,
                    "render": "true",
                    **_super_params(),  # WS-G: {} when OFF (default) -> byte-identical
                },
            )

            cost = _parse_request_cost(resp)
            if resp.status_code == 200:
                html = resp.text
                if html and len(html) > 500:
                    logger.info(f"[SCRAPEDO] Got {len(html)//1024}KB HTML from {url}")
                    return html, 200, cost
                return None, 200, cost

            logger.warning(f"[SCRAPEDO] HTTP {resp.status_code} for {url}")
            return None, resp.status_code, cost

    except httpx.TimeoutException:
        logger.warning(f"[SCRAPEDO] Timeout ({SCRAPEDO_TIMEOUT}s) for {url}")
        return None, 0, 0
    except Exception as e:
        logger.warning(f"[SCRAPEDO] Error: {e}")
        return None, 0, 0
