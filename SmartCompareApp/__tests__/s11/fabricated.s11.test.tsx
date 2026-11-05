/**
 * S81-11 RED -- the fabricated surfaces removed (spec part A, C1-C3, C7-C9;
 * rulings R-S11-11, R-S11-20, R-S11-31).
 *
 * CohortBadge is deleted (zero renderers left); the InviteeQuiz 78 fallback
 * goes (no score -> no score row); LoadingRings has NO 2,074 default (no
 * target -> no counter chip) and guards an undefined counterTarget in the
 * state init and the tick; the savings tile and line go from Profile and
 * History (the /home/savings sum counts estimated and converted prices).
 * Static rows read files with fs.readFileSync (CRLF normalised) and strip
 * comments, so a comment naming a removed thing is not a violation (RC9).
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent, act } from '@testing-library/react-native';

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
    useAnimatedProps: (fn: any) => fn(),
    useAnimatedReaction: (_p: any, _r: any) => undefined,
    useDerivedValue: (fn: any) => ({ value: fn() }),
    interpolate: (_v: number, _i: number[], o: number[]) => o[0],
    withTiming: (v: any) => v,
    withSpring: (v: any) => v,
    withRepeat: (a: any) => a,
    withDelay: (_: any, a: any) => a,
    withSequence: (...a: any[]) => a[a.length - 1],
    runOnJS: (fn: any) => fn,
    cancelAnimation: () => undefined,
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
jest.mock('../../src/services/referralService', () => ({
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

const SRC = path.resolve(__dirname, '../../src');

function readSrc(rel: string): string {
  return fs.readFileSync(path.join(SRC, rel), 'utf8').replace(/\r\n/g, '\n');
}

/** Strip block and line comments (JSX comment bodies included). */
function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:'"`\\])\/\/[^\n]*/g, '$1');
}

function loadOptional(rel: string): any {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require(rel);
  } catch {
    return null;
  }
}

function allText(node: any): string[] {
  const out: string[] = [];
  const walk = (n: any) => {
    if (n == null) return;
    if (typeof n === 'string') {
      out.push(n);
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walk);
      return;
    }
    if (n.children) n.children.forEach(walk);
  };
  walk(node);
  return out;
}

describe('S81-11 A1 / A2 -- CohortBadge is deleted with zero renderers left', () => {
  it('A1: the module no longer exists', () => {
    expect(fs.existsSync(path.join(SRC, 'components/CohortBadge.tsx'))).toBe(false);
    expect(loadOptional('../../src/components/CohortBadge')).toBeNull();
  });

  it('A2: ResultsContent / ReferralLanding / ResultsScreen carry no CohortBadge token or slot', () => {
    for (const rel of [
      'components/results/ResultsContent.tsx',
      'screens/ReferralLandingScreen.tsx',
      'screens/ResultsScreen.tsx',
    ]) {
      const code = stripComments(readSrc(rel));
      expect({ rel, hit: /\bCohortBadge\b/.test(code) }).toEqual({ rel, hit: false });
      expect({ rel, hit: /cohort-badge-slot/.test(code) }).toEqual({ rel, hit: false });
    }
    const code = stripComments(readSrc('screens/ResultsScreen.tsx'));
    expect(code).not.toMatch(/resolveCohortPeerCount|resolveCohortGovernorate/);
  });
});

describe('S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20)', () => {
  const { LoadingRings } = require('../../src/components/hero/LoadingRings');

  it('A3: no counterTarget -> no counter chip and no digit at all', () => {
    const r = render(<LoadingRings animated={false} />);
    expect(r.queryByTestId('loading-rings-counter-chip')).toBeNull();
    const digits = allText(r.toJSON()).filter((s) => /\d/.test(s));
    expect(digits).toEqual([]);
  });

  it('A3b: showCounter alone (no target) still renders no chip', () => {
    const r = render(<LoadingRings animated={false} showCounter />);
    expect(r.queryByTestId('loading-rings-counter-chip')).toBeNull();
  });

  it('A3c (R-S11-20): animated with no target never ticks a NaN or a number', async () => {
    jest.useFakeTimers();
    const r = render(<LoadingRings />);
    await act(async () => {
      jest.advanceTimersByTime(3000);
    });
    const texts = allText(r.toJSON());
    expect(texts.filter((s) => /NaN/.test(s))).toEqual([]);
    expect(texts.filter((s) => /\d/.test(s))).toEqual([]);
    r.unmount();
    jest.useRealTimers();
  });

  it('PIN: an explicit real target still renders its chip (Step14 cohort count path)', () => {
    const r = render(<LoadingRings counterTarget={120} animated={false} />);
    expect(r.queryByTestId('loading-rings-counter-chip')).not.toBeNull();
    expect(r.queryByText('120')).not.toBeNull();
  });

  it('PIN: showCounter={false} with a target renders no chip', () => {
    const r = render(<LoadingRings counterTarget={120} animated={false} showCounter={false} />);
    expect(r.queryByTestId('loading-rings-counter-chip')).toBeNull();
  });

  it('A3d: the component source carries no 2074 default', () => {
    const code = stripComments(readSrc('components/hero/LoadingRings.tsx'));
    expect(code).not.toMatch(/2074|2,074/);
  });
});

describe('S81-11 A4 -- InviteeQuiz renders no fabricated match score (C2)', () => {
  const InviteeQuizScreen = require('../../src/screens/InviteeQuizScreen').default;
  const mockNavigation: any = {
    navigate: jest.fn(),
    goBack: jest.fn(),
    reset: jest.fn(),
    getState: () => ({ routeNames: ['Auth', 'ReferralLanding', 'InviteeQuiz'] }),
    canGoBack: () => true,
  };
  const baseRoute: any = {
    params: { share_token: 'tok-s11', invite_id: 'invite-s11', ref: 'QR-ABCDEF' },
  };

  async function walkToResult(payload: any) {
    mockSubmitInviteeQuiz.mockResolvedValueOnce(payload);
    const utils = render(<InviteeQuizScreen navigation={mockNavigation} route={baseRoute} />);
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

  it('A4: no scoring -> no quiz-match-score row and no 78%', async () => {
    const r = await walkToResult({
      overview: { winner: { product_index: 0, name: 'Fragrance A', reason: 'Fits.' } },
    });
    expect(r.queryByTestId('quiz-winner-card')).not.toBeNull();
    expect(r.queryByTestId('quiz-match-score')).toBeNull();
    expect(r.queryByText('78%')).toBeNull();
  });

  it('A4b: a non-finite overall is not a score either', async () => {
    const r = await walkToResult({
      overview: { winner: { product_index: 0, name: 'Fragrance A', reason: 'Fits.' } },
      scoring: { scores: { product_0: { overall: 'n/a' } } },
    });
    expect(r.queryByTestId('quiz-match-score')).toBeNull();
  });

  it('PIN: a real overall still renders (91.4 -> 91%)', async () => {
    const r = await walkToResult({
      overview: { winner: { product_index: 1, name: 'Fragrance B', reason: 'Fits.' } },
      scoring: { scores: { product_0: { overall: 55.2 }, product_1: { overall: 91.4 } } },
    });
    expect(await r.findByText('91%')).toBeTruthy();
  });
});

describe('S81-11 A6 -- the savings tile and line are gone from Profile and History (C8 / C9)', () => {
  it('ProfileEditorialSections renders no savings tile', () => {
    const code = stripComments(readSrc('components/ProfileEditorialSections.tsx'));
    expect(code).not.toMatch(/profile-month-stat-savings/);
    expect(code).not.toMatch(/['"]profile\.month\.savings['"]/);
    expect(code).not.toMatch(/savingsBhd/);
  });

  it('HistoryScreen renders no savings line', () => {
    const code = stripComments(readSrc('screens/HistoryScreen.tsx'));
    expect(code).not.toMatch(/['"]history\.hero\.savings['"]/);
    expect(code).not.toMatch(/savingsBhd/);
    expect(code).not.toMatch(/shopped smarter/i);
  });

  it('HomeEditorialSections has no SavingsBanner', () => {
    const code = stripComments(readSrc('components/HomeEditorialSections.tsx'));
    expect(code).not.toMatch(/\bSavingsBanner\b/);
    expect(code).not.toMatch(/home-savings-banner/);
    expect(code).not.toMatch(/['"]home\.savings\.(eyebrow|amount)['"]/);
  });
});
