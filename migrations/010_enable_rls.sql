-- migrations/010_enable_rls.sql
-- Security hardening: Enable Row Level Security on all user-data tables
-- Run in Supabase SQL Editor (Dashboard > SQL Editor > New Query)

-- ============================================
-- Enable RLS
-- ============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparison_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;

-- ============================================
-- users: read/update own row only
-- ============================================
CREATE POLICY users_select ON users FOR SELECT
  USING (auth.uid() = id);
CREATE POLICY users_update ON users FOR UPDATE
  USING (auth.uid() = id);
CREATE POLICY users_insert ON users FOR INSERT
  WITH CHECK (auth.uid() = id);

-- ============================================
-- comparisons: own rows + shared via token
-- ============================================
CREATE POLICY comparisons_select ON comparisons FOR SELECT
  USING (auth.uid() = user_id OR share_token IS NOT NULL);
CREATE POLICY comparisons_insert ON comparisons FOR INSERT
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY comparisons_delete ON comparisons FOR DELETE
  USING (auth.uid() = user_id);
-- UPDATE needed for share_token assignment
CREATE POLICY comparisons_update ON comparisons FOR UPDATE
  USING (auth.uid() = user_id);

-- ============================================
-- search_logs: own rows (allow anonymous inserts)
-- ============================================
CREATE POLICY search_logs_insert ON search_logs FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY search_logs_select ON search_logs FOR SELECT
  USING (auth.uid() = user_id);

-- ============================================
-- comparison_feedback: own rows (allow anonymous)
-- ============================================
CREATE POLICY feedback_insert ON comparison_feedback FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY feedback_select ON comparison_feedback FOR SELECT
  USING (auth.uid() = user_id);

-- ============================================
-- user_events: own rows (allow anonymous)
-- ============================================
CREATE POLICY events_insert ON user_events FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY events_select ON user_events FOR SELECT
  USING (auth.uid() = user_id);

-- ============================================
-- bahrain_approved_drugs: read-only for all
-- ============================================
CREATE POLICY drugs_select ON bahrain_approved_drugs FOR SELECT
  USING (true);

-- ============================================
-- Atomic cascade delete function (SECURITY DEFINER = runs as owner, bypasses RLS)
-- ============================================
CREATE OR REPLACE FUNCTION delete_user_cascade(target_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  DELETE FROM user_events WHERE user_id = target_user_id;
  DELETE FROM comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM comparisons WHERE user_id = target_user_id;
  DELETE FROM search_logs WHERE user_id = target_user_id;
  UPDATE users SET preferences = NULL, behavior_profile = NULL,
    preferences_completed = false WHERE id = target_user_id;
END;
$$;
