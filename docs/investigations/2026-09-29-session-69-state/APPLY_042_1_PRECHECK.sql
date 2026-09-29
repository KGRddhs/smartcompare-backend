-- 042 PRE-CHECK (separate read-only run, BEFORE the one-paste apply)
-- Expected: NO is_synthetic column in the output.
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'search_logs'
 ORDER BY ordinal_position;
