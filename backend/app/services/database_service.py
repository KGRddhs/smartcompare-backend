"""
Database Service - Supabase integration for storing comparisons and user data
"""
import os
from typing import Dict, List, Optional
from datetime import datetime, date
from supabase import create_client, Client

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
            "updated_at": datetime.utcnow().isoformat()
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
    user_id: str,
    products: List[Dict],
    winner_index: int,
    recommendation: str,
    key_differences: List[str],
    data_source: str,
    total_cost: float,
    image_urls: Optional[List[str]] = None
) -> Optional[Dict]:
    """
    Save a comparison to the database.
    
    Args:
        user_id: User's ID
        products: List of product dicts with price data
        winner_index: Index of winning product
        recommendation: AI recommendation text
        key_differences: List of key differences
        data_source: "live", "cached", or "estimated"
        total_cost: API cost in USD
        image_urls: Optional list of image URLs
    
    Returns:
        Saved comparison record or None
    """
    try:
        client = get_supabase_client()
        
        response = client.table("comparisons").insert({
            "user_id": user_id,
            "image_urls": image_urls or [],
            "products": products,
            "winner_index": winner_index,
            "recommendation": recommendation,
            "key_differences": key_differences,
            "data_source": data_source,
            "total_cost": total_cost
        }).execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving comparison: {e}")
        return None


async def get_user_comparisons(
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict]:
    """Get user's comparison history"""
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
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
# Daily Usage Functions (Database backup for Redis)
# ============================================

async def get_daily_usage_db(user_id: str) -> int:
    """Get user's daily usage from database (backup for Redis)"""
    try:
        client = get_supabase_client()
        today = date.today().isoformat()
        
        response = (
            client.table("daily_usage")
            .select("comparison_count")
            .eq("user_id", user_id)
            .eq("usage_date", today)
            .single()
            .execute()
        )
        
        return response.data["comparison_count"] if response.data else 0
    except Exception as e:
        # Record might not exist
        return 0


async def increment_daily_usage_db(user_id: str) -> int:
    """Increment user's daily usage in database"""
    try:
        client = get_supabase_client()
        today = date.today().isoformat()
        
        # Try to get existing record
        existing = (
            client.table("daily_usage")
            .select("*")
            .eq("user_id", user_id)
            .eq("usage_date", today)
            .execute()
        )
        
        if existing.data:
            # Update existing
            new_count = existing.data[0]["comparison_count"] + 1
            client.table("daily_usage").update({
                "comparison_count": new_count
            }).eq("id", existing.data[0]["id"]).execute()
            return new_count
        else:
            # Insert new
            client.table("daily_usage").insert({
                "user_id": user_id,
                "usage_date": today,
                "comparison_count": 1
            }).execute()
            return 1
    except Exception as e:
        print(f"Error incrementing daily usage: {e}")
        return 0


# ============================================
# Price Cache Functions (Database backup for Redis)
# ============================================

async def cache_price_db(
    product_key: str,
    price: float,
    currency: str,
    retailer: Optional[str] = None,
    confidence: str = "medium"
) -> bool:
    """Cache price in database (backup for Redis)"""
    try:
        client = get_supabase_client()
        
        # Upsert (insert or update)
        client.table("price_cache").upsert({
            "product_key": product_key,
            "price": price,
            "currency": currency,
            "retailer": retailer,
            "confidence": confidence,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        return True
    except Exception as e:
        print(f"Error caching price in DB: {e}")
        return False


async def get_cached_price_db(product_key: str) -> Optional[Dict]:
    """Get cached price from database"""
    try:
        client = get_supabase_client()
        response = (
            client.table("price_cache")
            .select("*")
            .eq("product_key", product_key)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        return None


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
