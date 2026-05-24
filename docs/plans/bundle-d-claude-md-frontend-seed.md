# Bundle D — Frontend Seed for CLAUDE.md + MEMORY.md (Phase 4 close-out)

**Purpose:** Pre-drafted Frontend-side inserts dispatcher pastes into `CLAUDE.md` and `memory/MEMORY.md` during Bundle D Phase 4 close-out per design § 9. Saves re-discovery time at merge gate.

**Scope:** Frontend lane only. Backend / Native-Ops / Test / QA lanes own their own seeds.

**Author:** Frontend agent (Bundle D worktree, branch `feature/bundle-d-testflight-readiness`).

---

## CLAUDE.md — "Frontend (React Native + Expo)" section delta

Insert at end of the existing "Services:" sub-section (after the `sentry.ts` entry), before any subsequent section:

```markdown
### Bundle D additions (2026-05-23)
- **Refresh-token mutex** at `SmartCompareApp/src/services/api.ts:47` — module-scope singleton `Promise<RefreshResult> | null` deduplicates concurrent 401-triggered refreshes (R9). Test hooks `__resetRefreshMutex()` + `__testRefreshDedup()` exported for test only.
- **Camera help overlay** at `SmartCompareApp/src/components/CameraHelpOverlay.tsx` — Modal-based 3-step explainer wired to the `?` button on ScanCameraScreen (R17). i18n keys: `home.camera.help.{title,step1,step2,step3,close}`.
- **`ai_sharing_enabled` default OFF** at `SmartCompareApp/src/screens/ProfileScreen.tsx:97` — `?? false` (opt-IN per App Store privacy / R23). Distinct from re-engagement sub-toggles which use `!== false` (opt-OUT) per onboarding-step-17 intent — see in-source comment at ProfileScreen.tsx:189.
- **`putReengagementSubs()`** at `SmartCompareApp/src/services/api.ts` — wrapper for `PUT /api/v1/auth/reengagement-subs` with plural-keyed body `{decision_insights, peer_decision_updates, decision_retrospectives}` (R18 FE-side; backend translates plural → singular DB keys server-side per Backend `228ff63`).
- **Edit-style profile re-entry** at `SmartCompareApp/App.tsx` authed-branch stack — Onboarding screen registered twice (needs-preferences branch + authed-mode-edit branch). `NewOnboardingHost` accepts `mode: 'full' | 'edit'` + `onEditDone` props; edit-mode jumps to step 8 and terminates at step 10 via `OnboardingFlow` `lastStep` prop.
- **Bundle D Claude-Design tokens skeleton** at `SmartCompareApp/src/theme/bundleD.ts` — 5 empty namespace objects (`bundleDColors / bundleDTypography / bundleDSpacing / bundleDRadii / bundleDShadows`) re-exported from `theme/index.ts`. R10 additive contract — legacy tokens unchanged; pages migrate one-by-one.
- **Bundle B contract preservation suites** at `SmartCompareApp/__tests__/HomeScreen.bundleB.contract.test.tsx` (48 PASS + 5 TODO) + `SmartCompareApp/__tests__/Screens.bundleD.contract.test.ts` (44 PASS + 8 TODO) — source-grep behavior contracts that MUST survive the Claude-Design redesign. Includes 8 concrete testID-preservation assertions across 7 screen / component files. Drop-in workflow: replace page .tsx → run matching describe block → any RED pinpoints exact invariant broken (R16 FE-side first leg).
- **EAS preview smoke runbook** at `docs/runbooks/bundle-d-eas-preview-smoke.md` — 9-section / 45-60 min walkthrough covering 7 risk device-legs (R4 R9 R10 R16 R17 R18 R23).
```

Note for dispatcher: the existing CLAUDE.md "Frontend (React Native + Expo)" section may already mention some of these from prior bundle entries — DEDUPE on insert; keep the most recent description per item.

---

## CLAUDE.md — Environment Variables section delta

Backend lane will mention their flag changes. Frontend has no new env vars in Bundle D; no insert.

---

## CLAUDE.md — Bundle history (sessions 44-52) update

Append new line to the existing bundle-history paragraph:

```markdown
**Bundle D — TestFlight Readiness (Session 53, 2026-05-23)** SHIPPED. 5-Opus team (Backend / Frontend / Native-Ops / Test / QA + dispatcher). 24 risks; 21+ ADDRESSED at merge gate (3 PENDING are R10 + R16 device-legs awaiting Claude-Design prototype + 2.N.1 EAS preview build). Frontend deliverables: refresh-token mutex (R9), profile.name i18n (R11), Edit-style nav fix, camera help overlay (R17), history detail pin (R3 backfill from Backend), ai_sharing OFF default (R23), 5-toggle wiring with optimistic UI (R18), Bundle B contract preservation framework (R16 first leg), per-page contract framework, EAS preview smoke runbook, theme/bundleD.ts skeleton. See `memory/BUNDLE_D_RISK_LEDGER.md` for ledger.
```

---

## memory/MEMORY.md — "Pending follow-ups" cleanup

Move these FE-side resolved items from "Pending follow-ups" to a new "Resolved Bundle D 2026-05-23" section (or delete entirely if already covered by anchor / risk ledger):

Items to mark resolved:
- Refresh-token mutex (was an audit-2026-05-22 follow-up — R9 ADDRESSED via `03b9139`)
- `ai_sharing_enabled` default OFF (was code-side blocker C17 — R23 ADDRESSED via `7b5a35d`)
- Camera help overlay wiring (was Phase 1.F.4 placeholder — R17 ADDRESSED via `6bd81a0`)
- Edit-style profile nav fix (was a Bundle B regression — 1.F.3 ADDRESSED via `7c677c9`)
- Bundle B PR #6 simulator sign-off framework (3.F.1 pre-staged via contract suites)

Items to keep PENDING (carry into next bundle):
- HomeScreen Claude-Design integration (R10 + R16 device legs — blocked on Ahmed prototype; framework ready)
- 2.N.1 EAS preview build (blocked on Native/Ops + Ahmed)
- 4.N.1b Expo placeholder asset replacement (blocked on Ahmed A5 Claude-Design icon)
- 1.N.5 SENTRY_AUTH_TOKEN secret + sourcemap upload (Native/Ops)
- v1.2 backlog items: A.8.2 unified dimension adapter, etc. (Backend lane — already logged at `8af0a24`)

---

## memory/MEMORY.md — new feedback memory entries

Add these as new feedback memories under `memory/` (each as its own file, indexed in `MEMORY.md`):

### Suggested filename: `feedback_source_comment_growth_invalidates_grep_regex.md`
```markdown
---
name: Source-comment growth invalidates source-grep regex windows
description: Adding comments to a source file can break source-grep contract tests if regex char-window bounds are tight
type: feedback
---
When you write a source-grep contract test (e.g. `__tests__/Screens.bundleD.contract.test.ts` patterns like `/handleSubToggle[\s\S]{0,1200}putReengagementSubs/`), the char-window bound must allow for FUTURE comment additions to the source file.

**Why:** Bundle D 2.F.1 — I committed a 9-line policy comment between `handleSubToggle` and `putReengagementSubs` in ProfileScreen.tsx. The 1200-char window (~25% margin at original) became too tight (1543 chars actual). Test went RED on the next combined-suite run.

**How to apply:**
- New source-grep test: pick a char window with ≥30% headroom over current measured distance
- Existing test fired RED after a comment edit: widen the window (not refactor the source)
- Re-run combined contract suite AFTER any source-file comment additions, not just behavior changes — the single-file solo re-run won't surface it if the broken assertion is in a sibling test file
```

### Suggested filename: `feedback_grep_before_pinning_testIDs.md`
```markdown
---
name: grep-before-pinning testIDs in preservation frameworks
description: Verify testID exists on shipped code before adding to a preservation test
type: feedback
---
When adding testID-preservation assertions to a contract test (Bundle D R16 framework), grep the source for the literal string FIRST. Pinning a testID that doesn't exist makes the test pass vacuously today AND fail mysteriously post-redesign even if the redesign correctly reproduces the visual component.

**Why:** Bundle D Ask 4 cycle — QA suggested 6 testIDs to pin (`home-center-area`, `two-input-shell`, `image-slot-X`, `scan-camera-*`, `camera-help-overlay-*`, `onboarding-*`, `results-empty-state`, `winner-card`, `paywall-modal`, `comparison-counter`). Independent grep showed `paywall-modal` and `comparison-counter` don't exist on shipped code; QA self-corrected, frontend didn't pin them. `winner-card-anim` exists conditionally (only when `isWinner=true` per ResultsScreen.tsx:640) and was pinned via literal-string regex.

**How to apply:**
- Suggesting agent: `grep -rn 'testID="X"' src/` before suggesting
- Consuming agent: same grep before adding the assertion to a contract test
- For conditional mounts (testID inside ternary), use literal-string regex `/testID=\{[^}]*['"]X['"]/` not a family-prefix pattern
```

---

## Dispatcher integration checklist (Phase 4)

- [ ] Paste CLAUDE.md "Bundle D additions" block at end of "Frontend (React Native + Expo)" section's Services sub-section
- [ ] Append "Bundle D — TestFlight Readiness" line to bundle-history paragraph
- [ ] Reorganize MEMORY.md "Pending follow-ups" — move 5 items to "Resolved Bundle D 2026-05-23"
- [ ] Create 2 new feedback memory files (with frontmatter); add 1-line index entries to MEMORY.md per the auto-memory protocol
- [ ] Confirm CLAUDE.md ≤ 270 lines after edits (current target per MEMORY.md "Context File Strategy")

Frontend lane responsibilities documented; ship via dispatcher in same commit as the bundle merge or as a follow-up `docs(claude-md)` commit.
