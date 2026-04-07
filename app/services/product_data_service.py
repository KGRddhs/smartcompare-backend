"""Product Data Service — L2 cache (DB) for specs, prices, and reviews.

Redis (L1) has short TTLs (7d specs, 24h prices, 7d reviews).
DB (L2) has longer TTLs (30d specs, 1d prices, 14d reviews).
On Redis miss, check DB before burning API credits.
Price rows are appended (history), specs/reviews are upserted.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)

# Freshness thresholds for L2 cache
SPECS_DB_TTL = timedelta(days=30)
PRICE_DB_TTL = timedelta(days=1)
REVIEWS_DB_TTL = timedelta(days=14)


async def get_cached_specs(product_key: str) -> Optional[Dict[str, Any]]:
    """Fetch specs from DB if fresher than 30 days."""
    try:
        client = get_admin_supabase_client()
        response = (
            client.table("product_specs")
            .select("specs, fetched_at")
            .eq("product_key", product_key)
            .single()
            .execute()
        )
        if not response.data:
            return None
        fetched_at = datetime.fromisoformat(response.data["fetched_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - fetched_at > SPECS_DB_TTL:
            return None
        return response.data["specs"]
    except Exception as e:
        logger.debug(f"L2 specs miss for {product_key}: {e}")
        return None


async def save_specs(
    product_key: str, brand: str, name: str,
    variant: Optional[str], category: Optional[str], specs: Dict[str, Any]
) -> None:
    """Upsert specs into product_specs."""
    try:
        client = get_admin_supabase_client()
        client.table("product_specs").upsert(
            {
                "product_key": product_key,
                "brand": brand,
                "name": name,
                "variant": variant,
                "category": category,
                "specs": specs,
                "source": "gpt",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="product_key",
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to save specs for {product_key}: {e}")


async def get_cached_price(product_key: str, region: str) -> Optional[Dict[str, Any]]:
    """Fetch latest price from DB if fresher than 24h."""
    try:
        client = get_admin_supabase_client()
        response = (
            client.table("product_prices")
            .select("amount, currency, retailer, url, source_method, estimated, fetched_at")
            .eq("product_key", product_key)
            .eq("region", region)
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        fetched_at = datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - fetched_at > PRICE_DB_TTL:
            return None
        return {
            "amount": float(row["amount"]) if row["amount"] is not None else None,
            "currency": row["currency"],
            "retailer": row["retailer"],
            "url": row["url"],
            "source_method": row["source_method"],
            "estimated": row["estimated"] or False,
        }
    except Exception as e:
        logger.debug(f"L2 price miss for {product_key}/{region}: {e}")
        return None


async def save_price(
    product_key: str, brand: str, name: str,
    variant: Optional[str], region: str, price_data: Dict[str, Any]
) -> None:
    """Append a price row (keeps history)."""
    try:
        client = get_admin_supabase_client()
        client.table("product_prices").insert({
            "product_key": product_key,
            "brand": brand,
            "name": name,
            "variant": variant,
            "region": region,
            "amount": price_data.get("amount"),
            "currency": price_data.get("currency"),
            "retailer": price_data.get("retailer"),
            "url": price_data.get("url"),
            "source_method": price_data.get("source_method"),
            "estimated": price_data.get("estimated", False),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to save price for {product_key}/{region}: {e}")


async def get_cached_reviews(product_key: str) -> Optional[Dict[str, Any]]:
    """Fetch reviews from DB if fresher than 14 days."""
    try:
        client = get_admin_supabase_client()
        response = (
            client.table("product_reviews")
            .select("reviews, fetched_at")
            .eq("product_key", product_key)
            .single()
            .execute()
        )
        if not response.data:
            return None
        fetched_at = datetime.fromisoformat(response.data["fetched_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - fetched_at > REVIEWS_DB_TTL:
            return None
        return response.data["reviews"]
    except Exception as e:
        logger.debug(f"L2 reviews miss for {product_key}: {e}")
        return None


async def save_reviews(
    product_key: str, brand: str, name: str,
    variant: Optional[str], reviews: Dict[str, Any]
) -> None:
    """Upsert reviews into product_reviews."""
    try:
        client = get_admin_supabase_client()
        client.table("product_reviews").upsert(
            {
                "product_key": product_key,
                "brand": brand,
                "name": name,
                "variant": variant,
                "reviews": reviews,
                "source": "gpt",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="product_key",
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to save reviews for {product_key}: {e}")
