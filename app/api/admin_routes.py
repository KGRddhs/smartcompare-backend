"""Admin routes — analytics endpoints protected by API key."""
import hmac
import os
import logging
from datetime import datetime, timedelta, timezone
from starlette.requests import Request
from fastapi import APIRouter, Header, HTTPException, Depends, Query
from typing import Optional

from app.services.api_budget_service import get_usage_summary
from app.services.database_service import get_supabase_client, get_admin_supabase_client
from app.middleware.rate_limiter import limiter
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
    if not expected or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True


@router.get("/stats/daily")
@limiter.limit("30/minute")
async def daily_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    _=Depends(verify_admin_key),
):
    """Daily comparison stats — count, cost, errors, duration."""
    return await get_daily_stats(days)


@router.get("/stats/popular")
@limiter.limit("30/minute")
async def popular_queries(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    _=Depends(verify_admin_key),
):
    """Most popular comparison queries ranked by frequency."""
    return await get_popular_queries(limit)


@router.get("/stats/costs")
@limiter.limit("30/minute")
async def cost_trends(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    _=Depends(verify_admin_key),
):
    """Cost trends — total, average, daily breakdown."""
    return await get_cost_trends(days)


@router.get("/stats/errors")
@limiter.limit("30/minute")
async def error_stats(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    _=Depends(verify_admin_key),
):
    """Error rate and common error messages."""
    return await get_error_stats(days)


@router.get("/stats/products")
@limiter.limit("30/minute")
async def product_stats(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    _=Depends(verify_admin_key),
):
    """Most compared products and category breakdown."""
    return await get_product_stats(limit)


@router.get("/costs")
@limiter.limit("30/minute")
async def api_costs(request: Request, _=Depends(verify_admin_key)):
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


@router.get("/audit-log")
@limiter.limit("30/minute")
async def get_audit_log(
    request: Request,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(7, ge=1, le=90, description="Look back N days"),
    limit: int = Query(100, ge=1, le=500, description="Max entries"),
    _admin=Depends(verify_admin_key),
):
    """Query audit log entries with filters."""
    client = get_admin_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    query = client.table("admin_audit_log").select("*").gte("created_at", since).order("created_at", desc=True).limit(limit)

    if event_type:
        query = query.eq("event_type", event_type)
    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()
    return {"entries": result.data, "count": len(result.data)}


@router.get("/audit-log/summary")
@limiter.limit("30/minute")
async def get_audit_log_summary(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="Look back N days"),
    _admin=Depends(verify_admin_key),
):
    """Get aggregated audit event counts by type."""
    client = get_admin_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = client.table("admin_audit_log").select("event_type").gte("created_at", since).execute()

    counts = {}
    for row in result.data:
        et = row["event_type"]
        counts[et] = counts.get(et, 0) + 1

    return {"period_days": days, "event_counts": counts, "total": sum(counts.values())}


# ============================================
# Cohort metrics (Session 41 — survey-driven personalization)
# ============================================
#
# All three endpoints read from views defined in migration 013:
#   vw_cohort_match_rate, vw_cohort_persona_distribution, vw_cohort_feedback_lift
#
# Auth: existing X-Admin-Key (verify_admin_key) — same as other admin routes.
# Rate limit: 30/minute, matching the rest of the admin surface.


@router.get("/cohort/metrics")
@limiter.limit("30/minute")
async def cohort_metrics(
    request: Request,
    _admin=Depends(verify_admin_key),
):
    """Cohort match rate over time + persona distribution + edit rate.

    Returns:
      {
        "match_rate": [{day, strong_matches, total_with_demographics, total_users}, ...],
        "personas": [{persona, user_count}, ...],
        "submission_rate": <float — total_with_demographics / total_users>,
        "edit_rate": <float — fraction of seeded users who later flipped a source>,
      }
    """
    client = get_admin_supabase_client()

    match_rate_rows: list[dict] = []
    try:
        result = client.table("vw_cohort_match_rate").select("*").order("day", desc=True).limit(90).execute()
        match_rate_rows = result.data or []
    except Exception as e:
        logger.warning(f"[ADMIN] vw_cohort_match_rate read failed: {e}")

    personas: list[dict] = []
    try:
        result = client.table("vw_cohort_persona_distribution").select("*").execute()
        personas = result.data or []
    except Exception as e:
        logger.warning(f"[ADMIN] vw_cohort_persona_distribution read failed: {e}")

    # Submission rate = users with demographics_profile / total users (current).
    submission_rate = 0.0
    try:
        if match_rate_rows:
            with_demo = sum(int(r.get("total_with_demographics", 0) or 0) for r in match_rate_rows[:1])
            total = sum(int(r.get("total_users", 0) or 0) for r in match_rate_rows[:1])
            if total > 0:
                submission_rate = round(with_demo / total, 4)
    except Exception:
        pass

    # Edit rate = users with any _sources.<field> == "user_stated" / users with seeded prefs
    edit_rate = 0.0
    try:
        result = client.table("users").select("preferences").execute()
        rows = result.data or []
        seeded = 0
        edited = 0
        for row in rows:
            prefs = row.get("preferences") or {}
            sources = prefs.get("_sources") if isinstance(prefs, dict) else None
            if not sources:
                continue
            seeded += 1
            if any(v == "user_stated" for v in sources.values() if v):
                edited += 1
        if seeded > 0:
            edit_rate = round(edited / seeded, 4)
    except Exception as e:
        logger.warning(f"[ADMIN] edit_rate calc failed: {e}")

    return {
        "match_rate": match_rate_rows,
        "personas": personas,
        "submission_rate": submission_rate,
        "edit_rate": edit_rate,
    }


@router.get("/cohort/feedback")
@limiter.limit("30/minute")
async def cohort_feedback(
    request: Request,
    _admin=Depends(verify_admin_key),
):
    """Verdict feedback ratings stratified by whether cohort priors were injected.

    Reads vw_cohort_feedback_lift. Used to detect lift (or regression) in
    user-rated verdict quality when cohort-level personalization is on.
    """
    client = get_admin_supabase_client()
    rows: list[dict] = []
    try:
        result = client.table("vw_cohort_feedback_lift").select("*").execute()
        rows = result.data or []
    except Exception as e:
        logger.warning(f"[ADMIN] vw_cohort_feedback_lift read failed: {e}")
    return {"rows": rows}


@router.get("/cohort/retention")
@limiter.limit("30/minute")
async def cohort_retention(
    request: Request,
    days: int = Query(7, ge=1, le=30, description="Return-window in days"),
    _admin=Depends(verify_admin_key),
):
    """7-day return rate stratified by demographics-submission status.

    Two cohorts: users who submitted demographics vs those who didn't.
    Return rate = users who returned within the window after their first
    comparison / total users in that cohort.
    """
    client = get_admin_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days * 2)).isoformat()

    submitted_returned = submitted_total = 0
    not_submitted_returned = not_submitted_total = 0
    try:
        users = client.table("users").select(
            "id, demographics_profile"
        ).gte("created_at", since).execute().data or []
        # For each user, count distinct days they had user_events
        for u in users:
            uid = u.get("id")
            has_demo = u.get("demographics_profile") is not None
            if has_demo:
                submitted_total += 1
            else:
                not_submitted_total += 1

            try:
                events = client.table("user_events").select(
                    "created_at"
                ).eq("user_id", uid).limit(50).execute().data or []
                distinct_days = {(e.get("created_at") or "")[:10] for e in events}
                if len(distinct_days) >= 2:  # ≥ 2 distinct days = returning
                    if has_demo:
                        submitted_returned += 1
                    else:
                        not_submitted_returned += 1
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[ADMIN] cohort retention read failed: {e}")

    def _rate(returned: int, total: int) -> float:
        return round(returned / total, 4) if total > 0 else 0.0

    return {
        "window_days": days,
        "with_demographics": {
            "total": submitted_total,
            "returned": submitted_returned,
            "rate": _rate(submitted_returned, submitted_total),
        },
        "without_demographics": {
            "total": not_submitted_total,
            "returned": not_submitted_returned,
            "rate": _rate(not_submitted_returned, not_submitted_total),
        },
    }
