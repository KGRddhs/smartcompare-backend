/**
 * OnboardingScreen (legacy 6-step) analytics — Task #60.
 *
 * Mirrors the new-flow analytics contract from Task #53 + #58 so canary
 * dashboards can compare new-vs-legacy cohort performance during the
 * 50→100% ramp decision (Task #48).
 *
 * Events:
 * - `onboarding_started` once on Step 0 mount
 * - `onboarding_step_completed` on each Continue with current step's
 *   slug + step_number (1-based to match new-flow events)
 * - `onboarding_completed` when Step 5 (final) onComplete fires
 *
 * Payload: { step_number, step_name, locale, flow_variant: "legacy" }.
 * step_name slugs are stable English (language/region/priorities/
 * budget/lifestyle/brand) — same shape as new-flow STEP_NAMES.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

// react-native-reanimated is mock-mapped via jest.config.js moduleNameMapper.
// (Same pattern as the existing OnboardingFlow analytics suite — adding
// `jest.mock('react-native-reanimated')` here loses the manual mock's
// proper useSharedValue/useAnimatedStyle shapes.)

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

let mockLanguage: 'en' | 'ar' = 'en';
const switchLanguageMock = jest.fn();
jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: mockLanguage,
    switchLanguage: switchLanguageMock,
  }),
}));

const trackEventsMock = jest.fn().mockResolvedValue(undefined);
const savePreferencesMock = jest.fn().mockResolvedValue({});
jest.mock('../src/services/api', () => ({
  savePreferences: (...args: unknown[]) => savePreferencesMock(...args),
  trackEvents: (events: any[]) => trackEventsMock(events),
}));

import OnboardingScreen from '../src/screens/OnboardingScreen';

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
} as any;

beforeEach(() => {
  jest.clearAllMocks();
  trackEventsMock.mockClear().mockResolvedValue(undefined);
  savePreferencesMock.mockClear().mockResolvedValue({});
  mockLanguage = 'en';
});

describe('OnboardingScreen analytics — Task #60 (legacy mirror)', () => {
  it('fires onboarding_started exactly once on Step 0 mount', () => {
    render(<OnboardingScreen navigation={mockNavigation} />);
    const started = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []).filter(
      (e: any) => e?.event_type === 'onboarding_started'
    );
    expect(started).toHaveLength(1);
    expect(started[0].event_data?.flow_variant).toBe('legacy');
  });

  it('fires onboarding_step_completed on Step 0 → 1 advance', () => {
    const { getByText } = render(<OnboardingScreen navigation={mockNavigation} />);
    trackEventsMock.mockClear();
    fireEvent.press(getByText('onboarding.next'));
    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const completed = events.find(
      (e: any) => e?.event_type === 'onboarding_step_completed'
    );
    expect(completed).toBeDefined();
    expect(completed.event_data?.step_number).toBe(1);
    expect(completed.event_data?.step_name).toBe('language');
    expect(completed.event_data?.flow_variant).toBe('legacy');
    expect(completed.event_data?.locale).toBe('en');
  });

  it('fires the correct slug for each step (region, priorities, budget, lifestyle, brand)', () => {
    const { getByText } = render(<OnboardingScreen navigation={mockNavigation} />);
    // Step 0 → 1
    fireEvent.press(getByText('onboarding.next'));
    // Step 1 → 2 (region needs selection)
    fireEvent.press(getByText('onboarding.region.bahrain'));
    fireEvent.press(getByText('onboarding.next'));
    // Step 2 → 3 (priority needs selection)
    fireEvent.press(getByText('onboarding.priorities.price'));
    fireEvent.press(getByText('onboarding.next'));
    // Step 3 → 4 (budget needs selection)
    fireEvent.press(getByText('onboarding.budget.mid'));
    fireEvent.press(getByText('onboarding.next'));
    // Step 4 → 5 (lifestyle optional, no selection needed)
    fireEvent.press(getByText('onboarding.next'));

    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const stepCompleted = events.filter(
      (e: any) => e?.event_type === 'onboarding_step_completed'
    );
    const slugs = stepCompleted.map((e: any) => e.event_data?.step_name);
    expect(slugs).toEqual(['language', 'region', 'priorities', 'budget', 'lifestyle']);
  });

  it('fires onboarding_completed when Step 5 (final) finishes', async () => {
    const onComplete = jest.fn();
    const { getByText } = render(
      <OnboardingScreen navigation={mockNavigation} onComplete={onComplete} />
    );
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

    await waitFor(() => expect(onComplete).toHaveBeenCalled());

    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const completed = events.find(
      (e: any) => e?.event_type === 'onboarding_completed'
    );
    expect(completed).toBeDefined();
    expect(completed.event_data?.flow_variant).toBe('legacy');
    expect(completed.event_data?.step_number).toBe(6);
    expect(completed.event_data?.step_name).toBe('brand');
  });

  it('reflects ar locale when language is Arabic', () => {
    mockLanguage = 'ar';
    render(<OnboardingScreen navigation={mockNavigation} />);
    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    expect(events.length).toBeGreaterThan(0);
    for (const e of events) {
      expect(e.event_data?.locale).toBe('ar');
    }
  });

  it('does NOT fire onboarding_completed when blocked by validation (e.g. region empty)', () => {
    const { getByText } = render(<OnboardingScreen navigation={mockNavigation} />);
    // Step 0 → 1 (advance)
    fireEvent.press(getByText('onboarding.next'));
    trackEventsMock.mockClear();
    // Step 1 (region) — no selection, press Next: existing screen disables
    // the Next button via `disabled` so the press is a no-op. No new event
    // should fire.
    fireEvent.press(getByText('onboarding.next'));
    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const stepCompleted = events.find(
      (e: any) => e?.event_type === 'onboarding_step_completed'
    );
    expect(stepCompleted).toBeUndefined();
  });
});
