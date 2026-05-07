/**
 * Step13Anticipation tests — Phase 2 Task 20.
 *
 * "Time to build your shopping advisor" + ConcentricMotif illustration #3
 * + "Build my advisor" CTA. Build-up before the theatrical loading payoff
 * on screen 14. See design spec § 2 row 13.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step13Anticipation } from '../../../src/screens/onboarding/Step13Anticipation';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step13Anticipation', () => {
  it('renders the ConcentricMotif illustration', () => {
    const { getByTestId } = render(<Step13Anticipation onNext={jest.fn()} />);
    expect(getByTestId('s13-concentric')).toBeTruthy();
  });

  it('renders the hero title', () => {
    const { getByText } = render(<Step13Anticipation onNext={jest.fn()} />);
    expect(getByText('onboarding.s13.title')).toBeTruthy();
  });

  it('renders the "Build my advisor" CTA and fires onNext', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step13Anticipation onNext={onNext} />);
    const cta = getByText('onboarding.s13.cta');
    expect(cta).toBeTruthy();
    fireEvent.press(cta);
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
