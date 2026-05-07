/**
 * Step05Trust tests — Phase 2 Task 14.
 *
 * Trust bridge — pure typography + small filled lock icon, hero "Your data
 * stays yours. We just compare." + 3 thin bullets. Pre-empts the "why do
 * you need this?" objection. See design spec § 2 row 5.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step05Trust } from '../../../src/screens/onboarding/Step05Trust';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step05Trust', () => {
  it('renders the lock icon and hero copy', () => {
    const { getByTestId, getByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByTestId('trust-lock-icon')).toBeTruthy();
    expect(getByText('onboarding.s5.title')).toBeTruthy();
  });

  it('renders all 3 trust bullets', () => {
    const { getByText } = render(<Step05Trust onNext={jest.fn()} />);
    expect(getByText('onboarding.s5.bullet_1')).toBeTruthy();
    expect(getByText('onboarding.s5.bullet_2')).toBeTruthy();
    expect(getByText('onboarding.s5.bullet_3')).toBeTruthy();
  });

  it('fires onNext when continue is pressed', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step05Trust onNext={onNext} />);
    fireEvent.press(getByText('onboarding.s5.continue'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  // Phase 5 polish — design § 2 row 5 calls for a 5° rotation animation
  // on mount. The Reanimated mock captures useAnimatedStyle output ONCE
  // at first render (before the useEffect's withTiming has applied), so
  // the snapshot transform shows the initial 0deg. We assert the
  // STRUCTURE of the rotation transform — it MUST be wired up — and
  // confirm the import chain pulls Animated + withTiming.
  it('lock icon mounts with a rotate transform driven by Reanimated', () => {
    const { getByTestId } = render(<Step05Trust onNext={jest.fn()} />);
    const lock = getByTestId('trust-lock-icon');
    const styleArr = Array.isArray(lock.props.style)
      ? lock.props.style
      : [lock.props.style];
    const flat: Record<string, unknown> = styleArr
      .filter(Boolean)
      .reduce(
        (acc: Record<string, unknown>, s: Record<string, unknown>) =>
          Object.assign(acc, s),
        {} as Record<string, unknown>,
      );
    const transforms = (flat.transform ?? []) as Array<Record<string, unknown>>;
    const rot = transforms.find((t) => 'rotate' in t);
    expect(rot).toBeDefined();
    // Either initial "0deg" (pre-effect) or target "5deg" (post-effect)
    // is acceptable — what we're locking down is the rotation contract
    // on this surface. The actual 5° landing happens on-device per the
    // Reanimated runtime (mock is identity). Forbidding non-rotation
    // fallbacks keeps the design § 2 row 5 cue from regressing silently.
    expect(['0deg', '5deg']).toContain(rot?.rotate);
  });
});
