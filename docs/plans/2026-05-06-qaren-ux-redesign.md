# Qaren UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development when delegating to teammates.

**Goal:** Ship a Cal-AI-Lite onboarding + black-emerald hybrid visual identity + cohort-led referral flow across the Qaren mobile app, with implementation carried out by a 4-Opus agent team using mandatory cross-QA.

**Architecture:** 5 sequential phases. Phase 1 is foundational visual swap (low-risk, ships first). Phase 2 builds the new 17-screen onboarding behind a feature flag. Phase 3 redesigns Home + Results. Phase 4 adds bonus expiry + referral redesign. Phase 5 polishes + canary-rolls the feature flag.

**Tech Stack:** React Native + Expo SDK, Reanimated 3, react-native-svg, Geist font (EN) + Cairo (AR), FastAPI + Python 3.12 backend, Supabase Postgres, Upstash Redis, Expo Push, slowapi.

**Design spec:** [docs/plans/2026-05-06-qaren-ux-redesign-design.md](2026-05-06-qaren-ux-redesign-design.md) — refer to this for all visual specs, copy strings, animation timings, color tokens, and icon inventories.

**Build principles (locked):** No generic SaaS. No AI-art. No vibecoded animations. No scary copy. No exit ramps during loading. Cohort moat surfaced. Bilingual EN + AR with full RTL.

---

## Team Setup (run before Phase 1)

### Task 0: Spawn the 4-Opus team

**Files:** none (orchestrator only)

**Step 1: Confirm spec is committed**

Run: `git log --oneline -1 docs/plans/2026-05-06-qaren-ux-redesign-design.md`
Expected: shows commit `fe7aafb` or later.

**Step 2: Spawn team via TeamCreate**

```
TeamCreate({
  name: "qaren-ux-redesign",
  members: [
    {
      name: "frontend-visual",
      subagent_type: "general-purpose",
      model: "opus",
      mode: "bypassPermissions",
      prompt: "<<see Team Brief below>>"
    },
    {
      name: "frontend-flow",
      subagent_type: "general-purpose",
      model: "opus",
      mode: "bypassPermissions",
      prompt: "<<see Team Brief below>>"
    },
    {
      name: "backend",
      subagent_type: "general-purpose",
      model: "opus",
      mode: "bypassPermissions",
      prompt: "<<see Team Brief below>>"
    },
    {
      name: "test-qa",
      subagent_type: "general-purpose",
      model: "opus",
      mode: "bypassPermissions",
      prompt: "<<see Team Brief below>>"
    }
  ]
})
```

**Step 3: Hand each agent the Team Brief**

See `## Team Brief (paste verbatim to each agent)` section at the end of this document.

**Step 4: Verify TaskList visible to all agents**

Run: TaskList
Expected: every agent can see all tasks.

**Step 5: Commit team setup record**

```bash
git commit --allow-empty -m "chore: spawn qaren-ux-redesign 4-opus team for redesign implementation"
```

---

## Phase 1 — Visual Foundation

**Goal:** Existing app inherits new visual identity. No flow changes. Low risk.

**Owner:** frontend-visual (primary), test-qa (cross-QA)

### Task 1: Add Geist font via Expo Font

**Files:**
- Modify: `SmartCompareApp/app.json`
- Create: `SmartCompareApp/src/theme/fonts.ts`
- Modify: `SmartCompareApp/App.tsx` (font loading)

**Step 1: Use context7 to fetch current Expo Font docs**

Use `mcp__plugin_context7_context7__query-docs` with library `expo-font` for "loadAsync useFonts". Confirm API surface for SDK in use.

**Step 2: Confirm Geist license (SIL OFL allows commercial mobile redistribution)**

Run: `curl -s https://github.com/vercel/geist-font/raw/main/LICENSE.TXT | head -10`
Expected: SIL Open Font License v1.1 — confirm commercial redistribution allowed.

**Step 3: Download Geist font files**

Place `Geist-Regular.ttf`, `Geist-SemiBold.ttf`, `Geist-Bold.ttf` in `SmartCompareApp/assets/fonts/`.

**Step 4: Write fonts.ts**

```typescript
export const fontFamilies = {
  en: { regular: 'Geist-Regular', semibold: 'Geist-SemiBold', bold: 'Geist-Bold' },
  ar: { regular: 'Cairo-Regular', semibold: 'Cairo-SemiBold', bold: 'Cairo-Bold' },
} as const;

export const fontMap = {
  'Geist-Regular': require('../../assets/fonts/Geist-Regular.ttf'),
  'Geist-SemiBold': require('../../assets/fonts/Geist-SemiBold.ttf'),
  'Geist-Bold': require('../../assets/fonts/Geist-Bold.ttf'),
};
```

**Step 5: Wire useFonts in App.tsx**

Add `useFonts(fontMap)` at App root, gate splash screen on `fontsLoaded`.

**Step 6: Verify on device**

Run: `cd SmartCompareApp && npx expo start --clear`
Expected: splash → home renders with Geist (visually different from Inter, more compressed bold).

**Step 7: Commit**

```bash
git add SmartCompareApp/app.json SmartCompareApp/src/theme/fonts.ts SmartCompareApp/App.tsx SmartCompareApp/assets/fonts/Geist-*.ttf
git commit -m "feat(theme): add Geist font for EN, retain Cairo for AR" -- SmartCompareApp/app.json SmartCompareApp/src/theme/fonts.ts SmartCompareApp/App.tsx SmartCompareApp/assets/fonts/
```

---

### Task 2: Update theme tokens (colors, typography, motion)

**Files:**
- Modify: `SmartCompareApp/src/theme/index.ts`
- Create: `SmartCompareApp/src/theme/motion.ts`

**Step 1: Write failing snapshot test for theme**

Create `SmartCompareApp/__tests__/theme/tokens.test.ts`:

```typescript
import { colors, typography, radii, spacing } from '../../src/theme';

describe('theme tokens', () => {
  it('cta.primary is now black, not emerald', () => {
    expect(colors.cta.primary).toBe('#0A0A0B');
  });

  it('exposes accent.glow for winner reveal', () => {
    expect(colors.accent.glow).toMatch(/rgba\(16,\s*185,\s*129,\s*0?\.20?\)/);
  });

  it('typography.hero is 36pt Bold with -0.02em tracking', () => {
    expect(typography.hero.fontSize).toBe(36);
    expect(typography.hero.fontWeight).toBe('700');
    expect(typography.hero.letterSpacing).toBeCloseTo(-0.72); // 36 * -0.02
  });

  it('typography.eyebrow is 11pt SemiBold UPPERCASE +0.10em tracking', () => {
    expect(typography.eyebrow.textTransform).toBe('uppercase');
    expect(typography.eyebrow.letterSpacing).toBeCloseTo(1.1); // 11 * 0.10
  });

  it('radii.hero is 24', () => {
    expect(radii.hero).toBe(24);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd SmartCompareApp && npm test -- tokens.test.ts`
Expected: FAIL with "colors.cta is undefined" or similar.

**Step 3: Update theme/index.ts to add new tokens**

Add to `colors`:
```typescript
cta: {
  primary: '#0A0A0B',
  onPrimary: '#FFFFFF',
},
text: {
  primary: '#0A0A0B', // was #1A1A1E
  // ...rest unchanged
  onInverse: '#FFFFFF',
},
bg: {
  primary: '#FFFFFF',
  secondary: '#F8F8FA',
  inverse: '#0A0A0B',
},
accent: '#10B981',
accentDark: '#059669',
accentLight: '#ECFDF5',
accentGlow: 'rgba(16,185,129,0.20)',
```

Add to `typography`:
```typescript
hero: { fontSize: 36, fontWeight: '700', lineHeight: 36 * 1.2, letterSpacing: 36 * -0.02 },
display: { fontSize: 28, fontWeight: '700', lineHeight: 28 * 1.3, letterSpacing: 28 * -0.01 },
bodyEmphasis: { fontSize: 16, fontWeight: '600', lineHeight: 16 * 1.5 },
eyebrow: {
  fontSize: 11,
  fontWeight: '600',
  lineHeight: 11 * 1.4,
  letterSpacing: 11 * 0.10,
  textTransform: 'uppercase' as const,
},
```

Add `radii.hero = 24`.

**Step 4: Create motion.ts**

```typescript
import { Easing } from 'react-native-reanimated';

export const motion = {
  screenTransition: { duration: 320, easing: Easing.bezier(0.32, 0.72, 0, 1) },
  springConfig: {
    chip: { damping: 14, stiffness: 200 }, // chip bounce
    progress: { damping: 18, stiffness: 120 }, // progress bar
    tab: { damping: 12, stiffness: 180 }, // tab icon
  },
  variableEasing: {
    fast: Easing.bezier(0, 0.55, 0.45, 1),
    slow: Easing.bezier(0.4, 0, 0.6, 1),
    snap: Easing.bezier(0.55, 0, 0.1, 1),
  },
  haptic: {
    chip: 'light' as const,
    stage: 'light' as const,
    winner: 'medium' as const,
    error: 'warning' as const, // never used in success paths
  },
} as const;
```

**Step 5: Run tests**

Run: `cd SmartCompareApp && npm test -- tokens.test.ts && npx tsc --noEmit`
Expected: PASS + zero TypeScript errors.

**Step 6: Commit**

```bash
git commit -m "feat(theme): black/emerald hybrid tokens + Geist typography + motion config" -- SmartCompareApp/src/theme/ SmartCompareApp/__tests__/theme/
```

---

### Task 3: Update Button component to use new black CTA

**Files:**
- Modify: `SmartCompareApp/src/components/Button.tsx`
- Modify: `SmartCompareApp/__tests__/components/Button.test.tsx` (or create)

**Step 1: Write failing test for primary variant**

```typescript
import { render } from '@testing-library/react-native';
import { Button } from '../../src/components/Button';

describe('Button primary variant', () => {
  it('uses black background by default', () => {
    const { getByRole } = render(<Button title="Continue" onPress={() => {}} />);
    const btn = getByRole('button');
    expect(btn).toHaveStyle({ backgroundColor: '#0A0A0B' });
  });

  it('uses emerald only for variant="signature"', () => {
    const { getByRole } = render(
      <Button title="Reveal" variant="signature" onPress={() => {}} />
    );
    const btn = getByRole('button');
    expect(btn).toHaveStyle({ backgroundColor: '#10B981' });
  });
});
```

**Step 2: Run test, verify fail**

Run: `cd SmartCompareApp && npm test -- Button.test.tsx`
Expected: FAIL — current Button uses emerald background.

**Step 3: Update Button.tsx**

Add `variant?: 'primary' | 'signature' | 'secondary'` prop. Default `primary` → black bg + white text. `signature` → emerald (used ONLY on invitee-landing "Reveal my verdict" CTA — see design doc Section 4e). `secondary` → white bg + black border + black text.

**Step 4: Run test, verify pass**

Run: `cd SmartCompareApp && npm test -- Button.test.tsx`
Expected: PASS.

**Step 5: Run full type check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors.

**Step 6: Commit**

```bash
git commit -m "feat(button): black primary CTA, emerald reserved for signature variant" -- SmartCompareApp/src/components/Button.tsx SmartCompareApp/__tests__/components/Button.test.tsx
```

---

### Task 4: Build src/icons/ infrastructure + QaranIcon brand mark

**Files:**
- Create: `SmartCompareApp/src/icons/index.ts`
- Create: `SmartCompareApp/src/icons/QaranIcon.tsx`
- Create: `SmartCompareApp/__tests__/icons/QaranIcon.test.tsx`

**Step 1: Use context7 for react-native-svg API**

Query: `mcp__plugin_context7_context7__query-docs` for `react-native-svg` "Path Svg G".

**Step 2: Write failing test**

```typescript
import { render } from '@testing-library/react-native';
import { QaranIcon } from '../../src/icons/QaranIcon';

describe('QaranIcon', () => {
  it('renders with default 24px size', () => {
    const { UNSAFE_getByType } = render(<QaranIcon />);
    const svg = UNSAFE_getByType(require('react-native-svg').Svg);
    expect(svg.props.width).toBe(24);
    expect(svg.props.height).toBe(24);
  });

  it('accepts size prop and color prop', () => {
    const { UNSAFE_getByType } = render(<QaranIcon size={48} color="#10B981" />);
    const svg = UNSAFE_getByType(require('react-native-svg').Svg);
    expect(svg.props.width).toBe(48);
  });
});
```

**Step 3: Build QaranIcon component**

```typescript
import React from 'react';
import Svg, { Circle, Line } from 'react-native-svg';

interface Props { size?: number; color?: string; }

export const QaranIcon: React.FC<Props> = ({ size = 24, color = '#0A0A0B' }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    {/* Q-as-magnifier: circle ring + diagonal handle */}
    <Circle cx="10" cy="10" r="6" stroke={color} strokeWidth="2.5" fill="none" />
    <Line x1="14" y1="14" x2="20" y2="20" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    {/* Q-tail dot at handle end (matches logo) */}
    <Circle cx="20" cy="20" r="1.5" fill={color} />
  </Svg>
);
```

**Step 4: Create index.ts**

```typescript
export { QaranIcon } from './QaranIcon';

// Helper: flips icons that bear direction (arrows, share) when in RTL
export const flipForRTL = (isRTL: boolean): { transform: any[] } =>
  isRTL ? { transform: [{ scaleX: -1 }] } : { transform: [] };
```

**Step 5: Run test, verify pass**

Run: `cd SmartCompareApp && npm test -- QaranIcon.test.tsx && npx tsc --noEmit`
Expected: PASS + 0 type errors.

**Step 6: Commit**

```bash
git commit -m "feat(icons): src/icons/ infra + QaranIcon brand mark" -- SmartCompareApp/src/icons/ SmartCompareApp/__tests__/icons/
```

---

### Task 5: Add 6 utility custom icons (back, close, search, bell, settings, plus)

**Files:**
- Create: `SmartCompareApp/src/icons/UtilityIcons.tsx`
- Create: `SmartCompareApp/__tests__/icons/UtilityIcons.test.tsx`
- Modify: `SmartCompareApp/src/icons/index.ts` (re-export)

**Step 1: Write tests for all 6 icons** — render check + size prop accepted.

**Step 2: Build each as filled-mono SVG path** — design spec contract: 24×24 grid, filled, geometric. See design doc Section 5a for spec.

**Step 3: Re-export from index.ts**

**Step 4: Run tests + tsc**

**Step 5: Commit:** `feat(icons): 6 utility icons (back, close, search, bell, settings, plus)`

---

### Task 6: Snapshot test existing screens with new theme (regression catch)

**Files:**
- Create: `SmartCompareApp/__tests__/snapshots/visual-foundation.test.tsx`

**Step 1: Snapshot all 12 existing screens in EN + AR** to catch any unintended visual regression.

**Step 2: Run snapshot tests, confirm clean**

Run: `cd SmartCompareApp && npm test -- visual-foundation`
Expected: snapshots created, all pass on second run.

**Step 3: Manual visual check** — open each screen in dev build, confirm Geist renders, black CTAs everywhere, RTL still works.

**Step 4: Commit:** `test(visual): snapshot existing screens after Phase 1 visual swap`

---

### Task 7: Phase 1 cross-QA + commit gate

**Owner:** test-qa agent

**Step 1: Use superpowers:code-reviewer skill on Phase 1 commits**

Run: `git log --oneline main..HEAD` to see all Phase 1 commits.

For each commit, invoke code review per the skill's checklist (correctness, security, perf, style, tests).

**Step 2: Verify exit criteria**

- [ ] `npx tsc --noEmit` exits 0
- [ ] All tests pass
- [ ] Coverage ≥80% on new files
- [ ] Geist renders correctly on device (visual confirmation)
- [ ] All buttons in app use black bg (no orphaned emerald CTAs)
- [ ] No "scary" copy introduced
- [ ] RTL still works (open app in Arabic, navigate every screen)

**Step 3: If any criterion fails — send back via TaskUpdate to original author with specific findings.**

**Step 4: When all green: open Phase 2 by re-claiming TaskList.**

---

## Phase 2 — Onboarding Overhaul

**Goal:** Build the 17-screen Cal-AI-Lite onboarding flow behind feature flag `ENABLE_NEW_ONBOARDING`.

**Owner:** frontend-flow (primary), backend (attribution endpoint), frontend-visual (illustrations), test-qa (cross-QA + tests)

### Task 8: Backend — attribution endpoint

**Owner:** backend agent

**Files:**
- Modify: `app/api/auth_routes.py`
- Create: `tests/test_attribution_endpoint.py`
- Modify: `app/services/auth_service.py` (helper)

**Step 1: Write failing test**

```python
def test_attribution_accepts_valid_source(client, auth_token):
    resp = client.post(
        "/api/v1/auth/attribution",
        json={"source": "instagram"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

def test_attribution_rejects_invalid_source(client, auth_token):
    resp = client.post(
        "/api/v1/auth/attribution",
        json={"source": "myspace"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422

VALID_SOURCES = {"friend", "instagram", "tiktok", "app_store", "google", "other"}
```

**Step 2: Run, verify fail**

`python -m pytest tests/test_attribution_endpoint.py -v` → FAIL (endpoint doesn't exist).

**Step 3: Implement endpoint with Pydantic enum + slowapi 30/min limit + auth required + writes to `users.attribution_source`**

**Step 4: Apply migration if column doesn't exist** — use `mcp__plugin_supabase_supabase__apply_migration` with name `019_users_attribution_source`:

```sql
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS attribution_source TEXT;
```

**Step 5: Run test, verify pass**

**Step 6: Commit:** `feat(auth): POST /attribution endpoint + users.attribution_source column`

---

### Task 9: Frontend — OnboardingFlow orchestrator skeleton

**Owner:** frontend-flow agent

**Files:**
- Create: `SmartCompareApp/src/screens/onboarding/OnboardingFlow.tsx`
- Create: `SmartCompareApp/src/screens/onboarding/types.ts`
- Create: `SmartCompareApp/__tests__/screens/onboarding/OnboardingFlow.test.tsx`

**Step 1: Write failing test for step navigation**

Test: starts at step 1, advances on `handleNext`, decrements on back, blocks Next when validation fails.

**Step 2: Build OnboardingFlow** — owns `step` state, progress bar component, slide-transition wrapper, back/next handlers, RTL-aware direction.

**Step 3: Define `OnboardingData` type** with all 17 step keys.

**Step 4: Run tests, verify pass.**

**Step 5: Commit:** `feat(onboarding): OnboardingFlow orchestrator + types`

---

### Task 10: Build CounterTicker component

**Files:**
- Create: `SmartCompareApp/src/components/CounterTicker.tsx`
- Create: `SmartCompareApp/__tests__/components/CounterTicker.test.tsx`

**Step 1: Write test**

```typescript
it('animates 0 → target over duration', async () => {
  const { findByText } = render(<CounterTicker target={388} duration={800} />);
  // Initially 0
  await findByText('0');
  // After duration, target reached
  jest.advanceTimersByTime(800);
  expect(await findByText('388')).toBeTruthy();
});
```

**Step 2: Build using `useSharedValue` + `useAnimatedReaction` from Reanimated 3** — interpolates 0 → target using ease-out, renders rounded integer.

**Step 3: Run, pass, commit:** `feat(component): CounterTicker — animated number ticker`

---

### Task 11: Build StageChecklist component

**Files:**
- Create: `SmartCompareApp/src/components/StageChecklist.tsx`
- Create: `SmartCompareApp/__tests__/components/StageChecklist.test.tsx`

**Step 1: Write test** — accepts `stages: Stage[]` (5 items), each with `label`, `status: 'pending' | 'active' | 'done'`, fires haptic on done transition.

**Step 2: Build** — vertical list, ✓ for done (emerald), ⟳ spinner for active (emerald), ○ for pending (gray). Each row haptic-light on transition to done.

**Step 3: Test, pass, commit:** `feat(component): StageChecklist — multi-stage progress with haptics`

---

### Task 12: Build ProgressBar variableEasing variant

**Files:**
- Modify: `SmartCompareApp/src/components/ProgressBar.tsx`
- Modify: `SmartCompareApp/__tests__/components/ProgressBar.test.tsx`

**Step 1: Add `variableEasing?: boolean` prop**

**Step 2: When true, segment animation:** 0→25% fast (0.6s), 25→60% slow (matches API time), 60→90% fast, 90→100% snap (0.4s).

**Step 3: Test + commit:** `feat(progress): variableEasing prop for theatrical loading`

---

### Task 13: Onboarding screens 1-3 (Welcome, Language, Value Prop)

**Owner:** frontend-flow

**Files:**
- Create: `SmartCompareApp/src/screens/onboarding/Step01Welcome.tsx`
- Create: `SmartCompareApp/src/screens/onboarding/Step02Language.tsx`
- Create: `SmartCompareApp/src/screens/onboarding/Step03ValueProp.tsx`
- Create: tests for each

**Step 1: Write tests** — each screen renders title, subhead, CTA, fires `onNext` callback with valid data.

**Step 2: Build each per design doc Section 2 spec.** Step 3 references hero illustration #1 (placeholder for now — comes in Task 18).

**Step 3: i18n keys** — add 12 keys to `src/i18n/en.json` + `src/i18n/ar.json`.

**Step 4: Test, pass, commit:** `feat(onboarding): screens 1-3 (welcome, language, value prop)`

---

### Task 14: Onboarding screens 4-7 (Country/Governorate, Trust, Age, Gender)

**Files:** create 4 step components + 4 test files.

**Step 1: Write tests** for each.

**Step 2: Build per design doc.**
- Step 4: country picker with conditional governorate sub-question
- Step 5: trust bridge (typography + small filled lock with 5° rotation animation on mount)
- Step 6: age group (5 cards + "prefer not to say")
- Step 7: gender (3 cards including prefer not to say)

**Step 3: i18n keys (~18 keys)**

**Step 4: Wire to `PUT /api/v1/auth/demographics` on completion** (backend already exists per CLAUDE.md).

**Step 5: Test, pass, commit:** `feat(onboarding): screens 4-7 (cohort demographics)`

---

### Task 15: Onboarding screens 8-11 (Priorities, Budget, Brand, Attribution)

**Step 1: Tests for each.**

**Step 2: Build:**
- Step 8: priority chip select (8 chips, max 3)
- Step 9: budget tier (3 cards with BHD ranges)
- Step 10: brand attitude (3 cards)
- Step 11: attribution (6 stacked cards)

**Step 3: Wire `PUT /api/v1/auth/preferences` for steps 8-10. Wire `POST /api/v1/auth/attribution` for step 11.**

**Step 4: i18n (~30 keys).**

**Step 5: Commit:** `feat(onboarding): screens 8-11 (shopping prefs + attribution)`

---

### Task 16: Hero illustration #2 (CohortBarChart)

**Owner:** frontend-visual

**Files:**
- Create: `SmartCompareApp/src/components/illustrations/CohortBarChart.tsx`
- Create: test file

**Step 1: Hand-code as SVG + Reanimated.** Per design doc Section 5b, illustration #2:
- 4 vertical bars at varying heights, emerald accent on user's matched bar
- Below: 20×20 dot grid (388 dots), 12 emerald-highlighted
- Animation: bars rise stagger 80ms, dots fade left-to-right, "0 → 388" counter using CounterTicker

**Step 2: Test renders + animation completes within 1.2s.**

**Step 3: Commit:** `feat(illust): CohortBarChart — hand-coded SVG hero illustration #2`

---

### Task 17: Hero illustrations #3, #4, #5 (Concentric, Loading rings, Reveal burst)

**Files:**
- Create: `SmartCompareApp/src/components/illustrations/ConcentricMotif.tsx`
- Create: `SmartCompareApp/src/components/illustrations/LoadingRings.tsx`
- Create: `SmartCompareApp/src/components/illustrations/RevealBurst.tsx`
- Create: 3 test files

**Step 1: Hand-code each per design doc Section 5b.** Pure SVG + Reanimated. No Lottie.

**Step 2: Each test:** mounts cleanly, animation runs, no console errors.

**Step 3: Commit:** `feat(illust): hand-coded SVG hero illustrations #3, #4, #5`

---

### Task 18: Hero illustration #1 (PhoneMockup) — designer Figma export

**Files:**
- Create: `SmartCompareApp/src/components/illustrations/PhoneMockup.tsx`
- Create: test
- Place: `SmartCompareApp/assets/illustrations/phone-mockup.svg`

**Step 1: Designer hands off Figma → SVG export.** Wrap as React component.

**Step 2: Animation: phone slides up 16px + fades on mount, glow ring pulses.**

**Step 3: Test + commit:** `feat(illust): PhoneMockup hero illustration #1 (designer SVG)`

---

### Task 19: Onboarding screen 12 (cohort social proof)

**Files:** Step12CohortProof.tsx + test.

**Step 1: Test** — renders CohortBarChart + 3 bullet stats animating one-by-one.

**Step 2: Build per design doc Section 2.**

**Step 3: Commit:** `feat(onboarding): screen 12 — cohort social proof reveal`

---

### Task 20: Onboarding screen 13 (anticipation)

**Step 1: Test** — renders ConcentricMotif + "Time to build your shopping advisor" + "Build my advisor" CTA.

**Step 2: Build.**

**Step 3: Commit.**

---

### Task 21: Onboarding screen 14 (theatrical loading — centerpiece)

**Files:** Step14Loading.tsx + test.

**Step 1: Test** — runs for **3.2 seconds minimum** even if API faster, cycles 4 stage copy strings, ticks counter 0 → 47.

**Step 2: Build:**
- LoadingRings illustration #4
- Stage copy cycler (every 800ms)
- Progress bar 0 → 100% over 3.2s with variableEasing
- CounterTicker for "0 → 47 cohort peers"
- On completion, fires `onComplete()` callback that advances to step 15

**Step 3: Test, pass, commit:** `feat(onboarding): screen 14 — theatrical custom-plan loading (3.2s minimum)`

---

### Task 22: Onboarding screen 15 (reveal)

**Step 1: Test** — RevealBurst illustration plays, 4 stat cards stagger-fade in (80ms), CTA "Compare your first product" fires.

**Step 2: Build per design doc.**

**Step 3: Commit.**

---

### Task 23: Onboarding screens 16, 17 (Save your advisor, Notifications)

**Files:** Step16Account.tsx, Step17Notifications.tsx + tests.

**Step 1: Tests:**
- Step 16: Apple/Google/Email buttons present, NO skip link, signup blocks navigation forward without success
- Step 17: notification permission request + Allow/Not now CTAs

**Step 2: Build:**
- Step 16: integrate existing `authService` social login. Per design — drop "skip" link entirely.
- Step 17: use `expo-notifications` (already present). Mock notification preview as visual element.

**Step 3: Use context7** to confirm current `expo-notifications` API for permission request.

**Step 4: Commit.**

---

### Task 24: Wire OnboardingFlow into App.tsx with feature flag

**Files:**
- Modify: `SmartCompareApp/App.tsx`
- Modify: `app/main.py` (env flag)

**Step 1: Add `ENABLE_NEW_ONBOARDING` feature flag** read from environment + remote config (whatever exists).

**Step 2: Conditional routing:** if flag on, new 17-screen flow; if off, existing 6-step flow stays as fallback.

**Step 3: Test both paths render correctly.**

**Step 4: Commit:** `feat(app): wire new OnboardingFlow behind ENABLE_NEW_ONBOARDING flag`

---

### Task 25: Phase 2 cross-QA gate

**Owner:** test-qa agent

**Step 1: Code review every Phase 2 commit** using superpowers:code-reviewer.

**Step 2: Run completion-rate instrumentation check** — confirm analytics events fire on each step completion (we measure drop-off heatmap per screen).

**Step 3: RTL audit** — switch to AR, complete entire 17-step flow, fix any mirror bugs.

**Step 4: Coverage check** — `npm run test:coverage` should show ≥80% on `src/screens/onboarding/`, `src/components/CounterTicker.tsx`, `src/components/StageChecklist.tsx`, `src/components/illustrations/*`.

**Step 5: Copy audit** — sweep i18n new keys for any "scary" language. Fix per design doc Section 4g table.

**Step 6: Send back any failing tasks via TaskUpdate.** Iterate until all green.

---

## Phase 3 — Home + Results Redesign

**Goal:** Main daily-use surfaces match the new identity. Camera-first card on Home; winner-celebration post-reveal on Results.

**Owner:** frontend-flow (primary), test-qa (cross-QA), frontend-visual (icon migrations)

### Task 26: Home — camera-first card layout

**Files:**
- Modify: `SmartCompareApp/src/screens/HomeScreen.tsx`
- Modify: existing tests

**Step 1: Tests:**
- Camera viewfinder is in a 40% screen-height card with 16px corners
- Mode chips below viewfinder (3 equal: Scan, Link, Type)
- Active dot under selected chip
- Tap "Link" → viewfinder card cross-fades to URL input over 240ms

**Step 2: Refactor HomeScreen.tsx** — viewfinder in card not background. Mode-tap morphs card content (240ms cross-fade).

**Step 3: All Lucide → custom icon migrations** for Home (Q-mark in header, mode icons).

**Step 4: Commit:** `feat(home): camera-first card layout + 3-mode equal chips`

---

### Task 27: StreamingProductCard component

**Files:**
- Create: `SmartCompareApp/src/components/StreamingProductCard.tsx`
- Create: test

**Step 1: Test** — accepts SSE stage events, fills fields progressively (title → specs → prices with counter ticks → rating fade-in).

**Step 2: Build per design doc Section 3.**

**Step 3: Commit:** `feat(component): StreamingProductCard with progressive fill`

---

### Task 28: Results — stage checklist + ghost cards loading

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

**Step 1: Tests:**
- Initial render: progress bar at 0%, 5 stages all `pending`
- On `onSpecs`: stage 1 → done, stage 2 → active, ghost card fills with title + specs
- Min display floor 1.2s (even on cache hit, loading shows minimum 1.2s)
- After `onVerdict`: reveal sequence fires (stage list slides up, cards slide together, glow ring expands)

**Step 2: Replace existing skeleton with StageChecklist + StreamingProductCard.** Wire to existing SSE callbacks.

**Step 3: Implement min-display floor** — use `setTimeout(advance, max(0, 1200 - elapsed))`.

**Step 4: Implement variable-easing progress bar** with stage-correlated segments.

**Step 5: Tips carousel after 8s** — render `LoadingTipsCarousel` (next task).

**Step 6: Commit:** `feat(results): stage checklist + ghost cards + min-display floor`

---

### Task 29: LoadingTipsCarousel component

**Files:**
- Create: `SmartCompareApp/src/components/LoadingTipsCarousel.tsx`
- Create: test

**Step 1: Test** — rotates through 5 tips every 4s. Mounts visible after 8s wait. Reads i18n locale.

**Step 2: Build with 5 tips per design doc Section 3 "Tips during deep waits" table.**

**Step 3: i18n keys** for both EN + AR.

**Step 4: Commit.**

---

### Task 30: Results — winner-celebration post-reveal layout

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

**Step 1: Tests:**
- After `onVerdict`: winner card prominent above-fold with emerald glow ring
- Cohort badge slides in from side after winner pulse
- "Why we picked this" section visible
- "Where the runner-up wins" section renders tradeoff pairs (NOT "What you trade off" — copy audit)
- Specs / Reviews collapsed by default
- Sticky footer with "What's next?" + Save + Share

**Step 2: Refactor ResultsScreen post-reveal layout.**

**Step 3: Copy audit on all visible strings** — apply table from design doc Section 4g.

**Step 4: Commit:** `feat(results): winner-celebration post-reveal layout + copy audit`

---

### Task 31: CohortBadge component (slide-in animation)

**Files:**
- Create or modify: `SmartCompareApp/src/components/CohortBadge.tsx`
- Test

**Step 1: Test** — accepts `peerCount`, `governorate`. Slides from right (LTR) / left (RTL) on mount with 240ms ease-out + opacity fade.

**Step 2: Build using `useSharedValue` + `withSpring`.**

**Step 3: Commit.**

---

### Task 32: Bottom nav refresh

**Files:**
- Modify: navigation config in `App.tsx`

**Step 1: Test** — selected icon scales 1.0 → 1.15 → 1.0 spring + emerald dot fades in below + filled icon. Inactive: 60% black opacity.

**Step 2: Wire custom TabIcons (Home, History, Profile) with selection-state animation.**

**Step 3: Commit.**

---

### Task 33: Phase 3 cross-QA gate

**Owner:** test-qa

**Step 1: Code review.**

**Step 2: Test all 3 modes on Home** — camera, link, type — all morph smoothly.

**Step 3: Test Results loading** with cache hit (1.2s minimum displayed) AND with slow real comparison (>10s) — confirm stage progression looks intentional.

**Step 4: Test 25s+ stall** — tips carousel appears, no scary copy.

**Step 5: Test offline / network drop** — silent retries, no scary banner.

**Step 6: Manual perf check** — 60fps on mid-range Android device during reveal animation.

**Step 7: Coverage ≥80% on Phase 3 changes.**

**Step 8: Send back any failing tasks. Iterate until clean.**

---

## Phase 4 — Referral + Bonus Expiry

**Goal:** Loop 2 funnel optimized. Bonus credits expire in 3 days. Push notifications ship.

**Owner:** backend (primary on data + cron + push), frontend-flow (UI), test-qa (cross-QA)

### Task 34: Backend — Migration 018 (expires_at on bonus credits)

**Owner:** backend

**Files:**
- Create: `migrations/018_referral_bonus_expires_at.sql`
- Create: `tests/test_migration_018.py`

**Step 1: Write SQL:**

```sql
-- Add expires_at to existing redemptions
ALTER TABLE public.referral_redemptions
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Backfill: existing in-flight credits get 3 days from now (one-time grace)
UPDATE public.referral_redemptions
SET expires_at = NOW() + INTERVAL '3 days'
WHERE expires_at IS NULL AND consumed_at IS NULL;

-- Index for cron query
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_expires_at
  ON public.referral_redemptions (expires_at)
  WHERE consumed_at IS NULL;

-- Same on Loop 1 deep_review_credits if separate table
ALTER TABLE public.referral_invites
  ADD COLUMN IF NOT EXISTS deep_review_expires_at TIMESTAMPTZ;
```

**Step 2: Apply via Supabase MCP** — `mcp__plugin_supabase_supabase__apply_migration` with name `018_referral_bonus_expires_at`. Tracks in migration history (preferred over SQL Editor per CLAUDE.md).

**Step 3: Verify schema with information_schema query.**

**Step 4: Commit:** `feat(db): migration 018 — bonus credit expires_at + index`

---

### Task 35: Backend — referral_service.py expiry logic

**Files:**
- Modify: `app/services/referral_service.py`
- Modify: `app/services/usage_service.py`
- Create: `tests/test_referral_expiry.py`

**Step 1: Tests:**
- New invitee redemption sets `expires_at = signup_time + 3 days`
- New inviter redemption sets `expires_at = issue_time + 3 days`
- Expired credits NOT counted in `usage_service.get_available_comparisons()`
- Active (non-expired) credits ARE counted

**Step 2: Update `try_trigger_loop2`** to set `expires_at` on row insert.

**Step 3: Update `usage_service.get_available_comparisons`** to filter by `expires_at > now()`.

**Step 4: Run, pass, commit:** `feat(referral): 3-day expiry on bonus credits + usage filter`

---

### Task 36: Backend — cron expire bonuses + send 24h reminder

**Files:**
- Create: `scripts/cron_expire_bonuses.py`
- Create: `tests/test_cron_expire_bonuses.py`

**Step 1: Test:**
- Finds users with bonuses expiring within 24h
- Sends Expo push: "Don't forget — your X bonus comparisons from {referrer} expire tomorrow."
- Marks notification sent so we don't double-send
- Idempotent (re-running doesn't duplicate)

**Step 2: Build cron script.** Use existing `push_service.py` infra.

**Step 3: Schedule via existing cron infrastructure** (same pattern as `cron_reengagement.py` mentioned in CLAUDE.md).

**Step 4: Commit:** `feat(cron): expire bonus credits + 24h reminder push`

---

### Task 37: Backend — Loop 2 push notification copy (gift framing)

**Files:**
- Modify: `app/services/push_service.py`
- Test

**Step 1: Test:**
- Push fires when invitee completes first comparison
- Title: "Your friend just compared something"
- Body: "{name}, your friend just used Qaren. You got 5 bonus comparisons. Expires in 3 days."

**Step 2: Implement.**

**Step 3: Commit:** `feat(push): Loop 2 success notification with gift-framing copy`

---

### Task 38: Frontend — ReferralLandingScreen partial-blur redesign

**Files:**
- Modify: `SmartCompareApp/src/screens/ReferralLandingScreen.tsx`

**Step 1: Tests:**
- Product names + images visible (no blur on those)
- Cohort badge visible
- Winner ✓ + glow + reasoning + score are GATED behind quiz or signup
- Two CTAs: "See how it scores for YOU" (emerald, signature variant) → quiz; "Just give me the app" (small text link) → onboarding

**Step 2: Refactor screen per design doc Section 4e.**

**Step 3: Use existing `_strip_personalization` already in backend; combine with frontend "partial blur" logic.**

**Step 4: Commit:** `feat(referral): partial-blur invitee landing with curiosity gap + 2 CTAs`

---

### Task 39: Frontend — InviteeQuizScreen reveal with personalized score

**Files:**
- Modify: `SmartCompareApp/src/screens/InviteeQuizScreen.tsx`

**Step 1: Tests:**
- After 4Q quiz: reveal screen shows winner with emerald glow + match score animating 0 → N via CounterTicker
- "How your answers shaped this" section echoes user's quiz answers
- Soft signup CTA at bottom (black, "Try Qaren free — 5 comparisons")

**Step 2: Build reveal screen.**

**Step 3: Commit:** `feat(invitee-quiz): personalized score reveal animation`

---

### Task 40: Frontend — ShareBottomSheet redesign

**Files:**
- Modify: `SmartCompareApp/src/components/ShareBottomSheet.tsx`

**Step 1: Tests:**
- Live preview card reflects privacy toggles (show_name, show_winner, show_reasons) in real-time
- "You'll unlock" reward block visible
- After share: toast "✦ Sent to {name}. We'll add 5 more if they sign up."

**Step 2: Refactor per design doc Section 4e.**

**Step 3: Commit:** `feat(share): live-preview share sheet with reward block`

---

### Task 41: Frontend — Home countdown surface

**Files:**
- Modify: `SmartCompareApp/src/screens/HomeScreen.tsx`
- Create or modify: freemium counter component

**Step 1: Test:**
- If user has invitee bonus active: shows "5 free — 2 from {referrer} (expires 2d 14h)" with countdown ticker
- Countdown updates each minute
- After expiry: drops to "3 free anytime"

**Step 2: Build.** Use CounterTicker for the time display.

**Step 3: Commit.**

---

### Task 42: Phase 4 cross-QA gate

**Owner:** test-qa

**Step 1: End-to-end Loop 2 dry run on staging:**
1. Sender shares from Results → invitee link generated
2. Open link in fresh browser → partial-blur landing renders
3. Tap "Try Qaren free" → onboarding flow → signup
4. Confirm 5 comparisons available (3 + 2 invitee bonus, with 3-day expiry on the 2)
5. Make first comparison
6. Confirm sender receives push: "Your friend just compared..."
7. Confirm sender now has +5 bonus with 3-day expiry

**Step 2: Cron dry run** — set test row's `expires_at` to 23h from now, run cron, confirm push sent.

**Step 3: Code review.**

**Step 4: Coverage ≥80%.**

**Step 5: Send back failures, iterate.**

---

## Phase 5 — Profile + Polish + Canary Rollout

**Goal:** Close the loop. Audit everything. Roll feature flag from 10% → 50% → 100%.

**Owner:** frontend-flow + test-qa

### Task 43: Profile — cohort match card promoted to top

**Files:**
- Modify: `SmartCompareApp/src/screens/ProfileScreen.tsx`

**Step 1: Test:**
- Top of Profile shows cohort match card with strength badge, peer count, governorate, progress bar to "Strong"
- Tap → reveals which priorities your peers share, what categories they buy, "improve match" link
- "Improve match" tap → opens Demographics edit OR re-take quiz (decide: open question #6 in design doc)

**Step 2: Build per design doc Section 4d.**

**Step 3: Use `cohort_service.get_display_profile()` — already exists.**

**Step 4: Commit.**

---

### Task 44: Audit — copy sweep across all screens

**Owner:** test-qa

**Step 1: Run grep for forbidden words:**

```bash
grep -rE "(couldn't|try again|unusual|edge cases|locked|unlock|connection lost|something went wrong|error)" SmartCompareApp/src/i18n/
```

Expected: zero matches in user-facing copy. (Internal log strings OK.)

**Step 2: For each match, propose replacement per design doc Section 4g table.**

**Step 3: Apply fixes.**

**Step 4: Commit:** `chore: copy audit — replace scary language with confident verbs`

---

### Task 45: RTL audit

**Owner:** test-qa

**Step 1: Switch app to AR.**

**Step 2: Walk every screen, every flow:**
- Onboarding 1-17
- Home (camera, link, type modes)
- Results (loading + reveal)
- History
- Profile
- Share / Referral
- Invitee quiz

**Step 3: Document any mirror bugs in TaskCreate followups.**

**Step 4: Fix all bugs.**

**Step 5: Commit:** `fix: RTL mirror corrections across redesigned screens`

---

### Task 46: Accessibility audit

**Owner:** test-qa

**Step 1: Touch targets** — confirm all interactive elements ≥44pt (use accessibility inspector).

**Step 2: Contrast** — run WCAG contrast check on:
- Black on white (primary CTA): 21:1 ✓
- Emerald on white (badges): ~3.5:1 — need to verify on small text only used in chips, not body
- Body text: 16pt+ minimum

**Step 3: Screen reader labels** — every icon button has `accessibilityLabel`. Every animated section has `accessibilityRole`.

**Step 4: Reduced-motion** — respects OS setting; animations skip to final state when on.

**Step 5: Commit fixes:** `fix(a11y): touch targets, contrast, screen reader labels, reduced motion`

---

### Task 47: Canary rollout — `ENABLE_NEW_ONBOARDING` 10%

**Owner:** backend (helper) + test-qa (wire + monitor)

**REVISION (Task 47 implementation, commit 5685272):** the ramp knob is NOT a Railway env var. `ENABLE_NEW_ONBOARDING` is a frontend build-time getter that evaluates `hashBucket(stableId, CANARY_NEW_ONBOARDING_PERCENT)` per call. The actual rollout mechanic:

**Step 1: Set `CANARY_NEW_ONBOARDING_PERCENT = 10`** in `SmartCompareApp/src/config/features.ts`. Push via `eas update --branch production` — JS/TS-only change, no app-store re-release.

The bucketing primitive (`SmartCompareApp/src/config/featureBucket.ts`) uses djb2 hash on a stable id (device-id pre-signup via expo-secure-store, user.id post-signup). Same `(id, percent)` → same boolean every call, every device. App.tsx wires `getStableId() + setFlagStableId()` in `init()` BEFORE any state setter that gates onboarding render — no flicker.

**Step 2: Monitor for 48h** via the analytics events shipped in Task #53 (`onboarding_started`, `onboarding_step_completed`, `onboarding_completed`) plus the `flow_variant` field added in commit c83acf0:
- Crash reports (should be near-zero on new flow vs legacy baseline)
- Onboarding completion rate per step (target: ≥75% complete all 17)
- First-comparison conversion (signup → compare, target: ≥85%)
- Drop-off heatmap (any single step >40% drop-off needs investigation)
- Loop 2 trigger rate ≥35% (referral mechanic)

**Step 3: If metrics OK → 50%. If not → revert + fix root cause + retry.**

---

### Task 48: Canary rollout — 50% → 100%

Same mechanic as Task 47: bump `CANARY_NEW_ONBOARDING_PERCENT` in `features.ts`, EAS Update.

**Step 1:** `CANARY_NEW_ONBOARDING_PERCENT = 50` for 72h.
**Step 2:** Check metrics (same criteria as Task 47).
**Step 3:** `CANARY_NEW_ONBOARDING_PERCENT = 100` if all green.
**Step 4:** After 7 days at 100%, remove the legacy `OnboardingScreen` import + conditional from App.tsx.

---

### Task 49: Final cross-QA + team disassemble

**Owner:** test-qa (signoff)

**Exit criteria — ALL must be true:**

- [ ] All tasks marked completed in TaskList
- [ ] `npx tsc --noEmit` exits 0
- [ ] `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)"` passes
- [ ] Coverage ≥80% on all new code (`npm run test:coverage`, `pytest --cov`)
- [ ] Each agent has performed at least one cross-QA on another agent's work
- [ ] All QA findings either resolved or explicitly deferred via TaskCreate'd follow-up
- [ ] Copy audit clean (grep returns zero matches for forbidden words)
- [ ] RTL run-through complete
- [ ] Accessibility audit complete
- [ ] Feature flag at 100% (or explicit hold reason)
- [ ] Loop 2 end-to-end dry run passed on staging
- [ ] Push notifications confirmed working on physical iOS + Android
- [ ] Update CLAUDE.md, MEMORY.md, `docs/CONTEXT_SESSION_LOG.md` (per Operating Principle #5)

**Step 1: Each criterion checked off explicitly with link to evidence (commit, test output, screenshot).**

**Step 2: Final commit:** `chore: Phase 5 complete — Qaren UX redesign shipped`

**Step 3: Disassemble team via TeamDelete.**

---

## Team Brief (paste verbatim to each agent at Task 0)

```
You are part of the qaren-ux-redesign team — a 4-Opus team implementing
a major UX redesign across the Qaren mobile app + backend.

DESIGN SPEC: docs/plans/2026-05-06-qaren-ux-redesign-design.md
PLAN: docs/plans/2026-05-06-qaren-ux-redesign.md (this document)
WORKING DIRECTORY: C:\Users\SynAckITPC\Documents\ai\smartcompare

ROLE: {frontend-visual | frontend-flow | backend | test-qa} (set per agent)

MANDATORY RULES (per user directive):
1. Features 100% complete before disassemble. No partial commits at end.
2. Cross-QA mandatory. Each agent QAs at least one other's work.
3. Idle agents write red-green tests targeting 80% coverage OR wait for QA.
4. Path-restricted commits: `git commit -m "msg" -- <paths>`
5. NEVER use `git commit -- <paths> -m "msg"` (-m parsed as path, errors)

REQUIRED TOOLS / SKILLS:
- typescript-lsp via project config; trust ONLY `npx tsc --noEmit` exit 0
  as ground truth (project MEMORY.md notes LSP unreliable on Windows)
- context7 MCP (`mcp__plugin_context7_context7__query-docs`) for any
  library version-sensitive question. Don't guess from training data.
- superpowers:code-reviewer skill for cross-QA passes
- superpowers:test-driven-development for red-green cycles
- superpowers:verification-before-completion before claiming work done.
  Run verification + confirm output. Evidence > assertions.
- superpowers:systematic-debugging when bugs surface. Diagnose root cause,
  don't bypass.
- superpowers:prove-it-works for bug fixes (reproduce bug first)
- mcp__plugin_supabase_supabase__apply_migration for DDL (NOT SQL Editor)
- figma:figma-implement-design for hero illustration #1 if Figma file present

WORKFLOW (per task):
1. Claim task via TaskUpdate (set owner=your-name)
2. Use context7 to fetch any library docs you need
3. Write failing test first
4. Run test, confirm fail
5. Implement minimal code to pass
6. Run test, confirm pass
7. Run `npx tsc --noEmit` (frontend) or `python -m py_compile` (backend)
8. Path-restricted commit
9. TaskUpdate status=completed
10. Claim next available task OR claim a QA task on another's work

QA WORKFLOW:
1. Pull diff: `git diff <range>`
2. Use superpowers:code-reviewer skill on the diff
3. Check exit criteria for that task (tests pass, types clean,
   coverage, copy audit, RTL works, a11y OK)
4. If pass: leave QA approval comment in TaskUpdate description
5. If fail: TaskUpdate the original task back to in_progress with
   specific findings; original author re-iterates

NEVER:
- Skip hooks or `--no-verify` on commits
- Use destructive git ops (reset --hard, force push) unless user-authorized
- Mark task complete with failing tests
- Write copy that implies the app might not work ("error", "couldn't",
  "try again later", "unusual", "edge cases", "connection lost")
- Use `npm install` for Expo native deps (use `npx expo install`)
- Edit files in `backend/app/` — that directory is NOT deployed
  (root `app/` is deployed; see CLAUDE.md "Critical: Two app/ Directories")

ALWAYS:
- Read CLAUDE.md before any major action
- Test in light + RTL (Arabic) before claiming complete
- Confirm migrations via Supabase MCP, not SQL Editor
- Check existing tests pass after every change (`npm test` / `pytest`)

Begin by reading the design spec and the plan top-to-bottom. Claim the
lowest-numbered available task assigned to your role.
```

---

## Open Questions (resolve as encountered)

Tracked in design doc Section 9. Re-list here for execution-time visibility:

1. Designer for hero illustration #1 — internal or commission?
2. Geist font license — confirm SIL OFL allows commercial mobile redistribution (Task 1 step 2)
3. Migration 018 — exact `expires_at` semantics for in-flight credits (Task 34 backfills with 3-day grace)
4. Push notification testing on physical iOS + Android (Task 42)
5. Tips carousel content review by Ahmed (Task 29)
6. Cohort match card "improve match" tap behavior — opens Demographics edit OR re-take quiz? (Task 43)
7. Web landing pages (Phase 6) — separate scope, not in this plan

---

**End of plan.** Total: 49 tasks across 5 phases. Estimated 5-6 sessions of execution. Implementation begins via 4-Opus team per Section 7 of the design doc.
