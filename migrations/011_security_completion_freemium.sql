-- migrations/011_security_completion_freemium.sql
-- Session 39: Security Completion + Freemium Tiers
-- Run via Supabase SQL Editor (manual step)

-- ============================================
-- 1. USAGE TRACKING TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    comparison_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, period)
);

ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;
CREATE POLICY usage_select ON user_usage FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY usage_insert ON user_usage FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY usage_update ON user_usage FOR UPDATE USING (auth.uid() = user_id);

CREATE INDEX idx_usage_user_period ON user_usage (user_id, period);

-- ============================================
-- 2. USERS TABLE: NEW COLUMNS
-- ============================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS lifetime_comparisons_used INT DEFAULT 0;

-- ============================================
-- 3. AUDIT LOG TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    user_id UUID,
    ip_address TEXT,
    endpoint TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;
-- Only service_role can read audit logs (admin endpoints use admin client)
CREATE POLICY audit_insert ON admin_audit_log FOR INSERT WITH CHECK (true);

CREATE INDEX idx_audit_event_time ON admin_audit_log (event_type, created_at DESC);
CREATE INDEX idx_audit_user_time ON admin_audit_log (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_created ON admin_audit_log (created_at DESC);

-- ============================================
-- 4. LIFETIME COMPARISONS INCREMENT FUNCTION
-- ============================================
CREATE OR REPLACE FUNCTION increment_lifetime_comparisons(target_user_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE users SET lifetime_comparisons_used = COALESCE(lifetime_comparisons_used, 0) + 1
    WHERE id = target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
