/**
 * Step04Country tests — Phase 2 Task 14.
 *
 * 6 GCC flag cards. If country === BH, conditional governorate
 * sub-question reveals. See design spec § 2 row 4.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step04Country } from '../../../src/screens/onboarding/Step04Country';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step04Country', () => {
  it('renders all 6 GCC country options', () => {
    const { getByTestId } = render(
      <Step04Country onChangeCountry={jest.fn()} onChangeGovernorate={jest.fn()} />
    );
    expect(getByTestId('country-BH')).toBeTruthy();
    expect(getByTestId('country-SA')).toBeTruthy();
    expect(getByTestId('country-AE')).toBeTruthy();
    expect(getByTestId('country-KW')).toBeTruthy();
    expect(getByTestId('country-QA')).toBeTruthy();
    expect(getByTestId('country-OM')).toBeTruthy();
  });

  it('does not show governorate sub-question initially', () => {
    const { queryByTestId } = render(
      <Step04Country onChangeCountry={jest.fn()} onChangeGovernorate={jest.fn()} />
    );
    expect(queryByTestId('gov-Capital')).toBeNull();
  });

  it('reveals 4 governorate options when country=BH', () => {
    const { getByTestId } = render(
      <Step04Country
        country="BH"
        onChangeCountry={jest.fn()}
        onChangeGovernorate={jest.fn()}
      />
    );
    expect(getByTestId('gov-Capital')).toBeTruthy();
    expect(getByTestId('gov-Muharraq')).toBeTruthy();
    expect(getByTestId('gov-Northern')).toBeTruthy();
    expect(getByTestId('gov-Southern')).toBeTruthy();
  });

  it('does NOT show governorate sub-question for non-BH countries', () => {
    const { queryByTestId } = render(
      <Step04Country
        country="SA"
        onChangeCountry={jest.fn()}
        onChangeGovernorate={jest.fn()}
      />
    );
    expect(queryByTestId('gov-Capital')).toBeNull();
  });

  it('fires onChangeCountry when a country card is tapped', () => {
    const onChangeCountry = jest.fn();
    const { getByTestId } = render(
      <Step04Country onChangeCountry={onChangeCountry} onChangeGovernorate={jest.fn()} />
    );
    fireEvent.press(getByTestId('country-BH'));
    expect(onChangeCountry).toHaveBeenCalledWith('BH');
  });

  it('fires onChangeGovernorate when a governorate card is tapped', () => {
    const onChangeGovernorate = jest.fn();
    const { getByTestId } = render(
      <Step04Country
        country="BH"
        onChangeCountry={jest.fn()}
        onChangeGovernorate={onChangeGovernorate}
      />
    );
    fireEvent.press(getByTestId('gov-Capital'));
    expect(onChangeGovernorate).toHaveBeenCalledWith('Capital');
  });
});
