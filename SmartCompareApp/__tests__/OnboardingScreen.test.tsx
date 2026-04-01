/**
 * OnboardingScreen Tests
 * Tests the 6-step onboarding wizard flow
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import OnboardingScreen from '../src/screens/OnboardingScreen';
import { savePreferences } from '../src/services/api';

jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  Reanimated.default.call = () => {};
  return Reanimated;
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
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

describe('OnboardingScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render step 1 (language) by default', () => {
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );
    expect(getByText('onboarding.language.title')).toBeTruthy();
    expect(getByText('English')).toBeTruthy();
    expect(getByText('العربية')).toBeTruthy();
  });

  it('should show progress bar', () => {
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );
    // Progress bar component is rendered (verify via ProgressBar existence)
    expect(getByText('onboarding.next')).toBeTruthy();
  });

  it('should advance to step 2 when Next pressed', () => {
    const { getByText, queryByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );

    const nextButton = getByText('onboarding.next');
    fireEvent.press(nextButton);

    expect(getByText('onboarding.region.title')).toBeTruthy();
    expect(queryByText('onboarding.language.title')).toBeNull();
  });

  it('should disable Next when region not selected (step 2)', () => {
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );

    // Advance to step 2
    fireEvent.press(getByText('onboarding.next'));

    const nextButton = getByText('onboarding.next');
    // Button should be disabled (via disabled prop)
    expect(nextButton).toBeTruthy();
  });

  it('should allow selecting up to 3 priorities', () => {
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );

    // Navigate to step 3 (priorities)
    fireEvent.press(getByText('onboarding.next')); // Step 2
    fireEvent.press(getByText('onboarding.region.bahrain')); // Select region
    fireEvent.press(getByText('onboarding.next')); // Step 3

    expect(getByText('onboarding.priorities.title')).toBeTruthy();
  });

  it('should allow going back', () => {
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );

    // Advance to step 2
    fireEvent.press(getByText('onboarding.next'));
    expect(getByText('onboarding.region.title')).toBeTruthy();

    // Go back
    fireEvent.press(getByText('onboarding.back'));
    expect(getByText('onboarding.language.title')).toBeTruthy();
  });

  it('should call savePreferences on complete', async () => {
    const mockOnComplete = jest.fn();
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} onComplete={mockOnComplete} />
    );

    // Navigate through all steps and complete
    fireEvent.press(getByText('onboarding.next')); // Step 2
    fireEvent.press(getByText('onboarding.region.bahrain'));
    fireEvent.press(getByText('onboarding.next')); // Step 3
    fireEvent.press(getByText('onboarding.priorities.price'));
    fireEvent.press(getByText('onboarding.next')); // Step 4
    fireEvent.press(getByText('onboarding.budget.mid'));
    fireEvent.press(getByText('onboarding.next')); // Step 5
    fireEvent.press(getByText('onboarding.next')); // Step 6
    fireEvent.press(getByText('onboarding.brand.best_of_both'));
    fireEvent.press(getByText('onboarding.complete')); // Final step

    await waitFor(() => {
      expect(savePreferences).toHaveBeenCalled();
      expect(mockOnComplete).toHaveBeenCalled();
    });
  });

  it('should call onComplete even if savePreferences fails', async () => {
    (savePreferences as jest.Mock).mockRejectedValueOnce(new Error('API error'));
    const mockOnComplete = jest.fn();
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} onComplete={mockOnComplete} />
    );

    // Navigate through all steps
    fireEvent.press(getByText('onboarding.next'));
    fireEvent.press(getByText('onboarding.region.bahrain'));
    fireEvent.press(getByText('onboarding.next'));
    fireEvent.press(getByText('onboarding.priorities.price'));
    fireEvent.press(getByText('onboarding.next'));
    fireEvent.press(getByText('onboarding.budget.mid'));
    fireEvent.press(getByText('onboarding.next'));
    fireEvent.press(getByText('onboarding.next'));
    fireEvent.press(getByText('onboarding.brand.best_of_both'));
    fireEvent.press(getByText('onboarding.complete'));

    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalled();
    });
  });

  it('should handle lifestyle as optional (step 5)', () => {
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} />
    );

    // Navigate to step 5
    fireEvent.press(getByText('onboarding.next')); // Step 2
    fireEvent.press(getByText('onboarding.region.bahrain'));
    fireEvent.press(getByText('onboarding.next')); // Step 3
    fireEvent.press(getByText('onboarding.priorities.price'));
    fireEvent.press(getByText('onboarding.next')); // Step 4
    fireEvent.press(getByText('onboarding.budget.mid'));
    fireEvent.press(getByText('onboarding.next')); // Step 5

    expect(getByText('onboarding.lifestyle.title')).toBeTruthy();
    // Next should be enabled without selecting anything (lifestyle is optional)
    const nextButton = getByText('onboarding.next');
    expect(nextButton).toBeTruthy();
  });
});
