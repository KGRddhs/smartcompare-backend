/**
 * Step03ValueProp tests — Phase 2 Task 13.
 *
 * Phone mockup hero illustration #1 + "Stop guessing. Start knowing."
 * + Continue. Show value before asking anything. See design spec § 2 row 3.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step03ValueProp } from '../../../src/screens/onboarding/Step03ValueProp';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step03ValueProp', () => {
  it('renders the phone mockup illustration', () => {
    const { getByTestId } = render(<Step03ValueProp onNext={jest.fn()} />);
    expect(getByTestId('s3-phone-mockup')).toBeTruthy();
  });

  it('renders the hero title and continue CTA', () => {
    const { getByText } = render(<Step03ValueProp onNext={jest.fn()} />);
    expect(getByText('onboarding.s3.title')).toBeTruthy();
    expect(getByText('onboarding.s3.continue')).toBeTruthy();
  });

  it('fires onNext when Continue is pressed', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step03ValueProp onNext={onNext} />);
    fireEvent.press(getByText('onboarding.s3.continue'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
