/**
 * Step01Welcome tests — Phase 2 Task 13.
 *
 * Big black Q-logo, hero "Look closer. Decide smarter." Continue + small
 * "Already have an account? Sign in" link below. See design spec § 2 row 1.
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
