// Bundle C — BudgetPicker 5-tier expansion tests (Section C plan C.4 + C.11.3).
//
// Spec §3a + 3c + 3d: 5 budget cards (Budget-savvy / Mid-range / Premium /
// Luxury / Top-tier). Premium/Luxury/Top-tier visually editorial. Top-tier
// gets heavy font weight.
//
// Backwards-compat (spec §3d): legacy 3-tier values still pass; new 2 values
// also pass.

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { expectNoForbiddenStrings } from './_bundle_c_helpers';
import BudgetPicker from '../src/components/BudgetPicker';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,  // identity — pass through key as label for tests
  }),
}));

describe('BudgetPicker (Bundle C 5-tier)', () => {
  it('renders all 5 tier cards with testID for each tier value', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<BudgetPicker onChange={onChange} />);
    for (const tier of ['budget', 'mid', 'premium', 'luxury', 'top_tier']) {
      expect(getByTestId(`budget-${tier}`)).toBeTruthy();
    }
  });

  it('emits the new tier value via onChange when card pressed', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<BudgetPicker onChange={onChange} />);
    fireEvent.press(getByTestId('budget-top_tier'));
    expect(onChange).toHaveBeenCalledWith('top_tier');
  });

  it('emits each legacy + new tier value correctly', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<BudgetPicker onChange={onChange} />);
    for (const tier of ['budget', 'mid', 'premium', 'luxury', 'top_tier']) {
      onChange.mockReset();
      fireEvent.press(getByTestId(`budget-${tier}`));
      expect(onChange).toHaveBeenLastCalledWith(tier);
    }
  });

  it('marks the currently-selected card via accessibilityState.selected', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <BudgetPicker value="luxury" onChange={onChange} />,
    );
    const luxuryCard = getByTestId('budget-luxury');
    expect(luxuryCard.props.accessibilityState).toMatchObject({ selected: true });
    // Non-selected card should not have selected=true
    const midCard = getByTestId('budget-mid');
    expect(midCard.props.accessibilityState?.selected).toBeFalsy();
  });

  it('renders i18n keys for all 5 tiers (no hard-coded strings)', () => {
    const onChange = jest.fn();
    const { getByText } = render(<BudgetPicker onChange={onChange} />);
    // With identity-mock useTranslation, label text === key
    expect(getByText('onboarding.s9.budget')).toBeTruthy();
    expect(getByText('onboarding.s9.mid')).toBeTruthy();
    expect(getByText('onboarding.s9.premium')).toBeTruthy();
    expect(getByText('onboarding.s9.luxury')).toBeTruthy();
    expect(getByText('onboarding.s9.top_tier')).toBeTruthy();
  });

  it('NO forbidden vocabulary in render tree (no "estimated"/scary copy)', () => {
    const onChange = jest.fn();
    const tree = render(<BudgetPicker onChange={onChange} />).toJSON();
    expectNoForbiddenStrings(tree);
  });

  it('snapshot — default rendered state', () => {
    const onChange = jest.fn();
    const tree = render(<BudgetPicker onChange={onChange} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('snapshot — top_tier selected', () => {
    const onChange = jest.fn();
    const tree = render(
      <BudgetPicker value="top_tier" onChange={onChange} />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });
});
