-- Migration 023: Replace weekly per-user invite cap with lifetime per-device cap.
-- Aligns with Bundle A's device-bound anti-abuse model (Migration 021).

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS lifetime_invites_consumed INT NOT NULL DEFAULT 0;

ALTER TABLE users
  DROP COLUMN IF EXISTS weekly_invites_used;

CREATE INDEX IF NOT EXISTS idx_users_device_fingerprint_active
  ON users(device_fingerprint_hash)
  WHERE device_fingerprint_hash IS NOT NULL;

COMMENT ON COLUMN users.lifetime_invites_consumed IS
  'Successful referrals attributed to this user. Hard cap 3 enforced per device fingerprint (not per user). Set at receiver signup completion, never reset.';
