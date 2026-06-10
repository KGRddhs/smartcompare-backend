/**
 * OnboardingFlow Bundle E — 17-step traversal test.
 *
 * Stays compatible with the existing onboarding test suite (which targets the
 * older OnboardingScreen). This file specifically asserts the Bundle E
 * contract:
 *
 *   - Mount at step 1 → testID "onboarding-step-1" present
 *   - Continue advances step monotonically through 1 → 17
 *   - Steps requiring data (2 language, 4 country, 8 priorities, 9 budget,
 *     10 brand, 11 attribution) are pre-seeded via initialData so the
 *     traversal does not stall at invalid-state Continue buttons.
 *   - onboarding_started fires ONCE on mount (Bundle D 1.F.3 invariant)
 *   - onboarding_step_completed fires BEFORE setStep (payload reflects the
 *     FINISHED step, per CLAUDE.md Onboarding analytics contract)
 *   - onboarding_completed fires on Step 17 Finish
 */
import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';
import { OnboardingFlow } from '../src/screens/onboarding/OnboardingFlow';
import type { OnboardingFlowData } from '../src/screens/onboarding/types';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string, opts?: any) => opts?.defaultValue ?? k }),
}));

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en', switchLanguage: jest.fn() }),
}));

const trackEvents = jest.fn().mockResolvedValue(undefined);
jest.mock('../src/services/api', () => ({
  trackEvents: (...args: any[]) => trackEvents(...args),
}));

// All seeded data needed to make every isStepValid case return true so the
// traversal can run to completion without stopping at invalid Continue.
// Discriminated-union fields (language, country, age_group, gender, budget,
// brand_attitude, attribution_source) need per-field literal narrowing.
// priorities stays string[] (mutable). The outer object is asserted as
// Partial<OnboardingFlowData> rather than `as const` (which would freeze
// the priorities array readonly and break the field's mutable type).
const seededData: Partial<OnboardingFlowData> = {
  language: 'en',
  country: 'BH',
  age_group: '25-34',
  gender: 'Male',
  priorities: ['quality'],
  budget: 'mid',
  brand_attitude: 'trust_known_brands',
  attribution_source: 'friend',
};

describe('OnboardingFlow — Bundle E 17-step traversal', () => {
  beforeEach(() => {
    trackEvents.mockClear();
  });

  it('mounts at step 1 with testID onboarding-step-1', () => {
    const { getByTestId } = render(
      <OnboardingFlow onComplete={jest.fn()} initialData={seededData} />,
    );
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
  });

  it('fires onboarding_started exactly once on mount', () => {
    render(<OnboardingFlow onComplete={jest.fn()} initialData={seededData} />);
    const startedCalls = trackEvents.mock.calls.filter((c) =>
      c[0]?.[0]?.event_type === 'onboarding_started',
    );
    expect(startedCalls.length).toBe(1);
    expect(startedCalls[0][0][0].event_data.step_number).toBe(1);
  });

  it('Continue advances through the production sequence and fires onComplete on Finish', () => {
    // Production mounts OnboardingFlow with isAuthenticated={true} (Step 16
    // sign-in is skipped — App.tsx only reaches the onboarding stack when the
    // user is already authed). Several steps carry their OWN CTA and suppress
    // the orchestrator 'onboarding-next' (STEPS_WITH_OWN_CTA = 1,3,5,12,13,14,
    // 15,16,17); Step 14 auto-advances on a stage timer. This helper presses
    // the correct advance affordance per step so the traversal is faithful to
    // how the flow actually runs. B.1 F3.6.
    jest.useFakeTimers();
    try {
      const onComplete = jest.fn();
      const { getByTestId } = render(
        <OnboardingFlow
          onComplete={onComplete}
          initialData={seededData}
          isAuthenticated
        />,
      );

      // Authed sequence: Step 16 dropped.
      const SEQUENCE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17];
      // Per-step advance testID; steps absent here use 'onboarding-next'.
      const OWN_CTA: Record<number, string> = {
        1: 'welcome-continue',
        3: 's3-continue',
        5: 'trust-continue',
        12: 's12-continue',
        13: 's13-cta',
        15: 's15-cta',
        17: 's17-not-now',
      };

      for (const step of SEQUENCE) {
        expect(getByTestId(`onboarding-step-${step}`)).toBeTruthy();
        if (step === 14) {
          // Theatrical loading auto-advances via 4 stage timers + min-display
          // floor; drain all pending timers to reach onComplete.
          act(() => {
            jest.runOnlyPendingTimers();
            jest.runOnlyPendingTimers();
            jest.runOnlyPendingTimers();
            jest.runOnlyPendingTimers();
            jest.runOnlyPendingTimers();
          });
          continue;
        }
        const testID = OWN_CTA[step] ?? 'onboarding-next';
        act(() => {
          fireEvent.press(getByTestId(testID));
        });
      }

      expect(onComplete).toHaveBeenCalledTimes(1);
      const arg = onComplete.mock.calls[0][0];
      expect(arg.language).toBe('en');
      expect(arg.country).toBe('BH');
      expect(arg.priorities).toEqual(['quality']);
    } finally {
      jest.useRealTimers();
    }
  });

  it('onboarding_step_completed payload reflects FINISHED step, not next step', () => {
    // CLAUDE.md "Onboarding analytics" contract: the event is fired BEFORE
    // setStep so payload.step_number == the step the user just finished.
    const { getByTestId } = render(
      <OnboardingFlow onComplete={jest.fn()} initialData={seededData} />,
    );
    // Step 1 (Welcome) is in STEPS_WITH_OWN_CTA — it advances via its own
    // 'welcome-continue' button, not the orchestrator's 'onboarding-next'.
    act(() => {
      fireEvent.press(getByTestId('welcome-continue'));
    });
    // Should now be on step 2; event must reflect step 1.
    const completedCalls = trackEvents.mock.calls.filter((c) =>
      c[0]?.[0]?.event_type === 'onboarding_step_completed',
    );
    expect(completedCalls.length).toBe(1);
    expect(completedCalls[0][0][0].event_data.step_number).toBe(1);
    expect(getByTestId('onboarding-step-2')).toBeTruthy();
  });

  it('onboarding_completed fires on Step 17 Finish', () => {
    const { getByTestId } = render(
      <OnboardingFlow
        onComplete={jest.fn()}
        initialStep={17}
        initialData={seededData}
      />,
    );
    expect(getByTestId('onboarding-step-17')).toBeTruthy();
    // Step 17 (Notifications) has its own CTAs (s17-allow / s17-not-now) and
    // suppresses 'onboarding-next'. "Not now" is the synchronous completion
    // path that fires the orchestrator onComplete via onDone(false).
    act(() => {
      fireEvent.press(getByTestId('s17-not-now'));
    });
    const completedFlow = trackEvents.mock.calls.filter((c) =>
      c[0]?.[0]?.event_type === 'onboarding_completed',
    );
    expect(completedFlow.length).toBe(1);
  });

  it('Back button decrements step but does NOT go below 1', () => {
    const { getByTestId } = render(
      <OnboardingFlow
        onComplete={jest.fn()}
        initialStep={3}
        initialData={seededData}
      />,
    );
    expect(getByTestId('onboarding-step-3')).toBeTruthy();
    act(() => { fireEvent.press(getByTestId('onboarding-back')); });
    expect(getByTestId('onboarding-step-2')).toBeTruthy();
    act(() => { fireEvent.press(getByTestId('onboarding-back')); });
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
    act(() => { fireEvent.press(getByTestId('onboarding-back')); });
    // Floor at step 1.
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
  });

  it('slide wrapper exposes data-direction matching isRTL', () => {
    const { getByTestId } = render(
      <OnboardingFlow onComplete={jest.fn()} initialData={seededData} />,
    );
    const wrapper = getByTestId('onboarding-slide-wrapper');
    expect(wrapper.props['data-direction']).toBe('ltr');
  });
});
