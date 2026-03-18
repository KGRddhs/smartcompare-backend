-- Migration: Add share_token column to comparisons table
-- Date: 2026-03-18
-- Session: 24

-- Apply
ALTER TABLE comparisons ADD COLUMN IF NOT EXISTS share_token VARCHAR(12) DEFAULT NULL UNIQUE;
CREATE INDEX IF NOT EXISTS idx_comparisons_share_token ON comparisons(share_token) WHERE share_token IS NOT NULL;

-- Rollback (run manually if needed):
-- DROP INDEX IF EXISTS idx_comparisons_share_token;
-- ALTER TABLE comparisons DROP COLUMN IF EXISTS share_token;
