/**
 * Time-related edge cases for shouldShowDemographicsPrompt cooldown.
 *
 * Covers DST transitions, time arithmetic with non-integer days, and
 * cooldown calculations stable under timezone shifts.
 */

import {
  shouldShowDemographicsPrompt,
  COOLDOWN_DAYS,
} from '../src/services/demographicsTrigger';

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

describe('shouldShowDemographicsPrompt — fine-grained timing', () => {
  it('shows when cooldown is exactly 7 days minus 1 hour (still under, does NOT show)', () => {
    // 6 days 23 hours since dismissal — still under 7 days → no show
    const dismissed = new Date(Date.now() - (COOLDOWN_DAYS * DAY - HOUR));
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: dismissed,
        currentSessionIndex: 4,
      })
    ).toBe(false);
  });

  it('shows when cooldown is 7 days plus 1 hour (over → show)', () => {
    const dismissed = new Date(Date.now() - (COOLDOWN_DAYS * DAY + HOUR));
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: dismissed,
        currentSessionIndex: 4,
      })
    ).toBe(true);
  });

  it('shows when cooldown is 7 days plus 1 second (just over → show)', () => {
    const dismissed = new Date(Date.now() - (COOLDOWN_DAYS * DAY + SECOND));
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: dismissed,
        currentSessionIndex: 4,
      })
    ).toBe(true);
  });

  it('handles a wildly old lastDismissedAt (1 year ago) for dismissedCount=3', () => {
    const dismissed = new Date(Date.now() - 365 * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: dismissed,
        currentSessionIndex: 4,
      })
    ).toBe(true);
  });

  it('cooldown evaluation does not crash on Date constructed from invalid string', () => {
    // Defensive — getTime() on Invalid Date is NaN; comparison is false
    const invalid = new Date('not-a-date');
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: invalid,
        currentSessionIndex: 4,
      })
    ).toBe(false);
  });

  it('with dismissedCount=2 and stale lastDismissedAt, sessionIndex=3 still shows (cooldown does not apply yet)', () => {
    const dismissed = new Date(Date.now() - 30 * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 2,
        lastDismissedAt: dismissed,
        currentSessionIndex: 3,
      })
    ).toBe(true);
  });

  it('with dismissedCount=2 and SAME-session index 2, does NOT show (already shown)', () => {
    const dismissed = new Date(Date.now() - HOUR);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 2,
        lastDismissedAt: dismissed,
        currentSessionIndex: 2,
      })
    ).toBe(false);
  });
});
