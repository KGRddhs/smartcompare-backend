/**
 * W3-16 — the attestation line ConsentRow ACTUALLY renders, in both catalogs.
 *
 * The consent sentence is legal wording that Ahmed approves; this pins the
 * exact string the row renders from the real en.json / ar.json (the screen
 * suites mock t() as the identity, so they never see the copy). Spacing is
 * part of the copy: the Arabic conjunction "و" attaches to the next word, so
 * `auth.consent.and` carries its own spacing (" and " / " و") and the row
 * adds none around it.
 *
 * If this test reddens because the COPY was deliberately changed, update the
 * expected strings AND the PR body / CLAUDE.md wording Ahmed approved.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

let mockCatalog: Record<string, string> = en as Record<string, string>;

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const value = mockCatalog[key];
      if (typeof value !== 'string') throw new Error(`missing i18n key ${key}`);
      return value;
    },
  }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { ConsentRow } = require('../src/components/ConsentRow');

function renderRow(error = false) {
  return render(
    <ConsentRow checked={false} onToggle={jest.fn()} onOpenLegal={jest.fn()} error={error} />,
  );
}

describe('W3-16 ConsentRow — rendered attestation copy', () => {
  it('English renders "I am 13 or older and I agree to the Terms and Privacy"', () => {
    mockCatalog = en as Record<string, string>;
    const screen = renderRow(true);

    expect(
      screen.getByText('I am 13 or older and I agree to the Terms and Privacy'),
    ).toBeTruthy();
    expect(screen.getByTestId('consent-error').props.children).toBe(
      'Please accept the Terms and confirm you are 13 or older to continue',
    );
  });

  it('Arabic renders the conjunction attached to the next word ("الشروط والخصوصية")', () => {
    mockCatalog = ar as Record<string, string>;
    const screen = renderRow(true);

    expect(
      screen.getByText('عمري 13 عامًا أو أكثر وأوافق على الشروط والخصوصية'),
    ).toBeTruthy();
    expect(screen.getByTestId('consent-error').props.children).toBe(
      'يرجى قبول الشروط وتأكيد أن عمرك 13 عامًا أو أكثر للمتابعة',
    );
  });
});
