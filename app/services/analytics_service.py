"""Analytics service — queries search_logs and products tables for admin dashboards."""
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from app.services.database_service import (
    get_supabase_client,
    search_log_synthetic_marker_enabled,
)

logger = logging.getLogger(__name__)


def _drop_synthetic(records, marker):
    """W4-13 flag 2: drop rows whose is_synthetic IS TRUE; NULL (written before
    the flip / legacy) and False rows are KEPT -- `is not True`, never falsy."""
    if not marker:
        return records, 0
    kept = [r for r in records if r.get("is_synthetic") is not True]
    return kept, len(records) - len(kept)


async def get_daily_stats(days: int = 30) -> Dict:
    """Comparison count, cost, errors aggregated by day."""
    try:
        client = get_supabase_client()
        marker = search_log_synthetic_marker_enabled()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            client.table("search_logs")
            .select("success, cost, duration_ms, created_at" + (", is_synthetic" if marker else ""))
            .gte("created_at", since)
            .execute()
        )
        records, excluded = _drop_synthetic(response.data or [], marker)

        total = len(records)
        successes = sum(1 for r in records if r.get("success"))
        errors = total - successes
        total_cost = sum(float(r.get("cost") or 0) for r in records)
        avg_duration = (
            sum(int(r.get("duration_ms") or 0) for r in records) / total
            if total > 0 else 0
        )

        # Group by day
        daily = Counter()
        for r in records:
            day = r.get("created_at", "")[:10]  # YYYY-MM-DD
            if day:
                daily[day] += 1

        return {
            "total_comparisons": total,
            "success_count": successes,
            "error_count": errors,
            "total_cost": round(total_cost, 4),
            "avg_duration_ms": round(avg_duration),
            "daily_breakdown": dict(sorted(daily.items())),
            "period_days": days,
            **({"synthetic_excluded": excluded} if marker else {}),
        }
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        return {
            "total_comparisons": 0, "success_count": 0,
            "error_count": 0, "total_cost": 0, "avg_duration_ms": 0,
            "daily_breakdown": {}, "period_days": days,
        }


async def get_popular_queries(limit: int = 20) -> List[Dict]:
    """Top queries ranked by frequency."""
    try:
        client = get_supabase_client()
        marker = search_log_synthetic_marker_enabled()
        response = (
            client.table("search_logs")
            .select("query, input_type" + (", is_synthetic" if marker else ""))
            .execute()
        )
        records, _excluded = _drop_synthetic(response.data or [], marker)

        counter = Counter(r.get("query", "") for r in records if r.get("query"))
        return [
            {"query": q, "count": c}
            for q, c in counter.most_common(limit)
        ]
    except Exception as e:
        logger.error(f"Error getting popular queries: {e}")
        return []


async def get_cost_trends(days: int = 30) -> Dict:
    """Cost aggregation — total, average, trend by day."""
    try:
        client = get_supabase_client()
        marker = search_log_synthetic_marker_enabled()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            client.table("search_logs")
            .select("cost, created_at, success" + (", is_synthetic" if marker else ""))
            .gte("created_at", since)
            .execute()
        )
        records, excluded = _drop_synthetic(response.data or [], marker)

        costs = [float(r.get("cost") or 0) for r in records]
        total = sum(costs)
        avg = total / len(costs) if costs else 0

        # Daily cost
        daily_cost = {}
        for r in records:
            day = r.get("created_at", "")[:10]
            if day:
                daily_cost[day] = daily_cost.get(day, 0) + float(r.get("cost") or 0)

        return {
            "total_cost": round(total, 4),
            "avg_cost_per_comparison": round(avg, 4),
            "comparison_count": len(records),
            "daily_costs": {k: round(v, 4) for k, v in sorted(daily_cost.items())},
            "period_days": days,
            **({"synthetic_excluded": excluded} if marker else {}),
        }
    except Exception as e:
        logger.error(f"Error getting cost trends: {e}")
        return {
            "total_cost": 0, "avg_cost_per_comparison": 0,
            "comparison_count": 0, "daily_costs": {}, "period_days": days,
        }


async def get_error_stats(days: int = 7) -> Dict:
    """Error rate and common error messages."""
    try:
        client = get_supabase_client()
        marker = search_log_synthetic_marker_enabled()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            client.table("search_logs")
            .select("success, error_message, created_at" + (", is_synthetic" if marker else ""))
            .gte("created_at", since)
            .execute()
        )
        records, excluded = _drop_synthetic(response.data or [], marker)

        total = len(records)
        errors = [r for r in records if not r.get("success")]
        error_rate = len(errors) / total if total > 0 else 0

        error_messages = Counter(
            r.get("error_message", "Unknown") for r in errors
        )

        return {
            "total_requests": total,
            "error_count": len(errors),
            "error_rate": round(error_rate, 3),
            "common_errors": [
                {"message": msg, "count": c}
                for msg, c in error_messages.most_common(10)
            ],
            "period_days": days,
            **({"synthetic_excluded": excluded} if marker else {}),
        }
    except Exception as e:
        logger.error(f"Error getting error stats: {e}")
        return {
            "total_requests": 0, "error_count": 0, "error_rate": 0,
            "common_errors": [], "period_days": days,
        }


async def get_product_stats(limit: int = 20) -> Dict:
    """Most compared products and category breakdown."""
    try:
        client = get_supabase_client()
        response = (
            client.table("products")
            .select("canonical_name, brand, category, updated_at")
            .execute()
        )
        records = response.data or []

        categories = Counter(r.get("category") or "other" for r in records)
        brands = Counter(r.get("brand") or "Unknown" for r in records)

        return {
            "total_products": len(records),
            "category_breakdown": dict(categories.most_common()),
            "top_brands": dict(brands.most_common(limit)),
        }
    except Exception as e:
        logger.error(f"Error getting product stats: {e}")
        return {"total_products": 0, "category_breakdown": {}, "top_brands": {}}
