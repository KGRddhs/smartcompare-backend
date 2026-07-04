-- Rollback 034: drop product_prices.in_stock
--
-- Safe: the column is only written/read when ENABLE_PRICE_TITLE_PERSIST is ON
-- (the same flag that governs the title round-trip in migration 033). Flip that
-- flag OFF BEFORE running this rollback so no in-flight insert/select references
-- the column, then drop it.

BEGIN;

ALTER TABLE public.product_prices
  DROP COLUMN IF EXISTS in_stock;

COMMIT;
