/**
 * W3-11bcd — MB-I18N-RTL-14(d): the loading shimmer sweeps with the reading
 * direction.
 *
 * Measured at base b63a8368 (probe w311.shimmer.probe.test.tsx): the
 * `GhostField` sweep starts at `-SHIMMER_TRANSLATE_PX` (-60) and travels to
 * +60 regardless of `I18nManager.isRTL` (LoadingScreenVariants.tsx:529/:534)
 * — left → right under a mirrored Arabic layout.
 *
 * Mechanics: __mocks__/react-native.ts exports a MUTABLE `I18nManager`, and
 * the reanimated mock evaluates `useAnimatedStyle` once at render, so the
 * shimmer's rendered `translateX` IS the sweep's start value. The module is
 * imported while `isRTL === false`, so a fix that reads `isRTL` at module
 * scope instead of inside `GhostField` at render time stays -60 under RTL and
 * fails the second test.
 *
 * The start value alone is half the contract: the sweep's END is the
 * `withTiming` target set in GhostField's effect, which the rendered style
 * never shows (the mock evaluates useAnimatedStyle once, before the effect).
 * The second test spies on the reanimated mock's `withTiming` and pins the
 * target's sign, so dropping `* dir` from the target (Arabic sweep frozen at
 * +60 -> +60) reddens it.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string, opts?: any) => opts?.defaultValue ?? k }),
}));
jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en' }),
}));

import { LoadingScreenVariants } from '../src/screens/LoadingScreenVariants';

const RN = require('react-native');

function shimmerTranslateX(rendered: any): unknown[] {
  const node = rendered.getByTestId('loading-streaming-card-a-name-shimmer');
  const flat = ([] as any[]).concat(...[node.props.style].flat(Infinity)).filter(Boolean);
  return flat
    .map((s: any) => s?.transform)
    .filter(Boolean)
    .flat()
    .map((tr: any) => tr?.translateX)
    .filter((v: unknown) => v !== undefined);
}

beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  RN.I18nManager.isRTL = false;
  jest.useRealTimers();
});

describe('W3-11 RTL-14(d) — GhostField shimmer direction', () => {
  it('starts at -60 under LTR and at +60 under RTL (isRTL read at render time)', () => {
    // One test on purpose: the LTR half alone is today's behaviour; the
    // pair is the contract (the sign follows the direction).
    RN.I18nManager.isRTL = false;
    const ltr = render(<LoadingScreenVariants variant="streaming" mode="comparison" />);
    const ltrTx = shimmerTranslateX(ltr);
    ltr.unmount();

    RN.I18nManager.isRTL = true;
    const rtl = render(<LoadingScreenVariants variant="streaming" mode="comparison" />);
    const rtlTx = shimmerTranslateX(rtl);
    rtl.unmount();

    expect({ ltr: ltrTx, rtl: rtlTx }).toEqual({ ltr: [-60], rtl: [60] });
  });

  it('sweeps TO +60 under LTR and TO -60 under RTL (the withTiming target follows the direction)', () => {
    const reanimated = require('react-native-reanimated');
    const timing = jest.spyOn(reanimated, 'withTiming');

    const targetsFor = (isRTL: boolean): number[] => {
      timing.mockClear();
      RN.I18nManager.isRTL = isRTL;
      const r = render(<LoadingScreenVariants variant="streaming" mode="comparison" />);
      // GhostField's effect has run inside render's act(); collect the
      // shimmer sweep targets (the only 60-magnitude withTiming callers).
      const targets = timing.mock.calls
        .map((c: unknown[]) => c[0] as number)
        .filter((v) => Math.abs(v) === 60);
      r.unmount();
      return targets;
    };

    const ltr = targetsFor(false);
    const rtl = targetsFor(true);
    timing.mockRestore();

    expect(ltr.length).toBeGreaterThan(0);
    expect(rtl.length).toBe(ltr.length);
    expect({ ltr: [...new Set(ltr)], rtl: [...new Set(rtl)] }).toEqual({ ltr: [60], rtl: [-60] });
  });
});
