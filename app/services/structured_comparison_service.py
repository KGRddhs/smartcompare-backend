"""
Structured Comparison Service - Main orchestrator for product comparisons
Handles caching, parallel fetching, and assembling complete product data
"""
import os
import re
import json
import time
import asyncio
import logging
import httpx
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.services.extraction_service import (
    parse_product_query,
    extract_specs,
    extract_price,
    extract_price_from_training_data,
    extract_reviews,
    generate_comparison,
    get_specs_cache_key,
    get_price_cache_key,
    get_reviews_cache_key,
    GCC_REGIONS
)
from app.services.serper_service import search_product_prices, search_price_organic, search_web
from app.services.cache_service import get_cached, set_cached
from app.services.drug_database_service import find_matching_drugs, format_drug_context
from app.services.scoring_service import get_scoring_service, MISSING_SCORE
from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed,
)
from app.services import firecrawl_service, scrapedo_service

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
ENABLE_PAGE_SCRAPE = os.environ.get("ENABLE_PAGE_SCRAPE", "true").lower() != "false"

logger = logging.getLogger(__name__)

# Pattern for stripping model variants to broaden price searches
MODEL_VARIANT_PATTERN = re.compile(r'\s+(pro|plus|max|ultra|\d{2,}gb|\d+tb)$', re.IGNORECASE)

# Cache TTLs (in seconds)
SPECS_CACHE_TTL = 7 * 24 * 60 * 60    # 7 days - specs rarely change
PRICE_CACHE_TTL = 24 * 60 * 60         # 24 hours - prices change daily
REVIEWS_CACHE_TTL = 7 * 24 * 60 * 60   # 7 days - reviews aggregate slowly

# Retailer quality tiers — prefer official/authorized retailers over resellers
# Keys are lowercase substrings matched against the Serper "source" field
RETAILER_TIERS = {
    # Tier 1: Official stores & major authorized retailers (score 1.0)
    "amazon": 1.0,
    "apple": 1.0,
    "samsung": 1.0,
    "best buy": 1.0,
    "bestbuy": 1.0,
    "walmart": 1.0,
    "target": 1.0,
    "noon": 1.0,
    "jarir": 1.0,
    "extra": 1.0,       # eXtra (GCC)
    "lulu": 1.0,
    "carrefour": 1.0,
    "sharaf dg": 1.0,
    "virgin megastore": 1.0,
    "microsof": 1.0,     # Microsoft Store (matches "microsoft")
    "google store": 1.0,
    "oneplus": 1.0,
    "sony": 1.0,
    "dell": 1.0,
    "hp store": 1.0,
    "lenovo": 1.0,
    "iherb": 1.0,
    "vitacost": 1.0,
    "gnc": 1.0,
    # Tier 1: Luxury fashion official + authorized retailers
    "hermes": 1.0,
    "hermès": 1.0,
    "louis vuitton": 1.0,
    "louisvuitton": 1.0,
    "chanel": 1.0,
    "gucci": 1.0,
    "prada": 1.0,
    "dior": 1.0,
    "burberry": 1.0,
    "fendi": 1.0,
    "nordstrom": 1.0,
    "farfetch": 1.0,
    "ssense": 1.0,
    "net-a-porter": 1.0,
    "harrods": 1.0,
    "selfridges": 1.0,
    "sephora": 1.0,
    "ulta": 1.0,
    # Tier 2: Reputable specialty retailers (score 0.7)
    "newegg": 0.7,
    "b&h": 0.7,
    "bhphoto": 0.7,
    "adorama": 0.7,
    "costco": 0.7,
    "ubuy": 0.7,
    "micro center": 0.7,
    "john lewis": 0.7,
    "currys": 0.7,
    "fnac": 0.7,
    # Tier 3: Marketplaces with mixed new/used/refurb (score 0.3)
    "ebay": 0.3,
    "aliexpress": 0.3,
    "alibaba": 0.3,
    "temu": 0.3,
    "wish": 0.3,
    "dhgate": 0.3,
    "banggood": 0.3,
    "gearbest": 0.3,
    "etsy": 0.3,
    "mercari": 0.3,
    "swappa": 0.3,
    "backmarket": 0.3,
    "back market": 0.3,
    "refurbished": 0.3,
}
DEFAULT_RETAILER_SCORE = 0.5  # Unknown retailers get benefit of the doubt

# Fields where numeric values must match exactly during citation verification
NUMERIC_SPEC_FIELDS = {"ram", "storage", "battery", "weight", "display", "count", "dosage",
                       "nutrition_calories", "nutrition_protein", "nutrition_fat", "nutrition_carbs"}

# Retailer search URL templates — maps retailer name (lowercase) to search page URL
# Used instead of Serper's "link" field which is a Google Shopping redirect
RETAILER_SEARCH_URLS = {
    # Major US/Global retailers
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
    # GCC retailers
    "noon": "https://www.noon.com/search?q={query}",
    "jarir": "https://www.jarir.com/sa-en/catalogsearch/result/?q={query}",
    "extra": "https://www.extra.com/en-sa/search/?q={query}",
    "sharaf dg": "https://uae.sharafdg.com/search/?q={query}",
    "ubuy": "https://www.ubuy.com.bh/en/search?q={query}",
    "lulu": "https://www.luluhypermarket.com/en-bh/search?q={query}",
    "carrefour": "https://www.carrefouruae.com/mafuae/en/search?q={query}",
    "virgin megastore": "https://www.virginmegastore.ae/search/{query}",
    # Brand stores
    "apple": "https://www.apple.com/shop/buy?fh={query}",
    "samsung": "https://www.samsung.com/search/?searchvalue={query}",
    "dell": "https://www.dell.com/en-us/search/{query}",
    "lenovo": "https://www.lenovo.com/us/en/search?query={query}",
    # UK/EU retailers
    "currys": "https://www.currys.co.uk/search/{query}",
    "john lewis": "https://www.johnlewis.com/search?search-term={query}",
    "fnac": "https://www.fnac.com/SearchResult/ResultList.aspx?Search={query}",
    # Marketplaces
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={query}",
    "aliexpress": "https://www.aliexpress.com/wholesale?SearchText={query}",
    "temu": "https://www.temu.com/search_result.html?search_key={query}",
    "back market": "https://www.backmarket.com/en-us/search?q={query}",
    "backmarket": "https://www.backmarket.com/en-us/search?q={query}",
    "swappa": "https://swappa.com/search?q={query}",
    # Health/Supplement stores
    "iherb": "https://bh.iherb.com/search?kw={query}",
    "vitacost": "https://www.vitacost.com/search?t={query}",
    "nasser pharmacy": "https://www.nasserpharmacy.com/search?q={query}",
    # Pharmacy/health retailers (BH)
    "boots": "https://www.bn.boots.com/search?q={query}",
    "al deerah": "https://aldeerahpharmacy.com/catalogsearch/result/?q={query}",
}


class StructuredComparisonService:
    """
    Main service for structured product comparisons.
    
    Flow:
    1. Parse query → extract product names
    2. For each product (parallel):
       a. Check cache for specs/prices/reviews
       b. Fetch missing data via search + extraction
       c. Generate pros/cons
    3. Compare products
    4. Return structured result
    """
    
    def __init__(self):
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}  # Reuse shopping data between price and rating
    
    async def compare_from_text(
        self,
        query: str,
        region: str = "bahrain",
        include_specs: bool = True,
        include_reviews: bool = True,
        include_pros_cons: bool = True,
        nocache: bool = False,
        selected_category: Optional[str] = None,
        vision_products: Optional[List[Dict]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for text-based comparisons.

        Args:
            vision_products: If provided (from camera input), skip parse_product_query
                             and use these directly. Each dict has brand, name, visible_price, confidence.
            user_id: If provided, fetches behavioral profile for weight adjustments
                     and triggers fire-and-forget profile update after comparison.

        Example: compare_from_text("iPhone 15 vs Galaxy S24", "bahrain")
        """
        start_time = datetime.now()
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}  # Clear per-request to prevent cross-request data leak

        try:
            # Step 1: Parse the query (or use vision products directly)
            if vision_products and len(vision_products) >= 2:
                # Camera input: use vision-identified products directly — no re-parsing
                # This preserves exact product names (e.g., "Vitamin D-3 360 Softgels")
                products = []
                for vp in vision_products[:2]:
                    brand = vp.get("brand", "Unknown")
                    vname = vp.get("name", "Unknown Product")
                    full = f"{brand} {vname}".strip()
                    # Auto-detect category for vision products (no GPT parser to classify)
                    category = "supplements" if self._is_supplement_query(full) else "other"
                    products.append({
                        "brand": brand,
                        "name": vname,               # GPT prompt: "{brand} {name}" = "NOW Vitamin D-3 360 Softgels"
                        "variant": vp.get("size_or_count"),  # "360 Softgels", "128GB", etc. — used for cache key + specs hint
                        "category": category,
                        "search_query": full,         # Serper search: "NOW Vitamin D-3 360 Softgels"
                        "_vision": True,              # Flag for display name override
                    })
                logger.info(f"[VISION] Using vision-identified products directly: {[p['search_query'] for p in products]}")
            else:
                logger.info(f"Parsing query: {query}")
                parsed, usage = await parse_product_query(query)
                self._track_gpt_cost(usage)

                if not parsed.get("products") or len(parsed["products"]) < 2:
                    return {
                        "success": False,
                        "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'",
                        "parsed": parsed
                    }

                products = parsed["products"][:2]  # Limit to 2 products
                logger.info(f"Identified products: {products}")

            # Determine detected category from first product
            detected_category = products[0].get("category", "other")

            # Track category switching (selected vs AI-detected)
            category_switched = False
            original_category = None
            if selected_category and selected_category != detected_category:
                category_switched = True
                original_category = selected_category
                logger.info(f"Category switch: selected={selected_category}, detected={detected_category}")

            # Always use AI-detected category (AI decision wins)
            category_used = detected_category

            # Step 2: Fetch data for each product (parallel)
            product_data = await asyncio.gather(
                self._fetch_product_data(products[0], region, include_specs, include_reviews, nocache),
                self._fetch_product_data(products[1], region, include_specs, include_reviews, nocache)
            )
            
            # Fetch behavioral profile if user is logged in
            behavior_profile = None
            if user_id:
                behavior_profile = await self._fetch_behavior_profile(user_id)

            # Step 3: Compute deterministic scores (pure math, $0 cost)
            scoring_service = get_scoring_service()
            scoring_result = scoring_service.compute_scores(
                product_data,
                preferences=user_preferences,
                behavior_profile=behavior_profile,
            )
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in product_data
            ]
            scores_summary = scoring_service.build_scores_summary(
                scoring_result, product_names
            )

            # Step 4: Generate comparison (includes pros/cons to save a GPT call)
            comparison, usage = await generate_comparison(
                product_data[0],
                product_data[1],
                region,
                parsed.get("comparison_type", "value") if not vision_products else "value",
                user_preferences=user_preferences,
                scores_summary=scores_summary,
                category=detected_category,
            )
            self._track_gpt_cost(usage)

            # Trust validation: cross-check GPT claims against scores
            from app.services.trust_validation_service import validate_verdict
            verdict_validation = validate_verdict(comparison, scoring_result, detected_category)

            # Extract pros/cons from comparison result into product data
            if include_pros_cons:
                product_data[0]["pros_cons"] = {
                    "pros": comparison.pop("product_0_pros", []),
                    "cons": comparison.pop("product_0_cons", []),
                }
                product_data[1]["pros_cons"] = {
                    "pros": comparison.pop("product_1_pros", []),
                    "cons": comparison.pop("product_1_cons", []),
                }

            # Compute value badges per product
            for i, product in enumerate(product_data):
                value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
                price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
                product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)

            # Compute tradeoff pairs
            tradeoffs = scoring_service.compute_tradeoff_pairs(
                scoring_result.get("dimension_winners", {}), product_names, scoring_result.get("winner_index", 0)
            )

            # Compute confidence
            from_cache = not nocache  # simplified: if nocache=False, data may be cached
            confidence = scoring_service.compute_confidence(
                product_data, shopping_count=len(self._shopping_items_cache), cached=from_cache
            )

            # Calculate timing
            elapsed = (datetime.now() - start_time).total_seconds()

            # Build personalization metadata
            personalized = user_preferences is not None and bool(user_preferences)
            personalization_factors = []
            if personalized:
                for p in user_preferences.get("priorities", []):
                    personalization_factors.append(f"priority_{p}")
                if user_preferences.get("budget"):
                    personalization_factors.append(f"budget_{user_preferences['budget']}")
                for tag in user_preferences.get("lifestyle", []):
                    personalization_factors.append(f"lifestyle_{tag}")

            # Detect price method mismatch (different price sourcing methods across products)
            price_methods = [p.get("price", {}).get("source_method") for p in product_data if p.get("price")]
            unique_methods = set(m for m in price_methods if m)

            # Derive ratings for products with no real ratings
            for i, pd_item in enumerate(product_data):
                if pd_item.get("rating") is None:
                    key = f"product_{i}"
                    overall = scoring_result.get("scores", {}).get(key, {}).get("overall", MISSING_SCORE)
                    pd_item["rating"] = self._derive_rating_from_scores(overall)
                    pd_item["rating_derived"] = True

            # Build new structured response
            winner_index = comparison.get("winner_index", 0)
            win_margin = scoring_result.get("win_margin", 0)

            result = {
                "success": True,
                "query": query,
                "category": category_used,
                "category_switched": category_switched,
                "original_category": original_category,

                "overview": {
                    "winner": {
                        "product_index": winner_index,
                        "name": comparison.get("winner_declaration", product_names[winner_index] if product_names else ""),
                        "declaration": comparison.get("winner_declaration", ""),
                        "reason": comparison.get("winner_reason", ""),
                        "key_tradeoff": comparison.get("key_tradeoff", ""),
                        "margin": win_margin,
                    },
                    "products": [
                        {
                            "brand": pd.get("brand"),
                            "name": pd.get("name"),
                            "price": pd.get("price"),
                            "rating": pd.get("rating"),
                            "review_count": pd.get("review_count"),
                            "overall_score": scoring_result.get("scores", {}).get(f"product_{i}", {}).get("overall"),
                            "value_badge": pd.get("value_badge", "fair_price"),
                            "value_context": comparison.get("value_context", ""),
                            "pros": pd.get("pros_cons", {}).get("pros", []),
                            "cons": pd.get("pros_cons", {}).get("cons", []),
                            "best_for": comparison.get("best_for", {}).get(f"product_{i}", ""),
                        }
                        for i, pd in enumerate(product_data)
                    ],
                    "tradeoffs": tradeoffs,
                    "confidence": confidence,
                },

                "specs": {
                    "products": [
                        {
                            "brand": pd.get("brand"),
                            "name": pd.get("name"),
                            "specs": pd.get("specs"),
                            "spec_advantages": comparison.get("specs_comparison", {}).get(f"product_{i}_advantages", []),
                        }
                        for i, pd in enumerate(product_data)
                    ],
                    "specs_comparison": comparison.get("specs_comparison", {}),
                },

                "reviews": {
                    "products": [
                        {
                            "brand": pd.get("brand"),
                            "name": pd.get("name"),
                            "rating": pd.get("rating"),
                            "review_count": pd.get("review_count"),
                            "rating_source": pd.get("rating_source"),
                            "review_summary": pd.get("reviews", {}).get("review_summary", {
                                "overall_sentiment": "mixed",
                                "consensus": "",
                                "highlights": [],
                                "review_volume": "minimal",
                                "agreement_level": "moderate",
                            }),
                        }
                        for pd in product_data
                    ],
                },

                "scoring": {
                    "scores": scoring_result.get("scores", {}),
                    "dimension_winners": scoring_result.get("dimension_winners", {}),
                    "price_tiers": scoring_result.get("price_tiers", {}),
                    "is_cross_tier": scoring_result.get("is_cross_tier", False),
                    "scoring_method": scoring_result.get("scoring_method", "category_weighted"),
                    "category_weights": scoring_result.get("category_weights", {}),
                },

                "personalization": {
                    "personalized": personalized,
                    "factors": personalization_factors,
                    "personalized_insights": comparison.get("personalized_insights", []),
                },

                "metadata": {
                    "query": query,
                    "region": region,
                    "elapsed_ms": round(elapsed * 1000),
                    "elapsed_seconds": round(elapsed, 2),
                    "api_calls": self.api_calls,
                    "total_cost": round(self.total_cost, 6),
                    "gpt_calls": self.gpt_calls,
                    "serper_calls": self.serper_calls,
                    "cached": from_cache,
                    "fact_check": {
                        "product_0": product_data[0].get("fact_check", {}),
                        "product_1": product_data[1].get("fact_check", {}),
                    },
                    "verdict_validation": verdict_validation,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            # Backward compatibility aliases for old stored comparisons in history
            result["products"] = product_data
            result["comparison"] = comparison
            result["recommendation"] = comparison.get("winner_reason", "")
            result["key_differences"] = []
            result["winner_index"] = winner_index
            result["category_used"] = category_used
            result["personalized"] = personalized
            result["personalization_factors"] = personalization_factors
            result["personalized_insights"] = comparison.get("personalized_insights", [])
            result["price_method_mismatch"] = len(unique_methods) > 1
            result["tier_context"] = {
                "price_tiers": scoring_result.get("price_tiers", {}),
                "is_cross_tier": scoring_result.get("is_cross_tier", False),
            }

            # Fire-and-forget: update behavioral profile after comparison
            if user_id:
                asyncio.create_task(self._update_behavior_profile(user_id))

            return result

        except Exception as e:
            logger.error(f"Comparison error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "total_cost": self.total_cost
            }

    async def compare_from_text_streaming(
        self,
        query: str,
        region: str = "bahrain",
        include_specs: bool = True,
        include_reviews: bool = True,
        include_pros_cons: bool = True,
        nocache: bool = False,
        selected_category: Optional[str] = None,
        vision_products: Optional[List[Dict]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        """
        Async generator version of compare_from_text that yields partial results.
        Each yield is a (event_type, data) tuple for SSE streaming.
        """
        start_time = datetime.now()
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}

        try:
            # Step 1: Parse the query
            yield ("status", {"message": "Parsing query...", "progress": 10})

            if vision_products and len(vision_products) >= 2:
                products = []
                for vp in vision_products[:2]:
                    brand = vp.get("brand", "Unknown")
                    vname = vp.get("name", "Unknown Product")
                    full = f"{brand} {vname}".strip()
                    category = "supplements" if self._is_supplement_query(full) else "other"
                    products.append({
                        "brand": brand,
                        "name": vname,
                        "variant": vp.get("size_or_count"),
                        "category": category,
                        "search_query": full,
                        "_vision": True,
                    })
                parsed = {}
            else:
                parsed, usage = await parse_product_query(query)
                self._track_gpt_cost(usage)

                if not parsed.get("products") or len(parsed["products"]) < 2:
                    yield ("error", {
                        "success": False,
                        "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'",
                        "parsed": parsed,
                    })
                    return

                products = parsed["products"][:2]

            # Determine category
            detected_category = products[0].get("category", "other")
            category_switched = False
            original_category = None
            if selected_category and selected_category != detected_category:
                category_switched = True
                original_category = selected_category
            category_used = detected_category

            # Step 2: Fetch product data (Phase 1 + Phase 2 inside _fetch_product_data)
            yield ("status", {"message": "Fetching specs and prices...", "progress": 20})

            product_data = await asyncio.gather(
                self._fetch_product_data(products[0], region, include_specs, include_reviews, nocache),
                self._fetch_product_data(products[1], region, include_specs, include_reviews, nocache),
            )

            # Yield specs (wrapped in specs section format)
            yield ("specs", {
                "products": [
                    {
                        "brand": pd.get("brand"),
                        "name": pd.get("name"),
                        "specs": pd.get("specs"),
                        "fact_check": pd.get("fact_check"),
                    }
                    for pd in product_data
                ]
            })

            # Yield prices with value badges
            scoring_service = get_scoring_service()
            prices_payload = {}
            for i, pd in enumerate(product_data):
                key = f"product_{i}"
                # Compute value badge early for streaming
                value_score = 50  # placeholder until scores computed
                price_tier = "mid"
                prices_payload[key] = {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "price": pd.get("price"),
                    "best_price": pd.get("best_price"),
                    "currency": pd.get("currency"),
                    "retailer": pd.get("retailer"),
                }
            yield ("prices", prices_payload)

            # Yield reviews with review_summary format
            yield ("status", {"message": "Analyzing reviews...", "progress": 50})
            yield ("reviews", {
                "products": [
                    {
                        "brand": pd.get("brand"),
                        "name": pd.get("name"),
                        "rating": pd.get("rating"),
                        "review_count": pd.get("review_count"),
                        "rating_verified": pd.get("rating_verified"),
                        "rating_source": pd.get("rating_source"),
                        "review_summary": pd.get("reviews", {}).get("review_summary", {
                            "overall_sentiment": "mixed",
                            "consensus": "",
                            "highlights": [],
                            "review_volume": "minimal",
                            "agreement_level": "moderate",
                        }),
                    }
                    for pd in product_data
                ]
            })

            # Fetch behavioral profile if user is logged in
            behavior_profile = None
            if user_id:
                behavior_profile = await self._fetch_behavior_profile(user_id)

            # Step 3: Compute scores (instant, $0)
            scoring_result = scoring_service.compute_scores(
                product_data,
                preferences=user_preferences,
                behavior_profile=behavior_profile,
            )
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in product_data
            ]
            scores_summary = scoring_service.build_scores_summary(
                scoring_result, product_names
            )

            # Compute confidence for scores event
            from_cache = not nocache
            confidence = scoring_service.compute_confidence(
                product_data, shopping_count=len(self._shopping_items_cache), cached=from_cache
            )
            yield ("scores", {
                "scores": scoring_result.get("scores", {}),
                "dimension_winners": scoring_result.get("dimension_winners", {}),
                "winner_index": scoring_result.get("winner_index", 0),
                "win_margin": scoring_result.get("win_margin", 0),
                "confidence": confidence,
            })

            # Step 4: Generate verdict
            yield ("status", {"message": "Generating verdict...", "progress": 80})
            comparison, usage = await generate_comparison(
                product_data[0],
                product_data[1],
                region,
                parsed.get("comparison_type", "value") if not vision_products else "value",
                user_preferences=user_preferences,
                scores_summary=scores_summary,
                category=detected_category,
            )
            self._track_gpt_cost(usage)

            # Trust validation: cross-check GPT claims against scores
            from app.services.trust_validation_service import validate_verdict
            verdict_validation = validate_verdict(comparison, scoring_result, detected_category)

            if include_pros_cons:
                product_data[0]["pros_cons"] = {
                    "pros": comparison.pop("product_0_pros", []),
                    "cons": comparison.pop("product_0_cons", []),
                }
                product_data[1]["pros_cons"] = {
                    "pros": comparison.pop("product_1_pros", []),
                    "cons": comparison.pop("product_1_cons", []),
                }

            # Compute value badges per product
            for i, product in enumerate(product_data):
                value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
                price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
                product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)

            # Compute tradeoff pairs
            tradeoffs = scoring_service.compute_tradeoff_pairs(
                scoring_result.get("dimension_winners", {}), product_names, scoring_result.get("winner_index", 0)
            )

            winner_index = comparison.get("winner_index", 0)
            win_margin = scoring_result.get("win_margin", 0)

            yield ("verdict", {
                "winner": {
                    "product_index": winner_index,
                    "name": comparison.get("winner_declaration", product_names[winner_index] if product_names else ""),
                    "reason": comparison.get("winner_reason", ""),
                    "key_tradeoff": comparison.get("key_tradeoff", ""),
                    "margin": win_margin,
                },
                "value_context": comparison.get("value_context", ""),
                "best_for": comparison.get("best_for", {}),
                "personalized_insights": comparison.get("personalized_insights", []),
                # Backward compat
                "comparison": comparison,
                "winner_index": winner_index,
                "recommendation": comparison.get("winner_reason", ""),
                "key_differences": [],
            })

            # Step 5: Build complete response
            elapsed = (datetime.now() - start_time).total_seconds()
            personalized = user_preferences is not None and bool(user_preferences)
            personalization_factors = []
            if personalized:
                for p in user_preferences.get("priorities", []):
                    personalization_factors.append(f"priority_{p}")
                if user_preferences.get("budget"):
                    personalization_factors.append(f"budget_{user_preferences['budget']}")
                for tag in user_preferences.get("lifestyle", []):
                    personalization_factors.append(f"lifestyle_{tag}")

            # Derive ratings for products with no real ratings
            for i, pd_item in enumerate(product_data):
                if pd_item.get("rating") is None:
                    key = f"product_{i}"
                    overall = scoring_result.get("scores", {}).get(key, {}).get("overall", MISSING_SCORE)
                    pd_item["rating"] = self._derive_rating_from_scores(overall)
                    pd_item["rating_derived"] = True

            complete_response = {
                "success": True,
                "query": query,
                "category": category_used,
                "category_switched": category_switched,
                "original_category": original_category,

                "overview": {
                    "winner": {
                        "product_index": winner_index,
                        "name": comparison.get("winner_declaration", product_names[winner_index] if product_names else ""),
                        "declaration": comparison.get("winner_declaration", ""),
                        "reason": comparison.get("winner_reason", ""),
                        "key_tradeoff": comparison.get("key_tradeoff", ""),
                        "margin": win_margin,
                    },
                    "products": [
                        {
                            "brand": pd.get("brand"),
                            "name": pd.get("name"),
                            "price": pd.get("price"),
                            "rating": pd.get("rating"),
                            "review_count": pd.get("review_count"),
                            "overall_score": scoring_result.get("scores", {}).get(f"product_{i}", {}).get("overall"),
                            "value_badge": pd.get("value_badge", "fair_price"),
                            "value_context": comparison.get("value_context", ""),
                            "pros": pd.get("pros_cons", {}).get("pros", []),
                            "cons": pd.get("pros_cons", {}).get("cons", []),
                            "best_for": comparison.get("best_for", {}).get(f"product_{i}", ""),
                        }
                        for i, pd in enumerate(product_data)
                    ],
                    "tradeoffs": tradeoffs,
                    "confidence": confidence,
                },

                "specs": {
                    "products": [
                        {
                            "brand": pd.get("brand"),
                            "name": pd.get("name"),
                            "specs": pd.get("specs"),
                            "spec_advantages": comparison.get("specs_comparison", {}).get(f"product_{i}_advantages", []),
                        }
                        for i, pd in enumerate(product_data)
                    ],
                    "specs_comparison": comparison.get("specs_comparison", {}),
                },

                "reviews": {
                    "products": [
                        {
                            "brand": pd.get("brand"),
                            "name": pd.get("name"),
                            "rating": pd.get("rating"),
                            "review_count": pd.get("review_count"),
                            "rating_source": pd.get("rating_source"),
                            "review_summary": pd.get("reviews", {}).get("review_summary", {
                                "overall_sentiment": "mixed",
                                "consensus": "",
                                "highlights": [],
                                "review_volume": "minimal",
                                "agreement_level": "moderate",
                            }),
                        }
                        for pd in product_data
                    ],
                },

                "scoring": {
                    "scores": scoring_result.get("scores", {}),
                    "dimension_winners": scoring_result.get("dimension_winners", {}),
                    "price_tiers": scoring_result.get("price_tiers", {}),
                    "is_cross_tier": scoring_result.get("is_cross_tier", False),
                    "scoring_method": scoring_result.get("scoring_method", "category_weighted"),
                    "category_weights": scoring_result.get("category_weights", {}),
                },

                "personalization": {
                    "personalized": personalized,
                    "factors": personalization_factors,
                    "personalized_insights": comparison.get("personalized_insights", []),
                },

                "metadata": {
                    "query": query,
                    "region": region,
                    "elapsed_ms": round(elapsed * 1000),
                    "elapsed_seconds": round(elapsed, 2),
                    "api_calls": self.api_calls,
                    "total_cost": round(self.total_cost, 6),
                    "gpt_calls": self.gpt_calls,
                    "serper_calls": self.serper_calls,
                    "cached": from_cache,
                    "fact_check": {
                        "product_0": product_data[0].get("fact_check", {}),
                        "product_1": product_data[1].get("fact_check", {}),
                    },
                    "verdict_validation": verdict_validation,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            # Backward compatibility aliases
            complete_response["products"] = product_data
            complete_response["comparison"] = comparison
            complete_response["recommendation"] = comparison.get("winner_reason", "")
            complete_response["key_differences"] = []
            complete_response["winner_index"] = winner_index
            complete_response["category_used"] = category_used
            complete_response["personalized"] = personalized
            complete_response["personalization_factors"] = personalization_factors
            complete_response["personalized_insights"] = comparison.get("personalized_insights", [])
            complete_response["tier_context"] = {
                "price_tiers": scoring_result.get("price_tiers", {}),
                "is_cross_tier": scoring_result.get("is_cross_tier", False),
            }

            # Fire-and-forget: update behavioral profile after comparison
            if user_id:
                asyncio.create_task(self._update_behavior_profile(user_id))

            yield ("complete", complete_response)

        except Exception as e:
            logger.error(f"Streaming comparison error: {e}", exc_info=True)
            yield ("error", {
                "success": False,
                "error": str(e),
                "total_cost": self.total_cost,
            })

    async def _fetch_behavior_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user's behavioral profile from Supabase."""
        try:
            from app.services.database_service import get_supabase_client
            supabase = get_supabase_client()
            result = supabase.table("users").select("behavior_profile").eq("id", user_id).single().execute()
            if result.data and result.data.get("behavior_profile"):
                return result.data["behavior_profile"]
        except Exception as e:
            logger.debug(f"Failed to fetch behavior profile: {e}")
        return None

    async def _update_behavior_profile(self, user_id: str):
        """Fire-and-forget: update user's behavioral profile after comparison."""
        try:
            from app.services.behavior_service import get_behavior_service
            from app.services.database_service import get_supabase_client

            behavior_service = get_behavior_service()
            supabase = get_supabase_client()

            # Fetch user's comparison history, feedback, and events
            comparisons = supabase.table("comparisons").select("category_used, products, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
            feedback = supabase.table("comparison_feedback").select("useful").eq("user_id", user_id).execute()
            events = supabase.table("user_events").select("event_type, metadata").eq("user_id", user_id).order("created_at", desc=True).limit(200).execute()

            profile = await behavior_service.build_behavior_profile(
                comparisons.data or [],
                feedback.data or [],
                events.data or [],
            )

            # Upsert profile
            supabase.table("users").update({"behavior_profile": profile}).eq("id", user_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update behavior profile: {e}")

    async def _fetch_product_data(
        self,
        product_info: Dict,
        region: str,
        include_specs: bool,
        include_reviews: bool,
        nocache: bool = False
    ) -> Dict[str, Any]:
        """Fetch all data for a single product."""
        brand = product_info.get("brand", "")
        name = product_info.get("name", "")
        variant = product_info.get("variant")
        category = product_info.get("category", "other")
        search_query = product_info.get("search_query", f"{brand} {name} {variant or ''}")
        is_vision = product_info.get("_vision", False)

        if is_vision:
            # Vision path: name=product name, variant=same (for GPT hint)
            # full_name = "Brand ProductName" (no doubling with variant)
            full_name = search_query  # already "Brand ProductName"
            display_name = full_name  # include brand for frontend display
        else:
            full_name = f"{brand} {name} {variant or ''}".strip()
            display_name = name

        result = {
            "brand": brand,
            "name": display_name,
            "full_name": full_name,
            "variant": variant,
            "category": category,
            "query": search_query,
        }

        # === Unified web search (one Serper call for both specs + reviews) ===
        # Saves $0.001/product vs separate searches per function
        unified_search = None
        if include_specs or include_reviews:
            specs_key = get_specs_cache_key(brand, name, variant)
            reviews_key = get_reviews_cache_key(brand, name, variant)
            specs_hit = get_cached(specs_key) if not nocache else None
            reviews_hit = get_cached(reviews_key) if not nocache else None
            if (include_specs and not specs_hit) or (include_reviews and not reviews_hit):
                unified_search = await search_web(
                    f"{search_query} specifications reviews price",
                    num_results=10
                )
                self._track_serper_cost()

        # === Phase 1: specs + price (parallel) ===
        # Price must run first so _shopping_items_cache is populated for reviews
        phase1_tasks = []
        phase1_keys = []

        # Drug database lookup for supplements (enriches GPT prompt with official data)
        drug_context = ""
        if include_specs and category == "supplements":
            try:
                drugs = await find_matching_drugs(search_query, limit=5)
                drug_context = format_drug_context(drugs)
                if drug_context:
                    logger.info(f"Drug DB: found {len(drugs)} matches for '{search_query}'")
            except Exception as e:
                logger.warning(f"Drug DB lookup failed: {e}")

        if include_specs:
            phase1_tasks.append(self._get_specs(brand, name, variant, category, search_query, nocache, search_results=unified_search, drug_context=drug_context))
            phase1_keys.append("specs")

        phase1_tasks.append(self._get_price(brand, name, variant, region, search_query, nocache, category))
        phase1_keys.append("price")

        phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

        for i, key in enumerate(phase1_keys):
            if isinstance(phase1_results[i], Exception):
                logger.error(f"Error fetching {key}: {phase1_results[i]}")
                result[key] = None
            else:
                result[key] = phase1_results[i]

        # Extract best price
        if result.get("price"):
            result["best_price"] = result["price"].get("amount")
            result["currency"] = result["price"].get("currency", "BHD")
            result["retailer"] = result["price"].get("retailer")

        # Fact-check: verify spec citations before cleaning
        if result.get("specs") and isinstance(result["specs"], dict):
            raw_specs = result["specs"]
            search_snippets = raw_specs.pop("_search_snippets", [])

            # Citation verification: check GPT's _source claims against snippet text
            citation_confidence = self._verify_spec_citations(raw_specs, search_snippets)

            # Cross-validate against shopping data (upgrades 'likely' → 'verified')
            shopping_items = self._shopping_items_cache.get(full_name, [])
            shopping_flags = self._cross_validate_specs_with_shopping(raw_specs, shopping_items)

            # Merge: shopping verification can upgrade citation confidence
            spec_confidence = {}
            for key in citation_confidence:
                if shopping_flags.get(key) == "verified":
                    spec_confidence[key] = "verified"
                else:
                    spec_confidence[key] = citation_confidence[key]

            result["_spec_confidence"] = spec_confidence

        # Clean specs: remove meta keys, _source fields, flatten additional_specs
        if result.get("specs"):
            result["specs"] = self._clean_specs(result["specs"])

        # === Phase 2: reviews + verified rating (parallel) ===
        # Reviews can now use retailer ratings from shopping data
        retailer_ratings = self._collect_retailer_ratings(full_name)

        phase2_tasks = []
        phase2_keys = []

        if include_reviews:
            phase2_tasks.append(self._get_reviews(
                brand, name, variant, search_query, nocache,
                category=category, retailer_ratings=retailer_ratings,
                search_results=unified_search
            ))
            phase2_keys.append("reviews")

        phase2_tasks.append(self._get_verified_rating(full_name))
        phase2_keys.append("_rating_data")

        phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)

        rating_data = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}
        for i, key in enumerate(phase2_keys):
            if isinstance(phase2_results[i], Exception):
                logger.error(f"Error fetching {key}: {phase2_results[i]}")
                if key != "_rating_data":
                    result[key] = None
            else:
                if key == "_rating_data":
                    rating_data = phase2_results[i]
                else:
                    result[key] = phase2_results[i]

        result["rating"] = rating_data.get("rating")
        result["review_count"] = rating_data.get("review_count")
        result["rating_verified"] = rating_data.get("rating_verified", False)
        result["rating_source"] = rating_data.get("rating_source")

        # Fallback: if no shopping rating found, use GPT-extracted average_rating from reviews (unverified)
        if result["rating"] is None and result.get("reviews") and isinstance(result["reviews"], dict):
            avg = result["reviews"].get("average_rating")
            if avg is not None:
                try:
                    avg_float = round(float(avg), 1)
                    if 1.0 <= avg_float <= 5.0:
                        result["rating"] = avg_float
                        result["review_count"] = result["reviews"].get("total_reviews")
                        result["rating_verified"] = False
                        result["rating_source"] = {
                            "name": "Aggregated from reviews",
                            "url": None,
                            "extract_method": "gpt_review_aggregate",
                            "confidence": "low",
                        }
                        logger.info(f"[RATING] Fallback to GPT review average: {avg_float} for {full_name}")
                except (ValueError, TypeError):
                    pass

        # Inject verified rating into reviews so frontend has a single source of truth
        if result.get("reviews") and isinstance(result["reviews"], dict) and rating_data.get("rating"):
            result["reviews"]["verified_rating"] = {
                "rating": rating_data["rating"],
                "review_count": rating_data.get("review_count"),
                "source": rating_data.get("rating_source", {}).get("name"),
                "verified": rating_data.get("rating_verified", False),
            }

        # Pass through expert pros/cons if available (from Tier 0 review scrape)
        if rating_data.get("expert_pros"):
            result["expert_pros"] = rating_data["expert_pros"]
        if rating_data.get("expert_cons"):
            result["expert_cons"] = rating_data["expert_cons"]

        # === Fact-checking: review sentiment + price verification ===
        # Review sentiment cross-validation (GPT vs Serper ratings)
        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["_review_verification"] = self._verify_review_sentiment(
                result["reviews"], retailer_ratings
            )
        else:
            result["_review_verification"] = {"sentiment_consistent": None, "gpt_rating": None, "serper_avg_rating": None, "deviation": None}

        # Price cross-check against shopping data
        shopping_items = self._shopping_items_cache.get(full_name, [])
        result["_price_verification"] = self._verify_price(
            result.get("price"), shopping_items
        )

        # Clean review content (garbage text, short items, misclassified sentiments)
        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["reviews"] = self._clean_review_content(result["reviews"])

        # Clean review citations for display (replace [snippet_N] with source domain)
        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["reviews"] = self._clean_review_citations(
                result["reviews"],
                unified_search.get("organic", []) if unified_search else []
            )

        # Assemble fact_check object (pops internal _spec_confidence, _review_verification, _price_verification)
        result["fact_check"] = self._build_fact_check(result)

        # Calculate data freshness
        result["data_freshness"] = self._calculate_freshness(result)

        return result
    
    async def _get_specs(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        category: str,
        search_query: str,
        nocache: bool = False,
        search_results: Optional[Dict] = None,
        drug_context: str = ""
    ) -> Dict[str, Any]:
        """Get specs with caching. Uses pre-fetched search_results if provided."""
        cache_key = get_specs_cache_key(brand, name, variant)

        # Check cache
        cached = get_cached(cache_key) if not nocache else None
        if cached:
            logger.info(f"Specs cache hit: {cache_key}")
            cached["_cached"] = True
            return cached

        # Fetch from search (reuse unified search if available)
        logger.info(f"Fetching specs for: {brand} {name}")
        if search_results is None:
            search_results = await search_web(f"{search_query} specifications features")
            self._track_serper_cost()

        # Use numbered snippets for citation tracking
        search_context, raw_snippets = self._format_numbered_search_results(search_results)

        # Extract specs
        specs, usage = await extract_specs(brand, name, variant, category, search_context, drug_context=drug_context)
        self._track_gpt_cost(usage)

        # Cache result (without internal _search_snippets)
        if specs and not specs.get("error"):
            set_cached(cache_key, specs, SPECS_CACHE_TTL)

        # Attach raw snippets for fact-check verification (stripped before response)
        specs["_search_snippets"] = raw_snippets
        specs["_cached"] = False
        return specs
    
    async def _get_price(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        region: str,
        search_query: str,
        nocache: bool = False,
        category: str = "other"
    ) -> Dict[str, Any]:
        """
        Get price with 3-tier strategy to guarantee a price:
        1. Direct Serper Shopping extraction (structured data, most accurate)
        2. GPT extraction from search results text
        3. GPT training data fallback (estimated, confidence 0.5)
        """
        # Gate 0: Input validation
        if not self._validate_price_query(brand, name, region):
            return {
                "amount": 0, "currency": "BHD", "estimated": True,
                "source_method": "validation_rejected",
            }

        cache_key = get_price_cache_key(brand, name, variant, region)

        # Check cache
        cached = get_cached(cache_key) if not nocache else None
        if cached:
            logger.info(f"Price cache hit: {cache_key}")
            cached["_cached"] = True
            return cached

        region_info = GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])
        currency = region_info["currency"]
        # Avoid doubling variant — for vision products, name already includes size_or_count
        # e.g., name="high potency vitamin d-3 360 Softgels", variant="360 Softgels"
        if variant and variant.lower() in name.lower():
            full_name = f"{brand} {name}".strip()
        else:
            full_name = f"{brand} {name} {variant or ''}".strip()
        logger.info(f"Fetching price for: {full_name} in {region}")

        # Detect supplement early — used by Opts A/B/C to skip wasteful calls
        # Use GPT category as primary signal, keyword matching as backup
        is_supplement = (category == "supplements") or self._is_supplement_query(full_name)

        # --- Tier 1: Direct Serper Shopping extraction ---
        if is_supplement:
            # Opt A: BH shopping always returns 0 for supplements — skip the $0.001 call
            logger.info(f"[PRICE] Supplement detected, skipping BH shopping for {full_name}")
            search_results = {"shopping": [], "organic": []}
            shopping_items = []
            self._shopping_items_cache[full_name] = []
        else:
            # Fetch shopping results from Serper (organic deferred to Tier 2 if needed)
            search_results = await search_product_prices(search_query, region_info["code"])
            self._track_serper_cost()
            shopping_items = search_results.get("shopping", [])
            # Store for reuse by rating extraction (avoids duplicate API call)
            self._shopping_items_cache[full_name] = shopping_items

        # Cached Tier 3 estimate — reused across sanity checks and final fallback
        tier3_estimate = None

        price = self._extract_price_from_shopping(full_name, shopping_items, currency)
        if price and price.get("amount"):
            # Official domain prices (retailer_score >= 1.0) skip sanity check entirely
            if price.get("retailer_score", 0) >= 1.0:
                logger.info(f"[PRICE] Official domain price ({price.get('retailer')}) — skipping sanity check")
            elif (self._is_high_value_query(full_name) or self._is_luxury_brand(full_name)) and price.get("retailer_score", 0) < 1.0:
                # Luxury brands get tighter thresholds (less tolerance for outliers)
                if self._is_luxury_brand(full_name):
                    high_threshold = 1.8
                    low_threshold = 0.6
                else:
                    high_threshold = 2.0
                    low_threshold = 0.5
                tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
                self._track_gpt_cost(usage)
                self._sanitize_gpt_price(tier3_estimate)
                self._convert_gpt_price_currency(tier3_estimate, currency)
                if tier3_estimate and tier3_estimate.get("amount"):
                    tier1_bhd = _convert_to_bhd(price["amount"], currency)
                    tier3_bhd = _convert_to_bhd(tier3_estimate["amount"], currency)
                    if tier1_bhd > tier3_bhd * high_threshold:
                        logger.info(
                            f"[PRICE] Tier 1 too HIGH: {currency} {price['amount']} from {price.get('retailer')} "
                            f"vs estimate {currency} {tier3_estimate['amount']} (threshold {high_threshold}x) — falling through"
                        )
                        price = None
                    elif tier1_bhd < tier3_bhd * low_threshold:
                        logger.info(
                            f"[PRICE] Tier 1 too LOW: {currency} {price['amount']} from {price.get('retailer')} "
                            f"vs estimate {currency} {tier3_estimate['amount']} (threshold {low_threshold}x) — falling through"
                        )
                        price = None
            if price and price.get("amount"):
                logger.info(f"[PRICE] Tier 1 (Shopping): {currency} {price['amount']} from {price.get('retailer')}")
                price.pop("retailer_score", None)  # Clean internal field before cache/return
                set_cached(cache_key, price, PRICE_CACHE_TTL)
                price["_cached"] = False
                return price

        # --- Tier 1.5: Page scraping cascade (luxury brands only) ---
        if not price and self._is_luxury_brand(full_name) and ENABLE_PAGE_SCRAPE:
            tier15_start = time.monotonic()
            tier15_budget = self.TIER_15_BUDGET_TIMEOUT
            failed_curl_urls = []  # URLs where curl got HTML but no price — Scrape.do candidates

            # --- Tier 1.5a: Official brand site ---
            official_domain = self._get_official_domain(full_name)
            if official_domain:
                logger.info(f"[PRICE] Tier 1.5a: trying official domain {official_domain}")
                try:
                    official_results = await search_web(f"{full_name} site:{official_domain}")
                    self.api_calls += 1
                    self._track_cost(0.001)
                    if official_results and official_results.get("organic"):
                        for organic_item in official_results["organic"][:2]:
                            page_url = organic_item.get("link")
                            if not page_url or not self._validate_scrape_url(page_url):
                                continue

                            # Try Firecrawl first (Smart Wait catches XHR-loaded prices)
                            if firecrawl_service.is_available() and is_circuit_closed("firecrawl") and has_budget("firecrawl"):
                                html, status = await firecrawl_service.scrape_page_with_status(page_url)
                                # Always count usage if we got a 200 (API credit was spent)
                                if status == 200:
                                    record_usage("firecrawl")
                                if html:
                                    record_success("firecrawl")
                                    price = self._extract_price_from_html(html, full_name, currency, official_domain, page_url)
                                    if price:
                                        price["source_method"] = "firecrawl"
                                        price["retailer"] = official_domain
                                        logger.info(f"[PRICE] Tier 1.5a: Firecrawl price {currency} {price['amount']} from {official_domain}")
                                        set_cached(cache_key, price, PRICE_CACHE_TTL)
                                        price["_cached"] = False
                                        return price
                                elif status in (429, 503) or status == 0:
                                    record_failure("firecrawl")
                                # If Firecrawl got 200 but no price, that's NOT a circuit failure — continue

                            # Fallback: curl_cffi for non-SPA official sites
                            page_price = await self._fetch_page_price(page_url, full_name, currency)
                            if page_price and page_price.get("amount"):
                                page_price.pop("_got_html", None)  # Clean up internal marker
                                page_price["retailer"] = official_domain
                                logger.info(f"[PRICE] Tier 1.5a: official price {currency} {page_price['amount']} from {official_domain}")
                                set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                                page_price["_cached"] = False
                                return page_price
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5a failed: {e}")

            # Check budget before Tier 1.5b
            elapsed = time.monotonic() - tier15_start
            if elapsed >= tier15_budget:
                logger.info(f"[PRICE] Tier 1.5 budget exhausted ({elapsed:.1f}s), skipping to Tier 2")
            else:
                # --- Tier 1.5b: Authorized luxury retailers ---
                logger.info(f"[PRICE] Tier 1.5b: trying authorized retailers")
                try:
                    # Use brand name + retailer names (avoids long site: OR chains)
                    retailer_query = f"{full_name} farfetch OR ssense OR net-a-porter"
                    retailer_results = await search_web(retailer_query)
                    self.api_calls += 1
                    self._track_cost(0.001)
                    if retailer_results and retailer_results.get("organic"):
                        # Filter to only authorized retailer domains
                        retailer_urls = []
                        for item in retailer_results["organic"][:5]:
                            link = item.get("link", "")
                            link_domain = urlparse(link).netloc.replace("www.", "")
                            if link_domain in self.AUTHORIZED_LUXURY_RETAILERS or link_domain in self.OFFICIAL_BRAND_DOMAINS:
                                retailer_urls.append((link, link_domain))

                        if retailer_urls:
                            # Fetch top 3 in parallel
                            fetch_tasks = [
                                self._fetch_page_price(url, full_name, currency)
                                for url, _ in retailer_urls[:3]
                            ]
                            page_prices = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                            # Collect valid prices
                            valid_prices = []
                            for i, pp in enumerate(page_prices):
                                if isinstance(pp, dict) and pp.get("amount"):
                                    pp["_retailer_domain"] = retailer_urls[i][1]
                                    valid_prices.append(pp)
                                elif isinstance(pp, dict) and pp.get("_got_html"):
                                    # curl_cffi got HTML but no price — JS render may help
                                    failed_curl_urls.append(retailer_urls[i][0])
                                # If pp is None (curl failed) or Exception → NOT a Scrape.do candidate

                            if len(valid_prices) >= 2:
                                # Cross-validate: max/min <= 1.15
                                amounts = [p["amount"] for p in valid_prices]
                                if max(amounts) / min(amounts) <= 1.15:
                                    # Prices agree — use lowest
                                    best = min(valid_prices, key=lambda p: p["amount"])
                                    logger.info(f"[PRICE] Tier 1.5b: cross-validated price {currency} {best['amount']} ({len(valid_prices)} sources agree)")
                                    best.pop("_retailer_domain", None)
                                    set_cached(cache_key, best, PRICE_CACHE_TTL)
                                    best["_cached"] = False
                                    return best
                                else:
                                    # Prices diverge — use the one from highest-tier retailer
                                    best = valid_prices[0]
                                    logger.info(f"[PRICE] Tier 1.5b: single retailer price {currency} {best['amount']} (prices diverged)")
                                    best.pop("_retailer_domain", None)
                                    set_cached(cache_key, best, PRICE_CACHE_TTL)
                                    best["_cached"] = False
                                    return best
                            elif len(valid_prices) == 1:
                                best = valid_prices[0]
                                logger.info(f"[PRICE] Tier 1.5b: single retailer price {currency} {best['amount']}")
                                best.pop("_retailer_domain", None)
                                set_cached(cache_key, best, PRICE_CACHE_TTL)
                                best["_cached"] = False
                                return best
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5b failed: {e}")

                # Check budget before Tier 1.5c
                elapsed = time.monotonic() - tier15_start
                if elapsed >= tier15_budget:
                    logger.info(f"[PRICE] Tier 1.5 budget exhausted ({elapsed:.1f}s), skipping to Tier 2")
                else:
                    # --- Tier 1.5c: GCC luxury retailers ---
                    logger.info(f"[PRICE] Tier 1.5c: trying GCC retailers")
                    try:
                        gcc_query = f"{full_name} ounass OR bloomingdales dubai OR namshi"
                        gcc_results = await search_web(gcc_query)
                        self.api_calls += 1
                        self._track_cost(0.001)
                        if gcc_results and gcc_results.get("organic"):
                            for item in gcc_results["organic"][:3]:
                                link = item.get("link", "")
                                link_domain = urlparse(link).netloc.replace("www.", "")
                                if link_domain in self.GCC_LUXURY_RETAILERS:
                                    gcc_price = await self._fetch_page_price(link, full_name, currency)
                                    if gcc_price and gcc_price.get("amount"):
                                        # GCC sites often return AED — conversion handled by _fetch_page_price
                                        logger.info(f"[PRICE] Tier 1.5c: GCC price {currency} {gcc_price['amount']} from {link_domain}")
                                        set_cached(cache_key, gcc_price, PRICE_CACHE_TTL)
                                        gcc_price["_cached"] = False
                                        return gcc_price
                                    elif gcc_price and gcc_price.get("_got_html"):
                                        failed_curl_urls.append(link)
                                    # If gcc_price is None → curl itself failed, don't retry with Scrape.do
                    except Exception as e:
                        logger.warning(f"[PRICE] Tier 1.5c failed: {e}")

                    # --- Tier 1.5d: Scrape.do rendering fallback ---
                    # Only fires if curl_cffi found URLs but extraction failed (not timeouts)
                    elapsed = time.monotonic() - tier15_start
                    if (failed_curl_urls and elapsed < tier15_budget
                            and scrapedo_service.is_available()
                            and is_circuit_closed("scrapedo") and has_budget("scrapedo")):
                        # Prioritize GCC retailer URLs (more likely to have prices in rendered DOM)
                        gcc_domains = self.GCC_LUXURY_RETAILERS
                        sorted_urls = sorted(
                            failed_curl_urls,
                            key=lambda u: 0 if urlparse(u).netloc.replace("www.", "") in gcc_domains else 1,
                        )
                        for retry_url in sorted_urls[:2]:
                            if not self._validate_scrape_url(retry_url):
                                continue
                            retry_domain = urlparse(retry_url).netloc.replace("www.", "")
                            logger.info(f"[PRICE] Tier 1.5d: Scrape.do retry on {retry_domain}")
                            html, status = await scrapedo_service.render_page_with_status(retry_url)
                            # Always count usage on 200 (API credit spent even if no price)
                            if status == 200:
                                record_usage("scrapedo")
                            if html:
                                record_success("scrapedo")
                                price = self._extract_price_from_html(html, full_name, currency, retry_domain, retry_url)
                                if price:
                                    price["source_method"] = "scrapedo_rendered"
                                    logger.info(f"[PRICE] Tier 1.5d: Scrape.do price {currency} {price['amount']} from {retry_domain}")
                                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                                    price["_cached"] = False
                                    return price
                            elif status in (429, 503) or status == 0:
                                record_failure("scrapedo")
                                break  # Don't burn another credit if provider is struggling

            logger.info(f"[PRICE] Tier 1.5 cascade complete, no price found for {full_name}")

        # --- Tier 2: GPT extraction from search context ---
        if is_supplement:
            # Opt B: Supplements — search iHerb via Serper with price-focused query
            # Note: direct iHerb scrape blocked by Cloudflare from cloud IPs
            # Strip pill count and generic words from query — iHerb search is noisy with these
            iherb_query = re.sub(
                r'\b\d+\s*(softgels?|capsules?|tablets?|gummies?|caplets?|count|ct)\b',
                '', search_query, flags=re.IGNORECASE
            ).strip()
            # Remove generic supplement words that distort iHerb search results
            iherb_query = re.sub(
                r'\b(supplement|vitamin|vitamins|mineral|minerals)\b',
                '', iherb_query, flags=re.IGNORECASE
            ).strip()
            iherb_query = re.sub(r'\s+', ' ', iherb_query)  # collapse whitespace
            iherb_cc = region_info["code"]  # "bh" for Bahrain, "ae" for UAE, etc.

            # Direct iHerb scrape via curl_cffi (bypasses Cloudflare TLS fingerprinting)
            iherb_price = await self._fetch_iherb_price(iherb_query, brand, full_name, iherb_cc, currency)
            if iherb_price:
                iherb_price["_cached"] = False
                logger.info(f"[PRICE] Supplement: direct iHerb price {currency} {iherb_price['amount']} for {full_name}")
                # Cache iHerb rating in _shopping_items_cache for _get_verified_rating (zero extra API calls)
                if iherb_price.get("iherb_rating"):
                    self._shopping_items_cache[full_name] = [{
                        "source": "iHerb",
                        "rating": iherb_price["iherb_rating"],
                        "ratingCount": iherb_price.get("iherb_review_count"),
                        "link": iherb_price["url"],
                        "title": full_name,
                    }]
                    logger.info(f"[RATING] Cached iHerb rating {iherb_price['iherb_rating']} for {full_name}")
                set_cached(cache_key, iherb_price, PRICE_CACHE_TTL)
                return iherb_price

            # Direct scrape failed — search iHerb + Bahrain pharmacies in parallel
            logger.info(f"[PRICE] iHerb direct scrape failed, trying Serper + Bahrain pharmacy for {full_name}")
            iherb_task = search_web(f"{iherb_query} iherb price", num_results=5, country=iherb_cc)
            bh_pharmacy_task = search_web(f"{brand} {name} price", num_results=5, country="bh")
            iherb_results, bh_pharmacy_results = await asyncio.gather(iherb_task, bh_pharmacy_task)
            self._track_serper_cost()
            self._track_serper_cost()
            iherb_organic = iherb_results.get("organic", [])
            bh_organic = bh_pharmacy_results.get("organic", [])

            # NEW: Try JSON-LD extraction from Bahrain pharmacy product pages (FREE)
            pharmacy_price = await self._fetch_pharmacy_price(bh_organic, brand, full_name, currency)
            if pharmacy_price:
                pharmacy_price["_cached"] = False
                logger.info(f"[PRICE] Supplement: pharmacy JSON-LD price {currency} {pharmacy_price['amount']} for {full_name}")
                set_cached(cache_key, pharmacy_price, PRICE_CACHE_TTL)
                return pharmacy_price

            # Try page scraping on known retailer URLs from organic results (zero Serper cost)
            if ENABLE_PAGE_SCRAPE:
                known_supplement_retailers = {"iherb.com", "bn.boots.com", "bolo.bh", "amazon.com", "noon.com"}
                for item in (iherb_organic + bh_organic)[:5]:
                    link = item.get("link", "")
                    link_domain = urlparse(link).netloc.replace("www.", "")
                    if link_domain in known_supplement_retailers or link_domain in self.PHARMACY_DOMAINS:
                        page_price = await self._fetch_page_price(link, full_name, currency)
                        if page_price and page_price.get("amount"):
                            page_price["_cached"] = False
                            logger.info(f"[PRICE] Supplement: page scrape price {currency} {page_price['amount']} from {link_domain}")
                            set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                            return page_price

            # Combine results for GPT extraction fallback
            combined_organic = iherb_organic + bh_organic
            if combined_organic:
                logger.info(f"[PRICE] Supplement Serper: {len(iherb_organic)} iHerb + {len(bh_organic)} BH pharmacy results for {full_name}")
                organic_results = {"organic": combined_organic, "knowledge_graph": None}
            else:
                logger.info(f"[PRICE] No Serper results at all for {full_name}, falling to Tier 3")
                organic_results = {"organic": [], "knowledge_graph": None}
        else:
            # Non-supplements: fetch BH organic results on-demand (only when Tier 1 shopping failed)
            organic_results = await search_price_organic(search_query, region_info["code"])
            self._track_serper_cost()

        # Merge organic into search_results for context formatting
        search_results["organic"] = organic_results.get("organic", [])
        search_results["knowledge_graph"] = organic_results.get("knowledge_graph")
        search_context = self._format_search_results(search_results)
        price, usage = await extract_price(brand, name, variant, region, search_context)
        self._track_gpt_cost(usage)
        self._sanitize_gpt_price(price)
        # iHerb keyword search returns mixed currencies in snippets (mostly USD from www.iherb.com)
        # Trust GPT's currency detection — the extraction prompt handles USD/$, BHD/BD etc.
        # If GPT says USD → _convert_gpt_price_currency converts to BHD
        # If GPT says BHD → no conversion (might be from bh.iherb.com snippet)
        self._convert_gpt_price_currency(price, currency)
        if price and price.get("amount"):
            # Tag source_method based on whether currency conversion occurred
            original_cur = price.get("original_currency", "").upper()
            if original_cur and original_cur != currency:
                price["source_method"] = "converted_usd"
            else:
                price["source_method"] = "local_bhd"
            # Opt C: Supplements with iHerb data — skip sanity check (iHerb is Tier 1 trusted)
            if is_supplement:
                # Backfill iHerb as retailer when GPT didn't identify one
                if iherb_organic and not price.get("retailer"):
                    price["retailer"] = "iHerb"
                    from urllib.parse import quote_plus
                    price["url"] = f"https://{iherb_cc}.iherb.com/search?kw={quote_plus(full_name)}"
                logger.info(f"[PRICE] Supplement: trusting iHerb price, skipping sanity check for {full_name}")
            else:
                # Sanity check Tier 2 for non-supplement products (too high OR too low vs GPT estimate)
                # Reuse Tier 3 estimate if already fetched during Tier 1 check
                if tier3_estimate is None:
                    tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
                    self._track_gpt_cost(usage)
                    self._sanitize_gpt_price(tier3_estimate)
                    self._convert_gpt_price_currency(tier3_estimate, currency)
                if tier3_estimate and tier3_estimate.get("amount"):
                    tier2_bhd = _convert_to_bhd(price["amount"], currency)
                    tier3_bhd = _convert_to_bhd(tier3_estimate["amount"], currency)
                    # Luxury brands get tighter thresholds (same as Tier 1 sanity check)
                    if self._is_luxury_brand(full_name):
                        high_threshold = 1.8
                        low_threshold = 0.6
                    else:
                        high_threshold = 2.0
                        low_threshold = 0.5
                    if tier2_bhd > tier3_bhd * high_threshold:
                        logger.info(
                            f"[PRICE] Tier 2 too HIGH: {currency} {price['amount']} "
                            f"vs estimate {currency} {tier3_estimate['amount']} "
                            f"(threshold {high_threshold}x) — using Tier 3"
                        )
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
                    elif tier2_bhd < tier3_bhd * low_threshold:
                        logger.info(
                            f"[PRICE] Tier 2 too LOW: {currency} {price['amount']} "
                            f"vs estimate {currency} {tier3_estimate['amount']} "
                            f"(threshold {low_threshold}x) — using Tier 3"
                        )
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
            # Backfill URL from retailer name (GPT returns url: null)
            if price.get("retailer") and not price.get("url"):
                price["url"] = self._build_retailer_url(price["retailer"], full_name)
            logger.info(f"[PRICE] Tier 2 (GPT search): {currency} {price['amount']}")
            set_cached(cache_key, price, PRICE_CACHE_TTL)
            price["_cached"] = False
            return price

        # --- Broader search fallback (max 1 extra Serper call) ---
        broader_name = full_name
        for _ in range(3):  # Strip up to 3 trailing variants
            stripped = MODEL_VARIANT_PATTERN.sub('', broader_name).strip()
            if stripped == broader_name:
                break
            broader_name = stripped

        if broader_name != full_name and not is_supplement:
            logger.info(f"[PRICE] Trying broader search: '{broader_name}' (was '{full_name}')")
            broader_results = await search_product_prices(broader_name, region_info["code"])
            self._track_serper_cost()
            broader_shopping = broader_results.get("shopping", [])
            if broader_shopping:
                price = self._extract_price_from_shopping(broader_name, broader_shopping, currency)
                if price and price.get("amount"):
                    logger.info(f"[PRICE] Broader search hit: {currency} {price['amount']}")
                    price.pop("retailer_score", None)
                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                    price["_cached"] = False
                    return price

        # --- Tier 3: GPT training data fallback ---
        logger.info(f"[PRICE] Tiers 1-2 failed, falling back to GPT estimate for {full_name}")
        # Reuse Tier 3 estimate if already fetched during sanity checks
        if tier3_estimate is None:
            tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
            self._track_gpt_cost(usage)
            self._sanitize_gpt_price(tier3_estimate)
            self._convert_gpt_price_currency(tier3_estimate, currency)
        price = tier3_estimate
        if price and price.get("amount"):
            price["estimated"] = True
            price["source_method"] = "estimated"
            # Backfill URL from retailer name (GPT returns url: null)
            if price.get("retailer") and not price.get("url"):
                price["url"] = self._build_retailer_url(price["retailer"], full_name)
            logger.info(f"[PRICE] Tier 3 (estimated): {currency} {price['amount']}")
            # Cache estimates for shorter time
            set_cached(cache_key, price, PRICE_CACHE_TTL // 2)
            price["_cached"] = False
            return price

        # All tiers failed
        logger.warning(f"[PRICE] All tiers failed for {full_name}")
        return {"amount": None, "currency": currency, "_cached": False}

    # Accessory keywords — if title contains any of these, it's not the product itself
    ACCESSORY_KEYWORDS = {
        "case", "cover", "protector", "charger", "cable", "adapter", "holder",
        "stand", "strap", "sleeve", "pouch", "film", "tempered", "glass",
        "mount", "grip", "wallet", "skin", "bumper", "shell", "screen protector",
        "armband", "holster", "dock", "cradle", "earbuds", "headphone",
        "stylus", "pen", "keyboard", "mouse",
    }

    # Product keywords that indicate high-value electronics (minimum BHD 100)
    HIGH_VALUE_KEYWORDS = {
        "iphone", "galaxy", "pixel", "samsung", "oneplus", "huawei", "xiaomi",
        "macbook", "ipad", "laptop", "playstation", "xbox", "nintendo",
        "rtx", "nvidia", "geforce", "radeon", "amd", "gpu",
    }

    # Keywords indicating counterfeit/replica/used listings — filter from price results
    COUNTERFEIT_KEYWORDS = {
        "replica", "fake", "dupe", "inspired by", "inspired",
        "knockoff", "knock-off", "imitation", "copy",
        "look alike", "lookalike", "designer inspired",
        "unbranded", "generic", "homage", "alternative",
        "pre-owned", "used", "vintage", "secondhand", "second hand",
    }

    @staticmethod
    def _is_counterfeit_listing(title: str) -> bool:
        """Check if a shopping listing title indicates counterfeit/replica/used product."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in StructuredComparisonService.COUNTERFEIT_KEYWORDS)

    # Luxury/designer brand keywords — triggers price guardrails regardless of category
    LUXURY_BRAND_KEYWORDS = {
        "louis vuitton", "lv", "hermes", "hermès", "chanel", "gucci", "prada",
        "dior", "burberry", "fendi", "balenciaga", "versace", "givenchy",
        "ysl", "saint laurent", "cartier", "rolex", "omega", "patek philippe",
        "tag heuer", "tiffany", "tom ford", "bottega veneta", "valentino",
        "celine", "loewe", "moncler", "balmain", "alexander mcqueen",
    }

    # Official brand website domains — always trust score 1.0 for price
    OFFICIAL_BRAND_DOMAINS = {
        "hermes.com", "louisvuitton.com", "chanel.com", "gucci.com", "prada.com",
        "dior.com", "burberry.com", "fendi.com", "balenciaga.com", "cartier.com",
        "rolex.com", "omegawatches.com", "tiffany.com", "tomford.com",
        "apple.com", "samsung.com", "sony.com", "dell.com", "hp.com",
        "nordstrom.com", "farfetch.com", "ssense.com", "net-a-porter.com",
        "sephora.com", "harrods.com", "selfridges.com",
    }

    # Authorized luxury retailers — trusted for cross-validation (Tier 1.5b)
    AUTHORIZED_LUXURY_RETAILERS = {
        "farfetch.com", "ssense.com", "net-a-porter.com",
        "mytheresa.com", "matchesfashion.com", "nordstrom.com",
    }

    # GCC luxury retailers — regional fallback (Tier 1.5c)
    GCC_LUXURY_RETAILERS = {
        "ounass.ae", "ounass.com", "namshi.com", "bloomingdales.ae",
        "level-shoes.com", "harveynichols.com", "galerieslafayette.ae",
        "theluxurycloset.com", "boutique1.com",
    }

    PAGE_SCRAPE_TIMEOUT = 5  # seconds per curl_cffi page fetch (reduced; JS render has separate timeout)
    TIER_15_BUDGET_TIMEOUT = 20  # seconds total across all Tier 1.5 sub-tiers

    @staticmethod
    def _is_accessory(title: str) -> bool:
        """Check if a shopping result title is an accessory, not the actual product."""
        title_lower = title.lower()
        for kw in StructuredComparisonService.ACCESSORY_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                return True
        return False

    @staticmethod
    def _sanitize_gpt_price(price: Optional[Dict]) -> None:
        """Fix GPT returning the string 'null' or echoing prompt templates for optional fields."""
        if not price:
            return
        for key in ("retailer", "url"):
            val = price.get(key)
            if not isinstance(val, str):
                continue
            # Catch: "null", "store name or null", "product url or null", etc.
            if val.lower() == "null" or "or null" in val.lower():
                price[key] = None

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract clean domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain or ""
        except Exception:
            return ""

    @staticmethod
    def _validate_price_query(brand: str, name: str, region: str) -> bool:
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

    @staticmethod
    def _validate_scrape_url(url: str) -> bool:
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
            # NOTE: "/shop/" intentionally excluded — many GCC retailers use /shop/ in product URLs
            if any(p in path_lower for p in blocked_patterns):
                logger.info(f"[PRICE] URL validation: rejected non-product URL: {url[:80]}")
                return False
            return True
        except Exception:
            return False

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

    NEGATIVE_INDICATORS = {"bad", "poor", "disappointing", "issue", "problem", "broke", "broken",
        "flimsy", "cheap", "overpriced", "uncomfortable", "fragile", "peeling",
        "fading", "cracking", "defect", "flaw", "mediocre", "underwhelming",
        "lacking", "missing", "difficult", "annoying", "frustrating", "worse", "worst"}

    POSITIVE_INDICATORS = {"great", "excellent", "premium", "beautiful", "perfect", "love",
        "amazing", "wonderful", "fantastic", "superb", "outstanding", "impressive",
        "comfortable", "luxurious", "elegant", "sturdy", "durable", "quality"}

    def _clean_review_content(self, reviews: dict) -> dict:
        """Remove garbage text, short items, and misclassified sentiments from reviews."""
        import re
        for section in ["common_praises", "detailed_praises", "common_complaints", "detailed_complaints"]:
            items = reviews.get(section, [])
            if not items:
                continue
            cleaned = []
            for item in items:
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                if any(re.search(p, text, re.IGNORECASE) for p in self.GARBAGE_PATTERNS):
                    continue
                if len(text.split()) < 8:
                    continue
                if "complaint" in section:
                    words = set(text.lower().split())
                    has_negative = bool(words & self.NEGATIVE_INDICATORS)
                    has_positive = bool(words & self.POSITIVE_INDICATORS)
                    if has_positive and not has_negative:
                        continue
                cleaned.append(item)
            reviews[section] = cleaned
        return reviews

    def _derive_rating_from_scores(self, overall_score: float) -> float:
        """Derive a synthetic rating (1-5 scale) from overall score when no real rating exists."""
        rating = 2.5 + (overall_score / 100) * 2.3
        return round(min(rating, 4.8), 1)

    def _clean_review_citations(self, reviews: dict, search_results: list) -> dict:
        """Replace [snippet_N] with source domain name in review text fields.

        Only cleans review display fields (common_praises, common_complaints,
        detailed_praises, detailed_complaints). Does NOT touch spec _source fields.
        """
        # Build snippet index → source domain map
        snippet_source_map = {}
        for i, result in enumerate(search_results or []):
            link = result.get("link", "")
            if link:
                snippet_source_map[str(i + 1)] = self._extract_domain(link)

        def replace_citation(text: str) -> str:
            def replacer(match):
                snippet_num = match.group(1)
                domain = snippet_source_map.get(snippet_num, "")
                if domain:
                    return f"Per {domain}: "
                return ""
            return re.sub(r'\[snippet_(\d+)\]\s*', replacer, text)

        cleaned = dict(reviews)
        for key in ["common_praises", "common_complaints"]:
            if key in cleaned and isinstance(cleaned[key], list):
                cleaned[key] = [replace_citation(str(item)) for item in cleaned[key]]
        for key in ["detailed_praises", "detailed_complaints"]:
            if key in cleaned and isinstance(cleaned[key], list):
                for item in cleaned[key]:
                    if isinstance(item, dict) and "text" in item:
                        item["text"] = replace_citation(str(item["text"]))
        return cleaned

    @staticmethod
    def _convert_gpt_price_currency(price: Optional[Dict], target_currency: str) -> None:
        """Convert GPT-returned price from original_currency to target currency using _convert_to_bhd rates."""
        if not price or not price.get("amount"):
            return
        original = price.get("original_currency", "").upper()
        if not original or original == target_currency:
            return
        # Convert: original → BHD → target
        amount = price["amount"]
        amount_bhd = _convert_to_bhd(amount, original)
        if target_currency == "BHD":
            converted = amount_bhd
        else:
            # BHD → target: divide by the target's BHD rate
            target_bhd_rate = _convert_to_bhd(1.0, target_currency)
            converted = amount_bhd / target_bhd_rate if target_bhd_rate > 0 else amount_bhd
        logger.info(
            f"[PRICE] GPT currency convert: {original} {amount} -> {target_currency} {round(converted, 2)}"
        )
        price["amount"] = round(converted, 2)
        price["currency"] = target_currency

    @staticmethod
    def _is_high_value_query(product_name: str) -> bool:
        """Check if the query is for a high-value product (phone, laptop, console)."""
        name_lower = product_name.lower()
        return any(kw in name_lower for kw in StructuredComparisonService.HIGH_VALUE_KEYWORDS)

    @staticmethod
    def _is_luxury_brand(product_name: str) -> bool:
        """Check if the product is from a luxury/designer brand (triggers price guardrails)."""
        name_lower = product_name.lower()
        return any(brand in name_lower for brand in StructuredComparisonService.LUXURY_BRAND_KEYWORDS)

    def _get_official_domain(self, product_name: str) -> Optional[str]:
        """Return the official brand domain for a luxury product, or None."""
        name_lower = product_name.lower()
        for keyword in self.LUXURY_BRAND_KEYWORDS:
            if keyword in name_lower:
                for domain in self.OFFICIAL_BRAND_DOMAINS:
                    domain_base = domain.split(".")[0].replace("-", "")
                    keyword_clean = keyword.replace(" ", "").replace("-", "")
                    if keyword_clean in domain_base or domain_base in keyword_clean:
                        return domain
        return None

    SUPPLEMENT_KEYWORDS = {
        "vitamin", "supplement", "softgel", "capsule", "mineral",
        "omega", "probiotic", "protein", "magnesium", "zinc", "calcium",
        "fish oil", "collagen", "biotin", "melatonin", "turmeric", "creatine",
        "multivitamin", "iron", "folic", "coq10", "glucosamine",
        "d3", "d-3",  # unambiguously vitamin names
        "nature made", "now foods", "solgar", "garden of life", "kirkland",  # supplement brands
    }

    async def _fetch_iherb_price(self, query: str, brand: str, full_name: str, region_code: str, currency: str) -> Optional[Dict[str, Any]]:
        """Fetch price directly from regional iHerb search page.

        iHerb embeds structured product data in HTML data-ga-* attributes.
        Returns price dict or None if fetch/parse fails.
        """
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
                logger.warning(f"[PRICE] iHerb returned {resp.status_code}")
                return None
            page = resp.text
            # Parse product cards using BeautifulSoup (attribute-order-independent)
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
                # Extract rating data from data-ga attributes (zero extra cost)
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
                logger.info(f"[PRICE] iHerb: no product cards found on page")
                return None
            logger.info(f"[PRICE] iHerb: found {len(products)} products, matching to '{full_name}'")
            # Match: among brand matches containing ALL query words, pick cheapest
            brand_lower = brand.lower()
            name_words = self._normalize_words(full_name)
            brand_matches = []
            for p in products:
                if p["brand"].lower() != brand_lower and brand_lower not in p["brand"].lower():
                    continue
                brand_matches.append(p)
            if not brand_matches:
                # Try looser brand match (e.g., "NOW" in "Now Foods")
                brand_matches = [p for p in products if brand_lower in p["title"].lower()]
            # Primary: products whose title contains ALL query words → cheapest wins
            best = None
            full_matches = []
            for p in brand_matches:
                title_words = self._normalize_words(p["title"])
                if name_words.issubset(title_words):
                    full_matches.append(p)
            if full_matches:
                # Use iHerb's relevance order (first match) — their search puts popular products first
                best = full_matches[0]
                logger.info(f"[PRICE] iHerb match: all-words, first of {len(full_matches)} candidates")
            else:
                # Fallback: best word overlap, cheapest tiebreaker
                best_score = -1
                for p in brand_matches:
                    title_words = self._normalize_words(p["title"])
                    overlap = len(name_words & title_words)
                    if self._numbers_match(full_name, p["title"]):
                        overlap += 2
                    if overlap > best_score or (overlap == best_score and best and p["price"] < best["price"]):
                        best_score = overlap
                        best = p
                if best:
                    logger.info(f"[PRICE] iHerb match: overlap fallback (score={best_score})")
            if not best:
                logger.info(f"[PRICE] iHerb: no brand match for '{brand}' in results")
                return None
            if best.get("rating"):
                logger.info(f"[PRICE] iHerb direct: {currency} {best['price']} for '{best['title'][:80]}' (rating: {best['rating']}, reviews: {best.get('review_count')})")
            else:
                logger.info(f"[PRICE] iHerb direct: {currency} {best['price']} for '{best['title'][:80]}'")
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

    @staticmethod
    def _is_supplement_query(product_name: str) -> bool:
        """Check if the query is for a supplement/vitamin product.
        Uses electronics anti-keywords to prevent false positives like 'Galaxy Tablet'."""
        name_lower = product_name.lower()
        # Electronics anti-keywords — if present, NOT a supplement
        if any(kw in name_lower for kw in StructuredComparisonService.HIGH_VALUE_KEYWORDS):
            return False
        return any(kw in name_lower for kw in StructuredComparisonService.SUPPLEMENT_KEYWORDS)

    # Manufacturer names that AIB partners replace in product titles
    # (e.g. "NVIDIA RTX 3070" → "EVGA GeForce RTX 3070", "MSI RTX 3070")
    MANUFACTURER_BRAND_WORDS = {"nvidia", "amd", "intel"}

    @staticmethod
    def _normalize_words(text: str) -> set:
        """Normalize words for matching: lowercase, remove hyphens and punctuation.

        'Vitamin D-3, 1000 IU' → {'vitamin', 'd3', '1000', 'iu'}
        """
        return set(w.replace("-", "").strip(",.()&:;'\"") for w in text.lower().split() if w.strip(",.()&:;'\""))

    @staticmethod
    def _numbers_match(product_name: str, title: str) -> bool:
        """Check that significant numbers in product name appear in title.

        'NOW Vitamin D-3 360 Softgels' → title must contain '360'.
        Ignores small numbers (<=9) which are often model suffixes like 'D-3'.
        Only checks standalone numbers (not embedded in words).
        """
        # Extract standalone numbers > 9 from product name
        product_numbers = set(re.findall(r'\b(\d{2,})\b', product_name))
        if not product_numbers:
            return True  # No significant numbers to enforce

        title_numbers = set(re.findall(r'\b(\d{2,})\b', title))
        # At least one product number must appear in title
        return bool(product_numbers & title_numbers)

    @staticmethod
    def _extract_jsonld_price(html: str, brand: str, expected_currency: str) -> Optional[Dict[str, Any]]:
        """Parse JSON-LD Product schema from HTML for price data.

        Looks for <script type="application/ld+json"> containing a Product
        with offers.price in the expected currency. Verifies brand name
        appears in the product name.

        Returns price dict or None if no valid match found.
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

            # Collect Product objects (may be top-level, in @graph, or in a list)
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
                # Verify brand in product name (space-insensitive: "HealthAid" matches "Health Aid")
                product_name = product.get("name", "")
                brand_nospace = brand_lower.replace(" ", "")
                name_nospace = product_name.lower().replace(" ", "")
                if brand_nospace not in name_nospace:
                    continue

                # Extract offers (single dict or list)
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

    # Bahrain pharmacy domains that serve JSON-LD Product schema with BHD prices
    PHARMACY_DOMAINS = {
        "bolo.bh": "Bolo",
        "bn.boots.com": "Boots",
        "aldeerahpharmacy.com": "Al Deerah Pharmacy",
    }

    async def _fetch_pharmacy_price(
        self,
        serper_organic: List[Dict],
        brand: str,
        full_name: str,
        currency: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch BHD price from Bahrain pharmacy product pages via JSON-LD.

        Filters Serper organic results for known pharmacy domains, fetches
        each product page, and parses JSON-LD Product schema for price.
        If initial URLs have no JSON-LD (e.g. search pages), tries a targeted
        site:bolo.bh search to find indexed product pages.
        Returns first valid match or None.
        """
        # Collect pharmacy URLs from existing Serper results
        pharmacy_urls = []
        for item in serper_organic:
            link = item.get("link", "")
            for domain, retailer_name in self.PHARMACY_DOMAINS.items():
                if domain in link:
                    pharmacy_urls.append((link, retailer_name))
                    break

        # Try fetching and parsing JSON-LD from pharmacy URLs
        result = await self._try_pharmacy_urls(pharmacy_urls, brand, currency)
        if result:
            return result

        # Initial URLs had no JSON-LD (likely search/listing pages) — try targeted site search
        site_query = " OR ".join(f"site:{d}" for d in self.PHARMACY_DOMAINS.keys())
        logger.info(f"[PRICE] No JSON-LD in initial pharmacy URLs, trying targeted pharmacy search for {full_name}")
        try:
            site_results = await search_web(f"{full_name} {site_query}", num_results=5, country="bh")
            self._track_serper_cost()
            site_urls = []
            for item in site_results.get("organic", []):
                link = item.get("link", "")
                for domain, retailer_name in self.PHARMACY_DOMAINS.items():
                    if domain in link:
                        site_urls.append((link, retailer_name))
                        break
            result = await self._try_pharmacy_urls(site_urls, brand, currency)
            if result:
                return result
        except Exception as e:
            logger.warning(f"[PRICE] Site search failed: {e}")

        logger.info(f"[PRICE] No pharmacy JSON-LD price found for {full_name}")
        return None

    async def _try_pharmacy_urls(
        self,
        pharmacy_urls: List[Tuple[str, str]],
        brand: str,
        currency: str,
    ) -> Optional[Dict[str, Any]]:
        """Try fetching JSON-LD price from a list of pharmacy URLs.

        Returns price dict on first successful JSON-LD extraction, or None.
        """
        if not pharmacy_urls:
            return None

        logger.info(f"[PRICE] Trying {len(pharmacy_urls)} pharmacy URLs for JSON-LD extraction")

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url, retailer_name in pharmacy_urls[:3]:
                try:
                    resp = await client.get(url, follow_redirects=True)
                    if resp.status_code != 200:
                        logger.info(f"[PRICE] Pharmacy {retailer_name}: HTTP {resp.status_code} for {url}")
                        continue

                    price_data = self._extract_jsonld_price(resp.text, brand, currency)
                    if price_data:
                        logger.info(f"[PRICE] Pharmacy JSON-LD: {currency} {price_data['amount']} from {retailer_name}")
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
                    else:
                        logger.info(f"[PRICE] Pharmacy {retailer_name}: no valid JSON-LD price at {url}")

                except Exception as e:
                    logger.warning(f"[PRICE] Pharmacy {retailer_name} fetch failed: {e}")
                    continue

        return None

    async def _curl_fetch_html(self, url: str) -> Optional[str]:
        """Fetch raw HTML via curl_cffi (no JS rendering). Returns HTML string or None."""
        try:
            from curl_cffi import requests as curl_requests
            resp = await asyncio.to_thread(
                lambda: curl_requests.get(
                    url,
                    impersonate="chrome",
                    timeout=self.PAGE_SCRAPE_TIMEOUT,
                    allow_redirects=True,
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

    def _extract_price_from_html(
        self, html: str, product_name: str, currency: str, domain: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """Extract price from HTML using structured data (JSON-LD, OG, microdata).

        Sync helper — no I/O, just HTML parsing. Reuses existing
        _extract_jsonld_price() for JSON-LD, adds OG and microdata fallbacks.
        """
        from bs4 import BeautifulSoup
        brand = product_name.split()[0] if product_name else ""

        # Priority 1: JSON-LD (reuse existing method)
        price_data = self._extract_jsonld_price(html, brand, currency)
        if not price_data:
            # Try USD — convert later
            price_data = self._extract_jsonld_price(html, brand, "USD")
            if price_data:
                price_data["_needs_conversion"] = True

        if price_data and price_data.get("amount"):
            logger.info(f"[PRICE] Page scrape: JSON-LD price {price_data['amount']} {price_data.get('currency', currency)} from {domain}")
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
                self._convert_gpt_price_currency(result, currency)
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
                    logger.info(f"[PRICE] Page scrape: OG meta price {amount} {detected_currency} from {domain}")
                    result = {
                        "amount": amount, "original_currency": detected_currency,
                        "currency": detected_currency, "retailer": domain, "url": url,
                        "in_stock": True, "confidence": 0.9, "estimated": False,
                        "source_method": "page_scrape",
                    }
                    if detected_currency.upper() != currency.upper():
                        self._convert_gpt_price_currency(result, currency)
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
                    logger.info(f"[PRICE] Page scrape: microdata price {amount} {detected_currency} from {domain}")
                    result = {
                        "amount": amount, "original_currency": detected_currency,
                        "currency": detected_currency, "retailer": domain, "url": url,
                        "in_stock": True, "confidence": 0.8, "estimated": False,
                        "source_method": "page_scrape",
                    }
                    if detected_currency.upper() != currency.upper():
                        self._convert_gpt_price_currency(result, currency)
                    return result
            except (ValueError, TypeError):
                pass

        return None

    async def _fetch_page_price(
        self,
        url: str,
        product_name: str,
        currency: str = "BHD",
    ) -> Optional[Dict[str, Any]]:
        """Fetch a product page via curl_cffi and extract price from structured data.

        Uses _extract_price_from_html() for JSON-LD/OG/microdata parsing.
        Gated by ENABLE_PAGE_SCRAPE feature flag.
        JS rendering (Firecrawl/Scrape.do) is handled at the cascade level in _get_price().

        Returns:
            - Dict with price data if found
            - {"_got_html": True} if curl_cffi fetched HTML but no price (Scrape.do candidate)
            - None if curl_cffi failed to fetch (not a Scrape.do candidate)
        """
        if not ENABLE_PAGE_SCRAPE:
            return None

        domain = urlparse(url).netloc.replace("www.", "")
        html = await self._curl_fetch_html(url)
        if html:
            price = self._extract_price_from_html(html, product_name, currency, domain, url)
            if price:
                logger.info(f"[PRICE] Page scrape: curl_cffi price {currency} {price['amount']} from {domain}")
                return price
            logger.info(f"[PRICE] Page scrape: curl_cffi no structured data from {domain}")
            return {"_got_html": True}  # Signal: HTML fetched but no price — JS render may help

        return None  # curl_cffi itself failed — JS render won't help either

    @staticmethod
    def _strict_title_match(product_name: str, title: str) -> bool:
        """Key words from the product name must appear in the shopping title.

        'iPhone 16 Pro Max' → title must contain 'iphone' AND '16' AND 'pro' AND 'max'.
        'HealthAid Vitamin D-3' → title must contain 'healthaid' AND 'vitamin' (d3 is <=2 chars).
        Small words (<=2 chars after hyphen removal) like 'vs', 'of', 'd3' are skipped.
        Manufacturer brands (nvidia, amd, intel) are skipped since AIB partners rebrand.
        Hyphens are normalized: 'D-3' matches 'D3'.
        """
        # Reject counterfeit/replica listings outright
        if StructuredComparisonService._is_counterfeit_listing(title):
            return False

        title_normalized = title.lower().replace("-", "")
        key_words = [
            w.replace("-", "") for w in product_name.lower().split()
            if len(w.replace("-", "")) > 2
            and w.replace("-", "") not in StructuredComparisonService.MANUFACTURER_BRAND_WORDS
        ]
        return all(w in title_normalized for w in key_words)

    # Rating retailer tiers — determines confidence label
    RATING_TIER_1 = {  # "Verified" — official/authorized, real product ratings
        "amazon", "apple", "samsung", "best buy", "bestbuy", "walmart",
        "target", "noon", "jarir", "extra", "newegg", "b&h", "bhphoto",
        "iherb", "sephora", "ulta",
    }
    RATING_TIER_2 = {  # "Verified" — known retailers, real product ratings
        "costco", "carrefour", "sharaf dg", "virgin megastore", "currys",
        "john lewis", "adorama", "micro center", "google store", "microsoft",
        "dell", "hp store", "lenovo", "fnac",
        "fragrantica", "sally beauty", "lookfantastic", "beautybay", "nykaa",
        "bath & body", "boots",
    }
    RATING_TIER_3 = {  # "Marketplace rating" — only if review_count > 1000
        "ebay", "aliexpress", "alibaba", "temu", "wish",
    }

    @staticmethod
    def _get_rating_tier(source: str) -> int:
        """Classify a retailer into rating trust tiers. Returns 1, 2, or 3."""
        if not source:
            return 3
        source_lower = source.lower()
        for r in StructuredComparisonService.RATING_TIER_1:
            if r in source_lower:
                return 1
        for r in StructuredComparisonService.RATING_TIER_2:
            if r in source_lower:
                return 2
        # Check for .com or .ae domains — likely a real retailer site
        if ".com" in source_lower or ".ae" in source_lower:
            return 2
        return 3

    @staticmethod
    def _get_retailer_score(retailer_name: str) -> float:
        """Score a retailer by quality tier. Higher = more trustworthy."""
        if not retailer_name:
            return DEFAULT_RETAILER_SCORE
        name_lower = retailer_name.lower()
        for key, score in RETAILER_TIERS.items():
            if key in name_lower:
                return score
        return DEFAULT_RETAILER_SCORE

    def _has_retailer_url(self, source: str) -> bool:
        """Check if a source name matches any key in RETAILER_SEARCH_URLS."""
        if not source:
            return False
        source_lower = source.lower().strip()
        return any(key in source_lower for key in RETAILER_SEARCH_URLS)

    def _build_retailer_url(self, source: str, product_name: str) -> Optional[str]:
        """Build a retailer search URL from the source name and product name.
        Returns None for unknown retailers instead of a generic Google search."""
        if not source:
            return None
        from urllib.parse import quote_plus
        source_lower = source.lower().strip()
        for key, template in RETAILER_SEARCH_URLS.items():
            if key in source_lower:
                return template.format(query=quote_plus(product_name))
        return None

    def _extract_price_from_shopping(
        self,
        product_name: str,
        shopping_items: List[Dict],
        currency: str
    ) -> Optional[Dict[str, Any]]:
        """Extract best matching price from Serper Shopping results.

        Filters: accessories removed, minimum price for phones, strict title match.
        Then: purge Tier 3 if better retailers exist.
        Prioritizes: title match → retailer quality → lowest price.
        """
        if not shopping_items:
            return None

        p_words = self._normalize_words(product_name)
        is_high_value = self._is_high_value_query(product_name)
        is_luxury = self._is_luxury_brand(product_name)
        min_price = 100.0 if is_high_value else 0

        # For luxury brands: filter out untrusted sellers entirely
        if is_luxury:
            min_price = max(min_price, 50.0)  # Luxury items rarely under BHD 50

        candidates = []

        for item in shopping_items:
            price_str = item.get("price", "")
            if not price_str:
                continue

            amount = self._parse_price_string(price_str)
            if amount is None or amount <= 0:
                continue

            # Detect original currency and convert to target if needed
            detected_currency = self._detect_currency(price_str)
            if detected_currency and detected_currency != currency:
                original_amount = amount
                amount = _convert_to_bhd(amount, detected_currency)
                if currency != "BHD":
                    # Convert from BHD to target currency (reverse lookup)
                    bhd_rate = _convert_to_bhd(1.0, currency)
                    if bhd_rate > 0:
                        amount = amount / bhd_rate
                logger.debug(
                    f"[PRICE] Converted {detected_currency} {original_amount} -> {currency} {round(amount, 2)}"
                )

            title = item.get("title", "")

            # FILTER 0: Reject counterfeit/replica/used listings
            if self._is_counterfeit_listing(title):
                logger.debug(f"[PRICE] Skipping counterfeit listing: {title[:60]}")
                continue

            # FILTER 1: Reject accessories
            if self._is_accessory(title):
                logger.debug(f"[PRICE] Skipped accessory: '{title}' ({price_str})")
                continue

            # FILTER 2: Minimum price for high-value products
            if is_high_value and amount < min_price:
                logger.debug(f"[PRICE] Skipped too-cheap: '{title}' at {currency} {amount} (min {min_price})")
                continue

            # FILTER 3: Strict title match for high-value products
            if is_high_value and not self._strict_title_match(product_name, title):
                logger.debug(f"[PRICE] Skipped weak title match: '{title}' for '{product_name}'")
                continue

            # FILTER 4: Number preservation — quantity must match (360 softgels ≠ 120 softgels)
            if not self._numbers_match(product_name, title):
                logger.debug(f"[PRICE] Skipped number mismatch: '{title}' for '{product_name}'")
                continue

            # Standard word-overlap score (still used for sorting)
            t_words = self._normalize_words(title)
            match_score = len(p_words & t_words) / len(p_words) if p_words else 0

            if match_score < 0.4:
                continue

            retailer = item.get("source", "")
            retailer_score = self._get_retailer_score(retailer)

            # Boost official brand domains to max trust
            link = item.get("link", "")
            if link:
                domain = self._extract_domain(link)
                if domain in self.OFFICIAL_BRAND_DOMAINS:
                    retailer_score = 1.0
                    logger.debug(f"[PRICE] Official brand domain boost: {domain}")

            candidates.append({
                "amount": round(amount, 2),
                "currency": currency,
                "retailer": retailer,
                "url": item.get("link") or self._build_retailer_url(retailer, product_name),
                "in_stock": True,
                "source_method": "local_bhd",
                "confidence": round(min(0.7 + match_score * 0.3, 1.0), 2),
                "match_score": match_score,
                "retailer_score": retailer_score,
                "title": title,
            })

        if not candidates:
            return None

        # FILTER 4: Purge Tier 3 retailers if better options exist
        tier1_exists = any(c["retailer_score"] >= 1.0 for c in candidates)
        tier2_exists = any(c["retailer_score"] >= 0.7 for c in candidates)

        if tier1_exists or tier2_exists:
            candidates = [c for c in candidates if c["retailer_score"] >= 0.5]
            logger.debug(f"[PRICE] Filtered out low-tier retailers, {len(candidates)} remain")

        if not candidates:
            return None

        # Sort: best retailer quality → best title match → lowest price
        # For luxury brands, retailer trust is most important (official > reseller)
        if is_luxury:
            candidates.sort(key=lambda c: (-c["retailer_score"], -c["match_score"], c["amount"]))
        else:
            candidates.sort(key=lambda c: (-c["match_score"], -c["retailer_score"], c["amount"]))
        best = candidates[0]

        logger.info(
            f"[PRICE] Selected: {best['retailer']} (tier {best['retailer_score']}) "
            f"at {best['currency']} {best['amount']} for '{product_name}' "
            f"({len(candidates)} candidates)"
        )

        # Remove internal fields (keep retailer_score for sanity check in _get_price)
        best.pop("match_score", None)
        best.pop("title", None)
        return best

    # Currency detection patterns — order matters (check specific codes before generic strip)
    CURRENCY_SYMBOLS = {
        "$": "USD", "£": "GBP", "€": "EUR", "¥": "JPY",
    }
    CURRENCY_CODES = {
        "USD": "USD", "GBP": "GBP", "EUR": "EUR", "JPY": "JPY",
        "AED": "AED", "SAR": "SAR", "BHD": "BHD", "KWD": "KWD",
        "QAR": "QAR", "OMR": "OMR", "INR": "INR",
    }

    @staticmethod
    def _detect_currency(price_str: str) -> Optional[str]:
        """Detect original currency from a price string before stripping."""
        if not price_str:
            return None
        # Check symbols first
        for sym, code in StructuredComparisonService.CURRENCY_SYMBOLS.items():
            if sym in price_str:
                return code
        # Check currency codes (e.g. "BHD 200", "SAR 2,499")
        upper = price_str.upper()
        for code in StructuredComparisonService.CURRENCY_CODES:
            if code in upper:
                return code
        return None

    @staticmethod
    def _parse_price_string(price_str: str) -> Optional[float]:
        """Parse price strings like '$699.99', 'BHD 339.000', 'SAR 2,499'.
        Returns the numeric amount only. Use _detect_currency() to get the original currency."""
        if not price_str:
            return None
        # Strip currency symbols and codes
        cleaned = re.sub(r'[A-Z]{2,3}\s*', '', price_str)  # Remove currency codes
        cleaned = re.sub(r'[$£€¥]', '', cleaned)            # Remove currency symbols
        cleaned = cleaned.replace(',', '')                    # Remove thousands separators
        cleaned = cleaned.strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            # Try to find first number-like pattern
            match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
            if match:
                return float(match.group(1))
            return None
    
    # Category-specific review search terms for richer snippets
    CATEGORY_REVIEW_TERMS = {
        "electronics": "user reviews pros cons battery camera performance display",
        "grocery": "user reviews taste quality ingredients value",
        "beauty": "user reviews results skin ingredients effectiveness",
        "fashion": "user reviews fit quality comfort sizing",
        "home": "user reviews quality durability assembly value",
        "sports": "user reviews performance comfort durability",
    }

    def _collect_retailer_ratings(self, full_name: str) -> List[Dict[str, Any]]:
        """Extract per-retailer rating data from shopping cache for review enrichment."""
        shopping_items = self._shopping_items_cache.get(full_name, [])
        ratings = []
        seen = set()

        for item in shopping_items:
            rating = item.get("rating")
            source = item.get("source", "")
            if not rating or not source:
                continue
            # Deduplicate by source name
            source_key = source.lower().strip()
            if source_key in seen:
                continue
            seen.add(source_key)

            review_count = None
            for key in ("ratingCount", "reviewCount", "reviews"):
                raw = item.get(key)
                if raw is not None:
                    try:
                        review_count = int(str(raw).replace(",", "").replace("+", ""))
                        break
                    except (ValueError, TypeError):
                        continue

            try:
                ratings.append({
                    "source": source,
                    "rating": round(float(rating), 1),
                    "review_count": review_count,
                })
            except (ValueError, TypeError):
                continue

        return ratings

    def _format_review_search_results(self, results: Dict, retailer_ratings: List[Dict]) -> str:
        """Format search results for review extraction — uses all 10 organic results with source attribution."""
        if not results:
            return "No search results available."

        formatted = []

        # All organic results (up to 10) with domain prefix
        organic = results.get("organic", [])[:10]
        for i, r in enumerate(organic):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            # Extract domain for attribution
            domain = ""
            if link:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(link).netloc.replace("www.", "")
                except Exception:
                    pass
            prefix = f"[{domain}] " if domain else ""
            formatted.append(f"{i+1}. {prefix}{title}\n   {snippet}")

        # Append retailer ratings from shopping data
        if retailer_ratings:
            formatted.append("\n--- Retailer Ratings (from shopping data) ---")
            for r in retailer_ratings:
                count_str = f" ({r['review_count']} reviews)" if r.get("review_count") else ""
                formatted.append(f"- {r['source']}: {r['rating']}/5{count_str}")

        return "\n".join(formatted)

    async def _get_reviews(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        search_query: str,
        nocache: bool = False,
        category: str = "other",
        retailer_ratings: Optional[List[Dict]] = None,
        search_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get reviews with caching. Uses pre-fetched search_results if provided."""
        cache_key = get_reviews_cache_key(brand, name, variant)

        # Check cache
        cached = get_cached(cache_key) if not nocache else None
        if cached:
            logger.info(f"Reviews cache hit: {cache_key}")
            cached["_cached"] = True
            return cached

        # Fetch from search (reuse unified search if available)
        review_terms = self.CATEGORY_REVIEW_TERMS.get(category, "user reviews pros cons rating")
        logger.info(f"Fetching reviews for: {brand} {name} (category: {category})")
        if search_results is None:
            search_results = await search_web(f"{search_query} {review_terms}")
            self._track_serper_cost()

        # Use enhanced formatter with retailer ratings
        search_context = self._format_review_search_results(
            search_results, retailer_ratings or []
        )

        # Extract reviews with category awareness
        reviews, usage = await extract_reviews(brand, name, variant, search_context, category=category)
        self._track_gpt_cost(usage)

        # Inject REAL retailer ratings as source_ratings (replaces any GPT-hallucinated data)
        if retailer_ratings:
            reviews["source_ratings"] = retailer_ratings

        # Cache result
        if reviews and not reviews.get("error"):
            set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)

        reviews["_cached"] = False
        return reviews
    
    def _format_search_results(self, results: Dict) -> str:
        """Format search results into context string."""
        if not results:
            return "No search results available."
        
        formatted = []
        
        # Organic results
        organic = results.get("organic", [])[:5]
        for i, r in enumerate(organic):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            formatted.append(f"{i+1}. {title}\n   {snippet}")
        
        # Shopping results (if available)
        shopping = results.get("shopping", [])[:3]
        if shopping:
            formatted.append("\n--- Shopping Results ---")
            for s in shopping:
                title = s.get("title", "")
                price = s.get("price", "")
                source = s.get("source", "")
                formatted.append(f"- {title}: {price} ({source})")
        
        return "\n".join(formatted)
    
    def _format_numbered_search_results(self, results: Dict) -> Tuple[str, List[str]]:
        """Format search results with [snippet_N] labels for GPT citation tracking.

        Returns:
            (formatted_context, raw_snippets) where raw_snippets[i] is the text
            of snippet_{i+1} for later citation verification.
        """
        if not results:
            return "No search results available.", []

        formatted = []
        raw_snippets = []

        organic = results.get("organic", [])[:5]
        for i, r in enumerate(organic):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            snippet_text = f"{title} - {snippet}"
            raw_snippets.append(snippet_text)
            formatted.append(f"[snippet_{i+1}] {title}\n   {snippet}")

        shopping = results.get("shopping", [])[:3]
        if shopping:
            formatted.append("\n--- Shopping Results ---")
            for s in shopping:
                title = s.get("title", "")
                price = s.get("price", "")
                source = s.get("source", "")
                formatted.append(f"- {title}: {price} ({source})")

        return "\n".join(formatted), raw_snippets

    def _calculate_freshness(self, product: Dict) -> str:
        """Calculate overall data freshness."""
        specs_cached = (product.get("specs") or {}).get("_cached", True)
        price_cached = (product.get("price") or {}).get("_cached", True)
        reviews_cached = (product.get("reviews") or {}).get("_cached", True)

        if not specs_cached and not price_cached:
            return "live"
        elif specs_cached and price_cached and reviews_cached:
            return "cached"
        else:
            return "mixed"

    def _build_fact_check(self, product: Dict) -> Dict:
        """Assemble fact_check object from per-field verification results.

        Pops internal _spec_confidence, _review_verification, _price_verification
        keys from the product dict and returns a clean fact_check summary.
        """
        spec_confidence = product.pop("_spec_confidence", {})
        review_verification = product.pop("_review_verification", {})
        price_verification = product.pop("_price_verification", {})

        specs_verified = sum(1 for v in spec_confidence.values() if v == "verified")
        specs_likely = sum(1 for v in spec_confidence.values() if v == "likely")
        specs_flagged = sum(1 for v in spec_confidence.values() if v == "flagged")
        specs_unverified = sum(1 for v in spec_confidence.values() if v == "unverified")

        price_verified = price_verification.get("price_verified", False)
        sentiment_consistent = review_verification.get("sentiment_consistent")

        # Overall confidence
        if specs_flagged > 0 or (sentiment_consistent is False):
            overall = "low"
        elif specs_unverified > specs_verified + specs_likely:
            overall = "medium"
        elif price_verified and (sentiment_consistent is True or sentiment_consistent is None):
            overall = "high"
        else:
            overall = "medium"

        return {
            "specs_verified": specs_verified,
            "specs_likely": specs_likely,
            "specs_flagged": specs_flagged,
            "specs_unverified": specs_unverified,
            "price_verified": price_verified,
            "price_deviation_pct": price_verification.get("deviation_pct"),
            "review_sentiment_consistent": sentiment_consistent,
            "review_rating_deviation": review_verification.get("deviation"),
            "overall_confidence": overall,
        }

    def _track_gpt_cost(self, usage: dict):
        """Track real GPT cost from token usage. gpt-4o-mini: $0.15/1M input, $0.60/1M output."""
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
        self.total_cost += cost
        self.api_calls += 1
        self.gpt_calls += 1

    def _track_serper_cost(self):
        """Track a single Serper API call ($0.001 per call)."""
        self.total_cost += 0.001
        self.api_calls += 1
        self.serper_calls += 1

    async def _get_verified_rating(self, full_name: str) -> Dict[str, Any]:
        """
        Get verified rating with minimal cost:
        1. Reuse shopping data from price fetch (FREE — Bahrain results)
        2. If no Tier 1/2 rating, ONE US shopping search for Amazon/BestBuy (1 credit)
        """
        empty = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

        # Step 1: Reuse shopping items already fetched during price extraction (FREE)
        shopping_items = self._shopping_items_cache.get(full_name, [])
        if shopping_items:
            logger.info(f"[RATING] Reusing {len(shopping_items)} shopping items from price fetch")
            result = self._extract_rating_from_shopping(full_name, shopping_items)
            if result and result.get("rating") and result.get("rating_source", {}).get("confidence") != "low":
                return result
            logger.info(f"[RATING] Bahrain data had no Tier 1/2 rating, trying US search")

        # Step 2: One US shopping search for better retailer ratings (1 credit)
        if not SERPER_API_KEY:
            return empty

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://google.serper.dev/shopping",
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                    json={"q": full_name, "gl": "us", "num": 10}
                )
                self._track_serper_cost()

                if response.status_code != 200:
                    logger.error(f"[RATING] US shopping search failed: {response.status_code}")
                    return empty

                us_items = response.json().get("shopping", [])
                if us_items:
                    result = self._extract_rating_from_shopping(full_name, us_items)
                    if result and result.get("rating"):
                        return result

        except Exception as e:
            logger.error(f"[RATING] US shopping search error: {e}")

        logger.info(f"[RATING] No rating found across all sources for: {full_name}")
        return empty

    def _extract_rating_from_shopping(self, product_name: str, shopping_items: List[Dict]) -> Dict[str, Any]:
        """Extract best matching rating from Serper Shopping results.

        Tiered fallback: Tier 1 (trusted) -> Tier 2 (known) -> Tier 3 (marketplace, >1000 reviews).
        Accessories and weak title matches are always rejected.
        """
        empty = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

        if not shopping_items:
            return empty

        p_words = self._normalize_words(product_name)
        tier1_candidates = []
        tier2_candidates = []
        tier3_candidates = []

        for item in shopping_items:
            rating = item.get("rating")
            if not rating:
                continue
            try:
                rating_val = float(rating)
            except (ValueError, TypeError):
                continue
            if not (0 < rating_val <= 5):
                continue

            title = item.get("title", "")
            source = item.get("source", "")

            # FILTER 1: Reject accessories
            if self._is_accessory(title):
                logger.debug(f"[RATING] Skipped accessory: '{title}'")
                continue

            # FILTER 2: Strict title match — all key words must appear in title
            if not self._strict_title_match(product_name, title):
                logger.debug(f"[RATING] Skipped weak title match: '{title}' for '{product_name}'")
                continue

            # FILTER 3: Number preservation — quantity must match
            if not self._numbers_match(product_name, title):
                logger.debug(f"[RATING] Skipped number mismatch: '{title}' for '{product_name}'")
                continue

            # Standard word-overlap score
            t_words = self._normalize_words(title)
            match_score = len(p_words & t_words) / len(p_words) if p_words else 0

            if match_score < 0.4:
                continue

            review_count = None
            for key in ["ratingCount", "reviewCount", "reviews"]:
                raw = item.get(key)
                if raw is not None:
                    try:
                        review_count = int(str(raw).replace(",", "").replace("+", ""))
                        break
                    except (ValueError, TypeError):
                        continue

            candidate = {
                "rating": rating_val,
                "review_count": review_count,
                "source": source,
                "link": item.get("link"),
                "title": title,
                "match_score": match_score,
            }

            # Sort into tier buckets
            tier = self._get_rating_tier(source)
            if tier == 1:
                tier1_candidates.append(candidate)
            elif tier == 2:
                tier2_candidates.append(candidate)
            else:
                # Tier 3: only keep if review_count > 1000 (real product, not single seller)
                if review_count and review_count > 1000:
                    tier3_candidates.append(candidate)
                else:
                    logger.debug(f"[RATING] Skipped low-count marketplace: '{source}' ({review_count} reviews)")

        # Check for Google aggregate consensus: if the same rating+reviewCount appears
        # across 3+ different sellers, it's Google's product-level aggregate — trustworthy
        all_candidates = tier1_candidates + tier2_candidates + tier3_candidates
        if not tier1_candidates and not tier2_candidates and all_candidates:
            from collections import Counter
            rating_counts = Counter((c["rating"], c["review_count"]) for c in all_candidates if c["review_count"])
            most_common, count = rating_counts.most_common(1)[0] if rating_counts else ((None, None), 0)
            if count >= 3:
                # Same rating across 3+ sellers = Google product aggregate, promote to verified
                consensus = [c for c in all_candidates if (c["rating"], c["review_count"]) == most_common]
                # Prefer sources with known retailer URLs (avoid Google fallback)
                consensus.sort(key=lambda c: (
                    self._has_retailer_url(c["source"]),  # Known retailer first
                    c["match_score"],                      # Then best title match
                ), reverse=True)
                best = consensus[0]
                logger.info(f"[RATING] ✓ CONSENSUS ({count} sellers): {best['rating']}/5 ({best['review_count']} reviews)")
                return {
                    "rating": round(best["rating"], 1),
                    "review_count": best["review_count"],
                    "rating_verified": True,
                    "rating_source": {
                        "name": "Google Shopping (product aggregate)",
                        "url": best.get("link") or self._build_retailer_url(best["source"], product_name),
                        "retrieved_at": datetime.now().isoformat() + "Z",
                        "extract_method": "google_shopping_consensus",
                        "confidence": "high"
                    }
                }

        # Tiered fallback: try Tier 1 first, then 2, then 3
        chosen_tier = None
        candidates = []
        if tier1_candidates:
            candidates = tier1_candidates
            chosen_tier = "tier1"
        elif tier2_candidates:
            candidates = tier2_candidates
            chosen_tier = "tier2"
        elif tier3_candidates:
            candidates = tier3_candidates
            chosen_tier = "tier3"

        if not candidates:
            logger.info(f"[RATING] No rating found across all tiers for '{product_name}'")
            return empty

        # Sort: highest review count first
        candidates.sort(key=lambda c: (c["review_count"] or 0, c["match_score"]), reverse=True)
        best = candidates[0]

        # Confidence label based on tier
        if chosen_tier == "tier3":
            confidence = "low"
            label = f"{best['source']} (marketplace rating)"
            verified = False
            logger.info(f"[RATING] ~ MARKETPLACE: {best['rating']}/5 ({best['review_count']} reviews) from {best['source']}")
        else:
            confidence = "high" if chosen_tier == "tier1" else "medium"
            label = f"{best['source']} via Google Shopping"
            verified = True
            logger.info(f"[RATING] ✓ VERIFIED: {best['rating']}/5 ({best['review_count']} reviews) from {best['source']}")

        return {
            "rating": round(best["rating"], 1),
            "review_count": best["review_count"],
            "rating_verified": verified,
            "rating_source": {
                "name": label,
                "url": best.get("link") or self._build_retailer_url(best["source"], product_name),
                "retrieved_at": datetime.now().isoformat() + "Z",
                "extract_method": "google_shopping",
                "confidence": confidence
            }
        }

    def _verify_spec_citations(self, specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
        """Verify GPT spec citations against actual search snippets.

        For numeric fields (ram, storage, battery, weight, etc.): requires exact number match.
        For text fields (os, connectivity, etc.): uses keyword overlap (50% threshold).

        Returns dict mapping spec_field -> confidence:
          'verified': citation matches snippet text
          'likely': citation provided but can't fully cross-check
          'unverified': no citation or citation doesn't match
        """
        confidence = {}
        for key, value in specs.items():
            if key.endswith("_source") or key.startswith("_") or key in ("brand", "model", "variant", "category"):
                continue
            source_key = f"{key}_source"
            source = specs.get(source_key)

            if not source or source == "training":
                confidence[key] = "unverified"
            elif source.startswith("snippet_"):
                try:
                    idx = int(source.split("_")[1]) - 1
                    if 0 <= idx < len(search_snippets):
                        snippet_text = search_snippets[idx].lower()
                        value_str = str(value).lower()

                        # Extract numbers from the spec value
                        spec_numbers = re.findall(r'\d+', value_str)

                        if key in NUMERIC_SPEC_FIELDS and spec_numbers:
                            # STRICT: all significant numbers must appear in snippet
                            # Filter to numbers >= 2 digits (skip "1", "2" etc. which match everywhere)
                            sig_numbers = [n for n in spec_numbers if len(n) >= 2]
                            if sig_numbers:
                                matches = sum(1 for n in sig_numbers if n in snippet_text)
                                confidence[key] = "verified" if matches == len(sig_numbers) else "likely"
                            else:
                                # Only small numbers — use keyword matching
                                terms = [t for t in value_str.split() if len(t) > 2]
                                if not terms:
                                    confidence[key] = "likely"
                                else:
                                    matches = sum(1 for t in terms if t in snippet_text)
                                    confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                        else:
                            # TEXT fields: keyword overlap matching (original behavior)
                            terms = [t for t in value_str.split() if len(t) > 2]
                            if not terms:
                                confidence[key] = "likely"
                            else:
                                matches = sum(1 for t in terms if t in snippet_text)
                                confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                    else:
                        confidence[key] = "unverified"
                except (ValueError, IndexError):
                    confidence[key] = "unverified"
            else:
                confidence[key] = "unverified"

        return confidence

    def _cross_validate_specs_with_shopping(self, specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
        """Cross-check spec values against Serper Shopping product titles/descriptions.

        Upgrades 'likely' to 'verified' if shopping data confirms.
        For numeric fields, requires ALL significant numbers to match (not just any).
        Returns dict mapping field -> 'verified' for confirmed fields.
        """
        if not shopping_items:
            return {}

        # Combine all shopping titles into one searchable text
        shopping_text = " ".join(
            f"{item.get('title', '')} {item.get('description', '')}"
            for item in shopping_items
        ).lower()

        flags = {}
        checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
        for key in checkable:
            value = specs.get(key)
            if not value or value == "N/A":
                continue
            value_str = str(value).lower()
            # Extract significant numbers (2+ digits) from spec value
            spec_numbers = [n for n in re.findall(r'\d+', value_str) if len(n) >= 2]
            if spec_numbers:
                # ALL significant numbers must appear in shopping text
                all_found = all(n in shopping_text for n in spec_numbers)
                if all_found:
                    flags[key] = "verified"
            else:
                # Non-numeric: check key words
                terms = [t for t in value_str.split() if len(t) > 2]
                found = sum(1 for t in terms if t in shopping_text)
                if terms and found >= len(terms) * 0.5:
                    flags[key] = "verified"

        return flags

    def _verify_review_sentiment(self, reviews: Dict, source_ratings: List[Dict]) -> Dict:
        """Cross-check GPT review sentiment against real Serper ratings.

        Returns:
          sentiment_consistent: bool or None (None if insufficient data)
          gpt_rating: float or None
          serper_avg_rating: float or None
          deviation: float or None
        """
        gpt_rating = reviews.get("average_rating")
        if not source_ratings or gpt_rating is None:
            return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

        # Calculate weighted average from source_ratings
        total_weight = 0
        weighted_sum = 0
        for sr in source_ratings:
            rating = sr.get("rating")
            count = sr.get("review_count", 1) or 1
            if rating and isinstance(rating, (int, float)):
                weighted_sum += rating * count
                total_weight += count

        if total_weight == 0:
            return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

        serper_avg = round(weighted_sum / total_weight, 2)
        deviation = abs(gpt_rating - serper_avg)
        consistent = deviation <= 0.8  # Allow 0.8 point tolerance

        return {
            "sentiment_consistent": consistent,
            "gpt_rating": gpt_rating,
            "serper_avg_rating": serper_avg,
            "deviation": round(deviation, 2)
        }

    def _verify_price(self, price: Dict, shopping_items: List[Dict]) -> Dict:
        """Cross-check final price against Serper Shopping prices.

        Returns:
          price_verified: bool
          deviation_pct: float or None
          source_count: int
        """
        if not price or not shopping_items:
            return {"price_verified": price is not None and not (price or {}).get("estimated", False), "deviation_pct": None, "source_count": 0}

        final_amount = price.get("amount")
        if not final_amount:
            return {"price_verified": False, "deviation_pct": None, "source_count": 0}

        # Collect valid prices from shopping items
        shopping_prices = []
        for item in shopping_items:
            p = item.get("price")
            if isinstance(p, (int, float)) and p > 0:
                shopping_prices.append(p)
            elif isinstance(p, str):
                nums = re.findall(r'[\d.]+', p.replace(',', ''))
                if nums:
                    try:
                        shopping_prices.append(float(nums[0]))
                    except ValueError:
                        pass

        if not shopping_prices:
            return {"price_verified": not price.get("estimated", False), "deviation_pct": None, "source_count": 0}

        median = sorted(shopping_prices)[len(shopping_prices) // 2]
        deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None

        return {
            "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),
            "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
            "source_count": len(shopping_prices)
        }

    @staticmethod
    def _clean_specs(specs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean specs for display: remove meta keys, _source citation fields, replace None with N/A."""
        if not specs or not isinstance(specs, dict):
            return {}

        meta_keys = {"brand", "model", "variant", "category", "_cached", "error"}

        cleaned = {}
        for key, value in specs.items():
            if key in meta_keys:
                continue
            # Strip _source citation fields (used for fact-checking, not displayed)
            if key.endswith("_source"):
                continue
            # Strip internal keys
            if key.startswith("_"):
                continue
            if value is None or value == "" or value == "null" or (isinstance(value, str) and "or null" in value.lower()):
                cleaned[key] = "N/A"
            elif isinstance(value, list):
                cleaned[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                cleaned[key] = json.dumps(value)
            else:
                cleaned[key] = str(value) if not isinstance(value, str) else value

        return cleaned


# ============================================
# GCC REGIONAL PRICING
# ============================================

async def get_regional_prices(
    brand: str,
    name: str,
    variant: Optional[str],
    search_query: str
) -> Dict[str, Any]:
    """Get prices across all GCC regions in parallel."""
    service = StructuredComparisonService()
    
    # Fetch all regions in parallel
    tasks = []
    for region in GCC_REGIONS.keys():
        tasks.append(service._get_price(brand, name, variant, region, search_query))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Build regional prices dict
    regional = {}
    best_price = None
    best_region = None
    
    for region, result in zip(GCC_REGIONS.keys(), results):
        if isinstance(result, Exception):
            regional[region] = None
            continue
        
        regional[region] = result
        
        if result and result.get("amount"):
            # Convert to common currency (BHD) for comparison
            amount_bhd = _convert_to_bhd(result["amount"], result.get("currency", "BHD"))
            if best_price is None or amount_bhd < best_price:
                best_price = amount_bhd
                best_region = region
    
    return {
        "regional_prices": regional,
        "best_region": best_region,
        "best_price_bhd": best_price
    }


def _convert_to_bhd(amount: float, currency: str) -> float:
    """Convert amount to BHD (approximate rates)."""
    if not currency:
        return amount
    rates = {
        "BHD": 1.0,
        "SAR": 0.1,      # 1 SAR ≈ 0.10 BHD
        "AED": 0.1,      # 1 AED ≈ 0.10 BHD
        "KWD": 1.22,     # 1 KWD ≈ 1.22 BHD
        "QAR": 0.1,      # 1 QAR ≈ 0.10 BHD
        "OMR": 0.98,     # 1 OMR ≈ 0.98 BHD
        "USD": 0.377,    # 1 USD ≈ 0.377 BHD
        "EUR": 0.41,     # 1 EUR ≈ 0.41 BHD
        "GBP": 0.47,     # 1 GBP ≈ 0.47 BHD
    }
    return amount * rates.get(currency.upper(), 1.0)


# ============================================
# SINGLETON INSTANCE
# ============================================

_service_instance = None

def get_comparison_service() -> StructuredComparisonService:
    """Get or create the comparison service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = StructuredComparisonService()
    return _service_instance
