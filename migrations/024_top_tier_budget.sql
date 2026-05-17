-- Migration 024: Add top_tier to users.preferences.budget CHECK enum
-- Bundle C tier expansion (per design § 3a/3d/8a)
-- Apply via Supabase MCP: mcp__plugin_supabase_supabase__apply_migration

ALTER TABLE public.users
  DROP CONSTRAINT IF EXISTS users_preferences_budget_check;

ALTER TABLE public.users
  ADD CONSTRAINT users_preferences_budget_check
  CHECK (
    preferences->>'budget' IS NULL
    OR preferences->>'budget' IN ('budget', 'mid', 'premium', 'luxury', 'top_tier')
  );

-- Existing rows untouched. New users default to 'mid' (per design § 3d).
-- Backwards-compat: 3-tier values ('budget','mid','premium') remain valid (per design § 3d).
