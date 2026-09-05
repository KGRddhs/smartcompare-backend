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
from app.utils.db_offload import run_db  # M13-05 / #115 ENABLE_SYNC_DB_OFFLOAD

logger = logging.getLogger(__name__)

# Freshness thresholds for L2 cache
SPECS_DB_TTL = timedelta(days=30)
PRICE_DB_TTL = timedelta(days=1)
REVIEWS_DB_TTL = timedelta(days=14)

# Faithful-Results Phase 1 (Task 1.1) — a GENUINE Bahrain shelf price stays
# fresh at L2 for a week (matches the L1 GENUINE_PRICE_CACHE_TTL). The OLD flat
# 24h window wrongly rejected a 3-day-old genuine row at L2 → re-burned a scrape.
# A converted/estimated row keeps the 24h window so it refreshes toward a genuine
# price sooner. Env-overridable to mirror the L1 knob.
import os as _os
GENUINE_PRICE_DB_TTL = timedelta(
    seconds=int(_os.getenv("GENUINE_PRICE_CACHE_TTL_SECONDS", str(7 * 24 * 60 * 60)))
)

# Issue #54 — how many recent `product_prices` rows the L2 read inspects when the
# clobber guard is ON. `product_prices` is append-only (save_price is a plain
# insert, no dedup), so a Tier-3 estimate row appended after a genuine one becomes
# the newest row and hides a genuine row that is still inside its OWN 7d window.
# Scanning a short window lets the selector prefer the genuine row. Deliberately
# small: 5 rows is one extra page of a `fetched_at desc` read, not a table scan,
# and it does NOT widen any freshness window — every row still has to pass
# `_price_row_fresh` for its own method.
_L2_PRICE_ROW_SCAN = 5


def _genuine_clobber_guard_enabled() -> bool:
    """Issue #54 — the L2 half of `price_service.genuine_clobber_guard_enabled`.

    Delegates to the ONE definition in price_service (imported lazily, exactly
    like `_price_row_fresh` imports `_GENUINE_BH_SOURCE_METHODS`, so this module
    never grows a module-level dependency on the price cascade). Fail-CLOSED: if
    the import raises, the guard reads OFF and `get_cached_price` keeps its
    pre-#54 behaviour. Never cached — the underlying helper reads os.getenv per
    call so a Railway flip needs no restart."""
    try:
        from app.services.price_service import genuine_clobber_guard_enabled
    except Exception:  # noqa: BLE001 — never let the import change the read path
        return False
    return genuine_clobber_guard_enabled()


def _title_persist_enabled() -> bool:
    """Persist + rehydrate the resolved listing identity (title + in_stock, and
    the ALREADY-persisted brand) on the L2 product_prices cache. Default OFF ->
    byte-identical pre-033/pre-034 behavior (no `title`/`in_stock` in the insert,
    no `title`/`brand`/`in_stock` in the returned dict). Flip ON only AFTER
    migrations 033 (adds nullable `title`) AND 034 (adds nullable `in_stock`)
    land; a flag-ON write before the columns exist would error the fire-and-forget
    insert (swallowed), and a flag-ON read would degrade the L2 hit to a miss
    (get_cached_price swallows it) — never a crash, but the correct order is
    migrations-then-flag. One flag governs the whole title+brand+in_stock
    identity round-trip (Wave-2 B1.2 DB-leg fix)."""
    return _os.getenv("ENABLE_PRICE_TITLE_PERSIST", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _price_row_fresh(source_method: Optional[str], age: timedelta) -> bool:
    """True iff a stored price row of `age` is still fresh for its source_method.

    Genuine-BH methods get the 7d window (GENUINE_PRICE_DB_TTL); converted /
    estimated / unknown methods get the 24h window (PRICE_DB_TTL). Pure decision
    so it is unit-tested without touching Supabase. Defensive: a method
    containing "converted"/"estimate", or a missing one, always uses the short
    window."""
    sm = (source_method or "").lower()
    if sm and "converted" not in sm and "estimate" not in sm:
        try:
            from app.services.price_service import _GENUINE_BH_SOURCE_METHODS
            if sm in _GENUINE_BH_SOURCE_METHODS:
                return age <= GENUINE_PRICE_DB_TTL
        except Exception:  # noqa: BLE001 — never let the import block the read
            pass
    return age <= PRICE_DB_TTL


def _select_price_row(rows: list, now: datetime) -> Optional[Dict[str, Any]]:
    """Issue #54 — pick which of the recent `product_prices` rows the L2 read serves.

    Rule, in order:
      1. Drop every row that is NOT fresh for its own `source_method`
         (`_price_row_fresh` — genuine 7d, converted/estimated 24h). No window is
         widened here; a row that used to be rejected is still rejected.
      2. Of the survivors, return the NEWEST genuine-method row.
      3. If none is genuine, return the newest survivor (today's answer).
      4. Nothing fresh -> None (today's answer).

    Why: `product_prices` is append-only, so an estimate row written after a
    genuine one is newest and used to win — serving a 12h guess over a real
    Bahrain shelf price, and then serving NOTHING once the estimate aged past 24h
    while a genuine row inside its 7d window sat one position deeper.

    Genuineness is `price_service.is_genuine_source_method` — the SAME predicate
    the L1 TTL policy branches on, imported (never re-derived: re-deriving it is
    the drift defect tracked in #67). Pure decision, unit-tested without Supabase.
    Ordering is recomputed here rather than trusted from the query, so the helper
    is correct for any input order; unparseable/missing `fetched_at` rows are
    skipped rather than raising."""
    try:
        from app.services.price_service import is_genuine_source_method
    except Exception:  # noqa: BLE001 — never let the import block the read
        def is_genuine_source_method(_sm):  # type: ignore[misc]
            return False

    fresh = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        raw = row.get("fetched_at")
        if not raw:
            continue
        try:
            fetched_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            age = now - fetched_at
        except Exception:  # noqa: BLE001 — a malformed row is skipped, not fatal
            continue
        if _price_row_fresh(row.get("source_method"), age):
            fresh.append((fetched_at, row))

    if not fresh:
        return None
    fresh.sort(key=lambda pair: pair[0], reverse=True)
    for _fetched_at, row in fresh:
        if is_genuine_source_method(row.get("source_method")):
            return row
    return fresh[0][1]


async def get_cached_specs(product_key: str) -> Optional[Dict[str, Any]]:
    """Fetch specs from DB if fresher than 30 days."""
    try:
        client = get_admin_supabase_client()
        # #115 — all six L2 request-path Supabase round trips in this module
        # route through run_db (ENABLE_SYNC_DB_OFFLOAD; inline byte-identical
        # when OFF).
        response = await run_db(lambda: (
            client.table("product_specs")
            .select("specs, fetched_at")
            .eq("product_key", product_key)
            .single()
            .execute()
        ))
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
        await run_db(lambda: client.table("product_specs").upsert(
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
        ).execute())
    except Exception as e:
        logger.warning(f"Failed to save specs for {product_key}: {e}")


async def get_cached_price(product_key: str, region: str) -> Optional[Dict[str, Any]]:
    """Fetch latest price from DB if fresher than 24h."""
    try:
        client = get_admin_supabase_client()
        cols = "amount, currency, retailer, url, source_method, estimated, fetched_at"
        if _title_persist_enabled():
            cols += ", title"
            # Wave-2 B1.2 — also rehydrate brand (column exists since migration
            # 012; save_price has always written it) + in_stock (migration 034)
            # so a DB-served price is SKU- AND stock-verifiable. Gated by the SAME
            # flag as title so flag-OFF is byte-identical (no extra SELECT cols).
            cols += ", brand, in_stock"
        # Issue #54 — flag OFF reads exactly ONE row and applies the freshness
        # check to it, byte-identically to the pre-#54 code. Flag ON reads a short
        # `fetched_at desc` window so `_select_price_row` can prefer a still-fresh
        # genuine row over a newer estimate row appended on top of it.
        guard_on = _genuine_clobber_guard_enabled()
        row_limit = _L2_PRICE_ROW_SCAN if guard_on else 1
        response = await run_db(lambda: (
            client.table("product_prices")
            .select(cols)
            .eq("product_key", product_key)
            .eq("region", region)
            .order("fetched_at", desc=True)
            .limit(row_limit)
            .execute()
        ))
        if not response.data:
            return None
        if guard_on:
            row = _select_price_row(response.data, datetime.now(timezone.utc))
            if row is None:
                return None
        else:
            row = response.data[0]
            fetched_at = datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00"))
            # Faithful-Results Phase 1 — freshness window depends on source_method:
            # genuine BH price = 7d, converted/estimated = 24h.
            age = datetime.now(timezone.utc) - fetched_at
            if not _price_row_fresh(row.get("source_method"), age):
                return None
        result = {
            "amount": float(row["amount"]) if row["amount"] is not None else None,
            "currency": row["currency"],
            "retailer": row["retailer"],
            "url": row["url"],
            "source_method": row["source_method"],
            "estimated": row["estimated"] or False,
        }
        # Rehydrate the persisted title so the L2-served price is SKU-verifiable
        # (a None title = a legacy/flag-OFF row, treated exactly as pre-033).
        if _title_persist_enabled() and row.get("title"):
            result["title"] = row["title"]
        # Wave-2 B1.2 — rehydrate brand + in_stock under the SAME flag. A None
        # brand or a None in_stock = a legacy/flag-OFF row, so omit it (treated
        # exactly as the pre-034 title-less/stock-less row). Only an explicit
        # bool in_stock is rehydrated, so False correctly re-fires the display
        # OOS pend on the DB-served path.
        if _title_persist_enabled():
            if row.get("brand"):
                result["brand"] = row["brand"]
            if isinstance(row.get("in_stock"), bool):
                result["in_stock"] = row["in_stock"]
        return result
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
        row = {
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
        }
        # Persist the resolved listing title so a rehydrated L2 price stays
        # SKU-verifiable (usable_exact_genuine KPI + should_cache_price). Gated
        # so pre-033 (no column) writes are byte-identical.
        if _title_persist_enabled():
            row["title"] = price_data.get("title")
            # Wave-2 B1.2 — persist in_stock too (migration 034), ONLY when it is
            # an explicit bool. A None/absent in_stock is left off the row so the
            # column stays NULL (= unknown), matching the pre-034 semantics. brand
            # is already persisted unconditionally above (function param).
            _in_stock = price_data.get("in_stock")
            if isinstance(_in_stock, bool):
                row["in_stock"] = _in_stock
        await run_db(lambda: client.table("product_prices").insert(row).execute())
    except Exception as e:
        logger.warning(f"Failed to save price for {product_key}/{region}: {e}")


async def get_cached_reviews(product_key: str) -> Optional[Dict[str, Any]]:
    """Fetch reviews from DB if fresher than 14 days."""
    try:
        client = get_admin_supabase_client()
        response = await run_db(lambda: (
            client.table("product_reviews")
            .select("reviews, fetched_at")
            .eq("product_key", product_key)
            .single()
            .execute()
        ))
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
        await run_db(lambda: client.table("product_reviews").upsert(
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
        ).execute())
    except Exception as e:
        logger.warning(f"Failed to save reviews for {product_key}: {e}")
