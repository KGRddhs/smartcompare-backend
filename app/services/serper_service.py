"""
Serper Service - Web search via Serper API (Google Search)
Enhanced for structured product data extraction
"""
import asyncio
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

# Bundle C § 1c A.3.3-fix-1 — Serper credit-meter integration. Every
# successful Serper call (HTTP 200) bumps the Redis counter so the
# admin/costs Serper figure reflects actual usage. Missing-API-key and
# exception paths skip the bump (we don't bill non-events).
from app.services.api_budget_service import record_usage

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_BASE_URL = "https://google.serper.dev"


# ============================================
# MULTI-KEY SERPER FAILOVER (genuine-price serper-multikey)
# ============================================
# A single free Serper key holds a finite lifetime credit pool; when it
# depletes mid-run the warmer cron (and live compares) silently degrade to
# `estimated`. This layer reads an ORDERED key list from SERPER_API_KEYS
# (comma-separated, priority order) and rotates to the next non-exhausted key
# when a response signals credit depletion.
#
# Backward compatibility (critical): when only SERPER_API_KEY is set (no
# SERPER_API_KEYS) and that key is NOT exhausted, behaviour is byte-identical
# to before — the active key IS SERPER_API_KEY, exactly ONE POST fires on the
# happy path (no rotation), only a single cheap Redis exhaustion-check read is
# added. The module attr SERPER_API_KEY is preserved (tests patch it) and is
# consulted as the single-key fallback so `monkeypatch.setattr(serper_service,
# "SERPER_API_KEY", ...)` continues to work.
#
# Exhaustion is DISTINCT from the api_budget_service circuit breaker: a
# credit-depletion failover marks the KEY exhausted (Redis flag serper:
# exhausted:<key8>) and rotates — it does NOT trip the 3-failure CB cooldown.
# A transient 500/timeout is neither: it neither marks the key exhausted nor
# rotates (the caller's existing except/raise handling deals with it).

# Redis prefix for the per-key exhaustion flag. Keyed by the same 8-char
# prefix api_budget_service uses to scope the lifetime counter.
_SERPER_EXHAUSTED_PREFIX = "serper:exhausted:"

# TTL for the exhaustion flag. MODERATE (6h): long enough that a truly-depleted
# free key is skipped for the rest of a warmer run / session, short enough that
# a transiently-misclassified key (or a key whose free quota resets) is retried
# later instead of being permanently blacklisted.
_SERPER_EXHAUSTED_TTL = 6 * 3600

# In-process de-dupe so the "key exhausted" WARNING logs once per key per
# process (Redis carries the cross-process authoritative state).
_serper_exhausted_logged: set = set()


def _serper_key_prefix8(key: Optional[str]) -> str:
    """First 8 chars of a key (for the Redis exhaustion flag + logs). Mirrors
    api_budget_service._serper_key_prefix scoping."""
    raw = (key or "").strip()
    return raw[:8] if raw else "nokey"


def _resolve_serper_keys() -> List[str]:
    """Resolve the ORDERED Serper key list, fresh per call (so a Railway env
    update takes effect without a restart).

    Priority: SERPER_API_KEYS (comma-separated, order = priority; trimmed,
    blanks skipped, de-duplicated preserving order). Falls back to the single
    module-level SERPER_API_KEY when SERPER_API_KEYS is unset/empty — this is
    what preserves backward compatibility AND test monkeypatching of the
    SERPER_API_KEY module attr.
    """
    raw_multi = (os.environ.get("SERPER_API_KEYS") or "").strip()
    keys: List[str] = []
    if raw_multi:
        for part in raw_multi.split(","):
            k = part.strip()
            if k and k not in keys:
                keys.append(k)
    if keys:
        return keys
    # Single-key fallback — read the MODULE attr (not os.getenv) so tests that
    # monkeypatch serper_service.SERPER_API_KEY keep working and a runtime
    # override is honoured.
    single = (SERPER_API_KEY or "")
    single = single.strip() if isinstance(single, str) else ""
    return [single] if single else []


def _is_serper_key_exhausted(key: str) -> bool:
    """True if the per-key exhaustion flag is set in Redis. Fail-open: on Redis
    error / unavailability the key is treated as NOT exhausted (do not block a
    healthy key just because Redis is down)."""
    try:
        from app.services.cache_service import _redis_get
        return bool(_redis_get(_SERPER_EXHAUSTED_PREFIX + _serper_key_prefix8(key)))
    except Exception:  # noqa: BLE001
        return False


def _mark_serper_key_exhausted(key: str) -> None:
    """Set the per-key exhaustion flag in Redis with a MODERATE TTL and log a
    WARNING once per key per process. Best-effort — a Redis failure just means
    the flag is not persisted (the failover for THIS call still rotated)."""
    prefix = _serper_key_prefix8(key)
    try:
        from app.services.cache_service import _redis_set
        _redis_set(_SERPER_EXHAUSTED_PREFIX + prefix, "1", ex=_SERPER_EXHAUSTED_TTL)
    except Exception:  # noqa: BLE001
        pass
    if prefix not in _serper_exhausted_logged:
        _serper_exhausted_logged.add(prefix)
        logger.warning(
            "SERPER_KEY_EXHAUSTED key=%s… marked exhausted (ttl=%ss); "
            "rotating to next key",
            prefix,
            _SERPER_EXHAUSTED_TTL,
        )


def _active_serper_key() -> Optional[str]:
    """The first key in priority order that is NOT currently marked exhausted.
    Returns None when there are no keys OR every key is exhausted (caller then
    degrades exactly as the legacy 'SERPER_API_KEY not set' path)."""
    for key in _resolve_serper_keys():
        if not _is_serper_key_exhausted(key):
            return key
    return None


def _response_signals_exhaustion(status_code: Optional[int], body_text: str) -> bool:
    """Detect credit depletion from a Serper response. Two independent signals:
      1. HTTP status in {402, 403} (payment/forbidden — credit-related), OR
      2. body/message contains 'credit' (case-insensitive) — a depleted free
         key returns {"message":"Not enough credits"} (observed with HTTP 400).
    A transient 500 / non-credit 4xx does NOT match (no 'credit' substring,
    status not in the set) so it never marks a key exhausted."""
    if status_code in (402, 403):
        return True
    if isinstance(body_text, str) and body_text and "credit" in body_text.lower():
        return True
    return False


async def _serper_post(client, path: str, payload: Dict[str, Any]):
    """Shared Serper POST with credit-exhaustion failover.

    Picks the active (first non-exhausted) key, POSTs to
    `{SERPER_BASE_URL}{path}` with the standard headers, and — if the response
    signals credit depletion — marks that key exhausted and retries with the
    NEXT non-exhausted key (bounded to len(keys) attempts). Returns the httpx
    Response of the FIRST non-exhaustion result (which the caller inspects /
    raise_for_status()es exactly as before), so response handling is unchanged.

    On the happy path (single healthy key) this fires exactly ONE POST and adds
    only one cheap Redis exhaustion-check read — byte-identical behaviour.

    The caller is responsible for the `if not <key>` guard BEFORE calling this
    (preserving the legacy short-circuit + no-record_usage semantics). Callers
    pass the active key implicitly via this helper; a None active key means all
    keys are exhausted and this helper is not reached.
    """
    keys = _resolve_serper_keys()
    attempts = 0
    max_attempts = max(1, len(keys))
    last_response = None
    while attempts < max_attempts:
        key = _active_serper_key()
        if not key:
            # All keys exhausted mid-loop — return the last response (if any) so
            # the caller's existing handling degrades gracefully.
            break
        attempts += 1
        response = await client.post(
            f"{SERPER_BASE_URL}{path}",
            headers={
                "X-API-KEY": key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        last_response = response
        # Inspect for credit exhaustion. Reading .text on a MagicMock is cheap;
        # on a real httpx.Response it is the already-buffered body.
        try:
            status = getattr(response, "status_code", None)
            body_text = getattr(response, "text", "") or ""
        except Exception:  # noqa: BLE001
            status = None
            body_text = ""
        if _response_signals_exhaustion(status, body_text):
            _mark_serper_key_exhausted(key)
            continue  # rotate to the next non-exhausted key
        return response
    return last_response


# ============================================
# ORIGINAL FUNCTIONS (backward compatibility)
# ============================================

async def search_product_price(product_name: str, country: str = "Bahrain") -> Dict[str, Any]:
    """
    Original function - Search for product prices.
    Kept for backward compatibility with comparison_service.py
    """
    country_codes = {
        "Bahrain": "bh",
        "Saudi Arabia": "sa",
        "UAE": "ae",
        "Kuwait": "kw",
        "Qatar": "qa",
        "Oman": "om"
    }
    
    code = country_codes.get(country, "bh")
    query = f"{product_name} price {country}"
    
    results = await search_product_prices(product_name, code)
    
    # Format for backward compatibility
    return {
        "query": query,
        "organic": results.get("organic", []),
        "shopping": results.get("shopping", []),
        "knowledge_graph": results.get("knowledge_graph")
    }


# ============================================
# CORE SEARCH FUNCTIONS
# ============================================

async def search_web(
    query: str,
    num_results: int = 10,
    country: str = "bh"
) -> Dict[str, Any]:
    """
    General web search.
    
    Args:
        query: Search query
        num_results: Number of results (max 100)
        country: Country code for localized results
    
    Returns:
        Search results with organic, featured snippets, etc.
    """
    if not _active_serper_key():
        logger.warning("SERPER_API_KEY not set")
        return {"organic": [], "error": "Search not configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await _serper_post(
                client,
                "/search",
                {
                    "q": query,
                    "num": num_results,
                    "gl": country,
                    "hl": "en"
                }
            )
            response.raise_for_status()
            record_usage("serper")
            return response.json()

    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"organic": [], "error": str(e)}


# Bundle C § 1c A.3.3-fix-2 — Serper Shopping has thin GCC coverage.
# Direct-curl diagnostic (Session 52) showed gl=bh returns empty
# shopping[] for mainstream queries (iPhone 16, CeraVe, Centrum) while
# gl=us returns 20-40 items. The fallback below retries once with gl=us
# when the primary GCC country returns empty; downstream price_service
# converts USD→BHD via exchange_rate_service + tags source_method:
# 'converted_usd'. OPERATIONAL STOPGAP until Google Shopping's Bahrain
# merchant feed catches up.
_GCC_COUNTRIES = frozenset({"bh", "sa", "ae", "kw", "qa", "om"})


# Bundle C HOTFIX-2 round 2 — GPT-emitted product_info["search_query"]
# sometimes appends operator-style suffixes like "price", "buy", "best
# price" because PRODUCT_PARSER_PROMPT (extraction_service.py:71+82)
# tells GPT to emit "an optimized search query for price searches".
# Direct curl proves these suffixes KILL Google Shopping match:
#   q="Apple iPhone 16 price" gl=us → 0 items
#   q="iPhone 16"             gl=us → 20 items
# Strip defensively so cached + new GPT outputs both work. The match
# is case-insensitive, only trailing tokens, only the operator words
# below (does not touch product-essential keywords like "Pro", "Plus").
import re as _re

_SHOPPING_QUERY_TAIL_NOISE = _re.compile(
    r"(?:\s+(?:price|prices|pricing|cost|buy|best\s+price|cheapest|deals?|sale|"
    r"on\s+sale|amazon|noon|carrefour|bahrain|saudi(?:\s+arabia)?|uae|"
    r"dubai|kuwait|qatar|oman|bhd|sar|aed|kwd|qar|omr|usd))+\s*$",
    _re.IGNORECASE,
)


def _clean_shopping_query(product: str) -> str:
    """Strip trailing operator-style suffixes that wreck Google Shopping
    match. Idempotent — calling twice is a no-op. Preserves all interior
    tokens (only the trailing run is removed). Applied repeatedly until
    no more trailing tail noise — handles 'iPhone price Bahrain BHD buy'
    by chewing one operator-run at a time."""
    if not product:
        return product
    prev = None
    cleaned = product
    while cleaned != prev:
        prev = cleaned
        cleaned = _SHOPPING_QUERY_TAIL_NOISE.sub("", cleaned).strip()
    return cleaned or product  # never return empty string


async def _do_serper_shopping(product: str, gl: str) -> Dict[str, Any]:
    """Single Serper Shopping call. Records usage on HTTP 200. Returns
    parsed JSON or {} on error. No retry, no fallback — fallback logic
    lives in the caller (search_product_prices)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            shopping_response = await _serper_post(
                client,
                "/shopping",
                {
                    "q": product,
                    "gl": gl,
                    "hl": "en",
                    "num": 10
                }
            )
            if shopping_response.status_code == 200:
                record_usage("serper")
                return shopping_response.json()
            # Bundle C v1.1 § 1c SERPER_SHOPPING_NON_200 — capture what
            # Serper actually returns when not 200 so we can disambiguate
            # the 3 likely production failure modes:
            #   1. HTTP 429 + Retry-After  → rate limit (op fix)
            #   2. HTTP 200 empty shopping  → genuine coverage gap
            #      (this branch never fires for empty-but-200; here for
            #      completeness as a reminder that 200 is the success arm)
            #   3. HTTP 4xx other-shape    → request-side bug grep missed
            # All Serper POSTs in this codebase explicitly set
            # Content-Type: application/json AND use httpx json= kwarg
            # (auto-set) — verified by grep at all 7 sites. So a 400
            # here would point to a different cause than the header.
            # Always-on WARNING — appears in Railway prod without flag.
            # Body truncated to 300 chars to keep log lines bounded.
            try:
                body_snippet = (shopping_response.text or "")[:300]
            except Exception:  # noqa: BLE001
                body_snippet = "<unreadable>"
            retry_after = shopping_response.headers.get("retry-after")
            ratelimit_remaining = shopping_response.headers.get(
                "x-ratelimit-remaining"
            )
            logger.warning(
                "SERPER_SHOPPING_NON_200 gl=%s status=%s "
                "retry_after=%s ratelimit_remaining=%s "
                "body=%r product=%r",
                gl,
                shopping_response.status_code,
                retry_after,
                ratelimit_remaining,
                body_snippet,
                product[:80],
            )
            return {}
    except Exception as e:
        logger.error(f"Serper shopping call error (gl={gl}): {e}")
        return {}


async def search_product_prices(
    product: str,
    country: str = "bh",
    currency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for product prices via Serper Shopping API.

    Bundle C § 1c A.3.3-fix-2: when the GCC primary call returns an empty
    `shopping[]` array, retry ONCE with `gl=us` so downstream USD→BHD
    conversion can land real prices. The response's `shopping_region`
    field identifies which call's items are returned so admin
    dashboards can monitor fallback rate.

    Organic search is deferred to search_price_organic() and only
    called if both shopping calls return empty (Saudi-only items like
    Almarai laban — pipeline naturally falls through to Tier 1.5).
    """
    if not _active_serper_key():
        return {"shopping": [], "organic": [], "error": "Search not configured"}

    # HOTFIX-2 round 2 — drop GPT-emitted " price"/"buy"/etc. tails.
    # Both primary GCC and us_fallback share the cleaned string so
    # behaviour is consistent. Log when we actually changed something
    # so Ahmed can see in Railway whether old GPT outputs are still
    # producing dirty queries.
    original_product = product
    product = _clean_shopping_query(product)
    if product != original_product:
        logger.info(
            f"[SHOPPING_QUERY_CLEAN] before={original_product!r} after={product!r}"
        )

    # genuine-BH starvation fix (2026-06-27) — for a GCC country, fire the gl=country
    # primary AND the gl=us fallback CONCURRENTLY rather than sequentially. Google has
    # NO Bahrain shopping feed, so the gl=bh primary returns 0 essentially every time
    # and the gl=us fallback was ALWAYS reached — but it ran ~3s AFTER the dead gl=bh
    # call, stealing budget the downstream 15s genuine-BH curl fan_out needs. Running
    # them in parallel reclaims that ~3s. Selection is UNCHANGED: prefer gl=country
    # items when present (genuine local feed), else the gl=us fallback (powers the
    # USD->BHD conversion + parks the converted_fallback). Net Serper calls are the
    # same as before for the empty-primary path (the dominant GCC case); only WHEN the
    # second call fires changes (concurrent, not serial). Non-GCC countries keep the
    # single-call, no-fallback behaviour byte-for-byte.
    if country in _GCC_COUNTRIES:
        primary, fallback = await asyncio.gather(
            _do_serper_shopping(product, gl=country),
            _do_serper_shopping(product, gl="us"),
        )
        primary_shopping = primary.get("shopping", []) or []
        if primary_shopping:
            return {
                "shopping": primary_shopping,
                "organic": [],
                "query": product,
                "shopping_region": country,
            }
        fallback_shopping = fallback.get("shopping", []) or []
        if fallback_shopping:
            return {
                "shopping": fallback_shopping,
                "organic": [],
                "query": product,
                "shopping_region": "us_fallback",
            }
        # Both empty — pipeline falls through to Tier 1.5 / Tier 2 / Tier 3.
        return {
            "shopping": [],
            "organic": [],
            "query": product,
            "shopping_region": "us_fallback",
        }

    # Non-GCC primary — single call, no gl=us fallback.
    primary = await _do_serper_shopping(product, gl=country)
    primary_shopping = primary.get("shopping", []) or []
    if primary_shopping:
        return {
            "shopping": primary_shopping,
            "organic": [],
            "query": product,
            "shopping_region": country,
        }
    # Non-GCC primary returned empty — no fallback, just echo the primary
    # region tag so callers know we tried.
    return {
        "shopping": [],
        "organic": [],
        "query": product,
        "shopping_region": country,
    }


async def search_price_organic(
    product: str,
    country: str = "bh",
) -> Dict[str, Any]:
    """
    Organic search for price context — only called when Tier 1 shopping fails.
    Returns organic results for GPT Tier 2 price extraction.
    """
    if not _active_serper_key():
        return {"organic": [], "error": "Search not configured"}

    country_terms = {
        "bh": "Bahrain price BHD buy",
        "sa": "Saudi Arabia price SAR buy",
        "ae": "UAE Dubai price AED buy",
        "kw": "Kuwait price KWD buy",
        "qa": "Qatar price QAR buy",
        "om": "Oman price OMR buy"
    }
    location_term = country_terms.get(country, "price buy")
    search_query = f"{product} {location_term}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await _serper_post(
                client,
                "/search",
                {
                    "q": search_query,
                    "gl": country,
                    "hl": "en",
                    "num": 10
                }
            )

            results = {}
            if response.status_code == 200:
                results = response.json()
                record_usage("serper")

            return {
                "organic": results.get("organic", []),
                "knowledge_graph": results.get("knowledgeGraph"),
                "query": search_query
            }

    except Exception as e:
        logger.error(f"Price organic search error: {e}")
        return {"organic": [], "error": str(e)}


async def search_product_specs(
    product: str,
    category: str = "electronics"
) -> Dict[str, Any]:
    """
    Search for product specifications.
    
    Args:
        product: Product name
        category: Product category for targeted search
    """
    # Category-specific search terms
    category_terms = {
        "electronics": "specifications specs features technical details",
        "grocery": "ingredients nutrition facts details",
        "beauty": "ingredients benefits how to use",
        "fashion": "material size guide care instructions",
        "home": "specifications dimensions features",
    }
    
    spec_terms = category_terms.get(category, "specifications details features")
    query = f"{product} {spec_terms}"
    
    return await search_web(query, num_results=10)


async def search_product_reviews(
    product: str,
    include_video: bool = False
) -> Dict[str, Any]:
    """
    Search for product reviews and ratings.
    
    Args:
        product: Product name
        include_video: Include video review results
    """
    query = f"{product} review rating user experience pros cons"
    
    results = await search_web(query, num_results=10)
    
    if include_video:
        video_results = await search_videos(f"{product} review")
        results["videos"] = video_results.get("videos", [])
    
    return results


async def search_videos(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for videos (reviews, tutorials, etc.)."""
    if not _active_serper_key():
        return {"videos": [], "error": "Search not configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await _serper_post(
                client,
                "/videos",
                {
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            record_usage("serper")
            return response.json()

    except Exception as e:
        logger.error(f"Video search error: {e}")
        return {"videos": [], "error": str(e)}


async def search_images(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for product images."""
    if not _active_serper_key():
        return {"images": [], "error": "Search not configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await _serper_post(
                client,
                "/images",
                {
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            record_usage("serper")
            return response.json()

    except Exception as e:
        # Image search is NON-CRITICAL — the image pipeline (ProductImage's
        # 4-state fallback) degrades to a placeholder, so a failure here NEVER
        # breaks the comparison. Log at WARNING (not ERROR → Sentry noise:
        # PYTHON-FASTAPI-M/-K, super-low actionability, 0 users) and include the
        # exception TYPE so an empty str(e) (some httpx/transient errors carry no
        # message) is still debuggable.
        logger.warning(
            f"Image search failed (non-critical, placeholder fallback): "
            f"{type(e).__name__}: {e}"
        )
        return {"images": [], "error": str(e)}


async def search_news(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for recent news about a product."""
    if not _active_serper_key():
        return {"news": [], "error": "Search not configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await _serper_post(
                client,
                "/news",
                {
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            record_usage("serper")
            return response.json()

    except Exception as e:
        logger.error(f"News search error: {e}")
        return {"news": [], "error": str(e)}


# ============================================
# GCC Store-specific searches
# ============================================

GCC_RETAILERS = {
    "bahrain": [
        "carrefour bahrain",
        "lulu hypermarket bahrain",
        "sharaf dg bahrain",
        "virgin megastore bahrain",
        "best al yousifi",
        "ashraf"
    ],
    "saudi_arabia": [
        "amazon.sa",
        "jarir bookstore",
        "extra stores",
        "carrefour saudi",
        "noon.com"
    ],
    "uae": [
        "amazon.ae",
        "noon.com",
        "sharaf dg",
        "carrefour uae",
        "lulu hypermarket"
    ],
    "kuwait": [
        "xcite kuwait",
        "best al yousifi",
        "carrefour kuwait",
        "lulu hypermarket"
    ],
    "qatar": [
        "carrefour qatar",
        "lulu hypermarket qatar",
        "jarir bookstore qatar",
        "virgin megastore qatar"
    ],
    "oman": [
        "carrefour oman",
        "lulu hypermarket oman",
        "sharaf dg oman"
    ]
}


async def search_gcc_retailer_prices(
    product: str,
    region: str = "bahrain"
) -> List[Dict[str, Any]]:
    """
    Search specific GCC retailers for prices.
    
    Returns list of prices from different retailers.
    """
    retailers = GCC_RETAILERS.get(region, GCC_RETAILERS["bahrain"])
    results = []
    
    # Search top 3 retailers
    for retailer in retailers[:3]:
        query = f"{product} {retailer} price"
        search_result = await search_web(query, num_results=3)
        
        results.append({
            "retailer": retailer,
            "results": search_result.get("organic", [])[:2]
        })
    
    return results


# ============================================
# Utility functions
# ============================================

def extract_prices_from_text(text: str, currency: str = "BHD") -> List[Dict]:
    """
    Extract price patterns from text.
    
    Patterns:
    - BHD 99.99
    - 99.99 BHD
    - BD 99.99
    - $99.99
    """
    import re
    
    patterns = [
        # BHD/BD patterns
        r'(?:BHD|BD)\s*(\d+(?:\.\d{1,3})?)',
        r'(\d+(?:\.\d{1,3})?)\s*(?:BHD|BD)',
        # SAR patterns
        r'(?:SAR|SR)\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:SAR|SR)',
        # AED patterns
        r'(?:AED|DHS?)\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:AED|DHS?)',
        # USD patterns
        r'\$\s*(\d+(?:\.\d{1,2})?)',
        # Generic number with decimal
        r'(\d+\.\d{2,3})\s*(?:dinar|riyal)?'
    ]
    
    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match)
                if 0.1 < amount < 10000:  # Reasonable price range
                    prices.append({
                        "amount": amount,
                        "currency": currency,
                        "raw_text": match
                    })
            except ValueError:
                continue
    
    return prices
