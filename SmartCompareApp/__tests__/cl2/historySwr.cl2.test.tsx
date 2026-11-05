/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R22-R24, P4-P6 (spec section 5, RULINGS_S81_G6
 * R-G6-10): the History SWR. With a user set, a tab focus inside the 30 s
 * window serves the cached list and does not refetch; a remount paints the
 * cached rows before the fetch lands; a delete invalidates. Without a user
 * every focus refetches (the A12 behaviour); pull-to-refresh, the search
 * submit and retry are always live; a failed load leaves no stamp.
 *
 * Harness: the HistoryScreen.searchState.a12 boundary mocks (the focus
 * callback is captured so a test can re-fire it the way React Navigation
 * does). The clock is the real one plus a settable skew, so waitFor keeps
 * its own timeout. swrCache is read through loadOptional (absent at base).
 */

import React from 'react';
import { Alert } from 'react-native';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';

const mockGetComparisonHistory = jest.fn();
const mockDeleteComparison = jest.fn();
const mockGetProfileRecentDecisions = jest.fn();
const mockGetProfileMonthlyStats = jest.fn();
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

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  getComparisonHistory: (...args: any[]) => mockGetComparisonHistory(...args),
  deleteComparison: (...args: any[]) => mockDeleteComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  getProfileRecentDecisions: (...args: any[]) => mockGetProfileRecentDecisions(...args),
  getProfileMonthlyStats: (...args: any[]) => mockGetProfileMonthlyStats(...args),
}));

jest.mock('../../src/services/authService', () => ({
  clearSession: jest.fn().mockResolvedValue(undefined),
}));

// eslint-disable-next-line import/first
import HistoryScreen from '../../src/screens/HistoryScreen';

function loadOptional(rel: string): any {
  try {
    return require(rel);
  } catch {
    return null;
  }
}

const SWR = '../../src/services/swrCache';

function historyItem(id: string): any {
  return {
    id,
    full_response: null,
    query: 'q-' + id,
    input_type: 'text',
    product_names: ['Alpha ' + id, 'Beta ' + id],
    winner_index: 0,
    created_at: '2020-01-01T00:00:00Z',
    category: null,
    verdict_short: null,
    winner_image_url: null,
    runner_up_image_url: null,
  };
}

function page(ids: string[]) {
  return { comparisons: ids.map(historyItem), total: ids.length };
}

function setupApi(ids: string[]) {
  mockGetComparisonHistory.mockResolvedValue(page(ids));
  mockGetProfileMonthlyStats.mockResolvedValue({ decisions_count: 0, savings_bhd: 0 });
  mockGetProfileRecentDecisions.mockResolvedValue({ empty_state: true, recent: [] });
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

const TEST_TIMEOUT_MS = 60000;
const WAIT_MS = 20000;

const realNow = Date.now.bind(Date);
let skewMs = 0;

/** The swrCache module (asserted present), reset and set to `user`. */
function swrWithUser(user: string | null): any {
  const swr = loadOptional(SWR);
  expect(swr).not.toBeNull();
  swr.clearSwrCache();
  swr.setSwrUser(user);
  return swr;
}

async function focus() {
  expect(mockFocusHolder.cb).not.toBeNull();
  await act(async () => {
    mockFocusHolder.cb!();
  });
  await act(async () => {
    await Promise.resolve();
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockFocusHolder.cb = null;
  skewMs = 0;
  jest.spyOn(Date, 'now').mockImplementation(() => realNow() + skewMs);
  const swr = loadOptional(SWR);
  if (swr && typeof swr.clearSwrCache === 'function') swr.clearSwrCache();
});

afterEach(() => {
  (Date.now as any).mockRestore?.();
});

describe('CL2 History SWR (C4)', () => {
  it('R22 user set: a focus at +10 s does not refetch; a focus at +31 s does', async () => {
    swrWithUser('u-a');
    setupApi(['h1']);
    const { getByTestId } = renderScreen();
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);

    skewMs = 10000;
    await focus();
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);

    skewMs = 31000;
    await focus();
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(2);
  }, TEST_TIMEOUT_MS);

  it('R23 warm cache: a remount paints the cached rows before the pending fetch', async () => {
    swrWithUser('u-a');
    setupApi(['h1', 'h2']);
    const first = renderScreen();
    await waitFor(() => first.getByTestId('history-row-h2'), { timeout: WAIT_MS });
    first.unmount();

    mockGetComparisonHistory.mockImplementation(() => new Promise(() => undefined));
    const second = renderScreen();
    expect(second.queryByTestId('history-row-h1')).not.toBeNull();
    expect(second.queryByTestId('history-row-h2')).not.toBeNull();
  }, TEST_TIMEOUT_MS);

  it('R24 a delete invalidates: the next focus inside 30 s fetches', async () => {
    swrWithUser('u-a');
    setupApi(['h1', 'h2']);
    const { getByTestId, queryByTestId } = renderScreen();
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);

    fireEvent.press(getByTestId('history-row-h1-delete'));
    const alertCalls = (Alert.alert as jest.Mock).mock.calls;
    expect(alertCalls.length).toBeGreaterThan(0);
    const buttons = alertCalls[alertCalls.length - 1][2];
    const destructive = buttons.find((b: any) => b.style === 'destructive');
    await act(async () => {
      await destructive.onPress();
    });
    expect(mockDeleteComparison).toHaveBeenCalledWith('h1');
    await waitFor(() => expect(queryByTestId('history-row-h1')).toBeNull(), {
      timeout: WAIT_MS,
    });

    skewMs = 10000;
    await focus();
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(2);
  }, TEST_TIMEOUT_MS);

  it('P4 no user: every focus refetches (the A12 behaviour)', async () => {
    const swr = loadOptional(SWR);
    if (swr) {
      swr.clearSwrCache();
      swr.setSwrUser(null);
    }
    setupApi(['h1']);
    const { getByTestId } = renderScreen();
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);
    skewMs = 1000;
    await focus();
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(2);
    skewMs = 2000;
    await focus();
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(3);
  }, TEST_TIMEOUT_MS);

  it('P5 user set, inside the window: search submit, pull-to-refresh and retry each fetch', async () => {
    const swr = loadOptional(SWR);
    if (swr) {
      swr.clearSwrCache();
      swr.setSwrUser('u-a');
    }
    setupApi(['h1']);
    const rendered = renderScreen();
    await waitFor(() => rendered.getByTestId('history-row-h1'), { timeout: WAIT_MS });
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);

    // Search submit.
    skewMs = 1000;
    fireEvent.changeText(rendered.getByPlaceholderText('history.search'), 'alpha');
    fireEvent(rendered.getByPlaceholderText('history.search'), 'submitEditing');
    await waitFor(() => expect(mockGetComparisonHistory).toHaveBeenCalledTimes(2), {
      timeout: WAIT_MS,
    });
    expect(mockGetComparisonHistory.mock.calls[1]).toEqual([50, 0, 'alpha']);
    await waitFor(() => rendered.getByTestId('history-row-h1'), { timeout: WAIT_MS });

    // Pull-to-refresh (made to fail, so the inline retry appears).
    skewMs = 2000;
    mockGetComparisonHistory.mockRejectedValueOnce(
      Object.assign(new Error('synthetic network'), { code: 'ERR_NETWORK' })
    );
    const lists = rendered.UNSAFE_root.findAll(
      (n: any) => !!(n.props && n.props.refreshControl)
    );
    expect(lists.length).toBeGreaterThan(0);
    await act(async () => {
      lists[0].props.refreshControl.props.onRefresh();
    });
    await waitFor(() => expect(mockGetComparisonHistory).toHaveBeenCalledTimes(3), {
      timeout: WAIT_MS,
    });

    // Retry.
    skewMs = 3000;
    const retry = await waitFor(() => rendered.getByTestId('history-inline-retry'), {
      timeout: WAIT_MS,
    });
    fireEvent.press(retry);
    await waitFor(() => expect(mockGetComparisonHistory).toHaveBeenCalledTimes(4), {
      timeout: WAIT_MS,
    });
  }, TEST_TIMEOUT_MS);

  it('P6 user set: a failed load leaves no stamp, so the next focus fetches', async () => {
    const swr = loadOptional(SWR);
    if (swr) {
      swr.clearSwrCache();
      swr.setSwrUser('u-a');
    }
    setupApi([]);
    mockGetComparisonHistory.mockReset();
    mockGetComparisonHistory.mockRejectedValueOnce(
      Object.assign(new Error('synthetic network'), { code: 'ERR_NETWORK' })
    );
    mockGetComparisonHistory.mockResolvedValue(page(['h1']));
    const { getByTestId } = renderScreen();
    await waitFor(() => getByTestId('history-load-error'), { timeout: WAIT_MS });
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(1);
    skewMs = 1000;
    await focus();
    expect(mockGetComparisonHistory).toHaveBeenCalledTimes(2);
    await waitFor(() => getByTestId('history-row-h1'), { timeout: WAIT_MS });
  }, TEST_TIMEOUT_MS);
});
