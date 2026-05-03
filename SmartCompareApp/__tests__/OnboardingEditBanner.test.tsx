/**
 * Tests for the "These were inferred from your background" banner that
 * appears when the user opens the Onboarding screen in edit mode from
 * StyleProfileCard. The banner should NOT appear in first-time onboarding
 * or in normal "edit preferences" flow.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import OnboardingScreen from '../src/screens/OnboardingScreen';
import { savePreferences } from '../src/services/api';

jest.mock('react-native-reanimated');

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock('../src/components/ProgressBar', () => ({
  ProgressBar: ({ progress }: { progress: number }) =>
    require('react').createElement('View', { progress }),
}));

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: 'en',
    switchLanguage: jest.fn(),
  }),
}));

jest.mock('../src/services/api', () => ({
  savePreferences: jest.fn().mockResolvedValue({}),
}));

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
} as any;

describe('OnboardingScreen — inferred preferences banner', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does NOT render banner in first-time onboarding (no route.params)', () => {
    const { queryByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );
    expect(queryByText('profile.styleProfile.banner')).toBeNull();
  });

  it('does NOT render banner when opened in edit mode without styleProfile source', () => {
    const route = { params: { mode: 'edit' } } as any;
    const { queryByText } = render(
      <OnboardingScreen navigation={mockNavigation} route={route} />
    );
    expect(queryByText('profile.styleProfile.banner')).toBeNull();
  });

  it('renders banner when opened in edit mode from styleProfile source', () => {
    const route = { params: { mode: 'edit', source: 'styleProfile' } } as any;
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} route={route} />
    );
    expect(getByText('profile.styleProfile.banner')).toBeTruthy();
  });
});
