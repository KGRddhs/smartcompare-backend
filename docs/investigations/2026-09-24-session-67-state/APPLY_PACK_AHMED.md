# Ahmed's apply pack — 2026-09-24 (session 67)

## 0. FIRST — the Railway trial expired: PRODUCTION HAS BEEN DOWN SINCE 2026-09-21 08:03 UTC

Measured 2026-09-24 ~15:00 local via the Railway CLI (logged in as the account you used):

- `https://web-production-58776.up.railway.app/health` → **404 `{"status":"error","code":404,"message":"Application not found"}`** with `x-railway-fallback: true` = no live deployment behind the domain.
- `web` deploy log: `sending signal SIGTERM to container` at **2026-09-21T08:03:31Z**, `Stopping Container` at 08:04:02Z. `qaren-landing` (nginx) logged its workers exiting at **08:03:30Z the same second** → an account-wide platform action, not a code or config change (`qaren.app` is 522 for the same reason).
- `railway redeploy --service web --yes` → **`Your trial has expired. Please select a plan to continue using Railway.`** That is the cause.
- Consequence for the code: `web` has had **no deployment since 2026-09-11 10:26 UTC (PR #162, `fe0298ae`)**. Every merge of sessions 66 and 67 (#163–#196) is on main but has NEVER run in production; the GitHub webhook still reaches the project (`price-warmer` records a `SKIPPED` row per push, correctly, via its watch patterns) but blocked builds create nothing on `web`.

**UPDATE 15:20 local — steps 1 and 2 are DONE:** you subscribed at ~15:18; Railway re-created `web` and `qaren-landing` and I re-issued `railway redeploy` for both; `/health` is 200 on image `fe0298ae` (2026-09-11). **UPDATE 15:25: step 4 is DONE too** — the logout-flag variable change rebuilt `web` from the connected GitHub source at current main `dff65210` (deployment `2c4dbf6e`, `/health` 200), so every session-66/67 merge is now in production with `ENABLE_BRIGHTDATA_BUDGET_GATE=true` and `ENABLE_LOGOUT_UPSTREAM_REVOCATION=true`. Nothing remains in this section except watching the first `[auth]` and `[BUDGET]` log lines.

Do, in order:

1. Railway dashboard → Billing → **select a plan** (Hobby is enough for one web + one static service; the price-warmer is off). I cannot do this: payments are yours alone.
2. Then `railway redeploy --service web --yes` restores the 2026-09-11 image (fe0298ae) immediately — or, better, deploy CURRENT main: dashboard → `web` → Deployments → "Deploy" from `main` (or push an empty commit: `git commit --allow-empty -m "chore: redeploy" && git push origin main`). Tell me which, and I verify `/health` 200 + `loop_lag_ms` on the new process and read the `[BUDGET]`/`[brightdata]` lines. Also redeploy `qaren-landing` (same command with `--service qaren-landing`) so `qaren.app` stops 522-ing.
3. **`ENABLE_BRIGHTDATA_BUDGET_GATE=true` is ALREADY SET on `web` and `price-warmer`** (done by me 2026-09-24 ~14:50 local, verified by an exact-line count on both services; no other variable was read or printed). It takes effect on the first deployment after the plan is selected — nothing else to do for it.
4. If, after step 2, pushes to main still create no `web` deployments: `web` → Settings → Source: reconnect `KGRddhs/smartcompare-backend` branch `main`, "Deploy on push" on. Proof it works: the next merge shows a `BUILDING` row within a minute.

Everything below needs a credential or a dashboard this box does not have (no `psql`, no database URL in `.env`, no Supabase dashboard access, no provider consoles). Each step is written so it can be pasted as-is. Keep every query output next to this file (paste into `docs/investigations/2026-09-24-session-67-state/APPLY_OUTPUTS.md`).

## A. Migrations — DONE 2026-09-24 17:50–18:35 (kept as the record of what was run and measured)

**MIGRATIONS APPLIED 2026-09-24 17:50–18:35 local** (Ahmed's clicks in the Supabase SQL editor, driven from the browser pane; every step measured, the pre-state first): **040** → `cleanup_expired_ratings()` is SECURITY INVOKER (`prosecdef=false` — the review's "SECURITY DEFINER" was wrong; body `DELETE FROM rating_cache WHERE expires_at < NOW()`), proacl `{=X,postgres,anon,authenticated,service_role}` → `{postgres,service_role}`; anon GET on the rpc 25006 → 42501. **037** → `delete_user_cascade` + `increment_lifetime_comparisons` `{postgres,service_role}` only, `resolve_referral_code` `{postgres,anon,authenticated,service_role}` (PUBLIC removed, anon kept by design); the anon-executable SECURITY DEFINER census = `resolve_referral_code` alone; anon POST `rpc/delete_user_cascade` (nil uuid) 204 → 42501; `tests/test_migration_037_security_definer_grants.py -m live_db` 4 passed. All three had carried the stock explicit grants, so a PUBLIC-only revoke would have been a no-op — 037's `FROM PUBLIC, anon, authenticated` was exactly right. **037's RLS half was a no-op by 037's own rule:** `user_events` already had RLS enabled (owner postgres, force off) and FOUR policies — the leak was the out-of-band policy "Service role can read all events" (PERMISSIVE, SELECT, {public}, USING (true); service_role bypasses RLS, so it granted every role, anon included: 147 rows), plus a harmless out-of-band duplicate of events_insert ("Users can insert own events", left in place). **041** (`migrations/041_user_events_drop_public_select_policy.sql`, PR #199 → `3b0ea5d7`, test-first, rollback re-creates the policy verbatim) dropped it BY NAME → three policies remain, anon `count=exact` 147 → 0. **038** → the three nullable consent columns exist on `users`. NOT applied: 035, 036 (re-run the idempotent 037 after a late 036); 039 stays reserved. `ENABLE_CONSENT_PERSIST=true` was set on `web` right after (its own redeploy); `ENABLE_CONSENT_REQUIRED` still waits for the smoke-probe consent fields (and phones on the new OTA).

### Original plan — Supabase SQL editor, in this order (one script per run; the editor wraps each run in ONE transaction, so a "no error" screen is not evidence — the AFTER queries are)

### A1. 040 census (read-only, BEFORE) — run in the same session as A2

```sql
SELECT p.oid::regprocedure AS signature,
       p.prosecdef,
       p.proacl,
       pg_get_functiondef(p.oid) AS definition
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'public' AND p.proname = 'cleanup_expired_ratings';

SELECT p.oid::regprocedure AS signature, p.proacl
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'public'
   AND p.prosecdef
   AND has_function_privilege('anon', p.oid, 'EXECUTE')
 ORDER BY 1;
```

Expected BEFORE: `cleanup_expired_ratings` is listed in the second query. An `anon=X/...` entry, a bare `=X/...` entry (the empty grantee IS PUBLIC) or a NULL `proacl` in the first query means anon can call it. If the first query returns NO row, stop and tell me: 040 becomes a no-op (it still applies safely, but the finding needs a re-look).

### A2. Apply `migrations/040_revoke_cleanup_expired_ratings.sql` (paste the whole file). Re-run both A1 queries. Expected AFTER: the second query lists ONLY `resolve_referral_code` (deliberately anon-callable for signup). Any OTHER row is a further out-of-band function and needs its own migration — tell me.

Live proof from a shell (no values are printed; the variables come from your environment):

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$SUPABASE_URL/rest/v1/rpc/cleanup_expired_ratings" -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY"
```

Must be 401/403 (42501 permission denied) or 404 after a schema reload — NEVER 25006 again.

### A3. 037 BEFORE checks (read-only) — keep the output, the rollback needs the first one

```sql
SELECT c.relrowsecurity, c.relforcerowsecurity
  FROM pg_class c
 WHERE c.oid = 'public.user_events'::regclass;

SELECT policyname, permissive, cmd, roles, qual, with_check
  FROM pg_policies
 WHERE schemaname = 'public' AND tablename = 'user_events';

SELECT p.proname, p.proacl
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'public'
   AND p.proname IN ('delete_user_cascade', 'increment_lifetime_comparisons',
                     'resolve_referral_code', 'home_savings_aggregate');
```

THE RULE (from 037's header): if `relrowsecurity` is ALREADY true, or `pg_policies` lists ANY policy other than `events_insert` / `events_select`, or either of those two differs from `010_*.sql` (`events_insert PERMISSIVE INSERT {public} with_check ((auth.uid() = user_id) OR (user_id IS NULL))`, `events_select PERMISSIVE SELECT {public} qual (auth.uid() = user_id)`), then 037 does NOT close CR-SECURITY-02 — the anon read comes from a policy, and the fix is a follow-up migration that drops or re-creates the offending policies BY NAME from that output. Apply 037 anyway (its function revokes are independent), and tell me what the policies query showed.

### A4. Apply `migrations/037_security_definer_grants_and_rls.sql` (whole file). 037 no longer depends on 035/036 (statement 4 is guarded). Re-run the third A3 query: `delete_user_cascade` and `increment_lifetime_comparisons` must show a `service_role=X/...` entry and NO `anon=`, NO `authenticated=`, NO bare `=X/...` entry; no `home_savings_aggregate` row is expected until 036 is applied. Live proof:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$SUPABASE_URL/rest/v1/rpc/delete_user_cascade" -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY" -H "Content-Type: application/json" -d '{"target_user_id": "00000000-0000-0000-0000-000000000000"}'
```

Must be 401/403 (42501), never 200/204. Then the anon-key `count=exact` over `user_events` must return 0 rows (only if the A3 rule said 037 closes CR-SECURITY-02).

### A5. Apply `migrations/038_users_consent_capture.sql` (additive, nullable, no backfill). Verify:

```sql
SELECT column_name, data_type FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'users'
   AND column_name IN ('terms_accepted_at', 'terms_version', 'age_attested_at');
```

Three rows expected. 036 stays unapplied until `ENABLE_HOME_SAVINGS_AGGREGATE` is readied (then re-run 037 once, it is idempotent). 039 stays reserved for the M13-29 RLS migration.

## B. Supabase Auth — Redirect URL allow-list

Dashboard → Authentication → URL Configuration → Redirect URLs → add `qaren://reset-password`. Without it GoTrue silently falls back to the Site URL and the W3-6 deep link never reaches the app. Precondition for `ENABLE_PASSWORD_RESET_DEEP_LINK`.

## C. Railway flags (after the OTA is on phones, one flip per canary, read the named log line before the next)

Done by me if the Railway CLI on this box is linked; otherwise, in this order:

1. `ENABLE_BRIGHTDATA_BUDGET_GATE=true` on `web` AND `price-warmer` — no precondition, stops unbudgeted Bright Data spend today (the gated path applies the 4,500/month budget row). A variable change redeploys the service.
2. `ENABLE_CONSENT_PERSIST=true` on `web` — ONLY after A5 (038) is applied. Canary: a registration from a phone on the new OTA writes the three columns.
3. `ENABLE_LOGOUT_UPSTREAM_REVOCATION=true` on `web` — after the OTA (the client half is R-CLIENT's W1-4d; the backend now revokes by the access token regardless). Do NOT combine with `ENABLE_PROXY_AWARE_RATELIMIT` until W1-9e lands. Canary: `[auth]` lines on logout; `/auth/logout` 5xx rate stays 0.
4. `ENABLE_PASSWORD_RESET_DEEP_LINK=true` on `web` — after B and the OTA. Canary: the first `[auth] password recovery rejected: amr=` line tells us the live AMR claim shape of a recovery session (unmeasured until then).
5. `ENABLE_CONSENT_REQUIRED=true` on `web` — LAST: after 2 and the OTA, and after `scripts/bundle_d_prod_smoke.py` probes 5, 10, 11 are given the three consent fields (or declared expected-red). Canary: the count of `TERMS_ACCEPTANCE_REQUIRED` 400s on `/register` + `/social-login`; any non-zero rate means phones without the OTA.

Still dark by design until a product call: `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (W4-2; needs your call on the "(converted from USD)" rendering — see the decision note), `ENABLE_PRESCORING_SHOWABLE_GUARD` (W4-3; flip only after `PO-RECORDED-MEASURED-04b`), `ENABLE_HONEST_PARTIAL_SCORING` (W4-4; not together with `ENABLE_FULL_STREAM_DEADLINE` until the SSE stash lands; after the FE copy row), `ENABLE_PRICE_PARSE_OFFLOAD` (W0 step 2, after `ENABLE_OFFLOOP_DNS_RESOLVE` alone has canaried).

## D. Credentials — yours only

Rotate the eight leaked keys (Supabase service key, OpenAI, Bright Data, Cloudflare token, Upstash, Serper, Firecrawl, Scrape.do / Zyte / YouTube / Nasser guest token, Sentry DSN — the 2026-09-07 dump list) and then `ADMIN_API_KEY` (in public git history since June). Set the new values in Railway yourself; I never handle secret values. `EXPO_TOKEN` as a repo secret (W3-13's channel-freshness CI job stays skipped until then).

## E. Native build (not an OTA)

W3-7's privacy manifest, `RECORD_AUDIO` block and the `react-native-gesture-handler` uninstall need `eas build` (plus the icon artwork). Not blocking anything above.
