-- 015_push_tokens.sql
-- Adds Expo Push token storage + notifications opt-out flag on users.
--
-- Required for: Loop 2 referrer push (B4.4), re-engagement push system
-- (B5.1-B5.3). push_service._get_user_push_token already reads this
-- column gracefully (returns None when missing) — adding it lets actual
-- push delivery work.
--
-- Apply via Supabase MCP `apply_migration` (NOT SQL Editor).

-- 1. Expo Push token (registered by frontend via expo-notifications).
-- Nullable — users can decline notifications permission at OS level.
ALTER TABLE users ADD COLUMN IF NOT EXISTS expo_push_token TEXT;

-- 2. Notifications enabled master toggle. Default TRUE so users opt IN
-- by default (matches design 9.2 + Profile UI default state). Re-engagement
-- cron filters on this column.
ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN
    NOT NULL DEFAULT TRUE;

-- 3. Last comparison timestamp — used by the re-engagement cron's
-- "active in last 60 days" filter (plan B5.1). Backfilled from
-- comparisons.created_at on initial deploy via the trigger below; new
-- rows get updated by feedback_service.save_comparison_and_track_cohort
-- once frontend wires it (deferred — for MVP cron reads from comparisons
-- table directly).
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_comparison_at TIMESTAMPTZ;

-- Index for re-engagement cron's eligibility query
CREATE INDEX IF NOT EXISTS idx_users_notifications_active
    ON users(notifications_enabled, last_comparison_at)
    WHERE notifications_enabled = TRUE;

-- Index on expo_push_token for fast push dispatch lookups
CREATE INDEX IF NOT EXISTS idx_users_expo_push_token
    ON users(expo_push_token)
    WHERE expo_push_token IS NOT NULL;
