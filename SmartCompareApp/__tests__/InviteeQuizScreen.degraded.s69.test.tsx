/**
 * S69 U7 R2 (InviteeQuiz half) — a DEGRADED comparison's template winner
 * reason is not shown to the invitee as if it were a real verdict.
 *
 * run_invitee_quiz (referral_service.py) returns the referrer's stored
 * `full_response`, so a comparison saved on the degraded path (the verdict
 * LLM call failed after Phase-1: `comparison.error` truthy, winner reason =
 * the response builder's template "{winner} is the stronger overall pick.")
 * reaches this screen with that template as `overview.winner.reason`. The
 * gate is the SAME predicate ResultsContent uses
 * (services/resultHonesty.isDegradedComparison). The winner name and the
 * score-derived match score are real and stay.
 *
 * Mock block mirrors InviteeQuizScreen.matchScore.m18.test.tsx.
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
  // W3-4: the screens' exit controls now read the navigator's own
  // mounted route names (and ask whether there is anything to go back
  // to) instead of hard-coding 'Main'. Without these two the press
  // handlers would throw `navigation.getState is not a function` /
  // `navigation.canGoBack is not a function`. Assertions unchanged.
  getState: () => ({ routeNames: ['Auth', 'ReferralLanding', 'InviteeQuiz'] }),
  canGoBack: () => true,
};

const baseRoute: any = {
  params: {
    share_token: 'tok-123',
    invite_id: 'invite-uuid-1',
    ref: 'QR-ABCDEF',
  },
};

const TEMPLATE_REASON = 'Galaxy S24 is the stronger overall pick.';
const REAL_REASON = 'Better camera for your priority.';

function makeResult(degraded: boolean): any {
  const reason = degraded ? TEMPLATE_REASON : REAL_REASON;
  return {
    overview: {
      winner: { product_index: 1, name: 'Galaxy S24', reason },
    },
    recommendation: reason,
    comparison: degraded
      ? { winner_index: 1, error: 'verdict generation unavailable' }
      : { winner_index: 1, recommendation: REAL_REASON },
    scoring: {
      scoring_method: 'invitee_quiz',
      scores: {
        product_0: { overall: 55.2, breakdown: {}, weights_used: {} },
        product_1: { overall: 91.4, breakdown: {}, weights_used: {} },
      },
    },
  };
}

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

describe('S69 U7 R2 — InviteeQuiz hides the template reason of a degraded comparison', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('degraded (comparison.error): winner card renders, the template reason does not', async () => {
    const { getByTestId, getByText, queryByText, findByText } = await walkToResult(
      makeResult(true),
    );
    expect(getByTestId('quiz-winner-card')).toBeTruthy();
    expect(getByText('Galaxy S24')).toBeTruthy();
    // The score-derived match score is real and stays.
    expect(await findByText('91%')).toBeTruthy();
    expect(queryByText(TEMPLATE_REASON)).toBeNull();
  });

  it('control: a normal comparison still shows its real winner reason', async () => {
    const { getByText } = await walkToResult(makeResult(false));
    expect(getByText(REAL_REASON)).toBeTruthy();
  });
});
