"""
Comparison Service - Main orchestration for product comparison
"""
from typing import List, Dict, Optional
from app.services.openai_service import (
    identify_products,
    extract_price_from_search_results,
    estimate_price_fallback,
    generate_comparison
)
from app.services.serper_service import search_product_price
from app.services.cache_service import (
    get_product_cache_key,
    get_cached_price,
    cache_price,
    track_api_cost
)


async def compare_products(
    image_data_list: List[Dict],
    country: str = "Bahrain"
) -> Dict:
    """
    Main comparison function - orchestrates the entire pipeline.
    
    Pipeline:
    1. Identify products from images (OpenAI Vision)
    2. For each product:
       a. Check cache for price
       b. If not cached, search web (Serper)
       c. If search successful, extract price (OpenAI)
       d. If search fails, estimate price (OpenAI fallback)
       e. Cache the result
    3. Generate comparison and winner (OpenAI)
    
    Args:
        image_data_list: List of image data dicts
            - {"path": "/path/to/image.jpg"} for file paths
            - {"bytes": b"...", "mime_type": "image/jpeg"} for raw bytes
        country: Country for price search (default: Bahrain)
    
    Returns:
        {
            "success": True,
            "products": [
                {
                    "brand": "Nido",
                    "name": "Full Cream Milk Powder",
                    "size": "2.5kg",
                    "price": 8.50,
                    "currency": "BHD",
                    "source": "live" | "cached" | "estimated",
                    "retailer": "Lulu Hypermarket"
                },
                ...
            ],
            "winner_index": 0,
            "recommendation": "Product 1 offers the best value...",
            "key_differences": [...],
            "total_cost": 0.00234,
            "data_freshness": "live" | "mixed" | "estimated"
        }
    """
    
    total_cost = 0.0
    errors = []
    
    # Step 1: Identify products from images
    try:
        vision_result = await identify_products(image_data_list)
        
        if "error" in vision_result:
            return {
                "success": False,
                "error": vision_result["error"],
                "raw_response": vision_result.get("raw_response")
            }
        
        products = vision_result["products"]
        total_cost += vision_result["cost"]
        
        if not products:
            return {
                "success": False,
                "error": "Could not identify any products from the images"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Vision processing failed: {str(e)}"
        }
    
    # Step 2: Get prices for each product
    data_sources = []
    
    for product in products:
        brand = product.get("brand", "")
        name = product.get("name", "")
        size = product.get("size")
        
        # Generate cache key
        cache_key = get_product_cache_key(brand, name, size, country)
        
        # 2a. Check cache first
        cached_price = get_cached_price(cache_key)
        if cached_price and cached_price.get("price"):
            product["price"] = cached_price["price"]
            product["currency"] = cached_price.get("currency", "BHD")
            product["retailer"] = cached_price.get("retailer")
            product["source"] = "cached"
            product["confidence"] = cached_price.get("confidence", "medium")
            data_sources.append("cached")
            continue
        
        # 2b. Search web for price
        try:
            search_result = await search_product_price(brand, name, size, country)
            
            if search_result["success"] and search_result.get("snippets"):
                # 2c. Extract price from search results
                product_full_name = f"{brand} {name} {size or ''}".strip()
                price_result = await extract_price_from_search_results(
                    product_full_name,
                    search_result["snippets"]
                )
                
                total_cost += price_result.get("extraction_cost", 0)
                
                if price_result.get("price") and price_result.get("confidence") != "none":
                    product["price"] = price_result["price"]
                    product["currency"] = price_result.get("currency", "BHD")
                    product["retailer"] = price_result.get("retailer")
                    product["source"] = "live"
                    product["confidence"] = price_result.get("confidence", "medium")
                    data_sources.append("live")
                    
                    # Cache the result
                    cache_price(cache_key, {
                        "price": price_result["price"],
                        "currency": price_result.get("currency"),
                        "retailer": price_result.get("retailer"),
                        "confidence": price_result.get("confidence")
                    })
                    continue
        
        except Exception as e:
            errors.append(f"Search failed for {brand} {name}: {str(e)}")
        
        # 2d. Fallback to OpenAI estimation
        try:
            fallback_result = await estimate_price_fallback(product, country)
            total_cost += fallback_result.get("estimation_cost", 0)
            
            product["price"] = fallback_result.get("price")
            product["currency"] = fallback_result.get("currency", "BHD")
            product["retailer"] = None
            product["source"] = "estimated"
            product["confidence"] = "estimated"
            product["note"] = fallback_result.get("note", "Price estimated from training data")
            data_sources.append("estimated")
            
        except Exception as e:
            errors.append(f"Estimation failed for {brand} {name}: {str(e)}")
            product["price"] = None
            product["source"] = "failed"
            data_sources.append("failed")
    
    # Step 3: Generate comparison
    try:
        comparison_result = await generate_comparison(products)
        total_cost += comparison_result.get("comparison_cost", 0)
        
    except Exception as e:
        comparison_result = {
            "winner_index": 0,
            "recommendation": f"Comparison generation failed: {str(e)}",
            "key_differences": ["Unable to complete comparison"]
        }
    
    # Track total API cost
    track_api_cost(total_cost)
    
    # Determine overall data freshness
    if "live" in data_sources:
        data_freshness = "live" if all(s == "live" for s in data_sources) else "mixed"
    elif "cached" in data_sources:
        data_freshness = "cached" if all(s == "cached" for s in data_sources) else "mixed"
    else:
        data_freshness = "estimated"
    
    return {
        "success": True,
        "products": products,
        "winner_index": comparison_result.get("winner_index", 0),
        "recommendation": comparison_result.get("recommendation", ""),
        "key_differences": comparison_result.get("key_differences", []),
        "total_cost": round(total_cost, 6),
        "data_freshness": data_freshness,
        "errors": errors if errors else None
    }


async def quick_compare(
    product1: Dict,
    product2: Dict,
    country: str = "Bahrain"
) -> Dict:
    """
    Quick comparison when products are already identified.
    Skips vision processing.
    
    Args:
        product1: First product dict (brand, name, size)
        product2: Second product dict (brand, name, size)
        country: Country for price search
    
    Returns:
        Same structure as compare_products()
    """
    
    products = [product1, product2]
    total_cost = 0.0
    data_sources = []
    
    # Get prices for each product (same logic as main function)
    for product in products:
        brand = product.get("brand", "")
        name = product.get("name", "")
        size = product.get("size")
        
        cache_key = get_product_cache_key(brand, name, size, country)
        
        # Check cache
        cached_price = get_cached_price(cache_key)
        if cached_price and cached_price.get("price"):
            product["price"] = cached_price["price"]
            product["currency"] = cached_price.get("currency", "BHD")
            product["source"] = "cached"
            data_sources.append("cached")
            continue
        
        # Search web
        search_result = await search_product_price(brand, name, size, country)
        
        if search_result["success"] and search_result.get("snippets"):
            product_full_name = f"{brand} {name} {size or ''}".strip()
            price_result = await extract_price_from_search_results(
                product_full_name,
                search_result["snippets"]
            )
            total_cost += price_result.get("extraction_cost", 0)
            
            if price_result.get("price"):
                product["price"] = price_result["price"]
                product["currency"] = price_result.get("currency", "BHD")
                product["source"] = "live"
                data_sources.append("live")
                
                cache_price(cache_key, {
                    "price": price_result["price"],
                    "currency": price_result.get("currency")
                })
                continue
        
        # Fallback
        fallback_result = await estimate_price_fallback(product, country)
        total_cost += fallback_result.get("estimation_cost", 0)
        product["price"] = fallback_result.get("price")
        product["currency"] = fallback_result.get("currency", "BHD")
        product["source"] = "estimated"
        data_sources.append("estimated")
    
    # Generate comparison
    comparison_result = await generate_comparison(products)
    total_cost += comparison_result.get("comparison_cost", 0)
    
    track_api_cost(total_cost)
    
    return {
        "success": True,
        "products": products,
        "winner_index": comparison_result.get("winner_index", 0),
        "recommendation": comparison_result.get("recommendation", ""),
        "key_differences": comparison_result.get("key_differences", []),
        "total_cost": round(total_cost, 6),
        "data_freshness": "live" if "live" in data_sources else "cached" if "cached" in data_sources else "estimated"
    }
