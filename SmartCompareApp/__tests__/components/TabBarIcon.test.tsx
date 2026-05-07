/**
 * TabBarIcon tests — Phase 3 Task 32.
 *
 * Wraps a tab-bar icon with active-state visuals per design § 4c:
 * focused → emerald + small emerald dot below + filled icon.
 * unfocused → filled black at 60% opacity, no dot.
 * On-device the focused icon also scale-bounces 1.0 → 1.15 → 1.0;
 * unit tests cover the static state contract.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { TabBarIcon } from '../../src/components/TabBarIcon';

const StubIcon = ({ size, color }: { size: number; color: string }) =>
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  require('react').createElement('StubIcon', { size, color });

describe('TabBarIcon', () => {
  it('renders the dot indicator when focused', () => {
    const { getByTestId } = render(
      <TabBarIcon
        focused
        size={24}
        Icon={StubIcon}
        testID="tab"
      />
    );
    expect(getByTestId('tab-dot')).toBeTruthy();
  });

  it('hides the dot indicator when not focused', () => {
    const { queryByTestId } = render(
      <TabBarIcon
        focused={false}
        size={24}
        Icon={StubIcon}
        testID="tab"
      />
    );
    expect(queryByTestId('tab-dot')).toBeNull();
  });

  it('passes the focused color (emerald) to the icon when focused', () => {
    const { UNSAFE_getByType } = render(
      <TabBarIcon focused size={24} Icon={StubIcon} testID="tab" />
    );
    const stub = UNSAFE_getByType('StubIcon' as any);
    expect(stub.props.color).toBe('#10B981');
  });

  it('passes a darker color to the icon when not focused', () => {
    const { UNSAFE_getByType } = render(
      <TabBarIcon focused={false} size={24} Icon={StubIcon} testID="tab" />
    );
    const stub = UNSAFE_getByType('StubIcon' as any);
    expect(stub.props.color).not.toBe('#10B981');
    // Inactive is black (or any non-emerald dark) — we just assert it's
    // a hex string starting with # so the contract is captured without
    // pinning to one specific opacity implementation.
    expect(stub.props.color).toMatch(/^(#|rgba\()/);
  });
});
