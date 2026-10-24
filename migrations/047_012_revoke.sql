-- Migration 047: close the anon / authenticated access migration 012 opened on
-- product_specs, product_prices and product_reviews (S81-14 KB-SCHEMA, S81)
--
-- 012 created eight policies with no TO clause, so they apply to every role
-- (PUBLIC): specs_select / specs_insert / specs_update (USING / WITH CHECK
-- true), prices_select / prices_insert, reviews_select / reviews_insert /
-- reviews_update. With the stock Supabase table grants that lets the public
-- anon key read, insert and update the L2 cache (a poisoning path; M18
-- CD-db-rls-03, PLAN_S81 A2). This file drops the eight policies BY NAME and
-- revokes every table privilege from PUBLIC, anon and authenticated; it
-- re-grants service_role explicitly (the migrations/037 both-readings rule).
--
-- APP CODE IS UNAFFECTED: every reader and writer of the three tables uses the
-- service-role client (app/services/product_data_service.py get_cached_* /
-- save_*, app/api/text_routes.py the cache flush DELETE,
-- app/services/reengagement_service.py, scripts/shadow_experiments.py).
--
-- APPLY ORDER: after the owner's live pg_policies read (APPLY_047_1_PRECHECK
-- .sql). If that read lists a policy on these tables beyond the eight names
-- below, the REVOKE still removes the table privilege from anon and
-- authenticated (a policy cannot grant a privilege), and the extra policy is
-- dropped by name in a follow-up migration. No ordering against 045.
--
-- Owner postcheck (APPLY_047_3_POSTCHECK.sql): no policy left on the three
-- tables; has_table_privilege anon / authenticated INSERT, UPDATE, DELETE and
-- SELECT false; service_role SELECT, INSERT, UPDATE, DELETE true.
--
-- Rollback: migrations/rollback/047_012_revoke.sql

BEGIN;

DROP POLICY IF EXISTS specs_select ON public.product_specs;
DROP POLICY IF EXISTS specs_insert ON public.product_specs;
DROP POLICY IF EXISTS specs_update ON public.product_specs;
DROP POLICY IF EXISTS prices_select ON public.product_prices;
DROP POLICY IF EXISTS prices_insert ON public.product_prices;
DROP POLICY IF EXISTS reviews_select ON public.product_reviews;
DROP POLICY IF EXISTS reviews_insert ON public.product_reviews;
DROP POLICY IF EXISTS reviews_update ON public.product_reviews;

ALTER TABLE public.product_specs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_reviews ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.product_specs FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.product_prices FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.product_reviews FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_specs TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_prices TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_reviews TO service_role;

COMMIT;
