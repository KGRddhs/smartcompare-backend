/**
 * TwoInputShell forced-RTL layout — M21 W4 rtl-i18n (MB-i18n-rtl-04).
 *
 * Under I18nManager.forceRTL(true) React Native ALREADY mirrors
 * `flexDirection: 'row'` (and resolves logical start/end). The shipped
 * component layered an explicit `row-reverse` + physical left/right
 * hairline/vs-pill variants ON TOP of that native mirroring, so the two
 * mirrors cancelled and the Home compare input rendered visually
 * backwards (LTR anatomy) for Arabic users.
 *
 * Contract after the fix:
 *   - NO 'row-reverse' anywhere in the rendered tree, either direction —
 *     rows are plain 'row' and RN owns the mirroring.
 *   - The hairline (the absolute-positioned width-1 rule) is anchored via
 *     the LOGICAL `start` offset, not physical left/right, so it tracks
 *     the numeral circles in both directions.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

let _mockLang = 'en';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: {
      language: _mockLang,
      changeLanguage: jest.fn(async (lang: string) => {
        _mockLang = lang;
      }),
    },
  }),
  initReactI18next: { type: '3rdParty', init: jest.fn() },
}));

jest.mock('react-native', () => {
  const actual = jest.requireActual('../../../__mocks__/react-native');
  return {
    ...actual,
    Keyboard: { dismiss: jest.fn() },
  };
});

import TwoInputShell, {
  __resetTwoInputCacheForTests,
} from '../TwoInputShell';
import { I18nManager, StyleSheet } from 'react-native';
import { spacing } from '../../theme';

const HAIRLINE_EDGE = spacing.lg + 12; // spacing.lg + CIRCLE_SIZE / 2

beforeEach(() => {
  __resetTwoInputCacheForTests();
  _mockLang = 'en';
  (I18nManager as any).isRTL = false;
});

afterEach(() => {
  (I18nManager as any).isRTL = false;
});

/** Flattened styles of every node in the rendered JSON tree. */
function collectStyles(node: any, out: Record<string, any>[] = []): Record<string, any>[] {
  if (!node) return out;
  if (Array.isArray(node)) {
    node.forEach((n) => collectStyles(n, out));
    return out;
  }
  if (node.props?.style) out.push(StyleSheet.flatten(node.props.style));
  collectStyles(node.children, out);
  return out;
}

function renderShell(): Record<string, any>[] {
  const { toJSON } = render(
    <TwoInputShell mode="text" onSubmit={jest.fn()} />
  );
  return collectStyles(toJSON());
}

describe('TwoInputShell — no double-mirror under forced RTL (MB-i18n-rtl-04)', () => {
  it('RTL: never uses row-reverse (RN mirrors plain row natively)', () => {
    _mockLang = 'ar';
    (I18nManager as any).isRTL = true;
    const styles = renderShell();
    const reversed = styles.filter((s) => s.flexDirection === 'row-reverse');
    expect(reversed).toEqual([]);
  });

  it('LTR: rows are plain row too (single code path both directions)', () => {
    const styles = renderShell();
    expect(styles.filter((s) => s.flexDirection === 'row-reverse')).toEqual([]);
    expect(styles.some((s) => s.flexDirection === 'row')).toBe(true);
  });

  it('the numeral+box row itself keeps flexDirection row (both directions)', () => {
    // Regression guard: the old inline ternary was the ONLY thing giving
    // the row a horizontal direction — dropping it must not let the row
    // fall back to RN's default 'column'. The row is identified by its
    // gap+alignItems signature (styles.row).
    for (const rtl of [false, true]) {
      (I18nManager as any).isRTL = rtl;
      _mockLang = rtl ? 'ar' : 'en';
      const styles = renderShell();
      const rows = styles.filter(
        (s) => s.gap === spacing.sm && s.alignItems === 'center'
      );
      expect(rows.length).toBeGreaterThanOrEqual(2); // Box A + Box B rows
      for (const row of rows) expect(row.flexDirection).toBe('row');
    }
  });

  it('hairline anchors via logical start (not physical left/right) in RTL', () => {
    _mockLang = 'ar';
    (I18nManager as any).isRTL = true;
    const styles = renderShell();
    const hairline = styles.find(
      (s) => s.position === 'absolute' && s.width === 1
    );
    expect(hairline).toBeDefined();
    expect(hairline!.start).toBe(HAIRLINE_EDGE);
    expect(hairline!.left).toBeUndefined();
    expect(hairline!.right).toBeUndefined();
  });

  it('hairline anchors via logical start in LTR as well', () => {
    const styles = renderShell();
    const hairline = styles.find(
      (s) => s.position === 'absolute' && s.width === 1
    );
    expect(hairline).toBeDefined();
    expect(hairline!.start).toBe(HAIRLINE_EDGE);
    expect(hairline!.left).toBeUndefined();
    expect(hairline!.right).toBeUndefined();
  });
});
