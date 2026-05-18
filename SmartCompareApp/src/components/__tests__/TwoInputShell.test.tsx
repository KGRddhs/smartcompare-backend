/**
 * Tests for `TwoInputShell` — shared two-input shell for Text + Link modes.
 *
 * Spec: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md
 *   § 3 (anatomy) · § 4 (interactions) · § 7 (RTL) · § 8 (analytics caller-fires)
 * Plan: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.4.
 *
 * Coverage target: 80% on `SmartCompareApp/src/components/TwoInputShell.tsx`.
 *
 * IMPORTANT — what this file does NOT test (per component-contract docstring
 * lines 151-158 of TwoInputShell.tsx):
 *   - Analytics events. The component fires CALLBACKS (`onPasteSplit`,
 *     `onModeAutoswitch`, `onReady`); the CALLER (HomeScreen) fires
 *     `trackEvent('compare_entry_*')`. Spec § 8 + TwoInputShell.tsx line ~150.
 *     Analytics tests live in HomeScreen tests, not here.
 *   - canCompare branching. HomeScreen renders PaywallBanner OR TwoInputShell
 *     in this slot — never both at once.
 *   - Mode-chip state on HomeScreen.
 *   - Min-display-floor 1.2s timing on Home→Results.
 *
 * What this file DOES test:
 *   - Phase 1 critical-path #4: negative-assertion shake test (kept green).
 *   - Render contract in both modes.
 *   - Validation timing — blur-only predicate, no keystroke flicker.
 *   - Paste-detection (auto-split + URL auto-mode-switch) with edge guards.
 *   - Celebration — onReady fires once + Success haptic.
 *   - Reverse direction — no haptic re-fire, no onReady re-fire.
 *   - ⊗ clear button — focus + value gating.
 *   - Per-mode state preservation across mode prop flips.
 */

import * as fs from 'fs';
import * as path from 'path';

import React from 'react';
import {
  act,
  fireEvent,
  render,
} from '@testing-library/react-native';

// Per-test language toggle. The react-i18next mock reads `_mockLang`.
let _mockLang = 'en';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: {
      language: _mockLang,
      changeLanguage: jest.fn(async (lang: string) => {
        _mockLang = lang;
      }),
    },
  }),
  initReactI18next: { type: '3rdParty', init: jest.fn() },
}));

// The global __mocks__/react-native.ts mock doesn't expose Keyboard. Add
// it here for the TwoInputShell submit/dismiss paths (spec § 4.4 — silent
// dismiss on invalid Box B submit, dismiss on tap-outside Pressable).
// Spread the global mock + extend.
jest.mock('react-native', () => {
  const actual = jest.requireActual('../../../__mocks__/react-native');
  return {
    ...actual,
    Keyboard: { dismiss: jest.fn() },
  };
});

import TwoInputShell, {
  __resetTwoInputCacheForTests,
} from '../TwoInputShell';
import * as Haptics from 'expo-haptics';
import { I18nManager } from 'react-native';

// ============================================
// File-source grep helpers — used by negative-assertion suite.
// ============================================

const COMPONENT_PATH = path.resolve(__dirname, '..', 'TwoInputShell.tsx');
const PAYWALL_PATH = path.resolve(__dirname, '..', 'PaywallBanner.tsx');
const HOMESCREEN_PATH = path.resolve(__dirname, '..', '..', 'screens', 'HomeScreen.tsx');
const SCANCAMERA_PATH = path.resolve(__dirname, '..', '..', 'screens', 'ScanCameraScreen.tsx');

function readIfExists(p: string): string {
  try {
    return fs.readFileSync(p, 'utf-8');
  } catch {
    return '';
  }
}

function stripBlockComments(src: string): string {
  // Drop /* … */ block comments so the negative grep doesn't trip on the
  // component's documentary comment that says "no shake". The component's
  // contract docstring explicitly calls this out.
  return src.replace(/\/\*[\s\S]*?\*\//g, '');
}

const SHAKE_WORDS = /\b(shake|wobble|jitter|tremor)\b/i;
const TRANSLATE_BOUNCE_SHAPE = /translateX[^\n]{0,400}-\d+[^\n]{0,40},\s*\d+[^\n]{0,40},\s*-\d+/;
const SCALE_BOUNCE_SHAPE = /scale[^\n]{0,200}1\s*,\s*1\.\d+\s*,\s*0\.\d+\s*,\s*1\.\d+/;

function buildCallbacks() {
  return {
    onSubmit: jest.fn(),
    onPasteSplit: jest.fn(),
    onModeAutoswitch: jest.fn(),
    onReady: jest.fn(),
  };
}

beforeEach(() => {
  __resetTwoInputCacheForTests();
  _mockLang = 'en';
  (I18nManager as any).isRTL = false;
  (Haptics.notificationAsync as jest.Mock).mockClear();
});

afterEach(() => {
  jest.useRealTimers();
});

// ============================================
// Phase 1 critical-path #4 — negative-assertion shake (kept green)
// ============================================

describe('TwoInputShell — negative-assertion shake (Phase 1 critical-path #4)', () => {
  it('TwoInputShell.tsx source (sans block comments) contains no shake-style keywords', () => {
    const src = stripBlockComments(readIfExists(COMPONENT_PATH));
    expect(src).not.toMatch(SHAKE_WORDS);
  });

  it('TwoInputShell.tsx contains no alternating-sign translateX bounce', () => {
    const src = stripBlockComments(readIfExists(COMPONENT_PATH));
    expect(src).not.toMatch(TRANSLATE_BOUNCE_SHAPE);
  });

  it('TwoInputShell.tsx contains no scale bounce above 1.0 then below 1.0', () => {
    const src = stripBlockComments(readIfExists(COMPONENT_PATH));
    expect(src).not.toMatch(SCALE_BOUNCE_SHAPE);
  });

  it('PaywallBanner.tsx contains no shake-style keywords', () => {
    const src = stripBlockComments(readIfExists(PAYWALL_PATH));
    expect(src).not.toMatch(SHAKE_WORDS);
  });

  it('HomeScreen.tsx contains no shake-style keywords in compare-entry blocks', () => {
    const src = stripBlockComments(readIfExists(HOMESCREEN_PATH));
    expect(src).not.toMatch(SHAKE_WORDS);
  });

  it('ScanCameraScreen.tsx contains no shake-style keywords in celebration block', () => {
    const src = stripBlockComments(readIfExists(SCANCAMERA_PATH));
    expect(src).not.toMatch(SHAKE_WORDS);
  });
});

// ============================================
// § 4 — render contract
// ============================================

describe('TwoInputShell — render contract', () => {
  it('renders text-mode placeholders + vs pill + CTA in English locale', () => {
    const cb = buildCallbacks();
    const { getByPlaceholderText, getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    expect(getByPlaceholderText('home.compare.box_a_text')).toBeTruthy();
    expect(getByPlaceholderText('home.compare.box_b_text')).toBeTruthy();
    expect(getByTestId('two-input-shell-vs-pill')).toBeTruthy();
    expect(getByTestId('two-input-shell-cta')).toBeTruthy();
  });

  it('renders url-mode placeholders', () => {
    const cb = buildCallbacks();
    const { getByPlaceholderText } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    expect(getByPlaceholderText('home.compare.box_a_url')).toBeTruthy();
    expect(getByPlaceholderText('home.compare.box_b_url')).toBeTruthy();
  });

  it('renders CTA disabled initially (both boxes empty)', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const cta = getByTestId('two-input-shell-cta');
    expect(cta.props.accessibilityState.disabled).toBe(true);
  });

  it('renders CTA enabled once both boxes are blur-valid', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15');
    fireEvent(a, 'blur');
    fireEvent.changeText(b, 'Galaxy S24');
    fireEvent(b, 'blur');
    expect(
      getByTestId('two-input-shell-cta').props.accessibilityState.disabled
    ).toBe(false);
  });
});

// ============================================
// § 4.2 — validation timing (blur-only)
// ============================================

describe('TwoInputShell — validation timing', () => {
  it('text-mode valid input flips numeral fill on blur (accessibility label set)', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'iPhone 15');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBe('home.compare.a11y_box_a_valid');
  });

  it('text-mode invalid input keeps numeral neutral on blur (no scary copy)', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByText } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'x');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
    expect(queryByText(/try again|couldn't|error|failed/i)).toBeNull();
  });

  it('text-mode 2-char input is the lower boundary — valid on blur', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'iP');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBe('home.compare.a11y_box_a_valid');
  });

  it('text-mode 80-char input is the upper boundary — valid on blur', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'X'.repeat(80));
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBe('home.compare.a11y_box_a_valid');
  });

  it('text-mode 81-char input exceeds upper boundary — neutral on blur', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'X'.repeat(81));
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
  });

  it('text-mode control character in trimmed value fails predicate', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'iPhone\u000015');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
  });

  it('url-mode valid https URL flips numeral fill on blur', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'https://amazon.ae/dp/B0XYZ12345');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBe('home.compare.a11y_box_a_valid');
  });

  it('url-mode invalid URL keeps numeral neutral, no error toast/banner', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByText } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'not a url');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
    expect(queryByText(/invalid|try again/i)).toBeNull();
  });

  it('url-mode accepts http://localhost client-side (backend SSRF rejects)', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'http://localhost:3000');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBe('home.compare.a11y_box_a_valid');
  });

  it('url-mode rejects ftp:// scheme', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'ftp://example.com/file');
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
  });

  it('no per-keystroke revalidation flicker — circle only flips on blur', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'x');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
    fireEvent.changeText(a, 'iP');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBeUndefined();
    fireEvent(a, 'blur');
    expect(
      getByTestId('two-input-shell-a-circle').props.accessibilityLabel
    ).toBe('home.compare.a11y_box_a_valid');
  });
});

// ============================================
// § 4.1.1 — paste-shape auto-split
// ============================================

describe('TwoInputShell — paste-shape auto-split', () => {
  it('pasting "X vs Y" into empty Box A populates both boxes + fires onPasteSplit("a")', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15 vs Galaxy S24');
    expect(a.props.value).toBe('iPhone 15');
    expect(b.props.value).toBe('Galaxy S24');
    expect(cb.onPasteSplit).toHaveBeenCalledWith('a');
  });

  it('pasting "X مقابل Y" (AR separator) splits correctly', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15 مقابل Galaxy S24');
    expect(a.props.value).toBe('iPhone 15');
    expect(b.props.value).toBe('Galaxy S24');
  });

  it('pasting "X, Y" comma-separator splits', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15, Galaxy S24');
    expect(a.props.value).toBe('iPhone 15');
    expect(b.props.value).toBe('Galaxy S24');
  });

  it('pasting into empty Box B fires onPasteSplit("b") with Box A empty', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(b, 'iPhone 15 vs Galaxy S24');
    expect(a.props.value).toBe('iPhone 15');
    expect(b.props.value).toBe('Galaxy S24');
    expect(cb.onPasteSplit).toHaveBeenCalledWith('b');
  });

  it('does NOT split when sibling already has content — raw paste falls through', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
        initialB="Pixel 8"
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15 vs Galaxy S24');
    expect(a.props.value).toBe('iPhone 15 vs Galaxy S24');
    expect(b.props.value).toBe('Pixel 8');
    expect(cb.onPasteSplit).not.toHaveBeenCalled();
  });

  it('does NOT fire onPasteSplit when short-half guard rejects ("x vs y")', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    // String length = 11 (jump >= 10), looksLikeTwoProducts = true,
    // splitComparisonShape -> ["x", "y    pad"] → left half 1 char →
    // returns null → falls through to raw paste, no onPasteSplit.
    fireEvent.changeText(a, 'x vs y     ');
    expect(cb.onPasteSplit).not.toHaveBeenCalled();
  });

  it('shows the paste_split caption after a successful split and auto-hides at 2.5s', () => {
    jest.useFakeTimers();
    const cb = buildCallbacks();
    const { getByTestId, queryByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'iPhone 15 vs Galaxy S24');
    expect(queryByTestId('two-input-shell-caption-paste-split')).toBeTruthy();
    act(() => {
      jest.advanceTimersByTime(2600);
    });
    expect(queryByTestId('two-input-shell-caption-paste-split')).toBeNull();
  });
});

// ============================================
// § 4.1.2 — URL paste auto-mode-switch
// ============================================

describe('TwoInputShell — URL paste auto-mode-switch', () => {
  it('pasting a URL into text-mode Box A fires onModeAutoswitch("text","url")', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onModeAutoswitch={cb.onModeAutoswitch}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'https://amazon.ae/dp/B0XYZ12345');
    expect(cb.onModeAutoswitch).toHaveBeenCalledWith('text', 'url');
  });

  it('does NOT switch when URL-mode cache already has content (preserves link state)', () => {
    const cb = buildCallbacks();
    // First mount in URL mode + populate, then re-render in text mode.
    const { rerender, getByTestId } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    const aUrl = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(aUrl, 'https://existing.example.com/page');
    fireEvent(aUrl, 'blur');

    rerender(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onModeAutoswitch={cb.onModeAutoswitch}
      />
    );
    const aText = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(aText, 'https://new.example.com/page');
    expect(cb.onModeAutoswitch).not.toHaveBeenCalled();
    expect(aText.props.value).toBe('https://new.example.com/page');
  });

  it('does NOT switch when already in URL mode (no recursion)', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="url"
        onSubmit={cb.onSubmit}
        onModeAutoswitch={cb.onModeAutoswitch}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'https://amazon.ae/dp/B0XYZ12345');
    expect(cb.onModeAutoswitch).not.toHaveBeenCalled();
  });

  it('shows the mode_switch caption after a successful auto-switch', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onModeAutoswitch={cb.onModeAutoswitch}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'https://amazon.ae/dp/B0XYZ12345');
    expect(queryByTestId('two-input-shell-caption-mode-switch')).toBeTruthy();
  });
});

// ============================================
// § 4.3 — celebration on bothValid transition
// ============================================

describe('TwoInputShell — celebration on bothValid transition', () => {
  it('fires onReady ONCE + Success haptic when both boxes blur-valid', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} onReady={cb.onReady} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15');
    fireEvent(a, 'blur');
    expect(cb.onReady).not.toHaveBeenCalled();
    fireEvent.changeText(b, 'Galaxy S24');
    fireEvent(b, 'blur');
    expect(cb.onReady).toHaveBeenCalledTimes(1);
    expect(Haptics.notificationAsync).toHaveBeenCalledTimes(1);
    expect(Haptics.notificationAsync).toHaveBeenCalledWith(
      Haptics.NotificationFeedbackType.Success
    );
  });

  it('does NOT re-fire haptic or onReady on reverse transition (valid → invalid)', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} onReady={cb.onReady} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15');
    fireEvent(a, 'blur');
    fireEvent.changeText(b, 'Galaxy S24');
    fireEvent(b, 'blur');
    expect(cb.onReady).toHaveBeenCalledTimes(1);
    fireEvent.changeText(b, 'x');
    fireEvent(b, 'blur');
    expect(cb.onReady).toHaveBeenCalledTimes(1);
    expect(Haptics.notificationAsync).toHaveBeenCalledTimes(1);
  });

  it('survives haptic engine throwing synchronously (try/catch wrap)', () => {
    (Haptics.notificationAsync as jest.Mock).mockImplementationOnce(() => {
      throw new Error('haptic engine offline');
    });
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} onReady={cb.onReady} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    expect(() => {
      fireEvent.changeText(a, 'iPhone 15');
      fireEvent(a, 'blur');
      fireEvent.changeText(b, 'Galaxy S24');
      fireEvent(b, 'blur');
    }).not.toThrow();
    expect(cb.onReady).toHaveBeenCalledTimes(1);
  });

  it('survives haptic promise rejection (maybePromise.catch wrap)', () => {
    (Haptics.notificationAsync as jest.Mock).mockImplementationOnce(() =>
      Promise.reject(new Error('rejected'))
    );
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} onReady={cb.onReady} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    expect(() => {
      fireEvent.changeText(a, 'iPhone 15');
      fireEvent(a, 'blur');
      fireEvent.changeText(b, 'Galaxy S24');
      fireEvent(b, 'blur');
    }).not.toThrow();
    expect(cb.onReady).toHaveBeenCalledTimes(1);
  });
});

// ============================================
// § 4.4 — keyboard flow + submit
// ============================================

describe('TwoInputShell — keyboard flow + submit', () => {
  it('Box B submit-editing fires onSubmit when both valid', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15');
    fireEvent(a, 'blur');
    fireEvent.changeText(b, 'Galaxy S24');
    fireEvent(b, 'blur');
    fireEvent(b, 'submitEditing');
    expect(cb.onSubmit).toHaveBeenCalledWith('iPhone 15', 'Galaxy S24');
  });

  it('Box B submit-editing does NOT submit when invalid (silent dismiss, no error UX)', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByText } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(b, 'x');
    fireEvent(b, 'submitEditing');
    expect(cb.onSubmit).not.toHaveBeenCalled();
    expect(queryByText(/error|invalid|try again/i)).toBeNull();
  });

  it('CTA tap submits trimmed strings to onSubmit when both valid', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, '  iPhone 15  ');
    fireEvent(a, 'blur');
    fireEvent.changeText(b, '  Galaxy S24  ');
    fireEvent(b, 'blur');
    fireEvent.press(getByTestId('two-input-shell-cta'));
    expect(cb.onSubmit).toHaveBeenCalledWith('iPhone 15', 'Galaxy S24');
  });

  it('CTA tap does NOT submit when CTA is disabled', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    fireEvent.press(getByTestId('two-input-shell-cta'));
    expect(cb.onSubmit).not.toHaveBeenCalled();
  });

  it('disabled prop blocks the CTA even when initial values are valid', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        disabled
        initialA="iPhone 15"
        initialB="Galaxy S24"
      />
    );
    const cta = getByTestId('two-input-shell-cta');
    expect(cta.props.accessibilityState.disabled).toBe(true);
    fireEvent.press(cta);
    expect(cb.onSubmit).not.toHaveBeenCalled();
  });

  it('Box A returnKeyType is "next"', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    expect(
      getByTestId('two-input-shell-a-input').props.returnKeyType
    ).toBe('next');
  });

  it('Box B returnKeyType is "search" in text mode', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    expect(
      getByTestId('two-input-shell-b-input').props.returnKeyType
    ).toBe('search');
  });

  it('Box B returnKeyType is "go" in url mode', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    expect(
      getByTestId('two-input-shell-b-input').props.returnKeyType
    ).toBe('go');
  });

  it('inputs are editable={false} when disabled=true', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} disabled />
    );
    expect(getByTestId('two-input-shell-a-input').props.editable).toBe(false);
    expect(getByTestId('two-input-shell-b-input').props.editable).toBe(false);
  });
});

// ============================================
// § 3.2 — ⊗ clear button (focus + value gating)
// ============================================

describe('TwoInputShell — ⊗ clear button', () => {
  it('is hidden when box is empty (even when focused)', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent(a, 'focus');
    expect(queryByTestId('two-input-shell-a-clear')).toBeNull();
  });

  it('is hidden when box is filled but unfocused', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent.changeText(a, 'iPhone');
    fireEvent(a, 'blur');
    expect(queryByTestId('two-input-shell-a-clear')).toBeNull();
  });

  it('is visible when box is focused AND filled', () => {
    const cb = buildCallbacks();
    const { getByTestId, queryByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent(a, 'focus');
    fireEvent.changeText(a, 'iPhone');
    expect(queryByTestId('two-input-shell-a-clear')).toBeTruthy();
  });

  it('tapping clear empties the box (value goes back to "")', () => {
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    const a = getByTestId('two-input-shell-a-input');
    fireEvent(a, 'focus');
    fireEvent.changeText(a, 'iPhone');
    fireEvent.press(getByTestId('two-input-shell-a-clear'));
    expect(a.props.value).toBe('');
  });
});

// ============================================
// § 3.3 — per-mode state preservation across mode flips
// ============================================

describe('TwoInputShell — per-mode cache survives mode flip', () => {
  it('text inputs persist when mode flips text → url → text', () => {
    const cb = buildCallbacks();
    const { rerender, getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    fireEvent.changeText(getByTestId('two-input-shell-a-input'), 'iPhone 15');

    rerender(<TwoInputShell mode="url" onSubmit={cb.onSubmit} />);
    expect(getByTestId('two-input-shell-a-input').props.value).toBe('');

    rerender(<TwoInputShell mode="text" onSubmit={cb.onSubmit} />);
    expect(getByTestId('two-input-shell-a-input').props.value).toBe('iPhone 15');
  });

  it('url inputs persist when mode flips url → text → url', () => {
    const cb = buildCallbacks();
    const { rerender, getByTestId } = render(
      <TwoInputShell mode="url" onSubmit={cb.onSubmit} />
    );
    fireEvent.changeText(
      getByTestId('two-input-shell-a-input'),
      'https://amazon.ae/dp/B0XYZ12345'
    );

    rerender(<TwoInputShell mode="text" onSubmit={cb.onSubmit} />);
    expect(getByTestId('two-input-shell-a-input').props.value).toBe('');

    rerender(<TwoInputShell mode="url" onSubmit={cb.onSubmit} />);
    expect(getByTestId('two-input-shell-a-input').props.value).toBe(
      'https://amazon.ae/dp/B0XYZ12345'
    );
  });

  it('__resetTwoInputCacheForTests clears the module cache for the NEXT mount', () => {
    // The helper is mount-time only — existing components hold a ref to the
    // OLD cache object. Reset → next fresh mount sees a clean slate.
    const cb = buildCallbacks();
    const first = render(<TwoInputShell mode="text" onSubmit={cb.onSubmit} />);
    fireEvent.changeText(
      first.getByTestId('two-input-shell-a-input'),
      'iPhone 15'
    );
    first.unmount();

    __resetTwoInputCacheForTests();

    const second = render(<TwoInputShell mode="text" onSubmit={cb.onSubmit} />);
    expect(second.getByTestId('two-input-shell-a-input').props.value).toBe('');
  });

  it('initialA / initialB win over cache when provided', () => {
    const cb = buildCallbacks();
    const { rerender, getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    fireEvent.changeText(getByTestId('two-input-shell-a-input'), 'cached');

    rerender(
      <TwoInputShell
        mode="url"
        onSubmit={cb.onSubmit}
        initialA="https://injected.example.com"
      />
    );
    expect(getByTestId('two-input-shell-a-input').props.value).toBe(
      'https://injected.example.com'
    );
  });
});

// ============================================
// § 7.1 — RTL behavior smoke
// ============================================

describe('TwoInputShell — Arabic / RTL smoke', () => {
  it('renders without crashing in AR locale + isRTL=true', () => {
    _mockLang = 'ar';
    (I18nManager as any).isRTL = true;
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    expect(getByTestId('two-input-shell')).toBeTruthy();
    expect(getByTestId('two-input-shell-vs-pill')).toBeTruthy();
    expect(getByTestId('two-input-shell-a-circle')).toBeTruthy();
    expect(getByTestId('two-input-shell-b-circle')).toBeTruthy();
  });

  it('AR locale renders the same i18n keys (production AR JSON file provides translations)', () => {
    _mockLang = 'ar';
    (I18nManager as any).isRTL = true;
    const cb = buildCallbacks();
    const { getByPlaceholderText } = render(
      <TwoInputShell mode="text" onSubmit={cb.onSubmit} />
    );
    // The i18n mock returns the key verbatim; production AR JSON resolves
    // to "المنتج أ · مثال: آيفون 15". We assert the contract (key) not
    // the rendered string.
    expect(getByPlaceholderText('home.compare.box_a_text')).toBeTruthy();
  });

  it('AR + isRTL=true allows full happy-path: paste-split → celebration', () => {
    _mockLang = 'ar';
    (I18nManager as any).isRTL = true;
    const cb = buildCallbacks();
    const { getByTestId } = render(
      <TwoInputShell
        mode="text"
        onSubmit={cb.onSubmit}
        onPasteSplit={cb.onPasteSplit}
        onReady={cb.onReady}
      />
    );
    const a = getByTestId('two-input-shell-a-input');
    const b = getByTestId('two-input-shell-b-input');
    fireEvent.changeText(a, 'iPhone 15 أو Galaxy S24');
    expect(a.props.value).toBe('iPhone 15');
    expect(b.props.value).toBe('Galaxy S24');
    fireEvent(a, 'blur');
    fireEvent(b, 'blur');
    expect(cb.onReady).toHaveBeenCalledTimes(1);
  });
});
