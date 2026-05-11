-- migrations/022_referral_invites_code_redeem.sql
-- Bundle A §1.1 — Code Redeem flow.
--
-- Allows a referral_invites row to be created at Register time when the new
-- user typed an `invite_code` (vs. arriving via a share-token deep link with
-- a pre-existing comparison_id).
--
-- Two changes:
--   1. Relax `comparison_id` to NULLABLE — code_redeem invites have no source
--      comparison; they're freshly minted when the new user types QR-XXXXXX.
--   2. Add `source` TEXT column distinguishing the two creation paths:
--        'share_link'   — existing share-sheet flow, comparison_id NOT NULL
--        'code_redeem'  — new Bundle A flow, comparison_id NULL
--
-- Defense-in-depth CHECK: code_redeem rows must NOT have a comparison_id, and
-- share_link rows MUST have one. Prevents future drift.

ALTER TABLE referral_invites
    ALTER COLUMN comparison_id DROP NOT NULL;

ALTER TABLE referral_invites
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'share_link';

-- Backfill existing rows are share_link by definition (had comparison_id NOT NULL).
UPDATE referral_invites SET source = 'share_link' WHERE source IS NULL;

ALTER TABLE referral_invites
    ADD CONSTRAINT referral_invites_source_check
    CHECK (source IN ('share_link', 'code_redeem'));

-- A code_redeem invite must have no comparison_id; a share_link invite must.
ALTER TABLE referral_invites
    ADD CONSTRAINT referral_invites_source_comparison_consistency
    CHECK (
        (source = 'share_link'  AND comparison_id IS NOT NULL)
     OR (source = 'code_redeem' AND comparison_id IS NULL)
    );

CREATE INDEX IF NOT EXISTS idx_referral_invites_source
    ON referral_invites(source);

COMMENT ON COLUMN referral_invites.source IS
    'Creation path: share_link (share-sheet flow) or code_redeem (Bundle A — invite_code typed at Register).';
