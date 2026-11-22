/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1b RED -- B-d: the Reviews header never spreads one side's rating or
 * count over both (INC_C1B_UNIT_SPEC_V2.md section 7 and 10.4: rows D1-D3,
 * pins P-D1, P-D2, P-D3; words of section 9 row 2 as ruled in RU-10; row D4
 * added by the orchestrator for row W3 of the owner's window test of 22 Nov
 * 2026, spec V2 addendum 1).
 *
 * The contract this file fixes for GREEN:
 *  - ResultsAccordion's Reviews header sub: N = the review products, R = those
 *    whose rating is a number > 0, C = those whose review_count is a number
 *    > 0. When N >= 2 and (0 < R < N or 0 < C < N) the sub is
 *    t('results.accordion.reviewsEach') with no figure (row 2: EN "Shown per
 *    product", AR from the section 9 code points).
 *  - Otherwise today's sub, byte for byte (both rated and counted: the
 *    weighted average and the total "across both"; neither: the bare phrase;
 *    counts only or ratings only on both sides: today's line).
 *  - The per-product body is unchanged (P-D3).
 *
 * Data: the owner's phone test of 22 Nov 2026 (case row B-d): only Creed
 * Aventus has a rating (4.4) and a count (5,600); Imagination men has a praise
 * line only. The praise lines are synthetic.
 *
 * Harness: ResultsAccordion real; react-i18next answers through a real
 * i18next instance over the real catalogs (the INC-C1 lastChecked pattern),
 * its language set before each render. The header sub is the second Text
 * under results-accordion-toggle-reviews, read with the section closed, so no
 * body text can match. F1: no new symbol; every base failure is an expect
 * assertion. Arabic is built from code points; this source stays ASCII.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { ResultsAccordion } from '../../src/components/results/ResultsAccordion';

let mockLang: 'en' | 'ar' = 'en';

// The real i18next over the real catalogs (referralExpiryPlurals.w414 setup).
jest.mock('react-i18next', () => {
  const i18next = require('i18next');
  const en = require('../../src/i18n/en.json');
  const ar = require('../../src/i18n/ar.json');
  const inst = i18next.createInstance();
  inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  });
  const t = inst.t.bind(inst);
  return {
    __esModule: true,
    __inst: inst,
    useTranslation: () => ({
      t,
      i18n: {
        get language() {
          return mockLang;
        },
      },
    }),
  };
});

const I18N = (require('react-i18next') as any).__inst;

// ------------------------------------------------------------------ strings --

const u = (...cps: number[]) => String.fromCodePoint(...cps);
const MIDDOT = u(0xb7);

// Section 9 row 2, the primary words (RU-10). If the owner's read picks the
// alternative, this one constant moves with the catalogs.
const ROW2: Record<'en' | 'ar', string> = {
  en: 'Shown per product',
  ar: u(0x645, 0x639, 0x631, 0x648, 0x636, 0x629, 0x20, 0x644, 0x643, 0x644, 0x20, 0x645, 0x646, 0x62a, 0x62c),
};
// Today's catalog words (results.accordion.reviewsAvg / reviewsSub), for the pins.
const AVG: Record<'en' | 'ar', string> = {
  en: u(0x2605) + ' avg',
  ar: u(0x2605, 0x20, 0x645, 0x62a, 0x648, 0x633, 0x637),
};
const SUB: Record<'en' | 'ar', string> = {
  en: 'reviews across both',
  ar: u(
    0x622, 0x631, 0x627, 0x621, 0x20, 0x645, 0x646, 0x20, 0x643, 0x644, 0x627, 0x20, 0x627, 0x644,
    0x645, 0x646, 0x62a, 0x62c, 0x64a, 0x646,
  ),
};
const LANGS = ['en', 'ar'] as const;

// ------------------------------------------------------------------ bodies --

const ROOT: any[] = [
  { name: 'Imagination men', pros: ['Bright citrus opening'], cons: ['Soft drydown'] },
  { name: 'Creed Aventus', pros: ['Long wear'], cons: ['Pricey'] },
];
const IMAGINATION_PRAISE = 'Owners highlight a citrus aromatic profile.';
const AVENTUS_PRAISE = 'Owners say it opens with pineapple and bergamot.';
const imagination = (x: Record<string, unknown> = {}) => ({
  name: 'Imagination men',
  rating: null,
  review_count: 0,
  review_praise: IMAGINATION_PRAISE,
  ...x,
});
const aventus = (x: Record<string, unknown> = {}) => ({
  name: 'Creed Aventus',
  rating: 4.4,
  review_count: 5600,
  review_praise: AVENTUS_PRAISE,
  ...x,
});

function allText(node: any): string[] {
  const out: string[] = [];
  const walkNode = (n: any) => {
    if (n == null) return;
    if (typeof n === 'string') {
      out.push(n);
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walkNode);
      return;
    }
    if (n.children) n.children.forEach(walkNode);
  };
  walkNode(node);
  return out;
}

function show(reviewProducts: any[], lang: 'en' | 'ar') {
  mockLang = lang;
  I18N.changeLanguage(lang);
  // Harness check (passes at base): the real i18next now speaks this language.
  expect(I18N.language).toBe(lang);
  return render(
    <ResultsAccordion products={ROOT} reviewProducts={reviewProducts} winnerIndex={1} testID="acc" />,
  );
}

/** The Reviews header sub: the second Text under the closed toggle. */
function headerSub(r: ReturnType<typeof render>): string | null {
  const toggle = r.getByTestId('results-accordion-toggle-reviews');
  const texts = toggle.findAll((n: any) => n.type === 'Text');
  return texts.length >= 2 ? allText(texts[1].children).join('') : null;
}

/** Figures or the "across both" words that must not reach a one-sided header. */
const leaks = (sub: string | null, lang: 'en' | 'ar', figures: string[]) =>
  [...figures, SUB[lang]].filter((s) => (sub ?? '').includes(s));

beforeEach(() => {
  mockLang = 'en';
});
afterEach(() => {
  mockLang = 'en';
});

// ------------------------------------------------------------------ rows --

describe('INC-C1b B-d rows (fail at base)', () => {
  it('D1 the case: one side rated and counted, the header is row 2 with no figure (EN, AR)', () => {
    for (const lang of LANGS) {
      const r = show([imagination(), aventus()], lang);
      const sub = headerSub(r);
      expect({ lang, sub, leaks: leaks(sub, lang, ['5,600', '4.4']) }).toEqual({
        lang,
        sub: ROW2[lang],
        leaks: [],
      });
      r.unmount();
    }
  });

  it('D2 one side rated, both counted: row 2 (EN, AR)', () => {
    for (const lang of LANGS) {
      const r = show([imagination({ review_count: 1200 }), aventus()], lang);
      const sub = headerSub(r);
      expect({ lang, sub, leaks: leaks(sub, lang, ['6,800', '4.4']) }).toEqual({
        lang,
        sub: ROW2[lang],
        leaks: [],
      });
      r.unmount();
    }
  });

  it('D3 both rated, one side counted: row 2 (EN, AR)', () => {
    for (const lang of LANGS) {
      const r = show([imagination({ rating: 4.1, review_count: null }), aventus()], lang);
      const sub = headerSub(r);
      expect({ lang, sub, leaks: leaks(sub, lang, ['5,600', '4.4']) }).toEqual({
        lang,
        sub: ROW2[lang],
        leaks: [],
      });
      r.unmount();
    }
  });

  it('D4 the window case: Versace Eros EDP rated 4.6 across 12,000, Creed Aventus with no figure: row 2 (EN, AR)', () => {
    // The owner's window test of 22 Nov 2026 (case row W3): the header said
    // "4.6 avg, 12,000 reviews across both" while the 12,000 reviews are the
    // Versace side's only. The praise line is synthetic.
    for (const lang of LANGS) {
      const eros = {
        name: 'Versace Eros EDP',
        rating: 4.6,
        review_count: 12000,
        review_praise: 'Owners call it fresh with a sweet vanilla base.',
      };
      const r = show([eros, aventus({ rating: null, review_count: 0 })], lang);
      const sub = headerSub(r);
      expect({ lang, sub, leaks: leaks(sub, lang, ['12,000', '4.6']) }).toEqual({
        lang,
        sub: ROW2[lang],
        leaks: [],
      });
      r.unmount();
    }
  });
});

describe('INC-C1b B-d pins (pass at base)', () => {
  it('P-D1 both rated and counted: the weighted average and the total across both, as today (EN, AR)', () => {
    for (const lang of LANGS) {
      const r = show(
        [imagination({ rating: 4.4, review_count: 520 }), aventus({ rating: 4.6, review_count: 720 })],
        lang,
      );
      expect({ lang, sub: headerSub(r) }).toEqual({
        lang,
        sub: '4.5' + AVG[lang] + ' ' + MIDDOT + ' 1,240 ' + SUB[lang],
      });
      r.unmount();
    }
  });

  it('P-D2 none rated and none counted, counts only on both, ratings only on both: today\'s header (EN, AR)', () => {
    for (const lang of LANGS) {
      const none = show([imagination(), aventus({ rating: null, review_count: 0 })], lang);
      const noneSub = headerSub(none);
      none.unmount();
      const counts = show(
        [imagination({ review_count: 1200 }), aventus({ rating: null, review_count: 5600 })],
        lang,
      );
      const countsSub = headerSub(counts);
      counts.unmount();
      const ratings = show(
        [imagination({ rating: 4.4, review_count: 0 }), aventus({ rating: 4.2, review_count: 0 })],
        lang,
      );
      const ratingsSub = headerSub(ratings);
      ratings.unmount();
      expect({ lang, noneSub, countsSub, ratingsSub }).toEqual({
        lang,
        noneSub: SUB[lang],
        countsSub: '6,800 ' + SUB[lang],
        ratingsSub: '4.3' + AVG[lang] + ' ' + MIDDOT + ' ' + SUB[lang],
      });
    }
  });

  it('P-D3 the per-product body is unchanged: Creed Aventus keeps its star line, Imagination men its praise only', () => {
    const r = show([imagination(), aventus()], 'en');
    fireEvent.press(r.getByTestId('results-accordion-toggle-reviews'));
    const block = (i: number) => {
      const n = r.queryByTestId(`acc-reviews-praise-${i}`);
      return n ? allText(n.children) : null;
    };
    expect({ aventus: block(1), imagination: block(0) }).toEqual({
      aventus: ['Creed Aventus', '4.4 ' + MIDDOT + ' 5,600 reviews', AVENTUS_PRAISE],
      imagination: ['Imagination men', IMAGINATION_PRAISE],
    });
  });
});
