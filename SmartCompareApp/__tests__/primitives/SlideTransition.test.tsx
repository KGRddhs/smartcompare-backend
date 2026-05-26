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
});
