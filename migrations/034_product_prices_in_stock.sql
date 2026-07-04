-- Migration 034: product_prices.in_stock — persist the resolved in-stock flag
--
-- Companion to migration 033 (product_prices.title). The L2 price cache
-- (product_prices) never stored the resolved listing's in-stock state, so a
-- warmed price rehydrated from Postgres came back with in_stock=None (unknown).
-- That matters for two chokepoints:
--   * the usable_exact_genuine KPI counts a row as usable only when in_stock is
--     not False (an OOS price must NOT count), and
--   * is_price_showable(enforce_correctness) pends an in_stock=False price
--     (guard_rejected='out_of_stock').
-- Without a persisted flag, a genuinely in-stock warmed price that goes OUT OF
-- STOCK mid-TTL can never be detected on the DB-served path, and the OOS display
-- pend can never re-fire for a rehydrated price.
--
-- This adds a nullable `in_stock BOOLEAN` column so save_price can persist it and
-- get_cached_price can rehydrate it, making a warmed price's stock state durably
-- checkable on the cache-served path. NULL = unknown, treated exactly as the
-- pre-034 (title-less/stock-less) row.
--
-- SAME FLAG as 033: the application code writes/reads BOTH the title (033) and
-- in_stock + brand (034) columns only when ENABLE_PRICE_TITLE_PERSIST is ON —
-- one flag now governs the whole title+brand+in_stock identity round-trip.
--
-- ROLLOUT ORDER (important): apply migration 033 AND this migration 034 FIRST,
-- then flip ENABLE_PRICE_TITLE_PERSIST=true. The application code only
-- writes/reads these columns when that flag is ON (default OFF = byte-identical
-- to today), so a deploy with the code but without the columns is a no-op, and
-- flipping the flag before the columns exist would only degrade the L2 read to a
-- miss (never a crash — get_cached_price swallows the error).
--
-- Plan: docs/plans/2026-07-03-wave2-variantdescriptor-recon.md (B1.2 DB-leg fix)
-- Rollback: migrations/rollback/034_product_prices_in_stock.sql
-- Additive + nullable → safe, no backfill, no lock of note on a small table.

BEGIN;

ALTER TABLE public.product_prices
  ADD COLUMN IF NOT EXISTS in_stock BOOLEAN;

COMMENT ON COLUMN public.product_prices.in_stock IS
  'Resolved listing in-stock flag, persisted so a rehydrated L2 price stays '
  'stock-checkable (usable_exact_genuine KPI + is_price_showable OOS pend). '
  'Written/read only when ENABLE_PRICE_TITLE_PERSIST is ON (the same flag that '
  'governs the title round-trip in migration 033). Nullable: legacy rows + '
  'flag-OFF writes have NULL = unknown, which the app treats exactly as the '
  'pre-034 row.';

COMMIT;
