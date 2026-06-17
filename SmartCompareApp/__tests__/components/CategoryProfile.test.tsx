/**
 * CategoryProfile — Faithful-results Phase 3.1 (Contract 1) tests.
 *
 * Pins the LOCKED Contract 1 behavior: one generic component renders the
 * backend's ordered `products[i].category_profile.fields` as a curated
 * `label · value` block per product, with i18n-key-then-backend-label
 * resolution, winner-first ordering, the hide-when-empty rule, and the
 * no-blank-second-product symmetry rule. Exercised across 3 representative
 * categories (fragrances / electronics / supplements).
 */

import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    // Real-ish i18n: a tiny catalog covers a couple of keys so we can prove
    // the catalog string WINS over the backend label; every other key falls
    // back to opts.defaultValue (the backend label).
    t: (key: string, opts?: Record<string, unknown>) => {
      const catalog: Record<string, string> = {
        'results.categoryProfile.title': 'At a glance',
        'results.spec.scent_family': 'Scent family',
        'results.spec.storage': 'Storage',
      };
      if (catalog[key]) return catalog[key];
      return (opts?.defaultValue as string) ?? key;
    },
  }),
}));

import { CategoryProfile } from '../../src/components/results/CategoryProfile';

const fragranceProducts: any = [
  {
    name: 'Tobacco Vanille',
    category_profile: {
      category: 'fragrances',
      fields: [
        { key: 'scent_family', label: 'Scent family', value: 'Amber / Spicy' },
        { key: 'notes_top', label: 'Top notes', value: 'Bergamot, Black pepper' },
        { key: 'longevity', label: 'Longevity', value: '8-10 hours' },
      ],
    },
  },
  {
    name: 'Ombré Leather',
    category_profile: {
      category: 'fragrances',
      fields: [
        { key: 'scent_family', label: 'Scent family', value: 'Leather / Floral' },
        { key: 'notes_top', label: 'Top notes', value: 'Cardamom' },
        { key: 'longevity', label: 'Longevity', value: '6-8 hours' },
      ],
    },
  },
];

const baseProps: any = {
  products: fragranceProducts,
  winnerIndex: 0 as 0 | 1,
  testID: 'cat-profile',
};

describe('CategoryProfile — Contract 1', () => {
  it('renders the block title + a column for each product', () => {
    const { getByText, getByTestId } = render(<CategoryProfile {...baseProps} />);
    expect(getByText('At a glance')).toBeTruthy();
    expect(getByTestId('cat-profile-col-0')).toBeTruthy();
    expect(getByTestId('cat-profile-col-1')).toBeTruthy();
  });

  it('renders each field as label · value in order, both products', () => {
    const { getByTestId, getByText } = render(<CategoryProfile {...baseProps} />);
    // Field rows keyed by product index + field key.
    expect(getByTestId('cat-profile-field-0-scent_family')).toBeTruthy();
    expect(getByTestId('cat-profile-field-0-notes_top')).toBeTruthy();
    expect(getByTestId('cat-profile-field-0-longevity')).toBeTruthy();
    expect(getByTestId('cat-profile-field-1-scent_family')).toBeTruthy();
    // Values surfaced.
    expect(getByText('Amber / Spicy')).toBeTruthy();
    expect(getByText('Leather / Floral')).toBeTruthy();
    expect(getByText('8-10 hours')).toBeTruthy();
  });

  it('prefers the i18n catalog label over the backend label, and falls back when absent', () => {
    const products: any = [
      {
        name: 'X',
        category_profile: {
          category: 'fragrances',
          fields: [
            // Catalog has results.spec.scent_family → "Scent family" (wins).
            { key: 'scent_family', label: 'BACKEND_SCENT_LABEL', value: 'Woody' },
            // No catalog entry for results.spec.sillage → backend label used.
            { key: 'sillage', label: 'Sillage', value: 'Strong' },
          ],
        },
      },
    ];
    const { getByText, queryByText } = render(
      <CategoryProfile products={products} testID="cat-profile" />
    );
    expect(getByText('Scent family')).toBeTruthy(); // catalog wins
    expect(queryByText('BACKEND_SCENT_LABEL')).toBeNull(); // backend label NOT used
    expect(getByText('Sillage')).toBeTruthy(); // fallback to backend label
  });

  it('renders the winner column first with a ★ + accent name', () => {
    // winnerIndex 1 → product 1 column should carry the star.
    const { getByTestId, queryByTestId } = render(
      <CategoryProfile {...baseProps} winnerIndex={1} />
    );
    expect(getByTestId('cat-profile-winner-star-1')).toBeTruthy();
    expect(queryByTestId('cat-profile-winner-star-0')).toBeNull();
  });

  it('draws NO winner star when winnerIndex is undefined', () => {
    const { queryByTestId } = render(
      <CategoryProfile products={fragranceProducts} testID="cat-profile" />
    );
    expect(queryByTestId('cat-profile-winner-star-0')).toBeNull();
    expect(queryByTestId('cat-profile-winner-star-1')).toBeNull();
  });

  it('hides the entire block when NEITHER product has a category_profile', () => {
    const products: any = [{ name: 'A' }, { name: 'B' }];
    const { queryByTestId } = render(
      <CategoryProfile products={products} testID="cat-profile" />
    );
    expect(queryByTestId('cat-profile')).toBeNull();
  });

  it('hides the block when fields is an empty array', () => {
    const products: any = [
      { name: 'A', category_profile: { category: 'fragrances', fields: [] } },
      { name: 'B', category_profile: { category: 'fragrances', fields: [] } },
    ];
    const { queryByTestId } = render(
      <CategoryProfile products={products} testID="cat-profile" />
    );
    expect(queryByTestId('cat-profile')).toBeNull();
  });

  it('SYMMETRY — one product has a field the other lacks → no blank, each renders its own', () => {
    const products: any = [
      {
        name: 'Rich',
        category_profile: {
          category: 'fashion',
          fields: [
            { key: 'material', label: 'Material', value: 'Leather' },
            { key: 'origin', label: 'Origin', value: 'Italy' },
          ],
        },
      },
      {
        name: 'Sparse',
        category_profile: {
          category: 'fashion',
          fields: [{ key: 'material', label: 'Material', value: 'Canvas' }],
        },
      },
    ];
    const { getByTestId, queryByTestId } = render(
      <CategoryProfile products={products} winnerIndex={0} testID="cat-profile" />
    );
    // Both columns present.
    expect(getByTestId('cat-profile-col-0')).toBeTruthy();
    expect(getByTestId('cat-profile-col-1')).toBeTruthy();
    // Rich product shows both fields; sparse shows only material — no dash row
    // for the missing origin.
    expect(getByTestId('cat-profile-field-0-material')).toBeTruthy();
    expect(getByTestId('cat-profile-field-0-origin')).toBeTruthy();
    expect(getByTestId('cat-profile-field-1-material')).toBeTruthy();
    expect(queryByTestId('cat-profile-field-1-origin')).toBeNull();
  });

  it('still renders when ONLY one product has fields (the other column is name-only)', () => {
    const products: any = [
      {
        name: 'Has',
        category_profile: {
          category: 'supplements',
          fields: [{ key: 'count', label: 'Count', value: '120 capsules' }],
        },
      },
      { name: 'None' },
    ];
    const { getByTestId } = render(
      <CategoryProfile products={products} winnerIndex={0} testID="cat-profile" />
    );
    expect(getByTestId('cat-profile')).toBeTruthy();
    expect(getByTestId('cat-profile-field-0-count')).toBeTruthy();
    expect(getByTestId('cat-profile-col-1-empty')).toBeTruthy();
  });

  it('drops malformed field entries (missing value) defensively', () => {
    const products: any = [
      {
        name: 'X',
        category_profile: {
          category: 'electronics',
          fields: [
            { key: 'storage', label: 'Storage', value: '256GB' },
            { key: 'ram', label: 'RAM', value: '' }, // empty value → dropped
            { key: 'battery', label: 'Battery' }, // no value → dropped
          ],
        },
      },
    ];
    const { getByTestId, queryByTestId } = render(
      <CategoryProfile products={products} testID="cat-profile" />
    );
    expect(getByTestId('cat-profile-field-0-storage')).toBeTruthy();
    expect(queryByTestId('cat-profile-field-0-ram')).toBeNull();
    expect(queryByTestId('cat-profile-field-0-battery')).toBeNull();
  });

  // Per-category smoke: electronics + supplements render their schema fields.
  it('renders electronics fields (storage/processor) generically', () => {
    const products: any = [
      {
        name: 'iPhone 15',
        category_profile: {
          category: 'electronics',
          fields: [
            { key: 'storage', label: 'Storage', value: '128 GB' },
            { key: 'processor', label: 'Processor', value: 'A16 Bionic' },
          ],
        },
      },
      {
        name: 'Galaxy S24',
        category_profile: {
          category: 'electronics',
          fields: [
            { key: 'storage', label: 'Storage', value: '256 GB' },
            { key: 'processor', label: 'Processor', value: 'Snapdragon 8 Gen 3' },
          ],
        },
      },
    ];
    const { getByText, getAllByText } = render(
      <CategoryProfile products={products} winnerIndex={1} testID="cat-profile" />
    );
    expect(getByText('A16 Bionic')).toBeTruthy();
    expect(getByText('Snapdragon 8 Gen 3')).toBeTruthy();
    // Both columns render the Processor label (one per product).
    expect(getAllByText('Processor').length).toBe(2);
  });

  it('renders supplements fields (count/dosage) generically', () => {
    const products: any = [
      {
        name: 'NOW D3',
        category_profile: {
          category: 'supplements',
          fields: [
            { key: 'count', label: 'Count', value: '240 softgels' },
            { key: 'dosage', label: 'Dosage', value: '5000 IU' },
          ],
        },
      },
      {
        name: 'Solgar D3',
        category_profile: {
          category: 'supplements',
          fields: [
            { key: 'count', label: 'Count', value: '120 softgels' },
            { key: 'dosage', label: 'Dosage', value: '5000 IU' },
          ],
        },
      },
    ];
    const { getByText, getAllByText } = render(
      <CategoryProfile products={products} winnerIndex={0} testID="cat-profile" />
    );
    expect(getByText('240 softgels')).toBeTruthy();
    expect(getByText('120 softgels')).toBeTruthy();
    // Both products list a 5000 IU dosage.
    expect(getAllByText('5000 IU').length).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// Bundle-next Task #18(b) — fuller-payload 2-up column does NOT overflow/break.
// Backend #15 deepens 2nd-product extraction (MORE fields, longer values) — no
// contract change. RNTL has no real layout engine, so we verify the STRUCTURAL
// guards that prevent horizontal overflow + the graceful asymmetric render:
//   - col: flex:1 + minWidth:0 (lets each column shrink below content width so a
//     wide value/long token can't blow out the 50/50 split).
//   - product name: numberOfLines={1} (truncates a long name, never wrap-blowout).
//   - field value: NO numberOfLines (a long value WRAPS — vertical growth, not
//     horizontal overflow), full column width via label-above-value layout.
//   - a fuller / ASYMMETRIC payload (B has many more fields than A) renders both
//     columns with every field, no crash.
// ---------------------------------------------------------------------------
describe('CategoryProfile — Task #18(b) fuller-payload column overflow guards', () => {
  const flatten = (style: any) =>
    Object.assign({}, ...(Array.isArray(style) ? style : [style]).filter(Boolean));

  // All 11 electronics schema fields on product B (fuller), incl. deliberately
  // LONG values; product A intentionally sparse (asymmetric).
  const fullerProducts: any = [
    {
      name: 'iPhone 15',
      category_profile: {
        category: 'electronics',
        fields: [
          { key: 'storage', label: 'Storage', value: '128 GB' },
          { key: 'battery', label: 'Battery', value: '3,349 mAh' },
        ],
      },
    },
    {
      // A very long product name to exercise name truncation.
      name: 'Samsung Galaxy S24 Ultra 5G Titanium Black 1TB Unlocked International',
      category_profile: {
        category: 'electronics',
        fields: [
          { key: 'display', label: 'Display', value: '6.8" Dynamic AMOLED 2X, 120Hz, 1440 x 3120, peak 2600 nits' },
          { key: 'processor', label: 'Processor', value: 'Snapdragon 8 Gen 3 for Galaxy (4nm)' },
          { key: 'ram', label: 'RAM', value: '12 GB LPDDR5X' },
          { key: 'storage', label: 'Storage', value: '256 GB / 512 GB / 1 TB UFS 4.0' },
          { key: 'battery', label: 'Battery', value: '5,000 mAh, 45W wired, 15W wireless' },
          { key: 'rear_camera', label: 'Rear camera', value: '200 MP wide + 50 MP periscope + 10 MP tele + 12 MP ultrawide' },
          { key: 'front_camera', label: 'Front camera', value: '12 MP' },
          { key: 'os', label: 'OS', value: 'Android 14, One UI 6.1' },
          { key: 'connectivity', label: 'Connectivity', value: '5G, Wi-Fi 7, Bluetooth 5.3, NFC, UWB' },
          { key: 'weight', label: 'Weight', value: '232 g' },
          { key: 'water_resistance', label: 'Water resistance', value: 'IP68' },
        ],
      },
    },
  ];

  it('renders BOTH columns with every field for an asymmetric fuller payload (no crash)', () => {
    const { getByTestId } = render(
      <CategoryProfile products={fullerProducts} winnerIndex={1} testID="cp" />
    );
    expect(getByTestId('cp-col-0')).toBeTruthy();
    expect(getByTestId('cp-col-1')).toBeTruthy();
    // Sparse product A — its 2 fields.
    expect(getByTestId('cp-field-0-storage')).toBeTruthy();
    expect(getByTestId('cp-field-0-battery')).toBeTruthy();
    // Fuller product B — all 11 fields rendered.
    for (const k of [
      'display', 'processor', 'ram', 'storage', 'battery', 'rear_camera',
      'front_camera', 'os', 'connectivity', 'weight', 'water_resistance',
    ]) {
      expect(getByTestId(`cp-field-1-${k}`)).toBeTruthy();
    }
  });

  it('each column carries the flex:1 + minWidth:0 overflow guard', () => {
    const { getByTestId } = render(
      <CategoryProfile products={fullerProducts} winnerIndex={1} testID="cp" />
    );
    for (const colId of ['cp-col-0', 'cp-col-1']) {
      const style = flatten(getByTestId(colId).props.style);
      expect(style.flex).toBe(1);
      // minWidth:0 is THE guard that lets a column shrink below its content
      // width — without it a long value/token blows out the 50/50 split.
      expect(style.minWidth).toBe(0);
    }
  });

  it('a long product name truncates to one line (numberOfLines=1), never wraps to blow out the row', () => {
    const { getByText } = render(
      <CategoryProfile products={fullerProducts} winnerIndex={1} testID="cp" />
    );
    const nameNode = getByText(
      'Samsung Galaxy S24 Ultra 5G Titanium Black 1TB Unlocked International'
    );
    expect(nameNode.props.numberOfLines).toBe(1);
  });

  it('long field VALUES wrap (no numberOfLines) — vertical growth, never horizontal overflow', () => {
    const { getByText } = render(
      <CategoryProfile products={fullerProducts} winnerIndex={1} testID="cp" />
    );
    // The longest value renders in full (present in the tree) and is NOT capped
    // to a line count — it wraps within the column.
    const longValue = getByText(
      '6.8" Dynamic AMOLED 2X, 120Hz, 1440 x 3120, peak 2600 nits'
    );
    expect(longValue.props.numberOfLines).toBeUndefined();
  });

  it('handles a fuller Arabic (RTL) payload value without crash or truncation', () => {
    const arProducts: any = [
      {
        name: 'منتج أ',
        category_profile: {
          category: 'fragrances',
          fields: [{ key: 'scent_family', label: 'Scent family', value: 'عنبري / حار' }],
        },
      },
      {
        name: 'منتج ب الطويل جداً لاختبار الاقتطاع في العمود الضيق',
        category_profile: {
          category: 'fragrances',
          fields: [
            { key: 'scent_family', label: 'Scent family', value: 'جلدي / زهري' },
            { key: 'notes_top', label: 'Top notes', value: 'برغموت، فلفل أسود، هيل، زعفران، فلفل وردي' },
            { key: 'longevity', label: 'Longevity', value: 'من ٨ إلى ١٠ ساعات على البشرة' },
          ],
        },
      },
    ];
    const { getByTestId, getByText } = render(
      <CategoryProfile products={arProducts} winnerIndex={1} testID="cp" />
    );
    expect(getByTestId('cp-col-0')).toBeTruthy();
    expect(getByTestId('cp-col-1')).toBeTruthy();
    // The long Arabic value renders in full and wraps (not line-capped).
    const arVal = getByText('برغموت، فلفل أسود، هيل، زعفران، فلفل وردي');
    expect(arVal.props.numberOfLines).toBeUndefined();
  });
});
