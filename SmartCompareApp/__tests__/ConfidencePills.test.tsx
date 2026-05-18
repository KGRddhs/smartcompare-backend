// Bundle C — ConfidencePills RED tests (Section C plan C.6.3 / C.6.4).
//
// Spec §5b + 5c: 3 small pills (Price · Reviews · Specs) replacing the legacy
// single-word banner. Tap → bottom sheet with countable facts.
//
// Price pill HIDDEN ENTIRELY (not muted) when any product is estimated (§5c).
//
// RED until B.7 lands `ConfidencePills` + `ConfidenceDetailsSheet` at
// src/components/results/.

import React from 'react';
import { render } from '@testing-library/react-native';
import { expectNoForbiddenStrings } from './_bundle_c_helpers';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

function importComponent() {
  try {
    return require('../src/components/results/ConfidencePills').default;
  } catch {
    return null;
  }
}

describe('ConfidencePills (Bundle C §5)', () => {
  it('renders all 3 pills when no product is estimated', () => {
    const ConfidencePills = importComponent();
    if (!ConfidencePills) {
      throw new Error(
        'RED: ConfidencePills not yet implemented at src/components/results/ConfidencePills.tsx (B.7 pending)',
      );
    }
    const products = [
      { price: { source_method: 'page_scrape' } },
      { price: { source_method: 'firecrawl' } },
    ];
    const confidence = {
      legs: { price: 'strong', reviews: 'strong', specs: 'strong' },
    };
    const { queryByLabelText } = render(
      <ConfidencePills products={products} confidence={confidence} />,
    );
    expect(queryByLabelText(/price.*pill/i)).toBeTruthy();
    expect(queryByLabelText(/reviews.*pill/i)).toBeTruthy();
    expect(queryByLabelText(/specs.*pill/i)).toBeTruthy();
  });

  it('hides Price pill ENTIRELY when any product is estimated (§5c)', () => {
    const ConfidencePills = importComponent();
    if (!ConfidencePills) {
      throw new Error('RED: ConfidencePills not yet implemented');
    }
    const products = [
      { price: { source_method: 'page_scrape' } },
      { price: { source_method: 'estimated' } },
    ];
    const confidence = {
      legs: { price: 'strong', reviews: 'strong', specs: 'strong' },
    };
    const { queryByLabelText, toJSON } = render(
      <ConfidencePills products={products} confidence={confidence} />,
    );
    // Spec §5c — pill ABSENT from render tree, not muted
    expect(queryByLabelText(/price.*pill/i)).toBeNull();
    // Reviews + Specs still render
    expect(queryByLabelText(/reviews.*pill/i)).toBeTruthy();
    expect(queryByLabelText(/specs.*pill/i)).toBeTruthy();
    // NO "estimated" wording anywhere user-visible
    expectNoForbiddenStrings(toJSON());
  });

  it('hides Price pill even when only one product is estimated', () => {
    const ConfidencePills = importComponent();
    if (!ConfidencePills) {
      throw new Error('RED: ConfidencePills not yet implemented');
    }
    const products = [
      { price: { source_method: 'estimated' } },
      { price: { source_method: 'official_brand' } },
    ];
    const { queryByLabelText } = render(
      <ConfidencePills
        products={products}
        confidence={{ legs: { price: 'weak', reviews: 'strong', specs: 'strong' } }}
      />,
    );
    expect(queryByLabelText(/price.*pill/i)).toBeNull();
  });

  it('snapshot — all 3 strong, no estimated', () => {
    const ConfidencePills = importComponent();
    if (!ConfidencePills) {
      throw new Error('RED: ConfidencePills not yet implemented');
    }
    const tree = render(
      <ConfidencePills
        products={[
          { price: { source_method: 'page_scrape' } },
          { price: { source_method: 'firecrawl' } },
        ]}
        confidence={{ legs: { price: 'strong', reviews: 'strong', specs: 'strong' } }}
      />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('snapshot — Price pill hidden (one product estimated)', () => {
    const ConfidencePills = importComponent();
    if (!ConfidencePills) {
      throw new Error('RED: ConfidencePills not yet implemented');
    }
    const tree = render(
      <ConfidencePills
        products={[
          { price: { source_method: 'estimated' } },
          { price: { source_method: 'page_scrape' } },
        ]}
        confidence={{ legs: { price: 'weak', reviews: 'strong', specs: 'strong' } }}
      />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });
});
