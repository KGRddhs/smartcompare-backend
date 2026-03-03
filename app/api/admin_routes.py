"""Admin routes — analytics endpoints protected by API key."""
import os
import logging
from fastapi import APIRouter, Header, HTTPException, Depends, Query

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
