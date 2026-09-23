/**
 * W3-3 — MB-NETWORK-CONTRACT-04 (client half; this half closes the finding on
 * its own, no backend change and no flag).
 *
 * THE DEFECT (measured at ed75dc70 / b63a8368)
 * `ShareBottomSheet.handleTargetPress` already forwards
 * `device_fingerprint_hash: deviceFingerprintHash` to `createShare`
 * (ShareBottomSheet.tsx:159), but the ONLY source of that value is the optional
 * prop declared at :43 — and the ONLY mount of the sheet
 * (`ResultsScreen.tsx:830-841`) never passes it (0 `deviceFingerprint` hits in
 * that file). `createShare` posts the input as-is, so `undefined` is dropped by
 * JSON.stringify, the backend's Optional field stays None,
 * `referral_invites.device_fingerprint_hash` is written NULL, and
 * `abuse_detection_service._get_referrer_device_hash` returns None →
 * `is_same_device` False → the SAME_DEVICE control is dead.
 *
 * RED here: C7.
 * PINS (green today AND after the fix, each with a named mutation): C8, C9.
 *
 * Harness: `__tests__/ShareBottomSheet.lifetimeLimit.test.tsx:11-49` (haptics,
 * i18n, referralService mock with a createShare recorder) + a deviceFingerprint
 * recorder. Per RULING R6 the haptics mock carries BOTH NotificationFeedbackType
 * members. `Share` is NOT exported by `__mocks__/react-native.ts` (only
 * `Linking`, :128, whose `canOpenURL` resolves false by design): the resulting
 * TypeError is swallowed by the sheet's INNER try and `onShared` still fires, so
 * every assertion here is on `createShare`'s argument, never on `Share`.
 */
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  impactAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'Success', Error: 'Error' },
  ImpactFeedbackStyle: { Light: 'Light' },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockCreateShare = jest.fn();
jest.mock('../src/services/referralService', () => ({
  createShare: (...args: unknown[]) => mockCreateShare(...args),
  ReferralError: class FakeReferralError extends Error {
    code = 'UNKNOWN';
    status = null;
  },
}));

const FP = 'c'.repeat(64);
const PROP_FP = 'd'.repeat(64);
const mockGetDeviceFingerprint = jest.fn();
jest.mock('../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: (...args: unknown[]) => mockGetDeviceFingerprint(...args),
}));

import ShareBottomSheet from '../src/components/ShareBottomSheet';

const COMPARISON = {
  id: 'cmp-123',
  productA: 'iPhone 15',
  productB: 'Galaxy S24',
  winnerName: 'iPhone 15',
};

const SHARE_RESULT = {
  success: true as const,
  invite_id: 'inv-1',
  share_link: 'https://qaren.app/r/QR-ABCDEF?ref=QR-ABCDEF',
};

beforeEach(() => {
  mockCreateShare.mockReset();
  mockGetDeviceFingerprint.mockReset();
  mockCreateShare.mockResolvedValue(SHARE_RESULT);
  mockGetDeviceFingerprint.mockResolvedValue(FP);
});

describe('W3-3 C7 — share payload carries the device fingerprint (RED at base)', () => {
  it('C7: a share tap on a sheet mounted WITHOUT the prop (as ResultsScreen mounts it) sends a 64-hex hash', async () => {
    // Mutation that reddens this after the fix: drop the in-tap resolution.
    const onShared = jest.fn();
    const { getByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={onShared}
        lifetimeRemaining={2}
      />
    );

    fireEvent.press(getByTestId('share-target-copy'));
    await waitFor(() => expect(mockCreateShare).toHaveBeenCalledTimes(1));

    const payload = mockCreateShare.mock.calls[0][0];
    expect(payload.device_fingerprint_hash).toMatch(/^[a-f0-9]{64}$/);
    expect(payload.device_fingerprint_hash).toBe(FP);
    // Everything else on the wire is unchanged.
    expect(payload.comparison_id).toBe('cmp-123');
    expect(payload.share_target).toBe('copy');
    expect(payload.privacy).toEqual({
      show_name: true,
      show_result: true,
      show_reasons: true,
    });
  });
});

describe('W3-3 share pins', () => {
  it('C8 (pin): an explicit deviceFingerprintHash prop still wins and suppresses the lookup', async () => {
    // Mutation that reddens this: ignore the prop / always resolve.
    const { getByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        deviceFingerprintHash={PROP_FP}
        onClose={jest.fn()}
        onShared={jest.fn()}
        lifetimeRemaining={2}
      />
    );

    fireEvent.press(getByTestId('share-target-copy'));
    await waitFor(() => expect(mockCreateShare).toHaveBeenCalledTimes(1));

    expect(mockCreateShare.mock.calls[0][0].device_fingerprint_hash).toBe(PROP_FP);
    expect(mockGetDeviceFingerprint).not.toHaveBeenCalled();
  });

  it('C9 (pin): a fingerprint failure never blocks the share', async () => {
    // Mutation that reddens this: remove the INNER catch around the resolution
    // — the rejection then hits the outer catch, errorMessage renders and
    // createShare is never called.
    mockGetDeviceFingerprint.mockRejectedValue(new Error('keychain-busy'));
    const onShared = jest.fn();
    const { getByTestId, queryByText } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={onShared}
        lifetimeRemaining={2}
      />
    );

    fireEvent.press(getByTestId('share-target-copy'));
    await waitFor(() => expect(mockCreateShare).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onShared).toHaveBeenCalledWith(SHARE_RESULT));

    expect(mockCreateShare.mock.calls[0][0].device_fingerprint_hash).toBeUndefined();
    // No error copy rendered: neither the raw rejection message nor the
    // generic key (the i18n mock returns keys verbatim).
    expect(queryByText('keychain-busy')).toBeNull();
    expect(queryByText('referrals.share.error.generic')).toBeNull();
  });
});
