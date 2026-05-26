# Bundle E — Tomorrow Session Handoff

**Filed:** 2026-05-26 (end of Bundle E day-1 session, ~9 hours team execution)
**Status:** S0 SEALED + S1 80% complete with RED items + S2 not started.
**Purpose:** Resume Bundle E in a fresh session with full context. Do NOT carry today's compaction state; it includes ~9 hours of agent coordination + B4 debugging.

---

## Read me first (next session)

Before doing anything:

1. **This file** (`bundle-e-tomorrow-handoff.md`) — full state snapshot
2. **`docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md`** — design contract (canonical spec). Already patched with QA § 6 audit findings (Step01 QuoteRow, Step12 PeerLattice, Step15 MatchBadge).
3. **`docs/plans/bundle-e-visual-fidelity.md`** — executable plan (canonical, with TDD pattern example in B3.1).
4. **`docs/plans/bundle-e-s2-prep.md`** — frontend's S2 prep notes covering 10 onboarding steps (shipped at `499b2a3`).
5. **`docs/claude-design-handoff/ui_kits/mobile/*.jsx`** — 15 reference JSX files (the SPEC per Claude-Design handoff README).
6. **`docs/claude-design-handoff/screenshots/*.png`** — 22 Playwright-rendered references at retina.

---

## Today's wins

### S0 Foundation — SEALED ✅ (Q-S0 gate GREEN)

7 commits, tsc 0, Jest 1340 PASS. Delivered:
- 5 hero SVG illustrations under `SmartCompareApp/src/components/hero/` (PhoneMockup, ConcentricMotif, PeerLattice, LoadingRings, RevealBurst) — react-native-svg + Reanimated, zero Lottie.
- 12 primitives under `SmartCompareApp/src/components/primitives/` (VsPair, ProductBlock, DetailsAccordion, OptionRow, MarqueeCard, ConfidencePill, DimensionBar, MatchBadge, StatBlock, QuoteRow, CohortBullet, SlideTransition).
- Motion tokens in `src/theme/motion.ts` — 7 Bundle E tokens (accordionChevron, ctaGlow, modeSegment, shimmer, counterTick, revealBurst, screenTransition with `mirrorRTL: true`).
- `src/utils/deriveTone.ts` — brand→tone hex util (29/29 snapshot test GREEN).
- CohortBarChart deleted (no JSX consumer per QA audit).

### Backend lane — DONE ✅

All deliverables shipped:
- B3 priorities-weighted normalize regression test (`a686b7d`) — verifies sum=100 largest-remainder Hamilton method.
- `/home/trending` reshape `{tag, a, b, count}` (`dca8067`) — additive + legacy compat.
- `/home/smart-pick` extend with `category`, `updated_at`, `winner_sub`, `runner_up_sub`, `verdict_short` (`3bb31bd`) — null-when-absent.
- Endpoint shape contract test vs JSX (`2bcbb14`) — declarative manifest, catches future drift.
- B-XQA primitive contracts audit (`94f9e0a`) — 5/5 CLEAN, zero gaps.
- B-S2.idle cohort + scoring load smoke (`567f6bd`) — double-gated (live_unit + RUN_LOAD=1).

### B4 Google sign-in — RESOLVED ✅

Root cause: Supabase enforces nonce parity between request body and id_token claim. Google iOS SDK auto-embeds a hashed nonce but doesn't expose the raw value to JS, so `SHA-256(raw) === claim` is mathematically impossible from FE.

**Resolution:** Ahmed enabled "Skip nonce checks" in Supabase Dashboard → Authentication → Providers → Google. Verified end-to-end: Google sign-in → onboarding → Step 17 Finish → lands in Home tab.

Side-fix shipped during diagnosis (worth keeping):
- **B4 navigation hotfix** — `2e1ceb7` — renamed post-auth edit-mode `<Stack.Screen name="Onboarding">` → `OnboardingEdit` to fix RN-Navigation-v7 duplicate-name bug that caused Step 17 Finish to leave user stuck on Step 17 instead of swapping to MainTabs. Updated 2 call sites in EditProfileScreen + ProfileScreen.

### S1 Tab surfaces — 8/8 composed (but with RED items)

| Stage | Commit | Screen |
|---|---|---|
| F-S1.1 | `07dadbb` | PaywallScreen |
| F-S1.2 | `6d0e8f8` | LoginScreen |
| F-S1.3 | `a523767` | Step16Account |
| F-S1.4 | `1d49d4b` | HomeScreen |
| F-S1.5 | `b713043` | ProfileScreen |
| F-S1.6 | `bc83688` | HistoryScreen |
| F-S1.7 | `0ad3815` | ScanCameraScreen |
| F-S1.8 | `0fab1ed` | ResultsScreen |
| F-S1.0 | `1acb4d8` | deriveTone snapshot test (29/29 GREEN) |

### Test lane — chained per-screen integration tests + B4 regression

- T-S1.3a Home contract test (9/9 GREEN once F-S1.4 shipped)
- T-S1.3b PaywallScreen integration test (`d28691f`, 13/13 GREEN)
- T-B4.NONCE-FINAL pin no-nonce invariant (`c8a91c2`, post-Supabase-toggle)
- Per-screen fixtures (`__tests__/fixtures/bundleE-endpoint-mocks.ts`)
- SlideTransition RTL snapshot
- `tests/integration/bundle-e-smoke.sh` — 10/10 PASS against production

### QA lane — Q-S0 GREEN, § 6 audit, rollback runbook

- Q-S0 foundation gate signed off after F-S0.5 GREEN.
- Q-S0-AUDIT § 6 acceptance checkpoints vs JSX — caught 3 design doc spec bugs (Step01 PhoneMockup → QuoteRow, Step12 CohortBarChart → PeerLattice, Step15 RevealBurst → MatchBadge). All patched in design doc.
- `docs/runbooks/bundle-e-rollback.md` — OTA rollback procedure.

---

## Today's RED items (Ahmed device walkthrough — must fix tomorrow)

Ahmed ran the EAS preview build (update_id `019e6629-efd9-7d5d-b5a6-e83176380970`) and screenshotted the screens. Findings:

### Real bugs (regressions)

**B1 — HomeScreen TrendingNearYou render bug** *(task #56)*
- Rows show only `vs 1247 ↗` / `vs 893 ↗` — **product names `a` and `b` are MISSING**.
- Backend ships `{tag, a, b, count}` correctly per `dca8067`. Data is there.
- Fix at `src/components/HomeEditorialSections.tsx` TrendingNearYou block: render `[tag pill] {a} <vs> {b} {count ↗}` per `HomeScreen.jsx:625-645`.
- Legacy `it.query` split fallback only when `it.a`/`it.b` absent.

**B2 — HomeScreen ScanBody doesn't match JSX preview pattern** *(task #58)*
- Currently: giant camera icon + "Tap to scan products / 1 of 2".
- JSX `HomeScreen.jsx:222-265` requires ① ② numeral preview circles + dashed "Tap to snap product A/B" buttons + hairline + emerald "vs" pill (TwoInputShell preview pattern).
- Replace HomeScreen Scan placeholder with the JSX pattern.

### Deferred-to-S3-but-pulled-back-into-S1

**D1 — HistoryScreen HeroStats marquee + stat strip missing** *(task #59)*
- Current: empty state with camera icon + "Your first comparison is waiting" + green CTA.
- JSX `HistoryScreen.jsx:60-109` renders HeroStats marquee ALWAYS (even on empty state shows 0 decisions / 0 BHD).
- Add MarqueeCard horizontal scroll wired to `/profile/recent-decisions` + stat strip "N decisions this month · BHD shopped smarter" above the search field.

**D2 — ProfileScreen FlatSettings eyebrow grouping missing** *(task #60)*
- JSX `ProfileScreen.jsx:226-275` shows settings grouped by SettingsEyebrow headers (ACCOUNT / PRIVACY & NOTIFICATIONS / HELP / DANGER ZONE).
- Currently flat list. Compose FlatSettings + Delete account in destructive red.

**D3 — ResultsScreen TopMatchBadge winner-card emerald bg missing** *(task #61)*
- JSX `ResultsScreen.jsx:39-66` ProductCard winner has `background: accentLight` + `border: 2px solid accent`.
- Apply to winner-card composition.

### S2 work — not started (revealed by Ahmed walkthrough)

Ahmed's edit-preferences flow screenshots (NewOnboardingHost mode='edit' from Profile "Tune my priorities") showed:
- "How do you feel about brands?" (Step10BrandAttitude) — 1-column black-bordered card list
- "What's your usual budget?" (Step09Budget) — 5-tier list with thick left-border accent
- "What describes you?" (Step07Gender or similar) — 2-column capsule chip grid

**None match the JSX `OnboardingScreen.jsx` icon-circle OptionRow pattern.** Bundle D step components were NOT touched in S0. S2 work has to start. Per frontend's prep doc `bundle-e-s2-prep.md`, the per-Step deltas are mapped.

---

## Pending tasks for tomorrow

### Day-1 urgent (~3-4 hours of frontend work)

1. **Bug fixes** — task #56 (B1 TrendingNearYou) + task #58 (B2 ScanBody). Ship as path-restricted commits, then OTA.
2. **Deferral pullbacks** — task #59 (D1 HeroStats marquee) + task #60 (D2 FlatSettings) + task #61 (D3 winner-card bg). Ship + OTA.
3. **Ahmed re-verification** — walk through 4 affected screens on device. If GREEN, S1 truly closes.

### Day-1 next (~3-5 hours of frontend work)

4. **S2 KICKOFF** — task #62. 12 onboarding step components to compose per `bundle-e-s2-prep.md`. Sequencing: Step01 → 03 → 04 → 05 → 08 → 09 → 10 → 11 → 13 → 14 → 15 → 17. Step16 done. Step12 verify on device. Apply SlideTransition wrapper to every step. Backend stays idle.
5. **Ahmed onboarding fresh-install walkthrough** — install fresh OR `AsyncStorage.clear()` + walk all 17 steps. Switch locale to Arabic mid-flow to verify RTL slides.

### Day-1 cleanup (small)

6. **B4 cleanup** — task #49. Revert FE nonce-decode (commit `8d1444e`) since Supabase ignores nonce now. Remove `[B4-DIAG]` + `[B4-BE-DIAG]` verbose error strings (commits `bc15e0b` + `c19202b` + `9f6954c`). Restore slim "Google sign-in failed" generic error. ~15 min.
7. **Memory entries** — task #50. Add `memory/project_supabase_google_skip_nonce.md` documenting the Supabase dashboard toggle as the prod-required setting (Google iOS SDK auto-embeds nonce, can't be satisfied from FE). Also add the `agent_signoff_vs_device_walkthrough_again.md` lesson — Bundle E S1 self-sign-off claimed "8 screens composed" but Ahmed walkthrough surfaced 5 RED items + 2 bugs. Same failure mode as Bundle D Phase 3.

### Day-1 ship gate (after all above GREEN)

8. **S3 ship** — pre-deploy curl smoke pack PASS, `pip-audit` + `npm audit` clean, OTA `eas update --branch preview` final, Sentry watch T+15/60/120 min.
9. **TestFlight invite path** — once S1+S2 GREEN on device, TestFlight invite to ~150 testers can go out.

---

## Branch state at handoff

- Branch: `feature/bundle-e-visual-fidelity` (pushed to origin)
- HEAD: `499b2a3` (S2 prep doc) — 20 commits ahead of main
- Worktree: `C:\Users\SynAckITPC\Documents\AI\smartcompare-bundle-e-vf`
- Main HEAD: `2e1ceb7` (nav rename hotfix)
- Last EAS update: `019e6629-efd9-7d5d-b5a6-e83176380970` on `preview` channel (Bundle E S1 composition)

### Tests
- tsc 0
- Jest 1372 PASS / 17 RED across 8 suites (all pre-existing forward-ref scaffolds — zero new Bundle E regressions)
- expo-doctor 16/18 (2 pre-existing failures unrelated to Bundle E)

### Backend (Railway main)
- B3 fix shipped
- `/home/trending` reshape shipped
- `/home/smart-pick` extend shipped
- Endpoint shape contract test landed
- Production /health 200

### Supabase
- "Skip nonce checks" enabled for Google provider (B4 resolution — prod-required setting, NOT in code)

---

## Tomorrow's session — ready-to-paste prompt

Copy into the first message of the new Claude Code session:

```
Resuming Bundle E day-2. Read in order:

1. docs/plans/bundle-e-tomorrow-handoff.md — full state snapshot
2. docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md — design contract (patched per QA § 6 audit)
3. docs/plans/bundle-e-visual-fidelity.md — executable plan
4. docs/plans/bundle-e-s2-prep.md — S2 onboarding step deltas (per-Step composition notes)
5. CLAUDE.md — project conventions

Worktree: C:\Users\SynAckITPC\Documents\AI\smartcompare-bundle-e-vf on branch
feature/bundle-e-visual-fidelity. Branch HEAD: 499b2a3 (20 commits ahead of main).

Status going in:
- S0 SEALED, Q-S0 GREEN
- Backend lane DONE (8 deliverables)
- B4 RESOLVED (Supabase dashboard "Skip nonce checks" toggle, NOT code)
- S1: 8 screens composed but 5 RED items + 2 bugs from Ahmed device walkthrough
- S2: not started — Bundle D step components revealed during edit-preferences flow

Today's work:
1. RED #B1 + #B2 bug fixes (TrendingNearYou render + ScanBody preview pattern)
2. RED #D1 + #D2 + #D3 deferral pullbacks (HeroStats marquee + FlatSettings eyebrow + winner-card emerald bg)
3. Ahmed re-verifies on device → S1 closes
4. S2 KICKOFF — 12 onboarding step compositions per bundle-e-s2-prep.md sequencing
5. Ahmed onboarding fresh-install walkthrough → S2 closes
6. B4 cleanup (revert dead code) + memory entries
7. S3 ship gate + OTA + TestFlight invite path

Spawn 2-Opus team: frontend (composition lead) + qa (device walkthrough gate + § 6
checkpoints). Backend stays idle unless contract gap surfaces. Test lane chains
per-screen integration tests as frontend ships.

Discipline reminders from today:
- JSX wins on every spec ambiguity (Claude-Design handoff README)
- Agent self-sign-off ≠ device walkthrough (Bundle D Phase 3 + Bundle E S1 both
  taught this — DO NOT mark complete without Ahmed's screenshot match)
- Path-restricted commits: git commit -m "msg" -- <paths>
- Stage on creation in shared worktrees (git reset hazard from parallel lanes)
- Don't fabricate when backend ships null — render null-hide-surround
- No scary copy ever (Build Principle #4)
- No Lottie ever (hero SVGs are react-native-svg + Reanimated)

The single most important discipline: device walkthrough gate is the only true
S1/S2 sign-off. Agent self-verification (tsc 0 + Jest baseline + expo-doctor) is
necessary but NOT sufficient.
```

---

## Lessons logged for memory (file post-Bundle-E ship)

1. **`feedback_supabase_google_skip_nonce.md`** — Supabase enforces OIDC nonce parity by default. Google iOS SDK auto-embeds hashed nonce but doesn't expose raw value. Solution: Supabase Dashboard → Authentication → Providers → Google → "Skip nonce checks" toggle. Replay protection holds via RS256 signature + aud claim + short TTL. NOT in code — must re-enable if Supabase project migrates.

2. **`feedback_agent_signoff_vs_device_walkthrough_again.md`** — Bundle E S1: frontend self-signed-off "8 screens composed" but Ahmed walkthrough surfaced 5 RED items (3 intentional "S3 polish" deferrals that were actually in S1 scope per design doc § 6) + 2 actual bugs. Same failure mode as Bundle D Phase 3. The acceptance gate MUST be Ahmed's device walkthrough with side-by-side JSX/screenshot comparison. Self-sign-off allows "deferrals" that aren't approved.

3. **`feedback_dispatcher_cherry_pick_stash_hazard.md`** — when dispatcher cherry-picks docs across worktrees with uncommitted lane work present, lane work auto-stashes. Lanes need `git checkout stash@{$N} -- <paths>` to recover. Fix: dispatcher should cherry-pick only when worktree is clean OR with explicit lane-coordination.

4. **`feedback_git_show_over_worktree_read.md`** — for verifying a fix on another branch, use `git show <sha> -- <path>` as ground truth, NOT Read on possibly-stale worktree state. Diff +/- lines must be read distinctly (kept vs removed). Commit-subject and test-assertion that contradict each other = stop signal. (Captured from test lane's B4 nonce-test misread + correction.)

5. **`project_bundle_e_step_composition_throughput.md`** — Bundle E S1 throughput was ~2-3 screens/hour for a single Opus frontend agent on JSX-aligned composition. 12 S2 onboarding steps at similar throughput = 4-6 hours. Plan accordingly.

---

## Quick reference

- **Worktree:** `C:\Users\SynAckITPC\Documents\AI\smartcompare-bundle-e-vf`
- **Branch:** `feature/bundle-e-visual-fidelity` (push origin done)
- **Design doc:** `docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md`
- **Plan:** `docs/plans/bundle-e-visual-fidelity.md`
- **S2 prep:** `docs/plans/bundle-e-s2-prep.md`
- **Rollback runbook:** `docs/runbooks/bundle-e-rollback.md`
- **Screenshots:** `docs/claude-design-handoff/screenshots/*.png`
- **JSX refs:** `docs/claude-design-handoff/ui_kits/mobile/*.jsx`
- **Last OTA:** `019e6629-efd9-7d5d-b5a6-e83176380970` (preview, S1 composition)
- **Supabase:** "Skip nonce checks" enabled for Google provider (prod-required dashboard setting)
- **TestFlight blocker:** S1 RED items + S2 not started. Once both GREEN, invite path opens.
