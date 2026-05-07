/**
 * CohortBadge tests — Phase 3 Task 31.
 *
 * Inline pill that surfaces "X shoppers in {governorate} also picked
 * this" on the Results screen. Slides from right (LTR) / left (RTL) on
 * mount with 240ms ease-out + opacity fade per design § 4b.
 *
 * Pure presentational. Slide direction comes from the `isRTL` prop so
 * tests can control it without mocking I18nManager.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

// Honor `defaultValue` + simple {{var}} interpolation. The shared mock at
// __mocks__/react-i18next.ts only knows a few keys and ignores defaults,
// which makes assertion against the rendered string brittle. This local
// mock keeps the test independent of the i18n catalog.
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

import { CohortBadge } from '../../src/components/CohortBadge';

describe('CohortBadge', () => {
  it('renders the cohort copy with peer count and governorate', () => {
    const { getByText } = render(
      <CohortBadge peerCount={12} governorate="Capital" />
    );
    // Component composes the copy; we test for the parts so the test is
    // resilient to copy phrasing tweaks (the i18n suite owns the literal).
    expect(getByText(/12/)).toBeTruthy();
    expect(getByText(/Capital/)).toBeTruthy();
  });

  it('exposes the peer count as a host node prop for assertions', () => {
    const { getByTestId } = render(
      <CohortBadge peerCount={47} governorate="Muharraq" testID="badge" />
    );
    const node = getByTestId('badge');
    expect(node.props['data-peer-count']).toBe(47);
    expect(node.props['data-governorate']).toBe('Muharraq');
  });

  it('exposes data-direction=ltr by default', () => {
    const { getByTestId } = render(
      <CohortBadge peerCount={12} governorate="Capital" testID="badge" />
    );
    expect(getByTestId('badge').props['data-direction']).toBe('ltr');
  });

  it('exposes data-direction=rtl when isRTL=true', () => {
    const { getByTestId } = render(
      <CohortBadge peerCount={12} governorate="Capital" isRTL testID="badge" />
    );
    expect(getByTestId('badge').props['data-direction']).toBe('rtl');
  });

  it('renders nothing when peerCount is 0 or below', () => {
    const { queryByTestId, rerender } = render(
      <CohortBadge peerCount={0} governorate="Capital" testID="badge" />
    );
    expect(queryByTestId('badge')).toBeNull();

    rerender(<CohortBadge peerCount={-5} governorate="Capital" testID="badge" />);
    expect(queryByTestId('badge')).toBeNull();
  });

  it('renders nothing when governorate is missing', () => {
    const { queryByTestId } = render(
      <CohortBadge peerCount={12} governorate="" testID="badge" />
    );
    expect(queryByTestId('badge')).toBeNull();
  });
});
