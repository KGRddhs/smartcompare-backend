/**
 * Step05Trust tests — Phase 2 Task 14.
 *
 * Trust bridge — pure typography + small filled lock icon, hero "Your data
 * stays yours. We just compare." + 3 thin bullets. Pre-empts the "why do
 * you need this?" objection. See design spec § 2 row 5.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step05Trust } from '../../../src/screens/onboarding/Step05Trust';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step05Trust', () => {
  it('renders the lock icon and hero copy', () => {
    const { getByTestId, getByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByTestId('trust-lock-icon')).toBeTruthy();
    expect(getByText('onboarding.s5.title')).toBeTruthy();
  });

  it('renders all 3 trust bullets', () => {
    const { getByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByText('onboarding.s5.bullet_1')).toBeTruthy();
    expect(getByText('onboarding.s5.bullet_2')).toBeTruthy();
    expect(getByText('onboarding.s5.bullet_3')).toBeTruthy();
  });

  it('fires onNext when continue is pressed', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step05Trust onNext={onNext} />);
    fireEvent.press(getByText('onboarding.s5.continue'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
