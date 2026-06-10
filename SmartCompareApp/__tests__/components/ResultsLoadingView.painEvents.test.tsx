/**
 * ResultsLoadingView pain-workflow wiring — Bundle B B.1 (F3.5).
 *
 * Verifies the parent threads a trackEvent-backed onSignal to the ghost
 * cards: a signal from a card -> trackEvent(signal, { stage }, comparisonId)
 * on the existing /events batch endpoint. The card-side emission logic is
 * covered by StreamingProductCard.painEvents.test.tsx; here we cover the
 * parent's trackEvent plumbing.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

const trackEvent = jest.fn();
jest.mock('../../src/services/api', () => ({
  trackEvent: (...args: unknown[]) => trackEvent(...args),
}));

import { ResultsLoadingView } from '../../src/components/ResultsLoadingView';

beforeEach(() => {
  jest.useFakeTimers();
  trackEvent.mockClear();
});

afterEach(() => {
  jest.useRealTimers();
});

const baseProps = {
  query: 'iPhone 15 vs Galaxy S24',
  productNames: ['iPhone 15', 'Galaxy S24'],
  reachedStage: 'specs' as const,
};

describe('ResultsLoadingView pain-workflow wiring', () => {
  it('calls trackEvent with the stage + comparisonId when a card fires spec_expand', () => {
    const { getAllByTestId } = render(
      <ResultsLoadingView
        {...baseProps}
        comparisonId="cmp-1"
        products={[
          { name: 'iPhone 15', specs: { a: '1', b: '2', c: '3', d: '4' } },
          { name: 'Galaxy S24', specs: { a: '1' } },
        ]}
      />
    );
    // First ghost card has 4 specs -> "+1 more" affordance.
    const expand = getAllByTestId('ghost-card-0-card-spec-expand')[0];
    fireEvent.press(expand);
    expect(trackEvent).toHaveBeenCalledWith(
      'spec_expand',
      { stage: 'specs' },
      'cmp-1'
    );
  });

  it('fires result_abandon via trackEvent on unmount before verdict', () => {
    const { unmount } = render(
      <ResultsLoadingView {...baseProps} reachedStage="prices" />
    );
    unmount();
    const abandon = trackEvent.mock.calls.filter((c) => c[0] === 'result_abandon');
    expect(abandon.length).toBeGreaterThanOrEqual(1);
    // event_data carries the stage at abandon time.
    expect(abandon[0][1]).toEqual({ stage: 'prices' });
  });

  it('does NOT call trackEvent when trackPainEvents is false', () => {
    const { unmount } = render(
      <ResultsLoadingView
        {...baseProps}
        reachedStage="prices"
        trackPainEvents={false}
        products={[
          { name: 'iPhone 15', specs: { a: '1', b: '2', c: '3', d: '4' } },
          { name: 'Galaxy S24', specs: { a: '1' } },
        ]}
      />
    );
    unmount();
    expect(trackEvent).not.toHaveBeenCalled();
  });
});
