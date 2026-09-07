/**
 * A5 — the splash brand moment is a FLOOR, not a flat 1.5s toll.
 *
 * Before this fix SplashScreen armed `setTimeout(onFinish, 1500)` at mount
 * unconditionally. That clock starts AFTER process launch + bundle parse +
 * RN root mount, so the 1.5s stacked on native startup even when fonts and
 * the auth check were already settled — which, since A3's cached-session
 * boot, is the common case.
 *
 * The contract now has two branches and BOTH are pinned here:
 *   ready  — release at MIN (700ms), never the full 1.5s
 *   !ready — hold to the unchanged MAX (1500ms) cap
 * plus the crossing cases (readiness landing before vs. after MIN) and the
 * exactly-once guarantee.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, act } from '@testing-library/react-native';
import SplashScreen from '../src/screens/SplashScreen';

// react-native-reanimated is mapped to __mocks__/react-native-reanimated.ts via
// jest.config.js moduleNameMapper — see SplashScreen.test.tsx for why a bare
// jest.mock() factory-less call breaks the shared values.

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'app.name': 'Qaren',
        'splash.tagline': 'Compare smarter',
      };
      return translations[key] || key;
    },
  }),
}));

const MIN_SPLASH_MS = 700;
const MAX_SPLASH_MS = 1500;

describe('SplashScreen — elapsed-aware brand-moment floor (A5)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('releases at the 700ms minimum when the app is already ready at mount', () => {
    const onFinish = jest.fn();
    render(<SplashScreen onFinish={onFinish} ready />);

    act(() => {
      jest.advanceTimersByTime(MIN_SPLASH_MS - 1);
    });
    // The brand moment still gets its minimum — this is not "release instantly".
    expect(onFinish).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(1);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);
  });

  it('does not stack the old 1.5s toll on a ready boot', () => {
    const onFinish = jest.fn();
    render(<SplashScreen onFinish={onFinish} ready />);

    act(() => {
      jest.advanceTimersByTime(MIN_SPLASH_MS);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);

    // Running past the old constant must not produce a second release.
    act(() => {
      jest.advanceTimersByTime(MAX_SPLASH_MS);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);
  });

  it('readiness landing BEFORE the minimum still waits for the minimum', () => {
    const onFinish = jest.fn();
    const { rerender } = render(<SplashScreen onFinish={onFinish} ready={false} />);

    act(() => {
      jest.advanceTimersByTime(300);
    });
    rerender(<SplashScreen onFinish={onFinish} ready />);
    expect(onFinish).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(MIN_SPLASH_MS - 300 - 1);
    });
    expect(onFinish).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(1);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);
  });

  it('readiness landing AFTER the minimum releases immediately, not at the cap', () => {
    const onFinish = jest.fn();
    const { rerender } = render(<SplashScreen onFinish={onFinish} ready={false} />);

    act(() => {
      jest.advanceTimersByTime(1000);
    });
    expect(onFinish).not.toHaveBeenCalled();

    // No timer advance after this — the release must come from the state
    // change itself, not from waiting out the remaining 500ms to the cap.
    rerender(<SplashScreen onFinish={onFinish} ready />);
    expect(onFinish).toHaveBeenCalledTimes(1);
  });

  it('holds to the unchanged 1.5s cap while the app is not ready', () => {
    const onFinish = jest.fn();
    render(<SplashScreen onFinish={onFinish} ready={false} />);

    act(() => {
      jest.advanceTimersByTime(MAX_SPLASH_MS - 1);
    });
    expect(onFinish).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(1);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);
  });

  it('never releases twice when readiness lands after the cap already fired', () => {
    const onFinish = jest.fn();
    const { rerender } = render(<SplashScreen onFinish={onFinish} ready={false} />);

    act(() => {
      jest.advanceTimersByTime(MAX_SPLASH_MS);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);

    rerender(<SplashScreen onFinish={onFinish} ready />);
    act(() => {
      jest.advanceTimersByTime(MAX_SPLASH_MS);
    });
    expect(onFinish).toHaveBeenCalledTimes(1);
  });

  it('a changed onFinish identity does not restart the floor', () => {
    // The timers are armed once at mount; re-arming on every parent render
    // would let a busy boot push the release out indefinitely.
    const first = jest.fn();
    const second = jest.fn();
    const { rerender } = render(<SplashScreen onFinish={first} ready />);

    act(() => {
      jest.advanceTimersByTime(400);
    });
    rerender(<SplashScreen onFinish={second} ready />);

    act(() => {
      jest.advanceTimersByTime(300);
    });
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });
});

describe('App.tsx — splash readiness wiring (A5)', () => {
  const appSrc: string = fs.readFileSync(path.resolve(__dirname, '../App.tsx'), 'utf8');

  it('hands SplashScreen the real readiness signal', () => {
    // Without this prop the screen falls back to the legacy hold-to-cap
    // behaviour and the fix is inert in the app.
    expect(appSrc).toMatch(
      /<SplashScreen[\s\S]{0,160}ready=\{\s*fontsLoaded\s*&&\s*!isLoading\s*\}/,
    );
  });

  it('keeps the render gate itself unchanged', () => {
    expect(appSrc).toMatch(/if\s*\(!fontsLoaded\s*\|\|\s*isLoading\s*\|\|\s*showSplash\)/);
  });
});
