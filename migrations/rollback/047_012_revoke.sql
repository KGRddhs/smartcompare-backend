-- Rollback for migration 047_012_revoke.sql (S81-14 KB-SCHEMA, S81)
--
-- EMERGENCY ONLY: this RE-OPENS the anon write path on the L2 cache (the
-- poisoning path 047 closed). It recreates the eight 012 policies verbatim and
-- restores the stock table grants to anon and authenticated; compare the
-- result with the relacl recorded by APPLY_047_1_PRECHECK.sql before running.

BEGIN;

CREATE POLICY specs_select ON public.product_specs FOR SELECT USING (true);
CREATE POLICY specs_insert ON public.product_specs FOR INSERT WITH CHECK (true);
CREATE POLICY specs_update ON public.product_specs FOR UPDATE USING (true);
CREATE POLICY prices_select ON public.product_prices FOR SELECT USING (true);
CREATE POLICY prices_insert ON public.product_prices FOR INSERT WITH CHECK (true);
CREATE POLICY reviews_select ON public.product_reviews FOR SELECT USING (true);
CREATE POLICY reviews_insert ON public.product_reviews FOR INSERT WITH CHECK (true);
CREATE POLICY reviews_update ON public.product_reviews FOR UPDATE USING (true);

GRANT ALL ON TABLE public.product_specs, public.product_prices, public.product_reviews TO anon, authenticated;

COMMIT;
