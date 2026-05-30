/**
 * Primitive contract — SlideTransition.
 *
 * Contract (plan S0.4):
 *   - Wraps any onboarding step content in an Animated.View keyed on `step` index.
 *   - Animates translateX from ±width → 0 (320ms, cubic-bezier(0.32,0.72,0,1)).
 *   - Direction MIRRORS based on I18nManager.isRTL: LTR slides in from right (+w),
 *     RTL slides in from left (-w).
 *   - Re-renders WITHOUT changing step do not retrigger the slide.
 */
import React from 'react';
import { I18nManager, Text } from 'react-native';
import { render } from '@testing-library/react-native';
import { SlideTransition } from '../../src/components/SlideTransition';

describe('SlideTransition primitive', () => {
  afterEach(() => {
    // Reset the global I18nManager between tests so direction state
    // doesn't leak. The RN mock allows direct assignment in tests.
    (I18nManager as any).isRTL = false;
  });

  it('renders children inside an animated wrapper', () => {
    const { getByText } = render(
      <SlideTransition step={0}>
        <Text>step content</Text>
      </SlideTransition>,
    );
    expect(getByText('step content')).toBeTruthy();
  });

  it('LTR direction: incoming translateX is positive (slides in from right)', () => {
    (I18nManager as any).isRTL = false;
    const { getByTestId } = render(
      <SlideTransition step={1} testID="slide">
        <Text>x</Text>
      </SlideTransition>,
    );
    const node = getByTestId('slide');
    // Animated mock forwards transform values verbatim; we expect the
    // component to expose its starting translateX via a data prop or
    // via a discoverable initial style. The contract: starting offset
    // sign is +1 (right of viewport) when LTR.
    expect(node.props['data-direction']).toBe('ltr');
  });

  it('RTL direction: incoming translateX is negative (slides in from left)', () => {
    (I18nManager as any).isRTL = true;
    const { getByTestId } = render(
      <SlideTransition step={1} testID="slide">
        <Text>x</Text>
      </SlideTransition>,
    );
    const node = getByTestId('slide');
    expect(node.props['data-direction']).toBe('rtl');
  });

  it('re-rendering with SAME step keeps the same direction prop', () => {
    (I18nManager as any).isRTL = false;
    const { getByTestId, rerender } = render(
      <SlideTransition step={2} testID="slide">
        <Text>a</Text>
      </SlideTransition>,
    );
    const before = getByTestId('slide').props['data-direction'];
    rerender(
      <SlideTransition step={2} testID="slide">
        <Text>b</Text>
      </SlideTransition>,
    );
    const after = getByTestId('slide').props['data-direction'];
    expect(after).toBe(before);
  });

  // -----------------------------------------------------------------
  // F-S2.CRITICAL (task #40) regression-guard: initial mount must be
  // visible (translateX:0), NOT offscreen at startOffset.
  //
  // Background: prior implementation initialized translateX to
  // ±width (393px on iPhone). The same-step early-return guard in
  // the useEffect fired on first mount because prevStepRef was
  // initialized to the same step, so the withTiming(0) slide-in
  // never ran. Every fresh-session entry (Google sign-in, Apple
  // sign-in, fresh device) landed on a blank Step01 with content
  // sitting offscreen at translateX=393.
  //
  // These tests fail loudly if the regression returns. The pre-fix
  // behaviour: initial render would expose translateX === ±width
  // in the style prop. The post-fix behaviour: initial render
  // exposes translateX === 0 regardless of LTR/RTL or step value.
  // -----------------------------------------------------------------

  function extractTranslateX(node: any): number | undefined {
    // The mock's useAnimatedStyle returns the updater output
    // directly: { transform: [{ translateX: <number> }] }. The
    // host node receives an array [{ flex:1 }, animatedStyle].
    const style = node.props.style;
    if (!Array.isArray(style)) return undefined;
    for (const layer of style) {
      if (layer && Array.isArray(layer.transform)) {
        for (const op of layer.transform) {
          if (op && typeof op.translateX === 'number') return op.translateX;
        }
      }
    }
    return undefined;
  }

  it('F-S2.CRITICAL: initial mount renders at translateX=0 (visible), NOT at startOffset', () => {
    (I18nManager as any).isRTL = false;
    const { getByTestId } = render(
      <SlideTransition step={1} testID="slide">
        <Text>step content</Text>
      </SlideTransition>,
    );
    const node = getByTestId('slide');
    // Initial mount MUST be at the destination (visible). If this
    // assertion ever fails with a non-zero value, fresh-session
    // entries (Google/Apple/email sign-in, first onboarding step)
    // will render blank — content sitting outside the viewport.
    expect(extractTranslateX(node)).toBe(0);
  });

  it('F-S2.CRITICAL: initial mount is visible even in RTL (Arabic locale)', () => {
    (I18nManager as any).isRTL = true;
    const { getByTestId } = render(
      <SlideTransition step={1} testID="slide">
        <Text>step content</Text>
      </SlideTransition>,
    );
    expect(extractTranslateX(getByTestId('slide'))).toBe(0);
  });

  it('F-S2.CRITICAL: initial mount is visible regardless of the step value', () => {
    // Ahmed's bug hit on step 1 specifically (post-Google sign-in
    // lands on Step01). Pin every initial step value the
    // OnboardingFlow can mount at — the orchestrator can resume on
    // any step via initialStep prop (tests use it; edit-mode uses
    // OnboardingEdit + Step8 entry per RN-Navigation v7 hotfix).
    (I18nManager as any).isRTL = false;
    for (const initialStep of [1, 8, 16, 17]) {
      const { getByTestId, unmount } = render(
        <SlideTransition step={initialStep} testID={`slide-${initialStep}`}>
          <Text>x</Text>
        </SlideTransition>,
      );
      expect(extractTranslateX(getByTestId(`slide-${initialStep}`))).toBe(0);
      unmount();
    }
  });

  it('F-S2.CRITICAL: same-step re-render keeps translateX at 0 (no jump to offscreen)', () => {
    // Guards the parallel risk: even if a future change re-introduces
    // a startOffset-style initial value, this pins that re-renders
    // with the same step must leave translateX alone (no replay,
    // no flash to offscreen).
    (I18nManager as any).isRTL = false;
    const { getByTestId, rerender } = render(
      <SlideTransition step={2} testID="slide">
        <Text>a</Text>
      </SlideTransition>,
    );
    expect(extractTranslateX(getByTestId('slide'))).toBe(0);
    rerender(
      <SlideTransition step={2} testID="slide">
        <Text>b</Text>
      </SlideTransition>,
    );
    expect(extractTranslateX(getByTestId('slide'))).toBe(0);
  });
});
