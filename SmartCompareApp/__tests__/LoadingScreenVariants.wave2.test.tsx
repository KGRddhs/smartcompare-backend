/**
 * Bundle E S3 Hot-Fix Wave 2 — L1 lane.
 *
 * Wave 1 wired LoadingScreenVariants into Home but didn't pass stages or
 * tips, so the concentric variant rendered the rings hero ONLY. Per
 * docs/claude-design-handoff/ui_kits/mobile/LoadingScreen.jsx the
 * comparison loader has:
 *   1. Hero (rings + counter)               ← already present
 *   2. StageChecklist (5 stages, 900ms cycle pending→active→done)  ← MISSING
 *   3. Factoid card (4 tips, ~5s cross-fade rotation)              ← MISSING
 *
 * Wave 2 lands those two sections WITH default copy inside
 * LoadingScreenVariants.tsx itself so HomeScreen doesn't need to know
 * about the loader's internal composition. When the caller passes
 * explicit `stages` or `tips` arrays, those win (back-compat with
 * Step14 onboarding which already supplies its own).
 *
 * TDD discipline: this file pins the failing contract first. Implementation
 * follows once these tests turn red.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

// Stub i18n so tests assert on i18n keys (not English copy) — that way
// AR locale flips are pinned by separate locale-key tests, not by re-running
// these with a different mock.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

// LoadingRings is the hero; its internals (rAF counter, ring SVG)
// would explode under fake timers + the reanimated test renderer in
// isolation. Mock to a marker so the wave-2 assertions can focus on
// the two new sections.
jest.mock('../src/components/hero/LoadingRings', () => {
  const ReactRequired = require('react');
  return {
    LoadingRings: (props: any) =>
      ReactRequired.createElement('View', {
        testID: 'mock-loading-rings',
        ...props,
      }),
  };
});

import { LoadingScreenVariants } from '../src/screens/LoadingScreenVariants';

// Default copy keys (i18n) that should land inside the component when
// the caller does NOT pass stages / tips. Wave-1 pulled the JSX literals
// into i18n keys; this test pins them.
const EXPECTED_STAGE_KEYS = [
  'loading.stage.understanding',
  'loading.stage.reading_specs',
  'loading.stage.cross_checking',
  'loading.stage.analyzing_reviews',
  'loading.stage.locking_match',
];

const EXPECTED_TIP_KEYS = [
  'loading.tip.peer_prioritize',
  'loading.tip.cross_checks',
  'loading.tip.work_for_you',
  'loading.tip.save_offline',
];

describe('LoadingScreenVariants — Wave 2 default sections (comparison mode)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders the StageChecklist card when called without explicit stages prop', () => {
    const { queryByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // The card host carries testID loading-stage-card; before wave 2 it
    // only rendered when stages.length > 0. After wave 2 the host is
    // always mounted in comparison mode.
    expect(queryByTestId('loading-stage-card')).toBeTruthy();
  });

  it('renders 5 default stage rows in comparison mode (no override)', () => {
    const { getAllByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // Each stage row exposes stage-<id>-icon. With 5 default stages we
    // expect 5 icons.
    const icons = getAllByTestId(/^stage-.*-icon$/);
    expect(icons.length).toBe(5);
  });

  it('renders the LoadingTipsCarousel when called without explicit tips prop', () => {
    const { queryByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // Existing tip host testID is loading-tips. Before wave 2 it only
    // rendered when tips.length > 0. After wave 2 it's always mounted in
    // comparison mode with the COMPARISON_TIPS default.
    expect(queryByTestId('loading-tips')).toBeTruthy();
  });

  // A2 (2026-09-05): the cadence moved off a flat 900ms metronome onto the
  // per-stage schedule DEFAULT_COMPARISON_STAGE_DONE_AT_MS =
  // [1200, 4200, 12000, 19500, 26000]. The walk contract — pending → active
  // → done, one stage at a time — is unchanged.
  it('walks stage status one at a time on the per-stage schedule (pending → active → done)', () => {
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // Stage 0 starts as active, stages 1-4 as pending. Accessibility
    // label mirrors status so we can assert without inspecting style.
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-1-icon').props.accessibilityLabel).toBe('pending');

    // After the first step (1200ms) stage 0 → done, stage 1 → active.
    act(() => {
      jest.advanceTimersByTime(1200);
    });
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-1-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-2-icon').props.accessibilityLabel).toBe('pending');

    // At 26,000ms total from mount every stage is done.
    act(() => {
      jest.advanceTimersByTime(26000 - 1200);
    });
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-4-icon').props.accessibilityLabel).toBe('done');
  });

  it('rotates the factoid tip every 5s', () => {
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // Wave 2 R2: tip string lives on the inner Text node (testID
    // `loading-tips-text`); the host is the Animated.View. Cross-fade
    // adds a 200ms fade-out before the index swap, so advance by
    // intervalMs + 200ms to land on the next tip.
    const initial = getByTestId('loading-tips-text').props.children;
    act(() => {
      jest.advanceTimersByTime(5000 + 200);
    });
    const next = getByTestId('loading-tips-text').props.children;
    expect(next).not.toBe('');
    expect(next).not.toBe(initial);
  });

  it('uses i18n keys (not hardcoded English) for stage labels', () => {
    const { getByText } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // Mocked t() returns the key when there is no defaultValue. Each
    // expected stage key must therefore appear as rendered text.
    for (const key of EXPECTED_STAGE_KEYS) {
      // Allow getByText to throw with a useful message if missing.
      expect(getByText(key)).toBeTruthy();
    }
  });

  it('uses i18n keys (not hardcoded English) for tip copy', () => {
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-wave2"
      />,
    );
    // The first tip rendered must be one of the comparison-mode keys.
    const text = getByTestId('loading-tips-text').props.children;
    expect(EXPECTED_TIP_KEYS).toContain(text);
  });

  it('respects an explicit stages prop (caller override wins over default)', () => {
    const customStages = [
      { id: 'a', label: 'Custom A', status: 'active' as const },
      { id: 'b', label: 'Custom B', status: 'pending' as const },
    ];
    const { getByTestId, getAllByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        stages={customStages}
        testID="lsv-wave2"
      />,
    );
    // Override = 2 stages, no cycling (caller owns status).
    expect(getAllByTestId(/^stage-.*-icon$/).length).toBe(2);
    expect(getByTestId('stage-a-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-b-icon').props.accessibilityLabel).toBe('pending');
  });

  it('respects an explicit tips prop (caller override wins over default)', () => {
    const customTips = ['Only this tip'];
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        tips={customTips}
        testID="lsv-wave2"
      />,
    );
    const text = getByTestId('loading-tips-text').props.children;
    expect(text).toBe('Only this tip');
  });

  it('does NOT auto-inject defaults in onboarding mode (Step14 keeps its own stages/tips)', () => {
    // Step14 explicitly supplies its own ONBOARDING_STAGES / ONBOARDING_TIPS;
    // when caller omits them in onboarding mode, do NOT silently inject the
    // comparison defaults (would mislabel the onboarding moment).
    const { queryByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="onboarding"
        testID="lsv-wave2"
      />,
    );
    expect(queryByTestId('loading-stage-card')).toBeNull();
    expect(queryByTestId('loading-tips')).toBeNull();
  });
});

describe('LoadingScreenVariants — Wave 2 i18n locale presence', () => {
  // Sanity-pin: en.json + ar.json must define the new keys so any future
  // commit that adds the key to one locale and forgets the other red-tests.
  const fs = require('fs');
  const path = require('path');
  const en = JSON.parse(
    fs.readFileSync(
      path.resolve(__dirname, '../src/i18n/en.json'),
      'utf8',
    ),
  );
  const ar = JSON.parse(
    fs.readFileSync(
      path.resolve(__dirname, '../src/i18n/ar.json'),
      'utf8',
    ),
  );

  it.each(EXPECTED_STAGE_KEYS)(
    'en.json defines %s',
    (key: string) => {
      expect(en[key]).toBeDefined();
      expect(typeof en[key]).toBe('string');
      expect(en[key].length).toBeGreaterThan(0);
    },
  );

  it.each(EXPECTED_STAGE_KEYS)(
    'ar.json defines %s',
    (key: string) => {
      expect(ar[key]).toBeDefined();
      expect(typeof ar[key]).toBe('string');
      expect(ar[key].length).toBeGreaterThan(0);
    },
  );

  it.each(EXPECTED_TIP_KEYS)(
    'en.json defines %s',
    (key: string) => {
      expect(en[key]).toBeDefined();
      expect(typeof en[key]).toBe('string');
      expect(en[key].length).toBeGreaterThan(0);
    },
  );

  it.each(EXPECTED_TIP_KEYS)(
    'ar.json defines %s',
    (key: string) => {
      expect(ar[key]).toBeDefined();
      expect(typeof ar[key]).toBe('string');
      expect(ar[key].length).toBeGreaterThan(0);
    },
  );

  it('no scary forbidden vocab in any new EN key', () => {
    const banned = ["couldn't", 'try again', 'Failed to'];
    for (const key of [...EXPECTED_STAGE_KEYS, ...EXPECTED_TIP_KEYS]) {
      const v: string = en[key] ?? '';
      for (const b of banned) {
        expect(v.toLowerCase()).not.toContain(b.toLowerCase());
      }
    }
  });

  it('no scary forbidden vocab in any new AR key', () => {
    const bannedAr = ['تعذر', 'فشل'];
    for (const key of [...EXPECTED_STAGE_KEYS, ...EXPECTED_TIP_KEYS]) {
      const v: string = ar[key] ?? '';
      for (const b of bannedAr) {
        expect(v).not.toContain(b);
      }
    }
  });
});
