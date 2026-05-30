/**
 * BrandAttitudePicker — Bundle E F-S2.X3 regression suite.
 *
 * Pins the OptionRow icon-circle pattern after the X3 rewrite swapped
 * the prior bespoke TouchableOpacity cards for the W2.hotfix Step10
 * rhythm. EditPreferencesFlow.test.tsx mocks this component, so a
 * missing lucide glyph or sub-line regression would otherwise sneak
 * past CI.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import BrandAttitudePicker from '../../src/components/BrandAttitudePicker';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('BrandAttitudePicker (S2.X3 OptionRow rewrite)', () => {
  it('renders all 3 user-pickable attitudes with lucide icon glyphs', () => {
    const { getByTestId, getAllByTestId } = render(
      <BrandAttitudePicker onChange={jest.fn()} />
    );
    expect(getByTestId('brand-brand_loyal')).toBeTruthy();
    expect(getByTestId('brand-function_first')).toBeTruthy();
    expect(getByTestId('brand-best_of_both')).toBeTruthy();
    // 3 OptionRow icon-circle ReactNode lucide glyphs.
    expect(getAllByTestId('option-row-icon-node').length).toBe(3);
  });

  it('renders the sub line below each label', () => {
    const { getAllByTestId } = render(
      <BrandAttitudePicker onChange={jest.fn()} />
    );
    // OptionRow's sub-line renders only when `option.sub` is truthy.
    // 3 rows × 1 sub each = 3.
    expect(getAllByTestId('option-row-sub').length).toBe(3);
  });

  it('fires onChange with the chosen attitude value', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <BrandAttitudePicker onChange={onChange} />
    );
    fireEvent.press(getByTestId('brand-function_first'));
    expect(onChange).toHaveBeenCalledWith('function_first');
  });

  it('mirrors accessibilityState.selected on the active row', () => {
    const { getByTestId } = render(
      <BrandAttitudePicker value="best_of_both" onChange={jest.fn()} />
    );
    expect(
      getByTestId('brand-best_of_both').props.accessibilityState?.selected
    ).toBe(true);
    expect(
      getByTestId('brand-brand_loyal').props.accessibilityState?.selected
    ).toBe(false);
  });
});
