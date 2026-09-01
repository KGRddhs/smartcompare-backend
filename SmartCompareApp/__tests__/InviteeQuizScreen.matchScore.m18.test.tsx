/**
 * M18 MB-contract-10 (InviteeQuiz half) — the match score must come from the
 * REAL scoring payload, not a phantom key.
 *
 * Backend `scoring` block emits {scores: {product_N: {overall, ...}}, ...}
 * (response_builder.py:1557-1564) and run_invitee_quiz returns the sanitized
 * comparison payload with that same block tagged scoring_method:'invitee_quiz'
 * (referral_service.py). There is NO `scoring.products` key on any backend
 * shape — so `result?.scoring?.products ?? []` always fell through to the
 * hardcoded 78 and every invitee saw a fabricated match score.
 *
 * Mock block mirrors InviteeQuizScreen.test.tsx.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import InviteeQuizScreen from '../src/screens/InviteeQuizScreen';

jest.mock('react-native-reanimated', () => {
  const RealRN = require('react-native');
  return {
    __esModule: true,
    default: {
      View: RealRN.View,
      Text: RealRN.Text,
      Image: RealRN.Image,
      ScrollView: RealRN.View,
      createAnimatedComponent: <P,>(C: any) => C,
    },
    FadeIn: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    FadeInDown: {
      duration: () => ({ delay: () => ({}) }),
      delay: () => ({ duration: () => ({}) }),
    },
    useSharedValue: (init: any) => ({ value: init }),
    useAnimatedStyle: (fn: any) => fn(),
    useAnimatedReaction: (_p: any, _r: any) => undefined,
    useDerivedValue: (fn: any) => ({ value: fn() }),
    interpolate: (_v: number, _i: number[], o: number[]) => o[0],
    withTiming: (v: any) => v,
    withSpring: (v: any) => v,
    withRepeat: (a: any) => a,
    withDelay: (_: any, a: any) => a,
    withSequence: (...a: any[]) => a[a.length - 1],
    runOnJS: (fn: any) => fn,
    Easing: {
      inOut: () => (t: number) => t,
      out: () => (t: number) => t,
      ease: (t: number) => t,
      cubic: (t: number) => t,
      bezier: () => (t: number) => t,
    },
  };
});

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

const mockSubmitInviteeQuiz = jest.fn();

jest.mock('../src/services/referralService', () => ({
  submitInviteeQuiz: (...args: any[]) => mockSubmitInviteeQuiz(...args),
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
  params: {
    share_token: 'tok-123',
    invite_id: 'invite-uuid-1',
    ref: 'QR-ABCDEF',
  },
};

/** Real backend shape: scoring.scores.product_N.overall (no scoring.products). */
const RESULT_WITH_SCORING = {
  overview: {
    winner: {
      product_index: 1,
      name: 'Galaxy S24',
      reason: 'Better camera for your priority.',
    },
  },
  scoring: {
    scoring_method: 'invitee_quiz',
    scores: {
      product_0: { overall: 55.2, breakdown: {}, weights_used: {} },
      product_1: { overall: 91.4, breakdown: {}, weights_used: {} },
    },
  },
};

const RESULT_WITHOUT_SCORING = {
  overview: {
    winner: {
      product_index: 0,
      name: 'iPhone 15',
      reason: 'Simpler for you.',
    },
  },
};

async function walkToResult(payload: any) {
  mockSubmitInviteeQuiz.mockResolvedValueOnce(payload);
  const utils = render(
    <InviteeQuizScreen navigation={mockNavigation} route={baseRoute} />
  );
  const { getByText } = utils;
  fireEvent.press(getByText('onboarding.priorities.quality'));
  fireEvent.press(getByText('referrals.quiz.next'));
  fireEvent.press(getByText('onboarding.budget.premium'));
  fireEvent.press(getByText('referrals.quiz.next'));
  fireEvent.press(getByText('referrals.quiz.brand.open_to_emerging'));
  fireEvent.press(getByText('referrals.quiz.next'));
  fireEvent.press(getByText('referrals.quiz.submit'));
  await utils.findByText('referrals.quiz.resultTitle');
  return utils;
}

describe('InviteeQuizScreen — match score reads the real scoring payload (M18 MB-contract-10)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the winner's scoring.scores.product_N.overall as the match score", async () => {
    const { findByText, queryByText } = await walkToResult(RESULT_WITH_SCORING);
    // winner product_index=1 → product_1.overall 91.4 → rounds to 91.
    expect(await findByText('91%')).toBeTruthy();
    // The fabricated fallback must NOT render when real scores exist.
    expect(queryByText('78%')).toBeNull();
  });

  it('keeps the 78 fallback ONLY when the payload carries no scores at all', async () => {
    const { findByText } = await walkToResult(RESULT_WITHOUT_SCORING);
    expect(await findByText('78%')).toBeTruthy();
  });
});
