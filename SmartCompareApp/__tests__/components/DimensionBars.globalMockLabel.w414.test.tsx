/**
 * W4-14 PIN 10 — under the GLOBAL `__mocks__/react-i18next` (no per-file mock:
 * its `stableT` ignores `defaultValue` and returns the KEY for anything outside
 * its tiny dictionary) a DimensionBars row still renders the backend label, never
 * `results.dimension.<key>`.
 *
 * PIN = green at the unit base 3985eaac (the label is rendered raw) and must stay
 * green: it reddens if the label helper loses the `localizedCurrency` echo guard
 * (mutation M2: `return t(k, { defaultValue: label })`).
 */
import React from 'react';
import { render } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';

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

describe('W4-14 DimensionBars under the global react-i18next mock', () => {
  it('PIN 10: rows, the insufficient row and the point-math fallback render the backend label, never the catalog key', () => {
    const r = render(
      <DimensionBars
        dimensions={[
          { key: 'longevity', label: 'Longevity', score_a: 80, score_b: 60, delta_text: '', confidence: 'medium' },
          { key: 'projection', label: 'Projection', score_a: 70, score_b: 60, delta_text: '+18pt', confidence: 'medium' },
          { key: 'durability', label: 'Durability', score_a: null, score_b: null, delta_text: '', data_insufficient: true },
        ] as any}
        winnerIndex={0}
        testID="bars"
      />,
    );
    const longevity = texts(r.getByTestId('bars-row-longevity').children as any);
    const projection = texts(r.getByTestId('bars-row-projection').children as any);
    const insufficient = texts(r.getByTestId('bars-row-durability-insufficient').children as any);
    r.unmount();
    expect(longevity[0]).toBe('Longevity');
    expect(projection[0]).toBe('Projection');
    expect(projection.filter((s) => s === 'Projection')).toHaveLength(2);
    expect(insufficient[0]).toBe('Durability');
    const all = [...longevity, ...projection, ...insufficient];
    expect(all.filter((s) => s.startsWith('results.dimension.'))).toEqual([]);
  });
});
