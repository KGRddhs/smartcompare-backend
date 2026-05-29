/**
 * Step05Trust tests — Bundle E S2.W1 rewrite contract.
 *
 * The Phase 2 lock-badge hero + 3 bullets layout was replaced with the
 * JSX OnboardingExtras.jsx s5 recipe: 3 PrivacyRow primitives + "I'm in"
 * CTA + emerald-accentWord headline. Lock-rotation contract dropped per
 * JSX-wins doctrine — JSX has no hero on this surface.
 *
 * Pin the new contract:
 *   - 3 PrivacyRow rows render with testIDs trust-row-{use,anon,never}
 *   - Each row exposes head + body strings via i18n keys
 *   - "I'm in" CTA fires onNext
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step05Trust } from '../../../src/screens/onboarding/Step05Trust';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step05Trust — Bundle E S2.W1 rewrite', () => {
  it('renders the 3 PrivacyRow hosts with new testIDs', () => {
    const { getByTestId } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByTestId('trust-row-use')).toBeTruthy();
    expect(getByTestId('trust-row-anon')).toBeTruthy();
    expect(getByTestId('trust-row-never')).toBeTruthy();
  });

  it('renders the 3 PrivacyRow head + body i18n keys', () => {
    const { getByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByText('onboarding.s5.privacy_use_head')).toBeTruthy();
    expect(getByText('onboarding.s5.privacy_use_body')).toBeTruthy();
    expect(getByText('onboarding.s5.privacy_anon_head')).toBeTruthy();
    expect(getByText('onboarding.s5.privacy_anon_body')).toBeTruthy();
    expect(getByText('onboarding.s5.privacy_never_head')).toBeTruthy();
    expect(getByText('onboarding.s5.privacy_never_body')).toBeTruthy();
  });

  it('renders the emerald-accentWord headline parts', () => {
    // Nested <Text> elements (before / accent / after) get
    // concatenated into the parent's accessible text by
    // testing-library, so we match against the joined string with a
    // regex that asserts all three key fragments are present.
    const { getByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(
      getByText(/onboarding\.s5\.title_before/),
    ).toBeTruthy();
    expect(
      getByText(/onboarding\.s5\.title_accent/),
    ).toBeTruthy();
  });

  it('CTA label is the new "I\'m in" i18n key (not "Continue")', () => {
    const { getByText, queryByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByText('onboarding.s5.cta')).toBeTruthy();
    // Legacy "continue" key should no longer drive the CTA on this
    // surface (the key still exists in i18n for backward-compat but
    // Step05 no longer reads it).
    expect(queryByText('onboarding.s5.continue')).toBeNull();
  });

  it('fires onNext when the CTA is pressed', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step05Trust onNext={onNext} />);
    fireEvent.press(getByText('onboarding.s5.cta'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('does NOT render the Phase 2 lock-badge hero', () => {
    // JSX-wins: the lock-icon hero was dropped per JSX OnboardingExtras
    // s5. The testID is gone, and the prior 5° rotation Reanimated
    // contract no longer applies.
    const { queryByTestId } = render(<Step05Trust onNext={jest.fn()} />);
    expect(queryByTestId('trust-lock-icon')).toBeNull();
  });
});
