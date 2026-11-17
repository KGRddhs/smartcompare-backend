# INC-SEC-1 ADV-A1 (SQL and database) report, 2026-11-17

Verdict: SOUND (no BLOCKING, no MAJOR; 4 MINOR = stated limits or note fixes).
Head read: e4cfe89e (merge of origin/main 7f672cfe into 89d94d25). The SQL blobs at the head equal the unit commit c8941dfe
(git diff c8941dfe e4cfe89e -- migrations docs is empty). sha256 up ed0959f7, down 041b62ec, check 2d4a8af5 = the apply note values.
Read-only toward W, with one disclosure: one `git fetch origin` in W (remote-tracking refs only; origin/main is now 9bc13109, #419,
which adds no migration). No branch, index or worktree change. No scratch worktree was needed (SQL lens; no pytest run).

## Own throwaway cluster
PG 18.1, initdb in adv_a1/pgdata, 127.0.0.1:55541, trust. Roles plus red/cluster/setup_db.sql (synthetic ids only), the 054 blob at the
head (equal to red/cluster/blobs/054_up.sql) and 055 at the head. Stopped with pg_ctl stop -m fast: no postmaster.pid, port not
listening. The Windows service was not touched. Nothing live was contacted.

## Runs
- a1 (superuser owner): 054 -> grid g1 (K01 26 rows, K02 42 rows, set_equals_measured_21 true, PUBLIC none) -> 055 rc 0 -> g2
  (K01 10, K02 26 rows over 13 relations, set_equals_measured_21 FALSE) -> rollback rc 0 -> g3 byte-equal to g1. A second rollback
  is equal too; two re-applies of 055 give a rich snapshot equal to the first apply.
- Rich catalog snapshot (ACL entries with grantor and grant option, policies with permissive/cmd/roles/expressions, function
  acl/config/owner/comment, triggers, column and schema and default ACLs): after rollback equal to before, EXCEPT the raw proacl text
  order of resolve_referral_code (the same four entries in another order; semantically identical).
- a2 (NON-superuser owner owner_pg, member of anon/authenticated/service_role, owning schema public and every public object, like the
  hosted postgres role): 054, 055 and the rollback all rc 0 as owner_pg; rollback grid equals the before grid; the AFTER grid equals
  the superuser AFTER grid once the owner name is normalised. The live proofs file (THROWAWAY_ID filled with a synthetic id, both
  synthetic users set to tester), run as owner_pg: before 055 P0 P7 P8a PASS and P1-P6 P8b FAIL; after 055 P0-P8b all PASS;
  referral_invites empty afterwards.
- a3 lock_timeout: an open reader holding ACCESS SHARE on comparisons makes 055 fail at 5 s (lock timeout); grid unchanged.
- a3 delete path: FKs added (verdict_critiques CASCADE, pain_workflow_events SET NULL, comparison_feedback SET NULL, referral_invites
  CASCADE); after 055 an authenticated owner deletes its own comparison and every referential action runs (they run as the owner).

## Probes beyond P0-P8 (after 054 + 055; out/probes_after055.txt, 50 rows)
Closed as intended: another user's shared row is invisible to authenticated and anon; an own UPDATE of comparisons is refused; email,
created_at, attribution_source, last_comparison_at, behavior_profile and demographics_profile (a jsonb merge and a set to NULL included)
are refused with the 055 message; TRUNCATE is refused; users INSERT and DELETE are refused; the views, the ratings table and the referral
lookup are refused; a signed-out feedback insert is refused; a referral_invites insert is refused by row security; claims saying
service_role while current_user is authenticated are refused; a definer-style write (current_user postgres, claims authenticated,
also through the legacy single-claim setting) is refused, the same rule as 054.
Server paths intact: service_role with service claims writes the six columns, inserts users with them, runs delete_user_cascade (the
048 cascade, which nulls email and profile columns), calls resolve_referral_code under its new search_path, reads the three views,
reads and writes the ratings table, products, eval_runs, comparisons (insert plus share token), feedback with a comparison id, and
search / event / audit / usage rows. postgres with no claims writes freely.
Still writable by the row owner: the L4 columns plus the user-owned expo_push_token, notifications_enabled and preferences (the three
server writes made with the user's key, push token and the two preference routes, touch only these). With 054: an update of an
entitlement column and a profile column together is refused by 054's message first (BEFORE triggers fire by name). Unreadable claims
raise 22P02 (L2).

## State mix walk (database view)
1. 054 on, 055 off, server before C2 (today): unchanged.
2. 054 on, 055 off, server with C1/C2/C2b: every write by the server key; the openings stay until 055.
3. 054 on, 055 on, server with C2: the target; the probes above.
4. 055 on, server before C2: FORBIDDEN (R-5), named in both notes and the 055 header.
5. 055 on, 054 rolled back: 055 stands alone (RED run 5); K04 then shows only users_profile_guard.
6. 055 rolled back, server with C2: state 2, nothing lost.
7. C3 ON or OFF, with or without 055: the invitee read uses the server key; database-neutral.
8. ENABLE_HOME_SAVINGS_AGGREGATE: its RPC is absent live and untouched by 055.

## PG 15
No construct newer than 15 in up, down, check or proofs (scanned for MAINTAIN, SYSTEM_USER, IS JSON, JSON_TABLE, any_value,
pg_get_acl, membership WITH SET/INHERIT, MERGE RETURNING and others). Newest used: CREATE OR REPLACE TRIGGER (14), gen_random_uuid (13),
AS PERMISSIVE (10). On 15, GRANT ALL lacks MAINTAIN, so the rollback restores exactly what 15 holds. Not run on 15 (L1); K11 guards it.

## Findings
- A1-M1 MINOR (apply note section 6): "The rest as section 4" carries the BEFORE STOP rules into the AFTER grid. After a correct apply
  K02 set_equals_measured_21 is false (13 relations, 26 rows measured) and K04 shows a trigger besides 054's, so the note calls a STOP
  on a good apply. Must change: state K02 AFTER explicitly (false expected; the 13 relations; public_acl none) and mark which STOPs are
  BEFORE-only (K01 catalog, K02, K04 other-trigger) and which hold both times (K03, K11).
- A1-M2 MINOR (owner summary, "What is permitted today"): says the public key "ships inside the app"; the review, 037 and the summary's
  own "What stays" say the app ships no database key. Must change: the key is public by design and must be assumed known.
- A1-M3 MINOR (055 F8): resolve_referral_code gets search_path = public with an unqualified body, so the temporary schema is still
  searched first for relations. After 055 only the server role and the owner may execute it. Stated limit, or 'public, pg_temp' or a
  qualified body in a follow-up.
- A1-M4 MINOR (check K10): flags only definer functions that write users. After 055 the expected set of definer functions executable by
  anon or authenticated is empty; a row over every public definer function with app-role EXECUTE would STOP on any future one that
  bypasses the 055 revokes. The catalog has none today besides resolve_referral_code. Stated limit.

No misuse text, key, project ref, real id or address in the unit diff (afde168f..89d94d25) or the three notes; ids are synthetic and
addresses use example.invalid.
