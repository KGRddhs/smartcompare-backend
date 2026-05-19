-- Pre-rollback step for Migration 024 (Bundle C tier expansion).
--
-- Purpose: downgrade any persisted users.preferences.budget rows currently set to
-- 'top_tier' or 'luxury' down to 'premium' BEFORE running the main rollback
-- (migrations/rollback/024_top_tier_budget.sql), so the rollback CHECK swap
-- does not fail or block in-flight UPDATE statements with CHECK violations.
--
-- Idempotent: re-running is safe (the WHERE filter is a no-op once all rows
-- are at 'premium' or below).
--
-- When to run: emergency rollback path only. Plan reference: D.7.3.
-- Spec reference: §8e (rollback path) + §3d (existing rows untouched on forward).
--
-- Apply via Supabase MCP: mcp__plugin_supabase_supabase__execute_sql
-- (Migration MCP not used here — this is a data fix, not a schema change.)
--
-- User-side UX impact: their saved preference silently degrades to 'premium';
-- the picker may still show 5 tiers until a fresh `eas update` reverts it,
-- but selecting 'top_tier'/'luxury' would fail with a CHECK violation on save.
-- Acceptable for an emergency-only path.

UPDATE public.users
SET preferences = jsonb_set(preferences, '{budget}', '"premium"')
WHERE preferences->>'budget' IN ('top_tier', 'luxury');

-- Verification query (run AFTER the UPDATE, BEFORE the rollback CHECK swap):
--   SELECT preferences->>'budget' AS budget, COUNT(*) AS rows
--   FROM public.users
--   GROUP BY 1
--   ORDER BY 1;
-- Expected: no rows with budget IN ('top_tier', 'luxury').
