"""Price Service — all price-related functions extracted from structured_comparison_service.

Functions are standalone (no self) — pass shopping_items_cache dict where needed.
"""
import os
import re
import json
import time
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, quote_plus

import httpx

from app.services.extraction_service import (
    extract_price,
    extract_price_from_training_data,
    get_price_cache_key,
    GCC_REGIONS,
)
from app.services.serper_service import search_product_prices, search_price_organic, search_web
from app.services.cache_service import get_cached, set_cached
from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed,
)
from app.services import firecrawl_service, scrapedo_service

ENABLE_PAGE_SCRAPE = os.environ.get("ENABLE_PAGE_SCRAPE", "true").lower() != "false"

logger = logging.getLogger(__name__)


def _median(values: List[float]) -> float:
    """Median that returns the arithmetic mean of the middle two for
    even-length lists (standard statistical median)."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def consolidate_price_sources(sources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """L2.8 — cross-validation across multiple price candidates.

    Takes a list of source dicts (``{"src": str, "amount": float,
    "retailer_score": float?}``) and returns ``{"amount": median,
    "sources_count": int, "flags": [str], "cross_validation":
    "passed"|"single_source"}`` or ``None`` if no usable sources exist.

    Outlier rejection rule: when there are 3+ sources, drop any value more
    than 2 standard deviations from the mean, then re-compute the median
    of the remaining values.

    Disagreement flag: when any surviving value differs by more than 20%
    from the consolidated median, ``"sources_disagree"`` is appended to
    ``flags`` (the consolidated number is still returned — caller decides
    whether to suppress).
    """
    if not sources:
        return None

    amounts = [
        float(s["amount"])
        for s in sources
        if s.get("amount") is not None and float(s["amount"]) > 0
    ]
    if not amounts:
        return None

    flags: List[str] = []

    if len(amounts) == 1:
        return {
            "amount": amounts[0],
            "sources_count": 1,
            "flags": flags,
            "cross_validation": "single_source",
        }

    # Outlier rejection — anchor on the median (robust to skew). Anything
    # outside [0.5x, 2x] of the initial median is treated as a bogus listing
    # (counterfeit, garbled price string, wrong currency). Median-anchored
    # is more reliable than stdev when 1 of 3 samples is an order of
    # magnitude off, because that single value dominates the stdev.
    survivors = list(amounts)
    if len(amounts) >= 3:
        initial_median = _median(amounts)
        if initial_median > 0:
            new_survivors = [
                a for a in amounts
                if 0.5 * initial_median <= a <= 2.0 * initial_median
            ]
            if new_survivors and len(new_survivors) < len(amounts):
                survivors = new_survivors
                flags.append("outlier_dropped")

    consolidated = _median(survivors)

    # Disagreement flag — any survivor >20% from the consolidated median.
    if consolidated > 0 and any(
        abs(a - consolidated) / consolidated > 0.20 for a in survivors
    ):
        flags.append("sources_disagree")

    return {
        "amount": consolidated,
        "sources_count": len(sources),
        "flags": flags,
        "cross_validation": "passed",
    }


# Pattern for stripping model variants to broaden price searches
MODEL_VARIANT_PATTERN = re.compile(r'\s+(pro|plus|max|ultra|\d{2,}gb|\d+tb)$', re.IGNORECASE)

# Cache TTL
PRICE_CACHE_TTL = 24 * 60 * 60  # 24 hours

# Retailer quality tiers
RETAILER_TIERS = {
    # Tier 1: Official stores & major authorized retailers (score 1.0)
    "amazon": 1.0, "apple": 1.0, "samsung": 1.0, "best buy": 1.0,
    "bestbuy": 1.0, "walmart": 1.0, "target": 1.0, "noon": 1.0,
    "jarir": 1.0, "extra": 1.0, "lulu": 1.0, "carrefour": 1.0,
    "sharaf dg": 1.0, "virgin megastore": 1.0, "microsof": 1.0,
    "google store": 1.0, "oneplus": 1.0, "sony": 1.0, "dell": 1.0,
    "hp store": 1.0, "lenovo": 1.0, "iherb": 1.0, "vitacost": 1.0, "gnc": 1.0,
    # Tier 1: Luxury fashion official + authorized retailers
    "hermes": 1.0, "hermès": 1.0, "louis vuitton": 1.0, "louisvuitton": 1.0,
    "chanel": 1.0, "gucci": 1.0, "prada": 1.0, "dior": 1.0, "burberry": 1.0,
    "fendi": 1.0, "nordstrom": 1.0, "farfetch": 1.0, "ssense": 1.0,
    "net-a-porter": 1.0, "harrods": 1.0, "selfridges": 1.0,
    "sephora": 1.0, "ulta": 1.0,
    # Tier 2: Reputable specialty retailers (score 0.7)
    "newegg": 0.7, "b&h": 0.7, "bhphoto": 0.7, "adorama": 0.7,
    "costco": 0.7, "ubuy": 0.7, "micro center": 0.7, "john lewis": 0.7,
    "currys": 0.7, "fnac": 0.7,
    # Tier 3: Marketplaces with mixed new/used/refurb (score 0.3)
    "ebay": 0.3, "aliexpress": 0.3, "alibaba": 0.3, "temu": 0.3,
    "wish": 0.3, "dhgate": 0.3, "banggood": 0.3, "gearbest": 0.3,
    "etsy": 0.3, "mercari": 0.3, "swappa": 0.3, "backmarket": 0.3,
    "back market": 0.3, "refurbished": 0.3,
}
DEFAULT_RETAILER_SCORE = 0.5

# Retailer search URL templates
RETAILER_SEARCH_URLS = {
    "amazon": "https://www.amazon.com/s?k={query}",
    "amazon.ae": "https://www.amazon.ae/s?k={query}",
    "amazon.sa": "https://www.amazon.sa/s?k={query}",
    "walmart": "https://www.walmart.com/search?q={query}",
    "best buy": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
    "bestbuy": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
    "target": "https://www.target.com/s?searchTerm={query}",
    "costco": "https://www.costco.com/CatalogSearch?dept=All&keyword={query}",
    "newegg": "https://www.newegg.com/p/pl?d={query}",
    "b&h": "https://www.bhphotovideo.com/c/search?q={query}",
    "bhphoto": "https://www.bhphotovideo.com/c/search?q={query}",
    "adorama": "https://www.adorama.com/l/?searchinfo={query}",
    "micro center": "https://www.microcenter.com/search/search_results.aspx?Ntt={query}",
    "noon": "https://www.noon.com/search?q={query}",
    "jarir": "https://www.jarir.com/sa-en/catalogsearch/result/?q={query}",
    # L1.3 (Bundle B S3) — Bahrain-correct retailer URLs. Pre-S3 these pointed
    # at the wrong GCC country (extra=/en-sa Saudi, sharaf dg=uae.*), while the
    # registry (source_router.py) uses bahrain.sharafdg.com. Align the direct
    # URL builder so the Tier 1.5 cascade lands on the Bahrain storefront.
    # Templates control-calibrated LIVE (HTTP 200 + BHD product content) in the
    # same env — see L1_DIAGNOSTIC_bh_scrapeability.md. extra.com BH search uses
    # the `text=` param (`q=` lands on /en-bh/error); sharafdg BH is WooCommerce
    # `?s=...&post_type=product`.
    "extra": "https://www.extra.com/en-bh/search?text={query}",
    # Both keys map to the BH WooCommerce search: "sharaf dg" (the human
    # retailer name, used by Serper-source matching) AND "sharafdg" (the bare
    # form so the registry DOMAIN bahrain.sharafdg.com — which has no space —
    # resolves via build_retailer_url for the direct-BH injector).
    "sharaf dg": "https://bahrain.sharafdg.com/?s={query}&post_type=product",
    "sharafdg": "https://bahrain.sharafdg.com/?s={query}&post_type=product",
    "ubuy": "https://www.ubuy.com.bh/en/search?q={query}",
    # lulu: the bare host (www.luluhypermarket.com) catalog is en-ae/AED and
    # redirects to gcc.luluhypermarket.com/en-bh/ — point straight at the GCC
    # Bahrain storefront so the price comes back in BHD (the AED-vs-BHD host bug
    # was THE electronics keystone; registry retargeted to match).
    "lulu": "https://gcc.luluhypermarket.com/en-bh/search/?q={query}",
    "carrefour": "https://www.carrefouruae.com/mafuae/en/search?q={query}",
    "virgin megastore": "https://www.virginmegastore.ae/search/{query}",
    "apple": "https://www.apple.com/shop/buy?fh={query}",
    "samsung": "https://www.samsung.com/search/?searchvalue={query}",
    "dell": "https://www.dell.com/en-us/search/{query}",
    "lenovo": "https://www.lenovo.com/us/en/search?query={query}",
    "currys": "https://www.currys.co.uk/search/{query}",
    "john lewis": "https://www.johnlewis.com/search?search-term={query}",
    "fnac": "https://www.fnac.com/SearchResult/ResultList.aspx?Search={query}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={query}",
    "aliexpress": "https://www.aliexpress.com/wholesale?SearchText={query}",
    "temu": "https://www.temu.com/search_result.html?search_key={query}",
    "back market": "https://www.backmarket.com/en-us/search?q={query}",
    "backmarket": "https://www.backmarket.com/en-us/search?q={query}",
    "swappa": "https://swappa.com/search?q={query}",
    "iherb": "https://bh.iherb.com/search?kw={query}",
    "vitacost": "https://www.vitacost.com/search?t={query}",
    "nasser pharmacy": "https://www.nasserpharmacy.com/search?q={query}",
    "boots": "https://www.bn.boots.com/search?q={query}",
    "al deerah": "https://aldeerahpharmacy.com/catalogsearch/result/?q={query}",
    # L1.3 (Bundle B S3) — verified-live Bahrain retailers (control-calibrated,
    # HTTP 200 + BHD product content, L1_DIAGNOSTIC_bh_scrapeability.md). Both
    # `shopalmoayyed` + `asgharali` are Shopify (static JSON-LD prices — the
    # cascade scrapes them cleanly without render credits); bahrainpharmacy is
    # WordPress `?s=`. Two key spellings each so the substring match in
    # build_retailer_url catches both "Al Moayyed"/"shopalmoayyed" and
    # "Asghar Ali"/"asgharali" source-name forms.
    "almoayyed": "https://www.shopalmoayyed.com/search?q={query}",
    "al moayyed": "https://www.shopalmoayyed.com/search?q={query}",
    "asgharali": "https://bh.asgharali.com/search?q={query}",
    "asghar ali": "https://bh.asgharali.com/search?q={query}",
    "bahrain pharmacy": "https://bahrainpharmacy.com/?s={query}",
}

# Accessory keywords
ACCESSORY_KEYWORDS = {
    "case", "cover", "protector", "charger", "cable", "adapter", "holder",
    "stand", "strap", "sleeve", "pouch", "film", "tempered", "glass",
    "mount", "grip", "wallet", "skin", "bumper", "shell", "screen protector",
    "armband", "holster", "dock", "cradle", "earbuds", "headphone",
    "stylus", "pen", "keyboard", "mouse",
}

# High-value electronics keywords
HIGH_VALUE_KEYWORDS = {
    "iphone", "galaxy", "pixel", "samsung", "oneplus", "huawei", "xiaomi",
    "macbook", "ipad", "laptop", "playstation", "xbox", "nintendo",
    "rtx", "nvidia", "geforce", "radeon", "amd", "gpu",
}

# Counterfeit/replica keywords
COUNTERFEIT_KEYWORDS = {
    "replica", "fake", "dupe", "inspired by", "inspired",
    "knockoff", "knock-off", "imitation", "copy",
    "look alike", "lookalike", "designer inspired",
    "unbranded", "generic", "homage", "alternative",
    "pre-owned", "used", "vintage", "secondhand", "second hand",
}

# Luxury brand keywords
LUXURY_BRAND_KEYWORDS = {
    "louis vuitton", "lv", "hermes", "hermès", "chanel", "gucci", "prada",
    "dior", "burberry", "fendi", "balenciaga", "versace", "givenchy",
    "ysl", "saint laurent", "cartier", "rolex", "omega", "patek philippe",
    "tag heuer", "tiffany", "tom ford", "bottega veneta", "valentino",
    "celine", "loewe", "moncler", "balmain", "alexander mcqueen",
}

# Official brand domains
OFFICIAL_BRAND_DOMAINS = {
    "hermes.com", "louisvuitton.com", "chanel.com", "gucci.com", "prada.com",
    "dior.com", "burberry.com", "fendi.com", "balenciaga.com", "cartier.com",
    "rolex.com", "omegawatches.com", "tiffany.com", "tomford.com",
    "apple.com", "samsung.com", "sony.com", "dell.com", "hp.com",
    "nordstrom.com", "farfetch.com", "ssense.com", "net-a-porter.com",
    "sephora.com", "harrods.com", "selfridges.com",
}

# Authorized luxury retailers
AUTHORIZED_LUXURY_RETAILERS = {
    "farfetch.com", "ssense.com", "net-a-porter.com",
    "mytheresa.com", "matchesfashion.com", "nordstrom.com",
}

# GCC luxury retailers
GCC_LUXURY_RETAILERS = {
    "ounass.ae", "ounass.com", "namshi.com", "bloomingdales.ae",
    "level-shoes.com", "harveynichols.com", "galerieslafayette.ae",
    "theluxurycloset.com", "boutique1.com",
}

# Supplement keywords
SUPPLEMENT_KEYWORDS = {
    "vitamin", "supplement", "softgel", "capsule", "mineral",
    "omega", "probiotic", "protein", "magnesium", "zinc", "calcium",
    "fish oil", "collagen", "biotin", "melatonin", "turmeric", "creatine",
    "multivitamin", "iron", "folic", "coq10", "glucosamine",
    "d3", "d-3",
    "nature made", "now foods", "solgar", "garden of life", "kirkland",
}

# Manufacturer brands (AIB partners)
MANUFACTURER_BRAND_WORDS = {"nvidia", "amd", "intel"}

# Bahrain pharmacy domains
PHARMACY_DOMAINS = {
    "bolo.bh": "Bolo",
    "bn.boots.com": "Boots",
    "aldeerahpharmacy.com": "Al Deerah Pharmacy",
}

# Currency detection patterns
CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR", "¥": "JPY"}
CURRENCY_CODES = {
    "USD": "USD", "GBP": "GBP", "EUR": "EUR", "JPY": "JPY",
    "AED": "AED", "SAR": "SAR", "BHD": "BHD", "KWD": "KWD",
    "QAR": "QAR", "OMR": "OMR", "INR": "INR",
}

PAGE_SCRAPE_TIMEOUT = 5
TIER_15_BUDGET_TIMEOUT = 20


# ============================================
# Currency conversion
# ============================================

def _convert_to_bhd(amount: float, currency: str) -> float:
    """Convert amount to BHD using the central FALLBACK_RATES table.

    Logs a warning if the currency is not in the rate table — this prevents
    the silent-failure mode where unknown currencies were multiplied by 1.0
    and labelled BHD (e.g. SGD values displayed as BHD on luxury queries).
    """
    if not currency:
        return amount
    from app.services.exchange_rate_service import FALLBACK_RATES
    currency_upper = currency.upper()
    if currency_upper not in FALLBACK_RATES:
        logger.warning(
            f"[CURRENCY] No rate for {currency_upper}->BHD, returning amount unchanged. "
            f"Add {currency_upper} to FALLBACK_RATES to enable conversion."
        )
        return amount
    return amount * FALLBACK_RATES[currency_upper]


def _convert_gpt_price_currency(price: Optional[Dict], target_currency: str) -> None:
    """Convert GPT-returned price from original_currency to target currency."""
    if not price or not price.get("amount"):
        return
    original = price.get("original_currency", "").upper()
    if not original or original == target_currency:
        return
    amount = price["amount"]
    amount_bhd = _convert_to_bhd(amount, original)
    if target_currency == "BHD":
        converted = amount_bhd
    else:
        target_bhd_rate = _convert_to_bhd(1.0, target_currency)
        converted = amount_bhd / target_bhd_rate if target_bhd_rate > 0 else amount_bhd
    logger.info(
        f"[PRICE] GPT currency convert: {original} {amount} -> {target_currency} {round(converted, 2)}"
    )
    price["amount"] = round(converted, 2)
    price["currency"] = target_currency


# ============================================
# Validation helpers
# ============================================

def validate_price_query(brand: str, name: str, region: str) -> bool:
    """Gate 0: Reject garbage queries before wasting API credits."""
    full_name = f"{brand} {name}".strip()
    if len(full_name) < 3 or len(full_name) > 200:
        logger.warning(f"[PRICE] Gate 0: rejected query (length {len(full_name)}): {full_name[:50]}")
        return False
    if not full_name[0].isalpha():
        logger.warning(f"[PRICE] Gate 0: rejected query (starts non-alpha): {full_name[:50]}")
        return False
    if region not in GCC_REGIONS:
        logger.warning(f"[PRICE] Gate 0: rejected region: {region}")
        return False
    return True


def validate_scrape_url(url: str) -> bool:
    """Reject URLs that waste rendering credits (search/category pages)."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc or "." not in parsed.netloc:
            return False
        path_lower = parsed.path.lower()
        blocked_patterns = ["/search", "/category", "/collection", "/c/", "/s?k=", "/browse"]
        if any(p in path_lower for p in blocked_patterns):
            logger.info(f"[PRICE] URL validation: rejected non-product URL: {url[:80]}")
            return False
        return True
    except Exception:
        return False


# ============================================
# Detection helpers
# ============================================

def is_counterfeit_listing(title: str) -> bool:
    """Check if a shopping listing title indicates counterfeit/replica/used product."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in COUNTERFEIT_KEYWORDS)


def is_accessory(title: str) -> bool:
    """Check if a shopping result title is an accessory, not the actual product."""
    title_lower = title.lower()
    for kw in ACCESSORY_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
            return True
    return False


def is_high_value_query(product_name: str) -> bool:
    """Check if the query is for a high-value product (phone, laptop, console)."""
    name_lower = product_name.lower()
    return any(kw in name_lower for kw in HIGH_VALUE_KEYWORDS)


def is_luxury_brand(product_name: str) -> bool:
    """Check if the product is from a luxury/designer brand."""
    name_lower = product_name.lower()
    return any(brand in name_lower for brand in LUXURY_BRAND_KEYWORDS)


def is_supplement_query(product_name: str) -> bool:
    """Check if the query is for a supplement/vitamin product."""
    name_lower = product_name.lower()
    if any(kw in name_lower for kw in HIGH_VALUE_KEYWORDS):
        return False
    return any(kw in name_lower for kw in SUPPLEMENT_KEYWORDS)


# ============================================
# Parsing / matching helpers
# ============================================

def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or ""
    except Exception:
        return ""


def parse_price_string(price_str: str) -> Optional[float]:
    """Parse price strings like '$699.99', 'BHD 339.000', 'SAR 2,499'."""
    if not price_str:
        return None
    cleaned = re.sub(r'[A-Z]{2,3}\s*', '', price_str)
    cleaned = re.sub(r'[$£€¥]', '', cleaned)
    cleaned = cleaned.replace(',', '')
    cleaned = cleaned.strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
        if match:
            return float(match.group(1))
        return None


def detect_currency(price_str: str) -> Optional[str]:
    """Detect original currency from a price string."""
    if not price_str:
        return None
    for sym, code in CURRENCY_SYMBOLS.items():
        if sym in price_str:
            return code
    upper = price_str.upper()
    for code in CURRENCY_CODES:
        if code in upper:
            return code
    return None


def normalize_words(text: str) -> set:
    """Normalize words for matching."""
    return set(w.replace("-", "").strip(",.()&:;'\"") for w in text.lower().split() if w.strip(",.()&:;'\""))


def numbers_match(product_name: str, title: str) -> bool:
    """Check that significant numbers in product name appear in title."""
    product_numbers = set(re.findall(r'\b(\d{2,})\b', product_name))
    if not product_numbers:
        return True
    title_numbers = set(re.findall(r'\b(\d{2,})\b', title))
    return bool(product_numbers & title_numbers)


def strict_title_match(product_name: str, title: str) -> bool:
    """Key words from the product name must appear in the shopping title."""
    if is_counterfeit_listing(title):
        return False
    title_normalized = title.lower().replace("-", "")
    key_words = [
        w.replace("-", "") for w in product_name.lower().split()
        if len(w.replace("-", "")) > 2
        and w.replace("-", "") not in MANUFACTURER_BRAND_WORDS
    ]
    return all(w in title_normalized for w in key_words)


def get_retailer_score(retailer_name: str) -> float:
    """Score a retailer by quality tier."""
    if not retailer_name:
        return DEFAULT_RETAILER_SCORE
    name_lower = retailer_name.lower()
    for key, score in RETAILER_TIERS.items():
        if key in name_lower:
            return score
    return DEFAULT_RETAILER_SCORE


def has_retailer_url(source: str) -> bool:
    """Check if a source name matches any key in RETAILER_SEARCH_URLS."""
    if not source:
        return False
    source_lower = source.lower().strip()
    return any(key in source_lower for key in RETAILER_SEARCH_URLS)


def build_retailer_url(source: str, product_name: str) -> Optional[str]:
    """Build a retailer search URL from the source name and product name."""
    if not source:
        return None
    source_lower = source.lower().strip()
    for key, template in RETAILER_SEARCH_URLS.items():
        if key in source_lower:
            return template.format(query=quote_plus(product_name))
    return None


def build_direct_bh_candidates(
    full_name: str, category: str
) -> List[Tuple[str, str]]:
    """S3-genuine (team-lead pivot 2026-06-14) — SERPER-INDEPENDENT BH candidates.

    The BH registry retailers (gcc.lulu, sharafdg, extra, ...) normally reach the
    price scraper ONLY through the Serper `site:` discovery query, which no-ops
    when the Serper account is dry. This builds each BH-tier NON-Shopify source's
    search URL DIRECTLY from the registry + RETAILER_SEARCH_URLS — zero Serper —
    so the Tier-1.5 fan_out can curl these directly-scrapeable BH pages even with
    Serper down. The caller PREPENDS these to the Serper-discovered candidates
    (purely additive).

    Shopify BH stores are EXCLUDED — they already have a dedicated
    Serper-independent /products.json direct-discovery path (and the search-URL
    template is wrong for them).

    Returns ``[(url, domain_label), ...]`` in registry (bahrain-first) order;
    empty list when a category's BH tier has no non-Shopify URL-resolvable source.
    """
    # Lazy import — avoids a top-level price_service -> source_router coupling.
    from app.services.source_router import get_sources_for_category

    candidates: List[Tuple[str, str]] = []
    seen: set = set()
    for s in get_sources_for_category(category):
        if s.tier != "bahrain":
            continue
        if getattr(s, "is_shopify", False):
            continue  # Shopify has its own /products.json path.
        url = build_retailer_url(s.domain, full_name)
        if not url or url in seen:
            continue
        seen.add(url)
        candidates.append((url, s.domain))
    return candidates


def sanitize_gpt_price(price: Optional[Dict]) -> None:
    """Fix GPT returning the string 'null' or echoing prompt templates."""
    if not price:
        return
    for key in ("retailer", "url"):
        val = price.get(key)
        if not isinstance(val, str):
            continue
        if val.lower() == "null" or "or null" in val.lower():
            price[key] = None


# S3-reopen T1 (team-lead Decision-F 2026-06-14) — ABSOLUTE plausibility gate.
# Wide-by-design category floor/ceiling multipliers: only catch GROSS
# mis-extractions (an iPhone at 5 or 9000 BHD), never a legitimately cheap or
# expensive REAL price. The GPT estimate is the judge of nothing — this is what
# replaces the old deviation-from-estimate veto at the two price sanity sites.
_PLAUSIBILITY_FLOOR_MULT = 0.1   # reject below 0.1 x the category budget breakpoint
_PLAUSIBILITY_CEIL_MULT = 3.0    # reject above 3 x the highest FINITE breakpoint


def is_price_plausible(amount_bhd: Optional[float], category: Optional[str]) -> bool:
    """Absolute-plausibility gate for a real (cited/converted) price, in BHD.

    Returns False only for gross category outliers — amount<=0, below
    0.1x the category budget breakpoint, or above 3x the highest finite
    breakpoint. A plausible price is TRUSTED even when it deviates wildly from
    the GPT training guess (the guess being wrong is exactly why we don't let it
    veto a cited price). Unknown / 'other' categories are permissive (only
    amount>0) since their magnitude is unbounded (cars to snacks).

    Anchors on scoring_service.PRICE_TIERS_BY_CATEGORY so the bounds track the
    same per-category BHD breakpoints the scorer already maintains.
    """
    if amount_bhd is None or amount_bhd <= 0:
        return False
    # Lazy import — keeps price_service's top-level import surface minimal and
    # avoids any scoring_service import-order coupling.
    from app.services.scoring_service import PRICE_TIERS_BY_CATEGORY

    ranges = PRICE_TIERS_BY_CATEGORY.get((category or "").lower())
    if not ranges:
        # 'other'/unknown — unbounded magnitude; only positivity is required.
        return True
    budget_breakpoint = ranges[0][0]
    finite_breakpoints = [u for u, _ in ranges if u != float("inf")]
    # Highest finite breakpoint anchors the ceiling (luxury is often inf when
    # top_tier is folded — fall back to premium so a real expensive item isn't
    # over-rejected but 9000-BHD garbage still is).
    top_finite = max(finite_breakpoints) if finite_breakpoints else budget_breakpoint
    floor = budget_breakpoint * _PLAUSIBILITY_FLOOR_MULT
    ceiling = top_finite * _PLAUSIBILITY_CEIL_MULT
    return floor <= amount_bhd <= ceiling


def get_official_domain(product_name: str) -> Optional[str]:
    """Return the official brand domain for a luxury product, or None."""
    name_lower = product_name.lower()
    for keyword in LUXURY_BRAND_KEYWORDS:
        if keyword in name_lower:
            for domain in OFFICIAL_BRAND_DOMAINS:
                domain_base = domain.split(".")[0].replace("-", "")
                keyword_clean = keyword.replace(" ", "").replace("-", "")
                if keyword_clean in domain_base or domain_base in keyword_clean:
                    return domain
    return None


# ============================================
# Shopping price extraction
# ============================================

def extract_price_from_shopping(
    product_name: str,
    shopping_items: List[Dict],
    currency: str,
    shopping_region: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract best matching price from Serper Shopping results.

    S3-reopen T2 (honest labels) — `shopping_region` is the gl region the items
    came from (`search_product_prices` returns it as `shopping_region`). When it
    is the gl=us fallback (``"us_fallback"`` / ``"us"``), OR a candidate's price
    string was in a non-target currency and got converted, that candidate is
    stamped ``converted_usd`` — NEVER ``local_bhd``. Only genuinely native-BHD
    prices get ``local_bhd``. Ahmed's directive: US-converted is an HONEST
    last-resort label, not a fake local price.
    """
    if not shopping_items:
        return None

    region_is_us_fallback = str(shopping_region or "").lower() in (
        "us_fallback", "us",
    )

    # L2 content safety — drop unsafe shopping items before pricing/ranking
    # logic runs. Inline import avoids circular-import risk at module load.
    # Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md sec 5.2.
    from app.services.content_safety_service import get_content_safety_service
    shopping_items = get_content_safety_service().filter_shopping_items(shopping_items)
    if not shopping_items:
        return None

    p_words = normalize_words(product_name)
    is_hv = is_high_value_query(product_name)
    is_lux = is_luxury_brand(product_name)
    min_price = 100.0 if is_hv else 0

    if is_lux:
        min_price = max(min_price, 50.0)

    candidates = []

    for item in shopping_items:
        price_str = item.get("price", "")
        if not price_str:
            continue

        amount = parse_price_string(price_str)
        if amount is None or amount <= 0:
            continue

        detected_cur = detect_currency(price_str)
        # T2 — a candidate is "converted" if its price string was a non-target
        # currency (so we converted it), OR the items came from the gl=us
        # fallback region (their prices are US even when the string is bare).
        item_converted = region_is_us_fallback or bool(
            detected_cur and detected_cur != currency
        )
        if detected_cur and detected_cur != currency:
            amount = _convert_to_bhd(amount, detected_cur)
            if currency != "BHD":
                bhd_rate = _convert_to_bhd(1.0, currency)
                if bhd_rate > 0:
                    amount = amount / bhd_rate

        title = item.get("title", "")

        if is_counterfeit_listing(title):
            continue
        if is_accessory(title):
            continue
        if is_hv and amount < min_price:
            continue
        if is_hv and not strict_title_match(product_name, title):
            continue
        if not numbers_match(product_name, title):
            continue

        t_words = normalize_words(title)
        match_score = len(p_words & t_words) / len(p_words) if p_words else 0
        if match_score < 0.4:
            continue

        retailer = item.get("source", "")
        retailer_score = get_retailer_score(retailer)

        link = item.get("link", "")
        if link:
            domain = extract_domain(link)
            if domain in OFFICIAL_BRAND_DOMAINS:
                retailer_score = 1.0

        candidates.append({
            "amount": round(amount, 2),
            "currency": currency,
            "retailer": retailer,
            "url": item.get("link") or build_retailer_url(retailer, product_name),
            "in_stock": True,
            # T2 — honest label: converted_usd for gl=us-fallback / converted
            # prices, local_bhd only for genuinely native-BHD listings.
            "source_method": "converted_usd" if item_converted else "local_bhd",
            "confidence": round(min(0.7 + match_score * 0.3, 1.0), 2),
            "match_score": match_score,
            "retailer_score": retailer_score,
            "title": title,
        })

    if not candidates:
        # Bundle C v1 hot-fix — diagnostic log when ZERO candidates survive
        # the filters despite shopping_items having results. Helps Ahmed/qa
        # see which filter is rejecting items (numbers_match, strict_title_match,
        # match_score < 0.4, counterfeit, accessory). Lightweight INFO log.
        logger.info(
            f"[PRICE_FILTER_TRACE] zero candidates from {len(shopping_items)} "
            f"shopping items for {product_name!r} — all rejected by "
            f"counterfeit/accessory/min_price/strict_title_match/numbers_match/"
            f"match_score filters. First 3 titles: "
            f"{[(item.get('title') or '')[:60] for item in shopping_items[:3]]}"
        )
        return None

    tier1_exists = any(c["retailer_score"] >= 1.0 for c in candidates)
    tier2_exists = any(c["retailer_score"] >= 0.7 for c in candidates)

    if tier1_exists or tier2_exists:
        candidates = [c for c in candidates if c["retailer_score"] >= 0.5]

    if not candidates:
        return None

    if is_lux:
        candidates.sort(key=lambda c: (-c["retailer_score"], -c["match_score"], c["amount"]))
    else:
        candidates.sort(key=lambda c: (-c["match_score"], -c["retailer_score"], c["amount"]))
    best = candidates[0]

    logger.info(
        f"[PRICE] Selected: {best['retailer']} (tier {best['retailer_score']}) "
        f"at {best['currency']} {best['amount']} for '{product_name}' "
        f"({len(candidates)} candidates)"
    )

    best.pop("match_score", None)
    best.pop("title", None)
    return best


# ============================================
# HTML / JSON-LD price extraction
# ============================================


def _is_product_type(item) -> bool:
    """JSON-LD @type may be a string or a list (e.g. ["Product","Vehicle"])."""
    t = item.get("@type") if isinstance(item, dict) else None
    if isinstance(t, list):
        return "Product" in t
    return t == "Product"


def extract_jsonld_price(
    html: str, brand: str, expected_currency: str, query_name: str = "",
) -> Optional[Dict[str, Any]]:
    """Parse JSON-LD Product schema from HTML for price data.

    `query_name` (S4 gate, optional) — the full query string. When a Product
    matches only via the JSON-LD `brand` field (not its name), this is used to
    require the matched product's NAME to actually relate to the query, so a
    multi-Product same-brand page can't attribute the cheapest UNRELATED same-
    brand item's price to the query. Empty `query_name` preserves the pre-S4
    behaviour (brand-field match alone). NOTE: kept distinct from the per-loop
    `product_name` (the candidate's own JSON-LD name) to avoid shadowing.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    ld_scripts = soup.find_all('script', type='application/ld+json')
    if not ld_scripts:
        return None

    brand_lower = brand.lower()
    best_price = None

    for script in ld_scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        products = []
        if isinstance(data, dict):
            if _is_product_type(data):
                products.append(data)
            elif "@graph" in data:
                for item in data["@graph"]:
                    if isinstance(item, dict) and _is_product_type(item):
                        products.append(item)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and _is_product_type(item):
                    products.append(item)

        for product in products:
            product_name = product.get("name", "")
            brand_nospace = brand_lower.replace(" ", "")
            name_nospace = product_name.lower().replace(" ", "")
            # L1.4 (Bundle B S3) — also match the JSON-LD `brand` field, not just
            # the product name. Many BH retailers (verified: bahrain.ounass.com)
            # carry the brand in a dedicated `brand` field ({"@type":"Brand",
            # "name":"Jessie and James"} or a bare string) while the name is just
            # "Orangey Dress" — pre-fix that valid BHD price was wrongly rejected.
            ld_brand = product.get("brand")
            if isinstance(ld_brand, dict):
                ld_brand = ld_brand.get("name", "")
            elif isinstance(ld_brand, list):
                ld_brand = " ".join(
                    (b.get("name", "") if isinstance(b, dict) else str(b))
                    for b in ld_brand
                )
            brand_field_nospace = str(ld_brand or "").lower().replace(" ", "")
            matched_in_name = brand_nospace in name_nospace
            matched_in_brand_field = bool(
                brand_field_nospace and brand_nospace in brand_field_nospace
            )
            if not matched_in_name and not matched_in_brand_field:
                continue

            # S4 — when the match is ONLY via the brand field (the product NAME
            # didn't contain the brand), require the matched product's name to
            # actually relate to the full query. Otherwise a multi-Product
            # same-brand page lets the cheapest UNRELATED same-brand item's price
            # be attributed to the query. Skipped when product_name is empty
            # (pre-S4 callers) or when the brand already matched in the name.
            if query_name and not matched_in_name:
                cand_name = product_name  # the candidate's own JSON-LD name
                # significant query numbers (e.g. "256") must appear in the name,
                if not numbers_match(query_name, cand_name):
                    continue
                # AND a real word overlap between the query and the candidate.
                q_words = normalize_words(query_name)
                n_words = normalize_words(cand_name)
                overlap = (len(q_words & n_words) / len(q_words)) if q_words else 0.0
                if overlap < 0.3:
                    continue

            offers = product.get("offers", {})
            if isinstance(offers, dict):
                offers = [offers]
            elif not isinstance(offers, list):
                continue

            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                currency = offer.get("priceCurrency", "")
                if currency.upper() != expected_currency.upper():
                    continue
                try:
                    # AggregateOffer carries lowPrice instead of price (I5.8)
                    price_val = float(offer.get("price") or offer.get("lowPrice") or 0)
                except (ValueError, TypeError):
                    continue
                if price_val <= 0:
                    continue

                availability = offer.get("availability", "")
                in_stock = "OutOfStock" not in availability

                if best_price is None or price_val < best_price["amount"]:
                    best_price = {
                        "amount": price_val,
                        "currency": expected_currency,
                        "in_stock": in_stock,
                    }

    return best_price


def extract_price_from_html(
    html: str, product_name: str, currency: str, domain: str, url: str
) -> Optional[Dict[str, Any]]:
    """Extract price from HTML using structured data (JSON-LD, OG, microdata)."""
    from bs4 import BeautifulSoup
    brand = product_name.split()[0] if product_name else ""

    # Priority 1: JSON-LD (S4 — pass the full query as query_name so a brand-
    # field-only match still requires name-relatedness, no cheapest-unrelated-
    # sibling grab).
    price_data = extract_jsonld_price(html, brand, currency, query_name=product_name)
    if not price_data:
        price_data = extract_jsonld_price(html, brand, "USD", query_name=product_name)
        if price_data:
            price_data["_needs_conversion"] = True

    if price_data and price_data.get("amount"):
        result = {
            "amount": price_data["amount"],
            "original_currency": price_data.get("currency", currency),
            "currency": price_data.get("currency", currency),
            "retailer": domain,
            "url": url,
            "in_stock": price_data.get("in_stock", True),
            "confidence": 1.0,
            "estimated": False,
            "source_method": "page_scrape",
        }
        if price_data.get("_needs_conversion") or result["currency"].upper() != currency.upper():
            _convert_gpt_price_currency(result, currency)
        return result

    # Priority 2: OpenGraph meta tags
    soup = BeautifulSoup(html, 'html.parser')
    og_price = soup.find('meta', property='og:price:amount')
    og_currency = soup.find('meta', property='og:price:currency')
    if not og_price:
        og_price = soup.find('meta', property='product:price:amount')
        og_currency = soup.find('meta', property='product:price:currency')

    if og_price and og_price.get('content'):
        try:
            amount = float(og_price['content'])
            if amount > 0:
                detected_currency = og_currency['content'] if og_currency and og_currency.get('content') else "USD"
                result = {
                    "amount": amount, "original_currency": detected_currency,
                    "currency": detected_currency, "retailer": domain, "url": url,
                    "in_stock": True, "confidence": 0.9, "estimated": False,
                    "source_method": "page_scrape",
                }
                if detected_currency.upper() != currency.upper():
                    _convert_gpt_price_currency(result, currency)
                return result
        except (ValueError, TypeError):
            pass

    # Priority 3: Schema.org MICRODATA (itemprop=price + itemprop=priceCurrency).
    # S3-genuine (gap-fill): bahrain.sharafdg.com PDPs are microdata-only (no
    # JSON-LD), so this is the path that produces a genuine BH electronics price.
    # CRITICAL — the page also carries an EPP INSTALLMENT itemprop=price
    # ("BHD 48.332/month"); the old find-first grabbed THAT (wrong). The helper
    # skips installment-context elements + reads the currency paired in the SAME
    # Offer itemscope (not a page-global find), and normalizes lowercase "bhd".
    micro = _extract_microdata_price(soup, currency, domain, url)
    if micro:
        return micro

    return None


# S3-genuine — installment markers an itemprop=price might sit next to (the EPP
# "BHD NN/month" widget). Used to skip a non-product-price microdata node.
_INSTALLMENT_RE = re.compile(
    r"/\s*month|per\s*month|/mo\b|monthly|installment|EPP|تقسيط", re.I
)


def _extract_microdata_price(
    soup, currency: str, domain: str, url: str
) -> Optional[Dict[str, Any]]:
    """Extract a product price from Schema.org microdata, skipping EPP
    installment nodes and pairing priceCurrency within the same Offer scope.

    Returns a ``page_scrape_microdata`` dict or ``None``. Prefers an
    ``itemprop=price`` inside an ``schema.org/Offer`` (or Product) itemscope;
    a bare/installment one is skipped.
    """
    candidates = soup.find_all(attrs={"itemprop": "price"})
    if not candidates:
        return None

    best = None  # (in_offer_scope: bool, amount, currency)
    for el in candidates:
        raw = el.get("content") or el.get_text(" ", strip=True)
        if not raw:
            continue
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)", str(raw).replace(",", ""))
        if not m:
            continue
        try:
            amount = float(m.group(1))
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue

        # Is this price inside an Offer/Product itemscope? Walk up; also grab the
        # currency paired within that SAME scope (not a page-global find).
        in_offer = False
        cur = None
        offer_scope = None
        s = el
        for _ in range(5):
            if s is None or not hasattr(s, "get"):
                break
            itemtype = s.get("itemtype") or ""
            if "Offer" in itemtype or "Product" in itemtype:
                in_offer = True
                offer_scope = s
                break
            s = s.parent
        if offer_scope is not None:
            cur_el = offer_scope.find(attrs={"itemprop": "priceCurrency"})
            if cur_el is not None:
                cur = cur_el.get("content") or cur_el.get_text(strip=True)

        # Installment skip — ONLY for a price NOT inside an Offer/Product scope
        # (a genuine Offer price is the product price even if an installment
        # widget shares an outer container). Check the node's own + immediate
        # parent text for a per-month / EPP marker.
        if not in_offer:
            ctx = el.get_text(" ", strip=True)
            if el.parent is not None:
                ctx += " " + el.parent.get_text(" ", strip=True)
            if _INSTALLMENT_RE.search(ctx):
                continue

        if not cur:
            cur_el = soup.find(attrs={"itemprop": "priceCurrency"})
            cur = (cur_el.get("content") or cur_el.get_text(strip=True)) if cur_el else "USD"
        cur = str(cur).strip().upper()  # lulu lowercase "bhd" -> "BHD"

        # Prefer an Offer-scoped price; among equals, the larger plausible value.
        key = (in_offer, amount)
        if best is None or key > (best[0], best[1]):
            best = (in_offer, amount, cur)

    if best is None:
        return None

    _in_offer, amount, cur = best
    result = {
        "amount": amount, "original_currency": cur, "currency": cur,
        "retailer": domain, "url": url, "in_stock": True,
        "confidence": 0.8, "estimated": False,
        # Use the existing "page_scrape" method (microdata is structured-data
        # from the page, same tier as JSON-LD/OG) so it's recognized as a real
        # price by scoring_service / quality_ranker / the L1.5 metric without a
        # cross-lane source_method-enum change.
        "source_method": "page_scrape",
    }
    if cur.upper() != currency.upper():
        _convert_gpt_price_currency(result, currency)
    return result


# ============================================
# Page fetching
# ============================================

async def curl_fetch_html(url: str) -> Optional[str]:
    """Fetch raw HTML via curl_cffi (no JS rendering)."""
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url, impersonate="chrome", timeout=PAGE_SCRAPE_TIMEOUT, allow_redirects=True,
            )
        )
        if resp.status_code != 200:
            domain = urlparse(url).netloc.replace("www.", "")
            logger.info(f"[PRICE] Page scrape: HTTP {resp.status_code} for {domain}")
            return None
        return resp.text
    except Exception as e:
        logger.warning(f"[PRICE] curl_cffi fetch failed for {url}: {e}")
        return None


async def fetch_page_price(
    url: str, product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Fetch a product page via curl_cffi and extract price from structured data."""
    if not ENABLE_PAGE_SCRAPE:
        return None

    domain = urlparse(url).netloc.replace("www.", "")
    html = await curl_fetch_html(url)
    if html:
        price = extract_price_from_html(html, product_name, currency, domain, url)
        if price:
            # L2 content safety — Tier 1.5 page-scrape entry point (Bundle B,
            # team-lead expansion of spec sec 5.2). Drop the candidate if the
            # title/retailer surface trips the blocklist, before it can become
            # a price source on the response.
            from app.services.content_safety_service import get_content_safety_service
            _surface = f"{price.get('title', '')} {price.get('retailer', '') or domain} {product_name}"
            if not get_content_safety_service().is_text_safe(_surface):
                logger.info("[content_safety] L2 dropped page-scrape candidate for %s", domain)
                return None
            return price
        return {"_got_html": True}

    return None


# ============================================
# Shopify direct-discovery (/products.json)
# ============================================
# L1.3 part 2 (Bundle B S3 'Sources'). Diagnostic
# (L1_DIAGNOSTIC_bh_scrapeability.md): the major BH retailers are JS-SPAs whose
# prices are NOT in static curl HTML — but Shopify-platform BH stores
# (shopalmoayyed.com, bh.asgharali.com) expose a static `/products.json`
# catalog with real BHD prices. Hitting it directly gives a real BH price with
# ZERO Serper + ZERO render credits — the cleanest real-price lever for the
# winner axis. Match the catalog client-side with the existing title helpers.

# Shopify caps /products.json at 250/page; one page is plenty for the small BH
# storefronts (≈30 products) and keeps the call cheap. Cache the catalog so a
# 2-product comparison on the same store is a single fetch.
SHOPIFY_PRODUCTS_PATH = "/products.json?limit=250"
_SHOPIFY_CATALOG_TTL = 6 * 3600  # 6h — catalogs are stable intraday
# M2 — negative cache: a failed/non-Shopify/slow fetch is remembered for a
# SHORT window so it isn't re-paid (~5s) on every escalating request (which ate
# the 12s fan_out budget at full-200). 30min is short enough to recover from a
# transient outage, long enough to stop the per-query re-cost storm.
_SHOPIFY_NEG_TTL = 30 * 60
_SHOPIFY_NEG_SENTINEL = {"_shopify_neg": True}


async def _fetch_shopify_catalog(domain: str) -> Optional[Dict[str, Any]]:
    """Fetch + JSON-parse `https://{domain}/products.json` via curl_cffi.

    Returns the parsed dict (``{"products": [...]}``) or ``None`` on any
    failure (non-Shopify store, non-200, non-JSON, network error). Cached in
    Redis for 6h on success; FAILURES are negative-cached for 30min (M2) so a
    dead/slow store isn't re-fetched every escalation. Graceful-None throughout
    (never raises)."""
    domain = (domain or "").replace("www.", "").strip().lower()
    if not domain:
        return None

    cache_key = f"shopify_catalog:{domain}"
    cached = get_cached(cache_key)
    if cached is not None:
        # M2 — a negative sentinel reads back as "known-failed" → None, no fetch.
        if isinstance(cached, dict) and cached.get("_shopify_neg"):
            return None
        return cached if isinstance(cached, dict) else None

    def _negcache():
        set_cached(cache_key, _SHOPIFY_NEG_SENTINEL, _SHOPIFY_NEG_TTL)

    url = f"https://{domain}{SHOPIFY_PRODUCTS_PATH}"
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url, impersonate="chrome", timeout=PAGE_SCRAPE_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as e:  # noqa: BLE001 — discovery is best-effort
        logger.info(f"[PRICE] Shopify catalog fetch failed for {domain}: {e}")
        _negcache()
        return None

    if resp.status_code != 200:
        logger.info(f"[PRICE] Shopify catalog HTTP {resp.status_code} for {domain}")
        _negcache()
        return None
    try:
        data = resp.json()
    except Exception:
        # Not a Shopify store (HTML, redirect to a storefront, etc.).
        _negcache()
        return None
    if not isinstance(data, dict) or "products" not in data:
        _negcache()
        return None

    # M1 — capture the store's REAL base currency (Shopify /meta.json) so the
    # matcher converts to BHD instead of blindly stamping it. A BH-targeted
    # `.myshopify.com` can be USD/AED-base (discovery found USD stores). Best-
    # effort: on any failure `_store_currency` stays absent → matcher skips the
    # hit (no blind BHD). Cached with the catalog (one fetch per domain/6h).
    data["_store_currency"] = await _fetch_shopify_currency(domain)

    set_cached(cache_key, data, _SHOPIFY_CATALOG_TTL)
    return data


async def _fetch_shopify_currency(domain: str) -> Optional[str]:
    """Shopify store base currency from ``/meta.json`` (ISO code, upper) or None.

    Graceful-None on any failure — the caller then skips the hit rather than
    stamping a fabricated currency (M1 Decision-F)."""
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                f"https://{domain}/meta.json", impersonate="chrome",
                timeout=PAGE_SCRAPE_TIMEOUT, allow_redirects=True,
            )
        )
        if resp.status_code != 200:
            return None
        cur = resp.json().get("currency")
        return str(cur).upper() if cur else None
    except Exception as e:  # noqa: BLE001 — best-effort
        logger.info(f"[PRICE] Shopify currency probe failed for {domain}: {e}")
        return None


def _match_shopify_product(
    catalog: Optional[Dict[str, Any]],
    product_name: str,
    currency: str,
    domain: str,
) -> Optional[Dict[str, Any]]:
    """Find the best title-matching product in a Shopify `/products.json`
    catalog and return its price dict, or ``None``.

    Matching reuses the price_service title helpers so it behaves exactly like
    the Serper-Shopping path: significant numbers must match
    (``numbers_match``), key words must all appear (``strict_title_match``),
    and the word-overlap ratio gates weak matches (>= 0.4).

    M1 (S3 gate) — CURRENCY VERIFICATION (no blind BHD stamp). The Shopify
    `/products.json` variant price is in the STORE'S base currency, which is NOT
    always BHD even on a `.bh`/BH-targeted store (the discovery sweep found
    USD-base `.myshopify.com` BH stores). `_fetch_shopify_catalog` records the
    store's real base currency from `/meta.json` in ``catalog["_store_currency"]``.
    Here: if it equals the target → keep; if it's a known other currency →
    `_convert_to_bhd`; if it is UNKNOWN/undeterminable → return None (skip the
    hit, let the cascade continue — Decision-F: never fabricate a currency, a
    wrong-price stamp is worse than an honest estimate).
    """
    if not isinstance(catalog, dict):
        return None
    products = catalog.get("products")
    if not isinstance(products, list) or not products:
        return None

    # M1 — resolve + validate the store's base currency up front.
    store_currency = str(catalog.get("_store_currency") or "").upper()
    target_currency = (currency or "BHD").upper()
    if not store_currency:
        # Currency undeterminable → do NOT stamp BHD. Skip (cascade continues).
        logger.info(
            "[PRICE] Shopify %s: store currency undeterminable — skipping hit "
            "(no blind BHD stamp)", domain,
        )
        return None
    needs_conversion = store_currency != target_currency
    if needs_conversion:
        from app.services.exchange_rate_service import FALLBACK_RATES
        if store_currency not in FALLBACK_RATES or target_currency != "BHD":
            # Can't safely convert (unknown rate, or non-BHD target) → skip.
            logger.info(
                "[PRICE] Shopify %s: store currency %s not safely convertible to "
                "%s — skipping hit", domain, store_currency, target_currency,
            )
            return None

    domain = (domain or "").replace("www.", "").strip().lower()
    p_words = normalize_words(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for product in products:
        if not isinstance(product, dict):
            continue
        title = product.get("title") or ""
        if not title:
            continue

        # Same gates as extract_price_from_shopping (counterfeit/accessory are
        # not expected on a curated BH storefront but stay defensive).
        if is_counterfeit_listing(title) or is_accessory(title):
            continue
        if not numbers_match(product_name, title):
            continue
        if not strict_title_match(product_name, title):
            continue

        t_words = normalize_words(title)
        match_score = len(p_words & t_words) / len(p_words) if p_words else 0.0
        if match_score < 0.4:
            continue

        variants = product.get("variants")
        if not isinstance(variants, list) or not variants:
            continue
        variant = variants[0] if isinstance(variants[0], dict) else {}
        amount = parse_price_string(str(variant.get("price", "")))
        if amount is None or amount <= 0:
            continue

        # M1 — convert from the store's base currency to the BHD target.
        if needs_conversion:
            amount = _convert_to_bhd(amount, store_currency)
            if amount is None or amount <= 0:
                continue

        if match_score > best_score:
            handle = product.get("handle") or ""
            url = (
                f"https://{domain}/products/{handle}" if handle and domain
                else f"https://{domain}/" if domain else ""
            )
            best = {
                "amount": round(amount, 2),
                "currency": target_currency,
                "original_currency": store_currency,
                "retailer": domain,
                "url": url,
                "in_stock": bool(variant.get("available", True)),
                "confidence": round(min(0.7 + match_score * 0.3, 1.0), 2),
                "estimated": False,
                "source_method": "shopify_json",
                "title": title,
                "match_score": round(match_score, 3),
            }
            best_score = match_score

    return best


async def fetch_shopify_price(
    domain: str, product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Direct-discovery price for a Shopify-platform BH retailer.

    Fetches the store's `/products.json`, matches `product_name`, and returns a
    ``source_method="shopify_json"`` price dict (real BHD, no Serper/render) or
    ``None``. L2 content-safety gated like the other Tier-1.5 entry points.
    """
    if not ENABLE_PAGE_SCRAPE:
        return None
    catalog = await _fetch_shopify_catalog(domain)
    if not catalog:
        return None
    price = _match_shopify_product(catalog, product_name, currency, domain)
    if not price:
        return None

    # L2 content safety — drop a candidate whose surface trips the blocklist.
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{price.get('title', '')} {price.get('retailer', '') or domain} {product_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped Shopify candidate for %s", domain)
        return None
    return price


# ============================================
# iHerb scraping
# ============================================

async def fetch_iherb_price(
    query: str, brand: str, full_name: str, region_code: str, currency: str,
) -> Optional[Dict[str, Any]]:
    """Fetch price directly from regional iHerb search page."""
    try:
        from curl_cffi import requests as curl_requests
        from bs4 import BeautifulSoup
        search_url = f"https://{region_code}.iherb.com/search?kw={query.replace(' ', '+')}&lang=en-US"
        logger.info(f"[PRICE] Direct iHerb fetch (curl_cffi): {search_url}")
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: curl_requests.get(search_url, impersonate="chrome", timeout=15, allow_redirects=True)
        )
        logger.info(f"[PRICE] iHerb response: status={resp.status_code}, length={len(resp.text)}")
        if resp.status_code != 200:
            return None
        page = resp.text
        soup = BeautifulSoup(page, 'html.parser')
        cards = soup.select('a[data-ga-brand-name][data-ga-discount-price][title]')
        products = []
        for card in cards:
            item_brand = card.get('data-ga-brand-name', '')
            price_str = card.get('data-ga-discount-price', '')
            title = card.get('title', '')
            href = card.get('href', '')
            if not price_str:
                continue
            rating_str = card.get('data-ga-rating', '')
            review_count_str = card.get('data-ga-review-count', '')
            rating = None
            review_count = None
            try:
                if rating_str:
                    rating = float(rating_str)
                    if rating <= 0 or rating > 5:
                        rating = None
            except (ValueError, TypeError):
                pass
            try:
                if review_count_str:
                    review_count = int(review_count_str)
            except (ValueError, TypeError):
                pass
            # L2 content safety — iHerb entry point (Bundle B, team-lead
            # expansion of spec sec 5.2). Per-card filter so unsafe items
            # never enter the brand-match / best-pick pipeline below.
            from app.services.content_safety_service import get_content_safety_service
            if not get_content_safety_service().is_text_safe(f"{item_brand} {title}"):
                continue
            products.append({
                "url": href if href.startswith("http") else f"https://{region_code}.iherb.com{href}",
                "brand": item_brand,
                "price": float(price_str),
                "title": title,
                "rating": rating,
                "review_count": review_count,
            })

        # F2.2 — schema.org microdata fallback. When iHerb drops/renames the
        # proprietary data-ga-* anchor attributes the selector above yields
        # zero cards; the standards-based `meta[itemprop="price"]` markers
        # (one per `div.product-inner` card) survive. Parsing them here keeps
        # the price local instead of falling through to the caller's
        # Firecrawl/Scrape.do fan-out (the 5-15s cost). Only runs on a GA-card
        # miss, so the GA path stays authoritative (no behaviour change when
        # cards are present).
        if not products:
            for card in soup.select("div.product-inner"):
                price_meta = card.select_one('meta[itemprop="price"]')
                if price_meta is None:
                    continue
                price_str = (price_meta.get("content") or "").strip()
                if not price_str:
                    continue
                try:
                    price_val = float(price_str)
                except (ValueError, TypeError):
                    continue
                anchor = card.select_one('a[href*="/pr/"]') or card.select_one("a[title]")
                href = anchor.get("href", "") if anchor else ""
                name_node = card.select_one('[itemprop="name"]')
                if name_node is not None:
                    title = (name_node.get("content") or name_node.get_text(strip=True) or "")
                elif anchor is not None:
                    title = anchor.get("title", "") or anchor.get_text(strip=True)
                else:
                    title = ""
                title = title.strip()
                if not title:
                    continue
                # iHerb titles are "Brand, rest...": derive brand from the head
                # so the existing brand-match logic below works identically to
                # the GA path (which carries data-ga-brand-name).
                item_brand = title.split(",", 1)[0].strip()
                rating = None
                review_count = None
                rating_node = card.select_one("[data-rating]")
                if rating_node is not None:
                    try:
                        rv = float(rating_node.get("data-rating", ""))
                        rating = rv if 0 < rv <= 5 else None
                    except (ValueError, TypeError):
                        pass
                    try:
                        review_count = int(rating_node.get("data-review-count", ""))
                    except (ValueError, TypeError):
                        pass
                from app.services.content_safety_service import get_content_safety_service
                if not get_content_safety_service().is_text_safe(f"{item_brand} {title}"):
                    continue
                products.append({
                    "url": href if href.startswith("http") else f"https://{region_code}.iherb.com{href}",
                    "brand": item_brand,
                    "price": price_val,
                    "title": title,
                    "rating": rating,
                    "review_count": review_count,
                })

        if not products:
            return None

        brand_lower = brand.lower()
        name_words = normalize_words(full_name)
        brand_matches = []
        for p in products:
            if p["brand"].lower() != brand_lower and brand_lower not in p["brand"].lower():
                continue
            brand_matches.append(p)
        if not brand_matches:
            brand_matches = [p for p in products if brand_lower in p["title"].lower()]

        best = None
        full_matches = []
        for p in brand_matches:
            title_words = normalize_words(p["title"])
            if name_words.issubset(title_words):
                full_matches.append(p)
        if full_matches:
            best = full_matches[0]
        else:
            best_score = -1
            for p in brand_matches:
                title_words = normalize_words(p["title"])
                overlap = len(name_words & title_words)
                if numbers_match(full_name, p["title"]):
                    overlap += 2
                if overlap > best_score or (overlap == best_score and best and p["price"] < best["price"]):
                    best_score = overlap
                    best = p

        if not best:
            return None

        return {
            "amount": best["price"],
            "original_currency": currency,
            "currency": currency,
            "retailer": "iHerb",
            "url": best["url"],
            "in_stock": True,
            "confidence": 1.0,
            "estimated": False,
            "_cached": False,
            "iherb_rating": best.get("rating"),
            "iherb_review_count": best.get("review_count"),
            "source_method": "converted_usd",
        }
    except Exception as e:
        logger.warning(f"[PRICE] iHerb direct fetch failed: {e}")
        return None


# ============================================
# Pharmacy JSON-LD scraping
# ============================================

async def fetch_pharmacy_price(
    serper_organic: List[Dict],
    brand: str,
    full_name: str,
    currency: str,
    track_serper_cost_fn=None,
) -> Optional[Dict[str, Any]]:
    """Fetch BHD price from Bahrain pharmacy product pages via JSON-LD."""
    pharmacy_urls = []
    for item in serper_organic:
        link = item.get("link", "")
        for domain, retailer_name in PHARMACY_DOMAINS.items():
            if domain in link:
                pharmacy_urls.append((link, retailer_name))
                break

    result = await _try_pharmacy_urls(pharmacy_urls, brand, currency)
    if result:
        return result

    site_query = " OR ".join(f"site:{d}" for d in PHARMACY_DOMAINS.keys())
    logger.info(f"[PRICE] No JSON-LD in initial pharmacy URLs, trying targeted pharmacy search for {full_name}")
    try:
        site_results = await search_web(f"{full_name} {site_query}", num_results=5, country="bh")
        if track_serper_cost_fn:
            track_serper_cost_fn()
        site_urls = []
        for item in site_results.get("organic", []):
            link = item.get("link", "")
            for domain, retailer_name in PHARMACY_DOMAINS.items():
                if domain in link:
                    site_urls.append((link, retailer_name))
                    break
        result = await _try_pharmacy_urls(site_urls, brand, currency)
        if result:
            return result
    except Exception as e:
        logger.warning(f"[PRICE] Site search failed: {e}")

    return None


async def _try_pharmacy_urls(
    pharmacy_urls: List[Tuple[str, str]],
    brand: str,
    currency: str,
) -> Optional[Dict[str, Any]]:
    """Try fetching JSON-LD price from a list of pharmacy URLs."""
    if not pharmacy_urls:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url, retailer_name in pharmacy_urls[:3]:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    continue

                price_data = extract_jsonld_price(resp.text, brand, currency)
                if price_data:
                    # L2 content safety — pharmacy JSON-LD entry point
                    # (Bundle B, team-lead expansion of spec sec 5.2).
                    from app.services.content_safety_service import get_content_safety_service
                    _surface = f"{price_data.get('title', '')} {brand} {retailer_name}"
                    if not get_content_safety_service().is_text_safe(_surface):
                        logger.info("[content_safety] L2 dropped pharmacy candidate for %s", retailer_name)
                        continue
                    return {
                        "amount": price_data["amount"],
                        "original_currency": currency,
                        "currency": currency,
                        "retailer": retailer_name,
                        "url": url,
                        "in_stock": price_data.get("in_stock", True),
                        "confidence": 1.0,
                        "estimated": False,
                        "source_method": "local_bhd",
                    }
            except Exception as e:
                logger.warning(f"[PRICE] Pharmacy {retailer_name} fetch failed: {e}")
                continue

    return None


# =============================================================================
# Bundle E Task 2.2 — scatter-gather price lookup
# Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 8.
# Tests: tests/test_scatter_gather_price.py
# =============================================================================

# Confirmation thresholds per design line 403.
HIGH_RANK_THRESHOLD = 85               # rank >= 85 alone confirms (firecrawl_brand_domain etc.)
AGREEMENT_PCT = 0.05                   # 2 sources within ±5% confirms


def _candidates_agree(a: dict, b: dict, tolerance: float = AGREEMENT_PCT) -> bool:
    """Two candidates agree if their price values are within ±tolerance fraction."""
    if not a or not b:
        return False
    va = a.get("value")
    vb = b.get("value")
    if va is None or vb is None:
        return False
    if va <= 0 or vb <= 0:
        return False
    diff = abs(va - vb) / max(va, vb)
    return diff <= tolerance


def _confirmed(candidates: List[dict]) -> bool:
    """True iff: (a) any candidate has rank >= HIGH_RANK_THRESHOLD, or
       (b) any pair of candidates agrees within AGREEMENT_PCT."""
    for c in candidates:
        if c.get("rank", 0) >= HIGH_RANK_THRESHOLD:
            return True
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            if _candidates_agree(candidates[i], candidates[j]):
                return True
    return False


def _select_best(candidates: List[dict]) -> Optional[dict]:
    """Highest-rank wins; ties broken by lowest value."""
    if not candidates:
        return None
    return max(candidates, key=lambda c: (c.get("rank", 0), -float(c.get("value", 0))))


async def fan_out_price_lookup(
    product: dict,
    *,
    scrapers: List[Any],
    scraping_mode: str = "hard",
) -> dict:
    """Run price scrapers concurrently; cancel pending tasks once a
    confirmed price lands (rank >= 85 OR 2 sources agree within 5%).

    Returns:
        {
            "best": dict | None,
            "alternates": list[dict],
            "cancelled_count": int,
            "elapsed_seconds": float,
        }
    """
    start = time.monotonic()

    if not scrapers:
        return {
            "best": None,
            "alternates": [],
            "cancelled_count": 0,
            "elapsed_seconds": time.monotonic() - start,
        }

    tasks = [asyncio.create_task(s(product)) for s in scrapers]
    completed: List[dict] = []
    cancelled_count = 0

    try:
        for fut in asyncio.as_completed(tasks):
            try:
                result = await fut
            except asyncio.CancelledError:
                # L5.3 (S3, gate Finding 1): distinguish an OUTER/parent cancel
                # (this whole coroutine is being cancelled — e.g. the lever-1
                # _price_task cleanup or the outer STREAM_HARD_CAP wait_for) from
                # an INDIVIDUAL inner-scraper cancel (the confirmation-cancel
                # block below cancels pending scrapers). For the OUTER case a bare
                # `continue` ABSORBS the cancel and keeps awaiting the remaining
                # un-cancelled scrapers → Firecrawl/Scrape.do run to completion in
                # the background (orphan-burn). `current_task().cancelling() > 0`
                # is set only when THIS task received a cancel request (proven:
                # inner-future cancel leaves it 0). On an outer cancel: cancel
                # every still-pending scraper, then re-raise so the cancel
                # propagates to the caller. The `finally` below drains them.
                current = asyncio.current_task()
                if current is not None and current.cancelling() > 0:
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    raise
                cancelled_count += 1
                continue
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[fan_out] scraper raised: {e}")
                continue

            if result and result.get("value") is not None:
                completed.append(result)

            if _confirmed(completed):
                # Cancel any task still pending.
                for t in tasks:
                    if not t.done():
                        t.cancel()
                # Drain the cancelled tasks so their handlers run + we
                # observe the CancelledError. Without this, the cancel
                # markers in tests never get appended.
                for t in tasks:
                    if t.cancelled() or t.done():
                        continue
                    try:
                        await t
                    except asyncio.CancelledError:
                        cancelled_count += 1
                    except Exception:  # noqa: BLE001
                        pass
                break
    finally:
        # Defensive: ensure no stray task survives the function.
        for t in tasks:
            if not t.done():
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass

    best = _select_best(completed)
    alternates = [c for c in completed if c is not best] if best else []

    return {
        "best": best,
        "alternates": alternates,
        "cancelled_count": cancelled_count,
        "elapsed_seconds": time.monotonic() - start,
    }
