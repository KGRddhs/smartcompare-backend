/**
 * Step15Reveal tests — Bundle E S2.W4 REWRITE contract.
 *
 * The Phase 2 RevealBurst hero + ad-hoc StatCard cells + CounterTicker
 * peer-count layout is replaced with the JSX-spec MatchBadge primitive
 * (88px emerald circle + 92% + ✦ sparkle + "Strong match" eyebrow) +
 * 4× StatBlock 2x2 grid (Top priority / Budget tier / Peers in
 * {governorate} / GCC cohort) per QA § 6 audit drop of RevealBurst
 * from this surface.
 *
 * Contract pinned:
 *   - testID="s15-match-badge" + "match-badge-circle" + "match-badge-sparkle"
 *   - testID="s15-title" + "s15-subtitle"
 *   - testID="stat-top-priority" / "stat-budget-tier" / "stat-peers-in" /
 *     "stat-gcc-cohort" on the 4 StatBlock tiles
 *   - testID="stat-card-wrap-0..3" on the staggered Animated.View hosts
 *   - testID="s15-cta" fires onNext, label = onboarding.s15.cta key
 *   - DROPPED testIDs: s15-burst (RevealBurst gone), stat-match-quality
 *     (replaced by MatchBadge), stat-peer-count (replaced by peers-in)
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step15Reveal } from '../../../src/screens/onboarding/Step15Reveal';

const impactAsyncMock = jest.fn().mockResolvedValue(undefined);
jest.mock('expo-haptics', () => ({
  impactAsync: (style: string) => impactAsyncMock(style),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium', Heavy: 'heavy' },
  __esModule: true,
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const dv = opts?.defaultValue as string | undefined;
      if (dv && opts?.governorate) {
        return dv.replace(/{{governorate}}/g, String(opts.governorate));
      }
      return key;
    },
  }),
}));

const baseProfile = {
  matchQuality: 92,
  priorities: ['quality', 'durability'],
  budget: 'mid' as const,
  brand_attitude: 'best_of_both' as const,
  country: 'BH' as const,
  governorate: 'Capital' as const,
};

describe('Step15Reveal (S2.W4 REWRITE)', () => {
  it('renders the MatchBadge primitive (NOT the RevealBurst hero)', () => {
    const { getByTestId, queryByTestId } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />,
    );
    expect(getByTestId('s15-match-badge')).toBeTruthy();
    expect(getByTestId('match-badge-circle')).toBeTruthy();
    expect(getByTestId('match-badge-sparkle')).toBeTruthy();
    // RevealBurst dropped from this surface per QA § 6 audit — guard
    // against regression silently re-importing it.
    expect(queryByTestId('s15-burst')).toBeNull();
  });

  it('renders the headline + subtitle', () => {
    const { getByTestId, getByText } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />,
    );
    expect(getByTestId('s15-title')).toBeTruthy();
    expect(getByTestId('s15-subtitle')).toBeTruthy();
    expect(getByText('onboarding.s15.title')).toBeTruthy();
  });

  it('renders all 4 StatBlock tiles in a 2x2 grid', () => {
    const { getByTestId } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />,
    );
    expect(getByTestId('stat-top-priority')).toBeTruthy();
    expect(getByTestId('stat-budget-tier')).toBeTruthy();
    expect(getByTestId('stat-peers-in')).toBeTruthy();
    expect(getByTestId('stat-gcc-cohort')).toBeTruthy();
  });

  it('substitutes the localized governorate label into the "Peers in" tile', () => {
    const { getByText } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />,
    );
    // Mock t() returns the substituted defaultValue when {{governorate}}
    // is present. governorateDisplay resolves to the i18n key
    // `onboarding.s4.gov_capital` per Step13/14 pattern; the mock returns
    // that key verbatim, which the peers_in defaultValue then
    // substitutes in.
    const peerTile = getByText(/onboarding.s4.gov_capital/);
    expect(peerTile).toBeTruthy();
  });

  it('falls back to "the GCC" when no governorate is supplied (privacy invariant)', () => {
    const { getByText } = render(
      <Step15Reveal
        onNext={jest.fn()}
        profile={{ ...baseProfile, governorate: undefined }}
      />,
    );
    // Falls back to the i18n key `onboarding.s13.gcc_fallback`; mock
    // returns the key verbatim which the peers_in defaultValue then
    // interpolates.
    expect(getByText(/onboarding.s13.gcc_fallback/)).toBeTruthy();
  });

  it('renders the staggered wrappers around each of the 4 stat cards', () => {
    const { getByTestId } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />,
    );
    [0, 1, 2, 3].forEach((i) => {
      const wrap = getByTestId(`stat-card-wrap-${i}`);
      const styleArr = Array.isArray(wrap.props.style)
        ? wrap.props.style
        : [wrap.props.style];
      const flat: Record<string, unknown> = styleArr
        .filter(Boolean)
        .reduce(
          (acc: Record<string, unknown>, s: Record<string, unknown>) =>
            Object.assign(acc, s),
          {} as Record<string, unknown>,
        );
      expect(flat.opacity).toBeDefined();
      expect(flat.transform).toBeDefined();
    });
  });

  it('renders the CTA and fires onNext when pressed', () => {
    const onNext = jest.fn();
    const { getByTestId } = render(
      <Step15Reveal onNext={onNext} profile={baseProfile} />,
    );
    fireEvent.press(getByTestId('s15-cta'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('defaults match percent to 92 when matchQuality is absent', () => {
    const { getByText } = render(
      <Step15Reveal
        onNext={jest.fn()}
        profile={{ ...baseProfile, matchQuality: undefined }}
      />,
    );
    // MatchBadge renders "92%" inside the circle per JSX default.
    expect(getByText('92%')).toBeTruthy();
  });
});
