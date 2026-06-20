"""Scrape.do Service — thin async wrapper around Scrape.do rendering API.

Scrape.do renders JavaScript pages with residential proxies and anti-bot bypass.
Used as Tier 1.5d fallback when curl_cffi fails to extract prices from retailer pages.
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
# the env before importing the service. NOTE: a longer timeout does NOT defeat a
# Cloudflare bot-wall (the WS3 capability trace found bolo.bh/boutiqaat/sephora.bh
# return a CF "you have been blocked" interstitial regardless of budget).
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
