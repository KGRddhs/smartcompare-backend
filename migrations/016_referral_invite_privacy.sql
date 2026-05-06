-- 016_referral_invite_privacy.sql
-- Adds per-share privacy toggle storage on referral_invites.
--
-- Closes the F2.3 gap: ShareBottomSheet exposes 3 user-togglable privacy
-- options (show_name / show_result / show_reasons) but the data wasn't
-- reaching the backend. Now stored as JSONB so resolve_invite can honour
-- the referrer's choices when rendering the invitee landing page.
--
-- Schema choice: single JSONB column (not 3 booleans) for forward-compat —
-- design 11 mentions vanity-code privacy and other v1.1 additions.

ALTER TABLE referral_invites ADD COLUMN IF NOT EXISTS privacy JSONB
    NOT NULL DEFAULT '{"show_name": true, "show_result": true, "show_reasons": true}'::jsonb;

-- Comment captures the contract so future readers don't need to grep code:
COMMENT ON COLUMN referral_invites.privacy IS
    'Per-share privacy toggles (design 3.3). Keys: show_name, show_result, show_reasons. show_budget is always false — never include the referrer''s budget in the invitee view.';
