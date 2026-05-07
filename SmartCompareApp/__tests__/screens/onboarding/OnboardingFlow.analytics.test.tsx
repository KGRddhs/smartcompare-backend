/**
 * OnboardingFlow analytics — Task #53.
 *
 * Verifies the orchestrator fires the canary-monitoring events:
 * - `onboarding_started` on Step 1 mount (deduped per session)
 * - `onboarding_step_completed` on each Continue advance
 * - `onboarding_completed` when Step 17 finishes
 *
 * Payload includes `step_number`, `step_name`, plus a session token so
 * the backend can dedup and the canary dashboards can compute drop-off
 * heatmaps. Calls go through trackEvents (POST /api/v1/events,
 * auth-optional, fire-and-forget) per CLAUDE.md feedback_routes.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

const trackEventsMock = jest.fn().mockResolvedValue(undefined);
jest.mock('../../../src/services/api', () => ({
  trackEvents: (
    events: Array<{ event_type: string; event_data?: Record<string, unknown> }>
  ) => trackEventsMock(events),
}));

let mockLanguage: 'en' | 'ar' = 'en';
let mockIsRTL = false;
jest.mock('../../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: mockLanguage,
    isRTL: mockIsRTL,
    switchLanguage: jest.fn(),
  }),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { OnboardingFlow } from '../../../src/screens/onboarding/OnboardingFlow';

beforeEach(() => {
  trackEventsMock.mockClear();
  mockLanguage = 'en';
  mockIsRTL = false;
});

describe('OnboardingFlow analytics — Task #53', () => {
  it('fires onboarding_started exactly once on Step 1 mount', () => {
    render(<OnboardingFlow onComplete={jest.fn()} />);
    const startedCalls = trackEventsMock.mock.calls.filter((c) =>
      c[0]?.[0]?.event_type === 'onboarding_started'
    );
    expect(startedCalls).toHaveLength(1);
  });

  it('fires onboarding_step_completed on Continue tap with step_number', () => {
    const { getByTestId } = render(<OnboardingFlow onComplete={jest.fn()} />);
    trackEventsMock.mockClear();
    fireEvent.press(getByTestId('onboarding-next'));
    const stepEvents = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const stepCompleted = stepEvents.find(
      (e: any) => e?.event_type === 'onboarding_step_completed'
    );
    expect(stepCompleted).toBeDefined();
    expect(stepCompleted.event_data?.step_number).toBe(1);
    expect(typeof stepCompleted.event_data?.step_name).toBe('string');
  });

  it('includes locale on every event payload for cohort segmentation', () => {
    render(<OnboardingFlow onComplete={jest.fn()} />);
    const allEvents = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    expect(allEvents.length).toBeGreaterThan(0);
    for (const e of allEvents) {
      expect(e.event_data?.locale).toBe('en');
    }
  });

  it('reflects ar locale when language is Arabic', () => {
    mockLanguage = 'ar';
    mockIsRTL = true;
    render(<OnboardingFlow onComplete={jest.fn()} />);
    const allEvents = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    for (const e of allEvents) {
      expect(e.event_data?.locale).toBe('ar');
    }
  });

  it('fires onboarding_completed when Step 17 finishes', () => {
    const { getByTestId } = render(
      <OnboardingFlow onComplete={jest.fn()} initialStep={17} />
    );
    trackEventsMock.mockClear();
    fireEvent.press(getByTestId('onboarding-next'));
    const allEvents = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const completed = allEvents.find(
      (e: any) => e?.event_type === 'onboarding_completed'
    );
    expect(completed).toBeDefined();
  });

  it('does NOT fire onboarding_completed when blocked from advancing past 17', () => {
    // Force a step that has invalid data; advance is blocked.
    const { getByTestId } = render(
      <OnboardingFlow onComplete={jest.fn()} initialStep={4} />
    );
    trackEventsMock.mockClear();
    // Step 4 needs country selected — pressing Next without selection
    // should not fire any step_completed event (the orchestrator
    // returns early in handleNext when valid is false).
    fireEvent.press(getByTestId('onboarding-next'));
    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const completed = events.find(
      (e: any) =>
        e?.event_type === 'onboarding_step_completed' ||
        e?.event_type === 'onboarding_completed'
    );
    expect(completed).toBeUndefined();
  });

  it('fires step_completed event with step_number 4 once Bahrain is selected', () => {
    const { getByTestId } = render(
      <OnboardingFlow onComplete={jest.fn()} initialStep={4} />
    );
    trackEventsMock.mockClear();
    fireEvent.press(getByTestId('country-bahrain'));
    fireEvent.press(getByTestId('onboarding-next'));
    const events = trackEventsMock.mock.calls.flatMap((c) => c[0] ?? []);
    const completed = events.find(
      (e: any) => e?.event_type === 'onboarding_step_completed'
    );
    expect(completed).toBeDefined();
    expect(completed.event_data?.step_number).toBe(4);
  });
});
