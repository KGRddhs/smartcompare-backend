/**
 * Step10BrandAttitude tests — Phase 2 Task 15.
 *
 * 3 brand attitude cards: Brand-loyal / Function-first / Best of both.
 * Final personalization key. See design spec § 2 row 10.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step10BrandAttitude } from '../../../src/screens/onboarding/Step10BrandAttitude';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step10BrandAttitude', () => {
  it('renders all 3 brand attitudes', () => {
    const { getByTestId } = render(<Step10BrandAttitude onChange={jest.fn()} />);
    expect(getByTestId('brand-brand_loyal')).toBeTruthy();
    expect(getByTestId('brand-function_first')).toBeTruthy();
    expect(getByTestId('brand-best_of_both')).toBeTruthy();
  });

  it('fires onChange with the chosen attitude', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step10BrandAttitude onChange={onChange} />);
    fireEvent.press(getByTestId('brand-best_of_both'));
    expect(onChange).toHaveBeenCalledWith('best_of_both');
  });

  it('marks selected with accessibilityState.selected=true', () => {
    const { getByTestId } = render(
      <Step10BrandAttitude value="brand_loyal" onChange={jest.fn()} />
    );
    expect(getByTestId('brand-brand_loyal').props.accessibilityState?.selected).toBe(true);
  });

  // F-S2.W2.hotfix (task #38): per-attitude lucide icons inside the
  // OptionRow icon-circle. Ahmed's W2 device walk caught empty
  // circles on Step10 — W2 shipped label+sub only. Regression-guard
  // each row has a ReactNode icon mounted via the lucide mock.
  it('renders a per-attitude icon inside each OptionRow icon-circle', () => {
    const { getAllByTestId } = render(
      <Step10BrandAttitude onChange={jest.fn()} />
    );
    // OptionRow exposes testID="option-row-icon-node" for the
    // ReactNode-icon render path (vs "option-row-icon-glyph" for
    // string icons). One node per row → 3 total.
    expect(getAllByTestId('option-row-icon-node').length).toBe(3);
  });
});
