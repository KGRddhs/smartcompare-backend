-- rollback/041_user_events_drop_public_select_policy.sql
--
-- WARNING — RUNNING THIS RE-OPENS CR-SECURITY-02. It restores the out-of-band
-- policy exactly as it was measured live on 2026-09-24 (PERMISSIVE, FOR SELECT,
-- roles {public}, USING (true)), which is what let the anon role read all 147
-- public.user_events rows. A rollback restores the PRIOR state; it does not make
-- that state safe. Run it only to reproduce the pre-041 database, and re-apply
-- 041 afterwards.
--
-- Verify after running: the anon-key count=exact over user_events goes back to
-- every row (147 at the time of measurement); pg_policies lists the policy again.

BEGIN;

-- RF05 exemption: the measured live policy name contains spaces, so it can
-- only be re-created by quoting it verbatim.
CREATE POLICY "Service role can read all events" ON public.user_events -- noqa: RF05
  FOR SELECT
  TO public
  USING (true);

COMMIT;
