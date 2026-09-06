/**
 * A2 — the synthetic loading checklist must not lie about the compare.
 *
 * BEFORE: the derived comparison checklist advanced on a flat 900ms
 * interval, so all five emerald checkmarks — "Cross-checking 25+ retailers"
 * and "Locking in your top match" included — read DONE at t=4.5s while a
 * cold compare runs ~24.5-31.5s on prod. The loader stays mounted the whole
 * time (freeze-at-done is deliberate, see
 * LoadingScreenVariants.freezeAtComplete.test.tsx), so the user then stared
 * at a finished checklist for ~20-26 more seconds, under ONE static caption
 * — `onStatus` is unreachable while ENABLE_EXPO_FETCH_SSE is false, so
 * nothing on the screen moved.
 *
 * AFTER: the checklist walks a per-stage schedule whose last check lands at
 * 26s, and the caption escalates at 8s and 18s.
 *
 * These tests pin the HONESTY properties, not the exact numbers where a
 * number would only re-state the implementation:
 *   - at 4.5s (the old all-done point) the list is NOT all done
 *   - the final check never lands before 20s
 *   - it DOES land by 26s (the schedule completes; it does not stall)
 *   - the caption escalates at 8s and again at 18s, in EN and AR
 *   - a real caller-supplied status update outranks the escalation
 *   - onboarding mode is untouched
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

// Resolve t() against the REAL catalog so the escalation assertions pin the
// shipped copy, not a key echo. Mirrors i18next: catalog hit wins, then
// defaultValue, then the key.
let mockLocale: 'en' | 'ar' = 'en';
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      const table = require(
        mockLocale === 'ar' ? '../src/i18n/ar.json' : '../src/i18n/en.json',
      ) as Record<string, string>;
      if (Object.prototype.hasOwnProperty.call(table, key)) return table[key];
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

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
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const enRec = en as Record<string, string>;
const arRec = ar as Record<string, string>;

const STAGE_COUNT = 5;
const LAST_STAGE = STAGE_COUNT - 1;
// The measured prod envelope for a cold compare (audit doc): 24.5-31.5s.
const OLD_ALL_DONE_MS = 4500;
const HONESTY_FLOOR_MS = 20000;
const SCHEDULE_COMPLETE_MS = 26000;

const CAPTION_BASE = 'Finding products...';

function statusOf(api: any, index: number): string {
  return api.getByTestId(`stage-${index}-icon`).props.accessibilityLabel;
}

function captionText(api: any): string {
  return api.getByTestId('loading-caption').props.children as string;
}

/**
 * How many stage rows the component ACTUALLY renders, rather than trusting
 * the local STAGE_COUNT constant. If a sixth default stage is ever added,
 * the completion assertion below walks it too — so an unscheduled stage
 * cannot slip in behind a hardcoded 5.
 */
function renderedStageCount(api: any): number {
  let n = 0;
  while (api.queryByTestId(`stage-${n}-icon`)) n += 1;
  return n;
}

describe('A2 — derived comparison checklist is paced to the real compare', () => {
  beforeEach(() => {
    mockLocale = 'en';
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('is NOT all-done at 4.5s (the cadence that claimed finished work in 4.5s)', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    act(() => {
      jest.advanceTimersByTime(OLD_ALL_DONE_MS);
    });
    const statuses = Array.from({ length: STAGE_COUNT }, (_, i) =>
      statusOf(api, i),
    );
    expect(statuses.every((s) => s === 'done')).toBe(false);
    // Specifically: the two stages that dominate wall time have not been
    // claimed yet.
    expect(statusOf(api, 3)).toBe('pending');
    expect(statusOf(api, LAST_STAGE)).toBe('pending');
  });

  it('holds an honest intermediate state at 4.5s (early stages done, later ones not)', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    act(() => {
      jest.advanceTimersByTime(OLD_ALL_DONE_MS);
    });
    // The list has visibly MOVED — this is not a frozen all-pending list.
    expect(statusOf(api, 0)).toBe('done');
    expect(statusOf(api, 1)).toBe('done');
    // ...and is honestly mid-flight on the long stage.
    expect(statusOf(api, 2)).toBe('active');
  });

  it('never lands the final check before 20s', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    act(() => {
      jest.advanceTimersByTime(HONESTY_FLOOR_MS - 1);
    });
    expect(statusOf(api, LAST_STAGE)).not.toBe('done');
  });

  // Over-correction guard (the mirror of the 20s floor above): a schedule
  // that outruns the compare is less bad than one that lies, but it is
  // still wrong. This is deliberately asserted over the RENDERED stage
  // count, not the local constant.
  it('does land the final check by 26s (the walk completes, it does not stall)', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    const count = renderedStageCount(api);
    expect(count).toBe(STAGE_COUNT);
    act(() => {
      jest.advanceTimersByTime(SCHEDULE_COMPLETE_MS);
    });
    for (let i = 0; i < count; i++) {
      expect(statusOf(api, i)).toBe('done');
    }
  });

  it('advances one stage at a time — no stage is skipped on the way up', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    let seenActive = 0;
    // Sample every 100ms across the whole schedule; the active cursor must
    // never jump by more than one.
    for (let elapsed = 0; elapsed <= SCHEDULE_COMPLETE_MS; elapsed += 100) {
      const doneCount = Array.from({ length: STAGE_COUNT }, (_, i) =>
        statusOf(api, i),
      ).filter((s) => s === 'done').length;
      expect(doneCount - seenActive).toBeLessThanOrEqual(1);
      seenActive = doneCount;
      act(() => {
        jest.advanceTimersByTime(100);
      });
    }
    expect(seenActive).toBe(STAGE_COUNT);
  });

  it('tolerates being unmounted mid-walk (fast compare) without a stray timer', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    act(() => {
      jest.advanceTimersByTime(6000);
    });
    expect(() => api.unmount()).not.toThrow();
    expect(() => {
      act(() => {
        jest.advanceTimersByTime(SCHEDULE_COMPLETE_MS);
      });
    }).not.toThrow();
  });
});

describe('A2 — the caption escalates instead of sitting on one static string', () => {
  beforeEach(() => {
    mockLocale = 'en';
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('keeps the caller caption before 8s', () => {
    const api = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption={CAPTION_BASE}
      />,
    );
    expect(captionText(api)).toBe(CAPTION_BASE);
    act(() => {
      jest.advanceTimersByTime(7999);
    });
    expect(captionText(api)).toBe(CAPTION_BASE);
  });

  it('escalates at 8s, then again at 18s', () => {
    const api = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption={CAPTION_BASE}
      />,
    );
    act(() => {
      jest.advanceTimersByTime(8000);
    });
    expect(captionText(api)).toBe(enRec['loading.caption.still_checking']);
    expect(captionText(api)).not.toBe(CAPTION_BASE);

    act(() => {
      jest.advanceTimersByTime(10000);
    });
    expect(captionText(api)).toBe(enRec['loading.caption.almost_there']);
  });

  it('escalates in Arabic too (both locales carry the copy)', () => {
    mockLocale = 'ar';
    const api = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption={CAPTION_BASE}
      />,
    );
    act(() => {
      jest.advanceTimersByTime(8000);
    });
    expect(captionText(api)).toBe(arRec['loading.caption.still_checking']);
    act(() => {
      jest.advanceTimersByTime(10000);
    });
    expect(captionText(api)).toBe(arRec['loading.caption.almost_there']);
  });

  it('yields to a real caller status update (the escalation is a stand-in, not an override)', () => {
    const api = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption={CAPTION_BASE}
      />,
    );
    act(() => {
      jest.advanceTimersByTime(8000);
    });
    expect(captionText(api)).toBe(enRec['loading.caption.still_checking']);
    // A live onStatus message arrives (what ENABLE_EXPO_FETCH_SSE would
    // restore) — the caller's string wins from then on.
    api.rerender(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption="Checking prices"
      />,
    );
    expect(captionText(api)).toBe('Checking prices');
    act(() => {
      jest.advanceTimersByTime(20000);
    });
    expect(captionText(api)).toBe('Checking prices');
  });

  it('stays yielded after a live feed returns the caption to its mount value (latch, not equality)', () => {
    // HomeScreen's caption is `statusMessage || t('results.loading.finding')`
    // and it CLEARS statusMessage when the compare settles — so a real
    // onStatus feed ends by handing the prop back to exactly the string it
    // mounted with. A per-render equality against the mount value would read
    // that as "the caller went static again" and resume narrating over a feed
    // that is demonstrably alive. Once live, always live.
    const api = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption={CAPTION_BASE}
      />,
    );
    act(() => {
      jest.advanceTimersByTime(8000);
    });
    expect(captionText(api)).toBe(enRec['loading.caption.still_checking']);

    api.rerender(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption="Checking prices"
      />,
    );
    expect(captionText(api)).toBe('Checking prices');

    // Feed clears — prop returns to the mount string.
    api.rerender(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        caption={CAPTION_BASE}
      />,
    );
    expect(captionText(api)).toBe(CAPTION_BASE);
    act(() => {
      jest.advanceTimersByTime(20000);
    });
    expect(captionText(api)).toBe(CAPTION_BASE);
  });

  it('renders no caption at all when the caller supplies none', () => {
    const api = render(
      <LoadingScreenVariants variant="concentric" mode="comparison" />,
    );
    act(() => {
      jest.advanceTimersByTime(20000);
    });
    expect(api.queryByTestId('loading-caption')).toBeNull();
  });

  it('never escalates the onboarding caption (3.2s brand beat, nothing to narrate)', () => {
    const api = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="onboarding"
        caption="Building your shopping advisor"
      />,
    );
    act(() => {
      jest.advanceTimersByTime(30000);
    });
    expect(captionText(api)).toBe('Building your shopping advisor');
  });
});

describe('A2 — escalation copy exists in both locales and stays non-scary', () => {
  const KEYS = [
    'loading.caption.still_checking',
    'loading.caption.almost_there',
  ];

  it.each(KEYS)('en.json defines %s', (key) => {
    expect(typeof enRec[key]).toBe('string');
    expect(enRec[key].length).toBeGreaterThan(0);
  });

  it.each(KEYS)('ar.json defines %s', (key) => {
    expect(typeof arRec[key]).toBe('string');
    expect(arRec[key].length).toBeGreaterThan(0);
  });

  it('EN copy carries no forbidden vocab', () => {
    const banned = ["couldn't", 'try again', 'failed to', 'failed'];
    for (const key of KEYS) {
      for (const b of banned) {
        expect(enRec[key].toLowerCase()).not.toContain(b);
      }
    }
  });

  it('AR copy carries no forbidden vocab', () => {
    const bannedAr = ['تعذر', 'فشل'];
    for (const key of KEYS) {
      for (const b of bannedAr) {
        expect(arRec[key]).not.toContain(b);
      }
    }
  });

  it('the 8s caption sets an honest expectation about how long this takes', () => {
    // The whole point of the escalation: tell the user a cold compare can
    // run to ~30s rather than implying it is nearly done.
    expect(enRec['loading.caption.still_checking']).toMatch(/30/);
    expect(arRec['loading.caption.still_checking']).toMatch(/30/);
  });
});
