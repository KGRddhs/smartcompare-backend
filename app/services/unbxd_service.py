"""Unbxd search-API adapter — R3c (genuine Bahrain pricing).

extra.com's Bahrain storefront is backed by an Unbxd site-search API
(``search.unbxd.io/{apiKey}/{siteKey}/search``). The response carries native
BHD prices in ``response.products[]`` (NOT ``hits``), so a single read-only GET
yields a genuine ``source_method="local_bhd"`` price — $0, no Serper / render
credits.

Discipline mirrors the Algolia + Shopify adapters: STRICT title/brand match
(reuses ``price_service.strict_title_match`` / ``numbers_match`` /
``normalize_words``) so a fuzzy cross-brand hit is REJECTED, never shipped as a
wrong-brand price. ``is_price_showable`` plausibility gate + L2 content-safety
gate before returning. NEVER raises — best-effort, never critical-path.

Per-store config (apiKey + siteKey + currency + genuine) is pinned in
``UNBXD_STORES``; the apiKey is a PUBLIC site-search key shipped to every
browser. If extra-BH 401s, re-scrape the 32-hex apiKey from
``www.extra.com/en-bh/`` (the siteKey is stable).
"""
import logging
import asyncio
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus

from app.services.price_service import (
    strict_title_match,
    numbers_match,
    variant_mismatch,
    normalize_words,
    is_counterfeit_listing,
    is_accessory,
    is_price_showable,
    _convert_to_bhd,
    ENABLE_PAGE_SCRAPE,
)
from app.services.api_budget_service import (
    record_failure, record_success, is_circuit_closed,
)

logger = logging.getLogger(__name__)

# Circuit-breaker provider label (provider-agnostic — no PROVIDER_CONFIGS entry
# needed; record_failure/is_circuit_closed work for any provider string).
_UNBXD_PROVIDER = "unbxd"

_HTTP_TIMEOUT = 8.0
_ROWS = 20

# Per-store Unbxd config. `genuine`=True => native BHD => local_bhd;
# False => GCC ccy => convert => converted_usd.
UNBXD_STORES: Dict[str, Dict[str, Any]] = {
    "extra.com": {
        "api_key": "72883ca2a4420a7c7ca07cefda404539",
        "site_key": "ss-unbxd-auk-extra-bahrain-en-prod11541714990628",
        "currency": "BHD",
        "genuine": True,
    },
}


def _parse_unbxd_amount(product: Dict[str, Any]) -> Optional[float]:
    """Selling price (sale) with `price` fallback. Positive only."""
    for key in ("sellingPrice", "price", "wasPrice"):
        val = product.get(key)
        if val is None:
            continue
        if isinstance(val, bool):  # guard: bool is an int subclass
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return None


def _parse_unbxd_stock(product: Dict[str, Any]) -> bool:
    """`inStockFlag` is a STRING boolean ("true"/"false"). Default True when
    absent."""
    raw = product.get("inStockFlag")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes")
    return bool(raw)


def _match_unbxd_product(
    products: List[Dict[str, Any]], product_name: str
) -> Optional[Dict[str, Any]]:
    """Best STRICT title match among Unbxd products, or None. Same gates as the
    Algolia/Shopify paths so a fuzzy cross-brand/cross-model hit is REJECTED."""
    if not products:
        return None
    p_words = normalize_words(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for product in products:
        if not isinstance(product, dict):
            continue
        surface = (product.get("title") or product.get("name") or "").strip()
        if not surface:
            continue
        if is_counterfeit_listing(surface) or is_accessory(surface):
            continue
        if not numbers_match(product_name, surface):
            continue
        if not strict_title_match(product_name, surface):
            continue
        # Verification F1 (HIGH no-fab fix): reject a different model-line variant.
        # Without this, a base-model query ("iPhone 17 Pro 256GB") matched the
        # superset "iPhone 17 Pro MAX 256GB" (strict_title_match passes on a
        # superset, numbers_match passes — both 256GB) and, on the 1.0-overlap tie,
        # the first-seen Pro MAX (559.99) shipped as a GENUINE local_bhd price for a
        # Pro query (+14% wrong). Every other adapter (woo/salla/occ/magento/shopify)
        # applies this gate; unbxd omitted it.
        if variant_mismatch(product_name, surface):
            continue
        t_words = normalize_words(surface)
        score = (len(p_words & t_words) / len(p_words)) if p_words else 0.0
        if score < 0.4:
            continue
        if _parse_unbxd_amount(product) is None:
            continue
        if score > best_score:
            best = product
            best_score = score
    return best


async def _unbxd_search(store: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """ONE read-only GET to the Unbxd search API. Returns response.products[]
    (possibly empty). NEVER raises — graceful empty on any failure."""
    try:
        from curl_cffi import requests as curl_requests

        api_key = store["api_key"]
        site_key = store["site_key"]
        url = (
            f"https://search.unbxd.io/{api_key}/{site_key}/search"
            f"?q={quote_plus(query)}&rows={_ROWS}"
        )
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url, impersonate="chrome", timeout=_HTTP_TIMEOUT,
                allow_redirects=True,
            )
        )
        if resp.status_code != 200:
            if resp.status_code >= 500 or resp.status_code == 429:
                record_failure(_UNBXD_PROVIDER)
            logger.info("[UNBXD] search HTTP %s", resp.status_code)
            return []
        record_success(_UNBXD_PROVIDER)
        data = resp.json()
        products = (data or {}).get("response", {}).get("products")
        return products if isinstance(products, list) else []
    except Exception as e:  # noqa: BLE001 — best-effort; any failure → empty
        logger.info("[UNBXD] search error: %s", e)
        record_failure(_UNBXD_PROVIDER)
        return []


async def fetch_unbxd_price(
    domain: str, product_name: str, category: str = "other",
) -> Optional[Dict[str, Any]]:
    """Genuine-BHD (or converted-GCC) price for an Unbxd-backed storefront.

    Returns a price dict (``local_bhd`` for native-BHD extra-BH, ``converted_usd``
    for any GCC store) or ``None`` on miss / wrong-brand / disabled / error.
    NEVER raises."""
    if not ENABLE_PAGE_SCRAPE:
        return None

    norm_domain = (domain or "").replace("www.", "").strip().lower()
    store = UNBXD_STORES.get(norm_domain)
    if not store:
        return None

    if not is_circuit_closed(_UNBXD_PROVIDER):
        logger.info("[UNBXD] circuit open — skipping %s", norm_domain)
        return None

    products = await _unbxd_search(store, product_name)
    product = _match_unbxd_product(products, product_name)
    if not product:
        return None

    raw_amount = _parse_unbxd_amount(product)
    if raw_amount is None:
        return None

    title = (product.get("title") or product.get("name") or "").strip()
    url = (product.get("productUrl") or "").strip() or (
        f"https://{norm_domain}/" if norm_domain else ""
    )
    in_stock = _parse_unbxd_stock(product)

    # Currency: the product carries `currency`, but pin per store as the source
    # of truth (the hit field could drift); fall back to the product field.
    src_currency = (store.get("currency") or product.get("currency") or "BHD").upper()

    if store.get("genuine") and src_currency == "BHD":
        amount_bhd = round(float(raw_amount), 3)
        source_method = "local_bhd"
        original_currency = None
    else:
        from app.services.exchange_rate_service import FALLBACK_RATES
        if src_currency not in FALLBACK_RATES:
            logger.info("[UNBXD] no rate for %s->BHD (%s) — dropping", src_currency, norm_domain)
            return None
        converted = _convert_to_bhd(float(raw_amount), src_currency)
        if converted is None or converted <= 0:
            return None
        amount_bhd = round(float(converted), 3)
        source_method = "converted_usd"  # LITERAL
        original_currency = src_currency

    price: Dict[str, Any] = {
        "amount": amount_bhd,
        "currency": "BHD",
        "retailer": norm_domain,
        "url": url,
        "in_stock": in_stock,
        "estimated": False,
        "source_method": source_method,
        "title": title,
        "confidence": 0.9 if source_method == "local_bhd" else 0.85,
    }
    if original_currency:
        price["original_currency"] = original_currency

    if not is_price_showable(product_name, price):
        logger.info("[UNBXD] candidate not showable: %s %s", norm_domain, title)
        return None

    try:
        from app.services.content_safety_service import get_content_safety_service
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(f"{title} {norm_domain} {product_name}"):
            logger.info("[UNBXD] candidate dropped by content safety: %s", norm_domain)
            return None
    except Exception:  # noqa: BLE001 — safety best-effort
        pass

    return price
