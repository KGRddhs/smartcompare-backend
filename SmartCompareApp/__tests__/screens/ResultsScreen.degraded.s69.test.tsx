/**
 * S69 U7 T2 (spec R2) — a degraded HTTP 200 is shown as degraded.
 *
 * Base (d792f00e): when the verdict LLM call fails after Phase-1,
 * `extraction_service.generate_comparison` returns
 * `{"winner_index": 0, "error": "verdict generation unavailable"}`
 * (extraction_service.py:2758-2760) and `build_comparison_response` still ships
 * `success: true` with that dict passed through as `result.comparison`
 * (response_builder.py:1891-1892, :2219). The ONLY signal is a truthy
 * `result.comparison.error`; `overview.winner.reason` becomes the template
 * `_QUALITATIVE_WINNER_REASON` ("{winner} is the stronger overall pick.") and
 * every product's pros/cons are []. ResultsContent renders it as a normal
 * result: the template reason as the verdict body (when there is no
 * `scoring_v2.factual_verdict`) and an always-present, empty Pros & Cons row.
 *
 * Contract pinned (spec R2 + binding review corrections 10/11 and open
 * question 6):
 *   - truthy `result.comparison.error` -> a visible truth notice under the
 *     verdict eyebrow: testID `results-content-degraded-note`, copy key
 *     `results.degraded.note` (its own key — NOT `results.partial.note`);
 *   - the template winner reason is NOT rendered;
 *   - the empty Pros & Cons accordion row is NOT rendered;
 *   - FactualVerdict (deterministic from scores, verdict_builder.py) stays;
 *   - a payload WITHOUT `comparison.error` renders exactly as today;
 *   - the legacy text-only share (no comparison id) leaves the template
 *     winner reason out of the shared message;
 *   - the notice does not say "verdict": a score-derived FactualVerdict line
 *     can render right below it, so it names the write-up instead.
 *
 * ResultsAccordion is rendered for real (not mocked) so the Pros & Cons row
 * assertion is on what the user sees, whatever prop GREEN uses to hide it.
 * The i18n mock is a key passthrough, so assertions are on catalog keys.
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import policy from '../../src/i18n/.copy-policy.json';

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  const entering = { duration: () => entering, delay: () => entering };
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    FadeIn: entering,
    FadeInDown: entering,
  };
});

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
    i18n: { language: 'en' },
  }),
}));

jest.mock('../../src/components/results/DimensionBars', () => ({
  DimensionBars: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-dim-bars'} />;
  },
}));
jest.mock('../../src/components/results/FactualVerdict', () => ({
  FactualVerdict: ({ testID, line1 }: any) => {
    const { Text } = require('react-native');
    return <Text testID={testID ?? 'mock-factual-verdict'}>{line1}</Text>;
  },
}));
jest.mock('../../src/components/results/ConfidencePills', () => ({
  ConfidencePills: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-confidence-pills'} />;
  },
}));
jest.mock('../../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: () => null,
}));
jest.mock('../../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: () => null,
}));
jest.mock('../../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: () => null,
}));
jest.mock('../../src/components/results/RunnerUpWinsCard', () => ({
  RunnerUpWinsCard: () => null,
}));
jest.mock('../../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../../src/services/sourceMethod', () => ({
  anyEstimated: jest.fn(() => false),
  isConvertedUsd: jest.fn(() => false),
}));

// Boundary mocks for the ResultsScreen share case below (the orchestrator's
// import graph); mirror camera.engineUnavailable.s69.test.tsx.
jest.mock('../../src/services/api', () => ({
  getComparison: jest.fn(),
  identifyFromImages: jest.fn(),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  shareComparison: jest.fn(),
  putDemographics: jest.fn().mockResolvedValue(undefined),
  parseApiError: jest.fn(() => ({ code: null, message: '' })),
}));
jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));
jest.mock('../../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: jest.fn().mockResolvedValue(null),
  onSessionInvalid: jest.fn(() => () => undefined),
}));
jest.mock('../../src/services/demographicsTrigger', () => ({
  loadDemographicsState: jest.fn().mockResolvedValue({}),
  shouldShowDemographicsPrompt: jest.fn().mockReturnValue(false),
  recordDismissal: jest.fn().mockResolvedValue(undefined),
  recordSubmission: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));
jest.mock('../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en', setLanguage: jest.fn() }),
}));
jest.mock('../../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({ mark: jest.fn(), report: jest.fn(), reset: jest.fn() }),
}));

import { ResultsContent } from '../../src/components/results/ResultsContent';
import ResultsScreen from '../../src/screens/ResultsScreen';

const DEGRADED_NOTE_KEY = 'results.degraded.note';
const DEGRADED_NOTE_TESTID = 'results-content-degraded-note';
const PROS_CONS_LABEL_KEY = 'results.accordion.prosConsLabel';
// The response builder's _QUALITATIVE_WINNER_REASON on the degraded path.
const TEMPLATE_REASON = 'Galaxy S24 is the stronger overall pick.';
const REAL_REASON = 'Longer battery life and a brighter screen for the same money.';

function makeProducts(degraded: boolean): any[] {
  return [
    {
      name: 'Galaxy S24',
      brand: 'Samsung',
      price: { amount: 289, currency: 'BHD' },
      pros: degraded ? [] : ['Bright screen'],
      cons: degraded ? [] : ['Slow charging'],
    },
    {
      name: 'iPhone 15',
      brand: 'Apple',
      price: { amount: 329, currency: 'BHD' },
      pros: degraded ? [] : ['Camera'],
      cons: degraded ? [] : ['Price'],
    },
  ];
}

/** The REAL degraded-200 shape (review correction 10), or today's normal one. */
function makeProps(opts: { degraded: boolean; factualVerdict?: boolean }): any {
  const products = makeProducts(opts.degraded);
  const reason = opts.degraded ? TEMPLATE_REASON : REAL_REASON;
  const scoring_v2 = opts.factualVerdict
    ? {
        factual_verdict: { line1: 'Galaxy S24 leads on 3 of 4 dimensions.', line2: '' },
        dimensions: [
          { key: 'battery', winner_index: 0 },
          { key: 'display', winner_index: 0 },
          { key: 'price', winner_index: 0 },
        ],
        confidence_legs: { price: 'high', reviews: 'medium', specs: 'high' },
        personalization: { applied_shifts: [] },
        comparison_quality: 'normal',
        confidence_details: {},
      }
    : undefined;
  return {
    result: {
      success: true,
      overview: {
        winner: {
          product_index: 0,
          name: 'Galaxy S24',
          reason,
          key_tradeoff: opts.degraded ? '' : 'The iPhone keeps its value longer.',
        },
        products,
      },
      recommendation: reason,
      comparison: opts.degraded
        ? { winner_index: 0, error: 'verdict generation unavailable' }
        : { winner_index: 0, recommendation: REAL_REASON },
      metadata: { query: 'Galaxy S24 vs iPhone 15', region: 'bahrain' },
    },
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2,
    comparisonId: 'cmp-degraded-s69',
    cohortPeerCount: 0,
    cohortGovernorate: '',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-degraded-s69',
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
  };
}

describe('S69 U7 T2 — degraded 200 (comparison.error) renders as degraded', () => {
  it('shows the truth notice, hides the template reason and the empty Pros & Cons row; a normal payload is unchanged', () => {
    const degraded = render(<ResultsContent {...makeProps({ degraded: true })} />);

    // The notice: own testID + own key, not the price-settling partial note.
    expect(degraded.getByTestId(DEGRADED_NOTE_TESTID)).toBeTruthy();
    expect(degraded.getByText(DEGRADED_NOTE_KEY)).toBeTruthy();
    expect(degraded.queryByText('results.partial.note')).toBeNull();
    // The template reason is not presented as a real verdict.
    expect(degraded.queryByText(TEMPLATE_REASON)).toBeNull();
    // The empty Pros & Cons row is not presented as if real.
    expect(degraded.queryByText(PROS_CONS_LABEL_KEY)).toBeNull();
    // Everything that IS real still renders.
    expect(degraded.getByText('Galaxy S24')).toBeTruthy();
    expect(degraded.getByText('iPhone 15')).toBeTruthy();

    // Control: the same screen without comparison.error renders as today.
    const normal = render(<ResultsContent {...makeProps({ degraded: false })} />);
    expect(normal.queryByTestId(DEGRADED_NOTE_TESTID)).toBeNull();
    expect(normal.queryByText(DEGRADED_NOTE_KEY)).toBeNull();
    expect(normal.getByText(REAL_REASON)).toBeTruthy();
    expect(normal.getByText(PROS_CONS_LABEL_KEY)).toBeTruthy();
  });

  it('keeps the deterministic FactualVerdict and still shows the notice when scoring_v2 is present', () => {
    const degraded = render(
      <ResultsContent {...makeProps({ degraded: true, factualVerdict: true })} />,
    );
    expect(degraded.getByTestId(DEGRADED_NOTE_TESTID)).toBeTruthy();
    expect(degraded.getByText(DEGRADED_NOTE_KEY)).toBeTruthy();
    // verdict_builder.py factual line is score-derived, not LLM — it stays.
    expect(degraded.getByTestId('results-content-factual-verdict')).toBeTruthy();
    expect(degraded.getByTestId('results-v2-bars')).toBeTruthy();
    expect(degraded.queryByText(TEMPLATE_REASON)).toBeNull();
    expect(degraded.queryByText(PROS_CONS_LABEL_KEY)).toBeNull();
  });

  it('the legacy text-only share (no comparison id) leaves the template winner reason out of a degraded result', async () => {
    // ResultsScreen.handleShare's Share.share fallback used to append
    // `recommendation` (= overview.winner.reason = the template sentence on
    // the degraded path) to the shared text, presenting it as the verdict.
    // The jest react-native shim ships no Share; install a spy for this case.
    const RN = require('react-native');
    const hadShare = Object.prototype.hasOwnProperty.call(RN, 'Share');
    const prevShare = RN.Share;
    const shareSpy = jest.fn(() => Promise.resolve({ action: 'sharedAction' }));
    RN.Share = { share: shareSpy };
    try {
      const shareFor = async (degraded: boolean): Promise<string> => {
        shareSpy.mockClear();
        // No comparison_id anywhere -> sharableComparisonId is undefined ->
        // the legacy Share.share branch.
        const { result } = makeProps({ degraded });
        const navigation = { goBack: jest.fn(), navigate: jest.fn(), setOptions: jest.fn() };
        const screen = render(
          <ResultsScreen route={{ params: { result } } as any} navigation={navigation as any} />,
        );
        await act(async () => {
          fireEvent.press(screen.getByTestId('results-content-share-btn'));
        });
        expect(shareSpy).toHaveBeenCalledTimes(1);
        const message: string = (shareSpy.mock.calls[0] as any[])[0].message;
        screen.unmount();
        return message;
      };

      const degradedMessage = await shareFor(true);
      expect(degradedMessage).toContain('Galaxy S24');
      expect(degradedMessage).toContain('iPhone 15');
      expect(degradedMessage).not.toContain(TEMPLATE_REASON);

      // Control: a normal result still shares its real verdict line.
      const normalMessage = await shareFor(false);
      expect(normalMessage).toContain(REAL_REASON);
    } finally {
      if (hadShare) RN.Share = prevShare;
      else delete RN.Share;
    }
  });

  it('both catalogs carry results.degraded.note, copy-policy clean, no app or provider name', () => {
    const EN = en as Record<string, string>;
    const AR = ar as Record<string, string>;
    const enStr = EN[DEGRADED_NOTE_KEY];
    const arStr = AR[DEGRADED_NOTE_KEY];
    expect(typeof enStr).toBe('string');
    expect(typeof arStr).toBe('string');
    expect(enStr.trim().length).toBeGreaterThan(0);
    expect(arStr).toMatch(/[؀-ۿ]/);
    expect(arStr).not.toBe(enStr);
    expect(enStr).not.toBe(EN['results.partial.note']);
    // Review fix: a factual verdict line can sit directly below the notice,
    // so the notice must not claim the verdict is unavailable.
    expect(enStr).not.toMatch(/verdict/i);
    expect(arStr).not.toMatch(/الحكم/);

    // The review's rewrite of the spec copy: "could not" is the uncontracted
    // form of the banned "couldn't" (W3-11 asserts /Could not/ never renders).
    for (const re of [/couldn['’]t/i, /could not/i, /try again/i, /fail/i]) {
      expect(enStr).not.toMatch(re);
    }
    for (const word of (policy as any).scary_vocab_en as string[]) {
      expect(enStr.toLowerCase()).not.toContain(word.toLowerCase());
    }
    for (const word of (policy as any).scary_vocab_ar as string[]) {
      expect(arStr).not.toContain(word);
    }
    for (const row of (policy as any).banned_en as Array<{ pattern: string }>) {
      expect(enStr).not.toMatch(new RegExp(row.pattern));
    }
    for (const row of (policy as any).banned_ar as Array<{ pattern: string }>) {
      expect(arStr).not.toMatch(new RegExp(row.pattern));
    }
    for (const re of [/qaren/i, /myez/i, /openai/i, /\bgpt\b/i]) {
      expect(enStr).not.toMatch(re);
      expect(arStr).not.toMatch(re);
    }
    expect(arStr).not.toMatch(/[ً-ْٰ]/);
  });
});
