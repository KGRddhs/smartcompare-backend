-- 018_referral_bonus_expires_at.sql
-- Adds expires_at + consumed_at to referral_redemptions, deep_review_expires_at
-- to referral_invites, and expiry_reminder_sent_at idempotency flag.
-- Plan task 34 / design 4e (3-day bonus-credit expiry).
--
-- Apply via Supabase MCP `apply_migration` — NEVER SQL Editor (per CLAUDE.md
-- gotcha; multi-statement scripts wrap in a transaction and a failing view
-- can roll back the ALTER before it).
--
-- LIVE-SCHEMA VERIFIED 2026-05-06 via information_schema.columns:
-- referral_redemptions current columns (migration 014, no consumed_at): id,
-- invite_id, referrer_user_id, invitee_user_id, loop2_comparisons_granted,
-- created_at. The `consumed_at TIMESTAMPTZ` in migration 014 line 53 lives
-- on `deep_review_credits` — NOT on `referral_redemptions`. The ADD COLUMN
-- below is therefore necessary, not redundant. (frontend-visual QA misread.)
-- No existing index named `idx_referral_redemptions_expires_at` (verified
-- via pg_indexes).

-- 1. expires_at on redemptions. NULL = legacy/unbounded; new rows from
-- referral_service set this 3 days after creation.
ALTER TABLE public.referral_redemptions
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- 2. consumed_at marks when an invitee actually used the bonus
-- comparisons. Migration 014 omits this column on referral_redemptions;
-- adding it now (column exists on deep_review_credits but that's a
-- separate table). Idempotent — safe if a future migration also adds it.
ALTER TABLE public.referral_redemptions
  ADD COLUMN IF NOT EXISTS consumed_at TIMESTAMPTZ;

-- 3. Backfill: existing in-flight (NULL expires_at) redemptions get
-- 3-day grace from now. One-shot — safe because of the WHERE clause.
UPDATE public.referral_redemptions
SET expires_at = NOW() + INTERVAL '3 days'
WHERE expires_at IS NULL AND consumed_at IS NULL;

-- 4. Partial index for cron query — only unconsumed rows matter for
-- expiry sweep. Coexists fine with `idx_referral_redemptions_referrer`
-- from migration 014 (different columns).
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_expires_at
  ON public.referral_redemptions (expires_at)
  WHERE consumed_at IS NULL;

-- 5. Loop 1 deep-review credit expiry on referral_invites — separate
-- from deep_review_credits.expires_at (already 30d default per migration
-- 014). This is the *invite-level* tracker for "X days left to redeem".
ALTER TABLE public.referral_invites
  ADD COLUMN IF NOT EXISTS deep_review_expires_at TIMESTAMPTZ;

-- 6. Notification-sent flag on redemptions — prevents the cron from
-- double-sending the 24h-before-expiry reminder push (idempotency
-- invariant for plan task 36). TIMESTAMPTZ (not BOOL) so we can audit
-- WHEN the reminder went out, not just IF.
ALTER TABLE public.referral_redemptions
  ADD COLUMN IF NOT EXISTS expiry_reminder_sent_at TIMESTAMPTZ;
