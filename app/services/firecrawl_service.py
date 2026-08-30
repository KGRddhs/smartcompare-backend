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
# seconds — luxury SPAs (LV, Chanel) need longer to render. Env-driven (Genuine-
# BH bundle WS3/D5): the OFF-CLOCK warmer raises FIRECRAWL_TIMEOUT (e.g. 45) so a
# slow luxury SPA can finish inside its 35s FAN_OUT_BUDGET; live keeps the 30s
# default (the 15s request clock is the real bound there anyway). Read at import;
# the warmer sets the env before importing the service.
FIRECRAWL_TIMEOUT = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))
FIRECRAWL_WAIT_MS = int(os.getenv("FIRECRAWL_WAIT_MS", "5000"))  # ms to wait for dynamic content after page load

# Firecrawl format names. `html` is Firecrawl's CLEANED html — its own OpenAPI
# spec says it "Removes <script>, <style>, <noscript>, <meta>, and <head>
# tags". `rawHtml` is "the exact, unmodified HTML as received from the page".
_RAW_HTML_FORMAT = "rawHtml"
_CLEANED_HTML_FORMAT = "html"


def raw_html_enabled() -> bool:
    """True iff Firecrawl is asked for RAW markup instead of cleaned html
    (default ON).

    #92 / the measured bake-off (`docs/investigations/2026-08-25-scraper-bakeoff.md`):
    this service hardcoded ``formats: ["html"]``, so every successful fetch came
    back with 0 ``<script>`` tags and 0 ``ld+json`` blocks. This repo's
    extractor reads prices out of ``<script type="application/ld+json">``, so
    the integration could not price a page **by construction** — 0 of 9 on the
    bake-off — while billing one Firecrawl credit per call. The controlled
    probe on the same URL with ``formats: ["rawHtml"]`` returned 615 KB / 158
    scripts / 5 ld+json blocks, priced at 1.400 BHD, and was 5.4x faster.

    Default ON because this is a REPAIR of a paid integration with a measured
    0% success rate, not a new capability — there is no behaviour to preserve.
    Read per call (never cached at import) so Railway can flip it without a
    restart. With the flag OFF the service takes its exact pre-#92 path — the
    legacy format is requested, the legacy response key is read, and the
    upstream-status metadata is never even looked at — so the rollback is
    byte-identical to `main`.
    """
    return os.getenv("ENABLE_FIRECRAWL_RAW_HTML", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def _html_format() -> str:
    """The Firecrawl format this call requests — and therefore also the response
    key that carries it, since Firecrawl returns each requested format under its
    own name."""
    return _RAW_HTML_FORMAT if raw_html_enabled() else _CLEANED_HTML_FORMAT


def _upstream_status(data: dict) -> Optional[int]:
    """The TARGET site's HTTP status, from ``data.metadata.statusCode``.

    Returns None when it is absent or unparseable — the caller then fails OPEN
    (an absent status must never manufacture a failure)."""
    try:
        meta = data.get("data", {}).get("metadata")
    except AttributeError:
        return None
    if not isinstance(meta, dict):
        return None
    code = meta.get("statusCode")
    if isinstance(code, bool):  # bool is an int subclass — reject it explicitly
        return None
    if isinstance(code, int):
        return code
    if isinstance(code, str) and code.strip().isdigit():
        return int(code.strip())
    return None


def _upstream_error_page(url: str, data: dict) -> bool:
    """True when Firecrawl rendered — and BILLED for — an upstream error page.

    Firecrawl answers HTTP 200 for a URL that is really a 404 (measured on
    letoile.ae in the bake-off), so a dead registry row otherwise looks like a
    successful render and its error body gets handed to the price extractor.
    Fails OPEN: only an explicit >=400 upstream status is a miss."""
    code = _upstream_status(data)
    if code is None or code < 400:
        return False
    logger.warning(
        "[FIRECRAWL] upstream HTTP %s for %s — billed render of an error page, "
        "not a successful scrape", code, url,
    )
    return True


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
    fmt = _html_format()

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
                    "formats": [fmt],
                    "waitFor": FIRECRAWL_WAIT_MS,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    if fmt == _RAW_HTML_FORMAT and _upstream_error_page(url, data):
                        return None
                    html = data.get("data", {}).get(fmt, "")
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
    fmt = _html_format()

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
                    "formats": [fmt],
                    "waitFor": FIRECRAWL_WAIT_MS,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                # An upstream error page falls through to the shared "200 but no
                # usable content" return below — deliberately NOT a non-200
                # status. Firecrawl's own call succeeded and was BILLED, and the
                # caller records the credit only on status 200 while opening the
                # circuit breaker on 429/503/0. Reporting the upstream 404 here
                # would lose a spent credit from the budget counter and blame
                # Firecrawl for a dead registry row.
                if data.get("success") and not (
                    fmt == _RAW_HTML_FORMAT and _upstream_error_page(url, data)
                ):
                    html = data.get("data", {}).get(fmt, "")
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
