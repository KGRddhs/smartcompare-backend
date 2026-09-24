/**
 * W3-11bcd — MB-I18N-RTL-07 (c): the Home smart-pick tiles stop truncating
 * prices to whole dinars.
 *
 * Measured at base b63a8368: `HomeEditorialSections.tsx:142` / `:187`
 * render `{price.toFixed(0)} {t('home.smart_pick.bhd')}` — 12.345 BHD shows
 * as "12 د.ب" in Arabic. The fix routes both tiles through
 * `formatPrice(amount, 'BHD', t)` (BHD minor unit = 3 decimals, amount then
 * symbol). Under the echo-`t` mock `localizedCurrency` falls back to the ISO
 * code, so the expected text is "12.345 BHD".
 *
 * Harness = __tests__/SmartPickCard.imageUrl.test.tsx.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
  };
});

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

const mockSmartPick = jest.fn();
jest.mock('../src/services/api', () => ({
  getHomeSmartPick: () => mockSmartPick(),
  getHomeQuickCategories: () => Promise.resolve({ categories: [] }),
  getHomeSavings: () => Promise.resolve({ savings: null }),
  getHomeTrending: () => Promise.resolve({ items: [] }),
}));

import { SmartPickCard } from '../src/components/HomeEditorialSections';

function basePick(overrides: Record<string, any> = {}) {
  return {
    comparison_id: 'cmp_1',
    winner_name: 'Galaxy S24',
    runner_up_name: 'iPhone 15',
    winner_price_bhd: 12.345,
    runner_up_price_bhd: 8.5,
    reason_key: 'home.smart_pick.reason.fallback',
    reason_params: {},
    category: 'Electronics',
    updated_at: 'Updated today',
    winner_sub: null,
    runner_up_sub: null,
    verdict_short: null,
    winner_image_url: null,
    runner_up_image_url: null,
    ...overrides,
  };
}

describe('W3-11 RTL-07 (c) — smart-pick prices keep the BHD minor unit', () => {
  it('winner 12.345 → "12.345 BHD" and runner-up 8.5 → "8.500 BHD" (no whole-dinar truncation)', async () => {
    mockSmartPick.mockResolvedValue({ smart_pick: basePick(), empty_state: false });
    const { findByTestId, queryByText, getByText } = render(<SmartPickCard />);
    await findByTestId('home-smart-pick');

    expect(getByText('12.345 BHD')).toBeTruthy();
    expect(getByText('8.500 BHD')).toBeTruthy();
    // Today's truncated shape must be gone.
    expect(queryByText(/^12 /)).toBeNull();
  });
});
