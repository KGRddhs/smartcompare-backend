/**
 * SplashScreen Tests
 * Tests the splash screen animation flow and onFinish callback
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import SplashScreen from '../src/screens/SplashScreen';

// Use our local mock instead of package mock
jest.mock('react-native-reanimated');

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
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

  it('should render the logo text', () => {
    const mockOnFinish = jest.fn();
    const { getByText } = render(<SplashScreen onFinish={mockOnFinish} />);
    expect(getByText('قارن')).toBeTruthy();
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
