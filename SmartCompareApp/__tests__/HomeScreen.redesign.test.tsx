/**
 * HomeScreen redesign tests — Phase 3 Task 26.
 *
 * Camera-first card layout per design § 4a. Verifies the structural
 * changes ONLY — full SSE/camera flow tests live in HomeScreen.test.ts.
 *
 * Contract:
 * - Camera viewfinder lives inside a card with rounded corners (testID
 *   `home-camera-card`)
 * - 3-mode equal chips below the card: Scan / Link / Type, with an
 *   active-state dot indicator
 * - Compressed hero "Compare anything." not the old large logo
 * - Freemium counter copy: "{n} free comparisons left this month" — never
 *   "X of Y used" (per § 4g audit)
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
  // useFocusEffect's callback runs the on-focus side-effects (loadUser,
  // checkServer, etc). The host functions are declared via `const`
  // later in the component so eager invocation hits a TDZ. Tests for
  // structure don't need the side-effects, so we no-op.
  useFocusEffect: jest.fn(),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(() => Promise.resolve(null)),
  setItem: jest.fn(() => Promise.resolve()),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string; n?: number }) =>
      // For redesign tests we just echo the key; the i18n suite verifies
      // the actual EN/AR strings exist & follow the § 4g audit rules.
      typeof opts?.n === 'number' ? `${key}|n=${opts.n}` : key,
  }),
}));

import HomeScreen from '../src/screens/HomeScreen';

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
} as any;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('HomeScreen redesign — Phase 3 Task 26', () => {
  it('renders the camera card host (camera-first layout)', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    expect(getByTestId('home-camera-card')).toBeTruthy();
  });

  it('renders all 3 mode chips: scan, link, type', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    expect(getByTestId('home-mode-scan')).toBeTruthy();
    expect(getByTestId('home-mode-link')).toBeTruthy();
    expect(getByTestId('home-mode-type')).toBeTruthy();
  });

  it('marks the active mode chip with accessibilityState.selected=true', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    // Default mode is 'scan'
    expect(getByTestId('home-mode-scan').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('home-mode-link').props.accessibilityState?.selected).toBe(false);
    expect(getByTestId('home-mode-type').props.accessibilityState?.selected).toBe(false);
  });

  it('switches active mode chip when user taps Link', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    fireEvent.press(getByTestId('home-mode-link'));
    expect(getByTestId('home-mode-scan').props.accessibilityState?.selected).toBe(false);
    expect(getByTestId('home-mode-link').props.accessibilityState?.selected).toBe(true);
  });

  it('renders the hero "Compare anything." copy on mount', () => {
    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);
    expect(getByText('home.hero')).toBeTruthy();
  });

  it('shows the "X free comparisons left this month" copy via the counter slot', () => {
    const { getByTestId } = render(<HomeScreen navigation={mockNavigation} />);
    // The redesign exposes the counter in its own host node so QA can
    // check the slot is wired even when the visual ComparisonCounter
    // component is mocked.
    expect(getByTestId('home-counter-slot')).toBeTruthy();
  });
});
