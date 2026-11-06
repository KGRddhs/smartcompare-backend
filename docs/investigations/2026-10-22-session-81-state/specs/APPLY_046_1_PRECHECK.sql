-- APPLY_046_1_PRECHECK (S81-SF1 SURFACES-BE): READ-ONLY, one row. Run it in the
-- Supabase SQL editor BEFORE APPLY_046_2_ONE_PASTE and send the row (values only, no
-- row content). Expected: pg15_or_later t, feedback_table_present t,
-- useful_is_boolean t, the_027_checks 3, v2_columns_absent t. RECORD useful_is_nullable
-- (NO = 046 will drop NOT NULL and write the sf1_dropped_not_null comment; YES = it
-- will not) and useful_has_comment (t = a comment already exists: tell the orchestrator
-- before applying, 046 would overwrite it).
SELECT
    current_setting('server_version_num')::int >= 150000 AS pg15_or_later,
    to_regclass('public.comparison_feedback') IS NOT NULL AS feedback_table_present,
    (
        SELECT c.data_type = 'boolean'
        FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'useful'
    ) AS useful_is_boolean,
    (
        SELECT c.is_nullable
        FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name = 'useful'
    ) AS useful_is_nullable,
    col_description(to_regclass('public.comparison_feedback'), (
        SELECT a.attnum::int FROM pg_attribute AS a
        WHERE a.attrelid = to_regclass('public.comparison_feedback') AND a.attname = 'useful'
    )) IS NOT NULL AS useful_has_comment,
    (
        SELECT count(*) FROM pg_constraint AS k
        WHERE k.conrelid = to_regclass('public.comparison_feedback') AND k.contype = 'c'
            AND k.conname IN (
                'comparison_feedback_winner_correct_check',
                'comparison_feedback_price_correct_check',
                'comparison_feedback_specs_correct_check'
            )
    ) AS the_027_checks,
    (
        SELECT count(*) = 0 FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'comparison_feedback'
            AND c.column_name IN ('identity_correct', 'wrong_side', 'preference', 'correction', 'source', 'compare_request_id')
    ) AS v2_columns_absent,
    (SELECT count(*) FROM public.comparison_feedback) AS feedback_row_count;
