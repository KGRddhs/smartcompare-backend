-- Migration 046: comparison_feedback v2 answer columns (S81-SF1 SURFACES-BE)
--
-- WRITTEN NOT APPLIED. MERGING THIS FILE CHANGES NOTHING IN PRODUCTION: the owner
-- applies it (APPLY_046_1_PRECHECK, APPLY_046_2_ONE_PASTE, APPLY_046_3_POSTCHECK in
-- the session-81 state folder) and only then turns ENABLE_FEEDBACK_V2 on.
--
-- Order: after 027 (the three correctness CHECKs; the guard refuses without them),
-- before 049, and the flag after BOTH (RULINGS_S81_SF1 R-SF1-29).
--
-- Adds to public.comparison_feedback (all nullable except source):
--   identity_correct   text, CHECK in ('correct', 'wrong', 'unsure')
--   wrong_side         text, CHECK in ('first', 'second', 'both')  (body product order)
--   preference         text, CHECK in ('first', 'second', 'neither', 'unsure')
--   correction         text, CHECK char_length <= 80 (the optional correct product
--                      name: user text; never read by a prompt, an exemplar builder
--                      or a store report)
--   source             text NOT NULL DEFAULT 'result', CHECK in ('result', 'contact')
--                      (learning readers exclude contact; existing rows read result)
--   compare_request_id uuid (the per-compare request id) + the partial index
--                      idx_comparison_feedback_request
-- price_correct is NOT re-added (027 has it).
--
-- useful: DROP NOT NULL only inside the guarded DO block that reads the live
-- information_schema.columns.is_nullable (the PRECHECK reports it: record it). When
-- this file drops it, the column comment 'sf1_dropped_not_null' is written in the
-- same block; the rollback restores NOT NULL only when that comment is present.
--
-- Locks: every ALTER holds ACCESS EXCLUSIVE on the table until COMMIT and the
-- partial index build scans it; lock_timeout 5s makes a busy table fail fast
-- instead of queueing writers. Apply in a quiet window.
--
-- No function, no RLS policy, no GRANT / REVOKE: the 010 policies cover new columns.
-- Rollback: migrations/rollback/046_comparison_feedback_v2.sql (unset the flag first).

BEGIN;

SET LOCAL lock_timeout = '5s';

DO $$
BEGIN
    IF to_regclass('public.comparison_feedback') IS NULL THEN
        RAISE EXCEPTION '046 guard: public.comparison_feedback is missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns AS c
        WHERE
            c.table_schema = 'public'
            AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'useful'
            AND c.data_type = 'boolean'
    ) THEN
        RAISE EXCEPTION '046 guard: comparison_feedback.useful (boolean) is missing';
    END IF;
    IF (
        SELECT count(*)
        FROM pg_constraint AS k
        WHERE
            k.conrelid = 'public.comparison_feedback'::regclass
            AND k.contype = 'c'
            AND k.conname IN (
                'comparison_feedback_winner_correct_check',
                'comparison_feedback_price_correct_check',
                'comparison_feedback_specs_correct_check'
            )
    ) <> 3 THEN
        RAISE EXCEPTION '046 guard: the three 027 CHECK constraints are missing (apply 027 first)';
    END IF;
END
$$;

ALTER TABLE public.comparison_feedback
ADD COLUMN IF NOT EXISTS identity_correct text NULL;

ALTER TABLE public.comparison_feedback
ADD COLUMN IF NOT EXISTS wrong_side text NULL;

ALTER TABLE public.comparison_feedback
ADD COLUMN IF NOT EXISTS preference text NULL;

ALTER TABLE public.comparison_feedback
ADD COLUMN IF NOT EXISTS correction text NULL;

ALTER TABLE public.comparison_feedback
ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'result';

ALTER TABLE public.comparison_feedback
ADD COLUMN IF NOT EXISTS compare_request_id uuid NULL;

ALTER TABLE public.comparison_feedback
DROP CONSTRAINT IF EXISTS comparison_feedback_identity_correct_check;
ALTER TABLE public.comparison_feedback
ADD CONSTRAINT comparison_feedback_identity_correct_check
CHECK (identity_correct IN ('correct', 'wrong', 'unsure'));

ALTER TABLE public.comparison_feedback
DROP CONSTRAINT IF EXISTS comparison_feedback_wrong_side_check;
ALTER TABLE public.comparison_feedback
ADD CONSTRAINT comparison_feedback_wrong_side_check
CHECK (wrong_side IN ('first', 'second', 'both'));

ALTER TABLE public.comparison_feedback
DROP CONSTRAINT IF EXISTS comparison_feedback_preference_check;
ALTER TABLE public.comparison_feedback
ADD CONSTRAINT comparison_feedback_preference_check
CHECK (preference IN ('first', 'second', 'neither', 'unsure'));

ALTER TABLE public.comparison_feedback
DROP CONSTRAINT IF EXISTS comparison_feedback_correction_check;
ALTER TABLE public.comparison_feedback
ADD CONSTRAINT comparison_feedback_correction_check
CHECK (char_length(correction) <= 80);

ALTER TABLE public.comparison_feedback
DROP CONSTRAINT IF EXISTS comparison_feedback_source_check;
ALTER TABLE public.comparison_feedback
ADD CONSTRAINT comparison_feedback_source_check
CHECK (source IN ('result', 'contact'));

CREATE INDEX IF NOT EXISTS idx_comparison_feedback_request
ON public.comparison_feedback (compare_request_id)
WHERE compare_request_id IS NOT NULL;

DO $$
BEGIN
    IF (
        SELECT c.is_nullable
        FROM information_schema.columns AS c
        WHERE
            c.table_schema = 'public'
            AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'useful'
    ) = 'NO' THEN
        ALTER TABLE public.comparison_feedback ALTER COLUMN useful DROP NOT NULL;
        COMMENT ON COLUMN public.comparison_feedback.useful IS 'sf1_dropped_not_null';
    END IF;
END
$$;

COMMENT ON COLUMN public.comparison_feedback.correction IS
'S81-SF1: the optional correct product name (user text, at most 80 characters). Never read by a prompt, an exemplar builder or a store report.';

COMMENT ON COLUMN public.comparison_feedback.source IS
'S81-SF1: result = an answer on a comparison result; contact = a Contact Us submission. Learning readers exclude contact.';

DO $$
BEGIN
    IF (
        SELECT count(*)
        FROM information_schema.columns AS c
        WHERE
            c.table_schema = 'public'
            AND c.table_name = 'comparison_feedback'
            AND c.column_name IN (
                'identity_correct', 'wrong_side', 'preference', 'correction', 'source',
                'compare_request_id'
            )
    ) <> 6 THEN
        RAISE EXCEPTION '046 assert: a v2 column is missing';
    END IF;
    IF (
        SELECT c.is_nullable
        FROM information_schema.columns AS c
        WHERE
            c.table_schema = 'public'
            AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'useful'
    ) <> 'YES' THEN
        RAISE EXCEPTION '046 assert: comparison_feedback.useful is still NOT NULL';
    END IF;
    IF (
        SELECT count(*)
        FROM pg_constraint AS k
        WHERE
            k.conrelid = 'public.comparison_feedback'::regclass
            AND k.contype = 'c'
            AND k.conname IN (
                'comparison_feedback_identity_correct_check',
                'comparison_feedback_wrong_side_check',
                'comparison_feedback_preference_check',
                'comparison_feedback_correction_check',
                'comparison_feedback_source_check'
            )
    ) <> 5 THEN
        RAISE EXCEPTION '046 assert: a v2 CHECK constraint is missing';
    END IF;
    IF to_regclass('public.idx_comparison_feedback_request') IS NULL THEN
        RAISE EXCEPTION '046 assert: idx_comparison_feedback_request is missing';
    END IF;
END
$$;

COMMIT;

NOTIFY pgrst, 'reload schema';
