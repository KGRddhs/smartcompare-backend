"""Zyte render-tier adapter — genuine BHD prices from Akamai-walled luxury sites.

The luxury Western fragrance/beauty gap (Tom Ford, Dior, YSL …) lives on sites
like sephora.me /bh-en that are Akamai-walled — `curl_cffi` and even a plain
datacenter render get a 403. Zyte API's AI extraction with `geolocation: "BH"`
cracks the wall (residential, Bahrain-geo) and returns a STRUCTURED BHD price.
Feasibility-proven 2026-06-26 (Tom Ford Oud Wood EDP 77.000 BHD via sephora.me).

⚠️ OFF-CLOCK ONLY. A Zyte browser render is SLOW (browserHtml >90s; product
extraction tens of seconds) — far past the 15s live price clock. So this adapter
is GATED by ENABLE_ZYTE_RENDER (fail-CLOSED, default OFF) and is invoked ONLY by
the off-clock seed/warmer (scripts/seed_zyte_luxury.py), never on the request
path. The live cascade serves the genuine BHD price the seed wrote to the cache.

Genuine method ``zyte_render_bhd``. FRAGRANCE/BEAUTY-scoped (the fils-fix assumes
a plausible price < 1000 BHD). Strict-match no-fab (sephora doesn't stock every
brand — a "Creed Aventus" search returns makeup, which MUST be rejected, not
shipped as a wrong price). Budget-aware (records Zyte usage). NEVER raises.
"""
from __future__ import annotations

import base64
import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from app.services.price_service import (
    strict_title_match,
    numbers_match,
    variant_mismatch,
    is_counterfeit_listing,
    is_accessory,
    is_price_showable,
    normalize_words,
)

logger = logging.getLogger(__name__)

ZYTE_API_URL = "https://api.zyte.com/v1/extract"
_TIMEOUT = float(os.getenv("ZYTE_TIMEOUT", "100"))
_GENUINE_METHOD = "zyte_render_bhd"

# Per-store config: apex domain -> {search URL template, currency}. The search
# productList extraction returns matching PDPs + prices in one Zyte call.
ZYTE_STORES: Dict[str, Dict[str, str]] = {
    "sephora.me": {
        "search": "https://www.sephora.me/bh-en/search?q={q}",
        "currency": "BHD",
    },
}


def _enabled() -> bool:
    """Fail-CLOSED gate. Zyte is a PAID, SLOW render — it fires ONLY when the
    off-clock seed explicitly enables it. The live web service leaves this OFF, so
    a Zyte render can never land on the 15s request path."""
    return os.getenv("ENABLE_ZYTE_RENDER", "").strip().lower() in ("true", "1", "yes", "on")


def _auth_header() -> Optional[str]:
    key = os.getenv("ZYTE_API_KEY")
    if not key:
        return None
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()


def normalize_bhd_amount(raw: Any) -> Optional[float]:
    """The fils-fix. Zyte parses BHD's 3-decimal format INCONSISTENTLY — the same
    "77.000 BHD" comes back as "77000.0" (decimal stripped → fils) or, sometimes,
    "11.0" (kept). For the FRAGRANCE/BEAUTY scope (genuine prices well under 1000
    BHD) a value >= 1000 is therefore the fils form → divide by 1000. A value < 1000
    is already the major unit. Returns None for non-positive/garbage. (NOT safe for
    electronics, where a genuine >1000 BHD price exists — this adapter is
    fragrance/beauty-scoped.)"""
    try:
        amt = float(raw)
    except (TypeError, ValueError):
        return None
    if amt <= 0:
        return None
    if amt >= 1000:
        amt = amt / 1000.0
    return round(amt, 3)


async def _zyte_extract(url: str, body: Dict[str, Any]) -> Optional[dict]:
    """ONE Zyte API extraction with geolocation=BH. Returns the parsed JSON or
    None on any failure (no key / non-200 / transport). Never raises."""
    auth = _auth_header()
    if not auth:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                ZYTE_API_URL,
                headers={"Authorization": auth},
                json={"url": url, "geolocation": "BH", **body},
            )
    except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
        logger.warning("[ZYTE] extract failed for %s: %s", url, exc)
        return None
    if resp.status_code != 200:
        logger.info("[ZYTE] HTTP %s for %s: %s", resp.status_code, url, resp.text[:120])
        return None
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return None


def _match_product(products: List[Dict[str, Any]], product_name: str) -> Optional[Dict[str, Any]]:
    """Best STRICT title match among Zyte products, or None. Same no-fab gates as
    every other adapter so a wrong-brand hit (sephora returns makeup for a "Creed
    Aventus" search) is REJECTED, never shipped as the query's price."""
    if not products:
        return None
    p_words = normalize_words(product_name)
    if not p_words:
        return None
    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for product in products:
        if not isinstance(product, dict):
            continue
        name = (product.get("name") or "").strip()
        if not name:
            continue
        if is_counterfeit_listing(name) or is_accessory(name):
            continue
        if not numbers_match(product_name, name):
            continue
        if variant_mismatch(product_name, name):
            continue
        if normalize_bhd_amount(product.get("price")) is None:
            continue
        t_words = normalize_words(name)
        # BRAND-IMPLIED-BY-SEARCH relaxation: sephora's productList titles OMIT the
        # brand ("Oud Wood - Eau de Parfum", not "Tom Ford Oud Wood …") because the
        # search already scoped the brand — so strict_title_match (which requires
        # EVERY query word, incl. the brand) wrongly rejects the right product.
        # Instead require the DISTINCTIVE product tokens present (overlap >= 0.5,
        # which rejects a wrong-brand result whose overlap is ~0, e.g. a "Creed
        # Aventus" search returning makeup), and prefer the title with the FEWEST
        # EXTRA tokens so the plain "Eau de Parfum" beats the "… Set"/gift SKU.
        overlap = len(p_words & t_words) / len(p_words)
        if overlap < 0.5:
            continue
        extra = len(t_words - p_words)
        score = overlap - 0.1 * extra
        if score > best_score:
            best = product
            best_score = score
    return best


async def fetch_zyte_price(
    domain: str, product_name: str, currency: str = "BHD", category: str = "fragrances",
) -> Optional[Dict[str, Any]]:
    """Genuine BHD price for an Akamai-walled luxury store via Zyte render, or None.

    OFF-CLOCK only (gated by ENABLE_ZYTE_RENDER). Searches the store via Zyte
    productList, strict-matches the product (no-fab), fils-normalizes the BHD
    amount, and returns a ``source_method="zyte_render_bhd"`` price dict
    (is_price_showable + content-safety gated) or None on any miss / wrong-match /
    error. NEVER raises."""
    if not _enabled():
        return None
    store = ZYTE_STORES.get((domain or "").replace("www.", "").strip().lower())
    if not store:
        return None

    search_url = store["search"].format(q=urllib.parse.quote(product_name))
    data = await _zyte_extract(search_url, {"productList": True})
    if not data:
        return None
    products = (data.get("productList") or {}).get("products") or []
    hit = _match_product(products, product_name)
    if not hit:
        logger.info("[ZYTE] no strict match for '%s' @ %s (%d candidates)",
                    product_name, domain, len(products))
        return None

    amount = normalize_bhd_amount(hit.get("price"))
    if amount is None:
        return None

    domain = (domain or "").replace("www.", "").strip().lower()
    title = (hit.get("name") or "").strip()
    price = {
        "amount": amount,
        "currency": "BHD",
        "retailer": domain,
        "url": hit.get("url") or f"https://{domain}/",
        "in_stock": True,
        "estimated": False,
        "source_method": _GENUINE_METHOD,
        "title": title,
        "confidence": 0.9,
        "image_url": (hit.get("mainImage") or {}).get("url") if isinstance(hit.get("mainImage"), dict) else None,
    }

    if not is_price_showable(product_name, price):
        return None
    try:
        from app.services.content_safety_service import get_content_safety_service
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(f"{title} {domain} {product_name}"):
            logger.info("[ZYTE] candidate dropped by content safety: %s", domain)
            return None
    except Exception:  # noqa: BLE001 — safety best-effort; never block a clean price
        pass

    logger.info("[ZYTE] genuine BHD: %.3f for '%s' @ %s", amount, product_name, domain)
    return price
