/**
 * ToggleRow component — Bundle A Task 4.4
 *
 * Contract (Bundle A design §6.1 + plan Task 2.6):
 * - tapping anywhere on the row (not just the switch thumb) flips the value
 * - light haptic fires on every flip (selectionAsync)
 * - disabled rows do NOT respond to taps and do NOT fire haptics
 * - accessibilityState reflects { checked, disabled }
 *
 * Why: the previous Profile row design used the bare Switch, which on
 * RTL Android has a tiny hit target on the thumb. Bundle A makes the
 * whole 56-pt row tappable.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  impactAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium' },
}));

import * as Haptics from 'expo-haptics';
import ToggleRow from '../src/components/ToggleRow';

describe('ToggleRow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('flips when the row (outer Touchable) is pressed — not just the switch', () => {
    const onValueChange = jest.fn();
    const { getByTestId } = render(
      <ToggleRow
        label="Notifications"
        value={false}
        onValueChange={onValueChange}
        testID="toggle-notifications"
      />,
    );

    fireEvent.press(getByTestId('toggle-notifications'));

    expect(onValueChange).toHaveBeenCalledTimes(1);
    expect(onValueChange).toHaveBeenCalledWith(true);
  });

  it('fires a light haptic on every flip', () => {
    const { getByTestId } = render(
      <ToggleRow
        label="Notifications"
        value={false}
        onValueChange={jest.fn()}
        testID="toggle-1"
      />,
    );
    fireEvent.press(getByTestId('toggle-1'));
    expect(Haptics.selectionAsync).toHaveBeenCalledTimes(1);
  });

  it('does NOT respond to taps when disabled', () => {
    const onValueChange = jest.fn();
    const { getByTestId } = render(
      <ToggleRow
        label="Notifications"
        value={false}
        onValueChange={onValueChange}
        disabled
        testID="toggle-disabled"
      />,
    );

    fireEvent.press(getByTestId('toggle-disabled'));

    expect(onValueChange).not.toHaveBeenCalled();
    expect(Haptics.selectionAsync).not.toHaveBeenCalled();
  });

  it('reflects current state in accessibilityState', () => {
    const { getByTestId, rerender } = render(
      <ToggleRow
        label="Notifications"
        value={true}
        onValueChange={jest.fn()}
        testID="toggle-acc"
      />,
    );
    const row = getByTestId('toggle-acc');
    expect(row.props.accessibilityState).toEqual({ checked: true, disabled: false });

    rerender(
      <ToggleRow
        label="Notifications"
        value={false}
        onValueChange={jest.fn()}
        disabled
        testID="toggle-acc"
      />,
    );
    expect(row.props.accessibilityState).toEqual({ checked: false, disabled: true });
  });

  it('flips to false when value is currently true', () => {
    const onValueChange = jest.fn();
    const { getByTestId } = render(
      <ToggleRow
        label="Notifications"
        value={true}
        onValueChange={onValueChange}
        testID="toggle-on"
      />,
    );
    fireEvent.press(getByTestId('toggle-on'));
    expect(onValueChange).toHaveBeenCalledWith(false);
  });

  it('swallows haptic failure (no throw) and still calls onValueChange', () => {
    (Haptics.selectionAsync as jest.Mock).mockImplementationOnce(() => {
      throw new Error('haptic backend dead');
    });
    const onValueChange = jest.fn();
    const { getByTestId } = render(
      <ToggleRow
        label="Notifications"
        value={false}
        onValueChange={onValueChange}
        testID="toggle-haptic-fail"
      />,
    );

    expect(() => fireEvent.press(getByTestId('toggle-haptic-fail'))).not.toThrow();
    expect(onValueChange).toHaveBeenCalledWith(true);
  });
});
