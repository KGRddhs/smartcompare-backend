"""Price Service — all price-related functions extracted from structured_comparison_service.

Functions are standalone (no self) — pass shopping_items_cache dict where needed.
"""
import os
import re
import json
import time
import asyncio
import hashlib
import functools
import logging
import unicodedata
from dataclasses import dataclass
# NOTE: imported as a NAME, not the module — extract_jsonld_price /
# _bolo_jsonld_main_price take a parameter literally called `html` that would
# shadow the module inside those bodies (Wave C C2 entity-decode).
from html import unescape as html_unescape
from typing import Optional, List, Dict, Any, FrozenSet, Tuple
from urllib.parse import urlparse, quote_plus, urljoin

import httpx

from app.services.extraction_service import (
    extract_price,
    extract_price_from_training_data,
    get_price_cache_key,
    generate_cache_key,
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

# Faithful-Results Phase 1 (Task 1.1 / 1.3) — TTL policy keyed on source_method.
#   - A GENUINE Bahrain shelf price (a `_GENUINE_BH_SOURCE_METHODS` method) is
#     stable for a week — cache it 7 days so the genuine-share survives without
#     re-burning a scrape on every TTL tick. THIS is the free-tier-survival lever
#     (scrape rarely, serve from cache long).
#   - A converted_usd / estimated / converted_fallback figure is short-lived
#     (rates drift, a genuine price may appear) — keep the 24h TTL so it refreshes
#     toward a genuine price sooner.
#   - A negative-cache sentinel for a structural dead-end (no genuine BH source
#     exists at all — luxury fragrance/haircare/gadgets) is cached 30 days so the
#     scrape cascade is not re-attempted on every request (Task 1.3).
# Env-overridable so an ops tune does not need a code change.
GENUINE_PRICE_CACHE_TTL = int(os.getenv("GENUINE_PRICE_CACHE_TTL_SECONDS", str(7 * 24 * 60 * 60)))  # 7 days
NEGATIVE_PRICE_CACHE_TTL = int(os.getenv("NEGATIVE_PRICE_CACHE_TTL_SECONDS", str(30 * 24 * 60 * 60)))  # 30 days


def price_cache_ttl(price: Optional[Dict[str, Any]]) -> int:
    """The cache TTL (seconds) for a resolved price, branched on source_method.

    Returns GENUINE_PRICE_CACHE_TTL (7d) when the price carries a genuine-BH
    source method (`_GENUINE_BH_SOURCE_METHODS`), else PRICE_CACHE_TTL (24h) for
    converted/estimated/unknown. Single point of policy so the ~12 price
    `set_cached` call sites in the cascade don't each duplicate the branch.

    Defensive: anything containing "converted" or "estimate" in the method is
    NEVER treated as genuine even if it also matches a genuine token, and a
    missing/blank method or a non-dict input falls back to the short TTL (a price
    we can't vouch for as genuine should refresh sooner, not linger a week).
    `_GENUINE_BH_SOURCE_METHODS` is defined further down the module, so it is
    resolved lazily at call time (same pattern as `_showable_source_methods`).
    """
    if not isinstance(price, dict):
        return PRICE_CACHE_TTL
    sm = (price.get("source_method") or "").lower()
    if not sm or "converted" in sm or "estimate" in sm:
        return PRICE_CACHE_TTL
    if sm in _GENUINE_BH_SOURCE_METHODS:
        return GENUINE_PRICE_CACHE_TTL
    return PRICE_CACHE_TTL


def negative_cache_key(price_cache_key: str) -> str:
    """The negative-cache (structural dead-end) sentinel key for a price key.

    `nogenuine:{price_cache_key}` — namespaced off the SAME size-aware price key
    so a structural gap is recorded per normalized product+size+region (Task 1.3).
    """
    return f"nogenuine:{price_cache_key}"


def should_negative_cache(price: Optional[Dict[str, Any]]) -> bool:
    """True iff a resolved price represents a structural genuine-BH dead-end that
    is worth negative-caching so the expensive scrape cascade is NOT re-run
    (Task 1.3).

    A dead-end is: no price at all, a price-pending shape, or a NON-genuine
    method (estimated / converted_fallback / unknown) — i.e. the full cascade ran
    and could not find a genuine Bahrain shelf price. A genuine price
    (`_GENUINE_BH_SOURCE_METHODS`) is NOT a dead-end.

    Exception: `converted_usd` is a LIVE Serper-cited price (USD→BHD), not a
    structural dead-end — the genuine scrape may succeed on a later request (a
    transient render failure) or the price-cache warmer may resolve it, so it
    must NOT be 30d-negative-cached (SF-1, code review 2026-06-18). Retrying the
    cascade costs some Firecrawl/Scrape.do budget but yields correct info.

    Exception: a `validation_rejected` price is a garbage-QUERY rejection, not a
    structural product gap — it must NOT be negative-cached (a real product typed
    later under the same key must re-resolve).
    """
    if not isinstance(price, dict):
        return True  # None / missing → dead-end
    sm = (price.get("source_method") or "").lower()
    if sm == "validation_rejected":
        return False
    # A genuine BH price is never a dead-end.
    if sm in _GENUINE_BH_SOURCE_METHODS and "converted" not in sm and "estimate" not in sm:
        return False
    # `converted_usd` is a live cited price, not a structural gap — see docstring.
    if sm == "converted_usd":
        return False
    # `sitemap_no_match` (Wave 2 source-intelligence) is a TRANSIENT discovery
    # miss — either the off-clock sitemap index hasn't been built yet (flag OFF /
    # first deploy) or the matcher found no PDP this run. It is NOT a structural
    # product dead-end: a later index refresh (cron_index_sitemaps) can resolve
    # the PDP and upgrade it to a genuine page_scrape_jsonld price, so it must NOT
    # be 30d-negative-cached (exempt-like converted_usd / SF-1).
    if sm == "sitemap_no_match":
        return False
    # Everything else (estimated, converted_fallback, pending, blank method) is a gap.
    return True

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
# S3 electronics-authority — a 3P marketplace reseller sits BELOW the 0.5
# first-party floor, so a first-party listing out-ranks it (and the >=0.5 tier
# filter drops the reseller when a first-party exists). A 3P-only result keeps
# this low score → it loses to any genuine BH price downstream.
_RESELLER_RETAILER_SCORE = 0.2

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
    # microless BH (Magento) — search path verified 200. NOTE the SEARCH page is
    # JS-rendered (0 static product links); the genuine BHD price is on the PDP
    # (439.062 BHD JSON-LD). So the registry row's real value is the Serper->PDP
    # ->curl path; this search URL is a fallback for any search-page-static case.
    "microless": "https://bahrain.microless.com/search/?q={query}",
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
    # S3 #34 — BH-English accessory terms (the Galaxy-S24-"screen guard" / case
    # confident-wrong-product class). "guard" matched whole-word via \b in
    # is_accessory, so it flags "screen guard" without catching e.g. "guardian".
    "screen guard", "guard",
}

# High-value electronics keywords (EL-2 split, G4)
# ------------------------------------------------
# The flagship floor (is_implausible_high_value_price) must protect a genuine
# phone/laptop/console/GPU from an accessory-priced wrong-scrape, WITHOUT
# flooring a genuine cheap accessory of the same brand. So the old flat set is
# split by self-identifying-ness:
#
#   HIGH_VALUE_DEVICE_TOKENS — name a device on their own (iphone, macbook,
#     rtx, playstation) → ALWAYS high-value.
#   HIGH_VALUE_BRANDS — bare brands (samsung, galaxy, xiaomi) → high-value ONLY
#     with a co-occurring device noun OR a confirmed flagship phone model
#     (_PHONE_MODEL_RE). "Samsung 25W charger" must NOT be high-value.
#   HIGH_VALUE_DEVICE_NOUNS — the device-class nouns that, with a bare brand,
#     confirm a device. EXCLUDES watch/buds/band/fit (accessory classes the
#     floor must NOT catch).
HIGH_VALUE_DEVICE_TOKENS = {
    "iphone", "pixel", "macbook", "ipad", "laptop",
    "playstation", "xbox", "nintendo",
    "rtx", "geforce", "radeon", "gpu",
}
HIGH_VALUE_BRANDS = {
    "samsung", "galaxy", "xiaomi", "huawei", "oneplus", "nvidia", "amd",
}
HIGH_VALUE_DEVICE_NOUNS = {
    "phone", "smartphone", "laptop", "notebook", "ultrabook", "tablet",
    "console", "tv", "television", "graphics card", "gpu", "monitor",
    # EXCLUDED on purpose: watch, buds, band, fit (accessory classes).
}
# BC alias — `HIGH_VALUE_KEYWORDS` is imported by structured_comparison_service
# (scs:718) and re-exported (scs:1551, used as self.HIGH_VALUE_KEYWORDS in
# tests). Keep it a derived union so no import breaks. NOTE: membership in this
# raw set is NOT the high-value predicate anymore — use is_high_value_query().
HIGH_VALUE_KEYWORDS = HIGH_VALUE_DEVICE_TOKENS | HIGH_VALUE_BRANDS

# Flagship phone-model regex (G4): confirms a high-value device from a bare brand
# even when no device noun is present ("Samsung Galaxy S24" has no noun). Matches
# the common flagship/numeral PHONE lines across Samsung Galaxy (S/Note/A/M/Z),
# OnePlus, Huawei (P/Mate/Nova), Pixel and Xiaomi. MUST NOT match accessory model
# contexts (Mi Band 8 / Galaxy Watch 6 / Buds / Fit): those carry no flagship line
# token after the brand, and accessory-WORDED queries ("OnePlus 12 case") are
# dropped earlier by the is_accessory() guard in is_high_value_query.
# WS-1 fix (dispatcher gate): the prior regex only covered Galaxy S/Note/Z +
# Xiaomi, so brand-present non-S/Note flagships ("OnePlus 12", "Galaxy A54",
# "Huawei P60") lost flagship-floor protection (True->False vs the old flat set) —
# a silent no-wrong-scrapes regression. Broadened below.
_PHONE_MODEL_RE = re.compile(
    r"(?<![a-z0-9])(?:"
    r"galaxy\s+(?:s|note|a|m|z\s*(?:fold|flip))\s*\d"  # Galaxy S24/Note20/A54/M14/Z Fold5
    r"|(?:s|note)\s*\d{2}\s*(?:ultra|plus|\+|fe)?"      # bare "S24 Ultra" / "Note 20"
    r"|oneplus\s+(?:nord\s+)?\d{1,2}"                   # OnePlus 12 / OnePlus Nord 3
    r"|huawei\s+(?:p|mate|nova)\s*\d{1,2}"              # Huawei P60 / Mate 60 / Nova 12
    r"|pixel\s+\d"                                       # Google Pixel 9
    r"|xiaomi\s+\d{1,2}"                                 # Xiaomi 14 / Xiaomi 11
    r")",
    re.IGNORECASE,
)

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

# Designer / niche fragrance brands — used by is_fragrance_query to recognise a
# perfume even when the query omits the "perfume"/"edp" product word (e.g. "Tom
# Ford Ombré Leather", "Creed Aventus"). Distinct from LUXURY_BRAND_KEYWORDS
# (which spans handbags + watches): a fragrance from any of these is reliably an
# expensive FULL bottle, so an implausibly-low scrape is a sample/decant.
FRAGRANCE_BRAND_KEYWORDS = {
    "tom ford", "creed", "amouage", "mfk", "maison francis kurkdjian",
    "initio", "frederic malle", "frédéric malle", "byredo", "le labo",
    "montale", "mancera", "xerjoff", "parfums de marly", "kilian",
    "chanel", "dior", "guerlain", "ysl", "yves saint laurent", "armani",
    "versace", "valentino", "givenchy", "jean paul gaultier", "gucci",
    "lancome", "lancôme", "viktor rolf", "viktor & rolf", "carolina herrera",
    "paco rabanne", "hermes", "hermès", "burberry", "prada", "bvlgari",
    "ajmal", "asghar ali", "asgharali", "al haramain", "lattafa", "rasasi",
}

# Generic fragrance product words (concentration tokens covered separately by
# extract_concentration). Presence of any → almost certainly a perfume query.
FRAGRANCE_PRODUCT_KEYWORDS = {
    "perfume", "perfumes", "cologne", "fragrance", "fragrances",
    "eau de parfum", "eau de toilette", "eau de cologne", "edp", "edt", "edc",
    "parfum", "extrait", "body spray", "body mist", "attar", "oud",
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

# Supplement keywords (G2 split — whole-token + corroboration)
# ------------------------------------------------------------
# Old behavior was naive substring matching: "iron" matched "environment",
# "Tefal steam iron", "cast iron skillet"; "protein" matched "protein bar";
# "collagen" matched "collagen serum" (skincare). The detector now matches on
# WHOLE TOKENS (lookaround boundary) and splits tokens into:
#
#   SUPPLEMENT_UNAMBIGUOUS — tokens/brands that are supplement-only on their own
#     (vitamin, softgel, probiotic, biotin, ... + the supp/sports BRANDS).
#   SUPPLEMENT_AMBIGUOUS — tokens that ALSO name non-supplement products (iron,
#     collagen, protein, zinc, calcium, omega, d3, magnesium, ...). These count
#     ONLY with a co-occurring dose (SUPPLEMENT_DOSE_RE) OR form token OR a
#     supp-brand.
SUPPLEMENT_UNAMBIGUOUS = {
    # Supplement-only product words / nutrients.
    "vitamin", "supplement", "supplements", "softgel", "softgels",
    "probiotic", "probiotics", "fish oil", "biotin", "melatonin",
    "turmeric", "creatine", "multivitamin", "folic", "coq10", "glucosamine",
    # WS-1 dispatcher gate-fix — unambiguous supplement product words that the
    # whole-token rewrite would otherwise drop (Thorne Magnesium class: a true
    # supplement from a brand not in the set + an ambiguous nutrient + no
    # dose/form was returning False). These are supplement-only forms/herbs/
    # sports-nutrition words (NOT a blanket "powder" — that would catch "iron
    # oxide powder" / "zinc oxide" pigments; closed via specific tokens instead).
    "ashwagandha", "theanine", "bcaa", "glutamine", "spirulina",
    "whey", "whey protein", "protein powder", "collagen peptides",
    "pre-workout", "pre workout",
    # Supplement / sports-nutrition BRANDS — closing-token corroboration so a
    # brand-led ambiguous query ("Optimum Nutrition Whey Protein",
    # "Nordic Naturals Omega-3", "Thorne Magnesium") resolves True even with no
    # dose/form. (test_error_paths:104 pins "Nordic Naturals Omega-3" -> True.)
    # Curated supplement-ONLY brands (no ambiguous houses like Himalaya/Swisse
    # that also sell skincare — those would misroute a face wash).
    "nature made", "now foods", "solgar", "garden of life", "kirkland",
    "nordic naturals", "centrum", "optimum nutrition", "dymatize",
    "myprotein", "muscletech", "thorne", "doctor's best", "sports research",
    "california gold nutrition", "healthaid", "vitabiotics", "natrol",
    "jarrow", "jarrow formulas", "nature's bounty", "applied nutrition",
    "emergen-c", "one a day", "nature's way", "life extension",
    "blackmores", "puritan's pride",
}
SUPPLEMENT_AMBIGUOUS = {
    "iron", "collagen", "protein", "zinc", "calcium", "omega", "omega-3",
    "magnesium", "mineral", "d3", "d-3", "b12", "b-12", "potassium", "whey",
}
# Dose pattern — a numeric quantity in supplement units. Reuses the canonical
# (\d+(?:[.,]\d+)?)\s*(IU|mg|mcg|g) reference; whole-unit boundary via lookahead.
SUPPLEMENT_DOSE_RE = re.compile(
    r"(?<![a-z0-9])\d+(?:[.,]\d+)?\s*(?:iu|mg|mcg|g)(?![a-z])",
    re.IGNORECASE,
)
# Dosage-form tokens — a supplement is sold in these forms.
SUPPLEMENT_FORM_TOKENS = {
    "softgel", "softgels", "capsule", "capsules", "tablet", "tablets",
    "gummy", "gummies", "caplet", "caplets", "count", "ct",
}

# BC alias — kept a derived union so structured_comparison_service's
# `from .price_service import SUPPLEMENT_KEYWORDS` (scs:724) + the re-export at
# scs:1557 do not break. Membership is NOT the predicate — use
# is_supplement_query().
SUPPLEMENT_KEYWORDS = SUPPLEMENT_UNAMBIGUOUS | SUPPLEMENT_AMBIGUOUS | SUPPLEMENT_FORM_TOKENS

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
# S3-genuine (team-lead live probe 2026-06-14, WRINKLE 1): gcc.luluhypermarket.com
# is ~3.4s warm but the 5s cap clipped it COLD (curl(28) timeout) — the keystone
# broad BH source then intermittently returned nothing. Bahrain-tier registry
# curls get a longer cold-tolerant timeout; non-BH scrapes stay at 5s so the
# whole cascade isn't slowed.
BH_REGISTRY_CURL_TIMEOUT = 10
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


# Pharmacy-class categories where the category-ambiguous ACCESSORY keyword
# "skin" is ordinary descriptive vocabulary ("...For Normal To Oily SKIN",
# "All SKIN Types") rather than a phone-decal signal (Wave B-FIX BF4, coverage
# sweep OR-7). The nasser pharmacy matcher (see the NOTE at its accessory
# pre-filter omission, ~:7813) already documents + exempts this exact
# false-positive; the six direct store-API chains (occ/woo/salla/algolia x2/
# unbxd) keep the filter but SCOPE it via is_accessory_for_category.
_PHARMACY_TITLE_CATEGORIES = frozenset({"skincare", "haircare", "supplements", "makeup"})
_PHARMACY_BENIGN_ACCESSORY_KEYWORDS = frozenset({"skin"})

# GCC laptop listings state the KEYBOARD LAYOUT mid-title (Wave C C2, kpiE2E
# re-sweep RS-1/RS-4: "English & Arabic Keyboard" on EVERY live sharafdg
# MacBook row; "Arabic Keyboard" is standard GCC retailer phrasing) — a bare
# "keyboard" keyword hit alone must NOT classify a LAPTOP-class listing as an
# accessory. Scoped like the pharmacy 'skin' exemption above, but by SURFACE
# context (a laptop-class device noun on the SAME title) rather than category:
# a real keyboard product ("Logitech MX Keys Keyboard" — head noun, no device
# context) still rejects, and any OTHER accessory keyword ("Keyboard Case for
# MacBook") still flags. The broad `is_accessory` keeps the unscoped hit — the
# noisy Serper-shopping/zyte/rating nets AND the QUERY-side flagship-floor
# exclusion (is_high_value_query: a laptop-keyboard accessory QUERY must stay
# excluded so its genuine cheap price is never floored away) are unchanged.
_LAPTOP_NOUN_RE = re.compile(
    r"\b(?:macbook|macbooks|laptop|laptops|notebook|notebooks|chromebook|"
    r"chromebooks|ultrabook|ultrabooks)\b"
)
_LAPTOP_CONTEXT_BENIGN_ACCESSORY_KEYWORDS = frozenset({"keyboard"})

# Wave D (convergence CV2) — BOUND the laptop-surface keyboard exemption: a
# FULL-SPEC keyboard PART listing ("Arabic Keyboard for Apple MacBook Air 13
# M5 512GB" @ 59.9 BHD) carried the laptop noun, rode the bare-keyword
# exemption past the accessory gate, and — carrying the laptop's complete
# spec set — cleared every identity axis above the 50-BHD flagship floor.
# The exemption is a LAYOUT-attribute reading, so it applies ONLY when the
# phrasing is a layout attribute OF the laptop:
#   - part/compat phrasing ("Keyboard for ..." / "Keyboard compatible ...")
#     ALWAYS keeps the accessory flag, wherever it sits in the title;
#   - the laptop device noun must appear BEFORE the (first) keyboard token —
#     GCC retailer laptop rows head with the device and state the layout
#     mid/late-title (the live sharafdg/extra/IdeaPad shapes, all pinned),
#     while a part listing heads with the part.
# Rejected alternatives: requiring a storage/RAM spec token FAILS (the CV2
# part title carries 512GB — that is exactly what made it leak); exempting
# only inside _KEYBOARD_LAYOUT_RE FAILS too ("Arabic Keyboard" IS a layout
# phrase and the leak title heads with it). Fail direction of any residual is
# over-flagging -> the broad is_accessory -> fail-closed (over-rejection,
# never a wrong price).
_KEYBOARD_TOKEN_RE = re.compile(r"\bkeyboards?\b")
_KEYBOARD_PART_PHRASE_RE = re.compile(r"\bkeyboards?\s+(?:for|compatible)\b")


def _laptop_layout_keyboard_exempt(title_lower: str) -> bool:
    """True iff the lowered surface reads as a LAPTOP listing whose keyboard
    mention is a layout attribute (CV2 bound): a laptop-class device noun is
    present, it PRECEDES the first keyboard token, and no part/compat
    "keyboard for/compatible" phrasing appears."""
    m_laptop = _LAPTOP_NOUN_RE.search(title_lower)
    if not m_laptop:
        return False
    if _KEYBOARD_PART_PHRASE_RE.search(title_lower):
        return False
    m_kb = _KEYBOARD_TOKEN_RE.search(title_lower)
    if m_kb and m_kb.start() < m_laptop.start():
        return False
    return True


def is_accessory_for_category(title: str, category: Optional[str] = None) -> bool:
    """Scoped `is_accessory` for the direct store-API matcher chains (BF4,
    sweep OR-7 + Wave C C2, RS-4). Two bounded exemptions, one keyword each:

    - PHARMACY category scope: when the ORCHESTRATOR-RESOLVED category is a
      pharmacy class (skincare/haircare/supplements/makeup), a bare "skin"
      keyword hit alone must NOT classify a genuine pharmacy title ("CeraVe
      ... For Dry Skin", "Nivea ... All Skin Types") as an accessory —
      fail-closed on the QUERY's resolved category, never the title, so a
      real phone-skin decal under an electronics query still rejects.
    - LAPTOP surface scope (C2, bounded by Wave D CV2): a bare "keyboard" hit
      is a LAYOUT attribute, not an accessory, when the SAME surface carries
      a laptop-class device noun ("MacBook ... English & Arabic Keyboard") —
      any non-pharmacy category, keyed off the title context itself. CV2
      bound: the device noun must PRECEDE the keyboard token and part/compat
      phrasing ("Keyboard for/compatible ...") never exempts — a full-spec
      keyboard PART listing must keep its accessory flag (see
      _laptop_layout_keyboard_exempt).

    In both scopes any OTHER accessory keyword still flags. Everything else
    keeps the full broad is_accessory. The Serper-shopping extractors
    deliberately keep the unscoped is_accessory (noisy listings need the
    broad net; direct store-API names are resolved products)."""
    title_lower = (title or "").lower()
    if (category or "").lower() in _PHARMACY_TITLE_CATEGORIES:
        benign = _PHARMACY_BENIGN_ACCESSORY_KEYWORDS
    elif _laptop_layout_keyboard_exempt(title_lower):
        benign = _LAPTOP_CONTEXT_BENIGN_ACCESSORY_KEYWORDS
    else:
        return is_accessory(title)
    for kw in ACCESSORY_KEYWORDS:
        if kw in benign:
            continue
        if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
            return True
    return False


# Unambiguous electronics ACCESSORY add-ons (a phone CASE, a CHARGER) — used by the
# shared select_best + is_price_showable gates to reject a cheap accessory matched as
# the device. DELIBERATELY EXCLUDES class-nouns that are PRODUCTS in their own right
# (keyboard / mouse / headphone / earbuds / stylus / pen) and category-ambiguous words
# (skin / glass / film) that appear in genuine skincare/makeup titles — `is_accessory`
# (used by the per-adapter extractors) keeps the broad list; this narrow set is for the
# correctness gates so a genuine standalone keyboard / Sony WH-1000XM5 / CeraVe is NOT
# false-pended. Electronics-scoped at the call site.
_DEVICE_ACCESSORY_TOKENS = frozenset({
    "case", "cover", "charger", "charging", "cable", "adapter", "protector",
    "dock", "cradle", "sleeve", "pouch", "casing", "bumper",
})


def _is_device_accessory(text: str) -> bool:
    """True iff `text` names an electronics ACCESSORY (case/cover/charger/...). Plain
    ASCII tokenize (the keywords are all ASCII) so it can be defined before _fold_identity."""
    toks = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    return bool(toks & _DEVICE_ACCESSORY_TOKENS)


def _contains_token(name_lower: str, token: str) -> bool:
    """Whole-token (lookaround word-boundary) containment. Unlike `\\b`, the
    lookaround treats digits as part of the token so `d3`/`d-3`/`omega-3` match
    cleanly and `iron` does NOT match inside `environment`. Multi-word tokens
    ("now foods", "graphics card") are matched as a phrase."""
    pattern = r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])"
    return re.search(pattern, name_lower) is not None


def is_high_value_query(product_name: str) -> bool:
    """True iff `product_name` names a high-value product (phone/laptop/console/
    GPU). EL-2 split (G4):

    - A self-identifying DEVICE TOKEN (iphone, macbook, rtx, playstation, ...)
      is high-value on its own.
    - A bare BRAND (samsung, galaxy, xiaomi, ...) is high-value ONLY with a
      co-occurring device noun OR a confirmed flagship phone model
      (_PHONE_MODEL_RE) — so "Samsung 25W charger" / "Galaxy Watch" are NOT
      high-value and their genuine cheap prices are not floored away.
    - An ACCESSORY of a high-value device ("iPhone 15 case", "OnePlus 12 cover",
      "Samsung 25W charger") is itself a genuine cheap product whose low price
      must NOT be floored — excluded FIRST so neither the device-token nor the
      bare-brand+model path floors it (this is what lets _PHONE_MODEL_RE be
      broadened to OnePlus/Huawei/Galaxy-A without re-flooring their accessories).
    """
    if is_accessory(product_name):
        return False
    name_lower = product_name.lower()
    if any(_contains_token(name_lower, tok) for tok in HIGH_VALUE_DEVICE_TOKENS):
        return True
    if any(_contains_token(name_lower, brand) for brand in HIGH_VALUE_BRANDS):
        has_device_noun = any(
            _contains_token(name_lower, noun) for noun in HIGH_VALUE_DEVICE_NOUNS
        )
        if has_device_noun or _PHONE_MODEL_RE.search(name_lower):
            return True
    return False


# Wrong-scrape guard (Ahmed's hard line: "no wrong scrapes"). A genuine BH scrape
# can land on an ACCESSORY listing — a "Galaxy S24" case at 11.9 BHD — whose title
# dodges the is_accessory keyword filter; the cascade then caches it as a genuine
# BH price. is_price_plausible only floors at ~0.1x the category budget-breakpoint
# (~10 BHD for electronics), so an 11.9 accessory slips through. For a HIGH-VALUE
# product (phone/laptop/console/GPU) any price below this floor is almost always a
# wrong-product hit (real units are >= ~100 BHD). Reject it on the genuine paths so
# the cascade falls through to an HONEST converted/estimated figure instead of a
# wrong "genuine" one. NON-high-value categories are untouched (is_high_value_query
# is False for fragrances ~18 BHD, supplements ~5 BHD, makeup, grocery).
HIGH_VALUE_PRICE_FLOOR_BHD = 50.0


def is_implausible_high_value_price(product_name: str, amount: Optional[float]) -> bool:
    """True iff `product_name` is a high-value product but `amount` (BHD) is
    implausibly low — a likely accessory / wrong-product scrape that must NOT be
    served as a genuine price. False for non-high-value products and for
    missing/zero amounts (nothing to reject)."""
    if amount is None or amount <= 0:
        return False
    return is_high_value_query(product_name) and amount < HIGH_VALUE_PRICE_FLOOR_BHD


def is_luxury_brand(product_name: str) -> bool:
    """Check if the product is from a luxury/designer brand."""
    name_lower = product_name.lower()
    return any(brand in name_lower for brand in LUXURY_BRAND_KEYWORDS)


def is_supplement_query(product_name: str) -> bool:
    """True iff `product_name` is (almost certainly) a supplement/vitamin (G2).

    Whole-token matching (lookaround boundary, NOT `\\b`) so `d3`/`d-3`/`omega-3`
    match while `iron` does NOT match inside `environment`:

    - An UNAMBIGUOUS token or a supp/sports BRAND stands alone → True.
    - An AMBIGUOUS token (iron/collagen/protein/zinc/calcium/omega/d3/...) counts
      ONLY with a co-occurring dose (SUPPLEMENT_DOSE_RE) OR form token OR a
      supp-brand — so "Tefal steam iron", "collagen serum", "protein bar",
      "cast iron skillet", "calcium antacid" are NOT supplements.

    The high-value short-circuit is repointed to is_high_value_query() (the
    function, NOT the raw narrowed set) so the floor and this guard never
    disagree on what's high-value (Q1 silent-inconsistency gate). It is
    technically redundant under whole-token matching (a real device name has no
    supplement token), but kept defensively + repointed to satisfy the gate.
    """
    if not product_name:
        return False
    if is_high_value_query(product_name):
        return False
    name_lower = product_name.lower()

    # Unambiguous tokens / supp-brands stand alone.
    if any(_contains_token(name_lower, tok) for tok in SUPPLEMENT_UNAMBIGUOUS):
        return True

    # Ambiguous tokens need corroboration: dose OR form OR a supp-brand.
    has_ambiguous = any(
        _contains_token(name_lower, tok) for tok in SUPPLEMENT_AMBIGUOUS
    )
    if not has_ambiguous:
        return False
    has_dose = SUPPLEMENT_DOSE_RE.search(name_lower) is not None
    has_form = any(
        _contains_token(name_lower, tok) for tok in SUPPLEMENT_FORM_TOKENS
    )
    # (supp-brand corroboration already returns True above via UNAMBIGUOUS.)
    return has_dose or has_form


# ============================================
# Fragrance size-plausibility guard (#17 B1)
# ============================================
#
# The shipped accuracy guards (is_implausible_high_value_price) only floor
# HIGH-VALUE electronics. A prod-smoke PARTIAL surfaced an implausibly-LOW
# fragrance converted price — Tom Ford Ombré Leather 19.93 BHD (~$53), a
# sample/decant-grade listing whose genuine full bottle is ~80 BHD. There was no
# fragrance analog, so the cascade cached/served the sample price as if genuine.
#
# Fragrances legitimately vary by SIZE: a genuine 30ml decant is cheap by
# design, so a blanket BHD floor would wrongly reject it. The guard therefore
# floors on a price that is implausibly low FOR THE DETECTED/EXPECTED size,
# reusing the WS5 extract_sizes_ml annotations: a size-proportional floor scaled
# off the flagship 100ml full-bottle floor. Size-unspecified luxury fragrance
# defaults to the flagship 100ml basis (consistent with flagship_basis_bonus).
# Gated to DESIGNER/NICHE fragrance brands — where a full bottle is reliably
# expensive — so a genuinely-cheap mass-market body spray is never floored.

# Designer-fragrance full-bottle (100ml-basis) floor. A 100ml-basis listing
# under this in BHD is a sample/decant/wrong-SKU mis-extraction, not the genuine
# bottle. Tuned so the Ombré Leather 19.93 sample is caught while leaving wide
# margin under the cheapest plausible full designer bottle (~30+ BHD = the
# fragrances budget breakpoint). Scaled by size for smaller bottles.
FRAGRANCE_FULL_SIZE_FLOOR_BHD = 25.0
_FRAGRANCE_FLAGSHIP_SIZE_ML = 100.0

# F1.2a — PREMIUM/niche houses genuinely cost 80-150+/100ml, so the flat 25/100ml
# floor was too low and let a decant/body-spray leak through (Tom Ford Tobacco
# Vanille showed 28.2 BHD; genuine ~118). These houses get a higher 50/100ml
# floor; the broader designer set (Versace/Gucci/...) keeps the 25 floor so the
# cheaper-designer tier is not over-rejected.
PREMIUM_FRAGRANCE_BRAND_KEYWORDS = {
    "tom ford", "creed", "amouage", "mfk", "maison francis kurkdjian",
    "initio", "frederic malle", "frédéric malle", "byredo", "le labo",
    "montale", "mancera", "xerjoff", "parfums de marly", "kilian",
    "roja", "clive christian", "nishane", "bdk", "ormonde jayne",
}
PREMIUM_FRAGRANCE_FULL_SIZE_FLOOR_BHD = 50.0
# A floor never drops below this absolute BHD value (a sub-5-BHD "fragrance" at
# any labelled size is a scrape artifact, not a real perfume).
_FRAGRANCE_MIN_FLOOR_BHD = 5.0

# Budget Arabic/Gulf fragrance houses (Lattafa, Rasasi, Al Haramain, Ajmal,
# Armaf, Swiss Arabian, ...). Their genuine full 100ml EDP retails for ~8-25 BHD
# in Bahrain (alhajisbahrain/alibaksh/fragrancebh list Lattafa Khamrah 11-12,
# Asad 8-9, Armaf Club de Nuit 14-15, Rasasi Hawas 14-17, Al Haramain Amber Oud
# 22 — all in BHD). The 25/100ml DESIGNER floor (is_implausible_low_fragrance_
# price) is calibrated for Western designer houses and WRONGLY pends these houses'
# genuine cheap price — but ONLY on the display chokepoint for a TRUSTWORTHY
# direct-adapter exact-PDP price (see _budget_house_trusted_price). The floor
# STILL applies on the loose Serper-shopping path (where a wrong-cheap mislabel is
# common), so this never lowers protection there. Tokens are unambiguous multi-
# char house names (no generic/collision-prone token — e.g. NOT "my perfumes",
# which substring-pollutes a "Chanel my perfumes" query).
# ONLY the houses that are ALSO in FRAGRANCE_BRAND_KEYWORDS (so
# is_implausible_low_fragrance_price actually floors them and the bypass is
# load-bearing). Other budget houses (Armaf, Swiss Arabian, Maison Alhambra,
# Afnan, ...) are NOT in the designer set -> never floored -> their genuine cheap
# price already shows without this bypass, so listing them here would be dead
# config that weakens no guard but misleads. Keep this set == the Arabic houses in
# FRAGRANCE_BRAND_KEYWORDS.
BUDGET_FRAGRANCE_BRAND_KEYWORDS = {
    "lattafa", "rasasi", "al haramain", "ajmal", "asghar ali", "asgharali",
}
# The SAME budget houses ALSO sell genuinely-expensive concentrated lines (pure
# dehn-al-oud / mukhallat / perfume-oil / attar, 40-150+ BHD). A wrong-cheap price
# for one of THOSE must stay floored even from a direct adapter, so a title/name
# carrying one of these line tokens is EXCLUDED from the budget-house trust (it
# keeps the designer floor). Deliberately specific to the concentrated-OIL lines —
# NOT bare "oud" (an "Amber Oud" EDP is a cheap mainstream spray, still trusted).
_BUDGET_HOUSE_PREMIUM_LINE_TOKENS = {
    # canonical + the common alternate transliterations these houses actually list
    # (dahn/dehn/dhan; mukhallat/muhallat/mukhalat; attar/ittar). Deliberately NOT
    # a bare "oud"/"oudh" token — that would over-floor the cheap mainstream "Amber
    # Oud" EDP sprays (a hero SKU), and NOT a bare "itr" (collides with "citrus").
    "dahn al", "dehn al", "dhan al", "dhen al", "dahn oud", "dehn oud", "dhan oud",
    "dahnal", "dehnal", "dhanal", "dahn al oudh", "dehn al oudh", "dhan al oudh",
    "mukhallat", "mukhallad", "mukhalat", "muhallat", "muhalat",
    "oud oil", "oudh oil", "oud perfume oil", "perfume oil", "oil perfume",
    "concentrated perfume", "concentrated oud", "attar", "ittar", "cpo",
}
# WORD-BOUNDARY match (not bare substring) so a short token can't collide with a
# name fragment — e.g. "attar" must NOT hit "muattar"/"moattar" (معطر = "scented",
# a cheap EDP name), "cpo" must not hit a larger word. \b around each phrase.
_BUDGET_HOUSE_PREMIUM_LINE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in sorted(_BUDGET_HOUSE_PREMIUM_LINE_TOKENS, key=len, reverse=True)) + r")\b"
)


def is_fragrance_query(product_name: str) -> bool:
    """True iff `product_name` is (almost certainly) a perfume — either a
    designer/niche fragrance house OR a generic fragrance product word. High-value
    electronics short-circuit to False (a phone is never a fragrance), so the two
    guards stay mutually exclusive."""
    if not product_name:
        return False
    # Mandatory coupled repoint (Q1 gate): use the is_high_value_query() function,
    # NOT the raw narrowed HIGH_VALUE_KEYWORDS set, so the fragrance guard and the
    # flagship floor agree on what's high-value after the EL-2 split.
    if is_high_value_query(product_name):
        return False
    name_lower = product_name.lower()
    if any(brand in name_lower for brand in FRAGRANCE_BRAND_KEYWORDS):
        return True
    return any(kw in name_lower for kw in FRAGRANCE_PRODUCT_KEYWORDS)


# The ORCHESTRATOR-RESOLVED pair category for the in-flight price fetch, set once at the
# top of scs._get_price. A per-task ContextVar (asyncio sub-tasks inherit a COPY at creation,
# and the pair's two _get_price tasks have independent contexts → no cross-contamination), so
# the deep render/page-scrape extractor chain (firecrawl/scrapedo/_fetch_page_price →
# extract_price_from_html/_jsonld) gets the authoritative category WITHOUT threading it through
# 5 helper layers. The variant-add KEYSTONE was leaking on those paths because weak keyword
# inference returned None for bare compounds (Magnesium) / brand-omitted lines (Galaxy Watch 6)
# (coverage review round 8 CRITICAL + independent review). Resolution order in the extractors:
# explicit category param > this ContextVar > _infer_category_from_query.
import contextvars as _contextvars
_resolved_category_ctx: "_contextvars.ContextVar[Optional[str]]" = _contextvars.ContextVar(
    "qaren_resolved_price_category", default=None,
)


def set_resolved_price_category(category: Optional[str]) -> None:
    """scs._get_price sets the in-flight pair category here so every downstream extractor
    resolves identity on the right axes even on the un-threaded render/page-scrape paths."""
    _resolved_category_ctx.set((category or "").strip().lower() or None)


def _resolve_extractor_category(explicit: Optional[str], query_name: str) -> Optional[str]:
    """explicit param > the orchestrator-resolved ContextVar > best-effort keyword inference.
    "other" is treated as unresolved (re-infer) — a frequent LLM label that must not disable
    the variant-add guard for a genuinely-categorizable product (round-8 CRITICAL)."""
    cat = (explicit or "").strip().lower()
    if cat and cat != "other":
        return cat
    ctx = (_resolved_category_ctx.get() or "").strip().lower()
    if ctx and ctx != "other":
        return ctx
    return _infer_category_from_query(query_name) or (cat or ctx or None)


def _infer_category_from_query(query_name: str) -> Optional[str]:
    """Best-effort category for the exact-identity gate when a caller (jsonld /
    page-scrape extractor) only has the query string, not the resolved category.
    Reuses the existing query detectors so the category axes (electronics
    qualifiers + colour aliasing, fragrance concentration, supplement count) engage
    on the right axis. Returns None for fashion/grocery/makeup/other (the gate then
    relies on identity-equality + the universal concentration/size/count checks)."""
    if not query_name:
        return None
    # COSMETIC detectors FIRST (coverage review round 2) — a topical form word makes the
    # product a cosmetic even when a supplement/fragrance token also matches: "Vitamin C
    # Serum" is skincare (not supplements), "Dior Addict Lip Glow" is makeup (not
    # fragrances). makeup before skincare (a NARS blush is makeup).
    if is_makeup_query(query_name):
        return "makeup"
    if is_skincare_query(query_name):
        return "skincare"
    if is_haircare_query(query_name):
        return "haircare"
    if is_supplement_query(query_name):
        return "supplements"
    if is_fragrance_query(query_name):
        return "fragrances"
    if is_fashion_query(query_name):
        return "fashion"
    if is_grocery_query(query_name):
        return "grocery"
    # BROAD electronics (coverage review CRITICAL) — resolves AirPods/Canon R6/Kindle/
    # headphones etc. so the variant-add guard engages on the scrape paths (was None ->
    # guard skipped -> AirPods Pro -> Pro 2 shown).
    if is_electronics_query(query_name):
        return "electronics"
    return None


def _effective_fragrance_size_ml(query_name: str, title: Optional[str]) -> float:
    """The size (ml) to floor against: the smallest size token found in the
    candidate `title` first (the listing's own size is the ground truth), else
    the query's stated size, else the flagship 100ml basis (an unspecified
    designer-fragrance query is priced at full-bottle by convention — same basis
    as flagship_basis_bonus). Returns a float ml."""
    for text in (title, query_name):
        if not text:
            continue
        sizes = extract_sizes_ml(text)
        if sizes:
            # Smallest detected size → most generous (lowest) floor, so a genuine
            # small decant is never wrongly rejected.
            return float(min(int(s) for s in sizes))
    return _FRAGRANCE_FLAGSHIP_SIZE_ML


def is_implausible_low_fragrance_price(
    product_name: str,
    amount: Optional[float],
    title: Optional[str] = None,
) -> bool:
    """True iff `product_name` is a designer/niche fragrance but `amount` (BHD) is
    implausibly low FOR ITS DETECTED/EXPECTED size — a sample/decant/wrong-SKU
    listing that must NOT be served as the genuine full-bottle price.

    Size-aware: the floor is the flagship 100ml floor scaled to the size the
    listing (or query) actually carries, so a genuine 30ml priced as a 30ml is
    KEPT while a 100ml-basis listing under the full-bottle floor is rejected.
    Returns False for non-fragrance products, non-designer/niche fragrances
    (mass-market body sprays can be genuinely cheap), and missing/zero amounts.
    Gated to luxury/designer/niche so it never over-rejects a cheap real perfume."""
    if amount is None or amount <= 0:
        return False
    if not is_fragrance_query(product_name):
        return False
    # Only DESIGNER/NICHE fragrances reliably have an expensive full bottle — a
    # generic "body spray" can be genuinely 3 BHD, so don't floor it.
    name_lower = product_name.lower()
    is_designer = (
        any(brand in name_lower for brand in FRAGRANCE_BRAND_KEYWORDS)
        or is_luxury_brand(product_name)
    )
    if not is_designer:
        return False
    # F1.2a — PREMIUM/niche houses use a higher per-100ml floor (50 vs 25), so a
    # decant/body-spray leak (Tobacco Vanille 28.2) is caught; the broader
    # designer set keeps the standard floor (no over-rejection of cheaper tiers).
    is_premium = any(brand in name_lower for brand in PREMIUM_FRAGRANCE_BRAND_KEYWORDS)
    base_floor = (
        PREMIUM_FRAGRANCE_FULL_SIZE_FLOOR_BHD if is_premium
        else FRAGRANCE_FULL_SIZE_FLOOR_BHD
    )
    size_ml = _effective_fragrance_size_ml(product_name, title)
    floor = base_floor * (size_ml / _FRAGRANCE_FLAGSHIP_SIZE_ML)
    floor = max(floor, _FRAGRANCE_MIN_FLOOR_BHD)
    return amount < floor


# F1.2b — PREMIUM haircare brands (K18, Olaplex, Kerastase, ...) are never a few
# BHD — K18 showed 4.51 BHD (genuine ~30+). A flat absolute floor (not size-aware:
# haircare sizes are small/varied and the price doesn't scale as cleanly as
# fragrance ml). Only PREMIUM brands are floored — a drugstore shampoo can be
# genuinely cheap.
PREMIUM_HAIRCARE_BRAND_KEYWORDS = {
    "k18", "olaplex", "kerastase", "kérastase", "redken", "moroccanoil",
    "oribe", "ouai", "living proof", "briogeo", "color wow", "k 18",
    "aveda", "pureology", "shu uemura", "davines", "virtue",
}
HAIRCARE_PRODUCT_KEYWORDS = {
    "shampoo", "conditioner", "hair mask", "hair oil", "hair serum",
    "leave-in", "leave in", "hair treatment", "scalp", "hair repair",
    "hair perfector", "bond builder", "heat protectant",
}
# A premium haircare product below this BHD is a wrong-SKU/sample leak.
PREMIUM_HAIRCARE_FLOOR_BHD = 12.0


def is_haircare_query(product_name: str) -> bool:
    """True iff `product_name` is (almost certainly) a haircare product — a known
    premium haircare brand OR a generic haircare product word."""
    if not product_name:
        return False
    name_lower = product_name.lower()
    if any(brand in name_lower for brand in PREMIUM_HAIRCARE_BRAND_KEYWORDS):
        return True
    return any(kw in name_lower for kw in HAIRCARE_PRODUCT_KEYWORDS)


def is_implausible_low_haircare_price(
    product_name: str, amount: Optional[float]
) -> bool:
    """True iff `product_name` is a PREMIUM haircare brand but `amount` (BHD) is
    implausibly low — a wrong-SKU/sample leak that must NOT be served as the
    genuine price (F1.2: K18 showed 4.51 BHD; genuine ~30+).

    Gated to premium brands only (a drugstore shampoo is genuinely cheap). Returns
    False for non-haircare products, non-premium haircare, and missing/zero
    amounts."""
    if amount is None or amount <= 0:
        return False
    name_lower = product_name.lower()
    is_premium = any(brand in name_lower for brand in PREMIUM_HAIRCARE_BRAND_KEYWORDS)
    if not is_premium:
        return False
    return amount < PREMIUM_HAIRCARE_FLOOR_BHD


# --- skincare / makeup / fashion query detectors (coverage review F) ----------
# Conservative keyword detectors so _infer_category_from_query resolves the right
# category on the JSON-LD / page-scrape path (where only the query string is known),
# engaging the per-category axes (%-strength / form / shoe-size / pack). Brand OR a
# product class word is enough; high-value electronics short-circuit elsewhere.
_SKINCARE_BRAND_KEYWORDS = {
    "cerave", "the ordinary", "paula's choice", "paulas choice", "la roche-posay",
    "la roche", "cetaphil", "drunk elephant", "the inkey list", "inkey", "cosrx",
    "skinceuticals", "bioderma", "eucerin", "first aid beauty", "kiehl's", "kiehls",
}
_SKINCARE_PRODUCT_KEYWORDS = {
    "serum", "moisturizer", "moisturiser", "cleanser", "niacinamide", "retinol",
    "hyaluronic", "salicylic", "glycolic", "sunscreen", "spf", "toner",
    "exfoliant", "face wash", "eye cream", "essence", "ampoule", "micellar",
    "face cream", "facial", "suspension", "peeling solution", "moisturizing lotion",
}
_MAKEUP_BRAND_KEYWORDS = {
    "nars", "charlotte tilbury", "fenty beauty", "rare beauty", "huda beauty",
    "huda", "too faced", "urban decay", "nyx", "rimmel", "benefit cosmetics",
    "anastasia beverly hills", "mac cosmetics", "maybelline", "estee lauder",
    "revlon", "bobbi brown", "clinique", "fit me", "studio fix", "pro filt",
    "double wear", "pillow talk", "ruby woo",
}
_MAKEUP_PRODUCT_KEYWORDS = {
    "lipstick", "blush", "mascara", "foundation", "concealer", "eyeshadow",
    "eyeliner", "highlighter", "bronzer", "lip gloss", "lipgloss", "lip liner",
    "setting powder", "setting spray", "contour", "liquid lipstick",
    "lip glow", "lip oil", "lip tint", "lip color", "lip balm", "lip stain",
    "rouge", "kohl", "kajal", "compact powder", "blusher",
}
_GROCERY_BRAND_KEYWORDS = {
    "coca-cola", "coca cola", "coke", "pepsi", "nescafe", "lipton", "lays",
    "doritos", "pringles", "red bull", "heinz", "oreo", "kitkat", "maggi",
    "quaker", "vimto", "rani", "almarai", "nadec", "fanta", "sprite", "7up",
}
_GROCERY_PRODUCT_KEYWORDS = {
    "instant coffee", "ground coffee", "coffee beans", "green tea", "black tea",
    "ketchup", "mayonnaise", "cereal", "cornflakes", "potato chips", "crisps",
    "soft drink", "fizzy drink", "fruit juice", "olive oil", "basmati rice",
    "butter", "cheese", "yogurt", "yoghurt", "bread", "biscuit", "biscuits",
    "peanut butter", "honey", "jam", "pasta", "noodles", "diapers", "diaper",
}


def is_grocery_query(product_name: str) -> bool:
    if not product_name:
        return False
    nl = product_name.lower()
    # WORD-BOUNDARY brand match (coverage R8): a bare `in` substring let 'lays' match
    # 'pLAYStation' → PlayStation misrouted to grocery (grocery is checked before electronics).
    return (any(_contains_token(nl, b) for b in _GROCERY_BRAND_KEYWORDS)
            or any(k in nl for k in _GROCERY_PRODUCT_KEYWORDS))


# BROAD electronics detector for _infer_category_from_query (coverage review CRITICAL):
# is_high_value_query is narrow (phone/laptop/console/GPU for the price floor) and returns
# None for mainstream electronics (AirPods/Canon R6/Kindle/headphones), which DISABLED the
# variant-add guard on the Serper-shopping + JSON-LD scrape paths (the runtime supplies the
# category the coverage tests hard-coded). This broader detector resolves them to electronics
# so the keystone engages end-to-end.
_ELECTRONICS_BRAND_KEYWORDS = {
    "apple", "samsung", "sony", "bose", "jbl", "logitech", "razer", "dyson", "canon",
    "nikon", "fujifilm", "gopro", "dji", "anker", "belkin", "sandisk", "kindle",
    "lg", "dell", "hp", "lenovo", "asus", "acer", "msi", "gigabyte", "huawei",
    "xiaomi", "oppo", "vivo", "realme", "oneplus", "nintendo", "microsoft", "google",
    "garmin", "fitbit", "sennheiser", "marshall", "beats", "nothing", "tcl", "hisense",
}
_ELECTRONICS_DEVICE_NOUNS = {
    "airpods", "earbuds", "earphones", "headphones", "headset", "headphone",
    "speaker", "soundbar", "camera", "dslr", "mirrorless", "lens", "laptop",
    "notebook", "tablet", "console", "monitor", "keyboard", "mouse", "router",
    "drone", "smartwatch", "powerbank", "graphics card", "gpu", "ssd", "hard drive",
    "projector", "printer", "webcam", "microphone",
    # self-identifying device LINES (electronics on their own, even with no model number).
    "kindle", "ipad", "iphone", "macbook", "playstation", "xbox", "airpod",
}


def is_electronics_query(product_name: str) -> bool:
    if not product_name:
        return False
    if is_high_value_query(product_name):
        return True
    nl = product_name.lower()
    if any(_contains_token(nl, n) if " " not in n else n in nl
           for n in _ELECTRONICS_DEVICE_NOUNS):
        return True
    # an electronics brand + ANY digit (a model number: R6, WH-1000XM5, V15, 4070).
    if any(_contains_token(nl, b) for b in _ELECTRONICS_BRAND_KEYWORDS) and any(c.isdigit() for c in nl):
        return True
    return False
_FASHION_BRAND_KEYWORDS = {
    "air jordan", "jordan", "air force", "air max", "dunk", "yeezy", "samba",
    "gazelle", "new balance", "converse", "vans", "timberland", "superstar",
    "stan smith", "ultraboost",
}
_FASHION_PRODUCT_KEYWORDS = {
    "sneakers", "sneaker", "trainers", "hoodie", "t-shirt", "tshirt", "jeans",
    "jacket", "dress", "sweatshirt", "shorts", "leggings", "backpack", "handbag",
}


def is_skincare_query(product_name: str) -> bool:
    if not product_name:
        return False
    nl = product_name.lower()
    return (any(b in nl for b in _SKINCARE_BRAND_KEYWORDS)
            or any(k in nl for k in _SKINCARE_PRODUCT_KEYWORDS))


def is_makeup_query(product_name: str) -> bool:
    if not product_name:
        return False
    nl = product_name.lower()
    return (any(b in nl for b in _MAKEUP_BRAND_KEYWORDS)
            or any(k in nl for k in _MAKEUP_PRODUCT_KEYWORDS))


def is_fashion_query(product_name: str) -> bool:
    if not product_name:
        return False
    nl = product_name.lower()
    return (any(b in nl for b in _FASHION_BRAND_KEYWORDS)
            or any(k in nl for k in _FASHION_PRODUCT_KEYWORDS))


# ============================================
# Task C1 — price-pending presentation (showable predicate)
# ============================================
#
# Per Ahmed's decision (fragrance-quality redesign): we do NOT raise a floor to
# fabricate a "plausible" amount. Instead, when a resolved price is NOT
# genuine/showable, the backend flags it (price-pending shape) so the app can
# render an engaging "pricing in a future update" line (FE work, Phase 4). This
# aligns with the standing "estimates unacceptable" KPI.

# A real converted price is fine to show (an honest converted label is shipped
# already). So the showable set is the genuine-BH methods PLUS converted_usd.
# `estimated` is the canonical NON-showable method. `_GENUINE_BH_SOURCE_METHODS`
# is defined further down the module, so resolve the set lazily at call time.
def _showable_source_methods() -> frozenset:
    return frozenset(_GENUINE_BH_SOURCE_METHODS) | {"converted_usd"}

# A title token that marks a listing as a sample/decant/tester — never the
# genuine full-bottle price regardless of the amount.
_SAMPLE_LISTING_RE = re.compile(r"\b(sample|decant|tester|vial)s?\b", re.I)

# A "tiny" fragrance listing (<= this ml) priced at/above this BHD is a decant
# masquerading at full-bottle money — not a genuine showable price. Kept narrow
# (only flags small sizes carrying a clearly-too-high amount) so a genuine 30ml
# at a sane price is untouched.
_TINY_FRAGRANCE_SIZE_ML = 10
_TINY_FRAGRANCE_IMPLAUSIBLE_BHD = 30.0


def _is_sample_or_decant_listing(product_name: str, title: Optional[str], amount: Optional[float]) -> bool:
    """True iff the price clearly comes from a sample/decant/tester listing —
    either an explicit token in the title OR a tiny fragrance size (<=10ml)
    carrying a full-bottle-grade price. Returns False for non-fragrance products
    (a small electronics SKU is not a 'decant')."""
    # schema.org name/title can be a LIST (or other non-str) — coerce so the regex never
    # TypeErrors and crashes the request instead of failing closed (comprehensive review).
    if isinstance(title, (list, tuple)):
        title = " ".join(str(x) for x in title)
    text = str(title) if title else ""
    if _SAMPLE_LISTING_RE.search(text):
        return True
    # Tiny-size-with-implausible-price only applies to fragrances (a 5ml phone
    # makes no sense; this heuristic is about decants priced like bottles).
    if amount and amount > 0 and is_fragrance_query(product_name):
        sizes = extract_sizes_ml(text)
        if sizes:
            smallest = min(int(s) for s in sizes)
            if smallest <= _TINY_FRAGRANCE_SIZE_ML and amount >= _TINY_FRAGRANCE_IMPLAUSIBLE_BHD:
                return True
    return False


def is_price_showable(
    product_name: str, price: Optional[Dict[str, Any]], category: Optional[str] = None,
    *, enforce_correctness: bool = False,
) -> bool:
    """True iff a resolved `price` object is GENUINE/CORRECT/showable to the user.

    NOT showable (→ Phase-4 price-pending line) when:
      - no price / no positive amount, OR
      - source_method is missing or not in the showable set (e.g. ``estimated``), OR
      - it fails an accuracy guard (low-fragrance sample floor / high-value
        accessory leak), OR
      - it is a sample/decant/tester/vial listing, OR
      - (correctness backstop, gated by ENABLE_EXACT_PRICE_GATE) it is explicitly
        OUT OF STOCK, served behind a non-PDP listing/search URL, or NOT the exact
        requested product (wrong variant/concentration/size/storage/count).

    `converted_usd` and the genuine-BH methods (local_bhd / page_scrape* /
    shopify_json / firecrawl* / scrapedo_rendered / official_brand) are showable —
    but converted_usd, like every method, must ALSO be the exact product. This is
    the single predicate the response chokepoint uses for BOTH the sync and
    streaming paths; it never weakens the existing is_implausible_* guards — it
    composes them. The fail-closed correctness backstop is defense-in-depth behind
    the per-extractor is_exact_match gate; when a guard rejects, it stamps
    ``price['guard_rejected']`` so the drop is MEASURED, never silent.
    """
    if not isinstance(price, dict):
        return False
    amount = price.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        return False
    source_method = price.get("source_method") or ""
    if source_method not in _showable_source_methods():
        return False
    title = price.get("title")
    # schema.org name/title can be a LIST (or other non-str) — coerce ONCE here so every
    # downstream guard (is_counterfeit_listing/.lower(), the sample-listing regex, the
    # backstop) never AttributeError/TypeErrors and crashes the request instead of failing
    # closed (comprehensive review crash). Mutate the dict so the resolved title is consistent.
    if isinstance(title, (list, tuple)):
        title = " ".join(str(x) for x in title)
        price["title"] = title
    elif title is not None and not isinstance(title, str):
        title = str(title)
        price["title"] = title
    # Compose the shipped accuracy guards — a price that fails any is not
    # showable (the guards already encode the "no wrong scrapes" contract).
    # EXCEPTION (budget Arabic-house coverage) — a genuine direct-adapter exact-PDP
    # price for a budget house (Lattafa/Rasasi/Al Haramain/...) bypasses the
    # designer low-price FLOOR: it is the store's authoritative listed price for the
    # exact SKU, so the 25/100ml floor is a false positive there. The floor still
    # runs on the loose Serper-shopping path (unaffected). Flag OFF / non-genuine /
    # listing-URL / expensive-oil-line -> the floor applies unchanged.
    if is_implausible_low_fragrance_price(product_name, amount, title=title) and not (
        _budget_house_trusted_price(product_name, price)
    ):
        return False
    # F1.2b — premium haircare wrong-cheap leak (K18 4.51 BHD).
    if is_implausible_low_haircare_price(product_name, amount):
        return False
    if is_implausible_high_value_price(product_name, amount):
        return False
    if _is_sample_or_decant_listing(product_name, title, amount):
        return False
    # --- correctness backstop (CARDINAL RULE) — OPT-IN via enforce_correctness ---
    # Defense-in-depth at the RESPONSE CHOKEPOINT only (response_builder + streaming
    # pass enforce_correctness=True). It is NOT applied to the legacy adapter /
    # reselect plausibility calls: an adapter legitimately RETURNS an out-of-stock
    # price flagged in_stock=False (the chokepoint then pends it), and the fairness
    # reselect DELIBERATELY re-selects to a DIFFERENT size — so an always-on backstop
    # here would wrongly pend both. Gated by ENABLE_EXACT_PRICE_GATE (rollback).
    if enforce_correctness and exact_gate_enabled():
        if price.get("in_stock") is False:
            price["guard_rejected"] = "out_of_stock"
            return False
        # A listing/search URL is never a PDP -> pend. A MISSING url is NOT pended
        # HERE: the PDP-URL + identity requirement is enforced at SELECTION
        # (select_best, where multi-candidate adapters carry title+url) + CACHE-WRITE
        # (should_cache_price) + the usable_exact_genuine KPI — exactly the directive's
        # "require title/name + a valid PDP URL BEFORE selection OR cache write". The
        # display chokepoint must NOT re-pend an already-resolved genuine price merely
        # for an absent url/title field, or it over-rejects the broad "genuine
        # source_method + amount = showable" contract (Task C1 + ws5 + timeout-partial).
        url = price.get("url")
        if url and _is_listing_url(url):
            price["guard_rejected"] = "non_pdp_url"
            return False
        identity = title or price.get("name")
        # CARDINAL RULE (coverage review F) — a genuine-method price with NO identity
        # (no title/name) AND NO url has NOTHING to verify the exact product against, so
        # it must PEND, not be shown. A price with EITHER a title OR a url is still
        # showable here (the full PDP-URL+identity requirement is enforced at SELECTION +
        # cache-write, not re-pended at the display chokepoint, per the calibration that
        # keeps the broad "genuine source_method + amount = showable" contract). Real
        # adapter/cache prices always carry both; only a truly-unverifiable price pends.
        if not identity and not url:
            price["guard_rejected"] = "no_identity"
            return False
        # An electronics accessory matched as the device itself (narrow set + category
        # gate so a genuine standalone keyboard / headphone / skincare title is not pended).
        if (identity and (category or "").lower() == "electronics"
                and _is_device_accessory(identity) and not _is_device_accessory(product_name)):
            price["guard_rejected"] = "accessory"
            return False
        # Identity gate at the display chokepoint = the axis-only _backstop_identity_ok
        # PLUS the FLAGSHIP-concentration / supplement-TYPE flanker check
        # (_category_type_added). The full superset _selection_match was tried here and an
        # adversarial coverage sweep CONFIRMED it over-rejects CORRECT products that reach
        # display via a path that did not pre-run _selection_match (converted_usd /
        # page-scrape / iHerb), because their genuine DESCRIPTIVE PDP title carries extra
        # marketing tokens the short query omits ("Niacinamide 10%" -> the real SKU title
        # "Niacinamide 10% + Zinc 1%"; "Omega-3" -> "...Molecularly Distilled"). So the
        # superset stays UPSTREAM (brand-aware, where the canonical full_name is known); the
        # backstop adds only the bounded flagship/type-ADD check, which catches the common
        # flanker class ("Sauvage" -> "Sauvage Parfum/Extrait", "Whey" -> "Whey Isolate")
        # with no descriptive-title over-rejection. A same-token flanker whose extra token is
        # NOT a flagship concentration ("Sauvage Elixir") remains a documented deferred leak.
        if identity:
            _ok, _reason = backstop_identity_verdict(product_name, identity, category)
            if not _ok:
                price["guard_rejected"] = _reason or "not_exact"
                return False
    return True


def make_pending_price(currency: str = "BHD", reason: str = "pending_genuine",
                       size: Optional[str] = None) -> Dict[str, Any]:
    """The price-pending object the FE (Phase 4) renders as a 'pricing in a
    future update' line. No misleading amount is emitted. `size` carried through
    when known so the FE can still show the bottle size context."""
    pending: Dict[str, Any] = {
        "amount": None,
        "currency": currency or "BHD",
        "unavailable": True,
        "reason": reason,
    }
    if size:
        pending["size"] = size
    return pending


def _product_size_text_fields(product: Dict[str, Any]) -> List[str]:
    """The free-text fields a product's size could be hiding in, in PRECEDENCE
    order: the product NAME the user actually compared (full_name / name) first,
    then the price listing title, then the spec volume. Each is scanned for a
    `\\d+ml` token by effective_pair_size_ml."""
    fields: List[str] = []
    for key in ("full_name", "name"):
        val = product.get(key)
        if isinstance(val, str) and val:
            fields.append(val)
    price = product.get("price")
    if isinstance(price, dict):
        title = price.get("title")
        if isinstance(title, str) and title:
            fields.append(title)
        size = price.get("size")
        if isinstance(size, str) and size:
            fields.append(size)
    specs = product.get("specs")
    if isinstance(specs, dict):
        for key in ("volume", "size", "concentration"):
            val = specs.get(key)
            if isinstance(val, str) and val:
                fields.append(val)
    return fields


def effective_pair_size_ml(
    product: Dict[str, Any],
    treat_unsized_as_flagship: bool = False,
) -> Optional[float]:
    """ITEM 2 — the SIZE (ml) a product is effectively being compared at, derived
    from ALL available signals — product NAME first (the listing the user named
    is ground truth), then price listing title, then price.size, then the spec
    volume. This is the FAIRNESS basis the pair must agree on.

    Returns:
      - the smallest `\\d+ml` token found across those fields (a name like
        "Tobacco Vanille 30 ML" resolves 30 even when price.size is None), ELSE
      - the flagship 100ml basis for a SIZE-UNSPECIFIED DESIGNER/NICHE fragrance
        (matches flagship_basis_bonus / the per-product selection convention, so
        two unsized designer fragrances converge on the same 100ml basis), ELSE
      - None for any non-fragrance / non-designer product with no size signal (so
        two unsized phones stay None==None and never trip a false mismatch).

    `treat_unsized_as_flagship` (frag-reconcile fix, flag-gated by the caller):
    when True, a SIZE-UNSPECIFIED product defaults to the flagship 100ml basis
    even when the NAME is not _is_designer_fragrance_name-recognized. The caller
    passes True ONLY on the canon=="fragrances" reconcile path, where the
    orchestrator already confirmed the pair is a fragrance — so the too-narrow
    brand-keyword heuristic must not be the gate for the flagship default. It
    NEVER overrides an explicit size token (any `\\d+ml` above still wins), so a
    genuine 30ml/50ml still resolves to its real size.
    """
    if not isinstance(product, dict):
        return None
    for text in _product_size_text_fields(product):
        sizes = extract_sizes_ml(text)
        if sizes:
            # Smallest detected size — a single listing carries one bottle size;
            # if several tokens appear ("30ml 100ml" range text) the smaller is
            # the conservative basis.
            return float(min(int(s) for s in sizes))
    # No explicit size anywhere. A designer/niche fragrance defaults to the
    # flagship 100ml retail basis (same convention as the per-product flagship
    # bias), so two unsized designer fragrances are treated as the SAME basis.
    name = product.get("full_name") or product.get("name") or ""
    if _is_designer_fragrance_name(name):
        return _FRAGRANCE_FLAGSHIP_SIZE_ML
    # frag-reconcile fix — the caller has already established (via the resolved
    # category) that this is a fragrance; default an unsized fragrance to the
    # flagship basis even when the name is not brand-keyword-recognized.
    if treat_unsized_as_flagship:
        return _FRAGRANCE_FLAGSHIP_SIZE_ML
    return None


def _is_designer_fragrance_name(name: str) -> bool:
    """True iff `name` is a DESIGNER/NICHE fragrance — a house in
    FRAGRANCE_BRAND_KEYWORDS or any luxury brand AND a fragrance query. This is
    the SAME gate used by is_implausible_low_fragrance_price and the flagship-
    basis default, hoisted to a shared helper so the flagship-target logic and
    the per-product floor stay in lockstep (a generic 'body spray' is NOT
    designer → never gets a flagship target/floor)."""
    if not name or not is_fragrance_query(name):
        return False
    name_lower = name.lower()
    return (
        any(brand in name_lower for brand in FRAGRANCE_BRAND_KEYWORDS)
        or is_luxury_brand(name)
    )


def target_pair_size_ml(
    user_query: Optional[str],
    p0: Dict[str, Any],
    p1: Dict[str, Any],
    treat_unsized_as_flagship: bool = False,
) -> Optional[float]:
    """The size (ml) the PAIR should be compared at — the FAIRNESS target.

    Precedence (Part A — the target comes from the USER QUERY, never a matched
    listing NAME the backend appended):
      1. An explicit `\\d+ml` size in the USER QUERY → that size (applies to any
         category; if the user typed a size, honor it).
      2. No user size + BOTH products are designer/niche fragrances → the flagship
         100ml retail basis (the size-UNSPECIFIED designer convention, reusing
         _FRAGRANCE_FLAGSHIP_SIZE_ML / flagship_basis_bonus). A matched product
         name carrying "30 ML" does NOT set the target here.
      3. Otherwise → None (no shared target: non-fragrance pairs, mixed pairs).
         The caller then falls back to the legacy effective-size comparison, so
         electronics is completely untouched.
    """
    if user_query:
        q_sizes = extract_sizes_ml(user_query)
        if q_sizes:
            return float(min(int(s) for s in q_sizes))
    n0 = (p0.get("full_name") or p0.get("name") or "") if isinstance(p0, dict) else ""
    n1 = (p1.get("full_name") or p1.get("name") or "") if isinstance(p1, dict) else ""
    if _is_designer_fragrance_name(n0) and _is_designer_fragrance_name(n1):
        return _FRAGRANCE_FLAGSHIP_SIZE_ML
    # frag-reconcile fix — on the canon=="fragrances" path the pair is already
    # known to be fragrances; a size-SILENT designer/retail pair shares the same
    # flagship 100ml basis even when neither name is brand-keyword-recognized.
    # An explicit user size above still wins; a per-product explicit size is
    # honored later in reconcile (effective size != target -> re-select / pend).
    if treat_unsized_as_flagship:
        return _FRAGRANCE_FLAGSHIP_SIZE_ML
    return None


def _candidate_size_ml(c: Dict[str, Any]) -> Optional[float]:
    """The effective ml of a RETAINED price candidate, read from its raw_data /
    own fields: the price.size annotation first, then the listing title (a Shopify
    /products.json variant often carries the size only in the title). Returns the
    smallest `\\d+ml` token, or None when the candidate carries no size signal."""
    if not isinstance(c, dict):
        return None
    raw = c.get("raw_data") if isinstance(c.get("raw_data"), dict) else {}
    for src in (raw, c):
        for key in ("size", "title"):
            val = src.get(key)
            if isinstance(val, str) and val:
                sizes = extract_sizes_ml(val)
                if sizes:
                    return float(min(int(s) for s in sizes))
    return None


def reselect_to_target_size(
    product_name: str,
    candidates: Optional[List[Dict[str, Any]]],
    target_ml: float,
    currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Re-select a product's price to `target_ml` from the candidates ALREADY
    fetched this request (Part B — NO new network).

    Picks the best GENUINE candidate (genuine-BH source ∪ converted_usd) that:
      - carries the target size (candidate size == target_ml), AND
      - passes the shipped accuracy guards (is_implausible_low_fragrance_price /
        is_implausible_high_value_price) — a sample/decant/wrong-SKU 100ml under
        the full-bottle floor is NOT a valid re-selection.

    Ranking reuses the existing precedence: genuine-BH authority first, then the
    candidate's variant_rank (the WS5 size/concentration precision signal), then
    cheapest. Returns a clean price dict (raw_data with source_method stamped) or
    None when no acceptable target-size candidate exists (→ the caller pends that
    product). Pure + side-effect-free.
    """
    if not candidates:
        return None
    acceptable: List[Dict[str, Any]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        size = _candidate_size_ml(c)
        if size is None or size != target_ml:
            continue
        raw = c.get("raw_data") if isinstance(c.get("raw_data"), dict) else None
        price = dict(raw) if raw else None
        if price is None:
            # No raw_data — synthesize a minimal price dict from the candidate.
            amount = c.get("value")
            if amount is None:
                continue
            price = {
                "amount": amount,
                "currency": currency,
                "source_method": c.get("source_method") or "",
                "retailer": c.get("retailer"),
                "title": c.get("title"),
                "size": c.get("size"),
            }
        else:
            # Stamp the selection source_method onto the price (mirrors
            # _finalize_fan_winner: best.raw_data + best.source_method).
            price.setdefault("source_method", c.get("source_method") or "")
            if c.get("source_method"):
                price["source_method"] = c.get("source_method")
        # CORRECTNESS — never re-select an explicitly OUT-OF-STOCK candidate (a
        # costlier in-stock exact beats a cheap OOS; with no in-stock match the
        # product pends), and never swap an EDP query onto a cheaper EDT just because
        # both are 100ml. Checked here, NOT via the is_price_showable axis backstop:
        # this re-selection DELIBERATELY targets a DIFFERENT SIZE for pair fairness,
        # so the size axis must not run — only stock + concentration. Gated by
        # exact_gate_enabled() so a rollback is byte-identical to b207bfa.
        if exact_gate_enabled():
            if c.get("in_stock") is False or price.get("in_stock") is False:
                continue
            _c_title = c.get("title") or price.get("title") or ""
            if _concentration_mismatch(product_name, _c_title):
                continue
        # Use the CANONICAL plausibility predicate (genuine/converted source ∪ the
        # is_implausible_* accuracy guards ∪ the sample/decant title check) — the
        # SAME gate the response chokepoint applies downstream. This guarantees a
        # re-selected price actually survives C1 (we never claim "show" for a
        # price that the downstream gate would null), and never re-selects a wrong
        # scrape / sample / decant.
        if not is_price_showable(product_name, price):
            continue
        acceptable.append({"_cand": c, "_price": price})

    if not acceptable:
        return None
    # Authority (genuine-BH first) → variant_rank (size/concentration precision)
    # → cheapest. Mirrors _select_best + the WS5 variant tie-break.
    best = max(
        acceptable,
        key=lambda a: (
            1 if _is_genuine_bh_candidate(a["_cand"]) else 0,
            float(a["_cand"].get("variant_rank", 0) or 0),
            -float(a["_price"].get("amount", 0) or 0),
        ),
    )
    return best["_price"]


def reconcile_pair_sizes(
    product_data: List[Dict[str, Any]],
    user_query: Optional[str] = None,
    candidates_by_name: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    treat_unsized_as_flagship: bool = False,
) -> bool:
    """Task C2 + ITEM 2 + same-size GENUINE re-selection — pair-level size-basis
    reconciliation (FAIRNESS).

    The pair must be compared at a COMMON size. The TARGET size comes from the
    USER QUERY (an explicit `\\d+ml`), else the designer-fragrance flagship 100ml
    when BOTH products are designer/niche fragrances — NEVER from a matched
    listing NAME the backend appended (target_pair_size_ml, Part A).

    Each product is then resolved to the target size, RE-SELECTING from the
    candidates ALREADY fetched this request (`candidates_by_name`, keyed by
    full_name) when its currently-selected price is off-target — no new network
    (Part B, reselect_to_target_size). Outcome priority:

      1. BOTH reach the target genuinely → show BOTH (the win — e.g. Ombré 80 @
         100ml + Tobacco re-selected to its genuine 100ml listing).
      2. Only ONE reaches the target → show that one, pend ONLY the other
         (reason="size_mismatch"). A genuine common-basis price is never dropped
         just because its partner can't match (the Tom Ford fallback: Ombré 80
         shows, Tobacco pends).
      3. NEITHER reaches the target → BOTH pending (the prior behavior).

    No TARGET derivable (non-fragrance / mixed pair with no user size) → fall
    back to the legacy effective-size comparison (both-pending on a genuine
    divergence), so electronics is completely untouched.

    Pure + in-place (apart from candidate-driven price swaps); returns True iff
    it changed any price (a swap OR a pend). No network, no latency.

    No-ops when: either price is missing/non-positive (a C1-pending side already
    kills the cross-size delta), or both sides already sit at the same basis.
    """
    if not isinstance(product_data, list) or len(product_data) < 2:
        return False
    p0, p1 = product_data[0], product_data[1]
    price0 = p0.get("price") if isinstance(p0, dict) else None
    price1 = p1.get("price") if isinstance(p1, dict) else None
    if not isinstance(price0, dict) or not isinstance(price1, dict):
        return False
    amt0, amt1 = price0.get("amount"), price1.get("amount")
    # Only act when BOTH sides have a real, comparable amount. If either is
    # None/<=0 (e.g. already C1-pending), there is no cross-size delta to guard.
    if not (isinstance(amt0, (int, float)) and amt0 > 0):
        return False
    if not (isinstance(amt1, (int, float)) and amt1 > 0):
        return False

    # Fairness fix (2026-07-07) — an ESTIMATE is not a comparable DISPLAYED price
    # (the chokepoint suppresses it) and has no real size basis, so the flagship
    # 100ml default wrongly made a sizeless estimate 'reach the target' and PEND
    # the pair's genuine, showable price (Ajmal Aristocrat 21.5 pended because
    # Rasasi only estimated). Treat an estimate side as non-comparable → no-op → the
    # genuine price stays; the estimate suppresses to pending at display. Flag-gated
    # (default ON) → flag-OFF byte-identical (the prior pend-the-genuine behavior).
    if _fairness_ignore_estimate_enabled() and (
        _is_estimate_price(price0) or _is_estimate_price(price1)
    ):
        return False

    # An EXPLICIT user size is authoritative; otherwise the only shared target is
    # the designer-fragrance flagship default.
    user_size = None
    if user_query:
        _q = extract_sizes_ml(user_query)
        if _q:
            user_size = float(min(int(s) for s in _q))

    # FAIR ALREADY — when the user did NOT type a size, two products that sit at
    # the SAME effective size are a valid common basis (two shared "50ml"
    # listings, two unsized designer fragrances both at the flagship 100ml
    # default, ...). Honor it and pass through. This must run BEFORE the
    # flagship-target derivation so a SHARED explicit size the user didn't type is
    # never overridden up to 100ml. (When the user DID type a size, the target is
    # authoritative — the re-selection path below resolves to it.)
    eff0 = effective_pair_size_ml(p0, treat_unsized_as_flagship)
    eff1 = effective_pair_size_ml(p1, treat_unsized_as_flagship)
    if user_size is None and eff0 is not None and eff0 == eff1:
        return False

    target = target_pair_size_ml(user_query, p0, p1, treat_unsized_as_flagship)

    # No shared target (non-fragrance / mixed pair, no user size) → legacy
    # effective-size comparison. Equal/both-unknown → no-op; genuine divergence →
    # both pending. Electronics stays exactly as before.
    if target is None:
        size0 = effective_pair_size_ml(p0, treat_unsized_as_flagship)
        size1 = effective_pair_size_ml(p1, treat_unsized_as_flagship)
        if size0 == size1:
            return False
        _mark_size_pending(p0, p1)
        return True

    candidates_by_name = candidates_by_name or {}
    changed = False

    def _resolve_to_target(p: Dict[str, Any]) -> bool:
        """Return True iff `p` ends up AT the target size. Re-selects from
        retained candidates when the current price is off-target; on a successful
        swap mutates p['price'] (+ best_price/retailer) in place."""
        nonlocal changed
        if effective_pair_size_ml(p, treat_unsized_as_flagship) == target:
            return True
        name = p.get("full_name") or p.get("name") or ""
        cands = candidates_by_name.get(name) or candidates_by_name.get(p.get("name") or "")
        new_price = reselect_to_target_size(
            name, cands, target,
            currency=(p.get("price") or {}).get("currency") or "BHD",
        )
        if new_price is None:
            return False
        p["price"] = new_price
        amount = new_price.get("amount")
        if "best_price" in p:
            p["best_price"] = amount
        if "retailer" in p:
            p["retailer"] = new_price.get("retailer")
        changed = True
        return True

    at0 = _resolve_to_target(p0)
    at1 = _resolve_to_target(p1)

    if at0 and at1:
        # Outcome 1 — both at the target basis. Either already converged (no-op)
        # or one/both re-selected (changed=True). Show both.
        return changed
    if at0 and not at1:
        # Outcome 2 — pend ONLY p1; p0's genuine common-basis price stays.
        _mark_size_pending(p1)
        return True
    if at1 and not at0:
        _mark_size_pending(p0)
        return True
    # Outcome 3 — neither reached the target → both pending.
    _mark_size_pending(p0, p1)
    return True


def _mark_size_pending(*products: Dict[str, Any]) -> None:
    """Mark each product price-pending (reason="size_mismatch"), preserving its
    own size annotation for FE context and nulling best_price/retailer."""
    for p in products:
        if not isinstance(p, dict):
            continue
        price = p.get("price") if isinstance(p.get("price"), dict) else {}
        p["price"] = make_pending_price(
            currency=price.get("currency") or "BHD",
            reason="size_mismatch",
            size=price.get("size"),
        )
        if "best_price" in p:
            p["best_price"] = None
        if "retailer" in p:
            p["retailer"] = None


# ============================================================================
# CATEGORY-AWARE FAIRNESS STANDARD (generalizes the fragrance pair-size fix)
# ============================================================================
#
# CATEGORY_FAIRNESS is the SINGLE SOURCE OF TRUTH for "what makes two products
# in this category comparable on price". The fragrance pair-size reconcile (a
# pair must be priced at a COMMON ml, re-selecting genuine prices from retained
# candidates) is now ONE instance of a general per-category rule.
#
# Per category → the comparable "must-match" unit (None when the category has
# no single comparable axis — fashion/other), an `extract` that reads that
# unit off a PRODUCT, a `user_query_value` that reads it off the USER QUERY,
# and a `default_basis(p0, p1)` that supplies the pair target when the query is
# silent. Shape (each value a callable unless noted):
#
#   {
#     "unit":             str | None,        # the axis name (e.g. "GB", "ml")
#     "extract":          (product) -> float | None,
#     "normalize":        (value)   -> value, # canonicalize a raw value (identity
#                                             #   here — extractors already
#                                             #   normalize TB→GB / kg→g / L→ml)
#     "user_query_value": (query)   -> float | None,
#     "default_basis":    (p0, p1)  -> float | None,  # pair target, query-silent
#     "label":            str,               # human label for the unit
#   }
#
# Categories (per the fairness spec):
#   electronics → storage GB (TB→GB); spec storage → variant → name; default =
#                 the resolved base (NO force-bump — the smaller achievable
#                 capacity in the pair); exact match.
#   fragrances  → ml; REUSES effective_pair_size_ml + the flagship-100ml
#                 default verbatim, so the shipped fragrance behavior is
#                 byte-preserved (the per-fragrance helpers are the callables).
#   supplements → unit count (caps/tablets/softgels) from spec count / name.
#   grocery     → net weight/volume (g/kg→g, ml/L→ml) from spec size / name.
#   makeup      → volume/weight (ml or g).
#   skincare    → volume/weight (ml or g).
#   haircare    → volume (ml).
#   fashion     → None (no single comparable unit).
#   other       → None.


def _identity(value):
    """Default `normalize` — the extractors already normalize units (TB→GB,
    kg→g, L→ml), so the stored value is canonical."""
    return value


def _product_unit_text_fields(product: Dict[str, Any], spec_keys: Tuple[str, ...]) -> List[str]:
    """Free-text fields a product's unit could hide in, PRECEDENCE order:
    the named spec field(s) first (the structured value is ground truth), then
    the top-level `variant` (e.g. "256GB"), then the product NAME, then the
    price listing title. Mirrors _product_size_text_fields' precedence idea but
    parameterized by the per-category spec key list."""
    fields: List[str] = []
    specs = product.get("specs")
    if isinstance(specs, dict):
        for key in spec_keys:
            val = specs.get(key)
            if isinstance(val, str) and val:
                fields.append(val)
            elif isinstance(val, (int, float)):
                fields.append(str(val))
    variant = product.get("variant")
    if isinstance(variant, str) and variant:
        fields.append(variant)
    for key in ("full_name", "name"):
        val = product.get(key)
        if isinstance(val, str) and val:
            fields.append(val)
    price = product.get("price")
    if isinstance(price, dict):
        for key in ("title", "size"):
            val = price.get(key)
            if isinstance(val, str) and val:
                fields.append(val)
    return fields


def _first_non_none(fields: List[str], parser) -> Optional[float]:
    """Apply `parser` (returns float|None) to each field in precedence order;
    return the first non-None result, else None."""
    for text in fields:
        v = parser(text)
        if v is not None:
            return v
    return None


def _extract_storage(product: Dict[str, Any]) -> Optional[float]:
    """Electronics comparable unit: storage GB. spec `storage` → `variant` →
    name → price title (precedence)."""
    if not isinstance(product, dict):
        return None
    return _first_non_none(
        _product_unit_text_fields(product, ("storage",)), extract_storage_gb
    )


def _extract_count(product: Dict[str, Any]) -> Optional[float]:
    """Supplements comparable unit: unit count. spec `count` → name → title."""
    if not isinstance(product, dict):
        return None
    return _first_non_none(
        _product_unit_text_fields(product, ("count", "serving_size")), extract_count
    )


def _extract_ml_only(product: Dict[str, Any]) -> Optional[float]:
    """Haircare comparable unit: volume (ml). spec `volume` → variant → name →
    title. (Reuses extract_sizes_ml — ml only, no weight axis.)"""
    if not isinstance(product, dict):
        return None
    def _ml(text: str) -> Optional[float]:
        sizes = extract_sizes_ml(text)
        return float(min(int(s) for s in sizes)) if sizes else None
    return _first_non_none(
        _product_unit_text_fields(product, ("volume", "size")), _ml
    )


def _extract_volume_or_weight(product: Dict[str, Any]) -> Optional[float]:
    """Makeup/skincare comparable unit: volume OR weight (ml or g). spec
    `volume`/`size` → variant → name → title. Returns the numeric magnitude;
    the base (ml vs g) gates comparability inside reconcile via _unit_base."""
    if not isinstance(product, dict):
        return None
    res = _first_non_none(
        _product_unit_text_fields(product, ("volume", "size")),
        lambda t: (extract_weight_or_volume(t) or (None,))[0],
    )
    return res


def _extract_grocery(product: Dict[str, Any]) -> Optional[float]:
    """Grocery comparable unit: net weight/volume (g or ml). spec `size`/
    `count` → name → title."""
    if not isinstance(product, dict):
        return None
    return _first_non_none(
        _product_unit_text_fields(product, ("size", "net_weight")),
        lambda t: (extract_weight_or_volume(t) or (None,))[0],
    )


def _unit_base(product: Dict[str, Any], spec_keys: Tuple[str, ...]) -> Optional[str]:
    """For the weight/volume categories — which base ("ml"/"g") a product's
    value is on, so two products on DIFFERENT bases (a 200g cream vs a 50ml
    serum) are never declared a mismatch (they're simply incomparable → no
    target). None when no weight/volume token present."""
    if not isinstance(product, dict):
        return None
    for text in _product_unit_text_fields(product, spec_keys):
        res = extract_weight_or_volume(text)
        if res is not None:
            return res[1]
    return None


def _resolved_base_default(p0: Dict[str, Any], p1: Dict[str, Any], extractor) -> Optional[float]:
    """Generic query-silent default for EXACT-match units (electronics storage,
    supplement count, volume/weight): the resolved base = the LARGER of the two
    products' resolved values.

    "NO force-bump" means we NEVER invent a value that is absent from the pair
    (the way fragrances bump to a flagship 100ml even when neither product is
    100ml). We only ever target a capacity/count/volume ALREADY present on one
    of the two products. The larger is chosen because it is the more complete /
    standard SKU and mirrors the fragrance flagship convention's spirit (target
    the standard full size, re-selecting the partner up to it from retained
    genuine candidates when one exists). Returns None when neither product
    resolves a value (nothing in the pair to anchor on)."""
    v0 = extractor(p0)
    v1 = extractor(p1)
    vals = [v for v in (v0, v1) if v is not None]
    if not vals:
        return None
    return float(max(vals))


# NOTE on query-side extraction: a USER QUERY mentioning TWO DISTINCT unit
# values ("iPhone 15 256GB vs iPhone 15 128GB") names a DIFFERENT basis per
# product — there is NO single user-stated target, so we fall through to the
# pair default_basis. So the query helpers return a value ONLY when the query
# resolves to exactly ONE distinct value (a genuine single stated basis). The
# PRODUCT-side extractors keep "smallest token" semantics (a single listing
# carries one size; range text → conservative basis).
def _all_storage_gb(text: str) -> set:
    out = set()
    for num, unit in _STORAGE_GB_RE.findall(text or ""):
        try:
            v = float(num)
        except (TypeError, ValueError):
            continue
        out.add(v * 1024.0 if unit.lower() == "tb" else v)
    return out


def _single_or_none(values: set) -> Optional[float]:
    """The lone value when `values` has exactly one element, else None (zero →
    no signal; two-or-more → ambiguous per-product bases → defer to default)."""
    return float(next(iter(values))) if len(values) == 1 else None


def _query_storage(query: Optional[str]) -> Optional[float]:
    return _single_or_none(_all_storage_gb(query or ""))


def _query_count(query: Optional[str]) -> Optional[float]:
    counts = {float(n) for n, _u in _COUNT_RE.findall(query or "")}
    return _single_or_none(counts)


def _query_ml(query: Optional[str]) -> Optional[float]:
    sizes = {float(int(s)) for s in extract_sizes_ml(query or "")}
    return _single_or_none(sizes)


def _query_volume_or_weight(query: Optional[str]) -> Optional[float]:
    grams, mls = set(), set()
    for num, unit in _WEIGHT_VOLUME_RE.findall(query or ""):
        try:
            v = float(num)
        except (TypeError, ValueError):
            continue
        u = unit.lower()
        if u == "kg":
            grams.add(v * 1000.0)
        elif u == "g":
            grams.add(v)
        elif u == "l":
            mls.add(v * 1000.0)
        elif u == "ml":
            mls.add(v)
    # Prefer ml when the query mixes both (rare); single-distinct within a base.
    if mls:
        return _single_or_none(mls)
    if grams:
        return _single_or_none(grams)
    return None


def _no_unit_extract(product: Dict[str, Any]) -> None:
    """Fashion/other — no comparable unit, so a product never resolves a value
    (reconcile then passes the pair through untouched)."""
    return None


def _no_target(p0: Dict[str, Any], p1: Dict[str, Any]) -> None:
    return None


def _fragrance_default_basis(p0: Dict[str, Any], p1: Dict[str, Any]) -> Optional[float]:
    """The fragrance query-silent default — DELEGATES to target_pair_size_ml's
    designer-flagship branch verbatim (BOTH designer/niche → 100ml, else None)
    so the fragrance behavior is byte-preserved."""
    return target_pair_size_ml(None, p0, p1)


# Per-category comparable-value TOLERANCE (Rule 4 — "similar values are treated
# as matching, no pend"). A pair whose two resolved values are within the band
# is a FAIR common basis already and passes through (honor_each) without forcing
# a reselect or a pend.
#
#   DISCRETE units (storage GB, unit count) — equal, or within a TIGHT 5% band.
#     128 vs 256 (×2) is a genuine tier gap → mismatch; 60 vs 62 (a "+2 free"
#     pack) or 250 vs 256GB (rounding) → match.
#   CONTINUOUS units (ml, g/weight) — within ±15%. 90ml vs 100ml, a 230g vs 250g
#     jar → "similar" → match; 30ml vs 100ml → mismatch.
#
# The band is fractional, measured against the LARGER of the two values, so it is
# symmetric and scale-free.
_DISCRETE_TOLERANCE = 0.05
_CONTINUOUS_TOLERANCE = 0.15


def values_within_tolerance(
    a: Optional[float], b: Optional[float], spec: Dict[str, Any]
) -> bool:
    """True iff two resolved comparable values are "the same" for fairness under
    `spec`'s per-category tolerance — equal, or within the band relative to the
    larger value. False when either value is None (one side has no signal → not a
    confirmed match). The single divergence-tolerance check used across ALL
    categories (Rule 4)."""
    if a is None or b is None:
        return False
    if a == b:
        return True
    tol = spec.get("tolerance", 0.0) or 0.0
    larger = max(abs(a), abs(b))
    if larger == 0:
        return True
    return abs(a - b) <= tol * larger


# Pair-query separators (case-insensitive). A canonical compare query is "<A> vs
# <B>"; the dual-shape (explicit product_a/product_b) is concatenated to the same
# "A vs B" form upstream (text_routes.py), so splitting here recovers each side.
_PAIR_SPLIT_RE = re.compile(r"\s+(?:vs\.?|versus|v\.?s\.?)\s+|\s*\|\s*", re.I)


def split_pair_query(query: Optional[str]) -> Optional[Tuple[str, str]]:
    """Split a compare query into its two sides on " vs "/" versus "/"|".

    Returns (left, right) ONLY when the query splits cleanly into EXACTLY two
    non-empty halves (a genuine pair query). Returns None otherwise (no separator,
    or 3+ segments — ambiguous) so the caller falls back to whole-query parsing.
    """
    if not query or not isinstance(query, str):
        return None
    parts = [p.strip() for p in _PAIR_SPLIT_RE.split(query)]
    parts = [p for p in parts if p]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None


def user_value_for(query_side: Optional[str], category: Optional[str]) -> Optional[float]:
    """The comparable-unit value the USER stated on ONE side of the query (e.g.
    "iPhone 15 256GB" → 256, "Vitamin D3 120 capsules" → 120, "Dior 50ml" → 50).

    Reads the per-category `user_query_value` parser over the single side, so it
    returns a value ONLY when that side resolves EXACTLY ONE distinct value
    (a genuine single stated basis; an ambiguous "256GB or 512GB" side → None).
    unit=None categories (fashion/other) → always None.

    This is the per-product MENTION parser that powers Rule 1 (both sides
    mentioned → honor each) and the first clause of Rule 2 (one side mentioned →
    target it). It deliberately reads the USER QUERY side, NEVER a product's
    backend-resolved name (a matched listing's appended "30 ML" is NOT a user
    mention).
    """
    spec = fairness_for_category(category)
    if spec["unit"] is None:
        return None
    return spec["user_query_value"](query_side)


CATEGORY_FAIRNESS: Dict[str, Dict[str, Any]] = {
    "electronics": {
        "unit": "GB",
        "extract": _extract_storage,
        "normalize": _identity,
        "user_query_value": _query_storage,
        "default_basis": lambda p0, p1: _resolved_base_default(p0, p1, _extract_storage),
        "label": "storage (GB)",
        # Storage is a DISCRETE tier — 128 vs 256 is a real gap, never "similar".
        # Tight band: a 256 vs 250GB rounding still matches, 128 vs 256 (×2) does
        # not. (See _DISCRETE_TOLERANCE / values_within_tolerance.)
        "tolerance": _DISCRETE_TOLERANCE,
    },
    "fragrances": {
        # REUSE the shipped fragrance machinery verbatim — behavior unchanged.
        "unit": "ml",
        "extract": effective_pair_size_ml,
        "normalize": _identity,
        "user_query_value": _query_ml,
        "default_basis": _fragrance_default_basis,
        "label": "volume (ml)",
        # Continuous ml — 90ml vs 100ml is "similar". (Reconcile for fragrances
        # delegates to reconcile_pair_sizes; the tolerance lives here so
        # target_pair_value reports honor_each on a near-equal ml pair too.)
        "tolerance": _CONTINUOUS_TOLERANCE,
    },
    "supplements": {
        "unit": "count",
        "extract": _extract_count,
        "normalize": _identity,
        "user_query_value": _query_count,
        "default_basis": lambda p0, p1: _resolved_base_default(p0, p1, _extract_count),
        "label": "unit count",
        # Unit count is DISCRETE — 60 vs 62 (a "+2 free" pack) is similar; 60 vs
        # 120 (double) is not.
        "tolerance": _DISCRETE_TOLERANCE,
    },
    "grocery": {
        "unit": "net",
        "extract": _extract_grocery,
        "normalize": _identity,
        "user_query_value": _query_volume_or_weight,
        "default_basis": lambda p0, p1: _resolved_base_default(p0, p1, _extract_grocery),
        "label": "net weight/volume",
        # Continuous weight/volume — a 230g vs 250g jar is similar.
        "tolerance": _CONTINUOUS_TOLERANCE,
    },
    "makeup": {
        "unit": "volume",
        "extract": _extract_volume_or_weight,
        "normalize": _identity,
        "user_query_value": _query_volume_or_weight,
        "default_basis": lambda p0, p1: _resolved_base_default(p0, p1, _extract_volume_or_weight),
        "label": "volume/weight",
        "tolerance": _CONTINUOUS_TOLERANCE,
    },
    "skincare": {
        "unit": "volume",
        "extract": _extract_volume_or_weight,
        "normalize": _identity,
        "user_query_value": _query_volume_or_weight,
        "default_basis": lambda p0, p1: _resolved_base_default(p0, p1, _extract_volume_or_weight),
        "label": "volume/weight",
        "tolerance": _CONTINUOUS_TOLERANCE,
    },
    "haircare": {
        "unit": "volume",
        "extract": _extract_ml_only,
        "normalize": _identity,
        "user_query_value": _query_ml,
        "default_basis": lambda p0, p1: _resolved_base_default(p0, p1, _extract_ml_only),
        "label": "volume (ml)",
        "tolerance": _CONTINUOUS_TOLERANCE,
    },
    "fashion": {
        "unit": None,
        "extract": _no_unit_extract,
        "normalize": _identity,
        "user_query_value": lambda q: None,
        "default_basis": _no_target,
        "label": "—",
        # No comparable axis — tolerance is never consulted (unit is None) but the
        # key is present so the config shape stays uniform.
        "tolerance": _DISCRETE_TOLERANCE,
    },
    "other": {
        "unit": None,
        "extract": _no_unit_extract,
        "normalize": _identity,
        "user_query_value": lambda q: None,
        "default_basis": _no_target,
        "label": "—",
        "tolerance": _DISCRETE_TOLERANCE,
    },
}


def fairness_for_category(category: Optional[str]) -> Dict[str, Any]:
    """The CATEGORY_FAIRNESS spec for `category` (free-form input is
    canonicalized to one of the 9 keys; unknown/None → the unit=None "other"
    spec, so an unrecognized category is safely passed through)."""
    try:
        from app.services.extraction_service import canonicalize_category
        key = canonicalize_category(category)
    except Exception:  # noqa: BLE001 — canonicalizer is best-effort
        key = (category or "").strip().lower()
    return CATEGORY_FAIRNESS.get(key, CATEGORY_FAIRNESS["other"])


# Categories whose values are weight/volume and therefore carry a BASE (ml vs g)
# that must agree before two products are comparable. Maps category → the spec
# keys to inspect for the base.
_BASE_GATED_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "makeup": ("volume", "size"),
    "skincare": ("volume", "size"),
    "grocery": ("size", "net_weight"),
}


def _candidate_value(c: Dict[str, Any], category: str) -> Optional[float]:
    """The comparable-unit value of a RETAINED price candidate for `category`,
    read from its raw_data / own fields (price.size, then title). Returns the
    parsed value or None when the candidate carries no signal on that axis.
    Generalizes _candidate_size_ml to every category's unit."""
    if not isinstance(c, dict):
        return None
    spec = fairness_for_category(category)
    if spec["unit"] is None:
        return None
    # Build a faux-product so the candidate flows through the SAME extractor the
    # product side uses (precedence: title/size carried on raw_data + the
    # candidate). This keeps the candidate axis identical to the product axis.
    raw = c.get("raw_data") if isinstance(c.get("raw_data"), dict) else {}
    faux = {
        "name": raw.get("title") or c.get("title") or "",
        "full_name": raw.get("title") or c.get("title") or "",
        "price": {
            "title": raw.get("title") or c.get("title"),
            "size": raw.get("size") or c.get("size"),
        },
        "variant": raw.get("size") or c.get("size"),
        "specs": {},
    }
    return spec["extract"](faux)


def _candidate_value_set(
    candidates: Optional[List[Dict[str, Any]]], category: Optional[str]
) -> set:
    """The DISTINCT comparable-unit values a product's RETAINED candidates carry
    on this category's axis (e.g. {128.0, 256.0} from a pool with both storages).
    Candidates with no signal on the axis are skipped. Empty set when no pool /
    no signal. Used for fixed-size detection + the largest-common-value
    (common-standard) target."""
    out: set = set()
    for c in candidates or []:
        v = _candidate_value(c, category)
        if v is not None:
            out.add(v)
    return out


def _largest_common_value(
    cands0: Optional[List[Dict[str, Any]]],
    cands1: Optional[List[Dict[str, Any]]],
    category: Optional[str],
) -> Optional[float]:
    """The LARGEST comparable value BOTH products can satisfy from their retained
    candidate pools (Rule 3 — common standard). Falls back to the next-smaller
    shared value implicitly (it is just the max of the intersection). None when
    the pools share no value at all (no common basis)."""
    shared = _candidate_value_set(cands0, category) & _candidate_value_set(cands1, category)
    return float(max(shared)) if shared else None


def target_pair_value(
    user_query: Optional[str],
    p0: Dict[str, Any],
    p1: Dict[str, Any],
    category: Optional[str],
    candidates_by_name: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """The pair-fairness PLAN for `category` — Ahmed's 4-rule target selection.

    Returns a RICH result:
        {
          "mode": "honor_each" | "target" | "none",
          "target": <float | None>,      # the common value, when mode == "target"
          "per_product": {0: <float|None>, 1: <float|None>},  # each side's value
        }

    Rule priority (highest first):
      1. MENTIONED PER PRODUCT → "honor_each". The USER QUERY states a value for
         BOTH products (split "A vs B" / explicit pair, per-product). Keep each
         price at its own value — no force-match, no pend.
      2a. ONE MENTIONED → "target" = that value (reconcile the other to it).
      2b. FIXED-SIZE → one product's retained candidates all share a SINGLE value
          → "target" = that value (the other matches it). Both fixed at DIFFERENT
          single values → "honor_each" (each is genuinely single-size).
      3. NEITHER MENTIONED → "target" = the LARGEST value BOTH candidate pools
         share (common standard); else the category `default_basis` (resolved
         base for exact-match units; designer-flagship 100ml for fragrances).
      4. SIMILAR VALUES → "honor_each". When the two products already resolve
         values within the per-category tolerance (90ml vs 100ml; 60 vs 62 count)
         they are a fair common basis already — pass through, no pend.

    unit=None (fashion/other) → always {"mode": "none", ...}. A weight/volume
    base mismatch (200g vs 50ml) → {"mode": "none", ...} (incomparable, not a
    mismatch to reconcile).
    """
    none_plan = {"mode": "none", "target": None, "per_product": {0: None, 1: None}}
    spec = fairness_for_category(category)
    if spec["unit"] is None:
        return none_plan
    if not isinstance(p0, dict) or not isinstance(p1, dict):
        return none_plan

    canon = _canonical_fairness_key(category)
    # Base gate: for ml/g categories, both products must be on the SAME base.
    base_keys = _BASE_GATED_CATEGORIES.get(canon)
    if base_keys is not None:
        b0 = _unit_base(p0, base_keys)
        b1 = _unit_base(p1, base_keys)
        if b0 is not None and b1 is not None and b0 != b1:
            return none_plan  # weight vs volume — incomparable

    # --- Rule 1 / 2a: per-product MENTIONED values from the USER QUERY ---------
    # Split the canonical "A vs B" (or explicit-pair concatenation) into sides and
    # map side i → product i by order. A non-pair query (no separator / 3+
    # segments) yields a single shared mention instead.
    sides = split_pair_query(user_query)
    if sides is not None:
        m0 = user_value_for(sides[0], category)
        m1 = user_value_for(sides[1], category)
    else:
        shared = user_value_for(user_query, category)
        # Can't attribute a single shared mention to one product → treat as BOTH
        # mentioning the same value only when there genuinely is one (so a bare
        # "256GB" query targets 256 via Rule 2a below; honor_each needs two
        # DISTINCT per-product mentions which a non-split query can't express).
        m0 = m1 = None
        if shared is not None:
            # A shared single value behaves like "one stated basis" → target it.
            return {"mode": "target", "target": shared,
                    "per_product": {0: shared, 1: shared}}

    if m0 is not None and m1 is not None:
        # Rule 1 — both sides mentioned. Honor each (even when equal: reconcile
        # then no-ops on an already-matching pair).
        return {"mode": "honor_each", "target": None,
                "per_product": {0: m0, 1: m1}}
    if m0 is not None or m1 is not None:
        # Rule 2a — exactly one side mentioned → target it.
        target = m0 if m0 is not None else m1
        return {"mode": "target", "target": target,
                "per_product": {0: m0, 1: m1}}

    # --- Rule 2b: fixed-size detection from retained candidate pools -----------
    cbn = candidates_by_name or {}
    n0 = (p0.get("full_name") or p0.get("name") or "") if isinstance(p0, dict) else ""
    n1 = (p1.get("full_name") or p1.get("name") or "") if isinstance(p1, dict) else ""
    cands0 = cbn.get(n0) or cbn.get(p0.get("name") or "")
    cands1 = cbn.get(n1) or cbn.get(p1.get("name") or "")
    vals0 = _candidate_value_set(cands0, category)
    vals1 = _candidate_value_set(cands1, category)
    fixed0 = next(iter(vals0)) if len(vals0) == 1 else None
    fixed1 = next(iter(vals1)) if len(vals1) == 1 else None
    if fixed0 is not None and fixed1 is not None and fixed0 != fixed1:
        # Both genuinely single-size at different values → honor each.
        return {"mode": "honor_each", "target": None,
                "per_product": {0: fixed0, 1: fixed1}}
    if fixed0 is not None and fixed1 is None:
        return {"mode": "target", "target": float(fixed0),
                "per_product": {0: fixed0, 1: None}}
    if fixed1 is not None and fixed0 is None:
        return {"mode": "target", "target": float(fixed1),
                "per_product": {0: None, 1: fixed1}}

    # --- Rule 4: already-fair within tolerance → honor each --------------------
    v0 = spec["extract"](p0)
    v1 = spec["extract"](p1)
    if values_within_tolerance(v0, v1, spec):
        return {"mode": "honor_each", "target": None,
                "per_product": {0: v0, 1: v1}}

    # --- Rule 3: common standard — largest value both candidate pools share ----
    common = _largest_common_value(cands0, cands1, category)
    if common is not None:
        return {"mode": "target", "target": common,
                "per_product": {0: v0, 1: v1}}

    # Fall back to the category default_basis (resolved base / flagship 100ml).
    default = spec["default_basis"](p0, p1)
    if default is not None:
        return {"mode": "target", "target": default,
                "per_product": {0: v0, 1: v1}}
    return {"mode": "none", "target": None, "per_product": {0: v0, 1: v1}}


def _canonical_fairness_key(category: Optional[str]) -> str:
    """Canonical category key (for the base-gate / fragrance-delegation lookups)
    using the same canonicalizer fairness_for_category uses."""
    try:
        from app.services.extraction_service import canonicalize_category
        return canonicalize_category(category)
    except Exception:  # noqa: BLE001
        return (category or "").strip().lower()


def reselect_to_target_value(
    product_name: str,
    candidates: Optional[List[Dict[str, Any]]],
    target: float,
    category: Optional[str],
    currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Re-select a product's price to the comparable-unit `target` from the
    candidates ALREADY fetched this request (NO new network). Generalizes
    reselect_to_target_size to every category.

    For fragrances this DELEGATES to reselect_to_target_size verbatim (identical
    ranking + accuracy guards), so the shipped fragrance behavior is preserved.

    For other unit-bearing categories: picks the best GENUINE candidate (genuine
    -BH ∪ converted_usd, via is_price_showable) whose value == target, ranked
    genuine-BH-authority → variant_rank → cheapest. None when no acceptable
    target candidate exists (→ the caller pends that product). unit=None → None.
    """
    canon = _canonical_fairness_key(category)
    if canon == "fragrances":
        return reselect_to_target_size(product_name, candidates, target, currency=currency)
    spec = fairness_for_category(category)
    if spec["unit"] is None or not candidates:
        return None
    acceptable: List[Dict[str, Any]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        val = _candidate_value(c, category)
        if val is None or val != target:
            continue
        raw = c.get("raw_data") if isinstance(c.get("raw_data"), dict) else None
        price = dict(raw) if raw else None
        if price is None:
            amount = c.get("value")
            if amount is None:
                continue
            price = {
                "amount": amount,
                "currency": currency,
                "source_method": c.get("source_method") or "",
                "retailer": c.get("retailer"),
                "title": c.get("title"),
                "size": c.get("size"),
            }
        else:
            price.setdefault("source_method", c.get("source_method") or "")
            if c.get("source_method"):
                price["source_method"] = c.get("source_method")
        # CORRECTNESS (parity with reselect_to_target_size) — never re-select an
        # OUT-OF-STOCK candidate, and never swap to a wrong model-line VARIANT
        # (S24→S24 FE) just because the comparable-unit `target` matches. Gated by
        # exact_gate_enabled() so a rollback restores legacy behaviour. NOTE: only the
        # VARIANT-QUALIFIER axis is re-checked — the category's fairness unit (storage
        # for electronics, count for supplements, weight for grocery) is the DELIBERATE
        # re-selection target (val == target above), so its axis must NOT be enforced.
        if exact_gate_enabled():
            if c.get("in_stock") is False or price.get("in_stock") is False:
                continue
            _t = c.get("title") or price.get("title") or ""
            _quals = _CATEGORY_VARIANT_QUALIFIERS.get((category or "").lower(), frozenset())
            if _quals and _quals_in(product_name, _quals) != _quals_in(_t, _quals):
                continue
            # CORRECTNESS (coverage review F) — reselect bypassed _selection_match, so a
            # candidate whose comparable-unit MATCHES the target but whose OTHER axes are
            # WRONG (a different %-strength, shade, concentration, supplement type, colour)
            # was shipped. Run the full identity+axis gate, but with the category's
            # FAIRNESS-UNIT measure stripped from BOTH sides (the unit value IS the
            # deliberate re-selection target — `val == target` above — so its axis must
            # NOT be enforced here; every NON-unit axis still gates).
            if _t:
                _pn_nounit = _IDENTITY_MEASURE_STRIP_RE.sub(" ", product_name or "")
                _t_nounit = _IDENTITY_MEASURE_STRIP_RE.sub(" ", _t)
                if not _selection_match(_pn_nounit, _t_nounit, category,
                                        candidate_brand=c.get("brand") or ""):
                    continue
        # The canonical showable predicate — genuine/converted ∪ the
        # is_implausible_* accuracy guards. A re-selected price must survive the
        # same downstream gate.
        if not is_price_showable(product_name, price):
            continue
        acceptable.append({"_cand": c, "_price": price})

    if not acceptable:
        return None
    best = max(
        acceptable,
        key=lambda a: (
            1 if _is_genuine_bh_candidate(a["_cand"]) else 0,
            float(a["_cand"].get("variant_rank", 0) or 0),
            -float(a["_price"].get("amount", 0) or 0),
        ),
    )
    return best["_price"]


def _mark_unit_pending(*products: Dict[str, Any]) -> None:
    """Mark each product price-pending with the GENERAL reason="unit_mismatch"
    (the category-general analogue of _mark_size_pending's "size_mismatch").
    Preserves the product's own size annotation for FE context, nulls
    best_price/retailer. The FE renders any price.unavailable the same way."""
    for p in products:
        if not isinstance(p, dict):
            continue
        price = p.get("price") if isinstance(p.get("price"), dict) else {}
        p["price"] = make_pending_price(
            currency=price.get("currency") or "BHD",
            reason="unit_mismatch",
            size=price.get("size"),
        )
        if "best_price" in p:
            p["best_price"] = None
        if "retailer" in p:
            p["retailer"] = None


def reconcile_pair_fairness(
    product_data: List[Dict[str, Any]],
    user_query: Optional[str],
    category: Optional[str],
    candidates_by_name: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> bool:
    """CATEGORY-AWARE pair-level fairness reconciliation — the general form of
    reconcile_pair_sizes. Drives off the `target_pair_value` PLAN (Ahmed's 4-rule
    target selection):

      • mode "honor_each" → the USER mentioned a value for BOTH products (Rule 1)
        OR the pair already sits at similar/single-size values (Rule 4 tolerance
        / Rule 2b both-fixed). Leave BOTH prices exactly as they are — NO
        re-select, NO pend. The verdict's like-for-like rule flags any tier
        difference (e.g. "iPhone 256GB vs Galaxy 128GB" → both shown).
      • mode "target" → a single common value (Rule 2a one-mentioned / Rule 2b
        one-fixed / Rule 3 common-standard). Each product is RE-SELECTED to that
        value from candidates already fetched this request (no new network):
          1. BOTH reach the target → show BOTH.
          2. Only ONE reaches it → show that one, pend ONLY the other
             (reason="unit_mismatch"). A side already WITHIN tolerance of the
             target counts as at-target (no false pend).
          3. NEITHER reaches it → BOTH pending.
      • mode "none" → no comparable axis / incomparable base → pass through.

    FRAGRANCES delegate to reconcile_pair_sizes verbatim — the shipped fragrance
    behavior (flagship-100ml target, size_mismatch reason, all three outcomes)
    is byte-preserved.

    unit=None (fashion/other) → pass through untouched (returns False).

    Pure + in-place (apart from candidate-driven price swaps). Returns True iff
    it changed any price (a swap OR a pend). No network, no latency. No-ops when
    either price is missing/non-positive (a pending side already kills any cross-
    basis delta).
    """
    if not isinstance(product_data, list) or len(product_data) < 2:
        return False

    canon = _canonical_fairness_key(category)
    # FRAGRANCES — delegate to the shipped reconcile. The orchestrator has already
    # resolved the pair category to fragrances, so an UNSIZED product here IS a
    # fragrance — pass the frag-reconcile fix flag so a size-silent genuine pair
    # defaults to the flagship 100ml basis even when its house is not in the
    # brand-keyword list (flag OFF -> byte-identical to the frozen behavior).
    if canon == "fragrances":
        return reconcile_pair_sizes(
            product_data, user_query=user_query,
            candidates_by_name=candidates_by_name,
            treat_unsized_as_flagship=frag_reconcile_fix_enabled(),
        )

    spec = fairness_for_category(category)
    if spec["unit"] is None:
        return False  # no comparable axis — never touch the pair

    p0, p1 = product_data[0], product_data[1]
    price0 = p0.get("price") if isinstance(p0, dict) else None
    price1 = p1.get("price") if isinstance(p1, dict) else None
    if not isinstance(price0, dict) or not isinstance(price1, dict):
        return False
    amt0, amt1 = price0.get("amount"), price1.get("amount")
    if not (isinstance(amt0, (int, float)) and amt0 > 0):
        return False
    if not (isinstance(amt1, (int, float)) and amt1 > 0):
        return False

    # Fairness fix (2026-07-07) — mirror of the reconcile_pair_sizes guard for the
    # NON-fragrance categories: an estimate side is not a comparable displayed price,
    # so it must not pend the pair's genuine, showable price. Flag-OFF byte-identical.
    if _fairness_ignore_estimate_enabled() and (
        _is_estimate_price(price0) or _is_estimate_price(price1)
    ):
        return False

    extract = spec["extract"]
    candidates_by_name = candidates_by_name or {}

    plan = target_pair_value(
        user_query, p0, p1, category, candidates_by_name=candidates_by_name
    )
    mode = plan.get("mode")

    # Rule 1 / 4 / 2b-both-fixed — honor each: leave BOTH prices untouched.
    if mode == "honor_each":
        return False

    # mode "none" — no derivable common basis. Pend BOTH only on a genuine
    # off-axis divergence (both resolve DIFFERENT, non-tolerant values); otherwise
    # leave the pair alone (one/both unknown, or within tolerance → no false
    # mismatch).
    if mode != "target":
        v0 = extract(p0)
        v1 = extract(p1)
        if (v0 is not None and v1 is not None
                and not values_within_tolerance(v0, v1, spec)):
            _mark_unit_pending(p0, p1)
            return True
        return False

    target = plan.get("target")
    if target is None:  # defensive — a "target" plan always carries a value
        return False

    changed = False

    def _resolve_to_target(p: Dict[str, Any]) -> bool:
        """True iff `p` ends up at (or within tolerance of) the target. Re-selects
        from retained candidates when off-target; mutates p['price'] on a swap."""
        nonlocal changed
        cur = extract(p)
        # A value already within the per-category tolerance of the target is a
        # fair basis — never re-select or pend it (Rule 4 applied to the target).
        if cur is not None and values_within_tolerance(cur, target, spec):
            return True
        if cur == target:
            return True
        name = p.get("full_name") or p.get("name") or ""
        cands = candidates_by_name.get(name) or candidates_by_name.get(p.get("name") or "")
        new_price = reselect_to_target_value(
            name, cands, target, category,
            currency=(p.get("price") or {}).get("currency") or "BHD",
        )
        if new_price is None:
            return False
        p["price"] = new_price
        amount = new_price.get("amount")
        if "best_price" in p:
            p["best_price"] = amount
        if "retailer" in p:
            p["retailer"] = new_price.get("retailer")
        changed = True
        return True

    at0 = _resolve_to_target(p0)
    at1 = _resolve_to_target(p1)

    if at0 and at1:
        return changed
    if at0 and not at1:
        _mark_unit_pending(p1)
        return True
    if at1 and not at0:
        _mark_unit_pending(p0)
        return True
    _mark_unit_pending(p0, p1)
    return True


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


# Apostrophes INSIDE words (ASCII ' + the typographic U+2018/U+2019 retailers emit)
# fold away before tokenizing so the possessive/elision spelling a retailer title
# carries compares equal to the bare query form ("Levi's"=="Levis", "'07"=="07",
# "Men's"=="Mens") — the edge-strip in normalize_words never reached an internal
# apostrophe, which survived as a token mismatch rejecting the EXACT product
# (KPI fash-001/003 gate repro 2026-07-02). Shared by normalize_words AND
# strict_title_match (which tokenizes raw, without normalize_words).
_APOSTROPHES_RE = re.compile("['‘’]")

# SPACED-UNIT fold (Wave B-FIX BF3, over-rejection sweep OR-1..OR-3) — join a
# digit token with an immediately-following bare unit token so the spaced
# retailer spelling tokenizes IDENTICALLY to the glued query form
# ("256 GB"=="256GB", "11 INCH"=="11-inch"->"11inch", "90 ml"=="90ml",
# "12 GB RAM"). Real extra.com/unbxd titles space every unit and were rejected
# by strict_title_match's raw substring check on the EXACT in-stock SKU.
# The unit vocabulary is BOUNDED to the units the existing size/storage/inch
# regexes already parse in BOTH spellings (their patterns all use \s*):
# gb|tb (_STORAGE_GB_RE), ml (_SIZE_ML_RE), oz (_SIZE_OZ_RE), inch(es)
# (_INCH_RE), + the electronics spec units mm/hz/mah — so the fold can never
# weaken an axis: a folded "512 GB" hits _storage_mismatch exactly like
# "512GB". DELIBERATELY EXCLUDED: "w" ("AF1 '07 W" is the Nike women's
# suffix), "l" (clothing size / jeans length), and the supplement/grocery
# weight-strength units g/kg/lb/mg/mcg/iu — their axes (_STRENGTH_RE /
# _WEIGHT_VOLUME_RE) already parse both spellings, folding buys nothing at
# strict for those categories, and the legacy iHerb overlap matcher pins
# {"1000", "iu"} as SEPARATE tokens (folding rewrote that contract).
# GATED on exact_gate_enabled() at the call sites (the Wave-B1
# candidate_brand-fold precedent) so the ENABLE_EXACT_PRICE_GATE rollback
# surface keeps the raw pre-fold tokenization byte-for-byte.
_SPACED_UNIT_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)[ \t]+(gb|tb|ml|oz|mm|hz|mah|inch(?:es)?)\b",
    re.I,
)


def _fold_spaced_units(text: str) -> str:
    """Join '<digits> <unit>' into one token (see the vocabulary note above).
    Case is preserved — callers lowercase downstream. No-op on empty input."""
    if not text:
        return text or ""
    return _SPACED_UNIT_RE.sub(lambda m: m.group(1) + m.group(2), text)


# Wave C (re-sweep RS8) — a digit-bearing UNIT-shaped query token ("5ml",
# "8gb", "256gb", "11inch"; the _SPACED_UNIT_RE vocabulary) must match the
# title on a token BOUNDARY, not as a raw substring: the spaced-unit fold
# widened strict's per-word substring acceptance ("5ml" in the folded
# "75 ml"->"75ml", "8gb" in "128 GB"->"128gb") on strict-ONLY surfaces (the
# sitemap JSON-LD discovery chain has no _selection_match after strict).
_STRICT_UNIT_TOKEN_RE = re.compile(
    r"^\d+(?:\.\d+)?(?:gb|tb|ml|oz|mm|hz|mah|inch(?:es)?)$",
)


def _strict_word_present(word: str, title_normalized: str) -> bool:
    """strict_title_match per-word presence: substring for ordinary words
    (unchanged), token-boundary equality for unit-shaped digit tokens (RS8).
    The boundary excludes [a-z0-9.] on the left ('.' so "5ml" never matches
    inside a decimal "13.5ml") and [a-z0-9] on the right."""
    if not _STRICT_UNIT_TOKEN_RE.match(word):
        return word in title_normalized
    return re.search(
        r"(?<![a-z0-9.])" + re.escape(word) + r"(?![a-z0-9])",
        title_normalized,
    ) is not None


def normalize_words(text: str) -> set:
    """Normalize words for matching."""
    text = _APOSTROPHES_RE.sub("", text)
    if exact_gate_enabled():
        text = _fold_spaced_units(text)
    return set(w.replace("-", "").strip(",.()&:;'\"") for w in text.lower().split() if w.strip(",.()&:;'\""))


def numbers_match(product_name: str, title: str) -> bool:
    """Check that significant numbers in product name appear in title."""
    product_numbers = set(re.findall(r'\b(\d{2,})\b', product_name))
    if not product_numbers:
        return True
    title_numbers = set(re.findall(r'\b(\d{2,})\b', title))
    return bool(product_numbers & title_numbers)


def _collapse_concentration(text: str) -> str:
    """Replace any spelled-out fragrance concentration phrase with its canonical
    token (e.g. "eau de toilette" -> "edt", "eau de parfum" -> "edp") so the
    word-presence matcher treats abbreviation variants as equal. Defined once and
    reused by `strict_title_match`; `_CONCENTRATION_PATTERNS` is module-level and
    fully bound by call time. No-op on text without a concentration phrase."""
    if not text:
        return text or ""
    out = text
    for pat, label in _CONCENTRATION_PATTERNS:
        out = pat.sub(label, out)
    return out


def normalize_candidate_brand(raw) -> str:
    """Best-effort brand STRING from a heterogeneous adapter brand field.

    The price adapters carry the product's own brand in different shapes: a scalar
    string (unbxd brandEn, beautybooth brand), a ``{"name": ...}`` dict (salla,
    panda, woo brands[]/pa_brand terms), a list of either, or JSON null. This
    normalizes all of them to a plain trimmed string ("" when unknown/absent).

    Robustness contract (brand-implied review 2026-07-07): NEVER raises and never
    stringifies a container into junk tokens — a bare-string `brand` (salla can
    return `"Ajmal"`, not `{"name": ...}`) no longer AttributeErrors, and a dict/
    list slipped into a scalar field yields its name/first-element instead of
    ``"{'id': 1, ...}"``. Unknown shapes → "" → legacy brand-required behaviour."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, (list, tuple)):
        return normalize_candidate_brand(raw[0]) if raw else ""
    return ""


def strict_title_match(
    product_name: str, title: str, candidate_brand: str = "",
) -> bool:
    """Key words from the product name must appear in the shopping title.

    Concentration-aware: a designer-fragrance PDP often spells the concentration
    differently than the query ("Eau de Toilette" vs "EDT"). Both sides are
    normalized via the same `_CONCENTRATION_PATTERNS` map BEFORE the word-presence
    loop, so abbreviation variants compare equal — e.g. the query
    "Dior Sauvage Eau de Toilette 100ml" now matches the genuine alhajis PDP
    "Dior Sauvage Edt M 100Ml" (both collapse to the "edt" token). No-fab is
    preserved: a DIFFERENT concentration ("Eau de Parfum" vs "EDT") still fails,
    because the labels differ.

    `candidate_brand` (genuine-BH coverage) — a BH retailer lists a device by its
    MODEL LINE ("iPad Air M2 128GB", no "Apple"), so requiring the query's brand
    word literally rejected the exact-SKU PDP (MANUFACTURER_BRAND_WORDS only
    exempts chip vendors). When the CANDIDATE's own brand matches the query brand,
    drop ONLY that brand's tokens from the required set — so a correct model-line
    PDP passes, while a WRONG-brand candidate keeps the query brand required and
    still rejects. This is BACKED by _selection_match (run alongside every caller),
    which strips candidate_brand + vets the full SKU, so the brand is never
    unverified. Empty candidate_brand → legacy behaviour (brand required)."""
    if is_counterfeit_listing(title):
        return False
    # Apostrophe fold on BOTH sides (this matcher tokenizes raw, so the shared
    # normalize_words fold never reaches it): "levis" must substring-match a
    # "Levi's 501" title however the retailer typed the quote.
    product_name = _APOSTROPHES_RE.sub("", _collapse_concentration(product_name))
    title = _APOSTROPHES_RE.sub("", _collapse_concentration(title))
    # Spaced-unit fold on BOTH sides (BF3, sweep OR-1/OR-3): the query's glued
    # "256GB"/"11inch"/"90ml" must substring-match the spaced retailer spelling
    # ("256 GB", "11 INCH", "90 ml"). Pure alias — a DIFFERENT unit value still
    # fails the substring check, and the numeric axes parse both spellings.
    # Gate-OFF keeps the raw pre-fold tokenization (rollback surface).
    if exact_gate_enabled():
        product_name = _fold_spaced_units(product_name)
        title = _fold_spaced_units(title)
    title_normalized = title.lower().replace("-", "")
    # Tokens of the candidate's OWN brand — dropped from the required query words
    # only when the candidate actually carries that brand (so a Samsung candidate
    # never lets an "apple" query word be skipped). Apostrophe-folded like BOTH
    # text sides above (Wave B review MED): a retailer brand label spelled
    # "Levi's"/"L'Oreal" must equal the folded query token ("levis"/"loreal") to
    # release it — unfolded, the brand-omitting titles the candidate_brand path
    # exists to recover kept rejecting.
    brand_toks = {
        b for b in _APOSTROPHES_RE.sub("", candidate_brand or "")
        .lower().replace("-", "").split()
        if len(b) > 2
    } if exact_gate_enabled() else set()
    key_words = [
        w.replace("-", "") for w in product_name.lower().split()
        if len(w.replace("-", "")) > 2
        and w.replace("-", "") not in MANUFACTURER_BRAND_WORDS
        and w.replace("-", "") not in brand_toks
    ]
    # RS8 — unit-shaped digit tokens need a token BOUNDARY ("5ml" must not
    # substring-match the folded "75ml"). Gate-scoped like the fold itself so
    # the rollback surface keeps the raw substring check byte-for-byte.
    if exact_gate_enabled():
        return all(_strict_word_present(w, title_normalized) for w in key_words)
    return all(w in title_normalized for w in key_words)


# S3 #1 (discovery-match) — model-line variant qualifiers. A base-model query
# ("iPhone 15") strict-matches a HIGHER variant ("iPhone 15 Pro Max") because
# the base name is a prefix of the variant — so the wrong, pricier SKU's PDP can
# be attributed to the query (the iPhone16->14 wrong-product class, inverted).
# These tokens DISTINGUISH SKUs within a model line; variant_mismatch rejects a
# candidate whose qualifier set differs from the query's.
_VARIANT_QUALIFIERS = frozenset({
    "pro", "max", "plus", "ultra", "mini", "air", "promax",
})


def _size_qualifiers(text: str) -> set:
    """Size discriminators present in `text` (e.g. {'13', '15'} from '13-inch',
    '15"', or a bare laptop-range '13'). A size in the QUERY constrains the SKU;
    a size only in the title (query unspecified) does not."""
    t = text.lower()
    sizes = set()
    # N-inch / N inch / N"  → the screen size number (explicit)
    for m in re.findall(r'(\d{2})\s*(?:-?\s*inch|")', t):
        sizes.add(m)
    # A bare 2-digit number in the laptop/tablet screen range (11-17") is also a
    # size discriminator ("MacBook Air 13 M3"). Conservative range avoids model
    # numbers (15/16/17 phones are caught by numbers_match separately; here we
    # only add 11-17 which are the common screen inches).
    for m in re.findall(r'\b(1[1-7])\b', t):
        sizes.add(m)
    return sizes


def variant_mismatch(product_name: str, title: str) -> bool:
    """True iff `title` is a DIFFERENT model-line variant than `product_name`
    (so its price must NOT be attributed to the query).

    Logic:
      - model-line qualifiers (pro/max/plus/ultra/mini/air): the SET present in
        the query must equal the set present in the title. A qualifier in the
        title-but-not-query ("Pro Max" when query is base) OR query-but-not-title
        ("iPhone 15 Pro" when title is base) → mismatch.
      - size qualifiers (13-inch/15-inch): only enforced when the QUERY specifies
        a size — then the title's size, if any, must include it. A size only in
        the title (query unspecified) is allowed (query didn't constrain it).

    Never raises. Returns False (no mismatch) when neither side carries a
    discriminating qualifier — the brand/number matchers handle the rest.
    """
    q = (product_name or "").lower()
    t = (title or "").lower()
    # Normalize "pro max" -> token set membership: treat the two-word "pro max"
    # by checking each word; "promax" is also in the set for safety.
    q_words = set(re.findall(r"[a-z]+", q))
    t_words = set(re.findall(r"[a-z]+", t))
    q_quals = q_words & _VARIANT_QUALIFIERS
    t_quals = t_words & _VARIANT_QUALIFIERS
    if q_quals != t_quals:
        return True
    # Size: only when the query constrains it.
    q_sizes = _size_qualifiers(q)
    if q_sizes:
        t_sizes = _size_qualifiers(t)
        if t_sizes and not (q_sizes & t_sizes):
            return True
    return False


# ============================================================================
# WS5 (Genuine-BH latency+warmer bundle) — variant/concentration precision.
# A fragrance PDP differs by CONCENTRATION (EDP/EDT/Parfum/EDC) and SIZE (ml).
# The trace pair mis-compared a 118-BHD 100ml-class Ounass listing vs a 72-BHD
# 30ml Sephora listing (a size mismatch — not a like-for-like price). These
# helpers parse the two axes so the candidate scorer can (a) prefer the listing
# matching a query's STATED size/concentration and (b) — when the query is
# unspecified — let the orchestrator pick a basis CONSISTENT across both products.
# Annotated onto the price dict as price.size / price.concentration.
# ============================================================================

# Canonical concentration tokens -> normalized label. Order matters: the longer
# / more-specific phrases are checked first ("eau de parfum" before "parfum").
_CONCENTRATION_PATTERNS = (
    (re.compile(r"\bextrait(?:\s+de\s+parfum)?\b", re.I), "Extrait"),
    (re.compile(r"\bparfum\s+intense\b", re.I), "Parfum Intense"),
    (re.compile(r"\beau\s+de\s+parfum\b|\bedp\b", re.I), "EDP"),
    (re.compile(r"\beau\s+de\s+toilette\b|\bedt\b", re.I), "EDT"),
    (re.compile(r"\beau\s+de\s+cologne\b|\bedc\b", re.I), "EDC"),
    (re.compile(r"\beau\s+fraiche\b", re.I), "Eau Fraiche"),
    # bare "parfum" / "perfume" LAST (most generic; EDP/EDT already consumed).
    (re.compile(r"\bparfum\b", re.I), "Parfum"),
)
# Size in millilitres: "100ml", "100 ml", "100-ml", "3.4 oz" -> ml is NOT
# converted (oz left as-is in a separate axis would over-complicate); we capture
# the ml integer. A bare "100" is NOT a size (too ambiguous) — ml unit required.
_SIZE_ML_RE = re.compile(r"(\d{1,4})\s*(?:-?\s*)ml\b", re.I)


def extract_concentration(text: str) -> Optional[str]:
    """Normalized fragrance concentration label in `text` (EDP/EDT/Parfum/...),
    or None when none is present. First (most-specific) match wins."""
    if not text:
        return None
    for pat, label in _CONCENTRATION_PATTERNS:
        if pat.search(text):
            return label
    return None


def extract_sizes_ml(text: str) -> set:
    """Set of millilitre sizes in `text` (e.g. {'50', '100'} from '50ml / 100ml').
    Empty set when no `\\d+ml` token is present. Returned as strings to match the
    `_size_qualifiers` style."""
    if not text:
        return set()
    return {m for m in _SIZE_ML_RE.findall(text)}


# Fluid-ounce size, e.g. "3.4 oz", "1.7 fl oz", "1oz". Fragrances are very often
# labelled in oz on brand/PDP names/titles ("3.4 oz" = the flagship 100ml), so a
# size-capture that ignored oz would miss the genuine size on those listings.
_SIZE_OZ_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:fl\.?\s*)?oz\b", re.I)
# 1 US fluid ounce ≈ 29.5735 ml.
_ML_PER_FL_OZ = 29.5735
# Standard retail fragrance bottle sizes (ml). Perfume oz labels are CONVENTIONAL
# round-bottle markers, not exact conversions: a "3.4 oz" bottle is sold as 100ml
# (raw 3.4*29.5735 = 100.55), "1.7 oz" as 50ml, "1 oz" as 30ml, "6.7/6.8 oz" as
# 200ml. So an oz→ml conversion is SNAPPED to the nearest standard size — the
# size the bottle is actually retailed at — rather than a raw decimal.
_STANDARD_FRAGRANCE_SIZES_ML = (5, 10, 15, 30, 50, 75, 100, 125, 150, 200, 250)


def _snap_to_standard_fragrance_size(ml: float) -> int:
    """Snap a (possibly raw-converted) ml value to the nearest standard retail
    fragrance bottle size, so "3.4 oz" (100.55 raw) resolves to the 100ml it is
    sold as. The snap window is ±12% of the value (wide enough to absorb the
    oz-rounding slack, tight enough not to swallow a genuinely off-standard
    size); outside any window the rounded raw value is kept."""
    nearest = min(_STANDARD_FRAGRANCE_SIZES_ML, key=lambda s: abs(s - ml))
    if abs(nearest - ml) <= 0.12 * ml:
        return nearest
    return int(round(ml))


def extract_size_ml_any(text: Optional[str]) -> Optional[int]:
    """The size in MILLILITRES parsed from `text`, recognising BOTH ml and fl-oz
    tokens. ml tokens are taken verbatim; oz tokens are converted
    (``_ML_PER_FL_OZ``) and SNAPPED to the nearest standard fragrance bottle size
    (so "3.4 oz" → 100, not 101). Returns the SMALLEST size found across all
    tokens (the conservative basis when a title carries several, e.g. range text
    "30ml / 50ml / 100ml" → 30), or None when no ml/oz token is present.

    This is the size-CAPTURE primitive (it produces a single int we then store as
    an "<n>ml" string on ``price.size``). It deliberately reuses ``_SIZE_ML_RE``
    so the ml semantics stay in lockstep with ``extract_sizes_ml``; the oz axis
    is added on top so a JSON-LD/PDP name like "...Eau de Parfum 3.4 oz"
    resolves to the flagship 100. A bare number (no unit) is NOT a size."""
    if not text:
        return None
    sizes_ml: List[int] = [int(m) for m in _SIZE_ML_RE.findall(text)]
    for oz_str in _SIZE_OZ_RE.findall(text):
        try:
            sizes_ml.append(_snap_to_standard_fragrance_size(float(oz_str) * _ML_PER_FL_OZ))
        except (ValueError, TypeError):
            continue
    if not sizes_ml:
        return None
    return min(sizes_ml)


# ---------------------------------------------------------------------------
# Category-fairness unit extractors (CATEGORY_FAIRNESS, Part 1).
#
# Each parses a SINGLE comparable axis off a free-text field. Like
# extract_sizes_ml they are pure + return None when no token is present, so a
# product with no signal on that axis never trips a false mismatch. They power
# the per-category `extract`/`user_query_value` callables in CATEGORY_FAIRNESS.
# ---------------------------------------------------------------------------

# Storage: "256GB", "256 GB", "1TB", "1 TB". TB is normalized to GB (×1024) so
# a 1TB laptop and a 512GB laptop compare on ONE axis. A bare integer is NOT
# storage (too ambiguous) — the GB/TB unit is required.
_STORAGE_GB_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(tb|gb)\b", re.I)

# Unit count: "60 capsules", "120 tablets", "90 softgels", "30 count",
# "60 caps", "90 gummies". The count is the integer immediately before the
# unit word. Used by supplements (caps/tablets/softgels) and grocery packs.
_COUNT_RE = re.compile(
    r"(\d+)\s*(?:x\s*)?"
    # optional "veg/vegetable/veggie/plant" qualifier before the unit so a NOW/iHerb
    # "180 Veg Capsules" parses the count (coverage review) instead of leaking "180".
    r"(?:(?:veg(?:etable|gie)?|plant)\s+)?"
    r"(capsules?|caps|tablets?|tabs|softgels?|gummies|gummy|count|ct|pieces?|pcs|sachets?)\b",
    re.I,
)

# Net weight/volume: "200g", "5kg", "1L", "500ml", "1.5l", "250 g". Normalized
# to a base unit: grams (g/kg→g) and millilitres (ml/L→ml) are SEPARATE bases,
# so a 200g jar and a 250g jar compare while a 200g vs 500ml pair stays
# incomparable (different base → None target). Returns (value, base) where base
# is "g" or "ml", or None when no weight/volume token is present.
_WEIGHT_VOLUME_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l|lbs?|pounds?)\b", re.I)

# A bare cellular-GENERATION token — "5G"/"4G"/"3G"/"2G" — is a NETWORK generation on
# a phone/tablet/router, NOT a "5 gram" net weight. In ELECTRONICS context it must be
# excluded from weight parsing so a phone's base query ("Galaxy S24 FE") and its genuine
# "…5G" PDP title hash to ONE size token / price cache key (the warmer's warm-vs-live
# parity). This is consistent with the codebase's documented stance that 5G is noise, not
# a discriminator (see _ELECTRONICS_QUALIFIERS, which deliberately omits "5g").
# Bounded to 2-5 (the real cellular generations); "5GB" is UNAFFECTED (the trailing B
# blocks the \bG\b boundary). CATEGORY-SCOPED by the caller — a supplement/grocery "5G"/
# "10G" is a genuine gram weight, so a category-blind strip would FALSE-MERGE
# "Creatine 5G" == "Creatine 10G" (a strictly-worse wrong-SKU cache serve).
_CELLULAR_GEN_RE = re.compile(r"\b[2-5]G\b", re.I)


def _strip_cellular_generation(text: str, category: Optional[str]) -> str:
    """Remove bare cellular-generation tokens (see `_CELLULAR_GEN_RE`) from `text` when
    the resolved category is ELECTRONICS and the exact-price gate is ON.

    Category resolution reuses `_resolve_extractor_category` (explicit arg > the
    orchestrator per-task ContextVar > best-effort inference; "other" is re-inferred),
    so an LLM-mislabelled "other" phone still collapses while a supplement/grocery text
    resolves to its own category (the cosmetic/supplement/grocery detectors run BEFORE
    electronics) and its gram weight is preserved. Non-electronics / unresolved text is
    returned unchanged — the SAFE direction (never a false gram-weight merge).

    CRITICAL: the INFERENCE fallback runs on the CELLULAR-STRIPPED text, never the raw
    text. `is_electronics_query`'s brand+digit rule would otherwise be satisfied by the
    "3" of a bare "3G" on a food that merely shares an electronics BRAND whole-token
    ("Apple Sauce 3G", "Nothing Bundt Cake 2G") — self-promoting it to electronics and
    false-merging its genuine gram sizes (coverage review R2). Inferring on the stripped
    text removes that digit, so only text with a REAL device/model signal resolves to
    electronics ("Galaxy S24 FE" stays electronics via "Galaxy"/"S24").

    Gated on `exact_gate_enabled()` so with the gate OFF the strip is a no-op and the
    legacy cache namespace stays BYTE-IDENTICAL to b207bfa (a rollback must not orphan
    the warmed cache)."""
    if not text or not exact_gate_enabled():
        return text
    stripped = _CELLULAR_GEN_RE.sub(" ", text)
    if stripped == text:
        return text  # no cellular token present — skip category resolution entirely
    cat = _resolve_extractor_category(category, stripped)
    if (cat or "").lower() == "electronics":
        return stripped
    return text


def extract_storage_gb(text: str) -> Optional[float]:
    """Smallest storage size in `text`, in GB (TB→GB ×1024). None when no
    GB/TB token is present. Smallest is the conservative basis when a listing
    title mentions several capacities."""
    if not text:
        return None
    vals: List[float] = []
    for num, unit in _STORAGE_GB_RE.findall(text):
        try:
            v = float(num)
        except (TypeError, ValueError):
            continue
        if unit.lower() == "tb":
            v *= 1024.0
        vals.append(v)
    return min(vals) if vals else None


def extract_count(text: str) -> Optional[float]:
    """Unit count in `text` (caps/tablets/softgels/gummies/pieces/...), or None.
    Largest token wins — a "60+60 free" pack reads the bottle's headline count;
    when a single token appears it is returned as-is."""
    if not text:
        return None
    vals: List[float] = []
    for num, _unit in _COUNT_RE.findall(text):
        try:
            vals.append(float(num))
        except (TypeError, ValueError):
            continue
    return max(vals) if vals else None


def extract_weight_or_volume(
    text: str, category: Optional[str] = None
) -> Optional[Tuple[float, str]]:
    """(value, base) net weight/volume in `text` — grams (g/kg→g) OR millilitres
    (ml/L→ml), whichever token appears. None when neither is present. Smallest
    matching token of the FIRST base seen wins (a single listing carries one
    pack size). Grams and ml are distinct bases — the caller must only compare
    same-base values, so a weight vs a volume never trips a false match.

    `category` (optional): in ELECTRONICS context a bare cellular-generation token
    ("5G"/"4G"/…) is a network generation, NOT a gram weight, so it is excluded
    (see `_strip_cellular_generation`). Defaults to the orchestrator per-task
    ContextVar when omitted; supplement/grocery gram parsing is untouched."""
    if not text:
        return None
    text = _strip_cellular_generation(text, category)
    grams: List[float] = []
    mls: List[float] = []
    for num, unit in _WEIGHT_VOLUME_RE.findall(text):
        try:
            v = float(num)
        except (TypeError, ValueError):
            continue
        u = unit.lower()
        if u == "kg":
            grams.append(v * 1000.0)
        elif u == "g":
            grams.append(v)
        elif u == "l":
            mls.append(v * 1000.0)
        elif u == "ml":
            mls.append(v)
    # Prefer ml when both appear (a "200g (≈210ml)" oddity is rare; ml is the
    # dominant cosmetics/grocery-liquid axis). Within a base, smallest is the
    # conservative basis.
    if mls:
        return (min(mls), "ml")
    if grams:
        return (min(grams), "g")
    return None


# A union of every size/storage/count token the extractors recognize — used to
# STRIP the size out of name/variant before hashing the size-agnostic base key
# (build_size_aware_price_cache_key). Mirrors _STORAGE_GB_RE / _SIZE_ML_RE /
# _WEIGHT_VOLUME_RE / _COUNT_RE so the strip is exhaustive.
_SIZE_STRIP_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*"
    r"(?:tb|gb|ml|l|kg|g|"
    r"capsules?|caps|tablets?|tabs|softgels?|gummies|gummy|count|ct|pieces?|pcs|sachets?)\b",
    re.I,
)


def size_variant_token(text: Optional[str], category: Optional[str] = None) -> str:
    """A stable normalized size/variant token for a product identity string, or
    "" when no size is present (Faithful-Results Task 1.4).

    Reuses the SAME unit extractors `CATEGORY_FAIRNESS` uses, so the cache-key
    notion of "size" matches the fairness notion of "comparable unit". Fixed
    precedence (so a single product yields one deterministic token):
      storage GB > fragrance/volume ml > supplement count > weight g.
    TB is normalized to GB and L to ml by the underlying extractors, so "1TB"
    and "1024GB" (or "1L" and "1000ml") collapse to one token. Numbers are
    rendered without a trailing ".0" so "256GB" → "256gb" (not "256.0gb").

    The point: two SIZE variants of the same product (iPhone 256GB vs 128GB,
    Aventus 50ml vs 100ml) get DISTINCT tokens → distinct cache keys; two
    listings of the SAME size get the SAME token → cache hits preserved.
    """
    if not text or not isinstance(text, str):
        return ""

    def _fmt(v: float) -> str:
        # 256.0 -> "256", 1.5 -> "1.5"
        return str(int(v)) if float(v).is_integer() else str(v)

    gb = extract_storage_gb(text)
    if gb:
        return f"{_fmt(gb)}gb"
    ml = extract_size_ml_any(text)
    if ml:
        return f"{_fmt(ml)}ml"
    count = extract_count(text)
    if count:
        return f"{_fmt(count)}ct"
    # `category` is threaded ONLY into the weight branch — it is the only axis where a
    # cellular-generation token ("5G") could be mis-read as grams (electronics context).
    wv = extract_weight_or_volume(text, category)
    if wv:
        value, base = wv
        return f"{_fmt(value)}{base}"
    return ""


# ============================================================================
# GENUINE-PRICE CORRECTNESS — shared exact-identity gate + authority selector +
# availability policy.  Spec: docs/plans/2026-06-27-genuine-price-correctness-IMPL-SPEC.md
#
# CARDINAL RULE: select a price ONLY when the candidate is the EXACT requested
# product (model + concentration + size/storage + variant + count), in stock, on a
# valid PDP URL. Provenance (a genuine source_method) is necessary, NOT sufficient.
# The gate must also NOT over-reject legitimate alias wording (no false pends).
#
# ROLLBACK: this gate runs on EVERY request (high blast radius). The env flag
# ENABLE_EXACT_PRICE_GATE (default ON) flips the whole new layer off → exact
# b207bfa behaviour (is_exact_match→True, select_best→cheapest, no showable
# backstop). Flip it in Railway to disable without a code revert.
# ============================================================================

def exact_gate_enabled() -> bool:
    """True iff the exact-identity correctness gate is active (default ON)."""
    return os.getenv("ENABLE_EXACT_PRICE_GATE", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def sale_price_first_enabled() -> bool:
    """True iff the OpenGraph fallback prefers the SALE price over the LIST price
    (default ON).

    Fragrance sweep 2026-08-25 — on a Salla storefront ``product:price:amount`` is
    the crossed-out LIST price and the real shelf price is ``product:sale_price:
    amount``. Measured over the 86 mappable cached fragrance PDPs: the sale tag
    appears on 14 pages, ALL 14 Salla, and 10 of them diverge 1.13x-4.57x — so
    production shipped the LIST price on every one (P0 correctness).

    Default ON because it is a correctness fix, NOT a new capability. Read per
    call so Railway can flip it without a restart; with the flag OFF the OG
    branch takes its exact pre-change path (the sale tag is never even looked
    up), so the rollback is byte-identical. Deliberately INDEPENDENT of
    exact_gate_enabled(): this is a tag-precedence defect, not part of the
    exact-identity layer, and must survive that layer's master rollback."""
    return os.getenv("ENABLE_SALE_PRICE_FIRST", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def og_branch_fixes_enabled() -> bool:
    """True iff the two OpenGraph-branch correctness fixes are active (default ON).

    Fragrance sweep 2026-08-25, running the 92 cached PDPs through the production
    extractor. Both defects live in `_extract_og_price`, the OG fallback that
    `extract_price_from_html` calls at Priority 2:

    (a) `in_stock` was the LITERAL ``True`` — stock asserted with zero page
        signal (3 of the 4 live Shopify targets have zero available variants
        while production reported them in stock). The OG namespace carries
        ``product:availability`` on 20 of the 92 cached pages and
        ``og:availability`` on 1 more; the branch now reads it through the same
        tri-state ``is_available_state`` the JSON-LD path uses and emits None
        (unknown) when there is no tag. Never True by default.
    (b) ``float(og_price['content'])`` RAISED on a comma decimal, so the OG price
        of leperfumeqa ("279,00"), fyzara ("195,00") and mhgboutique ("403,75")
        was unparseable and thrown away. ``_parse_og_price_number`` below parses
        it (and must NOT be ``parse_price_string``, which strips commas
        unconditionally and reads "24,00" as 2400.0).
    REVERTED — a third change, "(c)", once rode this flag: it moved the OG
    branch from Priority 2 down BELOW microdata and the WooCommerce span. Over
    the same 92 cached pages with ENABLE_EXACT_PRICE_GATE=false that reorder
    produced ZERO improvements and four regressions (oudworlds 19.54 -> 3.00
    BHD, a 6.5x under-price; perfumeskuwait 10.95 -> 8.90; faces.ae 569.64 ->
    238.76; perfumeqatar's provenance relabelled fake-genuine), so it is gone.
    The OG call in `extract_price_from_html` is now UNCONDITIONAL at Priority 2
    and this flag no longer touches cascade order at all — pinned by
    tests/test_og_cascade_position.py. The two microdata changes that rode this
    flag as stated preconditions of (c) (document-order instead of max, and the
    converted_usd relabel) went with it; each is defensible on its own but must
    be measured on its own, not as a rider.

    Default ON because both remaining changes are correctness fixes, not new
    capability. Read per call so Railway can flip it without a restart; with the
    flag OFF the OG branch takes its exact pre-change path — the hardcoded True
    and the bare float() — so the rollback is byte-identical. Deliberately
    INDEPENDENT of exact_gate_enabled() and of sale_price_first_enabled(): these
    are OG tag-reading defects, not part of the exact-identity layer or of the
    sale-vs-list precedence fix, and must survive either one's rollback."""
    return os.getenv("ENABLE_OG_BRANCH_FIXES", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def wide_candidate_enabled() -> bool:
    """True iff extract_jsonld_price carries the WIDE candidate dict (default ON).

    Fragrance sweep 2026-08-25 — the extractor already json.loads() and walks the
    ENTIRE schema.org Product node to reach ``offers[].price``, then reduces it to
    five keys and discards the rest. Everything else on that SAME node is
    therefore free: zero extra fetches, zero extra parses, zero extra latency.
    Measured availability on the Product node across the 86 cached PDPs that map
    to a target row: description 73.3%, image 79.1%, sku 68.6%, brand 55.8%,
    gtin-or-mpn 36.0%, category 22.1%, aggregateRating 14.0%, reviewBody 9.3%.

    Default ON because it is additive capture on an already-parsed node, not a
    new network or CPU cost. Read per call so Railway can flip it without a
    restart; with the flag OFF the candidate dict has EXACTLY the five keys it
    had before (amount/currency/in_stock/name, plus brand iff
    exact_gate_enabled()), so the rollback is byte-identical. Deliberately
    INDEPENDENT of exact_gate_enabled(), sale_price_first_enabled() and
    og_branch_fixes_enabled(): this is data CAPTURE, not price selection, and
    none of those rollbacks should silently narrow it.

    NOTE the widened keys are consumed by NOTHING in the selection path —
    select_best reads only amount/in_stock/title/name/url/brand/retailer/
    retailer_score and _selection_match takes plain strings — so turning this on
    cannot move a winner (pinned in tests/test_wide_candidate_dict.py)."""
    return os.getenv("ENABLE_WIDE_CANDIDATE", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def wide_signal_text_enabled() -> bool:
    """True iff the Shopify adapter derives size/concentration from the WIDENED
    signal text — title + variant title + product_type + tags + body_html —
    instead of title + variant title alone (default OFF).

    Fragrance sweep 2026-08-25 — `_match_shopify_product` builds
    ``_signal_text = f"{title} {_variant_title}"`` and reads the two fragrance
    axes off it. The SAME `/products.json` row already carries `product_type`,
    `tags` and `body_html`, so folding them in costs nothing (no extra fetch, no
    extra parse). Measured over 999 live Shopify fragrance products: size capture
    25.6% -> 62.7%, concentration 7.6% -> 24.1%.

    DEFAULT OFF — it ships DORMANT for a canary. Unlike the other Step-2..5
    flags this is not a pure-capture change with a provably inert blast radius:
    ``price.size`` is consumed downstream (extraction_service, response_builder,
    structured_comparison_service), so filling a size that used to be None can
    move a like-for-like comparison. The default therefore uses the repo's
    explicit truthy ALLOW-LIST idiom (per `_shopify_pdp_json_enabled` /
    `variant_min_guard_enabled`) rather than the default-ON
    ``not in ("false","0","no","off","")`` form, so an unset, empty or misspelt
    value leaves the widening OFF.

    Read PER CALL so Railway can flip it without a restart. With the flag OFF
    `_wide_signal_capture_text` is never invoked — `body_html` is not even
    looked at — and the annotations come from exactly the pre-change narrow text
    via exactly the pre-change functions, so the rollback is byte-identical.

    Deliberately INDEPENDENT of exact_gate_enabled(), sale_price_first_enabled(),
    og_branch_fixes_enabled(), wide_candidate_enabled() and
    shopify_pdp_json_enabled(): this is the Shopify catalog adapter's CAPTURE
    text, not part of the exact-identity layer, the OG tag fixes, the JSON-LD
    candidate dict or the {pdp}.js data source, so none of their rollbacks (or
    rollouts) should move it.

    SELECTION SAFETY — the widened text feeds ONLY `extract_sizes_ml` /
    `extract_concentration`. `variant_precision_rank` and `flagship_basis_bonus`
    keep reading the NARROW text, so no variant and no price can move; pinned in
    tests/test_wide_signal_text.py (`test_wide_ranking_would_have_flipped_the_
    winner` builds the catalog where a wide-ranked implementation ships a 3x
    dearer product, and `test_the_winner_does_not_flip` proves this one does
    not)."""
    return os.getenv("ENABLE_WIDE_SIGNAL_TEXT", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def variant_min_guard_enabled() -> bool:
    """Scraping audit 2026-07-08 — gate the variable-product MIN-variation decant guard
    (a woo/shopify variable product served its cheapest 30ml variation as the full bottle).
    Default OFF (ships DORMANT); HARD-REQUIRES exact_gate_enabled() so a master rollback also
    disables it (mirrors the localhouse floor-bypass precedent). Read per-call (env flip, no
    restart). Flag OFF -> every adapter takes its exact current path -> byte-identical."""
    if not exact_gate_enabled():
        return False
    return os.getenv("ENABLE_VARIANT_MIN_PRICE_GUARD", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _budget_fragrance_floor_enabled() -> bool:
    """True iff the BUDGET Arabic/Gulf-house fragrance floor is active (default ON).

    When ON, is_implausible_low_fragrance_price applies a much lower price floor to
    known budget houses (Lattafa/Rasasi/Al Haramain/Ajmal/Armaf/... — see
    BUDGET_FRAGRANCE_BRAND_KEYWORDS) so their genuine cheap 8-25 BHD full bottles
    are NOT suppressed as "implausibly low" by the 25/100ml designer floor. Read
    FRESH per call so a flag flip takes effect without a restart. OFF -> the legacy
    25/100ml designer floor applies to these houses too (byte-identical to before).
    """
    return os.getenv("ENABLE_BUDGET_FRAGRANCE_FLOOR", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def _budget_house_trusted_price(
    product_name: str, price: Optional[Dict[str, Any]]
) -> bool:
    """True iff `price` is a TRUSTWORTHY genuine budget-Arabic-house price for which
    the fragrance low-price FLOOR is a false positive (so the display chokepoint may
    bypass it).

    The low-price floor (is_implausible_low_fragrance_price) is a heuristic for the
    LOOSE Serper-shopping path — it drops a wrong-cheap mislabel that slipped past
    matching. But a budget house (Lattafa/Rasasi/Al Haramain/Ajmal/...) genuinely
    retails a full 100ml EDP for 8-25 BHD, and when the price comes from a DIRECT
    store adapter (woo/shopify/…) that already exact-matched the SKU and carries a
    real PDP URL, the store's listed price IS authoritative — the 25/100ml designer
    floor then WRONGLY pends it (Lattafa Khamrah 12 BHD, even from the wired
    alhajisbahrain source). This bypass is applied ONLY at the display chokepoint;
    the floor STILL runs on the loose Serper-shopping extract AND on the pre-
    selection internal floor sites (noon `_select_offer`, scs fan-out/Tier-2
    winners), so wrong-cheap mislabels there are unaffected (a documented coverage
    limit — a genuine budget price resolved ONLY via those looser paths is dropped
    before display; the exact-gated direct-adapter path surfaces it).

    Guards keep it tight: gated on BOTH _budget_fragrance_floor_enabled() AND
    exact_gate_enabled() — the trust is PREMISED on the exact-gate's identity
    guarantee, so a full ENABLE_EXACT_PRICE_GATE=false rollback (which disables the
    identity/PDP backstops) also disables this bypass, keeping the rollback
    byte-identical to pre-PR. Requires a GENUINE native-BHD source_method (never
    estimated/converted), a real non-listing PDP URL, an IN-STOCK price (an OOS
    below-floor price stays floored), an amount >= the 5 BHD artifact floor (a
    fils/decimal glitch never trusted), a budget-house brand token, and NOT one of
    the houses' genuinely-expensive concentrated dehn-al-oud/mukhallat/attar OIL
    lines (word-boundary matched so "attar" can't hit "muattar")."""
    if not (_budget_fragrance_floor_enabled() and exact_gate_enabled()):
        return False
    if not isinstance(price, dict):
        return False
    # OUT-OF-STOCK — never trust an OOS below-floor price (the legacy floor dropped
    # it at the adapter; keep that defense so the bypass can't re-admit it).
    if price.get("in_stock") is False:
        return False
    # ABSOLUTE artifact floor — the bypass lowers the fragrance floor from the 25/
    # 100ml designer floor to this sanity bound, NEVER to 0. A trusted budget price
    # must still clear _FRAGRANCE_MIN_FLOOR_BHD (5 BHD): a budget house genuinely
    # retails 8+ BHD, so a sub-5 amount is a scrape/parse artifact (a mis-parsed
    # fils/decimal — the exact-gate validates IDENTITY, not the amount), which must
    # stay pended even for a correctly-titled exact SKU.
    amount = price.get("amount")
    if not isinstance(amount, (int, float)) or amount < _FRAGRANCE_MIN_FLOOR_BHD:
        return False
    name_lower = (product_name or "").lower()
    if not any(b in name_lower for b in BUDGET_FRAGRANCE_BRAND_KEYWORDS):
        return False
    # An expensive concentrated-oil line keeps the floor (belt-and-suspenders,
    # word-boundary matched so a short token can't collide with a name fragment).
    hay = name_lower + " " + str(price.get("title") or price.get("name") or "").lower()
    if _BUDGET_HOUSE_PREMIUM_LINE_RE.search(hay):
        return False
    if (price.get("source_method") or "") not in _GENUINE_BH_SOURCE_METHODS:
        return False
    url = price.get("url")
    if not (isinstance(url, str) and url.strip()) or _is_listing_url(url):
        return False
    return True


def frag_reconcile_fix_enabled() -> bool:
    """True iff the fragrance-pair size-reconcile broadening is active (default
    OFF -> byte-identical to today).

    Read FRESH per call (env, not module-level) so a flag flip takes effect
    without a restart. When ON, a SIZE-UNSPECIFIED fragrance on the
    canon=="fragrances" reconcile path defaults to the flagship 100ml basis even
    when its NAME is not caught by the (too-narrow) _is_designer_fragrance_name
    brand-keyword heuristic — because the ORCHESTRATOR already resolved the pair
    category to fragrances, so an unsized product on that path IS a fragrance. It
    ONLY broadens the unsized case: any explicit `\\d+ml` token on either side is
    still used verbatim (a genuine 30ml/50ml still resolves + still pends vs a
    100ml partner). Fixes genuine adapter prices (woo/magento/noon carry no
    price.size + no ml token in the title) being wrongly NULLED when only one side
    was brand-keyword-recognized.
    """
    return os.getenv("ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _fairness_ignore_estimate_enabled() -> bool:
    """True iff pair-fairness ignores an ESTIMATE side (default ON).

    An estimate is not a comparable DISPLAYED price (the chokepoint suppresses it)
    and carries no real size/unit basis, so it must not participate in the
    fairness reconcile — otherwise a sizeless estimate assigned the flagship-100ml
    default wrongly 'reaches the target' and PENDS the pair's genuine, showable
    price (observed: Ajmal Aristocrat 21.5 genuine pended because Rasasi only
    estimated). Read FRESH per call. Flag-OFF -> the prior pend-the-genuine
    behavior (byte-identical rollback)."""
    return os.getenv("ENABLE_FAIRNESS_IGNORE_ESTIMATE", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def _is_estimate_price(price: Any) -> bool:
    """True iff `price` is a GPT training-data ESTIMATE (not a cited/scraped
    price). Estimates are suppressed at the display chokepoint, so for the
    DISPLAYED pair-comparison they are effectively absent. Converted_usd is a real
    cited price (shown with the honesty caption) → NOT an estimate."""
    if not isinstance(price, dict):
        return False
    return bool(price.get("estimated")) or (price.get("source_method") == "estimated")


def _fold_identity(s: str) -> str:
    """Lowercase + NFKD diacritic-fold so an accented title matches a plain-ASCII
    query and vice versa ("Acqua di Giò"→"acqua di gio", "Lancôme"→"lancome").
    Trademark / registered / copyright marks are dropped FIRST — otherwise NFKD
    expands ™ (U+2122) to the letters "TM" and glues it onto the word ("Shark™" →
    "sharktm"), manufacturing a false identity token that breaks an exact match."""
    if not s:
        return ""
    s = s.replace("™", "").replace("®", "").replace("©", "")
    # "+" upgrade marker -> the WORD "plus" so the symbol form ("Galaxy S24+", "Effaclar Duo+")
    # and the spelled form ("Galaxy S24 Plus") produce the SAME identity token (coverage R9
    # HIGH) — a base query ("S24") still differs (no "plus" token) so the variant-add guard
    # rejects it; only the symbol-vs-spelled SAME-SKU pair is unified.
    s = s.replace("+", " plus ")
    # NOTE: parenthetical content is NOT stripped here. normalize_words already strips
    # edge-parens per token, and a blanket paren-strip is ASYMMETRIC — it drops a
    # candidate's "(Cholecalciferol)" while a query that writes the same chemical name
    # BARE keeps it, manufacturing a false subset-miss over-rejection (the Solgar D3
    # iherb case). Descriptive categories have no superset guard, so a parenthetical
    # synonym the candidate adds is already tolerated by the subset check.
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c)
    )
    # Drop a trailing STORE-NAME segment after a pipe / double-colon / guillemet — a page
    # <title>/og:title routinely appends the retailer ("... | Sharaf DG Bahrain", "... ::
    # Noon") which is NOT product identity and would otherwise add store tokens that
    # over-reject the superset guard (coverage review F). A pipe never appears inside a
    # real product name, so this is safe; " - " is preserved (it is used inside brand-omitted
    # titles like "Daisy - EDT").
    folded = re.split(r"\s*[|»]\s*|\s*::\s*", folded, 1)[0]
    # Slash-joined colourways/specs ("White/Black", "Cloud White/Core Black") -> each token
    # is matched individually (coverage review over-rejection); treat '/' like a space.
    folded = folded.replace("/", " ")
    # British/American spelling folds so a genuine GCC-retailer spelling matches the query
    # (coverage review: CeraVe Moisturising vs Moisturizing, Kerastase Masque vs Mask) —
    # before tokenizing so identity sets are equal.
    folded = re.sub(r"ising\b", "izing", folded)
    folded = re.sub(r"iser\b", "izer", folded)
    folded = re.sub(r"isation\b", "ization", folded)
    folded = folded.replace("colour", "color").replace("masque", "mask")
    # Possessive / internal apostrophe fold ("Men's"->"mens", "L'Oreal"->"loreal",
    # "Pro Filt'r"->"profiltr") — genuine GCC fashion titles overwhelmingly use the
    # apostrophe gender form, which otherwise survives as a non-padding token and pends
    # EVERY gendered listing (coverage review CRITICAL). The apostrophe-before-digit (a
    # fashion year "'07") is preserved for the year-suffix strip.
    folded = re.sub(r"'s\b", "s", folded)
    folded = re.sub(r"(?<=[a-z])'(?=[a-z])", "", folded)
    # Trailing "+" glyph (Effaclar Duo+) is decided by the real tokens, not punctuation.
    folded = re.sub(r"(\w)\+", r"\1", folded)
    # Nth-generation ORDINAL -> bare digit ("2nd"/"9th" -> "2"/"9") so AirPods Pro 2 ==
    # "Pro (2nd Generation)", iPad 9 == "9th Gen" (coverage review electronics over-rejection).
    folded = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", folded)
    # Screen-inch: STRIP the inch-marked number entirely ("13-inch"/'13"' -> "") so a
    # candidate that states a screen size the query OMITS does not over-reject (coverage
    # review). A both-stated DIFFERENT inch is caught by the _inch_mismatch axis (which
    # parses the raw string). A BARE number (no inch unit) stays as identity.
    folded = re.sub(r"\b\d+(?:\.\d+)?\s*(?:-\s*)?(?:inch(?:es)?\b|[\"”″]+)", " ", folded)
    # Punctuation/gluing normalization so a number-label glued vs spaced tokenizes the
    # SAME ("No.3"=="No. 3"=="#3"; "SPF30"=="SPF 30") — otherwise normalize_words keeps
    # "no.3"/"spf30" as one token and a genuine match false-pends (coverage review G).
    folded = re.sub(r"\bno\.?\s*(\d)", r"no \1", folded)
    folded = re.sub(r"#\s*(\d)", r"no \1", folded)
    folded = re.sub(r"\bspf\s*(\d)", r"spf \1", folded)
    # Collapse a thousands-separator inside a number ("5,000 IU" -> "5000 IU") so the dose
    # measure-strip + the dose axis see one number (a comma otherwise leaves "5"/"000"/"iu"
    # tokens that false-pend a genuine "5000 IU" listing — the iherb 5,000 IU case).
    folded = re.sub(r"(\d),(\d{3})\b", r"\1\2", folded)
    # Grocery diet variant written as two words -> one token so it is a distinctive
    # variant the superset guard rejects ("Sugar Free" -> "sugarfree").
    folded = re.sub(r"\bsugar\s*free\b", "sugarfree", folded)
    return folded


# Every measurement token that is a SEPARATE comparison axis (size/storage/count/
# strength) — stripped from the IDENTITY token set so it is compared on its own
# axis, never as an identity word. Superset of _SIZE_STRIP_RE + oz/fl-oz + mg/IU.
_IDENTITY_MEASURE_STRIP_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*"
    # optional veg/vegetable/veggie/plant qualifier before a count unit ("180 Veg Capsules")
    r"(?:(?:veg(?:etable|gie)?|plant)\s+)?"
    r"(?:tb|gb|ml|fl\s*oz|oz|lbs?|pounds?|l|kg|g|mg|mcg|iu|"
    r"capsules?|caps|tablets?|tabs|softgels?|gummies|gummy|count|ct|pieces?|pcs|sachets?)\b",
    re.I,
)

# Form / packaging words that are NOT product identity (defense-in-depth so a lone
# "Spray" on a normal EDP bottle, or a "Set" suffix, doesn't break identity equality).
_FORM_NOISE_TOKENS = frozenset({
    "set", "spray", "mist", "deodorant", "candle", "refill", "miniature",
    "lotion", "cream", "gel", "oil", "balm", "shower", "body", "hair", "travel",
    "pack",
})

# Colour / edition / gender tokens that are an OPEN alias class — a non-identity
# variant for the categories where colour is cosmetic (electronics/fashion). NOT
# stripped for fragrances (a colour word can be the product NAME: "Black Opium",
# "Light Blue") nor makeup/skincare (shade can matter).
_COLOR_EDITION_TOKENS = frozenset({
    "black", "white", "blue", "red", "green", "gold", "silver", "grey", "gray",
    "rose", "pink", "purple", "violet", "yellow", "orange", "brown", "beige",
    "navy", "teal", "titanium", "graphite", "midnight", "starlight", "space",
    "cream", "ivory", "bronze", "copper", "champagne", "lavender", "mint",
    "coral", "burgundy", "edition", "limited", "special",
    # Marketing COLOUR PREFIXES (Samsung/OEM) — a colour modifier, NOT a SKU variant,
    # so a "Phantom Black" / "Awesome Blue" / "Cosmic Grey" descriptive title must not
    # add a distinctive token (coverage review A over-rejection). Only for the
    # colour-alias categories (electronics/fashion), like the rest of this set.
    "phantom", "awesome", "cosmic", "prism", "mystic", "aura", "marble", "sierra",
    "pacific", "alpine", "obsidian", "onyx", "platinum", "graphene",
    "natural", "desert", "stormy",
    # Samsung 2025 colourway names, incl. the GLUED one-token form sharafdg
    # lists ("Icyblue" on the live S25 PDP — BF3, sweep OR-4: it was the second
    # bisected trigger blocking kpi-elec-002). Same class as phantom/awesome.
    "icy", "icyblue", "silvershadow", "titaniumsilverblue",
    # Sneaker COLOURWAY nicknames + modifiers (coverage review over-rejection) — a
    # colourway is a cosmetic variant in real fashion titles ("Dunk Low Panda", "Cloud
    # White/Core Black", "AJ1 Chicago"). Treated like a colour (stripped for fashion).
    "panda", "chicago", "bred", "sail", "cloud", "core", "gum", "oreo", "university",
    "wolf", "varsity", "bone", "sesame", "volt", "triple", "smoke",
})
_COLOR_ALIAS_CATEGORIES = frozenset({"electronics", "fashion"})
# "shadow" is DELIBERATELY NOT in the shared colour set (Wave B-FIX BF2, sweep
# L4): Nike AF1 "Shadow" is a distinct, pricier fashion SILHOUETTE — like
# Fontanka/Twist, which were never colour words — so for FASHION it must
# discriminate BOTH ways (colour-stripping it removed the only discriminating
# token and leaked the flanker end-to-end). For ELECTRONICS it IS a real OEM
# colour word ("HP Victus ... Shadow Black", "Realme ... Shadow Black"), so a
# flat removal would over-reject genuine colour-suffixed listings — the
# electronics identity strip keeps it via this scoped extension (the
# tighten's own over-rejection is the next blind spot).
# "sky" (Wave C C2, kpiE2E RS-1): the Apple "Sky Blue" colourway on the LIVE
# sharafdg MacBook Air M5 rows — an OEM colour word for ELECTRONICS, but kept
# distinctive for FASHION (Sky Jordan-class line names), exactly the "shadow"
# precedent.
_ELECTRONICS_ONLY_COLOR_TOKENS = frozenset({"shadow", "sky"})

# Model-line variant qualifiers that MUST match (set-equality, either direction).
# Category-gated: applied ONLY to electronics so brand words that collide with a
# qualifier in OTHER categories ("Max" in Max Factor, "Air" in Air Jordan, "Mini"
# in Mini) are NOT treated as qualifiers — there the identity-equality + axes carry it.
_ELECTRONICS_QUALIFIERS = frozenset({
    "fe", "se", "lite", "neo", "pro", "max", "plus", "ultra", "mini", "air",
    "promax",
    # NOTE: "5g" is deliberately NOT a qualifier — nearly all modern flagships are
    # 5G and the query routinely omits it ("Galaxy S24" must match a genuine
    # "Galaxy S24 ... 5G Smartphone" PDP). 5G is stripped as noise, not discriminated.
})
_CATEGORY_VARIANT_QUALIFIERS = {
    "electronics": _ELECTRONICS_QUALIFIERS,
}


# GENERIC category nouns — words that name a product CLASS, not a specific SKU
# ("smartphone", "headphones", "protein"). A resolved query name often carries one
# ("Sony WH-1000XM5 Headphones") that a terse genuine PDP/shopping title omits — a
# MISSING generic noun must NOT reject the match (the brand+model already discriminate).
# DELIBERATELY EXCLUDED: perfume/cologne/parfum (collide with the concentration axis —
# "Perfume" parses as the Parfum concentration); watch/buds/band (accessory CLASSES
# that DO discriminate). Built from HIGH_VALUE_DEVICE_NOUNS + audio/wearable/apparel/
# supplement class nouns.
# Generic CLASS nouns are CATEGORY-SCOPED (coverage review round 6): a noun is only
# "generic" (tolerated-when-omitted / class-swap-checked) for the category it belongs to.
# A makeup noun ("blush") is a DISTINCTIVE token for a FRAGRANCE ("Good Girl" vs "Good Girl
# Blush" are different perfumes) — subtracting it cross-category leaks the flanker.
_GENERIC_BASE_NOUNS = frozenset(HIGH_VALUE_DEVICE_NOUNS) | {
    "headphones", "headphone", "earphones", "earphone", "earbuds", "earbud",
    "speaker", "soundbar", "protein", "supplement", "supplements",
    "vitamin", "vitamins", "vacuum", "cleaner", "sunglasses", "eyewear",
    # "eyeglasses" — the optical-frame listing noun (namshi/eyewa/optica list
    # RX frames as "... Clubmaster Eyeglasses") beside "sunglasses" (BF4, sweep
    # OR-10). A sunglasses-vs-eyeglasses PAIR still class-swap-rejects (sun vs
    # optical Clubmaster are different products). NOTE: "optical frame" cannot
    # join — these are single-TOKEN sets (normalize_words tokens; a phrase can
    # never match) and the bare "optical"/"frame" tokens are collision-prone
    # cross-category (digital photo Frame), so they are deliberately omitted.
    "eyeglasses",
    # DELIBERATELY EXCLUDED: "whey"/"casein"/"plant" — a protein TYPE is distinctive.
}
_GENERIC_ELECTRONICS_NOUNS = frozenset({
    "keyboard", "mouse", "controller", "headset", "monitor", "webcam", "charger",
})
_GENERIC_MAKEUP_NOUNS = frozenset({
    "blush", "lipstick", "mascara", "foundation", "concealer", "eyeshadow",
    "eyeliner", "highlighter", "bronzer", "gloss", "lipgloss", "primer", "powder",
})
_GENERIC_FASHION_NOUNS = frozenset({
    "sneakers", "sneaker", "shoes", "shoe", "sandals", "sandal", "boots", "boot",
    "loafers", "loafer", "pumps", "heels", "slides", "clogs", "mules", "espadrilles",
    "slippers", "sliders",
    # garment-class nouns (moved out of _FASHION_PADDING so a CLASS SWAP — Dress vs Skirt —
    # rejects, while a one-sided class noun is tolerated) (coverage review round 6 HIGH).
    "dress", "shirt", "tshirt", "tee", "polo", "hoodie", "jacket", "coat", "blazer",
    "sweater", "sweatshirt", "skirt", "shorts", "pants", "pant", "jeans", "jean",
    "cardigan", "jumper", "leggings", "top",
})
_GENERIC_GROCERY_NOUNS = frozenset({
    "coffee", "tea", "juice", "milk", "cola", "soda", "water", "chocolate", "chips",
    "crisps", "cereal", "sauce", "snack", "biscuits", "butter", "cheese", "bread",
})
_CATEGORY_GENERIC_NOUNS = {
    "electronics": _GENERIC_ELECTRONICS_NOUNS,
    "makeup": _GENERIC_MAKEUP_NOUNS,
    "fashion": _GENERIC_FASHION_NOUNS,
    "grocery": _GENERIC_GROCERY_NOUNS,
}


def _generic_for(category: Optional[str]) -> frozenset:
    """The CLASS nouns generic for `category` (base universal + category-specific). Used
    so a cross-category noun (makeup 'blush' for a fragrance) stays a DISTINCTIVE token."""
    return _GENERIC_BASE_NOUNS | _CATEGORY_GENERIC_NOUNS.get((category or "").lower(), frozenset())


# Backward-compat: the union (used by any external reference / the flag-OFF no-op path).
GENERIC_CATEGORY_NOUNS = (_GENERIC_BASE_NOUNS | _GENERIC_ELECTRONICS_NOUNS
                          | _GENERIC_MAKEUP_NOUNS | _GENERIC_FASHION_NOUNS
                          | _GENERIC_GROCERY_NOUNS)


# Fragrance/fashion brand alias groups — each set holds every token form of one
# brand (abbreviation + spelled-out). When the resolved `brand` matches ANY token in a
# group, all forms are stripped from the identity tokens on both sides so a query that
# uses the abbreviation matches a candidate title that spells it out (and vice versa).
# Only triggered when the brand IS one of these houses, so there is no cross-category
# collateral (a phone brand never matches).
_BRAND_ALIAS_GROUPS = (
    frozenset({"ysl", "yves", "saint", "laurent"}),
    frozenset({"dg", "d&g", "dolce", "gabbana"}),
    frozenset({"jpg", "jean", "paul", "gaultier"}),
    frozenset({"ck", "calvin", "klein"}),
    frozenset({"ch", "carolina", "herrera"}),
    frozenset({"mj", "marc", "jacobs"}),
    frozenset({"tf", "tom", "ford"}),
    frozenset({"vr", "v&r", "viktor", "rolf"}),
    # HOUSE-name groups — a genuine title often carries the full house ("Christian
    # Dior Sauvage", "Gianni Versace Eros", "Giorgio/Emporio Armani", "Lancome Paris",
    # "Burberry London") while the resolved brand is the short form. Folding all forms
    # out of BOTH sides stops the extra house word from false-pending the match
    # (coverage review G). Each group is triggered ONLY when the brand is that house,
    # so there is no cross-brand collateral.
    frozenset({"dior", "christian"}),
    frozenset({"versace", "gianni"}),
    frozenset({"armani", "giorgio", "emporio"}),
    frozenset({"lancome", "paris"}),
    frozenset({"montblanc", "mont", "blanc"}),
    # NOTE: deliberately NO {burberry, london} — "Burberry London" is itself a real
    # fragrance line, so folding "london" would cross-match different products.
)


# Max input length for the identity/axis matchers — a real product name/title is well under
# this; longer inputs are truncated to bound the numeric-axis regexes (ReDoS guard, review HIGH).
_MATCH_INPUT_CAP = 512

# Luxottica catalog 0-prefix — namshi/Luxottica feeds list frames as "0RB3025"/
# "0RX5154"/"0Oo9102"/"0Po0714" where the consumer model code is RB3025/OO9102/
# PO0714. Generalized from (rb|rx) to ANY two-letter house code (Wave B-FIX BF4,
# sweep OR-9: namshi lists ALL Luxottica-house brands — Oakley 0Oo/Persol 0Po/
# Armani 0Ar/Versace 0Ve/D&G 0Dg — with the same 0-prefix convention). STILL
# narrow by design (full-token: 0 + exactly two letters + 3+ digits): a
# pure-numeric leading-zero token ("501"/"0801") or a short code ("0ab12") is
# NEVER stripped — the fold is an alias, not a wildcard (a DIFFERENT code still
# mismatches after folding; both directions pinned).
_LUXOTTICA_ZERO_RE = re.compile(r"^0([a-z]{2}\d{3,})$")

# The unicode hyphen family GCC retailer titles actually carry (Wave C C2,
# kpiE2E RS-1: the live sharafdg "8‑core" uses U+2011 NON-BREAKING HYPHEN,
# permalink-confirmed %e2%80%91) — U+2010 HYPHEN, U+2011 NON-BREAKING HYPHEN,
# U+2013 EN DASH. NFKD (_fold_identity) folds U+2011 -> U+2010 but leaves
# U+2010/U+2013 intact, and the raw-text axes see all of them, so every
# hyphen-shaped spec regex must accept the whole class alongside ASCII "-".
_UNICODE_HYPHENS = "‐‑–"

# CPU/GPU core-COUNT spec phrasing ("10-core CPU", "8 Core GPU", "10core",
# and the unicode-hyphen "8‑core") — retailer spec-sheet detail on
# electronics titles (BF3, sweep OR-2: the live sharafdg MacBook M5 title
# carries BOTH "10-core CPU" and "8‑core GPU", each surviving as a
# digit-bearing identity token that variant-add-rejected the EXACT SKU).
# Stripped from electronics IDENTITY and compared on its own
# both-stated-different axis (_core_count_mismatch) — one-sided tolerated
# (the chip-tier axis carries the major discrimination), a contradicting
# count (12-core query vs 10-core title) still rejects. Word forms only:
# "dual/octa-core" carry no digit and stay with the octa/quad/core padding.
_CORE_COUNT_RE = re.compile(
    rf"\b(\d+)\s*(?:[-{_UNICODE_HYPHENS}]\s*)?core\b", re.I,
)

# macOS-ANCHORED OS-version strip (Wave C C2, kpiE2E RS-1): "macOS Tahoe" /
# "macOS Sequoia" is the SHIPPING OS a GCC retailer states mid-title — never
# a SKU discriminator (the chip/model axes discriminate the laptop). BOUNDED:
# the version word is stripped ONLY when anchored to its "macos" token — a
# bare floating "tahoe"/"sequoia" stays a distinctive identity token, so a
# product genuinely NAMED with one of these words never gains acceptance.
_MACOS_VERSION_RE = re.compile(
    r"\bmacos(?:\s+(?:tahoe|sequoia|sonoma|ventura|monterey))?\b"
)

# Keyboard-LAYOUT phrase strip (Wave C C2, kpiE2E RS-1): "English & Arabic
# Keyboard" / "Arabic Keyboard" / "English Keyboard" is the standard GCC
# laptop layout attribute — the language words are stripped ONLY in the
# "<layout> keyboard" phrase (collapsed onto the already-padded "keyboard"
# token), and ONLY on a LAPTOP-class surface (_LAPTOP_NOUN_RE at the call
# site) — so a KEYBOARD product's layout ("Logitech K120 Arabic Keyboard")
# and a bare "arabic"/"english" edition word anywhere else stay identity.
# Runs on _fold_identity output ("/" already folded to a space); "&amp;" is
# tolerated defense-in-depth for a title that missed the ingestion decode.
_KEYBOARD_LAYOUT_RE = re.compile(
    rf"\b(?:(?:english|arabic)\s*(?:&amp;|[&+,\-{_UNICODE_HYPHENS}]|and)?\s*)"
    rf"{{1,2}}keyboards?\b"
)

# Wave-2 B2b (C2): the curated nutrient-name prefixes whose SPACED digit form must fold to
# the glued form (Omega 3 -> omega3, B 12 -> b12, Co Q10 -> coq10, D 3 -> d3, K 2 -> k2,
# Q 10 -> q10). Bounded to real vitamin/nutrient prefixes so no unrelated "word <digit>" pair
# bridges. The digit run is 1-2 (vitamin numbers) so a 3+-digit dose never glues.
# Separator is space OR hyphen ("Omega 3" / "Omega-3" / "B-12" / "B 12") — both glue to the
# same token. Electronics model codes (WH-1000XM5) are NEVER reached: both fold sites are
# supplement-category-scoped, and the curated prefix set has no overlap with model codes.
#
# B2fix — two convergence bugs the B2 sweep found (both flag-ON-only, supplement-scoped):
#   DEFECT 1 (vitamin-alt glued the WORD "vitamin"): the dedicated
#     "vitamin[sep][letter]" alternative captured "vitamin b" into group(1), so
#     "Vitamin B-6" folded to "vitaminb6" while "Vitamin B6" stayed {vitamin, b6}
#     (the letter+digit were already adjacent, no separator for the alt to consume)
#     => disjoint identity => flag-ON REJECT of the same SKU. FIX: DROP the vitamin
#     alternative and let the bare-letter alt ([abcdek]) normalize ONLY the
#     "<letter><digit>" part, leaving "vitamin" as its own token, so B-6/B6/B 6 all
#     -> {vitamin, b6}.
#   DEFECT 2 (spaced "Co Q10" did not fold): the digit-separator run was `+`
#     (>=1), so "Co Q10" (q immediately followed by "10") did not match — only
#     "Coq 10" did. FIX: make the separator run `*` (>=0) so "Co Q10" == "CoQ10"
#     == "Coq 10" == "co-q10" all -> "coq10". `*` is idempotent (an already-glued
#     "b12"/"coq10" folds to itself), so the output is stable for every spelling.
_NUTRIENT_DIGIT_FOLD_RE = re.compile(
    rf"\b(omega|coq|co[\s\-{_UNICODE_HYPHENS}]*q|[abcdek])"
    rf"[\s\-{_UNICODE_HYPHENS}]*(\d{{1,2}})\b", re.I,
)


def _apply_nutrient_digit_fold(folded: str) -> str:
    """Glue a curated nutrient-name prefix to a 1-2 digit run so the SPACED spelling
    produces the SAME token as the glued/hyphen form ("omega 3"->"omega3", "b 12"->"b12",
    "co q10"->"coq10"). Wave-2 B2b (C2). Callers gate this behind
    variant_descriptor_axes_enabled() and scope it to supplements; runs on _fold_identity
    output AFTER the 4+-digit dose strip so a 3+-digit dose never glues."""
    return _NUTRIENT_DIGIT_FOLD_RE.sub(
        lambda m: re.sub(r"\s+", "", m.group(1)) + m.group(2), folded)


def _identity_tokens_ps(text: str, brand: str = "", category: Optional[str] = None) -> set:
    """PRODUCT-IDENTITY token set of `text`: diacritic-folded words, minus the
    brand words, the concentration PHRASE, every measurement token (size/storage/
    count/strength — separate axes), the category's variant qualifiers (compared
    separately), form-noise, and (for colour-alias categories) colour/edition
    tokens. Sub-3-char noise is dropped EXCEPT a pure 2+-digit model number ("15",
    "24") which stays as identity (the Zyte len>2 electronics gap). Two listings
    are the SAME product iff their identity sets are EQUAL."""
    cat = (category or "").lower()
    if text and len(text) > _MATCH_INPUT_CAP:  # ReDoS guard (comprehensive review HIGH)
        text = text[:_MATCH_INPUT_CAP]
    folded = _fold_identity(text)
    for pat, _label in _CONCENTRATION_PATTERNS:
        folded = pat.sub(" ", folded)
    folded = _IDENTITY_MEASURE_STRIP_RE.sub(" ", folded)
    # %-strength is a SEPARATE axis for cosmetics (and never an identity word) — strip it
    # so "Niacinamide 10%" identity == "Niacinamide" identity (the % drives _percent_mismatch).
    folded = _PERCENT_RE.sub(" ", folded)
    # SPF rating is a SEPARATE axis (one-sided tolerated, both-different -> _spf_mismatch) —
    # strip "spf <n>" so a sunscreen query that omits SPF matches an SPF-stated PDP.
    folded = _SPF_RE.sub(" ", folded)
    # Warranty/age CONTEXT numbers ("2 Year Warranty") are not identity — strip so the
    # kept-single-digit rule below doesn't manufacture a "2" identity token.
    folded = re.sub(r"\b\d+\s*(?:year|years|yr|yrs|month|months)\b", " ", folded)
    # Pack/multipack CONTEXT — a SKU axis for GROCERY (handled by _pack_mismatch), but
    # pure noise elsewhere ("Pack of 2" on a phone bundle) — strip for non-grocery.
    if cat != "grocery":
        folded = re.sub(r"\bpack\s*of\s*\d+\b|\b\d+\s*[-\s]?pack\b", " ", folded)
    # Electronics CPU/GPU core-count spec ("10-core CPU / 8-core GPU") is not
    # identity — compared on the _core_count_mismatch axis instead (BF3, OR-2).
    if cat == "electronics":
        folded = _CORE_COUNT_RE.sub(" ", folded)
        # C2 (kpiE2E RS-1) — the sharafdg-style slash-segment descriptors:
        # the SHIPPING OS ("macOS Tahoe", anchored to its "macos" token) and
        # the keyboard LAYOUT ("English & Arabic Keyboard", laptop-class
        # surfaces only, collapsed onto the padded "keyboard" token). Bounds
        # pinned both directions in tests/test_electronics_unlock_bfix.py:
        # a bare "tahoe"/"arabic" outside its anchor stays identity, and a
        # keyboard PRODUCT's layout still discriminates (no laptop noun).
        folded = _MACOS_VERSION_RE.sub(" ", folded)
        if _LAPTOP_NOUN_RE.search(folded):
            folded = _KEYBOARD_LAYOUT_RE.sub(" keyboard ", folded)
    # Fashion year/colourway re-release suffix ("'07") is noise, NOT the model number.
    if cat == "fashion":
        folded = re.sub(r"'\s*\d{2}\b", " ", folded)
        # The SAME suffix written bare or with a typographic quote ("Air Force 1 07",
        # "’07"): a LEADING-ZERO 2-digit is always the year form — a model number never
        # carries one (Air Max 95/90 stay identity) — so strip it too; the apostrophe
        # strip above is otherwise ONE-SIDED (query "07" kept vs candidate "'07"
        # dropped = a false identity miss on the exact SKU).
        folded = re.sub(r"\b0\d\b", " ", folded)
        # "Polo T-Shirt"/"Polo T Shirt" is retail phrasing for a POLO, not a tee
        # (6thstreet lists Lacoste L1212 that way) — collapse the compound so the
        # listing reads as class "polo": a polo query matches it, and a plain t-shirt
        # query now class-swap-rejects it. A BARE "t-shirt" (no polo) is untouched,
        # so polo-vs-t-shirt stays a contradiction in both directions.
        folded = re.sub(r"\bpolo\s+t[\s-]?shirts?\b", " polo ", folded)
        # "Special/Limited Edition" is a distinct, pricier SKU. Collapse the spelled phrase AND
        # the "SE" abbreviation into ONE distinctive identity token so (a) a base query rejects
        # EITHER form (coverage re-sweep HIGH: 'special'/'edition' were stripped as colour-edition
        # tokens, collapsing the candidate onto the base) and (b) "SE" and "Special Edition"
        # listings of the SAME edition MATCH (alias unify, like '+'/'Plus'). "limited edition" is
        # phrase-only (the bare "le" abbreviation collides with brands like "Le Coq Sportif").
        folded = re.sub(r"\bspecial\s+edition\b", " specialedition ", folded)
        folded = re.sub(r"\blimited\s+edition\b", " limitededition ", folded)
        folded = re.sub(r"\bse\b", " specialedition ", folded)
    # Supplement BARE dose number ("D3 5000" written without IU) — the measure strip only
    # removes a number WITH a unit ("5000 IU"), so a unit-less dose survives as a false
    # identity token and over-rejects a genuine "5000 IU" listing. Strip a bare 4+-digit
    # number (the dose range; a supplement COUNT is <1000) so the dose axis governs it.
    if cat == "supplements":
        folded = re.sub(r"\b\d{4,}\b", " ", folded)
        # Wave-2 B2b (C2, flag-gated): fold a digit-adjacent nutrient-name so the spaced
        # form matches the glued/hyphen form ("Omega 3" == "Omega-3" == "Omega3";
        # "B 12" == "B-12" == "B12"; "Co Q10" == "CoQ10"). normalize_words already REMOVES
        # hyphens (so "omega-3"->"omega3"), leaving ONLY the SPACED form disjoint; this glues
        # the space so any spelling produces the same identity token. Runs AFTER the 4+-digit
        # dose strip and is bounded to a 1-2 digit run (vitamin numbers) so a 3+-digit dose
        # ("Vitamin D 250") never glues. Curated nutrient prefixes only, so no unrelated
        # alnum tokens bridge (WH-1000XM5 is electronics, untouched by this cat-scoped fold).
        # Flag-OFF stays byte-identical.
        if variant_descriptor_axes_enabled():
            folded = _apply_nutrient_digit_fold(folded)
    words = normalize_words(folded)
    # Luxottica 0-prefix alias: "0rb3025" -> "rb3025" so the catalog list form and
    # the consumer model code are the SAME identity token (namshi KPI fash-004).
    words = {_LUXOTTICA_ZERO_RE.sub(r"\1", w) for w in words}
    brand_words = normalize_words(_fold_identity(brand)) if brand else set()
    # Also strip the HYPHEN-COLLAPSED brand form (in the brand's ORIGINAL word order) so a
    # hyphen-joined brand-in-title ("Coca-Cola"->"cocacola") is removed for a spaced brand
    # ("Coca Cola") and vice versa (coverage review).
    if brand and " " in brand.strip():
        brand_words = brand_words | {re.sub(r"\s+", "", _fold_identity(brand))}
    # Brand-ABBREVIATION fold — when the brand matches a known alias group, drop ALL
    # forms (abbreviation + spelled-out) from BOTH sides, so "YSL Black Opium" (query)
    # and "Yves Saint Laurent Black Opium" (candidate title) resolve to the same
    # identity {black, opium} instead of false-pending on the unmatched "ysl".
    for _group in _BRAND_ALIAS_GROUPS:
        if brand_words & _group:
            brand_words = brand_words | _group
    quals = _CATEGORY_VARIANT_QUALIFIERS.get(cat, frozenset())
    drop = set(brand_words) | _FORM_NOISE_TOKENS | quals
    if cat in _COLOR_ALIAS_CATEGORIES:
        drop = drop | _COLOR_EDITION_TOKENS
        if cat == "electronics":
            # OEM colour words that are a fashion SILHOUETTE ("shadow") stay
            # strippable ONLY for electronics (BF2, sweep L4).
            drop = drop | _ELECTRONICS_ONLY_COLOR_TOKENS
    if cat in _FRAGRANCE_BEAUTY_CATEGORIES:
        # Strip gender markers from identity (the _gender_mismatch contradiction axis
        # handles them) so a one-sided "Pour Homme" the terse query omits never breaks
        # the subset/flanker check.
        drop = drop | _GENDER_IDENTITY_STRIP
    out = set()
    for w in (words - drop):
        # Keep a token when it carries identity:
        #   - len>2 (ordinary words)
        #   - ANY digit-bearing token, incl a STANDALONE single digit ("1"/"4"/"3"/"6")
        #     — Air Jordan 1 vs 4, AirPods Pro 2 vs 3, Omega 3 vs 6, Chanel No 5 (the
        #     len>2-or-2+digit rule dropped these = the coverage-review superset leak).
        #     m2/m3/r6/5g (short alphanumeric models) keep here too.
        #   - makeup: a single letter / 2-char shade code (NARS Orgasm X, MAC shade A/B).
        #   - electronics: a 2-char alpha token (4070 Ti, Mark II roman numerals).
        #   - fashion: a whitelisted short model qualifier (Samba OG, Dunk Hi/Lo).
        if (len(w) > 2
                or any(c.isdigit() for c in w)
                or w in _ROMAN_NUMERAL_TOKENS  # Type II / Mark IV (2+-char roman = identity)
                or (cat == "makeup" and len(w) >= 1)
                # electronics keeps single+2-char model letters (Xbox Series S/X, iPhone
                # XR/XS, Galaxy A/S series) — a trailing model letter is the discriminator.
                or (cat == "electronics" and 1 <= len(w) <= 2)
                # skincare/haircare keep only WHITELISTED 2-char line codes (CeraVe SA,
                # Skinceuticals AM/PM, CeraVe CF) — NOT every 2-char word ("to" in "Normal
                # to Dry" must drop, else it over-rejects).
                or (cat in ("skincare", "haircare") and w in _SKINCARE_LINE_CODES)
                or (cat == "fashion" and w in _FASHION_KEPT_QUALIFIERS)):
            out.add(w)
    return out


# 2+-char roman numerals kept as identity tokens in EVERY category (Collagen Type II,
# Canon Mark IV, Civilization VI) — a SKU discriminator the len>2 rule would drop.
_ROMAN_NUMERAL_TOKENS = frozenset({
    "ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii",
})


def _quals_in(text: str, qualset: frozenset) -> set:
    """The variant-qualifier tokens present in `text` (diacritic-folded), restricted
    to `qualset`. Tokenizes on [a-z0-9]+ so "5g" is seen as one token."""
    toks = set(re.findall(r"[a-z0-9]+", _fold_identity(text)))
    return toks & qualset


def _concentration_mismatch(q: str, t: str) -> bool:
    """True iff BOTH carry an explicit fragrance concentration and they DIFFER
    (EDP vs EDT). A side that omits concentration does not trigger a mismatch.
    (Wave-2 A1: delegates to the VariantDescriptor — one implementation.)"""
    return _vd_scalar_differs(
        extract_variant_descriptor(q, None).concentration,
        extract_variant_descriptor(t, None).concentration,
    )


def _size_ml_raw(text: Optional[str]) -> Optional[float]:
    """The smallest ml size in `text` with oz converted RAW (oz*_ML_PER_FL_OZ, with
    NO standard-fragrance-bottle snap). The non-fragrance counterpart to
    extract_size_ml_any: that primitive snaps an oz value to a luxury bottle size
    (3.4oz->100) which is correct ONLY for fragrances — for a skincare/grocery
    product it pushed e.g. 8oz (236.6ml) to 250 and falsely mismatched a genuine
    '236 ml' listing of the SAME product. Returns None when no ml/oz token present."""
    if not text:
        return None
    vals: List[float] = [float(m) for m in _SIZE_ML_RE.findall(text)]
    for oz_str in _SIZE_OZ_RE.findall(text):
        try:
            vals.append(float(oz_str) * _ML_PER_FL_OZ)
        except (ValueError, TypeError):
            continue
    return min(vals) if vals else None


def _size_ml_mismatch(q: str, t: str, category: Optional[str] = None) -> bool:
    """True iff BOTH carry an ml/oz size and they DIFFER. A side with no size token
    does not mismatch.

    Category-aware (local review #2): for FRAGRANCES an oz value is snapped to the
    nearest standard retail bottle size (3.4oz == 100ml) and an EXACT match is
    required — unchanged, heavily-tested behaviour. For EVERY OTHER category an oz
    value is converted RAW (no luxury-bottle snap) and sizes within ~5% are the SAME
    size (absorbs oz<->ml rounding: 8oz == 236.6ml ≈ a '236 ml' / '237 ml' listing),
    so an oz-labelled skincare/grocery/supplement product is no longer over-rejected
    against its ml-labelled listing while a real size difference (88ml vs 236ml)
    still mismatches.
    (Wave-2 A1: delegates to the VariantDescriptor — one implementation.)"""
    return _vd_size_ml_mismatch(
        extract_variant_descriptor(q, category),
        extract_variant_descriptor(t, category),
        (category or "").lower(),
    )


def _match_storage_gb(text: str) -> Optional[float]:
    """The STORAGE capacity (GB) for the matcher — the LARGEST GB/TB token, since on a
    phone/laptop title that lists BOTH RAM and storage the storage is always the larger
    (8GB RAM + 256GB storage). extract_storage_gb() returns the MIN (a fairness-side
    conservative basis) which grabs the RAM value and manufactured a false storage
    mismatch (coverage review: '8GB 256GB' over-rejected a genuine '256GB')."""
    vals: List[float] = []
    for num, unit in _STORAGE_GB_RE.findall(text or ""):
        try:
            v = float(num)
        except (TypeError, ValueError):
            continue
        vals.append(v * 1024.0 if unit.lower() == "tb" else v)
    return max(vals) if vals else None


def _storage_mismatch(q: str, t: str) -> bool:
    """True iff BOTH carry a GB/TB storage size and they DIFFER (256 vs 128). Uses the
    LARGEST GB token (storage, not RAM) so a query pinning both RAM+storage does not
    false-pend a genuine storage-only listing.
    (Wave-2 A1: delegates to the VariantDescriptor — one implementation.)"""
    return _vd_scalar_differs(
        extract_variant_descriptor(q, None).storage_gb,
        extract_variant_descriptor(t, None).storage_gb,
    )


def _count_mismatch(q: str, t: str) -> bool:
    """True iff BOTH carry a unit count and they DIFFER (120 vs 240 softgels).
    (Wave-2 A1: delegates to the VariantDescriptor — one implementation.)"""
    return _vd_scalar_differs(
        extract_variant_descriptor(q, None).count,
        extract_variant_descriptor(t, None).count,
    )


# Supplement strength: capture (value, unit) so a wrong DOSE (5000 IU vs 1000 IU)
# is a discriminating axis. Conservative cross-unit: only an explicit SAME-unit
# different-value is a mismatch (mg vs g equivalence is NOT asserted → no false pend).
_STRENGTH_RE = re.compile(r"(?<![a-z0-9])(\d+(?:[.,]\d+)?)\s*(iu|mg|mcg)(?![a-z])", re.IGNORECASE)


def _doses(text: str) -> set:
    out = set()
    for val, unit in _STRENGTH_RE.findall(text or ""):
        try:
            # A comma in a dose is a THOUSANDS separator ("5,000 IU" = 5000), never a
            # decimal — supplement doses are integers; treating it as a decimal point
            # ("5,000"->5.0) manufactured a false strength mismatch (5000 IU vs 5,000 IU).
            out.add((float(val.replace(",", "")), unit.lower()))
        except (TypeError, ValueError):
            continue
    return out


def _strength_mismatch(q: str, t: str) -> bool:
    """True iff BOTH carry an explicit mg/IU/mcg dose with the SAME unit but a
    DIFFERENT value (Vitamin D3 5000 IU vs 1000 IU). Cross-unit pairs (mg vs g) are
    NOT a mismatch — avoids false-pending an mg↔g-equivalent listing.
    (Wave-2 A1: delegates to the VariantDescriptor — one implementation.)"""
    return _vd_strength_mismatch(
        extract_variant_descriptor(q, None).doses,
        extract_variant_descriptor(t, None).doses,
    )


def _weights_volumes(text: str) -> set:
    """ALL (value, base) weight/volume tokens in `text` — base normalized to grams
    (kg→g) or millilitres (L→ml). A SET (not min) so a SECONDARY figure (a 30g
    per-serving, a 50g travel bonus) does not hide the headline net weight."""
    out = set()
    for num, unit in _WEIGHT_VOLUME_RE.findall(text or ""):
        try:
            v = float(num)
        except (TypeError, ValueError):
            continue
        u = unit.lower()
        if u == "kg":
            out.add((v * 1000.0, "g"))
        elif u == "g":
            out.add((v, "g"))
        elif u in ("lb", "lbs", "pound", "pounds"):
            # Protein/grocery are nearly always lb-labelled in the GCC — a 2lb vs 5lb
            # mismatch must fire (coverage review B). lb -> g (×453.592), same "g" base.
            out.add((round(v * 453.592, 2), "g"))
        elif u == "l":
            out.add((v * 1000.0, "ml"))
        elif u == "ml":
            out.add((v, "ml"))
    return out


# lb/pound token presence — the lb->g conversion (×453.592) is the ONLY weight
# conversion that yields a non-integer gram value, so an lb-labelled side never
# EXACTLY equals a gram/kg-labelled listing of the same tub (5lb=2267.96g vs a
# "2270g" / "2.27kg" label). kg->g and L->ml are exact (×1000).
_LB_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:lbs?|pounds?)\b", re.I)


def _weight_or_volume_mismatch(q: str, t: str) -> bool:
    """True iff BOTH carry a SAME-BASE weight/volume (grams or ml) and the HEADLINE
    (net/package) size DIFFERS (CeraVe 50g vs 340g). Different bases (g vs ml) never
    mismatch.

    HEADLINE = the LARGEST value per base. A product title routinely lists a SECONDARY
    measurement alongside the net weight — a serving/nutrition figure ("ISO100 5lb,
    25g protein per scoop") or a per-bottle figure — that is NOT the package size. The
    old SET-overlap rule (no mismatch if ANY value overlaps) let that secondary figure
    MASK a different net weight: "ISO100 5lb 25g" vs "ISO100 2lb 25g" both share the 25g
    serving and were wrongly accepted as the same SKU (external review P1). Comparing the
    MAX per base ignores the smaller serving/nutrition figure and compares the real
    package size (5lb=2267.96g vs 2lb=907.18g -> mismatch), while still NOT mismatching a
    "908g + 30g per serving" listing against a plain "908g" (both headline 908).

    lb->g rounding tolerance (review #2b): when EITHER side carries an lb/pound token,
    the two HEADLINE grams values within 1% are the SAME size (5lb=2267.96g matches a
    "2270g" / "2.27kg" listing). Native g-vs-g and ml-vs-ml stay EXACT (distinct retail
    sizes are >>1% apart -> no spurious merge); the tolerance arms ONLY for lb.
    (Wave-2 A1: delegates to the VariantDescriptor — one implementation.)"""
    return _vd_weight_or_volume_mismatch(
        extract_variant_descriptor(q, None),
        extract_variant_descriptor(t, None),
    )


# Categories where a PRODUCT FORM (deodorant / candle / lotion / shower gel) names
# a DIFFERENT product than the default bottle/jar, so a one-sided form must reject.
_FRAGRANCE_BEAUTY_CATEGORIES = frozenset({
    "fragrances", "makeup", "skincare", "haircare",
})
# Only fragrances get the strict flanker near-equality (sub-line names — "Intense",
# "Elixir", "Over Red" — ARE the identity; titles carry little non-identity padding).
_FRAGRANCE_FLANKER_CATEGORIES = frozenset({"fragrances"})
# Non-identity padding words a genuine fragrance title carries (gender/marketing/
# atomizer wording) — stripped from BOTH sides before the fragrance flanker
# near-equality so a descriptive genuine title ("…Spray For Men Natural
# Vaporisateur") is NOT over-rejected, while a real sub-line marker ("Intense",
# "Elixir", "Over", "Red") stays distinctive and rejects the flanker. Concentration
# words (eau/de/parfum/toilette/edp/edt) are already stripped as the concentration
# PHRASE, so they need not appear here.
# Gender markers are PADDING for the flanker/subset token check (so "Bleu de Chanel
# Pour Homme" matches a genuine "Bleu de Chanel" PDP that omits the suffix — the common
# GCC bestseller case). The gender-FLIP flanker (Eros men's vs Eros Pour Femme women's)
# is caught SEPARATELY by the _gender_mismatch CONTRADICTION axis, which fires only when
# BOTH sides state a gender and they DIFFER — never on a one-sided omission.
_FRAGRANCE_PADDING_TOKENS = frozenset({
    "for", "men", "women", "man", "woman", "mens", "womens", "ladies", "gents",
    "unisex", "homme", "hommes", "femme", "femmes", "pour", "him", "her",
    "natural", "spray", "sprays",
    "vaporisateur", "vapo", "vaporizer", "atomiser", "atomizer", "new", "gift",
    "perfume", "perfumes", "fragrance", "fragrances", "scent", "scented",
    "the", "and", "with", "size", "full", "genuine", "original", "authentic", "brand",
    # NOTE: "cologne" is DELIBERATELY NOT padding — bare "Cologne" (not the "Eau de
    # Cologne" concentration phrase) is a distinct sub-line (Creed Aventus -> Aventus
    # Cologne is a different ~$300 fragrance), so it must stay a distinctive identity
    # token the superset guard rejects (coverage review A).
})

# Gender CONTRADICTION axis — a fragrance is the WRONG product only when the query and
# the candidate state OPPOSITE genders (Eros Pour Homme vs Eros Pour Femme). A one-sided
# gender (query states it, candidate omits, or vice versa) is the canonical single-gender
# title and must NOT reject (the dominant genuine case). These base sets hold the
# unambiguous STRICT gender words — they feed BOTH the contradiction axis AND the
# femme-asymmetry / identity logic, so the flanker pronouns "him"/"her" are NOT added here
# (that would extend the asymmetry to a "For Her" query and collapse "Woman" vs "Her").
# him/her feed ONLY the contradiction axis, via _pronoun_gender_of + _vd_gender_mismatch.
# "ladies"/"gents" remain excluded.
_GENDER_MEN_TOKENS = frozenset({"homme", "hommes", "men", "man", "mens", "uomo", "herren"})
_GENDER_WOMEN_TOKENS = frozenset({"femme", "femmes", "women", "woman", "womens", "donna", "damen"})
# Gender markers are STRIPPED from the identity token set (like the concentration
# phrase) for fragrance/beauty, so the subset/flanker checks ignore a one-sided
# "Pour Homme"; the _gender_mismatch CONTRADICTION axis does the real discrimination.
# "him"/"her" are NOT in the strict gender sets and NOT stripped from identity here — they
# feed ONLY the contradiction axis via _pronoun_gender_of (flag-gated), so a name like
# Burberry "Her"/"Him" keeps its distinctive-token behaviour AND the femme-asymmetry is
# unchanged (no "For Her"-query over-rejection, no "Woman" vs "Her" collapse).
_GENDER_IDENTITY_STRIP = _GENDER_MEN_TOKENS | _GENDER_WOMEN_TOKENS | frozenset({"pour"})


def _gender_of(text: str) -> Optional[str]:
    """'men' / 'women' / None (none or BOTH → ambiguous/unisex) for `text`, from the
    STRICT gender words only. This is the general gender axis — it feeds the
    femme-asymmetry (_vd_feminine_query_unconfirmed) and the empty-core/identity logic, so
    it must NOT include the flanker pronouns him/her: doing so would over-reject a "For Her"
    query vs its gender-omitting base AND collapse "Woman" vs "Her". Pronoun contradiction
    is handled SEPARATELY by _pronoun_gender_of + _vd_gender_mismatch."""
    toks = set(re.findall(r"[a-z0-9]+", _fold_identity(text or "")))
    m = bool(toks & _GENDER_MEN_TOKENS)
    w = bool(toks & _GENDER_WOMEN_TOKENS)
    if m and not w:
        return "men"
    if w and not m:
        return "women"
    return None


def _pronoun_gender_of(text: str) -> Optional[str]:
    """Flanker-pronoun gender for the CONTRADICTION axis ONLY: 'men' for a bare "him",
    'women' for a bare "her" (both/neither → None). Gated behind
    variant_descriptor_axes_enabled() so it is inert (None) flag-OFF → byte-identical.

    DECOUPLED from _gender_of on purpose: him/her feed ONLY _vd_gender_mismatch (so
    "Burberry Her" vs "Burberry Him" is rejected as a gender contradiction), NOT the
    femme-asymmetry nor the identity/empty-core collapse — so a one-sided "X For Her" query
    still tolerates its gender-omitting base and "X Woman" vs "X Her" stays rejected by the
    STRICT asymmetry (no new over-rejection, no new empty-core leak). Tokenized on WORD
    boundaries (_fold_identity + [a-z0-9]+), so "Cher"/"Hermes"/"his"/"hers" never trigger."""
    if not variant_descriptor_axes_enabled():
        return None
    toks = set(re.findall(r"[a-z0-9]+", _fold_identity(text or "")))
    m = "him" in toks
    w = "her" in toks
    if m and not w:
        return "men"
    if w and not m:
        return "women"
    return None


def _gender_mismatch(query_name: str, candidate_title: str) -> bool:
    """True iff query and candidate state CONFLICTING genders (a gender-flip flanker).
    A one-sided gender (the canonical 'Pour Homme' the terse query omits) is NOT a
    mismatch. (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_gender_mismatch(
        extract_variant_descriptor(query_name, None),
        extract_variant_descriptor(candidate_title, None),
    )


def _feminine_query_unconfirmed(query_name: str, candidate_title: str) -> bool:
    """True iff the QUERY states a WOMEN's flanker (Eros Pour Femme) but the candidate does
    NOT confirm it (Eros / Eros Pour Homme). The unspecified base of a designer fragrance is
    conventionally the men's/original, so a femme query matching a gender-OMITTING candidate is
    a WRONG product (comprehensive review MEDIUM leak). ASYMMETRIC by design: a men's/unisex
    query still tolerates the unspecified base (preserves the 'Pour Homme'-bestseller match).

    NOTE (local review #1, INTENTIONALLY NOT symmetrized): the inverse — a base/men's query
    matching a women's CANDIDATE ("Versace Eros" -> "Eros Pour Femme") — is a real but
    UNFIXABLE-by-tokens leak. A symmetric "reject when exactly one side states women's" rule
    mass-over-rejects every WOMEN's-BASE fragrance whose candidate merely adds a "For Women"
    descriptor ("Black Opium" -> "Black Opium For Women" is the SAME product), because gender
    tokens alone cannot distinguish a flanker-of-a-men's-base from a women's-base descriptor.
    The asymmetry deliberately trades the narrow Eros-style leak for not pending the far more
    common women's-base case. See tests/test_correctness_review_pr9_fixes.py.
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_feminine_query_unconfirmed(
        extract_variant_descriptor(query_name, None),
        extract_variant_descriptor(candidate_title, None),
    )

# Form PHRASES that name a different product when present on only one side. Ordered
# longest-first so "body lotion" wins over a bare "body". The default bottle/jar form
# is None. "spray"/"mist"/"set"/"travel" alone are NOT discriminating (a perfume IS a
# spray) — only the explicit alternate forms below discriminate.
_PRODUCT_FORM_PATTERNS: List[Tuple[str, str]] = [
    # A gift SET / multi-piece BUNDLE is a DIFFERENT SKU than the single bottle/jar
    # (different contents + price) — discriminating, longest-first.
    ("gift set", "set"), ("coffret", "set"), ("bundle", "set"),
    ("collection set", "set"), ("travel set", "set"), ("set", "set"),
    ("body lotion", "lotion"), ("body cream", "cream"), ("body butter", "butter"),
    ("body mist", "bodymist"), ("body spray", "bodyspray"), ("body wash", "wash"),
    ("shower gel", "showergel"), ("hair mist", "hairmist"), ("after shave", "aftershave"),
    ("aftershave", "aftershave"), ("roll on", "rollon"), ("roll-on", "rollon"),
    ("rollon", "rollon"), ("deodorant", "deodorant"), ("antiperspirant", "deodorant"),
    ("candle", "candle"), ("soap", "soap"), ("scrub", "scrub"), ("shampoo", "shampoo"),
    ("conditioner", "conditioner"), ("shower", "showergel"), ("lotion", "lotion"),
    ("refill", "refill"), ("pomade", "pomade"), ("serum", "serum"),
    # Standalone cosmetic FORMS (skincare/haircare/makeup) — cream vs gel vs oil vs balm
    # are DIFFERENT products (coverage review C). These are also in _FORM_NOISE_TOKENS
    # (stripped from IDENTITY) so a form word is an enforced axis, never a silent identity
    # token. ONE-SIDED tolerance for these categories lives in _form_mismatch.
    ("cream", "cream"), ("gel", "gel"), ("oil", "oil"), ("balm", "balm"),
    ("butter", "butter"), ("mask", "mask"), ("toner", "toner"),
    ("essence", "essence"), ("foam", "foam"), ("mousse", "mousse"),
    ("ampoule", "ampoule"), ("peel", "peel"),
    # skincare/haircare cleanser/treatment/emulsion forms — so _form_mismatch fires
    # both-stated-different (Cleanser vs Cream/Treatment/Mask) while staying one-sided
    # tolerant (coverage review round 5 HIGH).
    ("cleansing", "cleanser"), ("cleanser", "cleanser"), ("face wash", "wash"),
    ("wash", "wash"), ("treatment", "treatment"), ("emulsion", "emulsion"),
    ("fluid", "fluid"),
]


def _extract_product_form(text: str, brand: str = "") -> Optional[str]:
    """The discriminating product FORM in `text` (after removing brand words so a
    brand like "The Body Shop" / "Old Spice" doesn't manufacture a form), or None
    for the default bottle/jar. Phrase-matched longest-first."""
    folded = _fold_identity(text or "")
    if brand:
        for bw in normalize_words(_fold_identity(brand)):
            folded = re.sub(rf"\b{re.escape(bw)}\b", " ", folded)
    # An explicit multi-PIECE count ("3 Piece", "2 Pcs") is a SET, even without the
    # word "set" — a different SKU than the single bottle.
    if re.search(r"\b\d+\s*(?:piece|pieces|pcs|pc)\b", folded):
        return "set"
    for phrase, canon in _PRODUCT_FORM_PATTERNS:
        if re.search(rf"\b{re.escape(phrase)}\b", folded):
            return canon
    return None


def _form_mismatch(query_name: str, candidate_title: str, category: Optional[str],
                   brand: str = "") -> bool:
    """True iff the query and candidate name DIFFERENT product forms. A no-op outside
    fragrance/beauty categories (a phone has no 'form').

    Strictness differs by category (coverage review C):
      - FRAGRANCES: strict — a one-sided form (query=bottle/None, candidate=Deodorant)
        rejects (a deodorant is a different product than the EDP).
      - skincare/haircare/makeup: ONE-SIDED tolerant — a descriptive PDP that states a
        form the form-omitting query lacks (Niacinamide -> "Niacinamide Serum") must NOT
        pend; only TWO explicitly-stated DIFFERENT forms (cream vs gel) reject.
    (Wave-2 A1: delegates to the VariantDescriptor — the FRAGRANCES+MAKEUP
    strict-one-sided vs skincare/haircare both-stated split lives in
    _vd_form_mismatch.)"""
    return _vd_form_mismatch(
        extract_variant_descriptor(query_name, category, brand),
        extract_variant_descriptor(candidate_title, category, brand),
        (category or "").lower(),
    )


def _candidate_missing_query_axis(query_name: str, candidate_title: str,
                                  category: Optional[str]) -> bool:
    """True iff the QUERY states a discriminating axis that the CANDIDATE does NOT —
    i.e. the candidate is UNVERIFIED on an axis the user pinned, so it must PEND
    (fail-closed), not auto-accept. Scoped to the axes where a silent omission is a
    real wrong-variant leak: fragrance concentration + ml size, supplement strength +
    count. (Electronics storage is DELIBERATELY excluded — terse genuine PDP titles
    routinely omit it; the qualifier/variant_mismatch axes carry electronics.)
    (Wave-2 A1: delegates to the VariantDescriptor — the per-category axis set
    lives in _vd_candidate_missing_query_axis, comment-for-comment.)"""
    return _vd_candidate_missing_query_axis(
        extract_variant_descriptor(query_name, category),
        extract_variant_descriptor(candidate_title, category),
        (category or "").lower(),
    )


# Categories where a query-stated weight/volume the candidate omits = unverified -> pend.
# Supplements included (coverage review): a Whey 5lb query must not match a no-size listing.
_SIZE_OMIT_CATEGORIES = frozenset({"skincare", "makeup", "haircare", "grocery", "supplements"})

# Fashion CLOTHING sizes (apparel) — a SKU axis. Standalone size tokens.
_CLOTHING_SIZE_RE = re.compile(
    r"(?<![a-z0-9])(xxs|xs|s|m|l|xl|xxl|xxxl|2xl|3xl|small|medium|large)(?![a-z0-9])",
    re.I,
)
# A bare single-letter clothing size (S/M/L) is only a size when it follows "size".
_SIZED_CLOTHING_RE = re.compile(r"\bsize\s+(xxs|xs|s|m|l|xl|xxl|xxxl|2xl|3xl)\b", re.I)
_VITAMIN_LETTER_RE = re.compile(r"\bvitamin\s+([a-k])(?![a-z])", re.I)


def _colors_in(text: str) -> set:
    """The colour/colourway tokens present in `text` (from _COLOR_EDITION_TOKENS)."""
    toks = set(re.findall(r"[a-z0-9]+", _fold_identity(text or "")))
    return toks & _COLOR_EDITION_TOKENS


def _color_mismatch(query_name: str, candidate_title: str) -> bool:
    """Fashion colourway contradiction. The query's STATED colours must ALL appear in the
    candidate (a "White Green" query is NOT the "White Red" colourway just because both carry
    white — comprehensive-review HIGH dual-colourway leak). A one-sided colour (the query
    states none, or the candidate adds an extra colour beyond the query's) is tolerated.
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_color_mismatch(
        extract_variant_descriptor(query_name, None),
        extract_variant_descriptor(candidate_title, None),
    )


def _clothing_sizes_in(text: str) -> set:
    folded = _fold_identity(text or "")
    out = {m.lower() for m in _SIZED_CLOTHING_RE.findall(folded)}
    # also accept an explicit XL/XXL/small/medium/large standalone (unambiguous)
    for m in _CLOTHING_SIZE_RE.findall(folded):
        ml = m.lower()
        if ml in ("xs", "xxs", "xl", "xxl", "xxxl", "2xl", "3xl", "small", "medium", "large"):
            out.add(ml)
    return out


def _clothing_size_mismatch(query_name: str, candidate_title: str) -> bool:
    """Fashion apparel size contradiction — both state a clothing size and they DIFFER.
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).clothing_sizes,
        extract_variant_descriptor(candidate_title, None).clothing_sizes,
    )


def _vitamin_letter_mismatch(query_name: str, candidate_title: str) -> bool:
    """Supplement vitamin-letter contradiction — Vitamin C vs Vitamin D (the single
    letter is dropped from identity tokens, so it is checked as an explicit axis).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).vitamin_letters,
        extract_variant_descriptor(candidate_title, None).vitamin_letters,
    )


# Flagship fragrance concentrations — a different, more concentrated JUICE than the
# default EDP/EDT line. A candidate that ADDS one the query never asked for ("Black
# Opium" -> "Black Opium Le Parfum", "Sauvage" -> "Sauvage Parfum/Elixir") is a
# DIFFERENT product. (EDP/EDT/EDC are the standard lines — adding them is just a more
# specific title, NOT a different juice, so they are excluded here.)
_FLAGSHIP_CONCENTRATIONS = frozenset({"Extrait", "Parfum", "Parfum Intense"})


def _flagship_concentration_added(query_name: str, candidate_title: str) -> bool:
    """True iff the candidate states a FLAGSHIP concentration (Parfum/Extrait/Parfum
    Intense) that the query did not state — a different juice, fail-closed.
    (Wave-2 A1: delegates to the VariantDescriptor — _category_type_added, the
    untouched chokepoint pair check, inherits through this helper.)"""
    return _vd_flagship_concentration_added(
        extract_variant_descriptor(query_name, None),
        extract_variant_descriptor(candidate_title, None),
    )


# Supplement product-TYPE tokens that name a DIFFERENT formulation (Whey vs Whey
# Isolate/Concentrate/Hydrolysate; Vitamin D3 vs D3+K2). A candidate that ADDS one
# the query lacks is a different SKU.
_SUPPLEMENT_TYPE_TOKENS = frozenset({
    "isolate", "concentrate", "hydrolysate", "hydrolyzed", "hydrolysed",
    # Combo minerals/vitamins — a candidate that ADDS one the query lacks is a different
    # formulation ("Vitamin D3" vs "Vitamin D3 with Zinc"; "Calcium" vs "Calcium + Magnesium").
    "k2", "zinc", "magnesium", "calcium", "iron", "copper", "selenium",
    "b12", "b6", "folate", "folic", "biotin",
    # Mineral SALT forms — a candidate that ADDS a salt the query lacks is a DIFFERENT
    # SKU ("Magnesium" -> "Magnesium Glycinate/Citrate/Oxide") (coverage review A).
    "glycinate", "citrate", "oxide", "bisglycinate", "malate", "threonate",
    "gluconate", "chloride", "sulfate", "sulphate", "carbonate", "picolinate",
    "aspartate", "orotate", "taurate", "ascorbate",
    # Product SUB-LINE / potency suffixes — a different formulation/potency SKU
    # ("Centrum" -> "Centrum Silver"; "Fish Oil" -> "Triple Strength"; "Multivitamin" ->
    # "Advanced/Senior/Complete") (coverage review A). Tier words gold/ultimate/platinum
    # are NOT here — the superset guard catches them (they are not padding). REMOVED:
    # micronized (processing, same product), extra/double/mega/ultra (ambiguous flavour
    # "Double Rich Chocolate" / marketing) (coverage review round 4).
    "silver", "triple", "advanced", "senior", "complete",
})
# The bare ELEMENT / VITAMIN CONSTITUENT names within _SUPPLEMENT_TYPE_TOKENS (NOT the salt
# forms or formulation types). For a SINGLE-constituent query these discriminate a COMBO add
# ("Calcium" -> "Calcium Magnesium Zinc" is a different SKU). But for a MULTI-CONSTITUENT
# product query they are the product's own declared CONTENTS, not a flanker.
_SUPPLEMENT_CONSTITUENT_TOKENS = frozenset({
    "zinc", "magnesium", "calcium", "iron", "copper", "selenium",
    "b12", "b6", "folate", "folic", "biotin",
})
# Query words that NAME a multi-constituent product (defined BY containing several
# elements/vitamins): a descriptive title that ENUMERATES those constituents is the SAME SKU
# ("Now B-Complex" -> "Now B-Complex with B12 B6 Folate Biotin"; "Centrum Multivitamin" ->
# "...with Iron Zinc"; "Prenatal" -> "...with Folic Acid and Iron"). The acronym/abbreviation
# forms (ZMA, Cal-Mag) are NOT here — they ALSO fail the upstream selection superset (the
# acronym is not a subset of its expansion) so they need brand-alias normalization, a
# documented deferred residual (coverage re-sweep of the parallel review-fix commits).
_MULTI_CONSTITUENT_QUERY = frozenset({"complex", "multivitamin", "multivitamins", "prenatal"})

# --- Wave-2 B2a (C1): ACRONYM -> CONSTITUENTS fold (flag-gated) ---------------
# A supplement named by an ACRONYM (ZMA, Cal-Mag, B-Complex) is the SAME SKU as its
# descriptively-titled form that ENUMERATES the very constituents the acronym stands for
# ("Optimum ZMA" == "Optimum ZMA Zinc Magnesium Aspartate"). The acronym is not a subset of
# its expansion, so the superset/type-add guards over-reject the correct product at ALL
# decision points (census C1, runtime-verified). This curated table maps each acronym token
# to the constituent set it expands to; when the QUERY carries a table acronym, the
# candidate's EXTRA supplement-constituent tokens that fall INSIDE that expansion are folded
# (not counted as a variant-add). The fold is BOUNDED — it fires ONLY when the query token IS
# a table acronym, so the combo-leak boundary is untouched: "Calcium" (NOT an acronym) ->
# "Calcium Magnesium Zinc" still rejects, and any candidate constituent OUTSIDE the acronym's
# expansion still discriminates. Gated behind ENABLE_VARIANT_DESCRIPTOR_AXES (the exact-gate-
# scoped Wave-2 axes flag) so flag-OFF stays byte-identical.
#
# Keys are matched against the query's fold_tokens. Cal-Mag tokenizes to {cal, mag} (the
# hyphen splits it) while CalMag glues to {calmag}; both are handled via the split-form rule
# in _query_acronym_constituents. B-Complex ({b, complex}) / B Complex are ALSO already
# covered by the existing _MULTI_CONSTITUENT_QUERY "complex" path; the explicit "bcomplex"
# glued key here catches the glued spelling for parity.
_SUPPLEMENT_ACRONYM_CONSTITUENTS = {
    "zma": frozenset({"zinc", "magnesium", "aspartate"}),
    "calmag": frozenset({"calcium", "magnesium"}),
    "calmagnesium": frozenset({"calcium", "magnesium"}),
    "bcomplex": frozenset({
        "b12", "b6", "b1", "b2", "b3", "b5", "folate", "folic", "biotin",
        "thiamine", "riboflavin", "niacin", "pantothenic", "pyridoxine", "cobalamin",
    }),
}
# Multi-token acronym spellings the tokenizer splits (Cal-Mag -> {cal, mag}): the required
# token SET maps to the same constituent expansion as the glued key.
_SUPPLEMENT_ACRONYM_SPLIT_FORMS = (
    (frozenset({"cal", "mag"}), frozenset({"calcium", "magnesium"})),
)


def _query_acronym_constituents(q_fold: FrozenSet[str]) -> FrozenSet[str]:
    """The union of constituent expansions for every table acronym the QUERY fold carries —
    the token set the candidate is allowed to enumerate WITHOUT it counting as a variant-add
    (Wave-2 B2a / census C1). Empty when the query carries no table acronym (so a
    single-element query keeps the full combo-add discrimination)."""
    out: set = set()
    for acronym, constituents in _SUPPLEMENT_ACRONYM_CONSTITUENTS.items():
        if acronym in q_fold:
            out |= constituents
    for req_tokens, constituents in _SUPPLEMENT_ACRONYM_SPLIT_FORMS:
        if req_tokens <= q_fold:
            out |= constituents
    return frozenset(out)


def _supplement_type_added(query_name: str, candidate_title: str) -> bool:
    """True iff the candidate carries a supplement product-TYPE token (isolate/concentrate/
    hydrolysate / mineral salt-form / sub-line) the query lacks — a different formulation.

    EXCEPTION (coverage re-sweep): when the QUERY itself names a MULTI-CONSTITUENT product
    (B-Complex / Multivitamin / Prenatal), a title that merely ENUMERATES the bare element/
    vitamin CONSTITUENTS the product is defined to contain is the SAME SKU, not a flanker, so
    the bare constituent names are excluded for such queries. A SINGLE-constituent query keeps
    them — so a COMBO add still rejects ("Calcium" -> "Calcium Magnesium Zinc") and a
    formulation/salt-form add ("Magnesium" -> "Magnesium Citrate", "Whey" -> "Whey Isolate")
    stays a discriminator on BOTH (no combo leak).
    (Wave-2 A1: delegates to the VariantDescriptor — _category_type_added, the
    untouched chokepoint pair check, inherits through this helper.)"""
    return _vd_supplement_type_added(
        extract_variant_descriptor(query_name, None),
        extract_variant_descriptor(candidate_title, None),
    )


def _category_type_added(query_name: str, candidate_title: str, category: Optional[str]) -> bool:
    """A candidate that ADDS a category-specific DISTINCTIVE variant the query never
    asked for: a flagship fragrance concentration, or a supplement formulation type."""
    cat = (category or "").lower()
    if cat == "fragrances":
        return _flagship_concentration_added(query_name, candidate_title)
    if cat == "supplements":
        return (_supplement_type_added(query_name, candidate_title)
                or _supplement_form_added(query_name, candidate_title))
    return False


# ============================================================================
# COVERAGE-REVIEW (2026-06-28) — the missing numeric/form axes + the generalized
# candidate-adds-distinctive-token (superset) guard. Spec clusters A/B/C.
# ============================================================================

# --- % active-ingredient STRENGTH axis (skincare/haircare/makeup) ------------
# A discriminating axis ONLY for cosmetics, where % = active concentration
# (Niacinamide 10% vs 5%). NOT for supplements/grocery, where % is purity/marketing
# ("100% Whey", "2% milk") and must NOT gate. Spaced / "percent" / "pct" spellings + a
# single-digit / decimal value all parse.
_PERCENT_RE = re.compile(r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*(?:%|percent|pct)(?![a-z])", re.I)
_PERCENT_CATEGORIES = frozenset({"skincare", "haircare", "makeup"})


def _percents(text: str) -> set:
    out = set()
    for v in _PERCENT_RE.findall(text or ""):
        try:
            out.add(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _percent_mismatch(q: str, t: str) -> bool:
    """True iff BOTH carry a %-strength and they share NO value (10% vs 5%).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(q, None).percents,
        extract_variant_descriptor(t, None).percents,
    )


# --- fashion SHOE-SIZE axis ---------------------------------------------------
# A system-prefixed size (US/UK/EU 9, 10.5) is a SKU axis. A bare number is NOT
# captured (it collides with the model number, handled as identity).
_SHOE_SIZE_RE = re.compile(r"\b(us|uk|eu|eur)\s*(\d{1,2}(?:\.\d)?)\b", re.I)


def _shoe_sizes(text: str) -> set:
    out = set()
    for sys_, val in _SHOE_SIZE_RE.findall(text or ""):
        try:
            out.add((sys_.lower().replace("eur", "eu"), float(val)))
        except (TypeError, ValueError):
            continue
    return out


def _shoe_size_mismatch(q: str, t: str) -> bool:
    """True iff BOTH state a system-prefixed shoe size and share none (US 9 vs US 10).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(q, None).shoe_sizes,
        extract_variant_descriptor(t, None).shoe_sizes,
    )


# --- grocery PACK-COUNT axis --------------------------------------------------
_PACK_RE = re.compile(
    r"\bpack\s*of\s*(\d+)\b|\b(\d+)\s*[-\s]?pack\b|\b(\d+)\s*x\b|\b(\d+)\s*(?:ct|count)\b",
    re.I,
)


def _packs(text: str) -> set:
    out = set()
    for m in _PACK_RE.finditer(text or ""):
        for g in m.groups():
            if g:
                try:
                    out.add(float(g))
                except (TypeError, ValueError):
                    continue
    return out


def _pack_mismatch(q: str, t: str) -> bool:
    """True iff BOTH state a pack count and share none (6 Pack vs 24 Pack).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(q, None).packs,
        extract_variant_descriptor(t, None).packs,
    )


# --- supplement delivery FORM axis -------------------------------------------
# Default pill forms (softgel/capsule/tablet) are the standard presentation — a
# one-sided default form is TOLERATED. Alternative forms (gummy/powder/liquid/...)
# are a DIFFERENT SKU — a one-sided alternative form, or any two differing forms,
# rejects. Spec cluster C.
_SUPPLEMENT_DEFAULT_FORMS = frozenset({
    "softgel", "softgels", "capsule", "capsules", "caplet", "caplets",
    "tablet", "tablets", "pill", "pills", "vcap", "vcaps", "vegcap", "vegcaps",
    # "powder" is the DEFAULT presentation for protein/creatine (whey IS a powder), so a
    # one-sided "... Powder" must be TOLERATED, not pended — it only discriminates when the
    # other side states an ALTERNATIVE form (powder vs gummy), via the class check below.
    "powder",
})
_SUPPLEMENT_ALT_FORMS = frozenset({
    "gummy", "gummies", "liquid", "drops", "spray", "lozenge",
    "lozenges", "chewable", "chewables", "effervescent", "syrup",
})


def _supplement_form_added(query_name: str, candidate_title: str) -> bool:
    """Candidate adds an ALTERNATIVE delivery form (gummy/liquid/...) the query
    lacks, or the stated (default vs alternative) form CLASSES differ.
    (Wave-2 A1: delegates to the VariantDescriptor — _category_type_added, the
    untouched chokepoint pair check, inherits through this helper.)"""
    return _vd_supplement_form_added(
        extract_variant_descriptor(query_name, None),
        extract_variant_descriptor(candidate_title, None),
    )


# --- generalized candidate-adds-distinctive-token (SUPERSET) guard ------------
# THE KEYSTONE (coverage review, round 2): a candidate that carries an EXTRA distinctive
# IDENTITY token beyond the query — after subtracting a per-category PADDING allowlist —
# is a DIFFERENT (related) SKU, not just a longer title. This is the fragrance flanker
# pattern (t_core ⊆ q_core), GENERALIZED to EVERY category. A curated variant-marker
# allowlist was tried and is structurally leaky — sub-line/formulation/flavour tokens are
# UNBOUNDED (Kindle->Paperwhite, Creatine->Monohydrate, Coke->Cherry, AF1->AF1 Mid). The
# robust shape is the inverse: reject ANY extra non-padding token. Over-rejection is
# controlled by (a) the per-category PADDING (descriptive/marketing/connectivity/form/
# flavour-noise + major brand words) and (b) the q_core-EMPTY skip (a generic/class query
# legitimately matches any specific member: "Sony Headphones" -> "Sony WH-CH520").
# Categories with NO discriminating superset would be the leak family; ALL get it now.

# Base marketing/packaging/warranty noise (every category).
_BASE_NOISE_TOKENS = frozenset({
    "new", "genuine", "authentic", "brand", "official", "sealed", "boxed", "the",
    "and", "with", "for", "version", "item", "warranty", "year", "years", "month",
    "months", "yr", "yrs", "imported", "stock", "edition",
})
# Major MANUFACTURER words — a brand word a genuine title adds that the (brand-omitted)
# query lacks is never a SKU discriminator. Bounded to common GCC electronics/appliance/
# fashion houses so the superset never over-rejects a brand-in-title ("16-inch MacBook
# Pro" -> "...Apple..."). NOT applied to grocery (where "apple"/"orange" are flavours).
_MANUFACTURER_NOISE = frozenset({
    "apple", "samsung", "sony", "lg", "dell", "hp", "lenovo", "asus", "acer",
    "microsoft", "google", "huawei", "xiaomi", "oppo", "vivo", "realme", "nokia",
    "motorola", "oneplus", "nintendo", "canon", "nikon", "bose", "jbl", "logitech",
    "razer", "dyson", "anker", "belkin", "sandisk", "seagate", "kingston", "corsair",
    "msi", "gigabyte", "intel", "amd", "nvidia", "garmin", "fitbit", "gopro", "dji",
    "amazon", "philips", "panasonic", "tcl", "hisense", "honor", "nothing",
    "nike", "adidas", "puma", "reebok", "asics", "converse", "vans", "newbalance",
})
_ELECTRONICS_PADDING = _MANUFACTURER_NOISE | frozenset({
    "dual", "sim", "5g", "4g", "3g", "lte", "wifi", "gsm", "esim",
    "unlocked", "international", "global", "factory", "android", "ios", "mobile",
    "cellular", "smartphone", "smartphones", "phone", "phones", "gen", "generation",
    "wireless", "advanced", "bluetooth", "portable", "rechargeable", "smart",
    "inch", "display", "screen", "ram",
    # high-frequency descriptive/marketing words a genuine electronics title adds
    # (coverage review) — NOT a SKU variant for a model-number query.
    "noise", "cancelling", "cancellation", "anc", "cordless", "illuminated",
    # Apple-Silicon canonical-title descriptors + MagSafe accessory-name word (coverage R8):
    # "MacBook Air with M2 chip", "AirPods Pro 2 with MagSafe" — descriptive, not a variant.
    # ("chip" is safe — the M2/M3 tier is the discriminator, caught by _chip_tier_mismatch.)
    "with", "chip", "magsafe",
    # Regional / stock descriptors a GCC retailer title appends ("iPhone 15 128GB - Pink
    # Middle East Version with FaceTime") — same SKU, not a variant (coverage R8 sharafdg).
    "middle", "east", "version", "facetime", "region", "regional", "warranty", "years",
    # NOTE: "detect"/"absolute" are Dyson TRIM/line words (V8 Absolute, V15 Detect are
    # distinct SKUs) — NOT padding; they discriminate.
    "gaming", "geforce", "radeon", "model", "joycon", "joy", "con",
    # NOTE: "ventus"/"trio" REMOVED — MSI GPU COOLER-design LINES (RTX 4070 Ventus vs Trio
    # are distinct SKUs), like Dyson detect/absolute. They discriminate.
    "charger", "console", "headphones", "headphone", "earbuds",
    "speaker", "performance", "uhd", "4k", "8k", "octa", "quad", "core",
    # GPU factory-tune + camera/laptop spec descriptors (NOT a SKU/chip variant) —
    # 'oc'=overclocked, mirrorless/dslr/body/lens descriptive (coverage review round 5).
    "oc", "mirrorless", "dslr", "body", "lens", "ssd", "hdd", "ryzen", "camera",
    "intel", "amd",
    # spec NOUNS a BH retailer title appends alongside the already-padded
    # gpu/ram/ssd (BF3, sweep OR-2: sharafdg "10-core CPU", extra "13 Inch
    # IPS") — "cpu" is the exact sibling of "gpu" above; "ips" is a display
    # PANEL tech like the padded "uhd"/"4k" (the model number discriminates a
    # monitor/laptop SKU, never the panel word). NOTE: "oled" is DELIBERATELY
    # NOT padding — it names a distinct SKU (Switch OLED vs base Switch).
    "cpu", "ips",
    # NOTE: "kit" REMOVED — a camera Kit (body+lens) is a materially pricier SKU than the
    # body; an added "Kit" must reject a body/base query (coverage review round 6).
    # NOTE: "crystal" REMOVED — Samsung TV LINE (Crystal UHD vs QLED vs Neo QLED). It
    # discriminates. "ventus"/"trio" already removed (MSI cooler lines).
    "over", "ear", "overear", "onear", "inear", "vacuum", "cleaner", "keyboard", "mouse",
    "power", "bank", "powerbank", "graphics", "card", "gpu", "mic", "microphone",
    "adapter", "supply", "certified",
    # NOTE: "nano"/"refurbished"/"renewed" REMOVED — nano is a product LINE (iPod Nano);
    # refurbished/renewed is a CONDITION axis (_condition_mismatch), not padding.
})
_FASHION_PADDING = frozenset({
    "mens", "womens", "men", "women", "unisex", "ladies", "gents",
    # NOTE: kids/youth REMOVED — an age-SEGMENT is a distinct (lower-priced) SKU; a
    # one-sided "Kids"/"Youth" add must reject (coverage review round 5).
    "shoe", "shoes", "sneaker", "sneakers", "trainers", "footwear", "originals",
    # "retro" is Nike's standard release-line word in genuine same-product titles.
    # running/runner/performance = shoe-ACTIVITY descriptors (the MODEL name discriminates,
    # not the activity) — a genuine "Air Max SC Runner Sneakers Performance" listing for an
    # "Air Max SC" query (coverage R8 6thStreet fashion lever). A real shoe TYPE that IS a
    # SKU axis (trail vs road) is NOT padded.
    "retro", "running", "runner", "performance", "casual",
    # MATERIAL descriptors a genuine apparel title adds (one-sided tolerated; a both-
    # stated DIFFERENT material is caught by _material_mismatch): "Orangey Dress in
    # Cotton-blend". NOTE: fit/cut words (slim/regular/relaxed) are NOT padding — they are
    # a denim/apparel SKU axis (Levis 501 vs 501 Slim), kept as identity + _fit_mismatch.
    "cotton", "blend", "cottonblend", "leather", "denim", "wool", "silk", "linen",
    "polyester", "suede", "canvas", "nylon", "cashmere", "fleece", "jersey", "knit",
    "woven", "fabric", "material", "fit", "in", "original",
    # NOTE: garment CLASS nouns (dress/shirt/jacket/...) moved to _GENERIC_FASHION_NOUNS so
    # a CLASS SWAP (Dress vs Skirt) rejects while a one-sided class noun is tolerated.
}) | {b for b in _MANUFACTURER_NOISE if b in {"nike", "adidas", "puma", "reebok",
                                              "asics", "converse", "vans", "newbalance"}}
_GROCERY_PADDING = frozenset({
    "jar", "bottle", "can", "bag", "packet", "box", "tin", "carton", "bottles",
    # canonical-product descriptors (NOT variants): "Coca-Cola Original Taste",
    # "Nescafe Gold Instant Coffee" (coverage review over-rejection).
    "original", "instant", "taste", "drink", "soft", "fresh", "premium", "pure",
    # descriptive (non-variant) grocery type/prep nouns (coverage review).
    "potato", "tomato", "spread", "blend", "rolled",
    "plain",
    # NOTE: "hazelnut" REMOVED (it is a FLAVOUR -> _FLAVOUR_TOKENS); ground/whole/skimmed/
    # semi/still/sparkling/salted moved to the _grocery_prep_mismatch contradiction axis.
    # NOTE: grocery CLASS nouns (coffee/tea/juice/milk/cola/chocolate/...) moved to
    # GENERIC_CATEGORY_NOUNS so a CLASS SWAP (Coffee vs Tea) rejects, while a one-sided
    # class noun is still tolerated (coverage review cross-class leak).
})
# Cosmetic FORM words (skincare/haircare) — stripped from the superset (the form axis
# _form_mismatch handles them, one-sided-tolerant). NOT padding for makeup, where a
# format (liquid/oil/stick) IS a distinct SKU.
_COSMETIC_FORM_PADDING = frozenset({
    "serum", "toner", "essence", "cleanser", "mask", "foam", "mousse", "ampoule",
    "peel", "scrub", "shampoo", "conditioner", "wash", "cream", "gel", "oil",
    "balm", "lotion", "butter", "treatment", "perfector", "bond", "builder",
    "maintenance", "moisturiser", "drops",
    # packaging containers (not a SKU variant): "...340g Tub", "...473ml Pump".
    "tub", "pump", "tube", "dispenser", "sachet", "pot", "jar", "bottle",
})
# Chemical-synonym words a supplement title restates (cholecalciferol == D3) — a no-op
# token whether in the query (bare) or candidate (paren); padding on BOTH sides.
_SUPPLEMENT_CHEM_SYNONYMS = frozenset({
    "cholecalciferol", "ergocalciferol", "ascorbic", "acid", "tocopherol",
    "pyridoxine", "thiamine", "riboflavin",
    "pantothenic", "phylloquinone", "menaquinone", "alpha", "lipoic",
    # NOTE: cyanocobalamin / methylcobalamin are DIFFERENT B12 molecules (synthetic vs
    # active, different price) — NOT no-op synonyms; kept as distinctive identity tokens
    # so a B12-form swap rejects (coverage review round 5).
})
# makeup PADDING is intentionally SPARSE — a shade (number OR spelled-out name) is the
# PRIMARY SKU axis, so shade-NAME words must NOT be unconditional padding (that accepted
# any shade — coverage review CRITICAL). Spelled shade names are dropped only when BOTH
# sides share the shade NUMBER (handled in _selection_match). FINISH (matte/satin/dewy) is
# a CONTRADICTION axis (_finish_mismatch), not padding. Only truly-generic descriptors here.
# FINISH words — ONE-SIDED tolerated (Ruby Woo -> Ruby Woo Matte is the same matte
# lipstick) so they are padding, but a both-stated DIFFERENT finish (Matte vs Dewy) is a
# different SKU caught by _finish_mismatch.
_MAKEUP_FINISH_TOKENS = frozenset({
    "matte", "satin", "shimmer", "dewy", "glossy", "luminous", "radiant", "velvet",
    "metallic", "natural", "poreless",
    # FORMULA/finish words that distinguish foundation LINES (Pro Filt'r Hydrating vs Soft
    # Matte; Infallible Glow vs Matte). Both-stated-different rejects via _finish_mismatch; a
    # ONE-SIDED add is tolerated as descriptive (coverage re-sweep: "Fit Me 310 Smooth
    # Coverage" / "Natural Beige Glow" / "Hydrating Tint" must NOT over-reject — so 'smooth' is
    # deliberately EXCLUDED, it is a generic coverage descriptor, not a line word).
    "glow", "glowy", "glowing", "hydrating", "illuminating", "mattifying",
})
_MAKEUP_PADDING = _MAKEUP_FINISH_TOKENS | frozenset({
    "longwear", "longlasting", "buildable", "blendable", "lightweight",
    # "soft" is a FINISH/texture descriptor in makeup (Pro Filt'r Soft Matte, Soft Glow,
    # Soft Pinch) — padding it recovers the canonical product-line title (coverage R8). A
    # numbered shade ("Fit Me 240 Soft Sand") is already handled by the shade-NUMBER tolerance.
    "soft",
    # Pure connective stopwords (local review #4). Makeup is the ONLY category that keeps
    # these 2-char tokens as identity (the `len(w) >= 1` makeup keep-rule in
    # _identity_tokens_ps; every other category drops them via the len>2 rule), where they
    # over-reject the canonical "<product> IN <shade>" listing ("NARS Lipstick in Dolce Vita"
    # vs the query "NARS Lipstick Dolce Vita"). Padding them only here keeps the blast radius
    # to makeup and never touches another category. Deliberately EXCLUDES the article "a"/"an"
    # — a single-letter "a" can be a makeup shade code (the keep-rule's MAC-shade-A/B case), so
    # padding it would strip a real shade token.
    "to", "of", "in", "on", "by",
})
# --- contradiction axes (coverage review round 2): one-sided tolerated, both-stated-
# different rejected — mirrors _gender_mismatch / _color_mismatch ---------------
_FLAVOUR_TOKENS = frozenset({
    "vanilla", "chocolate", "strawberry", "berry", "citrus", "orange", "lemon", "mint",
    "cookies", "mango", "banana", "caramel", "cinnamon", "coconut", "grape", "cherry",
    "lime", "apple", "peach", "raspberry", "tropical", "unflavored", "unflavoured",
    "hazelnut", "almond", "pistachio", "honey",
    # 'cheese' is a generic grocery noun that is ALSO a flavour (Pringles Cheese vs Original) —
    # adding it closes the same one-sided grocery flavour-add leak as 'chocolate' (re-sweep LOW).
    "cheese",
    # flavour words a candidate ADDS that the prior set missed (coverage sweep CRIT/HIGH:
    # "Creatine Unflavored" -> "...Fruit Punch"; "...Cookies" -> "...Cream") — without
    # these the one-sided flavour add slipped past both the contradiction axis and the
    # padding subtraction (_SUPPLEMENT_PADDING listed 'fruit'/'punch' but they were absent
    # here, so _flavour_mismatch saw no flavour and the superset stripped them).
    "fruit", "punch", "cream",
})
# "Absence" flavour markers — a candidate ADDING one of these to a flavour-LESS query is
# the canonical UNFLAVOURED base ("Creatine" -> "Creatine Unflavored" is the SAME SKU), so
# it must NOT trigger the one-sided add rejection; but an UNFLAVORED query vs a real-flavour
# candidate DOES still conflict (caught because the real flavour is the add).
_FLAVOUR_ABSENCE = frozenset({"unflavored", "unflavoured", "plain", "natural"})
_FLAVOUR_CATEGORIES = frozenset({"supplements", "grocery"})


def _flavour_mismatch(query_name: str, candidate_title: str,
                      category: Optional[str] = None) -> bool:
    """CATEGORY-AWARE flavour discriminator (coverage sweep CRIT/HIGH).

    GROCERY is ASYMMETRIC: a candidate flavour the query does not cover is a DIFFERENT
    SKU ("Cheerios" -> "Cheerios Chocolate"; "Pepsi" -> "Pepsi Mango"). The old
    both-stated-different rule let this one-sided ADD slip because the added flavour
    word was also generic/padding and was subtracted before the variant-add guard.

    SUPPLEMENTS keep the both-stated-different rule (one-sided tolerated) — a bare
    protein/creatine query matching any flavour is INTENDED ("ISO100" -> "ISO100
    Vanilla" is the same product; see the flavour padding in _SUPPLEMENT_PADDING). Only
    a CONTRADICTION rejects: "Creatine Unflavored" -> "...Fruit Punch", "...Cookies" ->
    "...Cream" (both sides state a flavour and they differ). This is now caught because
    'fruit'/'punch'/'cream' were added to _FLAVOUR_TOKENS.

    A candidate that OMITS the query's flavour (terse listing) is tolerated in BOTH
    categories; a pure 'unflavored'/'plain' ADD to a flavour-less query is the canonical
    base (no reject).
    (Wave-2 A1: delegates to the VariantDescriptor — the grocery-asymmetric vs
    supplements-contradiction split lives in _vd_flavour_mismatch.)"""
    return _vd_flavour_mismatch(
        extract_variant_descriptor(query_name, category),
        extract_variant_descriptor(candidate_title, category),
        (category or "").lower(),
    )


def _finish_mismatch(query_name: str, candidate_title: str) -> bool:
    """True iff BOTH sides state a makeup finish and they share none (Matte vs Dewy).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).finishes,
        extract_variant_descriptor(candidate_title, None).finishes,
    )


_MATERIAL_TOKENS = frozenset({
    "leather", "suede", "canvas", "nylon", "denim", "mesh", "knit", "rubber",
    "synthetic", "wool", "cotton", "silk", "satin", "velvet",
})


def _material_mismatch(query_name: str, candidate_title: str) -> bool:
    """Fashion — True iff BOTH state a material and they share none (Leather vs Suede).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).materials,
        extract_variant_descriptor(candidate_title, None).materials,
    )


# CONDITION (electronics) — a refurbished/used/open-box unit is a different price TIER, so
# if EITHER side states a non-new condition the other lacks, reject (the default is new).
_CONDITION_TOKENS = frozenset({
    "refurbished", "refurb", "renewed", "used", "preowned", "openbox", "secondhand",
})


def _condition_mismatch(query_name: str, candidate_title: str) -> bool:
    """EITHER-direction one-sided reject (the only such axis): a non-new
    condition stated on exactly one side is a different price tier.
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return (extract_variant_descriptor(query_name, None).condition
            != extract_variant_descriptor(candidate_title, None).condition)


_INCH_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:inch(?:es)?\b|[\"”″]+)", re.I)


def _inch_mismatch(query_name: str, candidate_title: str) -> bool:
    """Electronics — True iff BOTH state a screen-inch size and they differ (14 vs 16).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).inches,
        extract_variant_descriptor(candidate_title, None).inches,
    )


# SPF (sunscreen rating) — a SKU axis for cosmetics (SPF 30 vs SPF 50). One-sided
# tolerated (stripped from identity), both-stated-different rejects (coverage review).
# NOTE (coverage sweep): a one-sided SPF ADD ("Kiehl's Ultra Facial Cream" -> "...SPF 30")
# is a real but DELIBERATELY-TOLERATED leak — making it asymmetric mass-over-rejects every
# sunscreen whose query omits the inherent SPF (Anthelios / EltaMD / Supergoop), pinned by
# test_R6_overrej_skincare_spf_one_sided_accepted. Tokens cannot distinguish an inherent-SPF
# sunscreen from an SPF variant of a cream, so the tolerate-one-sided decision stands.
_SPF_RE = re.compile(r"\bspf\s*(\d+)\b", re.I)


def _spf_mismatch(query_name: str, candidate_title: str) -> bool:
    """Both-stated-different SPF rating (SPF 30 vs SPF 50); one-sided tolerated
    (see the revert note below). (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).spfs,
        extract_variant_descriptor(candidate_title, None).spfs,
    )

# NOTE (external review #4): an SPF-ADD axis (candidate states an SPF the query omits ->
# different SKU) was implemented and then REVERTED. A sunscreen-context carve-out cannot
# cover the unbounded set of sunscreen names (a coverage sweep over-rejected mainstream
# sunscreens — Vichy Capital Soleil, Bioderma Photoderm, Banana Boat, Neutrogena Ultra
# Sheer — whose names carry no sun/UV token), while the leak it prevents is low-harm (a
# base cream vs its SPF variant are near-identical prices). A one-sided SPF is therefore
# TOLERATED; only a both-stated DIFFERENT SPF (_spf_mismatch) rejects. Doing better needs
# structured variant metadata, not a token rule.


# Electronics RAM axis — a dual-GB title ("S24 8GB 256GB") pins RAM + storage; the storage
# axis compares only the max (storage), so the RAM tier (8 vs 16) would leak. RAM = a GB
# value <= 32 (RAM range; storage is 64/128/256/512/1024). One-sided tolerated, both-differ
# rejects (coverage review round 6).
_GB_RE = re.compile(r"(\d+)\s*gb\b", re.I)


def _ram_value(text: str) -> set:
    return {int(m) for m in _GB_RE.findall(text or "") if int(m) <= 32}


def _ram_mismatch(query_name: str, candidate_title: str) -> bool:
    """Both-stated-different RAM tier (8GB vs 16GB, GB values <= 32); one-sided
    tolerated. (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).ram_gb,
        extract_variant_descriptor(candidate_title, None).ram_gb,
    )


# Wave C (re-sweep RS4) — LABEL-AWARE core-count parse: the count's cpu/gpu
# label ("10-Core CPU", "8 Core GPU") is captured when it directly follows the
# "core" word (the real sharafdg/extra spec phrasing); an unlabelled count
# ("12-core 1TB") keeps the old set semantics. Hyphen class covers the
# unicode family (C2, RS-1): this axis parses RAW text, where the live
# sharafdg "8‑core GPU" carries U+2011 — ASCII-only missed it, so the 8-GPU
# vs 10-GPU bin could not discriminate on the real title.
_CORE_COUNT_LABELED_RE = re.compile(
    rf"\b(\d+)\s*(?:[-{_UNICODE_HYPHENS}]\s*)?core\b(?:\s*(cpu|gpu))?", re.I,
)
# Wave D (convergence CV4) — an immediately-PRECEDING cpu/gpu label ("CPU
# 10-core"): anchored to the END of the gap before the count so only the word
# directly in front of it binds.
_CORE_COUNT_PRE_LABEL_RE = re.compile(
    rf"\b(cpu|gpu)\s*[:\-{_UNICODE_HYPHENS}]?\s*$", re.I,
)


def _labeled_core_counts(text: str) -> Tuple[set, set, set]:
    """(cpu, gpu, unlabelled) core-count value sets stated in `text`
    ("10-core CPU / 8-core GPU" -> ({10}, {8}, set()); "12-core" ->
    (set(), set(), {12})).

    Label-BEFORE aware (Wave D, convergence CV4): "CPU 10-core GPU 8-core"
    used to bind the FOLLOWING word, labeling 10 as GPU — the EXACT bin then
    over-rejected against the label-after retailer form. A cpu/gpu word
    immediately PRECEDING the count binds too, PREFERRED over the trailing
    word when both are present. The pre-label is searched ONLY in the gap
    since the previous match's end, so one label word can never bind twice:
    in "10-core CPU 10-core GPU" the "CPU" consumed as count-1's trailing
    label is outside count-2's gap, and count 2 keeps its own "GPU"
    (({10},{10},set()) — the pinned RS4 parse). A count whose trailing label
    was consumed by the preceding preference stays UNLABELLED and keeps the
    tolerant set semantics (fail direction: same bin accepts, a disjoint
    value still rejects)."""
    cpu: set = set()
    gpu: set = set()
    unlabeled: set = set()
    t = text or ""
    prev_end = 0
    for m in _CORE_COUNT_LABELED_RE.finditer(t):
        v = int(m.group(1))
        post = (m.group(2) or "").lower()
        pre_m = _CORE_COUNT_PRE_LABEL_RE.search(t[prev_end:m.start()])
        lab = (pre_m.group(1).lower() if pre_m else "") or post
        if lab == "cpu":
            cpu.add(v)
        elif lab == "gpu":
            gpu.add(v)
        else:
            unlabeled.add(v)
        prev_end = m.end()
    return cpu, gpu, unlabeled


def _core_count_mismatch(query_name: str, candidate_title: str) -> bool:
    """Electronics — True iff both sides state core counts that CONTRADICT.
    One-sided (either side states none at all) is tolerated: the count is spec
    phrasing stripped from identity (BF3), and the chip-tier / model axes
    carry the major discrimination.

    LABEL-AWARE (Wave C, re-sweep RS4): the old flat set-INTERSECTION masked a
    differing GPU bin whenever the CPU count was shared — the real M4 Air
    10c/8g title was accepted for the 10c/10g query (a distinct, pricier
    Apple bin). Semantics now:
      - a label BOTH sides state (cpu-vs-cpu, gpu-vs-gpu) must share a value;
      - an UNLABELLED value keeps the old set semantics against the other
        side's FULL value set (which bin it refers to is unknowable — reject
        only when it appears nowhere, the pre-RS4 pinned behaviour);
      - both sides fully UNLABELLED compare set EQUALITY (a stated count set
        that differs is a different bin; singletons behave exactly as the old
        disjoint check).
    (Wave-2 A1: delegates to the VariantDescriptor — the label-aware logic
    lives in _vd_core_count_mismatch, line-for-line.)"""
    return _vd_core_count_mismatch(
        extract_variant_descriptor(query_name, None).core_counts,
        extract_variant_descriptor(candidate_title, None).core_counts,
    )


# Apple silicon CHIP-TIER axis — "M3" (base) vs "M3 Pro" vs "M3 Max" vs "M3 Ultra" are
# distinct chips at very different prices, but the tier word "Pro"/"Max" collapses into the
# "MacBook Pro" qualifier set (repeated-token set-collapse), so M3 == M3 Pro leaked. Parse
# the (chip-number, tier) and reject when the SAME chip number carries a DIFFERENT tier.
_CHIP_TIER_RE = re.compile(r"\bm(\d)\s*(pro|max|ultra)?\b", re.I)


def _chip_tier(text: str) -> set:
    out = set()
    for num, tier in _CHIP_TIER_RE.findall(_fold_identity(text or "")):
        out.add((num, tier.lower() or "base"))
    return out


def _chip_tier_mismatch(query_name: str, candidate_title: str) -> bool:
    """True iff both name an Apple M-series chip with the SAME number but a DIFFERENT tier
    (M3 base vs M3 Pro). A different chip NUMBER is already caught by identity (m2!=m3).
    (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_chip_tier_mismatch(
        extract_variant_descriptor(query_name, None).chip_tiers,
        extract_variant_descriptor(candidate_title, None).chip_tiers,
    )


# Supplement bare (unit-less) dose — "D3 5000" vs "D3 1000" (the bare 4+-digit number is
# stripped from identity so the unit-less query matches a "5000 IU" listing, but the dose
# value must still be compared). One-sided tolerated, both-stated-different rejects.
_BARE_DOSE_RE = re.compile(r"(?<![a-z])(\d{4,})(?![a-z])", re.I)


def _supplement_bare_dose_mismatch(query_name: str, candidate_title: str) -> bool:
    """Both-stated-different bare (unit-less) dose number (D3 5000 vs D3 1000);
    one-sided tolerated. (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).bare_doses,
        extract_variant_descriptor(candidate_title, None).bare_doses,
    )


# Trailing "+" upgrade-variant axis (category-INDEPENDENT). A word immediately followed by
# "+" (Effaclar Duo+, Vitamin C10+, Galaxy S24+) is a DIFFERENT, upgraded SKU — but the
# tokenizer drops the "+" separator so "Duo+" == "Duo". Compare the set of "+"-marked stems;
# a differing set (one side carries a + the other lacks) is a different product (coverage R8).
_PLUS_VARIANT_RE = re.compile(r"([a-z0-9]{2,})\+")


_PLUS_SPELLED_RE = re.compile(r"([a-z0-9]{2,})\s+plus\b")


def _plus_stems(s: str) -> set:
    # capture BOTH the symbol form ("S24+") and the SPELLED form ("S24 Plus") into one set so
    # they compare EQUAL (same SKU) while the base ("S24") still differs (coverage R9 HIGH).
    s = (s or "").lower()
    return set(_PLUS_VARIANT_RE.findall(s)) | set(_PLUS_SPELLED_RE.findall(s))


def _plus_variant_mismatch(query_name: str, candidate_title: str) -> bool:
    """SET-EQUALITY of '+'-marked stems (symbol + spelled forms unified) — a
    one-sided '+' is a different, upgraded SKU (S24 vs S24+).
    (Wave-2 A1: delegates to the VariantDescriptor; _plus_stems parses the raw
    .lower() text, NOT _fold_identity — the fold strips the '+'.)"""
    return (extract_variant_descriptor(query_name, None).plus_stems
            != extract_variant_descriptor(candidate_title, None).plus_stems)


# Fashion CUT/FIT — a different denim/apparel cut is a SKU (Levis 501 vs 501 Slim). Both-
# stated-different rejects; one-sided is tolerated (the token is also fashion padding).
_FIT_TOKENS = frozenset({
    "slim", "skinny", "relaxed", "regular", "straight", "bootcut", "tapered",
    "loose", "baggy", "oversized", "fitted",
})


def _fit_mismatch(query_name: str, candidate_title: str) -> bool:
    """Both-stated-different apparel cut/fit (501 Slim vs 501 Regular); one-sided
    tolerated. (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).fits,
        extract_variant_descriptor(candidate_title, None).fits,
    )


# Grocery PREP / fat / carbonation — a real SKU axis (instant vs ground coffee, whole vs
# skimmed milk, still vs sparkling water). Both-stated-different rejects; one-sided tolerated.
_GROCERY_PREP_TOKENS = frozenset({
    "instant", "ground", "whole", "skimmed", "semi", "still", "sparkling",
    "smooth", "crunchy", "fine", "coarse", "salted", "unsalted",
})


def _grocery_prep_mismatch(query_name: str, candidate_title: str) -> bool:
    """Both-stated-different grocery prep/fat/carbonation (instant vs ground);
    one-sided tolerated. (Wave-2 A1: delegates to the VariantDescriptor.)"""
    return _vd_disjoint(
        extract_variant_descriptor(query_name, None).preps,
        extract_variant_descriptor(candidate_title, None).preps,
    )
# Skin-type / area / product-class descriptors (NEVER a SKU axis — the SKU axes %/size/
# +active/form are enforced separately). The BENEFIT/effect words (brightening/clarifying/
# volumizing/...) are DELIBERATELY EXCLUDED — they are the variant LINE discriminator for
# mass-market shampoo/cleanser lines, so they must stay distinctive (coverage review:
# padding them collapsed different SKUs). A benefit-line query that omits the line PENDS
# (fail-closed = correct).
_SKINCARE_PADDING = _COSMETIC_FORM_PADDING | frozenset({
    # skin-type / area / class descriptors only (NEVER a SKU axis). The cleanser/cream-TYPE
    # discriminators (foaming/hydrating/moisturizing/gentle/daily/oily/micellar) are
    # DELIBERATELY EXCLUDED — they name the mass-market LINE (CeraVe Foaming vs Hydrating
    # Cleanser are different SKUs), exactly like the benefit words (coverage review CRITICAL).
    "face", "facial", "body", "skin", "fluid", "dermatologist", "tested", "formula",
    "care", "normal", "dry", "oily", "combination", "sensitive", "rough", "bumpy",
    "all", "types", "water", "h2o", "emulsion", "sunscreen", "sunblock",
    "broad", "spectrum",
})
_HAIRCARE_PADDING = _SKINCARE_PADDING | frozenset({
    "hair", "scalp", "anti", "dandruff",
})
_SUPPLEMENT_PADDING = _SUPPLEMENT_CHEM_SYNONYMS | frozenset({
    "high", "absorption", "premium", "pure", "natural", "veg", "vegetarian", "veggie",
    "vegan", "halal", "kosher", "gmo", "gluten", "free", "non", "serving",
    "servings", "dietary", "supplement", "supplements", "formula", "foods",
    "strength", "potency", "grade", "quality", "per", "count", "vit", "vits",
    # multivitamin class noun + 'adult(s)' descriptor (coverage R8: Centrum Silver Adults
    # Multivitamin / One A Day mass-over-rejected). NOTE: 'men'/'women' are DELIBERATELY NOT
    # padding — a gendered SKU (Centrum Men vs Women) is a real variant that must reject.
    # NOTE: bare 'multi' REMOVED (coverage sweep HIGH) — it is the distinctive TYPE word that
    # separates single-source "Collagen Peptides" from a "Multi Collagen Peptides" blend (a
    # different, differently-priced SKU). 'multivitamin'/'multivitamins' stay padding (the
    # Centrum class noun); only the bare 'multi' blend-modifier now rejects when one-sided.
    "multivitamin", "multivitamins", "adult", "adults",
    # marketing / descriptor words a terse query omits (coverage review).
    "extract", "chelated", "buffered", "bioflavonoids", "rosehips", "rose", "hips",
    "billion", "cfu", "rich", "labs", "health", "naturals", "life",
    "nutrition", "support", "micronized", "instantized",
    # NOTE: tier/LINE words (gold/silver/ultimate/platinum/signature/standardized/max/
    # double/mega/extra/standard) are DELIBERATELY NOT padding — they name a distinct
    # product LINE (Centrum Gold vs Silver, ON Gold Standard, Creatine Ultimate), so an
    # ADDED tier token must reject. A symmetric "Gold Standard Whey" query keeps gold/
    # standard on BOTH sides and still matches (coverage review round 4).
    # flavours — ONE-SIDED tolerated (padding) so "ISO100" matches "ISO100 Vanilla", but a
    # both-stated DIFFERENT flavour (Vanilla vs Chocolate) is caught by _flavour_mismatch.
    "vanilla", "chocolate", "strawberry", "berry", "citrus", "orange", "lemon", "mint",
    "cookies", "unflavored", "unflavoured", "plain", "fruit", "punch", "mango", "banana",
    "caramel", "cinnamon", "coconut",
    # default pill forms (one-sided tolerated; alt forms gummy/liquid handled by the
    # supplement FORM axis).
    "softgel", "softgels", "capsule", "capsules", "caplet", "caplets", "tablet",
    "tablets", "pill", "pills", "vcap", "vcaps", "vegcap", "vegcaps", "powder",
})
_CATEGORY_PADDING = {
    "fragrances": _FRAGRANCE_PADDING_TOKENS,
    "electronics": _ELECTRONICS_PADDING,
    "fashion": _FASHION_PADDING,
    "grocery": _GROCERY_PADDING,
    "makeup": _MAKEUP_PADDING,
    "skincare": _SKINCARE_PADDING,
    "haircare": _HAIRCARE_PADDING,
    "supplements": _SUPPLEMENT_PADDING,
}
# Short (<=2-char) fashion model qualifiers KEPT as identity (Samba OG, Dunk Hi/Lo).
# Short (<=2-char) fashion model qualifiers KEPT as distinctive identity tokens (the len>2
# rule would otherwise drop them). "og"/"hi"/"lo" are Nike/adidas line markers (Samba OG,
# Dunk Hi/Lo). NOTE: "se" (Special Edition) is NOT kept here — it is normalized to the
# distinctive token "specialedition" in _identity_tokens_ps so the abbreviation and the
# spelled "Special Edition" UNIFY (coverage re-sweep); a bare kept "se" left the spelled form
# leaking (it was stripped as a colour-edition token).
_FASHION_KEPT_QUALIFIERS = frozenset({"og", "hi", "lo"})
# 2-char skincare/haircare LINE codes kept as identity (CeraVe SA, Skinceuticals AM/PM).
_SKINCARE_LINE_CODES = frozenset({"sa", "am", "pm", "cf"})


def _category_padding(category: Optional[str]) -> frozenset:
    """The per-category NON-identity padding (marketing/descriptive/connectivity/form/
    flavour/brand words) stripped before the superset guard, so a genuine DESCRIPTIVE
    title is not over-rejected while a real variant token still rejects."""
    cat = (category or "").lower()
    return _BASE_NOISE_TOKENS | _CATEGORY_PADDING.get(cat, frozenset())


# ============================================================================
# R1 (genuine-price KPI Wave B3) — adapter RETRIEVAL-TERM LADDER.
#
# Store search APIs (Woo Store API / Magento GraphQL / Salla / Algolia) are
# AND-restrictive: the full canonical name ("Yves Saint Laurent Black Opium
# Eau de Parfum 90ml") returns 0 rows on every live-probed store while the
# model-core term ("Black Opium") returns the EXACT SKU (recon_cascade R1,
# 2026-07-02: theperfumesclub 48.000 BHD in-stock via the Woo Store API;
# klinq 39.38 via magento_graphql_bhd). The ladder tries the FULL name first
# and — ONLY when the response carries ZERO rows — retries ONCE with the core
# term. A response WITH rows (matched or not) never triggers the second
# request (latency pin: +1 HTTP round-trip only on the empty-first-response
# path, still bounded by the cascade's per-source _ADAPTER_TIMEOUT).
#
# The core term strips EXACTLY the axes the acceptance gates re-verify per
# candidate (strict_title_match / _selection_match / select_best):
#   * a LEADING known-brand token run   (candidate_brand / brand-alias folds)
#   * the concentration PHRASE          (the concentration axis)
#   * size/measure tokens               (the ml/oz/GB/count axes) — NOT for
#     electronics/fashion (see the digit pin below)
#   * per-category PADDING + gender     (non-identity by definition)
# so widening RETRIEVAL cannot widen ACCEPTANCE — every retrieved candidate
# is still matched against the ORIGINAL full name by the fail-closed chain.
#
# PINNED (numeric-axis categories electronics/fashion): the core drops ONLY
# brand + padding and NEVER a digit-bearing token ("256GB", "S25", "'07" —
# even a digit-bearing padding word like "5G" is kept), so the core term can
# never blur a numeric SKU axis at retrieval time.
#
# Rollback: ENABLE_ADAPTER_QUERY_LADDER (default ON, read fresh per call).
# OFF -> [full_name] only = byte-identical single-request adapter behaviour.
# ============================================================================

_LADDER_DIGIT_PRESERVING_CATEGORIES = frozenset({"electronics", "fashion"})
# A brand name is at most ~3 words (Yves Saint Laurent / Maison Francis
# Kurkdjian / Parfums de Marly); capping the leading run keeps a brand-vocab
# collision from eating into the product name (Jean Paul Gaultier "Le Male":
# "le" is a brand token via Le Labo, but the run is already 3 deep at "le").
_LADDER_BRAND_RUN_CAP = 3
_ADAPTER_BRAND_TOKEN_VOCAB: Optional[frozenset] = None


def adapter_query_ladder_enabled() -> bool:
    """True iff the adapter retrieval-term ladder is active (default ON). Read
    FRESH per call (the scs._price_cache_bust_enabled read-fresh pattern, with
    exact_gate_enabled's default-ON polarity/parse) so a Railway flip needs no
    redeploy coordination."""
    return os.getenv("ENABLE_ADAPTER_QUERY_LADDER", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def adapter_selection_primary_enabled() -> bool:
    """True iff the direct store-API adapter chains accept on the keystone
    _selection_match with strict_title_match DEMOTED to a fast-accept surface
    check (recon_cascade R2; sibling of ENABLE_ADAPTER_QUERY_LADDER, default
    ON, read FRESH per call so a Railway flip needs no redeploy).

    Scope: ONLY the 6 chains that run _selection_match ALONGSIDE strict
    (woo _match_woo_product / magento _best_match / salla _select_candidate /
    rest_json _title_matches / occ _select_product / unbxd
    _match_unbxd_product — the last wired in Wave B-FIX, over-rejection sweep
    OR-1). A strict PASS keeps the pre-change fast path; a strict FAIL falls
    through to the remaining chain (numbers_match / variant_mismatch /
    counterfeit / accessory / _selection_match + each chain's overlap/stock
    gates) instead of hard-rejecting — strict's RAW tokenization otherwise
    throws away correct rows on pure alias/spacing variance ("90ml" vs
    "90 ml", "YSL" vs the spelled brand via candidate_brand) that
    _identity_tokens_ps collapses. Call sites gate the fallthrough through
    selection_primary_admits (flag + the wrong-brand fence below), NEVER this
    raw flag read alone. The bolo-sitemap strict gate has NO _selection_match
    alongside and keeps strict as its only protection (the PR#13 lesson) —
    NOT in scope.

    HARD-REQUIRES the exact gate: _selection_match returns True (no-op) when
    ENABLE_EXACT_PRICE_GATE is off, so demoting strict then would leave the
    chains gated only by numbers/variant/counterfeit/accessory — a wrong-SKU
    leak class the documented rollback state must never gain. Exact gate OFF
    -> False -> every chain keeps the strict hard pre-gate (byte-identical
    pre-change behaviour)."""
    if not exact_gate_enabled():
        return False
    return os.getenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def variant_descriptor_axes_enabled() -> bool:
    """True iff the Wave-2 VariantDescriptor BACKSTOP-mode NEW axes are active
    (flanker_markers / generation_ints / gender / model-year / prefixed
    clothing-size enforcement at the two weak chokepoints — cache-read
    _cache_price_identity_ok + display is_price_showable). Default OFF, read
    FRESH per call so a Railway flip needs no redeploy (the
    adapter_selection_primary_enabled :5027 idiom).

    HARD-REQUIRES the exact gate: the whole descriptor comparison chain is a
    no-op when ENABLE_EXACT_PRICE_GATE is off (is_exact_match / _selection_match
    / _backstop_identity_ok all early-return True), so enabling the new backstop
    axes then would either do nothing or, worse, gain a gate the documented
    rollback state must never have. Exact gate OFF -> False -> backstop_identity_verdict
    returns the EXACT legacy pair (_backstop_identity_ok and not
    _category_type_added), byte-identical pre-change behaviour."""
    if not exact_gate_enabled():
        return False
    return os.getenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def selection_primary_admits(
    query_name: str, candidate_title: str, *,
    candidate_brand: str = "", category: Optional[str] = None,
) -> bool:
    """True iff a strict_title_match FAILURE may fall through to the
    selection-primary chain (the Wave B4 demotion) for THIS candidate — the
    flag gate + the WRONG-BRAND FENCE (Wave B-FIX; coverage leak sweep L1
    CRITICAL + L2 HIGH).

    strict's brand requirement was the ONLY gate that kept the QUERY's brand
    word required when that word is _category_padding-STRIPPABLE ("adidas"/
    "puma"/"vans" are fashion padding; manufacturers are electronics padding):
    _selection_match drops it from q_core, so after the demotion a
    same-model-word CROSS-BRAND row ("Golden Goose Superstar White Sneakers"
    under an "Adidas Superstar White" query) sailed through every demoted
    chain and cached 7d-genuine. On the fallthrough, require BRAND EVIDENCE:

      (a) candidate_brand NON-EMPTY -> it must alias-equal a query token
          (folded via _fold_identity/normalize_words, _BRAND_ALIAS_GROUPS-
          expanded so a spelled house label still releases an abbreviated
          query). A stated CONTRADICTING brand is definitive wrong-brand
          evidence -> reject. A pure-digit label (a magento option-id leak)
          asserts no brand -> treated as NO signal, falls to (b).
      (b) NO candidate-brand signal (woo/salla/rest_json/unbxd rows) -> for
          FASHION the query's padding-strippable brand token must appear
          folded in the title (the L2 brandless class: with the brand absent
          from BOTH the title and the row, correct and cross-brand rows are
          indistinguishable — keep strict's brand requirement). Electronics
          keeps the B4 brand-omitted unlock ("iPad Air M2 128GB", no
          "Apple"): model-line tokens are brand-unique, and the leak sweep
          probed that cross-brand space naturally rejected.

    Queries with NO padding-strippable brand token pass untouched — for every
    other brand word the keystone's own subset check keeps it required
    (candidate_brand only ever releases the candidate's OWN brand), so the
    klinq brand-omitted fragrance unlock and the spaced-unit unlocks are
    unaffected (both pinned in tests/test_selection_primary_acceptance.py).
    Flag OFF (or exact gate OFF) -> False -> the strict hard pre-gate,
    byte-identical pre-change behaviour.

    Wave C (re-sweep RS2 + RS7): the fence logic itself is CENTRALIZED in
    _brand_evidence_ok — this wrapper only adds the selection-primary flag
    gate. The shared consumers (extract_price_from_shopping / select_best /
    should_cache_price) call the helper directly, so the fence can never
    fork/drift between the adapter fallthroughs and the no-adapter paths.
    """
    if not adapter_selection_primary_enabled():
        return False
    return _brand_evidence_ok(
        query_name, candidate_title,
        candidate_brand=candidate_brand, category=category,
    )


def _brand_evidence_ok(
    query_name: str, candidate_title: str, *,
    candidate_brand: str = "", category: Optional[str] = None,
) -> bool:
    """THE BF1 wrong-brand fence, centralized (Wave C, re-sweep RS2 + RS7 +
    kpiE2E RS-2). Semantics as documented on selection_primary_admits, with
    the RS2 tightening: the candidate's stated brand is compared against the
    QUERY's padding-BRAND token(s) ONLY — alias-expanded on BOTH sides — never
    against the full query token set. Pre-RS2 a compound/junk brand FIELD
    ("Vans Suede", "Classic") re-opened the L1 wrong-brand leak by
    intersecting a NON-brand query word ('suede'/'classic'), the exact chains
    BF1 closed.

    Bounded exactly like BF1: only queries whose brand token is
    padding-strippable (_MANUFACTURER_NOISE ∩ category padding) are fenced;
    path (b) — no candidate-brand signal — requires the brand folded in the
    TITLE for FASHION only (electronics keeps the B4 brand-omitted unlock).
    exact gate OFF → True (no-op; the callers are themselves gate-scoped, and
    the selection-primary wrapper hard-requires the gate already)."""
    if not exact_gate_enabled():
        return True
    cat = (category or "").lower()
    if cat == "other":
        # Mirror _selection_match's explicit-"other" re-inference so the fence
        # uses the same padding the keystone will.
        cat = (_infer_category_from_query(query_name) or cat).lower()
    padding_brands = _MANUFACTURER_NOISE & _category_padding(cat)
    if not padding_brands:
        return True
    q_toks = normalize_words(_fold_identity(query_name or ""))
    q_brand = q_toks & padding_brands
    if not q_brand:
        return True
    # RS2 — the evidence target is the query's BRAND token(s), alias-expanded.
    q_brand_exp = set(q_brand)
    for _group in _BRAND_ALIAS_GROUPS:
        if q_brand_exp & _group:
            q_brand_exp = q_brand_exp | _group
    cand_toks = {
        w for w in normalize_words(_fold_identity(candidate_brand or ""))
        if len(w) > 2 and not w.isdigit()
    }
    if cand_toks:
        for _group in _BRAND_ALIAS_GROUPS:
            if cand_toks & _group:
                cand_toks = cand_toks | _group
        return bool(cand_toks & q_brand_exp)
    if cat != "fashion":
        return True
    t_toks = normalize_words(_fold_identity(candidate_title or ""))
    return bool(q_brand_exp & t_toks)


def _ladder_fold_token(tok: str) -> str:
    """Folded MEMBERSHIP form of one whitespace token (lowercase, NFKD
    diacritic-fold, apostrophe fold, edge-punctuation + hyphen strip — the
    normalize_words treatment applied token-wise) so the ORIGINAL token can be
    emitted verbatim in the core term while set-membership checks use the fold."""
    t = _APOSTROPHES_RE.sub("", tok or "").lower()
    t = "".join(
        c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)
    )
    return t.strip(",.()&:;'\"!?").replace("-", "")


def _adapter_brand_token_vocab() -> frozenset:
    """Folded brand-WORD vocabulary for the ladder's leading-run strip, built
    lazily ONCE from the existing brand tables (LUXURY_BRAND_KEYWORDS,
    FRAGRANCE_BRAND_KEYWORDS, _MANUFACTURER_NOISE, _BRAND_ALIAS_GROUPS) so the
    ladder can never drift from the matcher's own brand knowledge. Leading-run
    ONLY at the call site — a mid-name collision ("Mon Paris", "Burberry
    London") is never stripped."""
    global _ADAPTER_BRAND_TOKEN_VOCAB
    if _ADAPTER_BRAND_TOKEN_VOCAB is None:
        toks: set = set()
        for phrase in set(LUXURY_BRAND_KEYWORDS) | set(FRAGRANCE_BRAND_KEYWORDS):
            for w in str(phrase).split():
                f = _ladder_fold_token(w)
                if f:
                    toks.add(f)
        toks.update(_MANUFACTURER_NOISE)
        for group in _BRAND_ALIAS_GROUPS:
            toks.update(group)
        _ADAPTER_BRAND_TOKEN_VOCAB = frozenset(toks)
    return _ADAPTER_BRAND_TOKEN_VOCAB


def build_adapter_search_terms(
    full_name: str, category: Optional[str] = None,
) -> List[str]:
    """The retrieval-term ladder for the direct store-API adapters:
    ``[full_name]`` or ``[full_name, core_term]``.

    Semantics (pinned by tests/test_adapter_query_ladder.py):
      * terms[0] is ALWAYS the untouched ``full_name`` (flag-OFF byte-identity).
      * core = full_name minus a LEADING known-brand run, minus the
        concentration phrase + size/measure tokens (EXCEPT electronics/fashion,
        where a digit-bearing token is NEVER dropped), minus per-category
        padding/gender words — exactly the axes the acceptance gates re-verify
        per candidate, so widening retrieval cannot widen acceptance.
      * deduped (``[full_name]`` when the core equals the full name); an empty
        or single-char core is never emitted.
      * flag OFF (ENABLE_ADAPTER_QUERY_LADDER) -> ``[full_name]`` only.

    Adapter contract: try terms[0]; ONLY a ZERO-ROW response tries terms[1]; a
    response WITH rows — matched or not — never triggers the second request.
    """
    if not adapter_query_ladder_enabled():
        return [full_name]
    if not full_name or not isinstance(full_name, str):
        return [full_name]

    cat = (category or "").lower()
    if cat in ("", "other"):
        # Mirror _selection_match's explicit-"other" re-inference so the
        # category-scoped strips below run on the right axes.
        cat = _infer_category_from_query(full_name) or cat
    digit_preserving = cat in _LADDER_DIGIT_PRESERVING_CATEGORIES

    src = full_name[:_MATCH_INPUT_CAP]  # ReDoS bound, mirrors the matchers
    if not digit_preserving:
        for pat, _label in _CONCENTRATION_PATTERNS:
            src = pat.sub(" ", src)
        src = _IDENTITY_MEASURE_STRIP_RE.sub(" ", src)

    drop = _category_padding(cat)
    if cat in _FRAGRANCE_BEAUTY_CATEGORIES:
        # The matcher strips gender markers from identity for these categories
        # (_GENDER_IDENTITY_STRIP); fragrances already carry them in padding.
        drop = drop | _GENDER_IDENTITY_STRIP

    tokens = src.split()
    folded = [_ladder_fold_token(t) for t in tokens]

    # Leading known-BRAND run (capped; punctuation-only tokens like "&" inside
    # the run don't count toward the cap). Leading-run only — a brand-vocab
    # word later in the name is product identity ("Mon Paris") and stays.
    vocab = _adapter_brand_token_vocab()
    idx = 0
    brand_words = 0
    while idx < len(tokens) and brand_words < _LADDER_BRAND_RUN_CAP:
        f = folded[idx]
        if not f:
            idx += 1  # punctuation-only token inside a brand run ("&")
            continue
        if f in vocab:
            idx += 1
            brand_words += 1
            continue
        break
    if brand_words == 0:
        idx = 0  # no brand found — keep any leading punctuation-only tokens

    core_tokens: List[str] = []
    for tok, f in zip(tokens[idx:], folded[idx:]):
        if not f:
            continue
        if digit_preserving and any(c.isdigit() for c in f):
            # PINNED: electronics/fashion NEVER drop a digit-bearing token —
            # not even a digit-bearing padding word ("5G").
            core_tokens.append(tok)
            continue
        if f in drop:
            continue
        core_tokens.append(tok)

    core = " ".join(core_tokens).strip()
    if len(core) < 2:
        return [full_name]  # never emit an empty / single-char core
    if core.lower() == " ".join(full_name.split()).lower():
        return [full_name]  # dedupe — the core adds nothing
    return [full_name, core]


# ============================================================================
# === VARIANT DESCRIPTOR (Wave-2) ===
#
# Phase-A EXTRACT-ONCE formalization (design lane R1/R2/R5 STEP 1,
# docs/investigations/2026-07-03-wave2-recon/descriptor-design.json).
#
# Every axis the matcher discriminates on already existed as a pure extractor
# primitive that was re-parsed up to ~5x per candidate across
# strict_title_match / _axis_mismatch / _selection_match / should_cache_price /
# is_price_showable. This section extracts each axis ONCE per
# (text, category, brand, gate) into a frozen VariantDescriptor (memoized), and
# encodes TODAY'S comparison semantics in ONE decision function
# (descriptor_verdict) with three modes:
#
#   SELECTION — the _selection_match contract (axes + leak-direction subset +
#               variant-add superset + per-category padding + tolerances)
#   EXACT     — the is_exact_match contract (axes + identity set-EQUALITY)
#   BACKSTOP  — the _backstop_identity_ok contract (axis-only,
#               strict_extras=False — brand-independent, never false-pends a
#               descriptive title; the chokepoints pair it with the SEPARATE
#               _category_type_added bounded check)
#
# BEHAVIOR-IDENTICAL BY CONSTRUCTION: extraction calls the EXISTING extractor
# primitives verbatim with the exact input form (capped/uncapped/folded) each
# legacy call site used; the comparator table replicates each per-axis
# predicate field-for-field. The golden corpus
# (tests/test_variant_descriptor_golden.py, 1149 pinned verdicts) is the
# equivalence gate. NO new flag: every consumer already no-ops when
# ENABLE_EXACT_PRICE_GATE is off, so flag-OFF byte-identity is inherited.
#
# Phase-A scope note: the NEW Phase-B fields (flanker_markers,
# generation_ints) are deliberately ABSENT — this phase formalizes, it does
# not change any verdict.
#
# CAPPED-PARSE SEMANTICS (Phase-A closure ruling, ACCEPTED): the descriptor
# parses the _MATCH_INPUT_CAP(512)-capped text for EVERY axis. The >512-char
# DIRECT-CALL surfaces that legacy code parsed UNCAPPED — the
# _category_type_added helper pair at the display/cache-read chokepoints
# (is_price_showable :1425 / scs._cache_price_identity_ok) and
# _concentration_mismatch (:1634) — now deliberately see capped text too.
# This UNIFIES the ReDoS envelope across the whole matcher chain and
# SUPERSEDES the legacy uncapped parsing on pathological (>512-char) inputs.
# The cap is PARTIAL-TOKEN-SAFE (a mid-token boundary slice strips the
# trailing fragment instead of manufacturing a phantom token — see
# _build_variant_descriptor). Pinned by the >512 `capped_semantics` corpus
# rows in tests/data/variant_descriptor_golden_corpus.json.
#
# MEMO-KEY FAN-OUT (deliberate): the standalone wrappers
# (_concentration_mismatch, _flagship_concentration_added,
# _supplement_type_added, _supplement_form_added) call
# extract_variant_descriptor with category=None while the gate chain passes
# the RESOLVED category — so the same text can occupy TWO lru slots (one per
# category key). Benchmarked cheaper than the legacy per-call re-parse (the
# extra slot is one small frozen dataclass; unifying the key would force
# threading category through wrapper signatures frozen by their callers).
# Tests must never rely on memo persistence across tests —
# tests/conftest.py clears the lru per-test (B1.0 memo-staleness fixture).
#
# PHASE-B1 NEW FIELDS (extraction ALWAYS ON — harmless pure fields; the
# ENFORCEMENT is flag-gated behind variant_descriptor_axes_enabled at the
# BACKSTOP consumers only):
#   flanker_markers  FRAGRANCES-SCOPED curated symmetric concentration-flanker
#                    words (Sauvage Elixir / Good Girl Supreme). CURATED and
#                    BOUNDED on purpose: only unambiguous flanker labels, NEVER
#                    a base-name word (private/oud/noir/nuit/sport) — "Tom Ford
#                    Private Blend Oud Wood" IS "Oud Wood".
#   generation_ints  ELECTRONICS-SCOPED bare generation ints 1-4 that FOLLOW a
#                    model-noun token (AirPods Pro 2 / iPad Pro 4). The
#                    adjacency bound keeps it off "Dual SIM 2 Nano" / "2 Year
#                    Warranty" / "USB 3" / "Type 2 cable".
# ============================================================================

# --- flanker_markers (fragrances) -------------------------------------------
# The BOUNDED, curated set of unambiguous concentration-flanker words. These
# create a DISTINCT SKU/price ("Dior Sauvage" vs "Dior Sauvage Elixir",
# "Good Girl" vs "Good Girl Supreme") yet are NOT extract_concentration values
# (so the concentration axis + the flagship-add check never see them). Diacritic
# folding is inherited from _fold_identity (NFKD) so "Supreme" catches
# "Supreme"/"Supreme" alike; extracted from fold_tokens. Membership is STRICT:
# adding a base-name word here would over-reject correct base products
# (Oud Wood / Bleu de Chanel Noir), so this list is intentionally minimal.
_FLANKER_MARKER_TOKENS = frozenset({
    "elixir", "supreme", "absolu", "intense", "extreme",
})

# --- generation_ints (electronics) ------------------------------------------
# A bare standalone digit 1-4 is a GENERATION marker ONLY when it immediately
# follows a model-noun token in the identity stream (AirPods Pro *2*, iPad Air
# *4*, Echo Dot *3*). The adjacency condition is the ReDoS-free bound that keeps
# it OFF "Dual SIM 2 Nano" / "2 Year Warranty" / "USB 3" / "Type 2 cable".
_GENERATION_MODEL_NOUNS = frozenset({
    "pro", "max", "air", "mini", "series", "gen", "generation",
    "watch", "pixel", "echo", "dot", "pencil", "airpods",
})
# Ordinal generation forms ("2nd generation", "3rd gen") folded to the bare int.
_GENERATION_ORDINAL_RE = re.compile(
    r"\b([1-4])(?:st|nd|rd|th)\s+gen(?:eration)?\b", re.I,
)
# PARENTHETICAL ordinal-generation annotation ("(4th generation)"/"(2nd Gen)").
# This is RELEASE PADDING (exactly like a "(2025)" year annotation), NOT a
# discriminator, so the backstop ADD-check ignores it (B1-FIX ruling A1). Only
# an INLINE bare model-noun-adjacent int counts as a generation discriminator.
_GENERATION_ANNOTATED_RE = re.compile(
    r"\(\s*([1-4])(?:st|nd|rd|th)\s+gen(?:eration)?\s*\)", re.I,
)
# B1-FIX ruling A2: a bare inline digit 1-4 that is IMMEDIATELY FOLLOWED by a
# quantity/spec/measurement noun is a quantity, not a generation ("3 Quart",
# "4 Ah", "2 Meter", "2 Pack"). Curated; extend as sweeps reveal.
_GENERATION_QUANTITY_NOUNS = frozenset({
    "pack", "piece", "pieces", "pcs", "count", "ct", "meter", "metre", "m",
    "strap", "straps", "port", "ports", "player", "filter", "filters", "year",
    "years", "quart", "qt", "qts", "litre", "liter", "l", "ah", "mah", "atm",
    "bar", "camera", "cameras", "lens", "lenses", "ply", "mm", "cm", "inch",
    "in", "watt", "w", "kw", "gb", "tb", "hz", "khz", "ghz", "seat", "seats",
    "door", "doors",
    # B1-FIX2: descriptive count/marketing nouns a bare digit QUANTIFIES in real
    # titles ("... 2 Colors", "... 2 Sensors", "... 2 Ear Tips"). Extending this
    # set can ONLY make the generation axis fire LESS (more tolerance), so it can
    # never create a NEW over-rejection. NONE of these is a model-variant / spec /
    # color-name token (classic/plus/max/pro/mini/wifi/cellular/charcoal/... stay
    # OUT) so no real generation leak reopens (the canonical leaks are
    # title-terminal or non-count-suffixed: Pro 2 / Dot 3 / Pencil 2 / Watch 4
    # Classic / Air 4 Wi-Fi).
    "colors", "colours", "color", "colour", "sensors", "sensor", "tips", "tip",
    "options", "option", "bands", "band", "sizes", "remotes", "remote",
    "speakers", "speaker", "cores", "core", "buttons", "button", "modes", "mode",
    "blades", "blade", "heads", "head", "nibs", "nib", "refills", "refill",
    "cartridges", "cartridge", "pods", "pod", "cups", "cup", "bulbs", "bulb",
    "keys", "key", "zones", "zone", "pairs", "pair", "sets", "set", "ear",
    "buds", "bud", "chargers", "charger", "cables", "adapters", "adapter",
    "stands", "stand", "mounts", "mount", "brushes", "brush", "rolls", "roll",
    "sheets", "sheet", "packs",
})


def _flanker_markers_of(fold_tokens: FrozenSet[str]) -> FrozenSet[str]:
    """The curated concentration-flanker words present in `fold_tokens`
    (fragrances-scoped; the CONSUMER checks the category)."""
    return frozenset(fold_tokens & _FLANKER_MARKER_TOKENS)


def _generation_ints_of(text: str) -> FrozenSet[int]:
    """INLINE bare generation ints 1-4 in `text` — the DISCRIMINATOR set the
    backstop ADD-check enforces (electronics-scoped; the CONSUMER checks the
    category).

    A bare digit 1-4 counts ONLY when (a) the PRECEDING identity token is a
    model-noun AND (b) the FOLLOWING token is NOT a quantity/spec noun
    (B1-FIX A2 — "Apple Watch 2 Pack"/"Series 2 Meter" are quantities, not
    generations). Inline ordinal "2nd gen" forms count; the PARENTHETICAL
    "(2nd generation)" annotation form does NOT (B1-FIX A1 — that is release
    padding, captured by _generation_ints_annotated_of instead). The
    _MATCH_INPUT_CAP cap is applied by the descriptor builder before calling
    this (text is already capped)."""
    low = (text or "").lower()
    out = set()
    # Inline ordinal ("Nth gen"), but NOT the parenthetical "(Nth gen)" form —
    # strip the annotated occurrences before scanning so they don't leak in.
    inline_ord = _GENERATION_ANNOTATED_RE.sub(" ", low)
    for m in _GENERATION_ORDINAL_RE.finditer(inline_ord):
        out.add(int(m.group(1)))
    words = re.findall(r"[a-z0-9]+", low)
    for i in range(1, len(words)):
        w = words[i]
        if w in ("1", "2", "3", "4") and words[i - 1] in _GENERATION_MODEL_NOUNS:
            nxt = words[i + 1] if i + 1 < len(words) else None
            if nxt in _GENERATION_QUANTITY_NOUNS:
                continue  # a quantity/spec noun, not a generation
            out.add(int(w))
    return frozenset(out)


def _generation_ints_annotated_of(text: str) -> FrozenSet[int]:
    """The PARENTHETICAL "(Nth generation)"/"(Nth gen)" annotation ints —
    informational release padding, IGNORED by the backstop ADD-check (B1-FIX
    A1). Extracted so the descriptor keeps the axis visible for diagnostics/
    future structured-code work without letting it discriminate."""
    low = (text or "").lower()
    return frozenset(int(m.group(1)) for m in _GENERATION_ANNOTATED_RE.finditer(low))


@dataclass(frozen=True)
class VariantDescriptor:
    """The extract-once product-variant identity of ONE side (query or
    candidate title), per descriptor-design.json R1.

    Every field None/empty == UNKNOWN (the axis is unstated on this side) —
    the comparator table decides per axis whether UNKNOWN is tolerated
    (one-sided axes), required (fail-closed query-stated axes) or compared
    (set-equality axes).

    R1's single `size` field is SPLIT into the three representations today's
    comparators actually consume (behavior-identity beats a single typed
    scalar): `size_ml_snapped` (extract_size_ml_any — the fragrance
    standard-bottle snap basis), `size_ml_raw` (_size_ml_raw — the
    non-fragrance raw+5%-tolerance basis) and `weights_volumes`
    (_weights_volumes — the g/ml typed set with cross-base fail-closed
    semantics). A convenience `size` property exposes the R1 typed view.

    `structured_code` is "" in Phase A: structured codes are STAMPED by
    adapters onto the price dict (algolia_service.py:532), never parsed from
    title text. TODO(Wave-2 Phase B, R1 provenance): structured-first stamping
    — a retailer-structured brand/code/size field wins over the title parse
    for that axis and marks provenance='structured'.
    """
    # --- identity ---
    identity_core: FrozenSet[str]        # _identity_tokens_ps(text, brand, category)
    brand_tokens: FrozenSet[str]         # brand words + hyphen-collapsed + alias groups
    structured_code: str                 # "" (adapter-stamped, not text-derived)
    model_codes: FrozenSet[str]          # _luxottica_model_codes (0-prefix-folded)
    # --- numeric / typed axes ---
    concentration: Optional[str]         # extract_concentration (EDP/EDT/Parfum/...)
    size_ml_snapped: Optional[int]       # extract_size_ml_any (fragrance snap basis)
    size_ml_raw: Optional[float]         # _size_ml_raw (raw oz->ml, non-fragrance basis)
    weights_volumes: FrozenSet[Tuple[float, str]]  # _weights_volumes {(value,'g'|'ml')}
    lb_present: bool                     # _LB_TOKEN_RE (arms the lb 1% headline tolerance)
    storage_gb: Optional[float]          # _match_storage_gb (MAX = storage-not-RAM)
    ram_gb: FrozenSet[int]               # _ram_value (GB values <= 32)
    count: Optional[float]               # extract_count (caps/tablets/... headline max)
    doses: FrozenSet[Tuple[float, str]]  # _doses {(value, 'mg'|'mcg'|'iu')}, comma=thousands
    bare_doses: FrozenSet[int]           # _BARE_DOSE_RE over the folded text (4+ digits)
    percents: FrozenSet[float]           # _percents (% active strength)
    spfs: FrozenSet[int]                 # _SPF_RE values
    packs: FrozenSet[float]              # _packs (grocery pack counts)
    shoe_sizes: FrozenSet[Tuple[str, float]]  # _shoe_sizes {(system, value)}
    clothing_sizes: FrozenSet[str]       # _clothing_sizes_in (apparel S/M/L/XL...)
    inches: FrozenSet[float]             # _INCH_RE values (the both-stated axis)
    inch_tokens: FrozenSet[str]          # _inch_digit_tokens on the UNCAPPED text
    chip_tiers: FrozenSet[Tuple[str, str]]    # _chip_tier {(chip_number, tier)}
    core_counts: Tuple[FrozenSet[int], FrozenSet[int], FrozenSet[int]]  # (cpu, gpu, unlabelled)
    qualifiers: FrozenSet[str]           # _quals_in vs the category's variant qualifiers
    plus_stems: FrozenSet[str]           # _plus_stems (symbol + spelled '+' variants)
    # --- categorical axes ---
    gender: Optional[str]                # _gender_of ('men'/'women'/None) STRICT — asymmetry + identity
    gender_pronoun: Optional[str]        # _pronoun_gender_of (him/her; contradiction axis ONLY; flag-gated, None flag-OFF)
    form: Optional[str]                  # _extract_product_form (brand-stripped)
    flavours: FrozenSet[str]             # fold tokens & _FLAVOUR_TOKENS
    finishes: FrozenSet[str]             # fold tokens & _MAKEUP_FINISH_TOKENS
    materials: FrozenSet[str]            # fold tokens & _MATERIAL_TOKENS
    fits: FrozenSet[str]                 # fold tokens & _FIT_TOKENS
    preps: FrozenSet[str]                # fold tokens & _GROCERY_PREP_TOKENS
    vitamin_letters: FrozenSet[str]      # _VITAMIN_LETTER_RE on the capped raw text
    supplement_types: FrozenSet[str]     # fold tokens & _SUPPLEMENT_TYPE_TOKENS
    supplement_alt_forms: FrozenSet[str]      # fold tokens & _SUPPLEMENT_ALT_FORMS
    supplement_default_forms: FrozenSet[str]  # fold tokens & _SUPPLEMENT_DEFAULT_FORMS
    colors: FrozenSet[str]               # fold tokens & _COLOR_EDITION_TOKENS
    year_annotations: FrozenSet[str]     # _annotation_year_tokens on the UNCAPPED text
    condition: bool                      # fold tokens & _CONDITION_TOKENS (non-new stated)
    # --- tolerance-family fields (SELECTION-mode title-side tolerances) ---
    construction_tolerated: FrozenSet[str]  # _fashion_construction_tolerated_for (UNCAPPED)
    eyewear_annotations: FrozenSet[str]  # title-derived colorway/lens tokens (code-gated at verdict)
    # --- Phase-B1 NEW axes (extraction always-on; ENFORCEMENT flag-gated at backstops) ---
    flanker_markers: FrozenSet[str]      # _flanker_markers_of (fragrances curated flanker words)
    generation_ints: FrozenSet[int]      # _generation_ints_of (electronics INLINE model-noun-adjacent 1-4; the ADD-check discriminator)
    generation_ints_annotated: FrozenSet[int]  # _generation_ints_annotated_of (parenthetical "(Nth gen)" release padding; IGNORED by ADD-check)
    # --- normalized token blob (whole-set subtractions: supplement type-add) ---
    fold_tokens: FrozenSet[str]          # re.findall([a-z0-9]+, _fold_identity(capped))

    @property
    def size(self) -> Optional[Tuple[float, str]]:
        """R1's typed (value, unit_class) convenience view, size_variant_token
        precedence (storage > ml > count > weight/volume). INFORMATIONAL ONLY —
        the comparators consume the split fields above."""
        if self.storage_gb:
            return (self.storage_gb, "gb")
        if self.size_ml_raw is not None:
            return (float(self.size_ml_raw), "ml")
        if self.count:
            return (self.count, "ct")
        if self.weights_volumes:
            value, base = max(self.weights_volumes)
            return (value, base)
        return None


def _eyewear_annotation_tokens(text: str) -> set:
    """The TITLE-DERIVED eyewear annotation tokens of `text` (colorway
    sub-tokens adjacent to a Luxottica model code, lens-size annotations, the
    'lens size' phrase words) — the dynamic part of _eyewear_code_tolerated_for,
    split out so the descriptor extracts it once per side and the legacy helper
    delegates (single implementation, no drift). The static
    _EYEWEAR_DESCRIPTOR_TOKENS and the query-code gate stay at the CONSUMER
    (they are pair-conditional)."""
    low = (text or "").lower()
    if len(low) > _MATCH_INPUT_CAP:
        low = low[:_MATCH_INPUT_CAP]
    out: set = set()
    for m in _LUXOTTICA_COLORWAY_ADJ_RE.finditer(low):
        for part in m.group(1).split("/"):
            if part:
                out.add(part)
        if m.group(2):
            out.add(m.group(2))
    for n in _EYEWEAR_LENS_MM_RE.findall(low):
        out.add(n)
        out.add(f"{n}mm")
    if _EYEWEAR_LENS_PHRASE_RE.search(low):
        out.update(("lens", "size"))
    return out


def _build_variant_descriptor(text: str, category: Optional[str],
                              brand: str) -> VariantDescriptor:
    """Run every existing extractor primitive ONCE over `text` and freeze the
    result. Input forms replicate the legacy call sites exactly:
      - axis extractors get the _MATCH_INPUT_CAP-capped text (the cap
        _axis_mismatch applied before every per-axis predicate, ReDoS guard);
      - _identity_tokens_ps / _luxottica_model_codes get the raw text (they
        self-cap at the same 512);
      - the SELECTION tolerance helpers (_annotation_year_tokens,
        _inch_digit_tokens, _fashion_construction_tolerated_for) get the raw
        UNCAPPED text — _selection_match always called them uncapped.
    None input is treated as "" (the extractors' own `text or ""` idiom).

    PARTIAL-TOKEN-SAFE CAP (Phase-A closure, B1.0): when the 512-byte boundary
    slices MID-TOKEN, a plain slice can MANUFACTURE a token the text never
    contained (drift-reviewer repro: a 531-char title whose "Parfumerie"
    sliced at byte 512 left a trailing "Parfum" — a phantom flagship
    concentration). If the char AT the boundary and the last capped char are
    both non-whitespace, the trailing partial fragment is stripped so a sliced
    token contributes NOTHING instead of a phantom axis value.
    _identity_tokens_ps / _luxottica_model_codes keep their own plain
    self-caps untouched (identity tokens are subset/equality-compared — a
    trailing partial token cannot manufacture an AXIS there)."""
    text = text or ""
    if len(text) > _MATCH_INPUT_CAP:
        capped = text[:_MATCH_INPUT_CAP]
        if not text[_MATCH_INPUT_CAP].isspace() and not capped[-1].isspace():
            _parts = capped.rsplit(None, 1)
            if len(_parts) == 2:  # only when a whitespace boundary exists to cut at
                capped = _parts[0]
    else:
        capped = text
    fold_full = _fold_identity(capped)
    cat = (category or "").lower()
    # Wave-2 B2b (C2, flag-gated): fold a supplement nutrient-name's SPACED digit form to the
    # glued form on fold_full too, so the fold_tokens-derived axes (supplement_types /
    # supplement constituents) see "b 12" as "b12" — matching the identity-token fold in
    # _identity_tokens_ps. Kept CONSISTENT with that site (same helper, same supplement scope,
    # same 1-2-digit bound) so identity_core and fold_tokens never disagree. Flag-OFF stays
    # byte-identical; the axes flag is in the lru memo key so a flip never serves a stale
    # descriptor.
    if cat == "supplements" and variant_descriptor_axes_enabled():
        fold_full = _apply_nutrient_digit_fold(fold_full)
    fold_tokens = frozenset(re.findall(r"[a-z0-9]+", fold_full))

    # Brand token set — the same computation _identity_tokens_ps runs
    # internally (plain words + hyphen-collapsed multiword form + alias-group
    # expansion). Informational on the descriptor: identity_core already had
    # the brand subtracted by _identity_tokens_ps itself.
    brand_words = set(normalize_words(_fold_identity(brand))) if brand else set()
    if brand and " " in brand.strip():
        brand_words |= {re.sub(r"\s+", "", _fold_identity(brand))}
    for _group in _BRAND_ALIAS_GROUPS:
        if brand_words & _group:
            brand_words |= set(_group)

    quals_set = _CATEGORY_VARIANT_QUALIFIERS.get(cat, frozenset())
    cpu, gpu, unlabeled = _labeled_core_counts(capped)

    return VariantDescriptor(
        identity_core=frozenset(_identity_tokens_ps(text, brand, category)),
        brand_tokens=frozenset(brand_words),
        structured_code="",  # Phase A: adapter-stamped only (see class docstring TODO)
        model_codes=frozenset(_luxottica_model_codes(text)),
        concentration=extract_concentration(capped),
        size_ml_snapped=extract_size_ml_any(capped),
        size_ml_raw=_size_ml_raw(capped),
        weights_volumes=frozenset(_weights_volumes(capped)),
        lb_present=bool(_LB_TOKEN_RE.search(capped)),
        storage_gb=_match_storage_gb(capped),
        ram_gb=frozenset(_ram_value(capped)),
        count=extract_count(capped),
        doses=frozenset(_doses(capped)),
        bare_doses=frozenset(int(m) for m in _BARE_DOSE_RE.findall(fold_full)),
        percents=frozenset(_percents(capped)),
        spfs=frozenset(int(m) for m in _SPF_RE.findall(capped)),
        packs=frozenset(_packs(capped)),
        shoe_sizes=frozenset(_shoe_sizes(capped)),
        clothing_sizes=frozenset(_clothing_sizes_in(capped)),
        inches=frozenset(float(m) for m in _INCH_RE.findall(capped)),
        inch_tokens=frozenset(_inch_digit_tokens(text)),
        chip_tiers=frozenset(_chip_tier(capped)),
        core_counts=(frozenset(cpu), frozenset(gpu), frozenset(unlabeled)),
        qualifiers=frozenset(_quals_in(capped, quals_set)) if quals_set else frozenset(),
        plus_stems=frozenset(_plus_stems(capped)),
        gender=_gender_of(capped),
        gender_pronoun=_pronoun_gender_of(capped),
        form=_extract_product_form(capped, brand),
        flavours=fold_tokens & _FLAVOUR_TOKENS,
        finishes=fold_tokens & _MAKEUP_FINISH_TOKENS,
        materials=fold_tokens & _MATERIAL_TOKENS,
        fits=fold_tokens & _FIT_TOKENS,
        preps=fold_tokens & _GROCERY_PREP_TOKENS,
        vitamin_letters=frozenset(m.lower() for m in _VITAMIN_LETTER_RE.findall(capped)),
        supplement_types=fold_tokens & _SUPPLEMENT_TYPE_TOKENS,
        supplement_alt_forms=fold_tokens & _SUPPLEMENT_ALT_FORMS,
        supplement_default_forms=fold_tokens & _SUPPLEMENT_DEFAULT_FORMS,
        colors=fold_tokens & _COLOR_EDITION_TOKENS,
        year_annotations=frozenset(_annotation_year_tokens(text)),
        condition=bool(fold_tokens & _CONDITION_TOKENS),
        construction_tolerated=frozenset(_fashion_construction_tolerated_for(text)),
        eyewear_annotations=frozenset(_eyewear_annotation_tokens(text)),
        flanker_markers=_flanker_markers_of(fold_tokens),
        generation_ints=_generation_ints_of(capped),
        generation_ints_annotated=_generation_ints_annotated_of(capped),
        fold_tokens=fold_tokens,
    )


@functools.lru_cache(maxsize=2048)
def _extract_variant_descriptor_cached(
    text: str, category: Optional[str], brand: str, _gate_on: bool,
    _axes_on: bool = False,
) -> VariantDescriptor:
    """Memoized builder. `_gate_on` is part of the key because identity
    tokenization (normalize_words' spaced-unit fold) branches on
    ENABLE_EXACT_PRICE_GATE — a flag flip must never serve a stale descriptor.
    `_axes_on` (Wave-2 B2b) is likewise in the key because the supplement
    nutrient-digit fold (_apply_nutrient_digit_fold) branches identity_core AND
    fold_tokens on ENABLE_VARIANT_DESCRIPTOR_AXES — a flip must not serve a stale
    (unfolded) descriptor. Flag-OFF -> _axes_on False -> the fold no-ops so the
    key/behaviour is byte-identical to the pre-B2b default."""
    return _build_variant_descriptor(text, category, brand)


def extract_variant_descriptor(text: Optional[str], category: Optional[str],
                               brand: str = "") -> VariantDescriptor:
    """The extract-once entry point: the VariantDescriptor of `text` under
    (`category`, `brand`), LRU-memoized (pure function; kills the ~5x re-parse
    per candidate across the matcher chain). Arguments must be hashable —
    an unhashable input raises TypeError loudly (never silently coerced)."""
    return _extract_variant_descriptor_cached(
        text or "", category, brand or "", exact_gate_enabled(),
        variant_descriptor_axes_enabled(),
    )


# ----------------------------------------------------------------------------
# The COMPARATOR TABLE (design lane R2) — ONE decision function, three modes,
# encoding TODAY'S semantics per axis:
#   EXACT_BOTH_STATED  one-sided tolerated; both-stated-different rejects
#                      (concentration, ml-size, storage, count, dose, weight/
#                      volume headline, percent, SPF, RAM, inch, chip-tier,
#                      core-count, supplement flavour, finish, material, fit,
#                      prep, vitamin-letter, shoe-size, pack, clothing-size,
#                      bare-dose, gender-contradiction)
#   SET_EQUALITY       electronics variant qualifiers, plus-stems, both-
#                      unlabelled core-counts
#   ASYMMETRIC_ADD     candidate-adds rejects (flagship concentration,
#                      supplement type/alt-form, grocery flavour); colors is
#                      the query-subset variant
#   EITHER_SIDED       condition — the ONLY either-direction one-sided reject
#   QUERY_STATED_REQUIRES_CANDIDATE  the _candidate_missing_query_axis set
#                      (fail-closed omission of a query-pinned axis)
#   CROSS_CLASS_FAIL_CLOSED  weight-vs-volume disjoint bases
# plus the mode-scoped SELECTION tolerances (year-annotation, electronics
# 'ai', fashion construction bigram, eyewear code-confirmed, inch equality,
# makeup shade-number).
# ----------------------------------------------------------------------------

DESCRIPTOR_MODE_SELECTION = "selection"
DESCRIPTOR_MODE_EXACT = "exact"
DESCRIPTOR_MODE_BACKSTOP = "backstop"
_DESCRIPTOR_MODES = frozenset({
    DESCRIPTOR_MODE_SELECTION, DESCRIPTOR_MODE_EXACT, DESCRIPTOR_MODE_BACKSTOP,
})


@dataclass(frozen=True)
class DescriptorVerdict:
    """descriptor_verdict result: `match` is the decision; `axis` names the
    failing comparator when match is False (diagnostics only — no consumer
    branches on it in Phase A)."""
    match: bool
    axis: Optional[str] = None


def _vd_scalar_differs(a, b) -> bool:
    """EXACT_BOTH_STATED scalar: both stated and different (None = UNKNOWN)."""
    return a is not None and b is not None and a != b


def _vd_disjoint(a: frozenset, b: frozenset) -> bool:
    """EXACT_BOTH_STATED set: both stated and sharing NO value."""
    return bool(a and b and not (a & b))


def _vd_size_ml_mismatch(q: VariantDescriptor, c: VariantDescriptor, cat: str) -> bool:
    """ml/oz size axis (_size_ml_mismatch): fragrances compare the
    standard-bottle SNAPPED sizes exactly; every other category compares the
    RAW oz->ml conversion with a ~5% tolerance (oz<->ml rounding)."""
    if cat == "fragrances":
        return _vd_scalar_differs(q.size_ml_snapped, c.size_ml_snapped)
    if q.size_ml_raw is None or c.size_ml_raw is None:
        return False
    return abs(q.size_ml_raw - c.size_ml_raw) > 0.05 * max(q.size_ml_raw, c.size_ml_raw)


def _vd_strength_mismatch(qd: frozenset, td: frozenset) -> bool:
    """Dose axis (_strength_mismatch): same-unit-only — mismatch iff EVERY
    shared unit has disjoint values (cross-unit pairs never assert)."""
    if not qd or not td:
        return False
    q_units = {u for _v, u in qd}
    t_units = {u for _v, u in td}
    shared = q_units & t_units
    if not shared:
        return False
    for u in shared:
        if {v for v, uu in qd if uu == u} & {v for v, uu in td if uu == u}:
            return False
    return True


def _vd_weight_or_volume_mismatch(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """Weight/volume axis (_weight_or_volume_mismatch): HEADLINE = max per
    base; disjoint bases (g vs ml) = CROSS_CLASS_FAIL_CLOSED mismatch; the lb
    1% tolerance arms only when either side carried an lb token."""
    qwv, twv = q.weights_volumes, c.weights_volumes
    if not qwv or not twv:
        return False
    q_bases = {b for _v, b in qwv}
    t_bases = {b for _v, b in twv}
    shared = q_bases & t_bases
    if not shared:
        return True  # cross-class fail-closed (340g vs 177ml unverifiable)
    _lb_present = q.lb_present or c.lb_present
    for b in shared:
        qv = [v for v, bb in qwv if bb == b]
        tv = [v for v, bb in twv if bb == b]
        if not qv or not tv:
            continue
        qmax, tmax = max(qv), max(tv)
        if qmax == tmax:
            continue
        if _lb_present and b == "g" and abs(qmax - tmax) <= 0.01 * max(qmax, tmax):
            continue
        return True
    return False


def _vd_flavour_mismatch(q: VariantDescriptor, c: VariantDescriptor, cat: str) -> bool:
    """Flavour axis (_flavour_mismatch): grocery is ASYMMETRIC-ADD (a candidate
    flavour the query does not cover is a different SKU, 'unflavored'-add to a
    flavour-less query excepted); supplements are contradiction-only."""
    qf, tf = q.flavours, c.flavours
    if not tf:
        return False
    if cat == "grocery":
        extra = tf - qf
        if not extra:
            return False
        real_q = qf - _FLAVOUR_ABSENCE
        extra_real = extra - _FLAVOUR_ABSENCE
        if not real_q and not extra_real:
            return False
        return True
    if not qf:
        return False
    return not (qf & tf)


def _vd_core_count_mismatch(q_counts, t_counts) -> bool:
    """Core-count axis (_core_count_mismatch): label-aware — same-label bins
    must share a value; unlabelled values compare against the other side's
    full set; both fully unlabelled = SET_EQUALITY."""
    q_cpu, q_gpu, q_un = q_counts
    t_cpu, t_gpu, t_un = t_counts
    q_all = q_cpu | q_gpu | q_un
    t_all = t_cpu | t_gpu | t_un
    if not q_all or not t_all:
        return False
    if q_cpu and t_cpu and not (q_cpu & t_cpu):
        return True
    if q_gpu and t_gpu and not (q_gpu & t_gpu):
        return True
    if not (q_cpu or q_gpu or t_cpu or t_gpu):
        return q_un != t_un
    if q_un and not (q_un & t_all):
        return True
    if t_un and not (t_un & q_all):
        return True
    return False


def _vd_chip_tier_mismatch(qc: frozenset, tc: frozenset) -> bool:
    """Chip-tier axis (_chip_tier_mismatch): same chip NUMBER must carry the
    same tier set (M3 base vs M3 Pro)."""
    q_nums = {n for n, _ in qc}
    t_nums = {n for n, _ in tc}
    shared = q_nums & t_nums
    if not shared:
        return False
    for n in shared:
        if {t for nn, t in qc if nn == n} != {t for nn, t in tc if nn == n}:
            return True
    return False


def _vd_form_mismatch(q: VariantDescriptor, c: VariantDescriptor, cat: str) -> bool:
    """Form axis (_form_mismatch): fragrances+makeup STRICT one-sided (a
    deodorant/oil is a different SKU than the bottle/balm); skincare/haircare
    both-stated-only; a no-op outside fragrance/beauty."""
    if cat not in _FRAGRANCE_BEAUTY_CATEGORIES:
        return False
    if cat in ("fragrances", "makeup"):
        return q.form != c.form
    return bool(q.form and c.form and q.form != c.form)


def _vd_candidate_missing_query_axis(q: VariantDescriptor, c: VariantDescriptor,
                                     cat: str) -> bool:
    """QUERY_STATED_REQUIRES_CANDIDATE (_candidate_missing_query_axis): the
    candidate omitting a query-pinned axis is UNVERIFIED -> fail-closed."""
    if cat == "fragrances":
        if q.concentration and not c.concentration:
            return True
        if q.size_ml_snapped is not None and c.size_ml_snapped is None:
            return True
    if cat == "supplements":
        if q.doses and not c.doses:
            return True
        if q.count is not None and c.count is None:
            return True
    if cat == "electronics":
        if q.storage_gb is not None and c.storage_gb is None:
            return True
    if cat in _SIZE_OMIT_CATEGORIES:
        if q.weights_volumes and not c.weights_volumes:
            return True
    if cat in _PERCENT_CATEGORIES:
        if q.percents and not c.percents:
            return True
    if cat == "fashion":
        if q.shoe_sizes and not c.shoe_sizes:
            return True
    if cat == "grocery":
        if q.packs and not c.packs:
            return True
    return False


def _vd_flagship_concentration_added(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """ASYMMETRIC_ADD (_flagship_concentration_added): the candidate states a
    FLAGSHIP concentration (Parfum/Extrait/Parfum Intense) the query did not."""
    if c.concentration not in _FLAGSHIP_CONCENTRATIONS:
        return False
    return q.concentration != c.concentration


def _vd_supplement_type_added(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """ASYMMETRIC_ADD (_supplement_type_added): candidate adds a formulation
    type/salt-form/sub-line token the query lacks; a MULTI-CONSTITUENT query
    (B-Complex/Multivitamin/Prenatal) excludes the bare constituent names."""
    added = c.supplement_types - q.fold_tokens
    if q.fold_tokens & _MULTI_CONSTITUENT_QUERY:
        added = added - _SUPPLEMENT_CONSTITUENT_TOKENS
    # Wave-2 B2a (C1, flag-gated): when the QUERY is an ACRONYM product, its declared
    # constituents that a descriptive candidate enumerates are the SAME SKU, not a flanker —
    # subtract that acronym's expansion. Bounded (only fires for a table acronym) so the
    # single-element combo-add leak is untouched. Flag-OFF stays byte-identical.
    if variant_descriptor_axes_enabled():
        acronym_expansion = _query_acronym_constituents(q.fold_tokens)
        if acronym_expansion:
            added = added - acronym_expansion
    return bool(added)


def _vd_supplement_form_class(d: VariantDescriptor) -> set:
    """The (default vs alternative) delivery-form class set of one side —
    _supplement_form_added's `_class` on descriptor fields."""
    out = {"alt:" + f for f in d.supplement_alt_forms}
    if d.supplement_default_forms:
        out.add("default")
    return out


def _vd_supplement_form_added(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """ASYMMETRIC_ADD (_supplement_form_added): candidate adds an ALTERNATIVE
    delivery form (gummy/liquid/...) the query lacks, or the stated form
    CLASSES differ (default pill vs alternative)."""
    if c.supplement_alt_forms - q.supplement_alt_forms:
        return True
    q_cls = _vd_supplement_form_class(q)
    t_cls = _vd_supplement_form_class(c)
    return bool(q_cls and t_cls and q_cls != t_cls)


def _vd_category_type_added(q: VariantDescriptor, c: VariantDescriptor, cat: str) -> bool:
    """_category_type_added on descriptor fields (fragrances flagship
    concentration + supplements type/alt-form ONLY; False elsewhere). The
    string-signature _category_type_added (the chokepoints' bounded pair
    check) delegates its helpers here — one implementation."""
    if cat == "fragrances":
        return _vd_flagship_concentration_added(q, c)
    if cat == "supplements":
        return (_vd_supplement_type_added(q, c)
                or _vd_supplement_form_added(q, c))
    return False


def _vd_gender_mismatch(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """Gender CONTRADICTION (_gender_mismatch): both stated and conflicting. Combines the
    STRICT gender with the flag-gated flanker-pronoun gender (him/her) so "Her" vs "Him"
    rejects — WITHOUT the pronoun leaking into the femme-asymmetry, which reads q.gender/
    c.gender STRICT. gender_pronoun is None flag-OFF → byte-identical to the strict check."""
    def _combined(d: VariantDescriptor) -> Optional[str]:
        men = d.gender == "men" or d.gender_pronoun == "men"
        women = d.gender == "women" or d.gender_pronoun == "women"
        if men and not women:
            return "men"
        if women and not men:
            return "women"
        return None
    qg, cg = _combined(q), _combined(c)
    return bool(qg and cg and qg != cg)


def _vd_feminine_query_unconfirmed(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """ASYMMETRIC (_feminine_query_unconfirmed): a WOMEN's-flanker query must
    be confirmed by the candidate; a men's/unisex query tolerates the
    unspecified base (the deliberate one-way trade — see the legacy docstring)."""
    return q.gender == "women" and c.gender != "women"


def _vd_color_mismatch(q: VariantDescriptor, c: VariantDescriptor) -> bool:
    """Fashion colourway (_color_mismatch): the query's stated colours must
    ALL appear in the candidate (query-subset); one-sided tolerated."""
    if not q.colors or not c.colors:
        return False
    return not q.colors.issubset(c.colors)


def _descriptor_axis_mismatch(q: VariantDescriptor, c: VariantDescriptor,
                              category: Optional[str], *,
                              strict_extras: bool = True) -> Optional[str]:
    """The axis core of the comparator table — the descriptor form of the
    legacy _axis_mismatch body, check-for-check in the same order. Returns the
    FAILING AXIS name, or None when no explicit axis discriminates.
    `strict_extras=False` is the BACKSTOP contract (numeric-axis-only — no
    form / candidate-omits / category-type-add / gender / color / clothing /
    vitamin enforcement)."""
    cat = (category or "").lower()
    # SET_EQUALITY — category variant qualifiers (electronics fe/se/pro/...).
    # Extraction already scoped the field to the category's qualifier set, so
    # non-electronics sides carry frozenset() and compare equal (the legacy
    # `if quals` guard).
    if q.qualifiers != c.qualifiers:
        return "variant_qualifier"
    # Universal numeric axes (any category, both-stated-different).
    if _vd_scalar_differs(q.concentration, c.concentration):
        return "concentration"
    if _vd_size_ml_mismatch(q, c, cat):
        return "size_ml"
    if _vd_scalar_differs(q.storage_gb, c.storage_gb):
        return "storage"
    if _vd_scalar_differs(q.count, c.count):
        return "count"
    if _vd_strength_mismatch(q.doses, c.doses):
        return "strength"
    if _vd_weight_or_volume_mismatch(q, c):
        return "weight_volume"
    # %-strength + SPF are CATEGORY-INDEPENDENT discriminators (legacy note:
    # must fire even when the category inferred None on the scrape path).
    if _vd_disjoint(q.percents, c.percents):
        return "percent"
    if _vd_disjoint(q.spfs, c.spfs):
        return "spf"
    if q.plus_stems != c.plus_stems:  # SET_EQUALITY (symbol+spelled unified)
        return "plus_variant"
    # Category-scoped axes (also enforced by the brand-independent backstop).
    if cat == "fashion" and _vd_disjoint(q.shoe_sizes, c.shoe_sizes):
        return "shoe_size"
    if cat == "grocery" and _vd_disjoint(q.packs, c.packs):
        return "pack"
    if cat in _FLAVOUR_CATEGORIES and _vd_flavour_mismatch(q, c, cat):
        return "flavour"
    if cat == "makeup" and _vd_disjoint(q.finishes, c.finishes):
        return "finish"
    if cat == "fashion" and _vd_disjoint(q.materials, c.materials):
        return "material"
    if cat == "fashion" and _vd_disjoint(q.fits, c.fits):
        return "fit"
    if cat == "grocery" and _vd_disjoint(q.preps, c.preps):
        return "grocery_prep"
    # EITHER_SIDED — condition is the ONLY either-direction one-sided reject
    # (a stated non-new condition on EITHER side alone is a different tier).
    if cat == "electronics" and q.condition != c.condition:
        return "condition"
    if cat == "electronics" and _vd_disjoint(q.inches, c.inches):
        return "inch"
    if cat == "electronics" and _vd_disjoint(q.ram_gb, c.ram_gb):
        return "ram"
    if cat == "electronics" and _vd_core_count_mismatch(q.core_counts, c.core_counts):
        return "core_count"
    if cat == "electronics" and _vd_chip_tier_mismatch(q.chip_tiers, c.chip_tiers):
        return "chip_tier"
    if cat == "supplements" and _vd_disjoint(q.bare_doses, c.bare_doses):
        return "bare_dose"
    if strict_extras:
        if _vd_form_mismatch(q, c, cat):
            return "form"
        if _vd_candidate_missing_query_axis(q, c, cat):
            return "candidate_missing_query_axis"
        if _vd_category_type_added(q, c, cat):
            return "category_type_added"
        if (cat in _FRAGRANCE_BEAUTY_CATEGORIES or cat == "fashion") and (
                _vd_gender_mismatch(q, c) or _vd_feminine_query_unconfirmed(q, c)):
            return "gender"
        if cat == "fashion" and _vd_color_mismatch(q, c):
            return "color"
        if cat == "fashion" and _vd_disjoint(q.clothing_sizes, c.clothing_sizes):
            return "clothing_size"
        if cat == "supplements" and _vd_disjoint(q.vitamin_letters, c.vitamin_letters):
            return "vitamin_letter"
    return None


def _descriptor_selection_verdict(q: VariantDescriptor, c: VariantDescriptor,
                                  category: Optional[str]) -> DescriptorVerdict:
    """The SELECTION-mode identity/superset steps — the descriptor form of the
    legacy _selection_match keystone, step-for-step: generic class-swap, the
    per-category PADDING subtraction, the mode-scoped title-side tolerances
    (year-annotation / electronics 'ai' / inch equality / fashion construction
    bigram / eyewear code-confirmed / makeup shade-number), the LEAK-direction
    subset, and the VARIANT-ADD superset with the generic-query skip. Axis
    checks have already passed by the time this runs."""
    cat = (category or "").lower()
    q_ident, t_ident = q.identity_core, c.identity_core
    _generic = _generic_for(category)
    q_distinct = q_ident - _generic
    t_distinct = t_ident - _generic
    # (1) generic CLASS SWAP — each names a generic class noun, sharing none.
    q_generic = q_ident & _generic
    t_generic = t_ident & _generic
    if q_generic and t_generic and not (q_generic & t_generic):
        return DescriptorVerdict(False, "generic_class_swap")
    # (2)+(3) THE KEYSTONE — per-category padding, both directions.
    padding = _category_padding(cat)
    q_core = q_distinct - padding
    t_core = t_distinct - padding
    if cat in _MODEL_YEAR_CATEGORIES:
        # ONE-SIDED model-year tolerance (annotation-form title year, query
        # generation pinned by a non-year discriminator the title shares,
        # query states no year) — see the legacy comment block.
        if not any(_MODEL_YEAR_RE.match(w) for w in q_core):
            if c.year_annotations and (_year_generation_discriminators(q_core) & t_core):
                t_core = t_core - c.year_annotations
    if cat == "electronics":
        # TITLE-side-only marketing tokens ("AI Smartphone") — query-stated
        # copies stay on both sides.
        t_core = t_core - (_ELECTRONICS_TITLE_SIDE_TOLERATED - q_core)
        # INCH-axis equality tolerance, both spellings (bare vs annotated).
        if c.inch_tokens:
            q_core = q_core - c.inch_tokens
        if q.inch_tokens:
            t_core = t_core - q.inch_tokens
    if cat == "fashion" and q_core:
        # Construction/neckline descriptors (query-conditional) + the
        # Luxottica model-code-CONFIRMED eyewear annotation tolerance.
        t_core = t_core - (c.construction_tolerated - q_core)
        if q.model_codes and (q.model_codes & c.model_codes):
            _eyewear_tol = frozenset(_EYEWEAR_DESCRIPTOR_TOKENS) | c.eyewear_annotations
            t_core = t_core - (_eyewear_tol - q_core)
    if cat == "makeup":
        # Shared shade-NUMBER acceptance (no extra number, non-number core
        # subset-compatible) — different formula LINES already rejected by the
        # finish axis upstream.
        q_nums = {w for w in q_core if w.isdigit()}
        t_nums = {w for w in t_core if w.isdigit()}
        if (q_nums and t_nums and (q_nums & t_nums) and not (t_nums - q_nums)
                and (q_core - q_nums).issubset(t_core - t_nums)):
            return DescriptorVerdict(True)
    # LEAK direction — candidate must carry every query distinctive token.
    if not q_core.issubset(t_core):
        return DescriptorVerdict(False, "identity_subset")
    # VARIANT-ADD direction — an extra distinctive candidate token is a
    # DIFFERENT SKU (known categories + explicit "other"; truly-unresolved
    # stays subset-only).
    if (cat in _SUPERSET_VARIANT_CATEGORIES or cat == "other") and (t_core - q_core):
        if q_core:
            return DescriptorVerdict(False, "variant_add")
        if (q_distinct - _MANUFACTURER_NOISE) or cat not in _GENERIC_QUERY_SKIP_CATEGORIES:
            return DescriptorVerdict(False, "variant_add")
    return DescriptorVerdict(True)


def descriptor_verdict(q: VariantDescriptor, c: VariantDescriptor,
                       category: Optional[str], mode: str) -> DescriptorVerdict:
    """THE decision function (R2): compare two VariantDescriptors under
    `category` in one of the three modes. `category` MUST be the category the
    descriptors were extracted with (the wrappers guarantee it; the
    _selection_match "other" re-inference happens BEFORE extraction).

      SELECTION — strict axes + the keystone subset/superset with padding and
                  tolerances (the _selection_match contract)
      EXACT     — strict axes + identity-token set-EQUALITY (is_exact_match)
      BACKSTOP  — loose axes only (strict_extras=False, the
                  _backstop_identity_ok contract; the chokepoints pair it with
                  the separate bounded _category_type_added)
    """
    if mode not in _DESCRIPTOR_MODES:
        raise ValueError(f"unknown descriptor mode: {mode!r}")
    axis = _descriptor_axis_mismatch(
        q, c, category, strict_extras=(mode != DESCRIPTOR_MODE_BACKSTOP))
    if axis is not None:
        return DescriptorVerdict(False, axis)
    if mode == DESCRIPTOR_MODE_BACKSTOP:
        return DescriptorVerdict(True)
    if mode == DESCRIPTOR_MODE_EXACT:
        if q.identity_core == c.identity_core:
            return DescriptorVerdict(True)
        return DescriptorVerdict(False, "identity_equality")
    return _descriptor_selection_verdict(q, c, category)


def _axis_mismatch(query_name: str, candidate_title: str, category: Optional[str],
                   brand: str = "", *, strict_extras: bool = True) -> bool:
    """True iff query and candidate disagree on an EXPLICIT discriminating axis:
    a variant qualifier (either direction), concentration, ml/oz size, GB/TB
    storage, unit count, supplement strength (mg/IU), weight/volume (g/ml), and —
    when `strict_extras` (the primary brand-aware gates) — a product FORM
    (deodorant/candle/lotion vs the bottle) OR the candidate OMITting a query-stated
    axis (fragrance conc/size, supplement strength/count → unverified, fail-closed).

    `brand` is used only to strip the brand before form detection. The shared core
    of both the strict `is_exact_match` and the brand-tolerant chokepoint backstop;
    the backstop passes `strict_extras=False` so it keeps its original
    numeric-axis-only, never-false-pend-a-descriptive-title contract (the form +
    candidate-omits enforcement lives on the brand-aware primary gates). Each numeric
    axis is a no-op unless BOTH sides carry it (a fragrance has no storage, a phone
    no dose).

    Wave-2 A1: thin wrapper over the extract-once VariantDescriptor — the
    per-axis checks (and the _MATCH_INPUT_CAP ReDoS cap) live in
    extract_variant_descriptor + _descriptor_axis_mismatch, check-for-check
    identical (golden-corpus pinned)."""
    q_vd = extract_variant_descriptor(query_name, category, brand)
    c_vd = extract_variant_descriptor(candidate_title, category, brand)
    return _descriptor_axis_mismatch(
        q_vd, c_vd, category, strict_extras=strict_extras) is not None


def is_exact_match(
    query_name: str, candidate_title: str, category: Optional[str],
    *, candidate_brand: str = "",
) -> bool:
    """True iff `candidate_title` is the SAME product as `query_name` — set-EQUALITY
    on identity tokens (after subtracting `candidate_brand` from BOTH sides so a
    brand-omitted sephora-style title "Daisy - EDT" matches a "Marc Jacobs Daisy"
    query) AND no explicit mismatch on any discriminating axis (variant qualifier /
    concentration / size / storage / count).

    This is the single shared gate every selection site calls. When the rollback
    flag is OFF it returns True (no-op). It is intentionally STRICT (equality, not
    `strict_title_match`'s subset) to reject S24→S24 FE / EDP→EDT / 256→128 /
    100ml→30ml / flanker leaks, and intentionally BRAND-AWARE + alias-tolerant
    (EDT≡"eau de toilette", oz≡ml, diacritics, colour/edition for electronics) to
    avoid false pends.

    Wave-2 A1: thin wrapper over the extract-once VariantDescriptor (EXACT
    mode = strict axes + identity-token set-EQUALITY, golden-corpus pinned).
    The gate no-op + empty-input early-returns stay here, byte-identical."""
    if not exact_gate_enabled():
        return True
    if not query_name or not candidate_title:
        return True
    q_vd = extract_variant_descriptor(query_name, category, candidate_brand)
    c_vd = extract_variant_descriptor(candidate_title, category, candidate_brand)
    return descriptor_verdict(q_vd, c_vd, category, DESCRIPTOR_MODE_EXACT).match


# ---------------------------------------------------------------------------
# BF3 (Wave B-FIX, over-rejection sweep OR-1..OR-4) — bounded TITLE-SIDE
# tolerances applied inside _selection_match AFTER the padding subtraction.
# Each is query-CONDITIONAL (never a static both-sides padding), so the
# numeric/identity axis is untouched whenever the QUERY states the token.
# ---------------------------------------------------------------------------

# Bare model-year token 2020-2029 (forms: "2025", "(2025)" — parens are
# normalize_words-stripped — and "GEN 2025", "gen" being electronics padding).
# BOUNDED to the 2020s so RTX-2080-class model numbers stay identity.
_MODEL_YEAR_RE = re.compile(r"^202[0-9]$")
_MODEL_YEAR_CATEGORIES = frozenset({"electronics", "fashion"})

# Wave C (re-sweep RS1 + kpiE2E RS-3) — the year tolerance is RE-BOUND to the
# retailer RELEASE-TAG ANNOTATION shapes on the RAW title: "(2025)" and
# "GEN 2025" (the two live sharafdg/extra forms the BF3 unlock needed). A bare
# mid-title year is a MODEL / SEASON / GENERATION name (Air Max 2021, jersey
# 2024 seasons, Watch SE (2020)-class re-releases sell at 2-3x spreads) and
# stays identity.
_ANNOTATION_YEAR_RE = re.compile(
    r"\(\s*(202[0-9])\s*\)|\bgen[\s\-]+(202[0-9])\b", re.I,
)
# A digit-run followed by a pure-letter unit tail ("128gb", "44mm", "13inch",
# "2xl") is a MEASURE-shaped token — never a generation discriminator.
_MEASURE_SHAPE_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?[a-z]+")


def _annotation_year_tokens(title: str) -> set:
    """The 2020s year tokens that appear in ANNOTATION form in raw `title`
    ("iPad Air (2025) M3" -> {"2025"}; a bare "Air Max 2021" -> set())."""
    out = set()
    for m in _ANNOTATION_YEAR_RE.finditer(title or ""):
        out.add(m.group(1) or m.group(2))
    return out


def _year_generation_discriminators(q_core: set) -> set:
    """The query-core tokens that pin a product GENERATION independently of a
    year: digit-bearing model/chip tokens (m3 / m5 / s25 / wh1000xm5 / a bare
    model number "15"/"9"-post-ordinal-fold) — NEVER a 202x year itself and
    NEVER a measure-shaped token (128gb / 44mm / 13inch / 2xl). Only when the
    title carries one of these too is a title-side annotation year redundant
    release-tag padding (re-sweep RS1/RS-3: the year-ONLY-discriminated
    families — iPhone SE / Watch SE / jersey seasons — must keep the year as
    identity)."""
    return {
        w for w in q_core
        if any(c.isdigit() for c in w)
        and not _MODEL_YEAR_RE.match(w)
        and not _MEASURE_SHAPE_TOKEN_RE.fullmatch(w)
    }

# Marketing tokens tolerated on the TITLE side only (the 2025+ Samsung
# "AI Smartphone" class killing kpi-elec-002/003) — NEVER dropped from the
# query side: a hypothetical product line named "AI" ("Nothing AI Phone")
# keeps its token required. This asymmetry is why the token is NOT in
# _ELECTRONICS_PADDING (padding strips BOTH sides).
_ELECTRONICS_TITLE_SIDE_TOLERATED = frozenset({"ai"})

# Apparel CONSTRUCTION/NECKLINE descriptors tolerated on the TITLE side only
# (Wave B-FIX BF4, sweep OR-6): namshi lists the kpi-fash-006 exact SKU as
# "Essential Flag EMBROIDERY CREW NECK T-Shirt" — 'Embroidery'/'Crew'/'Neck'
# each individually variant-add-rejected it, and the same phrasing is
# ubiquitous GCC apparel listing style (6thstreet Heritage/Essential tees).
# The _ELECTRONICS_TITLE_SIDE_TOLERATED asymmetry: NEVER dropped from the
# query side — a query-stated neckline ("V-Neck") keeps its token required,
# so a both-stated-DIFFERENT neckline still rejects via the LEAK-direction
# subset (there is NO dedicated neckline axis; the query-side token IS the
# contradiction guard — pinned both directions in
# tests/test_fashion_skincare_unlock_bfix.py). "v-neck"/"t-shirt" hyphens are
# collapsed by normalize_words, hence the glued "vneck" form. The class axis
# is untouched: polo-vs-t-shirt still class-swap-rejects (the garment nouns
# live in _GENERIC_FASHION_NOUNS, consulted BEFORE this tolerance).
#
# Wave C (re-sweep RS5): bare "crew"/"neck" are NO LONGER in the static set —
# a bare 'crew' is a BRAND word ("J Crew", made brand-invisible by the
# tolerance after 'j' fell to the len rule) and a bare 'neck' asserts nothing
# about construction. They are tolerated ONLY when the RAW title carries a
# garment NECKLINE BIGRAM ("crew neck" / "v neck" / "round neck", hyphen or
# space) — see _fashion_construction_tolerated_for. The glued single tokens
# ("crewneck"/"vneck") stay, as do embroidery/embroidered/stitch/stitched
# (the BF4 pin battery; the Disney-'Stitch' residual is documented in the
# re-sweep and deliberately out of the RS5 bound).
# Wave-2 B1.1c (gate-scoped UN-flagged, same class as the RS5 bigram-conditional
# neckline change): bare "stitch"/"stitched" are NO LONGER static members. A
# standalone/leading "Stitch" is the Disney character (a DISTINCT graphic-print
# SKU — census FULL-leak); a sewing-context "stitch" ("contrast stitch",
# "stitched logo", "stitch detail", "topstitch") is genuine construction padding.
# So stitch/stitched join the tolerated set ONLY when the raw title spells a
# sewing-context bigram (mirrors _FASHION_NECKLINE_BIGRAM_RE).
_FASHION_CONSTRUCTION_TOLERATED = frozenset({
    "crewneck", "vneck", "embroidery", "embroidered",
})
# Sewing-context words that, adjacent to stitch/stitched (either order, hyphen or
# space) OR glued ("topstitch"), mark it as construction rather than the
# character name. Kept deliberately broad on the sewing vocabulary so a genuine
# GCC-retailer descriptive title ("Twin Tipped stitched collar", "contrast
# stitch trim") still tolerates, while a bare/leading "Stitch" stays distinctive.
_STITCH_CONTEXT_WORDS = (
    "contrast", "detail", "details", "logo", "trim", "top", "double", "triple",
    "chain", "seam", "seams", "collar", "hem", "pattern", "decorative",
    "embroidered", "flat", "over", "cross", "saddle", "blanket", "running",
    "visible", "tonal",
)
_STITCH_CTX = "|".join(_STITCH_CONTEXT_WORDS)
_FASHION_STITCH_BIGRAM_RE = re.compile(
    rf"\b(?:(?:{_STITCH_CTX})[\s\-{_UNICODE_HYPHENS}]+stitch(?:ed|ing)?"
    rf"|stitch(?:ed|ing)?[\s\-{_UNICODE_HYPHENS}]+(?:{_STITCH_CTX})"
    rf"|topstitch(?:ed|ing)?)\b",
    re.I,
)
# Separator accepts the C2 _UNICODE_HYPHENS canon (Wave D, convergence CV5):
# a U+2011 "Crew‑Neck" title is the same GCC-retailer bigram — ASCII-only left
# it a distinctive add and a genuine enriched title over-rejected.
_FASHION_NECKLINE_BIGRAM_RE = re.compile(
    rf"\b(crew|v|round)[\s\-{_UNICODE_HYPHENS}]+neck\b", re.I,
)


def _fashion_construction_tolerated_for(candidate_title: str) -> frozenset:
    """The title-CONDITIONAL construction-descriptor token set (RS5): the
    neckline words 'crew'/'v'/'round' + 'neck' join the tolerated set only
    when the raw title spells the garment bigram — so the bigram's own tokens
    are droppable while a bare 'crew'/'neck' elsewhere stays distinctive.

    Wave D (convergence CV5): a UNICODE-hyphen bigram ("Crew‑Neck", U+2011)
    survives tokenization GLUED — normalize_words strips only the ASCII
    hyphen, so the identity token is the folded "crew‐neck", not the pair.
    Tolerate that glued form too, derived from the ACTUAL matched text via
    the same _fold_identity the tokenizer path runs (U+2011 NFKD-folds to
    U+2010; U+2010/U+2013 pass through), so the tolerance and the tokenizer
    can never drift. ASCII/spaced forms fold to the static "crewneck"-style
    token and add nothing new."""
    extra = set()
    for m in _FASHION_NECKLINE_BIGRAM_RE.finditer(candidate_title or ""):
        g = m.group(1).lower()
        extra.add(g)
        extra.add("neck")
        glued = re.sub(r"\s+", "", _fold_identity(m.group(0))).replace("-", "")
        if glued != f"{g}neck":
            extra.add(glued)
    # Wave-2 B1.1c: 'stitch'/'stitched'/'stitching'/'topstitch' tolerated ONLY in
    # a sewing-context bigram (a bare/leading "Stitch" = the Disney character stays
    # distinctive). Tolerate the WHOLE matched bigram (the stitch token AND its
    # sewing-context word, mirroring the neckline bigram that tolerates both 'crew'
    # and 'neck') so a genuine "contrast stitch"/"stitched collar" descriptive title
    # is not rejected on the context word instead. Add the ACTUAL folded tokens the
    # tokenizer emits from the matched span so the tolerance and the tokenizer can
    # never drift. NOTE: a bare 'collar'/'contrast' elsewhere (no adjacent stitch)
    # is untouched and stays distinctive.
    for m in _FASHION_STITCH_BIGRAM_RE.finditer(candidate_title or ""):
        for tok in re.findall(r"[a-z0-9]+", _fold_identity(m.group(0))):
            extra.add(tok)
    if extra:
        return _FASHION_CONSTRUCTION_TOLERATED | frozenset(extra)
    return _FASHION_CONSTRUCTION_TOLERATED


def _inch_digit_tokens(text: str) -> set:
    """The BARE-digit token forms of the inch-annotated screen sizes stated in
    raw `text` ('13-inch' / '13 Inch' / '13"' -> {'13'}; '13.6-inch' ->
    {'13.6'}). Used for the inch-axis EQUALITY tolerance (BF3, OR-2): a
    title-side inch-annotation of a bare query digit is the SAME axis value,
    not an added axis — but only on EXACT digit equality, so 13 vs 15-inch
    still contradicts via the ordinary subset/variant-add checks."""
    out = set()
    for m in _INCH_RE.findall(text or ""):
        tok = str(m)
        if "." in tok:
            tok = tok.rstrip("0").rstrip(".")
        out.add(tok)
    return out


# ---------------------------------------------------------------------------
# Wave E (kpi-fash-004) — Luxottica MODEL-CODE-CONFIRMED eyewear tolerance.
# The live noon-BH RB3025 bisect (2026-07-02): every upstream gate passed
# (counterfeit/accessory/numbers/strict/variant/axis) and the ONLY killing
# gate was the variant-add direction — the GCC eyewear listing style decorates
# the exact frame with the Luxottica NNN/NN colorway code ("RB3025 002/58"),
# a lens-size annotation ("Lens Size: 58 mm", the trailing bare "58" run) and
# stock descriptors (Unisex/Polarized), each surviving as a distinctive
# title-side ADD. When the QUERY carries a Luxottica-family model code
# ((rb|rx|oo|po|ar|pr|ve|dg)\d{3,}, the same family the 0-prefix fold covers)
# AND the title carries the SAME code (0-prefix-folded), the code is
# query-confirmed exact-model evidence — the established structured-code-
# override principle, here TITLE-derived — and ONLY those annotation shapes
# become title-side padding. Query-CONDITIONAL like every BF3 tolerance
# (`tolerated - q_core`): a query-stated colorway/size token stays required,
# so 'RB3025 901/58' still rejects an '002/58' title via the leak direction.
# numbers_match is untouched globally; a non-eyewear query (no code) gains
# nothing; a DIFFERENT-code title never triggers (leak direction rejects).
# Shared-matcher placement so namshi/optica/6thstreet eyewear benefit too.
_LUXOTTICA_MODEL_CODE_RE = re.compile(
    r"(?<![a-z0-9])0?((?:rb|rx|oo|po|ar|pr|ve|dg)\d{3,})(?![a-z0-9])"
)
# The NNN/NN(alnum) colorway ADJACENT to the model code ("RB3025 002/58",
# "0Rb3025-003/3F"), plus the trailing bare lens-digit run ("002/58 58").
_LUXOTTICA_COLORWAY_ADJ_RE = re.compile(
    rf"(?<![a-z0-9])0?(?:rb|rx|oo|po|ar|pr|ve|dg)\d{{3,}}"
    rf"[\s\-{_UNICODE_HYPHENS}]+(\d{{2,3}}/[a-z0-9]{{1,3}})\b(?:\s+(\d{{2}})\b)?"
)
# Lens-size annotation forms: "Lens Size: 58 mm" / bare "58 mm" (the spaced-
# unit fold turns these into the '58mm' token; the bare '58' also appears).
_EYEWEAR_LENS_MM_RE = re.compile(r"(?<![a-z0-9.])(\d{2})\s*mm(?![a-z0-9])")
_EYEWEAR_LENS_PHRASE_RE = re.compile(r"\blens\s*size\b")
# Stock eyewear listing descriptors — never SKU discriminators on a
# code-confirmed frame (the frame's own code + colorway discriminate).
_EYEWEAR_DESCRIPTOR_TOKENS = frozenset({
    "unisex", "polarized", "gradient", "mirrored",
})


def _luxottica_model_codes(text: str) -> set:
    """The Luxottica-family model-code tokens present in `text`, lowercased and
    0-prefix-FOLDED ("0Rb3025" -> "rb3025") so the catalog list form and the
    consumer code compare equal. Empty set on no code / empty input."""
    if not text:
        return set()
    if len(text) > _MATCH_INPUT_CAP:  # ReDoS guard, matching the other matchers
        text = text[:_MATCH_INPUT_CAP]
    return {m.group(1) for m in _LUXOTTICA_MODEL_CODE_RE.finditer(text.lower())}


def _eyewear_code_tolerated_for(query_name: str, candidate_title: str) -> frozenset:
    """The title-side tolerated token set for a QUERY-CONFIRMED Luxottica model
    code (empty unless query and title share a code, 0-prefix-folded): the
    colorway sub-tokens adjacent to the code, the lens-size annotation tokens,
    and the stock eyewear descriptors. Derived from the RAW title so only the
    exact annotation values present are tolerated — never arbitrary digits."""
    q_codes = _luxottica_model_codes(query_name)
    if not q_codes or not (q_codes & _luxottica_model_codes(candidate_title)):
        return frozenset()
    # Wave-2 A1: the title scan ("002/58" -> {'002','58'}, lens-mm forms,
    # the 'lens size' phrase words) lives in _eyewear_annotation_tokens so the
    # VariantDescriptor and this legacy helper share ONE implementation.
    return frozenset(_EYEWEAR_DESCRIPTOR_TOKENS | _eyewear_annotation_tokens(candidate_title))


def _selection_match(
    query_name: str, candidate_title: str, category: Optional[str],
    *, candidate_brand: str = "",
) -> bool:
    """The pragmatic SELECTION gate used by the extractors and select_best (real
    retailer titles are DESCRIPTIVE — "Samsung Galaxy S24 256GB Dual SIM Phantom
    Black" — so a pure-equality gate would over-reject genuine listings). A
    candidate is acceptable iff:
      - NO explicit axis mismatch (variant qualifier / concentration / ml-size /
        GB-storage / count), AND
      - the query's distinctive identity tokens are ALL present in the candidate
        (query ⊆ candidate) — so a wrong/related product MISSING a query
        discriminator (Nike Dunk Low → "Nike Air Force 1") is rejected, while a
        descriptive longer title (extra colour/SIM/packaging words) is kept.
    This catches every documented warm-cache leak (S24→FE, EDP→EDT, 256→128,
    decant-size, related-product, count drift) without false pends. The strict
    set-EQUALITY `is_exact_match` is reserved for clean brand-omitted sources
    (sephora/Zyte) + the shared contract.

    Wave-2 A1: thin wrapper over the extract-once VariantDescriptor — the
    identity/superset keystone, per-category padding and the title-side
    tolerances live step-for-step in _descriptor_selection_verdict (see the
    comment blocks there; golden-corpus pinned). The gate no-op, the empty-
    input early-returns and the "other" re-inference stay HERE (re-inference
    must run BEFORE extraction — the category is an extraction parameter)."""
    if not exact_gate_enabled():
        return True
    if not query_name or not candidate_title:
        return True
    # EXPLICIT "other" is a FREQUENT real LLM output, not just the unresolved fallback (round-8
    # CRITICAL): re-infer FIRST so every category-dependent step below (axes, identity
    # colour/qualifier handling, generic scoping, padding) uses the right category, and the
    # variant-add guard runs (AirPods Pro labelled "other" still rejects Pro 2). A TRULY-None
    # category (caller passed nothing) is left as-is → subset-only below — on prod paths the
    # orchestrator category is always threaded (param/ContextVar) so None only occurs in a
    # direct off-path/unit call, where lenient subset matching avoids mass over-rejection.
    if (category or "").lower() == "other":
        category = _infer_category_from_query(query_name) or category
    q_vd = extract_variant_descriptor(query_name, category, candidate_brand)
    c_vd = extract_variant_descriptor(candidate_title, category, candidate_brand)
    return descriptor_verdict(q_vd, c_vd, category, DESCRIPTOR_MODE_SELECTION).match


# The 8 KNOWN categories whose PADDING lists are tuned enough to run the variant-add guard.
_SUPERSET_VARIANT_CATEGORIES = frozenset({
    "electronics", "fashion", "grocery", "makeup", "skincare", "haircare",
    "supplements", "fragrances",
})
# Categories where a brand/class query (no distinctive core) legitimately matches any
# specific member ("Sony Headphones" -> "Sony WH-CH520", "Dior" -> "Dior Sauvage"). For
# grocery/makeup/skincare/haircare/supplements a base query implies the canonical product,
# so a candidate that ADDS a variant token is a different SKU and must pend.
# NOTE: "fragrances" is DELIBERATELY EXCLUDED — a fragrance query emptied to a bare brand
# + gender (Dior Homme: brand Dior + gender 'homme' stripped -> q_core empty) must NOT skip
# the variant-add guard, or it accepts a flanker (Dior Homme Intense) (coverage review).
# fashion EXCLUDED too — a fashion query emptied to brand+material+colour (Puma Suede:
# suede is material-padding) must NOT skip the guard, else it matches any Puma (coverage
# review). Only electronics (Sony Headphones -> WH-CH520) + unresolved keep the skip.
_GENERIC_QUERY_SKIP_CATEGORIES = frozenset({"electronics", "other", ""})


def _backstop_identity_ok(query_name: str, candidate_title: str, category: Optional[str]) -> bool:
    """Brand-INDEPENDENT exactness check for the response chokepoint
    (is_price_showable). The primary per-extractor/select_best gate (_selection_match,
    which knows the brand) is the real enforcement; this backstop runs WITHOUT the
    brand, so it relies ONLY on the explicit-axis mismatch checks (variant qualifier /
    concentration / size / storage / count) — brand-independent and direction-free,
    so it never false-pends a genuine brand-omitted (sephora) NOR a descriptive
    (Dual SIM Phantom Black) listing. It catches the dominant wrong-axis leaks
    (S24→FE, EDP→EDT, 256→128, decant-size, count drift) on any path that bypassed
    the primary gate; the rarer same-token flanker is caught upstream where the
    brand is known.

    Wave-2 A1: thin wrapper over the extract-once VariantDescriptor (BACKSTOP
    mode = loose axes only, strict_extras=False — never the superset, per the
    is_price_showable revert proof). The empty-title early-return stays here."""
    if not candidate_title:
        return True
    q_vd = extract_variant_descriptor(query_name, category, "")
    c_vd = extract_variant_descriptor(candidate_title, category, "")
    return descriptor_verdict(q_vd, c_vd, category, DESCRIPTOR_MODE_BACKSTOP).match


def _descriptor_backstop_axes_verdict(
    q: VariantDescriptor, c: VariantDescriptor, category: Optional[str],
) -> Optional[str]:
    """The Phase-B1 EXTRA backstop-mode checks (flag-gated), each firing ONLY
    when the axis was EXTRACTED on the relevant side(s) so a descriptive title
    is never false-pended. Returns the granular failing-axis reason suffix
    (appended to "not_exact:") or None. NEVER the identity-token superset (the
    proven-reverted over-rejection, comment ps:1408-1420) and NOT the
    candidate-omits-query-axis check (dispatcher ruling: over-rejection risk on
    converted/iHerb display paths).

    Decides ONLY the token-decidable weak-chokepoint leak classes the recon
    census flagged as BACKSTOP-ONLY:
      - gender both-stated CONTRADICTION only (Homme vs Femme). The
        feminine-query-unconfirmed asymmetry was DROPPED here (B1-FIX ruling B —
        over-rejected correct women's bases; still enforced at selection/cache-
        write).
      - prefixed clothing-size both-stated mismatch (Size M vs Size XL)
      - model-year both-stated mismatch (both sides state a year, disjoint)
      - flanker_markers ADD direction only (fragrances; candidate ADDS a flanker,
        Sauvage->Elixir; the query-omits reverse tolerates, B1-FIX ruling C)
      - generation_ints ADD direction only (candidate adds a model-noun-adjacent
        INLINE generation int absent from the query; parenthetical "(Nth gen)"
        annotations + quantity-noun-suffixed ints excluded, B1-FIX ruling A;
        the reverse stays selection-only)
    """
    cat = (category or "").lower()
    # Gender (fragrance/beauty + fashion): both-stated CONTRADICTION only
    # (B1-FIX ruling B). The feminine-query-unconfirmed asymmetry was DROPPED at
    # this axis-only backstop because it over-rejected correct women's bases
    # (Black Opium / Coco Mademoiselle / La Vie Est Belle vs a gender-omitting
    # genuine PDP) across all four beauty categories; the leak it closed (femme
    # query -> men's base) is backstop-only and STILL caught by the selection
    # gate + should_cache_price (which keep _feminine_query_unconfirmed), so the
    # warmer write path is unaffected. q.gender/c.gender are None when unstated.
    if cat in _FRAGRANCE_BEAUTY_CATEGORIES or cat == "fashion":
        if _vd_gender_mismatch(q, c):
            return "gender"
    # Prefixed clothing-size (fashion): both state a "Size L"-form letter and
    # share none. Bare letters stay ambiguous (not extracted) as at selection.
    if cat == "fashion" and _vd_disjoint(q.clothing_sizes, c.clothing_sizes):
        return "clothing_size"
    # Model-year both-stated (electronics/fashion): a year stated on BOTH sides
    # (annotation "(2022)"/"gen 2022" OR a bare 2020s model-year token) that is
    # disjoint = a different generation. One-sided stays tolerated (the selection
    # side owns the latest-generation-default direction).
    if cat in _MODEL_YEAR_CATEGORIES:
        q_years = _vd_model_years(q)
        c_years = _vd_model_years(c)
        if q_years and c_years and not (q_years & c_years):
            return "model_year"
    # Flanker markers (fragrances): the CANDIDATE ADDS a curated concentration-
    # flanker word the query never asked for (Sauvage -> Sauvage Elixir) = a
    # distinct pricier SKU. ADD-DIRECTION ONLY (B1-FIX ruling C, consistent with
    # the B1.1 "no candidate-omits-query-axis at backstop" rule): a query that
    # carries a flanker the candidate omits ("Dior Homme Intense" -> "Dior
    # Homme") TOLERATES here — the flanker word is part of a canonical base-line
    # name and the omission stays a selection-side concern. The curated set never
    # contains a base-name word so a correct base ("Oud Wood") carries none.
    if cat == "fragrances" and (c.flanker_markers - q.flanker_markers):
        return "flanker"
    # Generation ints (electronics): candidate ADDS a model-noun-adjacent
    # generation int the query never asked for (AirPods Pro -> Pro 2). ADD
    # direction only — the reverse (query pins a generation, candidate omits it)
    # stays a selection-side concern (a bare-int omission is not backstop-safe).
    if cat == "electronics" and (c.generation_ints - q.generation_ints):
        return "generation"
    return None


def _vd_model_years(d: VariantDescriptor) -> FrozenSet[str]:
    """The model-year tokens on one side for the backstop both-stated check:
    the annotation-form years (year_annotations) UNION the bare 2020s
    model-year tokens present in the identity (a "SE 2020" bare year, which
    _annotation_year_tokens deliberately does NOT capture). Non-2020s numbers
    (RTX 2080-class model numbers) are excluded by _MODEL_YEAR_RE's 202[0-9]
    bound."""
    bare = frozenset(w for w in d.fold_tokens if _MODEL_YEAR_RE.match(w))
    return d.year_annotations | bare


def backstop_identity_verdict(
    query_name: str, candidate_title: str, category: Optional[str], *,
    brand: str = "",
) -> Tuple[bool, Optional[str]]:
    """THE shared weak-chokepoint identity decision — one implementation for BOTH
    the display enforce block (is_price_showable) and the cache-read
    _cache_price_identity_ok, so read==display parity is STRUCTURAL.

    Returns (ok, reason): ok=True passes; ok=False pends/drops with `reason` the
    guard_rejected value ("not_exact" flag-OFF; "not_exact:<axis>" flag-ON).

    FLAG-OFF (variant_descriptor_axes_enabled False -> default, and whenever the
    exact gate is off) returns EXACTLY the legacy pair
      (_backstop_identity_ok(...) and not _category_type_added(...))
    with reason "not_exact" on failure -> byte-identical pre-change behaviour
    (pinned by the golden corpus + a flag-OFF unit pin).

    FLAG-ON adds the Phase-B1 bounded extra axes
    (_descriptor_backstop_axes_verdict), each firing only when the axis was
    extracted, with a granular "not_exact:<axis>" reason. `brand` is accepted for
    signature parity with the primary gates but the backstop stays
    brand-INDEPENDENT (the extractors subtract nothing extra), so a genuine
    brand-omitted sephora title is never false-pended."""
    if not exact_gate_enabled():
        # Gate off -> the legacy backstop is itself a no-op contract; reproduce it.
        legacy_ok = (_backstop_identity_ok(query_name, candidate_title, category)
                     and not _category_type_added(query_name, candidate_title, category))
        return (legacy_ok, None if legacy_ok else "not_exact")
    legacy_ok = (_backstop_identity_ok(query_name, candidate_title, category)
                 and not _category_type_added(query_name, candidate_title, category))
    if not legacy_ok:
        return (False, "not_exact")
    if not variant_descriptor_axes_enabled():
        return (True, None)
    if not candidate_title:
        return (True, None)
    q_vd = extract_variant_descriptor(query_name, category, brand)
    c_vd = extract_variant_descriptor(candidate_title, category, brand)
    axis = _descriptor_backstop_axes_verdict(q_vd, c_vd, category)
    if axis is not None:
        return (False, "not_exact:" + axis)
    return (True, None)


# --- Availability policy (schema.org-complete; never raises) ----------------
_OOS_AVAIL_TOKENS = ("outofstock", "soldout", "discontinued")
# PreOrder / BackOrder / PreSale / MadeToOrder = buyable-but-FUTURE → not a CURRENT
# shelf price → pend.
_FUTURE_AVAIL_TOKENS = ("preorder", "backorder", "presale", "madetoorder")
_INSTOCK_AVAIL_TOKENS = ("instock", "onlineonly", "limitedavailability", "instoreonly")


def _availability_text(raw: Any) -> str:
    """Flatten any schema.org availability shape (str, URL form, None, list, dict)
    to a lowercased, NON-ALPHANUMERIC-STRIPPED token blob — never raises (the literal
    substring check upstream TypeErrors on None/list/dict). Stripping spaces/slashes
    collapses the display form "Out of Stock" / "Sold Out" and the URL form
    ".../OutOfStock" to the same compact token the OOS/instock sets match on."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return re.sub(r"[^a-z0-9]", "", raw.lower())
    if isinstance(raw, (list, tuple, set)):
        return " ".join(_availability_text(x) for x in raw)
    if isinstance(raw, dict):
        return " ".join(_availability_text(v) for v in raw.values())
    return re.sub(r"[^a-z0-9]", "", str(raw).lower())


def is_available_state(raw: Any) -> Optional[bool]:
    """Tri-state availability: True (in stock), False (OOS/SoldOut/Discontinued/
    PreOrder/BackOrder — not a current buyable shelf price), or None (unknown — no
    signal; treated as showable so clean adapters that omit the field never
    false-pend)."""
    t = _availability_text(raw)
    if not t:
        return None
    if any(tok in t for tok in _OOS_AVAIL_TOKENS):
        return False
    if any(tok in t for tok in _FUTURE_AVAIL_TOKENS):
        return False
    if any(tok in t for tok in _INSTOCK_AVAIL_TOKENS):
        return True
    return None


def _is_listing_url(url: Optional[str]) -> bool:
    """True iff `url` is a non-PDP listing/search/category surface (lazy import of
    source_router.is_non_pdp_listing_url — same module-internal lazy pattern as
    the SOURCE_REGISTRY use below). A missing url is NOT a listing url (benign)."""
    if not url:
        return False
    try:
        from app.services.source_router import is_non_pdp_listing_url
        return is_non_pdp_listing_url(url)
    except Exception:  # noqa: BLE001 — a URL-classifier failure must never pend a price
        return False


def _candidate_authority(cand: Dict[str, Any], category: Optional[str]) -> float:
    """Retailer authority for select_best — registry weight (score_source, 0.5-3.0)
    blended with the candidate's own retailer_score (0..1 → ×3 onto the same scale,
    so a 1.0 official-domain hit reaches 3.0). Higher = more authoritative."""
    score = 0.5
    url = cand.get("url") or ""
    if url:
        try:
            from app.services.source_router import score_source
            score = score_source(url, category or "")
        except Exception:  # noqa: BLE001
            score = 0.5
    rs = cand.get("retailer_score")
    if isinstance(rs, (int, float)):
        score = max(score, float(rs) * 3.0)
    return score


def select_best(
    candidates: List[Dict[str, Any]], query_name: str, category: Optional[str] = None,
    *, drop_out_of_stock: bool = True, require_url: bool = True,
    stable_tiebreak: bool = False,
) -> Optional[Dict[str, Any]]:
    """Pick the single best price among `candidates` by RETAILER AUTHORITY — NEVER
    cheapest. Among candidates that have a verifiable IDENTITY (title/name), are
    identity-matched (_selection_match), ∧ are on a valid PDP URL, rank IN-STOCK
    first, then authority, then variant precision (closer to the stated size/
    concentration), then amount as the LAST tiebreak.

    `drop_out_of_stock` (default True — the Tier-2 cross-adapter consume's contract:
    an out-of-stock genuine hit must NOT short-circuit the cascade, so it returns
    None and the cascade keeps looking). Adapters / the JSON-LD extractor pass
    False: there an explicitly out-of-stock candidate is RANKED LAST but still
    RETURNED (flagged in_stock=False) when it is the only match, so the existing
    "report OOS" behaviour is preserved and the response chokepoint pends it.

    `require_url` (default True — fail-CLOSED on a candidate with no PDP URL, B5):
    a price with no verifiable PDP can't be confirmed CURRENT, so it pends. The
    JSON-LD within-page extractor passes False (its candidates are page-internal —
    the page URL is stamped onto the result by the caller, so requiring a
    per-candidate URL there would wrongly drop every JSON-LD match).

    `stable_tiebreak` (default False — byte-identical for ALL existing callers,
    ENABLE_GENUINE_PRICE_PRIORITY determinism item 1): when True, ties past
    `amount` resolve lexicographically on (retailer, url) instead of Python
    stable-sort insertion order, so equal-authority/precision/amount candidates
    pick the SAME winner regardless of arrival order across runs. It is the
    LAST tiebreak — authority/precision/amount ordering is unchanged.

    Returns None when no candidate qualifies. Rollback: with the gate OFF this
    restores the legacy cheapest-pick (min amount)."""
    cands = [
        c for c in (candidates or [])
        if isinstance(c, dict)
        and isinstance(c.get("amount"), (int, float))
        and c.get("amount", 0) > 0
    ]
    if not cands:
        return None
    if not exact_gate_enabled():
        return min(cands, key=lambda c: c["amount"])
    eligible: List[Dict[str, Any]] = []
    for c in cands:
        if drop_out_of_stock and c.get("in_stock") is False:
            continue
        # B5 — no IDENTITY (title/name) → can't verify the product → fail-closed.
        title = c.get("title") or c.get("name") or ""
        if not title:
            continue
        # An electronics ACCESSORY (Galaxy S24 *Case* / *Charger*) is not the device —
        # the shared authority selector did not reject it. Narrow set + electronics gate
        # so a genuine standalone keyboard / Sony WH-1000XM5 / earbuds is NOT pended.
        if ((category or "").lower() == "electronics"
                and _is_device_accessory(title) and not _is_device_accessory(query_name)):
            continue
        # B5 — require a valid PDP URL (fail-closed on missing url). A listing/search
        # URL is rejected even when require_url is False (it is never a PDP).
        url = c.get("url")
        if require_url and not url:
            continue
        if url and _is_listing_url(url):
            continue
        brand = c.get("brand") or ""
        if not _selection_match(query_name, title, category, candidate_brand=brand):
            continue
        # Wave C (kpiE2E re-sweep RS-2) — the BF1 wrong-brand fence on the
        # shared selector: the organic-harvest → JSON-LD route reaches
        # select_best with NO adapter fence in the path, so a wrong-brand /
        # brandless same-model-word fashion row was picked (then shown +
        # cached). Same centralized helper as the adapter fallthroughs.
        if not _brand_evidence_ok(
            query_name, title, candidate_brand=str(brand), category=category,
        ):
            continue
        eligible.append(c)
    if not eligible:
        return None
    def _precision(c: Dict[str, Any]) -> float:
        title = c.get("title") or c.get("name") or ""
        cr, sr = variant_precision_rank(query_name, title)
        return float(cr + sr)
    def _sort_key(c: Dict[str, Any]):
        key = (
            c.get("in_stock") is False,   # in-stock (False) sorts before OOS (True)
            -_candidate_authority(c, category),
            -_precision(c),
            c["amount"],
        )
        if stable_tiebreak:
            # Lexicographic FINAL tiebreak (determinism) — only extends the
            # tuple; default False keeps the key byte-identical.
            key = key + (str(c.get("retailer") or ""), str(c.get("url") or ""))
        return key
    eligible.sort(key=_sort_key)
    return eligible[0]


def query_confirmed_structured_code(code: Any, query_words: set) -> str:
    """Normalize + validate a structured MODEL code (a retailer's style_code /
    SKU stem) against the QUERY's normalized words. The code is a match ENABLER
    only when:
      - letter+digit shaped (a pure-digit code — "00501-0660" — is catalog
        plumbing, not a model assertion; it would inject numeric noise / bridge
        different models), AND
      - present as a query token (hyphen-folded, as normalize_words folds) —
        an UNQUERIED code appended to a surface would read as a variant-add
        and over-reject / a relaxation it never earned.
    Returns the stripped code on success, "" otherwise. Shared by the algolia
    matcher override (Wave A3, _confirmed_style_code) and the
    should_cache_price parity override (Wave B0) so the two ends never drift.

    Tightened (Wave B-FIX BF2, sweep L3): letter+digit SHAPE alone admitted
    tokens that assert nothing about the exact SKU —
      - a pure MEASURE ("100ML"/"2LB"/"1TB", _IDENTITY_MEASURE_STRIP_RE) or a
        CLOTHING SIZE ("2XL", _CLOTHING_SIZE_RE) is a size, not a model; it
        waived the ONLY gate rejecting the Elixir flanker / wrong-variant;
      - a short FAMILY stem without a >=2-digit run ("AF1") names a LINE the
        base/Kids/GS/LV8 variants all share, not an exact SKU.
    Real model codes (L1212, NKCW4554-001) carry a multi-digit run and keep
    confirming."""
    if not isinstance(code, str):
        return ""
    tok = code.strip()
    if not tok:
        return ""
    if not (any(c.isalpha() for c in tok) and any(c.isdigit() for c in tok)):
        return ""
    low = tok.lower()
    if (_IDENTITY_MEASURE_STRIP_RE.fullmatch(low)
            or _CLOTHING_SIZE_RE.fullmatch(low)):
        return ""
    if not re.search(r"\d{2}", low):
        return ""
    if low.replace("-", "") not in query_words:
        return ""
    return tok


# Wave B-FIX BF2 (sweep L3) — sellable-UNIT markers that flip a title to a
# DIFFERENT purchasable SKU even under a retailer-confirmed MODEL code (a
# style code asserts the model, never the unit): kids / grade-school sizing,
# gift sets, testers, decants. BOUNDED list, asymmetric (a query that itself
# states the marker is unaffected), and consulted ONLY inside the structured
# -code override — it can never over-reject a candidate the normal
# _selection_match gates accept.
_STRUCTURED_OVERRIDE_BLOCK_TOKENS = frozenset({
    "kids", "kid", "gs", "gift", "set", "tester", "decant",
    # Wave C (re-sweep RS3) — the sibling kid-SEGMENT and bundle wordings GCC
    # stores actually use ("Boys"/"Girls"/"Junior" on 6thstreet, "with Cap
    # Bundle"): each is a differently-priced sellable unit sharing the model's
    # style code, so the confirmed code must not waive the variant fence.
    "boys", "girls", "junior", "youth", "toddler", "bundle", "combo",
    # Wave D (convergence CV1) — the RS3 fix's own blind spot: baby/infant
    # (listed in the original RS3 fix-direction, dropped by C1) and the
    # MULTIPACK sellable-unit wordings ("Twin Pack" / "2-Pack" / "Multipack"
    # — common GCC polo/tee listings). normalize_words FOLDS hyphens
    # ("twin-pack" -> "twinpack") and SPLITS spaced forms ("twin pack" ->
    # {"twin","pack"}); the bare "pack" covers every spaced
    # "<n>/Twin/Value/Multi Pack" form (an added "pack" is always a
    # different sellable unit — same asymmetry: a query stating it is
    # unaffected, and candidates the normal _selection_match accepts never
    # consult this set).
    # Wave D polish (review W2) — bare "twin" is deliberately NOT listed:
    # it over-rejected Fred Perry "Twin Tipped" MAINLINE polos and is
    # redundant for the multipack class ("pack" catches the spaced form,
    # the glued tokens catch "twin-pack"/"twinpack"). "baby" IS listed but
    # bounded in _structured_override_variant_blocked: the "Baby Blue" /
    # "Baby Pink" COLORWAY bigram is a shade name, not the infant segment.
    "baby", "infant", "pack", "multipack",
    "twinpack", "twopack", "2pack", "3pack", "4pack", "5pack", "6pack",
})

# Wave D polish (review W2) — the COLORWAY sense of "baby": "Baby Blue" /
# "Baby Pink" name a SHADE on an adult mainline SKU (Lacoste "L1212 Polo
# Baby Blue"), not the infant garment segment. Hyphen family included for
# symmetry with the C2 _UNICODE_HYPHENS canon (normalize_words glues
# hyphenated bigrams anyway, so only the spaced form ever surfaces "baby").
_BABY_COLORWAY_BIGRAM_RE = re.compile(
    rf"\bbaby[\s\-{_UNICODE_HYPHENS}]+(?:blue|pink)\b", re.I,
)


def _structured_override_variant_blocked(query_name: str, surface: str) -> bool:
    """True when the candidate surface ADDS a kids/gs/gift-set/tester/decant
    marker the query never stated — the structured-code override must keep the
    variant-add fence UP for those (sweep L3: 'L1212 Polo Gift Set with Cap'
    rode the confirmed code). Shared by both override ends.

    Wave D polish (review W2): "baby" is exempt when EVERY surface occurrence
    is part of the "Baby Blue"/"Baby Pink" COLORWAY bigram (a shade name, not
    the infant segment); any bare occurrence — "Polo Baby - 6-12 months", or
    a surface carrying BOTH senses — keeps blocking (fail-closed)."""
    added = normalize_words(surface) & _STRUCTURED_OVERRIDE_BLOCK_TOKENS
    if "baby" in added and not re.search(
            r"\bbaby\b", _BABY_COLORWAY_BIGRAM_RE.sub(" ", surface.lower())):
        added = added - {"baby"}
    if not added:
        return False
    return bool(added - normalize_words(query_name))


def _structured_code_cache_override(
    request_name: str, price: Dict[str, Any], title: str, category: Optional[str],
) -> bool:
    """Wave-B cache-gate PARITY with the adapter-side structured-identity
    override (Wave A3, algolia _catalog_match_hit/_match_algolia_hit): a
    QUERY-CONFIRMED structured model code carried on the price dict
    (`structured_code`, stamped by the adapter whose matcher accepted the hit)
    is the retailer's own exact-model assertion — descriptive title words
    around a confirmed code are noise, not a variant-add ("Logo Detail Short
    Sleeves Polo T-Shirt" + style_code L1212 IS the queried Lacoste L1212).
    ONLY the superset/variant-add rejection is relaxed; the SAME bounds the
    adapter override enforces stay enforced here, fail-closed:
      - the code must be letter+digit shaped AND appear as a token in the
        QUERY (query_confirmed_structured_code — an unqueried code relaxes
        NOTHING);
      - LEAK direction: every query discriminator must appear in the
        brand+title+code surface (strict_title_match, candidate_brand-aware —
        a WRONG-brand stamp keeps the query's own brand token required and
        still rejects);
      - significant query numbers must match (numbers_match);
      - the contradiction/numeric axes stay enforced (_axis_mismatch, with
        _selection_match's explicit-"other" re-inference mirrored).
    Everything else in should_cache_price (identity/URL/OOS/accessory checks)
    ran BEFORE this override. Flag-OFF never reaches here (should_cache_price
    early-returns True)."""
    code = query_confirmed_structured_code(
        price.get("structured_code"), normalize_words(request_name),
    )
    if not code:
        return False
    brand = price.get("brand")
    brand = brand.strip() if isinstance(brand, str) else ""
    surface = " ".join(part for part in (brand, title, code) if part)
    # BF2 (sweep L3): a kids/gs/gift-set/tester/decant ADD is a different
    # sellable unit — the confirmed code never waives that fence.
    if _structured_override_variant_blocked(request_name, surface):
        return False
    if not numbers_match(request_name, surface):
        return False
    if not strict_title_match(request_name, surface, candidate_brand=brand):
        return False
    cat = category
    if (cat or "").lower() == "other":
        cat = _infer_category_from_query(request_name) or cat
    return not _axis_mismatch(request_name, surface, cat, brand)


# ============================================================================
# WAVE-2 B3a — CURATED VARIANT-HINT REFERENCE + WARM-CONTEXT CACHE-WRITE VETO
# ============================================================================
# The 2+1 warmer-writable POISON classes (residual-census.json) —
#   gender_flanker_base_to_femme (Versace Eros -> Eros Pour Femme),
#   spf_one_sided_add            (CeraVe Lotion -> +SPF 30),
#   makeup_one_sided_formula_add (Fit Me Matte -> Fit Me Dewy)
# — PASS should_cache_price today: they pass _selection_match (they are the HELD
# DISPLAY tradeoffs — symmetrizing them mass-over-rejects correct products, the
# proven revert). A live-origin flanker is the already-accepted low-frequency
# display trade; the AMPLIFIED harm is the CRON WARMER writing such a row
# CONTINUOUSLY under the genuine 7d TTL, served to everyone. So the veto fires
# ONLY off-clock/warm — the live 15s path + is_price_showable display stay
# BYTE-IDENTICAL. A vetoed price still RESOLVES + DISPLAYS; the warmer merely
# skips caching that row.
#
# WARM-CONTEXT DISCRIMINATOR (belt-and-braces per descriptor-design.json R3):
#   (a) the WARMER_CONTEXT env the off-clock scripts export
#       (cron_warm_price_cache / warm_kpi_truth / measure_warmed_kpi /
#        seed_zyte_luxury), AND
#   (b) an explicit warm_context=True kwarg a caller may force.
# The veto activates when EITHER warm signal is present (an env alone can leak
# into a dev server, so a caller can also force it; a script that forgets the
# env can still pass the kwarg — either path arms it, neither is required to be
# both). The LIVE web request never sets the env nor passes the kwarg, so
# should_cache_price on the live path is byte-identical.
#
# The whole thing is gated behind variant_descriptor_axes_enabled() (which
# hard-requires the exact gate): flag-OFF -> byte-identical, curated ref is
# deterministic/$0 but stays flag-gated to keep the merge clean.

_VARIANT_HINT_REFERENCE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "variant_hint_reference.json",
)


@functools.lru_cache(maxsize=1)
def _load_variant_hint_reference() -> Dict[str, Any]:
    """Load data/variant_hint_reference.json ONCE (module-level memo, the
    bh_gcc_sources.json committed-data precedent). Missing/malformed -> empty
    sections (every lookup then returns 'unknown' -> fail-closed veto). Never
    raises."""
    try:
        with open(_VARIANT_HINT_REFERENCE_PATH, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict):
            return {}
        return doc
    except Exception as exc:  # noqa: BLE001 — reference is additive, never fatal
        logger.warning("[variant_hint] reference load failed: %s", exc)
        return {}


def _vh_longest_base_match(folded: str, keys) -> Optional[str]:
    """The LONGEST curated base-line key contained (whitespace-boundary) in
    `folded`, or None. Longest-key wins so 'sauvage elixir' beats 'sauvage'
    when both are present."""
    best = None
    for k in keys:
        if not k or k.startswith("_"):
            continue
        # containment on a padded string so 'si' does not match inside 'basil'.
        if f" {k} " in f" {folded} ":
            if best is None or len(k) > len(best):
                best = k
    return best


def _strip_trailing_spf_token(folded: str) -> str:
    """Remove a TRAILING standalone 'spf'/'spf <n>' AND a trailing standalone
    'sunscreen' token (repeatedly, in either interleaved order) from a folded
    string.

    B3-FIX (spf) + Wave-2 FINALIZE (sunscreen): a candidate can self-shadow a
    non_sunscreen base into a phantom inherent match by appending EITHER its own
    'spf'/'spf NN' suffix OR the standalone word 'sunscreen' (or BOTH, e.g.
    'cetaphil moisturizing' -> '...moisturizing sunscreen spf 30', where the
    surviving 'moisturizing sunscreen' out-lengths the non_sunscreen stem). We
    strip ONLY at the END, and this is called ONLY when a non_sunscreen base has
    already matched -- so a genuine sunscreen name that carries 'sunscreen'/'spf'
    as a NON-trailing part (anthelios/capital soleil never reach here; coppertone
    sport 'sunscreen lotion spf 50' keeps its inner 'sunscreen') is unaffected,
    and its inherent line still wins. Iterates so any trailing mix of the two
    tokens is peeled off."""
    if not folded:
        return folded
    stripped = folded
    _trailing = re.compile(r"\s+(?:spf(?:\s+\d+)?|sunscreen)\s*$")
    while True:
        nxt = _trailing.sub("", stripped).strip()
        if nxt == stripped:
            break
        stripped = nxt
    return stripped or folded


def _variant_hint_lookup(category: Optional[str], query_name: str,
                         candidate_title: str, axis: str) -> str:
    """Deterministic $0 reader over data/variant_hint_reference.json.

    Returns "distinct" | "same" | "unknown" for the given `axis` in
    {"gender", "spf", "formula"}. The base line is matched by LONGEST-key
    CONTAINMENT in the folded query (falls back to the candidate when the query
    is terse and omits the line word). A base-line MISS -> "unknown" (the
    caller fail-closes)."""
    ref = _load_variant_hint_reference()
    qf = _fold_identity(query_name or "")
    cf = _fold_identity(candidate_title or "")

    if axis == "gender":
        table = ref.get("fragrance_base_gender") or {}
        base = _vh_longest_base_match(qf, table.keys()) or _vh_longest_base_match(cf, table.keys())
        if base is None:
            return "unknown"
        base_gender = table.get(base)
        # The gender the CANDIDATE adds (candidate stated, query did not).
        cand_gender = _gender_of(candidate_title)
        if cand_gender is None or base_gender is None:
            return "unknown"
        return "same" if cand_gender == base_gender else "distinct"

    if axis == "spf":
        spf_section = ref.get("inherent_spf_lines") or {}
        inherent = spf_section.get("lines") or []
        non_sun = spf_section.get("non_sunscreen_lines") or []
        # A KNOWN non-sunscreen line: the SPF add is a distinct variant -> DISTINCT.
        non = _vh_longest_base_match(qf, non_sun) or _vh_longest_base_match(cf, non_sun)
        # SELF-SHADOW HARDENING (B3-FIX + Wave-2 FINALIZE): the candidate's OWN
        # trailing "spf"/"spf NN" AND/OR standalone "sunscreen" suffix must not
        # extend a non_sunscreen stem into a phantom inherent match (e.g.
        # "hydro boost water gel" + " spf 25" matching an inherent line; or
        # "cetaphil moisturizing" + " sunscreen spf 30" where the surviving
        # "moisturizing sunscreen" out-lengths the non_sunscreen stem). When the
        # base already matched a non_sunscreen line, strip trailing standalone
        # "spf"/"spf <n>"/"sunscreen" tokens from the text used to match the
        # INHERENT lines, so an inherent win must come from a genuine sunscreen
        # name that carries "spf"/"sunscreen" as a NON-trailing part
        # (anthelios / capital soleil / coppertone sport 'sunscreen lotion spf'
        # are unaffected -- their base is not a non_sunscreen line so the strip
        # never engages).
        qf_inh, cf_inh = qf, cf
        if non:
            qf_inh = _strip_trailing_spf_token(qf)
            cf_inh = _strip_trailing_spf_token(cf)
        # An inherent-SPF line: the SPF add is descriptive of the base -> SAME.
        inh = (_vh_longest_base_match(qf_inh, inherent)
               or _vh_longest_base_match(cf_inh, inherent))
        # When BOTH match (a longer non-sunscreen key vs a shorter inherent key or
        # vice versa) prefer the LONGER, more-specific base line.
        if inh and (not non or len(inh) >= len(non)):
            return "same"
        if non:
            return "distinct"
        # Base in NEITHER list. We CANNOT prove it is a distinct SKU from tokens
        # alone (the exact reason the display axis is HELD), so a MISS is UNKNOWN
        # -> fail-closed veto (never a wrong cache).
        return "unknown"

    if axis == "formula":
        table = ref.get("makeup_formula_lines") or {}
        base = _vh_longest_base_match(qf, table.keys()) or _vh_longest_base_match(cf, table.keys())
        if base is None:
            return "unknown"
        distinct_tokens = set(table.get(base) or [])
        cand_forms = extract_variant_descriptor(candidate_title, "makeup").finishes
        query_forms = extract_variant_descriptor(query_name, "makeup").finishes
        added = (cand_forms - query_forms) & distinct_tokens
        # The candidate ADDS a distinct formula sub-line token the query lacks
        # AND that token is a DISTINCT sub-line of this base -> DISTINCT.
        return "distinct" if added else "same"

    return "unknown"


def _warm_context_active(warm_context: bool = False) -> bool:
    """True iff the OFF-CLOCK warm signal is present: the explicit
    warm_context kwarg OR the WARMER_CONTEXT env the warm/seed/measure scripts
    export (belt-and-braces, R3). Read FRESH so a script's os.environ set before
    import is honored and a live request (neither set) is never armed."""
    if warm_context:
        return True
    return os.getenv("WARMER_CONTEXT", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _detect_ambiguous_variant_axes(
    request_name: str, title: str, category: Optional[str],
) -> List[str]:
    """The ordered list of Class-B AMBIGUOUS axes the candidate ADDS that the
    query lacks: any subset of ["gender", "spf", "formula"] in warmer_write_veto's
    original branch order. The SHARED axis detector for both the sync curated veto
    and the async LLM-hint path so the two never drift. Returning ALL applicable
    axes (not just the first) preserves B3a's fall-through semantics: a 'same'
    gender verdict then still checks spf, exactly as the original sequential
    branches did."""
    cat = (category or "").lower()
    qd = extract_variant_descriptor(request_name, category)
    cd = extract_variant_descriptor(title, category)
    axes: List[str] = []
    # --- gender flanker base->femme (fragrance/beauty + fashion) ---
    if (cat in _FRAGRANCE_BEAUTY_CATEGORIES or cat == "fashion") \
            and cd.gender and not qd.gender:
        axes.append("gender")
    # --- one-sided SPF add (skincare/makeup/haircare — category-independent) ---
    if cd.spfs and not qd.spfs:
        axes.append("spf")
    # --- makeup one-sided formula add ---
    if cat == "makeup" and (cd.finishes - qd.finishes):
        axes.append("formula")
    return axes


# ---------------------------------------------------------------------------
# Wave-2 B3b — the NARROW OFF-CLOCK LLM variant-hint (curated-miss fallback).
#
# When the curated reference (_variant_hint_lookup) returns "unknown" on a
# Class-B ambiguous axis, B3a fail-closes (vetoes the write). B3b recovers the
# CORRECT-product misses whose family is not yet in the curated reference, by
# consulting a NARROW disambiguator — but ONLY when EVERY hard invariant holds:
#   (1) variant_descriptor_axes_enabled()  (hard-requires the exact gate)
#   (2) ENABLE_VARIANT_LLM_HINT            (default OFF)
#   (3) the OFF-CLOCK warm signal          (WARMER_CONTEXT env / warm_context arg
#                                           / allow_llm_hint arg)
#   (4) _variant_hint_lookup returned "unknown".
# The LLM is NEVER constructed on the live 15s path (no warm signal -> the
# machinery is never reached). Consulted at cache-WRITE time only.
#
# CACHE: a Redis verdict cache varhint:<sha12(normalized_family, axis)> TTL 90d
# (product-line facts are stable). A HIT short-circuits ($0) — and the LIVE path
# MAY read this $0 cache (a filled verdict costs nothing) but must NEVER call the
# LLM. On a MISS: the async path calls gpt-4o-mini (temperature=0, json_object),
# caches the verdict, optionally appends to data/variant_hint_learned.json for
# convergence. FAIL-CLOSED default (flag off / low confidence / client error /
# per-run cap exceeded / "unknown" response) = VETO the write (never cache an
# unverified identity). Only a HIGH-confidence answer acts:
#   distinct + high -> veto ; same + high -> allow ; else -> fail-closed veto.
#
# PER-RUN CAP: VARHINT_MAX_CALLS_PER_RUN (default 40, mirrors
# WARMER_MAX_SERPER_CREDITS_PER_RUN). Beyond the cap -> fail-closed veto WITHOUT
# calling the LLM. The counter is a process-local module global (a warm run is a
# single process; reset at import / via _reset_varhint_run_state for tests).
# ---------------------------------------------------------------------------
_VARHINT_VERDICT_TTL_SECONDS = 90 * 24 * 3600  # 90d — product-line facts are stable
_VARHINT_LEARNED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "variant_hint_learned.json",
)
# Process-local per-run LLM-call counter (a warm run = one process).
_varhint_calls_this_run = 0


def variant_llm_hint_enabled() -> bool:
    """True iff the B3b LLM-hint machinery is active. Default OFF, read FRESH per
    call (the adapter_selection_primary_enabled :5027 idiom). HARD-REQUIRES the
    variant-descriptor axes (which in turn hard-require the exact gate), so the
    hint never exists in a rollback state and flag-OFF is byte-identical."""
    if not variant_descriptor_axes_enabled():
        return False
    return os.getenv("ENABLE_VARIANT_LLM_HINT", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _varhint_max_calls_per_run() -> int:
    """Per-run LLM-call cap (mirrors WARMER_MAX_SERPER_CREDITS_PER_RUN). Beyond
    the cap the hint fail-closes WITHOUT calling. Default 40; non-numeric -> 40."""
    try:
        return max(0, int(os.getenv("VARHINT_MAX_CALLS_PER_RUN", "40")))
    except (TypeError, ValueError):
        return 40


def _reset_varhint_run_state() -> None:
    """Reset the process-local per-run LLM-call counter. Called at warm-run start
    (and by tests). No-op-safe."""
    global _varhint_calls_this_run
    _varhint_calls_this_run = 0


def _varhint_normalized_family(query_name: str, candidate_title: str, axis: str) -> str:
    """The stable normalized-family string the verdict cache is keyed on. Uses the
    SAME curated base-line match as _variant_hint_lookup so a cached verdict is
    reused across the many candidate titles that share one product line; falls
    back to the folded query when no curated line matches (the exact curated-miss
    case B3b exists to resolve). The axis is folded in by the caller's sha12."""
    ref = _load_variant_hint_reference()
    qf = _fold_identity(query_name or "")
    cf = _fold_identity(candidate_title or "")
    table_keys: List[str] = []
    if axis == "gender":
        table_keys = list((ref.get("fragrance_base_gender") or {}).keys())
    elif axis == "spf":
        spf = ref.get("inherent_spf_lines") or {}
        table_keys = list(spf.get("lines") or []) + list(spf.get("non_sunscreen_lines") or [])
    elif axis == "formula":
        table_keys = list((ref.get("makeup_formula_lines") or {}).keys())
    base = _vh_longest_base_match(qf, table_keys) or _vh_longest_base_match(cf, table_keys)
    return base or qf


def _varhint_verdict_key(query_name: str, candidate_title: str, axis: str) -> str:
    """varhint:<sha12(normalized_family + '|' + axis)> — the Redis verdict-cache
    key. Product-line facts are family-stable, so the family (not the raw title)
    is the cache axis."""
    family = _varhint_normalized_family(query_name, candidate_title, axis)
    digest = hashlib.sha256(f"{family}|{axis}".encode("utf-8")).hexdigest()[:12]
    return f"varhint:{digest}"


def _varhint_read_verdict_cache(key: str) -> Optional[str]:
    """Read a cached LLM verdict ("distinct"|"same") from Redis, or None on miss /
    Redis-down / malformed. $0 — the LIVE path may call this (never the LLM)."""
    try:
        from app.services.cache_service import _redis_get
        raw = _redis_get(key)
    except Exception:  # noqa: BLE001 — Redis is a soft dependency (fail-open read)
        return None
    if raw in ("distinct", "same"):
        return raw
    return None


def _varhint_write_verdict_cache(key: str, verdict: str) -> None:
    """Persist a resolved HIGH-confidence LLM verdict to Redis (90d TTL). Only
    'distinct'/'same' are cached (never 'unknown' — an unknown must re-resolve)."""
    if verdict not in ("distinct", "same"):
        return
    try:
        from app.services.cache_service import _redis_set
        _redis_set(key, verdict, ex=_VARHINT_VERDICT_TTL_SECONDS)
    except Exception:  # noqa: BLE001 — cache write is best-effort
        pass


def _varhint_append_learned(family: str, axis: str, verdict: str) -> None:
    """Append a resolved verdict to data/variant_hint_learned.json for convergence
    (the committed-data precedent). Best-effort; never raises. Keyed 'family|axis'."""
    if verdict not in ("distinct", "same"):
        return
    try:
        doc: Dict[str, Any] = {}
        if os.path.exists(_VARHINT_LEARNED_PATH):
            with open(_VARHINT_LEARNED_PATH, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    doc = loaded
        doc[f"{family}|{axis}"] = verdict
        with open(_VARHINT_LEARNED_PATH, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=True, indent=2, sort_keys=True)
    except Exception:  # noqa: BLE001 — learned-file is additive, never fatal
        pass


async def _consult_variant_llm_hint(
    category: Optional[str], query_name: str, candidate_title: str, axis: str,
) -> str:
    """The async curated-miss fallback. Returns "distinct" | "same" | "unknown".

    ORDER: (a) Redis verdict cache HIT -> return it ($0, NO client construction).
    (b) MISS: enforce the per-run cap (beyond it -> "unknown" WITHOUT calling),
    else call disambiguate_variant_line; only a HIGH-confidence answer resolves
    to distinct/same (cached + learned); anything else -> "unknown" (the caller
    fail-closes). NEVER raises."""
    global _varhint_calls_this_run
    key = _varhint_verdict_key(query_name, candidate_title, axis)
    cached = _varhint_read_verdict_cache(key)
    if cached is not None:
        return cached
    # Cache miss -> the LLM would be called. Enforce the per-run cap FIRST so the
    # (N+1)th consult fails-closed WITHOUT constructing a client.
    if _varhint_calls_this_run >= _varhint_max_calls_per_run():
        return "unknown"
    _varhint_calls_this_run += 1
    from app.services import openai_service
    result = await openai_service.disambiguate_variant_line(
        category, query_name, candidate_title, axis,
    )
    distinct = result.get("distinct_product")
    conf = str(result.get("confidence") or "").lower()
    if conf != "high":
        return "unknown"
    if distinct is True:
        verdict = "distinct"
    elif distinct is False:
        verdict = "same"
    else:
        return "unknown"
    _varhint_write_verdict_cache(key, verdict)
    _varhint_append_learned(
        _varhint_normalized_family(query_name, candidate_title, axis), axis, verdict,
    )
    return verdict


def _apply_variant_verdict(axis: str, verdict: str) -> Optional[Tuple[bool, str]]:
    """Map a per-axis verdict to a (allow, reason) veto decision, or None when the
    verdict is 'same' (allow — let the caller continue to the next axis / final
    allow). Shared by the sync + async vetoes so the reason strings never drift.
      distinct -> (False, "<axis>_..._distinct")
      unknown  -> (False, "<axis>_..._unknown_failclosed")
      same     -> None (allow)."""
    reason_stem = {
        "gender": "gender_flanker", "spf": "spf_add", "formula": "formula_add",
    }.get(axis, axis)
    if verdict == "distinct":
        return False, f"{reason_stem}_distinct"
    if verdict == "unknown":
        return False, f"{reason_stem}_unknown_failclosed"
    return None  # "same" -> allow


def warmer_write_veto(
    request_name: str, price: Optional[Dict[str, Any]], category: Optional[str] = None,
    *, warm_context: bool = False,
) -> Tuple[bool, Optional[str]]:
    """The WARM-CONTEXT cache-write veto for the 2+1 warmer-writable poison
    classes. Returns (allow, reason). SYNCHRONOUS — the deterministic curated
    path, plus a $0 read of the B3b Redis verdict cache when the hint is enabled
    (NEVER an LLM call — that lives only in warmer_write_veto_async).

    NO-OP (returns (True, None)) unless BOTH: the warm signal is present
    (_warm_context_active) AND variant_descriptor_axes_enabled(). So the live
    15s path is byte-identical (no warm signal) and flag-OFF is byte-identical.

    When armed, detects a Class-B AMBIGUOUS axis the candidate ADDS that the
    query lacks (gender / spf / makeup formula), consults _variant_hint_lookup:
      "distinct" -> veto (do NOT cache — a different SKU);
      "same"     -> allow (descriptive of the same product);
      "unknown"  -> (B3b) when variant_llm_hint_enabled(), first try the $0 Redis
                    verdict cache; a cached distinct/same acts, else FAIL-CLOSED
                    veto (the LLM is only consulted in the async variant).
    is_price_showable is deliberately NOT touched — display stays as today."""
    if not _warm_context_active(warm_context) or not variant_descriptor_axes_enabled():
        return True, None
    if not isinstance(price, dict):
        return True, None
    title = price.get("title") or price.get("name") or ""
    if not title:
        return True, None
    for axis in _detect_ambiguous_variant_axes(request_name, title, category):
        verdict = _variant_hint_lookup(category, request_name, title, axis)
        if verdict == "unknown" and variant_llm_hint_enabled():
            # B3b sync path: consult ONLY the $0 Redis verdict cache — NEVER the
            # LLM (a live request may benefit from an already-resolved verdict at
            # $0, but a network call belongs to the async off-clock variant).
            cached = _varhint_read_verdict_cache(
                _varhint_verdict_key(request_name, title, axis)
            )
            if cached is not None:
                verdict = cached
        decision = _apply_variant_verdict(axis, verdict)
        if decision is not None:
            return decision
    return True, None


async def warmer_write_veto_async(
    request_name: str, price: Optional[Dict[str, Any]], category: Optional[str] = None,
    *, warm_context: bool = False, allow_llm_hint: bool = False,
) -> Tuple[bool, Optional[str]]:
    """OFF-CLOCK async variant of warmer_write_veto. Identical to the sync veto,
    EXCEPT that on a curated "unknown" it consults the B3b LLM hint
    (Redis-verdict-cache first, then a capped gpt-4o-mini call). The LLM is
    constructed/called ONLY when ALL hold:
      variant_llm_hint_enabled()  (axes + ENABLE_VARIANT_LLM_HINT + exact gate)
      AND the warm signal          (warm_context / WARMER_CONTEXT / allow_llm_hint)
      AND _variant_hint_lookup == "unknown".
    A live request never passes warm_context/allow_llm_hint and never sets
    WARMER_CONTEXT, so this coroutine's LLM branch is unreachable from the 15s
    path. Fail-closed on every uncertainty (low confidence / cap / error /
    'unknown' response) -> veto the write."""
    warm = _warm_context_active(warm_context) or bool(allow_llm_hint)
    if not warm or not variant_descriptor_axes_enabled():
        return True, None
    if not isinstance(price, dict):
        return True, None
    title = price.get("title") or price.get("name") or ""
    if not title:
        return True, None
    for axis in _detect_ambiguous_variant_axes(request_name, title, category):
        verdict = _variant_hint_lookup(category, request_name, title, axis)
        if verdict == "unknown" and variant_llm_hint_enabled():
            verdict = await _consult_variant_llm_hint(
                category, request_name, title, axis,
            )
        decision = _apply_variant_verdict(axis, verdict)
        if decision is not None:
            return decision
    return True, None


def should_cache_price(
    request_name: str, price: Optional[Dict[str, Any]], category: Optional[str] = None,
    *, warm_context: bool = False,
) -> bool:
    """B6 — gate a cache WRITE on the RESOLVED identity matching the request, so a
    wrong candidate (which a permissive matcher might once have let through) can NEVER
    be cached under the requested product for the genuine TTL.

    Uses the SAME matcher (`_selection_match`) the selector ran, so it NEVER blocks a
    legitimately-selected price (defense-in-depth for the non-select_best writes:
    iHerb / pharmacy / converted). Returns True (allow) when there is nothing to
    verify against (no title to compare, or no request) — an estimated price has its
    own honesty + TTL. No-op (True) when the rollback flag is OFF.

    WAVE-2 B3a — when the OFF-CLOCK warm signal is present (WARMER_CONTEXT env or
    warm_context=True) AND the axes flag is on, the base decision is additionally
    subject to warmer_write_veto (gender-flanker / one-sided SPF / makeup one-sided
    formula ADD closed via the curated variant-hint reference). The veto can ONLY
    turn an ALLOW into a REFUSE — a live request (no warm signal) is byte-identical."""
    if not exact_gate_enabled():
        return True
    if not isinstance(price, dict):
        return False
    # FAIL-CLOSED (external review B6): never cache a price we cannot verify — no
    # identity, no valid PDP URL, or explicitly OUT OF STOCK. A wrong/unverifiable
    # price cached under the request key would poison the genuine TTL.
    title = price.get("title") or price.get("name") or ""
    if not title:
        return False
    # FAIL-CLOSED — the VERIFIED positive-price cache requires a real, verifiable PDP URL
    # for EVERY method, including converted_usd. (An earlier pass exempted converted from
    # this gate to stop a re-burn, but external review P2 is right: a URL-less / synthesized-
    # search converted price has no cited PDP and must NOT share the verified cache with
    # genuine prices — that conflates provenance. A converted price WITH a real PDP link
    # still caches; a URL-less one simply re-resolves next request, which is correct, not a
    # leak. A dedicated short estimate cache for url-less converted is a possible future
    # enhancement, deliberately NOT in the verified-cache gate.)
    url = price.get("url")
    if not url or _is_listing_url(url):
        return False
    if price.get("in_stock") is False:
        return False
    # An electronics ACCESSORY (charger/adapter/case) lives in _ELECTRONICS_PADDING, so the
    # shared _selection_match strips it and would accept "Galaxy S24 Charger" as the phone —
    # caching a cheap charger price under the device query poisons the genuine TTL. select_best
    # and is_price_showable already reject it via _is_device_accessory; mirror that asymmetry
    # here so the CACHE-WRITE gate is closed too (coverage sweep HIGH).
    if ((category or "").lower() == "electronics"
            and _is_device_accessory(title) and not _is_device_accessory(request_name)):
        return False
    if not request_name:
        return True
    if _selection_match(
        request_name, title, category, candidate_brand=price.get("brand", ""),
    ):
        # Wave C (re-sweep RS7 / kpiE2E RS-2) — the BF1 wrong-brand fence on
        # the WRITE gate: a keystone pass alone still cached the wrong-brand /
        # brandless same-model-word fashion row under the genuine TTL on the
        # no-adapter paths (shopping / harvest JSON-LD). Same centralized
        # helper; the structured-code override below keeps its own brand
        # protection (strict_title_match keeps the query brand required).
        base_ok = _brand_evidence_ok(
            request_name, title,
            candidate_brand=str(price.get("brand") or ""), category=category,
        )
    else:
        # Wave-B parity — the bounded structured-identity override the algolia
        # matcher already ran (A3): a query-confirmed model code relaxes ONLY the
        # variant-add direction; leak direction + axes stay enforced. Without this
        # the write gate re-rejects exactly the descriptive-title hit the adapter
        # accepted, so the correct product resolves+displays but NEVER caches.
        base_ok = _structured_code_cache_override(request_name, price, title, category)
    if not base_ok:
        return False
    # Wave-2 B3a — OFF-CLOCK ONLY: apply the curated variant-hint veto on TOP of
    # an allowed base decision. No-op (returns (True, ...)) on the live path and
    # flag-OFF, so byte-identity holds; it can only turn an ALLOW into a REFUSE.
    allow, _reason = warmer_write_veto(
        request_name, price, category, warm_context=warm_context,
    )
    return allow


def public_price_view(price: Any) -> Any:
    """B7 — the PUBLIC projection of a price object: strips the internal
    `guard_rejected` diagnostic (it belongs in metadata, never the user-facing price)
    and any `_`-prefixed internal key (`_cached`, `_cache_source`, …). Returns a NEW
    dict (never mutates the input, so the orchestrator's cache-hit metadata that reads
    `_cached` off the pre-projection price is unaffected). Non-dicts pass through."""
    if not isinstance(price, dict):
        return price
    # Rollback (B8): b207bfa exposed internal `_cached`/`_cache_source` on the public
    # price; with the gate OFF, leave the projection byte-identical (guard_rejected is
    # never stamped flag-OFF anyway, so nothing leaks).
    if not exact_gate_enabled():
        return price
    return {
        k: v for k, v in price.items()
        if k != "guard_rejected" and not (isinstance(k, str) and k.startswith("_"))
    }


def _identity_cache_token(text: str, category: Optional[str] = None) -> str:
    """A stable composite cache token of ALL identity-discriminating axes —
    concentration (EDP/EDT/…) + variant qualifier (FE/Pro/Max/…) + size/storage/
    count/weight — so distinct VARIANTS of the same product never collide on one
    cache key (EDP 100ml vs EDT 100ml; S24 vs S24 FE) while ALIAS wording maps to
    the SAME token (EDT ≡ "eau de toilette" via the normalized label; oz snapped to
    ml by size_variant_token). Empty when NO discriminating axis is present → the
    caller keeps the legacy size-agnostic key (backward-compatible, no cache-warm
    invalidation for plain products). The qualifier set is applied category-agnostically
    here — it only ever ADDS a discriminator, so a brand word that happens to be a
    qualifier (Max Factor) stays consistent across the request and the resolved match."""
    parts: List[str] = []
    conc = extract_concentration(text)
    if conc:
        parts.append(conc.lower().replace(" ", ""))
    quals = _quals_in(text, _ELECTRONICS_QUALIFIERS)
    if quals:
        parts.append("".join(sorted(quals)))
    size = size_variant_token(text, category)
    if size:
        parts.append(size)
    return ".".join(parts)


_QUALIFIER_WORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(q) for q in sorted(_ELECTRONICS_QUALIFIERS)) + r")\b",
    re.I,
)


def _strip_identity_axes(text: str) -> str:
    """Remove the size/storage/concentration/qualifier tokens from `text` so the
    cache-key BASE is identity-axis-agnostic — the composite _identity_cache_token
    carries them. Mirrors that token's axes so a discriminator living in `name` vs
    `search_query` collapses to one base (the same product → one key)."""
    out = _IDENTITY_MEASURE_STRIP_RE.sub(" ", text or "")
    for pat, _label in _CONCENTRATION_PATTERNS:
        out = pat.sub(" ", out)
    out = _QUALIFIER_WORD_RE.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


def build_size_aware_price_cache_key(
    brand: str, name: str, variant: Optional[str], region: str,
    identity_text: str = "", category: Optional[str] = None,
) -> str:
    """Price cache key that folds in a normalized size/variant token so distinct
    sizes never collide (Task 1.4).

    `identity_text` is any extra product-identity string to mine the size from
    (the search query / full title) — combined with name+variant so a size that
    lives in EITHER reaches the key. When NO size is found anywhere, the key is
    IDENTICAL to the legacy `get_price_cache_key(...)` so sizeless products are
    backward-compatible (no cache-warm invalidation).

    The same product+size yields the SAME key regardless of WHERE the size
    appears: the resolved token is STRIPPED out of name/variant before hashing
    the base components, then re-appended once — so name="iPhone 15 256GB" and
    name="iPhone 15"+identity="… 256GB" collapse to one key.
    """
    # ROLLBACK — with the exact gate OFF, fall back to the LEGACY size-only token +
    # _SIZE_STRIP_RE base so the cache namespace is byte-identical to b207bfa (a
    # rollback must not orphan the warmed cache / re-collide EDP↔EDT only on the
    # selection side). The concentration/qualifier axes are part of the new gate.
    if not exact_gate_enabled():
        token = size_variant_token(f"{name} {variant or ''} {identity_text or ''}")
        if not token:
            return get_price_cache_key(brand, name, variant, region)
        base_name = re.sub(r"\s+", " ", _SIZE_STRIP_RE.sub(" ", name or "")).strip()
        base_variant = (
            re.sub(r"\s+", " ", _SIZE_STRIP_RE.sub(" ", variant or "")).strip()
            if variant else variant
        )
        return generate_cache_key("price", brand, base_name, base_variant, region, token)
    full_text = f"{name} {variant or ''} {identity_text or ''}"
    # `category` (the orchestrator-resolved pair category) lets the size token drop a bare
    # cellular-generation "5G" for electronics so a base query and its "…5G" PDP collapse
    # to ONE key. Defaults to the per-task ContextVar when the caller omits it.
    token = _identity_cache_token(full_text, category)
    if not token:
        # NOTE (known, pre-existing, non-regressive narrow gap): this legacy fallback
        # hashes the RAW name, so a sizeless+qualifierless electronics model that carries
        # "5G" ONLY in its name (e.g. "iPhone 15 5G" with no storage/qualifier anywhere)
        # does NOT collapse onto its base. It is NOT the reported/warmer scenario (there the
        # 5G rides search_query, or storage/qualifier makes the token non-empty → handled
        # above). A blanket _strip_identity_axes(name) here would DOSE-MERGE supplements
        # (1000 IU ≡ 5000 IU) since this branch has no token to carry the dose — so it is
        # deliberately left as-is rather than "fixed" unsafely.
        return get_price_cache_key(brand, name, variant, region)
    # Strip ANY size/storage/concentration/qualifier token out of name+variant so
    # the base key is identity-axis-agnostic; the normalized composite token is the
    # single discriminator. Without this, the same axis living in `name` vs
    # `search_query` would hash differently (name differs) — defeating cache hits.
    base_name = _strip_identity_axes(name or "")
    base_variant = _strip_identity_axes(variant or "") if variant else variant
    # Append the composite identity token as an extra key component (generate_cache_key
    # joins truthy args with "|" before hashing), keeping the "price:" prefix.
    return generate_cache_key("price", brand, base_name, base_variant, region, token)


def variant_precision_rank(
    query_name: str, title: str,
) -> Tuple[int, int]:
    """A (concentration_rank, size_rank) tuple — HIGHER is a better variant match
    to the query. Used as a TIE-BREAK in the candidate sort, BEFORE price, so a
    listing that matches the query's stated size/concentration is preferred over
    one that doesn't. Neutral (0,0) when the query specifies neither axis or the
    title carries no signal — so non-fragrance categories are completely
    unaffected (no concentration/ml tokens → all-zero, sort unchanged).

    Ranks:
      concentration: +1 query+title agree; -1 both present and DISAGREE; 0 else.
      size:          +1 query size present and title includes it; -1 query size
                     present and title has a DIFFERENT size; 0 else.
    """
    if not query_name or not title:
        return (0, 0)
    q_conc = extract_concentration(query_name)
    t_conc = extract_concentration(title)
    if q_conc and t_conc:
        conc_rank = 1 if q_conc == t_conc else -1
    else:
        conc_rank = 0

    q_sizes = extract_sizes_ml(query_name)
    if q_sizes:
        t_sizes = extract_sizes_ml(title)
        if t_sizes:
            size_rank = 1 if (q_sizes & t_sizes) else -1
        else:
            size_rank = 0  # title silent on size — neither rewarded nor punished
    else:
        size_rank = 0
    return (conc_rank, size_rank)


# WS5/D4 (consistency default) — the flagship retail size for luxury fragrance.
# When the query is size-UNSPECIFIED, two compared products should converge on
# the SAME basis instead of one grabbing a 30ml miniature and the other a 100ml.
# 100ml is the dominant luxury-EDP retail size, so an unspecified luxury query
# prefers a 100ml candidate — a tie-break SMALLER than an explicit query-size
# match (so a stated size still wins) and gated to luxury so non-fragrance is
# untouched. Per the team-lead ruling: option A (per-product convergence +
# annotation); active pair-level re-selection is the deferred v1.1.
_FLAGSHIP_FRAGRANCE_SIZE = "100"


def flagship_basis_bonus(query_name: str, title: str, is_luxury: bool) -> float:
    """A small positive bonus (0.5) when, for a SIZE-UNSPECIFIED luxury query,
    the candidate carries the flagship 100ml basis — so two same-category
    products converge on a consistent size. Returns 0.0 when: not luxury, the
    query DID specify a size (the explicit match already drives selection), or
    the candidate isn't the flagship size. Smaller than the ±1 query-size signal
    so a stated size always dominates. Non-luxury / non-fragrance → always 0.0."""
    if not is_luxury or not title:
        return 0.0
    if extract_sizes_ml(query_name):
        return 0.0  # query specified a size — don't override it
    return 0.5 if _FLAGSHIP_FRAGRANCE_SIZE in extract_sizes_ml(title) else 0.0


def get_retailer_score(retailer_name: str) -> float:
    """Score a retailer by quality tier."""
    if not retailer_name:
        return DEFAULT_RETAILER_SCORE
    name_lower = retailer_name.lower()
    for key, score in RETAILER_TIERS.items():
        if key in name_lower:
            return score
    return DEFAULT_RETAILER_SCORE


# S3 electronics-authority (prod-verify fix) — host-marketplaces whose THIRD-
# PARTY sellers list gray-market / used / import units. Serper renders a 3P
# listing's source as "<Marketplace> - <SellerName>" (e.g. "Walmart -
# YYWireless"). The bare marketplace ("Walmart", "Amazon.com") is first-party.
_THIRD_PARTY_HOST_MARKETPLACES = ("walmart", "amazon", "ebay", "newegg", "aliexpress")
# Used-goods / refurb marketplaces — the whole storefront is reseller inventory.
_USED_GOODS_MARKETPLACES = (
    "swappa", "gazelle", "unclaimed baggage", "back market", "backmarket",
    "decluttr", "reebelo", "mercari", "poshmark",
)


def is_marketplace_reseller(source: str) -> bool:
    """True iff `source` is a THIRD-PARTY marketplace reseller (gray-market /
    used / import) — NOT a first-party/authorized retailer.

    Signals: (1) a host-marketplace source with a " - <seller>" suffix
    ("Walmart - YYWireless"); (2) a used-goods marketplace storefront
    (Swappa/Gazelle/Unclaimed Baggage/...). A bare "Walmart"/"Amazon.com" is
    first-party → False.

    Prod-verify root cause (2026-06-14): a us_fallback "Walmart - YYWireless"
    $339→127.8 BHD out-ranked the genuine sharafdg 244.99 because it was the
    cheapest passing match; is_counterfeit_listing targets DHgate/AliExpress
    DOMAINS, not these marketplace-seller source strings.
    """
    if not source:
        return False
    s = source.lower().strip()
    # Used-goods storefronts — whole source is reseller.
    if any(m in s for m in _USED_GOODS_MARKETPLACES):
        return True
    # Host-marketplace + " - <seller>" suffix = a 3P seller on that marketplace.
    if " - " in s:
        head = s.split(" - ", 1)[0].strip()
        if any(m in head for m in _THIRD_PARTY_HOST_MARKETPLACES):
            return True
    return False


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


# NOTE: build_direct_bh_candidates (the curl-SEARCH-URL injector, b250b55) was
# REMOVED 2026-06-14. The team-lead's live probe + our own captures proved the BH
# retailers' SEARCH pages are JS-rendered (gcc.lulu /en-bh/search → 404; sharafdg
# ?s= → noise) — constructed search URLs carry no extractable price. PDP discovery
# for these non-Shopify retailers comes from the Serper `site:` query +
# BH-locale filter (is_wrong_locale_url); Serper-independence is Shopify
# /products.json + a future Firecrawl-render-search (deferred, budget-gated).


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
# S3-genuine (team-lead floor fix 2026-06-14) — low-value categories (cheap OTC
# meds, grocery staples) routinely have GENUINE sub-1-BHD prices (Panadol 0.990,
# Evian 0.595, yoghurt 0.750). For these the 0.1×budget-breakpoint floor (1.1 for
# supplements) wrongly dropped real prices — so they use an ABSOLUTE small floor
# instead. High-value categories keep the multiplicative floor (an iPhone at
# 0.99 BHD is still garbage).
_ABSOLUTE_FLOOR_CATEGORIES = {"supplements", "grocery"}
_ABSOLUTE_PRICE_FLOOR = 0.1   # BHD — below this is a scrape artifact, not a price


def is_price_plausible(amount_bhd: Optional[float], category: Optional[str]) -> bool:
    """Absolute-plausibility gate for a real (cited/converted) price, in BHD.

    Returns False only for gross category outliers — amount<=0, below the
    category floor, or above 3x the highest finite breakpoint. A plausible price
    is TRUSTED even when it deviates wildly from the GPT training guess (the
    guess being wrong is exactly why we don't let it veto a cited price). Unknown
    / 'other' categories are permissive (only amount>0) since their magnitude is
    unbounded (cars to snacks).

    Floor: high-value categories use 0.1×budget-breakpoint (an iPhone at 5 BHD is
    garbage); low-value categories (supplements/grocery) use an ABSOLUTE 0.1-BHD
    floor so a genuine cheap OTC/grocery price (0.990 Panadol, 0.595 Evian) is
    KEPT — the multiplicative floor (1.1 for supplements) wrongly dropped them.

    Anchors on scoring_service.PRICE_TIERS_BY_CATEGORY so the bounds track the
    same per-category BHD breakpoints the scorer already maintains.
    """
    if amount_bhd is None or amount_bhd <= 0:
        return False
    # Lazy import — keeps price_service's top-level import surface minimal and
    # avoids any scoring_service import-order coupling.
    from app.services.scoring_service import PRICE_TIERS_BY_CATEGORY

    cat = (category or "").lower()
    ranges = PRICE_TIERS_BY_CATEGORY.get(cat)
    if not ranges:
        # 'other'/unknown — unbounded magnitude; only positivity is required.
        return True
    budget_breakpoint = ranges[0][0]
    finite_breakpoints = [u for u, _ in ranges if u != float("inf")]
    # Highest finite breakpoint anchors the ceiling (luxury is often inf when
    # top_tier is folded — fall back to premium so a real expensive item isn't
    # over-rejected but 9000-BHD garbage still is).
    top_finite = max(finite_breakpoints) if finite_breakpoints else budget_breakpoint
    if cat in _ABSOLUTE_FLOOR_CATEGORIES:
        floor = _ABSOLUTE_PRICE_FLOOR
    else:
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

def shopping_listing_matches(product_name: str, title: str) -> bool:
    """True iff a Serper Shopping listing `title` is a genuine SKU match for
    `product_name` — the counterfeit / accessory / wrong-variant / wrong-product
    relevance gate that ``extract_price_from_shopping`` applies inline (see its
    chain ~:2967-2988) BEFORE accepting a listing's price.

    Factored out for CDE-3's candidate-retention seed (_seed_shortcircuit_
    candidates in structured_comparison_service): the seed retains the WHOLE
    shopping list for size re-selection, and ``is_price_showable`` checks price
    plausibility (floor/sample/source) but NOT SKU match — so without this gate a
    wrong-variant alternate ("iPhone 15 Pro Max 256GB" under an "iPhone 15" query)
    at a plausible price could be re-selected as the product's price (wrong-SKU
    attribution). Price-plausibility (the high-value min_price floor) stays the
    caller's concern (is_price_showable downstream). Keep in sync with the inline
    chain above."""
    if not title:
        return False
    if is_counterfeit_listing(title):
        return False
    if is_accessory(title):
        return False
    if is_high_value_query(product_name) and not strict_title_match(product_name, title):
        return False
    if not numbers_match(product_name, title):
        return False
    if variant_mismatch(product_name, title):
        return False
    p_words = normalize_words(product_name)
    t_words = normalize_words(title)
    match_score = (len(p_words & t_words) / len(p_words)) if p_words else 0
    return match_score >= 0.4


def extract_price_from_shopping(
    product_name: str,
    shopping_items: List[Dict],
    currency: str,
    shopping_region: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract best matching price from Serper Shopping results.

    `category` (coverage/independent review) — the ORCHESTRATOR-RESOLVED pair
    category. When supplied it is authoritative so the variant-add guard engages
    for queries the weak keyword inference would miss (bare "Magnesium" /
    "Sony WH-1000XM5"). None → fall back to `_infer_category_from_query`.

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
    _category = _resolve_extractor_category(category, product_name)
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
        # S3 #1 (discovery-match) — reject a different model-line variant
        # ("iPhone 15" query vs "iPhone 15 Pro Max" listing): the base name is a
        # prefix of the variant so strict/numbers both pass, but it's a pricier
        # different SKU. Genuine-or-correct: don't attribute the wrong variant's
        # price.
        if variant_mismatch(product_name, title):
            continue
        # CORRECTNESS — identity + axis gate for ALL queries (gap #9: strict_title_match
        # ran only for high-value; everything else fell through to the 0.4-overlap +
        # cheapest tie-break, leaking wrong concentration/size/variant). _selection_match
        # rejects an EXPLICIT axis mismatch (EDP↔EDT, 256↔128, 100ml↔30ml, FE) and a
        # related product missing a query discriminator, while tolerating a descriptive
        # listing title. No-op when the rollback flag is OFF.
        if not _selection_match(product_name, title, _category):
            continue
        # Wave C (re-sweep RS7) — the BF1 wrong-brand fence at the SHARED
        # shopping tier: a fashion padding-brand query stripped its brand from
        # the keystone, so a brandless same-model-word row ("Superstar White
        # Sneakers" — could be Golden Goose) served + cached with no adapter
        # fence in the path. Shopping items carry no brand field → path (b):
        # the query's brand must appear folded in the title (fashion only).
        if not _brand_evidence_ok(
            product_name, title,
            candidate_brand=str(item.get("brand") or ""), category=_category,
        ):
            continue

        t_words = normalize_words(title)
        match_score = len(p_words & t_words) / len(p_words) if p_words else 0
        if match_score < 0.4:
            continue

        retailer = item.get("source", "")
        retailer_score = get_retailer_score(retailer)

        # S3 electronics-authority — a THIRD-PARTY marketplace reseller (gray-
        # market / used: "Walmart - YYWireless", Swappa, Gazelle) is LOW
        # authority. CRITICAL: get_retailer_score("Walmart - YYWireless") returns
        # Walmart's HIGH first-party tier (substring "walmart"), so the cap must
        # apply here BEFORE the OFFICIAL_BRAND_DOMAINS check — the 3P seller must
        # NOT inherit the host marketplace's first-party score. A genuine brand
        # DOMAIN in the link still overrides to 1.0 below (a 3P seller won't have
        # one). Result: a first-party listing out-ranks the reseller, the >=0.5
        # tier filter drops a reseller when a first-party exists, and a 3P-only
        # result keeps the low score → loses to any genuine BH price downstream.
        _is_reseller = is_marketplace_reseller(retailer)
        if _is_reseller:
            retailer_score = _RESELLER_RETAILER_SCORE

        link = item.get("link", "")
        if link:
            domain = extract_domain(link)
            if domain in OFFICIAL_BRAND_DOMAINS:
                retailer_score = 1.0

        # WS5 — variant precision tie-break + size/concentration annotation.
        # variant_rank = query size/concentration match (±1 each) + a smaller
        # flagship-basis bonus (+0.5) that converges an UNSPECIFIED luxury query
        # on 100ml so two compared products share a basis (D4 consistency default).
        _conc_rank, _size_rank = variant_precision_rank(product_name, title)
        _flagship = flagship_basis_bonus(product_name, title, is_lux)
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
            # WS5 — sort priority (higher=better variant match) + annotations.
            "variant_rank": _conc_rank + _size_rank + _flagship,
            "concentration": extract_concentration(title),
            "size": (sorted(extract_sizes_ml(title))[0] + "ml")
                     if extract_sizes_ml(title) else None,
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

    # WS5 — variant_rank is the FIRST price-independent tie-break after the
    # authority/match signals: a listing matching the query's stated size/
    # concentration outranks one that doesn't, BEFORE cheapest-price ordering.
    # All-zero for non-fragrance / unspecified queries → sort unchanged.
    if is_lux:
        candidates.sort(key=lambda c: (
            -c["retailer_score"], -c["variant_rank"], -c["match_score"], c["amount"],
        ))
    else:
        candidates.sort(key=lambda c: (
            -c["match_score"], -c["variant_rank"], -c["retailer_score"], c["amount"],
        ))
    best = candidates[0]

    logger.info(
        f"[PRICE] Selected: {best['retailer']} (tier {best['retailer_score']}) "
        f"at {best['currency']} {best['amount']} for '{product_name}' "
        f"({len(candidates)} candidates; variant_rank={best['variant_rank']} "
        f"size={best.get('size')} conc={best.get('concentration')})"
    )

    best.pop("match_score", None)
    best.pop("variant_rank", None)
    # KEEP `title` (IMPL-SPEC §"identity must survive to the backstop") so the
    # response chokepoint's is_price_showable(enforce_correctness=True) can re-verify
    # exactness on the shopping path + the KPI can read the resolved identity. The
    # FE ignores the extra key. With the rollback flag OFF, pop it (legacy popped
    # `title`) so flag-OFF is byte-identical (comprehensive review rollback NIT).
    if not exact_gate_enabled():
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


_PRICE_VALID_UNTIL_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})")


# Google Merchant REQUIRES priceValidUntil, and a large fraction of retailers set it
# once (year-end) and never refresh it, so a months-old date on a CURRENT in-stock PDP
# is normal. Only treat the offer as stale when the date is CLEARLY abandoned (> 1 year
# past) — this still catches the 2020-dated leak without false-pending a current price
# whose date a careless retailer let lapse a few months ago.
_PRICE_VALID_UNTIL_GRACE_DAYS = 365


def _offer_price_expired(offer: Dict[str, Any]) -> bool:
    """True iff the offer's `priceValidUntil` is a parseable date more than ~1 year in
    the past — a clearly-abandoned price (the 2020-dated offer the live PDP never
    refreshed) is not the current shelf price (B4). Absent / unparseable / future /
    recently-lapsed → not expired (no false pend on a careless date). Never raises."""
    pvu = offer.get("priceValidUntil")
    if not isinstance(pvu, str):
        return False
    m = _PRICE_VALID_UNTIL_RE.match(pvu)
    if not m:
        return False
    try:
        import datetime as _dt
        valid_until = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        cutoff = _dt.date.today() - _dt.timedelta(days=_PRICE_VALID_UNTIL_GRACE_DAYS)
        return valid_until < cutoff
    except (ValueError, TypeError):
        return False


# ============================================================================
# WIDE CANDIDATE DICT (ENABLE_WIDE_CANDIDATE, default ON)
# ----------------------------------------------------------------------------
# extract_jsonld_price parses the whole schema.org Product node to reach
# offers[].price and then keeps five keys. These helpers carry the REST of the
# SAME node — no extra fetch, no extra parse.
#
# THE CONVENTION (pinned by tests/test_wide_candidate_dict.py): a field that is
# absent / empty / whitespace-only / unparseable is OMITTED from the candidate
# dict entirely. A key is NEVER present carrying None, "" or [], so a downstream
# `if "sku" in cand` stays honest and never has to also test the value. Every
# helper below therefore returns a FALSY value ("" / [] / None) that the caller
# tests before assigning, rather than assigning unconditionally.
# ============================================================================

# review[] is the only UNBOUNDED-cardinality field on the node (a PDP can carry
# hundreds of embedded reviews, each an arbitrarily long body), so it is the one
# field that gets a hard cap in both dimensions. `description` is a single field
# and is carried WHOLE — truncating it would invent a lossy semantic no consumer
# asked for, and the parsed node is already in memory either way.
_WIDE_CANDIDATE_MAX_REVIEWS = 20
_WIDE_CANDIDATE_MAX_REVIEW_CHARS = 500

# The gtin flavours schema.org defines, in the precedence the widened dict folds
# them into ONE "gtin" key. mpn is deliberately NOT in this list — a
# manufacturer part number is not a global trade item number, so it stays a
# separate key (a consumer matching on GTIN must not be handed an MPN).
_WIDE_CANDIDATE_GTIN_FIELDS = ("gtin13", "gtin12", "gtin8", "gtin")

# A rating attached to one of these node types is the STORE's, not the product's
# — fyzara.com ships Organization/4.9-from-1100 and capitalstoreoman.com ships
# Organization/4.6-from-10 in the same document as the Product. Kept as an
# explicit deny-list belt to the structural brace: only @type=="Product" nodes
# ever reach the widening, so a store node cannot get here in the first place.
_WIDE_CANDIDATE_NON_PRODUCT_RATING_TYPES = frozenset({
    "organization", "localbusiness", "store", "onlinestore", "website",
    "webpage", "corporation", "brand",
})


def _jsonld_scalar_text(value: Any) -> str:
    """A schema.org Text-ish field -> ONE stripped string, or "" when there is
    nothing usable. Tolerates every shape the spec (and real retailers) allow:
    a bare string, a number (sku 100234), a list (first usable member wins), or
    a Thing node carrying the text in `name` / `@value`. Never raises."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):          # a bool is an int in Python — not text
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        for item in value:
            text = _jsonld_scalar_text(item)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        for key in ("name", "@value", "value"):
            text = _jsonld_scalar_text(value.get(key))
            if text:
                return text
    return ""


def _jsonld_image_urls(value: Any) -> List[str]:
    """schema.org `image` -> a flat list of url STRINGS, de-duplicated with
    order preserved. The spec allows a bare url string, a list, or an
    ImageObject node (url / contentUrl) — and real pages mix all three in one
    list. A member with no usable url is dropped, so an all-junk image field
    yields [] and the caller omits the key. Never raises."""
    urls: List[str] = []

    def _push(item: Any) -> None:
        if isinstance(item, str):
            text = item.strip()
            if text:
                urls.append(text)
            return
        if isinstance(item, dict):
            for key in ("url", "contentUrl", "@id"):
                text = _jsonld_scalar_text(item.get(key))
                if text:
                    urls.append(text)
                    return
            return
        if isinstance(item, list):
            for sub in item:
                _push(sub)

    _push(value)
    seen = set()
    deduped = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _jsonld_product_rating(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The Product node's OWN aggregateRating -> {"rating_value": float
    [, "review_count": int]}, or None.

    THE TRAP this exists for: fyzara.com and capitalstoreoman.com each attach an
    aggregateRating to an @type Organization node sitting in the SAME document
    as the Product — a STORE rating (4.9 from 1100 / 4.6 from 10) that would
    ship as a product rating if anything scanned the document instead of the
    node. This reads ONLY the node handed to it, and refuses outright unless
    that node is a Product (and unless the rating node itself is not a
    store/organization shape).

    A missing / non-numeric / non-positive ratingValue means NO rating: the key
    is omitted rather than carried as None. `reviewCount` is preferred over
    `ratingCount` (a review count is the stronger claim); when neither parses,
    the value is carried alone rather than with a fabricated zero."""
    if not isinstance(node, dict) or not _is_product_type(node):
        return None
    agg = node.get("aggregateRating")
    if not isinstance(agg, dict):
        return None
    agg_type = _jsonld_scalar_text(agg.get("@type")).lower()
    if agg_type in _WIDE_CANDIDATE_NON_PRODUCT_RATING_TYPES:
        return None
    try:
        rating_value = float(_jsonld_scalar_text(agg.get("ratingValue")))
    except (TypeError, ValueError):
        return None
    if not rating_value > 0:
        return None
    rating: Dict[str, Any] = {"rating_value": rating_value}
    for count_field in ("reviewCount", "ratingCount"):
        try:
            count = int(float(_jsonld_scalar_text(agg.get(count_field))))
        except (TypeError, ValueError):
            continue
        if count > 0:
            rating["review_count"] = count
            break
    return rating


def _jsonld_review_bodies(value: Any) -> List[str]:
    """schema.org `review` (a node or a list of nodes) -> the review BODIES as
    stripped strings. Bounded in BOTH dimensions — at most
    _WIDE_CANDIDATE_MAX_REVIEWS bodies, each truncated to
    _WIDE_CANDIDATE_MAX_REVIEW_CHARS — so a PDP with hundreds of long embedded
    reviews cannot bloat the candidate dict. A member with no usable body is
    skipped (it does not consume a slot). Never raises."""
    nodes = value if isinstance(value, list) else [value]
    bodies: List[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        body = _jsonld_scalar_text(node.get("reviewBody"))
        if not body:
            continue
        bodies.append(body[:_WIDE_CANDIDATE_MAX_REVIEW_CHARS])
        if len(bodies) >= _WIDE_CANDIDATE_MAX_REVIEWS:
            break
    return bodies


def _widen_jsonld_candidate(cand: Dict[str, Any], product: Dict[str, Any]) -> None:
    """Carry the rest of the ALREADY-PARSED Product node onto `cand`, in place.

    Every key is assigned only when it has real content (see THE CONVENTION
    above). Callers must gate on wide_candidate_enabled() — this function does
    not, so the flag is read exactly once per candidate at the call site."""
    description = _jsonld_scalar_text(product.get("description"))
    if description:
        cand["description"] = description

    images = _jsonld_image_urls(product.get("image"))
    if images:
        cand["image"] = images

    sku = _jsonld_scalar_text(product.get("sku"))
    if sku:
        cand["sku"] = sku

    for field in _WIDE_CANDIDATE_GTIN_FIELDS:
        gtin = _jsonld_scalar_text(product.get(field))
        if gtin:
            cand["gtin"] = gtin
            break

    mpn = _jsonld_scalar_text(product.get("mpn"))
    if mpn:
        cand["mpn"] = mpn

    ld_category = _jsonld_scalar_text(product.get("category"))
    if ld_category:
        cand["category"] = ld_category

    rating = _jsonld_product_rating(product)
    if rating:
        cand["aggregate_rating"] = rating

    reviews = _jsonld_review_bodies(product.get("review"))
    if reviews:
        cand["reviews"] = reviews


def extract_jsonld_price(
    html: str, brand: str, expected_currency: str, query_name: str = "",
    category: Optional[str] = None,
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
    _category = _resolve_extractor_category(category, query_name)
    candidates: List[Dict[str, Any]] = []

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
            # C2 (kpiE2E RS-1) — html.parser does NOT entity-decode <script>
            # contents, so a JSON-LD name's "&amp;" reaches the identity gates
            # verbatim and tokenizes as a false "amp" add. Decode at ingestion.
            # GATED: the name is carried unconditionally for flag-OFF
            # byte-identity (see the name-carry note below), so the flag-OFF
            # path must keep the legacy raw bytes.
            if exact_gate_enabled() and product_name:
                product_name = html_unescape(product_name)
            # S3 #34 (blocker) — REJECT an accessory PDP. A "Galaxy S24 Case"
            # JSON-LD (brand Samsung, numbers 24, no model-line qualifier) was
            # matching as the phone → 11.9 BHD GENUINE-labeled confident-wrong
            # product (the exact "wrong scrape" forbidden). is_accessory was on
            # the shopping + Shopify matchers but MISSING here (the curl-scrape /
            # backfill JSON-LD path). A real phone PDP is not an accessory.
            # C2 (RS-4): scoped via is_accessory_for_category — a resolved
            # JSON-LD PDP name is exactly the "direct store-API" class the BF4
            # scoping exists for (the godukkan/sharafdg MacBook PDPs all carry
            # the "English Keyboard" layout segment); a Galaxy-case PDP still
            # rejects ("case" flags in every scope).
            if is_accessory_for_category(product_name, _category):
                continue
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
            # External review — match the brand ALIAS forms too (query brand "YSL" vs a
            # JSON-LD brand "Yves Saint Laurent"), BEFORE this literal substring filter
            # rejects the candidate (the alias fold in _selection_match ran too late).
            _brand_forms = {brand_nospace}
            _bw = set(re.findall(r"[a-z0-9&]+", brand_lower))
            for _grp in _BRAND_ALIAS_GROUPS:
                if _bw & _grp:
                    _brand_forms |= {a.replace(" ", "").replace("&", "") for a in _grp}
            matched_in_name = any(f and f in name_nospace for f in _brand_forms)
            matched_in_brand_field = bool(brand_field_nospace and any(
                f and f in brand_field_nospace for f in _brand_forms))
            if not matched_in_name and not matched_in_brand_field:
                continue

            # S3 #1 (discovery-match) — reject a DIFFERENT model-line variant
            # even when the base name matched (matched_in_name=True for "iPhone
            # 15" vs an "iPhone 15 Pro Max" JSON-LD Product, since the base is a
            # prefix). sharafdg/microless PDP discovery surfaces base+Pro+Pro Max
            # on one query; without this the cheapest/first variant's price is
            # mis-attributed. Applies whenever the full query is known.
            if query_name and variant_mismatch(query_name, product_name):
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

            # CORRECTNESS — identity + axis gate (the warm-cache S24->S24 FE /
            # EDP->EDT / 256->128 / related-product leaks). variant_mismatch above
            # is a coarse qualifier check; _selection_match adds concentration / ml /
            # storage / count axes + a query-tokens-present check, while tolerating a
            # DESCRIPTIVE JSON-LD name (extra colour/packaging words). Applied only
            # when the full query is known (pre-S4 callers unaffected); a no-op when
            # the rollback flag is OFF.
            # candidate_brand prefers the matched Product's JSON-LD brand FIELD
            # (e.g. "Jessie and James") over the coarse first-word `brand` arg, so a
            # brand-FIELD-only match (name "Orangey Dress") subtracts the full brand
            # from both sides and the residual identity ({orangey,dress}) matches.
            _cand_brand = str(ld_brand or brand)
            if query_name and not _selection_match(
                query_name, product_name, _category, candidate_brand=_cand_brand,
            ):
                continue

            offers = product.get("offers", {})
            if isinstance(offers, dict):
                offers = [offers]
            elif not isinstance(offers, list):
                continue

            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                # priceCurrency can be an explicit JSON null (key present, value
                # None) — e.g. bahrainpharmacy's empty WooCommerce Offer node.
                # Coerce to str so a malformed Offer is SKIPPED, not a crash that
                # aborts the whole extractor before the WC/microdata fallbacks.
                currency = offer.get("priceCurrency") or ""
                if str(currency).upper() != expected_currency.upper():
                    continue
                # B4 — drop a STALE offer (priceValidUntil already past). No-op when
                # absent/unparseable/future or when the rollback flag is OFF.
                if exact_gate_enabled() and _offer_price_expired(offer):
                    continue
                try:
                    explicit = offer.get("price")
                    low = offer.get("lowPrice")
                    high = offer.get("highPrice")
                    # B4 (external review) — on the EXACTNESS path (query known), an
                    # AggregateOffer with NO explicit per-SKU `price` (only low/high) is
                    # the cheapest variant/seller, NOT proof of the EXACT SKU's price ->
                    # skip (pend), whether or not a high is present. A plain Offer.price
                    # is unchanged; the pre-S4 no-query callers keep lowPrice (I5.8).
                    _no_explicit = explicit is None or str(explicit).strip() in ("", "0")
                    _is_aggregate = "AggregateOffer" in str(offer.get("@type") or "")
                    # A low==high AggregateOffer is a SINGLE price point = the exact SKU
                    # price (a single-seller PDP modelled as AggregateOffer), NOT the
                    # "cheapest variant/seller" ambiguity — accept it (local review #6
                    # coverage). A genuine low<high RANGE is still skipped (not proof of
                    # the exact SKU's price).
                    _low_eq_high = False
                    if low is not None and high is not None:
                        try:
                            _low_eq_high = float(low) == float(high)
                        except (ValueError, TypeError):
                            _low_eq_high = False
                    if (
                        exact_gate_enabled() and query_name and _is_aggregate and _no_explicit
                        and not _low_eq_high
                    ):
                        continue
                    # AggregateOffer carries lowPrice instead of price (I5.8, no-query path)
                    price_val = float(explicit or low or 0)
                except (ValueError, TypeError):
                    continue
                if price_val <= 0:
                    continue

                # Availability policy — COLLECT the offer with its real stock flag.
                # An out-of-stock offer is NOT dropped here (so an only-OOS PDP still
                # reports its price flagged in_stock=False, which the chokepoint
                # pends) — select_best below RANKS in-stock first and only falls back
                # to OOS when there is no in-stock alternative.
                # B8 — the EXPANDED tri-state (SoldOut/Discontinued/PreOrder/BackOrder →
                # False) only applies with the gate ON. With the gate OFF, replicate the
                # b207bfa literal (only the OutOfStock token flips to False) so a
                # rollback is byte-identical — but keep the str() coercion so the
                # non-string availability shapes (None/list/dict) never TypeError.
                if exact_gate_enabled():
                    avail_state = is_available_state(offer.get("availability"))
                    if query_name:
                        # External review B4 — on the EXACTNESS path UNKNOWN availability
                        # stays None (do NOT assert in_stock=True with no signal); the KPI
                        # requires confirmed in-stock, the chokepoint shows None as unknown.
                        in_stock = avail_state
                    else:
                        # Legacy no-query (I5.8) callers keep the old unknown→in_stock=True.
                        in_stock = True if avail_state is None else avail_state
                else:
                    in_stock = "OutOfStock" not in str(offer.get("availability") or "")

                cand: Dict[str, Any] = {
                    "amount": price_val,
                    "currency": expected_currency,
                    "in_stock": in_stock,
                }
                # The JSON-LD Product NAME is carried UNCONDITIONALLY — LEGACY (b207bfa /
                # origin/main) always returned it and the fragrance size-capture
                # (_stamp_listing_size, parses ml/oz from this name) depends on it, so a
                # flag-OFF rollback MUST keep it byte-identical (comprehensive review HIGH —
                # gating it dropped size-capture on rollback). Only `brand` is the NEW
                # identity addition the exact gate introduced, so only it is flag-gated.
                cand["name"] = product_name
                # `brand` is UNGATED by the wide flag (carried like `name`): it is a
                # plain field off the same node and the exact-gate coupling was only
                # ever about who CONSUMED it, not about who could capture it. Under
                # ENABLE_WIDE_CANDIDATE it is carried unconditionally; with that flag
                # OFF it stays exactly as gated as before, so the rollback is
                # byte-identical. (No behaviour rides on the ungating today: with the
                # exact gate OFF select_best short-circuits to min(amount) without
                # reading `brand`, and the caller reads price_data["brand"] only
                # inside its own exact_gate_enabled() branch.)
                if exact_gate_enabled() or wide_candidate_enabled():
                    # Carry the matched brand so _selection_match subtracts the FULL brand
                    # (brand-FIELD-only match, name "Orangey Dress" + ld brand "Jessie and James").
                    cand["brand"] = _cand_brand
                if wide_candidate_enabled():
                    # Everything else on the SAME already-parsed node — description,
                    # image, sku, gtin/mpn, category, the PRODUCT's aggregateRating
                    # (never a store's) and the embedded review bodies. Absent fields
                    # stay ABSENT; nothing here is read by the selection path.
                    _widen_jsonld_candidate(cand, product)
                candidates.append(cand)

    if not candidates:
        return None
    # CORRECTNESS — pick by variant precision, NEVER cheapest, RANKING in-stock
    # first; an only-OOS PDP still returns its price flagged in_stock=False (the
    # chokepoint pends it — preserves the existing OOS-detection behaviour). When
    # the query is unknown (pre-S4 callers) there is no identity to gate on → keep
    # the legacy cheapest pick.
    if query_name:
        # require_url=False — JSON-LD candidates are page-INTERNAL (the PDP URL is
        # the page being scraped; the caller stamps it onto the result). Requiring a
        # per-candidate URL here would drop every JSON-LD match.
        return select_best(
            candidates, query_name, _category,
            drop_out_of_stock=False, require_url=False,
        )
    return min(candidates, key=lambda c: c["amount"])


def _page_size_signals(soup, jsonld_name: str = "") -> List[str]:
    """Free-text fields on a scraped PDP a fragrance size could be hiding in, in
    PRECEDENCE order: the matched JSON-LD Product ``name`` first (the most
    specific — "...Eau de Parfum 100ml"), then ``og:title``, then the page
    ``<title>``. Used by the size-capture in extract_price_from_html so a
    genuine listing whose size is NOT in a shopping-title "Xml" token (but IS in
    the JSON-LD name / og:title / page title) still populates ``price.size``."""
    signals: List[str] = []
    if jsonld_name:
        signals.append(jsonld_name)
    try:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            signals.append(og["content"])
        if soup.title and soup.title.string:
            signals.append(soup.title.string)
    except Exception:  # noqa: BLE001 — a malformed head must never break pricing
        pass
    return signals


def _stamp_listing_size(
    result: Dict[str, Any],
    product_name: str,
    soup,
    jsonld_name: str = "",
) -> Dict[str, Any]:
    """Set ``result['size']`` (an "<n>ml" string) from the listing's REAL size,
    captured from the JSON-LD name / og:title / page <title> (ml OR oz) — but
    ONLY for fragrance queries, so non-fragrance scrapes (electronics, etc.) are
    completely untouched. Mutates + returns `result`. No-op (size left as-is /
    unset) when the query isn't a fragrance or NO ml/oz token is present in any
    signal — the flagship-100ml default remains a pair-level fairness concern,
    never fabricated onto a single price here."""
    if not is_fragrance_query(product_name):
        return result
    for text in _page_size_signals(soup, jsonld_name):
        size_ml = extract_size_ml_any(text)
        if size_ml is not None:
            result["size"] = f"{size_ml}ml"
            break
    return result


def _page_identity_ok(product_name: str, soup, category: Optional[str]) -> bool:
    """CORRECTNESS — gate the OG / microdata / WooCommerce-span fallback paths,
    which carry NO per-product structured identity and otherwise grab the FIRST
    price on the page. Verify the PAGE identity (og:title / page <title>) actually
    matches the query before any fallback price is attributed: True iff ANY page
    signal _selection_match's the query. Returns True when the gate is OFF, there
    is no query, or there are NO identity signals at all (title-less page —
    preserve legacy, don't over-reject). False (→ caller pends) when signals exist
    and NONE match the query — kills the multi-product / wrong-SKU first-price grab."""
    if not exact_gate_enabled() or not product_name:
        return True
    signals = [s for s in _page_size_signals(soup) if s and s.strip()]
    if not signals:
        return True
    # CONSERVATIVE — pend when a page signal exists but NONE match the query. This
    # is the deliberate weak-signal guard: a store-name-only title shares no tokens
    # with the query and will pend (a rare false-pend for title-less-product pages),
    # but that is SAFER than the alternative — "no overlap → keep" cannot distinguish
    # a store-name title from a COMPLETELY DIFFERENT product (e.g. "Wireless Earbuds
    # Pro" vs a phone query), which must pend. (Review L2: accepted as-is.)
    return any(_selection_match(product_name, s, category) for s in signals)


def _page_identity_name(soup) -> Optional[str]:
    """The page's identity string (og:title / page <title>) — stamped as `name` on
    the OG/microdata/Woo fallback prices so the response chokepoint's axis backstop
    + the KPI can read the resolved identity (those paths carry no structured name)."""
    for s in _page_size_signals(soup):
        if s and s.strip():
            return s.strip()
    return None


def _parse_og_price_number(raw: Any) -> Optional[float]:
    """Parse an OpenGraph price meta ``content`` into a float, telling a comma
    DECIMAL separator apart from a comma THOUSANDS separator. Returns None when
    there is no number to read (never raises).

    LOCAL ON PURPOSE — do NOT swap in ``parse_price_string``: it strips commas
    unconditionally (see line ~2835) and turns the shelf price "24,00" into
    2400.0. Measured: leperfumeqa "279,00", fyzara "195,00" and mhgboutique
    "403,75" are real cached PDPs whose OG price the old bare ``float()`` could
    not parse at all.

    Resolution table (pinned by tests/test_og_branch_fixes.py):

      both separators  -> the RIGHTMOST one is the decimal point
                          "1.234,56" -> 1234.56   "1,234.56" -> 1234.56
      comma only, ONE comma with a 3-digit tail -> thousands group
                          "1,234"    -> 1234.0
      comma only, more than one comma           -> thousands groups
                          "1,234,567"-> 1234567.0
      comma only, any other tail length         -> decimal separator
                          "279,00"   -> 279.0    "22,902" ... see below
      dot only / no separator -> AS-IS, a lone dot is ALWAYS a decimal point
                          "3.000"    -> 3.0      "244.990" -> 244.99

    THE "3.000" RULING. It is genuinely ambiguous — 3.000 BHD (the 3-decimal GCC
    currencies) or three thousand. It resolves as a DECIMAL POINT because
    (1) og:price:amount is specified as a plain decimal number and BHD/OMR/KWD
    storefronts legitimately publish "244.990"/"3.000" (the cached corpus is full
    of them), and (2) ``float("3.000")`` is 3.0 — i.e. EXACTLY what the
    pre-change code produced, so this helper only ever changes the outcome for
    input the old code could not parse at all. Never treat a lone dot as a
    thousands separator.

    KNOWN LIMIT of the 3-digit-tail rule: a lone comma with exactly 3 digits
    after it cannot be told from a thousands group by shape alone, so a
    hypothetical 3-decimal BHD price written "22,902" reads as 22902.0. The
    corpus settles the tie-break — all three real comma-decimal pages are
    2-decimal (279,00 / 195,00 / 403,75) and no cached page writes a 3-decimal
    price with a comma, while "1,234"-style thousands are common. Pinned by
    test_a_three_digit_comma_tail_is_thousands_even_on_a_3_decimal_currency.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    negative = text.lstrip().startswith("-")
    # Drop currency codes/symbols, NBSP, thin spaces — keep only the numeric body.
    text = re.sub(r"[^0-9.,]", "", text)
    if not any(ch.isdigit() for ch in text):
        return None

    last_comma = text.rfind(",")
    last_dot = text.rfind(".")
    if last_comma >= 0 and last_dot >= 0:
        if last_comma > last_dot:      # "1.234,56" — comma is the decimal point
            text = text.replace(".", "").replace(",", ".")
        else:                          # "1,234.56" — comma groups the thousands
            text = text.replace(",", "")
    elif last_comma >= 0:
        tail = text[last_comma + 1:]
        if text.count(",") > 1 or len(tail) == 3:
            text = text.replace(",", "")   # "1,234,567" / "1,234" — thousands
        else:
            text = text.replace(",", ".")  # "279,00" — decimal separator
    # dot-only / separator-less falls through UNCHANGED (the "3.000" ruling).

    try:
        value = float(text)
    except (ValueError, TypeError):
        return None
    return -value if negative else value


# OG/product-namespace availability meta, in the order we trust them. Measured
# across the 92 cached PDPs: product:availability on 20 pages ("in stock" x14,
# "instock" x5, "out of stock" x1), og:availability on 1 ("instock").
_OG_AVAILABILITY_PROPS = ("og:availability", "product:availability")


def _og_availability(soup) -> Optional[bool]:
    """Tri-state stock for the OG branch: True / False / None (unknown).

    The OG branch used to hardcode ``"in_stock": True`` — an assertion with no
    page signal behind it. Reads the OG availability meta through the SAME
    ``is_available_state`` tri-state the JSON-LD path uses (so "in stock",
    "instock", "https://schema.org/InStock" and "Out of Stock" all classify
    identically on both paths) and returns None when nothing on the page says.
    NEVER defaults to True."""
    for prop in _OG_AVAILABILITY_PROPS:
        tag = soup.find("meta", property=prop)
        raw = tag.get("content") if tag else None
        if not raw:
            continue
        state = is_available_state(raw)
        if state is not None:
            return state
    return None


def _extract_og_price(
    soup, product_name: str, currency: str, domain: str, url: str,
) -> Optional[Dict[str, Any]]:
    """The OpenGraph meta-tag price fallback.

    Lifted out of ``extract_price_from_html`` VERBATIM, originally so the
    cascade could place it at two different priorities. That reorder (the "(c)"
    change on ENABLE_OG_BRANCH_FIXES) is REVERTED — this runs at Priority 2, the
    single unconditional call site, and the extraction here is what the flag
    still gates: (a) tri-state in_stock, (b) the comma-decimal parse. The helper
    stays split out because it keeps the cascade readable. Returns a price dict
    or None.
    """
    og_price = soup.find('meta', property='og:price:amount')
    og_currency = soup.find('meta', property='og:price:currency')
    # P0 (fragrance sweep 2026-08-25) — SALE price BEFORE list price. On Salla
    # `product:price:amount` is the CROSSED-OUT list price; the shelf price is
    # `product:sale_price:amount`. Measured over the 86 mappable cached PDPs the
    # sale tag appears on 14 pages, ALL 14 Salla, 10 diverging 1.13x-4.57x (3saf
    # 799 vs 175, sa.abdulsamadalqurashi 990 vs 495, kw.oudelite 14 vs 7 ...) —
    # production shipped the LIST price on every one. The JSON-LD branch cannot
    # save these: extract_jsonld_price hard-continues on a currency mismatch and
    # only retries "USD", so a SAR/AED/KWD/QAR/OMR page always lands HERE.
    # Precedence is og:price:amount -> product:sale_price:amount ->
    # product:price:amount. Flag-gated (ENABLE_SALE_PRICE_FIRST, default ON):
    # with the flag OFF the sale tag is never looked up and the two statements
    # below are the exact pre-change bytes.
    if not og_price and sale_price_first_enabled():
        _sale_price = soup.find('meta', property='product:sale_price:amount')
        _sale_raw = _sale_price.get('content') if _sale_price else None
        if _sale_raw:
            # Only PREFER a sale tag we can actually turn into a positive
            # amount — otherwise a junk/zero sale tag ("on request", "0") would
            # blow up the shared float() below and cost us the perfectly good
            # list price, making flag-ON strictly worse than flag-OFF.
            try:
                # (b) — with ENABLE_OG_BRANCH_FIXES ON the usability probe uses
                # the SAME parser as the consumer below, so a comma-decimal sale
                # tag ("79,99") is no longer misjudged as junk and silently
                # replaced by the list price. Flag OFF keeps the bare float().
                if og_branch_fixes_enabled():
                    _sale_val = _parse_og_price_number(_sale_raw)
                    _sale_usable = _sale_val is not None and _sale_val > 0
                else:
                    _sale_usable = float(_sale_raw) > 0
            except (ValueError, TypeError):
                _sale_usable = False
            if _sale_usable:
                og_price = _sale_price
                # Salla ships a matching product:sale_price:currency on all 14
                # cached pages, but do NOT depend on it: fall back to the LIST
                # price's currency tag (same page, same money) so a currency-less
                # sale tag never silently re-labels the amount.
                og_currency = (
                    soup.find('meta', property='product:sale_price:currency')
                    or soup.find('meta', property='product:price:currency')
                )
    if not og_price:
        og_price = soup.find('meta', property='product:price:amount')
        og_currency = soup.find('meta', property='product:price:currency')

    if og_price and og_price.get('content'):
        try:
            # (b) COMMA DECIMALS — the old bare `float()` RAISED on "279,00"
            # (leperfumeqa), "195,00" (fyzara), "403,75" (mhgboutique), so those
            # OG prices were dropped entirely. `_parse_og_price_number` tells a
            # comma decimal from a comma thousands group; a None (nothing
            # numeric) re-enters the legacy except-branch below unchanged.
            if og_branch_fixes_enabled():
                amount = _parse_og_price_number(og_price['content'])
                if amount is None:
                    raise ValueError(og_price['content'])
            else:
                amount = float(og_price['content'])
            if amount > 0:
                # S3-genuine (PDP curl Decision-F): a currency-LESS OG price
                # defaults to the EXPECTED currency arg, NOT hardcoded "USD".
                # bahrain.sharafdg.com ships product:price:amount=244.990 with NO
                # currency tag on a BHD page — the old "USD" default converted a
                # genuine 244.990 BHD price down to 92.12 BHD. An unlabeled price
                # on a BH retailer page is in BHD (the region/expected currency).
                detected_currency = (
                    og_currency['content']
                    if og_currency and og_currency.get('content')
                    else currency
                )
                # (a) STOCK — the literal True here asserted availability with no
                # page signal behind it (3 of 4 live Shopify targets have zero
                # available variants while production called them in stock). Read
                # the real og:availability / product:availability tag; None when
                # the page is silent. Flag OFF restores the hardcoded True.
                _in_stock = _og_availability(soup) if og_branch_fixes_enabled() else True
                result = {
                    "amount": amount, "original_currency": detected_currency,
                    "currency": detected_currency, "retailer": domain, "url": url,
                    "in_stock": _in_stock, "confidence": 0.9, "estimated": False,
                    "source_method": "page_scrape",
                }
                if detected_currency.upper() != currency.upper():
                    _convert_gpt_price_currency(result, currency)
                    # S3 coverage #2 — a converted OG price is converted_usd, not
                    # a genuine local page_scrape (provenance honesty).
                    result["source_method"] = "converted_usd"
                # frag-size-capture — size from og:title / page <title>.
                _stamp_listing_size(result, product_name, soup)
                # M2 — stamp the page identity so the chokepoint axis backstop runs. Flag-gated:
                # legacy never carried `name` on the OG/microdata/WC branches, so a flag-OFF
                # rollback stays byte-identical (comprehensive review rollback NIT).
                if exact_gate_enabled():
                    result["name"] = _page_identity_name(soup)
                return result
        except (ValueError, TypeError):
            pass
    return None


def extract_price_from_html(
    html: str, product_name: str, currency: str, domain: str, url: str,
    category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract price from HTML using structured data (JSON-LD, OG, microdata).

    For FRAGRANCE queries the returned price also carries a ``size`` ("<n>ml")
    captured from the listing's real size signals (JSON-LD product name /
    og:title / page <title>, ml or oz) when present — so the pair-level size
    fairness engages on TRUE sizes instead of silently assuming the flagship
    100ml basis (frag-size-capture). Non-fragrance scrapes are unaffected."""
    from bs4 import BeautifulSoup
    brand = product_name.split()[0] if product_name else ""
    _category = _resolve_extractor_category(category, product_name)
    # Parse once up front — also needed by the size-capture (frag-size-capture)
    # for the JSON-LD branch, which builds its result before the OG path.
    soup = BeautifulSoup(html, 'html.parser')

    # Priority 1: JSON-LD (S4 — pass the full query as query_name so a brand-
    # field-only match still requires name-relatedness, no cheapest-unrelated-
    # sibling grab).
    price_data = extract_jsonld_price(html, brand, currency, query_name=product_name, category=category)
    if not price_data:
        price_data = extract_jsonld_price(html, brand, "USD", query_name=product_name, category=category)
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
            # S3 coverage #2 (apple.com-198.9 wrong-scrape) — a JSON-LD price in
            # a FOREIGN currency that we converted to the target is NOT a genuine
            # local shelf price; it's a converted figure. Label its provenance
            # HONESTLY as converted_usd (the USD-fallback at line ~939 fired, or
            # the page served e.g. a US $529 refurb that became 198.9 BHD). This
            # keeps it out of the genuine-BH-share KPI + the UI says
            # "indicative/reference", never a genuine BH price.
            result["source_method"] = "converted_usd"
        # frag-size-capture — stamp the REAL listing size (ml/oz) from the
        # JSON-LD name / og:title / page <title> so the pair fairness engages on
        # true sizes (fragrance-scoped; no-op otherwise).
        _stamp_listing_size(result, product_name, soup, price_data.get("name", ""))
        # M2 (extended) — carry the MATCHED JSON-LD Product name as the listing
        # identity so the response chokepoint axis backstop, should_cache_price,
        # and the usable_exact_genuine KPI can verify the exact SKU. The OG /
        # microdata / WC branches below already stamp `name` (via _page_identity_
        # name); the JSON-LD branch OMITTED it, so a genuine page-scrape price
        # reached the cache-write gate with NO identity and was refused (warmer
        # gate: 8/18 genuine PDP prices blocked on missing identity). Uses the
        # extractor's OWN matched Product name (NOT the query), so it verifies
        # rather than trivially self-matches. Flag-gated for flag-OFF byte-
        # identity, matching the sibling branches.
        if exact_gate_enabled():
            result["name"] = price_data.get("name")
            # Forward the matched JSON-LD `brand` field too, so should_cache_price's
            # brand-aware _selection_match subtracts the FULL brand for a brand-
            # FIELD-only PDP (ounass-style: brand in the JSON-LD brand field, bare
            # name like "Libre Eau de Parfum 90ml"). Without it, the brand-unaware
            # gate requires the brand tokens IN the bare name and over-rejects a
            # correct genuine price (sweep MED). price_data already carries `brand`
            # (extract_jsonld_price stamps it when the gate is on).
            if price_data.get("brand"):
                result["brand"] = price_data.get("brand")
        return result

    # CORRECTNESS — the JSON-LD path gates identity per-Product; the OG / microdata
    # / WooCommerce-span fallbacks below do NOT (they grab the first price on the
    # page). Gate the whole fallback cascade ONCE on the page identity (og:title /
    # page <title>): if the page is a DIFFERENT product than the query, pend (None)
    # rather than mis-attribute a wrong-SKU / sibling first price.
    if not _page_identity_ok(product_name, soup, _category):
        return None

    # Priority 2: OpenGraph meta tags. `_extract_og_price` holds the body.
    #
    # THIS POSITION IS FROZEN — pinned by tests/test_og_cascade_position.py, and
    # deliberately NOT flag-gated. ENABLE_OG_BRANCH_FIXES once carried a "(c)"
    # change that moved this call BELOW microdata and the WooCommerce span on
    # the theory that OG is the least trustworthy structured source. Measured
    # over the 92 cached fragrance PDPs with ENABLE_EXACT_PRICE_GATE=false, that
    # reorder produced ZERO improvements and four regressions, so it is
    # REVERTED:
    #   oudworlds.com      19.54 BHD (OMR, converted_usd) -> 3.00 (page_scrape).
    #                      A 6.5x UNDER-price: the Woo "first span not in <del>"
    #                      rule lands on a different product on a page whose
    #                      spans run 4.000 / 3.000 / 2.500 / 4.000 / 20.000, the
    #                      real one being 20.000.
    #   perfumeskuwait.com 10.95 BHD (KWD, converted_usd) -> 8.90 ("KD",
    #                      page_scrape).
    #   perfumeqatar.com   same amount, provenance relabelled page_scrape.
    # The provenance half is the general defect: the branches below OG take the
    # currency string the page happens to print — "KD", or an Arabic-script
    # symbol — which no rate table maps, so the conversion silently no-ops and
    # an unconverted foreign amount ships labelled as a genuine local shelf
    # price that the genuine-BH-share KPI counts. The OG branch converts and
    # relabels converted_usd honestly. What DOES remain under
    # ENABLE_OG_BRANCH_FIXES is (a) the tri-state in_stock and (b) the
    # comma-decimal parse, both inside _extract_og_price.
    og_result = _extract_og_price(soup, product_name, currency, domain, url)
    if og_result is not None:
        return og_result

    # Priority 3: Schema.org MICRODATA (itemprop=price + itemprop=priceCurrency).
    # S3-genuine (gap-fill): bahrain.sharafdg.com PDPs are microdata-only (no
    # JSON-LD), so this is the path that produces a genuine BH electronics price.
    # CRITICAL — the page also carries an EPP INSTALLMENT itemprop=price
    # ("BHD 48.332/month"); the old find-first grabbed THAT (wrong). The helper
    # skips installment-context elements + reads the currency paired in the SAME
    # Offer itemscope (not a page-global find), and normalizes lowercase "bhd".
    micro = _extract_microdata_price(soup, currency, domain, url)
    if micro:
        # frag-size-capture — size from og:title / page <title> (microdata
        # nodes rarely carry a volume; the name signals do).
        _stamp_listing_size(micro, product_name, soup)
        if exact_gate_enabled():  # flag-OFF byte-identity (legacy carried no `name` here)
            micro["name"] = _page_identity_name(soup)  # M2 — chokepoint axis backstop
        return micro

    # Priority 4: WooCommerce price span. S3-genuine (PDP curl Decision-F):
    # bahrainpharmacy.com/store PDPs are WooCommerce with an EMPTY JSON-LD Offer
    # (price=None) and no OG/microdata — the real price is in a
    # `.woocommerce-Price-amount` span (<bdi>VALUE<span
    # class="woocommerce-Price-currencySymbol">BHD</span></bdi>). The first such
    # span NOT inside a <del> is the product price (a <del> wraps a crossed-out
    # sale original; later spans are related products).
    wc = _extract_woocommerce_price(soup, currency, domain, url)
    if wc:
        # frag-size-capture — size from og:title / page <title>.
        _stamp_listing_size(wc, product_name, soup)
        if exact_gate_enabled():  # flag-OFF byte-identity (legacy carried no `name` here)
            wc["name"] = _page_identity_name(soup)  # M2 — chokepoint axis backstop
        return wc

    return None


def _extract_woocommerce_price(
    soup, currency: str, domain: str, url: str
) -> Optional[Dict[str, Any]]:
    """Extract a price from a WooCommerce `.woocommerce-Price-amount` span.

    Reads the FIRST such span (the product price; later ones are related
    products) — but SKIPS a crossed-out original inside a `<del>` (on a SALE
    item the markup is `<del>OLD</del> <ins>NEW</ins>`; the first amount is the
    pre-sale price). Prefers the `<ins>`/non-`<del>` sale price. The numeric is
    the span text minus the currency-symbol child; the currency comes from
    `.woocommerce-Price-currencySymbol` (BHD on a BH page), normalized .upper().
    Returns a ``page_scrape`` dict or None.
    """
    # S3-genuine (team-lead #3 scope) — take the MAIN price, NOT a crossed-out
    # original. WooCommerce sale markup nests the old price in <del> and the
    # sale price in <ins>; pick the first amount NOT inside a <del>.
    span = None
    for cand in soup.find_all(class_="woocommerce-Price-amount"):
        # find_parent("del") walks ancestors — a price inside <del> is the
        # struck-out original; skip it.
        if cand.find_parent("del") is not None:
            continue
        span = cand
        break
    if span is None:
        return None
    # Currency from the symbol child (strip it out of the numeric text after).
    sym = span.find(class_="woocommerce-Price-currencySymbol")
    detected_currency = (sym.get_text(" ", strip=True) if sym else "") or currency
    detected_currency = detected_currency.strip().upper()
    if sym:
        sym.extract()  # remove so it doesn't pollute the numeric parse
    amount = parse_price_string(span.get_text(" ", strip=True))
    if amount is None or amount <= 0:
        return None
    result = {
        "amount": amount,
        "original_currency": detected_currency,
        "currency": detected_currency,
        "retailer": domain,
        "url": url,
        "in_stock": True,
        "confidence": 0.9,
        "estimated": False,
        "source_method": "page_scrape",
    }
    if detected_currency != currency.upper():
        _convert_gpt_price_currency(result, currency)
    return result


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
        #
        # NOT flag-gated. A "document order, not max" variant rode
        # ENABLE_OG_BRANCH_FIXES as a stated precondition of the reverted (c)
        # cascade reorder. With (c) gone the precondition is gone too, and the
        # variant is not free: faces.ae is a cached page where microdata ALREADY
        # wins at Priority 3, and first-wins moved it 569.64 BHD -> 238.76 BHD.
        # The max-rule's own weakness (a related-products rail can outbid the
        # real Offer — nazih.qa carries 10 QAR plus rail items up to 45) is real
        # but latent: OG runs first and covers it there. Fixing it is its own
        # change, measured on its own, not a rider on an OG flag.
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
        # NOTE microdata does NOT relabel a converted price `converted_usd` the
        # way JSON-LD and _extract_og_price do. That relabel rode
        # ENABLE_OG_BRANCH_FIXES as a precondition of the reverted (c) cascade
        # reorder and went with it — on the cached corpus it moved faces.ae from
        # page_scrape to converted_usd, which is a KPI-visible change nobody
        # measured on its own. The honesty argument still stands; make it its
        # own flagged change against a measured before/after.
        _convert_gpt_price_currency(result, currency)
    return result


# ============================================
# Page fetching
# ============================================

def _curl_timeout_for_url(url: str) -> int:
    """Per-fetch curl timeout: bahrain-tier registry domains get the longer
    cold-tolerant BH_REGISTRY_CURL_TIMEOUT; everything else stays at
    PAGE_SCRAPE_TIMEOUT (WRINKLE 1 — keep non-BH scrapes fast)."""
    try:
        from app.services.source_router import SOURCE_REGISTRY
        host = urlparse(url).netloc.replace("www.", "").lower()
        if not host:
            return PAGE_SCRAPE_TIMEOUT
        for s in SOURCE_REGISTRY:
            if s.tier != "bahrain":
                continue
            d = s.domain.replace("www.", "").lower()
            if host == d or host.endswith("." + d) or d.endswith("." + host):
                return BH_REGISTRY_CURL_TIMEOUT
    except Exception:  # noqa: BLE001 — selector must never break the fetch
        pass
    return PAGE_SCRAPE_TIMEOUT


async def curl_fetch_html(url: str) -> Optional[str]:
    """Fetch raw HTML via curl_cffi (no JS rendering)."""
    try:
        from curl_cffi import requests as curl_requests
        timeout = _curl_timeout_for_url(url)
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url, impersonate="chrome", timeout=timeout, allow_redirects=True,
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


def _host_on_domain(u: str, domain: str) -> bool:
    """True iff url ``u``'s host is the bare ``domain`` OR a subdomain of it.

    Strips a leading ``www.`` from both sides; matches the bare domain exactly
    OR ``*.`` + the bare domain. Used by curl_fetch_html_same_site to pin a
    redirect chain to the source storefront (NO sitemap_discovery import —
    avoids the circular). Empty/garbage host → False (fail-closed)."""
    try:
        host = (urlparse(u).hostname or "").strip().lower()
    except Exception:  # noqa: BLE001 — malformed url is "off-domain", never a crash
        return False
    if not host:
        return False
    host = host[4:] if host.startswith("www.") else host
    bare = (domain or "").strip().lower()
    bare = bare[4:] if bare.startswith("www.") else bare
    if not bare:
        return False
    return host == bare or host.endswith("." + bare)


async def curl_fetch_html_same_site(
    url: str,
    domain: str,
    max_redirects: int = 3,
    max_bytes: int = 3_000_000,
) -> Optional[str]:
    """Redirect-validating same-site HTML fetch (Codex HIGH-5 SSRF fix).

    ``curl_fetch_html`` follows redirects with ``allow_redirects=True`` — a
    same-site PDP url can 30x-redirect to an arbitrary host / private IP /
    ``*.railway.internal``. This variant validates EVERY hop: each url (the
    initial AND every Location) must pass ``validate_external_url`` (blocks
    private/loopback/link-local IPs + non-http(s)) AND ``_host_on_domain`` (stays
    on the source storefront). Any off-domain / private / non-2xx-non-3xx hop, a
    redirect-cap breach, or any exception → ``None``. NEVER raises.

    On a 200, returns ``resp.text`` truncated to ``max_bytes`` (guards a huge
    body). Body is capped, not rejected, so a legit large PDP still parses."""
    from app.utils.url_validator import validate_external_url

    # Validate the INITIAL url before any network call.
    if not validate_external_url(url) or not _host_on_domain(url, domain):
        logger.info("[PRICE] same-site fetch blocked initial url for %s", domain)
        return None

    try:
        from curl_cffi import requests as curl_requests
        timeout = _curl_timeout_for_url(url)
        current = url
        for _ in range(max_redirects + 1):
            resp = await asyncio.to_thread(
                lambda u=current: curl_requests.get(
                    u, impersonate="chrome", timeout=timeout, allow_redirects=False,
                )
            )
            status = resp.status_code
            if 300 <= status < 400:
                location = resp.headers.get("Location") or resp.headers.get("location")
                if not location:
                    return None
                # Resolve a relative Location against the current url.
                nxt = urljoin(current, location)
                if not validate_external_url(nxt) or not _host_on_domain(nxt, domain):
                    logger.info(
                        "[PRICE] same-site fetch blocked redirect to off-domain/private host for %s",
                        domain,
                    )
                    return None
                current = nxt
                continue
            if status == 200:
                text = resp.text or ""
                return text[:max_bytes]
            # Any other non-2xx/non-3xx status → honest miss.
            return None
        # Exceeded the redirect cap without a terminal 200.
        logger.info("[PRICE] same-site fetch exceeded redirect cap for %s", domain)
        return None
    except Exception as e:  # noqa: BLE001 — fetch must never raise
        logger.warning(f"[PRICE] curl_fetch_html_same_site failed for {url}: {e}")
        return None


async def fetch_page_price(
    url: str, product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Fetch a product page via curl_cffi and extract price from structured data."""
    if not ENABLE_PAGE_SCRAPE:
        return None

    domain = urlparse(url).netloc.replace("www.", "")
    # SSRF hardening (scraping audit 2026-07-08) — a Serper-discovered storefront
    # URL is externally-influenced, so validate the initial URL AND every redirect
    # hop (block private/loopback/link-local/metadata) and pin to the source host
    # via the same-site helper, instead of the unvalidated curl_fetch_html.
    html = await curl_fetch_html_same_site(url, domain)
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
#
# NOTE (R1 retrieval-term ladder, Wave B3): the shopify path is deliberately
# NOT laddered — it has NO search side (a full-catalog /products.json fetch;
# matching happens client-side over the whole page), so there is no
# AND-restrictive search term to widen. build_adapter_search_terms is wired
# only into the search-side adapters (woo / magento / salla / algolia).

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


def _select_shopify_variant(
    variants: List[Any], product_name: str, product_title: str,
    category: Optional[str], is_lux: bool,
) -> Optional[Dict[str, Any]]:
    """Bind the queried size to a specific Shopify variant instead of blindly pricing
    variants[0] (usually the smallest/cheapest → a decant leak). Returns the chosen
    variant, or None to PEND the product when the query STATES a size no variant offers,
    or a size-unspecified query hits an unbindable price SPREAD on a non-fragrance.
    Fragrances/luxury default to the flagship 100ml (else the LARGEST bottle) — never the
    decant. Called only under variant_min_guard_enabled(); the caller keeps variants[0]
    flag-OFF (byte-identical)."""
    valid: List[Tuple[Dict[str, Any], Optional[int], float]] = []
    for v in variants:
        if not isinstance(v, dict):
            continue
        amt = parse_price_string(str(v.get("price", "")))
        if amt is None or amt <= 0:
            continue
        # The variant's OWN title carries the authoritative per-variant size; fall back to the
        # product-title context only when the variant title has no ml/oz token — so a product
        # TITLE that lists a marketing size can't pollute a differently-sized variant's size
        # (coverage review: extract_size_ml_any returns min(...), so a "…100ml" title would
        # otherwise cap a "30ml" variant and could defeat the flagship pick).
        vt = v.get("title") or ""
        size = extract_size_ml_any(vt) or extract_size_ml_any(f"{product_title} {vt}")
        valid.append((v, size, round(amt, 3)))
    if not valid:
        return None
    q_size = extract_size_ml_any(product_name)
    if q_size:
        for v, size, _amt in valid:
            if size == q_size:
                return v
        return None  # the stated size is not offered → pend, never serve a different size
    # size-unspecified query
    prices = {amt for _v, _s, amt in valid}
    if len(prices) == 1:
        return valid[0][0]  # all variants same price → unambiguous, no decant risk
    cat = (category or "").lower()
    if cat == "fragrances" or is_lux:
        flagship = [v for v, size, _a in valid if size == 100]
        if flagship:
            return flagship[0]                                   # 100ml flagship convention
        sized = [(size, v) for v, size, _a in valid if size]
        if sized:
            return max(sized, key=lambda t: t[0])[1]             # largest bottle, never the decant
        return valid[0][0]                                       # no parseable sizes → no worse than today
    return None  # non-fragrance size-unspecified spread → ambiguous → pend


# ============================================================================
# Step 6 (fragrance hybrid capture, 2026-08-25) — the WIDE Shopify signal text.
# ============================================================================
# `_match_shopify_product` reads the two fragrance axes off
# `f"{title} {variant_title}"`. The same /products.json row already carries
# `product_type`, `tags` and `body_html`; folding them into a SECOND, capture-only
# string lifts size capture 25.6% -> 62.7% and concentration 7.6% -> 24.1% over
# 999 live Shopify fragrance products. Gated by wide_signal_text_enabled().
#
# WHY CAPS. `body_html` is unbounded free HTML — tens of KB is routine, and this
# runs once per candidate product on a catalog that can hold 250+ rows. Each
# supplementary segment gets its OWN budget so one long field cannot starve the
# others, and the body's plain-text budget is the repo's existing
# `_MATCH_INPUT_CAP` (512) — the same ReDoS bound the descriptor/axis matchers
# apply — rather than a fresh magic number. The raw-HTML pre-cut is 8x that:
# PDP copy runs roughly 4-8 markup chars per text char, so 4096 raw is enough to
# still fill the 512-char text budget on a typical body while bounding the strip.
_WIDE_SIGNAL_TYPE_CAP = 64        # product_type is a short taxonomy label
_WIDE_SIGNAL_TAGS_CAP = 256       # tags are short tokens; 256 holds ~20 of them
_WIDE_SIGNAL_BODY_CAP = _MATCH_INPUT_CAP   # 512 — the repo's matcher/ReDoS bound
_WIDE_SIGNAL_BODY_RAW_CAP = 8 * _MATCH_INPUT_CAP  # 4096 chars of raw HTML in

# `<[^<>]*>` and NOT `<[^>]*>`: excluding "<" from the class makes a failed
# tag-open abort at the very next angle bracket, so a pathological run of "<"
# cannot go quadratic. Truncation can only DROP a match that straddles the cut,
# never invent one (we always cut the tail).
_WIDE_SIGNAL_TAG_RE = re.compile(r"<[^<>]*>")
_WIDE_SIGNAL_WS_RE = re.compile(r"\s+")


def _wide_signal_capture_text(narrow: str, product: Dict[str, Any]) -> str:
    """`narrow` widened with the product row's `product_type`, `tags` and
    plain-texted `body_html`, each capped (see the block comment above).

    CAPTURE ONLY. The result is fed to `extract_sizes_ml` /
    `extract_concentration` and to nothing else — never to
    `variant_precision_rank` or `flagship_basis_bonus`, which must keep seeing
    the narrow text so no variant and no price can move.

    Accepts both field spellings: `/products.json` says body_html/product_type,
    the `{pdp}.js` envelope says description/type."""
    parts: List[str] = []
    if narrow:
        parts.append(narrow)

    ptype = product.get("product_type")
    if ptype is None:
        ptype = product.get("type")
    ptype = str(ptype or "").strip()
    if ptype:
        parts.append(ptype[:_WIDE_SIGNAL_TYPE_CAP])

    tags = product.get("tags")
    if isinstance(tags, (list, tuple, set)):
        tag_text = " ".join(str(t) for t in tags if t)
    else:
        tag_text = str(tags or "")
    tag_text = tag_text.strip()
    if tag_text:
        parts.append(tag_text[:_WIDE_SIGNAL_TAGS_CAP])

    body = product.get("body_html")
    if body is None:
        body = product.get("description")
    body = str(body or "")[:_WIDE_SIGNAL_BODY_RAW_CAP]
    if body:
        body = _WIDE_SIGNAL_TAG_RE.sub(" ", body)
        body = html_unescape(body)
        body = _WIDE_SIGNAL_WS_RE.sub(" ", body).strip()
        if body:
            parts.append(body[:_WIDE_SIGNAL_BODY_CAP])

    return " ".join(parts).strip()


def _match_shopify_product(
    catalog: Optional[Dict[str, Any]],
    product_name: str,
    currency: str,
    domain: str,
    resolved_category: Optional[str] = None,
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
    _is_lux = is_luxury_brand(product_name)  # WS5 — for the flagship-basis default
    best: Optional[Dict[str, Any]] = None
    # WS5 — rank tuple (variant_rank, match_score); a better variant match
    # (query size/concentration) wins even at equal word-overlap. variant_rank is
    # a float (carries the +0.5 flagship-basis bonus).
    best_rank: Tuple[float, float] = (-(10**9), -1.0)

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
        # Brand-implied match (2026-07-07) — a brand's OWN Shopify store OMITS its
        # brand from product titles (en-bh.ajmal.com lists "ARISTOCRAT CORAL EDP",
        # vendor="Ajmal", NOT "Ajmal Aristocrat"), so requiring the query brand token
        # rejected the exact SKU and threw away a genuine BHD price. Thread the
        # Shopify `vendor` (the product's own brand) as candidate_brand so a
        # brand-omitted title of the QUERY's brand resolves, while a WRONG-brand
        # candidate keeps the query brand required and is still rejected (no
        # wrong-match). Mirrors the proven magento_graphql/occ/noon/algolia pattern;
        # candidate_brand is gated by exact_gate_enabled() inside the matchers, so
        # flag-OFF (ENABLE_EXACT_PRICE_GATE=false) is byte-identical.
        _cand_brand = normalize_candidate_brand(product.get("vendor"))
        if not strict_title_match(product_name, title, candidate_brand=_cand_brand):
            continue
        # S3 #1 (discovery-match) — reject a different model-line variant.
        if variant_mismatch(product_name, title):
            continue
        # Keystone variant-add guard (coverage/independent review) — category-aware
        # superset/axes beyond variant_mismatch's pro/max set. Flag-safe (True when off).
        if not _selection_match(product_name, title, resolved_category, candidate_brand=_cand_brand):
            continue

        t_words = normalize_words(title)
        match_score = len(p_words & t_words) / len(p_words) if p_words else 0.0
        if match_score < 0.4:
            continue

        variants = product.get("variants")
        if not isinstance(variants, list) or not variants:
            continue
        # Variant-min decant guard (audit 2026-07-08): bind the queried size to a specific
        # variant instead of blindly pricing variants[0] (usually the smallest = a decant
        # served as the full bottle). Flag OFF → variants[0] (byte-identical).
        if variant_min_guard_enabled():
            variant = _select_shopify_variant(
                variants, product_name, title, resolved_category, _is_lux,
            )
            if variant is None:
                continue  # unbindable size/spread → pend this product (don't serve a decant)
        else:
            variant = variants[0] if isinstance(variants[0], dict) else {}
        amount = parse_price_string(str(variant.get("price", "")))
        if amount is None or amount <= 0:
            continue

        # M1 — convert from the store's base currency to the BHD target.
        if needs_conversion:
            amount = _convert_to_bhd(amount, store_currency)
            if amount is None or amount <= 0:
                continue

        # WS5 — variant precision: rank on (query size/concentration match,
        # word-overlap). The product title + the chosen variant's title (Shopify
        # often puts the size, e.g. "100ml", in the variant title) both feed the
        # signal. A better variant match wins even at equal/lower match_score.
        _variant_title = str(variant.get("title") or "")
        _signal_text = f"{title} {_variant_title}".strip()
        _conc_rank, _size_rank = variant_precision_rank(product_name, _signal_text)
        _flagship = flagship_basis_bonus(product_name, _signal_text, _is_lux)
        _rank = (_conc_rank + _size_rank + _flagship, match_score)
        if _rank > best_rank:
            handle = product.get("handle") or ""
            url = (
                f"https://{domain}/products/{handle}" if handle and domain
                else f"https://{domain}/" if domain else ""
            )
            # ---- capture axes -------------------------------------------
            # Flag OFF: exactly the pre-change expressions, on exactly the
            # pre-change input (`_signal_text`) — byte-identical.
            _sizes = extract_sizes_ml(_signal_text)
            _size = (sorted(_sizes)[0] + "ml") if _sizes else None
            _conc = extract_concentration(_signal_text)
            if wide_signal_text_enabled() and (_size is None or _conc is None):
                # NARROW-FIRST. The title/variant title is authoritative: the
                # widened text is a FALLBACK that may only fill a None, never
                # rewrite a value the narrow text already produced (a body that
                # says "also available in 100 ml" must not overwrite a "50ml"
                # title). Additive-only, so the flag can only widen capture.
                _wide = _wide_signal_capture_text(_signal_text, product)
                if _conc is None:
                    _conc = extract_concentration(_wide)
                if _size is None:
                    _wide_sizes = extract_sizes_ml(_wide)
                    # AMBIGUITY -> ABSTAIN. body_html is marketing copy: it names
                    # flankers, related items and bundle contents. The real
                    # om.swissarabian "MUSK 07 EDP + BODY LOTION GIFT SET" body
                    # lists a 50ml perfume AND a 300ml BODY LOTION; the legacy
                    # `sorted(...)[0]` is a STRING sort, so a naive union would
                    # ship "300ml" — the lotion — as the fragrance size. Take a
                    # widened size ONLY when the whole widened text agrees on one.
                    if len(_wide_sizes) == 1:
                        _size = next(iter(_wide_sizes)) + "ml"
            best = {
                "amount": round(amount, 2),
                "currency": target_currency,
                "original_currency": store_currency,
                "retailer": domain,
                "url": url,
                "in_stock": bool(variant.get("available", True)),
                "confidence": round(min(0.7 + match_score * 0.3, 1.0), 2),
                "estimated": False,
                # BH/GCC source-build (2026-06-25) — stamp by ACTUAL resolved
                # currency. A native-BHD store is genuine ("shopify_json", 7d TTL,
                # counts genuine-share). A NON-BHD store whose price we just
                # _convert_to_bhd'd is a real-but-converted figure → "converted_usd"
                # (the canonical converted sentinel: showable, 24h TTL, NOT genuine,
                # NOT the genuine-share KPI). Previously stamped "shopify_json"
                # unconditionally — a latent mis-stamp that, once GCC Shopify rows
                # exist in the registry, would bank a converted AED/SAR price as a
                # genuine BH price for a week and inflate the headline metric.
                "source_method": ("converted_usd" if needs_conversion else "shopify_json"),
                "concentration": _conc,
                "size": _size,
                "title": title,
                "match_score": round(match_score, 3),
            }
            best_rank = _rank

    return best


async def fetch_shopify_price(
    domain: str, product_name: str, currency: str = "BHD",
    resolved_category: Optional[str] = None,
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
    price = _match_shopify_product(catalog, product_name, currency, domain, resolved_category=resolved_category)
    if not price:
        return None

    # L2 content safety — drop a candidate whose surface trips the blocklist.
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{price.get('title', '')} {price.get('retailer', '') or domain} {product_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped Shopify candidate for %s", domain)
        return None
    return price


# ============================================================================
# bolo.bh direct-discovery (Wave 3a — BH Source-Intelligence, 2026-06-23)
# ============================================================================
# RECON-VERIFIED LIVE (2026-06-23): bolo.bh is a Nuxt SSR storefront whose PDPs
# are PLAIN-CURL READABLE (no JS render). The genuine BHD price is in the PDP's
# schema.org JSON-LD `@graph` → Product → offers (priceCurrency=BHD) AND mirrored
# in a Nuxt `"price":N` token next to a `<sup class="currency">BHD</sup>`.
#
# THE BINDING TRAP (F3a): the ~790KB PDP HTML carries MULTIPLE "price" values
# (the main product + a related-items carousel, e.g. 24.89 main vs 132/133
# related). We MUST bind the MAIN product. Two live-verified facts make this
# safe: (1) the FIRST `@graph` Product is the PDP's primary product (the URL
# resolved to it); (2) the FIRST Nuxt `"price"` token is the main price (the
# carousel prices come later in the HTML). So:
#   1. Parse the `@graph` Product offers BHD price directly (the reliable main-
#      product binding) — NOT the generic brand-gated extract_jsonld_price, which
#      false-negatives on bolo (its brand-field/accessory guards reject a long
#      marketing PDP name even when the offer IS the genuine main price — proven
#      live on the e.l.f. serum: extract_jsonld_price→None, @graph offer=8.16 BHD).
#   2. Fall back to the FIRST Nuxt `"price"` token only if JSON-LD has no offer.
# Both stamp `page_scrape_jsonld` (an EXISTING genuine method — no new set entry).
#
# Discovery is via resolve_pdp_via_sitemap (Wave 2 — a Redis-cached slug index
# built OFF-CLOCK by scripts/cron_index_sitemaps.py; the request path only READS
# the index, never crawls). A no-resolve / no-price returns None (NOT a pending
# dict — the cascade continues to an honest pending downstream).

# Bind the main product: the FIRST Nuxt `"price":N` token (the carousel prices
# trail it in the HTML). Tolerant of whitespace; integers and decimals.
_BOLO_NUXT_PRICE_RE = re.compile(r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)')
# The genuine-currency guard for the Nuxt fallback: a <sup class="currency">BHD
# </sup> must be present so we never stamp BHD on a non-BHD Nuxt number.
_BOLO_BHD_SUP_RE = re.compile(
    r'<sup[^>]*class="[^"]*currency[^"]*"[^>]*>\s*BHD\s*</sup>', re.I
)


def _bolo_jsonld_main_price(
    html: str, product_name: str, currency: str,
) -> Optional[Dict[str, Any]]:
    """The bolo-specific JSON-LD main-product price: the FIRST `@graph` Product's
    offers price in `currency`, validated against `product_name` (numbers +
    variant + word-overlap) so a wrong PDP can't slip through. Returns a price
    dict or None. Does NOT use the generic brand-gated extract_jsonld_price (it
    false-negatives on bolo's long marketing names)."""
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:  # noqa: BLE001 — a malformed page is a miss, never a crash
        return None
    target = (currency or "BHD").upper()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        graph = data.get("@graph") if isinstance(data, dict) else None
        nodes = graph if isinstance(graph, list) else (
            [data] if isinstance(data, dict) else []
        )
        for node in nodes:
            if not (isinstance(node, dict) and _is_product_type(node)):
                continue
            ld_name = node.get("name", "") or ""
            # C2 — same JSON-LD entity-decode as extract_jsonld_price (an
            # "&amp;" in the blob is the page's escaping, not identity); gated
            # to keep the flag-OFF path byte-identical.
            if exact_gate_enabled() and ld_name:
                ld_name = html_unescape(ld_name)
            # Validate the resolved PDP product against the query — a discovery
            # mis-resolve must not attribute the wrong product's price.
            # FAIL-CLOSED (source-intel review 2026-06-23, no-fab): a Product node
            # with NO `name` is UNVALIDATABLE — skip it rather than blindly return
            # its offer. _bolo_has_jsonld_product still sees the node (so the Nuxt
            # fallback stays suppressed), and an all-nameless page returns None →
            # honest miss, never a wrong-product price stamped genuine.
            if not ld_name:
                continue
            if product_name:
                if not numbers_match(product_name, ld_name):
                    continue
                if variant_mismatch(product_name, ld_name):
                    continue
                # Strict key-word bind (Codex HIGH-1, no-fab): EVERY >2-char
                # non-brand query word must appear in the candidate name — the
                # same guard _match_nasser_product uses. Without it a WRONG product
                # slips through: query "Tom Ford Oud Wood 100ml" vs an "Oud
                # Minerale ... 100ml" PDP — numbers_match passes VACUOUSLY ("100ml"
                # yields NO \b\d{2,}\b token, so there is no number to compare), no
                # variant qualifier differs, and the word-overlap is 4/5 == 0.8
                # ({tom,ford,oud,100ml} shared, only "wood" missing) — FAR above the
                # 0.4 floor, so raising that floor would NOT catch it. strict_title_
                # match is the discriminating guard: "wood" is absent from "Oud
                # Minerale" → every key word is NOT present → rejected.
                # KNOWN RECALL TRADEOFF (review NIT, errs SAFE = drop never wrong):
                # strict_title_match requires size/concentration tokens too, so a
                # fragrance query "Dior Sauvage EDP 100ml" vs a PDP name spelled
                # "Dior Sauvage Eau de Parfum" (size in a variant field) is dropped
                # to honest-pending. Dormant today (bolo/boutiqaat inert until the
                # sitemap cron); revisit with soft size/concentration tokens when the
                # cron is activated + real fragrance recall is measured.
                # NB: this sitemap-discovery path has NO _selection_match after
                # strict_title_match, so it must NOT pass candidate_brand here —
                # dropping the brand without the _selection_match variant-add guard
                # leaks a same-brand accessory ("Apple Watch" -> "...Sport Band")
                # (both-directions sweep wf_e759837b MED). Keep the legacy
                # brand-required gate; the candidate_brand relaxation is wired only at
                # adapters that run _selection_match(candidate_brand=...) alongside.
                if not strict_title_match(product_name, ld_name):
                    continue
                # Word-overlap bind (the docstring's third guard, Wave-3 reviewer
                # ISSUE 2): two products with no numbers/variant qualifiers
                # ("Logitech Mouse" vs "Kensington Presenter") both pass
                # numbers/variant VACUOUSLY — the token-overlap ratio is the real
                # bind for that class, so a sitemap mis-resolve can't slip through.
                # FAIL-CLOSED on an empty query token set (all-punctuation) — it
                # must NOT vacuously pass (mirrors _match_nasser_product's posture).
                _pw = normalize_words(product_name)
                if not _pw or (len(_pw & normalize_words(ld_name)) / len(_pw)) < 0.4:
                    continue
            offers = node.get("offers")
            if isinstance(offers, dict):
                offers = [offers]
            elif not isinstance(offers, list):
                continue
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                if str(offer.get("priceCurrency") or "").upper() != target:
                    continue
                try:
                    amount = float(offer.get("price") or offer.get("lowPrice") or 0)
                except (ValueError, TypeError):
                    continue
                if amount <= 0:
                    continue
                # is_available_state (not the literal substring) — handles SoldOut/
                # Discontinued + the URL/dict shapes; None(unknown) → in stock.
                _avail = is_available_state(offer.get("availability"))
                return {
                    "amount": round(amount, 3),
                    "currency": target,
                    "in_stock": True if _avail is None else _avail,
                    "name": ld_name,
                }
            return None  # main Product found but no usable offer → no fallback need
    return None


def _bolo_nuxt_main_price(html: str, currency: str) -> Optional[Dict[str, Any]]:
    """The bolo Nuxt fallback: the FIRST `"price":N` token (the main product —
    the carousel prices trail it), gated by a `<sup class="currency">BHD</sup>`
    so a non-BHD number is never BHD-stamped. Returns a price dict or None."""
    target = (currency or "BHD").upper()
    # Only honor the Nuxt number when the page shows a BHD currency marker.
    if target == "BHD" and not _BOLO_BHD_SUP_RE.search(html or ""):
        return None
    m = _BOLO_NUXT_PRICE_RE.search(html or "")
    if not m:
        return None
    try:
        amount = float(m.group(1))
    except (ValueError, TypeError):
        return None
    if amount <= 0:
        return None
    return {"amount": round(amount, 3), "currency": target, "in_stock": True, "name": ""}


def _bolo_has_jsonld_product(html: str) -> bool:
    """True iff the bolo PDP carries >=1 JSON-LD Product node. When True the
    JSON-LD is AUTHORITATIVE (it validated the product against the query in
    _bolo_jsonld_main_price); the unvalidated Nuxt-"price" fallback must NOT run,
    else a sitemap-mis-resolved WRONG-product PDP (whose JSON-LD product mismatched
    the query and was rejected) would get its price attributed (no-fab / wrong-SKU
    leak — Wave-3 reviewer ISSUE 1). A page with NO JSON-LD product still allows
    the Nuxt fallback (the sitemap slug-match is the only binding there)."""
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:  # noqa: BLE001 — malformed page is "no product", never a crash
        return False
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        graph = data.get("@graph") if isinstance(data, dict) else None
        nodes = graph if isinstance(graph, list) else (
            [data] if isinstance(data, dict) else []
        )
        if any(isinstance(n, dict) and _is_product_type(n) for n in nodes):
            return True
    return False


async def fetch_bolo_price(
    product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Direct-discovery genuine BHD price for bolo.bh (Wave 3a).

    discover (sitemap index, Wave 2) → curl-fetch the PDP → parse the JSON-LD
    main-product offer (then Nuxt-`"price"` fallback) → a genuine
    ``source_method="page_scrape_jsonld"`` price dict, or ``None``.

    A no-resolve / no-price returns ``None`` (NOT a pending dict — the cascade
    continues to an honest pending downstream; the WS-2 _price_fallback_on_miss
    revert lesson). Gated by ENABLE_PAGE_SCRAPE + L2 content-safety like the other
    Tier-1.5 entry points; gated showable by is_price_showable (the sample/
    implausible guards still bite). $0 — no Serper, no render."""
    if not ENABLE_PAGE_SCRAPE:
        return None
    from app.services.sitemap_discovery_service import resolve_pdp_via_sitemap
    pdp_url = resolve_pdp_via_sitemap("bolo.bh", product_name)
    if not pdp_url:
        return None  # cold/missing index or no match → honest miss, NOT pending
    # Codex HIGH-5: fetch with a redirect-validating same-site fetcher — a
    # sitemap-resolved bolo.bh url can 30x-redirect to an arbitrary host / private
    # IP / *.railway.internal; pin every hop to bolo.bh.
    html = await curl_fetch_html_same_site(pdp_url, "bolo.bh")
    if not html:
        return None

    parsed = _bolo_jsonld_main_price(html, product_name, currency)
    if not parsed:
        # The Nuxt-"price" fallback has NO product-name validation. Only use it
        # when the PDP has NO JSON-LD Product node — if a Product node exists but
        # _bolo_jsonld_main_price returned None, the JSON-LD is authoritative (the
        # product mismatched the query, or had no BHD offer), so Nuxt would
        # attribute the WRONG product's price (Wave-3 reviewer ISSUE 1, no-fab).
        if _bolo_has_jsonld_product(html):
            return None
        parsed = _bolo_nuxt_main_price(html, currency)
    if not parsed or not parsed.get("amount"):
        return None

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    listing_name = parsed.get("name") or ""
    price: Dict[str, Any] = {
        "amount": parsed["amount"],
        "currency": parsed.get("currency", currency),
        "retailer": "bolo.bh",
        "url": pdp_url,
        "in_stock": parsed.get("in_stock", True),
        "confidence": 1.0,
        "estimated": False,
        "source_method": "page_scrape_jsonld",
        "title": listing_name,
    }
    # frag-size-capture — carry the real listing size (ml/oz) for fragrance pair
    # fairness; no-op for non-fragrance. Uses the PDP JSON-LD name / og:title /
    # page <title> like extract_price_from_html does.
    _stamp_listing_size(price, product_name, soup, jsonld_name=listing_name)

    # The showable accuracy guards (sample/implausible-low/high) still bite — a
    # bolo decant under the fragrance floor must PEND, not show.
    if not is_price_showable(product_name, price):
        return None

    # L2 content safety — drop a candidate whose surface trips the blocklist.
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{listing_name} bolo.bh {product_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped bolo candidate for %s", product_name)
        return None
    logger.info(
        "[PRICE] bolo.bh genuine: %s %s for '%s' (%s)",
        price["currency"], price["amount"], product_name, pdp_url,
    )
    return price


# ============================================================================
# boutiqaat.com direct-discovery (Wave 3c — BH Source-Intelligence)
# ============================================================================
# RE-VERIFIED LIVE (2026-06-23, Wave-3c): boutiqaat.com /en-bh PDPs serve a
# GENUINE native-BHD price in PLAIN-curl-readable JSON-LD — a flat `@type:Product`
# node with `offers.price` + `offers.priceCurrency="BHD"` + availability. Proven
# across 4 product types: fragrance (Ghuyoum Alqassar 100ml EDP → 50.430 BHD),
# contact-lens conf SKU (10.460), bundle (Mother Day Box 4pcs → 43.050), and
# single beauty (Luminizer/Moisturizer → 15.930; Hair Revival Kit → 38.130). The
# old render-only/requires_super flag was the CONSERVATIVE pre-re-verify stance —
# the Wave-3c live probe cracks it to a $0 curl adapter (NO Serper, NO render).
#
# PER-SKU DATA GAP (verify-or-omit): some boutiqaat SKUs (a few `bdl`/sold-out
# items) server-render ONLY an Organization JSON-LD block (no Product offer). On
# those the adapter returns None — an honest miss, NOT a fabricated price — and
# the cascade continues to an honest pending. NOT rate-limiting: a known-good
# PDP re-fetches its price cleanly back-to-back (verified live).
#
# Discovery uses the SAME Wave-2 sitemap channel as bolo (resolve_pdp_via_sitemap,
# a request-path Redis index READ — NO crawl on the clock; the 47k-PDP urlset is
# indexed off-clock by cron_index_sitemaps). The PDP JSON-LD is a FLAT Product
# node, which the bolo helper _bolo_jsonld_main_price already handles (its
# non-@graph `[data]` branch) — so it is reused verbatim (numbers_match +
# variant_mismatch validation included). Stamps the EXISTING genuine
# source_method="page_scrape_jsonld" (no new _GENUINE_BH_SOURCE_METHODS string →
# parity test untouched).


async def fetch_boutiqaat_price(
    product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Direct-discovery genuine BHD price for boutiqaat.com (Wave 3c).

    discover (sitemap index, Wave 2) → curl-fetch the PDP → parse the flat
    JSON-LD `@type:Product` main-offer (the bolo helper handles the non-@graph
    case) → a genuine ``source_method="page_scrape_jsonld"`` price dict, or
    ``None``.

    A no-resolve / no-Product-offer (a per-SKU data gap) returns ``None`` (NOT a
    pending dict — the cascade continues to an honest pending downstream). Gated by
    ENABLE_PAGE_SCRAPE + L2 content-safety like the other Tier-1.5 entry points;
    gated showable by is_price_showable (the sample/implausible guards still bite).
    $0 — no Serper, no render."""
    if not ENABLE_PAGE_SCRAPE:
        return None
    from app.services.sitemap_discovery_service import resolve_pdp_via_sitemap
    pdp_url = resolve_pdp_via_sitemap("boutiqaat.com", product_name)
    if not pdp_url:
        return None  # cold/missing index or no match → honest miss, NOT pending
    # Codex HIGH-5: fetch with a redirect-validating same-site fetcher — a
    # sitemap-resolved boutiqaat.com url can 30x-redirect to an arbitrary host /
    # private IP / *.railway.internal; pin every hop to boutiqaat.com.
    html = await curl_fetch_html_same_site(pdp_url, "boutiqaat.com")
    if not html:
        return None

    # boutiqaat ships a FLAT @type:Product JSON-LD (no @graph). _bolo_jsonld_main_price
    # handles that via its `[data]` branch + the same numbers/variant validation.
    parsed = _bolo_jsonld_main_price(html, product_name, currency)
    if not parsed or not parsed.get("amount"):
        return None  # Organization-only / no offer (per-SKU gap) → honest None

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    listing_name = parsed.get("name") or ""
    price: Dict[str, Any] = {
        "amount": parsed["amount"],
        "currency": parsed.get("currency", currency),
        "retailer": "boutiqaat.com",
        "url": pdp_url,
        "in_stock": parsed.get("in_stock", True),
        "confidence": 1.0,
        "estimated": False,
        "source_method": "page_scrape_jsonld",
        "title": listing_name,
    }
    # frag-size-capture — carry the real listing size (ml/oz) for fragrance pair
    # fairness; no-op for non-fragrance. Same as bolo / extract_price_from_html.
    _stamp_listing_size(price, product_name, soup, jsonld_name=listing_name)

    # The showable accuracy guards (sample/implausible-low/high) still bite — a
    # boutiqaat decant under the fragrance floor must PEND, not show.
    if not is_price_showable(product_name, price):
        return None

    # L2 content safety — drop a candidate whose surface trips the blocklist.
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{listing_name} boutiqaat.com {product_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped boutiqaat candidate for %s", product_name)
        return None
    logger.info(
        "[PRICE] boutiqaat.com genuine: %s %s for '%s' (%s)",
        price["currency"], price["amount"], product_name, pdp_url,
    )
    return price


# ============================================================================
# nasserpharmacy.com direct-discovery (Wave 3b — BH Source-Intelligence)
# ============================================================================
# RECON-VERIFIED LIVE (2026-06-23): nasserpharmacy.com exposes its OWN JSON
# search API (newapi.nasserpharmacy.com /v1/filterSearchs) returning genuine
# native-BHD prices in a SINGLE authenticated GET — NO second /newproduct call,
# NO Serper, NO render. `page=1` is REQUIRED (422 without). `currency_code=BHD`
# drives server-side FX. The price is in the SEARCH response directly.
#
# The price/special are 3-decimal BHD-fils strings; `special != "0"` is an active
# offer (prefer the LOWER of price/special). Match the query to `products[].name`
# via strict_title_match/numbers_match. Stamp `source_method="local_bhd"` (an
# EXISTING genuine method, native BHD — no new set entry).
#
# F3b — the guest token is a static const cracked from the app bundle; it rotates
# on a FE redeploy. A wrong/expired token → HTTP 401 (proven live — fails cleanly,
# never silently). Token-missing / 401 / empty → None (verify-or-omit). The ONE
# live-credential risk in the bundle; re-probe via scripts/verify_source_registry.

_NASSER_SEARCH_URL = "https://newapi.nasserpharmacy.com/v1/filterSearchs"
# Guest auth header. The `Nasser` header carries a base64-ish
# {"token":...,"id":...} guest session cracked from the app bundle. On rotation
# the live probe / verify_source_registry surfaces a 401 → re-scrape.
#
# MED-2 (Codex re-review): the token is REQUIRED via the NASSER_GUEST_TOKEN env
# var (set on Railway) and defaults to "" — fail closed. A fresh process with no
# env var gets an empty token; the `if not _NASSER_GUEST_HEADERS.get("Nasser")`
# guard in fetch_nasser_price then short-circuits to None, so nasser is DORMANT
# (no network, no credential) until the var is set. The prior in-source token is
# BURNED (it lived in branch history) and MUST be re-scraped fresh and set on
# Railway before the adapter can activate. No literal credential lives in source.
_NASSER_GUEST_TOKEN = os.environ.get("NASSER_GUEST_TOKEN", "")
_NASSER_GUEST_HEADERS = {
    "Nasser": _NASSER_GUEST_TOKEN,
    "MOBILEOS": "REACT",
    "APPVERSION": "1",
}

# MED-2 kill switch — flip ENABLE_NASSER_ADAPTER=false in Railway to disable the
# adapter entirely (e.g. token permanently dead, or to stop hammering a rotated
# credential). Truthy DEFAULT True so prod is unchanged until explicitly disabled.
ENABLE_NASSER_ADAPTER = os.environ.get("ENABLE_NASSER_ADAPTER", "true").lower() != "false"

# MED-2 401 circuit breaker — on a rotated/expired token nasser returns 401. After
# >=_NASSER_401_THRESHOLD consecutive 401s within the cooldown window the adapter
# short-circuits to None (stops hammering the dead token). A 200 resets it. Backed
# by a Redis counter with a short TTL; fail-OPEN (Redis down → proceed).
_NASSER_401_KEY = "breaker:nasser:401"
_NASSER_401_THRESHOLD = 3
_NASSER_401_COOLDOWN_SECONDS = 600  # ~10min


def _nasser_breaker_tripped() -> bool:
    """True when the 401 circuit breaker is tripped (>=threshold consecutive 401s
    within the cooldown window). Fail-OPEN: any Redis error / Redis-down → False
    (proceed) so an infra blip never silently kills a working adapter."""
    try:
        from app.services.cache_service import _redis_get
        raw = _redis_get(_NASSER_401_KEY)
        return raw is not None and int(raw) >= _NASSER_401_THRESHOLD
    except Exception:  # noqa: BLE001 — fail-open
        return False


def _nasser_breaker_record_401() -> None:
    """Increment the consecutive-401 counter (with a cooldown TTL). Fail-OPEN."""
    try:
        from app.services.cache_service import _redis_incr, _redis_expire
        count = _redis_incr(_NASSER_401_KEY)
        # (Re)arm the cooldown window on every 401 so a fresh burst keeps it open.
        if count:
            _redis_expire(_NASSER_401_KEY, _NASSER_401_COOLDOWN_SECONDS)
    except Exception:  # noqa: BLE001 — fail-open
        pass


def _nasser_breaker_reset() -> None:
    """A 200 clears the consecutive-401 counter (token is alive again). Fail-OPEN."""
    try:
        from app.services.cache_service import redis_client
        if redis_client:
            redis_client.delete(_NASSER_401_KEY)
    except Exception:  # noqa: BLE001 — fail-open
        pass


# MED-3 — out-of-stock markers (EN + AR) used to derive in_stock from stock_text
# when no numeric stock_count is present. نفذ / غير متوفر = sold out / unavailable.
_NASSER_OOS_MARKERS = (
    "out of stock", "sold out", "unavailable", "نفذ", "غير متوفر",
)


def _derive_nasser_in_stock(prod: Dict[str, Any]) -> Optional[bool]:
    """Derive in_stock from the REAL signal the nasser payload carries (MED-3 re-
    review — no more fabrication in EITHER direction). Priority: numeric
    ``stock_count`` (int/float > 0) → ``stock_text`` (False iff an out-of-stock
    marker, else True) → ``None`` when there is NO stock signal at all (was an
    optimistic hard-coded True; now we OMIT rather than claim availability we
    can't verify)."""
    stock_count = prod.get("stock_count")
    # int OR float (review NIT: a float-encoded 0.0 must read as out-of-stock, not
    # fall through to the no-signal default); exclude bool (a subclass of int).
    if isinstance(stock_count, (int, float)) and not isinstance(stock_count, bool):
        return stock_count > 0
    # Some payloads ship stock_count as a numeric string — honor it too.
    if isinstance(stock_count, str) and stock_count.strip().lstrip("-").isdigit():
        try:
            return int(stock_count) > 0
        except (ValueError, TypeError):
            pass
    stock_text = prod.get("stock_text")
    if isinstance(stock_text, str) and stock_text.strip():
        low = stock_text.lower()
        return not any(marker in low for marker in _NASSER_OOS_MARKERS)
    return None  # MED-3 re-review: no stock signal → unknown, do NOT fabricate


def _match_nasser_product(
    payload: Optional[Dict[str, Any]], product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """PURE matcher: the best query-matching product in a nasser ``filterSearchs``
    JSON ``payload`` and its genuine BHD price dict, or ``None``.

    Reuses the price_service title helpers (numbers_match + strict_title_match +
    word-overlap) like the Shopify matcher. Prefers the LOWER of price/special
    (special != "0" = active offer). Rounds to 3 decimals (BHD fils). Stamps
    ``source_method="local_bhd"`` (genuine, native BHD)."""
    if not isinstance(payload, dict):
        return None
    products = payload.get("products")
    if not isinstance(products, list) or not products:
        return None

    p_words = normalize_words(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for prod in products:
        if not isinstance(prod, dict):
            continue
        name = prod.get("name") or ""
        if not name:
            continue
        # NOTE: NO is_accessory / is_counterfeit pre-filter here. Those guards are
        # for NOISY Serper-shopping listings; on a direct pharmacy-API product the
        # name is the resolved product and strict_title_match (all query words
        # present) + numbers_match + variant_mismatch + the word-overlap gate are
        # the real protection. is_accessory false-positives on benign skincare
        # descriptors ("...For Normal To Oily SKIN" → 'skin' is an accessory
        # keyword) — it must not reject a genuine pharmacy product.
        if not numbers_match(product_name, name):
            continue
        if not strict_title_match(product_name, name):
            continue
        if variant_mismatch(product_name, name):
            continue
        t_words = normalize_words(name)
        score = len(p_words & t_words) / len(p_words) if p_words else 0.0
        if score < 0.4:
            continue
        # The server returns BHD natively; only honor a BHD symbol (no FX here).
        if str(prod.get("price_symbol") or "").upper() not in ("BHD", currency.upper()):
            continue
        price_val = parse_price_string(str(prod.get("price") or ""))
        special_raw = str(prod.get("special") or "0").strip()
        special_val = parse_price_string(special_raw)
        # special != "0" (and > 0) is an active offer — prefer the LOWER price.
        amount = price_val
        if special_val is not None and special_val > 0 and special_raw not in ("0", "0.000"):
            if amount is None or special_val < amount:
                amount = special_val
        if amount is None or amount <= 0:
            continue
        decimals = prod.get("decimal_places")
        ndp = decimals if isinstance(decimals, int) and 0 <= decimals <= 6 else 3
        if score > best_score:
            best_score = score
            alias = prod.get("product_alias") or prod.get("url_alias") or ""
            url = f"https://www.nasserpharmacy.com/bh-en/{alias}" if alias else ""
            best = {
                "amount": round(amount, ndp),
                "currency": (currency or "BHD").upper(),
                "retailer": "nasserpharmacy.com",
                "url": url,
                "confidence": round(min(0.7 + score * 0.3, 1.0), 2),
                "estimated": False,
                "source_method": "local_bhd",
                "title": name,
            }
            # MED-3 re-review: stamp in_stock ONLY when the payload carries a real
            # stock signal. None (no signal) → OMIT the key — never fabricate
            # availability in EITHER direction. Downstream reads are .get-style
            # (Optional[bool] schema), so a missing key is safe.
            derived_in_stock = _derive_nasser_in_stock(prod)
            if derived_in_stock is not None:
                best["in_stock"] = derived_in_stock
    return best


async def fetch_nasser_price(
    product_name: str, currency: str = "BHD",
) -> Optional[Dict[str, Any]]:
    """Direct-discovery genuine BHD price for nasserpharmacy.com (Wave 3b).

    A SINGLE authenticated GET to /v1/filterSearchs (page=1 REQUIRED,
    currency_code=BHD) → match the query → a genuine
    ``source_method="local_bhd"`` price dict, or ``None``.

    Token-missing / 401 / non-200 / empty / no-match → ``None`` (verify-or-omit;
    NOT a pending dict). Gated by ENABLE_NASSER_ADAPTER (kill switch) +
    ENABLE_PAGE_SCRAPE + L2 content-safety; a 401 circuit breaker short-circuits
    after >=3 consecutive 401s (rotated token). Gated showable by
    is_price_showable. $0 — no Serper, no render."""
    if not ENABLE_NASSER_ADAPTER:
        return None  # MED-2 kill switch
    if not ENABLE_PAGE_SCRAPE:
        return None
    if not _NASSER_GUEST_HEADERS.get("Nasser"):
        return None  # no token → cannot auth → honest None
    if _nasser_breaker_tripped():
        # MED-2 — token looks rotated (>=3 recent 401s); don't hammer it. Short-
        # circuit WITHOUT a network call until the cooldown window lapses.
        logger.info("[PRICE] nasser 401 breaker tripped — skipping '%s'", product_name)
        return None
    try:
        from curl_cffi import requests as curl_requests
        params = {
            "search_term": product_name,
            "page": 1,                 # REQUIRED — 422 without
            "limit": 20,
            "lang": 1,
            "currency_code": currency or "BHD",  # drives server-side FX
        }
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                _NASSER_SEARCH_URL,
                params=params,
                headers=_NASSER_GUEST_HEADERS,
                impersonate="chrome",
                timeout=8,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
        logger.warning("[PRICE] nasser fetch failed for %s: %s", product_name, exc)
        return None
    if resp.status_code == 401:
        # MED-2 — token rotated (the one live-credential risk, F3b). Record the
        # consecutive-401 for the circuit breaker so a sustained burst trips it.
        _nasser_breaker_record_401()
        logger.info("[PRICE] nasser HTTP 401 (token rotated?) for '%s'", product_name)
        return None
    if resp.status_code != 200:
        # 422 = bad params; any other non-200 = a miss (NOT a 401, so don't count it).
        logger.info("[PRICE] nasser HTTP %s for '%s'", resp.status_code, product_name)
        return None
    # A live 200 → the token works; clear any stale 401 streak.
    _nasser_breaker_reset()
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001 — non-JSON body → miss
        return None

    price = _match_nasser_product(payload, product_name, currency)
    if not price:
        return None
    if not is_price_showable(product_name, price):
        return None

    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{price.get('title', '')} nasserpharmacy.com {product_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped nasser candidate for %s", product_name)
        return None
    logger.info(
        "[PRICE] nasser genuine: %s %s for '%s'",
        price["currency"], price["amount"], product_name,
    )
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
            # WS-2 (genuine-bh bundle): inner curl timeout shrunk 15→4s. The
            # supplement branch wraps fetch_iherb_price in a 4s asyncio.wait_for,
            # but a wait_for cannot hard-cancel the run_in_executor thread — so the
            # inner curl timeout MUST be ≤ the outer bound or the executor thread
            # leaks past the cancel and burns into the 15s Phase-1 price cap.
            lambda: curl_requests.get(search_url, impersonate="chrome", timeout=4, allow_redirects=True)
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

        # CORRECTNESS (B1) — the requested SKU may be ABSENT from the iHerb results
        # while a same-brand DIFFERENT product is present (Solgar D3 5000IU query ->
        # only Solgar Magnesium Citrate on the page). The legacy best-overlap fallback
        # had NO threshold, so it shipped that wrong product's price. Gate brand-matches
        # through the shared identity gate; a miss returns None (pend), never a
        # same-brand flanker. No-op when the rollback flag is OFF (legacy pick below).
        if exact_gate_enabled():
            exact = [
                p for p in brand_matches
                if _selection_match(full_name, p["title"], "supplements",
                                    candidate_brand=p.get("brand", ""))
            ]
            if not exact:
                return None
            # Among identity-matched cards prefer a full name-subset match, else the
            # first (same identity); never a cheaper NON-matching card.
            best = next(
                (p for p in exact if name_words.issubset(normalize_words(p["title"]))),
                exact[0],
            )
        else:
            best = None
            full_matches = [p for p in brand_matches
                            if name_words.issubset(normalize_words(p["title"]))]
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

        # S3-genuine (team-lead 2026-06-14) — the regional iHerb storefront
        # ({region_code}.iherb.com) serves its data-ga-discount-price NATIVELY in
        # the region currency (bh.iherb.com → BHD). A native-BHD price is GENUINE
        # → stamp local_bhd, NOT converted_usd. Labeling it converted_usd
        # undercounts the genuine-BH-price-share (a real BHD price miscounted as a
        # conversion). Rule: original_currency == region currency → local_bhd;
        # only a genuinely-foreign-origin price is converted_usd.
        _origin = currency  # the regional storefront prices in the region currency
        _genuine_bh = str(_origin).upper() == str(currency).upper()
        return {
            "amount": best["price"],
            "original_currency": _origin,
            "currency": currency,
            "retailer": "iHerb",
            "url": best["url"],
            # B1 — keep the matched product title so the chokepoint + cache-write
            # guard can re-verify identity (it was stripped before, hiding wrong picks).
            "title": best.get("title", ""),
            "in_stock": True,
            "confidence": 1.0,
            "estimated": False,
            "_cached": False,
            "iherb_rating": best.get("rating"),
            "iherb_review_count": best.get("review_count"),
            "source_method": "local_bhd" if _genuine_bh else "converted_usd",
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

    result = await _try_pharmacy_urls(pharmacy_urls, brand, currency, full_name)
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
        result = await _try_pharmacy_urls(site_urls, brand, currency, full_name)
        if result:
            return result
    except Exception as e:
        logger.warning(f"[PRICE] Site search failed: {e}")

    return None


async def _try_pharmacy_urls(
    pharmacy_urls: List[Tuple[str, str]],
    brand: str,
    currency: str,
    full_name: str = "",
) -> Optional[Dict[str, Any]]:
    """Try fetching JSON-LD price from a list of pharmacy URLs.

    `full_name` (B1) — the full requested product, threaded into extract_jsonld_price
    as `query_name` so its identity gate is ARMED: a multi-Product same-brand pharmacy
    page can NOT attribute the cheapest unrelated same-brand item to the query."""
    if not pharmacy_urls:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url, retailer_name in pharmacy_urls[:3]:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    continue

                price_data = extract_jsonld_price(
                    resp.text, brand, currency, query_name=full_name,
                )
                if price_data:
                    # L2 content safety — pharmacy JSON-LD entry point
                    # (Bundle B, team-lead expansion of spec sec 5.2).
                    from app.services.content_safety_service import get_content_safety_service
                    _ld_title = price_data.get("name") or price_data.get("title", "")
                    _surface = f"{_ld_title} {brand} {retailer_name}"
                    if not get_content_safety_service().is_text_safe(_surface):
                        logger.info("[content_safety] L2 dropped pharmacy candidate for %s", retailer_name)
                        continue
                    return {
                        "amount": price_data["amount"],
                        "original_currency": currency,
                        "currency": currency,
                        "retailer": retailer_name,
                        "url": url,
                        # B1 — carry the matched JSON-LD product name so the chokepoint
                        # + cache-write guard can re-verify identity.
                        "title": _ld_title,
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
    """True iff a GENUINE candidate confirms the race: (a) a genuine candidate
    has rank >= HIGH_RANK_THRESHOLD, or (b) two GENUINE candidates agree within
    AGREEMENT_PCT.

    S3 electronics-authority (prod-verify fix): confirmation ends the race and
    CANCELS pending scrapers. A converted_usd/estimated candidate must NOT
    trigger it — apple.com's converted_usd curl (rank 85) was confirming early
    and cancelling sharafdg's pending GENUINE curl before it could win. Only a
    genuine BH price ends the race; a converted figure waits for the genuine one."""
    genuine = [c for c in candidates if _is_genuine_bh_candidate(c)]
    for c in genuine:
        if c.get("rank", 0) >= HIGH_RANK_THRESHOLD:
            return True
    for i in range(len(genuine)):
        for j in range(i + 1, len(genuine)):
            if _candidates_agree(genuine[i], genuine[j]):
                return True
    return False


# S3 electronics-authority (prod-verify fix) — genuine BH source-methods. A
# candidate carrying one of these is a real Bahrain shelf price; a converted_usd
# / estimated one is a foreign/guessed figure. The fan_out winner MUST prefer a
# genuine BH price over a converted one REGARDLESS of price/rank (CLAUDE.md
# "MOST AUTHORITATIVE not lowest"). Prod-verify: apple.com converted 198.9
# (rank 85) was beating the genuine sharafdg page_scrape 244.99 (rank 85) on the
# lowest-value tie-break.
_GENUINE_BH_SOURCE_METHODS = frozenset({
    "page_scrape", "page_scrape_jsonld", "page_scrape_rendered",
    "local_bhd", "shopify_json",
    # the ACTUAL method strings the fan_out scrapers stamp (scs.py): the
    # firecrawl scraper emits "firecrawl_brand_domain", scrapedo emits
    # "scrapedo_rendered". A rendered genuine BH price is still genuine.
    "firecrawl", "firecrawl_brand_domain", "scrapedo_rendered",
    "official_brand",
    # BH/GCC source-build (2026-06-25) — the 5 new $0 direct-fetch adapters stamp
    # these ONLY for a genuine NATIVE-BHD price (a converted GCC→BHD price always
    # stamps the literal "converted_usd", never one of these). None contains the
    # substring "converted"/"estimate" so they pass the price_cache_ttl:159 /
    # _is_genuine_bh_candidate:5029 substring guards → 7d TTL + showable +
    # no-negcache + counted in the genuine-share KPI. Mirrored in eval_runner.py
    # GENUINE_BH_SOURCE_METHODS (tests/test_eval_genuine_methods_parity.py pins
    # the two sets equal).
    "woo_store_api", "salla_api", "occ_rest_bhd",
    "magento_graphql_bhd", "rest_json_bhd",
    # Zyte render-tier (2026-06-26) — a genuine NATIVE-BHD price rendered from an
    # Akamai-walled luxury store (sephora.me) via Zyte + geolocation=BH. OFF-CLOCK
    # only (seed/warmer); the live cascade serves it from cache. Genuine → 7d TTL.
    "zyte_render_bhd",
})


def _is_genuine_bh_candidate(c: dict) -> bool:
    """True iff a fan_out candidate is a genuine BH price (not converted/estimate
    AND not from a GLOBAL-tier domain).

    Checks both the candidate's source_method and its raw_data's (the curl
    scraper stamps the genuine method on raw_data; a global-tier downgrade sets
    converted_usd on both).

    apple-phantom hotfix (prod-verify on 110d0ff): a GLOBAL-tier domain
    (apple.com/samsung.com — no Bahrain storefront) stamped with a genuine method
    (page_scrape_jsonld) was counting as genuine — a PHANTOM. So ALSO require the
    candidate's retailer/domain to NOT be registry tier='global' (defense-in-
    depth: the _curl_scraper converted_usd downgrade is the first line; this is
    the second, so apple.com is never genuine even if the downgrade didn't fire).
    gcc/bahrain-tier and OFF-registry (None — a discovered BH retailer PDP) stay
    genuine; only an explicit global-tier domain is excluded."""
    sm = (c.get("source_method") or "")
    raw = c.get("raw_data") or {}
    raw_sm = (raw.get("source_method") or "")
    # converted/estimate on EITHER disqualifies (a global-tier downgrade stamps
    # converted_usd on raw_data even when the rank-name was page_scrape_jsonld).
    if "converted" in sm or "converted" in raw_sm or "estimated" in sm or "estimated" in raw_sm:
        return False
    if not (sm in _GENUINE_BH_SOURCE_METHODS or raw_sm in _GENUINE_BH_SOURCE_METHODS):
        return False
    # apple-phantom — a global-tier domain can NEVER be a genuine BH price.
    retailer = raw.get("retailer") or c.get("retailer") or raw.get("url") or ""
    if retailer:
        try:
            from app.services.source_router import registry_tier
            if registry_tier(retailer) == "global":
                return False
        except Exception:  # noqa: BLE001 — never let the tier lookup block a price
            pass
    return True


def _select_best(candidates: List[dict]) -> Optional[dict]:
    """Pick the fan_out winner. AUTHORITY first: a genuine BH price beats a
    converted_usd/estimated one regardless of rank/price. Within the same
    authority tier: highest-rank wins, ties broken by lowest value."""
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda c: (
            1 if _is_genuine_bh_candidate(c) else 0,  # genuine BH tier first
            c.get("rank", 0),
            -float(c.get("value", 0)),
        ),
    )


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
