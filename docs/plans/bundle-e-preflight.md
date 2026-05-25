# Bundle E Preflight — Visual Fidelity Pass to Match Claude-Design

**Filed:** 2026-05-25 (end of Bundle D Phase 3 device-leg session)
**Purpose:** Hand-off document so the Bundle E brainstorm starts in a *fresh* session with clean context. This session has carried ~6 hours of auth-debug + Path A hotfix artifacts; brainstorming benefits from a clean slate.

---

## Read me first (next session)

Before brainstorming, load these in order:

1. **This file** — sets the scope boundary + brainstorm prompt.
2. **`docs/plans/bundle-d-phase3-fidelity-triage.md`** — the honest B1-B6 + D1-D7 reassessment filed mid-session. D1-D7 is your fidelity-gap starting list.
3. **`docs/claude-design-handoff/CLAUDE_DESIGN_HANDOFF_README.md`** + **`docs/claude-design-handoff/SKILL.md`** — Claude-Design's intent + handoff format.
4. **`docs/claude-design-handoff/ui_kits/mobile/*.jsx`** — the 14 reference React snapshots (`HomeScreen.jsx`, `OnboardingScreen.jsx`, `HistoryScreen.jsx`, `ResultsScreen.jsx`, `AuthScreens.jsx`, etc.). Compare them screen-by-screen to the current `SmartCompareApp/src/screens/*.tsx`.
5. **`docs/claude-design-handoff/tokens.json`** + **`SmartCompareApp/src/theme/bundleD.ts`** — verify token parity, then move on (Bundle D already poured tokens.json into bundleD.ts).

Do not re-read this session's compaction summary — it is auth-debug + Path A heavy and will bias the brainstorm toward bug-fix mindset rather than visual-fidelity mindset.

---

## What this session shipped (and what it did NOT)

| Lane | What landed | Commit |
|------|-------------|--------|
| Path A R1 — auth restoration | LE E7 SPKI pin + Google `iosClientId` + Google nonce-drop + 17 onboarding step components wired + i18n interp args | `f6214c6` · `bb78b6b` |
| Path A R1 — diagnostics | `[SOCIAL_LOGIN_TRACE]` + Apple token RCA logging (kept until B4 Google diag complete) | `1fe71ed` · `510a8f2` |
| Path A R1 — hotfix sweep | Scan z-index + brand dedupe + priorities SUM-not-MAX + paywall trigger | `c0678d3` |
| Path A R2 — residuals | Scan chip UX (no auto-jump to camera) + priorities sum=100 (largest-remainder) + history detail unwrap (`response.data.comparison.full_response`) | `4aa9cff` |
| Path A R2 — verification | Sign-in: Apple ✅ Email ✅ Google ❌ (awaits Ahmed's `[GOOGLE-DIAG]`); history list ✅ no double brand; priorities labels ✅ human-readable; paywall ✅ surfaces | (manual device walkthrough) |

**What this session did NOT change:**

- Hero illustrations (PhoneMockup, CohortBarChart, ConcentricMotif, LoadingRings, RevealBurst) — D1.
- Theatrical loading (Step 14 cohort ticker, ring animation) — D2.
- RTL-mirrored step transitions — D3.
- History per-row mini-VS card layout — D4.
- "Tune my priorities" hero motifs — D5.
- Results winner-reveal RevealBurst — D6.
- Any composition-layer visual identity beyond the token + spacing layer.

The triage doc D1-D7 list is your accurate starting point.

---

## Confirmed pending items going into Bundle E

### Carry-over from Bundle D Path A (will be tied off BEFORE Bundle E kicks off, in the wrap-up of this session or a short follow-up)

| ID | Status | Action |
|----|--------|--------|
| B4 — Google sign-in still fails | Blocked on Ahmed | Need `[GOOGLE-DIAG]` Xcode console line + Railway `SOCIAL_LOGIN_TRACE provider=google token_segs=N` log to disambiguate iosClientId / Bundle-ID / token-shape failure mode |
| B5 — v1 history filter | Blocked on Ahmed | Need failing `comparison_id` (the 1 row that didn't backfill from R3 Migration 026); 3-LOC fix to add `.eq('schema_version', 2)` defensive check or surgical row repair |
| HomeScreen overlap | Partial | Path A R1 + R2 dropped scan z-index + chip auto-jump; Ahmed reports "still some issues" — needs visual diff against Claude-Design `HomeScreen.jsx` |

### Bundle E scope (visual fidelity)

D1-D7 from triage doc, plus whatever the next session's brainstorm uncovers from a fresh side-by-side Claude-Design vs current-code review.

Ahmed's framing: *"the new design from claude design is entirely different. […] we want the app design to be identical as the claude design, in terms of design, motion and flow."*

---

## Ahmed's screenshot list (this session)

Screenshots to load into the Bundle E brainstorm so the new session can SEE what Ahmed sees:

### Pre-Path-A-R2 (state Ahmed flagged)

These are the snapshots that triggered the triage doc + Path A R2 hotfix. Many are general fidelity concerns, not just bugs:

| # | Screen | Ahmed's complaint |
|---|--------|-------------------|
| 3-16 | Various | "wow the design is no where like the design system in cluade, it is embarassing, it is not the same […] many aspects have the old design like history and old comparisons show and they dont even work" |

### Post-Path-A-R2 (24-30, current device state)

| # | Screen | Current state | Bundle E concern |
|---|--------|---------------|------------------|
| 24 | HomeScreen, Link mode | Scan/Link/Type chips inline; "1 First link / vs / 2 Second link" stacked layout works | Layout works; whether it matches Claude-Design `HomeScreen.jsx` visual identity is open |
| 25 | HomeScreen, Type mode | Same as 24, with "Product A · e.g. iPhone 15" placeholder | Same — composition layer to compare |
| 26 | History list | Items render, no double brand, dates work | Per-row layout is text-only chevron — Claude-Design wants per-product mini-VS tiles (D4) |
| 27 | Profile | "What shapes your matches" — Price/Durability/Ease of use all 33% (post-Path-A-R2 will be 34/33/33=100) | Bars work; underlying "Tune my priorities" CTA opens the edit flow — D5 wants hero motifs there |
| 28 | Scan modal | Bare camera with "Snap to compare" — open via tap on chip currently, post-Path-A-R2 will require tap on in-card placeholder | Post-Path-A-R2 the chip→placeholder→camera flow works; the camera UI itself is bare-bones — Bundle E may want a shutter ring + framing guide |
| 29 | HomeScreen, Today's Tailored Pick | Smart-pick card renders with prices + "See full verdict" CTA + bottom nav (Qaren/History/Profile) | Card works; visual identity comparison against Claude-Design `HomeScreen.jsx` lines 438-651 needed |
| 30 | Paywall | "Upgrade to Premium" sheet surfaces, Free vs Premium side-by-side, "Coming Soon" CTA | Paywall surfaces — Path A B6 fix worked; visual layout vs Claude-Design Paywall reference TBD |

---

## Recommended Bundle E brainstorm prompt (for next session)

```
I'd like to brainstorm Bundle E — the visual fidelity pass to match Claude-Design.

Context to load:
1. docs/plans/bundle-e-preflight.md (this file)
2. docs/plans/bundle-d-phase3-fidelity-triage.md § D-series
3. docs/claude-design-handoff/CLAUDE_DESIGN_HANDOFF_README.md
4. docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx
5. docs/claude-design-handoff/ui_kits/mobile/OnboardingScreen.jsx
6. docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx
7. docs/claude-design-handoff/ui_kits/mobile/HistoryScreen.jsx
8. Screenshots in this conversation (Ahmed's device walkthrough)

Goal: produce a Bundle E plan that takes the app from "tokens-only fidelity"
to "tokens + composition + motion + hero illustrations fidelity" so the
device experience matches docs/claude-design-handoff/ui_kits/mobile/*.jsx
side-by-side.

Constraints:
- ~150 testers waiting on TestFlight invite — Bundle E ships before invite
- 4-Opus team (backend not needed unless we discover gaps), 3-5 days estimated
- No new backend endpoints unless a Claude-Design screen demands one we
  don't have
- Keep CLAUDE.md guardrails: no scary copy, no info banners, no "estimated"
  in UI, no backend internals in diagnostic reveals, Build Principle #4 (no
  shake/wobble/jitter for errors)

Sub-goal for the brainstorm:
1. Walk each screen Claude-Design provides vs current code, list gaps
2. Group gaps by effort tier (S/M/L)
3. Identify the 3-5 hero illustrations that need authoring (SVG + Reanimated, no Lottie per CLAUDE.md)
4. Identify motion + transition gaps
5. Output: docs/plans/bundle-e-visual-fidelity.md plan skeleton with
   <!-- OWNED BY: name --> section anchors for the 4-Opus team
```

---

## Process learning to apply in Bundle E

Bundle D Frontend signed off "11 screens integrated + R10/R16 ADDRESSED"
but the device walkthrough surfaced 6 concrete bugs + 7 fidelity gaps.
That's a process gap, not a code gap. Bundle E should not repeat it.

Two structural changes for Bundle E:

1. **Device-walkthrough acceptance gate.** Sign-off is contingent on Ahmed
   running the EAS preview build (not just `npx tsc --noEmit` + Jest +
   `expo-doctor`) and confirming each screen visually matches the
   Claude-Design reference. No agent self-signs-off on visual fidelity.

2. **Per-screen acceptance checklist.** Each Bundle E task lists the
   specific Claude-Design `.jsx` source file + 2-4 visual checkpoints
   that must hold post-merge. Frontend cannot mark complete until those
   checkpoints are mapped to screenshots Ahmed has approved.

This is *not* extra ceremony for ceremony's sake — it's the absent
acceptance contract that let Bundle D ship with 7 visual gaps.

---

## Open question for Ahmed (answer in next session)

1. **Bundle E team shape** — 4-Opus team like Bundle D, or 2 parallel Sonnet agents (lower cost, slower)?
2. **Bundle E size budget** — ship in one bundle (~3-5 days, larger PR) or split into E1 (hero illustrations) + E2 (composition + motion) + E3 (history/profile detail layouts)?
3. **Hero illustration authoring** — Claude-Design provides JSX references; do we have visual mockups (Figma export, PNG snapshots) to author against, or do we work purely from the .jsx render code?
4. **Apple Sign-In production switch** — currently sign-in flow works on EAS preview; for TestFlight external (>100 testers needs Beta App Review) we may need to confirm the Apple/Google provider config holds at scale.

---

**End of preflight.** Open Bundle E brainstorm in a fresh session. Do NOT carry Path A debugging state into it.
