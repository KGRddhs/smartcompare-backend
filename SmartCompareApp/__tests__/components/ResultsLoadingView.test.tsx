/**
 * ResultsLoadingView tests — Phase 3 Task 28.
 *
 * Full-screen dramatized loading per design § 3 — stage checklist
 * + ghost cards + variable-easing progress bar + tips carousel after
 * 8s. Pure presentational; the parent owns the SSE subscription and
 * passes the streaming state in.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium', Heavy: 'heavy' },
  __esModule: true,
}));

// B.1 F3.5 — the ghost cards now thread an onSignal that calls trackEvent
// (e.g. result_abandon fires when a card unmounts before the verdict stage,
// which auto-cleanup triggers at teardown). Stub trackEvent so these tests
// make no network attempt; pain-event behaviour is covered by
// ResultsLoadingView.painEvents.test.tsx + StreamingProductCard.painEvents.test.tsx.
jest.mock('../../src/services/api', () => ({
  trackEvent: jest.fn(),
}));

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

import { ResultsLoadingView } from '../../src/components/ResultsLoadingView';

beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

const baseProps = {
  query: 'iPhone 15 vs Galaxy S24',
  productNames: ['iPhone 15', 'Galaxy S24'],
  reachedStage: 'init' as const,
};

describe('ResultsLoadingView', () => {
  it('renders the query echo and 5 stage rows on initial mount', () => {
    const { getByTestId, getByText } = render(<ResultsLoadingView {...baseProps} />);
    expect(getByText('iPhone 15 vs Galaxy S24')).toBeTruthy();
    expect(getByTestId('results-loading')).toBeTruthy();
    expect(getByTestId('stage-init-icon')).toBeTruthy();
    expect(getByTestId('stage-specs-icon')).toBeTruthy();
    expect(getByTestId('stage-prices-icon')).toBeTruthy();
    expect(getByTestId('stage-reviews-icon')).toBeTruthy();
    expect(getByTestId('stage-verdict-icon')).toBeTruthy();
  });

  it('renders one StreamingProductCard per product name', () => {
    const { getByTestId } = render(<ResultsLoadingView {...baseProps} />);
    expect(getByTestId('ghost-card-0')).toBeTruthy();
    expect(getByTestId('ghost-card-1')).toBeTruthy();
  });

  it('marks earlier stages as done as reachedStage advances', () => {
    const { getByTestId } = render(
      <ResultsLoadingView {...baseProps} reachedStage="prices" />
    );
    expect(getByTestId('stage-init-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-specs-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-prices-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-reviews-icon').props.accessibilityLabel).toBe('pending');
    expect(getByTestId('stage-verdict-icon').props.accessibilityLabel).toBe('pending');
  });

  it('does not show LoadingTipsCarousel before 8s elapsed', () => {
    const { queryByTestId } = render(<ResultsLoadingView {...baseProps} />);
    act(() => {
      jest.advanceTimersByTime(7999);
    });
    expect(queryByTestId('loading-tips')).toBeNull();
  });

  it('shows LoadingTipsCarousel after 8s', () => {
    const { getByTestId } = render(<ResultsLoadingView {...baseProps} />);
    act(() => {
      jest.advanceTimersByTime(8000);
    });
    expect(getByTestId('loading-tips')).toBeTruthy();
  });

  it('respects the configurable tipsAfterMs override', () => {
    const { getByTestId, queryByTestId } = render(
      <ResultsLoadingView {...baseProps} tipsAfterMs={2000} />
    );
    act(() => {
      jest.advanceTimersByTime(1999);
    });
    expect(queryByTestId('loading-tips')).toBeNull();
    act(() => {
      jest.advanceTimersByTime(2);
    });
    expect(getByTestId('loading-tips')).toBeTruthy();
  });

  it('passes per-product streaming data through to ghost cards', () => {
    const { getByText } = render(
      <ResultsLoadingView
        {...baseProps}
        reachedStage="specs"
        products={[
          { name: 'iPhone 15', specs: { storage: '256GB' } },
          { name: 'Galaxy S24', specs: { storage: '128GB' } },
        ]}
      />
    );
    expect(getByText('iPhone 15')).toBeTruthy();
    expect(getByText('Galaxy S24')).toBeTruthy();
  });
});
