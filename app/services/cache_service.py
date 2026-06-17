"""
Cache Service - Redis caching and rate limiting via Upstash
Supports both standard Redis URLs and Upstash REST API
"""
import os
import json
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

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
# B.0 (Lane F1, F1.6) — Tier 1.5 hit-rate metrics
# ============================================
# Per-category + per-source escalation counters, fire-and-forget + fail-open.
# An "attempt" = Tier 1.5 escalation entered the page-scrape candidate pool;
# a "hit" = a scraped/structured winner was returned (vs falling through to a
# GPT estimate). Surfaced as `tier1_5_hit_rate` on /admin/costs.

_TIER15_METRIC_TTL = 30 * 86400  # 30 days


def _utc_daystamp(offset_days: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=offset_days)).strftime("%Y%m%d")


def record_tier15_attempt(category: str) -> None:
    """Count one Tier 1.5 escalation attempt for `category` (today, UTC)."""
    if not redis_client:
        return
    key = f"tier15:attempts:{category}:{_utc_daystamp()}"
    if _redis_incr(key) == 1:
        _redis_expire(key, _TIER15_METRIC_TTL)


def record_tier15_hit(category: str, domain: Optional[str] = None) -> None:
    """Count one Tier 1.5 scraped/structured hit for `category` (+ winning
    `domain`, when known), today (UTC).

    G1 finding F2: the winning host is normalized to its registry apex
    (uae.sharafdg.com -> sharafdg.com) before recording, so a regional
    subdomain win lands under the apex the reader probes. Off-registry hosts
    (legacy-fallback wins) record under their own normalized host."""
    if not redis_client:
        return
    cat_key = f"tier15:hits:{category}:{_utc_daystamp()}"
    if _redis_incr(cat_key) == 1:
        _redis_expire(cat_key, _TIER15_METRIC_TTL)
    if domain:
        try:
            from app.services.source_router import match_registry_apex
            domain = match_registry_apex(domain)
        except Exception:  # noqa: BLE001 — normalization is best-effort
            domain = str(domain).lower()
        src_key = f"tier15:source_hits:{domain}:{_utc_daystamp()}"
        if _redis_incr(src_key) == 1:
            _redis_expire(src_key, _TIER15_METRIC_TTL)


def get_tier15_hit_rate(days: int = 7, categories: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Aggregate the trailing `days`-window attempts/hits per category.

    Returns `{category: {attempts, hits, hit_rate}}`. Fail-open: a missing or
    down Redis yields a well-formed zeroed block (never raises).

    All counter keys are fetched in a SINGLE `mget` so the /admin/costs
    endpoint adds one Redis round-trip, not days*categories*2 blocking calls.
    """
    if categories is None:
        categories = [
            "electronics", "grocery", "supplements", "makeup", "skincare",
            "haircare", "fragrances", "fashion", "other",
        ]
    daystamps = [_utc_daystamp(i) for i in range(days)]

    # Build the full key list (attempts + hits, per category per day) and the
    # zeroed result up front so we can early-return on any Redis failure.
    out: Dict[str, Dict[str, Any]] = {
        cat: {"attempts": 0, "hits": 0, "hit_rate": 0.0} for cat in categories
    }
    if not redis_client:
        return out

    keys: List[str] = []
    for cat in categories:
        for ds in daystamps:
            keys.append(f"tier15:attempts:{cat}:{ds}")
            keys.append(f"tier15:hits:{cat}:{ds}")

    try:
        values = redis_client.mget(*keys)
    except TypeError:
        # Some clients take a single iterable rather than *args.
        try:
            values = redis_client.mget(keys)
        except Exception as e:
            logger.warning(f"[TIER15] hit-rate mget failed: {e}")
            return out
    except Exception as e:
        logger.warning(f"[TIER15] hit-rate mget failed: {e}")
        return out

    # values aligns 1:1 with `keys` (attempts, hits interleaved per cat/day).
    idx = 0
    for cat in categories:
        attempts = 0
        hits = 0
        for _ in daystamps:
            a = values[idx] if idx < len(values) else None
            h = values[idx + 1] if idx + 1 < len(values) else None
            idx += 2
            try:
                attempts += int(a) if a else 0
            except (TypeError, ValueError):
                pass
            try:
                hits += int(h) if h else 0
            except (TypeError, ValueError):
                pass
        out[cat] = {
            "attempts": attempts,
            "hits": hits,
            "hit_rate": round(hits / attempts, 4) if attempts > 0 else 0.0,
        }
    return out


# ============================================
# S3 L1.5 — real-price-coverage metric
# ============================================
# Per-category live gauge of how many priced products got a REAL price vs a GPT
# estimate. The PROD-runtime counterpart to L4's eval estimate-share (no
# double-build: L4 owns the % in the gold eval run via eval_runner; this owns
# the live /admin/costs gauge). Fire-and-forget + fail-open, same shape as the
# F1.6 tier1_5 counters. Surfaced as `real_price_coverage` on /admin/costs —
# the dial that shows Ahmed's "facts not estimation" progress per category.

# A source_method is "estimated" iff it contains "estimate" (gpt_training_
# estimate / estimated). Everything else (local_bhd, page_scrape, shopify_json,
# converted_usd, firecrawl, scrapedo_rendered, page_scrape_jsonld,
# firecrawl_brand_domain, confirmed_multi_source, …) is a REAL price.

def _price_outcome_bucket(source_method: Optional[str]) -> str:
    """'estimated' when the method is missing or contains 'estimate', else 'real'."""
    sm = (source_method or "").lower()
    if not sm or "estimate" in sm:
        return "estimated"
    return "real"


def record_price_outcome(category: str, source_method: Optional[str]) -> None:
    """Count one priced-product outcome for `category` (today, UTC): a `real`
    price or an `estimated` one, classified from `source_method`.

    Fire-and-forget + fail-open — never raises, no-op when Redis is down.
    """
    if not redis_client:
        return
    bucket = _price_outcome_bucket(source_method)
    key = f"price_outcome:{bucket}:{category}:{_utc_daystamp()}"
    if _redis_incr(key) == 1:
        _redis_expire(key, _TIER15_METRIC_TTL)


def get_real_price_coverage(
    days: int = 7, categories: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """Aggregate the trailing `days`-window real/estimated price outcomes per
    category.

    Returns `{category: {real, estimated, total, real_share}}`. Fail-open: a
    missing/down Redis yields a well-formed zeroed block (never raises). Single
    `mget` for the whole window, like get_tier15_hit_rate.
    """
    if categories is None:
        categories = [
            "electronics", "grocery", "supplements", "makeup", "skincare",
            "haircare", "fragrances", "fashion", "other",
        ]
    daystamps = [_utc_daystamp(i) for i in range(days)]

    out: Dict[str, Dict[str, Any]] = {
        cat: {"real": 0, "estimated": 0, "total": 0, "real_share": 0.0}
        for cat in categories
    }
    if not redis_client:
        return out

    keys: List[str] = []
    for cat in categories:
        for ds in daystamps:
            keys.append(f"price_outcome:real:{cat}:{ds}")
            keys.append(f"price_outcome:estimated:{cat}:{ds}")

    try:
        values = redis_client.mget(*keys)
    except TypeError:
        try:
            values = redis_client.mget(keys)
        except Exception as e:
            logger.warning(f"[PRICE_COVERAGE] mget failed: {e}")
            return out
    except Exception as e:
        logger.warning(f"[PRICE_COVERAGE] mget failed: {e}")
        return out

    idx = 0
    for cat in categories:
        real = 0
        estimated = 0
        for _ in daystamps:
            r = values[idx] if idx < len(values) else None
            e = values[idx + 1] if idx + 1 < len(values) else None
            idx += 2
            try:
                real += int(r) if r else 0
            except (TypeError, ValueError):
                pass
            try:
                estimated += int(e) if e else 0
            except (TypeError, ValueError):
                pass
        total = real + estimated
        out[cat] = {
            "real": real,
            "estimated": estimated,
            "total": total,
            "real_share": round(real / total, 4) if total > 0 else 0.0,
        }
    return out


# ============================================
# S? Faithful-Results Task 1.6 — cache hit-rate observability
# ============================================
# Per-day counters of price cache outcomes so /admin/costs shows how much of the
# genuine-price load is served from cache ($0) vs freshly scraped — the dial that
# proves the warmer + long-TTL cache are working. Three buckets per day:
#   cache_hit       — a price served from cache (any method)
#   genuine_cache   — a GENUINE-BH price served from cache (the warmer win)
#   genuine_fresh   — a GENUINE-BH price freshly resolved (a scrape was spent)
# Fire-and-forget + fail-open, same shape as record_price_outcome.

def record_cache_observability(cache_hit: bool, genuine_from_cache: bool, genuine_fresh: bool) -> None:
    """Count one comparison's price cache outcome (today, UTC). Each flag that is
    True increments its day bucket. Fail-open — no-op when Redis is down."""
    if not redis_client:
        return
    ds = _utc_daystamp()
    for flag, name in (
        (cache_hit, "cache_hit"),
        (genuine_from_cache, "genuine_cache"),
        (genuine_fresh, "genuine_fresh"),
    ):
        if flag:
            key = f"cache_obs:{name}:{ds}"
            if _redis_incr(key) == 1:
                _redis_expire(key, _TIER15_METRIC_TTL)


def get_cache_observability(days: int = 7) -> Dict[str, Any]:
    """Aggregate the trailing `days`-window cache outcomes.

    Returns `{cache_hits, genuine_from_cache, genuine_fresh, genuine_cache_share}`
    where genuine_cache_share = genuine_from_cache / (genuine_from_cache +
    genuine_fresh) — the fraction of genuine prices served at $0. Fail-open to a
    zeroed block; single mget for the whole window."""
    out = {
        "cache_hits": 0, "genuine_from_cache": 0, "genuine_fresh": 0,
        "genuine_cache_share": 0.0,
    }
    if not redis_client:
        return out
    daystamps = [_utc_daystamp(i) for i in range(days)]
    names = ["cache_hit", "genuine_cache", "genuine_fresh"]
    keys = [f"cache_obs:{n}:{ds}" for n in names for ds in daystamps]
    try:
        values = redis_client.mget(*keys)
    except TypeError:
        try:
            values = redis_client.mget(keys)
        except Exception as e:
            logger.warning(f"[CACHE_OBS] mget failed: {e}")
            return out
    except Exception as e:
        logger.warning(f"[CACHE_OBS] mget failed: {e}")
        return out
    totals = {n: 0 for n in names}
    idx = 0
    for n in names:
        for _ in daystamps:
            v = values[idx] if idx < len(values) else None
            idx += 1
            try:
                totals[n] += int(v) if v else 0
            except (TypeError, ValueError):
                pass
    gen_cache = totals["genuine_cache"]
    gen_fresh = totals["genuine_fresh"]
    gen_total = gen_cache + gen_fresh
    out["cache_hits"] = totals["cache_hit"]
    out["genuine_from_cache"] = gen_cache
    out["genuine_fresh"] = gen_fresh
    out["genuine_cache_share"] = round(gen_cache / gen_total, 4) if gen_total > 0 else 0.0
    return out


def _registry_domains() -> List[str]:
    """Domains to probe for per-domain source-hit aggregation. Defaults to the
    Bahrain-first source registry so the dashboard works without a
    hand-maintained list. Best-effort import — empty list if unavailable."""
    try:
        from app.services.source_router import SOURCE_REGISTRY
        # De-dup while preserving registry order (Bahrain-first).
        seen: Dict[str, None] = {}
        for s in SOURCE_REGISTRY:
            seen.setdefault(s.domain.lower(), None)
        return list(seen.keys())
    except Exception as e:  # noqa: BLE001 — registry import is best-effort
        logger.warning(f"[TIER15] registry domain import failed: {e}")
        return []


def _legacy_domains() -> List[str]:
    """Legacy-whitelist domains a Tier-1.5 win can be recorded under when the
    registry-first gate falls through to `route="legacy_fallback"` (the old
    OFFICIAL_BRAND_DOMAINS / AUTHORIZED_LUXURY_RETAILERS / GCC_LUXURY_RETAILERS
    sets). G1 finding F3: by_source was structurally blind to these — the
    reader only probed registry apexes, so legacy wins were written but never
    read. Best-effort import — empty list if unavailable."""
    try:
        from app.services.price_service import (
            OFFICIAL_BRAND_DOMAINS,
            AUTHORIZED_LUXURY_RETAILERS,
            GCC_LUXURY_RETAILERS,
        )
        registry = set(_registry_domains())
        seen: Dict[str, None] = {}
        for group in (OFFICIAL_BRAND_DOMAINS, AUTHORIZED_LUXURY_RETAILERS, GCC_LUXURY_RETAILERS):
            for d in group:
                dl = str(d).lower()
                # A domain that is ALSO a registry apex belongs to the registry
                # bucket — keep the legacy bucket to genuinely-legacy domains.
                if dl not in registry:
                    seen.setdefault(dl, None)
        return list(seen.keys())
    except Exception as e:  # noqa: BLE001 — legacy import is best-effort
        logger.warning(f"[TIER15] legacy domain import failed: {e}")
        return []


def _aggregate_source_hits(domains: List[str], daystamps: List[str]) -> Dict[str, int]:
    """Single-`mget` sum of tier15:source_hits:{domain}:{day} over the window,
    returning `{domain: hits}` for hits>0, descending. Fail-open to `{}`."""
    if not redis_client or not domains:
        return {}
    keys: List[str] = []
    for d in domains:
        for ds in daystamps:
            keys.append(f"tier15:source_hits:{d.lower()}:{ds}")
    try:
        values = redis_client.mget(*keys)
    except TypeError:
        try:
            values = redis_client.mget(keys)
        except Exception as e:
            logger.warning(f"[TIER15] source-hits mget failed: {e}")
            return {}
    except Exception as e:
        logger.warning(f"[TIER15] source-hits mget failed: {e}")
        return {}

    idx = 0
    totals: Dict[str, int] = {}
    for d in domains:
        total = 0
        for _ in daystamps:
            v = values[idx] if idx < len(values) else None
            idx += 1
            try:
                total += int(v) if v else 0
            except (TypeError, ValueError):
                pass
        if total > 0:
            totals[d.lower()] = total
    # Sort descending by hit count (stable on ties → registry order preserved).
    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))


def get_tier15_source_hits(
    days: int = 7, domains: Optional[List[str]] = None
):
    """I5.1 — aggregate the trailing `days`-window per-domain Tier-1.5 hits, so
    /admin/costs surfaces WHICH domains produced the scraped wins (the F1.7
    registry-vs-legacy attribution residual).

    Two return shapes:
    - `domains=<explicit list>` → flat `{domain: hits}` (hits>0, descending) —
      back-compat for callers probing a known set.
    - `domains=None` (default) → bucketed `{"registry": {...}, "legacy": {...}}`
      probing BOTH the registry apexes AND the legacy whitelist, so
      legacy_fallback wins are VISIBLE (G1 finding F3 — the reader was
      registry-only and structurally blind to them).

    The winning host is normalized to its registry apex at record time
    (`record_tier15_hit`, F2). Single `mget` per bucket; fail-open on Redis
    down.
    """
    daystamps = [_utc_daystamp(i) for i in range(days)]

    if domains is not None:
        # Explicit probe — flat back-compat shape.
        return _aggregate_source_hits(domains, daystamps)

    # Default probe — bucketed registry vs legacy.
    return {
        "registry": _aggregate_source_hits(_registry_domains(), daystamps),
        "legacy": _aggregate_source_hits(_legacy_domains(), daystamps),
    }


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
# NEGATIVE CACHE (Faithful-Results Task 1.3)
# ============================================
# A structural genuine-BH dead-end (luxury fragrance/haircare/gadgets behind
# Cloudflare — no genuine BH source exists) is recorded under a `nogenuine:`
# sentinel so the expensive Tier-1.5 scrape cascade is not re-run on every
# request. The stored value is the LAST non-genuine resolution (a converted/
# estimated price or a price-pending shape), served directly on a sentinel hit.
# Fail-open like the rest of the cache: a missing/down Redis is a normal miss.

def get_negative_cache(negative_key: str) -> Optional[Dict[str, Any]]:
    """Read a negative-cache sentinel (the stored non-genuine result), or None."""
    return get_cached(negative_key)


def set_negative_cache(negative_key: str, value: Dict[str, Any], ttl: int) -> bool:
    """Write a negative-cache sentinel with the structural-dead-end TTL (30d)."""
    return set_cached(negative_key, value, ttl)


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
    """Add to monthly API cost tracker (atomic operation)."""
    if not redis_client:
        return 0.0
    month = datetime.now().strftime("%Y-%m")
    key = f"cost:{month}"
    try:
        new_total = redis_client.incrbyfloat(key, cost)
        _redis_expire(key, 32 * 86400)
        return float(new_total)
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
