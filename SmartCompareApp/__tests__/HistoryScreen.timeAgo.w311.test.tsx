/**
 * W3-11bcd — MB-I18N-RTL-08: the History row's relative time goes through
 * the catalog under the SCREEN's own `t`.
 *
 * `HistoryScreen.tsx` (HistoryRow) is the only product call site of
 * `formatTimeAgo(d, language, t)`. The formatter itself is pinned in
 * src/utils/__tests__/formatDate.test.ts, but that says nothing about what
 * the screen passes in: an identity or stub `t` at the call site still
 * type-checks and would render raw `time.minutesAgo` keys in every History
 * row. This renders the real screen with `t` resolving through a REAL
 * i18next instance over the real catalogs (lng='ar', so the plural families
 * resolve) and pins the sentence an Arabic user reads.
 *
 * Harness = __tests__/HistoryScreen.searchState.a12.test.tsx.
 */
import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import { createInstance } from 'i18next';
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const AR = ar as Record<string, string>;

const mockI18n = createInstance();

jest.mock('react-i18next', () => {
  const t = (key: string, opts?: any) => mockI18n.t(key, opts);
  const result = { t, i18n: { language: 'ar', changeLanguage: jest.fn() } };
  return { useTranslation: () => result };
});

const mockGetComparisonHistory = jest.fn();

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      ReactRequired.useEffect(() => {
        const cleanup = cb();
        return cleanup;
      }, []);
    },
  };
});

jest.mock('../src/services/api', () => ({
  __esModule: true,
  getComparisonHistory: (...args: any[]) => mockGetComparisonHistory(...args),
  deleteComparison: jest.fn().mockResolvedValue(undefined),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  getProfileRecentDecisions: jest.fn().mockResolvedValue({ empty_state: false, recent: [] }),
  getProfileMonthlyStats: jest.fn().mockResolvedValue({ decisions_count: 3, savings_bhd: 12 }),
}));

jest.mock('../src/services/authService', () => ({
  clearSession: jest.fn().mockResolvedValue(undefined),
}));

// eslint-disable-next-line import/first
import HistoryScreen from '../src/screens/HistoryScreen';

const NOW = Date.UTC(2026, 8, 11, 12);
const WAIT_MS = 20000;

function historyItem(id: string, createdAtMs: number): any {
  return {
    id,
    full_response: null,
    query: `q-${id}`,
    input_type: 'text',
    product_names: [`Alpha ${id}`, `Beta ${id}`],
    winner_index: 0,
    created_at: new Date(createdAtMs).toISOString(),
    category: null,
    verdict_short: null,
    winner_image_url: null,
    runner_up_image_url: null,
  };
}

beforeAll(async () => {
  await mockI18n.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
  });
});

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(Date, 'now').mockReturnValue(NOW);
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('W3-11 RTL-08 — History row relative time under ar', () => {
  it('5 minutes and 2 hours ago render the Arabic plural forms, never a raw catalog key', async () => {
    mockGetComparisonHistory.mockResolvedValue({
      comparisons: [historyItem('h1', NOW - 5 * 60_000), historyItem('h2', NOW - 2 * 3_600_000)],
      total: 2,
    });
    const screen = render(
      <HistoryScreen
        navigation={{ navigate: jest.fn(), goBack: jest.fn() } as any}
        onLogout={jest.fn()}
      />,
    );
    await waitFor(() => screen.getByTestId('history-row-h2'), { timeout: WAIT_MS });

    // Arabic "few" (3-10) for 5 minutes and the grammatical dual for 2 hours
    // (no digit), read straight from the catalog.
    const fiveMinutes = AR['time.minutesAgo_few'].replace('{{count}}', '5');
    const twoHours = AR['time.hoursAgo_two'];
    expect(screen.getByText(fiveMinutes)).toBeTruthy();
    expect(screen.getByText(twoHours)).toBeTruthy();
    expect(screen.queryByText(/^time\./)).toBeNull();
  }, 60000);
});
