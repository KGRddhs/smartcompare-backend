-- Rollback for migration 046 (S81-SF1 SURFACES-BE): comparison_feedback v2 columns.
--
-- Unset ENABLE_FEEDBACK_V2 on web FIRST (the writer would otherwise name dropped
-- columns). DESTRUCTIVE: every v2 answer (identity_correct, wrong_side, preference,
-- correction, source, compare_request_id) is lost; the partial index and the five
-- CHECK constraints go with their columns.
--
-- useful: NOT NULL is restored ONLY when 046 itself dropped it, which 046 recorded as
-- the column comment 'sf1_dropped_not_null' (RULINGS_S81_SF1 R-SF1-36). A database
-- whose useful was already nullable before 046 has no such comment and keeps the
-- column nullable. While a row with useful NULL exists the restore is refused (RAISE)
-- and the whole rollback rolls back: delete or backfill those rows first (owner call).

BEGIN;

ALTER TABLE public.comparison_feedback
DROP COLUMN IF EXISTS identity_correct,
DROP COLUMN IF EXISTS wrong_side,
DROP COLUMN IF EXISTS preference,
DROP COLUMN IF EXISTS correction,
DROP COLUMN IF EXISTS source,
DROP COLUMN IF EXISTS compare_request_id;

DO $$
BEGIN
    IF col_description('public.comparison_feedback'::regclass, (
        SELECT a.attnum
        FROM pg_attribute AS a
        WHERE
            a.attrelid = 'public.comparison_feedback'::regclass
            AND a.attname = 'useful'
    )) = 'sf1_dropped_not_null' THEN
        IF exists(SELECT 1 FROM public.comparison_feedback WHERE useful IS NULL) THEN
            RAISE EXCEPTION 'rollback 046: rows with useful NULL exist; NOT NULL cannot be restored';
        END IF;
        ALTER TABLE public.comparison_feedback ALTER COLUMN useful SET NOT NULL;
        COMMENT ON COLUMN public.comparison_feedback.useful IS NULL;
    END IF;
END
$$;

COMMIT;

NOTIFY pgrst, 'reload schema';
