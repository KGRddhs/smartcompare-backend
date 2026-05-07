/**
 * BonusCountdownCard tests — Phase 4 Task 41.
 *
 * Surfaces invitee bonus state on Home per design § 4e bonus-expiry
 * mechanics. Renders nothing when no active bonus. When active:
 * "5 free — 2 from {referrer} (expires 2d 14h)" with per-minute
 * countdown. After expiry: parent simply stops passing `expiresAt` so
 * the component renders its no-bonus state ("3 free anytime").
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

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

import { BonusCountdownCard } from '../../src/components/BonusCountdownCard';

beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2026-05-07T12:00:00Z'));
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('BonusCountdownCard — Phase 4 Task 41', () => {
  it('renders the active-bonus card with referrer + total + countdown', () => {
    const expiresAt = new Date('2026-05-09T14:00:00Z'); // ~ 2d 2h
    const { getByTestId } = render(
      <BonusCountdownCard
        baseFreeRemaining={3}
        bonusRemaining={2}
        referrerName="Ahmed"
        expiresAt={expiresAt}
      />
    );
    expect(getByTestId('bonus-countdown-card')).toBeTruthy();
    expect(getByTestId('bonus-countdown-time')).toBeTruthy();
  });

  it('renders the no-bonus fallback when bonusRemaining is 0', () => {
    const { getByTestId, queryByTestId } = render(
      <BonusCountdownCard baseFreeRemaining={3} bonusRemaining={0} />
    );
    expect(getByTestId('bonus-countdown-card')).toBeTruthy();
    expect(queryByTestId('bonus-countdown-time')).toBeNull();
  });

  it('renders the no-bonus fallback when expiresAt is missing', () => {
    const { getByTestId, queryByTestId } = render(
      <BonusCountdownCard
        baseFreeRemaining={3}
        bonusRemaining={2}
        referrerName="Ahmed"
      />
    );
    // No expiry → can't surface the countdown; treat as inactive bonus.
    expect(getByTestId('bonus-countdown-card')).toBeTruthy();
    expect(queryByTestId('bonus-countdown-time')).toBeNull();
  });

  it('renders the no-bonus fallback when expiresAt is in the past', () => {
    const expiresAt = new Date('2026-05-06T12:00:00Z'); // yesterday
    const { queryByTestId } = render(
      <BonusCountdownCard
        baseFreeRemaining={3}
        bonusRemaining={2}
        referrerName="Ahmed"
        expiresAt={expiresAt}
      />
    );
    expect(queryByTestId('bonus-countdown-time')).toBeNull();
  });

  it('hides the whole card when both baseFreeRemaining and bonusRemaining are 0', () => {
    const { queryByTestId } = render(
      <BonusCountdownCard baseFreeRemaining={0} bonusRemaining={0} />
    );
    expect(queryByTestId('bonus-countdown-card')).toBeNull();
  });

  it('updates the countdown per minute (re-renders when time advances)', () => {
    // 1h 5m to expiry → label "1h 5m"; +60s elapsed → "1h 4m"
    const expiresAt = new Date('2026-05-07T13:05:00Z');
    const { getByTestId } = render(
      <BonusCountdownCard
        baseFreeRemaining={3}
        bonusRemaining={2}
        referrerName="Ahmed"
        expiresAt={expiresAt}
      />
    );
    const initial = getByTestId('bonus-countdown-time').props.children;
    act(() => {
      jest.advanceTimersByTime(60 * 1000); // tick a minute
    });
    const later = getByTestId('bonus-countdown-time').props.children;
    expect(later).not.toBe(initial);
  });

  it('cleans up its interval on unmount (no throws)', () => {
    const { unmount } = render(
      <BonusCountdownCard
        baseFreeRemaining={3}
        bonusRemaining={2}
        referrerName="Ahmed"
        expiresAt={new Date('2026-05-09T12:00:00Z')}
      />
    );
    unmount();
    expect(() => {
      act(() => {
        jest.advanceTimersByTime(5 * 60 * 1000);
      });
    }).not.toThrow();
  });
});
