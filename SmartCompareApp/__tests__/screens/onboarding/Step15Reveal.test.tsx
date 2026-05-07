/**
 * Step15Reveal tests — Phase 2 Task 22.
 *
 * "Your shopping advisor is ready" — RevealBurst illustration #5 + 4
 * stat cards in 2x2 grid (match quality / top priority / budget tier /
 * region peers count) + "Compare your first product" CTA. The payoff
 * the loading earned. See design spec § 2 row 15.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step15Reveal } from '../../../src/screens/onboarding/Step15Reveal';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const baseProfile = {
  matchQuality: 'Strong',
  topPriority: 'Quality',
  budgetTier: 'Mid-range',
  peerCount: 47,
};

describe('Step15Reveal', () => {
  it('renders the RevealBurst hero illustration', () => {
    const { getByTestId } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />
    );
    expect(getByTestId('s15-burst')).toBeTruthy();
  });

  it('renders the hero title', () => {
    const { getByText } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />
    );
    expect(getByText('onboarding.s15.title')).toBeTruthy();
  });

  it('renders all 4 stat cards in a 2x2 grid', () => {
    const { getByTestId } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />
    );
    expect(getByTestId('stat-match-quality')).toBeTruthy();
    expect(getByTestId('stat-top-priority')).toBeTruthy();
    expect(getByTestId('stat-budget-tier')).toBeTruthy();
    expect(getByTestId('stat-peer-count')).toBeTruthy();
  });

  it('shows the user-facing values inside each card', () => {
    const { getByText } = render(
      <Step15Reveal onNext={jest.fn()} profile={baseProfile} />
    );
    expect(getByText('Strong')).toBeTruthy();
    expect(getByText('Quality')).toBeTruthy();
    expect(getByText('Mid-range')).toBeTruthy();
  });

  it('renders the "Compare your first product" CTA and fires onNext', () => {
    const onNext = jest.fn();
    const { getByText } = render(
      <Step15Reveal onNext={onNext} profile={baseProfile} />
    );
    fireEvent.press(getByText('onboarding.s15.cta'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
