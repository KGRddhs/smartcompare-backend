/**
 * Step16Account tests — Phase 2 Task 23.
 *
 * "Save your advisor" — Apple / Google / Email choice. NO skip link
 * (forced sign-in per design § 2 row 16; sunk-cost makes drop-off lowest
 * here, account required for Loop 2 + cohort persistence + push +
 * Apple guideline 4.8). Screen is presentational — orchestrator handles
 * the actual auth call.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step16Account } from '../../../src/screens/onboarding/Step16Account';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step16Account', () => {
  it('renders the title and the 3 sign-in choices', () => {
    const { getByText, getByTestId } = render(
      <Step16Account onSelectMethod={jest.fn()} />
    );
    expect(getByText('onboarding.s16.title')).toBeTruthy();
    expect(getByTestId('account-apple')).toBeTruthy();
    expect(getByTestId('account-google')).toBeTruthy();
    expect(getByTestId('account-email')).toBeTruthy();
  });

  it('does NOT render any skip link', () => {
    const { queryByText, queryByTestId } = render(
      <Step16Account onSelectMethod={jest.fn()} />
    );
    expect(queryByText('onboarding.skip')).toBeNull();
    expect(queryByTestId('account-skip')).toBeNull();
    expect(queryByText('Skip')).toBeNull();
  });

  it('fires onSelectMethod("apple") on Apple tap', () => {
    const onSelectMethod = jest.fn();
    const { getByTestId } = render(<Step16Account onSelectMethod={onSelectMethod} />);
    fireEvent.press(getByTestId('account-apple'));
    expect(onSelectMethod).toHaveBeenCalledWith('apple');
  });

  it('fires onSelectMethod("google") on Google tap', () => {
    const onSelectMethod = jest.fn();
    const { getByTestId } = render(<Step16Account onSelectMethod={onSelectMethod} />);
    fireEvent.press(getByTestId('account-google'));
    expect(onSelectMethod).toHaveBeenCalledWith('google');
  });

  it('fires onSelectMethod("email") on Email tap', () => {
    const onSelectMethod = jest.fn();
    const { getByTestId } = render(<Step16Account onSelectMethod={onSelectMethod} />);
    fireEvent.press(getByTestId('account-email'));
    expect(onSelectMethod).toHaveBeenCalledWith('email');
  });

  it('hides Apple sign-in when appleAvailable=false', () => {
    const { queryByTestId } = render(
      <Step16Account onSelectMethod={jest.fn()} appleAvailable={false} />
    );
    expect(queryByTestId('account-apple')).toBeNull();
  });
});
