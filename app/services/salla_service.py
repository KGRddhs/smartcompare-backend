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
import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.services.price_service import (
    normalize_candidate_brand,
    strict_title_match,
    _selection_match,
    selection_primary_admits,
    build_adapter_search_terms,
    numbers_match,
    variant_mismatch,
    is_counterfeit_listing,
    is_accessory_for_category,
    is_price_showable,
    _convert_to_bhd,
    ENABLE_PAGE_SCRAPE,
)
from app.services.exchange_rate_service import is_convertible

logger = logging.getLogger(__name__)

# Public Salla storefront products API (no token).
_SALLA_API_URL = "https://api.salla.dev/store/v1/products"

# Per-request curl timeout (SPEC universal recipe: 12-15s; Salla is fast).
from app.services.adapter_timeouts import adapter_timeout
_HTTP_TIMEOUT = adapter_timeout(12)  # M13-34: clamp under the per-source _timeout_none wrap

# How many search hits to pull per lookup — enough to find the right product
# past fuzzy noise, small enough to keep the response light.
_PER_PAGE = 10

# Store id is stable per domain -> cache it to skip the storefront round-trip.
_STORE_ID_CACHE: Dict[str, str] = {}

# The store-id lives in the storefront HTML as `"store":{ ... "id":<digits> ... }`.
# Works for custom domains AND salla.sa/<slug>.
_STORE_ID_RE = re.compile(r'"store"\s*:\s*\{[^}]*?"id"\s*:\s*(\d+)')

# Convertibility is decided by exchange_rate_service.is_convertible (the
# EFFECTIVE fallback-rate table — M21 W4). The old hand-copied ``_CONVERTIBLE``
# mirror set is deliberately GONE: it had drifted from FALLBACK_RATES (missing
# Bug 4's SGD/JPY/CNY/INR) and ignored ENABLE_EXTENDED_FALLBACK_RATES entirely.
# Anything outside the effective table is unconvertible -> we omit (honest
# None) rather than fabricate a 1:1 number.


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
    data: list, product_name: str, resolved_category: Optional[str] = None,
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
        # Brand-implied match (2026-07-07) — the Salla product carries brand as a
        # NESTED dict `{"id","url","name"}` (item["brand"] can itself be null).
        # An own-brand store (Ajmal/Asghar Ali) OMITS its brand from titles;
        # brand.name lets that pass while a WRONG-brand hit keeps the query brand
        # required. Null-safe read; inert flag-OFF (byte-identical). Mirrors magento/occ.
        _cand_brand = normalize_candidate_brand(item.get("brand"))
        if is_counterfeit_listing(title):
            continue
        # Asymmetric accessory guard (review gate-fix): only drop an accessory
        # hit when the QUERY is not itself accessory-intent, so an accessory query
        # ("AirPods Pro case", "Apple Watch band") can still match its product.
        # Category-scoped (BF4, sweep OR-7): a bare 'skin' hit on a pharmacy-class
        # resolved category is descriptive, not a phone-decal signal.
        if (is_accessory_for_category(title, resolved_category)
                and not is_accessory_for_category(product_name, resolved_category)):
            continue
        # SELECTION-PRIMARY acceptance (recon_cascade R2, Wave B4): strict's
        # RAW tokenization rejects correct rows on spacing/alias variance
        # ("90ml" vs "90 ml") the keystone _selection_match below collapses —
        # a strict FAIL falls through to the remaining chain instead of
        # hard-rejecting, GATED by selection_primary_admits (Wave B-FIX
        # wrong-brand fence: salla rows carry no brand field, so a FASHION
        # padding-brand query requires its brand token in the title). Flag
        # OFF (or exact gate OFF, where _selection_match is a no-op True)
        # restores the exact pre-change hard gate.
        if (not strict_title_match(product_name, title, candidate_brand=_cand_brand)
                and not selection_primary_admits(
                    product_name, title, candidate_brand=_cand_brand,
                    category=resolved_category)):
            continue
        if not numbers_match(product_name, title):
            continue
        if variant_mismatch(product_name, title):
            continue
        # Keystone variant-add guard (coverage/independent review) — strict_title_match
        # is SUBSET-based + variant_mismatch covers only pro/max/ultra; the broad
        # variant-add class (Mark II / mineral salt / sub-line) needs the category-aware
        # _selection_match. Flag-safe: returns True when ENABLE_EXACT_PRICE_GATE is off.
        if not _selection_match(product_name, title, resolved_category,
                                candidate_brand=_cand_brand):
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
    resolved_category: Optional[str] = None,
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

    data = None
    # R1 retrieval-term ladder: the full name first; ONLY an empty data[]
    # retries ONCE with the model-core term (rows returned — matched or not —
    # never trigger a second request; non-200/error keeps the legacy
    # immediate-None). Matching below runs against the ORIGINAL product_name,
    # so wider retrieval cannot widen acceptance.
    for term in build_adapter_search_terms(product_name, resolved_category):
        try:
            from curl_cffi import requests as curl_requests
            resp = await asyncio.to_thread(
                lambda t=term: curl_requests.get(
                    _SALLA_API_URL,
                    params={"per_page": _PER_PAGE, "keyword": t},
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
        if not (isinstance(data, list) and not data):
            break  # rows returned (even unmatched) — never a second request

    if not isinstance(data, list) or not data:
        return None

    item = _select_candidate(data, product_name, resolved_category=resolved_category)
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
        if not is_convertible(src_ccy):
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


# ===========================================================================
# UNIT B5 — cross-country Salla slug resolution (ENABLE_SALLA_SLUG_RESOLVE)
# ===========================================================================
# MEASURED (B4): ae.abdulsamadalqurashi.com prices cleanly from its Salla @graph
# JSON-LD (227.81 AED), but the kw/om/qa hosts FAILED only because the AE product
# slug does not exist on those storefronts and the request REDIRECTS to the store
# HOMEPAGE (proof: the "PDP" byte counts were identical to the homepage rows). A
# homepage has no product structured data, so extract_price_from_html returns
# nothing and the page-scrape cascade gives up. That is RESOLUTION, not a wall:
# the same store's Salla search API can still find the product by name.
#
# So when a fetched Salla PDP has collapsed to the storefront homepage, resolve
# the product via the storefront SEARCH API for that store — REUSING the existing
# ``fetch_salla_api_price`` client (store-id + keyword search). No second Salla
# client, no new transport. Ships DARK behind ENABLE_SALLA_SLUG_RESOLVE (default
# OFF, read PER CALL); with it off the resolver returns None before doing
# anything, so the caller's pre-B5 value (the got-html sentinel) is byte-identical.


def salla_slug_resolve_enabled() -> bool:
    """True iff the B5 cross-country slug resolver is active (default OFF).

    This is a NEW capture capability (recover a cross-country dead-slug price via
    the Salla search API), not a repair of a measured-0%-success production path,
    so it ships DARK and is flipped on Railway during canary. Read PER CALL from
    ``os.getenv`` (copying ``price_service.exact_gate_enabled``) so the flag can be
    flipped without a restart. With the flag OFF the resolver never runs — no
    search is issued — so the caller returns its exact pre-B5 value and the
    rollback is byte-identical."""
    return os.getenv("ENABLE_SALLA_SLUG_RESOLVE", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


# A real Salla PDP carries the product's identity in structured data — a JSON-LD
# Product node (``"@type":"Product"``, standalone OR inside an ``@graph``) and/or
# an OpenGraph ``og:type=product``. The storefront homepage the dead slug
# redirects to carries NEITHER (it is ``og:type=website`` with only a WebSite/
# Organization node). Absence of BOTH product signals on a Salla page is the
# cheap, reliable homepage-collapse tell.
_PRODUCT_JSONLD_RE = re.compile(r'"@type"\s*:\s*"product"', re.IGNORECASE)
# og:type=product in either attribute order (property-then-content or reverse),
# tolerant of surrounding whitespace/quote style.
_OG_TYPE_PRODUCT_RE = re.compile(
    r'og:type["\'][^>]*content\s*=\s*["\']\s*product'
    r'|content\s*=\s*["\']\s*product["\'][^>]*og:type',
    re.IGNORECASE,
)


def _is_salla_homepage_collapse(html: Optional[str], url: str = "") -> bool:
    """True iff ``html`` is a Salla STOREFRONT HOMEPAGE reached by a dead PDP slug.

    Cheap and total (never raises): a Salla storefront (``detect_platform`` ==
    ``"salla"``) that carries NO product structured data (no JSON-LD Product node,
    no ``og:type=product``). A genuine Salla PDP — even one whose price the
    extractor happened to miss — carries those markers and is NOT treated as a
    collapse, so the resolver never hijacks a real product page. Non-Salla / empty
    input is never a collapse."""
    if not html or not isinstance(html, str):
        return False
    try:
        from app.services.platform_router import detect_platform
        if detect_platform(html, url) != "salla":
            return False
    except Exception:  # noqa: BLE001 — platform probe is best-effort
        return False
    if _PRODUCT_JSONLD_RE.search(html):
        return False
    if _OG_TYPE_PRODUCT_RE.search(html):
        return False
    return True


async def fetch_salla_slug_resolved_price(
    url: str,
    product_name: str,
    currency: str = "BHD",
    resolved_category: Optional[str] = None,
    html: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Recover a Salla price when a cross-country PDP slug collapsed to the store
    homepage, by resolving the product through the storefront SEARCH API.

    ``url`` is the (dead) PDP url that was fetched; ``html`` is the body it
    returned (the storefront homepage on a collapse). Returns the shared price
    dict (genuine ``salla_api`` for a native-BHD store, else BHD-converted stamped
    ``converted_usd``) or ``None`` on flag-OFF / non-Salla / not-a-collapse /
    miss / error (verify-or-omit — never raises). ``$0`` — no Serper, no render.

    REUSES ``fetch_salla_api_price`` (store-id + keyword search); NO second Salla
    client. The store-id is seeded from the homepage bytes we already hold (the
    redirect target carries it), so the reused client skips its storefront
    round-trip and issues only the one search request."""
    if not salla_slug_resolve_enabled():
        return None
    if not _is_salla_homepage_collapse(html, url):
        return None
    domain = (urlparse(url).netloc or "").replace("www.", "").strip().lower()
    if not domain:
        return None
    # Don't fetch what we already have (CLAUDE.md op-principle #2): the homepage
    # body carries the numeric store-id, so seed the cache and let the reused
    # client's _resolve_store_id serve it without a second storefront GET.
    store_id = _extract_store_id(html or "")
    if store_id:
        _STORE_ID_CACHE.setdefault(domain, store_id)
    logger.info(
        "[PRICE] salla slug-collapse for '%s' @ %s -> search-resolve",
        product_name, domain,
    )
    return await fetch_salla_api_price(
        domain, product_name, currency, resolved_category=resolved_category,
    )
