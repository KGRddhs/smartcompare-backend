
---

## Orchestrator rulings (BINDING - supersede the review corrections and the body)

Fable orchestrator, session 71, 2026-10-03 09:32 +03. The spec body and the review section (file sha256 `7d579f1a...` after the reviewer's append) were read. Verdict: ACCEPTED with the rulings below. RED may start. Precedence: these rulings, then the review corrections, then the body. Agents never edit this spec.

- **UR1 - review corrections C1 to C14 are ACCEPTED as written and are binding.**
- **UR2 - live schema METADATA, measured by the orchestrator at 09:30** (the PostgREST OpenAPI document of the production project, fetched inside `railway run -s web`; column names, types, NOT NULL flags, defaults and foreign-key notes only; no table row was read and no credential, URL or project ref was printed):
  - `public.users` has exactly 27 columns, and they are the 27 of section 2a: `id`, `email`, `display_name`, `auth_provider`, `subscription_tier`, `subscription_expires_at`, `created_at`, `updated_at`, `preferences`, `preferences_completed`, `behavior_profile`, `lifetime_comparisons_used`, `demographics_profile`, `demographics_dismissed_count`, `demographics_dismissed_at`, `referral_code`, `referral_bonus_comparisons_this_month`, `referral_bonus_reset_at`, `expo_push_token`, `notifications_enabled`, `last_comparison_at`, `attribution_source`, `device_fingerprint_hash`, `lifetime_invites_consumed`, `terms_accepted_at`, `terms_version`, `age_attested_at`.
  - NOT NULL live: `id`, `referral_bonus_comparisons_this_month`, `notifications_enabled`, `lifetime_invites_consumed`. The tombstone values `0`, `false`, `0` for those three are therefore REQUIRED; `email` is nullable.
  - `governorate` is NOT a column of the live `users` table. C6's STOP does not trigger; the tombstone stays at 25 columns. The two readers of that non-existent column (`scripts/cron_reengagement.py`, `reengagement_service.py`) are a separate follow-up issue, filed by the orchestrator.
  - `created_at` exists (C11 resolved).
  - Foreign keys to `users.id` are declared on `deep_review_credits`, `pain_workflow_events`, `re_engagement_events`, `referral_invites` (both columns), `referral_redemptions` (both columns), `user_preference_history`, `user_usage`. None is declared on `comparisons`, `comparison_feedback`, `search_logs`, `user_events` or `admin_audit_log`.
  - NOT visible through this channel, so PRECHECK still decides them: the `users.id` foreign key to `auth.users` (branch A or B), unique indexes, CHECK constraints, triggers, RLS flags and owners. 043 stays correct in both branches.
- **UR3 (Q1) - `admin_audit_log`:** the cascade sets `ip_address` to NULL on the target's rows and keeps the rows. A retention window is a separate follow-up.
- **UR4 (Q2) - the backfill** ships as the optional fourth one-paste file; it is run only when PRECHECK shows a count above 0, after POSTCHECK passes.
- **UR5 (Q3) - the three consent columns are erased.** Counsel confirms the wording in U8.
- **UR6 (Q4) - the tombstone stays** (correct in both branches).
- **UR7 (Q5) - the client's `@qaren_recent_searches` is OUT of U8b;** one follow-up issue, to ship before U8 states that searches are deleted from the device.
- **UR8 (Q6) - 025's behaviour for invite rows where the deleted user is the redeemer is kept.**
- **UR9 (Q7) - no restated GRANT;** the assert block proves the privilege with `has_function_privilege`.
- **UR10 (Q8) - the free-quota reset on delete-and-re-register is accepted** and recorded beside U13's account-farming residual.
- **UR11 (Q9, C14) - the PostgreSQL 18 SINGLE-USER harness is allowed** for the GREEN gate G8 and for the adversaries: stdin only, no listener, no port, no network; the data directory lives under the agent's own notes folder and is left in place (no recursive delete). No agent ever connects to a real database, Supabase or Railway.
- **UR12 (Q10) - no `account_deleted` audit event.**
- **UR13 - the owner applies.** No agent applies, runs or pastes anything against production. The one-paste files are written to `docs/investigations/2026-10-03-session-71-state/` in the unit worktree. UR3, UR5 and UR10 are privacy defaults the owner may change before he applies 043: each is one place in the tombstone map or the function body, and the fence's expected map changes with it.
- **UR14 - roles.** Every agent is Opus. The RED agent writes ONLY `tests/test_migration_043_delete_user_cascade.py` and `tests/test_account_deletion_u8b.py`; it writes no migration, no SQL file, no file under `app/`. A RED fails inside its test body (the migration file does not exist yet), never at collection. The RED files are frozen after the orchestrator's gate; GREEN is a separate launch.
- **UR15 - base** is main `eb86075e`; the migration number is 043 (042 is the highest file, 039 stays reserved).
