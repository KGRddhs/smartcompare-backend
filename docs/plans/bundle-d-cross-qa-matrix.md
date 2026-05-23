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

**Risk Ledger progress:** 6 of 24 ADDRESSED (R5, R6, R9, R11, R20, R22). 18 PENDING. **R3 SHIPPED + Migration 026 PROD-APPLIED (10 v2 / 1 v1 confirmed via dispatcher Supabase MCP)** — needs ledger citation commit (Backend follow-up).

Append rows as commits land on the worktree. Statuses: `pending` → `in_review` → `GREEN` / `SEND-BACK` (→ re-review).

---

## Phase 2/3 device-smoke gates (must verify at EAS preview build before Final GREEN)

Each item below is a Phase 1 commit whose runtime cannot be exercised in CI and is held back to device-smoke at Task 2.N.1. QA will NOT close Final GREEN until every gate here is checked.

| Source commit | Lane | What to smoke | Acceptance criterion |
|---|---|---|---|
| `7c677c9` | Frontend 1.F.3 | EditProfile → "Edit style profile" button → onboarding steps 8-10 progression → save returns to EditProfile screen | NewOnboardingHost mounted in edit-mode, `onEditDone` called on save, no silent no-op |
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
