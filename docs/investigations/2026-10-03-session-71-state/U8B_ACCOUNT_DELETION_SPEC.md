# U8b: account deletion that erases what it says it erases (spec)

Unit U8b of the MYEZ Apple launch lane. The spec was written by a read-and-measure agent on 2026-10-03, from 08:29 to 09:05 AST. No database, network service, Railway or Supabase was touched. Every live-schema unknown is listed as a PRECHECK query (R8.1).

Ahmed's approval, recorded in `sc-docs-70/docs/investigations/2026-10-03-session-71-state/IMPLEMENTATION_PLAN.md` ("Ahmed's answers", ~07:20 AST): **"account deletion is fixed in code — a new backend unit U8b (`delete_user_cascade` also nulls demographics, display name and email; a migration Ahmed applies)"**. The research digest names the gap (`RESEARCH_DIGEST.md:461-466`): "`delete_user_cascade` keeps `admin_audit_log` and the users row. It does not null `demographics_profile`, `display_name`, `email` or the consent columns." Guideline 5.1.1(v) needs deletion of the account and its data, and the M11 policy item needs a true statement of what is kept.

---

## 1. Base

```
$ git -C C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b rev-parse HEAD
eb86075ed1f9c65716118ae5567898d01b16a27a
$ git -C ... status
On branch feature/s71-u8b-account-deletion
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
$ git -C ... log --oneline -1
eb86075e Merge pull request #279 from KGRddhs/feature/s70-u4b-icons-deps
```

The PIN set was run at base through the bounded runner, as run R0:

```
pyt.py --bound 600 --tag u8b-spec-pins-base -- tests/test_delete_user_cascade.py tests/test_account_deletion.py
  tests/test_migration_037_security_definer_grants.py tests/test_retro_w1_2b.py tests/test_retro_w1_2d.py
  tests/test_sqlfluff_config.py tests/test_migration_index_predicate_immutability.py tests/test_security_regression.py
=============== 241 passed, 4 deselected, 11 warnings in 23.71s ===============
[pyt] tag=u8b-spec-pins-base start=2026-10-03 08:50:54 end=2026-10-03 08:51:21 elapsed=26s bound=600s status=OK rc=0
```

The scratch evidence is in `<scratchpad>/u8b/`: `notes.md`, `scan_migrations.py` with `scan_out.txt`, `fence_proto.py` with `fence_base.txt` and `fence_head.txt`, the `proto/` copies of the migration and the rollback, and `comm_set_base.txt`.

---

## 2. Measured facts

### 2a. The `users` table

**No migration creates `public.users`.** The table was created out of band, like `comparisons`, `comparison_feedback` and `user_events`.

```
$ grep -n -i -E "create table|alter table" migrations/*.sql   (no CREATE TABLE users / comparisons / comparison_feedback / user_events)
$ grep -rn -i -E "create table (if not exists )?(public\.)?(users|comparisons|comparison_feedback|user_events)\b" .
./docs/CONTEXT_DATABASE_API.md:83:CREATE TABLE public.users (
./docs/CONTEXT_DATABASE_API.md:101:CREATE TABLE comparisons (
```

Two sources describe the table. `docs/CONTEXT_DATABASE_API.md:83-92` is documentation, not DDL. The 2026-06-08 live audit, `docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md:61-83`, reads "`users` columns (currently 22)". From the documentation:

```
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT,
    auth_provider TEXT DEFAULT 'email',
    subscription_tier TEXT DEFAULT 'free',
    subscription_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

The audit adds `preferences jsonb default '{}'`, `preferences_completed boolean default false` and `behavior_profile jsonb default '{}'` (all three out of band, nullability not stated).

The columns that migrations add were found with `scan_migrations.py`; the output is in `scan_out.txt`:

| column | type, nullability, default and constraints (as the file writes them) | file:line |
|---|---|---|
| subscription_tier | TEXT DEFAULT 'free' (`ADD COLUMN IF NOT EXISTS`, already present per the doc) | 011:28 |
| lifetime_comparisons_used | INT DEFAULT 0, nullable | 011:29 |
| demographics_profile | JSONB DEFAULT NULL | 013:19 |
| demographics_dismissed_count | INT DEFAULT 0, nullable | 013:20 |
| demographics_dismissed_at | TIMESTAMPTZ DEFAULT NULL | 013:21 |
| referral_code | TEXT **UNIQUE**, nullable (UNIQUE allows many NULLs) | 014:11 |
| referral_bonus_comparisons_this_month | INT DEFAULT 0 **NOT NULL** | 014:12 |
| referral_bonus_reset_at | TIMESTAMPTZ DEFAULT date_trunc('month', now()) + interval '1 month' | 014:13-14 |
| expo_push_token | TEXT, nullable | 015:13 |
| notifications_enabled | BOOLEAN **NOT NULL** DEFAULT TRUE | 015:18-19 |
| last_comparison_at | TIMESTAMPTZ | 015:27 |
| attribution_source | TEXT CHECK (NULL or one of 6 values) | 019:12-17 |
| device_fingerprint_hash | TEXT | 021:5-6 |
| lifetime_invites_consumed | INT **NOT NULL** DEFAULT 0 | 023:4-5 |
| weekly_invites_used | DROPPED | 023:7-8 |
| terms_accepted_at, terms_version, age_attested_at | TIMESTAMPTZ / TEXT / TIMESTAMPTZ, nullable | 038:30-33 |

The table also carries constraint `users_preferences_budget_check` (`preferences->>'budget' IS NULL OR IN (...)`, 024:5-13) and partial index `idx_users_device_fingerprint_active` (023:10-12; the duplicate `idx_users_device_fp` was dropped at 032:73).

Answers to the questions this section was asked:

- **Is `users.id` a foreign key to `auth.users`, and with which ON DELETE?** In the repo, only the documentation says so: `REFERENCES auth.users(id) ON DELETE CASCADE` (`CONTEXT_DATABASE_API.md:84`). No migration, test or live dump confirms it. `docs/CONTEXT_DECISIONS_BUGS.md:18` says "VERIFY in Supabase Studio". Review finding data-03 (`docs/investigations/2026-08-31-m13-review/data-migrations.verified.json`) was DOWNGRADED on the strength of the same documentation line. The question is **PRECHECK §4**.
- **Is `email` NOT NULL or UNIQUE?** The documentation says `email TEXT`, which is nullable and not unique. No migration touches it. The question is **PRECHECK §1, §2 and §3**. The migration's guard block (R1) aborts if it is NOT NULL live.
- **Columns the code writes that no migration creates.** All `.table("users")` sites were checked: 53 in `app/` and 54 counting `scripts/` (`grep -rhoE 'table\("users"\)' app/ scripts/ | wc -l` gives 54). The written columns are `email`, `subscription_tier` (`auth_service.py:405-410, 827-833`), `auth_provider` (:830), `display_name` (:906-908), `preferences` and `preferences_completed` (:958-961, `auth_routes.py:1392, 1462`), `behavior_profile` (`structured_comparison_service.py:5226`), `updated_at` and `subscription_expires_at` (`database_service.py:374-381`), and the consent columns (`consent_columns`). **The out-of-band columns are `email, display_name, auth_provider, subscription_expires_at, updated_at, preferences, preferences_completed, behavior_profile`.** Every other written column (`device_fingerprint_hash`, `lifetime_comparisons_used`, `expo_push_token`, `demographics_profile`, `attribution_source`, `referral_code`, `referral_bonus_*`, `lifetime_invites_consumed`) is created by a migration. No column is written that neither a migration nor the documentation names. `demographics_dismissed_count`, `demographics_dismissed_at` and `last_comparison_at` are created but **never written** by app code (grep finds no writer). They are still erased.
- **The `admin_audit_log` foreign key.** `011:34-42` creates `user_id UUID,` with **no REFERENCES**. The reason 025 gives for keeping the row (`025:57`: "We keep the row so admin_audit_log foreign keys resolve") is false in the files. This was measured independently by data-03, whose `verify_evidence` reads: "admin_audit_log is in NONE of them". The live table could differ (`CREATE TABLE IF NOT EXISTS`), which is **PRECHECK §4**.

**What happens today, in order** (`auth_routes.py:1165-1177`, `auth_service.py:980-988`, `database_service.py:392-401`):

1. `DELETE /api/v1/auth/account` runs: bearer only, no password re-auth, `@limiter.limit("1/minute")`. The client sends nothing else.
2. `delete_user_account` awaits `delete_user_data_cascade`, which issues ONE `rpc("delete_user_cascade")` on the service-role client. One RPC is one statement, so the function is atomic: if it fails, nothing changed.
3. `admin.auth.admin.delete_user(user_id)` runs, a hard delete (`should_soft_delete=False`; supabase_auth 2.31.0 `gotrue_admin_api.py:184-193`).
4. What step 3 does to `public.users` depends on the live foreign key:
   - **Branch A** (the documented FK is live): deleting from `auth.users` deletes the `public.users` row. That row cascades to `user_usage`, `referral_invites` (as referrer), `referral_redemptions`, `deep_review_credits`, `re_engagement_events`, `pain_workflow_events` and `user_preference_history` (all `ON DELETE CASCADE` to `users`: 011:10, 014:20/39/40/49/63, 028:35, 029:45), and sets `referral_invites.redeemed_by_user_id` to NULL (014:27). In this branch 025's "kept row" lives for milliseconds. What survives a *successful* deletion today is the `admin_audit_log` rows (no FK) and the Redis caches (§2c).
   - **Branch B** (no such FK live): the row survives with `email`, `display_name`, `auth_provider`, demographics, attribution, referral code, consent, opt-in and counters. Every row of the 014, 028 and 029 tables that 025 does not touch also survives. Nothing ever removes them.
5. If step 3 fails (any branch), the data is already erased, the auth user still exists, the route returns 500, and the user is still signed in to an emptied account. A retry is safe because the function is idempotent.
6. If step 2 fails, both log lines carry the PostgREST error text (§2c, finding F-LOG) and nothing is deleted.

### 2b. Every table that references a user

Sources: `scan_out.txt` (CREATE/ALTER statements with a user FK or a user-ish column name), the out-of-band tables from §2a, and the 2026-06-08 audit (`preflight.md:85-110`).

| table | created | user columns | FK and ON DELETE (files) | 025 does | personal? | 043 does |
|---|---|---|---|---|---|---|
| users | out of band | id | id→auth.users CASCADE (doc only, PRECHECK) | partial UPDATE | yes | full tombstone (R3) |
| comparisons | out of band (+001, 017, 020) | user_id, share_token | user_id→auth.users CASCADE (doc :103) | DELETE | yes: queries, results, public share links | DELETE (same) |
| comparison_feedback | out of band (+027) | user_id; change_suggestion free text | "FK to users.id" (audit), action unknown | DELETE | yes | DELETE |
| user_events | out of band | user_id, session_id, event_data | "FK", target unknown | DELETE | yes | DELETE |
| search_logs | 002:5-16 (IF NOT EXISTS) | user_id | →auth.users, **NO ACTION** (002:7) | DELETE | yes: queries | DELETE |
| user_usage | 011:8-16 | user_id | users CASCADE | DELETE | usage counts | DELETE |
| admin_audit_log | 011:34-42 | user_id (no FK), **ip_address**, details jsonb | none | KEPT | yes: user id + IP on `login_success` and `invite_code_redeemed` (`auth_routes.py:659-662, 728-731`); referral-flag rows carry `referrer_user_id` in details (`referral_service.py:668-694`); lockouts carry `email_hash` = sha256(email)[:16] with `user_id` NULL (`auth_routes.py:688-692`) | KEPT; `ip_address` set to NULL where `user_id` = target (R1, Q1) |
| referral_invites | 014:18-30 (+016, 018, 022) | referrer_user_id, redeemed_by_user_id, device_fingerprint_hash (the referrer's, `referral_service.py:322`) | referrer users CASCADE; redeemed_by SET NULL | DELETE either role | yes | DELETE (same; Q6) |
| referral_redemptions | 014:36-43 (+018) | referrer_user_id, invitee_user_id | both users CASCADE | DELETE either role | yes | DELETE (same) |
| deep_review_credits | 014:47-55 | user_id | users CASCADE | **not touched** | low | **DELETE** |
| re_engagement_events | 014:61-70 | user_id, content_payload | users CASCADE | **not touched** | yes: push content | **DELETE** |
| pain_workflow_events | 028:33-67 | user_id, signal_payload | public.users CASCADE | **not touched** | yes: behaviour | **DELETE** |
| user_preference_history | 029:43-60 | user_id, preferences snapshots | public.users CASCADE | **not touched** | yes | **DELETE** |

These tables have no user reference: `products` (002), `product_specs`, `product_prices` and `product_reviews` (012; keyed by `product_key`, written from compares but never with a user id), `verdict_critiques` (030; FK `comparisons` CASCADE, so it goes with the comparisons), `eval_runs` (031), `spec_spine` (035), `rating_cache` (out of band, `CONTEXT_DATABASE_API.md:66-78`), `bahrain_approved_drugs` (out of band), and `comparisons_cache` (dropped at 032:54). The `vw_cohort_*` views (013) store nothing. **The 038 consent columns are on `users`.** **`search_logs.is_synthetic` (042:132-133) is a classification flag, not a user reference.** Shares are rows of `comparisons` (`share_token`), so deleting the comparisons makes every shared link 404.

`grep -rhoE 'table\("[a-z_]+"\)' app/ scripts/` lists every table the code touches. Each one is in the two lists above, plus `pain_workflow_events`, which no code writes.

### 2c. The delete path in code, and Redis

- **Route**, `auth_routes.py:1165-1177` (`delete_account`): `@router.delete("/account")`, `@limiter.limit("1/minute")`, `Depends(get_current_user)`. On any exception it runs `logger.error(f"Account deletion failed for user {current_user['id']}: {e}")` and raises `HTTPException(500, "Account deletion failed")`.
- **`auth_service.delete_user_account`** (`:980-988`): cascade, then `admin.auth.admin.delete_user`. It does no logging of its own. A cascade exception propagates before the auth delete runs.
- **`database_service.delete_user_data_cascade`** (`:392-401`): `client.rpc("delete_user_cascade", {"target_user_id": user_id}).execute()`. On error it runs `logger.error(f"Error in cascade delete for user {user_id}: {e}")` and re-raises.
- **Finding F-LOG (measured).** On the pinned postgrest 2.31.0, `str(APIError)` includes `details`:

  ```
  $ <venv python> -c "from postgrest.exceptions import APIError; e=APIError({'message':'null value in column ...','code':'23502','hint':None,'details':'Failing row contains (..., SENTINEL_EMAIL_VALUE, ...).'}); print('str has details:', 'SENTINEL_EMAIL_VALUE' in f'{e}')"
  str has details: True
  ```
  (`postgrest/exceptions.py:37-51`: `__init__` stores `details` and passes `str(self)` to `Exception`.)

  For a NOT NULL (23502) or CHECK (23514) violation in the tombstone UPDATE, PostgreSQL's DETAIL is "Failing row contains (...)", which is the user's whole row. Inside a SECURITY DEFINER function the definer can read every column, so the detail is not redacted. **Both log lines would then write the email, name and demographics to Railway logs.** Sentry's default LoggingIntegration would carry them too: `sentry_service.py:299-329` passes no `default_integrations=False`. That last point is reasoned, not measured at runtime.
- **Token.** `verify_token` (`auth_service.py:543-582`) checks the Redis blacklist, then calls `client.auth.get_user(access_token)` on every request. Once the auth user is deleted, the bearer fails on the next request. That is GoTrue platform behaviour, not measured here. Deletion writes no blacklist entry, and none is needed.
- **Per-user Redis keys** (`grep -rn -E '(cache_key|key)\s*=\s*f"[^"]*\{[^}]*(user|uid)' app/`):

| key | writer | TTL | content | removed on deletion today? |
|---|---|---|---|---|
| `home:savings:{user_id}` | `home_routes.py:205` | 6 h (`:121`) | savings and decision count from comparisons | no |
| `home:smart_pick:{user_id}` | `home_routes.py:719` | 5 min (`:122`) | a pick built from the user's comparisons and preferences | no |
| `profile_recent:{user_id}` | `profile_routes.py:176` | 5 min (`:48`) | recent decisions (queries, product names) | no |
| `monthly_stats:{user_id}` | `profile_routes.py:297` | 5 min (`:49`) | per-month stats | no |
| `priorities_weighted:{user_id}` | `profile_routes.py:466` | 5 min (`:50`) | priorities from preferences and behavior_profile | no |
| `usage:daily:{uid}:{day}`, `usage:monthly:{uid}:{month}` | `usage_service.py:150-174` | 24 h / ~32 d (`:698-702`) | integer counters | no (KEEP, R4.3) |
| `usage:{uid}:{day}` (legacy) | `cache_service.py:812-824` | 24 h | integer | no (KEEP) |
| `anon:{device_fingerprint}` counters | `usage_service.py:61` | same windows | integer, keyed by device, not user | no (KEEP) |
| `failed_login:{sha256(email)[:16]}` | `auth_service.py:1153-1156` (`_login_attempt_key`) | 900 s (`:45`) | integer | no (KEEP) |
| `revoked:{sha256(token)}` | `auth_service.py:746-752` | 3600 s | "1" | no (KEEP) |
| slowapi rate-limit counters | `rate_limiter.py:52, 149-185` | window | keyed by IP | no (KEEP) |

The history-delete route already removes three of these keys (`history_routes.py:198-210`). Account deletion removes none of them. **Finding F-CACHE:** for up to 6 h after a deletion, Redis still holds content derived from the erased rows.

- **The `account_deleted` audit event** is listed in the `log_audit_event` docstring (`audit_service.py:24-27`), but no caller exists. All 8 call sites were checked; none logs a deletion.
- **Free-quota anti-abuse.** 025 clears `device_fingerprint_hash`. `_inherit_device_counter` (`auth_routes.py:488-526`) and `_referrer_device_lifetime_count` (`referral_service.py:772-806`) read sibling rows by fingerprint. Deleting the account and signing up again on the same device therefore resets the free counter. This is already true today, and 043 does not change it (Q8).

### 2d. The mobile client

`SmartCompareApp/src/screens/EditProfileScreen.tsx:125-155` (`handleDeleteAccount`) does, in order: `api.delete('/api/v1/auth/account')`, then `clearAiConsent(user?.id)`, then `clearSession()`. `clearSession` (`src/services/authService.ts:626-637`) deletes SecureStore `TOKEN_STORAGE_KEY` and `REFRESH_TOKEN_KEY`, and AsyncStorage `@qaren_user`.

The AsyncStorage key census (`grep -rhoE "'@(qaren|smartcompare)[^']*'" src/`) found: `@qaren_user`, `@qaren_ai_consent_<id>`, `@qaren_recent_searches`, `@qaren_onboarding_draft_v1`, `@qaren_language`, `@qaren_rtl_bootstrapped`, `@qaren_push_token_registered`, `@qaren_push_preprompt_answered` and `@qaren_free_comparisons_used`, plus the legacy token keys that `purgeLegacyAuthStorage` removes.

**`@qaren_recent_searches` (`HomeScreen.tsx:93, 300-321`), the user's last search queries, is NOT cleared on deletion or logout. It stays on the device and shows to the next account.** The onboarding draft is cleared when onboarding completes (`onboardingDraft.ts:147-149`, `authService.ts:345-346`). Client changes are out of scope, so this is open question Q5.

### 2e. What the existing tests pin

(`grep -rln -E "delete_user_cascade|delete_account|delete_user_data_cascade|delete_user_account" tests/`)

- `tests/test_delete_user_cascade.py`: string pins on **025 and rollback/025 only**, including "users row is updated not deleted" and "does not delete admin_audit_log". These tests do not look at later migrations. They stay unchanged and green.
- `tests/test_account_deletion.py`: the route needs auth, returns 200 with "deleted" on success, returns 500 on failure, and `delete_user_account` is called with the id. Everything else is mocked.
- `tests/test_security_regression.py:581-585` pins `'rpc("delete_user_cascade"' in database_service.py`.
- `tests/test_migration_037_security_definer_grants.py:476-525` checks the forward path for **EXACTLY ONE** `GRANT EXECUTE ON FUNCTION public.delete_user_cascade(uuid) TO service_role` (assertion `len(hits) == 1`). It forbids any grant to PUBLIC, anon or authenticated in any file, and requires every forward REVOKE on the function to name `PUBLIC, anon, authenticated` (:528-567). Its census includes the rollback files (:313-323).
- `tests/test_retro_w1_2d.py:323-357` (`_order_aware_offenders`): for every SECURITY DEFINER signature, the **last** forward file that `CREATE [OR REPLACE]`s it must be followed by a top-level REVOKE naming `public, anon, authenticated`. CREATE OR REPLACE counts as a (re)definition (`tests/_retro_r_mig_sql.py:118-121, 166-173`).
- `tests/test_sqlfluff_config.py:198-215` runs `python -m sqlfluff lint migrations/`. sqlfluff 4.3.0 is in the venv, and `.sqlfluff` enforces CP01 upper-case keywords and LT05 ≤ 180.
- **What static tests cannot see:** the live DDL of the four out-of-band tables, live constraints and triggers, live FKs, live ACLs, and whether the function body executes. These are covered by PRECHECK, the guard and assert blocks, and POSTCHECK.

### 2f. What CREATE OR REPLACE FUNCTION does

The local PostgreSQL 18 documentation (`C:/Program Files/PostgreSQL/18/doc/src/sgml/html/sql-createfunction.html`, the CREATE OR REPLACE notes and "Writing SECURITY DEFINER Functions Safely") says, in paraphrase: replacing an existing function keeps its "ownership and permissions"; every other property takes the value the new command states or implies; and a newly created function grants EXECUTE to PUBLIC by default.

Consequences:

- The 037 ACL survives the replacement. That ACL was measured live on 2026-09-24 and is recorded in `CLAUDE.md:577` as "`{postgres,service_role}` only" (abbreviated; the raw `proacl` text is expected to be `{postgres=X/postgres,service_role=X/postgres}`).
- **SECURITY DEFINER and `SET search_path` must be restated.** If either is omitted, it resets to SECURITY INVOKER and no `proconfig`.

The session-67 retro adversary measured on a throwaway PG18 cluster that "rollback/025 (CREATE OR REPLACE) keeps the tightened ACL" (`docs/investigations/2026-09-24-session-67-state/retro_adversary_results.json:269`). Not verified for this unit without a live database: the live owner, the stored `proconfig` text (`search_path=public` is expected), and whether the live body is 025. The normalised md5 (`md5_norm`, R8.1) of the 025 source between the `$function$` tags is **`76e8e2f65e9d5cb3b29c5ab57ab9bf61`**; the raw LF md5 is `af5b0db12048a1c302330e47d4ddb602`. PRECHECK §6 prints the live `md5_norm`.

---

## 3. Requirements

### R1. The forward migration: `migrations/043_delete_user_cascade_full_erasure.sql`

**Number.** 043 is the next free number: 042 is the highest file, `039` is reserved (`CLAUDE.md:86`; `tests/test_migration_042_search_logs_is_synthetic.py:108`), and no sibling worktree claims 043 (`grep` over `sc-s71-u13`, `sc-s70-oai` and the session-71 docs).

**Content.** The file is exactly the following, LF endings, ASCII only. It lints clean on sqlfluff 4.3.0 with the repo `.sqlfluff` ("All Finished!", rc 0, prototype at `proto/migrations/`). A lower-case-keyword mutant of it fails CP01, rc 1, so the linter was really running.

```sql
-- 043_delete_user_cascade_full_erasure.sql
-- S71 U8b: account deletion erases every user-owned row and every personal
-- column of the kept users row (App Store guideline 5.1.1(v)).
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION. Ahmed applies it in the Supabase
-- SQL editor from the one-paste files in
-- docs/investigations/2026-10-03-session-71-state/ (PRECHECK, ONE_PASTE,
-- POSTCHECK). Apply order: 037 must already be applied (it was, 2026-09-24);
-- 039 stays reserved; 035/036 are not needed.
--
-- WHAT 025 MISSED (measured at eb86075e):
--   * four tables created with user_id FKs that cascade from public.users,
--     which never fire because the function keeps the users row:
--     deep_review_credits and re_engagement_events (014),
--     pain_workflow_events (028), user_preference_history (029);
--   * every users column except preferences, behavior_profile,
--     preferences_completed, expo_push_token and device_fingerprint_hash:
--     email, display_name, demographics (013), referral code (014), push
--     opt-in (015), attribution (019), consent (038) and the rest.
--   * 025's reason for keeping the row ("admin_audit_log foreign keys") is
--     false in the files: 011 creates admin_audit_log.user_id with no FK.
--
-- WHAT THIS KEEPS: users.id and users.created_at (a de-identified stub), and
-- admin_audit_log rows with their ip_address removed.
--
-- SAFETY: the guard block aborts the whole file if a column this function
-- writes is missing live or is NOT NULL where the function writes NULL; the
-- assert block aborts it if SECURITY DEFINER, the pinned search_path or the
-- 037 ACL did not survive. CREATE OR REPLACE keeps the owner and the ACL
-- (PostgreSQL 18 docs, CREATE FUNCTION), so the 037 GRANT is not restated
-- here (tests/test_migration_037_security_definer_grants.py pins exactly one);
-- the REVOKE is restated because the order-aware census in
-- tests/test_retro_w1_2d.py requires one after every (re)definition.
--
-- BODY ORDER: 025's seven DELETEs (same order: user_events before
-- comparisons), then the four U8b DELETEs, then the admin_audit_log IP
-- UPDATE, then the users UPDATE. No comment lives inside a dollar-quoted
-- body: the SQL editor paste joins lines, where a -- would swallow code.
--
-- Rollback: migrations/rollback/043_delete_user_cascade_full_erasure.sql
-- restores the 025 body. It cannot restore erased data.

BEGIN;

DO $guard$
DECLARE
  missing text;
  not_nullable text;
BEGIN
  SELECT string_agg(t.tbl, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'public.users', 'public.user_events', 'public.comparison_feedback',
      'public.comparisons', 'public.search_logs', 'public.user_usage',
      'public.referral_invites', 'public.referral_redemptions',
      'public.deep_review_credits', 'public.re_engagement_events',
      'public.pain_workflow_events', 'public.user_preference_history',
      'public.admin_audit_log'
    ]) AS t (tbl)
   WHERE to_regclass(t.tbl) IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '043 guard: missing table(s): %', missing;
  END IF;

  SELECT string_agg(c.col, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'email', 'display_name', 'auth_provider', 'subscription_tier',
      'subscription_expires_at', 'updated_at', 'preferences',
      'preferences_completed', 'behavior_profile', 'lifetime_comparisons_used',
      'demographics_profile', 'demographics_dismissed_count',
      'demographics_dismissed_at', 'referral_code',
      'referral_bonus_comparisons_this_month', 'referral_bonus_reset_at',
      'expo_push_token', 'notifications_enabled', 'last_comparison_at',
      'attribution_source', 'device_fingerprint_hash',
      'lifetime_invites_consumed', 'terms_accepted_at', 'terms_version',
      'age_attested_at'
    ]) AS c (col)
   WHERE NOT EXISTS (
     SELECT 1
       FROM information_schema.columns AS i
      WHERE i.table_schema = 'public'
        AND i.table_name = 'users'
        AND i.column_name = c.col
   );
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '043 guard: public.users lacks column(s): %', missing;
  END IF;

  SELECT string_agg(i.column_name, ', ')
    INTO not_nullable
    FROM information_schema.columns AS i
   WHERE i.table_schema = 'public'
     AND i.table_name = 'users'
     AND i.is_nullable = 'NO'
     AND i.column_name = ANY (ARRAY[
       'email', 'display_name', 'auth_provider', 'subscription_expires_at',
       'preferences', 'behavior_profile', 'demographics_profile',
       'demographics_dismissed_at', 'referral_code', 'referral_bonus_reset_at',
       'expo_push_token', 'last_comparison_at', 'attribution_source',
       'device_fingerprint_hash', 'terms_accepted_at', 'terms_version',
       'age_attested_at'
     ]);
  IF not_nullable IS NOT NULL THEN
    RAISE EXCEPTION '043 guard: NOT NULL live, cannot erase to NULL: %', not_nullable;
  END IF;

  IF NOT EXISTS (
    SELECT 1
      FROM information_schema.columns AS i
     WHERE i.table_schema = 'public'
       AND i.table_name = 'admin_audit_log'
       AND i.column_name = 'ip_address'
       AND i.is_nullable = 'YES'
  ) THEN
    RAISE EXCEPTION '043 guard: admin_audit_log.ip_address missing or NOT NULL';
  END IF;
END
$guard$;

CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
BEGIN
  DELETE FROM public.user_events WHERE user_id = target_user_id;
  DELETE FROM public.comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM public.comparisons WHERE user_id = target_user_id;
  DELETE FROM public.search_logs WHERE user_id = target_user_id;
  DELETE FROM public.user_usage WHERE user_id = target_user_id;
  DELETE FROM public.referral_invites
   WHERE referrer_user_id = target_user_id
      OR redeemed_by_user_id = target_user_id;
  DELETE FROM public.referral_redemptions
   WHERE referrer_user_id = target_user_id
      OR invitee_user_id = target_user_id;

  DELETE FROM public.deep_review_credits WHERE user_id = target_user_id;
  DELETE FROM public.re_engagement_events WHERE user_id = target_user_id;
  DELETE FROM public.pain_workflow_events WHERE user_id = target_user_id;
  DELETE FROM public.user_preference_history WHERE user_id = target_user_id;

  UPDATE public.admin_audit_log
     SET ip_address = NULL
   WHERE user_id = target_user_id;

  UPDATE public.users
     SET email = NULL,
         display_name = NULL,
         auth_provider = NULL,
         subscription_tier = 'free',
         subscription_expires_at = NULL,
         updated_at = now(),
         preferences = NULL,
         preferences_completed = false,
         behavior_profile = NULL,
         lifetime_comparisons_used = 0,
         demographics_profile = NULL,
         demographics_dismissed_count = 0,
         demographics_dismissed_at = NULL,
         referral_code = NULL,
         referral_bonus_comparisons_this_month = 0,
         referral_bonus_reset_at = NULL,
         expo_push_token = NULL,
         notifications_enabled = false,
         last_comparison_at = NULL,
         attribution_source = NULL,
         device_fingerprint_hash = NULL,
         lifetime_invites_consumed = 0,
         terms_accepted_at = NULL,
         terms_version = NULL,
         age_attested_at = NULL
   WHERE id = target_user_id;
END;
$function$;

REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid)
FROM PUBLIC, anon, authenticated;

DO $assert$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_proc AS p
     WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure
       AND p.prosecdef
       AND p.proconfig = ARRAY['search_path=public']
  ) THEN
    RAISE EXCEPTION '043 assert: SECURITY DEFINER or search_path=public lost';
  END IF;
  IF NOT has_function_privilege(
    'service_role', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION '043 assert: service_role cannot EXECUTE (apply 037 first)';
  END IF;
  IF has_function_privilege(
    'anon', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) OR has_function_privilege(
    'authenticated', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION '043 assert: anon or authenticated can EXECUTE';
  END IF;
END
$assert$;

COMMIT;
```

The prototype's sha256 is `7eb06a20e96f3e4140a28d3b3e5b4f263c8470b2665f1a299d9648b3fb666973`, and the normalised md5 of its `$function$` body is `fa3e7996ea28f5025b40d6e9aa23e855` (`md5_norm`, defined in R8.1). The GREEN agent recomputes both on the committed bytes.

The binding rules this content follows:

- **R1.1 Shape.** The file is one transaction: exactly one `BEGIN;` first and one `COMMIT;` last. In order it holds: the guard `DO $guard$`, then `CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'`, then the top-level `REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid) FROM PUBLIC, anon, authenticated;`, then the assert `DO $assert$`, then `COMMIT;`.
- **R1.2 No GRANT** anywhere in executable SQL. The 037 test pins exactly one forward grant, and the ACL survives CREATE OR REPLACE (§2f). The assert block proves the ACL instead of re-granting (Q7).
- **R1.3 Schema-qualified relations.** Every relation in the function body is written `public.<table>`. With qualified names, a `pg_temp` table cannot mask a target even though `search_path` is `'public'` only (PG18 docs, "Writing SECURITY DEFINER Functions Safely").
- **R1.4 Order and semantics.** 025's seven DELETEs keep their order and their WHERE clauses: both roles on `referral_invites` and `referral_redemptions`. The four U8b DELETEs follow. Then the `admin_audit_log` UPDATE (ruling Q1), then the `users` UPDATE.
- **R1.5 Guard arrays.** The guard's column-exists array is exactly the set of `users` columns the function assigns. The guard's NOT NULL array is exactly the subset assigned `NULL`. The guard's table array is exactly the set of tables the body touches, plus `public.users`.
- **R1.6 Idempotent.** Re-running the file re-creates the same function, re-revokes and re-asserts. Calling the function twice for the same id is a no-op the second time.
- **R1.7** LF, ASCII only, sqlfluff-clean.
- **R1.8 No `--` inside any dollar-quoted body** (`$guard$`, `$function$`, `$assert$`). The 042 apply joined each file's statements onto ONE line in the SQL editor, with comment lines dropped (`docs/investigations/2026-09-29-session-69-state/APPLY_OUTPUTS.md:3`). Inside a joined body, a `--` comment would swallow the code after it. Comments live in the file header only.

### R2. The rollback: `migrations/rollback/043_delete_user_cascade_full_erasure.sql`

The rollback holds a header comment, then `BEGIN;`, then the statement **byte for byte** from `migrations/025_delete_user_cascade_completeness.sql` lines 28-70 (`CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)` … `$function$;`, which includes the 025 em dash at 025:56, so the file is UTF-8), then `REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid)` / `FROM PUBLIC, anon, authenticated;`, then `COMMIT;`. It has no GRANT.

The header must say:

- the statement is 025:28-70 verbatim;
- CREATE OR REPLACE keeps the 037 ACL;
- **"this restores the FUNCTION only. Rows and columns 043 erased stay erased, and admin_audit_log.ip_address values it cleared do not come back"**.

Paste note: the rollback carries 025's whole-line comments inside its `$function$` body. Paste it as-is, or drop the whole-line comments first, but never join its lines while a `--` remains.

The prototype is at `proto/migrations/rollback/043_delete_user_cascade_full_erasure.sql`, built with Python from `git show HEAD:migrations/025_...` lines 28-70. It is sqlfluff-clean.

### R3. The tombstone map (what the `users` UPDATE writes)

The rule: NULL wherever the column allows it. A NOT NULL column gets its documented default value instead. Counters get 0 because a reader does `user_info.get("lifetime_comparisons_used", 0)`, which yields `None` for a NULL (`usage_service.py:354`). `subscription_tier` gets `'free'`, the value the app inserts and therefore one any live CHECK accepts.

| column | value | why |
|---|---|---|
| email, display_name, auth_provider | NULL | direct identifiers (`auth_provider` names the identity provider) |
| subscription_tier | `'free'` | default plan; avoids a NULL tier for readers in the auth-failure window |
| subscription_expires_at | NULL | |
| updated_at | `now()` | records the erasure time on the stub |
| preferences, behavior_profile | NULL | as in 025 |
| preferences_completed | `false` | as in 025 |
| lifetime_comparisons_used, demographics_dismissed_count | `0` | counters |
| demographics_profile, demographics_dismissed_at | NULL | |
| referral_code | NULL | UNIQUE allows many NULLs. This also stops `resolve_referral_code` (014:97-101) from resolving a deleted user's code, and stops `invite_code` at register from attaching new invitees to a deleted account |
| referral_bonus_comparisons_this_month, lifetime_invites_consumed | `0` | NOT NULL counters (014:12, 023:5) |
| referral_bonus_reset_at, expo_push_token, last_comparison_at, attribution_source, device_fingerprint_hash | NULL | 019's CHECK admits NULL |
| notifications_enabled | `false` | NOT NULL (015:18-19). The tombstone must never be pushed to (the re-engagement cron filters on this column) |
| terms_accepted_at, terms_version, age_attested_at | NULL | consent evidence cannot be tied to a person once the identity is gone (Q3) |

**Fallback if PRECHECK shows a constraint that forbids a value.** STOP and rule. The pre-agreed tombstones are:

- `email`, if NOT NULL: `'deleted-' || target_user_id || '@deleted.invalid'` (RFC 2606 `.invalid`; unique per user, so it also satisfies a UNIQUE constraint);
- `preferences` or `behavior_profile`, if NOT NULL: `'{}'::jsonb`;
- any other NOT NULL text column: `''`, unless it is UNIQUE.

The guard array, the fence's `EXPECTED_TOMBSTONE` and the one-paste file change together.

### R4. The KEEP allowlists (each entry with its justification)

- **R4.1 `users` columns kept:**
  - `id`: "Primary key of the de-identified stub: a random v4 uuid that identifies no person once every other column is erased; target of the FKs in 011/014/028/029, and the key the auth-failure retry needs."
  - `created_at`: "Account creation date kept on the stub for cohort and retention counts (vw_cohort_match_rate, 013:23-33); on its own it identifies no person."
- **R4.2 Table columns kept:** `("admin_audit_log", "user_id")`: "Security events (login_success, invite_code_redeemed, referral abuse flags) are kept for fraud and abuse forensics; the key is the stub's random uuid, and 043 sets ip_address to NULL on these rows." This is ruling-dependent (Q1). If the ruling is "retain IP", drop the `admin_audit_log` UPDATE from R1 and add `("admin_audit_log", "ip_address")` here with the ruling's justification.
- **R4.3 Redis keys kept (documented here, not fenced):** `usage:*` and `anon:*` counters (integers, TTL ≤ 32 d, needed for quota symmetry); `failed_login:*` (900 s, hashed email); `revoked:*` (1 h); slowapi counters (IP, one window). None holds content.

### R5. The static fence: `tests/test_migration_043_delete_user_cascade.py`

The fence imports `code_only`, `dollar_bodies`, `strip_line_comments`, `norm`, `read`, `forward_sql_files`, `top_level_revokes`, `create_or_drop_events`, `GRANT_FN` and `install_network_guard` from `tests/_retro_r_mig_sql.py`, and applies the autouse zero-network fixture the same way `test_retro_w1_2d.py:82-86` (`_zero_network`) does.

**Allowlist format.** Module-level literals, each value a justification string of at least 40 characters:

```python
USERS_BASELINE_COLUMNS: dict[str, str]          # out-of-band users DDL -> source (CONTEXT_DATABASE_API.md:83-92 or the 2026-06-08 audit)
    # = id, email, display_name, auth_provider, subscription_tier, subscription_expires_at,
    #   created_at, updated_at, preferences, preferences_completed, behavior_profile
OUT_OF_BAND_USER_TABLES: dict[str, tuple[str, ...]]  # {"comparisons": ("user_id",), "comparison_feedback": ("user_id",), "user_events": ("user_id",)}
KEEP_USERS_COLUMNS: dict[str, str]              # R4.1
KEEP_TABLE_COLUMNS: dict[tuple[str, str], str]  # R4.2
EXPECTED_TOMBSTONE: dict[str, str]              # R3, normalised lower-case value text: "null", "'free'", "now()", "false", "0"
```

**Fence rules** (prototype `fence_proto.py`, measured):

- **F1.** The users columns are the keys of `USERS_BASELINE_COLUMNS`, plus every `ADD [COLUMN] [IF NOT EXISTS] <name>` inside every `ALTER TABLE [ONLY] [public.]users … ;` of every forward migration, after `code_only` (comments stripped and dollar bodies blanked, so DDL quoted inside a DO block never counts). `DROP COLUMN` and `RENAME COLUMN` are applied in file order.
- **F2.** The user-referencing tables are `OUT_OF_BAND_USER_TABLES`, plus every `CREATE TABLE` (other than users) with a column that `REFERENCES [public.|auth.]users(` or whose name matches `((^|_)user_id$|email|fingerprint|push_token|ip_address|user_agent|session_id)`, plus the same for `ALTER TABLE <t> ADD COLUMN`.
- **F3.** The cascade body is the `$function$` body of the **last** forward file, in `sorted(MIGRATIONS_DIR.glob("*.sql"))` order (the order the 037 and W1-2d tests use), that `CREATE [OR REPLACE] FUNCTION [public.]delete_user_cascade(`. Comments are stripped; the body is the first dollar span after the CREATE match.
- **F4.** Every F1 column is either assigned by the body's `UPDATE [public.]users SET … WHERE id = target_user_id`, or listed in `KEEP_USERS_COLUMNS`, never both. The assignment map must equal `EXPECTED_TOMBSTONE`.
- **F5.** For every F2 table: if the body has `DELETE FROM [public.]<t>`, every column of `<t>` matching `(^|_)user_id$` must appear as `<col> = target_user_id` in that DELETE's WHERE. Otherwise every user-ref column of `<t>` must be `SET <col> = NULL` by an `UPDATE [public.]<t> … WHERE <a user_id column> = target_user_id`, or be listed in `KEEP_TABLE_COLUMNS`.
- **F6.** No KEEP entry is stale: the users column must exist in F1, and the table and column must exist in F2. No KEEP entry is also erased. Every justification is at least 40 characters.

The prototype was measured against the base migrations and the prototype 043 (`fence_base.txt`, `fence_head.txt`):

- **base:** "cascade defined last in: 025_delete_user_cascade_completeness.sql", **GAPS=25**. That is 20 `users.<col> neither cleared nor KEEP-listed` lines (email, display_name, auth_provider, demographics ×3, attribution_source, consent ×3, referral ×3, notifications_enabled, last_comparison_at, lifetime ×2, subscription ×2, updated_at), plus `admin_audit_log.ip_address`, `deep_review_credits.user_id`, `pain_workflow_events.user_id`, `re_engagement_events.user_id` and `user_preference_history.user_id`.
- **head:** "cascade defined last in: 043_…", users columns (27), **GAPS=0**.

### R6. Backend B1: purge the per-user caches (finding F-CACHE)

In `app/services/auth_service.py`:

- Line 26 becomes `from app.services.cache_service import delete_cached, redis_client, _redis_offload_enabled`.
- Add, directly above `delete_user_account`:

```python
# U8b -- per-user Redis keys whose values are derived from rows the cascade
# erases. Writers: home_routes.py:205 (6 h), :719 (5 min); profile_routes.py
# :176, :297, :466 (5 min). Usage/anon/lockout/revocation counters are kept
# (integers, short TTLs) -- see the U8b spec R4.3.
DELETED_USER_CACHE_KEY_TEMPLATES: Tuple[str, ...] = (
    "home:savings:{user_id}",
    "home:smart_pick:{user_id}",
    "profile_recent:{user_id}",
    "monthly_stats:{user_id}",
    "priorities_weighted:{user_id}",
)


async def _purge_deleted_user_caches(user_id: str) -> None:
    """U8b -- drop the per-user caches of an erased account. Fail-soft and
    never raises: a Redis outage must not block a deletion (every key expires
    within 6 h anyway). ENABLE_ASYNC_REDIS_OFFLOAD dispatches off-loop."""
    for template in DELETED_USER_CACHE_KEY_TEMPLATES:
        key = template.format(user_id=user_id)
        try:
            if _redis_offload_enabled():
                await asyncio.to_thread(delete_cached, key)
            else:
                delete_cached(key)
        except Exception as exc:  # noqa: BLE001 -- delete_cached already swallows
            logger.warning("[AUTH] cache purge failed: %s", type(exc).__name__)
```

- `delete_user_account` becomes cascade, then `await _purge_deleted_user_caches(user_id)`, then auth delete, returning True. Its docstring states the order. If the cascade raises, nothing else runs. If the auth delete raises, the exception propagates as today.

### R7. Backend B2: no exception text in the deletion log lines (finding F-LOG)

- `database_service.delete_user_data_cascade` except arm (`:398-401`):

```python
    except Exception as e:
        # U8b: never format the exception. A PostgREST APIError's str() carries
        # `details`, which for a constraint violation is "Failing row contains
        # (...)" -- the user's whole row (email, name, demographics).
        logger.error(
            "Error in cascade delete for user %s: %s (sqlstate=%s)",
            user_id, type(e).__name__, getattr(e, "code", None),
        )
        raise
```

- `auth_routes.delete_account` except arm (`:1175-1177`): `logger.error("Account deletion failed for user %s: %s", current_user["id"], type(e).__name__)`. The `HTTPException(500, "Account deletion failed")` is unchanged.
- The decorator, `@limiter.limit("1/minute")`, `Depends(get_current_user)`, the success body and `rpc("delete_user_cascade"` (pinned by `test_security_regression.py:585`) stay byte-identical. No `logger.exception` is added.

### R8. The files Ahmed applies (in `docs/investigations/2026-10-03-session-71-state/`, template: the 042 files)

The Supabase SQL editor shows one result grid per run. Each check file is therefore ONE `SELECT` that returns `(sec, kind, item, detail)` rows. No row prints an email, a name or a token.

**R8.1 `APPLY_043_1_PRECHECK.sql`** (read-only, run alone, paste the whole grid back):

```sql
-- 043 PRE-CHECK (U8b). Read-only. ONE run, BEFORE the one-paste. Paste the WHOLE grid back.
-- No row prints an email, a name or a token.
SELECT x.sec, x.kind, x.item, x.detail
FROM (
    SELECT 1 AS sec, 'users_column' AS kind,
           lpad(c.ordinal_position::text, 2, '0') || ' ' || c.column_name::text AS item,
           c.data_type::text || ' nullable=' || c.is_nullable::text
           || ' default=' || coalesce(c.column_default::text, '-') AS detail
      FROM information_schema.columns AS c
     WHERE c.table_schema = 'public' AND c.table_name = 'users'
    UNION ALL
    SELECT 2, 'users_constraint', con.conname::text,
           con.contype::text || ' ' || pg_get_constraintdef(con.oid)
      FROM pg_constraint AS con
     WHERE con.conrelid = 'public.users'::regclass
    UNION ALL
    SELECT 3, 'users_index', i.indexname::text, i.indexdef
      FROM pg_indexes AS i
     WHERE i.schemaname = 'public' AND i.tablename = 'users'
    UNION ALL
    SELECT 4, 'fk_into_users_auth_or_comparisons',
           con.conrelid::regclass::text || ' ' || con.conname::text,
           'on_delete=' || CASE con.confdeltype
               WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT' WHEN 'c' THEN 'CASCADE'
               WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' END
           || ' ' || pg_get_constraintdef(con.oid)
      FROM pg_constraint AS con
      JOIN pg_class AS rel ON rel.oid = con.conrelid
      JOIN pg_namespace AS ns ON ns.oid = rel.relnamespace
     WHERE con.contype = 'f'
       AND ns.nspname = 'public'
       AND con.confrelid IN ('public.users'::regclass, 'auth.users'::regclass,
                             'public.comparisons'::regclass)
    UNION ALL
    SELECT 5, 'user_ref_column', c.table_name::text || '.' || c.column_name::text,
           c.data_type::text || ' nullable=' || c.is_nullable::text
      FROM information_schema.columns AS c
     WHERE c.table_schema = 'public'
       AND c.table_name <> 'users'
       AND c.column_name::text ~ '((^|_)user_id$|email|fingerprint|push_token|ip_address|user_agent|session_id)'
    UNION ALL
    SELECT 6, 'function', p.oid::regprocedure::text,
           'secdef=' || p.prosecdef::text
           || ' config=' || coalesce(array_to_string(p.proconfig, ','), '-')
           || ' owner=' || pg_get_userbyid(p.proowner)::text
           || ' acl=' || coalesce(p.proacl::text, 'NULL')
           || ' md5_norm=' || md5(btrim(regexp_replace(
                  regexp_replace(p.prosrc, '^\s*--.*$', '', 'gn'), '\s+', ' ', 'g')))
      FROM pg_proc AS p
     WHERE p.proname = 'delete_user_cascade'
       AND p.pronamespace = 'public'::regnamespace
    UNION ALL
    SELECT 7, 'execute_privilege', r.rolname::text,
           has_function_privilege(r.rolname, 'public.delete_user_cascade(uuid)', 'EXECUTE')::text
      FROM pg_roles AS r
     WHERE r.rolname IN ('service_role', 'anon', 'authenticated')
    UNION ALL
    SELECT 8, 'trigger', t.tgrelid::regclass::text || ' ' || t.tgname::text, pg_get_triggerdef(t.oid)
      FROM pg_trigger AS t
     WHERE NOT t.tgisinternal
       AND t.tgrelid IN ('public.users'::regclass, 'auth.users'::regclass)
    UNION ALL
    SELECT 9, 'count', 'a public.users rows', count(*)::text FROM public.users
    UNION ALL
    SELECT 9, 'count', 'b users rows with no auth.users row', count(*)::text
      FROM public.users AS u
     WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id)
    UNION ALL
    SELECT 9, 'count', 'c (b) rows still holding email, display_name or demographics', count(*)::text
      FROM public.users AS u
     WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id)
       AND (u.email IS NOT NULL OR u.display_name IS NOT NULL OR u.demographics_profile IS NOT NULL)
    UNION ALL
    SELECT 9, 'count', 'd admin_audit_log rows with ip_address whose user has no auth.users row',
           count(*)::text
      FROM public.admin_audit_log AS l
     WHERE l.user_id IS NOT NULL AND l.ip_address IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = l.user_id)
    UNION ALL
    SELECT 9, 'count', 'e rows in 014/028/029 tables whose user has no auth.users row', (
          (SELECT count(*) FROM public.deep_review_credits AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
        + (SELECT count(*) FROM public.re_engagement_events AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
        + (SELECT count(*) FROM public.pain_workflow_events AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
        + (SELECT count(*) FROM public.user_preference_history AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
      )::text
) AS x
ORDER BY x.sec, x.item;
```

**Expected PRECHECK results, with STOP rules.** Any STOP goes back to the orchestrator, and nothing is applied until it is resolved.

- **§1:** 27 rows: `id`, `created_at` and the 25 R3 columns. **STOP** on a missing column, on an extra column (it must then be classified in the fence baseline and the cascade), and on `nullable=NO` for a NULL target.
- **§2:** expect `users_pkey`, `users_referral_code_key` (014), `users_preferences_budget_check` (024), the attribution CHECK (019), and possibly an FK `FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE`, which is branch A. **STOP** on any other CHECK or UNIQUE that a value in R3 violates.
- **§4:** decides branch A or B, and shows each FK into `comparisons`. **STOP** on any FK into `public.comparisons` from another user's row with `NO ACTION` or `RESTRICT` that 025 does not already handle, such as `user_events.comparison_id`.
- **§6:** expect `secdef=true config=search_path=public owner=postgres acl={postgres=X/postgres,service_role=X/postgres} md5_norm=76e8e2f65e9d5cb3b29c5ab57ab9bf61`. **STOP** if the md5 differs: the live body is not 025, so paste `pg_get_functiondef` back.
- **§7:** service_role true, anon false, authenticated false.
- **§8:** any trigger is reviewed before applying.
- **§9:** recorded. If `c > 0` or `d > 0`, Q2 decides the backfill.

**`md5_norm` (used by PRECHECK §6 and POSTCHECK §2):** whole-line `--` comments are dropped, every whitespace run is collapsed to one space, and the ends are trimmed. In SQL: `md5(btrim(regexp_replace(regexp_replace(prosrc, '^\s*--.*$', '', 'gn'), '\s+', ' ', 'g')))`, where the `n` flag makes `^`, `$` and `.` line-bounded. In Python: `hashlib.md5(' '.join(' '.join(l for l in body.splitlines() if not l.strip().startswith('--')).split()).encode()).hexdigest()`. The value is the same whether the editor received the file as-is or joined onto one line with the comments dropped (the 042 practice).

**R8.2 `APPLY_043_2_ONE_PASTE.sql`.** The file is a header (`-- 043 ONE-PASTE APPLY (Supabase SQL editor: ONE paste, ONE run = ONE transaction)`; "run 1_PRECHECK first and resolve every STOP"; "a guard/assert RAISE aborts everything — that is the safety, not a failure to work around"; "assembled from migrations/043_delete_user_cascade_full_erasure.sql, byte-for-byte body"), followed by the migration's text from `BEGIN;` through `COMMIT;`, **byte-identical** after LF normalisation. Success looks like "Success. No rows returned".

**R8.3 `APPLY_043_3_POSTCHECK.sql`** (run alone after the apply):

```sql
-- 043 POST-CHECK (U8b). ONE run, AFTER the one-paste. Paste the WHOLE grid back.
-- The dry run calls the function with the NIL uuid: no account has it (Supabase mints v4 uuids),
-- so every statement runs, every table and column resolves, and zero rows change.
WITH dry AS (
    SELECT public.delete_user_cascade('00000000-0000-0000-0000-000000000000'::uuid) AS r
)
SELECT x.sec, x.kind, x.item, x.detail
FROM (
    SELECT 1 AS sec, 'dry_run' AS kind, 'delete_user_cascade(nil uuid)' AS item, 'ok' AS detail
      FROM dry
    UNION ALL
    SELECT 2, 'function', p.oid::regprocedure::text,
           'secdef=' || p.prosecdef::text
           || ' config=' || coalesce(array_to_string(p.proconfig, ','), '-')
           || ' owner=' || pg_get_userbyid(p.proowner)::text
           || ' acl=' || coalesce(p.proacl::text, 'NULL')
           || ' md5_norm=' || md5(btrim(regexp_replace(
                  regexp_replace(p.prosrc, '^\s*--.*$', '', 'gn'), '\s+', ' ', 'g')))
      FROM pg_proc AS p
     WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure
    UNION ALL
    SELECT 3, 'execute_privilege', r.rolname::text,
           has_function_privilege(r.rolname, 'public.delete_user_cascade(uuid)', 'EXECUTE')::text
      FROM pg_roles AS r
     WHERE r.rolname IN ('service_role', 'anon', 'authenticated')
    UNION ALL
    SELECT 4, 'count', 'users rows with the nil uuid', count(*)::text
      FROM public.users
     WHERE id = '00000000-0000-0000-0000-000000000000'::uuid
) AS x
ORDER BY x.sec, x.item;
-- EXPECTED: 1 dry_run ok | 2 secdef=true config=search_path=public owner=postgres
--   acl=<unchanged from PRECHECK §6> md5_norm=<MD5_NORM_OF_043_BODY> | 3 service_role true, anon false,
--   authenticated false | 4 count 0.
```

The GREEN agent replaces `<MD5_NORM_OF_043_BODY>` with the `md5_norm` of the committed 043 `$function$` body, computed with the §6 G6 command. A test pins that the two agree. The prototype's value is `fa3e7996ea28f5025b40d6e9aa23e855`. The CTE call is VOLATILE (plpgsql default), so PostgreSQL does not inline it and evaluates it once.

**R9. (Ruling Q2) `APPLY_043_4_BACKFILL_ORPHANS.sql`**, run only if PRECHECK §9 c or d is above 0, and only after the POSTCHECK passed:

```sql
-- 043 BACKFILL (U8b, ruling Q2). Erases users rows whose auth user was deleted before 043,
-- and the IPs of their audit rows. ONE run = ONE transaction. Output = the counts AFTER.
BEGIN;
SELECT public.delete_user_cascade(u.id)
  FROM public.users AS u
 WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id);
UPDATE public.admin_audit_log AS l
   SET ip_address = NULL
 WHERE l.user_id IS NOT NULL
   AND l.ip_address IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = l.user_id);
COMMIT;
SELECT
  (SELECT count(*) FROM public.users AS u
    WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id)
      AND (u.email IS NOT NULL OR u.display_name IS NOT NULL OR u.demographics_profile IS NOT NULL)) AS c_after,
  (SELECT count(*) FROM public.admin_audit_log AS l
    WHERE l.user_id IS NOT NULL AND l.ip_address IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = l.user_id)) AS d_after;
-- EXPECTED: c_after = 0, d_after = 0.
```

---

## 4. Files

**Create:**

- `migrations/043_delete_user_cascade_full_erasure.sql` (R1)
- `migrations/rollback/043_delete_user_cascade_full_erasure.sql` (R2)
- `tests/test_migration_043_delete_user_cascade.py` (R5 and the §5 static tests)
- `tests/test_account_deletion_u8b.py` (the §5 backend tests)
- `docs/investigations/2026-10-03-session-71-state/APPLY_043_1_PRECHECK.sql`, `APPLY_043_2_ONE_PASTE.sql`, `APPLY_043_3_POSTCHECK.sql`, and, on a Q2 yes, `APPLY_043_4_BACKFILL_ORPHANS.sql`

**Modify (only the lines named):**

- `app/services/auth_service.py`: the import at line 26; a new constant and helper above `delete_user_account`; `delete_user_account` at :980-988
- `app/services/database_service.py`: the `delete_user_data_cascade` except arm at :398-401
- `app/api/auth_routes.py`: the `delete_account` except arm at :1175-1177

**MUST NOT change:**

- every other file under `migrations/`, including `025_*`, `rollback/025_*` and `037_*`
- `tests/test_delete_user_cascade.py`, `tests/test_account_deletion.py`, `tests/test_migration_037_security_definer_grants.py`, `tests/test_retro_w1_2b.py`, `tests/test_retro_w1_2d.py`, `tests/_retro_r_mig_sql.py` (import only), `tests/test_sqlfluff_config.py`
- `.sqlfluff`, `.githooks/*`, `tests/.pre_impl_failures.txt`, `requirements*.txt`
- everything under `SmartCompareApp/`
- `CLAUDE.md`, `docs/CONTEXT_*.md` (the orchestrator's docs PR records 043 as "written, unapplied")
- every other line of the three Python files, including the route decorators, the rate limit and the success message

Line endings: the backend working copy is CRLF and the index LF. Edits go through the Edit tool, and a whole-file diff in `git diff --stat` is a defect.

---

## 5. Tests

### 5.1 RED: `tests/test_migration_043_delete_user_cascade.py`

At base, the 043 file is missing, so every 043 pin fails with a missing-file assert. The two coverage tests fail by listing 025's 25 gaps, which is the defect itself.

| test | asserts | why red at base |
|---|---|---|
| `test_043_and_rollback_exist_exactly_once_and_039_stays_reserved` | `glob("043_*.sql")` = [the file] in both dirs; no `039_*` | file absent |
| `test_043_is_one_transaction` | `code_only` statements: first `begin`, last `commit`, one of each | absent |
| `test_043_redefines_the_cascade_security_definer_with_pinned_search_path` | normalised CREATE header = `create or replace function public.delete_user_cascade(target_user_id uuid) returns void language plpgsql security definer set search_path to 'public' as $function$` | absent |
| `test_043_body_schema_qualifies_every_relation` | every `delete from` and `update` target in the body starts with `public.` | absent |
| `test_043_revokes_after_the_create_and_grants_nothing` | a `top_level_revokes` entry for `(public.delete_user_cascade,(uuid,))` with roles ⊇ {public, anon, authenticated} at an offset after the CREATE event; `GRANT_FN` finds nothing in `code_only` | absent |
| `test_043_assert_block_proves_secdef_search_path_and_acl` | the `$assert$` body (after the REVOKE, before COMMIT) contains `p.prosecdef`, `proconfig = array['search_path=public']`, and `has_function_privilege(` for `'service_role'` (negated), `'anon'` and `'authenticated'` | absent |
| `test_043_guard_block_matches_what_the_function_writes` | guard exists-array == set of assigned users columns; guard NOT-NULL array == columns assigned `null`; guard table array == tables in the body ∪ {public.users}; the guard sits before the CREATE | absent |
| `test_043_tombstone_values_are_exactly_the_documented_map` | parsed `UPDATE public.users SET` map == `EXPECTED_TOMBSTONE`; `WHERE id = target_user_id` | absent |
| `test_043_keeps_025_deletes_in_order_then_the_u8b_deletes` | the ordered list of `DELETE FROM` targets == the 11 of R1.4; both role clauses on the two referral tables | absent |
| `test_043_never_deletes_users_or_audit_rows` | no `delete from public.users`, no `delete from public.admin_audit_log` | absent |
| `test_043_audit_log_ip_is_nulled_for_the_target_only` | exactly `update public.admin_audit_log set ip_address = null where user_id = target_user_id` (Q1) | absent |
| `test_rollback_043_restores_the_025_statement_byte_for_byte` | rollback CREATE…`$function$;` span (LF) == `migrations/025_…` lines 28-70 (LF) | absent |
| `test_rollback_043_is_one_transaction_revokes_and_grants_nothing` | BEGIN/COMMIT, a REVOKE naming the three roles, no GRANT | absent |
| `test_one_paste_body_is_byte_identical_to_043` | `APPLY_043_2_ONE_PASTE.sql` `BEGIN;`…`COMMIT;` span == 043's (LF) | absent |
| `test_precheck_is_read_only` | `code_only(APPLY_043_1)`, with single-quoted literals also blanked, has no `\b(insert\|update\|delete\|alter\|create\|drop\|grant\|revoke\|truncate)\b` word and no `delete_user_cascade(` call | absent |
| `test_postcheck_only_call_is_the_nil_uuid_dry_run_and_its_md5_matches_043` | exactly one `delete_user_cascade(` call, with argument `'00000000-0000-0000-0000-000000000000'::uuid`; the file contains `md5_norm=<the Python md5_norm of 043's body>`; PRECHECK and POSTCHECK both carry the identical `md5_norm` SQL expression | absent |
| `test_043_dollar_bodies_carry_no_line_comment` | no `--` between the tags of `$guard$`, `$function$` or `$assert$` (R1.8) | absent |
| **`test_cascade_erases_or_keeps_every_users_column`** (F1, F4) | no gaps | **RED: 20 users gaps from 025** |
| **`test_cascade_erases_or_keeps_every_user_referencing_table`** (F2, F5) | no gaps | **RED: ip_address and four tables** |

### 5.2 RED: `tests/test_account_deletion_u8b.py`

Use mocks only. The sentinel is `U8B_SENTINEL_ROW_DETAILS`, never an `sk-` shape. Log assertions patch the module `logger` with a MagicMock and render every call (`args[0] % args[1:]` when there are args, else `args[0]`), so they do not depend on caplog propagation.

| test | asserts | why red at base |
|---|---|---|
| `test_cascade_rpc_failure_logs_no_postgrest_details` | `database_service.get_admin_supabase_client` returns a client whose `rpc().execute()` raises `APIError({"message": "...", "code": "23502", "details": "Failing row contains (U8B_SENTINEL_ROW_DETAILS)"})`; `delete_user_data_cascade` re-raises; no rendered log text contains the sentinel; one contains `23502`; `logger.exception` is not called | base logs `f"{e}"`, which contains the details (measured, §2c) |
| `test_delete_route_failure_logs_no_exception_text` | `auth_routes.delete_user_account` raises that APIError; `DELETE /api/v1/auth/account` → 500, detail "Account deletion failed"; the sentinel is in no rendered `auth_routes.logger` call (limiter disabled as in `test_account_deletion.py:33`) | base logs `{e}` |
| `test_delete_user_account_purges_the_five_per_user_caches` (parametrised over `ENABLE_ASYNC_REDIS_OFFLOAD` unset and `true`) | `auth_service.delete_cached` is called with exactly the five keys for `user-u8b` | no purge at base |
| `test_delete_order_is_cascade_then_purge_then_auth_delete` | a recorded event list == `["cascade", "purge"×5, "auth_delete"]` | no purge |
| `test_cache_purge_failure_never_blocks_the_auth_delete` | `delete_cached` raises → `admin.auth.admin.delete_user` is still called once; returns True | no purge |
| `test_purge_key_templates_match_their_writers` | `auth_service.DELETED_USER_CACHE_KEY_TEMPLATES` has exactly the five templates, and each appears as `f"<template>"` in `app/api/home_routes.py` or `app/api/profile_routes.py` (after GREEN this is the drift pin) | the constant is absent at base (AttributeError) |

### 5.3 PIN (green at base and at head)

In `tests/test_account_deletion_u8b.py`, patch `app.services.auth_service.delete_cached` with `create=True` so these run at base:

- `test_cascade_failure_skips_purge_and_auth_delete`: the cascade raises → `delete_cached` and `admin.auth.admin.delete_user` are not called; the exception propagates
- `test_auth_delete_failure_propagates_after_the_cascade`: the auth delete raises → `delete_user_account` raises, after the cascade ran once
- `test_delete_route_keeps_rate_limit_and_auth`: a source pin on `@limiter.limit("1/minute")` directly above `async def delete_account`, and on `Depends(get_current_user)`

In the fence file, self-tests on synthetic input in the style of the W1-2d `999_mutant` approach. They pass whenever the parser works:

- `test_fence_sees_the_27_known_users_columns`
- `test_fence_sees_the_12_known_user_tables`
- `test_keep_allowlists_are_justified_and_not_stale`
- `test_fence_flags_a_users_column_added_by_a_later_migration` (append `999_m.sql`: `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_number TEXT;` → a gap names `phone_number`)
- `test_fence_flags_a_new_table_with_a_user_fk` (`owner_id uuid REFERENCES public.users (id)` → gap)
- `test_fence_flags_a_personal_column_without_an_fk` (`contact_email text` → gap)
- `test_fence_reads_the_latest_definition` (a later file redefines the cascade with no users UPDATE → gaps)

Existing pins that stay green: the eight files of run R0 (§1), unchanged.

### 5.4 Mutants (each killed; byte copy before, restore after, sha256 compare)

| # | mutation | killed by |
|---|---|---|
| M1 | 043: delete `email = NULL,` | `test_cascade_erases_or_keeps_every_users_column`, tombstone map (prototype: "GAP users.email") |
| M2 | 043: delete the `pain_workflow_events` DELETE | table coverage, order test (prototype: "GAP pain_workflow_events.user_id") |
| M3 | 043: drop `SET search_path TO 'public'` | `test_043_redefines…`, assert-block test |
| M4 | 043: drop `SECURITY DEFINER` | `test_043_redefines…` |
| M5 | add `migrations/044_zz_mutant.sql` = `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_number TEXT;` | users coverage (prototype: "GAP users.phone_number") |
| M6 | rollback/043: drop the `user_usage` DELETE line | `test_rollback_043_restores_the_025_statement_byte_for_byte` |
| M7 | 043: drop `OR redeemed_by_user_id = target_user_id` | table coverage (prototype: "DELETE does not key on ['redeemed_by_user_id']") |
| M8 | 043: drop the REVOKE | `test_043_revokes…`, plus `test_retro_w1_2d::test_pin_order_aware_census_is_green_on_the_forward_path` |
| M9 | 043: add `GRANT EXECUTE ON FUNCTION public.delete_user_cascade(uuid) TO service_role;` | `test_043_revokes…grants_nothing`, plus 037 `…exactly ONE…` |
| M10 | 043: remove `'email'` from the guard exists-array | guard test |
| M11 | 043: `email = NULL` → `email = email` | tombstone map |
| M12 | `database_service`: restore `f"... {e}"` | `test_cascade_rpc_failure_logs_no_postgrest_details` |
| M13 | `auth_service`: drop `"home:savings:{user_id}"` | purge test |
| M14 | `auth_service`: purge before the cascade | order test |
| M15 | ONE_PASTE: change one body line | `test_one_paste_body_is_byte_identical_to_043` |

---

## 6. GREEN gates (in order, cheapest first; every pytest through the bounded runner)

`PYT` = `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad/harness/pyt.py`, with `--cwd C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b` and `--log` under the agent's scratchpad.

- **G1, syntax and lint:**
  - `<venv python> -m py_compile app/services/auth_service.py app/services/database_service.py app/api/auth_routes.py tests/test_migration_043_delete_user_cascade.py tests/test_account_deletion_u8b.py`
  - `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache <same files>`
- **G2, sqlfluff** (the repo runs it in `.githooks/pre-commit` stanza 5 and in `test_sqlfluff_config.py`): `PYTHONIOENCODING=utf-8 <venv python> -m sqlfluff lint migrations/043_delete_user_cascade_full_erasure.sql migrations/rollback/043_delete_user_cascade_full_erasure.sql`. Expected: "All Finished!", rc 0.
- **G3, new tests:** `PYT --bound 600 --tag u8b-new -- tests/test_migration_043_delete_user_cascade.py tests/test_account_deletion_u8b.py`. Every node passes.
- **G4, PIN set:** `PYT --bound 600 --tag u8b-pins -- tests/test_delete_user_cascade.py tests/test_account_deletion.py tests/test_migration_037_security_definer_grants.py tests/test_retro_w1_2b.py tests/test_retro_w1_2d.py tests/test_sqlfluff_config.py tests/test_migration_index_predicate_immutability.py tests/test_security_regression.py`. Base was 241 passed and 4 deselected. Head must equal that.
- **G5, comm gate.** The set is `grep -l -E "auth_service|database_service|auth_routes|migrations" tests/test_*.py | sort`: 89 files at base (`comm_set_base.txt`, sha256 prefix `8ca26f6c9b47d911`), plus the 2 new files at head.
  1. Create the base worktree: `git -C C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b worktree add --detach <scratchpad>/u8b-base eb86075ed1f9c65716118ae5567898d01b16a27a`. It is backend-only, so it needs no node_modules.
  2. Run chunks of ≤ 25 files at `--bound 1200`, base then head, with identical file lists. Pass `-rA` among the pytest args so the log carries one outcome line per node. At base, the two new files do not exist: run them at head only. Their base state is the §5 RED table.
  3. Compare node outcomes. Any node that passes at base and fails or errors at head is a defect. A node that fails at base must fail the same way at head, or be explained.
  4. Remove the base worktree: `git worktree remove --force <scratchpad>/u8b-base`.
- **G6, mutants M1-M15 (§5.4).** Use `shutil.copyfile` before each mutation, run only the killing file(s) at `--bound 600`, restore, compare sha256, and stop on a mismatch. M5 creates and then deletes a single scratch file, `migrations/044_zz_mutant.sql`, with no recursive delete; confirm it is gone with `git status --short` afterwards.
  - The `md5_norm` command for R8.3 must be written as a script file, not inline bash, because of the `$` characters. It reads the committed 043, takes the text between `AS $function$` and `$function$;`, applies the Python `md5_norm` of R8.1, and prints the hex digest.
- **G7, diff hygiene:** `git -C <wt> diff --stat` shows only the R6 and R7 hunks in the three Python files, with no whole-file churn. `git status --short` lists exactly the §4 files.
- **G8, optional, needs an orchestrator ruling (Q9):** execute 043, rollback/043 and 043 again on a throwaway local PostgreSQL 18 cluster (`C:/Program Files/PostgreSQL/18/bin` has initdb, pg_ctl and psql), with stand-in tables built from §2a/§2b, Supabase-style roles and one seeded user. Assert the stub columns, zero rows in the 11 tables, NULL audit IPs, the ACL unchanged, and that the guard aborts on a NOT NULL `email`.

---

## 7. Risks, stated limits, and what U8 may say

**Risks:**

- **The out-of-band DDL.** The `users` table and three other tables are not in any migration, so their constraints, triggers and FKs are unknown. The guard block (missing or NOT NULL columns), PRECHECK §1-§4 and §8, and the POSTCHECK nil-uuid dry run cover them. A live CHECK that rejects `'free'`, `0` or `false` would surface at the first real deletion as a 500, without PII in the logs after R7. PRECHECK §2 exists to catch that first.
- **An FK from another user's rows** into the target's `comparisons` with NO ACTION, such as `user_events.comparison_id` of an invitee who viewed a share, would make the cascade fail. 025 has the same exposure today. PRECHECK §4 shows it.
- **Races.**
  - A compare in flight during deletion can write `behavior_profile` back onto the stub (a fire-and-forget task, `structured_comparison_service.py:4255, 5205-5226`), or insert `search_logs` and `comparisons` rows after the cascade.
  - In branch A, a late `search_logs` row (FK NO ACTION, 002:7) blocks the auth delete. The result is a 500, and the retry succeeds.
  - In branch B, a late row survives until the stub is backfilled again.

  The window is seconds and the user is on the delete screen.
- **The auth-delete-failure window.** The data is erased, the account is alive, and the user sees an error. The retry is idempotent.
- **No undo.** The rollback restores the function, not the data.
- **Anti-abuse.** Clearing the fingerprint (already true since 025) lets a user who deletes and signs up again on the same device get a fresh free quota.

**Not covered by U8b:**

- Railway and Sentry logs already written (user ids and URLs), and their retention
- Supabase backups and PITR, which keep deleted rows for the plan's backup window (platform; unverified)
- data already sent to OpenAI
- anonymous `search_logs`, `user_events` and `login_failed` rows that carry no user id
- `brute_force_lockout` audit rows (IP plus `email_hash`, no user id)
- `@qaren_recent_searches` on the device (Q5)
- Sign in with Apple token revocation (U11)

**What the privacy policy (U8) may then truthfully say** (after 043 is applied and POSTCHECK passes, and after the Q2 backfill if PRECHECK §9 c or d is above 0):

> When you delete your account (Profile, then Edit profile, then Delete account), we immediately and permanently delete your comparisons and the links you shared, your searches, feedback, usage, referral and in-app activity records and your preference history. We also erase your email address, name, demographic answers, referral code, notification token, device identifier, preferences, consent records and other profile details from your account record. We keep only a de-identified record (a random account number and the date the account was created) and security logs of sign-in and referral-abuse events linked to that number with your IP address removed; copies in our backups and service logs expire on those systems' schedules.

---

## 8. Open questions (each with a recommendation)

- **Q1. `admin_audit_log` retention.** Should the cascade set the IP to NULL (as R1 does), retain it, or delete the rows? **Recommend NULLing the IP:** the events keep their forensic value through the event type, the time and the stub uuid. Add a retention window, for example 12 months, as a follow-up and not in U8b.
- **Q2. Backfill for accounts deleted before 043** (R9, run only if PRECHECK §9 c or d is above 0). **Recommend yes, right after the POSTCHECK.** Otherwise the policy statement is false for every past deletion in branch B, and in both branches for the audit IPs.
- **Q3. The consent columns.** They are erased, although 038 calls them "legal evidence". **Recommend erasing them:** a timestamp on a stub with no identity proves nothing about a person. Counsel confirms in U8.
- **Q4. Delete the `users` row instead of making a stub?** **Recommend the stub, as R1 does.** It is correct in both FK branches, keeps the auth-failure window consistent, and in branch A the row disappears with the auth user anyway. Turning off 025's "keep the row" is a separate decision with no measured benefit.
- **Q5. Client: `@qaren_recent_searches` survives deletion and logout** (`HomeScreen.tsx:93, 321`). **Recommend a one-line client follow-up:** `AsyncStorage.removeItem('@qaren_recent_searches')` in the delete handler and `clearSession`, shipped via OTA, as part of U3b or a new unit. It is out of scope here.
- **Q6. `referral_invites` where the deleted user is the redeemer.** 025 deletes the referrer's invite row, although the FK was designed as SET NULL (014:27). **Recommend keeping 025's behaviour in U8b**, since it changes nothing for users; revisit with the referral analytics.
- **Q7. Restate the GRANT or not.** R1 does not, because the 037 pin requires exactly one. The assert block proves the grant instead. **Recommend R1 as written.** The alternative is amending the 037 test to allow an identical restatement, which weakens a security pin.
- **Q8. Free-quota reset via delete and re-signup** (already true since 025). **Recommend accepting it:** privacy wins over anti-abuse at this scale. The Redis `anon:{fp}` counter still caps anonymous use for up to 32 days.
- **Q9. Gate G8**, a throwaway local PG18 cluster on localhost. **Recommend allowing it for the adversary only.** It is the only way to execute the SQL before Ahmed does, and it touches no real database. It needs the orchestrator's explicit permission under the "no network" rule.
- **Q10. An `account_deleted` audit event** as evidence of deletion. **Recommend no for U8b:** it would create a new record about the deleted person. Revisit with counsel.

---

## Review corrections (BINDING - supersede the body)

Adversarial review, 2026-10-03 09:02-09:35 AST, Opus, read-and-measure only. The only write outside the reviewer's scratch folder is this appended section. Scratch evidence: `<scratchpad>/u8b/review/` (`notes.md`, the probe scripts, `fence_mutants.txt`, `pg/run*.log`). No real database, Supabase, Railway or network was touched.

**How the SQL was executed.** The body's SQL was run, not only read, on a throwaway PostgreSQL 18.1 cluster in **single-user mode** (`postgres.exe --single -j -D <scratch>/pg/data postgres`, stdin only: no listener, no TCP, no socket). The setup was stand-in DDL for the four out-of-band tables (`users` as in §2a with the branch-A FK, `comparisons`, `comparison_feedback`, `user_events`) and the Supabase roles `anon`, `authenticated` and `service_role`, followed by every forward migration in sorted order. Only 036 failed (`auth.role()` missing; 036 is unapplied live too). Single-user mode gives objects system-range OIDs, so RLS is not enforced there (run 10: `SET ROLE fowner` saw a row under RLS with no policy). Nothing in this section relies on RLS behaviour measured that way.

**What the measurements confirmed.** These parts of the body stand.
- PRECHECK runs, and §6 prints `secdef=true config=search_path=public owner=postgres acl={postgres=X/postgres,service_role=X/postgres} md5_norm=76e8e2f65e9d5cb3b29c5ab57ab9bf61`. That is the Python `md5_norm` of 025.
- The prototype 043 applies cleanly. The POSTCHECK then prints `dry_run ok` and `md5_norm=fa3e7996ea28f5025b40d6e9aa23e855`, with service_role `true` and anon and authenticated `false`. The stored `proconfig` is `{search_path=public}`, which matches the assert's `ARRAY['search_path=public']`.
- The cascade on a fully seeded user, called after `SET ROLE service_role`, leaves the 25-column stub, 0 rows in the 11 tables, and a NULL audit IP for the target only. A second call is a no-op. `DELETE FROM auth.users` then removes the stub (`stub_after_auth_delete 0`, branch A).
- rollback/043 restores `md5_norm 76e8…` with the ACL unchanged.
- With `email SET NOT NULL`, 043 aborts with `043 guard: NOT NULL live, cannot erase to NULL: email`, and the whole file rolls back (the md5 stays 76e8…). Applying it twice is idempotent.
- R9 in branch B (FK dropped, an orphan row with an email and an audit IP) gives `c_after 0`, `d_after 0`.
- The users column set (27) and the user-table set (12) match an independent rebuild from the migrations.
- The PIN set at base: `[pyt] tag=u8b-adv-pins-base start=2026-10-03 09:18:27 end=2026-10-03 09:18:47 elapsed=19s bound=600s status=OK rc=0`, with `241 passed, 4 deselected`.
- 043 and the reviewer variant both lint clean on sqlfluff ("All Finished!").

### C1. Run the nil-uuid dry run INSIDE the migration transaction, and count nil-uuid rows first

The guard checks that the tables exist, but not the `user_id` / `referrer_user_id` / `invitee_user_id` / `redeemed_by_user_id` columns the DELETEs name, and not `admin_audit_log.user_id`. plpgsql resolves those identifiers lazily. The POSTCHECK dry run runs only after `COMMIT`.

Measured in run 7, with `ALTER TABLE public.pain_workflow_events RENAME COLUMN user_id TO uid`:
- The spec's 043 applied with no error, and its md5 became `fa3e7996…`. Every deletion would then fail at call time until the rollback.
- The reviewer variant, which adds the line below as the first statement of `$assert$`, aborted with `ERROR: column "user_id" does not exist … CONTEXT: PL/pgSQL function delete_user_cascade(uuid) line 26`. The function stayed at `76e8e2f6…` (025 in force).

```sql
  PERFORM public.delete_user_cascade('00000000-0000-0000-0000-000000000000'::uuid);
```

**Binding:**
- The line above is the first statement of `$assert$` (R1.1 order unchanged otherwise).
- The test `test_043_assert_block_runs_the_nil_dry_run_inside_the_transaction` pins it between the REVOKE and the `COMMIT;`.
- Mutant **M16**: delete the PERFORM. That test must go red.
- PRECHECK gains a read-only section, **§12 `nil_uuid_rows`**. It counts rows keyed by `00000000-0000-0000-0000-000000000000` in `public.users` (id), `admin_audit_log` (user_id) and each of the 11 tables (every user-ref id column). **STOP if any count is above 0**: both dry runs would erase them. The POSTCHECK dry run stays as a confirmation.

### C2. Detach other people's rows that point at the deleted user's comparisons, before deleting the comparisons

Measured in run 5 (E1). Under a stand-in `user_events.comparison_id → comparisons` FK with NO ACTION, an anonymous `share_opened` event (`user_id` NULL) on the target's shared comparison makes the whole cascade fail:

```
ERROR: update or delete on table "comparisons" violates foreign key constraint "user_events_comparison_id_fkey" … CONTEXT: SQL statement "DELETE FROM public.comparisons WHERE user_id = target_user_id"
```

The call rolls back atomically. `e1_email_still_there = u3@example.test`, the route returns 500, and the account cannot be deleted.

The live FK actions of `user_events.comparison_id` and `comparison_feedback.comparison_id` are unknown (both tables are out of band; the 2026-06-08 audit says only "FK"). 025 has the same exposure today. The body's §4 STOP has no agreed fix, so it would stall the apply.

**Binding:** insert these two statements immediately before `DELETE FROM public.comparisons …`:

```sql
  UPDATE public.user_events
     SET comparison_id = NULL
   WHERE comparison_id IN (
     SELECT c.id FROM public.comparisons AS c WHERE c.user_id = target_user_id
   );
  UPDATE public.comparison_feedback
     SET comparison_id = NULL
   WHERE comparison_id IN (
     SELECT c.id FROM public.comparisons AS c WHERE c.user_id = target_user_id
   );
```

Run 7 measured the effect: after the reviewer variant, the E1 retry succeeds with `email NULL` and `events_detached=1`.

- R1.4: these two UPDATEs come right before the comparisons DELETE. The order test asserts that.
- The R1.5 table array does not change.
- The GREEN recomputes `md5_norm`. Cross-check: the reviewer variant body (C2 only changes the body) measured `970e7ecc98821f8e97581ee76d4162c9` on PG18.
- PRECHECK gains a read-only **§10 `cross_user_comparison_refs`**. It counts `user_events` and `comparison_feedback` rows whose `comparison_id` belongs to a comparison of a different user (or of a NULL `user_id`), so Ahmed learns whether 025 deletions are already failing in production.
- Mutant **M19**: delete the `user_events` detach. A new pin, `test_043_detaches_cross_user_comparison_refs_before_deleting_comparisons`, must go red.

### C3. Probe the tombstone VALUES against the live CHECK constraints inside the transaction

The nil dry run updates zero rows, so a live CHECK or NOT NULL default that rejects `'free'`, `0`, `false` or `now()` is never exercised. It would surface at the first real deletion, which may be the App Review test, as a 500. PRECHECK §2 relies on a human reading constraint text.

Measured in run 12. With a live-like `CHECK (subscription_tier IN ('premium','pro')) NOT VALID` on users, this guard-block probe aborted the transaction before the CREATE:

```
ERROR: new row for relation "u8b_probe" violates check constraint "zz_tier_check"
```

The DETAIL row it printed is the probe's synthetic row, with no personal data.

**Binding:** add this to the end of `$guard$`, using exactly the 25 assignments of the function's users UPDATE:

```sql
  CREATE TEMP TABLE u8b_probe (LIKE public.users INCLUDING DEFAULTS INCLUDING CONSTRAINTS) ON COMMIT DROP;
  INSERT INTO u8b_probe (id) VALUES ('00000000-0000-0000-0000-000000000000');
  UPDATE u8b_probe SET <the 25 assignments of R3>;
```

- The test `test_043_guard_probe_set_map_equals_the_function_set_map_and_expected_tombstone` pins it. It parses both SET lists and compares them with `EXPECTED_TOMBSTONE`.
- Mutant **M20**: change one probe value. That test must go red.
- A failing `INSERT (id)` (a live NOT NULL column with no default) is also a STOP. Paste the error back.
- `test_043_body_schema_qualifies_every_relation` stays scoped to the `$function$` body; the probe's `UPDATE u8b_probe` lives in `$guard$`.
- The fence (C5) ignores `CREATE TEMP TABLE`.

### C4. Remove `--` from inside SQL string literals in the check files: the read-only and single-call tests are vacuous as specified

`tests/_retro_r_mig_sql.strip_line_comments` is `re.sub(r"--.*$", "", line)`, which also cuts inside string literals. PRECHECK §6 and POSTCHECK §2 contain the literal `'^\s*--.*$'`, so `code_only` leaves `regexp_replace(p.prosrc, '^\s*` with an unterminated quote. Quote parity is then inverted for the rest of the file.

Measured with `review/precheck_readonly_probe.py`:
- On the spec's own PRECHECK, `'delete_user_cascade('` appears as code (base verdict `([], True)`), so `test_precheck_is_read_only` would be RED on a correct file.
- A `DELETE FROM public.users` planted inside §6 is NOT detected (`mutant1 … ([], True)`).
- On the spec's POSTCHECK, the literal-blanked count of `delete_user_cascade(` is **3**, not 1.

With the regex written `'^\s*-{2}.*$'`:
- The POSTCHECK count is 1.
- PRECHECK shows no cascade call.
- The planted DELETE is detected (`['DELETE']`).
- On PG18 the two spellings give the identical `md5_norm` (run 5 E2: `fa3e7996…` both ways).

**Binding:**
- R8.1 and R8.3 (and the R8.1 `md5_norm` definition) use `'^\s*-{2}.*$'`.
- A new test asserts that in 043, rollback/043 and every `APPLY_043_*` file, every `--` starts a whole-line comment (`line.lstrip().startswith('--')`), which makes the naive stripper exact.
- Mutants **M17** (a `DELETE FROM public.users` planted in PRECHECK §6) and **M18** (a second `delete_user_cascade(` call planted in POSTCHECK §3) must turn `test_precheck_is_read_only` and the POSTCHECK single-call test red.

### C5. The static fence is vacuous on 9 of 10 realistic mutants: widen it and pin each mutant

`review/run_fence_mutants.py` ran `fence_proto.py` on HEAD plus the prototype 043 plus one mutant file each (`fence_mutants.txt`). Every case below printed `GAPS=0`:
- `900_A` adds `phone_number` to users inside `DO $$ … ALTER TABLE users ADD COLUMN … $$`. That is the repo's own idiom (001). `code_only` blanks dollar bodies.
- `900_B` uses `ALTER TABLE "users" ADD COLUMN …`.
- `900_C` uses `owner uuid REFERENCES public.users ON DELETE CASCADE`, which has no column list and is valid PG.
- `900_F` uses a table-level `CONSTRAINT … FOREIGN KEY (author) REFERENCES public.users (id)`, an item the prototype skips.
- `900_D` uses `phone_number`, `full_name`.
- `900_E` uses `anon_id`, `device_id`, `client_ip`.
- `901_K` adds `… WHERE user_id = target_user_id AND consumed_at IS NULL` in a later redefinition.
- `901_M` uses users `WHERE id = target_user_id AND false`.
- `901_L` uses `email = email`. The body's F4 map-equality rule would catch it; the prototype does not implement F4.

Only `created_by uuid REFERENCES auth.users (id)` was caught.

**Binding fence rules (supersede F1, F2 and F5):**
- **(a)** F1 and F2 scan `strip_line_comments(sql)`, NOT `code_only`, so DDL inside DO blocks counts. The cascade body holds no DDL, so this adds no noise.
- **(b)** Identifiers may be double-quoted, and schema-qualified as `public.` or `"public".`.
- **(c)** A column is a user reference when it carries `REFERENCES [public.|auth.]users` with or without `(…)`, or appears in a table-level `[CONSTRAINT x] FOREIGN KEY (…) REFERENCES [public.|auth.]users`.
- **(d)** The personal-name regex becomes `(^|_)(user|owner|account|profile|member|customer|actor|author|referrer|invitee|redeemer)(_user)?_id$|^(created|updated|deleted)_by$|email|phone|full_name|first_name|last_name|display_name|address|fingerprint|device_id|install_id|anon_id|push_token|(^|_)ip($|_)|ip_address|remote_addr|user_agent|session_id|governorate|gender|birth`. It comes with a `NOT_PERSONAL` allowlist (justification ≥ 40 chars) for false positives. `review/widened_regex_probe.py` measured this regex over `strip_line_comments` of every forward migration. At head it flags exactly the columns the current fence already sees: `admin_audit_log.{ip_address,user_id}`, the `user_id`-shaped columns of the 9 migration tables, `referral_invites.device_fingerprint_hash`, and `users.{device_fingerprint_hash,expo_push_token}`. The 001 DO-block columns are not flagged, so `NOT_PERSONAL` starts empty.
- **(e)** Each DELETE's WHERE must be EXACTLY an OR-chain of `<col> = target_user_id` terms covering every user-ref id column of that table. A user-ref id column is one with an FK into users or a name matching the `…_id$` / `…_by$` part of (d). Other personal columns of a table deleted by owner, such as `session_id` or `device_fingerprint_hash`, need no WHERE term. The users UPDATE WHERE must be exactly `id = target_user_id`. The audit UPDATE WHERE must be exactly `user_id = target_user_id`. The C2 detach UPDATEs are recognised as `SET comparison_id = NULL WHERE comparison_id IN (SELECT … user_id = target_user_id)`.
- **(f)** F4 compares the parsed SET map with `EXPECTED_TOMBSTONE`, so `email = email` fails.

Each of the ten mutants above becomes a §5.3 self-test on an in-memory file list, never a file in `migrations/`. Each must produce a named gap. M5's coverage is kept.

### C6. `users.governorate` is read by the code, but no migration or doc creates it: a likely out-of-band personal column

```
$ grep -rn -A3 -E 'table\("users"\)' app/ scripts/ | grep -oE '\.select\(\s*"[^"]*"'
… .select("id, expo_push_token, last_comparison_at, governorate, preferences")   (scripts/cron_reengagement.py:46)
app/services/reengagement_service.py:178:        governorate = user.get("governorate")
```

The §2a census checked only the columns the code WRITES. It must also list the columns the code READS. The full `.select(` set on users is in `notes.md`, and `governorate` is the only unknown.

**Binding:**
- §2a names `governorate` as a candidate.
- If PRECHECK §1 shows it (or any other column outside the 27), STOP and add it before applying. That means `governorate = NULL` in the users UPDATE, in the C3 probe, in both guard arrays, in `EXPECTED_TOMBSTONE` and in `USERS_BASELINE_COLUMNS`.
- If PRECHECK shows it absent, the re-engagement cron's select is broken (that is a separate issue) and nothing changes here.

### C7. A RED test passes at base

`test_cache_purge_failure_never_blocks_the_auth_delete` asserts only that `admin.auth.admin.delete_user` is called once and that the function returns True. At base, `delete_user_account` (`auth_service.py:980-988`, read) never calls `delete_cached`, so with `create=True` patching the test is GREEN at base. This is reasoned from the code, not executed.

**Binding:** it also asserts `delete_cached.call_count == 5`. Every key is attempted, even though each one raises.

### C8. Add the reverse Redis drift fence

`test_purge_key_templates_match_their_writers` proves that each purged template has a writer. It does not prove that every per-user writer is purged.

**Binding:** add `test_every_per_user_cache_key_is_purged_or_kept`. It scans `app/` for f-string Redis keys that interpolate a user id (`{user_id}`, `{uid}`, `{current_user[...]}`), and requires each template to be in `DELETED_USER_CACHE_KEY_TEMPLATES` or in an explicit `KEPT_USER_CACHE_KEY_TEMPLATES` with a justification (the `usage:*` counters). The writers measured today are exactly the five plus `usage:daily:{user_id}:{today}`, `usage:monthly:{user_id}:{month}` and `usage:{user_id}:{today}` (`grep -rn -E 'f"[a-z_:]*\{[^}]*(user|uid)[^}]*\}' app/`), so the test is green at head.

### C9. PRECHECK must show what can make the erase silently incomplete (all read-only)

**Binding:**
- **§8** covers triggers on all 13 tables (users, admin_audit_log and the 11), not only `public.users` and `auth.users`. A BEFORE DELETE or archive trigger on a child table would defeat the erase with no error.
- New **§11**: for each of the 13 tables, the owner, `relrowsecurity` and `relforcerowsecurity`, plus `rolbypassrls` of the function owner. **STOP** if the function owner is neither the table owner nor BYPASSRLS on any table, or if FORCE ROW LEVEL SECURITY is on. Under PostgreSQL's documented semantics, an RLS-filtered DELETE or UPDATE affects 0 rows with NO error, and both dry runs would still pass. This could not be measured in single-user mode; it is stated as PG semantics.
- The **§2 STOP** also covers **§3** unique indexes, including expression indexes such as `lower(email)`, which a CREATE UNIQUE INDEX produces with no constraint row.
- **§10** comes from C2 and **§12** from C1.
- Optional and non-binding: a §13 row with the `auth.audit_log_entries` count, guarded with `CASE WHEN to_regclass('auth.audit_log_entries') IS NULL THEN 'absent' ELSE … query_to_xml(…) END`. GoTrue's audit log (when enabled) stores the actor email and IP and is not removed by `admin.delete_user`. That is platform knowledge, not measured. See C10.

### C10. The §7 policy text overstates the erase

**Binding corrections to the draft U8 may use:**
- **(a)** The stub keeps the creation time AND the deletion time (`updated_at = now()`). In branch A it is deleted with the auth user (run 4, `stub_after_auth_delete 0`).
- **(b)** `login_failed` and `brute_force_lockout` audit rows keep the IP address, and lockouts keep `email_hash` (sha256 of the lowercased email, 16 hex characters). They are NOT linked to the account number and are NOT erased (`auth_routes.py:688-695, 711-718, 1065-1072`). The text must disclose them with a retention period, and must not imply that every sign-in record is de-identified.
- **(c)** "your searches" holds for the server only until Q5 ships. Write "from our servers", or ship Q5 first.
- **(d)** The Supabase auth audit log, if enabled, is platform data. Either verify it (C9 §13) or cover it under the backups-and-service-logs sentence.
- **(e)** Deleting an account that redeemed an invite also deletes the other party's invite and redemption rows, so the referrer loses that bonus. This is 025 behaviour, measured in run 4 (`invites=0`). It is not a privacy statement, but the referral FAQ should not promise otherwise.

### C11. R4.1's justification for `created_at` cites the wrong evidence

`vw_cohort_match_rate` (013:23-33) groups by `date_trunc('day', updated_at)`, not `created_at`. Also, the 2026-06-08 audit's "currently 22" list names neither `created_at` nor `updated_at` (the 22 listed columns sum to 22 without them). `updated_at` must exist, because the 013 view applied. `created_at`'s existence rests on the documentation only.

**Binding:**
- Rewrite the justification as "account creation date on the stub; no person-identifying value".
- PRECHECK §1 decides whether `created_at` exists. If it is absent, drop it from `USERS_BASELINE_COLUMNS` and `KEEP_USERS_COLUMNS`.
- Note that 043's `updated_at = now()` moves tombstones into the deletion day of `vw_cohort_match_rate`. That affects analytics only.

### C12. The 043 header wording is wrong in branch A

"four tables … which never fire because the function keeps the users row" becomes "… whose `ON DELETE CASCADE` fires only when the `public.users` row itself is deleted, which happens in branch A on the auth delete and never in branch B". Run 4 measured the branch-A cascade.

### C13. The G5 comm set

The grep becomes `grep -l -E "auth_service|database_service|auth_routes|cache_service|migrations" tests/test_*.py`. `auth_service` gains a module-level `delete_cached` binding from `cache_service`, and the W0-3 reload hazard (CLAUDE.md, five rules) is exactly a `from … import` binding.

### C14. Gate G8 (Q9) runs in single-user mode, so it needs no network ruling

The GREEN agent re-runs the reviewer's harness on the committed bytes, with a fresh `initdb` into its own scratch folder (never a recursive delete of the old one):
- `review/pgsingle.py`, which splits on top-level `;`, drops blank lines and terminates each statement with `;\n\n` for `-j`
- `pg_setup.sql`
- every forward migration
- PRECHECK, 043, POSTCHECK, `pg_seed_and_delete.sql`, rollback/043, 043 twice
- the C1, C2 and C3 negative cases (`pg_edge.sql`, `pg_probe_values.sql`, the run-7 column rename)

Expected: the same verdicts as in this section, with the recomputed `md5_norm` values. RLS is not measurable there (see the top of this section).

### Answers to the writer's open questions (recommendations; the orchestrator rules)

- **Q1 (audit IP):** agree. NULL the IP on rows where `user_id` = target, and keep the event rows. Also disclose the unlinked `login_failed` and `brute_force_lockout` rows (C10b). File the 12-month retention as a follow-up covering ALL `admin_audit_log` rows, because the unlinked rows are the ones still holding IPs.
- **Q2 (backfill):** agree, YES, run it right after POSTCHECK whenever PRECHECK §9 c or d is above 0. Measured in branch B: `c_after 0`, `d_after 0`. It is re-runnable (a second run changes 0 rows). Run it after §12 (C1) shows no nil-uuid rows.
- **Q3 (consent columns):** agree, erase them. Counsel confirms in U8.
- **Q4 (stub vs delete):** agree, keep the stub. It is correct in both branches, and in branch A the row is gone after the auth delete anyway (measured).
- **Q5 (`@qaren_recent_searches`):** agree it is out of scope for U8b. Ship it in the same OTA as U3b, before U8's policy text claims "your searches" are deleted (C10c). Clear it in both `clearSession` and the delete handler.
- **Q6 (redeemer-side invite rows):** agree, keep 025's behaviour in U8b. Record the measured side effect (the referrer's invite and redemption are deleted, and with them the referrer's active bonus) as a referral follow-up (C10e).
- **Q7 (GRANT restatement):** agree, R1 as written. Measured on PG18: CREATE OR REPLACE, rollback/043 and a re-apply all keep `{postgres=X/postgres,service_role=X/postgres}`. The `$assert$` proves it.
- **Q8 (free-quota reset):** agree, accept it.
- **Q9 (local PG):** allow it, in single-user mode only (C14). The reviewer already ran it that way, with no listener and no network.
- **Q10 (`account_deleted` audit event):** agree, NO for U8b.

**Verdict: APPROVED_WITH_CORRECTIONS.** The design is sound and its SQL executes as specified on PG18. The binding gaps are:
- the post-commit-only dry run (C1)
- a cross-user FK that can block every deletion (C2)
- unprobed tombstone values (C3)
- vacuous read-only and single-call tests (C4)
- a fence that misses the repo's own DO-block DDL idiom and 8 other mutants (C5)
- the unclassified `users.governorate` (C6)
- one RED test that is green at base (C7)

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

---

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ)

Fable orchestrator, session 71, 2026-10-03 10:04 +03. Verdict: **PASS, no change**. GREEN may start.

Reviewed: `tests/test_migration_043_delete_user_cascade.py` (sha256 `4f8d7dadf5ad3729...`, 1336 lines, 51 nodes) and `tests/test_account_deletion_u8b.py` (`846f34e8274e64f1...`, 266 lines, 10 nodes). Measured by the RED agent at `eb86075e`: 35 failed / 26 passed, 0 collection errors, 0 network attempts; every RED fails for its stated reason (the missing 043, rollback and one-paste files fail inside the test body; the two coverage tests list exactly the 20 users gaps and 5 table gaps of the 025 body; the backend reds show the sentinel in the logged text, zero purge calls and the missing constant); the PIN set is 241 passed without the files and only the 35 REDs fail with them; a spec-shaped prototype in a detached scratch worktree passed all 61 nodes and the full PIN set (303 passed), and 26 of 26 file-level mutants were killed. The orchestrator read the report, the expected tombstone map (25 columns, the three NOT NULL columns at 0 / false / 0) and the KEEP lists.

- **UG1 - the RED deviations are accepted:** the route's 500 text is read under `error` or `detail` (the envelope renders it under `error`); the cascade-body mutant self-tests run over the LATEST cascade definition, so they are PINs at base; the KEPT cache-key list lives in the static test file; the seven extra tests; the stronger no-GRANT scan.
- **UG2 - the two RED files are FROZEN.** A test edit needs a test defect proven by measurement and is reported as a deviation.
- **UG3 - the SQL keeps the spec's SHAPES.** The guard arrays, the temp-table probe (`CREATE TEMP TABLE u8b_probe (LIKE public.users INCLUDING DEFAULTS INCLUDING CONSTRAINTS) ON COMMIT DROP`) and the statement order are parsed by the tests as the spec writes them; a semantically equal rewrite is not accepted.
- **UG4 - the base moved** to main `ca604e0a` (PR #285). Measured: #285 changed none of `auth_service.py`, `database_service.py`, `auth_routes.py`, `cache_service.py`, `home_routes.py` or `migrations/`. The worktree is fast-forwarded; BASE for the comm gate is `ca604e0a`.
- **UG5 - the PostgreSQL 18 single-user run (G8) is MANDATORY for GREEN**, including the three abort paths that must leave the 025 body in force.
- **UG6 - the PR text carries the owner's apply runbook** (PRECHECK first and its STOP rules, ONE_PASTE, POSTCHECK, the optional BACKFILL, the rollback and its limit), the three privacy defaults he may change before applying (UR3, UR5, UR10), the corrected policy statement for U8 (C10) and the follow-ups. Merging the PR applies nothing to the database.

## Orchestrator rulings after the adversaries (BINDING, 2026-10-03 12:13, supersede everything above)

Both adversaries returned SOUND (0 defects; 10 + 8 minors). The fix agent changed no app code, rewrote the PRECHECK STOP rules, the BACKFILL header and the rollback warning, and added one pin file. The orchestrator re-hashed the thirteen files, read migration 043, the backend diff and the pin file, fast-forwarded the worktree to main 0a7446b4 (no overlap) and re-ran the three unit files (71 passed) and the pin set (242 passed, 4 deselected).

- **UF1 (gate PASS).** tests/test_account_deletion_u8b_fix_pins.py (10 nodes) is accepted as part of the unit: it pins that neither deletion log line attaches a traceback (MD1, MD2), that the sqlstate slot never falls back to the exception text (MS), that the purge runs off the loop only under ENABLE_ASYNC_REDIS_OFFLOAD (MG), and that the purge warning names the type only (MW). The two RED files stay frozen.
- **UF2 (follow-up, Ahmed instruction).** Accounts deleted OUTSIDE the app (the Supabase Auth dashboard) in branch A leave comparisons (with live share tokens), user_events, comparison_feedback and search_logs rows that neither 043 nor the BACKFILL erases; PRECHECK section 9 f and BACKFILL f_after now report them. Erasing them changes R9 and a frozen pin, so it is a follow-up issue. Until it ships, accounts are deleted through the app (DELETE /auth/account) or by calling public.delete_user_cascade(id) in the SQL editor BEFORE the auth delete.
- **UF3 (follow-up).** The route raises HTTPException(500) inside the except arm, so the Sentry Starlette integration carries the chained exception text (URL, email) for non-PostgREST failures; pre-existing at base. Fix = raise ... from None plus a pin; it changes the R7-frozen raise line, so it is its own small unit, before launch.
- **UF4 (follow-up).** delete_cached logs "Cache delete error: {e}" at ERROR, so a Redis outage adds five ERROR lines and up to five Sentry events per deletion (cache_service is outside this unit).
- **UF5 (follow-up).** The apply-time probe tests CHECK and NOT NULL only; a NULLS NOT DISTINCT unique index or an outgoing FK on users passes the apply and fails the first real deletion with a 500 (fail-closed). PRECHECK sections 2 and 3 carry the STOP wording; a guard-level check is a 044 follow-up.
- **UF6 (follow-up, low).** The reverse cache-key fence sees f-string keys only; a census found no other per-user key today.
- **UF7 (stated limit).** With ENABLE_ASYNC_REDIS_OFFLOAD unset (the production default) the purge runs five blocking Upstash DELs on the event loop (R6 shape, the history_routes idiom, route limited to 1/minute). Not changed.
- **UF8 (privacy defaults, Ahmed).** Unchanged from the spec: audit-log rows are kept with their IP nulled; the consent timestamps are erased with the row; the free quota resets on delete-and-re-register. If Ahmed wants any of the three otherwise, that is a 044, not an edit of 043.
