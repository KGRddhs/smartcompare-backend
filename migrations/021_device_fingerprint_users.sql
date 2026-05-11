-- migrations/021_device_fingerprint_users.sql
-- Free-tier counter inheritance via device fingerprint to prevent
-- freebie-farming via re-signup. See Bundle A design §1.5.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS device_fingerprint_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_users_device_fp
  ON users(device_fingerprint_hash)
  WHERE device_fingerprint_hash IS NOT NULL;

COMMENT ON COLUMN users.device_fingerprint_hash IS
  'SHA-256 hash of expo-application bundle id + expo-device osBuildId + SecureStore-pinned nonce. Used to lock free-tier counter across re-signups on same device.';
