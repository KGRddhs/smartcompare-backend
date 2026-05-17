/**
 * Tests for `TwoInputShell` — shared two-input shell for Text + Link modes.
 * Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 3, § 4, § 8.
 * Plan ref: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.4.
 *
 * Coverage target: 80% on `SmartCompareApp/src/components/TwoInputShell.tsx`.
 *
 * THIS FILE LANDS IN PHASES:
 *   Phase 1 (NOW): negative-assertion shake test + import-contract red stubs.
 *     - Shake test fires CI-loudly the moment a Frontend commit accidentally
 *       introduces `shake|wobble|jitter|tremor` anywhere in the component
 *       source. Lands BEFORE the component exists (initially passes — the
 *       file is absent, the negative assertion holds vacuously) then stays
 *       passing as long as Frontend stays disciplined. Plan critical-path #4.
 *     - Import-contract tests fail with require/module errors until Frontend
 *       Opus commits the `TwoInputShell.tsx` skeleton with stable props.
 *   Phase 3 (LATER): the 50+ behavioral test cases (render, focus, paste,
 *     celebration, validation, analytics, RTL) — written once Frontend wires
 *     the skeleton + props contract is stable.
 */

import * as fs from 'fs';
import * as path from 'path';

const COMPONENT_PATH = path.resolve(
  __dirname,
  '..',
  'TwoInputShell.tsx',
);

const PAYWALL_PATH = path.resolve(
  __dirname,
  '..',
  'PaywallBanner.tsx',
);

const HOMESCREEN_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'screens',
  'HomeScreen.tsx',
);

const SCANCAMERA_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'screens',
  'ScanCameraScreen.tsx',
);

function readIfExists(p: string): string {
  // Returns empty string if the file isn't on disk yet — keeps the negative
  // assertion vacuously true BEFORE the component lands, and CI-loud the
  // moment a forbidden token is introduced after.
  try {
    return fs.readFileSync(p, 'utf-8');
  } catch {
    return '';
  }
}

// Patterns that frame the app as "scary" or signal punishment — Build
// Principle #4 forbids these animations across the Compare entry surfaces.
// Plan § 3.4 + spec § 4.3 + § 5.3 (6th item).
const SHAKE_WORDS = /\b(shake|wobble|jitter|tremor)\b/i;

// Detect a Reanimated `withSequence([...negative offset, +N, -N, ...])`
// shake-shape — belt-and-suspenders, in case someone introduces a shake
// without naming it.
//
// We look for `translateX:` (or `translateY:`) followed within a few hundred
// chars by what looks like an alternating-sign sequence of small numbers.
const TRANSLATE_BOUNCE_SHAPE = /translateX[^\n]{0,400}-\d+[^\n]{0,40},\s*\d+[^\n]{0,40},\s*-\d+/;
const SCALE_BOUNCE_SHAPE = /scale[^\n]{0,200}1\s*,\s*1\.\d+\s*,\s*0\.\d+\s*,\s*1\.\d+/;

describe('TwoInputShell — negative assertion (Phase 1 critical-path)', () => {
  describe('no shake / wobble / jitter / tremor animations anywhere', () => {
    it('TwoInputShell.tsx must not contain shake-style keywords', () => {
      const src = readIfExists(COMPONENT_PATH);
      expect(src).not.toMatch(SHAKE_WORDS);
    });

    it('TwoInputShell.tsx must not contain an alternating-sign translateX bounce', () => {
      const src = readIfExists(COMPONENT_PATH);
      expect(src).not.toMatch(TRANSLATE_BOUNCE_SHAPE);
    });

    it('TwoInputShell.tsx must not contain a scale bounce above 1.0 then below 1.0', () => {
      const src = readIfExists(COMPONENT_PATH);
      expect(src).not.toMatch(SCALE_BOUNCE_SHAPE);
    });

    it('PaywallBanner.tsx must not contain shake-style keywords', () => {
      const src = readIfExists(PAYWALL_PATH);
      expect(src).not.toMatch(SHAKE_WORDS);
    });

    it('HomeScreen.tsx must not contain shake-style keywords in any compare-entry block', () => {
      const src = readIfExists(HOMESCREEN_PATH);
      // HomeScreen historically has no shake; pin so Bundle B rewire stays
      // disciplined.
      expect(src).not.toMatch(SHAKE_WORDS);
    });

    it('ScanCameraScreen.tsx must not contain shake-style keywords in the celebration block', () => {
      const src = readIfExists(SCANCAMERA_PATH);
      expect(src).not.toMatch(SHAKE_WORDS);
    });
  });
});

describe('TwoInputShell — Phase 3 behavioral tests (RED until Frontend skeleton lands)', () => {
  // These tests fail-red with a module-not-found error until Frontend Opus
  // commits the TwoInputShell.tsx skeleton. After skeleton + props contract
  // are stable, the Test agent fills in the behavioral assertions per plan
  // § 3.4 (render, focus, paste-detection, celebration, validation, analytics,
  // RTL, ⊗ clear button, per-mode state preservation). 50+ assertions land
  // in Phase 3.

  it('imports the TwoInputShell module without throwing (skeleton must exist)', () => {
    // Use require so a missing module fails the test (instead of failing
    // the whole file at parse time). This keeps the negative-assertion
    // suite green even while the skeleton is in flight.
    expect(() => {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      require('../TwoInputShell');
    }).not.toThrow();
  });

  it.todo('renders text-mode placeholders in English locale (Phase 3)');
  it.todo('renders url-mode placeholders in English locale (Phase 3)');
  it.todo('renders Arabic placeholders + RTL numeral positions in AR locale (Phase 3)');
  it.todo('renders the Compare CTA disabled initially (Phase 3)');
  it.todo('renders the Compare CTA enabled when both boxes are blur-valid (Phase 3)');

  it.todo('auto-focuses Box A 250ms after mount (Phase 3)');
  it.todo('Box A returnKeyType is "next" (Phase 3)');
  it.todo('Box B returnKeyType is "search" in text mode (Phase 3)');
  it.todo('Box B returnKeyType is "go" in url mode (Phase 3)');
  it.todo('Box A onSubmitEditing focuses Box B (Phase 3)');
  it.todo('Box B onSubmitEditing fires onSubmit when both blur-valid (Phase 3)');
  it.todo('Box B onSubmitEditing dismisses keyboard when invalid (Phase 3)');
  it.todo('tap outside dismisses the keyboard (Phase 3)');

  it.todo('text-mode valid input fills the numeral circle on blur (Phase 3)');
  it.todo('text-mode invalid input keeps the numeral outlined on blur (no red, no error copy) (Phase 3)');
  it.todo('text-mode strips control characters silently before predicate (Phase 3)');
  it.todo('text-mode input over 80 chars is invalid (Phase 3)');
  it.todo('text-mode input at the 80-char boundary is valid (Phase 3)');
  it.todo('text-mode input at the 2-char boundary is valid (Phase 3)');
  it.todo('url-mode valid https URL fills the numeral on blur (Phase 3)');
  it.todo('url-mode invalid input keeps numeral outlined, no error toast (Phase 3)');
  it.todo('url-mode accepts http://localhost client-side (backend SSRF rejects) (Phase 3)');
  it.todo('url-mode input over 2048 chars is invalid (Phase 3)');
  it.todo('no per-keystroke revalidation flicker — numeral only flips on blur (Phase 3)');

  it.todo('pasting "X vs Y" into Box A splits into both boxes when Box B empty (Phase 3)');
  it.todo('pasting into Box B splits into both boxes when Box A empty (Phase 3)');
  it.todo('pasting AR " أو " separator splits correctly (Phase 3)');
  it.todo('pasting AR " مقابل " separator splits correctly (Phase 3)');
  it.todo('pasting comma separator splits correctly (Phase 3)');
  it.todo('pasting ampersand separator splits correctly (Phase 3)');
  it.todo('pasting "and" separator splits correctly (Phase 3)');
  it.todo('pasting "or" separator splits correctly (Phase 3)');
  it.todo('does NOT split if Box B already filled — raw paste into Box A (Phase 3)');
  it.todo('does NOT split if both halves under 2 chars — raw paste into Box A (Phase 3)');
  it.todo('cursor lands at end of Box B after split (Phase 3)');
  it.todo('paste-split caption disappears after 2.5s (Phase 3)');

  it.todo('pasting a URL into text-mode Box A triggers mode auto-switch to url (Phase 3)');
  it.todo('does NOT switch mode when Link-mode boxes already filled (Phase 3)');
  it.todo('does NOT re-switch when already in url-mode (Phase 3)');
  it.todo('mode-switch caption disappears after 2.5s (Phase 3)');

  it.todo('celebration fires when both boxes blur-valid (Phase 3)');
  it.todo('celebration haptic intensity is Success (NOT Warning/Error) (Phase 3)');
  it.todo('reverse un-fill does NOT re-fire haptic (Phase 3)');
  it.todo('celebration haptic wrapped in try/catch — failure does not crash render (Phase 3)');
  it.todo('celebration does NOT fire on initial mount with pre-valid boxes (Phase 3)');

  it.todo('⊗ clear button visible when Box A focused + filled (Phase 3)');
  it.todo('⊗ clear button hidden when Box A empty (Phase 3)');
  it.todo('⊗ clear button hidden when Box A unfocused (Phase 3)');
  it.todo('⊗ clear button empties the box but preserves focus (Phase 3)');

  it.todo('text-mode inputs preserved across mode switch and back (Phase 3)');
  it.todo('url-mode inputs preserved across mode switch and back (Phase 3)');
  it.todo('per-mode focus memory — no re-auto-focus on return to first mode (Phase 3)');

  it.todo('analytics: compare_entry_view fires on mount (Phase 3)');
  it.todo('analytics: compare_entry_view fires once per mode entry (Phase 3)');
  it.todo('analytics: compare_entry_paste_split fires with source_box payload (Phase 3)');
  it.todo('analytics: compare_entry_mode_autoswitch fires with from/to/trigger payload (Phase 3)');
  it.todo('analytics: compare_entry_ready fires on celebration with time_to_ready_ms (Phase 3)');
  it.todo('analytics: compare_entry_ready fires once per celebration (no double-fire on reverse) (Phase 3)');
  it.todo('analytics: compare_entry_submit fires with used_paste_split=true after paste-split happy path (Phase 3)');
  it.todo('analytics: compare_entry_submit fires with used_autoswitch=true after mode-switch path (Phase 3)');
  it.todo('analytics: compare_entry_submit fires with both booleans false on clean type-and-submit (Phase 3)');
  it.todo('analytics privacy: no user-typed text appears in any payload (Phase 3)');
  it.todo('analytics: all payload keys are in the allowlist (mode/source_box/from/to/trigger/time_to_ready_ms/used_paste_split/used_autoswitch) (Phase 3)');
});
