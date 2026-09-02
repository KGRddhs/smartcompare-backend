/**
 * M21 mobile-jank — HistoryScreen perceived-performance + dead-tap fixes.
 *
 * M18 findings covered:
 *  - MB-perf-07: row entrance stagger is index-scaled (`FadeInDown.delay(index * 50)`)
 *    so a row mounted by scrolling into the ~44-row "Older" section sits
 *    INVISIBLE for up to ~2.2s. Fix: cap the stagger (<= 300ms).
 *  - MB-perf-06/07: zero React.memo in the app — every search keystroke
 *    re-renders ALL mounted rows (each with 2 ProductImages + tone
 *    derivation). Fix: memoized HistoryRow + stable callbacks, measured
 *    here via the deriveTone call count per keystroke.
 *  - MB-flows-08: hero marquee tap resolves the id against the separately
 *    fetched history page and silently no-ops on a miss. Fix: navigate
 *    with the id directly, and prune the marquee after a delete.
 *
 * Render-based (not source-grep): the defects are runtime render behavior.
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { FadeInDown } from 'react-native-reanimated';

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

const mockGetComparisonHistory = jest.fn();
const mockDeleteComparison = jest.fn();
const mockGetProfileRecentDecisions = jest.fn();
const mockGetProfileMonthlyStats = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  getComparisonHistory: (...args: any[]) => mockGetComparisonHistory(...args),
  deleteComparison: (...args: any[]) => mockDeleteComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  getProfileRecentDecisions: (...args: any[]) => mockGetProfileRecentDecisions(...args),
  getProfileMonthlyStats: (...args: any[]) => mockGetProfileMonthlyStats(...args),
}));

jest.mock('../src/services/authService', () => ({
  clearSession: jest.fn().mockResolvedValue(undefined),
}));

// Wrap deriveTone so row re-renders are countable: it runs once per
// product tile derivation inside the row render path.
jest.mock('../src/utils/deriveTone', () => {
  const actual = jest.requireActual('../src/utils/deriveTone');
  return {
    __esModule: true,
    deriveTone: jest.fn((...args: any[]) => actual.deriveTone(...args)),
  };
});

// eslint-disable-next-line import/first
import { deriveTone } from '../src/utils/deriveTone';
// eslint-disable-next-line import/first
import HistoryScreen from '../src/screens/HistoryScreen';

const OLD_DATE = '2020-01-01T00:00:00Z';

function historyItem(id: string): any {
  return {
    id,
    full_response: null,
    query: `q-${id}`,
    input_type: 'text',
    product_names: [`Alpha ${id}`, `Beta ${id}`],
    winner_index: 0,
    created_at: OLD_DATE,
    category: null,
    verdict_short: null,
    winner_image_url: null,
    runner_up_image_url: null,
  };
}

function recentDecision(id: string): any {
  return {
    comparison_id: id,
    winner_name: `Winner ${id}`,
    runner_up_name: `Runner ${id}`,
    winner_image_url: null,
    runner_up_image_url: null,
  };
}

function setupApi({
  historyIds,
  recentIds,
}: {
  historyIds: string[];
  recentIds: string[];
}) {
  mockGetComparisonHistory.mockResolvedValue({
    comparisons: historyIds.map(historyItem),
    total: historyIds.length,
  });
  mockGetProfileMonthlyStats.mockResolvedValue({
    decisions_count: 3,
    savings_bhd: 12,
  });
  mockGetProfileRecentDecisions.mockResolvedValue({
    empty_state: false,
    recent: recentIds.map(recentDecision),
  });
  mockDeleteComparison.mockResolvedValue(undefined);
}

function makeNavigation() {
  return { navigate: jest.fn(), goBack: jest.fn() } as any;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('MB-flows-08 — hero marquee tap', () => {
  it('navigates to Results for a recent decision NOT in the loaded history page', async () => {
    setupApi({ historyIds: ['h1'], recentIds: ['gone-1', 'h1'] });
    const navigation = makeNavigation();
    const { getByTestId } = render(
      <HistoryScreen navigation={navigation} onLogout={jest.fn()} />
    );

    await waitFor(() => getByTestId('history-hero-card-gone-1'));
    fireEvent.press(getByTestId('history-hero-card-gone-1'));

    // Base behavior: `history.find((h) => h.id === id)` misses and the tap
    // is a silent no-op — navigate is never called.
    expect(navigation.navigate).toHaveBeenCalledWith('Results', {
      comparison_id: 'gone-1',
    });
  });

  it('prunes a just-deleted comparison from the marquee', async () => {
    setupApi({ historyIds: ['h1', 'h2'], recentIds: ['h1', 'h2'] });
    const navigation = makeNavigation();
    const { getByTestId, queryByTestId } = render(
      <HistoryScreen navigation={navigation} onLogout={jest.fn()} />
    );

    await waitFor(() => getByTestId('history-hero-card-h1'));
    fireEvent.press(getByTestId('history-row-h1-delete'));

    // Alert.alert is a jest.fn in the RN mock — invoke the destructive
    // confirm button the screen registered.
    const alertCalls = (Alert.alert as jest.Mock).mock.calls;
    expect(alertCalls.length).toBeGreaterThan(0);
    const buttons = alertCalls[alertCalls.length - 1][2];
    const destructive = buttons.find((b: any) => b.style === 'destructive');
    await destructive.onPress();

    // Base behavior: handleDelete only mutates the `history` array; the
    // marquee (fetched once on mount) keeps the deleted comparison.
    // (Explicit timeout: the default 1s waitFor can expire under full-suite
    // worker contention.)
    await waitFor(
      () => {
        expect(queryByTestId('history-hero-card-h1')).toBeNull();
      },
      { timeout: 5000 }
    );
    // The other card survives.
    expect(queryByTestId('history-hero-card-h2')).not.toBeNull();
  });
});

describe('MB-perf-07 — row entrance stagger cap', () => {
  it('caps every row entering delay at 300ms even deep in a section', async () => {
    const ids = Array.from({ length: 12 }, (_, i) => `r${i}`);
    setupApi({ historyIds: ids, recentIds: [] });
    const { getByTestId } = render(
      <HistoryScreen navigation={makeNavigation()} onLogout={jest.fn()} />
    );
    await waitFor(() => getByTestId('history-row-r11'));

    const delays = (FadeInDown.delay as jest.Mock).mock.calls.map((c) => c[0]);
    expect(delays.length).toBeGreaterThanOrEqual(12);
    // Base behavior: index * 50 → row 11 waits 550ms (and row ~44 in the
    // real "Older" section waits ~2.2s) before becoming visible.
    expect(Math.max(...delays)).toBeLessThanOrEqual(300);
  });
});

describe('MB-perf-06/07 — search keystrokes must not re-render mounted rows', () => {
  it('a keystroke in the search field derives zero row tones (memoized rows)', async () => {
    const ids = Array.from({ length: 12 }, (_, i) => `r${i}`);
    setupApi({ historyIds: ids, recentIds: ['r0'] });
    const { getByTestId, getByPlaceholderText } = render(
      <HistoryScreen navigation={makeNavigation()} onLogout={jest.fn()} />
    );
    await waitFor(() => getByTestId('history-row-r11'));

    (deriveTone as jest.Mock).mockClear();
    fireEvent.changeText(getByPlaceholderText('history.search'), 'a');

    // Base behavior: renderItem is an inline closure with zero memoized
    // row components, so ONE keystroke re-renders all 12 rows + marquee
    // (2 deriveTone calls each ≈ 26 calls). After the fix the memoized
    // rows and hero skip entirely: 0 calls.
    expect((deriveTone as jest.Mock).mock.calls.length).toBe(0);
  });
});
