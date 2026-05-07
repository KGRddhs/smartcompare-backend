/**
 * Step06Age tests — Phase 2 Task 14.
 *
 * 5 age-group cards (cohort key #2, exact-format "25-34" etc) +
 * "Prefer not to say" link. See design spec § 2 row 6.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step06Age } from '../../../src/screens/onboarding/Step06Age';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step06Age', () => {
  it('renders all 5 age groups with cohort-exact keys', () => {
    const { getByTestId } = render(<Step06Age onChange={jest.fn()} onSkip={jest.fn()} />);
    expect(getByTestId('age-18-24')).toBeTruthy();
    expect(getByTestId('age-25-34')).toBeTruthy();
    expect(getByTestId('age-35-44')).toBeTruthy();
    expect(getByTestId('age-45-54')).toBeTruthy();
    expect(getByTestId('age-55+')).toBeTruthy();
  });

  it('fires onChange("25-34") with the cohort-exact value', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step06Age onChange={onChange} onSkip={jest.fn()} />);
    fireEvent.press(getByTestId('age-25-34'));
    expect(onChange).toHaveBeenCalledWith('25-34');
  });

  it('fires onSkip when "Prefer not to say" link is tapped', () => {
    const onSkip = jest.fn();
    const { getByTestId } = render(<Step06Age onChange={jest.fn()} onSkip={onSkip} />);
    fireEvent.press(getByTestId('age-prefer-not-to-say'));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('shows selected state on the active age group', () => {
    const { getByTestId } = render(
      <Step06Age value="35-44" onChange={jest.fn()} onSkip={jest.fn()} />
    );
    expect(getByTestId('age-35-44').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('age-25-34').props.accessibilityState?.selected).toBe(false);
  });
});
