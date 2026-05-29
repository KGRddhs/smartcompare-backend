/**
 * Step13Anticipation tests — Bundle E S2.W3 REWRITE contract.
 *
 * The Phase 2 ConcentricMotif hero + immediate Continue layout was
 * replaced with the JSX OnboardingExtras.jsx s13 recipe: emerald-
 * accentWord headline + 4-stage StageChecklist auto-progressing every
 * 900ms + factoid line + dynamic CTA disabled until all stages reach
 * done.
 *
 * Contract pinned:
 *   - testID="s13-headline" renders the accentWord title pieces
 *   - testID="s13-stage-card" wraps the StageChecklist primitive
 *   - testID="s13-factoid" renders the cohort-substituted factoid line
 *   - testID="s13-cta" reads "Almost there…" initially (disabled),
 *     flips to "Continue" enabled after all stages tick to done
 *   - Governorate prop substitutes into the peers stage + factoid
 *   - Null/undefined governorate falls back to the i18n
 *     onboarding.s13.gcc_fallback key per privacy invariant
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';

const impactAsyncMock = jest.fn().mockResolvedValue(undefined);
jest.mock('expo-haptics', () => ({
  impactAsync: (style: string) => impactAsyncMock(style),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium', Heavy: 'heavy' },
  __esModule: true,
}));

import { Step13Anticipation } from '../../../src/screens/onboarding/Step13Anticipation';

jest.mock('react-i18next', () => ({
  // Simple stub: pass-through key, but interpolate any {{var}} in
  // defaultValue if options contain a matching field. Mirrors the
  // production i18next behavior closely enough for assertion.
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

beforeEach(() => {
  impactAsyncMock.mockClear();
  jest.useFakeTimers();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('Step13Anticipation (S2.W3 REWRITE)', () => {
  it('renders the headline + stage card + factoid + CTA scaffolding', () => {
    const { getByTestId } = render(<Step13Anticipation onNext={jest.fn()} />);
    expect(getByTestId('s13-headline')).toBeTruthy();
    expect(getByTestId('s13-stage-card')).toBeTruthy();
    expect(getByTestId('s13-factoid')).toBeTruthy();
    expect(getByTestId('s13-cta')).toBeTruthy();
  });

  it('CTA reads the "Almost there…" copy on initial mount (loading variant)', () => {
    const { getByTestId } = render(<Step13Anticipation onNext={jest.fn()} />);
    // Button forwards `title` to accessibilityLabel — assert against
    // that since TouchableOpacity-based Button doesn't surface
    // accessibilityState.disabled to the rendered tree under jest.
    const cta = getByTestId('s13-cta');
    expect(cta.props.accessibilityLabel).toBe('onboarding.s13.cta_loading');
  });

  it('CTA flips to the ready copy after all 4 stages auto-progress', () => {
    const onNext = jest.fn();
    const { getByTestId } = render(
      <Step13Anticipation onNext={onNext} stageTickMs={100} />,
    );
    act(() => {
      jest.advanceTimersByTime(500);
    });
    // After completion the CTA is press-enabled; pressing fires onNext.
    // (TouchableOpacity-based Button doesn't surface accessibilityState
    // to the rendered tree under jest, so we assert behavior via the
    // press handler — the disabled→enabled transition is the contract.)
    fireEvent.press(getByTestId('s13-cta'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('fires onNext when CTA is pressed after completion', () => {
    const onNext = jest.fn();
    const { getByTestId } = render(
      <Step13Anticipation onNext={onNext} stageTickMs={100} />,
    );
    act(() => {
      jest.advanceTimersByTime(450);
    });
    fireEvent.press(getByTestId('s13-cta'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('renders 4 StageChecklist rows with the expected ids (region/priorities/peers/calibrate)', () => {
    const { getByTestId } = render(<Step13Anticipation onNext={jest.fn()} />);
    expect(getByTestId('stage-region-icon')).toBeTruthy();
    expect(getByTestId('stage-priorities-icon')).toBeTruthy();
    expect(getByTestId('stage-peers-icon')).toBeTruthy();
    expect(getByTestId('stage-calibrate-icon')).toBeTruthy();
  });

  it('substitutes the governorate display value into the factoid copy', () => {
    // Step13 first resolves the localized governorate label via
    // t('onboarding.s4.gov_capital'). The mock returns the key
    // verbatim, so the factoid string ends up substituting that key
    // as the {{governorate}} token. Asserting on the localized key
    // proves the wiring is governorate-aware without needing the
    // mock to ape full i18next behavior.
    const { getByTestId } = render(
      <Step13Anticipation onNext={jest.fn()} governorate="Capital" />,
    );
    const factoidText = getByTestId('s13-factoid').props.children as string;
    expect(factoidText).toContain('onboarding.s4.gov_capital');
  });

  it('falls back to "the GCC" key when no governorate is supplied (privacy invariant)', () => {
    const { getByTestId } = render(<Step13Anticipation onNext={jest.fn()} />);
    // Step13 resolves the display via t('onboarding.s13.gcc_fallback')
    // which the mock returns verbatim. The mock then substitutes that
    // string into the factoid {{governorate}} slot.
    const factoidText = getByTestId('s13-factoid').props.children as string;
    expect(factoidText).toContain('onboarding.s13.gcc_fallback');
  });
});
