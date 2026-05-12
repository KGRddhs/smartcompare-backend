/**
 * HomeScreen — Bundle B/C/D Task 2.6 contract.
 *
 * Tapping the Scan mode chip navigates to the new ScanCamera modal
 * (instead of switching into the inline camera mode) — see plan
 * § Task 2.6 + design doc § 4.6.
 *
 * Also enforces MAX_IMAGES=2 (down from 4).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

jest.mock('expo-camera', () => ({
  CameraView: ({ children, ...rest }: any) =>
    require('react').createElement('CameraView', rest, children),
  useCameraPermissions: () => [{ granted: true }, jest.fn()],
}));

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn(),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(),
  notificationAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

jest.mock('lucide-react-native', () => ({
  Camera: 'Camera',
  Search: 'Search',
  Link2: 'Link2',
  RotateCcw: 'RotateCcw',
  ImageIcon: 'ImageIcon',
  X: 'X',
  Edit3: 'Edit3',
}));

jest.mock('../src/services/api', () => ({
  healthCheck: jest.fn(() => Promise.resolve(true)),
  streamComparison: jest.fn(),
  parseApiError: jest.fn((e: any) => ({ message: e.message || 'Error' })),
  identifyFromImages: jest.fn(),
  default: { post: jest.fn() },
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: jest.fn(() => Promise.resolve(null)),
}));

jest.mock('../src/services/usageService', () => ({
  isUsageLimitError: jest.fn(() => false),
  getUsageLimitDetail: jest.fn(),
}));

jest.mock('../src/components/CategorySelector', () => ({
  __esModule: true,
  default: () => require('react').createElement('CategorySelector'),
}));

jest.mock('../src/components/SearchOverlay', () => ({
  SearchOverlay: () => require('react').createElement('SearchOverlay'),
}));

jest.mock('../src/components/ComparisonCounter', () => ({
  ComparisonCounter: ({ used, total }: { used: number; total: number }) =>
    require('react').createElement('ComparisonCounter', { used, total }),
}));

jest.mock('../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    shouldShowPaywall: false,
    increment: jest.fn(() => Promise.resolve(2)),
  }),
}));

jest.mock('@react-navigation/native', () => ({
  useFocusEffect: jest.fn(),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(() => Promise.resolve(null)),
  setItem: jest.fn(() => Promise.resolve()),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string; n?: number }) =>
      typeof opts?.n === 'number' ? `${key}|n=${opts.n}` : key,
  }),
}));

import HomeScreen, { MAX_IMAGES } from '../src/screens/HomeScreen';

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
} as any;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('HomeScreen — Bundle B/C/D scan-chip navigation', () => {
  it('navigates to ScanCamera when scan mode chip is tapped', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    fireEvent.press(getByTestId('home-mode-scan'));
    expect(mockNavigation.navigate).toHaveBeenCalledWith('ScanCamera');
  });

  it('does NOT navigate when Link or Type chips are tapped', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    fireEvent.press(getByTestId('home-mode-link'));
    fireEvent.press(getByTestId('home-mode-type'));
    expect(mockNavigation.navigate).not.toHaveBeenCalledWith('ScanCamera');
  });

  it('exports MAX_IMAGES === 2 (Bundle B/C/D camera cap)', () => {
    expect(MAX_IMAGES).toBe(2);
  });
});
