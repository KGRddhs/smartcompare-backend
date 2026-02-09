"""
URL Extraction Service - Scrape and extract product data from retailer URLs
Supports major GCC retailers: Amazon, Noon, Carrefour, Sharaf DG, Lulu, etc.
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import re
import json
import logging
import httpx
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Lazy OpenAI client
_client = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# ============================================
# RETAILER DETECTION
# ============================================

SUPPORTED_RETAILERS = {
    "amazon.ae": {"name": "Amazon UAE", "region": "uae", "currency": "AED"},
    "amazon.sa": {"name": "Amazon Saudi", "region": "saudi_arabia", "currency": "SAR"},
    "amazon.com": {"name": "Amazon US", "region": "us", "currency": "USD"},
    "noon.com": {"name": "Noon", "region": "uae", "currency": "AED"},
    "carrefour": {"name": "Carrefour", "region": "bahrain", "currency": "BHD"},
    "sharafdg.com": {"name": "Sharaf DG", "region": "uae", "currency": "AED"},
    "luluhypermarket": {"name": "Lulu Hypermarket", "region": "bahrain", "currency": "BHD"},
    "extra.com": {"name": "Extra Stores", "region": "saudi_arabia", "currency": "SAR"},
    "jarir.com": {"name": "Jarir Bookstore", "region": "saudi_arabia", "currency": "SAR"},
    "xcite.com": {"name": "Xcite Kuwait", "region": "kuwait", "currency": "KWD"},
}


def detect_retailer(url: str) -> Optional[Dict[str, Any]]:
    """Detect retailer from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    
    for key, info in SUPPORTED_RETAILERS.items():
        if key in domain:
            return {
                "key": key,
                "domain": domain,
                **info
            }
    
    # Unknown retailer - still try to scrape
    return {
        "key": "unknown",
        "domain": domain,
        "name": domain,
        "region": "unknown",
        "currency": "USD"
    }


# ============================================
# WEB SCRAPING
# ============================================

async def fetch_page(url: str) -> Optional[str]:
    """Fetch webpage content with proper headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return None


def extract_json_ld(html: str) -> List[Dict]:
    """Extract JSON-LD structured data from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    
    results = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    
    return results


def extract_meta_tags(html: str) -> Dict[str, str]:
    """Extract OpenGraph and meta tags."""
    soup = BeautifulSoup(html, "html.parser")
    meta = {}
    
    # OpenGraph tags
    for tag in soup.find_all("meta", property=re.compile(r"^og:")):
        prop = tag.get("property", "").replace("og:", "")
        content = tag.get("content", "")
        if prop and content:
            meta[f"og_{prop}"] = content
    
    # Product meta tags
    for tag in soup.find_all("meta", property=re.compile(r"^product:")):
        prop = tag.get("property", "").replace("product:", "")
        content = tag.get("content", "")
        if prop and content:
            meta[f"product_{prop}"] = content
    
    # Regular meta tags
    for name in ["description", "keywords", "title"]:
        tag = soup.find("meta", attrs={"name": name})
        if tag:
            meta[name] = tag.get("content", "")
    
    # Title tag
    title_tag = soup.find("title")
    if title_tag:
        meta["page_title"] = title_tag.string
    
    return meta


# ============================================
# RETAILER-SPECIFIC EXTRACTORS
# ============================================

def extract_amazon_data(html: str, url: str) -> Dict[str, Any]:
    """Extract product data from Amazon pages."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    # Title
    title_elem = soup.find("span", id="productTitle")
    if title_elem:
        data["title"] = title_elem.get_text(strip=True)
    
    # Price
    price_elem = soup.find("span", class_="a-price-whole")
    if price_elem:
        price_text = price_elem.get_text(strip=True).replace(",", "")
        try:
            data["price"] = float(price_text)
        except ValueError:
            pass
    
    # Alternative price location
    if "price" not in data:
        price_elem = soup.find("span", id="priceblock_ourprice")
        if price_elem:
            price_match = re.search(r"[\d,]+\.?\d*", price_elem.get_text())
            if price_match:
                data["price"] = float(price_match.group().replace(",", ""))
    
    # Rating
    rating_elem = soup.find("span", class_="a-icon-alt")
    if rating_elem:
        rating_text = rating_elem.get_text()
        rating_match = re.search(r"([\d.]+) out of 5", rating_text)
        if rating_match:
            data["rating"] = float(rating_match.group(1))
    
    # Review count
    review_elem = soup.find("span", id="acrCustomerReviewText")
    if review_elem:
        review_match = re.search(r"([\d,]+)", review_elem.get_text())
        if review_match:
            data["review_count"] = int(review_match.group(1).replace(",", ""))
    
    # Image
    img_elem = soup.find("img", id="landingImage")
    if img_elem:
        data["image_url"] = img_elem.get("src") or img_elem.get("data-old-hires")
    
    # Features/specs
    features = []
    feature_list = soup.find("ul", class_="a-unordered-list a-vertical a-spacing-mini")
    if feature_list:
        for li in feature_list.find_all("li"):
            text = li.get_text(strip=True)
            if text:
                features.append(text)
    data["features"] = features[:10]
    
    # ASIN
    asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if asin_match:
        data["asin"] = asin_match.group(1)
    
    return data


def extract_noon_data(html: str, url: str) -> Dict[str, Any]:
    """Extract product data from Noon pages."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    # Try JSON-LD first (Noon uses it)
    json_ld = extract_json_ld(html)
    for item in json_ld:
        if item.get("@type") == "Product":
            data["title"] = item.get("name")
            data["description"] = item.get("description")
            data["image_url"] = item.get("image")
            data["brand"] = item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else item.get("brand")
            
            offers = item.get("offers", {})
            if isinstance(offers, dict):
                data["price"] = offers.get("price")
                data["currency"] = offers.get("priceCurrency")
                data["availability"] = offers.get("availability")
            
            rating = item.get("aggregateRating", {})
            if rating:
                data["rating"] = rating.get("ratingValue")
                data["review_count"] = rating.get("reviewCount")
            break
    
    # Fallback to HTML parsing
    if "title" not in data:
        title_elem = soup.find("h1")
        if title_elem:
            data["title"] = title_elem.get_text(strip=True)
    
    return data


def extract_generic_data(html: str, url: str) -> Dict[str, Any]:
    """Generic extraction for unknown retailers."""
    data = {}
    
    # Try JSON-LD structured data first
    json_ld = extract_json_ld(html)
    for item in json_ld:
        if item.get("@type") == "Product":
            data["title"] = item.get("name")
            data["description"] = item.get("description")
            data["image_url"] = item.get("image")
            data["brand"] = item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else item.get("brand")
            
            offers = item.get("offers", {})
            if isinstance(offers, dict):
                data["price"] = offers.get("price")
                data["currency"] = offers.get("priceCurrency")
            elif isinstance(offers, list) and offers:
                data["price"] = offers[0].get("price")
                data["currency"] = offers[0].get("priceCurrency")
            
            rating = item.get("aggregateRating", {})
            if rating:
                data["rating"] = rating.get("ratingValue")
                data["review_count"] = rating.get("reviewCount")
            break
    
    # Fallback to meta tags
    meta = extract_meta_tags(html)
    
    if "title" not in data:
        data["title"] = meta.get("og_title") or meta.get("page_title")
    
    if "description" not in data:
        data["description"] = meta.get("og_description") or meta.get("description")
    
    if "image_url" not in data:
        data["image_url"] = meta.get("og_image")
    
    if "price" not in data and "product_price:amount" in meta:
        try:
            data["price"] = float(meta["product_price:amount"])
        except ValueError:
            pass
    
    return data


# ============================================
# AI-POWERED EXTRACTION (FALLBACK)
# ============================================

URL_EXTRACTION_PROMPT = """You are a product data extraction expert. Extract product information from this webpage content.

URL: {url}
Page Title: {title}

Page Content (truncated):
{content}

Extract and return ONLY valid JSON:
{{
    "brand": "brand name or null",
    "name": "product name",
    "full_title": "complete product title",
    "price": numeric_price_or_null,
    "currency": "currency code (AED, SAR, BHD, USD, etc.)",
    "category": "electronics|grocery|beauty|fashion|home|sports|automotive|other",
    "variant": "size/storage/color if specified or null",
    "specs": {{
        "key": "value for important specifications"
    }},
    "rating": 0.0-5.0 or null,
    "review_count": number or null,
    "in_stock": true|false|null,
    "retailer": "store name",
    "image_url": "main product image URL or null"
}}

RULES:
- Extract accurate data only, use null for uncertain fields
- Price should be numeric only (no currency symbols)
- Detect brand from title if not explicitly stated
- Be precise with product name and variant"""


async def extract_with_ai(url: str, html: str, retailer: Dict) -> Dict[str, Any]:
    """Use AI to extract product data when structured data is insufficient."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Get page title
    title = soup.find("title")
    title_text = title.string if title else "Unknown"
    
    # Get main content (remove scripts, styles, nav, footer)
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    
    # Get text content
    text_content = soup.get_text(separator="\n", strip=True)
    # Truncate to avoid token limits
    text_content = text_content[:4000]
    
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": URL_EXTRACTION_PROMPT.format(
                    url=url,
                    title=title_text,
                    content=text_content
                )
            }],
            max_tokens=800,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean markdown if present
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        return {"error": str(e)}


# ============================================
# MAIN EXTRACTION FUNCTION
# ============================================

async def extract_from_url(url: str) -> Dict[str, Any]:
    """
    Main function to extract product data from a URL.
    
    Returns structured product data suitable for comparison.
    """
    # Detect retailer
    retailer = detect_retailer(url)
    logger.info(f"Detected retailer: {retailer['name']} for URL: {url}")
    
    # Fetch page
    html = await fetch_page(url)
    if not html:
        return {
            "success": False,
            "error": "Failed to fetch URL",
            "url": url
        }
    
    # Extract data based on retailer
    if "amazon" in retailer["key"]:
        raw_data = extract_amazon_data(html, url)
    elif "noon" in retailer["key"]:
        raw_data = extract_noon_data(html, url)
    else:
        raw_data = extract_generic_data(html, url)
    
    # If insufficient data, use AI extraction
    if not raw_data.get("title") or not raw_data.get("price"):
        logger.info("Insufficient structured data, using AI extraction")
        ai_data = await extract_with_ai(url, html, retailer)
        # Merge AI data with raw data (raw data takes precedence)
        for key, value in ai_data.items():
            if key not in raw_data or raw_data[key] is None:
                raw_data[key] = value
    
    # Normalize to our schema
    normalized = normalize_product_data(raw_data, retailer, url)
    
    return {
        "success": True,
        "product": normalized,
        "retailer": retailer,
        "source_url": url,
        "extraction_method": "structured" if raw_data.get("title") else "ai"
    }


def normalize_product_data(raw: Dict, retailer: Dict, url: str) -> Dict[str, Any]:
    """Normalize extracted data to our standard schema."""
    
    # Parse brand and name from title if needed
    title = raw.get("title") or raw.get("full_title") or "Unknown Product"
    brand = raw.get("brand")
    name = raw.get("name") or title
    
    # Try to extract brand from title
    if not brand:
        known_brands = [
            "Apple", "Samsung", "Google", "Sony", "LG", "Huawei", "Xiaomi",
            "OnePlus", "OPPO", "Vivo", "Nokia", "Motorola", "Dell", "HP",
            "Lenovo", "ASUS", "Acer", "Microsoft", "Nike", "Adidas", "Puma"
        ]
        for b in known_brands:
            if b.lower() in title.lower():
                brand = b
                break
    
    return {
        "brand": brand,
        "name": name,
        "full_name": title,
        "variant": raw.get("variant"),
        "category": raw.get("category", "other"),
        "price": {
            "amount": raw.get("price"),
            "currency": raw.get("currency") or retailer.get("currency", "USD"),
            "retailer": retailer.get("name"),
            "url": url,
            "in_stock": raw.get("in_stock", raw.get("availability"))
        },
        "specs": raw.get("specs", {}),
        "reviews": {
            "rating": raw.get("rating"),
            "count": raw.get("review_count")
        },
        "image_url": raw.get("image_url"),
        "source_url": url,
        "retailer": retailer
    }


# ============================================
# COMPARE FROM URLs
# ============================================

async def compare_from_urls(url1: str, url2: str, region: str = "bahrain") -> Dict[str, Any]:
    """
    Compare two products from their URLs.
    
    Args:
        url1: First product URL
        url2: Second product URL
        region: Region for additional price lookup
    
    Returns:
        Comparison result with both products
    """
    from app.services.structured_comparison_service import get_comparison_service
    from app.services.extraction_service import generate_comparison
    
    # Extract both products in parallel
    import asyncio
    results = await asyncio.gather(
        extract_from_url(url1),
        extract_from_url(url2),
        return_exceptions=True
    )
    
    products = []
    errors = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"URL {i+1}: {str(result)}")
        elif not result.get("success"):
            errors.append(f"URL {i+1}: {result.get('error', 'Extraction failed')}")
        else:
            products.append(result["product"])
    
    if len(products) < 2:
        return {
            "success": False,
            "error": "Could not extract both products",
            "details": errors
        }
    
    # Generate comparison
    comparison = await generate_comparison(products[0], products[1], region)
    
    return {
        "success": True,
        "products": products,
        "comparison": comparison,
        "winner_index": comparison.get("winner_index", 0),
        "recommendation": comparison.get("recommendation", ""),
        "key_differences": comparison.get("key_differences", []),
        "source_urls": [url1, url2]
    }
