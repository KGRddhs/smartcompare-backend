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


# ============================================
# Referral metrics dashboard (B6.1)
# ============================================
#
# Backed by tables introduced in migration 014: referral_invites,
# referral_redemptions. Frontend page: /admin/referrals.html.
# Auth: X-Admin-Key (verify_admin_key), rate-limited 30/minute (matches
# the rest of the admin surface).


def _count_since(client, table: str, *, since_iso: str, where: dict) -> int:
    """Count rows in `table` matching `where` filters since `since_iso`."""
    try:
        q = client.table(table).select("id", count="exact").gte("created_at", since_iso)
        for col, val in where.items():
            q = q.eq(col, val)
        return q.execute().count or 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] count_since {table} failed: {exc}")
        return 0


@router.get("/referrals/metrics")
@limiter.limit("30/minute")
async def referrals_metrics(
    request: Request,
    _=Depends(verify_admin_key),
):
    """Volume + conversion + active-referrer metrics.

    Returns counts for week / month / lifetime windows + conversion rate
    (redemptions / invites), suitable for the Chart.js funnel panel.
    """
    client = get_admin_supabase_client()
    now = datetime.now(timezone.utc)
    week_iso = (now - timedelta(days=7)).isoformat()
    month_iso = (now - timedelta(days=30)).isoformat()

    invites_week = _count_since(client, "referral_invites", since_iso=week_iso, where={})
    invites_month = _count_since(client, "referral_invites", since_iso=month_iso, where={})
    redemptions_week = _count_since(client, "referral_redemptions", since_iso=week_iso, where={})
    redemptions_month = _count_since(client, "referral_redemptions", since_iso=month_iso, where={})

    # Lifetime
    try:
        invites_lifetime = client.table("referral_invites").select("id", count="exact").execute().count or 0
        redemptions_lifetime = client.table("referral_redemptions").select("id", count="exact").execute().count or 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] lifetime referral count failed: {exc}")
        invites_lifetime = 0
        redemptions_lifetime = 0

    # Active referrers this month — distinct referrer_user_id with a recent invite
    try:
        ar_resp = (
            client.table("referral_invites")
            .select("referrer_user_id")
            .gte("created_at", month_iso)
            .execute()
        )
        active_referrers_month = len({r["referrer_user_id"] for r in (ar_resp.data or [])})
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] active_referrers query failed: {exc}")
        active_referrers_month = 0

    def _rate(num: int, denom: int) -> float:
        return round(num / denom, 4) if denom > 0 else 0.0

    return {
        "invites": {
            "week": invites_week,
            "month": invites_month,
            "lifetime": invites_lifetime,
        },
        "redemptions": {
            "week": redemptions_week,
            "month": redemptions_month,
            "lifetime": redemptions_lifetime,
        },
        "conversion_rate": {
            "week": _rate(redemptions_week, invites_week),
            "month": _rate(redemptions_month, invites_month),
            "lifetime": _rate(redemptions_lifetime, invites_lifetime),
        },
        "active_referrers_month": active_referrers_month,
    }


@router.get("/referrals/viral")
@limiter.limit("30/minute")
async def referrals_viral(
    request: Request,
    weeks: int = Query(12, ge=1, le=52),
    _=Depends(verify_admin_key),
):
    """K-coefficient trendline over the last N weeks.

    K = avg(invites per referring user) * conversion_rate, computed in
    weekly buckets. Target band: 0.4 - 0.7 per design 8.2.
    """
    client = get_admin_supabase_client()
    now = datetime.now(timezone.utc)
    series = []
    for i in range(weeks):
        end = now - timedelta(days=7 * i)
        start = end - timedelta(days=7)
        start_iso = start.isoformat()
        end_iso = end.isoformat()

        try:
            invites = (
                client.table("referral_invites")
                .select("referrer_user_id")
                .gte("created_at", start_iso)
                .lte("created_at", end_iso)
                .execute()
                .data
                or []
            )
            redemptions = (
                client.table("referral_redemptions")
                .select("id", count="exact")
                .gte("created_at", start_iso)
                .lte("created_at", end_iso)
                .execute()
                .count
                or 0
            )
            distinct_referrers = len({inv["referrer_user_id"] for inv in invites})
            avg_invites = (len(invites) / distinct_referrers) if distinct_referrers > 0 else 0.0
            conversion = (redemptions / len(invites)) if invites else 0.0
            k = avg_invites * conversion
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ADMIN] viral bucket {i} failed: {exc}")
            avg_invites = 0.0
            conversion = 0.0
            k = 0.0

        series.append(
            {
                "week_start": start.date().isoformat(),
                "avg_invites_per_referrer": round(avg_invites, 3),
                "conversion_rate": round(conversion, 4),
                "k": round(k, 3),
            }
        )

    series.reverse()  # oldest first for chart left-to-right
    return {"weeks": weeks, "series": series, "target_band": [0.4, 0.7]}


@router.get("/referrals/cohort_uplift")
@limiter.limit("30/minute")
async def referrals_cohort_uplift(
    request: Request,
    days: int = Query(30, ge=7, le=365),
    _=Depends(verify_admin_key),
):
    """Compare retention + per-user comparisons between referred and
    organic users. Reuses Session 41 user_events for retention checks
    (any user_event in the last `days` window counts as 'returned')."""
    client = get_admin_supabase_client()
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    referred_user_ids: set[str] = set()
    try:
        rr = client.table("referral_redemptions").select("invitee_user_id").execute()
        referred_user_ids = {r["invitee_user_id"] for r in (rr.data or []) if r.get("invitee_user_id")}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] referred user lookup failed: {exc}")

    referred = {"total": len(referred_user_ids), "returned": 0, "comparisons_total": 0}
    organic = {"total": 0, "returned": 0, "comparisons_total": 0}

    try:
        users = client.table("users").select("id").execute().data or []
        organic_ids = [u["id"] for u in users if u["id"] not in referred_user_ids]
        organic["total"] = len(organic_ids)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] organic user list failed: {exc}")
        organic_ids = []

    def _stats_for(user_ids: list[str], group: dict) -> None:
        for uid in user_ids[:500]:  # cap per-call cost; sample only
            try:
                cmp_count = (
                    client.table("comparisons")
                    .select("id", count="exact")
                    .eq("user_id", uid)
                    .gte("created_at", cutoff_iso)
                    .execute()
                    .count
                    or 0
                )
                group["comparisons_total"] += cmp_count
                if cmp_count >= 2:
                    group["returned"] += 1
            except Exception:
                continue

    _stats_for(list(referred_user_ids), referred)
    _stats_for(organic_ids, organic)

    def _rate(num: int, denom: int) -> float:
        return round(num / denom, 4) if denom > 0 else 0.0

    def _avg(total: int, denom: int) -> float:
        return round(total / denom, 2) if denom > 0 else 0.0

    return {
        "window_days": days,
        "referred": {
            **referred,
            "retention_rate": _rate(referred["returned"], referred["total"]),
            "avg_comparisons": _avg(referred["comparisons_total"], referred["total"]),
        },
        "organic": {
            **organic,
            "retention_rate": _rate(organic["returned"], organic["total"]),
            "avg_comparisons": _avg(organic["comparisons_total"], organic["total"]),
        },
    }


@router.get("/referrals/abuse")
@limiter.limit("30/minute")
async def referrals_abuse(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    _=Depends(verify_admin_key),
):
    """Most recent abuse-flagged invites + audit-log events."""
    client = get_admin_supabase_client()

    flagged_invites: list[dict] = []
    try:
        flagged_invites = (
            client.table("referral_invites")
            .select("id, referrer_user_id, redeemed_by_user_id, flagged_reason, created_at")
            .not_.is_("flagged_reason", "null")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] flagged invites read failed: {exc}")

    audit_events: list[dict] = []
    try:
        audit_events = (
            client.table("admin_audit_log")
            .select("event_type, user_id, created_at, details")
            .like("event_type", "referral_%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] audit log read failed: {exc}")

    by_reason: dict[str, int] = {}
    for inv in flagged_invites:
        reason = inv.get("flagged_reason") or "UNKNOWN"
        by_reason[reason] = by_reason.get(reason, 0) + 1

    return {
        "flagged_invites": flagged_invites,
        "audit_events": audit_events,
        "counts_by_reason": by_reason,
    }


# ============================================
# Cost dashboard (B6.2)
# ============================================


_FIXED_SUBSCRIPTIONS = [
    {"line": "Railway Hobby", "monthly_usd": 5.0, "notes": "Backend hosting"},
    {"line": "Railway usage", "monthly_usd": 3.5, "notes": "Variable, ~$2-5/mo at low volume"},
    {"line": "Apple Developer", "monthly_usd": 8.25, "notes": "$99/yr, due Sep 2026"},
    {"line": "Domain (qaren.app)", "monthly_usd": 1.5, "notes": "$18/yr"},
    {"line": "Supabase", "monthly_usd": 0.0, "notes": "Free tier; $25 once over 5K comparisons/day"},
    {"line": "Upstash Redis", "monthly_usd": 0.0, "notes": "Free tier; $5-30 PAYG over ~800/day"},
    {"line": "Sentry", "monthly_usd": 0.0, "notes": "Free tier (5K errors/mo)"},
]


@router.get("/costs/subscriptions")
@limiter.limit("30/minute")
async def costs_subscriptions(
    request: Request,
    _=Depends(verify_admin_key),
):
    """Static list of recurring subscriptions and their monthly USD cost.

    Hardcoded here because these values are stable month-to-month and
    swapping to a config table would just add ops surface for no benefit.
    """
    total = round(sum(line["monthly_usd"] for line in _FIXED_SUBSCRIPTIONS), 2)
    return {"items": _FIXED_SUBSCRIPTIONS, "total_monthly_usd": total}


@router.get("/costs/api")
@limiter.limit("30/minute")
async def costs_api(
    request: Request,
    days: int = Query(30, ge=1, le=90),
    _=Depends(verify_admin_key),
):
    """API costs this month — OpenAI spillover (paid-tier usage), Serper,
    Firecrawl, Scrape.do. OpenAI is read from comparisons.api_calls when
    available; scraper budgets from api_budget_service Redis counters."""
    client = get_admin_supabase_client()
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    openai_total = 0.0
    daily_burn: dict[str, float] = {}
    try:
        rows = (
            client.table("comparisons")
            .select("created_at, full_response")
            .gte("created_at", cutoff_iso)
            .limit(2000)
            .execute()
            .data
            or []
        )
        for row in rows:
            cost = ((row.get("full_response") or {}).get("metadata") or {}).get("total_cost") or 0
            try:
                cost_f = float(cost)
            except (TypeError, ValueError):
                cost_f = 0.0
            day = (row.get("created_at") or "")[:10]
            daily_burn[day] = daily_burn.get(day, 0.0) + cost_f
            openai_total += cost_f
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] OpenAI cost read failed: {exc}")

    # Scraper / Serper budgets via api_budget_service
    scraper_budgets: dict[str, dict] = {}
    try:
        summary = get_usage_summary() or {}
        # api_budget_service returns {providers: {...}, circuit_breakers: {...}};
        # we only surface the providers slice on the cost dashboard.
        scraper_budgets = summary.get("providers") if isinstance(summary, dict) else {}
        scraper_budgets = scraper_budgets or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] scraper budget read failed: {exc}")

    return {
        "window_days": days,
        "openai_paid_usd": round(openai_total, 4),
        "daily_burn": [
            {"day": day, "usd": round(usd, 4)}
            for day, usd in sorted(daily_burn.items())
        ],
        "scrapers": scraper_budgets,
    }


_FUNCTION_MAP = [
    {
        "service": "OpenAI gpt-4o-mini",
        "purpose": "Spec / price / review extraction + product parsing",
        "fires_when": "Every comparison; cached 7d for specs+reviews, 24h for prices",
    },
    {
        "service": "OpenAI gpt-4o",
        "purpose": "Verdict generation only (highest-impact subjective prose)",
        "fires_when": "Every signed-in comparison while daily 4o cap < 80%; falls back to mini above threshold",
    },
    {
        "service": "Serper",
        "purpose": "Google Search + Shopping API for prices + organic snippets",
        "fires_when": "Per comparison (1 unified call shared by specs+reviews); cached 24h",
    },
    {
        "service": "Firecrawl",
        "purpose": "JS-rendered scrape for luxury / SPA brand sites",
        "fires_when": "Tier 1.5a cascade — only when curl_cffi returns no price",
    },
    {
        "service": "Scrape.do",
        "purpose": "Residential-proxy scrape fallback",
        "fires_when": "Tier 1.5d cascade — only when Firecrawl is unavailable",
    },
    {
        "service": "Supabase",
        "purpose": "Auth + RLS-protected storage (users, comparisons, referral_*, etc.)",
        "fires_when": "Per request (cached aggressively via L2 product_data cache)",
    },
    {
        "service": "Upstash Redis",
        "purpose": "L1 response cache + rate limiting + budget counters",
        "fires_when": "Every cache lookup",
    },
    {
        "service": "Expo Push",
        "purpose": "Loop 2 referrer push + 3-type re-engagement notifications",
        "fires_when": "Loop 2 fire + daily cron at 06:00 GCC (max 1/user/week)",
    },
]


@router.get("/costs/function_map")
@limiter.limit("30/minute")
async def costs_function_map(request: Request, _=Depends(verify_admin_key)):
    """Static service-to-function map shown on /admin/costs.html."""
    return {"items": _FUNCTION_MAP}


@router.get("/costs/gauges")
@limiter.limit("30/minute")
async def costs_gauges(request: Request, _=Depends(verify_admin_key)):
    """Cap utilisation gauges. Reads OpenAI 4o usage from the model_router
    Redis counter and scraper budgets from api_budget_service.

    Returns 4 gauges, each with `used / cap / pct` so the dashboard can
    render simple progress bars."""
    from app.services.cache_service import _redis_get
    from app.services.model_router_service import ModelRouterService

    today_key = ModelRouterService()._get_counter_key()

    openai_4o_used = 0
    try:
        raw = _redis_get(today_key)
        openai_4o_used = int(raw) if raw is not None else 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] 4o usage read failed: {exc}")

    openai_4o_cap = ModelRouterService.DAILY_4O_CAP

    scraper_summary: dict = {}
    try:
        scraper_summary = get_usage_summary() or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ADMIN] scraper summary failed: {exc}")

    def _gauge(used: int, cap: int) -> dict:
        pct = round((used / cap) * 100, 2) if cap > 0 else 0.0
        return {"used": used, "cap": cap, "pct": pct}

    providers = scraper_summary.get("providers") or {}
    fc = providers.get("firecrawl") or {}
    sd = providers.get("scrapedo") or {}
    sp = providers.get("serper") or {}

    return {
        "openai_4o_today": _gauge(openai_4o_used, openai_4o_cap),
        "firecrawl_lifetime": _gauge(int(fc.get("used", 0)), int(fc.get("limit", 450))),
        "scrapedo_month": _gauge(int(sd.get("used", 0)), int(sd.get("limit", 900))),
        "serper_lifetime": _gauge(int(sp.get("used", 0)), int(sp.get("limit", 2200))),
    }
