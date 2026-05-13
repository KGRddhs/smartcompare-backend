"""Structured Comparison Service - Main orchestrator for product comparisons.

Delegates to focused modules:
- price_service: all price fetching, extraction, currency conversion
- rating_service: verified ratings from shopping data
- review_service: review fetching, cleaning, citation cleanup
- fact_check_service: spec/price/review cross-validation
- response_builder: builds the full response dict
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
from urllib.parse import urlparse, quote_plus

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
    was_cohort_block_active,
    GCC_REGIONS
)
from app.services.database_service import get_user_demographics
from app.services.serper_service import search_product_prices, search_price_organic, search_web
from app.services.cache_service import get_cached, set_cached
from app.services.drug_database_service import find_matching_drugs, format_drug_context
from app.services.scoring_service import get_scoring_service, MISSING_SCORE
from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed,
)
from app.services import firecrawl_service, scrapedo_service

# Import from new modules
from app.services.price_service import (
    _convert_to_bhd,
    _convert_gpt_price_currency,
    validate_price_query,
    validate_scrape_url,
    is_counterfeit_listing,
    is_accessory,
    is_high_value_query,
    is_luxury_brand,
    is_supplement_query,
    extract_domain,
    parse_price_string,
    detect_currency,
    normalize_words,
    numbers_match,
    strict_title_match,
    get_retailer_score,
    has_retailer_url,
    build_retailer_url,
    sanitize_gpt_price,
    get_official_domain,
    extract_price_from_shopping,
    extract_jsonld_price,
    extract_price_from_html,
    curl_fetch_html,
    fetch_page_price,
    fetch_iherb_price,
    fetch_pharmacy_price,
    # Constants re-exported for backward compat
    MODEL_VARIANT_PATTERN,
    PRICE_CACHE_TTL,
    RETAILER_TIERS,
    DEFAULT_RETAILER_SCORE,
    RETAILER_SEARCH_URLS,
    ACCESSORY_KEYWORDS,
    HIGH_VALUE_KEYWORDS,
    COUNTERFEIT_KEYWORDS,
    LUXURY_BRAND_KEYWORDS,
    OFFICIAL_BRAND_DOMAINS,
    AUTHORIZED_LUXURY_RETAILERS,
    GCC_LUXURY_RETAILERS,
    SUPPLEMENT_KEYWORDS,
    MANUFACTURER_BRAND_WORDS,
    PHARMACY_DOMAINS,
    CURRENCY_SYMBOLS,
    CURRENCY_CODES,
    PAGE_SCRAPE_TIMEOUT,
    TIER_15_BUDGET_TIMEOUT,
    ENABLE_PAGE_SCRAPE,
)
from app.services.rating_service import (
    get_rating_tier,
    collect_retailer_ratings,
    extract_rating_from_shopping,
    get_verified_rating,
    RATING_TIER_1,
    RATING_TIER_2,
    RATING_TIER_3,
)
from app.services.review_service import (
    clean_review_content,
    clean_review_citations,
    format_review_search_results,
    get_reviews as _get_reviews_standalone,
    REVIEWS_CACHE_TTL,
    CATEGORY_REVIEW_TERMS,
    GARBAGE_PATTERNS,
    NEGATIVE_INDICATORS,
    POSITIVE_INDICATORS,
)
from app.services.fact_check_service import (
    verify_spec_citations,
    cross_validate_specs_with_shopping,
    verify_review_sentiment,
    verify_price,
    build_fact_check,
    NUMERIC_SPEC_FIELDS,
)
from app.services.response_builder import (
    build_comparison_response,
    derive_rating_from_scores,
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

logger = logging.getLogger(__name__)

# Cache TTLs
SPECS_CACHE_TTL = 7 * 24 * 60 * 60    # 7 days


class StructuredComparisonService:
    """Main service for structured product comparisons.

    Orchestrates: parse -> fetch -> score -> compare -> build response.
    Delegates price/rating/review/fact-check to focused modules.
    """

    # Class-level constants preserved for backward compat (tests reference self.CONSTANT)
    ACCESSORY_KEYWORDS = ACCESSORY_KEYWORDS
    HIGH_VALUE_KEYWORDS = HIGH_VALUE_KEYWORDS
    COUNTERFEIT_KEYWORDS = COUNTERFEIT_KEYWORDS
    LUXURY_BRAND_KEYWORDS = LUXURY_BRAND_KEYWORDS
    OFFICIAL_BRAND_DOMAINS = OFFICIAL_BRAND_DOMAINS
    AUTHORIZED_LUXURY_RETAILERS = AUTHORIZED_LUXURY_RETAILERS
    GCC_LUXURY_RETAILERS = GCC_LUXURY_RETAILERS
    SUPPLEMENT_KEYWORDS = SUPPLEMENT_KEYWORDS
    MANUFACTURER_BRAND_WORDS = MANUFACTURER_BRAND_WORDS
    PHARMACY_DOMAINS = PHARMACY_DOMAINS
    CATEGORY_REVIEW_TERMS = CATEGORY_REVIEW_TERMS
    GARBAGE_PATTERNS = GARBAGE_PATTERNS
    NEGATIVE_INDICATORS = NEGATIVE_INDICATORS
    POSITIVE_INDICATORS = POSITIVE_INDICATORS
    RATING_TIER_1 = RATING_TIER_1
    RATING_TIER_2 = RATING_TIER_2
    RATING_TIER_3 = RATING_TIER_3
    CURRENCY_SYMBOLS = CURRENCY_SYMBOLS
    CURRENCY_CODES = CURRENCY_CODES
    PAGE_SCRAPE_TIMEOUT = PAGE_SCRAPE_TIMEOUT
    TIER_15_BUDGET_TIMEOUT = TIER_15_BUDGET_TIMEOUT

    def __init__(self):
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}

    # ============================================
    # Static method wrappers for backward compat
    # (tests call svc._is_luxury_brand() etc.)
    # ============================================

    @staticmethod
    def _is_counterfeit_listing(title: str) -> bool:
        return is_counterfeit_listing(title)

    @staticmethod
    def _is_accessory(title: str) -> bool:
        return is_accessory(title)

    @staticmethod
    def _is_high_value_query(product_name: str) -> bool:
        return is_high_value_query(product_name)

    @staticmethod
    def _is_luxury_brand(product_name: str) -> bool:
        return is_luxury_brand(product_name)

    @staticmethod
    def _is_supplement_query(product_name: str) -> bool:
        return is_supplement_query(product_name)

    @staticmethod
    def _validate_price_query(brand: str, name: str, region: str) -> bool:
        return validate_price_query(brand, name, region)

    @staticmethod
    def _validate_scrape_url(url: str) -> bool:
        return validate_scrape_url(url)

    @staticmethod
    def _extract_domain(url: str) -> str:
        return extract_domain(url)

    @staticmethod
    def _parse_price_string(price_str: str) -> Optional[float]:
        return parse_price_string(price_str)

    @staticmethod
    def _detect_currency(price_str: str) -> Optional[str]:
        return detect_currency(price_str)

    @staticmethod
    def _normalize_words(text: str) -> set:
        return normalize_words(text)

    @staticmethod
    def _numbers_match(product_name: str, title: str) -> bool:
        return numbers_match(product_name, title)

    @staticmethod
    def _strict_title_match(product_name: str, title: str) -> bool:
        return strict_title_match(product_name, title)

    @staticmethod
    def _get_retailer_score(retailer_name: str) -> float:
        return get_retailer_score(retailer_name)

    @staticmethod
    def _sanitize_gpt_price(price: Optional[Dict]) -> None:
        sanitize_gpt_price(price)

    @staticmethod
    def _convert_gpt_price_currency(price: Optional[Dict], target_currency: str) -> None:
        _convert_gpt_price_currency(price, target_currency)

    @staticmethod
    def _extract_jsonld_price(html: str, brand: str, expected_currency: str) -> Optional[Dict[str, Any]]:
        return extract_jsonld_price(html, brand, expected_currency)

    @staticmethod
    def _get_rating_tier(source: str) -> int:
        return get_rating_tier(source)

    @staticmethod
    def _clean_specs(specs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean specs for display."""
        if not specs or not isinstance(specs, dict):
            return {}
        meta_keys = {"brand", "model", "variant", "category", "_cached", "error"}
        cleaned = {}
        for key, value in specs.items():
            if key in meta_keys:
                continue
            if key.endswith("_source"):
                continue
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

    def _has_retailer_url(self, source: str) -> bool:
        return has_retailer_url(source)

    def _build_retailer_url(self, source: str, product_name: str) -> Optional[str]:
        return build_retailer_url(source, product_name)

    def _get_official_domain(self, product_name: str) -> Optional[str]:
        return get_official_domain(product_name)

    def _derive_rating_from_scores(self, overall_score: float) -> float:
        return derive_rating_from_scores(overall_score)

    # Delegated methods
    def _clean_review_content(self, reviews: dict) -> dict:
        return clean_review_content(reviews)

    def _clean_review_citations(self, reviews: dict, search_results: list) -> dict:
        return clean_review_citations(reviews, search_results)

    def _verify_spec_citations(self, specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
        return verify_spec_citations(specs, search_snippets)

    def _cross_validate_specs_with_shopping(self, specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
        return cross_validate_specs_with_shopping(specs, shopping_items)

    def _verify_review_sentiment(self, reviews: Dict, source_ratings: List[Dict]) -> Dict:
        return verify_review_sentiment(reviews, source_ratings)

    def _verify_price(self, price: Dict, shopping_items: List[Dict]) -> Dict:
        return verify_price(price, shopping_items)

    def _build_fact_check(self, product: Dict) -> Dict:
        return build_fact_check(product)

    def _extract_price_from_shopping(self, product_name: str, shopping_items: List[Dict], currency: str) -> Optional[Dict[str, Any]]:
        return extract_price_from_shopping(product_name, shopping_items, currency)

    def _extract_price_from_html(self, html: str, product_name: str, currency: str, domain: str, url: str) -> Optional[Dict[str, Any]]:
        return extract_price_from_html(html, product_name, currency, domain, url)

    def _extract_rating_from_shopping(self, product_name: str, shopping_items: List[Dict]) -> Dict[str, Any]:
        return extract_rating_from_shopping(product_name, shopping_items)

    def _collect_retailer_ratings(self, full_name: str) -> List[Dict[str, Any]]:
        return collect_retailer_ratings(full_name, self._shopping_items_cache)

    async def _fetch_page_price(self, url: str, product_name: str, currency: str = "BHD") -> Optional[Dict[str, Any]]:
        """Fetch a product page via curl_cffi and extract price from structured data.
        Kept as instance method so tests can patch _curl_fetch_html via patch.object."""
        if not ENABLE_PAGE_SCRAPE:
            return None
        domain = urlparse(url).netloc.replace("www.", "")
        html = await self._curl_fetch_html(url)
        if html:
            price = extract_price_from_html(html, product_name, currency, domain, url)
            if price:
                return price
            return {"_got_html": True}
        return None

    async def _curl_fetch_html(self, url: str) -> Optional[str]:
        return await curl_fetch_html(url)

    async def _fetch_iherb_price(self, query: str, brand: str, full_name: str, region_code: str, currency: str) -> Optional[Dict[str, Any]]:
        return await fetch_iherb_price(query, brand, full_name, region_code, currency)

    async def _fetch_pharmacy_price(self, serper_organic: List[Dict], brand: str, full_name: str, currency: str) -> Optional[Dict[str, Any]]:
        return await fetch_pharmacy_price(serper_organic, brand, full_name, currency, track_serper_cost_fn=self._track_serper_cost)

    async def _try_pharmacy_urls(self, pharmacy_urls: List[Tuple[str, str]], brand: str, currency: str) -> Optional[Dict[str, Any]]:
        from app.services.price_service import _try_pharmacy_urls
        return await _try_pharmacy_urls(pharmacy_urls, brand, currency)

    # ============================================
    # Main entry points
    # ============================================

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
        """Main entry point for text-based comparisons."""
        start_time = datetime.now()
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}

        try:
            # Step 1: Parse the query (or use vision products directly)
            if vision_products and len(vision_products) >= 2:
                products = []
                for vp in vision_products[:2]:
                    brand = vp.get("brand", "Unknown")
                    vname = vp.get("name", "Unknown Product")
                    full = f"{brand} {vname}".strip()
                    category = "supplements" if is_supplement_query(full) else "other"
                    products.append({
                        "brand": brand, "name": vname,
                        "variant": vp.get("size_or_count"),
                        "category": category, "search_query": full, "_vision": True,
                    })
                parsed = {}
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

                products = parsed["products"][:2]

            # Determine category
            detected_category = products[0].get("category", "other")
            category_switched = False
            original_category = None
            if selected_category and selected_category != detected_category:
                category_switched = True
                original_category = selected_category
            category_used = detected_category

            # Step 2: Fetch data for each product (parallel)
            product_data = await asyncio.gather(
                self._fetch_product_data(products[0], region, include_specs, include_reviews, nocache),
                self._fetch_product_data(products[1], region, include_specs, include_reviews, nocache)
            )

            # Fetch behavioral profile + demographics_profile if user is logged in
            behavior_profile = None
            demographics_profile = None
            if user_id:
                behavior_profile, demographics_profile = await asyncio.gather(
                    self._fetch_behavior_profile(user_id),
                    get_user_demographics(user_id),
                )

            # Step 3: Compute deterministic scores
            scoring_service = get_scoring_service()
            scoring_result = scoring_service.compute_scores(
                product_data, preferences=user_preferences, behavior_profile=behavior_profile,
            )
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in product_data
            ]
            scores_summary = scoring_service.build_scores_summary(scoring_result, product_names)

            # Step 4: Generate comparison (passes demographics_profile so the cohort
            # priors block in extraction_service can render when conditions are met).
            comparison, usage = await generate_comparison(
                product_data[0], product_data[1], region,
                parsed.get("comparison_type", "value") if not vision_products else "value",
                user_preferences=user_preferences,
                scores_summary=scores_summary, category=detected_category,
                demographics_profile=demographics_profile,
            )
            self._track_gpt_cost(usage)

            # Trust validation
            from app.services.trust_validation_service import validate_verdict
            verdict_validation = validate_verdict(comparison, scoring_result, detected_category)

            # Extract pros/cons
            if include_pros_cons:
                product_data[0]["pros_cons"] = {
                    "pros": comparison.pop("product_0_pros", []),
                    "cons": comparison.pop("product_0_cons", []),
                }
                product_data[1]["pros_cons"] = {
                    "pros": comparison.pop("product_1_pros", []),
                    "cons": comparison.pop("product_1_cons", []),
                }

            # Compute value badges
            for i, product in enumerate(product_data):
                value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
                price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
                product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)

            # Compute tradeoffs and confidence
            tradeoffs = scoring_service.compute_tradeoff_pairs(
                scoring_result.get("dimension_winners", {}), product_names, scoring_result.get("winner_index", 0)
            )
            from_cache = not nocache
            confidence = scoring_service.compute_confidence(
                product_data, shopping_count=len(self._shopping_items_cache), cached=from_cache
            )

            elapsed = (datetime.now() - start_time).total_seconds()

            result = build_comparison_response(
                product_data=product_data,
                comparison=comparison,
                scoring_result=scoring_result,
                product_names=product_names,
                tradeoffs=tradeoffs,
                confidence=confidence,
                verdict_validation=verdict_validation,
                user_preferences=user_preferences,
                from_cache=from_cache,
                query=query,
                region=region,
                category_used=category_used,
                category_switched=category_switched,
                original_category=original_category,
                total_cost=self.total_cost,
                api_calls=self.api_calls,
                gpt_calls=self.gpt_calls,
                serper_calls=self.serper_calls,
                elapsed_seconds=elapsed,
            )

            # Record whether the cohort priors block was active for this verdict.
            # Read by text_routes to write a `cohort_injected` user_events row
            # (powers vw_cohort_feedback_lift).
            if isinstance(result.get("metadata"), dict):
                result["metadata"]["cohort_injected"] = was_cohort_block_active(
                    demographics_profile
                )

            # Fire-and-forget: update behavioral profile
            if user_id:
                asyncio.create_task(self._update_behavior_profile(user_id))

            return result

        except Exception as e:
            logger.error(f"Comparison error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "total_cost": self.total_cost}

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
        """Async generator version of compare_from_text that yields partial results."""
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
                    category = "supplements" if is_supplement_query(full) else "other"
                    products.append({
                        "brand": brand, "name": vname,
                        "variant": vp.get("size_or_count"),
                        "category": category, "search_query": full, "_vision": True,
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

            # Step 2: Fetch product data
            yield ("status", {"message": "Fetching specs and prices...", "progress": 20})

            product_data = await asyncio.gather(
                self._fetch_product_data(products[0], region, include_specs, include_reviews, nocache),
                self._fetch_product_data(products[1], region, include_specs, include_reviews, nocache),
            )

            # Yield specs
            yield ("specs", {
                "products": [
                    {"brand": pd.get("brand"), "name": pd.get("name"), "specs": pd.get("specs"), "fact_check": pd.get("fact_check")}
                    for pd in product_data
                ]
            })

            # Yield prices
            scoring_service = get_scoring_service()
            prices_payload = {}
            for i, pd in enumerate(product_data):
                key = f"product_{i}"
                prices_payload[key] = {
                    "brand": pd.get("brand"), "name": pd.get("name"),
                    "price": pd.get("price"), "best_price": pd.get("best_price"),
                    "currency": pd.get("currency"), "retailer": pd.get("retailer"),
                }
            yield ("prices", prices_payload)

            # Yield reviews
            yield ("status", {"message": "Analyzing reviews...", "progress": 50})
            yield ("reviews", {
                "products": [
                    {
                        "brand": pd.get("brand"), "name": pd.get("name"),
                        "rating": pd.get("rating"), "review_count": pd.get("review_count"),
                        "rating_verified": pd.get("rating_verified"),
                        "rating_source": pd.get("rating_source"),
                        "review_summary": pd.get("reviews", {}).get("review_summary", {
                            "overall_sentiment": "mixed", "consensus": "",
                            "highlights": [], "review_volume": "minimal", "agreement_level": "moderate",
                        }),
                    }
                    for pd in product_data
                ]
            })

            # Bundle E Task 2.5 § Decision 8 — first_paint marks "all core
            # dimensions ready, frontend can paint the UI." Fires after
            # specs+prices+reviews land; before scoring/verdict.
            yield ("first_paint", {
                "products": [
                    {"brand": pd.get("brand"), "name": pd.get("name")}
                    for pd in product_data
                ]
            })

            # Fetch behavioral profile + demographics_profile
            behavior_profile = None
            demographics_profile = None
            if user_id:
                behavior_profile, demographics_profile = await asyncio.gather(
                    self._fetch_behavior_profile(user_id),
                    get_user_demographics(user_id),
                )

            # Step 3: Compute scores
            scoring_result = scoring_service.compute_scores(
                product_data, preferences=user_preferences, behavior_profile=behavior_profile,
            )
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in product_data
            ]
            scores_summary = scoring_service.build_scores_summary(scoring_result, product_names)

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

            # Step 4: Generate verdict (passes demographics_profile so the cohort
            # priors block in extraction_service can render when conditions are met).
            yield ("status", {"message": "Generating verdict...", "progress": 80})
            comparison, usage = await generate_comparison(
                product_data[0], product_data[1], region,
                parsed.get("comparison_type", "value") if not vision_products else "value",
                user_preferences=user_preferences,
                scores_summary=scores_summary, category=detected_category,
                demographics_profile=demographics_profile,
            )
            self._track_gpt_cost(usage)

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

            # Compute value badges
            for i, product in enumerate(product_data):
                value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
                price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
                product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)

            # Compute tradeoffs
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
                "comparison": comparison,
                "winner_index": winner_index,
                "recommendation": comparison.get("winner_reason", ""),
                "key_differences": [],
            })

            # Step 5: Build complete response
            elapsed = (datetime.now() - start_time).total_seconds()

            complete_response = build_comparison_response(
                product_data=product_data,
                comparison=comparison,
                scoring_result=scoring_result,
                product_names=product_names,
                tradeoffs=tradeoffs,
                confidence=confidence,
                verdict_validation=verdict_validation,
                user_preferences=user_preferences,
                from_cache=from_cache,
                query=query,
                region=region,
                category_used=category_used,
                category_switched=category_switched,
                original_category=original_category,
                total_cost=self.total_cost,
                api_calls=self.api_calls,
                gpt_calls=self.gpt_calls,
                serper_calls=self.serper_calls,
                elapsed_seconds=elapsed,
            )

            # Mark cohort_injected on the complete response so route handler can
            # log a `cohort_injected` user_events row (powers vw_cohort_feedback_lift).
            if isinstance(complete_response.get("metadata"), dict):
                complete_response["metadata"]["cohort_injected"] = was_cohort_block_active(
                    demographics_profile
                )

            # Fire-and-forget: update behavioral profile
            if user_id:
                asyncio.create_task(self._update_behavior_profile(user_id))

            # Bundle E Task 2.3 § Decision 8 — settle_complete closes the
            # settle window; no further settle_update events can fire
            # after this. Existing `complete` event is preserved
            # immediately after for backward-compat with current EAS
            # builds that listen on `complete`.
            yield ("settle_complete", complete_response)
            yield ("complete", complete_response)

        except Exception as e:
            logger.error(f"Streaming comparison error: {e}", exc_info=True)
            yield ("error", {
                "success": False, "error": str(e), "total_cost": self.total_cost,
            })

    # ============================================
    # Internal orchestration methods
    # ============================================

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

            comparisons = supabase.table("comparisons").select("category_used, products, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
            feedback = supabase.table("comparison_feedback").select("useful").eq("user_id", user_id).execute()
            events = supabase.table("user_events").select("event_type, metadata").eq("user_id", user_id).order("created_at", desc=True).limit(200).execute()

            profile = await behavior_service.build_behavior_profile(
                comparisons.data or [], feedback.data or [], events.data or [],
            )
            supabase.table("users").update({"behavior_profile": profile}).eq("id", user_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update behavior profile: {e}")

    async def _fetch_product_data(
        self, product_info: Dict, region: str, include_specs: bool, include_reviews: bool, nocache: bool = False
    ) -> Dict[str, Any]:
        """Fetch all data for a single product."""
        brand = product_info.get("brand", "")
        name = product_info.get("name", "")
        variant = product_info.get("variant")
        category = product_info.get("category", "other")
        search_query = product_info.get("search_query", f"{brand} {name} {variant or ''}")
        is_vision = product_info.get("_vision", False)

        if is_vision:
            full_name = search_query
            display_name = full_name
        else:
            full_name = f"{brand} {name} {variant or ''}".strip()
            display_name = name

        result = {
            "brand": brand, "name": display_name, "full_name": full_name,
            "variant": variant, "category": category, "query": search_query,
        }

        # === Unified web search ===
        unified_search = None
        if include_specs or include_reviews:
            specs_key = get_specs_cache_key(brand, name, variant)
            reviews_key = get_reviews_cache_key(brand, name, variant)
            specs_hit = get_cached(specs_key) if not nocache else None
            reviews_hit = get_cached(reviews_key) if not nocache else None
            if (include_specs and not specs_hit) or (include_reviews and not reviews_hit):
                unified_search = await search_web(
                    f"{search_query} specifications reviews price", num_results=10
                )
                self._track_serper_cost()

        # === Phase 1: specs + price (parallel) ===
        phase1_tasks = []
        phase1_keys = []

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

        if result.get("price"):
            result["best_price"] = result["price"].get("amount")
            result["currency"] = result["price"].get("currency", "BHD")
            result["retailer"] = result["price"].get("retailer")

        # Fact-check: verify spec citations
        if result.get("specs") and isinstance(result["specs"], dict):
            raw_specs = result["specs"]
            search_snippets = raw_specs.pop("_search_snippets", [])
            citation_confidence = verify_spec_citations(raw_specs, search_snippets)
            shopping_items = self._shopping_items_cache.get(full_name, [])
            shopping_flags = cross_validate_specs_with_shopping(raw_specs, shopping_items)
            spec_confidence = {}
            for key in citation_confidence:
                if shopping_flags.get(key) == "verified":
                    spec_confidence[key] = "verified"
                else:
                    spec_confidence[key] = citation_confidence[key]
            result["_spec_confidence"] = spec_confidence

        if result.get("specs"):
            result["specs"] = self._clean_specs(result["specs"])

        # === Phase 2: reviews + verified rating (parallel) ===
        retailer_ratings = collect_retailer_ratings(full_name, self._shopping_items_cache)

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

        # Fallback: use GPT-extracted average_rating
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
                            "name": "Aggregated from reviews", "url": None,
                            "extract_method": "gpt_review_aggregate", "confidence": "low",
                        }
                except (ValueError, TypeError):
                    pass

        # Inject verified rating into reviews
        if result.get("reviews") and isinstance(result["reviews"], dict) and rating_data.get("rating"):
            result["reviews"]["verified_rating"] = {
                "rating": rating_data["rating"],
                "review_count": rating_data.get("review_count"),
                "source": rating_data.get("rating_source", {}).get("name"),
                "verified": rating_data.get("rating_verified", False),
            }

        if rating_data.get("expert_pros"):
            result["expert_pros"] = rating_data["expert_pros"]
        if rating_data.get("expert_cons"):
            result["expert_cons"] = rating_data["expert_cons"]

        # === Fact-checking ===
        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["_review_verification"] = verify_review_sentiment(result["reviews"], retailer_ratings)
        else:
            result["_review_verification"] = {"sentiment_consistent": None, "gpt_rating": None, "serper_avg_rating": None, "deviation": None}

        shopping_items = self._shopping_items_cache.get(full_name, [])
        result["_price_verification"] = verify_price(result.get("price"), shopping_items)

        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["reviews"] = clean_review_content(result["reviews"])

        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["reviews"] = clean_review_citations(
                result["reviews"],
                unified_search.get("organic", []) if unified_search else []
            )

        result["fact_check"] = build_fact_check(result)
        result["data_freshness"] = self._calculate_freshness(result)

        return result

    async def _get_specs(
        self, brand: str, name: str, variant: Optional[str], category: str,
        search_query: str, nocache: bool = False, search_results: Optional[Dict] = None, drug_context: str = ""
    ) -> Dict[str, Any]:
        """Get specs with caching (L1: Redis, L2: DB)."""
        cache_key = get_specs_cache_key(brand, name, variant)
        cached = get_cached(cache_key) if not nocache else None
        if cached:
            cached["_cached"] = True
            return cached

        # L2: Check DB before API call
        if not nocache:
            from app.services.product_data_service import get_cached_specs
            db_specs = await get_cached_specs(cache_key)
            if db_specs:
                set_cached(cache_key, db_specs, SPECS_CACHE_TTL)
                db_specs["_cached"] = True
                db_specs["_cache_source"] = "db"
                return db_specs

        if search_results is None:
            search_results = await search_web(f"{search_query} specifications features")
            self._track_serper_cost()

        search_context, raw_snippets = self._format_numbered_search_results(search_results)
        specs, usage = await extract_specs(brand, name, variant, category, search_context, drug_context=drug_context)
        self._track_gpt_cost(usage)

        if specs and not specs.get("error"):
            set_cached(cache_key, specs, SPECS_CACHE_TTL)
            # Save to L2 DB (fire-and-forget)
            from app.services.product_data_service import save_specs
            asyncio.create_task(save_specs(cache_key, brand, name, variant, category, specs))

        specs["_search_snippets"] = raw_snippets
        specs["_cached"] = False
        return specs

    async def _get_price(
        self, brand: str, name: str, variant: Optional[str], region: str,
        search_query: str, nocache: bool = False, category: str = "other"
    ) -> Dict[str, Any]:
        """Get price with 3-tier strategy."""
        if not validate_price_query(brand, name, region):
            return {"amount": 0, "currency": "BHD", "estimated": True, "source_method": "validation_rejected"}

        cache_key = get_price_cache_key(brand, name, variant, region)
        cached = get_cached(cache_key) if not nocache else None
        if cached:
            cached["_cached"] = True
            return cached

        # L2: Check DB before tier cascade
        if not nocache:
            from app.services.product_data_service import get_cached_price
            db_price = await get_cached_price(cache_key, region)
            if db_price:
                set_cached(cache_key, db_price, PRICE_CACHE_TTL)
                db_price["_cached"] = True
                db_price["_cache_source"] = "db"
                return db_price

        region_info = GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])
        currency = region_info["currency"]
        if variant and variant.lower() in name.lower():
            full_name = f"{brand} {name}".strip()
        else:
            full_name = f"{brand} {name} {variant or ''}".strip()

        is_supplement = (category == "supplements") or is_supplement_query(full_name)

        # --- Tier 1: Direct Serper Shopping extraction ---
        if is_supplement:
            search_results = {"shopping": [], "organic": []}
            shopping_items = []
            self._shopping_items_cache[full_name] = []
        else:
            search_results = await search_product_prices(search_query, region_info["code"])
            self._track_serper_cost()
            shopping_items = search_results.get("shopping", [])
            self._shopping_items_cache[full_name] = shopping_items

        tier3_estimate = None

        price = extract_price_from_shopping(full_name, shopping_items, currency)
        if price and price.get("amount"):
            if price.get("retailer_score", 0) >= 1.0:
                pass  # Official domain — skip sanity check
            elif (is_high_value_query(full_name) or is_luxury_brand(full_name)) and price.get("retailer_score", 0) < 1.0:
                if is_luxury_brand(full_name):
                    high_threshold, low_threshold = 1.8, 0.6
                else:
                    high_threshold, low_threshold = 2.0, 0.5
                tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
                self._track_gpt_cost(usage)
                sanitize_gpt_price(tier3_estimate)
                _convert_gpt_price_currency(tier3_estimate, currency)
                if tier3_estimate and tier3_estimate.get("amount"):
                    tier1_bhd = _convert_to_bhd(price["amount"], currency)
                    tier3_bhd = _convert_to_bhd(tier3_estimate["amount"], currency)
                    if tier1_bhd > tier3_bhd * high_threshold:
                        price = None
                    elif tier1_bhd < tier3_bhd * low_threshold:
                        price = None
            if price and price.get("amount"):
                price.pop("retailer_score", None)
                set_cached(cache_key, price, PRICE_CACHE_TTL)
                self._save_price_to_db(cache_key, brand, name, variant, region, price)
                price["_cached"] = False
                return price

        # --- Tier 1.5: Page scraping cascade (luxury brands only) ---
        if not price and is_luxury_brand(full_name) and ENABLE_PAGE_SCRAPE:
            tier15_start = time.monotonic()
            tier15_budget = TIER_15_BUDGET_TIMEOUT
            failed_curl_urls = []

            # --- Tier 1.5a: Official brand site ---
            official_domain = get_official_domain(full_name)
            if official_domain:
                try:
                    official_results = await search_web(f"{full_name} site:{official_domain}")
                    self.api_calls += 1
                    self._track_cost_amount(0.001)
                    if official_results and official_results.get("organic"):
                        for organic_item in official_results["organic"][:2]:
                            page_url = organic_item.get("link")
                            if not page_url or not validate_scrape_url(page_url):
                                continue
                            if firecrawl_service.is_available() and is_circuit_closed("firecrawl") and has_budget("firecrawl"):
                                html, status = await firecrawl_service.scrape_page_with_status(page_url)
                                if status == 200:
                                    record_usage("firecrawl")
                                if html:
                                    record_success("firecrawl")
                                    price = extract_price_from_html(html, full_name, currency, official_domain, page_url)
                                    if price:
                                        price["source_method"] = "firecrawl"
                                        price["retailer"] = official_domain
                                        set_cached(cache_key, price, PRICE_CACHE_TTL)
                                        self._save_price_to_db(cache_key, brand, name, variant, region, price)
                                        price["_cached"] = False
                                        return price
                                elif status in (429, 503) or status == 0:
                                    record_failure("firecrawl")
                            page_price = await fetch_page_price(page_url, full_name, currency)
                            if page_price and page_price.get("amount"):
                                page_price.pop("_got_html", None)
                                page_price["retailer"] = official_domain
                                set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                                page_price["_cached"] = False
                                return page_price
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5a failed: {e}")

            elapsed = time.monotonic() - tier15_start
            if elapsed < tier15_budget:
                # --- Tier 1.5b: Authorized luxury retailers ---
                try:
                    retailer_query = f"{full_name} farfetch OR ssense OR net-a-porter"
                    retailer_results = await search_web(retailer_query)
                    self.api_calls += 1
                    self._track_cost_amount(0.001)
                    if retailer_results and retailer_results.get("organic"):
                        retailer_urls = []
                        for item in retailer_results["organic"][:5]:
                            link = item.get("link", "")
                            link_domain = urlparse(link).netloc.replace("www.", "")
                            if link_domain in AUTHORIZED_LUXURY_RETAILERS or link_domain in OFFICIAL_BRAND_DOMAINS:
                                retailer_urls.append((link, link_domain))
                        if retailer_urls:
                            fetch_tasks = [fetch_page_price(url, full_name, currency) for url, _ in retailer_urls[:3]]
                            page_prices = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                            valid_prices = []
                            for i, pp in enumerate(page_prices):
                                if isinstance(pp, dict) and pp.get("amount"):
                                    pp["_retailer_domain"] = retailer_urls[i][1]
                                    valid_prices.append(pp)
                                elif isinstance(pp, dict) and pp.get("_got_html"):
                                    failed_curl_urls.append(retailer_urls[i][0])
                            if len(valid_prices) >= 2:
                                amounts = [p["amount"] for p in valid_prices]
                                if max(amounts) / min(amounts) <= 1.15:
                                    best = min(valid_prices, key=lambda p: p["amount"])
                                else:
                                    best = valid_prices[0]
                                best.pop("_retailer_domain", None)
                                set_cached(cache_key, best, PRICE_CACHE_TTL)
                                best["_cached"] = False
                                return best
                            elif len(valid_prices) == 1:
                                best = valid_prices[0]
                                best.pop("_retailer_domain", None)
                                set_cached(cache_key, best, PRICE_CACHE_TTL)
                                best["_cached"] = False
                                return best
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5b failed: {e}")

                elapsed = time.monotonic() - tier15_start
                if elapsed < tier15_budget:
                    # --- Tier 1.5c: GCC luxury retailers ---
                    try:
                        gcc_query = f"{full_name} ounass OR bloomingdales dubai OR namshi"
                        gcc_results = await search_web(gcc_query)
                        self.api_calls += 1
                        self._track_cost_amount(0.001)
                        if gcc_results and gcc_results.get("organic"):
                            for item in gcc_results["organic"][:3]:
                                link = item.get("link", "")
                                link_domain = urlparse(link).netloc.replace("www.", "")
                                if link_domain in GCC_LUXURY_RETAILERS:
                                    gcc_price = await fetch_page_price(link, full_name, currency)
                                    if gcc_price and gcc_price.get("amount"):
                                        set_cached(cache_key, gcc_price, PRICE_CACHE_TTL)
                                        gcc_price["_cached"] = False
                                        return gcc_price
                                    elif gcc_price and gcc_price.get("_got_html"):
                                        failed_curl_urls.append(link)
                    except Exception as e:
                        logger.warning(f"[PRICE] Tier 1.5c failed: {e}")

                    # --- Tier 1.5d: Scrape.do rendering fallback ---
                    elapsed = time.monotonic() - tier15_start
                    if (failed_curl_urls and elapsed < tier15_budget
                            and scrapedo_service.is_available()
                            and is_circuit_closed("scrapedo") and has_budget("scrapedo")):
                        gcc_domains = GCC_LUXURY_RETAILERS
                        sorted_urls = sorted(
                            failed_curl_urls,
                            key=lambda u: 0 if urlparse(u).netloc.replace("www.", "") in gcc_domains else 1,
                        )
                        for retry_url in sorted_urls[:2]:
                            if not validate_scrape_url(retry_url):
                                continue
                            retry_domain = urlparse(retry_url).netloc.replace("www.", "")
                            html, status = await scrapedo_service.render_page_with_status(retry_url)
                            if status == 200:
                                record_usage("scrapedo")
                            if html:
                                record_success("scrapedo")
                                price = extract_price_from_html(html, full_name, currency, retry_domain, retry_url)
                                if price:
                                    price["source_method"] = "scrapedo_rendered"
                                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                                    self._save_price_to_db(cache_key, brand, name, variant, region, price)
                                    price["_cached"] = False
                                    return price
                            elif status in (429, 503) or status == 0:
                                record_failure("scrapedo")
                                break

        # --- Tier 2: GPT extraction from search context ---
        if is_supplement:
            iherb_query = re.sub(
                r'\b\d+\s*(softgels?|capsules?|tablets?|gummies?|caplets?|count|ct)\b',
                '', search_query, flags=re.IGNORECASE
            ).strip()
            iherb_query = re.sub(
                r'\b(supplement|vitamin|vitamins|mineral|minerals)\b',
                '', iherb_query, flags=re.IGNORECASE
            ).strip()
            iherb_query = re.sub(r'\s+', ' ', iherb_query)
            iherb_cc = region_info["code"]

            iherb_price = await fetch_iherb_price(iherb_query, brand, full_name, iherb_cc, currency)
            if iherb_price:
                iherb_price["_cached"] = False
                if iherb_price.get("iherb_rating"):
                    self._shopping_items_cache[full_name] = [{
                        "source": "iHerb",
                        "rating": iherb_price["iherb_rating"],
                        "ratingCount": iherb_price.get("iherb_review_count"),
                        "link": iherb_price["url"],
                        "title": full_name,
                    }]
                set_cached(cache_key, iherb_price, PRICE_CACHE_TTL)
                return iherb_price

            iherb_task = search_web(f"{iherb_query} iherb price", num_results=5, country=iherb_cc)
            bh_pharmacy_task = search_web(f"{brand} {name} price", num_results=5, country="bh")
            iherb_results, bh_pharmacy_results = await asyncio.gather(iherb_task, bh_pharmacy_task)
            self._track_serper_cost()
            self._track_serper_cost()
            iherb_organic = iherb_results.get("organic", [])
            bh_organic = bh_pharmacy_results.get("organic", [])

            pharmacy_price = await fetch_pharmacy_price(bh_organic, brand, full_name, currency, track_serper_cost_fn=self._track_serper_cost)
            if pharmacy_price:
                pharmacy_price["_cached"] = False
                set_cached(cache_key, pharmacy_price, PRICE_CACHE_TTL)
                return pharmacy_price

            if ENABLE_PAGE_SCRAPE:
                known_supplement_retailers = {"iherb.com", "bn.boots.com", "bolo.bh", "amazon.com", "noon.com"}
                for item in (iherb_organic + bh_organic)[:5]:
                    link = item.get("link", "")
                    link_domain = urlparse(link).netloc.replace("www.", "")
                    if link_domain in known_supplement_retailers or link_domain in PHARMACY_DOMAINS:
                        page_price = await fetch_page_price(link, full_name, currency)
                        if page_price and page_price.get("amount"):
                            page_price["_cached"] = False
                            set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                            return page_price

            combined_organic = iherb_organic + bh_organic
            if combined_organic:
                organic_results = {"organic": combined_organic, "knowledge_graph": None}
            else:
                organic_results = {"organic": [], "knowledge_graph": None}
        else:
            organic_results = await search_price_organic(search_query, region_info["code"])
            self._track_serper_cost()

        search_results["organic"] = organic_results.get("organic", [])
        search_results["knowledge_graph"] = organic_results.get("knowledge_graph")
        search_context = self._format_search_results(search_results)
        price, usage = await extract_price(brand, name, variant, region, search_context)
        self._track_gpt_cost(usage)
        sanitize_gpt_price(price)
        _convert_gpt_price_currency(price, currency)
        if price and price.get("amount"):
            original_cur = price.get("original_currency", "").upper()
            if original_cur and original_cur != currency:
                price["source_method"] = "converted_usd"
            else:
                price["source_method"] = "local_bhd"
            if is_supplement:
                if iherb_organic and not price.get("retailer"):
                    price["retailer"] = "iHerb"
                    price["url"] = f"https://{iherb_cc}.iherb.com/search?kw={quote_plus(full_name)}"
            else:
                if tier3_estimate is None:
                    tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
                    self._track_gpt_cost(usage)
                    sanitize_gpt_price(tier3_estimate)
                    _convert_gpt_price_currency(tier3_estimate, currency)
                if tier3_estimate and tier3_estimate.get("amount"):
                    tier2_bhd = _convert_to_bhd(price["amount"], currency)
                    tier3_bhd = _convert_to_bhd(tier3_estimate["amount"], currency)
                    if is_luxury_brand(full_name):
                        high_threshold, low_threshold = 1.8, 0.6
                    else:
                        high_threshold, low_threshold = 2.0, 0.5
                    if tier2_bhd > tier3_bhd * high_threshold:
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
                    elif tier2_bhd < tier3_bhd * low_threshold:
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
            if price.get("retailer") and not price.get("url"):
                price["url"] = build_retailer_url(price["retailer"], full_name)
            set_cached(cache_key, price, PRICE_CACHE_TTL)
            self._save_price_to_db(cache_key, brand, name, variant, region, price)
            price["_cached"] = False
            return price

        # --- Broader search fallback ---
        broader_name = full_name
        for _ in range(3):
            stripped = MODEL_VARIANT_PATTERN.sub('', broader_name).strip()
            if stripped == broader_name:
                break
            broader_name = stripped

        if broader_name != full_name and not is_supplement:
            broader_results = await search_product_prices(broader_name, region_info["code"])
            self._track_serper_cost()
            broader_shopping = broader_results.get("shopping", [])
            if broader_shopping:
                price = extract_price_from_shopping(broader_name, broader_shopping, currency)
                if price and price.get("amount"):
                    price.pop("retailer_score", None)
                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                    self._save_price_to_db(cache_key, brand, name, variant, region, price)
                    price["_cached"] = False
                    return price

        # --- Tier 3: GPT training data fallback ---
        if tier3_estimate is None:
            tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
            self._track_gpt_cost(usage)
            sanitize_gpt_price(tier3_estimate)
            _convert_gpt_price_currency(tier3_estimate, currency)
        price = tier3_estimate
        if price and price.get("amount"):
            price["estimated"] = True
            price["source_method"] = "estimated"
            if price.get("retailer") and not price.get("url"):
                price["url"] = build_retailer_url(price["retailer"], full_name)
            set_cached(cache_key, price, PRICE_CACHE_TTL // 2)
            self._save_price_to_db(cache_key, brand, name, variant, region, price)
            price["_cached"] = False
            return price

        return {"amount": None, "currency": currency, "_cached": False}

    async def _get_reviews(
        self, brand: str, name: str, variant: Optional[str], search_query: str,
        nocache: bool = False, category: str = "other",
        retailer_ratings: Optional[List[Dict]] = None, search_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get reviews with caching."""
        return await _get_reviews_standalone(
            brand, name, variant, search_query, nocache=nocache,
            category=category, retailer_ratings=retailer_ratings,
            search_results=search_results,
            track_serper_cost_fn=self._track_serper_cost,
            track_gpt_cost_fn=self._track_gpt_cost,
        )

    async def _get_verified_rating(self, full_name: str) -> Dict[str, Any]:
        """Get verified rating."""
        return await get_verified_rating(full_name, self._shopping_items_cache, track_serper_cost_fn=self._track_serper_cost)

    # ============================================
    # Formatting helpers (kept in orchestrator)
    # ============================================

    def _format_search_results(self, results: Dict) -> str:
        """Format search results into context string."""
        if not results:
            return "No search results available."
        formatted = []
        organic = results.get("organic", [])[:5]
        for i, r in enumerate(organic):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            formatted.append(f"{i+1}. {title}\n   {snippet}")
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
        """Format search results with [snippet_N] labels."""
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

    # ============================================
    # Cost tracking
    # ============================================

    def _save_price_to_db(self, cache_key: str, brand: str, name: str, variant: Optional[str], region: str, price: Dict):
        """Fire-and-forget save price to L2 DB."""
        from app.services.product_data_service import save_price
        asyncio.create_task(save_price(cache_key, brand, name, variant, region, price))

    def _track_gpt_cost(self, usage: dict):
        """Track real GPT cost from token usage."""
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
        self.total_cost += cost
        self.api_calls += 1
        self.gpt_calls += 1

    def _track_serper_cost(self):
        """Track a single Serper API call."""
        self.total_cost += 0.001
        self.api_calls += 1
        self.serper_calls += 1

    def _track_cost_amount(self, amount: float):
        """Track a generic cost amount (used by Tier 1.5 cascade)."""
        self.total_cost += amount

    def _format_review_search_results(self, results: Dict, retailer_ratings: List[Dict]) -> str:
        return format_review_search_results(results, retailer_ratings)


# ============================================
# GCC REGIONAL PRICING
# ============================================

async def get_regional_prices(
    brand: str, name: str, variant: Optional[str], search_query: str
) -> Dict[str, Any]:
    """Get prices across all GCC regions in parallel."""
    service = StructuredComparisonService()
    tasks = []
    for region in GCC_REGIONS.keys():
        tasks.append(service._get_price(brand, name, variant, region, search_query))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    regional = {}
    best_price = None
    best_region = None
    for region, result in zip(GCC_REGIONS.keys(), results):
        if isinstance(result, Exception):
            regional[region] = None
            continue
        regional[region] = result
        if result and result.get("amount"):
            amount_bhd = _convert_to_bhd(result["amount"], result.get("currency", "BHD"))
            if best_price is None or amount_bhd < best_price:
                best_price = amount_bhd
                best_region = region
    return {"regional_prices": regional, "best_region": best_region, "best_price_bhd": best_price}


# ============================================
# FACTORY
# ============================================

def get_comparison_service() -> StructuredComparisonService:
    """Create a new comparison service instance per request."""
    return StructuredComparisonService()
