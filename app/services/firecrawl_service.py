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
FIRECRAWL_TIMEOUT = 15  # seconds — Smart Wait needs time for XHR
FIRECRAWL_WAIT_MS = 5000  # ms to wait for dynamic content after page load


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
