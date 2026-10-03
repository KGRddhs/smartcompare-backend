/**
 * SplashScreen Tests
 * Tests the splash screen animation flow and onFinish callback
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';
import SplashScreen from '../src/screens/SplashScreen';

// react-native-reanimated is mapped to __mocks__/react-native-reanimated.ts via
// jest.config.js moduleNameMapper. A bare `jest.mock('react-native-reanimated')`
// (no factory) auto-mocks and stubs useSharedValue → undefined, crashing any
// component that does `animatedWidth.value = ...`. Rely on the mapper.

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'app.name': 'MYEZ',
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

  it('E1 does not render the app name beside the mark (D1)', () => {
    // U4c D1 (spec 2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md §5 E1):
    // the splash shows the MYEZ mark alone; the t('app.name') wordmark that
    // used to sit beside it is removed. The tagline stays (next case).
    const mockOnFinish = jest.fn();
    const { queryByText } = render(<SplashScreen onFinish={mockOnFinish} />);
    // queryByText('MYEZ') must be null; its children are read so a red
    // names the rendered text instead of dumping the fiber.
    expect(queryByText('MYEZ')?.props.children ?? null).toBeNull();
  });

  it('should render the tagline', () => {
    const mockOnFinish = jest.fn();
    const { getByText } = render(<SplashScreen onFinish={mockOnFinish} />);
    expect(getByText('Compare smarter')).toBeTruthy();
  });

  it('should call onFinish after 1.5 seconds when no readiness signal is given', () => {
    // A5 — 1500ms is now the CAP, not a flat toll, and an omitted `ready`
    // prop deliberately degrades to that cap (the safe fallback: never
    // shorter than the pre-A5 behaviour). The ready-boot branch and the
    // crossing cases are pinned in SplashScreen.readyFloor.a5.test.tsx.
    const mockOnFinish = jest.fn();
    render(<SplashScreen onFinish={mockOnFinish} />);

    expect(mockOnFinish).not.toHaveBeenCalled();
    act(() => {
      jest.advanceTimersByTime(1500);
    });
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
