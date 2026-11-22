/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1b RED -- B-f: a one-word spec label fits on one line instead of
 * breaking inside the word (INC_C1B_UNIT_SPEC_V2.md section 8 and 10.5: rows
 * F1, F2, pins P-F1, P-F2; ruling RU-5).
 *
 * The contract this file fixes for GREEN:
 *  - ResultsAccordion spec table: the row label Text whose text has no
 *    whitespace carries numberOfLines={1}, adjustsFontSizeToFit and
 *    minimumFontScale={0.85} (the StatBlock precedent), in English and
 *    Arabic.
 *  - A label of several words keeps no line rule (it breaks at a space), the
 *    specs header's empty middle cell keeps none, and the label style is
 *    unchanged (width 96, 11 pt, weight 500, text.secondary, centred,
 *    uppercase, letterSpacing 0.4), so the table stays aligned.
 *
 * Data: the owner's phone test of 22 Nov 2026 (case row B-f: CONCENTRATION
 * broke as "CONCENTRATI" / "ON"; SCENT FAMILY wrapped at its space). Spec
 * values are synthetic.
 *
 * Harness: ResultsAccordion real; react-i18next answers through a real
 * i18next instance over the real catalogs (the INC-C1 lastChecked pattern).
 * F1: no new symbol; every base failure is an expect assertion. Arabic is
 * built from code points; this source stays ASCII.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { ResultsAccordion } from '../../src/components/results/ResultsAccordion';
import { colors } from '../../src/theme';

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

const u = (...cps: number[]) => String.fromCodePoint(...cps);

// results.spec.concentration and results.spec.scent_family as the catalogs hold them.
const ONE_WORD: Record<'en' | 'ar', string> = {
  en: 'Concentration',
  ar: u(0x627, 0x644, 0x62a, 0x631, 0x643, 0x64a, 0x632),
};
const TWO_WORDS: Record<'en' | 'ar', string> = {
  en: 'Scent family',
  ar: u(0x639, 0x627, 0x626, 0x644, 0x629, 0x20, 0x627, 0x644, 0x639, 0x637, 0x631),
};

const SPECS: any[] = [
  { name: 'Imagination men', specs: { concentration: 'EDP', scent_family: 'Citrus aromatic' } },
  { name: 'Creed Aventus', specs: { concentration: 'EDP', scent_family: 'Woody' } },
];

type Rendered = ReturnType<typeof render>;

const flat = (style: unknown): Record<string, any> => {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
};
const lineRule = (n: any) =>
  n
    ? {
        numberOfLines: n.props.numberOfLines,
        adjustsFontSizeToFit: n.props.adjustsFontSizeToFit,
        minimumFontScale: n.props.minimumFontScale,
      }
    : null;
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

/** Renders the accordion in one language with the Specs section open. */
function openSpecs(lang: 'en' | 'ar'): Rendered {
  mockLang = lang;
  I18N.changeLanguage(lang);
  // Harness check (passes at base): the real i18next now speaks this language.
  expect(I18N.language).toBe(lang);
  const r = render(<ResultsAccordion products={SPECS} specsProducts={SPECS} testID="acc" />);
  fireEvent.press(r.getByTestId('results-specs-toggle'));
  return r;
}

/** Every Text in the label column (the 96-pt cell), rows and header alike. */
const labelColumn = (r: Rendered) =>
  r.UNSAFE_root.findAll((n: any) => n.type === 'Text' && flat(n.props.style).width === 96);

const ONE_LINE = { numberOfLines: 1, adjustsFontSizeToFit: true, minimumFontScale: 0.85 };
const NO_RULE = { numberOfLines: undefined, adjustsFontSizeToFit: undefined, minimumFontScale: undefined };

beforeEach(() => {
  mockLang = 'en';
});
afterEach(() => {
  mockLang = 'en';
});

describe('INC-C1b B-f rows (fail at base)', () => {
  it('F1 EN: the one-word label "Concentration" fits on one line (shrink floor 0.85)', () => {
    const r = openSpecs('en');
    expect({ label: lineRule(r.queryByText(ONE_WORD.en)) }).toEqual({ label: ONE_LINE });
  });

  it('F2 AR: the one-word Concentration label fits on one line (shrink floor 0.85)', () => {
    const r = openSpecs('ar');
    expect({ label: lineRule(r.queryByText(ONE_WORD.ar)) }).toEqual({ label: ONE_LINE });
  });
});

describe('INC-C1b B-f pins (pass at base)', () => {
  it('P-F1 a label of two words and the header\'s empty middle cell carry no line rule (EN, AR)', () => {
    for (const lang of ['en', 'ar'] as const) {
      const r = openSpecs(lang);
      const empty = labelColumn(r).filter((n: any) => allText(n.children).join('') === '');
      expect({
        lang,
        twoWords: lineRule(r.queryByText(TWO_WORDS[lang])),
        emptyCells: empty.length,
        emptyRules: empty.map((n: any) => lineRule(n)),
      }).toEqual({ lang, twoWords: NO_RULE, emptyCells: 1, emptyRules: [NO_RULE] });
      r.unmount();
    }
  });

  it('P-F2 the label style is unchanged, so the table stays aligned (EN, AR)', () => {
    for (const lang of ['en', 'ar'] as const) {
      const r = openSpecs(lang);
      const n = r.queryByText(ONE_WORD[lang]);
      expect({ lang, style: n ? flat(n.props.style) : null }).toEqual({
        lang,
        style: {
          width: 96,
          fontSize: 11,
          fontWeight: '500',
          color: colors.text.secondary,
          textAlign: 'center',
          textTransform: 'uppercase',
          letterSpacing: 0.4,
        },
      });
      r.unmount();
    }
  });
});
