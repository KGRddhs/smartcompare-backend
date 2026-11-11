-- Migration 048 (S81-22 COMPARE-RUNS + capped judge): public.compare_runs,
-- public.compare_judgements, public.compare_runs_prune(integer) and the
-- delete_user_cascade kb_feedback hook.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION. The file is written, not applied;
-- the request-path writer (app/services/compare_runs.py) stays dark behind
-- ENABLE_COMPARE_RUN_LEDGER and the nightly judge (scripts/cron_compare_judge.py)
-- behind ENABLE_BATCH_JUDGE.
-- APPLY ORDER: 043 and 045 applied before 048 (the guard reads the 043 cascade
-- marker, public.kb_feedback and kb_feedback.compare_request_id); roll back 048
-- before 045. Rollback file: migrations/rollback/048_compare_runs.sql.
--
-- compare_runs keeps one de-identified row per DELIVERED compare: no user id, no
-- raw query, no URL, no raw fingerprint, no personalisation. comparison_id
-- references public.comparisons (id) ON DELETE SET NULL, so the runs of a deleted
-- account stay only as unlinked rows. device_key and query_hmac are HMAC-SHA256
-- under DEVICE_KEY_PEPPER, computed at request time (the judge never reads the
-- pepper). Both tables are service role only: RLS enabled, no policy, the 045
-- REVOKE / GRANT form. Retention: COMPARE_RUN_RETENTION_DAYS = 365 ("up to 12
-- months"), enforced by compare_runs_prune(365) from the nightly job, which also
-- runs kb_prune_feedback(365) (the 045 header assigns that prune to this unit).
--
-- The guard raises only when a table 048 needs is missing, when 043 is not
-- applied, or when compare_runs / compare_judgements already exists with a column
-- set different from the one created here (information_schema.columns, names
-- only); a re-apply over the same columns proceeds (CREATE ... IF NOT EXISTS).
--
-- delete_user_cascade = the 043 body plus ONE statement before the first detach
-- UPDATE: every kb_feedback row whose compare_request_id belongs to a run linked
-- to one of the account's comparisons is deleted (including a row another device
-- wrote against that request id). Any failure inside the hook aborts the whole
-- account deletion (the SECURITY DEFINER function is one statement list in one
-- transaction). The REVOKE is restated; the one GRANT stays 037's.
-- There is no comment inside a dollar body.

BEGIN;

DO $guard$
DECLARE
  missing text;
  v_cols text[];
BEGIN
  SELECT string_agg(t.tbl, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'public.users', 'public.user_events', 'public.comparison_feedback',
      'public.comparisons', 'public.search_logs', 'public.user_usage',
      'public.referral_invites', 'public.referral_redemptions',
      'public.deep_review_credits', 'public.re_engagement_events',
      'public.pain_workflow_events', 'public.user_preference_history',
      'public.admin_audit_log', 'public.kb_feedback'
    ]) AS t (tbl)
   WHERE to_regclass(t.tbl) IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '048 guard: missing table(s): %', missing;
  END IF;
  IF NOT EXISTS (
    SELECT 1
      FROM information_schema.columns AS col
     WHERE col.table_schema = 'public'
       AND col.table_name = 'kb_feedback'
       AND col.column_name = 'compare_request_id'
  ) THEN
    RAISE EXCEPTION '048 guard: kb_feedback.compare_request_id missing';
  END IF;
  IF position('user_preference_history' IN pg_get_functiondef(
    'public.delete_user_cascade(uuid)'::regprocedure
  )) = 0 THEN
    RAISE EXCEPTION '048 guard: 043 not applied';
  END IF;
  SELECT array_agg(col.column_name::text)
    INTO v_cols
    FROM information_schema.columns AS col
   WHERE col.table_schema = 'public'
     AND col.table_name = 'compare_runs';
  IF v_cols IS NOT NULL AND NOT (
    v_cols @> ARRAY[
      'cache_hits', 'category', 'compare_request_id', 'comparison_id',
      'consent_version', 'created_at', 'data_coverage', 'device_key',
      'evidence', 'field_status', 'id', 'identity_confidence', 'input_type',
      'judged_at', 'kb_product_ids', 'llm_calls', 'partial_stage',
      'product_categories', 'query_hmac', 'recompare', 'refusal_reason',
      'result_status', 'sources_used', 'stage_timings', 'winner_supported'
    ]::text[]
    AND v_cols <@ ARRAY[
      'cache_hits', 'category', 'compare_request_id', 'comparison_id',
      'consent_version', 'created_at', 'data_coverage', 'device_key',
      'evidence', 'field_status', 'id', 'identity_confidence', 'input_type',
      'judged_at', 'kb_product_ids', 'llm_calls', 'partial_stage',
      'product_categories', 'query_hmac', 'recompare', 'refusal_reason',
      'result_status', 'sources_used', 'stage_timings', 'winner_supported'
    ]::text[]
  ) THEN
    RAISE EXCEPTION '048 guard: compare_runs exists with a different column set';
  END IF;
  SELECT array_agg(col.column_name::text)
    INTO v_cols
    FROM information_schema.columns AS col
   WHERE col.table_schema = 'public'
     AND col.table_name = 'compare_judgements';
  IF v_cols IS NOT NULL AND NOT (
    v_cols @> ARRAY[
      'batch_id', 'cost_usd', 'created_at', 'flags', 'id', 'judge', 'model',
      'note', 'run_id', 'verdicts'
    ]::text[]
    AND v_cols <@ ARRAY[
      'batch_id', 'cost_usd', 'created_at', 'flags', 'id', 'judge', 'model',
      'note', 'run_id', 'verdicts'
    ]::text[]
  ) THEN
    RAISE EXCEPTION '048 guard: compare_judgements exists with a different column set';
  END IF;
END
$guard$;

CREATE TABLE IF NOT EXISTS public.compare_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    comparison_id uuid NULL REFERENCES public.comparisons (id) ON DELETE SET NULL,
    consent_version smallint NULL CHECK (consent_version BETWEEN 0 AND 999),
    compare_request_id uuid NULL,
    device_key text NULL CHECK (device_key ~ '^[a-f0-9]{64}$'),
    input_type text NOT NULL CHECK (input_type IN ('text', 'text_stream', 'camera', 'url')),
    category text NULL CHECK (category ~ '^[a-z_]{1,32}$'),
    product_categories jsonb NULL CHECK (
        product_categories IS NULL OR jsonb_typeof(product_categories) = 'array'
    ),
    refusal_reason text NULL CHECK (refusal_reason ~ '^[A-Za-z0-9_:-]{1,64}$'),
    query_hmac text NULL CHECK (query_hmac ~ '^[a-f0-9]{64}$'),
    kb_product_ids jsonb NULL CHECK (
        kb_product_ids IS NULL OR jsonb_typeof(kb_product_ids) = 'array'
    ),
    sources_used jsonb NULL,
    cache_hits jsonb NULL,
    llm_calls jsonb NULL,
    stage_timings jsonb NULL,
    result_status text NULL CHECK (result_status IN (
        'supported_result', 'partial_no_winner', 'needs_identification',
        'unsupported_category', 'failed'
    )),
    identity_confidence text NULL CHECK (
        identity_confidence IN ('high', 'medium', 'low', 'unresolved')
    ),
    data_coverage smallint NULL CHECK (data_coverage BETWEEN 0 AND 4),
    winner_supported boolean NULL,
    field_status jsonb NULL,
    partial_stage text NULL CHECK (
        partial_stage IN ('gather', 'post_gather', 'scoring', 'verdict')
    ),
    evidence jsonb NULL CHECK (evidence IS NULL OR pg_column_size(evidence) <= 131072),
    recompare boolean NOT NULL DEFAULT false,
    judged_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS public.compare_judgements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES public.compare_runs (id) ON DELETE CASCADE,
    judge text NOT NULL CHECK (judge IN ('programmatic', 'haiku', 'sonnet')),
    model text NULL CHECK (model ~ '^[a-z0-9.-]{1,64}$'),
    batch_id text NULL CHECK (char_length(batch_id) <= 128),
    verdicts jsonb NOT NULL CHECK (jsonb_typeof(verdicts) = 'object'),
    flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(flags) = 'array'),
    note text NULL CHECK (char_length(note) <= 300),
    cost_usd numeric NULL CHECK (cost_usd >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT compare_judgements_run_judge UNIQUE (run_id, judge)
);

CREATE INDEX IF NOT EXISTS idx_compare_runs_created
ON public.compare_runs (created_at);
CREATE INDEX IF NOT EXISTS idx_compare_runs_recompare
ON public.compare_runs (query_hmac, device_key, created_at)
WHERE query_hmac IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compare_runs_comparison
ON public.compare_runs (comparison_id)
WHERE comparison_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compare_runs_request
ON public.compare_runs (compare_request_id)
WHERE compare_request_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compare_runs_unjudged
ON public.compare_runs (created_at)
WHERE judged_at IS NULL;

CREATE OR REPLACE FUNCTION public.compare_runs_prune(p_days integer)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO 'public'
AS $$
DECLARE
  v_deleted integer;
BEGIN
  IF p_days IS NULL OR p_days < 1 OR p_days > 3650 THEN
    RAISE EXCEPTION 'compare_runs_prune: bounds out of range';
  END IF;
  DELETE FROM public.compare_runs AS r
  WHERE r.created_at < now() - make_interval(days => p_days);
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END
$$;

ALTER TABLE public.compare_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compare_judgements ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.compare_runs FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.compare_runs TO service_role;
REVOKE ALL ON TABLE public.compare_judgements FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.compare_judgements TO service_role;
REVOKE ALL ON FUNCTION public.compare_runs_prune(integer)
FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.compare_runs_prune(integer) TO service_role;

CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
BEGIN
  DELETE FROM public.user_events WHERE user_id = target_user_id;
  DELETE FROM public.comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM public.kb_feedback
   WHERE compare_request_id IN (
     SELECT r.compare_request_id
       FROM public.compare_runs AS r
       JOIN public.comparisons AS c ON c.id = r.comparison_id
      WHERE c.user_id = target_user_id
        AND r.compare_request_id IS NOT NULL
   );
  UPDATE public.user_events
     SET comparison_id = NULL
   WHERE comparison_id IN (
     SELECT c.id FROM public.comparisons AS c WHERE c.user_id = target_user_id
   );
  UPDATE public.comparison_feedback
     SET comparison_id = NULL
   WHERE comparison_id IN (
     SELECT c.id FROM public.comparisons AS c WHERE c.user_id = target_user_id
   );
  DELETE FROM public.comparisons WHERE user_id = target_user_id;
  DELETE FROM public.search_logs WHERE user_id = target_user_id;
  DELETE FROM public.user_usage WHERE user_id = target_user_id;
  DELETE FROM public.referral_invites
   WHERE referrer_user_id = target_user_id
      OR redeemed_by_user_id = target_user_id;
  DELETE FROM public.referral_redemptions
   WHERE referrer_user_id = target_user_id
      OR invitee_user_id = target_user_id;

  DELETE FROM public.deep_review_credits WHERE user_id = target_user_id;
  DELETE FROM public.re_engagement_events WHERE user_id = target_user_id;
  DELETE FROM public.pain_workflow_events WHERE user_id = target_user_id;
  DELETE FROM public.user_preference_history WHERE user_id = target_user_id;

  UPDATE public.admin_audit_log
     SET ip_address = NULL
   WHERE user_id = target_user_id;

  UPDATE public.users
     SET email = NULL,
         display_name = NULL,
         auth_provider = NULL,
         subscription_tier = 'free',
         subscription_expires_at = NULL,
         updated_at = now(),
         preferences = NULL,
         preferences_completed = false,
         behavior_profile = NULL,
         lifetime_comparisons_used = 0,
         demographics_profile = NULL,
         demographics_dismissed_count = 0,
         demographics_dismissed_at = NULL,
         referral_code = NULL,
         referral_bonus_comparisons_this_month = 0,
         referral_bonus_reset_at = NULL,
         expo_push_token = NULL,
         notifications_enabled = false,
         last_comparison_at = NULL,
         attribution_source = NULL,
         device_fingerprint_hash = NULL,
         lifetime_invites_consumed = 0,
         terms_accepted_at = NULL,
         terms_version = NULL,
         age_attested_at = NULL
   WHERE id = target_user_id;
END;
$function$;

REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid)
FROM PUBLIC, anon, authenticated;

DO $assert$
BEGIN
  PERFORM public.delete_user_cascade('00000000-0000-0000-0000-000000000000'::uuid);
  IF NOT EXISTS (
    SELECT 1
      FROM pg_proc AS p
     WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure
       AND p.prosecdef
       AND p.proconfig = ARRAY['search_path=public']
  ) THEN
    RAISE EXCEPTION '048 assert: SECURITY DEFINER or search_path=public lost';
  END IF;
  IF NOT has_function_privilege(
    'service_role', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION '048 assert: service_role cannot EXECUTE (apply 037 first)';
  END IF;
  IF has_function_privilege(
    'anon', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) OR has_function_privilege(
    'authenticated', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION '048 assert: anon or authenticated can EXECUTE';
  END IF;
  PERFORM public.compare_runs_prune(3650);
END
$assert$;

COMMIT;
