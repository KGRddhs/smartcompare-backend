"""
Cache Service - Redis caching and rate limiting via Upstash
Supports both standard Redis URLs and Upstash REST API
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Initialize Redis client
UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", "")
UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN", "")

redis_client = None

# Try to initialize Redis
if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
    try:
        # Check if it's a REST API URL (https://) or standard Redis URL (redis://)
        if UPSTASH_REDIS_URL.startswith("https://"):
            # Use upstash-redis for REST API
            try:
                from upstash_redis import Redis
                redis_client = Redis(url=UPSTASH_REDIS_URL, token=UPSTASH_REDIS_TOKEN)
                logger.info("Upstash Redis (REST) client initialized")
            except ImportError:
                logger.warning("upstash-redis not installed, caching disabled")
                redis_client = None
        else:
            # Standard Redis URL (redis:// or rediss://)
            import redis
            redis_client = redis.from_url(
                UPSTASH_REDIS_URL,
                password=UPSTASH_REDIS_TOKEN,
                decode_responses=True
            )
            logger.info("Standard Redis client initialized")
    except Exception as e:
        logger.warning(f"Redis initialization failed (non-fatal): {e}")
        redis_client = None
else:
    logger.info("Redis not configured - caching disabled")


# ============================================
# HELPER: Redis operations with fallback
# ============================================

def _redis_get(key: str) -> Optional[str]:
    """Get value from Redis with error handling."""
    if not redis_client:
        return None
    try:
        result = redis_client.get(key)
        if hasattr(result, 'decode'):
            return result.decode()
        return result
    except Exception as e:
        logger.error(f"Redis GET error: {e}")
        return None


def _redis_set(key: str, value: str, ex: int = None) -> bool:
    """Set value in Redis with error handling."""
    if not redis_client:
        return False
    try:
        if ex:
            redis_client.setex(key, ex, value)
        else:
            redis_client.set(key, value)
        return True
    except Exception as e:
        logger.error(f"Redis SET error: {e}")
        return False


def _redis_incr(key: str) -> int:
    """Increment value in Redis."""
    if not redis_client:
        return 0
    try:
        return int(redis_client.incr(key) or 0)
    except Exception as e:
        logger.error(f"Redis INCR error: {e}")
        return 0


def _redis_expire(key: str, seconds: int) -> bool:
    """Set expiry on key."""
    if not redis_client:
        return False
    try:
        redis_client.expire(key, seconds)
        return True
    except Exception as e:
        logger.error(f"Redis EXPIRE error: {e}")
        return False


# ============================================
# GENERIC CACHE FUNCTIONS
# ============================================

def get_cached(key: str) -> Optional[Dict[str, Any]]:
    """Get a value from cache by key."""
    data = _redis_get(key)
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def set_cached(key: str, value: Dict[str, Any], ttl: int = 86400) -> bool:
    """Set a value in cache with TTL."""
    try:
        return _redis_set(key, json.dumps(value), ex=ttl)
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


def delete_cached(key: str) -> bool:
    """Delete a key from cache."""
    if not redis_client:
        return False
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


# ============================================
# CACHE KEY GENERATORS
# ============================================

def get_product_cache_key(product_name: str, country: str = "default") -> str:
    """Generate cache key for product data."""
    normalized = product_name.lower().strip().replace(' ', '_')
    return f"product:{country}:{normalized}"


def get_price_cache_key(product_name: str, country: str) -> str:
    """Generate cache key for price data."""
    normalized = product_name.lower().strip().replace(' ', '_')
    return f"price:{country}:{normalized}"


def get_comparison_cache_key(products: list, country: str) -> str:
    """Generate cache key for comparison results."""
    product_key = "_vs_".join(sorted([p.lower().replace(' ', '_') for p in products]))
    return f"comparison:{country}:{product_key}"


# ============================================
# PRICE CACHE (used by comparison_service.py)
# ============================================

CACHE_DURATION = int(os.getenv("CACHE_DURATION", "86400"))  # 24 hours default


def get_cached_price(product_name: str, country: str) -> Optional[Dict[str, Any]]:
    """
    Get cached price for a product.
    Used by comparison_service.py
    """
    key = get_price_cache_key(product_name, country)
    return get_cached(key)


def cache_price(product_name: str, country: str, price_data: Dict[str, Any], ttl: int = None) -> bool:
    """
    Cache price data for a product.
    Used by comparison_service.py
    """
    key = get_price_cache_key(product_name, country)
    return set_cached(key, price_data, ttl or CACHE_DURATION)


# ============================================
# PRODUCT CACHE
# ============================================

def get_product_cache(product_name: str, country: str) -> Optional[Dict[str, Any]]:
    """Get cached product data."""
    key = get_product_cache_key(product_name, country)
    return get_cached(key)


def set_product_cache(product_name: str, country: str, data: Dict[str, Any], ttl: int = None) -> bool:
    """Cache product data."""
    key = get_product_cache_key(product_name, country)
    return set_cached(key, data, ttl or CACHE_DURATION)


def get_comparison_cache(products: list, country: str) -> Optional[Dict[str, Any]]:
    """Get cached comparison result."""
    key = get_comparison_cache_key(products, country)
    return get_cached(key)


def set_comparison_cache(products: list, country: str, data: Dict[str, Any], ttl: int = None) -> bool:
    """Cache comparison result."""
    key = get_comparison_cache_key(products, country)
    return set_cached(key, data, ttl or CACHE_DURATION)


# ============================================
# RATE LIMITING
# ============================================

FREE_TIER_DAILY_LIMIT = int(os.getenv("FREE_TIER_DAILY_LIMIT", "5"))


def check_rate_limit(user_id: str, is_premium: bool = False) -> Dict[str, Any]:
    """Check if user has exceeded their daily rate limit."""
    if is_premium:
        return {
            "allowed": True,
            "current_usage": 0,
            "daily_limit": None,
            "remaining": None
        }
    
    daily_limit = FREE_TIER_DAILY_LIMIT
    current_usage = get_user_daily_usage(user_id)
    
    return {
        "allowed": current_usage < daily_limit,
        "current_usage": current_usage,
        "daily_limit": daily_limit,
        "remaining": max(0, daily_limit - current_usage)
    }


def get_user_daily_usage(user_id: str) -> int:
    """Get user's usage count for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"usage:{user_id}:{today}"
    
    data = _redis_get(key)
    return int(data) if data else 0


def increment_user_daily_usage(user_id: str) -> int:
    """Increment user's daily usage count."""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"usage:{user_id}:{today}"
    
    count = _redis_incr(key)
    _redis_expire(key, 86400)  # Expire after 24 hours
    return count


# ============================================
# API COST TRACKING (used by comparison_service.py)
# ============================================

MAX_MONTHLY_COST = float(os.getenv("MAX_MONTHLY_COST", "100"))


def track_api_cost(cost: float, service: str = "unknown") -> float:
    """
    Track API cost for billing/monitoring.
    Used by comparison_service.py
    
    Args:
        cost: Cost in USD
        service: Service name (openai, serper, etc.)
    
    Returns:
        New monthly total
    """
    return add_api_cost(cost)


def check_monthly_budget(budget_limit: float = None) -> Dict[str, Any]:
    """Check if monthly API budget has been exceeded."""
    limit = budget_limit or MAX_MONTHLY_COST
    current_cost = get_monthly_cost()
    
    return {
        "allowed": current_cost < limit,
        "current_cost": current_cost,
        "budget_limit": limit,
        "remaining": max(0, limit - current_cost)
    }


def get_monthly_cost() -> float:
    """Get total API cost for current month."""
    month = datetime.now().strftime("%Y-%m")
    key = f"cost:{month}"
    
    data = _redis_get(key)
    return float(data) if data else 0.0


def add_api_cost(cost: float) -> float:
    """Add to monthly API cost tracker."""
    if not redis_client:
        return 0.0
    
    month = datetime.now().strftime("%Y-%m")
    key = f"cost:{month}"
    
    try:
        current = get_monthly_cost()
        new_total = current + cost
        _redis_set(key, str(new_total), ex=32 * 86400)
        return new_total
    except Exception as e:
        logger.error(f"Error adding API cost: {e}")
        return 0.0


# ============================================
# HEALTH CHECK
# ============================================

def health_check() -> Dict[str, Any]:
    """Check Redis connection health."""
    if not redis_client:
        return {
            "status": "not configured",
            "message": "Redis/cache disabled - running without caching"
        }
    
    try:
        redis_client.set("health_check", "ok")
        result = redis_client.get("health_check")
        if result:
            return {
                "status": "healthy",
                "message": "Redis connection OK"
            }
        return {
            "status": "degraded",
            "message": "Redis connected but not responding correctly"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}"
        }
