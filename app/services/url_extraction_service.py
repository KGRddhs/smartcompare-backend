"""
URL Extraction Service - Scrape and extract product data from retailer URLs
Supports major GCC retailers: Amazon, Noon, Carrefour, Sharaf DG, Lulu, etc.
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import re
import json
import logging
import string
import httpx
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urljoin, urlsplit
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from app.services.llm_provider import provider_base_url
from app.services.model_config import sampling_kwargs, standard_model, token_limit_kwargs

from app.services.extraction_service import canonicalize_category
from app.services import api_budget_service as _llm_breaker

logger = logging.getLogger(__name__)

# Lazy OpenAI client
_client = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        from app.services.model_config import openai_max_retries
        _client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=provider_base_url(),
            timeout=httpx.Timeout(120.0, connect=30.0),
            # #265 (A-C11) — OPENAI_MAX_RETRIES (default 2 == SDK default), read
            # at first construction and cached with the client, exactly like
            # extraction_service.get_client.
            max_retries=openai_max_retries(),
        )
    return _client


# ============================================
# RETAILER DETECTION
# ============================================

SUPPORTED_RETAILERS = {
    "amazon.ae": {"name": "Amazon UAE", "region": "uae", "currency": "AED"},
    "amazon.sa": {"name": "Amazon Saudi", "region": "saudi_arabia", "currency": "SAR"},
    "amazon.com": {"name": "Amazon US", "region": "us", "currency": "USD"},
    "noon.com": {"name": "Noon", "region": "uae", "currency": "AED"},
    "carrefour": {"name": "Carrefour", "region": "bahrain", "currency": "BHD"},
    "sharafdg.com": {"name": "Sharaf DG", "region": "uae", "currency": "AED"},
    "luluhypermarket": {"name": "Lulu Hypermarket", "region": "bahrain", "currency": "BHD"},
    "extra.com": {"name": "Extra Stores", "region": "saudi_arabia", "currency": "SAR"},
    "jarir.com": {"name": "Jarir Bookstore", "region": "saudi_arabia", "currency": "SAR"},
    "xcite.com": {"name": "Xcite Kuwait", "region": "kuwait", "currency": "KWD"},
}


def detect_retailer(url: str) -> Optional[Dict[str, Any]]:
    """Detect retailer from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    
    for key, info in SUPPORTED_RETAILERS.items():
        if key in domain:
            return {
                "key": key,
                "domain": domain,
                **info
            }
    
    # Unknown retailer - still try to scrape
    return {
        "key": "unknown",
        "domain": domain,
        "name": domain,
        "region": "unknown",
        "currency": "USD"
    }


# ============================================
# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2)
# ============================================
# Default OFF. The ROUTE reads the flag ONCE per request and threads a bool down
# (`url_mode_v2=True`, a conditional kwarg), so one request never mixes states and
# nothing below runs, imports price_service or reads the env on the flag-OFF path.
# Spec .qa-s80/B4_UNIT_SPEC.md (session 80), rulings B4-R1..R11, RED gate GC-1..GC-8.

# Copy constants (Build Principle #4: calm, no "couldn't" / "try again" / "Failed to").
NOT_PRODUCT_PAGE_MESSAGE = (
    "That link opens a store page, not a product page. Paste the product's own page link."
)
STORE_UNREADABLE_MESSAGE = (
    "That store does not let us read its pages. Paste a link from another store, "
    "or type the product name."
)
UNRESOLVED_PRODUCT_MESSAGE = (
    "We did not find a product on that page. Paste the product's own page link."
)

# Test seam: the httpx transport of the v2 fetch (production None = httpx's own
# default transport). fetch_page (the flag-OFF fetch) never reads it.
_TRANSPORT = None


def url_mode_v2_enabled() -> bool:
    """ENABLE_URL_MODE_V2 (B4, default OFF), the house idiom, read PER CALL."""
    return os.getenv("ENABLE_URL_MODE_V2", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _host_only(u: Any) -> str:
    """The hostname of a pasted link for a log line, never its path or query.
    '' for a non-str or malformed link: never raises (the _url_log_query shape)."""
    try:
        return urlsplit(u if isinstance(u, str) else "").hostname or ""
    except ValueError:
        return ""


def _retailer_log_name(retailer: Any) -> str:
    """A log-safe retailer label: a SUPPORTED_RETAILERS name (a constant), else
    'unknown' (an unknown retailer's `name` is the raw netloc, which can carry a
    pasted `user:pass@`)."""
    if isinstance(retailer, dict) and retailer.get("key") in SUPPORTED_RETAILERS:
        return str(retailer.get("name") or "unknown")
    return "unknown"


def normalize_url_for_same_check(u: Any, *, pairs: Optional[List[Tuple[str, str]]] = None) -> str:
    """The url1 == url2 key of the pre-gate: scheme and host casefolded, ONE
    leading 'www.' dropped, an explicit port kept, ONE trailing '/' dropped (the
    root becomes ''), path case and percent-encoding kept, the fragment and every
    query key dropped EXCEPT the product-route keys and their values (RULINGS_FIX3_B4
    F3-1: route=product/product, product_id, id_product, product, products_id; keys
    case-insensitive, values percent-decoded and stripped, sorted), so two products
    of one query-routed store are not the same url. '' for a non-str or malformed
    link (never raises); the caller never treats two '' as the same url.
    ``pairs`` (RULINGS_FIX4_B4 F4-1): the link's already parsed product-route pairs
    (url_pre_gate_view), so the query is not parsed a second time."""
    try:
        parts = urlsplit(u if isinstance(u, str) else "")
        port = parts.port  # ValueError on a malformed port
    except ValueError:
        return ""
    host = (parts.hostname or "").casefold()
    if not parts.scheme or not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path[:-1] if parts.path.endswith("/") else parts.path
    key = f"{parts.scheme.casefold()}://{netloc}{path}"
    if pairs is None:
        pairs = _product_route_pairs(parts.query, _SAME_URL_PRODUCT_QUERY_KEYS)
    return key + "?" + urlencode(pairs) if pairs else key


# Pre-gate path classes beyond price_service's storefront-root / search pair
# (reused, never copied). PATH-anchored with an optional `xx/` or `xx-yy/` locale
# segment, re.I; the query string is never read (R-A7 is path-only) except for the
# product-route exemption of the homepage class below (F2-1).
_URL_CART_PATH_RE = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:cart|basket|checkouts?)(?:/|$)", re.I,
)
_URL_ACCOUNT_PATH_RE = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:account|accounts|my-account|login|signin|sign-in"
    r"|register|signup|sign-up|customer/account)(?:/|$)", re.I,
)
_URL_CATEGORY_PATH_RE = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:collections?|category|categories|c|brands?)(?:/|$)",
    re.I,
)
# A product segment anywhere in the path vetoes the category class
# (`/collections/men/products/sauvage` is a Shopify PDP).
_URL_PRODUCT_SEGMENT_RE = re.compile(r"/(?:products?|p|dp|item)/|/-/p", re.I)
# RULINGS_FIX2_B4 F2-1: the one exception to "the query is never read". A root or
# /index.* path whose query names a PRODUCT ROUTE is not the homepage (OpenCart
# index.php?route=product/product&product_id=N, PrestaShop id_product, WooCommerce
# /?product=<slug>). Keys compared case-insensitively; an explicit allow-list, never
# "any non-empty query" (tracking-only queries stay homepage). A bare `p` (a
# WordPress post id) is deliberately absent.
# RULINGS_FIX4_B4 F4-3: the osCommerce / Zen Cart products_id is a product-route
# marker too (Zen Cart's default PDP is index.php?main_page=product_info&products_id=N).
_PRODUCT_ROUTE_QUERY_KEYS = frozenset({"product_id", "id_product", "product", "products_id"})
# RULINGS_FIX3_B4 F3-1: the same-url key keeps these keys plus osCommerce
# products_id (since F4-3 the two sets are equal); an ASP.NET `pid` is generic (a
# WordPress post or page id) and stays out.
_SAME_URL_PRODUCT_QUERY_KEYS = _PRODUCT_ROUTE_QUERY_KEYS | {"products_id"}
# F3-2: OpenCart's one product-page route; listing routes (product/category,
# product/search, product/compare, ...) are not product routes.
_OPENCART_PRODUCT_ROUTE = "product/product"


def _product_route_pairs(query: str, keys: frozenset) -> List[Tuple[str, str]]:
    """The product-route markers of a query, sorted: (key lower-cased, value
    percent-decoded and stripped) for a key in ``keys`` with a NON-EMPTY value
    (F3-4), and ("route", "product/product") for an OpenCart route whose value is
    exactly product/product, case-insensitive (F3-2), de-duplicated. Every other
    key is dropped."""
    pairs = []
    for key, values in parse_qs(query, keep_blank_values=True).items():
        k = key.lower()
        for value in values:
            v = value.strip()
            if k == "route":
                if v.lower() == _OPENCART_PRODUCT_ROUTE:
                    pairs.append((k, _OPENCART_PRODUCT_ROUTE))
            elif k in keys and v:
                pairs.append((k, v))
    return sorted(set(pairs))


def _query_names_a_product_route(query: str) -> bool:
    """True when the query carries a product-route marker (F2-1 allow-list, as
    narrowed by F3-2 and F3-4)."""
    return bool(_product_route_pairs(query, _PRODUCT_ROUTE_QUERY_KEYS))


def classify_url_path(u: Any, *, pairs: Optional[List[Tuple[str, str]]] = None) -> Optional[str]:
    """'homepage' | 'search' | 'cart' | 'account' | 'category' for a link whose
    PATH is a storefront page, else None (the query is ignored, except that a root
    or /index.* path whose query names a product route is not the homepage, F2-1).
    Checkout routes are the 'cart' class. A falsy, non-str or malformed link is
    None (GC-4: the route only ever passes the pydantic str fields). ``pairs``
    (RULINGS_FIX4_B4 F4-1): the link's already parsed product-route pairs
    (url_pre_gate_view), so the query is not parsed a second time."""
    if not isinstance(u, str) or not u:
        return None
    try:
        parts = urlsplit(u)
    except ValueError:
        return None
    path = parts.path
    from app.services.price_service import (
        _NOT_A_PDP_HOME_PATH_RE,
        _NOT_A_PDP_SEARCH_PATH_RE,
    )
    if _NOT_A_PDP_HOME_PATH_RE.match(path) and not (
            _query_names_a_product_route(parts.query) if pairs is None else pairs):
        return "homepage"
    if _NOT_A_PDP_SEARCH_PATH_RE.match(path):
        return "search"
    if _URL_CART_PATH_RE.match(path):
        return "cart"
    if _URL_ACCOUNT_PATH_RE.match(path):
        return "account"
    if _URL_CATEGORY_PATH_RE.match(path) and not _URL_PRODUCT_SEGMENT_RE.search(path):
        return "category"
    return None


def url_pre_gate_view(u: Any) -> Tuple[Optional[str], str]:
    """RULINGS_FIX4_B4 F4-1: (classify_url_path(u), normalize_url_for_same_check(u))
    with the link's query parsed ONCE: one _product_route_pairs call feeds both the
    homepage exemption and the same-url key. The flagged pre-gate
    (url_routes._url_pre_gate) calls it only on a link it has already bounded to
    the client's 2,048 characters. Never raises (a malformed link has no query)."""
    try:
        query = urlsplit(u).query if isinstance(u, str) else ""
    except ValueError:
        query = ""
    pairs = _product_route_pairs(query, _SAME_URL_PRODUCT_QUERY_KEYS)
    route_pairs = [p for p in pairs if p[0] == "route" or p[0] in _PRODUCT_ROUTE_QUERY_KEYS]
    return (classify_url_path(u, pairs=route_pairs),
            normalize_url_for_same_check(u, pairs=pairs))


# The first <title> of a page, read with str.find only (no soup: the v2 fetch
# outcome is decided in an `async def`, ruling B4-R2; no regex: a lazy group over
# the window was quadratic on a crafted '<title ' flood, RULINGS_FIX2_B4 F2-2).
_V2_TITLE_WINDOW = 65536
_V2_TITLE_MAX_CHARS = 1024  # the text read after an opener with no close tag
_V2_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_V2_CHALLENGE_TITLE_PREFIXES = (
    "just a moment", "attention required", "access denied", "checking your browser",
    "please verify you are a human", "verify you are human", "enable javascript and cookies",
)


def _v2_first_title(html: str) -> Optional[str]:
    """The text of the FIRST <title> element in html[:65536] (opener matched
    ASCII-case-insensitively, followed by '>' or whitespace, attributes allowed),
    up to the first '</title' followed by optional whitespace and '>'; with no
    such close tag, at most _V2_TITLE_MAX_CHARS characters after the opener.
    None when there is no opener or the opener never ends with '>'. Linear: one
    pass of str.find per search (the translate keeps every index)."""
    window = html[:_V2_TITLE_WINDOW]
    lower = window.translate(_V2_ASCII_LOWER)
    start = 0
    while True:
        i = lower.find("<title", start)
        if i < 0:
            return None
        j = i + 6
        if j < len(lower) and (lower[j] == ">" or lower[j].isspace()):
            break
        start = j
    gt = lower.find(">", j)
    if gt < 0:
        return None
    pos = gt + 1
    while True:
        end = lower.find("</title", pos)
        if end < 0:
            return window[gt + 1:gt + 1 + _V2_TITLE_MAX_CHARS]
        k = end + 7
        while k < len(lower) and lower[k].isspace():
            k += 1
        if k < len(lower) and lower[k] == ">":
            return window[gt + 1:end]
        pos = k


def _is_challenge_page(html: Any) -> bool:
    """A bot-challenge / wall page, judged on the START of its <title> only (never a
    body substring: 'Access denied' in a reviews widget is not a wall)."""
    if not isinstance(html, str):
        return False
    title = _v2_first_title(html)
    if title is None:
        return False
    return title.strip().casefold().startswith(_V2_CHALLENGE_TITLE_PREFIXES)


_ASCII_PUNCTUATION = str.maketrans("", "", string.punctuation)


def _title_key(value: Any) -> str:
    """Casefolded, ASCII punctuation removed, whitespace collapsed; '' for a non-str."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.casefold().translate(_ASCII_PUNCTUATION).split())


_PLACEHOLDER_TITLE_KEYS = frozenset(
    _title_key(t) for t in ("", "unknown", "unknown product", "n/a", "product", "this product")
)
# The schema.org nodes whose `name` is the SITE's name (plus og:site_name). Not
# WebPage: a WebPage node names the page itself, and on a PDP without Product
# schema it often equals the <title>, which must stay usable.
_V2_SITE_NAME_TYPES = frozenset({"Organization", "WebSite"})


def _v2_site_names(json_ld_items: Any, meta: Any) -> set:
    """The title keys of the site's own name: every Organization / WebSite node
    (`@type` str or list, top level or inside `@graph`) plus og:site_name."""
    names = set()

    def visit(node: Any, depth: int) -> None:
        if depth > 4:
            return
        if isinstance(node, list):
            for item in node:
                visit(item, depth + 1)
            return
        if not isinstance(node, dict):
            return
        types = node.get("@type")
        types = [types] if isinstance(types, str) else (types if isinstance(types, list) else [])
        if any(isinstance(t, str) and t in _V2_SITE_NAME_TYPES for t in types):
            key = _title_key(node.get("name"))
            if key:
                names.add(key)
        if isinstance(node.get("@graph"), (list, dict)):
            visit(node["@graph"], depth + 1)

    visit(json_ld_items if isinstance(json_ld_items, list) else [], 0)
    site = meta.get("og_site_name") if isinstance(meta, dict) else None
    key = _title_key(site)
    if key:
        names.add(key)
    return names


def is_usable_title(title: Any, site_names: Any) -> bool:
    """A title that names a product: a str that is not a placeholder (R-A5 shape:
    '', 'unknown', 'unknown product', 'n/a', 'product', 'this product' after
    casefold + punctuation strip) and not the site's own name."""
    if not isinstance(title, str):
        return False
    key = _title_key(title)
    if key in _PLACEHOLDER_TITLE_KEYS:
        return False
    return key not in {_title_key(n) for n in (site_names or ())}


def normalize_image_url(value: Any, base_url: Any) -> Optional[str]:
    """schema.org / og `image` -> the FIRST absolute https url string, joined against
    ``base_url`` (the FINAL fetched url), else None. A str, a list or an
    ImageObject is read through price_service._jsonld_image_urls; a
    protocol-relative '//cdn/x.jpg' takes the base scheme; http is refused."""
    from app.services.price_service import _jsonld_image_urls
    base = base_url if isinstance(base_url, str) else ""
    for candidate in _jsonld_image_urls(value):
        try:
            joined = urljoin(base, candidate)
            parts = urlsplit(joined)
            host = parts.hostname
        except ValueError:
            continue
        if parts.scheme == "https" and host:
            return joined
    return None


def _v2_code_message(code: Any) -> str:
    """The copy constant of a B4 code (UNRESOLVED_PRODUCT's for any other value)."""
    if code == "STORE_UNREADABLE":
        return STORE_UNREADABLE_MESSAGE
    if code == "NOT_PRODUCT_PAGE":
        return NOT_PRODUCT_PAGE_MESSAGE
    return UNRESOLVED_PRODUCT_MESSAGE


def _log_fetch_failed(url: str, reason: str, error_type: Optional[str]) -> None:
    """GC-1 as amended by RULINGS_FIX1_B4 F4-1: ONE WARNING per unreadable fetch that
    is not a transport error (blocked hop, redirect cap, non-2xx, challenge), the
    host, the reason word and the exception TYPE only (None when no exception). The
    transport error logs the same template at ERROR inside _fetch_page_v2's except
    arm."""
    logger.warning("[URL-V2] fetch failed host=%s reason=%s type=%s",
                   _host_only(url), reason, error_type)


# ============================================
# WEB SCRAPING
# ============================================

async def fetch_page(url: str) -> Optional[str]:
    """Fetch webpage content with proper headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # SSRF hardening (scraping audit 2026-07-08) — the public /url/* routes validate
    # only the initial user URL, so a 30x redirect to a private/loopback/link-local/
    # cloud-metadata (169.254.169.254) address would otherwise be followed blindly.
    # Follow redirects MANUALLY, bounded, re-validating EVERY hop with the SSRF guard.
    #
    # W0-1 (P0 LS-REQUEST-PATH-BLOCKING-01): this is an `async def`, so the
    # guard's synchronous getaddrinfo used to resolve ON the event loop for the
    # initial URL and for every hop -- a black-holed host froze the single
    # uvicorn worker for the OS resolver timeout before a byte was sent. Under
    # ENABLE_OFFLOOP_DNS_RESOLVE the resolve moves to the dedicated
    # `dns-resolve` pool under a 2s bound; flag OFF calls the same sync
    # validator inline (byte-identical).
    from app.utils.url_validator import _validate_url_offloop_or_sync

    if not await _validate_url_offloop_or_sync(url):
        logger.warning(f"[SSRF] Blocked initial URL: {url}")
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            current = url
            for _ in range(5):  # bounded redirect chain
                response = await client.get(current, headers=headers)
                if response.is_redirect and response.next_request is not None:
                    nxt = str(response.next_request.url)
                    if not await _validate_url_offloop_or_sync(nxt):
                        logger.warning(f"[SSRF] Blocked redirect to {nxt}")
                        return None
                    current = nxt
                    continue
                response.raise_for_status()
                return response.text
            logger.warning(f"[SSRF] Too many redirects for {url}")
            return None
    except Exception as e:
        # U8d R8 / UG2: the user's URL path and query never reach the log line
        # (and so Sentry) -- the host and the exception TYPE only; str(e) of an
        # httpx.HTTPStatusError carries the full URL.
        try:
            host = urlparse(url).hostname
        except ValueError:
            host = None
        logger.error(f"Failed to fetch URL host {host}: {type(e).__name__}")
        return None


async def _fetch_page_v2(url: str) -> Dict[str, Any]:
    """B4: fetch_page's loop (same headers, the SSRF guard on the initial url AND on
    every hop, the same 5-hop bound, the same client) that NEVER raises on a status
    and keeps what fetch_page discards: the LAST status and the FINAL url.

    Returns {"status": int|None, "final_url": str, "text": str|None,
    "outcome": "ok"|"blocked"|"redirect_cap"|"error", "error_type": str|None};
    a non-2xx is outcome "ok" with its status (the caller classifies it).
    fetch_page itself stays byte-unchanged (its pins). Log lines carry the host
    only (GC-1 / U8d): never the pasted path, query or a redirect target's path."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    from app.utils.url_validator import _validate_url_offloop_or_sync

    result: Dict[str, Any] = {
        "status": None, "final_url": url, "text": None, "outcome": "error", "error_type": None,
    }
    if not await _validate_url_offloop_or_sync(url):
        logger.warning("[SSRF] Blocked initial URL: host=%s", _host_only(url))
        _log_fetch_failed(url, "blocked", None)
        result["outcome"] = "blocked"
        return result
    current = url
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False,
                                     transport=_TRANSPORT) as client:
            for _ in range(5):  # bounded redirect chain, every hop re-validated
                response = await client.get(current, headers=headers)
                if response.is_redirect and response.next_request is not None:
                    nxt = str(response.next_request.url)
                    if not await _validate_url_offloop_or_sync(nxt):
                        logger.warning("[SSRF] Blocked redirect to host=%s", _host_only(nxt))
                        _log_fetch_failed(url, "blocked", None)
                        result.update(outcome="blocked", final_url=current)
                        return result
                    current = nxt
                    continue
                result.update(status=response.status_code, final_url=current,
                              text=response.text, outcome="ok")
                return result
        logger.warning("[SSRF] Too many redirects for host=%s", _host_only(url))
        _log_fetch_failed(url, "redirect_cap", None)
        result.update(outcome="redirect_cap", final_url=current)
        return result
    except Exception as e:
        # F4-1 (RULINGS_FIX1_B4, amends GC-1): the transport error is ONE ERROR line
        # inside this except arm with the distinct [URL-V2] template (host, reason
        # word, exception TYPE only), never the base 'Failed to fetch' template.
        logger.error("[URL-V2] fetch failed host=%s reason=%s type=%s",
                     _host_only(url), "fetch_error", type(e).__name__)
        result.update(outcome="error", error_type=type(e).__name__, final_url=current)
        return result


def extract_json_ld(html: str) -> List[Dict]:
    """Extract JSON-LD structured data from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    
    results = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    
    return results


def extract_meta_tags(html: str) -> Dict[str, str]:
    """Extract OpenGraph and meta tags."""
    soup = BeautifulSoup(html, "html.parser")
    meta = {}
    
    # OpenGraph tags
    for tag in soup.find_all("meta", property=re.compile(r"^og:")):
        prop = tag.get("property", "").replace("og:", "")
        content = tag.get("content", "")
        if prop and content:
            meta[f"og_{prop}"] = content
    
    # Product meta tags
    for tag in soup.find_all("meta", property=re.compile(r"^product:")):
        prop = tag.get("property", "").replace("product:", "")
        content = tag.get("content", "")
        if prop and content:
            meta[f"product_{prop}"] = content
    
    # Regular meta tags
    for name in ["description", "keywords", "title"]:
        tag = soup.find("meta", attrs={"name": name})
        if tag:
            meta[name] = tag.get("content", "")
    
    # Title tag
    title_tag = soup.find("title")
    if title_tag:
        meta["page_title"] = title_tag.string
    
    return meta


# ============================================
# RETAILER-SPECIFIC EXTRACTORS
# ============================================

def extract_amazon_data(html: str, url: str) -> Dict[str, Any]:
    """Extract product data from Amazon pages."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    # Title
    title_elem = soup.find("span", id="productTitle")
    if title_elem:
        data["title"] = title_elem.get_text(strip=True)
    
    # Price
    price_elem = soup.find("span", class_="a-price-whole")
    if price_elem:
        price_text = price_elem.get_text(strip=True).replace(",", "")
        try:
            data["price"] = float(price_text)
        except ValueError:
            pass
    
    # Alternative price location
    if "price" not in data:
        price_elem = soup.find("span", id="priceblock_ourprice")
        if price_elem:
            price_match = re.search(r"[\d,]+\.?\d*", price_elem.get_text())
            if price_match:
                data["price"] = float(price_match.group().replace(",", ""))
    
    # Rating
    rating_elem = soup.find("span", class_="a-icon-alt")
    if rating_elem:
        rating_text = rating_elem.get_text()
        rating_match = re.search(r"([\d.]+) out of 5", rating_text)
        if rating_match:
            data["rating"] = float(rating_match.group(1))
    
    # Review count
    review_elem = soup.find("span", id="acrCustomerReviewText")
    if review_elem:
        review_match = re.search(r"([\d,]+)", review_elem.get_text())
        if review_match:
            data["review_count"] = int(review_match.group(1).replace(",", ""))
    
    # Image
    img_elem = soup.find("img", id="landingImage")
    if img_elem:
        data["image_url"] = img_elem.get("src") or img_elem.get("data-old-hires")
    
    # Features/specs
    features = []
    feature_list = soup.find("ul", class_="a-unordered-list a-vertical a-spacing-mini")
    if feature_list:
        for li in feature_list.find_all("li"):
            text = li.get_text(strip=True)
            if text:
                features.append(text)
    data["features"] = features[:10]
    
    # ASIN
    asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if asin_match:
        data["asin"] = asin_match.group(1)
    
    return data


def extract_noon_data(html: str, url: str) -> Dict[str, Any]:
    """Extract product data from Noon pages."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    # Try JSON-LD first (Noon uses it)
    json_ld = extract_json_ld(html)
    for item in json_ld:
        if item.get("@type") == "Product":
            data["title"] = item.get("name")
            data["description"] = item.get("description")
            data["image_url"] = item.get("image")
            data["brand"] = item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else item.get("brand")
            
            offers = item.get("offers", {})
            if isinstance(offers, dict):
                data["price"] = offers.get("price")
                data["currency"] = offers.get("priceCurrency")
                data["availability"] = offers.get("availability")
            
            rating = item.get("aggregateRating", {})
            if rating:
                data["rating"] = rating.get("ratingValue")
                data["review_count"] = rating.get("reviewCount")
            break
    
    # Fallback to HTML parsing
    if "title" not in data:
        title_elem = soup.find("h1")
        if title_elem:
            data["title"] = title_elem.get_text(strip=True)
    
    return data


def extract_generic_data(html: str, url: str) -> Dict[str, Any]:
    """Generic extraction for unknown retailers."""
    data = {}
    
    # Try JSON-LD structured data first
    json_ld = extract_json_ld(html)
    for item in json_ld:
        if item.get("@type") == "Product":
            data["title"] = item.get("name")
            data["description"] = item.get("description")
            data["image_url"] = item.get("image")
            data["brand"] = item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else item.get("brand")
            
            offers = item.get("offers", {})
            if isinstance(offers, dict):
                data["price"] = offers.get("price")
                data["currency"] = offers.get("priceCurrency")
            elif isinstance(offers, list) and offers:
                data["price"] = offers[0].get("price")
                data["currency"] = offers[0].get("priceCurrency")
            
            rating = item.get("aggregateRating", {})
            if rating:
                data["rating"] = rating.get("ratingValue")
                data["review_count"] = rating.get("reviewCount")
            break
    
    # Fallback to meta tags
    meta = extract_meta_tags(html)
    
    if "title" not in data:
        data["title"] = meta.get("og_title") or meta.get("page_title")
    
    if "description" not in data:
        data["description"] = meta.get("og_description") or meta.get("description")
    
    if "image_url" not in data:
        data["image_url"] = meta.get("og_image")
    
    if "price" not in data and "product_price:amount" in meta:
        try:
            data["price"] = float(meta["product_price:amount"])
        except ValueError:
            pass
    
    return data


def extract_generic_data_v2(html: str, url: str, final_url: Optional[str] = None) -> Dict[str, Any]:
    """B4: extract_generic_data with (1) the Product node found through
    price_service's JSON-LD shape ladder (`@graph` at any depth, an `@type` list,
    `ProductGroup.hasVariant` members; first node in document order), (2) the
    image normalised to ONE absolute https url string joined against the FINAL
    url, (3) the og:image fallback taken when the node has no usable image (the
    base tests key PRESENCE, so a Product node without an image skipped it).

    Pure sync (one parse job: the caller runs it on the price-parse pool under
    ENABLE_PRICE_PARSE_OFFLOAD, ruling B4-R2). Adds two PRIVATE keys the caller
    pops before normalising: `_v2_product_node` (a node was found) and
    `_v2_site_names` (the site's own name keys, `_v2_site_names`)."""
    from app.services.price_service import _shape_ladder_product_nodes

    base = final_url or url
    data: Dict[str, Any] = {}
    json_ld = extract_json_ld(html)
    nodes: List[Dict[str, Any]] = []
    for block in json_ld:
        nodes.extend(_shape_ladder_product_nodes(block))
    if nodes:
        item = nodes[0]
        data["title"] = item.get("name")
        data["description"] = item.get("description")
        data["image_url"] = normalize_image_url(item.get("image"), base)
        brand = item.get("brand")
        data["brand"] = brand.get("name") if isinstance(brand, dict) else brand

        offers = item.get("offers", {})
        if isinstance(offers, dict):
            data["price"] = offers.get("price")
            data["currency"] = offers.get("priceCurrency")
        elif isinstance(offers, list) and offers and isinstance(offers[0], dict):
            data["price"] = offers[0].get("price")
            data["currency"] = offers[0].get("priceCurrency")

        rating = item.get("aggregateRating", {})
        if isinstance(rating, dict) and rating:
            data["rating"] = rating.get("ratingValue")
            data["review_count"] = rating.get("reviewCount")

    meta = extract_meta_tags(html)
    site_names = _v2_site_names(json_ld, meta)
    # RULINGS_FIX4_B4 F4-4: the first USABLE of og:title, the <title> tag (not the
    # first truthy), so an og:title equal to the site name or a placeholder no
    # longer shadows a usable <title>.
    meta_title = next((t for t in (meta.get("og_title"), meta.get("page_title"))
                       if is_usable_title(t, site_names)), None)
    # F2-5 (RULINGS_FIX2_B4): a Product node whose name is missing or unusable takes
    # a usable meta title (decided on the value, not on key presence).
    if "title" not in data or (not is_usable_title(data.get("title"), site_names)
                               and is_usable_title(meta_title, site_names)):
        data["title"] = meta_title
    if "description" not in data:
        data["description"] = meta.get("og_description") or meta.get("description")
    if not data.get("image_url"):
        data["image_url"] = normalize_image_url(meta.get("og_image"), base)
    if "price" not in data and "product_price:amount" in meta:
        try:
            data["price"] = float(meta["product_price:amount"])
        except ValueError:
            pass

    data["_v2_product_node"] = bool(nodes)
    data["_v2_site_names"] = site_names
    return data


# ============================================
# AI-POWERED EXTRACTION (FALLBACK)
# ============================================

URL_EXTRACTION_PROMPT = """You are a product data extraction expert. Extract product information from this webpage content.

URL: {url}

{page_block}

Extract and return ONLY valid JSON:
{{
    "brand": "brand name or null",
    "name": "product name",
    "full_title": "complete product title",
    "price": numeric_price_or_null,
    "currency": "currency code (AED, SAR, BHD, USD, etc.)",
    "category": "electronics|grocery|supplements|makeup|skincare|haircare|fragrances|fashion|other",
    "variant": "size/storage/color if specified or null",
    "specs": {{
        "key": "value for important specifications"
    }},
    "rating": 0.0-5.0 or null,
    "review_count": number or null,
    "in_stock": true|false|null,
    "retailer": "store name",
    "image_url": "main product image URL or null"
}}

RULES:
- Extract accurate data only, use null for uncertain fields
- Price should be numeric only (no currency symbols)
- Detect brand from title if not explicitly stated
- Be precise with product name and variant"""


def _derive_url_extraction_prompt_v2(base: str) -> str:
    """B4 (R0-6 B4-PROMPT-PINS): URL_EXTRACTION_PROMPT stays byte-identical; V2 is
    DERIVED from it by two count-checked swaps (the W4-11 pattern): the
    `is_product_page` JSON field after `image_url`, and one RULES line. Same render
    shape (the `URL:` line before the one region, the 9-key category enumeration).
    A drifted anchor raises RuntimeError at IMPORT, never a silent no-op."""
    swaps = (
        ('    "image_url": "main product image URL or null"',
         '    "image_url": "main product image URL or null",\n'
         '    "is_product_page": true|false'),
        ("- Be precise with product name and variant",
         "- Be precise with product name and variant\n"
         "- is_product_page is false when the page is a storefront homepage, a category "
         "or collection listing, a search page, a cart, checkout or account page, or an "
         "error page; then name is null"),
    )
    out = base
    for old, new in swaps:
        found = out.count(old)
        if found != 1:
            raise RuntimeError(
                f"URL_EXTRACTION_PROMPT_V2: expected exactly one anchor {old!r}, found {found}"
            )
        out = out.replace(old, new, 1)
    return out


URL_EXTRACTION_PROMPT_V2 = _derive_url_extraction_prompt_v2(URL_EXTRACTION_PROMPT)


def _price_parse_offload_enabled() -> bool:
    """ENABLE_PRICE_PARSE_OFFLOAD (W0-4, default OFF), read PER CALL. A local
    one-liner (like structured_comparison_service's) so the flag-OFF path never
    imports price_service."""
    return os.getenv("ENABLE_PRICE_PARSE_OFFLOAD", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


async def extract_with_ai(url: str, html: str, retailer: Dict,
                          url_mode_v2: bool = False) -> Dict[str, Any]:
    """Use AI to extract product data when structured data is insufficient.

    B4: ``url_mode_v2=True`` (passed only by the flagged URL path) selects
    URL_EXTRACTION_PROMPT_V2, which also asks for ``is_product_page``; the
    message layout and the call kwargs are identical in both states."""
    # R-W04 (W0-4c) — the soup + text extraction is pure-sync parsing. Under
    # ENABLE_PRICE_PARSE_OFFLOAD it runs as ONE job on the bounded price-parse
    # pool; flag OFF the same block runs inline, exactly as before.
    def _w04_parse_block():
        soup = BeautifulSoup(html, "html.parser")
    
        # Get page title
        title = soup.find("title")
        title_text = title.string if title else "Unknown"
    
        # Get main content (remove scripts, styles, nav, footer)
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
    
        # Get text content
        text_content = soup.get_text(separator="\n", strip=True)
        # Truncate to avoid token limits
        text_content = text_content[:4000]
        return title_text, text_content
    if _price_parse_offload_enabled():
        from app.services.price_service import run_parse_offloaded
        title_text, text_content = await run_parse_offloaded(_w04_parse_block)
    else:
        title_text, text_content = _w04_parse_block()
    
    try:
        client = get_client()
        _model = standard_model()
        # W4-11 (R13/R20): the fetched page title + text sit in ONE <SEARCH_RESULTS>
        # region under the guard sentence; the user-supplied URL stays outside the
        # region, neutralized like the verdict's concern/region.
        from app.services.extraction_service import SEARCH_RESULTS_GUARD, _wrap_search_context
        from app.utils.prompt_sanitizer import neutralize_prompt_tags

        page_block = _wrap_search_context(
            f"Page Title: {title_text}\n\nPage Content (truncated):\n{text_content}"
        )
        prompt = URL_EXTRACTION_PROMPT_V2 if url_mode_v2 else URL_EXTRACTION_PROMPT
        response = await _llm_breaker.guarded_llm_create(client,
            model=_model,
            messages=[{
                "role": "user",
                "content": SEARCH_RESULTS_GUARD + "\n\n" + prompt.format(
                    url=neutralize_prompt_tags(f"{url}"),
                    page_block=page_block,
                )
            }],
            **token_limit_kwargs(_model, 800),
            **sampling_kwargs(_model, 0.1),
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean markdown if present
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
    
    except Exception as e:
        # RULINGS_FIX4_B4 F4-5 (unflagged, log-only, R-A1 b): the exception TYPE
        # only, never its text (the U8d class); the return value is unchanged.
        logger.error("AI extraction error: %s", type(e).__name__)
        return {"error": str(e)}


# ============================================
# MAIN EXTRACTION FUNCTION
# ============================================

def _v2_status_reason(status: Any) -> str:
    """The reason word of a non-2xx final status (review C19): a 3xx can only end
    the loop when it carries no Location (a 3xx chain past five hops is
    redirect_cap, decided in _fetch_page_v2)."""
    if status == 403:
        return "http_403"
    if isinstance(status, int) and 300 <= status <= 399:
        return "http_3xx"
    if isinstance(status, int) and 400 <= status <= 499:
        return "http_4xx"
    return "http_5xx"


_V2_FETCH_OUTCOME_REASONS = {"error": "fetch_error", "blocked": "blocked",
                             "redirect_cap": "redirect_cap"}


def _v2_refusal(url: str, code: str, reason: str, outcome: str, status: Any) -> Dict[str, Any]:
    """One coded per-url failure (the shape compare_from_urls collects) and its
    ONE `[URL-V2] outcome=` INFO counter line (constants and an int only)."""
    logger.info("[URL-V2] outcome=%s reason=%s status=%s", outcome, reason, status)
    return {"success": False, "code": code, "reason": reason, "url": url,
            "error": _v2_code_message(code)}


async def _extract_from_url_v2(url: str) -> Dict[str, Any]:
    """B4 (ENABLE_URL_MODE_V2): extract_from_url where every non-delivery is a coded
    failure (never `success: True` with "Unknown Product"):

    (a) the v2 fetch: a transport error, an SSRF-blocked hop, the redirect cap, a
        non-2xx status or a title-anchored challenge page -> STORE_UNREADABLE;
    (b) a FINAL url in any pre-gate path class (a redirect to the storefront root,
        a search, cart/checkout, account or category route) -> NOT_PRODUCT_PAGE
        with that class as the reason (GC-2);
    (c) the extractor (amazon / noon base bodies, generic -> extract_generic_data_v2)
        on the price-parse pool under ENABLE_PRICE_PARSE_OFFLOAD, else inline;
    (d) no Product node and no usable title -> UNRESOLVED_PRODUCT `no_product_node`,
        with NO LLM call ($0);
    (e) missing title or price -> the V2 extraction prompt; `is_product_page: false`
        refuses (`not_product_page`) only when no Product node was found
        (ruling B4-R1: a node-bearing page is never refused on the LLM's word);
    (f) the title is the first USABLE of title / full_title (`null_name` when
        neither is; an unusable title gives way to a usable full_title, F3-3), an
        unusable merged name gives way to it (F2-5), and the product is
        normalised with its image as ONE https url string or None."""
    retailer = detect_retailer(url)
    logger.info("Detected retailer: %s for host %s", _retailer_log_name(retailer), _host_only(url))

    fetched = await _fetch_page_v2(url)
    status = fetched.get("status")
    outcome = fetched.get("outcome")
    if outcome != "ok":
        reason = _V2_FETCH_OUTCOME_REASONS.get(outcome, "fetch_error")
        return _v2_refusal(url, "STORE_UNREADABLE", reason, reason, status)
    if not isinstance(status, int) or not 200 <= status <= 299:
        reason = _v2_status_reason(status)
        _log_fetch_failed(url, reason, None)
        return _v2_refusal(url, "STORE_UNREADABLE", reason, "http_error", status)
    html = fetched.get("text") or ""
    if _is_challenge_page(html):
        _log_fetch_failed(url, "challenge", None)
        return _v2_refusal(url, "STORE_UNREADABLE", "challenge", "challenge", status)
    final_url = fetched.get("final_url") or url
    page_class = classify_url_path(final_url)
    if page_class is not None:
        return _v2_refusal(url, "NOT_PRODUCT_PAGE", page_class, "not_product_page", status)

    if "amazon" in retailer["key"]:
        _extractor, _extra = extract_amazon_data, ()
    elif "noon" in retailer["key"]:
        _extractor, _extra = extract_noon_data, ()
    else:
        _extractor, _extra = extract_generic_data_v2, (final_url,)
    if _price_parse_offload_enabled():
        # W0-4f shape (ruling B4-R2): the capped html and the soup-building
        # extractor as ONE job on the price-parse pool.
        from app.services import price_service as _w04_ps
        html = html[:_w04_ps.PRICE_FETCH_MAX_BYTES]
        raw_data = await _w04_ps.run_parse_offloaded(_extractor, html, url, *_extra)
    else:
        raw_data = _extractor(html, url, *_extra)

    # The amazon / noon bodies set neither key: no node, no site names.
    nodes_present = bool(raw_data.pop("_v2_product_node", False))
    site_names = raw_data.pop("_v2_site_names", None) or set()
    if not nodes_present and not is_usable_title(raw_data.get("title"), site_names):
        return _v2_refusal(url, "UNRESOLVED_PRODUCT", "no_product_node", "unresolved", status)

    if not raw_data.get("title") or not raw_data.get("price"):
        logger.info("Insufficient structured data, using AI extraction")
        ai_data = await extract_with_ai(url, html, retailer, url_mode_v2=True)
        if isinstance(ai_data, dict):
            if ai_data.get("is_product_page") is False and not nodes_present:
                return _v2_refusal(url, "UNRESOLVED_PRODUCT", "not_product_page",
                                   "unresolved", status)
            # Merge AI data with raw data (raw data takes precedence), as base.
            for key, value in ai_data.items():
                if key == "is_product_page":
                    continue
                if key not in raw_data or raw_data[key] is None:
                    raw_data[key] = value

    # F3-3 (RULINGS_FIX3_B4): the first USABLE of title / full_title, so a
    # placeholder node name no longer shadows a usable LLM full_title; an unusable
    # title is cleared so normalize_product_data ships the usable one.
    title = next((t for t in (raw_data.get("title"), raw_data.get("full_title"))
                  if is_usable_title(t, site_names)), None)
    if title is None:
        return _v2_refusal(url, "UNRESOLVED_PRODUCT", "null_name", "unresolved", status)
    if not is_usable_title(raw_data.get("title"), site_names):
        raw_data["title"] = None
    # F2-5 (RULINGS_FIX2_B4): an unusable merged name (a placeholder, the site's own
    # name, a non-str) never ships; the usable title above takes its place.
    if not is_usable_title(raw_data.get("name"), site_names):
        raw_data["name"] = None

    normalized = normalize_product_data(raw_data, retailer, url, url_mode_v2=True,
                                        final_url=final_url)
    logger.info("[URL-V2] outcome=%s reason=%s status=%s", "ok", "delivered", status)
    return {
        "success": True,
        "product": normalized,
        "retailer": retailer,
        "source_url": url,
        "extraction_method": "structured" if raw_data.get("title") else "ai"
    }


async def extract_from_url(url: str, url_mode_v2: bool = False) -> Dict[str, Any]:
    """
    Main function to extract product data from a URL.
    
    Returns structured product data suitable for comparison.

    B4: ``url_mode_v2=True`` (passed only by the flagged URL path) dispatches to
    _extract_from_url_v2; the default is the base body, unchanged.
    """
    if url_mode_v2:
        return await _extract_from_url_v2(url)
    # Detect retailer
    retailer = detect_retailer(url)
    # R-A1(b), UNFLAGGED log-only: the host, never the pasted path or query.
    logger.info("Detected retailer: %s for host %s", _retailer_log_name(retailer), _host_only(url))
    
    # Fetch page
    html = await fetch_page(url)
    if not html:
        return {
            "success": False,
            "error": "Failed to fetch URL",
            "url": url
        }
    
    # Extract data based on retailer
    if "amazon" in retailer["key"]:
        _extractor = extract_amazon_data
    elif "noon" in retailer["key"]:
        _extractor = extract_noon_data
    else:
        _extractor = extract_generic_data
    if _price_parse_offload_enabled():
        # W0-4f: bounded parse input (the same capped html reaches
        # extract_with_ai) and the soup-building extractor on the parse pool.
        # price_service resolved via the package attribute at call time (#185).
        from app.services import price_service as _w04_ps
        html = html[:_w04_ps.PRICE_FETCH_MAX_BYTES]
        raw_data = await _w04_ps.run_parse_offloaded(_extractor, html, url)
    else:
        raw_data = _extractor(html, url)
    
    # If insufficient data, use AI extraction
    if not raw_data.get("title") or not raw_data.get("price"):
        logger.info("Insufficient structured data, using AI extraction")
        ai_data = await extract_with_ai(url, html, retailer)
        # Merge AI data with raw data (raw data takes precedence)
        for key, value in ai_data.items():
            if key not in raw_data or raw_data[key] is None:
                raw_data[key] = value
    
    # Normalize to our schema
    normalized = normalize_product_data(raw_data, retailer, url)
    
    return {
        "success": True,
        "product": normalized,
        "retailer": retailer,
        "source_url": url,
        "extraction_method": "structured" if raw_data.get("title") else "ai"
    }


def normalize_product_data(raw: Dict, retailer: Dict, url: str, url_mode_v2: bool = False,
                           final_url: Optional[str] = None) -> Dict[str, Any]:
    """Normalize extracted data to our standard schema.

    B4 (``url_mode_v2=True``, flagged URL path only): the caller has already
    refused an unusable title, so the "Unknown Product" default is never used,
    and ``image_url`` ships as ONE absolute https url string joined against the
    FINAL url, or None (never a list, a dict or a relative path). Default: base."""
    
    # Parse brand and name from title if needed
    if url_mode_v2:
        title = raw.get("title") or raw.get("full_title") or ""
    else:
        title = raw.get("title") or raw.get("full_title") or "Unknown Product"
    brand = raw.get("brand")
    name = raw.get("name") or title
    
    # Try to extract brand from title
    if not brand:
        known_brands = [
            "Apple", "Samsung", "Google", "Sony", "LG", "Huawei", "Xiaomi",
            "OnePlus", "OPPO", "Vivo", "Nokia", "Motorola", "Dell", "HP",
            "Lenovo", "ASUS", "Acer", "Microsoft", "Nike", "Adidas", "Puma"
        ]
        for b in known_brands:
            if b.lower() in title.lower():
                brand = b
                break
    
    return {
        "brand": brand,
        "name": name,
        "full_name": title,
        "variant": raw.get("variant"),
        # CLEANUP-2(b): canonicalize the LLM-returned category to one of the 9
        # canonical keys so the URL path keys scoring dims / spec schema / fairness
        # correctly (a stale "beauty"/"home" etc. -> "other"). The prompt now offers
        # canonical keys; this is the defensive normalization.
        "category": canonicalize_category(raw.get("category")),
        "price": {
            "amount": raw.get("price"),
            "currency": raw.get("currency") or retailer.get("currency", "USD"),
            "retailer": retailer.get("name"),
            "url": url,
            "in_stock": raw.get("in_stock", raw.get("availability"))
        },
        "specs": raw.get("specs", {}),
        "reviews": {
            "rating": raw.get("rating"),
            "count": raw.get("review_count")
        },
        "image_url": (normalize_image_url(raw.get("image_url"), final_url or url)
                      if url_mode_v2 else raw.get("image_url")),
        "source_url": url,
        "retailer": retailer
    }


# ============================================
# COMPARE FROM URLs
# ============================================

async def compare_from_urls(
    url1: str,
    url2: str,
    region: str = "bahrain",
    selected_category: Optional[str] = None,
    url_mode_v2: bool = False,
) -> Dict[str, Any]:
    """
    Compare two products from their URLs.
    
    Args:
        url1: First product URL
        url2: Second product URL
        region: Region for additional price lookup
        selected_category: the caller's category chip, threaded through to
            ``_resolve_pair_category`` exactly as the text path threads
            ``body.selected_category`` (MB-RECONCILE-07). It was hardcoded
            ``None`` here, so a URL comparison could never honour a user chip
            even when the LLM abstained with "other". UNFLAGGED: the default is
            ``None``, which is byte-identical to the hardcoded value.
        url_mode_v2: B4 (ENABLE_URL_MODE_V2, read once by the route and passed
            only when ON): coded per-url failures become ONE coded result
            (_v2_pair_failure) and the frozen `recommendation` /
            `key_differences` keys are filled from the verdict prose
            (_v2_verdict_fill). Default False: the base body, unchanged.
    
    Returns:
        Comparison result with both products
    """
    from app.services.structured_comparison_service import get_comparison_service
    from app.services.extraction_service import generate_comparison
    
    # Extract both products in parallel
    import asyncio
    if url_mode_v2:
        extractions = (extract_from_url(url1, url_mode_v2=True),
                       extract_from_url(url2, url_mode_v2=True))
    else:
        extractions = (extract_from_url(url1), extract_from_url(url2))
    results = await asyncio.gather(*extractions, return_exceptions=True)
    
    products = []
    errors = []
    coded = []  # B4: (index, code, reason) of each coded per-url failure (ON only)
    codeless = False
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"URL {i+1}: {str(result)}")
            codeless = True
        elif not result.get("success"):
            errors.append(f"URL {i+1}: {result.get('error', 'Extraction failed')}")
            if url_mode_v2 and result.get("code"):
                coded.append((i, result.get("code"), result.get("reason")))
            else:
                codeless = True
        else:
            products.append(result["product"])
    
    if len(products) < 2:
        if url_mode_v2 and coded and not codeless:
            return _v2_pair_failure(coded, errors)
        # Any codeless failure (an exception inside extract_from_url) keeps the
        # base codeless body in both flag states.
        return {
            "success": False,
            "error": "Could not extract both products",
            "details": errors
        }

    # CLEANUP-2(c): resolve the pair category and write it back onto BOTH products
    # before the verdict, so URL-mode fragrance/supplement compares get the correct
    # category (dims + spec framing). extract_from_url's per-product category is the
    # LLM's full-context judgment (the parser-path analog), so it is AUTHORITATIVE:
    # reuse the shared _resolve_pair_category with parser_path=True. The caller's
    # chip is honoured on exactly the same terms as the text path (MB-RECONCILE-07:
    # under parser_path=True a real chip is consulted only when the LLM abstained
    # with "other", and otherwise only re-flags a switch) — it used to be hardcoded
    # None here, which made the chip unreachable. Falls back gracefully to "other"
    # if resolution can't decide.
    from app.services.structured_comparison_service import _resolve_pair_category
    category_used, _switched, _orig = await _resolve_pair_category(
        products, selected_category, parser_path=True
    )
    for _p in products:
        _p["category"] = category_used

    # Generate comparison (now told the resolved category instead of the default).
    # MB-RECONCILE-01 / PO-VERDICT-TRUTH-01: generate_comparison returns
    # ``(parsed, usage)`` on EVERY path (extraction_service.py `:2543` and the
    # except-branch twin at `:2547`) — its `-> Dict[str, Any]` annotation was
    # simply wrong, and is corrected in the same change. This call site was the
    # only one of four that kept the 2-tuple whole and then called ``.get()`` on
    # it below, so POST/GET /api/v1/url/compare raised
    # ``AttributeError: 'tuple' object has no attribute 'get'`` and 500'd on
    # EVERY successful extraction — a successful URL comparison has never been
    # deliverable. UNFLAGGED (the M13-10 / M13-44 pure-defect class): gating the
    # unpack would leave the route 500ing whenever the flag was off.
    comparison, _usage = await generate_comparison(
        products[0], products[1], region, category=category_used
    )

    # R-METER (W2-1c), UNFLAGGED -- a live leak with no legitimate reader:
    # generate_comparison's except-branch returns
    # `{"winner_index": 0, "error": <text>}`, which the unpack above made
    # deliverable as `success: True` with a fabricated winner_index 0 and the
    # raw exception text (measured: an OpenAI key tail) in `comparison.error`.
    # Keyed on the TRUTHINESS of the value (Fable round-3 ruling): that branch
    # stores a non-empty string whether it is str(e) today or W4-9's constant,
    # so the check composes with either; a verdict carrying a falsy `error`
    # (None / "") is delivered exactly as base. Never forward the text; the
    # route maps LLM_UNAVAILABLE through the text route's failure contract.
    if comparison.get("error"):
        from app.services.structured_comparison_service import (
            LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
        )
        logger.warning("[URL] verdict generation failed; not delivering a comparison")
        return {
            "success": False,
            "code": "LLM_UNAVAILABLE",
            "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
        }

    if url_mode_v2:
        recommendation, key_differences = _v2_verdict_fill(comparison, products)
    else:
        recommendation = comparison.get("recommendation", "")
        key_differences = comparison.get("key_differences", [])

    return {
        "success": True,
        "products": products,
        "comparison": comparison,
        "winner_index": comparison.get("winner_index", 0),
        "recommendation": recommendation,
        "key_differences": key_differences,
        "category_used": category_used,
        "source_urls": [url1, url2]
    }


# B4: the most actionable cause wins when the two links fail differently.
_V2_CODE_PRECEDENCE = ("STORE_UNREADABLE", "NOT_PRODUCT_PAGE", "UNRESOLVED_PRODUCT")


def _v2_pair_failure(coded: List[Tuple[int, str, Any]], errors: List[str]) -> Dict[str, Any]:
    """The ONE coded result of a pair with coded per-url failures: the code by
    precedence STORE_UNREADABLE > NOT_PRODUCT_PAGE > UNRESOLVED_PRODUCT, `field`
    url1 / url2 / both over the failing links, `reason` of the first failing link
    carrying the chosen code, that code's constant as `error`, and today's
    `details` list (the route drops it)."""
    def _rank(code: str) -> int:
        return (_V2_CODE_PRECEDENCE.index(code) if code in _V2_CODE_PRECEDENCE
                else len(_V2_CODE_PRECEDENCE))

    chosen = min((code for _i, code, _r in coded), key=_rank)
    failing = sorted({i for i, _c, _r in coded})
    field = "both" if len(failing) > 1 else ("url1" if failing[0] == 0 else "url2")
    reason = next(r for _i, code, r in sorted(coded, key=lambda row: row[0]) if code == chosen)
    return {"success": False, "code": chosen, "error": _v2_code_message(chosen), "field": field,
            "reason": reason, "details": errors}


def _v2_verdict_fill(comparison: Dict[str, Any], products: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """B4 value fill on the FROZEN keys (no new top-level key): `recommendation`
    from the verdict's winner_reason with score internals stripped, falling back
    to THE qualitative winner reason (issue #99) for the winner; `key_differences`
    from the specs_comparison advantages (product 0 then product 1; str items
    only, score internals stripped, empties dropped; never the `similar` list)."""
    from app.services.response_builder import _QUALITATIVE_WINNER_REASON
    from app.services.text_sanitize import strip_score_internals

    idx = comparison.get("winner_index", 0)
    if type(idx) is not int or idx not in (0, 1) or idx >= len(products):
        idx = 0
    winner = products[idx] if products else {}
    winner_name = winner.get("full_name") or winner.get("name") or ""
    reason = comparison.get("winner_reason")
    recommendation = (strip_score_internals(reason if isinstance(reason, str) else "")
                      or _QUALITATIVE_WINNER_REASON(winner_name))

    specs_comparison = comparison.get("specs_comparison")
    if not isinstance(specs_comparison, dict):
        specs_comparison = {}
    key_differences: List[str] = []
    for key in ("product_0_advantages", "product_1_advantages"):
        items = specs_comparison.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, str) and item.strip():
                cleaned = strip_score_internals(item)
                if cleaned:
                    key_differences.append(cleaned)
    return recommendation, key_differences
