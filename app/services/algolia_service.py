"""Algolia harvester — S3 #21 (genuine Bahrain pricing).

A GENERIC harvester for storefronts backed by a public Algolia search index
(6thStreet today; Namshi drops in via ALGOLIA_STORES once its BH app-id is
confirmed). The flow:

  1. Harvest the PUBLIC search-only Algolia config (app-id + search-key + index)
     from the storefront's landing page + main JS chunk. These credentials are
     shipped to every browser by design — a real ADMIN key is NEVER sent
     client-side (it would let anyone wipe the index). We use the harvested key
     STRICTLY for read-only `/1/indexes/{index}/query` search requests, exactly
     as the storefront browser does — never any write / settings / admin route.
  2. Query the index directly for the product → genuine BHD hits (free, $0, no
     Serper / render credits).
  3. STRICT title/brand match (reuses price_service.strict_title_match /
     numbers_match / normalize_words) so a fuzzy Algolia hit — e.g. "Tom Ford"
     → "TOMS" footwear — is REJECTED, never shipped as a wrong-brand price
     (the iPhone16→14 wrong-product class). Genuine BHD only.

Returns a `source_method="local_bhd"` price dict (real fetched BHD, `estimated`
False) or `None` on miss / config-fail / error. NEVER raises — best-effort,
never critical-path. Budget: build-time HTTP only; Algolia search is free.

L1 owns the registry + cascade wiring (the `is_algolia` flag + Tier-2 call-site);
this module is the standalone adapter L1 plugs in.
"""
import json
import re
import logging
import asyncio
from typing import Optional, Dict, Any, List

from app.services.cache_service import get_cached, set_cached
from app.services.price_service import (
    strict_title_match,
    numbers_match,
    normalize_words,
    is_counterfeit_listing,
    is_accessory,
    ENABLE_PAGE_SCRAPE,
    PAGE_SCRAPE_TIMEOUT,
)
from app.services.api_budget_service import (
    record_failure, record_success, is_circuit_closed,
)

# L1 hardening (price_service.variant_mismatch) — rejects a different model-line
# variant whose name is a prefix-superset of the query ("Galaxy S24" query vs
# "Galaxy S24 Ultra" hit passes strict_title_match but is a pricier different
# SKU). Defensive import: the helper lives on the integration branch; when this
# module is merged alongside it, the guard activates automatically. Until then
# (and on any older price_service) it no-ops to False (no mismatch) so the
# module always imports and behaviour degrades to the pre-guard matcher.
try:
    from app.services.price_service import variant_mismatch
except ImportError:  # pragma: no cover - exercised only pre-merge
    def variant_mismatch(product_name: str, title: str) -> bool:  # type: ignore
        return False

logger = logging.getLogger(__name__)

# Per-store Algolia metadata. `chunk_hint` narrows which JS bundle carries the
# search-key default (the landing-page HTML carries app-id via the DSN
# preconnect + the index, but the key lives in the main app chunk). Adding
# Namshi later = one row here once its BH app-id is confirmed (brief §2).
ALGOLIA_STORES: Dict[str, Dict[str, str]] = {
    "en-bh.6thstreet.com": {
        "index": "enterprise_magento_en_bh_products",
        "chunk_pattern": r"static/js/main\.[a-f0-9]+\.chunk\.js",
    },
}

# Config cached 24h (app-id/key/index rotate rarely; a stale key just yields a
# 403 → None → the cascade continues). Genuine-price hits are NOT cached here —
# price freshness is the price-cache layer's job (the brief's "rent facts that
# age in hours").
_CONFIG_CACHE_TTL = 24 * 60 * 60

# Algolia provider label for the circuit breaker (Firecrawl pattern: fast-fail
# repeated 5xx so a 6thStreet/Algolia outage doesn't eat the cascade budget).
_ALGOLIA_PROVIDER = "algolia"

# How many hits to pull per query — enough to find the right product past the
# fuzzy noise, small enough to keep the response light.
_HITS_PER_PAGE = 20

_HTTP_TIMEOUT = 8.0


# ---------------------------------------------------------------------------
# Generic extraction primitive (Namshi reuses this verbatim)
# ---------------------------------------------------------------------------

# app-id: the DSN preconnect host `<APPID>-dsn.algolia.net` (canonical form,
# present in every Algolia storefront's <head>).
_APPID_DSN_RE = re.compile(r"([A-Z0-9]{8,})-dsn\.algolia\.net", re.IGNORECASE)
# search-key: the minified `...adminKey..."<32-hex>"...` init default in the
# app chunk. We anchor on a 32-hex string that sits near "adminKey"/"apiKey" OR
# right after the app-id default, to avoid grabbing an unrelated hex blob.
_KEY_NEAR_RE = re.compile(
    r"""(?:adminKey|apiKey|searchKey|api_key)[^"']{0,40}["']([a-f0-9]{32})["']""",
    re.IGNORECASE,
)
_KEY_AFTER_APPID_RE = re.compile(
    r"""["'][A-Z0-9]{8,}["'][^"']{0,40}["']([a-f0-9]{32})["']""",
    re.IGNORECASE,
)


def extract_algolia_config(
    page_html: str, chunk_js: Optional[str]
) -> Optional[Dict[str, str]]:
    """Extract `{app_id, api_key, index}` from a storefront's page HTML + main
    JS chunk. Returns None if any field is missing (a partial config would 400
    the Algolia call — better to skip and let the cascade continue).

    GENERIC: app-id from the DSN preconnect host; index from an
    `enterprise_magento_*_products` / `idx=` token in the HTML; search-key from
    the chunk's minified init default near adminKey/apiKey (or right after the
    app-id default). No hard-coded credentials — works for any Algolia store.
    """
    page_html = page_html or ""

    # app-id from the DSN preconnect.
    m_app = _APPID_DSN_RE.search(page_html)
    app_id = m_app.group(1) if m_app else None

    # index — prefer an explicit enterprise_magento_*_products token, else idx=.
    m_idx = re.search(r"(enterprise_magento_[a-z0-9_]*products)", page_html, re.IGNORECASE)
    if not m_idx:
        m_idx = re.search(r"idx=([a-z0-9_]+products)", page_html, re.IGNORECASE)
    index = m_idx.group(1) if m_idx else None

    # search-key from the chunk.
    api_key = None
    if chunk_js:
        m_key = _KEY_NEAR_RE.search(chunk_js) or _KEY_AFTER_APPID_RE.search(chunk_js)
        if m_key:
            api_key = m_key.group(1)

    if not (app_id and api_key and index):
        return None
    return {"app_id": app_id, "api_key": api_key, "index": index}


# ---------------------------------------------------------------------------
# Config harvest (live page + chunk fetch, cached 24h)
# ---------------------------------------------------------------------------

async def _harvest_config(domain: str) -> Optional[Dict[str, str]]:
    """Fetch the storefront landing page + its main JS chunk, extract the
    Algolia config, cache 24h. Graceful-None on any failure."""
    domain = (domain or "").replace("www.", "").strip().lower()
    if not domain:
        return None

    cache_key = f"algolia_config:{domain}"
    cached = get_cached(cache_key)
    if cached is not None:
        if isinstance(cached, dict) and cached.get("_algolia_neg"):
            return None
        return cached if isinstance(cached, dict) else None

    def _negcache():
        set_cached(cache_key, {"_algolia_neg": True}, _CONFIG_CACHE_TTL)

    store = ALGOLIA_STORES.get(domain, {})
    chunk_pattern = store.get("chunk_pattern", r"static/js/main\.[a-f0-9]+\.chunk\.js")

    try:
        from curl_cffi import requests as curl_requests

        page = await asyncio.to_thread(
            lambda: curl_requests.get(
                f"https://{domain}/", impersonate="chrome",
                timeout=_HTTP_TIMEOUT, allow_redirects=True,
            )
        )
        if page.status_code != 200:
            logger.info("[ALGOLIA] %s landing HTTP %s", domain, page.status_code)
            _negcache()
            return None
        html = page.text

        # Locate the main chunk that carries the search-key default.
        m_chunk = re.search(rf'(https://[^"\']+{chunk_pattern})', html)
        chunk_js = None
        if m_chunk:
            chunk = await asyncio.to_thread(
                lambda: curl_requests.get(
                    m_chunk.group(1), impersonate="chrome",
                    timeout=_HTTP_TIMEOUT, allow_redirects=True,
                )
            )
            if chunk.status_code == 200:
                chunk_js = chunk.text
    except Exception as e:  # noqa: BLE001 — harvest is best-effort
        logger.info("[ALGOLIA] config harvest failed for %s: %s", domain, e)
        _negcache()
        return None

    cfg = extract_algolia_config(html, chunk_js)
    # If the store row pins an index, prefer it (HTML token can drift).
    if cfg and store.get("index"):
        cfg["index"] = store["index"]
    if not cfg:
        _negcache()
        return None

    set_cached(cache_key, cfg, _CONFIG_CACHE_TTL)
    return cfg


# ---------------------------------------------------------------------------
# Read-only Algolia query
# ---------------------------------------------------------------------------

async def _algolia_query(
    app_id: str, api_key: str, index: str, query: str
) -> List[Dict[str, Any]]:
    """POST ONE read-only search to `/1/indexes/{index}/query`. Returns the hits
    list (possibly empty). Records circuit success/failure (Firecrawl pattern).
    Raises on transport error (the caller swallows it)."""
    from curl_cffi import requests as curl_requests

    url = f"https://{app_id}-dsn.algolia.net/1/indexes/{index}/query"
    headers = {
        "X-Algolia-API-Key": api_key,
        "X-Algolia-Application-Id": app_id,
        "Content-Type": "application/json",
    }
    body = json.dumps({"query": query, "hitsPerPage": _HITS_PER_PAGE})

    resp = await asyncio.to_thread(
        lambda: curl_requests.post(
            url, headers=headers, data=body,
            impersonate="chrome", timeout=_HTTP_TIMEOUT,
        )
    )
    if resp.status_code != 200:
        # 5xx / 429 = service-level → trip the breaker. 4xx (bad key/index) =
        # config-level → don't trip (a stale key shouldn't open the breaker for
        # everyone), just return empty.
        if resp.status_code >= 500 or resp.status_code == 429:
            record_failure(_ALGOLIA_PROVIDER)
        logger.info("[ALGOLIA] query HTTP %s for index=%s", resp.status_code, index)
        return []
    record_success(_ALGOLIA_PROVIDER)
    data = resp.json()
    hits = data.get("hits")
    return hits if isinstance(hits, list) else []


# ---------------------------------------------------------------------------
# Price parsing + strict matching
# ---------------------------------------------------------------------------

def _parse_algolia_price(hit: Dict[str, Any]) -> Optional[float]:
    """Extract the genuine BHD amount from a 6thStreet/Magolia-Algolia hit.

    Shape (verified live): hit["price"] is a list; price[0]["BHD"]["default"] is
    the numeric BHD amount. Returns None when no positive BHD amount is present
    (non-BH store, missing price, 0/negative)."""
    if not isinstance(hit, dict):
        return None
    price = hit.get("price")
    if not isinstance(price, list) or not price:
        return None
    first = price[0]
    if not isinstance(first, dict):
        return None
    bhd = first.get("BHD")
    if not isinstance(bhd, dict):
        return None
    amount = bhd.get("default")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return amount


def _hit_title(hit: Dict[str, Any]) -> str:
    """Build a match surface from name + brand so brand disambiguates a fuzzy
    name (Algolia returns 'TOMS' footwear for a 'Tom Ford' query — the brand
    field is what tells them apart)."""
    name = (hit.get("name") or hit.get("title") or "").strip()
    brand = (hit.get("brand_name") or hit.get("brand") or hit.get("main_brand") or "").strip()
    return f"{brand} {name}".strip()


def _match_algolia_hit(
    hits: List[Dict[str, Any]], product_name: str
) -> Optional[Dict[str, Any]]:
    """Best STRICT title/brand match among `hits`, or None.

    Reuses the price_service gates so behaviour matches the Serper-Shopping +
    Shopify paths exactly: counterfeit/accessory dropped, significant numbers
    must match, every key product word must appear in the (brand+name) surface,
    word-overlap >= 0.4. This is what rejects the TOMS-shoes fuzzy hits for a
    'Tom Ford Black Orchid' query."""
    if not hits:
        return None
    p_words = normalize_words(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for hit in hits:
        if not isinstance(hit, dict):
            continue
        surface = _hit_title(hit)
        if not surface:
            continue
        if is_counterfeit_listing(surface) or is_accessory(surface):
            continue
        if not numbers_match(product_name, surface):
            continue
        if not strict_title_match(product_name, surface):
            continue
        # L1 hardening — reject a different model-line variant whose name is a
        # prefix-superset of the query ("Galaxy S24" vs "Galaxy S24 Ultra"):
        # strict_title_match passes (base name is a substring) but it's a
        # pricier different SKU. No-ops to False pre-merge (see import guard).
        if variant_mismatch(product_name, surface):
            continue
        t_words = normalize_words(surface)
        score = (len(p_words & t_words) / len(p_words)) if p_words else 0.0
        if score < 0.4:
            continue
        # Require a genuine BHD price before considering the hit a candidate.
        if _parse_algolia_price(hit) is None:
            continue
        if score > best_score:
            best = hit
            best_score = score
    return best


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def fetch_algolia_price(
    domain: str, product_name: str, category: str = "other",
) -> Optional[Dict[str, Any]]:
    """Genuine-BHD price for an Algolia-backed BH storefront.

    Harvests the public search config, queries the index, strict-matches the
    product, and returns a ``source_method="local_bhd"`` price dict (real BHD,
    no Serper/render) or ``None`` on miss / config-fail / wrong-brand-only /
    error. NEVER raises. L2 content-safety gated like the other Tier-1.5 entry
    points.
    """
    if not ENABLE_PAGE_SCRAPE:
        return None
    # Circuit breaker — fast-fail a sustained Algolia/storefront outage.
    if not is_circuit_closed(_ALGOLIA_PROVIDER):
        logger.info("[ALGOLIA] circuit open — skipping %s", domain)
        return None

    cfg = await _harvest_config(domain)
    if not cfg:
        return None

    try:
        hits = await _algolia_query(
            cfg["app_id"], cfg["api_key"], cfg["index"], product_name
        )
    except Exception as e:  # noqa: BLE001 — best-effort; any failure → None
        logger.info("[ALGOLIA] query error for %s: %s", domain, e)
        record_failure(_ALGOLIA_PROVIDER)
        return None

    hit = _match_algolia_hit(hits, product_name)
    if not hit:
        return None

    amount = _parse_algolia_price(hit)
    if amount is None:
        return None

    domain = (domain or "").replace("www.", "").strip().lower()
    url = hit.get("url") or hit.get("product_url") or (f"https://{domain}/" if domain else "")
    title = (hit.get("name") or hit.get("title") or "").strip()

    price = {
        "amount": round(amount, 2),
        "currency": "BHD",
        "retailer": domain,
        "url": url,
        "in_stock": bool(hit.get("in_stock", True)),
        "estimated": False,
        "source_method": "local_bhd",
        "title": title,
        "confidence": 0.9,  # genuine fetched BHD from the store's own index
    }

    # L2 content safety — drop a candidate whose surface trips the blocklist.
    try:
        from app.services.content_safety_service import get_content_safety_service
        _surface = f"{title} {domain} {product_name}"
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(_surface):
            logger.info("[ALGOLIA] candidate dropped by content safety: %s", domain)
            return None
    except Exception:  # noqa: BLE001 — safety check best-effort; never block a clean price on its failure
        pass

    return price
