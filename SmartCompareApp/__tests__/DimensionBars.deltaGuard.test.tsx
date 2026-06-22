// DimensionBars delta-guard tests — frag-content-quality WS-B Task B3.
//
// Defense-in-depth: a non-hero dimension whose delta_text leaked raw
// point-math ("+18pt longevity") must render the dim LABEL ("longevity"),
// never the raw "+18pt". A qualitative delta_text ("Longer-lasting") renders
// unchanged. Backend (WS-B) is canonical + already emits qualitative copy;
// this guard fails a future regression clean.

import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { DimensionBars } from '../src/components/results/DimensionBars';
import { POINT_MATH_RE, safeDelta } from '../src/components/results/_deltaText';

describe('_deltaText shared helper', () => {
  it('POINT_MATH_RE matches "+Npt" and spelled-out point forms, not qualitative copy', () => {
    expect(POINT_MATH_RE.test('+18pt longevity')).toBe(true);
    expect(POINT_MATH_RE.test('10.7-point higher')).toBe(true);
    expect(POINT_MATH_RE.test('4 points')).toBe(true);
    expect(POINT_MATH_RE.test('Longer-lasting')).toBe(false);
  });

  it('safeDelta falls back to the label on point-math, keeps qualitative copy', () => {
    expect(safeDelta('+18pt longevity', 'longevity')).toBe('longevity');
    expect(safeDelta('Longer-lasting', 'longevity')).toBe('Longer-lasting');
    expect(safeDelta('+5 pts', '')).toBe('');
  });
});

describe('DimensionBars (WS-B Task B3 — +Npt delta guard)', () => {
  it('renders the dim LABEL when delta_text is raw point-math, not the +Npt', () => {
    const dims = [
      {
        key: 'longevity',
        label: 'longevity',
        score_a: 80,
        score_b: 70,
        delta_text: '+18pt longevity',
      },
    ];
    const { queryAllByText, toJSON } = render(
      <DimensionBars dimensions={dims as any} winnerIndex={0} />,
    );
    // The raw point-math must NOT appear anywhere in the rendered tree.
    const serialised = JSON.stringify(toJSON());
    expect(serialised).not.toMatch(/\+18pt/i);
    // The clean dim label is what renders in the delta caption (in addition to
    // the label row) — the guard swapped "+18pt longevity" for "longevity".
    expect(queryAllByText('longevity').length).toBeGreaterThan(0);
  });

  it('renders a qualitative delta_text unchanged', () => {
    const dims = [
      {
        key: 'longevity',
        label: 'longevity',
        score_a: 80,
        score_b: 70,
        delta_text: 'Longer-lasting',
      },
    ];
    const { queryByText } = render(
      <DimensionBars dimensions={dims as any} winnerIndex={0} />,
    );
    expect(queryByText('Longer-lasting')).toBeTruthy();
  });
});
