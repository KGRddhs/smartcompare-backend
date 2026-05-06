/**
 * ReferralStatusCard tests (F4.5)
 *
 * Covers the 4 render branches:
 *  - loading (initial)
 *  - unavailable (any error → silent hide; ENABLE_REFERRAL_SYSTEM off → 503)
 *  - happy path with full status data
 *  - credits ribbon: hidden when 0, shown when >0
 *
 * Mocks getReferralStatus at the import boundary, drives each path with
 * mockResolvedValueOnce / mockRejectedValueOnce.
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import ReferralStatusCard from '../src/components/ReferralStatusCard';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, any>) => {
      if (opts) {
        const argSummary = Object.entries(opts)
          .filter(([k]) => k !== 'defaultValue')
          .map(([, v]) => v)
          .join('|');
        return `${key}|${argSummary}`;
      }
      return key;
    },
  }),
}));

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'success', Error: 'error' },
}));

const mockGetStatus = jest.fn();
class FakeReferralError extends Error {
  code: string;
  status: number | null;
  constructor(message: string, code: string, status: number | null) {
    super(message);
    this.name = 'ReferralError';
    this.code = code;
    this.status = status;
  }
}

jest.mock('../src/services/referralService', () => ({
  getReferralStatus: (...args: any[]) => mockGetStatus(...args),
  ReferralError: class extends Error {
    code: string;
    status: number | null;
    constructor(message: string, code: string, status: number | null) {
      super(message);
      this.code = code;
      this.status = status;
    }
  },
}));

const FULL_STATUS = {
  referral_code: 'QR-ABC123',
  weekly_invites_used: 1,
  weekly_invites_remaining: 2,
  monthly_bonus_comparisons: 5,
  deep_review_credits_available: 2,
  total_lifetime_redemptions: 3,
};

const ZERO_CREDITS_STATUS = {
  ...FULL_STATUS,
  deep_review_credits_available: 0,
};

describe('ReferralStatusCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the loading indicator while getReferralStatus is in flight', () => {
    let resolveOnce: (value: any) => void = () => {};
    mockGetStatus.mockImplementationOnce(
      () => new Promise((r) => { resolveOnce = r; })
    );
    const { getByLabelText } = render(<ReferralStatusCard />);
    expect(getByLabelText('referrals.status.loading')).toBeTruthy();
    resolveOnce(FULL_STATUS);
  });

  it('hides the card on 503 (feature flag off)', async () => {
    mockGetStatus.mockRejectedValueOnce(
      new FakeReferralError('disabled', 'FEATURE_DISABLED', 503)
    );
    const { queryByText, queryByLabelText } = render(<ReferralStatusCard />);
    await waitFor(() => {
      expect(mockGetStatus).toHaveBeenCalled();
    });
    // After error settles, neither title nor loading label remain
    await waitFor(() => {
      expect(queryByLabelText('referrals.status.loading')).toBeNull();
    });
    expect(queryByText('referrals.status.title')).toBeNull();
  });

  it('hides the card on 401 (anonymous user)', async () => {
    mockGetStatus.mockRejectedValueOnce(
      new FakeReferralError('unauth', 'AUTH_REQUIRED', 401)
    );
    const { queryByText } = render(<ReferralStatusCard />);
    await waitFor(() => expect(mockGetStatus).toHaveBeenCalled());
    await waitFor(() => {
      expect(queryByText('referrals.status.title')).toBeNull();
    });
  });

  it('renders code + 3 stat rows on happy path', async () => {
    mockGetStatus.mockResolvedValueOnce(FULL_STATUS);
    const { findByText } = render(<ReferralStatusCard />);
    expect(await findByText('referrals.status.title')).toBeTruthy();
    expect(await findByText('QR-ABC123')).toBeTruthy();
    // Weekly stat: t('referrals.status.weeklyUsed', {used:1, total:3}) → 'referrals.status.weeklyUsed|1|3'
    expect(await findByText(/referrals\.status\.weeklyUsed\|1\|3/)).toBeTruthy();
    // Bonus value: +5
    expect(await findByText(/referrals\.status\.bonusValue\|5/)).toBeTruthy();
    // Lifetime value: 3
    expect(await findByText(/referrals\.status\.lifetimeValue\|3/)).toBeTruthy();
  });

  it('renders the Deep Review credits ribbon when count > 0', async () => {
    mockGetStatus.mockResolvedValueOnce(FULL_STATUS);
    const { findByText } = render(<ReferralStatusCard />);
    expect(await findByText(/referrals\.status\.creditsAvailable\|2/)).toBeTruthy();
  });

  it('hides the Deep Review credits ribbon when count is 0', async () => {
    mockGetStatus.mockResolvedValueOnce(ZERO_CREDITS_STATUS);
    const { findByText, queryByText } = render(<ReferralStatusCard />);
    // Wait for happy path render
    await findByText('referrals.status.title');
    expect(queryByText(/referrals\.status\.creditsAvailable/)).toBeNull();
  });

  it('refetches when refreshKey changes', async () => {
    mockGetStatus.mockResolvedValue(FULL_STATUS);
    const { rerender } = render(<ReferralStatusCard refreshKey={1} />);
    await waitFor(() => expect(mockGetStatus).toHaveBeenCalledTimes(1));
    rerender(<ReferralStatusCard refreshKey={2} />);
    await waitFor(() => expect(mockGetStatus).toHaveBeenCalledTimes(2));
  });
});
