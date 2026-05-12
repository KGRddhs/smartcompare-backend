# Bundle B/C/D Consolidated Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship Bundle B (Arabic proofread), Bundle C (Cal-AI camera redesign + glyph polish + animation polish + UX hints), and Bundle D (perf audit + obvious fixes) plus referral hardening (3 lifetime/device + signup-decrement + 7-day expiry + hybrid DIY install-survival) as one consolidated PR.

**Architecture:** Single feature branch `feature/bundle-bcd` in worktree `../smartcompare-bundle-bcd`. Four Opus agents (backend-bcd, frontend-bcd, test-bcd, qa-bcd) run parallel within phases, with mandatory cross-QA before disband. Migration 023 + Cloudflare Worker for web fallback. One EAS dev build at end for native-module verification (Play Install Referrer).

**Tech Stack:** FastAPI + Python 3.12 (backend), React Native + Expo SDK 54 (frontend), Reanimated 4 + react-native-svg + lucide-react-native (UI), react-native-play-install-referrer (Android native), expo-clipboard (iOS), expo-image-picker (camera), Cloudflare Workers (web fallback), Supabase MCP (migrations), Jest + pytest (tests).

**Design doc:** `docs/plans/2026-05-12-bundle-bcd-consolidated-design.md` (committed in `a5b57a4`).

**Bundle A precedent:** `docs/plans/2026-05-11-bundle-a-p0-fixes.md`.

---

## Phase 0 — Worktree + branch setup

### Task 0.1: Create worktree and branch

**Owner:** Ahmed (interactive — Claude can't pipe to git for worktree create with auth)

**Files:** none (git operation)

**Step 1: From project root, create worktree**
```bash
git worktree add -b feature/bundle-bcd ../smartcompare-bundle-bcd main
```

**Step 2: Verify worktree**
```bash
cd ../smartcompare-bundle-bcd
git status   # Should show: On branch feature/bundle-bcd
git log -1 --oneline   # Should show: a5b57a4 docs(plans): Bundle B/C/D...
```

**Step 3: Install frontend deps in worktree (one-time)**
```bash
cd SmartCompareApp
npm install
```

**Step 4: Verify build baseline**
```bash
npx tsc --noEmit   # Expected: exit 0
npx jest --silent   # Expected: 588/588 passing (Bundle A baseline)
```

**Step 5: Commit nothing yet — this is setup**

---

## Phase 1 — Foundation (parallel, ~day 1)

### Task 1.1: Migration 023 — drop weekly counter, add lifetime counter

**Owner:** backend-bcd

**Files:**
- Create: `migrations/023_referral_lifetime_cap.sql`
- Create: `migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql`

**Step 1: Write the migration**

`migrations/023_referral_lifetime_cap.sql`:
```sql
-- Migration 023: Replace weekly per-user invite cap with lifetime per-device cap.
-- Aligns with Bundle A's device-bound anti-abuse model (Migration 021).

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS lifetime_invites_consumed INT NOT NULL DEFAULT 0;

ALTER TABLE users
  DROP COLUMN IF EXISTS weekly_invites_used;

CREATE INDEX IF NOT EXISTS idx_users_device_fingerprint_active
  ON users(device_fingerprint_hash)
  WHERE device_fingerprint_hash IS NOT NULL;

COMMENT ON COLUMN users.lifetime_invites_consumed IS
  'Successful referrals attributed to this user. Hard cap 3 enforced per device fingerprint (not per user). Set at receiver signup completion, never reset.';
```

**Step 2: Write rollback**

`migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql`:
```sql
ALTER TABLE users DROP COLUMN IF EXISTS lifetime_invites_consumed;
DROP INDEX IF EXISTS idx_users_device_fingerprint_active;
ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_invites_used INT NOT NULL DEFAULT 0;
```

**Step 3: Apply via Supabase MCP**

Tool: `mcp__plugin_supabase_supabase__apply_migration`
Args: `{name: "023_referral_lifetime_cap", query: "<contents of 023_referral_lifetime_cap.sql>"}`
Expected: no error; migration history table updated.

**Step 4: Verify schema**

Tool: `mcp__plugin_supabase_supabase__list_tables`
Filter: `users`
Expected: `lifetime_invites_consumed INT NOT NULL DEFAULT 0` present; `weekly_invites_used` absent.

**Step 5: Commit**
```bash
git add migrations/023_referral_lifetime_cap.sql migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql
git commit -m "feat(migration): 023 lifetime invite cap + device fingerprint index"
```

---

### Task 1.2: Backend — `attribution_service.py` scaffold

**Owner:** backend-bcd

**Files:**
- Create: `app/services/attribution_service.py`
- Create: `tests/test_attribution_service.py`

**Step 1: Write failing test**

`tests/test_attribution_service.py`:
```python
import pytest
from app.services.attribution_service import parse_install_referrer

def test_parse_install_referrer_returns_code_for_valid_qr():
    referrer_raw = "referrer=QR-ATAUX9&utm_source=share"
    assert parse_install_referrer(referrer_raw) == "QR-ATAUX9"

def test_parse_install_referrer_returns_none_for_invalid_format():
    assert parse_install_referrer("referrer=garbage&utm_source=x") is None

def test_parse_install_referrer_returns_none_for_empty():
    assert parse_install_referrer("") is None

def test_parse_install_referrer_returns_none_for_self_referral_pattern():
    # Defense-in-depth: a referrer with no QR- prefix is invalid
    assert parse_install_referrer("referrer=QR-LOWER1") is None  # case-sensitive uppercase only
```

**Step 2: Run test, verify fails**
```bash
python -m pytest tests/test_attribution_service.py -v
# Expected: ImportError: cannot import name 'parse_install_referrer'
```

**Step 3: Write minimal implementation**

`app/services/attribution_service.py`:
```python
"""Hybrid DIY install-survival attribution.

Replaces Branch.io after its free tier paywalled to $199/mo. Parses raw
Play Install Referrer payloads (Android) and clipboard payloads (iOS) into
canonical QR-XXXXXX invite codes for handoff to referral_service.

Reference: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
"""
import re
from typing import Optional
from urllib.parse import parse_qs

_QR_CODE_PATTERN = re.compile(r'^QR-[A-Z0-9]{6}$')


def parse_install_referrer(raw: str) -> Optional[str]:
    """Extract a QR-XXXXXX code from a Play Install Referrer or clipboard string.

    Args:
        raw: Either a URL-encoded query string (`referrer=QR-XYZ123&...`) or
             a bare code (`QR-XYZ123`).

    Returns:
        The validated code, or None if no match.
    """
    if not raw:
        return None

    # Bare code
    if _QR_CODE_PATTERN.match(raw):
        return raw

    # URL-encoded query string
    try:
        params = parse_qs(raw)
    except Exception:
        return None
    candidates = params.get("referrer", [])
    for candidate in candidates:
        if _QR_CODE_PATTERN.match(candidate):
            return candidate
    return None
```

**Step 4: Run test, verify passes**
```bash
python -m pytest tests/test_attribution_service.py -v
# Expected: 4 passed
```

**Step 5: Commit**
```bash
git add app/services/attribution_service.py tests/test_attribution_service.py
git commit -m "feat(attribution): scaffold parse_install_referrer for hybrid DIY"
```

---

### Task 1.3: Backend — Arabic proofread first pass

**Owner:** backend-bcd

**Files:**
- Create: `.drafts/ar-proofread.diff` (gitignored)
- Read-only: `SmartCompareApp/src/i18n/ar.json`

**Step 1: Read current `ar.json`**

Use Read tool on `SmartCompareApp/src/i18n/ar.json`.

**Step 2: Generate proofread suggestions**

Run an AI proofread pass over the 514 keys focusing on:
- MSA vs. Gulf dialect consistency (target: neutral MSA suitable for all GCC users; reject overly Egyptian, Levantine, or Maghrebi colorings)
- Stilted machine-translated phrasings (look for direct EN→AR word-for-word patterns)
- RTL punctuation (Arabic-specific: `،` not `,`; `؟` not `?`; `؛` not `;`)
- Interpolation token preservation — `{{count}}`, `{{name}}`, `{{code}}`, `{{strength}}` must appear in EXACT same positions
- Gender-neutral framing where possible (Arabic verbs have gender; default to masculine generic per regional convention)

**Step 3: Write `.drafts/ar-proofread.diff`**

Format as a unified diff so reviewer can see before/after side-by-side. Sample:
```diff
--- a/SmartCompareApp/src/i18n/ar.json
+++ b/SmartCompareApp/src/i18n/ar.json
@@ -100,7 +100,7 @@
   "home.hero": "قارن المنتجات في 30 ثانية",
-  "home.cta.scan": "افحص",
+  "home.cta.scan": "امسح ضوئياً",
```

**Step 4: Await Ahmed's approval**

Ahmed reviews `.drafts/ar-proofread.diff` and:
- Accepts: gives green-light → backend-bcd applies the diff to `ar.json` in Phase 2 Task 2.0
- Rejects specific entries: edits the diff to keep what they want, backend-bcd applies edited version
- Rejects entirely: drops Bundle B from this PR

**Step 5: Do NOT commit `.drafts/`** — it's in `.gitignore` already; the diff is intermediate state

---

### Task 1.4: Frontend — `ScanCameraScreen` skeleton

**Owner:** frontend-bcd

**Files:**
- Create: `SmartCompareApp/src/screens/ScanCameraScreen.tsx`
- Create: `SmartCompareApp/src/screens/__tests__/ScanCameraScreen.test.tsx`

**Step 1: Write failing test**

`SmartCompareApp/src/screens/__tests__/ScanCameraScreen.test.tsx`:
```tsx
import React from 'react';
import { render } from '@testing-library/react-native';
import ScanCameraScreen from '../ScanCameraScreen';

const mockNavigation = { goBack: jest.fn(), navigate: jest.fn() } as any;

describe('ScanCameraScreen', () => {
  it('renders close button with testID', () => {
    const { getByTestId } = render(<ScanCameraScreen navigation={mockNavigation} route={{} as any} />);
    expect(getByTestId('scan-camera-close')).toBeTruthy();
  });

  it('renders help button with testID', () => {
    const { getByTestId } = render(<ScanCameraScreen navigation={mockNavigation} route={{} as any} />);
    expect(getByTestId('scan-camera-help')).toBeTruthy();
  });

  it('renders 2 image slots', () => {
    const { getAllByTestId } = render(<ScanCameraScreen navigation={mockNavigation} route={{} as any} />);
    expect(getAllByTestId(/^image-slot-\d$/)).toHaveLength(2);
  });
});
```

**Step 2: Run test, verify fails**
```bash
cd SmartCompareApp
npx jest src/screens/__tests__/ScanCameraScreen.test.tsx
# Expected: Cannot find module '../ScanCameraScreen'
```

**Step 3: Write minimal skeleton**

`SmartCompareApp/src/screens/ScanCameraScreen.tsx`:
```tsx
/**
 * Cal-AI-style fullscreen camera modal.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 */
import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { X, HelpCircle } from 'lucide-react-native';
import { colors } from '../theme';
import ImageSlotRow from '../components/ImageSlotRow';
import ScannerReticle from '../components/ScannerReticle';

type Slot = { uri: string } | null;

export default function ScanCameraScreen({ navigation }: any) {
  const [slots, setSlots] = useState<[Slot, Slot]>([null, null]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity testID="scan-camera-close" onPress={() => navigation.goBack()}>
          <X color="white" size={28} />
        </TouchableOpacity>
        <TouchableOpacity testID="scan-camera-help">
          <HelpCircle color="white" size={28} />
        </TouchableOpacity>
      </View>
      <ScannerReticle />
      <ImageSlotRow slots={slots} onChange={setSlots} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.inverse },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', padding: 16 },
});
```

**Step 4: Run test, verify passes**
```bash
npx jest src/screens/__tests__/ScanCameraScreen.test.tsx
# Expected: 3 passed (after Task 1.5 + 1.6 land ImageSlotRow + ScannerReticle stubs)
```
NOTE: If ImageSlotRow / ScannerReticle don't exist yet, the test errors with "Cannot find module". Land Tasks 1.5 + 1.6 first OR stub them temporarily.

**Step 5: Commit**
```bash
git add SmartCompareApp/src/screens/ScanCameraScreen.tsx SmartCompareApp/src/screens/__tests__/ScanCameraScreen.test.tsx
git commit -m "feat(camera): ScanCameraScreen skeleton with close/help/slots"
```

---

### Task 1.5: Frontend — `ScannerReticle` component

**Owner:** frontend-bcd

**Files:**
- Create: `SmartCompareApp/src/components/ScannerReticle.tsx`
- Create: `SmartCompareApp/src/components/__tests__/ScannerReticle.test.tsx`

**Step 1: Write failing test**

```tsx
import React from 'react';
import { render } from '@testing-library/react-native';
import ScannerReticle from '../ScannerReticle';

describe('ScannerReticle', () => {
  it('renders SVG with 4 corner brackets', () => {
    const { UNSAFE_getAllByType } = render(<ScannerReticle />);
    const paths = UNSAFE_getAllByType('Path' as any);
    expect(paths.length).toBeGreaterThanOrEqual(4); // 4 corners
  });
});
```

**Step 2: Run test, verify fails**

**Step 3: Write minimal implementation**

```tsx
/**
 * 4 corner brackets centered on screen, animated pulse via Reanimated.
 * Spec: design doc § 4.6 reticle layout.
 */
import React, { useEffect } from 'react';
import { Dimensions, StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming } from 'react-native-reanimated';

const SIZE = Math.min(Dimensions.get('window').width * 0.7, 280);
const BRACKET = 30; // length of each corner bracket
const STROKE = 3;

export default function ScannerReticle() {
  const pulse = useSharedValue(1);

  useEffect(() => {
    pulse.value = withRepeat(withTiming(1.04, { duration: 1200 }), -1, true);
  }, []);

  const animStyle = useAnimatedStyle(() => ({ transform: [{ scale: pulse.value }] }));

  return (
    <View style={styles.center} pointerEvents="none">
      <Animated.View style={animStyle}>
        <Svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          {/* Top-left */}
          <Path d={`M 0 ${BRACKET} L 0 0 L ${BRACKET} 0`} stroke="white" strokeWidth={STROKE} fill="none" />
          {/* Top-right */}
          <Path d={`M ${SIZE - BRACKET} 0 L ${SIZE} 0 L ${SIZE} ${BRACKET}`} stroke="white" strokeWidth={STROKE} fill="none" />
          {/* Bottom-right */}
          <Path d={`M ${SIZE} ${SIZE - BRACKET} L ${SIZE} ${SIZE} L ${SIZE - BRACKET} ${SIZE}`} stroke="white" strokeWidth={STROKE} fill="none" />
          {/* Bottom-left */}
          <Path d={`M ${BRACKET} ${SIZE} L 0 ${SIZE} L 0 ${SIZE - BRACKET}`} stroke="white" strokeWidth={STROKE} fill="none" />
        </Svg>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, alignItems: 'center', justifyContent: 'center' },
});
```

**Step 4: Run test, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/components/ScannerReticle.tsx SmartCompareApp/src/components/__tests__/ScannerReticle.test.tsx
git commit -m "feat(camera): ScannerReticle SVG with pulse animation"
```

---

### Task 1.6: Frontend — `ImageSlotRow` component

**Owner:** frontend-bcd

**Files:**
- Create: `SmartCompareApp/src/components/ImageSlotRow.tsx`
- Create: `SmartCompareApp/src/components/__tests__/ImageSlotRow.test.tsx`

**Step 1: Write failing tests**

```tsx
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import ImageSlotRow from '../ImageSlotRow';

describe('ImageSlotRow', () => {
  it('renders 2 empty slots with placeholder styling', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<ImageSlotRow slots={[null, null]} onChange={onChange} />);
    expect(getByTestId('image-slot-0')).toBeTruthy();
    expect(getByTestId('image-slot-1')).toBeTruthy();
  });

  it('renders thumbnail when slot filled', () => {
    const { getByTestId } = render(
      <ImageSlotRow slots={[{ uri: 'file://photo1.jpg' }, null]} onChange={jest.fn()} />
    );
    expect(getByTestId('image-slot-0-thumb')).toBeTruthy();
  });

  it('removes slot when × tapped', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <ImageSlotRow slots={[{ uri: 'file://photo1.jpg' }, null]} onChange={onChange} />
    );
    fireEvent.press(getByTestId('image-slot-0-remove'));
    expect(onChange).toHaveBeenCalledWith([null, null]);
  });
});
```

**Step 2: Run, verify fails**

**Step 3: Write minimal implementation**

```tsx
import React from 'react';
import { View, Image, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { X } from 'lucide-react-native';
import { colors, spacing, radii } from '../theme';

type Slot = { uri: string } | null;
type Props = { slots: [Slot, Slot]; onChange: (next: [Slot, Slot]) => void };

export default function ImageSlotRow({ slots, onChange }: Props) {
  const remove = (idx: 0 | 1) => {
    const next: [Slot, Slot] = [...slots] as any;
    next[idx] = null;
    onChange(next);
  };

  return (
    <View style={styles.row}>
      {[0, 1].map((idx) => {
        const slot = slots[idx];
        return (
          <View key={idx} testID={`image-slot-${idx}`} style={styles.slot}>
            {slot ? (
              <>
                <Image testID={`image-slot-${idx}-thumb`} source={{ uri: slot.uri }} style={styles.thumb} />
                <TouchableOpacity testID={`image-slot-${idx}-remove`} style={styles.remove} onPress={() => remove(idx as 0 | 1)}>
                  <X size={14} color="white" />
                </TouchableOpacity>
              </>
            ) : (
              <Text style={styles.placeholder}>{idx + 1}</Text>
            )}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'center', gap: spacing.sm, padding: spacing.base },
  slot: { width: 80, height: 80, borderRadius: radii.base, borderWidth: 2, borderColor: 'rgba(255,255,255,0.5)', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
  thumb: { width: '100%', height: '100%', borderRadius: radii.base },
  placeholder: { color: 'white', fontSize: 32, fontWeight: '300' },
  remove: { position: 'absolute', top: -8, right: -8, backgroundColor: 'rgba(0,0,0,0.7)', borderRadius: 12, width: 24, height: 24, alignItems: 'center', justifyContent: 'center' },
});
```

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/components/ImageSlotRow.tsx SmartCompareApp/src/components/__tests__/ImageSlotRow.test.tsx
git commit -m "feat(camera): ImageSlotRow with 2 slots + remove"
```

---

### Task 1.7: Frontend — install native deps + verify

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/package.json`

**Step 1: Install deps**
```bash
cd SmartCompareApp
npx expo install react-native-play-install-referrer expo-clipboard expo-image-picker
```

**Step 2: Verify package.json updated**
```bash
cat package.json | grep -E "play-install-referrer|expo-clipboard|expo-image-picker"
# Expected: all 3 present with versions
```

**Step 3: Verify TS still compiles**
```bash
npx tsc --noEmit
# Expected: exit 0
```

**Step 4: Run baseline tests**
```bash
npx jest --silent
# Expected: still passing
```

**Step 5: Commit**
```bash
git add package.json package-lock.json
git commit -m "deps: react-native-play-install-referrer + expo-clipboard + expo-image-picker"
```

---

### Task 1.8: Frontend — `App.tsx` modal route for `ScanCamera`

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/App.tsx`
- Test: `SmartCompareApp/src/__tests__/App.routing.test.tsx`

**Step 1: Write failing test (routing exists)**

Add to `App.routing.test.tsx`:
```tsx
it('declares ScanCamera modal route in root stack', () => {
  // smoke check the route is registered
  const navigationRef = require('../App').__navigationRef;
  // (specific assertion depends on existing test scaffolding — adapt to project pattern)
});
```
NOTE: If this scaffolding doesn't exist, write a smoke test that imports App and asserts no throw.

**Step 2: Run, verify fails or skip if hard to assert**

**Step 3: Add route in `App.tsx`**

Locate the root stack navigator and add (matching existing modal route pattern):
```tsx
<Stack.Screen
  name="ScanCamera"
  component={ScanCameraScreen}
  options={{ presentation: 'modal', headerShown: false }}
/>
```

**Step 4: Run baseline tests**

**Step 5: Commit**
```bash
git add SmartCompareApp/App.tsx SmartCompareApp/src/__tests__/App.routing.test.tsx
git commit -m "feat(camera): wire ScanCamera modal route in App.tsx"
```

---

### Task 1.9: Frontend — `playInstallReferrerService.ts` skeleton

**Owner:** frontend-bcd

**Files:**
- Create: `SmartCompareApp/src/services/playInstallReferrerService.ts`
- Create: `SmartCompareApp/src/services/__tests__/playInstallReferrerService.test.ts`

**Step 1: Write failing tests**

```ts
import { tryReadPlayInstallReferrer } from '../playInstallReferrerService';

jest.mock('react-native-play-install-referrer', () => ({
  PlayInstallReferrer: {
    getInstallReferrerInfo: jest.fn(),
  },
}));

describe('playInstallReferrerService', () => {
  it('returns code when referrer contains valid QR-XXXXXX', async () => {
    const { PlayInstallReferrer } = require('react-native-play-install-referrer');
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'referrer=QR-ATAUX9&utm_source=share' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBe('QR-ATAUX9');
  });

  it('returns null when no QR pattern found', async () => {
    const { PlayInstallReferrer } = require('react-native-play-install-referrer');
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'utm_source=organic' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null on Play Service error', async () => {
    const { PlayInstallReferrer } = require('react-native-play-install-referrer');
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb(null, new Error('PLAY_SERVICE_UNAVAILABLE'))
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });
});
```

**Step 2: Run, verify fails**

**Step 3: Write minimal implementation**

```ts
/**
 * Android-only: read Play Install Referrer once on app startup.
 * Spec: design doc § 4.1 Android section.
 */
import { Platform } from 'react-native';

const QR_PATTERN = /(?:^|[?&])referrer=(QR-[A-Z0-9]{6})(?:&|$)/;

export async function tryReadPlayInstallReferrer(): Promise<string | null> {
  if (Platform.OS !== 'android') return null;
  let mod: any;
  try {
    mod = require('react-native-play-install-referrer');
  } catch {
    return null; // module missing (Expo Go without dev client)
  }
  return new Promise((resolve) => {
    mod.PlayInstallReferrer.getInstallReferrerInfo((info: any, err: any) => {
      if (err || !info) return resolve(null);
      const raw: string = info.installReferrer || '';
      const match = QR_PATTERN.exec(raw);
      resolve(match ? match[1] : (raw === `QR-${raw.slice(3)}` && /^QR-[A-Z0-9]{6}$/.test(raw) ? raw : null));
    });
  });
}
```

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/services/playInstallReferrerService.ts SmartCompareApp/src/services/__tests__/playInstallReferrerService.test.ts
git commit -m "feat(referral): playInstallReferrerService Android-only reader"
```

---

### Task 1.10: Frontend — `clipboardFallbackService.ts` skeleton

**Owner:** frontend-bcd

**Files:**
- Create: `SmartCompareApp/src/services/clipboardFallbackService.ts`
- Create: `SmartCompareApp/src/services/__tests__/clipboardFallbackService.test.ts`

**Step 1: Write failing tests**

```ts
import { tryReadClipboardForInviteCode } from '../clipboardFallbackService';

jest.mock('expo-clipboard', () => ({
  getStringAsync: jest.fn(),
}));

describe('clipboardFallbackService', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns code when clipboard matches QR-XXXXXX', async () => {
    require('expo-clipboard').getStringAsync.mockResolvedValue('QR-ATAUX9');
    expect(await tryReadClipboardForInviteCode()).toBe('QR-ATAUX9');
  });

  it('returns null when clipboard does not match', async () => {
    require('expo-clipboard').getStringAsync.mockResolvedValue('hello world');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null when clipboard read throws', async () => {
    require('expo-clipboard').getStringAsync.mockRejectedValue(new Error('denied'));
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });
});
```

**Step 2: Run, verify fails**

**Step 3: Write minimal implementation**

```ts
/**
 * iOS-primary clipboard fallback for install-survival.
 * Spec: design doc § 4.1 iOS section.
 */
import * as Clipboard from 'expo-clipboard';

const QR_PATTERN = /^QR-[A-Z0-9]{6}$/;

export async function tryReadClipboardForInviteCode(): Promise<string | null> {
  try {
    const raw = (await Clipboard.getStringAsync()).trim();
    return QR_PATTERN.test(raw) ? raw : null;
  } catch {
    return null;
  }
}
```

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/services/clipboardFallbackService.ts SmartCompareApp/src/services/__tests__/clipboardFallbackService.test.ts
git commit -m "feat(referral): clipboardFallbackService iOS reader"
```

---

## Phase 2 — Core integration (parallel after Phase 1, ~day 2-3)

### Task 2.0: Backend — apply approved Arabic diff

**Owner:** backend-bcd

**Files:**
- Modify: `SmartCompareApp/src/i18n/ar.json`

**Step 1: Confirm Ahmed approved `.drafts/ar-proofread.diff`**

If not approved, BLOCK this task. Skip Bundle B if Ahmed rejects entirely.

**Step 2: Apply diff manually (Edit tool per key)**

For each line in approved diff, use Edit to update the corresponding key in `ar.json`.

**Step 3: Verify token preservation**

```bash
cd SmartCompareApp
node -e "
const en = require('./src/i18n/en.json');
const ar = require('./src/i18n/ar.json');
function flatten(o, p='') { const out={}; for (const k in o) { const key=p?p+'.'+k:k; if (o[k] && typeof o[k]==='object') Object.assign(out, flatten(o[k], key)); else out[key]=o[k]; } return out; }
const enF = flatten(en), arF = flatten(ar);
const enKeys = Object.keys(enF);
let mismatched = 0;
for (const k of enKeys) {
  const enTokens = (enF[k] || '').match(/\{\{\w+\}\}/g) || [];
  const arTokens = (arF[k] || '').match(/\{\{\w+\}\}/g) || [];
  if (enTokens.sort().join(',') !== arTokens.sort().join(',')) {
    console.log('TOKEN MISMATCH at', k, '— EN:', enTokens, 'AR:', arTokens);
    mismatched++;
  }
}
if (mismatched > 0) process.exit(1);
console.log('All interpolation tokens preserved.');
"
```
Expected: "All interpolation tokens preserved."

**Step 4: Verify EN/AR key parity unchanged**

```bash
node -e "
const en = require('./src/i18n/en.json');
const ar = require('./src/i18n/ar.json');
function flatten(o,p=''){ const out={}; for (const k in o) { const key=p?p+'.'+k:k; if (o[k] && typeof o[k]==='object') Object.assign(out, flatten(o[k], key)); else out[key]=o[k]; } return out; }
const enK = Object.keys(flatten(en)); const arK = Object.keys(flatten(ar));
if (enK.length !== arK.length || enK.some(k => !arK.includes(k))) { console.error('PARITY BROKEN'); process.exit(1); }
console.log('Parity:', enK.length, '=', arK.length);
"
```
Expected: "Parity: 514 = 514"

**Step 5: Commit**
```bash
git add SmartCompareApp/src/i18n/ar.json
git commit -m "i18n(ar): proofread pass — dialect consistency + RTL punctuation + stilted phrasings"
```

---

### Task 2.1: Backend — lifetime cap enforcement in `try_trigger_loop2`

**Owner:** backend-bcd

**Files:**
- Modify: `app/services/referral_service.py`
- Test: `tests/test_referral_lifetime_cap.py` (new)

**Step 1: Write failing tests**

```python
import pytest
from app.services.referral_service import try_trigger_loop2

@pytest.mark.asyncio
async def test_lifetime_cap_rejects_at_3_on_device(mock_supabase):
    """Device with 3 already-consumed lifetime invites cannot earn another."""
    mock_supabase.execute_sql.return_value = [{'sum': 3}]  # SUM(lifetime_invites_consumed) for this device
    result = await try_trigger_loop2(inviter_id='user_A', new_user_id='user_B', device_fp='deadbeef')
    assert result['triggered'] is False
    assert result['reason'] == 'device_lifetime_cap_reached'

@pytest.mark.asyncio
async def test_lifetime_cap_allows_under_3(mock_supabase):
    mock_supabase.execute_sql.return_value = [{'sum': 2}]
    result = await try_trigger_loop2(inviter_id='user_A', new_user_id='user_B', device_fp='deadbeef')
    assert result['triggered'] is True

@pytest.mark.asyncio
async def test_lifetime_cap_aggregates_across_users_on_same_device(mock_supabase):
    """Account A used 2, account B on same device used 1 — total 3 — block."""
    mock_supabase.execute_sql.return_value = [{'sum': 3}]
    result = await try_trigger_loop2(inviter_id='user_C', new_user_id='user_D', device_fp='deadbeef')
    assert result['triggered'] is False
```

**Step 2: Run, verify fails**

**Step 3: Modify `referral_service.try_trigger_loop2()`**

Find the function, add at start:
```python
# Lifetime device cap (Bundle B/C/D Migration 023)
device_cap_query = """
  SELECT COALESCE(SUM(lifetime_invites_consumed), 0) AS sum
  FROM users
  WHERE device_fingerprint_hash = $1
"""
row = await supabase.execute_sql(device_cap_query, [device_fp])
device_total = row[0]['sum'] if row else 0
LIFETIME_CAP = 3
if device_total >= LIFETIME_CAP:
    return {'triggered': False, 'reason': 'device_lifetime_cap_reached'}
```

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add app/services/referral_service.py tests/test_referral_lifetime_cap.py
git commit -m "feat(referral): lifetime device cap (3) enforcement in try_trigger_loop2"
```

---

### Task 2.2: Backend — signup-decrement in `try_trigger_loop2`

**Owner:** backend-bcd

**Files:**
- Modify: `app/services/referral_service.py`
- Test: `tests/test_referral_lifetime_cap.py` (extend)

**Step 1: Add failing test**

```python
@pytest.mark.asyncio
async def test_signup_increments_inviter_lifetime_counter(mock_supabase):
    mock_supabase.execute_sql.side_effect = [
        [{'sum': 1}],  # device cap query
        [{'success': True}],  # update query
    ]
    result = await try_trigger_loop2(inviter_id='user_A', new_user_id='user_B', device_fp='dead')
    assert result['triggered'] is True
    # Check the update query was the increment
    assert 'lifetime_invites_consumed' in str(mock_supabase.execute_sql.call_args_list[1])
```

**Step 2: Run, verify fails**

**Step 3: Add increment after cap passes**

In `try_trigger_loop2`, after the cap check passes and the redemption row is created:
```python
await supabase.execute_sql(
    "UPDATE users SET lifetime_invites_consumed = lifetime_invites_consumed + 1 WHERE id = $1",
    [inviter_id]
)
```

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add app/services/referral_service.py tests/test_referral_lifetime_cap.py
git commit -m "feat(referral): increment lifetime_invites_consumed on successful Loop 2"
```

---

### Task 2.3: Backend — 7-day expiry constant change

**Owner:** backend-bcd

**Files:**
- Modify: `app/services/referral_service.py`
- Modify: `tests/test_referral_expiry.py`

**Step 1: Find existing 3-day constant**

```bash
grep -n "interval '3 days'\|days=3\|3 \* 24" app/services/referral_service.py
```

**Step 2: Update test expectation**

In `tests/test_referral_expiry.py`, find tests asserting `expires_at == issued_at + 3 days`, change to `7 days`.

**Step 3: Run, verify fails**

**Step 4: Update constant to 7 days**

```python
# In referral_service.create_redemption() (or wherever expires_at is computed)
BONUS_EXPIRY_DAYS = 7  # was 3 in Bundle A Migration 018
```

**Step 5: Update existing redemption row test (must NOT change)**

Add a regression test asserting an existing 3-day row is NOT retroactively updated:
```python
def test_existing_3day_rows_retain_original_expiry():
    # Mock a redemption row with expires_at = issued_at + 3 days from Bundle A era
    # Apply migration — assert the row's expires_at is unchanged
    # (Migration 023 doesn't touch existing rows; this is a safety check)
    pass
```

**Step 6: Run, verify passes; commit**
```bash
git add app/services/referral_service.py tests/test_referral_expiry.py
git commit -m "feat(referral): bonus expiry 3 → 7 days; existing rows unchanged"
```

---

### Task 2.4: Backend — share endpoint stops decrementing

**Owner:** backend-bcd

**Files:**
- Modify: `app/api/referral_routes.py` (or wherever POST /share lives)
- Modify: `tests/test_referral_routes.py`

**Step 1: Add failing test**

```python
def test_share_does_not_decrement_lifetime_counter(authed_client, mock_supabase):
    # Pre-state: user has lifetime_invites_consumed = 0
    response = authed_client.post("/api/v1/referrals/share", json={...})
    assert response.status_code == 200
    # Post-state: still 0 (decrement happens at signup, not share)
    final = mock_supabase.execute_sql.call_args_list
    assert not any('UPDATE users SET lifetime_invites_consumed' in str(c) for c in final)

def test_share_returns_lifetime_remaining(authed_client, mock_supabase):
    mock_supabase.execute_sql.return_value = [{'lifetime_invites_consumed': 1}]
    response = authed_client.post("/api/v1/referrals/share", json={...})
    body = response.json()
    assert body['lifetime_invites_remaining'] == 2
```

**Step 2: Run, verify fails**

**Step 3: Remove decrement; add informational response**

In `referral_routes.share()`:
- Remove any `UPDATE users SET weekly_invites_used = ...` or similar
- Add to response: `{..., 'lifetime_invites_remaining': max(0, 3 - lifetime_invites_consumed)}`

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add app/api/referral_routes.py tests/test_referral_routes.py
git commit -m "feat(referral): /share no longer decrements; returns lifetime_remaining"
```

---

### Task 2.5: Backend — status endpoint returns lifetime counters

**Owner:** backend-bcd

**Files:**
- Modify: `app/api/referral_routes.py`
- Modify: `tests/test_referral_routes.py`

**Step 1: Add failing test**

```python
def test_status_returns_lifetime_counters(authed_client, mock_supabase):
    response = authed_client.get("/api/v1/referrals/status")
    body = response.json()
    assert 'lifetime_invites_used' in body
    assert 'lifetime_invites_remaining' in body
    assert 'weekly_invites_used' not in body
```

**Step 2: Run, verify fails**

**Step 3: Update GET /status response shape**

Replace `weekly_invites_used`/`weekly_invites_remaining` with `lifetime_invites_used`/`lifetime_invites_remaining`.

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add app/api/referral_routes.py tests/test_referral_routes.py
git commit -m "feat(referral): /status returns lifetime_invites_used/remaining"
```

---

### Task 2.6: Frontend — HomeScreen camera mode launches modal

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/screens/HomeScreen.tsx`
- Test: `SmartCompareApp/src/screens/__tests__/HomeScreen.test.tsx`

**Step 1: Write failing test**

```tsx
it('navigates to ScanCamera when scan mode chip is tapped', () => {
  const navigation = { navigate: jest.fn() } as any;
  const { getByTestId } = render(<HomeScreen navigation={navigation} />);
  fireEvent.press(getByTestId('mode-chip-scan'));
  expect(navigation.navigate).toHaveBeenCalledWith('ScanCamera');
});

it('MAX_IMAGES is 2 and MIN_IMAGES is 2', () => {
  // Read the module constants directly
  const HomeModule = require('../HomeScreen');
  expect(HomeModule.MAX_IMAGES).toBe(2);
});
```

**Step 2: Run, verify fails**

**Step 3: Edit `HomeScreen.tsx`**

- Change `const MAX_IMAGES = 4` → `const MAX_IMAGES = 2` (line 52)
- Update `handleModeChange('scan')` to `navigation.navigate('ScanCamera')` instead of showing inline camera
- Remove the inline camera card markup (lines ~444-580 — the CameraView block)
- Remove unused imports (`CameraView`, `useCameraPermissions`, etc.) if no longer referenced
- Update "Product N of 4" copy → use t() with new key `home.camera.slot` returning "1 of 2" / "2 of 2"

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/screens/HomeScreen.tsx SmartCompareApp/src/screens/__tests__/HomeScreen.test.tsx
git commit -m "feat(camera): HomeScreen scan-chip launches ScanCamera modal; gut inline"
```

---

### Task 2.7: Frontend — ScanCameraScreen camera + gallery picker

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/screens/ScanCameraScreen.tsx`
- Modify: `SmartCompareApp/src/screens/__tests__/ScanCameraScreen.test.tsx`

**Step 1: Add failing tests**

```tsx
it('captures photo into next empty slot on shutter press', async () => {
  const { getByTestId } = render(<ScanCameraScreen navigation={navMock} route={{} as any} />);
  fireEvent.press(getByTestId('shutter-button'));
  // assert mocked camera.takePictureAsync called
  // assert slot 0 now has a uri
});

it('launches gallery picker on gallery button press', async () => {
  const mockPickAsync = jest.fn().mockResolvedValue({ canceled: false, assets: [{ uri: 'file://lib.jpg' }] });
  jest.mock('expo-image-picker', () => ({ launchImageLibraryAsync: mockPickAsync }));
  const { getByTestId } = render(<ScanCameraScreen navigation={navMock} route={{} as any} />);
  fireEvent.press(getByTestId('gallery-button'));
  expect(mockPickAsync).toHaveBeenCalled();
});

it('shows Compare CTA only when both slots filled', () => {
  const { queryByTestId, rerender } = render(<ScanCameraScreen ... />);
  expect(queryByTestId('compare-cta')).toBeNull();
  // ... fill both slots
  rerender(<ScanCameraScreen ... />);
  expect(queryByTestId('compare-cta')).toBeTruthy();
});
```

**Step 2: Run, verify fails**

**Step 3: Implement camera + gallery + compare CTA**

Add to `ScanCameraScreen.tsx`:
- Camera permission check + `<CameraView ref={cameraRef} />` background
- Shutter button (`testID="shutter-button"`) → `cameraRef.takePictureAsync()` → fills next empty slot
- Gallery button (`testID="gallery-button"`) → `ImagePicker.launchImageLibraryAsync({mediaTypes: Images})` → fills next empty slot
- Flash button (`testID="flash-button"`) → cycles `'off' | 'on' | 'auto'`
- Compare CTA pill (`testID="compare-cta"`) → only renders when both slots non-null → navigates to Results with `vision_products: slots.map(s => s.uri)`

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/screens/ScanCameraScreen.tsx SmartCompareApp/src/screens/__tests__/ScanCameraScreen.test.tsx
git commit -m "feat(camera): camera capture + gallery picker + Compare CTA"
```

---

### Task 2.8: Frontend — SearchOverlay "you need TWO products" hint

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/components/SearchOverlay.tsx`
- Modify: `SmartCompareApp/src/components/__tests__/SearchOverlay.test.tsx`
- Modify: `SmartCompareApp/src/i18n/en.json` + `ar.json`

**Step 1: Add i18n keys**

`en.json`:
```json
"home.search.needTwoHint": "Enter TWO products to compare"
```
`ar.json`:
```json
"home.search.needTwoHint": "أدخل منتجَين للمقارنة"
```

**Step 2: Add failing test**

```tsx
it('shows hint until 2 distinct queries entered', () => {
  const { getByText, queryByText, getByPlaceholderText } = render(<SearchOverlay visible onClose={jest.fn()} />);
  expect(getByText('Enter TWO products to compare')).toBeTruthy();
  // simulate entering 2 queries
  // ...
  expect(queryByText('Enter TWO products to compare')).toBeNull();
});
```

**Step 3: Run, verify fails**

**Step 4: Add hint to SearchOverlay**

Display the hint banner above the search input area when `queries.length < 2`. Dismiss when 2 distinct non-empty queries are present.

**Step 5: Run, verify passes; commit**
```bash
git add SmartCompareApp/src/components/SearchOverlay.tsx SmartCompareApp/src/components/__tests__/SearchOverlay.test.tsx SmartCompareApp/src/i18n/en.json SmartCompareApp/src/i18n/ar.json
git commit -m "feat(search): 'you need TWO products' hint in SearchOverlay"
```

---

### Task 2.9: Frontend — CategorySelector lucide glyphs

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/components/CategorySelector.tsx`
- Test: `SmartCompareApp/src/components/__tests__/CategorySelector.test.tsx`

**Step 1: Add failing test**

```tsx
it('renders lucide icons instead of emoji codepoints', () => {
  const { UNSAFE_root } = render(<CategorySelector value="electronics" onChange={jest.fn()} />);
  // Assert lucide-react-native icons rendered (check by displayName or testID)
  const tree = UNSAFE_root.findAll((n: any) => n.type?.displayName?.includes('Smartphone'));
  expect(tree.length).toBeGreaterThan(0);
});

it('has no emoji codepoints in icon strings', () => {
  const src = require('../CategorySelector');
  const stringified = src.toString();
  expect(stringified).not.toMatch(/\\u\{1F[0-9A-F]{3}\}/); // no \u{1F...} emoji escapes
});
```

**Step 2: Run, verify fails**

**Step 3: Replace emoji icons with lucide imports**

```tsx
import {
  Smartphone, ShoppingCart, Pill, Lipstick,
  Sparkles, Scissors, Flower, ShoppingBag, Package,
} from 'lucide-react-native';

const CATEGORIES: Category[] = [
  { value: 'electronics', i18nKey: 'home.categories.electronics', Icon: Smartphone },
  { value: 'grocery', i18nKey: 'home.categories.grocery', Icon: ShoppingCart },
  { value: 'supplements', i18nKey: 'home.categories.supplements', Icon: Pill },
  { value: 'makeup', i18nKey: 'home.categories.makeup', Icon: Lipstick },
  { value: 'skincare', i18nKey: 'home.categories.skincare', Icon: Sparkles },
  { value: 'haircare', i18nKey: 'home.categories.haircare', Icon: Scissors },
  { value: 'fragrances', i18nKey: 'home.categories.fragrances', Icon: Flower },
  { value: 'fashion', i18nKey: 'home.categories.fashion', Icon: ShoppingBag },
  { value: 'other', i18nKey: 'home.categories.other', Icon: Package },
];
```

Render `<cat.Icon size={16} color={...} />` instead of `<Text>{cat.icon}</Text>`.

**Step 4: Run, verify passes; commit**
```bash
git add SmartCompareApp/src/components/CategorySelector.tsx SmartCompareApp/src/components/__tests__/CategorySelector.test.tsx
git commit -m "feat(ui): CategorySelector lucide glyphs replace emoji codepoints"
```

---

### Task 2.10: Frontend — QarenLogo SVG + header swaps

**Owner:** frontend-bcd

**Files:**
- Create: `SmartCompareApp/src/components/QarenLogo.tsx`
- Create: `SmartCompareApp/src/components/__tests__/QarenLogo.test.tsx`
- Modify: `SmartCompareApp/src/screens/HomeScreen.tsx`, `ProfileScreen.tsx`, `HistoryScreen.tsx`, `SplashScreen.tsx`

**Step 1: Write failing test for QarenLogo**

```tsx
import { render } from '@testing-library/react-native';
import QarenLogo from '../QarenLogo';

describe('QarenLogo', () => {
  it('renders SVG with brand mark', () => {
    const { UNSAFE_root } = render(<QarenLogo size={32} />);
    expect(UNSAFE_root.findByType('Svg' as any)).toBeTruthy();
  });
});
```

**Step 2: Run, verify fails**

**Step 3: Implement QarenLogo (placeholder — refine glyph with frontend-design skill if needed)**

```tsx
/**
 * Qaren brand glyph — Q with subtle accent.
 * Replaces the plain text "Qaren" header.
 */
import React from 'react';
import Svg, { Circle, Path, G } from 'react-native-svg';
import { colors } from '../theme';

type Props = { size?: number; color?: string };

export default function QarenLogo({ size = 32, color = colors.text.primary }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <G>
        <Circle cx="16" cy="16" r="13" stroke={color} strokeWidth="2.5" fill="none" />
        <Path d="M22 22 L27 27" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
        {/* Subtle accent dot — emerald per Bundle A signal-color rules */}
        <Circle cx="22" cy="11" r="2" fill={colors.accent} />
      </G>
    </Svg>
  );
}
```

**Step 4: Swap header in 4 screens**

In each of HomeScreen, ProfileScreen, HistoryScreen, SplashScreen:
- Find `<Text style={styles.logo}>{t('app.name')}</Text>` (or equivalent)
- Replace with `<View style={{flexDirection: 'row', alignItems: 'center', gap: 8}}><QarenLogo size={28} /><Text style={styles.logo}>{t('app.name')}</Text></View>`
- (Both glyph + wordmark for clarity at pre-launch; glyph-only later)

**Step 5: Run tests + commit**
```bash
git add SmartCompareApp/src/components/QarenLogo.tsx SmartCompareApp/src/components/__tests__/QarenLogo.test.tsx \
        SmartCompareApp/src/screens/HomeScreen.tsx SmartCompareApp/src/screens/ProfileScreen.tsx \
        SmartCompareApp/src/screens/HistoryScreen.tsx SmartCompareApp/src/screens/SplashScreen.tsx
git commit -m "feat(brand): QarenLogo SVG glyph + header swaps in 4 screens"
```

---

### Task 2.11: Frontend — Play Install Referrer init in App.tsx

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/App.tsx`
- Test: `SmartCompareApp/src/__tests__/App.referral.test.tsx`

**Step 1: Write failing test**

```tsx
it('calls tryReadPlayInstallReferrer on mount (Android only)', () => {
  const mockTryRead = jest.fn().mockResolvedValue('QR-ATAUX9');
  jest.mock('../src/services/playInstallReferrerService', () => ({ tryReadPlayInstallReferrer: mockTryRead }));
  render(<App />);
  expect(mockTryRead).toHaveBeenCalled();
});
```

**Step 2: Run, verify fails**

**Step 3: Wire init in App.tsx**

```tsx
import { tryReadPlayInstallReferrer } from './src/services/playInstallReferrerService';
import { setDeferredInviteCode } from './src/services/deferredInviteCode';

useEffect(() => {
  (async () => {
    const code = await tryReadPlayInstallReferrer();
    if (code) setDeferredInviteCode(code);
  })();
}, []);
```

Also create `SmartCompareApp/src/services/deferredInviteCode.ts`:
```ts
let _code: string | null = null;
export function setDeferredInviteCode(code: string) { _code = code; }
export function consumeDeferredInviteCode(): string | null {
  const c = _code; _code = null; return c;
}
```

**Step 4: Run, verify passes; commit**

---

### Task 2.12: Frontend — RegisterScreen consumes deferred code + clipboard fallback

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/screens/RegisterScreen.tsx`
- Modify: `SmartCompareApp/src/screens/__tests__/RegisterScreen.test.tsx`

**Step 1: Add failing tests**

```tsx
it('pre-fills invite code from deferred Play Install Referrer on mount', async () => {
  jest.mock('../../services/deferredInviteCode', () => ({ consumeDeferredInviteCode: () => 'QR-ATAUX9' }));
  const { getByDisplayValue } = render(<RegisterScreen ... />);
  expect(getByDisplayValue('QR-ATAUX9')).toBeTruthy();
});

it('shows clipboard consent prompt when clipboard contains valid code', async () => {
  jest.mock('../../services/clipboardFallbackService', () => ({ tryReadClipboardForInviteCode: jest.fn().mockResolvedValue('QR-BBBBBB') }));
  const { findByText } = render(<RegisterScreen ... />);
  expect(await findByText(/saw an invite code/i)).toBeTruthy();
});
```

**Step 2: Run, verify fails**

**Step 3: Implement consume + clipboard fallback**

In `RegisterScreen` mount effect:
```tsx
useEffect(() => {
  // Priority 1: deferred from Play Install Referrer (Android)
  const deferred = consumeDeferredInviteCode();
  if (deferred) { setInviteCode(deferred); setInviteCodeLocked(true); return; }
  // Priority 2: iOS clipboard fallback
  (async () => {
    const fromClipboard = await tryReadClipboardForInviteCode();
    if (fromClipboard) setClipboardPrompt(fromClipboard);
  })();
}, []);

// In render:
{clipboardPrompt && (
  <ConsentBanner
    title={t('register.clipboardConsent.title')}
    message={t('register.clipboardConsent.message', { code: clipboardPrompt })}
    onAccept={() => { setInviteCode(clipboardPrompt!); setClipboardPrompt(null); }}
    onReject={() => setClipboardPrompt(null)}
  />
)}
```

Add i18n keys:
- `register.clipboardConsent.title`: EN "Invite code on clipboard" / AR "رمز دعوة على الحافظة"
- `register.clipboardConsent.message`: EN "We saw an invite code ({{code}}) on your clipboard. Use it?" / AR equivalent

**Step 4: Run, verify passes**

**Step 5: Commit**
```bash
git add SmartCompareApp/src/screens/RegisterScreen.tsx SmartCompareApp/src/screens/__tests__/RegisterScreen.test.tsx SmartCompareApp/src/i18n/en.json SmartCompareApp/src/i18n/ar.json
git commit -m "feat(register): consume deferred PIR code + iOS clipboard fallback with consent"
```

---

### Task 2.13: Frontend — ReferralStatusCard lifetime counter UI

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/components/ReferralStatusCard.tsx`
- Modify: `SmartCompareApp/src/services/referralService.ts` (status type)
- Test: `SmartCompareApp/src/components/__tests__/ReferralStatusCard.test.tsx`

**Step 1: Add failing test**

```tsx
it('renders lifetime counter X of 3', () => {
  const { getByText } = render(<ReferralStatusCard status={{ lifetime_invites_used: 1, lifetime_invites_remaining: 2, ... }} />);
  expect(getByText(/1 of 3/)).toBeTruthy();
});

it('renders gifted-thanks message when 3 of 3 used', () => {
  const { getByText } = render(<ReferralStatusCard status={{ lifetime_invites_used: 3, lifetime_invites_remaining: 0, ... }} />);
  expect(getByText(/gifted/i)).toBeTruthy();
});
```

**Step 2: Update status type + render**

```ts
// referralService.ts
export type ReferralStatus = {
  referral_code: string;
  lifetime_invites_used: number;
  lifetime_invites_remaining: number;
  monthly_bonus_comparisons: number;
  deep_review_credits_available: number;
  total_lifetime_redemptions: number;
};
```

ReferralStatusCard:
- Display `{used} of 3 lifetime invites used`
- Display gift-thanks copy when `remaining === 0`

Add i18n: `referrals.status.lifetime` (`"{{used}} of 3 lifetime invites used"`), `referrals.status.gifted` (`"Thanks for gifting Qaren to 3 friends 🎁"`).

**Step 3: Run, verify passes**

**Step 4: Commit**

---

### Task 2.14: Frontend — ShareBottomSheet disabled at 3 lifetime

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/components/ShareBottomSheet.tsx`
- Test: existing test file

**Step 1: Add failing test**

```tsx
it('disables Share CTA when lifetime_invites_remaining === 0', () => {
  const { getByTestId } = render(<ShareBottomSheet ... lifetimeRemaining={0} />);
  expect(getByTestId('share-cta').props.disabled).toBe(true);
});

it('still enables Copy button when limit reached', () => {
  const { getByTestId } = render(<ShareBottomSheet ... lifetimeRemaining={0} />);
  expect(getByTestId('copy-cta').props.disabled).toBeFalsy();
});
```

**Step 2: Implement**

Pass `lifetimeRemaining` prop; if `=== 0`, disable Share button + show microcopy `t('referrals.share.maxReached')`.

**Step 3: Run, verify passes; commit**

---

### Task 2.15: Frontend — BonusCountdownCard 7-day copy

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/components/BonusCountdownCard.tsx`
- Modify i18n EN+AR for any "3 days" hardcoded text

**Step 1: Update copy to use day-count interpolation**

Find hardcoded "3 days" or `expires in 3` strings → replace with i18n key using `{{count}}`.

`en.json`:
```json
"referrals.bonus.expiresIn_one": "Expires in {{count}} day",
"referrals.bonus.expiresIn_other": "Expires in {{count}} days"
```
AR with proper plural forms.

**Step 2: Test rendering at day-7 issue, day-6 (24h before), day-0 expired**

**Step 3: Commit**

---

## Phase 3 — Polish (after Phase 2, sequential within frontend)

### Task 3.1: Frontend — animation polish on mode chips

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/screens/HomeScreen.tsx` (mode chip area)

**Step 1: Add spring animation to mode chip selection**

Use `withSpring` from Reanimated with `motion.springConfig.chip` from theme.

**Step 2: Add haptic.light on chip tap**

**Step 3: Test smoke**

**Step 4: Commit**

---

### Task 3.2: Frontend — animation polish on capture button

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/screens/ScanCameraScreen.tsx`

**Step 1: Press scale-down feedback**

Pressable wrapper around shutter with `withTiming(0.95, ...)` on press in.

**Step 2: Haptic.light on press**

**Step 3: Test + commit**

---

### Task 3.3: Frontend — animation polish on winner reveal

**Owner:** frontend-bcd

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

**Step 1: Subtle scale-in on winner card reveal**

`withSpring` scale 0.96 → 1.0 with `motion.springConfig.progress`.

**Step 2: haptic.medium fires once on reveal**

**Step 3: Test + commit**

---

### Task 3.4: Cloudflare Worker — web fallback page

**Owner:** frontend-bcd (deploys via wrangler) — Ahmed has Cloudflare account access

**Files:**
- Create: `cloudflare-workers/qaren-redirect/wrangler.toml`
- Create: `cloudflare-workers/qaren-redirect/src/index.ts`

**Step 1: Write Worker**

```ts
/**
 * qaren.app/r/{code} → redirects to store with referrer param.
 * Android: Play Store with ?referrer=QR-XXXXXX (Play Install Referrer survives install)
 * iOS: copies code to clipboard via inline JS, then App Store redirect
 */
export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const match = url.pathname.match(/^\/r\/(QR-[A-Z0-9]{6})$/);
    if (!match) return new Response('Not Found', { status: 404 });
    const code = match[1];
    const ua = request.headers.get('user-agent') || '';
    const isAndroid = /Android/i.test(ua);
    const isIos = /iPhone|iPad|iPod/i.test(ua);

    if (isAndroid) {
      const playUrl = `https://play.google.com/store/apps/details?id=com.kersher2.qaren&referrer=${encodeURIComponent('referrer=' + code)}`;
      return Response.redirect(playUrl, 302);
    }

    if (isIos) {
      // Inline JS copies code to clipboard, then redirects
      const html = `
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Opening Qaren…</title></head>
<body><script>
  (async () => {
    try { await navigator.clipboard.writeText('${code}'); } catch(e) {}
    location.href = 'https://apps.apple.com/app/qaren/idTBD';
  })();
</script>
<p>Code copied — open Qaren after install.</p></body></html>`;
      return new Response(html, { headers: { 'Content-Type': 'text/html;charset=utf-8' } });
    }

    return new Response(`<p>Open this link on your phone. Code: ${code}</p>`, { headers: { 'Content-Type': 'text/html' } });
  },
};
```

**Step 2: wrangler.toml**

```toml
name = "qaren-redirect"
main = "src/index.ts"
compatibility_date = "2026-05-12"

routes = [
  { pattern = "qaren.app/r/*", custom_domain = true }
]
```

**Step 3: Deploy**

```bash
cd cloudflare-workers/qaren-redirect
npm install -g wrangler  # one-time
wrangler login  # interactive, Ahmed runs
wrangler deploy
```

**Step 4: Smoke test**

```bash
curl -A "Mozilla/5.0 (Linux; Android 13)" -I https://qaren.app/r/QR-ABCDEF
# Expected: 302 redirect to Play Store URL with referrer parameter
```

**Step 5: Commit**
```bash
git add cloudflare-workers/
git commit -m "feat(infra): Cloudflare Worker for qaren.app/r/{code} install-survival redirect"
```

---

### Task 3.5: Perf audit + obvious-win fixes

**Owner:** frontend-bcd

**Files:**
- Create: `docs/runbooks/bundle-bcd-perf-audit.md`
- Possibly modify: any files where obvious wins surface

**Step 1: Run bundle visualizer**

```bash
cd SmartCompareApp
npx expo export --platform android --output-dir ./dist-android
npx source-map-explorer dist-android/_expo/static/js/android/*.js
# Identify >50 KB modules; document in report
```

**Step 2: Run Reanimated worklet inventory**

```bash
grep -rn "useSharedValue\|withSpring\|withTiming\|useAnimatedStyle" SmartCompareApp/src/ | wc -l
# Catalog all worklets; flag any not using useNativeDriver-compatible patterns
```

**Step 3: SVG audit — CohortBarChart**

```bash
grep -c "<Circle\|<Rect\|<Path" SmartCompareApp/src/components/illustrations/CohortBarChart.tsx
# Verify or correct the "388 dots" claim
```

**Step 4: Write report**

```markdown
# Bundle B/C/D Perf Audit
**Date:** 2026-05-12
## Bundle size
- Total: X MB
- Largest modules: ...
- Obvious wins: ...

## Reanimated
- Worklet count: X
- Issues found: ...

## SVG
- CohortBarChart primitives: X (vs. doc claim of 388)
- Action: ...
```

**Step 5: Apply ONLY obvious wins** (>50 KB savings OR confirmed dropped frames); commit each fix as separate commit.

---

## Phase 4 — Exit gate (sequential)

### Task 4.1: Full test suite

**Owner:** test-bcd

**Step 1: Run frontend suite**
```bash
cd SmartCompareApp
npx tsc --noEmit                   # Must exit 0
npx jest --coverage                 # All pass; ≥80% on new files
npm run lint                        # ESLint i18next/no-literal-string passes
```

**Step 2: Run backend suite**
```bash
python -m pytest tests/ -v --timeout=180
pip-audit -r requirements.txt --strict
```

**Step 3: Generate coverage report**

Save `docs/runbooks/bundle-bcd-coverage.md` with per-file coverage; fail merge if any new file < 80%.

---

### Task 4.2: Cross-QA pairings sign-off

**Owner:** all 4 agents

Each agent runs through their assigned reviews per design Section 2 cross-QA matrix. Open `REWORK:` tasks for any subpar/missed work.

---

### Task 4.3: QA report

**Owner:** qa-bcd

**Files:**
- Create: `docs/plans/2026-05-12-bundle-bcd-qa-report.md`

Cover: each of 8 items DoD status, accessibility findings, i18n parity, integration test results, smoke-test script for Ahmed's dev build.

---

### Task 4.4: EAS dev build for Ahmed verification

**Owner:** Ahmed (interactive)

```bash
cd SmartCompareApp
eas build --profile development --platform android
# Wait for build (~25 min)
# Install resulting APK on phone
# Walk through qa-bcd's smoke script
```

---

### Task 4.5: PR open

**Owner:** qa-bcd

After Ahmed approves the smoke test:
```bash
git push origin feature/bundle-bcd
gh pr create --title "Bundle B/C/D consolidated — polish + referral hardening" \
             --body-file docs/plans/2026-05-12-bundle-bcd-qa-report.md
```

CLAUDE.md updates (Session 46) + MEMORY.md updates committed BEFORE the PR open.

---

## Agent assignment matrix (quick reference)

| Phase | backend-bcd | frontend-bcd | test-bcd | qa-bcd |
|---|---|---|---|---|
| 1 | 1.1, 1.2, 1.3 | 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10 | rolling RED tests | spec drift watch |
| 2 | 2.0, 2.1, 2.2, 2.3, 2.4, 2.5 | 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15 | rolling GREEN + RED | contract verification |
| 3 | (perf checks) | 3.1, 3.2, 3.3, 3.4, 3.5 | mutation + coverage push | accessibility sweep, E2E |
| 4 | suite pass | suite pass | 4.1 | 4.2 cross-QA, 4.3 report, 4.5 PR |

---

## Critical-path dependencies (high-impact)

```
1.1 Migration 023 → 1.2 attribution_service → 2.1 lifetime cap → 2.2 signup decrement → 2.4 share endpoint → 2.5 status endpoint
                                                                                       ↘ 2.13 ReferralStatusCard UI (frontend gates here)
                                                                                                                     ↘ 2.14 ShareBottomSheet disable

1.4 ScanCameraScreen skel + 1.5 ScannerReticle + 1.6 ImageSlotRow → 2.6 HomeScreen integration → 2.7 camera+gallery → 3.2 capture animation
                                                                                                                     ↘ 3.3 winner reveal anim (different screen)

1.9 playInstallReferrerService + 1.10 clipboardFallbackService → 2.11 App.tsx init → 2.12 RegisterScreen consume

(parallel) 2.8 SearchOverlay hint, 2.9 CategorySelector glyphs, 2.10 QarenLogo, 3.1 mode-chip anim — independent

3.4 Cloudflare Worker — independent

4.1 → 4.2 → 4.3 → 4.4 → 4.5 strictly sequential
```

---

## Verification checklist (final pre-PR)

- [ ] All 8 design items shipped per DoD in Section 5.1
- [ ] `npx tsc --noEmit` exits 0
- [ ] `npx jest --coverage` all green, every NEW file ≥80%
- [ ] `python -m pytest tests/ -v --timeout=180` all green
- [ ] `pip-audit -r requirements.txt --strict` no HIGH/CRIT CVEs
- [ ] `npm run lint` passes ESLint i18next/no-literal-string
- [ ] EN/AR i18n parity preserved (`514 = 514` or new key count matches)
- [ ] Migration 023 applied + rollback file saved
- [ ] Cloudflare Worker deployed + responds 302 with referrer param on Android UA
- [ ] EAS dev build smoke test passed by Ahmed on Android device
- [ ] Cross-QA matrix all 6 pairings signed off
- [ ] `docs/plans/2026-05-12-bundle-bcd-qa-report.md` written
- [ ] CLAUDE.md updated with Session 46
- [ ] MEMORY.md updated with Bundle B/C/D learnings
- [ ] `git push origin feature/bundle-bcd` BEFORE branch deletion (CLAUDE.md rule)
