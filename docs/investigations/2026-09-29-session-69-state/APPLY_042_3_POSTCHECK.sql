-- 042 POST-CHECKS (separate read-only runs, AFTER the one-paste apply)
SELECT count(*) FROM public.search_logs WHERE is_synthetic;
SELECT count(*) FROM public.search_logs WHERE is_synthetic AND created_at < TIMESTAMPTZ '2026-06-01 00:00:00+00';
SELECT count(*) FROM public.search_logs WHERE is_synthetic IS NULL;
-- Paste back: BEFORE = a + b, EXCLUDED = c, AFTER, plus a_pull (anchor 11,724) and c_pull (anchor 295)
-- into docs/investigations/2026-09-29-session-69-state/APPLY_OUTPUTS.md
