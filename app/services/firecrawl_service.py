"""Firecrawl Service — thin async wrapper around Firecrawl /v1/scrape API.

Firecrawl renders JavaScript SPAs with Smart Wait, capturing XHR-loaded content
that Cloudflare/Microlink miss. Used as Tier 1.5a for official brand sites.
"""
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_TIMEOUT = 30  # seconds — luxury SPAs (LV, Chanel) need longer to render
FIRECRAWL_WAIT_MS = 5000  # ms to wait for dynamic content after page load


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
    so post-deploy probes can identify why mainstream products fall to
    `estimated`. Never raises."""
    if not _diag_enabled():
        return
    try:
        from app.services import api_budget_service
        logger.info(
            "PRICE_PIPELINE_DIAG firecrawl_invocation url=%s credits_remaining=%s breaker_state=%s",
            url,
            api_budget_service.get_remaining("firecrawl"),
            api_budget_service.get_breaker_state("firecrawl"),
        )
    except Exception:  # noqa: BLE001 — diagnostic must never raise
        pass


def is_available() -> bool:
    """Check if Firecrawl is configured (API key present)."""
    enabled = os.environ.get("ENABLE_FIRECRAWL", "true").lower() != "false"
    has_key = bool(os.environ.get("FIRECRAWL_API_KEY"))
    return enabled and has_key


async def scrape_page(url: str) -> Optional[str]:
    """Scrape a URL via Firecrawl and return rendered HTML.

    Returns None if:
    - API key not configured
    - API returns error
    - Response has no HTML content

    Raises no exceptions — all errors are logged and return None.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None

    _log_invocation(url)

    try:
        async with httpx.AsyncClient(timeout=FIRECRAWL_TIMEOUT) as client:
            resp = await client.post(
                FIRECRAWL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["html"],
                    "waitFor": FIRECRAWL_WAIT_MS,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    html = data.get("data", {}).get("html", "")
                    if html and len(html) > 500:
                        logger.info(f"[FIRECRAWL] Got {len(html)//1024}KB HTML from {url}")
                        return html
                    else:
                        logger.info(f"[FIRECRAWL] Empty/short response from {url}")
                else:
                    logger.warning(f"[FIRECRAWL] API error: {data.get('error', 'unknown')}")
                return None

            # Return status code for circuit breaker classification
            logger.warning(f"[FIRECRAWL] HTTP {resp.status_code} for {url}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"[FIRECRAWL] Timeout ({FIRECRAWL_TIMEOUT}s) for {url}")
        return None
    except Exception as e:
        logger.warning(f"[FIRECRAWL] Error: {e}")
        return None


async def scrape_page_with_status(url: str) -> tuple[Optional[str], int]:
    """Like scrape_page but also returns HTTP status code for circuit breaker decisions.

    Returns (html_or_none, status_code). Status 0 means connection/timeout error.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None, 0

    _log_invocation(url)

    try:
        async with httpx.AsyncClient(timeout=FIRECRAWL_TIMEOUT) as client:
            resp = await client.post(
                FIRECRAWL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["html"],
                    "waitFor": FIRECRAWL_WAIT_MS,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    html = data.get("data", {}).get("html", "")
                    if html and len(html) > 500:
                        logger.info(f"[FIRECRAWL] Got {len(html)//1024}KB HTML from {url}")
                        return html, 200
                return None, 200  # 200 but no usable content

            logger.warning(f"[FIRECRAWL] HTTP {resp.status_code} for {url}")
            return None, resp.status_code

    except httpx.TimeoutException:
        logger.warning(f"[FIRECRAWL] Timeout ({FIRECRAWL_TIMEOUT}s) for {url}")
        return None, 0
    except Exception as e:
        logger.warning(f"[FIRECRAWL] Error: {e}")
        return None, 0


# =============================================================================
# Bundle E Task 2.4 — SCRAPING_MODE classifier
# Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 8.
# Tests: tests/test_scraping_mode.py
# =============================================================================

# Luxury / premium fashion + jewelry brand domains. Soft mode fans out
# only for these (where Cloudflare/SPA rendering tends to defeat curl).
# Subset mirrors price_service.OFFICIAL_BRAND_DOMAINS + GCC luxury retailers.
_LUXURY_DOMAINS = frozenset({
    "louisvuitton.com", "hermes.com", "chanel.com", "gucci.com", "prada.com",
    "dior.com", "burberry.com", "fendi.com", "balenciaga.com", "cartier.com",
    "tiffany.com", "rolex.com", "versace.com", "givenchy.com", "valentino.com",
    "bloomingdales.com", "bloomingdales.ae", "ounass.com", "ounass.ae",
    "harveynichols.com", "selfridges.com",
})


def _normalize_host(url: str) -> str:
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:  # noqa: BLE001
        return ""


def _is_luxury_url(url: str) -> bool:
    host = _normalize_host(url)
    if not host:
        return False
    # Match exact host or any suffix match (e.g. uk.louisvuitton.com).
    if host in _LUXURY_DOMAINS:
        return True
    for dom in _LUXURY_DOMAINS:
        if host.endswith("." + dom) or host == dom:
            return True
    return False


def should_fan_out(url: str, mode: Optional[str] = None) -> bool:
    """Decide whether to fire Firecrawl/Scrape.do for a given URL.

    `mode` precedence: explicit arg > SCRAPING_MODE env var > "hard".
    Anything other than the literal "soft" string falls back to hard
    (fail-OPEN: burn credits, produce results).

    - hard: always fan out (Firecrawl + Scrape.do fire for every URL).
    - soft: fan out only for known luxury/SPA domains where curl-only
            scrape typically returns no price.
    """
    if mode is None:
        mode = os.environ.get("SCRAPING_MODE", "hard")
    if not isinstance(mode, str) or mode != "soft":
        return True  # hard or unknown → fan out
    # soft: only luxury domains
    return _is_luxury_url(url)
