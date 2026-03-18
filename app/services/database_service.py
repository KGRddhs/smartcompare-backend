"""
Database Service - Supabase integration for storing comparisons and user data
"""
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend

supabase: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


# ============================================
# User Functions
# ============================================

async def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID"""
    try:
        client = get_supabase_client()
        response = client.table("users").select("*").eq("id", user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    try:
        client = get_supabase_client()
        response = client.table("users").select("*").eq("email", email).single().execute()
        return response.data
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None


async def create_user(email: str, subscription_tier: str = "free") -> Optional[Dict]:
    """Create a new user"""
    try:
        client = get_supabase_client()
        response = client.table("users").insert({
            "email": email,
            "subscription_tier": subscription_tier
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


async def update_user_subscription(
    user_id: str, 
    tier: str, 
    expires_at: Optional[datetime] = None
) -> bool:
    """Update user's subscription tier"""
    try:
        client = get_supabase_client()
        update_data = {
            "subscription_tier": tier,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if expires_at:
            update_data["subscription_expires_at"] = expires_at.isoformat()
        
        client.table("users").update(update_data).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating subscription: {e}")
        return False


# ============================================
# Comparison Functions
# ============================================

async def save_comparison(
    full_response: Dict,
    query: str,
    input_type: str = "text",
    user_id: Optional[str] = None,
) -> Optional[Dict]:
    """
    Save a comparison to the database.

    Args:
        full_response: The entire API response dict (products, comparison, metadata, etc.)
        query: Original search query
        input_type: "text" or "camera"
        user_id: Authenticated user's ID, or None for anonymous

    Returns:
        Saved comparison record or None on failure
    """
    try:
        client = get_supabase_client()

        # Extract product names for indexing
        products = full_response.get("products", [])
        product_names = []
        for p in products:
            name = f"{p.get('brand', '')} {p.get('name', '')}".strip()
            if name:
                product_names.append(name)

        record = {
            "full_response": full_response,
            "query": query,
            "input_type": input_type,
            "product_names": product_names,
        }

        if user_id:
            record["user_id"] = user_id

        response = client.table("comparisons").insert(record).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        # Fire-and-forget — never break the comparison response
        logger.warning(f"Error saving comparison: {e}", exc_info=True)
        return None


async def get_user_comparisons(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
) -> List[Dict]:
    """Get user's comparison history, optionally filtered by product name search."""
    try:
        client = get_supabase_client()
        query = (
            client.table("comparisons")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )

        if search:
            query = query.ilike("query", f"%{search}%")

        response = query.range(offset, offset + limit - 1).execute()
        return response.data or []
    except Exception as e:
        print(f"Error getting comparisons: {e}")
        return []


async def get_comparison_by_id(comparison_id: str) -> Optional[Dict]:
    """Get a specific comparison by ID"""
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .select("*")
            .eq("id", comparison_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"Error getting comparison: {e}")
        return None


async def delete_comparison(comparison_id: str, user_id: str) -> bool:
    """Delete a comparison (only if owned by user)."""
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .delete()
            .eq("id", comparison_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0 if response.data else False
    except Exception as e:
        print(f"Error deleting comparison: {e}")
        return False


async def create_share_token(comparison_id: str, user_id: str) -> Optional[str]:
    """
    Generate a share token for a comparison.
    Verifies ownership. Returns existing token if already shared.
    Retries on collision (max 3 attempts).
    """
    import secrets

    try:
        client = get_supabase_client()

        # Fetch comparison and verify ownership
        comparison = await get_comparison_by_id(comparison_id)
        if not comparison:
            return None
        if comparison.get("user_id") != user_id:
            raise PermissionError("Not authorized to share this comparison")

        # Return existing token if already shared
        existing_token = comparison.get("share_token")
        if existing_token:
            return existing_token

        # Generate and store token (retry on collision)
        for attempt in range(3):
            token = secrets.token_urlsafe(6)  # 8 chars
            try:
                response = (
                    client.table("comparisons")
                    .update({"share_token": token})
                    .eq("id", comparison_id)
                    .eq("user_id", user_id)
                    .execute()
                )
                if response.data:
                    return token
            except Exception as e:
                if "unique" in str(e).lower() and attempt < 2:
                    continue  # Retry with new token
                raise

        return None
    except PermissionError:
        raise
    except Exception as e:
        logger.warning(f"Error creating share token: {e}", exc_info=True)
        return None


async def get_shared_comparison(share_token: str) -> Optional[Dict]:
    """
    Get a shared comparison by share token. No auth required.
    Strips personalization fields from full_response.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .select("id, query, product_names, input_type, full_response, created_at")
            .eq("share_token", share_token)
            .single()
            .execute()
        )
        if not response.data:
            return None

        data = response.data

        # Strip personalization fields from full_response
        full_response = data.get("full_response", {})
        if isinstance(full_response, dict):
            for key in ("personalized", "personalization_factors", "personalization_prompt"):
                full_response.pop(key, None)
            data["full_response"] = full_response

        return data
    except Exception as e:
        logger.warning(f"Error getting shared comparison: {e}", exc_info=True)
        return None


async def get_user_comparison_count(user_id: str) -> int:
    """Get total number of comparisons for a user"""
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return response.count or 0
    except Exception as e:
        print(f"Error counting comparisons: {e}")
        return 0


# ============================================
# Search Logging Functions
# ============================================

async def log_search(
    query: str,
    input_type: str = "text",
    user_id: Optional[str] = None,
    products_found: Optional[List[str]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    cost: float = 0.0,
    duration_ms: int = 0,
) -> None:
    """
    Log a search/comparison request for analytics. Fire-and-forget.

    Args:
        query: The search query
        input_type: "text" or "camera"
        user_id: Authenticated user ID or None
        products_found: List of product names identified
        success: Whether the comparison succeeded
        error_message: Error message if failed
        cost: Total API cost in USD
        duration_ms: Request duration in milliseconds
    """
    try:
        client = get_supabase_client()
        record = {
            "query": query,
            "input_type": input_type,
            "products_found": products_found or [],
            "success": success,
            "cost": cost,
            "duration_ms": duration_ms,
        }
        if user_id:
            record["user_id"] = user_id
        if error_message:
            record["error_message"] = error_message

        client.table("search_logs").insert(record).execute()
    except Exception as e:
        # Never fail the request for logging
        logger.warning(f"Error logging search: {e}", exc_info=True)


# ============================================
# Product Dedup Functions
# ============================================

async def upsert_product(
    canonical_name: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[str]:
    """
    Upsert a product by exact canonical_name. Returns product ID.
    Updates last_seen_at on existing records.
    """
    try:
        client = get_supabase_client()
        response = client.table("products").upsert(
            {
                "canonical_name": canonical_name,
                "brand": brand,
                "category": category,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="canonical_name",
        ).execute()
        return response.data[0]["id"] if response.data else None
    except Exception as e:
        print(f"Error upserting product: {e}")
        return None


async def upsert_products_from_comparison(full_response: Dict) -> List[str]:
    """
    Upsert all products from a comparison response. Returns list of product IDs.
    """
    product_ids = []
    for product in full_response.get("products", []):
        name = f"{product.get('brand', '')} {product.get('name', '')}".strip()
        if name:
            pid = await upsert_product(
                canonical_name=name,
                brand=product.get("brand"),
                category=product.get("category"),
            )
            if pid:
                product_ids.append(pid)
    return product_ids


# ============================================
# Health Check
# ============================================

async def health_check() -> Dict:
    """Check database connection health"""
    try:
        client = get_supabase_client()
        # Simple query to test connection
        client.table("users").select("id").limit(1).execute()
        return {"status": "healthy", "connection": "ok"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
