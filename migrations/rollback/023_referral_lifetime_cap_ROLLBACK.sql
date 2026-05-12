-- Rollback for Migration 023.
-- Drops the lifetime counter + device fingerprint index, restores the weekly counter
-- to the pre-023 shape (data not restorable — referral system was OFF in Railway when 023 applied).

ALTER TABLE users DROP COLUMN IF EXISTS lifetime_invites_consumed;
DROP INDEX IF EXISTS idx_users_device_fingerprint_active;
ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_invites_used INT NOT NULL DEFAULT 0;
