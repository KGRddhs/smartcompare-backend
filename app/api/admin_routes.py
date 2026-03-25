"""Admin routes — analytics endpoints protected by API key."""
import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Depends, Query

from app.services.api_budget_service import get_usage_summary
from app.services.database_service import get_supabase_client
from app.services.analytics_service import (
    get_daily_stats,
    get_popular_queries,
    get_cost_trends,
    get_error_stats,
    get_product_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


def verify_admin_key(x_admin_key: str = Header(...)):
    """Verify the admin API key from X-Admin-Key header."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True


@router.get("/stats/daily")
async def daily_stats(
    days: int = Query(30, ge=1, le=365),
    _=Depends(verify_admin_key),
):
    """Daily comparison stats — count, cost, errors, duration."""
    return await get_daily_stats(days)


@router.get("/stats/popular")
async def popular_queries(
    limit: int = Query(20, ge=1, le=100),
    _=Depends(verify_admin_key),
):
    """Most popular comparison queries ranked by frequency."""
    return await get_popular_queries(limit)


@router.get("/stats/costs")
async def cost_trends(
    days: int = Query(30, ge=1, le=365),
    _=Depends(verify_admin_key),
):
    """Cost trends — total, average, daily breakdown."""
    return await get_cost_trends(days)


@router.get("/stats/errors")
async def error_stats(
    days: int = Query(7, ge=1, le=90),
    _=Depends(verify_admin_key),
):
    """Error rate and common error messages."""
    return await get_error_stats(days)


@router.get("/stats/products")
async def product_stats(
    limit: int = Query(20, ge=1, le=100),
    _=Depends(verify_admin_key),
):
    """Most compared products and category breakdown."""
    return await get_product_stats(limit)


@router.get("/costs")
async def api_costs(_=Depends(verify_admin_key)):
    """API cost dashboard — provider budgets, circuit breakers, monthly spend."""
    summary = get_usage_summary()

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0).isoformat()

    # OpenAI cost: sum from comparisons table this month
    openai_cost = 0.0
    try:
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table("comparisons").select("metadata").gte("created_at", month_start).execute()
            for row in (result.data or []):
                meta = row.get("metadata") or {}
                openai_cost += meta.get("total_cost", 0)
    except Exception as e:
        logger.warning(f"[ADMIN] Failed to fetch OpenAI costs: {e}")

    # Comparison count this month
    comp_count = 0
    try:
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table("comparisons").select("id", count="exact").gte("created_at", month_start).execute()
            comp_count = result.count or 0
    except Exception:
        pass

    summary["openai"] = {"cost_usd": round(openai_cost, 4), "source": "comparisons.metadata.total_cost"}
    summary["comparisons_this_month"] = comp_count
    summary["avg_cost_per_comparison"] = round(openai_cost / comp_count, 4) if comp_count > 0 else 0
    summary["fixed_costs_monthly"] = 30.00  # Railway $5 + Supabase $25
    summary["estimated_monthly_total"] = round(summary["fixed_costs_monthly"] + openai_cost, 2)
    summary["period"] = datetime.now(timezone.utc).strftime("%Y-%m")

    return summary
