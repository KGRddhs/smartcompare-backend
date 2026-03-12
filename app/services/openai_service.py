"""
OpenAI Service - Vision and text processing for product comparison
"""
import json
import base64
from typing import List, Dict
import httpx
from openai import AsyncOpenAI

# Initialize async client (reads OPENAI_API_KEY from env at request time)
# Explicit timeout: 30s connect (Railway networking can be slow), 120s total
client = AsyncOpenAI(timeout=httpx.Timeout(120.0, connect=30.0))


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
                {"brand": "Apple", "name": "iPhone 16 Pro", "visible_price": "BHD 449", "confidence": "high"},
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
            "text": """You are a product identification expert with OCR skills. Analyze these images and identify EVERY distinct product visible.

CRITICAL: READ the EXACT text printed on each product's packaging, label, or screen. Do NOT guess from memory or training data. Only report what you can actually SEE in the image.

For EACH product found, extract:
- brand: Manufacturer/brand name. Read it from the label/logo/packaging.
- name: The FULL product name exactly as printed on the packaging. Include model numbers, variants, and descriptors. "Vitamin D-3 5000 IU" not just "Vitamin D". "iPhone 16 Pro Max 256GB" not just "iPhone".
- size_or_count: The quantity, count, weight, volume, or storage size printed on the package. Examples: "360 Softgels", "1000mg", "128GB", "500ml", "2.5kg". null if not visible.
- visible_price: Any price shown in the image (shelf tag, screen, label). Include currency symbol. null if not visible.
- confidence: "high" (text clearly readable), "medium" (partially readable, some inference), "low" (best guess)

RULES:
- READ the label text character by character — exact numbers and units matter
- One image may contain MULTIPLE products — identify ALL (up to 4 total across all images)
- For supplements/vitamins: read the EXACT count from the front label (e.g., "360 Softgels", "120 Tablets", "250 Capsules")
- For electronics: read the EXACT model and storage/memory if visible (e.g., "Galaxy S25 Ultra 512GB")
- For food/grocery: read weight, volume, or count (e.g., "500g", "1L", "12 pack")
- Identify products even WITHOUT packaging: use shape, color, logo, design cues (confidence="low")
- For screenshots of retailer pages: extract the product name exactly as shown
- If you see a price tag next to a product, associate it with that product
- Do NOT include markdown code blocks
- Return ONLY a valid JSON array, nothing else

EXAMPLES:
[
  {"brand": "NOW", "name": "Vitamin D-3 5000 IU", "size_or_count": "360 Softgels", "visible_price": "BHD 8.50", "confidence": "high"},
  {"brand": "Apple", "name": "iPhone 16 Pro", "size_or_count": "256GB", "visible_price": null, "confidence": "medium"}
]"""
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
                "detail": "auto"  # "auto" lets GPT choose resolution — needed for reading label text
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

    # Normalize: ensure each product has all expected fields
    normalized = []
    for p in (products if isinstance(products, list) else []):
        normalized.append({
            "brand": p.get("brand") or "Unknown",
            "name": p.get("name") or "Unknown Product",
            "size_or_count": p.get("size_or_count"),
            "visible_price": p.get("visible_price"),
            "confidence": p.get("confidence", "medium"),
        })

    # Calculate cost (gpt-4o-mini pricing)
    # Input: $0.15 per 1M tokens, Output: $0.60 per 1M tokens
    usage = response.usage
    input_cost = (usage.prompt_tokens * 0.15) / 1_000_000
    output_cost = (usage.completion_tokens * 0.60) / 1_000_000
    total_cost = input_cost + output_cost

    return {
        "products": normalized,
        "tokens_used": usage.total_tokens,
        "cost": round(total_cost, 6)
    }
