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

candidate_brand (fix-ladder item 2 remainder, occ_service mirror): klinq/trikart expose a
custom `brand_name: String` HUMAN label ("Dior"/"Apple"); ajmal-kwt has NO queryable brand
field (mono-brand → pinned static "Ajmal"); Shape A carries brand generically in
`productView.attributes`. The label threads into strict_title_match + _selection_match so
a brand-omitting title ("Black Opium EDP") is recovered while a wrong-brand candidate
still rejects. Missing brand → "" → byte-identical legacy behaviour (fail-safe).

Returns a price dict or ``None``. NEVER raises — every network / parse error → None
(verify-or-omit). Gated by ENABLE_PAGE_SCRAPE + is_price_showable + L2 content-safety.
$0 — no Serper, no render.
"""
import json
import os
import re
import time
import logging
import asyncio
# Entity-decode at name ingestion (Wave C C2, kpiE2E RS-1 audit) — Magento
# stores product names HTML-escaped ("Black &amp; White"), the classic false
# "amp" identity-token class.
from html import unescape as html_unescape
from typing import Optional, Dict, Any, List

from app.services.price_service import (
    strict_title_match,
    _selection_match,
    selection_primary_admits,
    build_adapter_search_terms,
    numbers_match,
    normalize_words,
    variant_mismatch,
    is_counterfeit_listing,
    is_accessory_for_category,
    is_price_showable,
    exact_gate_enabled,
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
    # `brand_field` = the store's HUMAN-label brand field, spliced into the query
    # per-store ONLY (an unknown GraphQL field is a VALIDATION error that kills
    # the whole query — proven live on ajmal). NEVER pin the option-id fields
    # (klinq `brand`="743", `mgs_brand`). `static_brand` = mono-brand store pin.
    "klinq.com": {"shape": "B", "store_view": "default",
                  "brand_field": "brand_name"},                     # native BHD
    "trikart.com": {"shape": "B", "store_view": "kwt_en",
                    "brand_field": "brand_name"},                   # KWD → convert
    "en-kwt.ajmal.com": {"shape": "B", "store_view": "default",
                         "static_brand": "Ajmal"},                  # KWD → convert
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
# `attributes(roles: [])` is on the ProductView INTERFACE (no per-name filter
# exists — the arg filters by roles); the full list carries the generic
# {name:"brand", value:"Bath & Body Works"} entry, a few KB at pageSize 5.
# Built from a template (Shape-B __BRAND_SEL__ mirror) so the attrs-free
# FALLBACK query stays byte-identical modulo the attributes selection: the
# field is live-proven on www.footlocker.com.bh (2026-07-02 probe: HTTP 200, no
# errors[], 5 nodes, brand="Nike", genuine BHD) but NOT schema-guaranteed
# across all 6 Alshaya tenants — an older Catalog Service rejects it with a
# VALIDATION error (errors[] + no data) that kills the whole query, silently
# reverting the store to built-but-dead. See _shape_a_attrs_rejected.
_SHAPE_A_QUERY_TEMPLATE = """
query($phrase: String!, $pageSize: Int!) {
  productSearch(phrase: $phrase, page_size: $pageSize) {
    items {
      productView {
        name
        sku
        urlKey
        inStock
        __typename__ATTRS_SEL__
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

_SHAPE_A_QUERY = _SHAPE_A_QUERY_TEMPLATE.replace(
    "__ATTRS_SEL__", "\n        attributes(roles: []) { name value }"
)
_SHAPE_A_QUERY_NO_ATTRS = _SHAPE_A_QUERY_TEMPLATE.replace("__ATTRS_SEL__", "")

# Shape B — vanilla Magento core search. Built per-store: the pinned brand
# field is spliced in at __BRAND_SEL__ ONLY when the store has one (an unknown
# field is a validation error with NO data — the shared query must stay
# brand-free for unpinned stores).
_SHAPE_B_QUERY_TEMPLATE = """
query($phrase: String!, $pageSize: Int!) {
  products(search: $phrase, pageSize: $pageSize) {
    items {
      name
      sku
      url_key
      stock_status__BRAND_SEL__
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


def _build_shape_b_query(brand_field: Optional[str] = None) -> str:
    """Shape-B products query with the per-store pinned brand field spliced into
    the items selection. No pin → byte-identical legacy query."""
    brand_sel = f"\n      {brand_field}" if brand_field else ""
    return _SHAPE_B_QUERY_TEMPLATE.replace("__BRAND_SEL__", brand_sel)


# ---------------------------------------------------------------------------
# UNIT B3 — Shape C: URL-driven url_key filter lookup (ENABLE_MAGENTO_GQL_ADAPTER)
# ---------------------------------------------------------------------------
# Unlike Shape A/B (a phrase productSearch keyed by category→host discovery),
# Shape C is driven by a PDP URL: the last path segment (minus ``.html``) is the
# Magento ``url_key``, and ``products(filter:{url_key:{eq:...}})`` returns the ONE
# matching product's final_price + regular_price + currency in a single POST.
# B4 measured this live 3/3 on cached-free hosts — arenal.com 51.45/105 EUR,
# jomashop.com 46.99 USD, pacoperfumerias.co.uk 42.5/89 GBP — and on jomashop it
# walks straight past the Cloudflare wall that 403s the HTML PDP route. So it is
# wired as a FALLBACK adapter in the page-scrape cascade (fetch_page_price): when
# the HTML route yields no price for a pinned Magento host, this recovers it.


def magento_gql_adapter_enabled() -> bool:
    """True iff the URL-driven Magento GraphQL url_key adapter is active
    (UNIT B3, default OFF).

    This is a NEW capture capability (a url_key GraphQL side-door that recovers
    the price on a Cloudflare-walled HTML PDP — measured live on jomashop.com),
    not a repair of a measured-0%-success production path, so it ships DARK and
    is flipped on Railway during canary (contrast ENABLE_FIRECRAWL_RAW_HTML, which
    repaired a live 0/9 path and justified default-ON). Read PER CALL from
    ``os.getenv`` (copying ``price_service.exact_gate_enabled``) so the flag can
    be flipped without a restart. With the flag OFF the fallback never fires — the
    POST is never issued — so ``fetch_page_price`` returns its exact pre-B3 value
    and the rollback is byte-identical."""
    return os.getenv("ENABLE_MAGENTO_GQL_ADAPTER", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


# Hosts (www-stripped apex) known to answer the url_key filter shape. Pinned so
# the fallback never blind-POSTs ``/graphql`` at an arbitrary Serper-discovered
# host — the exact same host-pin discipline as _MAGENTO_STORES. All three were
# measured live 3/3 by B4.
_MAGENTO_GQL_URLKEY_HOSTS: frozenset = frozenset({
    "arenal.com",
    "jomashop.com",
    "pacoperfumerias.co.uk",
})

# Shape C — url_key filter. The price_range shape is IDENTICAL to Shape B's
# minimum_price.final_price/regular_price, so _shape_b_items / _shape_b_price_node
# parse it unchanged. ``$urlKey`` is a typed String! variable (Shape B already
# uses a $phrase variable via _post_graphql), so no query-string interpolation.
_SHAPE_C_URLKEY_QUERY = """
query($urlKey: String!) {
  products(filter: { url_key: { eq: $urlKey } }) {
    total_count
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


def _url_key_from_url(url: str) -> str:
    """Derive the Magento ``url_key`` from a PDP URL: the last non-empty path
    segment, minus a trailing ``.html`` (the Magento product-url convention).
    Query string, fragment and a trailing slash are dropped. Returns "" when no
    path segment exists (→ the caller emits no POST)."""
    from urllib.parse import urlparse, unquote
    path = urlparse(url or "").path or ""
    segs = [s for s in path.split("/") if s]
    if not segs:
        return ""
    seg = unquote(segs[-1])
    if seg.lower().endswith(".html"):
        seg = seg[: -len(".html")]
    return seg


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

# A5 (genuine-price KPI, 2026-07-02) — Alshaya Shape-A FASHION names omit the
# colorway; it survives only as the urlKey tail ("...-white-white"). The KPI
# colorway axis + strict_title_match REJECT a colourless title for a
# colour-stated query ("Nike Air Force 1 07 White"), so the tail is humanized
# and appended before matching. BOUNDED: only these recognized colour words are
# ever promoted — an arbitrary slug tail (gender/fit/pack words, SKU digits)
# never is.
_URLKEY_COLOUR_WORDS = frozenset({
    "black", "white", "grey", "gray", "red", "blue", "navy", "green", "olive",
    "yellow", "gold", "silver", "beige", "brown", "tan", "cream", "pink",
    "purple", "orange", "khaki", "maroon", "burgundy", "teal", "ivory",
    "charcoal",
})


def _urlkey_colour_tail(url_key: str) -> List[str]:
    """The TRAILING run of recognized colour words in a Shape-A urlKey slug
    ("buy-nike-air-force-1-07-mens-shoes-white-white" -> ["white"]), slug order,
    deduped. The walk stops at the first non-colour token from the END — a
    colour ELSEWHERE in the slug ("...-white-gum") is not a colorway tail.
    [] when the slug does not end in a colour word."""
    toks = [t for t in (url_key or "").lower().split("-") if t]
    run: List[str] = []
    for tok in reversed(toks):
        if tok not in _URLKEY_COLOUR_WORDS:
            break
        run.append(tok)
    run.reverse()  # restore slug order
    seen: set = set()
    return [t for t in run if not (t in seen or seen.add(t))]


def _with_colour_tail(name: str, url_key: str) -> str:
    """`name` with the urlKey colour tail appended (Title-case) when the name
    lacks it; a name already carrying the colour is returned unchanged."""
    tail = _urlkey_colour_tail(url_key)
    if not name or not tail:
        return name
    have = set(re.findall(r"[a-z]+", name.lower()))
    if have & {"grey", "gray"}:  # spelling variants suppress each other
        have |= {"grey", "gray"}
    missing = [t for t in tail if t not in have]
    if not missing:
        return name
    return name + " " + " ".join(t.capitalize() for t in missing)


def _shape_a_items(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or {}
    ps = data.get("productSearch") or {}
    items = ps.get("items")
    return items if isinstance(items, list) else []


def _shape_a_attrs_rejected(payload: Any) -> bool:
    """True iff the GraphQL response carries a validation errors[] entry that
    mentions the `attributes` field — the class where an older Catalog-Service
    tenant rejects `attributes(roles: [])` and the WHOLE query dies (no data
    comes back with a validation error). The caller re-POSTs ONCE with
    _SHAPE_A_QUERY_NO_ATTRS (brand="" legacy path). Deliberately NARROW: an
    unrelated error / clean response / non-dict never triggers the re-POST."""
    if not isinstance(payload, dict):
        return False
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return False
    for e in errors:
        msg = e.get("message") if isinstance(e, dict) else e
        if isinstance(msg, str) and "attributes" in msg.lower():
            return True
    return False


def _shape_a_price_node(pv: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract {value, currency, in_stock, name, url_key, brand} from a Shape-A
    productView, branching by __typename. Returns None on any missing field.
    Brand comes from the generic Catalog-Service attributes entry name=="brand";
    absence tolerated (brand="" → legacy matching)."""
    typename = pv.get("__typename") or ""
    # Entity-decode (C2) — the node name is BOTH the match surface and the
    # stamped title; no-op on entity-free names.
    name = html_unescape(pv.get("name") or "")
    url_key = pv.get("urlKey") or ""
    in_stock = bool(pv.get("inStock", True))
    brand = ""
    attrs = pv.get("attributes")
    if isinstance(attrs, list):
        for a in attrs:
            if isinstance(a, dict) and a.get("name") == "brand":
                brand = str(a.get("value") or "").strip()
                break
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
        "brand": brand,
    }


def _shape_b_items(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or {}
    products = data.get("products") or {}
    items = products.get("items")
    return items if isinstance(items, list) else []


def _shape_b_price_node(
    item: Dict[str, Any], brand_field: Optional[str] = None, static_brand: str = "",
) -> Optional[Dict[str, Any]]:
    # Entity-decode (C2) — see _shape_a_price_node.
    name = html_unescape(item.get("name") or "")
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
    # Brand label for candidate_brand threading — ONLY the per-store pinned
    # human-label field (klinq/trikart `brand_name`), NEVER the option-id
    # fields (`brand`="743"/5479, `mgs_brand`). Mono-brand store → static pin.
    if brand_field:
        brand = str(item.get(brand_field) or "").strip()
    else:
        brand = static_brand
    return {
        "value": value,
        "currency": str(currency).upper(),
        "in_stock": in_stock,
        "name": name,
        "url_key": url_key,
        "brand": brand,
    }


# ---------------------------------------------------------------------------
# Strict matching (reuse the price_service gates)
# ---------------------------------------------------------------------------

def _best_match(
    nodes: List[Dict[str, Any]], product_name: str, resolved_category=None,
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
        # Accessory check category-scoped (C2, kpiE2E RS-4) — magento was the
        # one direct store-API chain still on the broad is_accessory (BF4
        # scoped occ/woo/salla/algolia x2/unbxd): a godukkan-class Magento
        # laptop row ("... English Keyboard Sky Blue") was accessory-rejected
        # on its layout segment. Same scoping as the other five chains.
        if is_counterfeit_listing(title) or is_accessory_for_category(
                title, resolved_category):
            continue
        if not numbers_match(product_name, title):
            continue
        # KEYSTONE candidate_brand (occ_service mirror) — the store's own brand
        # label lets a brand-omitting title ("Black Opium EDP") pass, while a
        # wrong-brand node keeps the query brand required (candidate_brand only
        # drops the CANDIDATE's own tokens; _selection_match vets the full SKU
        # alongside). Missing brand → "" → legacy behaviour.
        _cand_brand = str(node.get("brand") or "").strip()
        # SELECTION-PRIMARY acceptance (recon_cascade R2, Wave B4): a strict
        # FAIL no longer hard-rejects — the klinq class ("Black Opium Eau De
        # Parfum 90 ml" under a spelled-brand node) fails strict on the raw
        # "90ml"/brand-alias tokens while _selection_match(candidate_brand=)
        # below vets the full SKU via the alias-folding identity sets. The
        # variant / selection / word-overlap gates still run — the fallthrough
        # GATED by selection_primary_admits (Wave B-FIX wrong-brand fence: a
        # node whose OWN brand contradicts a padding-brand query — Golden
        # Goose "Superstar" under an "Adidas Superstar" query — hard-rejects).
        # Flag OFF (or exact gate OFF) restores the exact pre-change hard gate.
        if (not strict_title_match(product_name, title, candidate_brand=_cand_brand)
                and not selection_primary_admits(
                    product_name, title, candidate_brand=_cand_brand,
                    category=resolved_category)):
            continue
        if variant_mismatch(product_name, title):
            continue
        if not _selection_match(product_name, title, resolved_category,
                                candidate_brand=_cand_brand):
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
    resolved_category: Optional[str] = None,
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
    if not store and ("www." + host) in _MAGENTO_STORES:
        # Registry rows are stored APEX (source_router._normalize_domain
        # www-strips hosts, so a "www." row can never score/tier); the Shape-A
        # pins are keyed by the canonical www host — re-canonicalize so config
        # GETs / PDP urls / the retailer stamp all carry the real storefront.
        host = "www." + host
        store = _MAGENTO_STORES.get(host)
    if not store:
        return None
    shape = store.get("shape")

    # --- resolve the node (value/currency/name/url_key/in_stock) per shape ---
    node: Optional[Dict[str, Any]] = None
    pdp_url = ""

    # R1 retrieval-term ladder: the full phrase first; ONLY a zero-item
    # response retries ONCE with the model-core term (klinq resolves "Black
    # Opium" where the full canonical name returns 0 items). Rows returned —
    # matched or not — never trigger a second search term. Matching below runs
    # against the ORIGINAL product_name, so wider retrieval cannot widen
    # acceptance.
    terms = build_adapter_search_terms(product_name, resolved_category)

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
        payload = None
        for term in terms:
            payload = await _post_graphql(
                cfg["endpoint"], _SHAPE_A_QUERY,
                {"phrase": term, "pageSize": _PAGE_SIZE}, headers,
            )
            # Wave B2 — attributes-rejecting tenant: re-POST ONCE (same term)
            # without the attributes selection (brand="" legacy matching), so a
            # Catalog-Service schema drift can never silently kill the whole
            # store again. Orthogonal to the ladder (a schema retry, not a
            # search-term retry).
            if _shape_a_attrs_rejected(payload):
                logger.info(
                    "[MAGENTO] %s rejected attributes selection — retrying attrs-free",
                    host,
                )
                payload = await _post_graphql(
                    cfg["endpoint"], _SHAPE_A_QUERY_NO_ATTRS,
                    {"phrase": term, "pageSize": _PAGE_SIZE}, headers,
                )
            # F2 politeness (Wave B-FIX): a TRANSPORT failure (_post_graphql
            # -> None on non-200/exception/non-JSON) must NOT ladder — only a
            # genuine ZERO-ROW response retries the core term (woo/salla
            # semantics: no second request against an erroring store).
            if payload is None:
                break
            if _shape_a_items(payload):
                break  # rows returned (even unmatched) — never a second term
        items = _shape_a_items(payload)
        nodes = [
            n for n in (
                _shape_a_price_node(it.get("productView") or {})
                for it in items if isinstance(it, dict)
            ) if n
        ]
        # A5 — fashion colorway enrichment (see _with_colour_tail), applied
        # BEFORE matching so the colorway axis can discriminate AND the enriched
        # title is what gets stored/cached. Fashion-scoped: a colour word can be
        # product identity elsewhere (fragrances "Black Opium").
        if resolved_category == "fashion":
            nodes = [
                dict(n, name=_with_colour_tail(n.get("name") or "", n.get("url_key") or ""))
                for n in nodes
            ]
        node = _best_match(nodes, product_name, resolved_category=resolved_category)
        if node:
            base = (cfg.get("base_endpoint") or f"https://{host}").rstrip("/")
            # A5 — Alshaya PDPs live ONLY under the /en/ locale: the bare
            # {base}/{urlKey} serves a ~3.4KB SPA stub (no og:title/JSON-LD).
            # All 6 Shape-A storefront roots 301 to /en/ (live-verified
            # 2026-07-02; footlocker /en/ PDP = the real 200 page).
            if not base.endswith("/en"):
                base = f"{base}/en"
            pdp_url = f"{base}/{node.get('url_key', '').lstrip('/')}"

    elif shape == "B":
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Store": store.get("store_view", "default"),
        }
        payload = None
        for term in terms:
            payload = await _post_graphql(
                f"https://{host}/graphql", _build_shape_b_query(store.get("brand_field")),
                {"phrase": term, "pageSize": _PAGE_SIZE}, headers,
            )
            # F2 politeness (Wave B-FIX): transport failure (None) never
            # ladders — only a genuine zero-row response retries the core term.
            if payload is None:
                break
            if _shape_b_items(payload):
                break  # rows returned (even unmatched) — never a second term
        items = _shape_b_items(payload)
        nodes = [
            n for n in (
                _shape_b_price_node(
                    it,
                    brand_field=store.get("brand_field"),
                    static_brand=store.get("static_brand", ""),
                )
                for it in items if isinstance(it, dict)
            ) if n
        ]
        node = _best_match(nodes, product_name, resolved_category=resolved_category)
        if node:
            # Shape-B PDP url REQUIRES a .html suffix (klinq bare path 302s away).
            pdp_url = f"https://{host}/{node.get('url_key', '').lstrip('/')}.html"
    else:
        return None

    if not node:
        return None

    return _finalize_magento_price(node, host, pdp_url, product_name, currency)


def _finalize_magento_price(
    node: Dict[str, Any], host: str, pdp_url: str,
    product_name: str, currency: str,
) -> Optional[Dict[str, Any]]:
    """Thread a matched Shape-A/B/C node through the shared genuine-vs-converted
    currency-label + identity-stamp + plausibility + content-safety machinery →
    the standard price dict (or None). Extracted VERBATIM from the Shape-A/B tail
    so the URL-driven Shape-C adapter (UNIT B3) reuses the exact same contract —
    genuine BHD → ``magento_graphql_bhd`` (7d TTL), any other rated GCC currency →
    ``_convert_to_bhd`` + the literal ``converted_usd`` with ``original_currency``
    carried, an un-rated currency dropped (never a 1:1 BHD relabel)."""
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

    # Wave-B identity stamp (review HIGH; PR#13 JSON-LD precedent) — carry the
    # matched node's brand (A4 put it on the node for both shapes) onto the
    # price dict, so select_best / should_cache_price can replay the same
    # candidate_brand-aware match that accepted a brand-omitting title
    # ("Black Opium Eau De Parfum 90ml" @ klinq). Empty -> omitted (legacy
    # shape). Flag-gated for flag-OFF byte-identity, matching the precedent.
    if exact_gate_enabled():
        node_brand = node.get("brand")
        if isinstance(node_brand, str) and node_brand.strip():
            price["brand"] = node_brand.strip()

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


async def fetch_magento_graphql_url_price(
    url: str, product_name: str, currency: str = "BHD",
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """UNIT B3 — URL-driven Magento/Adobe-Commerce price via the url_key filter.

    Given a PDP ``url`` on a pinned Magento host, derive the ``url_key`` (last
    path segment minus ``.html``) and POST
    ``products(filter:{url_key:{eq:...}})`` → the single matching product's
    final_price + regular_price + currency in ONE call. On jomashop this walks
    past the Cloudflare wall that 403s the HTML PDP route (B4, measured live 3/3).

    Wired as a FALLBACK adapter in ``fetch_page_price``: it fires ONLY when
    ``magento_gql_adapter_enabled()`` (ENABLE_MAGENTO_GQL_ADAPTER, default OFF)
    AND the host is one of ``_MAGENTO_GQL_URLKEY_HOSTS``. Returns a price dict or
    ``None`` on miss / wrong-brand-only / non-pinned host / flag-OFF / error.
    NEVER raises."""
    if not (ENABLE_PAGE_SCRAPE and magento_gql_adapter_enabled()):
        return None

    host = (url or "").strip()
    if host.startswith("http://"):
        host = host[7:]
    elif host.startswith("https://"):
        host = host[8:]
    host = host.split("/")[0].split("?")[0].lower()
    apex = host[4:] if host.startswith("www.") else host
    if apex not in _MAGENTO_GQL_URLKEY_HOSTS:
        return None

    url_key = _url_key_from_url(url)
    if not url_key:
        return None

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = await _post_graphql(
        f"https://{host}/graphql", _SHAPE_C_URLKEY_QUERY, {"urlKey": url_key}, headers,
    )
    # Reuse the Shape-B parser — the price_range.minimum_price shape is identical.
    # No brand_field (these are multi-brand storefronts, not own-brand stores), so
    # brand="" → legacy strict matching.
    nodes = [
        n for n in (
            _shape_b_price_node(it)
            for it in _shape_b_items(payload) if isinstance(it, dict)
        ) if n
    ]
    node = _best_match(nodes, product_name, resolved_category=resolved_category)
    if not node:
        return None

    return _finalize_magento_price(node, host, url, product_name, currency)
