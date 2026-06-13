"""Review Service — all review-related functions extracted from structured_comparison_service.

Functions are standalone (no self).
FIX M5: _clean_review_citations processes review_summary.highlights[].point format.
FIX M6: Removed dead code processing detailed_praises/detailed_complaints (never populated).
"""
import asyncio
import os
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from app.services.extraction_service import (
    extract_reviews,
    get_reviews_cache_key,
)
from app.services.serper_service import search_web
from app.services.cache_service import get_cached, set_cached
from app.services.api_budget_service import has_budget, record_usage

logger = logging.getLogger(__name__)

# Cache TTL
REVIEWS_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days

# Category-specific review search terms
# L2.10 — added 4 missing entries (supplements/fragrances/haircare/other) so
# every category in CATEGORY_SPEC_SCHEMAS has its own review-search term
# vocabulary. Previously these fell back to the implicit "user reviews pros
# cons rating" string, which yielded weak Serper organic results for
# supplements (no dosage/clinical context) and fragrances (no
# longevity/sillage signal).
CATEGORY_REVIEW_TERMS = {
    "electronics": "user reviews pros cons battery camera performance display",
    "grocery": "user reviews taste quality ingredients value",
    "beauty": "user reviews results skin ingredients effectiveness",
    "makeup": "user reviews shade match coverage finish wear",
    "skincare": "user reviews skin texture irritation results",
    "fashion": "user reviews fit quality comfort sizing",
    "home": "user reviews quality durability assembly value",
    "sports": "user reviews performance comfort durability",
    "supplements": "user reviews dosage effectiveness side effects clinical purity",
    "fragrances": "user reviews longevity sillage projection scent character season",
    "haircare": "user reviews results frizz scalp hair type texture scent",
    "other": "user reviews quality value durability function",
}

GARBAGE_PATTERNS = [
    r"learn more about",
    r"see (full |more )?details",
    r"click (here|to)",
    r"read more",
    r"shop now",
    r"free (shipping|delivery|returns)",
    r"add to (cart|bag|wishlist)",
    r"available (in|at) (stores|select)",
    r"sign up for",
    r"join (our|the) (newsletter|waitlist)",
]

NEGATIVE_INDICATORS = {
    "bad", "poor", "disappointing", "issue", "problem", "broke", "broken",
    "flimsy", "cheap", "overpriced", "uncomfortable", "fragile", "peeling",
    "fading", "cracking", "defect", "flaw", "mediocre", "underwhelming",
    "lacking", "missing", "difficult", "annoying", "frustrating", "worse", "worst",
}

POSITIVE_INDICATORS = {
    "great", "excellent", "premium", "beautiful", "perfect", "love",
    "amazing", "wonderful", "fantastic", "superb", "outstanding", "impressive",
    "comfortable", "luxurious", "elegant", "sturdy", "durable", "quality",
}


def clean_review_content(reviews: dict) -> dict:
    """Remove garbage text, short items, and misclassified sentiments from reviews."""
    for section in ["common_praises", "common_complaints"]:
        items = reviews.get(section, [])
        if not items:
            continue
        cleaned = []
        for item in items:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if any(re.search(p, text, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                continue
            if len(text.split()) < 8:
                continue
            if "complaint" in section:
                words = set(text.lower().split())
                has_negative = bool(words & NEGATIVE_INDICATORS)
                has_positive = bool(words & POSITIVE_INDICATORS)
                if has_positive and not has_negative:
                    continue
            cleaned.append(item)
        reviews[section] = cleaned

    # FIX M5: Also clean review_summary.highlights[].point
    review_summary = reviews.get("review_summary", {})
    if isinstance(review_summary, dict):
        highlights = review_summary.get("highlights", [])
        if highlights and isinstance(highlights, list):
            cleaned_highlights = []
            for h in highlights:
                if isinstance(h, dict):
                    point = h.get("point", "")
                    if any(re.search(p, point, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                        continue
                    if len(point.split()) < 4:
                        continue
                    cleaned_highlights.append(h)
                else:
                    cleaned_highlights.append(h)
            review_summary["highlights"] = cleaned_highlights

    return reviews


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or ""
    except Exception:
        return ""


def clean_review_citations(reviews: dict, search_results: list) -> dict:
    """Replace [snippet_N] with source domain name in review text fields.

    FIX M5: Now processes review_summary.highlights[].point format (current format).
    FIX M6: Removed dead code for detailed_praises/detailed_complaints (never populated).
    """
    snippet_source_map = {}
    for i, result in enumerate(search_results or []):
        link = result.get("link", "")
        if link:
            snippet_source_map[str(i + 1)] = _extract_domain(link)

    def replace_citation(text: str) -> str:
        def replacer(match):
            snippet_num = match.group(1)
            domain = snippet_source_map.get(snippet_num, "")
            if domain:
                return f"Per {domain}: "
            return ""
        return re.sub(r'\[snippet_(\d+)\]\s*', replacer, text)

    cleaned = dict(reviews)

    # Legacy fields (common_praises, common_complaints)
    for key in ["common_praises", "common_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            cleaned[key] = [replace_citation(str(item)) for item in cleaned[key]]

    # FIX M5: Current format — review_summary.highlights[].point
    review_summary = cleaned.get("review_summary", {})
    if isinstance(review_summary, dict):
        highlights = review_summary.get("highlights", [])
        if highlights and isinstance(highlights, list):
            for h in highlights:
                if isinstance(h, dict) and "point" in h:
                    h["point"] = replace_citation(str(h["point"]))

    return cleaned


def format_review_search_results(results: Dict, retailer_ratings: List[Dict]) -> str:
    """Format search results for review extraction."""
    if not results:
        return "No search results available."

    formatted = []

    organic = results.get("organic", [])[:10]
    for i, r in enumerate(organic):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        domain = ""
        if link:
            try:
                domain = urlparse(link).netloc.replace("www.", "")
            except Exception:
                pass
        prefix = f"[{domain}] " if domain else ""
        formatted.append(f"{i+1}. {prefix}{title}\n   {snippet}")

    if retailer_ratings:
        formatted.append("\n--- Retailer Ratings (from shopping data) ---")
        for r in retailer_ratings:
            count_str = f" ({r['review_count']} reviews)" if r.get("review_count") else ""
            formatted.append(f"- {r['source']}: {r['rating']}/5{count_str}")

    return "\n".join(formatted)


async def get_reviews(
    brand: str,
    name: str,
    variant: Optional[str],
    search_query: str,
    nocache: bool = False,
    category: str = "other",
    retailer_ratings: Optional[List[Dict]] = None,
    search_results: Optional[Dict] = None,
    track_serper_cost_fn=None,
    track_gpt_cost_fn=None,
) -> Dict[str, Any]:
    """Get reviews with caching (L1: Redis, L2: DB)."""
    import asyncio
    cache_key = get_reviews_cache_key(brand, name, variant)

    cached = get_cached(cache_key) if not nocache else None
    if cached:
        logger.info(f"Reviews cache hit: {cache_key}")
        cached["_cached"] = True
        return cached

    # L2: Check DB before API call
    if not nocache:
        from app.services.product_data_service import get_cached_reviews
        db_reviews = await get_cached_reviews(cache_key)
        if db_reviews:
            set_cached(cache_key, db_reviews, REVIEWS_CACHE_TTL)
            db_reviews["_cached"] = True
            db_reviews["_cache_source"] = "db"
            return db_reviews

    review_terms = CATEGORY_REVIEW_TERMS.get(category, "user reviews pros cons rating")
    logger.info(f"Fetching reviews for: {brand} {name} (category: {category})")
    if search_results is None:
        search_results = await search_web(f"{search_query} {review_terms}")
        if track_serper_cost_fn:
            track_serper_cost_fn()

    search_context = format_review_search_results(
        search_results, retailer_ratings or []
    )

    reviews, usage = await extract_reviews(brand, name, variant, search_context, category=category)
    if track_gpt_cost_fn:
        track_gpt_cost_fn(usage)

    if retailer_ratings:
        reviews["source_ratings"] = retailer_ratings

    # F3 (G2): persist the COMPLETED extraction BEFORE the optional consult.
    # The consult can run inside the outer 10s reviews-race wait_for; if that
    # cap fires DURING the consult, this coroutine is cancelled — so the cache
    # write MUST happen first, otherwise the finished extract_reviews result is
    # lost (PYTHON-FASTAPI-J pattern). After this point the extraction is safe
    # regardless of what the consult does.
    extraction_persisted = False
    if reviews and not reviews.get("error"):
        set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
        from app.services.product_data_service import save_reviews
        asyncio.create_task(save_reviews(cache_key, brand, name, variant, reviews))
        extraction_persisted = True

    # S2 I2.5 — optional review-content consultation from usage="review" GCC
    # sources. Flag-gated (ENABLE_REVIEW_SOURCE_CONSULT, default OFF → no-op),
    # never critical-path: any miss/timeout yields [] and the already-persisted
    # reviews ship as-is. consult_review_sources is itself wait_for-capped
    # (active mode) / synchronous (passive mode).
    try:
        consult = await consult_review_sources(
            brand, name, variant, category, search_results,
            track_serper_cost_fn=track_serper_cost_fn,
        )
        if consult and isinstance(reviews, dict):
            reviews["review_source_quotes"] = consult
            # Re-cache the enriched copy so a subsequent cache hit carries the
            # quotes too (the pre-consult write already protected the baseline).
            if extraction_persisted:
                set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
    except Exception as e:  # noqa: BLE001 — defensive; consult is best-effort
        logger.warning("[I2.5] consult_review_sources wiring error: %s", e)

    reviews["_cached"] = False
    return reviews


# ---------- L2.11: per-retailer review-quote fetcher (Y from design) ----------

# Retailer-specific Serper site-filters. Order is the design priority:
# Amazon (deepest review depth) -> Noon (GCC native) -> X (social/word of mouth).
RETAILER_QUOTE_SITES = [
    ("Amazon", "amazon.com OR amazon.ae"),
    ("Noon", "noon.com"),
    ("X", "x.com OR twitter.com"),
]

# Cache per product 14d — review quote is stable.
_RETAILER_QUOTES_CACHE_TTL = 14 * 24 * 60 * 60


def _quote_cache_key(brand: str, name: str, variant: str | None) -> str:
    parts = [brand or "", name or "", variant or ""]
    return "retailer_quotes:" + "|".join(p.strip().lower() for p in parts)


async def fetch_retailer_quotes(
    brand: str,
    name: str,
    variant: str | None,
    track_serper_cost_fn=None,
) -> list:
    """L2.11 — fetch up to 3 per-retailer review snippets in parallel.

    Returns a list of ``{retailer, rating, text}`` entries (max 3). Each entry
    comes from a single Serper site-filtered organic search. Quote text is the
    first organic snippet of length > 20 chars; rating is extracted from the
    Serper richSnippet when present, otherwise None.

    Caches per product 14 days. ~$0.003 net cost per cache miss (3x Serper).
    """
    cache_key = _quote_cache_key(brand, name, variant)
    cached = get_cached(cache_key)
    if cached and isinstance(cached, dict) and isinstance(cached.get("quotes"), list):
        return cached["quotes"]

    product_query = f"{brand} {name} {variant or ''} review".strip()

    async def _one(retailer: str, site_filter: str):
        # B0-C-2: gate every Serper site-search behind has_budget("serper") so
        # the 2200-credit lifetime quota cannot be drained by retailer-quote
        # traffic (3 calls per product, 6 per compare). fail-open on Redis down
        # is inherited from has_budget(); record_usage on success keeps the
        # counter accurate for subsequent guards.
        if not has_budget("serper"):
            logger.info("[L2.11] retailer quote skipped — serper budget exhausted: %s", retailer)
            return None
        try:
            q = f'{product_query} site:{site_filter}'.strip()
            result = await search_web(q, num_results=5)
            # L5.1 (S3): NO manual record_usage("serper") here — search_web
            # records the budget meter internally on success
            # (serper_service.py:94). A manual call double-counted every credit
            # (3 retailers x 2 products = 6 calls/compare metered as 12). Same
            # bug class as F4/G2 fixed in fetch_review_source_snippets (9ee695c).
            # track_serper_cost_fn is the separate per-request cost tracker (not
            # the budget meter) so it stays.
            if track_serper_cost_fn:
                track_serper_cost_fn()
        except Exception as e:
            logger.warning("[L2.11] retailer quote fetch failed for %s: %s", retailer, e)
            return None
        organic = (result or {}).get("organic", []) or []
        for item in organic:
            snippet = (item.get("snippet") or "").strip()
            if len(snippet) < 20:
                continue
            rating = None
            rich = item.get("richSnippet") or {}
            top = rich.get("top") if isinstance(rich, dict) else None
            if isinstance(top, dict):
                detected = top.get("detected_extensions") or {}
                rating_val = detected.get("rating") or detected.get("starRating")
                if isinstance(rating_val, (int, float)):
                    rating = float(rating_val)
            return {"retailer": retailer, "rating": rating, "text": snippet}
        return None

    tasks = [_one(r, s) for r, s in RETAILER_QUOTE_SITES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    quotes = []
    for r in results:
        if isinstance(r, Exception) or r is None:
            continue
        quotes.append(r)
        if len(quotes) >= 3:
            break

    if quotes:
        set_cached(cache_key, {"quotes": quotes}, _RETAILER_QUOTES_CACHE_TTL)
    return quotes


# ---------- S2 I2.5: review-content consultation from usage="review" sources ----------

# Cache per product 14d — editorial review content is stable.
_REVIEW_SOURCE_CACHE_TTL = 14 * 24 * 60 * 60


def _review_source_cache_key(brand: str, name: str, variant: str | None, category: str) -> str:
    parts = [brand or "", name or "", variant or "", category or ""]
    return "review_source_snippets:" + "|".join(p.strip().lower() for p in parts)


async def fetch_review_source_snippets(
    brand: str,
    name: str,
    variant: str | None,
    category: str,
    track_serper_cost_fn=None,
) -> list:
    """S2 I2.5 — consult registry sources flagged usage in ("review","both")
    for editorial review snippets (e.g. the Arabic GCC sources sayidaty.net /
    khaleejtimes.com / gulfnews.com for beauty/fashion).

    ONE Serper `site:`-filtered organic search across the category's review
    sources. Budget-gated (`has_budget("serper")`), cached per product 14d.
    Returns a list of ``{domain, text}`` (max 3) or ``[]`` on miss / no review
    sources / budget-exhausted / timeout — NEVER raises, NEVER critical-path.
    The caller wraps this in asyncio.wait_for so a slow Serper call cannot drag
    the reviews race past its budget.
    """
    from app.services.source_router import get_sources_for_category

    review_sources = get_sources_for_category(category, usage="review")
    if not review_sources:
        return []  # category has no review-content sources — no-op

    cache_key = _review_source_cache_key(brand, name, variant, category)
    cached = get_cached(cache_key)
    if cached and isinstance(cached, dict) and isinstance(cached.get("snippets"), list):
        return cached["snippets"]

    if not has_budget("serper"):
        logger.info("[I2.5] review-source consult skipped — serper budget exhausted")
        return []

    domains = [s.domain for s in review_sources][:5]
    site_filter = " OR ".join(f"site:{d}" for d in domains)
    product_query = f"{brand} {name} {variant or ''} review".strip()
    query = f"{product_query} {site_filter}".strip()

    try:
        # F4 (G2): NO manual record_usage("serper") here — search_web already
        # records the budget meter internally (serper_service.py:94), and only
        # on success. A manual call here double-counted the credit AND counted
        # failed calls. track_serper_cost_fn is the separate per-request cost
        # tracker (not the budget meter) so it stays.
        result = await search_web(query, num_results=6)
        if track_serper_cost_fn:
            track_serper_cost_fn()
    except Exception as e:  # noqa: BLE001
        logger.warning("[I2.5] review-source consult fetch failed: %s", e)
        return []

    organic = (result or {}).get("organic", []) or []
    snippets = []
    for item in organic:
        snippet = (item.get("snippet") or "").strip()
        if len(snippet) < 20:
            continue
        link = item.get("link", "") or ""
        link_domain = urlparse(link).netloc.replace("www.", "").lower()
        snippets.append({"domain": link_domain, "text": snippet})
        if len(snippets) >= 3:
            break

    if snippets:
        set_cached(cache_key, {"snippets": snippets}, _REVIEW_SOURCE_CACHE_TTL)
    return snippets


def review_source_consult_mode() -> Optional[str]:
    """Read ENABLE_REVIEW_SOURCE_CONSULT fresh each call (default OFF).

    Returns "active" | "passive" | None.
    - "active" (EXPLICIT only) → fires the dedicated budget-gated Serper
      site-search. This is the ONLY value that spends a Serper credit, so it is
      deliberately NOT reachable via a generic truthy flip.
    - "passive" OR any other truthy value ("true"/"1"/"on") → reuses the
      already-fetched unified search organic (zero extra Serper). F3 (G2):
      truthy defaults to the SAFE passive mode so a careless `=true` flip can't
      silently start burning Serper credits.
    - unset / "false" / anything else → None (feature OFF).
    Read fresh (not process-cached) so I4 can A/B both modes at G5.
    """
    raw = os.environ.get("ENABLE_REVIEW_SOURCE_CONSULT", "").strip().lower()
    if raw == "active":
        return "active"
    if raw in ("passive", "true", "1", "on"):
        return "passive"
    return None


def passive_review_snippets(
    search_results: Optional[Dict], category: str
) -> list:
    """PASSIVE mode (zero extra Serper): scan the already-fetched unified
    search organic for hits on the category's usage="review" registry domains.
    Returns up to 3 {domain, text} entries, [] on miss."""
    from app.services.source_router import get_sources_for_category

    review_sources = get_sources_for_category(category, usage="review")
    if not review_sources or not search_results:
        return []
    review_domains = {s.domain.lower() for s in review_sources}
    organic = (search_results or {}).get("organic", []) or []
    snippets = []
    for item in organic:
        link = item.get("link", "") or ""
        link_domain = urlparse(link).netloc.replace("www.", "").lower()
        # match registry domain (incl. subdomains)
        matched = any(
            link_domain == d or link_domain.endswith("." + d) for d in review_domains
        )
        if not matched:
            continue
        snippet = (item.get("snippet") or "").strip()
        if len(snippet) < 20:
            continue
        snippets.append({"domain": link_domain, "text": snippet})
        if len(snippets) >= 3:
            break
    return snippets


async def consult_review_sources(
    brand: str,
    name: str,
    variant: str | None,
    category: str,
    search_results: Optional[Dict],
    track_serper_cost_fn=None,
    timeout: float = 4.0,
) -> list:
    """S2 I2.5 mode dispatcher. OFF (default) -> []; passive -> scan existing
    organic (sync, instant); active -> dedicated budget-gated Serper call
    (wait_for-capped). NEVER raises, NEVER critical-path — any error/timeout
    yields []."""
    mode = review_source_consult_mode()
    if mode is None:
        return []
    try:
        if mode == "passive":
            return passive_review_snippets(search_results, category)
        # active
        return await asyncio.wait_for(
            fetch_review_source_snippets(
                brand, name, variant, category,
                track_serper_cost_fn=track_serper_cost_fn,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.info("[I2.5] review-source consult timed out (mode=%s)", mode)
        return []
    except Exception as e:  # noqa: BLE001
        logger.warning("[I2.5] review-source consult error (mode=%s): %s", mode, e)
        return []
