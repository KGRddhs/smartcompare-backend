/**
 * A12 — HistoryScreen search / focus-refetch / load-failure states.
 *
 * Mobile-checkup finding A12 (P2). Three coupled defects, all render
 * behaviour (not source-grep):
 *
 *  1. Submit blanked the WHOLE screen. `onSubmitEditing` set the single
 *     `loading` flag, and the full-screen early return above the main
 *     `return (...)` then unmounted the header, the hero marquee and the
 *     very search field the user had just typed into — the field they
 *     submitted from vanished under a centred spinner.
 *
 *  2. Focus refetch used a STALE closure. `useFocusEffect(useCallback(fn,
 *     []))` pins render-1's arrow, which resolved render-1's `const
 *     loadHistory`, which closed over render-1's `searchQuery` = ''.
 *     `search` is a server-side query param, so every return to the tab
 *     (History stays mounted while Results opens as a root-stack modal)
 *     refetched UNFILTERED and clobbered the filtered list while the input
 *     still displayed the query.
 *
 *  3. A first-load network failure rendered the ONBOARDING empty state.
 *     The non-401 catch left `history` at [], `finally` cleared loading,
 *     and the render ternary hit `history.length === 0 ? renderEmpty()` —
 *     so a user with 40 saved comparisons and a flaky connection was told
 *     "Your first comparison is waiting" with a "Start Comparing" CTA.
 *     Same block also gave a zero-result SEARCH that same onboarding copy
 *     with no way to drop the filter.
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';

const mockGetComparisonHistory = jest.fn();
const mockDeleteComparison = jest.fn();
const mockGetProfileRecentDecisions = jest.fn();
const mockGetProfileMonthlyStats = jest.fn();

// Holds the callback the screen handed to useFocusEffect, so a test can
// re-invoke it the way React Navigation does when the tab regains focus.
const mockFocusHolder: { cb: null | (() => void) } = { cb: null };

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      mockFocusHolder.cb = cb;
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
  deleteComparison: (...args: any[]) => mockDeleteComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  getProfileRecentDecisions: (...args: any[]) => mockGetProfileRecentDecisions(...args),
  getProfileMonthlyStats: (...args: any[]) => mockGetProfileMonthlyStats(...args),
}));

jest.mock('../src/services/authService', () => ({
  clearSession: jest.fn().mockResolvedValue(undefined),
}));

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

function page(ids: string[]) {
  return { comparisons: ids.map(historyItem), total: ids.length };
}

function setupApi(historyIds: string[]) {
  mockGetComparisonHistory.mockResolvedValue(page(historyIds));
  mockGetProfileMonthlyStats.mockResolvedValue({ decisions_count: 3, savings_bhd: 12 });
  mockGetProfileRecentDecisions.mockResolvedValue({ empty_state: false, recent: [] });
  mockDeleteComparison.mockResolvedValue(undefined);
}

function renderScreen() {
  return render(
    <HistoryScreen
      navigation={{ navigate: jest.fn(), goBack: jest.fn() } as any}
      onLogout={jest.fn()}
    />
  );
}

// Explicit budgets: jest's 5s default and waitFor's 1s default both expire
// on this suite under worker contention (the same reason
// HistoryScreen.mobileJank.m21.test.tsx pins `{ timeout: 5000 }`), which
// reports as a spurious "element not found" on a fix that works.
const TEST_TIMEOUT_MS = 60000;
const WAIT_MS = 20000;

beforeEach(() => {
  jest.clearAllMocks();
  mockFocusHolder.cb = null;
});

describe('A12 — search submit keeps the screen mounted', () => {
  it('does not unmount the search field or the loaded rows while refetching', async () => {
    setupApi(['h1', 'h2']);
    const { getByTestId, getByPlaceholderText, queryByTestId } = renderScreen();
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });

    // Hold the refetch open so the busy window is observable.
    let resolveRefetch: (value: any) => void = () => {};
    mockGetComparisonHistory.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveRefetch = resolve;
      })
    );

    fireEvent.changeText(getByPlaceholderText('history.search'), 'alpha');
    fireEvent(getByPlaceholderText('history.search'), 'submitEditing');

    // Base behaviour: `setLoading(true)` hit the full-screen early return,
    // so the field the user just submitted from was gone and this throws.
    expect(getByPlaceholderText('history.search')).toBeTruthy();
    // The rows the user was looking at stay on screen...
    expect(queryByTestId('history-row-h1')).not.toBeNull();
    // ...and the busy state is an inline indicator in the search row.
    expect(queryByTestId('history-search-busy')).not.toBeNull();

    await act(async () => {
      resolveRefetch(page(['h1']));
    });
    await waitFor(() => expect(queryByTestId('history-search-busy')).toBeNull(), {
      timeout: WAIT_MS,
    });
  }, TEST_TIMEOUT_MS);
});

describe('A12 — focus refetch carries the active filter', () => {
  it('refetches with the submitted query, not an empty one, when the tab regains focus', async () => {
    setupApi(['h1']);
    const { getByTestId, getByPlaceholderText } = renderScreen();
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });

    fireEvent.changeText(getByPlaceholderText('history.search'), 'alpha');
    fireEvent(getByPlaceholderText('history.search'), 'submitEditing');
    await waitFor(() => expect(mockGetComparisonHistory).toHaveBeenCalledTimes(2), {
      timeout: WAIT_MS,
    });
    expect(mockGetComparisonHistory.mock.calls[1]).toEqual([50, 0, 'alpha']);

    mockGetComparisonHistory.mockClear();
    expect(mockFocusHolder.cb).not.toBeNull();
    await act(async () => {
      mockFocusHolder.cb!();
    });

    // Base behaviour: the `[]`-pinned focus callback resolved render-1's
    // `loadHistory`, whose `searchQuery` was '' — so this arrived as
    // [50, 0, undefined] and `setHistory` clobbered the filtered list.
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);
    expect(mockGetComparisonHistory.mock.calls[0]).toEqual([50, 0, 'alpha']);
  }, TEST_TIMEOUT_MS);
});

describe('A12 — load failure is distinct from an empty account', () => {
  it('renders a retry state instead of the first-comparison onboarding CTA', async () => {
    setupApi([]);
    mockGetComparisonHistory.mockReset();
    mockGetComparisonHistory.mockRejectedValueOnce(
      Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' })
    );

    const { getByTestId, queryByText } = renderScreen();

    // Base behaviour: the catch left history at [] and the ternary fell
    // through to renderEmpty(), so this testID never existed.
    await waitFor(() => getByTestId('history-load-error'), { timeout: WAIT_MS });
    expect(queryByText('history.empty.title')).toBeNull();
    expect(queryByText('history.empty.cta')).toBeNull();

    mockGetComparisonHistory.mockResolvedValue(page(['h1']));
    fireEvent.press(getByTestId('history-load-error-retry'));
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });
  }, TEST_TIMEOUT_MS);

  it('a zero-result search offers clearing the filter, not "Start Comparing"', async () => {
    setupApi(['h1']);
    const { getByTestId, getByPlaceholderText, queryByText } = renderScreen();
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });

    mockGetComparisonHistory.mockResolvedValueOnce(page([]));
    fireEvent.changeText(getByPlaceholderText('history.search'), 'zzz');
    fireEvent(getByPlaceholderText('history.search'), 'submitEditing');

    // Base behaviour: zero matches rendered the onboarding empty state,
    // whose only CTA navigated away to Home.
    await waitFor(() => getByTestId('history-no-matches'), { timeout: WAIT_MS });
    expect(queryByText('history.empty.cta')).toBeNull();

    mockGetComparisonHistory.mockResolvedValueOnce(page(['h1']));
    fireEvent.press(getByTestId('history-no-matches-clear'));
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });

    const calls = mockGetComparisonHistory.mock.calls;
    expect(calls[calls.length - 1]).toEqual([50, 0, undefined]);
  }, TEST_TIMEOUT_MS);
});
