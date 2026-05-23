# Bundle D — Cross-QA Review Matrix

**Owner:** QA agent (FINAL REVIEWER)
**Created:** 2026-05-23
**Worktree HEAD at creation:** `3928d7a`
**Contract:** Ahmed Rule #2 — every implementation commit reviewed by ≥1 other agent; QA is final word.

---

## Reviewer × task grid

Each column lists tasks reviewed by the row's agent (in addition to QA's universal coverage).

| Reviewer | Backend tasks | Frontend tasks | Native/Ops tasks |
|---|---|---|---|
| **Backend** | self | 1.F.1, 1.F.6 | — |
| **Frontend** | 1.B.2, 1.B.3 | self | 1.N.3, 1.N.4 |
| **Native/Ops** | 1.B.4 | 1.F.4 | self |
| **QA** | ALL | ALL | ALL |

### Reviewer-of-record assignments (rationale)

- **Frontend reviews 1.B.2 (legal markdown rebrand C15)** — Frontend renders the markdown via `LegalScreen`; cross-checks brand string sweep does not break heading/paragraph structure (R22).
- **Frontend reviews 1.B.3 (Sentry `_before_send` query-string scrub C14)** — Frontend owns the URL-construction call sites; verifies regex preserves `?nocache=true`, `?token=` patterns (R21).
- **Backend reviews 1.F.1 (refresh-token mutex R9)** — Backend `auth_routes.refresh` is the failure surface; cross-checks the singleton `Promise` is module-scoped, not function-scoped.
- **Backend reviews 1.F.6 (ai_sharing_enabled default OFF C17)** — Backend owns `users.preferences` schema; verifies SQL spot-check that NEW users default OFF while existing ON rows are untouched (R23).
- **Native/Ops reviews 1.B.4 (`_fire_and_forget` audit on 24 sites R15)** — Native/Ops anchor independence check; per-site WRAP/SKIP-with-reason decisions are listed in PR comment.
- **Frontend reviews 1.N.3 (`expo-apple-authentication` config plugin R5)** + **1.N.4 (`expo-notifications` plugin block C16)** — Frontend consumes `app.json` plugin block; verifies no breaking change to existing plugins.
- **Native/Ops reviews 1.F.4 (camera ? help overlay R17)** — Native/Ops owns the EAS build that will ship this; cross-checks scary-vocab copy gate.

---

## Cross-QA review template (paste per agent commit)

```markdown
## QA review — <Lane>: Task <#>

**Reviewer:** QA
**Reviewed commits:** <SHA1>..<SHAN>

### Risks verified (R<N>: [verified via <cmd>] PASS/FAIL)
- R<N>: [verified via <command>] PASS
- R<M>: [verified via <command>] PASS
...

### Verification commands run
- $ <cmd1> → <result>
- $ <cmd2> → <result>

### Test status
- Lane unit tests: PASS / FAIL
- Lane integration tests: PASS / FAIL
- Cross-lane regression: PASS / FAIL

### Three-confirmation rule (L6 control)
- (a) Test GREEN: ✓ / ✗
- (b) Cross-QA approval: ✓ / ✗ (this comment)
- (c) Prod smoke (if applicable): ✓ / ✗ / N/A

### Verdict
GREEN / SEND-BACK

### If SEND-BACK
- Owner: <agent>
- Reason: <one sentence>
- Required re-work: <bullet list>
```

---

## Review-progress tracker

| Commit SHA | Lane | Task # | Reviewer | Status | Verdict | Notes |
|---|---|---|---|---|---|---|
| `29e4d76` | Test | 1.T.1 | QA | reviewed | **GREEN** | RED triage doc only; defer of `test_phase1_includes_reviews` cites design § 12 line 385. Doc-only, no test status manipulation. |
| `70a34b3` | Native/Ops | 1.N.4 (C16) | QA | reviewed | **GREEN** | expo-notifications plugin object-form, brand `#10B981` tint, lines 87-92 of `SmartCompareApp/app.json`. Plugin separation discipline preserved. |
| `03cdc1e` | Native/Ops | R5 citation | QA | reviewed | **GREEN** | R5 → ADDRESSED with proper citation per Risk Ledger update protocol. Surfaces R14 BOTH-gate split correctly (app.json leg done, Apple Dev Portal leg PENDING). |
| `03b9139` + `a654a55` | Frontend | 1.F.1 (R9) | QA | reviewed | **GREEN** | Module-scope `refreshPromise` at api.ts:47 (verified outside function body); `.finally()` release on settle path at lines 67-69; 401 interceptor at line 115 calls `getOrStartRefresh()`. Jest 5/5 GREEN re-run by QA locally (0.447s). R9 → ADDRESSED. |
| `966c66c` | Test | 1.T.1 amend | QA | reviewed | **GREEN** | Triage doc adds `HomeScreen.minDisplayFloor.test.ts` as 4th out-of-scope file. QA independently re-ran the 4 HomeScreen variant suites: **13 failed / 23 total** — 13-RED floor 100% concentrated in these 4 files (root cause `trackEvent` undefined at HomeScreen.tsx:207, Bundle B `21e7bc0` rewire). Zero net-new RED from `03b9139` confirmed. |
| `eeaea11` + `83a83f0` | Backend | 1.B.1 + 1.B.7 (R22) | QA | reviewed | **GREEN** | Double `@router.get()` decorator pattern on existing handlers (no logic change); markdown structure preserved (only 5 SmartCompare→Qaren + 2 email rewrites); 3 new tests named correctly (privacy/terms returns_200 + brand_residue at lines 73/83/93). QA re-ran `pytest tests/test_legal_routes.py tests/test_security_regression.py` → **114/114 GREEN in 87.5s**. Static grep: 0 "SmartCompare" + 0 "smartcompare.app" residue. R22 → ADDRESSED. |
| `4121d23` + `078fbdf` | Frontend | 1.F.2 (R11) | QA | reviewed | **GREEN** | `profile.name` key inserted at en.json:153 ("Name") + ar.json:153 ("الاسم"), between editProfile (152) and settings (154). R11 default per anchor (Ahmed override deferred). Ledger row + citation entry per protocol. R11 → ADDRESSED. |
| `528d53a` | Test | 1.T.idle (R9 coverage top-up) | QA | reviewed | **GREEN** | 2 new test files (`api.refreshMutex.branches.test.ts` + `api.refreshInterceptor.test.ts`) covering 4+15=19 new cases on R9 mutex region. QA re-ran `npx jest --testPathPattern=api\\.refresh` → **24/24 PASS in 0.577s** (5 mutex + 4 branches + 15 interceptor). Zero net-new RED. Doubles down on R9 acceptance. |
| `1f4e380` | Native/Ops | 4.N.1 asset audit | QA | reviewed | **GREEN** | docs/runbooks/bundle-d-asset-audit-2026-05-23.md — finds icon/splash are 2024-era Expo boilerplate PNGs, classifies as "BLOCKER for App Store, NOT blocker for TestFlight internal smoke" + 3 resolution options. Correct call: Phase 2 EAS preview build can proceed; App Store production build needs Ahmed branding decision. Task 4.N.1b filed (BLOCKED on Ahmed). |
| `975f921` | Native/Ops | R6 citation | QA | reviewed | **GREEN** | R6 → ADDRESSED. Ahmed dispatcher-session confirmation cited + on-disk verification (`SmartCompareApp/app.json:17 ios.bundleIdentifier "com.qaren.app"`, :23 android.package, :20 associatedDomains). Fallback ladder preserved. Citation entry per protocol. |
| `9008e5f` | Native/Ops | 1.N.6 DNS plan | QA | reviewed | **GREEN** | docs/runbooks/bundle-d-dns-and-hosting.md — Vercel + Cloudflare alt, TTL 300s for fast revert (R24 control respected), AASA/assetlinks paths match app.json deep-link config, vercel.json snippet with .well-known Content-Type + HSTS. Phase 2 cutover-only — no Phase 1 DNS change yet (correct). |
| `52e7f01` | Backend | R3 RCA + Migration 026 | QA | reviewed | **GREEN-with-caveat** | Migration 026 SQL parsed: data-only backfill of 7 renderable v1 rows using identical `_validate_renderable` predicate (jsonb-path-aware for both `products` flat + `overview.products` nested), DO $$ verification block, rollback file present. Tests `test_get_comparison_returns_404_for_v1_row` + `test_delete_comparison_works_for_v1_rows` PASS. **CAVEAT: R3 ledger row still PENDING at line 13 — needs citation commit before R3 closes.** Migration not yet MCP-applied to live Supabase (Task #33). |
| `7c677c9` | Frontend | 1.F.3 Edit nav fix | QA | reviewed | **GREEN (caveated)** | Code GREEN + source-grep contract GREEN (`App.navigation.test.tsx` 4/4) + **jest runtime DEFERRED to device smoke** (Test lane abandoned i18n-init hoist after 3 iterations, infra cost > delta). Onboarding route now permanent transparentModal; NewOnboardingHost accepts `mode: 'full' \| 'edit'` + `onEditDone`. **DEVICE-SMOKE CHECKPOINT (must verify at Task 2.N.1 EAS preview):** EditProfile → Edit style profile button → onboarding steps 8-10 progression → save returns to EditProfile screen. |
| `2dba367` | Frontend | 1.F.5 history-404 test pin | QA | reviewed | **GREEN** | Pins existing 404 handler at `ResultsScreen.tsx:182-189` (renders `t('results.emptyState.notFound')`). No new screen code — correct per R3 anchor recipe. Backed by Migration 026 backfill. |
| `6c17ca8` + `0dc774e` | Backend | 1.B.5 (R20) Migration 025 | QA | reviewed | **GREEN** | Migration 025 SQL: SECURITY DEFINER, `CREATE OR REPLACE` idempotent. Adds `user_usage` + `referral_invites` (referrer + redeemed_by) + `referral_redemptions` (referrer + invitee) + clears `users.preferences`/`expo_push_token`/`device_fingerprint_hash` for App Store delete-cascade. `admin_audit_log` correctly RETAINED per Session 43 forensics. Rollback file present. QA ran `pytest tests/test_delete_user_cascade.py tests/test_history_routes.py` → **30/30 GREEN in 2.24s**. R20 → ADDRESSED. Migration not yet MCP-applied (Task #34). |
| `5449da7` | Backend | 1.B.3 refresh-token docstring | QA | reviewed | **GREEN** | Docstring-only change documenting single-use rotation contract + client-side dedup is Frontend's responsibility (mutex landed in 03b9139). Anchor-prescribed scope, no logic change. |
| `6121432` | Native/Ops | AASA Team ID substitution | QA | reviewed | **GREEN** | Apple Team ID `8K562M549D` (10-char alphanumeric, valid format) substituted in `apple-app-site-association.json:6`, README + `dns-and-hosting.md` updated. JSON syntax preserved. Unblocks R4 / R14 / 1.N.2 / 1.B.4. assetlinks.json SHA-256 still placeholder (correct — waits on Task 2.N.1 EAS preview build). |
| `7b5a35d` + `2b8919d` | Frontend | 1.F.6 (R23) ai_sharing default OFF | QA | reviewed | **GREEN** | Single-line flip at `ProfileScreen.tsx:93` `!== false` → `?? false`. Truth table proven: undefined→false, true→true, false→false. **QA Supabase SQL spot-check executed:** 7 total users, 1 explicit `true` (NOT at risk — `?? false` only changes undefined branch), 6 undefined (will correctly default OFF for App Store privacy opt-in). Jest 14/14 GREEN (3 aiSharingDefault + 11 bundleA). Ledger flip + citation per protocol. R23 → ADDRESSED. |
| `6bd81a0` + `eda917a` | Frontend | 1.F.4 (R17) Camera help overlay | QA | reviewed | **GREEN** | New `CameraHelpOverlay.tsx` Modal-based, tap-anywhere-close via `TouchableOpacity activeOpacity=1` (preserves react-native mock compat). `ScanCameraScreen` wires `helpVisible` state + onPress on `scan-camera-help` testID. 5 new i18n keys EN + AR (`home.camera.help.{title,step1,step2,step3,close}` at en.json/ar.json:642-646). Scary-vocab gate clean (no couldn't/try again/Failed to/تعذر/فشل/estimated in component or copy). Jest 121/121 GREEN across 10 suites (CameraHelpOverlay 5/5 + render + ScanCameraScreen.edges 6/6 + copy-policy + i18n). Ledger flip + citation per protocol. R17 → ADDRESSED. |

| `f89ea58` | Backend | R3 ledger citation | QA | reviewed | **GREEN** | R3 row PENDING → ADDRESSED with proper citation per protocol. Migration 026 prod-applied (10 v2 / 1 v1 confirmed via dispatcher Supabase MCP session). Bonus: R20 APPLIED addendum cites pg_get_functiondef byte-for-byte match. **R3 → ADDRESSED.** |
| `bf22b61` | Backend | R21 ledger citation | QA | reviewed | **GREEN** | R21 row PENDING → ADDRESSED via Sentry query-string scrub (commit `5fa6c11` referenced). 5 PII param names scrubbed (`q,query,email,search,text`) → `[QUERY_REDACTED]`; bookkeeping params (`nocache,limit,offset,sort`) preserved. QA re-ran `pytest tests/test_sentry_service.py tests/test_security_regression.py` as part of 239-test pack → all GREEN. **R21 → ADDRESSED.** |
| `78aeb23` + `4775152` | Backend | 2.B.6 (R15) `_fire_and_forget` audit | QA | reviewed | **GREEN** | Audited 22 `asyncio.create_task` sites across `app/api/{auth,feedback,image,text}_routes.py` — ALL 22 WRAPPED via new `app/utils/async_utils.fire_and_forget(coro, label)`. Helper migrated from `structured_comparison_service.py` (thin alias preserved for existing 5 in-service call sites). Independent grep verification: 0 surviving `asyncio.create_task(` in `app/api/`. Surviving calls in `app/services/{price,review,structured_comparison,usage}_service.py` are out-of-scope `gather()` patterns or pre-existing internal use. QA re-ran combined backend pack → **239/239 GREEN in 93.14s** (security_regression + push_token + legal + account_deletion + delete_user_cascade + sentry_service + auth_routes_invite_fingerprint + feedback + text_routes_sse_contract). **R15 → ADDRESSED.** |
| `228ff63` + `2e28d9f` + `f766e9f` | Backend | 2.B.7 (R18) reengagement-subs PUT | QA | reviewed | **GREEN** | New `PUT /api/v1/auth/reengagement-subs` endpoint (per anchor R18 recipe: grep first, create if missing). Frontend FE-side closure commit `f766e9f` wires it. Ledger flip + citation per protocol. **R18 → ADDRESSED (both backend + FE-side).** |
| `faead5e` | Backend | 1.B.4 (R4) Apple 3-leg checkpoint | QA | reviewed | **GREEN** | Apple Sign-In end-to-end verified live in prod via 4-leg checkpoint (Service ID + .p8 + Supabase provider + backend curl). RCA caught anchor curl path was wrong (`/social/apple` → actual `/social-login` with provider in body). Gradient triangulation: apple/google response parity = industry-standard "provider enabled" signal. Apple HTTP 401 + AUTH_REQUIRED (request_id `a59eb83b`) matches Google HTTP 401 + AUTH_REQUIRED (request_id `d937a28b`). Bogus provider gets 422 from Pydantic Literal whitelist. **R4 → ADDRESSED.** R14's app.json leg also closed via R5; Native/Ops to flip R14 fully ADDRESSED in follow-up. |
| `3bad8f5` | Frontend | 1.F.3 coverage top-up | QA | reviewed | **GREEN** | `NewOnboardingHost.editMode.test.tsx` 7/7 GREEN runtime — partial substitute for 1.F.3 device-smoke gate (still requires real EAS preview). `react-test-renderer.d.ts` shim closes TS7016 emitted by tsc for both this test + Test lane's `9096729` CameraHelpOverlay.render. Net new RED = 0. |
| `9096729` | Test | R17 coverage top-up | QA | reviewed | **GREEN** | `CameraHelpOverlay.render.test.tsx` 6/6 GREEN runtime — coverage on `CameraHelpOverlay.tsx` from 0% → **100% statements / 100% branches / 100% funcs / 100% lines**. Combined with author's 5/5 source-grep → 11/11 GREEN total. Net new RED = 0. |
| `c5fd165` | Test | design § 12 anchor polish | QA | reviewed | **GREEN** | Design doc § 12 now explicitly names `test_phase1_includes_reviews` as D2 Intervention 1 follow-up + lists the 4th HomeScreen variant. Closes the trace loop I flagged earlier. Docs-only, no logic change. |
| `10ff816` | Native/Ops | 1.N.7 privacyManifests (R13-adj) | QA | reviewed | **GREEN** | iOS 17+ submission blocker: `privacyManifests` block added to `app.json`. Substitutes for the Apple-side PrivacyInfo.xcprivacy requirement at runtime. Task 4.N.1 (R13 nutrition labels) is separate from this — R13 still PENDING for ASC label draft (Ahmed approval). |
| `c2aec12` + `a23ed51` + `6bbe14d` + `a8110cb` + `148d735` | Native/Ops | landing/+ASC prep | QA | reviewed | **GREEN** | landing/support.html replaces broken mailto-redirect; legal terms.html § 12 regenerated to match 3-lifetime-per-device referral cap (Migration 023); 'Compare Smart' tagline; ASC metadata draft for 3.N.2. All docs-only; copy is policy-clean. No code or test paths touched. |

| `0a06d01` + `f766e9f` | Frontend | 2.F.1 (R18 FE-side) reengagement subs UI | QA | reviewed | **GREEN** | New `putReengagementSubs(body)` in api.ts + `ReengagementSubsBody` interface (plural keys match Backend 228ff63 contract). `handleSubToggle(key, value)` at ProfileScreen.tsx:170-212 — optimistic update first (line 185), rollback `setPreferences(previous)` on BOTH `!result.success` (line 199) + catch (line 205), Alert.alert fires `errorTitle` + msg. Master `notifications_enabled` still routes through `savePreferences`/`/preferences` (correctly split). Plural→singular at FE call site verified line 191-193. QA re-ran `npx jest --testPathPattern="ProfileScreen\\.(optimistic\\|bundleA\\|aiSharingDefault)"` → **20/20 GREEN in 0.579s** (6 + 11 + 3). R18 → ADDRESSED (both backend + FE-side). |
| `17b5a50` | Native/Ops | A6-refit landing/ → Railway | QA | reviewed | **GREEN** | landing/ refit from Vercel to Railway. New Dockerfile (nginx:1.27-alpine), nginx.conf.template (envsubst ${PORT}), railway.toml. Vercel config moved to docs/runbooks/ as `.alternative`. AASA + assetlinks + 4 HTML files PRESERVED (git diff scope verified). nginx template verified: `/.well-known/{aasa,assetlinks.json}` explicit `application/json` (Apple/Google validator requirements), `/support` clean-URL via try_files, `/healthz` 200 ok for Railway monitoring, 5 security headers at server scope (HSTS+X-CTO+X-Frame-Options DENY+Referrer-Policy strict-origin-when-cross-origin+Permissions-Policy). **One observation (NOT blocking):** nginx `add_header` inheritance — `.well-known` location blocks have their own `add_header Cache-Control` + `X-Content-Type-Options`, which REPLACES server-scope headers in those locations per nginx semantics. HSTS/X-Frame-Options/Referrer-Policy/Permissions-Policy will NOT inherit to `/.well-known/*`. Negligible impact since AASA + assetlinks are pure JSON without browser rendering, but worth a Phase 3 follow-up if hardening matters. |
| `4f9b015` | Backend | 2.B.1 B.0 response_builder kwarg refactor | QA | reviewed | **GREEN** | Liberal kwarg signature + metadata override merge. Greens `test_comparison_quality_in_response_metadata_payload` (QA verified 1/1 PASS in 1.54s). Backend regression pack `pytest tests/test_structured_comparison_service.py tests/test_push_token_endpoint.py tests/test_security_regression.py` → **135/135 GREEN in 86.64s** — no breakage from kwarg refactor. **Net Backend RED floor: 3 → 1 deferred.** |
| `fc1451b` | Backend | 2.B.2 A.7.2 strip price.note | QA | reviewed | **GREEN** | Defense-in-depth: when `source_method=estimated`, response_builder strips the `price.note` field. Bundle C GREEN gate item 17 per commit message. No regression in 135-test pack above (covers structured_comparison_service). |
| `3def805` | Test/Frontend | R16 Bundle B contract preservation (HomeScreen) | QA | reviewed | **GREEN** | 338 lines, 11 sections (TwoInputShell mount, paste-split + URL mode-switch, dual-shape product_a/b, L1-L4 moderation, 8 analytics events via it.each, paywall takeover, 1.2s floor, haptic vocabulary, 3-part ready celebration, forbidden vocab, post-redesign placeholders). QA verified regex discipline: word-boundary `\b(shake\|wobble\|jitter)\b` at line 293 prevents `tree-shaken` false positive; `looksLikeUrl(next)` without `.trim()` at lines 83-84 pins OQ-FE Bundle B § 4.1.2 invariant. 40 PASS + 5 todo placeholders covering R10 theme additive + EN A-L + AR M-P + snapshot regen + post-redesign hook. |
| `cbdd183` | Test/Frontend | Per-page contract preservation (multi-screen) | QA | reviewed | **GREEN** | 344 lines, 9 screens (Results, History, Profile, EditProfile, Login, Register, ForgotPassword, NewOnboardingHost edit-mode, ScanCameraScreen). 44 PASS + 8 todo placeholders. Combined with 3def805: **84 PASS + 13 todo in 0.607s**. **One observation (NOT blocking):** HistoryScreen todo at line 337 reads "FlatList virtualization" but code-side regex (per frontend note) accepts `<FlatList\|SectionList>` since Bundle B/C ships SectionList. Wording mismatch worth a minor edit. |

**R16 framework: 84 PASS + 13 TODO total** (3def805 + cbdd183 combined). FE-side first leg of R16 control complete. Device leg closes during 2.N.1 EAS preview walkthroughs.
| `b2e4c7e` | Native/Ops | R13 defense-in-depth note | QA | reviewed | **GREEN** | Per dispatcher guidance: privacyManifests commit `10ff816` cited in R13's defense-in-depth note. R13 row STAYS PENDING — privacyManifests is a different runtime gate (iOS 17+), R13 is ASC Nutrition Labels approval (Ahmed sign-off). Two distinct controls, intentional separation. |
| `f7732dd` | Native/Ops | 2.N.1c screenshot capture runbook | QA | reviewed | **GREEN** | Phase 3 prep runbook for Ahmed device-smoke session. Docs-only, no logic. |
| `fff259a` | Native/Ops | landing/vercel.json removal cleanup | QA | reviewed | **GREEN** | Removes `landing/vercel.json` (the original, missed in `17b5a50` Railway refit). `vercel.json.alternative` in `docs/runbooks/` remains as the historical reference. Tidies up the worktree. |

| `3095304` | Native/Ops | R14 BOTH-gate closure | QA | reviewed | **GREEN** | R14 → ADDRESSED. Both legs cited: (a) Apple Dev Portal — App ID `com.qaren.app` "Sign in with Apple" capability enabled + Service ID `app.qaren.signin` + Key ID `7S9CT35UX7` + .p8 (Ahmed A3-A7 dispatcher session); (b) build-time entitlement — `expo-apple-authentication` plugin at app.json:86 + `ios.usesAppleSignIn: true` at app.json:19 (Expo SDK 54 auto-injects `com.apple.developer.applesignin` at EAS prebuild; verifiable via `find ios -name *.entitlements` post-Task-2.N.1). Closes my prior R14 BOTH-gate follow-up note. |
| `931650b` | Frontend | Policy comment opt-OUT vs opt-IN | QA | reviewed | **GREEN** | 9-line comment at ProfileScreen.tsx:189 explains intentional asymmetry between `!== false` (sub-toggles opt-OUT, user opted into re-engagement at onboarding step 17) and `?? false` (ai_sharing_enabled opt-IN, App Store privacy). Forward pointers to BUNDLE_D_FRONTEND_ANCHOR § R23 + Backend 228ff63. Wording-only; ProfileScreen 20/20 unchanged. |
| `35f9443` | Test/Frontend | R16 framework v2 — testIDs + regex bounds | QA | reviewed | **GREEN** | Per my Ask #4 on the R16 deep-review: pinned critical testIDs as query anchors + widened regex windows that the 0a06d01 + 931650b ProfileScreen comments had pushed past the 1200-char threshold. Bumped 1200→2000 (line 127) + 1500→2500 (line 137). 7 new tests added (testID coverage). QA re-ran combined R16 contract pack → **91 PASS + 13 TODO in 0.552s**. Previously failing `handleSubToggle → /reengagement-subs` test now PASSES. Closes my prior flag — Frontend RED floor back to 13. |
| `903b0b5` | Backend | Backend final sign-off | QA | reviewed | **GREEN-noted** | Per design § 9 rubric — Backend lane files final sign-off with verification evidence. Note: this is Backend's lane sign-off (Rule #5: "Per-lane GREEN gate"); QA Final GREEN sign-off (the merge-blocking comment) is a separate gate I post when all 5 lanes + Risk Ledger + Sentry + curl pack are all green. |

**Triage closure delta (verified via independent QA pytest re-run):**
- `test_decision_insight_skipped_when_subtoggle_off`: RED → **GREEN** (closed by Backend `228ff63`)
- `test_missing_preferences_treats_as_all_on`: RED → **GREEN** (closed by Backend `228ff63`)
- `test_comparison_quality_in_response_metadata_payload`: RED → **GREEN** (closed by Backend `4f9b015`)
- `test_phase1_runs_reviews_in_parallel_with_specs_price`: RED (deferred § 12, unchanged)

**Net Backend RED floor: 3 → 1 deferred.** Phase 4 target met.

**Risk Ledger progress:** 14 ADDRESSED + 2 N/A = **16 of 24 closed.** 8 PENDING.
- ADDRESSED (14): R3, R4, R5, R6, R9, R11, R14, R15, R17, R18, R20, R21, R22, R23
- N/A (2): R1 + R2 (per dispatcher 2026-05-23 — `git diff bca2ffe..HEAD -- app/main.py app/middleware/` returned 0 lines; preventive control surfaces wholly absent in Bundle D scope)
- PENDING (8): R7, R8, R10, R12, R13, R16, R19, R24

**QA verification cmds re-run after this batch:**
- `pytest <9-file backend pack>` → **239/239 GREEN in 93.14s**
- `npx jest --testPathPattern="NewOnboardingHost\.editMode|CameraHelpOverlay\.render"` → 13/13 GREEN
- `npx jest --testPathPattern="ProfileScreen\.(optimistic|bundleA|aiSharingDefault)"` → 20/20 GREEN
- `mcp__plugin_sentry_sentry__search_issues query=firstSeen:-1h sort=date` → **2 new Apple Sign-In test-driven probes** (PYTHON-FASTAPI-B + C at `social_login`, 6-7 min ago) — **EXPECTED from R4 gradient triangulation, NOT regressions.** Both prove Apple provider IS now reaching `sign_in_with_id_token()` and exception-handling correctly. 0 user impact, 4 events total. Documented for transparency.

Append rows as commits land on the worktree. Statuses: `pending` → `in_review` → `GREEN` / `SEND-BACK` (→ re-review).

---

## Phase 2/3 device-smoke gates (must verify at EAS preview build before Final GREEN)

Each item below is a Phase 1 commit whose runtime cannot be exercised in CI and is held back to device-smoke at Task 2.N.1. QA will NOT close Final GREEN until every gate here is checked.

| Source commit | Lane | What to smoke | Acceptance criterion |
|---|---|---|---|
| `7c677c9` | Frontend 1.F.3 | EditProfile → "Edit style profile" button → onboarding steps 8-10 progression → save returns to EditProfile screen | NewOnboardingHost mounted in edit-mode, `onEditDone` called on save, no silent no-op |
| `6bd81a0` | Frontend 1.F.4 R17 | ScanCamera → tap ? button → CameraHelpOverlay visible → tap anywhere → closes | `helpVisible` toggles on/off; no haptic on open/close (Build Principle #4) |
| `7b5a35d` | Frontend 1.F.6 R23 | Fresh signup with no preferences row → ProfileScreen → "Share AI data" toggle should be OFF by default | Toggle defaults OFF (opt-IN required for App Store); existing users with explicit `true` remain ON |
| `0a06d01` | Frontend 2.F.1 R18 | Toggle each of 3 sub-toggles online → expect new server-side row in `users.preferences.notification_types` (singular keys server-side). Toggle while offline → expect Alert with `profile.notifs.errorTitle` + revert to previous state | (a) Online: PUT /reengagement-subs 200 + DB row updated, UI stays in target state. (b) Offline: optimistic UI flip, then Alert.alert fires, UI reverts. (c) Master toggle still hits /preferences. |
| (more rows as commits land) | | | |

---

## Three-confirmation rule (Ahmed Rule #7) — enforcement

Every "done" sign-off requires:
- **(a)** Test GREEN (unit or integration as applicable)
- **(b)** Cross-QA approval (this matrix + QA template)
- **(c)** Prod smoke where applicable (Backend deploy + Native/Ops EAS build)

**Two-of-three is NOT done.** QA will reject any sign-off that lists 2/3.

---

## Risk Ledger (R1-R24) verification gate

QA verifies every R# transition from PENDING → ADDRESSED / N/A / ACCEPTED. See `memory/BUNDLE_D_RISK_LEDGER.md`. Dispatcher cannot merge until **ZERO PENDING** rows remain. Send-back authority applies to any unverified or improperly-cited risk.

---

## Send-back protocol (Ahmed Rule #3)

When QA issues SEND-BACK:
1. Post template above to the owner via `SendMessage` with `Verdict: SEND-BACK`
2. Cite the specific design doc § / R# / verification command that failed
3. Original owner re-does the work (no silent merge of "good enough")
4. Owner re-requests review with new commit SHA(s)
5. QA re-verifies, posts GREEN or another SEND-BACK

---

## QA Final GREEN sign-off gate

QA posts `## Bundle D QA Final GREEN sign-off — verified 2026-MM-DD` comment on PR only when ALL of the following are GREEN:

- ☐ All 5 lane sign-offs posted in PR (Backend, Frontend, Native/Ops, Test, QA-self)
- ☐ `BUNDLE_D_RISK_LEDGER.md` shows zero PENDING (every R1-R24 = ADDRESSED / N/A / ACCEPTED)
- ☐ Sentry MCP 30-min watch: zero new issue types over `bundle-d-sentry-baseline-2026-05-23.txt`
- ☐ Production curl pack: 100% 200 OK
- ☐ Supabase audit-log: privacy invariants hold (Q2 = 0 bad hash, Q3 = 0 raw text)
- ☐ Static audit greps: zero hits per anchor doc
- ☐ All pre-existing RED tests triaged (greened by Bundle D or explicitly deferred with Ahmed approval)

---

## Sentry baseline reference

`docs/plans/bundle-d-sentry-baseline-2026-05-23.txt` — Phase 0 snapshot:
- 3 known issue types (1 Apple provider, 1 Google Sign-In native, 1 refresh-token race)
- All 3 expected to be addressed by Bundle D itself, NOT regressions
- Phase 3 close-out gate: any NEW issue type post-deploy = block merge until triaged
