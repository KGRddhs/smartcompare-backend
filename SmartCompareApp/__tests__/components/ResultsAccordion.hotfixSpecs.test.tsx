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

  it('renders the em-dash placeholder when one product has an object value at a shared key', () => {
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
    // 'ram' key still surfaces (from the other product's string value)
    expect(queryByText('ram')).toBeTruthy();
    // but the object-valued cell renders the em-dash, not "[object Object]"
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
