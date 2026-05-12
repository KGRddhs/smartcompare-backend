/**
 * SplashScreen Tests
 * Tests the splash screen animation flow and onFinish callback
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import SplashScreen from '../src/screens/SplashScreen';

// react-native-reanimated is mapped to __mocks__/react-native-reanimated.ts via
// jest.config.js moduleNameMapper. A bare `jest.mock('react-native-reanimated')`
// (no factory) auto-mocks and stubs useSharedValue → undefined, crashing any
// component that does `animatedWidth.value = ...`. Rely on the mapper.

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'app.name': 'Qaren',
        'splash.tagline': 'Compare smarter',
      };
      return translations[key] || key;
    },
  }),
}));

describe('SplashScreen', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should render the wordmark via i18n (no longer a hardcoded Arabic glyph)', () => {
    // Bundle B/C/D Task 2.10 — splash header now uses t('app.name') so
    // EN/AR users see their own locale's brand name.
    const mockOnFinish = jest.fn();
    const { getByText } = render(<SplashScreen onFinish={mockOnFinish} />);
    expect(getByText('Qaren')).toBeTruthy();
  });

  it('should render the tagline', () => {
    const mockOnFinish = jest.fn();
    const { getByText } = render(<SplashScreen onFinish={mockOnFinish} />);
    expect(getByText('Compare smarter')).toBeTruthy();
  });

  it('should call onFinish after 1.5 seconds', () => {
    const mockOnFinish = jest.fn();
    render(<SplashScreen onFinish={mockOnFinish} />);

    expect(mockOnFinish).not.toHaveBeenCalled();
    jest.advanceTimersByTime(1500);
    expect(mockOnFinish).toHaveBeenCalledTimes(1);
  });

  it('should clean up timer on unmount', () => {
    const mockOnFinish = jest.fn();
    const { unmount } = render(<SplashScreen onFinish={mockOnFinish} />);

    unmount();
    jest.advanceTimersByTime(1500);
    // onFinish should NOT be called after unmount
    expect(mockOnFinish).not.toHaveBeenCalled();
  });
});
