/**
 * Step17Notifications tests — Phase 2 Task 23.
 *
 * "Be the first to know when prices drop" — Allow / Not now. Asked AFTER
 * value built, not at launch. Compact mock notification preview as a
 * visual element. See design spec § 2 row 17 + § 4g audit ("Want
 * price-drop alerts?" → "Be the first to know when prices drop").
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step17Notifications } from '../../../src/screens/onboarding/Step17Notifications';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const requestPermissionsAsyncMock = jest
  .fn()
  .mockResolvedValue({ status: 'granted', granted: true });

jest.mock('expo-notifications', () => ({
  requestPermissionsAsync: () => requestPermissionsAsyncMock(),
  __esModule: true,
}));

beforeEach(() => requestPermissionsAsyncMock.mockClear());

describe('Step17Notifications', () => {
  it('renders the title and mock preview', () => {
    const { getByText, getByTestId } = render(<Step17Notifications onDone={jest.fn()} />);
    expect(getByText('onboarding.s17.title')).toBeTruthy();
    expect(getByTestId('s17-preview')).toBeTruthy();
  });

  it('renders both Allow and "Not now" CTAs', () => {
    const { getByTestId } = render(<Step17Notifications onDone={jest.fn()} />);
    expect(getByTestId('s17-allow')).toBeTruthy();
    expect(getByTestId('s17-not-now')).toBeTruthy();
  });

  it('calls expo-notifications.requestPermissionsAsync on Allow', async () => {
    const onDone = jest.fn();
    const { getByTestId } = render(<Step17Notifications onDone={onDone} />);
    fireEvent.press(getByTestId('s17-allow'));
    // microtask flush for the awaited promise
    await Promise.resolve();
    await Promise.resolve();
    expect(requestPermissionsAsyncMock).toHaveBeenCalledTimes(1);
  });

  it('calls onDone(true) after Allow + permission granted', async () => {
    const onDone = jest.fn();
    const { getByTestId } = render(<Step17Notifications onDone={onDone} />);
    fireEvent.press(getByTestId('s17-allow'));
    await Promise.resolve();
    await Promise.resolve();
    expect(onDone).toHaveBeenCalledWith(true);
  });

  it('calls onDone(false) on Not now without requesting permission', () => {
    const onDone = jest.fn();
    const { getByTestId } = render(<Step17Notifications onDone={onDone} />);
    fireEvent.press(getByTestId('s17-not-now'));
    expect(onDone).toHaveBeenCalledWith(false);
    expect(requestPermissionsAsyncMock).not.toHaveBeenCalled();
  });

  it('calls onDone(false) when permission is denied', async () => {
    requestPermissionsAsyncMock.mockResolvedValueOnce({
      status: 'denied',
      granted: false,
    });
    const onDone = jest.fn();
    const { getByTestId } = render(<Step17Notifications onDone={onDone} />);
    fireEvent.press(getByTestId('s17-allow'));
    await Promise.resolve();
    await Promise.resolve();
    expect(onDone).toHaveBeenCalledWith(false);
  });
});
