"""Salla storefront-API genuine/converted price adapter (BUILD SPEC §2.2).

Mechanism — TWO steps, both unauthenticated, $0 (no Serper, no render):

  1. Scrape the storefront HTML (``GET https://<domain>/``) for the numeric
     Salla store id (regex; works for custom domains AND ``salla.sa/<slug>``).
     The store id is STABLE per domain -> cache it to skip the HTML round-trip
     on subsequent lookups.
  2. ``GET https://api.salla.dev/store/v1/products?per_page=10&keyword=<name>``
     with header ``Store-Identifier: <store_id>`` (PUBLIC, no token/cookie).

Pagination is CURSOR-based (``?page=N`` is ignored); for a price lookup we use
``?keyword=<name>`` (server-side search). There is NO per-product ``/{id}``
endpoint, so we match by ``data[].name`` within the returned page.

Genuine-vs-converted is decided at RUNTIME on ``data[].currency`` (NOT the
catalog country tag — e.g. ``rend-bahrain.com`` markets "bahrain" but bills
SAR): ``"BHD"`` -> stamp the genuine ``salla_api``; any other GCC currency ->
convert with ``_convert_to_bhd`` and stamp the literal ``"converted_usd"``.

Prices are MAJOR units (bare numbers like ``18`` / ``440``) — NEVER divide.

The adapter NEVER raises: every network/parse error -> ``None`` (verify-or-omit).
Gated by ``ENABLE_PAGE_SCRAPE`` (return ``None`` when off). Match gates
(strict_title_match / numbers_match / variant_mismatch / counterfeit /
accessory) + ``is_price_showable`` + L2 content-safety are applied before any
price is emitted (no-fab).
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional

from app.services.price_service import (
    strict_title_match,
    numbers_match,
    variant_mismatch,
    is_counterfeit_listing,
    is_accessory,
    is_price_showable,
    _convert_to_bhd,
    ENABLE_PAGE_SCRAPE,
)

logger = logging.getLogger(__name__)

# Public Salla storefront products API (no token).
_SALLA_API_URL = "https://api.salla.dev/store/v1/products"

# Per-request curl timeout (SPEC universal recipe: 12-15s; Salla is fast).
_HTTP_TIMEOUT = 12

# How many search hits to pull per lookup — enough to find the right product
# past fuzzy noise, small enough to keep the response light.
_PER_PAGE = 10

# Store id is stable per domain -> cache it to skip the storefront round-trip.
_STORE_ID_CACHE: Dict[str, str] = {}

# The store-id lives in the storefront HTML as `"store":{ ... "id":<digits> ... }`.
# Works for custom domains AND salla.sa/<slug>.
_STORE_ID_RE = re.compile(r'"store"\s*:\s*\{[^}]*?"id"\s*:\s*(\d+)')

# Currencies we can convert to BHD (mirrors exchange_rate_service.FALLBACK_RATES).
# Anything outside this set is unconvertible -> we omit (honest None) rather than
# fabricate a 1:1 number.
_CONVERTIBLE = {"SAR", "AED", "KWD", "QAR", "OMR", "USD", "EUR", "GBP", "BHD"}


def _extract_store_id(html: str) -> Optional[str]:
    """Pull the numeric Salla store id out of storefront HTML. None if absent."""
    if not html:
        return None
    m = _STORE_ID_RE.search(html)
    return m.group(1) if m else None


async def _resolve_store_id(domain: str) -> Optional[str]:
    """Return the cached store id for ``domain``, else fetch the storefront HTML
    once and extract it. ``None`` on any failure."""
    cached = _STORE_ID_CACHE.get(domain)
    if cached:
        return cached
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                f"https://{domain}/",
                impersonate="chrome",
                timeout=_HTTP_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — storefront fetch error is a miss
        logger.warning("[PRICE] salla storefront fetch failed for %s: %s", domain, exc)
        return None
    if getattr(resp, "status_code", 0) != 200:
        return None
    store_id = _extract_store_id(getattr(resp, "text", "") or "")
    if store_id:
        _STORE_ID_CACHE[domain] = store_id
    return store_id


def _select_candidate(
    data: list, product_name: str
) -> Optional[Dict[str, Any]]:
    """Pick the first hit whose ``name`` passes the strict match gates.

    Salha hits expose ``name`` (often Arabic) and frequently null
    ``brand``/``sku``/``gtin`` — so we match on ``name`` only (no-fab: a hit
    that fails strict_title_match / numbers_match / is a different variant /
    counterfeit / accessory is REJECTED, never shipped as the query's price).
    """
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get("name") or ""
        if not title:
            continue
        if is_counterfeit_listing(title):
            continue
        # Asymmetric accessory guard (review gate-fix): only drop an accessory
        # hit when the QUERY is not itself accessory-intent, so an accessory query
        # ("AirPods Pro case", "Apple Watch band") can still match its product.
        if is_accessory(title) and not is_accessory(product_name):
            continue
        if not strict_title_match(product_name, title):
            continue
        if not numbers_match(product_name, title):
            continue
        if variant_mismatch(product_name, title):
            continue
        # price must be a positive number (MAJOR units).
        try:
            amount = float(item.get("price"))
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        return item
    return None


async def fetch_salla_api_price(
    domain: str, product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Genuine/converted price for a Salla storefront, or ``None``.

    ``domain`` = the storefront host (e.g. ``reefperfumes.com``). Returns the
    shared price dict (genuine ``salla_api`` for a native-BHD store, else a
    BHD-converted price stamped ``converted_usd``) or ``None`` on any
    gate-fail / miss / error (verify-or-omit — never a pending dict, never
    raises). ``$0`` — no Serper, no render."""
    if not ENABLE_PAGE_SCRAPE:
        return None

    store_id = await _resolve_store_id(domain)
    if not store_id:
        return None

    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                _SALLA_API_URL,
                params={"per_page": _PER_PAGE, "keyword": product_name},
                headers={
                    "Store-Identifier": store_id,
                    "Accept": "application/json",
                },
                impersonate="chrome",
                timeout=_HTTP_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
        logger.warning("[PRICE] salla fetch failed for %s: %s", domain, exc)
        return None

    if getattr(resp, "status_code", 0) != 200:
        logger.info("[PRICE] salla HTTP %s for '%s' @ %s",
                    getattr(resp, "status_code", "?"), product_name, domain)
        return None

    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001 — non-JSON body -> miss
        return None

    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None

    item = _select_candidate(data, product_name)
    if item is None:
        return None

    # MAJOR units — parse as-is, NEVER divide.
    try:
        amount = float(item.get("price"))
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None

    src_ccy = (item.get("currency") or "").upper()
    if not src_ccy:
        # Review gate-fix (HIGH): a hit with NO/empty currency must NOT default to
        # BHD-genuine. A SAR/AED store that omits `currency` on a hit would
        # otherwise bank a raw foreign amount (e.g. 440) as a genuine "440 BHD"
        # price — cached 7d, showable, counted in the genuine-share KPI (a ~10x
        # over-statement). We cannot know the source currency → omit (verify-or-
        # omit), never guess.
        logger.info("[PRICE] salla hit missing currency for '%s' @ %s — omit",
                    product_name, domain)
        return None
    title = item.get("name") or ""
    url = item.get("url") or f"https://{domain}/"
    # is_out_of_stock is RELIABLE; quantity is usually null (do NOT use it).
    in_stock = not bool(item.get("is_out_of_stock"))

    # --- Genuine vs converted: branch on the ACTUAL response currency ---------
    if src_ccy == "BHD":
        price: Dict[str, Any] = {
            "amount": round(amount, 3),
            "currency": "BHD",
            "retailer": domain,
            "url": url,
            "in_stock": in_stock,
            "estimated": False,
            "source_method": "salla_api",
            "title": title,
            "confidence": 0.9,
        }
    else:
        if src_ccy not in _CONVERTIBLE:
            # Unconvertible currency -> omit rather than fabricate a 1:1 number.
            logger.info("[PRICE] salla unconvertible currency %s for '%s' @ %s",
                        src_ccy, product_name, domain)
            return None
        bhd = _convert_to_bhd(amount, src_ccy)
        if not bhd or bhd <= 0:
            return None
        price = {
            "amount": round(bhd, 3),
            "currency": "BHD",
            "original_currency": src_ccy,
            "retailer": domain,
            "url": url,
            "in_stock": in_stock,
            "estimated": False,
            "source_method": "converted_usd",
            "title": title,
            "confidence": 0.85,
        }

    # Plausibility guard (low-fragrance sample floor / high-value ceiling).
    if not is_price_showable(product_name, price):
        return None

    # L2 content-safety on the combined surface. Review gate-fix: wrapped so a
    # content-safety init/regex failure never propagates out of the adapter (the
    # never-raises contract, line 23). Fail-OPEN — never block a clean price on a
    # safety-service failure (mirrors the woo/algolia adapters).
    try:
        from app.services.content_safety_service import get_content_safety_service
        surface = f"{title} {domain} {product_name}"
        if not get_content_safety_service().is_text_safe(surface):
            logger.info("[content_safety] L2 dropped salla candidate for %s", product_name)
            return None
    except Exception:  # noqa: BLE001 — safety best-effort; never raise out of the adapter
        pass

    logger.info(
        "[PRICE] salla %s: %s %s for '%s' @ %s",
        "genuine" if src_ccy == "BHD" else "converted",
        price["currency"], price["amount"], product_name, domain,
    )
    return price
