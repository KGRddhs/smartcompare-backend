-- Rollback Migration 024 — revert to pre-Bundle-C 4-tier enum
-- WARNING: Any users with budget='top_tier' will fail CHECK; UPDATE to 'luxury' first.

UPDATE public.users
SET preferences = jsonb_set(preferences, '{budget}', '"luxury"')
WHERE preferences->>'budget' = 'top_tier';

ALTER TABLE public.users
  DROP CONSTRAINT IF EXISTS users_preferences_budget_check;

ALTER TABLE public.users
  ADD CONSTRAINT users_preferences_budget_check
  CHECK (
    preferences->>'budget' IS NULL
    OR preferences->>'budget' IN ('budget', 'mid', 'premium', 'luxury')
  );
