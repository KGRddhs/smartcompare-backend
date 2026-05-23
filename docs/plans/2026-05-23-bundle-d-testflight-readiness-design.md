# Bundle D — TestFlight Readiness (Design)

**Status:** Brainstormed 2026-05-23. Awaiting implementation plan (next step: `writing-plans` skill).
**Bundle target:** `feature/bundle-d-testflight-readiness` (single mega-team, single PR to `main`)
**Scope:** 59 distinct work items across 5 lanes
**Wall-clock budget:** 2-3 days with 5-Opus team executing in 4 phases

---

## 1. Goal

Ship the Qaren mobile app to Apple TestFlight (internal test group, up to 100 testers) with:
- Every reproducible Expo bug fixed (12 items)
- Every Bundle C v1.1 polish item shipped (5 items)
- Pre-existing audit follow-up complete (24 `_fire_and_forget` sites + 5 critical pre-existing gaps)
- Full operational pipeline live (Apple Developer Portal, App Store Connect, EAS production build, internal tester invite, Sentry sourcemap upload, force-update env wiring, app icon/splash finalization)
- ASC mandatory URLs hosted at `qaren.app` (landing page placeholder + privacy + terms subpages)
- PR #6 Bundle B simulator sign-off comment posted

**Success state:** Ahmed receives TestFlight invite → installs build → cold-starts → completes a full comparison → submits feedback → 30-min Sentry watch shows zero new issue types over baseline. Dispatcher merges Bundle D PR. Internal testers can be invited at will.

---

## 2. Scope inventory (59 items)

### Lane: Mobile bugs (12) — Frontend agent owns, Backend agent assists
1. HomeScreen Claude-Design refresh (consume design tokens from Ahmed-provided Claude-Design output; extend `src/theme/index.ts`; preserve Bundle B TwoInputShell contract — paste-split, mode-switch, content moderation)
2. History detail load fail — investigate `schema_version=2` filter (R3 — likely Ahmed's failing rows are v1)
3. `/api/v1/legal/*` Privacy + Terms load fail (frontend retry UX + backend root-cause)
4. Profile toggle optimistic UI (instant state, rollback on failure)
5. Profile 5-toggle wiring audit (AI sharing + 4 reengagement subs all save end-to-end)
6. Preferences save error
7. EditProfile `profile.name` i18n missing key (`src/screens/EditProfileScreen.tsx:135,143` — add EN: "Name" / AR: "الاسم")
8. EditProfile "Edit style profile" NAVIGATE→Onboarding fail (`App.tsx:301` — Onboarding only registered when `needsPreferences=true`)
9. Camera `?` help button no-op (`src/screens/ScanCameraScreen.tsx` — add help overlay modal)
10. Google Sign-In native module crash (`RNGoogleSignin` not in Expo Go binary; needs EAS dev build)
11. Apple Sign-In missing (now unblocked — Apple Dev account acquired; needs Service ID + Supabase provider + entitlement + EAS build)
12. Refresh-token "Already Used" race (`src/services/api.ts` 401 interceptor; module-scope singleton `Promise` mutex)

### Lane: Backend polish (5) — Backend agent
13. B.0 response_builder kwarg refactor (greens 3 RED tests including `test_comparison_quality_in_response_metadata_payload`)
14. A.8.1 dimensions thin-adapter from `CATEGORY_DIMENSIONS` (replace hand-coded `_dim_dpi/_popularity/_build_quality`)
15. A.4.8 Tier 3 GPT-4o batched synthesis (last-resort spec fill when Tier 2 also blank)
16. A.6.2-A.6.5 richer value-math `delta_text` + cross-tier framing + per-product `value_match` + `budget_mismatch` metadata
17. A.7.2 backend strip `price.note` when `source_method=estimated` (defense-in-depth; frontend already silent)

### Lane: Audit follow-up (24 sites) — Backend agent
18. 24 remaining `asyncio.create_task` sites in `app/api/*` wrapped with `_fire_and_forget(coro, label)` helper (judge per site — no blanket-wrap; some legitimate one-shot tracking events can stay plain)

### Lane: Operational (7) — Native/Ops agent + dispatcher
19. PR #6 Bundle B EN+AR simulator walkthrough on new EAS preview build + screenshots + analytics log + post prepared comment
20. Sentry RN sourcemap upload (create EAS secret `SENTRY_AUTH_TOKEN`; flip `SENTRY_DISABLE_AUTO_UPLOAD=false`)
21. Force-update env vars wiring check (`APP_MIN_VERSION`, `APP_LATEST_VERSION`; `APP_FORCE_UPDATE` set false initially, flip later per R19)
22. App icon + splash final audit (zero "SmartCompare" residue; EN+AR look right at all densities)
23. `ENABLE_REENGAGEMENT_PUSHES=true` flip (Phase 4, AFTER Ahmed installs build + acknowledges first cron tick safe)
24. TestFlight internal pipeline (bundle ID claim + ASC app record + EAS submit profile + internal tester invite for Ahmed + ≤9 others)
25. Railway env-var audit (after Ahmed runs `railway login` from terminal; cross-check actual env vs documented)

### Lane: Pre-existing critical gaps surfaced 2026-05-23 (5) — distributed
26. **C13** `delete_user_cascade` cascade-completeness gap (Backend; SQL function extension — explicit DELETEs from `user_usage`, `referral_invites`, `referral_redemptions`, `expo_push_tokens`; document `admin_audit_log` retention)
27. **C14** Sentry URL query-string passthrough (Backend; extend `_before_send` in `app/services/sentry_service.py` to redact `?q=` and similar query strings)
28. **C15** Stale legal-doc brand mismatch (Backend; rewrite `app/legal/{privacy_policy,terms_of_service}.md` to use Qaren / `support@qaren.app` — text content stays substantively the same modulo brand swap; full legal redraft deferred to legal-decisions follow-up)
29. **C16** `expo-notifications` plugin missing from `app.json` (Native/Ops; add plugin entry with iOS `NSUserNotificationUsageDescription` + Android `POST_NOTIFICATIONS` — push won't work otherwise)
30. **C17** `ai_sharing_enabled` defaults ON (Frontend; flip default to OFF in `ProfileScreen.tsx:102` per PDPL Art. 4 / GDPR opt-IN expectation; show in onboarding wizard with explicit opt-in)

### Lane: ASC mandatory URLs + landing page (6) — Native/Ops + Backend + Ahmed-provided artifact
31. **O1** Privacy Policy URL live at `qaren.app/privacy` (subpage rendering rewritten `privacy_policy.md` from C15)
32. **O2** Support URL or email reachable (`support@qaren.app` mailto + `qaren.app/support` redirect)
33. **O3** Public-facing landing page at `qaren.app` (Ahmed provides Claude-Design output OR Native/Ops ships placeholder "Coming soon — App Store / Google Play")
34. **O4** ASC Privacy Nutrition Labels filled (Native/Ops drafts; Ahmed approves: Contact Info / Identifiers / Usage Data / User Content / Diagnostics)
35. **O5** Apple Developer Program account holder + email confirmed in ASC (Ahmed provides when Native/Ops requests)
36. **O6** Account-deletion in-app path documented (Profile → Edit Profile → Delete account; surface in ASC submission notes + new legal docs)

**Total:** 12 + 5 + 24 + 7 + 5 + 6 = **59 items**

---

## 3. Team composition

**5 Opus agents** (no Sonnet, no Haiku, no exceptions — per Ahmed instruction):

| Agent | Lane focus | Item count |
|---|---|---|
| **Backend** | Backend polish + audit follow-up + legal endpoints + preferences save + refresh token + Supabase Apple provider + 5 v1.1 polish + 24 `_fire_and_forget` + C13/C14/C15 | ~33 items |
| **Frontend** | All 11 non-redesign Expo bugs + HomeScreen Claude-Design refresh + refresh-token mutex + C17 + i18n + nav fix | ~13 items |
| **Native/Ops** | EAS preview + production builds + Apple Developer Portal (Service ID + entitlement + provisioning) + ASC (app record + TestFlight + Privacy Nutrition Labels + tester invite) + Sentry sourcemap + app icon/splash + force-update env + `app.json` plugins (C16) + landing page hosting (O1-O3) | ~13 items |
| **Test** | 80%+ coverage on touched files + triage 3 pre-existing RED tests + red-green tests for new features + idle-time test writing | continuous |
| **QA** | Cross-review all 4 implementation agents + R1-R24 risk-ledger verification + production curl smokes + Sentry MCP 30-min watch + Supabase audit-log SQL pack + final GREEN sign-off | continuous |

**Why 5 (not 4):** Native/Ops is an entire lane of operational paperwork (Apple Dev Portal + ASC + EAS submit + DNS + provisioning) distinct from app coding. Splitting it out prevents the Backend or Frontend agent from getting blocked on web-console work. Per CLAUDE.md OP #8 (4-Opus team stall pattern), 5 distinct lanes reduces inbox-collision and idle-loop risk.

---

## 4. Team contract rules (Ahmed-instructed, codified)

1. **100% complete before disassembly** — no half-finished items, no "defer to v1.1 again." Every scope item ships or is explicitly downgraded with Ahmed approval.
2. **Mandatory cross-QA** — every implementation member's work reviewed by ≥1 other member before merge; QA agent is final reviewer for all three implementation lanes.
3. **Send-back on subpar** — reviewer can veto; original owner re-does; no silent merge of "good enough." Final word: QA agent.
4. **Idle time = red-green tests** — any agent waiting on QA writes tests for in-flight features, target 80% line coverage on touched files.
5. **Opus only** — no Sonnet, no Haiku, no model downgrades.
6. **Memory anchor docs against hallucination** — each lane gets a pre-loaded anchor MD with file:line citations, expected behavior, verification commands, risk subset; agents read before starting work.
7. **Three-confirmation rule** — every "done" claim verified by (a) test green (b) cross-QA approval (c) prod smoke where applicable. Two-of-three is NOT done.
8. **OP #8 escalation** — dispatcher polls team inbox every 30 min; agent silent + uncommitted state past 30min = dispatcher absorbs task immediately. Per CLAUDE.md Operating Principles.

---

## 5. Sequencing (4 phases, ~2-3 days wall clock)

### Phase 0 — Setup (dispatcher, <1hr, day 0)
- Create worktree `bundle-d-testflight-readiness` off `main`
- Write 6 memory anchor docs (Section 7)
- Spawn 5-Opus team in `bypassPermissions` mode
- Backend ask: Ahmed runs `railway login` for env-var MCP access
- Pre-flight: confirm `git push origin main` has no uncommitted/un-pushed changes

### Phase 1 — Foundation (parallel, day 1, no inter-agent blocks)
- **Backend**: `/api/v1/legal/*` Privacy + Terms fix · Preferences save fix · Supabase Auth Apple provider config · `/api/v1/auth/refresh` rotation audit · C13 `delete_user_cascade` SQL extension · C14 Sentry query-string scrub · C15 legal-doc rebrand
- **Frontend**: refresh-token mutex (R9 — module-scope singleton) · EditProfile `profile.name` i18n add · "Edit style profile" nav fix (decision: extract `StyleProfileScreen` modal OR register Onboarding permanently with `mode` param) · Camera help overlay · History detail fetch fix (after Backend C3-check confirms schema_version cause) · C17 `ai_sharing_enabled` default OFF
- **Native/Ops**: Bundle ID claim (try `app.qaren` reverse-DNS first since Ahmed owns `qaren.app`; fallback `com.qaren.app`) · Apple Developer Portal Service ID · `expo-apple-authentication` install + `app.json` plugin · `@react-native-google-signin` config double-check · EAS secret `SENTRY_AUTH_TOKEN` create · C16 expo-notifications plugin · DNS planning for qaren.app
- **Test**: red-green test scaffolds for all above; cover happy + sad paths
- **QA**: cross-QA matrix template + Sentry MCP baseline snapshot (so Phase 4 diff is measurable) + R1-R24 risk ledger initialization

### Phase 2 — Integration (depends on Phase 1, day 1-2)
- **Backend**: 5 v1.1 polish (B.0 → A.7.2 → A.8.1 → A.4.8 → A.6.2-A.6.5 in dependency order; B.0 first because it greens 3 RED tests) + 24 `_fire_and_forget` audit sweep
- **Frontend**: Profile toggle optimistic UI + 5-toggle wiring audit (depends on Backend preferences save fix) · HomeScreen Claude-Design refresh implementation (depends on Ahmed-provided design tokens)
- **Native/Ops**: EAS preview build (`eas build --profile preview --platform ios`) → unblocks Google + Apple runtime smokes · Landing page hosting setup (Vercel/Netlify; placeholder if Ahmed hasn't provided design yet)
- **Test**: extend coverage to Phase 2 work
- **QA**: cross-review Phase 1 work; send-back loop opens

### Phase 3 — TestFlight pipeline (depends on Phase 2 EAS preview build, day 2)
- **Native/Ops**: EAS production build → App Store Connect upload → wait for Apple processing (~30min) → configure internal test group → invite Ahmed + ≤9 testers
- **Backend**: full prod Railway curl smoke pack (auth + compare + legal + preferences + history + social_login Apple + social_login Google)
- **Frontend**: PR #6 EN+AR simulator walkthrough on EAS preview build → screenshots + analytics log capture → post PR #6 sign-off comment per template at `.pr-6-phase4-comment.md`
- **Test**: full pytest + `npx tsc --noEmit` + `npx jest` clean across all touched files
- **QA**: cross-review Phase 2 work; send-back loop closes by end of phase

### Phase 4 — Close-out (day 2-3)
- **Backend**: force-update env vars set (`APP_MIN_VERSION` = current TestFlight build version; `APP_LATEST_VERSION` matches; `APP_FORCE_UPDATE=false` initially per R19) + reengagement flag flip `ENABLE_REENGAGEMENT_PUSHES=true` (AFTER Ahmed confirms first cron tick safe)
- **Native/Ops**: app icon + splash final audit (no "SmartCompare" residue, EN+AR look right at all densities; densities @1x/@2x/@3x iOS, mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi Android)
- **Test**: final test sweep
- **QA**: 30-min Sentry MCP watch post-TestFlight upload + Supabase audit-log SQL pack
- **All 5 agents**: file individual sign-off in PR comment (per § 9 rubric)
- **Dispatcher**: merge `--no-ff` to main after all 5 sign-offs present + QA explicit GREEN

---

## 6. File-touch maps

**Backend** (~10 files):
- `app/api/legal_routes.py` (load fail root-cause)
- `app/api/auth_routes.py` (preferences + refresh + Apple social_login)
- `app/api/history_routes.py` (`schema_version=2` filter check)
- `app/api/*.py` (24 `_fire_and_forget` sweep sites)
- `app/services/response_builder.py` (B.0 kwarg + A.7.2 strip)
- `app/services/scoring_service.py` (A.8.1 + A.6.2-A.6.5)
- `app/services/extraction_service.py` (A.4.8)
- `app/services/sentry_service.py` (C14 query-string scrub)
- `app/legal/{privacy_policy,terms_of_service}.md` (C15 rebrand)
- `migrations/025_delete_user_cascade_completeness.sql` (C13; new migration)

**Frontend** (~12 files):
- `src/screens/HomeScreen.tsx` (redesign)
- `src/screens/HistoryScreen.tsx` + `ResultsScreen.tsx` (history detail)
- `src/screens/LegalScreen.tsx` (retry UX)
- `src/screens/EditProfileScreen.tsx` (i18n + nav)
- `src/screens/ProfileScreen.tsx` (optimistic toggles + C17 default)
- `src/screens/ScanCameraScreen.tsx` (help overlay)
- `src/services/api.ts` (refresh-token mutex + getComparison)
- `src/services/authService.ts` (Google + Apple wiring)
- `src/theme/index.ts` (Claude-Design token extension)
- `src/i18n/en.json` + `ar.json` (profile.name + camera help + any new copy)
- `App.tsx` (Onboarding registration decision)

**Native/Ops** (~5 files + 3 web consoles):
- `app.json` (`expo-apple-authentication` plugin + `expo-notifications` plugin + iOS entitlements + bundle ID + version)
- `package.json` (new deps if needed)
- `eas.json` (preview + production + submit profiles + iOS distribution cert reference)
- `assets/icon.png` + `assets/splash.png` (if updates needed)
- Apple Developer Portal (Service ID, entitlement, provisioning profile) — web console
- App Store Connect (app record, bundle ID claim, TestFlight, Privacy Nutrition Labels) — web console
- Supabase Auth dashboard (Apple provider enable) — web console

---

## 7. Memory anchor docs (anti-hallucination)

**Architecture:** 6 docs, dispatcher writes in Phase 0. Each agent reads their anchor BEFORE starting any work.

| Doc | Owner | Contents |
|---|---|---|
| `BUNDLE_D_BACKEND_ANCHOR.md` | Backend agent | Scope items (33) with file:line + acceptance criteria + verification commands + risk subset + dependency map + rollback recipe |
| `BUNDLE_D_FRONTEND_ANCHOR.md` | Frontend agent | Same shape (13 items) + HomeScreen redesign Bundle B contract preservation list + Claude-Design token consumption rules |
| `BUNDLE_D_NATIVE_OPS_ANCHOR.md` | Native/Ops agent | Same shape (13 items) + Apple Dev Portal step-by-step + EAS build commands + ASC Privacy Nutrition Labels draft answers + bundle ID fallback ladder |
| `BUNDLE_D_TEST_ANCHOR.md` | Test agent | 80% coverage target per touched file + pre-existing-failure triage list (3 known RED tests + B.0-greens-test-X mapping) |
| `BUNDLE_D_QA_ANCHOR.md` | QA agent | Cross-QA review template + R1-R24 verification checklist + send-back protocol + production smoke pack + Sentry MCP watch script |
| `BUNDLE_D_RISK_LEDGER.md` | Dispatcher-owned | Master R1-R24 list + preventive control per risk + rollback recipe per change + status tracker (ADDRESSED / N/A / ACCEPTED / PENDING) |

**Per-agent anchor template:**
```
## My scope (N items)
1. [item] — file:line + acceptance criterion + verification command
...
## Memory facts I need (anti-hallucination)
- verify_token returns {id, email, access_token} per audit-r2 51385d3
- /admin/* CSP allows 'unsafe-inline' + cdn.jsdelivr.net; rest of app strict
- saved_comparisons.schema_version=2 filter excludes legacy rows
- ...
## Pre-flight (run before starting)
$ git log --oneline -5
$ git status
$ <lane-specific health check>
## Verification commands (run before "done")
$ <test cmd 1>
$ <test cmd 2>
$ <prod smoke cmd>
## Risks I own (subset of R1-R24)
- R1: snapshot middleware → edit → diff → reject reorder
- R3: check schema_version on Ahmed's failing comparison ID first
- ...
## Dependencies (who I wait on)
- Blocked by: <agent>:<task>
- Blocking: <agent>:<task>
## Rollback recipe (3 lines max)
- Revert: git revert <commit>
- Redeploy: git push origin main → Railway 90s
- DB: <migration_rollback_file.sql> if applicable
```

---

## 8. Leak-prevention controls (defense-in-depth)

Per Ahmed instruction: "we dont want leaks or gaps so risks should be overcome and errors or issues prevented."

| Layer | Mechanism | Catches |
|---|---|---|
| **L1: Pre-flight snapshots** | Each agent runs `git show HEAD:<critical-file>` and saves to `/tmp/<name>-snapshot` before editing. Post-edit diff must not touch off-limits sections. | R1 (admin middleware reorder), R2 (CSP scoping) |
| **L2: Mandatory regression suite** | Before sign-off: `pytest tests/test_security_regression.py` (~98 tests) + `npx tsc --noEmit` + `npx jest`. Zero new failures. Pre-existing failures explicitly listed with triage. | R1, R2, R9, all backend regression risks |
| **L3: Cross-QA verification with risk citations** | QA agent's review template includes one line per R# touched by the change: "R<N>: [verified via <command>] PASS/FAIL". Send-back if any R# unverified. | All risks |
| **L4: Production curl smokes per Phase** | After each Phase merge to bundle branch: run prod-Railway curl pack (auth + compare + legal + preferences + history). Fail → roll back Phase. | R3 (legal regression), R4 (Apple provider), live auth |
| **L5: Sentry MCP watch** | QA agent baselines Sentry issue count at Phase 0. At Phase 3 close-out, runs `search_issues firstSeen:-2d` — ANY new issue type over baseline = block merge until triaged. | All runtime risks |
| **L6: Three-confirmation rule** | Every "done" claim needs: (a) test green (b) cross-QA approval (c) prod smoke where applicable. Two-of-three is NOT done. | False sign-offs |
| **L7: Risk ledger gate** | Dispatcher reviews `BUNDLE_D_RISK_LEDGER.md` before merging PR — every R# must have a status: ADDRESSED (with citation) / N/A (with reason) / ACCEPTED (with explicit user approval). NONE in PENDING. | Silent risk acceptance |
| **L8: Rollback recipe per change** | Every change has a 3-line rollback recipe in the agent's anchor doc. Dispatcher mentally verifies before merge. | Bad-ship recovery time |

---

## 9. Success criteria + sign-off rubric

### Per-lane GREEN gate

**Backend lane:**
- ✓ All 5 v1.1 polish items shipped (B.0 + A.7.2 + A.8.1 + A.4.8 + A.6.2-A.6.5)
- ✓ All 24 `_fire_and_forget` audit sites wrapped + judged (no blanket-wrap)
- ✓ C13/C14/C15 complete
- ✓ `pytest tests/test_security_regression.py` 100% pass
- ✓ Pre-existing baseline ≥ 503/503 maintained
- ✓ 3 RED tests triaged (`TestReengagementSubToggles`, `test_phase1_includes_reviews`, `test_comparison_quality_in_response_metadata_payload`) — either GREEN or explicit deferral
- ✓ Prod-Railway curl pack green: `/api/v1/legal/{privacy,terms}` 200 · `/api/v1/auth/preferences` save 200 · `/api/v1/auth/refresh` concurrent-refresh dedup verified · `/api/v1/auth/social/apple` 200
- ✓ Reengagement subs endpoint exists or created (R18)
- ✓ Cross-QA approval from QA agent

**Frontend lane:**
- ✓ All 11 mobile bug fixes shipped (incl. HomeScreen redesign + C17)
- ✓ `npx tsc --noEmit` clean (0 errors)
- ✓ `npx jest` ≥1011/1011 + 30 snapshots passing (Bundle B baseline)
- ✓ HomeScreen redesign passes Bundle B PR #6 EN+AR walkthrough on EAS preview build (TwoInputShell paste-split + mode-switch + content moderation all green)
- ✓ Refresh-token mutex verified as module-scope singleton (PR comment code excerpt)
- ✓ EditProfile: `profile.name` resolves EN+AR; "Edit style profile" navigates successfully
- ✓ Camera `?` shows help overlay; Profile toggles update optimistically (≤100ms perceived); 5 toggles confirmed wired end-to-end to backend
- ✓ Sentry RN scrub pattern still matches backend (regression check)
- ✓ Cross-QA approval

**Native/Ops lane:**
- ✓ EAS preview build green on iOS device/simulator
- ✓ EAS production build uploaded to App Store Connect + Apple-processed
- ✓ TestFlight internal test group configured; Ahmed received invite + installed + cold-start green
- ✓ App icon + splash final at all densities, EN+AR look right, zero "SmartCompare" residue
- ✓ Apple Sign-In entitlement verified in both Apple Dev Portal + `eas.json` (R14)
- ✓ Bundle ID claim verified in ASC (R6 fallback ready if conflict)
- ✓ Sentry sourcemap upload green on most recent EAS build
- ✓ Apple 3-leg checkpoint complete (Service ID ✓ / .p8 downloaded ✓ / Supabase provider ON ✓ / backend social_login curl 200 ✓)
- ✓ ASC Privacy Nutrition Labels filled (Ahmed approved)
- ✓ Landing page live at `qaren.app` (placeholder OK if Ahmed hasn't shipped Claude-Design output yet)
- ✓ `qaren.app/privacy` + `qaren.app/terms` subpages live with rewritten content
- ✓ C16 expo-notifications plugin verified working
- ✓ Cross-QA approval

**Test lane:**
- ✓ ≥80% line coverage on every file touched by Backend + Frontend
- ✓ Net new tests ≥ count of new features
- ✓ Zero net new RED (pre-existing triaged, no new ones)
- ✓ Cross-QA approval

**QA lane (FINAL REVIEWER):**
- ✓ `BUNDLE_D_RISK_LEDGER.md` — every R1-R24 status: ADDRESSED / N/A / ACCEPTED. NONE in PENDING.
- ✓ Cross-QA matrix filled for all 4 implementation agents
- ✓ Production curl smoke pack runs 100% green at Phase 3 close
- ✓ Sentry MCP 30-min watch post-deploy: ZERO new issue types over Phase-0 baseline
- ✓ Supabase audit-log SQL pack: privacy invariants hold (no raw text in audit, `query_hash` = 64-char hex on every row)
- ✓ PR #6 Bundle B sign-off comment posted with screenshots + analytics log
- ✓ Final GREEN comment posted in Bundle D PR

### Team disassembly gate

Team CANNOT disassemble until all 5 lane sign-offs are GREEN in the PR. If any RED:
- Send-back to owner agent
- Owner re-does
- Cross-QA re-runs
- Re-post sign-off
- Idle agents write red-green tests per Ahmed instruction
- Dispatcher polls inbox every 30 min; OP #8 escalation if silent

### Bundle-level GREEN gate (dispatcher merges PR only when):

- All 5 lane sign-offs GREEN
- All R1-R24 documented in risk ledger (none PENDING)
- TestFlight build live + Ahmed installed + tested end-to-end smoke flow on device
- Final `git push origin main` → Railway redeploy verified green (90s + curl smoke)
- CLAUDE.md updated with Bundle D entry (per OP #5)
- MEMORY.md + `docs/CONTEXT_SESSION_LOG.md` updated
- Dispatcher posts final "Bundle D verified" comment with timestamp + commit SHA

### Rollback triggers

- New Sentry issue type post-merge → `git revert <merge_commit>` → push → Railway 90s
- TestFlight build crashes → keep prior EAS preview build live; do not promote production
- Production curl smoke fails → roll back, post-mortem before retry
- Each agent's anchor has a 3-line rollback recipe (L8 control)

---

## 10. Risk ledger (R1-R24)

| # | Risk | Preventive control | Owner |
|---|---|---|---|
| R1 | `/admin/*` static auth gate (audit C2) regression — `app/main.py` middleware order load-bearing | Backend snapshots middleware → edit → diff → reject reorder; PR sub-commit isolates middleware changes | Backend |
| R2 | CSP scoping — admin pages allow `'unsafe-inline'` + `cdn.jsdelivr.net`, rest strict `default-src 'none'` | No inline scripts on non-admin pages; reject any diff that broadens CSP allow-list | Backend |
| R3 | `schema_version=2` filter excludes legacy v1 rows — History detail fail may be working-as-designed | Backend's FIRST action on history detail = query Supabase for failing comparison's `schema_version`; if v1 → backfill + relax filter, not new screen code | Backend |
| R4 | Apple Sign-In three-leg dependency (Service ID → .p8 → Supabase provider → backend test) | Native/Ops posts "Apple 3-leg checkpoint" comment with all 4 green before Frontend wires the button | Native/Ops |
| R5 | `expo-apple-authentication` is a config plugin — first EAS build fails if `app.json` plugin block missing | Native/Ops commits `app.json` plugin block FIRST in own commit BEFORE triggering any EAS build | Native/Ops |
| R6 | Bundle ID conflict (`com.qaren.app` may be taken in ASC) | Native/Ops research bundle ID availability FIRST; fallback ladder `app.qaren` → `com.qaren.app` → `bh.qaren.app` ready; escalate to Ahmed before proceeding | Native/Ops |
| R7 | EAS production build signing — first build needs Apple Distribution cert + provisioning profile | Native/Ops sets up Apple Dev Portal provisioning profile FIRST; EAS auto-manages signing if `eas.json` ios.credentials configured | Native/Ops |
| R8 | App Store Connect 30-min upload+processing window | Phase 3 timing budgets this explicitly; tester invite waits until processing complete | Native/Ops |
| R9 | Refresh-token mutex must be module-scope singleton | Frontend PR comment includes code excerpt showing singleton `Promise` cached at module scope, not function scope | Frontend |
| R10 | HomeScreen Claude-Design output integration — token conflicts with existing `src/theme/index.ts` | Frontend extends theme, doesn't replace; tokens applied additively; cross-QA verifies no breaking theme change | Frontend |
| R11 | `profile.name` i18n naming — `profile.title`/`profile.editProfile` exist; new key conflicts? | Frontend agent picks "Name" / "الاسم" as default; if Ahmed wants different (e.g., "Display name"), agent asks before commit | Frontend |
| R12 | Reengagement flag flip ON during TestFlight may spam testers if cron has bug | Backend confirms cron stable + payload-safe BEFORE flipping; Phase 4 dispatcher action only after Ahmed acknowledges | Backend |
| R13 | App Privacy Nutrition Labels — Apple still asks for these even for internal TestFlight | Native/Ops drafts based on observed data flows; Ahmed approves answers before ASC submission | Native/Ops |
| R14 | Apple "Sign in with Apple" entitlement must exist in BOTH Apple Dev Portal + `eas.json` `ios.entitlements` | Native/Ops anchor includes literal entitlements snippet to paste; checklist verifies both locations | Native/Ops |
| R15 | 24 `_fire_and_forget` audit sites — false positives (some legitimate plain `create_task` sites) | Backend judges per site; PR comment lists each site with decision (WRAP / SKIP-with-reason) | Backend |
| R16 | HomeScreen redesign may REMOVE TwoInputShell behavior | Frontend acceptance test = full Bundle B PR #6 EN+AR walkthrough on new design; ZERO regressions on TwoInputShell contract | Frontend |
| R17 | Camera help button i18n — new copy must pass scary-vocab gate | Frontend uses approved vocabulary; copy-policy test (`.copy-policy.json`) catches violations | Frontend |
| R18 | Profile toggle wiring — Reengagement subs endpoint may not exist | Backend FIRST action = grep for `reengagement_subscriptions` table + endpoint; if missing, Backend creates BEFORE Frontend wires UI | Backend |
| R19 | Force-update env vars dangerous — `APP_FORCE_UPDATE=true` boots all old-version users | Sequence: `APP_MIN_VERSION` = TestFlight build version FIRST; flip `APP_FORCE_UPDATE=true` only AFTER all testers on new build | Backend |
| R20 | C13 `delete_user_cascade` SQL changes must not break existing cascade flow | Backend writes migration 025 with rollback file; tests delete flow end-to-end on staging Supabase before prod apply | Backend |
| R21 | C14 Sentry query-string scrub — `_before_send` regex must not eat legitimate non-PII URL data | Backend writes targeted regex (matches `?q=`, `?query=`, `?email=` patterns; preserves `?nocache=true`, `?token=` already handled); test pack verifies | Backend |
| R22 | C15 legal-doc rebrand — risk of breaking existing in-app rendering if markdown structure shifts | Backend rewrites brand strings only, preserves heading/paragraph structure; FE LegalScreen renders unchanged | Backend |
| R23 | C17 `ai_sharing_enabled` default flip OFF — existing users with ON should NOT be reset | Frontend default applies to NEW users only; existing `users.preferences.ai_sharing_enabled = true` rows untouched; verified via SQL spot-check | Frontend |
| R24 | Landing page hosting (O1-O3) — DNS propagation delay could leave qaren.app offline mid-cutover | Native/Ops sets up hosting + tests via direct hostname FIRST; DNS cutover only after green; TTL set low (300s) for fast revert | Native/Ops |

---

## 11. Defaults applied (per Ahmed sign-off)

| # | Decision | Default |
|---|---|---|
| 1 | Branch name | `feature/bundle-d-testflight-readiness` |
| 2 | Bundle ID | Try `app.qaren` first (reverse-DNS of owned `qaren.app`); fallback ladder `com.qaren.app` → `bh.qaren.app` → escalate to Ahmed |
| 3 | Internal TestFlight tester list | Ahmed only at Phase 3 close; ≤9 more invited via separate session |
| 4 | ASC Privacy Nutrition Labels | Native/Ops drafts based on observed data flows (Contact Info / Identifiers / Usage Data / User Content / Diagnostics); Ahmed approves in PR before ASC submission |
| 5 | `profile.name` i18n value | EN: "Name" / AR: "الاسم" (unless Ahmed override) |
| 6 | Reengagement subs endpoint shape (if missing) | `PUT /api/v1/auth/reengagement-subs` body `{decision_insights: bool, peer_decision_updates: bool, decision_retrospectives: bool}` |
| 7 | `ENABLE_REENGAGEMENT_PUSHES` flip timing | Phase 4 dispatcher flip AFTER Ahmed installs TestFlight build + acknowledges first cron tick is safe |
| 8 | Apple Developer Team ID | Ahmed pings when Native/Ops requests; not blocking design doc |
| 9 | Landing page artifact | Ahmed provides Claude-Design output OR Native/Ops ships "Coming soon" placeholder |

---

## 12. Out of scope (deferred to follow-up bundles)

- **Bundle B 7 deferred polish items** (recent searches, autocomplete, voice input, soft hints, sound on celebration, per-mode CTA labels, admin content_safety dashboard) — tester data should drive triage
- **External TestFlight (up to 10,000)** — needs Apple Beta App Review, full 15 legal decisions resolved, App Privacy Nutrition Labels final, Beta App Description; separate bundle once internal testers validate
- **Full legal-doc redraft** — C15 only swaps brand strings; full Qaren-specific ToS/Privacy redraft per `docs/plans/2026-05-16-tos-decisions-pending.md` (15 items) is a separate legal-decisions bundle
- **HomeScreen UI variants** (`HomeScreen.redesign.test.tsx`, `.modeChipAnim.test.tsx`, `.scanCamera.test.tsx`, `.minDisplayFloor.test.ts`) re-mocking — pre-existing red tests from Bundle B `21e7bc0`; not introduced by Bundle D. The 4 files together account for the 13 RED jest cases at the `1118/1131` baseline.
- **`tests/test_phase1_includes_reviews.py::test_phase1_runs_reviews_in_parallel_with_specs_price`** — pre-existing RED asserting reviews run in Phase 1 parallel with specs+price (<1.2s wall budget). This is a D2 Intervention 1 follow-up; restructuring `_fetch_product_data` to start review fetch in Phase 1 is a price-pipeline change, not TestFlight-readiness. Triage doc anchor: `docs/plans/bundle-d-red-test-triage.md` row 2.
- **Apple App Store production submission** — separate from TestFlight; happens once internal + external testing complete

---

## 13. Open items Ahmed will fill during execution

- Apple Developer Team ID (Native/Ops will ping)
- Apple Developer Program account holder email (Native/Ops will ping for ASC)
- ASC Privacy Nutrition Labels approval (Native/Ops drafts, posts to PR for Ahmed approval)
- Landing page Claude-Design output (Ahmed provides when ready; placeholder ships otherwise)
- Bundle ID choice if all 3 fallbacks taken (Native/Ops will escalate)
- Profile `profile.name` text if Ahmed wants different from "Name" / "الاسم"
- `ENABLE_REENGAGEMENT_PUSHES=true` flip approval (Phase 4 explicit ack)

---

## Next step (per brainstorming skill)

Invoke `writing-plans` skill to produce the detailed implementation plan that the 5-Opus team will execute.
