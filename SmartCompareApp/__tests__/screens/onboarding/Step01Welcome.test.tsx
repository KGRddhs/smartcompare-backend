/**
 * Step01Welcome tests — Phase 2 Task 13 + Bundle E S2.W1 REWRITE.
 *
 * Original (Phase 2): big black 96px Q-badge + hero copy + Continue +
 * sign-in link.
 *
 * S2.W1 anatomy per OnboardingWelcomeScreen.jsx:
 *   - warm-wash tinted-corner bg (testIDs welcome-warm-{left,right})
 *   - QarenLogo 40px (testID welcome-qicon stays on the wrapper)
 *   - headline + subtitle copy unchanged
 *   - 3 QuoteRow testimonials (testIDs welcome-quote-{1,2,3})
 *   - Continue + sign-in link unchanged
 *
 * Tests below pin BOTH the preserved Phase 2 contract AND the new S2.W1
 * QuoteRow trio + warm-wash corner anchors, so neither piece can
 * regress silently.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step01Welcome } from '../../../src/screens/onboarding/Step01Welcome';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step01Welcome', () => {
  it('renders the brand Q-icon', () => {
    const { getByTestId } = render(<Step01Welcome onNext={jest.fn()} onSignIn={jest.fn()} />);
    expect(getByTestId('welcome-qicon')).toBeTruthy();
  });

  it('renders the warm-wash tinted corner pair (S2.W1)', () => {
    const { getByTestId } = render(<Step01Welcome onNext={jest.fn()} onSignIn={jest.fn()} />);
    expect(getByTestId('welcome-warm-left')).toBeTruthy();
    expect(getByTestId('welcome-warm-right')).toBeTruthy();
  });

  it('renders the 3 QuoteRow testimonials (S2.W1)', () => {
    const { getByTestId, getByText } = render(
      <Step01Welcome onNext={jest.fn()} onSignIn={jest.fn()} />,
    );
    expect(getByTestId('welcome-quote-1')).toBeTruthy();
    expect(getByTestId('welcome-quote-2')).toBeTruthy();
    expect(getByTestId('welcome-quote-3')).toBeTruthy();
    expect(getByText('onboarding.s1.quote_1')).toBeTruthy();
    expect(getByText('onboarding.s1.quote_2')).toBeTruthy();
    expect(getByText('onboarding.s1.quote_3')).toBeTruthy();
  });

  it('renders the hero tagline and continue CTA', () => {
    const { getByText } = render(<Step01Welcome onNext={jest.fn()} onSignIn={jest.fn()} />);
    expect(getByText('onboarding.s1.title')).toBeTruthy();
    expect(getByText('onboarding.s1.continue')).toBeTruthy();
  });

  it('fires onNext when Continue is pressed', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step01Welcome onNext={onNext} onSignIn={jest.fn()} />);
    fireEvent.press(getByText('onboarding.s1.continue'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('renders the sign-in link and fires onSignIn when pressed', () => {
    const onSignIn = jest.fn();
    const { getByText } = render(<Step01Welcome onNext={jest.fn()} onSignIn={onSignIn} />);
    fireEvent.press(getByText('onboarding.s1.sign_in_link'));
    expect(onSignIn).toHaveBeenCalledTimes(1);
  });

  it('omits the sign-in link when no onSignIn prop is supplied', () => {
    const { queryByText } = render(<Step01Welcome onNext={jest.fn()} />);
    expect(queryByText('onboarding.s1.sign_in_link')).toBeNull();
  });
});
