/**
 * Bundle E S3 — Lane A2 — ResultsAccordion render-based coverage tests.
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

const mockProducts: any = [
  {
    name: 'iPhone 15',
    brand: 'Apple',
    price: { amount: 329, currency: 'BHD' },
    rating: 4.4,
    review_count: 520,
    pros: ['Faster CPU', 'Better ecosystem'],
    cons: ['Lower camera score'],
    specs: {
      display: '6.1" OLED',
      camera: '48 MP',
      battery: '3,349 mAh',
      storage: '128 GB',
      brand: 'Apple', // hidden
      _source: 'gpt', // ends with _source, hidden
      missing: null, // null, filtered
      na: 'N/A', // NA value, filtered
    },
  },
  {
    name: 'Galaxy S24',
    brand: 'Samsung',
    price: { amount: 299, currency: 'BHD' },
    rating: 4.6,
    review_count: 720,
    pros: ['Better camera', 'Longer battery', 'Lower price'],
    cons: ['Slower updates'],
    specs: {
      display: '6.2" AMOLED',
      camera: '50 MP',
      battery: '4,000 mAh',
      storage: '128 GB',
    },
  },
];

const mockReviewProducts: any = [
  {
    name: 'iPhone 15',
    rating: 4.4,
    review_count: 520,
    review_summary: {
      consensus: 'Reliable but pricey',
      highlights: [
        { sentiment: 'positive', point: 'Great ecosystem integration' },
        { sentiment: 'negative', point: 'Battery weaker than rivals' },
      ],
    },
  },
  {
    name: 'Galaxy S24',
    rating: 4.6,
    review_count: 720,
    review_summary: {
      consensus: 'Strong camera + battery',
      highlights: [
        { sentiment: 'positive', point: 'Sharp low-light photos' },
      ],
    },
  },
];

describe('ResultsAccordion — render coverage', () => {
  it('renders the "Dig deeper" eyebrow + 3 toggles', () => {
    const { getByText, getByTestId } = render(
      <ResultsAccordion products={mockProducts} />
    );
    expect(getByText('results.digDeeper')).toBeTruthy();
    expect(getByTestId('results-accordion-toggle-reviews')).toBeTruthy();
    expect(getByTestId('results-accordion-toggle-proscons')).toBeTruthy();
    expect(getByTestId('results-specs-toggle')).toBeTruthy();
  });

  it('starts with all sections collapsed (no body rendered)', () => {
    const { queryByTestId } = render(
      <ResultsAccordion products={mockProducts} />
    );
    expect(queryByTestId('results-accordion-body-reviews')).toBeNull();
    expect(queryByTestId('results-accordion-body-proscons')).toBeNull();
    expect(queryByTestId('results-accordion-body-specs')).toBeNull();
  });

  it('opens the reviews section when its toggle is pressed', () => {
    const { getByTestId } = render(
      <ResultsAccordion products={mockProducts} reviewProducts={mockReviewProducts} />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByTestId('results-accordion-body-reviews')).toBeTruthy();
  });

  it('closes the reviews section when toggled twice', () => {
    const { getByTestId, queryByTestId } = render(
      <ResultsAccordion products={mockProducts} reviewProducts={mockReviewProducts} />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByTestId('results-accordion-body-reviews')).toBeTruthy();
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(queryByTestId('results-accordion-body-reviews')).toBeNull();
  });

  it('one-toggle-at-a-time — opening proscons closes reviews', () => {
    const { getByTestId, queryByTestId } = render(
      <ResultsAccordion products={mockProducts} reviewProducts={mockReviewProducts} />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByTestId('results-accordion-body-reviews')).toBeTruthy();
    fireEvent.press(getByTestId('results-accordion-toggle-proscons'));
    expect(queryByTestId('results-accordion-body-reviews')).toBeNull();
    expect(getByTestId('results-accordion-body-proscons')).toBeTruthy();
  });

  it('Phase 5.2 — renders review_praise per product; NO consensus, highlights, or verbatim quotes', () => {
    // Faithful-results Phase 5.2 (Contract 2): the reviews body shows a
    // synthesized praise line per product. The consensus paragraph, the
    // +/− sentiment bullets, AND the highlight-point quote lines are all
    // gone — `review_summary.highlights` is no longer a render source.
    const reviewProductsWithPraise = mockReviewProducts.map((p: any, i: number) => ({
      ...p,
      review_praise:
        i === 0
          ? 'Owners praise the ecosystem and overall reliability.'
          : 'Reviewers highlight the sharp low-light camera.',
    }));
    const { getByTestId, getByText, queryByText } = render(
      <ResultsAccordion
        products={mockProducts}
        reviewProducts={reviewProductsWithPraise}
      />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    // Consensus paragraph not rendered.
    expect(queryByText('Reliable but pricey')).toBeNull();
    // Old +/− prefixed bullets not rendered.
    expect(queryByText('+ Great ecosystem integration')).toBeNull();
    expect(queryByText('− Battery weaker than rivals')).toBeNull();
    // Highlight points are NO LONGER surfaced as quote lines.
    expect(queryByText('“Great ecosystem integration”')).toBeNull();
    expect(queryByText('“Sharp low-light photos”')).toBeNull();
    // The synthesized praise lines ARE rendered.
    expect(getByText('Owners praise the ecosystem and overall reliability.')).toBeTruthy();
    expect(getByText('Reviewers highlight the sharp low-light camera.')).toBeTruthy();
  });

  it('renders pros + cons per product in the proscons body', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={mockProducts} />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-proscons'));
    expect(getByText('+ Faster CPU')).toBeTruthy();
    expect(getByText('+ Better camera')).toBeTruthy();
    expect(getByText('− Lower camera score')).toBeTruthy();
    expect(getByText('− Slower updates')).toBeTruthy();
  });

  it('renders the specs table with merged keys', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={mockProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
    expect(getByText('display')).toBeTruthy();
    expect(getByText('6.1" OLED')).toBeTruthy();
    expect(getByText('6.2" AMOLED')).toBeTruthy();
  });

  it('filters HIDDEN_FIELDS + _source suffix + NA values from specs', () => {
    const { getByTestId, queryByText } = render(
      <ResultsAccordion products={mockProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // 'brand' (HIDDEN) + '_source' (suffix) + 'missing' (null) + 'na' (N/A)
    expect(queryByText('brand')).toBeNull();
    expect(queryByText('_source')).toBeNull();
    expect(queryByText('missing')).toBeNull();
    expect(queryByText('na')).toBeNull();
  });

  it('always shows same-on-both spec rows (no Show-differences-only toggle)', () => {
    // Design-structure pass (2026-06-16): the "Show differences only"
    // Switch was removed to match the reference. Same-on-both rows like
    // 'storage' (128 GB on both) now always render.
    const { getByTestId, queryByText } = render(
      <ResultsAccordion products={mockProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(queryByText('storage')).toBeTruthy();
  });

  it('renders specs eyebrow with key count fallback when no specs', () => {
    const noSpecs = [
      { name: 'A', brand: 'X', price: null, specs: {} },
      { name: 'B', brand: 'Y', price: null, specs: {} },
    ];
    const { getByTestId } = render(
      <ResultsAccordion products={noSpecs as any} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
  });

  it('renders the bare reviews fallback sub when no count AND no rating', () => {
    // Strip both review_count and rating → sub falls back to the plain
    // phrase (no avg prefix, no count prefix).
    const noSignal = [
      { ...mockProducts[0], review_count: 0, rating: undefined },
      { ...mockProducts[1], review_count: 0, rating: undefined },
    ];
    const { getByText } = render(
      <ResultsAccordion products={noSignal as any} />
    );
    expect(getByText('results.accordion.reviewsSub')).toBeTruthy();
  });

  it('prepends the weighted-avg rating to the reviews sub when ratings present', () => {
    // ratings 4.4 + 4.6 weighted by 520/720 reviews ≈ 4.5; total reviews
    // 1,240. Sub format: "{avg}★ avg · {total} reviews across both".
    const { getByText } = render(
      <ResultsAccordion products={mockProducts} reviewProducts={mockReviewProducts} />
    );
    expect(
      getByText(
        '4.5results.accordion.reviewsAvg · 1,240 results.accordion.reviewsSub'
      )
    ).toBeTruthy();
  });

  it('handles missing reviewProducts (defaults to products array)', () => {
    const { getByTestId } = render(
      <ResultsAccordion products={mockProducts} />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByTestId('results-accordion-body-reviews')).toBeTruthy();
  });

  it('handles missing specsProducts (defaults to products array)', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={mockProducts} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByText('display')).toBeTruthy();
  });

  it('exposes accessibilityState.expanded on the specs toggle', () => {
    const { getByTestId } = render(
      <ResultsAccordion products={mockProducts} />
    );
    const toggle = getByTestId('results-specs-toggle');
    expect(toggle.props.accessibilityState).toMatchObject({ expanded: false });
    fireEvent.press(toggle);
    const reFetched = getByTestId('results-specs-toggle');
    expect(reFetched.props.accessibilityState).toMatchObject({ expanded: true });
  });

  it('renders spec rows for the single-product degenerate case', () => {
    // With one product the table still surfaces its spec rows.
    const oneProduct = [mockProducts[0]];
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={oneProduct as any} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByText('display')).toBeTruthy();
  });

  it('renders empty proscons body when both products lack pros + cons', () => {
    const noPC = [
      { ...mockProducts[0], pros: [], cons: [] },
      { ...mockProducts[1], pros: [], cons: [] },
    ];
    const { getByTestId, queryByText } = render(
      <ResultsAccordion products={noPC as any} />
    );
    fireEvent.press(getByTestId('results-accordion-toggle-proscons'));
    expect(queryByText('+ Faster CPU')).toBeNull();
    expect(queryByText('+ Better camera')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// W1 walk-fix 2026-06-18 — CategoryProfile moved INTO the accordion as the
// FIRST "At a glance" section (curated; NOT the full Specs table). It renders
// EMBEDDED (no own card — the accordion body supplies the chrome) and is
// hidden entirely when neither product has category_profile fields.
// ---------------------------------------------------------------------------
describe('ResultsAccordion — "At a glance" category-profile section (W1)', () => {
  const productsWithProfile: any = [
    {
      name: 'Black Orchid',
      category_profile: {
        category: 'fragrances',
        fields: [
          { key: 'scent_family', label: 'Scent family', value: 'Amber / Spicy' },
          { key: 'longevity', label: 'Longevity', value: '8-10 hours' },
        ],
      },
    },
    {
      name: 'Oud Wood',
      category_profile: {
        category: 'fragrances',
        fields: [
          { key: 'scent_family', label: 'Scent family', value: 'Woody' },
          { key: 'notes_top', label: 'Top notes', value: 'Rosewood, Cardamom' },
        ],
      },
    },
  ];

  it('shows the profile section FIRST (its toggle precedes reviews) when a product has profile fields', () => {
    const { getByTestId } = render(
      <ResultsAccordion
        products={productsWithProfile}
        winnerIndex={0}
        testID="acc"
      />,
    );
    const profileToggle = getByTestId('results-accordion-toggle-profile');
    const reviewsToggle = getByTestId('results-accordion-toggle-reviews');
    expect(profileToggle).toBeTruthy();
    // DFS order — the profile toggle is encountered before the reviews toggle.
    const order: string[] = [];
    const walk = (n: any) => {
      if (!n) return;
      const tid = n?.props?.testID;
      if (tid === 'results-accordion-toggle-profile' || tid === 'results-accordion-toggle-reviews') order.push(tid);
      (Array.isArray(n.children) ? n.children : []).forEach(walk);
    };
    walk(render(
      <ResultsAccordion products={productsWithProfile} winnerIndex={0} testID="acc" />,
    ).toJSON());
    expect(order[0]).toBe('results-accordion-toggle-profile');
  });

  it('renders the EMBEDDED curated grid when the profile section is opened', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion
        products={productsWithProfile}
        winnerIndex={0}
        testID="acc"
      />,
    );
    fireEvent.press(getByTestId('results-accordion-toggle-profile'));
    expect(getByTestId('results-accordion-body-profile')).toBeTruthy();
    // Embedded CategoryProfile renders both columns + real field values.
    expect(getByTestId('acc-category-profile-col-0')).toBeTruthy();
    expect(getByTestId('acc-category-profile-col-1')).toBeTruthy();
    expect(getByText('Amber / Spicy')).toBeTruthy();
    expect(getByText('Rosewood, Cardamom')).toBeTruthy();
  });

  it('embedded profile does NOT render its own standalone card/eyebrow (no double-card)', () => {
    const { getByTestId, queryByText } = render(
      <ResultsAccordion
        products={productsWithProfile}
        winnerIndex={0}
        testID="acc"
      />,
    );
    fireEvent.press(getByTestId('results-accordion-toggle-profile'));
    // The standalone "At a glance" eyebrow (results.categoryProfile.title) is
    // NOT rendered inside the embedded grid — the SECTION HEADER carries the
    // label instead. (The i18n stub returns the key, so assert the key text
    // appears only via the section header path, not duplicated in the body.)
    // The embedded component renders just the grid (no wrapper eyebrow Text).
    const body = getByTestId('results-accordion-body-profile');
    const texts: string[] = [];
    const walk = (n: any) => {
      if (!n) return;
      if (typeof n.children?.[0] === 'string') texts.push(n.children[0]);
      (Array.isArray(n.children) ? n.children : []).forEach(walk);
    };
    walk(body);
    // The body shows field values/labels but NOT the standalone title eyebrow.
    expect(texts).not.toContain('results.categoryProfile.title');
    expect(queryByText).toBeTruthy();
  });

  it('hides the profile section entirely when no product has category_profile fields', () => {
    const { queryByTestId } = render(
      <ResultsAccordion products={mockProducts} testID="acc" />,
    );
    expect(queryByTestId('results-accordion-toggle-profile')).toBeNull();
  });
});
