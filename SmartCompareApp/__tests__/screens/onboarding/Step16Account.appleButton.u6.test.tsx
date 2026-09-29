/**
 * S69 U6 R1 fix-round — onboarding Step 16 offers Sign in with Apple through
 * the SDK's native button (system-drawn logo, guideline 4.8 / HIG), never a
 * label-only SocialButton. Step 16 is unreachable today
 * (NewOnboardingHost passes isAuthenticated), but it becomes a live 4.8
 * surface the moment the anonymous flow is wired, so the choice is pinned.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import * as AppleAuthentication from 'expo-apple-authentication';
import { Step16Account } from '../../../src/screens/onboarding/Step16Account';
import { radii } from '../../../src/theme';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('S69 U6 R1 — Step16 Apple row is the native Sign in with Apple button', () => {
  it('renders AppleAuthenticationButton (CONTINUE, BLACK, radius 12, 48 high) as account-apple', () => {
    const { getByTestId, queryByText } = render(
      <Step16Account onSelectMethod={jest.fn()} appleAvailable />,
    );
    const btn = getByTestId('account-apple');
    expect(btn.type).toBe('AppleAuthenticationButton');
    expect(btn.props.buttonType).toBe(
      AppleAuthentication.AppleAuthenticationButtonType.CONTINUE,
    );
    expect(btn.props.buttonStyle).toBe(
      AppleAuthentication.AppleAuthenticationButtonStyle.BLACK,
    );
    expect(btn.props.cornerRadius).toBe(radii.button);
    const style = Object.assign({}, ...[btn.props.style].flat(Infinity).filter(Boolean));
    expect(style.height).toBe(48);
    expect(style.width).toBe('100%');
    // No hand-rolled label-only Apple row.
    expect(queryByText('onboarding.s16.apple')).toBeNull();
  });

  it('a press on the native button selects the apple method', () => {
    const onSelectMethod = jest.fn();
    const { getByTestId } = render(
      <Step16Account onSelectMethod={onSelectMethod} appleAvailable />,
    );
    fireEvent.press(getByTestId('account-apple'));
    expect(onSelectMethod).toHaveBeenCalledWith('apple');
  });

  it('renders no Apple control at all when Apple sign-in is unavailable', () => {
    const { queryByTestId } = render(
      <Step16Account onSelectMethod={jest.fn()} appleAvailable={false} />,
    );
    expect(queryByTestId('account-apple')).toBeNull();
    expect(queryByTestId('account-google')).toBeTruthy();
    expect(queryByTestId('account-email')).toBeTruthy();
  });
});
