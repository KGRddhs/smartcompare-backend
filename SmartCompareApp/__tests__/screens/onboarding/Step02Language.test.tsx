/**
 * Step02Language tests — Phase 2 Task 13.
 *
 * "Choose your language / اختر لغتك" — English / العربية choice.
 * Setting language EARLY so subsequent screens render in the right
 * direction. See design spec § 2 row 2.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step02Language } from '../../../src/screens/onboarding/Step02Language';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const switchLanguageMock = jest.fn();
jest.mock('../../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: 'en',
    isRTL: false,
    switchLanguage: switchLanguageMock,
  }),
}));

beforeEach(() => switchLanguageMock.mockClear());

describe('Step02Language', () => {
  it('renders the title', () => {
    const { getByText } = render(<Step02Language onChange={jest.fn()} />);
    expect(getByText('onboarding.s2.title')).toBeTruthy();
  });

  it('renders both language choices', () => {
    const { getByTestId } = render(<Step02Language onChange={jest.fn()} />);
    expect(getByTestId('lang-en')).toBeTruthy();
    expect(getByTestId('lang-ar')).toBeTruthy();
  });

  it('fires onChange("en") and switchLanguage("en") on English tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step02Language onChange={onChange} />);
    fireEvent.press(getByTestId('lang-en'));
    expect(onChange).toHaveBeenCalledWith('en');
    expect(switchLanguageMock).toHaveBeenCalledWith('en');
  });

  it('fires onChange("ar") and switchLanguage("ar") on Arabic tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step02Language onChange={onChange} />);
    fireEvent.press(getByTestId('lang-ar'));
    expect(onChange).toHaveBeenCalledWith('ar');
    expect(switchLanguageMock).toHaveBeenCalledWith('ar');
  });

  it('marks the active language with accessibilityState.selected=true', () => {
    const { getByTestId } = render(<Step02Language onChange={jest.fn()} value="en" />);
    expect(getByTestId('lang-en').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('lang-ar').props.accessibilityState?.selected).toBe(false);
  });
});
