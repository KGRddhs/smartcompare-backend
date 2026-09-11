/**
 * W3-4 — the referral screens' escape hatches must reset to a route the
 * navigator ACTUALLY has (finding MB-FLOWS-STATE-04).
 *
 * App.tsx's root navigator is a three-way ternary and mounts one of three
 * route-name sets. `'Main'` exists in exactly ONE of them (authed):
 *
 *   unauth            ["Auth","ReferralLanding","InviteeQuiz"]
 *   needsPreferences  ["Onboarding","ReferralLanding","InviteeQuiz"]
 *   authed            ["Main", … ,"ReferralLanding","InviteeQuiz"]
 *
 * Three controls on the two referral screens dispatch
 * `reset({ routes: [{ name: 'Main' }] })` unconditionally, and on the other
 * two sets the INSTALLED `@react-navigation/routers` returns `null` for that
 * action (`BaseRouter.tsx:45-57` — every route name in the payload must be a
 * member of `state.routeNames`). `@react-navigation/core` then calls
 * `onUnhandledAction`, which in a release build returns silently. Nothing
 * throws; the screen just stays. A test that only asserts `reset` WAS CALLED
 * therefore cannot tell a working control from a dead one — so every cell
 * below feeds the RECORDED payload to the real router and asserts it is
 * handled. `__tests__/helpers/routerSandbox.ts` is what makes the installed
 * (ESM-only) router loadable under this repo's jest.
 *
 * Per FABLE REVIEW RULING 4 this file deliberately imports NOTHING from
 * `src/utils/branchRoot` — the expected root is a LITERAL per set, so a
 * `resolveBranchRoot` that returned some other member of the authed set
 * (`'Results'`, `'Paywall'`…) would still redden the authed cells.
 * Per RULING 5 the suite owns a key-returning `t` mock and selects both back
 * arrows with the one deterministic string `'common.back'`.
 */

import * as fs from 'fs';
import * as path from 'path';
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ReferralLandingScreen from '../src/screens/ReferralLandingScreen';
import InviteeQuizScreen from '../src/screens/InviteeQuizScreen';
import {
  APP_ROOT,
  coldStartState,
  loadInstalledRouters,
  resetOutcome,
  rootRouteNameSets,
} from './helpers/routerSandbox';

// Union of the reanimated shapes the two screens need (the InviteeQuiz suite's
// mock is the superset; ReferralLanding only adds FadeInDown chaining, which it
// already covers).
jest.mock('react-native-reanimated', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const RealRN = require('react-native');
  return {
    __esModule: true,
    default: {
      View: RealRN.View,
      Text: RealRN.Text,
      Image: RealRN.Image,
      ScrollView: RealRN.View,
      createAnimatedComponent: (C: any) => C,
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

// RULING 5 — one deterministic string per key; `defaultValue` ignored.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: 'en',
    isRTL: false,
    switchLanguage: jest.fn(),
  }),
}));

const mockResolveInvite = jest.fn();
const mockSubmitInviteeQuiz = jest.fn();

jest.mock('../src/services/referralService', () => ({
  resolveInvite: (...args: any[]) => mockResolveInvite(...args),
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

const RESOLUTION = {
  invite_id: 'invite-uuid-1',
  referrer_display_name: 'Ahmed',
  comparison: {
    products: [{ name: 'iPhone 15' }, { name: 'Galaxy S24' }],
    winner_index: 1,
  },
  cohort_match: { peers_count: 12, governorate: 'Capital' },
};

const RESULT_PAYLOAD = {
  overview: { winner: { name: 'Galaxy S24', reason: 'Better camera.' } },
};

const landingRoute: any = { params: { share_token: 'abc123', ref: 'QR-ABCDEF' } };
const quizRoute: any = {
  params: { share_token: 'abc123', invite_id: 'invite-uuid-1', ref: 'QR-ABCDEF' },
};

// ---------------------------------------------------------------------------
// The installed router + the three route-name sets App.tsx actually mounts.
// ---------------------------------------------------------------------------
const routers = loadInstalledRouters();
const stackRouter = routers.StackRouter({});
const SETS = rootRouteNameSets();

type Screen = 'ReferralLanding' | 'InviteeQuiz';

/**
 * Does the INSTALLED router HANDLE this reset payload on the one-route
 * cold-start deep-link stack for this branch? `null` = dropped silently.
 */
function routerOutcome(
  payload: any,
  screen: Screen,
  routeNames: readonly string[],
): any {
  const state = coldStartState(
    stackRouter,
    screen,
    { share_token: 'abc123', ref: 'QR-ABCDEF' },
    routeNames,
  );
  return resetOutcome(routers, stackRouter, state, payload, routeNames);
}

function makeNav(routeNames: readonly string[], canGoBack = false): any {
  return {
    navigate: jest.fn(),
    goBack: jest.fn(),
    reset: jest.fn(),
    getState: () => ({ routeNames: [...routeNames] }),
    canGoBack: () => canGoBack,
  };
}

// --- the three controls -----------------------------------------------------

async function pressLandingSkip(nav: any): Promise<void> {
  mockResolveInvite.mockResolvedValueOnce(RESOLUTION);
  const { getByTestId } = render(
    <ReferralLandingScreen navigation={nav} route={landingRoute} />
  );
  await waitFor(() => getByTestId('referral-cta-skip'));
  fireEvent.press(getByTestId('referral-cta-skip'));
}

async function pressLandingOpenQaren(nav: any): Promise<void> {
  mockResolveInvite.mockRejectedValueOnce(
    new FakeReferralError('not found', 'NOT_FOUND', 404)
  );
  const { findByLabelText } = render(
    <ReferralLandingScreen navigation={nav} route={landingRoute} />
  );
  fireEvent.press(await findByLabelText('referrals.landing.openQaren'));
}

async function pressQuizSkipSignup(nav: any): Promise<void> {
  mockSubmitInviteeQuiz.mockResolvedValueOnce(RESULT_PAYLOAD);
  const { getByText, findByText } = render(
    <InviteeQuizScreen navigation={nav} route={quizRoute} />
  );
  fireEvent.press(getByText('onboarding.priorities.price'));
  fireEvent.press(getByText('referrals.quiz.next'));
  fireEvent.press(getByText('onboarding.budget.budget'));
  fireEvent.press(getByText('referrals.quiz.next'));
  fireEvent.press(getByText('referrals.quiz.brand.value_first'));
  fireEvent.press(getByText('referrals.quiz.next'));
  fireEvent.press(getByText('referrals.quiz.submit'));
  fireEvent.press(await findByText('referrals.quiz.skipSignup'));
}

const CONTROLS: [string, Screen, (nav: any) => Promise<void>][] = [
  ['ReferralLanding "Maybe later"', 'ReferralLanding', pressLandingSkip],
  ['ReferralLanding error-card "Open Qaren"', 'ReferralLanding', pressLandingOpenQaren],
  ['InviteeQuiz "skip signup"', 'InviteeQuiz', pressQuizSkipSignup],
];

// The expected root is a LITERAL per branch (RULING 4), never read back out of
// the fix's own resolver.
const BRANCHES: [string, readonly string[], string][] = [
  ['unauth', SETS.unauth, 'Auth'],
  ['needsPreferences', SETS.needsPreferences, 'Onboarding'],
  ['authed', SETS.authed, 'Main'],
];

const CELLS: [string, string, readonly string[], string, Screen, (nav: any) => Promise<void>][] =
  [];
for (const [branchLabel, routeNames, expectedRoot] of BRANCHES) {
  for (const [controlLabel, screen, press] of CONTROLS) {
    CELLS.push([branchLabel, controlLabel, routeNames, expectedRoot, screen, press]);
  }
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('W3-4 — the exit controls reset to the MOUNTED branch root', () => {
  it('loaded the installed @react-navigation/routers, not a mock', () => {
    expect(routers.version).toBe('7.5.5');
    expect(typeof stackRouter.getStateForAction).toBe('function');
  });

  it('extracted the three route-name sets App.tsx mounts', () => {
    expect(SETS.unauth).toEqual(['Auth', 'ReferralLanding', 'InviteeQuiz']);
    expect(SETS.needsPreferences).toEqual([
      'Onboarding',
      'ReferralLanding',
      'InviteeQuiz',
    ]);
    expect(SETS.authed).toContain('Main');
  });

  it.each(CELLS)(
    '[%s] %s dispatches a reset the router accepts, onto the branch root',
    async (_branch, _control, routeNames, expectedRoot, screen, press) => {
      const nav = makeNav(routeNames);
      await press(nav);

      await waitFor(() => expect(nav.reset).toHaveBeenCalledTimes(1));
      const payload = nav.reset.mock.calls[0][0];
      expect(payload.routes).toHaveLength(1);

      // The load-bearing line: ask the INSTALLED router whether it would do
      // anything with this action on this branch. `null` = dropped silently.
      expect(routerOutcome(payload, screen, routeNames)).not.toBeNull();

      expect(payload.routes[0].name).toBe(expectedRoot);
    },
    20000
  );

  it('neither screen casts a route name with `as never`', () => {
    // RULING 10 — the guard matches `as never` ONLY. `InviteeQuizScreen.tsx`'s
    // `(navigation as any)` signup navigate is deliberately out of scope.
    const counts: Record<string, number> = {};
    for (const rel of [
      'src/screens/ReferralLandingScreen.tsx',
      'src/screens/InviteeQuizScreen.tsx',
    ]) {
      const src = fs.readFileSync(path.join(APP_ROOT, rel), 'utf8');
      counts[rel] = (src.match(/\bas never\b/g) ?? []).length;
    }
    expect(counts).toEqual({
      'src/screens/ReferralLandingScreen.tsx': 0,
      'src/screens/InviteeQuizScreen.tsx': 0,
    });
  });
});

describe('W3-4 — the back arrow on a cold-start deep link', () => {
  async function renderLandingBack(nav: any) {
    mockResolveInvite.mockResolvedValueOnce(RESOLUTION);
    const { findByLabelText } = render(
      <ReferralLandingScreen navigation={nav} route={landingRoute} />
    );
    return findByLabelText('common.back');
  }

  function renderQuizBack(nav: any) {
    const { getByLabelText } = render(
      <InviteeQuizScreen navigation={nav} route={quizRoute} />
    );
    return getByLabelText('common.back');
  }

  it('ReferralLanding: nothing beneath us -> exits to the branch root, never goBack', async () => {
    const nav = makeNav(SETS.unauth, false);
    fireEvent.press(await renderLandingBack(nav));

    expect(nav.goBack).not.toHaveBeenCalled();
    await waitFor(() => expect(nav.reset).toHaveBeenCalledTimes(1));
    const payload = nav.reset.mock.calls[0][0];
    expect(routerOutcome(payload, 'ReferralLanding', SETS.unauth)).not.toBeNull();
    expect(payload.routes[0].name).toBe('Auth');
  });

  it('ReferralLanding: in-app entry -> still goBack, never resets (PIN, green today)', async () => {
    const nav = makeNav(SETS.unauth, true);
    fireEvent.press(await renderLandingBack(nav));

    expect(nav.goBack).toHaveBeenCalledTimes(1);
    expect(nav.reset).not.toHaveBeenCalled();
  });

  it('InviteeQuiz step 0: nothing beneath us -> exits to the branch root, never goBack', async () => {
    const nav = makeNav(SETS.unauth, false);
    fireEvent.press(renderQuizBack(nav));

    expect(nav.goBack).not.toHaveBeenCalled();
    await waitFor(() => expect(nav.reset).toHaveBeenCalledTimes(1));
    const payload = nav.reset.mock.calls[0][0];
    expect(routerOutcome(payload, 'InviteeQuiz', SETS.unauth)).not.toBeNull();
    expect(payload.routes[0].name).toBe('Auth');
  });

  // The goBack half of this cell is ALREADY covered by
  // `__tests__/InviteeQuizScreen.test.tsx` ("Back from Q1 calls
  // navigation.goBack (not setStep)"); this one exists as the symmetric
  // partner of the `canGoBack:false` case above and adds the "never resets"
  // half, so the guard's two branches are readable side by side.
  it('InviteeQuiz step 0: in-app entry -> still goBack, never resets (PIN, green today)', () => {
    const nav = makeNav(SETS.unauth, true);
    fireEvent.press(renderQuizBack(nav));

    expect(nav.goBack).toHaveBeenCalledTimes(1);
    expect(nav.reset).not.toHaveBeenCalled();
  });
});
