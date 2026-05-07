/**
 * Step09Budget tests — Phase 2 Task 15.
 *
 * 3 budget tier cards with BHD ranges. Aligns with backend
 * `_get_price_tier()`: budget(<11), mid(11-57), premium(57-189).
 * See design spec § 2 row 9.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step09Budget } from '../../../src/screens/onboarding/Step09Budget';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step09Budget', () => {
  it('renders all 3 budget tiers', () => {
    const { getByTestId } = render(<Step09Budget onChange={jest.fn()} />);
    expect(getByTestId('budget-budget')).toBeTruthy();
    expect(getByTestId('budget-mid')).toBeTruthy();
    expect(getByTestId('budget-premium')).toBeTruthy();
  });

  it('fires onChange("mid") on mid tier tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step09Budget onChange={onChange} />);
    fireEvent.press(getByTestId('budget-mid'));
    expect(onChange).toHaveBeenCalledWith('mid');
  });

  it('marks selected tier with accessibilityState.selected=true', () => {
    const { getByTestId } = render(<Step09Budget value="premium" onChange={jest.fn()} />);
    expect(getByTestId('budget-premium').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('budget-mid').props.accessibilityState?.selected).toBe(false);
  });
});
