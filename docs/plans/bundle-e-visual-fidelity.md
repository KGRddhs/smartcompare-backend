# Bundle E — Visual Fidelity Pass Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for task-by-task execution, OR `superpowers:subagent-driven-development` if dispatching fresh subagents per task. This bundle uses a parallel 4-Opus team coordinated via TeamCreate (see § Team Protocol) — each lane's owned section below is the slice that lane executes serially with TDD cycle.

**Goal:** Take Qaren from tokens-only fidelity (Bundle D) to tokens + composition + motion + hero illustrations fidelity matching `docs/claude-design-handoff/ui_kits/mobile/*.jsx` side-by-side, ready to ship before TestFlight invite to ~150 testers.

**Architecture:** One PR with 4 staged device-walkthrough gates (S0 foundation → S1 tab surfaces → S2 onboarding polish → S3 polish + ship). 4-Opus parallel team with mandatory cross-QA. Zero new backend endpoints — all editorial surfaces (`/home/{savings,smart-pick,trending}`, `/profile/{recent-decisions,monthly-stats,priorities-weighted}`) already live. B3 priorities-weighted normalize bug + B4 Google sign-in fix folded in.

**Tech Stack:** React Native + Expo (SmartCompareApp/) · react-native-svg · react-native-reanimated · FastAPI + Python 3.12 (app/) · Supabase Auth · EAS Build / Update · Sentry · Playwright (for reference rendering only).

**Design doc:** `docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md`
**Reference:** `docs/claude-design-handoff/ui_kits/mobile/*.jsx` (15 files) + `docs/claude-design-handoff/screenshots/*.png` (22 Playwright-rendered references)
**Branch:** `feature/bundle-e-visual-fidelity` (worktree at `../smartcompare-bundle-e-vf`)
**Ship vehicle:** One PR with staged device-walkthrough gates → OTA via `eas update --branch preview`
**Team:** 4-Opus (backend, frontend, test, qa) with mandatory cross-QA and rework cycle.

---

---

## Stage map

| Stage | What lands | Gate |
|---|---|---|
| **S0 — Foundation** | 5 hero SVG components, motion.ts extensions, shared primitives | Agent self-verification (tsc 0 + Jest baseline). No device walkthrough — no user-visible change yet. |
| **S1 — Tab surfaces** | Home, Results, History, Profile, Paywall, Scan, SignIn, SaveAdvisor wired against primitives. B3 + B4 land here. | Ahmed device walkthrough; screenshot-match per screen. |
| **S2 — Onboarding polish** | 18 onboarding step components + LoadingScreen variants A/B + theatrical Step 14 + RTL-mirrored slides | Ahmed device walkthrough; full onboarding flow on fresh install. |
| **S3 — Polish + ship** | EditProfile, Share/Demographics sheets, Splash polish, RED sweep, pre-deploy smoke. | Ahmed approves; OTA fires; Sentry watch T+~120 min. |

Each stage gates the next. Cross-QA pairings before disassembly per § Team Protocol.

---

## Team Protocol (Ahmed's rules — 2026-05-26)

1. All Opus. No Sonnet/Haiku.
2. Features 100% complete before disassembly. No grade-inflated "good enough."
3. Mandatory cross-QA pairings before disassembly:
   - **frontend** QA's **backend's** B3 + B4 work.
   - **backend** QA's **frontend's** primitive contracts.
   - **test** QA's both frontend and backend deltas.
   - **qa** lane does final sign-off across all lanes + runs the device walkthrough with Ahmed.
4. Subpar / missed → send back with specific delta. Owning lane reworks.
5. Idle members write R/G tests targeting 80%+ coverage of new components OR review another lane's pre-merge diffs. No idle waiting.
6. Path-restricted commits: `git commit -m "msg" -- <paths>` (paths AFTER `--`).
7. Worktree subagents have network sandbox limits — pre-fetch data, embed in prompts.

---

## Pre-flight (dispatcher before team spawn)

- [ ] Confirm `feature/bundle-e-visual-fidelity` worktree exists or create:
  ```bash
  git worktree add -b feature/bundle-e-visual-fidelity ../smartcompare-bundle-e main
  ```
- [ ] Confirm 22 screenshots exist at `docs/claude-design-handoff/screenshots/*.png`. If not, run:
  ```bash
  cd docs/claude-design-handoff && python -m http.server 8731 --bind 127.0.0.1 &
  node render-screenshots.js
  ```
- [ ] Stop the http.server background process after rendering.
- [ ] Ahmed posts `[GOOGLE-DIAG]` Xcode line + Railway `SOCIAL_LOGIN_TRACE` line for B4 diagnostic before backend lane starts S1.
- [ ] TeamCreate with `mode: "bypassPermissions"` (else sandbox blocks Bash).

---

<!-- OWNED BY: backend -->
## Backend lane

**Lead deliverables:** B3 priorities-weighted normalize fix (sum=100), B4 Google sign-in diagnostic + fix, endpoint cross-checks for editorial surfaces.

### S0 — No backend work in foundation stage.

Idle backend writes R/G tests for `home_routes.py` + `profile_routes.py` editorial endpoints (response-shape contract tests + rate-limit smoke).

### S1 — B3 + B4 + endpoint audit

#### B3.1 — Priorities-weighted normalize fix (verification) — **canonical TDD pattern example**

Path A R2 (commit `4aa9cff`) already shipped the sum=100 backend normalize. Verify it lives in `app/api/profile_routes.py` and produces correct response shape. Use this task as the TDD-cycle pattern reference for all other lane tasks.

**Files:**
- Modify (verify): `app/api/profile_routes.py` (the `_normalize_weights_to_100` helper)
- Create: `tests/test_profile_priorities_normalize.py`

**Step 1: Write the failing tests**

```python
# tests/test_profile_priorities_normalize.py
import pytest
from app.api.profile_routes import _normalize_weights_to_100

def test_equal_weights_sum_to_100_largest_remainder():
    result = _normalize_weights_to_100({"quality": 1.0, "price": 1.0, "durable": 1.0})
    assert sum(result.values()) == 100
    # largest-remainder: one bucket gets 34, the others 33
    counts = sorted(result.values(), reverse=True)
    assert counts == [34, 33, 33]

def test_skewed_weights_sum_to_100():
    result = _normalize_weights_to_100({"quality": 5.0, "price": 2.0, "durable": 1.0})
    assert sum(result.values()) == 100
    assert result["quality"] > result["price"] > result["durable"]

def test_single_nonzero_weight_pegs_to_100():
    result = _normalize_weights_to_100({"quality": 5.0, "price": 0.0, "durable": 0.0})
    assert result["quality"] == 100
    assert result["price"] == 0
    assert result["durable"] == 0

def test_all_zero_weights_falls_back_uniform():
    result = _normalize_weights_to_100({"quality": 0.0, "price": 0.0, "durable": 0.0})
    assert sum(result.values()) == 100  # divide-by-zero guard
```

**Step 2: Run the tests — they should fail if normalize is wrong**

```bash
cd /c/Users/SynAckITPC/Documents/ai/smartcompare-bundle-e-vf
python -m pytest tests/test_profile_priorities_normalize.py -v
```

Expected if normalize divides by MAX (old bug): `test_skewed_weights_sum_to_100` FAILS with `sum=200` or similar; `test_equal_weights_sum_to_100_largest_remainder` FAILS with `[100, 100, 100]`.
Expected if normalize already divides by SUM (Path A R2): all PASS.

**Step 3: If tests fail, fix `_normalize_weights_to_100`**

```python
# app/api/profile_routes.py — sketch
def _normalize_weights_to_100(weights: dict[str, float]) -> dict[str, int]:
    total = sum(weights.values())
    if total <= 0:
        # divide-by-zero guard: uniform split
        n = len(weights)
        base = 100 // n
        result = {k: base for k in weights}
        # distribute remainder to first n keys
        for k in list(weights.keys())[:100 - base * n]:
            result[k] += 1
        return result
    # largest-remainder method
    scaled = {k: (v / total) * 100 for k, v in weights.items()}
    floors = {k: int(v) for k, v in scaled.items()}
    remainder = 100 - sum(floors.values())
    remainders = sorted(scaled.items(), key=lambda kv: kv[1] - floors[kv[0]], reverse=True)
    for i in range(remainder):
        floors[remainders[i][0]] += 1
    return floors
```

**Step 4: Run tests — they should PASS**

```bash
python -m pytest tests/test_profile_priorities_normalize.py -v
```

Expected: 4 passed.

**Step 5: Commit** (path-restricted)

```bash
git add tests/test_profile_priorities_normalize.py app/api/profile_routes.py
git commit -m "fix(profile): priorities-weighted normalize uses largest-remainder sum=100

Replaces divide-by-MAX bug surfaced in Bundle D Phase 3 device walkthrough
(B3 in fidelity triage). Adds 4 regression tests covering equal-weight
largest-remainder, skewed weights, single non-zero, and divide-by-zero
guard.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
" -- tests/test_profile_priorities_normalize.py app/api/profile_routes.py
```

(Use `-- <paths>` AFTER the message to stay path-restricted per team protocol.)

**Pattern recap (use this shape for every TDD task in this plan):**
1. Write failing test
2. Run → verify FAIL
3. Implement minimal code
4. Run → verify PASS
5. Commit (path-restricted)

#### B4.1 — Google sign-in diagnostic capture

- [ ] Wait for Ahmed's `[GOOGLE-DIAG]` Xcode line.
- [ ] Query Railway logs via `mcp__railway__get_logs` with `log_type=deploy`, `search=SOCIAL_LOGIN_TRACE`, `since=1h`, `service_id=7ab6a780-e4df-4f72-97c2-b95992b96312`.
- [ ] Cross-reference against the diagnostic matrix in design doc § 3.5:

| Xcode | Railway | Diagnosis | Fix location |
|---|---|---|---|
| `token length: 0` / `parts: 0` | none | Native SDK threw | `app.json` plugin config OR Supabase iOS Client ID |
| `parts: 3` valid JWT | none | Network/cert pin | `certificatePinning.ts` Railway SPKI pin |
| `parts: 3` | `token_segs=3` + Supabase reject | aud claim mismatch | Supabase dashboard `iosClientId` |
| `parts: 3` | `token_segs=3` + "Nonces mismatch" | Nonce drop didn't deploy | `eas update` to re-push Path A R1+ |

#### B4.2 — Google sign-in fix

Based on B4.1 diagnosis, apply one of:

- Fix `app.json` Google plugin `iosClientId` to match Supabase Auth → Providers → Google → "iOS client ID" exactly (verify in browser).
- Confirm `com.qaren.app` Bundle ID is in Supabase Google provider iOS app list.
- If network: confirm `API_BASE_URL` resolves on device, confirm SPKI pin in `certificatePinning.ts` matches Railway's current LE E7 intermediate.
- If nonce regression: re-fire `eas update --branch preview` to push the Path A R1+ commits to phone.

After fix:
- [ ] Re-test on EAS preview build; confirm `[SOCIAL_LOGIN_TRACE provider=google token_segs=3]` lands in Railway AND user lands in Home tab.
- [ ] Add `tests/test_social_login_smoke.py` — mock Google id_token → POST `/auth/social-login` → 200 + valid session.

#### B4.3 — Endpoint shape verification

Frontend will consume these in S1. Re-verify response shapes match the JSX expectations:

- [ ] `GET /api/v1/home/smart-pick` returns `{ products: [{name, sub, price, winner, tone?}, ...], category, updated_at, verdict_short }`. Compare to `HomeScreen.jsx` `<SmartPickCard>` rendering.
- [ ] `GET /api/v1/home/savings` returns `{ amount_bhd, decisions_count, period: "month" }`. Compare to `<SavingsBanner>`.
- [ ] `GET /api/v1/home/trending` returns `{ items: [{tag, a, b, count}, ...], region }`. Compare to `<TrendingNearYou>`.
- [ ] `GET /api/v1/profile/recent-decisions` returns `{ items: [{a, b, ago, category}, ...] }`. Compare to `ProfileScreen.jsx` `<RecentDecisions>` + `HistoryScreen.jsx` `<HeroStats>` marquee.
- [ ] `GET /api/v1/profile/monthly-stats` returns `{ decisions, bhd_saved, bonus_credits }`. Compare to `<MonthStrip>`.
- [ ] `GET /api/v1/profile/priorities-weighted` returns 3 items sum=100 with human-readable `label_key` paths.

Any shape gap → coordinate with frontend on whether to adjust endpoint OR adapt frontend. Default: adjust endpoint to match JSX (the reference is the spec).

### S2 — No backend work in onboarding polish stage.

Idle backend writes integration tests for the cohort + scoring paths under load (`tests/test_cohort_match_under_load.py`).

### S3 — Polish + ship

- [ ] Run `pip-audit -r requirements.txt --strict` — must be clean.
- [ ] Push to `main` (after merge) → Railway auto-deploy.
- [ ] Watch Railway deploy logs for 60s; confirm `[startup]` line + `/health` 200.
- [ ] Sentry watch via `mcp__plugin_sentry_sentry__search_issues` query `project:qaren-rr level:error firstSeen:>2026-05-26T00:00:00` for ~120 min after OTA fires.

### Cross-QA owed (backend → frontend)

- [ ] Open frontend's foundation primitives (S0); verify TwoInputShell, DetailsAccordion, MarqueeCard contracts match what backend endpoints serve. If frontend's expectations diverge, raise to test lane.
- [ ] Open frontend's Auth fix; verify B4 retry logic doesn't loop or burn credits.

<!-- /OWNED BY: backend -->

---

<!-- OWNED BY: frontend -->
## Frontend lane

**Lead deliverables:** All 15 screens composed against Claude-Design references; 5 hero SVG illustrations; motion infrastructure; RTL mirror.

### S0 — Foundation (~1 day)

#### S0.1 — Hero SVG components

Location: `SmartCompareApp/src/components/hero/`. Each component takes `{ size?: number, animated?: boolean }` props. ZERO Lottie — pure `react-native-svg` + `react-native-reanimated`.

- [ ] `PhoneMockup.tsx` — iOS-shape SVG outline with Qaren wordmark inside + emerald accent dot. Spec: 180×280px default, 0.95→1.0 scale-in on mount (`withTiming(1, 320ms cubicBezier(0.32,0.72,0,1))`).
- [ ] `ConcentricMotif.tsx` — 3 emerald rings expanding outward from a center logo. Spec: 220×220px default. Animation: each ring runs `Animated.loop(withTiming({ scale: 0.8→2.5, opacity: 0.9→0 }, 2100ms), -1)` staggered 0ms / 700ms / 1400ms.
- [ ] `CohortBarChart.tsx` — 8 vertical bars (24px wide, heights 30–90px), one emerald-filled (the user's cohort), rest gray. Spec: caption text below "Capital · 25-34". Animation: each bar grows from 0 to full height staggered 80ms each, cubic-bezier(0.32,0.72,0,1).
- [ ] `LoadingRings.tsx` — Reuses ConcentricMotif + adds a tabular-nums counter chip below ticking 0→2074 over 2400ms (ease-out-cubic). Uses `requestAnimationFrame`.
- [ ] `RevealBurst.tsx` — 6–8 emerald particles emit from center on a parabolic fall, fade out over 1.2s. Center holds a scale-bounce badge (0→1.1→1.0 with `withSpring({ damping: 8, stiffness: 100 })`). `fireOnce` prop ensures it only animates on first mount per `key`.

**Acceptance for hero SVGs:**
- [ ] Each renders without warnings on iOS simulator (light + dark mode if applicable).
- [ ] Each respects `useReducedMotion()` — animations no-op when system reduces motion.
- [ ] Each has a Jest snapshot test in `__tests__/hero/`.

#### S0.2 — Motion infrastructure extensions

Extend `SmartCompareApp/src/theme/motion.ts`:

- [ ] `screenTransition: { duration: 320, easing: Easing.bezier(0.32, 0.72, 0, 1), mirrorRTL: true }`.
- [ ] `accordionChevron: { duration: 220, easing: Easing.ease }`.
- [ ] `ctaGlow: { duration: 240, easing: Easing.ease, shadowColor: '#10B981', shadowRadius: 12 }`.
- [ ] `modeSegment: { duration: 180, easing: Easing.bezier(0.32, 0.72, 0, 1) }`.
- [ ] `shimmer: { duration: 1400, easing: Easing.linear, repeat: -1 }`.
- [ ] `counterTick: { duration: 2400, easing: Easing.out(Easing.cubic) }`.
- [ ] `revealBurst: { particleEmit: 600, particleFall: 800, badgeSpring: { damping: 8, stiffness: 100 } }`.

#### S0.3 — Shared primitives

Location: `SmartCompareApp/src/components/primitives/`.

- [ ] `VsPair.tsx` — Two product blocks with center absolute-positioned emerald "VS" pill. Props: `left`, `right`, `winner: 'left' | 'right' | null`. Used in HistoryRowV2, SmartPickCard, MarqueeCard, MiniVsCard, PaywallScreen HeroVisual.
- [ ] `DetailsAccordion.tsx` — 3-section accordion shell with icon-circle + chevron rotate. Props: `sections: { key, label, sub, icon, body }[]`. Used in ResultsScreen.
- [ ] `OptionRow.tsx` — Icon-in-circle option row (Cal AI pattern). Props: `option`, `active`, `onToggle`, `style: 'icon-circle' | 'plain'`. Used across Step08 priorities + OnboardingExtras.
- [ ] `MarqueeCard.tsx` — Horizontal-scroll card for HistoryScreen HeroStats + ProfileScreen RecentDecisions.
- [ ] `ConfidencePill.tsx` — Dot + label pill. Props: `label`, `level: 'high' | 'medium' | 'low'`.
- [ ] `DimensionBar.tsx` — Two-color comparative bar (secondary + emerald, 2px gap).
- [ ] `ProductBlock.tsx` — Used by VsPair. Shows tile + name + sub, optional winner outline + "TOP MATCH" eyebrow.

#### S0.4 — RTL screen-transition wrapper

- [ ] `SmartCompareApp/src/components/SlideTransition.tsx` — wraps any onboarding step in `<Animated.View>` keyed on `step` index, animates `translateX` from `±width → 0`, mirrors based on `I18nManager.isRTL`.

#### S0.5 — Verification (all S0 work)

- [ ] `cd SmartCompareApp && npx tsc --noEmit` → exit 0.
- [ ] `cd SmartCompareApp && npx jest --testPathPattern="(hero|primitives|SlideTransition)"` → all PASS.
- [ ] `cd SmartCompareApp && npx expo-doctor` → clean.

### S1 — Tab surfaces (~1.5 days)

For EACH screen below, the agent:
1. Opens the matching reference `.jsx` AND the rendered screenshot.
2. Re-composes the current `.tsx` against the reference.
3. Adds the per-screen acceptance checkpoints (from design doc § 6) as JSDoc above the component.
4. Self-verifies on iOS simulator.
5. Adds 1–2 Jest snapshot tests.

| Screen | Reference | Current | Notes |
|---|---|---|---|
| Home | `HomeScreen.jsx` + `screenshots/home.png` | `screens/HomeScreen.tsx` | HeaderCounter pill, SmartPickCard VS-pair, QuickCategories 2x2, SavingsBanner dark-inverse w/ emerald arc, TrendingNearYou. Wire S0 `VsPair` + `MarqueeCard`. |
| Results | `ResultsScreen.jsx` + `screenshots/results.png` | `screens/ResultsScreen.tsx` | TopMatchBadge eyebrow, hero ProductCard pair w/ VsPair, DimensionBar, ConfidencePill, DetailsAccordion, RevealBurst on winner card mount (fireOnce keyed on `comparison_id`). |
| History | `HistoryScreen.jsx` + `screenshots/history.png` | `screens/HistoryScreen.tsx` | HeroStats marquee using `/profile/recent-decisions`. HistoryRowV2 using `VsPair`. Row tap → ResultsScreen w/ unwrap (B5 fix already at `4aa9cff`). |
| Profile | `ProfileScreen.jsx` + `screenshots/profile.png` | `screens/ProfileScreen.tsx` | Lens header, RecentDecisions marquee, PrioritiesInline (B3 fix: i18n keys), MonthStrip 3-tile, FlatSettings eyebrow-grouped. |
| Paywall | `PaywallScreen.jsx` + `screenshots/paywall.png` | `screens/PaywallScreen.tsx` | HeroVisual (3 staggered mini-vs pairs), SocialProof avatar row, PlanCardLarge x2 with "3 days free" eyebrow, trial timeline. |
| Scan | `ScanCameraScreen.jsx` + `screenshots/scan.png` | `screens/ScanCameraScreen.tsx` | Full-bleed black, Reticle 4-corner brackets, top bar glass-blur pills, SlotThumb pair, 76px shutter, sticky disabled CTA until both slots filled. |
| SignIn | `AuthScreens.jsx` (lines 86-150) + `screenshots/sign-in.png` | `screens/LoginScreen.tsx` | SocialRow at top, OrDivider, AuthField pair, Forgot password right-aligned, sticky black CTA. **B4 Google fix runs here**. |
| SaveAdvisor (s16) | `AuthScreens.jsx` (lines 152-226) + `screenshots/save-advisor.png` | `screens/onboarding/Step16Account.tsx` | Emerald-tint check hero, "Save your advisor" headline, SocialRow, AuthField, Terms/Privacy fine print, NO skip link. |

#### S1 i18n work (B3 frontend)

- [ ] Add 8 missing priority i18n keys to `SmartCompareApp/src/i18n/en.json` and `ar.json`:
  ```
  priorities.price → "Best price" / "أفضل سعر"
  priorities.quality → "Quality" / "الجودة"
  priorities.brand → "Trusted brand" / "علامة موثوقة"
  priorities.durable → "Built to last" / "متين"
  priorities.features → "Latest features" / "أحدث الميزات"
  priorities.easy / ease_of_use → "Easy to use" / "سهل الاستخدام"
  priorities.eco → "Eco-friendly" / "صديق للبيئة"
  priorities.health → "Health & safety" / "الصحة والسلامة"
  ```
- [ ] `ProfileEditorialSections.tsx::PrioritiesInline` reads `t(p.label_key, { defaultValue: humanize(p.key) })` so falls back to humanized snake_case if key still missing.

#### S1 verification

- [ ] `cd SmartCompareApp && npx tsc --noEmit` → 0.
- [ ] `npx jest` → existing baseline + new snapshots PASS, no NEW RED.
- [ ] `npx expo-doctor` → clean.
- [ ] Frontend builds + runs on iOS simulator without warnings.
- [ ] Frontend self-screenshots each of the 8 surfaces in simulator, compares against `docs/claude-design-handoff/screenshots/*.png`, posts to PR thread.
- [ ] **STAGE GATE**: Ahmed runs EAS preview build, walks all 8 screens, signs off each.

### S2 — Onboarding polish (~1.5 days)

For each of 17 step components + `OnboardingFlow.tsx`:

| Step | Reference | Current | Hero used | Notes |
|---|---|---|---|---|
| Step01Welcome | `OnboardingWelcomeScreen.jsx` | exists | PhoneMockup | Brand wordmark + accent + sticky Continue. |
| Step02Language | (existing) | exists | none | Visual polish only. |
| Step03ValueProp | (existing) | exists | ConcentricMotif | Replace inline spinner. |
| Step04Country | `OnboardingExtras.jsx` (s4) | exists | none | IconRow flag glyph pattern. |
| Step05Trust | `OnboardingExtras.jsx` (s5) | exists | ConcentricMotif | PrivacyRow w/ emerald-tint icon. |
| Step06Age | (existing) | exists | none | OptionRow pattern. |
| Step07Gender | (existing) | exists | none | OptionRow pattern. |
| Step08Priorities | `OnboardingScreen.jsx` (s8) | exists | none | Icon-in-circle OptionRow, max 3 picks, optional warm wash. |
| Step09Budget | (existing) | exists | none | OptionRow w/ 5-tier (top_tier added Migration 024). |
| Step10BrandAttitude | (existing) | exists | none | OptionRow. |
| Step11Attribution | (existing) | exists | none | OptionRow + "How did you hear about Qaren?" |
| Step12CohortProof | `OnboardingCohortScreen.jsx` | exists | CohortBarChart | Hero chart hardcoded for now; pulls from `/cohort-profile` later. |
| Step13Anticipation | `OnboardingExtras.jsx` (s13) | exists | none | StageChecklist + factoid card. |
| Step14Loading | `LoadingScreen.jsx` (onboarding mode) | exists | LoadingRings (concentric) | 3.2s min display floor. Theatrical loader. |
| Step15Reveal | `OnboardingReadyScreen.jsx` | exists | RevealBurst | "Your advisor is ready" headline + emerald confetti. |
| Step16Account | `AuthScreens.jsx` (SaveAdvisor) | exists | none (emerald check hero) | NO skip link. Covered in S1 — link from there. |
| Step17Notifications | `OnboardingExtras.jsx` (s17) | exists | none | Mock iOS push prompt anchor + Tag rows + "Maybe later" secondary. |

#### S2.x — LoadingScreen variants (used by Step14 + comparison loading)

- [ ] `screens/LoadingScreenVariants.tsx` — exports `ConcentricVariant` + `StreamingCardsVariant`.
- [ ] ConcentricVariant uses `<LoadingRings />` hero + StageChecklist + TipCard rotator.
- [ ] StreamingCardsVariant: two product-shape ghost cards with field-by-field reveal (photo → name → price → stars → top-match badge). Use shimmer overlay during pending fields.
- [ ] Mode `comparison` rotates between variants on mount (`useMemo(() => Math.random() < 0.5 ? 'concentric' : 'streaming')`).
- [ ] Mode `onboarding` always concentric (the dramatic moment).

#### S2.x — RTL slide transitions

- [ ] Wrap each step's content in `<SlideTransition step={index} direction={isRTL ? 'rtl' : 'ltr'}>...</SlideTransition>` (the wrapper from S0.4).
- [ ] Verify Arabic locale mirrors correctly via `I18nManager.forceRTL(true)` + RN reload.

#### S2 verification

- [ ] `npx tsc --noEmit` → 0.
- [ ] `npx jest --testPathPattern=onboarding` → new step tests PASS + baseline holds.
- [ ] **STAGE GATE**: Ahmed runs onboarding end-to-end on EAS preview (fresh install OR dev-reset), confirms each hero illustration matches reference + transitions feel RTL-mirrored when locale=ar.

### S3 — Polish + ship (~0.5 day)

- [ ] EditProfileScreen, ShareBottomSheet, DemographicsBottomSheet — wire against references `EditProfileScreen.jsx`, `ShareBottomSheet.jsx`, `DemographicsBottomSheet.jsx`.
- [ ] SplashScreen polish — emerald accent pulse on logo.
- [ ] Address ALL RED from S1 + S2 device walkthroughs.
- [ ] Final `tsc 0 + jest PASS + expo-doctor clean`.
- [ ] OTA: `cd SmartCompareApp && eas update --branch preview --message "Bundle E — visual fidelity pass"`.

### Cross-QA owed (frontend → backend)

- [ ] Open backend's B3 normalize fix; verify response shape matches `PrioritiesInline` expected `{label_key, key, weight}` per item.
- [ ] Open backend's B4 fix path; trace through `signInWithGoogle` → `/auth/social-login` → Supabase to confirm no silent regressions to Apple sign-in.

<!-- /OWNED BY: frontend -->

---

<!-- OWNED BY: test -->
## Test lane

**Lead deliverables:** R/G test suites for new components + endpoints (80%+ coverage), regression tests for B3 + B4, snapshot tests for hero SVGs, contract tests for screen → endpoint mappings.

### S0 — Foundation

#### S0.1 — Hero SVG snapshot tests

- [ ] `SmartCompareApp/__tests__/hero/PhoneMockup.test.tsx` — snapshot at default size + scale state.
- [ ] `__tests__/hero/ConcentricMotif.test.tsx` — snapshot at rest + animated state.
- [ ] `__tests__/hero/CohortBarChart.test.tsx` — snapshot with default + custom cohort highlight.
- [ ] `__tests__/hero/LoadingRings.test.tsx` — snapshot + counter format verification (`2,074` not `2074`).
- [ ] `__tests__/hero/RevealBurst.test.tsx` — snapshot + `fireOnce` invariant (re-render with same `key` → no re-emit).

#### S0.2 — Primitive contract tests

- [ ] `__tests__/primitives/VsPair.test.tsx` — winner outline applies correctly, emerald vs pill positioned center.
- [ ] `__tests__/primitives/DetailsAccordion.test.tsx` — clicking section toggles open, chevron rotates, only one open at a time.
- [ ] `__tests__/primitives/OptionRow.test.tsx` — `style='icon-circle'` shows 36px icon circle; `style='plain'` does not.
- [ ] `__tests__/primitives/MarqueeCard.test.tsx` — horizontal scroll behavior.
- [ ] `__tests__/primitives/ConfidencePill.test.tsx` — dot color matches `level`.
- [ ] `__tests__/primitives/DimensionBar.test.tsx` — two-color bar + 2px gap.
- [ ] `__tests__/primitives/SlideTransition.test.tsx` — `translateX` direction respects `I18nManager.isRTL`.

#### S0.3 — Motion token tests

- [ ] `__tests__/theme/motion.test.ts` — every motion token has required keys (`duration`, `easing`, plus stage-specific) AND no token uses banned shake/wobble/jitter primitives.

### S1 — Backend + frontend regression nets

#### S1.1 — B3 backend regression

- [ ] `tests/test_profile_priorities_normalize.py` (already specified in backend lane § B3.1). Test lane reviews + signs off.

#### S1.2 — B4 backend smoke

- [ ] `tests/test_social_login_smoke.py` — mock Google id_token POST → 200 + valid session. Cover: valid 3-part JWT, invalid token (no dots), missing id_token, valid token w/ Apple provider (regression).

#### S1.3 — Per-screen integration tests

For each S1 screen (Home, Results, History, Profile, Paywall, Scan, SignIn, SaveAdvisor):

- [ ] One Jest test that renders the screen with mocked endpoint responses (matching the JSX expected shape) AND verifies the per-screen acceptance checkpoints from design doc § 6.
  - Example: `Home.test.tsx` mocks `/home/smart-pick` + `/home/savings` + `/home/trending`, renders HomeScreen, asserts HeaderCounter shows `2/3 free · +1`, SmartPickCard has center vs pill + winner outline, etc.

#### S1.4 — Visual regression smoke (optional)

- [ ] Spawn the same Playwright render script the dispatcher used to capture screenshots — adapt to render the React Native web build via `expo export:web` + Playwright. Compare output to `docs/claude-design-handoff/screenshots/*.png` with pixel diff threshold ~5%. Surface any RED to frontend lane.

### S2 — Onboarding tests

- [ ] One test per Step component (Step01–Step17) verifying its hero illustration mounts + step transitions to the next step on Continue press.
- [ ] `OnboardingFlow.test.tsx` — full 17-step traversal with mocked analytics events.
- [ ] `LoadingScreen.test.tsx` — verify both ConcentricVariant + StreamingCardsVariant render without warnings; verify 3.2s min display floor on `onboarding` mode.

### S3 — Pre-deploy smoke pack

- [ ] Curl smoke pack:
  ```bash
  # Sentinel block (must 400 with content-safety code if ENABLE_CONTENT_SAFETY_TEST_SEEDS off)
  curl -s -o /dev/null -w "%{http_code}\n" "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24" -H "X-Device-Fingerprint: $(echo -n smoke | sha256sum | cut -c1-64)"

  # Editorial endpoints (with mock auth)
  for ep in home/savings home/smart-pick home/trending profile/recent-decisions profile/monthly-stats profile/priorities-weighted; do
    curl -s -o /dev/null -w "$ep %{http_code}\n" "https://web-production-58776.up.railway.app/api/v1/$ep" -H "Authorization: Bearer $TOKEN"
  done

  # SSE happy-path
  timeout 30 curl -N -s "https://web-production-58776.up.railway.app/api/v1/text/compare/stream?q=iPhone+15+vs+Galaxy+S24" | head -50
  ```
- [ ] All curl checks PASS before OTA fires.

### Cross-QA owed (test → frontend + backend)

- [ ] Open both lanes' deliverables; verify every new component / endpoint has a corresponding test in this lane's suite. Send back any uncovered surface.

<!-- /OWNED BY: test -->

---

<!-- OWNED BY: qa -->
## QA lane

**Lead deliverables:** Acceptance gate enforcement at each stage; device walkthrough orchestration; final sign-off; Sentry watch post-OTA.

### S0 — Foundation gate

- [ ] Pull latest from `feature/bundle-e-visual-fidelity`; run `cd SmartCompareApp && npx tsc --noEmit && npx jest && npx expo-doctor`. ALL must exit 0.
- [ ] Visually verify hero SVG components in iOS simulator (5 components × 2 states each = 10 spot checks).
- [ ] Verify motion tokens have no `shake`/`wobble`/`jitter`/`bounce` keys (Build Principle #4).
- [ ] Sign off S0 → S1 transition. Backend + frontend may start S1.

### S1 — Tab surface gate

- [ ] Before Ahmed walkthrough: spot-check each of the 8 surfaces in iOS simulator against the matching screenshot in `docs/claude-design-handoff/screenshots/`. Use the design doc § 6 per-screen checkpoints as the rubric.
- [ ] List any agent-self-sign-off claims that don't hold visually. Send back to frontend lane.
- [ ] Coordinate Ahmed's device walkthrough:
  - Ahmed installs latest EAS preview (`eas build --profile preview --platform ios` OR pulls OTA from `preview` channel).
  - Walk Home → Results → History → Profile → Paywall → Scan → SignIn (including Google) → SaveAdvisor (via onboarding fresh install).
  - For each screen, side-by-side compare against the matching `screenshots/*.png`.
  - Document RED items in this thread with screenshot of device vs reference.
- [ ] Block S2 start until ALL S1 RED resolved or explicitly deferred to S3.

### S2 — Onboarding polish gate

- [ ] Before Ahmed walkthrough: traverse the 17-step flow in simulator with `I18nManager.forceRTL(false)` then `forceRTL(true)`. Slide transitions must mirror under RTL.
- [ ] Ahmed device walkthrough:
  - Fresh install OR `await AsyncStorage.clear()` dev-reset.
  - Walk all 17 steps + final loading.
  - Confirm Step01 PhoneMockup hero renders.
  - Confirm Step12 CohortBarChart renders + bar animates.
  - Confirm Step14 theatrical loading: 3.2s min, ConcentricVariant, counter ticks.
  - Confirm Step15 RevealBurst fires.
  - Switch locale to Arabic mid-flow → confirm slides mirror.
- [ ] Block S3 start until ALL S2 RED resolved.

### S3 — Ship gate

- [ ] Confirm backend B3 + B4 fixes deployed to Railway (`mcp__railway__get_logs` shows startup).
- [ ] Confirm test lane's pre-deploy smoke pack ALL PASS (`/health` 200, editorial endpoints 200, SSE happy-path).
- [ ] Confirm `pip-audit --strict` clean + `npm audit --audit-level=high` clean.
- [ ] Ahmed final approve → frontend fires `eas update --branch preview --message "Bundle E"`.
- [ ] T+15min: pull `mcp__railway__get_logs` looking for new error patterns. Spot-check Sentry via `mcp__plugin_sentry_sentry__search_issues` with filter `firstSeen:>2026-05-26T<deploy-time>`.
- [ ] T+60min: same check.
- [ ] T+120min: same check + ask Ahmed for device feedback (any new bug surface?).
- [ ] If clean through T+120min → mark Bundle E SHIPPED + ready for TestFlight invite to ~150 testers.

### Cross-QA owed (qa → everyone)

- [ ] Final sign-off pass over all four lanes. No lane disassembles until qa has explicitly signed off their work via comment in this plan doc OR direct ack to dispatcher.
- [ ] Identify any "good enough" sign-offs that don't hold up; send back with specific delta + screenshot evidence.

### Idle work

- [ ] Triple-check the per-screen acceptance checkpoints in design doc § 6 against the JSX references. If any checkpoint is impossible OR contradicts the reference, flag to dispatcher and revise.
- [ ] Author the post-merge runbook at `docs/runbooks/bundle-e-rollback.md` covering OTA rollback procedure (revert commit + `eas update --republish <prior_update_id>`).

<!-- /OWNED BY: qa -->

---

## Disassembly checklist

The team can disassemble ONLY when ALL of:

- [ ] All four lanes have signed off cross-QA pairings (backend ↔ frontend, test ↔ both, qa final).
- [ ] All 15 screen acceptance checkpoints (design doc § 6) hold on Ahmed's device.
- [ ] `tsc 0` + `jest` baseline + `expo-doctor` clean.
- [ ] `pip-audit --strict` + `npm audit --audit-level=high` clean.
- [ ] Sentry T+120min watch shows no new error patterns.
- [ ] Bundle E PR merged to `main` + OTA fired + Ahmed confirms on device.

Until all six boxes ticked, the team stays online. No grade-inflated "ship and pray." If any item is RED, the owning lane reworks; idle lanes write tests OR review pre-merge diffs.

---

## Definition of done

Bundle E ships when every checkpoint in design doc § 9 is GREEN. TestFlight invite to ~150 testers fires after Bundle E lands.

---

## Reference

- Design doc: `docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md`
- Reference JSX: `docs/claude-design-handoff/ui_kits/mobile/*.jsx`
- Reference screenshots: `docs/claude-design-handoff/screenshots/*.png`
- Bundle D fidelity triage: `docs/plans/bundle-d-phase3-fidelity-triage.md`
- Preflight: `docs/plans/bundle-e-preflight.md`
- Team protocol: design doc § 5 + this doc § Team Protocol
- Per-screen acceptance: design doc § 6
