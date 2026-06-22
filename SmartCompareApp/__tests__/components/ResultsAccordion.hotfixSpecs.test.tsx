/**
 * Bundle E S3 hotfix — ResultsAccordion specs population from real
 * backend shape.
 *
 * Device walk (image #10) showed the Specs accordion expanded with the
 * two product-name header cells but NO spec rows underneath. Curl probe
 * against Railway confirmed `specs.products[i].specs` includes the
 * internal diagnostic key `_field_confidence` whose value is a nested
 * object — that key was leaking into the table and the row render
 * rendered "[object Object]" for the cell value.
 *
 * This regression net pins the new filter rules:
 *   - keys starting with `_` are excluded (diagnostic, never user-facing)
 *   - values that are objects (even when the key is otherwise allowed)
 *     are excluded so a stray nested struct can never reach the table
 *
 * Fixture mirrors the actual production Railway response shape
 * (probed via curl 2026-06-01).
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

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
  }),
}));

import { ResultsAccordion } from '../../src/components/results/ResultsAccordion';

// Real Railway response shape (curl probe 2026-06-01)
const realSpecsProducts: any = [
  {
    brand: 'Apple',
    name: 'iPhone 15',
    specs: {
      os: 'iOS v17',
      ram: '6 GB',
      weight: '171 g',
      battery: '3349 mAh',
      display: '6.1 inches',
      storage: '128 GB',
      processor: 'Apple A16',
      rear_camera: '48 MP',
      connectivity: 'Wi-Fi 6, 5G, Bluetooth 5.3',
      front_camera: 'N/A',
      water_resistance: 'IP68',
      _field_confidence: {
        os: 'snippet',
        ram: 'snippet',
        weight: 'smart_fallback',
      },
    },
  },
  {
    brand: 'Samsung',
    name: 'Galaxy S24',
    specs: {
      os: 'Android v14',
      ram: '8 GB',
      weight: '167 g',
      battery: '4000 mAh',
      display: '6.2 inches',
      storage: '128 GB',
      processor: 'Snapdragon 8 Gen 3',
      rear_camera: '50 MP',
      connectivity: 'Wi-Fi 7, 5G, Bluetooth 5.3',
      front_camera: '12 MP',
      water_resistance: 'IP68',
      _field_confidence: { os: 'snippet' },
    },
  },
];

const minimalProducts: any = [
  { name: 'iPhone 15', brand: 'Apple', price: null, specs: realSpecsProducts[0].specs },
  { name: 'Galaxy S24', brand: 'Samsung', price: null, specs: realSpecsProducts[1].specs },
];

describe('ResultsAccordion — real backend shape (Bundle E S3 hotfix)', () => {
  it('populates spec rows when fed the live `specs.products` shape', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={minimalProducts} specsProducts={realSpecsProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
    // At least the well-known spec keys (`replace(/_/g, ' ')` for display)
    expect(getByText('os')).toBeTruthy();
    expect(getByText('ram')).toBeTruthy();
    expect(getByText('rear camera')).toBeTruthy();
    expect(getByText('water resistance')).toBeTruthy();
    // values land for both products
    expect(getByText('iOS v17')).toBeTruthy();
    expect(getByText('Android v14')).toBeTruthy();
    expect(getByText('48 MP')).toBeTruthy();
    expect(getByText('50 MP')).toBeTruthy();
  });

  it('excludes diagnostic `_field_confidence` key from the table', () => {
    const { getByTestId, queryByText } = render(
      <ResultsAccordion products={minimalProducts} specsProducts={realSpecsProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // Neither the unprefixed nor the dash-rendered form should appear
    expect(queryByText('_field_confidence')).toBeNull();
    expect(queryByText(' field confidence')).toBeNull();
    expect(queryByText('field confidence')).toBeNull();
    // And the dreaded object stringification must NOT escape
    expect(queryByText('[object Object]')).toBeNull();
  });

  it('excludes the "N/A" string value from rendered rows', () => {
    const { getByTestId, queryByText } = render(
      <ResultsAccordion products={minimalProducts} specsProducts={realSpecsProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // front_camera="N/A" on iPhone 15 — that string must NOT appear as a
    // cell value. (Galaxy has "12 MP" so the row stays visible.)
    expect(queryByText('N/A')).toBeNull();
  });

  it('drops the row (no silent one-sided dash) when one product has an object value at a shared key', () => {
    // Task E3 (frag-content-quality WS-E / P7 / FE-3): an object value coerces
    // to the em-dash "—" (missing) on one product; with a real string on the
    // other the row is one-sided → DROPPED to keep the table symmetric
    // (re-baselined from the prior silent value·LABEL·"—" behavior).
    const oneObjOneStr: any = [
      { ...realSpecsProducts[0], specs: { ...realSpecsProducts[0].specs, ram: { nested: 'bad' } } },
      realSpecsProducts[1],
    ];
    const minimal = [
      { name: oneObjOneStr[0].name, brand: oneObjOneStr[0].brand, price: null, specs: oneObjOneStr[0].specs },
      { name: oneObjOneStr[1].name, brand: oneObjOneStr[1].brand, price: null, specs: oneObjOneStr[1].specs },
    ];
    const { getByTestId, queryByText } = render(
      <ResultsAccordion products={minimal as any} specsProducts={oneObjOneStr} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // The one-sided 'ram' row is dropped (symmetric-contract).
    expect(queryByText('ram')).toBeNull();
    // and the object stringification never escapes either way.
    expect(queryByText('[object Object]')).toBeNull();
  });

  it('header row shows the two product names (carry-over invariant)', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={minimalProducts} specsProducts={realSpecsProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByText('iPhone 15')).toBeTruthy();
    expect(getByText('Galaxy S24')).toBeTruthy();
  });
});

// ─── Highlights mini-section ─────────────────────────────────────────
// Live Railway response (probed by dispatcher 2026-06-02) for the
// q=iPhone+15+vs+Galaxy+S24 cached path returns:
//   specs.products[i].specs = { color: "N/A", weight: "N/A", ... }    // ALL N/A
//   specs.products[i].spec_advantages = ["A16 Bionic chipset…", ...]  // POPULATED
// When every spec row collapses to em-dash, the accordion is visually
// empty. Recommendation (2) from dispatcher: always render
// `spec_advantages` as a Highlights mini-section above the spec table
// so the accordion is never empty.
const advProducts: any = [
  {
    brand: '',
    name: 'iPhone 15',
    spec_advantages: [
      'A16 Bionic chipset for enhanced performance.',
      'Lighter weight at 171g.',
    ],
    specs: {
      color: 'N/A',
      weight: 'N/A',
      features: 'N/A',
    },
  },
  {
    brand: '',
    name: 'Galaxy S24',
    spec_advantages: [
      'Display brightness of 2,600 nits.',
      '50MP main camera sensor.',
    ],
    specs: {
      color: 'N/A',
      weight: 'N/A',
      features: 'N/A',
    },
  },
];

// Design-structure pass (2026-06-16): the spec_advantages "Highlights"
// mini-section was REMOVED from the Specs body to match the design-system
// reference (SpecRow, ResultsScreen.jsx 265-284 — value · CENTERED-label ·
// value, no highlights block, no toggle). The spec TABLE itself stays.
describe('ResultsAccordion — Specs body no longer renders the Highlights block', () => {
  it('does NOT render the spec_advantages Highlights block even when present', () => {
    const { getByTestId, queryByTestId } = render(
      <ResultsAccordion
        products={minimalProducts}
        specsProducts={advProducts}
      />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(queryByTestId('results-spec-advantages')).toBeNull();
    expect(queryByTestId('results-spec-advantages-product-0')).toBeNull();
    expect(queryByTestId('results-spec-advantages-product-1')).toBeNull();
  });

  it('does NOT render the spec_advantages sentences as text', () => {
    const { getByTestId, queryByText } = render(
      <ResultsAccordion
        products={minimalProducts}
        specsProducts={advProducts}
      />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(queryByText('A16 Bionic chipset for enhanced performance.')).toBeNull();
    expect(queryByText('Display brightness of 2,600 nits.')).toBeNull();
  });

  it('still renders the spec table rows (em-dash when all N/A)', () => {
    const { getByTestId, getAllByText } = render(
      <ResultsAccordion
        products={minimalProducts}
        specsProducts={advProducts}
      />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
    // Spec rows still rendered — values em-dash since all N/A
    // (3 keys × 2 products = 6 em-dashes minimum)
    expect(getAllByText('—').length).toBeGreaterThanOrEqual(6);
  });
});
