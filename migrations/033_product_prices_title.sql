-- Migration 033: product_prices.title — persist the resolved listing title
--
-- The L2 price cache (product_prices) never stored the resolved/matched listing
-- TITLE, so a warmed price rehydrated from Postgres came back title-less. That
-- title-less price then:
--   * fails the usable_exact_genuine KPI (it needs a title to re-verify the SKU),
--   * fails should_cache_price (title is a hard requirement), so it can never be
--     re-cached, and
--   * is shown by is_price_showable only via the url-OR-title leniency.
-- The Redis L1 object keeps the title (exact gate ON), so a FRESH warm measures
-- usable, but the benefit decays to a title-less DB row after the L1 TTL.
--
-- This adds a nullable `title TEXT` column so save_price can persist it and
-- get_cached_price can rehydrate it, making a warmed price durably SKU-verifiable
-- on the cache-served path.
--
-- ROLLOUT ORDER (important): apply THIS migration FIRST, then flip
-- ENABLE_PRICE_TITLE_PERSIST=true. The application code only writes/reads the
-- column when that flag is ON (default OFF = byte-identical to today), so a
-- deploy with the code but without the column is a no-op, and flipping the flag
-- before the column exists would only degrade the L2 read to a miss (never a
-- crash — get_cached_price swallows the error).
--
-- Plan: docs/plans/2026-06-30-genuine-price-warmer-and-variant-metadata-plan.md
-- Rollback: migrations/rollback/033_product_prices_title.sql
-- Additive + nullable → safe, no backfill, no lock of note on a small table.

BEGIN;

ALTER TABLE public.product_prices
  ADD COLUMN IF NOT EXISTS title TEXT;

COMMENT ON COLUMN public.product_prices.title IS
  'Resolved/matched listing title, persisted so a rehydrated L2 price stays '
  'SKU-verifiable (usable_exact_genuine KPI + should_cache_price). Written/read '
  'only when ENABLE_PRICE_TITLE_PERSIST is ON. Nullable: legacy rows + flag-OFF '
  'writes have NULL, which the app treats exactly as the pre-033 title-less row.';

COMMIT;
