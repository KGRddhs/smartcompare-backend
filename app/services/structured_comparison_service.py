"""
Structured Comparison Service - Main orchestrator for product comparisons
Handles caching, parallel fetching, and assembling complete product data
"""
import os
import re
import json
import asyncio
import logging
import httpx
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from app.services.extraction_service import (
    parse_product_query,
    extract_specs,
    extract_price,
    extract_reviews,
    generate_pros_cons,
    generate_comparison,
    get_specs_cache_key,
    get_price_cache_key,
    get_reviews_cache_key,
    GCC_REGIONS
)
from app.services.serper_service import search_product_prices, search_web
from app.services.cache_service import get_cached, set_cached

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

logger = logging.getLogger(__name__)

# Cache TTLs (in seconds)
SPECS_CACHE_TTL = 7 * 24 * 60 * 60    # 7 days - specs rarely change
PRICE_CACHE_TTL = 24 * 60 * 60         # 24 hours - prices change daily
REVIEWS_CACHE_TTL = 7 * 24 * 60 * 60   # 7 days - reviews aggregate slowly
PROS_CONS_CACHE_TTL = 7 * 24 * 60 * 60 # 7 days - derived from specs/reviews


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
    
    async def compare_from_text(
        self,
        query: str,
        region: str = "bahrain",
        include_specs: bool = True,
        include_reviews: bool = True,
        include_pros_cons: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry point for text-based comparisons.
        
        Example: compare_from_text("iPhone 15 vs Galaxy S24", "bahrain")
        """
        start_time = datetime.now()
        self.total_cost = 0.0
        self.api_calls = 0
        
        try:
            # Step 1: Parse the query
            logger.info(f"Parsing query: {query}")
            parsed = await parse_product_query(query)
            self._track_cost(0.0003)  # ~300 tokens
            
            if not parsed.get("products") or len(parsed["products"]) < 2:
                return {
                    "success": False,
                    "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'",
                    "parsed": parsed
                }
            
            products = parsed["products"][:2]  # Limit to 2 products
            logger.info(f"Identified products: {products}")
            
            # Step 2: Fetch data for each product (parallel)
            product_data = await asyncio.gather(
                self._fetch_product_data(products[0], region, include_specs, include_reviews),
                self._fetch_product_data(products[1], region, include_specs, include_reviews)
            )
            
            # Step 3: Generate pros/cons if requested
            if include_pros_cons:
                pros_cons = await asyncio.gather(
                    self._get_pros_cons(product_data[0]),
                    self._get_pros_cons(product_data[1])
                )
                product_data[0]["pros_cons"] = pros_cons[0]
                product_data[1]["pros_cons"] = pros_cons[1]
            
            # Step 4: Generate comparison
            comparison = await generate_comparison(
                product_data[0],
                product_data[1],
                region,
                parsed.get("comparison_type", "value")
            )
            self._track_cost(0.0008)  # ~800 tokens
            
            # Calculate timing
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "products": product_data,
                "comparison": comparison,
                "winner_index": comparison.get("winner_index", 0),
                "recommendation": comparison.get("recommendation", ""),
                "key_differences": comparison.get("key_differences", []),
                "metadata": {
                    "query": query,
                    "region": region,
                    "elapsed_seconds": round(elapsed, 2),
                    "total_cost": round(self.total_cost, 6),
                    "api_calls": self.api_calls,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Comparison error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "total_cost": self.total_cost
            }
    
    async def _fetch_product_data(
        self,
        product_info: Dict,
        region: str,
        include_specs: bool,
        include_reviews: bool
    ) -> Dict[str, Any]:
        """Fetch all data for a single product."""
        brand = product_info.get("brand", "")
        name = product_info.get("name", "")
        variant = product_info.get("variant")
        category = product_info.get("category", "other")
        search_query = product_info.get("search_query", f"{brand} {name} {variant or ''}")
        
        full_name = f"{brand} {name} {variant or ''}".strip()
        
        result = {
            "brand": brand,
            "name": name,
            "full_name": full_name,
            "variant": variant,
            "category": category,
            "query": search_query,
        }
        
        # Parallel fetch: specs, price, reviews
        tasks = []
        
        if include_specs:
            tasks.append(("specs", self._get_specs(brand, name, variant, category, search_query)))
        
        tasks.append(("price", self._get_price(brand, name, variant, region, search_query)))
        
        if include_reviews:
            tasks.append(("reviews", self._get_reviews(brand, name, variant, search_query)))
        
        # Execute all tasks
        task_results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        # Assign results
        for i, (key, _) in enumerate(tasks):
            if isinstance(task_results[i], Exception):
                logger.error(f"Error fetching {key}: {task_results[i]}")
                result[key] = None
            else:
                result[key] = task_results[i]
        
        # Extract best price
        if result.get("price"):
            result["best_price"] = result["price"].get("amount")
            result["currency"] = result["price"].get("currency", "BHD")
            result["retailer"] = result["price"].get("retailer")

        # Clean specs: remove meta keys, flatten additional_specs
        if result.get("specs"):
            result["specs"] = self._clean_specs(result["specs"])

        # Extract verified rating from Google Shopping
        rating_data = await self._get_verified_rating(full_name)
        result["rating"] = rating_data.get("rating")
        result["review_count"] = rating_data.get("review_count")
        result["rating_verified"] = rating_data.get("rating_verified", False)
        result["rating_source"] = rating_data.get("rating_source")

        # Calculate data freshness
        result["data_freshness"] = self._calculate_freshness(result)

        return result
    
    async def _get_specs(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        category: str,
        search_query: str
    ) -> Dict[str, Any]:
        """Get specs with caching."""
        cache_key = get_specs_cache_key(brand, name, variant)
        
        # Check cache
        cached = get_cached(cache_key)
        if cached:
            logger.info(f"Specs cache hit: {cache_key}")
            cached["_cached"] = True
            return cached
        
        # Fetch from search
        logger.info(f"Fetching specs for: {brand} {name}")
        search_results = await search_web(f"{search_query} specifications features")
        self._track_cost(0.001)  # Serper cost
        
        search_context = self._format_search_results(search_results)
        
        # Extract specs
        specs = await extract_specs(brand, name, variant, category, search_context)
        self._track_cost(0.0005)  # ~500 tokens
        
        # Cache result
        if specs and not specs.get("error"):
            set_cached(cache_key, specs, SPECS_CACHE_TTL)
        
        specs["_cached"] = False
        return specs
    
    async def _get_price(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        region: str,
        search_query: str
    ) -> Dict[str, Any]:
        """Get price with caching."""
        cache_key = get_price_cache_key(brand, name, variant, region)
        
        # Check cache
        cached = get_cached(cache_key)
        if cached:
            logger.info(f"Price cache hit: {cache_key}")
            cached["_cached"] = True
            return cached
        
        # Fetch from search
        region_info = GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])
        logger.info(f"Fetching price for: {brand} {name} in {region}")
        
        search_results = await search_product_prices(
            f"{search_query}",
            region_info["code"]
        )
        self._track_cost(0.001)  # Serper cost
        
        search_context = self._format_search_results(search_results)
        
        # Extract price
        price = await extract_price(brand, name, variant, region, search_context)
        self._track_cost(0.0003)  # ~300 tokens
        
        # Cache result (only if we found a price)
        if price and price.get("amount"):
            set_cached(cache_key, price, PRICE_CACHE_TTL)
        
        price["_cached"] = False
        return price
    
    async def _get_reviews(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        search_query: str
    ) -> Dict[str, Any]:
        """Get reviews with caching."""
        cache_key = get_reviews_cache_key(brand, name, variant)
        
        # Check cache
        cached = get_cached(cache_key)
        if cached:
            logger.info(f"Reviews cache hit: {cache_key}")
            cached["_cached"] = True
            return cached
        
        # Fetch from search
        logger.info(f"Fetching reviews for: {brand} {name}")
        search_results = await search_web(f"{search_query} review rating user feedback")
        self._track_cost(0.001)  # Serper cost
        
        search_context = self._format_search_results(search_results)
        
        # Extract reviews
        reviews = await extract_reviews(brand, name, variant, search_context)
        self._track_cost(0.0004)  # ~400 tokens
        
        # Cache result
        if reviews and not reviews.get("error"):
            set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
        
        reviews["_cached"] = False
        return reviews
    
    async def _get_pros_cons(self, product: Dict) -> Dict[str, Any]:
        """Generate pros/cons from specs and reviews."""
        cache_key = f"proscons:{product.get('brand', '')}:{product.get('name', '')}:{product.get('variant', '')}"
        
        # Check cache
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        # Generate
        pros_cons = await generate_pros_cons(
            product.get("brand", ""),
            product.get("name", ""),
            product.get("variant"),
            product.get("category", "other"),
            product.get("specs", {}),
            product.get("reviews", {}),
            product.get("best_price"),
            product.get("currency", "BHD")
        )
        self._track_cost(0.0004)
        
        # Cache
        if pros_cons and not pros_cons.get("error"):
            set_cached(cache_key, pros_cons, PROS_CONS_CACHE_TTL)
        
        return pros_cons
    
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
    
    def _calculate_freshness(self, product: Dict) -> str:
        """Calculate overall data freshness."""
        specs_cached = product.get("specs", {}).get("_cached", True)
        price_cached = product.get("price", {}).get("_cached", True)
        reviews_cached = product.get("reviews", {}).get("_cached", True)
        
        if not specs_cached and not price_cached:
            return "live"
        elif specs_cached and price_cached and reviews_cached:
            return "cached"
        else:
            return "mixed"
    
    def _track_cost(self, cost: float):
        """Track API costs."""
        self.total_cost += cost
        self.api_calls += 1

    async def _get_verified_rating(self, full_name: str) -> Dict[str, Any]:
        """
        Get verified rating from Google Shopping data via Serper.
        Returns real ratings from retailer listings - NO AI generation.
        """
        if not SERPER_API_KEY:
            return {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

        logger.info(f"[RATING] Searching Google Shopping for: {full_name}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://google.serper.dev/shopping",
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                    json={"q": full_name, "num": 15}
                )

                if response.status_code != 200:
                    logger.error(f"[RATING] Serper shopping search failed: {response.status_code}")
                    return {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

                shopping_items = response.json().get("shopping", [])
                self._track_cost(0.001)

            return self._extract_rating_from_shopping(full_name, shopping_items)

        except Exception as e:
            logger.error(f"[RATING] Shopping search error: {e}")
            return {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

    def _extract_rating_from_shopping(self, product_name: str, shopping_items: List[Dict]) -> Dict[str, Any]:
        """Extract best matching rating from Serper Shopping results."""
        empty = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

        if not shopping_items:
            return empty

        p_words = set(product_name.lower().split())
        candidates = []

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
            t_words = set(title.lower().split())
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

            candidates.append({
                "rating": rating_val,
                "review_count": review_count,
                "source": item.get("source", "Google Shopping"),
                "link": item.get("link", ""),
                "title": title,
                "match_score": match_score,
            })

        if not candidates:
            return empty

        candidates.sort(key=lambda c: (c["review_count"] or 0, c["match_score"]), reverse=True)
        best = candidates[0]

        logger.info(f"[RATING] ✓ VERIFIED: {best['rating']}/5 ({best['review_count']} reviews) from {best['source']}")

        return {
            "rating": round(best["rating"], 1),
            "review_count": best["review_count"],
            "rating_verified": True,
            "rating_source": {
                "name": f"{best['source']} via Google Shopping",
                "url": best["link"],
                "retrieved_at": datetime.now().isoformat() + "Z",
                "extract_method": "google_shopping",
                "confidence": "high"
            }
        }

    @staticmethod
    def _clean_specs(specs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean specs for display: remove meta keys, flatten additional_specs, handle arrays."""
        if not specs or not isinstance(specs, dict):
            return {}

        # Keys that are metadata, not actual specs
        meta_keys = {"brand", "model", "variant", "category", "_cached", "error"}

        cleaned = {}
        for key, value in specs.items():
            if key in meta_keys:
                continue
            if value is None:
                continue

            if key == "additional_specs" and isinstance(value, dict):
                # Flatten additional_specs into main specs
                for sub_key, sub_val in value.items():
                    if sub_val is not None:
                        cleaned[sub_key] = str(sub_val) if not isinstance(sub_val, str) else sub_val
            elif isinstance(value, list):
                cleaned[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                cleaned[key] = json.dumps(value)
            else:
                cleaned[key] = value

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
    rates = {
        "BHD": 1.0,
        "SAR": 0.1,      # 1 SAR ≈ 0.10 BHD
        "AED": 0.1,      # 1 AED ≈ 0.10 BHD
        "KWD": 1.22,     # 1 KWD ≈ 1.22 BHD
        "QAR": 0.1,      # 1 QAR ≈ 0.10 BHD
        "OMR": 0.98,     # 1 OMR ≈ 0.98 BHD
        "USD": 0.377,    # 1 USD ≈ 0.377 BHD
    }
    return amount * rates.get(currency, 1.0)


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
