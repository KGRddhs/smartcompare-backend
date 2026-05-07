/**
 * ReferralLandingScreen redesign — Phase 4 Task 38.
 *
 * Verifies the partial-blur invitee landing per design § 4e:
 * - Product names + cohort badge slot visible (no gate)
 * - Winner ✓ + verdict + score GATED behind quiz/signup
 * - Two CTAs:
 *   - "See how it scores for YOU" (signature emerald) → quiz path
 *   - "Just give me the app" (small text link) → onboarding/auth path
 *
 * Existing 4-state tests stay in ReferralLandingScreen.test.tsx;
 * this file targets the new structural contract.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('react-native-reanimated', () => {
  const RealReact = require('react');
  const passthrough = ({ children, ...props }: any) =>
    RealReact.createElement('mock-Animated-View', props, children);
  return {
    __esModule: true,
    default: { View: passthrough, Text: passthrough },
    FadeIn: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    FadeInDown: {
      duration: () => ({ delay: () => ({}) }),
      delay: () => ({ duration: () => ({}) }),
    },
    useSharedValue: (init: any) => ({ value: init }),
    useAnimatedStyle: (fn: any) => fn(),
    withTiming: (v: any) => v,
    Easing: {
      inOut: () => (t: number) => t,
      out: () => (t: number) => t,
      cubic: (t: number) => t,
      bezier: () => (t: number) => t,
    },
  };
});

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: 'en',
    isRTL: false,
    switchLanguage: jest.fn(),
  }),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = (opts?.defaultValue as string) ?? key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

const mockResolveInvite = jest.fn();
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

import ReferralLandingScreen from '../src/screens/ReferralLandingScreen';

const mockNavigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  reset: jest.fn(),
};

const baseRoute: any = {
  params: { share_token: 'abc123', ref: 'QR-ABCDEF' },
};

const RESOLUTION_WITH_WINNER = {
  invite_id: 'invite-uuid-1',
  referrer_display_name: 'Ahmed',
  comparison: {
    products: [{ name: 'iPhone 15' }, { name: 'Galaxy S24' }],
    winner_index: 1,
  },
  cohort_match: { peers_count: 12, governorate: 'Capital' },
};

beforeEach(() => {
  jest.clearAllMocks();
  mockResolveInvite.mockResolvedValue(RESOLUTION_WITH_WINNER);
});

describe('ReferralLandingScreen redesign — Phase 4 Task 38', () => {
  it('renders BOTH product names side-by-side (visible, no blur)', async () => {
    const { getByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => {
      expect(getByText('iPhone 15')).toBeTruthy();
      expect(getByText('Galaxy S24')).toBeTruthy();
    });
  });

  it('does NOT render a winner badge or "Best for you" pill on the products', async () => {
    const { queryByTestId, queryByText } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => {
      // The winner is gated — no winner-styled element should appear.
      expect(queryByTestId('referral-winner-badge')).toBeNull();
      // Legacy "Winner" copy must be gone.
      expect(queryByText(/^WINNER$/i)).toBeNull();
    });
  });

  it('renders the cohort badge slot when cohort_match has data', async () => {
    const { getByTestId } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => {
      expect(getByTestId('referral-cohort-badge-slot')).toBeTruthy();
    });
  });

  it('renders the EMERALD signature "See how it scores for YOU" CTA', async () => {
    const { getByTestId } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => {
      expect(getByTestId('referral-cta-quiz')).toBeTruthy();
    });
  });

  it('renders the COOL-PATH "Just give me the app" small text link', async () => {
    const { getByTestId } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => {
      expect(getByTestId('referral-cta-skip')).toBeTruthy();
    });
  });

  it('navigates to InviteeQuiz on the emerald CTA tap (hot path)', async () => {
    const { getByTestId } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => getByTestId('referral-cta-quiz'));
    fireEvent.press(getByTestId('referral-cta-quiz'));
    expect(mockNavigation.navigate).toHaveBeenCalledWith(
      'InviteeQuiz',
      expect.objectContaining({
        share_token: 'abc123',
        invite_id: 'invite-uuid-1',
        ref: 'QR-ABCDEF',
      })
    );
  });

  it('resets into Auth/Main on the skip-link tap (cool path)', async () => {
    const { getByTestId } = render(
      <ReferralLandingScreen navigation={mockNavigation} route={baseRoute} />
    );
    await waitFor(() => getByTestId('referral-cta-skip'));
    fireEvent.press(getByTestId('referral-cta-skip'));
    // Cool path drops the invitee into the main onboarding/auth flow.
    expect(mockNavigation.reset).toHaveBeenCalled();
  });
});
