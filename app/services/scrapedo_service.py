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
SCRAPEDO_TIMEOUT = 15  # seconds — render=true needs time


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


async def render_page_with_status(url: str) -> tuple[Optional[str], int]:
    """Like render_page but returns (html_or_none, status_code) for circuit breaker."""
    token = os.environ.get("SCRAPEDO_API_TOKEN")
    if not token:
        return None, 0

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
                    return html, 200
                return None, 200

            logger.warning(f"[SCRAPEDO] HTTP {resp.status_code} for {url}")
            return None, resp.status_code

    except httpx.TimeoutException:
        logger.warning(f"[SCRAPEDO] Timeout ({SCRAPEDO_TIMEOUT}s) for {url}")
        return None, 0
    except Exception as e:
        logger.warning(f"[SCRAPEDO] Error: {e}")
        return None, 0
