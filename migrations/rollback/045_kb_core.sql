-- Rollback for migration 045_kb_core.sql (S81-14 KB-SCHEMA, S81)
--
-- No flag to flip first: no code reads or writes kb_* in this unit. DESTRUCTIVE:
-- every knowledge-base row is lost. Functions that read the tables go first,
-- then the view, then the tables children first (their triggers go with them),
-- then the trigger function and the GTIN check function the tables used.

BEGIN;

DROP FUNCTION IF EXISTS public.kb_product_card(text, text);
DROP FUNCTION IF EXISTS public.kb_prune_feedback(integer);
DROP FUNCTION IF EXISTS public.kb_prune_offers(integer, integer);
DROP VIEW IF EXISTS public.kb_offers_latest;
DROP TABLE IF EXISTS public.kb_feedback;
DROP TABLE IF EXISTS public.kb_gaps;
DROP TABLE IF EXISTS public.kb_reviews;
DROP TABLE IF EXISTS public.kb_specs;
DROP TABLE IF EXISTS public.kb_images;
DROP TABLE IF EXISTS public.kb_offers;
DROP TABLE IF EXISTS public.kb_variants;
DROP TABLE IF EXISTS public.kb_products;
DROP TABLE IF EXISTS public.kb_merchants;
DROP TABLE IF EXISTS public.kb_coverage_daily;
DROP FUNCTION IF EXISTS public.kb_set_updated_at();
DROP FUNCTION IF EXISTS public.kb_gtin_check_digit_ok(text);

COMMIT;
