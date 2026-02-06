"""
OpenAI Service - Vision and text processing for product comparison
"""
import os
import json
import base64
from typing import List, Dict, Optional
from openai import AsyncOpenAI

# Initialize async client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def encode_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")


def encode_image_bytes_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string"""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def clean_json_response(raw_content: str) -> str:
    """Remove markdown code blocks from OpenAI response"""
    content = raw_content.strip()
    if content.startswith("```"):
        # Remove opening ```json or ```
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    return content.strip()


async def identify_products(image_data_list: List[Dict]) -> Dict:
    """
    Use OpenAI Vision to identify products from images.
    
    Args:
        image_data_list: List of dicts with either:
            - {"path": "/path/to/image.jpg"} for file paths
            - {"bytes": b"...", "mime_type": "image/jpeg"} for raw bytes
    
    Returns:
        {
            "products": [
                {"brand": "Nido", "name": "Full Cream Milk Powder", "size": "2.5kg", "visible_price": "8.50 BD"},
                ...
            ],
            "tokens_used": 1234,
            "cost": 0.00056
        }
    """
    
    # Build message content with images
    content = [
        {
            "type": "text",
            "text": """Analyze these product images and identify each product. For EACH product image, extract:

- brand: The brand name (e.g., "Nido", "Tide", "Almarai")
- name: The product name (e.g., "Full Cream Milk Powder", "Liquid Detergent")
- size: Size/weight/volume if visible (e.g., "2.5kg", "1L", "500ml")
- visible_price: Any price shown on the label or shelf tag (e.g., "8.50 BD", "$12.99")

Return ONLY a valid JSON array. Example:
[
  {"brand": "Nido", "name": "Full Cream Milk Powder", "size": "2.5kg", "visible_price": "8.50 BD"},
  {"brand": "Almarai", "name": "Fresh Milk Full Fat", "size": "1L", "visible_price": null}
]

RULES:
- Return one object per product image
- Use null for any field you cannot determine
- Do NOT include markdown code blocks
- Return ONLY the JSON array, nothing else"""
        }
    ]
    
    # Add images to content
    for img_data in image_data_list:
        if "path" in img_data:
            base64_image = encode_image_to_base64(img_data["path"])
            mime_type = "image/jpeg"  # Default
            if img_data["path"].lower().endswith(".png"):
                mime_type = "image/png"
        else:
            base64_image = encode_image_bytes_to_base64(img_data["bytes"])
            mime_type = img_data.get("mime_type", "image/jpeg")
        
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}",
                "detail": "low"  # Use "low" to save costs
            }
        })
    
    # Call OpenAI Vision API
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": content}],
        max_tokens=500,
        temperature=0  # Deterministic output
    )
    
    # Parse response
    raw_content = response.choices[0].message.content
    clean_content = clean_json_response(raw_content)
    
    try:
        products = json.loads(clean_content)
    except json.JSONDecodeError as e:
        # If parsing fails, return error info
        return {
            "products": [],
            "error": f"Failed to parse response: {str(e)}",
            "raw_response": raw_content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "cost": 0
        }
    
    # Calculate cost (gpt-4o-mini pricing)
    # Input: $0.15 per 1M tokens, Output: $0.60 per 1M tokens
    usage = response.usage
    input_cost = (usage.prompt_tokens * 0.15) / 1_000_000
    output_cost = (usage.completion_tokens * 0.60) / 1_000_000
    total_cost = input_cost + output_cost
    
    return {
        "products": products,
        "tokens_used": usage.total_tokens,
        "cost": round(total_cost, 6)
    }


async def extract_price_from_search_results(
    product_name: str,
    search_snippets: List[Dict]
) -> Dict:
    """
    Extract price from web search results using OpenAI.
    
    Args:
        product_name: Full product name (brand + name + size)
        search_snippets: List of search result snippets from Serper
    
    Returns:
        {
            "price": 8.50,
            "currency": "BHD",
            "retailer": "Lulu Hypermarket",
            "confidence": "high" | "medium" | "low" | "none"
        }
    """
    
    # Format search results for context
    context_parts = []
    for i, snippet in enumerate(search_snippets[:5], 1):
        title = snippet.get("title", "")
        text = snippet.get("snippet", "")
        link = snippet.get("link", "")
        context_parts.append(f"Result {i}:\nTitle: {title}\nSnippet: {text}\nURL: {link}")
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""Extract the current retail price for this product from the search results:

PRODUCT: {product_name}

SEARCH RESULTS:
{context}

Return ONLY a JSON object:
{{
  "price": 8.50,
  "currency": "BHD",
  "retailer": "Store name where price was found",
  "confidence": "high"
}}

RULES:
- price: The numeric price (no currency symbol)
- currency: "BHD" for Bahraini Dinar, "SAR" for Saudi Riyal, "USD" for US Dollar, etc.
- retailer: The store/website name
- confidence: "high" if exact match found, "medium" if similar product, "low" if uncertain, "none" if no price found
- If no price found, set price to null and confidence to "none"
- Return ONLY JSON, no markdown"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0
    )
    
    raw_content = response.choices[0].message.content
    clean_content = clean_json_response(raw_content)
    
    try:
        result = json.loads(clean_content)
    except json.JSONDecodeError:
        result = {
            "price": None,
            "currency": None,
            "retailer": None,
            "confidence": "none"
        }
    
    # Add token cost
    usage = response.usage
    input_cost = (usage.prompt_tokens * 0.15) / 1_000_000
    output_cost = (usage.completion_tokens * 0.60) / 1_000_000
    result["extraction_cost"] = round(input_cost + output_cost, 6)
    
    return result


async def estimate_price_fallback(product: Dict, country: str = "Bahrain") -> Dict:
    """
    Estimate price using OpenAI's training data when web search fails.
    
    Args:
        product: Product dict with brand, name, size
        country: Target country for price estimation
    
    Returns:
        {
            "price": 8.50,
            "currency": "BHD",
            "confidence": "estimated",
            "note": "Based on typical market prices"
        }
    """
    
    product_desc = f"{product.get('brand', '')} {product.get('name', '')} {product.get('size', '')}".strip()
    
    prompt = f"""Estimate a typical retail price for this product in {country}:

PRODUCT: {product_desc}

Based on your training data, what would be a reasonable retail price?

Return ONLY JSON:
{{
  "price": 8.50,
  "currency": "BHD",
  "confidence": "estimated",
  "note": "Based on typical {country} supermarket prices"
}}

RULES:
- Use local currency (BHD for Bahrain, SAR for Saudi Arabia, AED for UAE)
- If you cannot estimate, set price to null
- Return ONLY JSON, no markdown"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.3  # Slight variation allowed
    )
    
    raw_content = response.choices[0].message.content
    clean_content = clean_json_response(raw_content)
    
    try:
        result = json.loads(clean_content)
    except json.JSONDecodeError:
        result = {
            "price": None,
            "currency": "BHD",
            "confidence": "failed",
            "note": "Could not estimate price"
        }
    
    # Add token cost
    usage = response.usage
    input_cost = (usage.prompt_tokens * 0.15) / 1_000_000
    output_cost = (usage.completion_tokens * 0.60) / 1_000_000
    result["estimation_cost"] = round(input_cost + output_cost, 6)
    
    return result


async def generate_comparison(products: List[Dict]) -> Dict:
    """
    Generate final comparison and determine the winner.
    
    Args:
        products: List of products with price data attached
    
    Returns:
        {
            "winner_index": 0,
            "recommendation": "Product 1 (Nido) offers the best value...",
            "key_differences": [
                "Price: Nido is 15% cheaper per kg",
                "Size: Almarai offers larger quantity",
                ...
            ],
            "comparison_cost": 0.00012
        }
    """
    
    products_json = json.dumps(products, indent=2, default=str)
    
    prompt = f"""Compare these products and determine which offers the best value:

PRODUCTS:
{products_json}

Analyze and return ONLY JSON:
{{
  "winner_index": 0,
  "recommendation": "A 2-3 sentence recommendation explaining why this product is the best choice",
  "key_differences": [
    "Price: Specific price comparison",
    "Value: Price per unit comparison if applicable",
    "Quality: Any quality differences noted",
    "Availability: Data source reliability"
  ]
}}

RULES:
- winner_index is 0-based (0 = first product)
- Consider: price, price-per-unit, data reliability (live > cached > estimated)
- Be specific with numbers in key_differences
- Maximum 5 key differences
- Return ONLY JSON, no markdown"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.3
    )
    
    raw_content = response.choices[0].message.content
    clean_content = clean_json_response(raw_content)
    
    try:
        result = json.loads(clean_content)
    except json.JSONDecodeError:
        result = {
            "winner_index": 0,
            "recommendation": "Unable to generate comparison. Please try again.",
            "key_differences": ["Comparison failed - please retry"]
        }
    
    # Add token cost
    usage = response.usage
    input_cost = (usage.prompt_tokens * 0.15) / 1_000_000
    output_cost = (usage.completion_tokens * 0.60) / 1_000_000
    result["comparison_cost"] = round(input_cost + output_cost, 6)
    
    return result
