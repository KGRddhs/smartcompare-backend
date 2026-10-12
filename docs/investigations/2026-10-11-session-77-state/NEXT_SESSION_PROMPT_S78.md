# Session 78 resume prompt (MYEZ: App Review watch, PostHog analytics, post-approval OTA)

Paste this to start session 78. Run it under /synack-build-orchestrator: the orchestrator plans and gates, and every workflow agent runs on Opus.

**Model check.** Before the first launch, grep `CLAUDE_CODE_SUBAGENT_MODEL` in `~/.claude/settings.json`. Then confirm `"model":"claude-opus-5-5"` in the first agent transcript of every launch.

**Weekly budget.** All models was at 87 % at the close (~05:00 AST on 2026-10-12); Fable was at 100 %. It resets 2026-10-14 at 15:59 AST. Run ONE workflow at a time until then, and check `get_usage` before each launch.

## Step 0 — housekeeping first

1. **Merge the session-77 docs PR** (branch `docs/session-77-state`; it carries this file, the ledger and the CLAUDE.md pointer) before anything else. Use `docs/investigations/2026-09-26-session-68-state/scripts/pr_rest.py merge <n>`, never `watch`, which auto-merges on green.
2. **Bring main into the PostHog branch** before its PR: `feature/s77-posthog-server` was cut from 18121839. After merging main into a unit branch, run the FULL jest suite (for client units) and the LF proof: a detached checkout with `core.autocrlf=false`, the unit set re-run. These are S76 rules.
3. **Worktree cleanup** (read-only check done at the close):
   - Unlink the junctions in `sc-s76-domain` and `sc-s76-u10` FIRST with `cmd /c rmdir <wt>\SmartCompareApp\node_modules`, run from PowerShell. Check that `sc-s70-u4b/SmartCompareApp/node_modules/@babel/core` still exists.
   - Then `git worktree remove` those two, plus `sc-s77-catalog` and `sc-s77-legal` (both merged).
   - KEEP `sc-s70-u4b` (the only real node_modules) and `sc-s77-posthog`.

## State at the close of session 77 (2026-10-12 ~05:00 AST)

**main = 18121839.** Session 77 merged:
- **#350 REDIS-OFFLOOP:** the synchronous Upstash catalog reads moved off the event loop, behind `ENABLE_PRICE_PATH_REDIS_OFFLOOP`.
- **#351 LEGAL-DISCLOSURE:** the OpenAI data-sharing exchange is disclosed; Gmail is named as the mailbox for support@ and privacy@; the landing claims are corrected.

**App Store**
- MYEZ 1.0.0 (build 2) was SUBMITTED for review on 2026-10-12 at 01:08 AST. Status: Waiting for Review. Release is MANUAL.
- Build 2 = EAS build a3c3e8b5 (submission 36725e1d). Its app source equals eed0f628, unchanged through 7b224c5a.
- No demo account was given: "Sign-in required" is unticked; the notes give self sign-up steps and "demo credentials on request at support@getmyez.com". The exact text is `REVIEW_NOTES_SUBMITTED_S77.txt`.
- 5 screenshots: the 1206x2622 "iPhone with Dynamic Island (medium)" set. Renderer: `scripts/render_frames.py`; captures in `Documents/AI/_s77_screenshots/raw`.
- App Privacy is PUBLISHED, at the owner's yes: 13 data types, Privacy Policy URL https://getmyez.com/privacy.html. The Support URL is https://getmyez.com/support.
- TestFlight group "MYEZ Internal" holds Hussain Aseeri and Ahmed Jameel (ASC Admin).
- The production EAS channel has NEVER received an update; the reviewer runs build 2's embedded JS.

**Domain**
- getmyez.com and www serve `qaren-landing`; www returns a 301 to the apex. The AASA, /privacy.html, /support and /terms.html return 200.
- pause.getmyez.com is attached to getmyez/web. Its HTTPS was 000 at 22:34 (certificate pending) and has not been verified since.

**Legal (live, verified 02:40)**
- The API (EN and `?lang=ar`) and getmyez.com/privacy.html carry:
  - the general not-sold promise, with the OpenAI programme as the only exception;
  - the "free use of its service" exchange;
  - Google (Gmail) as mailbox provider;
  - email retention, and email surviving account deletion.
- The terms carry the same disclosure.
- The effective date is still October 11, 2026 (ruling RL1). The FIRST legal change after release must bump all twelve anchors, including `consent.ts` TERMS_VERSION, and publish the prior version.

**Production flags on `web`** (from the ledger; agents never read Railway variables, and the reads are denied anyway):
- **ON:** `ENABLE_PRICE_PATH_REDIS_OFFLOOP`, `ENABLE_OFFLOOP_DNS_RESOLVE`, `ENABLE_PRICE_PARSE_OFFLOAD`. Loop lag went from 9.7-26 s to about 3 s. /health misses: 0 in c1, 2 in s2b.
- **Rolled back:** `ENABLE_SUPABASE_CLIENT_REUSE` (canary s3 was worse).
- **Held:** `ENABLE_UPSTASH_BOUNDED_TRANSPORT`. Its 2.0 s default is below the 2.24 s large-catalog GET. It is read at import, so it needs its own window WITH a redeploy, plus a knob ruling (about 5 s). On that redeploy, read the OLD deployment's log for the owed `[DRAIN]` lines.
- **From earlier sessions:** the U13 trio and `ENABLE_PHASE2_RESIDUAL_GUARD` / `ENABLE_UNIFIED_SEARCH_BOUND` are ON.
- **Stay OFF:** `ENABLE_SYNC_DB_OFFLOAD`, `ENABLE_ASYNC_REDIS_OFFLOAD` and `ENABLE_COMPARISON_ID_ECHO`, until all four W0 flags (REUSE and UPSTASH included) are ACTIVE and stable. `ENABLE_PARSE_PRESPLIT` and `ENABLE_PARSE_BUDGET` also stay OFF; they are the owner's flips.

**Compare quality is still poor.** Every S77 canary was RESULT FAIL; the best was s2b with ready 2 of 3. Most pairs end as hard-cap PARTIALs (`no_pros` or `no_spec_rows` at about 30.4 s), even after the loop fix. A diagnosis unit is owed: where do the 30 s go now that loop lag is about 3 s?

**PostHog (in flight).** Spec, review and rulings are in `specs/`:
- `POSTHOG_UNIT_SPEC.md`
- `POSTHOG_SPEC_REVIEW.md` (PR1-PR19)
- `RULINGS_S77_POSTHOG.md` (PH1-PH11)
- `RED_GATE_S77_POSTHOG_B.md` (PG1-PG12)
- `RULINGS_S77_POSTHOG_B_FIX1.md` (PF1-PF11)

The units run B (backend), then A (client), then L (legal). All stay dark until the owner's keys exist and their flags are flipped.

**Unit B** (worktree `sc-s77-posthog`, branch `feature/s77-posthog-server`):
- GREEN and adversary are done (wf_acc1290f-59a).
- GREEN gates: RED 139/139; comm gate over 149 files, branch-only-NEW empty in both directions; U8 fill-in round trip byte-identical; ruff, py_compile and the lock reproduce.
- **Adversary: NOT READY.**
  - F1 MAJOR: `save_preferences` and the cohort seed overwrite `users.preferences` and erase `analytics_enabled`, so the opt-out is lost.
  - Also 10 MINOR findings and 5 surviving mutants.
- Saved as WIP commit `d3a7dc9e`: pushed, NO PR, DO NOT MERGE.
- Reports: `runs/posthog_b_green_wf_acc1290f.md` and `runs/posthog_b/`.

## Remaining, in order

### 1. Watch App Review (up to 48 h from 01:08 on 2026-10-12)

**Every day until approval:**
- the OpenAI balance (or auto-recharge on);
- `/health`;
- the Gmail inbox that support@getmyez.com forwards to. Apple may ask there for demo credentials.

**If Apple asks for a demo account (2.1)**, follow audit finding F06 exactly (`runs/presubmission_audit_wf_84625002.json`):
1. The owner creates two accounts in the app (account creation is prohibited for Claude).
2. The owner onboards both accounts once.
3. Run queries A and B (read-only), then C: `UPDATE public.users SET subscription_tier='premium' WHERE lower(email) IN (...) RETURNING ...`. Expect 2 rows.
4. Never run a compare on those accounts before the reviewer does.
5. Re-tick "Sign-in required" and fill the username and password in App Review Information. The owner types them, never into chat.
6. Never write "premium" in the notes.
7. The owner replies in the Resolution Center.

Deleting an account resets its tier.

**Likely rejection causes and fixes:**
- **Google Sign-In broken on build 2 (2.1).** It is unverified and always shown. Fix: hide the button via an OTA, which needs the OTA gates below, then resubmit.
- **Login wall (5.1.1(v)).** Fix: guest mode (a backend flag plus a client change).
- **The required "How did you hear about us" onboarding step (audit C7).** Fix: make it skippable.
- **Forgot-password landing on the API host (audit C2).** Fix: `ENABLE_PASSWORD_RESET_DEEP_LINK`, plus `qaren://reset-password` on the Supabase Redirect-URL allow-list (owner).

**On approval:** the owner releases manually, after the "Before you press Release" items in `OWNER_ACTIONS_S77.md`. Only after release may anything go to the `production` EAS branch.

### 2. Fix round 1 of PostHog unit B

Follow `specs/RULINGS_S77_POSTHOG_B_FIX1.md` (PF1-PF11):
- pins first, red against `d3a7dc9e`, then code;
- the comm set over the same 149 files, plus the cohort and preference suites;
- a final adversary on the exact bytes must return READY.

**Never rewrite the pushed branch.** Add the fix as new commits and SQUASH-MERGE the PR, or cut `feature/s77-posthog-server-v2` from main and `git merge --squash` into it. No force-push in any form (`--force`, `-f`, `--force-with-lease`, `+ref`).

Then: open the PR with `pr_rest.py create`, bind it, read CI with ccd_pr `get_status` (no polling), and merge on green. B is inert: no key, flags OFF.

### 3. PostHog unit A (client), cut from the main that contains B

- **Worktree:** one with its OWN real node_modules (no junction).
- **Install:** the orchestrator installs `posthog-react-native` with `--save-exact`, at a version at least 14 days old, using `npm install --before=<date-14d>` (PR15).
- **Fingerprint gate (PR9):** the fingerprint at build 2's source commit (eed0f628; EAS build a3c3e8b5's recorded fingerprint, or `npx @expo/fingerprint` at that commit) must equal the branch's after the install.
- **Implement:**
  - PR1, the PR2 client half, PR6, PR10 and PR11;
  - the "Share usage analytics" switch (PH2);
  - the 12 `ph-no-capture` screens.
- **Tests:** run the FULL jest suite.
- **Legal row:** in the same PR, add the client module and probe to the posthog `processors.json` row (PR7).
- **Inert at merge:** unit A ships with no `EXPO_PUBLIC_POSTHOG_KEY` in EAS production.

### 4. PostHog unit L (legal)

Flip the fill-in flag `ENABLE_POSTHOG_SERVER_CAPTURE` from "off" to "on", and add the PostHog text through the U8 machinery, per PR8 and PH1-PH6:
- s3.2 and s3.4;
- s5;
- s7: the EU;
- s8: 1 year;
- s9: deletion is requested, then completed on PostHog's schedule;
- s14: the reset semantics.

**Date (PH5):** keep October 11, 2026 if L merges BEFORE release; if after, bump all twelve anchors, and the `consent.ts` bump rides the next OTA.

**Then:** redeploy the landing from a clean checkout of the merge SHA.

### 5. PostHog activation

Every step is owner-gated and needs the owner's explicit yes for each flag flip. Follow the PR17 order:
1. L is live on the API and the landing.
2. The app is approved and released.
3. The owner creates the PostHog EU project:
   - "Discard client IP data" ON;
   - exception autocapture OFF;
   - DPA signed;
   - on the free plan (1-year retention), or the s8 text changes first (PH3).
4. The owner confirms the PUBLISHED ASC App Privacy label ticks Analytics for Product Interaction, Search History and User ID. If it does not, edit and republish; that is an attestation, so the owner's yes is needed.
5. `ENABLE_SEARCH_LOG_TRUTH=true` is confirmed on web (PR4).
6. B2 first (it needs L live, PF11): `POSTHOG_PERSONAL_API_KEY` (person:write), `POSTHOG_PROJECT_ID`, then `ENABLE_POSTHOG_PERSON_DELETE=true`.
7. `POSTHOG_PROJECT_API_KEY`. `POSTHOG_HOST` defaults to EU. A key change needs a restart.
8. `ENABLE_POSTHOG_SERVER_CAPTURE=true`. Then:
   - one own-account compare shows `server_compare_completed`, with no `$ip` and no IP-derived `$geoip_city_*` or `$geoip_country_*` property (`$geoip_disable: true` is expected);
   - watch `/health loop_lag_max_60s_ms` for a regression;
   - verify `persons/bulk_delete` once live: the owner creates and deletes one test account, and the log shows the counts.
9. Preview QA with a SEPARATE test project key, on an internal build whose fingerprint equals build 2's (PR9).
10. **PR18:** the owner lists the NAMES of the EAS production environment variables. Only `EXPO_PUBLIC_POSTHOG_KEY` (and optionally `EXPO_PUBLIC_POSTHOG_HOST`) may be new. Then create `EXPO_PUBLIC_POSTHOG_KEY`; not earlier, because any production update after its creation carries the client.
11. The production OTA that turns the client on.

### 6. Post-approval OTA (the UI fixes): SEPARATE from PostHog activation

It ships after approval and release, with unit A merged but inert: no PostHog key in EAS production yet.

**Gates for EVERY production OTA**, this one included:
- **(a) Fingerprint:** the branch fingerprint equals build 2's (a3c3e8b5 / eed0f628).
- **(b) Preview first:** the same commit goes to `preview` first, on an internal build with an equal fingerprint, and is checked on a device.
- **(c) Environment names:** the owner lists the EAS production variable NAMES; nothing new appears.
- **(d) No `expo.version` bump.**
- **(e) Publish:** `npm ls`, then `eas update --branch production --environment production`, then two cold launches.

**Contents** (each item is its own unit under the harness):
- **The 9 visible UI bugs:**
  - the "N/A · N/A" brand line;
  - the duplicate "(converted from USD)";
  - dimension captions that repeat their labels, and a duplicate Reviews row;
  - the stuck MYEZ logo overlay;
  - "+ N/A vs N/A projection";
  - internal scores in the pros;
  - "1 dimensions", the empty specs table and the "CONCENTRATI ON" wrap;
  - the History vs Home month mismatch;
  - missing images, the "OTHER" category tag and lowercase typed names.
- **Onboarding and copy:**
  - the M6 onboarding copy ("Your name. Your email. Not now, not ever." heading);
  - make onboarding step 11 (attribution, "how did you hear") skippable (audit C7);
  - remove or soften the "25+ retailers" strings in EN and AR (`en.json` ~279/285/544/749 and the AR twins; audit C6).
- **Consent sheet:** the free-use sentence, which closes legal limit L1. That means `AI_CONSENT_VERSION` 3 plus the sha-fence re-pin, and the `consent.ts` TERMS_VERSION bump if L merged after release (PH5).
- **`LANDING_BASE_URL`:** move it to getmyez.com, together with the `legalScreenLang.u8` pin.

## Follow-ups (not blocking)

**Security**
- A migration for the three anon-readable SECURITY DEFINER views: `vw_cohort_match_rate`, `vw_cohort_persona_distribution`, `vw_cohort_feedback_lift` (the anon key gets 200 today).
- Sign in with Apple token revocation on account deletion (U11 = A, after launch; audit F14).
- Fix-soon items from `LEGAL_EXPOSURE_REVIEW_S77.md` §3:
  - Server-side consent record plus "Withdraw AI permission" in the app (PR body L2).
  - Denial-of-wallet: a global daily compare ceiling and a disposable-email blocklist. Do NOT turn on `ENABLE_PROXY_AWARE_RATELIMIT`.
  - Lockout DoS: key the lockout on IP + email.
  - "No fixed period" retention: migration 044 + a cron, and an HMAC email hash.
  - The ToS s6 health paragraph.
  - A Terms v2 pack in one OTA window, with the TERMS_VERSION bump.
  - In-app absolutes: "never paid by sellers", "25+ retailers", "Real buys".
  - robots.txt honoured in code.

**Load and quality**
- The compare-quality diagnosis unit (above).
- The remaining unflagged on-loop small Upstash calls (about 3 s residual lag).
- The UPSTASH knob ruling plus a redeploy window.
- A SUPABASE_CLIENT_REUSE re-test.
- A small-call lane or single-flight memo for the redis-offloop pool.
- Second-product price coverage.
- The six REDIS-OFFLOOP final-adversary minors (ledger 22:16).
- Supabase showed 65.1 % request success (68 API-gateway warnings, ledger 19:32).

**Legal minors**
- The landing lede "prices from online retailers across the region".
- README:52 vs :141, and the Android assetlinks placeholder.
- The AR P5G conditional style.
- The terms s8 licence extended to OpenAI's own training use (owner Q2).
- The robots.txt UA string still carries a personal Gmail contact (L5).
- The ASC label lists 5 "Other Purposes" rows against 3 in the manifest.
- Drop the Apple FULL_NAME scope.
- Confirm `ENABLE_ZYTE_RENDER` is off, or name Zyte.
- `cf-ipcountry`.
- osBuildId in the fingerprint.
- The fixed password `bundle_d_prod_smoke` uses for the prod accounts it creates.
- The U8 minors from S76:
  - AR-P1 presence pin to s9;
  - the UF14 AR construction into `ug12_ar.terms_retired`;
  - the AR s9 qualifier;
  - privacy s3.6 naming the compiled de-identified data;
  - paraphrase gaps Z1-Z4.

**Before release (older owed items)**
- The UB-R13 on-device consent-sheet check at the smallest iPhone and at AX sizes.
- The S75 native review of the AR consent sentence (`2026-10-09-session-75-state/NATIVE_REVIEW_S75.md`).
- Mobile Sentry: zero react-native events have ever been observed (S70/S72). Verify reporting works.

**CLAUDE.md fixes (edit in place, dated; measure in code first)**
- The W0-2 row says `http2=True`, but `database_service.py` builds the client with `http2=False`.
- The `ENABLE_ASYNC_REDIS_OFFLOAD` row's half-open hard precondition is resolved by #115 (`api_budget_service.py` ~546-580).

**Other**
- SYNACKSOFTWARE: move the Apple membership after the D-U-N-S arrives.

## Owner items

See `OWNER_ACTIONS_S77.md`.

## Standing rules (sessions 76-77)

**Owner-only actions.** The auto-mode classifier refuses these even in bypass mode, and it treats retries as bypass attempts:
- DNS, domain and certificate changes (Railway domain delete, Cloudflare DNS pages);
- ASC user invites (Permission Grant).

Attestations (ASC App Privacy Publish) need the owner's explicit yes in chat. Hand all of these to the owner with exact clicks.

**Railway variables.** `railway variables` (any read) and copying `.env` are refused by the deny rules. Production flag state comes from the ledger. Tests are credential-free; worktrees need no `.env`.

**Production flag flips.** A flip needs the owner's explicit yes in chat for that specific flag. Run it in the owner's Terminal panel only with that yes, one flip per canary window. Never use another tool to run a command a deny rule blocks without that yes.

**Canary discipline.** Fix the canary pairs BEFORE running: never compared before, category-matched to the comparison run. Roll back on any regression in ready count, /health misses or loop lag.

**PR helper.** `docs/investigations/2026-09-26-session-68-state/scripts/pr_rest.py`: never `watch` a PR that must not auto-merge; use `status`. `scripts/pr_body.py get|set` (in this folder) edits a PR description.

**CI.** Frontend jest is BLOCKING. A client pin that a backend or legal unit changes is arbitrated by CI's frontend-tests job.

**New external hosts.** Any new external host in `app/services` needs a `processors.json` row (T7b). When the policy text comes later, use the U8 gate: a fill-in flag recorded "off" plus a row with `gate_flag` (PG2).

**Supply chain.** Pin new dependencies to a release at least 14 days old (posthog 7.60.1, from 2026-09-25).

**Landing redeploy.** Run it from a clean detached checkout of the merge SHA; `railway up landing --path-as-root -s qaren-landing -d` works from Bash.

**Reference files.** The ledger is `ledger.md` in this folder: the authoritative per-step record. The legal exposure review is `LEGAL_EXPOSURE_REVIEW_S77.md`. The handoff critic's findings are applied here (`runs/handoff_critic_s77.md`).
