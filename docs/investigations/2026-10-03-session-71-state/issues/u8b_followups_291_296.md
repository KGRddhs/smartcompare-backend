=== TITLE: Erase the rows of accounts deleted outside the app (PRECHECK section 9 f)
=== LABELS: backend,privacy
## Context
U8b (PR #U13PR, migration 043) erases everything when an account is deleted THROUGH the app. An account deleted from the Supabase Auth dashboard (branch A: `users_id_fkey ... ON DELETE CASCADE`) loses its `public.users` row by cascade, but its `comparisons` (with live share tokens), `user_events`, `comparison_feedback` and `search_logs` rows survive, because those tables have no FK to users. The SQL adversary measured it (run14). `APPLY_043_1_PRECHECK.sql` section 9 now counts them (the four `f` rows) and the BACKFILL reports `f_after`, but neither erases them (ruling UF2: it changes R9 and a frozen pin).

## What to build
- A 044 backfill (one-paste, PRECHECK, POSTCHECK) that deletes or detaches those rows for every user id with neither an `auth.users` nor a `public.users` row, with the same hermetic PostgreSQL 18 single-user test harness U8b used, and the UR8 / C2 semantics for other users' rows.
- Optionally a scheduled or trigger-based path so a future dashboard deletion cannot leave orphans.

## Until it ships
Delete accounts through the app (`DELETE /auth/account`) or run `select public.delete_user_cascade('<id>')` in the SQL editor BEFORE deleting the auth user.

=== TITLE: Deletion route: raise from None so Sentry stops carrying the chained exception text
=== LABELS: backend,privacy
## Context
Pre-existing at main `ca604e0a`, measured by the U8b backend adversary with `init_sentry()` and an in-memory transport: `DELETE /auth/account` raises `HTTPException(500)` inside its `except` arm (`app/api/auth_routes.py`, the deletion route), so the Starlette/FastAPI Sentry integration captures the 5xx with the original exception chained as `__context__`. For `httpx.ConnectError`, `AuthApiError` and `RuntimeError` the chained text (URL, email) reaches the Sentry event. For a PostgREST `APIError` only `.message` is sent, never `details`, so the failing-row leak U8b closed in the logs does not reach Sentry.

## What to build
`raise HTTPException(...) from None` on that line, plus a pin with the in-memory-transport pattern from the adversary notes (scratchpad `u8b/adv-backend`). U8b froze that raise line under R7, so this is its own small unit. Before launch: it is the only path left where an email can reach Sentry from the deletion flow.

=== TITLE: delete_cached logs the Redis error text at ERROR; a Redis outage now adds five lines per account deletion
=== LABELS: backend,observability
## Context
`app/services/cache_service.py` `delete_cached` swallows every Redis exception and logs `Cache delete error: {e}` at ERROR. U8b purges five per-user keys on every account deletion, so a Redis outage now emits five ERROR lines (and, through the Sentry logging integration, up to five events) per deletion. The text is a Redis error, not personal data, but it is new noise on the delete path, and the unit's own type-only WARNING is unreachable because `delete_cached` never raises.

## What to build
Log the exception TYPE at WARNING in `delete_cached` (or let it raise and keep the type-only WARNING in the purge), with the `exc_summary` helper from `app/services/log_scrub.py` (#285) if text is wanted; pin it.

=== TITLE: Migration 043 guard: probe unique indexes and outgoing FKs at apply time
=== LABELS: backend,migrations
## Context
The U8b SQL adversary measured that the apply-time tombstone probe in `migrations/043_delete_user_cascade_full_erasure.sql` tests CHECK and NOT NULL only. A `UNIQUE ... NULLS NOT DISTINCT` index on a tombstoned column (two tombstones collide on NULL) or an outgoing FK from `users` to another table (for example `subscription_tier` to a plans table without 'free') passes the apply and fails the first real deletion with a 500 (fail-closed, data intact). Today only the PRECHECK STOP wording (sections 2 and 3) covers it, i.e. a human reading the grid.

## What to build
A 044 guard block that raises on those two shapes (query `pg_index` with `indnullsnotdistinct` and `pg_constraint` contype `f` where `conrelid = 'public.users'::regclass` and the target is not `auth.users`), with the hermetic PostgreSQL 18 harness U8b used. Also list `pg_rules` in the probe (a `DO ALSO` rule that archives deleted rows defeats the erase; PRECHECK section 8 lists it now).

=== TITLE: Client: clear @qaren_recent_searches on account deletion
=== LABELS: mobile,privacy
## Context
U8b erases the server side of an account. The client keeps recent searches on the device under the `@qaren_recent_searches` AsyncStorage key, so the policy text must not claim that searches saved on the device are deleted until this ships (U8b PR text, policy statement note).

## What to build
On a successful `DELETE /auth/account` (and on logout if the product wants it), remove `@qaren_recent_searches` and any other per-account device cache; pin it in the auth service tests. OTA-capable.

=== TITLE: Audit-log retention window for admin_audit_log rows of deleted accounts
=== LABELS: backend,privacy
## Context
Ruling UR3 of U8b keeps the `admin_audit_log` rows of a deleted account (sign-in events, referral-abuse checks, invite redemptions) with `ip_address` set to NULL, linked to the de-identified account id, for abuse forensics. There is no retention window: they are kept forever.

## What to build
A scheduled purge (or a cron SQL function with the 037 ACL pattern) that deletes audit rows older than N days whose `user_id` has no `auth.users` row, with N decided by the owner together with the legal inputs (U8). Pin the window in the policy text.
