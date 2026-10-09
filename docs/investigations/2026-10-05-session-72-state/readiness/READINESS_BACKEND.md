# MYEZ launch readiness: backend, legal, operations and App Store Connect listing (finder BACKEND)

Read-only audit of main `845ece15` (worktree `sc-s71-u13`, `git status` clean at 13:47 AST on 2026-10-05). Written 2026-10-05 ~14:05 AST.
Sources: the session-69 runbook (sections 2, 3, 4, 6), the session-69 state doc and its 82 verified findings, the session-71 state (section 0), ledger, Step 6 plan, implementation plan and PR bodies, CLAUDE.md (ship-blockers + SESSION 71 block), open_issues.json (97 issues). **The repo at 845ece15 wins over every document.** Production values are quoted from the ledger / CLAUDE.md with their date, or from the orchestrator's 2026-10-05 measurements; nothing in production was measured by this agent (no network, no Railway, no Supabase).

## 0. The truth in one paragraph

The launch is **not close on the backend/legal side**. The code that App Review exercises is in place and U13 is live, but five things block submission outright, and none of them is a code change Claude can make alone. (1) OpenAI is unfunded, so every compare fails. (2) The privacy policy and terms are still the 2026-03-26 DRAFT template. They say "Qaren", promise an AI-sharing opt-out that routes nothing, and mention "Premium subscribers". The app links them, so does the ASC listing, and they sit in 4 landing pages plus 2 backend routes. (3) There are no screenshots. (4) There is no ASC record, signing or API key. (5) There is no premium demo account. The critical path is **Ahmed's 8 legal inputs + D3 + D5 → Claude U8 → landing redeploy**. In parallel: OpenAI funding → canary → warm-up → screenshots, and the Hussain session → ASC record → U10 → builds. Four findings here are new or sharpened since session 71:
- **BE-01:** the canary script `verify_after_credits.py` passes on a degraded verdict. It is weaker than the runbook's pass rule.
- **BE-02:** every anonymous recipe in the runbook (the canary curl and the warm-up) now returns 401 under U13.
- **BE-03:** the listing and the review notes claim estimated prices are labelled. The client deliberately never labels them.
- **BE-04:** Google Sign-In has been recorded as failing since session 54, and nothing has verified it since, while the review notes advertise it.

Supabase auto-pause has also become more urgent. Production has had zero mobile traffic for 38 h, so there is no DB activity. `/health` never touches the DB. With U13 on, a Supabase outage is a total compare outage.

## 1. Rows (status at 845ece15)

Schema: id | title | status | launch_severity | evidence | next_action. DONE rows need proof in code or a merged PR.

### 1a. Runbook section 2 (non-client rows)

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| RB-1 | OpenAI unfunded: every compare path fails | OPEN-AHMED | blocker | orchestrator 2026-10-05: Sentry python-fastapi 429 `credit_balance_exhausted` last seen 2026-10-03; ledger 2026-10-03 05:50 | Ahmed: prepaid low-cap top-up, NEW key on `web` from his terminal, revoke old key; then the canary (after BE-01) |
| RB-2 | ToS still promises "Premium subscribers earn 10 per conversion" (no IAP exists) | OPEN-CLAUDE (in U8) | high | app/legal/terms_of_service.md:85; landing/terms.html:263 | Claude: drop it in U8 (paywall half DONE #255, client) |
| RB-3 | Privacy/Terms are the DRAFT template of 2026-03-26, say Qaren, served in-app + landing EN/AR | OPEN-BOTH | blocker | privacy_policy.md:3,5,7,11,95; terms_of_service.md:3,5,7,98; legal_routes.py:30,47 (`last_updated` 2026-03-26); landing/privacy.html:195-196,199,288; landing/terms.html:184-185,275; landing/ar/privacy.html + ar/terms.html each carry the `draft-notice` class (3 hits incl. CSS) and the 2026 date line (:189 / :175) | Ahmed: 8 legal inputs + D3 + D5 (+ #296 window); Claude: U8; Ahmed: landing redeploy `railway up landing --path-as-root -s qaren-landing -d` |
| RB-5 | No App Store screenshots | OPEN-AHMED | blocker | orchestrator 2026-10-05: none exist; runbook §3 E3 | after OpenAI + warm-up: 6 real screens on an iPhone; Claude resizes/strips alpha |
| RB-6 | No ASC record, distribution profile or ASC API key (Individual team, Hussain) | OPEN-AHMED | blocker | orchestrator 2026-10-05: no ASC record, no production build; SmartCompareApp/eas.json:23-25 `"submit": {"production": {}}` | Ahmed + Hussain: §3 C1-C4 in one sitting (1-2 h) |
| RB-7 | AI disclosure: consent sheet shipped; the opt-out toggle, policy §11 and `select_client_for_user` still false promises | OPEN-BOTH | high | #274 merged (client); app/services/openai_service.py:82 defined, 0 callers (#266); SmartCompareApp/src/screens/ProfileScreen.tsx:140 toggle still live; privacy_policy.md:80-88 opt-out | Ahmed: D3 (recommended A: OpenAI data sharing OFF); Claude: U3b + U8 §11 |
| RB-8 | Login-gated app needs a premium demo account | OPEN-AHMED | blocker | SmartCompareApp/App.tsx:363-368 (auth stack only); app/services/usage_service.py:138-148 | Ahmed: see §2 demo-account recipe (20-30 min), plus a spare (BE-06) |
| RB-11 | Policy omits demographics, device-fingerprint hash, country, push token; processor list incomplete; no equal-protection clause or named controller | OPEN-CLAUDE (in U8) | high | privacy_policy.md:16-23, :41 (lists only Railway, Supabase, OpenAI, Serper, Upstash, Sentry) | Claude in U8: add Bright Data, Firecrawl, Scrape.do, Expo push, Apple/Google sign-in, Cloudflare and the data rows |
| RB-12 | qaren.app dead (522): universal links, referral/share links, ASC URL plan | OPEN-AHMED (hand-off page DONE #273; landing redeployed 2026-09-30 per CLAUDE.md S70) | high | orchestrator: still 522 at last measurement; app/services/referral_service.py:50 `APP_BASE_URL = "https://qaren.app"`; :348 link also carries an empty token (#272); SmartCompareApp/app.json:24 `applinks:qaren.app` | Ahmed: attach qaren.app to `qaren-landing` + fix Cloudflare + verify AASA (45 min); fallback = Claude env override of APP_BASE_URL |
| RB-13 | Verdicts never cached: OpenAI must stay funded and pairs re-warmed daily | OPEN-BOTH | high | app/services/cache_service.py:771,777 `get/set_comparison_cache` have no caller; runbook §3 E2 recipe is anonymous, so it returns 401 under U13 (BE-02) | Claude: authenticated warm-up script (BE-02); Ahmed: run it within 24 h of submission and daily in review |
| RB-14 | 24 s event-loop stall on the single worker; W0 load flags unset | OPEN-AHMED | medium | railway.json:7 one uvicorn process, no `--workers`; ledger 2026-10-03 08:50 `WEB_CONCURRENCY` absent, 1 replica; s69 BP-05 (2026-09-29) W0 flags absent, no later flip recorded | Ahmed after funding: CLAUDE.md W0 order, one canary each (§3) |
| RB-17 | ASC description/listing claims | OPEN-BOTH | medium | runbook §6 against code: BE-03, BE-08, BE-09, BE-04; lengths all inside limits (listing_lengths.txt) | Claude: correct §6 text; Ahmed: D11 approval |
| RB-18 | Checklist repointed to the inventory, May draft superseded | DONE | none | PR #271 (U9) | Ahmed fills ASC labels (CL-labels) |
| RB-19 | Publisher/controller identity D5 (seller = Hussain, docs say "Qaren") | OPEN-AHMED | high | privacy_policy.md:11; terms_of_service.md:41 "property of Qaren" | Ahmed: D5 (feeds U8 and the copyright string) |
| RB-20 | Age rating: 12+ gone, override to 13+ | OPEN-AHMED | medium | runbook D9 | Ahmed in ASC (15 min) |
| RB-22 | Supabase free-plan auto-pause; `/health` never touches the DB | OPEN-AHMED | high | app/main.py health_check returns loop-lag + pool only (#81 open); paused once (session 67); orchestrator 2026-10-05: 0 mobile-UA requests in 38 h, so no DB traffic; U13 stated limit L4 makes a Supabase outage a compare outage | Ahmed: paid plan (10-20 min); else a signed-in keep-alive |
| RB-23 | No app-level OpenAI dollar cap (D8) | OPEN-AHMED | medium | `MAX_MONTHLY_COST` dead config (s69 BP-08); the S71 plan says prepaid, low cap | Ahmed: prepaid + project budget + 50/80% alerts |
| RB-24 | OpenAI retry variables | DONE (variables); SSE tail open | low | CLAUDE.md SESSION 70: `OPENAI_MAX_RETRIES=1` + `OPENAI_FALLBACK_MAX_RETRIES=0` on `web` 2026-09-30 (deploy d88b5957); ledger 2026-10-03 08:24 `OPENAI_MAX_RETRIES` count 1 | optional later: `ENABLE_FULL_STREAM_DEADLINE` (the app uses REST by default) |
| RB-25 | D7 preflight breaker | OPEN-AHMED (Claude half DONE #258) | low | app/api/image_routes.py:310-316 (503 LLM_UNAVAILABLE) | keep OFF at Tier 1; use it as the incident lever |
| RB-26 | Post-launch OTA rule (`--branch production`) | OPEN-CLAUDE | low | CLAUDE.md EAS "Store-build rules" present; docs/runbooks/qaren-canary-onboarding.md:430 still says never `--branch production` | Claude: edit it in the PR that records the production build |
| RB-27 | APNs key in EAS credentials | OPEN-AHMED | medium | runbook §3 C4 | answer yes in `eas credentials` |
| RB-29 | No iOS build since 2026-07-04: preview first, then production | OPEN-AHMED | high | s69 state §1 EAS; orchestrator 2026-10-05: no production build | Ahmed: preview build + 2-iPhone smoke (incl. BE-04), then production |
| RB-31 | ar-SA listing | OPEN-BOTH | medium | the SA-06 draft exists only in appstore_findings_verified.json and predates the rename | Claude: redraft under the MYEZ Arabic name; native review; Ahmed D11 |
| RB-34 | Sign in with Apple tokens never revoked on deletion | OPEN-BOTH | low | grep `authorizationCode` / `auth/revoke`: 0 hits in app/ and SmartCompareApp/src | optional U11; needs a SIWA key (Hussain) |
| RB-35 | Search budget (Bright Data gate ON; Serper paid again; Firecrawl in-app lifetime counter) | OPEN-AHMED | medium | api_budget_service.py:34-58; CLAUDE.md: `ENABLE_BRIGHTDATA_BUDGET_GATE=true` on web + price-warmer since 2026-09-24; Serper 200 (S70); `web` `SERPER_LIFETIME_LIMIT=0` = Serper gate inert, bounded only by the paid balance | Ahmed: read `/api/v1/admin/costs` twice a day in launch week: `openai.cost_usd` is the month's list-price OpenAI spend over recorded comparisons (`openai.today_usd` for the day), `null` = nothing recorded yet, and the OpenAI billing page is the only figure that includes the free daily allowance; `/admin/stats/costs` is not an OpenAI figure (COST-METER #66, S75) |
| RB-36 | "One shared 10/min bucket" | MOOT | low | the premise was wrong (#299; ledger 2026-10-03 08:50); rate_limiter.py:52-59 keys on the TCP peer, which varies across Railway edge addresses | none for launch; the usage quota is the spend control |
| RB-37 | Railway paid plan/card; config-as-code deprecated 2026-12-01 | OPEN-AHMED | medium | railway.json (start command, healthcheck, `drainingSeconds: 30`), railway.warmer.json watchPatterns; CLAUDE.md deprecation note | Ahmed: confirm plan + card + cap; mirror into the dashboard before 2026-12-01 (20 min) |
| RB-38a EXPO-12 | `SENTRY_ALLOW_FAILURE` on the EAS production env | OPEN-AHMED | low | runbook §5 | optional |
| RB-38b PM-7 | Post-build privacy report / ITMS emails | OPEN-AHMED | low | runbook §3 D3 | read the ASC processing email |
| RB-38c LL-13/RT-11 | support@/privacy@/legal@qaren.app delivery unverified | OPEN-AHMED | medium | privacy_policy.md:93; terms_of_service.md:96; ContactUsScreen.tsx:218 mailto | Cloudflare Email Routing + 1 test mail each (15 min) |
| RB-38d LL-14 | Legal route English-only | OPEN-CLAUDE (in U8) | low | legal_routes.py:17-48 has no `lang` parameter | fold into U8 (`?lang=ar` + AR markdown) |
| RB-38e BLD-BP-04 | eas.json submit block (U10) | OPEN-BOTH | high | eas.json:23-25 | after the ascAppId: U10 |
| RB-38f BLD-BP-10 | `APP_STORE_URL` + Worker `idTBD` | OPEN-BOTH | low | version_routes.py:14 `APP_STORE_URL` env; cloudflare-workers/qaren-redirect/src/index.ts:29 `'idTBD'` | after approval (runbook §3 F) |
| RB-38g RT-10 | Password-reset email does not return to the app | OPEN-AHMED | low | `ENABLE_PASSWORD_RESET_DEEP_LINK` default OFF (auth_service.py `password_reset_deep_link_enabled`) | Supabase redirect `qaren://reset-password`; flag after the store build |
| RB-38h RT-13 | Bahrain-only pricing note | OPEN-AHMED | low | SmartCompareApp/src/services/api.ts:254,678,968 hard-code `bahrain` | keep the sentence in the review notes |
| RB-38i PRD-BP-02 | Key-suffix log line | DONE | none | PR #252; extraction_service.get_client logs `configured`/`missing` | none |
| RB-38j PRD-BP-12 | `DAILY_4O_CAP` per call | DONE | none | PR #285; model_router_service.py:48-59 | none (unset on web per ledger 08:24, so the 1M default applies) |
| RB-38l PM-8 / BLD-BP-08 / SA-09 | IP triggers in the inventory, CI gate list, EN keywords | DONE | none | PR #271 (docs/privacy-data-inventory.md:49; ci.yml:331-336; checklist) | none |
| RB-38k PRD-BP-13 | Stale breaker census comment | OPEN-CLAUDE | low | api_budget_service.py:941-951 says image_service is NOT wired; image_service.py:179 is wired | fix together with any D7 flip (and decide `record=False` for the image fallback) |

### 1b. Runbook section 3 (owner steps) and section 4 (units)

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| S3-A1.1 | Read OpenAI tier / TPM | OPEN-AHMED | high | runbook A1.1; the sizing runbook's Tier-1 ceiling is MODELLED | Ahmed: Settings → Limits (5 min) |
| S3-A1.5 | OpenAI data-sharing OFF (D3) + Chat Completions storage default | OPEN-AHMED | high | policy §11 depends on it (RB-7) | Ahmed: OpenAI data controls (5 min) |
| S3-A1.8 | Canary after funding | OPEN-BOTH | high | BE-01 (weak script), BE-02 (anonymous curl now 401) | Claude fixes the harness first; Ahmed runs it |
| S3-A1.9 | Revoke the old OpenAI key | OPEN-AHMED | medium | runbook A1.9 | after the new key works |
| S3-A3.3 | Optional `ENABLE_FULL_STREAM_DEADLINE` / `ENABLE_PREVERDICT_DISCONNECT_ABORT` | OPEN-AHMED | low | CLAUDE.md M13-W3 rows | after the W0 flags |
| S3-A3.5 | Keep-OFF list | DONE (no conflict) | none | the U13 trio is ON per ledger 2026-10-03 14:23, consistent with #195 ("flip both"); no keep-OFF flag is recorded as set | keep it |
| S3-B-legal | The 8 legal inputs (controller, CR, address, emails, response time, effective date, D3, lawyer/Beta) | OPEN-AHMED | blocker | runbook §3 B; the S71 plan's answers: 10/15 working days, no Beta label | Ahmed answers (30-45 min) → U8 |
| S3-B-D6 | Guest mode | OPEN-AHMED | low | U13 now refuses every anonymous paid call, so guest mode would mean reopening it | recommend "later" (the review notes explain the account features) |
| S3-B-D10 | Are re-engagement pushes marketing? | OPEN-AHMED | low | push_service.py ignores `notifications_enabled` (#264); ToS line 91 promises a per-type off switch | decide; U8 wording |
| S3-C3 | Optional SIWA key | OPEN-AHMED | low | needed only for U11 | in the Hussain session |
| S3-E1 | Demo account | OPEN-AHMED | blocker | = RB-8 | §2 recipe |
| S3-E5 | App Privacy labels in ASC | OPEN-BOTH | high | docs/privacy-data-inventory.md (last changed by #271); BE-12 IP caveat | Claude re-verifies against session 71 (no new collected type found in U13/U8b/U13c); Ahmed fills ASC |
| S3-E7 | Submit for Review | OPEN-AHMED | blocker | everything above | last |
| S3-F | After approval: `APP_STORE_URL`, Worker id, production-branch OTAs | OPEN-BOTH | low | = RB-38f, RB-26 | after approval |
| U1 | Key-suffix log | DONE | none | PR #252 | none |
| U3a / U3b | AI consent sheet / toggle + §11 + router | U3a DONE; U3b OPEN-CLAUDE (waits on D3) | high | PR #274; openai_service.py:82 (0 callers) | Claude U3b after D3 (M) |
| U7 | Error honesty (backend seam) | DONE | none | PR #258; image_routes.py:310-316 | none |
| U8 | Legal redraft | OPEN-CLAUDE (waits on inputs) | blocker | see RB-3 | Claude (L) after the 8 inputs + D3 + D5 |
| U8b / 043 | Full-erasure cascade | code DONE (#290); migration OPEN-AHMED | high | orchestrator 2026-10-05: 043 written, NOT applied; migrations/043:166-232 | Ahmed: PRECHECK grid → ONE_PASTE → POSTCHECK (→ BACKFILL) |
| U8c | Deletion 500 raised `from None` | DONE | none | PR #310; auth_routes.py:1181 | none |
| U9 | Docs + CI | DONE | none | PR #271 | none |
| U10 | eas.json submit block | OPEN-BOTH | high | eas.json:23-25 | after the ascAppId (XS) |
| U11 | SIWA revoke / census comment / guest mode | OPEN (optional) | low | = RB-34, RB-38k, S3-B-D6 | optional |
| U13 | Paid routes require a caller | DONE + ACTIVE | none | PR #297; text_routes.py:242,310,335,576,771,954,1375,1475; url_routes.py:273,310,331,368; image_routes.py:153; orchestrator 2026-10-05: anonymous `GET /text/compare` → 401 | the 24 h watch (U13-watch) |
| U13-watch | 24 h post-activation watch (mobile-UA 401 → refresh → retry) | OPEN-AHMED | medium | orchestrator 2026-10-05: 0 mobile-UA requests in 38 h, so the watch has measured nothing | testers open the app; then read the `[paid-auth]` histogram |
| T0b-B | gitleaks + CI secret scan + #315/#316/#317 | OPEN-CLAUDE | low | the repo is public, so a commit is a disclosure; dev tooling, no App Review effect | Phase B unit |

### 1c. CLAUDE.md "Routine before App Store production submission"

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| CL-icon | Real brand icon in the binary | DONE in code (binary pending) | none (backend) | PRs #279/#288/#307 | ships only with the production build |
| CL-legal | GCC legal redraft | OPEN-BOTH | blocker | = RB-3 | U8 |
| CL-pip | `pip-audit --strict` | DONE (CI-enforced) | low | .github/workflows/ci.yml:213-216 (blocking, no continue-on-error); ledger 2026-10-03 05:50 clean after #278 (pyjwt 2.15.1, urllib3 2.8.0) | re-read the CI result on the release commit; new CVEs can redden it any day |
| CL-npm | `npm audit --audit-level=high` triaged | OPEN-CLAUDE | low | ci.yml:226-228 report-only; last measured 35 (1 low/20 mod/13 high/1 crit, none direct) on 2026-09-29; NOT re-measured after the #279 SDK bumps | a triage note on the release commit (orchestrator runs npm) |
| CL-grep | QA static audit grep pack re-run | OPEN-CLAUDE | low | docs/plans/bundle-d-static-audit-pre-merge.txt last touched 2026-05-24 | re-run on the release commit; add a `Qaren` user-visible residue grep over app/legal and landing |
| CL-labels | ASC privacy labels against data flows | OPEN-BOTH | high | = S3-E5 | as above |

### 1d. Account deletion (5.1.1(v)) end to end

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| DEL-route | In-app deletion route | DONE | none | auth_routes.py:1165-1181 (`DELETE /api/v1/auth/account`, 1/min, `get_current_user`, type-only log, 500 `from None`); auth_service.py:1008-1023: cascade RPC → purge 5 Redis keys (:984-1005) → `admin.auth.admin.delete_user` | none (the flow satisfies the App Review check) |
| DEL-today | Erasure TODAY (025 body, 043 unapplied) | OPEN-AHMED | high | migrations/025:36-65: 7 table deletes + users UPDATE of 5 columns. Branch A (`users.id` FK to auth.users CASCADE): the auth delete removes the users row and its 4 FK-cascade tables; survivors = `admin_audit_log` rows incl. IP. Branch B (no FK): email, display_name, demographics, referral code, consent and attribution survive forever, as do the 014/028/029 tables. The branch is decided by PRECHECK §4 (live FK not visible via PostgREST, ledger 09:30). A NO-ACTION FK from another user's `user_events.comparison_id` would 500 the whole deletion (U8B spec C2; the same exposure in 025) | apply 043; until then the policy line "all associated data" is untrue in branch B |
| DEL-043 | What 043 changes | OPEN-AHMED | high | migrations/043:166-232 adds the 4 table deletes, detaches other users' rows pointing at the target's comparisons (fixes C2), nulls the audit IP, tombstones 25 users columns (keeps id/created_at/updated_at); guard + assert blocks in one transaction; 3 privacy defaults are open owner decisions (audit IP nulled, consent erased, free quota resets on re-register) | Ahmed: accept the defaults or ask for a 044 |
| #291 | Dashboard-deleted accounts leave comparisons (live share tokens), events, feedback, logs | OPEN-CLAUDE | low | issue body; rule until shipped: delete through the app or `delete_user_cascade` BEFORE the auth delete | 044 backfill after 043; matters for #303 cleanup |
| #294 | 043 guard misses NULLS-NOT-DISTINCT unique indexes / outgoing FKs / rules | OPEN-CLAUDE | low | issue body; PRECHECK §2/§3/§8 cover them by a human reading | read the PRECHECK grid carefully |
| #295 | Client keeps `@qaren_recent_searches` after deletion | OPEN-CLAUDE (client) | low | issue body | the policy must not claim device searches are deleted until fixed |
| #296 | No retention window for the audit rows of deleted accounts | OPEN-AHMED | medium | issue body; 043 keeps them forever, IP-free | Ahmed picks N days with the legal inputs; U8 states it |
| #318 | Purge = 5 sequential Upstash DELs inline; cascade + auth delete are bare sync calls | OPEN-CLAUDE | low | auth_service.py:997-1005, :1022; database_service.py:396 | one multi-key DEL + `run_db` (S) |

### 1e. U13 aftermath

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| #299 | Per-user limiter key on paid routes | OPEN-CLAUDE | low | rate_limiter.py:52-59 TCP-peer key; refusals never consume a bucket (U13 T19) | post-launch |
| #300 | Live/integration tests 401 with U13 on | OPEN-CLAUDE | low | issue body (13 files); not collected in CI | when the live tier is next used |
| #301 | Raw query/URL at INFO in logs | OPEN-CLAUDE | low (privacy) | text_routes.py:594, :1199; url_routes.py:294, :355 | hash + length (S); disclose logs in U8 |
| #302 | Multipart parse before the U13 guard | OPEN-CLAUDE | low | image_routes.py:153-157 (1-4 UploadFiles); U13 L5 | measure first; post-launch |
| #303 | Smoke accounts with a public password | OPEN-BOTH | low | scripts/bundle_d_prod_smoke.py:177-178, :308-322 (a new `bundle-d-smoke-<unix-ts>@qaren.app` per run) | §3 assessment: delete them (SQL, cascade first) + env password (S) |
| #304 | Whitespace-only `ADMIN_API_KEY` counts as configured | OPEN-CLAUDE | low | admin_routes.py:53-58 (no `strip()`); the live key is 64 chars (ledger 14:13) | one-line fix (XS) |

### 1f. Observability and privacy channels

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| RN-SENTRY | Mobile error reporting never observed working | OPEN-AHMED | high | orchestrator 2026-10-05: Sentry react-native 0 issues in 14 days, 0 mobile-UA requests in 38 h | testers open the app; force one test event in the preview build |
| #311 | Exception text still reaches Sentry (5 except-arms, ErrorHandlerMiddleware, cache logs, unscrubbed spans) | OPEN-CLAUDE | medium | error_handler.py:241,247 `f"Unhandled {type}: {exc}"` + `exc_info=True`; auth_routes.py:1192 `{e}`; sentry_service.py:175 (transactions), :311 traces 0.1 | unit before launch (S-M) |
| #286 | Scrub patterns: quadratic JWT regex, five unredacted shapes | OPEN-CLAUDE | low | issue body | fold into #311 |
| #287 | Model-router Redis read blocks the loop; empty error logs | OPEN-CLAUDE | low | issue body | post-launch |
| #293 | `delete_cached` logs Redis text at ERROR (5 per deletion during a Redis outage) | OPEN-CLAUDE | low | issue body; cache_service `delete_cached` | fold into #311 |
| #321 | Cap `exc_summary` input; one scrub pipeline | OPEN-CLAUDE | low | issue body | fold into #311 |

### 1g. New findings of this audit

| id | title | status | sev | evidence | next action |
|---|---|---|---|---|---|
| BE-01 | The canary script passes on a degraded verdict | OPEN-CLAUDE | high | docs/investigations/2026-09-29-session-69-state/verify_after_credits.py: the pass rule is `http==200 and success and has_verdict` (:67); `has_verdict = bool(verdict or overview.winner)` (:38), true on a degraded 200; `specs_rows` is computed (:37) but never asserted; it does not check `comparison.error`, specs, a price amount or pros/cons; it probes only `q=`, not the app's `product_a`/`product_b`; the stream probe passes on any event count (:68). The s69 state doc §2 claims the opposite | Claude: make it enforce runbook A1.8 before Ahmed funds OpenAI (S) |
| BE-02 | Every anonymous runbook recipe is now 401 | OPEN-CLAUDE | medium | runbook §3 A1.8 curl (lines 102-105) and §3 E2 / RT-6 "unauthenticated" warm-up; U13 active per ledger 14:23 | Claude: `scripts/review_warmup.py` (opt-in admin key through `railway run`, six pairs ×2, pacing ≤ 6/min, per-pair pass rule) + a runbook update (S) |
| BE-03 | Listing and review notes claim estimated prices are labelled; they never are | OPEN-CLAUDE | medium | SmartCompareApp/src/services/sourceMethod.ts:1-42 (rule: no "estimated" copy anywhere; the price pill is hidden when any price is estimated, ResultsContent.tsx:512); runbook §6 description "when a price is estimated … we say so", review notes "some are labelled estimated", promo "we always show how confident we are" | Claude: rewrite the §6 lines (an accurate-metadata risk under 2.3) |
| BE-04 | Google Sign-In last recorded FAILING on EAS preview; review notes advertise it | OPEN-BOTH | high | CLAUDE.md "Known Remaining Bugs" (session 54, not verified since); auth_service.py:795-806 TEMP `[SOCIAL_LOGIN_TRACE]`; runbook §6 review notes "Sign in with Apple and Google are also available" | Ahmed: test it in the preview build; if broken, hide the button for 1.0 or fix before the build; drop the claim otherwise |
| BE-05 | Supabase pause risk raised (fold into RB-22) | OPEN-AHMED | high | no DB traffic for 38 h, `/health` has no DB probe, U13 L4 | paid plan before submission |
| BE-06 | The reviewer can delete the only demo account (the notes tell them how) | OPEN-AHMED | medium | runbook §6 review notes line "Account deletion: Profile → … → Delete account"; auth_routes.py:1165 | keep a second premium account or a 20-minute recreate recipe; never in the repo |
| BE-07 | Supabase Auth email path unmeasured (Confirm-email setting, sender, templates still Qaren-branded?) | OPEN-AHMED | medium | ledger 2026-10-03 14:36 "Confirm-email setting unmeasured"; the reviewer may register a fresh account | Ahmed: read Auth → Providers/Email and the templates; use custom SMTP if confirmations are ON (NOT VERIFIED: the built-in sender's limits) |
| BE-08 | "Available in English and Arabic": verdict, spec and review prose stays English | OPEN-CLAUDE | low | `ENABLE_ARABIC_VERDICT_OUTPUT` dark with hard preconditions (#245); W4-14d #246 | listing wording: "Interface in English and Arabic; comparison write-ups in English" |
| BE-09 | "Prices from stores serving Bahrain, Saudi Arabia, UAE, Kuwait, Qatar and Oman" while results are Bahrain/BHD only | OPEN-CLAUDE | low | api.ts:254,678,968 `bahrain` | listing wording: "prices for the Bahrain market (BHD), from retailers across the GCC" |
| BE-10 | A converted price is labelled "Local listing" in the provenance pill | OPEN-CLAUDE (client lane) | low | sourceMethod.ts:24 `converted_usd: 'Local listing'` | client finder: verify against the "(converted from USD)" caption |
| BE-11 | TEMP social-login trace logs the token head at INFO on every social sign-in | OPEN-CLAUDE | low | auth_service.py:795-806 | remove after BE-04 is settled |
| BE-12 | Inventory says "IP not collected", but the Railway HTTP log stores caller IPs; INFO logs carry query text | OPEN-AHMED (legal) | low | docs/privacy-data-inventory.md:49; TRAFFIC_FINDING_2026-10-02.md (155 caller IPs from the Railway HTTP log); #301 | legal call in U8 (state the log retention) |
| BE-13 | Repo public; the GitHub plan check is held | OPEN-AHMED | low | ledger 2026-10-03 14:05; U13 L3 | decide; no App Review effect |
| BE-14 | The 20 permission deny rules are not applied | OPEN-AHMED | none | orchestrator 2026-10-05 | dev safety only: `apply_audit_batch_a.py --apply` |
| BE-15 | Price-warmer | MOOT for launch | none | cron_warm_price_cache.py:100,265 (exits unless `ENABLE_PRICE_CACHE_WARMER`); CLAUDE.md (2026-09-02) warmer false on `price-warmer`, no later flip recorded; railway.warmer.json watchPatterns | keep frozen (Ahmed: no scraper flips until approval) |
| BE-16 | The onboarding canary at 10% means most reviewers see the OLD onboarding | OPEN-BOTH (client lane) | medium | SmartCompareApp/src/config/features.ts:30 `CANARY_NEW_ONBOARDING_PERCENT = 100`; CLAUDE.md says set 10 before the production build | client finder: keep 100 for 1.0 or verify the old path in the preview build |
| #272 | Referral share link carries an empty token | OPEN-CLAUDE | medium | referral_service.py:348 | create the token in `create_invite` (S), with RB-12 |
| #264 | Push senders ignore `notifications_enabled` | OPEN-BOTH | low | push_service.py (no hit); ToS :91 | D10 + wording in U8 |
| #284 | Re-engagement reads a non-existent `users.governorate` | OPEN-CLAUDE | low | reengagement_service.py:178 | keep `ENABLE_REENGAGEMENT_PUSHES` as is; fix before enabling |

## 2. Demo account path for App Review (with U13 and metering on)

- **Credential path.** The reviewer signs in with email and password. The bearer passes `require_paid_route_user` (text_routes.py:310) on all six app routes. No admin key is involved. A bad or expired bearer gets 401 `BEARER_REJECTED`, then the axios interceptor refreshes. The camera's refresh path (U13c #313) exists only in the new binary, not on tester phones (OTA e2bde9c9).
- **Tier.** Set `users.subscription_tier = 'premium'`. That gives 10/day and 70/month (usage_service.py:144-148).
  - `consume_comparison_credit` (:331-385) never reads `subscription_expires_at`, so no expiry date is needed.
  - Text, Link and camera compares all draw on the same credits. Metering is ON per ledger 2026-10-03 14:23.
  - Failed compares are refunded. A day of review (a handful of compares) fits.
  - If the users-row read fails, the code falls back to free, which allows the 3 lifetime-free compares (:538-544).
- **Confirmed email.** Supabase "Confirm email" is unmeasured. Confirm the account in the dashboard if it is ON (BE-07).
- **Onboarding state.** `users.preferences_completed` must be true (App.tsx:223, :235, :310). Otherwise the reviewer lands in the 17-step onboarding. Complete onboarding once on a device. This also seeds the preferences that personalize the verdict.
- **What the reviewer will still see.** The AI-consent sheet is stored per device in AsyncStorage (#274), so it appears on the reviewer's first compare. That is desirable for 5.1.2(i).
- **Sign in with Apple.** If the reviewer uses it instead, they get a new free account (3 lifetime-free, then 3/day and 10/month).
- **Account deletion.** If the reviewer deletes the demo account (BE-06), it is gone. After 043 the same email can be registered again.
- **Never.** The password goes only into ASC. Never delete the demo account through a smoke cleanup.
- **Harness under U13.**
  - `verify_after_credits.py` works only as `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python …` (docstring :7-9; header injected only when opted in, :49-56). The admin path is unmetered and writes no history. Its pass rule is too weak (BE-01).
  - `bundle_d_prod_smoke.py` registers a new production user on every run with the public password (:177-178). Its compare probe 12 uses the login bearer (:476-479), so it spends that account's credit. It passes on a degraded 200 (#267). Probes 5, 10 and 11 would turn red if `ENABLE_CONSENT_REQUIRED` were flipped.

## 3. #303: real exposure with U13 and metering ON, and the cheapest safe remedy

- **What an attacker needs.** Each run creates `bundle-d-smoke-<unix-ts>@qaren.app` with a password readable in the public repo (:177-178). Logging in to one means guessing the run's timestamp. Login is limited to 5/min per edge peer, plus Supabase's own limits. A rotating-IP caller like the 2026-10-02 burst could still enumerate a day's window.
- **What they gain.** One account's free tier: 3 lifetime-free (if unused; each smoke run spent 1 on probe 12), then 3/day and 10/month of OpenAI-paid compares. `/auth/register` gives anyone exactly that already (U13 L1). If Supabase confirmations are OFF, the smoke accounts are worth no more than a self-registered one. If confirmations are ON, the smoke's own login probe would have failed, so prior passes imply they are OFF or auto-confirmed. NOT VERIFIED.
- **Privacy content.** The accounts hold only the cached canonical-pair compare. No real person's data.
- **Verdict.** Low incremental exposure. It is not a launch blocker.
- **Cheapest safe remedy.**
  1. Ahmed runs a Claude-drafted SQL one-paste after 043 is applied:
     - count `auth.users` where the email matches `bundle-d-smoke-%@qaren.app`;
     - for each id, `select public.delete_user_cascade(id)` FIRST (#291 rule);
     - then delete the auth users.
  2. Claude makes the smoke password a required environment value and deletes the account at the end of the run (`DELETE /auth/account`).

## 4. Launch-day operations

- **Single worker.** `railway.json:7` / `Procfile:1` start one uvicorn process with `--limit-concurrency 512`, `drainingSeconds 30`. Per ledger 2026-10-03 08:50 there is one replica and no `WEB_CONCURRENCY`.
  - The documented W0 activation order (CLAUDE.md) is one canary per step: `ENABLE_OFFLOOP_DNS_RESOLVE` → `ENABLE_PRICE_PARSE_OFFLOAD` → `ENABLE_SUPABASE_CLIENT_REUSE` → `ENABLE_UPSTASH_BOUNDED_TRANSPORT` (needs a restart). Each canary is 3 app-shaped compares, then `/health` `loop_lag_max_60s_ms` must read under 1000.
  - Owed before a reviewer uses the app: funded OpenAI (for real canaries) and an authenticated canary path (BE-02).
  - U13 removed the anonymous load, but one reviewer's own Link-mode compare (`/url/compare` → DNS) can still freeze the loop for 11-12 s per black-holed host while the P0 flag is OFF.
- **Limiter.** The 10/min decorators key on the TCP peer (rate_limiter.py:52-59), which varies across Railway edge addresses.
  - 51 requests/min from 155 IPs drew no 429 on 2026-10-02.
  - A reviewer or two testers behind one address would need more than 10 compares/min on one route through one edge peer. At 20-40 s per compare that is not reachable.
  - U13 refusals consume no bucket.
  - Only `/auth/login` at 5/min could 429 a reviewer who mistypes repeatedly (now mapped to copy by #269).
- **OpenAI retry variables.** Set (RB-24).
- **Review-window warm-up.** Verdicts are uncached (RB-13). Prices last 24 h (genuine prices 7 d), specs and reviews 7 d. Re-warm daily with the authenticated script (BE-02). Put only pairs that pass the A1.8 rule into the notes.
- **Supabase.** Plan unchanged as far as recorded. See RB-22 / BE-05.
- **Price-warmer.** A no-op while its flag is false (BE-15).

## 5. ASC listing (runbook §6) against the code

- **Lengths.** EN name 20, subtitle 29, promo 160, keywords 95 bytes. AR name 22 chars, subtitle 30, promo 151, keywords 95 bytes. EN description 1,554 chars. All inside the limits (measured from the runbook text).
- **Claims that are false or untestable:**
  - BE-03: estimated prices labelled; "always show how confident".
  - BE-08: Arabic content.
  - BE-09: six-country prices.
  - BE-04: Google sign-in.
  - RB-12: share links, while qaren.app is dead.
  - LL-13: `support@qaren.app` delivery unverified.
  - "Delete your account and its data": true for the account. For residual data it is true only after 043 in branch B.
  - "Photograph one and type the other": the backend supports it (`need_second_product`, image_routes.py:166, :377). The client half is NOT VERIFIED here.
- **Fields still blocked on inputs:**
  - Privacy Policy URL: the page shows the DRAFT banner (RB-3).
  - Copyright: D5.
  - Age rating: D9.
  - App Privacy: CL-labels.
  - Sign-in credentials: RB-8.

## 6. Owner actions (backend / ops side), in order

1. **Answer the legal inputs** (30-45 min). The 8 inputs, plus:
   - D3: recommended A, OpenAI data sharing OFF.
   - D5: publisher/controller.
   - #296: the audit-log retention days.
   - D10: whether pushes are marketing.
   - The three 043 privacy defaults.
   This unblocks U8 and U3b, which are on the critical path.
2. **Supabase** (25 min):
   - Paid plan (10-20 min).
   - Read the Auth Confirm-email setting, the sender and the templates.
   - Add `qaren://reset-password` to the redirect URLs.
3. **Migration 043** (30-45 min over two sittings). PRECHECK, then send the grid back, then ONE_PASTE + POSTCHECK, then BACKFILL if §9 c or d is above 0.
4. **OpenAI** (30 min):
   - Read the tier/TPM.
   - Turn data sharing OFF and read the storage default.
   - Prepaid, low cap, with 50/80% alerts (D8).
   - NEW key on `web` from his terminal; revoke the old one.
   - Then the canary with the fixed script (10-15 min), after Claude unit 1.
5. **Testers open the app** and one Sentry test event is sent (15 min). This starts the U13 24-hour watch and proves mobile reporting works.
6. **W0 flags** in the documented order, one canary each (~1 h hands-on, ½ day elapsed; after step 4).
7. **Domain and mail** (45-60 min):
   - Attach qaren.app to `qaren-landing` and fix the Cloudflare 522; verify the AASA.
   - Cloudflare Email Routing for support@, privacy@ and legal@, with one test mail each.
8. **Railway** (20 min): confirm the paid plan, card and usage cap; mirror the config-as-code settings into the dashboard before 2026-12-01.
9. **Apple session with Hussain** (1-2 h):
   - ASC API key.
   - App record (send Claude the numeric ascAppId).
   - `eas credentials`: production profile, APNs key, capabilities.
   - Optional SIWA key.
10. **Landing redeploy** after U8 and #308 (5 min).
11. **Demo accounts** (30 min): two premium, confirmed, onboarded accounts. Passwords go only into ASC.
12. **Warm-up** (15 min/day): run the authenticated script within 24 h of submission and daily during review.
13. **Screenshots** (½ day) on an iPhone, after the warm-up.
14. **Builds** (2 build cycles):
    - Preview build and the 2-iPhone smoke, including Google sign-in (BE-04).
    - Production build.
    - `eas submit`, then an internal TestFlight smoke.
15. **ASC listing** (1 h): paste the corrected §6, App Privacy from the inventory, the age-rating override to 13+, copyright per D5, the review notes and the demo credentials. Then submit.
16. **Smoke-account cleanup** (#303) with the drafted SQL (15 min, after step 3).
17. **After approval** (10 min): `APP_STORE_URL` on `web`; Worker redeploy with the real id.
18. **Off the launch path:** repo visibility and the GitHub plan (10 min); the deny-rules command (2 min).

## 7. Proposed Claude units

1. **BE-HARNESS (S, waits on none; do first).**
   - `verify_after_credits.py` enforces the runbook A1.8 rule:
     - no `comparison.error`;
     - specs non-empty;
     - at least one price amount;
     - pros and cons present;
     - the stream's terminal event is `success:true`;
     - the app-shaped `product_a`/`product_b` probe.
   - New `scripts/review_warmup.py`: the six pairs twice each, opt-in admin key, paced, with a pass/fail table.
   - Runbook §3 A1.8 and E2 rewritten for U13.
   - Files: `docs/investigations/2026-09-29-session-69-state/verify_after_credits.py`, `scripts/review_warmup.py`, `tests/` (a hermetic harness test), the runbook.
2. **U8 legal redraft (L, waits on the 8 inputs + D3 + D5 + the #296 window).**
   - Replace `app/legal/privacy_policy.md` and `terms_of_service.md`: MYEZ, the controller, the processors, the data rows, deletion truth matching 043, retention, 10/15 working days, log/IP disclosure; no §11 opt-out and no "Premium subscribers".
   - Move the `last_updated` / `TERMS_VERSION` anchors together: `legal_routes.py` ×2, both .md files, `consent_service.py`, `consent.ts`, 4 landing pages + the 2 AR date lines.
   - Optional `?lang=ar`.
   - Must merge BEFORE the production build (`consent.ts` lives in the binary).
3. **U3b (M, waits on D3).**
   - Remove the Profile AI-sharing toggle and its keys.
   - Delete `select_client_for_user` and the `OPENAI_API_KEY_PRIVATE` branch (closes #266).
   - Add the in-app consent withdrawal control.
   - Files: `ProfileScreen.tsx`, `i18n/{en,ar}.json`, `openai_service.py`, tests.
4. **OBS-311 (S-M, waits on none).**
   - #311: type-only log + `from None` at the five sites; ErrorHandlerMiddleware text off; `cache_service` logs through `exc_summary` (#293); span URL scrub in `_before_send_transaction`.
   - Fold in #321 (cap the input), #286 (scrub patterns) and #304 (whitespace key).
   - Files: `app/api/{auth,image,share}_routes.py`, `app/middleware/error_handler.py`, `app/services/{cache_service,sentry_service,log_scrub,database_service}.py`, `admin_routes.py`.
5. **LISTING-TRUTH (S, docs; waits on D11 and D5 for the copyright string).**
   - Correct the runbook §6 EN/AR description, promo and review notes for BE-03, BE-04, BE-06, BE-08 and BE-09.
   - Redraft the ar-SA description under the MYEZ Arabic name for native review.
6. **SMOKE-HYGIENE (S, waits on none; the SQL waits on 043).**
   - #267/#303: required env password; end-of-run account deletion; assert a real verdict.
   - SQL one-paste to count and erase the existing smoke accounts (cascade, then the auth delete).
   - Files: `scripts/bundle_d_prod_smoke.py`, a new APPLY sql in the state folder.
7. **SHARE-LINKS (S, waits on whether qaren.app attaches before launch).**
   - #272: `create_invite` creates the share token.
   - Optional `APP_BASE_URL` env override (default unchanged) so links can use the Railway landing host.
   - Files: `app/services/referral_service.py`, tests.
8. **LOG-PRIVACY #301 (S, waits on none).** Replace raw query/URL INFO logs with a length + hash. Files: `text_routes.py:594,1199`, `url_routes.py:294,355`, tests.
9. **DEL-FOLLOWUPS (S-M, waits on 043 applied).**
   - #318: one multi-key purge + `run_db` offload.
   - #291: 044 orphan backfill.
   - #294: 044 apply guards.
   - Files: `auth_service.py`, `database_service.py`, migrations 044 + APPLY files.
10. **U10 (XS, waits on the ascAppId).** The `submit.production` block in `SmartCompareApp/eas.json`, validated with the resolved submit schema.
11. **POST-APPROVAL (XS, waits on the ascAppId).** Worker `idTBD` → id (`cloudflare-workers/qaren-redirect/src/index.ts:29`); runbook canary §430 production-OTA rule.
12. **Optional:**
    - U11 SIWA revoke (M, waits on the SIWA key).
    - BP-13 census comment + `record=False` for the image fallback (XS, only if D7 goes ON).
    - #284 governorate read (S, before re-engagement pushes are enabled).
    - BE-11 remove the TEMP social trace (XS, after BE-04).

## 8. Not verified by this agent

- Every production variable value (quoted from the ledger and CLAUDE.md only).
- The Supabase plan, the Confirm-email setting and the email templates.
- The live FK branch (A/B) and the PRECHECK grid.
- Whether qaren.app still returns 522 today.
- `npm audit` after #279.
- Whether `dependency-audit` is one of the five required checks.
- Google Sign-In on any build.
- The client half of the camera "one photo + typed" flow.
- The Arabic listing text quality.
- Railway HTTP log retention.
- Whether the price-warmer redeployed on the 2026-10-03 key rotation.
