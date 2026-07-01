-- Rollback 033: drop product_prices.title
--
-- Safe: the column is only written/read when ENABLE_PRICE_TITLE_PERSIST is ON.
-- Flip that flag OFF BEFORE running this rollback so no in-flight insert/select
-- references the column, then drop it.

BEGIN;

ALTER TABLE public.product_prices
  DROP COLUMN IF EXISTS title;

COMMIT;
