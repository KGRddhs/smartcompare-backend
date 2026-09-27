/**
 * W4-14 Part A3 — "Where the runner-up wins": `dimRowText(d, t)` falls back to the
 * LOCALIZED dimension label when delta_text is raw point-math.
 *
 * REAL i18next at lng='ar' with the REAL catalogs (per-file factory).
 * RED = fails at the unit base 3985eaac; PIN = green there and must stay green.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

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
    initReactI18next: { type: '3rdParty', init: () => {} },
  };
});

import { RunnerUpWinsCard } from '../../src/components/results/RunnerUpWinsCard';
import ar from '../../src/i18n/ar.json';

const arCat = ar as Record<string, string>;

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

function renderDim(delta: string): string[] {
  const r = render(
    <RunnerUpWinsCard
      products={[{ name: 'A' }, { name: 'B' }] as any}
      winnerIndex={0}
      dimensions={[{ key: 'projection', label: 'Projection', score_a: 60, score_b: 80, delta_text: delta } as any]}
      keyTradeoff={null}
    />,
  );
  const t = texts(r.getByTestId('runner-up-wins-dim-projection').children as any);
  r.unmount();
  return t;
}

describe('W4-14 RunnerUpWinsCard under lng=ar (real catalog)', () => {
  it("RED 11: a point-math delta ('+18pt') falls back to the Arabic label", () => {
    const t = renderDim('+18pt');
    expect(t).not.toContain('Projection');
    expect(t).not.toContain('+18pt');
    expect(arCat['results.dimension.projection']).toBeDefined();
    expect(t).toContain(arCat['results.dimension.projection']);
  });

  it("PIN 12: a qualitative delta_text ('Longer-lasting') passes through unchanged", () => {
    const t = renderDim('Longer-lasting');
    expect(t).toContain('Longer-lasting');
  });
});
