"""Magento / Adobe-Commerce GraphQL price adapter — R3b (BH/GCC source-build 2026-06-25).

A single $0 direct-fetch adapter covering the TWO Magento GraphQL shapes found in
the BH/GCC discovery sweep:

  - **Shape A (Alshaya Catalog Service)** — the `*.com.bh` Alshaya brands + bn.boots.com.
    GET `https://<host>/configs.json` (a FLAT `{key,value}` record list under `.data[]`)
    → read the per-brand commerce endpoint + environment-id + store-view/website/store
    codes + x-api-key (these ROTATE per brand → NEVER hardcode; read live, cache ~24h).
    POST that endpoint a `productSearch(phrase, page_size)` query requesting BOTH the
    `SimpleProductView` and `ComplexProductView` inline fragments, then branch by
    `__typename`: single SKUs (`Simple`) carry `price.final.amount.value`; apparel /
    variant products (`Complex`) carry `priceRange.minimum.final.amount.value`.

  - **Shape B (vanilla Magento core)** — klinq / trikart / ajmal-kwt. POST
    `https://<host>/graphql` with a `Store:<store_view>` header (NO config / api-key).
    Price at `data.products.items[].price_range.minimum_price.final_price.{value,currency}`.
    `url_key` → PDP url (klinq REQUIRES the `.html` suffix; bare path 302s away).

Genuine-vs-converted: branch on the response's ACTUAL `.currency` (NOT the domain).
`currency=="BHD"` → genuine `source_method="magento_graphql_bhd"` (7d TTL, counts in the
genuine-share KPI). Any other GCC currency → `_convert_to_bhd` + the LITERAL
`"converted_usd"` (NEVER a per-platform `*_converted` string — it mis-buckets), with
`original_currency` carried.

Strict title-match (price_service gates) before emitting any price — a fuzzy / wrong-brand
hit is REJECTED, never shipped (the iPhone16→14 wrong-product class). NO minor-unit quirk —
Magento returns decimal majors (48.13, 3.75); do NOT divide.

Returns a price dict or ``None``. NEVER raises — every network / parse error → None
(verify-or-omit). Gated by ENABLE_PAGE_SCRAPE + is_price_showable + L2 content-safety.
$0 — no Serper, no render.
"""
import json
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List

from app.services.price_service import (
    strict_title_match,
    numbers_match,
    normalize_words,
    variant_mismatch,
    is_counterfeit_listing,
    is_accessory,
    is_price_showable,
    _convert_to_bhd,
    ENABLE_PAGE_SCRAPE,
)

logger = logging.getLogger(__name__)

# Per-domain pinned config. `shape` selects the parser/access path. For Shape-B
# the `store_view` is the `Store:` header value + (for stamping) the expected
# native currency lives implicitly in the response (we branch on the actual
# `.currency`). Hosts are stored normalized (no scheme, may include subdomain).
#
# Shape A reads everything else (endpoint, x-api-key, codes) LIVE from
# /configs.json — only the host + shape are pinned here.
_MAGENTO_STORES: Dict[str, Dict[str, str]] = {
    # --- Shape A (Alshaya Catalog Service + bn.boots) — native BHD ---
    "www.bathandbodyworks.com.bh": {"shape": "A"},
    "www.footlocker.com.bh": {"shape": "A"},
    "www.americaneagle.com.bh": {"shape": "A"},
    "www.muji.bh": {"shape": "A"},
    "www.newbalance.com.bh": {"shape": "A"},
    "bn.boots.com": {"shape": "A"},  # configs at the BARE host, no www
    # --- Shape B (vanilla Magento core) ---
    "klinq.com": {"shape": "B", "store_view": "default"},          # native BHD
    "trikart.com": {"shape": "B", "store_view": "kwt_en"},          # KWD → convert
    "en-kwt.ajmal.com": {"shape": "B", "store_view": "default"},    # KWD → convert
}

# Shape-A /configs.json cache — keys ROTATE, so cache the resolved config ~24h
# (a stale config just 4xx's the next POST → None → cascade continues). Module-
# level dict (no Redis dependency at import time): {host: (expires_at, cfg)}.
_CONFIG_CACHE: Dict[str, Any] = {}
_CONFIG_TTL = 24 * 60 * 60

_HTTP_TIMEOUT = 12.0
_PAGE_SIZE = 5  # productSearch / products page size — small; strict-match the hits

# --- GraphQL queries -------------------------------------------------------

# Shape A — Alshaya Catalog Service. Request BOTH inline fragments so we can
# branch by __typename (Simple = single SKU, Complex = variant/apparel).
_SHAPE_A_QUERY = """
query($phrase: String!, $pageSize: Int!) {
  productSearch(phrase: $phrase, page_size: $pageSize) {
    items {
      productView {
        name
        sku
        urlKey
        inStock
        __typename
        ... on SimpleProductView {
          price { final { amount { value currency } } regular { amount { value currency } } }
        }
        ... on ComplexProductView {
          priceRange {
            minimum {
              final { amount { value currency } }
              regular { amount { value currency } }
            }
          }
        }
      }
    }
  }
}
""".strip()

# Shape B — vanilla Magento core search.
_SHAPE_B_QUERY = """
query($phrase: String!, $pageSize: Int!) {
  products(search: $phrase, pageSize: $pageSize) {
    items {
      name
      sku
      url_key
      stock_status
      price_range {
        minimum_price {
          final_price { value currency }
          regular_price { value currency }
        }
      }
    }
  }
}
""".strip()


# ---------------------------------------------------------------------------
# Shape A — config harvest (live /configs.json, cached 24h)
# ---------------------------------------------------------------------------

def _parse_configs(payload: Any) -> Optional[Dict[str, str]]:
    """Flatten the Alshaya /configs.json `.data[]` {key,value} record list into a
    plain dict, then pull the commerce config we need. Returns None if any
    required field is missing (a partial config would 4xx the POST)."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, list):
        return None
    flat: Dict[str, str] = {}
    for rec in data:
        if isinstance(rec, dict):
            k = rec.get("key")
            v = rec.get("value")
            if isinstance(k, str):
                flat[k] = v
    endpoint = flat.get("commerce-endpoint")
    base_endpoint = flat.get("commerce-base-endpoint")
    env_id = flat.get("commerce-environment-id")
    api_key = flat.get("commerce-x-api-key")
    store_view = flat.get("commerce-store-view-code")
    website = flat.get("commerce-website-code")
    store_code = flat.get("commerce-store-code")
    customer_group = flat.get("commerce-customer-group") or "0"
    if not (endpoint and env_id and api_key and store_view and website and store_code):
        return None
    return {
        "endpoint": endpoint,
        "base_endpoint": base_endpoint or "",
        "env_id": env_id,
        "api_key": api_key,
        "store_view": store_view,
        "website": website,
        "store_code": store_code,
        "customer_group": str(customer_group),
    }


async def _harvest_shape_a_config(host: str) -> Optional[Dict[str, str]]:
    """GET https://<host>/configs.json → parsed commerce config, cached 24h.
    Graceful-None on any failure."""
    now = time.time()
    cached = _CONFIG_CACHE.get(host)
    if cached:
        expires_at, cfg = cached
        if expires_at > now:
            return cfg if cfg else None  # cached miss returns None too

    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                f"https://{host}/configs.json",
                impersonate="chrome",
                timeout=_HTTP_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.info("[MAGENTO] %s configs fetch failed: %s", host, exc)
        _CONFIG_CACHE[host] = (now + _CONFIG_TTL, None)
        return None

    if resp.status_code != 200:
        logger.info("[MAGENTO] %s configs HTTP %s", host, resp.status_code)
        _CONFIG_CACHE[host] = (now + _CONFIG_TTL, None)
        return None
    try:
        cfg = _parse_configs(resp.json())
    except Exception:  # noqa: BLE001 — non-JSON body → miss
        cfg = None
    _CONFIG_CACHE[host] = (now + _CONFIG_TTL, cfg)
    return cfg


# ---------------------------------------------------------------------------
# GraphQL POST helpers
# ---------------------------------------------------------------------------

async def _post_graphql(
    url: str, query: str, variables: Dict[str, Any], headers: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """POST a GraphQL query, return the parsed JSON or None. Never raises."""
    body = json.dumps({"query": query, "variables": variables})
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.post(
                url,
                data=body,
                headers=headers,
                impersonate="chrome",
                timeout=_HTTP_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — fetch error is a miss, never a crash
        logger.info("[MAGENTO] graphql POST failed for %s: %s", url, exc)
        return None
    if resp.status_code != 200:
        logger.info("[MAGENTO] graphql HTTP %s for %s", resp.status_code, url)
        return None
    try:
        return resp.json()
    except Exception:  # noqa: BLE001 — non-JSON body → miss
        return None


# ---------------------------------------------------------------------------
# Per-shape item parsing
# ---------------------------------------------------------------------------

def _shape_a_items(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or {}
    ps = data.get("productSearch") or {}
    items = ps.get("items")
    return items if isinstance(items, list) else []


def _shape_a_price_node(pv: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract {value, currency, in_stock, name, urlKey} from a Shape-A
    productView, branching by __typename. Returns None on any missing field."""
    typename = pv.get("__typename") or ""
    name = pv.get("name") or ""
    url_key = pv.get("urlKey") or ""
    in_stock = bool(pv.get("inStock", True))
    amount_node = None
    if "Complex" in typename:
        pr = (pv.get("priceRange") or {}).get("minimum") or {}
        amount_node = (pr.get("final") or {}).get("amount")
    else:
        # SimpleProductView (default; also covers any unexpected single-price node)
        amount_node = ((pv.get("price") or {}).get("final") or {}).get("amount")
    if not isinstance(amount_node, dict):
        return None
    value = amount_node.get("value")
    currency = amount_node.get("currency")
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value <= 0 or not currency:
        return None
    return {
        "value": value,
        "currency": str(currency).upper(),
        "in_stock": in_stock,
        "name": name,
        "url_key": url_key,
    }


def _shape_b_items(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or {}
    products = data.get("products") or {}
    items = products.get("items")
    return items if isinstance(items, list) else []


def _shape_b_price_node(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = item.get("name") or ""
    url_key = item.get("url_key") or ""
    stock_status = (item.get("stock_status") or "").upper()
    in_stock = stock_status != "OUT_OF_STOCK"  # default True when unknown
    mp = (item.get("price_range") or {}).get("minimum_price") or {}
    fp = mp.get("final_price") or {}
    value = fp.get("value")
    currency = fp.get("currency")
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value <= 0 or not currency:
        return None
    return {
        "value": value,
        "currency": str(currency).upper(),
        "in_stock": in_stock,
        "name": name,
        "url_key": url_key,
    }


# ---------------------------------------------------------------------------
# Strict matching (reuse the price_service gates)
# ---------------------------------------------------------------------------

def _best_match(
    nodes: List[Dict[str, Any]], product_name: str
) -> Optional[Dict[str, Any]]:
    """Best STRICT title match among normalized {name,...} nodes, or None.

    Reuses the price_service gates so behaviour matches the Shopify / Algolia
    paths exactly: counterfeit/accessory dropped, significant numbers must match,
    every key product word must appear, variant-line mismatch rejected,
    word-overlap >= 0.4."""
    if not nodes:
        return None
    p_words = normalize_words(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for node in nodes:
        if not node:
            continue
        title = node.get("name") or ""
        if not title:
            continue
        if is_counterfeit_listing(title) or is_accessory(title):
            continue
        if not numbers_match(product_name, title):
            continue
        if not strict_title_match(product_name, title):
            continue
        if variant_mismatch(product_name, title):
            continue
        t_words = normalize_words(title)
        score = (len(p_words & t_words) / len(p_words)) if p_words else 0.0
        if score < 0.4:
            continue
        if score > best_score:
            best = node
            best_score = score
    if best is not None:
        best = dict(best)
        best["_match_score"] = best_score
    return best


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def fetch_magento_graphql_price(
    domain: str, product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Genuine-BH / converted-GCC price from a Magento/Adobe-Commerce GraphQL
    storefront (Alshaya Shape-A OR vanilla Shape-B). See module docstring.

    Returns a price dict or ``None`` on miss / config-fail / wrong-brand-only /
    error. NEVER raises."""
    if not ENABLE_PAGE_SCRAPE:
        return None

    host = (domain or "").strip().lower()
    if host.startswith("http://"):
        host = host[7:]
    if host.startswith("https://"):
        host = host[8:]
    host = host.split("/")[0]

    store = _MAGENTO_STORES.get(host)
    if not store:
        return None
    shape = store.get("shape")

    # --- resolve the node (value/currency/name/url_key/in_stock) per shape ---
    node: Optional[Dict[str, Any]] = None
    pdp_url = ""

    if shape == "A":
        cfg = await _harvest_shape_a_config(host)
        if not cfg:
            return None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": cfg["api_key"],
            "Magento-Environment-Id": cfg["env_id"],
            "Magento-Store-View-Code": cfg["store_view"],
            "Magento-Website-Code": cfg["website"],
            "Magento-Store-Code": cfg["store_code"],
            "Magento-Customer-Group": cfg["customer_group"],
        }
        payload = await _post_graphql(
            cfg["endpoint"], _SHAPE_A_QUERY,
            {"phrase": product_name, "pageSize": _PAGE_SIZE}, headers,
        )
        items = _shape_a_items(payload)
        nodes = [
            n for n in (
                _shape_a_price_node(it.get("productView") or {})
                for it in items if isinstance(it, dict)
            ) if n
        ]
        node = _best_match(nodes, product_name)
        if node:
            base = cfg.get("base_endpoint") or f"https://{host}"
            pdp_url = f"{base.rstrip('/')}/{node.get('url_key', '').lstrip('/')}"

    elif shape == "B":
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Store": store.get("store_view", "default"),
        }
        payload = await _post_graphql(
            f"https://{host}/graphql", _SHAPE_B_QUERY,
            {"phrase": product_name, "pageSize": _PAGE_SIZE}, headers,
        )
        items = _shape_b_items(payload)
        nodes = [n for n in (_shape_b_price_node(it) for it in items if isinstance(it, dict)) if n]
        node = _best_match(nodes, product_name)
        if node:
            # Shape-B PDP url REQUIRES a .html suffix (klinq bare path 302s away).
            pdp_url = f"https://{host}/{node.get('url_key', '').lstrip('/')}.html"
    else:
        return None

    if not node:
        return None

    # --- genuine vs converted: branch on the ACTUAL response currency ---
    resp_currency = node["currency"]
    amount = node["value"]
    target = (currency or "BHD").upper()
    original_currency: Optional[str] = None
    source_method: str

    if resp_currency == "BHD":
        # Native BHD → genuine. (No conversion; if a caller ever asks for a
        # non-BHD target we don't fabricate — only BHD targets are supported by
        # the genuine path here, matching the registry which is BHD/GCC-only.)
        source_method = "magento_graphql_bhd"
    else:
        # Any other GCC currency → convert to BHD + stamp the LITERAL
        # "converted_usd" (never a per-platform *_converted string).
        if target != "BHD":
            return None  # non-BHD target unsupported (no fabrication)
        converted = _convert_to_bhd(amount, resp_currency)
        # _convert_to_bhd returns the amount UNCHANGED (with a warning) for an
        # unknown currency — guard that: an un-rated currency must NOT be shipped
        # as a 1:1 BHD figure.
        from app.services.exchange_rate_service import FALLBACK_RATES
        if resp_currency not in FALLBACK_RATES:
            return None
        if converted is None or converted <= 0:
            return None
        amount = converted
        original_currency = resp_currency
        source_method = "converted_usd"

    price: Dict[str, Any] = {
        "amount": round(float(amount), 3),  # BHD fils precision
        "currency": "BHD",
        "retailer": host,
        "url": pdp_url,
        "in_stock": bool(node.get("in_stock", True)),
        "estimated": False,
        "source_method": source_method,
        "title": node.get("name", ""),
        "confidence": round(min(0.7 + node.get("_match_score", 0.0) * 0.25, 0.95), 2),
    }
    if original_currency:
        price["original_currency"] = original_currency

    # Plausibility guard (accessory leaks / sample floors / high-value ceiling).
    if not is_price_showable(product_name, price):
        return None

    # L2 content safety.
    try:
        from app.services.content_safety_service import get_content_safety_service
        _surface = f"{price['title']} {host} {product_name}"
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(_surface):
            logger.info("[MAGENTO] candidate dropped by content safety: %s", host)
            return None
    except Exception:  # noqa: BLE001 — safety best-effort; never block a clean price on its failure
        pass

    logger.info(
        "[MAGENTO] %s %s %s for '%s' (%s)",
        source_method, price["currency"], price["amount"], product_name, host,
    )
    return price
