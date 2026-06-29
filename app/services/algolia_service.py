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
    _selection_match,
    numbers_match,
    normalize_words,
    is_counterfeit_listing,
    is_accessory,
    is_price_showable,
    _convert_to_bhd,
    ENABLE_PAGE_SCRAPE,
    PAGE_SCRAPE_TIMEOUT,
)
from app.services.api_budget_service import (
    record_failure, record_success, is_circuit_closed,
)

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

# R3c — EXPLICIT-KEY catalog stores. These storefronts do NOT expose their appId
# via the DSN-preconnect harvest (the chunk-scrape path above), so the public
# search-only credentials are pinned here per store. All keys are PUBLIC
# search-only Algolia keys (read-only `/1/indexes/{index}/query` route — never
# write/settings/admin), exactly what the storefront browser ships.
#
# Per-store fields:
#   app_id, api_key, index — the explicit Algolia config (skips harvest).
#   currency               — pinned (the hit does NOT carry it); drives the
#                            multi-shape parser nest key + genuine/converted.
#   genuine                — True => native BHD => source_method=local_bhd;
#                            False => GCC ccy => convert => converted_usd.
#   host                   — for stores whose url field is RELATIVE (danube).
#   extra_params           — Algolia request-body `params` string (danube needs
#                            the tenant_id filter or it returns the wrong tenant).
ALGOLIA_EXPLICIT_STORES: Dict[str, Dict[str, Any]] = {
    "bahrain.sharafdg.com": {
        "app_id": "9KHJLG93J1",
        "api_key": "e81d5b30a712bb28f0f1d2a52fc92dd0",
        "index": "bahrain_products",
        "currency": "BHD",
        "genuine": True,
    },
    "uae.sharafdg.com": {
        "app_id": "9KHJLG93J1",
        "api_key": "e81d5b30a712bb28f0f1d2a52fc92dd0",
        "index": "products_index",
        "currency": "AED",
        "genuine": False,
    },
    "danube.sa": {
        "app_id": "1D2IEWLQAD",
        "api_key": "87ca3b6b2ce56f0bb76fc194a8d170e2",
        "index": "spree_products",
        "currency": "SAR",
        "genuine": False,
        "host": "https://danube.sa",
        "extra_params": "filters=tenant_id%20%3D%201",
    },
    "nahdionline.com": {
        "app_id": "H9X4IH7M99",
        "api_key": "2bbce1340a1cab2ccebe0307b1310881",
        "index": "prod_en_products",
        "currency": "SAR",
        "genuine": False,
    },
    # OMIT oman.sharafdg.com — price systematically 0.000 (parser returns None
    # for every hit, but we don't even register it as a working store).
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


async def _algolia_query_explicit(
    store: Dict[str, Any], query: str
) -> List[Dict[str, Any]]:
    """POST ONE read-only search using a store's PINNED explicit config (no
    harvest). `store` carries app_id/api_key/index and an optional
    `extra_params` request-body `params` string (danube's tenant_id filter).
    Returns the hits list (possibly empty). NEVER raises — graceful empty."""
    try:
        from curl_cffi import requests as curl_requests

        app_id = store["app_id"]
        api_key = store["api_key"]
        index = store["index"]
        url = f"https://{app_id}-dsn.algolia.net/1/indexes/{index}/query"
        headers = {
            "X-Algolia-API-Key": api_key,
            "X-Algolia-Application-Id": app_id,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {"query": query, "hitsPerPage": _HITS_PER_PAGE}
        if store.get("extra_params"):
            payload["params"] = store["extra_params"]
        body = json.dumps(payload)

        resp = await asyncio.to_thread(
            lambda: curl_requests.post(
                url, headers=headers, data=body,
                impersonate="chrome", timeout=_HTTP_TIMEOUT,
            )
        )
        if resp.status_code != 200:
            if resp.status_code >= 500 or resp.status_code == 429:
                record_failure(_ALGOLIA_PROVIDER)
            logger.info("[ALGOLIA] explicit query HTTP %s for index=%s",
                        resp.status_code, index)
            return []
        record_success(_ALGOLIA_PROVIDER)
        data = resp.json()
        hits = data.get("hits")
        return hits if isinstance(hits, list) else []
    except Exception as e:  # noqa: BLE001 — best-effort; any failure → empty
        logger.info("[ALGOLIA] explicit query error: %s", e)
        record_failure(_ALGOLIA_PROVIDER)
        return []


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


def _parse_algolia_price_multishape(
    hit: Dict[str, Any], currency: str
) -> Optional[float]:
    """Extract a positive amount from a catalog-store hit, trying, in order:

      1. NESTED  hit['price'][CUR]['default']  (nahdi: CUR='SAR')
      2. FLAT    float(hit['price'])           (sharafdg / danube)
      3. LIST    hit['price'][0][CUR]['default'] (6thStreet back-compat)

    `currency` is the store's pinned currency (the hit does NOT carry it).
    Returns None on any non-positive / unparseable amount (a 0.000 hit ->
    None, which is what makes oman.sharafdg never ship)."""
    if not isinstance(hit, dict):
        return None
    price = hit.get("price")
    cur = (currency or "").upper()

    # 1. nested dict keyed by currency
    if isinstance(price, dict):
        bucket = price.get(cur)
        if isinstance(bucket, dict):
            amount = bucket.get("default")
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                return None
            return amount if amount > 0 else None
        return None

    # 3. existing 6thStreet list shape: [{CUR: {default: N}}]
    if isinstance(price, list):
        if not price:
            return None
        first = price[0]
        if not isinstance(first, dict):
            return None
        bucket = first.get(cur)
        if not isinstance(bucket, dict):
            return None
        amount = bucket.get("default")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return None
        return amount if amount > 0 else None

    # 2. flat float / numeric string
    if isinstance(price, bool):  # guard: bool is an int subclass
        return None
    try:
        amount = float(price)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _catalog_hit_fields(
    hit: Dict[str, Any], store: Dict[str, Any]
) -> Dict[str, Any]:
    """Per-store title / url / stock extraction for the explicit-key catalog
    stores (their field names differ from the 6thStreet shape)."""
    # title: sharafdg post_title, danube full_name_en, nahdi name, fallbacks.
    title = (
        hit.get("post_title")
        or hit.get("full_name_en")
        or hit.get("name")
        or hit.get("title")
        or ""
    ).strip()

    # url: sharafdg permalink, danube url_en (RELATIVE), nahdi url.
    url = (hit.get("permalink") or hit.get("url_en") or hit.get("url") or "").strip()
    host = store.get("host")
    if url and url.startswith("/") and host:
        url = f"{host}{url}"

    # stock: sharafdg in_stock 1/0, danube in_stock bool, nahdi no clean field.
    raw_stock = hit.get("in_stock")
    if raw_stock is None:
        in_stock = True  # nahdi has no clean stock field -> default True
    elif isinstance(raw_stock, str):
        in_stock = raw_stock.strip().lower() in ("1", "true", "yes", "in_stock")
    else:
        in_stock = bool(raw_stock)

    return {"title": title, "url": url, "in_stock": in_stock}


def _overlap_score(p_words: set, surface: str) -> float:
    """Fraction of query words present in `surface`, CONCATENATION-tolerant.

    The plain `len(p_words & t_words) / len(p_words)` floor wrongly drops a
    genuine hit when the index collapses a multi-word model name into one token:
    "Air Force 1" -> "AIRFORCE" makes only 1 of 4 query words match (0.25), even
    though the hit already PASSES strict_title_match + numbers_match. Here a query
    word counts as matched when it is a whole token OR a substring of the
    concatenated, separator-free surface ("air"/"force" both ⊂ "airforce..."),
    so the redundant overlap floor stops vetoing correct hits. No-fab is intact:
    the stronger gates (strict_title_match, numbers_match, counterfeit/accessory)
    still reject wrong models/brands before this score is ever consulted."""
    if not p_words:
        return 0.0
    t_words = normalize_words(surface)
    tnorm = "".join(t_words)
    matched = sum(1 for w in p_words if w in t_words or (w and w in tnorm))
    return matched / len(p_words)


def _catalog_match_hit(
    hits: List[Dict[str, Any]], product_name: str, store: Dict[str, Any],
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """STRICT title/brand best-match over catalog-store hits (per-store title
    fields + the pinned currency for price presence). Reuses the same gates as
    the 6thStreet path so a fuzzy cross-brand hit is REJECTED."""
    if not hits:
        return None
    p_words = normalize_words(product_name)
    currency = store.get("currency", "BHD")
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for hit in hits:
        if not isinstance(hit, dict):
            continue
        surface = _catalog_hit_fields(hit, store)["title"]
        if not surface:
            continue
        if is_counterfeit_listing(surface) or is_accessory(surface):
            continue
        if not numbers_match(product_name, surface):
            continue
        if not strict_title_match(product_name, surface):
            continue
        # Keystone variant-add guard (independent review CRITICAL) — strict_title_match is
        # SUBSET-based, so a token-ADD sibling (AirPods Pro->Pro 2, Aventus->Aventus Cologne)
        # passed it; the category-aware _selection_match rejects it. Pass the hit brand so a
        # brand word in the title ("Apple"/"Samsung") is stripped, not read as a variant-add.
        # Flag-safe (True when off).
        _cand_brand = str(hit.get("brand") or hit.get("brand_name") or hit.get("manufacturer") or "")
        if not _selection_match(product_name, surface, resolved_category, candidate_brand=_cand_brand):
            continue
        score = _overlap_score(p_words, surface)
        if score < 0.4:
            continue
        # Require a positive price (in the pinned currency) before considering.
        if _parse_algolia_price_multishape(hit, currency) is None:
            continue
        if score > best_score:
            best = hit
            best_score = score
    return best


def _hit_title(hit: Dict[str, Any]) -> str:
    """Build a match surface from name + brand so brand disambiguates a fuzzy
    name (Algolia returns 'TOMS' footwear for a 'Tom Ford' query — the brand
    field is what tells them apart)."""
    name = (hit.get("name") or hit.get("title") or "").strip()
    brand = (hit.get("brand_name") or hit.get("brand") or hit.get("main_brand") or "").strip()
    return f"{brand} {name}".strip()


def _match_algolia_hit(
    hits: List[Dict[str, Any]], product_name: str, resolved_category: Optional[str] = None,
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
        # Keystone variant-add guard (independent review CRITICAL) — see _catalog_match_hit.
        # candidate_brand strips a brand word in the surface (the surface IS brand+name, so
        # "Fenty Beauty"/"Nike" would otherwise read as variant-adds).
        _cand_brand = str(hit.get("brand_name") or hit.get("brand") or hit.get("main_brand") or "")
        if not _selection_match(product_name, surface, resolved_category, candidate_brand=_cand_brand):
            continue
        score = _overlap_score(p_words, surface)
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

    norm_domain = (domain or "").replace("www.", "").strip().lower()

    # R3c — EXPLICIT-KEY catalog stores (sharafdg BH/UAE, danube, nahdi). These
    # carry pinned config (no harvest) + a per-store currency + genuine flag, and
    # the GCC ones convert -> converted_usd.
    if norm_domain in ALGOLIA_EXPLICIT_STORES:
        return await _fetch_explicit_store_price(norm_domain, product_name, resolved_category=category)

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

    hit = _match_algolia_hit(hits, product_name, resolved_category=category)
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


def _content_safe(surface: str) -> bool:
    """Shared L2 content-safety gate. True (allow) on any check failure —
    best-effort, never block a clean price on the safety service erroring."""
    try:
        from app.services.content_safety_service import get_content_safety_service
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(surface):
            return False
    except Exception:  # noqa: BLE001
        return True
    return True


async def _fetch_explicit_store_price(
    domain: str, product_name: str, resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """R3c orchestrator for the EXPLICIT-KEY catalog stores. Queries with the
    pinned config, strict-matches, then stamps EITHER a genuine ``local_bhd``
    (native-BHD store) OR a converted ``converted_usd`` (GCC store → _convert_to_bhd).
    NEVER raises."""
    store = ALGOLIA_EXPLICIT_STORES.get(domain)
    if not store:
        return None

    hits = await _algolia_query_explicit(store, product_name)
    hit = _catalog_match_hit(hits, product_name, store, resolved_category=resolved_category)
    if not hit:
        return None

    src_currency = store.get("currency", "BHD")
    raw_amount = _parse_algolia_price_multishape(hit, src_currency)
    if raw_amount is None:
        return None

    fields = _catalog_hit_fields(hit, store)
    title = fields["title"]
    url = fields["url"] or (f"https://{domain}/" if domain else "")

    if store.get("genuine"):
        # Native BHD — fils precision (round to 3, not 2).
        amount_bhd = round(float(raw_amount), 3)
        source_method = "local_bhd"
        original_currency = None
    else:
        # GCC currency — convert. _convert_to_bhd returns the amount UNCHANGED
        # for an unknown currency; guard with FALLBACK_RATES membership so we
        # never label an unconvertible amount as BHD.
        from app.services.exchange_rate_service import FALLBACK_RATES
        if (src_currency or "").upper() not in FALLBACK_RATES:
            logger.info("[ALGOLIA] no rate for %s->BHD (%s) — dropping", src_currency, domain)
            return None
        converted = _convert_to_bhd(float(raw_amount), src_currency)
        if converted is None or converted <= 0:
            return None
        amount_bhd = round(float(converted), 3)
        source_method = "converted_usd"  # LITERAL — never a per-platform string
        original_currency = (src_currency or "").upper()

    price: Dict[str, Any] = {
        "amount": amount_bhd,
        "currency": "BHD",
        "retailer": domain,
        "url": url,
        "in_stock": fields["in_stock"],
        "estimated": False,
        "source_method": source_method,
        "title": title,
        "confidence": 0.9 if store.get("genuine") else 0.85,
    }
    if original_currency:
        price["original_currency"] = original_currency

    # Plausibility guard (low-fragrance/high-value/accessory/sample leaks).
    if not is_price_showable(product_name, price):
        logger.info("[ALGOLIA] explicit candidate not showable: %s %s", domain, title)
        return None

    # L2 content safety.
    if not _content_safe(f"{title} {domain} {product_name}"):
        logger.info("[ALGOLIA] explicit candidate dropped by content safety: %s", domain)
        return None

    return price
