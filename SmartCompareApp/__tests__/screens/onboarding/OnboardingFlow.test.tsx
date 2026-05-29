/**
 * OnboardingFlow orchestrator tests — Phase 2 Task 9.
 *
 * The orchestrator owns step state (1-17), renders sub-step components,
 * handles back/next navigation, RTL-aware slide direction, validation gating.
 *
 * See docs/plans/2026-05-06-qaren-ux-redesign-design.md Section 2 for the
 * 17-screen map and Section 1 motion language for the slide-transition spec.
 */

import React from 'react';
import { I18nManager } from 'react-native';
import { render, fireEvent } from '@testing-library/react-native';
import { OnboardingFlow } from '../../../src/screens/onboarding/OnboardingFlow';

// react-native-reanimated is mock-mapped via jest.config.js moduleNameMapper.

// Stub `../../../src/services/api` so this navigation-focused suite doesn't
// drag in expo-image-manipulator (whose ESM source isn't transformed by
// ts-jest). Analytics-event behavior is verified in
// OnboardingFlow.analytics.test.tsx with its own trackEvents mock.
jest.mock('../../../src/services/api', () => ({
  trackEvents: jest.fn().mockResolvedValue(undefined),
}));

// Bundle D Phase 3 device-leg fix: OnboardingFlow now transitively imports
// Step17Notifications → expo-notifications (ESM). Mock at the orchestrator
// test level so the transitive chain transforms cleanly under ts-jest.
jest.mock('expo-notifications', () => ({
  getPermissionsAsync: jest.fn().mockResolvedValue({ status: 'undetermined' }),
  requestPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
  setNotificationHandler: jest.fn(),
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

const noop = () => {};

beforeEach(() => {
  mockLanguage = 'en';
  mockIsRTL = false;
});

describe('OnboardingFlow orchestrator', () => {
  it('renders step 1 (Welcome) by default', () => {
    const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
  });

  it('exposes a 17-step total via the progress bar', () => {
    const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
    const bar = getByTestId('onboarding-progress');
    expect(bar.props['data-total-steps']).toBe(17);
    expect(bar.props['data-current-step']).toBe(1);
  });

  // F-S2.W4.hotfix: Step01Welcome has its own Continue button, so the
  // orchestrator's chrome Next is gated off on Step 1 (was showing as a
  // duplicate). Tests now drive the advance via the per-step CTA
  // (welcome-continue) — same end-to-end path as the device user.
  it('advances when handleNext fires on a valid step', () => {
    const { getByTestId, queryByTestId } = render(<OnboardingFlow onComplete={noop} />);
    fireEvent.press(getByTestId('welcome-continue'));
    expect(queryByTestId('onboarding-step-1')).toBeNull();
    expect(getByTestId('onboarding-step-2')).toBeTruthy();
  });

  it('decrements when handleBack fires', () => {
    const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
    fireEvent.press(getByTestId('welcome-continue'));
    expect(getByTestId('onboarding-step-2')).toBeTruthy();
    fireEvent.press(getByTestId('onboarding-back'));
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
  });

  it('does not advance past step 1 when handleBack fires', () => {
    const { getByTestId, queryByTestId } = render(<OnboardingFlow onComplete={noop} />);
    fireEvent.press(getByTestId('onboarding-back'));
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
    expect(queryByTestId('onboarding-step-0')).toBeNull();
  });

  // F-S2.X1 — SlideTransition chrome wrap. Verify the orchestrator
  // wraps StepContent in a single SlideTransition at the chrome layer
  // (not per-step). The primitive's data-direction prop mirrors
  // I18nManager.isRTL; LTR keeps 'ltr', RTL flips to 'rtl'. Same-step
  // re-renders do not retrigger the slide per the primitive contract.
  describe('F-S2.X1 SlideTransition chrome wrap', () => {
    it('wraps StepContent in <SlideTransition> at the chrome layer (testID onboarding-step-slide)', () => {
      const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
      expect(getByTestId('onboarding-step-slide')).toBeTruthy();
    });

    // SlideTransition reads I18nManager.isRTL directly (not from the
    // useLanguage hook), so the chrome-wrap direction prop is gated on
    // the RN I18nManager mock — flip + restore in each test so state
    // doesn't leak across cases. Same discipline as the primitive's
    // own RTL test suite (SlideTransition.rtl.test.tsx).
    afterEach(() => {
      (I18nManager as any).isRTL = false;
    });

    it('LTR mode: chrome-wrap data-direction = "ltr"', () => {
      (I18nManager as any).isRTL = false;
      mockIsRTL = false;
      const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
      expect(
        getByTestId('onboarding-step-slide').props['data-direction'],
      ).toBe('ltr');
    });

    it('RTL mode: chrome-wrap data-direction = "rtl" (mirror)', () => {
      (I18nManager as any).isRTL = true;
      mockIsRTL = true;
      const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
      expect(
        getByTestId('onboarding-step-slide').props['data-direction'],
      ).toBe('rtl');
    });

    it('chrome-wrap persists across step advance (same SlideTransition keyed by `step`)', () => {
      const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
      expect(getByTestId('onboarding-step-slide')).toBeTruthy();
      // Step 1 has its own Continue (welcome-continue) per
      // STEPS_WITH_OWN_CTA — orchestrator Next is gated off.
      fireEvent.press(getByTestId('welcome-continue'));
      // The wrap stays mounted across step advance — only its internal
      // step prop changes, which retriggers the slide animation per
      // SlideTransition's contract.
      expect(getByTestId('onboarding-step-slide')).toBeTruthy();
    });
  });

  // F-S2.W4.hotfix — gate the orchestrator's Next button on steps that
  // own a primary CTA (1/3/5/12/13/14/15/16/17). The back chevron
  // stays available on every step. Ahmed's W4 device walk reported
  // "stray magnifier + Next" on Step15 — the magnifier was the
  // BackIcon chevron (acceptable; backwards nav useful) but the Next
  // button stacked under "Compare your first product" was a duplicate.
  describe('F-S2.W4.hotfix orchestrator Next gating', () => {
    it('Step 1 (Welcome): orchestrator Next is GONE (Step01 owns its Continue)', () => {
      const { queryByTestId, getByTestId } = render(
        <OnboardingFlow onComplete={noop} />,
      );
      expect(queryByTestId('onboarding-next')).toBeNull();
      // Per-step CTA stays available + back chevron still renders.
      expect(getByTestId('welcome-continue')).toBeTruthy();
      expect(getByTestId('onboarding-back')).toBeTruthy();
    });

    it('Step 15 (Reveal): orchestrator Next is GONE (Step15 owns "Compare your first product")', () => {
      const { queryByTestId, getByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={15} />,
      );
      expect(queryByTestId('onboarding-next')).toBeNull();
      expect(getByTestId('s15-cta')).toBeTruthy();
      expect(getByTestId('onboarding-back')).toBeTruthy();
    });

    it('Step 17 (Notifications): orchestrator Next is GONE (Step17 owns Allow / Maybe later)', () => {
      const { queryByTestId, getByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={17} />,
      );
      expect(queryByTestId('onboarding-next')).toBeNull();
      expect(getByTestId('s17-allow')).toBeTruthy();
      expect(getByTestId('s17-not-now')).toBeTruthy();
    });

    it('Step 4 (Country, no own CTA): orchestrator Next IS rendered', () => {
      const { getByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={4} />,
      );
      // Step 4 has no inline primary CTA — the orchestrator Next
      // carries the advance. Still renders for the user.
      expect(getByTestId('onboarding-next')).toBeTruthy();
    });
  });

  it('disables Next when current step validation fails', () => {
    const { getByTestId } = render(
      <OnboardingFlow onComplete={noop} initialStep={4} />
    );
    expect(getByTestId('onboarding-next').props.disabled).toBe(true);
  });

  it('enables Next once required field is set', () => {
    const { getByTestId } = render(
      <OnboardingFlow onComplete={noop} initialStep={4} />
    );
    fireEvent.press(getByTestId('country-BH'));
    expect(getByTestId('onboarding-next').props.disabled).toBe(false);
  });

  it('exposes RTL direction on the slide wrapper when language is Arabic', () => {
    mockLanguage = 'ar';
    mockIsRTL = true;
    const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
    const wrapper = getByTestId('onboarding-slide-wrapper');
    expect(wrapper.props['data-direction']).toBe('rtl');
  });

  it('uses LTR direction by default', () => {
    const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
    const wrapper = getByTestId('onboarding-slide-wrapper');
    expect(wrapper.props['data-direction']).toBe('ltr');
  });

  // F-S2.W4.hotfix: Step17Notifications has its own Allow / Maybe-later
  // CTAs, so the orchestrator's chrome Next is gated off on Step 17.
  // Pressing s17-not-now triggers onNotificationsDone(false) →
  // setField + handleNext → onComplete (since step 17 === terminalStep).
  it('calls onComplete when step 17 finishes', () => {
    const onComplete = jest.fn();
    const { getByTestId } = render(
      <OnboardingFlow onComplete={onComplete} initialStep={17} />
    );
    fireEvent.press(getByTestId('s17-not-now'));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  // -----------------------------------------------------------------
  // F-S2.step16-skip (task #42) — skip Step 16 Save Advisor when the
  // user is pre-authenticated. App.tsx already gates the Onboarding
  // stack on `isAuthenticated === true`, so the production wiring
  // hard-codes `isAuthenticated={true}` at NewOnboardingHost. The
  // OnboardingFlow prop defaults `false` so the original 17-step
  // sequence is preserved for any future call site.
  // -----------------------------------------------------------------
  describe('F-S2.step16-skip — Step 16 omission when isAuthenticated', () => {
    it('default (anonymous): renders 17-step sequence + denominator 17', () => {
      const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
      const bar = getByTestId('onboarding-progress');
      expect(bar.props['data-total-steps']).toBe(17);
      expect(bar.props['data-current-step']).toBe(1);
      expect(bar.props['data-current-step-index']).toBe(1);
    });

    it('authenticated: renders 16-step sequence + denominator 16 (Step 16 skipped)', () => {
      const { getByTestId } = render(
        <OnboardingFlow onComplete={noop} isAuthenticated />
      );
      const bar = getByTestId('onboarding-progress');
      expect(bar.props['data-total-steps']).toBe(16);
      expect(bar.props['data-current-step']).toBe(1);
      expect(bar.props['data-current-step-index']).toBe(1);
    });

    it('authenticated: Step 15 next-press advances directly to Step 17 (skips Step 16)', () => {
      const { getByTestId, queryByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={15} isAuthenticated />
      );
      expect(getByTestId('onboarding-step-15')).toBeTruthy();
      // Step 15 owns its own CTA — press it to advance.
      fireEvent.press(getByTestId('s15-cta'));
      // Lands on Step 17, NOT Step 16. Step 16 is filtered out of
      // the auth'd traversal sequence.
      expect(getByTestId('onboarding-step-17')).toBeTruthy();
      expect(queryByTestId('onboarding-step-16')).toBeNull();
    });

    it('anonymous: Step 15 next-press lands on Step 16 (sequence preserved)', () => {
      const { getByTestId, queryByTestId } = render(
        // No isAuthenticated prop — defaults to false, original 17-step path.
        <OnboardingFlow onComplete={noop} initialStep={15} />
      );
      fireEvent.press(getByTestId('s15-cta'));
      // Lands on Step 16, NOT Step 17. Original anonymous flow.
      expect(getByTestId('onboarding-step-16')).toBeTruthy();
      expect(queryByTestId('onboarding-step-17')).toBeNull();
    });

    it('authenticated: back from Step 17 lands on Step 15 (skips Step 16)', () => {
      const { getByTestId, queryByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={17} isAuthenticated />
      );
      expect(getByTestId('onboarding-step-17')).toBeTruthy();
      fireEvent.press(getByTestId('onboarding-back'));
      // Retreats to Step 15, NOT Step 16. Sequence-aware.
      expect(getByTestId('onboarding-step-15')).toBeTruthy();
      expect(queryByTestId('onboarding-step-16')).toBeNull();
    });

    it('anonymous: back from Step 17 lands on Step 16 (sequence preserved)', () => {
      const { getByTestId, queryByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={17} />
      );
      fireEvent.press(getByTestId('onboarding-back'));
      // Retreats to Step 16 (original anonymous flow).
      expect(getByTestId('onboarding-step-16')).toBeTruthy();
      expect(queryByTestId('onboarding-step-17')).toBeNull();
    });

    it('authenticated: Step 17 is terminal — pressing s17-not-now calls onComplete (not Step 16 advance)', () => {
      const onComplete = jest.fn();
      const { getByTestId } = render(
        <OnboardingFlow
          onComplete={onComplete}
          initialStep={17}
          isAuthenticated
        />
      );
      fireEvent.press(getByTestId('s17-not-now'));
      // Step 17 is the last entry of AUTHED_STEP_SEQUENCE, so
      // handleNext detects terminal and fires onComplete.
      expect(onComplete).toHaveBeenCalledTimes(1);
    });

    it('authenticated: orchestrator Next chrome stays gated off on Step 17 (no duplicate button)', () => {
      const { queryByTestId, getByTestId } = render(
        <OnboardingFlow onComplete={noop} initialStep={17} isAuthenticated />
      );
      // F-S2.W4.hotfix invariant must hold in the auth'd flow too:
      // Step 17 owns its own CTA, the orchestrator's Next is gated.
      // Regression check that the dynamic sequence didn't accidentally
      // re-introduce the chrome footer's Next button.
      expect(queryByTestId('onboarding-next')).toBeNull();
      expect(getByTestId('s17-allow')).toBeTruthy();
      expect(getByTestId('s17-not-now')).toBeTruthy();
    });
  });

  it('passes accumulated data through onComplete', () => {
    const onComplete = jest.fn();
    const { getByTestId } = render(
      <OnboardingFlow
        onComplete={onComplete}
        initialStep={17}
        initialData={{
          language: 'en',
          country: 'BH',
          age_group: '25-34',
          priorities: ['quality_reliability'],
          budget: 'mid',
          brand_attitude: 'best_of_both',
        }}
      />
    );
    fireEvent.press(getByTestId('s17-not-now'));
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        language: 'en',
        country: 'BH',
        age_group: '25-34',
        priorities: ['quality_reliability'],
        budget: 'mid',
        brand_attitude: 'best_of_both',
      })
    );
  });
});
