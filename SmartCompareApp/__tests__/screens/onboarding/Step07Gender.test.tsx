/**
 * Step07Gender tests — Phase 2 Task 14.
 *
 * 3 gender cards (Male / Female / Prefer not to say) — cohort key #3,
 * exact strings. See design spec § 2 row 7.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step07Gender } from '../../../src/screens/onboarding/Step07Gender';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step07Gender', () => {
  it('renders all 3 gender options', () => {
    const { getByTestId } = render(<Step07Gender onChange={jest.fn()} onSkip={jest.fn()} />);
    expect(getByTestId('gender-Male')).toBeTruthy();
    expect(getByTestId('gender-Female')).toBeTruthy();
    expect(getByTestId('gender-prefer-not-to-say')).toBeTruthy();
  });

  it('fires onChange("Male") on Male card tap (cohort-exact case)', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step07Gender onChange={onChange} onSkip={jest.fn()} />);
    fireEvent.press(getByTestId('gender-Male'));
    expect(onChange).toHaveBeenCalledWith('Male');
  });

  it('fires onChange("Female") on Female card tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step07Gender onChange={onChange} onSkip={jest.fn()} />);
    fireEvent.press(getByTestId('gender-Female'));
    expect(onChange).toHaveBeenCalledWith('Female');
  });

  it('fires onSkip on prefer-not-to-say tap', () => {
    const onSkip = jest.fn();
    const { getByTestId } = render(<Step07Gender onChange={jest.fn()} onSkip={onSkip} />);
    fireEvent.press(getByTestId('gender-prefer-not-to-say'));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('marks selected state on active gender', () => {
    const { getByTestId } = render(
      <Step07Gender value="Female" onChange={jest.fn()} onSkip={jest.fn()} />
    );
    expect(getByTestId('gender-Female').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('gender-Male').props.accessibilityState?.selected).toBe(false);
  });
});
