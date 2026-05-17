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
    "extra": "https://www.extra.com/en-sa/search/?q={query}",
    "sharaf dg": "https://uae.sharafdg.com/search/?q={query}",
    "ubuy": "https://www.ubuy.com.bh/en/search?q={query}",
    "lulu": "https://www.luluhypermarket.com/en-bh/search?q={query}",
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
) -> Optional[Dict[str, Any]]:
    """Extract best matching price from Serper Shopping results."""
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
            "source_method": "local_bhd",
            "confidence": round(min(0.7 + match_score * 0.3, 1.0), 2),
            "match_score": match_score,
            "retailer_score": retailer_score,
            "title": title,
        })

    if not candidates:
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

def extract_jsonld_price(html: str, brand: str, expected_currency: str) -> Optional[Dict[str, Any]]:
    """Parse JSON-LD Product schema from HTML for price data."""
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
            if data.get("@type") == "Product":
                products.append(data)
            elif "@graph" in data:
                for item in data["@graph"]:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        products.append(item)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    products.append(item)

        for product in products:
            product_name = product.get("name", "")
            brand_nospace = brand_lower.replace(" ", "")
            name_nospace = product_name.lower().replace(" ", "")
            if brand_nospace not in name_nospace:
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
                    price_val = float(offer.get("price", 0))
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

    # Priority 1: JSON-LD
    price_data = extract_jsonld_price(html, brand, currency)
    if not price_data:
        price_data = extract_jsonld_price(html, brand, "USD")
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

    # Priority 3: Microdata itemprop="price"
    price_elem = soup.find(attrs={"itemprop": "price"})
    if price_elem:
        price_val = price_elem.get("content") or price_elem.get_text(strip=True)
        try:
            amount = float(price_val.replace(",", "").replace("$", "").replace("£", "").replace("€", ""))
            if amount > 0:
                currency_elem = soup.find(attrs={"itemprop": "priceCurrency"})
                detected_currency = currency_elem.get("content", "USD") if currency_elem else "USD"
                result = {
                    "amount": amount, "original_currency": detected_currency,
                    "currency": detected_currency, "retailer": domain, "url": url,
                    "in_stock": True, "confidence": 0.8, "estimated": False,
                    "source_method": "page_scrape",
                }
                if detected_currency.upper() != currency.upper():
                    _convert_gpt_price_currency(result, currency)
                return result
        except (ValueError, TypeError):
            pass

    return None


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
            return price
        return {"_got_html": True}

    return None


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
            products.append({
                "url": href if href.startswith("http") else f"https://{region_code}.iherb.com{href}",
                "brand": item_brand,
                "price": float(price_str),
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
