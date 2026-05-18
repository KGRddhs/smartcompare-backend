// Bundle C — DimensionBars RED tests (Section C plan C.7.2 / C.7.3 / C.7.4).
//
// Spec §6: hero + expand UI (3-4 dims immediately, "See full breakdown" row).
// Silent omission for both-products-null dims. Last-resort "—" only when single
// dim survives. Dev-mode contract violation node retained.
//
// RED until B.5 overhauls DimensionBars at src/components/results/DimensionBars.tsx.

import React from 'react';
import { render } from '@testing-library/react-native';
import { expectNoForbiddenStrings, expectNoBanner } from './_bundle_c_helpers';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { DimensionBars } from '../src/components/results/DimensionBars';

describe('DimensionBars (Bundle C §6 — hero + expand + silent omission)', () => {
  it('dims with BOTH products null are silently omitted from render', () => {
    const dims = [
      // value_score present — both products have data
      { dim_key: 'value_score', label: 'Value', score_a: 70, score_b: 65,
        winner: 'a' as const },
      // performance_score absent from dims[] (backend silent omission per §2h)
    ];
    const { queryByText, toJSON } = render(
      <DimensionBars dimensions={dims as any} />,
    );
    // No performance copy anywhere
    expect(queryByText(/performance/i)).toBeNull();
    // Value present
    expect(queryByText(/Value/i)).toBeTruthy();
    // NO "—" or "Limited data" copy when dim is silently omitted
    const serialised = JSON.stringify(toJSON());
    expect(serialised).not.toMatch(/—/);
    expect(serialised).not.toMatch(/Limited data/i);
  });

  it('NO forbidden vocabulary in rendered tree', () => {
    const dims = [
      { dim_key: 'value_score', label: 'Value', score_a: 70, score_b: 65,
        winner: 'a' as const },
      { dim_key: 'reviews', label: 'Reviews', score_a: 85, score_b: 80,
        winner: 'a' as const },
    ];
    const tree = render(<DimensionBars dimensions={dims as any} />).toJSON();
    expectNoForbiddenStrings(tree);
  });

  it('NO banner elements (project rule #1)', () => {
    const dims = [
      { dim_key: 'value_score', label: 'Value', score_a: 70, score_b: 65,
        winner: 'a' as const },
    ];
    const { queryByRole, queryByLabelText } = render(
      <DimensionBars dimensions={dims as any} />,
    );
    expectNoBanner(queryByRole, queryByLabelText);
  });

  it('snapshot — 4-dim hero view', () => {
    const dims = [
      { dim_key: 'value_score', label: 'Value', score_a: 78, score_b: 72,
        winner: 'a' as const },
      { dim_key: 'reviews', label: 'Reviews', score_a: 85, score_b: 80,
        winner: 'a' as const },
      { dim_key: 'price', label: 'Price', score_a: 80, score_b: 75,
        winner: 'a' as const },
      { dim_key: 'performance_score', label: 'Performance',
        score_a: 82, score_b: 79, winner: 'a' as const },
    ];
    const tree = render(<DimensionBars dimensions={dims as any} />).toJSON();
    expect(tree).toMatchSnapshot();
  });
});
