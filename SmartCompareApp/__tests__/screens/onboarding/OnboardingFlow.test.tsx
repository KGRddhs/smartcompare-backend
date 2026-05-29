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

  it('advances when handleNext fires on a valid step', () => {
    const { getByTestId, queryByTestId } = render(<OnboardingFlow onComplete={noop} />);
    fireEvent.press(getByTestId('onboarding-next'));
    expect(queryByTestId('onboarding-step-1')).toBeNull();
    expect(getByTestId('onboarding-step-2')).toBeTruthy();
  });

  it('decrements when handleBack fires', () => {
    const { getByTestId } = render(<OnboardingFlow onComplete={noop} />);
    fireEvent.press(getByTestId('onboarding-next'));
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
      fireEvent.press(getByTestId('onboarding-next'));
      // The wrap stays mounted across step advance — only its internal
      // step prop changes, which retriggers the slide animation per
      // SlideTransition's contract.
      expect(getByTestId('onboarding-step-slide')).toBeTruthy();
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

  it('calls onComplete when step 17 finishes', () => {
    const onComplete = jest.fn();
    const { getByTestId } = render(
      <OnboardingFlow onComplete={onComplete} initialStep={17} />
    );
    fireEvent.press(getByTestId('onboarding-next'));
    expect(onComplete).toHaveBeenCalledTimes(1);
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
    fireEvent.press(getByTestId('onboarding-next'));
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
