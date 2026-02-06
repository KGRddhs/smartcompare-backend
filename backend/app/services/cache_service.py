"""
Cache Service - Redis caching for price data and rate limiting
"""
import os
import json
import hashlib
from typing import Optional, Dict
from datetime import date, datetime
import redis

# Initialize Redis client
# Upstash uses REST API, but redis-py works with their Redis URL
REDIS_URL = os.getenv("UPSTASH_REDIS_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN", "")

# For Upstash, we need to use their REST URL format
# Convert REST URL to Redis URL if needed
if REDIS_URL.startswith("https://"):
    # Upstash REST URL - construct Redis URL
    # Format: rediss://default:TOKEN@HOST:PORT
    host = REDIS_URL.replace("https://", "").rstrip("/")
    redis_url = f"rediss://default:{REDIS_TOKEN}@{host}:6379"
else:
    redis_url = REDIS_URL

try:
    redis_client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0
    )
except Exception as e:
    print(f"Redis connection error: {e}")
    redis_client = None

# Cache duration (24 hours)
CACHE_DURATION = int(os.getenv("CACHE_DURATION", 86400))

# Rate limiting
FREE_TIER_DAILY_LIMIT = int(os.getenv("FREE_TIER_DAILY_LIMIT", 5))


def get_product_cache_key(
    brand: str,
    name: str,
    size: Optional[str] = None,
    country: str = "Bahrain"
) -> str:
    """
    Generate a consistent cache key for a product.
    
    Uses MD5 hash for consistent key length and to handle special characters.
    """
    # Normalize inputs
    parts = [
        brand.lower().strip(),
        name.lower().strip(),
        (size or "").lower().strip(),
        country.lower().strip()
    ]
    key_string = "|".join(parts)
    
    # Hash for consistent key length
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    return f"price:{key_hash}"


def get_cached_price(cache_key: str) -> Optional[Dict]:
    """
    Retrieve cached price data.
    
    Args:
        cache_key: Cache key from get_product_cache_key()
    
    Returns:
        Cached price data dict or None if not found/expired
    """
    if not redis_client:
        return None
    
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            data["from_cache"] = True
            return data
        return None
    except redis.RedisError as e:
        print(f"Redis read error: {e}")
        return None
    except json.JSONDecodeError:
        return None


def cache_price(cache_key: str, price_data: Dict) -> bool:
    """
    Cache price data with 24-hour expiry.
    
    Args:
        cache_key: Cache key from get_product_cache_key()
        price_data: Price information to cache
    
    Returns:
        True if cached successfully, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        # Add timestamp
        price_data["cached_at"] = datetime.utcnow().isoformat()
        
        redis_client.setex(
            cache_key,
            CACHE_DURATION,
            json.dumps(price_data)
        )
        return True
    except redis.RedisError as e:
        print(f"Redis write error: {e}")
        return False


def get_user_daily_usage(user_id: str) -> int:
    """
    Get user's comparison count for today.
    
    Args:
        user_id: User's unique identifier
    
    Returns:
        Number of comparisons made today
    """
    if not redis_client:
        return 0
    
    key = f"usage:{user_id}:{date.today().isoformat()}"
    
    try:
        count = redis_client.get(key)
        return int(count) if count else 0
    except redis.RedisError:
        return 0


def increment_user_daily_usage(user_id: str) -> int:
    """
    Increment user's daily comparison count.
    
    Args:
        user_id: User's unique identifier
    
    Returns:
        New count after increment
    """
    if not redis_client:
        return 0
    
    key = f"usage:{user_id}:{date.today().isoformat()}"
    
    try:
        count = redis_client.incr(key)
        # Set expiry to 25 hours (in case of timezone edge cases)
        redis_client.expire(key, 90000)
        return count
    except redis.RedisError as e:
        print(f"Redis usage tracking error: {e}")
        return 0


def check_rate_limit(user_id: str, is_premium: bool = False) -> Dict:
    """
    Check if user has exceeded their daily limit.
    
    Args:
        user_id: User's unique identifier
        is_premium: Whether user has premium subscription
    
    Returns:
        {
            "allowed": True/False,
            "current_usage": 3,
            "daily_limit": 5 or None,
            "remaining": 2 or None
        }
    """
    # Premium users have no limit
    if is_premium:
        return {
            "allowed": True,
            "current_usage": get_user_daily_usage(user_id),
            "daily_limit": None,
            "remaining": None
        }
    
    current_usage = get_user_daily_usage(user_id)
    
    return {
        "allowed": current_usage < FREE_TIER_DAILY_LIMIT,
        "current_usage": current_usage,
        "daily_limit": FREE_TIER_DAILY_LIMIT,
        "remaining": max(0, FREE_TIER_DAILY_LIMIT - current_usage)
    }


def track_api_cost(cost: float) -> float:
    """
    Track API costs for the current month.
    
    Args:
        cost: Cost in USD to add
    
    Returns:
        Total monthly cost after addition
    """
    if not redis_client:
        return 0.0
    
    month_key = f"monthly_cost:{datetime.now().strftime('%Y-%m')}"
    
    try:
        # Increment by cost (Redis doesn't have incrbyfloat for all versions)
        current = redis_client.get(month_key)
        current_cost = float(current) if current else 0.0
        new_cost = current_cost + cost
        
        redis_client.setex(
            month_key,
            32 * 86400,  # 32 days expiry
            str(new_cost)
        )
        return new_cost
    except redis.RedisError as e:
        print(f"Cost tracking error: {e}")
        return 0.0


def get_monthly_cost() -> float:
    """Get total API cost for current month."""
    if not redis_client:
        return 0.0
    
    month_key = f"monthly_cost:{datetime.now().strftime('%Y-%m')}"
    
    try:
        cost = redis_client.get(month_key)
        return float(cost) if cost else 0.0
    except redis.RedisError:
        return 0.0


def check_monthly_budget(max_budget: float = 100.0) -> Dict:
    """
    Check if monthly API budget is exceeded.
    
    Args:
        max_budget: Maximum monthly budget in USD
    
    Returns:
        {
            "allowed": True/False,
            "current_spend": 45.50,
            "budget": 100.0,
            "remaining": 54.50,
            "percentage_used": 45.5
        }
    """
    current_spend = get_monthly_cost()
    percentage = (current_spend / max_budget) * 100 if max_budget > 0 else 0
    
    return {
        "allowed": current_spend < max_budget,
        "current_spend": round(current_spend, 2),
        "budget": max_budget,
        "remaining": round(max_budget - current_spend, 2),
        "percentage_used": round(percentage, 1)
    }


def health_check() -> Dict:
    """Check Redis connection health."""
    if not redis_client:
        return {
            "status": "disconnected",
            "error": "Redis client not initialized"
        }
    
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "connection": "ok"
        }
    except redis.RedisError as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
