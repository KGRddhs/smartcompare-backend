/**
 * S74 CLIENT-TRUTH - supplements / OTC "not medical advice" note (AR-5,
 * decision MED=A).
 *
 * Spec CLIENT_TRUTH_SPEC.md section 3 + section 8 rows CT-M1/CT-M2, amended by
 * FABLE_RULINGS_CLIENT_TRUTH.md CT6: isSupplementComparison(result, products)
 * in src/services/resultHonesty.ts is true when (a) a category
 * (result.category_used, result.category, products[i].category_profile.category,
 * products[i].category) normalises to supplements or a backend synonym
 * (supplement / vitamin / vitamins), OR (b) a product name carries a token of
 * the backend _PHARMACY_TABLET_TOKENS set (app/services/extraction_service.py,
 * read cross-package here), OR (c) a product name carries a dose
 * number + (mg|mcg|iu) - never ml, so a perfume's "100ml" shows no note.
 * ResultsContent renders the note (testID results-content-medical-note) in
 * the "why" block whenever the helper is true.
 *
 * At main dfbda511 no note exists anywhere (0 hits medical/doctor/pharmacist
 * in en.json) and the helper does not exist.
 *
 * Harness: the mocks of __tests__/components/ResultsContent.render.test.tsx
 * :14-185, with a t that resolves from the REAL en.json.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render } from '@testing-library/react-native';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import * as honesty from '../../src/services/resultHonesty';

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  const entering = {
    duration: () => entering,
    delay: () => entering,
  };
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    FadeIn: entering,
    FadeInDown: entering,
  };
});

jest.mock('react-i18next', () => {
  const cat: Record<string, string> = require('../../src/i18n/en.json');
  const t = (key: string, opts?: Record<string, unknown>) => {
    let str: string = cat[key] ?? (opts?.defaultValue as string | undefined) ?? key;
    if (opts) {
      for (const [k, v] of Object.entries(opts)) {
        if (k === 'defaultValue') continue;
        str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      }
    }
    return str;
  };
  return { useTranslation: () => ({ t, i18n: { language: 'en' } }) };
});

jest.mock('../../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-top-match-badge'} />;
  },
}));
jest.mock('../../src/components/results/DimensionBars', () => ({
  DimensionBars: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-dim-bars'} />;
  },
}));
jest.mock('../../src/components/results/FactualVerdict', () => ({
  FactualVerdict: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-factual-verdict'} />;
  },
}));
jest.mock('../../src/components/results/ConfidencePills', () => ({
  ConfidencePills: ({ testID, onPillPress }: any) => {
    const { View, TouchableOpacity } = require('react-native');
    return (
      <View testID={testID ?? 'mock-confidence-pills'}>
        <TouchableOpacity testID="mock-pill-price" onPress={() => onPillPress?.('price')} />
      </View>
    );
  },
}));
jest.mock('../../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: ({ testID, onClose }: any) => {
    const { View, TouchableOpacity } = require('react-native');
    return (
      <View testID={testID ?? 'mock-confidence-sheet'}>
        <TouchableOpacity testID="mock-sheet-close" onPress={onClose} />
      </View>
    );
  },
}));
jest.mock('../../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-personalization-chip'} />;
  },
}));
jest.mock('../../src/components/hero/RevealBurst', () => ({
  RevealBurst: () => {
    const { View } = require('react-native');
    return <View testID="mock-reveal-burst" />;
  },
}));
jest.mock('../../src/components/CohortBadge', () => ({
  CohortBadge: ({ peerCount, governorate }: any) => {
    const { View, Text } = require('react-native');
    if (!peerCount || !governorate) return null;
    return (
      <View testID="mock-cohort-badge">
        <Text>{peerCount} - {governorate}</Text>
      </View>
    );
  },
}));
jest.mock('../../src/components/FeedbackCard', () => ({
  __esModule: true,
  default: ({ submitted, onSubmitted }: any) => {
    const { View, TouchableOpacity } = require('react-native');
    return (
      <View testID="mock-feedback-card">
        <TouchableOpacity testID="mock-feedback-submit" onPress={onSubmitted} />
        {submitted ? <View testID="mock-feedback-thanks" /> : null}
      </View>
    );
  },
}));
jest.mock('../../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-accordion'} />;
  },
}));
jest.mock('../../src/services/sourceMethod', () => ({
  anyEstimated: jest.fn(() => false),
  isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd'),
}));

import { ResultsContent } from '../../src/components/results/ResultsContent';

const EN = en as unknown as Record<string, string>;
const AR = ar as unknown as Record<string, string>;
const NOTE = 'results-content-medical-note';

function product(name: string, extra: Record<string, unknown> = {}): any {
  return {
    name,
    brand: name.split(' ')[0],
    price: { amount: 5, currency: 'BHD', retailer: 'Shop' },
    pros: ['Good'],
    cons: ['Pricey'],
    ...extra,
  };
}

const mockScoringV2: any = {
  overall_score: { product_a: 72, product_b: 81 },
  dimensions: [
    { dim: 'quality', winner_index: 1, leftPct: 38, rightPct: 62 },
    { dim: 'value', winner_index: 1, leftPct: 30, rightPct: 70 },
    { dim: 'price', winner_index: 0, leftPct: 56, rightPct: 44 },
  ],
  confidence_legs: { price: 'high', reviews: 'medium', specs: 'high' },
  factual_verdict: { line1: 'B takes 2 of 3 dimensions', line2: 'Value holds the most weight' },
  personalization: { applied_shifts: [] },
  comparison_quality: 'normal',
  confidence_details: {},
};

function propsFor(products: any[], resultExtra: Record<string, unknown> = {}): any {
  const result: any = {
    overview: {
      winner: {
        product_index: 1,
        name: products[1].name,
        reason: 'Fits your priorities',
        key_tradeoff: 'Costs a little more',
      },
      products,
    },
    comparison: {},
    recommendation: `${products[1].name} wins`,
    metadata: { query: 'a-vs-b', elapsed_seconds: 14 },
    ...resultExtra,
  };
  return {
    result,
    products,
    winnerIndex: 1 as 0 | 1,
    scoring_v2: mockScoringV2,
    comparisonId: 'cmp-123',
    cohortPeerCount: 0,
    cohortGovernorate: 'Capital',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-123',
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
  };
}

function textOf(inst: any): string {
  if (inst == null) return '';
  if (typeof inst === 'string' || typeof inst === 'number') return String(inst);
  return (inst.children ?? []).map(textOf).join('');
}

function noteShown(props: any): boolean {
  const { queryByTestId, unmount } = render(<ResultsContent {...props} />);
  const shown = queryByTestId(NOTE) !== null;
  unmount();
  return shown;
}

const NEUTRAL = [product('Nature Made D3'), product('Solgar D3')];

const EXTRACTION_PY = fs.readFileSync(
  path.resolve(__dirname, '../../../app/services/extraction_service.py'),
  'utf8',
);

function backendPharmacyTokens(): string[] {
  const m = EXTRACTION_PY.match(/^_PHARMACY_TABLET_TOKENS\s*=\s*\(([\s\S]*?)\)/m);
  if (!m) throw new Error('_PHARMACY_TABLET_TOKENS not found in app/services/extraction_service.py');
  return Array.from(m[1].matchAll(/"([^"]+)"/g)).map((x) => x[1]);
}

describe('S74 CLIENT-TRUTH medical note (rendered)', () => {
  it('CT-M1: category_used supplements renders results-content-medical-note with the catalog results.medicalNote', () => {
    const { queryByTestId } = render(
      <ResultsContent {...propsFor(NEUTRAL, { category_used: 'supplements' })} />,
    );
    const node = queryByTestId(NOTE);
    expect(node).not.toBeNull();
    expect(EN['results.medicalNote']).toMatch(/not medical advice/i);
    expect(typeof AR['results.medicalNote']).toBe('string');
    expect(textOf(node)).toBe(EN['results.medicalNote']);
  });

  it('CT-M1: the note is independent of the degraded note (both render on a degraded supplements result)', () => {
    const { queryByTestId } = render(
      <ResultsContent
        {...propsFor(NEUTRAL, {
          category_used: 'supplements',
          comparison: { error: 'verdict generation unavailable' },
        })}
      />,
    );
    expect(queryByTestId('results-content-degraded-note')).not.toBeNull();
    expect(queryByTestId(NOTE)).not.toBeNull();
  });

  it('CT-M2: only products[0].category_profile.category "Vitamins" (category_used other) renders the note', () => {
    const products = [
      product('Nature Made D3', { category_profile: { category: 'Vitamins', fields: [] } }),
      product('Solgar D3'),
    ];
    expect(noteShown(propsFor(products, { category_used: 'other' }))).toBe(true);
  });

  it('CT6 arm (a): result.category, products[i].category and case variants of the backend synonyms render the note', () => {
    const cases: [string, any][] = [
      ['result.category Supplement', propsFor(NEUTRAL, { category: 'Supplement' })],
      ['category_used SUPPLEMENTS', propsFor(NEUTRAL, { category_used: 'SUPPLEMENTS' })],
      [
        'products[1].category vitamin',
        propsFor([product('Nature Made D3'), product('Solgar D3', { category: 'vitamin' })]),
      ],
      [
        'products[1].category_profile vitamins',
        propsFor([
          product('Nature Made D3'),
          product('Solgar D3', { category_profile: { category: 'vitamins', fields: [] } }),
        ]),
      ],
    ];
    const missing = cases.filter(([, props]) => !noteShown(props)).map(([label]) => label);
    expect(missing).toEqual([]);
  });

  it('CT6 arm (b): a pharmacy token in a product name (Panadol / Adol, category other) renders the note', () => {
    const products = [product('Panadol Extra'), product('Adol Extra')];
    expect(noteShown(propsFor(products, { category_used: 'other' }))).toBe(true);
  });

  it('CT6 arm (c): a dose number + mg / mcg / IU in a product name (category other) renders the note', () => {
    const cases = ['Brand A 500mg', 'Brand B 1000 IU', 'Brand C 400 mcg'];
    const missing = cases.filter(
      (name) => !noteShown(propsFor([product(name), product('Brand Z Daily')], { category_used: 'other' })),
    );
    expect(missing).toEqual([]);
  });

  it('CT6 GUARD perfume negative: "Dior Sauvage EDP 100ml" (ml is not a dose) shows no note', () => {
    const products = [
      product('Dior Sauvage EDP 100ml', { category_profile: { category: 'fragrances', fields: [] } }),
      product('Bleu de Chanel EDP 100 ml', { category_profile: { category: 'fragrances', fields: [] } }),
    ];
    expect(noteShown(propsFor(products, { category_used: 'fragrances' }))).toBe(false);
  });

  it('CT6 GUARD electronics negative: an electronics pair shows no note', () => {
    const products = [
      product('iPhone 15 Pro 256GB', { category_profile: { category: 'electronics', fields: [] } }),
      product('Galaxy S24 Ultra 12GB RAM', { category_profile: { category: 'electronics', fields: [] } }),
    ];
    expect(noteShown(propsFor(products, { category_used: 'electronics', category: 'electronics' }))).toBe(
      false,
    );
  });
});

/** Ruling Y3: backend tokens that are context, not a pharmacy signal, on their own. */
const CONTEXT_ONLY = ['vinegar', 'glucose', 'flu', 'dose', 'dosage', 'pharmacy'];

describe('S74 CLIENT-TRUTH isSupplementComparison (cross-package token mirror)', () => {
  it('CT6 arm (b) mirror + Y3: every backend token outside PHARMACY_CONTEXT_ONLY_TOKENS fires; a context-only token alone never does', () => {
    const tokens = backendPharmacyTokens();
    expect(tokens.length).toBeGreaterThanOrEqual(10);
    expect(CONTEXT_ONLY.filter((tok) => !tokens.includes(tok))).toEqual([]);
    const fn = (honesty as any).isSupplementComparison;
    expect(typeof fn).toBe('function');
    const contextOnly = (honesty as any).PHARMACY_CONTEXT_ONLY_TOKENS;
    expect(Array.isArray(contextOnly)).toBe(true);
    expect([...(contextOnly as string[])].sort()).toEqual([...CONTEXT_ONLY].sort());
    const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
    const fires = (tok: string) =>
      fn({ category_used: 'other' }, [{ name: `Acme ${cap(tok)} Extra` }, { name: 'Acme Plain' }]) === true;
    expect({
      missed: tokens.filter((tok) => !CONTEXT_ONLY.includes(tok) && !fires(tok)),
      firedAlone: tokens.filter((tok) => CONTEXT_ONLY.includes(tok) && fires(tok)),
    }).toEqual({ missed: [], firedAlone: [] });
  });
});

describe('S74 CLIENT-TRUTH trigger reads the product identity and the query (rulings Y1-Y3)', () => {
  const shown = (products: any[], resultExtra: Record<string, unknown> = {}) =>
    noteShown(propsFor(products, resultExtra));
  const plain = () => [product('Daily', { brand: 'Acme' }), product('Daily', { brand: 'Zeta' })];

  it('Y1: the trigger reads brand + name + variant (the overview projection) and the raw result.query', () => {
    expect({
      brandNamePair: shown([product('Extra', { brand: 'Panadol' }), product('Extra', { brand: 'Adol' })]),
      doseInVariant: shown([
        product('Daily', { brand: 'Acme', variant: '500mg' }),
        product('Daily', { brand: 'Zeta' }),
      ]),
      queryOnly: shown(plain(), { query: 'Panadol Extra vs Adol Extra' }),
      appleIphone: shown([product('iPhone 15', { brand: 'Apple' }), product('Galaxy S24', { brand: 'Samsung' })]),
      phoneQuery: shown(plain(), { query: 'iPhone 15 vs Galaxy S24' }),
    }).toEqual({
      brandNamePair: true,
      doseInVariant: true,
      queryOnly: true,
      appleIphone: false,
      phoneQuery: false,
    });
  });

  it('Y2: a dose followed by a pack count is a dose; a unit glued to a digit is a model code; ml is never a dose', () => {
    const one = (name: string, extra: Record<string, unknown> = {}) =>
      shown([product(name, extra), product('Brand Z Daily')], { category_used: 'other' });
    expect({
      panadolPack: one('Panadol Extra 500mg 24 tablets'),
      vitaminD3Pack: one('Vitamin D3 1000 IU 60 softgels'),
      nurofenPack: one('Nurofen 200mg 24 Tablets'),
      mercedes: one('ML350', { brand: 'Mercedes' }),
      mg5: one('2024 MG5', { brand: 'MG' }),
      dior: one('Dior Sauvage EDP 100ml', { category_profile: { category: 'fragrances', fields: [] } }),
    }).toEqual({
      panadolPack: true,
      vitaminD3Pack: true,
      nurofenPack: true,
      mercedes: false,
      mg5: false,
      dior: false,
    });
  });

  it('Y3: context-only tokens never fire alone and tokens match whole words only', () => {
    expect({
      whiteVinegar: shown(
        [
          product('White Vinegar', { brand: 'Heinz', category_profile: { category: 'grocery', fields: [] } }),
          product('Apple Cider Vinegar', { brand: 'Bragg', category_profile: { category: 'grocery', fields: [] } }),
        ],
        { category_used: 'grocery' },
      ),
      fluke: shown(
        [
          product('Fluke 117 Multimeter', { category_profile: { category: 'electronics', fields: [] } }),
          product('Klein MM400 Multimeter', { category_profile: { category: 'electronics', fields: [] } }),
        ],
        { category_used: 'electronics' },
      ),
      adolfo: shown(
        [
          product('Adolfo Dominguez Agua Fresca EDT 120ml', {
            brand: 'Adolfo Dominguez',
            category_profile: { category: 'fragrances', fields: [] },
          }),
          product('Bleu de Chanel EDP 100 ml', { category_profile: { category: 'fragrances', fields: [] } }),
        ],
        { category_used: 'fragrances' },
      ),
      paracetamol: shown([product('Paracetamol 500mg'), product('Brand Z Daily')], { category_used: 'other' }),
    }).toEqual({ whiteVinegar: false, fluke: false, adolfo: false, paracetamol: true });
  });

  it('Y3: a token glued to a letter on either side never fires (whole-word boundary on both sides)', () => {
    const fn = (honesty as any).isSupplementComparison;
    const active = backendPharmacyTokens().filter((tok) => !CONTEXT_ONLY.includes(tok));
    expect(active.length).toBeGreaterThanOrEqual(5);
    const fires = (word: string) =>
      fn({ category_used: 'other' }, [{ name: `Acme ${word} Extra` }, { name: 'Acme Plain' }]) === true;
    expect({
      gluedBefore: active.filter((tok) => fires(`X${tok}`)),
      gluedAfter: active.filter((tok) => fires(`${tok}x`)),
      bare: active.filter((tok) => !fires(tok)),
    }).toEqual({ gluedBefore: [], gluedAfter: [], bare: [] });
  });
});

/** Spec section 3 results.medicalNote AR text, as \u escapes (ruling Y5). */
const AR_MEDICAL_NOTE =
  '\u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0639\u0627\u0645\u0629 \u0641\u0642\u0637 ' +
  '\u0648\u0644\u064a\u0633\u062a \u0646\u0635\u064a\u062d\u0629 \u0637\u0628\u064a\u0629. ' +
  '\u0627\u0633\u062a\u0634\u0631 \u0627\u0644\u0635\u064a\u062f\u0644\u064a \u0623\u0648 ' +
  '\u0627\u0644\u0637\u0628\u064a\u0628 \u0642\u0628\u0644 \u0627\u0644\u0627\u0633\u062a\u062e\u062f\u0627\u0645.';

describe('S74 CLIENT-TRUTH medical note content (ruling Y5)', () => {
  it('Y5: EN says not medical advice and names a pharmacist or doctor; AR equals the spec text', () => {
    const enNote = EN['results.medicalNote'];
    expect({
      enNotMedicalAdvice: /not medical advice/i.test(enNote),
      enPharmacistOrDoctor: /pharmacist|doctor/i.test(enNote),
      arIsSpecText: AR['results.medicalNote'] === AR_MEDICAL_NOTE,
    }).toEqual({ enNotMedicalAdvice: true, enPharmacistOrDoctor: true, arIsSpecText: true });
  });
});

describe('S74 CLIENT-TRUTH PHARMACY_TABLET_TOKENS equality (ruling G4)', () => {
  it('G4: resultHonesty exports PHARMACY_TABLET_TOKENS equal to the backend _PHARMACY_TABLET_TOKENS set (no extra, no missing, no duplicate)', () => {
    const backend = backendPharmacyTokens();
    expect(backend.length).toBeGreaterThanOrEqual(10);
    const client = (honesty as any).PHARMACY_TABLET_TOKENS;
    expect(Array.isArray(client)).toBe(true);
    const list = client as string[];
    expect(list.length).toBe(new Set(list).size);
    expect([...list].sort()).toEqual([...new Set(backend)].sort());
  });
});
