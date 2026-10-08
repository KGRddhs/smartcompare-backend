# MYEZ App Store launch - implementation plan, session 72 (2026-10-05)

Produced under `/synack-build-orchestrator` Step 4 by the Fable orchestrator. It continues the approved session-71 plan (`../2026-10-03-session-71-state/IMPLEMENTATION_PLAN.md`); the PRD is unchanged (`../2026-09-29-session-69-state/APP_STORE_LAUNCH_RUNBOOK.md` + the session-69 state doc). Base: main `845ece15`.

Inputs (all in `readiness/` beside this file): Step 1 delta `CONFIG_AUDIT_DELTA.md`; Step 3 delta `READINESS_BACKEND.md`, `READINESS_CLIENT.md`, `ISSUE_TRIAGE.md`; the synthesis `LAUNCH_PUNCH_LIST.md`; two adversarial critiques (`CRITIQUE_APP_REVIEW.md`, `CRITIQUE_ENG_OPS.md`). Unit specs and their adversarial reviews: `specs/`. Seven Opus agents wrote the readiness set and six the specs; the orchestrator re-derived the top new claims in code before accepting them (marked "re-derived").

**Roles and loop (unchanged, binding).** Fable plans, rules, gates and reviews; every agent is Opus (`model: 'opus'`, confirmed `claude-opus-5-5` in the transcripts). Per unit: Opus spec -> Opus adversarial spec review -> Fable rulings -> Opus RED -> Fable gate -> Opus GREEN -> two Opus adversaries -> fix -> Fable diff review -> commit -> PR -> merge on 6 green checks. At most two gate-heavy workflows at once.

**Out of scope (binding, from the PRD):** switching LLM provider; StoreKit/IAP; iPad; scraper flag flips and dark-flag activation before App Store approval; the fourteen session-68b flags. A finding is never a licence to add scope: such items are parked under "after launch" or turned into an explicit owner decision.

---

## 1. Verdict

The app cannot be submitted today, and funding OpenAI alone does not make it submittable. The code side is close; what remains is mostly owner input plus a short chain of units that wait on it.

Seven hard stops, each owned:

| # | Hard stop | Owner |
|---|---|---|
| 1 | OpenAI unfunded: every compare fails | Ahmed |
| 2 | Privacy policy and terms are the 2026-03-26 DRAFT (say Qaren, promise an AI opt-out that does nothing, mention "Premium subscribers") in the app, two backend routes and four landing pages | Ahmed's inputs, then unit U8 |
| 3 | The Profile "Help improve AI quality" toggle does nothing; the policy cannot describe it truthfully | Ahmed D3, then unit U3b |
| 4 | No App Store screenshots | Ahmed |
| 5 | No App Store Connect record, App Store profile or API key (Hussain's Individual team) | Ahmed + Hussain |
| 6 | No demo account for a login-gated app | Ahmed |
| 7 | No iOS binary since 2026-07-04; the icon, launch screen and native config reach a phone only in a NEW binary | Ahmed (builds) |

New findings the critics added and the orchestrator re-derived in code (none was in the session-71 plan):

| Id | Finding | Evidence (main `845ece15`) | Goes into |
|---|---|---|---|
| AR-1 | The Share sheet promises a reward that does not exist ("+1 Deep Review credit now", "2x deeper" toast), counts a lifetime cap as "this week" and renders a placeholder link `qaren.app/r/QR-XXXXXX`. Guideline 2.3.1(a) and 2.1(a) | `SmartCompareApp/src/i18n/en.json:423,449,489,511`; `ShareBottomSheet.tsx:143-144`; `deep_review_credits` is granted in `referral_service.py` and consumed nowhere | CLIENT-TRUTH |
| EO-01 | `/url/detect` is anonymous and resolves DNS on the event loop while `ENABLE_OFFLOOP_DNS_RESOLVE` is off: any internet caller can freeze the single worker 11-12 s per request. No app screen calls the route | `app/api/url_routes.py:390-417`; 0 callers in `SmartCompareApp/src` | U13e (or decision W0) |
| BE-01 | The post-funding canary script passes on a degraded 200 (it checks only 200 + success + a winner name; the stream check is "any event") | `verify_after_credits.py:38,67,68` | BE-HARNESS |
| BE-02 | Every anonymous runbook recipe (the A1.8 canary curl, the E2 warm-up) now returns 401 | production, 2026-10-05 | BE-HARNESS |
| L-C1 | The referral push tells the inviter the invitee's name, or the part of the invitee's email before the @ | `referral_service.py:926-929` | U3c |
| L-C3 | No OpenAI call passes `store=False`; what OpenAI stores then depends on the account, not on code | 0 `store=` hits in `app/services` | U3c |
| AR-8 | Register reads the clipboard on mount, so iOS shows a paste alert to a reviewer who registers by email; nothing can have copied a code (the redirect Worker is not deployed) | `RegisterScreen.tsx:101-108` | CLIENT-TRUTH |
| AR-5 | Supplement comparisons carry no "not medical advice" line (guideline 1.4.1) | 0 hits in `en.json` | CLIENT-TRUTH |
| CFG-01 | CLAUDE.md still tells agents to copy `.env` into worktrees, while the agent rules forbid it; every Opus agent now receives CLAUDE.md | CLAUDE.md "Recurring durable gotchas" (c), (g) | DOCS-CONFIG |

Estimate (arithmetic over unit sizes and owner minutes; EAS build and Apple processing times are NOT VERIFIED): about 4 to 6 working days of elapsed time counted from the day the decisions reply arrives AND the Apple session with Hussain happens; owner hands-on time about 12 to 16 hours.

---

## 2. Critical path to "Submit for Review" (corrected by both critics)

| # | Owner | Step | Waits for |
|---|---|---|---|
| 1 | Ahmed | Send the decisions reply (section 6) | - |
| 2 | Ahmed | Fund OpenAI; data sharing OFF in the OpenAI dashboard (if D3 = A); the NEW key on every Railway service that holds the name | - |
| 3 | Ahmed | Supabase paid plan; read Confirm-email, sender, SMTP; add `qaren://reset-password` | - |
| 4 | Ahmed | A tester opens the app signed in and runs one compare (the first mobile Sentry signal) | - |
| 5 | Ahmed + Hussain | Apple session: pending agreements accepted, the API key, the app record (send the numeric Apple ID), `eas credentials`, territories | - |
| 6 | Ahmed, then Claude | Migration 043: PRECHECK grid -> Claude reads it -> ONE_PASTE -> POSTCHECK | 1 |
| 7 | Claude | Units of wave 1 (section 3), no owner input | - |
| 8 | Ahmed + Claude | Post-funding canary (the orchestrator reads the JSON against the runbook A1.8 rule until BE-HARNESS lands); then revoke the old key | 2 |
| 9 | Claude | CLIENT-TRUTH and U3b (the two client units that must be in the store binary) | 1 (copy and D3) |
| 10 | Ahmed | Preview build from main containing step 9; delete the old app on both iPhones; the NEW-binary device checklist | 9 (NOT the legal unit) |
| 11 | Claude | U8 legal: RED and GREEN on placeholders on a branch now; the fill-in commit and merge after 1, 2 (sharing OFF confirmed), 6 (043 POSTCHECK) and U3b + U3c on main | 1, 2, 6, 9 |
| 12 | Ahmed | Landing redeploy in the same hour as the U8 merge | 11 |
| 13 | Claude (only if a device check fails) | U-GOOGLE / U-SNT (U-SPLASH only if the flash is long: decision SPL) | 4, 10 |
| 14 | Ahmed | Two demo accounts with a raised daily limit; never called "premium" in the notes | 3, 6, 8 |
| 15 | Ahmed | Production build from the release commit; `eas submit --id <that build>`; TestFlight smoke on the exact binary; the processing email (ITMS lines, the Xcode version) | 5, 8, 10, 11, 13 (U10 optional) |
| 16 | Ahmed | Six real screenshots on a physical iPhone | 8, 10, 14 |
| 17 | Claude | LISTING-TRUTH: the corrected listing text and review notes | 1 |
| 18 | Ahmed | ASC listing, App Privacy from the inventory, age questionnaire, Content Rights, territories, "Manually release this version" | 5, 12, 14, 16, 17 |
| 19 | Ahmed | Warm-up with the authenticated script within 24 h; Submit for Review; re-warm daily; backend merge freeze until approval except reviewer-path fixes | 15, 18 |

Dependency corrections folded in: the preview build no longer waits for the legal unit (the policy is fetched at run time; only `TERMS_VERSION` is in the binary); U8 waits for the data-sharing switch and for U3b's withdrawal control; U10 is optional for the production build (interactive `eas submit` is the fallback); the TestFlight smoke and the demo accounts need funded OpenAI.

---

## 3. Units

Lever key: backend deploy (Railway on merge) | OTA | new binary | landing redeploy | docs/tooling. OTA-capable client code must still be in the store binary (the `production` channel has never received an update).

### Wave 1 - start now, no owner input

| Unit | Scope (2-3 lines) | Files | Size | Lever | State |
|---|---|---|---|---|---|
| **U8d** Sentry text channels (#311) | Make "Sentry receives exception types and scrubbed templates, not raw exception text or user content" true on the launch paths. The scope split (which of #293 #286 #287 #321 #301 #226 fold in) is ruled from the spec review | `app/api/*_routes.py`, `app/middleware/error_handler.py`, `app/services/{cache_service,sentry_service,log_scrub}.py`, tests | M | backend deploy | spec + review written; rulings next |
| **T0b-B** secret scanning | gitleaks hook pass, `.gitleaks.toml`, the CI secret-scan job (pinned 8.30.1, sha256 `551f6fc8...`), ESLint on staged content, #315 (binary-looking blobs) and #316 (colour / external diff blind spot) | `.githooks/pre-commit`, `.gitleaks.toml`, `.github/workflows/ci.yml`, new hook test files, `tests/test_ci_gates.py` pins | M | docs/tooling | addendum written; review running |
| **U3c** privacy pins | (a) `store=False` on every OpenAI dispatch through the `guarded_llm_create` chokepoint, with an AST pin; (b) the referral push says the invitee's display name or "A friend", never an email prefix. Both make sentences of the new policy true without waiting for D3 | `app/services/api_budget_service.py` (chokepoint), the 15 call sites as needed, `referral_service.py:926-929`, tests | S | backend deploy | spec needed |
| **BE-HARNESS** canary truth | `verify_after_credits.py` enforces the runbook A1.8 rule (no `comparison.error`, specs, a price amount, pros and cons, stream terminal `success:true`, the `product_a`/`product_b` probe); a new authenticated `scripts/review_warmup.py` (six pairs twice, paced, a pass table, a `--send-admin-key` switch, "no price" pairs reported separately); runbook A1.8 / E2 rewritten for the sign-in rule | the session-69 `verify_after_credits.py`, `scripts/review_warmup.py`, a hermetic test, the runbook | S | docs/tooling | spec needed |
| **U13e** anonymous DNS path | `/url/detect` (both verbs) joins the admin-only guard of the paid routes, so an anonymous caller is refused before any DNS work; #304 (a whitespace-only `ADMIN_API_KEY` counts as unset) rides. Needs decision W0 = "guard" | `app/api/url_routes.py`, `app/api/admin_routes.py`, the U13 fixtures and tests | S | backend deploy | spec needed; waits for W0 |
| **DOCS-CONFIG** | CLAUDE.md: delete the three "copy `.env`" instructions; "U4d in flight" -> merged; restate the Ultracode rules that fight principle 4; "Sourcemap upload deferred" -> on since `43cca757`; the rule change for the onboarding canary (decision CAN). Extend the deny-rules script with the shell readers of `.env` (the owner still runs it) | `CLAUDE.md`, `scripts/apply_audit_batch_a.py` (state folder), the canary runbook | S | docs/tooling | editor + reviewer workflow |
| **COST-METER** (#66) | `/admin/costs` reads `full_response.metadata.total_cost`, so launch-week OpenAI spend is not shown as 0 | `app/api/admin_routes.py:130`, `tests/test_cost_dashboard.py` | S | backend deploy | spec needed |
| **SSRF-PHARMACY** (#79) | Match pharmacy domains by parsed hostname and fetch them through the same-site guard that validates every redirect hop | `app/services/price_service.py`, `structured_comparison_service.py`, tests (price path: the corpus byte-identity gate) | S | backend deploy | spec needed |

### Wave 2 - client units that must be in the store binary

| Unit | Scope | Files | Size | Waits for |
|---|---|---|---|---|
| **CLIENT-TRUTH** | Share sheet: remove the Deep Review reward, the "2x deeper" toast and the "this week" wording, show no placeholder link (AR-1). Two placeholder lines on the reviewer path ("Photo upload coming soon", "Pricing lands in an upcoming update"). "388 GCC shoppers" per decision N388. A one-line "not medical advice" note on supplement results (AR-5). Drop the clipboard read on Register for 1.0 (AR-8). Plural "retail sources" (#239). Clear `@qaren_recent_searches` on account deletion (#295). Privacy manifest: SearchHistory purposes gain Analytics (legal review C34). EN + AR under the copy-policy and i18n fences | `ShareBottomSheet.tsx`, `ResultsScreen.tsx`, `EditProfileScreen.tsx`, `RegisterScreen.tsx`, `ResultsContent.tsx`, `src/i18n/{en,ar}.json`, `authService.ts`, `app.json`, `docs/privacy-data-inventory.md`, tests | M | decisions SHARE, COPY, N388, MED, CLIP (the spec is written on the recommended defaults) |
| **U3b** | D3 = A: remove the Profile toggle and its keys, delete `select_client_for_user` and the `OPENAI_API_KEY_PRIVATE` branch (#266); add the consent-withdrawal control approved on 2026-10-03; correct the onboarding "never share" lines. `AI_CONSENT_VERSION` stays 1 only if the consent sheet copy is untouched | `ProfileScreen.tsx`, `src/i18n/{en,ar}.json`, `app/services/openai_service.py`, `auth_routes.py`, tests | M | D3 |

### Wave 3 - gated on owner inputs

| Unit | Scope | Size | Waits for |
|---|---|---|---|
| **U8** legal redraft | Spec `specs/U8_LEGAL_REDRAFT_SPEC.md` with the 28 binding review corrections: both documents rewritten from the code truth table, the full processor list, deletion truth matching 043, the landing pages GENERATED from the markdown (no tables), EN + AR, all twelve version and date anchors moving together, `?lang=` on the legal routes, the support page. RED and GREEN run now on placeholders on a branch; the fill-in commit and the merge wait | L | the input form (`specs/U8_INPUT_FORM_AHMED.md`), 043 applied, U3b + U3c merged, sharing OFF confirmed |
| **LISTING-TRUTH** | Runbook section 6: estimated prices are hidden, not labelled; drop "photograph one and type the other"; the demo account is "a review account with a raised daily limit" (no "premium tier"); keep the sign-in reason sentence (5.1.1(v)); the deletion path; one line on data sources; Google sign-in claim per the device check | S | decisions D11, D5, GOO |
| **U10** | `eas.json` `submit.production.ios` (`ascAppId` as quoted digits, `appleTeamId` 8K562M549D), validated with the resolved submit schema | XS | the ASC app id |
| **DEL-FOLLOWUPS** (044) | #291 orphan backfill, #296 audit-row purge after N days and the retention cleanup of unlinked security and anonymous logs (legal form item 10 = B), #294 apply guards, #318 one multi-key purge | M | 043 applied; R296 / form 10 |
| **PUSH-OPTOUT** (#264) | Every push sender honours `notifications_enabled` | S | D10 = B |
| **SHARE-LINKS** (#272) | `create_invite` mints the share token; optional `APP_BASE_URL` so links can use the Railway landing host | S | decision DNS |
| **RELEASE-CHECKS** | `npm audit` triage on the release commit; the QA static grep pack; App Privacy labels against the inventory; the production-OTA rule rewritten in the production-build PR | S | the release commit |
| **Step 6 structured review** | Security, performance, complexity, dead code over everything merged in this session, two refuters per finding | - | before the production build |
| Conditional | **U-GOOGLE** (hide the Google row for 1.0 or fix), **U-SNT** (a delivery probe if no mobile Sentry event arrives), **U-SPLASH** (only if decision SPL = A) | S-M | device checks |

### After launch (with the reason)

The W0 load flags and every other dark flag (scope rule); #299 per-user limiter key; Sign in with Apple token revocation (needs a key from Hussain; Apple's page says "should"); the Step 6 groups #317-#322 not folded above; scraper coverage and price truth (#61 #75-#78 #93 #94 #96, PRs #39 #42); the W4 dark-flag follow-ups; Arabic verdict prose (#244-#247); perf and ops (#65 #70 #73 #74 #80 #81); test hygiene (#89 #210 #211 #222 #300 #309 #314); the CLAUDE.md slimming (about 86K tokens per agent today; run it when no other unit edits CLAUDE.md); audit batch D housekeeping; issue housekeeping (close #63 #64 #69 #72 #128 with their proofs, decision ISS).

---

## 4. Sequencing (two gate-heavy slots)

- **Slot A (backend):** U8d -> U3c -> BE-HARNESS -> U13e -> COST-METER -> SSRF-PHARMACY -> DEL-FOLLOWUPS.
- **Slot B:** T0b-B -> CLIENT-TRUTH -> U3b -> U8 (GREEN on placeholders) -> LISTING-TRUTH, U10.
- **Light, beside them:** DOCS-CONFIG (docs only); spec + review workflows for the next units; the Step 6 review at the end.
- Every unit already has its spec written before its slot frees. A client unit runs alone in `sc-s70-u4b` (the only worktree with a real `node_modules`).

## 5. Assumptions (and why each beats the alternative)

1. **U3c is split out of U3b.** `store=False` and the push fix need no owner decision, are backend-only and make two policy sentences true; leaving them inside U3b would hold them behind D3.
2. **U13e instead of activating a load flag.** The route has no app caller, and the guard rides a flag that is already on; flipping `ENABLE_OFFLOOP_DNS_RESOLVE` would break the "no dark-flag activation before approval" rule. The owner can still choose the flag (decision W0).
3. **U8 is built on placeholders now, merged later.** The legal inputs are the longest pole; building the generator, the tests and the Arabic structure now turns the owner's answers into a fill-in commit instead of a two-day unit.
4. **The preview build does not wait for U8.** The policy is fetched at run time; the device checks (Google, splash, prompts, pinning, Sentry) need none of the legal inputs, and an early build surfaces a conditional unit days sooner.
5. **The onboarding canary stays 100 for 1.0** (decision CAN = A). At 10, about 90% of new accounts, including a reviewer who signs in with Apple, would get the legacy 6-step flow that no device has run in months.
6. **T0b-B keeps its slot although it is off the launch path.** The repository is public and agents commit daily; the spec is ready, and the unit touches no app code, so it cannot conflict with a launch unit.
7. **No new Arabic copy ships without a native review mark.** Every new AR string is listed for the on-device walkthrough; the alternative (machine text unmarked) is how the earlier label fixes became necessary.

## 6. Decisions needed from Ahmed

The full reply block with every option and consequence is section D of `readiness/LAUNCH_PUNCH_LIST.md`, and the legal questions are `specs/U8_INPUT_FORM_AHMED.md`. Changes the critics and the orchestrator made to the recommended defaults:

- **W0** (anonymous DNS freeze): recommended = **guard** (unit U13e). Options: flag (`ENABLE_OFFLOOP_DNS_RESOLVE` alone, one canary, an exception to the scope rule) or leave open.
- **SPL** (white flash at launch): recommended = decide after seeing it on the preview build; a short flash is not a rejection reason.
- **New:** SHARE (remove the Deep Review claims for 1.0: recommended), MED (a "not medical advice" line on supplement results: recommended), CLIP (drop the clipboard read on Register for 1.0: recommended), TERR (GCC storefronts only for 1.0, so no EU trader declaration: recommended), SMTP (custom SMTP if Supabase "Confirm email" is on).
- **D8:** a small prepayment in submission week can leave the OpenAI account on its lowest rate tier; fund early. NOT VERIFIED against OpenAI's current tier rules.
- **Legal form additions (review C17, C18, C20):** the exact legal name as on the Apple Developer membership; whether an IP licence or assignment between Ahmed and the account holder exists; D14 confirmed (keep the `qaren.app` addresses); whether a data protection guardian or officer was appointed (default no).

## 7. Risks that remain when every row is green (ranked)

1. The backend fails or degrades during review (verdicts are never cached; a drained prepaid balance; the lowest OpenAI rate tier).
2. Google sign-in fails on the reviewer's device (recorded as failing since session 54, never re-verified).
3. The reviewer does not use the demo account (a new account has 3 compares a day), or deletes it (two accounts).
4. Login required for everything (guideline 5.1.1(v)); the review-note sentence is the mitigation.
5. Metadata accuracy: Bahrain-only BHD prices, English verdict prose in Arabic mode, hidden (not labelled) estimates.
6. Supabase or Railway down is a total compare outage under the sign-in rule; `/health` has no database probe; no alert reaches a phone yet.
7. A certificate chain outside the 13 pins makes every call fail and the only alarm is mobile Sentry, which has never been observed working.
8. Apple runs the iPhone-only app on an iPad.

## 8. Not verified

Every production variable value (ledger dates only); the Supabase plan, Confirm-email and sender settings; the live foreign-key branch that decides what deletion keeps today (the 043 PRECHECK decides); `qaren.app` today; `npm audit` after the SDK bumps; Google sign-in on any build since session 54; mobile Sentry delivery; the EAS default Xcode image against Apple's upload floor; EAS build and Apple processing times; the Arabic text quality; whether the permission deny rules bind shell readers of `.env`.
