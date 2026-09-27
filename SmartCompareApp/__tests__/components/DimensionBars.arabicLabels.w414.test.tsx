/**
 * W4-14 Part A3 — DimensionBars renders the dimension label through the catalog.
 *
 * REAL i18next with the REAL en.json / ar.json (a per-file react-i18next factory
 * that builds one instance; the language is switched per describe). The 9-category
 * row fixture is the probe's `dims_reach.json` `reach` table (what
 * build_dimensions_v2 emits at HEAD), inlined.
 *
 * RED = fails at the unit base 3985eaac (72/72 rows render the backend's raw
 * English label under ar); PIN = green there and must stay green.
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

jest.mock('react-i18next', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const i18next = require('i18next');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const enJson = require('../../src/i18n/en.json');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const arJson = require('../../src/i18n/ar.json');
  const inst = i18next.createInstance();
  inst.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: enJson }, ar: { translation: arJson } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  });
  const t = (key: string, opts?: Record<string, unknown>) => inst.t(key, opts);
  return {
    useTranslation: () => ({ t, i18n: inst }),
    __inst: inst,
    initReactI18next: { type: '3rdParty', init: () => {} },
  };
});

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  impactAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'Light', Medium: 'Medium' },
}));

import { DimensionBars } from '../../src/components/results/DimensionBars';
import ar from '../../src/i18n/ar.json';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { __inst: inst } = require('react-i18next');
const arCat = ar as Record<string, string>;

const REACH: Record<string, [string, string][]> = {
  electronics: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['performance', 'Performance'], ['build_quality', 'Build quality'], ['feature', 'Features'], ['ecosystem', 'Ecosystem'], ['futureproof', 'Future-proofing']],
  grocery: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['nutrition', 'Nutrition'], ['ingredient', 'Ingredients'], ['taste', 'Taste'], ['dietary', 'Dietary fit'], ['availability', 'Availability']],
  supplements: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['efficacy', 'Efficacy'], ['safety', 'Safety'], ['dosage', 'Dosage'], ['form', 'Form'], ['trust', 'Trust']],
  makeup: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['shade', 'Shade range'], ['longevity', 'Longevity'], ['skin_compat', 'Skin compatibility'], ['finish', 'Finish'], ['ingredient_safety', 'Ingredient safety']],
  skincare: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['actives', 'Active ingredients'], ['evidence', 'Evidence'], ['skin_compat', 'Skin compatibility'], ['formulation', 'Formulation'], ['sensory', 'Sensory']],
  haircare: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['hair_match', 'Hair match'], ['results', 'Results'], ['ingredient', 'Ingredients'], ['scent', 'Scent'], ['scalp', 'Scalp']],
  fragrances: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['character', 'Character'], ['longevity', 'Longevity'], ['projection', 'Projection'], ['versatility', 'Versatility'], ['presentation', 'Presentation']],
  fashion: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['craft', 'Craftsmanship'], ['fit', 'Fit'], ['style', 'Style'], ['durability', 'Durability'], ['heritage', 'Heritage']],
  other: [['price', 'Price'], ['reviews', 'Reviews'], ['value', 'Value'], ['function', 'Function'], ['build', 'Build'], ['review', 'Reviews'], ['reliability', 'Reliability'], ['feature_match', 'Feature match']],
};

function texts(node: any, acc: string[] = []): string[] {
  if (node == null) return acc;
  if (typeof node === 'string') {
    acc.push(node);
    return acc;
  }
  if (Array.isArray(node)) {
    node.forEach((n) => texts(n, acc));
    return acc;
  }
  if (node.children) texts(node.children, acc);
  return acc;
}

/** Render every category (expand row pressed) and return [key, backendLabel, rowTexts]. */
function renderAllRows(): [string, string, string[]][] {
  const out: [string, string, string[]][] = [];
  for (const pairs of Object.values(REACH)) {
    const dims = pairs.map(([key, label], i) => ({
      key, label, score_a: 80 - i, score_b: 60 + i, delta_text: '', confidence: 'medium' as const,
    }));
    const r = render(<DimensionBars dimensions={dims as any} winnerIndex={0} testID="bars" />);
    const expand = r.queryByTestId('bars-expand-row');
    if (expand) fireEvent.press(expand);
    for (const [key, label] of pairs) {
      const row = r.queryByTestId(`bars-row-${key}`);
      out.push([key, label, row ? texts(row.children as any) : []]);
    }
    r.unmount();
  }
  return out;
}

describe('W4-14 DimensionBars labels under lng=ar (real catalog)', () => {
  beforeEach(() => {
    inst.changeLanguage('ar');
  });

  it('RED 5: DimensionRow renders the Arabic label for all 72 rows (9 categories, expand pressed)', () => {
    const rows = renderAllRows();
    expect(rows).toHaveLength(72);
    expect(rows.filter(([, , t]) => t.length === 0)).toEqual([]);
    const rawEnglish = rows.filter(([, label, t]) => t.includes(label)).map(([k]) => k);
    expect({ rawEnglishRows: rawEnglish.length }).toEqual({ rawEnglishRows: 0 });
    const wrong = rows
      .filter(([key, , t]) => !arCat[`results.dimension.${key}`] || t[0] !== arCat[`results.dimension.${key}`])
      .map(([k]) => k);
    expect(wrong).toEqual([]);
  });

  it('RED 6: InsufficientRow renders the Arabic label (latent path: data_insufficient has 0 backend emitters)', () => {
    const r = render(
      <DimensionBars
        dimensions={[{ key: 'longevity', label: 'Longevity', score_a: null, score_b: null, delta_text: '', data_insufficient: true } as any]}
        winnerIndex={0}
        testID="bars"
      />,
    );
    const t = texts(r.getByTestId('bars-row-longevity-insufficient').children as any);
    r.unmount();
    expect(t).not.toContain('Longevity');
    expect(t[0]).toBe(arCat['results.dimension.longevity']);
    expect(typeof t[0]).toBe('string');
  });

  it("RED 7: a point-math delta_text ('+18pt') on a non-hero row falls back to the Arabic label", () => {
    const r = render(
      <DimensionBars
        dimensions={[{ key: 'projection', label: 'Projection', score_a: 80, score_b: 60, delta_text: '+18pt', confidence: 'medium' } as any]}
        winnerIndex={0}
        testID="bars"
      />,
    );
    const t = texts(r.getByTestId('bars-row-projection').children as any);
    r.unmount();
    const arLabel = arCat['results.dimension.projection'];
    expect(t).not.toContain('Projection');
    expect(t).not.toContain('+18pt');
    expect(arLabel).toBeDefined();
    // label + the point-math fallback caption, both Arabic
    expect(t.filter((s) => s === arLabel)).toHaveLength(2);
  });

  it('PIN 9: an uncatalogued key renders its backend label under lng=ar', () => {
    const r = render(
      <DimensionBars
        dimensions={[{ key: 'popularity', label: 'Popularity', score_a: 80, score_b: 60, delta_text: '', confidence: 'medium' } as any]}
        winnerIndex={0}
        testID="bars"
      />,
    );
    const t = texts(r.getByTestId('bars-row-popularity').children as any);
    r.unmount();
    expect(t[0]).toBe('Popularity');
  });
});

describe('W4-14 DimensionBars labels under lng=en (real catalog) — the EN identity gate', () => {
  beforeEach(() => {
    inst.changeLanguage('en');
  });
  afterAll(() => {
    inst.changeLanguage('ar');
  });

  it('PIN 8: every one of the 72 rows renders the backend label byte-identically', () => {
    const rows = renderAllRows();
    expect(rows).toHaveLength(72);
    const wrong = rows.filter(([, label, t]) => t[0] !== label).map(([k, l, t]) => [k, l, t[0]]);
    expect(wrong).toEqual([]);
  });
});
