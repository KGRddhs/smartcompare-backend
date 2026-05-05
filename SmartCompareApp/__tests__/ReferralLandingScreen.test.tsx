/**
 * ReferralLandingScreen tests (F3.2 + F3.3 batch)
 *
 * Per qa-referral's review of 7ccb4a3 — covers all 4 UX states
 * (loading / 404 / 503 / network) plus the privacy-aware happy paths
 * (titleWithWinner vs titleNoWinner).
 *
 * Mocks `resolveInvite` at the service module level so component code
 * runs unchanged. Drives each error path via .mockRejectedValueOnce
 * with a synthesized ReferralError shape.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ReferralLandingScreen from '../src/screens/ReferralLandingScreen';

// The shared __mocks__/react-native-reanimated.ts doesn't export the
// `entering`-style helpers we use (FadeInDown). Provide a minimal
// inline mock so this test file doesn't depend on the shared mock.
jest.mock('react-native-reanimated', () => {
  const RealReact = require('react');
  const passthrough = ({ children, ...props }: any) =>
    RealReact.createElement('mock-Animated-View', props, children);
  const noop = () => ({ duration: () => ({ delay: () => ({}) }), delay: () => ({ duration: () => ({}) }) });
  return {
    __esModule: true,
    default: { View: passthrough, Text: passthrough },
    FadeIn: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    FadeInDown: { duration: () => ({ delay: () => ({}) }), delay: () => ({ duration: () => ({}) }) },
    useSharedValue: (init: any) => ({ value: init }),
    useAnimatedStyle: (fn: any) => fn(),
    withTiming: (v: any) => v,
    withRepeat: (a: any) => a,
    withDelay: (_: any, a: any) => a,
    withSequence: (...a: any[]) => a[a.length - 1],
    runOnJS: (fn: any) => fn,
    Easing: {
      inOut: () => (t: number) => t,
      out: () => (t: number) => t,
      ease: (t: number) => t,
      cubic: (t: number) => t,
    },
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, any>) => {
      // Surface interpolation values so tests can match on the rendered string.
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

const mockResolveInvite = jest.fn();
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
  resolveInvite: (...args: any[]) => mockResolveInvite(...args),
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

const mockNavigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  reset: jest.fn(),
};

const baseRoute: any = {
  params: { share_token: 'abc123', ref: 'QR-ABCDEF' },
};

const HAPPY_RESOLUTION = {
  invite_id: 'invite-uuid-1',
  referrer_display_name: 'Ahmed',
  comparison: {
    products: [{ name: 'iPhone 15' }, { name: 'Galaxy S24' }],
    winner_index: 1,
  },
  cohort_match: null,
};

const PRIVACY_NO_WINNER_RESOLUTION = {
  invite_id: 'invite-uuid-2',
  referrer_display_name: 'A friend',
  comparison: {
    products: [{ name: 'Vitamin C' }, { name: 'Vitamin D' }],
    // winner_index intentionally absent — referrer's show_result=false
  },
  cohort_match: null,
};

describe('ReferralLandingScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders ActivityIndicator with loading a11y label while resolveInvite is in flight', () => {
    let resolveOnce: (value: any) => void = () => {};
    mockResolveInvite.mockImplementationOnce(
      () => new Promise((r) => { resolveOnce = r; })
    );
    const { getByLabelText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    expect(getByLabelText('referrals.landing.loading')).toBeTruthy();
    // resolve so the component cleanup path runs cleanly
    resolveOnce(HAPPY_RESOLUTION);
  });

  it('renders 404 fallback copy + Open Qaren CTA when status=404', async () => {
    mockResolveInvite.mockRejectedValueOnce(
      new FakeReferralError('not found', 'NOT_FOUND', 404)
    );
    const { findByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    expect(await findByText('referrals.landing.notFound')).toBeTruthy();
    // Two occurrences of the open-qaren key in the rendered tree:
    // one as the button label, one as the accessibilityLabel surfaced via t().
    // findByText is fine — it grabs the rendered Text node.
    expect(await findByText('referrals.landing.openQaren')).toBeTruthy();
  });

  it('renders feature-disabled copy when status=503', async () => {
    mockResolveInvite.mockRejectedValueOnce(
      new FakeReferralError('disabled', 'FEATURE_DISABLED', 503)
    );
    const { findByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    expect(await findByText('referrals.landing.unavailable')).toBeTruthy();
  });

  it('renders network fallback when error has neither 404 nor 503 status', async () => {
    mockResolveInvite.mockRejectedValueOnce(
      new FakeReferralError('flaky', 'NETWORK', null)
    );
    const { findByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    expect(await findByText('referrals.landing.network')).toBeTruthy();
  });

  it('renders titleWithWinner interpolated with referrer + products + winner on happy path', async () => {
    mockResolveInvite.mockResolvedValueOnce(HAPPY_RESOLUTION);
    const utils = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    // Allow the resolveInvite promise to resolve and setState to commit.
    await waitFor(() => {
      expect(mockResolveInvite).toHaveBeenCalled();
    });
    // Then poll for the rendered hero text.
    let heroText: any;
    await waitFor(() => {
      heroText = utils.getByText(/Ahmed/);
    });
    const flat = heroText.props.children as string;
    expect(flat).toContain('Ahmed');
    expect(flat).toContain('iPhone 15');
    expect(flat).toContain('Galaxy S24');
    expect(flat).toContain('referrals.landing.titleWithWinner');
  });

  it('renders titleNoWinner (no winner badge) when referrer privacy hid the result', async () => {
    mockResolveInvite.mockResolvedValueOnce(PRIVACY_NO_WINNER_RESOLUTION);
    const { findByText, queryByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    const heroText = await findByText(/A friend/);
    const flat = heroText.props.children as string;
    expect(flat).toContain('referrals.landing.titleNoWinner');
    expect(flat).not.toContain('referrals.landing.titleWithWinner');
    // No winner badge should be rendered when winner_index is undefined
    expect(queryByText('referrals.landing.winnerBadge')).toBeNull();
  });

  it('Start CTA navigates to InviteeQuiz with invite_id + share_token + ref', async () => {
    mockResolveInvite.mockResolvedValueOnce(HAPPY_RESOLUTION);
    const { findByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    const cta = await findByText('referrals.landing.startCta');
    fireEvent.press(cta);
    await waitFor(() => expect(mockNavigation.navigate).toHaveBeenCalled());
    expect(mockNavigation.navigate).toHaveBeenCalledWith(
      'InviteeQuiz',
      expect.objectContaining({
        invite_id: 'invite-uuid-1',
        share_token: 'abc123',
        ref: 'QR-ABCDEF',
      })
    );
  });
});
