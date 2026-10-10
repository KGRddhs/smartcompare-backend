"""Admin routes — analytics endpoints protected by API key."""
import hmac
import math
import os
import logging
from datetime import datetime, timedelta, timezone
from starlette.requests import Request
from fastapi import APIRouter, Header, HTTPException, Depends, Query
from typing import Optional

from app.services.api_budget_service import get_usage_summary, get_burn_status
from app.services.cache_service import (
    get_tier15_hit_rate,
    get_tier15_source_hits,
    get_real_price_coverage,
    # Faithful-Results Task 1.6 — cache hit-rate observability.
    get_cache_observability,
)
from app.services.database_service import get_supabase_client, get_admin_supabase_client
from app.services.model_config import standard_model, verdict_model
from app.services.openai_pricing import PRICE_TABLE_AS_OF  # COST-METER (#66)
from app.utils.db_offload import run_db  # COST-METER (#66) G4: never a blocking .execute() on the loop
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


def verify_admin_key(x_admin_key: str = Header(default="")):
    """Verify the admin API key from X-Admin-Key header.

    CR-SECURITY-04: compare BYTES, never ``str``. HTTP header values reach the
    handler latin-1 decoded, so any byte >= 0x80 in ``X-Admin-Key`` produces a
    non-ASCII ``str`` and ``hmac.compare_digest`` on two ``str`` arguments
    raises ``TypeError: comparing strings with non-ASCII characters is not
    supported``. That ``TypeError`` escaped the dependency, became a 500, and
    the 500 was captured by Sentry carrying ``expected`` (the real
    ``ADMIN_API_KEY``) in this frame's locals — i.e. an unauthenticated request
    with one high byte in a header disclosed the production admin key.

    ``errors="surrogateescape"`` so the encode step itself can never raise.
    ``compare_digest`` on ``bytes`` keeps the comparison constant time.

    An ABSENT header is a 403 like a wrong one (``Header(default="")``): a 422
    tells an unauthenticated caller that the header is the thing being checked,
    and it is a different response shape for the same "you are not an admin".

    #304: a whitespace-only ``ADMIN_API_KEY`` counts as unset (``str.strip``);
    the compare stays against the raw value, so a padded key fails closed.
    """
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected.strip() or not hmac.compare_digest(
        x_admin_key.encode("utf-8", errors="surrogateescape"),
        expected.encode("utf-8", errors="surrogateescape"),
    ):
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


# COST-METER (#66, S74/S75) -- the OpenAI figure the two cost endpoints report.
# Every comparison persisted since the unit carries
# ``full_response.metadata.openai`` (openai_pricing.summarize_openai_ledger:
# model ids, token counts, LIST-PRICE USD recorded at guarded_llm_create). The
# read pages through PostgREST with the JSON-path column selection (CM5) so the
# full_response blob is never transferred, falls back to the blob shape when
# the path is rejected, runs every .execute() through the db offload helper
# (G4) and sums ONLY rows that recorded a cost: unknown is null, never 0 (the
# defect this unit fixes: the old read selected a non-existent `metadata`
# column and reported 0 for every month).
OPENAI_COST_NOTE = (
    "List price over persisted comparisons only; excludes Link-mode compares "
    "(never persisted today, issue #340), failed compares and calls cancelled "
    "by the hard cap or retried by the SDK. OpenAI applies its free daily "
    "allowance on its side (organisation data sharing ON since 2026-10-08, "
    "decision D3 = C), so this figure is not a bill."
)
OPENAI_COST_SOURCE = "comparisons.full_response.metadata.openai"
_OPENAI_PAGE = 1000
_OPENAI_MAX_PAGES = 10
_OPENAI_SELECT_JSON_PATH = "id,created_at,full_response->metadata->openai"
_OPENAI_SELECT_BLOB = "id,created_at,full_response"


def _openai_of_row(row, shape):
    """The row's metadata.openai value in either select shape (None when absent)."""
    if shape == "json":
        return row.get("openai")
    full = row.get("full_response")
    meta = full.get("metadata") if isinstance(full, dict) else None
    return meta.get("openai") if isinstance(meta, dict) else None


async def _openai_rows(client, since_iso):
    """Page the comparisons created since ``since_iso``: ordered by created_at
    ASCENDING then id, page i = ``.range(i*1000, i*1000 + 999)`` (inclusive
    ends), a page is full at >= 1000 rows, at most 10 pages, rows
    de-duplicated by id across pages (CM2). Returns ``(rows, truncated)``
    with rows as ``{"id", "created_at", "openai"}``; raises when the client
    raises (the callers read that as unknown, never as 0)."""
    rows = []
    seen = set()
    shape = "json"
    page = 0
    while page < _OPENAI_MAX_PAGES:
        lo = page * _OPENAI_PAGE
        hi = lo + _OPENAI_PAGE - 1
        select = _OPENAI_SELECT_JSON_PATH if shape == "json" else _OPENAI_SELECT_BLOB

        def _fetch(select=select, lo=lo, hi=hi):
            return (
                client.table("comparisons")
                .select(select)
                .gte("created_at", since_iso)
                .order("created_at")
                .order("id")
                .range(lo, hi)
                .execute()
            )

        try:
            result = await run_db(_fetch)
        except Exception as exc:  # noqa: BLE001
            if shape != "json":
                raise
            # CM5: PostgREST rejected the JSON-path selection -> the blob shape
            # for this and every later page; the exception TYPE only (U8d).
            logger.warning(
                "[ADMIN] openai JSON-path select rejected (%s); falling back to the blob select",
                type(exc).__name__,
            )
            shape = "blob"
            continue
        data = result.data or []
        for row in data:
            rid = row.get("id")
            if rid is not None:
                if rid in seen:
                    continue
                seen.add(rid)
            rows.append({
                "id": rid,
                "created_at": row.get("created_at") or "",
                "openai": _openai_of_row(row, shape),
            })
        page += 1
        if len(data) < _OPENAI_PAGE:
            return rows, False
    return rows, True


def _recorded_cost(openai):
    """The finite non-negative cost_usd of a metadata.openai dict, else None."""
    if not isinstance(openai, dict):
        return None
    cost = openai.get("cost_usd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        return None
    if not math.isfinite(cost) or cost < 0:
        return None
    return float(cost)


def _int_field(obj, key):
    value = obj.get(key) if isinstance(obj, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _aggregate_openai(rows, truncated=False):
    """Sum metadata.openai over the paged rows. A row with a finite
    non-negative cost_usd is rows_with_cost; any other row is
    rows_without_cost. Independently of cost presence, a row whose own
    summary says cost_complete False is rows_partial (X2: an ALL-unpriced
    compare is both rows_without_cost and rows_partial). cost_usd is None
    when no row recorded a cost; today_usd is None when no row created today
    did. cost_complete is ALWAYS present: None when no row recorded a cost
    (unknown), False when any row is partial (cost_usd is then a LOWER
    BOUND), else True."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = rows or []
    with_cost = partial = without = 0
    total = 0.0
    today_total = None
    by_day = {}
    calls = prompt = cached = completion = 0
    by_model = {}
    for row in rows:
        openai = row.get("openai")
        cost = _recorded_cost(openai)
        if cost is None:
            without += 1
        else:
            with_cost += 1
            total += cost
            day = (row.get("created_at") or "")[:10]
            by_day[day] = by_day.get(day, 0.0) + cost
            if day == today:
                today_total = (today_total or 0.0) + cost
        if isinstance(openai, dict):
            if openai.get("cost_complete") is False:
                partial += 1
            calls += _int_field(openai, "calls")
            prompt += _int_field(openai, "prompt_tokens")
            cached += _int_field(openai, "cached_tokens")
            completion += _int_field(openai, "completion_tokens")
            models = openai.get("by_model")
            if isinstance(models, dict):
                for model, entry in models.items():
                    target = by_model.setdefault(str(model), {"calls": 0, "cost_usd": None})
                    target["calls"] += _int_field(entry, "calls")
                    model_cost = _recorded_cost(entry)
                    if model_cost is not None:
                        target["cost_usd"] = round((target["cost_usd"] or 0.0) + model_cost, 6)
    if with_cost == 0:
        cost_complete = None
    elif partial > 0:
        cost_complete = False
    else:
        cost_complete = True
    out = {
        "cost_usd": round(total, 6) if with_cost > 0 else None,
        "today_usd": round(today_total, 6) if today_total is not None else None,
        "by_day": {day: round(usd, 6) for day, usd in sorted(by_day.items())},
        "rows": len(rows),
        "rows_with_cost": with_cost,
        "rows_partial": partial,
        "rows_without_cost": without,
        "cost_complete": cost_complete,
        "truncated": bool(truncated),
        "calls": calls,
        "prompt_tokens": prompt,
        "cached_tokens": cached,
        "completion_tokens": completion,
        "by_model": by_model,
        "basis": "list_price",
        "price_table_as_of": PRICE_TABLE_AS_OF,
        "note": OPENAI_COST_NOTE,
        "source": OPENAI_COST_SOURCE,
    }
    return out


@router.get("/costs")
@limiter.limit("30/minute")
async def api_costs(request: Request, _=Depends(verify_admin_key)):
    """API cost dashboard -- provider budgets, circuit breakers, monthly spend.

    COST-METER (#66): ``openai`` is the LIST-PRICE sum of the usage recorded per
    comparison (``metadata.openai``) over this UTC month's persisted rows --
    null when nothing is recorded (no rows, legacy rows only, no client, a
    Supabase error), never 0; ``openai.cost_complete`` is always present
    (None unknown, False a lower bound, True complete; X2);
    ``avg_cost_per_comparison`` averages over the rows WITH a recorded cost
    (partial rows included); ``estimated_monthly_total`` is fixed +
    month-to-date, not a projection (names kept, meaning stated, CM6).
    """
    summary = get_usage_summary()

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0).isoformat()

    # One Supabase client serves both the paged read and the count query (CM3).
    supabase = None
    try:
        supabase = get_supabase_client()
    except Exception as e:  # noqa: BLE001
        logger.warning("[ADMIN] Supabase client unavailable for the cost read: %s", type(e).__name__)

    openai_rows = None
    openai_truncated = False
    if supabase:
        try:
            openai_rows, openai_truncated = await _openai_rows(supabase, month_start)
        except Exception as e:  # noqa: BLE001
            logger.warning("[ADMIN] Failed to fetch OpenAI costs: %s", type(e).__name__)
    openai = _aggregate_openai(openai_rows, openai_truncated)
    openai_cost = openai["cost_usd"]

    # Comparison count this month
    comp_count = 0
    try:
        if supabase:
            result = await run_db(
                lambda: supabase.table("comparisons").select("id", count="exact").gte("created_at", month_start).execute()
            )
            comp_count = result.count or 0
    except Exception:
        pass

    summary["openai"] = openai
    summary["comparisons_this_month"] = comp_count
    summary["avg_cost_per_comparison"] = (
        round(openai_cost / openai["rows_with_cost"], 6)
        if openai_cost is not None and openai["rows_with_cost"] > 0
        else None
    )
    summary["fixed_costs_monthly"] = 30.00  # Railway $5 + Supabase $25
    summary["estimated_monthly_total"] = (
        round(summary["fixed_costs_monthly"] + openai_cost, 2) if openai_cost is not None else None
    )
    summary["period"] = datetime.now(timezone.utc).strftime("%Y-%m")

    # B.0 (Lane F1, F1.6) — Tier 1.5 escalation hit-rate, per-category 7-day
    # window. attempts = escalations that entered the scrape pool; hits =
    # scraped/structured winners returned (vs GPT-estimate fall-through).
    # I5.1 (Bundle B S2) adds `by_source` — which registry/legacy domains
    # produced the wins (the F1.7 attribution residual; counters already
    # write per-domain). Fail-open: zeroed block when Redis is down.
    try:
        summary["tier1_5_hit_rate"] = {
            "window_days": 7,
            "by_category": get_tier15_hit_rate(days=7),
            "by_source": get_tier15_source_hits(days=7),
        }
    except Exception as e:
        logger.warning(f"[ADMIN] tier1_5_hit_rate aggregate failed: {e}")
        summary["tier1_5_hit_rate"] = {
            "window_days": 7, "by_category": {}, "by_source": {}
        }

    # S3 L1.5 — real-price-coverage: per-category live ratio of REAL prices
    # (page_scrape/shopify_json/local_bhd/converted_usd/...) vs GPT estimates.
    # The prod-runtime dial for Ahmed's "facts not estimation" directive (the
    # eval-side estimate-share is L4's, in eval_runner). Fail-open zeroed block.
    try:
        summary["real_price_coverage"] = {
            "window_days": 7,
            "by_category": get_real_price_coverage(days=7),
        }
    except Exception as e:
        logger.warning(f"[ADMIN] real_price_coverage aggregate failed: {e}")
        summary["real_price_coverage"] = {"window_days": 7, "by_category": {}}

    # Faithful-Results Task 1.6 — cache hit-rate observability: how much of the
    # genuine-price load is served from cache ($0) vs freshly scraped. The dial
    # that proves the warmer + 7d genuine-TTL cache are working
    # (genuine_cache_share). Fail-open zeroed block.
    try:
        summary["cache_observability"] = {
            "window_days": 7,
            **get_cache_observability(days=7),
        }
    except Exception as e:
        logger.warning(f"[ADMIN] cache_observability aggregate failed: {e}")
        summary["cache_observability"] = {
            "window_days": 7, "cache_hits": 0, "genuine_from_cache": 0,
            "genuine_fresh": 0, "genuine_cache_share": 0.0,
        }

    # I5.0 (Bundle B S2) — Serper burn status vs the 80% ceiling. This is the
    # run-integrity canary: a measurement run that crosses 80% trips the
    # Sentry/log alert in api_budget_service; this surfaces the live number so
    # the balance can be reconciled before a full gold-200 re-run.
    try:
        summary["serper_burn"] = get_burn_status("serper")
    except Exception as e:
        logger.warning(f"[ADMIN] serper_burn status failed: {e}")
        summary["serper_burn"] = {}

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
    {"line": "Domain (getmyez.com)", "monthly_usd": 1.5, "notes": "$18/yr"},
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
    """API costs over the window: the OpenAI LIST-PRICE figure recorded per
    persisted comparison (``metadata.openai``, COST-METER #66; null when
    nothing is recorded, never 0; ``openai_paid_usd`` was RENAMED
    ``openai_list_usd`` because the old name asserted a billing fact the data
    cannot carry, CM12; ``cost_complete`` always present, None / False / True
    as in _aggregate_openai, X2), plus Serper / Firecrawl / Scrape.do budgets
    from the api_budget_service Redis counters."""
    client = get_admin_supabase_client()
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    openai_rows = None
    openai_truncated = False
    try:
        if client:
            openai_rows, openai_truncated = await _openai_rows(client, cutoff_iso)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ADMIN] OpenAI cost read failed: %s", type(exc).__name__)
    openai = _aggregate_openai(openai_rows, openai_truncated)

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

    openai_cost = openai["cost_usd"]
    avg_cost_per_request_usd = (
        round(openai_cost / openai["rows_with_cost"], 6)
        if openai_cost is not None and openai["rows_with_cost"] > 0
        else None
    )

    return {
        "window_days": days,
        "openai_list_usd": round(openai_cost, 4) if openai_cost is not None else None,
        "comparisons_with_cost": openai["rows_with_cost"],
        "avg_cost_per_request_usd": avg_cost_per_request_usd,
        "daily_burn": [
            {"day": day, "usd": round(usd, 4)}
            for day, usd in sorted(openai["by_day"].items())
        ],
        "rows": openai["rows"],
        "rows_without_cost": openai["rows_without_cost"],
        "rows_partial": openai["rows_partial"],
        "cost_complete": openai["cost_complete"],
        "truncated": openai["truncated"],
        "basis": openai["basis"],
        "price_table_as_of": openai["price_table_as_of"],
        "note": openai["note"],
        "scrapers": scraper_budgets,
    }


def _function_map():
    """Cost-panel rows. Built per call so the OpenAI rows name the models the
    deployment is ACTUALLY configured with (#58) — the ids are env-overridable,
    so a hardcoded label would silently misreport after a model change."""
    return [
    {
        "service": f"OpenAI {standard_model()}",
        "purpose": "Spec / price / review extraction + product parsing",
        "fires_when": "Every comparison; cached 7d for specs+reviews, 24h for prices",
    },
    {
        "service": f"OpenAI {verdict_model()}",
        "purpose": "Verdict generation only (highest-impact subjective prose)",
        "fires_when": "Every signed-in comparison while daily 4o cap < 80%; falls back to the standard model above threshold",
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
    """Service-to-function map shown on /admin/costs.html."""
    return {"items": _function_map()}


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

    # #268 — the cap the router actually uses (env DAILY_4O_CAP, per call;
    # the class constant when unset or invalid).
    openai_4o_cap = ModelRouterService().daily_4o_cap()

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
