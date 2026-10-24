-- APPLY_045_3_POSTCHECK.sql -- S81-14 migration 045 (the kb_* knowledge-base core), step 3 of 3.
--
-- Run AFTER step 2, in ONE paste. It has two parts.
--
-- Part 1 runs inside BEGIN ... ROLLBACK and leaves NO row behind: it writes a synthetic
-- product (host aba-check.example) and checks the behaviour 045 promises (ruling R-S14-1 A/B/A
-- and the rest). If any check fails the paste stops with an error that starts
-- "APPLY_045 POSTCHECK FAILED"; send that error back and apply nothing else. The checks:
--   A/B/A offers: price A first seen 400 days ago, price B seen 200 days ago, price A seen
--     again today through the observation upsert (sets last_seen, in_stock, evidence_rung,
--     canonical_url only); the latest offer (view and card) is A, kb_prune_offers(30, 1)
--     deletes exactly one row (B) and A survives;
--   the sale tie-break (ruling F1-4): a list row (50) and a sale row (30) of one observation
--     (same last_seen and captured_at) -> the view and the card serve the sale (30);
--   the BEFORE UPDATE trigger moves kb_products.updated_at;
--   kb_merchants STORES a denied host (deny, blocked), while kb_offers refuses a denied URL;
--   kb_merchants refuses an all-digit host such as 10.0.0.1 (ruling F1-6);
--   kb_variants refuses a GTIN whose check digit is wrong;
--   the card serves cited specs only, in p_lang with an English fallback;
--   the card rating is the review-count-weighted mean (4.5 x 10 and 3.5 x 30 -> 3.75);
--   device-less votes are stored, a second vote of one device key is refused;
--   kb_prune_feedback(365) deletes nothing fresh.
--
-- Part 2 is read-only: the grid below. Expected (one row), every column as shown, in order:
--   view_present                           = true
--   sr_view_select                         = true
--   sr_view_insert                         = false
--   card_missing_is_null                   = true
--   gtin_valid_true                        = true
--   gtin_altered_false                     = false
--   tables_present                         = 10
--   rls_on_all_ten                         = true
--   policy_count                           = 0
--   sr_sidu_all_tables                     = true   (service_role SELECT, INSERT, UPDATE, DELETE)
--   sr_truncate_any                        = false
--   anon_or_authenticated_any              = false  (no table privilege of any kind)
--   anon_or_authenticated_view_select      = false
--   functions_present                      = 5
--   security_definer_any                   = false
--   sr_execute_all                         = true
--   anon_authenticated_public_execute_any  = false
--   updated_at_triggers                    = 3
--   kb_row_count                           = 0      (part 1 rolled back; nothing writes kb_* yet)
-- FIRST APPLY ONLY: part 1 calls the global kb_prune_offers(30, 1) / kb_prune_feedback(365) and
-- part 2 expects kb_row_count 0, so a re-run after a kb_* writer has written reports a false
-- FAILED or a non-zero count (harmless: part 1 is rolled back).
-- Measured on a throwaway local PostgreSQL 18.1 cluster (S81-14 GREEN, 2026-10-24; the fix round
-- re-ran it on the fix bytes): this exact grid, and part 1 FAILS ("kb_offers_latest serves
-- 25.000, expected 30") on a 045 whose view ranks captured_at before last_seen (the BL1 defect).
-- Any other value: send the grid back before anything else is applied.

BEGIN;

DO $$
DECLARE
  v_pid text := 'fragrances|' || 'aba-check|aba-check|EDP';
  v_vid text := v_pid || '|100';
  v_host text := 'aba-check.example';
  v_url text := 'https://' || v_host || '/p/1';
  v_n integer;
  v_amount numeric;
  v_card jsonb;
  v_got text;
  v_upd timestamptz;
  v_req uuid := gen_random_uuid();
  v_dk text := repeat('ab', 32);
BEGIN
  INSERT INTO public.kb_merchants (host, status) VALUES (v_host, 'live');
  INSERT INTO public.kb_products (id, brand, name, concentration, identity_confidence, updated_at)
  VALUES (v_pid, 'ABA', 'ABA Check', 'EDP', 'high', '2000-01-01T00:00:00Z');
  INSERT INTO public.kb_variants (id, product_id, concentration, size_ml)
  VALUES (v_vid, v_pid, 'EDP', 100);

  INSERT INTO public.kb_offers (
    variant_id, merchant_id, market, amount, observed_currency, evidence_rung,
    first_seen, last_seen, captured_at, canonical_url
  ) VALUES (
    v_vid, v_host, 'BH', 30, 'BHD', 'own_token',
    now() - interval '400 days', now() - interval '400 days', now() - interval '400 days', v_url
  );
  INSERT INTO public.kb_offers (
    variant_id, merchant_id, market, amount, observed_currency, evidence_rung,
    first_seen, last_seen, captured_at, canonical_url
  ) VALUES (
    v_vid, v_host, 'BH', 25, 'BHD', 'own_token',
    now() - interval '200 days', now() - interval '200 days', now() - interval '200 days', v_url
  );
  INSERT INTO public.kb_offers (
    variant_id, merchant_id, market, amount, observed_currency, evidence_rung,
    in_stock, first_seen, last_seen, captured_at, canonical_url
  ) VALUES (
    v_vid, v_host, 'BH', 30, 'BHD', 'page_evidence', true, now(), now(), now(), v_url
  )
  ON CONFLICT ON CONSTRAINT kb_offers_observation DO UPDATE SET
    last_seen = excluded.last_seen,
    in_stock = excluded.in_stock,
    evidence_rung = excluded.evidence_rung,
    canonical_url = excluded.canonical_url;

  SELECT count(*) INTO v_n FROM public.kb_offers WHERE variant_id = v_vid;
  IF v_n <> 2 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: the re-observation made % rows, expected 2', v_n;
  END IF;
  SELECT l.amount INTO v_amount FROM public.kb_offers_latest AS l WHERE l.variant_id = v_vid;
  IF v_amount IS DISTINCT FROM 30 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: kb_offers_latest serves %, expected 30', v_amount;
  END IF;
  v_card := public.kb_product_card(v_pid);
  IF jsonb_array_length(v_card -> 'offers') <> 1
     OR (v_card -> 'offers' -> 0 ->> 'amount')::numeric <> 30 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: card offers %', v_card -> 'offers';
  END IF;
  v_n := public.kb_prune_offers(30, 1);
  IF v_n <> 1 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: kb_prune_offers(30, 1) deleted %, expected 1', v_n;
  END IF;
  SELECT count(*), max(o.amount) INTO v_n, v_amount FROM public.kb_offers AS o WHERE o.variant_id = v_vid;
  IF v_n <> 1 OR v_amount <> 30 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: after the prune % rows, amount %', v_n, v_amount;
  END IF;

  INSERT INTO public.kb_variants (id, product_id, concentration, size_ml)
  VALUES (v_pid || '|30', v_pid, 'EDP', 30);
  -- explicit ids: the list row carries the LARGER id, so a 045 that falls through to
  -- id DESC (no sale key) serves the list row and this check fails deterministically
  INSERT INTO public.kb_offers (
    id, variant_id, merchant_id, market, amount, observed_currency, evidence_rung, list_vs_sale,
    first_seen, last_seen, captured_at, canonical_url
  ) VALUES
    ('f0000000-0000-4000-8000-f0000f00000f', v_pid || '|30', v_host, 'BH', 50, 'BHD', 'own_token', 'list',
     now() - interval '1 day', now() - interval '1 day', now() - interval '1 day', v_url || '/30'),
    ('a0000000-0000-4000-8000-a0000a00000a', v_pid || '|30', v_host, 'BH', 30, 'BHD', 'own_token', 'sale',
     now() - interval '1 day', now() - interval '1 day', now() - interval '1 day', v_url || '/30');
  SELECT l.amount INTO v_amount FROM public.kb_offers_latest AS l WHERE l.variant_id = v_pid || '|30';
  IF v_amount IS DISTINCT FROM 30 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: the tie-break serves %, expected the sale 30', v_amount;
  END IF;
  SELECT (e ->> 'amount')::numeric INTO v_amount
  FROM jsonb_array_elements(public.kb_product_card(v_pid) -> 'offers') AS e
  WHERE e ->> 'variant_id' = v_pid || '|30';
  IF v_amount IS DISTINCT FROM 30 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: the card tie-break serves %, expected the sale 30', v_amount;
  END IF;
  BEGIN
    INSERT INTO public.kb_merchants (host, status) VALUES ('10.0.0.1', 'live');
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: kb_merchants accepted an all-digit host';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  UPDATE public.kb_products SET line = 'Check' WHERE id = v_pid;
  SELECT p.updated_at INTO v_upd FROM public.kb_products AS p WHERE p.id = v_pid;
  IF v_upd < now() THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: the updated_at trigger did not fire (%)', v_upd;
  END IF;

  INSERT INTO public.kb_merchants (host, deny, status, blocked_reason)
  VALUES ('fragrantica.com', true, 'blocked', 'deny_list');
  BEGIN
    INSERT INTO public.kb_offers (
      variant_id, merchant_id, market, amount, observed_currency, evidence_rung, canonical_url
    ) VALUES (v_vid, 'fragrantica.com', 'BH', 9, 'BHD', 'own_token', 'https://fragrantica.com/p/1');
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: kb_offers accepted a denied URL';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
  BEGIN
    INSERT INTO public.kb_variants (id, product_id, gtin)
    VALUES (v_pid || '|50', v_pid, '6291' || '0412' || '3456' || '0');
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: kb_variants accepted a bad GTIN check digit';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  INSERT INTO public.kb_specs (product_id, field, lang, value, source_url, extractor, cited) VALUES
    (v_pid, 'top_notes', 'en', 'Bergamot', v_url, 'jsonld', true),
    (v_pid, 'top_notes', 'ar', 'ar-value', v_url, 'jsonld', true),
    (v_pid, 'base_notes', 'en', 'Amber', v_url, 'jsonld', true),
    (v_pid, 'heart_notes', 'en', 'Rose', NULL, 'llm', false);
  SELECT string_agg((e ->> 'field') || ':' || (e ->> 'lang'), ',' ORDER BY e ->> 'field') INTO v_got
  FROM jsonb_array_elements(public.kb_product_card(v_pid, 'ar') -> 'specs') AS e;
  IF v_got IS DISTINCT FROM 'base_notes:en,top_notes:ar' THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: card specs (ar) %', v_got;
  END IF;
  SELECT string_agg((e ->> 'field') || ':' || (e ->> 'lang'), ',' ORDER BY e ->> 'field') INTO v_got
  FROM jsonb_array_elements(public.kb_product_card(v_pid) -> 'specs') AS e;
  IF v_got IS DISTINCT FROM 'base_notes:en,top_notes:en' THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: card specs (en) %', v_got;
  END IF;

  INSERT INTO public.kb_reviews (product_id, source, aggregate_rating, review_count, source_url) VALUES
    (v_pid, 'retailer_jsonld', 4.5, 10, v_url),
    (v_pid, 'retailer_widget', 3.5, 30, 'https://' || v_host || '/p/2');
  v_card := public.kb_product_card(v_pid);
  IF (v_card -> 'rating' ->> 'rating')::numeric <> 3.75
     OR (v_card -> 'rating' ->> 'sources')::int <> 2
     OR (v_card -> 'rating' ->> 'review_count')::int <> 40 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: card rating %', v_card -> 'rating';
  END IF;

  INSERT INTO public.kb_feedback (compare_request_id, product_id, field, verdict) VALUES
    (v_req, v_pid, 'price', 'wrong'),
    (v_req, v_pid, 'price', 'wrong');
  INSERT INTO public.kb_feedback (compare_request_id, product_id, field, verdict, device_key)
  VALUES (v_req, v_pid, 'price', 'correct', v_dk);
  BEGIN
    INSERT INTO public.kb_feedback (compare_request_id, product_id, field, verdict, device_key)
    VALUES (v_req, v_pid, 'price', 'wrong', v_dk);
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: one device voted twice';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
  v_n := public.kb_prune_feedback(365);
  IF v_n <> 0 THEN
    RAISE EXCEPTION 'APPLY_045 POSTCHECK FAILED: kb_prune_feedback(365) deleted % fresh rows', v_n;
  END IF;

  RAISE NOTICE 'APPLY_045 POSTCHECK part 1: every behaviour check passed (rolled back next)';
END
$$;

ROLLBACK;

WITH
kb_tables (tbl) AS (
    VALUES
    ('kb_merchants'), ('kb_products'), ('kb_variants'), ('kb_offers'), ('kb_images'),
    ('kb_specs'), ('kb_reviews'), ('kb_gaps'), ('kb_feedback'), ('kb_coverage_daily')
),

table_privs (priv) AS (
    VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE')
),

every_priv (priv) AS (
    VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')
),

client_roles (role_name) AS (
    VALUES ('anon'), ('authenticated')
),

kb_functions (sig) AS (
    VALUES
    ('public.kb_gtin_check_digit_ok(text)'),
    ('public.kb_set_updated_at()'),
    ('public.kb_prune_offers(integer, integer)'),
    ('public.kb_prune_feedback(integer)'),
    ('public.kb_product_card(text, text)')
)

SELECT
    to_regclass('public.kb_offers_latest') IS NOT NULL AS view_present,
    has_table_privilege('service_role', 'public.kb_offers_latest', 'SELECT') AS sr_view_select,
    has_table_privilege('service_role', 'public.kb_offers_latest', 'INSERT') AS sr_view_insert,
    public.kb_product_card('fragrances|' || 'x|y|-') IS NULL AS card_missing_is_null,
    public.kb_gtin_check_digit_ok('6291' || '0412' || '3456' || '9') AS gtin_valid_true,
    public.kb_gtin_check_digit_ok('6291' || '0412' || '3456' || '0') AS gtin_altered_false,
    (SELECT count(*) FROM kb_tables WHERE to_regclass('public.' || kb_tables.tbl) IS NOT NULL)
        AS tables_present,
    (
        SELECT bool_and(c.relrowsecurity)
        FROM pg_class AS c
        INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname IN (SELECT kb_tables.tbl FROM kb_tables)
    ) AS rls_on_all_ten,
    (SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename LIKE 'kb\_%')
        AS policy_count,
    (
        SELECT bool_and(has_table_privilege('service_role', 'public.' || t.tbl, p.priv))
        FROM kb_tables AS t CROSS JOIN table_privs AS p
    ) AS sr_sidu_all_tables,
    (
        SELECT bool_or(has_table_privilege('service_role', 'public.' || t.tbl, 'TRUNCATE'))
        FROM kb_tables AS t
    ) AS sr_truncate_any,
    (
        SELECT bool_or(has_table_privilege(r.role_name, 'public.' || t.tbl, e.priv))
        FROM kb_tables AS t CROSS JOIN every_priv AS e CROSS JOIN client_roles AS r
    ) AS anon_or_authenticated_any,
    (
        SELECT bool_or(has_table_privilege(r.role_name, 'public.kb_offers_latest', 'SELECT'))
        FROM client_roles AS r
    ) AS anon_or_authenticated_view_select,
    (SELECT count(*) FROM kb_functions WHERE to_regprocedure(kb_functions.sig) IS NOT NULL)
        AS functions_present,
    (
        SELECT bool_or(p.prosecdef)
        FROM pg_proc AS p
        WHERE p.oid IN (SELECT to_regprocedure(kb_functions.sig) FROM kb_functions)
    ) AS security_definer_any,
    (SELECT bool_and(has_function_privilege('service_role', kb_functions.sig, 'EXECUTE')) FROM kb_functions)
        AS sr_execute_all,
    (
        SELECT bool_or(has_function_privilege(r.role_name, f.sig, 'EXECUTE'))
        FROM kb_functions AS f
        CROSS JOIN (VALUES ('anon'), ('authenticated'), ('public')) AS r (role_name)
    ) AS anon_authenticated_public_execute_any,
    (
        SELECT count(*)
        FROM pg_trigger AS tg
        WHERE
            NOT tg.tgisinternal
            AND tg.tgname IN (
                'kb_merchants_set_updated_at', 'kb_products_set_updated_at', 'kb_variants_set_updated_at'
            )
    ) AS updated_at_triggers,
    (
        (SELECT count(*) FROM public.kb_merchants)
        + (SELECT count(*) FROM public.kb_products)
        + (SELECT count(*) FROM public.kb_variants)
        + (SELECT count(*) FROM public.kb_offers)
        + (SELECT count(*) FROM public.kb_images)
        + (SELECT count(*) FROM public.kb_specs)
        + (SELECT count(*) FROM public.kb_reviews)
        + (SELECT count(*) FROM public.kb_gaps)
        + (SELECT count(*) FROM public.kb_feedback)
        + (SELECT count(*) FROM public.kb_coverage_daily)
    ) AS kb_row_count;
