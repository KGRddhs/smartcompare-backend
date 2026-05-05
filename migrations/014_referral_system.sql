-- 014_referral_system.sql
-- Smart Decision Referral System schema (Cut C — Maximum Impact v1).
-- Adds dual-loop referrals (Loop 1 immediate Deep Review credit on share,
-- Loop 2 deferred +5/+10 comparisons on invitee conversion), bonus capacity
-- tracking, and re-engagement push event log.
--
-- Apply via Supabase MCP `apply_migration` (NOT SQL Editor — see Session 41
-- learning, view-bug rollback risk).

-- 1. Extend users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code TEXT UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_comparisons_this_month INT DEFAULT 0 NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_reset_at TIMESTAMPTZ
    DEFAULT date_trunc('month', now()) + interval '1 month';
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);

-- 2. referral_invites
CREATE TABLE IF NOT EXISTS referral_invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  comparison_id UUID NOT NULL REFERENCES comparisons(id) ON DELETE CASCADE,
  share_target TEXT NOT NULL CHECK (share_target IN ('whatsapp','copy','x','telegram','snapchat','other')),
  device_fingerprint_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  first_viewed_at TIMESTAMPTZ,
  redeemed_at TIMESTAMPTZ,
  redeemed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  invitee_first_comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL,
  flagged_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_referral_invites_referrer_created ON referral_invites(referrer_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_referral_invites_comparison ON referral_invites(comparison_id);
CREATE INDEX IF NOT EXISTS idx_referral_invites_redeemed_by ON referral_invites(redeemed_by_user_id);

-- 3. referral_redemptions
CREATE TABLE IF NOT EXISTS referral_redemptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invite_id UUID NOT NULL UNIQUE REFERENCES referral_invites(id) ON DELETE CASCADE,
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invitee_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  loop2_comparisons_granted INT NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_referrer ON referral_redemptions(referrer_user_id, created_at DESC);

-- 4. deep_review_credits
CREATE TABLE IF NOT EXISTS deep_review_credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('share_loop1','invitee_signup','manual')),
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + interval '30 days',
  consumed_at TIMESTAMPTZ,
  consumed_in_comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_deep_review_credits_user_available
  ON deep_review_credits(user_id, expires_at)
  WHERE consumed_at IS NULL;

-- 5. re_engagement_events
CREATE TABLE IF NOT EXISTS re_engagement_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('decision_insight','cohort_curiosity','decision_retrospective')),
  comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL,
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  content_payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_re_engagement_user_triggered ON re_engagement_events(user_id, triggered_at DESC);

-- 6. RLS policies (Session 38 pattern: SELECT only own rows; service-role bypasses RLS)
ALTER TABLE referral_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_review_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE re_engagement_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS referral_invites_select_own ON referral_invites;
CREATE POLICY referral_invites_select_own ON referral_invites FOR SELECT TO authenticated
  USING (referrer_user_id = auth.uid() OR redeemed_by_user_id = auth.uid());

DROP POLICY IF EXISTS referral_redemptions_select_own ON referral_redemptions;
CREATE POLICY referral_redemptions_select_own ON referral_redemptions FOR SELECT TO authenticated
  USING (referrer_user_id = auth.uid() OR invitee_user_id = auth.uid());

DROP POLICY IF EXISTS deep_review_credits_select_own ON deep_review_credits;
CREATE POLICY deep_review_credits_select_own ON deep_review_credits FOR SELECT TO authenticated
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS re_engagement_events_select_own ON re_engagement_events;
CREATE POLICY re_engagement_events_select_own ON re_engagement_events FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- 7. Public RPC for invitee landing — exposes only the referrer's display name
-- (per their privacy toggle for `name` — to be honored at app layer).
CREATE OR REPLACE FUNCTION resolve_referral_code(p_code TEXT)
RETURNS TABLE(referrer_user_id UUID, display_name TEXT)
LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT id, COALESCE(display_name, 'A friend') FROM users WHERE referral_code = p_code LIMIT 1;
$$;
GRANT EXECUTE ON FUNCTION resolve_referral_code(TEXT) TO anon, authenticated;
