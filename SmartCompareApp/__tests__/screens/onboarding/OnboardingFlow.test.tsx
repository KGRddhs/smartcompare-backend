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
import { render, fireEvent } from '@testing-library/react-native';
import { OnboardingFlow } from '../../../src/screens/onboarding/OnboardingFlow';

// react-native-reanimated is mock-mapped via jest.config.js moduleNameMapper.

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
    fireEvent.press(getByTestId('country-bahrain'));
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
