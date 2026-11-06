-- APPLY_046_3_POSTCHECK (S81-SF1 SURFACES-BE): READ-ONLY, one row, AFTER the one
-- paste. Expected: column_count_v2 6, useful_nullable YES, useful_comment
-- 'sf1_dropped_not_null' when the PRECHECK read useful_is_nullable NO (else the prior
-- comment or NULL), source_default 'result'::text, source_not_null t, check_count_v2 5,
-- request_index_present t, null_source_rows 0.
SELECT
    (
        SELECT count(*) FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name IN ('identity_correct', 'wrong_side', 'preference', 'correction', 'source', 'compare_request_id')
    ) AS column_count_v2,
    (
        SELECT c.is_nullable FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'useful'
    ) AS useful_nullable,
    col_description(to_regclass('public.comparison_feedback'), (
        SELECT a.attnum::int FROM pg_attribute AS a
        WHERE a.attrelid = to_regclass('public.comparison_feedback') AND a.attname = 'useful'
    )) AS useful_comment,
    (
        SELECT c.column_default FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'source'
    ) AS source_default,
    (
        SELECT c.is_nullable = 'NO' FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'source'
    ) AS source_not_null,
    (
        SELECT count(*) FROM pg_constraint AS k
        WHERE k.conrelid = to_regclass('public.comparison_feedback') AND k.contype = 'c'
            AND k.conname IN (
                'comparison_feedback_identity_correct_check',
                'comparison_feedback_wrong_side_check',
                'comparison_feedback_preference_check',
                'comparison_feedback_correction_check',
                'comparison_feedback_source_check'
            )
    ) AS check_count_v2,
    to_regclass('public.idx_comparison_feedback_request') IS NOT NULL AS request_index_present,
    (SELECT count(*) FROM public.comparison_feedback WHERE source IS NULL) AS null_source_rows;
